# ruff: noqa: E501
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = REPO_ROOT / "docs" / "portfolio_empresa_nr13_material_real"
FAMILY_SCHEMAS_DIR = REPO_ROOT / "docs" / "family_schemas"
SUMMARY_DOC = REPO_ROOT / "web" / "docs" / "portfolio_empresa_nr13_material_sintetico_base.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _family_dirs() -> list[Path]:
    itens: list[Path] = []
    if not WORKSPACE_DIR.exists():
        return itens
    for path in sorted(WORKSPACE_DIR.iterdir()):
        if not path.is_dir():
            continue
        if not (path / "manifesto_coleta.json").exists():
            continue
        itens.append(path)
    return itens


def _example_payload(family_key: str) -> dict[str, Any]:
    path = FAMILY_SCHEMAS_DIR / f"{family_key}.laudo_output_exemplo.json"
    if not path.exists():
        return {}
    return _read_json(path)


def _extract_case_title(payload: dict[str, Any]) -> str:
    identificacao = payload.get("identificacao") if isinstance(payload.get("identificacao"), dict) else {}
    return str(
        identificacao.get("identificacao_do_vaso")
        or identificacao.get("identificacao_da_caldeira")
        or identificacao.get("objeto_principal")
        or identificacao.get("codigo_interno")
        or "Objeto tecnico principal"
    ).strip()


def _extract_location(payload: dict[str, Any]) -> str:
    identificacao = payload.get("identificacao") if isinstance(payload.get("identificacao"), dict) else {}
    return str(identificacao.get("localizacao") or "Localizacao tecnica a confirmar").strip()


def _extract_conclusion(payload: dict[str, Any]) -> str:
    conclusao = payload.get("conclusao") if isinstance(payload.get("conclusao"), dict) else {}
    return str(
        conclusao.get("conclusao_tecnica")
        or conclusao.get("texto")
        or conclusao.get("status")
        or "Conclusao tecnica sintetica a confirmar com material real."
    ).strip()


def _slots_from_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    slots = manifest.get("required_slots_snapshot") if isinstance(manifest.get("required_slots_snapshot"), list) else []
    return [item for item in slots if isinstance(item, dict)]


def _sections_from_manifest(manifest: dict[str, Any]) -> list[str]:
    sections = manifest.get("output_sections_snapshot") if isinstance(manifest.get("output_sections_snapshot"), list) else []
    return [str(item).strip() for item in sections if str(item).strip()]


def _base_model_markdown(manifest: dict[str, Any], payload: dict[str, Any]) -> str:
    sections = _sections_from_manifest(manifest)
    return "\n".join(
        [
            "# Modelo Base Sintetico",
            "",
            "Status: sintetico_provisorio",
            f"Familia: `{manifest['family_key']}`",
            f"Nome: {manifest['nome_exibicao']}",
            "",
            "Este arquivo nao representa um modelo oficial da empresa. Ele existe apenas para orientar a montagem do template final enquanto o material real ainda nao foi entregue.",
            "",
            "## Estrutura sugerida",
            "",
            *[f"- {section}" for section in sections],
            "",
            "## Caso sintetico de referencia",
            "",
            f"- objeto_principal: {_extract_case_title(payload)}",
            f"- localizacao: {_extract_location(payload)}",
            f"- conclusao_base: {_extract_conclusion(payload)}",
            "",
            "## Regra",
            "",
            "Quando o modelo real da empresa chegar, este arquivo deve ser substituido ou anotado com as diferencas estruturais relevantes.",
            "",
        ]
    )


