from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.utils.validators import SESSION_ID_PATTERN, clean_text


class TriageRecommendation(BaseModel):
    """Contrato fixo consumido pelo card de triagem do frontend."""

    required: bool
    unit_type: Literal["UPA", "UBS"]
    urgency_label: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=600)
    warning: str = Field(min_length=1, max_length=400)


class TriageSessionCreate(BaseModel):
    session_id: str | None = Field(default=None, pattern=SESSION_ID_PATTERN)
    title: str | None = Field(default=None, max_length=160)


class TriageSessionResponse(BaseModel):
    id: str
    title: str
    status: str
    summary: str | None
    unit_type: str | None
    urgency_label: str | None
    created_at: datetime
    updated_at: datetime


class TriageMessageRequest(BaseModel):
    session_id: str = Field(pattern=SESSION_ID_PATTERN, examples=["3f1c2a8e-8d5b-4c1e-9f0a-1b2c3d4e5f60"])
    message: str = Field(min_length=1, max_length=2000, examples=["Estou com febre e dor de cabeça desde ontem"])

    @field_validator("message")
    @classmethod
    def _message(cls, value: str) -> str:
        return clean_text(value)


class TriageMessageResponse(BaseModel):
    session_id: str
    message_id: str
    reply: str
    timestamp: str
    triage_recommendation: TriageRecommendation | None
    source: Literal["llm", "fallback"]


class TriageMessageItem(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    timestamp: str
    triage_recommendation: TriageRecommendation | None = None


class TriageSessionDetail(TriageSessionResponse):
    messages: list[TriageMessageItem]


class TriageHistoryItem(BaseModel):
    """Campos `title/description/timestamp/status/route` seguem o tipo TriageHistoryItem do frontend."""

    id: str
    title: str
    description: str
    timestamp: str
    status: str
    route: str
    status_code: str
    summary: str | None
    unit_type: str | None
    created_at: datetime
    updated_at: datetime
