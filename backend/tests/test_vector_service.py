from typing import Any

import httpx
import pytest

from app.core.constants import Severity, VectorCollection
from app.schemas.vector import DiseaseIndexRequest
from app.services.vector_service import VectorService
from app.utils.embeddings import embed_text, normalize_text
from tests.conftest import auth_headers, make_admin, register

pytestmark = pytest.mark.anyio

DISEASES = [
    DiseaseIndexRequest(
        name="Dengue",
        description="Arbovirose transmitida pelo mosquito Aedes aegypti.",
        symptoms=["febre alta", "dor atrás dos olhos", "manchas vermelhas", "dor no corpo"],
        recommended_unit="UPA",
        severity=Severity.URGENT,
    ),
    DiseaseIndexRequest(
        name="Infecção urinária",
        description="Infecção bacteriana do trato urinário.",
        symptoms=["dor ao urinar", "ardência ao urinar", "urina turva"],
        recommended_unit="UBS",
        severity=Severity.MODERATE,
    ),
    DiseaseIndexRequest(
        name="Resfriado comum",
        description="Infecção viral leve das vias aéreas superiores.",
        symptoms=["coriza", "espirros", "dor de garganta", "nariz entupido"],
        recommended_unit="UBS",
        severity=Severity.MILD,
    ),
]


def test_embeddings_are_deterministic_and_normalized() -> None:
    first, second = embed_text("Febre alta e manchas", 64), embed_text("febre ALTA e mánchas", 64)
    assert first == second
    assert abs(sum(value * value for value in first) - 1.0) < 1e-9
    assert normalize_text("Dor  de Cabeça!") == "dor de cabeca"
    assert embed_text("", 16)[0] == 1.0


async def test_vector_search_with_qdrant(app: Any) -> None:
    async with app.state.session_factory() as session:
        from app.db.repositories.disease_repository import DiseaseRepository

        service = VectorService(app.state.vector_repository, app.state.settings.EMBEDDING_DIM, DiseaseRepository(session))
        for disease in DISEASES:
            await service.index_disease(disease)
        await session.commit()

        results = await service.search(VectorCollection.DISEASES, "estou com febre alta e manchas vermelhas na pele")
        assert results[0].payload["name"] == "Dengue"
        assert results[0].score is not None and results[0].score > results[-1].score

        urinary = await service.search(VectorCollection.DISEASES, "sinto ardência ao urinar", limit=1, with_vector=True)
        assert urinary[0].payload["name"] == "Infecção urinária"
        assert urinary[0].vector is not None and len(urinary[0].vector) == app.state.settings.EMBEDDING_DIM

        # Reindexar a mesma doença atualiza o ponto (id estável), sem duplicar.
        await service.index_disease(DISEASES[0])
        await session.commit()
        count = await app.state.vector_repository.client.count(VectorCollection.DISEASES)
        assert count.count == len(DISEASES)


async def test_user_scoped_collections_are_isolated(app: Any) -> None:
    service = VectorService(app.state.vector_repository, app.state.settings.EMBEDDING_DIM)
    await service.index(VectorCollection.USER_QUERIES, "dor de cabeça forte", {"user_id": "user-a"})
    await service.index(VectorCollection.USER_QUERIES, "dor de cabeça forte", {"user_id": "user-b"})

    results = await service.search(VectorCollection.USER_QUERIES, "dor de cabeça", user_id="user-a")
    assert [item.payload["user_id"] for item in results] == ["user-a"]
    with pytest.raises(ValueError):
        await service.search(VectorCollection.USER_QUERIES, "dor de cabeça")


async def test_vector_endpoints(app: Any, client: httpx.AsyncClient) -> None:
    session = await register(client)
    headers = auth_headers(session)
    payload = DISEASES[0].model_dump(mode="json")

    forbidden = await client.post("/api/v1/vector/index-disease", json=payload, headers=headers)
    assert forbidden.status_code == 403

    await make_admin(app, session["user"]["id"])
    indexed = await client.post("/api/v1/vector/index-disease", json=payload, headers=headers)
    assert indexed.status_code == 201, indexed.text
    assert indexed.json()["collection"] == "diseases"
    assert indexed.json()["vector_id"]

    search = await client.post(
        "/api/v1/vector/search", json={"query": "febre alta com manchas", "limit": 3}, headers=headers
    )
    assert search.status_code == 200
    body = search.json()
    assert body["collection"] == "diseases"
    assert body["results"][0]["payload"]["name"] == "Dengue"
    assert set(body["results"][0]) == {"id", "collection", "payload", "vector", "score"}

    invalid = await client.post("/api/v1/vector/search", json={"query": "x", "collection": "nao-existe"}, headers=headers)
    assert invalid.status_code == 422
