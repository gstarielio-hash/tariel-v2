from __future__ import annotations

from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, validates

from app.shared.db.models_base import Base, MixinAuditoria

_STATUS_CATALOGO_VALIDOS = ", ".join(repr(item) for item in ("rascunho", "publicado", "arquivado"))
_STATUS_MATERIAL_REAL_VALIDOS = ", ".join(repr(item) for item in ("sintetico", "parcial", "calibrado"))
_STATUS_TECNICO_VALIDOS = ", ".join(repr(item) for item in ("draft", "review", "ready", "deprecated"))
_CLASSIFICACAO_CATALOGO_VALIDAS = ", ".join(
    repr(item) for item in ("family", "inspection_method", "evidence_method")
)
_STATUS_LIFECYCLE_OFERTA_VALIDOS = ", ".join(
    repr(item) for item in ("draft", "testing", "active", "paused", "archived")
)
_MATERIAL_LEVEL_VALIDOS = ", ".join(repr(item) for item in ("synthetic", "partial", "real_calibrated"))
_STATUS_CALIBRACAO_VALIDOS = ", ".join(
    repr(item) for item in ("none", "synthetic_only", "partial_real", "real_calibrated")
)
_STATUS_RELEASE_VALIDOS = ", ".join(repr(item) for item in ("draft", "active", "paused", "expired"))
_CATEGORIA_METODO_VALIDAS = ", ".join(repr(item) for item in ("inspection_method", "evidence_method"))
_STATUS_EMISSAO_OFICIAL_VALIDOS = ", ".join(repr(item) for item in ("issued", "superseded", "revoked"))


def _normalizar_status_catalogo(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "rascunho",
        "rascunho": "rascunho",
        "draft": "rascunho",
        "publicado": "publicado",
        "published": "publicado",
        "arquivado": "arquivado",
        "archive": "arquivado",
        "archived": "arquivado",
    }
    if texto not in aliases:
        raise ValueError("Status do catálogo inválido.")
    return aliases[texto]


def _normalizar_status_material_real(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "sintetico",
        "sintetico": "sintetico",
        "sintetica": "sintetico",
        "base_sintetica": "sintetico",
        "parcial": "parcial",
        "misto": "parcial",
        "hibrido": "parcial",
        "material_real_parcial": "parcial",
        "calibrado": "calibrado",
        "real": "calibrado",
        "material_real": "calibrado",
    }
    if texto not in aliases:
        raise ValueError("Status de material real inválido.")
    return aliases[texto]


def _normalizar_status_tecnico(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "draft",
        "draft": "draft",
        "rascunho": "draft",
        "review": "review",
        "revisao": "review",
        "ready": "ready",
        "publicado": "ready",
        "deprecated": "deprecated",
        "arquivado": "deprecated",
        "archived": "deprecated",
    }
    if texto not in aliases:
        raise ValueError("Status técnico inválido.")
    return aliases[texto]


def _normalizar_classificacao_catalogo(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "family",
        "family": "family",
        "familia": "family",
        "inspection_method": "inspection_method",
        "metodo_inspecao": "inspection_method",
        "inspection": "inspection_method",
        "evidence_method": "evidence_method",
        "metodo_evidencia": "evidence_method",
        "evidence": "evidence_method",
    }
    if texto not in aliases:
        raise ValueError("Classificação do catálogo inválida.")
    return aliases[texto]


def _normalizar_lifecycle_oferta(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "draft",
        "draft": "draft",
        "rascunho": "draft",
        "testing": "testing",
        "teste": "testing",
        "active": "active",
        "ativo": "active",
        "paused": "paused",
        "pausado": "paused",
        "archived": "archived",
        "arquivado": "archived",
    }
    if texto not in aliases:
        raise ValueError("Lifecycle da oferta inválido.")
    return aliases[texto]


def _normalizar_material_level(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "synthetic",
        "synthetic": "synthetic",
        "sintetico": "synthetic",
        "partial": "partial",
        "parcial": "partial",
        "real_calibrated": "real_calibrated",
        "calibrado": "real_calibrated",
        "real": "real_calibrated",
    }
    if texto not in aliases:
        raise ValueError("Material level inválido.")
    return aliases[texto]


