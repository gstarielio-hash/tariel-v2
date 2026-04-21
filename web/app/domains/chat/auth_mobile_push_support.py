"""Persistencia e serializacao do registro push do app mobile."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.cliente.auditoria import registrar_auditoria_empresa
from app.shared.database import DispositivoPushMobile, Usuario, agora_utc


def _normalizar_texto(
    valor: object,
    *,
    limite: int,
    padrao: str = "",
) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return padrao
    return texto[:limite]


def _normalizar_bool(valor: object, *, padrao: bool = False) -> bool:
    if isinstance(valor, bool):
        return valor
    return padrao


def serializar_dispositivo_push_mobile(
    registro: DispositivoPushMobile,
) -> dict[str, object]:
    criado_em = getattr(registro, "criado_em", None)
    last_seen_at = getattr(registro, "last_seen_at", None)
    return {
        "id": int(registro.id),
        "device_id": str(registro.device_id or ""),
        "plataforma": str(registro.plataforma or "android"),
        "provider": str(registro.provider or "expo"),
        "push_token": str(registro.push_token or ""),
        "permissao_notificacoes": bool(registro.permissao_notificacoes),
        "push_habilitado": bool(registro.push_habilitado),
        "token_status": str(registro.token_status or "unavailable"),
        "canal_build": str(registro.canal_build or ""),
        "app_version": str(registro.app_version or ""),
        "build_number": str(registro.build_number or ""),
        "device_label": str(registro.device_label or ""),
        "is_emulator": bool(registro.is_emulator),
        "ultimo_erro": str(registro.ultimo_erro or ""),
        "registered_at": criado_em.isoformat() if criado_em else "",
        "last_seen_at": last_seen_at.isoformat() if last_seen_at else "",
    }


def _resumir_status_push(token_status: str) -> tuple[str, str]:
    status = str(token_status or "unavailable").strip() or "unavailable"
    if status == "registered":
        return (
            "Dispositivo push registrado",
            "Token push do dispositivo sincronizado para uso operacional.",
        )
    if status == "disabled":
        return (
            "Push desativado no dispositivo",
            "O app informou que o envio de push ficou desligado neste dispositivo.",
        )
    if status == "permission_denied":
        return (
            "Permissão de push negada",
            "O sistema operacional não liberou notificações para este dispositivo.",
        )
    if status == "missing_project_id":
        return (
            "Push sem project id",
            "O build atual não publicou o project id necessário para obter o token Expo.",
        )
    if status == "unsupported":
        return (
            "Push indisponível neste ambiente",
            "O ambiente atual do app não suporta materializar token push nativo.",
        )
    if status == "token_error":
        return (
            "Falha ao materializar token push",
            "O app tentou obter o token push, mas o runtime devolveu erro operacional.",
        )
    return (
        "Registro push atualizado",
        "O dispositivo mobile atualizou o estado operacional do push.",
    )


def registrar_dispositivo_push_mobile_usuario(
    banco: Session,
    *,
    usuario: Usuario,
    payload: dict[str, Any],
) -> DispositivoPushMobile:
    device_id = _normalizar_texto(payload.get("device_id"), limite=120)
    if not device_id:
        raise ValueError("device_id é obrigatório para registrar o push mobile.")

    plataforma = _normalizar_texto(
        payload.get("plataforma"),
        limite=20,
        padrao="android",
    )
    provider = _normalizar_texto(
        payload.get("provider"),
        limite=20,
        padrao="expo",
    )
    token_status = _normalizar_texto(
        payload.get("token_status"),
        limite=40,
        padrao="unavailable",
    )
    push_token = _normalizar_texto(payload.get("push_token"), limite=255)
    canal_build = _normalizar_texto(payload.get("canal_build"), limite=60)
    app_version = _normalizar_texto(payload.get("app_version"), limite=40)
    build_number = _normalizar_texto(payload.get("build_number"), limite=40)
    device_label = _normalizar_texto(payload.get("device_label"), limite=120)
    ultimo_erro = _normalizar_texto(payload.get("ultimo_erro"), limite=220)
    permissao_notificacoes = _normalizar_bool(
        payload.get("permissao_notificacoes"),
    )
    push_habilitado = _normalizar_bool(payload.get("push_habilitado"))
    is_emulator = _normalizar_bool(payload.get("is_emulator"))
    now = agora_utc()

    registro = banco.scalar(
        select(DispositivoPushMobile).where(
            DispositivoPushMobile.usuario_id == int(usuario.id),
            DispositivoPushMobile.device_id == device_id,
            DispositivoPushMobile.plataforma == plataforma,
        )
    )

    criado = registro is None
    if registro is None:
        registro = DispositivoPushMobile(
            usuario_id=int(usuario.id),
            empresa_id=int(usuario.empresa_id),
            device_id=device_id,
            plataforma=plataforma,
        )
        banco.add(registro)

    assinatura_anterior = (
        str(registro.provider or ""),
        str(registro.push_token or ""),
        bool(registro.permissao_notificacoes),
        bool(registro.push_habilitado),
        str(registro.token_status or ""),
        str(registro.canal_build or ""),
        str(registro.app_version or ""),
        str(registro.build_number or ""),
        str(registro.device_label or ""),
        bool(registro.is_emulator),
        str(registro.ultimo_erro or ""),
    )

    registro.provider = provider
    registro.push_token = push_token or None
    registro.permissao_notificacoes = permissao_notificacoes
    registro.push_habilitado = push_habilitado
    registro.token_status = token_status
    registro.canal_build = canal_build or None
    registro.app_version = app_version or None
    registro.build_number = build_number or None
    registro.device_label = device_label or None
    registro.is_emulator = is_emulator
    registro.ultimo_erro = ultimo_erro or None
    registro.last_seen_at = now
    registro.atualizado_em = now
    banco.flush()
    banco.refresh(registro)

    assinatura_atual = (
        str(registro.provider or ""),
        str(registro.push_token or ""),
        bool(registro.permissao_notificacoes),
        bool(registro.push_habilitado),
        str(registro.token_status or ""),
        str(registro.canal_build or ""),
        str(registro.app_version or ""),
        str(registro.build_number or ""),
        str(registro.device_label or ""),
        bool(registro.is_emulator),
        str(registro.ultimo_erro or ""),
    )

    if criado or assinatura_anterior != assinatura_atual:
        resumo, detalhe = _resumir_status_push(token_status)
        registrar_auditoria_empresa(
            banco,
            empresa_id=int(usuario.empresa_id),
            ator_usuario_id=int(usuario.id),
            alvo_usuario_id=int(usuario.id),
            portal="mobile",
            acao=(
                "push_dispositivo_registrado"
                if criado
                else "push_dispositivo_atualizado"
            ),
            resumo=resumo,
            detalhe=detalhe,
            payload={
                "device_id": registro.device_id,
                "plataforma": registro.plataforma,
                "provider": registro.provider,
                "token_status": registro.token_status,
                "push_habilitado": registro.push_habilitado,
                "permissao_notificacoes": registro.permissao_notificacoes,
                "canal_build": registro.canal_build,
                "app_version": registro.app_version,
                "build_number": registro.build_number,
                "is_emulator": registro.is_emulator,
            },
        )

    return registro


__all__ = [
    "registrar_dispositivo_push_mobile_usuario",
    "serializar_dispositivo_push_mobile",
]
