"""Sessões e mensagens de triagem: persistência do chat e montagem das respostas para o frontend."""

from datetime import UTC, datetime

from app.core.constants import BRT, TRIAGE_STATUS_LABELS, MessageRole, TriageStatus
from app.core.exceptions import ConflictError, NotFoundError
from app.db.base import new_uuid, utcnow
from app.db.models.symptom_record import SymptomRecord
from app.db.models.triage_message import TriageMessage
from app.db.models.triage_session import TriageSession
from app.db.models.user import User
from app.db.repositories.triage_repository import TriageRepository
from app.schemas.triage import (
    TriageHistoryItem,
    TriageMessageItem,
    TriageMessageRequest,
    TriageMessageResponse,
    TriageRecommendation,
    TriageSessionCreate,
    TriageSessionDetail,
    TriageSessionResponse,
)
from app.services.agent_service import AgentService
from app.services.storage_service import StorageService

DEFAULT_TITLE = "Nova triagem"
HISTORY_WINDOW = 20
_MONTHS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def _local(moment: datetime) -> datetime:
    """Datas são gravadas em UTC sem fuso; exibição no horário de Brasília."""
    return moment.replace(tzinfo=UTC).astimezone(BRT)


def format_clock(moment: datetime) -> str:
    return _local(moment).strftime("%H:%M")


def format_relative(moment: datetime, now: datetime | None = None) -> str:
    """'Hoje, 14:30', 'Ontem, 09:10' ou '02 out, 18:05' (mesmo estilo do frontend)."""
    local = _local(moment)
    today = _local(now or utcnow()).date()
    days = (today - local.date()).days
    clock = local.strftime("%H:%M")
    if days == 0:
        return f"Hoje, {clock}"
    if days == 1:
        return f"Ontem, {clock}"
    return f"{local.day:02d} {_MONTHS[local.month - 1]}, {clock}"


def _title_from(message: str, symptoms: list[str]) -> str:
    if symptoms:
        return symptoms[0][:1].upper() + symptoms[0][1:]
    text = " ".join(message.split())
    return text if len(text) <= 60 else text[:57].rstrip() + "..."


def _session_response(session: TriageSession) -> TriageSessionResponse:
    return TriageSessionResponse(
        id=session.id,
        title=session.title,
        status=session.status,
        summary=session.summary,
        unit_type=session.unit_type,
        urgency_label=session.urgency_label,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


class TriageService:
    def __init__(self, repository: TriageRepository, agents: AgentService, storage: StorageService) -> None:
        self.repository = repository
        self.agents = agents
        self.storage = storage

    async def _owned_session(self, user: User, session_id: str) -> TriageSession:
        session = await self.repository.get_session(session_id)
        # 404 também para sessão de outro usuário: não revela que o id existe.
        if session is None or session.user_id != user.id:
            raise NotFoundError("Sessão de triagem não encontrada.")
        return session

    async def create_session(self, user: User, data: TriageSessionCreate) -> TriageSessionResponse:
        if data.session_id and await self.repository.get_session(data.session_id):
            raise ConflictError("Sessão já existe.", code="session_exists")
        session = TriageSession(
            id=data.session_id or new_uuid(),
            user_id=user.id,
            title=(data.title or "").strip() or DEFAULT_TITLE,
        )
        await self.repository.add(session)
        await self.repository.session.commit()
        return _session_response(session)

    async def handle_message(self, user: User, data: TriageMessageRequest) -> TriageMessageResponse:
        session = await self.repository.get_session(data.session_id)
        if session is None:
            # O frontend gera o id da sessão no navegador: a 1ª mensagem cria a sessão.
            session = TriageSession(id=data.session_id, user_id=user.id, title=DEFAULT_TITLE)
            await self.repository.add(session)
        elif session.user_id != user.id:
            raise NotFoundError("Sessão de triagem não encontrada.")

        history = await self.repository.list_messages(session.id, limit=HISTORY_WINDOW)
        await self.repository.add(TriageMessage(session_id=session.id, role=MessageRole.USER.value, content=data.message))

        outcome = await self.agents.run_triage(user, session, data.message, history)
        recommendation = outcome.decision.recommendation

        assistant_message = TriageMessage(
            session_id=session.id,
            role=MessageRole.ASSISTANT.value,
            content=outcome.decision.reply,
            recommendation=recommendation.model_dump() if recommendation else None,
        )
        await self.repository.add(assistant_message)

        if session.title == DEFAULT_TITLE:
            session.title = _title_from(data.message, outcome.analysis.symptoms)
        if recommendation:
            session.status = TriageStatus.COMPLETED.value
            session.unit_type = recommendation.unit_type
            session.urgency_label = recommendation.urgency_label
            session.summary = outcome.summary
            await self.repository.add(
                SymptomRecord(
                    user_id=user.id,
                    session_id=session.id,
                    description=data.message,
                    symptoms=outcome.analysis.symptoms,
                    severity=outcome.analysis.severity.value,
                    unit_type=recommendation.unit_type,
                )
            )
        session.updated_at = utcnow()
        await self.repository.session.commit()

        if recommendation:
            await self._archive(user, session)

        return TriageMessageResponse(
            session_id=session.id,
            message_id=assistant_message.id,
            reply=outcome.decision.reply,
            timestamp=format_clock(assistant_message.created_at),
            triage_recommendation=recommendation,
            source=outcome.decision.source,
        )

    async def history(self, user: User) -> list[TriageHistoryItem]:
        items = []
        for session in await self.repository.list_sessions(user.id):
            status_label = TRIAGE_STATUS_LABELS.get(TriageStatus(session.status), session.status)
            relative = format_relative(session.updated_at)
            items.append(
                TriageHistoryItem(
                    id=session.id,
                    title=session.title,
                    description=f"{f'Orientação para {session.unit_type}' if session.unit_type else status_label}"
                    f" • {relative}",
                    timestamp=relative,
                    status=f"Encaminhado para {session.unit_type}" if session.unit_type else status_label,
                    route="/chat",
                    status_code=session.status,
                    summary=session.summary,
                    unit_type=session.unit_type,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                )
            )
        return items

    async def session_detail(self, user: User, session_id: str) -> TriageSessionDetail:
        session = await self._owned_session(user, session_id)
        messages = await self.repository.list_messages(session.id)
        return TriageSessionDetail(
            **_session_response(session).model_dump(),
            messages=[
                TriageMessageItem(
                    id=message.id,
                    role=message.role,
                    content=message.content,
                    created_at=message.created_at,
                    timestamp=format_clock(message.created_at),
                    triage_recommendation=(
                        TriageRecommendation.model_validate(message.recommendation) if message.recommendation else None
                    ),
                )
                for message in messages
            ],
        )

    async def _archive(self, user: User, session: TriageSession) -> None:
        detail = await self.session_detail(user, session.id)
        await self.storage.archive_transcript_safely(user.id, session.id, detail.model_dump(mode="json"))
