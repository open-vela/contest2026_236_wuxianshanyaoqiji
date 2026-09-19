"""Apply the minimal Aliyun dispatch patch to the pinned official source tree."""
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
project = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, str(project / 'tools/prepare_wifi_doubao.py'), str(root)], check=True)
agent = root / 'packages/ai_agent'
p = agent / 'src/voice/voice_asr.c'
text = p.read_text()
if 'qiji_aliyun_open' not in text:
    text = text.replace('/* ── Streaming ASR (delegates to volc_asr streaming API) ─────── */', '''/* Qiji: bind each live stream to the backend selected at open time. */
extern void *qiji_aliyun_open(void);
extern int qiji_aliyun_send(void *, const unsigned char *, size_t);
extern int qiji_aliyun_finish(void *, char *, size_t);
extern void qiji_aliyun_abort(void *);
''')
    text = text.replace('    volc_asr_stream_t* inner;', '    void* inner;\n    int aliyun;')
    text = text.replace('    volc_asr_stream_t* inner = volc_asr_stream_open();', '''    int aliyun = !strcmp(s_active->name, "aliyun");
    if (!aliyun && strcmp(s_active->name, "volcengine")) return NULL;
    void* inner = aliyun ? qiji_aliyun_open() : (void*)volc_asr_stream_open();''')
    text = text.replace('        volc_asr_stream_abort(inner);', '        if (aliyun) qiji_aliyun_abort(inner);\n        else volc_asr_stream_abort(inner);')
    text = text.replace('    s->inner = inner;', '    s->inner = inner;\n    s->aliyun = aliyun;')
    text = text.replace('return volc_asr_stream_send(s->inner, pcm, len);', 'return s->aliyun ? qiji_aliyun_send(s->inner, pcm, len) : volc_asr_stream_send(s->inner, pcm, len);')
    text = text.replace('int ret = volc_asr_stream_finish(s->inner, text_out, text_cap);', 'int ret = s->aliyun ? qiji_aliyun_finish(s->inner, text_out, text_cap) : volc_asr_stream_finish(s->inner, text_out, text_cap);')
    text = text.replace('    volc_asr_stream_abort(s->inner);', '    if (s->aliyun) qiji_aliyun_abort(s->inner);\n    else volc_asr_stream_abort(s->inner);')
    if 'extern void *qiji_aliyun_open' not in text: raise RuntimeError('Unexpected upstream streaming wrapper')
    p.write_text(text)
p = agent / 'src/voice/voice_channel.c'
text = p.read_text()
if 'qiji_aliyun_register' not in text:
    text = text.replace('        volc_asr_register();', '        volc_asr_register();\n        extern void qiji_aliyun_register(void);\n        qiji_aliyun_register();')
    # Do not report an ASR network failure as successful empty recognition.
    before = '        return 0;\n    }\n\n    /* Batch fallback: synchronous ASR inline'
    after = '        return ret;\n    }\n\n    /* Batch fallback: synchronous ASR inline'
    if before not in text: raise RuntimeError('Unexpected stop_with_text implementation')
    text = text.replace(before, after)
    p.write_text(text)
print('Prepared Aliyun streaming dispatch and backend registration')
