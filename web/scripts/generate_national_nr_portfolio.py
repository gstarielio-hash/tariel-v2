# ruff: noqa: E501
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILY_SCHEMAS_DIR = REPO_ROOT / "docs" / "family_schemas"
REGISTRY_PATH = REPO_ROOT / "docs" / "nr_programming_registry.json"
SUMMARY_DOC_PATH = REPO_ROOT / "web" / "docs" / "portfolio_nacional_nrs_artefatos.md"

TOKENS_EXEMPLO = {
    "cliente_nome": "Empresa Demo (DEV)",
    "unidade_nome": "Unidade Piloto Nacional",
    "engenheiro_responsavel": "Engenheiro Revisor (Dev)",
    "crea_art": "CREA 123456/D | ART 2026-0001",
    "revisao_template": "v1",
}

KIND_DEFAULTS: dict[str, dict[str, Any]] = {
    "inspection": {
        "min_fotos": 4,
        "min_documentos": 0,
        "min_textos": 1,
        "tipo_entrega": "inspecao_tecnica",
        "modo_execucao": "in_loco",
        "titles": {
            "kicker": "Tariel.ia | Biblioteca Nacional de Inspecao",
            "escopo": "Escopo da Inspecao",
            "execucao": "Execucao em Campo",
            "finding": "Achados Tecnicos e Pontos de Atencao",
        },
    },
    "test": {
        "min_fotos": 3,
        "min_documentos": 0,
        "min_textos": 1,
        "tipo_entrega": "teste_tecnico",
        "modo_execucao": "campo_controlado",
        "titles": {
            "kicker": "Tariel.ia | Biblioteca Nacional de Testes",
            "escopo": "Escopo do Teste",
            "execucao": "Execucao do Teste",
            "finding": "Desvios e Registros de Teste",
        },
    },
    "documentation": {
        "min_fotos": 1,
        "min_documentos": 1,
        "min_textos": 1,
        "tipo_entrega": "pacote_documental",
        "modo_execucao": "analise_documental",
        "titles": {
            "kicker": "Tariel.ia | Biblioteca Nacional Documental",
            "escopo": "Escopo Documental",
            "execucao": "Consolidacao Documental",
            "finding": "Lacunas, Pendencias e Pontos de Atencao",
        },
    },
    "engineering": {
        "min_fotos": 0,
        "min_documentos": 1,
        "min_textos": 1,
        "tipo_entrega": "engenharia",
        "modo_execucao": "analise_e_modelagem",
        "titles": {
            "kicker": "Tariel.ia | Biblioteca Nacional de Engenharia",
            "escopo": "Escopo de Engenharia",
            "execucao": "Execucao Tecnica",
            "finding": "Lacunas Tecnicas e Interfaces",
        },
    },
    "calculation": {
        "min_fotos": 0,
        "min_documentos": 1,
        "min_textos": 1,
        "tipo_entrega": "calculo_tecnico",
        "modo_execucao": "memoria_de_calculo",
        "titles": {
            "kicker": "Tariel.ia | Biblioteca Nacional de Calculo",
            "escopo": "Escopo do Calculo",
            "execucao": "Dados, Premissas e Processamento",
            "finding": "Lacunas Tecnicas e Sensibilidades",
        },
    },
    "training": {
        "min_fotos": 1,
        "min_documentos": 1,
        "min_textos": 1,
        "tipo_entrega": "treinamento",
        "modo_execucao": "turma_programada",
        "titles": {
            "kicker": "Tariel.ia | Biblioteca Nacional de Treinamento",
            "escopo": "Escopo do Treinamento",
            "execucao": "Execucao da Turma",
            "finding": "Pontos de Atencao e Rastreabilidade",
        },
    },
    "ndt": {
        "min_fotos": 2,
        "min_documentos": 0,
        "min_textos": 1,
        "tipo_entrega": "ensaio_nao_destrutivo",
        "modo_execucao": "campo_e_registro_tecnico",
        "titles": {
            "kicker": "Tariel.ia | Biblioteca Nacional END",
            "escopo": "Escopo do Ensaio",
            "execucao": "Execucao do Ensaio",
            "finding": "Indicacoes e Pontos de Atencao",
        },
    },
}


@dataclass(frozen=True)
class NationalFamilySpec:
    family_key: str
    nome_exibicao: str
    macro_categoria: str
    nr_code: str
    kind: str
    wave: int
    official_title: str
    objeto_exemplo: str
    localizacao_exemplo: str
    scope_example: str
    method_example: str
    document_example: str
    point_example: str
    recommendation_example: str
    status_example: str
    template_code: str | None = None


