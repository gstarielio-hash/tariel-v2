from __future__ import annotations

import uuid

from app.shared.database import Laudo, StatusRevisao, Usuario
from app.v2.mobile_rollout import (
    HEADER_MOBILE_CENTRAL_TRACE,
    HEADER_V2_ATTEMPTED,
    HEADER_V2_CAPABILITIES_VERSION,
    HEADER_V2_FALLBACK_REASON,
    HEADER_V2_GATE_SOURCE,
    HEADER_V2_OPERATOR_RUN,
    HEADER_V2_ROLLOUT_BUCKET,
    HEADER_V2_ROUTE,
    HEADER_V2_VALIDATION_SESSION,
    MOBILE_V2_CAPABILITIES_VERSION,
)
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    get_mobile_v2_rollout_operational_summary,
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


def _criar_laudo_demo(SessionLocal, ids: dict[str, int]) -> int:
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
            primeira_mensagem="Diagnóstico do trace do feed da central.",
        )
        banco.add(laudo)
        banco.commit()
        return int(laudo.id)


def test_request_trace_gap_summary_captura_recebimento_e_contagem_das_rotas_reais(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY", "1")

    headers = _login_mobile_inspetor(client)
    laudo_id = _criar_laudo_demo(SessionLocal, ids)
    trace_v2 = "feed-trace-v2-80"
    trace_legacy = "feed-trace-legacy-80"

    resposta_v2 = client.get(
        "/app/api/mobile/v2/mesa/feed",
        headers={
            **headers,
            HEADER_MOBILE_CENTRAL_TRACE: trace_v2,
            HEADER_V2_ATTEMPTED: "1",
            HEADER_V2_ROUTE: "feed",
            HEADER_V2_CAPABILITIES_VERSION: MOBILE_V2_CAPABILITIES_VERSION,
            HEADER_V2_ROLLOUT_BUCKET: "12",
            HEADER_V2_VALIDATION_SESSION: "orgv_09q",
            HEADER_V2_OPERATOR_RUN: "oprv_09q",
        },
        params={"laudo_ids": str(laudo_id)},
    )
    assert resposta_v2.status_code == 200

    resposta_legacy = client.get(
        "/app/api/mobile/mesa/feed",
        headers={
            **headers,
            HEADER_MOBILE_CENTRAL_TRACE: trace_legacy,
            HEADER_V2_ATTEMPTED: "1",
            HEADER_V2_ROUTE: "feed",
            HEADER_V2_FALLBACK_REASON: "http_error",
            HEADER_V2_GATE_SOURCE: "v2_read",
            HEADER_V2_CAPABILITIES_VERSION: MOBILE_V2_CAPABILITIES_VERSION,
            HEADER_V2_ROLLOUT_BUCKET: "12",
            HEADER_V2_VALIDATION_SESSION: "orgv_09q",
            HEADER_V2_OPERATOR_RUN: "oprv_09q",
        },
        params={"laudo_ids": str(laudo_id)},
    )
    assert resposta_legacy.status_code == 200

    traces = get_mobile_v2_rollout_operational_summary()["request_traces_recent"]
    v2_traces = [item for item in traces if item["trace_id"] == trace_v2]
    legacy_traces = [item for item in traces if item["trace_id"] == trace_legacy]

    assert any(
        item["phase"] == "received_route"
        and item["delivery_path"] == "v2"
        and item["route"] == "/app/api/mobile/v2/mesa/feed"
        and item["validation_session_id"] == "orgv_09q"
        and item["operator_run_id"] == "oprv_09q"
        for item in v2_traces
    )
    assert any(
        item["phase"] == "counted"
        and item["counted_kind"] == "v2_served"
        and item["delivery_path"] == "v2"
        for item in v2_traces
    )
    assert any(
        item["phase"] == "received_route"
        and item["delivery_path"] == "legacy"
        and item["route"] == "/app/api/mobile/mesa/feed"
        for item in legacy_traces
    )
    assert any(
        item["phase"] == "counted"
        and item["counted_kind"] == "legacy_fallbacks"
        and item["delivery_path"] == "legacy"
        for item in legacy_traces
    )


def test_request_trace_gap_summary_mantem_recebimento_legacy_mesmo_sem_headers_v2(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY", "1")

    headers = _login_mobile_inspetor(client)
    laudo_id = _criar_laudo_demo(SessionLocal, ids)
    trace_legacy = "feed-trace-legacy-puro-80"

    resposta = client.get(
        "/app/api/mobile/mesa/feed",
        headers={
            **headers,
            HEADER_MOBILE_CENTRAL_TRACE: trace_legacy,
        },
        params={"laudo_ids": str(laudo_id)},
    )
    assert resposta.status_code == 200

    traces = get_mobile_v2_rollout_operational_summary()["request_traces_recent"]
    matching = [item for item in traces if item["trace_id"] == trace_legacy]

    assert any(
        item["phase"] == "received_route"
        and item["delivery_path"] == "legacy"
        and item["attempted"] is False
        and item["counted_kind"] is None
        for item in matching
    )
