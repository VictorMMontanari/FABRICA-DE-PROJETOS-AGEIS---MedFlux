from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DiseaseEmbedding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Metadados de uma doença indexada. O vetor vive no Qdrant (vector_id); o MySQL é a fonte de verdade."""

    __tablename__ = "disease_embeddings"

    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    symptoms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    recommended_unit: Mapped[str | None] = mapped_column(String(3), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    collection: Mapped[str] = mapped_column(String(60), nullable=False)
    vector_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
