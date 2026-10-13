"""Perfil do usuário: leitura, atualização de dados e foto."""

from sqlalchemy.exc import IntegrityError

from app.core.constants import Bucket
from app.core.exceptions import ConflictError
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.file import FileUploadResponse
from app.schemas.user import UserResponse, UserUpdate
from app.services.storage_service import StorageService


class UserService:
    def __init__(self, users: UserRepository, storage: StorageService) -> None:
        self.users = users
        self.storage = storage

    def to_response(self, user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            city=user.city,
            avatar_url=self.storage.presigned_url(Bucket.USERS, user.avatar_key) if user.avatar_key else None,
            avatar_initials=user.avatar_initials,
            created_at=user.created_at,
        )

    async def update(self, user: User, data: UserUpdate) -> User:
        if data.email is not None and data.email != user.email:
            if await self.users.get_by_email(data.email):
                raise ConflictError("Email já cadastrado.", code="email_taken")
            user.email = data.email
        if data.name is not None:
            user.name = data.name
        if data.city is not None:
            user.city = data.city
        try:
            await self.users.session.commit()
        except IntegrityError as exc:
            await self.users.session.rollback()
            raise ConflictError("Email já cadastrado.", code="email_taken") from exc
        return user

    async def update_avatar(self, user: User, data: bytes) -> FileUploadResponse:
        upload = await self.storage.upload_avatar(user.id, data)
        previous_key = user.avatar_key
        user.avatar_key = upload.object_name
        await self.users.session.commit()
        if previous_key and previous_key != upload.object_name:
            await self.storage.delete_safely(Bucket.USERS, previous_key)
        return upload
