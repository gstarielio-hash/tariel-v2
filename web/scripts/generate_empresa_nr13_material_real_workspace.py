# ruff: noqa: E501
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "docs" / "family_schemas"
OUT_DIR = REPO_ROOT / "docs" / "portfolio_empresa_nr13_material_real"
SUMMARY_DOC = REPO_ROOT / "web" / "docs" / "portfolio_empresa_nr13_material_real.md"

KINDS = ("inspection", "test", "documentation", "engineering", "calculation", "training", "ndt")

WAVE_MAP = {
    "nr13_inspecao_vaso_pressao": 1,
    "nr13_inspecao_caldeira": 1,
    "nr13_inspecao_tubulacao": 1,
    "nr13_integridade_caldeira": 1,
    "nr13_teste_hidrostatico": 1,
    "nr13_teste_estanqueidade_tubulacao_gas": 1,
    "nr13_reconstituicao_prontuario": 2,
    "nr13_abertura_livro_registro_seguranca": 2,
    "nr13_levantamento_in_loco_equipamentos": 2,
    "nr13_fluxograma_linhas_acessorios": 2,
    "nr13_adequacao_planta_industrial": 3,
    "nr13_projeto_instalacao": 3,
    "nr13_par_projeto_alteracao_reparo": 3,
    "nr13_calculo_pmta_vaso_pressao": 3,
    "nr13_calculo_espessura_minima_caldeira": 3,
    "nr13_calculo_espessura_minima_vaso_pressao": 3,
    "nr13_calculo_espessura_minima_tubulacao": 3,
    "nr13_treinamento_operacao_caldeira": 4,
    "nr13_treinamento_operacao_unidades_processo": 4,
    "end_medicao_espessura_ultrassom": 5,
    "end_ultrassom_junta_soldada": 5,
    "end_liquido_penetrante": 5,
    "end_particula_magnetica": 5,
    "end_visual_solda": 5,
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _family_schema_files() -> list[Path]:
    arquivos: list[Path] = []
    for path in sorted(SCHEMAS_DIR.glob("*.json")):
        nome = path.name
        if (
            nome.endswith(".laudo_output_seed.json")
            or nome.endswith(".laudo_output_exemplo.json")
            or nome.endswith(".template_master_seed.json")
        ):
            continue
        arquivos.append(path)
    return arquivos


def _infer_kind(schema: dict[str, Any], family_key: str) -> str:
    scope = schema.get("scope") if isinstance(schema.get("scope"), dict) else {}
    allowed_contexts = scope.get("allowed_contexts") if isinstance(scope.get("allowed_contexts"), list) else []
    for kind in KINDS:
        if kind in allowed_contexts:
            return kind
    if family_key.startswith("end_"):
        return "ndt"
    if "teste" in family_key:
        return "test"
    if "treinamento" in family_key:
        return "training"
    if "calculo" in family_key:
        return "calculation"
    if "projeto" in family_key or family_key.endswith("_reparo") or "adequacao" in family_key:
        return "engineering"
    if "prontuario" in family_key or "livro" in family_key or "levantamento" in family_key or "fluxograma" in family_key:
        return "documentation"
    return "inspection"


def _infer_wave(schema: dict[str, Any], family_key: str) -> int:
    scope = schema.get("scope") if isinstance(schema.get("scope"), dict) else {}
    allowed_contexts = scope.get("allowed_contexts") if isinstance(scope.get("allowed_contexts"), list) else []
    for item in allowed_contexts:
        texto = str(item or "").strip().lower()
        if texto.startswith("wave_"):
            try:
                return max(1, int(texto.split("_", 1)[1]))
            except (TypeError, ValueError):
                break
    return int(WAVE_MAP.get(family_key, 5))


def _required_slots(schema: dict[str, Any]) -> list[dict[str, Any]]:
    evidence_policy = schema.get("evidence_policy") if isinstance(schema.get("evidence_policy"), dict) else {}
    slots = evidence_policy.get("required_slots") if isinstance(evidence_policy.get("required_slots"), list) else []
    return [item for item in slots if isinstance(item, dict)]


def _output_sections(schema: dict[str, Any]) -> list[str]:
    output_seed = schema.get("output_schema_seed") if isinstance(schema.get("output_schema_seed"), dict) else {}
    sections = output_seed.get("sections") if isinstance(output_seed.get("sections"), list) else []
    titulos: list[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        titulo = str(section.get("title") or section.get("section_id") or "").strip()
        if titulo:
            titulos.append(titulo)
    return titulos


def _preferred_template_codes(schema: dict[str, Any], family_key: str) -> list[str]:
    hints = schema.get("template_binding_hints") if isinstance(schema.get("template_binding_hints"), dict) else {}
    codes = hints.get("preferred_template_codes") if isinstance(hints.get("preferred_template_codes"), list) else []
    resolved: list[str] = []
    for item in [*codes, family_key]:
        texto = str(item or "").strip()
        if not texto or texto in resolved:
            continue
        resolved.append(texto)
    return resolved


def _minimum_real_documents(kind: str) -> int:
    if kind in {"inspection", "test", "ndt"}:
        return 3
    if kind in {"documentation", "engineering", "calculation"}:
        return 2
    return 1


def _base_materials(kind: str) -> list[dict[str, Any]]:
    comuns = [
        {
            "item_id": "modelo_atual_vazio",
            "label": "Modelo atual vazio usado pela empresa",
            "required": True,
            "min_items": 1,
            "accepted_examples": [".docx", ".pdf"],
            "purpose": "Comparar a estrutura atual com o template_master canonico.",
            "drop_folder": "coleta_entrada/modelo_atual_vazio",
        },
        {
            "item_id": "documentos_finais_reais",
            "label": "Documentos finais reais ja emitidos",
            "required": True,
            "min_items": _minimum_real_documents(kind),
            "accepted_examples": [".pdf", ".docx"],
            "purpose": "Extrair linguagem, estrutura efetiva e variacoes recorrentes do documento real.",
            "drop_folder": "coleta_entrada/documentos_finais_reais",
        },
        {
            "item_id": "padrao_linguagem_tecnica",
            "label": "Padrao de linguagem tecnica e conclusao",
            "required": True,
            "min_items": 1,
            "accepted_examples": [".md", ".txt", ".pdf", ".docx"],
            "purpose": "Fixar tom, parecer, ressalvas, clausulas e assinatura que a empresa realmente usa.",
            "drop_folder": "coleta_entrada/padrao_linguagem_tecnica",
        },
        {
            "item_id": "regras_comerciais_e_operacionais",
            "label": "Regras comerciais e operacionais do servico",
            "required": True,
            "min_items": 1,
            "accepted_examples": [".md", ".txt", ".pdf", ".docx", ".xlsx"],
            "purpose": "Capturar o que varia por cliente, ativo, escopo e contratacao.",
            "drop_folder": "coleta_entrada/regras_comerciais_e_operacionais",
        },
    ]

    if kind in {"inspection", "test", "ndt"}:
        comuns.append(
            {
                "item_id": "evidencias_reais_associadas",
                "label": "Evidencias reais associadas aos documentos finais",
                "required": True,
                "min_items": 1,
                "accepted_examples": [".jpg", ".jpeg", ".png", ".pdf", ".zip"],
                "purpose": "Validar slots de imagem, anexos e criterios reais de evidencia.",
                "drop_folder": "coleta_entrada/evidencias_reais_associadas",
            }
        )
    if kind in {"documentation", "engineering", "calculation"}:
        comuns.append(
            {
                "item_id": "documentos_base_e_memoria",
                "label": "Documentos base, memoria ou planilhas de apoio",
                "required": True,
                "min_items": 1,
                "accepted_examples": [".pdf", ".docx", ".xlsx", ".dwg", ".png"],
                "purpose": "Entender dados de entrada, memoria tecnica e dependencia de anexos externos.",
                "drop_folder": "coleta_entrada/documentos_base_e_memoria",
            }
        )
    if kind == "training":
        comuns.append(
            {
                "item_id": "programa_e_certificacao",
                "label": "Programa do treinamento e certificados usados",
                "required": True,
                "min_items": 1,
                "accepted_examples": [".pdf", ".docx", ".pptx", ".xlsx"],
                "purpose": "Mapear conteudo programatico, presenca, avaliacao e certificado final.",
                "drop_folder": "coleta_entrada/programa_e_certificacao",
            }
        )
    return comuns


def _slot_materials(schema: dict[str, Any]) -> list[dict[str, Any]]:
    materiais: list[dict[str, Any]] = []
    for slot in _required_slots(schema):
        slot_id = str(slot.get("slot_id") or "").strip()
        if not slot_id:
            continue
        materiais.append(
            {
                "item_id": f"slot_{slot_id}",
                "label": str(slot.get("label") or slot_id).strip(),
                "required": bool(slot.get("required", True)),
                "min_items": max(1, int(slot.get("min_items") or 1)),
                "accepted_examples": [str(item) for item in (slot.get("accepted_types") or []) if str(item or "").strip()],
                "purpose": str(slot.get("purpose") or "Validar como esse slot aparece no material real.").strip(),
                "binding_path": str(slot.get("binding_path") or "").strip(),
                "drop_folder": f"coleta_entrada/slots_reais/{slot_id}",
            }
        )
    return materiais


def _open_questions(kind: str) -> list[str]:
    perguntas = [
        "Qual documento atual a empresa considera referencia principal para esta familia?",
        "Quais anexos ou evidencias sao obrigatorios na pratica, mesmo quando nao estao escritos no modelo vazio?",
        "Quais campos sempre aparecem no documento final, mesmo quando o inspetor nao preencheu explicitamente em campo?",
        "Quais trechos de linguagem precisam seguir o padrao exato do engenheiro responsavel?",
    ]
    if kind in {"engineering", "calculation"}:
        perguntas.extend(
            [
                "Quais planilhas, memoria de calculo ou aprovacoes externas alimentam o documento final?",
                "Quais premissas tecnicas precisam ficar registradas em texto e quais podem ir so em anexo?",
            ]
        )
    if kind in {"inspection", "test", "ndt"}:
        perguntas.extend(
            [
                "Quais evidencias fotograficas entram no PDF final e quais ficam apenas em anexo ou acervo?",
                "Quais nao conformidades ou ressalvas sao mais recorrentes nessa familia?",
            ]
        )
    return perguntas


def _manifest_for_family(schema: dict[str, Any], family_key: str) -> dict[str, Any]:
    kind = _infer_kind(schema, family_key)
    wave = _infer_wave(schema, family_key)
    return {
        "family_key": family_key,
        "nome_exibicao": str(schema.get("nome_exibicao") or family_key),
        "macro_categoria": str(schema.get("macro_categoria") or ""),
        "kind": kind,
        "wave": wave,
        "template_codes": _preferred_template_codes(schema, family_key),
        "required_slots_snapshot": _slot_materials(schema),
        "output_sections_snapshot": _output_sections(schema),
        "review_blocking_snapshot": list(
            (schema.get("review_policy") or {}).get("blocking_conditions") or []
        )[:8],
        "material_real_checklist": _base_materials(kind),
        "open_questions": _open_questions(kind),
        "ingest_layout": {
            "raw_input_dir": "coleta_entrada",
            "reference_package_dir": "pacote_referencia",
            "status_file": "status_refino.json",
            "briefing_file": "briefing_real.md",
        },
        "ready_for_refinement_when": [
            "Existe ao menos 1 modelo atual vazio da empresa para a familia.",
            f"Existem ao menos {_minimum_real_documents(kind)} documentos finais reais ou equivalentes para comparacao.",
            "Existe definicao de linguagem tecnica e conclusao que a empresa quer preservar.",
            "Cada slot obrigatorio do family_schema tem exemplo real ou lacuna explicitamente anotada.",
            "O material bruto ja foi separado do futuro pacote de filled_reference.",
        ],
    }


def _briefing_markdown(schema: dict[str, Any], manifest: dict[str, Any]) -> str:
    family_key = str(manifest["family_key"])
    nome_exibicao = str(manifest["nome_exibicao"])
    materiais = manifest["material_real_checklist"]
    slots = manifest["required_slots_snapshot"]
    sections = manifest["output_sections_snapshot"]
    template_codes = manifest["template_codes"]
    perguntas = manifest["open_questions"]
    blocking = manifest["review_blocking_snapshot"]

    linhas: list[str] = [
        f"# {nome_exibicao}",
        "",
        f"- family_key: `{family_key}`",
        f"- macro_categoria: `{manifest['macro_categoria']}`",
        f"- kind: `{manifest['kind']}`",
        f"- wave: `{manifest['wave']}`",
        f"- template_codes: `{', '.join(template_codes)}`",
        "",
        "## Objetivo do refino",
        "",
        "Usar material real da empresa para ajustar linguagem, estrutura efetiva, anexos recorrentes, bindings e criterios operacionais dessa familia antes de mexer no template final ou no documento emitido.",
        "",
        "## O que coletar agora",
        "",
    ]
    for item in materiais:
        linhas.extend(
            [
                f"- `{item['item_id']}`: {item['label']}",
                f"  min_items={item['min_items']} | required={str(bool(item['required'])).lower()} | pasta=`{item['drop_folder']}`",
                f"  finalidade: {item['purpose']}",
            ]
        )
    linhas.extend(
        [
            "",
            "## Slots obrigatorios para confronto com o material real",
            "",
        ]
    )
    for slot in slots:
        linhas.extend(
            [
                f"- `{slot['item_id']}`: {slot['label']}",
                f"  binding_path=`{slot.get('binding_path') or ''}` | accepted={', '.join(slot.get('accepted_examples') or [])}",
                f"  finalidade: {slot['purpose']}",
            ]
        )
    linhas.extend(
        [
            "",
            "## Secoes esperadas no documento final",
            "",
        ]
    )
    for section in sections:
        linhas.append(f"- {section}")
    linhas.extend(
        [
            "",
            "## Perguntas que o material real precisa responder",
            "",
        ]
    )
    for pergunta in perguntas:
        linhas.append(f"- {pergunta}")
    linhas.extend(
        [
            "",
            "## Bloqueios estruturais da familia",
            "",
        ]
    )
    for item in blocking:
        linhas.append(f"- `{item}`")
    linhas.extend(
        [
            "",
            "## Layout local da coleta",
            "",
            "- `coleta_entrada/`: recepcao do material bruto da empresa",
            "- `pacote_referencia/`: futuro pacote consolidado para importacao de filled_reference",
            "- `status_refino.json`: checkpoint curto do estado da familia",
            "",
            "## Regra",
            "",
            "Nao adaptar o template final direto a partir de um PDF isolado. Primeiro fechar este pacote de coleta real, depois consolidar o blueprint/fill_reference e so entao revisar template e linguagem final.",
            "",
            f"Descricao canonica da familia: {str(schema.get('descricao') or '').strip()}",
            "",
        ]
    )
    return "\n".join(linhas)


def _status_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "family_key": manifest["family_key"],
        "status_refino": "aguardando_material_real",
        "material_recebido": [],
        "lacunas_abertas": [
            "Aguardando modelo atual vazio da empresa.",
            "Aguardando documentos finais reais para consolidar linguagem e estrutura recorrente.",
        ],
        "proximo_passo": "Preencher coleta_entrada/ com material real e consolidar pacote_referencia/.",
    }


def _incoming_readme(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Coleta de Entrada",
            "",
            f"Familia: `{manifest['family_key']}`",
            "",
            "Coloque aqui o material bruto da empresa para esta familia.",
            "",
            "Sugestao de subpastas:",
            "- `modelo_atual_vazio/`",
            "- `documentos_finais_reais/`",
            "- `padrao_linguagem_tecnica/`",
            "- `regras_comerciais_e_operacionais/`",
            "- `evidencias_reais_associadas/` ou `documentos_base_e_memoria/`, conforme a familia",
            "- `slots_reais/<slot_id>/` para exemplos que batem nos slots obrigatorios",
        ]
    )


