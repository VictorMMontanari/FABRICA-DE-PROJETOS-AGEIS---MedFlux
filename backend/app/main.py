"""Ponto de entrada da API MedFlux (FastAPI).

Execução: `uvicorn app.main:create_app --factory --port 5000`
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import text

from app.agents.runtime import build_runtime
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.constants import Bucket, VectorCollection
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import register_middleware
from app.db.repositories.file_repository import FileRepository
from app.db.repositories.vector_repository import VectorRepository
from app.db.session import create_engine, create_session_factory
from app.integrations.minio_client import create_minio_client
from app.integrations.openrouter_client import OpenRouterClient
from app.integrations.qdrant_client import create_qdrant_client
from app.services.ai_service import AIService

logger = get_logger(__name__)


OPENAPI_TAGS = [
    {"name": "auth", "description": "Cadastro, login e usuário autenticado (JWT)."},
    {"name": "users", "description": "Perfil do usuário e foto (MinIO)."},
    {"name": "health units", "description": "Unidades de saúde (UPA/UBS) para o mapa."},
    {"name": "triage", "description": "Chat de triagem com IA e histórico."},
    {"name": "agents", "description": "Eventos dos agentes de saúde."},
    {"name": "vector", "description": "Base de conhecimento e busca vetorial (Qdrant)."},
    {"name": "files", "description": "Download autenticado de arquivos do usuário."},
    {"name": "infra", "description": "Liveness e readiness."},
]


def _api_description(settings: Settings) -> str:
    demo = (
        "\n\nUsuário de demonstração: **marina.santos@medflux.com** / **123456**."
        if settings.SEED_DEMO_USER and settings.APP_ENV != "production"
        else ""
    )
    return f"""Backend do MedFlux - Health & Wellness.

### Como testar a autenticação
1. **Cadastro**: `POST /api/v1/auth/register` → *Try it out* → *Execute* (ou use um usuário existente).
2. **Login**: clique em **Authorize** (cadeado no topo), preencha `username` com o **email** e `password` com a
   senha e confirme. Client id/secret ficam vazios.
3. Rotas com cadeado passam a enviar `Authorization: Bearer <token>` sozinhas. Teste com `GET /api/v1/auth/me`.
4. Para sair, **Authorize** → **Logout**.

O token também pode ser obtido em `POST /api/v1/auth/login` (JSON, usado pelo frontend). Todos os erros
seguem `{{"code", "message", "details"}}`.{demo}"""


async def _init_vector_repository(settings: Settings) -> VectorRepository:
    repository = VectorRepository(create_qdrant_client(settings), settings.EMBEDDING_DIM)
    try:
        await repository.ensure_collections(VectorCollection)
    except Exception as exc:  # noqa: BLE001 - a API sobe degradada; o chat usa fallback sem contexto vetorial
        logger.warning("qdrant_unavailable_on_startup", extra={"error": type(exc).__name__})
    return repository


async def _init_file_repository(settings: Settings) -> FileRepository | None:
    if not settings.MINIO_ACCESS_KEY or not settings.MINIO_SECRET_KEY:
        logger.warning("minio_not_configured")
        return None
    repository = FileRepository(create_minio_client(settings), create_minio_client(settings, public=True))
    try:
        await repository.ensure_buckets([Bucket.USERS.value, Bucket.TRIAGE.value, settings.MINIO_BUCKET])
    except Exception as exc:  # noqa: BLE001
        logger.warning("minio_unavailable_on_startup", extra={"error": type(exc).__name__})
    return repository


def _init_redis(settings: Settings) -> Redis | None:
    if not settings.REDIS_HOST:
        return None
    return Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, socket_timeout=1, socket_connect_timeout=1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = create_engine(settings)
    http = httpx.AsyncClient()

    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.agent_runtime = build_runtime(settings, AIService(OpenRouterClient(http, settings)))
    app.state.vector_repository = await _init_vector_repository(settings)
    app.state.file_repository = await _init_file_repository(settings)
    app.state.redis = _init_redis(settings)
    logger.info(
        "startup",
        extra={
            "env": settings.APP_ENV,
            "agent_runtime": app.state.agent_runtime.name,
            "openrouter": settings.openrouter_enabled,
        },
    )
    try:
        yield
    finally:
        await http.aclose()
        await app.state.vector_repository.client.close()
        if app.state.redis is not None:
            await app.state.redis.aclose()
        await engine.dispose()


def create_app(settings: Settings | None = None, *, with_lifespan: bool = True) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.LOG_LEVEL)

    docs_enabled = settings.APP_ENV != "production"
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description=_api_description(settings),
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan if with_lifespan else None,
        # Swagger/ReDoc só fora de produção: em produção o contrato não fica público.
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        swagger_ui_parameters={
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "tryItOutEnabled": True,
            "docExpansion": "list",
            "filter": True,
        },
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    register_middleware(app)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/healthz", tags=["infra"])
    async def healthz() -> dict[str, str]:
        """Liveness: o processo está de pé."""
        return {"status": "ok"}

    @app.get("/readyz", tags=["infra"])
    async def readyz(request: Request) -> dict[str, Any]:
        """Readiness: estado de cada dependência externa."""
        state = request.app.state
        checks: dict[str, str] = {}
        try:
            async with state.session_factory() as session:
                await session.execute(text("SELECT 1"))
            checks["mysql"] = "ok"
        except Exception:  # noqa: BLE001
            checks["mysql"] = "error"
        try:
            await state.vector_repository.client.get_collections()
            checks["qdrant"] = "ok"
        except Exception:  # noqa: BLE001
            checks["qdrant"] = "error"
        checks["minio"] = "ok" if state.file_repository is not None else "disabled"
        if state.redis is None:
            checks["redis"] = "disabled"
        else:
            try:
                await state.redis.ping()
                checks["redis"] = "ok"
            except Exception:  # noqa: BLE001
                checks["redis"] = "error"
        checks["openrouter"] = "configured" if settings.openrouter_enabled else "fallback"
        status = "ok" if checks["mysql"] == "ok" else "degraded"
        return {"status": status, "agent_runtime": state.agent_runtime.name, "checks": checks}

    return app

