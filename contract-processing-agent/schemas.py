"""Compatibility imports; schemas are maintained in models/."""
from models.common import *
from models.service import *
from models.employment import *
from classifier import classification_schema
from registry import CONTRACT_TYPES
ContractType = classification_schema(CONTRACT_TYPES)