def _language_markdown(manifest: dict[str, Any], payload: dict[str, Any]) -> str:
    cliente = str(payload.get("tokens", {}).get("cliente_nome") or "Empresa alvo").strip()
    engenheiro = str(payload.get("tokens", {}).get("engenheiro_responsavel") or "Engenheiro responsavel").strip()
    return "\n".join(
        [
            "# Padrao de Linguagem Base",
            "",
            "Status: sintetico_provisorio",
            f"Familia: `{manifest['family_key']}`",
            "",
            "Objetivo: fornecer um padrao inicial de redacao tecnica enquanto a linguagem real da empresa ainda nao foi coletada.",
            "",
            "## Diretrizes",
            "",
            "- escrever em tom tecnico, objetivo e auditavel;",
            "- separar observacao, evidencia, nao conformidade e recomendacao;",
            "- evitar afirmacao normativa fina sem suporte no material do caso;",
            "- declarar ausencia de documento ou evidencia quando aplicavel;",
            "- manter a conclusao coerente com os slots obrigatorios e com os bloqueios da familia.",
            "",
            "## Formula base de conclusao",
            "",
            f"Com base nas evidencias apresentadas para {cliente}, no contexto do objeto `{_extract_case_title(payload)}`, a Mesa registra conclusao tecnica inicial: {_extract_conclusion(payload)}",
            "",
            "## Assinatura base",
            "",
            f"- responsavel tecnico sugerido: {engenheiro}",
            "- revisao_template: usar a versao ativa da familia no tenant",
            "",
        ]
    )


def _rules_markdown(manifest: dict[str, Any]) -> str:
    kind = str(manifest.get("kind") or "")
    wave = int(manifest.get("wave") or 0)
    return "\n".join(
        [
            "# Regras Operacionais Base",
            "",
            "Status: sintetico_provisorio",
            f"Familia: `{manifest['family_key']}`",
            f"Kind: `{kind}` | Wave: `{wave}`",
            "",
            "## Variacao esperada",
            "",
            "- confirmar o que muda por cliente, ativo, unidade e contrato;",
            "- confirmar se ha anexos obrigatorios na pratica;",
            "- confirmar se existe clausula comercial, ressalva ou texto padrao recorrente;",
            "- confirmar quais evidencias entram no PDF e quais ficam apenas no acervo.",
            "",
            "## Uso desta base",
            "",
            "- nao promover esta regra sintetica como regra oficial da empresa;",
            "- usar apenas para acelerar a conversa de refinamento;",
            "- substituir pelos arquivos reais assim que chegarem.",
            "",
        ]
    )


def _synthetic_document_markdown(manifest: dict[str, Any], payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Exemplo de Documento Sintetico",
            "",
            "Status: sintetico_provisorio",
            f"Familia: `{manifest['family_key']}`",
            "",
            "Este exemplo existe para orientar a leitura da familia e nao deve ser tratado como documento real emitido pela empresa.",
            "",
            f"- objeto_principal: {_extract_case_title(payload)}",
            f"- localizacao: {_extract_location(payload)}",
            f"- conclusao: {_extract_conclusion(payload)}",
            "",
            "## Campos que precisam ser comparados com o material real",
            "",
            *[
                f"- {slot.get('label')}: binding_path=`{slot.get('binding_path') or ''}`"
                for slot in _slots_from_manifest(manifest)
            ],
            "",
        ]
    )


def _support_folder_readme(manifest: dict[str, Any], item: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {item['label']}",
            "",
            "Status: aguardando_material_real",
            f"Familia: `{manifest['family_key']}`",
            "",
            f"Finalidade: {item['purpose']}",
            f"Minimo esperado: {item['min_items']}",
            "",
            "Use esta pasta para os arquivos reais da empresa. Se houver apenas material sintetico por enquanto, mantenha-o fora desta pasta ou marque explicitamente como provisorio.",
            "",
        ]
    )


def _slot_readme(manifest: dict[str, Any], slot: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Slot {slot['label']}",
            "",
            "Status: aguardando_material_real",
            f"Familia: `{manifest['family_key']}`",
            f"binding_path: `{slot.get('binding_path') or ''}`",
            f"accepted_examples: `{', '.join(slot.get('accepted_examples') or [])}`",
            "",
            f"Finalidade: {slot.get('purpose') or ''}",
            "",
            "Coloque aqui exemplos reais que demonstrem como esse slot aparece nos documentos e evidencias da empresa.",
            "",
        ]
    )


def _package_stub(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "family_key": manifest["family_key"],
        "status": "stub_sintetico",
        "description": "Stub local para orientar a futura consolidacao do pacote de filled_reference.",
        "required_files": [
            "manifest.json",
            "tariel_filled_reference_bundle.json",
        ],
        "source_of_truth": "material real consolidado em coleta_entrada/",
    }


