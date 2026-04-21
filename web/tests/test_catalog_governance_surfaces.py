from __future__ import annotations

import json

import app.domains.admin.services as admin_services

from app.shared.database import Laudo, StatusRevisao
from app.shared.tenant_report_catalog import (
    build_catalog_selection_token,
    resolve_runtime_template_code,
)
from tests.regras_rotas_criticas_support import (
    SENHA_PADRAO,
    _criar_laudo,
    _login_app_inspetor,
    _login_cliente,
    _login_revisor,
)


def _upsert_family_with_single_variant(
    *,
    banco,
    family_key: str,
    family_label: str,
    macro_categoria: str,
    variant_key: str,
    variant_label: str,
    template_code: str,
    admin_id: int,
) -> str:
    admin_services.upsert_familia_catalogo(
        banco,
        family_key=family_key,
        nome_exibicao=family_label,
        macro_categoria=macro_categoria,
        status_catalogo="publicado",
        criado_por_id=admin_id,
    )
    admin_services.upsert_oferta_comercial_familia(
        banco,
        family_key=family_key,
        nome_oferta=f"{family_label} · Oferta principal",
        pacote_comercial="Prime",
        ativo_comercial=True,
        variantes_comerciais_text=json.dumps(
            [
                {
                    "variant_key": variant_key,
                    "nome_exibicao": variant_label,
                    "template_code": template_code,
                }
            ]
        ),
        criado_por_id=admin_id,
    )
    return build_catalog_selection_token(family_key, variant_key)


def _option_values(items: list[dict[str, object]]) -> set[str]:
    return {
        str(item.get("value") or item.get("selection_token") or "").strip()
        for item in items
        if str(item.get("value") or item.get("selection_token") or "").strip()
    }


def _assert_surface_scope(payload: dict[str, object], *, expected_tokens: set[str]) -> None:
    assert bool(payload["catalog_governed_mode"]) is True
    assert str(payload["catalog_state"]) == "managed_active"
    assert _option_values(list(payload["tipo_template_options"] or [])) == expected_tokens


