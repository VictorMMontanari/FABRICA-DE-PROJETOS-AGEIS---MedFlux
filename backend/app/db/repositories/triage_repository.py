"""Persistência do domínio de triagem: sessões, mensagens, registros de sintomas e eventos de agentes."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_event import AgentEvent
from app.db.models.symptom_record import SymptomRecord
from app.db.models.triage_message import TriageMessage
from app.db.models.triage_session import TriageSession


class TriageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_session(self, session_id: str) -> TriageSession | None:
        return await self.session.get(TriageSession, session_id)

    async def add(self, entity: TriageSession | TriageMessage | SymptomRecord | AgentEvent) -> None:
        self.session.add(entity)
        await self.session.flush()

    async def list_sessions(self, user_id: str, limit: int = 50) -> Sequence[TriageSession]:
        result = await self.session.execute(
            select(TriageSession)
            .where(TriageSession.user_id == user_id)
            .order_by(TriageSession.updated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def list_messages(self, session_id: str, limit: int | None = None) -> Sequence[TriageMessage]:
        """Mensagens em ordem cronológica; com `limit`, apenas as últimas N."""
        query = select(TriageMessage).where(TriageMessage.session_id == session_id)
        if limit is None:
            result = await self.session.execute(query.order_by(TriageMessage.created_at, TriageMessage.id))
            return result.scalars().all()
        result = await self.session.execute(
            query.order_by(TriageMessage.created_at.desc(), TriageMessage.id.desc()).limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def list_agent_events(self, user_id: str, limit: int = 50) -> Sequence[AgentEvent]:
        result = await self.session.execute(
            select(AgentEvent).where(AgentEvent.user_id == user_id).order_by(AgentEvent.created_at.desc()).limit(limit)
        )
        return result.scalars().all()
