"""Bounded Gemini diagnostics; --exercise explicitly records on the board."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


def redact(text):
    text = re.sub(r'\b(?:sk|ark)-[A-Za-z0-9-]+', '[KEY]', text)
    return re.sub(r'(?i)(passphrase|password|psk)(\s*[:=]\s*)[^,\s]+', r'\1\2[HIDDEN]', text)


def parse_result(text):
    m = re.search(r'busy=([01]) recording=([01])', text)
    if not m or 'status=' not in text or 'reply=' not in text:
        raise RuntimeError('Incomplete board state; no acceptance inferred')
    return {'busy': int(m[1]), 'recording': int(m[2]),
            'status': redact(text.split('status=', 1)[1].splitlines()[0]),
            'reply_present': bool(text.split('reply=', 1)[1].strip())}


class Board:
    def __init__(self, adb, serial):
        self.adb, self.serial = adb, serial

    def run(self, args, timeout=10, input=None):
        try:
            p = subprocess.run([self.adb, '-s', self.serial, *args], input=input,
                               capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('ADB timed out; device requires inspection') from exc
        raw = p.stdout+p.stderr
        try:
            out = raw.decode('utf-8')
        except UnicodeDecodeError:
            out = raw.decode('gb18030', errors='replace')
        out = redact(out)
        if p.returncode or re.search(r'device offline|device .*not found|Unknown command|command not found', out):
            raise RuntimeError(out.strip() or 'ADB failed without output')
        return out.replace('\r', '')

    def shell(self, command):
        return self.run(['shell', command])

    def state(self):
        return parse_result(self.shell('qiji_config result'))

    def await_state(self, recording, timeout):
        end = time.monotonic()+timeout
        while time.monotonic() < end:
            state = self.state()
            if not state['busy'] and state['recording'] == recording:
                return state
            time.sleep(.5)
        raise RuntimeError('Board state deadline expired')

    def media_alive(self):
        # An interactive shell avoids NSH's short single-command response.
        raw = self.run(['shell'], input=b'ps\nexit\n')
        return bool(re.search(r'\bTask\b[^\n]*\bmediad\b', raw))


def exercise(board, rounds, record_seconds, idle_seconds):
    results = []
    initial = board.state()
    if initial['recording'] or initial['busy']:
        raise RuntimeError('Board is in use; finish the current interaction first')
    for index in range(rounds):
        began = time.monotonic()
        attempted = False
        try:
            ack = board.shell('qiji_config record')
            if 'Record transition accepted' not in ack:
                raise RuntimeError('Firmware did not accept record; verify installed version')
            attempted = True
            board.await_state(1, 10)
            time.sleep(record_seconds)
            ack = board.shell('qiji_config stop')
            if 'Record transition accepted' not in ack:
                raise RuntimeError('Firmware did not accept stop')
            final = board.await_state(0, 45)
            attempted = False
            alive = board.media_alive()
            results.append({'round': index+1, 'elapsed_s': round(time.monotonic()-began, 2),
                            'final': final, 'media_alive': alive,
                            'software_dialogue_completed': alive and final['reply_present'] and
                            final['status'] == '可以继续对话'})
            if not alive:
                raise RuntimeError('mediad exited after interaction')
        finally:
            if attempted:
                # Best-effort stop only after this harness attempted recording.
                try:
                    board.shell('qiji_config stop')
                except RuntimeError:
                    pass
        if index+1 < rounds:
            time.sleep(idle_seconds)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sdk = Path(os.environ.get('LOCALAPPDATA', ''))/'Android/sdk/platform-tools/adb.exe'
    parser.add_argument('--adb', default=str(sdk) if sdk.is_file() else shutil.which('adb'))
    parser.add_argument('--serial', default='1234')
    parser.add_argument('--expected-build', default='Sep 19 2026 20:26:48')
    parser.add_argument('--output', type=Path, default=Path('artifacts/board-acceptance.json'))
    parser.add_argument('--exercise', action='store_true', help='Record audio and use configured cloud services')
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--record-seconds', type=float, default=3)
    parser.add_argument('--idle-seconds', type=float, default=10)
    args = parser.parse_args()
    if not args.adb or not 1 <= args.rounds <= 10 or not 1 <= args.record_seconds <= 15 or not 0 <= args.idle_seconds <= 60:
        parser.error('ADB required; rounds 1..10, recording 1..15 s, idle 0..60 s')
    report = {'mode': 'exercise' if args.exercise else 'inspect', 'complete': False,
              'physical_audio_verified': False, 'recognition_accuracy_verified': False}
    try:
        board = Board(args.adb, args.serial)
        report['firmware'] = board.shell('uname -a').strip()
        if args.expected_build not in report['firmware']:
            raise RuntimeError('Unexpected or unreadable firmware version')
        report['voice'] = board.shell('qiji_config voice_status').strip()
        if not all(x in report['voice'] for x in ['ASR=aliyun', 'TTS=aliyun', 'AliyunKey=configured', 'clock=set']):
            raise RuntimeError('Voice prerequisites not ready')
        report['state'] = board.state()
        network = board.shell('ifconfig wlan0')
        report['wifi_running'] = bool(re.search(r'\bRUNNING\b', network))
        address = re.search(r'inet addr:([\d.]+)', network)
        report['ip'] = address[1] if address else None
        if not report['wifi_running'] or report['ip'] in (None, '0.0.0.0', '10.0.0.2', '255.255.255.255'):
            raise RuntimeError('Wi-Fi link or DHCP address not ready')
        report['media_alive'] = board.media_alive()
        if not report['media_alive']:
            raise RuntimeError('mediad not found in process snapshot')
        if args.exercise:
            report['rounds'] = exercise(board, args.rounds, args.record_seconds, args.idle_seconds)
            report['all_software_dialogues_completed'] = all(r['software_dialogue_completed'] for r in report['rounds'])
        report['complete'] = True
    except (RuntimeError, OSError) as exc:
        report['error'] = redact(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
