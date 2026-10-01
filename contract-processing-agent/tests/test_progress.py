"""Check progress output privacy, heartbeat cleanup and CLI JSON separation."""
import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from threading import Event
from unittest.mock import patch
from pydantic import BaseModel
from progress import Progress
import main

class Output(BaseModel):
    contract_type: str = 'service_agreement'

class ProgressTests(unittest.TestCase):
    def test_callback_ignores_sensitive_payloads(self):
        stream=io.StringIO();progress=Progress(debug=True,stream=stream)
        progress.callback(data='PRIVATE CONTRACT',reasoningText='PRIVATE REASONING',event={'contentBlockStart':{'start':{'toolUse':{'name':'PRIVATE NAME','input':'PRIVATE INPUT'}}}})
        self.assertNotIn('PRIVATE',stream.getvalue())
        self.assertIn('Structured-output tool event',stream.getvalue())

    def test_heartbeat_stops_after_failure(self):
        stream=io.StringIO();progress=Progress(stream=stream,heartbeat_seconds=0.005)
        with self.assertRaises(ValueError):
            with progress.step('Extraction','extract_candidate'):
                Event().wait(0.02)
                raise ValueError('PRIVATE ERROR')
        self.assertIn('running',stream.getvalue())
        self.assertIn('failed (ValueError)',stream.getvalue())
        before=stream.getvalue();Event().wait(0.02)
        self.assertEqual(before,stream.getvalue())
        self.assertNotIn('PRIVATE ERROR',before)

    def test_cli_json_stays_on_stdout(self):
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch('sys.argv',['main.py','file.pdf','--debug']),patch.object(main,'extract',return_value=Output()),redirect_stdout(stdout),redirect_stderr(stderr):
            self.assertEqual(main.main(),0)
        self.assertEqual(json.loads(stdout.getvalue()),{'contract_type':'service_agreement'})
        self.assertIn('Processing completed',stderr.getvalue())
