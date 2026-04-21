from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.domains.revisor.mesa_api import avaliar_laudo
from app.shared.database import (
    Laudo,
    MensagemLaudo,
    StatusRevisao,
    TemplateLaudo,
    TipoMensagem,
    Usuario,
)
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.contracts.provenance import ProvenanceEntry, build_content_origin_summary
from app.v2.document import (
    build_canonical_document_facade,
    build_document_hard_gate_decision,
    build_document_soft_gate_route_context,
    build_document_soft_gate_trace,
    clear_document_hard_gate_metrics_for_tests,
    get_document_hard_gate_operational_summary,
)
from tests.regras_rotas_criticas_support import (
    _criar_laudo,
    _salvar_pdf_temporario_teste,
)


def _build_pending_review_trace_with_template(ambiente_critico) -> object:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["revisor_a"])
        assert usuario is not None
        banco.add(
            TemplateLaudo(
                empresa_id=usuario.empresa_id,
                criado_por_id=usuario.id,
                nome="Template Padrao Review Approve",
                codigo_template="padrao",
                versao=1,
                ativo=True,
                base_recomendada_fixa=False,
                modo_editor="legado_pdf",
                status_template="ativo",
                arquivo_pdf_base=_salvar_pdf_temporario_teste("review_approve"),
                mapeamento_campos_json={},
                documento_editor_json=None,
                assets_json=[],
                estilo_json={},
                observacoes=None,
            )
        )
        banco.commit()

        provenance = build_content_origin_summary(
            entries=[
                ProvenanceEntry(
                    origin_kind="human",
                    source="review_package",
                    confidence="confirmed",
                    signal_count=3,
                )
            ]
        )
        snapshot = build_technical_case_status_snapshot_for_user(
            usuario=usuario,
            legacy_payload={
                "estado": "aguardando",
                "laudo_id": 91,
                "permite_reabrir": False,
                "laudo_card": {"id": 91, "status_revisao": StatusRevisao.AGUARDANDO.value},
            },
            content_origin_summary=provenance,
        )
        facade = build_canonical_document_facade(
            banco=banco,
            case_snapshot=snapshot,
            source_channel="review_api",
            template_key="padrao",
            provenance_summary=provenance,
            current_review_status=StatusRevisao.AGUARDANDO.value,
            has_form_data=True,
            has_ai_draft=True,
        )

    return build_document_soft_gate_trace(
        case_snapshot=snapshot,
        document_facade=facade,
        route_context=build_document_soft_gate_route_context(
            route_name="avaliar_laudo_review_approve",
            route_path="/revisao/api/laudo/91/avaliar",
            http_method="POST",
            source_channel="review_api",
            operation_kind="review_approve",
            side_effect_free=False,
            legacy_pipeline_name="legacy_review_approve",
        ),
    )


def _preparar_laudo_revisao_pendente(
    banco,
    *,
    empresa_id: int,
    usuario_id: int,
    tipo_template: str = "padrao",
) -> int:
    laudo_id = _criar_laudo(
        banco,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        status_revisao=StatusRevisao.AGUARDANDO.value,
        tipo_template=tipo_template,
    )
    laudo = banco.get(Laudo, laudo_id)
    assert laudo is not None
    laudo.primeira_mensagem = "Inspeção em revisão aguardando decisão da mesa."
    banco.add_all(
        [
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.USER.value,
                conteudo="Checklist técnico consolidado para avaliação.",
            ),
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.USER.value,
                conteudo="[imagem]",
            ),
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.IA.value,
                conteudo="Rascunho documental assistido disponível.",
            ),
        ]
    )
    banco.commit()
    return laudo_id


def _criar_template_ativo_revisao(
    banco,
    *,
    empresa_id: int,
    criado_por_id: int,
    codigo_template: str,
) -> None:
    banco.add(
        TemplateLaudo(
            empresa_id=empresa_id,
            criado_por_id=criado_por_id,
            nome=f"Template {codigo_template} review approve",
            codigo_template=codigo_template,
            versao=1,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="legado_pdf",
            status_template="ativo",
            arquivo_pdf_base=_salvar_pdf_temporario_teste(f"review_{codigo_template}"),
            mapeamento_campos_json={},
            documento_editor_json=None,
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
    )
    banco.commit()


def _build_review_request(laudo_id: int, csrf: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": f"/revisao/api/laudo/{laudo_id}/avaliar",
            "headers": [(b"x-csrf-token", csrf.encode())],
            "query_string": b"",
            "session": {"csrf_token_revisor": csrf},
            "state": {},
            "client": ("testclient", 50110),
        }
    )


def _aprovar_laudo_direct(
    *,
    laudo_id: int,
    csrf: str,
    usuario: Usuario,
    banco,
):
    return asyncio.run(
        avaliar_laudo(
            laudo_id=laudo_id,
            request=_build_review_request(laudo_id, csrf),
            acao="aprovar",
            motivo="",
            csrf_token="",
            usuario=usuario,
            banco=banco,
        )
    )


def _summary_blocker(payload: dict, blocker_code: str) -> dict:
    for item in payload["by_blocker_code"]:
        if item["blocker_code"] == blocker_code:
            return item
    raise AssertionError(f"Blocker {blocker_code} não encontrado no summary.")