def _load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _slug_to_title(text: str) -> str:
    cleaned = text.replace("-", " ").replace("_", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return ""
    return cleaned[:1].upper() + cleaned[1:]


def _family_suffix_title(family_key: str) -> str:
    parts = family_key.split("_")
    if len(parts) > 1 and re.fullmatch(r"nr\d{2}", parts[0]):
        return _slug_to_title("_".join(parts[1:]))
    return _slug_to_title(family_key)


def _infer_kind(item: dict[str, Any], family_key: str) -> str:
    strategy = str(item.get("product_strategy") or "").strip().lower()
    key = family_key.lower()
    if key.startswith("end_"):
        return "ndt"
    if "treinamento" in key:
        return "training"
    if "teste" in key:
        return "test"
    if any(token in key for token in ("calculo_", "memoria_calculo")):
        return "calculation"
    if any(token in key for token in ("projeto", "apreciacao_", "adequacao_", "par_")):
        return "engineering"
    if strategy == "documental_base" or any(
        token in key
        for token in (
            "prontuario",
            "programa",
            "plano",
            "pcmso",
            "gro",
            "pgr",
            "ordem_servico",
            "cipa",
            "laudo_",
            "analise_ergonomica",
            "pet",
        )
    ):
        return "documentation"
    return "inspection"


def _infer_status_example(kind: str) -> str:
    if kind in {"documentation", "engineering"}:
        return "ajuste"
    return "conforme"


def _build_spec(item: dict[str, Any], family_key: str) -> NationalFamilySpec:
    nr = int(item["nr"])
    nr_code = str(item["code"]).lower()
    macro_categoria = f"NR{nr}" if nr_code.startswith("nr") else nr_code.upper()
    kind = _infer_kind(item, family_key)
    wave = int(str(item.get("programming_wave") or "wave_5").split("_")[-1])
    suffix_title = _family_suffix_title(family_key)
    nome_exibicao = f"{macro_categoria} - {suffix_title}"
    official_title = str(item.get("title") or nome_exibicao).strip()
    status_example = _infer_status_example(kind)
    return NationalFamilySpec(
        family_key=family_key,
        nome_exibicao=nome_exibicao,
        macro_categoria=macro_categoria,
        nr_code=nr_code,
        kind=kind,
        wave=wave,
        official_title=official_title,
        objeto_exemplo=f"Objeto principal do servico {suffix_title.lower()}",
        localizacao_exemplo=f"Setor tecnico associado a {macro_categoria.lower()}",
        scope_example=(
            f"Execucao do servico {suffix_title.lower()} no contexto da norma {official_title.lower()}, "
            "com consolidacao de evidencias, registros de campo ou base documental e conclusao tecnica auditavel."
        ),
        method_example=(
            f"Metodo padrao Tariel para {suffix_title.lower()}, com registro estruturado do escopo, dados de execucao, anexos principais e pontos de atencao."
        ),
        document_example=f"Pacote tecnico de referencia para {suffix_title.lower()}.",
        point_example=(
            f"Ponto de atencao controlado no servico {suffix_title.lower()}, exigindo rastreabilidade documental complementar antes do fechamento definitivo."
        ),
        recommendation_example=(
            f"Manter rastreabilidade do servico {suffix_title.lower()} e registrar formalmente qualquer ajuste, complemento documental ou revalidacao futura."
        ),
        status_example=status_example,
        template_code=family_key,
    )


def _kind_defaults(kind: str) -> dict[str, Any]:
    return KIND_DEFAULTS.get(kind, KIND_DEFAULTS["inspection"])


def _objeto_referencia() -> dict[str, Any]:
    return {
        "disponivel": None,
        "referencias": [],
        "referencias_texto": None,
        "descricao": None,
        "observacao": None,
    }


def _build_required_slots(spec: NationalFamilySpec) -> list[dict[str, Any]]:
    kind_cfg = _kind_defaults(spec.kind)
    slots = [
        {
            "slot_id": "referencia_principal",
            "label": "Referencia principal",
            "accepted_types": ["foto", "documento"],
            "required": True,
            "min_items": 1,
            "binding_path": "identificacao.referencia_principal",
            "purpose": f"Vincular a referencia principal do objeto do servico {spec.family_key}.",
        },
        {
            "slot_id": "evidencia_execucao",
            "label": "Evidencia de execucao",
            "accepted_types": ["foto", "documento", "texto"],
            "required": True,
            "min_items": 1,
            "binding_path": "execucao_servico.evidencia_execucao",
            "purpose": "Registrar a execucao principal do servico com evidencia rastreavel.",
        },
        {
            "slot_id": "evidencia_principal",
            "label": "Evidencia principal",
            "accepted_types": ["foto", "documento", "texto"],
            "required": True,
            "min_items": 1,
            "binding_path": "evidencias_e_anexos.evidencia_principal",
            "purpose": "Consolidar a evidencia principal que sustenta a conclusao do servico.",
        },
    ]
    if int(kind_cfg["min_documentos"]) > 0:
        slots.append(
            {
                "slot_id": "documento_base",
                "label": "Documento base",
                "accepted_types": ["documento"],
                "required": True,
                "min_items": 1,
                "binding_path": "evidencias_e_anexos.documento_base",
                "purpose": "Vincular o documento ancora ou memoria principal do servico.",
            }
        )
    slots.append(
        {
            "slot_id": "conclusao_servico",
            "label": "Conclusao do servico",
            "accepted_types": ["texto"],
            "required": True,
            "min_items": 1,
            "binding_path": "conclusao.conclusao_tecnica",
            "purpose": "Registrar a conclusao tecnica estruturada para revisao.",
        }
    )
    return slots


def _build_optional_slots(spec: NationalFamilySpec) -> list[dict[str, Any]]:
    return [
        {
            "slot_id": "evidencia_complementar",
            "label": "Evidencia complementar",
            "accepted_types": ["foto", "documento", "texto"],
            "required": False,
            "min_items": 0,
            "binding_path": "evidencias_e_anexos.evidencia_complementar",
            "purpose": "Registrar evidencias complementares que contextualizem o servico.",
        },
        {
            "slot_id": "documento_base",
            "label": "Documento base",
            "accepted_types": ["documento"],
            "required": False,
            "min_items": 0,
            "binding_path": "evidencias_e_anexos.documento_base",
            "purpose": "Vincular documentos de apoio quando disponiveis.",
        },
        {
            "slot_id": "registro_lacuna_ou_ponto",
            "label": "Registro de lacuna ou ponto de atencao",
            "accepted_types": ["foto", "documento", "texto"],
            "required": False,
            "min_items": 0,
            "binding_path": "nao_conformidades_ou_lacunas.evidencias",
            "purpose": "Registrar visualmente ou documentalmente os pontos de atencao do servico.",
        },
    ]


def _build_output_sections() -> list[dict[str, Any]]:
    return [
        {
            "section_id": "identificacao",
            "title": "Identificacao do Objeto",
            "required": True,
            "fields": [
                {
                    "field_id": "objeto_principal",
                    "label": "Objeto principal",
                    "type": "text",
                    "required": True,
                    "critical": True,
                    "binding_path": "identificacao.objeto_principal",
                    "source_hint": "Identificacao principal do servico, ativo, pacote ou turma.",
                },
                {
                    "field_id": "localizacao",
                    "label": "Localizacao",
                    "type": "text",
                    "required": True,
                    "critical": True,
                    "binding_path": "identificacao.localizacao",
                    "source_hint": "Referencia de localizacao do servico.",
                },
                {
                    "field_id": "referencia_principal",
                    "label": "Referencia principal",
                    "type": "document_ref",
                    "required": False,
                    "critical": False,
                    "binding_path": "identificacao.referencia_principal",
                    "source_hint": "Slot referencia_principal.",
                },
                {
                    "field_id": "codigo_interno",
                    "label": "Codigo interno",
                    "type": "text",
                    "required": False,
                    "critical": False,
                    "binding_path": "identificacao.codigo_interno",
                    "source_hint": "Codigo interno do servico quando existir.",
                },
            ],
        },
        {
            "section_id": "escopo_servico",
            "title": "Escopo do Servico",
            "required": True,
            "fields": [
                {
                    "field_id": "tipo_entrega",
                    "label": "Tipo de entrega",
                    "type": "text",
                    "required": True,
                    "critical": False,
                    "binding_path": "escopo_servico.tipo_entrega",
                    "source_hint": "Natureza do servico contratado.",
                },
                {
                    "field_id": "modo_execucao",
                    "label": "Modo de execucao",
                    "type": "text",
                    "required": True,
                    "critical": False,
                    "binding_path": "escopo_servico.modo_execucao",
                    "source_hint": "Modo principal de execucao do servico.",
                },
                {
                    "field_id": "ativo_tipo",
                    "label": "Tipo de ativo ou escopo",
                    "type": "text",
                    "required": False,
                    "critical": False,
                    "binding_path": "escopo_servico.ativo_tipo",
                    "source_hint": "Tipo principal de ativo ou escopo do servico.",
                },
                {
                    "field_id": "resumo_escopo",
                    "label": "Resumo do escopo",
                    "type": "textarea",
                    "required": True,
                    "critical": True,
                    "binding_path": "escopo_servico.resumo_escopo",
                    "source_hint": "Sintese objetiva do escopo entregue.",
                },
            ],
        },
        {
            "section_id": "execucao_servico",
            "title": "Execucao do Servico",
            "required": True,
            "fields": [
                {
                    "field_id": "metodo_aplicado",
                    "label": "Metodo aplicado",
                    "type": "textarea",
                    "required": True,
                    "critical": True,
                    "binding_path": "execucao_servico.metodo_aplicado",
                    "source_hint": "Como o servico foi executado.",
                },
                {
                    "field_id": "condicoes_observadas",
                    "label": "Condicoes observadas",
                    "type": "textarea",
                    "required": True,
                    "critical": True,
                    "binding_path": "execucao_servico.condicoes_observadas",
                    "source_hint": "Condicoes observadas durante a execucao.",
                },
                {
                    "field_id": "parametros_relevantes",
                    "label": "Parametros relevantes",
                    "type": "textarea",
                    "required": False,
                    "critical": False,
                    "binding_path": "execucao_servico.parametros_relevantes",
                    "source_hint": "Parametros, leituras ou premissas relevantes do servico.",
                },
                {
                    "field_id": "evidencia_execucao",
                    "label": "Evidencia de execucao",
                    "type": "image_slot",
                    "required": False,
                    "critical": False,
                    "binding_path": "execucao_servico.evidencia_execucao",
                    "source_hint": "Slot evidencia_execucao.",
                },
            ],
        },
        {
            "section_id": "evidencias_e_anexos",
            "title": "Evidencias e Anexos",
            "required": True,
            "fields": [
                {
                    "field_id": "evidencia_principal",
                    "label": "Evidencia principal",
                    "type": "image_slot",
                    "required": False,
                    "critical": False,
                    "binding_path": "evidencias_e_anexos.evidencia_principal",
                    "source_hint": "Slot evidencia_principal.",
                },
                {
                    "field_id": "evidencia_complementar",
                    "label": "Evidencia complementar",
                    "type": "image_slot",
                    "required": False,
                    "critical": False,
                    "binding_path": "evidencias_e_anexos.evidencia_complementar",
                    "source_hint": "Slot evidencia_complementar.",
                },
                {
                    "field_id": "documento_base",
                    "label": "Documento base",
                    "type": "document_ref",
                    "required": False,
                    "critical": False,
                    "binding_path": "evidencias_e_anexos.documento_base",
                    "source_hint": "Slot documento_base.",
                },
            ],
        },
        {
            "section_id": "documentacao_e_registros",
            "title": "Documentacao e Registros",
            "required": True,
            "fields": [
                {
                    "field_id": "documentos_disponiveis",
                    "label": "Documentos disponiveis",
                    "type": "textarea",
                    "required": True,
                    "critical": False,
                    "binding_path": "documentacao_e_registros.documentos_disponiveis",
                    "source_hint": "Registro textual dos documentos disponiveis.",
                },
                {
                    "field_id": "documentos_emitidos",
                    "label": "Documentos emitidos",
                    "type": "textarea",
                    "required": False,
                    "critical": False,
                    "binding_path": "documentacao_e_registros.documentos_emitidos",
                    "source_hint": "Pacote ou entregavel emitido pelo servico.",
                },
                {
                    "field_id": "observacoes_documentais",
                    "label": "Observacoes documentais",
                    "type": "textarea",
                    "required": False,
                    "critical": False,
                    "binding_path": "documentacao_e_registros.observacoes_documentais",
                    "source_hint": "Observacoes documentais complementares.",
                },
            ],
        },
        {
            "section_id": "nao_conformidades_ou_lacunas",
            "title": "Nao Conformidades ou Lacunas",
            "required": True,
            "fields": [
                {
                    "field_id": "ha_pontos_de_atencao",
                    "label": "Ha pontos de atencao",
                    "type": "boolean",
                    "required": True,
                    "critical": False,
                    "binding_path": "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
                    "source_hint": "Registro do servico sobre a existencia de pontos de atencao.",
                },
                {
                    "field_id": "descricao",
                    "label": "Descricao",
                    "type": "textarea",
                    "required": True,
                    "critical": False,
                    "binding_path": "nao_conformidades_ou_lacunas.descricao",
                    "source_hint": "Descricao das lacunas, pontos de atencao ou ausencia declarada.",
                },
                {
                    "field_id": "evidencias",
                    "label": "Evidencias relacionadas",
                    "type": "image_slot",
                    "required": False,
                    "critical": False,
                    "binding_path": "nao_conformidades_ou_lacunas.evidencias",
                    "source_hint": "Slot registro_lacuna_ou_ponto.",
                },
            ],
        },
        {
            "section_id": "recomendacoes",
            "title": "Recomendacoes",
            "required": True,
            "fields": [
                {
                    "field_id": "texto",
                    "label": "Recomendacoes",
                    "type": "textarea",
                    "required": True,
                    "critical": False,
                    "binding_path": "recomendacoes.texto",
                    "source_hint": "Recomendacoes e proximos passos do servico.",
                },
            ],
        },
        {
            "section_id": "conclusao",
            "title": "Conclusao",
            "required": True,
            "fields": [
                {
                    "field_id": "status",
                    "label": "Status",
                    "type": "enum",
                    "required": True,
                    "critical": False,
                    "binding_path": "conclusao.status",
                    "source_hint": "Status final do servico.",
                },
                {
                    "field_id": "conclusao_tecnica",
                    "label": "Conclusao tecnica",
                    "type": "textarea",
                    "required": True,
                    "critical": True,
                    "binding_path": "conclusao.conclusao_tecnica",
                    "source_hint": "Conclusao tecnica do servico.",
                },
                {
                    "field_id": "justificativa",
                    "label": "Justificativa",
                    "type": "textarea",
                    "required": True,
                    "critical": False,
                    "binding_path": "conclusao.justificativa",
                    "source_hint": "Sintese das evidencias e fundamentos da conclusao.",
                },
            ],
        },
    ]


def build_family_schema(spec: NationalFamilySpec) -> dict[str, Any]:
    kind_cfg = _kind_defaults(spec.kind)
    template_code = spec.template_code or spec.family_key
    return {
        "family_key": spec.family_key,
        "nome_exibicao": spec.nome_exibicao,
        "macro_categoria": spec.macro_categoria,
        "descricao": spec.scope_example,
        "schema_version": 1,
        "scope": {
            "family_lock": True,
            "allowed_nrs": [spec.nr_code],
            "allowed_contexts": [spec.family_key, spec.kind, f"wave_{spec.wave}", spec.nr_code],
            "scope_signals": [
                f"servico_principal_identificado_como_{spec.family_key}",
                "escopo_registrado_de_forma_estruturada",
                "evidencias_vinculadas_ao_servico",
                "conclusao_tecnica_formalizada",
            ],
            "out_of_scope_examples": [
                "troca_silenciosa_do_tipo_de_servico",
                "mistura_de_entregaveis_sem_definicao_de_escopo",
                "documento_sem_rastreabilidade_de_evidencias",
            ],
            "review_required": [
                "quando_o_servico_principal_nao_estiver_claro",
                "quando_houver_escopo_misto_que_induza_troca_de_familia",
                "quando_o_caso_nao_tiver_rastreabilidade_documental_minima",
            ],
        },
        "evidence_policy": {
            "minimum_evidence": {
                "fotos": kind_cfg["min_fotos"],
                "documentos": kind_cfg["min_documentos"],
                "textos": kind_cfg["min_textos"],
            },
            "required_slots": _build_required_slots(spec),
            "optional_slots": _build_optional_slots(spec),
            "checklist_groups": [
                {
                    "group_id": "identificacao_e_escopo",
                    "title": "Identificacao e escopo",
                    "required": True,
                    "items": [
                        {"item_id": "objeto_registrado", "label": "Objeto principal registrado", "critical": True},
                        {"item_id": "localizacao_registrada", "label": "Localizacao registrada", "critical": True},
                        {"item_id": "escopo_registrado", "label": "Escopo registrado", "critical": True},
                    ],
                },
                {
                    "group_id": "execucao_e_evidencias",
                    "title": "Execucao e evidencias",
                    "required": True,
                    "items": [
                        {"item_id": "metodo_registrado", "label": "Metodo aplicado registrado", "critical": True},
                        {"item_id": "evidencia_principal_vinculada", "label": "Evidencia principal vinculada", "critical": True},
                        {"item_id": "documento_base_registrado_quando_existente", "label": "Documento base registrado quando existente", "critical": False},
                    ],
                },
                {
                    "group_id": "conclusao_e_pontos",
                    "title": "Conclusao e pontos de atencao",
                    "required": True,
                    "items": [
                        {"item_id": "conclusao_registrada", "label": "Conclusao tecnica registrada", "critical": True},
                        {"item_id": "pontos_de_atencao_registrados", "label": "Pontos de atencao registrados ou ausencia declarada", "critical": True},
                        {"item_id": "recomendacoes_registradas", "label": "Recomendacoes registradas", "critical": False},
                    ],
                },
            ],
            "review_required": [
                "quando_as_evidencias_minimas_nao_forem_atendidas",
                "quando_a_referencia_principal_estiver_ilegivel_sem_documento_equivalente",
                "quando_houver_duvida_sobre_qual_documento_base_ancora_o_servico",
            ],
        },
        "review_policy": {
            "requires_family_lock": True,
            "block_on_scope_mismatch": True,
            "block_on_missing_required_evidence": True,
            "block_on_critical_field_absent": True,
            "allow_override_with_reason": True,
            "allowed_override_cases": [
                "documento_opcional_ausente_com_justificativa_registrada",
                "evidencia_complementar_substituida_por_registro_textual_com_rastreabilidade",
                "limitacao_controlada_sem_impacto_na_conclusao_critica",
            ],
            "blocking_conditions": [
                "escopo_principal_divergente_da_familia",
                "troca_silenciosa_da_familia_principal",
                "ausencia_de_objeto_principal",
                "ausencia_de_localizacao",
                "ausencia_de_slot_obrigatorio",
                "ausencia_de_conclusao_tecnica",
            ],
            "non_blocking_conditions": [
                "documento_complementar_nao_disponivel",
                "evidencia_opcional_ausente_sem_impacto_critico",
                "lacuna_documental_secundaria_registrada",
            ],
            "preferred_pendencia_types": [
                "solicitar_foto",
                "solicitar_documento",
                "pedir_confirmacao",
                "apontar_inconsistencia",
                "corrigir_familia",
                "evidencia_insuficiente",
                "campo_critico_ausente",
                "revisao_conclusao",
                "aprovacao_com_ressalva",
            ],
            "review_required": [
                "qualquer_override_deve_ser_justificado_e_revisado_pela_mesa",
                "casos_com_inconsistencia_entre_evidencia_e_registro_textual_devem_ir_para_revisao",
                "casos_com_duvida_de_enquadramento_devem_ser_bloqueados_para_revisao",
            ],
        },
        "output_schema_seed": {
            "sections": _build_output_sections(),
            "conclusion_model": {
                "required_inputs": [
                    "identificacao.objeto_principal",
                    "identificacao.localizacao",
                    "escopo_servico.resumo_escopo",
                    "execucao_servico.metodo_aplicado",
                    "execucao_servico.condicoes_observadas",
                    "conclusao.conclusao_tecnica",
                ],
                "status_options": ["conforme", "nao_conforme", "ajuste", "pendente"],
                "notes": f"A conclusao da familia {spec.family_key} depende da identificacao, do escopo, do registro de execucao e da evidencia principal vinculada.",
            },
            "review_required": [
                "validar_os_bindings_definitivos_entre_slots_e_template",
                "confirmar_enums_fechados_do_status_final_do_servico",
            ],
        },
        "template_binding_hints": {
            "preferred_template_codes": [template_code, spec.family_key],
            "suggested_binding_paths": [
                "identificacao.objeto_principal",
                "identificacao.localizacao",
                "identificacao.referencia_principal",
                "escopo_servico.tipo_entrega",
                "escopo_servico.modo_execucao",
                "escopo_servico.resumo_escopo",
                "execucao_servico.metodo_aplicado",
                "execucao_servico.condicoes_observadas",
                "execucao_servico.evidencia_execucao",
                "evidencias_e_anexos.evidencia_principal",
                "evidencias_e_anexos.documento_base",
                "documentacao_e_registros.documentos_disponiveis",
                "documentacao_e_registros.documentos_emitidos",
                "nao_conformidades_ou_lacunas.descricao",
                "recomendacoes.texto",
                "conclusao.status",
                "conclusao.conclusao_tecnica",
            ],
            "expected_image_slots": [
                "referencia_principal",
                "evidencia_execucao",
                "evidencia_principal",
                "evidencia_complementar",
                "registro_lacuna_ou_ponto",
            ],
        },
        "notes": {
            "assumptions": [
                "A familia foi gerada a partir do roadmap nacional de NRs do produto Tariel.",
                "O modelo usa contrato canonico de laudo_output e template_master compativel com o renderer atual.",
                "Detalhamento setorial e comercial pode ser refinado sem quebrar o contrato base gerado.",
            ],
            "open_questions": [
                "Validar em operacao real se o servico exige campo tecnico adicional alem do seed generico.",
                "Confirmar se existe exigencia de documento ancora especifico para todos os casos desta familia.",
            ],
        },
    }


def build_laudo_output_seed(spec: NationalFamilySpec) -> dict[str, Any]:
    template_code = spec.template_code or spec.family_key
    kind_cfg = _kind_defaults(spec.kind)
    return {
        "schema_type": "laudo_output",
        "schema_version": 1,
        "family_key": spec.family_key,
        "template_code": template_code,
        "tokens": dict(TOKENS_EXEMPLO),
        "case_context": {
            "laudo_id": None,
            "empresa_nome": None,
            "unidade_nome": None,
            "data_execucao": None,
            "data_emissao": None,
            "status_mesa": None,
            "wave_portfolio": spec.wave,
            "modalidade_laudo": kind_cfg["tipo_entrega"],
        },
        "mesa_review": {
            "status": None,
            "family_lock": True,
            "scope_mismatch": False,
            "bloqueios": [],
            "bloqueios_texto": None,
            "pendencias_resolvidas_texto": None,
            "observacoes_mesa": None,
        },
        "resumo_executivo": None,
        "identificacao": {
            "objeto_principal": None,
            "localizacao": None,
            "referencia_principal": _objeto_referencia(),
            "codigo_interno": None,
        },
        "escopo_servico": {
            "tipo_entrega": None,
            "modo_execucao": None,
            "ativo_tipo": None,
            "resumo_escopo": None,
        },
        "execucao_servico": {
            "metodo_aplicado": None,
            "condicoes_observadas": None,
            "parametros_relevantes": None,
            "evidencia_execucao": _objeto_referencia(),
        },
        "evidencias_e_anexos": {
            "evidencia_principal": _objeto_referencia(),
            "evidencia_complementar": _objeto_referencia(),
            "documento_base": _objeto_referencia(),
        },
        "documentacao_e_registros": {
            "documentos_disponiveis": None,
            "documentos_emitidos": None,
            "observacoes_documentais": None,
        },
        "nao_conformidades_ou_lacunas": {
            "ha_pontos_de_atencao": None,
            "ha_pontos_de_atencao_texto": None,
            "descricao": None,
            "evidencias": _objeto_referencia(),
        },
        "recomendacoes": {"texto": None},
        "conclusao": {
            "status": None,
            "conclusao_tecnica": None,
            "justificativa": None,
        },
    }


def build_laudo_output_exemplo(spec: NationalFamilySpec) -> dict[str, Any]:
    kind_cfg = _kind_defaults(spec.kind)
    payload = build_laudo_output_seed(spec)
    template_code = spec.template_code or spec.family_key
    payload["template_code"] = template_code
    payload["case_context"] = {
        "laudo_id": f"{spec.family_key.upper()}-2026-001",
        "empresa_nome": TOKENS_EXEMPLO["cliente_nome"],
        "unidade_nome": TOKENS_EXEMPLO["unidade_nome"],
        "data_execucao": "2026-04-08",
        "data_emissao": "2026-04-08",
        "status_mesa": "aprovado_com_ressalva",
        "wave_portfolio": spec.wave,
        "modalidade_laudo": kind_cfg["tipo_entrega"],
    }
    payload["mesa_review"] = {
        "status": "aprovado_com_ressalva",
        "family_lock": True,
        "scope_mismatch": False,
        "bloqueios": [],
        "bloqueios_texto": "Sem bloqueios pendentes para emissao.",
        "pendencias_resolvidas_texto": "Pendencias documentais secundarias foram registradas e tratadas pela Mesa.",
        "observacoes_mesa": f"Caso mantido em {spec.family_key} com rastreabilidade de escopo e evidencias.",
    }
    payload["resumo_executivo"] = (
        f"Foi executado o servico {spec.nome_exibicao.lower()} com registro estruturado do objeto principal, "
        "evidencias vinculadas, documentacao de apoio e conclusao tecnica consolidada para a Mesa."
    )
    payload["identificacao"] = {
        "objeto_principal": spec.objeto_exemplo,
        "localizacao": spec.localizacao_exemplo,
        "referencia_principal": {
            "disponivel": True,
            "referencias": ["IMG_001", "DOC_001"],
            "referencias_texto": "IMG_001; DOC_001",
            "descricao": "Referencia principal do objeto identificada com apoio de evidencia visual e documento associado.",
            "observacao": "Rastreabilidade principal confirmada para o servico.",
        },
        "codigo_interno": f"{spec.family_key.upper()}-001",
    }
    payload["escopo_servico"] = {
        "tipo_entrega": kind_cfg["tipo_entrega"],
        "modo_execucao": kind_cfg["modo_execucao"],
        "ativo_tipo": spec.macro_categoria,
        "resumo_escopo": spec.scope_example,
    }
    payload["execucao_servico"] = {
        "metodo_aplicado": spec.method_example,
        "condicoes_observadas": "Servico executado dentro do escopo previsto, com registros suficientes para revisao da Mesa e consolidacao do documento final.",
        "parametros_relevantes": spec.document_example,
        "evidencia_execucao": {
            "disponivel": True,
            "referencias": ["IMG_010", "DOC_010"],
            "referencias_texto": "IMG_010; DOC_010",
            "descricao": "Evidencia da execucao principal do servico.",
            "observacao": "Registros principais consolidados.",
        },
    }
    payload["evidencias_e_anexos"] = {
        "evidencia_principal": {
            "disponivel": True,
            "referencias": ["IMG_020"],
            "referencias_texto": "IMG_020",
            "descricao": "Evidencia principal que suporta a conclusao tecnica.",
            "observacao": "Material principal vinculado ao caso.",
        },
        "evidencia_complementar": {
            "disponivel": True,
            "referencias": ["IMG_021"],
            "referencias_texto": "IMG_021",
            "descricao": "Evidencia complementar para contextualizacao do servico.",
            "observacao": "Registro complementar sem impacto critico.",
        },
        "documento_base": {
            "disponivel": True,
            "referencias": ["DOC_001"],
            "referencias_texto": spec.document_example,
            "descricao": "Documento base ou ancora principal do servico.",
            "observacao": "Documento vinculado ao pacote final.",
        },
    }
    payload["documentacao_e_registros"] = {
        "documentos_disponiveis": spec.document_example,
        "documentos_emitidos": f"Pacote tecnico de {spec.nome_exibicao.lower()} consolidado para entrega.",
        "observacoes_documentais": f"Documento vinculado ao contexto de {spec.official_title.lower()}.",
    }
    payload["nao_conformidades_ou_lacunas"] = {
        "ha_pontos_de_atencao": spec.status_example != "conforme",
        "ha_pontos_de_atencao_texto": "Sim" if spec.status_example != "conforme" else "Nao",
        "descricao": spec.point_example
        if spec.status_example != "conforme"
        else "Nao foram identificados pontos de atencao relevantes no fechamento deste servico.",
        "evidencias": {
            "disponivel": True,
            "referencias": ["IMG_030"],
            "referencias_texto": "IMG_030",
            "descricao": "Registro relacionado aos pontos de atencao ou a ausencia declarada deles.",
            "observacao": "Evidencia vinculada ao fechamento da analise.",
        },
    }
    payload["recomendacoes"] = {"texto": spec.recommendation_example}
    payload["conclusao"] = {
        "status": spec.status_example,
        "conclusao_tecnica": (
            f"O servico {spec.nome_exibicao.lower()} foi consolidado com rastreabilidade suficiente, "
            "evidencias principais vinculadas e conclusao tecnica formalizada."
        ),
        "justificativa": (
            "A conclusao considera o escopo registrado, o metodo aplicado, a documentacao disponivel, "
            "a evidencia principal e os pontos de atencao ou sua ausencia declarada."
        ),
    }
    return payload


def _text(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def _placeholder(mode: str, key: str) -> dict[str, Any]:
    return {
        "type": "placeholder",
        "attrs": {
            "mode": mode,
            "key": key,
            "raw": f"{mode}:{key}",
        },
    }


def _paragraph(parts: list[dict[str, Any]], class_name: str = "") -> dict[str, Any]:
    payload: dict[str, Any] = {"type": "paragraph", "content": parts}
    if class_name:
        payload["attrs"] = {"className": class_name}
    return payload


def _heading(level: int, text: str) -> dict[str, Any]:
    return {"type": "heading", "attrs": {"level": level}, "content": [_text(text)]}


def _table(headers: tuple[str, str], rows: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]]) -> dict[str, Any]:
    return {
        "type": "table",
        "attrs": {"className": "doc-compact"},
        "content": [
            {
                "type": "tableRow",
                "content": [
                    {"type": "tableHeader", "content": [{"type": "paragraph", "content": [_text(headers[0])]}]},
                    {"type": "tableHeader", "content": [{"type": "paragraph", "content": [_text(headers[1])]}]},
                ],
            },
            *[
                {
                    "type": "tableRow",
                    "content": [
                        {"type": "tableCell", "content": [{"type": "paragraph", "content": left}]},
                        {"type": "tableCell", "content": [{"type": "paragraph", "content": right}]},
                    ],
                }
                for left, right in rows
            ],
        ],
    }


