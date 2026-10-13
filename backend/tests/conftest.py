"""Fixtures: app com SQLite em memória, Qdrant em memória, MinIO/Redis falsos e OpenRouter mockado."""

import json
from collections.abc import AsyncIterator, Callable
from datetime import timedelta
from typing import Any

import httpx
import pytest
from qdrant_client import AsyncQdrantClient
from sqlalchemy import update

from app.agents.runtime import CustomRuntime
from app.core.config import Settings
from app.core.constants import VectorCollection
from app.db.base import Base
from app.db.models.health_unit import HealthUnit
from app.db.models.user import User
from app.db.repositories.file_repository import StoredObject
from app.db.repositories.vector_repository import VectorRepository
from app.db.session import create_engine, create_session_factory
from app.integrations.openrouter_client import OpenRouterClient
from app.main import create_app
from app.services.ai_service import AIService

OpenRouterHandler = Callable[[dict[str, Any]], httpx.Response]


class FakeFileRepository:
    """Substitui o MinIO: guarda objetos num dicionário {(bucket, nome): StoredObject}."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], StoredObject] = {}

    async def ensure_buckets(self, buckets: list[str]) -> None:
        return None

    async def put(self, bucket: str, object_name: str, data: bytes, content_type: str) -> None:
        self.objects[(str(bucket), object_name)] = StoredObject(data=data, content_type=content_type)

    async def get(self, bucket: str, object_name: str) -> StoredObject | None:
        return self.objects.get((str(bucket), object_name))

    async def remove(self, bucket: str, object_name: str) -> None:
        self.objects.pop((str(bucket), object_name), None)

    def presigned_get_url(self, bucket: str, object_name: str, expires: timedelta) -> str:
        return f"http://minio.test/{bucket}/{object_name}?X-Amz-Expires={int(expires.total_seconds())}"


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, int] = {}

    async def get(self, key: str) -> int | None:
        return self.data.get(key)

    async def incr(self, key: str) -> int:
        self.data[key] = self.data.get(key, 0) + 1
        return self.data[key]

    async def expire(self, key: str, seconds: int) -> bool:
        return True

    async def delete(self, key: str) -> int:
        return 1 if self.data.pop(key, None) is not None else 0


def chat_completion(content: str | dict[str, Any]) -> httpx.Response:
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": text}}]})


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def openrouter_api_key() -> str:
    """Vazio = OpenRouter desligado (fallback). Testes de integração sobrescrevem esta fixture."""
    return ""


@pytest.fixture
def openrouter_handler() -> OpenRouterHandler:
    def handler(_: dict[str, Any]) -> httpx.Response:
        return httpx.Response(503, json={"error": "indisponível"})

    return handler


@pytest.fixture
def openrouter_calls() -> list[dict[str, Any]]:
    return []


@pytest.fixture
def settings(openrouter_api_key: str) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        APP_ENV="test",
        LOG_LEVEL="WARNING",
        DATABASE_URL="sqlite+aiosqlite://",
        JWT_SECRET_KEY="test-secret-key-with-more-than-32-characters",
        BCRYPT_ROUNDS=4,
        MINIO_ACCESS_KEY="test",
        MINIO_SECRET_KEY="test",
        OPENROUTER_API_KEY=openrouter_api_key,
        EMBEDDING_DIM=128,
    )


@pytest.fixture
def fake_files() -> FakeFileRepository:
    return FakeFileRepository()


@pytest.fixture
async def app(
    settings: Settings,
    fake_files: FakeFileRepository,
    openrouter_handler: OpenRouterHandler,
    openrouter_calls: list[dict[str, Any]],
) -> AsyncIterator[Any]:
    application = create_app(settings, with_lifespan=False)

    engine = create_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        session.add_all(
            [
                HealthUnit(id="upa-sul", name="UPA Sul", type="UPA", address="R. A, 1", latitude=-22.22, longitude=-49.95),
                HealthUnit(id="ubs-1", name="UBS Centro", type="UBS", address="R. B, 2", latitude=-22.21, longitude=-49.94),
            ]
        )
        await session.commit()

    def transport_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        openrouter_calls.append(body)
        return openrouter_handler(body)

    http = httpx.AsyncClient(transport=httpx.MockTransport(transport_handler))
    qdrant = AsyncQdrantClient(location=":memory:")
    vector_repository = VectorRepository(qdrant, settings.EMBEDDING_DIM)
    await vector_repository.ensure_collections(VectorCollection)

    application.state.engine = engine
    application.state.session_factory = session_factory
    application.state.vector_repository = vector_repository
    application.state.file_repository = fake_files
    application.state.redis = None
    application.state.agent_runtime = CustomRuntime(AIService(OpenRouterClient(http, settings)))

    yield application

    await http.aclose()
    await qdrant.close()
    await engine.dispose()


@pytest.fixture
async def client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def register(
    client: httpx.AsyncClient,
    email: str = "marina.santos@medflux.com",
    password: str = "123456",
    name: str = "Marina Santos",
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/register", json={"name": name, "email": email, "password": password, "city": "Marília, SP"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(session: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['token']}"}


async def make_admin(app: Any, user_id: str) -> None:
    async with app.state.session_factory() as session:
        await session.execute(update(User).where(User.id == user_id).values(is_admin=True))
        await session.commit()
