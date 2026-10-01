"""Supported contract families: one registration owns classification and extraction."""
from dataclasses import dataclass
from pydantic import BaseModel
from models.service import ServiceAgreement
from models.employment import EmploymentContract
from prompts.service import INSTRUCTIONS as SERVICE_INSTRUCTIONS
from prompts.employment import INSTRUCTIONS as EMPLOYMENT_INSTRUCTIONS

@dataclass(frozen=True)
class ContractDefinition:
    """A family schema, extraction prompt and relationship description."""
    schema: type[BaseModel]
    instructions: str
    description: str

CONTRACT_TYPES = {
    'service_agreement': ContractDefinition(ServiceAgreement, SERVICE_INSTRUCTIONS,
        'Customer-provider products/services, including staffing where workers are employed by the provider and independent contractor/consulting agreements. A customer buys provider services; workers remain provider employees. Direct hiring by the customer belongs to employment_contract. Employee words alone do not make employment.'),
    'employment_contract': ContractDefinition(EmploymentContract, EMPLOYMENT_INSTRUCTIONS,
        'Direct employer-employee agreement, employment offer or appointment terms: the employer hires an individual as its employee. Excludes purchasing services from a staffing provider or independent contractor; a job title alone does not establish employment.'),
}
