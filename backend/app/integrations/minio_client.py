from minio import Minio

from app.core.config import Settings


def create_minio_client(settings: Settings, *, public: bool = False) -> Minio:
    """Cliente MinIO.

    `public=True` usa o endpoint acessível pelo navegador (MINIO_PUBLIC_ENDPOINT) só para assinar
    URLs pré-assinadas: dentro do Docker o backend fala com `minio:9000`, mas o navegador precisa
    de `localhost:9000`, e o host faz parte da assinatura. A região fixa evita chamada de rede ao assinar.
    """
    endpoint = (settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT) if public else settings.MINIO_ENDPOINT
    return Minio(
        endpoint,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
        region=settings.MINIO_REGION,
    )
