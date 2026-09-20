"""Save host-only cloud settings interactively or import the connected Gemini."""
import argparse
import getpass
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'artifacts/private-ai-logs/duet-runtime/cloud.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-gemini', action='store_true')
    parser.add_argument('--adb')
    parser.add_argument('--serial')
    args = parser.parse_args()
    if args.from_gemini:
        adb = args.adb or shutil.which('adb')
        if not adb and os.name == 'nt':
            adb = str(Path(os.environ['LOCALAPPDATA']) / 'Android/sdk/platform-tools/adb.exe')
        if not adb:
            raise SystemExit('ADB is not available')
        raw = subprocess.check_output([adb, 'devices'], timeout=10, text=True)
        devices = [line.split()[0] for line in raw.splitlines() if line.endswith('\tdevice')]
        serial = args.serial or (devices[0] if len(devices) == 1 else '')
        if not serial or serial not in devices:
            raise SystemExit('Connect one online Gemini, or select --serial')
        result = subprocess.run([adb, '-s', serial, 'shell', 'cat /data/ai_agent/config/config.json'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        # Capture, parse and allowlist only cloud fields; never print the raw file.
        raw = result.stdout.decode('utf-8', errors='strict')
        try:
            source = json.loads(raw[raw.index('{'):raw.rindex('}')+1])
            port = str(source.get('llm_port', '443'))
            host = source['llm_host'] + (':' + port if port != '443' else '')
            data = {'DUET_LLM_URL': 'https://' + host + source['llm_path'],
                    'DUET_LLM_MODEL': source['model'], 'DUET_LLM_KEY': source['api_key'],
                    'DASHSCOPE_API_KEY': source['aliyun_asr_key']}
        except (ValueError, KeyError, TypeError):
            raise SystemExit('Gemini cloud configuration is incomplete; no credentials printed')
    else:
        data = {
            'DUET_LLM_URL': input('LLM HTTPS URL [https://ark.cn-beijing.volces.com/api/v3/chat/completions]: ').strip() or 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
            'DUET_LLM_MODEL': input('Model [doubao-seed-character-260628]: ').strip() or 'doubao-seed-character-260628',
            'DUET_LLM_KEY': getpass.getpass('Doubao API key: ').strip(),
            'DASHSCOPE_API_KEY': getpass.getpass('Beijing DashScope API key: ').strip(),
        }
    if urlsplit(data['DUET_LLM_URL']).scheme != 'https' or not all(isinstance(v, str) and v for v in data.values()):
        raise SystemExit('Invalid cloud configuration')
    DEST.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(DEST, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print('Cloud settings saved locally. No keys written to source or Passport.')


if __name__ == '__main__': main()
