"""registro operacional de dispositivos push mobile

Revision ID: b7d4c1e9a2f3
Revises: ab4e8d1c9f32
Create Date: 2026-03-30 20:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7d4c1e9a2f3"
down_revision = "ab4e8d1c9f32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())
    if "dispositivos_push_mobile" not in tabelas:
        op.create_table(
            "dispositivos_push_mobile",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("device_id", sa.String(length=120), nullable=False),
            sa.Column("plataforma", sa.String(length=20), nullable=False),
            sa.Column("provider", sa.String(length=20), nullable=False),
            sa.Column("push_token", sa.String(length=255), nullable=True),
            sa.Column("permissao_notificacoes", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("push_habilitado", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("token_status", sa.String(length=40), nullable=False, server_default="unavailable"),
            sa.Column("canal_build", sa.String(length=60), nullable=True),
            sa.Column("app_version", sa.String(length=40), nullable=True),
            sa.Column("build_number", sa.String(length=40), nullable=True),
            sa.Column("device_label", sa.String(length=120), nullable=True),
            sa.Column("is_emulator", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("ultimo_erro", sa.String(length=220), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "usuario_id",
                "device_id",
                "plataforma",
                name="uq_push_mobile_usuario_device_plataforma",
            ),
        )

    indices = {
        indice["name"]
        for indice in inspector.get_indexes("dispositivos_push_mobile")
    }
    with op.batch_alter_table("dispositivos_push_mobile") as batch_op:
        if "ix_push_mobile_empresa_last_seen" not in indices:
            batch_op.create_index(
                "ix_push_mobile_empresa_last_seen",
                ["empresa_id", "last_seen_at"],
                unique=False,
            )
        if "ix_push_mobile_usuario_status" not in indices:
            batch_op.create_index(
                "ix_push_mobile_usuario_status",
                ["usuario_id", "token_status"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())
    if "dispositivos_push_mobile" not in tabelas:
        return

    indices = {
        indice["name"]
        for indice in inspector.get_indexes("dispositivos_push_mobile")
    }
    with op.batch_alter_table("dispositivos_push_mobile") as batch_op:
        if "ix_push_mobile_usuario_status" in indices:
            batch_op.drop_index("ix_push_mobile_usuario_status")
        if "ix_push_mobile_empresa_last_seen" in indices:
            batch_op.drop_index("ix_push_mobile_empresa_last_seen")
    op.drop_table("dispositivos_push_mobile")
