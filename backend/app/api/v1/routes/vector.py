from fastapi import APIRouter, status

from app.api.v1.deps import AdminUser, CurrentUser, DbSession, VectorServiceDep
from app.schemas.vector import DiseaseIndexRequest, DiseaseIndexResponse, VectorSearchRequest, VectorSearchResponse

router = APIRouter(prefix="/vector", tags=["vector"])


@router.post("/index-disease", response_model=DiseaseIndexResponse, status_code=status.HTTP_201_CREATED)
async def index_disease(
    data: DiseaseIndexRequest, _: AdminUser, db: DbSession, vectors: VectorServiceDep
) -> DiseaseIndexResponse:
    """Adiciona/atualiza uma doença na base de conhecimento (MySQL + Qdrant). Restrito a administradores."""
    disease = await vectors.index_disease(data)
    await db.commit()
    return DiseaseIndexResponse.model_validate(disease, from_attributes=True)


@router.post("/search", response_model=VectorSearchResponse)
async def search(data: VectorSearchRequest, user: CurrentUser, vectors: VectorServiceDep) -> VectorSearchResponse:
    """Busca por similaridade. Em coleções com dados pessoais, retorna apenas itens do próprio usuário."""
    results = await vectors.search(
        data.collection,
        data.query,
        limit=data.limit,
        user_id=user.id,
        score_threshold=data.score_threshold,
        with_vector=data.with_vector,
    )
    return VectorSearchResponse(query=data.query, collection=data.collection, results=results)
