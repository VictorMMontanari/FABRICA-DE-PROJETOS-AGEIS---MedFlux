from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.constants import Severity, VectorCollection
from app.utils.validators import clean_text


class VectorItem(BaseModel):
    id: str
    collection: str
    payload: dict[str, Any]
    vector: list[float] | None = None
    score: float | None = None


class VectorSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500, examples=["febre alta e manchas vermelhas"])
    collection: VectorCollection = VectorCollection.DISEASES
    limit: int = Field(default=5, ge=1, le=20)
    score_threshold: float | None = Field(default=None, ge=0, le=1)
    with_vector: bool = False

    @field_validator("query")
    @classmethod
    def _query(cls, value: str) -> str:
        return clean_text(value)


class VectorSearchResponse(BaseModel):
    query: str
    collection: str
    results: list[VectorItem]


class DiseaseIndexRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160, examples=["Dengue"])
    description: str = Field(min_length=10, max_length=4000)
    symptoms: list[str] = Field(min_length=1, max_length=40)
    recommended_unit: Literal["UPA", "UBS"] | None = None
    severity: Severity | None = None

    @field_validator("name", "description")
    @classmethod
    def _text(cls, value: str) -> str:
        return clean_text(value)

    @field_validator("symptoms")
    @classmethod
    def _symptoms(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("Informe ao menos um sintoma.")
        return cleaned


class DiseaseIndexResponse(BaseModel):
    id: str
    name: str
    description: str
    symptoms: list[str]
    recommended_unit: str | None
    severity: str | None
    collection: str
    vector_id: str
    created_at: datetime
    updated_at: datetime
