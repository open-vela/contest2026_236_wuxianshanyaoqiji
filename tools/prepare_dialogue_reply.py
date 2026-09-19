"""Fix local one-shot reply dispatch and the official audio sink EOF lifecycle."""
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
project = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, str(project/'tools/prepare_audio_unblock.py'), str(root)], check=True)

p = root/'packages/ai_agent/src/core/agent_loop.c'
s = p.read_text()
if 'Qiji local client has a one-shot final reply callback' not in s:
    old = '''    if (strcmp(msg->channel, AGENT_CHAN_FEISHU) == 0
        || strcmp(msg->channel, AGENT_CHAN_VOICE) == 0'''
    new = '''    /* Qiji local client has a one-shot final reply callback.
     * A working phrase would consume it before the actual model answer. */
    if (strcmp(msg->channel, "local_client") == 0
        || strcmp(msg->channel, AGENT_CHAN_FEISHU) == 0
        || strcmp(msg->channel, AGENT_CHAN_VOICE) == 0'''
    if s.count(old) != 1:
        raise RuntimeError('Unexpected working-status dispatcher')
    p.write_text(s.replace(old, new))

p = root/'external/ffmpeg/ffmpeg/libavfilter/asink_adevsink.c'
s = p.read_text()
if 'Qiji acknowledge drained input before requesting another frame' not in s:
    old = '''    ff_inlink_request_frame(inlink);

    return ret;
}'''
    new = '''    /* Qiji acknowledge drained input before requesting another frame.
     * abufsrc unlink propagates EOF through the volume filter. Requesting
     * from that ended link asserts and terminates mediad. A subsequent
     * player link resets the link status in audio_set_format_config(). */
    int status;
    if (ff_inlink_acknowledge_status(inlink, &status, &pts)) {
        adevsink_stop(ctx);
        return status == AVERROR_EOF ? 0 : status;
    }

    ff_inlink_request_frame(inlink);

    return ret;
}'''
    if s.count(old) != 1:
        raise RuntimeError('Unexpected audio sink activation')
    p.write_text(s.replace(old, new))

print('Prepared final-only local replies and drained audio sink EOF handling')
