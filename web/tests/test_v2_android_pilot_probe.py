from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.shared.database import Empresa, Laudo, MensagemLaudo, StatusRevisao, TipoMensagem
from app.shared.database import NivelAcesso, Usuario
from app.shared.security import obter_usuario_html
import main
from app.v2.mobile_probe import run_demo_mobile_v2_pilot_probe
from app.v2.mobile_rollout import MOBILE_V2_CAPABILITIES_VERSION
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    get_mobile_v2_rollout_operational_summary,
    record_mobile_v2_public_read,
)


def _configure_demo_probe_rollout(ambiente_critico, monkeypatch) -> None:
    tenant_key = str(ambiente_critico["ids"]["empresa_a"])
    started_at = (
        datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=2)
    ).isoformat().replace("+00:00", "Z")

    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", f"{tenant_key}=pilot_enabled")
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES",
        f"{tenant_key}:feed=promoted,{tenant_key}:thread=promoted",
    )
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_TENANT_KEY", tenant_key)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROMOTED_SINCE", started_at)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_ROLLOUT_WINDOW_STARTED_AT", started_at)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_ROLLBACK_WINDOW_HOURS", "24")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_SOURCE", "seed_dev_demo_company")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_NOTE", "probe_ready_demo")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MIN_REQUESTS", "5")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MAX_FALLBACK_RATE_PERCENT", "15")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MAX_VISIBILITY_VIOLATIONS", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MAX_PARSE_ERRORS", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MAX_HTTP_FAILURES", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_REQUIRE_FULL_WINDOW", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_ALLOW_CANDIDATE_WITHOUT_WINDOW_ELAPSED", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROBE_MAX_REQUESTS_PER_SURFACE", "5")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROBE_TARGET_LIMIT", "2")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROBE_TIMEOUT_MS", "8000")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROBE_DELAY_MS", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROBE_INCLUDE_LEGACY_COMPARE", "0")


def _prepare_demo_tenant_for_probe(ambiente_critico) -> dict[str, int]:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        empresa.nome_fantasia = "Empresa Demo (DEV)"
        empresa.cnpj = "00000000000000"

        laudo_feed = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="Probe Feed",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Probe feed",
        )
        laudo_thread = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="Probe Thread",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Probe thread",
        )
        banco.add_all([laudo_feed, laudo_thread])
        banco.flush()
        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo_feed.id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Mensagem segura para feed.",
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo_thread.id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Mensagem segura para thread.",
                    custo_api_reais=Decimal("0.0000"),
                ),
            ]
        )
        banco.commit()
        return {
            "feed_laudo_id": int(laudo_feed.id),
            "thread_laudo_id": int(laudo_thread.id),
        }


