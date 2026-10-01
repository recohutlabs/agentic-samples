"""Verification failure and final-output handoff contracts without provider calls."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from pydantic import BaseModel
import workflow
from agents.runner import require_model
from agents.verifier import verify_contract
from registry import ContractDefinition

class Sample(BaseModel):
    contract_type: str
    customer: str | None

class VerificationTests(unittest.TestCase):
    def test_missing_result_is_failure(self):
        agent=lambda *a,**kw:SimpleNamespace(structured_output=None)
        with self.assertRaisesRegex(ValueError,'Verification failed'):
            require_model(agent,'prompt',Sample,{},'Verification failed')

    def test_verifier_receives_source_and_candidate(self):
        candidate=Sample(contract_type='sample',customer='Wrong')
        corrected=Sample(contract_type='sample',customer='Right')
        definition=ContractDefinition(Sample,'Family rules','Description')
        with patch('agents.verifier.make_agent'),patch('agents.verifier.require_model',return_value=corrected) as run:
            self.assertIs(verify_contract('Original PDF',candidate,'sample',definition,'key','model'),corrected)
            self.assertIn('Original PDF',run.call_args.args[1])
            self.assertIn('Wrong',run.call_args.args[1])

    def test_changed_type_is_rejected(self):
        candidate=Sample(contract_type='sample',customer=None)
        with patch('agents.verifier.make_agent'),patch('agents.verifier.require_model',return_value=Sample(contract_type='other',customer=None)):
            with self.assertRaisesRegex(ValueError,'changed'):
                verify_contract('source',candidate,'sample',ContractDefinition(Sample,'rules','description'),'key','model')

    def test_workflow_returns_correction_and_propagates_failure(self):
        candidate=Sample(contract_type='sample',customer='Wrong')
        corrected=Sample(contract_type='sample',customer='Right')
        with patch.object(workflow,'CONTRACT_TYPES',{'sample':ContractDefinition(Sample,'rules','description')}),patch.object(workflow,'read_contract_text',return_value='source'),patch.object(workflow,'load_openai_config',return_value=('key','model')),patch.object(workflow,'classify',return_value='sample'),patch.object(workflow,'extract_candidate',return_value=candidate),patch.object(workflow,'verify_contract',return_value=corrected) as verify:
            self.assertIs(workflow.extract(Path('test.pdf')),corrected)
            verify.side_effect=ValueError('verification unavailable')
            with self.assertRaisesRegex(ValueError,'unavailable'):workflow.extract(Path('test.pdf'))
