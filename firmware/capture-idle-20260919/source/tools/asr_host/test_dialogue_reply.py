"""Compile the actual reply dispatcher/client and sink activation regressions."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
agent = (root/'packages/ai_agent/src/core/agent_loop.c').read_text()
working = agent[agent.index('static const char* s_working_phrases'):agent.index('/* Check for duplicate tool calls.')]
client = (root/'packages/ai_agent/src/sdk/velaclaw_client_local.c').read_text()
client = '\n'.join(line for line in client.splitlines() if not line.startswith('#include'))
sink = (root/'external/ffmpeg/ffmpeg/libavfilter/asink_adevsink.c').read_text()
sink = sink[sink.index('static int adevsink_activate('):sink.index('static int adevsink_query_formats(')]

cases = {
'reply': r'''
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
#include <stdio.h>
#define OK 0
#define AGENT_CHAN_FEISHU "feishu"
#define AGENT_CHAN_VOICE "voice"
#define AGENT_CHAN_WEIXIN "weixin"
typedef struct { char channel[32], chat_id[32]; char *content; } agent_msg_t;
typedef struct velaclaw_client_s velaclaw_client_t;
typedef struct { const char *text; int timeout_ms; } velaclaw_ask_req_t;
static void (*tap)(const agent_msg_t*,void*);
static void *tap_cookie;
static int sends, replies;
static int mbus_tap_register(const char *ch, void (*cb)(const agent_msg_t*,void*), void *cookie) {
    (void)ch;tap=cb;tap_cookie=cookie;return 0;
}
static void mbus_tap_unregister(const char *ch) { (void)ch;tap=NULL; }
static int message_bus_push_inbound(agent_msg_t *m) { free(m->content);return 0; }
static int message_bus_push_outbound(agent_msg_t *m) {
    sends++;
    if (tap && !strcmp(m->channel,"local_client")) tap(m,tap_cookie);
    free(m->content);return 0;
}
''' + client + '\n' + working + r'''
static void on_reply(int rc,const char *text,void *cookie) {
    assert(!rc);assert(cookie==&replies);
    assert(!strcmp(text,"actual model answer"));replies++;
}
int main(void) {
    velaclaw_client_t *c=velaclaw_client_open("qiji_chat");assert(c);
    agent_msg_t m={.channel="local_client",.chat_id="qiji_chat"};
    for (int i=0;i<3;i++) {
        velaclaw_ask_req_t req={.text="hello",.timeout_ms=90000};
        assert(!velaclaw_ask(c,&req,on_reply,&replies));
        send_working_status(&m,0);
        assert(replies==i);assert(sends==i);
        m.content=strdup("actual model answer");
        message_bus_push_outbound(&m);assert(replies==i+1);
    }
    strcpy(m.channel,"cli");send_working_status(&m,0);assert(sends==4);
    send_working_status(&m,1);assert(sends==4);
    velaclaw_client_close(c);puts("PASS final reply callback retained across 3 turns; CLI progress preserved");
}
''',
'sink': r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#define AVERROR_EOF (-541478725)
typedef struct { int queued,status_in,status_out; } AVFilterLink;
typedef struct { int frame_size; } Encoder;
typedef struct { Encoder *enc_ctx; bool started; } ADevSinkPriv;
typedef struct { AVFilterLink *inputs[1]; void *priv; } AVFilterContext;
typedef struct { int nb_samples; } AVFrame;
static int frames,requests,stops,output_error;
static int adevsink_output_packet(AVFilterContext *c,int s) { (void)c;(void)s;return output_error; }
static int ff_inlink_check_available_frame(AVFilterLink *l) { return l->queued>0; }
static int adevsink_start(AVFilterContext *c) { ((ADevSinkPriv*)c->priv)->started=true;return 0; }
static int ff_inlink_consume_frame(AVFilterLink *l,AVFrame **f) {
    if (!l->queued) return 0;
    l->queued--;*f=calloc(1,sizeof(**f));(*f)->nb_samples=480;return 1;
}
static int ff_inlink_consume_samples(AVFilterLink *l,int a,int b,AVFrame **f) {
    (void)a;(void)b;return ff_inlink_consume_frame(l,f);
}
static void av_frame_free(AVFrame **f) { free(*f);*f=NULL; }
static int adevsink_send_frame(AVFilterContext *c,AVFrame *f) { (void)c;if(f)frames++;return 0; }
static void ff_filter_set_ready(AVFilterContext *c,int n) { (void)c;(void)n; }
static int ff_inlink_acknowledge_status(AVFilterLink *l,int *s,int64_t *pts) {
    *pts=0;if(l->queued)return *s=0;
    if(l->status_out)return *s=l->status_out;
    if(!l->status_in)return *s=0;
    *s=l->status_out=l->status_in;return 1;
}
static void adevsink_stop(AVFilterContext *c) {
    ADevSinkPriv *p=c->priv;if(p->started){stops++;p->started=false;}
}
static void ff_inlink_request_frame(AVFilterLink *l) {
    assert(!l->status_in && !l->status_out);requests++;
}
''' + sink + r'''
int main(void) {
    AVFilterLink link={0};ADevSinkPriv priv={0};AVFilterContext ctx={{&link},&priv};
    for(int turn=0;turn<3;turn++) {
        /* Official audio_set_format_config resets these on each new link. */
        link.status_in=link.status_out=0;
        assert(!adevsink_activate(&ctx));assert(requests==turn+1);
        link.queued=3;link.status_in=AVERROR_EOF;
        for(int i=0;i<3;i++)assert(!adevsink_activate(&ctx));
        assert(frames==3*(turn+1));assert(stops==turn);
        assert(!adevsink_activate(&ctx));assert(stops==turn+1);
        assert(!adevsink_activate(&ctx));assert(requests==turn+1);
    }
    link.status_in=-5;link.status_out=0;assert(adevsink_activate(&ctx)==-5);
    output_error=-11;assert(adevsink_activate(&ctx)==-11);
    puts("PASS queued audio drains before EOF; no requests after EOF; 3 link lifecycles and errors");
}
'''
}
with tempfile.TemporaryDirectory(prefix='qiji-dialogue-') as tmp:
    for name, code in cases.items():
        source = Path(tmp)/(name+'.c')
        binary = Path(tmp)/name
        source.write_text(code)
        subprocess.run(['cc','-Wall','-Wextra','-Werror','-pthread',str(source),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True,timeout=10)
