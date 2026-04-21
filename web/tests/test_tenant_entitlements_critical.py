from __future__ import annotations

import json
import re

from app.shared.database import Empresa, Laudo, StatusRevisao, Usuario
from app.shared.tenant_admin_policy import summarize_tenant_admin_policy
from tests.regras_rotas_criticas_support import (
    _criar_laudo,
    _csrf_pagina,
    _extrair_csrf,
    _login_admin,
    _login_app_inspetor,
    _login_cliente,
    _login_revisor,
)


def _extrair_boot_inspetor(html: str) -> dict[str, object]:
    match = re.search(
        r'<script[^>]+id="tariel-boot"[^>]*>\s*(\{.*?\})\s*</script>',
        html,
        flags=re.DOTALL,
    )
    assert match, "Bootstrap do inspetor não encontrado."
    return json.loads(match.group(1))


def test_admin_ceo_persiste_entitlements_governados_do_tenant(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, f"/admin/clientes/{ids['empresa_a']}")

    resposta = client.post(
        f"/admin/clientes/{ids['empresa_a']}/politica-admin-cliente",
        data={
            "csrf_token": csrf,
            "tenant_portal_revisor_enabled": "false",
            "tenant_capability_admin_manage_team_enabled": "false",
            "tenant_capability_reviewer_issue_enabled": "false",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 303

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        resumo = summarize_tenant_admin_policy(empresa.admin_cliente_policy_json)

    assert resumo["tenant_portal_entitlements"]["revisor"] is False
    assert resumo["tenant_capability_entitlements"]["admin_manage_team"] is False
    assert resumo["tenant_capability_entitlements"]["reviewer_issue"] is False


def test_superficies_expoem_tenant_access_policy_governado(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        inspetor = banco.get(Usuario, ids["inspetor_a"])
        assert empresa is not None
        assert inspetor is not None

        empresa.admin_cliente_policy_json = {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
            "operational_user_cross_portal_enabled": True,
            "operational_user_admin_portal_enabled": True,
            "tenant_capability_admin_manage_team_enabled": False,
            "tenant_capability_inspector_case_finalize_enabled": False,
            "tenant_capability_reviewer_issue_enabled": False,
        }
        inspetor.allowed_portals_json = ["inspetor", "revisor", "cliente"]
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        banco.commit()

    resposta_login_mobile = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": "Senha@123",
            "lembrar": True,
        },
    )
    assert resposta_login_mobile.status_code == 200
    tenant_policy_mobile = resposta_login_mobile.json()["usuario"]["tenant_access_policy"]
    assert tenant_policy_mobile["governed_by_admin_ceo"] is True
    assert tenant_policy_mobile["allowed_portals"] == ["inspetor", "revisor", "cliente"]
    assert tenant_policy_mobile["user_capability_entitlements"]["inspector_case_finalize"] is False

    csrf_cliente = _login_cliente(client, "cliente@empresa-a.test")
    bootstrap_cliente = client.get("/cliente/api/bootstrap")
    assert bootstrap_cliente.status_code == 200
    tenant_policy_cliente = bootstrap_cliente.json()["tenant_access_policy"]
    assert tenant_policy_cliente["user_capability_entitlements"]["admin_manage_team"] is False

    usuario_bootstrap = next(
        item
        for item in bootstrap_cliente.json()["usuarios"]
        if item["email"] == "inspetor@empresa-a.test"
    )
    assert usuario_bootstrap["tenant_access_policy"]["allowed_portals"] == [
        "inspetor",
        "revisor",
        "cliente",
    ]

    csrf_inspetor = _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta_portal = client.get("/app/")
    assert resposta_portal.status_code == 200
    boot_inspetor = _extrair_boot_inspetor(resposta_portal.text)
    assert boot_inspetor["tenantAccessPolicy"]["user_capability_entitlements"]["inspector_case_finalize"] is False

    csrf_revisor = _login_revisor(client, "revisor@empresa-a.test")
    resposta_pacote = client.get(f"/revisao/api/laudo/{laudo_id}/pacote")
    assert resposta_pacote.status_code == 200
    tenant_policy_mesa = resposta_pacote.json()["tenant_access_policy"]
    assert tenant_policy_mesa["user_capability_entitlements"]["reviewer_issue"] is False
    assert tenant_policy_mesa["portal_entitlements"]["revisor"] is True

    assert csrf_cliente
    assert csrf_inspetor
    assert csrf_revisor


def test_revogacao_do_portal_revisor_reflete_nos_grants_e_bloqueia_login(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        inspetor = banco.get(Usuario, ids["inspetor_a"])
        assert empresa is not None
        assert inspetor is not None

        empresa.admin_cliente_policy_json = {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
            "operational_user_cross_portal_enabled": True,
            "operational_user_admin_portal_enabled": True,
            "tenant_portal_revisor_enabled": False,
        }
        inspetor.allowed_portals_json = ["inspetor", "revisor", "cliente"]
        banco.commit()

    resposta_login_mobile = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": "Senha@123",
            "lembrar": True,
        },
    )
    assert resposta_login_mobile.status_code == 200
    usuario_mobile = resposta_login_mobile.json()["usuario"]
    assert usuario_mobile["allowed_portals"] == ["inspetor", "cliente"]
    assert usuario_mobile["tenant_access_policy"]["portal_entitlements"]["revisor"] is False

    _login_cliente(client, "cliente@empresa-a.test")
    bootstrap_cliente = client.get("/cliente/api/bootstrap")
    assert bootstrap_cliente.status_code == 200
    usuario_bootstrap = next(
        item
        for item in bootstrap_cliente.json()["usuarios"]
        if item["email"] == "inspetor@empresa-a.test"
    )
    assert usuario_bootstrap["allowed_portals"] == ["inspetor", "cliente"]

    tela_login_revisor = client.get("/revisao/login")
    csrf = _extrair_csrf(tela_login_revisor.text)
    resposta_login_revisor = client.post(
        "/revisao/login",
        data={
            "email": "revisor@empresa-a.test",
            "senha": "Senha@123",
            "csrf_token": csrf,
        },
    )
    assert resposta_login_revisor.status_code == 403
    assert "portal correto" in resposta_login_revisor.text.lower()


