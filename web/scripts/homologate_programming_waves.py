# ruff: noqa: E501
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select


WEB_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = WEB_DIR.parents[0]
DOCS_DIR = REPO_ROOT / "docs"
WEB_DOCS_DIR = REPO_ROOT / "web" / "docs"
FAMILY_SCHEMAS_DIR = DOCS_DIR / "family_schemas"
REGISTRY_PATH = DOCS_DIR / "nr_programming_registry.json"

if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from app.domains.admin.services import (  # noqa: E402
    carregar_family_schema_canonico,
)
from app.domains.revisor.service_package import (  # noqa: E402
    materializar_documento_final_laudo_pdf,
    obter_proxima_versao_documento_emitido,
)
from app.domains.revisor.templates_laudo_support import marcar_template_status  # noqa: E402
from app.shared.database import (  # noqa: E402
    DocumentoLaudoEmitido,
    Laudo,
    SessaoLocal,
    StatusLaudo,
    StatusRevisao,
    TemplateLaudo,
    Usuario,
    commit_ou_rollback_integridade,
)
from app.shared.db.models_base import agora_utc  # noqa: E402
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

SUPPORTED_WAVES: tuple[str, ...] = ("wave_1", "wave_2", "wave_3", "wave_4")

WAVE_CONFIG: dict[str, dict[str, str]] = {
    "wave_1": {
        "label": "Onda 1",
        "title": "Nucleo vendavel de inspecao",
        "doc_name": "onda_1_homologacao_profissional.md",
        "pipeline_name": "wave_1_core_homologation",
        "source_channel": "wave_1_homologation_script",
        "logger_name": "tariel.wave1.homologation",
    },
    "wave_2": {
        "label": "Onda 2",
        "title": "Verticais setoriais",
        "doc_name": "onda_2_homologacao_profissional.md",
        "pipeline_name": "wave_2_vertical_homologation",
        "source_channel": "wave_2_homologation_script",
        "logger_name": "tariel.wave2.homologation",
    },
    "wave_3": {
        "label": "Onda 3",
        "title": "Documental, programa e apoio",
        "doc_name": "onda_3_homologacao_profissional.md",
        "pipeline_name": "wave_3_documental_homologation",
        "source_channel": "wave_3_homologation_script",
        "logger_name": "tariel.wave3.homologation",
    },
    "wave_4": {
        "label": "Onda 4",
        "title": "Governanca e excecoes",
        "doc_name": "onda_4_fechamento_governanca.md",
        "pipeline_name": "wave_4_governance_closure",
        "source_channel": "wave_4_governance_closure",
        "logger_name": "tariel.wave4.closure",
    },
}


def _registry_payload() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _save_registry_payload(payload: dict[str, Any]) -> None:
    REGISTRY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _wave_doc_path(wave_id: str) -> Path:
    return WEB_DOCS_DIR / str(WAVE_CONFIG[wave_id]["doc_name"])


def _families_for_wave(payload: dict[str, Any], wave_id: str) -> list[str]:
    families: list[str] = []
    for norma in payload.get("normas") or []:
        if str(norma.get("programming_wave") or "") != wave_id:
            continue
        for family_key in norma.get("suggested_families") or []:
            family_key_str = str(family_key or "").strip()
            if family_key_str:
                families.append(family_key_str)
    return families


def _normas_for_wave(payload: dict[str, Any], wave_id: str) -> list[dict[str, Any]]:
    return [item for item in payload.get("normas") or [] if str(item.get("programming_wave") or "") == wave_id]


def _family_kind(family_key: str) -> str:
    key = str(family_key or "").strip().lower()
    if "checklist" in key:
        return "module"
    if any(
        token in key
        for token in (
            "prontuario",
            "programa",
            "plano",
            "ordem_servico",
            "laudo_",
            "pcmso",
            "gro_",
            "pgr",
            "diagnostico",
            "gestao_",
            "auditoria_",
            "condicoes_",
            "sinalizacao",
            "cipa",
        )
    ):
        return "documentation"
    if any(token in key for token in ("apreciacao_", "projeto_", "adequacao_", "par_", "analise_")):
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


