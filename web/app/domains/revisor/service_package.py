from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
import zipfile
from typing import Any, Iterable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.chat.laudo_state_helpers import resolver_snapshot_leitura_caso_tecnico
from app.domains.chat.learning_helpers import listar_aprendizados_laudo, serializar_aprendizado_visual
from app.domains.chat.media_helpers import safe_remove_file
from app.domains.mesa.service import montar_pacote_mesa_laudo
from app.domains.revisor.base import (
    _agora_utc,
    _formatar_data_local,
    _gerar_pdf_placeholder_schemathesis,
    _listar_mensagens_laudo_paginadas,
)
from app.domains.revisor.common import _obter_laudo_empresa
from app.domains.revisor.service_contracts import (
    ExportacaoPacoteMesaPdf,
    ExportacaoPacoteMesaZip,
    PacoteMesaCarregado,
)
from app.shared.database import Usuario
from app.shared.official_issue_package import (
    build_official_issue_catalog_binding_trace,
    load_latest_approved_case_snapshot,
    resolve_official_issue_primary_pdf_artifact,
)
from app.shared.public_verification import build_public_verification_qr_png_bytes
from app.v2.acl.technical_case_core import build_case_status_visual_label
from nucleo.gerador_laudos import GeradorLaudos


def validar_parametros_pacote_mesa(parametros: Iterable[str]) -> None:
    parametros_invalidos = set(parametros) - {
        "limite_whispers",
        "limite_pendencias",
        "limite_revisoes",
    }
    if not parametros_invalidos:
        return

    raise HTTPException(
        status_code=422,
        detail=[
            {
                "loc": ["query", nome_parametro],
                "msg": "Extra inputs are not permitted",
                "type": "extra_forbidden",
            }
            for nome_parametro in sorted(parametros_invalidos)
        ],
    )


def carregar_historico_chat_revisor(
    banco: Session,
    *,
    laudo_id: int,
    empresa_id: int,
    cursor: int | None,
    limite: int,
) -> dict[str, Any]:
    _obter_laudo_empresa(banco, laudo_id, empresa_id)

    pagina = _listar_mensagens_laudo_paginadas(
        banco,
        laudo_id=laudo_id,
        cursor=cursor,
        limite=limite,
        com_data_longa=False,
    )

    return {
        "itens": pagina["itens"],
        "cursor_proximo": int(pagina["cursor_proximo"]) if pagina["cursor_proximo"] else None,
        "tem_mais": bool(pagina["tem_mais"]),
        "laudo_id": laudo_id,
        "limite": limite,
    }


def carregar_laudo_completo_revisor(
    banco: Session,
    *,
    laudo_id: int,
    empresa_id: int,
    incluir_historico: bool,
    cursor: int | None,
    limite: int,
) -> dict[str, Any]:
    laudo = _obter_laudo_empresa(banco, laudo_id, empresa_id)
    case_snapshot = resolver_snapshot_leitura_caso_tecnico(banco, laudo)

    return {
        "id": laudo.id,
        "hash": laudo.codigo_hash[-6:],
        "setor": laudo.setor_industrial,
        "status": laudo.status_revisao,
        "case_status": case_snapshot.canonical_status,
        "case_lifecycle_status": case_snapshot.case_lifecycle_status,
        "case_workflow_mode": case_snapshot.workflow_mode,
        "active_owner_role": case_snapshot.active_owner_role,
        "allowed_next_lifecycle_statuses": list(case_snapshot.allowed_next_lifecycle_statuses),
        "allowed_surface_actions": list(case_snapshot.allowed_surface_actions),
        "status_visual_label": build_case_status_visual_label(
            lifecycle_status=case_snapshot.case_lifecycle_status,
            active_owner_role=case_snapshot.active_owner_role,
        ),
        "tipo_template": getattr(laudo, "tipo_template", "padrao"),
        "criado_em": laudo.criado_em.strftime("%d/%m/%Y %H:%M"),
        **carregar_complementos_legado_laudo_revisor(
            banco,
            laudo=laudo,
            empresa_id=empresa_id,
            incluir_historico=incluir_historico,
            cursor=cursor,
            limite=limite,
        ),
    }


