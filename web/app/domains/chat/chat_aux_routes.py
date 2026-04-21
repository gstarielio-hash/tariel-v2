"""Endpoints auxiliares do chat do inspetor."""

from __future__ import annotations

from html import escape
import os
import tempfile
import uuid
from typing import Annotated

from fastapi import Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.routing import APIRouter
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.domains.chat.app_context import logger
from app.domains.chat.chat_service import obter_mensagens_laudo_payload, processar_upload_documento
from app.domains.chat.core_helpers import resposta_json_ok
from app.domains.chat.catalog_pdf_templates import (
    RENDER_MODE_CLIENT_PDF_FILLED,
    build_catalog_pdf_payload,
    has_viable_legacy_preview_overlay_for_pdf_template,
    materialize_runtime_document_editor_json,
    materialize_runtime_style_json_for_pdf_template,
    resolve_runtime_field_mapping_for_pdf_template,
    resolve_runtime_assets_for_pdf_template,
    resolve_pdf_template_for_laudo,
    should_use_rich_runtime_preview_for_pdf_template,
)
from app.domains.chat.laudo_access_helpers import obter_laudo_do_inspetor
from app.domains.chat.request_parsing_helpers import InteiroOpcionalNullish
from app.domains.chat.schemas import DadosFeedback, DadosPDF
from app.domains.chat.session_helpers import exigir_csrf, laudo_id_sessao
from app.domains.chat.media_helpers import safe_remove_file
from app.shared.backend_hotspot_metrics import observe_backend_hotspot
from app.shared.database import Laudo, Usuario, obter_banco
from app.shared.public_verification import (
    build_public_verification_payload,
    load_public_verification_payload,
)
from app.shared.security import exigir_inspetor
from app.v2.document import (
    build_document_soft_gate_route_context,
    build_document_soft_gate_trace,
    record_document_soft_gate_trace,
)
from app.v2.provenance import build_inspector_content_origin_summary, load_message_origin_counters
from app.v2.case_runtime import (
    build_legacy_case_status_payload_from_laudo,
    build_technical_case_runtime_bundle,
)
from app.v2.runtime import v2_document_soft_gate_enabled
from nucleo.gerador_laudos import GeradorLaudos
from nucleo.template_editor_word import (
    MODO_EDITOR_RICO,
    documento_editor_padrao,
    estilo_editor_padrao,
    normalizar_modo_editor,
)
from nucleo.template_laudos import gerar_preview_pdf_template

roteador_chat_aux = APIRouter()
RESPOSTA_LAUDO_NAO_ENCONTRADO = {404: {"description": "Laudo não encontrado."}}


def _registrar_soft_gate_documental_preview_pdf(
    *,
    request: Request,
    banco: Session,
    usuario: Usuario,
    laudo: Laudo | None,
    dados: DadosPDF,
    legacy_pipeline_name: str,
    legacy_compatibility_state: str | None = None,
) -> None:
    if not v2_document_soft_gate_enabled():
        return
    if laudo is None:
        return
    try:
        has_active_report = bool(laudo is not None and getattr(laudo, "id", None))
        message_counters = load_message_origin_counters(
            banco,
            laudo_id=int(laudo.id) if has_active_report else None,
        )
        provenance_summary = build_inspector_content_origin_summary(
            laudo=laudo,
            message_counters=message_counters,
            has_active_report=has_active_report,
        )
        request.state.v2_content_provenance_summary = provenance_summary.model_dump(mode="python")

        template_key = (
            str(getattr(laudo, "tipo_template", "") or "").strip()
            or str(dados.tipo_template or "").strip()
            or None
        )
        runtime_bundle = build_technical_case_runtime_bundle(
            request=request,
            banco=banco,
            usuario=usuario,
            laudo=laudo,
            legacy_payload=build_legacy_case_status_payload_from_laudo(
                banco=banco,
                laudo=laudo,
            ),
            source_channel="web_app",
            template_key=template_key,
            family_key=getattr(laudo, "catalog_family_key", None),
            variant_key=getattr(laudo, "catalog_variant_key", None),
            laudo_type=template_key,
            document_type=template_key,
            provenance_summary=provenance_summary,
            current_review_status=getattr(laudo, "status_revisao", None),
            has_form_data=bool(getattr(laudo, "dados_formulario", None)),
            has_ai_draft=bool(str(getattr(laudo, "parecer_ia", "") or "").strip()),
            report_pack_draft=getattr(laudo, "report_pack_draft_json", None),
        )

        route_context = build_document_soft_gate_route_context(
            route_name="rota_pdf",
            route_path=str(request.scope.get("path") or "/app/api/gerar_pdf"),
            http_method=str(request.method or "POST"),
            source_channel="web_app",
            operation_kind="preview_pdf",
            side_effect_free=True,
            legacy_pipeline_name=legacy_pipeline_name,
            legacy_compatibility_state=legacy_compatibility_state,
        )
        case_snapshot = runtime_bundle.case_snapshot
        document_facade = runtime_bundle.document_facade
        if case_snapshot is None or document_facade is None:
            return
        soft_gate_trace = build_document_soft_gate_trace(
            case_snapshot=case_snapshot,
            document_facade=document_facade,
            route_context=route_context,
            correlation_id=case_snapshot.correlation_id,
            request_id=(
                request.headers.get("X-Request-ID")
                or request.headers.get("X-Correlation-ID")
                or case_snapshot.correlation_id
            ),
        )
        record_document_soft_gate_trace(soft_gate_trace)
        request.state.v2_document_soft_gate_decision = soft_gate_trace.decision.model_dump(mode="python")
        request.state.v2_document_soft_gate_trace = soft_gate_trace.model_dump(mode="python")
    except Exception:
        logger.debug("Falha ao registrar soft gate documental do preview PDF.", exc_info=True)
        request.state.v2_document_soft_gate_error = "preview_pdf_soft_gate_failed"


