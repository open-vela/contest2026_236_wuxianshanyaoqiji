"""Exercise the patched media data function with real socket backpressure."""
from pathlib import Path
import subprocess
import sys
import tempfile

source = (Path(sys.argv[1])/'frameworks/multimedia/media/client/media_graph.c').read_text()
start = source.index('static int media_accept_socket(')
end = source.index('static void media_event_cb(', start)
functions = source[start:end]
code = '''#define _GNU_SOURCE
#define CONFIG_GEMINI_CHAT_MINIMAL 1
#include <sys/socket.h>
#include <sys/time.h>
#include <poll.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <errno.h>
#include <unistd.h>
#include <stdlib.h>
#include <assert.h>
#include <stdio.h>
typedef struct { int socket, socket_fd; atomic_int refs; } MediaIOPriv;
static void media_release_cb(void *p) { atomic_fetch_sub(&((MediaIOPriv *)p)->refs,1); }
'''+functions+'''
int main(void) {
    int pair[2];assert(!socketpair(AF_UNIX,SOCK_STREAM,0,pair));
    int size=1024;
    assert(!setsockopt(pair[0],SOL_SOCKET,SO_SNDBUF,&size,sizeof(size)));
    struct timeval timeout={0,250000};
    assert(!setsockopt(pair[0],SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout)));
    MediaIOPriv priv={.socket=pair[0],.socket_fd=0,.refs=1};
    char *data=calloc(1,65536);assert(data);
    ssize_t n=media_process_data(&priv,true,data,65536);
    assert(n>0 && n<65536 && priv.socket==pair[0]);
    assert(media_process_data(&priv,true,data,65536)==-EAGAIN);
    assert(priv.socket==pair[0]);
    assert(recv(pair[1],data,65536,0)==n);
    assert(media_process_data(&priv,true,data,32)==32);
    assert(recv(pair[1],data,32,0)==32);
    assert(atomic_load(&priv.refs)==1);
    free(data);close(pair[0]);close(pair[1]);
    puts("PASS: actual media data function preserves partial sends, times out under backpressure and resumes");
}
'''
with tempfile.TemporaryDirectory(prefix='qiji-media-') as folder:
    file = Path(folder)/'test.c'
    exe = Path(folder)/'test'
    file.write_text(code)
    subprocess.run(['cc','-Wall','-Wextra','-Werror',str(file),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=10)
