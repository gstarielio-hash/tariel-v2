from __future__ import annotations

from datetime import datetime, timezone

from starlette.requests import Request

from app.domains.mesa.service import _build_emissao_oficial_pacote, montar_pacote_mesa_laudo
from app.domains.revisor.panel_state import build_review_panel_state
from app.domains.revisor.service_package import carregar_laudo_completo_revisor
from app.domains.revisor.templates_laudo_support import coletar_metricas_uso_templates
from app.shared.database import Laudo, StatusRevisao, Usuario
from tests.regras_rotas_criticas_support import _criar_laudo


def _build_review_request(query_string: str = "") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/revisao/painel",
            "headers": [],
            "query_string": query_string.encode(),
            "session": {},
            "state": {},
        }
    )


def test_review_panel_state_classifica_devolvido_para_correcao_como_fluxo_do_inspetor(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None

        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.REJEITADO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Caso devolvido para correcao."
        laudo.revisado_por = revisor.id
        laudo.motivo_rejeicao = "Falta reenviar evidencia."
        laudo.atualizado_em = datetime.now(timezone.utc)
        banco.commit()

        state = build_review_panel_state(
            request=_build_review_request(),
            usuario=revisor,
            banco=banco,
        )

    assert [item["id"] for item in state.laudos_em_andamento] == [laudo_id]
    assert state.laudos_pendentes == []
    assert state.laudos_avaliados == []
    assert state.laudos_em_andamento[0]["case_lifecycle_status"] == "devolvido_para_correcao"
    assert state.laudos_em_andamento[0]["active_owner_role"] == "inspetor"
    assert state.laudos_em_andamento[0]["fila_operacional"] == "acompanhamento"


def test_build_emissao_oficial_pacote_tipifica_sinal_de_divergencia_do_pdf_principal() -> None:
    emissao_oficial = _build_emissao_oficial_pacote(
        {
            "issue_status": "reissue_recommended",
            "issue_status_label": "Reemissao recomendada",
            "already_issued": True,
            "reissue_recommended": True,
            "audit_trail": [],
            "blockers": [],
            "signatories": [],
            "current_issue": {
                "id": 91,
                "issue_state": "issued",
                "issue_state_label": "Emitido oficialmente",
                "issue_number": "TAR-20260417-0001",
                "primary_pdf_sha256": "a" * 64,
                "primary_pdf_storage_version": "v0003",
                "primary_pdf_storage_version_number": 3,
                "current_primary_pdf_sha256": "b" * 64,
                "current_primary_pdf_storage_version": "v0004",
                "current_primary_pdf_storage_version_number": 4,
                "primary_pdf_diverged": True,
                "primary_pdf_comparison_status": "diverged",
                "reissue_of_issue_id": 77,
                "reissue_of_issue_number": "TAR-20260410-0008",
                "reissue_reason_codes": ["primary_pdf_diverged"],
                "reissue_reason_summary": "Reemissão motivada por divergência do PDF principal.",
            },
        }
    )

    assert emissao_oficial is not None
    assert emissao_oficial.current_issue is not None
    assert emissao_oficial.current_issue.primary_pdf_sha256 == "a" * 64
    assert emissao_oficial.current_issue.primary_pdf_storage_version == "v0003"
    assert emissao_oficial.current_issue.primary_pdf_storage_version_number == 3
    assert emissao_oficial.current_issue.current_primary_pdf_sha256 == "b" * 64
    assert emissao_oficial.current_issue.current_primary_pdf_storage_version == "v0004"
    assert emissao_oficial.current_issue.current_primary_pdf_storage_version_number == 4
    assert emissao_oficial.current_issue.primary_pdf_diverged is True
    assert emissao_oficial.current_issue.primary_pdf_comparison_status == "diverged"
    assert emissao_oficial.current_issue.reissue_of_issue_id == 77
    assert emissao_oficial.current_issue.reissue_of_issue_number == "TAR-20260410-0008"
    assert emissao_oficial.current_issue.reissue_reason_codes == ["primary_pdf_diverged"]
    assert emissao_oficial.current_issue.reissue_reason_summary == "Reemissão motivada por divergência do PDF principal."


def test_review_panel_state_nao_perde_caso_reaberto_que_ainda_carrega_status_aprovado_legado(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None

        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.APROVADO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Caso reaberto e devolvido ao campo."
        laudo.reaberto_em = datetime.now(timezone.utc)
        laudo.atualizado_em = datetime.now(timezone.utc)
        banco.commit()

        state = build_review_panel_state(
            request=_build_review_request(),
            usuario=revisor,
            banco=banco,
        )

    assert [item["id"] for item in state.laudos_em_andamento] == [laudo_id]
    assert state.laudos_pendentes == []
    assert state.laudos_avaliados == []
    assert state.laudos_em_andamento[0]["status_revisao"] == StatusRevisao.APROVADO.value
    assert state.laudos_em_andamento[0]["case_lifecycle_status"] == "devolvido_para_correcao"
    assert state.laudos_em_andamento[0]["active_owner_role"] == "inspetor"
    assert state.laudos_em_andamento[0]["fila_operacional"] == "acompanhamento"


def test_metricas_templates_contam_devolvido_como_uso_em_campo_e_nao_aguardando(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.REJEITADO.value,
            tipo_template="nr13",
        )
        _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
            tipo_template="nr13",
        )

        metricas = coletar_metricas_uso_templates(
            banco,
            empresa_id=ids["empresa_a"],
        )

    assert metricas["nr13"]["uso_total"] == 2
    assert metricas["nr13"]["uso_em_campo"] == 1
    assert metricas["nr13"]["uso_aguardando"] == 1


def test_read_side_revisor_expoe_lifecycle_canonico_e_pacote_oculta_owner_mesa_inativo(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None

        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.REJEITADO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Caso voltou para o campo."
        laudo.revisado_por = revisor.id
        laudo.motivo_rejeicao = "Refazer captura."
        banco.commit()

        payload = carregar_laudo_completo_revisor(
            banco,
            laudo_id=laudo_id,
            empresa_id=ids["empresa_a"],
            incluir_historico=False,
            cursor=None,
            limite=60,
        )
        pacote = montar_pacote_mesa_laudo(
            banco,
            laudo=laudo,
            limite_whispers=20,
            limite_pendencias=20,
            limite_revisoes=10,
        )

    assert payload["status"] == StatusRevisao.REJEITADO.value
    assert payload["case_status"] == "review_feedback_pending"
    assert payload["case_lifecycle_status"] == "devolvido_para_correcao"
    assert payload["active_owner_role"] == "inspetor"
    assert payload["status_visual_label"] == "Devolvido para correcao / Responsavel: campo"
    assert payload["allowed_surface_actions"] == ["chat_finalize"]
    assert pacote.verificacao_publica is not None
    assert pacote.verificacao_publica.status_visual_label == "Devolvido para correcao / Responsavel: campo"
    assert pacote.revisor_id is None
