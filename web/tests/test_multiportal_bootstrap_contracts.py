from __future__ import annotations

import json
import re

from app.shared.database import Empresa, Usuario
from tests.regras_rotas_criticas_support import (
    SENHA_PADRAO,
    _login_app_inspetor,
    _login_cliente,
    _login_revisor,
)


def _extrair_script_json(html: str, *, element_id: str) -> dict[str, object]:
    match = re.search(
        rf'<script[^>]+id="{re.escape(element_id)}"[^>]*>\s*(\{{.*?\}})\s*</script>',
        html,
        flags=re.DOTALL,
    )
    assert match, f"Script JSON #{element_id} não encontrado."
    return json.loads(match.group(1))


def _extrair_data_attrs(html: str, *, element_id: str) -> dict[str, str]:
    match = re.search(
        rf'<[^>]+\sid="{re.escape(element_id)}"[^>]*>',
        html,
        flags=re.DOTALL,
    )
    assert match, f"Elemento #{element_id} não encontrado."
    return {
        chave: valor
        for chave, valor in re.findall(r'(data-[a-z0-9-]+)="([^"]*)"', match.group(0))
    }


def _extrair_csrf_meta(html: str) -> str:
    match = re.search(
        r'<meta\s+name="csrf-token"\s+content="([^"]+)"',
        html,
        flags=re.IGNORECASE,
    )
    assert match, "Meta CSRF não encontrada."
    return match.group(1)


