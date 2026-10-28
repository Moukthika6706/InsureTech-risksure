"""API request/response shapes (also drive the interactive docs at /docs)."""
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class QuoteRequest(BaseModel):
    product: str
    applicant: dict[str, Any]
    coverages: Optional[list[str]] = None     # optional covers; mandatory ones are always added
    actor: str = "customer"


class ActorRequest(BaseModel):
    actor: str = "customer"


class IssueRequest(ActorRequest):
    start_date: Optional[date] = None         # defaults to today


class UnderwriteRequest(BaseModel):
    action: Literal["approve", "decline"]
    note: str = Field(min_length=3, description="Why — recorded in the audit trail")
    override_premium: Optional[float] = Field(None, gt=0, description="Only with approve")
    actor: str = "underwriter"


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quote_id: int
    action: str
    from_status: Optional[str]
    to_status: str
    actor: str
    detail: dict
    created_at: datetime


class PolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    policy_number: str
    quote_id: int
    product: str
    premium: float
    start_date: date
    end_date: date
    issued_at: datetime


class QuoteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quote_number: str
    product: str
    status: str
    decision: Optional[str]
    premium: Optional[float]
    override_premium: Optional[float]
    final_premium: Optional[float]
    risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    rule_hits: list[dict]
    created_at: datetime
    updated_at: datetime


class QuoteDetail(QuoteSummary):
    product_version: str
    applicant_id: int
    applicant: dict
    coverages: list[dict]
    base_premium: Optional[float]
    rated_premium: Optional[float]
    total_load_pct: float
    breakdown: list[dict]
    risk: dict
    underwriter_note: Optional[str]
    policy: Optional[PolicyOut] = None
    events: list[AuditEventOut] = []
