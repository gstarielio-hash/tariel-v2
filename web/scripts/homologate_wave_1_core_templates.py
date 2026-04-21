# ruff: noqa: E501
from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select


WEB_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = WEB_DIR.parents[0]
FAMILY_SCHEMAS_DIR = REPO_ROOT / "docs" / "family_schemas"
OUTPUT_DOC_PATH = REPO_ROOT / "web" / "docs" / "onda_1_homologacao_profissional.md"

if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from app.domains.admin.services import (  # noqa: E402
    carregar_family_schema_canonico,
)
from app.domains.chat.catalog_pdf_templates import (  # noqa: E402
    ResolvedPdfTemplateRef,
    build_catalog_pdf_payload,
)
from app.domains.revisor.templates_laudo_support import marcar_template_status  # noqa: E402
from app.shared.database import (  # noqa: E402
    Laudo,
    SessaoLocal,
    StatusLaudo,
    StatusRevisao,
    TemplateLaudo,
    Usuario,
    commit_ou_rollback_integridade,
)
from nucleo.template_editor_word import normalizar_documento_editor, normalizar_estilo_editor  # noqa: E402
from nucleo.template_laudos import normalizar_codigo_template  # noqa: E402
from scripts.professionalize_inspection_templates import (  # noqa: E402
    _build_generic_template_seed,
    _dump_json,
    _load_json,
)


EMPRESA_ID_PADRAO = 1
ADMIN_EMAIL_PADRAO = "admin@tariel.ia"
INSPETOR_EMAIL_PADRAO = "inspetor@tariel.ia"
REVISOR_EMAIL_PADRAO = "revisor@tariel.ia"
VERSAO_HOMOLOGADA = 2

WAVE_1_FAMILIES: tuple[str, ...] = (
    "nr10_inspecao_instalacoes_eletricas",
    "nr10_prontuario_instalacoes_eletricas",
    "nr12_apreciacao_risco_maquina",
    "nr12_inspecao_maquina_equipamento",
    "nr13_inspecao_caldeira",
    "nr13_inspecao_vaso_pressao",
    "nr20_inspecao_instalacoes_inflamaveis",
    "nr20_prontuario_instalacoes_inflamaveis",
    "nr33_avaliacao_espaco_confinado",
    "nr33_permissao_entrada_trabalho",
    "nr35_inspecao_linha_de_vida",
    "nr35_inspecao_ponto_ancoragem",
)

WAVE_1_ACTIVE_FAMILIES: tuple[str, ...] = (
    "nr10_inspecao_instalacoes_eletricas",
    "nr10_prontuario_instalacoes_eletricas",
    "nr12_apreciacao_risco_maquina",
    "nr12_inspecao_maquina_equipamento",
    "nr13_inspecao_caldeira",
    "nr13_inspecao_vaso_pressao",
    "nr20_inspecao_instalacoes_inflamaveis",
    "nr20_prontuario_instalacoes_inflamaveis",
    "nr33_avaliacao_espaco_confinado",
    "nr33_permissao_entrada_trabalho",
    "nr35_inspecao_linha_de_vida",
    "nr35_inspecao_ponto_ancoragem",
)


def _family_kind(family_key: str) -> str:
    key = str(family_key or "").strip().lower()
    if any(token in key for token in ("prontuario", "programa", "plano", "ordem_servico", "laudo_")):
        return "documentation"
    if any(token in key for token in ("apreciacao_", "projeto_", "adequacao_", "par_")):
        return "engineering"
    if "teste" in key:
        return "test"
    return "inspection"


def _template_seed_path(family_key: str) -> Path:
    return FAMILY_SCHEMAS_DIR / f"{family_key}.template_master_seed.json"


def _example_path(family_key: str) -> Path:
    return FAMILY_SCHEMAS_DIR / f"{family_key}.laudo_output_exemplo.json"


