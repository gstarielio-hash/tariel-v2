"""Runtime e constantes do chat inspetor."""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.shared.database import ModoResposta
from app.shared.db.contracts import EntryModeEffective, EntryModePreference, EntryModeReason

LIMITE_MSG_CHARS = 8_000
LIMITE_HISTORICO = 20

LIMITE_DOC_BYTES = 15 * 1024 * 1024
LIMITE_DOC_CHARS = 40_000
LIMITE_PARECER = 4_000
LIMITE_FEEDBACK = 500

TIMEOUT_FILA_STREAM_SEGUNDOS = 90.0
TIMEOUT_KEEPALIVE_SSE_SEGUNDOS = 25.0

PREFIXO_METADATA = "__METADATA__:"
PREFIXO_CITACOES = "__CITACOES__:"
PREFIXO_MODO_HUMANO = "__MODO_HUMANO__:"

MODO_DETALHADO = ModoResposta.DETALHADO.value
MODO_CURTO = ModoResposta.CURTO.value
MODO_DEEP = ModoResposta.DEEP_RESEARCH.value

ENTRY_MODE_CHAT_FIRST = EntryModeEffective.CHAT_FIRST.value
ENTRY_MODE_EVIDENCE_FIRST = EntryModeEffective.EVIDENCE_FIRST.value
ENTRY_MODE_AUTO_RECOMMENDED = EntryModePreference.AUTO_RECOMMENDED.value

ENTRY_MODE_REASON_HARD_SAFETY_RULE = EntryModeReason.HARD_SAFETY_RULE.value
ENTRY_MODE_REASON_FAMILY_REQUIRED_MODE = EntryModeReason.FAMILY_REQUIRED_MODE.value
ENTRY_MODE_REASON_TENANT_POLICY = EntryModeReason.TENANT_POLICY.value
ENTRY_MODE_REASON_ROLE_POLICY = EntryModeReason.ROLE_POLICY.value
ENTRY_MODE_REASON_USER_PREFERENCE = EntryModeReason.USER_PREFERENCE.value
ENTRY_MODE_REASON_LAST_CASE_MODE = EntryModeReason.LAST_CASE_MODE.value
ENTRY_MODE_REASON_AUTO_RECOMMENDED = EntryModeReason.AUTO_RECOMMENDED.value
ENTRY_MODE_REASON_DEFAULT_PRODUCT_FALLBACK = EntryModeReason.DEFAULT_PRODUCT_FALLBACK.value
ENTRY_MODE_REASON_EXISTING_CASE_STATE = EntryModeReason.EXISTING_CASE_STATE.value

MIME_DOC_PERMITIDOS = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

try:
    import pypdf as leitor_pdf

    TEM_PYPDF = True
except ImportError:
    TEM_PYPDF = False
    leitor_pdf = None

try:
    import docx as leitor_docx

    TEM_DOCX = True
except ImportError:
    TEM_DOCX = False
    leitor_docx = None

executor_stream = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tariel_ia")


@dataclass(frozen=True, slots=True)
class EntryModeDecision:
    preference: str
    effective: str
    reason: str


def normalizar_entry_mode_preference(
    valor: Any,
    *,
    default: str = ENTRY_MODE_AUTO_RECOMMENDED,
) -> str:
    if valor in (None, ""):
        return EntryModePreference.normalizar(default)
    return EntryModePreference.normalizar(valor)


def normalizar_entry_mode_effective(
    valor: Any,
    *,
    default: str = ENTRY_MODE_CHAT_FIRST,
) -> str:
    if valor in (None, ""):
        return EntryModeEffective.normalizar(default)
    return EntryModeEffective.normalizar(valor)


def normalizar_entry_mode_reason(
    valor: Any,
    *,
    default: str = ENTRY_MODE_REASON_DEFAULT_PRODUCT_FALLBACK,
) -> str:
    if valor in (None, ""):
        return EntryModeReason.normalizar(default)
    return EntryModeReason.normalizar(valor)


