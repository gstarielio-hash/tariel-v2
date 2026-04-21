from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.responses import HTMLResponse
from starlette.requests import Request

import app.domains.revisor.panel as review_panel_module
from app.domains.revisor.panel import painel_revisor
from app.shared.database import Laudo, MensagemLaudo, NivelAcesso, StatusRevisao, Usuario
from app.v2.adapters.review_queue_dashboard import ReviewQueueDashboardShadowResult
from app.v2.contracts.review_queue import build_review_queue_dashboard_projection
from tests.regras_rotas_criticas_support import (
    _criar_laudo,
    _criar_template_ativo,
)


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=51,
        empresa_id=33,
        nivel_acesso=NivelAcesso.REVISOR.value,
    )


def _build_request(query_string: str = "") -> Request:
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


def test_shape_da_projecao_canonica_da_fila_da_mesa() -> None:
    agora = datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc)
    projection = build_review_queue_dashboard_projection(
        tenant_id=33,
        filtro_inspetor_id=17,
        filtro_busca="nr13",
        filtro_aprendizados="pendentes",
        filtro_operacao="responder_agora",
        whispers_pendentes=[
            {
                "laudo_id": 88,
                "hash": "abc123",
                "texto": "Campo respondeu",
                "timestamp": "2026-03-30T12:00:00+00:00",
            }
        ],
        laudos_em_andamento=[
            {
                "id": 88,
                "hash_curto": "abc123",
                "primeira_mensagem": "Inspecao em campo",
                "setor_industrial": "NR-13",
                "status_revisao": StatusRevisao.RASCUNHO.value,
                "atualizado_em": agora,
                "criado_em": agora,
                "inspetor_nome": "Inspetor A",
                "whispers_nao_lidos": 1,
                "pendencias_abertas": 0,
                "aprendizados_pendentes": 0,
                "collaboration_summary": {
                    "open_pendency_count": 0,
                    "resolved_pendency_count": 0,
                    "recent_whisper_count": 1,
                    "unread_whisper_count": 1,
                    "recent_review_count": 0,
                    "has_open_pendencies": False,
                    "has_recent_whispers": True,
                    "requires_reviewer_attention": True,
                },
                "tempo_em_campo": "42 min",
                "tempo_em_campo_status": "sla-atencao",
                "fila_operacional": "responder_agora",
                "fila_operacional_label": "Responder agora",
                "prioridade_operacional": "critica",
                "prioridade_operacional_label": "Critica",
                "proxima_acao": "Responder inspetor",
                "case_status": "collecting_evidence",
                "case_lifecycle_status": "laudo_em_coleta",
                "case_workflow_mode": "laudo_com_mesa",
                "active_owner_role": "inspetor",
                "allowed_next_lifecycle_statuses": ["aguardando_mesa"],
                "allowed_surface_actions": ["chat_finalize"],
            }
        ],
        laudos_pendentes=[],
        laudos_avaliados=[
            {
                "id": 91,
                "hash_curto": "def456",
                "primeira_mensagem": "Historico",
                "setor_industrial": "NR-12",
                "status_revisao": StatusRevisao.APROVADO.value,
                "atualizado_em": agora,
                "criado_em": agora,
                "inspetor_nome": "Inspetor B",
                "whispers_nao_lidos": 0,
                "pendencias_abertas": 0,
                "aprendizados_pendentes": 0,
                "collaboration_summary": {
                    "open_pendency_count": 0,
                    "resolved_pendency_count": 0,
                    "recent_whisper_count": 0,
                    "unread_whisper_count": 0,
                    "recent_review_count": 0,
                    "has_open_pendencies": False,
                    "has_recent_whispers": False,
                    "requires_reviewer_attention": False,
                },
                "tempo_em_campo": "5 h",
                "tempo_em_campo_status": "",
                "fila_operacional": "historico",
                "fila_operacional_label": "Historico",
                "prioridade_operacional": "baixa",
                "prioridade_operacional_label": "Baixa",
                "proxima_acao": "Consultar historico",
                "case_status": "approved",
                "case_lifecycle_status": "aprovado",
                "case_workflow_mode": "laudo_com_mesa",
                "active_owner_role": "none",
                "allowed_next_lifecycle_statuses": [],
                "allowed_surface_actions": [],
            }
        ],
        total_aprendizados_pendentes=2,
        total_pendencias_abertas=1,
        total_whispers_pendentes=1,
        totais_operacao={
            "responder_agora": 1,
            "validar_aprendizado": 0,
            "aguardando_inspetor": 0,
            "fechamento_mesa": 0,
            "acompanhamento": 0,
        },
        templates_operacao={
            "total_templates": 3,
            "total_codigos": 2,
            "total_ativos": 1,
            "total_em_teste": 1,
            "total_rascunhos": 1,
            "total_word": 1,
            "total_pdf": 2,
            "total_codigos_sem_ativo": 0,
            "total_codigos_em_operacao": 1,
            "total_codigos_em_operacao_sem_ativo": 0,
            "total_bases_manuais": 1,
            "ultima_utilizacao_em": "2026-03-30T11:00:00+00:00",
            "ultima_utilizacao_em_label": "30/03/2026 08:00",
        },
        actor_id=51,
        actor_role="revisor",
        source_channel="review_panel",
    )

    dumped = projection.model_dump(mode="json")
    assert dumped["contract_name"] == "ReviewQueueDashboardProjectionV1"
    assert dumped["projection_audience"] == "review_queue_web"
    assert dumped["payload"]["filter_summary"]["inspector_id"] == 17
    assert dumped["payload"]["queue_summary"]["in_field_count"] == 1
    assert dumped["payload"]["queue_summary"]["recent_history_count"] == 1
    assert dumped["payload"]["queue_summary"]["observed_case_ids"] == ["88", "91"]
    assert dumped["payload"]["operation_totals"]["responder_agora"] == 1
    assert dumped["payload"]["queue_sections"]["em_andamento"][0]["fila_operacional"] == "responder_agora"
    assert dumped["payload"]["queue_sections"]["em_andamento"][0]["case_lifecycle_status"] == "laudo_em_coleta"
    assert dumped["payload"]["queue_sections"]["em_andamento"][0]["active_owner_role"] == "inspetor"
    assert dumped["payload"]["queue_sections"]["em_andamento"][0]["status_visual_label"] == "Em coleta / Responsavel: campo"
    assert dumped["payload"]["queue_sections"]["em_andamento"][0]["allowed_surface_actions"] == [
        "chat_finalize"
    ]
    assert dumped["payload"]["queue_sections"]["em_andamento"][0]["collaboration_summary"]["unread_whisper_count"] == 1
    assert dumped["payload"]["template_operation_summary"]["total_templates"] == 3