def _reference_package_readme(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Pacote de Referencia",
            "",
            f"Familia: `{manifest['family_key']}`",
            "",
            "Depois da triagem do material bruto, esta pasta deve receber a consolidacao do pacote que sera usado para derivar blueprints e, quando aplicavel, importar referencias preenchidas.",
            "",
            "Contrato esperado pelo importador atual de filled_reference:",
            "- arquivo `manifest.json`",
            "- arquivo `tariel_filled_reference_bundle.json`",
            "- anexos auxiliares que o bundle referenciar",
            "",
            "Script de importacao existente:",
            "- `web/scripts/importar_referencias_preenchidas_zip.py`",
        ]
    )


def _summary_markdown(itens: list[dict[str, Any]]) -> str:
    linhas = [
        "# Portfolio Empresa NR13: Material Real",
        "",
        "Workspace canonica para refino por material real da empresa.",
        "",
        "## Regra",
        "",
        "- cada familia tem um manifesto de coleta, um briefing de refino, uma area para material bruto e uma area para pacote de referencia;",
        "- o objetivo aqui nao e guardar o family_schema; e fechar o gap entre a familia canonica e o jeito real como a empresa opera e escreve o documento;",
        "- toda adaptacao do template final deve passar por essa workspace antes.",
        "",
        "## Familias preparadas",
        "",
        "| Wave | Family key | Kind | Pasta de trabalho |",
        "| --- | --- | --- | --- |",
    ]
    for item in itens:
        linhas.append(
            f"| {item['wave']} | `{item['family_key']}` | `{item['kind']}` | `docs/portfolio_empresa_nr13_material_real/{item['family_key']}` |"
        )
    linhas.extend(
        [
            "",
            "## Fluxo curto",
            "",
            "1. colocar o material bruto em `coleta_entrada/` da familia;",
            "2. atualizar `status_refino.json` com o que chegou e o que ainda falta;",
            "3. consolidar o pacote em `pacote_referencia/`;",
            "4. importar o pacote de filled_reference quando ele estiver pronto;",
            "5. so depois revisar template, linguagem e bind final do documento.",
            "",
        ]
    )
    return "\n".join(linhas)