def test_revogacao_de_capacidades_bloqueia_acoes_criticas_do_tenant(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        empresa.admin_cliente_policy_json = {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
            "tenant_capability_admin_manage_team_enabled": False,
            "tenant_capability_inspector_case_create_enabled": False,
            "tenant_capability_inspector_case_finalize_enabled": False,
            "tenant_capability_inspector_send_to_mesa_enabled": False,
            "tenant_capability_mobile_case_approve_enabled": False,
            "tenant_capability_reviewer_decision_enabled": False,
            "tenant_capability_reviewer_issue_enabled": False,
        }
        laudo_rascunho_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo_aguardando_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        banco.commit()

    csrf_cliente = _login_cliente(client, "cliente@empresa-a.test")
    resposta_criar_usuario = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf_cliente},
        json={
            "nome": "Operador Bloqueado",
            "email": "operador-bloqueado@empresa-a.test",
            "nivel_acesso": "inspetor",
            "telefone": "62999990001",
            "crea": "",
            "allowed_portals": [],
        },
    )
    assert resposta_criar_usuario.status_code == 403
    assert "gestão de equipe" in resposta_criar_usuario.json()["detail"].lower()

    csrf_inspetor = _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta_iniciar = client.post(
        "/app/api/laudo/iniciar",
        headers={"X-CSRF-Token": csrf_inspetor},
        data={"tipo_template": "padrao"},
    )
    assert resposta_iniciar.status_code == 403
    assert "criação de laudos" in resposta_iniciar.json()["detail"].lower()

    resposta_finalizar = client.post(
        f"/app/api/laudo/{laudo_rascunho_id}/finalizar",
        headers={"X-CSRF-Token": csrf_inspetor},
    )
    assert resposta_finalizar.status_code == 403
    assert "finalização de laudos" in resposta_finalizar.json()["detail"].lower()

    resposta_enviar_mesa = client.post(
        f"/app/api/laudo/{laudo_rascunho_id}/mobile-review-command",
        headers={"X-CSRF-Token": csrf_inspetor},
        json={"command": "enviar_para_mesa"},
    )
    assert resposta_enviar_mesa.status_code == 403
    assert "mesa avaliadora" in resposta_enviar_mesa.json()["detail"].lower()

    resposta_login_mobile = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": "Senha@123",
            "lembrar": True,
        },
    )
    assert resposta_login_mobile.status_code == 200
    access_token = resposta_login_mobile.json()["access_token"]
    resposta_aprovar_mobile = client.post(
        f"/app/api/laudo/{laudo_rascunho_id}/mobile-review-command",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"command": "aprovar_no_mobile"},
    )
    assert resposta_aprovar_mobile.status_code == 403
    assert "aprovação final no mobile" in resposta_aprovar_mobile.json()["detail"].lower()

    csrf_revisor = _login_revisor(client, "revisor@empresa-a.test")
    resposta_avaliar = client.post(
        f"/revisao/api/laudo/{laudo_aguardando_id}/avaliar",
        headers={"X-CSRF-Token": csrf_revisor},
        data={"acao": "aprovar", "motivo": "ok"},
    )
    assert resposta_avaliar.status_code == 403
    assert "mesa avaliadora" in resposta_avaliar.json()["detail"].lower()

    with SessionLocal() as banco:
        laudo_emitivel = banco.get(Laudo, laudo_aguardando_id)
        assert laudo_emitivel is not None
        laudo_emitivel.status_revisao = StatusRevisao.APROVADO.value
        banco.commit()

    resposta_emitir = client.post(
        f"/revisao/api/laudo/{laudo_aguardando_id}/emissao-oficial",
        headers={"X-CSRF-Token": csrf_revisor},
        json={},
    )
    assert resposta_emitir.status_code == 403
    assert "emissão oficial" in resposta_emitir.json()["detail"].lower()


