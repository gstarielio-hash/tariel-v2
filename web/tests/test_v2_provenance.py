from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from starlette.requests import Request

from app.domains.chat.laudo_service import obter_status_relatorio_resposta
from app.domains.mesa.contracts import (
    MensagemPacoteMesa,
    PacoteMesaLaudo,
    ResumoEvidenciasMesa,
    ResumoMensagensMesa,
    ResumoPendenciasMesa,
    RevisaoPacoteMesa,
)
from app.domains.revisor.mesa_api import obter_pacote_mesa_laudo
from app.shared.database import (
    Laudo,
    MensagemLaudo,
    NivelAcesso,
    StatusLaudo,
    StatusRevisao,
    TipoMensagem,
    Usuario,
)
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.contracts.projections import (
    build_inspector_case_view_projection,
    build_reviewdesk_case_view_projection,
)
from app.v2.provenance import (
    MessageOriginCounters,
    build_inspector_content_origin_summary,
    build_reviewdesk_content_origin_summary,
)


def _build_inspector_request(session_data: dict[str, object] | None = None) -> Request:
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


def _build_review_request(query_string: str = "") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/revisao/api/laudo/88/pacote",
            "headers": [],
            "query_string": query_string.encode(),
            "state": {},
        }
    )


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def _build_review_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=51,
        empresa_id=33,
        nivel_acesso=NivelAcesso.REVISOR.value,
    )


def _build_review_package() -> PacoteMesaLaudo:
    agora = datetime.now(timezone.utc)
    return PacoteMesaLaudo(
        laudo_id=88,
        codigo_hash="abc123ef",
        tipo_template="padrao",
        setor_industrial="NR Teste",
        status_revisao=StatusRevisao.AGUARDANDO.value,
        status_conformidade=StatusLaudo.PENDENTE.value,
        criado_em=agora,
        atualizado_em=agora,
        tempo_em_campo_minutos=42,
        ultima_interacao_em=agora,
        inspetor_id=17,
        revisor_id=51,
        dados_formulario={"campo": "valor"},
        parecer_ia="Rascunho de apoio",
        resumo_mensagens=ResumoMensagensMesa(total=10, inspetor=4, ia=3, mesa=2, sistema_outros=1),
        resumo_evidencias=ResumoEvidenciasMesa(total=3, textuais=1, fotos=1, documentos=1),
        resumo_pendencias=ResumoPendenciasMesa(total=2, abertas=1, resolvidas=1),
        pendencias_abertas=[
            MensagemPacoteMesa(
                id=1,
                tipo="humano_eng",
                texto="Ajustar evidência",
                criado_em=agora,
                remetente_id=51,
                lida=False,
            )
        ],
        pendencias_resolvidas_recentes=[
            MensagemPacoteMesa(
                id=2,
                tipo="humano_eng",
                texto="Ajuste resolvido",
                criado_em=agora,
                remetente_id=51,
                lida=True,
            )
        ],
        whispers_recentes=[
            MensagemPacoteMesa(
                id=3,
                tipo="humano_insp",
                texto="Campo respondeu",
                criado_em=agora,
                remetente_id=17,
                lida=False,
                referencia_mensagem_id=1,
            )
        ],
        revisoes_recentes=[
            RevisaoPacoteMesa(
                numero_versao=1,
                origem="ia",
                resumo="Primeira revisão",
                confianca_geral="alta",
                criado_em=agora,
            )
        ],
    )


def test_shape_das_estruturas_de_provenance() -> None:
    summary = build_inspector_content_origin_summary(
        laudo=SimpleNamespace(
            primeira_mensagem="Inspeção inicial em campo",
            parecer_ia="Rascunho IA",
            confianca_ia_json={"geral": "alta"},
            dados_formulario={"item": "valor"},
        ),
        message_counters=MessageOriginCounters(user_messages=1, ai_messages=1),
        has_active_report=True,
    )

    dumped = summary.model_dump(mode="json")
    assert dumped["contract_name"] == "ContentOriginSummaryV1"
    assert dumped["primary_origin"] in {"human", "ai_generated"}
    assert dumped["mix_kind"] == "human_with_unknown" or dumped["mix_kind"] == "mixed"
    assert dumped["has_human_inputs"] is True
    assert dumped["has_ai_outputs"] is True
    assert dumped["has_legacy_unknown_content"] is True
    assert dumped["entries"]


def test_derivacao_segura_da_provenance_do_inspetor() -> None:
    summary = build_inspector_content_origin_summary(
        laudo=SimpleNamespace(
            primeira_mensagem="Inspeção inicial em campo",
            parecer_ia="Rascunho IA",
            confianca_ia_json={"geral": "alta"},
            dados_formulario={"item": "valor"},
        ),
        message_counters=MessageOriginCounters(
            user_messages=2,
            inspector_whispers=1,
            ai_messages=1,
        ),
        has_active_report=True,
    )

    assert summary.has_human_inputs is True
    assert summary.has_ai_outputs is True
    assert summary.has_ai_assisted_content is False
    assert summary.has_legacy_unknown_content is True
    assert summary.quality == "partial"


