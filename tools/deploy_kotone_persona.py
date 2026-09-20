"""Back up, deploy and read back only the board's SOUL.md; no reboot or key changes."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from board_acceptance import Board
from build_kotone_persona import compile_persona, PROJECT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default=str(Path(os.environ.get('LOCALAPPDATA', '')) / 'Android/sdk/platform-tools/adb.exe'))
    parser.add_argument('--serial')
    args = parser.parse_args()
    raw = subprocess.check_output([args.adb, 'devices'], timeout=10, text=True)
    online = [line.split()[0] for line in raw.splitlines() if line.strip().endswith('\tdevice')]
    serial = args.serial or (online[0] if len(online) == 1 else None)
    if serial not in online:
        raise SystemExit('Connect one online board, or specify --serial; nothing changed')
    board = Board(args.adb, serial)
    state = board.state()
    if state['busy'] or state['recording']:
        raise SystemExit('Board is busy; finish the interaction before deployment')
    persona = compile_persona().encode('utf-8')
    remote = '/data/ai_agent/config/SOUL.md'
    backup = PROJECT/'artifacts/private-ai-logs/persona-backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    # Old personalization may contain private user information; keep it ignored.
    board.run(['pull', remote, str(backup/'SOUL.md')])
    with tempfile.TemporaryDirectory(prefix='qiji-persona-') as tmp:
        local = Path(tmp)/'SOUL.md'
        local.write_bytes(persona)
        board.run(['push', str(local), remote])
        check = Path(tmp)/'readback.md'
        board.run(['pull', remote, str(check)])
        if check.read_bytes() != persona:
            raise RuntimeError(f'Persona readback mismatch; original retained at {backup}')
    report = {'serial':serial, 'sha256':hashlib.sha256(persona).hexdigest(),
              'bytes':len(persona), 'readback_verified':True,
              'scope':'SOUL only. Display name, session isolation and spoken-text filter require v0.4.0 firmware.'}
    (backup/'deployment.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
