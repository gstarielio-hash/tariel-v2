"""Adiciona catálogo oficial de famílias de laudo e ofertas comerciais.

Revision ID: c4e7b1a9d2f6
Revises: 9c4b6d1e2f3a
Create Date: 2026-04-09 08:55:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c4e7b1a9d2f6"
down_revision = "9c4b6d1e2f3a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "familias_laudo_catalogo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family_key", sa.String(length=120), nullable=False),
        sa.Column("macro_categoria", sa.String(length=80), nullable=True),
        sa.Column("nome_exibicao", sa.String(length=180), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("status_catalogo", sa.String(length=20), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("evidence_policy_json", sa.JSON(), nullable=True),
        sa.Column("review_policy_json", sa.JSON(), nullable=True),
        sa.Column("output_schema_seed_json", sa.JSON(), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status_catalogo IN ('rascunho', 'publicado', 'arquivado')",
            name="ck_familia_catalogo_status",
        ),
        sa.CheckConstraint("schema_version >= 1", name="ck_familia_catalogo_schema_version"),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("family_key", name="uq_familia_catalogo_family_key"),
    )
    op.create_index("ix_familias_laudo_catalogo_id", "familias_laudo_catalogo", ["id"], unique=False)
    op.create_index("ix_familias_laudo_catalogo_family_key", "familias_laudo_catalogo", ["family_key"], unique=True)
    op.create_index("ix_familia_catalogo_status", "familias_laudo_catalogo", ["status_catalogo"], unique=False)
    op.create_index(
        "ix_familia_catalogo_macro_categoria",
        "familias_laudo_catalogo",
        ["macro_categoria"],
        unique=False,
    )
    op.create_index("ix_familias_laudo_catalogo_criado_por_id", "familias_laudo_catalogo", ["criado_por_id"], unique=False)

    op.create_table(
        "familias_laudo_ofertas_comerciais",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("nome_oferta", sa.String(length=180), nullable=False),
        sa.Column("descricao_comercial", sa.Text(), nullable=True),
        sa.Column("pacote_comercial", sa.String(length=80), nullable=True),
        sa.Column("prazo_padrao_dias", sa.Integer(), nullable=True),
        sa.Column("ativo_comercial", sa.Boolean(), nullable=False),
        sa.Column("versao_oferta", sa.Integer(), nullable=False),
        sa.Column("material_real_status", sa.String(length=20), nullable=False),
        sa.Column("escopo_json", sa.JSON(), nullable=True),
        sa.Column("exclusoes_json", sa.JSON(), nullable=True),
        sa.Column("insumos_minimos_json", sa.JSON(), nullable=True),
        sa.Column("variantes_json", sa.JSON(), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("versao_oferta >= 1", name="ck_familia_oferta_versao"),
        sa.CheckConstraint(
            "prazo_padrao_dias IS NULL OR prazo_padrao_dias >= 0",
            name="ck_familia_oferta_prazo",
        ),
        sa.CheckConstraint(
            "material_real_status IN ('sintetico', 'parcial', 'calibrado')",
            name="ck_familia_oferta_material_real_status",
        ),
        sa.ForeignKeyConstraint(["family_id"], ["familias_laudo_catalogo.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("family_id", name="uq_familia_oferta_family"),
    )
    op.create_index(
        "ix_familias_laudo_ofertas_comerciais_id",
        "familias_laudo_ofertas_comerciais",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_familias_laudo_ofertas_comerciais_family_id",
        "familias_laudo_ofertas_comerciais",
        ["family_id"],
        unique=False,
    )
    op.create_index(
        "ix_familias_laudo_ofertas_comerciais_criado_por_id",
        "familias_laudo_ofertas_comerciais",
        ["criado_por_id"],
        unique=False,
    )
    op.create_index(
        "ix_familia_oferta_ativa",
        "familias_laudo_ofertas_comerciais",
        ["ativo_comercial"],
        unique=False,
    )
    op.create_index(
        "ix_familia_oferta_material_real_status",
        "familias_laudo_ofertas_comerciais",
        ["material_real_status"],
        unique=False,
    )
    op.create_index(
        "ix_familia_oferta_pacote",
        "familias_laudo_ofertas_comerciais",
        ["pacote_comercial"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_familia_oferta_pacote", table_name="familias_laudo_ofertas_comerciais")
    op.drop_index("ix_familia_oferta_material_real_status", table_name="familias_laudo_ofertas_comerciais")
    op.drop_index("ix_familia_oferta_ativa", table_name="familias_laudo_ofertas_comerciais")
    op.drop_index("ix_familias_laudo_ofertas_comerciais_criado_por_id", table_name="familias_laudo_ofertas_comerciais")
    op.drop_index("ix_familias_laudo_ofertas_comerciais_family_id", table_name="familias_laudo_ofertas_comerciais")
    op.drop_index("ix_familias_laudo_ofertas_comerciais_id", table_name="familias_laudo_ofertas_comerciais")
    op.drop_table("familias_laudo_ofertas_comerciais")

    op.drop_index("ix_familias_laudo_catalogo_criado_por_id", table_name="familias_laudo_catalogo")
    op.drop_index("ix_familia_catalogo_macro_categoria", table_name="familias_laudo_catalogo")
    op.drop_index("ix_familia_catalogo_status", table_name="familias_laudo_catalogo")
    op.drop_index("ix_familias_laudo_catalogo_family_key", table_name="familias_laudo_catalogo")
    op.drop_index("ix_familias_laudo_catalogo_id", table_name="familias_laudo_catalogo")
    op.drop_table("familias_laudo_catalogo")
