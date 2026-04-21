"""Helpers para tarefas operacionais estruturadas no canal Mesa."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable

_COVERAGE_RETURN_TASK_KIND = "coverage_return_request"
_TASK_REPLY_MODES = {
    "any",
    "text_required",
    "text_or_attachment",
    "attachment_required",
    "image_required",
    "document_required",
}


def _texto_curto(valor: Any, *, limite: int = 280) -> str | None:
    texto = " ".join(str(valor or "").strip().split())
    if not texto:
        return None
    return texto[:limite]


def _lista_textos(valores: Iterable[Any] | None, *, limite_item: int = 120) -> list[str]:
    vistos: set[str] = set()
    resultado: list[str] = []
    for valor in list(valores or []):
        texto = _texto_curto(valor, limite=limite_item)
        if not texto:
            continue
        chave = texto.lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(texto)
    return resultado


def _booleano(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor or "").strip().lower() in {"1", "true", "sim", "yes"}


def build_coverage_return_block_key(
    evidence_key: str | None,
    *,
    title: str | None = None,
) -> str:
    base = _texto_curto(evidence_key, limite=96) or _texto_curto(title, limite=72) or "coverage_item"
    normalizado = re.sub(r"[^a-z0-9:_-]+", "_", str(base).lower())
    normalizado = re.sub(r"_+", "_", normalizado).strip("_") or "coverage_item"
    prefixo = "coverage_return:"
    candidato = f"{prefixo}{normalizado}"
    if len(candidato) <= 120:
        return candidato
    hash_curto = hashlib.sha1(candidato.encode("utf-8")).hexdigest()[:10]
    limite_base = max(8, 120 - len(prefixo) - len(hash_curto) - 1)
    return f"{prefixo}{normalizado[:limite_base]}:{hash_curto}"


def _reply_mode_label(reply_mode: str) -> str:
    mapa = {
        "any": "resposta livre",
        "text_required": "texto obrigatório",
        "text_or_attachment": "texto ou anexo",
        "attachment_required": "anexo obrigatório",
        "image_required": "imagem obrigatória",
        "document_required": "documento obrigatório",
    }
    return mapa.get(str(reply_mode or "").strip().lower(), "resposta livre")


def infer_coverage_reply_mode(
    *,
    evidence_key: str | None,
    kind: str | None,
    title: str | None,
    failure_reasons: Iterable[Any] | None = None,
) -> str:
    evidence_key_text = str(evidence_key or "").strip().lower()
    tokens = " ".join(
        filter(
            None,
            [
                str(kind or "").strip().lower(),
                str(title or "").strip().lower(),
                " ".join(str(item or "").strip().lower() for item in list(failure_reasons or [])),
            ],
        )
    )
    if evidence_key_text.startswith("slot:") or any(token in tokens for token in ("image", "imagem", "foto", "placa", "tag")):
        return "image_required"
    if any(token in tokens for token in ("document", "documento", "pdf", "certificado", "certidao", "art", "rrt")):
        return "document_required"
    if evidence_key_text.startswith("gate:"):
        return "attachment_required"
    return "text_or_attachment"


def default_required_action_for_reply_mode(
    reply_mode: str,
    *,
    title: str | None = None,
) -> str:
    alvo = _texto_curto(title, limite=120) or "este item"
    modo = str(reply_mode or "").strip().lower()
    if modo == "image_required":
        return f"Reenviar foto nova e nitida para {alvo}."
    if modo == "document_required":
        return f"Anexar documento valido para {alvo}."
    if modo == "attachment_required":
        return f"Anexar evidencia valida para {alvo}."
    if modo == "text_required":
        return f"Responder em texto objetivo corrigindo {alvo}."
    return f"Responder com a correcao ou anexar a evidencia faltante para {alvo}."


def build_coverage_return_request_metadata(
    *,
    evidence_key: str,
    title: str,
    kind: str,
    required: bool = False,
    source_status: str | None = None,
    operational_status: str | None = None,
    mesa_status: str | None = None,
    component_type: str | None = None,
    view_angle: str | None = None,
    severity: str | None = None,
    summary: str | None = None,
    required_action: str | None = None,
    failure_reasons: Iterable[Any] | None = None,
    expected_reply_mode: str | None = None,
    block_key: str | None = None,
) -> dict[str, Any]:
    titulo = _texto_curto(title, limite=180) or "Item de cobertura"
    failure_reasons_list = _lista_textos(failure_reasons)
    reply_mode = str(expected_reply_mode or "").strip().lower()
    if reply_mode not in _TASK_REPLY_MODES:
        reply_mode = infer_coverage_reply_mode(
            evidence_key=evidence_key,
            kind=kind,
            title=titulo,
            failure_reasons=failure_reasons_list,
        )
    resumo = _texto_curto(summary, limite=280)
    if not resumo:
        if failure_reasons_list:
            resumo = f"Alertas operacionais: {', '.join(failure_reasons_list[:3])}."
        elif _booleano(required):
            resumo = "Item obrigatorio sem evidencia suficiente para aprovacao."
        else:
            resumo = "Item precisa de ajuste operacional antes da aprovacao."
    acao_esperada = _texto_curto(required_action, limite=280) or default_required_action_for_reply_mode(
        reply_mode,
        title=titulo,
    )
    return {
        "task_kind": _COVERAGE_RETURN_TASK_KIND,
        "evidence_key": _texto_curto(evidence_key, limite=160),
        "block_key": _texto_curto(block_key, limite=120)
        or build_coverage_return_block_key(evidence_key, title=titulo),
        "title": titulo,
        "kind": _texto_curto(kind, limite=40) or "coverage_item",
        "required": bool(required),
        "source_status": _texto_curto(source_status, limite=32),
        "operational_status": _texto_curto(operational_status, limite=24),
        "mesa_status": _texto_curto(mesa_status, limite=24),
        "component_type": _texto_curto(component_type, limite=80),
        "view_angle": _texto_curto(view_angle, limite=80),
        "severity": _texto_curto(severity, limite=16) or "warning",
        "summary": resumo,
        "required_action": acao_esperada,
        "failure_reasons": failure_reasons_list,
        "expected_reply_mode": reply_mode,
        "expected_reply_mode_label": _reply_mode_label(reply_mode),
    }


def build_coverage_return_request_text(metadata: dict[str, Any]) -> str:
    context = extract_operational_context(metadata)
    if context is None:
        return "Refazer evidencia solicitado pela Mesa."

    linhas = [f"⚠️ Refazer evidencia: {context['title']}"]
    if context.get("summary"):
        linhas.append(str(context["summary"]))
    if context.get("required_action"):
        linhas.append(f"Acao esperada: {context['required_action']}")

    contexto_visual = []
    if context.get("component_type"):
        contexto_visual.append(f"Componente: {context['component_type']}")
    if context.get("view_angle"):
        contexto_visual.append(f"Angulo: {context['view_angle']}")
    if contexto_visual:
        linhas.append(" | ".join(contexto_visual))

    if context.get("failure_reasons"):
        linhas.append(f"Motivos: {', '.join(context['failure_reasons'])}")

    linhas.append(f"Resposta esperada: {context['expected_reply_mode_label']}.")
    return "\n".join(str(item).strip() for item in linhas if str(item or "").strip())[:4000]


def extract_operational_context(message_or_metadata: Any) -> dict[str, Any] | None:
    metadata = message_or_metadata
    if not isinstance(metadata, dict):
        metadata = getattr(message_or_metadata, "metadata_json", None)
    if not isinstance(metadata, dict):
        return None
    task_kind = _texto_curto(metadata.get("task_kind"), limite=40)
    if task_kind != _COVERAGE_RETURN_TASK_KIND:
        return None

    reply_mode = str(metadata.get("expected_reply_mode") or "").strip().lower()
    if reply_mode not in _TASK_REPLY_MODES:
        reply_mode = "any"

    contexto = {
        "task_kind": _COVERAGE_RETURN_TASK_KIND,
        "evidence_key": _texto_curto(metadata.get("evidence_key"), limite=160),
        "block_key": _texto_curto(metadata.get("block_key"), limite=120),
        "title": _texto_curto(metadata.get("title"), limite=180) or "Item de cobertura",
        "kind": _texto_curto(metadata.get("kind"), limite=40) or "coverage_item",
        "required": _booleano(metadata.get("required")),
        "source_status": _texto_curto(metadata.get("source_status"), limite=32),
        "operational_status": _texto_curto(metadata.get("operational_status"), limite=24),
        "mesa_status": _texto_curto(metadata.get("mesa_status"), limite=24),
        "component_type": _texto_curto(metadata.get("component_type"), limite=80),
        "view_angle": _texto_curto(metadata.get("view_angle"), limite=80),
        "severity": _texto_curto(metadata.get("severity"), limite=16) or "warning",
        "summary": _texto_curto(metadata.get("summary"), limite=280),
        "required_action": _texto_curto(metadata.get("required_action"), limite=280),
        "failure_reasons": _lista_textos(metadata.get("failure_reasons")),
        "expected_reply_mode": reply_mode,
        "expected_reply_mode_label": _reply_mode_label(reply_mode),
    }
    if not contexto["evidence_key"] and not contexto["block_key"]:
        return None
    return contexto


def is_coverage_return_request(message_or_metadata: Any) -> bool:
    return extract_operational_context(message_or_metadata) is not None


def inspector_response_matches_operational_task(
    *,
    operational_context: dict[str, Any] | None,
    text: str | None,
    attachments: Iterable[Any] | None,
) -> bool:
    contexto = extract_operational_context(operational_context)
    if contexto is None:
        return False

    texto_limpo = " ".join(str(text or "").strip().split())
    tem_texto = bool(texto_limpo)
    categorias = {
        str(
            getattr(anexo, "categoria", None)
            if not isinstance(anexo, dict)
            else anexo.get("categoria")
            or ""
        ).strip().lower()
        for anexo in list(attachments or [])
    }
    tem_anexo = bool(categorias)
    modo = str(contexto.get("expected_reply_mode") or "any").strip().lower()

    if modo == "image_required":
        return "imagem" in categorias
    if modo == "document_required":
        return "documento" in categorias
    if modo == "attachment_required":
        return tem_anexo
    if modo == "text_required":
        return tem_texto
    if modo == "text_or_attachment":
        return tem_texto or tem_anexo
    return tem_texto or tem_anexo


__all__ = [
    "build_coverage_return_block_key",
    "build_coverage_return_request_metadata",
    "build_coverage_return_request_text",
    "default_required_action_for_reply_mode",
    "extract_operational_context",
    "infer_coverage_reply_mode",
    "inspector_response_matches_operational_task",
    "is_coverage_return_request",
]
