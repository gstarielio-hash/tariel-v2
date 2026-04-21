"""signatarios governados para emissao oficial

Revision ID: d5f7c1a9e2b4
Revises: c9e4a1b7d2f5
Create Date: 2026-04-10 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d5f7c1a9e2b4"
down_revision = "c9e4a1b7d2f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signatarios_governados_laudo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=160), nullable=False),
        sa.Column("funcao", sa.String(length=120), nullable=False),
        sa.Column("registro_profissional", sa.String(length=80), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allowed_family_keys_json", sa.JSON(), nullable=True),
        sa.Column("governance_metadata_json", sa.JSON(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "nome",
            "registro_profissional",
            name="uq_signatario_governado_tenant_nome_registro",
        ),
    )
    op.create_index(
        "ix_signatario_governado_tenant_ativo",
        "signatarios_governados_laudo",
        ["tenant_id", "ativo"],
        unique=False,
    )
    op.create_index(
        "ix_signatario_governado_tenant_validade",
        "signatarios_governados_laudo",
        ["tenant_id", "valid_until"],
        unique=False,
    )
    op.create_index(
        op.f("ix_signatarios_governados_laudo_id"),
        "signatarios_governados_laudo",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_signatarios_governados_laudo_tenant_id"),
        "signatarios_governados_laudo",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_signatarios_governados_laudo_criado_por_id"),
        "signatarios_governados_laudo",
        ["criado_por_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_signatarios_governados_laudo_criado_por_id"), table_name="signatarios_governados_laudo")
    op.drop_index(op.f("ix_signatarios_governados_laudo_tenant_id"), table_name="signatarios_governados_laudo")
    op.drop_index(op.f("ix_signatarios_governados_laudo_id"), table_name="signatarios_governados_laudo")
    op.drop_index("ix_signatario_governado_tenant_validade", table_name="signatarios_governados_laudo")
    op.drop_index("ix_signatario_governado_tenant_ativo", table_name="signatarios_governados_laudo")
    op.drop_table("signatarios_governados_laudo")
