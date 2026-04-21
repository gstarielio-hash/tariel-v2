from __future__ import annotations

from types import SimpleNamespace

from starlette.requests import Request
from fastapi.responses import JSONResponse

import app.domains.cliente.route_support as route_support
from app.shared.database import NivelAcesso, RegistroAuditoriaEmpresa, Usuario
from app.shared.security import token_esta_ativo
from tests.regras_rotas_criticas_support import _criar_laudo


def _request(path: str = "/cliente/painel", *, query_string: str = "", session: dict | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": query_string.encode("utf-8"),
        "scheme": "http",
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "state": {},
        "session": session or {},
    }
    request = Request(scope)
    request.state.csp_nonce = "nonce-teste"
    return request


def test_render_helpers_cliente_aplicam_headers_e_contexto() -> None:
    request = _request("/cliente/login")

    resposta_login = route_support._render_login_cliente(request, erro="Falha no login", status_code=401)
    resposta_troca = route_support._render_troca_senha(request, erro="Senha inválida", status_code=400)
    html_login = resposta_login.body.decode("utf-8")
    html_troca = resposta_troca.body.decode("utf-8")

    assert resposta_login.status_code == 401
    assert resposta_login.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert "Falha no login" in html_login
    assert "/static/css/cliente/cliente_auth.css?v=" in html_login
    assert "Continuar com Google" not in html_login
    assert "Continuar com Microsoft" not in html_login
    assert "Esqueceu a senha?" not in html_login
    assert "/admin/login" not in html_login

    assert resposta_troca.status_code == 400
    assert "Troca Obrigatória de Senha" in html_troca
    assert "Portal da empresa" in html_troca

    resposta_portal = route_support._render_portal_cliente(
        _request("/cliente/chat"),
        usuario=SimpleNamespace(email="cliente@empresa.test", nome_completo="Cliente Teste"),
        empresa=SimpleNamespace(nome_fantasia="Empresa Teste", plano_ativo="Ilimitado"),
        tab_inicial="chat",
    )
    html_portal = resposta_portal.body.decode("utf-8")
    assert 'data-cliente-tab-inicial="chat"' in html_portal
    assert 'data-cliente-route-admin="/cliente/painel"' in html_portal
    assert 'data-cliente-route-chat="/cliente/chat"' in html_portal
    assert 'data-cliente-route-mesa="/cliente/mesa"' in html_portal
    assert 'aria-selected="true"' in html_portal
    assert route_support._normalizar_tab_cliente("mesa") == "mesa"
    assert route_support._normalizar_tab_cliente("desconhecida") == "admin"
    assert route_support._normalizar_secao_cliente("admin", "planos") == "capacity"
    assert route_support._normalizar_secao_cliente("admin", "equipe") == "team"
    assert route_support._normalizar_secao_cliente("admin", "governanca") == "support"
    assert route_support._normalizar_secao_cliente("chat", "desconhecida") == "overview"
    assert route_support._normalizar_secao_cliente("mesa", "reply") == "reply"

    resposta_portal_admin_team = route_support._render_portal_cliente(
        _request("/cliente/painel", query_string="sec=equipe"),
        usuario=SimpleNamespace(email="cliente@empresa.test", nome_completo="Cliente Teste"),
        empresa=SimpleNamespace(nome_fantasia="Empresa Teste", plano_ativo="Ilimitado"),
        tab_inicial="admin",
    )
    html_portal_admin_team = resposta_portal_admin_team.body.decode("utf-8")
    assert 'data-cliente-admin-section-inicial="team"' in html_portal_admin_team

    resposta_portal_mesa_fallback = route_support._render_portal_cliente(
        _request("/cliente/mesa", query_string="sec=invalida"),
        usuario=SimpleNamespace(email="cliente@empresa.test", nome_completo="Cliente Teste"),
        empresa=SimpleNamespace(nome_fantasia="Empresa Teste", plano_ativo="Ilimitado"),
        tab_inicial="mesa",
    )
    html_portal_mesa_fallback = resposta_portal_mesa_fallback.body.decode("utf-8")
    assert 'data-cliente-mesa-section-inicial="overview"' in html_portal_mesa_fallback


def test_render_portal_cliente_oculta_superficies_de_caso_quando_tenant_usa_so_resumos() -> None:
    resposta = route_support._render_portal_cliente(
        _request("/cliente/chat"),
        usuario=SimpleNamespace(email="cliente@empresa.test", nome_completo="Cliente Teste"),
        empresa=SimpleNamespace(
            nome_fantasia="Empresa Teste",
            plano_ativo="Ilimitado",
            admin_cliente_policy_json={
                "case_visibility_mode": "summary_only",
                "case_action_mode": "read_only",
            },
        ),
        tab_inicial="chat",
    )

    html = resposta.body.decode("utf-8")
    assert 'data-cliente-tab-inicial="admin"' in html
    assert 'id="tab-chat"' in html
    assert 'id="tab-mesa"' in html
    assert 'id="tab-chat"' in html and "hidden" in html.split('id="tab-chat"', 1)[1].split(">", 1)[0]
    assert 'id="tab-mesa"' in html and "hidden" in html.split('id="tab-mesa"', 1)[1].split(">", 1)[0]


