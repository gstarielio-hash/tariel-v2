from __future__ import annotations

import uuid

import main
from app.shared.database import NivelAcesso
from app.shared.security import obter_usuario_html
from app.shared.database import Laudo, StatusRevisao, Usuario
from app.v2.mobile_rollout import (
    HEADER_V2_ATTEMPTED,
    HEADER_V2_CAPABILITIES_VERSION,
    HEADER_V2_FALLBACK_REASON,
    HEADER_V2_GATE_SOURCE,
    HEADER_V2_ROLLOUT_BUCKET,
    HEADER_V2_ROUTE,
    MOBILE_V2_CAPABILITIES_VERSION,
)
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    get_mobile_v2_rollout_operational_summary,
    record_mobile_v2_capabilities_check,
    record_mobile_v2_legacy_fallback,
    record_mobile_v2_public_read,
)
from tests.regras_rotas_criticas_support import SENHA_PADRAO


def _login_mobile_inspetor(client) -> dict[str, str]:
    resposta = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "lembrar": True,
        },
    )
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def test_mobile_v2_rollout_metrics_agregam_por_tenant_endpoint_e_reason() -> None:
    clear_mobile_v2_rollout_metrics_for_tests()

    record_mobile_v2_capabilities_check(
        tenant_key="33",
        rollout_bucket=42,
        capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
        reason="cohort_rollout",
        source="cohort",
        feed_enabled=True,
        feed_reason="cohort_rollout",
        thread_enabled=False,
        thread_reason="thread_route_disabled",
    )
    record_mobile_v2_public_read(
        tenant_key="33",
        endpoint="feed",
        reason="cohort_rollout",
        source="cohort",
        rollout_bucket=42,
        capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
    )
    record_mobile_v2_legacy_fallback(
        tenant_key="33",
        endpoint="thread",
        reason="http_error",
        source="v2_read",
        rollout_bucket=42,
        capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
    )

    payload = get_mobile_v2_rollout_operational_summary()

    assert payload["totals"] == {
        "capabilities_checks": 1,
        "rollout_denied": 1,
        "v2_served": 1,
        "legacy_fallbacks": 1,
    }
    assert any(
        item["tenant_key"] == "33"
        and item["v2_served"] == 1
        and item["legacy_fallbacks"] == 1
        for item in payload["by_tenant"]
    )
    assert any(
        item["endpoint"] == "thread" and item["rollout_denied"] == 1
        for item in payload["by_endpoint"]
    )
    assert any(
        item["kind"] == "legacy_fallbacks"
        and item["reason"] == "http_error"
        and item["count"] == 1
        for item in payload["by_reason"]
    )
    assert any(
        item["rollout_bucket"] == 42 and item["v2_served"] == 1
        for item in payload["by_cohort_bucket"]
    )


def test_admin_summary_endpoint_permanece_protegido_e_mostra_piloto(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    assert client.get("/admin/api/mobile-v2-rollout/summary").status_code == 401

    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY", "1")

    headers = _login_mobile_inspetor(client)

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="Piloto Mobile V2",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Piloto do rollout mobile V2.",
        )
        banco.add(laudo)
        banco.commit()
        laudo_id = int(laudo.id)

    resposta_capabilities = client.get(
        "/app/api/mobile/v2/capabilities",
        headers=headers,
    )
    assert resposta_capabilities.status_code == 200

    resposta_feed_v2 = client.get(
        "/app/api/mobile/v2/mesa/feed",
        headers={
            **headers,
            HEADER_V2_ATTEMPTED: "1",
            HEADER_V2_ROUTE: "feed",
            HEADER_V2_CAPABILITIES_VERSION: MOBILE_V2_CAPABILITIES_VERSION,
            HEADER_V2_ROLLOUT_BUCKET: "12",
        },
        params={"laudo_ids": str(laudo_id)},
    )
    assert resposta_feed_v2.status_code == 200

    resposta_feed_legado = client.get(
        "/app/api/mobile/mesa/feed",
        headers={
            **headers,
            HEADER_V2_ATTEMPTED: "1",
            HEADER_V2_ROUTE: "feed",
            HEADER_V2_FALLBACK_REASON: "http_error",
            HEADER_V2_GATE_SOURCE: "v2_read",
            HEADER_V2_CAPABILITIES_VERSION: MOBILE_V2_CAPABILITIES_VERSION,
            HEADER_V2_ROLLOUT_BUCKET: "12",
        },
        params={"laudo_ids": str(laudo_id)},
    )
    assert resposta_feed_legado.status_code == 200

    main.app.dependency_overrides[obter_usuario_html] = lambda: Usuario(
        id=ids["admin_a"],
        empresa_id=ids["empresa_a"],
        nivel_acesso=NivelAcesso.DIRETORIA.value,
        email="admin@empresa-a.test",
    )
    resposta_summary = client.get("/admin/api/mobile-v2-rollout/summary")
    main.app.dependency_overrides.pop(obter_usuario_html, None)

    assert resposta_summary.status_code == 200
    payload = resposta_summary.json()
    assert payload["contract_name"] == "MobileInspectorPilotObservabilityV1"
    assert payload["contract_version"] == "v1"
    assert payload["observability_enabled"] is True
    assert payload["totals"]["capabilities_checks"] >= 1
    assert payload["totals"]["v2_served"] >= 1
    assert payload["totals"]["legacy_fallbacks"] >= 1
    assert any(
        item["tenant_key"] == str(ids["empresa_a"]) and item["v2_served"] >= 1
        for item in payload["by_tenant"]
    )
    assert any(
        item["endpoint"] == "feed" and item["legacy_fallbacks"] >= 1
        for item in payload["by_endpoint"]
    )
    assert any(
        item["kind"] == "legacy_fallbacks" and item["reason"] == "http_error"
        for item in payload["by_reason"]
    )