def test_revogacao_de_capacidades_bloqueia_websocket_e_exports_governados_da_mesa(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        empresa.admin_cliente_policy_json = {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
            "tenant_capability_reviewer_decision_enabled": False,
            "tenant_capability_reviewer_issue_enabled": False,
        }
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        banco.commit()

    _login_revisor(client, "revisor@empresa-a.test")

    with client.websocket_connect("/revisao/ws/whispers") as websocket:
        pronto = websocket.receive_json()
        assert pronto["tipo"] == "whisper_ready"

        websocket.send_json(
            {
                "acao": "broadcast_mesa",
                "laudo_id": str(laudo_id),
                "preview": "mensagem bloqueada",
            }
        )
        erro = websocket.receive_json()
        assert erro["tipo"] == "erro"
        assert "mesa avaliadora" in erro["detail"].lower()

    resposta_pdf = client.get(f"/revisao/api/laudo/{laudo_id}/pacote/exportar-pdf")
    assert resposta_pdf.status_code == 403
    assert "mesa avaliadora" in resposta_pdf.json()["detail"].lower()

    resposta_zip = client.get(f"/revisao/api/laudo/{laudo_id}/pacote/exportar-oficial")
    assert resposta_zip.status_code == 403
    assert "emissão oficial" in resposta_zip.json()["detail"].lower()

    resposta_download = client.get(
        f"/revisao/api/laudo/{laudo_id}/emissao-oficial/download"
    )
    assert resposta_download.status_code == 403
    assert "emissão oficial" in resposta_download.json()["detail"].lower()
