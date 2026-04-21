"""Projection helpers for premium document composition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable


RENDER_MODE_TEMPLATE_PREVIEW_BLANK = "template_preview_blank"
RENDER_MODE_CLIENT_PDF_FILLED = "client_pdf_filled"
RENDER_MODE_ADMIN_PDF = "admin_pdf"

_VALID_RENDER_MODES = {
    RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
    RENDER_MODE_CLIENT_PDF_FILLED,
    RENDER_MODE_ADMIN_PDF,
}

_VALID_AUDIENCES = {"client", "admin"}

_INTERNAL_PATH_TOKENS_CLIENT = frozenset(
    {
        "family_key",
        "family_lock",
        "scope_mismatch",
        "schema_type",
        "schema_version",
        "template_code",
        "master_template",
        "contract",
        "telemetry",
        "debug",
        "binding",
        "governanca",
        "governance",
        "mesa_review",
    }
)

_KEY_LABELS = {
    "art": "ART",
    "cnpj": "CNPJ",
    "crea": "CREA",
    "ia": "IA",
    "nr": "NR",
    "pdf": "PDF",
    "pie": "PIE",
    "qr": "QR",
    "rti": "RTI",
}

_STATUS_LABELS = {
    "ajuste": "Liberado com ajustes",
    "bloqueio": "Bloqueado",
    "conforme": "Conforme",
    "em_operacao": "Em operacao",
    "fora_de_operacao": "Fora de operacao",
    "liberado": "Liberado",
    "liberado_com_ressalvas": "Liberado com ressalvas",
    "liberado_com_restricoes": "Liberado com restricoes",
    "pendente": "Pendente",
    "reprovado": "Reprovado",
}

_OBJECT_PATHS: tuple[str, ...] = (
    "identificacao.objeto_principal",
    "identificacao.identificacao_do_vaso",
    "identificacao.identificacao_do_equipamento",
    "identificacao.identificacao_da_caldeira",
    "objeto_inspecao.identificacao",
    "objeto_inspecao.identificacao_linha_vida",
    "objeto_inspecao.identificacao_ponto_ancoragem",
    "objeto_inspecao.objeto_principal",
    "informacoes_gerais.objeto_principal",
)

_CODE_PATHS: tuple[str, ...] = (
    "identificacao.codigo_interno",
    "identificacao.tag_patrimonial",
    "identificacao.numero_laudo_inspecao",
    "identificacao.numero_prontuario",
    "identificacao.numero_laudo_fabricante",
)

_LOCATION_PATHS: tuple[str, ...] = (
    "identificacao.localizacao",
    "objeto_inspecao.localizacao",
    "informacoes_gerais.local_inspecao",
    "informacoes_gerais.local",
    "case_context.unidade_nome",
)

_REFERENCE_PATHS: tuple[str, ...] = (
    "identificacao.referencia_principal.referencias_texto",
    "objeto_inspecao.referencia_principal.referencias_texto",
    "informacoes_gerais.referencia_principal.referencias_texto",
)

_METHOD_PATHS: tuple[str, ...] = (
    "execucao_servico.metodo_aplicado",
    "execucao_servico.metodologia",
    "escopo_servico.metodo_aplicado",
)

_CONDITION_PATHS: tuple[str, ...] = (
    "execucao_servico.condicoes_observadas",
    "informacoes_gerais.condicoes_gerais",
    "caracterizacao_do_equipamento.condicao_geral",
)

_PARAMETER_PATHS: tuple[str, ...] = (
    "execucao_servico.parametros_relevantes",
    "execucao_servico.instrumentos_utilizados",
    "execucao_servico.equipe_envolvida",
)

_FINDING_PATHS: tuple[str, ...] = (
    "nao_conformidades.descricao",
    "nao_conformidades_ou_lacunas.descricao",
)

_RECOMMENDATION_PATHS: tuple[str, ...] = (
    "recomendacoes.texto",
    "conclusao.proxima_acao",
)

_GENERIC_CHECKLIST_LIBRARY: tuple[tuple[tuple[str, ...], list[str]], ...] = (
    (("nr10",), ["Painel ou quadro principal", "Protecoes eletricas", "Aterramento", "Identificacao dos circuitos"]),
    (("nr12",), ["Protecoes fixas", "Comandos e intertravamentos", "Parada de emergencia", "Sinalizacao da maquina"]),
    (("nr13",), ["Estrutura principal", "Dispositivos de seguranca", "Instrumentacao e leitura", "Documentacao do ativo"]),
    (("nr35",), ["Fixacoes e suportes", "Elementos estruturais", "Dispositivos e conexoes", "Identificacao e rastreabilidade"]),
    (("nr33",), ["Isolamentos e bloqueios", "Medicoes e autorizacoes", "Sinalizacao do acesso", "Controle operacional"]),
    (("nr18", "nr22"), ["Estrutura principal", "Circulacao e isolamento", "Sinalizacao local", "Maquinas e equipamentos"]),
)


def _dict_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass(slots=True)
class FieldSpec:
    label: str
    paths: tuple[str, ...]
    semantics: str = "instance_fill"
    fallback: str | None = None
    multiline: bool = False
    include_when_blank: bool = True


def _normalize_render_mode(value: Any) -> str:
    render_mode = str(value or "").strip().lower()
    if render_mode in _VALID_RENDER_MODES:
        return render_mode
    return RENDER_MODE_CLIENT_PDF_FILLED


def _normalize_audience(value: Any) -> str:
    audience = str(value or "").strip().lower()
    if audience in _VALID_AUDIENCES:
        return audience
    return "client"


def _pick_first_text(*values: Any) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _value_by_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in str(path or "").split("."):
        key = segment.strip()
        if not key:
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set)):
        return not any(not _is_blank(item) for item in value)
    if isinstance(value, dict):
        return not any(not _is_blank(item) for item in value.values())
    return False


def _format_date(value: str) -> str:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return text


def _format_scalar(value: Any) -> str | None:
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        return "Sim" if value else "Nao"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = [_format_scalar(item) for item in value]
        clean_parts = [part for part in parts if part]
        return "; ".join(clean_parts) or None
    if isinstance(value, dict):
        return _collapse_leaf_dict(value)
    text = str(value).strip()
    if not text:
        return None
    normalized = text.lower()
    if normalized in _STATUS_LABELS:
        return _STATUS_LABELS[normalized]
    if len(text) >= 10 and text[:4].isdigit() and text[4] == "-":
        return _format_date(text)
    return text


def _humanize_key(value: str) -> str:
    parts = [part for part in str(value or "").replace("/", " ").split("_") if part]
    if not parts:
        return ""
    tokens: list[str] = []
    for part in parts:
        lowered = part.lower()
        if lowered in _KEY_LABELS:
            tokens.append(_KEY_LABELS[lowered])
            continue
        if lowered.isdigit():
            tokens.append(lowered)
            continue
        tokens.append(lowered.capitalize())
    return " ".join(tokens)


def _join_unique(values: list[str]) -> str | None:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        clean = str(value or "").strip()
        if not clean:
            continue
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(clean)
    return "; ".join(ordered) or None


def _is_internal_path(path: str, *, audience: str) -> bool:
    if audience != "client":
        return False
    lowered = str(path or "").strip().lower()
    return any(token in lowered for token in _INTERNAL_PATH_TOKENS_CLIENT)


def _collapse_leaf_dict(value: dict[str, Any]) -> str | None:
    parts: list[str] = []
    for key in (
        "descricao",
        "texto",
        "conclusao_tecnica",
        "justificativa",
        "referencias_texto",
        "observacao",
        "valor",
        "condicao",
        "status",
        "ha_nao_conformidades_texto",
        "ha_pontos_de_atencao_texto",
    ):
        formatted = _format_scalar(value.get(key))
        if formatted:
            parts.append(formatted)
    if "disponivel" in value and value.get("disponivel") is not None:
        available = _format_scalar(value.get("disponivel"))
        if available:
            parts.append(f"Disponibilidade: {available}")
    return _join_unique(parts)


def _flatten_section_rows(
    value: Any,
    *,
    audience: str,
    prefix: str = "",
) -> list[dict[str, str]]:
    if _is_blank(value):
        return []
    if isinstance(value, dict):
        collapsed = _collapse_leaf_dict(value)
        if collapsed and prefix:
            return [{"label": prefix, "value": collapsed}]
        rows: list[dict[str, str]] = []
        for key, child in value.items():
            child_label = _humanize_key(str(key or ""))
            if not child_label:
                continue
            label = f"{prefix} / {child_label}" if prefix else child_label
            if _is_internal_path(label, audience=audience):
                continue
            rows.extend(
                _flatten_section_rows(
                    child,
                    audience=audience,
                    prefix=label,
                )
            )
        return rows
    formatted = _format_scalar(value)
    if not formatted or not prefix:
        return []
    return [{"label": prefix, "value": formatted}]


def _dedupe_rows(rows: list[dict[str, str]], *, max_rows: int | None = None) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        label = str(row.get("label") or "").strip()
        value = str(row.get("value") or "").strip()
        if not label:
            continue
        key = (label.casefold(), value.casefold())
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"label": label, "value": value})
        if max_rows is not None and len(deduped) >= max_rows:
            break
    return deduped


def _extract_context(
    payload: dict[str, Any],
    *,
    audience: str,
    render_mode: str,
) -> dict[str, Any]:
    projection = _dict_payload(payload.get("document_projection"))
    document_control = _dict_payload(payload.get("document_control"))
    document_contract = _dict_payload(payload.get("document_contract"))
    required_slots_payload = projection.get("required_slots")
    required_slots: list[Any] = (
        list(required_slots_payload) if isinstance(required_slots_payload, list) else []
    )
    optional_slots_payload = projection.get("optional_slots")
    optional_slots: list[Any] = (
        list(optional_slots_payload) if isinstance(optional_slots_payload, list) else []
    )
    signature_roles_payload = projection.get("signature_roles")
    signature_roles: list[Any] = (
        list(signature_roles_payload) if isinstance(signature_roles_payload, list) else []
    )
    family_key = str(payload.get("family_key") or document_control.get("family_key") or "").strip()
    family_label = _pick_first_text(
        projection.get("family_label"),
        document_control.get("title"),
        payload.get("family_label"),
        family_key,
    ) or "Laudo Tecnico Tariel"
    return {
        "payload": payload,
        "audience": audience,
        "render_mode": render_mode,
        "projection": projection,
        "document_control": document_control,
        "document_contract": document_contract,
        "family_key": family_key,
        "family_label": family_label,
        "family_description": _pick_first_text(
            projection.get("family_description"),
            document_contract.get("summary"),
        )
        or "",
        "master_template_id": str(
            projection.get("master_template_id")
            or document_contract.get("id")
            or "inspection_conformity"
        ).strip()
        or "inspection_conformity",
        "macro_category": _pick_first_text(
            projection.get("macro_category"),
            _humanize_key(str(family_key).split("_", 1)[0]).replace(" ", ""),
        )
        or "",
        "required_slots": list(required_slots),
        "optional_slots": list(optional_slots),
        "signature_roles": list(signature_roles),
        "blank_row_targets": _dict_payload(projection.get("blank_row_targets")),
        "section_intros": _dict_payload(projection.get("section_intros")),
    }


def _blank_row_target(ctx: dict[str, Any], key: str, default: int) -> int:
    blank_row_targets = _dict_payload(ctx.get("blank_row_targets"))
    raw_value = blank_row_targets.get(key)
    if raw_value is None:
        return max(1, default)
    try:
        normalized = int(raw_value)
    except (TypeError, ValueError):
        normalized = default
    return max(1, normalized)


def _section_intro(ctx: dict[str, Any], section_id: str, default: str) -> str:
    section_intros = _dict_payload(ctx.get("section_intros"))
    override = str(section_intros.get(section_id) or "").strip()
    return override or default


def _value_for_spec(ctx: dict[str, Any], spec: FieldSpec) -> str | None:
    if spec.semantics == "internal_only" and ctx["audience"] != "admin":
        return None
    if (
        ctx["render_mode"] == RENDER_MODE_TEMPLATE_PREVIEW_BLANK
        and spec.semantics in {"instance_fill", "computed_on_emit"}
    ):
        return None
    for path in spec.paths:
        formatted = _format_scalar(_value_by_path(ctx["payload"], path))
        if formatted:
            return formatted
    return spec.fallback


def _row_from_spec(ctx: dict[str, Any], spec: FieldSpec) -> dict[str, Any] | None:
    value = _value_for_spec(ctx, spec)
    if value is None and not spec.include_when_blank and ctx["render_mode"] != RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        return None
    return {
        "label": spec.label,
        "value": value or "",
        "blank": not bool(value),
        "semantics": spec.semantics,
        "multiline": bool(spec.multiline),
    }


def _rows_from_specs(ctx: dict[str, Any], specs: list[FieldSpec]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in specs:
        row = _row_from_spec(ctx, spec)
        if row is None:
            continue
        rows.append(row)
    return rows


def _append_dynamic_rows(
    rows: list[dict[str, Any]],
    *,
    value: Any,
    audience: str,
    max_rows: int = 12,
) -> list[dict[str, Any]]:
    if _is_blank(value):
        return rows
    flattened = _flatten_section_rows(value, audience=audience)
    existing = {(str(row.get("label") or "")).casefold() for row in rows}
    for row in _dedupe_rows(flattened, max_rows=max_rows):
        label = str(row.get("label") or "").strip()
        if not label or label.casefold() in existing:
            continue
        rows.append({"label": label, "value": str(row.get("value") or ""), "blank": False, "semantics": "instance_fill"})
        existing.add(label.casefold())
    return rows


def _meta_row_specs(ctx: dict[str, Any]) -> list[FieldSpec]:
    return [
        FieldSpec("Documento", ("document_control.document_code",), semantics="template_static"),
        FieldSpec("Revisao", ("document_control.revision", "tokens.documento_revisao"), semantics="template_static"),
        FieldSpec("Categoria NR", ("document_projection.macro_category",), semantics="template_static"),
        FieldSpec("Classificacao", ("document_contract.label",), semantics="template_static"),
        FieldSpec("Cliente", ("tenant_branding.display_name", "case_context.empresa_nome"), semantics="instance_fill"),
        FieldSpec("Unidade", ("case_context.unidade_nome", "tenant_branding.location_label"), semantics="instance_fill"),
        FieldSpec("Data da execucao", ("case_context.data_execucao",), semantics="instance_fill"),
        FieldSpec("Data da emissao", ("case_context.data_emissao", "document_control.issue_date"), semantics="computed_on_emit"),
        FieldSpec("Responsavel tecnico", ("tokens.engenheiro_responsavel", "tenant_branding.contact_name"), semantics="instance_fill"),
    ]


def _identification_specs(ctx: dict[str, Any]) -> list[FieldSpec]:
    master_template_id = ctx["master_template_id"]
    if master_template_id == "controlled_permit":
        return [
            FieldSpec("Atividade autorizada", _OBJECT_PATHS),
            FieldSpec("Codigo interno", _CODE_PATHS),
            FieldSpec("Localizacao", _LOCATION_PATHS),
            FieldSpec("Equipe ou frente", ("informacoes_gerais.equipe", "identificacao.equipe_responsavel")),
            FieldSpec("Vigencia operacional", ("identificacao.vigencia", "case_context.data_execucao")),
        ]
    if master_template_id == "technical_dossier":
        return [
            FieldSpec("Documento principal", _OBJECT_PATHS),
            FieldSpec("Codigo do dossie", _CODE_PATHS),
            FieldSpec("Unidade ou base", _LOCATION_PATHS),
            FieldSpec("Referencia principal", _REFERENCE_PATHS),
            FieldSpec("Responsavel pelo pacote", ("tokens.engenheiro_responsavel", "tenant_branding.contact_name")),
        ]
    if master_template_id == "program_plan":
        return [
            FieldSpec("Programa ou plano", _OBJECT_PATHS),
            FieldSpec("Codigo interno", _CODE_PATHS),
            FieldSpec("Abrangencia", _LOCATION_PATHS),
            FieldSpec("Responsavel principal", ("tokens.engenheiro_responsavel", "tenant_branding.contact_name")),
            FieldSpec("Base normativa", ("document_projection.macro_category",), semantics="template_static"),
        ]
    if master_template_id == "risk_analysis":
        return [
            FieldSpec("Objeto analisado", _OBJECT_PATHS),
            FieldSpec("Codigo interno", _CODE_PATHS),
            FieldSpec("Localizacao", _LOCATION_PATHS),
            FieldSpec("Referencia principal", _REFERENCE_PATHS),
            FieldSpec("Contexto tecnico", ("escopo_servico.resumo_escopo",), multiline=True),
        ]
    return [
        FieldSpec("Objeto principal", _OBJECT_PATHS),
        FieldSpec("Codigo interno", _CODE_PATHS),
        FieldSpec("Localizacao", _LOCATION_PATHS),
        FieldSpec("Referencia principal", _REFERENCE_PATHS),
        FieldSpec("Categoria do ativo", ("escopo_servico.ativo_tipo",), semantics="template_static"),
    ]


def _build_document_control_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    rows = _rows_from_specs(ctx, _meta_row_specs(ctx))
    if not rows:
        return None
    return {
        "id": "controle_documental_sumario",
        "title": "Quadro de Controle do Documento",
        "intro": _section_intro(
            ctx,
            "controle_documental_sumario",
            "Identificacao documental, classificacao da entrega e pontos de rastreabilidade do laudo.",
        ),
        "blocks": [{"type": "kv_grid", "variant": "control", "rows": rows}],
    }


def _build_scope_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    rows = _rows_from_specs(
        ctx,
        [
            FieldSpec("Tipo de entrega", ("escopo_servico.tipo_entrega",), semantics="template_static"),
            FieldSpec("Modo de execucao", ("escopo_servico.modo_execucao",), semantics="template_static"),
            FieldSpec("Categoria principal", ("escopo_servico.ativo_tipo",), semantics="template_static"),
            FieldSpec("Escopo registrado", ("escopo_servico.resumo_escopo",), multiline=True),
        ],
    )
    opening_text = _pick_first_text(
        ctx["projection"].get("opening_statement"),
        ctx["family_description"],
    ) or "Documento tecnico governado para consolidar escopo, evidencias e conclusao da familia."
    narrative_text = (
        opening_text
        if ctx["render_mode"] == RENDER_MODE_TEMPLATE_PREVIEW_BLANK
        else _pick_first_text(
            _format_scalar(ctx["payload"].get("resumo_executivo")),
            _format_scalar(_value_by_path(ctx["payload"], "conclusao.conclusao_tecnica")),
            opening_text,
        )
    )
    return {
        "id": "objeto_escopo_base_normativa",
        "title": "Escopo Tecnico e Premissas",
        "intro": _section_intro(
            ctx,
            "objeto_escopo_base_normativa",
            "Abertura documental da familia e contexto de uso do documento.",
        ),
        "blocks": [
            {"type": "narrative", "variant": "opening", "text": narrative_text, "blank": False},
            {"type": "kv_grid", "variant": "scope", "rows": rows},
        ],
    }


def _build_summary_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    summary_text = _pick_first_text(
        _format_scalar(ctx["payload"].get("resumo_executivo")),
        _format_scalar(_value_by_path(ctx["payload"], "conclusao.conclusao_tecnica")),
        _format_scalar(_value_by_path(ctx["payload"], "conclusao.justificativa")),
        _format_scalar(_value_by_path(ctx["payload"], "document_projection.opening_statement")),
        ctx["family_description"],
    ) or "Documento tecnico estruturado para consolidar a leitura executiva do laudo."
    return {
        "id": "resumo_executivo",
        "title": "Resumo Executivo",
        "intro": _section_intro(
            ctx,
            "resumo_executivo",
            "Sintese de leitura rapida para contextualizar objetivo, situacao e intencao documental do laudo.",
        ),
        "blocks": [{"type": "narrative", "variant": "summary", "text": summary_text, "blank": False}],
    }


def _build_methodology_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    rows = _rows_from_specs(
        ctx,
        [
            FieldSpec("Metodo aplicado", _METHOD_PATHS, multiline=True),
            FieldSpec("Condicoes observadas", _CONDITION_PATHS, multiline=True),
            FieldSpec("Parametros relevantes", _PARAMETER_PATHS, multiline=True),
            FieldSpec("Evidencia de execucao", ("execucao_servico.evidencia_execucao.referencias_texto",), multiline=True),
        ],
    )
    rows = _append_dynamic_rows(
        rows,
        value=_value_by_path(ctx["payload"], "execucao_servico"),
        audience=ctx["audience"],
        max_rows=8,
    )
    if not rows and ctx["render_mode"] != RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        return None
    return {
        "id": "metodologia_instrumentos_equipe",
        "title": "Metodologia, Instrumentos e Equipe",
        "intro": _section_intro(
            ctx,
            "metodologia_instrumentos_equipe",
            "Como a evidencia foi produzida e quais parametros sustentam a leitura tecnica.",
        ),
        "blocks": [{"type": "kv_grid", "variant": "methodology", "rows": rows}],
    }


def _build_identification_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    rows = _rows_from_specs(ctx, _identification_specs(ctx))
    for path in ("identificacao", "objeto_inspecao", "informacoes_gerais"):
        rows = _append_dynamic_rows(
            rows,
            value=_value_by_path(ctx["payload"], path),
            audience=ctx["audience"],
            max_rows=12,
        )
    if not rows and ctx["render_mode"] != RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        return None
    return {
        "id": "identificacao_tecnica_do_objeto",
        "title": "Identificacao Tecnica do Objeto",
        "intro": _section_intro(
            ctx,
            "identificacao_tecnica_do_objeto",
            "Quadro tecnico do item, frente, unidade ou documento principal analisado.",
        ),
        "blocks": [{"type": "kv_grid", "variant": "identification", "rows": rows}],
    }


def _generic_checklist_items(ctx: dict[str, Any]) -> list[str]:
    family_key = str(ctx["family_key"] or "").lower()
    for prefixes, items in _GENERIC_CHECKLIST_LIBRARY:
        if any(prefix in family_key for prefix in prefixes):
            return items
    return ["Estrutura principal", "Fixacoes e suportes", "Dispositivos e protecoes", "Identificacao e rastreabilidade"]


def _build_checklist_rows(ctx: dict[str, Any]) -> list[list[dict[str, Any]]]:
    source = (
        _value_by_path(ctx["payload"], "checklist_componentes")
        or _value_by_path(ctx["payload"], "componentes_inspecionados")
        or _value_by_path(ctx["payload"], "dispositivos_e_acessorios")
        or _value_by_path(ctx["payload"], "dispositivos_e_controles")
    )
    rows: list[list[dict[str, Any]]] = []
    if isinstance(source, dict) and source and ctx["render_mode"] != RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        for key, item in list(source.items())[:8]:
            value = item if isinstance(item, dict) else {"descricao": item}
            rows.append(
                [
                    {"text": _humanize_key(str(key or "")) or "Item tecnico", "blank": False},
                    {
                        "text": _pick_first_text(
                            _format_scalar(value.get("condicao")),
                            _format_scalar(value.get("status")),
                        )
                        or "",
                        "blank": _is_blank(value.get("condicao")) and _is_blank(value.get("status")),
                    },
                    {
                        "text": _pick_first_text(
                            _format_scalar(value.get("observacao")),
                            _format_scalar(value.get("descricao")),
                        )
                        or "",
                        "blank": _is_blank(value.get("observacao")) and _is_blank(value.get("descricao")),
                    },
                ]
            )
    if rows:
        return rows
    for item in _generic_checklist_items(ctx)[: _blank_row_target(ctx, "checklist", 4)]:
        rows.append([{"text": item, "blank": False}, {"text": "", "blank": True}, {"text": "", "blank": True}])
    return rows


def _build_checklist_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    if ctx["master_template_id"] not in {"inspection_conformity", "integrity_specialized"}:
        return None
    return {
        "id": "checklist_tecnico",
        "title": "Checklist Tecnico",
        "intro": _section_intro(
            ctx,
            "checklist_tecnico",
            "Leitura dirigida dos componentes, protecoes, dispositivos ou itens de verificacao mais sensiveis da familia.",
        ),
        "blocks": [
            {
                "type": "table",
                "variant": "checklist",
                "headers": ["Item tecnico", "Condicao", "Observacao"],
                "rows": _build_checklist_rows(ctx),
            }
        ],
    }


def _build_evidence_rows(ctx: dict[str, Any]) -> list[list[dict[str, Any]]]:
    rows: list[list[dict[str, Any]]] = []
    slots = list(ctx["required_slots"]) + list(ctx["optional_slots"])
    for slot in slots:
        binding_path = str(slot.get("binding_path") or "").strip()
        binding_value = _value_by_path(ctx["payload"], binding_path) if binding_path else None
        reference_text = _format_scalar(binding_value)
        if isinstance(binding_value, dict):
            reference_text = _pick_first_text(
                _format_scalar(binding_value.get("referencias_texto")),
                _format_scalar(binding_value.get("descricao")),
                _format_scalar(binding_value.get("observacao")),
            )
        if ctx["render_mode"] == RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
            reference_text = None
        rows.append(
            [
                {"text": str(slot.get("label") or "Evidencia"), "blank": False},
                {"text": "Obrigatorio" if bool(slot.get("required")) else "Complementar", "blank": False},
                {"text": str(slot.get("purpose") or "").strip(), "blank": False},
                {"text": reference_text or "", "blank": not bool(reference_text)},
            ]
        )
    if not rows:
        evidencias = _value_by_path(ctx["payload"], "evidencias_e_anexos")
        if isinstance(evidencias, dict):
            for key, value in list(evidencias.items())[:6]:
                reference_text = _format_scalar(value)
                if isinstance(value, dict):
                    reference_text = _pick_first_text(
                        _format_scalar(value.get("referencias_texto")),
                        _format_scalar(value.get("descricao")),
                        _format_scalar(value.get("observacao")),
                    )
                if ctx["render_mode"] == RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
                    reference_text = None
                rows.append(
                    [
                        {"text": _humanize_key(str(key or "")) or "Evidencia", "blank": False},
                        {"text": "Elemento documental", "blank": False},
                        {"text": "Suportar a conclusao tecnica e a rastreabilidade do caso.", "blank": False},
                        {"text": reference_text or "", "blank": not bool(reference_text)},
                    ]
                )
    registros = _value_by_path(ctx["payload"], "registros_fotograficos")
    if isinstance(registros, list) and registros and ctx["render_mode"] != RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        for item in registros[:4]:
            if not isinstance(item, dict):
                continue
            rows.append(
                [
                    {"text": _pick_first_text(item.get("titulo"), "Registro fotografico") or "Registro fotografico", "blank": False},
                    {"text": "Foto", "blank": False},
                    {"text": _pick_first_text(item.get("legenda")) or "", "blank": _is_blank(item.get("legenda"))},
                    {"text": _pick_first_text(item.get("referencia_anexo")) or "", "blank": _is_blank(item.get("referencia_anexo"))},
                ]
            )
    return rows[:10]


def _build_evidence_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    rows = _build_evidence_rows(ctx)
    if not rows and ctx["render_mode"] != RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        return None
    return {
        "id": "evidencias_registros_fotograficos",
        "title": "Matriz de Evidencias e Registros",
        "intro": _section_intro(
            ctx,
            "evidencias_registros_fotograficos",
            "Relacao entre slots documentais, finalidade tecnica e evidencia vinculada ao laudo.",
        ),
        "blocks": [
            {
                "type": "table",
                "variant": "evidence",
                "headers": ["Elemento", "Natureza", "Finalidade tecnica", "Referencia"],
                "rows": rows,
            }
        ],
    }


def _build_findings_rows(ctx: dict[str, Any]) -> list[list[dict[str, Any]]]:
    rows: list[list[dict[str, Any]]] = []
    finding_text = _pick_first_text(
        *[_format_scalar(_value_by_path(ctx["payload"], path)) for path in _FINDING_PATHS]
    )
    recommendation_text = _pick_first_text(
        *[_format_scalar(_value_by_path(ctx["payload"], path)) for path in _RECOMMENDATION_PATHS]
    )
    status_text = _pick_first_text(
        _format_scalar(_value_by_path(ctx["payload"], "conclusao.status")),
        _format_scalar(_value_by_path(ctx["payload"], "nao_conformidades.status")),
        _format_scalar(_value_by_path(ctx["payload"], "nao_conformidades_ou_lacunas.status")),
    )
    if ctx["render_mode"] != RENDER_MODE_TEMPLATE_PREVIEW_BLANK and (finding_text or recommendation_text or status_text):
        rows.append(
            [
                {"text": "Achado principal", "blank": False},
                {"text": status_text or "", "blank": not bool(status_text)},
                {"text": finding_text or "", "blank": not bool(finding_text)},
                {"text": recommendation_text or "", "blank": not bool(recommendation_text)},
            ]
        )
    if not rows:
        for index in range(1, _blank_row_target(ctx, "findings", 3) + 1):
            rows.append(
                [
                    {"text": f"Achado {index}", "blank": False},
                    {"text": "", "blank": True},
                    {"text": "", "blank": True},
                    {"text": "", "blank": True},
                ]
            )
    return rows


def _build_findings_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    return {
        "id": "nao_conformidades_criticidade",
        "title": "Achados Tecnicos e Providencias",
        "intro": _section_intro(
            ctx,
            "nao_conformidades_criticidade",
            "Nao conformidades, pontos de atencao, restricoes ou lacunas que exigem leitura objetiva no documento.",
        ),
        "blocks": [
            {
                "type": "table",
                "variant": "findings",
                "headers": ["Item", "Status", "Descricao tecnica", "Acao ou encaminhamento"],
                "rows": _build_findings_rows(ctx),
            }
        ],
    }


def _build_measurement_rows(ctx: dict[str, Any]) -> list[list[dict[str, Any]]]:
    source = _value_by_path(ctx["payload"], "medicoes_e_resultados")
    rows: list[list[dict[str, Any]]] = []
    if isinstance(source, list) and source and ctx["render_mode"] != RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        for item in source[:6]:
            if not isinstance(item, dict):
                continue
            rows.append(
                [
                    {
                        "text": _pick_first_text(item.get("ponto"), item.get("descricao")) or "",
                        "blank": _is_blank(item.get("ponto")) and _is_blank(item.get("descricao")),
                    },
                    {"text": _pick_first_text(item.get("parametro")) or "", "blank": _is_blank(item.get("parametro"))},
                    {
                        "text": _pick_first_text(item.get("valor"), item.get("resultado")) or "",
                        "blank": _is_blank(item.get("valor")) and _is_blank(item.get("resultado")),
                    },
                    {"text": _pick_first_text(item.get("criterio")) or "", "blank": _is_blank(item.get("criterio"))},
                ]
            )
    if rows:
        return rows
    for _ in range(_blank_row_target(ctx, "measurement", 3)):
        rows.append(
            [
                {"text": "", "blank": True},
                {"text": "", "blank": True},
                {"text": "", "blank": True},
                {"text": "", "blank": True},
            ]
        )
    return rows


def _build_measurement_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    if ctx["master_template_id"] != "integrity_specialized":
        return None
    return {
        "id": "medicoes_e_resultados",
        "title": "Medicoes e Resultados",
        "intro": _section_intro(
            ctx,
            "medicoes_e_resultados",
            "Tabela de pontos de leitura, resultados, criterios e comparativos relevantes para a familia.",
        ),
        "blocks": [
            {
                "type": "table",
                "variant": "measurement",
                "headers": ["Ponto", "Parametro", "Resultado", "Criterio"],
                "rows": _build_measurement_rows(ctx),
            }
        ],
    }


def _build_risk_rows(ctx: dict[str, Any]) -> list[list[dict[str, Any]]]:
    source = _value_by_path(ctx["payload"], "analise_de_risco")
    rows: list[list[dict[str, Any]]] = []
    if isinstance(source, list) and source and ctx["render_mode"] != RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        for item in source[:6]:
            if not isinstance(item, dict):
                continue
            rows.append(
                [
                    {
                        "text": _pick_first_text(item.get("perigo"), item.get("evento")) or "",
                        "blank": _is_blank(item.get("perigo")) and _is_blank(item.get("evento")),
                    },
                    {"text": _pick_first_text(item.get("cenario")) or "", "blank": _is_blank(item.get("cenario"))},
                    {"text": _pick_first_text(item.get("severidade")) or "", "blank": _is_blank(item.get("severidade"))},
                    {"text": _pick_first_text(item.get("probabilidade")) or "", "blank": _is_blank(item.get("probabilidade"))},
                    {
                        "text": _pick_first_text(item.get("controle"), item.get("medida_existente")) or "",
                        "blank": _is_blank(item.get("controle")) and _is_blank(item.get("medida_existente")),
                    },
                    {"text": _pick_first_text(item.get("acao_recomendada")) or "", "blank": _is_blank(item.get("acao_recomendada"))},
                ]
            )
    if rows:
        return rows
    for _ in range(_blank_row_target(ctx, "risk", 3)):
        rows.append(
            [
                {"text": "", "blank": True},
                {"text": "", "blank": True},
                {"text": "", "blank": True},
                {"text": "", "blank": True},
                {"text": "", "blank": True},
                {"text": "", "blank": True},
            ]
        )
    return rows


def _build_risk_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    if ctx["master_template_id"] != "risk_analysis":
        return None
    return {
        "id": "analise_de_risco",
        "title": "Matriz de Risco",
        "intro": _section_intro(
            ctx,
            "analise_de_risco",
            "Leitura analitica de perigos, cenario, intensidade, controles existentes e encaminhamentos recomendados.",
        ),
        "blocks": [
            {
                "type": "table",
                "variant": "risk",
                "headers": ["Perigo", "Cenario", "Severidade", "Probabilidade", "Controle existente", "Acao recomendada"],
                "rows": _build_risk_rows(ctx),
            }
        ],
    }


def _build_document_index_rows(ctx: dict[str, Any]) -> list[list[dict[str, Any]]]:
    rows: list[list[dict[str, Any]]] = []
    documents_value = _value_by_path(ctx["payload"], "documentacao_e_registros")
    if isinstance(documents_value, dict) and documents_value and ctx["render_mode"] != RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        for label, value in list(documents_value.items())[:8]:
            rows.append(
                [
                    {"text": _humanize_key(str(label or "")), "blank": False},
                    {
                        "text": _pick_first_text(
                            _format_scalar(value.get("referencias_texto") if isinstance(value, dict) else None),
                            _format_scalar(value.get("descricao") if isinstance(value, dict) else None),
                            _format_scalar(value),
                        )
                        or "",
                        "blank": _is_blank(value),
                    },
                    {"text": "", "blank": True},
                    {"text": "Disponivel" if not _is_blank(value) else "", "blank": _is_blank(value)},
                ]
            )
    if rows:
        return rows
    for item in ("Documento-base principal", "Projeto ou diagrama", "Certificado ou comprovacao", "Relatorio ou memoria descritiva"):
        rows.append([{"text": item, "blank": False}, {"text": "", "blank": True}, {"text": "", "blank": True}, {"text": "", "blank": True}])
    return rows


def _build_document_index_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    if ctx["master_template_id"] != "technical_dossier":
        return None
    return {
        "id": "indice_e_documentacao_base",
        "title": "Indice e Documentacao Base",
        "intro": _section_intro(
            ctx,
            "indice_e_documentacao_base",
            "Organizacao do pacote documental, referencias-base, revisoes e disponibilidade de cada item essencial.",
        ),
        "blocks": [
            {
                "type": "table",
                "variant": "document-index",
                "headers": ["Documento", "Referencia", "Revisao", "Situacao"],
                "rows": _build_document_index_rows(ctx),
            }
        ],
    }


def _build_program_inventory_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    if ctx["master_template_id"] != "program_plan":
        return None
    rows: list[list[dict[str, Any]]] = []
    source = _value_by_path(ctx["payload"], "inventario_e_classificacao")
    if isinstance(source, list) and source and ctx["render_mode"] != RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        for item in source[:6]:
            if not isinstance(item, dict):
                continue
            rows.append(
                [
                    {
                        "text": _pick_first_text(item.get("unidade"), item.get("setor")) or "",
                        "blank": _is_blank(item.get("unidade")) and _is_blank(item.get("setor")),
                    },
                    {
                        "text": _pick_first_text(item.get("atividade"), item.get("processo")) or "",
                        "blank": _is_blank(item.get("atividade")) and _is_blank(item.get("processo")),
                    },
                    {
                        "text": _pick_first_text(item.get("classificacao"), item.get("risco")) or "",
                        "blank": _is_blank(item.get("classificacao")) and _is_blank(item.get("risco")),
                    },
                    {"text": _pick_first_text(item.get("responsavel")) or "", "blank": _is_blank(item.get("responsavel"))},
                    {"text": _pick_first_text(item.get("prazo")) or "", "blank": _is_blank(item.get("prazo"))},
                ]
            )
    if not rows:
        for _ in range(_blank_row_target(ctx, "program_inventory", 3)):
            rows.append(
                [
                    {"text": "", "blank": True},
                    {"text": "", "blank": True},
                    {"text": "", "blank": True},
                    {"text": "", "blank": True},
                    {"text": "", "blank": True},
                ]
            )
    return {
        "id": "inventario_e_classificacao",
        "title": "Inventario, Classificacao e Plano de Acao",
        "intro": _section_intro(
            ctx,
            "inventario_e_classificacao",
            "Visao consolidada de unidades, atividades, classificacoes e responsaveis previstos no programa ou plano.",
        ),
        "blocks": [
            {
                "type": "table",
                "variant": "program-inventory",
                "headers": ["Unidade", "Atividade", "Classificacao", "Responsavel", "Prazo"],
                "rows": rows,
            }
        ],
    }


def _build_conclusion_rows(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    return _rows_from_specs(
        ctx,
        [
            FieldSpec("Status tecnico", ("conclusao.status",), semantics="computed_on_emit"),
            FieldSpec("Conclusao tecnica", ("conclusao.conclusao_tecnica",), semantics="computed_on_emit", multiline=True),
            FieldSpec("Justificativa", ("conclusao.justificativa",), semantics="computed_on_emit", multiline=True),
            FieldSpec("Proxima acao", ("conclusao.proxima_acao", "recomendacoes.texto"), semantics="computed_on_emit", multiline=True),
        ],
    )


def _build_conclusion_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    rows = _build_conclusion_rows(ctx)
    return {
        "id": "conclusao",
        "title": "Conclusao Tecnica",
        "intro": _section_intro(
            ctx,
            "conclusao",
            "Fechamento tecnico do documento, com status, consolidacao textual e encaminhamento objetivo.",
        ),
        "blocks": [{"type": "conclusion_panel", "rows": rows}],
    }


def _build_signature_items(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    blueprint_roles = []
    for item in list(ctx.get("signature_roles") or []):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or item.get("label") or "").strip()
        if not role:
            continue
        blueprint_roles.append(
            {
                "role": role,
                "name": _pick_first_text(
                    *[
                        _format_scalar(_value_by_path(ctx["payload"], str(path or "").strip()))
                        for path in list(item.get("name_paths") or [])
                        if str(path or "").strip()
                    ]
                ),
                "detail": _pick_first_text(
                    *[
                        _format_scalar(_value_by_path(ctx["payload"], str(path or "").strip()))
                        for path in list(item.get("detail_paths") or [])
                        if str(path or "").strip()
                    ]
                ),
                "date": _pick_first_text(
                    *[
                        _format_scalar(_value_by_path(ctx["payload"], str(path or "").strip()))
                        for path in list(item.get("date_paths") or [])
                        if str(path or "").strip()
                    ]
                ),
            }
        )
    rows = blueprint_roles or [
        {
            "role": "Responsavel tecnico",
            "name": _value_for_spec(ctx, FieldSpec("", ("tokens.engenheiro_responsavel", "tenant_branding.contact_name"))),
            "detail": _pick_first_text(
                _format_scalar(_value_by_path(ctx["payload"], "tokens.crea_art")),
                _format_scalar(_value_by_path(ctx["payload"], "identificacao.art_numero")),
            ),
            "date": _pick_first_text(
                _format_scalar(_value_by_path(ctx["payload"], "case_context.data_emissao")),
                _format_scalar(_value_by_path(ctx["payload"], "document_control.issue_date")),
            ),
        },
        {
            "role": "Representante do cliente",
            "name": _value_for_spec(ctx, FieldSpec("", ("tenant_branding.display_name", "tokens.cliente_nome"))),
            "detail": _pick_first_text(
                _format_scalar(_value_by_path(ctx["payload"], "tenant_branding.cnpj")),
                _format_scalar(_value_by_path(ctx["payload"], "tenant_branding.legal_name")),
            ),
            "date": _pick_first_text(_format_scalar(_value_by_path(ctx["payload"], "case_context.data_emissao"))),
        },
    ]
    items: list[dict[str, Any]] = []
    for row in rows:
        blank = ctx["render_mode"] == RENDER_MODE_TEMPLATE_PREVIEW_BLANK or (
            not str(row.get("name") or "").strip() and not str(row.get("detail") or "").strip()
        )
        items.append(
            {
                "role": row["role"],
                "name": "" if blank else str(row.get("name") or "").strip(),
                "detail": "" if blank else str(row.get("detail") or "").strip(),
                "date": "" if blank else str(row.get("date") or "").strip(),
                "blank": blank,
            }
        )
    return items


def _build_signature_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    return {
        "id": "assinaturas_responsabilidade_tecnica",
        "title": "Assinaturas e Responsabilidade Tecnica",
        "intro": _section_intro(
            ctx,
            "assinaturas_responsabilidade_tecnica",
            "Campos finais para assinatura, responsabilidade e ciencia formal das partes envolvidas.",
        ),
        "blocks": [{"type": "signature_block", "items": _build_signature_items(ctx)}],
    }


def _build_admin_appendix_section(ctx: dict[str, Any]) -> dict[str, Any] | None:
    if ctx["audience"] != "admin":
        return None
    rows = [
        {"label": "Family key", "value": str(ctx["family_key"] or ""), "blank": _is_blank(ctx["family_key"])},
        {
            "label": "Template code",
            "value": _format_scalar(_value_by_path(ctx["payload"], "template_code")) or "",
            "blank": _is_blank(_value_by_path(ctx["payload"], "template_code")),
        },
        {
            "label": "Master template",
            "value": _format_scalar(_value_by_path(ctx["payload"], "document_contract.label")) or "",
            "blank": _is_blank(_value_by_path(ctx["payload"], "document_contract.label")),
        },
        {
            "label": "Mesa",
            "value": _format_scalar(_value_by_path(ctx["payload"], "mesa_review.status")) or "",
            "blank": _is_blank(_value_by_path(ctx["payload"], "mesa_review.status")),
        },
        {
            "label": "Family lock",
            "value": _format_scalar(_value_by_path(ctx["payload"], "mesa_review.family_lock")) or "",
            "blank": _is_blank(_value_by_path(ctx["payload"], "mesa_review.family_lock")),
        },
        {
            "label": "Scope mismatch",
            "value": _format_scalar(_value_by_path(ctx["payload"], "mesa_review.scope_mismatch")) or "",
            "blank": _is_blank(_value_by_path(ctx["payload"], "mesa_review.scope_mismatch")),
        },
    ]
    return {
        "id": "apendice_administrativo",
        "title": "Apendice Administrativo",
        "intro": "Rastreabilidade interna, governanca e observacoes administrativas da emissao.",
        "blocks": [{"type": "kv_grid", "variant": "admin", "rows": rows}],
    }


_SECTION_BUILDERS: dict[str, Callable[[dict[str, Any]], dict[str, Any] | None]] = {
    "controle_documental_sumario": _build_document_control_section,
    "resumo_executivo": _build_summary_section,
    "objeto_escopo_base_normativa": _build_scope_section,
    "metodologia_instrumentos_equipe": _build_methodology_section,
    "identificacao_tecnica_do_objeto": _build_identification_section,
    "checklist_tecnico": _build_checklist_section,
    "evidencias_registros_fotograficos": _build_evidence_section,
    "nao_conformidades_criticidade": _build_findings_section,
    "medicoes_e_resultados": _build_measurement_section,
    "analise_de_risco": _build_risk_section,
    "indice_e_documentacao_base": _build_document_index_section,
    "inventario_e_classificacao": _build_program_inventory_section,
    "conclusao": _build_conclusion_section,
    "assinaturas_responsabilidade_tecnica": _build_signature_section,
}


def _resolve_section_order(ctx: dict[str, Any]) -> list[str]:
    section_order = list(ctx["projection"].get("section_order") or [])
    if not section_order:
        section_order = [
            "controle_documental_sumario",
            "resumo_executivo",
            "objeto_escopo_base_normativa",
            "metodologia_instrumentos_equipe",
            "identificacao_tecnica_do_objeto",
            "checklist_tecnico",
            "evidencias_registros_fotograficos",
            "nao_conformidades_criticidade",
            "conclusao",
            "assinaturas_responsabilidade_tecnica",
        ]
    elif "resumo_executivo" not in section_order:
        insertion_point = 1 if "controle_documental_sumario" in section_order else 0
        section_order.insert(insertion_point, "resumo_executivo")
    return section_order


def _build_sections(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section_id in _resolve_section_order(ctx):
        builder = _SECTION_BUILDERS.get(section_id)
        if builder is None:
            continue
        section = builder(ctx)
        if section is None:
            continue
        sections.append(section)
    admin_appendix = _build_admin_appendix_section(ctx)
    if admin_appendix is not None:
        sections.append(admin_appendix)
    return sections


def build_catalog_document_view_model(
    payload: dict[str, Any] | None,
    *,
    audience: str = "client",
    render_mode: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict) or not payload:
        return {
            "modeled": False,
            "render_mode": RENDER_MODE_CLIENT_PDF_FILLED,
            "audience": _normalize_audience(audience),
            "eyebrow": "Tariel | Documento Tecnico",
            "title": "Laudo Tecnico Tariel",
            "subtitle": "",
            "identity_items": [],
            "opening_text": "Documento tecnico gerado em modo de contingencia.",
            "sections": [],
        }

    render_mode_norm = _normalize_render_mode(render_mode or payload.get("render_mode"))
    audience_norm = _normalize_audience(
        audience if audience in _VALID_AUDIENCES else (payload.get("document_projection", {}) or {}).get("audience")
    )
    ctx = _extract_context(
        payload,
        audience=audience_norm,
        render_mode=render_mode_norm,
    )

    revision = _pick_first_text(
        _format_scalar(_value_by_path(payload, "document_control.revision")),
        _format_scalar(_value_by_path(payload, "tokens.documento_revisao")),
    ) or ""
    document_code = _pick_first_text(
        _format_scalar(_value_by_path(payload, "document_control.document_code")),
        _format_scalar(_value_by_path(payload, "tokens.documento_codigo")),
    ) or ""
    classification = _pick_first_text(
        _format_scalar(_value_by_path(payload, "document_contract.label")),
        _format_scalar(_value_by_path(payload, "document_projection.usage_classification")),
    ) or ""
    preview_seal = str((ctx["projection"] or {}).get("preview_seal") or "").strip()
    if not preview_seal and render_mode_norm == RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        preview_seal = "Template pre-pronto"
    identity_items = [item for item in [document_code, revision, ctx["macro_category"], classification, preview_seal] if item]

    sections = _build_sections(ctx)
    modeled = bool(
        str(payload.get("schema_type") or "").strip().lower() == "laudo_output"
        or sections
    )
    subtitle = _pick_first_text(
        _format_scalar(_value_by_path(payload, "document_contract.label")),
        _format_scalar(_value_by_path(payload, "document_projection.macro_category")),
    ) or "Documento tecnico governado"

    return {
        "modeled": modeled,
        "render_mode": render_mode_norm,
        "audience": audience_norm,
        "eyebrow": "Tariel | Documento Tecnico",
        "title": ctx["family_label"],
        "subtitle": subtitle,
        "identity_items": identity_items,
        "opening_text": _pick_first_text(
            _format_scalar(_value_by_path(payload, "document_projection.opening_statement")),
            ctx["family_description"],
        )
        or "Documento tecnico estruturado para consolidacao de escopo, evidencias e conclusao.",
        "sections": sections,
    }


def _text_node(text: str) -> dict[str, Any]:
    return {"type": "text", "text": str(text or "")}


def _paragraph_node(text: str, *, class_name: str | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "paragraph", "content": [_text_node(text)]}
    if class_name:
        node["attrs"] = {"className": class_name}
    return node


def _heading_node(level: int, text: str, *, class_name: str | None = None) -> dict[str, Any]:
    attrs: dict[str, Any] = {"level": max(1, min(4, int(level or 1)))}
    if class_name:
        attrs["className"] = class_name
    return {
        "type": "heading",
        "attrs": attrs,
        "content": [_text_node(text)],
    }


def _section_node(class_name: str, content: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "section", "attrs": {"className": class_name}, "content": content}


def _panel_node(class_name: str, content: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "panel", "attrs": {"className": class_name}, "content": content}


def _spacer_node(class_name: str = "doc-spacer") -> dict[str, Any]:
    return {"type": "spacer", "attrs": {"className": class_name}}


def _empty_paragraph(class_name: str) -> dict[str, Any]:
    return {"type": "paragraph", "attrs": {"className": class_name}, "content": []}


def _identity_bar_node(items: list[str]) -> dict[str, Any] | None:
    if not items:
        return None
    chips = [_paragraph_node(item, class_name="doc-chip") for item in items]
    return _panel_node("doc-identity-bar", chips)


def _kv_grid_node(rows: list[dict[str, Any]], *, class_name: str) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    for row in rows:
        label_cell = {
            "type": "tableCell",
            "attrs": {"className": "doc-kv-label"},
            "content": [_paragraph_node(str(row.get("label") or ""), class_name="doc-kv-label-copy")],
        }
        value_class = "doc-kv-value"
        value_content: list[dict[str, Any]]
        if bool(row.get("blank")):
            value_class += " doc-kv-value--blank"
            if bool(row.get("multiline")):
                value_content = [_empty_paragraph("doc-blank-multiline-field")]
            else:
                value_content = [_empty_paragraph("doc-blank-field")]
        else:
            value_class += " doc-kv-value--filled"
            copy_class = "doc-kv-value-copy doc-kv-value-copy--multiline" if bool(row.get("multiline")) else "doc-kv-value-copy"
            value_content = [_paragraph_node(str(row.get("value") or ""), class_name=copy_class)]
        content.append(
            {
                "type": "tableRow",
                "content": [
                    label_cell,
                    {"type": "tableCell", "attrs": {"className": value_class}, "content": value_content},
                ],
            }
        )
    return {"type": "table", "attrs": {"className": class_name}, "content": content}


def _table_node(headers: list[str], rows: list[list[dict[str, Any]]], *, class_name: str) -> dict[str, Any]:
    content: list[dict[str, Any]] = [
        {
            "type": "tableRow",
            "content": [
                {
                    "type": "tableHeader",
                    "attrs": {"className": "doc-table-head"},
                    "content": [_paragraph_node(label, class_name="doc-table-head-copy")],
                }
                for label in headers
            ],
        }
    ]
    for row in rows:
        cells: list[dict[str, Any]] = []
        for cell in row:
            cell_text = str(cell.get("text") or "")
            blank = bool(cell.get("blank"))
            cell_class = "doc-table-cell doc-table-cell--blank" if blank else "doc-table-cell"
            if blank:
                cell_content = [_empty_paragraph("doc-blank-field")]
            else:
                cell_content = [_paragraph_node(cell_text, class_name="doc-table-cell-copy")]
            cells.append({"type": "tableCell", "attrs": {"className": cell_class}, "content": cell_content})
        content.append({"type": "tableRow", "content": cells})
    return {"type": "table", "attrs": {"className": class_name}, "content": content}


def _narrative_node(block: dict[str, Any]) -> dict[str, Any]:
    text = str(block.get("text") or "").strip()
    if not text:
        return _panel_node("doc-narrative doc-narrative--blank", [_empty_paragraph("doc-blank-multiline-field")])
    return _panel_node(
        "doc-narrative doc-narrative--filled",
        [_paragraph_node(text, class_name="doc-narrative-copy")],
    )


def _conclusion_panel_node(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_row = next((row for row in rows if str(row.get("label") or "").lower().startswith("status")), None)
    narrative_rows = [row for row in rows if row is not status_row]
    content: list[dict[str, Any]] = []
    if status_row is not None:
        status_text = str(status_row.get("value") or "").strip()
        if status_text:
            content.append(_paragraph_node(status_text, class_name="doc-status-chip"))
        else:
            content.append(_empty_paragraph("doc-status-chip doc-status-chip--blank"))
    for row in narrative_rows:
        title = _paragraph_node(str(row.get("label") or ""), class_name="doc-panel-title")
        if bool(row.get("blank")):
            body = _empty_paragraph("doc-blank-multiline-field")
        else:
            body = _paragraph_node(str(row.get("value") or ""), class_name="doc-panel-copy")
        content.append(_panel_node("doc-conclusion-card", [title, body]))
    return _panel_node("doc-conclusion-panel", content)


def _signature_block_node(items: list[dict[str, Any]]) -> dict[str, Any]:
    cards: list[dict[str, Any]] = []
    for item in items:
        role = _paragraph_node(str(item.get("role") or ""), class_name="doc-sign-role")
        line = _empty_paragraph("doc-sign-line")
        name = (
            _paragraph_node(str(item.get("name") or ""), class_name="doc-sign-name")
            if not bool(item.get("blank"))
            else _empty_paragraph("doc-sign-name doc-sign-name--blank")
        )
        details_text = " | ".join(
            part for part in [str(item.get("detail") or "").strip(), str(item.get("date") or "").strip()] if part
        )
        details = (
            _paragraph_node(details_text, class_name="doc-sign-detail")
            if details_text
            else _empty_paragraph("doc-sign-detail doc-sign-detail--blank")
        )
        cards.append(_panel_node("doc-signature-card", [role, line, name, details]))
    return _panel_node("doc-signature-grid", cards)


def build_universal_document_editor(
    view_model: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(view_model, dict) or not bool(view_model.get("modeled")):
        return None

    cover_content: list[dict[str, Any]] = [
        _paragraph_node(str(view_model.get("eyebrow") or "Tariel | Documento Tecnico"), class_name="doc-kicker"),
        _heading_node(1, str(view_model.get("title") or "Laudo Tecnico Tariel"), class_name="doc-title"),
    ]
    subtitle = str(view_model.get("subtitle") or "").strip()
    if subtitle:
        cover_content.append(_paragraph_node(subtitle, class_name="doc-subtitle"))
    identity_bar = _identity_bar_node(list(view_model.get("identity_items") or []))
    if identity_bar is not None:
        cover_content.append(identity_bar)
    cover_content.append(
        _panel_node(
            "doc-opening-panel",
            [_paragraph_node(str(view_model.get("opening_text") or ""), class_name="doc-opening-copy")],
        )
    )

    content: list[dict[str, Any]] = [_section_node("doc-cover-shell", cover_content)]
    for section in list(view_model.get("sections") or []):
        section_content: list[dict[str, Any]] = [
            _heading_node(2, str(section.get("title") or "Secao Tecnica"), class_name="doc-section-heading")
        ]
        intro = str(section.get("intro") or "").strip()
        if intro:
            section_content.append(_paragraph_node(intro, class_name="doc-section-intro"))
        for block in list(section.get("blocks") or []):
            block_type = str(block.get("type") or "").strip()
            if block_type == "kv_grid":
                section_content.append(
                    _kv_grid_node(
                        list(block.get("rows") or []),
                        class_name=f"doc-kv-grid doc-kv-grid--{str(block.get('variant') or 'default')}",
                    )
                )
            elif block_type == "table":
                section_content.append(
                    _table_node(
                        list(block.get("headers") or []),
                        list(block.get("rows") or []),
                        class_name=f"doc-table doc-table--{str(block.get('variant') or 'default')}",
                    )
                )
            elif block_type == "narrative":
                section_content.append(_narrative_node(block))
            elif block_type == "conclusion_panel":
                section_content.append(_conclusion_panel_node(list(block.get("rows") or [])))
            elif block_type == "signature_block":
                section_content.append(_signature_block_node(list(block.get("items") or [])))
        content.append(_section_node(f"doc-section doc-section--{str(section.get('id') or 'generic')}", section_content))
        content.append(_spacer_node())

    return {"version": 1, "doc": {"type": "doc", "content": content}}


__all__ = [
    "build_catalog_document_view_model",
    "build_universal_document_editor",
]
