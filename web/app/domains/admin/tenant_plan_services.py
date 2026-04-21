from __future__ import annotations

from typing import Any

from sqlalchemy import case
from sqlalchemy.orm import Session

from app.shared.database import Empresa, LimitePlano, PlanoEmpresa

# Aceita aliases comerciais antigos, mas persiste no formato canônico
# definido em banco_dados.PlanoEmpresa.
_ALIASES_PLANO = {
    "piloto": PlanoEmpresa.INICIAL.value,
    "inicial": PlanoEmpresa.INICIAL.value,
    "starter": PlanoEmpresa.INICIAL.value,
    "pro": PlanoEmpresa.INTERMEDIARIO.value,
    "intermediario": PlanoEmpresa.INTERMEDIARIO.value,
    "profissional": PlanoEmpresa.INTERMEDIARIO.value,
    "ilimitado": PlanoEmpresa.ILIMITADO.value,
    "enterprise": PlanoEmpresa.ILIMITADO.value,
}

_PRIORIDADE_PLANO = {
    PlanoEmpresa.ILIMITADO.value: 1,
    PlanoEmpresa.INTERMEDIARIO.value: 2,
    PlanoEmpresa.INICIAL.value: 3,
}


def _normalizar_plano(plano: str) -> str:
    try:
        # Banco já absorve parte da compatibilidade.
        return PlanoEmpresa.normalizar(plano)
    except Exception:
        chave = str(plano or "").strip().lower()
        if chave in _ALIASES_PLANO:
            return _ALIASES_PLANO[chave]
        raise ValueError("Plano inválido. Use: Inicial, Intermediario ou Ilimitado.")


def _case_prioridade_plano():
    return case(
        (Empresa.plano_ativo == PlanoEmpresa.ILIMITADO.value, 1),
        (Empresa.plano_ativo == PlanoEmpresa.INTERMEDIARIO.value, 2),
        else_=3,
    )


def _obter_limite_usuarios_empresa(db: Session, empresa: Empresa) -> int | None:
    limites = empresa.obter_limites(db)
    return limites.usuarios_max


def _obter_limite_laudos_empresa(db: Session, empresa: Empresa) -> int | None:
    limites = empresa.obter_limites(db)
    return limites.laudos_mes


def _obter_limites_plano(db: Session, plano: str):
    plano_norm = _normalizar_plano(plano)
    limite = db.get(LimitePlano, plano_norm)
    if limite is not None:
        return limite

    empresa_virtual = Empresa(
        nome_fantasia="preview",
        cnpj="00000000000000",
        plano_ativo=plano_norm,
    )
    return empresa_virtual.obter_limites(db)


def _snapshot_limites(limites: Any) -> dict[str, Any]:
    return {
        "usuarios_max": getattr(limites, "usuarios_max", None),
        "laudos_mes": getattr(limites, "laudos_mes", None),
        "upload_doc": bool(getattr(limites, "upload_doc", False)),
        "deep_research": bool(getattr(limites, "deep_research", False)),
        "integracoes_max": getattr(limites, "integracoes_max", None),
        "retencao_dias": getattr(limites, "retencao_dias", None),
    }


def _label_limite(valor: Any, *, sufixo: str = "") -> str:
    if valor is None:
        return f"Ilimitado{sufixo}"
    return f"{int(valor)}{sufixo}"


def _delta_label(atual: Any, novo: Any) -> str:
    if atual is None and novo is None:
        return "Sem alteração"
    if atual is None:
        return "Capacidade reduzida a limite explícito"
    if novo is None:
        return "Capacidade passa a ilimitada"
    delta = int(novo) - int(atual)
    if delta == 0:
        return "Sem alteração"
    return f"{delta:+d}"


def construir_preview_troca_plano(
    db: Session,
    *,
    empresa: Empresa,
    novo_plano: str,
    usuarios_total: int,
    uso_atual: int,
) -> dict[str, Any]:
    plano_atual = _normalizar_plano(str(getattr(empresa, "plano_ativo", "") or ""))
    plano_novo = _normalizar_plano(novo_plano)
    limites_atuais = _snapshot_limites(_obter_limites_plano(db, plano_atual))
    limites_novos = _snapshot_limites(_obter_limites_plano(db, plano_novo))

    capacidade_risco = []
    usuarios_max_novo = limites_novos["usuarios_max"]
    laudos_mes_novo = limites_novos["laudos_mes"]
    if usuarios_max_novo is not None and int(usuarios_total) > int(usuarios_max_novo):
        capacidade_risco.append("Total de usuários acima do novo limite")
    if laudos_mes_novo is not None and int(uso_atual) > int(laudos_mes_novo):
        capacidade_risco.append("Uso atual acima do novo limite mensal")

    return {
        "plano_atual": plano_atual,
        "plano_novo": plano_novo,
        "limites_atuais": limites_atuais,
        "limites_novos": limites_novos,
        "usuarios_total": int(usuarios_total),
        "uso_atual": int(uso_atual),
        "impacto": {
            "usuarios_max": _delta_label(limites_atuais["usuarios_max"], limites_novos["usuarios_max"]),
            "laudos_mes": _delta_label(limites_atuais["laudos_mes"], limites_novos["laudos_mes"]),
            "integracoes_max": _delta_label(limites_atuais["integracoes_max"], limites_novos["integracoes_max"]),
            "retencao_dias": _delta_label(limites_atuais["retencao_dias"], limites_novos["retencao_dias"]),
        },
        "alertas": capacidade_risco,
        "resumo_confirmacao": (
            f"Plano atual: {plano_atual} | Novo plano: {plano_novo} | "
            f"Usuarios: {_label_limite(limites_atuais['usuarios_max'])} -> {_label_limite(limites_novos['usuarios_max'])} | "
            f"Laudos/mes: {_label_limite(limites_atuais['laudos_mes'])} -> {_label_limite(limites_novos['laudos_mes'])}"
            + (f" | Alertas: {'; '.join(capacidade_risco)}" if capacidade_risco else "")
        ),
    }
