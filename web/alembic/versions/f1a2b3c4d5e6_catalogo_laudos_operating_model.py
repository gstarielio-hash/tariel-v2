"""Refatora o catálogo de laudos em camadas técnicas, comerciais e de release.

Revision ID: f1a2b3c4d5e6
Revises: e6f4c2a9b1d3
Create Date: 2026-04-09 14:20:00.000000
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "e6f4c2a9b1d3"
branch_labels = None
depends_on = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalizar_slug(valor: str, *, max_len: int) -> str:
    texto = str(valor or "").strip().lower()
    texto = (
        texto.replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    return texto[:max_len]


def _infer_nr_key(family_key: str, macro_categoria: str | None) -> str | None:
    bruto = str(macro_categoria or "").strip().lower()
    if not bruto and str(family_key or "").startswith("nr"):
        match = re.match(r"^(nr\d+[a-z]*)", str(family_key or "").strip().lower())
        bruto = match.group(1) if match else ""
    if not bruto:
        return None
    bruto = bruto.replace(" ", "").replace("/", "").replace("-", "")
    match = re.search(r"(nr\d+[a-z]*)", bruto)
    return match.group(1)[:40] if match else None


def _infer_classification(family_key: str, nome_exibicao: str | None, macro_categoria: str | None) -> str:
    family_norm = str(family_key or "").strip().lower()
    texto = " ".join(
        (
            family_norm,
            str(nome_exibicao or "").strip().lower(),
            str(macro_categoria or "").strip().lower(),
        )
    )
    pistas = ("ultrassom", "liquido_penetrante", "particula_magnetica", "visual", "estanqueidade", "hidrostatic")
    if family_norm.startswith("end_") or any(item in texto for item in pistas):
        return "inspection_method"
    return "family"


def _material_level_from_legacy(valor: str | None) -> str:
    texto = str(valor or "").strip().lower()
    if texto == "calibrado":
        return "real_calibrated"
    if texto == "parcial":
        return "partial"
    return "synthetic"


def _calibration_status_from_legacy(valor: str | None) -> str:
    texto = str(valor or "").strip().lower()
    if texto == "calibrado":
        return "real_calibrated"
    if texto == "parcial":
        return "partial_real"
    if texto == "sintetico":
        return "synthetic_only"
    return "none"


def _extract_template_default(variantes_json: object) -> str | None:
    if not variantes_json:
        return None
    payload = variantes_json
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None
    if not isinstance(payload, list):
        return None
    for item in payload:
        if not isinstance(item, dict):
            continue
        template_code = _normalizar_slug(str(item.get("template_code") or ""), max_len=120)
        if template_code:
            return template_code
    return None


def _coerce_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _table_exists(bind, table_name: str) -> bool:
    return table_name in sa.inspect(bind).get_table_names()


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    if not _table_exists(bind, table_name):
        return False
    return column_name in {item["name"] for item in sa.inspect(bind).get_columns(table_name)}


def _index_exists(bind, table_name: str, index_name: str) -> bool:
    if not _table_exists(bind, table_name):
        return False
    return index_name in {item["name"] for item in sa.inspect(bind).get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()

    if not _column_exists(bind, "familias_laudo_catalogo", "nr_key"):
        op.add_column("familias_laudo_catalogo", sa.Column("nr_key", sa.String(length=40), nullable=True))
    if not _column_exists(bind, "familias_laudo_catalogo", "technical_status"):
        op.add_column(
            "familias_laudo_catalogo",
            sa.Column("technical_status", sa.String(length=20), nullable=False, server_default="draft"),
        )
    if not _column_exists(bind, "familias_laudo_catalogo", "catalog_classification"):
        op.add_column(
            "familias_laudo_catalogo",
            sa.Column("catalog_classification", sa.String(length=24), nullable=False, server_default="family"),
        )
    if not _column_exists(bind, "familias_laudo_catalogo", "governance_metadata_json"):
        op.add_column("familias_laudo_catalogo", sa.Column("governance_metadata_json", sa.JSON(), nullable=True))
    if not _index_exists(bind, "familias_laudo_catalogo", "ix_familia_catalogo_technical_status"):
        op.create_index("ix_familia_catalogo_technical_status", "familias_laudo_catalogo", ["technical_status"], unique=False)
    if not _index_exists(bind, "familias_laudo_catalogo", "ix_familia_catalogo_classification"):
        op.create_index("ix_familia_catalogo_classification", "familias_laudo_catalogo", ["catalog_classification"], unique=False)
    if not _index_exists(bind, "familias_laudo_catalogo", "ix_familia_catalogo_nr_key"):
        op.create_index("ix_familia_catalogo_nr_key", "familias_laudo_catalogo", ["nr_key"], unique=False)

    if not _column_exists(bind, "familias_laudo_ofertas_comerciais", "family_mode_id"):
        op.add_column(
            "familias_laudo_ofertas_comerciais",
            sa.Column("family_mode_id", sa.Integer(), nullable=True),
        )
    if not _column_exists(bind, "familias_laudo_ofertas_comerciais", "offer_key"):
        op.add_column("familias_laudo_ofertas_comerciais", sa.Column("offer_key", sa.String(length=120), nullable=True))
    if not _column_exists(bind, "familias_laudo_ofertas_comerciais", "lifecycle_status"):
        op.add_column(
            "familias_laudo_ofertas_comerciais",
            sa.Column("lifecycle_status", sa.String(length=20), nullable=False, server_default="draft"),
        )
    if not _column_exists(bind, "familias_laudo_ofertas_comerciais", "showcase_enabled"):
        op.add_column(
            "familias_laudo_ofertas_comerciais",
            sa.Column("showcase_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if not _column_exists(bind, "familias_laudo_ofertas_comerciais", "material_level"):
        op.add_column(
            "familias_laudo_ofertas_comerciais",
            sa.Column("material_level", sa.String(length=24), nullable=False, server_default="synthetic"),
        )
    if not _column_exists(bind, "familias_laudo_ofertas_comerciais", "template_default_code"):
        op.add_column("familias_laudo_ofertas_comerciais", sa.Column("template_default_code", sa.String(length=120), nullable=True))
    if not _column_exists(bind, "familias_laudo_ofertas_comerciais", "flags_json"):
        op.add_column("familias_laudo_ofertas_comerciais", sa.Column("flags_json", sa.JSON(), nullable=True))
    if not _index_exists(bind, "familias_laudo_ofertas_comerciais", "ix_familia_oferta_lifecycle"):
        op.create_index("ix_familia_oferta_lifecycle", "familias_laudo_ofertas_comerciais", ["lifecycle_status"], unique=False)
    if not _index_exists(bind, "familias_laudo_ofertas_comerciais", "ix_familia_oferta_showcase"):
        op.create_index("ix_familia_oferta_showcase", "familias_laudo_ofertas_comerciais", ["showcase_enabled"], unique=False)
    if not _index_exists(bind, "familias_laudo_ofertas_comerciais", "ix_familia_oferta_offer_key_unique"):
        op.create_index(
            "ix_familia_oferta_offer_key_unique",
            "familias_laudo_ofertas_comerciais",
            ["offer_key"],
            unique=True,
        )

    if not _table_exists(bind, "familias_laudo_modos_tecnicos"):
        op.create_table(
        "familias_laudo_modos_tecnicos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("mode_key", sa.String(length=80), nullable=False),
        sa.Column("nome_exibicao", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("regras_adicionais_json", sa.JSON(), nullable=True),
        sa.Column("compatibilidade_template_json", sa.JSON(), nullable=True),
        sa.Column("compatibilidade_oferta_json", sa.JSON(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["family_id"], ["familias_laudo_catalogo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("family_id", "mode_key", name="uq_familia_modo_family_mode"),
    )
    if not _index_exists(bind, "familias_laudo_modos_tecnicos", "ix_familias_laudo_modos_tecnicos_id"):
        op.create_index("ix_familias_laudo_modos_tecnicos_id", "familias_laudo_modos_tecnicos", ["id"], unique=False)
    if not _index_exists(bind, "familias_laudo_modos_tecnicos", "ix_familia_modo_family_ativo"):
        op.create_index("ix_familia_modo_family_ativo", "familias_laudo_modos_tecnicos", ["family_id", "ativo"], unique=False)

    if bind.dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_familia_oferta_family_mode",
            "familias_laudo_ofertas_comerciais",
            "familias_laudo_modos_tecnicos",
            ["family_mode_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not _table_exists(bind, "familias_laudo_calibracoes"):
        op.create_table(
        "familias_laudo_calibracoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("calibration_status", sa.String(length=24), nullable=False),
        sa.Column("reference_source", sa.String(length=255), nullable=True),
        sa.Column("last_calibrated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_of_adjustments", sa.Text(), nullable=True),
        sa.Column("changed_fields_json", sa.JSON(), nullable=True),
        sa.Column("changed_language_notes", sa.Text(), nullable=True),
        sa.Column("attachments_json", sa.JSON(), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "calibration_status IN ('none', 'synthetic_only', 'partial_real', 'real_calibrated')",
            name="ck_familia_calibracao_status",
        ),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["family_id"], ["familias_laudo_catalogo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("family_id", name="uq_familia_calibracao_family"),
    )
    if not _index_exists(bind, "familias_laudo_calibracoes", "ix_familias_laudo_calibracoes_id"):
        op.create_index("ix_familias_laudo_calibracoes_id", "familias_laudo_calibracoes", ["id"], unique=False)
    if not _index_exists(bind, "familias_laudo_calibracoes", "ix_familia_calibracao_status"):
        op.create_index("ix_familia_calibracao_status", "familias_laudo_calibracoes", ["calibration_status"], unique=False)

    if not _table_exists(bind, "catalogo_metodos_inspecao"):
        op.create_table(
        "catalogo_metodos_inspecao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("method_key", sa.String(length=80), nullable=False),
        sa.Column("nome_exibicao", sa.String(length=120), nullable=False),
        sa.Column("categoria", sa.String(length=24), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "categoria IN ('inspection_method', 'evidence_method')",
            name="ck_catalogo_metodo_categoria",
        ),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("method_key", name="uq_catalogo_metodo_method_key"),
    )
    if not _index_exists(bind, "catalogo_metodos_inspecao", "ix_catalogo_metodos_inspecao_id"):
        op.create_index("ix_catalogo_metodos_inspecao_id", "catalogo_metodos_inspecao", ["id"], unique=False)
    if not _index_exists(bind, "catalogo_metodos_inspecao", "ix_catalogo_metodo_categoria_ativo"):
        op.create_index("ix_catalogo_metodo_categoria_ativo", "catalogo_metodos_inspecao", ["categoria", "ativo"], unique=False)
    if not _index_exists(bind, "catalogo_metodos_inspecao", "ix_catalogo_metodos_inspecao_method_key"):
        op.create_index("ix_catalogo_metodos_inspecao_method_key", "catalogo_metodos_inspecao", ["method_key"], unique=True)

    if not _table_exists(bind, "tenant_family_releases"):
        op.create_table(
        "tenant_family_releases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.Integer(), nullable=True),
        sa.Column("allowed_modes_json", sa.JSON(), nullable=True),
        sa.Column("allowed_offers_json", sa.JSON(), nullable=True),
        sa.Column("allowed_templates_json", sa.JSON(), nullable=True),
        sa.Column("allowed_variants_json", sa.JSON(), nullable=True),
        sa.Column("default_template_code", sa.String(length=120), nullable=True),
        sa.Column("release_status", sa.String(length=20), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "release_status IN ('draft', 'active', 'paused', 'expired')",
            name="ck_tenant_family_release_status",
        ),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["family_id"], ["familias_laudo_catalogo.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["offer_id"], ["familias_laudo_ofertas_comerciais.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "family_id", name="uq_tenant_family_release_family"),
    )
    if not _index_exists(bind, "tenant_family_releases", "ix_tenant_family_releases_id"):
        op.create_index("ix_tenant_family_releases_id", "tenant_family_releases", ["id"], unique=False)
    if not _index_exists(bind, "tenant_family_releases", "ix_tenant_family_release_tenant_status"):
        op.create_index("ix_tenant_family_release_tenant_status", "tenant_family_releases", ["tenant_id", "release_status"], unique=False)
    if not _index_exists(bind, "tenant_family_releases", "ix_tenant_family_release_offer"):
        op.create_index("ix_tenant_family_release_offer", "tenant_family_releases", ["tenant_id", "offer_id"], unique=False)

    family_rows = bind.execute(
        sa.text(
            "SELECT id, family_key, macro_categoria, nome_exibicao, status_catalogo FROM familias_laudo_catalogo"
        )
    ).mappings().all()
    for row in family_rows:
        status_catalogo = str(row["status_catalogo"] or "").strip().lower()
        technical_status = "ready" if status_catalogo == "publicado" else "deprecated" if status_catalogo == "arquivado" else "draft"
        bind.execute(
            sa.text(
                """
                UPDATE familias_laudo_catalogo
                   SET nr_key = :nr_key,
                       technical_status = :technical_status,
                       catalog_classification = :catalog_classification
                 WHERE id = :family_id
                """
            ),
            {
                "family_id": int(row["id"]),
                "nr_key": _infer_nr_key(str(row["family_key"] or ""), row["macro_categoria"]),
                "technical_status": technical_status,
                "catalog_classification": _infer_classification(
                    str(row["family_key"] or ""),
                    row["nome_exibicao"],
                    row["macro_categoria"],
                ),
            },
        )

    offer_rows = bind.execute(
        sa.text(
            """
            SELECT o.id,
                   o.family_id,
                   f.family_key,
                   o.ativo_comercial,
                   o.material_real_status,
                   o.variantes_json,
                   o.criado_por_id,
                   o.criado_em,
                   o.atualizado_em,
                   o.publicado_em
              FROM familias_laudo_ofertas_comerciais o
              JOIN familias_laudo_catalogo f ON f.id = o.family_id
            """
        )
    ).mappings().all()
    calibration_rows: list[dict[str, object]] = []
    offer_id_by_family_id: dict[int, int] = {}
    now = _utcnow()
    for row in offer_rows:
        family_id = int(row["family_id"])
        offer_id = int(row["id"])
        offer_id_by_family_id[family_id] = offer_id
        lifecycle_status = "active" if bool(row["ativo_comercial"]) else "draft"
        material_level = _material_level_from_legacy(row["material_real_status"])
        bind.execute(
            sa.text(
                """
                UPDATE familias_laudo_ofertas_comerciais
                   SET offer_key = :offer_key,
                       lifecycle_status = :lifecycle_status,
                       showcase_enabled = :showcase_enabled,
                       material_level = :material_level,
                       template_default_code = :template_default_code
                 WHERE id = :offer_id
                """
            ),
            {
                "offer_id": offer_id,
                "offer_key": _normalizar_slug(str(row["family_key"] or ""), max_len=120),
                "lifecycle_status": lifecycle_status,
                "showcase_enabled": bool(row["ativo_comercial"]),
                "material_level": material_level,
                "template_default_code": _extract_template_default(row["variantes_json"]),
            },
        )
        calibration_rows.append(
            {
                "family_id": family_id,
                "calibration_status": _calibration_status_from_legacy(row["material_real_status"]),
                "reference_source": "legacy_offer_material_status",
                "last_calibrated_at": _coerce_datetime(row["publicado_em"]) if row["material_real_status"] == "calibrado" else None,
                "summary_of_adjustments": "Migrado da leitura legada de material real da oferta comercial.",
                "changed_fields_json": None,
                "changed_language_notes": None,
                "attachments_json": None,
                "criado_por_id": row["criado_por_id"],
                "criado_em": _coerce_datetime(row["criado_em"]) or now,
                "atualizado_em": _coerce_datetime(row["atualizado_em"]) or _coerce_datetime(row["criado_em"]) or now,
            }
        )

    if calibration_rows:
        existing_calibrations = {
            int(item)
            for item in bind.execute(sa.text("SELECT family_id FROM familias_laudo_calibracoes")).scalars().all()
        }
        calibration_table = sa.table(
            "familias_laudo_calibracoes",
            sa.column("family_id", sa.Integer()),
            sa.column("calibration_status", sa.String()),
            sa.column("reference_source", sa.String()),
            sa.column("last_calibrated_at", sa.DateTime(timezone=True)),
            sa.column("summary_of_adjustments", sa.Text()),
            sa.column("changed_fields_json", sa.JSON()),
            sa.column("changed_language_notes", sa.Text()),
            sa.column("attachments_json", sa.JSON()),
            sa.column("criado_por_id", sa.Integer()),
            sa.column("criado_em", sa.DateTime(timezone=True)),
            sa.column("atualizado_em", sa.DateTime(timezone=True)),
        )
        op.bulk_insert(
            calibration_table,
            [item for item in calibration_rows if int(item["family_id"]) not in existing_calibrations],
        )

    method_table = sa.table(
        "catalogo_metodos_inspecao",
        sa.column("method_key", sa.String()),
        sa.column("nome_exibicao", sa.String()),
        sa.column("categoria", sa.String()),
        sa.column("ativo", sa.Boolean()),
        sa.column("criado_por_id", sa.Integer()),
        sa.column("criado_em", sa.DateTime(timezone=True)),
        sa.column("atualizado_em", sa.DateTime(timezone=True)),
    )
    existing_method_keys = {
        str(item)
        for item in bind.execute(sa.text("SELECT method_key FROM catalogo_metodos_inspecao")).scalars().all()
    }
    method_rows = [
            {
                "method_key": "ultrassom",
                "nome_exibicao": "Ultrassom",
                "categoria": "inspection_method",
                "ativo": True,
                "criado_por_id": None,
                "criado_em": now,
                "atualizado_em": now,
            },
            {
                "method_key": "liquido_penetrante",
                "nome_exibicao": "Líquido penetrante",
                "categoria": "inspection_method",
                "ativo": True,
                "criado_por_id": None,
                "criado_em": now,
                "atualizado_em": now,
            },
            {
                "method_key": "particula_magnetica",
                "nome_exibicao": "Partícula magnética",
                "categoria": "inspection_method",
                "ativo": True,
                "criado_por_id": None,
                "criado_em": now,
                "atualizado_em": now,
            },
            {
                "method_key": "visual",
                "nome_exibicao": "Visual",
                "categoria": "inspection_method",
                "ativo": True,
                "criado_por_id": None,
                "criado_em": now,
                "atualizado_em": now,
            },
            {
                "method_key": "estanqueidade",
                "nome_exibicao": "Estanqueidade",
                "categoria": "inspection_method",
                "ativo": True,
                "criado_por_id": None,
                "criado_em": now,
                "atualizado_em": now,
            },
            {
                "method_key": "hidrostatico",
                "nome_exibicao": "Hidrostático",
                "categoria": "inspection_method",
                "ativo": True,
                "criado_por_id": None,
                "criado_em": now,
                "atualizado_em": now,
            },
        ]
    if method_rows:
        op.bulk_insert(method_table, [item for item in method_rows if item["method_key"] not in existing_method_keys])

    activation_rows = bind.execute(
        sa.text(
            """
            SELECT id,
                   empresa_id,
                   family_id,
                   oferta_id,
                   family_key,
                   runtime_template_code,
                   variant_key,
                   criado_por_id,
                   criado_em,
                   atualizado_em
              FROM empresa_catalogo_laudo_ativacoes
             WHERE ativo = :ativo
             ORDER BY empresa_id ASC, family_key ASC, id ASC
            """
        ),
        {"ativo": True},
    ).mappings().all()
    grouped: dict[tuple[int, int], dict[str, object]] = {}
    for row in activation_rows:
        if row["family_id"] is None:
            continue
        family_id = int(row["family_id"])
        key = (int(row["empresa_id"]), family_id)
        bucket = grouped.setdefault(
            key,
            {
                "tenant_id": int(row["empresa_id"]),
                "family_id": family_id,
                "offer_id": int(row["oferta_id"]) if row["oferta_id"] is not None else offer_id_by_family_id.get(family_id),
                "allowed_modes_json": [],
                "allowed_offers_json": [],
                "allowed_templates_json": [],
                "allowed_variants_json": [],
                "default_template_code": None,
                "release_status": "active",
                "start_at": _coerce_datetime(row["criado_em"]) or now,
                "end_at": None,
                "observacoes": "Migrado da ativação legada por tenant.",
                "criado_por_id": row["criado_por_id"],
                "criado_em": _coerce_datetime(row["criado_em"]) or now,
                "atualizado_em": _coerce_datetime(row["atualizado_em"]) or _coerce_datetime(row["criado_em"]) or now,
            },
        )
        runtime = str(row["runtime_template_code"] or "").strip().lower()
        token = f"catalog:{str(row['family_key']).strip().lower()}:{str(row['variant_key']).strip().lower()}"
        if runtime and runtime not in bucket["allowed_templates_json"]:
            bucket["allowed_templates_json"].append(runtime)
        if token not in bucket["allowed_variants_json"]:
            bucket["allowed_variants_json"].append(token)
        if bucket["default_template_code"] is None and runtime:
            bucket["default_template_code"] = runtime
        offer_id = bucket["offer_id"]
        if offer_id is not None:
            offer_key = bind.execute(
                sa.text("SELECT offer_key FROM familias_laudo_ofertas_comerciais WHERE id = :offer_id"),
                {"offer_id": int(offer_id)},
            ).scalar_one_or_none()
            if offer_key and offer_key not in bucket["allowed_offers_json"]:
                bucket["allowed_offers_json"].append(str(offer_key))

    if grouped:
        existing_release_keys = {
            (int(item[0]), int(item[1]))
            for item in bind.execute(sa.text("SELECT tenant_id, family_id FROM tenant_family_releases")).all()
        }
        release_table = sa.table(
            "tenant_family_releases",
            sa.column("tenant_id", sa.Integer()),
            sa.column("family_id", sa.Integer()),
            sa.column("offer_id", sa.Integer()),
            sa.column("allowed_modes_json", sa.JSON()),
            sa.column("allowed_offers_json", sa.JSON()),
            sa.column("allowed_templates_json", sa.JSON()),
            sa.column("allowed_variants_json", sa.JSON()),
            sa.column("default_template_code", sa.String()),
            sa.column("release_status", sa.String()),
            sa.column("start_at", sa.DateTime(timezone=True)),
            sa.column("end_at", sa.DateTime(timezone=True)),
            sa.column("observacoes", sa.Text()),
            sa.column("criado_por_id", sa.Integer()),
            sa.column("criado_em", sa.DateTime(timezone=True)),
            sa.column("atualizado_em", sa.DateTime(timezone=True)),
        )
        op.bulk_insert(
            release_table,
            [
                item
                for item in grouped.values()
                if (int(item["tenant_id"]), int(item["family_id"])) not in existing_release_keys
            ],
        )

    if bind.dialect.name != "sqlite":
        op.alter_column("familias_laudo_catalogo", "technical_status", server_default=None)
        op.alter_column("familias_laudo_catalogo", "catalog_classification", server_default=None)
        op.alter_column("familias_laudo_ofertas_comerciais", "lifecycle_status", server_default=None)
        op.alter_column("familias_laudo_ofertas_comerciais", "showcase_enabled", server_default=None)
        op.alter_column("familias_laudo_ofertas_comerciais", "material_level", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_tenant_family_release_offer", table_name="tenant_family_releases")
    op.drop_index("ix_tenant_family_release_tenant_status", table_name="tenant_family_releases")
    op.drop_index("ix_tenant_family_releases_id", table_name="tenant_family_releases")
    op.drop_table("tenant_family_releases")

    op.drop_index("ix_catalogo_metodos_inspecao_method_key", table_name="catalogo_metodos_inspecao")
    op.drop_index("ix_catalogo_metodo_categoria_ativo", table_name="catalogo_metodos_inspecao")
    op.drop_index("ix_catalogo_metodos_inspecao_id", table_name="catalogo_metodos_inspecao")
    op.drop_table("catalogo_metodos_inspecao")

    op.drop_index("ix_familia_calibracao_status", table_name="familias_laudo_calibracoes")
    op.drop_index("ix_familias_laudo_calibracoes_id", table_name="familias_laudo_calibracoes")
    op.drop_table("familias_laudo_calibracoes")

    op.drop_constraint("fk_familia_oferta_family_mode", "familias_laudo_ofertas_comerciais", type_="foreignkey")
    op.drop_index("ix_familia_modo_family_ativo", table_name="familias_laudo_modos_tecnicos")
    op.drop_index("ix_familias_laudo_modos_tecnicos_id", table_name="familias_laudo_modos_tecnicos")
    op.drop_table("familias_laudo_modos_tecnicos")

    op.drop_index("ix_familia_oferta_offer_key_unique", table_name="familias_laudo_ofertas_comerciais")
    op.drop_index("ix_familia_oferta_showcase", table_name="familias_laudo_ofertas_comerciais")
    op.drop_index("ix_familia_oferta_lifecycle", table_name="familias_laudo_ofertas_comerciais")
    op.drop_column("familias_laudo_ofertas_comerciais", "flags_json")
    op.drop_column("familias_laudo_ofertas_comerciais", "template_default_code")
    op.drop_column("familias_laudo_ofertas_comerciais", "material_level")
    op.drop_column("familias_laudo_ofertas_comerciais", "showcase_enabled")
    op.drop_column("familias_laudo_ofertas_comerciais", "lifecycle_status")
    op.drop_column("familias_laudo_ofertas_comerciais", "offer_key")
    op.drop_column("familias_laudo_ofertas_comerciais", "family_mode_id")

    op.drop_index("ix_familia_catalogo_nr_key", table_name="familias_laudo_catalogo")
    op.drop_index("ix_familia_catalogo_classification", table_name="familias_laudo_catalogo")
    op.drop_index("ix_familia_catalogo_technical_status", table_name="familias_laudo_catalogo")
    op.drop_column("familias_laudo_catalogo", "governance_metadata_json")
    op.drop_column("familias_laudo_catalogo", "catalog_classification")
    op.drop_column("familias_laudo_catalogo", "technical_status")
    op.drop_column("familias_laudo_catalogo", "nr_key")
