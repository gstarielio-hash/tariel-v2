from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal

import app.domains.admin.services as admin_services
import app.domains.cliente.portal_bridge as portal_bridge
import pytest
from sqlalchemy import select

from app.shared.database import (
    AnexoMesa,
    Empresa,
    Laudo,
    MensagemLaudo,
    NivelAcesso,
    PlanoEmpresa,
    RegistroAuditoriaEmpresa,
    StatusRevisao,
    TipoMensagem,
    Usuario,
)
from tests.regras_rotas_criticas_support import (
    SENHA_HASH_PADRAO,
    _criar_laudo,
    _csrf_pagina,
    _docx_bytes_teste,
    _extrair_csrf,
    _imagem_png_bytes_teste,
    _login_admin,
    _login_cliente,
)


def _concluir_primeiro_login_cliente(
    client,
    *,
    email: str,
    senha_temporaria: str,
    nova_senha: str,
) -> str:
    tela_login = client.get("/cliente/login")
    csrf_login = _extrair_csrf(tela_login.text)
    resposta_login = client.post(
        "/cliente/login",
        data={
            "email": email,
            "senha": senha_temporaria,
            "csrf_token": csrf_login,
        },
        follow_redirects=False,
    )
    assert resposta_login.status_code == 303
    assert resposta_login.headers["location"] == "/cliente/trocar-senha"

    tela_troca = client.get("/cliente/trocar-senha")
    assert tela_troca.status_code == 200
    csrf_troca = _extrair_csrf(tela_troca.text)
    resposta_troca = client.post(
        "/cliente/trocar-senha",
        data={
            "senha_atual": senha_temporaria,
            "nova_senha": nova_senha,
            "confirmar_senha": nova_senha,
            "csrf_token": csrf_troca,
        },
        follow_redirects=False,
    )
    assert resposta_troca.status_code == 303
    assert resposta_troca.headers["location"] == "/cliente/painel"
    return _csrf_pagina(client, "/cliente/equipe")


def _concluir_primeiro_login_operacional(
    client,
    *,
    login_path: str,
    trocar_path: str,
    destino_final: str,
    email: str,
    senha_temporaria: str,
    nova_senha: str,
) -> None:
    tela_login = client.get(login_path)
    csrf_login = _extrair_csrf(tela_login.text)
    resposta_login = client.post(
        login_path,
        data={
            "email": email,
            "senha": senha_temporaria,
            "csrf_token": csrf_login,
        },
        follow_redirects=False,
    )
    assert resposta_login.status_code == 303
    assert resposta_login.headers["location"] == trocar_path

    tela_troca = client.get(trocar_path)
    assert tela_troca.status_code == 200
    csrf_troca = _extrair_csrf(tela_troca.text)
    resposta_troca = client.post(
        trocar_path,
        data={
            "senha_atual": senha_temporaria,
            "nova_senha": nova_senha,
            "confirmar_senha": nova_senha,
            "csrf_token": csrf_troca,
        },
        follow_redirects=False,
    )
    assert resposta_troca.status_code == 303
    assert resposta_troca.headers["location"] == destino_final
    resposta_final = client.get(destino_final, follow_redirects=False)
    assert resposta_final.status_code == 200


def test_admin_cliente_chat_obedece_portfolio_governado_por_variante(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_exibicao="NR13 · Caldeira",
            macro_categoria="NR13",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_oferta="NR13 Premium · Caldeira",
            pacote_comercial="Premium",
            ativo_comercial=True,
            variantes_comerciais_text="premium_campo | Premium campo | nr13_premium | Campo crítico",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_vaso_pressao",
            nome_exibicao="NR13 · Vaso de Pressão",
            macro_categoria="NR13",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_vaso_pressao",
            nome_oferta="NR13 Premium · Vaso de Pressão",
            pacote_comercial="Premium",
            ativo_comercial=True,
            variantes_comerciais_text="premium_campo | Premium campo | nr13_premium | Vaso crítico",
            criado_por_id=ids["admin_a"],
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[
                "catalog:nr13_inspecao_caldeira:premium_campo",
                "catalog:nr13_inspecao_vaso_pressao:premium_campo",
            ],
            admin_id=ids["admin_a"],
        )
        banco.commit()

    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta_ambigua = client.post(
        "/cliente/api/chat/laudos",
        headers={"X-CSRF-Token": csrf},
        data={"tipo_template": "nr13"},
    )
    assert resposta_ambigua.status_code == 403
    assert "variante comercial" in resposta_ambigua.json()["detail"].lower()

    resposta_ok = client.post(
        "/cliente/api/chat/laudos",
        headers={"X-CSRF-Token": csrf},
        data={"tipo_template": "catalog:nr13_inspecao_caldeira:premium_campo"},
    )
    assert resposta_ok.status_code == 200
    laudo_id = int(resposta_ok.json()["laudo_id"])

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.tipo_template == "nr13"
        assert laudo.catalog_family_key == "nr13_inspecao_caldeira"
        assert laudo.catalog_variant_key == "premium_campo"