def _renderizar_html_verificacao_publica(payload: dict[str, object]) -> str:
    empresa_nome = escape(str(payload.get("empresa_nome") or "Empresa"))
    family_label = escape(
        str(payload.get("family_label") or payload.get("family_key") or "Familia")
    )
    variant_label = escape(str(payload.get("variant_label") or payload.get("variant_key") or ""))
    selection_token = escape(str(payload.get("selection_token") or ""))
    template_code = escape(str(payload.get("template_code") or ""))
    status_revisao = escape(str(payload.get("status_revisao") or "desconhecido"))
    status_conformidade = escape(
        str(payload.get("status_conformidade") or "desconhecido")
    )
    verification_url = escape(str(payload.get("verification_url") or ""))
    codigo_hash = escape(str(payload.get("codigo_hash") or ""))
    hash_short = escape(str(payload.get("hash_short") or ""))
    approved_at = escape(str(payload.get("approved_at") or ""))
    document_outcome = escape(str(payload.get("document_outcome") or ""))
    qr_image_data_uri = escape(str(payload.get("qr_image_data_uri") or ""))
    official_issue_number = escape(str(payload.get("official_issue_number") or ""))
    official_issue_state_label = escape(str(payload.get("official_issue_state_label") or ""))
    official_issue_issued_at = escape(str(payload.get("official_issue_issued_at") or ""))
    official_issue_signatory_name = escape(str(payload.get("official_issue_signatory_name") or ""))
    official_issue_signatory_registration = escape(
        str(payload.get("official_issue_signatory_registration") or "")
    )
    official_issue_reissue_of_issue_number = escape(
        str(payload.get("official_issue_reissue_of_issue_number") or "")
    )
    official_issue_reissue_reason_summary = escape(
        str(payload.get("official_issue_reissue_reason_summary") or "")
    )
    official_issue_lineage_summary = escape(
        str(payload.get("official_issue_lineage_summary") or "")
    )
    official_issue_package_sha256 = escape(str(payload.get("official_issue_package_sha256") or ""))
    official_issue_primary_pdf_sha256 = escape(str(payload.get("official_issue_primary_pdf_sha256") or ""))
    official_issue_document_integrity_summary = escape(
        str(payload.get("official_issue_document_integrity_summary") or "")
    )
    official_issue_signatory_suffix = (
        f" · {official_issue_signatory_registration}"
        if official_issue_signatory_registration
        else ""
    )
    official_issue_summary_html = (
        (
            "<div class=\"item\"><strong>Emissao oficial</strong>"
            f"<span>{official_issue_number} · {official_issue_state_label or 'sem emissao'}</span></div>"
        )
        if official_issue_number
        else ""
    )
    official_issue_issued_at_html = (
        (
            "<div class=\"item\"><strong>Emitido em</strong>"
            f"<span>{official_issue_issued_at or 'nao informado'}</span></div>"
        )
        if official_issue_number
        else ""
    )
    official_issue_signatory_html = (
        (
            "<div class=\"item\"><strong>Signatario</strong>"
            "<span>"
            f"{official_issue_signatory_name or 'nao informado'}{official_issue_signatory_suffix}"
            "</span></div>"
        )
        if official_issue_number
        else ""
    )
    official_issue_package_html = (
        (
            "<div class=\"item\"><strong>SHA-256 pacote</strong>"
            f"<span>{official_issue_package_sha256}</span></div>"
        )
        if official_issue_package_sha256
        else ""
    )
    official_issue_lineage_html = (
        (
            "<div class=\"item\"><strong>Linhagem da emissão</strong>"
            f"<span>{official_issue_lineage_summary}</span></div>"
        )
        if official_issue_lineage_summary
        else (
            (
                "<div class=\"item\"><strong>Linhagem da emissão</strong>"
                f"<span>Esta emissão substitui {official_issue_reissue_of_issue_number}. "
                f"{official_issue_reissue_reason_summary}</span></div>"
            )
            if official_issue_reissue_of_issue_number
            else ""
        )
    )
    official_issue_primary_pdf_html = (
        (
            "<div class=\"item\"><strong>SHA-256 documento</strong>"
            f"<span>{official_issue_primary_pdf_sha256}</span></div>"
        )
        if official_issue_primary_pdf_sha256
        else ""
    )
    official_issue_document_integrity_html = (
        (
            "<div class=\"item\"><strong>Status do documento</strong>"
            f"<span>{official_issue_document_integrity_summary}</span></div>"
        )
        if official_issue_document_integrity_summary
        else ""
    )
    variant_html = (
        (
            "<div class=\"item\"><strong>Variante</strong>"
            f"<span>{variant_label}</span></div>"
        )
        if variant_label
        else ""
    )
    template_html = (
        (
            "<div class=\"item\"><strong>Template congelado</strong>"
            f"<span>{template_code}</span></div>"
        )
        if template_code
        else ""
    )
    selection_token_html = (
        (
            "<div class=\"item\"><strong>Token catalogado</strong>"
            f"<span>{selection_token}</span></div>"
        )
        if selection_token
        else ""
    )
    return f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Verificacao Publica Tariel</title>
    <style>
      :root {{
        color-scheme: dark;
        --bg: #0b1220;
        --panel: rgba(15, 23, 42, 0.92);
        --line: rgba(148, 163, 184, 0.18);
        --muted: #94a3b8;
        --text: #e2e8f0;
        --accent: #38bdf8;
        --ok: #22c55e;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
        background:
          radial-gradient(circle at top, rgba(56, 189, 248, 0.16), transparent 32%),
          linear-gradient(160deg, #020617, var(--bg));
        color: var(--text);
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      }}
      .card {{
        width: min(720px, 100%);
        border: 1px solid var(--line);
        border-radius: 22px;
        background: var(--panel);
        padding: 24px;
        box-shadow: 0 24px 80px rgba(2, 6, 23, 0.46);
      }}
      .eyebrow {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        border-radius: 999px;
        border: 1px solid rgba(34, 197, 94, 0.2);
        background: rgba(34, 197, 94, 0.12);
        color: #bbf7d0;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: .08em;
        text-transform: uppercase;
      }}
      h1 {{ margin: 16px 0 8px; font-size: 28px; }}
      p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
        margin-top: 18px;
      }}
      .item {{
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 14px;
        background: rgba(255,255,255,0.03);
      }}
      .item strong {{
        display: block;
        margin-bottom: 8px;
        color: var(--muted);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: .08em;
      }}
      .item span {{
        display: block;
        font-size: 15px;
        word-break: break-word;
      }}
      .url {{
        margin-top: 18px;
        padding: 14px;
        border-radius: 16px;
        border: 1px solid rgba(56, 189, 248, 0.22);
        background: rgba(56, 189, 248, 0.08);
      }}
      .url code {{
        display: block;
        margin-top: 8px;
        font-size: 13px;
        color: var(--accent);
        word-break: break-all;
      }}
      .verification-shell {{
        margin-top: 18px;
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: 16px;
        align-items: center;
      }}
      .verification-shell img {{
        width: 116px;
        height: 116px;
        border-radius: 18px;
        border: 1px solid var(--line);
        background: #fff;
        padding: 10px;
      }}
    </style>
  </head>
  <body>
    <article class="card">
      <div class="eyebrow">documento verificado</div>
      <h1>{empresa_nome}</h1>
      <p>Hash publico {hash_short} validado no runtime da Tariel para a familia {family_label}.</p>
      <div class="grid">
        <div class="item"><strong>Codigo hash</strong><span>{codigo_hash}</span></div>
        <div class="item"><strong>Status revisao</strong><span>{status_revisao}</span></div>
        <div class="item"><strong>Status conformidade</strong><span>{status_conformidade}</span></div>
        <div class="item"><strong>Outcome</strong><span>{document_outcome or "nao informado"}</span></div>
        <div class="item"><strong>Aprovado em</strong><span>{approved_at or "nao informado"}</span></div>
        {variant_html}
        {template_html}
        {selection_token_html}
        {official_issue_summary_html}
        {official_issue_issued_at_html}
        {official_issue_signatory_html}
        {official_issue_package_html}
        {official_issue_lineage_html}
        {official_issue_primary_pdf_html}
        {official_issue_document_integrity_html}
      </div>
      <div class="url">
        <strong>URL publica de verificacao</strong>
        <code>{verification_url}</code>
      </div>
      {f'''
      <div class="verification-shell">
        <img src="{qr_image_data_uri}" alt="QR Code de verificacao publica" />
        <p>Escaneie o QR Code para abrir a validacao publica oficial deste documento.</p>
      </div>
      ''' if qr_image_data_uri else ""}
    </article>
  </body>
