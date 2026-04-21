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
    get_mobile_v2_operator_validation_status,
    start_mobile_v2_operator_validation_run,
)
from app.v2.mobile_organic_validation import (
    clear_mobile_v2_organic_validation_session_for_tests,
    record_mobile_v2_organic_human_checkpoint,
)
from app.v2.mobile_rollout import MOBILE_V2_CAPABILITIES_VERSION
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    record_mobile_v2_legacy_fallback,
    record_mobile_v2_public_read,
)


def _configure_demo_operator_run(
    ambiente_critico,
    monkeypatch,
    *,
    with_targets: bool,
) -> str:
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
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_FALLBACK_RATE_PERCENT", "15")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_REQUIRE_FULL_WINDOW", "1")
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

        if with_targets:
            laudo_feed = Laudo(
                empresa_id=ambiente_critico["ids"]["empresa_a"],
                usuario_id=ambiente_critico["ids"]["inspetor_a"],
                setor_industrial="Operator Run Feed",
                tipo_template="padrao",
                status_revisao=StatusRevisao.AGUARDANDO.value,
                codigo_hash=uuid.uuid4().hex,
                primeira_mensagem="Operator run feed target",
            )
            laudo_thread = Laudo(
                empresa_id=ambiente_critico["ids"]["empresa_a"],
                usuario_id=ambiente_critico["ids"]["inspetor_a"],
                setor_industrial="Operator Run Thread",
                tipo_template="padrao",
                status_revisao=StatusRevisao.AGUARDANDO.value,
                codigo_hash=uuid.uuid4().hex,
                primeira_mensagem="Operator run thread target",
            )
            banco.add_all([laudo_feed, laudo_thread])
            banco.flush()
            banco.add(
                MensagemLaudo(
                    laudo_id=laudo_thread.id,
                    remetente_id=ambiente_critico["ids"]["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Mensagem segura para operator run.",
                    custo_api_reais=Decimal("0.0000"),
                )
            )
        banco.commit()
    return tenant_key


def _record_operator_surface_success(
    *,
    tenant_key: str,
    status,
    surface: str,
    fallback_reason: str | None = None,
) -> int:
    target = next(
        item for item in status.run.required_targets if item.surface == surface
    )
    for _ in range(3):
        record_mobile_v2_public_read(
            tenant_key=tenant_key,
            endpoint=surface,
            reason="promoted",
            source="surface_state_override",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
            traffic_class="organic_validation",
            validation_session_id=status.run.session_id,
            target_ids=[target.target_id],
        )
    if fallback_reason:
        record_mobile_v2_legacy_fallback(
            tenant_key=tenant_key,
            endpoint=surface,
            reason=fallback_reason,
            source="v2_read",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
            traffic_class="legacy_fallback_from_validation",
            validation_session_id=status.run.session_id,
            target_ids=[target.target_id],
        )
    record_mobile_v2_organic_human_checkpoint(
        tenant_key=tenant_key,
        session_id=status.run.session_id,
        surface=surface,
        target_id=target.target_id,
        checkpoint_kind="rendered",
        delivery_mode="v2",
        operator_run_id=status.run.operator_run_id,
    )
    return target.target_id


def test_operator_run_inicia_com_targets_e_sessao_organica(ambiente_critico, monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    clear_mobile_v2_operator_validation_run_for_tests()
    _configure_demo_operator_run(ambiente_critico, monkeypatch, with_targets=True)

    status = start_mobile_v2_operator_validation_run(remote_host="127.0.0.1")

    assert status.operator_run_active is True
    assert status.operator_run_outcome == "in_progress"
    assert status.operator_run_id and status.operator_run_id.startswith("oprv_")
    assert status.operator_run_session_id and status.operator_run_session_id.startswith("orgv_")
    assert status.required_surfaces == ("feed", "thread")
    assert len(status.operator_run_instructions) == 2
    assert status.validation_session_source == "operator_run"


def test_operator_run_bloqueia_sem_targets_elegiveis(ambiente_critico, monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    clear_mobile_v2_operator_validation_run_for_tests()
    _configure_demo_operator_run(ambiente_critico, monkeypatch, with_targets=False)

    status = start_mobile_v2_operator_validation_run(remote_host="127.0.0.1")

    assert status.operator_run_active is False
    assert status.operator_run_outcome == "blocked_no_targets"
    assert status.operator_run_reason == "eligible_targets_missing_for_feed_thread"
    assert status.operator_run_session_id is None


def test_operator_run_acompanha_progresso_e_conclui_com_sucesso(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    clear_mobile_v2_operator_validation_run_for_tests()
    tenant_key = _configure_demo_operator_run(
        ambiente_critico,
        monkeypatch,
        with_targets=True,
    )

    started = start_mobile_v2_operator_validation_run(remote_host="127.0.0.1")
    assert started.run is not None

    feed_target = _record_operator_surface_success(
        tenant_key=tenant_key,
        status=started,
        surface="feed",
    )
    thread_target = _record_operator_surface_success(
        tenant_key=tenant_key,
        status=started,
        surface="thread",
    )

    in_progress = get_mobile_v2_operator_validation_status()
    assert in_progress.progress is not None
    assert in_progress.progress.feed_completed is True
    assert in_progress.progress.thread_completed is True
    assert in_progress.progress.human_confirmed_minimum_met is True
    assert feed_target in in_progress.progress.human_confirmed_targets["feed"]
    assert thread_target in in_progress.progress.human_confirmed_targets["thread"]

    finished = finish_mobile_v2_operator_validation_run(remote_host="127.0.0.1")

    assert finished.operator_run_active is False
    assert finished.operator_run_outcome == "completed_successfully"
    assert finished.operator_run_reason == "required_surfaces_completed"
    assert finished.covered_surfaces == ("feed", "thread")
    assert finished.human_coverage_from_operator_run is True


def test_operator_run_conclui_com_sucesso_com_alvos_confirmados_mesmo_sem_coverage_met(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    clear_mobile_v2_operator_validation_run_for_tests()
    tenant_key = _configure_demo_operator_run(
        ambiente_critico,
        monkeypatch,
        with_targets=True,
    )

    started = start_mobile_v2_operator_validation_run(remote_host="127.0.0.1")
    assert started.run is not None

    for surface in ("feed", "thread"):
        target = next(
            item for item in started.run.required_targets if item.surface == surface
        )
        record_mobile_v2_public_read(
            tenant_key=tenant_key,
            endpoint=surface,
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
            surface=surface,
            target_id=target.target_id,
            checkpoint_kind="rendered",
            delivery_mode="v2",
            operator_run_id=started.run.operator_run_id,
        )

    in_progress = get_mobile_v2_operator_validation_status()
    assert in_progress.progress is not None
    assert in_progress.progress.feed_completed is True
    assert in_progress.progress.thread_completed is True
    assert in_progress.progress.human_confirmed_minimum_met is True

    finished = finish_mobile_v2_operator_validation_run(remote_host="127.0.0.1")

    assert finished.operator_run_outcome == "completed_successfully"
    assert finished.operator_run_reason == "required_surfaces_completed"
    assert finished.covered_surfaces == ("feed", "thread")


def test_operator_run_conclui_inconclusivo_sem_cobertura_humana(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    clear_mobile_v2_operator_validation_run_for_tests()
    _configure_demo_operator_run(ambiente_critico, monkeypatch, with_targets=True)

    start_mobile_v2_operator_validation_run(remote_host="127.0.0.1")
    finished = finish_mobile_v2_operator_validation_run(remote_host="127.0.0.1")

    assert finished.operator_run_active is False
    assert finished.operator_run_outcome == "completed_inconclusive"
    assert finished.operator_run_reason == "minimum_human_coverage_not_met"
    assert finished.human_coverage_from_operator_run is False


def test_operator_run_prefere_targets_acessiveis_ao_inspetor_demo(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    clear_mobile_v2_operator_validation_run_for_tests()
    _configure_demo_operator_run(
        ambiente_critico,
        monkeypatch,
        with_targets=True,
    )

    SessionLocal = ambiente_critico["SessionLocal"]
    with SessionLocal() as banco:
        laudo_estrangeiro = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["revisor_a"],
            setor_industrial="Laudo recente de outro operador",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Nao deve virar target do operator run mobile.",
        )
        banco.add(laudo_estrangeiro)
        banco.flush()
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_estrangeiro.id,
                remetente_id=ambiente_critico["ids"]["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mensagem de outro usuario do tenant.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()

    status = start_mobile_v2_operator_validation_run(remote_host="127.0.0.1")

    assert status.run is not None
    selected_target_ids = [item.target_id for item in status.run.required_targets]
    assert selected_target_ids

    with SessionLocal() as banco:
        selected_user_ids = banco.scalars(
            select(Laudo.usuario_id).where(Laudo.id.in_(selected_target_ids))
        ).all()

    assert selected_user_ids
    assert set(selected_user_ids) == {ambiente_critico["ids"]["inspetor_a"]}
