"""Tenant onboarding services for the admin domain."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.admin.tenant_client_write_services import (
    _normalizar_politica_admin_cliente_empresa,
)
from app.domains.admin.tenant_plan_services import _normalizar_plano
from app.domains.admin.tenant_user_services import (
    _normalizar_email,
    _normalizar_texto_curto,
    _normalizar_texto_opcional,
    criar_usuario_empresa,
)
from app.shared.backend_hotspot_metrics import observe_backend_hotspot
from app.shared.database import (
    Empresa,
    NivelAcesso,
    Usuario,
    commit_ou_rollback_integridade,
)
from app.shared.security import criar_hash_senha, gerar_senha_fortificada
from app.shared.tenant_admin_policy import tenant_admin_default_admin_cliente_portal_grants

logger = logging.getLogger("tariel.saas")


def _flag_ligada(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor or "").strip().lower() in {"1", "true", "on", "sim", "yes"}


def _nome_padrao_operacional(tipo: str, empresa_nome: str) -> str:
    if tipo == "revisor":
        return f"Equipe de analise {empresa_nome}"
    return f"Equipe de campo {empresa_nome}"


def _serializar_credencial_onboarding_operacional(
    usuario: Usuario,
    *,
    senha: str,
) -> dict[str, Any]:
    papel = "Equipe de analise" if int(usuario.nivel_acesso) == int(NivelAcesso.REVISOR) else "Equipe de campo"
    return {
        "usuario_id": int(usuario.id),
        "usuario_nome": str(
            getattr(usuario, "nome", None)
            or getattr(usuario, "nome_completo", None)
            or f"Usuário #{usuario.id}"
        ),
        "papel": papel,
        "login": str(usuario.email or ""),
        "senha": str(senha or ""),
        "allowed_portals": list(getattr(usuario, "allowed_portals", ())),
    }


def _aviso_notificacao_boas_vindas() -> str:
    return "Entrega automática de boas-vindas não configurada. Compartilhe a credencial por canal seguro."


def _disparar_email_boas_vindas(
    email: str,
    empresa: str,
    senha: str,
    *,
    notification_backend: str,
    logger_operacao: logging.Logger | None = None,
    aviso_factory: Callable[[], str] = _aviso_notificacao_boas_vindas,
) -> str | None:
    """
    Backend operacional minimo para onboarding:
    - `log`: registra metadados redigidos e devolve aviso para o operador.
    - `noop`: nao tenta enviar, mas devolve aviso explicito para o operador.
    - `strict`: falha explicitamente para nao mascarar ausencia de entrega.
    """

    logger_ref = logger_operacao or logger
    aviso = aviso_factory()

    if notification_backend == "log":
        logger_ref.info(
            "\n=========================================\n"
            "[BACKEND LOG] BOAS-VINDAS INTERCEPTADO\n"
            f"Empresa: {empresa}\n"
            f"E-mail:  {email}\n"
            "Credencial temporaria: [REDACTED]\n"
            "Acao:    compartilhe a credencial por canal seguro.\n"
            "=========================================\n"
        )
        return aviso

    if notification_backend == "noop":
        logger_ref.info(
            "Entrega automatica de boas-vindas desativada | empresa=%s | email=%s",
            empresa,
            email,
        )
        return aviso

    if notification_backend == "strict":
        raise RuntimeError(aviso)

    raise RuntimeError(
        "Backend de boas-vindas inválido. Use ADMIN_WELCOME_NOTIFICATION_BACKEND=log|noop|strict."
    )


def registrar_novo_cliente(
    db: Session,
    nome: str,
    cnpj: str,
    email_admin: str,
    plano: str,
    segmento: str = "",
    cidade_estado: str = "",
    nome_responsavel: str = "",
    observacoes: str = "",
    admin_cliente_case_visibility_mode: str = "",
    admin_cliente_case_action_mode: str = "",
    admin_cliente_operating_model: str = "",
    admin_cliente_mobile_web_inspector_enabled: str | bool = "",
    admin_cliente_mobile_web_review_enabled: str | bool = "",
    admin_cliente_operational_user_cross_portal_enabled: str | bool = "",
    admin_cliente_operational_user_admin_portal_enabled: str | bool = "",
    provisionar_inspetor_inicial: str | bool = "",
    inspetor_nome: str = "",
    inspetor_email: str = "",
    inspetor_telefone: str = "",
    provisionar_revisor_inicial: str | bool = "",
    revisor_nome: str = "",
    revisor_email: str = "",
    revisor_telefone: str = "",
    revisor_crea: str = "",
    *,
    normalizar_cnpj_fn: Callable[[str], str],
    welcome_email_fn: Callable[[str, str, str], str | None],
    password_generator: Callable[[], str] = gerar_senha_fortificada,
) -> tuple[Empresa, str, str | None]:
    with observe_backend_hotspot(
        "admin_tenant_onboarding",
        surface="admin_ceo",
        route_path="service:registrar_novo_cliente",
        method="SERVICE",
        detail={
            "provision_inspetor": bool(provisionar_inspetor_inicial),
            "provision_revisor": bool(provisionar_revisor_inicial),
        },
    ) as hotspot:
        nome_norm = _normalizar_texto_curto(nome, campo="Nome da empresa", max_len=200)
        cnpj_norm = normalizar_cnpj_fn(cnpj)
        email_norm = _normalizar_email(email_admin)
        plano_norm = _normalizar_plano(plano)

        if db.scalar(select(Empresa).where(Empresa.cnpj == cnpj_norm)):
            raise ValueError("CNPJ já cadastrado no sistema.")

        if db.scalar(select(Usuario).where(Usuario.email == email_norm)):
            raise ValueError("E-mail já em uso.")

        nova_empresa = Empresa(
            nome_fantasia=nome_norm,
            cnpj=cnpj_norm,
            plano_ativo=plano_norm,
            escopo_plataforma=False,
            admin_cliente_policy_json=_normalizar_politica_admin_cliente_empresa(
                case_visibility_mode=admin_cliente_case_visibility_mode,
                case_action_mode=admin_cliente_case_action_mode,
                operating_model=admin_cliente_operating_model,
                mobile_web_inspector_enabled=admin_cliente_mobile_web_inspector_enabled,
                mobile_web_review_enabled=admin_cliente_mobile_web_review_enabled,
                operational_user_cross_portal_enabled=admin_cliente_operational_user_cross_portal_enabled,
                operational_user_admin_portal_enabled=admin_cliente_operational_user_admin_portal_enabled,
            ),
            segmento=_normalizar_texto_opcional(segmento, 100),
            cidade_estado=_normalizar_texto_opcional(cidade_estado, 100),
            nome_responsavel=_normalizar_texto_opcional(nome_responsavel, 150),
            observacoes=_normalizar_texto_opcional(observacoes),
        )
        db.add(nova_empresa)

        try:
            db.flush()
        except IntegrityError as erro:
            db.rollback()
            logger.warning(
                "Falha ao criar empresa no onboarding | nome=%s cnpj=%s erro=%s",
                nome_norm,
                cnpj_norm,
                erro,
            )
            raise ValueError("Falha ao reservar registro da empresa.") from erro

        hotspot.tenant_id = int(getattr(nova_empresa, "id", 0) or 0) or None
        senha_plana = password_generator()

        usuario_admin = Usuario(
            empresa_id=nova_empresa.id,
            nome_completo=f"Administrador {nome_norm}",
            email=email_norm,
            senha_hash=criar_hash_senha(senha_plana),
            nivel_acesso=int(NivelAcesso.ADMIN_CLIENTE),
            ativo=True,
            senha_temporaria_ativa=True,
            allowed_portals_json=tenant_admin_default_admin_cliente_portal_grants(
                nova_empresa.admin_cliente_policy_json
            ),
        )
        db.add(usuario_admin)

        credenciais_operacionais_onboarding: list[dict[str, Any]] = []
        provisionamentos_operacionais: tuple[dict[str, Any], ...] = (
            {
                "habilitado": _flag_ligada(provisionar_inspetor_inicial),
                "nome": inspetor_nome,
                "email": inspetor_email,
                "telefone": inspetor_telefone,
                "crea": "",
                "nivel": NivelAcesso.INSPETOR,
                "tipo": "inspetor",
            },
            {
                "habilitado": _flag_ligada(provisionar_revisor_inicial),
                "nome": revisor_nome,
                "email": revisor_email,
                "telefone": revisor_telefone,
                "crea": revisor_crea,
                "nivel": NivelAcesso.REVISOR,
                "tipo": "revisor",
            },
        )
        provisionados: list[str] = ["admin_cliente"]
        for provisionamento in provisionamentos_operacionais:
            if not provisionamento["habilitado"]:
                continue

            email_operacional = _normalizar_email(str(provisionamento["email"] or ""))
            if not email_operacional:
                papel = "equipe de analise" if provisionamento["tipo"] == "revisor" else "equipe de campo"
                raise ValueError(f"Informe o e-mail da {papel} inicial.")

            nome_operacional = _normalizar_texto_curto(
                str(provisionamento["nome"] or _nome_padrao_operacional(provisionamento["tipo"], nome_norm)),
                campo="Nome do usuário",
                max_len=150,
            )
            usuario_operacional, senha_operacional = criar_usuario_empresa(
                db,
                empresa_id=int(nova_empresa.id),
                nome=nome_operacional,
                email=email_operacional,
                nivel_acesso=provisionamento["nivel"],
                telefone=str(provisionamento["telefone"] or ""),
                crea=str(provisionamento["crea"] or ""),
            )
            credenciais_operacionais_onboarding.append(
                _serializar_credencial_onboarding_operacional(
                    usuario_operacional,
                    senha=senha_operacional,
                )
            )
            provisionados.append(str(provisionamento["tipo"]))

        commit_ou_rollback_integridade(
            db,
            logger_operacao=logger,
            mensagem_erro="Falha de integridade ao concluir o cadastro. Verifique CNPJ e e-mail.",
        )

        db.refresh(nova_empresa)
        setattr(
            nova_empresa,
            "_onboarding_operational_credentials",
            credenciais_operacionais_onboarding,
        )

        aviso_boas_vindas: str | None = None
        try:
            aviso_boas_vindas = welcome_email_fn(email_norm, nome_norm, senha_plana)
        except RuntimeError as erro:
            aviso_boas_vindas = str(erro).strip() or None
            logger.error(
                "Falha ao enviar e-mail de boas-vindas | empresa=%s email=%s erro=%s",
                nome_norm,
                email_norm,
                erro,
                exc_info=True,
            )

        hotspot.outcome = "tenant_created"
        hotspot.response_status_code = 200
        hotspot.detail.update(
            {
                "plan": plano_norm,
                "provisioned_roles": provisionados,
                "welcome_notice_present": bool(aviso_boas_vindas),
            }
        )
        return nova_empresa, senha_plana, aviso_boas_vindas
