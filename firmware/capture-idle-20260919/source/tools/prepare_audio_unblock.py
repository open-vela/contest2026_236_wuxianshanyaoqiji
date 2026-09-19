"""Fix the observed Gemini PCM format mismatch and unbounded playback waits."""
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
project = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, str(project/'tools/prepare_aliyun_tts.py'), str(root)], check=True)
p = root/'packages/ai_agent/src/voice/audio_playback.c'
s = p.read_text()
if 'qiji_write_pcm' not in s:
    s = s.replace('#include <time.h>', '#include <time.h>\n#include <stdint.h>')
    s = s.replace('    unsigned int sample_rate;', '    unsigned int sample_rate;\n    unsigned int upsample;\n    int previous_valid;\n    int16_t previous;')
    s = s.replace('    (void)dev_path;', '''    (void)dev_path;
    /* The official minimal hardware graph is fixed at 48 kHz stereo.
     * Its volume filter cannot change rate/channel count. Convert before
     * sending PCM so every link agrees; preserve state across cloud chunks. */
    if ((sample_rate != 24000 && sample_rate != 16000) ||
        channels != 1 || bits_per_sample != 16) return NULL;
    unsigned int upsample = 48000 / sample_rate;
    sample_rate = 48000;
    channels = 2;''', 1)
    s = s.replace('    pb->sample_rate = sample_rate;', '    pb->sample_rate = sample_rate;\n    pb->upsample = upsample;')
    a = s.index('int audio_playback_write(')
    b = s.index('void audio_playback_stop(', a)
    s = s[:a] + '''static long long qiji_playback_ms(void)
{
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static int qiji_write_pcm(audio_playback_t *pb, const void *buf, size_t len)
{
    size_t done = 0;
    long long deadline = qiji_playback_ms() + 5000;
    while (done < len) {
        if (atomic_load(&pb->stopped)) return -ECANCELED;
        if (atomic_load(&pb->error)) return atomic_load(&pb->error);
        if (qiji_playback_ms() >= deadline) return -ETIMEDOUT;
        ssize_t n = media_player_write_data(pb->player,
            (const unsigned char *)buf + done, len - done);
        if (n == -EAGAIN || n == -EWOULDBLOCK || n == -EINTR) {
            usleep(1000);
            continue;
        }
        if (n <= 0) return n < 0 ? (int)n : -EIO;
        done += n;
        pb->total_written += n;
    }
    return 0;
}

int audio_playback_write(audio_playback_t *pb, const void *buf, size_t len)
{
    if (!pb || !pb->player || !buf || !len || len % 2) return -EINVAL;
    const unsigned char *src = buf;
    int16_t output[768];
    size_t offset = 0;
    while (offset < len) {
        size_t count = 0;
        while (offset < len && count + pb->upsample * 2 <= 768) {
            int16_t sample;
            memcpy(&sample, src + offset, sizeof(sample));
            offset += 2;
            if (!pb->previous_valid) {
                pb->previous = sample;
                pb->previous_valid = 1;
            }
            for (unsigned int j = 1; j <= pb->upsample; j++) {
                int32_t value = pb->previous +
                    ((int32_t)sample - pb->previous) * (int32_t)j / (int32_t)pb->upsample;
                output[count++] = (int16_t)value;
                output[count++] = (int16_t)value;
            }
            pb->previous = sample;
        }
        int ret = qiji_write_pcm(pb, output, count * sizeof(*output));
        if (ret) { atomic_store(&pb->error, ret); return ret; }
    }
    return (int)len;
}

''' + s[b:]
    s = s.replace('''        pb->stopped = 1;
        if (pb->player) {
            media_player_stop(pb->player);
        }''', '''        /* Called while holding the voice state lock: never perform IPC here.
         * The writer observes this flag after its bounded socket operation. */
        atomic_store(&pb->stopped, 1);''')
    p.write_text(s)



