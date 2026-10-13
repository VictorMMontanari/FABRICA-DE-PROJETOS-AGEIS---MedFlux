"""Cadastro, login (com limite de tentativas via Redis) e emissão de JWT."""

from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.exceptions import ConflictError, RateLimitError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate, UserLogin

logger = get_logger(__name__)

INVALID_CREDENTIALS = "Email ou senha inválidos."


class AuthService:
    _dummy_hash: str | None = None

    def __init__(self, users: UserRepository, settings: Settings, redis: Redis | None = None) -> None:
        self.users = users
        self.settings = settings
        self.redis = redis

    async def register(self, data: UserCreate) -> User:
        if await self.users.get_by_email(data.email):
            raise ConflictError("Email já cadastrado.", code="email_taken")
        user = User(
            name=data.name,
            email=data.email,
            city=data.city,
            password_hash=hash_password(data.password, self.settings.BCRYPT_ROUNDS),
        )
        try:
            await self.users.add(user)
            await self.users.session.commit()
        except IntegrityError as exc:  # corrida entre dois cadastros com o mesmo email
            await self.users.session.rollback()
            raise ConflictError("Email já cadastrado.", code="email_taken") from exc
        logger.info("user_registered", extra={"user_id": user.id})
        return user

    async def authenticate(self, data: UserLogin) -> User:
        await self._ensure_not_locked(data.email)
        user = await self.users.get_by_email(data.email)
        # Usuário inexistente também paga o custo do bcrypt: o tempo de resposta não revela emails cadastrados.
        password_hash = user.password_hash if user else self._get_dummy_hash()
        if not verify_password(data.password, password_hash) or user is None or not user.is_active:
            await self._register_failure(data.email)
            raise UnauthorizedError(INVALID_CREDENTIALS, code="invalid_credentials")
        await self._reset_failures(data.email)
        return user

    def issue_token(self, user: User) -> tuple[str, int]:
        return create_access_token(user.id, self.settings)

    def _get_dummy_hash(self) -> str:
        if AuthService._dummy_hash is None:
            AuthService._dummy_hash = hash_password("medflux-dummy-password", self.settings.BCRYPT_ROUNDS)
        return AuthService._dummy_hash

    # Rate limit: após LOGIN_MAX_ATTEMPTS falhas o email fica bloqueado por LOGIN_LOCKOUT_SECONDS.
    # Sem Redis (ou com Redis fora do ar) o login continua funcionando, apenas sem o limite.
    @staticmethod
    def _key(email: str) -> str:
        return f"medflux:login-failures:{email}"

    async def _ensure_not_locked(self, email: str) -> None:
        if self.redis is None:
            return
        try:
            attempts = await self.redis.get(self._key(email))
        except Exception as exc:  # noqa: BLE001
            logger.warning("rate_limit_unavailable", extra={"error": type(exc).__name__})
            return
        if attempts is not None and int(attempts) >= self.settings.LOGIN_MAX_ATTEMPTS:
            minutes = max(self.settings.LOGIN_LOCKOUT_SECONDS // 60, 1)
            raise RateLimitError(f"Muitas tentativas de login. Tente novamente em {minutes} minutos.")

    async def _register_failure(self, email: str) -> None:
        if self.redis is None:
            return
        try:
            key = self._key(email)
            attempts = await self.redis.incr(key)
            if attempts == 1:
                await self.redis.expire(key, self.settings.LOGIN_LOCKOUT_SECONDS)
        except Exception as exc:  # noqa: BLE001
            logger.warning("rate_limit_unavailable", extra={"error": type(exc).__name__})

    async def _reset_failures(self, email: str) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.delete(self._key(email))
        except Exception as exc:  # noqa: BLE001
            logger.warning("rate_limit_unavailable", extra={"error": type(exc).__name__})
