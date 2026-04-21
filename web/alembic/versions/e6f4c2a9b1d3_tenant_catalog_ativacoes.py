"""Adiciona ativação de catálogo por tenant e persistência da variante no laudo.

Revision ID: e6f4c2a9b1d3
Revises: c4e7b1a9d2f6
Create Date: 2026-04-09 11:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e6f4c2a9b1d3"
down_revision = "c4e7b1a9d2f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("laudos", sa.Column("catalog_family_key", sa.String(length=120), nullable=True))
    op.add_column("laudos", sa.Column("catalog_family_label", sa.String(length=180), nullable=True))
    op.add_column("laudos", sa.Column("catalog_variant_key", sa.String(length=80), nullable=True))
    op.add_column("laudos", sa.Column("catalog_variant_label", sa.String(length=120), nullable=True))
    op.create_index(
        "ix_laudo_catalog_family_variant",
        "laudos",
        ["empresa_id", "catalog_family_key", "catalog_variant_key"],
        unique=False,
    )

    op.create_table(
        "empresa_catalogo_laudo_ativacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=True),
        sa.Column("oferta_id", sa.Integer(), nullable=True),
        sa.Column("family_key", sa.String(length=120), nullable=False),
        sa.Column("family_label", sa.String(length=180), nullable=False),
        sa.Column("group_label", sa.String(length=120), nullable=True),
        sa.Column("offer_name", sa.String(length=180), nullable=True),
        sa.Column("variant_key", sa.String(length=80), nullable=False),
        sa.Column("variant_label", sa.String(length=120), nullable=False),
        sa.Column("variant_ordem", sa.Integer(), nullable=True),
        sa.Column("runtime_template_code", sa.String(length=80), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("variant_ordem IS NULL OR variant_ordem >= 0", name="ck_empresa_catalogo_variant_ordem"),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_id"], ["familias_laudo_catalogo.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["oferta_id"], ["familias_laudo_ofertas_comerciais.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "family_key", "variant_key", name="uq_empresa_catalogo_family_variant"),
    )
    op.create_index(
        "ix_empresa_catalogo_laudo_ativacoes_id",
        "empresa_catalogo_laudo_ativacoes",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_empresa_catalogo_laudo_ativacoes_empresa_id",
        "empresa_catalogo_laudo_ativacoes",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        "ix_empresa_catalogo_laudo_ativacoes_family_id",
        "empresa_catalogo_laudo_ativacoes",
        ["family_id"],
        unique=False,
    )
    op.create_index(
        "ix_empresa_catalogo_laudo_ativacoes_oferta_id",
        "empresa_catalogo_laudo_ativacoes",
        ["oferta_id"],
        unique=False,
    )
    op.create_index(
        "ix_empresa_catalogo_laudo_ativacoes_criado_por_id",
        "empresa_catalogo_laudo_ativacoes",
        ["criado_por_id"],
        unique=False,
    )
    op.create_index(
        "ix_empresa_catalogo_empresa_ativo",
        "empresa_catalogo_laudo_ativacoes",
        ["empresa_id", "ativo"],
        unique=False,
    )
    op.create_index(
        "ix_empresa_catalogo_runtime",
        "empresa_catalogo_laudo_ativacoes",
        ["empresa_id", "runtime_template_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_empresa_catalogo_runtime", table_name="empresa_catalogo_laudo_ativacoes")
    op.drop_index("ix_empresa_catalogo_empresa_ativo", table_name="empresa_catalogo_laudo_ativacoes")
    op.drop_index("ix_empresa_catalogo_laudo_ativacoes_criado_por_id", table_name="empresa_catalogo_laudo_ativacoes")
    op.drop_index("ix_empresa_catalogo_laudo_ativacoes_oferta_id", table_name="empresa_catalogo_laudo_ativacoes")
    op.drop_index("ix_empresa_catalogo_laudo_ativacoes_family_id", table_name="empresa_catalogo_laudo_ativacoes")
    op.drop_index("ix_empresa_catalogo_laudo_ativacoes_empresa_id", table_name="empresa_catalogo_laudo_ativacoes")
    op.drop_index("ix_empresa_catalogo_laudo_ativacoes_id", table_name="empresa_catalogo_laudo_ativacoes")
    op.drop_table("empresa_catalogo_laudo_ativacoes")

    op.drop_index("ix_laudo_catalog_family_variant", table_name="laudos")
    op.drop_column("laudos", "catalog_variant_label")
    op.drop_column("laudos", "catalog_variant_key")
    op.drop_column("laudos", "catalog_family_label")
    op.drop_column("laudos", "catalog_family_key")