def _normalizar_status_calibracao(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "none",
        "none": "none",
        "nenhum": "none",
        "synthetic_only": "synthetic_only",
        "sintetico": "synthetic_only",
        "partial_real": "partial_real",
        "parcial": "partial_real",
        "real_calibrated": "real_calibrated",
        "calibrado": "real_calibrated",
    }
    if texto not in aliases:
        raise ValueError("Status de calibração inválido.")
    return aliases[texto]


def _normalizar_status_release(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "draft",
        "draft": "draft",
        "rascunho": "draft",
        "active": "active",
        "ativo": "active",
        "paused": "paused",
        "pausado": "paused",
        "expired": "expired",
        "expirado": "expired",
    }
    if texto not in aliases:
        raise ValueError("Status de liberação inválido.")
    return aliases[texto]


def _normalizar_categoria_metodo(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "inspection_method",
        "inspection_method": "inspection_method",
        "metodo_inspecao": "inspection_method",
        "evidence_method": "evidence_method",
        "metodo_evidencia": "evidence_method",
    }
    if texto not in aliases:
        raise ValueError("Categoria do método inválida.")
    return aliases[texto]


def _normalizar_status_emissao_oficial(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "issued",
        "issued": "issued",
        "emitido": "issued",
        "active": "issued",
        "superseded": "superseded",
        "substituido": "superseded",
        "reissued": "superseded",
        "revoked": "revoked",
        "revogado": "revoked",
    }
    if texto not in aliases:
        raise ValueError("Status da emissão oficial inválido.")
    return aliases[texto]


