"""Validação de arquivos enviados pelo usuário pelo conteúdo real (magic bytes), não pela extensão."""

_IMAGE_SIGNATURES: tuple[tuple[bytes, str, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
)


def detect_image_type(data: bytes) -> tuple[str, str] | None:
    """Retorna (content_type, extensão) para JPEG, PNG ou WEBP; None para qualquer outro conteúdo."""
    for signature, content_type, extension in _IMAGE_SIGNATURES:
        if data.startswith(signature):
            return content_type, extension
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


def is_safe_object_name(object_name: str) -> bool:
    """Bloqueia path traversal e nomes vazios em chaves do MinIO."""
    parts = object_name.split("/")
    return bool(object_name) and not object_name.startswith("/") and all(p not in ("", ".", "..") for p in parts)
