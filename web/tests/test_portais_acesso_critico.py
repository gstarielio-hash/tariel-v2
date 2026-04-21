from __future__ import annotations

from app.shared.database import Empresa
from tests.regras_rotas_criticas_support import (
    SENHA_PADRAO,
    _login_admin,
    _login_app_inspetor,
    _login_cliente,
    _login_revisor,
)


def test_admin_login_exige_csrf_valido(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    resposta = client.post(
        "/admin/login",
        data={
            "email": "admin@empresa-a.test",
            "senha": SENHA_PADRAO,
            "csrf_token": "csrf-invalido",
        },
    )

    assert resposta.status_code == 400
    assert "Requisição inválida." in resposta.text


def test_sessao_admin_nao_vaza_para_portal_app(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_admin(client, "admin@empresa-a.test")

    resposta_app = client.get("/app/", follow_redirects=False)
    assert resposta_app.status_code == 303
    assert resposta_app.headers["location"] == "/app/login"

    tela_login_app = client.get("/app/login")
    assert tela_login_app.status_code == 200
    assert 'name="csrf_token"' in tela_login_app.text


def test_sessao_admin_nao_vaza_para_login_do_portal_revisao(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_admin(client, "admin@empresa-a.test")

    resposta_revisao = client.get("/revisao/login", follow_redirects=False)
    assert resposta_revisao.status_code == 200
    assert 'name="csrf_token"' in resposta_revisao.text


def test_sessao_revisor_nao_vaza_para_portal_app(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_revisor(client, "revisor@empresa-a.test")

    resposta_app = client.get("/app/", follow_redirects=False)
    assert resposta_app.status_code == 303
    assert resposta_app.headers["location"] == "/app/login"


def test_sessao_inspetor_nao_vaza_para_portal_revisao(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta_revisao = client.get("/revisao/painel", follow_redirects=False)
    assert resposta_revisao.status_code in (303, 401)
    if resposta_revisao.status_code == 303:
        assert resposta_revisao.headers["location"] == "/revisao/login"


def test_sessao_inspetor_nao_vaza_para_portal_admin(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta_admin = client.get("/admin/painel", follow_redirects=False)
    assert resposta_admin.status_code == 303
    assert resposta_admin.headers["location"] == "/admin/login"


def test_login_mobile_inspetor_retorna_token_e_bootstrap_funciona(ambiente_critico) -> None:
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
    assert corpo_login["auth_mode"] == "bearer"
    assert corpo_login["token_type"] == "bearer"
    assert corpo_login["usuario"]["email"] == "inspetor@empresa-a.test"

    headers = {"Authorization": f"Bearer {corpo_login['access_token']}"}

    resposta_bootstrap = client.get("/app/api/mobile/bootstrap", headers=headers)
    assert resposta_bootstrap.status_code == 200
    corpo_bootstrap = resposta_bootstrap.json()
    assert corpo_bootstrap["app"]["portal"] == "inspetor"
    assert corpo_bootstrap["usuario"]["empresa_nome"] == "Empresa A"

    resposta_push = client.post(
        "/app/api/mobile/push/register",
        headers=headers,
        json={
            "device_id": "pytest-device-001",
            "plataforma": "android",
            "provider": "expo",
            "push_token": "",
            "permissao_notificacoes": True,
            "push_habilitado": True,
            "token_status": "missing_project_id",
            "canal_build": "development",
            "app_version": "1.0.0",
            "build_number": "100",
            "device_label": "Pytest Android",
            "is_emulator": True,
            "ultimo_erro": "expo_project_id_missing",
        },
    )
    assert resposta_push.status_code == 200
    corpo_push = resposta_push.json()
    assert corpo_push["ok"] is True
    assert corpo_push["registration"]["device_id"] == "pytest-device-001"
    assert corpo_push["registration"]["token_status"] == "missing_project_id"
    assert corpo_push["registration"]["provider"] == "expo"
    assert corpo_push["registration"]["is_emulator"] is True

    resposta_perfil = client.put(
        "/app/api/mobile/account/profile",
        headers=headers,
        json={
            "nome_completo": "Inspetor Mobile A",
            "email": "inspetor@empresa-a.test",
            "telefone": "(11) 99999-0000",
        },
    )
    assert resposta_perfil.status_code == 200
    assert resposta_perfil.json()["usuario"]["nome_completo"] == "Inspetor Mobile A"

    resposta_suporte = client.post(
        "/app/api/mobile/support/report",
        headers=headers,
        json={
            "tipo": "bug",
            "titulo": "Campo de teste",
            "mensagem": "Fluxo mobile validado via teste automatizado.",
            "email_retorno": "inspetor@empresa-a.test",
            "contexto": "pytest",
            "anexo_nome": "screenshot.png",
        },
    )
    assert resposta_suporte.status_code == 200
    assert resposta_suporte.json()["status"] == "Recebido"

    resposta_senha = client.post(
        "/app/api/mobile/account/password",
        headers=headers,
        json={
            "senha_atual": SENHA_PADRAO,
            "nova_senha": "NovaSenha!123",
            "confirmar_senha": "NovaSenha!123",
        },
    )
    assert resposta_senha.status_code == 200

    resposta_settings_padrao = client.get("/app/api/mobile/account/settings", headers=headers)
    assert resposta_settings_padrao.status_code == 200
    assert resposta_settings_padrao.json()["settings"]["notificacoes"]["som_notificacao"] == "Ping"
    assert resposta_settings_padrao.json()["settings"]["experiencia_ia"]["modelo_ia"] == "equilibrado"

    resposta_settings_salva = client.put(
        "/app/api/mobile/account/settings",
        headers=headers,
        json={
            "notificacoes": {
                "notifica_respostas": False,
                "notifica_push": True,
                "som_notificacao": "Sino curto",
                "vibracao_ativa": False,
                "emails_ativos": True,
            },
            "privacidade": {
                "mostrar_conteudo_notificacao": False,
                "ocultar_conteudo_bloqueado": True,
                "mostrar_somente_nova_mensagem": True,
                "salvar_historico_conversas": False,
                "compartilhar_melhoria_ia": False,
                "retencao_dados": "30 dias",
            },
            "permissoes": {
                "microfone_permitido": True,
                "camera_permitida": True,
                "arquivos_permitidos": False,
                "notificacoes_permitidas": True,
                "biometria_permitida": True,
            },
            "experiencia_ia": {
                "modelo_ia": "avançado",
            },
        },
    )
    assert resposta_settings_salva.status_code == 200
    assert resposta_settings_salva.json()["settings"]["privacidade"]["retencao_dados"] == "30 dias"
    assert resposta_settings_salva.json()["settings"]["experiencia_ia"]["modelo_ia"] == "avançado"

    resposta_settings_lida = client.get("/app/api/mobile/account/settings", headers=headers)
    assert resposta_settings_lida.status_code == 200
    assert resposta_settings_lida.json()["settings"]["notificacoes"]["som_notificacao"] == "Sino curto"
    assert resposta_settings_lida.json()["settings"]["permissoes"]["arquivos_permitidos"] is False
    assert resposta_settings_lida.json()["settings"]["experiencia_ia"]["modelo_ia"] == "avançado"

    resposta_logout = client.post("/app/api/mobile/auth/logout", headers=headers)
    assert resposta_logout.status_code == 200

    resposta_bootstrap_expirado = client.get("/app/api/mobile/bootstrap", headers=headers)
    assert resposta_bootstrap_expirado.status_code == 401


def test_sessao_revisor_nao_vaza_para_portal_admin(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_revisor(client, "revisor@empresa-a.test")

    resposta_admin = client.get("/admin/painel", follow_redirects=False)
    assert resposta_admin.status_code == 303
    assert resposta_admin.headers["location"] == "/admin/login"


def test_admin_cliente_login_funciona_e_painel_abre(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_cliente(client, "cliente@empresa-a.test")

    resposta_painel = client.get("/cliente/painel")
    resposta_painel_team = client.get("/cliente/painel?sec=team")
    resposta_chat = client.get("/cliente/chat")
    resposta_chat_queue = client.get("/cliente/chat?sec=queue")
    resposta_mesa = client.get("/cliente/mesa")
    resposta_mesa_reply = client.get("/cliente/mesa?sec=reply")

    assert resposta_painel.status_code == 200
    assert "Portal da empresa" in resposta_painel.text
    assert 'data-cliente-tab-inicial="admin"' in resposta_painel.text
    assert resposta_painel_team.status_code == 200
    assert 'data-cliente-admin-section-inicial="team"' in resposta_painel_team.text

    assert resposta_chat.status_code == 200
    assert 'data-cliente-tab-inicial="chat"' in resposta_chat.text
    assert 'id="chat-busca-laudos"' in resposta_chat.text
    assert 'id="chat-new-policy-hint"' in resposta_chat.text
    assert 'id="chat-case-policy-note"' in resposta_chat.text
    assert 'id="chat-message-policy-note"' in resposta_chat.text
    assert 'id="btn-chat-msg-enviar"' in resposta_chat.text
    assert resposta_chat_queue.status_code == 200
    assert 'data-cliente-chat-section-inicial="queue"' in resposta_chat_queue.text

    assert resposta_mesa.status_code == 200
    assert 'data-cliente-tab-inicial="mesa"' in resposta_mesa.text
    assert 'id="mesa-busca-laudos"' in resposta_mesa.text
    assert 'id="mesa-reply-policy-hint"' in resposta_mesa.text
    assert 'id="mesa-reply-policy-note"' in resposta_mesa.text
    assert 'id="mesa-message-policy-note"' in resposta_mesa.text
    assert 'id="btn-mesa-msg-enviar"' in resposta_mesa.text
    assert resposta_mesa_reply.status_code == 200
    assert 'data-cliente-mesa-section-inicial="reply"' in resposta_mesa_reply.text


def test_admin_cliente_com_tenant_resumo_cai_no_painel_admin_e_nao_carrega_superficies_de_caso(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        empresa.admin_cliente_policy_json = {
            "case_visibility_mode": "summary_only",
            "case_action_mode": "read_only",
        }
        banco.commit()

    _login_cliente(client, "cliente@empresa-a.test")

    resposta_chat = client.get("/cliente/chat")
    resposta_mesa = client.get("/cliente/mesa")
    resposta_bootstrap_chat = client.get("/cliente/api/bootstrap?surface=chat")

    assert resposta_chat.status_code == 200
    assert 'data-cliente-tab-inicial="admin"' in resposta_chat.text
    assert 'id="tab-chat"' in resposta_chat.text
    assert 'id="tab-mesa"' in resposta_chat.text
    assert 'id="tab-chat"' in resposta_chat.text and "hidden" in resposta_chat.text.split('id="tab-chat"', 1)[1].split(">", 1)[0]
    assert 'id="tab-mesa"' in resposta_chat.text and "hidden" in resposta_chat.text.split('id="tab-mesa"', 1)[1].split(">", 1)[0]

    assert resposta_mesa.status_code == 200
    assert 'data-cliente-tab-inicial="admin"' in resposta_mesa.text

    assert resposta_bootstrap_chat.status_code == 200
    corpo_bootstrap_chat = resposta_bootstrap_chat.json()
    assert "usuarios" in corpo_bootstrap_chat
    assert "auditoria" in corpo_bootstrap_chat
    assert "chat" not in corpo_bootstrap_chat
    assert "mesa" not in corpo_bootstrap_chat
    assert (
        corpo_bootstrap_chat["tenant_admin_projection"]["payload"]["visibility_policy"][
            "admin_client_case_visibility_mode"
        ]
        == "summary_only"
    )


def test_admin_cliente_links_diretos_por_secao_resolvem_alias_e_fallback(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_cliente(client, "cliente@empresa-a.test")

    resposta_equipe_fixa = client.get("/cliente/equipe")
    resposta_alias_team = client.get("/cliente/painel?sec=equipe")
    resposta_alias_support = client.get("/cliente/painel?sec=governanca")
    resposta_chat_invalido = client.get("/cliente/chat?sec=invalida")
    resposta_mesa_invalido = client.get("/cliente/mesa?sec=desconhecida")

    assert resposta_equipe_fixa.status_code == 200
    assert 'data-cliente-admin-section-inicial="team"' in resposta_equipe_fixa.text

    assert resposta_alias_team.status_code == 200
    assert 'data-cliente-admin-section-inicial="team"' in resposta_alias_team.text

    assert resposta_alias_support.status_code == 200
    assert 'data-cliente-admin-section-inicial="support"' in resposta_alias_support.text

    assert resposta_chat_invalido.status_code == 200
    assert 'data-cliente-chat-section-inicial="overview"' in resposta_chat_invalido.text

    assert resposta_mesa_invalido.status_code == 200
    assert 'data-cliente-mesa-section-inicial="overview"' in resposta_mesa_invalido.text


def test_admin_cliente_nao_acessa_admin_geral(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_cliente(client, "cliente@empresa-a.test")

    resposta = client.get("/admin/painel", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/admin/login"


def test_admin_cliente_bootstrap_fica_restrito_a_propria_empresa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    _login_cliente(client, "cliente@empresa-a.test")

    resposta = client.get("/cliente/api/bootstrap")
    resposta_chat = client.get("/cliente/api/bootstrap?surface=chat")
    resposta_admin = client.get("/cliente/api/bootstrap?surface=admin")
    resposta_mesa = client.get("/cliente/api/bootstrap?surface=mesa")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["empresa"]["nome_fantasia"] == "Empresa A"
    emails = {item["email"] for item in corpo["usuarios"]}
    assert "cliente@empresa-a.test" not in emails
    assert "inspetor@empresa-a.test" in emails
    assert "revisor@empresa-a.test" in emails
    assert "admin@empresa-a.test" not in emails
    assert "inspetor@empresa-b.test" not in emails
    assert corpo["empresa"]["total_usuarios"] == 3
    assert corpo["empresa"]["usuarios_em_uso"] == 3
    assert "tenant_admin_projection" in corpo

    assert resposta_chat.status_code == 200
    corpo_chat = resposta_chat.json()
    assert corpo_chat["empresa"]["nome_fantasia"] == "Empresa A"
    assert "chat" in corpo_chat
    assert "usuarios" not in corpo_chat
    assert "auditoria" not in corpo_chat
    assert "mesa" not in corpo_chat
    assert "tenant_admin_projection" in corpo_chat

    assert resposta_admin.status_code == 200
    corpo_admin = resposta_admin.json()
    assert corpo_admin["empresa"]["nome_fantasia"] == "Empresa A"
    assert "usuarios" in corpo_admin
    assert "auditoria" in corpo_admin
    assert "chat" not in corpo_admin
    assert "mesa" not in corpo_admin
    assert "tenant_admin_projection" in corpo_admin

    assert resposta_mesa.status_code == 200
    corpo_mesa = resposta_mesa.json()
    assert corpo_mesa["empresa"]["nome_fantasia"] == "Empresa A"
    assert "mesa" in corpo_mesa
    assert "usuarios" not in corpo_mesa
    assert "auditoria" not in corpo_mesa
    assert "chat" not in corpo_mesa
    assert "tenant_admin_projection" in corpo_mesa


def test_admin_cliente_nao_gerencia_admin_ceo_mesmo_na_mesma_empresa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta_lista = client.get("/cliente/api/usuarios", headers={"X-CSRF-Token": csrf})

    assert resposta_lista.status_code == 200
    emails = {item["email"] for item in resposta_lista.json()["itens"]}
    assert "admin@empresa-a.test" not in emails

    resposta_atualizar = client.patch(
        f"/cliente/api/usuarios/{ids['admin_a']}",
        headers={"X-CSRF-Token": csrf},
        json={
            "nome": "Admin CEO Alterado",
            "email": "admin@empresa-a.test",
            "telefone": "",
            "crea": "",
        },
    )
    assert resposta_atualizar.status_code == 404

    resposta_bloqueio = client.patch(
        f"/cliente/api/usuarios/{ids['admin_a']}/bloqueio",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_bloqueio.status_code == 404

    resposta_reset = client.post(
        f"/cliente/api/usuarios/{ids['admin_a']}/resetar-senha",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_reset.status_code == 404


def test_admin_cliente_nao_acessa_revisao_geral(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_cliente(client, "cliente@empresa-a.test")

    resposta = client.get("/revisao/painel", follow_redirects=False)
    assert resposta.status_code in {303, 401}
    if resposta.status_code == 303:
        assert resposta.headers["location"] == "/revisao/login"
