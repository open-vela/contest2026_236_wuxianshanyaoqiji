"""Add Qwen Audio 3.1 TTS to the pinned official ASR/chat build."""
from pathlib import Path
import subprocess
import sys
root=Path(sys.argv[1]).resolve()
project=Path(__file__).resolve().parent.parent
subprocess.run([sys.executable,str(project/'tools/prepare_aliyun_asr.py'),str(root)],check=True)
p=root/'packages/ai_agent/src/voice/voice_tts.c'
text=p.read_text()
if 'qiji_aliyun_tts_stream' not in text:
    old='    return volc_tts_ws_synthesize_stream(text,'
    if text.count(old)!=1: raise RuntimeError('Unexpected upstream TTS dispatch')
    text=text.replace(old,'''    extern int qiji_aliyun_tts_stream(const char *, voice_tts_chunk_cb, void *);
    if (!strcmp(s_active->name, "aliyun"))
        return qiji_aliyun_tts_stream(text, cb, user_data);
    if (strcmp(s_active->name, "volcengine")) return -ENOTSUP;
    return volc_tts_ws_synthesize_stream(text,''')
    p.write_text(text)
p=root/'packages/ai_agent/src/voice/voice_channel.c'
text=p.read_text()
if 'qiji_aliyun_tts_register' not in text:
    old='        qiji_aliyun_register();'
    if text.count(old)!=1: raise RuntimeError('Missing ASR registration')
    text=text.replace(old,old+'\n        extern void qiji_aliyun_tts_register(void);\n        qiji_aliyun_tts_register();')
    p.write_text(text)
print('Prepared Qwen Audio 3.1 TTS registration and streaming dispatch')

# Finish buffered playback before closing the media player. Propagate write
# errors instead of reporting a successful spoken reply after a failed write.
p=root/'packages/ai_agent/src/voice/audio_playback.c'
text=p.read_text()
if 'qiji_audio_playback_finish' not in text:
    text=text.replace('#include <unistd.h>', '#include <unistd.h>\n#include <stdatomic.h>\n#include <time.h>')
    text=text.replace('    volatile int stopped;', '    atomic_int stopped;\n    atomic_int completed;\n    atomic_int error;\n    unsigned int sample_rate;')
    marker='audio_playback_t* audio_playback_open('
    callback='''static void qiji_playback_event(void *cookie, int event, int result, const char *extra)
{
    (void)extra;
    audio_playback_t *pb = cookie;
    if (result < 0) atomic_store(&pb->error, result);
    if (event == MEDIA_EVENT_COMPLETED) atomic_store(&pb->completed, 1);
}

'''
    text=text.replace(marker,callback+marker)
    marker='    pb->player = player;'
    text=text.replace(marker,'''    atomic_init(&pb->stopped, 0);
    atomic_init(&pb->completed, 0);
    atomic_init(&pb->error, 0);
    pb->sample_rate = sample_rate;
    if (media_player_set_event_callback(player, pb, qiji_playback_event) < 0) {
        media_player_close(player, 0);
        free(pb);
        return NULL;
    }
'''+marker)
    old='''    ssize_t n = media_player_write_data(pb->player, buf, len);
    if (n > 0) {
        pb->total_written += (size_t)n;
    }

    return (int)n;'''
    new='''    if (atomic_load(&pb->error)) return atomic_load(&pb->error);
    size_t written = 0;
    while (written < len) {
        if (atomic_load(&pb->stopped)) return -ECANCELED;
        ssize_t n = media_player_write_data(pb->player,
            (const unsigned char *)buf + written, len - written);
        if (n <= 0) {
            int error = n < 0 ? (int)n : -EIO;
            atomic_store(&pb->error, error);
            return error;
        }
        written += n;
        pb->total_written += n;
    }
    return (int)written;'''
    if old not in text: raise RuntimeError('Unexpected playback write implementation')
    text=text.replace(old,new)
    text+='''
/* EOF flushes decoder output; wait for audible completion, not network EOF. */
int qiji_audio_playback_finish(audio_playback_t *pb)
{
    if (!pb || !pb->player) return -EINVAL;
    media_player_close_socket(pb->player);
    struct timespec start, now;
    clock_gettime(CLOCK_MONOTONIC, &start);
    unsigned long limit = pb->total_written / (pb->sample_rate * pb->bytes_per_frame) + 10;
    if (limit > 130) limit = 130;
    for (;;) {
        if (atomic_load(&pb->error)) return atomic_load(&pb->error);
        if (atomic_load(&pb->stopped)) return -ECANCELED;
        if (atomic_load(&pb->completed)) return 0;
        clock_gettime(CLOCK_MONOTONIC, &now);
        if (now.tv_sec - start.tv_sec >= (long)limit) return -ETIMEDOUT;
        usleep(20000);
    }
}
'''
    p.write_text(text)
p=root/'packages/ai_agent/src/voice/voice_channel.c'
text=p.read_text()
if 'qiji_audio_playback_finish' not in text:
    old='''    audio_playback_close(pb);
    free(clean);'''
    if text.count(old)!=1: raise RuntimeError('Unexpected playback close site')
    text=text.replace(old,'''    extern int qiji_audio_playback_finish(audio_playback_t *);
    if (!ret) ret = qiji_audio_playback_finish(pb);
    audio_playback_close(pb);
    free(clean);''')
    p.write_text(text)
print('Prepared complete PCM writes and bounded playback drain')

# Official fix_gemini_s1.sh replaces graph/criteria but leaves the original
# settings.pfw referencing MuteMode and streams absent from the minimal graph.
# Keep a matching, parser-tested set for this application's PCM-only routes.
import shutil
media=root/'vendor/allwinnertech/boards/r528/r528s3-gemini-s1/src/etc/media'
graph=(media/'graph.conf').read_text()
for name in ('abufsink@acap','abufsrc@apb','volume@VolAcap','volume@VolApb'):
    if name not in graph: raise RuntimeError('Unexpected official audio graph: '+name)
for name in ('criteria.txt','settings.pfw'):
    shutil.copyfile(project/'app/gemini_chat_minimal/media'/name,media/name)

rc=root/'vendor/allwinnertech/boards/r528/r528s3-gemini-s1/src/etc/init.d/rcS.nsh'
text=rc.read_text()
text=text.replace('#ifdef CONFIG_SYSTEM_NTPC\nntpcstart &\n#endif',
    '#if defined(CONFIG_SYSTEM_NTPC) && !defined(CONFIG_GEMINI_CHAT_MINIMAL)\nntpcstart &\n#endif')
rc.write_text(text)
print('Prepared matching media policy and NTP only after Wi-Fi DHCP')

# Board.mk watches directory timestamps, not modified files inside them, and
# preprocessing rcS does not track its included rcS.nsh. Declare both inputs so
# incremental builds cannot silently retain the factory ROMFS configuration.
makefile=media.parent.parent/'Makefile'
text=makefile.read_text()
if '# Qiji ROMFS input dependencies' not in text:
    text+='''
# Qiji ROMFS input dependencies
ifeq ($(CONFIG_GEMINI_CHAT_MINIMAL),y)
etctmp/etc/init.d/rcS: $(wildcard etc/init.d/rcS.*)
etctmp.c: $(shell find etc/media -type f)
endif
'''
    makefile.write_text(text)
print('Prepared recursive media and rcS include build dependencies')
