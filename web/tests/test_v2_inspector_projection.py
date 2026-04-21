from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from starlette.requests import Request

from app.domains.chat.laudo_service import obter_status_relatorio_resposta
from app.shared.database import Laudo, NivelAcesso, StatusRevisao, Usuario
from app.v2.acl.technical_case_core import (
    build_technical_case_status_snapshot_for_user,
    is_mobile_review_command_allowed,
    resolve_allowed_mobile_review_decisions,
    resolve_supports_mobile_block_reopen,
)
from app.v2.adapters.inspector_status import adapt_inspector_case_view_projection_to_legacy_status
from app.v2.contracts.projections import build_inspector_case_view_projection


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def _build_request(session_data: dict[str, object] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/app/api/laudo/status",
            "headers": [],
            "query_string": b"",
            "session": session_data or {},
            "state": {},
        }
    )


def test_shape_da_projecao_canonica_do_inspetor() -> None:
    legacy_payload = {
        "estado": "aguardando",
        "laudo_id": 88,
        "permite_edicao": False,
        "permite_reabrir": False,
        "tem_interacao": True,
        "tipos_relatorio": ["padrao", "cbmgo"],
        "laudo_card": {
            "id": 88,
            "status_revisao": StatusRevisao.AGUARDANDO.value,
            "status_card": "aguardando",
        },
    }
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload=legacy_payload,
    )

    projection = build_inspector_case_view_projection(
        case_snapshot=snapshot,
        actor_id=17,
        actor_role="inspetor",
        source_channel="web_app",
        allows_edit=False,
        has_interaction=True,
        report_types={"padrao": "Inspeção Geral (Padrão)", "cbmgo": "CBM-GO Vistoria Bombeiro"},
        laudo_card=legacy_payload["laudo_card"],
    )

    dumped = projection.model_dump(mode="json")
    assert dumped["contract_name"] == "InspectorCaseViewProjectionV1"
    assert dumped["case_id"] == "case:legacy-laudo:33:88"
    assert dumped["thread_id"] == "thread:legacy-laudo:33:88"
    assert dumped["document_id"] == "document:legacy-laudo:33:88"
    assert dumped["projection_audience"] == "inspetor"
    assert dumped["payload"]["legacy_laudo_id"] == 88
    assert dumped["payload"]["case_status"] == "needs_reviewer"
    assert dumped["payload"]["case_lifecycle_status"] == "aguardando_mesa"
    assert dumped["payload"]["case_workflow_mode"] == "laudo_com_mesa"
    assert dumped["payload"]["active_owner_role"] == "mesa"
    assert dumped["payload"]["allowed_next_lifecycle_statuses"] == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert dumped["payload"]["allowed_surface_actions"] == [
        "mesa_approve",
        "mesa_return",
    ]
    assert [
        item["target_status"]
        for item in dumped["payload"]["allowed_lifecycle_transitions"]
    ] == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert dumped["payload"]["human_validation_required"] is True
    assert dumped["payload"]["legacy_public_state"] == "aguardando"
    assert dumped["payload"]["legacy_review_status"] == StatusRevisao.AGUARDANDO.value
    assert dumped["payload"]["review_requested"] is True
    assert dumped["payload"]["review_visible_to_inspector"] is True
    assert dumped["payload"]["document_available"] is True
    assert dumped["payload"]["report_types"] == {
        "padrao": "Inspeção Geral (Padrão)",
        "cbmgo": "CBM-GO Vistoria Bombeiro",
    }


def test_adapter_da_projecao_reconstroi_payload_legado() -> None:
    legacy_payload = {
        "estado": "relatorio_ativo",
        "laudo_id": 41,
        "status_card": "aberto",
        "permite_edicao": True,
        "permite_reabrir": False,
        "tem_interacao": False,
        "case_lifecycle_status": "pre_laudo",
        "case_workflow_mode": "analise_livre",
        "active_owner_role": "inspetor",
        "allowed_next_lifecycle_statuses": ["analise_livre", "laudo_em_coleta"],
        "allowed_lifecycle_transitions": [
            {
                "target_status": "analise_livre",
                "transition_kind": "analysis",
                "label": "Voltar para analise livre",
                "owner_role": "inspetor",
                "preferred_surface": "chat",
            },
            {
                "target_status": "laudo_em_coleta",
                "transition_kind": "advance",
                "label": "Entrar em laudo guiado",
                "owner_role": "inspetor",
                "preferred_surface": "chat",
            },
        ],
        "allowed_surface_actions": [],
        "tipos_relatorio": {"padrao": "Inspeção Geral (Padrão)"},
        "public_verification": {
            "verification_url": "/app/public/laudo/verificar/abc123ef",
            "hash_short": "abc123ef",
        },
        "emissao_oficial": {
            "issue_status": "ready_for_issue",
            "issue_status_label": "Pronto para emissão oficial",
        },
        "laudo_card": {"id": 41, "status_revisao": StatusRevisao.RASCUNHO.value},
    }
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload=legacy_payload,
    )
    projection = build_inspector_case_view_projection(
        case_snapshot=snapshot,
        actor_id=17,
        actor_role="inspetor",
        source_channel="web_app",
        allows_edit=True,
        has_interaction=False,
        report_types={"padrao": "Inspeção Geral (Padrão)"},
        laudo_card=legacy_payload["laudo_card"],
        public_verification=legacy_payload["public_verification"],
        emissao_oficial=legacy_payload["emissao_oficial"],
    )

    adapted = adapt_inspector_case_view_projection_to_legacy_status(
        projection=projection,
        expected_legacy_payload=legacy_payload,
    )

    assert adapted.compatible is True
    assert adapted.divergences == []
    assert adapted.payload == legacy_payload