def test_sessao_cliente_registra_e_limpa_token(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    request = _request()

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_cliente_a"])
        assert usuario is not None
        route_support._registrar_sessao_cliente(request, usuario, lembrar=True)

    token = request.session["session_token_cliente"]
    assert request.session["csrf_token"] == request.session["csrf_token_cliente"]
    assert token_esta_ativo(token) is True

    route_support._limpar_sessao_cliente(request)

    assert request.session == {}
    assert token_esta_ativo(token) is False


def test_fluxo_troca_senha_cliente_identifica_usuario_pendente(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    request = _request()

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_cliente_a"])
        assert usuario is not None
        usuario.senha_temporaria_ativa = True
        banco.commit()

    route_support._iniciar_fluxo_troca_senha(request, usuario_id=ids["admin_cliente_a"], lembrar=True)

    with SessionLocal() as banco:
        usuario_pendente = route_support._usuario_pendente_troca_senha(request, banco)
        assert usuario_pendente is not None
        assert int(usuario_pendente.id) == ids["admin_cliente_a"]

    request.session[route_support.CHAVE_TROCA_SENHA_UID] = "invalido"
    with SessionLocal() as banco:
        assert route_support._usuario_pendente_troca_senha(request, banco) is None

    assert route_support.CHAVE_TROCA_SENHA_UID not in request.session


def test_helpers_cliente_traduzem_erros_payloads_e_urls() -> None:
    assert (
        route_support._mensagem_portal_correto(Usuario(nivel_acesso=NivelAcesso.INSPETOR.value))
        == "Esta credencial deve acessar /app/login."
    )
    assert (
        route_support._mensagem_portal_correto(Usuario(nivel_acesso=NivelAcesso.REVISOR.value))
        == "Esta credencial deve acessar /revisao/login."
    )
    assert (
        route_support._mensagem_portal_correto(Usuario(nivel_acesso=NivelAcesso.DIRETORIA.value))
        == "Esta credencial pertence ao portal da Tariel em /admin/login."
    )
    assert (
        route_support._mensagem_portal_correto(Usuario(nivel_acesso=NivelAcesso.ADMIN_CLIENTE.value))
        == "Esta credencial deve acessar /cliente/login."
    )

    assert route_support._validar_nova_senha("", "", "") == "Preencha senha atual, nova senha e confirmação."
    assert route_support._validar_nova_senha("Senha@1", "Nova@1", "Outra@1") == "A confirmação da nova senha não confere."
    assert route_support._validar_nova_senha("Senha@1", "curta", "curta") == "A nova senha deve ter no mínimo 8 caracteres."
    assert (
        route_support._validar_nova_senha("Senha@123", "Senha@123", "Senha@123")
        == "A nova senha deve ser diferente da senha temporária."
    )
    assert route_support._validar_nova_senha("Senha@1", "NovaSenha@123", "NovaSenha@123") == ""

    assert route_support._traduzir_erro_servico_cliente(ValueError("Usuário não encontrado")).status_code == 404
    assert route_support._traduzir_erro_servico_cliente(ValueError("E-mail já cadastrado")).status_code == 409
    assert route_support._traduzir_erro_servico_cliente(ValueError("Operação inválida")).status_code == 400

    payload = {
        "itens": [
            {"anexos": [{"id": 3}, {"id": "x"}, "ignorar"]},
            {"filho": {"anexos": [{"id": 9}]}}
        ]
    }
    ajustado = route_support._rebase_urls_anexos_cliente(payload, laudo_id=55)
    assert ajustado["itens"][0]["anexos"][0]["url"] == "/cliente/api/mesa/laudos/55/anexos/3"
    assert ajustado["itens"][1]["filho"]["anexos"][0]["url"] == "/cliente/api/mesa/laudos/55/anexos/9"

    resposta = JSONResponse({"ok": True, "valor": 1})
    assert route_support._payload_json_resposta(resposta) == {"ok": True, "valor": 1}
    assert route_support._payload_json_resposta(JSONResponse([1, 2, 3])) == {}
    assert route_support._payload_json_resposta(object()) == {}

    assert route_support._resumir_texto_auditoria("texto curto") == "texto curto"
    assert route_support._resumir_texto_auditoria("x" * 200).endswith("...")


def test_titulo_laudo_e_auditoria_cliente(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_cliente_a"])
        assert usuario is not None
        empresa = route_support._empresa_usuario(banco, usuario)
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao="rascunho",
        )

        assert int(empresa.id) == ids["empresa_a"]
        assert route_support._titulo_laudo_cliente(banco, empresa_id=ids["empresa_a"], laudo_id=laudo_id) == "geral"
        assert route_support._titulo_laudo_cliente(banco, empresa_id=ids["empresa_b"], laudo_id=laudo_id) == f"Laudo #{laudo_id}"

        route_support._registrar_auditoria_cliente_segura(
            banco,
            empresa_id=ids["empresa_a"],
            ator_usuario_id=ids["admin_cliente_a"],
            acao="usuario_criado",
            resumo="Usuário criado no portal cliente",
            detalhe="Detalhe complementar",
            alvo_usuario_id=ids["inspetor_a"],
            payload={"origem": "teste"},
        )
        banco.commit()

        auditoria = banco.query(RegistroAuditoriaEmpresa).filter(RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"]).one()
        assert auditoria.acao == "usuario_criado"
        assert auditoria.resumo == "Usuário criado no portal cliente"
        assert auditoria.payload_json == {"origem": "teste"}
