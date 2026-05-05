from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class _ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CallAnalysisOut(_ORMBase):
    id: int
    outcome: str
    confidence: float
    reasoning: str
    flags: list[str]
    requires_review: bool
    created_at: datetime


class HumanReviewOut(_ORMBase):
    id: int
    action: str
    final_outcome: str
    notes: str
    reviewer_name: str
    reviewed_at: datetime


class CallSummaryOut(BaseModel):
    id: str
    external_id: str
    goal: str
    metadata: dict
    created_at: datetime
    latest_analysis: Optional[CallAnalysisOut] = None
    latest_review: Optional[HumanReviewOut] = None
    is_reviewed: bool = False


class CallDetailOut(CallSummaryOut):
    transcript: str
    analyses: list[CallAnalysisOut] = []


class StatsOut(BaseModel):
    total: int
    pending_review: int
    reviewed_today: int
    analyzed: int
    not_analyzed: int


class ReviewIn(BaseModel):
    action: str  # accept | reject | modify
    final_outcome: str
    notes: str = ""
    reviewer_name: str = ""


class IngestCallIn(BaseModel):
    id: str
    goal: str
    transcript: str
    metadata: dict = Field(default_factory=dict)


class IngestBatchIn(BaseModel):
    calls: list[IngestCallIn]


class IngestOut(BaseModel):
    created: int
    skipped: int
    errors: list[dict]