def test_admin_cliente_chat_cria_laudo_com_payload_serializavel_por_jsonable_encoder(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ambiente_critico["client"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    async def _fake_iniciar_relatorio_resposta(**_: object) -> tuple[dict[str, object], int]:
        return (
            {
                "success": True,
                "laudo_id": 321,
                "gerado_em": datetime(2026, 4, 10, 19, 14, tzinfo=timezone.utc),
            },
            200,
        )

    monkeypatch.setattr(
        portal_bridge,
        "iniciar_relatorio_resposta",
        _fake_iniciar_relatorio_resposta,
    )

    resposta = client.post(
        "/cliente/api/chat/laudos",
        headers={"X-CSRF-Token": csrf},
        data={"tipo_template": "padrao"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["laudo_id"] == 321
    assert resposta.json()["gerado_em"] == "2026-04-10T19:14:00+00:00"


def test_admin_cliente_chat_bloqueia_fallback_legado_quando_catalogo_governado_fica_vazio(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_exibicao="NR13 · Caldeira",
            macro_categoria="NR13",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_oferta="NR13 Premium · Caldeira",
            pacote_comercial="Premium",
            ativo_comercial=True,
            variantes_comerciais_text="premium_campo | Premium campo | nr13_premium | Campo crítico",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="active",
            allowed_variants=["catalog:nr13_inspecao_caldeira:premium_campo"],
            criado_por_id=ids["admin_a"],
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=["catalog:nr13_inspecao_caldeira:premium_campo"],
            admin_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="paused",
            allowed_variants=["catalog:nr13_inspecao_caldeira:premium_campo"],
            criado_por_id=ids["admin_a"],
        )
        banco.commit()

    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta = client.post(
        "/cliente/api/chat/laudos",
        headers={"X-CSRF-Token": csrf},
        data={"tipo_template": "nr13"},
    )

    assert resposta.status_code == 403
    assert "admin-ceo" in resposta.json()["detail"].lower()


def test_admin_cliente_respeita_governanca_de_casos_do_tenant(ambiente_critico) -> None:
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

    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta_lista_resumo = client.get("/cliente/api/chat/laudos", headers={"X-CSRF-Token": csrf})
    resposta_mesa_resumo = client.get("/cliente/api/mesa/laudos", headers={"X-CSRF-Token": csrf})
    resposta_criar_resumo = client.post(
        "/cliente/api/chat/laudos",
        headers={"X-CSRF-Token": csrf},
        data={"tipo_template": "padrao"},
    )

    assert resposta_lista_resumo.status_code == 403
    assert "resumos agregados" in resposta_lista_resumo.json()["detail"]
    assert resposta_mesa_resumo.status_code == 403
    assert resposta_criar_resumo.status_code == 403

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        empresa.admin_cliente_policy_json = {
            "case_visibility_mode": "case_list",
            "case_action_mode": "read_only",
        }
        banco.commit()

    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta_lista_read_only = client.get("/cliente/api/chat/laudos", headers={"X-CSRF-Token": csrf})
    resposta_mesa_read_only = client.get("/cliente/api/mesa/laudos", headers={"X-CSRF-Token": csrf})
    resposta_criar_read_only = client.post(
        "/cliente/api/chat/laudos",
        headers={"X-CSRF-Token": csrf},
        data={"tipo_template": "padrao"},
    )
    resposta_responder_read_only = client.post(
        "/cliente/api/mesa/laudos/999/responder",
        headers={"X-CSRF-Token": csrf},
        json={"texto": "teste", "referencia_mensagem_id": None},
    )

    assert resposta_lista_read_only.status_code == 200
    assert resposta_mesa_read_only.status_code == 200
    assert resposta_criar_read_only.status_code == 403
    assert "sem agir nos casos" in resposta_criar_read_only.json()["detail"]
    assert resposta_responder_read_only.status_code == 403


def test_admin_cliente_nao_altera_plano_diretamente_e_preserva_outra_empresa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta = client.patch(
        "/cliente/api/empresa/plano",
        headers={"X-CSRF-Token": csrf},
        json={"plano": "Intermediario"},
    )

    assert resposta.status_code == 403
    corpo = resposta.json()
    assert corpo["success"] is False
    assert corpo["empresa"]["plano_ativo"] == PlanoEmpresa.ILIMITADO.value
    assert corpo["plano"]["plano"] == "Intermediario"
    assert "Registre interesse" in corpo["detail"]

    with SessionLocal() as banco:
        empresa_a = banco.get(Empresa, ids["empresa_a"])
        empresa_b = banco.get(Empresa, ids["empresa_b"])
        assert empresa_a is not None
        assert empresa_b is not None
        assert empresa_a.plano_ativo == PlanoEmpresa.ILIMITADO.value
        assert empresa_b.plano_ativo == PlanoEmpresa.ILIMITADO.value


def test_admin_cliente_cria_e_gerencia_usuarios_restritos_a_empresa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta_admin_cliente = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf},
        json={
            "nome": "Par Administrativo",
            "email": "par-admin@empresa-a.test",
            "nivel_acesso": "admin_cliente",
            "telefone": "62998887766",
            "crea": "",
        },
    )

    assert resposta_admin_cliente.status_code == 403
    assert "Admin-Cliente" in resposta_admin_cliente.json()["detail"]

    resposta_inspetor = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf},
        json={
            "nome": "Inspetor Operacional A2",
            "email": "inspetor2@empresa-a.test",
            "nivel_acesso": "inspetor",
            "telefone": "62999990000",
            "crea": "",
        },
    )

    assert resposta_inspetor.status_code == 201
    corpo_inspetor = resposta_inspetor.json()
    usuario_inspetor_id = int(corpo_inspetor["usuario"]["id"])
    assert corpo_inspetor["usuario"]["papel"] == "Inspetor"
    assert corpo_inspetor["senha_temporaria"]
    credencial_inspetor = corpo_inspetor["credencial_onboarding"]
    assert credencial_inspetor["usuario_id"] == usuario_inspetor_id
    assert credencial_inspetor["login"] == "inspetor2@empresa-a.test"
    assert credencial_inspetor["acesso_inicial_url"] == f"/cliente/usuarios/{usuario_inspetor_id}/acesso-inicial"
    assert credencial_inspetor["portais"] == [
        {
            "portal": "inspetor",
            "label": "Inspetor web/mobile",
            "login_url": "/app/login",
        }
    ]

    resposta_acesso_inicial_inspetor = client.get(credencial_inspetor["acesso_inicial_url"])
    assert resposta_acesso_inicial_inspetor.status_code == 200
    assert "inspetor2@empresa-a.test" in resposta_acesso_inicial_inspetor.text
    assert corpo_inspetor["senha_temporaria"] in resposta_acesso_inicial_inspetor.text
    assert "/app/login" in resposta_acesso_inicial_inspetor.text

    resposta_acesso_inicial_consumido = client.get(credencial_inspetor["acesso_inicial_url"])
    assert resposta_acesso_inicial_consumido.status_code == 410
    assert "não está mais disponível" in resposta_acesso_inicial_consumido.text

    resposta_revisor = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf},
        json={
            "nome": "Mesa Operacional A2",
            "email": "mesa2@empresa-a.test",
            "nivel_acesso": "revisor",
            "telefone": "62999991111",
            "crea": "123456/GO",
        },
    )

    assert resposta_revisor.status_code == 201
    corpo_revisor = resposta_revisor.json()
    usuario_revisor_id = int(corpo_revisor["usuario"]["id"])
    assert corpo_revisor["usuario"]["papel"] == "Mesa Avaliadora"
    assert corpo_revisor["usuario"]["crea"] == "123456/GO"

    resposta_toggle_outra_empresa = client.patch(
        f"/cliente/api/usuarios/{ids['inspetor_b']}/bloqueio",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_toggle_outra_empresa.status_code == 404

    resposta_toggle_admin = client.patch(
        f"/cliente/api/usuarios/{ids['admin_cliente_a']}/bloqueio",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_toggle_admin.status_code == 404

    resposta_reset = client.post(
        f"/cliente/api/usuarios/{usuario_revisor_id}/resetar-senha",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_reset.status_code == 200
    corpo_reset = resposta_reset.json()
    assert corpo_reset["senha_temporaria"]
    assert corpo_reset["credencial_onboarding"]["usuario_id"] == usuario_revisor_id
    assert corpo_reset["credencial_onboarding"]["portais"] == [
        {
            "portal": "revisor",
            "label": "Mesa Avaliadora",
            "login_url": "/revisao/login",
        }
    ]

    resposta_lista = client.get("/cliente/api/usuarios")
    assert resposta_lista.status_code == 200
    papeis = {item["papel"] for item in resposta_lista.json()["itens"]}
    emails = {item["email"] for item in resposta_lista.json()["itens"]}
    assert papeis <= {"Inspetor", "Mesa Avaliadora"}
    assert "cliente@empresa-a.test" not in emails
    assert "par-admin@empresa-a.test" not in emails

    with SessionLocal() as banco:
        novo_inspetor = banco.scalar(select(Usuario).where(Usuario.email == "inspetor2@empresa-a.test"))
        novo_revisor = banco.scalar(select(Usuario).where(Usuario.email == "mesa2@empresa-a.test"))
        par_admin = banco.scalar(select(Usuario).where(Usuario.email == "par-admin@empresa-a.test"))
        assert novo_inspetor is not None
        assert novo_revisor is not None
        assert par_admin is None
        assert int(novo_inspetor.empresa_id) == ids["empresa_a"]
        assert int(novo_revisor.empresa_id) == ids["empresa_a"]
        assert int(novo_inspetor.nivel_acesso) == int(NivelAcesso.INSPETOR)
        assert int(novo_revisor.nivel_acesso) == int(NivelAcesso.REVISOR)


def test_fluxo_fixo_empresa_admin_cliente_equipe_e_logins_operacionais_funciona(
    ambiente_critico,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]

    senhas_temporarias = iter(
        [
            "AdminClienteTemp@123",
            "InspetorTemp@123",
            "MesaTemp@123",
        ]
    )
    monkeypatch.setattr(admin_services, "gerar_senha_fortificada", lambda: next(senhas_temporarias))

    _login_admin(client, "admin@empresa-a.test")
    csrf_admin = _csrf_pagina(client, "/admin/novo-cliente")

    resposta_empresa = client.post(
        "/admin/novo-cliente",
        data={
            "csrf_token": csrf_admin,
            "nome": "Fluxo Fixo Empresa",
            "cnpj": "88999888000991",
            "email": "admincliente@fluxo-fixo.test",
            "plano": "Ilimitado",
        },
        follow_redirects=False,
    )

    assert resposta_empresa.status_code == 303
    assert resposta_empresa.headers["location"].startswith("/admin/clientes/")

    pagina_onboarding_empresa = client.get(resposta_empresa.headers["location"])
    assert pagina_onboarding_empresa.status_code == 200
    assert "admincliente@fluxo-fixo.test" in pagina_onboarding_empresa.text
    assert "AdminClienteTemp@123" in pagina_onboarding_empresa.text
    assert "/cliente/login" in pagina_onboarding_empresa.text

    with SessionLocal() as banco:
        empresa = banco.scalar(select(Empresa).where(Empresa.cnpj == "88999888000991"))
        usuario_admin_cliente = banco.scalar(
            select(Usuario).where(Usuario.email == "admincliente@fluxo-fixo.test")
        )
        assert empresa is not None
        assert usuario_admin_cliente is not None
        assert int(usuario_admin_cliente.empresa_id) == int(empresa.id)
        assert int(usuario_admin_cliente.nivel_acesso) == int(NivelAcesso.ADMIN_CLIENTE)
        assert bool(usuario_admin_cliente.senha_temporaria_ativa) is True

    csrf_cliente = _concluir_primeiro_login_cliente(
        client,
        email="admincliente@fluxo-fixo.test",
        senha_temporaria="AdminClienteTemp@123",
        nova_senha="AdminClienteNova@123",
    )

    pagina_equipe = client.get("/cliente/equipe")
    assert pagina_equipe.status_code == 200
    assert 'data-cliente-admin-section-inicial="team"' in pagina_equipe.text
    assert "Novo usuario operacional" in pagina_equipe.text

    resposta_inspetor = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf_cliente},
        json={
            "nome": "Inspetor Fluxo Fixo",
            "email": "inspetor@fluxo-fixo.test",
            "nivel_acesso": "inspetor",
            "telefone": "62991111111",
            "crea": "",
        },
    )
    assert resposta_inspetor.status_code == 201
    corpo_inspetor = resposta_inspetor.json()
    assert corpo_inspetor["credencial_onboarding"]["acesso_inicial_url"].startswith("/cliente/usuarios/")
    assert corpo_inspetor["senha_temporaria"] == "InspetorTemp@123"

    resposta_revisor = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf_cliente},
        json={
            "nome": "Mesa Fluxo Fixo",
            "email": "mesa@fluxo-fixo.test",
            "nivel_acesso": "revisor",
            "telefone": "62992222222",
            "crea": "123456/GO",
        },
    )
    assert resposta_revisor.status_code == 201
    corpo_revisor = resposta_revisor.json()
    assert corpo_revisor["credencial_onboarding"]["acesso_inicial_url"].startswith("/cliente/usuarios/")
    assert corpo_revisor["senha_temporaria"] == "MesaTemp@123"

    with SessionLocal() as banco:
        inspetor = banco.scalar(select(Usuario).where(Usuario.email == "inspetor@fluxo-fixo.test"))
        revisor = banco.scalar(select(Usuario).where(Usuario.email == "mesa@fluxo-fixo.test"))
        assert inspetor is not None
        assert revisor is not None
        assert bool(inspetor.senha_temporaria_ativa) is True
        assert bool(revisor.senha_temporaria_ativa) is True
        assert int(inspetor.nivel_acesso) == int(NivelAcesso.INSPETOR)
        assert int(revisor.nivel_acesso) == int(NivelAcesso.REVISOR)

    client.cookies.clear()
    _concluir_primeiro_login_operacional(
        client,
        login_path="/app/login",
        trocar_path="/app/trocar-senha",
        destino_final="/app/",
        email="inspetor@fluxo-fixo.test",
        senha_temporaria="InspetorTemp@123",
        nova_senha="InspetorNova@123",
    )

    client.cookies.clear()
    _concluir_primeiro_login_operacional(
        client,
        login_path="/revisao/login",
        trocar_path="/revisao/trocar-senha",
        destino_final="/revisao/painel",
        email="mesa@fluxo-fixo.test",
        senha_temporaria="MesaTemp@123",
        nova_senha="MesaNova@123",
    )

    with SessionLocal() as banco:
        inspetor = banco.scalar(select(Usuario).where(Usuario.email == "inspetor@fluxo-fixo.test"))
        revisor = banco.scalar(select(Usuario).where(Usuario.email == "mesa@fluxo-fixo.test"))
        assert inspetor is not None
        assert revisor is not None
        assert bool(inspetor.senha_temporaria_ativa) is False
        assert bool(revisor.senha_temporaria_ativa) is False


