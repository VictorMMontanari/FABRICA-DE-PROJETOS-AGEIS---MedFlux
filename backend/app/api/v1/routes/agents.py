from fastapi import APIRouter, Query, status

from app.api.v1.deps import AgentServiceDep, CurrentUser
from app.schemas.agent import AgentEventRequest, AgentEventResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/history", response_model=AgentEventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(data: AgentEventRequest, user: CurrentUser, agents: AgentServiceDep) -> AgentEventResponse:
    event = await agents.record_event(user, data)
    return AgentEventResponse.model_validate(event, from_attributes=True)


@router.get("/history", response_model=list[AgentEventResponse])
async def list_events(
    user: CurrentUser, agents: AgentServiceDep, limit: int = Query(default=50, ge=1, le=200)
) -> list[AgentEventResponse]:
    return [AgentEventResponse.model_validate(e, from_attributes=True) for e in await agents.list_events(user, limit)]
