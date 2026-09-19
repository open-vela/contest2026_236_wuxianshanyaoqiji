"""Explicit, project-scoped recovery of visible Codex Desktop transcript events.

Uses the official event writer and unchanged schemas. Does not install hooks,
change workspace gates, modify native logs, or export hidden reasoning/prompts.
Every export is a new, immutable candidate; review before publishing.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys


def normal_path(value):
    return os.path.normcase(os.path.abspath(str(value).removeprefix('\\\\?\\')))


def visible_output(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        # Images/audio/encrypted blobs are not textual development evidence.
        return [visible_output(x) for x in value if not isinstance(x, dict)
                or x.get('type') in (None, 'text', 'output_text', 'input_text')]
    if isinstance(value, dict):
        return {k: visible_output(v) for k, v in value.items()
                if k not in ('encrypted_content', 'thinking', 'reasoning', 'data', 'image_url', 'audio')}
    return value


def convert(raw_records, session_id, project):
    events, counts, names = [], Counter(), {}
    active = False
    cwd = model = origin = None
    for line_number, raw in raw_records:
        kind, payload = raw.get('type'), raw.get('payload') or {}
        if kind == 'session_meta':
            active = (payload.get('id') == session_id
                      and normal_path(payload.get('cwd', '')) == normal_path(project)
                      and payload.get('source') == 'vscode')
            if active:
                cwd, origin = payload['cwd'], payload.get('originator')
            else:
                counts['unselected_session_segments'] += 1
            continue
        if not active:
            counts['outside_selected_segment'] += 1
            continue
        if kind == 'turn_context':
            if payload.get('cwd') and normal_path(payload['cwd']) != normal_path(project):
                raise ValueError('Selected session changes workspace; manual review required')
            model = payload.get('model')
            counts['private_context_omitted'] += 1
            continue
        if kind != 'response_item':
            counts['non_response_records_omitted'] += 1
            continue
        subtype = payload.get('type')
        ts = raw.get('timestamp')
        if not isinstance(ts, str):
            raise ValueError('Missing original timestamp')
        datetime.fromisoformat(ts.replace('Z', '+00:00'))
        common = {'ts': ts, 'cwd': cwd,
                  'metadata': {'source_line': line_number, 'source_type': subtype,
                               'capture_method': 'manual-native-visible-backfill'}}
        if isinstance(model, str):
            common['model'] = model
        if subtype == 'message':
            role = payload.get('role')
            if role not in ('user', 'assistant') or payload.get('channel') == 'analysis':
                counts['private_messages_omitted'] += 1
                continue
            blocks = payload.get('content') or []
            text = '\n'.join(b['text'] for b in blocks if isinstance(b, dict)
                             and b.get('type') in ('input_text', 'output_text', 'text')
                             and isinstance(b.get('text'), str))
            if text:
                events.append({**common, 'role': role, 'text': text})
        elif subtype in ('function_call', 'custom_tool_call'):
            call_id, name = payload.get('call_id'), payload.get('name')
            if not call_id or not name:
                raise ValueError('Tool call identity missing')
            names[call_id] = name
            arguments = payload.get('arguments') if subtype == 'function_call' else payload.get('input')
            if subtype == 'function_call' and isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except ValueError:
                    pass  # Keep original malformed arguments, do not invent a replacement.
            events.append({**common, 'role': 'tool', 'tool_name': name,
                           'tool_call_id': call_id, 'input': visible_output(arguments), 'output': None})
        elif subtype in ('function_call_output', 'custom_tool_call_output'):
            call_id = payload.get('call_id')
            if call_id not in names:
                counts['unpaired_tool_outputs_omitted'] += 1
                continue
            events.append({**common, 'role': 'tool', 'tool_name': names[call_id],
                           'tool_call_id': call_id, 'input': None,
                           'output': visible_output(payload.get('output'))})
        else:
            counts['reasoning_or_other_items_omitted'] += 1
    return events, dict(counts), origin


def load_records(data):
    records = []
    for index, line in enumerate(data.splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append((index, json.loads(line)))
        except ValueError:
            # A live session can end in an unfinished append. Never skip a broken interior line.
            if index == len(data.splitlines()) and not data.endswith(b'\n'):
                break
            raise
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--collector', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--github-login', required=True)
    parser.add_argument('--redaction-file', required=True, type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', args.github_login):
        parser.error('Invalid GitHub login')
    shared = args.collector/'adapters/shared'
    sys.path.insert(0, str(shared))
    import snapshot_core as official
    rules = list(official.DEFAULT_REDACT_RULES)
    rules.extend((re.compile(item['pattern']), item.get('replacement', '[REDACTED]'))
                 for item in json.loads(args.redaction_file.read_text(encoding='utf-8')))
    database = Path.home()/'.codex/state_5.sqlite'
    with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as connection:
        rows = connection.execute('SELECT id,cwd,rollout_path FROM threads').fetchall()
    selected = [r for r in rows if normal_path(r[1]) == normal_path(project)]
    if args.output.exists():
        parser.error('Output already exists; choose a new snapshot directory')
    args.output.mkdir(parents=True)
    member = args.output/'logs'/args.github_login
    member.mkdir(parents=True)
    manifest = {'schema_version': '1.0', 'team_id': project.name,
                'github_login': args.github_login, 'generator': 'qiji-codex-visible-backfill@1.0',
                'updated_at': datetime.now(timezone.utc).isoformat(), 'sessions': []}
    summary = {'matched_threads': len(selected), 'exported_sessions': 0, 'events': 0,
               'redactions': 0, 'official_acceptance_claimed': False,
               'automatic_workspace_gate_changed': False, 'skipped_threads': []}
    for session_id, cwd, path in selected:
        if not re.fullmatch(r'[A-Za-z0-9-]+', session_id):
            raise ValueError('Invalid native session ID')
        source = Path(path)
        data = source.read_bytes()
        events, omissions, origin = convert(load_records(data), session_id, project)
        if not events:
            summary['skipped_threads'].append({'id': session_id, 'reason': 'No selected visible events'})
            continue
        relative = f"logs/{args.github_login}/{events[0]['ts'][:10]}/codex__{session_id}.jsonl"
        result = official.append_events(args.output/relative, events, session_id, project.name,
                                        args.github_login, 'codex', 0, rules)
        manifest['sessions'].append({
            'session_id': session_id, 'tool': 'codex', 'started_at': events[0]['ts'],
            'last_event_at': events[-1]['ts'], 'event_count': len(events), 'file_path': relative,
            'collection_mode': 'vscode_extension_partial', 'health': 'degraded',
            'data_completeness_warning': 'Explicit project-scoped recovery of Codex Desktop native source=vscode. '
                'Visible user/assistant text and paired tool events only; internal reasoning, system/developer '
                'instructions, compaction, binary media, duplicate event_msg records and other-session segments '
                'are excluded. Secrets redacted during export. Historical workspace is outside .repo; '
                'not an official automatic capture, not a claim of contest eligibility or full work hours.',
            'capture_method': 'manual-native-visible-backfill', 'source_originator': origin,
            'original_cwd': cwd, 'omitted_record_counts': omissions,
            'redacted_count_total': result['redacted'],
            'source_integrity': {'main_sha256': hashlib.sha256(data).hexdigest(), 'main_size': len(data),
                                 'captured_at': datetime.now(timezone.utc).isoformat()},
            'export_sha256': hashlib.sha256((args.output/relative).read_bytes()).hexdigest(),
        })
        summary['exported_sessions'] += 1
        summary['events'] += len(events)
        summary['redactions'] += result['redacted']
    (member/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (args.output/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == '__main__':
    main()
