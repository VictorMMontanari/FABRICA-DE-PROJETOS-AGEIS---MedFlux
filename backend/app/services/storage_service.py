"""Regras de armazenamento de arquivos no MinIO (avatares, transcrições de triagem, documentos)."""

import json
from datetime import timedelta
from typing import Any

from app.core.config import Settings
from app.core.constants import AVATAR_MAX_BYTES, Bucket
from app.core.exceptions import (
    AppError,
    NotFoundError,
    PayloadTooLargeError,
    ServiceUnavailableError,
    UnsupportedMediaError,
)
from app.core.logging import get_logger
from app.db.base import new_uuid
from app.db.repositories.file_repository import FileRepository, StoredObject
from app.schemas.file import FileUploadResponse
from app.utils.file_utils import detect_image_type, is_safe_object_name

logger = get_logger(__name__)


class StorageService:
    def __init__(self, files: FileRepository | None, settings: Settings) -> None:
        self.files = files
        self.expires = timedelta(minutes=settings.PRESIGNED_URL_EXPIRE_MINUTES)
        self.allowed_buckets = frozenset({Bucket.USERS.value, Bucket.TRIAGE.value, settings.MINIO_BUCKET})

    def _repo(self) -> FileRepository:
        if self.files is None:
            raise ServiceUnavailableError("Armazenamento de arquivos indisponível.")
        return self.files

    def presigned_url(self, bucket: str, object_name: str) -> str | None:
        if self.files is None:
            return None
        try:
            return self.files.presigned_get_url(bucket, object_name, self.expires)
        except Exception as exc:  # noqa: BLE001 - URL é opcional na resposta do perfil
            logger.warning("presign_failed", extra={"error": type(exc).__name__})
            return None

    async def upload_avatar(self, user_id: str, data: bytes) -> FileUploadResponse:
        if not data:
            raise AppError("Arquivo vazio.", code="empty_file")
        if len(data) > AVATAR_MAX_BYTES:
            raise PayloadTooLargeError(f"A foto deve ter no máximo {AVATAR_MAX_BYTES // (1024 * 1024)} MB.")
        detected = detect_image_type(data)
        if detected is None:
            raise UnsupportedMediaError("Formato inválido. Envie uma imagem JPEG, PNG ou WEBP.")
        content_type, extension = detected

        object_name = f"{user_id}/avatar-{new_uuid()}.{extension}"
        try:
            await self._repo().put(Bucket.USERS, object_name, data, content_type)
        except ServiceUnavailableError:
            raise
        except Exception as exc:
            logger.warning("avatar_upload_failed", extra={"error": type(exc).__name__})
            raise ServiceUnavailableError("Não foi possível salvar a foto agora.") from exc

        return FileUploadResponse(
            bucket=Bucket.USERS.value,
            object_name=object_name,
            content_type=content_type,
            size=len(data),
            url=self.presigned_url(Bucket.USERS, object_name) or "",
            expires_in=int(self.expires.total_seconds()),
        )

    async def delete_safely(self, bucket: str, object_name: str) -> None:
        try:
            await self._repo().remove(bucket, object_name)
        except Exception as exc:  # noqa: BLE001 - limpeza de arquivo antigo não pode quebrar a requisição
            logger.warning("file_delete_failed", extra={"object": object_name, "error": type(exc).__name__})

    async def archive_transcript_safely(self, user_id: str, session_id: str, transcript: dict[str, Any]) -> None:
        """Guarda a conversa concluída como JSON no bucket de triagem (best-effort)."""
        data = json.dumps(transcript, ensure_ascii=False, default=str).encode("utf-8")
        try:
            await self._repo().put(Bucket.TRIAGE, f"{user_id}/{session_id}.json", data, "application/json")
        except Exception as exc:  # noqa: BLE001
            logger.warning("transcript_archive_failed", extra={"session_id": session_id, "error": type(exc).__name__})

    async def get_user_file(self, user_id: str, bucket: str, object_name: str) -> StoredObject:
        """Arquivos ficam sob o prefixo `{user_id}/`: o usuário só acessa o que é dele."""
        if bucket not in self.allowed_buckets or not is_safe_object_name(object_name):
            raise NotFoundError("Arquivo não encontrado.")
        if not object_name.startswith(f"{user_id}/"):
            raise NotFoundError("Arquivo não encontrado.")
        try:
            stored = await self._repo().get(bucket, object_name)
        except ServiceUnavailableError:
            raise
        except Exception as exc:
            logger.warning("file_get_failed", extra={"error": type(exc).__name__})
            raise ServiceUnavailableError("Armazenamento de arquivos indisponível.") from exc
        if stored is None:
            raise NotFoundError("Arquivo não encontrado.")
        return stored