def carregar_complementos_legado_laudo_revisor(
    banco: Session,
    *,
    laudo: Any,
    empresa_id: int,
    incluir_historico: bool,
    cursor: int | None,
    limite: int,
) -> dict[str, Any]:
    historico: list[dict[str, Any]] = []
    whispers: list[dict[str, Any]] = []
    cursor_proximo: int | None = None
    tem_mais = False

    if incluir_historico:
        pagina = _listar_mensagens_laudo_paginadas(
            banco,
            laudo_id=int(laudo.id),
            cursor=cursor,
            limite=limite,
            com_data_longa=True,
        )
        historico = pagina["itens"]
        whispers = [mensagem for mensagem in historico if mensagem["is_whisper"]]
        cursor_proximo = int(pagina["cursor_proximo"]) if pagina["cursor_proximo"] else None
        tem_mais = bool(pagina["tem_mais"])

    aprendizados_visuais = [
        serializar_aprendizado_visual(item)
        for item in listar_aprendizados_laudo(banco, laudo_id=int(laudo.id), empresa_id=empresa_id)
    ]

    return {
        "dados_formulario": getattr(laudo, "dados_formulario", None),
        "historico": historico,
        "whispers": whispers,
        "aprendizados_visuais": aprendizados_visuais,
        "historico_paginado": {
            "incluir_historico": incluir_historico,
            "cursor_proximo": cursor_proximo,
            "tem_mais": tem_mais,
            "limite": limite,
        },
    }


def carregar_pacote_mesa_laudo_revisor(
    banco: Session,
    *,
    laudo_id: int,
    empresa_id: int,
    limite_whispers: int,
    limite_pendencias: int,
    limite_revisoes: int,
) -> PacoteMesaCarregado:
    laudo = _obter_laudo_empresa(banco, laudo_id, empresa_id)
    pacote = montar_pacote_mesa_laudo(
        banco,
        laudo=laudo,
        limite_whispers=limite_whispers,
        limite_pendencias=limite_pendencias,
        limite_revisoes=limite_revisoes,
    )
    return PacoteMesaCarregado(laudo=laudo, pacote=pacote)


def gerar_exportacao_pacote_mesa_laudo_pdf(
    banco: Session,
    *,
    pacote_carregado: PacoteMesaCarregado,
    usuario: Usuario,
) -> ExportacaoPacoteMesaPdf:
    laudo = pacote_carregado.laudo
    pacote = pacote_carregado.pacote

    nome_arquivo_tmp = f"Pacote_Mesa_{laudo.id}_{uuid.uuid4().hex[:12]}.pdf"
    caminho_pdf = os.path.join(tempfile.gettempdir(), nome_arquivo_tmp)

    nome_empresa = getattr(usuario.empresa, "nome_fantasia", None) or getattr(usuario.empresa, "razao_social", None) or f"Empresa #{usuario.empresa_id}"

    inspetor_nome = "Nao informado"
    if pacote.inspetor_id:
        inspetor = banco.get(Usuario, pacote.inspetor_id)
        if inspetor and inspetor.empresa_id == usuario.empresa_id:
            inspetor_nome = inspetor.nome

    revisoes_payload = [
        {
            "numero_versao": revisao.numero_versao,
            "origem": revisao.origem,
            "resumo": revisao.resumo,
            "confianca_geral": revisao.confianca_geral,
            "criado_em": _formatar_data_local(revisao.criado_em),
        }
        for revisao in pacote.revisoes_recentes
    ]
    pendencias_payload = [
        {
            "id": item.id,
            "tipo": item.tipo,
            "texto": item.texto,
            "criado_em": _formatar_data_local(item.criado_em),
            "referencia_mensagem_id": item.referencia_mensagem_id,
            "anexos": [anexo.model_dump(mode="json") for anexo in item.anexos],
        }
        for item in pacote.pendencias_abertas
    ]
    whispers_payload = [
        {
            "id": item.id,
            "tipo": item.tipo,
            "texto": item.texto,
            "criado_em": _formatar_data_local(item.criado_em),
            "referencia_mensagem_id": item.referencia_mensagem_id,
            "anexos": [anexo.model_dump(mode="json") for anexo in item.anexos],
        }
        for item in pacote.whispers_recentes
    ]

    try:
        if os.getenv("SCHEMATHESIS_TEST_HINTS", "0").strip() == "1":
            _gerar_pdf_placeholder_schemathesis(
                caminho_pdf,
                f"Pacote Mesa Laudo #{laudo.id}",
            )
        else:
            GeradorLaudos.gerar_pdf_pacote_mesa(
                caminho_saida=caminho_pdf,
                laudo_id=laudo.id,
                codigo_hash=pacote.codigo_hash,
                empresa=nome_empresa,
                inspetor=inspetor_nome,
                data_geracao=_formatar_data_local(_agora_utc()),
                tipo_template=pacote.tipo_template,
                setor_industrial=pacote.setor_industrial,
                status_revisao=pacote.status_revisao,
                status_conformidade=pacote.status_conformidade,
                ultima_interacao=_formatar_data_local(pacote.ultima_interacao_em),
                tempo_em_campo_minutos=pacote.tempo_em_campo_minutos,
                resumo_mensagens=pacote.resumo_mensagens.model_dump(mode="json"),
                resumo_evidencias=pacote.resumo_evidencias.model_dump(mode="json"),
                resumo_pendencias=pacote.resumo_pendencias.model_dump(mode="json"),
                pendencias_abertas=pendencias_payload,
                whispers_recentes=whispers_payload,
                revisoes_recentes=revisoes_payload,
                engenheiro_nome=usuario.nome,
                engenheiro_cargo="Engenheiro Revisor",
                engenheiro_crea=(str(usuario.crea or "").strip()[:40] or "Nao informado"),
                carimbo_texto="CARIMBO DIGITAL TARIEL.IA",
            )
    except Exception:
        safe_remove_file(caminho_pdf)
        raise

    return ExportacaoPacoteMesaPdf(
        caminho_pdf=caminho_pdf,
        filename=f"pacote_mesa_laudo_{laudo.id}.pdf",
    )


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        default=str,
    ).encode("utf-8")


