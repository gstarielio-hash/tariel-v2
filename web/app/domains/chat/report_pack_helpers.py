"""Helpers do draft incremental de report packs semanticos."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.domains.chat.normalization import (
    normalizar_tipo_template,
    resolver_familia_padrao_template,
)
from app.domains.chat.report_pack_pre_laudo import (
    _attach_pre_laudo_views,
    _filename_from_reference,
    _normalize_family_key,
    _pick_first_nonempty_text,
    build_pre_laudo_prompt_context,
    build_pre_laudo_summary,
    obter_pre_laudo_outline_report_pack,
)
from app.domains.chat.report_pack_runtime_builders import (
    _build_catalog_backed_report_pack_draft,
    _build_cbmgo_report_pack_draft,
    _looks_like_catalog_structured_payload,
    _normalize_guided_draft,
)
from app.domains.chat.report_pack_semantic_builders import (
    _NR10_PRONTUARIO_FAMILY,
    _NR13_CALDEIRA_FAMILY,
    _NR13_VASO_PRESSAO_FAMILY,
    _NR20_PRONTUARIO_FAMILY,
    _build_nr10_prontuario_report_pack_draft,
    _build_nr13_caldeira_report_pack_draft,
    _build_nr13_vaso_pressao_report_pack_draft,
    _build_nr20_prontuario_report_pack_draft,
    _build_nr35_anchor_report_pack_draft,
    _build_nr35_report_pack_draft,
    build_unmodeled_report_pack_draft,
)
from app.domains.chat.templates_ai import obter_schema_template_ia
from app.shared.database import AprendizadoVisualIa, Laudo, MensagemLaudo, TipoMensagem


def _build_visual_attachment_by_message_id(
    *,
    banco: Session,
    laudo_id: int,
) -> dict[int, dict[str, Any]]:
    visual_rows = (
        banco.query(AprendizadoVisualIa)
        .filter(
            AprendizadoVisualIa.laudo_id == int(laudo_id),
            AprendizadoVisualIa.mensagem_referencia_id.isnot(None),
            AprendizadoVisualIa.imagem_url.isnot(None),
        )
        .order_by(AprendizadoVisualIa.criado_em.desc(), AprendizadoVisualIa.id.desc())
        .all()
    )
    by_message_id: dict[int, dict[str, Any]] = {}
    for item in visual_rows:
        message_id = int(getattr(item, "mensagem_referencia_id", 0) or 0)
        if message_id <= 0 or message_id in by_message_id:
            continue
        original_name = _pick_first_nonempty_text(
            getattr(item, "imagem_nome_original", None),
            _filename_from_reference(getattr(item, "caminho_arquivo", None)),
            _filename_from_reference(getattr(item, "imagem_url", None)),
            limit=160,
        )
        by_message_id[message_id] = {
            "imagem_url": _pick_first_nonempty_text(getattr(item, "imagem_url", None), limit=240) or None,
            "imagem_nome_original": original_name or None,
            "caminho_arquivo": _pick_first_nonempty_text(getattr(item, "caminho_arquivo", None), limit=240) or None,
            "reference": _pick_first_nonempty_text(
                original_name,
                _filename_from_reference(getattr(item, "caminho_arquivo", None)),
                _filename_from_reference(getattr(item, "imagem_url", None)),
                limit=180,
            )
            or None,
        }
    return by_message_id


def _resolved_catalog_family_key_for_laudo(laudo: Laudo, *, template_key: str) -> str:
    return _normalize_family_key(
        getattr(laudo, "catalog_family_key", None)
        or resolver_familia_padrao_template(template_key).get("family_key")
        or getattr(laudo, "tipo_template", None)
    )


def build_report_pack_draft_for_laudo(
    *,
    banco: Session,
    laudo: Laudo,
) -> dict[str, Any] | None:
    template_key = normalizar_tipo_template(getattr(laudo, "tipo_template", "padrao"))
    resolved_family_key = _resolved_catalog_family_key_for_laudo(
        laudo,
        template_key=template_key,
    )
    user_messages = (
        banco.query(MensagemLaudo)
        .filter(
            MensagemLaudo.laudo_id == int(laudo.id),
            MensagemLaudo.tipo.in_((TipoMensagem.USER.value, TipoMensagem.HUMANO_INSP.value)),
        )
        .order_by(MensagemLaudo.criado_em.asc())
        .all()
    )
    visual_attachment_by_message_id = _build_visual_attachment_by_message_id(
        banco=banco,
        laudo_id=int(laudo.id),
    )
    visual_message_ids = set(visual_attachment_by_message_id)

    if template_key == "nr35_linha_vida":
        return _attach_pre_laudo_views(
            draft=_build_nr35_report_pack_draft(
                laudo=laudo,
                user_messages=user_messages,
                visual_message_ids=visual_message_ids,
                visual_attachment_by_message_id=visual_attachment_by_message_id,
            ),
            laudo=laudo,
        )
    if template_key == "nr35_ponto_ancoragem":
        return _attach_pre_laudo_views(
            draft=_build_nr35_anchor_report_pack_draft(
                laudo=laudo,
                user_messages=user_messages,
                visual_message_ids=visual_message_ids,
                visual_attachment_by_message_id=visual_attachment_by_message_id,
            ),
            laudo=laudo,
        )
    if template_key == "nr13" and resolved_family_key == _NR13_VASO_PRESSAO_FAMILY:
        return _attach_pre_laudo_views(
            draft=_build_nr13_vaso_pressao_report_pack_draft(
                laudo=laudo,
                user_messages=user_messages,
                visual_message_ids=visual_message_ids,
                visual_attachment_by_message_id=visual_attachment_by_message_id,
            ),
            laudo=laudo,
        )
    if template_key == "nr13" and resolved_family_key == _NR13_CALDEIRA_FAMILY:
        return _attach_pre_laudo_views(
            draft=_build_nr13_caldeira_report_pack_draft(
                laudo=laudo,
                user_messages=user_messages,
                visual_message_ids=visual_message_ids,
                visual_attachment_by_message_id=visual_attachment_by_message_id,
            ),
            laudo=laudo,
        )
    if resolved_family_key == _NR20_PRONTUARIO_FAMILY:
        return _attach_pre_laudo_views(
            draft=_build_nr20_prontuario_report_pack_draft(
                laudo=laudo,
                user_messages=user_messages,
                visual_message_ids=visual_message_ids,
                visual_attachment_by_message_id=visual_attachment_by_message_id,
            ),
            laudo=laudo,
        )
    if resolved_family_key == _NR10_PRONTUARIO_FAMILY:
        return _attach_pre_laudo_views(
            draft=_build_nr10_prontuario_report_pack_draft(
                laudo=laudo,
                user_messages=user_messages,
                visual_message_ids=visual_message_ids,
                visual_attachment_by_message_id=visual_attachment_by_message_id,
            ),
            laudo=laudo,
        )
    if template_key == "cbmgo":
        return _attach_pre_laudo_views(
            draft=_build_cbmgo_report_pack_draft(
                laudo=laudo,
                guided_draft=_normalize_guided_draft(
                    getattr(laudo, "guided_inspection_draft_json", None)
                ),
                user_messages=user_messages,
                visual_message_ids=visual_message_ids,
                visual_attachment_by_message_id=visual_attachment_by_message_id,
            ),
            laudo=laudo,
        )
    if (
        _looks_like_catalog_structured_payload(laudo)
        or bool(resolver_familia_padrao_template(template_key).get("family_key"))
    ):
        return _attach_pre_laudo_views(
            draft=_build_catalog_backed_report_pack_draft(
                laudo=laudo,
                user_messages=user_messages,
                visual_message_ids=visual_message_ids,
                visual_attachment_by_message_id=visual_attachment_by_message_id,
            ),
            laudo=laudo,
        )

    return _attach_pre_laudo_views(
        draft=build_unmodeled_report_pack_draft(
            laudo=laudo,
            template_key=template_key,
            user_messages=user_messages,
            visual_message_ids=visual_message_ids,
        ),
        laudo=laudo,
    )


def atualizar_report_pack_draft_laudo(
    *,
    banco: Session,
    laudo: Laudo,
) -> dict[str, Any] | None:
    payload = build_report_pack_draft_for_laudo(
        banco=banco,
        laudo=laudo,
    )
    laudo.report_pack_draft_json = payload
    return payload


def obter_report_pack_draft_laudo(laudo: Laudo | None) -> dict[str, Any] | None:
    if laudo is None:
        return None
    payload = getattr(laudo, "report_pack_draft_json", None)
    return payload if isinstance(payload, dict) else None


def obter_dados_formulario_candidate_report_pack(laudo: Laudo | None) -> dict[str, Any] | None:
    draft = obter_report_pack_draft_laudo(laudo)
    if not draft:
        return None
    candidate = draft.get("structured_data_candidate")
    if not isinstance(candidate, dict):
        return None
    schema = obter_schema_template_ia(getattr(laudo, "tipo_template", None))
    if schema is None:
        return None
    try:
        validated = schema.model_validate(candidate)
    except ValidationError:
        return None
    return validated.model_dump(mode="python")


def atualizar_final_validation_mode_report_pack(
    *,
    laudo: Laudo,
    final_validation_mode: str,
) -> dict[str, Any] | None:
    draft = obter_report_pack_draft_laudo(laudo)
    if draft is None:
        return None
    quality_gates = dict(draft.get("quality_gates") or {})
    quality_gates["final_validation_mode"] = str(final_validation_mode or "").strip() or "mesa_required"
    draft["quality_gates"] = quality_gates
    laudo.report_pack_draft_json = draft
    return draft


__all__ = [
    "build_pre_laudo_prompt_context",
    "build_pre_laudo_summary",
    "atualizar_final_validation_mode_report_pack",
    "atualizar_report_pack_draft_laudo",
    "build_report_pack_draft_for_laudo",
    "obter_dados_formulario_candidate_report_pack",
    "obter_pre_laudo_outline_report_pack",
    "obter_report_pack_draft_laudo",
]