def _build_professional_seed(family_key: str, wave_label: str) -> dict[str, Any]:
    schema = _load_json(FAMILY_SCHEMAS_DIR / f"{family_key}.json")
    current_seed = _load_json(_template_seed_path(family_key))
    payload = _build_generic_template_seed(
        family_key=family_key,
        nome_exibicao=str(schema.get("nome_exibicao") or family_key).strip(),
        descricao=str(schema.get("descricao") or "").strip(),
        template_code=str(current_seed.get("template_code") or schema.get("family_key") or family_key).strip(),
    )
    payload["observacoes"] = (
        f"{str(payload.get('observacoes') or '').strip()} | Homologado para a {wave_label} nacional com acabamento profissional e emissao demo controlada."
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


def _build_wave_doc(
    *,
    wave_id: str,
    registry_payload: dict[str, Any],
    rows: list[dict[str, Any]],
    demos: list[dict[str, Any]],
) -> str:
    cfg = WAVE_CONFIG[wave_id]
    label = cfg["label"]
    title = cfg["title"]
    lines = [
        f"# {label}: Homologacao Profissional" if wave_id != "wave_4" else f"# {label}: Fechamento de Governanca",
        "",
        (
            f"Homologacao controlada da {label} nacional com seeds profissionais, rollout v2 e demos emitidos no tenant piloto."
            if wave_id != "wave_4"
            else f"Fechamento canônico da {label}, consolidando normas revogadas e itens de apoio/compliance fora da biblioteca vendável."
        ),
        "",
        "## Normas cobertas",
        "",
        "| NR | Titulo | Estrategia | Status atual |",
        "| --- | --- | --- | --- |",
    ]
    for norma in _normas_for_wave(registry_payload, wave_id):
        lines.append(
            f"| `{str(norma.get('code') or '').upper()}` | {str(norma.get('title') or '').strip()} | `{str(norma.get('product_strategy') or '')}` | `{str(norma.get('current_status') or '')}` |"
        )

    if rows:
        lines.extend(
            [
                "",
                "## Familias homologadas",
                "",
                "| Family key | Tipo | Template code | Versao | Status | Ativo |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
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
                f"- todas as familias da {label} foram promovidas para `ativo` na versao homologada;",
                "- cada familia possui seed profissional `v2` e demo emitida no tenant piloto;",
                f"- a promocao foi aplicada sem tocar os ativos ja homologados fora da {label}.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Encerramento",
                "",
                f"- a {label} foi encerrada sem criacao de templates vendaveis;",
                "- normas revogadas permanecem fora do catalogo;",
                "- normas de apoio/compliance permanecem como suporte operacional, nao como biblioteca primaria de laudos.",
            ]
        )

    lines.extend(
        [
            "",
            "## Escopo do fechamento",
            "",
            f"- bloco canônico: `{title}`;",
            f"- documento gerado automaticamente a partir do registro nacional: `{REGISTRY_PATH}`;",
            f"- artefato de saida: `{_wave_doc_path(wave_id)}`.",
        ]
    )
    return "\n".join(lines) + "\n"


async def _emit_demo_document(
    *,
    db,
    wave_id: str,
    family_key: str,
    template: TemplateLaudo,
    inspetor: Usuario,
    revisor: Usuario,
) -> dict[str, Any]:
    cfg = WAVE_CONFIG[wave_id]
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
        parecer_ia=f"Demo homologada da {cfg['label']} com pacote profissional.",
        family_key=family_key,
        family_lock=True,
        family_source=f"{wave_id}_homologation",
        codigo_hash=uuid.uuid4().hex,
        primeira_mensagem=f"Demo {cfg['label']} {family_key}"[:80],
    )
    db.add(laudo)
    db.flush()

    emissao_versao = obter_proxima_versao_documento_emitido(db, laudo_id=int(laudo.id))
    exportacao = await materializar_documento_final_laudo_pdf(
        laudo=laudo,
        template=template,
        dados_formulario=exemplo,
        emissao_versao=emissao_versao,
        issue_context={
            "source": cfg["source_channel"],
            "family_key": family_key,
            "template_version": int(template.versao or 0),
        },
    )

    documento = DocumentoLaudoEmitido(
        empresa_id=int(template.empresa_id),
        laudo_id=int(laudo.id),
        template_id=int(template.id),
        emitido_por_id=int(revisor.id),
        emissao_versao=int(exportacao.emissao_versao),
        family_key=family_key,
        template_code=str(template.codigo_template or ""),
        template_version=int(template.versao or 0),
        status_revisao_snapshot=StatusRevisao.APROVADO.value,
        readiness_state="ready_for_issue",
        issue_allowed=True,
        materialization_allowed=True,
        source_channel=cfg["source_channel"],
        pipeline_name=cfg["pipeline_name"],
        correlation_id=uuid.uuid4().hex,
        storage_root=str(exportacao.storage_root),
        arquivo_pdf_nome=str(exportacao.filename),
        arquivo_pdf_path=str(exportacao.caminho_pdf),
        arquivo_html_nome=str(exportacao.html_filename or "") or None,
        arquivo_html_path=str(exportacao.caminho_html or "") or None,
        manifest_path=str(exportacao.manifest_path or "") or None,
        payload_snapshot_path=str(exportacao.payload_snapshot_path or "") or None,
        pdf_sha256=str(exportacao.pdf_sha256 or "") or None,
        payload_sha256=str(exportacao.payload_sha256 or "") or None,
        pdf_bytes=int(exportacao.pdf_bytes or 0),
        payload_json=exemplo,
        issue_context_json={
            "source": cfg["source_channel"],
            "family_key": family_key,
            "template_code": str(template.codigo_template or ""),
        },
        emitido_em=agora_utc(),
    )
    db.add(documento)
    laudo.nome_arquivo_pdf = str(exportacao.filename)
    db.flush()
    return {
        "family_key": family_key,
        "laudo_id": int(laudo.id),
        "documento_emitido_id": int(documento.id),
        "template_code": str(template.codigo_template or ""),
        "pdf_path": str(exportacao.caminho_pdf),
        "html_path": str(exportacao.caminho_html or ""),
        "manifest_path": str(exportacao.manifest_path or ""),
    }


