from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.health_unit import HealthUnit


class HealthUnitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self, unit_type: str | None = None) -> Sequence[HealthUnit]:
        query = select(HealthUnit).where(HealthUnit.is_active.is_(True)).order_by(HealthUnit.type, HealthUnit.name)
        if unit_type:
            query = query.where(HealthUnit.type == unit_type)
        result = await self.session.execute(query)
        return result.scalars().all()