def _normalize_conformidade(conclusao_status: str) -> str:
    status = str(conclusao_status or "").strip().lower()
    if status == "conforme":
        return StatusLaudo.CONFORME.value
    if status == "nao_conforme":
        return StatusLaudo.NAO_CONFORME.value
    return StatusLaudo.PENDENTE.value


def _build_professional_seed(family_key: str) -> dict[str, Any]:
    schema = _load_json(FAMILY_SCHEMAS_DIR / f"{family_key}.json")
    current_seed = _load_json(_template_seed_path(family_key))
    payload = _build_generic_template_seed(
        family_key=family_key,
        nome_exibicao=str(schema.get("nome_exibicao") or family_key).strip(),
        descricao=str(schema.get("descricao") or "").strip(),
        template_code=str(current_seed.get("template_code") or schema.get("family_key") or family_key).strip(),
    )
    payload["observacoes"] = (
        f"{str(payload.get('observacoes') or '').strip()} | Homologado para a Onda 1 nacional com acabamento profissional e emissao demo controlada."
    ).strip()
    return payload


def _sync_template_from_seed(template: TemplateLaudo, seed: dict[str, Any]) -> None:
    template.nome = str(seed.get("nome_template") or template.nome or "").strip()[:180] or template.nome
    template.modo_editor = "editor_rico"
    template.documento_editor_json = normalizar_documento_editor(seed.get("documento_editor_json"))
    template.estilo_json = normalizar_estilo_editor(seed.get("estilo_json"))
    template.assets_json = []
    template.observacoes = str(seed.get("observacoes") or template.observacoes or "").strip() or template.observacoes


def _obter_ou_criar_template_homologado(
    db,
    *,
    family_key: str,
    empresa_id: int,
    criado_por_id: int | None,
) -> tuple[TemplateLaudo, bool]:
    seed = _load_json(_template_seed_path(family_key))
    schema = carregar_family_schema_canonico(family_key)
    template_code = normalizar_codigo_template(str(seed.get("template_code") or family_key))
    template = db.scalar(
        select(TemplateLaudo).where(
            TemplateLaudo.empresa_id == int(empresa_id),
            TemplateLaudo.codigo_template == template_code,
            TemplateLaudo.versao == VERSAO_HOMOLOGADA,
        )
    )
    created = False
    if template is None:
        template = TemplateLaudo(
            empresa_id=int(empresa_id),
            criado_por_id=criado_por_id,
            nome=str(seed.get("nome_template") or schema.get("nome_exibicao") or family_key).strip()[:180] or family_key,
            codigo_template=template_code,
            versao=VERSAO_HOMOLOGADA,
            ativo=False,
            base_recomendada_fixa=True,
            modo_editor="editor_rico",
            status_template="em_teste",
            arquivo_pdf_base="",
            mapeamento_campos_json={},
            documento_editor_json=normalizar_documento_editor(seed.get("documento_editor_json")),
            assets_json=[],
            estilo_json=normalizar_estilo_editor(seed.get("estilo_json")),
            observacoes=str(seed.get("observacoes") or "").strip() or None,
        )
        db.add(template)
        db.flush()
        created = True
    _sync_template_from_seed(template, seed)
    return template, created


