"""Tenant release governance policy.

Revision ID: c9e4a1b7d2f5
Revises: b7c4d9e2a1f3
Create Date: 2026-04-10 12:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c9e4a1b7d2f5"
down_revision = "b7c4d9e2a1f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_family_releases",
        sa.Column("governance_policy_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_family_releases", "governance_policy_json")