def test_projecoes_canonicas_carregam_provenance_quando_snapshot_tem_resumo() -> None:
    provenance = build_inspector_content_origin_summary(
        laudo=SimpleNamespace(
            primeira_mensagem="Escopo humano",
            parecer_ia="Texto IA",
            confianca_ia_json={"geral": "alta"},
            dados_formulario={"campo": "valor"},
        ),
        message_counters=MessageOriginCounters(user_messages=1, ai_messages=1),
        has_active_report=True,
    )
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aguardando",
            "laudo_id": 88,
            "status_card": "aguardando",
            "permite_reabrir": False,
            "laudo_card": {"id": 88, "status_revisao": StatusRevisao.AGUARDANDO.value},
        },
        content_origin_summary=provenance,
    )

    inspector_projection = build_inspector_case_view_projection(
        case_snapshot=snapshot,
        actor_id=17,
        actor_role="inspetor",
        source_channel="web_app",
        allows_edit=False,
        has_interaction=True,
        report_types={"padrao": "Inspeção Geral (Padrão)"},
        laudo_card={"id": 88, "status_revisao": StatusRevisao.AGUARDANDO.value},
    )
    review_projection = build_reviewdesk_case_view_projection(
        case_snapshot=snapshot,
        pacote=_build_review_package(),
        actor_id=51,
        actor_role="revisor",
        source_channel="review_api",
    )

    inspector_payload = inspector_projection.model_dump(mode="json")["payload"]
    review_payload = review_projection.model_dump(mode="json")["payload"]
    assert inspector_payload["origin_summary"]["contract_name"] == "ContentOriginSummaryV1"
    assert inspector_payload["has_human_inputs"] is True
    assert inspector_payload["has_ai_outputs"] is True
    assert inspector_payload["has_legacy_unknown_content"] is True
    assert review_payload["origin_summary"]["contract_name"] == "ContentOriginSummaryV1"
    assert review_payload["human_vs_ai_mix"] in {"human_with_unknown", "mixed"}
    assert review_payload["provenance_quality"] == "partial"


def test_derivacao_segura_da_provenance_da_mesa() -> None:
    summary = build_reviewdesk_content_origin_summary(
        pacote=_build_review_package(),
    )

    assert summary.has_human_inputs is True
    assert summary.has_ai_outputs is True
    assert summary.has_ai_assisted_content is False
    assert summary.has_legacy_unknown_content is True
    assert summary.quality == "partial"


def test_status_relatorio_com_provenance_preserva_payload_publico(
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
            primeira_mensagem="Escopo inicial humano",
            parecer_ia="Rascunho IA",
            confianca_ia_json={"geral": "alta"},
            dados_formulario={"campo": "valor"},
        )
        banco.add(laudo)
        banco.flush()

        sessao = {"laudo_ativo_id": laudo.id, "estado_relatorio": "aguardando"}

        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_ENVELOPES", raising=False)
        monkeypatch.delenv("TARIEL_V2_INSPECTOR_PROJECTION", raising=False)
        monkeypatch.delenv("TARIEL_V2_PROVENANCE", raising=False)
        payload_base, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=_build_inspector_request(dict(sessao)),
                usuario=usuario,
                banco=banco,
            )
        )

        request_flags = _build_inspector_request(dict(sessao))
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        monkeypatch.setenv("TARIEL_V2_INSPECTOR_PROJECTION", "1")
        monkeypatch.setenv("TARIEL_V2_PROVENANCE", "1")
        payload_flags, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=request_flags,
                usuario=usuario,
                banco=banco,
            )
        )

    assert payload_flags == payload_base
    provenance = request_flags.state.v2_content_provenance_summary
    assert provenance["contract_name"] == "ContentOriginSummaryV1"
    assert provenance["has_human_inputs"] is True
    assert provenance["has_ai_outputs"] is True
    assert provenance["has_legacy_unknown_content"] is True
    assert request_flags.state.v2_inspector_projection_result["provenance"]["quality"] == "partial"
    assert request_flags.state.v2_inspector_projection_result["compatible"] is True


def test_pacote_da_mesa_com_provenance_preserva_payload_publico(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None

        laudo = Laudo(
            empresa_id=revisor.empresa_id,
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            status_conformidade=StatusLaudo.PENDENTE.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"campo": "valor"},
            parecer_ia="Rascunho IA",
        )
        banco.add(laudo)
        banco.flush()

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo.id,
                    remetente_id=ids["inspetor_a"],
                    tipo=TipoMensagem.USER.value,
                    conteudo="Evidência textual em campo",
                ),
                MensagemLaudo(
                    laudo_id=laudo.id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Resposta da IA",
                ),
                MensagemLaudo(
                    laudo_id=laudo.id,
                    remetente_id=revisor.id,
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Ajustar evidência",
                ),
            ]
        )
        banco.flush()

        request_base = _build_review_request()
        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_REVIEW_DESK_PROJECTION", raising=False)
        monkeypatch.delenv("TARIEL_V2_PROVENANCE", raising=False)
        response_base = asyncio.run(
            obter_pacote_mesa_laudo(
                laudo_id=laudo.id,
                request=request_base,
                limite_whispers=80,
                limite_pendencias=80,
                limite_revisoes=10,
                usuario=revisor,
                banco=banco,
            )
        )
        payload_base = json.loads(response_base.body)

        request_flags = _build_review_request()
        monkeypatch.setenv("TARIEL_V2_REVIEW_DESK_PROJECTION", "1")
        monkeypatch.setenv("TARIEL_V2_PROVENANCE", "1")
        response_flags = asyncio.run(
            obter_pacote_mesa_laudo(
                laudo_id=laudo.id,
                request=request_flags,
                limite_whispers=80,
                limite_pendencias=80,
                limite_revisoes=10,
                usuario=revisor,
                banco=banco,
            )
        )
        payload_flags = json.loads(response_flags.body)

    assert payload_flags == payload_base
    provenance = request_flags.state.v2_content_provenance_summary
    assert provenance["contract_name"] == "ContentOriginSummaryV1"
    assert provenance["has_human_inputs"] is True
    assert provenance["has_ai_outputs"] is True
    assert provenance["has_legacy_unknown_content"] is True
    assert request_flags.state.v2_reviewdesk_projection_result["provenance"]["quality"] == "partial"
    assert request_flags.state.v2_reviewdesk_projection_result["compatible"] is True
