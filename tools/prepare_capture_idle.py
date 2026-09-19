"""Close the official capture source when its downstream recording has ended."""
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
project = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, str(project/'tools/prepare_dialogue_reply.py'), str(root)], check=True)

p = root/'external/ffmpeg/ffmpeg/libavfilter/asrc_adevsrc.c'
s = p.read_text()
if 'Qiji stop capture on downstream EOF' not in s:
    old = '''    if (!ff_outlink_frame_wanted(link))
        return FFERROR_NOT_READY;

    ret = adevsrc_open(ctx);'''
    new = '''    /* Qiji stop capture on downstream EOF. Device-readable events force
     * frame_wanted_out even after the recorder unlinks. Without this check
     * the source keeps producing into an ended link throughout idle time.
     * The next recorder link resets status via audio negotiation. */
    if (ff_outlink_get_status(link)) {
        adevsrc_close(ctx);
        return FFERROR_NOT_READY;
    }

    if (!ff_outlink_frame_wanted(link))
        return FFERROR_NOT_READY;

    ret = adevsrc_open(ctx);'''
    if s.count(old) != 1:
        raise RuntimeError('Unexpected audio capture source activation')
    p.write_text(s.replace(old, new))

p = root/'packages/ai_agent/src/voice/voice_channel.c'
s = p.read_text()
if 'capture first PCM:' not in s:
    old = '    size_t total_bytes_read = 0;'
    new = '''    struct timespec capture_begin;
    clock_gettime(CLOCK_MONOTONIC, &capture_begin);
    size_t total_bytes_read = 0;'''
    if s.count(old) != 1:
        raise RuntimeError('Unexpected recording thread counters')
    s = s.replace(old, new)
    old = '        total_bytes_read += (size_t)n;'
    new = '''        if (!total_bytes_read) {
            struct timespec now;
            clock_gettime(CLOCK_MONOTONIC, &now);
            syslog(LOG_INFO, "[%s] capture first PCM: %ldms\\n", TAG,
                (now.tv_sec-capture_begin.tv_sec)*1000 +
                (now.tv_nsec-capture_begin.tv_nsec)/1000000);
        }
        total_bytes_read += (size_t)n;'''
    if s.count(old) != 1:
        raise RuntimeError('Unexpected recording thread data path')
    p.write_text(s.replace(old, new))

print('Prepared capture source EOF shutdown and first PCM latency log')
