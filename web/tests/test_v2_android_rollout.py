from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from starlette.requests import Request

from app.shared.database import Laudo, MensagemLaudo, NivelAcesso, StatusRevisao, TipoMensagem, Usuario
from app.v2.mobile_rollout import (
    HEADER_V2_CAPABILITIES_VERSION,
    HEADER_V2_ATTEMPTED,
    HEADER_V2_FALLBACK_REASON,
    HEADER_V2_GATE_SOURCE,
    HEADER_V2_ROLLOUT_BUCKET,
    HEADER_V2_ROUTE,
    MOBILE_V2_CAPABILITIES_VERSION,
    extract_mobile_v2_fallback_observation,
    resolve_mobile_v2_capabilities_for_user,
)
from tests.regras_rotas_criticas_support import SENHA_PADRAO


def _build_user(*, user_id: int = 17, empresa_id: int = 33) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        empresa_id=empresa_id,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def _build_request(path: str, headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [
                (key.lower().encode("utf-8"), value.encode("utf-8"))
                for key, value in headers.items()
            ],
            "query_string": b"",
            "session": {},
            "state": {},
        }
    )


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


def test_resolve_mobile_v2_rollout_suporta_allowlist_e_flags_de_rota(monkeypatch) -> None:
    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_PERCENT", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST", "33")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "0")

    capabilities = resolve_mobile_v2_capabilities_for_user(_build_user())

    assert capabilities.mobile_v2_reads_enabled is True
    assert capabilities.mobile_v2_feed_enabled is True
    assert capabilities.mobile_v2_thread_enabled is False
    assert capabilities.tenant_allowed is True
    assert capabilities.cohort_allowed is False
    assert capabilities.reason == "tenant_allowlisted"
    assert capabilities.source == "tenant_allowlist"
    assert capabilities.thread_reason == "thread_route_disabled"
    assert capabilities.thread_source == "route_flag"
    assert capabilities.capabilities_version == MOBILE_V2_CAPABILITIES_VERSION


def test_resolve_mobile_v2_rollout_suporta_allowlist_por_coorte(monkeypatch) -> None:
    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_PERCENT", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST", "")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")

    baseline = resolve_mobile_v2_capabilities_for_user(_build_user(empresa_id=23))
    assert baseline.rollout_bucket is not None
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_ROLLOUT_COHORT_ALLOWLIST",
        str(baseline.rollout_bucket),
    )

    capabilities = resolve_mobile_v2_capabilities_for_user(_build_user(empresa_id=23))

    assert capabilities.rollout_bucket == baseline.rollout_bucket
    assert capabilities.mobile_v2_reads_enabled is True
    assert capabilities.cohort_allowed is True
    assert capabilities.reason == "cohort_allowlisted"
    assert capabilities.source == "cohort_allowlist"


def test_resolve_mobile_v2_rollout_permanece_conservador_fora_da_coorte(monkeypatch) -> None:
    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_PERCENT", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST", "")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_COHORT_ALLOWLIST", "")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")

    capabilities = resolve_mobile_v2_capabilities_for_user(_build_user())

    assert capabilities.mobile_v2_reads_enabled is False
    assert capabilities.reason == "cohort_not_allowed"
    assert capabilities.source == "cohort"


def test_extract_mobile_v2_fallback_observation_sanitiza_headers() -> None:
    request = _build_request(
        "/app/api/mobile/mesa/feed",
        {
            HEADER_V2_ATTEMPTED: "1",
            HEADER_V2_ROUTE: "thread",
            HEADER_V2_FALLBACK_REASON: "rollout_denied",
            HEADER_V2_GATE_SOURCE: "cohort bucket#42",
            HEADER_V2_CAPABILITIES_VERSION: "2026-03-25.09c",
            HEADER_V2_ROLLOUT_BUCKET: "42",
        },
    )

    observation = extract_mobile_v2_fallback_observation(request)

    assert observation == {
        "route": "thread",
        "reason": "rollout_denied",
        "gate_source": "cohort_bucket_42",
        "capabilities_version": "2026-03-25.09c",
        "client_rollout_bucket": 42,
    }


def test_capabilities_endpoint_retorna_shape_minimo_do_rollout(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    headers = _login_mobile_inspetor(client)

    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_PERCENT", "100")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", "")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES", "")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_TENANT_KEY", "")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROMOTED_SINCE", "")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_ROLLOUT_WINDOW_STARTED_AT", "")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_SOURCE", "")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_NOTE", "")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "0")

    resposta = client.get("/app/api/mobile/v2/capabilities", headers=headers)

    assert resposta.status_code == 200
    payload = resposta.json()
    assert payload["contract_name"] == "MobileInspectorCapabilitiesV2"
    assert payload["contract_version"] == "v2"
    assert payload["capabilities_version"] == MOBILE_V2_CAPABILITIES_VERSION
    assert payload["mobile_v2_reads_enabled"] is True
    assert payload["mobile_v2_feed_enabled"] is True
    assert payload["mobile_v2_thread_enabled"] is False
    assert payload["tenant_allowed"] is False
    assert payload["cohort_allowed"] is True
    assert payload["rollout_bucket"] is not None
    assert payload["thread_reason"] == "thread_route_disabled"


def test_endpoints_legados_preservam_payload_quando_recebem_headers_de_fallback(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    headers = _login_mobile_inspetor(client)

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="Rollout Legacy Preservation",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Fallback para legado do rollout mobile V2",
        )
        banco.add(laudo)
        banco.flush()
        banco.add(
            MensagemLaudo(
                laudo_id=laudo.id,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mesa continua visivel via legado.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        laudo.atualizado_em = datetime.now(timezone.utc)
        banco.commit()
        laudo_id = int(laudo.id)

    headers_feed = {
        **headers,
        HEADER_V2_ATTEMPTED: "1",
        HEADER_V2_ROUTE: "feed",
        HEADER_V2_FALLBACK_REASON: "rollout_denied",
        HEADER_V2_GATE_SOURCE: "cohort",
        HEADER_V2_CAPABILITIES_VERSION: MOBILE_V2_CAPABILITIES_VERSION,
        HEADER_V2_ROLLOUT_BUCKET: "12",
    }
    resposta_feed = client.get(
        "/app/api/mobile/mesa/feed",
        headers=headers_feed,
        params={"laudo_ids": str(laudo_id)},
    )
    assert resposta_feed.status_code == 200
    payload_feed = resposta_feed.json()
    assert payload_feed["laudo_ids"] == [laudo_id]
    assert payload_feed["itens"][0]["laudo_id"] == laudo_id

    headers_thread = {
        **headers,
        HEADER_V2_ATTEMPTED: "1",
        HEADER_V2_ROUTE: "thread",
        HEADER_V2_FALLBACK_REASON: "http_404",
        HEADER_V2_GATE_SOURCE: "v2_read",
        HEADER_V2_CAPABILITIES_VERSION: MOBILE_V2_CAPABILITIES_VERSION,
        HEADER_V2_ROLLOUT_BUCKET: "12",
    }
    resposta_thread = client.get(
        f"/app/api/laudo/{laudo_id}/mesa/mensagens",
        headers=headers_thread,
    )
    assert resposta_thread.status_code == 200
    payload_thread = resposta_thread.json()
    assert payload_thread["laudo_id"] == laudo_id
    assert len(payload_thread["itens"]) == 1
