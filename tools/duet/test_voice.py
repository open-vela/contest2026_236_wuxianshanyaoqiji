import io
import json
import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer
from voice import VoiceSession, read_chunked, MAX_PCM
from server import Handler, Coordinator, Provider


class FakeProvider:
    demo = text_only = False
    def transcribe(self, pcm):
        assert len(pcm) >= 8000
        return '今天想聊聊旅行'
    def respond(self, text, history):
        return '可以呀，你更喜欢海边还是山里的风景？'
    def solo_audio(self, text): return b'\x01\x00' * 2400, 24000


class VoiceTests(unittest.TestCase):
    def setUp(self): self.v = VoiceSession(FakeProvider(), lambda: None)
    def upload(self):
        ident = self.v.start()['id']; self.v.claim_upload(ident)
        self.v.submit(ident, b'\x01\x00' * 4000)
        self.v.worker.join(2)
        return ident

    def test_complete_only_after_playback(self):
        ident = self.upload()
        self.assertEqual(self.v.snapshot(ident)['state'], 'ready')
        self.assertEqual(self.v.history, [])
        self.assertEqual(len(self.v.audio(ident)), 4800)
        self.v.acknowledge(ident, True)
        self.assertEqual(len(self.v.history), 2)
        self.assertEqual(self.v.state, 'complete')
        self.assertEqual(self.v.pcm, b'')

    def test_failed_playback_not_in_history(self):
        ident = self.upload(); self.v.acknowledge(ident, False)
        self.assertEqual(self.v.history, [])
        self.assertEqual(self.v.state, 'error')

    def test_cancel_during_asr_discards_late_result(self):
        started, finish = threading.Event(), threading.Event()
        def asr(pcm): started.set(); finish.wait(2); return '迟到的识别'
        def forbidden(*args): raise AssertionError('Later cloud stages must not run')
        self.v.provider.transcribe = asr; self.v.provider.respond = forbidden
        ident = self.v.start()['id']; self.v.claim_upload(ident)
        self.v.submit(ident, b'\0' * 8000)
        self.assertTrue(started.wait(1)); self.v.cancel(ident)
        with self.assertRaises(ValueError): self.v.start()
        finish.set(); self.v.worker.join(2)
        self.assertEqual(self.v.state, 'cancelled')
        self.assertEqual(self.v.pcm, b'')

    def test_upload_bounds_stale_and_repeated(self):
        ident = self.v.start()['id']; self.v.claim_upload(ident)
        with self.assertRaises(ValueError): self.v.claim_upload(ident)
        for pcm in [b'', b'\0' * 7999, b'\0' * (MAX_PCM + 2)]:
            with self.assertRaises(ValueError): self.v.submit(ident, pcm)
        self.v.cancel(ident); newer = self.v.start()['id']
        with self.assertRaises(ValueError): self.v.claim_upload(ident)
        self.assertNotEqual(ident, newer)

    def test_timeout_and_demo_have_no_fake_reply(self):
        ident = self.v.start()['id']; self.v.deadline = -1
        self.assertEqual(self.v.snapshot(ident)['state'], 'error')
        self.v.provider.demo = True
        with self.assertRaises(ValueError): self.v.start()

    def test_chunk_framing(self):
        self.assertEqual(read_chunked(io.BytesIO(b'2\r\nab\r\n4\r\ncdef\r\n0\r\n\r\n'), lambda: None), b'abcdef')
        for bad in [b'2\r\na', b'1\r\na\r\n0\r\n\r\n', b'-2\r\n', b'1002\r\n', b'x\r\n', b'0\r\nX: a\r\n']:
            with self.assertRaises(ValueError): read_chunked(io.BytesIO(bad), lambda: None)
        with self.assertRaises(ValueError): read_chunked(io.BytesIO(b'4\r\nabcd\r\n'), lambda: None, limit=2)


class VoiceHTTPTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.token = 'test-token'
        self.server.coordinator = Coordinator(Provider(demo=True))
        self.server.voice = VoiceSession(FakeProvider(), self.server.coordinator.stop)
        self.thread = threading.Thread(target=self.server.serve_forever); self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        conn.request(method, path, body, headers or {'Authorization': 'Bearer test-token'})
        r = conn.getresponse(); result = r.status, r.read(); conn.close(); return result

    def test_real_chunked_upload_and_audio(self):
        status, raw = self.request('POST', '/v1/voice/start', '{}')
        self.assertEqual(status, 200); ident = json.loads(raw)['id']
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        conn.request('POST', '/v1/voice/upload/' + ident,
                     iter([b'\x01\x00' * 512] * 10),
                     {'Authorization': 'Bearer test-token', 'Content-Type': 'application/octet-stream'}, encode_chunked=True)
        r = conn.getresponse(); self.assertEqual(r.status, 200); r.read(); conn.close()
        self.server.voice.worker.join(2)
        status, raw = self.request('GET', '/v1/voice/' + ident)
        data = json.loads(raw); self.assertEqual(data['state'], 'ready')
        status, pcm = self.request('GET', data['audio']); self.assertEqual(len(pcm), 4800)
        status, _ = self.request('POST', '/v1/voice/ack/' + ident, '{"ok":true}')
        self.assertEqual(status, 200)
        self.assertEqual(self.server.voice.state, 'complete')
        self.assertEqual(self.server.coordinator.state, 'stopped')

    def test_auth_and_partial_upload(self):
        self.assertEqual(self.request('POST', '/v1/voice/start', '{}', {'Authorization': 'wrong'})[0], 401)
        _, raw = self.request('POST', '/v1/voice/start', '{}'); ident = json.loads(raw)['id']
        status, _ = self.request('POST', '/v1/voice/upload/' + ident,
                                b'2\r\nab\r\n0\r\n\r\n', {'Authorization': 'Bearer test-token', 'Transfer-Encoding': 'chunked'})
        self.assertEqual(status, 400)
        self.assertEqual(self.server.voice.state, 'error')


if __name__ == '__main__': unittest.main()
