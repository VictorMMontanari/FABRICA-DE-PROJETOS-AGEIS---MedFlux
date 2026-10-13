"""Importa todos os modelos para registrá-los no metadata (usado pelo Alembic)."""

from app.db.models.agent_event import AgentEvent
from app.db.models.disease_embedding import DiseaseEmbedding
from app.db.models.health_unit import HealthUnit
from app.db.models.symptom_record import SymptomRecord
from app.db.models.triage_message import TriageMessage
from app.db.models.triage_session import TriageSession
from app.db.models.user import User

__all__ = [
    "AgentEvent",
    "DiseaseEmbedding",
    "HealthUnit",
    "SymptomRecord",
    "TriageMessage",
    "TriageSession",
    "User",
]
