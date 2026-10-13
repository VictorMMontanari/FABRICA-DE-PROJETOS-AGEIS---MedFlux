from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.disease_embedding import DiseaseEmbedding


class DiseaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_name(self, name: str) -> DiseaseEmbedding | None:
        result = await self.session.execute(select(DiseaseEmbedding).where(DiseaseEmbedding.name == name))
        return result.scalar_one_or_none()

    async def add(self, disease: DiseaseEmbedding) -> DiseaseEmbedding:
        self.session.add(disease)
        await self.session.flush()
        return disease
