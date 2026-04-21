"""Adiciona configuracoes persistentes de governanca da plataforma.

Revision ID: 2c6d8e1f4a5b
Revises: 1b7c9d4e2f60
Create Date: 2026-03-31 12:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "2c6d8e1f4a5b"
down_revision = "1b7c9d4e2f60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuracoes_plataforma",
        sa.Column("chave", sa.String(length=80), nullable=False),
        sa.Column("categoria", sa.String(length=40), nullable=False),
        sa.Column("valor_json", sa.JSON(), nullable=True),
        sa.Column("motivo_ultima_alteracao", sa.String(length=300), nullable=True),
        sa.Column("atualizada_por_usuario_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["atualizada_por_usuario_id"],
            ["usuarios.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("chave"),
    )
    op.create_index(
        "ix_configuracao_plataforma_categoria",
        "configuracoes_plataforma",
        ["categoria"],
        unique=False,
    )
    op.create_index(
        "ix_configuracao_plataforma_atualizada_por",
        "configuracoes_plataforma",
        ["atualizada_por_usuario_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_configuracao_plataforma_atualizada_por", table_name="configuracoes_plataforma")
    op.drop_index("ix_configuracao_plataforma_categoria", table_name="configuracoes_plataforma")
    op.drop_table("configuracoes_plataforma")
