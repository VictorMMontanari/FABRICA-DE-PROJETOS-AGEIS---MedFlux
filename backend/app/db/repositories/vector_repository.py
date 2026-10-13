"""Acesso ao Qdrant: coleções, upsert e busca por similaridade."""

from collections.abc import Iterable
from typing import Any

from qdrant_client import AsyncQdrantClient, models

from app.core.constants import USER_SCOPED_COLLECTIONS


class VectorRepository:
    def __init__(self, client: AsyncQdrantClient, dim: int) -> None:
        self.client = client
        self.dim = dim

    async def ensure_collections(self, names: Iterable[str]) -> None:
        for name in names:
            if await self.client.collection_exists(name):
                continue
            await self.client.create_collection(
                name, vectors_config=models.VectorParams(size=self.dim, distance=models.Distance.COSINE)
            )
            if name in USER_SCOPED_COLLECTIONS:
                await self.client.create_payload_index(name, "user_id", models.PayloadSchemaType.KEYWORD)

    async def upsert(self, collection: str, point_id: str, vector: list[float], payload: dict[str, Any]) -> None:
        await self.client.upsert(
            collection, points=[models.PointStruct(id=point_id, vector=vector, payload=payload)], wait=True
        )

    async def search(
        self,
        collection: str,
        vector: list[float],
        *,
        limit: int = 5,
        filters: dict[str, str] | None = None,
        score_threshold: float | None = None,
        with_vectors: bool = False,
    ) -> list[models.ScoredPoint]:
        query_filter = None
        if filters:
            query_filter = models.Filter(
                must=[models.FieldCondition(key=k, match=models.MatchValue(value=v)) for k, v in filters.items()]
            )
        response = await self.client.query_points(
            collection,
            query=vector,
            limit=limit,
            query_filter=query_filter,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=with_vectors,
        )
        return response.points