def _bullet_list(items: list[list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [{"type": "listItem", "content": [{"type": "paragraph", "content": item}]} for item in items],
    }


def build_template_master_seed(spec: NationalFamilySpec) -> dict[str, Any]:
    kind_cfg = _kind_defaults(spec.kind)
    titles = kind_cfg["titles"]
    template_code = spec.template_code or spec.family_key
    doc_content = [
        _paragraph([_text(titles["kicker"])], class_name="doc-kicker"),
        _heading(1, spec.nome_exibicao),
        _paragraph([_text(spec.scope_example)], class_name="doc-lead"),
        _heading(2, "1. Quadro de Controle do Documento"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Cliente")], [_placeholder("token", "cliente_nome")]),
                ([_text("Unidade")], [_placeholder("token", "unidade_nome")]),
                ([_text("ID do laudo")], [_placeholder("json_path", "case_context.laudo_id")]),
                ([_text("Modalidade")], [_placeholder("json_path", "case_context.modalidade_laudo")]),
                ([_text("Data da execucao")], [_placeholder("json_path", "case_context.data_execucao")]),
                ([_text("Data da emissao")], [_placeholder("json_path", "case_context.data_emissao")]),
                ([_text("Status Mesa")], [_placeholder("json_path", "mesa_review.status")]),
                ([_text("Family key")], [_placeholder("json_path", "family_key")]),
            ],
        ),
        _heading(2, "2. Resumo Executivo"),
        _paragraph([_placeholder("json_path", "resumo_executivo")]),
        _heading(2, f"3. {titles['escopo']}"),
        _bullet_list(
            [
                [_text("Tipo de entrega: "), _placeholder("json_path", "escopo_servico.tipo_entrega")],
                [_text("Modo de execucao: "), _placeholder("json_path", "escopo_servico.modo_execucao")],
                [_text("Ativo ou escopo principal: "), _placeholder("json_path", "escopo_servico.ativo_tipo")],
                [_text("Resumo do escopo: "), _placeholder("json_path", "escopo_servico.resumo_escopo")],
            ]
        ),
        _paragraph(
            [_text("A emissao formal depende de rastreabilidade suficiente, coerencia de escopo, evidencia vinculada e governanca valida pela Mesa.")],
            class_name="doc-note",
        ),
        _heading(2, "4. Identificacao do Objeto"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Objeto principal")], [_placeholder("json_path", "identificacao.objeto_principal")]),
                ([_text("Localizacao")], [_placeholder("json_path", "identificacao.localizacao")]),
                ([_text("Codigo interno")], [_placeholder("json_path", "identificacao.codigo_interno")]),
                (
                    [_text("Referencia principal")],
                    [
                        _placeholder("json_path", "identificacao.referencia_principal.referencias_texto"),
                        _text(" | "),
                        _placeholder("json_path", "identificacao.referencia_principal.descricao"),
                    ],
                ),
            ],
        ),
        _heading(2, f"5. {titles['execucao']}"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Metodo aplicado")], [_placeholder("json_path", "execucao_servico.metodo_aplicado")]),
                ([_text("Condicoes observadas")], [_placeholder("json_path", "execucao_servico.condicoes_observadas")]),
                ([_text("Parametros relevantes")], [_placeholder("json_path", "execucao_servico.parametros_relevantes")]),
                (
                    [_text("Evidencia de execucao")],
                    [
                        _placeholder("json_path", "execucao_servico.evidencia_execucao.referencias_texto"),
                        _text(" | "),
                        _placeholder("json_path", "execucao_servico.evidencia_execucao.descricao"),
                    ],
                ),
            ],
        ),
        _heading(2, "6. Matriz de Evidencias e Anexos"),
        _table(
            ("Item", "Consolidacao"),
            [
                (
                    [_text("Evidencia principal")],
                    [
                        _placeholder("json_path", "evidencias_e_anexos.evidencia_principal.referencias_texto"),
                        _text(" | "),
                        _placeholder("json_path", "evidencias_e_anexos.evidencia_principal.descricao"),
                    ],
                ),
                (
                    [_text("Evidencia complementar")],
                    [
                        _placeholder("json_path", "evidencias_e_anexos.evidencia_complementar.referencias_texto"),
                        _text(" | "),
                        _placeholder("json_path", "evidencias_e_anexos.evidencia_complementar.descricao"),
                    ],
                ),
                (
                    [_text("Documento base")],
                    [
                        _placeholder("json_path", "evidencias_e_anexos.documento_base.referencias_texto"),
                        _text(" | "),
                        _placeholder("json_path", "evidencias_e_anexos.documento_base.descricao"),
                    ],
                ),
            ],
        ),
        _heading(2, "7. Documentacao e Registros"),
        _table(
            ("Item", "Consolidacao"),
            [
                ([_text("Documentos disponiveis")], [_placeholder("json_path", "documentacao_e_registros.documentos_disponiveis")]),
                ([_text("Documentos emitidos")], [_placeholder("json_path", "documentacao_e_registros.documentos_emitidos")]),
                ([_text("Observacoes documentais")], [_placeholder("json_path", "documentacao_e_registros.observacoes_documentais")]),
            ],
        ),
        _heading(2, f"8. {titles['finding']}"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Ha pontos de atencao")], [_placeholder("json_path", "nao_conformidades_ou_lacunas.ha_pontos_de_atencao_texto")]),
                ([_text("Descricao")], [_placeholder("json_path", "nao_conformidades_ou_lacunas.descricao")]),
                (
                    [_text("Evidencias relacionadas")],
                    [
                        _placeholder("json_path", "nao_conformidades_ou_lacunas.evidencias.referencias_texto"),
                        _text(" | "),
                        _placeholder("json_path", "nao_conformidades_ou_lacunas.evidencias.descricao"),
                    ],
                ),
            ],
        ),
        _heading(2, "9. Recomendacoes"),
        _paragraph([_placeholder("json_path", "recomendacoes.texto")]),
        _heading(2, "10. Conclusao Tecnica"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Status")], [_placeholder("json_path", "conclusao.status")]),
                ([_text("Conclusao tecnica")], [_placeholder("json_path", "conclusao.conclusao_tecnica")]),
                ([_text("Justificativa")], [_placeholder("json_path", "conclusao.justificativa")]),
            ],
        ),
        _heading(2, "11. Governanca da Mesa"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Status da Mesa")], [_placeholder("json_path", "mesa_review.status")]),
                ([_text("Family lock")], [_placeholder("json_path", "mesa_review.family_lock")]),
                ([_text("Scope mismatch")], [_placeholder("json_path", "mesa_review.scope_mismatch")]),
                ([_text("Bloqueios")], [_placeholder("json_path", "mesa_review.bloqueios_texto")]),
                ([_text("Pendencias resolvidas")], [_placeholder("json_path", "mesa_review.pendencias_resolvidas_texto")]),
                ([_text("Observacoes da Mesa")], [_placeholder("json_path", "mesa_review.observacoes_mesa")]),
            ],
        ),
        _heading(2, "12. Assinatura e Responsabilidade"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Engenheiro responsavel")], [_placeholder("token", "engenheiro_responsavel")]),
                ([_text("CREA / ART")], [_placeholder("token", "crea_art")]),
                ([_text("Data de emissao")], [_placeholder("json_path", "case_context.data_emissao")]),
            ],
        ),
        _paragraph([_text("Documento emitido a partir do template canonicamente governado pela Tariel e validado pela Mesa.")], class_name="doc-small"),
    ]
    return {
        "family_key": spec.family_key,
        "template_code": template_code,
        "nome_template": f"{spec.nome_exibicao} - Template Profissional",
        "modo_editor": "editor_rico",
        "observacoes": "Template profissional do roadmap nacional de NRs, com quadro de controle, matriz de evidencias, conclusao tecnica e governanca da Mesa.",
        "estilo_json": {
            "pagina": {
                "size": "A4",
                "orientation": "portrait",
                "margens_mm": {"top": 18, "right": 14, "bottom": 18, "left": 14},
            },
            "tipografia": {
                "font_family": "Georgia, 'Times New Roman', serif",
                "font_size_px": 11,
                "line_height": 1.5,
            },
            "tema": {
                "primaria": "#17324d",
                "secundaria": "#55697a",
                "acento": "#b6813a",
                "suave": "#eef3f7",
                "borda": "#c5d2dc",
            },
            "cabecalho_texto": f"{{{{token:cliente_nome}}}} | {spec.nome_exibicao} | {{{{token:cliente_cnpj}}}}",
            "rodape_texto": "{{token:documento_codigo}} | {{token:documento_revisao}} | {{token:status_assinatura}} | {{token:confidencialidade_documento}}",
            "marca_dagua": {"texto": "", "opacity": 0.08, "font_size_px": 72, "rotate_deg": -32},
        },
        "documento_editor_json": {
            "version": 1,
            "doc": {"type": "doc", "content": doc_content},
        },
    }


