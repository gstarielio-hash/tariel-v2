"""Contratos e enums compartilhados da camada de persistência."""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Any


def _normalizar_texto_chave(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    texto = (
        texto.replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return re.sub(r"[\s\-_\\/]+", "_", texto)


class NivelAcesso(enum.IntEnum):
    INSPETOR = 1
    REVISOR = 50
    ADMIN_CLIENTE = 80
    DIRETORIA = 99

    @classmethod
    def normalizar(cls, valor: Any) -> int:
        if isinstance(valor, cls):
            return int(valor)

        if valor is None:
            return int(cls.INSPETOR)

        try:
            inteiro = int(valor)
        except (TypeError, ValueError):
            chave = _normalizar_texto_chave(valor)
            mapa = {
                "inspetor": cls.INSPETOR,
                "inspector": cls.INSPETOR,
                "revisor": cls.REVISOR,
                "reviewer": cls.REVISOR,
                "admin_cliente": cls.ADMIN_CLIENTE,
                "admincliente": cls.ADMIN_CLIENTE,
                "cliente_admin": cls.ADMIN_CLIENTE,
                "clienteadmin": cls.ADMIN_CLIENTE,
                "administrador_cliente": cls.ADMIN_CLIENTE,
                "diretoria": cls.DIRETORIA,
                "admin": cls.DIRETORIA,
                "administrador": cls.DIRETORIA,
            }
            if chave not in mapa:
                raise ValueError(f"Nível de acesso inválido: {valor!r}")
            return int(mapa[chave])

        validos = {
            int(cls.INSPETOR),
            int(cls.REVISOR),
            int(cls.ADMIN_CLIENTE),
            int(cls.DIRETORIA),
        }
        if inteiro not in validos:
            raise ValueError(f"Nível de acesso inválido: {valor!r}")
        return inteiro


class _EnumTexto(str, enum.Enum):
    @classmethod
    def valores(cls) -> list[str]:
        return [item.value for item in cls]


class StatusLaudo(_EnumTexto):
    PENDENTE = "Pendente"
    CONFORME = "Conforme"
    NAO_CONFORME = "Nao Conforme"
    EM_ANDAMENTO = "Em Andamento"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "pendente": cls.PENDENTE.value,
            "conforme": cls.CONFORME.value,
            "nao_conforme": cls.NAO_CONFORME.value,
            "em_andamento": cls.EM_ANDAMENTO.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Status de laudo inválido: {valor!r}")


class StatusRevisao(_EnumTexto):
    RASCUNHO = "Rascunho"
    AGUARDANDO = "Aguardando Aval"
    APROVADO = "Aprovado"
    REJEITADO = "Rejeitado"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "rascunho": cls.RASCUNHO.value,
            "aguardando": cls.AGUARDANDO.value,
            "aguardando_aval": cls.AGUARDANDO.value,
            "aguardando_avaliacao": cls.AGUARDANDO.value,
            "aprovado": cls.APROVADO.value,
            "rejeitado": cls.REJEITADO.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Status de revisão inválido: {valor!r}")


class StatusAprendizadoIa(_EnumTexto):
    RASCUNHO_INSPETOR = "rascunho_inspetor"
    VALIDADO_MESA = "validado_mesa"
    REJEITADO_MESA = "rejeitado_mesa"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "rascunho": cls.RASCUNHO_INSPETOR.value,
            "rascunho_inspetor": cls.RASCUNHO_INSPETOR.value,
            "validado": cls.VALIDADO_MESA.value,
            "validado_mesa": cls.VALIDADO_MESA.value,
            "aprovado_mesa": cls.VALIDADO_MESA.value,
            "rejeitado": cls.REJEITADO_MESA.value,
            "rejeitado_mesa": cls.REJEITADO_MESA.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Status de aprendizado IA inválido: {valor!r}")


class EntryModePreference(_EnumTexto):
    CHAT_FIRST = "chat_first"
    EVIDENCE_FIRST = "evidence_first"
    AUTO_RECOMMENDED = "auto_recommended"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "chat_first": cls.CHAT_FIRST.value,
            "chatfirst": cls.CHAT_FIRST.value,
            "conversa": cls.CHAT_FIRST.value,
            "conversation": cls.CHAT_FIRST.value,
            "conversation_first": cls.CHAT_FIRST.value,
            "evidence_first": cls.EVIDENCE_FIRST.value,
            "evidencefirst": cls.EVIDENCE_FIRST.value,
            "evidencia": cls.EVIDENCE_FIRST.value,
            "evidencias": cls.EVIDENCE_FIRST.value,
            "guided": cls.EVIDENCE_FIRST.value,
            "checklist": cls.EVIDENCE_FIRST.value,
            "auto_recommended": cls.AUTO_RECOMMENDED.value,
            "autorecommended": cls.AUTO_RECOMMENDED.value,
            "auto": cls.AUTO_RECOMMENDED.value,
            "automatico": cls.AUTO_RECOMMENDED.value,
            "automatic": cls.AUTO_RECOMMENDED.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Preferência de modo de entrada inválida: {valor!r}")


class EntryModeEffective(_EnumTexto):
    CHAT_FIRST = "chat_first"
    EVIDENCE_FIRST = "evidence_first"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "chat_first": cls.CHAT_FIRST.value,
            "chatfirst": cls.CHAT_FIRST.value,
            "conversa": cls.CHAT_FIRST.value,
            "conversation": cls.CHAT_FIRST.value,
            "evidence_first": cls.EVIDENCE_FIRST.value,
            "evidencefirst": cls.EVIDENCE_FIRST.value,
            "evidencia": cls.EVIDENCE_FIRST.value,
            "evidencias": cls.EVIDENCE_FIRST.value,
            "guided": cls.EVIDENCE_FIRST.value,
            "checklist": cls.EVIDENCE_FIRST.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Modo de entrada efetivo inválido: {valor!r}")


class EntryModeReason(_EnumTexto):
    HARD_SAFETY_RULE = "hard_safety_rule"
    FAMILY_REQUIRED_MODE = "family_required_mode"
    TENANT_POLICY = "tenant_policy"
    ROLE_POLICY = "role_policy"
    USER_PREFERENCE = "user_preference"
    LAST_CASE_MODE = "last_case_mode"
    AUTO_RECOMMENDED = "auto_recommended"
    DEFAULT_PRODUCT_FALLBACK = "default_product_fallback"
    EXISTING_CASE_STATE = "existing_case_state"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "hard_safety_rule": cls.HARD_SAFETY_RULE.value,
            "hard_safety": cls.HARD_SAFETY_RULE.value,
            "family_required_mode": cls.FAMILY_REQUIRED_MODE.value,
            "family_required": cls.FAMILY_REQUIRED_MODE.value,
            "tenant_policy": cls.TENANT_POLICY.value,
            "role_policy": cls.ROLE_POLICY.value,
            "user_preference": cls.USER_PREFERENCE.value,
            "preferencia_usuario": cls.USER_PREFERENCE.value,
            "last_case_mode": cls.LAST_CASE_MODE.value,
            "ultimo_modo_caso": cls.LAST_CASE_MODE.value,
            "auto_recommended": cls.AUTO_RECOMMENDED.value,
            "autorecommended": cls.AUTO_RECOMMENDED.value,
            "default_product_fallback": cls.DEFAULT_PRODUCT_FALLBACK.value,
            "fallback_produto": cls.DEFAULT_PRODUCT_FALLBACK.value,
            "existing_case_state": cls.EXISTING_CASE_STATE.value,
            "legacy_case_state": cls.EXISTING_CASE_STATE.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Razão de modo de entrada inválida: {valor!r}")


class VereditoAprendizadoIa(_EnumTexto):
    CONFORME = "conforme"
    NAO_CONFORME = "nao_conforme"
    AJUSTE = "ajuste"
    DUVIDA = "duvida"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "conforme": cls.CONFORME.value,
            "correto": cls.CONFORME.value,
            "ok": cls.CONFORME.value,
            "nao_conforme": cls.NAO_CONFORME.value,
            "incorreto": cls.NAO_CONFORME.value,
            "errado": cls.NAO_CONFORME.value,
            "ajuste": cls.AJUSTE.value,
            "parcial": cls.AJUSTE.value,
            "duvida": cls.DUVIDA.value,
            "incerto": cls.DUVIDA.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Veredito de aprendizado IA inválido: {valor!r}")


class PlanoEmpresa(_EnumTexto):
    INICIAL = "Inicial"
    INTERMEDIARIO = "Intermediario"
    ILIMITADO = "Ilimitado"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "inicial": cls.INICIAL.value,
            "piloto": cls.INICIAL.value,
            "starter": cls.INICIAL.value,
            "intermediario": cls.INTERMEDIARIO.value,
            "pro": cls.INTERMEDIARIO.value,
            "profissional": cls.INTERMEDIARIO.value,
            "ilimitado": cls.ILIMITADO.value,
            "enterprise": cls.ILIMITADO.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Plano inválido: {valor!r}")


class ModoResposta(_EnumTexto):
    CURTO = "curto"
    DETALHADO = "detalhado"
    DEEP_RESEARCH = "deep_research"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "curto": cls.CURTO.value,
            "detalhado": cls.DETALHADO.value,
            "deepresearch": cls.DEEP_RESEARCH.value,
            "deep_research": cls.DEEP_RESEARCH.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Modo de resposta inválido: {valor!r}")


class TipoMensagem(_EnumTexto):
    USER = "user"
    IA = "ia"
    HUMANO_INSP = "humano_insp"
    HUMANO_ENG = "humano_eng"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "user": cls.USER.value,
            "usuario": cls.USER.value,
            "ia": cls.IA.value,
            "assistente": cls.IA.value,
            "humano_insp": cls.HUMANO_INSP.value,
            "whisper_insp": cls.HUMANO_INSP.value,
            "humano_eng": cls.HUMANO_ENG.value,
            "humanoeng": cls.HUMANO_ENG.value,
            "whisper_eng": cls.HUMANO_ENG.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Tipo de mensagem inválido: {valor!r}")


class OperationalEventType(_EnumTexto):
    IMAGE_BLURRY = "image_blurry"
    IMAGE_DARK = "image_dark"
    IMAGE_DUPLICATE = "image_duplicate"
    IMAGE_FAMILY_MISMATCH = "image_family_mismatch"
    IMAGE_ASSET_MISMATCH = "image_asset_mismatch"
    REQUIRED_ANGLE_MISSING = "required_angle_missing"
    EVIDENCE_CONCLUSION_CONFLICT = "evidence_conclusion_conflict"
    DOCUMENT_MISSING = "document_missing"
    FIELD_REOPENED = "field_reopened"
    BLOCK_RETURNED_TO_INSPECTOR = "block_returned_to_inspector"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "image_blurry": cls.IMAGE_BLURRY.value,
            "foto_borrada": cls.IMAGE_BLURRY.value,
            "imagem_borrada": cls.IMAGE_BLURRY.value,
            "image_dark": cls.IMAGE_DARK.value,
            "foto_escura": cls.IMAGE_DARK.value,
            "imagem_escura": cls.IMAGE_DARK.value,
            "image_duplicate": cls.IMAGE_DUPLICATE.value,
            "foto_duplicada": cls.IMAGE_DUPLICATE.value,
            "imagem_duplicada": cls.IMAGE_DUPLICATE.value,
            "image_family_mismatch": cls.IMAGE_FAMILY_MISMATCH.value,
            "familia_incompativel": cls.IMAGE_FAMILY_MISMATCH.value,
            "family_mismatch": cls.IMAGE_FAMILY_MISMATCH.value,
            "image_asset_mismatch": cls.IMAGE_ASSET_MISMATCH.value,
            "ativo_incompativel": cls.IMAGE_ASSET_MISMATCH.value,
            "asset_mismatch": cls.IMAGE_ASSET_MISMATCH.value,
            "required_angle_missing": cls.REQUIRED_ANGLE_MISSING.value,
            "angulo_obrigatorio_faltando": cls.REQUIRED_ANGLE_MISSING.value,
            "evidence_conclusion_conflict": cls.EVIDENCE_CONCLUSION_CONFLICT.value,
            "conflito_evidencia_conclusao": cls.EVIDENCE_CONCLUSION_CONFLICT.value,
            "document_missing": cls.DOCUMENT_MISSING.value,
            "documento_faltando": cls.DOCUMENT_MISSING.value,
            "field_reopened": cls.FIELD_REOPENED.value,
            "campo_reaberto": cls.FIELD_REOPENED.value,
            "block_returned_to_inspector": cls.BLOCK_RETURNED_TO_INSPECTOR.value,
            "bloco_devolvido_ao_inspetor": cls.BLOCK_RETURNED_TO_INSPECTOR.value,
            "refazer_inspetor": cls.BLOCK_RETURNED_TO_INSPECTOR.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Tipo de evento operacional invalido: {valor!r}")


class OperationalEventSource(_EnumTexto):
    SYSTEM_QUALITY_GATE = "system_quality_gate"
    MESA = "mesa"
    INSPETOR = "inspetor"
    CHAT_IA = "chat_ia"
    CURADORIA = "curadoria"
    RUNTIME = "runtime"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "system_quality_gate": cls.SYSTEM_QUALITY_GATE.value,
            "quality_gate": cls.SYSTEM_QUALITY_GATE.value,
            "sistema": cls.SYSTEM_QUALITY_GATE.value,
            "mesa": cls.MESA.value,
            "revisor": cls.MESA.value,
            "inspetor": cls.INSPETOR.value,
            "inspector": cls.INSPETOR.value,
            "chat_ia": cls.CHAT_IA.value,
            "ia": cls.CHAT_IA.value,
            "chat": cls.CHAT_IA.value,
            "curadoria": cls.CURADORIA.value,
            "curation": cls.CURADORIA.value,
            "runtime": cls.RUNTIME.value,
            "sistema_runtime": cls.RUNTIME.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Fonte de evento operacional invalida: {valor!r}")


class OperationalSeverity(_EnumTexto):
    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "info": cls.INFO.value,
            "informativo": cls.INFO.value,
            "warning": cls.WARNING.value,
            "aviso": cls.WARNING.value,
            "alerta": cls.WARNING.value,
            "blocker": cls.BLOCKER.value,
            "bloqueante": cls.BLOCKER.value,
            "critico": cls.BLOCKER.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Severidade operacional invalida: {valor!r}")


class EvidenceOperationalStatus(_EnumTexto):
    PENDING = "pending"
    OK = "ok"
    IRREGULAR = "irregular"
    REPLACED = "replaced"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "pending": cls.PENDING.value,
            "pendente": cls.PENDING.value,
            "validacao_operacional_pendente": cls.PENDING.value,
            "ok": cls.OK.value,
            "operational_ok": cls.OK.value,
            "operacional_ok": cls.OK.value,
            "irregular": cls.IRREGULAR.value,
            "operational_irregular": cls.IRREGULAR.value,
            "operacional_irregular": cls.IRREGULAR.value,
            "replaced": cls.REPLACED.value,
            "substituida": cls.REPLACED.value,
            "substituida_evidencia": cls.REPLACED.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Status operacional da evidencia invalido: {valor!r}")


class EvidenceMesaStatus(_EnumTexto):
    NOT_REVIEWED = "not_reviewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_RECHECK = "needs_recheck"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "not_reviewed": cls.NOT_REVIEWED.value,
            "nao_revisada": cls.NOT_REVIEWED.value,
            "pendente": cls.NOT_REVIEWED.value,
            "accepted": cls.ACCEPTED.value,
            "aceita_mesa": cls.ACCEPTED.value,
            "accepted_mesa": cls.ACCEPTED.value,
            "rejected": cls.REJECTED.value,
            "rejeitada_mesa": cls.REJECTED.value,
            "needs_recheck": cls.NEEDS_RECHECK.value,
            "revalidar": cls.NEEDS_RECHECK.value,
            "recheck": cls.NEEDS_RECHECK.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Status da Mesa para evidencia invalido: {valor!r}")


class OperationalIrregularityStatus(_EnumTexto):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "open": cls.OPEN.value,
            "aberta": cls.OPEN.value,
            "acknowledged": cls.ACKNOWLEDGED.value,
            "reconhecida": cls.ACKNOWLEDGED.value,
            "resolved": cls.RESOLVED.value,
            "resolvida": cls.RESOLVED.value,
            "dismissed": cls.DISMISSED.value,
            "descartada": cls.DISMISSED.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Status de irregularidade operacional invalido: {valor!r}")


class OperationalResolutionMode(_EnumTexto):
    RECAPTURED_EVIDENCE = "recaptured_evidence"
    EDITED_CASE_DATA = "edited_case_data"
    MESA_OVERRIDE = "mesa_override"
    DISMISSED_FALSE_POSITIVE = "dismissed_false_positive"
    NOT_APPLICABLE = "not_applicable"

    @classmethod
    def normalizar(cls, valor: Any) -> str:
        chave = _normalizar_texto_chave(valor)
        mapa = {
            "recaptured_evidence": cls.RECAPTURED_EVIDENCE.value,
            "nova_foto": cls.RECAPTURED_EVIDENCE.value,
            "recaptura": cls.RECAPTURED_EVIDENCE.value,
            "edited_case_data": cls.EDITED_CASE_DATA.value,
            "edicao_caso": cls.EDITED_CASE_DATA.value,
            "edited_data": cls.EDITED_CASE_DATA.value,
            "mesa_override": cls.MESA_OVERRIDE.value,
            "override_mesa": cls.MESA_OVERRIDE.value,
            "dismissed_false_positive": cls.DISMISSED_FALSE_POSITIVE.value,
            "falso_positivo": cls.DISMISSED_FALSE_POSITIVE.value,
            "not_applicable": cls.NOT_APPLICABLE.value,
            "nao_aplicavel": cls.NOT_APPLICABLE.value,
        }
        if chave in mapa:
            return mapa[chave]
        if valor in cls.valores():
            return str(valor)
        raise ValueError(f"Modo de resolucao operacional invalido: {valor!r}")


_TIPOS_MENSAGEM_VALIDOS = ", ".join(f"'{tipo.value}'" for tipo in TipoMensagem)


def _valores_enum(cls: type[enum.Enum]) -> list[str]:
    return [item.value for item in cls]


LIMITES_PADRAO: dict[str, dict[str, Any]] = {
    PlanoEmpresa.INICIAL.value: {
        "laudos_mes": 50,
        "usuarios_max": 1,
        "upload_doc": False,
        "deep_research": False,
        "integracoes_max": 0,
        "retencao_dias": 30,
    },
    PlanoEmpresa.INTERMEDIARIO.value: {
        "laudos_mes": 300,
        "usuarios_max": 5,
        "upload_doc": True,
        "deep_research": False,
        "integracoes_max": 1,
        "retencao_dias": 365,
    },
    PlanoEmpresa.ILIMITADO.value: {
        "laudos_mes": None,
        "usuarios_max": None,
        "upload_doc": True,
        "deep_research": True,
        "integracoes_max": None,
        "retencao_dias": None,
    },
}


@dataclass(slots=True)
class LimitePlanoFallback:
    plano: str
    laudos_mes: int | None
    usuarios_max: int | None
    upload_doc: bool
    deep_research: bool
    integracoes_max: int | None
    retencao_dias: int | None

    def laudos_ilimitados(self) -> bool:
        return self.laudos_mes is None

    def usuarios_ilimitados(self) -> bool:
        return self.usuarios_max is None


__all__ = [
    "EntryModeEffective",
    "EntryModePreference",
    "EntryModeReason",
    "EvidenceMesaStatus",
    "EvidenceOperationalStatus",
    "LIMITES_PADRAO",
    "LimitePlanoFallback",
    "ModoResposta",
    "NivelAcesso",
    "OperationalEventSource",
    "OperationalEventType",
    "OperationalIrregularityStatus",
    "OperationalResolutionMode",
    "OperationalSeverity",
    "PlanoEmpresa",
    "StatusAprendizadoIa",
    "StatusLaudo",
    "StatusRevisao",
    "TipoMensagem",
    "VereditoAprendizadoIa",
    "_TIPOS_MENSAGEM_VALIDOS",
    "_valores_enum",
]