def test_admin_cliente_concede_superficies_adicionais_dentro_da_regra_do_tenant(
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
            "operational_user_cross_portal_enabled": True,
            "operational_user_admin_portal_enabled": True,
        }
        banco.commit()

    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf},
        json={
            "nome": "Operador Full Surface",
            "email": "operador-full-surface@empresa-a.test",
            "nivel_acesso": "inspetor",
            "telefone": "62999990001",
            "crea": "",
            "allowed_portals": ["revisor", "cliente"],
        },
    )

    assert resposta.status_code == 201
    usuario = resposta.json()["usuario"]
    credencial = resposta.json()["credencial_onboarding"]
    assert usuario["allowed_portals"] == ["inspetor", "revisor", "cliente"]
    assert credencial["portais"] == [
        {
            "portal": "inspetor",
            "label": "Inspetor web/mobile",
            "login_url": "/app/login",
        },
        {
            "portal": "revisor",
            "label": "Mesa Avaliadora",
            "login_url": "/revisao/login",
        },
        {
            "portal": "cliente",
            "label": "Admin-Cliente",
            "login_url": "/cliente/login",
        },
    ]

    with SessionLocal() as banco:
        criado = banco.scalar(
            select(Usuario).where(Usuario.email == "operador-full-surface@empresa-a.test")
        )
        assert criado is not None
        assert criado.allowed_portals == ("inspetor", "revisor", "cliente")