def resolver_modo_entrada_caso(
    *,
    requested_preference: Any = None,
    existing_preference: Any = None,
    hard_safety_mode: Any = None,
    family_required_mode: Any = None,
    tenant_policy_mode: Any = None,
    role_policy_mode: Any = None,
    last_case_mode: Any = None,
    auto_recommended_mode: Any = None,
    fallback_mode: Any = ENTRY_MODE_CHAT_FIRST,
) -> EntryModeDecision:
    preference_source = requested_preference if requested_preference not in (None, "") else existing_preference
    preference = normalizar_entry_mode_preference(preference_source)

    regras_em_ordem = (
        (EntryModeReason.HARD_SAFETY_RULE.value, hard_safety_mode),
        (EntryModeReason.FAMILY_REQUIRED_MODE.value, family_required_mode),
        (EntryModeReason.TENANT_POLICY.value, tenant_policy_mode),
        (EntryModeReason.ROLE_POLICY.value, role_policy_mode),
    )
    for reason, candidate in regras_em_ordem:
        if candidate in (None, ""):
            continue
        return EntryModeDecision(
            preference=preference,
            effective=normalizar_entry_mode_effective(candidate),
            reason=reason,
        )

    if preference in {ENTRY_MODE_CHAT_FIRST, ENTRY_MODE_EVIDENCE_FIRST}:
        return EntryModeDecision(
            preference=preference,
            effective=preference,
            reason=EntryModeReason.USER_PREFERENCE.value,
        )

    if last_case_mode not in (None, ""):
        return EntryModeDecision(
            preference=preference,
            effective=normalizar_entry_mode_effective(last_case_mode),
            reason=EntryModeReason.LAST_CASE_MODE.value,
        )

    if auto_recommended_mode not in (None, ""):
        return EntryModeDecision(
            preference=preference,
            effective=normalizar_entry_mode_effective(auto_recommended_mode),
            reason=EntryModeReason.AUTO_RECOMMENDED.value,
        )

    return EntryModeDecision(
        preference=preference,
        effective=normalizar_entry_mode_effective(fallback_mode),
        reason=EntryModeReason.DEFAULT_PRODUCT_FALLBACK.value,
    )


__all__ = [
    "ENTRY_MODE_AUTO_RECOMMENDED",
    "ENTRY_MODE_CHAT_FIRST",
    "ENTRY_MODE_EVIDENCE_FIRST",
    "ENTRY_MODE_REASON_AUTO_RECOMMENDED",
    "ENTRY_MODE_REASON_DEFAULT_PRODUCT_FALLBACK",
    "ENTRY_MODE_REASON_EXISTING_CASE_STATE",
    "ENTRY_MODE_REASON_FAMILY_REQUIRED_MODE",
    "ENTRY_MODE_REASON_HARD_SAFETY_RULE",
    "ENTRY_MODE_REASON_LAST_CASE_MODE",
    "ENTRY_MODE_REASON_ROLE_POLICY",
    "ENTRY_MODE_REASON_TENANT_POLICY",
    "ENTRY_MODE_REASON_USER_PREFERENCE",
    "EntryModeDecision",
    "LIMITE_MSG_CHARS",
    "LIMITE_HISTORICO",
    "LIMITE_DOC_BYTES",
    "LIMITE_DOC_CHARS",
    "LIMITE_PARECER",
    "LIMITE_FEEDBACK",
    "TIMEOUT_FILA_STREAM_SEGUNDOS",
    "TIMEOUT_KEEPALIVE_SSE_SEGUNDOS",
    "PREFIXO_METADATA",
    "PREFIXO_CITACOES",
    "PREFIXO_MODO_HUMANO",
    "MODO_DETALHADO",
    "MODO_CURTO",
    "MODO_DEEP",
    "MIME_DOC_PERMITIDOS",
    "TEM_PYPDF",
    "leitor_pdf",
    "TEM_DOCX",
    "leitor_docx",
    "executor_stream",
    "normalizar_entry_mode_effective",
    "normalizar_entry_mode_preference",
    "normalizar_entry_mode_reason",
    "resolver_modo_entrada_caso",
]
