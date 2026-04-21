"""Adiciona a persistencia inicial da memoria operacional governada.

Revision ID: a8f1d2c3b4e5
Revises: f1a2b3c4d5e6
Create Date: 2026-04-10 07:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a8f1d2c3b4e5"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


EVENT_TYPES_VALIDOS = (
    "image_blurry",
    "image_dark",
    "image_duplicate",
    "image_family_mismatch",
    "image_asset_mismatch",
    "required_angle_missing",
    "evidence_conclusion_conflict",
    "document_missing",
    "field_reopened",
    "block_returned_to_inspector",
)
EVENT_SOURCES_VALIDOS = ("system_quality_gate", "mesa", "inspetor", "chat_ia", "curadoria", "runtime")
SEVERIDADES_VALIDAS = ("info", "warning", "blocker")
EVIDENCE_OPERATIONAL_STATUS_VALIDOS = ("pending", "ok", "irregular", "replaced")
EVIDENCE_MESA_STATUS_VALIDOS = ("not_reviewed", "accepted", "rejected", "needs_recheck")
IRREGULARITY_STATUS_VALIDOS = ("open", "acknowledged", "resolved", "dismissed")
RESOLUTION_MODE_VALIDOS = (
    "recaptured_evidence",
    "edited_case_data",
    "mesa_override",
    "dismissed_false_positive",
    "not_applicable",
)


def _quoted_items(values: tuple[str, ...]) -> str:
    return ", ".join(repr(item) for item in values)


def upgrade() -> None:
    op.create_table(
        "laudo_approved_case_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("laudo_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("family_key", sa.String(length=120), nullable=False),
        sa.Column("approval_version", sa.Integer(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("source_status_revisao", sa.String(length=40), nullable=True),
        sa.Column("source_status_conformidade", sa.String(length=40), nullable=True),
        sa.Column("document_outcome", sa.String(length=80), nullable=True),
        sa.Column("laudo_output_snapshot", sa.JSON(), nullable=False),
        sa.Column("evidence_manifest_json", sa.JSON(), nullable=True),
        sa.Column("mesa_resolution_summary_json", sa.JSON(), nullable=True),
        sa.Column("technical_tags_json", sa.JSON(), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("approval_version >= 1", name="ck_approved_case_snapshot_version"),
        sa.ForeignKeyConstraint(["approved_by_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["laudo_id"], ["laudos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("laudo_id", "approval_version", name="uq_approved_case_snapshot_laudo_version"),
    )
    op.create_index("ix_laudo_approved_case_snapshots_id", "laudo_approved_case_snapshots", ["id"], unique=False)
    op.create_index(
        "ix_approved_case_snapshot_laudo",
        "laudo_approved_case_snapshots",
        ["laudo_id", "approved_at"],
        unique=False,
    )
    op.create_index(
        "ix_approved_case_snapshot_empresa_familia",
        "laudo_approved_case_snapshots",
        ["empresa_id", "family_key"],
        unique=False,
    )
    op.create_index(
        "ix_approved_case_snapshot_family_approved",
        "laudo_approved_case_snapshots",
        ["family_key", "approved_at"],
        unique=False,
    )

    op.create_table(
        "laudo_operational_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("laudo_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("family_key", sa.String(length=120), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_source", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("block_key", sa.String(length=120), nullable=True),
        sa.Column("evidence_key", sa.String(length=160), nullable=True),
        sa.Column("event_metadata_json", sa.JSON(), nullable=True),
        sa.Column("resolution_mode", sa.String(length=40), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"event_type IN ({_quoted_items(EVENT_TYPES_VALIDOS)})", name="ck_operational_event_type"),
        sa.CheckConstraint(
            f"event_source IN ({_quoted_items(EVENT_SOURCES_VALIDOS)})",
            name="ck_operational_event_source",
        ),
        sa.CheckConstraint(f"severity IN ({_quoted_items(SEVERIDADES_VALIDAS)})", name="ck_operational_event_severity"),
        sa.CheckConstraint(
            f"(resolution_mode IS NULL OR resolution_mode IN ({_quoted_items(RESOLUTION_MODE_VALIDOS)}))",
            name="ck_operational_event_resolution_mode",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["laudo_id"], ["laudos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["laudo_approved_case_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_laudo_operational_events_id", "laudo_operational_events", ["id"], unique=False)
    op.create_index(
        "ix_operational_event_laudo_criado",
        "laudo_operational_events",
        ["laudo_id", "criado_em"],
        unique=False,
    )
    op.create_index(
        "ix_operational_event_empresa_familia_tipo",
        "laudo_operational_events",
        ["empresa_id", "family_key", "event_type"],
        unique=False,
    )
    op.create_index("ix_operational_event_snapshot", "laudo_operational_events", ["snapshot_id"], unique=False)

    op.create_table(
        "laudo_evidence_validations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("laudo_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("family_key", sa.String(length=120), nullable=False),
        sa.Column("evidence_key", sa.String(length=160), nullable=False),
        sa.Column("component_type", sa.String(length=80), nullable=True),
        sa.Column("view_angle", sa.String(length=80), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("coherence_score", sa.Integer(), nullable=True),
        sa.Column("operational_status", sa.String(length=24), nullable=False),
        sa.Column("mesa_status", sa.String(length=24), nullable=False),
        sa.Column("failure_reasons_json", sa.JSON(), nullable=True),
        sa.Column("evidence_metadata_json", sa.JSON(), nullable=True),
        sa.Column("replacement_evidence_key", sa.String(length=160), nullable=True),
        sa.Column("validated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100))",
            name="ck_evidence_validation_quality_score",
        ),
        sa.CheckConstraint(
            "(coherence_score IS NULL OR (coherence_score >= 0 AND coherence_score <= 100))",
            name="ck_evidence_validation_coherence_score",
        ),
        sa.CheckConstraint(
            f"operational_status IN ({_quoted_items(EVIDENCE_OPERATIONAL_STATUS_VALIDOS)})",
            name="ck_evidence_validation_operational_status",
        ),
        sa.CheckConstraint(
            f"mesa_status IN ({_quoted_items(EVIDENCE_MESA_STATUS_VALIDOS)})",
            name="ck_evidence_validation_mesa_status",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["laudo_id"], ["laudos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["validated_by_user_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("laudo_id", "evidence_key", name="uq_evidence_validation_laudo_evidence"),
    )
    op.create_index("ix_laudo_evidence_validations_id", "laudo_evidence_validations", ["id"], unique=False)
    op.create_index(
        "ix_evidence_validation_empresa_familia",
        "laudo_evidence_validations",
        ["empresa_id", "family_key"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_validation_component_angle",
        "laudo_evidence_validations",
        ["family_key", "component_type", "view_angle"],
        unique=False,
    )

    op.create_table(
        "laudo_operational_irregularities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("laudo_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("family_key", sa.String(length=120), nullable=False),
        sa.Column("source_event_id", sa.Integer(), nullable=True),
        sa.Column("validation_id", sa.Integer(), nullable=True),
        sa.Column("detected_by_user_id", sa.Integer(), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("irregularity_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("detected_by", sa.String(length=32), nullable=False),
        sa.Column("block_key", sa.String(length=120), nullable=True),
        sa.Column("evidence_key", sa.String(length=160), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("resolution_mode", sa.String(length=40), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            f"irregularity_type IN ({_quoted_items(EVENT_TYPES_VALIDOS)})",
            name="ck_operational_irregularity_type",
        ),
        sa.CheckConstraint(
            f"severity IN ({_quoted_items(SEVERIDADES_VALIDAS)})",
            name="ck_operational_irregularity_severity",
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted_items(IRREGULARITY_STATUS_VALIDOS)})",
            name="ck_operational_irregularity_status",
        ),
        sa.CheckConstraint(
            f"detected_by IN ({_quoted_items(EVENT_SOURCES_VALIDOS)})",
            name="ck_operational_irregularity_detected_by",
        ),
        sa.CheckConstraint(
            f"(resolution_mode IS NULL OR resolution_mode IN ({_quoted_items(RESOLUTION_MODE_VALIDOS)}))",
            name="ck_operational_irregularity_resolution_mode",
        ),
        sa.ForeignKeyConstraint(["detected_by_user_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["laudo_id"], ["laudos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_event_id"], ["laudo_operational_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["validation_id"], ["laudo_evidence_validations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_laudo_operational_irregularities_id",
        "laudo_operational_irregularities",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_operational_irregularity_laudo_status",
        "laudo_operational_irregularities",
        ["laudo_id", "status", "criado_em"],
        unique=False,
    )
    op.create_index(
        "ix_operational_irregularity_empresa_familia_status",
        "laudo_operational_irregularities",
        ["empresa_id", "family_key", "status"],
        unique=False,
    )
    op.create_index(
        "ix_operational_irregularity_event_validation",
        "laudo_operational_irregularities",
        ["source_event_id", "validation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_operational_irregularity_event_validation", table_name="laudo_operational_irregularities")
    op.drop_index("ix_operational_irregularity_empresa_familia_status", table_name="laudo_operational_irregularities")
    op.drop_index("ix_operational_irregularity_laudo_status", table_name="laudo_operational_irregularities")
    op.drop_index("ix_laudo_operational_irregularities_id", table_name="laudo_operational_irregularities")
    op.drop_table("laudo_operational_irregularities")

    op.drop_index("ix_evidence_validation_component_angle", table_name="laudo_evidence_validations")
    op.drop_index("ix_evidence_validation_empresa_familia", table_name="laudo_evidence_validations")
    op.drop_index("ix_laudo_evidence_validations_id", table_name="laudo_evidence_validations")
    op.drop_table("laudo_evidence_validations")

    op.drop_index("ix_operational_event_snapshot", table_name="laudo_operational_events")
    op.drop_index("ix_operational_event_empresa_familia_tipo", table_name="laudo_operational_events")
    op.drop_index("ix_operational_event_laudo_criado", table_name="laudo_operational_events")
    op.drop_index("ix_laudo_operational_events_id", table_name="laudo_operational_events")
    op.drop_table("laudo_operational_events")

    op.drop_index("ix_approved_case_snapshot_family_approved", table_name="laudo_approved_case_snapshots")
    op.drop_index("ix_approved_case_snapshot_empresa_familia", table_name="laudo_approved_case_snapshots")
    op.drop_index("ix_approved_case_snapshot_laudo", table_name="laudo_approved_case_snapshots")
    op.drop_index("ix_laudo_approved_case_snapshots_id", table_name="laudo_approved_case_snapshots")
    op.drop_table("laudo_approved_case_snapshots")