def test_admin_cliente_respeita_limite_operacional_do_pacote_mobile_single_operator(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]

    with SessionLocal() as banco:
        empresa = Empresa(
            nome_fantasia="Empresa Mobile Single Operator",
            cnpj="11222333000186",
            plano_ativo=PlanoEmpresa.ILIMITADO.value,
        )
        banco.add(empresa)
        banco.flush()
        empresa.admin_cliente_policy_json = {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
            "operating_model": "mobile_single_operator",
            "shared_mobile_operator_web_inspector_enabled": True,
            "shared_mobile_operator_web_review_enabled": True,
        }
        banco.add(
            Usuario(
                empresa_id=int(empresa.id),
                nome_completo="Admin Cliente Mobile Único",
                email="cliente-mobile-single@empresa.test",
                senha_hash=SENHA_HASH_PADRAO,
                nivel_acesso=NivelAcesso.ADMIN_CLIENTE.value,
            )
        )
        banco.commit()

    csrf = _login_cliente(client, "cliente-mobile-single@empresa.test")

    resposta_primeiro = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf},
        json={
            "nome": "Operador Mobile Único",
            "email": "operador.mobile@empresa-a.test",
            "nivel_acesso": "inspetor",
            "telefone": "62998880001",
            "crea": "",
        },
    )
    assert resposta_primeiro.status_code == 201

    resposta_segundo = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf},
        json={
            "nome": "Mesa Extra",
            "email": "mesa.extra@empresa-a.test",
            "nivel_acesso": "revisor",
            "telefone": "62998880002",
            "crea": "123456/GO",
        },
    )
    assert resposta_segundo.status_code == 409
    assert "limite operacional" in resposta_segundo.json()["detail"].lower()

    resposta_auditoria = client.get("/cliente/api/auditoria")
    assert resposta_auditoria.status_code == 200
    itens = resposta_auditoria.json()["itens"]
    registro_negado = next(item for item in itens if item["acao"] == "usuario_criacao_negada_pacote")
    assert registro_negado["categoria"] == "team"
    assert registro_negado["payload"]["requested_email"] == "mesa.extra@empresa-a.test"
    assert registro_negado["payload"]["contract_operational_user_limit"] == 1
    assert registro_negado["payload"]["operational_users_in_use"] == 1
    assert registro_negado["payload"]["shared_mobile_operator_surface_set"] == [
        "mobile",
        "inspetor_web",
        "mesa_web",
    ]

    resposta_diagnostico = client.get("/cliente/api/diagnostico", headers={"X-CSRF-Token": csrf})
    assert resposta_diagnostico.status_code == 200
    diagnostico = resposta_diagnostico.json()
    pacote_operacional = diagnostico["operational_package"]
    assert pacote_operacional["mobile_single_operator_enabled"] is True
    assert pacote_operacional["contract_operational_user_limit"] == 1
    assert pacote_operacional["operational_users_in_use"] == 1
    assert pacote_operacional["operational_users_at_limit"] is True
    assert pacote_operacional["shared_mobile_operator_surface_set"] == [
        "mobile",
        "inspetor_web",
        "mesa_web",
    ]


