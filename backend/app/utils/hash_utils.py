import hashlib
import uuid

_MEDFLUX_NAMESPACE = uuid.UUID("6f2b8c1e-4a1d-4f7e-9a3b-2c5d8e9f0a1b")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_uuid(*parts: str) -> str:
    """UUID determinístico (v5): reindexar o mesmo item sobrescreve o ponto no Qdrant em vez de duplicar."""
    return str(uuid.uuid5(_MEDFLUX_NAMESPACE, "::".join(parts)))
