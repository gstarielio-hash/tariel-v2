from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.shared.database as banco_dados  # noqa: E402
from app.domains.admin.services import registrar_novo_cliente  # noqa: E402
from app.shared.database import (  # noqa: E402
    AprendizadoVisualIa,
    AtivacaoCatalogoEmpresaLaudo,
    DispositivoPushMobile,
    Empresa,
    Laudo,
    MensagemLaudo,
    NivelAcesso,
    RegistroAuditoriaEmpresa,
    SignatarioGovernadoLaudo,
    StatusRevisao,
    TemplateLaudo,
    TenantFamilyReleaseLaudo,
    TipoMensagem,
    Usuario,
)
from app.shared.security import encerrar_todas_sessoes_usuario  # noqa: E402


BASE_URL_LOCAL = "http://127.0.0.1:8000"
SNAPSHOT_DIR = REPO_ROOT / "artifacts" / "demo_local"
SNAPSHOT_PATH = SNAPSHOT_DIR / "localhost_demo_snapshot.json"
DEFAULT_COMPANY_NAME = "Tariel Demo Local"
DEFAULT_COMPANY_CNPJ = "55555555000191"
DEFAULT_PLAN = "Ilimitado"
DEFAULT_ADMIN_EMAIL = "admin.demo.local@tariel.test"
DEFAULT_INSPETOR_EMAIL = "inspetor.demo.local@tariel.test"
DEFAULT_REVISOR_EMAIL = "mesa.demo.local@tariel.test"
DEFAULT_INSPETOR_NAME = "Inspetor Demo Local"
DEFAULT_REVISOR_NAME = "Mesa Avaliadora Demo"
DEFAULT_REVISOR_CREA = "123456/GO"
DEMO_PREVIEW = "Apresentação local controlada"
DEMO_USER_MESSAGE = (
    "Inspeção inicial lançada para a apresentação local, com equipamento identificado e "
    "evidências prontas para revisão."
)
DEMO_REVIEW_MESSAGE = (
    "Mesa avaliadora pronta. Validar o histórico do equipamento e confirmar o fechamento do "
    "fluxo com troca de senha no primeiro acesso."
)
PORTAL_URLS = {
    "cliente": f"{BASE_URL_LOCAL}/cliente/login",
    "inspetor": f"{BASE_URL_LOCAL}/app/login",
    "revisor": f"{BASE_URL_LOCAL}/revisao/login",
    "admin_ceo": f"{BASE_URL_LOCAL}/admin/login",
}


def _normalize_email(value: str) -> str:
    return str(value or "").strip().lower()


def _normalize_cnpj(value: str) -> str:
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits[:14]


def _portal_items(portais: list[str] | tuple[str, ...] | None) -> list[dict[str, str]]:
    itens: list[dict[str, str]] = []
    for portal in list(portais or []):
        portal_norm = str(portal or "").strip().lower()
        login_url = PORTAL_URLS.get(portal_norm)
        if not login_url:
            continue
        itens.append(
            {
                "portal": portal_norm,
                "login_url": login_url,
            }
        )
    return itens


def _resolve_company_ids(
    banco,
    *,
    cnpj: str,
    admin_email: str,
    inspetor_email: str,
    revisor_email: str,
) -> list[int]:
    ids: set[int] = set()
    cnpj_norm = _normalize_cnpj(cnpj)
    if cnpj_norm:
        ids.update(int(item) for item in banco.scalars(select(Empresa.id).where(Empresa.cnpj == cnpj_norm)).all())

    emails = [
        _normalize_email(admin_email),
        _normalize_email(inspetor_email),
        _normalize_email(revisor_email),
    ]
    emails_filtrados = [item for item in emails if item]
    if emails_filtrados:
        ids.update(
            int(item)
            for item in banco.scalars(select(Usuario.empresa_id).where(Usuario.email.in_(emails_filtrados))).all()
            if int(item or 0) > 0
        )
    return sorted(ids)


