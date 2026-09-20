"""Reuse Gemini's exact C ASR/TTS backend via the existing host executable."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def command():
    configured = os.environ.get('DUET_GEMINI_COMMAND')
    if configured:
        result = json.loads(configured)
        if not isinstance(result, list) or not result or not all(isinstance(x, str) for x in result):
            raise ValueError('DUET_GEMINI_COMMAND must be a JSON argument array')
        return result
    if os.name == 'nt':
        # WSL's DNS tunnel can stall a cold lookup. Bound both DNS retries and
        # the Linux process itself: killing wsl.exe alone can leave it running.
        return ['wsl', '-d', 'Ubuntu', '--exec', 'env',
                'RES_OPTIONS=timeout:2 attempts:2', 'timeout', '--kill-after=2s',
                '85s', '/home/vela/qiji-asr-host/qiji_asr_host']
    return [os.environ.get('DUET_GEMINI_HELPER', '/home/vela/qiji-asr-host/qiji_asr_host')]


def helper_path(path, args):
    path = Path(path).resolve()
    if os.name == 'nt' and Path(args[0]).stem.lower() == 'wsl':
        return '/mnt/' + path.drive[0].lower() + path.as_posix()[2:]
    return str(path)


def invoke(args, key, timeout=90):
    if not key or '\n' in key or '\r' in key:
        raise ValueError('Invalid voice key')
    proc = subprocess.run(args, input=(key + '\n').encode(), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if proc.returncode:
        # Backend logs may contain private transcription; do not surface them.
        raise RuntimeError('Gemini voice backend failed')
    return proc.stdout.decode('utf-8', errors='replace')


def transcribe(pcm, key):
    args = command()
    with tempfile.TemporaryDirectory(prefix='passport-voice-') as work:
        path = Path(work) / 'input.pcm'
        path.write_bytes(pcm)
        output = invoke(args + [helper_path(path, args)], key)
    prefix = 'Recognized: '
    text = next((line[len(prefix):].strip() for line in output.splitlines() if line.startswith(prefix)), '')
    if not text:
        raise ValueError('No speech recognized')
    return text


def synthesize(text, key):
    args = command()
    with tempfile.TemporaryDirectory(prefix='passport-voice-') as work:
        path = Path(work) / 'output.pcm'
        invoke(args + ['tts', text, helper_path(path, args)], key, timeout=150)
        pcm = path.read_bytes()
    if not pcm or len(pcm) % 2 or len(pcm) > 3_000_000:
        raise ValueError('Invalid synthesized PCM')
    return pcm, 24000
