"""Cumulative v0.3 UI/audio hooks. --ui-only permits compile checks before art generation."""
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
project = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable,str(project/'tools/prepare_enter_ui.py'),str(root)],check=True)
p=root/'packages/ai_agent/src/voice/voice_channel.c'
s=p.read_text()
if 'qiji_chat_audio_chunk' not in s:
    old='        audio_playback_write(pb, pcm_data, pcm_len);'
    if s.count(old)!=1:raise RuntimeError('Unexpected streaming PCM callback')
    s=s.replace(old,'''        int accepted = audio_playback_write(pb, pcm_data, pcm_len);
#ifdef CONFIG_GEMINI_CHAT_MINIMAL
        extern void qiji_chat_audio_chunk(const unsigned char *pcm, size_t bytes);
        if (accepted > 0) qiji_chat_audio_chunk(pcm_data, (size_t)accepted);
#else
        (void)accepted;
#endif''')
    old='    struct timespec tts_net;'
    if s.count(old)!=1:raise RuntimeError('Unexpected streaming completion site')
    s=s.replace(old,'''#ifdef CONFIG_GEMINI_CHAT_MINIMAL
    extern void qiji_chat_audio_network_done(void);
    qiji_chat_audio_network_done();
#endif

'''+old)
    p.write_text(s)
# Upgrade the previously installed byte-count-only callback, idempotently.
s = p.read_text()
old = '''        extern void qiji_chat_audio_chunk(size_t bytes);
        if (accepted > 0) qiji_chat_audio_chunk((size_t)accepted);'''
if old in s:
    s = s.replace(old, '''        extern void qiji_chat_audio_chunk(const unsigned char *pcm, size_t bytes);
        if (accepted > 0) qiji_chat_audio_chunk(pcm_data, (size_t)accepted);''')
    p.write_text(s)
if 'qiji_chat_audio_chunk(pcm_data, (size_t)accepted)' not in s:
    raise RuntimeError('Missing accepted PCM envelope hook')
names=('idle','blink','listen','think','speak','happy','comfort','surprise')
source=project/'assets/kotone-v1/bin'
missing=[n for n in names if not (source/(n+'.bin')).is_file()]
if missing and '--ui-only' not in sys.argv:
    raise RuntimeError('Sprite set incomplete; no release allowed: '+','.join(missing))
dest=root/'vendor/allwinnertech/lichee/board/common/data/res/qiji/kotone'
dest.mkdir(parents=True,exist_ok=True)
for name in names:
    if (source/(name+'.bin')).is_file():shutil.copy2(source/(name+'.bin'),dest/(name+'.bin'))
print('Prepared sprite/scroll UI; incomplete art='+str(bool(missing)))
