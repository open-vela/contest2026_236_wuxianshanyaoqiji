import threading
import unittest
import json
import urllib.request
import urllib.error
from unittest.mock import patch
import os
from http.server import ThreadingHTTPServer
from server import Coordinator, Provider, Handler, bounded_text, PRIMARY_NAME


class Clock:
    def __init__(self): self.now = 0
    def __call__(self): return self.now


class Tests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.c = Coordinator(Provider(demo=True), self.clock)

    def connect(self):
        self.c.poll("qiji")
        self.c.poll("xiaocheng")

    def ack(self):
        seq = self.c.seq
        self.c.poll("qiji", seq)
        self.c.poll("xiaocheng", seq)

    def test_requires_both_and_ready(self):
        self.c.poll("qiji")
        self.c.poll("xiaocheng", ready=False)
        self.assertEqual(self.c.state, "waiting")
        self.c.poll("xiaocheng")
        self.assertEqual(self.c.state, "generating")

    def test_six_turns_then_summary_once(self):
        self.connect()
        for i in range(6):
            self.c.tick()
            self.assertEqual(self.c.pending["qiji"]["speaker"], ("qiji", "xiaocheng")[i % 2])
            self.ack()
        self.assertEqual(len(self.c.transcript), 6)
        self.c.tick()
        self.assertEqual(self.c.pending["qiji"]["kind"], "summary")
        self.ack()
        self.assertEqual(self.c.state, "complete")
        self.assertTrue(self.c.summary)
        self.connect()
        self.c.tick()
        self.assertEqual(self.c.state, "complete")

    def test_duplicate_stale_and_future_ack(self):
        self.connect(); self.c.tick()
        seq = self.c.seq
        self.c.poll("qiji", seq)
        self.c.poll("qiji", seq)
        self.c.poll("xiaocheng", seq + 1)
        self.assertEqual(len(self.c.transcript), 0)
        self.c.poll("xiaocheng", seq)
        self.c.tick()
        self.c.poll("xiaocheng", seq)
        self.assertEqual(len(self.c.transcript), 1)
        self.assertEqual(self.c.state, "speaking")

    def test_disconnect_no_autorestart(self):
        self.connect(); self.c.tick()
        self.clock.now = 11
        self.c.tick()
        self.assertEqual(self.c.state, "stopped")
        self.connect()
        self.assertEqual(self.c.state, "stopped")
        self.assertTrue(self.c.start())

    def test_failed_playback_is_not_completed_conversation(self):
        self.connect(); self.c.tick()
        self.c.poll("xiaocheng", self.c.seq, "error")
        self.assertEqual(self.c.state, "stopped")
        self.assertEqual(self.c.transcript, [])

    def test_stop_invalidates_inflight_generation(self):
        entered, finish = threading.Event(), threading.Event()
        def generate(*args):
            entered.set(); finish.wait(2); return "迟到的回复"
        self.c.provider.generate = generate
        self.connect()
        worker = threading.Thread(target=self.c.tick)
        worker.start(); self.assertTrue(entered.wait(2))
        self.c.stop(); finish.set(); worker.join(2)
        self.assertEqual(self.c.pending, {})
        self.assertEqual(self.c.state, "stopped")

    def test_no_script_fallback_on_cloud_failure(self):
        import contextlib
        import io
        def fail(*args): raise RuntimeError("secret response")
        self.c.provider.generate = fail
        diagnostics = io.StringIO()
        with contextlib.redirect_stderr(diagnostics), contextlib.redirect_stdout(diagnostics):
            self.connect(); self.c.tick()
        self.assertEqual(self.c.state, "stopped")
        self.assertNotIn("secret", self.c.error)
        self.assertNotIn("secret", diagnostics.getvalue())
        self.assertFalse(self.c.summary)

    def test_playback_deadline_with_heartbeats(self):
        self.connect(); self.c.tick()
        self.clock.now = 81
        self.connect(); self.c.tick()
        self.assertEqual(self.c.state, "stopped")

    def test_text_contract(self):
        self.assertEqual(bounded_text("小澄，今天聊什么？"), "小澄，今天聊什么？")
        for value in ("", "🙂", "a" * 181):
            with self.assertRaises(ValueError): bounded_text(value)

    def test_live_roles_keep_existing_primary_persona(self):
        env = {"DUET_LLM_URL": "https://example.invalid/chat/completions", "DUET_LLM_MODEL": "test", "DUET_LLM_KEY": "not-a-real-key"}
        with patch.dict(os.environ, env), patch("server.request_json", return_value={"choices": [{"message": {"content": "我们可以先听一首歌。"}}]}) as request:
            provider = Provider(text_only=True)
            transcript = [{"speaker": PRIMARY_NAME, "text": "想听歌吗？"}]
            provider.generate("xiaocheng", "休息", transcript)
            sent = request.call_args.args[1]["messages"]
            self.assertIn("你是小澄", sent[0]["content"])
            self.assertIn(PRIMARY_NAME, sent[0]["content"])
            self.assertIn("想听歌吗", sent[1]["content"])
            provider.generate("qiji", "休息", transcript)
            self.assertIn(PRIMARY_NAME, request.call_args.args[1]["messages"][0]["content"])

    def test_duet_uses_working_solo_tts_and_propagates_errors(self):
        env = {'DUET_LLM_URL':'https://example.invalid/chat', 'DUET_LLM_MODEL':'test',
               'DUET_LLM_KEY':'test-key', 'DASHSCOPE_API_KEY':'voice-key'}
        with patch.dict(os.environ, env), patch('gemini_bridge.synthesize',
                return_value=(b'\x01\x00' * 20, 24000)) as speech:
            provider = Provider()
            self.assertEqual(provider.audio('小澄接着说话'), (b'\x01\x00' * 20, 24000))
            speech.assert_called_once_with('小澄接着说话', 'voice-key')
            speech.side_effect = RuntimeError('TTS unavailable')
            with self.assertRaises(RuntimeError): provider.audio('不能伪造语音')
            speech.reset_mock()
            self.assertEqual(Provider(demo=True).audio('演示'), (b'', 24000))
            self.assertEqual(Provider(text_only=True).audio('文字'), (b'', 24000))
            speech.assert_not_called()


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.token = "test-local-pairing-token"
        self.server.coordinator = Coordinator(Provider(demo=True))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def request(self, path, data=None, token="test-local-pairing-token"):
        req = urllib.request.Request(self.url + path,
            json.dumps(data).encode() if data is not None else None,
            {"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as r: return json.load(r)

    def test_real_http_encounter(self):
        self.request("/v1/poll", {"device": "qiji"})
        self.request("/v1/poll", {"device": "xiaocheng"})
        for _ in range(7):
            self.server.coordinator.tick()
            for device in ("qiji", "xiaocheng"):
                command = self.request("/v1/poll", {"device": device})
                self.assertIn("text", command)
                self.request("/v1/poll", {"device": device, "ack": command["seq"]})
        state = self.request("/v1/state")
        self.assertEqual(state["state"], "complete")
        self.assertEqual(len(state["transcript"]), 6)
        self.assertTrue(state["summary"])
        self.assertTrue(state["demo"])

    def test_auth_and_invalid_device(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.request("/v1/state", token="wrong")
        self.assertEqual(e.exception.code, 401)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.request("/v1/poll", {"device": "someone_else"})
        self.assertEqual(e.exception.code, 400)

    def test_stop_does_not_invent_summary(self):
        self.request("/v1/poll", {"device": "qiji"})
        self.request("/v1/poll", {"device": "xiaocheng"})
        self.server.coordinator.tick()
        self.request("/v1/stop", {})
        state = self.request("/v1/state")
        self.assertEqual(state["state"], "stopped")
        self.assertEqual(state["summary"], "")


if __name__ == "__main__": unittest.main()