def test_hard_gate_review_approve_mantem_blockers_sensiveis_apenas_em_shadow(
    ambiente_critico,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "review_approve")

    decision = build_document_hard_gate_decision(
        soft_gate_trace=_build_pending_review_trace_with_template(ambiente_critico),
        remote_host="testclient",
    )

    scopes = {item.blocker_code: item.enforcement_scope for item in decision.blockers}
    assert decision.operation_kind == "review_approve"
    assert decision.would_block is False
    assert decision.did_block is False
    assert scopes["issue_disallowed_by_policy"] == "shadow_only"
    assert scopes["review_requirement_not_satisfied"] == "shadow_only"
    assert scopes["engineer_approval_requirement_not_satisfied"] == "shadow_only"


def test_hard_gate_review_approve_shadow_only_nao_bloqueia_aprovacao(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()
    csrf = "csrf-review-approve-shadow"

    with SessionLocal() as banco:
        laudo_id = _preparar_laudo_revisao_pendente(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            tipo_template="avcb",
        )

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.delenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", raising=False)
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "review_approve")

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["revisor_a"])
        assert usuario is not None
        resposta = _aprovar_laudo_direct(
            laudo_id=laudo_id,
            csrf=csrf,
            usuario=usuario,
            banco=banco,
        )

    assert resposta.status_code == 200
    assert b'"success":true' in resposta.body

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.APROVADO.value

    summary = get_document_hard_gate_operational_summary()
    assert any(
        item["operation_kind"] == "review_approve" and item["evaluations"] >= 1
        for item in summary["by_operation_kind"]
    )
    assert summary["totals"]["would_block"] >= 1
    assert summary["totals"]["did_block"] == 0
    assert summary["totals"]["shadow_only"] >= 1


def test_hard_gate_review_approve_enforce_bloqueia_por_template_nao_vinculado(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()
    csrf = "csrf-review-approve-enforce-blocked"

    with SessionLocal() as banco:
        laudo_id = _preparar_laudo_revisao_pendente(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            tipo_template="avcb",
        )

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "review_approve")

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["revisor_a"])
        assert usuario is not None
        with pytest.raises(HTTPException) as exc_info:
            _aprovar_laudo_direct(
                laudo_id=laudo_id,
                csrf=csrf,
                usuario=usuario,
                banco=banco,
            )

    assert exc_info.value.status_code == 422
    detalhe = exc_info.value.detail
    assert detalhe["codigo"] == "DOCUMENT_HARD_GATE_BLOCKED"
    assert detalhe["operacao"] == "review_approve"
    blocker_codes = {item["blocker_code"] for item in detalhe["blockers"]}
    assert "template_not_bound" in blocker_codes or "template_source_unknown" in blocker_codes

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value

    summary = get_document_hard_gate_operational_summary()
    assert summary["totals"]["did_block"] >= 1
    assert any(
        item["operation_kind"] == "review_approve" and item["did_block"] >= 1
        for item in summary["by_operation_kind"]
    )


def test_hard_gate_review_approve_enforce_permita_quando_restam_apenas_shadow_blockers(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()
    csrf = "csrf-review-approve-enforce-allowed"

    with SessionLocal() as banco:
        _criar_template_ativo_revisao(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template="padrao",
        )
        laudo_id = _preparar_laudo_revisao_pendente(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            tipo_template="padrao",
        )

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "review_approve")

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["revisor_a"])
        assert usuario is not None
        resposta = _aprovar_laudo_direct(
            laudo_id=laudo_id,
            csrf=csrf,
            usuario=usuario,
            banco=banco,
        )

    assert resposta.status_code == 200
    assert b'"success":true' in resposta.body

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.APROVADO.value

    summary = get_document_hard_gate_operational_summary()
    assert summary["totals"]["did_block"] == 0
    assert _summary_blocker(summary, "issue_disallowed_by_policy")["shadow_only"] >= 1
    assert _summary_blocker(summary, "review_requirement_not_satisfied")["shadow_only"] >= 1
    assert _summary_blocker(summary, "engineer_approval_requirement_not_satisfied")["shadow_only"] >= 1


def test_hard_gate_review_approve_rollback_desligando_enforce_volta_a_permitir(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()
    csrf = "csrf-review-approve-rollback"

    with SessionLocal() as banco:
        laudo_bloqueado_id = _preparar_laudo_revisao_pendente(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            tipo_template="avcb",
        )
        laudo_rollback_id = _preparar_laudo_revisao_pendente(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            tipo_template="avcb",
        )

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "review_approve")

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["revisor_a"])
        assert usuario is not None
        with pytest.raises(HTTPException) as exc_info:
            _aprovar_laudo_direct(
                laudo_id=laudo_bloqueado_id,
                csrf=csrf,
                usuario=usuario,
                banco=banco,
            )
    assert exc_info.value.status_code == 422

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "0")

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["revisor_a"])
        assert usuario is not None
        resposta_rollback = _aprovar_laudo_direct(
            laudo_id=laudo_rollback_id,
            csrf=csrf,
            usuario=usuario,
            banco=banco,
        )

    assert resposta_rollback.status_code == 200
    assert b'"success":true' in resposta_rollback.body

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_rollback_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.APROVADO.value
