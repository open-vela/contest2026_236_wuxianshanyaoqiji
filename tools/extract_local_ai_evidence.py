"""Copy this project's WorkBuddy transcripts unchanged into a git-ignored archive.

This is a native evidence backup, NOT an official contest log converter.
Trae databases are inspected for format only; no decryption is attempted.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    root = Path(__file__).resolve().parent.parent
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination = root / 'artifacts/private-ai-logs' / stamp
    destination.mkdir(parents=True, exist_ok=False)
    report = {'created_at_utc': stamp, 'purpose': 'Unmodified native evidence backup',
              'official_contest_format': False, 'published': False,
              'workbuddy': [], 'trae_databases': []}
    home = Path.home()
    database = home / '.workbuddy/workbuddy.db'
    if database.is_file():
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
            rows = connection.execute(
                'SELECT id,cwd,created_at,updated_at FROM sessions WHERE lower(cwd)=lower(?)',
                (str(root),)).fetchall()
        project_dir = home / '.workbuddy/projects' / re.sub(r'[:\\/]+', '-', str(root)).lstrip('-')
        for session_id, cwd, created, updated in rows:
            if not re.fullmatch(r'[a-fA-F0-9-]{36}', session_id):
                raise ValueError('Unexpected session identifier')
            source = project_dir / (session_id + '.jsonl')
            raw = source.read_bytes()
            events = [json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]
            for event in events:
                if event.get('cwd') and os.path.normcase(os.path.normpath(event['cwd'])) != os.path.normcase(str(root)):
                    raise ValueError('Mixed-workspace transcript requires manual review')
            target = destination / 'workbuddy' / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            assert sha(target.read_bytes()) == sha(raw)
            # Counts only: never print matching secrets or transcript content.
            patterns = {
                'api_key_like': rb'\b(?:sk|ark)-[A-Za-z0-9-]{10,}',
                'credential_field': rb'(?i)(?:api[_-]?key|password|passphrase|access[_-]?token)\s*[=:]',
            }
            report['workbuddy'].append({
                'session_id': session_id, 'source': str(source),
                'copy': str(target.relative_to(destination)), 'bytes': len(raw), 'sha256': sha(raw),
                'created_at_ms': created, 'updated_at_ms': updated, 'events': len(events),
                'event_types': dict(Counter(e.get('type', 'unknown') for e in events)),
                'message_roles': dict(Counter(e.get('role', 'unknown') for e in events if e.get('type') == 'message')),
                'sensitive_pattern_counts': {key: len(re.findall(pattern, raw)) for key, pattern in patterns.items()},
                'privacy_review_required': True,
            })
    for name in ['Trae', 'TRAE SOLO CN']:
        source = Path(os.environ['APPDATA']) / name / 'ModularData/ai-agent/database.db'
        if source.is_file():
            with source.open('rb') as stream:
                sqlite_header = stream.read(16) == b'SQLite format 3\x00'
            report['trae_databases'].append({'client_directory': name, 'path': str(source),
                'bytes': source.stat().st_size, 'standard_sqlite_header': sqlite_header,
                'copied': False, 'next_step': 'Export the project conversation from the client'})
    (destination / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'archive': str(destination), 'sessions': len(report['workbuddy']),
        'total_bytes': sum(item['bytes'] for item in report['workbuddy']),
        'unchanged_copies_verified': True, 'official_contest_format': False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
