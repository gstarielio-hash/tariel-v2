"""Formaliza tenant tecnico da plataforma, acesso Admin-CEO e sessao enriquecida.

Revision ID: 1b7c9d4e2f60
Revises: e4b6c8d2f9a1, f7a1c9d3b6e2, b7d4c1e9a2f3
Create Date: 2026-03-31 10:15:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "1b7c9d4e2f60"
down_revision = ("e4b6c8d2f9a1", "f7a1c9d3b6e2", "b7d4c1e9a2f3")
branch_labels = None
depends_on = None

_NIVEL_DIRETORIA = 99


def upgrade() -> None:
    with op.batch_alter_table("empresas", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "escopo_plataforma",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.add_column(sa.Column("account_scope", sa.String(length=20), nullable=False, server_default="tenant"))
        batch_op.add_column(sa.Column("account_status", sa.String(length=30), nullable=False, server_default="active"))
        batch_op.add_column(sa.Column("allowed_portals_json", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("platform_role", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("mfa_required", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("mfa_secret_b32", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("mfa_enrolled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("can_password_login", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("can_google_login", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("can_microsoft_login", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("blocked_reason", sa.String(length=300), nullable=True))
        batch_op.add_column(
            sa.Column(
                "portal_admin_autorizado",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "admin_identity_status",
                sa.String(length=40),
                nullable=False,
                server_default="active",
            )
        )
        batch_op.add_column(sa.Column("admin_identity_provider", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("admin_identity_subject", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("admin_identity_verified_em", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_check_constraint(
            "ck_usuario_admin_identity_status_valido",
            "admin_identity_status IN ('invited', 'active', 'suspended', 'blocked', 'password_reset_required')",
        )
        batch_op.create_check_constraint(
            "ck_usuario_account_scope_valido",
            "account_scope IN ('tenant', 'platform')",
        )
        batch_op.create_check_constraint(
            "ck_usuario_account_status_valido",
            "account_status IN ('active', 'blocked', 'pending_activation')",
        )
        batch_op.create_index("ix_usuario_admin_portal_autorizado", ["portal_admin_autorizado", "email"], unique=False)
        batch_op.create_index(
            "ix_usuario_platform_scope_status",
            ["account_scope", "account_status", "empresa_id"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_usuario_admin_identity_subject",
            ["admin_identity_provider", "admin_identity_subject"],
        )

    with op.batch_alter_table("sessoes_ativas", schema=None) as batch_op:
        batch_op.add_column(sa.Column("portal", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("account_scope", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("device_id", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("mfa_level", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("reauth_at", sa.DateTime(timezone=True), nullable=True))

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE usuarios
               SET account_scope = 'platform',
                   account_status = 'active',
                   allowed_portals_json = '["admin"]',
                   platform_role = 'PLATFORM_OWNER',
                   mfa_required = TRUE,
                   can_password_login = TRUE,
                   can_google_login = TRUE,
                   can_microsoft_login = TRUE,
                   portal_admin_autorizado = TRUE,
                   admin_identity_status = 'active'
             WHERE nivel_acesso = :nivel_diretoria
            """
        ),
        {"nivel_diretoria": _NIVEL_DIRETORIA},
    )
    bind.execute(
        sa.text(
            """
            UPDATE usuarios
               SET allowed_portals_json = '[]'
             WHERE nivel_acesso != :nivel_diretoria
               AND (
                   allowed_portals_json IS NULL
                   OR CAST(allowed_portals_json AS TEXT) = ''
                   OR CAST(allowed_portals_json AS TEXT) = 'null'
               )
            """
        ),
        {"nivel_diretoria": _NIVEL_DIRETORIA},
    )
    bind.execute(
        sa.text(
            """
            UPDATE empresas
               SET escopo_plataforma = TRUE
             WHERE id IN (
                SELECT DISTINCT empresa_id
                  FROM usuarios
                 WHERE nivel_acesso = :nivel_diretoria
                   AND portal_admin_autorizado = TRUE
                   AND empresa_id IS NOT NULL
             )
            """
        ),
        {"nivel_diretoria": _NIVEL_DIRETORIA},
    )
    bind.execute(
        sa.text(
            """
            UPDATE sessoes_ativas
               SET portal = COALESCE(portal, 'admin'),
                   account_scope = COALESCE(account_scope, 'platform')
             WHERE usuario_id IN (
                SELECT id
                  FROM usuarios
                 WHERE nivel_acesso = :nivel_diretoria
                   AND account_scope = 'platform'
             )
            """
        ),
        {"nivel_diretoria": _NIVEL_DIRETORIA},
    )
    bind.execute(
        sa.text(
            """
            UPDATE sessoes_ativas
               SET portal = COALESCE(portal, 'cliente'),
                   account_scope = COALESCE(account_scope, 'tenant')
             WHERE usuario_id NOT IN (
                SELECT id
                  FROM usuarios
                 WHERE nivel_acesso = :nivel_diretoria
                   AND account_scope = 'platform'
             )
            """
        ),
        {"nivel_diretoria": _NIVEL_DIRETORIA},
    )

    with op.batch_alter_table("empresas", schema=None) as batch_op:
        batch_op.alter_column("escopo_plataforma", server_default=None)

    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.alter_column("account_scope", server_default=None)
        batch_op.alter_column("account_status", server_default=None)
        batch_op.alter_column("allowed_portals_json", server_default=None)
        batch_op.alter_column("mfa_required", server_default=None)
        batch_op.alter_column("can_password_login", server_default=None)
        batch_op.alter_column("can_google_login", server_default=None)
        batch_op.alter_column("can_microsoft_login", server_default=None)
        batch_op.alter_column("portal_admin_autorizado", server_default=None)
        batch_op.alter_column("admin_identity_status", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("sessoes_ativas", schema=None) as batch_op:
        batch_op.drop_column("reauth_at")
        batch_op.drop_column("mfa_level")
        batch_op.drop_column("device_id")
        batch_op.drop_column("account_scope")
        batch_op.drop_column("portal")

    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.drop_constraint("uq_usuario_admin_identity_subject", type_="unique")
        batch_op.drop_index("ix_usuario_platform_scope_status")
        batch_op.drop_index("ix_usuario_admin_portal_autorizado")
        batch_op.drop_constraint("ck_usuario_account_status_valido", type_="check")
        batch_op.drop_constraint("ck_usuario_account_scope_valido", type_="check")
        batch_op.drop_constraint("ck_usuario_admin_identity_status_valido", type_="check")
        batch_op.drop_column("admin_identity_verified_em")
        batch_op.drop_column("admin_identity_subject")
        batch_op.drop_column("admin_identity_provider")
        batch_op.drop_column("admin_identity_status")
        batch_op.drop_column("portal_admin_autorizado")
        batch_op.drop_column("blocked_reason")
        batch_op.drop_column("can_microsoft_login")
        batch_op.drop_column("can_google_login")
        batch_op.drop_column("can_password_login")
        batch_op.drop_column("mfa_enrolled_at")
        batch_op.drop_column("mfa_secret_b32")
        batch_op.drop_column("mfa_required")
        batch_op.drop_column("platform_role")
        batch_op.drop_column("allowed_portals_json")
        batch_op.drop_column("account_status")
        batch_op.drop_column("account_scope")

    with op.batch_alter_table("empresas", schema=None) as batch_op:
        batch_op.drop_column("escopo_plataforma")