def main() -> int:
    itens_resumo: list[dict[str, Any]] = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for schema_path in _family_schema_files():
        schema = _load_json(schema_path)
        family_key = str(schema.get("family_key") or schema_path.stem).strip()
        manifest = _manifest_for_family(schema, family_key)
        familia_dir = OUT_DIR / family_key
        _write_json(familia_dir / "manifesto_coleta.json", manifest)
        _write_json(familia_dir / "status_refino.json", _status_payload(manifest))
        _write_text(familia_dir / "briefing_real.md", _briefing_markdown(schema, manifest))
        _write_text(familia_dir / "coleta_entrada" / "README.md", _incoming_readme(manifest))
        _write_text(familia_dir / "pacote_referencia" / "README.md", _reference_package_readme(manifest))
        itens_resumo.append(
            {
                "family_key": family_key,
                "kind": manifest["kind"],
                "wave": manifest["wave"],
            }
        )

    _write_text(
        OUT_DIR / "README.md",
        _summary_markdown(sorted(itens_resumo, key=lambda item: (item["wave"], item["family_key"]))),
    )
    _write_text(
        SUMMARY_DOC,
        _summary_markdown(sorted(itens_resumo, key=lambda item: (item["wave"], item["family_key"]))),
    )
    print(
        json.dumps(
            {
                "familias_preparadas": len(itens_resumo),
                "workspace_dir": str(OUT_DIR),
                "summary_doc": str(SUMMARY_DOC),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
