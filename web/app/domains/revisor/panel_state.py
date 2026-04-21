from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.domains.mesa.attachments import resumo_mensagem_mesa
from app.domains.chat.laudo_state_helpers import (
    criar_cache_resumo_laudos,
    precarregar_interacoes_laudos,
    resolver_snapshot_leitura_caso_tecnico,
)
from app.domains.revisor.base import (
    _contar_mensagens_nao_lidas_por_laudo,
    _minutos_em_campo,
    _normalizar_termo_busca,
    _resumo_tempo_em_campo,
)
from app.domains.revisor.common import _contexto_base
from app.domains.revisor.templates_laudo_support import resumir_operacao_templates_mesa
from app.shared.database import (
    AprendizadoVisualIa,
    Laudo,
    MensagemLaudo,
    NivelAcesso,
    StatusAprendizadoIa,
    TipoMensagem,
    Usuario,
)
from app.shared.security import PORTAL_REVISOR, usuario_portal_switch_links
from app.v2.acl.technical_case_core import build_case_status_visual_label
from app.v2.contracts.collaboration import build_reviewdesk_collaboration_summary

OPERACOES_VALIDAS = {
    "responder_agora",
    "validar_aprendizado",
    "aguardando_inspetor",
    "fechamento_mesa",
    "acompanhamento",
}


@dataclass(slots=True)
class ReviewPanelState:
    inspetores_empresa: list[Usuario]
    filtro_inspetor_id: int | None
    filtro_busca: str
    filtro_aprendizados: str
    filtro_operacao: str
    whispers_pendentes: list[dict[str, Any]]
    laudos_em_andamento: list[dict[str, Any]]
    laudos_pendentes: list[dict[str, Any]]
    laudos_avaliados: list[dict[str, Any]]
    whispers_nao_lidos_por_laudo: dict[int, int]
    pendencias_abertas_por_laudo: dict[int, int]
    aprendizados_pendentes_por_laudo: dict[int, int]
    total_aprendizados_pendentes: int
    total_pendencias_abertas: int
    total_whispers_pendentes: int
    totais_operacao: dict[str, int]
    templates_operacao: dict[str, Any]

    def to_template_context(
        self,
        *,
        request: Request,
        usuario: Usuario,
    ) -> dict[str, Any]:
        return {
            **_contexto_base(request),
            "usuario": usuario,
            "portal_switch_links": usuario_portal_switch_links(
                usuario,
                portal_atual=PORTAL_REVISOR,
            ),
            "inspetores_empresa": self.inspetores_empresa,
            "filtro_inspetor_id": self.filtro_inspetor_id,
            "filtro_busca": self.filtro_busca,
            "filtro_aprendizados": self.filtro_aprendizados,
            "filtro_operacao": self.filtro_operacao,
            "whispers_pendentes": self.whispers_pendentes,
            "laudos_em_andamento": self.laudos_em_andamento,
            "laudos_pendentes": self.laudos_pendentes,
            "laudos_avaliados": self.laudos_avaliados,
            "whispers_nao_lidos_por_laudo": self.whispers_nao_lidos_por_laudo,
            "pendencias_abertas_por_laudo": self.pendencias_abertas_por_laudo,
            "aprendizados_pendentes_por_laudo": self.aprendizados_pendentes_por_laudo,
            "total_aprendizados_pendentes": self.total_aprendizados_pendentes,
            "total_pendencias_abertas": self.total_pendencias_abertas,
            "total_whispers_pendentes": self.total_whispers_pendentes,
            "totais_operacao": self.totais_operacao,
            "templates_operacao": self.templates_operacao,
        }


def _normalizar_status_revisao(valor: Any) -> str:
    return str(getattr(valor, "value", valor) or "").strip()


