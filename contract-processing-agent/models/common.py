"""Common contract structures and source-supported nullable facts."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema, model_validator

Money = Annotated[Decimal, WithJsonSchema({'type': 'string', 'pattern': r'^[0-9]+(?:\.[0-9]+)?$'})]

class ExecutionStatus(BaseModel):
    """Source-reported execution and uncertainty; no signature authentication."""
    model_config = ConfigDict(extra='forbid')
    status: Literal['executed', 'unsigned', 'unclear']
    signing_date: date | None
    conditions: str | None

class Amendment(BaseModel):
    """One amendment and its stated changes, without assumed execution."""
    model_config = ConfigDict(extra='forbid')
    reference: str
    amendment_date: date | None
    effective_date: date | None
    execution_status: Literal['executed', 'unsigned', 'unclear'] | None
    changes: list[str]
    conditions: str | None

class ConfidentialityAndDataProtection(BaseModel):
    """Stated information-handling duties, without inferred regulatory requirements."""
    model_config = ConfigDict(extra='forbid')
    confidentiality_obligations: list[str] | None
    survival: str | None
    data_protection_obligations: list[str] | None
    breach_notification: str | None
    return_or_deletion: str | None

class GoverningLawAndDisputes(BaseModel):
    """Applicable law, courts/arbitration and contractual escalation steps."""
    model_config = ConfigDict(extra='forbid')
    governing_law: str | None
    jurisdiction: str | None
    resolution_method: str | None
    escalation_steps: list[str] | None
    arbitration_seat: str | None
