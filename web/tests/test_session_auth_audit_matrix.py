from __future__ import annotations

from sqlalchemy import select

from app.shared.database import RegistroAuditoriaEmpresa
from tests.regras_rotas_criticas_support import _csrf_pagina, _login_admin, _login_cliente


def test_logout_cliente_preserva_sessao_admin_no_mesmo_browser(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_admin(client, "admin@empresa-a.test")
    csrf_cliente = _login_cliente(client, "cliente@empresa-a.test")

    resposta_admin_antes = client.get("/admin/painel", follow_redirects=False)
    assert resposta_admin_antes.status_code == 200

    resposta_logout_cliente = client.post(
        "/cliente/logout",
        data={"csrf_token": csrf_cliente},
        follow_redirects=False,
    )
    assert resposta_logout_cliente.status_code == 303
    assert resposta_logout_cliente.headers["location"] == "/cliente/login"

    resposta_admin_depois = client.get("/admin/painel", follow_redirects=False)
    assert resposta_admin_depois.status_code == 200

    resposta_cliente_depois = client.get("/cliente/painel", follow_redirects=False)
    assert resposta_cliente_depois.status_code == 303
    assert resposta_cliente_depois.headers["location"] == "/cliente/login"


def test_logout_admin_preserva_sessao_cliente_no_mesmo_browser(ambiente_critico) -> None:
    client = ambiente_critico["client"]

    _login_cliente(client, "cliente@empresa-a.test")
    csrf_admin = _login_admin(client, "admin@empresa-a.test")

    resposta_cliente_antes = client.get("/cliente/painel", follow_redirects=False)
    assert resposta_cliente_antes.status_code == 200

    resposta_logout_admin = client.post(
        "/admin/logout",
        data={"csrf_token": csrf_admin},
        follow_redirects=False,
    )
    assert resposta_logout_admin.status_code == 303
    assert resposta_logout_admin.headers["location"] == "/admin/login"

    resposta_cliente_depois = client.get("/cliente/painel", follow_redirects=False)
    assert resposta_cliente_depois.status_code == 200

    resposta_admin_depois = client.get("/admin/painel", follow_redirects=False)
    assert resposta_admin_depois.status_code == 303
    assert resposta_admin_depois.headers["location"] == "/admin/login"


def test_admin_geral_registra_auditoria_duravel_em_acoes_criticas_do_tenant(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    csrf = _csrf_pagina(client, "/admin/painel")

    resposta_bloqueio = client.post(
        f"/admin/clientes/{ids['empresa_b']}/bloquear",
        data={"csrf_token": csrf, "motivo": "Inadimplência"},
        follow_redirects=False,
    )
    assert resposta_bloqueio.status_code == 303

    csrf = _csrf_pagina(client, "/admin/painel")
    resposta_plano = client.post(
        f"/admin/clientes/{ids['empresa_b']}/trocar-plano",
        data={"csrf_token": csrf, "plano": "Pro"},
        follow_redirects=False,
    )
    assert resposta_plano.status_code == 303

    with SessionLocal() as banco:
        itens = list(
            banco.scalars(
                select(RegistroAuditoriaEmpresa)
                .where(
                    RegistroAuditoriaEmpresa.empresa_id == ids["empresa_b"],
                    RegistroAuditoriaEmpresa.portal == "admin",
                )
                .order_by(RegistroAuditoriaEmpresa.id.asc())
            ).all()
        )

    acoes = [item.acao for item in itens]
    assert "tenant_block_toggled" in acoes
    assert "tenant_plan_changed" in acoes

    auditoria_bloqueio = next(item for item in itens if item.acao == "tenant_block_toggled")
    assert auditoria_bloqueio.ator_usuario_id == ids["admin_a"]
    assert auditoria_bloqueio.payload_json["blocked"] is True
    assert auditoria_bloqueio.payload_json["reason"] == "Inadimplência"
    assert "sessions_invalidated" in auditoria_bloqueio.payload_json

    auditoria_plano = next(item for item in itens if item.acao == "tenant_plan_changed")
    assert auditoria_plano.ator_usuario_id == ids["admin_a"]
    assert auditoria_plano.payload_json["plano_novo"] == "Intermediario"
    assert "impacto" in auditoria_plano.payload_json