def test_painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.setattr(
        review_panel_module,
        "templates",
        SimpleNamespace(
            TemplateResponse=lambda request, template, context: HTMLResponse(
                "mesa:"
                f"{len(context['laudos_em_andamento'])}:"
                f"{len(context['laudos_pendentes'])}:"
                f"{len(context['laudos_avaliados'])}:"
                f"{context['totais_operacao'].get('responder_agora', 0)}:"
                f"{context['templates_operacao'].get('total_templates', 0)}"
            )
        ),
    )

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["revisor_a"])
        assert usuario is not None

        laudo_em_campo = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.APROVADO.value,
        )
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_em_campo,
                remetente_id=ids["inspetor_a"],
                tipo="humano_insp",
                conteudo="Campo respondeu para a mesa.",
                lida=False,
            )
        )
        _criar_template_ativo(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["revisor_a"],
            codigo_template="padrao",
            versao=1,
        )
        banco.commit()

        request_base = _build_request()
        monkeypatch.delenv("TARIEL_V2_REVIEW_QUEUE_PROJECTION", raising=False)
        response_base = asyncio.run(
            painel_revisor(
                request=request_base,
                usuario=usuario,
                banco=banco,
            )
        )

        request_flags = _build_request()
        monkeypatch.setenv("TARIEL_V2_REVIEW_QUEUE_PROJECTION", "1")
        response_flags = asyncio.run(
            painel_revisor(
                request=request_flags,
                usuario=usuario,
                banco=banco,
            )
        )

    assert response_flags.body == response_base.body
    assert request_flags.state.v2_review_queue_projection_result["compatible"] is True
    assert request_flags.state.v2_review_queue_projection_result["used_projection"] is True
    projection = request_flags.state.v2_review_queue_projection_result["projection"]
    assert projection["contract_name"] == "ReviewQueueDashboardProjectionV1"
    assert projection["payload"]["queue_summary"]["in_field_count"] == 1
    assert projection["payload"]["queue_summary"]["awaiting_review_count"] == 1
    assert projection["payload"]["queue_summary"]["recent_history_count"] == 1
    assert projection["payload"]["queue_summary"]["whisper_pending_count"] == 1
    assert projection["payload"]["operation_totals"]["responder_agora"] == 1
    assert projection["payload"]["operation_totals"]["fechamento_mesa"] == 1
    assert projection["payload"]["queue_sections"]["em_andamento"][0]["active_owner_role"] == "inspetor"
    assert projection["payload"]["template_operation_summary"]["total_templates"] >= 1


