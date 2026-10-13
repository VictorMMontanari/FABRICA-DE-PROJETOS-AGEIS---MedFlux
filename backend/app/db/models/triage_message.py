from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.triage_session import TriageSession


class TriageMessage(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "triage_messages"
    __table_args__ = (Index("ix_triage_messages_session_created", "session_id", "created_at"),)

    session_id: Mapped[str] = mapped_column(ForeignKey("triage_sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Recomendação estruturada da resposta do assistente, para reabrir o chat com o card.
    recommendation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    session: Mapped["TriageSession"] = relationship(back_populates="messages")
