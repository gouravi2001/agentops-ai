from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class IncidentStatus(str, Enum):
    open = "open"
    investigating = "investigating"
    awaiting_review = "awaiting_review"
    approved = "approved"
    rejected = "rejected"
    failed = "failed"

class Decision(str, Enum):
    approved = "approved"
    rejected = "rejected"

class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pipeline: str = Field(min_length=1, max_length=120)
    severity: Severity
    summary: str = Field(min_length=3, max_length=2000)
    observed_at: datetime
    labels: dict[str, str] = Field(default_factory=dict, max_length=30)

    @field_validator("pipeline")
    @classmethod
    def pipeline_trimmed(cls, value: str) -> str:
        return value.strip()

class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["retry_failed_task", "pause_pipeline", "notify_owner", "inspect_upstream"]
    rationale: str = Field(min_length=8, max_length=1200)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1, max_length=8)
    requires_approval: Literal[True] = True

class InvestigationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root_cause: str = Field(min_length=8, max_length=1200)
    confidence: float = Field(ge=0, le=1)
    evidence: list[dict[str, Any]] = Field(max_length=8)
    recommendation: Recommendation
    tool_calls: int = Field(ge=0, le=5)

class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Decision
    reviewer: str = Field(min_length=3, max_length=200)
    comment: str = Field(default="", max_length=1000)

class IncidentOut(BaseModel):
    id: str
    pipeline: str
    severity: Severity
    summary: str
    observed_at: datetime
    status: IncidentStatus
    labels: dict[str, str]
    investigation: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

class AuditOut(BaseModel):
    id: int
    incident_id: str
    event_type: str
    actor: str
    payload: dict[str, Any]
    created_at: datetime
