"""emissao oficial transacional

Revision ID: e7b4c1d9a2f6
Revises: d5f7c1a9e2b4
Create Date: 2026-04-10 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7b4c1d9a2f6"
down_revision = "d5f7c1a9e2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emissoes_oficiais_laudo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("laudo_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("approval_snapshot_id", sa.Integer(), nullable=True),
        sa.Column("signatory_id", sa.Integer(), nullable=True),
        sa.Column("issued_by_user_id", sa.Integer(), nullable=True),
        sa.Column("superseded_by_issue_id", sa.Integer(), nullable=True),
        sa.Column("issue_number", sa.String(length=80), nullable=False),
        sa.Column("issue_state", sa.String(length=20), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_hash", sa.String(length=64), nullable=True),
        sa.Column("public_verification_url", sa.String(length=400), nullable=True),
        sa.Column("package_sha256", sa.String(length=64), nullable=False),
        sa.Column("package_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("package_filename", sa.String(length=220), nullable=True),
        sa.Column("package_storage_path", sa.String(length=600), nullable=True),
        sa.Column("package_size_bytes", sa.Integer(), nullable=True),
        sa.Column("manifest_json", sa.JSON(), nullable=True),
        sa.Column("issue_context_json", sa.JSON(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "issue_state IN ('issued', 'superseded', 'revoked')",
            name="ck_emissao_oficial_issue_state",
        ),
        sa.ForeignKeyConstraint(["approval_snapshot_id"], ["laudo_approved_case_snapshots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["laudo_id"], ["laudos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signatory_id"], ["signatarios_governados_laudo.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["superseded_by_issue_id"], ["emissoes_oficiais_laudo.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issue_number", name="uq_emissao_oficial_issue_number"),
    )
    op.create_index("ix_emissao_oficial_laudo_estado", "emissoes_oficiais_laudo", ["laudo_id", "issue_state"], unique=False)
    op.create_index("ix_emissao_oficial_tenant_emitida", "emissoes_oficiais_laudo", ["tenant_id", "issued_at"], unique=False)
    op.create_index("ix_emissao_oficial_hash_pacote", "emissoes_oficiais_laudo", ["package_sha256"], unique=False)
    op.create_index("ix_emissao_oficial_hash_fingerprint", "emissoes_oficiais_laudo", ["package_fingerprint_sha256"], unique=False)
    op.create_index(op.f("ix_emissoes_oficiais_laudo_id"), "emissoes_oficiais_laudo", ["id"], unique=False)
    op.create_index(op.f("ix_emissoes_oficiais_laudo_laudo_id"), "emissoes_oficiais_laudo", ["laudo_id"], unique=False)
    op.create_index(op.f("ix_emissoes_oficiais_laudo_tenant_id"), "emissoes_oficiais_laudo", ["tenant_id"], unique=False)
    op.create_index(
        op.f("ix_emissoes_oficiais_laudo_approval_snapshot_id"),
        "emissoes_oficiais_laudo",
        ["approval_snapshot_id"],
        unique=False,
    )
    op.create_index(op.f("ix_emissoes_oficiais_laudo_signatory_id"), "emissoes_oficiais_laudo", ["signatory_id"], unique=False)
    op.create_index(
        op.f("ix_emissoes_oficiais_laudo_issued_by_user_id"),
        "emissoes_oficiais_laudo",
        ["issued_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_emissoes_oficiais_laudo_superseded_by_issue_id"),
        "emissoes_oficiais_laudo",
        ["superseded_by_issue_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_emissoes_oficiais_laudo_issue_number"),
        "emissoes_oficiais_laudo",
        ["issue_number"],
        unique=True,
    )
    op.create_index(
        op.f("ix_emissoes_oficiais_laudo_verification_hash"),
        "emissoes_oficiais_laudo",
        ["verification_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_emissoes_oficiais_laudo_verification_hash"), table_name="emissoes_oficiais_laudo")
    op.drop_index(op.f("ix_emissoes_oficiais_laudo_issue_number"), table_name="emissoes_oficiais_laudo")
    op.drop_index(op.f("ix_emissoes_oficiais_laudo_superseded_by_issue_id"), table_name="emissoes_oficiais_laudo")
    op.drop_index(op.f("ix_emissoes_oficiais_laudo_issued_by_user_id"), table_name="emissoes_oficiais_laudo")
    op.drop_index(op.f("ix_emissoes_oficiais_laudo_signatory_id"), table_name="emissoes_oficiais_laudo")
    op.drop_index(op.f("ix_emissoes_oficiais_laudo_approval_snapshot_id"), table_name="emissoes_oficiais_laudo")
    op.drop_index(op.f("ix_emissoes_oficiais_laudo_tenant_id"), table_name="emissoes_oficiais_laudo")
    op.drop_index(op.f("ix_emissoes_oficiais_laudo_laudo_id"), table_name="emissoes_oficiais_laudo")
    op.drop_index(op.f("ix_emissoes_oficiais_laudo_id"), table_name="emissoes_oficiais_laudo")
    op.drop_index("ix_emissao_oficial_hash_fingerprint", table_name="emissoes_oficiais_laudo")
    op.drop_index("ix_emissao_oficial_hash_pacote", table_name="emissoes_oficiais_laudo")
    op.drop_index("ix_emissao_oficial_tenant_emitida", table_name="emissoes_oficiais_laudo")
    op.drop_index("ix_emissao_oficial_laudo_estado", table_name="emissoes_oficiais_laudo")
    op.drop_table("emissoes_oficiais_laudo")
