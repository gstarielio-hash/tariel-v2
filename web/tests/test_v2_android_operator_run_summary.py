from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select

from app.shared.database import (
    Empresa,
    Laudo,
    MensagemLaudo,
    StatusRevisao,
    TipoMensagem,
)
from app.v2.mobile_operator_run import (
    clear_mobile_v2_operator_validation_run_for_tests,
    finish_mobile_v2_operator_validation_run,
    start_mobile_v2_operator_validation_run,
)
from app.v2.mobile_organic_validation import (
    clear_mobile_v2_organic_validation_session_for_tests,
    record_mobile_v2_organic_human_checkpoint,
)
from app.v2.mobile_rollout import MOBILE_V2_CAPABILITIES_VERSION
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    get_mobile_v2_rollout_operational_summary,
    record_mobile_v2_public_read,
)


def _configure_demo_summary_run(ambiente_critico, monkeypatch) -> str:
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
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_WINDOW_MINUTES", "30")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MIN_REQUESTS_PER_SURFACE", "3")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_TARGET_LIMIT", "100")
    monkeypatch.setenv("TARIEL_V2_ANDROID_OPERATOR_RUN_REQUIRED_TARGETS_PER_SURFACE", "1")

    SessionLocal = ambiente_critico["SessionLocal"]
    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ambiente_critico["ids"]["empresa_a"])
        assert empresa is not None
        empresa.nome_fantasia = "Empresa Demo (DEV)"
        empresa.cnpj = "00000000000000"

        laudo_ids = banco.scalars(
            select(Laudo.id).where(Laudo.empresa_id == ambiente_critico["ids"]["empresa_a"])
        ).all()
        if laudo_ids:
            banco.execute(delete(MensagemLaudo).where(MensagemLaudo.laudo_id.in_(laudo_ids)))
            banco.execute(delete(Laudo).where(Laudo.id.in_(laudo_ids)))
            banco.flush()

        laudo_feed = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["inspetor_a"],
            setor_industrial="Operator Summary Feed",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Operator summary feed target",
        )
        laudo_thread = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["inspetor_a"],
            setor_industrial="Operator Summary Thread",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Operator summary thread target",
        )
        banco.add_all([laudo_feed, laudo_thread])
        banco.flush()
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_thread.id,
                remetente_id=ambiente_critico["ids"]["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mensagem segura para summary do operator run.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()
    return tenant_key


def test_summary_rollout_expoe_operator_run_sem_conteudo_sensivel(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    clear_mobile_v2_operator_validation_run_for_tests()
    tenant_key = _configure_demo_summary_run(ambiente_critico, monkeypatch)

    started = start_mobile_v2_operator_validation_run(remote_host="127.0.0.1")
    assert started.run is not None
    for target in started.run.required_targets:
        for _ in range(3):
            record_mobile_v2_public_read(
                tenant_key=tenant_key,
                endpoint=target.surface,
                reason="promoted",
                source="surface_state_override",
                rollout_bucket=12,
                capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
                traffic_class="organic_validation",
                validation_session_id=started.run.session_id,
                target_ids=[target.target_id],
            )
        record_mobile_v2_organic_human_checkpoint(
            tenant_key=tenant_key,
            session_id=started.run.session_id,
            surface=target.surface,
            target_id=target.target_id,
            checkpoint_kind="rendered",
            delivery_mode="v2",
            operator_run_id=started.run.operator_run_id,
        )

    finish_mobile_v2_operator_validation_run(remote_host="127.0.0.1")
    payload = get_mobile_v2_rollout_operational_summary()

    assert payload["operator_run_active"] is False
    assert payload["operator_run_outcome"] == "completed_successfully"
    assert payload["validation_session_source"] == "operator_run"
    assert payload["human_coverage_from_operator_run"] is True
    assert payload["required_surfaces"] == ["feed", "thread"]
    assert payload["covered_surfaces"] == ["feed", "thread"]

    tenant_row = next(
        item
        for item in payload["tenant_rollout_states"]
        if item["tenant_key"] == tenant_key
    )
    assert tenant_row["operator_run_outcome"] == "completed_successfully"
    assert tenant_row["human_coverage_from_operator_run"] is True

    feed_surface_row = next(
        item
        for item in payload["tenant_surface_states"]
        if item["tenant_key"] == tenant_key and item["surface"] == "feed"
    )
    assert feed_surface_row["operator_run_surface_completed"] is True
    assert isinstance(feed_surface_row["operator_run_missing_targets"], list)

    serialized = str(payload).lower()
    assert "mensagem segura para summary do operator run" not in serialized
    assert "conteudo" not in serialized