def _sanitize_archive_name(value: str, *, fallback: str) -> str:
    nome = os.path.basename(str(value or "").strip()) or fallback
    allowed = []
    for char in nome:
        if char.isalnum() or char in {"-", "_", "."}:
            allowed.append(char)
        else:
            allowed.append("_")
    sanitized = "".join(allowed).strip("._")
    return sanitized or fallback


def _build_export_artifact_entry(
    *,
    archive_path: str,
    label: str,
    category: str,
    source: str,
    required: bool,
    present: bool,
    mime_type: str | None,
    size_bytes: int | None,
    sha256: str | None,
    summary: str | None = None,
) -> dict[str, Any]:
    return {
        "archive_path": archive_path,
        "label": label,
        "category": category,
        "source": source,
        "required": bool(required),
        "present": bool(present),
        "mime_type": mime_type,
        "size_bytes": int(size_bytes or 0) if size_bytes is not None else None,
        "sha256": sha256,
        "summary": summary,
    }


def _write_zip_bytes_artifact(
    zip_file: zipfile.ZipFile,
    *,
    archive_path: str,
    payload: bytes,
    label: str,
    category: str,
    source: str,
    required: bool,
    mime_type: str | None,
    summary: str | None = None,
) -> dict[str, Any]:
    zip_file.writestr(archive_path, payload)
    return _build_export_artifact_entry(
        archive_path=archive_path,
        label=label,
        category=category,
        source=source,
        required=required,
        present=True,
        mime_type=mime_type,
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        summary=summary,
    )


def _write_zip_file_artifact(
    zip_file: zipfile.ZipFile,
    *,
    source_path: str | None,
    archive_path: str,
    label: str,
    category: str,
    source: str,
    required: bool,
    mime_type: str | None,
    summary: str | None = None,
) -> dict[str, Any]:
    path = str(source_path or "").strip()
    if not path or not os.path.isfile(path):
        return _build_export_artifact_entry(
            archive_path=archive_path,
            label=label,
            category=category,
            source=source,
            required=required,
            present=False,
            mime_type=mime_type,
            size_bytes=None,
            sha256=None,
            summary=summary or "Arquivo material não localizado no disco.",
        )
    with open(path, "rb") as arquivo:
        payload = arquivo.read()
    zip_file.writestr(archive_path, payload)
    return _build_export_artifact_entry(
        archive_path=archive_path,
        label=label,
        category=category,
        source=source,
        required=required,
        present=True,
        mime_type=mime_type,
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        summary=summary,
    )


