"""Service contract structures and source-supported nullable facts."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema, model_validator

from models.common import Money, Amendment, ConfidentialityAndDataProtection, ExecutionStatus, GoverningLawAndDisputes

class PaymentTerms(BaseModel):
    """General payment rule; unresolved attributes remain null."""
    model_config = ConfigDict(extra='forbid')
    payment_type: Literal['advance', 'arrears', 'milestone', 'other'] | None
    due_in_days: int | None = Field(ge=0)
    day_basis: Literal['calendar', 'business', 'unspecified'] | None
    trigger: str | None
    conditions: str | None

class RenewalTerms(BaseModel):
    """Source renewal mechanism and opt-out notice, without assumed renewal events."""
    model_config = ConfigDict(extra='forbid')
    renewal_type: Literal['automatic', 'manual', 'none', 'other'] | None
    renewal_period: int | None = Field(ge=1)
    period_unit: Literal['days', 'months', 'years'] | None
    maximum_renewals: int | None = Field(ge=0)
    non_renewal_notice_days: int | None = Field(ge=0)
    notice_day_basis: Literal['calendar', 'business', 'unspecified'] | None
    notice_trigger: str | None
    notice_party: str | None
    notice_method: str | None
    conditions: str | None

    @model_validator(mode='after')
    def clear_unresolved_units(self):
        """A unit has no meaning without a period; unspecified is not source evidence."""
        if self.renewal_period is None:
            self.period_unit = None
        if self.non_renewal_notice_days is None and self.notice_day_basis == 'unspecified':
            self.notice_day_basis = None
        return self

class Fee(BaseModel):
    """One fixed fee, variable rate or optional charge as stated in the contract."""
    model_config = ConfigDict(extra='forbid')
    description: str
    amount: Money | None = Field(ge=0)
    kind: Literal['fixed', 'variable', 'optional', 'unknown']
    frequency: Literal['one_time', 'monthly', 'quarterly', 'annual', 'usage', 'milestone', 'other', 'unknown']
    basis: str | None
    period: str | None
    conditions: str | None

class FeesAndPricing(BaseModel):
    """Stated pricing, without calculated totals or actual spending."""
    model_config = ConfigDict(extra='forbid')
    currency: str | None
    tax_treatment: str | None
    stated_total: Money | None = Field(ge=0)
    fees: list[Fee]
    price_escalation: str | None

class TerminationRoute(BaseModel):
    """One source exit route, with notice and breach-cure requirements kept separate."""
    model_config = ConfigDict(extra='forbid')
    reason: Literal['convenience', 'material_breach', 'insolvency', 'other']
    entitled_party: str | None
    conditions: str | None
    notice_duration: int | None = Field(ge=0)
    notice_unit: Literal['hours', 'days', 'months', 'years'] | None
    notice_day_basis: Literal['calendar', 'business', 'unspecified'] | None
    cure_duration: int | None = Field(ge=0)
    cure_unit: Literal['hours', 'days', 'months', 'years'] | None
    cure_day_basis: Literal['calendar', 'business', 'unspecified'] | None
    exit_charges: str | None
    exit_obligations: str | None

    @model_validator(mode='after')
    def clear_unresolved_units(self):
        """Remove units that have no corresponding duration."""
        for prefix in ('notice', 'cure'):
            if getattr(self, f'{prefix}_duration') is None:
                setattr(self, f'{prefix}_unit', None)
                setattr(self, f'{prefix}_day_basis', None)
        return self

class TerminationTerms(BaseModel):
    """Stated termination routes and the general notice delivery method."""
    model_config = ConfigDict(extra='forbid')
    routes: list[TerminationRoute]
    notice_method: str | None

class Scope(BaseModel):
    """Included work, geographic coverage, exclusions and customer dependencies."""
    model_config = ConfigDict(extra='forbid')
    services: list[str] | None
    locations: list[str] | None
    exclusions: list[str] | None
    customer_responsibilities: list[str] | None

class ServiceLevel(BaseModel):
    """Promised performance and conditional remedies, not actual results."""
    model_config = ConfigDict(extra='forbid')
    metric: str
    target: str | None
    measurement_period: str | None
    conditions: str | None
    remedy: str | None

class LiabilityAndIndemnity(BaseModel):
    """Exposure formula, exceptions and defence/indemnity obligations."""
    model_config = ConfigDict(extra='forbid')
    cap_type: Literal['fixed_amount', 'fees_based', 'unlimited', 'other'] | None
    cap_amount: Money | None = Field(ge=0)
    currency: str | None
    cap_multiplier: Money | None = Field(ge=0)
    lookback_months: int | None = Field(ge=0)
    cap_formula: str | None
    exceptions: list[str] | None
    excluded_losses: list[str] | None
    indemnity_obligations: list[str] | None

class InsuranceRequirement(BaseModel):
    """One explicitly required insurance cover, not proof it was obtained."""
    model_config = ConfigDict(extra='forbid')
    insurance_type: str | None
    coverage_limit: Money | None = Field(ge=0)
    currency: str | None
    coverage_basis: str | None
    conditions: str | None

class InsuranceRequirements(BaseModel):
    """Required insurance covers and certificate duties, when stated."""
    model_config = ConfigDict(extra='forbid')
    requirements: list[InsuranceRequirement] | None
    certificate_requirements: str | None

class AssignmentAndSubcontracting(BaseModel):
    """Transfer/delegation restrictions; silence does not imply permission."""
    model_config = ConfigDict(extra='forbid')
    assignment_allowed: bool | None
    assignment_conditions: str | None
    subcontracting_allowed: bool | None
    subcontracting_conditions: str | None
    consent_required: bool | None
    change_of_control: str | None

class ServiceAgreement(BaseModel):
    """Customer-provider agreement; unknowns remain null."""
    model_config = ConfigDict(extra='forbid')
    contract_type: Literal['service_agreement'] = 'service_agreement'
    start_date: date | None
    customer: str | None = Field(description='Legal name of the customer buying or receiving the contracted services; otherwise null')
    vendor: str | None = Field(description='Legal name of the supplier/provider; otherwise null')
    end_date: date | None = Field(description='Controlling agreement expiry date; otherwise null')
    contract_id: str | None = Field(description='Agreement reference explicitly stated in the PDF; otherwise null')
    payment_terms: PaymentTerms | None
    renewal_terms: RenewalTerms | None
    fees_and_pricing: FeesAndPricing | None
    termination_terms: TerminationTerms | None
    scope: Scope | None
    service_levels: list[ServiceLevel] | None
    execution_status: ExecutionStatus | None
    amendments: list[Amendment] | None
    liability_and_indemnity: LiabilityAndIndemnity | None
    confidentiality_and_data_protection: ConfidentialityAndDataProtection | None
    governing_law_and_disputes: GoverningLawAndDisputes | None
    insurance_requirements: InsuranceRequirements | None
    assignment_and_subcontracting: AssignmentAndSubcontracting | None
