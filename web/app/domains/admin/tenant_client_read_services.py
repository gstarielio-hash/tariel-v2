from __future__ import annotations

from collections import defaultdict
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable
from urllib.parse import urlencode

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.admin.admin_platform_identity_services import _tenant_cliente_clause
from app.domains.admin.tenant_plan_services import (
    _PRIORIDADE_PLANO,
    _label_limite,
    _normalizar_plano,
    _obter_limite_laudos_empresa,
    _obter_limite_usuarios_empresa,
    construir_preview_troca_plano,
)
from app.domains.admin.tenant_user_services import _NIVEIS_GERENCIAVEIS_CLIENTE
from app.shared.database import (
    Empresa,
    Laudo,
    NivelAcesso,
    PlanoEmpresa,
    RegistroAuditoriaEmpresa,
    SessaoAtiva,
    SignatarioGovernadoLaudo,
    Usuario,
)


logger = logging.getLogger("tariel.saas")


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalizar_datetime_admin(valor: datetime | None) -> datetime | None:
    if not isinstance(valor, datetime):
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _max_datetime_admin(valores) -> datetime | None:
    candidatos = [valor for valor in valores if isinstance(valor, datetime)]
    return max(candidatos) if candidatos else None


def _formatar_data_admin(valor: datetime | None, *, fallback: str = "Sem atividade") -> str:
    valor_norm = _normalizar_datetime_admin(valor)
    if valor_norm is None:
        return fallback
    return valor_norm.strftime("%d/%m/%Y %H:%M UTC")


def _role_label(nivel_acesso: int) -> str:
    if int(nivel_acesso) == int(NivelAcesso.ADMIN_CLIENTE):
        return "Administrador da empresa"
    if int(nivel_acesso) == int(NivelAcesso.REVISOR):
        return "Equipe de analise"
    return "Equipe de campo"


