from __future__ import annotations

import app.domains.admin.services as admin_services

from app.domains.chat.auth_mobile_support import montar_contexto_portal_inspetor
from app.shared.database import Empresa, StatusRevisao, Usuario
from tests.regras_rotas_criticas_support import (
    SENHA_PADRAO,
    _criar_laudo,
    _csrf_pagina,
    _login_admin,
    _login_app_inspetor,
    _login_cliente,
    _login_revisor,
)


def test_tenant_boundary_matrix_isola_inspetor_web_por_tenant(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_empresa_a = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo_empresa_b = _criar_laudo(
            banco,
            empresa_id=ids["empresa_b"],
            usuario_id=ids["inspetor_b"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    _login_app_inspetor(client, "inspetor@empresa-a.test")

    resposta_empresa_a = client.get(f"/app/api/laudo/{laudo_empresa_a}/mensagens")
    assert resposta_empresa_a.status_code == 200

    resposta_empresa_b = client.get(f"/app/api/laudo/{laudo_empresa_b}/mensagens")
    assert resposta_empresa_b.status_code == 404


def test_tenant_boundary_matrix_isola_mobile_inspetor_por_tenant(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_empresa_a = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo_empresa_b = _criar_laudo(
            banco,
            empresa_id=ids["empresa_b"],
            usuario_id=ids["inspetor_b"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    resposta_login = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "lembrar": True,
        },
    )
    assert resposta_login.status_code == 200
    access_token = resposta_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    resposta_bootstrap = client.get("/app/api/mobile/bootstrap", headers=headers)
    assert resposta_bootstrap.status_code == 200
    assert resposta_bootstrap.json()["usuario"]["empresa_nome"] == "Empresa A"

    resposta_laudos = client.get("/app/api/mobile/laudos", headers=headers)
    assert resposta_laudos.status_code == 200
    laudo_ids = {int(item["id"]) for item in resposta_laudos.json()["itens"]}
    assert laudo_empresa_a in laudo_ids
    assert laudo_empresa_b not in laudo_ids


def test_tenant_boundary_matrix_mobile_respeita_revogacao_catalogada_sem_afetar_outro_tenant(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    selection_token = "catalog:nr35_inspecao_ponto_ancoragem:prime_site"

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr35_inspecao_ponto_ancoragem",
            nome_exibicao="NR35 · Ponto de ancoragem",
            macro_categoria="NR35",
            status_catalogo="publicado",
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_oferta_comercial_familia(
            banco,
            family_key="nr35_inspecao_ponto_ancoragem",
            nome_oferta="NR35 Prime · Ponto de ancoragem",
            pacote_comercial="Prime",
            ativo_comercial=True,
            variantes_comerciais_text="prime_site | Prime site | nr35_prime | Campo premium",
            criado_por_id=ids["admin_a"],
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[],
            admin_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr35_inspecao_ponto_ancoragem",
            release_status="paused",
            allowed_variants=[selection_token],
            criado_por_id=ids["admin_a"],
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_b"],
            selection_tokens=[selection_token],
            admin_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_b"],
            family_key="nr35_inspecao_ponto_ancoragem",
            release_status="active",
            allowed_variants=[selection_token],
            criado_por_id=ids["admin_a"],
        )
        banco.commit()

    with SessionLocal() as banco:
        usuario_a = banco.get(Usuario, ids["inspetor_a"])
        usuario_b = banco.get(Usuario, ids["inspetor_b"])
        assert usuario_a is not None
        assert usuario_b is not None

        contexto_a = montar_contexto_portal_inspetor(banco, usuario=usuario_a)
        contexto_b = montar_contexto_portal_inspetor(banco, usuario=usuario_b)

    tipos_a = {str(item.get("value") or "") for item in contexto_a["tipos_template_portal"]}
    tipos_b = {str(item.get("value") or "") for item in contexto_b["tipos_template_portal"]}
    modelos_a = {str(item.get("tipo") or "") for item in contexto_a["modelos_portal"]}
    modelos_b = {str(item.get("tipo") or "") for item in contexto_b["modelos_portal"]}

    assert contexto_a["catalog_governed_mode"] is True
    assert contexto_b["catalog_governed_mode"] is True
    assert selection_token not in tipos_a
    assert selection_token not in modelos_a
    assert selection_token in tipos_b
    assert selection_token in modelos_b


def test_tenant_boundary_matrix_isola_mesa_web_por_tenant(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_empresa_a = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo_empresa_b = _criar_laudo(
            banco,
            empresa_id=ids["empresa_b"],
            usuario_id=ids["inspetor_b"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    _login_revisor(client, "revisor@empresa-a.test")

    resposta_empresa_a = client.get(f"/revisao/api/laudo/{laudo_empresa_a}/pacote")
    assert resposta_empresa_a.status_code == 200

    resposta_empresa_b = client.get(f"/revisao/api/laudo/{laudo_empresa_b}/pacote")
    assert resposta_empresa_b.status_code == 404


def test_tenant_boundary_matrix_isola_admin_cliente_mesmo_com_recortes_operacionais(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        laudo_empresa_a = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo_empresa_b = _criar_laudo(
            banco,
            empresa_id=ids["empresa_b"],
            usuario_id=ids["inspetor_b"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    csrf = _login_cliente(client, "cliente@empresa-a.test")

    resposta_bootstrap = client.get("/cliente/api/bootstrap")
    assert resposta_bootstrap.status_code == 200
    assert resposta_bootstrap.json()["empresa"]["nome_fantasia"] == "Empresa A"

    resposta_empresa_a = client.get(
        f"/cliente/api/mesa/laudos/{laudo_empresa_a}/pacote",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_empresa_a.status_code == 200

    resposta_chat_empresa_b = client.get(
        f"/cliente/api/chat/laudos/{laudo_empresa_b}/mensagens",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_chat_empresa_b.status_code == 404

    resposta_mesa_empresa_b = client.get(
        f"/cliente/api/mesa/laudos/{laudo_empresa_b}/pacote",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_mesa_empresa_b.status_code == 404


def test_tenant_boundary_matrix_admin_geral_usa_alvo_explicito_de_tenant(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/painel")

    resposta = client.post(
        f"/admin/clientes/{ids['empresa_b']}/bloquear",
        data={"csrf_token": csrf, "motivo": "Inadimplência"},
        follow_redirects=False,
    )
    assert resposta.status_code == 303

    with SessionLocal() as banco:
        empresa_a = banco.get(Empresa, ids["empresa_a"])
        empresa_b = banco.get(Empresa, ids["empresa_b"])
        assert empresa_a is not None
        assert empresa_b is not None
        assert bool(empresa_a.status_bloqueio) is False
        assert bool(empresa_b.status_bloqueio) is True
