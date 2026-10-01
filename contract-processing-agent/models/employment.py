"""Employment contract structures and source-supported nullable facts."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema, model_validator

from models.common import Money, Amendment, ConfidentialityAndDataProtection, ExecutionStatus, GoverningLawAndDisputes

class EmploymentTerms(BaseModel):
    """Role and engagement details stated by employer and employee."""
    model_config = ConfigDict(extra='forbid')
    job_title: str | None
    employment_type: Literal['permanent', 'fixed_term', 'temporary', 'part_time', 'other'] | None
    work_locations: list[str] | None
    responsibilities: list[str] | None
    reporting_to: str | None

class SalaryComponent(BaseModel):
    """One salary component; annual CTC is not automatically base or take-home salary."""
    model_config = ConfigDict(extra='forbid')
    description: str
    amount: Money | None = Field(ge=0)
    frequency: str | None
    conditions: str | None

class Compensation(BaseModel):
    """Source salary, CTC, incentives and benefits; no inferred payroll calculations."""
    model_config = ConfigDict(extra='forbid')
    currency: str | None
    base_salary: Money | None = Field(ge=0)
    salary_period: Literal['hourly', 'daily', 'weekly', 'monthly', 'annual', 'other'] | None
    annual_ctc: Money | None = Field(ge=0)
    annual_fixed_gross_salary: Money | None = Field(default=None, ge=0)
    annual_fixed_ctc: Money | None = Field(default=None, ge=0)
    components: list[SalaryComponent] | None
    bonus_terms: str | None
    benefits: list[str] | None
    payment_schedule: str | None
    deductions: str | None

class Probation(BaseModel):
    """Probation duration, extension and confirmation requirements."""
    model_config = ConfigDict(extra='forbid')
    duration: int | None = Field(ge=0)
    unit: Literal['days', 'months', 'years'] | None
    extension_terms: str | None
    confirmation_terms: str | None

class WorkingHoursAndLeave(BaseModel):
    """Hours and leave explicitly stated, not assumed statutory entitlements."""
    model_config = ConfigDict(extra='forbid')
    working_hours: str | None
    working_days: str | None
    overtime_terms: str | None
    leave_entitlements: list[str] | None
    holidays: str | None

class EmploymentExitRule(BaseModel):
    """One resignation/employer exit rule, including probation-specific differences."""
    model_config = ConfigDict(extra='forbid')
    initiated_by: Literal['employee', 'employer', 'either'] | None
    grounds: str | None
    applies_during: str | None
    notice_duration: int | None = Field(ge=0)
    notice_unit: Literal['days', 'weeks', 'months'] | None
    day_basis: Literal['calendar', 'business', 'unspecified'] | None
    payment_in_lieu: str | None
    conditions: str | None

    @model_validator(mode='after')
    def clear_missing_notice_units(self):
        """A missing notice duration has no unit or day basis; explicit zero is retained."""
        if self.notice_duration is None:
            self.notice_unit = None
            self.day_basis = None
        return self

class EmploymentTermination(BaseModel):
    """Separate employee resignation and employer termination routes."""
    model_config = ConfigDict(extra='forbid')
    rules: list[EmploymentExitRule]
    severance_terms: str | None
    final_settlement: str | None
    exit_obligations: list[str] | None

class IntellectualProperty(BaseModel):
    """Work-product ownership and pre-existing IP treatment."""
    model_config = ConfigDict(extra='forbid')
    ownership: str | None
    covered_work: str | None
    pre_existing_ip: str | None
    obligations: list[str] | None

class EmploymentRestrictions(BaseModel):
    """Stated restrictions only, without a legal-enforceability conclusion."""
    model_config = ConfigDict(extra='forbid')
    non_compete: str | None
    non_solicitation: str | None
    outside_employment: str | None
    conflicts_of_interest: str | None

class EmploymentContract(BaseModel):
    """Employment facts use employee/employer and compensation, never customer/vendor fees."""
    model_config = ConfigDict(extra='forbid')
    contract_type: Literal['employment_contract'] = 'employment_contract'
    contract_id: str | None
    employee: str | None
    employer: str | None
    start_date: date | None
    end_date: date | None
    employment_terms: EmploymentTerms | None
    compensation: Compensation | None
    probation: Probation | None
    working_hours_and_leave: WorkingHoursAndLeave | None
    termination_terms: EmploymentTermination | None
    confidentiality_and_data_protection: ConfidentialityAndDataProtection | None
    intellectual_property: IntellectualProperty | None
    restrictions: EmploymentRestrictions | None
    governing_law_and_disputes: GoverningLawAndDisputes | None
    execution_status: ExecutionStatus | None
    amendments: list[Amendment] | None