def test_admin_cliente_chat_lista_laudos_da_empresa_sem_vazar_outra(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    with SessionLocal() as banco:
        laudo_empresa_a = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo_empresa_b = _criar_laudo(
            banco,
            empresa_id=ids["empresa_b"],
            usuario_id=ids["inspetor_b"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta_lista = client.get("/cliente/api/chat/laudos", headers={"X-CSRF-Token": csrf})

    assert resposta_lista.status_code == 200
    ids_laudos = {int(item["id"]) for item in resposta_lista.json()["itens"]}
    assert laudo_empresa_a in ids_laudos
    assert laudo_empresa_b not in ids_laudos

    resposta_mensagens_empresa_a = client.get(
        f"/cliente/api/chat/laudos/{laudo_empresa_a}/mensagens",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_mensagens_empresa_a.status_code == 200

    resposta_mensagens_empresa_b = client.get(
        f"/cliente/api/chat/laudos/{laudo_empresa_b}/mensagens",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_mensagens_empresa_b.status_code == 404


def test_admin_cliente_exclui_usuario_operacional_sem_apagar_historico_tecnico(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta_criacao = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf},
        json={
            "nome": "Inspetor Temporario A3",
            "email": "inspetor3@empresa-a.test",
            "nivel_acesso": "inspetor",
            "telefone": "62990000003",
            "crea": "",
        },
    )
    assert resposta_criacao.status_code == 201
    usuario_id = int(resposta_criacao.json()["usuario"]["id"])

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=usuario_id,
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.USER.value,
                conteudo="Historico em campo que nao pode desaparecer com a exclusao do cadastro.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()

    resposta_exclusao = client.delete(
        f"/cliente/api/usuarios/{usuario_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_exclusao.status_code == 200
    assert resposta_exclusao.json()["success"] is True
    assert int(resposta_exclusao.json()["usuario_id"]) == usuario_id

    with SessionLocal() as banco:
        usuario_removido = banco.get(Usuario, usuario_id)
        laudo = banco.get(Laudo, laudo_id)
        mensagem = (
            banco.query(MensagemLaudo)
            .filter(MensagemLaudo.laudo_id == laudo_id)
            .order_by(MensagemLaudo.id.desc())
            .first()
        )
        auditoria = (
            banco.query(RegistroAuditoriaEmpresa)
            .filter(
                RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"],
                RegistroAuditoriaEmpresa.acao == "usuario_excluido",
            )
            .order_by(RegistroAuditoriaEmpresa.id.desc())
            .first()
        )

        assert usuario_removido is None
        assert laudo is not None
        assert laudo.usuario_id is None
        assert mensagem is not None
        assert mensagem.remetente_id is None
        assert auditoria is not None
        assert auditoria.payload_json["usuario_id"] == usuario_id
        assert auditoria.payload_json["email"] == "inspetor3@empresa-a.test"

    resposta_recriacao = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf},
        json={
            "nome": "Inspetor Recriado A3",
            "email": "inspetor3@empresa-a.test",
            "nivel_acesso": "inspetor",
            "telefone": "62990000013",
            "crea": "",
        },
    )
    assert resposta_recriacao.status_code == 201
    assert resposta_recriacao.json()["usuario"]["email"] == "inspetor3@empresa-a.test"


def test_admin_cliente_mesa_reescreve_urls_de_anexo_para_o_proprio_portal(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    conteudo = _imagem_png_bytes_teste()
    caminho = ""

    try:
        with SessionLocal() as banco:
            laudo_id = _criar_laudo(
                banco,
                empresa_id=ids["empresa_a"],
                usuario_id=ids["inspetor_a"],
                status_revisao=StatusRevisao.AGUARDANDO.value,
            )

            mensagem = MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Pendencia com evidencia anexada.",
                lida=False,
                custo_api_reais=Decimal("0.0000"),
            )
            banco.add(mensagem)
            banco.flush()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as arquivo:
                arquivo.write(conteudo)
                caminho = arquivo.name

            anexo = AnexoMesa(
                laudo_id=laudo_id,
                mensagem_id=mensagem.id,
                enviado_por_id=ids["revisor_a"],
                nome_original="retorno-mesa.png",
                nome_arquivo="retorno-mesa.png",
                mime_type="image/png",
                categoria="imagem",
                tamanho_bytes=len(conteudo),
                caminho_arquivo=caminho,
            )
            banco.add(anexo)
            banco.commit()
            banco.refresh(anexo)
            anexo_id = int(anexo.id)

        resposta = client.get(
            f"/cliente/api/mesa/laudos/{laudo_id}/mensagens",
            headers={"X-CSRF-Token": csrf},
        )

        assert resposta.status_code == 200
        itens = resposta.json()["itens"]
        assert itens
        anexo_payload = itens[-1]["anexos"][0]
        assert anexo_payload["nome"] == "retorno-mesa.png"
        assert anexo_payload["url"] == f"/cliente/api/mesa/laudos/{laudo_id}/anexos/{anexo_id}"

        resposta_completo = client.get(
            f"/cliente/api/mesa/laudos/{laudo_id}/completo",
            params={"incluir_historico": "true"},
            headers={"X-CSRF-Token": csrf},
        )
        assert resposta_completo.status_code == 200
        historico = resposta_completo.json()["historico"]
        assert historico[-1]["anexos"][0]["url"] == f"/cliente/api/mesa/laudos/{laudo_id}/anexos/{anexo_id}"

        resposta_pacote = client.get(
            f"/cliente/api/mesa/laudos/{laudo_id}/pacote",
            headers={"X-CSRF-Token": csrf},
        )
        assert resposta_pacote.status_code == 200
        pacote = resposta_pacote.json()
        assert pacote["pendencias_abertas"][0]["anexos"][0]["url"] == f"/cliente/api/mesa/laudos/{laudo_id}/anexos/{anexo_id}"

        download = client.get(anexo_payload["url"])
        assert download.status_code == 200
        assert download.content == conteudo
    finally:
        if caminho and os.path.exists(caminho):
            os.unlink(caminho)


def test_admin_cliente_upload_documental_reaproveita_fluxo_do_chat(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta = client.post(
        "/cliente/api/chat/upload_doc",
        headers={"X-CSRF-Token": csrf},
        files={
            "arquivo": (
                "checklist-operacional.docx",
                _docx_bytes_teste("Checklist operacional do admin-cliente para a empresa."),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert "Checklist operacional do admin-cliente" in corpo["texto"]
    assert corpo["nome"] == "checklist-operacional.docx"
    assert corpo["chars"] >= 20
    assert corpo["truncado"] is False


def test_admin_cliente_registra_auditoria_de_plano_e_usuarios(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta_plano = client.post(
        "/cliente/api/empresa/plano/interesse",
        headers={"X-CSRF-Token": csrf},
        json={"plano": "Intermediario", "origem": "admin"},
    )
    assert resposta_plano.status_code == 200

    resposta_usuario = client.post(
        "/cliente/api/usuarios",
        headers={"X-CSRF-Token": csrf},
        json={
            "nome": "Auditado Empresa A",
            "email": "auditado@empresa-a.test",
            "nivel_acesso": "inspetor",
            "telefone": "62991110000",
            "crea": "",
        },
    )
    assert resposta_usuario.status_code == 201
    usuario_novo_id = int(resposta_usuario.json()["usuario"]["id"])

    resposta_auditoria = client.get("/cliente/api/auditoria")
    assert resposta_auditoria.status_code == 200
    auditoria_payload = resposta_auditoria.json()
    itens = auditoria_payload["itens"]
    acoes = [item["acao"] for item in itens]
    assert "plano_interesse_registrado" in acoes
    assert "usuario_criado" in acoes
    assert all(item["portal"] == "cliente" for item in itens)
    assert any(item["ator_usuario_id"] == ids["admin_cliente_a"] for item in itens)
    assert any(item["alvo_usuario_id"] == usuario_novo_id for item in itens if item["acao"] == "usuario_criado")
    assert auditoria_payload["resumo"]["categories"]["commercial"] >= 1
    assert auditoria_payload["resumo"]["categories"]["team"] >= 1
    registro_plano = next(item for item in itens if item["acao"] == "plano_interesse_registrado")
    assert registro_plano["payload"]["plano_anterior"] == "Ilimitado"
    assert registro_plano["payload"]["plano_sugerido"] == "Intermediario"
    assert registro_plano["payload"]["origem"] == "admin"
    assert registro_plano["payload"]["movimento"] == "downgrade"
    assert "Impacto esperado" in registro_plano["detalhe"]
    assert registro_plano["categoria"] == "commercial"
    assert registro_plano["scope"] == "admin"

    resposta_bootstrap = client.get("/cliente/api/bootstrap")
    assert resposta_bootstrap.status_code == 200
    bootstrap_itens = resposta_bootstrap.json()["auditoria"]["itens"]
    assert bootstrap_itens
    assert {item["acao"] for item in bootstrap_itens} >= {"plano_interesse_registrado", "usuario_criado"}
    assert resposta_bootstrap.json()["auditoria"]["resumo"]["categories"]["commercial"] >= 1

    with SessionLocal() as banco:
        registros = list(
            banco.scalars(
                select(RegistroAuditoriaEmpresa).where(RegistroAuditoriaEmpresa.empresa_id == ids["empresa_a"]).order_by(RegistroAuditoriaEmpresa.id.desc())
            ).all()
        )
        assert registros
        assert all(int(item.empresa_id) == ids["empresa_a"] for item in registros)
        assert {item.acao for item in registros} >= {"plano_interesse_registrado", "usuario_criado"}


def test_admin_cliente_registra_interesse_em_upgrade_no_historico(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        empresa.plano_ativo = PlanoEmpresa.INICIAL.value
        banco.commit()

    resposta_interesse = client.post(
        "/cliente/api/empresa/plano/interesse",
        headers={"X-CSRF-Token": csrf},
        json={"plano": "Intermediario", "origem": "chat"},
    )
    assert resposta_interesse.status_code == 200
    corpo = resposta_interesse.json()
    assert corpo["success"] is True
    assert corpo["plano"]["plano"] == "Intermediario"
    assert corpo["plano"]["movimento"] == "upgrade"

    resposta_auditoria = client.get("/cliente/api/auditoria")
    assert resposta_auditoria.status_code == 200
    itens = resposta_auditoria.json()["itens"]
    registro = next(item for item in itens if item["acao"] == "plano_interesse_registrado")
    assert registro["payload"]["origem"] == "chat"
    assert registro["payload"]["plano_sugerido"] == "Intermediario"
    assert "Impacto esperado" in registro["detalhe"]


def test_admin_cliente_bootstrap_expoe_override_humano_interno_no_chat_e_na_mesa(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.report_pack_draft_json = {
            "quality_gates": {
                "human_override": {
                    "scope": "quality_gate",
                    "applied_at": "2026-04-13T12:00:00+00:00",
                    "actor_user_id": ids["inspetor_a"],
                    "actor_name": "Inspetor A",
                    "reason": "O responsável técnico decidiu manter a conclusão após revisar a NR manualmente.",
                    "matched_override_cases": [
                        "evidencia_complementar_substituida_por_registro_textual_com_rastreabilidade"
                    ],
                    "matched_override_case_labels": [
                        "Evidência complementar substituída por registro textual com rastreabilidade"
                    ],
                    "overrideable_item_ids": ["fotos_essenciais"],
                },
                "human_override_history": [
                    {
                        "scope": "quality_gate",
                        "applied_at": "2026-04-13T12:00:00+00:00",
                        "actor_user_id": ids["inspetor_a"],
                        "actor_name": "Inspetor A",
                        "reason": "O responsável técnico decidiu manter a conclusão após revisar a NR manualmente.",
                    }
                ],
            }
        }
        banco.commit()

    _login_cliente(client, "cliente@empresa-a.test")

    resposta_chat = client.get("/cliente/api/bootstrap?surface=chat")
    assert resposta_chat.status_code == 200
    laudo_chat = next(item for item in resposta_chat.json()["chat"]["laudos"] if int(item["id"]) == laudo_id)
    assert laudo_chat["human_override_summary"]["latest"]["actor_name"] == "Inspetor A"
    assert "revisar a NR manualmente" in laudo_chat["human_override_summary"]["latest"]["reason"]

    resposta_mesa = client.get("/cliente/api/bootstrap?surface=mesa")
    assert resposta_mesa.status_code == 200
    laudo_mesa = next(item for item in resposta_mesa.json()["mesa"]["laudos"] if int(item["id"]) == laudo_id)
    assert laudo_mesa["human_override_summary"]["latest"]["actor_name"] == "Inspetor A"
    assert laudo_mesa["human_override_summary"]["count"] == 1


def test_admin_cliente_bootstrap_mesa_expoe_status_visual_label_canonico(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.APROVADO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.nome_arquivo_pdf = "laudo_emitido.pdf"
        banco.commit()

    _login_cliente(client, "cliente@empresa-a.test")

    resposta_mesa = client.get("/cliente/api/bootstrap?surface=mesa")
    assert resposta_mesa.status_code == 200
    laudo_mesa = next(item for item in resposta_mesa.json()["mesa"]["laudos"] if int(item["id"]) == laudo_id)
    assert laudo_mesa["case_lifecycle_status"] == "emitido"
    assert laudo_mesa["active_owner_role"] == "none"
    assert laudo_mesa["status_visual_label"] == "Emitido / Responsavel: conclusao"


def test_admin_cliente_exporta_diagnostico_e_registra_suporte(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta_diagnostico = client.get("/cliente/api/diagnostico", headers={"X-CSRF-Token": csrf})
    assert resposta_diagnostico.status_code == 200
    assert "attachment; filename=" in resposta_diagnostico.headers["content-disposition"]
    diagnostico = resposta_diagnostico.json()
    assert diagnostico["contract_name"] == "TenantAdminOperationalDiagnosticV1"
    assert int(diagnostico["empresa"]["id"]) == ids["empresa_a"]
    assert diagnostico["contexto_portal"]["support_report_url"] == "/cliente/api/suporte/report"
    assert diagnostico["fronteiras"]["chat_scope"] == "company_scoped"
    assert diagnostico["visibility_policy"]["technical_access_mode"] == "surface_scoped_operational"
    assert diagnostico["visibility_policy"]["audit_scope"] == "tenant_operational_timeline"
    assert diagnostico["operational_package"]["mobile_single_operator_enabled"] is False
    assert diagnostico["operational_package"]["identity_runtime_mode"] == "standard_role_accounts"

    resposta_suporte = client.post(
        "/cliente/api/suporte/report",
        headers={"X-CSRF-Token": csrf},
        json={
            "tipo": "feedback",
            "titulo": "Fila administrativa",
            "mensagem": "Precisamos revisar a trilha operacional do tenant.",
            "email_retorno": "cliente@empresa-a.test",
            "contexto": "fase07",
        },
    )
    assert resposta_suporte.status_code == 200
    corpo = resposta_suporte.json()
    assert corpo["success"] is True
    assert corpo["status"] == "Recebido"
    assert corpo["protocolo"].startswith("CLI-")

    resposta_auditoria = client.get("/cliente/api/auditoria")
    assert resposta_auditoria.status_code == 200
    itens = resposta_auditoria.json()["itens"]
    registro = next(item for item in itens if item["acao"] == "suporte_reportado")
    assert registro["payload"]["protocolo"] == corpo["protocolo"]
    assert registro["payload"]["contexto"] == "fase07"
    assert registro["categoria"] == "support"


def test_admin_cliente_filtra_auditoria_por_superficie_operacional(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta_criar = client.post(
        "/cliente/api/chat/laudos",
        headers={"X-CSRF-Token": csrf},
        data={"tipo_template": "padrao"},
    )
    assert resposta_criar.status_code == 200
    laudo_chat_id = int(resposta_criar.json()["laudo_id"])

    resposta_chat = client.post(
        "/cliente/api/chat/mensagem",
        headers={"X-CSRF-Token": csrf},
        json={
            "laudo_id": laudo_chat_id,
            "mensagem": "Mensagem auditada no chat.",
            "historico": [],
            "setor": "geral",
            "modo": "detalhado",
        },
    )
    assert resposta_chat.status_code == 200

    with SessionLocal() as banco:
        laudo_mesa_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    resposta_mesa = client.post(
        f"/cliente/api/mesa/laudos/{laudo_mesa_id}/responder",
        headers={"X-CSRF-Token": csrf},
        json={"texto": "Mesa respondeu pelo portal."},
    )
    assert resposta_mesa.status_code == 200

    auditoria_chat = client.get("/cliente/api/auditoria?scope=chat")
    assert auditoria_chat.status_code == 200
    itens_chat = auditoria_chat.json()["itens"]
    assert itens_chat
    assert all(item["scope"] == "chat" for item in itens_chat)
    assert {"chat_laudo_criado", "chat_mensagem_enviada"} <= {item["acao"] for item in itens_chat}

    auditoria_mesa = client.get("/cliente/api/auditoria?scope=mesa")
    assert auditoria_mesa.status_code == 200
    itens_mesa = auditoria_mesa.json()["itens"]
    assert itens_mesa
    assert all(item["scope"] == "mesa" for item in itens_mesa)
    assert any(item["acao"] == "mesa_resposta_enviada" for item in itens_mesa)


def test_admin_cliente_registra_auditoria_operacional_de_chat_e_mesa(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta_criar = client.post(
        "/cliente/api/chat/laudos",
        headers={"X-CSRF-Token": csrf},
        data={"tipo_template": "padrao"},
    )
    assert resposta_criar.status_code == 200
    laudo_chat_id = int(resposta_criar.json()["laudo_id"])

    resposta_chat = client.post(
        "/cliente/api/chat/mensagem",
        headers={"X-CSRF-Token": csrf},
        json={
            "laudo_id": laudo_chat_id,
            "mensagem": "Fluxo auditado do admin-cliente no chat.",
            "historico": [],
            "setor": "geral",
            "modo": "detalhado",
        },
    )
    assert resposta_chat.status_code == 200

    with SessionLocal() as banco:
        laudo_reaberto_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.REJEITADO.value,
        )
        laudo_mesa_resposta_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo_mesa_aprovacao_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    resposta_reabrir = client.post(
        f"/cliente/api/chat/laudos/{laudo_reaberto_id}/reabrir",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_reabrir.status_code == 200

    resposta_mesa = client.post(
        f"/cliente/api/mesa/laudos/{laudo_mesa_resposta_id}/responder",
        headers={"X-CSRF-Token": csrf},
        json={"texto": "Mesa respondeu pelo portal do admin-cliente."},
    )
    assert resposta_mesa.status_code == 200

    resposta_avaliar = client.post(
        f"/cliente/api/mesa/laudos/{laudo_mesa_aprovacao_id}/avaliar",
        headers={"X-CSRF-Token": csrf},
        json={"acao": "aprovar", "motivo": ""},
    )
    assert resposta_avaliar.status_code == 200

    resposta_auditoria = client.get("/cliente/api/auditoria")
    assert resposta_auditoria.status_code == 200
    itens = resposta_auditoria.json()["itens"]
    acoes = {item["acao"] for item in itens}
    assert {
        "chat_laudo_criado",
        "chat_mensagem_enviada",
        "chat_laudo_reaberto",
        "mesa_resposta_enviada",
        "mesa_laudo_avaliado",
    }.issubset(acoes)


def test_admin_cliente_reabrir_emitido_pode_ocultar_pdf_da_superficie_ativa(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_cliente(client, "cliente@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.APROVADO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Laudo emitido para entrega."
        laudo.nome_arquivo_pdf = "cliente_emitido.pdf"
        banco.commit()

    resposta = client.post(
        f"/cliente/api/chat/laudos/{laudo_id}/reabrir",
        headers={"X-CSRF-Token": csrf},
        json={"issued_document_policy": "hide_from_case"},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["issued_document_policy_applied"] == "hide_from_case"
    assert corpo["previous_issued_document_visible_in_case"] is False

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.nome_arquivo_pdf is None


def test_admin_cliente_resumo_empresa_explica_capacidade_e_upgrade_sugerido(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    _login_cliente(client, "cliente@empresa-a.test")

    with SessionLocal() as banco:
        _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        empresa.plano_ativo = PlanoEmpresa.INICIAL.value
        banco.commit()

    resposta = client.get("/cliente/api/empresa/resumo")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["plano_ativo"] == "Inicial"
    assert corpo["usuarios_em_uso"] == 3
    assert corpo["usuarios_max"] == 1
    assert corpo["usuarios_restantes"] == 0
    assert corpo["usuarios_excedente"] == 2
    assert corpo["laudos_mes_atual"] == 2
    assert corpo["laudos_mes_limite"] == 50
    assert corpo["laudos_restantes"] == 48
    assert corpo["capacidade_status"] == "critico"
    assert corpo["capacidade_tone"] == "ajustes"
    assert corpo["capacidade_gargalo"] == "usuarios"
    assert corpo["plano_sugerido"] == "Intermediario"
    assert "usuarios" in corpo["plano_sugerido_motivo"].lower()
    assert any(item["plano"] == "Intermediario" and item["sugerido"] is True for item in corpo["planos_catalogo"])
    assert any(item["canal"] == "admin" and "acessos" in item["badge"].lower() for item in corpo["avisos_operacionais"])
    saude = corpo["saude_operacional"]
    assert saude["historico_mensal"]
    assert saude["historico_diario"]
    assert saude["mix_equipe"]["inspetores"] >= 1
    assert saude["usuarios_ativos_total"] >= 1
    assert saude["status"]
    assert saude["tendencia_rotulo"]
