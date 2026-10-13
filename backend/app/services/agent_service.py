"""Orquestração dos agentes: contexto (histórico + Qdrant) -> sintomas -> triagem -> resumo -> persistência."""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from app.agents.base_agent import AgentContext
from app.agents.runtime import AgentRuntime
from app.agents.summarizer_agent import SummarizerAgent
from app.agents.symptoms_agent import SymptomAnalysis, SymptomsAgent
from app.agents.triage_agent import TriageAgent, TriageDecision
from app.core.constants import VectorCollection
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.models.agent_event import AgentEvent
from app.db.models.triage_message import TriageMessage
from app.db.models.triage_session import TriageSession
from app.db.models.user import User
from app.db.repositories.triage_repository import TriageRepository
from app.schemas.agent import AgentEventRequest
from app.services.prompt_service import PromptService
from app.services.vector_service import VectorService

logger = get_logger(__name__)


@dataclass
class TriageOutcome:
    analysis: SymptomAnalysis
    decision: TriageDecision
    summary: str | None


class AgentService:
    def __init__(
        self,
        repository: TriageRepository,
        vectors: VectorService,
        runtime: AgentRuntime,
        prompts: PromptService | None = None,
    ) -> None:
        self.repository = repository
        self.vectors = vectors
        self.runtime = runtime
        prompts = prompts or PromptService()
        self.symptoms_agent = SymptomsAgent(runtime, prompts)
        self.triage_agent = TriageAgent(runtime, prompts)
        self.summarizer_agent = SummarizerAgent(runtime, prompts)

    async def run_triage(
        self, user: User, session: TriageSession, message: str, history: Sequence[TriageMessage]
    ) -> TriageOutcome:
        retrieved = await self.vectors.retrieve_context(message, user.id)
        ctx = AgentContext(
            user_id=user.id,
            user_name=user.name,
            session_id=session.id,
            message=message,
            history=[{"role": item.role, "content": item.content} for item in history],
            diseases=retrieved.diseases,
            past_queries=retrieved.past_queries,
        )

        analysis = await self.symptoms_agent.run(ctx)
        decision = await self.triage_agent.run(ctx, analysis)
        summary = await self.summarizer_agent.run(ctx, analysis, decision) if decision.recommendation else None

        await self._store_event(
            user.id, session.id, self.symptoms_agent.name, "symptoms_analyzed", message, asdict(analysis), index=False
        )
        recommendation = decision.recommendation.model_dump() if decision.recommendation else None
        await self._store_event(
            user.id,
            session.id,
            self.triage_agent.name,
            "triage_decided",
            message,
            {"reply": decision.reply, "recommendation": recommendation, "source": decision.source},
        )
        if summary:
            await self._store_event(
                user.id, session.id, self.summarizer_agent.name, "session_summarized", message, {"summary": summary}
            )

        await self.vectors.index_safely(
            VectorCollection.USER_QUERIES,
            message,
            {
                "user_id": user.id,
                "session_id": session.id,
                "symptoms": analysis.symptoms,
                "severity": analysis.severity.value,
            },
        )
        logger.info(
            "triage_completed",
            extra={
                "session_id": session.id,
                "runtime": self.runtime.name,
                "severity": analysis.severity.value,
                "unit_type": decision.recommendation.unit_type if decision.recommendation else None,
                "source": decision.source,
            },
        )
        return TriageOutcome(analysis=analysis, decision=decision, summary=summary)

    async def record_event(self, user: User, data: AgentEventRequest) -> AgentEvent:
        """Registro manual de evento (POST /agents/history), salvo no MySQL e indexado no Qdrant."""
        if data.session_id:
            session = await self.repository.get_session(data.session_id)
            if session is None or session.user_id != user.id:
                raise NotFoundError("Sessão de triagem não encontrada.")
        event = await self._store_event(
            user.id, data.session_id, data.agent_name, data.event_type, data.input_text, data.output
        )
        await self.repository.session.commit()
        return event

    async def list_events(self, user: User, limit: int = 50) -> Sequence[AgentEvent]:
        return await self.repository.list_agent_events(user.id, limit)

    async def _store_event(
        self,
        user_id: str,
        session_id: str | None,
        agent_name: str,
        event_type: str,
        input_text: str | None,
        output: dict[str, Any],
        *,
        index: bool = True,
    ) -> AgentEvent:
        event = AgentEvent(
            user_id=user_id,
            session_id=session_id,
            agent_name=agent_name,
            event_type=event_type,
            input_text=input_text,
            output=output,
        )
        if index:
            text = " ".join(filter(None, [f"{agent_name} {event_type}", input_text, _describe(output)]))
            event.vector_id = await self.vectors.index_safely(
                VectorCollection.AGENT_HISTORY,
                text,
                {"user_id": user_id, "session_id": session_id, "agent_name": agent_name, "event_type": event_type},
            )
        await self.repository.add(event)
        return event


def _describe(output: dict[str, Any]) -> str:
    """Texto indexável de um output de agente (valores textuais, sem as chaves)."""
    parts: list[str] = []
    for value in output.values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            parts.append(_describe(value))
    return " ".join(parts)[:2000]
