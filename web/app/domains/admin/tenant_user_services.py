"""Serviços e validações de usuários gerenciáveis do tenant cliente."""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.shared.database import (
    AnexoMesa,
    AprendizadoVisualIa,
    ConfiguracaoPlataforma,
    Empresa,
    Laudo,
    MensagemLaudo,
    NivelAcesso,
    RegistroAuditoriaEmpresa,
    TemplateLaudo,
    Usuario,
    commit_ou_rollback_integridade,
    flush_ou_rollback_integridade,
)
from app.shared.security import (
    criar_hash_senha,
    encerrar_todas_sessoes_usuario,
    gerar_senha_fortificada,
)
from app.shared.tenant_admin_policy import (
    tenant_admin_enforces_single_operational_user,
    tenant_admin_forbidden_user_portal_grants,
    tenant_admin_normalize_user_portal_grants,
    tenant_admin_operational_user_limit,
)

logger = logging.getLogger("tariel.saas")
_HTML_SAFE_PASSWORD_TRANSLATION = str.maketrans(
    {
        "&": "@",
        "<": "A",
        ">": "Z",
        '"': "X",
        "'": "Y",
    }
)

_NIVEIS_GERENCIAVEIS_CLIENTE = frozenset(
    {
        int(NivelAcesso.ADMIN_CLIENTE),
        int(NivelAcesso.INSPETOR),
        int(NivelAcesso.REVISOR),
    }
)
_NIVEIS_OPERACIONAIS_CLIENTE = frozenset(
    {
        int(NivelAcesso.INSPETOR),
        int(NivelAcesso.REVISOR),
    }
)


def _gerar_senha_temporaria() -> str:
    # Mantém compatibilidade com testes e automações que monkeypatcham
    # `app.domains.admin.services.gerar_senha_fortificada`.
    try:
        from app.domains.admin import services as admin_services
    except Exception:
        return gerar_senha_fortificada()

    gerador = getattr(admin_services, "gerar_senha_fortificada", None)
    if callable(gerador):
        senha = str(gerador())
    else:
        senha = gerar_senha_fortificada()
    return senha.translate(_HTML_SAFE_PASSWORD_TRANSLATION)


def _normalizar_email(email: str) -> str:
    valor = str(email or "").strip().lower()
    if not valor:
        raise ValueError("E-mail obrigatório.")
    return valor


def _normalizar_texto_curto(valor: str, *, campo: str, max_len: int) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise ValueError(f"{campo} é obrigatório.")
    return texto[:max_len]


def _normalizar_texto_opcional(valor: Any, max_len: int | None = None) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    if max_len is not None:
        return texto[:max_len]
    return texto


def _normalizar_crea(valor: str) -> str | None:
    texto = str(valor or "").strip().upper()
    if not texto:
        return None

    texto = re.sub(r"\s+", "", texto)
    if len(texto) > 40:
        raise ValueError("CREA inválido. Limite de 40 caracteres.")

    if not re.fullmatch(r"[A-Z0-9./-]+", texto):
        raise ValueError("CREA inválido. Use apenas letras, números, ponto, barra e hífen.")

    return texto


def _normalizar_nivel_cliente(valor: str | int | NivelAcesso) -> int:
    nivel = NivelAcesso.normalizar(valor)
    if nivel not in _NIVEIS_GERENCIAVEIS_CLIENTE:
        raise ValueError("Perfil inválido para gestão do cliente.")
    return int(nivel)


def filtro_usuarios_gerenciaveis_cliente():
    return Usuario.nivel_acesso.in_(tuple(_NIVEIS_GERENCIAVEIS_CLIENTE))


def filtro_usuarios_operacionais_cliente():
    return Usuario.nivel_acesso.in_(tuple(_NIVEIS_OPERACIONAIS_CLIENTE))


