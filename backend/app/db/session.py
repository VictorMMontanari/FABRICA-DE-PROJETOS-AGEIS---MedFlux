"""Engine assíncrona e fábrica de sessões do SQLAlchemy."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    url = settings.database_url
    if url.startswith("sqlite"):
        # SQLite em memória (testes): uma única conexão compartilhada.
        return create_async_engine(
            url, echo=settings.DB_ECHO, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    return create_async_engine(url, echo=settings.DB_ECHO, pool_pre_ping=True, pool_recycle=1800)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
