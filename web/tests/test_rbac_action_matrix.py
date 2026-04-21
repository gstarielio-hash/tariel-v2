from __future__ import annotations

from tests.regras_rotas_criticas_support import (
    _criar_laudo,
    _login_admin,
    _login_app_inspetor,
    _login_cliente,
    _login_revisor,
)
from app.shared.database import StatusRevisao


def test_rbac_matrix_mantem_superficies_criticas_separadas(ambiente_critico) -> None:
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

    client.cookies.clear()
    _login_revisor(client, "revisor@empresa-a.test")
    resposta_app_com_revisor = client.get("/app/api/laudo/status")
    assert resposta_app_com_revisor.status_code in {401, 403}

    client.cookies.clear()
    _login_app_inspetor(client, "inspetor@empresa-a.test")
    resposta_mesa_com_inspetor = client.get(f"/revisao/api/laudo/{laudo_id}/pacote")
    assert resposta_mesa_com_inspetor.status_code in {401, 403}

    client.cookies.clear()
    csrf_cliente = _login_cliente(client, "cliente@empresa-a.test")
    resposta_bootstrap_cliente = client.get("/cliente/api/bootstrap")
    assert resposta_bootstrap_cliente.status_code == 200
    resposta_chat_cliente = client.get("/cliente/api/chat/laudos", headers={"X-CSRF-Token": csrf_cliente})
    assert resposta_chat_cliente.status_code == 200
    resposta_mesa_cliente = client.get(
        f"/cliente/api/mesa/laudos/{laudo_id}/pacote",
        headers={"X-CSRF-Token": csrf_cliente},
    )
    assert resposta_mesa_cliente.status_code == 200
    resposta_app_bruto_com_admin_cliente = client.get("/app/api/laudo/status")
    assert resposta_app_bruto_com_admin_cliente.status_code in {401, 403}
    resposta_mesa_bruta_com_admin_cliente = client.get(f"/revisao/api/laudo/{laudo_id}/pacote")
    assert resposta_mesa_bruta_com_admin_cliente.status_code in {401, 403}
    resposta_admin_com_admin_cliente = client.get("/admin/api/metricas-grafico")
    assert resposta_admin_com_admin_cliente.status_code == 401

    client.cookies.clear()
    _login_admin(client, "admin@empresa-a.test")
    resposta_admin_metricas = client.get("/admin/api/metricas-grafico")
    assert resposta_admin_metricas.status_code == 200
    resposta_bootstrap_cliente_com_admin = client.get("/cliente/api/bootstrap")
    assert resposta_bootstrap_cliente_com_admin.status_code in {401, 403}
    resposta_mesa_bruta_com_admin = client.get(f"/revisao/api/laudo/{laudo_id}/pacote")
    assert resposta_mesa_bruta_com_admin.status_code in {401, 403}
    resposta_mobile_com_admin = client.get("/app/api/mobile/bootstrap")
    assert resposta_mobile_com_admin.status_code in {401, 403}
