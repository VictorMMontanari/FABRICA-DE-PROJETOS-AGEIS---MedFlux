"""Injeção de dependências: sessão do banco, usuário autenticado e serviços por requisição.

Recursos de longa duração (engine, clientes Qdrant/MinIO/Redis, runtime de agentes) vivem em
`app.state`, criados no lifespan da aplicação. Nos testes eles são substituídos por dublês.
"""

from collections.abc import AsyncIterator
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.repositories.disease_repository import DiseaseRepository
from app.db.repositories.health_unit_repository import HealthUnitRepository
from app.db.repositories.triage_repository import TriageRepository
from app.db.repositories.user_repository import UserRepository
from app.services.agent_service import AgentService
from app.services.auth_service import AuthService
from app.services.storage_service import StorageService
from app.services.triage_service import TriageService
from app.services.user_service import UserService
from app.services.vector_service import VectorService

_bearer = HTTPBearer(auto_error=False, description="JWT obtido em /api/v1/auth/login")


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Não autenticado.")
    try:
        payload = decode_access_token(credentials.credentials, settings)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Token inválido ou expirado.", code="invalid_token") from exc
    user = await UserRepository(db).get_by_id(str(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("Token inválido ou expirado.", code="invalid_token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise ForbiddenError("Apenas administradores podem executar esta ação.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def get_storage_service(request: Request, settings: SettingsDep) -> StorageService:
    return StorageService(request.app.state.file_repository, settings)


StorageServiceDep = Annotated[StorageService, Depends(get_storage_service)]


def get_vector_service(request: Request, db: DbSession, settings: SettingsDep) -> VectorService:
    return VectorService(request.app.state.vector_repository, settings.EMBEDDING_DIM, DiseaseRepository(db))


VectorServiceDep = Annotated[VectorService, Depends(get_vector_service)]


def get_auth_service(request: Request, db: DbSession, settings: SettingsDep) -> AuthService:
    return AuthService(UserRepository(db), settings, request.app.state.redis)


def get_user_service(db: DbSession, storage: StorageServiceDep) -> UserService:
    return UserService(UserRepository(db), storage)


def get_agent_service(request: Request, db: DbSession, vectors: VectorServiceDep) -> AgentService:
    return AgentService(TriageRepository(db), vectors, request.app.state.agent_runtime)


AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]


def get_triage_service(db: DbSession, agents: AgentServiceDep, storage: StorageServiceDep) -> TriageService:
    return TriageService(TriageRepository(db), agents, storage)


def get_health_unit_repository(db: DbSession) -> HealthUnitRepository:
    return HealthUnitRepository(db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
TriageServiceDep = Annotated[TriageService, Depends(get_triage_service)]
HealthUnitRepositoryDep = Annotated[HealthUnitRepository, Depends(get_health_unit_repository)]
