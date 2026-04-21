from __future__ import annotations

from copy import deepcopy
from typing import Any
import json

from nucleo.template_laudos import normalizar_codigo_template


UNIVERSAL_SECTION_ORDER: tuple[str, ...] = (
    "capa_folha_rosto",
    "controle_documental_sumario",
    "objeto_escopo_base_normativa",
    "metodologia_instrumentos_equipe",
    "identificacao_tecnica_do_objeto",
    "checklist_tecnico",
    "evidencias_registros_fotograficos",
    "nao_conformidades_criticidade",
    "conclusao",
    "recomendacoes_plano_acao",
    "assinaturas_responsabilidade_tecnica",
    "anexos",
)

UNIVERSAL_BLOCKING_RULES: tuple[str, ...] = (
    "campo_critico_ausente",
    "checklist_obrigatorio_incompleto",
    "evidencia_minima_obrigatoria_ausente",
    "conflito_grave_entre_evidencia_e_conclusao",
    "familia_indefinida",
    "pendencia_critica_em_aberto",
)

TENANT_BRAND_FIELDS: tuple[dict[str, str], ...] = (
    {"key": "display_name", "label": "Nome exibido do cliente", "source": "empresa.nome_fantasia | override"},
    {"key": "legal_name", "label": "Razao social do cliente", "source": "override | empresa.nome_fantasia"},
    {"key": "cnpj", "label": "CNPJ do cliente", "source": "empresa.cnpj | override"},
    {"key": "location_label", "label": "Cidade/estado ou unidade principal", "source": "empresa.cidade_estado | override"},
    {"key": "contact_name", "label": "Responsavel de contato", "source": "empresa.nome_responsavel | override"},
    {"key": "confidentiality_notice", "label": "Aviso de confidencialidade", "source": "override"},
    {"key": "signature_status", "label": "Status de assinatura", "source": "runtime"},
    {"key": "logo_asset", "label": "Logo customizado do cliente", "source": "override runtime asset"},
)

MASTER_TEMPLATE_REGISTRY: dict[str, dict[str, Any]] = {
    "inspection_conformity": {
        "id": "inspection_conformity",
        "label": "Laudo de Inspecao de Conformidade",
        "documental_type": "tipo_a",
        "seed_path": "docs/master_templates/inspection_conformity.template_master.json",
        "summary": "Laudo operacional de conformidade com checklist item a item, evidencias, veredito e proxima inspecao.",
        "section_order": [
            "capa_folha_rosto",
            "controle_documental_sumario",
            "objeto_escopo_base_normativa",
            "metodologia_instrumentos_equipe",
            "identificacao_tecnica_do_objeto",
            "checklist_tecnico",
            "evidencias_registros_fotograficos",
            "nao_conformidades_criticidade",
            "conclusao",
            "recomendacoes_plano_acao",
            "assinaturas_responsabilidade_tecnica",
            "anexos",
        ],
        "primary_evidence_mode": "foto_texto_documento",
    },
    "risk_analysis": {
        "id": "risk_analysis",
        "label": "Laudo de Analise ou Apreciacao de Risco",
        "documental_type": "tipo_b",
        "summary": "Documento tecnico com inventario de perigos, analise de risco, medidas existentes e recomendadas.",
        "section_order": [
            "capa_folha_rosto",
            "controle_documental_sumario",
            "objeto_escopo_base_normativa",
            "metodologia_instrumentos_equipe",
            "identificacao_tecnica_do_objeto",
            "inventario_de_perigos",
            "analise_de_risco",
            "medidas_existentes",
            "medidas_recomendadas",
            "conclusao",
            "recomendacoes_plano_acao",
            "assinaturas_responsabilidade_tecnica",
            "anexos",
        ],
        "primary_evidence_mode": "matriz_analitica",
    },
    "integrity_specialized": {
        "id": "integrity_specialized",
        "label": "Laudo de Integridade ou Ensaio Especializado",
        "documental_type": "tipo_c",
        "summary": "Relatorio com dados operacionais, metodo de ensaio, medicoes, anomalias e parecer conclusivo ate a proxima inspeção.",
        "section_order": [
            "capa_folha_rosto",
            "controle_documental_sumario",
            "objeto_escopo_base_normativa",
            "metodologia_instrumentos_equipe",
            "identificacao_tecnica_do_objeto",
            "documentos_obrigatorios",
            "dados_operacionais",
            "medicoes_e_resultados",
            "evidencias_registros_fotograficos",
            "nao_conformidades_criticidade",
            "conclusao",
            "recomendacoes_plano_acao",
            "assinaturas_responsabilidade_tecnica",
            "anexos",
        ],
        "primary_evidence_mode": "medicoes_mais_fotos",
    },
    "controlled_permit": {
        "id": "controlled_permit",
        "label": "Documento Controlado por Permissao",
        "documental_type": "tipo_d",
        "summary": "Documento de entrada controlada com riscos, medidas de controle, isolamentos, validade e encerramento.",
        "section_order": [
            "capa_folha_rosto",
            "controle_documental_sumario",
            "objeto_escopo_base_normativa",
            "metodologia_instrumentos_equipe",
            "identificacao_tecnica_do_objeto",
            "riscos_e_controles",
            "bloqueios_e_isolamentos",
            "medicoes_e_autorizacoes",
            "evidencias_registros_fotograficos",
            "conclusao",
            "encerramento",
            "assinaturas_responsabilidade_tecnica",
            "anexos",
        ],
        "primary_evidence_mode": "medicoes_autorizacoes",
    },
    "technical_dossier": {
        "id": "technical_dossier",
        "label": "Prontuario ou Dossie Tecnico",
        "documental_type": "tipo_e",
        "summary": "Pacote tecnico controlado com indice, documentos-base, projetos, relatorios, certificados e historico de revisoes.",
        "section_order": [
            "capa_folha_rosto",
            "controle_documental_sumario",
            "objeto_escopo_base_normativa",
            "indice_e_documentacao_base",
            "projetos_e_diagramas",
            "procedimentos_e_relatorios",
            "certificados_e_qualificacoes",
            "historico_de_revisoes",
            "conclusao",
            "assinaturas_responsabilidade_tecnica",
            "anexos",
        ],
        "primary_evidence_mode": "pacote_documental",
    },
    "program_plan": {
        "id": "program_plan",
        "label": "Programa, Plano ou Inventario",
        "documental_type": "tipo_f",
        "summary": "Documento de programa/plano com inventario, classificacao do risco, responsaveis, cronograma e revisao.",
        "section_order": [
            "capa_folha_rosto",
            "controle_documental_sumario",
            "objeto_escopo_base_normativa",
            "identificacao_de_unidades",
            "caracterizacao_de_atividades",
            "inventario_e_classificacao",
            "plano_de_acao",
            "responsaveis_e_cronograma",
            "conclusao",
            "assinaturas_responsabilidade_tecnica",
            "anexos",
        ],
        "primary_evidence_mode": "inventario_mais_plano",
    },
}