p = root/'packages/ai_agent/src/voice/voice_channel.c'
s = p.read_text()
if 'qiji_lock_speech' not in s:
    helper = '''/* A stalled speaker must not leave PTT on "opening microphone" forever. */
static int qiji_lock_speech(void)
{
    struct timespec start, now;
    clock_gettime(CLOCK_MONOTONIC, &start);
    for (;;) {
        int ret = pthread_mutex_trylock(&s_voice.speak_lock);
        if (!ret) return 0;
        if (ret != EBUSY) return -ret;
        clock_gettime(CLOCK_MONOTONIC, &now);
        if ((now.tv_sec - start.tv_sec) * 1000 +
            (now.tv_nsec - start.tv_nsec) / 1000000 >= 5000) return -ETIMEDOUT;
        usleep(10000);
    }
}

'''
    s = s.replace('int voice_channel_start(void)', helper+'int voice_channel_start(void)', 1)
    s = s.replace('pthread_mutex_lock(&s_voice.speak_lock);',
                  'int lock_ret = qiji_lock_speech();\n        if (lock_ret) return lock_ret;')
    # Keep the playback registered through drain, so PTT can cancel it.
    finish = '''    extern int qiji_audio_playback_finish(audio_playback_t *);
    if (!ret) ret = qiji_audio_playback_finish(pb);
'''
    if s.count(finish) != 1: raise RuntimeError('Unexpected TTS drain site')
    s = s.replace(finish, '')
    s = s.replace('    /* Unregister active playback */', finish+'\n    /* Unregister active playback */')
    p.write_text(s)

p = root/'frameworks/multimedia/media/client/media_graph.c'
s = p.read_text()
if 'Qiji bounded PCM' not in s:
    s = '#include <poll.h>\n#include <sys/time.h>\n'+s
    old = '    priv->socket = accept4(priv->socket_fd, NULL, NULL, SOCK_CLOEXEC);'
    s = s.replace(old, '''#ifdef CONFIG_GEMINI_CHAT_MINIMAL
    /* Qiji bounded PCM connection establishment. */
    struct pollfd waitfd = { .fd = priv->socket_fd, .events = POLLIN };
    int ready = poll(&waitfd, 1, 5000);
    if (ready <= 0) return ready ? -errno : -ETIMEDOUT;
#endif
'''+old)
    needle = '    return 0;\n}\n\nstatic ssize_t media_process_data'
    if s.count(needle) != 1: raise RuntimeError('Unexpected media accept implementation')
    s = s.replace(needle, '''#ifdef CONFIG_GEMINI_CHAT_MINIMAL
    struct timeval timeout = { .tv_sec = 0, .tv_usec = 250000 };
    if (setsockopt(priv->socket, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout)) < 0) {
        int saved = errno;
        close(priv->socket);
        priv->socket = 0;
        return -saved;
    }
#endif
'''+needle)
    # A short successful send must not close the stream and discard its count.
    s = s.replace('        if (ret == len)\n            goto out;', '        if (ret > 0)\n            goto out;')
    p.write_text(s)

p = root/'frameworks/multimedia/media/client/media_proxy.c'
s = p.read_text()
if 'Qiji bounded control' not in s:
    s = '#include <sys/time.h>\n'+s
    needle = '    pthread_mutex_init(&priv->mutex, NULL);'
    if s.count(needle) != 1: raise RuntimeError('Unexpected proxy initialization')
    s = s.replace(needle, '''#ifdef CONFIG_GEMINI_CHAT_MINIMAL
    /* Qiji bounded control replies: dead media graph cannot pin UI workers. */
    struct timeval timeout = { .tv_sec = 5, .tv_usec = 0 };
    if (setsockopt(priv->fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) < 0 ||
        setsockopt(priv->fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout)) < 0)
        goto connect_error;
#endif
'''+needle)
    p.write_text(s)
print('Prepared 48 kHz stereo playback, cancellable PCM writes and bounded speech lock')

# A failed control exchange cannot be reused: a late reply would be mistaken
# for the next command's response.
p = root/'frameworks/multimedia/media/client/media_proxy.c'
s = p.read_text()
if 'Qiji discard incomplete control exchange' not in s:
    start = s.index('int media_proxy_send_with_ack(')
    end = s.index('int media_proxy_set_event_cb(', start)
    part = s[start:end]
    part = part.replace('out:\n    pthread_mutex_unlock', '''out:
#ifdef CONFIG_GEMINI_CHAT_MINIMAL
    /* Qiji discard incomplete control exchange. */
    if (ret < 0) shutdown(priv->fd, SHUT_RDWR);
#endif
    pthread_mutex_unlock''')
    s = s[:start]+part+s[end:]
    p.write_text(s)

