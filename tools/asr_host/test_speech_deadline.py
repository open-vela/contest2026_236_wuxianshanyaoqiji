"""Compile the actual patched voice lock helper and verify lock contention."""
from pathlib import Path
import subprocess
import sys
import tempfile

source = (Path(sys.argv[1])/'packages/ai_agent/src/voice/voice_channel.c').read_text()
start = source.index('static int qiji_lock_speech(void)')
end = source.index('int voice_channel_start(void)', start)
helper = source[start:end]
code = '''#include <pthread.h>
#include <errno.h>
#include <time.h>
#include <unistd.h>
#include <assert.h>
#include <stdio.h>
static struct { pthread_mutex_t speak_lock; } s_voice = { PTHREAD_MUTEX_INITIALIZER };
'''+helper+'''
int main(void) {
    struct timespec start,end;
    assert(!qiji_lock_speech());
    clock_gettime(CLOCK_MONOTONIC,&start);
    assert(qiji_lock_speech()==-ETIMEDOUT);
    clock_gettime(CLOCK_MONOTONIC,&end);
    long ms=(end.tv_sec-start.tv_sec)*1000+(end.tv_nsec-start.tv_nsec)/1000000;
    assert(ms>=4900 && ms<6500);
    pthread_mutex_unlock(&s_voice.speak_lock);
    assert(!qiji_lock_speech());
    pthread_mutex_unlock(&s_voice.speak_lock);
    puts("PASS: actual speech lock returns timeout under contention and recovers after release");
}
'''
with tempfile.TemporaryDirectory(prefix='qiji-lock-') as folder:
    file = Path(folder)/'test.c'
    exe = Path(folder)/'test'
    file.write_text(code)
    subprocess.run(['cc','-Wall','-Wextra','-Werror','-pthread',str(file),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=10)
