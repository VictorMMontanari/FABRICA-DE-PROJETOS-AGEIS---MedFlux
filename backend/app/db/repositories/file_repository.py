"""Acesso ao MinIO. O SDK oficial é síncrono, então cada chamada roda numa thread (asyncio.to_thread)."""

import asyncio
import io
from dataclasses import dataclass
from datetime import timedelta

from minio import Minio
from minio.error import S3Error


@dataclass(frozen=True)
class StoredObject:
    data: bytes
    content_type: str


class FileRepository:
    def __init__(self, client: Minio, public_client: Minio | None = None) -> None:
        self.client = client
        self.public_client = public_client or client

    async def ensure_buckets(self, buckets: list[str]) -> None:
        def _ensure() -> None:
            for bucket in buckets:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)

        await asyncio.to_thread(_ensure)

    async def put(self, bucket: str, object_name: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self.client.put_object, bucket, object_name, io.BytesIO(data), len(data), content_type=content_type
        )

    async def get(self, bucket: str, object_name: str) -> StoredObject | None:
        def _get() -> StoredObject | None:
            try:
                response = self.client.get_object(bucket, object_name)
            except S3Error as exc:
                if exc.code in ("NoSuchKey", "NoSuchBucket"):
                    return None
                raise
            try:
                return StoredObject(
                    data=response.read(),
                    content_type=response.headers.get("Content-Type", "application/octet-stream"),
                )
            finally:
                response.close()
                response.release_conn()

        return await asyncio.to_thread(_get)

    async def remove(self, bucket: str, object_name: str) -> None:
        await asyncio.to_thread(self.client.remove_object, bucket, object_name)

    def presigned_get_url(self, bucket: str, object_name: str, expires: timedelta) -> str:
        # Assinatura é calculada localmente (região fixa no cliente): não faz chamada de rede.
        return self.public_client.presigned_get_object(bucket, object_name, expires=expires)