def test_shadow_da_fila_preserva_lifecycle_canonico_de_caso_devolvido(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.setattr(
        review_panel_module,
        "templates",
        SimpleNamespace(
            TemplateResponse=lambda request, template, context: HTMLResponse("ok")
        ),
    )

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["revisor_a"])
        assert usuario is not None

        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.REJEITADO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.revisado_por = usuario.id
        laudo.motivo_rejeicao = "Refazer a evidencia."
        laudo.primeira_mensagem = "Caso devolvido."
        banco.commit()

        request = _build_request()
        response = asyncio.run(
            painel_revisor(
                request=request,
                usuario=usuario,
                banco=banco,
            )
        )

    assert response.status_code == 200
    projection = request.state.v2_review_queue_projection_result["projection"]
    queue_item = projection["payload"]["queue_sections"]["em_andamento"][0]
    assert request.state.v2_review_queue_projection_result["compatible"] is True
    assert queue_item["case_lifecycle_status"] == "devolvido_para_correcao"
    assert queue_item["active_owner_role"] == "inspetor"
    assert queue_item["allowed_surface_actions"] == ["chat_finalize"]


def test_painel_revisor_pode_promover_projecao_canonica_da_fila_no_contexto_ssr(
    monkeypatch,
) -> None:
    class _FakePanelState:
        filtro_inspetor_id = None
        filtro_busca = ""
        filtro_aprendizados = ""
        filtro_operacao = ""
        whispers_pendentes = [{"laudo_id": 10, "hash": "legacy1", "texto": "legacy whisper"}]
        laudos_em_andamento = [{"id": 10, "hash_curto": "legacy1", "status_revisao": "Rascunho"}]
        laudos_pendentes = [{"id": 11, "hash_curto": "legacy2", "status_revisao": "Aguardando Aval"}]
        laudos_avaliados = []
        total_aprendizados_pendentes = 1
        total_pendencias_abertas = 2
        total_whispers_pendentes = 1
        totais_operacao = {"responder_agora": 1, "fechamento_mesa": 1}
        templates_operacao = {"total_templates": 1}
        inspetores_empresa = []

        def to_template_context(self, *, request, usuario):  # type: ignore[no-untyped-def]
            return {
                "request": request,
                "usuario": usuario,
                "inspetores_empresa": self.inspetores_empresa,
                "filtro_inspetor_id": self.filtro_inspetor_id,
                "filtro_busca": self.filtro_busca,
                "filtro_aprendizados": self.filtro_aprendizados,
                "filtro_operacao": self.filtro_operacao,
                "whispers_pendentes": list(self.whispers_pendentes),
                "laudos_em_andamento": list(self.laudos_em_andamento),
                "laudos_pendentes": list(self.laudos_pendentes),
                "laudos_avaliados": list(self.laudos_avaliados),
                "whispers_nao_lidos_por_laudo": {},
                "pendencias_abertas_por_laudo": {},
                "aprendizados_pendentes_por_laudo": {},
                "total_aprendizados_pendentes": self.total_aprendizados_pendentes,
                "total_pendencias_abertas": self.total_pendencias_abertas,
                "total_whispers_pendentes": self.total_whispers_pendentes,
                "totais_operacao": dict(self.totais_operacao),
                "templates_operacao": dict(self.templates_operacao),
            }

    captured_context: dict[str, object] = {}

    monkeypatch.setattr(
        review_panel_module,
        "build_review_panel_state",
        lambda **_kwargs: _FakePanelState(),
    )
    monkeypatch.setattr(
        review_panel_module,
        "templates",
        SimpleNamespace(
            TemplateResponse=lambda request, template, context: (
                captured_context.update(context) or HTMLResponse("ok")
            )
        ),
    )
    monkeypatch.setattr(
        review_panel_module,
        "registrar_shadow_review_queue_dashboard",
        lambda **_kwargs: ReviewQueueDashboardShadowResult(
            compatible=True,
            divergences=[],
            observed_case_count=2,
            projection={
                "contract_name": "ReviewQueueDashboardProjectionV1",
                "payload": {
                    "queue_summary": {
                        "total_pending_learning": 7,
                        "total_open_pendencies": 8,
                        "total_pending_whispers": 9,
                    },
                    "operation_totals": {
                        "responder_agora": 5,
                        "validar_aprendizado": 4,
                        "aguardando_inspetor": 3,
                        "fechamento_mesa": 2,
                        "acompanhamento": 1,
                    },
                    "template_operation_summary": {
                        "total_templates": 6,
                    },
                    "pending_whispers_preview": [
                        {"laudo_id": 90, "hash": "proj90", "texto": "projecao whisper"}
                    ],
                    "queue_sections": {
                        "em_andamento": [
                            {
                                "id": 90,
                                "hash_curto": "proj90",
                                "primeira_mensagem": "Projecao em campo",
                                "setor_industrial": "NR-13",
                                "status_revisao": "Rascunho",
                                "atualizado_em": datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc),
                                "criado_em": datetime(2026, 4, 2, 9, 0, tzinfo=timezone.utc),
                                "inspetor_nome": "Inspetor Proj",
                                "whispers_nao_lidos": 5,
                                "pendencias_abertas": 0,
                                "aprendizados_pendentes": 0,
                                "fila_operacional": "responder_agora",
                                "fila_operacional_label": "Responder agora",
                                "prioridade_operacional": "critica",
                                "prioridade_operacional_label": "Crítica",
                                "proxima_acao": "Responder inspetor",
                                "case_status": "collecting_evidence",
                                "case_lifecycle_status": "laudo_em_coleta",
                                "case_workflow_mode": "laudo_com_mesa",
                                "active_owner_role": "inspetor",
                                "allowed_next_lifecycle_statuses": ["aguardando_mesa"],
                                "allowed_surface_actions": ["chat_finalize"],
                            }
                        ],
                        "aguardando_avaliacao": [],
                        "historico": [],
                    },
                },
            },
        ),
    )
    monkeypatch.setenv("TARIEL_V2_REVIEW_QUEUE_PROJECTION", "1")
    monkeypatch.setenv("TARIEL_V2_REVIEW_QUEUE_PROJECTION_PREFER", "1")
    monkeypatch.setattr(review_panel_module, "resolve_review_panel_redirect_url", lambda _request: None)
    monkeypatch.setattr(review_panel_module, "resolve_review_panel_surface", lambda _request: "ssr")

    request = _build_request()
    usuario = _build_user()

    response = asyncio.run(
        painel_revisor(
            request=request,
            usuario=usuario,
            banco=SimpleNamespace(),
        )
    )

    assert response.status_code == 200
    assert request.state.v2_review_queue_projection_preferred is True
    assert captured_context["total_whispers_pendentes"] == 9
    assert captured_context["total_pendencias_abertas"] == 8
    assert captured_context["total_aprendizados_pendentes"] == 7
    assert captured_context["totais_operacao"]["responder_agora"] == 5
    assert captured_context["templates_operacao"]["total_templates"] == 6
    assert captured_context["whispers_pendentes"][0]["hash"] == "proj90"
    assert captured_context["laudos_em_andamento"][0]["id"] == 90
    assert captured_context["laudos_em_andamento"][0]["case_lifecycle_status"] == "laudo_em_coleta"
    assert captured_context["laudos_em_andamento"][0]["active_owner_role"] == "inspetor"