def _buscar_empresa(db: Session, empresa_id: int) -> Empresa:
    empresa = db.scalar(
        select(Empresa).where(
            Empresa.id == empresa_id,
            Empresa.escopo_plataforma.is_not(True),
        )
    )
    if not empresa:
        raise ValueError("Empresa não encontrada.")
    return empresa


def _buscar_usuario_empresa(db: Session, empresa_id: int, usuario_id: int) -> Usuario:
    usuario = db.scalar(
        select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.empresa_id == empresa_id,
            filtro_usuarios_gerenciaveis_cliente(),
        )
    )
    if not usuario:
        raise ValueError("Usuário não encontrado para esta empresa.")
    return usuario


def _contar_usuarios_empresa(db: Session, empresa_id: int) -> int:
    return (
        db.scalar(
            select(func.count(Usuario.id)).where(
                Usuario.empresa_id == empresa_id,
                filtro_usuarios_gerenciaveis_cliente(),
            )
        )
        or 0
    )


def _contar_usuarios_operacionais_empresa(db: Session, empresa_id: int) -> int:
    return (
        db.scalar(
            select(func.count(Usuario.id)).where(
                Usuario.empresa_id == int(empresa_id),
                filtro_usuarios_operacionais_cliente(),
            )
        )
        or 0
    )


def _usuario_usa_slot_operacional(
    *,
    empresa: Empresa,
    nivel_acesso: int,
    allowed_portals: Any,
) -> bool:
    effective_grants = tenant_admin_normalize_user_portal_grants(
        getattr(empresa, "admin_cliente_policy_json", None),
        access_level=nivel_acesso,
        requested_portals=allowed_portals,
    )
    return bool({"inspetor", "revisor"} & set(effective_grants))


def _contar_slots_operacionais_empresa(
    db: Session,
    *,
    empresa: Empresa,
    ignorar_usuario_id: int | None = None,
) -> int:
    usuarios_empresa = list(
        db.scalars(
            select(Usuario).where(
                Usuario.empresa_id == int(empresa.id),
                filtro_usuarios_gerenciaveis_cliente(),
            )
        ).all()
    )
    total = 0
    for usuario in usuarios_empresa:
        if ignorar_usuario_id is not None and int(usuario.id) == int(ignorar_usuario_id):
            continue
        if _usuario_usa_slot_operacional(
            empresa=empresa,
            nivel_acesso=int(getattr(usuario, "nivel_acesso", 0) or 0),
            allowed_portals=getattr(usuario, "allowed_portals", ()),
        ):
            total += 1
    return total


def _normalizar_allowed_portals_usuario_empresa(
    *,
    empresa: Empresa,
    nivel_acesso: int,
    allowed_portals: Any = None,
) -> list[str]:
    forbidden = tenant_admin_forbidden_user_portal_grants(
        getattr(empresa, "admin_cliente_policy_json", None),
        access_level=nivel_acesso,
        requested_portals=allowed_portals,
    )
    if forbidden:
        labels = ", ".join(str(item).strip() for item in forbidden if str(item).strip())
        raise ValueError(
            "Este tenant não permite conceder acesso a: "
            f"{labels or 'portal solicitado'}."
        )
    return tenant_admin_normalize_user_portal_grants(
        getattr(empresa, "admin_cliente_policy_json", None),
        access_level=nivel_acesso,
        requested_portals=allowed_portals,
    )


def _validar_capacidade_novo_usuario(db: Session, empresa: Empresa) -> None:
    limite = empresa.obter_limites(db).usuarios_max
    if limite is None:
        return

    total_atual = _contar_usuarios_empresa(db, int(empresa.id))
    if total_atual >= limite:
        raise ValueError(f"Limite de usuários do plano atingido ({limite}).")


