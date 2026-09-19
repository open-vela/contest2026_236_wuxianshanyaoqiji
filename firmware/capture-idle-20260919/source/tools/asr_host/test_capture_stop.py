"""Exercise actual PCM accept/read and stop_with_text against an idle socket."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
media = (root/'frameworks/multimedia/media/client/media_graph.c').read_text()
media = media[media.index('static int media_accept_socket('):media.index('static void media_event_cb(')]
voice = (root/'packages/ai_agent/src/voice/voice_channel.c').read_text()
voice = voice[voice.index('int voice_channel_stop_with_text('):voice.index('/* Strip Markdown')]
code = r'''#define _GNU_SOURCE
#define CONFIG_GEMINI_CHAT_MINIMAL 1
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/time.h>
#include <syslog.h>
#include <poll.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <errno.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#include <fcntl.h>
typedef struct { int socket, socket_fd; atomic_int refs; } MediaIOPriv;
static void media_release_cb(void *p) { atomic_fetch_sub(&((MediaIOPriv *)p)->refs,1); }
'''+media+r'''
typedef void voice_asr_stream_t;
enum { VOICE_IDLE, VOICE_RECORDING, VOICE_STOPPING };
static const char *TAG="test";
static struct {
    pthread_mutex_t lock; int state; pthread_t rec_thread;
    MediaIOPriv *cap; size_t pcm_len; void *asr_stream; void *pcm_buf;
} s_voice={.lock=PTHREAD_MUTEX_INITIALIZER};
static atomic_int reader_exited, reader_ready;
static void audio_capture_abort(MediaIOPriv *cap) {
    assert(atomic_load(&reader_exited));
    close(cap->socket);cap->socket=0;
}
static void audio_capture_close(MediaIOPriv *cap) { close(cap->socket_fd); }
static int voice_asr_stream_finish(void *stream,char *text,size_t len) {
    (void)stream;assert(atomic_load(&reader_exited));snprintf(text,len,"recognized");return 0;
}
static int voice_asr_recognize(void *pcm,size_t n,char *text,size_t len) {
    (void)pcm;(void)n;(void)text;(void)len;return -ENODATA;
}
'''+voice+r'''
static void *reader(void *p) {
    (void)p;char chunk[256];
    for (;;) {
        pthread_mutex_lock(&s_voice.lock);int state=s_voice.state;pthread_mutex_unlock(&s_voice.lock);
        if (state!=VOICE_RECORDING) break;
        int n=media_process_data(s_voice.cap,false,chunk,sizeof(chunk));
        assert(n==-EAGAIN || n==-EWOULDBLOCK);
        atomic_store(&reader_ready,1);usleep(10000);
    }
    atomic_store(&reader_exited,1);return NULL;
}
int main(void) {
    for (int round=0;round<3;round++) {
        struct sockaddr_un addr={.sun_family=AF_UNIX};
        snprintf(addr.sun_path,sizeof(addr.sun_path),"/tmp/qiji-capture-%ld",(long)getpid());
        int listenfd=socket(AF_UNIX,SOCK_STREAM,0), peer=socket(AF_UNIX,SOCK_STREAM,0);
        assert(listenfd>0 && peer>0);assert(!bind(listenfd,(void*)&addr,sizeof(addr)));
        assert(!listen(listenfd,1));assert(!connect(peer,(void*)&addr,sizeof(addr)));
        MediaIOPriv cap={.socket=0,.socket_fd=listenfd,.refs=1};
        assert(!media_accept_socket(&cap));
        assert(fcntl(cap.socket,F_GETFL)&O_NONBLOCK);
        s_voice.cap=&cap;s_voice.state=VOICE_RECORDING;s_voice.asr_stream=&cap;
        atomic_store(&reader_ready,0);atomic_store(&reader_exited,0);
        assert(!pthread_create(&s_voice.rec_thread,NULL,reader,NULL));
        while (!atomic_load(&reader_ready)) usleep(1000);
        struct timespec start,end;clock_gettime(CLOCK_MONOTONIC,&start);
        char text[64];assert(!voice_channel_stop_with_text(text,sizeof(text)));
        clock_gettime(CLOCK_MONOTONIC,&end);
        assert((end.tv_sec-start.tv_sec)*1000+(end.tv_nsec-start.tv_nsec)/1000000<1000);
        assert(!strcmp(text,"recognized") && s_voice.state==VOICE_IDLE);
        close(peer);unlink(addr.sun_path);
    }
    puts("PASS: nonblocking capture, stop joins before close, ASR finalize and repeat sessions");
}
'''
with tempfile.TemporaryDirectory(prefix='qiji-capture-') as folder:
    file = Path(folder)/'test.c'
    exe = Path(folder)/'test'
    file.write_text(code)
    subprocess.run(['cc','-Wall','-Wextra','-Werror','-pthread',str(file),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=10)
