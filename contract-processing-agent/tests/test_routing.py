"""Focused routing and compatibility checks without provider calls."""
import unittest
from pathlib import Path
from unittest.mock import patch
from pydantic import BaseModel, ValidationError
import workflow as extraction
from classifier import classification_schema
from registry import CONTRACT_TYPES, ContractDefinition
from prompts.classification import classification_instructions

class RoutingTests(unittest.TestCase):
    def test_existing_outputs_validate_unchanged(self):
        service={'contract_type','start_date','customer','vendor','end_date','contract_id','payment_terms','renewal_terms','fees_and_pricing','termination_terms','scope','service_levels','execution_status','amendments','liability_and_indemnity','confidentiality_and_data_protection','governing_law_and_disputes','insurance_requirements','assignment_and_subcontracting'}
        employment={'contract_type','contract_id','employee','employer','start_date','end_date','employment_terms','compensation','probation','working_hours_and_leave','termination_terms','confidentiality_and_data_protection','intellectual_property','restrictions','governing_law_and_disputes','execution_status','amendments'}
        for kind, fields in [('service_agreement',service),('employment_contract',employment)]:
            schema=CONTRACT_TYPES[kind].schema
            self.assertEqual(set(schema.model_fields),fields)
            payload={name:None for name in fields}
            payload['contract_type']=kind
            self.assertEqual(schema.model_validate(payload).model_dump(mode='json'),payload)

    def test_third_family_uses_shared_flow(self):
        class Lease(BaseModel):
            contract_type: str
            landlord: str
        definitions={**CONTRACT_TYPES, 'lease':ContractDefinition(Lease,'Extract lease','Landlord-tenant lease')}
        schema=classification_schema(definitions)
        self.assertEqual(schema(contract_type='lease').contract_type,'lease')
        self.assertIn('Landlord-tenant lease',classification_instructions(definitions))
        with self.assertRaises(ValidationError): schema(contract_type='invented')
        value=Lease(contract_type='lease',landlord='Test landlord')
        with patch.object(extraction,'CONTRACT_TYPES',definitions), patch.object(extraction,'read_contract_text',return_value='PDF text'), patch.object(extraction,'load_openai_config',return_value=('key','model')), patch.object(extraction,'classify',return_value='lease'), patch.object(extraction,'extract_candidate',return_value=value) as run, patch.object(extraction,'verify_contract',return_value=value) as verify:
            self.assertIs(extraction.extract(Path('test.pdf')),value)
            self.assertIs(run.call_args.args[2].schema,Lease)
            self.assertIs(verify.call_args.args[1],value)

    def test_unsupported_does_not_extract(self):
        for kind in ('unsupported','unclear'):
            with patch.object(extraction,'read_contract_text',return_value='text'), patch.object(extraction,'load_openai_config',return_value=('key','model')), patch.object(extraction,'classify',return_value=kind), patch.object(extraction,'extract_candidate') as make:
                with self.assertRaises(ValueError): extraction.extract(Path('test.pdf'))
                make.assert_not_called()

if __name__=='__main__': unittest.main()