def test_case_core_expande_lifecycle_canonico_sem_quebrar_case_status() -> None:
    laudo_guiado = SimpleNamespace(
        id=205,
        status_revisao=StatusRevisao.RASCUNHO.value,
        revisado_por=None,
        entry_mode_effective="evidence_first",
        dados_formulario={"equipamento": "V-205"},
        guided_inspection_draft_json={"checklist": [{"id": "identificacao"}]},
        report_pack_draft_json=None,
        parecer_ia="",
        nome_arquivo_pdf=None,
    )
    snapshot_guiado = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 205,
            "permite_reabrir": False,
        },
        laudo=laudo_guiado,
    )

    assert snapshot_guiado.canonical_status == "collecting_evidence"
    assert snapshot_guiado.case_lifecycle_status == "laudo_em_coleta"
    assert snapshot_guiado.workflow_mode == "laudo_guiado"
    assert snapshot_guiado.active_owner_role == "inspetor"
    assert snapshot_guiado.allowed_next_lifecycle_statuses == [
        "aguardando_mesa",
        "aprovado",
    ]
    assert snapshot_guiado.human_validation_required is True

    laudo_em_revisao = SimpleNamespace(
        id=301,
        status_revisao=StatusRevisao.AGUARDANDO.value,
        revisado_por=51,
        entry_mode_effective="chat_first",
        dados_formulario={"campo": "valor"},
        guided_inspection_draft_json=None,
        report_pack_draft_json={"quality_gates": {"missing_evidence": []}},
        parecer_ia="Rascunho para revisao",
        nome_arquivo_pdf=None,
    )
    snapshot_em_revisao = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aguardando",
            "laudo_id": 301,
            "permite_reabrir": False,
        },
        laudo=laudo_em_revisao,
    )

    assert snapshot_em_revisao.case_lifecycle_status == "em_revisao_mesa"
    assert snapshot_em_revisao.workflow_mode == "laudo_com_mesa"
    assert snapshot_em_revisao.active_owner_role == "mesa"
    assert snapshot_em_revisao.allowed_next_lifecycle_statuses == [
        "devolvido_para_correcao",
        "aprovado",
    ]

    laudo_aprovado_autonomo = SimpleNamespace(
        id=403,
        status_revisao=StatusRevisao.APROVADO.value,
        revisado_por=None,
        entry_mode_effective="evidence_first",
        dados_formulario={"campo": "valor"},
        guided_inspection_draft_json={"checklist": [{"id": "identificacao"}]},
        report_pack_draft_json={
            "quality_gates": {"final_validation_mode": "mobile_autonomous"}
        },
        parecer_ia="Rascunho aprovado no mobile",
        nome_arquivo_pdf=None,
    )
    snapshot_aprovado_autonomo = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aprovado",
            "laudo_id": 403,
            "permite_reabrir": False,
        },
        laudo=laudo_aprovado_autonomo,
    )

    assert snapshot_aprovado_autonomo.case_lifecycle_status == "aprovado"
    assert snapshot_aprovado_autonomo.workflow_mode == "laudo_guiado"
    assert snapshot_aprovado_autonomo.active_owner_role == "none"
    assert snapshot_aprovado_autonomo.allowed_next_lifecycle_statuses == [
        "emitido",
        "devolvido_para_correcao",
    ]

    laudo_emitido = SimpleNamespace(
        id=404,
        status_revisao=StatusRevisao.APROVADO.value,
        revisado_por=51,
        entry_mode_effective="chat_first",
        dados_formulario={"campo": "valor"},
        guided_inspection_draft_json=None,
        report_pack_draft_json=None,
        parecer_ia="Rascunho aprovado",
        nome_arquivo_pdf="laudo-final.pdf",
    )
    snapshot_emitido = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aprovado",
            "laudo_id": 404,
            "permite_reabrir": False,
        },
        laudo=laudo_emitido,
    )

    assert snapshot_emitido.case_lifecycle_status == "emitido"
    assert snapshot_emitido.workflow_mode == "laudo_com_mesa"
    assert snapshot_emitido.active_owner_role == "none"
    assert snapshot_emitido.allowed_next_lifecycle_statuses == [
        "devolvido_para_correcao",
    ]

    laudo_reemitido_em_reabertura = SimpleNamespace(
        id=405,
        status_revisao=StatusRevisao.RASCUNHO.value,
        revisado_por=51,
        reaberto_em="2026-04-12T12:30:00+00:00",
        entry_mode_effective="chat_first",
        dados_formulario={"campo": "valor atualizado"},
        guided_inspection_draft_json=None,
        report_pack_draft_json=None,
        parecer_ia="Documento anterior reaberto",
        nome_arquivo_pdf="laudo-final-v1.pdf",
    )
    snapshot_reaberto = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 405,
            "permite_reabrir": False,
        },
        laudo=laudo_reemitido_em_reabertura,
    )

    assert snapshot_reaberto.case_lifecycle_status == "devolvido_para_correcao"
    assert snapshot_reaberto.active_owner_role == "inspetor"
    assert snapshot_reaberto.allowed_next_lifecycle_statuses == [
        "laudo_em_coleta",
        "aguardando_mesa",
    ]


