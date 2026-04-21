"""adiciona persistencia canonica do draft guiado no laudo

Revision ID: 8d2c4f6a1b3e
Revises: 6f2b1c4d8e9a
Create Date: 2026-04-06 22:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8d2c4f6a1b3e"
down_revision: Union[str, Sequence[str], None] = "6f2b1c4d8e9a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "laudos",
        sa.Column("guided_inspection_draft_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("laudos", "guided_inspection_draft_json")
