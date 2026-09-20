"""Operate the existing real-device coordinator without exposing its pairing token."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('status', 'start', 'stop', 'watch'))
    p.add_argument('--topic')
    p.add_argument('--wait', action='store_true')
    p.add_argument('--seconds', type=int, default=240)
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    if not 1 <= a.seconds <= 600:
        p.error('--seconds must be between 1 and 600')
    pairing = json.loads((ROOT/'artifacts/private-ai-logs/duet-runtime/config.json').read_text(encoding='utf-8'))

    def request(path, body=None):
        req = urllib.request.Request('http://127.0.0.1:8765'+path,
            json.dumps(body).encode() if body is not None else None,
            {'Authorization':'Bearer '+pairing['token'], 'Content-Type':'application/json'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.load(response)

    initial = request('/v1/state')
    began = False
    if a.action == 'start':
        if initial['demo'] or initial['text_only']:
            raise SystemExit('Expected LIVE AI with speech; refusing a scripted/text-only test')
        if not all(initial['peers'].values()) or not all(initial.get('ready', {}).values()):
            raise SystemExit('Both real devices must be online and ready')
        result = request('/v1/start', {'topic':a.topic} if a.topic else {})
        if not result.get('started'):
            raise SystemExit('Start rejected: finish/stop the current interaction first')
        began = True
    elif a.action == 'stop':
        request('/v1/stop', {})
    report = {'started_at':datetime.now(timezone.utc).isoformat(),
              'action':a.action, 'real_device_polls_only':True, 'initial':initial, 'events':[]}
    start = time.monotonic()
    previous = None
    code = 0
    try:
        while True:
            state = request('/v1/state')
            event = {'elapsed_s':round(time.monotonic()-start, 2), 'snapshot':state}
            key = json.dumps(state, sort_keys=True)
            if key != previous:
                report['events'].append(event)
                brief = {k:state.get(k) for k in ('state','peers','ready','error')}
                brief.update(elapsed_s=event['elapsed_s'], completed_turns=len(state['transcript']),
                    summary_present=bool(state['summary']))
                print(json.dumps(brief,ensure_ascii=True),flush=True)
                previous = key
            report['final'] = state
            report['elapsed_s'] = event['elapsed_s']
            if not (a.wait or a.action == 'watch') or state['state'] in ('complete','stopped'):
                if began and state['state'] == 'stopped': code = 1
                break
            if time.monotonic()-start >= a.seconds:
                report['timed_out'] = True
                if began: request('/v1/stop', {})
                code = 1
                break
            time.sleep(1)
    finally:
        if a.report:
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return code


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit('Coordinator operation failed: '+type(exc).__name__)