def _normalizar_filtro_status(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    if texto in {"ativo", "bloqueado", "pendente"}:
        return texto
    return ""


def _normalizar_filtro_saude(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    if texto in {"ok", "alerta", "critico"}:
        return texto
    return ""


def _normalizar_filtro_atividade(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    if texto in {"24h", "7d", "30d", "sem_atividade"}:
        return texto
    return ""


def _normalizar_ordenacao_clientes(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    if texto in {"nome", "criacao", "ultimo_acesso", "plano", "saude"}:
        return texto
    return "nome"


def _normalizar_direcao_ordenacao(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    if texto in {"asc", "desc"}:
        return texto
    return "asc"


def _normalizar_paginacao(valor: Any, *, default: int, min_value: int = 1, max_value: int = 100) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, numero))


def _coletar_contexto_empresas(
    db: Session,
    *,
    empresa_ids: list[int],
) -> dict[str, Any]:
    usuarios_por_empresa: dict[int, list[Usuario]] = defaultdict(list)
    sessoes_por_empresa: dict[int, list[tuple[SessaoAtiva, Usuario]]] = defaultdict(list)
    totais_laudos_por_empresa: dict[int, int] = {}

    if not empresa_ids:
        return {
            "usuarios_por_empresa": usuarios_por_empresa,
            "sessoes_por_empresa": sessoes_por_empresa,
            "totais_laudos_por_empresa": totais_laudos_por_empresa,
        }

    usuarios = list(
        db.scalars(
            select(Usuario)
            .where(Usuario.empresa_id.in_(empresa_ids))
            .order_by(Usuario.nivel_acesso.desc(), Usuario.nome_completo.asc())
        ).all()
    )
    for usuario in usuarios:
        usuarios_por_empresa[int(usuario.empresa_id)].append(usuario)

    sessoes = list(
        db.execute(
            select(SessaoAtiva, Usuario)
            .join(Usuario, Usuario.id == SessaoAtiva.usuario_id)
            .where(Usuario.empresa_id.in_(empresa_ids))
            .order_by(SessaoAtiva.ultima_atividade_em.desc())
        ).all()
    )
    for sessao, usuario in sessoes:
        sessoes_por_empresa[int(usuario.empresa_id)].append((sessao, usuario))

    totais_laudos = list(
        db.execute(
            select(Laudo.empresa_id, func.count(Laudo.id))
            .where(Laudo.empresa_id.in_(empresa_ids))
            .group_by(Laudo.empresa_id)
        ).all()
    )
    for empresa_id, total in totais_laudos:
        totais_laudos_por_empresa[int(empresa_id)] = int(total or 0)

    return {
        "usuarios_por_empresa": usuarios_por_empresa,
        "sessoes_por_empresa": sessoes_por_empresa,
        "totais_laudos_por_empresa": totais_laudos_por_empresa,
    }


def _serializar_usuario_admin(
    usuario: Usuario,
    *,
    sessoes_usuario: list[SessaoAtiva],
) -> dict[str, Any]:
    ultimo_acesso_em = _max_datetime_admin(
        _normalizar_datetime_admin(getattr(sessao, "ultima_atividade_em", None))
        for sessao in sessoes_usuario
    )
    return {
        "id": int(usuario.id),
        "nome_completo": str(getattr(usuario, "nome_completo", "") or ""),
        "email": str(getattr(usuario, "email", "") or ""),
        "nivel_acesso": int(getattr(usuario, "nivel_acesso", 0) or 0),
        "role_label": _role_label(int(getattr(usuario, "nivel_acesso", 0) or 0)),
        "ativo": bool(getattr(usuario, "ativo", False)),
        "status_bloqueio": bool(getattr(usuario, "status_bloqueio", False)),
        "senha_temporaria_ativa": bool(getattr(usuario, "senha_temporaria_ativa", False)),
        "crea": str(getattr(usuario, "crea", "") or ""),
        "session_count": len(sessoes_usuario),
        "ultimo_acesso_em": ultimo_acesso_em,
        "ultimo_acesso_label": _formatar_data_admin(ultimo_acesso_em),
    }


def _resumir_primeiro_acesso_empresa(
    *,
    empresa: Empresa,
    admins_cliente: list[dict[str, Any]],
) -> dict[str, Any]:
    admin_referencia = next(
        (item for item in admins_cliente if bool(item.get("senha_temporaria_ativa"))),
        admins_cliente[0] if admins_cliente else None,
    )
    login_base_url = "/cliente/login"
    if admin_referencia is None:
        return {
            "has_admin": False,
            "status_key": "missing_admin",
            "status_label": "Primeiro acesso ainda nao preparado",
            "login_base_url": login_base_url,
            "login_prefill_url": login_base_url,
            "copy_text": (
                f"Empresa: {str(getattr(empresa, 'nome_fantasia', '') or '').strip()}\n"
                "Portal da empresa: /cliente/login\n"
                "Nenhum acesso inicial foi configurado ainda."
            ),
        }

    email = str(admin_referencia.get("email") or "").strip().lower()
    prefill_query = urlencode({"email": email, "primeiro_acesso": "1"}) if email else "primeiro_acesso=1"
    status_key = (
        "password_reset_required"
        if bool(admin_referencia.get("senha_temporaria_ativa"))
        else "active"
    )
    status_label = (
        "Primeiro acesso pendente"
        if status_key == "password_reset_required"
        else "Acesso inicial ja concluido"
    )
    copy_lines = [
        f"Empresa: {str(getattr(empresa, 'nome_fantasia', '') or '').strip()}",
        "Portal da empresa: /cliente/login",
    ]
    if email:
        copy_lines.append(f"E-mail de acesso: {email}")
    copy_lines.append("Senha: use a senha temporaria enviada em canal seguro.")
    copy_lines.append("No primeiro acesso, o sistema vai pedir a definicao de uma nova senha.")
    return {
        "has_admin": True,
        "status_key": status_key,
        "status_label": status_label,
        "admin_name": str(admin_referencia.get("nome_completo") or "").strip() or "Responsavel da empresa",
        "admin_email": email,
        "requires_password_reset": status_key == "password_reset_required",
        "login_base_url": login_base_url,
        "login_prefill_url": f"{login_base_url}?{prefill_query}",
        "copy_text": "\n".join(copy_lines),
    }


def _classificar_status_empresa(
    empresa: Empresa,
    *,
    admins_cliente: list[Usuario],
) -> tuple[str, str, str]:
    if bool(getattr(empresa, "status_bloqueio", False)):
        return "bloqueado", "Bloqueado", "critico"

    if not admins_cliente or any(bool(getattr(item, "senha_temporaria_ativa", False)) for item in admins_cliente):
        return "pendente", "Pendente", "atencao"

    return "ativo", "Ativo", "conforme"


def _classificar_saude_empresa(
    *,
    status_value: str,
    admins_cliente: list[Usuario],
    inspetores: list[Usuario],
    revisores: list[Usuario],
    ultimo_acesso_em: datetime | None,
    uso_percentual: int | None,
) -> tuple[str, str, str, str]:
    ultimo_acesso_norm = _normalizar_datetime_admin(ultimo_acesso_em)
    if status_value == "bloqueado":
        return "critico", "Crítico", "critico", "Tenant bloqueado"

    if not admins_cliente:
        return "critico", "Crítico", "critico", "Sem administrador da empresa configurado"

    if uso_percentual is not None and uso_percentual >= 100:
        return "critico", "Crítico", "critico", "Capacidade do plano esgotada"

    if status_value == "pendente":
        return "alerta", "Alerta", "atencao", "Onboarding ou troca de senha pendente"

    if not inspetores and not revisores:
        return "alerta", "Alerta", "atencao", "Sem equipe operacional ativa"

    if uso_percentual is not None and uso_percentual >= 80:
        return "alerta", "Alerta", "atencao", "Uso acima de 80% do plano"

    limite_inatividade = _agora_utc() - timedelta(days=30)
    if ultimo_acesso_norm is None or ultimo_acesso_norm < limite_inatividade:
        return "alerta", "Alerta", "atencao", "Sem atividade recente"

    return "ok", "OK", "conforme", "Operação dentro do esperado"


def _atividade_recente_compat(
    *,
    ultimo_acesso_em: datetime | None,
    filtro_atividade: str,
) -> bool:
    ultimo_acesso_norm = _normalizar_datetime_admin(ultimo_acesso_em)
    if not filtro_atividade:
        return True

    agora = _agora_utc()
    if filtro_atividade == "sem_atividade":
        return ultimo_acesso_norm is None or ultimo_acesso_norm < (agora - timedelta(days=30))
    if ultimo_acesso_norm is None:
        return False
    if filtro_atividade == "24h":
        return ultimo_acesso_norm >= agora - timedelta(hours=24)
    if filtro_atividade == "7d":
        return ultimo_acesso_norm >= agora - timedelta(days=7)
    if filtro_atividade == "30d":
        return ultimo_acesso_norm >= agora - timedelta(days=30)
    return True


def buscar_todos_clientes(
    db: Session,
    filtro_nome: str = "",
    filtro_codigo: str = "",
    filtro_plano: str = "",
    filtro_status: str = "",
    filtro_saude: str = "",
    filtro_atividade: str = "",
    ordenar_por: str = "nome",
    direcao: str = "asc",
    pagina: int = 1,
    por_pagina: int = 20,
) -> dict[str, Any]:
    stmt = select(Empresa).where(_tenant_cliente_clause())

    nome = str(filtro_nome or "").strip()
    if nome:
        stmt = stmt.where(Empresa.nome_fantasia.ilike(f"%{nome}%"))

    import re

    codigo = re.sub(r"\D+", "", str(filtro_codigo or ""))
    if codigo:
        if len(codigo) <= 9:
            stmt = stmt.where(Empresa.id == int(codigo))
        else:
            stmt = stmt.where(Empresa.cnpj.ilike(f"%{codigo}%"))

    plano = str(filtro_plano or "").strip()
    if plano:
        stmt = stmt.where(Empresa.plano_ativo == _normalizar_plano(plano))

    empresas = list(db.scalars(stmt.order_by(Empresa.nome_fantasia.asc(), Empresa.id.asc())).all())
    contexto = _coletar_contexto_empresas(
        db,
        empresa_ids=[int(empresa.id) for empresa in empresas],
    )
    usuarios_por_empresa = contexto["usuarios_por_empresa"]
    sessoes_por_empresa = contexto["sessoes_por_empresa"]
    totais_laudos_por_empresa = contexto["totais_laudos_por_empresa"]

    itens: list[dict[str, Any]] = []
    for empresa in empresas:
        empresa_id = int(empresa.id)
        usuarios_empresa = list(usuarios_por_empresa.get(empresa_id, []))
        admins_cliente = [
            usuario for usuario in usuarios_empresa if int(usuario.nivel_acesso) == int(NivelAcesso.ADMIN_CLIENTE)
        ]
        inspetores = [
            usuario for usuario in usuarios_empresa if int(usuario.nivel_acesso) == int(NivelAcesso.INSPETOR)
        ]
        revisores = [
            usuario for usuario in usuarios_empresa if int(usuario.nivel_acesso) == int(NivelAcesso.REVISOR)
        ]
        sessoes_empresa = list(sessoes_por_empresa.get(empresa_id, []))
        ultimo_acesso_em = _max_datetime_admin(
            _normalizar_datetime_admin(getattr(sessao, "ultima_atividade_em", None))
            for sessao, _ in sessoes_empresa
        )
        total_usuarios = len(
            [
                usuario
                for usuario in usuarios_empresa
                if int(usuario.nivel_acesso) in _NIVEIS_GERENCIAVEIS_CLIENTE
            ]
        )
        limite_laudos = _obter_limite_laudos_empresa(db, empresa)
        uso_atual = int(getattr(empresa, "mensagens_processadas", 0) or 0)
        uso_percentual = None
        if isinstance(limite_laudos, int) and limite_laudos > 0:
            uso_percentual = min(999, int((uso_atual / limite_laudos) * 100))

        status_value, status_label, status_badge = _classificar_status_empresa(
            empresa,
            admins_cliente=admins_cliente,
        )
        saude_value, saude_label, saude_badge, saude_razao = _classificar_saude_empresa(
            status_value=status_value,
            admins_cliente=admins_cliente,
            inspetores=inspetores,
            revisores=revisores,
            ultimo_acesso_em=ultimo_acesso_em,
            uso_percentual=uso_percentual,
        )
        preview_planos = {
            plano_nome: construir_preview_troca_plano(
                db,
                empresa=empresa,
                novo_plano=plano_nome,
                usuarios_total=total_usuarios,
                uso_atual=uso_atual,
            )
            for plano_nome in (
                PlanoEmpresa.INICIAL.value,
                PlanoEmpresa.INTERMEDIARIO.value,
                PlanoEmpresa.ILIMITADO.value,
            )
        }

        itens.append(
            {
                "id": empresa_id,
                "empresa_id": empresa_id,
                "nome_fantasia": str(getattr(empresa, "nome_fantasia", "") or ""),
                "cnpj": str(getattr(empresa, "cnpj", "") or ""),
                "plano_ativo": str(getattr(empresa, "plano_ativo", "") or ""),
                "plano_sort_priority": int(_PRIORIDADE_PLANO.get(str(getattr(empresa, "plano_ativo", "") or ""), 99)),
                "status_bloqueio": bool(getattr(empresa, "status_bloqueio", False)),
                "status_value": status_value,
                "status_label": status_label,
                "status_badge_class": status_badge,
                "saude_value": saude_value,
                "saude_label": saude_label,
                "saude_badge_class": saude_badge,
                "saude_razao": saude_razao,
                "ultimo_acesso_em": ultimo_acesso_em,
                "ultimo_acesso_label": _formatar_data_admin(ultimo_acesso_em),
                "usuarios_total": total_usuarios,
                "admins_total": len(admins_cliente),
                "inspetores_total": len(inspetores),
                "revisores_total": len(revisores),
                "sessoes_ativas_total": len(sessoes_empresa),
                "uso_atual": uso_atual,
                "uso_percentual": uso_percentual,
                "uso_label": (
                    f"{uso_atual} / {_label_limite(limite_laudos)}"
                    if limite_laudos is not None
                    else f"{uso_atual} / Ilimitado"
                ),
                "limite_plano": limite_laudos,
                "limite_plano_label": _label_limite(limite_laudos),
                "total_laudos": int(totais_laudos_por_empresa.get(empresa_id, 0)),
                "admin_cliente_reset_id": int(admins_cliente[0].id) if admins_cliente else None,
                "motivo_bloqueio": str(getattr(empresa, "motivo_bloqueio", "") or ""),
                "criado_em": _normalizar_datetime_admin(getattr(empresa, "criado_em", None)),
                "criado_em_label": _formatar_data_admin(getattr(empresa, "criado_em", None), fallback="Sem data"),
                "preview_planos": preview_planos,
            }
        )

    status_norm = _normalizar_filtro_status(filtro_status)
    saude_norm = _normalizar_filtro_saude(filtro_saude)
    atividade_norm = _normalizar_filtro_atividade(filtro_atividade)
    if status_norm:
        itens = [item for item in itens if item["status_value"] == status_norm]
    if saude_norm:
        itens = [item for item in itens if item["saude_value"] == saude_norm]
    if atividade_norm:
        itens = [
            item
            for item in itens
            if _atividade_recente_compat(
                ultimo_acesso_em=item["ultimo_acesso_em"],
                filtro_atividade=atividade_norm,
            )
        ]

    ordenar_norm = _normalizar_ordenacao_clientes(ordenar_por)
    direcao_norm = _normalizar_direcao_ordenacao(direcao)
    reverse = direcao_norm == "desc"

    def _sort_key(item: dict[str, Any]) -> Any:
        if ordenar_norm == "criacao":
            return item["criado_em"] or datetime.min.replace(tzinfo=timezone.utc)
        if ordenar_norm == "ultimo_acesso":
            return item["ultimo_acesso_em"] or datetime.min.replace(tzinfo=timezone.utc)
        if ordenar_norm == "plano":
            return (item["plano_sort_priority"], item["nome_fantasia"].lower())
        if ordenar_norm == "saude":
            prioridade_saude = {"critico": 0, "alerta": 1, "ok": 2}
            return (
                prioridade_saude.get(item["saude_value"], 99),
                item["ultimo_acesso_em"] or datetime.min.replace(tzinfo=timezone.utc),
                item["nome_fantasia"].lower(),
            )
        return item["nome_fantasia"].lower()

    itens.sort(key=_sort_key, reverse=reverse)

    total_matching = len(itens)
    pagina_norm = _normalizar_paginacao(pagina, default=1, min_value=1, max_value=999)
    por_pagina_norm = _normalizar_paginacao(por_pagina, default=20, min_value=5, max_value=100)
    total_paginas = max(1, (total_matching + por_pagina_norm - 1) // por_pagina_norm)
    if pagina_norm > total_paginas:
        pagina_norm = total_paginas
    inicio = (pagina_norm - 1) * por_pagina_norm
    fim = inicio + por_pagina_norm

    totais = {
        "clientes_total": total_matching,
        "ativos": sum(1 for item in itens if item["status_value"] == "ativo"),
        "bloqueados": sum(1 for item in itens if item["status_value"] == "bloqueado"),
        "pendentes": sum(1 for item in itens if item["status_value"] == "pendente"),
        "alerta": sum(
            1
            for item in itens
            if item["saude_value"] in {"alerta", "critico"} and item["status_value"] != "bloqueado"
        ),
        "sem_atividade": sum(
            1
            for item in itens
            if _atividade_recente_compat(
                ultimo_acesso_em=item["ultimo_acesso_em"],
                filtro_atividade="sem_atividade",
            )
        ),
    }

    return {
        "itens": itens[inicio:fim],
        "totais": totais,
        "pagination": {
            "page": pagina_norm,
            "page_size": por_pagina_norm,
            "total_items": total_matching,
            "total_pages": total_paginas,
            "has_prev": pagina_norm > 1,
            "has_next": pagina_norm < total_paginas,
            "pages": list(range(max(1, pagina_norm - 2), min(total_paginas, pagina_norm + 2) + 1)),
        },
        "filtros": {
            "nome": nome,
            "codigo": codigo,
            "plano": plano,
            "status": status_norm,
            "saude": saude_norm,
            "atividade": atividade_norm,
            "ordenar": ordenar_norm,
            "direcao": direcao_norm,
            "por_pagina": por_pagina_norm,
        },
    }


def buscar_detalhe_cliente(
    db: Session,
    empresa_id: int,
    *,
    portfolio_summary_fn: Callable[..., dict[str, Any]],
    tenant_admin_policy_summary_fn: Callable[[Any], dict[str, Any]],
    user_serializer: Callable[..., dict[str, Any]],
    first_access_summary_fn: Callable[..., dict[str, Any]],
    signatory_serializer: Callable[..., dict[str, Any]],
) -> dict[str, Any] | None:
    empresa = db.scalar(select(Empresa).where(Empresa.id == empresa_id, _tenant_cliente_clause()))
    if not empresa:
        return None

    contexto = _coletar_contexto_empresas(db, empresa_ids=[int(empresa_id)])
    usuarios_empresa = list(contexto["usuarios_por_empresa"].get(int(empresa_id), []))
    sessoes_empresa = list(contexto["sessoes_por_empresa"].get(int(empresa_id), []))

    admins_cliente = [
        usuario for usuario in usuarios_empresa if int(usuario.nivel_acesso) == int(NivelAcesso.ADMIN_CLIENTE)
    ]
    inspetores = [
        usuario for usuario in usuarios_empresa if int(usuario.nivel_acesso) == int(NivelAcesso.INSPETOR)
    ]
    revisores = [
        usuario for usuario in usuarios_empresa if int(usuario.nivel_acesso) == int(NivelAcesso.REVISOR)
    ]
    usuarios_operacionais = [
        usuario
        for usuario in usuarios_empresa
        if int(usuario.nivel_acesso) in {int(NivelAcesso.INSPETOR), int(NivelAcesso.REVISOR)}
    ]

    stmt_stats = select(
        func.count(Laudo.id).label("total"),
        func.coalesce(func.sum(Laudo.custo_api_reais), 0).label("custo"),
    ).where(Laudo.empresa_id == empresa_id)
    stats = db.execute(stmt_stats).one()

    limite_usuarios = _obter_limite_usuarios_empresa(db, empresa)
    limite_laudos = _obter_limite_laudos_empresa(db, empresa)
    uso_atual = int(getattr(empresa, "mensagens_processadas", 0) or 0)
    uso_pct = None
    if isinstance(limite_laudos, int) and limite_laudos > 0:
        uso_pct = min(999, int((uso_atual / limite_laudos) * 100))

    ultimo_acesso_em = _max_datetime_admin(
        _normalizar_datetime_admin(getattr(sessao, "ultima_atividade_em", None))
        for sessao, _ in sessoes_empresa
    )
    status_value, status_label, status_badge = _classificar_status_empresa(
        empresa,
        admins_cliente=admins_cliente,
    )
    saude_value, saude_label, saude_badge, saude_razao = _classificar_saude_empresa(
        status_value=status_value,
        admins_cliente=admins_cliente,
        inspetores=inspetores,
        revisores=revisores,
        ultimo_acesso_em=ultimo_acesso_em,
        uso_percentual=uso_pct,
    )

    sessoes_por_usuario: dict[int, list[SessaoAtiva]] = defaultdict(list)
    sessoes_ativas = []
    for sessao, usuario in sessoes_empresa:
        sessoes_por_usuario[int(usuario.id)].append(sessao)
        ultima_atividade_em = _normalizar_datetime_admin(getattr(sessao, "ultima_atividade_em", None))
        expira_em = _normalizar_datetime_admin(getattr(sessao, "expira_em", None))
        sessoes_ativas.append(
            {
                "token": str(getattr(sessao, "token", "") or ""),
                "usuario_id": int(usuario.id),
                "usuario_nome": str(getattr(usuario, "nome_completo", "") or ""),
                "usuario_email": str(getattr(usuario, "email", "") or ""),
                "role_label": _role_label(int(getattr(usuario, "nivel_acesso", 0) or 0)),
                "ultima_atividade_em": ultima_atividade_em,
                "ultima_atividade_label": _formatar_data_admin(ultima_atividade_em),
                "expira_em": expira_em,
                "expira_em_label": _formatar_data_admin(expira_em, fallback="Sem expiração"),
            }
        )

    admins_cliente_proj = [
        user_serializer(usuario, sessoes_usuario=sessoes_por_usuario.get(int(usuario.id), []))
        for usuario in admins_cliente
    ]
    usuarios_operacionais_proj = [
        user_serializer(usuario, sessoes_usuario=sessoes_por_usuario.get(int(usuario.id), []))
        for usuario in usuarios_operacionais
    ]

    plan_change_preview = {
        plano_nome: construir_preview_troca_plano(
            db,
            empresa=empresa,
            novo_plano=plano_nome,
            usuarios_total=len(
                [item for item in usuarios_empresa if int(item.nivel_acesso) in _NIVEIS_GERENCIAVEIS_CLIENTE]
            ),
            uso_atual=uso_atual,
        )
        for plano_nome in (
            PlanoEmpresa.INICIAL.value,
            PlanoEmpresa.INTERMEDIARIO.value,
            PlanoEmpresa.ILIMITADO.value,
        )
    }

    auditoria_recente = list(
        db.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(RegistroAuditoriaEmpresa.empresa_id == empresa_id)
            .order_by(RegistroAuditoriaEmpresa.criado_em.desc())
            .limit(20)
        ).all()
    )
    falhas_recentes = [
        registro
        for registro in auditoria_recente
        if "erro" in str(getattr(registro, "acao", "") or "").lower()
        or "falha" in str(getattr(registro, "resumo", "") or "").lower()
    ]
    try:
        portfolio_catalogo = portfolio_summary_fn(db, empresa_id=int(empresa_id))
    except Exception:
        logger.exception(
            "Falha ao resumir portfólio comercial do tenant no detalhe administrativo",
            extra={"empresa_id": int(empresa_id)},
        )
        portfolio_catalogo = {
            "families": [],
            "active_activation_count": 0,
            "active_family_count": 0,
            "governed_mode": False,
            "managed_by_admin_ceo": False,
            "catalog_state": "unavailable",
            "permissions": {},
            "available_variant_count": 0,
            "operational_variant_count": 0,
        }
    family_labels = {
        str(item.get("family_key") or "").strip().lower(): str(item.get("family_label") or "").strip()
        for item in list(portfolio_catalogo.get("families", []) or [])
        if str(item.get("family_key") or "").strip()
    }
    signatarios_governados = list(
        db.scalars(
            select(SignatarioGovernadoLaudo)
            .where(SignatarioGovernadoLaudo.tenant_id == int(empresa_id))
            .order_by(SignatarioGovernadoLaudo.ativo.desc(), SignatarioGovernadoLaudo.nome.asc())
        ).all()
    )

    return {
        "empresa": empresa,
        "primeiro_acesso_empresa": first_access_summary_fn(
            empresa=empresa,
            admins_cliente=admins_cliente_proj,
        ),
        "admin_cliente_policy": tenant_admin_policy_summary_fn(
            getattr(empresa, "admin_cliente_policy_json", None)
        ),
        "admins_cliente": admins_cliente_proj,
        "inspetores": inspetores,
        "revisores": revisores,
        "inspetores_e_revisores": usuarios_operacionais_proj,
        "usuarios": usuarios_empresa,
        "laudos_recentes": [],
        "limite_plano": limite_laudos,
        "limite_usuarios": limite_usuarios,
        "uso_percentual": uso_pct,
        "uso_atual": uso_atual,
        "total_laudos": int(stats.total or 0),
        "custo_total": stats.custo or Decimal("0"),
        "status_admin": {
            "value": status_value,
            "label": status_label,
            "badge_class": status_badge,
            "motivo_bloqueio": str(getattr(empresa, "motivo_bloqueio", "") or ""),
            "bloqueado_em": getattr(empresa, "bloqueado_em", None),
            "bloqueado_em_label": _formatar_data_admin(
                getattr(empresa, "bloqueado_em", None),
                fallback="Sem bloqueio",
            ),
        },
        "saude_admin": {
            "value": saude_value,
            "label": saude_label,
            "badge_class": saude_badge,
            "razao": saude_razao,
        },
        "seguranca": {
            "total_sessoes_ativas": len(sessoes_ativas),
            "usuarios_com_sessao_ativa": len({item["usuario_id"] for item in sessoes_ativas}),
            "usuarios_bloqueados": len(
                [usuario for usuario in usuarios_empresa if bool(getattr(usuario, "status_bloqueio", False))]
            ),
            "usuarios_troca_senha_pendente": len(
                [usuario for usuario in usuarios_empresa if bool(getattr(usuario, "senha_temporaria_ativa", False))]
            ),
            "ultimo_acesso_em": ultimo_acesso_em,
            "ultimo_acesso_label": _formatar_data_admin(ultimo_acesso_em),
            "sessoes_ativas": sessoes_ativas,
        },
        "plano_preview": plan_change_preview,
        "resumo_operacional": {
            "usuarios_total": len(
                [usuario for usuario in usuarios_empresa if int(usuario.nivel_acesso) in _NIVEIS_GERENCIAVEIS_CLIENTE]
            ),
            "admins_total": len(admins_cliente_proj),
            "inspetores_total": len(inspetores),
            "revisores_total": len(revisores),
            "limite_usuarios_label": _label_limite(limite_usuarios),
            "limite_laudos_label": _label_limite(limite_laudos),
            "uso_label": (
                f"{uso_atual} / {_label_limite(limite_laudos)}"
                if limite_laudos is not None
                else f"{uso_atual} / Ilimitado"
            ),
        },
        "falhas_recentes": falhas_recentes,
        "portfolio_catalogo": portfolio_catalogo,
        "signatarios_governados": [
            signatory_serializer(item, family_labels=family_labels)
            for item in signatarios_governados
        ],
        "signatario_family_options": [
            {
                "family_key": family_key,
                "family_label": label or family_key,
            }
            for family_key, label in sorted(family_labels.items())
        ],
    }