def _summary_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Portfolio Nacional de NRs: Artefatos Canonicos",
        "",
        "Resumo da geracao nacional de familias tecnicas a partir do roadmap oficial de NRs do projeto.",
        "",
        "## Regra",
        "",
        "- um `family_schema` por familia vendavel sugerida no registro nacional;",
        "- cada familia tem `laudo_output_seed`, `laudo_output_exemplo` e `template_master_seed` profissional;",
        "- familias ja existentes foram preservadas quando o arquivo canônico ja estava no projeto.",
        "",
        "## Familias cobertas pelo roteiro nacional",
        "",
        "| Wave | Family key | Categoria | Kind | Template code | Status local |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['wave']} | `{row['family_key']}` | `{row['macro_categoria']}` | `{row['kind']}` | `{row['template_code']}` | `{row['status']}` |")
    return "\n".join(lines) + "\n"


def main() -> None:
    FAMILY_SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    registry = _load_registry()
    rows: list[dict[str, str]] = []

    for norma in registry.get("normas", []):
        if not isinstance(norma, dict):
            continue
        current_status = str(norma.get("current_status") or "").strip().lower()
        if current_status in {"revoked", "support_only"}:
            continue
        suggested_families = norma.get("suggested_families")
        if not isinstance(suggested_families, list):
            continue

        for family_key_raw in suggested_families:
            family_key = str(family_key_raw or "").strip()
            if not family_key:
                continue
            spec = _build_spec(norma, family_key)
            status = "preserved"

            schema_path = FAMILY_SCHEMAS_DIR / f"{family_key}.json"
            seed_path = FAMILY_SCHEMAS_DIR / f"{family_key}.laudo_output_seed.json"
            example_path = FAMILY_SCHEMAS_DIR / f"{family_key}.laudo_output_exemplo.json"
            template_path = FAMILY_SCHEMAS_DIR / f"{family_key}.template_master_seed.json"

            if not schema_path.exists():
                _dump_json(schema_path, build_family_schema(spec))
                _dump_json(seed_path, build_laudo_output_seed(spec))
                _dump_json(example_path, build_laudo_output_exemplo(spec))
                _dump_json(template_path, build_template_master_seed(spec))
                status = "generated"
            else:
                for path, payload in (
                    (seed_path, build_laudo_output_seed(spec)),
                    (example_path, build_laudo_output_exemplo(spec)),
                    (template_path, build_template_master_seed(spec)),
                ):
                    if not path.exists():
                        _dump_json(path, payload)
                        status = "completed_missing_artifacts"

            rows.append(
                {
                    "wave": str(spec.wave),
                    "family_key": spec.family_key,
                    "macro_categoria": spec.macro_categoria,
                    "kind": spec.kind,
                    "template_code": str(spec.template_code or spec.family_key),
                    "status": status,
                }
            )

    SUMMARY_DOC_PATH.write_text(_summary_markdown(rows), encoding="utf-8")
    print(
        json.dumps(
            {
                "familias_processadas": len(rows),
                "summary_doc": str(SUMMARY_DOC_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
