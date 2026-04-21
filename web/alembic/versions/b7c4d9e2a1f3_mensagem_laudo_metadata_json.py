"""Mensagem laudo metadata json.

Revision ID: b7c4d9e2a1f3
Revises: a8f1d2c3b4e5
Create Date: 2026-04-10 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b7c4d9e2a1f3"
down_revision = "a8f1d2c3b4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mensagens_laudo", sa.Column("metadata_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("mensagens_laudo", "metadata_json")