EXPLICIT_FAMILY_MASTER_TEMPLATE_IDS: dict[str, str] = {
    "nr07_pcmso": "program_plan",
    "nr09_avaliacao_exposicoes_ocupacionais": "risk_analysis",
    "nr10_implantacao_loto": "inspection_conformity",
    "nr10_inspecao_spda": "inspection_conformity",
    "nr10_prontuario_instalacoes_eletricas": "technical_dossier",
    "nr12_apreciacao_risco_maquina": "risk_analysis",
    "nr13_inspecao_caldeira": "integrity_specialized",
    "nr13_inspecao_vaso_pressao": "integrity_specialized",
    "nr13_inspecao_tubulacao": "integrity_specialized",
    "nr15_laudo_insalubridade": "risk_analysis",
    "nr16_laudo_periculosidade": "risk_analysis",
    "nr17_analise_ergonomica_trabalho": "risk_analysis",
    "nr17_checklist_ergonomia": "risk_analysis",
    "nr18_pgr_canteiro_obra": "program_plan",
    "nr20_prontuario_instalacoes_inflamaveis": "technical_dossier",
    "nr31_pgrtr": "program_plan",
    "nr32_plano_risco_biologico": "program_plan",
    "nr33_avaliacao_espaco_confinado": "risk_analysis",
    "nr33_permissao_entrada_trabalho": "controlled_permit",
}


