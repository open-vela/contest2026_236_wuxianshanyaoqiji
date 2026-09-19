"""Replay idle device events against actual official capture activation code."""
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
ffmpeg = root/'external/ffmpeg/ffmpeg'
relative = 'libavfilter/asrc_adevsrc.c'

def extract(source):
    force = source[source.index('static inline void adevsrc_force_request('):source.index('static int adevsrc_control_message(')]
    activate = source[source.index('static int adevsrc_activate('):source.index('static int adevsrc_get_control_message(')]
    return force + activate

prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#define AVERROR(e) (-(e))
#define AVERROR_EOF (-541478725)
#define FFERROR_NOT_READY (-12345)
typedef struct { int status_in, frame_wanted_out; } AVFilterLink;
typedef AVFilterLink FilterLinkInternal;
typedef struct { bool opened; } ADevSrcPriv;
typedef struct { AVFilterLink *outputs[1]; void *priv; } AVFilterContext;
typedef struct { int samples; } AVFrame;
static int reads, closes, opens, queued, next_error;
static FilterLinkInternal *ff_link_internal(AVFilterLink *l) { return l; }
static void ff_filter_set_ready(AVFilterContext *c,int n) { (void)c;(void)n; }
static int ff_outlink_frame_wanted(AVFilterLink *l) { return l->frame_wanted_out; }
static int ff_outlink_get_status(AVFilterLink *l) { return l->status_in; }
static int adevsrc_open(AVFilterContext *c) {
    ADevSrcPriv *p=c->priv;
    if(!p->opened){p->opened=true;opens++;}return 0;
}
static void adevsrc_close(AVFilterContext *c) {
    ADevSrcPriv *p=c->priv;
    if(p->opened){p->opened=false;closes++;}
}
static int adevsrc_receive_frame(AVFilterContext *c,AVFrame **f) {
    (void)c;reads++;
    if(next_error){int e=next_error;next_error=0;return e;}
    *f=calloc(1,sizeof(**f));(*f)->samples=960;return 0;
}
static int ff_filter_frame(AVFilterLink *l,AVFrame *f) {
    l->frame_wanted_out=0;queued+=f->samples;free(f);return 0;
}
static int adevsrc_send_empty_frame(AVFilterContext *c) { (void)c;return 0; }
'''
suffix = r'''
int main(void) {
    AVFilterLink link={.status_in=AVERROR_EOF};
    ADevSrcPriv priv={0};AVFilterContext ctx={{&link},&priv};
    adevsrc_force_request(&ctx);
    assert(adevsrc_activate(&ctx)==FFERROR_NOT_READY);
    assert(!reads && !opens);
    for(int turn=0;turn<3;turn++) {
        /* Official format negotiation reopens links for a new recording. */
        link.status_in=0;link.frame_wanted_out=0;
        assert(adevsrc_activate(&ctx)==FFERROR_NOT_READY);
        adevsrc_force_request(&ctx);assert(!adevsrc_activate(&ctx));
        assert(priv.opened && opens==turn+1 && queued==960);
        queued=0; /* recorder consumes the live frame */
        int live_reads=reads;
        /* unlink propagates status via volume; no recorder remains. */
        link.status_in=AVERROR_EOF;
        for(int event=0;event<10000;event++) {
            adevsrc_force_request(&ctx);
            assert(adevsrc_activate(&ctx)==FFERROR_NOT_READY);
        }
        assert(!priv.opened && closes==turn+1);
        assert(reads==live_reads && !queued);
    }
    link.status_in=0;adevsrc_force_request(&ctx);next_error=AVERROR(EAGAIN);
    assert(adevsrc_activate(&ctx)==AVERROR(EAGAIN));assert(priv.opened);
    adevsrc_force_request(&ctx);next_error=AVERROR_EOF;
    assert(!adevsrc_activate(&ctx));assert(!priv.opened);
    puts("PASS 3 recordings, 30000 idle events, zero idle audio queued, reopen and input EOF/EAGAIN");
}
'''

resource.setrlimit(resource.RLIMIT_CORE,(0,0))
with tempfile.TemporaryDirectory(prefix='qiji-capture-idle-') as tmp:
    before = subprocess.check_output(['git','-C',str(ffmpeg),'show','HEAD:'+relative],text=True)
    after = (ffmpeg/relative).read_text()
    for label, source in [('before',before),('after',after)]:
        p=Path(tmp)/(label+'.c');binary=Path(tmp)/label
        p.write_text(prefix+extract(source)+suffix)
        subprocess.run(['cc','-Wall','-Wextra','-Wno-unused-function',str(p),'-o',str(binary)],check=True)
        run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=10)
        if label=='before':
            assert run.returncode!=0,'Regression must reproduce on official pre-fix source'
            print('PASS regression reproduces on official pre-fix source')
        else:
            assert run.returncode==0,run.stderr
            print(run.stdout.strip())