def _reset_demo_companies(banco, *, company_ids: list[int]) -> list[dict[str, Any]]:
    removidas: list[dict[str, Any]] = []
    if not company_ids:
        return removidas

    for company_id in company_ids:
        empresa = banco.get(Empresa, int(company_id))
        if empresa is None:
            continue

        usuarios = list(
            banco.scalars(select(Usuario).where(Usuario.empresa_id == int(company_id)).order_by(Usuario.id.asc())).all()
        )
        for usuario in usuarios:
            encerrar_todas_sessoes_usuario(int(usuario.id))

        removidas.append(
            {
                "empresa_id": int(company_id),
                "nome_fantasia": str(getattr(empresa, "nome_fantasia", "") or ""),
                "cnpj": str(getattr(empresa, "cnpj", "") or ""),
                "usuarios_total": len(usuarios),
            }
        )

        banco.query(AtivacaoCatalogoEmpresaLaudo).filter(
            AtivacaoCatalogoEmpresaLaudo.empresa_id == int(company_id)
        ).delete(synchronize_session=False)
        banco.query(TenantFamilyReleaseLaudo).filter(
            TenantFamilyReleaseLaudo.tenant_id == int(company_id)
        ).delete(synchronize_session=False)
        banco.query(SignatarioGovernadoLaudo).filter(
            SignatarioGovernadoLaudo.tenant_id == int(company_id)
        ).delete(synchronize_session=False)
        banco.query(DispositivoPushMobile).filter(
            DispositivoPushMobile.empresa_id == int(company_id)
        ).delete(synchronize_session=False)
        banco.query(AprendizadoVisualIa).filter(
            AprendizadoVisualIa.empresa_id == int(company_id)
        ).delete(synchronize_session=False)
        banco.query(TemplateLaudo).filter(
            TemplateLaudo.empresa_id == int(company_id)
        ).delete(synchronize_session=False)
        banco.query(RegistroAuditoriaEmpresa).filter(
            RegistroAuditoriaEmpresa.empresa_id == int(company_id)
        ).delete(synchronize_session=False)
        banco.query(Laudo).filter(
            Laudo.empresa_id == int(company_id)
        ).delete(synchronize_session=False)
        banco.query(Usuario).filter(
            Usuario.empresa_id == int(company_id)
        ).delete(synchronize_session=False)
        banco.delete(empresa)

    banco.commit()
    return removidas


def _resolve_user(banco, *, empresa_id: int, email: str, nivel: NivelAcesso) -> Usuario:
    usuario = banco.scalar(
        select(Usuario).where(
            Usuario.empresa_id == int(empresa_id),
            Usuario.email == _normalize_email(email),
        )
    )
    if usuario is None:
        raise RuntimeError(f"Usuário não encontrado no tenant demo: {email}")
    if int(usuario.nivel_acesso or 0) != int(nivel):
        raise RuntimeError(
            "Usuário demo criado com papel inesperado: "
            f"email={email} nivel={usuario.nivel_acesso} esperado={int(nivel)}"
        )
    return usuario


def _create_demo_case(
    banco,
    *,
    empresa: Empresa,
    inspetor: Usuario,
    revisor: Usuario,
) -> tuple[Laudo, MensagemLaudo]:
    laudo = Laudo(
        empresa_id=int(empresa.id),
        usuario_id=int(inspetor.id),
        revisado_por=int(revisor.id),
        setor_industrial="Linha de apresentação local",
        tipo_template="padrao",
        status_revisao=StatusRevisao.AGUARDANDO.value,
        codigo_hash=uuid.uuid4().hex,
        primeira_mensagem=DEMO_PREVIEW,
        parecer_ia="Laudo seed local para a apresentação controlada em localhost.",
        modo_resposta="detalhado",
        custo_api_reais=Decimal("0.0000"),
        dados_formulario={
            "equipamento": "Vaso de pressão piloto",
            "setor": "Casa de utilidades",
            "objetivo": "Apresentação operacional local",
        },
    )
    banco.add(laudo)
    banco.flush()

    banco.add(
        MensagemLaudo(
            laudo_id=int(laudo.id),
            remetente_id=int(inspetor.id),
            tipo=TipoMensagem.USER.value,
            conteudo=DEMO_USER_MESSAGE,
            lida=True,
            custo_api_reais=Decimal("0.0000"),
        )
    )
    pendencia = MensagemLaudo(
        laudo_id=int(laudo.id),
        remetente_id=int(revisor.id),
        tipo=TipoMensagem.HUMANO_ENG.value,
        conteudo=DEMO_REVIEW_MESSAGE,
        lida=False,
        custo_api_reais=Decimal("0.0000"),
    )
    banco.add(pendencia)
    banco.flush()
    banco.commit()
    banco.refresh(laudo)
    banco.refresh(pendencia)
    return laudo, pendencia


def _credential_map(
    *,
    admin_email: str,
    admin_password: str,
    operational_credentials: list[dict[str, Any]],
) -> dict[str, Any]:
    creds: dict[str, Any] = {
        "admin_cliente": {
            "login": _normalize_email(admin_email),
            "senha_temporaria": str(admin_password or ""),
            "portais": [
                {
                    "portal": "cliente",
                    "login_url": PORTAL_URLS["cliente"],
                }
            ],
        }
    }

    for payload in operational_credentials:
        login = _normalize_email(str(payload.get("login", "")))
        papel = str(payload.get("papel", "") or "").strip().lower()
        key = "revisor" if "mesa" in papel or "revisor" in papel else "inspetor"
        creds[key] = {
            "login": login,
            "senha_temporaria": str(payload.get("senha", "") or ""),
            "portais": _portal_items(payload.get("allowed_portals")),
        }
    return creds


