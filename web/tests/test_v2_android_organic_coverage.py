from __future__ import annotations

import uuid
from decimal import Decimal

from app.shared.database import (
    Empresa,
    Laudo,
    MensagemLaudo,
    StatusRevisao,
    TipoMensagem,
)
from app.v2.mobile_organic_validation import (
    get_mobile_v2_organic_validation_summary,
    resolve_demo_mobile_organic_validation_targets,
    start_mobile_v2_organic_validation_session,
)
from app.v2.mobile_rollout import MOBILE_V2_CAPABILITIES_VERSION
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    get_mobile_v2_rollout_operational_summary,
    record_mobile_v2_legacy_fallback,
    record_mobile_v2_public_read,
)


def _configure_demo_coverage(ambiente_critico, monkeypatch) -> str:
    tenant_key = str(ambiente_critico["ids"]["empresa_a"])
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
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_TARGET_LIMIT", "100")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MIN_REQUESTS_PER_SURFACE", "3")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_REQUIRE_FULL_WINDOW", "1")

    SessionLocal = ambiente_critico["SessionLocal"]
    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ambiente_critico["ids"]["empresa_a"])
        assert empresa is not None
        empresa.nome_fantasia = "Empresa Demo (DEV)"
        empresa.cnpj = "00000000000000"
        laudo_feed = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["inspetor_a"],
            setor_industrial="Organic Coverage Feed",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Organic coverage feed target",
        )
        laudo_thread = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["inspetor_a"],
            setor_industrial="Organic Coverage Thread",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Organic coverage thread target",
        )
        banco.add_all([laudo_feed, laudo_thread])
        banco.flush()
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_thread.id,
                remetente_id=ambiente_critico["ids"]["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mensagem segura para cobertura organica.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()
    return tenant_key


def _record_validation_usage(
    *,
    tenant_key: str,
    surface: str,
    session_id: str,
    target_ids: list[int],
    v2_served: int,
    fallback_reasons: tuple[str, ...] = (),
) -> None:
    for _ in range(v2_served):
        record_mobile_v2_public_read(
            tenant_key=tenant_key,
            endpoint=surface,
            reason="promoted",
            source="surface_state_override",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
            traffic_class="organic_validation",
            validation_session_id=session_id,
            target_ids=target_ids,
        )
    for reason in fallback_reasons:
        record_mobile_v2_legacy_fallback(
            tenant_key=tenant_key,
            endpoint=surface,
            reason=reason,
            source="v2_read",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
            traffic_class="legacy_fallback_from_validation",
            validation_session_id=session_id,
            target_ids=target_ids,
        )


def _record_probe_usage(
    *,
    tenant_key: str,
    surface: str,
    target_ids: list[int],
    v2_served: int,
) -> None:
    for _ in range(v2_served):
        record_mobile_v2_public_read(
            tenant_key=tenant_key,
            endpoint=surface,
            reason="promoted",
            source="surface_state_override",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
            probe_label="pilot_probe",
            probe_source="demo_controlled",
            target_ids=target_ids,
        )


def test_validacao_organica_permanece_insufficient_evidence_quando_so_probe_tem_cobertura(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    tenant_key = _configure_demo_coverage(ambiente_critico, monkeypatch)
    start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    targets = resolve_demo_mobile_organic_validation_targets(tenant_key=tenant_key)

    _record_probe_usage(
        tenant_key=tenant_key,
        surface="feed",
        target_ids=list(targets.get("feed", ())[:1]),
        v2_served=3,
    )
    _record_probe_usage(
        tenant_key=tenant_key,
        surface="thread",
        target_ids=list(targets.get("thread", ())[:1]),
        v2_served=3,
    )

    summary = get_mobile_v2_organic_validation_summary()

    assert summary.outcome == "insufficient_evidence"
    assert summary.surface_coverage_summary["covered_surfaces"] == []
    assert summary.probe_vs_organic_evidence["evidence_source"] == "probe_only"
    assert summary.distinct_targets["total"] == 0


def test_validacao_organica_sai_de_insufficient_evidence_com_cobertura_real_de_feed_e_thread(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    tenant_key = _configure_demo_coverage(ambiente_critico, monkeypatch)
    started = start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    session = started.session
    assert session is not None
    targets = resolve_demo_mobile_organic_validation_targets(tenant_key=tenant_key)

    _record_validation_usage(
        tenant_key=tenant_key,
        surface="feed",
        session_id=session.session_id,
        target_ids=list(targets.get("feed", ())[:1]),
        v2_served=3,
    )
    _record_validation_usage(
        tenant_key=tenant_key,
        surface="thread",
        session_id=session.session_id,
        target_ids=list(targets.get("thread", ())[:1]),
        v2_served=3,
    )

    summary = get_mobile_v2_organic_validation_summary()
    operational_summary = get_mobile_v2_rollout_operational_summary()
    feed_row = next(
        row
        for row in operational_summary["tenant_surface_states"]
        if row["tenant_key"] == tenant_key and row["surface"] == "feed"
    )
    thread_row = next(
        row
        for row in operational_summary["tenant_surface_states"]
        if row["tenant_key"] == tenant_key and row["surface"] == "thread"
    )

    assert summary.outcome == "healthy"
    assert summary.surface_coverage_summary["both_surfaces_covered"] is True
    assert summary.distinct_targets["feed"] >= 1
    assert summary.distinct_targets["thread"] >= 1
    assert operational_summary["organic_validation_outcome"] == "healthy"
    assert feed_row["organic_validation_coverage_met"] is True
    assert thread_row["organic_validation_coverage_met"] is True
    assert feed_row["organic_validation_outcome"] == "healthy"
    assert thread_row["organic_validation_outcome"] == "healthy"