class FamiliaLaudoCatalogo(MixinAuditoria, Base):
    __tablename__ = "familias_laudo_catalogo"
    __table_args__ = (
        CheckConstraint(f"status_catalogo IN ({_STATUS_CATALOGO_VALIDOS})", name="ck_familia_catalogo_status"),
        CheckConstraint("schema_version >= 1", name="ck_familia_catalogo_schema_version"),
        CheckConstraint(f"technical_status IN ({_STATUS_TECNICO_VALIDOS})", name="ck_familia_catalogo_technical_status"),
        CheckConstraint(
            f"catalog_classification IN ({_CLASSIFICACAO_CATALOGO_VALIDAS})",
            name="ck_familia_catalogo_classification",
        ),
        UniqueConstraint("family_key", name="uq_familia_catalogo_family_key"),
        Index("ix_familia_catalogo_status", "status_catalogo"),
        Index("ix_familia_catalogo_macro_categoria", "macro_categoria"),
        Index("ix_familia_catalogo_technical_status", "technical_status"),
        Index("ix_familia_catalogo_classification", "catalog_classification"),
        Index("ix_familia_catalogo_nr_key", "nr_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_key = Column(String(120), nullable=False, unique=True, index=True)
    macro_categoria = Column(String(80), nullable=True)
    nr_key = Column(String(40), nullable=True)
    nome_exibicao = Column(String(180), nullable=False)
    descricao = Column(Text, nullable=True)
    status_catalogo = Column(String(20), nullable=False, default="rascunho")
    technical_status = Column(String(20), nullable=False, default="draft")
    catalog_classification = Column(String(24), nullable=False, default="family")
    schema_version = Column(Integer, nullable=False, default=1)
    evidence_policy_json = Column(JSON, nullable=True)
    review_policy_json = Column(JSON, nullable=True)
    output_schema_seed_json = Column(JSON, nullable=True)
    governance_metadata_json = Column(JSON, nullable=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    publicado_em = Column(DateTime(timezone=True), nullable=True)

    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])
    oferta_comercial = relationship(
        "OfertaComercialFamiliaLaudo",
        back_populates="familia",
        cascade="all, delete-orphan",
        uselist=False,
    )
    modos_tecnicos = relationship(
        "ModoTecnicoFamiliaLaudo",
        back_populates="familia",
        cascade="all, delete-orphan",
        order_by="ModoTecnicoFamiliaLaudo.nome_exibicao.asc()",
    )
    calibracao = relationship(
        "CalibracaoFamiliaLaudo",
        back_populates="familia",
        cascade="all, delete-orphan",
        uselist=False,
    )
    tenant_releases = relationship(
        "TenantFamilyReleaseLaudo",
        back_populates="familia",
        cascade="all, delete-orphan",
    )

    @validates("status_catalogo")
    def _validar_status_catalogo(self, _key: str, valor: Any) -> str:
        return _normalizar_status_catalogo(valor)

    @validates("technical_status")
    def _validar_status_tecnico(self, _key: str, valor: Any) -> str:
        return _normalizar_status_tecnico(valor)

    @validates("catalog_classification")
    def _validar_classificacao_catalogo(self, _key: str, valor: Any) -> str:
        return _normalizar_classificacao_catalogo(valor)


class OfertaComercialFamiliaLaudo(MixinAuditoria, Base):
    __tablename__ = "familias_laudo_ofertas_comerciais"
    __table_args__ = (
        CheckConstraint("versao_oferta >= 1", name="ck_familia_oferta_versao"),
        CheckConstraint("prazo_padrao_dias IS NULL OR prazo_padrao_dias >= 0", name="ck_familia_oferta_prazo"),
        CheckConstraint(
            f"material_real_status IN ({_STATUS_MATERIAL_REAL_VALIDOS})",
            name="ck_familia_oferta_material_real_status",
        ),
        CheckConstraint(
            f"material_level IN ({_MATERIAL_LEVEL_VALIDOS})",
            name="ck_familia_oferta_material_level",
        ),
        CheckConstraint(
            f"lifecycle_status IN ({_STATUS_LIFECYCLE_OFERTA_VALIDOS})",
            name="ck_familia_oferta_lifecycle",
        ),
        UniqueConstraint("family_id", name="uq_familia_oferta_family"),
        UniqueConstraint("offer_key", name="uq_familia_oferta_offer_key"),
        Index("ix_familia_oferta_ativa", "ativo_comercial"),
        Index("ix_familia_oferta_material_real_status", "material_real_status"),
        Index("ix_familia_oferta_pacote", "pacote_comercial"),
        Index("ix_familia_oferta_lifecycle", "lifecycle_status"),
        Index("ix_familia_oferta_showcase", "showcase_enabled"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("familias_laudo_catalogo.id", ondelete="CASCADE"), nullable=False, index=True)
    family_mode_id = Column(
        Integer,
        ForeignKey("familias_laudo_modos_tecnicos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    offer_key = Column(String(120), nullable=True, unique=True, index=True)
    nome_oferta = Column(String(180), nullable=False)
    descricao_comercial = Column(Text, nullable=True)
    pacote_comercial = Column(String(80), nullable=True)
    prazo_padrao_dias = Column(Integer, nullable=True)
    ativo_comercial = Column(Boolean, nullable=False, default=False)
    lifecycle_status = Column(String(20), nullable=False, default="draft")
    showcase_enabled = Column(Boolean, nullable=False, default=False)
    versao_oferta = Column(Integer, nullable=False, default=1)
    material_real_status = Column(String(20), nullable=False, default="sintetico")
    material_level = Column(String(24), nullable=False, default="synthetic")
    escopo_json = Column(JSON, nullable=True)
    exclusoes_json = Column(JSON, nullable=True)
    insumos_minimos_json = Column(JSON, nullable=True)
    variantes_json = Column(JSON, nullable=True)
    template_default_code = Column(String(120), nullable=True)
    flags_json = Column(JSON, nullable=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    publicado_em = Column(DateTime(timezone=True), nullable=True)

    familia = relationship("FamiliaLaudoCatalogo", back_populates="oferta_comercial")
    family_mode = relationship("ModoTecnicoFamiliaLaudo", back_populates="ofertas")
    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])

    @validates("material_real_status")
    def _validar_material_real_status(self, _key: str, valor: Any) -> str:
        return _normalizar_status_material_real(valor)

    @validates("material_level")
    def _validar_material_level(self, _key: str, valor: Any) -> str:
        return _normalizar_material_level(valor)

    @validates("lifecycle_status")
    def _validar_lifecycle_status(self, _key: str, valor: Any) -> str:
        return _normalizar_lifecycle_oferta(valor)


class ModoTecnicoFamiliaLaudo(MixinAuditoria, Base):
    __tablename__ = "familias_laudo_modos_tecnicos"
    __table_args__ = (
        UniqueConstraint("family_id", "mode_key", name="uq_familia_modo_family_mode"),
        Index("ix_familia_modo_family_ativo", "family_id", "ativo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("familias_laudo_catalogo.id", ondelete="CASCADE"), nullable=False, index=True)
    mode_key = Column(String(80), nullable=False)
    nome_exibicao = Column(String(120), nullable=False)
    descricao = Column(Text, nullable=True)
    regras_adicionais_json = Column(JSON, nullable=True)
    compatibilidade_template_json = Column(JSON, nullable=True)
    compatibilidade_oferta_json = Column(JSON, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)

    familia = relationship("FamiliaLaudoCatalogo", back_populates="modos_tecnicos")
    ofertas = relationship("OfertaComercialFamiliaLaudo", back_populates="family_mode")
    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])


class CalibracaoFamiliaLaudo(MixinAuditoria, Base):
    __tablename__ = "familias_laudo_calibracoes"
    __table_args__ = (
        CheckConstraint(
            f"calibration_status IN ({_STATUS_CALIBRACAO_VALIDOS})",
            name="ck_familia_calibracao_status",
        ),
        UniqueConstraint("family_id", name="uq_familia_calibracao_family"),
        Index("ix_familia_calibracao_status", "calibration_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("familias_laudo_catalogo.id", ondelete="CASCADE"), nullable=False, index=True)
    calibration_status = Column(String(24), nullable=False, default="none")
    reference_source = Column(String(255), nullable=True)
    last_calibrated_at = Column(DateTime(timezone=True), nullable=True)
    summary_of_adjustments = Column(Text, nullable=True)
    changed_fields_json = Column(JSON, nullable=True)
    changed_language_notes = Column(Text, nullable=True)
    attachments_json = Column(JSON, nullable=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)

    familia = relationship("FamiliaLaudoCatalogo", back_populates="calibracao")
    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])

    @validates("calibration_status")
    def _validar_calibration_status(self, _key: str, valor: Any) -> str:
        return _normalizar_status_calibracao(valor)


class MetodoCatalogoInspecao(MixinAuditoria, Base):
    __tablename__ = "catalogo_metodos_inspecao"
    __table_args__ = (
        CheckConstraint(f"categoria IN ({_CATEGORIA_METODO_VALIDAS})", name="ck_catalogo_metodo_categoria"),
        UniqueConstraint("method_key", name="uq_catalogo_metodo_method_key"),
        Index("ix_catalogo_metodo_categoria_ativo", "categoria", "ativo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    method_key = Column(String(80), nullable=False, unique=True, index=True)
    nome_exibicao = Column(String(120), nullable=False)
    categoria = Column(String(24), nullable=False, default="inspection_method")
    ativo = Column(Boolean, nullable=False, default=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)

    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])

    @validates("categoria")
    def _validar_categoria(self, _key: str, valor: Any) -> str:
        return _normalizar_categoria_metodo(valor)


class TenantFamilyReleaseLaudo(MixinAuditoria, Base):
    __tablename__ = "tenant_family_releases"
    __table_args__ = (
        CheckConstraint(f"release_status IN ({_STATUS_RELEASE_VALIDOS})", name="ck_tenant_family_release_status"),
        UniqueConstraint("tenant_id", "family_id", name="uq_tenant_family_release_family"),
        Index("ix_tenant_family_release_tenant_status", "tenant_id", "release_status"),
        Index("ix_tenant_family_release_offer", "tenant_id", "offer_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id = Column(Integer, ForeignKey("familias_laudo_catalogo.id", ondelete="CASCADE"), nullable=False, index=True)
    offer_id = Column(
        Integer,
        ForeignKey("familias_laudo_ofertas_comerciais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    allowed_modes_json = Column(JSON, nullable=True)
    allowed_offers_json = Column(JSON, nullable=True)
    allowed_templates_json = Column(JSON, nullable=True)
    allowed_variants_json = Column(JSON, nullable=True)
    governance_policy_json = Column(JSON, nullable=True)
    default_template_code = Column(String(120), nullable=True)
    release_status = Column(String(20), nullable=False, default="draft")
    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)

    familia = relationship("FamiliaLaudoCatalogo", back_populates="tenant_releases")
    oferta = relationship("OfertaComercialFamiliaLaudo")
    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])

    @validates("release_status")
    def _validar_status_release(self, _key: str, valor: Any) -> str:
        return _normalizar_status_release(valor)


class SignatarioGovernadoLaudo(MixinAuditoria, Base):
    __tablename__ = "signatarios_governados_laudo"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "nome",
            "registro_profissional",
            name="uq_signatario_governado_tenant_nome_registro",
        ),
        Index("ix_signatario_governado_tenant_ativo", "tenant_id", "ativo"),
        Index("ix_signatario_governado_tenant_validade", "tenant_id", "valid_until"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(160), nullable=False)
    funcao = Column(String(120), nullable=False)
    registro_profissional = Column(String(80), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    allowed_family_keys_json = Column(JSON, nullable=True)
    governance_metadata_json = Column(JSON, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    observacoes = Column(Text, nullable=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)

    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])


class EmissaoOficialLaudo(MixinAuditoria, Base):
    __tablename__ = "emissoes_oficiais_laudo"
    __table_args__ = (
        CheckConstraint(
            f"issue_state IN ({_STATUS_EMISSAO_OFICIAL_VALIDOS})",
            name="ck_emissao_oficial_issue_state",
        ),
        UniqueConstraint("issue_number", name="uq_emissao_oficial_issue_number"),
        Index("ix_emissao_oficial_laudo_estado", "laudo_id", "issue_state"),
        Index("ix_emissao_oficial_tenant_emitida", "tenant_id", "issued_at"),
        Index("ix_emissao_oficial_hash_pacote", "package_sha256"),
        Index("ix_emissao_oficial_hash_fingerprint", "package_fingerprint_sha256"),
    )

    id = Column(Integer, primary_key=True, index=True)
    laudo_id = Column(Integer, ForeignKey("laudos.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    approval_snapshot_id = Column(
        Integer,
        ForeignKey("laudo_approved_case_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    signatory_id = Column(
        Integer,
        ForeignKey("signatarios_governados_laudo.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    issued_by_user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    superseded_by_issue_id = Column(
        Integer,
        ForeignKey("emissoes_oficiais_laudo.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    issue_number = Column(String(80), nullable=False, unique=True, index=True)
    issue_state = Column(String(20), nullable=False, default="issued")
    issued_at = Column(DateTime(timezone=True), nullable=False)
    superseded_at = Column(DateTime(timezone=True), nullable=True)
    verification_hash = Column(String(64), nullable=True, index=True)
    public_verification_url = Column(String(400), nullable=True)
    package_sha256 = Column(String(64), nullable=False)
    package_fingerprint_sha256 = Column(String(64), nullable=False)
    package_filename = Column(String(220), nullable=True)
    package_storage_path = Column(String(600), nullable=True)
    package_size_bytes = Column(Integer, nullable=True)
    manifest_json = Column(JSON, nullable=True)
    issue_context_json = Column(JSON, nullable=True)

    laudo = relationship("Laudo", foreign_keys=[laudo_id])
    tenant = relationship("Empresa", foreign_keys=[tenant_id])
    approval_snapshot = relationship("ApprovedCaseSnapshot", foreign_keys=[approval_snapshot_id])
    signatory = relationship("SignatarioGovernadoLaudo", foreign_keys=[signatory_id])
    issued_by_user = relationship("Usuario", foreign_keys=[issued_by_user_id])
    superseded_by_issue = relationship("EmissaoOficialLaudo", remote_side=[id], foreign_keys=[superseded_by_issue_id])

    @validates("issue_state")
    def _validar_issue_state(self, _key: str, valor: Any) -> str:
        return _normalizar_status_emissao_oficial(valor)


class AtivacaoCatalogoEmpresaLaudo(MixinAuditoria, Base):
    __tablename__ = "empresa_catalogo_laudo_ativacoes"
    __table_args__ = (
        CheckConstraint("variant_ordem IS NULL OR variant_ordem >= 0", name="ck_empresa_catalogo_variant_ordem"),
        UniqueConstraint("empresa_id", "family_key", "variant_key", name="uq_empresa_catalogo_family_variant"),
        Index("ix_empresa_catalogo_empresa_ativo", "empresa_id", "ativo"),
        Index("ix_empresa_catalogo_runtime", "empresa_id", "runtime_template_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id = Column(Integer, ForeignKey("familias_laudo_catalogo.id", ondelete="SET NULL"), nullable=True, index=True)
    oferta_id = Column(
        Integer,
        ForeignKey("familias_laudo_ofertas_comerciais.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    family_key = Column(String(120), nullable=False)
    family_label = Column(String(180), nullable=False)
    group_label = Column(String(120), nullable=True)
    offer_name = Column(String(180), nullable=True)
    variant_key = Column(String(80), nullable=False)
    variant_label = Column(String(120), nullable=False)
    variant_ordem = Column(Integer, nullable=True)
    runtime_template_code = Column(String(80), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)

    familia = relationship("FamiliaLaudoCatalogo")
    oferta = relationship("OfertaComercialFamiliaLaudo")
    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])