def test_inspetor_bootstrap_ssr_expoe_contrato_minimo_estavel(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta = client.get("/app/")
    assert resposta.status_code == 200

    boot = _extrair_script_json(resposta.text, element_id="tariel-boot")
    csrf_meta = _extrair_csrf_meta(resposta.text)
    campos_minimos = {
        "csrfToken",
        "usuarioNome",
        "empresaNome",
        "laudosMesUsados",
        "laudosMesLimite",
        "planoUploadDoc",
        "deepResearchDisponivel",
        "estadoRelatorio",
        "laudoAtivoId",
        "suporteWhatsapp",
        "ambiente",
    }

    assert campos_minimos.issubset(boot)
    assert boot["csrfToken"] == csrf_meta
    assert boot["usuarioNome"] == "Inspetor A"
    assert boot["empresaNome"] == "Empresa A"
    assert isinstance(boot["laudosMesUsados"], int)
    assert isinstance(boot["planoUploadDoc"], bool)
    assert isinstance(boot["deepResearchDisponivel"], bool)
    assert boot["estadoRelatorio"] == "sem_relatorio"
    assert boot["laudoAtivoId"] is None
    assert isinstance(boot["suporteWhatsapp"], str) and boot["suporteWhatsapp"]
    assert isinstance(boot["ambiente"], str) and boot["ambiente"]


def test_revisor_painel_expoe_front_contract_bootstrap_minimo(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_revisor(client, "revisor@empresa-a.test")

    resposta = client.get("/revisao/painel?surface=ssr")
    assert resposta.status_code == 200

    csrf_meta = _extrair_csrf_meta(resposta.text)
    attrs = _extrair_data_attrs(resposta.text, element_id="revisor-front-contract")
    campos_minimos = {
        "data-websocket-url": "/revisao/ws/whispers",
        "data-pacote-url-template": "/revisao/api/laudo/${state.laudoAtivoId}/pacote",
        "data-pacote-pdf-url-template": "/revisao/api/laudo/${state.laudoAtivoId}/pacote/exportar-pdf",
        "data-marcar-whispers-url-template": "/revisao/api/laudo/${alvo}/marcar-whispers-lidos",
        "data-pendencia-url-template": "/revisao/api/laudo/${laudoId}/pendencias/${msgId}",
        "data-responder-anexo-url-template": "/revisao/api/laudo/${state.laudoAtivoId}/responder-anexo",
        "data-pacote-json-hook": "js-btn-pacote-json",
        "data-pacote-pdf-hook": "js-btn-pacote-pdf",
        "data-pendencias-key": "pendencias_resolvidas_recentes",
        "data-whispers-indicator-hook": "js-indicador-whispers",
        "data-pendencias-indicator-hook": "js-indicador-pendencias",
        "data-anexo-link-class": "anexo-mensagem-link",
    }

    assert csrf_meta
    assert re.search(r'<span class="topbar-usuario-nome">\s*Revisor A\s*</span>', resposta.text)
    assert re.search(r'data-mesa-action="responder-item"', resposta.text)
    assert re.search(r'data-mesa-action="alternar-pendencia"', resposta.text)
    for chave, valor in campos_minimos.items():
        assert attrs.get(chave) == valor


def test_android_mobile_auth_e_bootstrap_expoem_envelope_minimo_estavel(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    resposta_login = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "lembrar": True,
        },
    )

    assert resposta_login.status_code == 200
    corpo_login = resposta_login.json()
    campos_login = {
        "ok",
        "auth_mode",
        "access_token",
        "token_type",
        "usuario",
    }
    campos_usuario = {
        "id",
        "nome_completo",
        "email",
        "telefone",
        "foto_perfil_url",
        "empresa_nome",
        "empresa_id",
        "nivel_acesso",
        "allowed_portals",
        "allowed_portal_labels",
        "commercial_operating_model",
        "commercial_operating_model_label",
        "identity_runtime_mode",
        "identity_runtime_note",
        "portal_switch_links",
        "admin_ceo_governed",
    }

    assert set(corpo_login).issuperset(campos_login)
    assert corpo_login["ok"] is True
    assert corpo_login["auth_mode"] == "bearer"
    assert corpo_login["token_type"] == "bearer"
    assert isinstance(corpo_login["access_token"], str) and corpo_login["access_token"]
    assert set(corpo_login["usuario"]).issuperset(campos_usuario)
    assert corpo_login["usuario"]["email"] == "inspetor@empresa-a.test"
    assert corpo_login["usuario"]["empresa_nome"] == "Empresa A"
    assert corpo_login["usuario"]["allowed_portals"] == ["inspetor"]
    assert corpo_login["usuario"]["allowed_portal_labels"] == [
        "Area de campo"
    ]
    assert corpo_login["usuario"]["commercial_operating_model"] == "standard"
    assert corpo_login["usuario"]["commercial_operating_model_label"] == "Operação padrão"
    assert corpo_login["usuario"]["identity_runtime_mode"] == "standard_role_accounts"
    assert corpo_login["usuario"]["portal_switch_links"] == [
        {
            "portal": "inspetor",
            "label": "Area de campo",
            "url": "/app/",
        }
    ]
    assert corpo_login["usuario"]["admin_ceo_governed"] is True

    headers = {"Authorization": f"Bearer {corpo_login['access_token']}"}
    resposta_bootstrap = client.get("/app/api/mobile/bootstrap", headers=headers)

    assert resposta_bootstrap.status_code == 200
    corpo_bootstrap = resposta_bootstrap.json()
    assert set(corpo_bootstrap).issuperset({"ok", "app", "usuario"})
    assert corpo_bootstrap["ok"] is True
    assert corpo_bootstrap["app"]["nome"] == "Tariel Inspetor"
    assert corpo_bootstrap["app"]["portal"] == "inspetor"
    assert corpo_bootstrap["app"]["api_base_url"] == "http://testserver"
    assert isinstance(corpo_bootstrap["app"]["suporte_whatsapp"], str)
    assert corpo_bootstrap["usuario"] == corpo_login["usuario"]


def test_android_mobile_bootstrap_expoe_grants_multiportal_do_tenant(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert empresa is not None
        assert usuario is not None

        empresa.admin_cliente_policy_json = {
            "operating_model": "mobile_single_operator",
            "shared_mobile_operator_web_inspector_enabled": True,
            "shared_mobile_operator_web_review_enabled": True,
            "operational_user_cross_portal_enabled": True,
            "operational_user_admin_portal_enabled": True,
        }
        usuario.allowed_portals_json = ["inspetor", "revisor", "cliente"]
        banco.commit()

    resposta_login = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "lembrar": True,
        },
    )

    assert resposta_login.status_code == 200
    usuario_mobile = resposta_login.json()["usuario"]
    assert usuario_mobile["allowed_portals"] == ["inspetor", "revisor", "cliente"]
    assert usuario_mobile["allowed_portal_labels"] == [
        "Area de campo",
        "Area de analise",
        "Portal da empresa",
    ]
    assert usuario_mobile["commercial_operating_model"] == "mobile_single_operator"
    assert (
        usuario_mobile["commercial_operating_model_label"]
        == "Aplicativo principal com uma pessoa responsavel"
    )
    assert usuario_mobile["identity_runtime_mode"] == "tenant_scoped_portal_grants"
    assert "Admin-CEO" in usuario_mobile["identity_runtime_note"]
    assert usuario_mobile["portal_switch_links"] == [
        {
            "portal": "inspetor",
            "label": "Area de campo",
            "url": "/app/",
        },
        {
            "portal": "revisor",
            "label": "Area de analise",
            "url": "/revisao/painel",
        },
        {
            "portal": "cliente",
            "label": "Portal da empresa",
            "url": "/cliente/painel",
        },
    ]


def test_portais_web_expoem_troca_de_superficie_para_conta_multiportal(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert empresa is not None
        assert usuario is not None

        empresa.admin_cliente_policy_json = {
            "operating_model": "mobile_single_operator",
            "shared_mobile_operator_web_inspector_enabled": True,
            "shared_mobile_operator_web_review_enabled": True,
            "operational_user_cross_portal_enabled": True,
            "operational_user_admin_portal_enabled": True,
        }
        usuario.allowed_portals_json = ["inspetor", "revisor", "cliente"]
        banco.commit()

    _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta_inspetor = client.get("/app/")
    assert resposta_inspetor.status_code == 200
    assert "Abrir Area de analise" in resposta_inspetor.text
    assert "Abrir Portal da empresa" in resposta_inspetor.text

    _login_revisor(client, "inspetor@empresa-a.test")
    resposta_revisor = client.get("/revisao/painel?surface=ssr")
    assert resposta_revisor.status_code == 200
    assert "Area de campo" in resposta_revisor.text
    assert "Portal da empresa" in resposta_revisor.text

    _login_cliente(client, "inspetor@empresa-a.test")
    resposta_cliente = client.get("/cliente/painel")
    assert resposta_cliente.status_code == 200
    assert "Abrir Area de campo" in resposta_cliente.text
    assert "Abrir Area de analise" in resposta_cliente.text