def _contar_aprendizados_pendentes_por_laudo(
    banco: Session,
    *,
    laudo_ids: list[int],
) -> dict[int, int]:
    ids_normalizados = sorted({int(item) for item in laudo_ids if int(item) > 0})
    if not ids_normalizados:
        return {}

    registros = (
        banco.query(
            AprendizadoVisualIa.laudo_id,
            func.count(AprendizadoVisualIa.id),
        )
        .filter(
            AprendizadoVisualIa.laudo_id.in_(ids_normalizados),
            AprendizadoVisualIa.status == StatusAprendizadoIa.RASCUNHO_INSPETOR.value,
        )
        .group_by(AprendizadoVisualIa.laudo_id)
        .all()
    )
    return {
        int(laudo_id): int(total or 0)
        for laudo_id, total in registros
    }


def _classificar_fluxo_operacional(
    *,
    case_lifecycle_status: str,
    active_owner_role: str,
    whispers_nao_lidos: int,
    pendencias_abertas: int,
    aprendizados_pendentes: int,
    tempo_em_campo_status: str = "",
) -> dict[str, str]:
    lifecycle_status = str(case_lifecycle_status or "").strip().lower()
    owner_role = str(active_owner_role or "").strip().lower()
    sla = str(tempo_em_campo_status or "").strip()
    whispers = max(0, int(whispers_nao_lidos or 0))
    pendencias = max(0, int(pendencias_abertas or 0))
    aprendizados = max(0, int(aprendizados_pendentes or 0))

    if whispers > 0:
        return {
            "fila_operacional": "responder_agora",
            "fila_operacional_label": "Responder agora",
            "proxima_acao": "Responder inspetor",
            "prioridade_operacional": "critica",
            "prioridade_operacional_label": "Crítica",
            "resumo_operacional": "Whisper novo aguardando retorno técnico da mesa.",
        }
    if aprendizados > 0:
        return {
            "fila_operacional": "validar_aprendizado",
            "fila_operacional_label": "Validar aprendizado",
            "proxima_acao": "Validar aprendizado",
            "prioridade_operacional": "alta",
            "prioridade_operacional_label": "Alta",
            "resumo_operacional": "Há correções do campo aguardando validação final da mesa.",
        }
    if pendencias > 0:
        return {
            "fila_operacional": "aguardando_inspetor",
            "fila_operacional_label": "Aguardando campo",
            "proxima_acao": "Cobrar retorno do campo",
            "prioridade_operacional": "alta" if sla == "sla-critico" else "media",
            "prioridade_operacional_label": "Alta" if sla == "sla-critico" else "Média",
            "resumo_operacional": "A mesa já provocou o campo e ainda aguarda retorno do inspetor.",
        }
    if owner_role == "mesa" or lifecycle_status in {"aguardando_mesa", "em_revisao_mesa"}:
        return {
            "fila_operacional": "fechamento_mesa",
            "fila_operacional_label": "Fechamento",
            "proxima_acao": "Fechar revisão",
            "prioridade_operacional": "media",
            "prioridade_operacional_label": "Média",
            "resumo_operacional": "Laudo pronto para revisão final e decisão da mesa.",
        }
    if owner_role == "inspetor":
        return {
            "fila_operacional": "acompanhamento",
            "fila_operacional_label": "Acompanhamento",
            "proxima_acao": "Acompanhar campo",
            "prioridade_operacional": "alta" if sla == "sla-critico" else "media" if sla == "sla-atencao" else "baixa",
            "prioridade_operacional_label": "Alta" if sla == "sla-critico" else "Média" if sla == "sla-atencao" else "Baixa",
            "resumo_operacional": "Fluxo em campo sem bloqueios abertos neste momento.",
        }
    return {
        "fila_operacional": "historico",
        "fila_operacional_label": "Histórico",
        "proxima_acao": "Consultar histórico",
        "prioridade_operacional": "baixa",
        "prioridade_operacional_label": "Baixa",
        "resumo_operacional": "Laudo finalizado, mantido como referência de consulta.",
    }


def _prioridade_fluxo_valor(valor: str) -> int:
    mapa = {
        "critica": 0,
        "alta": 1,
        "media": 2,
        "baixa": 3,
    }
    return mapa.get(str(valor or "").strip().lower(), 9)


