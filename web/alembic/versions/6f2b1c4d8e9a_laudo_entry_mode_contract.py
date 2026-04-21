"""adiciona contrato de modo de entrada no laudo

Revision ID: 6f2b1c4d8e9a
Revises: 2c6d8e1f4a5b
Create Date: 2026-04-06 19:40:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f2b1c4d8e9a"
down_revision: Union[str, Sequence[str], None] = "2c6d8e1f4a5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "laudos",
        sa.Column(
            "entry_mode_preference",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'auto_recommended'"),
        ),
    )
    op.add_column(
        "laudos",
        sa.Column(
            "entry_mode_effective",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'chat_first'"),
        ),
    )
    op.add_column(
        "laudos",
        sa.Column(
            "entry_mode_reason",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'default_product_fallback'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("laudos", "entry_mode_reason")
    op.drop_column("laudos", "entry_mode_effective")
    op.drop_column("laudos", "entry_mode_preference")
