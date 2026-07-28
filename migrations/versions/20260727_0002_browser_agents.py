"""add browser agents and extension job execution

Revision ID: 20260727_0002
Revises: 20260727_0001
Create Date: 2026-07-27 14:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql


revision: str = "20260727_0002"
down_revision: Union[str, Sequence[str], None] = "20260727_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    json_document = sa.JSON().with_variant(
        postgresql.JSONB(astext_type=Text()), "postgresql"
    )
    op.create_table(
        "browser_agents",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("browser", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("capabilities", json_document, nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_browser_agents_user_id", "browser_agents", ["user_id"])
    op.create_index("ix_browser_agents_status", "browser_agents", ["status"])
    op.create_index(
        "ix_browser_agents_token_hash",
        "browser_agents",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_browser_agents_last_seen_at", "browser_agents", ["last_seen_at"]
    )

    op.create_table(
        "browser_agent_pairing_codes",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_browser_agent_pairing_codes_user_id",
        "browser_agent_pairing_codes",
        ["user_id"],
    )
    op.create_index(
        "ix_browser_agent_pairing_codes_code_hash",
        "browser_agent_pairing_codes",
        ["code_hash"],
        unique=True,
    )
    op.create_index(
        "ix_browser_agent_pairing_codes_expires_at",
        "browser_agent_pairing_codes",
        ["expires_at"],
    )

    op.add_column(
        "collection_jobs",
        sa.Column(
            "executor",
            sa.String(length=40),
            server_default="legacy_playwright",
            nullable=False,
        ),
    )
    op.add_column(
        "collection_jobs",
        sa.Column("browser_agent_id", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "collection_jobs",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_collection_jobs_browser_agent_id",
        "collection_jobs",
        "browser_agents",
        ["browser_agent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_collection_jobs_executor", "collection_jobs", ["executor"]
    )
    op.create_index(
        "ix_collection_jobs_browser_agent_id",
        "collection_jobs",
        ["browser_agent_id"],
    )
    op.alter_column(
        "collection_jobs",
        "executor",
        server_default="browser_extension",
    )


def downgrade() -> None:
    op.drop_index("ix_collection_jobs_browser_agent_id", table_name="collection_jobs")
    op.drop_index("ix_collection_jobs_executor", table_name="collection_jobs")
    op.drop_constraint(
        "fk_collection_jobs_browser_agent_id",
        "collection_jobs",
        type_="foreignkey",
    )
    op.drop_column("collection_jobs", "claimed_at")
    op.drop_column("collection_jobs", "browser_agent_id")
    op.drop_column("collection_jobs", "executor")

    op.drop_index(
        "ix_browser_agent_pairing_codes_expires_at",
        table_name="browser_agent_pairing_codes",
    )
    op.drop_index(
        "ix_browser_agent_pairing_codes_code_hash",
        table_name="browser_agent_pairing_codes",
    )
    op.drop_index(
        "ix_browser_agent_pairing_codes_user_id",
        table_name="browser_agent_pairing_codes",
    )
    op.drop_table("browser_agent_pairing_codes")

    op.drop_index("ix_browser_agents_last_seen_at", table_name="browser_agents")
    op.drop_index("ix_browser_agents_token_hash", table_name="browser_agents")
    op.drop_index("ix_browser_agents_status", table_name="browser_agents")
    op.drop_index("ix_browser_agents_user_id", table_name="browser_agents")
    op.drop_table("browser_agents")
