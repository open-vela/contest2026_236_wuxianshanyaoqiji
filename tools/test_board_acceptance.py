"""Host-only checks: never connect to or record from a real board."""
import unittest
from unittest.mock import patch
import subprocess
import board_acceptance as acceptance


class AcceptanceTests(unittest.TestCase):
    def test_rejects_truncated_state(self):
        with self.assertRaises(RuntimeError):
            acceptance.parse_result('busy=0 recording=0\nstatus=ready')

    def test_masks_credentials(self):
        text='sk-test123 ark-test456 passphrase=secret, password:other psk=value'
        clean=acceptance.redact(text)
        for value in ['test123','test456','secret','other','value']:
            self.assertNotIn(value,clean)

    def test_offline_and_timeout_are_errors(self):
        board=acceptance.Board('mock-adb','mock-board')
        with patch.object(acceptance.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'',b'device offline')):
            with self.assertRaises(RuntimeError):board.shell('uname -a')
        with patch.object(acceptance.subprocess,'run',side_effect=subprocess.TimeoutExpired('mock',1)):
            with self.assertRaises(RuntimeError):board.shell('uname -a')

    def test_refuses_to_interrupt_existing_recording(self):
        class Busy:
            def state(self):return {'recording':1,'busy':0}
            def shell(self,c):raise AssertionError('must not mutate a busy board')
        with self.assertRaises(RuntimeError):acceptance.exercise(Busy(),3,1,0)

    def test_cycles_and_checks_daemon(self):
        class Fake:
            def __init__(self):self.commands=[];self.checks=0
            def state(self):return {'recording':0,'busy':0}
            def shell(self,c):self.commands.append(c);return 'Record transition accepted'
            def await_state(self,recording,timeout):
                return {'recording':recording,'busy':0,'status':'可以继续对话','reply_present':True}
            def media_alive(self):self.checks+=1;return True
        board=Fake()
        with patch.object(acceptance.time,'sleep'):
            rounds=acceptance.exercise(board,3,1,0)
        self.assertEqual(board.commands,['qiji_config record','qiji_config stop']*3)
        self.assertEqual(board.checks,3)
        self.assertTrue(all(r['software_dialogue_completed'] for r in rounds))

    def test_stops_owned_recording_on_timeout(self):
        class Fake:
            def __init__(self):self.commands=[]
            def state(self):return {'recording':0,'busy':0}
            def shell(self,c):self.commands.append(c);return 'Record transition accepted'
            def await_state(self,*args):raise RuntimeError('timeout')
        board=Fake()
        with self.assertRaises(RuntimeError):acceptance.exercise(board,1,1,0)
        self.assertEqual(board.commands,['qiji_config record','qiji_config stop'])


if __name__=='__main__':unittest.main()
