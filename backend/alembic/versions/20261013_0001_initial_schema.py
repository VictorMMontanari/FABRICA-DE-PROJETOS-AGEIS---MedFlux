"""Schema inicial do MedFlux + unidades de saúde de Marília/SP.

Revision ID: 0001
Revises:
Create Date: 2026-10-13
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")

# Mesmas unidades exibidas hoje no mapa do frontend.
HEALTH_UNITS = [
    ("upa-central", "UPA Zona Norte", "UPA", "Av. das Hortênsias, 245 - Marília/SP", -22.2183, -49.9505),
    ("upa-sul", "UPA Sul", "UPA", "R. João Ramalho, 889 - Marília/SP", -22.2244, -49.9549),
    ("ubs-1", "UBS Santa Antonieta", "UBS", "Av. Mem de Sá, 112 - Marília/SP", -22.2143, -49.9441),
    ("ubs-2", "UBS Cascata", "UBS", "R. Benedito Mendes Faria, 1020 - Marília/SP", -22.2281, -49.9632),
]


def _timestamps(*, updated: bool = True) -> list[sa.Column]:
    columns = [sa.Column("created_at", TIMESTAMP, nullable=False)]
    if updated:
        columns.append(sa.Column("updated_at", TIMESTAMP, nullable=False))
    return columns


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("avatar_key", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "health_units",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("type", sa.String(3), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(updated=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_health_units")),
    )
    op.create_index(op.f("ix_health_units_type"), "health_units", ["type"], unique=False)

    op.create_table(
        "disease_embeddings",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("symptoms", sa.JSON(), nullable=False),
        sa.Column("recommended_unit", sa.String(3), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("collection", sa.String(60), nullable=False),
        sa.Column("vector_id", sa.String(36), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_disease_embeddings")),
        sa.UniqueConstraint("name", name=op.f("uq_disease_embeddings_name")),
        sa.UniqueConstraint("vector_id", name=op.f("uq_disease_embeddings_vector_id")),
    )

    op.create_table(
        "triage_sessions",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("unit_type", sa.String(3), nullable=True),
        sa.Column("urgency_label", sa.String(80), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_triage_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_triage_sessions")),
    )
    op.create_index("ix_triage_sessions_user_updated", "triage_sessions", ["user_id", "updated_at"], unique=False)

    op.create_table(
        "triage_messages",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.JSON(), nullable=True),
        *_timestamps(updated=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["triage_sessions.id"],
            name=op.f("fk_triage_messages_session_id_triage_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_triage_messages")),
    )
    op.create_index(
        "ix_triage_messages_session_created", "triage_messages", ["session_id", "created_at"], unique=False
    )

    op.create_table(
        "symptom_records",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("symptoms", sa.JSON(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("unit_type", sa.String(3), nullable=True),
        *_timestamps(updated=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["triage_sessions.id"],
            name=op.f("fk_symptom_records_session_id_triage_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_symptom_records_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_symptom_records")),
    )
    op.create_index(op.f("ix_symptom_records_user_id"), "symptom_records", ["user_id"], unique=False)
    op.create_index(op.f("ix_symptom_records_session_id"), "symptom_records", ["session_id"], unique=False)

    op.create_table(
        "agent_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("agent_name", sa.String(60), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=True),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("vector_id", sa.String(36), nullable=True),
        *_timestamps(updated=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["triage_sessions.id"],
            name=op.f("fk_agent_events_session_id_triage_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_agent_events_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_events")),
    )
    op.create_index("ix_agent_events_user_created", "agent_events", ["user_id", "created_at"], unique=False)
    op.create_index(op.f("ix_agent_events_session_id"), "agent_events", ["session_id"], unique=False)

    health_units = sa.table(
        "health_units",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("type", sa.String),
        sa.column("address", sa.String),
        sa.column("latitude", sa.Float),
        sa.column("longitude", sa.Float),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    op.bulk_insert(
        health_units,
        [
            {
                "id": unit_id,
                "name": name,
                "type": unit_type,
                "address": address,
                "latitude": lat,
                "longitude": lng,
                "is_active": True,
                "created_at": now,
            }
            for unit_id, name, unit_type, address, lat, lng in HEALTH_UNITS
        ],
    )


def downgrade() -> None:
    op.drop_table("agent_events")
    op.drop_table("symptom_records")
    op.drop_table("triage_messages")
    op.drop_table("triage_sessions")
    op.drop_table("disease_embeddings")
    op.drop_table("health_units")
    op.drop_table("users")
