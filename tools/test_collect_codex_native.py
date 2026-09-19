"""Privacy and provenance checks for manual Codex transcript recovery."""
import json
from pathlib import Path
import unittest
from collect_codex_native import convert, load_records, visible_output


class NativeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.project = str(Path.cwd())

    def record(self, kind, payload):
        return {'type': kind, 'timestamp': '2026-09-19T10:00:00Z', 'payload': payload}

    def metadata(self, **kwargs):
        return self.record('session_meta', {'id': 'test-session', 'cwd': self.project,
                           'source': 'vscode', 'originator': 'Codex Desktop', **kwargs})

    def export(self, records):
        return convert(list(enumerate(records, 1)), 'test-session', self.project)[0]

    def test_only_visible_messages_no_private_context(self):
        records = [self.metadata()]
        for role in ['system', 'developer', 'user', 'assistant']:
            records.append(self.record('response_item', {'type': 'message', 'role': role,
                           'content': [{'type': 'output_text', 'text': role}]}))
        records += [self.record('response_item', {'type': 'reasoning', 'summary': 'private'}),
                    self.record('compacted', {'summary': 'private'}),
                    self.record('event_msg', {'type': 'agent_message', 'message': 'duplicate'}),
                    self.record('response_item', {'type': 'message', 'role': 'assistant',
                                'channel': 'analysis', 'content': [{'type': 'output_text', 'text': 'private'}]})]
        events = self.export(records)
        self.assertEqual([e['text'] for e in events], ['user', 'assistant'])
        self.assertNotIn('private', json.dumps(events))
        self.assertEqual([e['metadata']['source_line'] for e in events], [4, 5])

    def test_scope_and_embedded_sessions(self):
        message = self.record('response_item', {'type': 'message', 'role': 'user',
                              'content': [{'type': 'input_text', 'text': 'visible'}]})
        records = [self.metadata(cwd=self.project+'-other'), message,
                   self.metadata(), message, self.metadata(id='other-session'), message]
        self.assertEqual(len(self.export(records)), 1)

    def test_subagent_metadata_not_exported_as_root(self):
        self.assertEqual(self.export([self.metadata(source={'subagent': {'other': 'guardian'}})]), [])

    def test_real_tool_identity_and_json_arguments(self):
        events = self.export([self.metadata(),
            self.record('response_item', {'type': 'function_call', 'name': 'test',
                        'call_id': 'c1', 'arguments': '{"x":1}'}),
            self.record('response_item', {'type': 'function_call_output', 'call_id': 'c1', 'output': 'done'}),
            self.record('response_item', {'type': 'function_call_output', 'call_id': 'unknown', 'output': 'omit'})])
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['input'], {'x': 1})
        self.assertTrue(all(e['tool_call_id'] == 'c1' and e['tool_name'] == 'test' for e in events))
        self.assertEqual(events[1]['output'], 'done')

    def test_partial_append_and_corrupt_interior(self):
        self.assertEqual(len(load_records(b'{"type":"a"}\n{"unfinished"')), 1)
        with self.assertRaises(ValueError):
            load_records(b'{"unfinished"\n{"type":"a"}\n')

    def test_workspace_change_stops_export(self):
        with self.assertRaises(ValueError):
            self.export([self.metadata(), self.record('turn_context', {'cwd': self.project+'-other'})])

    def test_binary_and_private_fields_excluded(self):
        value = [{'type': 'text', 'text': 'visible'}, {'type': 'image', 'data': 'private'}]
        self.assertEqual(visible_output(value), [{'type': 'text', 'text': 'visible'}])
        self.assertNotIn('private', str(visible_output({'thinking': 'private', 'text': 'visible'})))


if __name__ == '__main__':
    unittest.main()