def _build_doc(rows: list[dict[str, Any]], demos: list[dict[str, Any]]) -> str:
    lines = [
        "# Onda 1: Homologacao Profissional",
        "",
        "Homologacao controlada da Onda 1 nacional com seeds profissionais, rollout v2 e demos emitidos no tenant piloto.",
        "",
        "## Familias homologadas",
        "",
        "| Family key | Tipo | Template code | Versao | Status | Ativo |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['family_key']}` | `{row['kind']}` | `{row['template_code']}` | `{row['template_version']}` | `{row['template_status']}` | `{str(bool(row['template_active'])).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Demos emitidos",
            "",
            "| Family key | Laudo id | Template code | PDF |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in demos:
        lines.append(f"| `{item['family_key']}` | `{item['laudo_id']}` | `{item['template_code']}` | `{item['pdf_path']}` |")
    lines.extend(
        [
            "",
            "## Regra de promocao",
            "",
            "- todas as familias da Onda 1 foram promovidas para `ativo` na versao homologada;",
            "- cada familia possui seed profissional `v2` e demo emitida no tenant piloto;",
            "- a promocao foi aplicada sem tocar os ativos ja homologados fora da Onda 1.",
        ]
    )
    return "\n".join(lines) + "\n"


async def _emit_demo_document(
    *,
    db,
    family_key: str,
    template: TemplateLaudo,
    inspetor: Usuario,
    revisor: Usuario,
) -> dict[str, Any]:
    schema = carregar_family_schema_canonico(family_key)
    exemplo = _load_json(_example_path(family_key))
    laudo = Laudo(
        empresa_id=int(template.empresa_id),
        usuario_id=int(inspetor.id),
        setor_industrial=str(schema.get("macro_categoria") or family_key.split("_", 1)[0].upper()),
        tipo_template=str(template.codigo_template or family_key),
        status_conformidade=_normalize_conformidade(str((exemplo.get("conclusao") or {}).get("status") or "")),
        status_revisao=StatusRevisao.APROVADO.value,
        revisado_por=int(revisor.id),
        dados_formulario=exemplo,
        parecer_ia="Demo homologada da Onda 1 com pacote profissional.",
        catalog_family_key=family_key,
        catalog_family_label=str(schema.get("nome_exibicao") or family_key),
        catalog_variant_key="wave_1_homologation",
        catalog_variant_label="Homologação Onda 1",
        codigo_hash=uuid.uuid4().hex,
        primeira_mensagem=f"Demo Onda 1 {family_key}"[:80],
    )
    db.add(laudo)
    db.flush()

    template_ref = ResolvedPdfTemplateRef(
        source_kind="catalog_canonical_seed",
        family_key=family_key,
        template_id=int(template.id),
        codigo_template=str(template.codigo_template or family_key),
        versao=max(1, int(template.versao or 1)),
        modo_editor="editor_rico",
        arquivo_pdf_base=str(template.arquivo_pdf_base or ""),
        documento_editor_json=normalizar_documento_editor(template.documento_editor_json),
        estilo_json=normalizar_estilo_editor(template.estilo_json),
        assets_json=list(template.assets_json or []),
    )
    empresa_nome = getattr(inspetor.empresa, "nome_fantasia", None) or getattr(inspetor.empresa, "razao_social", None) or f"Empresa #{inspetor.empresa_id}"
    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=template_ref,
        source_payload=exemplo,
        diagnostico=str(exemplo.get("resumo_executivo") or f"Demo Onda 1 {family_key}"),
        inspetor=str(getattr(inspetor, "nome", "") or "Gabriel Santos"),
        empresa=str(empresa_nome),
        data=datetime.now().strftime("%d/%m/%Y"),
    )
    import app.domains.chat.chat as chat_facade

    pdf_bytes = await chat_facade.gerar_pdf_editor_rico_bytes(
        documento_editor_json=template_ref.documento_editor_json,
        estilo_json=template_ref.estilo_json,
        assets_json=template_ref.assets_json,
        dados_formulario=payload,
    )
    storage_root = WEB_DIR / "storage" / "laudos_emitidos" / f"empresa_{int(template.empresa_id)}" / f"laudo_{int(laudo.id)}" / "v0001"
    storage_root.mkdir(parents=True, exist_ok=True)
    filename = f"laudo_{int(laudo.id)}_{str(template.codigo_template or family_key)}_emitido_v0001.pdf"
    caminho_pdf = storage_root / filename
    payload_snapshot_path = storage_root / "payload_snapshot.json"
    manifest_path = storage_root / "manifest.json"
    caminho_pdf.write_bytes(pdf_bytes)
    payload_snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "source": "wave_1_homologation_script",
                "pipeline_name": "wave_1_core_homologation",
                "family_key": family_key,
                "template_code": str(template.codigo_template or family_key),
                "template_version": int(template.versao or 0),
                "storage_root": str(storage_root),
                "payload_snapshot_path": str(payload_snapshot_path),
                "pdf_path": str(caminho_pdf),
                "laudo_id": int(laudo.id),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    laudo.nome_arquivo_pdf = filename
    db.flush()
    return {
        "family_key": family_key,
        "laudo_id": int(laudo.id),
        "template_code": str(template.codigo_template or ""),
        "pdf_path": str(caminho_pdf),
        "manifest_path": str(manifest_path),
    }


