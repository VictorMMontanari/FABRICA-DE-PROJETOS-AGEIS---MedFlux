from fastapi import APIRouter, Path, status

from app.api.v1.deps import CurrentUser, TriageServiceDep
from app.schemas.triage import (
    TriageHistoryItem,
    TriageMessageRequest,
    TriageMessageResponse,
    TriageSessionCreate,
    TriageSessionDetail,
    TriageSessionResponse,
)
from app.utils.validators import SESSION_ID_PATTERN

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("/session", response_model=TriageSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: TriageSessionCreate, user: CurrentUser, triage: TriageServiceDep
) -> TriageSessionResponse:
    return await triage.create_session(user, data)


@router.post("/message", response_model=TriageMessageResponse)
async def send_message(
    data: TriageMessageRequest, user: CurrentUser, triage: TriageServiceDep
) -> TriageMessageResponse:
    """Envia uma mensagem ao chat. Se a sessão ainda não existir, ela é criada com o id informado."""
    return await triage.handle_message(user, data)


@router.get("/history", response_model=list[TriageHistoryItem])
async def history(user: CurrentUser, triage: TriageServiceDep) -> list[TriageHistoryItem]:
    return await triage.history(user)


@router.get("/session/{session_id}", response_model=TriageSessionDetail)
async def session_detail(
    user: CurrentUser,
    triage: TriageServiceDep,
    session_id: str = Path(pattern=SESSION_ID_PATTERN),
) -> TriageSessionDetail:
    return await triage.session_detail(user, session_id)
