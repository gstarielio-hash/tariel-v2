"""tenant admin policy per company

Revision ID: d8c4e1f7b2a3
Revises: f2c8d4a1b9e7
Create Date: 2026-04-13 07:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d8c4e1f7b2a3"
down_revision = "f2c8d4a1b9e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column("admin_cliente_policy_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("empresas", "admin_cliente_policy_json")
