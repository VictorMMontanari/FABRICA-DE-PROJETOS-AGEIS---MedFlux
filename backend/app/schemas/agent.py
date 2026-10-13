from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.utils.validators import SESSION_ID_PATTERN


class AgentEventRequest(BaseModel):
    agent_name: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9_.-]+$", examples=["support_agent"])
    event_type: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9_.-]+$", examples=["note"])
    input_text: str | None = Field(default=None, max_length=4000)
    output: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = Field(default=None, pattern=SESSION_ID_PATTERN)


class AgentEventResponse(BaseModel):
    id: str
    agent_name: str
    event_type: str
    input_text: str | None
    output: dict[str, Any]
    session_id: str | None
    vector_id: str | None
    created_at: datetime
