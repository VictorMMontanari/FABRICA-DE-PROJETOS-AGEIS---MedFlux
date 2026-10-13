from typing import Literal

from fastapi import APIRouter, Query

from app.api.v1.deps import HealthUnitRepositoryDep
from app.schemas.health_unit import HealthUnitResponse

router = APIRouter(prefix="/health", tags=["health units"])


@router.get("/units", response_model=list[HealthUnitResponse])
async def list_units(
    units: HealthUnitRepositoryDep,
    unit_type: Literal["UPA", "UBS"] | None = Query(default=None, alias="type"),
) -> list[HealthUnitResponse]:
    """Unidades de saúde para o mapa. Público: não contém dados pessoais."""
    return [HealthUnitResponse.model_validate(unit) for unit in await units.list_active(unit_type)]
