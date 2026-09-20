"""Manually test real cloud/HTTP with synthetic speech; stops any active duet.

Uses ignored local credentials. Does not record or play physical device audio.
"""
import array
import http.client
import json
import os
from pathlib import Path
import time

from server import Provider


def main():
    root = Path(__file__).resolve().parents[2]
    private = root / 'artifacts/private-ai-logs/duet-runtime'
    for key, value in json.loads((private / 'cloud.json').read_text()).items():
        os.environ[key] = value
    token = json.loads((private / 'config.json').read_text())['token']

    def request(method, path, body=None, chunked=False):
        conn = http.client.HTTPConnection('127.0.0.1', 8765, timeout=10)
        try:
            conn.request(method, path, body, {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/octet-stream' if chunked else 'application/json',
            }, encode_chunked=chunked)
            response = conn.getresponse()
            data = response.read()
            if response.status != 200:
                raise RuntimeError('HTTP ' + str(response.status))
            return data
        finally:
            conn.close()

    pcm, rate = Provider().solo_audio('你好小澄，今天我想放松一下，你有什么建议？')
    if rate != 24000:
        raise ValueError('Expected 24 kHz test speech')
    samples, down = array.array('h', pcm), array.array('h')
    for i in range(0, len(samples) - 2, 3):
        down.extend((samples[i], (samples[i + 1] + samples[i + 2]) // 2))
    payload = down.tobytes()
    ident = json.loads(request('POST', '/v1/voice/start', '{}'))['id']
    started = time.monotonic()
    try:
        request('POST', '/v1/voice/upload/' + ident,
                iter(payload[i:i + 1024] for i in range(0, len(payload), 1024)), True)
        stages = []
        while time.monotonic() - started < 115:
            state = json.loads(request('GET', '/v1/voice/' + ident))
            if not stages or stages[-1]['state'] != state['state']:
                stages.append({'state': state['state'], 'seconds': round(time.monotonic() - started, 2)})
                print(stages[-1], flush=True)
            if state['state'] == 'ready':
                break
            if state['state'] in ('error', 'cancelled'):
                raise RuntimeError(state['error'])
            time.sleep(.25)
        else:
            raise TimeoutError('Voice pipeline deadline')
        reply = request('GET', state['audio'])
        if len(reply) < 8000 or len(reply) % 2 or state['rate'] != 24000:
            raise ValueError('Invalid reply audio')
        report = {
            'status': 'PASS (real HTTP and cloud; synthetic input; no physical playback)',
            'upload_bytes': len(payload), 'reply_bytes': len(reply), 'rate': state['rate'],
            'transcript': state['transcript'], 'reply': state['text'], 'stages': stages,
            'device_microphone': 'NOT RUN', 'device_playback': 'NOT RUN',
        }
        output = root / 'artifacts/passport-device' / (time.strftime('%Y%m%d') + '-voice-http-cloud-test.json')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('HTTP cloud pipeline PASS; reply bytes:', len(reply),
              'elapsed:', round(time.monotonic() - started, 2), flush=True)
    finally:
        # No playback ACK: this synthetic exchange must not enter user history.
        request('POST', '/v1/voice/cancel/' + ident, '{}')


if __name__ == '__main__':
    main()