def _resolver_filtros_painel(
    *,
    request: Request,
    inspetores_empresa: list[Usuario],
    usuario: Usuario,
) -> tuple[int | None, str, str, str, list[Any]]:
    filtro_inspetor_id: int | None = None
    valor_filtro_bruto = (request.query_params.get("inspetor") or "").strip()
    if valor_filtro_bruto:
        try:
            valor_filtro = int(valor_filtro_bruto)
            if valor_filtro > 0:
                ids_inspetores = {item.id for item in inspetores_empresa}
                if valor_filtro in ids_inspetores:
                    filtro_inspetor_id = valor_filtro
        except ValueError:
            filtro_inspetor_id = None

    filtros_laudo: list[Any] = [Laudo.empresa_id == usuario.empresa_id]
    if filtro_inspetor_id is not None:
        filtros_laudo.append(Laudo.usuario_id == filtro_inspetor_id)

    filtro_busca = _normalizar_termo_busca(request.query_params.get("q") or "")
    if filtro_busca:
        padrao = f"%{filtro_busca}%"
        filtros_laudo.append(
            or_(
                Laudo.codigo_hash.ilike(padrao),
                Laudo.primeira_mensagem.ilike(padrao),
                Laudo.setor_industrial.ilike(padrao),
                Laudo.tipo_template.ilike(padrao),
            )
        )

    filtro_aprendizados = (request.query_params.get("aprendizados") or "").strip().lower()
    if filtro_aprendizados in {"pendentes", "1", "true", "sim"}:
        filtro_aprendizados = "pendentes"
        filtros_laudo.append(
            Laudo.aprendizados_visuais_ia.any(
                AprendizadoVisualIa.status == StatusAprendizadoIa.RASCUNHO_INSPETOR.value,
            )
        )
    else:
        filtro_aprendizados = ""

    filtro_operacao = (request.query_params.get("operacao") or "").strip().lower()
    if filtro_operacao not in OPERACOES_VALIDAS:
        filtro_operacao = ""

    return (
        filtro_inspetor_id,
        filtro_busca,
        filtro_aprendizados,
        filtro_operacao,
        filtros_laudo,
    )


def _grupo_fila_por_snapshot(*, case_lifecycle_status: str, active_owner_role: str) -> str:
    lifecycle_status = str(case_lifecycle_status or "").strip().lower()
    owner_role = str(active_owner_role or "").strip().lower()
    if lifecycle_status in {"aprovado", "emitido"} or owner_role == "none":
        return "historico"
    if owner_role == "mesa" or lifecycle_status in {"aguardando_mesa", "em_revisao_mesa"}:
        return "pendente"
    return "em_andamento"


