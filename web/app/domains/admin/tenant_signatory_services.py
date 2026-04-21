"""Serviços de signatários governados do tenant cliente."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.admin.tenant_client_read_services import (
    _formatar_data_admin,
    _normalizar_datetime_admin,
)
from app.domains.admin.tenant_user_services import (
    _buscar_empresa,
    _normalizar_texto_curto,
    _normalizar_texto_opcional,
)
from app.shared.database import (
    SignatarioGovernadoLaudo,
    flush_ou_rollback_integridade,
)

logger = logging.getLogger("tariel.saas")


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalizar_chave_signatario(valor: str, *, campo: str, max_len: int) -> str:
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
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    if not texto:
        raise ValueError(f"{campo} é obrigatório.")
    return texto[:max_len]


def _normalizar_lista_canonica_signatario(
    valor: str | list[str] | tuple[str, ...] | None,
    *,
    campo: str,
    max_len_item: int = 120,
) -> list[str] | None:
    if valor is None:
        return None
    if isinstance(valor, (list, tuple)):
        itens_brutos = list(valor)
    else:
        texto = str(valor or "").strip()
        if not texto:
            return None
        if texto.startswith("["):
            try:
                payload = json.loads(texto)
            except json.JSONDecodeError as erro:
                raise ValueError(f"{campo} precisa ser uma lista JSON.") from erro
            if not isinstance(payload, list):
                raise ValueError(f"{campo} precisa ser uma lista JSON.")
            itens_brutos = payload
        else:
            itens_brutos = texto.splitlines()

    itens: list[str] = []
    vistos: set[str] = set()
    for bruto in itens_brutos:
        item = _normalizar_chave_signatario(bruto, campo=campo, max_len=max_len_item)
        if not item or item in vistos:
            continue
        vistos.add(item)
        itens.append(item)
    return itens or None


def _normalizar_validade_signatario(valor: str | datetime | None) -> datetime | None:
    if isinstance(valor, datetime):
        dt = valor
    else:
        bruto = _normalizar_texto_opcional(valor, 40)
        if not bruto:
            return None
        try:
            dt = datetime.fromisoformat(bruto)
        except ValueError as exc:
            raise ValueError("Data de validade do signatário inválida.") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalizar_family_keys_signatario(
    family_keys: list[str] | tuple[str, ...] | str | None,
) -> list[str]:
    return _normalizar_lista_canonica_signatario(
        family_keys,
        campo="Famílias compatíveis",
    ) or []


def _status_signatario_governado(
    *,
    ativo: bool,
    valid_until: datetime | None,
) -> dict[str, str]:
    validade = _normalizar_datetime_admin(valid_until)
    if not ativo:
        return {"key": "inactive", "label": "Inativo", "tone": "idle"}
    if validade is not None and validade < _agora_utc():
        return {"key": "expired", "label": "Expirado", "tone": "archived"}
    if validade is not None and validade <= (_agora_utc() + timedelta(days=30)):
        return {"key": "expiring_soon", "label": "Validade próxima", "tone": "testing"}
    return {"key": "ready", "label": "Pronto", "tone": "active"}


def _serializar_signatario_governado_admin(
    signatario: SignatarioGovernadoLaudo,
    *,
    family_labels: dict[str, str],
) -> dict[str, Any]:
    allowed_family_keys = _normalizar_family_keys_signatario(
        getattr(signatario, "allowed_family_keys_json", None)
    )
    status = _status_signatario_governado(
        ativo=bool(getattr(signatario, "ativo", False)),
        valid_until=getattr(signatario, "valid_until", None),
    )
    family_scope = [
        {
            "family_key": family_key,
            "family_label": family_labels.get(family_key, family_key),
        }
        for family_key in allowed_family_keys
    ]
    return {
        "id": int(signatario.id),
        "nome": str(signatario.nome),
        "funcao": str(signatario.funcao),
        "registro_profissional": _normalizar_texto_opcional(signatario.registro_profissional, 80),
        "valid_until": _normalizar_datetime_admin(getattr(signatario, "valid_until", None)),
        "valid_until_label": _formatar_data_admin(
            getattr(signatario, "valid_until", None),
            fallback="Sem validade",
        ),
        "ativo": bool(getattr(signatario, "ativo", False)),
        "status": status,
        "allowed_family_keys": allowed_family_keys,
        "family_scope": family_scope,
        "family_scope_summary": "Todas as famílias liberadas do tenant" if not family_scope else ", ".join(
            item["family_label"] for item in family_scope[:3]
        ),
        "observacoes": _normalizar_texto_opcional(getattr(signatario, "observacoes", None)),
    }


def upsert_signatario_governado_laudo(
    db: Session,
    *,
    tenant_id: int,
    nome: str,
    funcao: str,
    registro_profissional: str = "",
    valid_until: str | datetime | None = None,
    allowed_family_keys: list[str] | tuple[str, ...] | str | None = None,
    observacoes: str = "",
    ativo: bool = True,
    signatario_id: int | None = None,
    criado_por_id: int | None = None,
) -> SignatarioGovernadoLaudo:
    empresa = _buscar_empresa(db, int(tenant_id))
    registro = None
    if signatario_id:
        registro = db.scalar(
            select(SignatarioGovernadoLaudo).where(
                SignatarioGovernadoLaudo.id == int(signatario_id),
                SignatarioGovernadoLaudo.tenant_id == int(empresa.id),
            )
        )
        if registro is None:
            raise ValueError("Signatário governado não encontrado para este tenant.")
    if registro is None:
        registro = SignatarioGovernadoLaudo(
            tenant_id=int(empresa.id),
            criado_por_id=criado_por_id,
        )
        db.add(registro)

    registro.nome = _normalizar_texto_curto(nome, campo="Nome do signatário", max_len=160)
    registro.funcao = _normalizar_texto_curto(funcao, campo="Função do signatário", max_len=120)
    registro.registro_profissional = _normalizar_texto_opcional(registro_profissional, 80)
    registro.valid_until = _normalizar_validade_signatario(valid_until)
    registro.allowed_family_keys_json = _normalizar_family_keys_signatario(allowed_family_keys)
    registro.observacoes = _normalizar_texto_opcional(observacoes)
    registro.ativo = bool(ativo)
    if criado_por_id and not registro.criado_por_id:
        registro.criado_por_id = criado_por_id

    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível salvar o signatário governado do tenant.",
    )
    return registro


__all__ = [
    "_serializar_signatario_governado_admin",
    "upsert_signatario_governado_laudo",
]
