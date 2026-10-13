from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import TriageStatus
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.triage_message import TriageMessage
    from app.db.models.user import User


class TriageSession(TimestampMixin, Base):
    __tablename__ = "triage_sessions"
    __table_args__ = (Index("ix_triage_sessions_user_updated", "user_id", "updated_at"),)

    # Até 64 caracteres: o frontend gera o próprio id (crypto.randomUUID) antes da 1ª mensagem.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), default="Nova triagem", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=TriageStatus.ACTIVE.value, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_type: Mapped[str | None] = mapped_column(String(3), nullable=True)
    urgency_label: Mapped[str | None] = mapped_column(String(80), nullable=True)

    user: Mapped["User"] = relationship(back_populates="triage_sessions")
    messages: Mapped[list["TriageMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TriageMessage.created_at",
    )