async def main() -> None:
    inventory_rows: list[dict[str, Any]] = []
    demo_rows: list[dict[str, Any]] = []

    for family_key in WAVE_1_FAMILIES:
        payload = _build_professional_seed(family_key)
        _dump_json(_template_seed_path(family_key), payload)

    with SessaoLocal() as db:
        admin = db.scalar(select(Usuario).where(Usuario.email == ADMIN_EMAIL_PADRAO))
        inspetor = db.scalar(select(Usuario).where(Usuario.email == INSPETOR_EMAIL_PADRAO))
        revisor = db.scalar(select(Usuario).where(Usuario.email == REVISOR_EMAIL_PADRAO))
        if admin is None or inspetor is None or revisor is None:
            raise RuntimeError("Usuarios base do piloto nao encontrados.")

        for family_key in WAVE_1_FAMILIES:
            seed = _load_json(_template_seed_path(family_key))
            template, created = _obter_ou_criar_template_homologado(
                db,
                family_key=family_key,
                empresa_id=EMPRESA_ID_PADRAO,
                criado_por_id=int(admin.id),
            )
            template_code = normalizar_codigo_template(str(seed.get("template_code") or family_key))
            marcar_template_status(
                db,
                template=template,
                status_template="ativo" if family_key in WAVE_1_ACTIVE_FAMILIES else "em_teste",
            )
            inventory_rows.append(
                {
                    "family_key": family_key,
                    "kind": _family_kind(family_key),
                    "template_code": template_code,
                    "template_version": int(template.versao or 0),
                    "template_status": str(template.status_template or ""),
                    "template_active": bool(template.ativo),
                    "template_id": int(template.id),
                    "template_created": created,
                }
            )

        commit_ou_rollback_integridade(
            db,
            logger_operacao=logging.getLogger("tariel.wave1.homologation"),
            mensagem_erro="Falha ao sincronizar templates homologados da Onda 1.",
        )

        for family_key in WAVE_1_ACTIVE_FAMILIES:
            template_code = normalizar_codigo_template(str(_load_json(_template_seed_path(family_key)).get("template_code") or family_key))
            template = db.scalar(
                select(TemplateLaudo).where(
                    TemplateLaudo.empresa_id == EMPRESA_ID_PADRAO,
                    TemplateLaudo.codigo_template == template_code,
                    TemplateLaudo.versao == VERSAO_HOMOLOGADA,
                )
            )
            if template is None:
                raise RuntimeError(f"Template ativo nao encontrado para demo de {family_key}.")
            demo_rows.append(
                await _emit_demo_document(
                    db=db,
                    family_key=family_key,
                    template=template,
                    inspetor=inspetor,
                    revisor=revisor,
                )
            )

        commit_ou_rollback_integridade(
            db,
            logger_operacao=logging.getLogger("tariel.wave1.homologation"),
            mensagem_erro="Falha ao emitir demos homologadas da Onda 1.",
        )

    OUTPUT_DOC_PATH.write_text(_build_doc(inventory_rows, demo_rows), encoding="utf-8")
    print(
        json.dumps(
            {
                "familias_homologadas": len(inventory_rows),
                "familias_ativas": len(WAVE_1_ACTIVE_FAMILIES),
                "demos_emitidas": len(demo_rows),
                "doc_saida": str(OUTPUT_DOC_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
