"""Bounded live persona smoke evaluation; responses require human review."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
from build_kotone_persona import APP, compile_persona


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--key-stdin', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    key = sys.stdin.readline().strip() if args.key_stdin else os.environ.get('ARK_API_KEY', '')
    if not key:
        raise SystemExit('Set ARK_API_KEY or use --key-stdin; no credentials are saved')
    persona = compile_persona()
    cases = json.loads((APP/'character/evals.json').read_text(encoding='utf-8'))

    def run(case):
        messages = [{'role':'system', 'content':persona}] + case.get('history', [])
        messages.append({'role':'user', 'content':case['question']})
        body = json.dumps({'model':'doubao-seed-character-260628', 'messages':messages,
                           'max_tokens':512, 'temperature':0.6}).encode()
        request = urllib.request.Request('https://ark.cn-beijing.volces.com/api/v3/chat/completions',
            data=body, headers={'Authorization':'Bearer '+key, 'Content-Type':'application/json'})
        start = time.monotonic()
        result = dict(case)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = json.load(response)
            result.update(response=data['choices'][0]['message']['content'],
                          finish_reason=data['choices'][0].get('finish_reason'),
                          usage=data.get('usage'), review='pending')
        except urllib.error.HTTPError as exc:
            result.update(error=f'HTTP {exc.code}', review='not_run')
        except Exception as exc:
            result.update(error=type(exc).__name__, review='not_run')
        result['elapsed_s'] = round(time.monotonic()-start, 2)
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, cases))
    report = {'scope':'Host persona-only smoke tests; excludes board tools, memories, audio and UI',
              'model':'doubao-seed-character-260628', 'temperature':0.6,
              'persona_sha256':hashlib.sha256(persona.encode()).hexdigest(), 'cases':results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Recorded {len(results)} cases; {sum("error" in r for r in results)} API errors; manual review required')


if __name__ == '__main__':
    main()