def _validar_limite_operacional_por_pacote_tenant(
    db: Session,
    *,
    empresa: Empresa,
    nivel_acesso: int,
    allowed_portals: Any = None,
    ignorar_usuario_id: int | None = None,
) -> None:
    if not _usuario_usa_slot_operacional(
        empresa=empresa,
        nivel_acesso=int(nivel_acesso),
        allowed_portals=allowed_portals,
    ):
        return

    policy = getattr(empresa, "admin_cliente_policy_json", None)
    if not tenant_admin_enforces_single_operational_user(policy):
        return

    limite_operacional = tenant_admin_operational_user_limit(policy) or 1
    total_operacional = _contar_slots_operacionais_empresa(
        db,
        empresa=empresa,
        ignorar_usuario_id=ignorar_usuario_id,
    )
    if total_operacional >= limite_operacional:
        raise ValueError(
            "Limite operacional do pacote mobile principal com operador único atingido. "
            "Mantenha apenas 1 conta operacional cadastrada nesta empresa."
        )


def resetar_senha_inspetor(db: Session, usuario_id: int) -> str:
    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id))
    if not usuario:
        raise ValueError("Usuário não encontrado.")

    nova_senha = _gerar_senha_temporaria()
    usuario.senha_hash = criar_hash_senha(nova_senha)
    usuario.tentativas_login = 0
    usuario.bloqueado_ate = None
    usuario.status_bloqueio = False
    usuario.senha_temporaria_ativa = True

    commit_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível resetar a senha do usuário.",
    )
    sessoes_encerradas = encerrar_todas_sessoes_usuario(int(usuario.id))
    if sessoes_encerradas:
        logger.info(
            "Sessões encerradas após reset de senha | usuario_id=%s | removidas=%s",
            usuario.id,
            sessoes_encerradas,
        )
    return nova_senha


def resetar_senha_usuario_empresa(db: Session, empresa_id: int, usuario_id: int) -> str:
    usuario = _buscar_usuario_empresa(db, empresa_id, usuario_id)
    return resetar_senha_inspetor(db, int(usuario.id))


def forcar_troca_senha_usuario_empresa(db: Session, empresa_id: int, usuario_id: int) -> Usuario:
    usuario = _buscar_usuario_empresa(db, empresa_id, usuario_id)
    usuario.senha_temporaria_ativa = True
    usuario.tentativas_login = 0
    usuario.status_bloqueio = False
    usuario.bloqueado_ate = None

    commit_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível marcar troca obrigatória de senha para o usuário.",
    )
    encerrar_todas_sessoes_usuario(int(usuario.id))
    return usuario


def atualizar_crea_revisor(db: Session, empresa_id: int, usuario_id: int, crea: str) -> Usuario:
    usuario = _buscar_usuario_empresa(db, empresa_id, usuario_id)

    if int(usuario.nivel_acesso) != int(NivelAcesso.REVISOR):
        raise ValueError("Somente usuários revisores aceitam cadastro de CREA.")

    usuario.crea = _normalizar_crea(crea)
    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível atualizar o CREA do revisor.",
    )
    return usuario


def adicionar_inspetor(db: Session, empresa_id: int, nome: str, email: str) -> str:
    return criar_usuario_empresa(
        db,
        empresa_id=empresa_id,
        nome=nome,
        email=email,
        nivel_acesso=NivelAcesso.INSPETOR,
    )[1]