def test_case_core_centraliza_decisoes_de_revisao_mobile_por_lifecycle() -> None:
    assert resolve_allowed_mobile_review_decisions(
        lifecycle_status="pre_laudo",
        allows_edit=True,
        review_mode="mobile_review_allowed",
    ) == [
        "aprovar_no_mobile",
        "enviar_para_mesa",
        "devolver_no_mobile",
    ]
    assert resolve_allowed_mobile_review_decisions(
        lifecycle_status="laudo_em_coleta",
        allows_edit=True,
        review_mode="mesa_required",
    ) == [
        "enviar_para_mesa",
        "devolver_no_mobile",
    ]
    assert resolve_allowed_mobile_review_decisions(
        lifecycle_status="aguardando_mesa",
        allows_edit=False,
        review_mode="mesa_required",
    ) == []
    assert resolve_supports_mobile_block_reopen(
        lifecycle_status="laudo_em_coleta",
        allows_edit=True,
        has_block_review_items=True,
    ) is True
    assert is_mobile_review_command_allowed(
        lifecycle_status="pre_laudo",
        allows_edit=True,
        review_mode="mobile_autonomous",
        command="aprovar_no_mobile",
    ) is True
    assert is_mobile_review_command_allowed(
        lifecycle_status="aguardando_mesa",
        allows_edit=False,
        review_mode="mesa_required",
        command="devolver_no_mobile",
    ) is False


def test_status_relatorio_passa_pela_projecao_quando_flag_ativa(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.flush()

        sessao = {"laudo_ativo_id": laudo.id, "estado_relatorio": "relatorio_ativo"}

        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_ENVELOPES", raising=False)
        monkeypatch.delenv("TARIEL_V2_INSPECTOR_PROJECTION", raising=False)
        payload_base, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=_build_request(dict(sessao)),
                usuario=usuario,
                banco=banco,
            )
        )

        request_projection = _build_request(dict(sessao))
        monkeypatch.setenv("TARIEL_V2_INSPECTOR_PROJECTION", "1")
        payload_projection, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=request_projection,
                usuario=usuario,
                banco=banco,
            )
        )

    assert payload_projection == payload_base
    assert "public_verification" in payload_projection
    assert request_projection.state.v2_inspector_projection_result["compatible"] is True
    assert request_projection.state.v2_inspector_projection_result["used_projection"] is True
    assert (
        request_projection.state.v2_inspector_projection_result["projection"]["contract_name"]
        == "InspectorCaseViewProjectionV1"
    )


def test_status_relatorio_com_projection_acl_e_envelopes_preserva_payload(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.flush()

        sessao = {"laudo_ativo_id": laudo.id, "estado_relatorio": "aguardando"}

        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_ENVELOPES", raising=False)
        monkeypatch.delenv("TARIEL_V2_INSPECTOR_PROJECTION", raising=False)
        payload_base, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=_build_request(dict(sessao)),
                usuario=usuario,
                banco=banco,
            )
        )

        request_flags = _build_request(dict(sessao))
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        monkeypatch.setenv("TARIEL_V2_ENVELOPES", "1")
        monkeypatch.setenv("TARIEL_V2_INSPECTOR_PROJECTION", "1")
        payload_flags, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=request_flags,
                usuario=usuario,
                banco=banco,
            )
        )

    assert payload_flags == payload_base
    assert "public_verification" in payload_flags
    assert request_flags.state.v2_inspector_projection_result["compatible"] is True
    assert request_flags.state.v2_shadow_projection_result["compatible"] is True
    assert request_flags.state.v2_case_core_snapshot["canonical_status"] == "needs_reviewer"
    assert request_flags.state.v2_technical_case_snapshot["case_state"] == "needs_reviewer"
    assert request_flags.state.v2_technical_case_snapshot["current_review_state"] == "pending_review"