</html>"""


async def rota_verificacao_publica_laudo(
    request: Request,
    codigo_hash: str,
    formato: str | None = Query(default=None, alias="format"),
    banco: Session = Depends(obter_banco),
):
    payload = load_public_verification_payload(
        banco,
        codigo_hash=codigo_hash,
        base_url=f"{request.url.scheme}://{request.url.netloc}",
    )
    if payload is None:
        raise HTTPException(status_code=404, detail="Hash publico nao encontrado.")

    wants_json = str(formato or "").strip().lower() == "json" or "application/json" in str(
        request.headers.get("accept") or ""
    ).lower()
    if wants_json:
        return JSONResponse(content=jsonable_encoder(payload))
    return HTMLResponse(_renderizar_html_verificacao_publica(payload))


async def obter_mensagens_laudo(
    laudo_id: int,
    request: Request,
    cursor: Annotated[InteiroOpcionalNullish, Query()] = None,
    limite: int = Query(default=80, ge=20, le=200),
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    return await obter_mensagens_laudo_payload(
        laudo_id=laudo_id,
        request=request,
        cursor=int(cursor) if cursor is not None else None,
        limite=limite,
        usuario=usuario,
        banco=banco,
    )


async def rota_pdf(
    request: Request,
    dados: DadosPDF,
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    with observe_backend_hotspot(
        "inspector_pdf_generation",
        request=request,
        surface="inspetor",
        tenant_id=getattr(usuario, "empresa_id", None),
        user_id=getattr(usuario, "id", None),
        route_path="/app/api/gerar_pdf",
        method="POST",
    ) as hotspot:
        exigir_csrf(request)

        nome_arquivo = f"Laudo_Tarielia_{uuid.uuid4().hex[:12]}.pdf"
        caminho_pdf = os.path.join(tempfile.gettempdir(), nome_arquivo)

        laudo_id_candidato = dados.laudo_id or laudo_id_sessao(request)
        laudo: Laudo | None = None
        if laudo_id_candidato:
            laudo = obter_laudo_do_inspetor(banco, int(laudo_id_candidato), usuario)
            hotspot.laudo_id = int(laudo.id)
            hotspot.case_id = int(laudo.id)

        dados_formulario_laudo = (
            laudo.dados_formulario if laudo and isinstance(laudo.dados_formulario, dict) else {}
        )
        resolved_template = None
        if laudo is not None:
            resolved_template = resolve_pdf_template_for_laudo(
                banco=banco,
                empresa_id=int(usuario.empresa_id),
                laudo=laudo,
                allow_runtime_fallback=bool(dados_formulario_laudo),
                allow_current_binding_lookup=True,
            )
        public_verification = (
            build_public_verification_payload(
                laudo=laudo,
                base_url=f"{request.url.scheme}://{request.url.netloc}",
            )
            if laudo is not None
            else None
        )

        try:
            if resolved_template is not None:
                dados_formulario_template = (
                    build_catalog_pdf_payload(
                        laudo=laudo,
                        template_ref=resolved_template,
                        diagnostico=str(dados.diagnostico or ""),
                        inspetor=str(dados.inspetor or ""),
                        empresa=str(dados.empresa or ""),
                        data=str(dados.data or ""),
                        render_mode=RENDER_MODE_CLIENT_PDF_FILLED,
                    )
                    if resolved_template.family_key
                    else dados_formulario_laudo
                )
                hotspot.detail.update(
                    {
                        "template_id": (
                            int(resolved_template.template_id)
                            if resolved_template.template_id is not None
                            else None
                        ),
                        "template_source_kind": str(resolved_template.source_kind or ""),
                    }
                )
                try:
                    modo_editor = normalizar_modo_editor(resolved_template.modo_editor)
                    hotspot.detail["editor_mode"] = modo_editor
                    promoted_from_legacy = (
                        modo_editor != MODO_EDITOR_RICO
                        and should_use_rich_runtime_preview_for_pdf_template(
                            template_ref=resolved_template,
                            payload=dados_formulario_template or {},
                            render_mode=RENDER_MODE_CLIENT_PDF_FILLED,
                        )
                    )
                    if modo_editor == MODO_EDITOR_RICO or promoted_from_legacy:
                        import app.domains.chat.chat as chat_facade

                        runtime_assets = resolve_runtime_assets_for_pdf_template(
                            template_ref=resolved_template,
                            payload=dados_formulario_template or {},
                        )
                        runtime_document = materialize_runtime_document_editor_json(
                            template_ref=resolved_template,
                            payload=dados_formulario_template or {},
                            render_mode=RENDER_MODE_CLIENT_PDF_FILLED,
                        )
                        pdf_template = await chat_facade.gerar_pdf_editor_rico_bytes(
                            documento_editor_json=runtime_document or documento_editor_padrao(),
                            estilo_json=materialize_runtime_style_json_for_pdf_template(
                                template_ref=resolved_template,
                                payload=dados_formulario_template or {},
                                render_mode=RENDER_MODE_CLIENT_PDF_FILLED,
                            )
                            or estilo_editor_padrao(),
                            assets_json=runtime_assets,
                            dados_formulario=dados_formulario_template or {},
                            public_verification=public_verification,
                        )
                        if resolved_template.source_kind == "catalog_canonical_seed":
                            pipeline_name = "catalog_canonical_seed_preview"
                        else:
                            pipeline_name = "editor_rico_preview"
                        if promoted_from_legacy:
                            hotspot.detail["runtime_render_strategy"] = "legacy_promoted_to_editor_rico"
                    else:
                        if not has_viable_legacy_preview_overlay_for_pdf_template(
                            template_ref=resolved_template,
                        ):
                            raise RuntimeError("Template legado sem overlay viavel para preview.")
                        pdf_template = gerar_preview_pdf_template(
                            caminho_pdf_base=resolved_template.arquivo_pdf_base,
                            mapeamento_campos=resolve_runtime_field_mapping_for_pdf_template(
                                template_ref=resolved_template,
                            ),
                            dados_formulario=dados_formulario_template or {},
                        )
                        pipeline_name = "legacy_pdf_preview"
                    with open(caminho_pdf, "wb") as arquivo_saida:
                        arquivo_saida.write(pdf_template)
                    _registrar_soft_gate_documental_preview_pdf(
                        request=request,
                        banco=banco,
                        usuario=usuario,
                        laudo=laudo,
                        dados=dados,
                        legacy_pipeline_name=pipeline_name,
                        legacy_compatibility_state=(
                            "legacy_template_promoted_to_editor_rico"
                            if promoted_from_legacy
                            else None
                        ),
                    )
                    hotspot.outcome = pipeline_name
                    hotspot.response_status_code = 200
                    return FileResponse(
                        path=caminho_pdf,
                        filename=f"Laudo_{resolved_template.codigo_template}_v{resolved_template.versao}.pdf",
                        media_type="application/pdf",
                        background=BackgroundTask(safe_remove_file, caminho_pdf),
                    )
                except Exception:
                    logger.warning(
                        (
                            "Falha ao gerar PDF pelo template resolvido. Aplicando fallback legacy. "
                            "| empresa_id=%s | usuario_id=%s | laudo_id=%s | template_id=%s | source=%s"
                        ),
                        usuario.empresa_id,
                        usuario.id,
                        laudo.id if laudo else None,
                        resolved_template.template_id,
                        resolved_template.source_kind,
                        exc_info=True,
                    )
                    _registrar_soft_gate_documental_preview_pdf(
                        request=request,
                        banco=banco,
                        usuario=usuario,
                        laudo=laudo,
                        dados=dados,
                        legacy_pipeline_name="legacy_pdf_fallback",
                        legacy_compatibility_state=(
                            "catalog_canonical_seed_fallback"
                            if resolved_template.source_kind == "catalog_canonical_seed"
                            else "template_generation_fallback"
                        ),
                    )

            GeradorLaudos.gerar_pdf_inspecao(
                dados=dados.model_dump(),
                caminho_saida=caminho_pdf,
                empresa_id=usuario.empresa_id,
                usuario_id=usuario.id,
                codigo_hash_override=str(getattr(laudo, "codigo_hash", "") or "") or None,
                public_verification=public_verification,
            )
            if not hasattr(request.state, "v2_document_soft_gate_trace"):
                _registrar_soft_gate_documental_preview_pdf(
                    request=request,
                    banco=banco,
                    usuario=usuario,
                    laudo=laudo,
                    dados=dados,
                    legacy_pipeline_name=(
                        "legacy_pdf_fallback" if resolved_template is not None else "legacy_pdf_preview"
                    ),
                )

            hotspot.outcome = "legacy_pdf_fallback" if resolved_template is not None else "legacy_pdf_preview"
            hotspot.response_status_code = 200
            return FileResponse(
                path=caminho_pdf,
                filename="laudo_art_wf.pdf",
                media_type="application/pdf",
                background=BackgroundTask(safe_remove_file, caminho_pdf),
            )
        except Exception:
            logger.error("Falha ao gerar PDF.", exc_info=True)
            safe_remove_file(caminho_pdf)
            hotspot.status = "error"
            hotspot.error_class = "infra"
            hotspot.error_code = "pdf_generation_failed"
            hotspot.outcome = "error_json"
            hotspot.response_status_code = 500
            return JSONResponse(
                status_code=500,
                content={"erro": "Falha ao gerar o PDF."},
            )


async def rota_upload_doc(
    request: Request,
    arquivo: UploadFile = File(...),
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    exigir_csrf(request)
    payload, status_code = await processar_upload_documento(
        arquivo=arquivo,
        usuario=usuario,
        banco=banco,
    )
    return resposta_json_ok(payload, status_code=status_code)


async def rota_feedback(
    request: Request,
    dados: DadosFeedback,
    usuario: Usuario = Depends(exigir_inspetor),
):
    exigir_csrf(request)

    logger.info(
        "Feedback recebido | tipo=%s | usuario_id=%s | trecho='%.80s'",
        dados.tipo,
        usuario.id,
        dados.trecho,
    )

    return resposta_json_ok({"ok": True})


roteador_chat_aux.add_api_route(
    "/api/laudo/{laudo_id}/mensagens",
    obter_mensagens_laudo,
    methods=["GET"],
    responses=RESPOSTA_LAUDO_NAO_ENCONTRADO,
)
roteador_chat_aux.add_api_route(
    "/api/gerar_pdf",
    rota_pdf,
    methods=["POST"],
    responses={
        200: {
            "description": "PDF gerado para o laudo.",
            "content": {"application/pdf": {}},
        },
        500: {"description": "Falha ao gerar o PDF."},
    },
)
roteador_chat_aux.add_api_route(
    "/api/upload_doc",
    rota_upload_doc,
    methods=["POST"],
    responses={
        400: {"description": "Multipart inválido ou corpo malformado."},
        413: {"description": "Arquivo muito grande."},
        415: {"description": "Tipo de arquivo não suportado."},
        422: {"description": "Não foi possível extrair texto do documento."},
        501: {"description": "Parser do tipo de documento indisponível."},
    },
)
roteador_chat_aux.add_api_route("/api/feedback", rota_feedback, methods=["POST"])
roteador_chat_aux.add_api_route(
    "/public/laudo/verificar/{codigo_hash}",
    rota_verificacao_publica_laudo,
    methods=["GET"],
    responses={
        200: {"description": "Hash publico verificado."},
        404: {"description": "Hash nao encontrado."},
    },
)

registrar_feedback = rota_feedback


__all__ = [
    "RESPOSTA_LAUDO_NAO_ENCONTRADO",
    "obter_mensagens_laudo",
    "registrar_feedback",
    "rota_feedback",
    "rota_pdf",
    "rota_upload_doc",
    "rota_verificacao_publica_laudo",
    "roteador_chat_aux",
]
