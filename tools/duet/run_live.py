"""Run the real voice/duet service with local credentials and the saved pairing token."""
import json
import argparse
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--model', choices=('character', 'turbo'))
selected, remaining = parser.parse_known_args()
sys.argv = [sys.argv[0]] + remaining

private = Path(__file__).resolve().parents[2] / 'artifacts/private-ai-logs/duet-runtime'
cloud = private / 'cloud.json'
if not cloud.exists():
    raise SystemExit('Run configure_cloud.py first (interactive, or --from-gemini).')
data = json.loads(cloud.read_text(encoding='utf-8'))
for name in ('DUET_LLM_URL', 'DUET_LLM_MODEL', 'DUET_LLM_KEY', 'DASHSCOPE_API_KEY'):
    if not isinstance(data.get(name), str) or not data[name]:
        raise SystemExit('Incomplete cloud configuration: ' + name)
    os.environ[name] = data[name]
if selected.model:
    os.environ['DUET_LLM_MODEL'] = {
        'character': 'doubao-seed-character-260628',
        'turbo': 'doubao-seed-2-1-turbo-260628',
    }[selected.model]
pairing = json.loads((private / 'config.json').read_text(encoding='utf-8'))
os.environ['DUET_TOKEN'] = pairing['token']
if '--host' not in sys.argv:
    sys.argv.extend(['--host', '0.0.0.0'])
from server import serve
serve()
