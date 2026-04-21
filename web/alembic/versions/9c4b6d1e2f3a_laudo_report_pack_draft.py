"""adiciona draft incremental de report pack no laudo

Revision ID: 9c4b6d1e2f3a
Revises: 8d2c4f6a1b3e
Create Date: 2026-04-06 23:55:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c4b6d1e2f3a"
down_revision: Union[str, Sequence[str], None] = "8d2c4f6a1b3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "laudos",
        sa.Column("report_pack_draft_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("laudos", "report_pack_draft_json")