def test_probe_nao_executa_sem_flag(ambiente_critico, monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_demo_probe_rollout(ambiente_critico, monkeypatch)
    _prepare_demo_tenant_for_probe(ambiente_critico)
    monkeypatch.delenv("TARIEL_V2_ANDROID_PILOT_PROBE", raising=False)

    result = run_demo_mobile_v2_pilot_probe(trigger_source="test")
    summary = get_mobile_v2_rollout_operational_summary()

    assert result.status == "disabled"
    assert result.ok is False
    assert summary["probe_requests_v2"] == 0
    assert summary["probe_requests_fallback"] == 0


def test_probe_nao_executa_fora_do_tenant_demo_seguro(ambiente_critico, monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_demo_probe_rollout(ambiente_critico, monkeypatch)
    _prepare_demo_tenant_for_probe(ambiente_critico)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROBE", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_TENANT_KEY", str(ambiente_critico["ids"]["empresa_b"]))

    result = run_demo_mobile_v2_pilot_probe(trigger_source="test")

    assert result.status == "blocked"
    assert result.detail == "pilot_tenant_not_safe_for_probe"


def test_probe_atualiza_metricas_sem_side_effects_de_negocio(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_demo_probe_rollout(ambiente_critico, monkeypatch)
    _prepare_demo_tenant_for_probe(ambiente_critico)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROBE", "1")
    SessionLocal = ambiente_critico["SessionLocal"]

    with SessionLocal() as banco:
        before_laudos = int(banco.scalar(select(func.count()).select_from(Laudo)) or 0)
        before_mensagens = int(
            banco.scalar(select(func.count()).select_from(MensagemLaudo)) or 0
        )

    result = run_demo_mobile_v2_pilot_probe(trigger_source="test")
    summary = get_mobile_v2_rollout_operational_summary()
    tenant_rows = {
        row["tenant_key"]: row for row in summary["tenant_rollout_states"]
    }
    surface_rows = {
        (row["tenant_key"], row["surface"]): row for row in summary["tenant_surface_states"]
    }

    with SessionLocal() as banco:
        after_laudos = int(banco.scalar(select(func.count()).select_from(Laudo)) or 0)
        after_mensagens = int(
            banco.scalar(select(func.count()).select_from(MensagemLaudo)) or 0
        )

    tenant_key = str(ambiente_critico["ids"]["empresa_a"])
    assert result.ok is True
    assert result.status == "completed"
    assert result.probe_requests_v2 == 10
    assert result.probe_requests_fallback == 0
    assert before_laudos == after_laudos
    assert before_mensagens == after_mensagens
    assert summary["probe_active"] is True
    assert summary["probe_requests_v2"] == 10
    assert summary["probe_requests_fallback"] == 0
    assert summary["probe_last_run_at"] is not None
    assert set(summary["probe_surfaces_exercised"]) == {"feed", "thread"}
    assert tenant_rows[tenant_key]["pilot_outcome"] == "healthy"
    assert tenant_rows[tenant_key]["probe_resolved_insufficient_evidence"] is True
    assert tenant_rows[tenant_key]["candidate_for_real_tenant"] is False
    assert surface_rows[(tenant_key, "feed")]["probe_requests_v2"] == 5
    assert surface_rows[(tenant_key, "thread")]["probe_requests_v2"] == 5


def test_summary_distingue_probe_de_uso_organico(ambiente_critico, monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_demo_probe_rollout(ambiente_critico, monkeypatch)
    _prepare_demo_tenant_for_probe(ambiente_critico)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROBE", "1")

    result = run_demo_mobile_v2_pilot_probe(trigger_source="test")
    assert result.ok is True

    record_mobile_v2_public_read(
        tenant_key=str(ambiente_critico["ids"]["empresa_a"]),
        endpoint="feed",
        reason="promoted",
        source="surface_state_override",
        rollout_bucket=12,
        capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
    )
    summary = get_mobile_v2_rollout_operational_summary()
    feed_row = next(
        row
        for row in summary["tenant_surface_states"]
        if row["tenant_key"] == str(ambiente_critico["ids"]["empresa_a"])
        and row["surface"] == "feed"
    )

    assert feed_row["probe_requests_v2"] == 5
    assert feed_row["organic_requests_v2"] == 1
    assert feed_row["requests_v2_observed"] == 6


def test_probe_admin_route_dispara_execucao_local_controlada(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_demo_probe_rollout(ambiente_critico, monkeypatch)
    _prepare_demo_tenant_for_probe(ambiente_critico)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROBE", "1")
    client = ambiente_critico["client"]

    assert client.post("/admin/api/mobile-v2-rollout/probe/run").status_code == 401

    main.app.dependency_overrides[obter_usuario_html] = lambda: Usuario(
        id=ambiente_critico["ids"]["admin_a"],
        empresa_id=ambiente_critico["ids"]["empresa_a"],
        nivel_acesso=NivelAcesso.DIRETORIA.value,
        email="admin@empresa-a.test",
    )
    response = client.post("/admin/api/mobile-v2-rollout/probe/run")
    main.app.dependency_overrides.pop(obter_usuario_html, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["probe_requests_v2"] == 10
    assert payload["probe_requests_fallback"] == 0
