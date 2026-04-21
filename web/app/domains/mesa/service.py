"""Serviços de aplicação do domínio Mesa Avaliadora."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domains.mesa.contracts import (
    AnexoPackItemPacoteMesa,
    AnexoPackPacoteMesa,
    CoverageMapItemPacoteMesa,
    CoverageMapPacoteMesa,
    DocumentoEstruturadoPacoteMesa,
    EmissaoOficialBlockerPacoteMesa,
    EmissaoOficialAtualPacoteMesa,
    EmissaoOficialPacoteMesa,
    EmissaoOficialTrailEventoPacoteMesa,
    EventoMesa,
    HistoricoInspecaoDiffBlocoPacoteMesa,
    HistoricoInspecaoDiffItemPacoteMesa,
    HistoricoInspecaoDiffPacoteMesa,
    HistoricoInspecaoPacoteMesa,
    HistoricoRefazerInspetorItemPacoteMesa,
    MemoriaOperacionalFamiliaPacoteMesa,
    MemoriaOperacionalFrequenciaPacoteMesa,
    MensagemPacoteMesa,
    NotificacaoMesa,
    PacoteMesaLaudo,
    RevisaoPorBlocoItemPacoteMesa,
    RevisaoPorBlocoPacoteMesa,
    ResumoEvidenciasMesa,
    ResumoMensagensMesa,
    ResumoPendenciasMesa,
    RevisaoPacoteMesa,
    SecaoDocumentoEstruturadoPacoteMesa,
    SignatarioGovernadoPacoteMesa,
    VerificacaoPublicaPacoteMesa,
)
from app.domains.mesa.attachments import serializar_anexos_mesa, texto_mensagem_mesa_visivel
from app.domains.mesa.operational_tasks import extract_operational_context
from app.domains.mesa.semantics import build_mesa_message_semantics
from app.domains.chat.laudo_state_helpers import resolver_snapshot_leitura_caso_tecnico
from app.domains.chat.normalization import TIPOS_TEMPLATE_VALIDOS
from app.shared.database import EvidenceValidation, Laudo, LaudoRevisao, MensagemLaudo, OperationalIrregularity, TipoMensagem
from app.shared.inspection_history import (
    build_human_override_summary,
    build_inspection_history_summary,
)
from app.shared.official_issue_package import build_official_issue_package
from app.shared.operational_memory import build_family_operational_memory_summary
from app.shared.public_verification import build_public_verification_payload
from app.shared.tenant_report_catalog import build_tenant_template_option_snapshot
from app.v2.acl.technical_case_core import build_case_status_visual_label
from app.v2.policy.governance import load_case_policy_governance_context
from nucleo.inspetor.referencias_mensagem import extrair_referencia_do_texto

REGEX_ARQUIVO_DOCUMENTO = re.compile(r"\.(?:pdf|docx?)\b", flags=re.IGNORECASE)
SECTION_TITLES = {
    "identificacao": "Identificacao",
    "caracterizacao_do_equipamento": "Caracterizacao",
    "inspecao_visual": "Inspecao visual",
    "dispositivos_e_acessorios": "Dispositivos e acessorios",
    "dispositivos_e_controles": "Dispositivos e controles",
    "documentacao_e_registros": "Documentacao e registros",
    "nao_conformidades": "Nao conformidades",
    "recomendacoes": "Recomendacoes",
    "conclusao": "Conclusao",
}
SECTION_ORDER = (
    "identificacao",
    "caracterizacao_do_equipamento",
    "inspecao_visual",
    "dispositivos_e_acessorios",
    "dispositivos_e_controles",
    "documentacao_e_registros",
    "nao_conformidades",
    "recomendacoes",
    "conclusao",
)
ATTENTION_CONCLUSION_STATUSES = {"ajuste", "reprovado", "nao_conforme", "bloqueado"}
RETURN_TO_INSPECTOR_TYPES = {"field_reopened", "block_returned_to_inspector"}
COVERAGE_STATUS_PRIORITY = {
    "missing": 0,
    "irregular": 1,
    "collected": 2,
    "accepted": 3,
    "pending": 4,
}
BLOCK_REVIEW_STATUS_PRIORITY = {
    "returned": 0,
    "attention": 1,
    "partial": 2,
    "ready": 3,
    "empty": 4,
}


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalizar_data_utc(data: datetime | None) -> datetime | None:
    if data is None:
        return None
    if data.tzinfo is None:
        return data.replace(tzinfo=timezone.utc)
    return data.astimezone(timezone.utc)


def _texto_eh_foto(conteudo: str) -> bool:
    texto = (conteudo or "").strip().lower()
    return texto in {"[imagem]", "imagem enviada", "[foto]"}


def _texto_eh_evidencia_textual(conteudo: str) -> bool:
    texto = (conteudo or "").strip()
    if not texto:
        return False
    if _texto_eh_foto(texto):
        return False
    if _texto_representa_documento(texto):
        return False
    return len(texto) >= 8


def _texto_representa_documento(conteudo: str) -> bool:
    texto = (conteudo or "").strip()
    if not texto:
        return False
    if texto.lower().startswith("documento:"):
        return True
    return bool(REGEX_ARQUIVO_DOCUMENTO.search(texto))


def _texto_limpo_curto(valor: Any) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    return " ".join(texto.split())


def _dict_payload(valor: Any) -> dict[str, Any]:
    return dict(valor) if isinstance(valor, dict) else {}


def _list_payload(valor: Any) -> list[Any]:
    return list(valor) if isinstance(valor, list) else []


def _resumir_texto_curto(valor: Any, *, limite: int = 180) -> str | None:
    texto = _texto_limpo_curto(valor)
    if texto is None:
        return None
    if len(texto) <= limite:
        return texto
    return f"{texto[: max(0, limite - 3)].rstrip()}..."


def _humanizar_slug(valor: Any) -> str:
    texto = str(valor or "").strip().replace("_", " ")
    if not texto:
        return ""
    return " ".join(parte.capitalize() for parte in texto.split())


def _normalizar_lista_textos(valores: Any) -> list[str]:
    if isinstance(valores, str):
        valores_iteraveis = [valores]
    else:
        valores_iteraveis = list(valores or [])
    resultado: list[str] = []
    vistos: set[str] = set()
    for valor in valores_iteraveis:
        texto = _texto_limpo_curto(valor)
        if not texto:
            continue
        chave = texto.lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(texto)
    return resultado


def _build_catalog_template_scope_pacote(
    banco: Session,
    *,
    laudo: Laudo,
) -> dict[str, Any]:
    empresa_id = int(getattr(laudo, "empresa_id", 0) or 0)
    runtime_template_code = (
        _texto_limpo_curto(getattr(laudo, "tipo_template", None)) or "padrao"
    ).lower()
    if empresa_id > 0:
        template_snapshot = build_tenant_template_option_snapshot(
            banco,
            empresa_id=empresa_id,
        )
    else:
        template_snapshot = {
            "governed_mode": False,
            "catalog_state": "legacy_open",
            "permissions": {},
            "options": [],
            "runtime_codes": list(TIPOS_TEMPLATE_VALIDOS.keys()),
            "activation_count": 0,
        }

    runtime_codes = _normalizar_lista_textos(template_snapshot.get("runtime_codes") or [])
    tipos_relatorio = (
        {
            runtime_code.lower(): TIPOS_TEMPLATE_VALIDOS.get(
                runtime_code.lower(),
                runtime_code,
            )
            for runtime_code in runtime_codes
        }
        if bool(template_snapshot.get("governed_mode"))
        else dict(TIPOS_TEMPLATE_VALIDOS)
    )
    governance_context = load_case_policy_governance_context(
        banco,
        tenant_id=empresa_id,
        family_key=getattr(laudo, "catalog_family_key", None),
        variant_key=getattr(laudo, "catalog_variant_key", None),
        template_key=getattr(laudo, "tipo_template", None),
    )
    return {
        "tipos_relatorio": tipos_relatorio,
        "tipo_template_options": list(template_snapshot.get("options") or []),
        "catalog_governed_mode": bool(template_snapshot.get("governed_mode")),
        "catalog_state": str(template_snapshot.get("catalog_state") or "legacy_open"),
        "catalog_permissions": dict(template_snapshot.get("permissions") or {}),
        "activation_count": int(template_snapshot.get("activation_count") or 0),
        "active_binding": {
            "selection_token": _texto_limpo_curto(
                getattr(laudo, "catalog_selection_token", None)
            ),
            "family_key": _texto_limpo_curto(getattr(laudo, "catalog_family_key", None)),
            "family_label": _texto_limpo_curto(
                getattr(laudo, "catalog_family_label", None)
            ),
            "variant_key": _texto_limpo_curto(
                getattr(laudo, "catalog_variant_key", None)
            ),
            "variant_label": _texto_limpo_curto(
                getattr(laudo, "catalog_variant_label", None)
            ),
            "runtime_template_code": runtime_template_code,
            "runtime_template_label": TIPOS_TEMPLATE_VALIDOS.get(
                runtime_template_code,
                runtime_template_code,
            ),
        },
        "family_governance": {
            "family_key": governance_context.get("family_key"),
            "family_label": governance_context.get("family_label"),
            "release_present": bool(governance_context.get("release_present")),
            "release_active": governance_context.get("release_active"),
            "release_status": governance_context.get("release_status"),
            "activation_active": bool(governance_context.get("activation_active")),
            "allowed_templates": list(governance_context.get("allowed_templates") or []),
            "allowed_variants": list(governance_context.get("allowed_variants") or []),
            "default_review_mode": governance_context.get("default_review_mode"),
            "max_review_mode": governance_context.get("max_review_mode"),
            "release_force_review_mode": governance_context.get(
                "release_force_review_mode"
            ),
            "release_max_review_mode": governance_context.get(
                "release_max_review_mode"
            ),
            "release_mobile_review_override": governance_context.get(
                "release_mobile_review_override"
            ),
            "release_mobile_autonomous_override": governance_context.get(
                "release_mobile_autonomous_override"
            ),
        },
    }


def _valor_tem_conteudo(valor: Any) -> bool:
    if valor is None:
        return False
    if isinstance(valor, bool):
        return True
    if isinstance(valor, (int, float)):
        return True
    if isinstance(valor, str):
        return bool(valor.strip())
    if isinstance(valor, dict):
        return any(_valor_tem_conteudo(item) for item in valor.values())
    if isinstance(valor, (list, tuple, set)):
        if not valor:
            return False
        return any(_valor_tem_conteudo(item) for item in valor)
    return True


def _contagem_folhas_preenchidas(valor: Any) -> tuple[int, int]:
    if isinstance(valor, dict):
        preenchidas = 0
        total = 0
        for item in valor.values():
            item_preenchidas, item_total = _contagem_folhas_preenchidas(item)
            preenchidas += item_preenchidas
            total += item_total
        return preenchidas, total
    if isinstance(valor, (list, tuple, set)):
        if not valor:
            return 0, 1
        preenchidas = 0
        total = 0
        for item in valor:
            item_preenchidas, item_total = _contagem_folhas_preenchidas(item)
            preenchidas += item_preenchidas
            total += item_total
        return preenchidas, max(1, total)
    return (1 if _valor_tem_conteudo(valor) else 0, 1)


def _obter_em_caminho(payload: dict[str, Any] | None, *chaves: str) -> Any:
    atual: Any = payload
    for chave in chaves:
        if not isinstance(atual, dict):
            return None
        atual = atual.get(chave)
    return atual


def _rotulo_disponibilidade(flag: Any) -> str | None:
    if flag is True:
        return "disponivel"
    if flag is False:
        return "ausente"
    return None


def _valor_status_conclusao(valor: Any) -> str | None:
    texto = str(valor or "").strip().lower()
    if not texto:
        return None
    return texto


def _rotulo_status_conclusao(valor: Any) -> str | None:
    status = _valor_status_conclusao(valor)
    if not status:
        return None
    rotulos = {
        "ajuste": "Ajuste",
        "aprovado": "Aprovado",
        "conforme": "Conforme",
        "reprovado": "Reprovado",
        "nao_conforme": "Nao conforme",
        "bloqueado": "Bloqueado",
        "pendente": "Pendente",
    }
    return rotulos.get(status, _humanizar_slug(status))


def _primeiro_texto(*valores: Any) -> str | None:
    for valor in valores:
        texto = _resumir_texto_curto(valor)
        if texto:
            return texto
    return None


def _descricao_artefato(payload: dict[str, Any] | None, *, incluir_flag: bool = False) -> str | None:
    if not isinstance(payload, dict):
        return None
    partes: list[str] = []
    if incluir_flag:
        rotulo_disponibilidade = _rotulo_disponibilidade(payload.get("disponivel"))
        if rotulo_disponibilidade:
            partes.append(rotulo_disponibilidade.capitalize())
    for chave in ("descricao", "referencias_texto", "observacao"):
        texto = _resumir_texto_curto(payload.get(chave))
        if texto:
            partes.append(texto)
    if not partes:
        return None
    return " | ".join(partes[:3])


def _sumario_identificacao(secao: dict[str, Any]) -> tuple[str | None, str | None]:
    identificador = None
    for chave, valor in secao.items():
        if chave.startswith("identificacao_"):
            identificador = _resumir_texto_curto(valor)
            if identificador:
                break
    localizacao = _resumir_texto_curto(secao.get("localizacao"))
    tag = _resumir_texto_curto(secao.get("tag_patrimonial"))
    resumo = " | ".join(
        parte
        for parte in (
            identificador,
            localizacao,
            f"tag {tag}" if tag else None,
        )
        if parte
    )
    diff_short = _primeiro_texto(
        _obter_em_caminho(secao, "placa_identificacao", "descricao"),
        _obter_em_caminho(secao, "placa_identificacao", "observacao"),
        _obter_em_caminho(secao, "placa_identificacao", "referencias_texto"),
    )
    return (resumo or None, diff_short)


def _sumario_caracterizacao(secao: dict[str, Any]) -> tuple[str | None, str | None]:
    descricao = _resumir_texto_curto(secao.get("descricao_sumaria"))
    condicao_operacao = _resumir_texto_curto(secao.get("condicao_de_operacao_no_momento"))
    vista = None
    for chave, valor in secao.items():
        if chave.startswith("vista_geral"):
            vista = _descricao_artefato(valor)
            if vista:
                break
    resumo = " | ".join(parte for parte in (descricao, condicao_operacao, vista) if parte)
    return (resumo or None, vista or descricao)


def _sumario_inspecao(secao: dict[str, Any]) -> tuple[str | None, str | None]:
    resumo = " | ".join(
        parte
        for parte in (
            _resumir_texto_curto(secao.get("condicao_geral")),
            _resumir_texto_curto(secao.get("integridade_aparente")),
            _resumir_texto_curto(secao.get("acessibilidade_para_inspecao")),
        )
        if parte
    )
    diff_short = _primeiro_texto(
        _obter_em_caminho(secao, "pontos_de_corrosao", "descricao"),
        _obter_em_caminho(secao, "pontos_de_vazamento_ou_fuligem", "descricao"),
        _obter_em_caminho(secao, "vazamentos", "descricao"),
        _obter_em_caminho(secao, "isolamento_termico", "descricao"),
        _obter_em_caminho(secao, "chamine_ou_exaustao", "descricao"),
    )
    return (resumo or diff_short, diff_short)


def _sumario_dispositivos(secao: dict[str, Any]) -> tuple[str | None, str | None]:
    destaques: list[str] = []
    diff_short = None
    for chave, valor in secao.items():
        if isinstance(valor, dict):
            texto = _descricao_artefato(valor)
            if not texto:
                continue
            rotulo = _humanizar_slug(chave)
            linha = f"{rotulo}: {texto}"
            destaques.append(linha)
            if diff_short is None:
                diff_short = _resumir_texto_curto(linha)
            continue
        texto = _resumir_texto_curto(valor)
        if texto:
            destaques.append(texto)
            if diff_short is None:
                diff_short = texto
    return (" | ".join(destaques[:3]) or None, diff_short)


def _sumario_documentacao(secao: dict[str, Any], mesa_review: dict[str, Any] | None) -> tuple[str | None, str | None]:
    itens: list[str] = []
    for chave in ("prontuario", "certificado", "relatorio_anterior"):
        bloco = secao.get(chave)
        if not isinstance(bloco, dict):
            continue
        rotulo = _humanizar_slug(chave)
        disponibilidade = _rotulo_disponibilidade(bloco.get("disponivel"))
        referencia = _resumir_texto_curto(bloco.get("referencias_texto"))
        if disponibilidade and referencia:
            itens.append(f"{rotulo}: {disponibilidade} ({referencia})")
        elif disponibilidade:
            itens.append(f"{rotulo}: {disponibilidade}")
        elif referencia:
            itens.append(f"{rotulo}: {referencia}")
    resumo = " | ".join(itens[:3]) or _resumir_texto_curto(secao.get("registros_disponiveis_no_local"))
    diff_short = _primeiro_texto(
        _obter_em_caminho(mesa_review, "pendencias_resolvidas_texto"),
        _obter_em_caminho(mesa_review, "observacoes_mesa"),
        _obter_em_caminho(mesa_review, "bloqueios_texto"),
    )
    return (resumo, diff_short)


def _sumario_nao_conformidades(secao: dict[str, Any]) -> tuple[str | None, str | None]:
    if secao.get("ha_nao_conformidades") is False:
        return ("Sem nao conformidades estruturadas.", None)
    resumo = _primeiro_texto(
        secao.get("descricao"),
        secao.get("ha_nao_conformidades_texto"),
    )
    diff_short = _primeiro_texto(
        _obter_em_caminho(secao, "evidencias", "descricao"),
        _obter_em_caminho(secao, "evidencias", "referencias_texto"),
    )
    return (resumo or "Nao conformidades registradas.", diff_short)


def _sumario_recomendacoes(secao: dict[str, Any]) -> tuple[str | None, str | None]:
    texto = _resumir_texto_curto(secao.get("texto"))
    return (texto, texto)


def _sumario_conclusao(secao: dict[str, Any]) -> tuple[str | None, str | None]:
    rotulo_status = _rotulo_status_conclusao(secao.get("status"))
    conclusao_tecnica = _resumir_texto_curto(secao.get("conclusao_tecnica"))
    justificativa = _resumir_texto_curto(secao.get("justificativa"))
    resumo = " | ".join(parte for parte in (rotulo_status, conclusao_tecnica) if parte)
    return (resumo or justificativa, justificativa)


def _sumario_secao_documental(
    key: str,
    secao: dict[str, Any],
    *,
    mesa_review: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    if key == "identificacao":
        return _sumario_identificacao(secao)
    if key == "caracterizacao_do_equipamento":
        return _sumario_caracterizacao(secao)
    if key == "inspecao_visual":
        return _sumario_inspecao(secao)
    if key in {"dispositivos_e_acessorios", "dispositivos_e_controles"}:
        return _sumario_dispositivos(secao)
    if key == "documentacao_e_registros":
        return _sumario_documentacao(secao, mesa_review)
    if key == "nao_conformidades":
        return _sumario_nao_conformidades(secao)
    if key == "recomendacoes":
        return _sumario_recomendacoes(secao)
    if key == "conclusao":
        return _sumario_conclusao(secao)
    return (_resumir_texto_curto(secao), None)


def _status_secao_documental(key: str, secao: dict[str, Any], *, preenchidas: int, total: int) -> str:
    if preenchidas <= 0:
        return "empty"
    if key == "nao_conformidades" and secao.get("ha_nao_conformidades") is True:
        return "attention"
    if key == "conclusao" and _valor_status_conclusao(secao.get("status")) in ATTENTION_CONCLUSION_STATUSES:
        return "attention"
    if total > 0 and preenchidas < max(2, total // 3):
        return "partial"
    return "filled"


def _rotulo_familia_catalogada(laudo: Laudo, family_key: str | None) -> str | None:
    label = _texto_limpo_curto(getattr(laudo, "catalog_family_label", None))
    if label:
        return label
    if family_key:
        return _humanizar_slug(family_key)
    return None


def _montar_documento_estruturado_pacote(laudo: Laudo) -> DocumentoEstruturadoPacoteMesa | None:
    payload = getattr(laudo, "dados_formulario", None)
    if not isinstance(payload, dict):
        return None
    schema_type = _texto_limpo_curto(payload.get("schema_type"))
    if schema_type != "laudo_output":
        return None

    family_key = _texto_limpo_curto(payload.get("family_key") or getattr(laudo, "catalog_family_key", None))
    mesa_review = payload.get("mesa_review") if isinstance(payload.get("mesa_review"), dict) else {}
    sections: list[SecaoDocumentoEstruturadoPacoteMesa] = []

    for key in SECTION_ORDER:
        secao = payload.get(key)
        if not isinstance(secao, dict):
            continue
        preenchidas, total = _contagem_folhas_preenchidas(secao)
        summary, diff_short = _sumario_secao_documental(
            key,
            secao,
            mesa_review=mesa_review,
        )
        sections.append(
            SecaoDocumentoEstruturadoPacoteMesa(
                key=key,
                title=SECTION_TITLES.get(key, _humanizar_slug(key)),
                status=_status_secao_documental(key, secao, preenchidas=preenchidas, total=total),
                summary=summary,
                diff_short=diff_short,
                filled_fields=preenchidas,
                total_fields=total,
            )
        )

    summary = _primeiro_texto(
        payload.get("resumo_executivo"),
        _obter_em_caminho(payload, "conclusao", "conclusao_tecnica"),
        _obter_em_caminho(payload, "conclusao", "justificativa"),
    )
    mesa_review = _dict_payload(mesa_review)
    review_notes = _primeiro_texto(
        mesa_review.get("pendencias_resolvidas_texto"),
        mesa_review.get("observacoes_mesa"),
        mesa_review.get("bloqueios_texto"),
    )

    return DocumentoEstruturadoPacoteMesa(
        schema_type=schema_type,
        family_key=family_key,
        family_label=_rotulo_familia_catalogada(laudo, family_key),
        summary=summary,
        review_notes=review_notes,
        sections=sections,
    )


def _inferir_secao_revisao_por_tokens(
    *,
    available_keys: set[str],
    tokens: list[str],
) -> str | None:
    texto = " ".join(token for token in tokens if token).lower()
    if not texto:
        return None

    for section_key in SECTION_ORDER:
        if section_key in available_keys and section_key in texto:
            return section_key

    if "identificacao" in available_keys and any(
        token in texto for token in ("placa", "identificacao", "tag", "patrimonial", "serial")
    ):
        return "identificacao"

    if "caracterizacao_do_equipamento" in available_keys and any(
        token in texto for token in ("vista_geral", "equipamento", "caracterizacao", "descricao_sumaria", "ativo")
    ):
        return "caracterizacao_do_equipamento"

    if "inspecao_visual" in available_keys and any(
        token in texto
        for token in (
            "inspecao",
            "visual",
            "corros",
            "vazamento",
            "fuligem",
            "isolamento",
            "chamine",
            "exaust",
            "integridade",
            "foto_",
            "imagem",
            "angulo",
        )
    ):
        return "inspecao_visual"

    if "dispositivos_e_controles" in available_keys and any(
        token in texto for token in ("controle", "painel", "intertrav", "chave", "botao")
    ):
        return "dispositivos_e_controles"

    if "dispositivos_e_acessorios" in available_keys and any(
        token in texto
        for token in ("dispositivo", "acessorio", "valvula", "manometro", "pressostato", "sensor", "seguranca")
    ):
        return "dispositivos_e_acessorios"

    if "documentacao_e_registros" in available_keys and any(
        token in texto for token in ("document", "prontuario", "certificado", "registro", "art", "rrt", "pdf")
    ):
        return "documentacao_e_registros"

    if "nao_conformidades" in available_keys and any(
        token in texto for token in ("nao_conform", "desvio", "anomalia", "irregularidade")
    ):
        return "nao_conformidades"

    if "recomendacoes" in available_keys and any(token in texto for token in ("recomend", "acao_corretiva", "prazo")):
        return "recomendacoes"

    if "conclusao" in available_keys and any(token in texto for token in ("conclus", "parecer", "status_final")):
        return "conclusao"

    return None


def _inferir_secao_revisao_item_cobertura(
    item: CoverageMapItemPacoteMesa,
    *,
    available_keys: set[str],
) -> str | None:
    return _inferir_secao_revisao_por_tokens(
        available_keys=available_keys,
        tokens=[
            str(item.evidence_key or ""),
            str(item.title or ""),
            str(item.kind or ""),
            str(item.component_type or ""),
            str(item.view_angle or ""),
            str(item.summary or ""),
            *[str(reason or "") for reason in list(item.failure_reasons or [])],
        ],
    )


def _inferir_secao_revisao_contexto_operacional(
    contexto: dict[str, Any],
    *,
    available_keys: set[str],
) -> str | None:
    return _inferir_secao_revisao_por_tokens(
        available_keys=available_keys,
        tokens=[
            str(contexto.get("block_key") or ""),
            str(contexto.get("evidence_key") or ""),
            str(contexto.get("title") or ""),
            str(contexto.get("kind") or ""),
            str(contexto.get("component_type") or ""),
            str(contexto.get("view_angle") or ""),
            str(contexto.get("summary") or ""),
            str(contexto.get("required_action") or ""),
            *[str(reason or "") for reason in list(contexto.get("failure_reasons") or [])],
        ],
    )


def _inferir_secao_revisao_irregularidade(
    registro: OperationalIrregularity,
    *,
    available_keys: set[str],
) -> str | None:
    detalhes = registro.details_json if isinstance(registro.details_json, dict) else {}
    return _inferir_secao_revisao_por_tokens(
        available_keys=available_keys,
        tokens=[
            str(registro.block_key or ""),
            str(registro.evidence_key or ""),
            str(registro.irregularity_type or ""),
            str(detalhes.get("title") or ""),
            str(detalhes.get("summary") or ""),
            str(detalhes.get("required_action") or ""),
            str(detalhes.get("reason") or ""),
            *[str(reason or "") for reason in list(detalhes.get("failure_reasons") or [])],
        ],
    )


def _status_revisao_bloco(
    *,
    document_status: str,
    coverage_alert_count: int,
    open_return_count: int,
    open_pendency_count: int,
) -> str:
    if open_return_count > 0 or open_pendency_count > 0:
        return "returned"
    if document_status == "attention" or coverage_alert_count > 0:
        return "attention"
    if document_status == "partial":
        return "partial"
    if document_status == "filled":
        return "ready"
    return "empty"


def _build_revisao_por_bloco_pacote(
    banco: Session,
    *,
    laudo_id: int,
    documento: DocumentoEstruturadoPacoteMesa | None,
    coverage_map: CoverageMapPacoteMesa | None,
    mensagens: list[MensagemLaudo],
) -> RevisaoPorBlocoPacoteMesa | None:
    if documento is None or not documento.sections:
        return None

    available_keys = {str(secao.key) for secao in documento.sections}
    por_bloco: dict[str, dict[str, Any]] = {
        str(secao.key): {
            "section": secao,
            "coverage_total": 0,
            "coverage_alert_count": 0,
            "open_return_count": 0,
            "open_pendency_count": 0,
            "latest_return_at": None,
            "recommended_action": None,
        }
        for secao in documento.sections
    }

    if coverage_map is not None:
        for item in coverage_map.items:
            section_key = _inferir_secao_revisao_item_cobertura(item, available_keys=available_keys)
            if not section_key:
                continue
            bloco = por_bloco.get(section_key)
            if bloco is None:
                continue
            bloco["coverage_total"] += 1
            if str(item.status or "").strip().lower() in {"missing", "irregular"}:
                bloco["coverage_alert_count"] += 1
                if bloco["recommended_action"] is None:
                    bloco["recommended_action"] = _primeiro_texto(
                        item.summary,
                        ", ".join(list(item.failure_reasons or [])) if item.failure_reasons else None,
                    )

    for mensagem in mensagens:
        contexto = extract_operational_context(mensagem)
        if contexto is None:
            continue
        section_key = _inferir_secao_revisao_contexto_operacional(contexto, available_keys=available_keys)
        if not section_key:
            continue
        bloco = por_bloco.get(section_key)
        if bloco is None:
            continue
        if not bool(mensagem.lida):
            bloco["open_pendency_count"] += 1
        data_retorno = _normalizar_data_utc(mensagem.criado_em)
        if data_retorno and (bloco["latest_return_at"] is None or data_retorno > bloco["latest_return_at"]):
            bloco["latest_return_at"] = data_retorno
        bloco["recommended_action"] = bloco["recommended_action"] or _primeiro_texto(
            contexto.get("required_action"),
            contexto.get("summary"),
        )

    irregularidades = (
        banco.execute(
            select(OperationalIrregularity)
            .where(
                OperationalIrregularity.laudo_id == int(laudo_id),
                OperationalIrregularity.irregularity_type.in_(tuple(sorted(RETURN_TO_INSPECTOR_TYPES))),
            )
            .order_by(OperationalIrregularity.criado_em.desc(), OperationalIrregularity.id.desc())
        )
        .scalars()
        .all()
    )

    for registro in irregularidades:
        section_key = _inferir_secao_revisao_irregularidade(registro, available_keys=available_keys)
        if not section_key:
            continue
        bloco = por_bloco.get(section_key)
        if bloco is None:
            continue
        if str(registro.status or "").strip().lower() == "open":
            bloco["open_return_count"] += 1
        data_retorno = _normalizar_data_utc(registro.criado_em)
        if data_retorno and (bloco["latest_return_at"] is None or data_retorno > bloco["latest_return_at"]):
            bloco["latest_return_at"] = data_retorno
        bloco["recommended_action"] = bloco["recommended_action"] or _primeiro_texto(
            _resumo_irregularidade_operacional(registro),
            registro.resolution_notes,
        )

    items: list[RevisaoPorBlocoItemPacoteMesa] = []
    ready_blocks = 0
    attention_blocks = 0
    returned_blocks = 0

    for secao in documento.sections:
        bloco = por_bloco[str(secao.key)]
        review_status = _status_revisao_bloco(
            document_status=str(secao.status or ""),
            coverage_alert_count=int(bloco["coverage_alert_count"]),
            open_return_count=int(bloco["open_return_count"]),
            open_pendency_count=int(bloco["open_pendency_count"]),
        )
        if review_status == "returned":
            returned_blocks += 1
        elif review_status == "attention":
            attention_blocks += 1
        elif review_status == "ready":
            ready_blocks += 1

        items.append(
            RevisaoPorBlocoItemPacoteMesa(
                block_key=str(secao.key),
                title=str(secao.title),
                document_status=str(secao.status),
                review_status=review_status,
                summary=secao.summary,
                diff_short=secao.diff_short,
                filled_fields=int(secao.filled_fields),
                total_fields=int(secao.total_fields),
                coverage_total=int(bloco["coverage_total"]),
                coverage_alert_count=int(bloco["coverage_alert_count"]),
                open_return_count=int(bloco["open_return_count"]),
                open_pendency_count=int(bloco["open_pendency_count"]),
                latest_return_at=bloco["latest_return_at"],
                recommended_action=_resumir_texto_curto(bloco["recommended_action"], limite=280),
            )
        )

    items.sort(
        key=lambda item: (
            BLOCK_REVIEW_STATUS_PRIORITY.get(str(item.review_status), 99),
            SECTION_ORDER.index(item.block_key) if item.block_key in SECTION_ORDER else 99,
            item.title.lower(),
        )
    )

    return RevisaoPorBlocoPacoteMesa(
        total_blocks=len(items),
        ready_blocks=ready_blocks,
        attention_blocks=attention_blocks,
        returned_blocks=returned_blocks,
        items=items,
    )


def _nome_resolvedor_pacote(msg: MensagemLaudo) -> str:
    if not getattr(msg, "resolvida_por_id", None):
        return ""

    resolvedor = getattr(msg, "resolvida_por", None)
    if resolvedor is not None:
        return getattr(resolvedor, "nome", None) or getattr(resolvedor, "nome_completo", None) or f"Usuario #{msg.resolvida_por_id}"

    return f"Usuario #{msg.resolvida_por_id}"


def _serializar_mensagem_pacote(msg: MensagemLaudo) -> MensagemPacoteMesa:
    referencia_mensagem_id, texto_limpo = extrair_referencia_do_texto(msg.conteudo)
    anexos_payload = serializar_anexos_mesa(getattr(msg, "anexos_mesa", None))
    semantics = build_mesa_message_semantics(
        legacy_message_type=msg.tipo,
        resolved_at=msg.resolvida_em,
        is_whisper=bool(getattr(msg, "is_whisper", False)),
    )
    return MensagemPacoteMesa(
        id=int(msg.id),
        tipo=str(msg.tipo or ""),
        item_kind=semantics.item_kind,
        message_kind=semantics.message_kind,
        pendency_state=semantics.pendency_state,
        texto=texto_mensagem_mesa_visivel(texto_limpo, anexos=getattr(msg, "anexos_mesa", None)),
        criado_em=_normalizar_data_utc(msg.criado_em) or agora_utc(),
        remetente_id=int(msg.remetente_id) if msg.remetente_id else None,
        lida=bool(msg.lida),
        referencia_mensagem_id=referencia_mensagem_id,
        resolvida_em=_normalizar_data_utc(msg.resolvida_em),
        resolvida_por_id=int(msg.resolvida_por_id) if msg.resolvida_por_id else None,
        resolvida_por_nome=_nome_resolvedor_pacote(msg) or None,
        anexos=anexos_payload,
    )


def _tempo_em_campo_minutos(inicio: datetime | None) -> int:
    inicio_utc = _normalizar_data_utc(inicio)
    if inicio_utc is None:
        return 0
    delta = agora_utc() - inicio_utc
    if delta.total_seconds() < 0:
        return 0
    return int(delta.total_seconds() // 60)


def criar_notificacao(
    *,
    evento: EventoMesa,
    laudo_id: int,
    origem: str,
    resumo: str,
) -> NotificacaoMesa:
    return NotificacaoMesa(
        evento=evento,
        laudo_id=laudo_id,
        origem=origem,
        resumo=resumo,
    )


def _coverage_item_base(
    *,
    evidence_key: str,
    title: str,
    kind: str,
    required: bool,
    source_status: str | None = None,
    summary: str | None = None,
    failure_reasons: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "evidence_key": evidence_key,
        "title": title,
        "kind": kind,
        "required": required,
        "source_status": source_status,
        "summary": summary,
        "failure_reasons": list(failure_reasons or []),
        "operational_status": None,
        "mesa_status": None,
        "component_type": None,
        "view_angle": None,
        "quality_score": None,
        "coherence_score": None,
        "replacement_evidence_key": None,
        "status": "pending",
    }


def _coverage_item_title_from_evidence_key(evidence_key: str) -> str:
    if evidence_key.startswith("slot:"):
        return _humanizar_slug(evidence_key.split(":", 1)[1])
    if evidence_key.startswith("gate:"):
        parts = evidence_key.split(":", 2)
        if len(parts) >= 3:
            return _humanizar_slug(parts[2])
    return _humanizar_slug(evidence_key)


def _coverage_item_status(item: dict[str, Any]) -> tuple[str, bool]:
    source_status = str(item.get("source_status") or "").strip().lower()
    operational_status = str(item.get("operational_status") or "").strip().lower()
    mesa_status = str(item.get("mesa_status") or "").strip().lower()
    required = bool(item.get("required"))
    failure_reasons = list(item.get("failure_reasons") or [])
    collected = (
        source_status == "resolved"
        or bool(item.get("replacement_evidence_key"))
        or operational_status in {"ok", "irregular", "replaced"}
        or item.get("quality_score") is not None
        or item.get("coherence_score") is not None
    )

    if operational_status == "ok" or mesa_status == "accepted":
        return "accepted", collected
    if operational_status == "irregular":
        return "irregular", collected
    if required and (source_status in {"missing", "pending"} or (failure_reasons and not collected) or not collected):
        return "missing", collected
    if collected:
        return "collected", True
    return "pending", False


def _build_coverage_map_pacote(
    banco: Session,
    *,
    laudo: Laudo,
) -> CoverageMapPacoteMesa | None:
    report_pack = getattr(laudo, "report_pack_draft_json", None)
    draft = report_pack if isinstance(report_pack, dict) else {}
    quality_gates = _dict_payload(draft.get("quality_gates"))
    final_validation_mode = _texto_limpo_curto(quality_gates.get("final_validation_mode"))
    validations = (
        banco.execute(
            select(EvidenceValidation)
            .where(EvidenceValidation.laudo_id == int(laudo.id))
            .order_by(EvidenceValidation.id.asc())
        )
        .scalars()
        .all()
    )

    items_by_key: dict[str, dict[str, Any]] = {}
    for slot in list(draft.get("image_slots") or []):
        if not isinstance(slot, dict):
            continue
        slot_code = _texto_limpo_curto(slot.get("slot"))
        if not slot_code:
            continue
        evidence_key = f"slot:{slot_code}"
        items_by_key[evidence_key] = _coverage_item_base(
            evidence_key=evidence_key,
            title=_texto_limpo_curto(slot.get("title")) or _humanizar_slug(slot_code),
            kind="image_slot",
            required=bool(slot.get("required")),
            source_status=_texto_limpo_curto(slot.get("status")),
            summary=_resumir_texto_curto(slot.get("resolved_caption")),
            failure_reasons=_normalizar_lista_textos(slot.get("missing_evidence")),
        )

    for index, item in enumerate(_list_payload(quality_gates.get("missing_evidence")), start=1):
        if not isinstance(item, dict):
            continue
        kind = _texto_limpo_curto(item.get("kind")) or "gate"
        code = _texto_limpo_curto(item.get("code")) or f"missing_{index}"
        evidence_key = f"gate:{kind}:{code}"
        items_by_key.setdefault(
            evidence_key,
            _coverage_item_base(
                evidence_key=evidence_key,
                title=_resumir_texto_curto(item.get("message"), limite=180) or _humanizar_slug(code),
                kind=kind,
                required=True,
                source_status="missing",
                summary=_resumir_texto_curto(item.get("message"), limite=280),
                failure_reasons=_normalizar_lista_textos([item.get("code")]),
            ),
        )

    for validation in validations:
        validation_evidence_key = _texto_limpo_curto(validation.evidence_key)
        if not validation_evidence_key or not (
            validation_evidence_key.startswith("slot:")
            or validation_evidence_key.startswith("gate:")
        ):
            continue
        base = items_by_key.get(validation_evidence_key)
        if base is None:
            base = _coverage_item_base(
                evidence_key=validation_evidence_key,
                title=_coverage_item_title_from_evidence_key(validation_evidence_key),
                kind=(
                    "image_slot"
                    if validation_evidence_key.startswith("slot:")
                    else "gate_requirement"
                ),
                required=validation_evidence_key.startswith("gate:"),
            )
            items_by_key[validation_evidence_key] = base

        failure_reasons = _normalizar_lista_textos(
            [*(base.get("failure_reasons") or []), *(validation.failure_reasons_json or [])]
        )
        evidence_metadata = validation.evidence_metadata_json if isinstance(validation.evidence_metadata_json, dict) else {}
        base.update(
            {
                "operational_status": _texto_limpo_curto(validation.operational_status),
                "mesa_status": _texto_limpo_curto(validation.mesa_status),
                "component_type": _texto_limpo_curto(validation.component_type),
                "view_angle": _texto_limpo_curto(validation.view_angle),
                "quality_score": validation.quality_score,
                "coherence_score": validation.coherence_score,
                "replacement_evidence_key": _texto_limpo_curto(validation.replacement_evidence_key),
                "summary": base.get("summary")
                or _resumir_texto_curto(
                    evidence_metadata.get("message") or evidence_metadata.get("reason") or evidence_metadata.get("title"),
                    limite=280,
                ),
                "failure_reasons": failure_reasons,
            }
        )
        if not base.get("source_status") and validation_evidence_key.startswith("gate:"):
            base["source_status"] = "resolved" if str(validation.operational_status or "").strip().lower() == "ok" else "pending"

    if not items_by_key and not final_validation_mode:
        return None

    total_required = 0
    total_collected = 0
    total_accepted = 0
    total_missing = 0
    total_irregular = 0
    items_payload: list[CoverageMapItemPacoteMesa] = []

    for item in items_by_key.values():
        status, collected = _coverage_item_status(item)
        item["status"] = status
        if item.get("required"):
            total_required += 1
        if collected:
            total_collected += 1
        if status == "accepted":
            total_accepted += 1
        elif status == "missing":
            total_missing += 1
        elif status == "irregular":
            total_irregular += 1
        items_payload.append(
            CoverageMapItemPacoteMesa(
                evidence_key=str(item["evidence_key"]),
                title=str(item["title"]),
                kind=str(item["kind"]),
                status=status,
                required=bool(item.get("required")),
                source_status=_texto_limpo_curto(item.get("source_status")),
                operational_status=_texto_limpo_curto(item.get("operational_status")),
                mesa_status=_texto_limpo_curto(item.get("mesa_status")),
                component_type=_texto_limpo_curto(item.get("component_type")),
                view_angle=_texto_limpo_curto(item.get("view_angle")),
                quality_score=item.get("quality_score"),
                coherence_score=item.get("coherence_score"),
                replacement_evidence_key=_texto_limpo_curto(item.get("replacement_evidence_key")),
                summary=_resumir_texto_curto(item.get("summary"), limite=280),
                failure_reasons=_normalizar_lista_textos(item.get("failure_reasons")),
            )
        )

    items_payload.sort(
        key=lambda item: (
            COVERAGE_STATUS_PRIORITY.get(str(item.status), 99),
            0 if item.required else 1,
            item.title.lower(),
        )
    )

    return CoverageMapPacoteMesa(
        total_required=total_required,
        total_collected=total_collected,
        total_accepted=total_accepted,
        total_missing=total_missing,
        total_irregular=total_irregular,
        final_validation_mode=final_validation_mode,
        items=items_payload,
    )


def _resumo_irregularidade_operacional(registro: OperationalIrregularity) -> str | None:
    detalhes = registro.details_json if isinstance(registro.details_json, dict) else {}
    return _primeiro_texto(
        detalhes.get("required_action"),
        detalhes.get("message"),
        detalhes.get("reason"),
        detalhes.get("motivo"),
        detalhes.get("summary"),
        _humanizar_slug(registro.block_key) if registro.block_key else None,
    )


def _nome_usuario_relacionado(usuario: Any, fallback_id: int | None) -> str | None:
    if usuario is not None:
        return _texto_limpo_curto(getattr(usuario, "nome", None) or getattr(usuario, "nome_completo", None))
    if fallback_id:
        return f"Usuario #{fallback_id}"
    return None


def _build_historico_refazer_inspetor_pacote(
    banco: Session,
    *,
    laudo_id: int,
    limite: int = 10,
) -> list[HistoricoRefazerInspetorItemPacoteMesa]:
    registros = (
        banco.execute(
            select(OperationalIrregularity)
            .options(
                selectinload(OperationalIrregularity.detected_by_user),
                selectinload(OperationalIrregularity.resolved_by),
            )
            .where(
                OperationalIrregularity.laudo_id == int(laudo_id),
                OperationalIrregularity.irregularity_type.in_(tuple(sorted(RETURN_TO_INSPECTOR_TYPES))),
            )
            .order_by(OperationalIrregularity.criado_em.desc(), OperationalIrregularity.id.desc())
            .limit(max(1, limite))
        )
        .scalars()
        .all()
    )
    return [
        HistoricoRefazerInspetorItemPacoteMesa(
            id=int(registro.id),
            irregularity_type=str(registro.irregularity_type or ""),
            severity=str(registro.severity or ""),
            status=str(registro.status or ""),
            detected_by=str(registro.detected_by or ""),
            block_key=_texto_limpo_curto(registro.block_key),
            evidence_key=_texto_limpo_curto(registro.evidence_key),
            summary=_resumir_texto_curto(_resumo_irregularidade_operacional(registro), limite=280),
            resolution_notes=_resumir_texto_curto(registro.resolution_notes, limite=400),
            resolution_mode=_texto_limpo_curto(registro.resolution_mode),
            detected_at=_normalizar_data_utc(registro.criado_em) or agora_utc(),
            resolved_at=_normalizar_data_utc(registro.resolved_at),
            detected_by_user_name=_nome_usuario_relacionado(registro.detected_by_user, registro.detected_by_user_id),
            resolved_by_user_name=_nome_usuario_relacionado(registro.resolved_by, registro.resolved_by_id),
        )
        for registro in registros
    ]


def _build_memoria_operacional_familia_pacote(
    banco: Session,
    *,
    laudo: Laudo,
) -> MemoriaOperacionalFamiliaPacoteMesa | None:
    family_key = _texto_limpo_curto(getattr(laudo, "catalog_family_key", None) or getattr(laudo, "tipo_template", None))
    if not family_key:
        return None

    resumo = build_family_operational_memory_summary(
        banco,
        empresa_id=int(laudo.empresa_id),
        family_key=family_key,
    )
    return MemoriaOperacionalFamiliaPacoteMesa(
        family_key=resumo.family_key,
        approved_snapshot_count=resumo.approved_snapshot_count,
        operational_event_count=resumo.operational_event_count,
        validated_evidence_count=resumo.validated_evidence_count,
        open_irregularity_count=resumo.open_irregularity_count,
        latest_approved_at=resumo.latest_approved_at,
        latest_event_at=resumo.latest_event_at,
        top_event_types=[
            MemoriaOperacionalFrequenciaPacoteMesa(item_key=item.item_key, count=item.count)
            for item in resumo.top_event_types
        ],
        top_open_irregularities=[
            MemoriaOperacionalFrequenciaPacoteMesa(item_key=item.item_key, count=item.count)
            for item in resumo.top_open_irregularities
        ],
    )


def _build_historico_inspecao_pacote(
    banco: Session,
    *,
    laudo: Laudo,
) -> HistoricoInspecaoPacoteMesa | None:
    historico = build_inspection_history_summary(
        banco,
        laudo=laudo,
    )
    if not isinstance(historico, dict):
        return None

    diff_payload = _dict_payload(historico.get("diff"))
    highlights = []
    identity_highlights = []
    block_highlights = []
    for item in _list_payload(diff_payload.get("highlights")):
        if not isinstance(item, dict):
            continue
        path = _texto_limpo_curto(item.get("path"),)  # type: ignore[misc]
        label = _texto_limpo_curto(item.get("label"),)  # type: ignore[misc]
        change_type = _texto_limpo_curto(item.get("change_type"),)  # type: ignore[misc]
        if not path or not label or not change_type:
            continue
        highlights.append(
            HistoricoInspecaoDiffItemPacoteMesa(
                path=path[:240],
                label=label[:240],
                change_type=change_type[:24],
                previous_value=_resumir_texto_curto(item.get("previous_value"), limite=120),
                current_value=_resumir_texto_curto(item.get("current_value"), limite=120),
            )
        )
    for item in _list_payload(diff_payload.get("identity_highlights")):
        if not isinstance(item, dict):
            continue
        path = _texto_limpo_curto(item.get("path"))  # type: ignore[misc]
        label = _texto_limpo_curto(item.get("label"))  # type: ignore[misc]
        change_type = _texto_limpo_curto(item.get("change_type"))  # type: ignore[misc]
        if not path or not label or not change_type:
            continue
        identity_highlights.append(
            HistoricoInspecaoDiffItemPacoteMesa(
                path=path[:240],
                label=label[:240],
                change_type=change_type[:24],
                previous_value=_resumir_texto_curto(item.get("previous_value"), limite=120),
                current_value=_resumir_texto_curto(item.get("current_value"), limite=120),
            )
        )
    for item in _list_payload(diff_payload.get("block_highlights")):
        if not isinstance(item, dict):
            continue
        block_key = _texto_limpo_curto(item.get("block_key"))
        title = _texto_limpo_curto(item.get("title"))
        if not block_key or not title:
            continue
        fields = []
        for field in list(item.get("fields") or []):
            if not isinstance(field, dict):
                continue
            path = _texto_limpo_curto(field.get("path"))  # type: ignore[misc]
            label = _texto_limpo_curto(field.get("label"))  # type: ignore[misc]
            change_type = _texto_limpo_curto(field.get("change_type"))  # type: ignore[misc]
            if not path or not label or not change_type:
                continue
            fields.append(
                HistoricoInspecaoDiffItemPacoteMesa(
                    path=path[:240],
                    label=label[:240],
                    change_type=change_type[:24],
                    previous_value=_resumir_texto_curto(field.get("previous_value"), limite=120),
                    current_value=_resumir_texto_curto(field.get("current_value"), limite=120),
                )
            )
        block_highlights.append(
            HistoricoInspecaoDiffBlocoPacoteMesa(
                block_key=block_key[:120],
                title=title[:160],
                changed_count=int(item.get("changed_count") or 0),
                added_count=int(item.get("added_count") or 0),
                removed_count=int(item.get("removed_count") or 0),
                total_changes=int(item.get("total_changes") or 0),
                identity_change_count=int(item.get("identity_change_count") or 0),
                summary=_resumir_texto_curto(item.get("summary"), limite=240),
                fields=fields,
            )
        )

    snapshot_id = int(historico.get("snapshot_id") or 0)
    source_laudo_id = int(historico.get("source_laudo_id") or 0)
    if snapshot_id <= 0 or source_laudo_id <= 0:
        return None

    return HistoricoInspecaoPacoteMesa(
        snapshot_id=snapshot_id,
        source_laudo_id=source_laudo_id,
        source_codigo_hash=_texto_limpo_curto(historico.get("source_codigo_hash")),
        approved_at=_normalizar_data_utc(historico.get("approved_at")),
        approval_version=int(historico.get("approval_version") or 0) or None,
        document_outcome=_resumir_texto_curto(historico.get("document_outcome"), limite=80),
        matched_by=_resumir_texto_curto(historico.get("matched_by"), limite=40),
        match_score=int(historico.get("match_score") or 0),
        prefilled_field_count=int(historico.get("prefilled_field_count") or 0),
        diff=HistoricoInspecaoDiffPacoteMesa(
            changed_count=int(diff_payload.get("changed_count") or 0),
            added_count=int(diff_payload.get("added_count") or 0),
            removed_count=int(diff_payload.get("removed_count") or 0),
            total_changes=int(diff_payload.get("total_changes") or 0),
            identity_change_count=int(diff_payload.get("identity_change_count") or 0),
            current_fields_count=int(diff_payload.get("current_fields_count") or 0),
            reference_fields_count=int(diff_payload.get("reference_fields_count") or 0),
            summary=_resumir_texto_curto(diff_payload.get("summary"), limite=240),
            highlights=highlights,
            identity_highlights=identity_highlights,
            block_highlights=block_highlights,
        ),
    )


def _build_verificacao_publica_pacote(
    laudo: Laudo,
    *,
    case_snapshot: Any | None = None,
) -> VerificacaoPublicaPacoteMesa:
    payload = build_public_verification_payload(laudo=laudo)
    status_visual_label = build_case_status_visual_label(
        lifecycle_status=getattr(case_snapshot, "case_lifecycle_status", None),
        active_owner_role=getattr(case_snapshot, "active_owner_role", None),
    )
    return VerificacaoPublicaPacoteMesa(
        codigo_hash=str(payload.get("codigo_hash") or ""),
        hash_short=str(payload.get("hash_short") or ""),
        verification_url=str(payload.get("verification_url") or ""),
        qr_payload=str(payload.get("qr_payload") or ""),
        qr_image_data_uri=_resumir_texto_curto(payload.get("qr_image_data_uri"), limite=12000),
        empresa_nome=_resumir_texto_curto(payload.get("empresa_nome"), limite=160),
        status_revisao=_resumir_texto_curto(payload.get("status_revisao"), limite=40),
        status_visual_label=_resumir_texto_curto(status_visual_label, limite=120),
        status_conformidade=_resumir_texto_curto(payload.get("status_conformidade"), limite=40),
        approved_at=_normalizar_data_utc(payload.get("approved_at")),
        approval_version=int(payload.get("approval_version") or 0) or None,
        document_outcome=_resumir_texto_curto(payload.get("document_outcome"), limite=80),
    )


def _build_anexo_pack_pacote(payload: dict[str, Any] | None) -> AnexoPackPacoteMesa | None:
    if not isinstance(payload, dict):
        return None
    items = []
    for item in list(payload.get("items") or []):
        if not isinstance(item, dict):
            continue
        item_key = _texto_limpo_curto(item.get("item_key"))
        label = _texto_limpo_curto(item.get("label"))
        category = _texto_limpo_curto(item.get("category"))
        source = _texto_limpo_curto(item.get("source"))
        if not item_key or not label or not category or not source:
            continue
        items.append(
            AnexoPackItemPacoteMesa(
                item_key=item_key[:160],
                label=label[:180],
                category=category[:40],
                required=bool(item.get("required")),
                present=bool(item.get("present")),
                source=source[:40],
                summary=_resumir_texto_curto(item.get("summary"), limite=280),
                mime_type=_resumir_texto_curto(item.get("mime_type"), limite=120),
                size_bytes=int(item.get("size_bytes") or 0) if item.get("size_bytes") is not None else None,
                file_name=_resumir_texto_curto(item.get("file_name"), limite=220),
                archive_path=_resumir_texto_curto(item.get("archive_path"), limite=260),
            )
        )
    return AnexoPackPacoteMesa(
        total_items=int(payload.get("total_items") or 0),
        total_required=int(payload.get("total_required") or 0),
        total_present=int(payload.get("total_present") or 0),
        missing_required_count=int(payload.get("missing_required_count") or 0),
        document_count=int(payload.get("document_count") or 0),
        image_count=int(payload.get("image_count") or 0),
        virtual_count=int(payload.get("virtual_count") or 0),
        ready_for_issue=bool(payload.get("ready_for_issue")),
        missing_items=_normalizar_lista_textos(payload.get("missing_items")),
        items=items,
    )


def _build_emissao_oficial_pacote(payload: dict[str, Any] | None) -> EmissaoOficialPacoteMesa | None:
    if not isinstance(payload, dict):
        return None
    signatories = []
    for item in list(payload.get("signatories") or []):
        if not isinstance(item, dict):
            continue
        signatory_id = int(item.get("id") or 0)
        nome = _texto_limpo_curto(item.get("nome"))
        funcao = _texto_limpo_curto(item.get("funcao"))
        status = _texto_limpo_curto(item.get("status"))
        status_label = _texto_limpo_curto(item.get("status_label"))
        if signatory_id <= 0 or not nome or not funcao or not status or not status_label:
            continue
        signatories.append(
            SignatarioGovernadoPacoteMesa(
                id=signatory_id,
                nome=nome[:160],
                funcao=funcao[:120],
                registro_profissional=_resumir_texto_curto(item.get("registro_profissional"), limite=80),
                valid_until=_normalizar_data_utc(item.get("valid_until")),
                status=status[:24],
                status_label=status_label[:80],
                ativo=bool(item.get("ativo")),
                allowed_family_keys=_normalizar_lista_textos(item.get("allowed_family_keys")),
                observacoes=_resumir_texto_curto(item.get("observacoes"), limite=280),
            )
        )
    blockers = []
    audit_trail = []
    for item in list(payload.get("blockers") or []):
        if not isinstance(item, dict):
            continue
        code = _texto_limpo_curto(item.get("code"))
        title = _texto_limpo_curto(item.get("title"))
        message = _texto_limpo_curto(item.get("message"))
        if not code or not title or not message:
            continue
        blockers.append(
            EmissaoOficialBlockerPacoteMesa(
                code=code[:64],
                title=title[:120],
                message=message[:280],
                blocking=bool(item.get("blocking", True)),
            )
        )
    for item in list(payload.get("audit_trail") or []):
        if not isinstance(item, dict):
            continue
        event_key = _texto_limpo_curto(item.get("event_key"))
        title = _texto_limpo_curto(item.get("title"))
        status = _texto_limpo_curto(item.get("status"))
        status_label = _texto_limpo_curto(item.get("status_label"))
        if not event_key or not title or not status or not status_label:
            continue
        audit_trail.append(
            EmissaoOficialTrailEventoPacoteMesa(
                event_key=event_key[:64],
                title=title[:120],
                status=status[:24],
                status_label=status_label[:80],
                summary=_resumir_texto_curto(item.get("summary"), limite=280),
                blocking=bool(item.get("blocking")),
                recorded_at=_normalizar_data_utc(item.get("recorded_at")),
            )
        )
    issue_status = _texto_limpo_curto(payload.get("issue_status"))
    issue_status_label = _texto_limpo_curto(payload.get("issue_status_label"))
    if not issue_status or not issue_status_label:
        return None
    current_issue_payload = payload.get("current_issue")
    current_issue = None
    if isinstance(current_issue_payload, dict):
        current_issue_id = int(current_issue_payload.get("id") or 0)
        current_issue_state = _texto_limpo_curto(current_issue_payload.get("issue_state"))
        current_issue_state_label = _texto_limpo_curto(current_issue_payload.get("issue_state_label"))
        if current_issue_id > 0 and current_issue_state and current_issue_state_label:
            current_issue = EmissaoOficialAtualPacoteMesa(
                id=current_issue_id,
                issue_number=_resumir_texto_curto(current_issue_payload.get("issue_number"), limite=80),
                issue_state=current_issue_state[:24],
                issue_state_label=current_issue_state_label[:80],
                issued_at=_normalizar_data_utc(current_issue_payload.get("issued_at")),
                superseded_at=_normalizar_data_utc(current_issue_payload.get("superseded_at")),
                package_sha256=_resumir_texto_curto(current_issue_payload.get("package_sha256"), limite=64),
                package_filename=_resumir_texto_curto(current_issue_payload.get("package_filename"), limite=220),
                package_storage_ready=bool(current_issue_payload.get("package_storage_ready")),
                package_size_bytes=(
                    int(current_issue_payload.get("package_size_bytes") or 0)
                    if current_issue_payload.get("package_size_bytes") is not None
                    else None
                ),
                verification_hash=_resumir_texto_curto(current_issue_payload.get("verification_hash"), limite=64),
                verification_url=_resumir_texto_curto(current_issue_payload.get("verification_url"), limite=400),
                approval_snapshot_id=(
                    int(current_issue_payload.get("approval_snapshot_id") or 0)
                    if current_issue_payload.get("approval_snapshot_id") is not None
                    else None
                ),
                approval_version=(
                    int(current_issue_payload.get("approval_version") or 0)
                    if current_issue_payload.get("approval_version") is not None
                    else None
                ),
                signatory_name=_resumir_texto_curto(current_issue_payload.get("signatory_name"), limite=160),
                signatory_function=_resumir_texto_curto(current_issue_payload.get("signatory_function"), limite=120),
                signatory_registration=_resumir_texto_curto(current_issue_payload.get("signatory_registration"), limite=80),
                issued_by_name=_resumir_texto_curto(current_issue_payload.get("issued_by_name"), limite=160),
                primary_pdf_sha256=_resumir_texto_curto(current_issue_payload.get("primary_pdf_sha256"), limite=64),
                primary_pdf_storage_version=_resumir_texto_curto(
                    current_issue_payload.get("primary_pdf_storage_version"),
                    limite=32,
                ),
                primary_pdf_storage_version_number=(
                    int(current_issue_payload.get("primary_pdf_storage_version_number") or 0)
                    if current_issue_payload.get("primary_pdf_storage_version_number") is not None
                    else None
                ),
                current_primary_pdf_sha256=_resumir_texto_curto(
                    current_issue_payload.get("current_primary_pdf_sha256"),
                    limite=64,
                ),
                current_primary_pdf_storage_version=_resumir_texto_curto(
                    current_issue_payload.get("current_primary_pdf_storage_version"),
                    limite=32,
                ),
                current_primary_pdf_storage_version_number=(
                    int(current_issue_payload.get("current_primary_pdf_storage_version_number") or 0)
                    if current_issue_payload.get("current_primary_pdf_storage_version_number") is not None
                    else None
                ),
                primary_pdf_diverged=bool(current_issue_payload.get("primary_pdf_diverged")),
                primary_pdf_comparison_status=_resumir_texto_curto(
                    current_issue_payload.get("primary_pdf_comparison_status"),
                    limite=32,
                ),
                reissue_of_issue_id=(
                    int(current_issue_payload.get("reissue_of_issue_id") or 0)
                    if current_issue_payload.get("reissue_of_issue_id") is not None
                    else None
                ),
                reissue_of_issue_number=_resumir_texto_curto(
                    current_issue_payload.get("reissue_of_issue_number"),
                    limite=80,
                ),
                reissue_reason_codes=_normalizar_lista_textos(current_issue_payload.get("reissue_reason_codes")),
                reissue_reason_summary=_resumir_texto_curto(
                    current_issue_payload.get("reissue_reason_summary"),
                    limite=280,
                ),
                superseded_by_issue_id=(
                    int(current_issue_payload.get("superseded_by_issue_id") or 0)
                    if current_issue_payload.get("superseded_by_issue_id") is not None
                    else None
                ),
                superseded_by_issue_number=_resumir_texto_curto(
                    current_issue_payload.get("superseded_by_issue_number"),
                    limite=80,
                ),
            )
    return EmissaoOficialPacoteMesa(
        issue_status=issue_status[:32],
        issue_status_label=issue_status_label[:120],
        ready_for_issue=bool(payload.get("ready_for_issue")),
        requires_human_signature=bool(payload.get("requires_human_signature", True)),
        compatible_signatory_count=int(payload.get("compatible_signatory_count") or 0),
        eligible_signatory_count=int(payload.get("eligible_signatory_count") or 0),
        blocker_count=int(payload.get("blocker_count") or 0),
        signature_status=_resumir_texto_curto(payload.get("signature_status"), limite=32),
        signature_status_label=_resumir_texto_curto(payload.get("signature_status_label"), limite=120),
        verification_url=_resumir_texto_curto(payload.get("verification_url"), limite=400),
        pdf_present=bool(payload.get("pdf_present")),
        public_verification_present=bool(payload.get("public_verification_present")),
        signatories=signatories,
        blockers=blockers,
        audit_trail=audit_trail,
        already_issued=bool(payload.get("already_issued")),
        reissue_recommended=bool(payload.get("reissue_recommended")),
        issue_action_label=_resumir_texto_curto(payload.get("issue_action_label"), limite=120),
        issue_action_enabled=bool(payload.get("issue_action_enabled")),
        current_issue=current_issue,
    )


def montar_pacote_mesa_laudo(
    banco: Session,
    *,
    laudo: Laudo,
    limite_whispers: int = 80,
    limite_pendencias: int = 80,
    limite_revisoes: int = 10,
) -> PacoteMesaLaudo:
    limite_whispers_seguro = max(10, min(int(limite_whispers), 400))
    limite_pendencias_seguro = max(10, min(int(limite_pendencias), 400))
    limite_revisoes_seguro = max(1, min(int(limite_revisoes), 80))

    mensagens = (
        banco.query(MensagemLaudo)
        .options(selectinload(MensagemLaudo.anexos_mesa))
        .filter(MensagemLaudo.laudo_id == laudo.id)
        .order_by(MensagemLaudo.id.asc())
        .all()
    )

    total_inspetor = 0
    total_ia = 0
    total_mesa = 0
    total_outros = 0
    evidencias_textuais = 0
    evidencias_fotos = 0
    evidencias_documentos = 0

    for msg in mensagens:
        tipo = str(msg.tipo or "")
        _, texto_limpo = extrair_referencia_do_texto(msg.conteudo)

        if tipo in {TipoMensagem.USER.value, TipoMensagem.HUMANO_INSP.value}:
            total_inspetor += 1
            if tipo != TipoMensagem.USER.value:
                continue
            if _texto_eh_foto(texto_limpo):
                evidencias_fotos += 1
            elif _texto_representa_documento(texto_limpo):
                evidencias_documentos += 1
            elif _texto_eh_evidencia_textual(texto_limpo):
                evidencias_textuais += 1
            continue

        if tipo == TipoMensagem.IA.value:
            total_ia += 1
            continue

        if tipo == TipoMensagem.HUMANO_ENG.value:
            total_mesa += 1
            continue

        total_outros += 1

    mensagens_mesa = [msg for msg in mensagens if msg.tipo == TipoMensagem.HUMANO_ENG.value]
    pendencias_abertas = [msg for msg in mensagens_mesa if msg.resolvida_em is None]
    pendencias_resolvidas = [msg for msg in mensagens_mesa if msg.resolvida_em is not None]
    pendencias_resolvidas.sort(
        key=lambda msg: (_normalizar_data_utc(msg.resolvida_em) or _normalizar_data_utc(msg.criado_em) or agora_utc()),
        reverse=True,
    )

    whispers = [msg for msg in mensagens if msg.is_whisper]
    whispers_recentes = list(reversed(whispers[-limite_whispers_seguro:]))

    revisoes = (
        banco.query(LaudoRevisao).filter(LaudoRevisao.laudo_id == laudo.id).order_by(LaudoRevisao.numero_versao.desc()).limit(limite_revisoes_seguro).all()
    )

    ultima_interacao = None
    if mensagens:
        ultima_interacao = _normalizar_data_utc(mensagens[-1].criado_em)
    if ultima_interacao is None:
        ultima_interacao = _normalizar_data_utc(laudo.atualizado_em) or _normalizar_data_utc(laudo.criado_em)

    resumo_mensagens = ResumoMensagensMesa(
        total=len(mensagens),
        inspetor=total_inspetor,
        ia=total_ia,
        mesa=total_mesa,
        sistema_outros=total_outros,
    )
    resumo_evidencias = ResumoEvidenciasMesa(
        total=evidencias_textuais + evidencias_fotos + evidencias_documentos,
        textuais=evidencias_textuais,
        fotos=evidencias_fotos,
        documentos=evidencias_documentos,
    )
    resumo_pendencias = ResumoPendenciasMesa(
        total=len(mensagens_mesa),
        abertas=len(pendencias_abertas),
        resolvidas=len(pendencias_resolvidas),
    )

    revisoes_payload = [
        RevisaoPacoteMesa(
            numero_versao=int(revisao.numero_versao),
            origem=str(revisao.origem or "ia"),
            resumo=(revisao.resumo or None),
            confianca_geral=(revisao.confianca_geral or None),
            criado_em=_normalizar_data_utc(revisao.criado_em) or agora_utc(),
        )
        for revisao in revisoes
    ]
    documento_estruturado = _montar_documento_estruturado_pacote(laudo)
    coverage_map = _build_coverage_map_pacote(banco, laudo=laudo)
    historico_refazer_inspetor = _build_historico_refazer_inspetor_pacote(
        banco,
        laudo_id=int(laudo.id),
    )
    historico_inspecao = _build_historico_inspecao_pacote(
        banco,
        laudo=laudo,
    )
    case_snapshot = resolver_snapshot_leitura_caso_tecnico(banco, laudo)
    human_override_summary = build_human_override_summary(laudo)
    memoria_operacional_familia = _build_memoria_operacional_familia_pacote(
        banco,
        laudo=laudo,
    )
    verificacao_publica = _build_verificacao_publica_pacote(
        laudo,
        case_snapshot=case_snapshot,
    )
    anexo_pack_payload, emissao_oficial_payload = build_official_issue_package(
        banco,
        laudo=laudo,
    )
    anexo_pack = _build_anexo_pack_pacote(anexo_pack_payload)
    emissao_oficial = _build_emissao_oficial_pacote(emissao_oficial_payload)
    revisao_por_bloco = _build_revisao_por_bloco_pacote(
        banco,
        laudo_id=int(laudo.id),
        documento=documento_estruturado,
        coverage_map=coverage_map,
        mensagens=mensagens,
    )
    catalog_template_scope = _build_catalog_template_scope_pacote(
        banco,
        laudo=laudo,
    )
    status_revisao = getattr(laudo, "status_revisao", "")
    status_conformidade = getattr(laudo, "status_conformidade", "")
    if hasattr(status_revisao, "value"):
        status_revisao = status_revisao.value
    if hasattr(status_conformidade, "value"):
        status_conformidade = status_conformidade.value
    status_visual_label = build_case_status_visual_label(
        lifecycle_status=case_snapshot.case_lifecycle_status,
        active_owner_role=case_snapshot.active_owner_role,
    )
    revisor_id_publico = (
        int(laudo.revisado_por)
        if laudo.revisado_por
        and str(case_snapshot.active_owner_role or "") in {"mesa", "none"}
        else None
    )

    return PacoteMesaLaudo(
        laudo_id=int(laudo.id),
        codigo_hash=str(laudo.codigo_hash or ""),
        tipo_template=str(getattr(laudo, "tipo_template", "") or ""),
        setor_industrial=str(laudo.setor_industrial or ""),
        status_revisao=str(status_revisao or ""),
        status_conformidade=str(status_conformidade or ""),
        case_status=str(case_snapshot.canonical_status or ""),
        case_lifecycle_status=str(case_snapshot.case_lifecycle_status or ""),
        case_workflow_mode=str(case_snapshot.workflow_mode or ""),
        active_owner_role=str(case_snapshot.active_owner_role or ""),
        allowed_next_lifecycle_statuses=list(case_snapshot.allowed_next_lifecycle_statuses),
        allowed_surface_actions=list(case_snapshot.allowed_surface_actions),
        status_visual_label=str(status_visual_label or ""),
        criado_em=_normalizar_data_utc(laudo.criado_em) or agora_utc(),
        atualizado_em=_normalizar_data_utc(laudo.atualizado_em),
        tempo_em_campo_minutos=_tempo_em_campo_minutos(laudo.criado_em),
        ultima_interacao_em=ultima_interacao,
        inspetor_id=int(laudo.usuario_id) if laudo.usuario_id else None,
        revisor_id=revisor_id_publico,
        dados_formulario=getattr(laudo, "dados_formulario", None),
        documento_estruturado=documento_estruturado,
        revisao_por_bloco=revisao_por_bloco,
        parecer_ia=getattr(laudo, "parecer_ia", None),
        resumo_mensagens=resumo_mensagens,
        resumo_evidencias=resumo_evidencias,
        resumo_pendencias=resumo_pendencias,
        catalog_template_scope=catalog_template_scope,
        coverage_map=coverage_map,
        historico_inspecao=historico_inspecao,
        human_override_summary=human_override_summary,
        verificacao_publica=verificacao_publica,
        anexo_pack=anexo_pack,
        emissao_oficial=emissao_oficial,
        historico_refazer_inspetor=historico_refazer_inspetor,
        memoria_operacional_familia=memoria_operacional_familia,
        pendencias_abertas=[_serializar_mensagem_pacote(msg) for msg in pendencias_abertas[:limite_pendencias_seguro]],
        pendencias_resolvidas_recentes=[_serializar_mensagem_pacote(msg) for msg in pendencias_resolvidas[:limite_pendencias_seguro]],
        whispers_recentes=[_serializar_mensagem_pacote(msg) for msg in whispers_recentes],
        revisoes_recentes=revisoes_payload,
    )


__all__ = [
    "agora_utc",
    "criar_notificacao",
    "montar_pacote_mesa_laudo",
]
