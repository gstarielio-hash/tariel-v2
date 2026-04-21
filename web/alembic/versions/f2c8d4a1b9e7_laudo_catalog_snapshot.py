"""adiciona snapshot catalogal imutavel no laudo

Revision ID: f2c8d4a1b9e7
Revises: e7b4c1d9a2f6
Create Date: 2026-04-12 00:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f2c8d4a1b9e7"
down_revision = "e7b4c1d9a2f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("laudos", sa.Column("catalog_selection_token", sa.String(length=240), nullable=True))
    op.add_column("laudos", sa.Column("catalog_snapshot_json", sa.JSON(), nullable=True))
    op.add_column("laudos", sa.Column("pdf_template_snapshot_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("laudos", "pdf_template_snapshot_json")
    op.drop_column("laudos", "catalog_snapshot_json")
    op.drop_column("laudos", "catalog_selection_token")