def _write_snapshot(payload: dict[str, Any]) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _status_revisao_value(laudo: Laudo) -> str:
    status = getattr(laudo, "status_revisao", "")
    return str(getattr(status, "value", status) or "")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reseta e provisiona um tenant local pronto para apresentação em localhost."
    )
    parser.add_argument("--reset", action="store_true", help="Remove o tenant demo anterior antes de recriar tudo.")
    parser.add_argument("--company-name", default=DEFAULT_COMPANY_NAME)
    parser.add_argument("--cnpj", default=DEFAULT_COMPANY_CNPJ)
    parser.add_argument("--plan", default=DEFAULT_PLAN)
    parser.add_argument("--admin-email", default=DEFAULT_ADMIN_EMAIL)
    parser.add_argument("--inspetor-email", default=DEFAULT_INSPETOR_EMAIL)
    parser.add_argument("--revisor-email", default=DEFAULT_REVISOR_EMAIL)
    parser.add_argument("--inspetor-name", default=DEFAULT_INSPETOR_NAME)
    parser.add_argument("--revisor-name", default=DEFAULT_REVISOR_NAME)
    parser.add_argument("--revisor-crea", default=DEFAULT_REVISOR_CREA)
    args = parser.parse_args()

    with banco_dados.SessaoLocal() as banco:
        company_ids = _resolve_company_ids(
            banco,
            cnpj=args.cnpj,
            admin_email=args.admin_email,
            inspetor_email=args.inspetor_email,
            revisor_email=args.revisor_email,
        )
        removed_companies: list[dict[str, Any]] = []
        if company_ids and not args.reset:
            raise SystemExit(
                "Tenant demo já existe para os identificadores informados. "
                "Rode novamente com --reset para recriar o ambiente de apresentação."
            )
        if company_ids and args.reset:
            removed_companies = _reset_demo_companies(banco, company_ids=company_ids)

        empresa, admin_password, welcome_notice = registrar_novo_cliente(
            banco,
            nome=args.company_name,
            cnpj=args.cnpj,
            email_admin=args.admin_email,
            plano=args.plan,
            provisionar_inspetor_inicial=True,
            inspetor_nome=args.inspetor_name,
            inspetor_email=args.inspetor_email,
            provisionar_revisor_inicial=True,
            revisor_nome=args.revisor_name,
            revisor_email=args.revisor_email,
            revisor_crea=args.revisor_crea,
        )
        operational_credentials = list(getattr(empresa, "_onboarding_operational_credentials", []) or [])
        inspetor = _resolve_user(
            banco,
            empresa_id=int(empresa.id),
            email=args.inspetor_email,
            nivel=NivelAcesso.INSPETOR,
        )
        revisor = _resolve_user(
            banco,
            empresa_id=int(empresa.id),
            email=args.revisor_email,
            nivel=NivelAcesso.REVISOR,
        )
        laudo, pendencia = _create_demo_case(
            banco,
            empresa=empresa,
            inspetor=inspetor,
            revisor=revisor,
        )

    payload = {
        "ok": True,
        "base_url": BASE_URL_LOCAL,
        "snapshot_path": str(SNAPSHOT_PATH),
        "removed_companies": removed_companies,
        "company": {
            "id": int(empresa.id),
            "name": str(getattr(empresa, "nome_fantasia", "") or ""),
            "cnpj": str(getattr(empresa, "cnpj", "") or ""),
            "plan": str(getattr(empresa, "plano_ativo", "") or ""),
        },
        "credentials": _credential_map(
            admin_email=args.admin_email,
            admin_password=admin_password,
            operational_credentials=operational_credentials,
        ),
        "users": {
            "admin_email": _normalize_email(args.admin_email),
            "inspetor_id": int(inspetor.id),
            "inspetor_email": _normalize_email(args.inspetor_email),
            "revisor_id": int(revisor.id),
            "revisor_email": _normalize_email(args.revisor_email),
        },
        "demo_case": {
            "laudo_id": int(laudo.id),
            "pendencia_mesa_id": int(pendencia.id),
            "preview": DEMO_PREVIEW,
            "status_revisao": _status_revisao_value(laudo),
        },
        "urls": {
            "admin_ceo_login": PORTAL_URLS["admin_ceo"],
            "admin_cliente_login": PORTAL_URLS["cliente"],
            "inspetor_login": PORTAL_URLS["inspetor"],
            "mesa_login": PORTAL_URLS["revisor"],
            "admin_novo_cliente": f"{BASE_URL_LOCAL}/admin/novo-cliente",
            "admin_empresa_detalhe": f"{BASE_URL_LOCAL}/admin/clientes/{int(empresa.id)}",
        },
        "notices": {
            "welcome_notice": str(welcome_notice or ""),
        },
    }
    _write_snapshot(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
