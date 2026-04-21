from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from starlette.requests import Request

from app.domains.chat.laudo_service import obter_status_relatorio_resposta
from app.shared.database import Laudo, NivelAcesso, StatusRevisao, Usuario
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.contracts.inspector_document import build_inspector_document_view_projection
from app.v2.document import build_canonical_document_facade


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


def test_shape_da_projecao_documental_do_inspetor() -> None:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aguardando",
            "laudo_id": 88,
            "permite_reabrir": False,
            "laudo_card": {"id": 88, "status_revisao": StatusRevisao.AGUARDANDO.value},
        },
    )
    facade = build_canonical_document_facade(
        banco=None,
        case_snapshot=snapshot,
        source_channel="web_app",
        template_key="padrao",
        current_review_status=StatusRevisao.AGUARDANDO.value,
        has_form_data=True,
        has_ai_draft=True,
    )

    projection = build_inspector_document_view_projection(
        case_snapshot=snapshot,
        document_facade=facade,
        actor_id=17,
        actor_role="inspetor",
        source_channel="web_app",
    )

    dumped = projection.model_dump(mode="json")
    assert dumped["contract_name"] == "InspectorDocumentViewProjectionV1"
    assert dumped["projection_audience"] == "inspetor_document_web"
    assert dumped["document_id"] == "document:legacy-laudo:33:88"
    assert dumped["payload"]["legacy_laudo_id"] == 88
    assert dumped["payload"]["document_status_summary"]["current_case_status"] == "needs_reviewer"
    assert dumped["payload"]["document_status_summary"]["current_document_status"] == "partially_filled"
    assert dumped["payload"]["document_status_summary"]["readiness_state"] == "blocked"
    assert dumped["payload"]["document_status_summary"]["materialization_allowed"] is True
    assert dumped["payload"]["document_status_summary"]["issue_allowed"] is False
    assert dumped["payload"]["template_summary"]["template_key"] == "padrao"
    assert dumped["payload"]["policy_summary"]["review_required"] is True
    assert dumped["payload"]["blockers"]


def test_status_relatorio_registra_projecao_documental_sem_mudar_payload_publico(
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
            dados_formulario={"campo": "valor"},
            parecer_ia="Rascunho IA",
        )
        banco.add(laudo)
        banco.flush()

        sessao = {"laudo_ativo_id": laudo.id, "estado_relatorio": "aguardando"}

        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_POLICY_ENGINE", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_FACADE", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_SHADOW", raising=False)
        payload_base, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=_build_request(dict(sessao)),
                usuario=usuario,
                banco=banco,
            )
        )

        request_document = _build_request(dict(sessao))
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        monkeypatch.setenv("TARIEL_V2_POLICY_ENGINE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_FACADE", "1")
        payload_document, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=request_document,
                usuario=usuario,
                banco=banco,
            )
        )

    assert payload_document == payload_base
    resultado = request_document.state.v2_inspector_document_projection_result
    assert resultado["projection"]["contract_name"] == "InspectorDocumentViewProjectionV1"
    assert resultado["projection"]["payload"]["document_status_summary"]["current_document_status"] == "partially_filled"
    assert resultado["projection"]["payload"]["document_status_summary"]["readiness_state"] == "blocked"
    assert resultado["projection"]["payload"]["template_summary"]["template_key"] == "padrao"
    assert resultado["projection"]["payload"]["policy_summary"]["review_required"] is True
    assert resultado["document_facade"]["contract_name"] == "CanonicalDocumentFacadeV1"