def test_admin_ceo_catalog_scope_propagates_to_admin_cliente_inspetor_mobile_e_mesa(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    family_nr35 = "nr35_inspecao_ponto_ancoragem"
    family_nr13 = "nr13_inspecao_caldeira"
    token_nr35 = ""
    token_nr13 = ""
    runtime_nr35 = ""
    runtime_nr13 = ""
    laudo_id = 0

    with SessionLocal() as banco:
        token_nr35 = _upsert_family_with_single_variant(
            banco=banco,
            family_key=family_nr35,
            family_label="NR35 · Ponto de ancoragem",
            macro_categoria="NR35",
            variant_key="prime_site",
            variant_label="Prime Site",
            template_code="nr35_ponto_ancoragem",
            admin_id=ids["admin_a"],
        )
        token_nr13 = _upsert_family_with_single_variant(
            banco=banco,
            family_key=family_nr13,
            family_label="NR13 · Caldeira",
            macro_categoria="NR13",
            variant_key="premium_campo",
            variant_label="Premium Campo",
            template_code="nr13",
            admin_id=ids["admin_a"],
        )
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[token_nr35, token_nr13],
            admin_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key=family_nr35,
            release_status="active",
            allowed_variants=[token_nr35],
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key=family_nr13,
            release_status="active",
            allowed_variants=[token_nr13],
            criado_por_id=ids["admin_a"],
        )
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
            tipo_template="nr35_ponto_ancoragem",
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.catalog_selection_token = token_nr35
        laudo.catalog_family_key = family_nr35
        laudo.catalog_family_label = "NR35 · Ponto de ancoragem"
        laudo.catalog_variant_key = "prime_site"
        laudo.catalog_variant_label = "Prime Site"
        banco.commit()

    runtime_nr35 = str(
        resolve_runtime_template_code(
            family_key=family_nr35,
            template_code="nr35_ponto_ancoragem",
            variant_key="prime_site",
        )
        or ""
    )
    runtime_nr13 = str(
        resolve_runtime_template_code(
            family_key=family_nr13,
            template_code="nr13",
            variant_key="premium_campo",
        )
        or ""
    )
    expected_tokens = {token_nr35, token_nr13}
    expected_runtime_codes = {runtime_nr35, runtime_nr13}

    _login_cliente(client, "cliente@empresa-a.test")
    bootstrap_cliente = client.get("/cliente/api/bootstrap")
    assert bootstrap_cliente.status_code == 200
    chat_cliente = bootstrap_cliente.json()["chat"]
    _assert_surface_scope(chat_cliente, expected_tokens=expected_tokens)

    _login_app_inspetor(client, "inspetor@empresa-a.test")
    status_inspetor = client.get("/app/api/laudo/status")
    assert status_inspetor.status_code == 200
    payload_status = status_inspetor.json()
    _assert_surface_scope(payload_status, expected_tokens=expected_tokens)
    assert set(payload_status["tipos_relatorio"]) == expected_runtime_codes

    resposta_login_mobile = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "lembrar": True,
        },
    )
    assert resposta_login_mobile.status_code == 200
    headers_mobile = {
        "Authorization": f"Bearer {resposta_login_mobile.json()['access_token']}"
    }
    bootstrap_mobile = client.get("/app/api/mobile/bootstrap", headers=headers_mobile)
    assert bootstrap_mobile.status_code == 200
    payload_mobile = bootstrap_mobile.json()
    _assert_surface_scope(payload_mobile, expected_tokens=expected_tokens)
    assert set(payload_mobile["tipos_relatorio"]) == expected_runtime_codes

    _login_revisor(client, "revisor@empresa-a.test")
    pacote_mesa = client.get(f"/revisao/api/laudo/{laudo_id}/pacote")
    assert pacote_mesa.status_code == 200
    payload_mesa = pacote_mesa.json()["catalog_template_scope"]
    _assert_surface_scope(payload_mesa, expected_tokens=expected_tokens)
    assert payload_mesa["active_binding"]["selection_token"] == token_nr35
    assert payload_mesa["family_governance"]["release_active"] is True

    with SessionLocal() as banco:
        admin_services.sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=ids["empresa_a"],
            selection_tokens=[token_nr35],
            admin_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key=family_nr13,
            release_status="paused",
            allowed_variants=[token_nr13],
            criado_por_id=ids["admin_a"],
        )
        banco.commit()

    expected_tokens_after_revoke = {token_nr35}
    expected_runtime_after_revoke = {runtime_nr35}

    _login_cliente(client, "cliente@empresa-a.test")
    bootstrap_cliente_restrito = client.get("/cliente/api/bootstrap")
    assert bootstrap_cliente_restrito.status_code == 200
    _assert_surface_scope(
        bootstrap_cliente_restrito.json()["chat"],
        expected_tokens=expected_tokens_after_revoke,
    )

    _login_app_inspetor(client, "inspetor@empresa-a.test")
    status_inspetor_restrito = client.get("/app/api/laudo/status")
    assert status_inspetor_restrito.status_code == 200
    payload_status_restrito = status_inspetor_restrito.json()
    _assert_surface_scope(
        payload_status_restrito,
        expected_tokens=expected_tokens_after_revoke,
    )
    assert set(payload_status_restrito["tipos_relatorio"]) == expected_runtime_after_revoke

    bootstrap_mobile_restrito = client.get(
        "/app/api/mobile/bootstrap",
        headers=headers_mobile,
    )
    assert bootstrap_mobile_restrito.status_code == 200
    payload_mobile_restrito = bootstrap_mobile_restrito.json()
    _assert_surface_scope(
        payload_mobile_restrito,
        expected_tokens=expected_tokens_after_revoke,
    )
    assert set(payload_mobile_restrito["tipos_relatorio"]) == expected_runtime_after_revoke

    _login_revisor(client, "revisor@empresa-a.test")
    pacote_mesa_restrito = client.get(f"/revisao/api/laudo/{laudo_id}/pacote")
    assert pacote_mesa_restrito.status_code == 200
    payload_mesa_restrito = pacote_mesa_restrito.json()["catalog_template_scope"]
    _assert_surface_scope(
        payload_mesa_restrito,
        expected_tokens=expected_tokens_after_revoke,
    )
    assert payload_mesa_restrito["active_binding"]["selection_token"] == token_nr35
    assert payload_mesa_restrito["family_governance"]["release_active"] is True
