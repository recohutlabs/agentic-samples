"""Compatibility imports; prompts are maintained in prompts/."""
from prompts.service import INSTRUCTIONS as SERVICE_AGREEMENT_INSTRUCTIONS
from prompts.employment import INSTRUCTIONS as EMPLOYMENT_INSTRUCTIONS
from prompts.classification import classification_instructions
from registry import CONTRACT_TYPES
TYPE_INSTRUCTIONS = classification_instructions(CONTRACT_TYPES)