def _status_update(status: dict[str, Any]) -> dict[str, Any]:
    atualizado = dict(status)
    atualizado["base_sintetica_disponivel"] = True
    atualizado["proximo_passo"] = "Substituir ou complementar a base sintetica com material real da empresa."
    return atualizado


def _summary_markdown(families: list[str]) -> str:
    return "\n".join(
        [
            "# Portfolio Empresa NR13: Base Sintetica",
            "",
            "Base provisoria criada para acelerar o refino das familias antes da chegada do material real da empresa.",
            "",
            "## O que foi criado em cada familia",
            "",
            "- modelo base sintetico;",
            "- padrao de linguagem base;",
            "- regras operacionais base;",
            "- exemplo sintetico de documento final;",
            "- guias de entrada por pasta e por slot obrigatorio;",
            "- stub de consolidacao do futuro pacote de referencia.",
            "",
            "## Regra",
            "",
            "- nada aqui substitui material real da empresa;",
            "- tudo aqui existe apenas como acelerador de refinamento;",
            "- quando o material real chegar, ele deve prevalecer sobre a base sintetica.",
            "",
            "## Familias cobertas",
            "",
            *[f"- `{family_key}`" for family_key in families],
            "",
        ]
    )


def main() -> int:
    families: list[str] = []
    for family_dir in _family_dirs():
        manifest = _read_json(family_dir / "manifesto_coleta.json")
        status_path = family_dir / "status_refino.json"
        status = _read_json(status_path)
        payload = _example_payload(str(manifest["family_key"]))
        family_key = str(manifest["family_key"])
        families.append(family_key)

        _write_text(
            family_dir / "coleta_entrada" / "modelo_atual_vazio" / "modelo_base_sintetico.md",
            _base_model_markdown(manifest, payload),
        )
        _write_text(
            family_dir / "coleta_entrada" / "padrao_linguagem_tecnica" / "padrao_linguagem_base.md",
            _language_markdown(manifest, payload),
        )
        _write_text(
            family_dir / "coleta_entrada" / "regras_comerciais_e_operacionais" / "regras_base.md",
            _rules_markdown(manifest),
        )
        _write_text(
            family_dir / "coleta_entrada" / "documentos_finais_reais" / "exemplo_documento_sintetico.md",
            _synthetic_document_markdown(manifest, payload),
        )

        for item in manifest.get("material_real_checklist") or []:
            if not isinstance(item, dict):
                continue
            drop_folder = str(item.get("drop_folder") or "").strip()
            if not drop_folder:
                continue
            folder = family_dir / drop_folder
            if folder.name in {
                "modelo_atual_vazio",
                "padrao_linguagem_tecnica",
                "regras_comerciais_e_operacionais",
                "documentos_finais_reais",
            }:
                continue
            _write_text(folder / "README.md", _support_folder_readme(manifest, item))

        for slot in _slots_from_manifest(manifest):
            drop_folder = str(slot.get("drop_folder") or "").strip()
            if not drop_folder:
                continue
            _write_text((family_dir / drop_folder) / "README.md", _slot_readme(manifest, slot))

        _write_json(family_dir / "pacote_referencia" / "stub_manifest.json", _package_stub(manifest))
        _write_text(
            family_dir / "pacote_referencia" / "consolidacao_base_sintetica.md",
            "\n".join(
                [
                    "# Consolidacao Base Sintetica",
                    "",
                    f"Familia: `{family_key}`",
                    "",
                    "Esta pasta ainda nao contem um pacote importavel de filled_reference.",
                    "Ela contem apenas um stub para orientar a futura consolidacao quando o material real da empresa for reunido.",
                    "",
                ]
            ),
        )
        _write_json(status_path, _status_update(status))

    _write_text(SUMMARY_DOC, _summary_markdown(sorted(families)))
    print(
        json.dumps(
            {
                "familias_atualizadas": len(families),
                "workspace_dir": str(WORKSPACE_DIR),
                "summary_doc": str(SUMMARY_DOC),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