def _close_registry_waves(payload: dict[str, Any], *, closed_waves: set[str]) -> dict[str, Any]:
    updated = json.loads(json.dumps(payload))
    for norma in updated.get("normas") or []:
        current_status = str(norma.get("current_status") or "").strip().lower()
        if current_status in {"revoked", "support_only"}:
            continue
        if str(norma.get("programming_wave") or "") not in closed_waves:
            continue
        if norma.get("suggested_families"):
            norma["current_status"] = "implemented_core"
    return updated


async def _homologate_wave(
    *,
    wave_id: str,
    registry_payload: dict[str, Any],
) -> dict[str, Any]:
    cfg = WAVE_CONFIG[wave_id]
    family_keys = _families_for_wave(registry_payload, wave_id)
    inventory_rows: list[dict[str, Any]] = []
    demo_rows: list[dict[str, Any]] = []

    if not family_keys:
        doc_path = _wave_doc_path(wave_id)
        doc_path.write_text(
            _build_wave_doc(wave_id=wave_id, registry_payload=registry_payload, rows=[], demos=[]),
            encoding="utf-8",
        )
        return {
            "wave_id": wave_id,
            "familias_homologadas": 0,
            "familias_ativas": 0,
            "demos_emitidas": 0,
            "doc_saida": str(doc_path),
        }

    for family_key in family_keys:
        payload = _build_professional_seed(family_key, cfg["label"])
        _dump_json(_template_seed_path(family_key), payload)

    with SessaoLocal() as db:
        admin = db.scalar(select(Usuario).where(Usuario.email == ADMIN_EMAIL_PADRAO))
        inspetor = db.scalar(select(Usuario).where(Usuario.email == INSPETOR_EMAIL_PADRAO))
        revisor = db.scalar(select(Usuario).where(Usuario.email == REVISOR_EMAIL_PADRAO))
        if admin is None or inspetor is None or revisor is None:
            raise RuntimeError("Usuarios base do piloto nao encontrados.")

        for family_key in family_keys:
            seed = _load_json(_template_seed_path(family_key))
            template, created = _obter_ou_criar_template_homologado(
                db,
                family_key=family_key,
                empresa_id=EMPRESA_ID_PADRAO,
                criado_por_id=int(admin.id),
            )
            template_code = normalizar_codigo_template(str(seed.get("template_code") or family_key))
            marcar_template_status(db, template=template, status_template="ativo")
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
            logger_operacao=logging.getLogger(cfg["logger_name"]),
            mensagem_erro=f"Falha ao sincronizar templates homologados da {cfg['label']}.",
        )

        for family_key in family_keys:
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
                    wave_id=wave_id,
                    family_key=family_key,
                    template=template,
                    inspetor=inspetor,
                    revisor=revisor,
                )
            )

        commit_ou_rollback_integridade(
            db,
            logger_operacao=logging.getLogger(cfg["logger_name"]),
            mensagem_erro=f"Falha ao emitir demos homologadas da {cfg['label']}.",
        )

    doc_path = _wave_doc_path(wave_id)
    doc_path.write_text(
        _build_wave_doc(wave_id=wave_id, registry_payload=registry_payload, rows=inventory_rows, demos=demo_rows),
        encoding="utf-8",
    )
    return {
        "wave_id": wave_id,
        "familias_homologadas": len(inventory_rows),
        "familias_ativas": len(family_keys),
        "demos_emitidas": len(demo_rows),
        "doc_saida": str(doc_path),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Homologa ondas de programacao do portfólio nacional de NRs.")
    parser.add_argument(
        "waves",
        nargs="*",
        choices=SUPPORTED_WAVES,
        default=["wave_2", "wave_3", "wave_4"],
        help="Ondas a fechar. Se omitido, fecha wave_2, wave_3 e wave_4.",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    waves = tuple(dict.fromkeys(args.waves))

    registry_payload = _registry_payload()
    closed_registry = _close_registry_waves(
        registry_payload,
        closed_waves={"wave_1", "wave_2", "wave_3"},
    )
    _save_registry_payload(closed_registry)

    summaries: list[dict[str, Any]] = []
    for wave_id in waves:
        summaries.append(await _homologate_wave(wave_id=wave_id, registry_payload=closed_registry))

    print(json.dumps({"waves": summaries}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