def gerar_exportacao_pacote_mesa_laudo_zip(
    banco: Session,
    *,
    pacote_carregado: PacoteMesaCarregado,
    usuario: Usuario,
) -> ExportacaoPacoteMesaZip:
    laudo = pacote_carregado.laudo
    pacote = pacote_carregado.pacote
    generated_at = _agora_utc()

    nome_arquivo_tmp = f"Pacote_Oficial_{laudo.id}_{uuid.uuid4().hex[:12]}.zip"
    caminho_zip = os.path.join(tempfile.gettempdir(), nome_arquivo_tmp)
    exportacao_pdf: ExportacaoPacoteMesaPdf | None = None

    try:
        exportacao_pdf = gerar_exportacao_pacote_mesa_laudo_pdf(
            banco,
            pacote_carregado=pacote_carregado,
            usuario=usuario,
        )
        case_snapshot = resolver_snapshot_leitura_caso_tecnico(banco, laudo)
        verification_payload = (
            pacote.verificacao_publica.model_dump(mode="json")
            if pacote.verificacao_publica is not None
            else {}
        )
        qr_payload = (
            str(verification_payload.get("qr_payload") or verification_payload.get("verification_url") or "").strip()
        )
        qr_png_bytes = build_public_verification_qr_png_bytes(qr_payload) if qr_payload else None
        anexo_pack_payload = (
            pacote.anexo_pack.model_dump(mode="json")
            if pacote.anexo_pack is not None
            else {}
        )
        emissao_oficial_payload = (
            pacote.emissao_oficial.model_dump(mode="json")
            if pacote.emissao_oficial is not None
            else {}
        )
        historico_inspecao_payload = (
            pacote.historico_inspecao.model_dump(mode="json")
            if pacote.historico_inspecao is not None
            else None
        )
        documento_estruturado_payload = (
            pacote.documento_estruturado.model_dump(mode="json")
            if pacote.documento_estruturado is not None
            else None
        )
        package_payload = pacote.model_dump(mode="json")
        audit_trail = list(emissao_oficial_payload.get("audit_trail") or [])
        latest_snapshot = load_latest_approved_case_snapshot(banco, laudo=laudo)
        catalog_binding_trace = build_official_issue_catalog_binding_trace(
            laudo=laudo,
            latest_snapshot=latest_snapshot,
        )
        catalog_snapshot_payload = (
            dict(getattr(laudo, "catalog_snapshot_json", None) or {})
            if isinstance(getattr(laudo, "catalog_snapshot_json", None), dict)
            else None
        )
        pdf_template_snapshot_payload = (
            dict(getattr(laudo, "pdf_template_snapshot_json", None) or {})
            if isinstance(getattr(laudo, "pdf_template_snapshot_json", None), dict)
            else None
        )

        artifacts: list[dict[str, Any]] = []
        with zipfile.ZipFile(caminho_zip, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            artifacts.append(
                _write_zip_bytes_artifact(
                    zip_file,
                    archive_path="payloads/pacote_mesa.json",
                    payload=_json_bytes(package_payload),
                    label="Pacote técnico da Mesa",
                    category="json",
                    source="reviewdesk_package",
                    required=True,
                    mime_type="application/json",
                    summary="Snapshot consolidado do pacote técnico governado.",
                )
            )
            artifacts.append(
                _write_zip_bytes_artifact(
                    zip_file,
                    archive_path="payloads/anexo_pack.json",
                    payload=_json_bytes(anexo_pack_payload),
                    label="Resumo do anexo pack",
                    category="json",
                    source="official_issue_package",
                    required=True,
                    mime_type="application/json",
                )
            )
            artifacts.append(
                _write_zip_bytes_artifact(
                    zip_file,
                    archive_path="payloads/emissao_oficial.json",
                    payload=_json_bytes(emissao_oficial_payload),
                    label="Resumo da emissão oficial",
                    category="json",
                    source="official_issue_package",
                    required=True,
                    mime_type="application/json",
                )
            )
            artifacts.append(
                _write_zip_bytes_artifact(
                    zip_file,
                    archive_path="payloads/verificacao_publica.json",
                    payload=_json_bytes(verification_payload),
                    label="Verificação pública",
                    category="json",
                    source="public_verification",
                    required=True,
                    mime_type="application/json",
                )
            )
            if historico_inspecao_payload is not None:
                artifacts.append(
                    _write_zip_bytes_artifact(
                        zip_file,
                        archive_path="payloads/historico_inspecao.json",
                        payload=_json_bytes(historico_inspecao_payload),
                        label="Histórico de inspeção",
                        category="json",
                        source="inspection_history",
                        required=False,
                        mime_type="application/json",
                    )
                )
            if documento_estruturado_payload is not None:
                artifacts.append(
                    _write_zip_bytes_artifact(
                        zip_file,
                        archive_path="payloads/documento_estruturado.json",
                        payload=_json_bytes(documento_estruturado_payload),
                        label="Documento estruturado",
                        category="json",
                        source="canonical_document",
                        required=False,
                        mime_type="application/json",
                    )
                )
            if isinstance(getattr(laudo, "dados_formulario", None), dict):
                artifacts.append(
                    _write_zip_bytes_artifact(
                        zip_file,
                        archive_path="documento/dados_formulario.json",
                        payload=_json_bytes(laudo.dados_formulario),
                        label="Dados de formulário",
                        category="json",
                        source="laudo_runtime",
                        required=False,
                        mime_type="application/json",
                    )
                )
            if isinstance(getattr(laudo, "report_pack_draft_json", None), dict):
                artifacts.append(
                    _write_zip_bytes_artifact(
                        zip_file,
                        archive_path="documento/report_pack_draft.json",
                        payload=_json_bytes(laudo.report_pack_draft_json),
                        label="Report pack draft",
                        category="json",
                        source="report_pack_runtime",
                        required=False,
                        mime_type="application/json",
                    )
                )
            if str(getattr(laudo, "parecer_ia", "") or "").strip():
                artifacts.append(
                    _write_zip_bytes_artifact(
                        zip_file,
                        archive_path="documento/parecer_ia.txt",
                        payload=str(laudo.parecer_ia).encode("utf-8"),
                        label="Parecer de IA",
                        category="text",
                        source="ai_draft",
                        required=False,
                        mime_type="text/plain",
                    )
                )
            artifacts.append(
                _write_zip_bytes_artifact(
                    zip_file,
                    archive_path="governanca/catalog_binding_trace.json",
                    payload=_json_bytes(catalog_binding_trace),
                    label="Rastreabilidade do binding catalogado",
                    category="json",
                    source="official_issue_catalog_binding",
                    required=True,
                    mime_type="application/json",
                    summary="Identidade congelada do catálogo/template usada na emissão oficial.",
                )
            )
            if catalog_snapshot_payload is not None:
                artifacts.append(
                    _write_zip_bytes_artifact(
                        zip_file,
                        archive_path="governanca/catalog_snapshot.json",
                        payload=_json_bytes(catalog_snapshot_payload),
                        label="Snapshot catalogado do caso",
                        category="json",
                        source="official_issue_catalog_snapshot",
                        required=False,
                        mime_type="application/json",
                    )
                )
            if pdf_template_snapshot_payload is not None:
                artifacts.append(
                    _write_zip_bytes_artifact(
                        zip_file,
                        archive_path="governanca/pdf_template_snapshot.json",
                        payload=_json_bytes(pdf_template_snapshot_payload),
                        label="Snapshot do template PDF",
                        category="json",
                        source="official_issue_pdf_template_snapshot",
                        required=False,
                        mime_type="application/json",
                    )
                )
            artifacts.append(
                _write_zip_file_artifact(
                    zip_file,
                    source_path=exportacao_pdf.caminho_pdf if exportacao_pdf is not None else None,
                    archive_path="exports/pacote_mesa_review.pdf",
                    label="PDF do pacote técnico da Mesa",
                    category="pdf",
                    source="reviewdesk_pdf_export",
                    required=True,
                    mime_type="application/pdf",
                )
            )
            primary_pdf_artifact = resolve_official_issue_primary_pdf_artifact(laudo)
            if primary_pdf_artifact is not None:
                artifacts.append(
                    _write_zip_file_artifact(
                        zip_file,
                        source_path=str(primary_pdf_artifact.get("storage_path") or ""),
                        archive_path=str(primary_pdf_artifact.get("archive_path") or ""),
                        label="PDF principal emitido",
                        category="pdf",
                        source="laudo_runtime",
                        required=True,
                        mime_type="application/pdf",
                        summary=(
                            f"Documento principal emitido incluído no bundle oficial da Mesa"
                            f" ({primary_pdf_artifact['storage_version']})."
                            if primary_pdf_artifact.get("storage_version")
                            else "Documento principal emitido incluído no bundle oficial da Mesa."
                        ),
                    )
                )
            if qr_png_bytes:
                artifacts.append(
                    _write_zip_bytes_artifact(
                        zip_file,
                        archive_path="metadados/verificacao_publica_qr.png",
                        payload=qr_png_bytes,
                        label="QR de verificação pública",
                        category="image",
                        source="public_verification",
                        required=False,
                        mime_type="image/png",
                    )
                )

            for attachment in list(getattr(laudo, "anexos_mesa", None) or []):
                safe_name = _sanitize_archive_name(
                    str(attachment.nome_original or attachment.nome_arquivo or ""),
                    fallback=f"anexo_mesa_{int(attachment.id)}",
                )
                artifacts.append(
                    _write_zip_file_artifact(
                        zip_file,
                        source_path=getattr(attachment, "caminho_arquivo", None),
                        archive_path=f"anexos_mesa/{int(attachment.id)}_{safe_name}",
                        label=str(attachment.nome_original or attachment.nome_arquivo or f"Anexo #{int(attachment.id)}"),
                        category="image" if str(attachment.categoria or "") == "imagem" else "document",
                        source="mesa_attachment",
                        required=False,
                        mime_type=str(attachment.mime_type or "application/octet-stream"),
                        summary="Anexo material associado à revisão da Mesa.",
                    )
                )

            manifest = {
                "bundle_kind": "tariel_official_issue_package",
                "bundle_version": "v1",
                "generated_at": generated_at.isoformat(),
                "laudo_id": int(laudo.id),
                "codigo_hash": str(pacote.codigo_hash or ""),
                "empresa_id": int(getattr(laudo, "empresa_id", 0) or 0),
                "tipo_template": str(pacote.tipo_template or ""),
                "family_key": str(getattr(laudo, "catalog_family_key", "") or ""),
                "status_revisao": str(pacote.status_revisao or ""),
                "case_status": case_snapshot.canonical_status,
                "case_lifecycle_status": case_snapshot.case_lifecycle_status,
                "case_workflow_mode": case_snapshot.workflow_mode,
                "active_owner_role": case_snapshot.active_owner_role,
                "allowed_next_lifecycle_statuses": list(case_snapshot.allowed_next_lifecycle_statuses),
                "allowed_surface_actions": list(case_snapshot.allowed_surface_actions),
                "status_visual_label": str(
                    build_case_status_visual_label(
                        lifecycle_status=case_snapshot.case_lifecycle_status,
                        active_owner_role=case_snapshot.active_owner_role,
                    )
                    or ""
                ),
                "status_conformidade": str(pacote.status_conformidade or ""),
                "issue_status": str(emissao_oficial_payload.get("issue_status") or ""),
                "issue_status_label": str(emissao_oficial_payload.get("issue_status_label") or ""),
                "ready_for_issue": bool(emissao_oficial_payload.get("ready_for_issue")),
                "catalog_binding_trace": catalog_binding_trace,
                "artifact_count": len(artifacts) + 1,
                "materialized_artifact_count": sum(1 for item in artifacts if bool(item.get("present"))),
                "audit_trail_count": len(audit_trail),
                "audit_trail": audit_trail,
                "artifacts": artifacts,
                "generated_by": {
                    "reviewer_id": int(getattr(usuario, "id", 0) or 0),
                    "reviewer_name": str(getattr(usuario, "nome", "") or ""),
                    "reviewer_crea": str(getattr(usuario, "crea", "") or ""),
                },
            }
            manifest_bytes = _json_bytes(manifest)
            zip_file.writestr("manifest.json", manifest_bytes)
            artifacts.insert(
                0,
                _build_export_artifact_entry(
                    archive_path="manifest.json",
                    label="Manifesto do pacote oficial",
                    category="json",
                    source="bundle_manifest",
                    required=True,
                    present=True,
                    mime_type="application/json",
                    size_bytes=len(manifest_bytes),
                    sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                    summary="Inventário e hashes SHA-256 do pacote exportado.",
                ),
            )

        hash_curto = str(pacote.codigo_hash or laudo.id)[-8:]
        return ExportacaoPacoteMesaZip(
            caminho_zip=caminho_zip,
            filename=f"pacote_oficial_{hash_curto}.zip",
        )
    except Exception:
        safe_remove_file(caminho_zip)
        raise
    finally:
        if exportacao_pdf is not None:
            safe_remove_file(exportacao_pdf.caminho_pdf)


__all__ = [
    "carregar_historico_chat_revisor",
    "carregar_laudo_completo_revisor",
    "carregar_pacote_mesa_laudo_revisor",
    "gerar_exportacao_pacote_mesa_laudo_pdf",
    "gerar_exportacao_pacote_mesa_laudo_zip",
    "validar_parametros_pacote_mesa",
]