def criar_usuario_empresa(
    db: Session,
    *,
    empresa_id: int,
    nome: str,
    email: str,
    nivel_acesso: str | int | NivelAcesso,
    telefone: str = "",
    crea: str = "",
    allowed_portals: Any = None,
) -> tuple[Usuario, str]:
    empresa = _buscar_empresa(db, empresa_id)
    _validar_capacidade_novo_usuario(db, empresa)

    email_norm = _normalizar_email(email)
    nome_norm = _normalizar_texto_curto(nome, campo="Nome do usuário", max_len=150)
    nivel_norm = _normalizar_nivel_cliente(nivel_acesso)
    allowed_portals_norm = _normalizar_allowed_portals_usuario_empresa(
        empresa=empresa,
        nivel_acesso=nivel_norm,
        allowed_portals=allowed_portals,
    )
    _validar_limite_operacional_por_pacote_tenant(
        db,
        empresa=empresa,
        nivel_acesso=nivel_norm,
        allowed_portals=allowed_portals_norm,
    )

    if db.scalar(select(Usuario).where(Usuario.email == email_norm)):
        raise ValueError("E-mail já cadastrado.")

    senha = _gerar_senha_temporaria()

    novo = Usuario(
        empresa_id=empresa_id,
        nome_completo=nome_norm,
        email=email_norm,
        telefone=_normalizar_texto_opcional(telefone, 30),
        crea=(
            _normalizar_crea(crea)
            if "revisor" in allowed_portals_norm
            else None
        ),
        senha_hash=criar_hash_senha(senha),
        nivel_acesso=nivel_norm,
        ativo=True,
        senha_temporaria_ativa=True,
        allowed_portals_json=allowed_portals_norm,
    )
    db.add(novo)

    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível adicionar o usuário da empresa.",
    )
    logger.info(
        "Usuário da empresa criado | empresa_id=%s | usuario_id=%s | nivel=%s",
        empresa_id,
        novo.id,
        nivel_norm,
    )
    return novo, senha


def alternar_bloqueio_usuario_empresa(db: Session, empresa_id: int, usuario_id: int) -> Usuario:
    usuario = _buscar_usuario_empresa(db, empresa_id, usuario_id)
    usuario.ativo = not bool(usuario.ativo)

    if usuario.ativo:
        usuario.status_bloqueio = False
        usuario.bloqueado_ate = None
        usuario.tentativas_login = 0
    else:
        usuario.status_bloqueio = True
        usuario.bloqueado_ate = None

    commit_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível alterar o bloqueio do usuário.",
    )
    encerrar_todas_sessoes_usuario(int(usuario.id))
    return usuario


def excluir_usuario_empresa(db: Session, empresa_id: int, usuario_id: int) -> dict[str, object]:
    usuario = _buscar_usuario_empresa(db, empresa_id, usuario_id)
    payload = {
        "usuario_id": int(usuario.id),
        "nome": str(getattr(usuario, "nome", "") or getattr(usuario, "nome_completo", "") or "").strip(),
        "email": str(getattr(usuario, "email", "") or "").strip(),
        "nivel_acesso": int(getattr(usuario, "nivel_acesso", 0) or 0),
    }

    db.query(Laudo).filter(Laudo.usuario_id == int(usuario.id)).update({"usuario_id": None}, synchronize_session=False)
    db.query(Laudo).filter(Laudo.revisado_por == int(usuario.id)).update({"revisado_por": None}, synchronize_session=False)
    db.query(MensagemLaudo).filter(MensagemLaudo.remetente_id == int(usuario.id)).update({"remetente_id": None}, synchronize_session=False)
    db.query(MensagemLaudo).filter(MensagemLaudo.resolvida_por_id == int(usuario.id)).update({"resolvida_por_id": None}, synchronize_session=False)
    db.query(AnexoMesa).filter(AnexoMesa.enviado_por_id == int(usuario.id)).update({"enviado_por_id": None}, synchronize_session=False)
    db.query(TemplateLaudo).filter(TemplateLaudo.criado_por_id == int(usuario.id)).update({"criado_por_id": None}, synchronize_session=False)
    db.query(AprendizadoVisualIa).filter(AprendizadoVisualIa.criado_por_id == int(usuario.id)).update({"criado_por_id": None}, synchronize_session=False)
    db.query(AprendizadoVisualIa).filter(AprendizadoVisualIa.validado_por_id == int(usuario.id)).update({"validado_por_id": None}, synchronize_session=False)
    db.query(RegistroAuditoriaEmpresa).filter(
        RegistroAuditoriaEmpresa.ator_usuario_id == int(usuario.id)
    ).update({"ator_usuario_id": None}, synchronize_session=False)
    db.query(RegistroAuditoriaEmpresa).filter(
        RegistroAuditoriaEmpresa.alvo_usuario_id == int(usuario.id)
    ).update({"alvo_usuario_id": None}, synchronize_session=False)
    db.query(ConfiguracaoPlataforma).filter(
        ConfiguracaoPlataforma.atualizada_por_usuario_id == int(usuario.id)
    ).update({"atualizada_por_usuario_id": None}, synchronize_session=False)

    db.delete(usuario)
    commit_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível excluir o usuário da empresa.",
    )
    encerrar_todas_sessoes_usuario(int(usuario.id))
    return payload