# Do not free an event cookie if the framework failed to release its player.
# Keep at most one quarantined player and refuse another until it can close.
p = root/'packages/ai_agent/src/voice/audio_playback.c'
s = p.read_text()
if 'quarantined player' not in s:
    s = s.replace('''        media_player_close(s_active_player, 0);
        s_active_player = NULL;''', '''        if (media_player_close(s_active_player, 0) < 0) {
            syslog(LOG_ERR, "[%s] quarantined player requires media restart\\n", TAG);
            return NULL;
        }
        s_active_player = NULL;''')
    s = s.replace('''        media_player_close(pb->player, 0);
        s_active_player = NULL;''', '''        if (media_player_close(pb->player, 0) < 0) {
            /* Callback may still reference pb; preserve its lifetime. */
            syslog(LOG_ERR, "[%s] player close failed; cookie retained\\n", TAG);
            return;
        }
        s_active_player = NULL;''')
    p.write_text(s)

# NuttX local sockets are FIFO-backed. Closing a socket in another thread
# need not wake an existing FIFO read. Use nonblocking PCM I/O and join the
# reader before closing its descriptor instead of relying on cross-thread close.
p = root/'frameworks/multimedia/media/client/media_graph.c'
s = p.read_text()
old = '    priv->socket = accept4(priv->socket_fd, NULL, NULL, SOCK_CLOEXEC);'
if 'Qiji nonblocking PCM' not in s:
    if s.count(old) != 1: raise RuntimeError('Unexpected PCM accept')
    s = s.replace(old, '''#ifdef CONFIG_GEMINI_CHAT_MINIMAL
    /* Qiji nonblocking PCM: the recording loop checks STOPPING between reads. */
    priv->socket = accept4(priv->socket_fd, NULL, NULL, SOCK_CLOEXEC | SOCK_NONBLOCK);
#else
'''+old+'''
#endif''')
    p.write_text(s)
p = root/'packages/ai_agent/src/voice/voice_channel.c'
s = p.read_text()
if 'Qiji join the nonblocking reader' not in s:
    old = '''    audio_capture_abort(s_voice.cap);

    /* Wait for recording thread to finish */
    pthread_join(s_voice.rec_thread, NULL);'''
    if s.count(old) != 2: raise RuntimeError('Unexpected capture stop paths')
    s = s.replace(old, '''    /* Qiji join the nonblocking reader before closing its PCM socket. */
    pthread_join(s_voice.rec_thread, NULL);
    audio_capture_abort(s_voice.cap);''')
    s = s.replace('''        audio_capture_abort(s_voice.cap);
        pthread_join(s_voice.rec_thread, NULL);''', '''        pthread_join(s_voice.rec_thread, NULL);
        audio_capture_abort(s_voice.cap);''')
    start = s.index('int voice_channel_stop_with_text(')
    part = s[start:]
    part = part.replace("    text_out[0] = '\\0';", """    text_out[0] = '\\0';
    struct timespec stop_start, stop_done;
    clock_gettime(CLOCK_MONOTONIC, &stop_start);
    syslog(LOG_INFO, "[%s] capture stop requested\\n", TAG);""", 1)
    part = part.replace('    /* Close capture device */', '''    clock_gettime(CLOCK_MONOTONIC, &stop_done);
    syslog(LOG_INFO, "[%s] capture stopped: %ldms\\n", TAG,
        (stop_done.tv_sec-stop_start.tv_sec)*1000 +
        (stop_done.tv_nsec-stop_start.tv_nsec)/1000000);

    /* Close capture device */''', 1)
    part = part.replace('''        int ret = voice_asr_stream_finish(stream, text,
            sizeof(text));''', '''        struct timespec begin, end;
        clock_gettime(CLOCK_MONOTONIC, &begin);
        int ret = voice_asr_stream_finish(stream, text, sizeof(text));
        clock_gettime(CLOCK_MONOTONIC, &end);
        syslog(LOG_INFO, "[%s] ASR finalize: %ldms rc=%d\\n", TAG,
            (end.tv_sec-begin.tv_sec)*1000+(end.tv_nsec-begin.tv_nsec)/1000000, ret);''', 1)
    s = s[:start]+part
    p.write_text(s)
print('Prepared nonblocking capture and close only after reader exit')
