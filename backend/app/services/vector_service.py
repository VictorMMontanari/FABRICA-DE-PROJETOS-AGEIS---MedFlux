"""Banco vetorial: indexação, busca por similaridade e recuperação de contexto para os agentes."""

from dataclasses import dataclass, field
from typing import Any

from app.core.constants import USER_SCOPED_COLLECTIONS, VectorCollection
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger
from app.db.base import new_uuid, utcnow
from app.db.models.disease_embedding import DiseaseEmbedding
from app.db.repositories.disease_repository import DiseaseRepository
from app.db.repositories.vector_repository import VectorRepository
from app.schemas.vector import DiseaseIndexRequest, VectorItem
from app.utils.embeddings import embed_text, normalize_text
from app.utils.hash_utils import stable_uuid

logger = get_logger(__name__)


@dataclass
class RetrievedContext:
    diseases: list[dict[str, Any]] = field(default_factory=list)
    past_queries: list[str] = field(default_factory=list)


class VectorService:
    def __init__(
        self, repository: VectorRepository | None, dim: int, diseases: DiseaseRepository | None = None
    ) -> None:
        self.repository = repository
        self.dim = dim
        self.diseases = diseases

    def _repo(self) -> VectorRepository:
        if self.repository is None:
            raise ServiceUnavailableError("Banco vetorial indisponível.")
        return self.repository

    async def index(
        self, collection: str, text: str, payload: dict[str, Any], point_id: str | None = None
    ) -> VectorItem:
        vector = embed_text(text, self.dim)
        point_id = point_id or new_uuid()
        full_payload = {**payload, "text": text, "indexed_at": utcnow().isoformat()}
        try:
            await self._repo().upsert(collection, point_id, vector, full_payload)
        except ServiceUnavailableError:
            raise
        except Exception as exc:
            logger.warning("vector_index_failed", extra={"collection": collection, "error": type(exc).__name__})
            raise ServiceUnavailableError("Banco vetorial indisponível.") from exc
        return VectorItem(id=point_id, collection=collection, payload=full_payload, vector=vector)

    async def index_safely(self, collection: str, text: str, payload: dict[str, Any]) -> str | None:
        """Indexação best-effort: o fluxo principal (ex.: chat) não falha se o Qdrant estiver fora."""
        try:
            return (await self.index(collection, text, payload)).id
        except ServiceUnavailableError:
            return None

    async def search(
        self,
        collection: str,
        query: str,
        *,
        limit: int = 5,
        user_id: str | None = None,
        score_threshold: float | None = None,
        with_vector: bool = False,
    ) -> list[VectorItem]:
        if collection in USER_SCOPED_COLLECTIONS and not user_id:
            raise ValueError("Coleções com dados de usuário exigem user_id.")
        filters = {"user_id": user_id} if collection in USER_SCOPED_COLLECTIONS and user_id else None
        try:
            points = await self._repo().search(
                collection,
                embed_text(query, self.dim),
                limit=limit,
                filters=filters,
                score_threshold=score_threshold,
                with_vectors=with_vector,
            )
        except ServiceUnavailableError:
            raise
        except Exception as exc:
            logger.warning("vector_search_failed", extra={"collection": collection, "error": type(exc).__name__})
            raise ServiceUnavailableError("Banco vetorial indisponível.") from exc

        return [
            VectorItem(
                id=str(point.id),
                collection=collection,
                payload=point.payload or {},
                vector=point.vector if with_vector and isinstance(point.vector, list) else None,
                score=round(point.score, 4),
            )
            for point in points
        ]

    async def retrieve_context(self, query: str, user_id: str) -> RetrievedContext:
        """Contexto para os agentes: doenças semelhantes + relatos anteriores do usuário. Nunca lança erro."""
        context = RetrievedContext()
        try:
            diseases = await self.search(VectorCollection.DISEASES, query, limit=3, score_threshold=0.15)
            context.diseases = [item.payload for item in diseases]
            past = await self.search(
                VectorCollection.USER_QUERIES, query, limit=3, user_id=user_id, score_threshold=0.3
            )
            context.past_queries = [str(item.payload.get("text", "")) for item in past if item.payload.get("text")]
        except ServiceUnavailableError:
            logger.info("vector_context_unavailable")
        return context

    async def index_disease(self, data: DiseaseIndexRequest) -> DiseaseEmbedding:
        """Grava/atualiza a doença no MySQL e o vetor no Qdrant (id estável: reindexar não duplica)."""
        if self.diseases is None:
            raise RuntimeError("DiseaseRepository não configurado.")

        vector_id = stable_uuid("disease", normalize_text(data.name))
        disease = await self.diseases.get_by_name(data.name)
        if disease is None:
            disease = DiseaseEmbedding(name=data.name, collection=VectorCollection.DISEASES.value, vector_id=vector_id)
        disease.description = data.description
        disease.symptoms = data.symptoms
        disease.recommended_unit = data.recommended_unit
        disease.severity = data.severity.value if data.severity else None
        await self.diseases.add(disease)

        text = f"{data.name}. {data.description} Sintomas: {', '.join(data.symptoms)}."
        payload = {
            "disease_id": disease.id,
            "name": data.name,
            "description": data.description,
            "symptoms": data.symptoms,
            "recommended_unit": disease.recommended_unit,
            "severity": disease.severity,
        }
        await self.index(VectorCollection.DISEASES, text, payload, point_id=disease.vector_id)
        return disease