def atualizar_usuario_empresa(
    db: Session,
    *,
    empresa_id: int,
    usuario_id: int,
    nome: str | None = None,
    email: str | None = None,
    telefone: str | None = None,
    crea: str | None = None,
    allowed_portals: Any = None,
) -> Usuario:
    empresa = _buscar_empresa(db, empresa_id)
    usuario = _buscar_usuario_empresa(db, empresa_id, usuario_id)

    if nome is not None:
        usuario.nome_completo = _normalizar_texto_curto(nome, campo="Nome do usuário", max_len=150)

    if email is not None:
        email_norm = _normalizar_email(email)
        existente = db.scalar(select(Usuario).where(Usuario.email == email_norm, Usuario.id != usuario.id))
        if existente:
            raise ValueError("E-mail já cadastrado.")
        usuario.email = email_norm

    if telefone is not None:
        usuario.telefone = _normalizar_texto_opcional(telefone, 30)

    allowed_portals_norm = _normalizar_allowed_portals_usuario_empresa(
        empresa=empresa,
        nivel_acesso=int(usuario.nivel_acesso),
        allowed_portals=getattr(usuario, "allowed_portals", ()) if allowed_portals is None else allowed_portals,
    )
    _validar_limite_operacional_por_pacote_tenant(
        db,
        empresa=empresa,
        nivel_acesso=int(usuario.nivel_acesso),
        allowed_portals=allowed_portals_norm,
        ignorar_usuario_id=int(usuario.id),
    )
    usuario.allowed_portals_json = allowed_portals_norm

    if crea is not None:
        if "revisor" not in allowed_portals_norm:
            raise ValueError("Somente revisores aceitam cadastro de CREA.")
        usuario.crea = _normalizar_crea(crea)
    elif "revisor" not in allowed_portals_norm and int(usuario.nivel_acesso) != int(NivelAcesso.REVISOR):
        usuario.crea = None

    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível atualizar o usuário da empresa.",
    )
    return usuario


__all__ = [
    "_NIVEIS_GERENCIAVEIS_CLIENTE",
    "_NIVEIS_OPERACIONAIS_CLIENTE",
    "_buscar_empresa",
    "_buscar_usuario_empresa",
    "_contar_slots_operacionais_empresa",
    "_contar_usuarios_empresa",
    "_contar_usuarios_operacionais_empresa",
    "_normalizar_allowed_portals_usuario_empresa",
    "_normalizar_crea",
    "_normalizar_email",
    "_normalizar_nivel_cliente",
    "_normalizar_texto_curto",
    "_normalizar_texto_opcional",
    "_validar_capacidade_novo_usuario",
    "_validar_limite_operacional_por_pacote_tenant",
    "adicionar_inspetor",
    "alternar_bloqueio_usuario_empresa",
    "atualizar_crea_revisor",
    "atualizar_usuario_empresa",
    "criar_usuario_empresa",
    "excluir_usuario_empresa",
    "filtro_usuarios_gerenciaveis_cliente",
    "filtro_usuarios_operacionais_cliente",
    "forcar_troca_senha_usuario_empresa",
    "resetar_senha_inspetor",
    "resetar_senha_usuario_empresa",
]
