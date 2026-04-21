"""Contratos do domínio Mesa Avaliadora."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.domains.mesa.semantics import MesaItemKind, MesaMessageKind, MesaPendencyState


class EventoMesa(StrEnum):
    CANAL_ABERTO = "canal_aberto"
    MENSAGEM_ENVIADA = "mensagem_enviada"
    MENSAGEM_RECEBIDA = "mensagem_recebida"
    PENDENCIA_CRIADA = "pendencia_criada"
    PENDENCIA_RESOLVIDA = "pendencia_resolvida"


class MensagemMesa(BaseModel):
    laudo_id: int = Field(..., ge=1)
    autor_id: int = Field(..., ge=1)
    texto: str = Field(..., min_length=1, max_length=8000)
    referencia_mensagem_id: int | None = Field(default=None, ge=1)
    criado_em: datetime


class NotificacaoMesa(BaseModel):
    evento: EventoMesa
    laudo_id: int = Field(..., ge=1)
    origem: str = Field(..., min_length=2, max_length=40)
    resumo: str = Field(..., min_length=1, max_length=300)


class ResumoMensagensMesa(BaseModel):
    total: int = Field(default=0, ge=0)
    inspetor: int = Field(default=0, ge=0)
    ia: int = Field(default=0, ge=0)
    mesa: int = Field(default=0, ge=0)
    sistema_outros: int = Field(default=0, ge=0)


class ResumoEvidenciasMesa(BaseModel):
    total: int = Field(default=0, ge=0)
    textuais: int = Field(default=0, ge=0)
    fotos: int = Field(default=0, ge=0)
    documentos: int = Field(default=0, ge=0)


class ResumoPendenciasMesa(BaseModel):
    total: int = Field(default=0, ge=0)
    abertas: int = Field(default=0, ge=0)
    resolvidas: int = Field(default=0, ge=0)


class AnexoPacoteMesa(BaseModel):
    id: int = Field(..., ge=1)
    nome: str = Field(..., min_length=1, max_length=160)
    mime_type: str = Field(..., min_length=3, max_length=120)
    categoria: str = Field(..., min_length=4, max_length=20)
    tamanho_bytes: int = Field(default=0, ge=0)
    eh_imagem: bool = False


class MensagemPacoteMesa(BaseModel):
    id: int = Field(..., ge=1)
    tipo: str = Field(..., min_length=1, max_length=20)
    item_kind: MesaItemKind = "message"
    message_kind: MesaMessageKind = "system_message"
    pendency_state: MesaPendencyState = "not_applicable"
    texto: str = Field(default="", max_length=8000)
    criado_em: datetime
    remetente_id: int | None = Field(default=None, ge=1)
    lida: bool = False
    referencia_mensagem_id: int | None = Field(default=None, ge=1)
    resolvida_em: datetime | None = None
    resolvida_por_id: int | None = Field(default=None, ge=1)
    resolvida_por_nome: str | None = Field(default=None, max_length=160)
    anexos: list[AnexoPacoteMesa] = Field(default_factory=list)


class RevisaoPacoteMesa(BaseModel):
    numero_versao: int = Field(..., ge=1)
    origem: str = Field(..., min_length=1, max_length=20)
    resumo: str | None = Field(default=None, max_length=240)
    confianca_geral: str | None = Field(default=None, max_length=32)
    criado_em: datetime


class SecaoDocumentoEstruturadoPacoteMesa(BaseModel):
    key: str = Field(..., min_length=1, max_length=80)
    title: str = Field(..., min_length=1, max_length=120)
    status: str = Field(..., min_length=1, max_length=20)
    summary: str | None = Field(default=None, max_length=400)
    diff_short: str | None = Field(default=None, max_length=240)
    filled_fields: int = Field(default=0, ge=0)
    total_fields: int = Field(default=0, ge=0)


class DocumentoEstruturadoPacoteMesa(BaseModel):
    schema_type: str = Field(..., min_length=1, max_length=80)
    family_key: str | None = Field(default=None, max_length=120)
    family_label: str | None = Field(default=None, max_length=180)
    summary: str | None = Field(default=None, max_length=400)
    review_notes: str | None = Field(default=None, max_length=280)
    sections: list[SecaoDocumentoEstruturadoPacoteMesa] = Field(default_factory=list)


class RevisaoPorBlocoItemPacoteMesa(BaseModel):
    block_key: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=120)
    document_status: str = Field(..., min_length=1, max_length=20)
    review_status: str = Field(..., min_length=1, max_length=24)
    summary: str | None = Field(default=None, max_length=400)
    diff_short: str | None = Field(default=None, max_length=240)
    filled_fields: int = Field(default=0, ge=0)
    total_fields: int = Field(default=0, ge=0)
    coverage_total: int = Field(default=0, ge=0)
    coverage_alert_count: int = Field(default=0, ge=0)
    open_return_count: int = Field(default=0, ge=0)
    open_pendency_count: int = Field(default=0, ge=0)
    latest_return_at: datetime | None = None
    recommended_action: str | None = Field(default=None, max_length=280)


class RevisaoPorBlocoPacoteMesa(BaseModel):
    total_blocks: int = Field(default=0, ge=0)
    ready_blocks: int = Field(default=0, ge=0)
    attention_blocks: int = Field(default=0, ge=0)
    returned_blocks: int = Field(default=0, ge=0)
    items: list[RevisaoPorBlocoItemPacoteMesa] = Field(default_factory=list)


class CoverageMapItemPacoteMesa(BaseModel):
    evidence_key: str = Field(..., min_length=1, max_length=160)
    title: str = Field(..., min_length=1, max_length=180)
    kind: str = Field(..., min_length=1, max_length=40)
    status: str = Field(default="pending", min_length=2, max_length=24)
    required: bool = False
    source_status: str | None = Field(default=None, max_length=32)
    operational_status: str | None = Field(default=None, max_length=24)
    mesa_status: str | None = Field(default=None, max_length=24)
    component_type: str | None = Field(default=None, max_length=80)
    view_angle: str | None = Field(default=None, max_length=80)
    quality_score: int | None = Field(default=None, ge=0, le=100)
    coherence_score: int | None = Field(default=None, ge=0, le=100)
    replacement_evidence_key: str | None = Field(default=None, max_length=160)
    summary: str | None = Field(default=None, max_length=280)
    failure_reasons: list[str] = Field(default_factory=list)


class CoverageMapPacoteMesa(BaseModel):
    total_required: int = Field(default=0, ge=0)
    total_collected: int = Field(default=0, ge=0)
    total_accepted: int = Field(default=0, ge=0)
    total_missing: int = Field(default=0, ge=0)
    total_irregular: int = Field(default=0, ge=0)
    final_validation_mode: str | None = Field(default=None, max_length=40)
    items: list[CoverageMapItemPacoteMesa] = Field(default_factory=list)


class HistoricoRefazerInspetorItemPacoteMesa(BaseModel):
    id: int = Field(..., ge=1)
    irregularity_type: str = Field(..., min_length=3, max_length=64)
    severity: str = Field(..., min_length=3, max_length=16)
    status: str = Field(..., min_length=2, max_length=24)
    detected_by: str = Field(..., min_length=2, max_length=32)
    block_key: str | None = Field(default=None, max_length=120)
    evidence_key: str | None = Field(default=None, max_length=160)
    summary: str | None = Field(default=None, max_length=280)
    resolution_notes: str | None = Field(default=None, max_length=400)
    resolution_mode: str | None = Field(default=None, max_length=40)
    detected_at: datetime
    resolved_at: datetime | None = None
    detected_by_user_name: str | None = Field(default=None, max_length=160)
    resolved_by_user_name: str | None = Field(default=None, max_length=160)


class MemoriaOperacionalFrequenciaPacoteMesa(BaseModel):
    item_key: str = Field(..., min_length=1, max_length=160)
    count: int = Field(..., ge=0)


class MemoriaOperacionalFamiliaPacoteMesa(BaseModel):
    family_key: str = Field(..., min_length=1, max_length=120)
    approved_snapshot_count: int = Field(default=0, ge=0)
    operational_event_count: int = Field(default=0, ge=0)
    validated_evidence_count: int = Field(default=0, ge=0)
    open_irregularity_count: int = Field(default=0, ge=0)
    latest_approved_at: datetime | None = None
    latest_event_at: datetime | None = None
    top_event_types: list[MemoriaOperacionalFrequenciaPacoteMesa] = Field(default_factory=list)
    top_open_irregularities: list[MemoriaOperacionalFrequenciaPacoteMesa] = Field(default_factory=list)


class HistoricoInspecaoDiffItemPacoteMesa(BaseModel):
    path: str = Field(..., min_length=1, max_length=240)
    label: str = Field(..., min_length=1, max_length=240)
    change_type: str = Field(..., min_length=3, max_length=24)
    previous_value: str | None = Field(default=None, max_length=120)
    current_value: str | None = Field(default=None, max_length=120)


class HistoricoInspecaoDiffBlocoPacoteMesa(BaseModel):
    block_key: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=160)
    changed_count: int = Field(default=0, ge=0)
    added_count: int = Field(default=0, ge=0)
    removed_count: int = Field(default=0, ge=0)
    total_changes: int = Field(default=0, ge=0)
    identity_change_count: int = Field(default=0, ge=0)
    summary: str | None = Field(default=None, max_length=240)
    fields: list[HistoricoInspecaoDiffItemPacoteMesa] = Field(default_factory=list)


class HistoricoInspecaoDiffPacoteMesa(BaseModel):
    changed_count: int = Field(default=0, ge=0)
    added_count: int = Field(default=0, ge=0)
    removed_count: int = Field(default=0, ge=0)
    total_changes: int = Field(default=0, ge=0)
    identity_change_count: int = Field(default=0, ge=0)
    current_fields_count: int = Field(default=0, ge=0)
    reference_fields_count: int = Field(default=0, ge=0)
    summary: str | None = Field(default=None, max_length=240)
    highlights: list[HistoricoInspecaoDiffItemPacoteMesa] = Field(default_factory=list)
    identity_highlights: list[HistoricoInspecaoDiffItemPacoteMesa] = Field(default_factory=list)
    block_highlights: list[HistoricoInspecaoDiffBlocoPacoteMesa] = Field(default_factory=list)


class HistoricoInspecaoPacoteMesa(BaseModel):
    snapshot_id: int = Field(..., ge=1)
    source_laudo_id: int = Field(..., ge=1)
    source_codigo_hash: str | None = Field(default=None, max_length=32)
    approved_at: datetime | None = None
    approval_version: int | None = Field(default=None, ge=1)
    document_outcome: str | None = Field(default=None, max_length=80)
    matched_by: str | None = Field(default=None, max_length=40)
    match_score: int = Field(default=0, ge=0)
    prefilled_field_count: int = Field(default=0, ge=0)
    diff: HistoricoInspecaoDiffPacoteMesa = Field(default_factory=HistoricoInspecaoDiffPacoteMesa)


class VerificacaoPublicaPacoteMesa(BaseModel):
    codigo_hash: str = Field(..., min_length=6, max_length=32)
    hash_short: str = Field(..., min_length=4, max_length=8)
    verification_url: str = Field(..., min_length=12, max_length=400)
    qr_payload: str = Field(..., min_length=12, max_length=400)
    qr_image_data_uri: str | None = Field(default=None, max_length=12000)
    empresa_nome: str | None = Field(default=None, max_length=160)
    status_revisao: str | None = Field(default=None, max_length=40)
    status_visual_label: str | None = Field(default=None, max_length=120)
    status_conformidade: str | None = Field(default=None, max_length=40)
    approved_at: datetime | None = None
    approval_version: int | None = Field(default=None, ge=1)
    document_outcome: str | None = Field(default=None, max_length=80)


class AnexoPackItemPacoteMesa(BaseModel):
    item_key: str = Field(..., min_length=1, max_length=160)
    label: str = Field(..., min_length=1, max_length=180)
    category: str = Field(..., min_length=2, max_length=40)
    required: bool = False
    present: bool = False
    source: str = Field(..., min_length=2, max_length=40)
    summary: str | None = Field(default=None, max_length=280)
    mime_type: str | None = Field(default=None, max_length=120)
    size_bytes: int | None = Field(default=None, ge=0)
    file_name: str | None = Field(default=None, max_length=220)
    archive_path: str | None = Field(default=None, max_length=260)


class AnexoPackPacoteMesa(BaseModel):
    total_items: int = Field(default=0, ge=0)
    total_required: int = Field(default=0, ge=0)
    total_present: int = Field(default=0, ge=0)
    missing_required_count: int = Field(default=0, ge=0)
    document_count: int = Field(default=0, ge=0)
    image_count: int = Field(default=0, ge=0)
    virtual_count: int = Field(default=0, ge=0)
    ready_for_issue: bool = False
    missing_items: list[str] = Field(default_factory=list)
    items: list[AnexoPackItemPacoteMesa] = Field(default_factory=list)


class SignatarioGovernadoPacoteMesa(BaseModel):
    id: int = Field(..., ge=1)
    nome: str = Field(..., min_length=1, max_length=160)
    funcao: str = Field(..., min_length=1, max_length=120)
    registro_profissional: str | None = Field(default=None, max_length=80)
    valid_until: datetime | None = None
    status: str = Field(..., min_length=2, max_length=24)
    status_label: str = Field(..., min_length=2, max_length=80)
    ativo: bool = False
    allowed_family_keys: list[str] = Field(default_factory=list)
    observacoes: str | None = Field(default=None, max_length=280)


class EmissaoOficialBlockerPacoteMesa(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1, max_length=280)
    blocking: bool = True


class EmissaoOficialTrailEventoPacoteMesa(BaseModel):
    event_key: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=1, max_length=120)
    status: str = Field(..., min_length=2, max_length=24)
    status_label: str = Field(..., min_length=2, max_length=80)
    summary: str | None = Field(default=None, max_length=280)
    blocking: bool = False
    recorded_at: datetime | None = None


class EmissaoOficialAtualPacoteMesa(BaseModel):
    id: int = Field(..., ge=1)
    issue_number: str | None = Field(default=None, max_length=80)
    issue_state: str = Field(..., min_length=2, max_length=24)
    issue_state_label: str = Field(..., min_length=2, max_length=80)
    issued_at: datetime | None = None
    superseded_at: datetime | None = None
    package_sha256: str | None = Field(default=None, max_length=64)
    package_filename: str | None = Field(default=None, max_length=220)
    package_storage_ready: bool = False
    package_size_bytes: int | None = Field(default=None, ge=0)
    verification_hash: str | None = Field(default=None, max_length=64)
    verification_url: str | None = Field(default=None, max_length=400)
    approval_snapshot_id: int | None = Field(default=None, ge=1)
    approval_version: int | None = Field(default=None, ge=1)
    signatory_name: str | None = Field(default=None, max_length=160)
    signatory_function: str | None = Field(default=None, max_length=120)
    signatory_registration: str | None = Field(default=None, max_length=80)
    issued_by_name: str | None = Field(default=None, max_length=160)
    primary_pdf_sha256: str | None = Field(default=None, max_length=64)
    primary_pdf_storage_version: str | None = Field(default=None, max_length=32)
    primary_pdf_storage_version_number: int | None = Field(default=None, ge=0)
    current_primary_pdf_sha256: str | None = Field(default=None, max_length=64)
    current_primary_pdf_storage_version: str | None = Field(default=None, max_length=32)
    current_primary_pdf_storage_version_number: int | None = Field(default=None, ge=0)
    primary_pdf_diverged: bool = False
    primary_pdf_comparison_status: str | None = Field(default=None, max_length=32)
    reissue_of_issue_id: int | None = Field(default=None, ge=1)
    reissue_of_issue_number: str | None = Field(default=None, max_length=80)
    reissue_reason_codes: list[str] = Field(default_factory=list)
    reissue_reason_summary: str | None = Field(default=None, max_length=280)
    superseded_by_issue_id: int | None = Field(default=None, ge=1)
    superseded_by_issue_number: str | None = Field(default=None, max_length=80)


class EmissaoOficialPacoteMesa(BaseModel):
    issue_status: str = Field(..., min_length=2, max_length=32)
    issue_status_label: str = Field(..., min_length=2, max_length=120)
    ready_for_issue: bool = False
    requires_human_signature: bool = True
    compatible_signatory_count: int = Field(default=0, ge=0)
    eligible_signatory_count: int = Field(default=0, ge=0)
    blocker_count: int = Field(default=0, ge=0)
    signature_status: str | None = Field(default=None, max_length=32)
    signature_status_label: str | None = Field(default=None, max_length=120)
    verification_url: str | None = Field(default=None, max_length=400)
    pdf_present: bool = False
    public_verification_present: bool = False
    signatories: list[SignatarioGovernadoPacoteMesa] = Field(default_factory=list)
    blockers: list[EmissaoOficialBlockerPacoteMesa] = Field(default_factory=list)
    audit_trail: list[EmissaoOficialTrailEventoPacoteMesa] = Field(default_factory=list)
    already_issued: bool = False
    reissue_recommended: bool = False
    issue_action_label: str | None = Field(default=None, max_length=120)
    issue_action_enabled: bool = False
    current_issue: EmissaoOficialAtualPacoteMesa | None = None


class PacoteMesaLaudo(BaseModel):
    laudo_id: int = Field(..., ge=1)
    codigo_hash: str = Field(..., min_length=6, max_length=32)
    tipo_template: str = Field(..., min_length=1, max_length=80)
    setor_industrial: str = Field(..., min_length=1, max_length=120)
    status_revisao: str = Field(..., min_length=1, max_length=30)
    status_conformidade: str = Field(..., min_length=1, max_length=30)
    case_status: str = Field(default="", max_length=40)
    case_lifecycle_status: str = Field(default="", max_length=40)
    case_workflow_mode: str = Field(default="", max_length=40)
    active_owner_role: str = Field(default="", max_length=24)
    allowed_next_lifecycle_statuses: list[str] = Field(default_factory=list)
    allowed_surface_actions: list[str] = Field(default_factory=list)
    status_visual_label: str = Field(default="", max_length=120)
    criado_em: datetime
    atualizado_em: datetime | None = None
    tempo_em_campo_minutos: int = Field(default=0, ge=0)
    ultima_interacao_em: datetime | None = None
    inspetor_id: int | None = Field(default=None, ge=1)
    revisor_id: int | None = Field(default=None, ge=1)
    dados_formulario: dict | None = None
    documento_estruturado: DocumentoEstruturadoPacoteMesa | None = None
    revisao_por_bloco: RevisaoPorBlocoPacoteMesa | None = None
    parecer_ia: str | None = None
    resumo_mensagens: ResumoMensagensMesa
    resumo_evidencias: ResumoEvidenciasMesa
    resumo_pendencias: ResumoPendenciasMesa
    catalog_template_scope: dict[str, Any] | None = None
    coverage_map: CoverageMapPacoteMesa | None = None
    historico_inspecao: HistoricoInspecaoPacoteMesa | None = None
    human_override_summary: dict[str, Any] | None = None
    verificacao_publica: VerificacaoPublicaPacoteMesa | None = None
    anexo_pack: AnexoPackPacoteMesa | None = None
    emissao_oficial: EmissaoOficialPacoteMesa | None = None
    historico_refazer_inspetor: list[HistoricoRefazerInspetorItemPacoteMesa] = Field(default_factory=list)
    memoria_operacional_familia: MemoriaOperacionalFamiliaPacoteMesa | None = None
    pendencias_abertas: list[MensagemPacoteMesa] = Field(default_factory=list)
    pendencias_resolvidas_recentes: list[MensagemPacoteMesa] = Field(default_factory=list)
    whispers_recentes: list[MensagemPacoteMesa] = Field(default_factory=list)
    revisoes_recentes: list[RevisaoPacoteMesa] = Field(default_factory=list)