def _dict_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _load_json_from_text(value: Any) -> dict[str, Any] | None:
    text = str(value or "").strip()
    if not text.startswith("{"):
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _branding_overrides(source_payload: dict[str, Any] | None, empresa_entity: Any | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if isinstance(getattr(empresa_entity, "observacoes", None), str):
        observacoes_payload = _load_json_from_text(getattr(empresa_entity, "observacoes", None))
        if isinstance(observacoes_payload, dict):
            nested = observacoes_payload.get("tenant_branding") or observacoes_payload.get("branding")
            if isinstance(nested, dict):
                merged.update(deepcopy(nested))

    if isinstance(source_payload, dict):
        for key in ("tenant_branding", "branding", "brand_pack"):
            payload = source_payload.get(key)
            if isinstance(payload, dict):
                merged.update(deepcopy(payload))
    return merged


def _normalize_logo_asset(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    path = _clean_text(value.get("path"))
    mime_type = _clean_text(value.get("mime_type"))
    if not path or not mime_type:
        return None
    asset_id = _clean_text(value.get("id")) or "tenant_logo"
    filename = _clean_text(value.get("filename")) or "logo_cliente"
    return {
        "id": asset_id,
        "path": path,
        "mime_type": mime_type,
        "filename": filename,
    }


def resolve_master_template_id_for_family(family_key: str | None) -> str:
    normalized = normalizar_codigo_template(str(family_key or "").strip().lower())[:120]
    if not normalized:
        return "inspection_conformity"
    explicit = EXPLICIT_FAMILY_MASTER_TEMPLATE_IDS.get(normalized)
    if explicit:
        return explicit
    if normalized.startswith("end_") or any(
        token in normalized
        for token in ("hidrostatico", "estanqueidade", "ultrassom", "liquido_penetrante", "particula_magnetica", "visual_solda")
    ):
        return "integrity_specialized"
    if any(token in normalized for token in ("permissao_", "pet", "ordem_servico")):
        return "controlled_permit"
    if any(token in normalized for token in ("prontuario", "dossie")):
        return "technical_dossier"
    if any(
        token in normalized
        for token in (
            "programa",
            "plano",
            "pgr",
            "gro",
            "pcmso",
            "gestao_",
            "diagnostico",
            "implantacao",
            "auditoria_",
            "inventario",
            "sinalizacao",
            "condicoes_",
        )
    ):
        return "program_plan"
    if any(
        token in normalized
        for token in (
            "apreciacao_risco",
            "analise_",
            "avaliacao_",
            "laudo_",
            "ergonomia",
            "exposicoes_",
        )
    ):
        return "risk_analysis"
    if any(token in normalized for token in ("caldeira", "vaso_pressao", "tubulacao", "integridade_")):
        return "integrity_specialized"
    return "inspection_conformity"


def build_document_contract_payload(
    *,
    family_key: str,
    family_label: str | None = None,
    template_code: str | None = None,
) -> dict[str, Any]:
    master_template_id = resolve_master_template_id_for_family(family_key)
    base = deepcopy(MASTER_TEMPLATE_REGISTRY[master_template_id])
    normalized_family_key = normalizar_codigo_template(str(family_key or "").strip().lower())[:120]
    base.update(
        {
            "family_key": normalized_family_key,
            "family_label": _clean_text(family_label) or normalized_family_key.replace("_", " "),
            "template_code": _clean_text(template_code) or normalized_family_key,
            "template_model_strategy": "master_template_plus_family_overlay_plus_tenant_branding",
            "universal_section_order": list(UNIVERSAL_SECTION_ORDER),
            "blocking_rules": list(UNIVERSAL_BLOCKING_RULES),
            "tenant_brand_fields": list(TENANT_BRAND_FIELDS),
            "branding_logo_asset_id": "tenant_logo",
        }
    )
    return base


def build_tenant_branding_payload(
    *,
    empresa_entity: Any | None,
    empresa_nome: str | None,
    source_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    overrides = _branding_overrides(source_payload, empresa_entity)
    display_name = (
        _clean_text(overrides.get("display_name"))
        or _clean_text(overrides.get("cliente_nome"))
        or _clean_text(empresa_nome)
        or _clean_text(getattr(empresa_entity, "nome_fantasia", None))
        or "Cliente nao identificado"
    )
    legal_name = (
        _clean_text(overrides.get("legal_name"))
        or _clean_text(overrides.get("razao_social"))
        or display_name
    )
    cnpj = _clean_text(overrides.get("cnpj")) or _clean_text(getattr(empresa_entity, "cnpj", None))
    location_label = (
        _clean_text(overrides.get("location_label"))
        or _clean_text(overrides.get("cidade_estado"))
        or _clean_text(getattr(empresa_entity, "cidade_estado", None))
    )
    contact_name = (
        _clean_text(overrides.get("contact_name"))
        or _clean_text(overrides.get("nome_responsavel"))
        or _clean_text(getattr(empresa_entity, "nome_responsavel", None))
    )
    confidentiality_notice = (
        _clean_text(overrides.get("confidentiality_notice"))
        or "Uso controlado do cliente. Distribuicao condicionada a autorizacao do emitente."
    )
    signature_status = _clean_text(overrides.get("signature_status")) or "Aguardando assinatura ou ciencia formal."
    logo_asset = _normalize_logo_asset(overrides.get("logo_asset"))

    return {
        "display_name": display_name,
        "legal_name": legal_name,
        "cnpj": cnpj,
        "location_label": location_label,
        "contact_name": contact_name,
        "confidentiality_notice": confidentiality_notice,
        "signature_status": signature_status,
        "logo_asset": logo_asset,
        "logo_asset_id": str((logo_asset or {}).get("id") or "tenant_logo"),
    }


def build_document_control_payload(
    *,
    family_key: str,
    family_label: str | None,
    template_code: str,
    version: int,
    laudo: Any,
    source_payload: dict[str, Any] | None,
    issue_date: str | None,
    master_template_id: str,
    master_template_label: str,
) -> dict[str, Any]:
    source = source_payload if isinstance(source_payload, dict) else {}
    existing_control = _dict_payload(source.get("document_control"))
    laudo_id = int(getattr(laudo, "id", 0) or 0) if laudo is not None else 0
    family_norm = normalizar_codigo_template(str(family_key or "").strip().lower())[:120]
    template_norm = normalizar_codigo_template(str(template_code or family_norm).strip().lower())[:120]
    document_code = (
        _clean_text(existing_control.get("document_code"))
        or _clean_text(source.get("codigo_documento"))
        or _clean_text(source.get("document_code"))
        or f"{template_norm.upper()}-{laudo_id or 'DRAFT'}"
    )
    revision = (
        _clean_text(existing_control.get("revision"))
        or _clean_text(source.get("revisao"))
        or f"v{max(1, int(version or 1))}"
    )
    title = _clean_text(existing_control.get("title")) or _clean_text(family_label) or family_norm.replace("_", " ")
    return {
        "document_code": document_code,
        "revision": revision,
        "title": title,
        "family_key": family_norm,
        "template_code": template_norm,
        "issue_date": _clean_text(issue_date),
        "master_template_id": master_template_id,
        "master_template_label": master_template_label,
    }


def build_document_delivery_package_payload(
    *,
    document_contract: dict[str, Any],
    document_control: dict[str, Any],
    render_mode: str,
) -> dict[str, Any]:
    render_mode_text = _clean_text(render_mode) or "client_pdf_filled"
    preview_mode = render_mode_text == "template_preview_blank"
    admin_mode = render_mode_text == "admin_pdf"
    final_delivery_mode = not preview_mode and not admin_mode
    artifacts = (
        ["document_projection", "editor_preview_pdf"]
        if preview_mode
        else ["document_projection", "editor_document", "admin_pdf_preview"]
        if admin_mode
        else [
            "document_projection",
            "editor_document",
            "pdf_final",
            "public_verification",
            "annex_pack",
            "official_issue_audit",
        ]
    )
    return {
        "package_kind": "tariel_pdf_delivery_bundle",
        "delivery_mode": render_mode_text,
        "delivery_path": "document_view_model_to_editor_to_render",
        "artifacts": artifacts,
        "human_validation_required": True,
        "human_signoff_surface": "mesa_or_signatory",
        "ai_trace_visibility": "internal_audit_only",
        "public_payload_mode": "human_validated_pdf" if final_delivery_mode else "preview_only",
        "document_code": _clean_text(document_control.get("document_code")),
        "document_title": _clean_text(document_control.get("title")),
        "master_template_id": _clean_text(document_contract.get("id")),
        "master_template_label": _clean_text(document_contract.get("label")),
    }


def build_runtime_brand_assets(
    *,
    template_assets_json: Any,
    payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    assets = deepcopy(list(template_assets_json or []))
    branding = payload.get("tenant_branding") if isinstance(payload, dict) else None
    logo_asset = _normalize_logo_asset((branding or {}).get("logo_asset"))
    if not logo_asset:
        return assets
    asset_id = str(logo_asset["id"])
    filtered = [item for item in assets if str(item.get("id") or "").strip() != asset_id]
    filtered.append(logo_asset)
    return filtered


__all__ = [
    "MASTER_TEMPLATE_REGISTRY",
    "TENANT_BRAND_FIELDS",
    "UNIVERSAL_BLOCKING_RULES",
    "UNIVERSAL_SECTION_ORDER",
    "build_document_contract_payload",
    "build_document_control_payload",
    "build_document_delivery_package_payload",
    "build_runtime_brand_assets",
    "build_tenant_branding_payload",
    "resolve_master_template_id_for_family",
]