def build_review_panel_state(
    *,
    request: Request,
    usuario: Usuario,
    banco: Session,
) -> ReviewPanelState:
    inspetores_empresa = (
        banco.query(Usuario)
        .filter(
            Usuario.empresa_id == usuario.empresa_id,
            Usuario.nivel_acesso == int(NivelAcesso.INSPETOR),
            Usuario.ativo.is_(True),
        )
        .order_by(Usuario.nome_completo.asc(), Usuario.id.asc())
        .all()
    )
    (
        filtro_inspetor_id,
        filtro_busca,
        filtro_aprendizados,
        filtro_operacao,
        filtros_laudo,
) = _resolver_filtros_painel(
        request=request,
        inspetores_empresa=inspetores_empresa,
        usuario=usuario,
    )

    laudos_candidatos = (
        banco.query(Laudo)
        .filter(
            *filtros_laudo,
        )
        .order_by(Laudo.atualizado_em.desc().nullslast(), Laudo.criado_em.desc().nullslast(), Laudo.id.desc())
        .all()
    )

    cache_resumo = criar_cache_resumo_laudos()
    precarregar_interacoes_laudos(
        banco,
        [int(item.id) for item in laudos_candidatos],
        cache=cache_resumo,
    )
    snapshots_por_laudo = {
        int(item.id): resolver_snapshot_leitura_caso_tecnico(
            banco,
            item,
            cache=cache_resumo,
        )
        for item in laudos_candidatos
    }
    grupos_por_laudo = {
        laudo_id: _grupo_fila_por_snapshot(
            case_lifecycle_status=snapshot.case_lifecycle_status if snapshot is not None else "",
            active_owner_role=snapshot.active_owner_role if snapshot is not None else "",
        )
        for laudo_id, snapshot in snapshots_por_laudo.items()
    }

    laudos_em_andamento = [item for item in laudos_candidatos if grupos_por_laudo.get(int(item.id)) == "em_andamento"]
    laudos_pendentes = [item for item in laudos_candidatos if grupos_por_laudo.get(int(item.id)) == "pendente"]
    laudos_avaliados = [
        item for item in laudos_candidatos if grupos_por_laudo.get(int(item.id)) == "historico"
    ]
    laudos_avaliados.sort(
        key=lambda item: (
            item.atualizado_em or item.criado_em,
            item.criado_em,
            item.id,
        ),
        reverse=True,
    )
    laudos_avaliados = laudos_avaliados[:10]

    laudo_ids_abertos = sorted(
        {
            *[int(item.id) for item in laudos_em_andamento if int(item.id or 0) > 0],
            *[int(item.id) for item in laudos_pendentes if int(item.id or 0) > 0],
        }
    )
    whispers_pendentes_db = []
    if laudo_ids_abertos:
        whispers_pendentes_db = (
            banco.query(MensagemLaudo)
            .options(selectinload(MensagemLaudo.anexos_mesa))
            .filter(
                MensagemLaudo.laudo_id.in_(laudo_ids_abertos),
                MensagemLaudo.tipo == TipoMensagem.HUMANO_INSP.value,
                MensagemLaudo.lida.is_(False),
            )
            .order_by(MensagemLaudo.criado_em.desc())
            .limit(10)
            .all()
        )

    whispers_hash_por_laudo = {
        int(item.id): str(item.codigo_hash or str(item.id))[-6:]
        for item in [*laudos_em_andamento, *laudos_pendentes]
    }

    usuario_ids_laudos = sorted(
        {
            int(item.usuario_id)
            for item in [*laudos_em_andamento, *laudos_pendentes, *laudos_avaliados]
            if int(item.usuario_id or 0) > 0
        }
    )
    usuarios_por_id: dict[int, Usuario] = {}
    if usuario_ids_laudos:
        usuarios_por_id = {
            int(item.id): item
            for item in banco.query(Usuario).filter(Usuario.id.in_(usuario_ids_laudos)).all()
        }

    laudo_ids_metricas = sorted(
        {
            *[int(item.laudo_id) for item in whispers_pendentes_db if int(item.laudo_id or 0) > 0],
            *[int(item.id) for item in laudos_em_andamento],
            *[int(item.id) for item in laudos_pendentes],
            *[int(item.id) for item in laudos_avaliados],
        }
    )
    whispers_nao_lidos_por_laudo = _contar_mensagens_nao_lidas_por_laudo(
        banco,
        laudo_ids=laudo_ids_metricas,
        tipo=TipoMensagem.HUMANO_INSP,
    )
    pendencias_abertas_por_laudo = _contar_mensagens_nao_lidas_por_laudo(
        banco,
        laudo_ids=laudo_ids_metricas,
        tipo=TipoMensagem.HUMANO_ENG,
    )
    aprendizados_pendentes_por_laudo = _contar_aprendizados_pendentes_por_laudo(
        banco,
        laudo_ids=laudo_ids_metricas,
    )
    whispers_pendentes = []
    for item in whispers_pendentes_db:
        laudo_id = int(item.laudo_id)
        case_snapshot = snapshots_por_laudo.get(laudo_id)
        collaboration_summary = build_reviewdesk_collaboration_summary(
            open_pendency_count=pendencias_abertas_por_laudo.get(laudo_id, 0),
            recent_whisper_count=whispers_nao_lidos_por_laudo.get(laudo_id, 0),
            unread_whisper_count=whispers_nao_lidos_por_laudo.get(laudo_id, 0),
        )
        whispers_pendentes.append(
            {
                "laudo_id": laudo_id,
                "hash": whispers_hash_por_laudo.get(laudo_id, str(item.laudo_id))[-6:],
                "texto": resumo_mensagem_mesa(item.conteudo or "", anexos=getattr(item, "anexos_mesa", None)),
                "timestamp": item.criado_em.isoformat() if item.criado_em else "",
                "case_lifecycle_status": (
                    case_snapshot.case_lifecycle_status if case_snapshot is not None else ""
                ),
                "active_owner_role": (
                    case_snapshot.active_owner_role if case_snapshot is not None else ""
                ),
                "status_visual_label": build_case_status_visual_label(
                    lifecycle_status=(
                        case_snapshot.case_lifecycle_status if case_snapshot is not None else ""
                    ),
                    active_owner_role=(
                        case_snapshot.active_owner_role if case_snapshot is not None else ""
                    ),
                ),
                "collaboration_summary": collaboration_summary.model_dump(mode="python"),
            }
        )

    def _serializar_item_lista(laudo: Laudo, *, grupo: str) -> dict[str, Any]:
        laudo_id = int(laudo.id)
        referencia = laudo.criado_em or laudo.atualizado_em
        minutos_em_campo = _minutos_em_campo(referencia)
        tempo_label, tempo_status = _resumo_tempo_em_campo(referencia)
        inspetor = usuarios_por_id.get(int(laudo.usuario_id or 0))
        inspetor_nome = (
            inspetor.nome
            if inspetor is not None
            else (f"Inspetor #{laudo.usuario_id}" if laudo.usuario_id else "Inspetor não identificado")
        )
        whispers_nao_lidos = whispers_nao_lidos_por_laudo.get(laudo_id, 0)
        pendencias_abertas = pendencias_abertas_por_laudo.get(laudo_id, 0)
        aprendizados_pendentes = aprendizados_pendentes_por_laudo.get(laudo_id, 0)
        case_snapshot = snapshots_por_laudo.get(laudo_id)
        fluxo = _classificar_fluxo_operacional(
            case_lifecycle_status=(
                case_snapshot.case_lifecycle_status if case_snapshot is not None else ""
            ),
            active_owner_role=(
                case_snapshot.active_owner_role if case_snapshot is not None else ""
            ),
            whispers_nao_lidos=whispers_nao_lidos,
            pendencias_abertas=pendencias_abertas,
            aprendizados_pendentes=aprendizados_pendentes,
            tempo_em_campo_status=tempo_status,
        )
        collaboration_summary = build_reviewdesk_collaboration_summary(
            open_pendency_count=pendencias_abertas,
            recent_whisper_count=whispers_nao_lidos,
            unread_whisper_count=whispers_nao_lidos,
        )
        return {
            "id": laudo_id,
            "hash_curto": (laudo.codigo_hash or str(laudo_id))[-6:],
            "primeira_mensagem": laudo.primeira_mensagem or ("Inspeção iniciada em campo" if grupo == "em_andamento" else "Sem descrição"),
            "setor_industrial": str(getattr(laudo, "setor_industrial", "") or ""),
            "status_revisao": _normalizar_status_revisao(laudo.status_revisao),
            "case_status": case_snapshot.canonical_status if case_snapshot is not None else None,
            "case_lifecycle_status": case_snapshot.case_lifecycle_status if case_snapshot is not None else None,
            "case_workflow_mode": case_snapshot.workflow_mode if case_snapshot is not None else None,
            "active_owner_role": case_snapshot.active_owner_role if case_snapshot is not None else None,
            "allowed_next_lifecycle_statuses": (
                list(case_snapshot.allowed_next_lifecycle_statuses)
                if case_snapshot is not None
                else []
            ),
            "allowed_surface_actions": (
                list(case_snapshot.allowed_surface_actions)
                if case_snapshot is not None
                else []
            ),
            "status_visual_label": build_case_status_visual_label(
                lifecycle_status=(
                    case_snapshot.case_lifecycle_status if case_snapshot is not None else ""
                ),
                active_owner_role=(
                    case_snapshot.active_owner_role if case_snapshot is not None else ""
                ),
            ),
            "atualizado_em": laudo.atualizado_em or laudo.criado_em,
            "criado_em": laudo.criado_em,
            "inspetor_nome": inspetor_nome,
            "whispers_nao_lidos": whispers_nao_lidos,
            "pendencias_abertas": pendencias_abertas,
            "aprendizados_pendentes": aprendizados_pendentes,
            "collaboration_summary": collaboration_summary.model_dump(mode="python"),
            "tempo_em_campo": tempo_label,
            "tempo_em_campo_status": tempo_status,
            "_minutos_em_campo": minutos_em_campo,
            **fluxo,
        }

    laudos_em_andamento_payload = [
        _serializar_item_lista(item, grupo="em_andamento")
        for item in laudos_em_andamento
    ]
    laudos_pendentes_payload = [
        _serializar_item_lista(item, grupo="pendente")
        for item in laudos_pendentes
    ]
    laudos_avaliados_payload = [
        _serializar_item_lista(item, grupo="historico")
        for item in laudos_avaliados
    ]

    if filtro_operacao:
        laudos_em_andamento_payload = [item for item in laudos_em_andamento_payload if item["fila_operacional"] == filtro_operacao]
        laudos_pendentes_payload = [item for item in laudos_pendentes_payload if item["fila_operacional"] == filtro_operacao]

    laudos_em_andamento_payload.sort(
        key=lambda item: (
            _prioridade_fluxo_valor(str(item.get("prioridade_operacional"))),
            -int(item.get("_minutos_em_campo") or 0),
            int(item.get("id") or 0),
        )
    )
    laudos_pendentes_payload.sort(
        key=lambda item: (
            _prioridade_fluxo_valor(str(item.get("prioridade_operacional"))),
            -int(item.get("aprendizados_pendentes") or 0),
            int(item.get("id") or 0),
        )
    )
    for item in [*laudos_em_andamento_payload, *laudos_pendentes_payload, *laudos_avaliados_payload]:
        item.pop("_minutos_em_campo", None)

    totais_operacao = {
        "responder_agora": 0,
        "validar_aprendizado": 0,
        "aguardando_inspetor": 0,
        "fechamento_mesa": 0,
        "acompanhamento": 0,
    }
    for item in [*laudos_em_andamento_payload, *laudos_pendentes_payload]:
        chave = str(item.get("fila_operacional") or "")
        if chave in totais_operacao:
            totais_operacao[chave] += 1

    return ReviewPanelState(
        inspetores_empresa=inspetores_empresa,
        filtro_inspetor_id=filtro_inspetor_id,
        filtro_busca=filtro_busca,
        filtro_aprendizados=filtro_aprendizados,
        filtro_operacao=filtro_operacao,
        whispers_pendentes=whispers_pendentes,
        laudos_em_andamento=laudos_em_andamento_payload,
        laudos_pendentes=laudos_pendentes_payload,
        laudos_avaliados=laudos_avaliados_payload,
        whispers_nao_lidos_por_laudo=whispers_nao_lidos_por_laudo,
        pendencias_abertas_por_laudo=pendencias_abertas_por_laudo,
        aprendizados_pendentes_por_laudo=aprendizados_pendentes_por_laudo,
        total_aprendizados_pendentes=sum(aprendizados_pendentes_por_laudo.values()),
        total_pendencias_abertas=sum(pendencias_abertas_por_laudo.values()),
        total_whispers_pendentes=len(whispers_pendentes),
        totais_operacao=totais_operacao,
        templates_operacao=resumir_operacao_templates_mesa(
            banco,
            empresa_id=int(usuario.empresa_id),
        ),
    )


__all__ = [
    "ReviewPanelState",
    "build_review_panel_state",
]
