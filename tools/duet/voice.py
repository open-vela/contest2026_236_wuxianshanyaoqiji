"""Bounded single-user voice session; recording stays in memory on the host."""
import secrets
import threading
import time

MAX_PCM = 20 * 16000 * 2


class VoiceSession:
    def __init__(self, provider, stop_duet, clock=time.monotonic):
        self.provider, self.stop_duet, self.clock = provider, stop_duet, clock
        self.lock = threading.RLock()
        self.id = ''
        self.state, self.error = 'idle', ''
        self.transcript, self.reply, self.pcm = '', '', b''
        self.rate = 24000
        self.worker = None
        self.history = []
        self.deadline = 0

    def available(self):
        return not self.provider.demo and not self.provider.text_only

    def start(self):
        with self.lock:
            if not self.available():
                raise ValueError('Voice service requires live mode and cloud configuration')
            if self.worker and self.worker.is_alive():
                raise ValueError('Previous request is still finishing')
            if self.state in ('recording', 'uploading') and self.clock() < self.deadline:
                raise ValueError('A recording is already active')
            self.stop_duet()
            self.id = secrets.token_hex(8)
            self.state, self.error = 'recording', ''
            self.transcript, self.reply, self.pcm = '', '', b''
            self.deadline = self.clock() + 35
            return {'id': self.id, 'max_seconds': 20}

    def check(self, ident, states):
        if not ident or ident != self.id or self.state not in states or self.clock() > self.deadline:
            raise ValueError('Expired or invalid voice session')

    def claim_upload(self, ident):
        with self.lock:
            self.check(ident, ('recording',))
            self.state = 'uploading'

    def accepting(self, ident):
        with self.lock:
            self.check(ident, ('uploading',))

    def submit(self, ident, pcm):
        if not 8000 <= len(pcm) <= MAX_PCM or len(pcm) % 2:
            raise ValueError('Invalid recording length')
        with self.lock:
            self.check(ident, ('uploading',))
            self.state, self.deadline = 'recognizing', self.clock() + 120
            self.worker = threading.Thread(target=self.process, args=(ident, bytes(pcm)), daemon=True)
            self.worker.start()

    def process(self, ident, pcm):
        try:
            text = self.provider.transcribe(pcm)
            with self.lock:
                self.check(ident, ('recognizing',))
                self.transcript, self.state = text, 'thinking'
                history = list(self.history)
            reply = self.provider.respond(text, history)
            with self.lock:
                self.check(ident, ('thinking',))
                self.reply, self.state = reply, 'synthesizing'
            audio, rate = self.provider.solo_audio(reply)
            if not audio or len(audio) % 2 or rate not in (16000, 24000):
                raise ValueError('Invalid voice output')
            with self.lock:
                self.check(ident, ('synthesizing',))
                self.pcm, self.rate, self.state = audio, rate, 'ready'
                self.deadline = self.clock() + 90
        except Exception as exc:
            self.fail(ident, '语音处理失败：' + type(exc).__name__)

    def fail(self, ident, message):
        with self.lock:
            if ident == self.id and self.state not in ('cancelled', 'complete'):
                self.state, self.error, self.pcm = 'error', message, b''

    def cancel(self, ident):
        with self.lock:
            if ident == self.id:
                self.state, self.pcm = 'cancelled', b''

    def acknowledge(self, ident, ok):
        with self.lock:
            self.check(ident, ('ready',))
            if ok:
                self.history.extend([{'role': 'user', 'content': self.transcript},
                                     {'role': 'assistant', 'content': self.reply}])
                self.history = self.history[-12:]
                self.state = 'complete'
            else:
                self.state, self.error = 'error', '语音播放失败'
            self.pcm = b''

    def audio(self, ident):
        with self.lock:
            self.check(ident, ('ready',))
            return self.pcm

    def snapshot(self, ident):
        with self.lock:
            if ident != self.id:
                raise ValueError('Unknown voice session')
            if self.state not in ('idle', 'complete', 'cancelled', 'error') and self.clock() > self.deadline:
                self.state, self.error, self.pcm = 'error', '语音请求超时', b''
            return {'id': self.id, 'state': self.state, 'transcript': self.transcript,
                    'text': self.reply, 'error': self.error, 'rate': self.rate,
                    'audio': '/v1/voice/audio/' + self.id if self.state == 'ready' else ''}


def read_chunked(stream, accepting, limit=MAX_PCM):
    """Only PCM chunks <= 4096 bytes; strict framing and finite total size."""
    result = bytearray()
    while True:
        accepting()
        line = stream.readline(32)
        if not line.endswith(b'\r\n') or len(line) >= 32:
            raise ValueError('Invalid chunk header')
        size = int(line[:-2], 16)
        if size == 0:
            if stream.read(2) != b'\r\n':
                raise ValueError('Trailers not supported')
            return bytes(result)
        if size < 0 or size > 4096 or size % 2 or len(result) + size > limit:
            raise ValueError('Invalid PCM chunk')
        data = stream.read(size)
        if len(data) != size or stream.read(2) != b'\r\n':
            raise ValueError('Truncated PCM chunk')
        result.extend(data)
