from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class SymptomRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "symptom_records"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("triage_sessions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    symptoms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_type: Mapped[str | None] = mapped_column(String(3), nullable=True)

    user: Mapped["User"] = relationship(back_populates="symptom_records")