def test_painel_revisor_nao_promove_projecao_incompativel_no_contexto_ssr(
    monkeypatch,
) -> None:
    class _FakePanelState:
        filtro_inspetor_id = None
        filtro_busca = ""
        filtro_aprendizados = ""
        filtro_operacao = ""
        whispers_pendentes = []
        laudos_em_andamento = [{"id": 10, "hash_curto": "legacy1", "status_revisao": "Rascunho"}]
        laudos_pendentes = []
        laudos_avaliados = []
        total_aprendizados_pendentes = 1
        total_pendencias_abertas = 2
        total_whispers_pendentes = 3
        totais_operacao = {"responder_agora": 1}
        templates_operacao = {"total_templates": 1}
        inspetores_empresa = []

        def to_template_context(self, *, request, usuario):  # type: ignore[no-untyped-def]
            return {
                "request": request,
                "usuario": usuario,
                "inspetores_empresa": self.inspetores_empresa,
                "filtro_inspetor_id": self.filtro_inspetor_id,
                "filtro_busca": self.filtro_busca,
                "filtro_aprendizados": self.filtro_aprendizados,
                "filtro_operacao": self.filtro_operacao,
                "whispers_pendentes": list(self.whispers_pendentes),
                "laudos_em_andamento": list(self.laudos_em_andamento),
                "laudos_pendentes": list(self.laudos_pendentes),
                "laudos_avaliados": list(self.laudos_avaliados),
                "whispers_nao_lidos_por_laudo": {},
                "pendencias_abertas_por_laudo": {},
                "aprendizados_pendentes_por_laudo": {},
                "total_aprendizados_pendentes": self.total_aprendizados_pendentes,
                "total_pendencias_abertas": self.total_pendencias_abertas,
                "total_whispers_pendentes": self.total_whispers_pendentes,
                "totais_operacao": dict(self.totais_operacao),
                "templates_operacao": dict(self.templates_operacao),
            }

    captured_context: dict[str, object] = {}

    monkeypatch.setattr(
        review_panel_module,
        "build_review_panel_state",
        lambda **_kwargs: _FakePanelState(),
    )
    monkeypatch.setattr(
        review_panel_module,
        "templates",
        SimpleNamespace(
            TemplateResponse=lambda request, template, context: (
                captured_context.update(context) or HTMLResponse("ok")
            )
        ),
    )
    monkeypatch.setattr(
        review_panel_module,
        "registrar_shadow_review_queue_dashboard",
        lambda **_kwargs: ReviewQueueDashboardShadowResult(
            compatible=False,
            divergences=["queue_summary"],
            observed_case_count=0,
            projection={"payload": {}},
        ),
    )
    monkeypatch.setenv("TARIEL_V2_REVIEW_QUEUE_PROJECTION", "1")
    monkeypatch.setenv("TARIEL_V2_REVIEW_QUEUE_PROJECTION_PREFER", "1")
    monkeypatch.setattr(review_panel_module, "resolve_review_panel_redirect_url", lambda _request: None)
    monkeypatch.setattr(review_panel_module, "resolve_review_panel_surface", lambda _request: "ssr")

    request = _build_request()
    usuario = _build_user()

    response = asyncio.run(
        painel_revisor(
            request=request,
            usuario=usuario,
            banco=SimpleNamespace(),
        )
    )

    assert response.status_code == 200
    assert request.state.v2_review_queue_projection_preferred is False
    assert captured_context["total_whispers_pendentes"] == 3
    assert captured_context["total_pendencias_abertas"] == 2
    assert captured_context["laudos_em_andamento"][0]["id"] == 10
