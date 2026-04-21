from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domains.chat.laudo_state_helpers import (
    criar_cache_resumo_laudos,
    precarregar_interacoes_laudos,
    resolver_snapshot_leitura_caso_tecnico,
)
from app.core.settings import env_str
from app.domains.revisor.common import _contexto_base, _obter_laudo_empresa
from app.shared.database import Laudo, RegistroAuditoriaEmpresa, TemplateLaudo, Usuario
from nucleo.template_editor_word import MODO_EDITOR_RICO, normalizar_documento_editor, normalizar_modo_editor
from nucleo.template_laudos import mapeamento_cbmgo_padrao

logger = logging.getLogger(__name__)

STATUS_TEMPLATE_RASCUNHO = "rascunho"
STATUS_TEMPLATE_EM_TESTE = "em_teste"
STATUS_TEMPLATE_ATIVO = "ativo"
STATUS_TEMPLATE_LEGADO = "legado"
STATUS_TEMPLATE_ARQUIVADO = "arquivado"

STATUS_TEMPLATE_VALIDOS = {
    STATUS_TEMPLATE_RASCUNHO,
    STATUS_TEMPLATE_EM_TESTE,
    STATUS_TEMPLATE_ATIVO,
    STATUS_TEMPLATE_LEGADO,
    STATUS_TEMPLATE_ARQUIVADO,
}

STATUS_TEMPLATE_LABELS = {
    STATUS_TEMPLATE_RASCUNHO: "Rascunho",
    STATUS_TEMPLATE_EM_TESTE: "Em teste",
    STATUS_TEMPLATE_ATIVO: "Ativo",
    STATUS_TEMPLATE_LEGADO: "Legado",
    STATUS_TEMPLATE_ARQUIVADO: "Arquivado",
}

PORTAL_AUDITORIA_TEMPLATES = "revisao_templates"


def normalizar_status_template(valor: Any, *, fallback: str = STATUS_TEMPLATE_RASCUNHO) -> str:
    texto = str(valor or "").strip().lower()
    if texto in STATUS_TEMPLATE_VALIDOS:
        return texto
    return fallback


def resolver_status_template_ativo(
    status_template: Any,
    *,
    ativo: bool,
) -> tuple[str, bool]:
    status_normalizado = normalizar_status_template(status_template)
    ativo_normalizado = bool(ativo) or status_normalizado == STATUS_TEMPLATE_ATIVO
    if ativo_normalizado:
        return STATUS_TEMPLATE_ATIVO, True
    return status_normalizado, False


def rebaixar_templates_ativos_mesmo_codigo(
    banco: Session,
    *,
    empresa_id: int,
    codigo_template: str,
    template_id_excluir: int | None = None,
) -> None:
    ativos_mesmo_codigo = (
        banco.query(TemplateLaudo)
        .filter(
            TemplateLaudo.empresa_id == empresa_id,
            TemplateLaudo.codigo_template == codigo_template,
            TemplateLaudo.ativo.is_(True),
        )
        .all()
    )
    for item in ativos_mesmo_codigo:
        if template_id_excluir is not None and int(item.id) == int(template_id_excluir):
            continue
        item.ativo = False
        if normalizar_status_template(getattr(item, "status_template", None)) == STATUS_TEMPLATE_ATIVO:
            item.status_template = STATUS_TEMPLATE_LEGADO


def desmarcar_bases_recomendadas_mesmo_codigo(
    banco: Session,
    *,
    empresa_id: int,
    codigo_template: str,
    template_id_excluir: int | None = None,
) -> list[TemplateLaudo]:
    bases_fixas_mesmo_codigo = (
        banco.query(TemplateLaudo)
        .filter(
            TemplateLaudo.empresa_id == empresa_id,
            TemplateLaudo.codigo_template == codigo_template,
            TemplateLaudo.base_recomendada_fixa.is_(True),
        )
        .all()
    )
    bases_desmarcadas: list[TemplateLaudo] = []
    for item in bases_fixas_mesmo_codigo:
        if template_id_excluir is not None and int(item.id) == int(template_id_excluir):
            continue
        item.base_recomendada_fixa = False
        bases_desmarcadas.append(item)
    return bases_desmarcadas


def coletar_metricas_uso_templates(
    banco: Session,
    *,
    empresa_id: int,
) -> dict[str, dict[str, Any]]:
    laudos = (
        banco.query(Laudo)
        .filter(Laudo.empresa_id == empresa_id)
        .order_by(Laudo.atualizado_em.desc().nullslast(), Laudo.criado_em.desc().nullslast(), Laudo.id.desc())
        .all()
    )
    cache_resumo = criar_cache_resumo_laudos()
    precarregar_interacoes_laudos(
        banco,
        [int(item.id) for item in laudos],
        cache=cache_resumo,
    )
    metricas: dict[str, dict[str, Any]] = {}
    for laudo in laudos:
        codigo = str(getattr(laudo, "tipo_template", "") or "").strip()
        if not codigo:
            continue
        snapshot = resolver_snapshot_leitura_caso_tecnico(
            banco,
            laudo,
            cache=cache_resumo,
        )
        atual = metricas.setdefault(
            codigo,
            {
                "uso_total": 0,
                "uso_em_campo": 0,
                "uso_aguardando": 0,
                "ultima_utilizacao_em": None,
            },
        )
        atual["uso_total"] += 1
        if str(snapshot.active_owner_role or "") == "mesa":
            atual["uso_aguardando"] += 1
        elif str(snapshot.active_owner_role or "") == "inspetor":
            atual["uso_em_campo"] += 1

        ultima_utilizacao_em = getattr(laudo, "atualizado_em", None)
        atual_iso = ultima_utilizacao_em.isoformat() if ultima_utilizacao_em else None
        if atual_iso and (not atual["ultima_utilizacao_em"] or atual_iso > str(atual["ultima_utilizacao_em"])):
            atual["ultima_utilizacao_em"] = atual_iso
    return metricas


def _prioridade_base_recomendada(payload: dict[str, Any]) -> tuple[int, int, int, int]:
    status_template = normalizar_status_template(
        payload.get("status_template"),
        fallback=STATUS_TEMPLATE_ATIVO if bool(payload.get("ativo")) else STATUS_TEMPLATE_RASCUNHO,
    )
    prioridade_status = {
        STATUS_TEMPLATE_ATIVO: 50,
        STATUS_TEMPLATE_EM_TESTE: 40,
        STATUS_TEMPLATE_RASCUNHO: 30,
        STATUS_TEMPLATE_LEGADO: 20,
        STATUS_TEMPLATE_ARQUIVADO: 10,
    }.get(status_template, 0)
    bonus_modo = 1 if bool(payload.get("is_editor_rico")) else 0
    return (
        prioridade_status,
        int(payload.get("versao") or 0),
        bonus_modo,
        int(payload.get("id") or 0),
    )


def motivo_base_recomendada(payload: dict[str, Any]) -> str:
    if bool(payload.get("base_recomendada_fixa")):
        return "Base promovida manualmente pela mesa"
    status_template = normalizar_status_template(
        payload.get("status_template"),
        fallback=STATUS_TEMPLATE_ATIVO if bool(payload.get("ativo")) else STATUS_TEMPLATE_RASCUNHO,
    )
    if status_template == STATUS_TEMPLATE_ATIVO:
        return "Versão ativa em operação"
    if status_template == STATUS_TEMPLATE_EM_TESTE:
        return "Versão em teste mais madura"
    if status_template == STATUS_TEMPLATE_RASCUNHO:
        return "Rascunho mais recente do grupo"
    if status_template == STATUS_TEMPLATE_LEGADO:
        return "Legado mais recente para referência"
    return "Última versão arquivada disponível"


def selecionar_base_recomendada_grupo(grupo_ordenado: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    bases_fixas = [item for item in grupo_ordenado if bool(item.get("base_recomendada_fixa"))]
    if bases_fixas:
        recomendada_manual = sorted(
            bases_fixas,
            key=lambda item: (
                int(item.get("versao") or 0),
                int(item.get("id") or 0),
            ),
            reverse=True,
        )[0]
        return recomendada_manual, "manual"
    return max(grupo_ordenado, key=_prioridade_base_recomendada), "automatica"


def obter_template_laudo_empresa(
    banco: Session,
    *,
    template_id: int,
    empresa_id: int,
) -> TemplateLaudo:
    template = banco.get(TemplateLaudo, template_id)
    if not template or template.empresa_id != empresa_id:
        raise HTTPException(status_code=404, detail="Template não encontrado.")
    return template


def template_codigo_versao_existe(
    banco: Session,
    *,
    empresa_id: int,
    codigo_template: str,
    versao: int,
) -> bool:
    return (
        banco.query(TemplateLaudo.id)
        .filter(
            TemplateLaudo.empresa_id == int(empresa_id),
            TemplateLaudo.codigo_template == str(codigo_template or ""),
            TemplateLaudo.versao == int(versao),
        )
        .first()
        is not None
    )


def listar_templates_mesmo_codigo_empresa(
    banco: Session,
    *,
    empresa_id: int,
    codigo_template: str,
) -> list[TemplateLaudo]:
    return (
        banco.query(TemplateLaudo)
        .filter(
            TemplateLaudo.empresa_id == int(empresa_id),
            TemplateLaudo.codigo_template == str(codigo_template or ""),
        )
        .order_by(TemplateLaudo.versao.desc(), TemplateLaudo.id.desc())
        .all()
    )


def listar_templates_ativos_mesmo_codigo(
    banco: Session,
    *,
    empresa_id: int,
    codigo_template: str,
    template_id_excluir: int | None = None,
) -> list[TemplateLaudo]:
    consulta = banco.query(TemplateLaudo).filter(
        TemplateLaudo.empresa_id == int(empresa_id),
        TemplateLaudo.codigo_template == str(codigo_template or ""),
        TemplateLaudo.ativo.is_(True),
    )
    if template_id_excluir is not None:
        consulta = consulta.filter(TemplateLaudo.id != int(template_id_excluir))
    return consulta.all()


def proxima_versao_template_codigo(
    banco: Session,
    *,
    empresa_id: int,
    codigo_template: str,
    versao_atual: int,
) -> int:
    maior_versao = (
        banco.query(func.max(TemplateLaudo.versao))
        .filter(
            TemplateLaudo.empresa_id == int(empresa_id),
            TemplateLaudo.codigo_template == str(codigo_template or ""),
        )
        .scalar()
    )
    return max(int(versao_atual or 1) + 1, int(maior_versao or 0) + 1)


def _normalizar_ids_lote_template(ids_brutos: list[int] | tuple[int, ...] | None) -> list[int]:
    ids_normalizados: list[int] = []
    vistos: set[int] = set()
    for valor in ids_brutos or []:
        try:
            template_id = int(valor)
        except (TypeError, ValueError):
            continue
        if template_id < 1 or template_id in vistos:
            continue
        vistos.add(template_id)
        ids_normalizados.append(template_id)
    if not ids_normalizados:
        raise HTTPException(status_code=400, detail="Selecione ao menos um template válido.")
    return ids_normalizados


def obter_templates_lote_empresa(
    banco: Session,
    *,
    template_ids: list[int],
    empresa_id: int,
) -> list[TemplateLaudo]:
    ids_normalizados = _normalizar_ids_lote_template(template_ids)
    templates_por_id = {
        int(item.id): item
        for item in (
            banco.query(TemplateLaudo)
            .filter(
                TemplateLaudo.empresa_id == empresa_id,
                TemplateLaudo.id.in_(ids_normalizados),
            )
            .all()
        )
    }
    if len(templates_por_id) != len(ids_normalizados):
        raise HTTPException(status_code=404, detail="Um ou mais templates não foram encontrados.")
    return [templates_por_id[item_id] for item_id in ids_normalizados]


def remover_assets_fisicos_template(template: TemplateLaudo) -> None:
    assets = template.assets_json if isinstance(template.assets_json, list) else []
    for item in assets:
        if not isinstance(item, dict):
            continue
        caminho = Path(str(item.get("path") or "")).expanduser().resolve()
        try:
            if caminho.is_file():
                caminho.unlink()
        except Exception:
            logger.warning(
                "Falha ao remover asset físico do template | template_id=%s path=%s",
                template.id,
                str(caminho),
                exc_info=True,
            )


_PREVIEW_FIELD_LABEL_OVERRIDES = {
    "informacoes_gerais": "Informações gerais",
    "dados_gerais": "Dados gerais",
    "resumo_executivo": "Resumo executivo",
    "responsavel_pela_inspecao": "Responsável pela inspeção",
    "data_inspecao": "Data da inspeção",
    "local_inspecao": "Local da inspeção",
    "nome_inspecao": "Nome da inspeção",
    "cliente": "Cliente",
    "unidade": "Unidade",
    "equipamento": "Equipamento",
    "observacoes": "Observações",
    "conclusao": "Conclusão",
    "parecer_final": "Parecer final",
    "recomendacoes": "Recomendações",
    "evidencias": "Evidências",
    "assinatura": "Assinatura",
}
_PREVIEW_STATUS_NOTES = {
    STATUS_TEMPLATE_ATIVO: "Modelo pronto para a mesa revisar e a IA preencher.",
    STATUS_TEMPLATE_EM_TESTE: "Modelo em ajuste fino antes de entrar no fluxo principal.",
    STATUS_TEMPLATE_RASCUNHO: "Modelo em montagem, mas já dá para enxergar a cara final do laudo.",
    STATUS_TEMPLATE_LEGADO: "Modelo antigo guardado como referência visual e estrutural.",
    STATUS_TEMPLATE_ARQUIVADO: "Modelo fora da vitrine principal, mantido só para histórico.",
}


def _lista_dicts_preview(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _mapa_preview(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {}


def _compactar_texto_preview(texto: Any, *, limite: int = 64) -> str:
    resumo = " ".join(str(texto or "").split()).strip()
    if len(resumo) <= limite:
        return resumo
    return resumo[: max(0, limite - 1)].rstrip() + "…"


def _texto_inline_preview(nodes: list[dict[str, Any]] | None) -> str:
    partes: list[str] = []
    for node in nodes or []:
        tipo = str(node.get("type") or "").strip()
        attrs = _mapa_preview(node.get("attrs"))
        filhos = _lista_dicts_preview(node.get("content"))
        if tipo == "text":
            partes.append(str(node.get("text") or ""))
            continue
        if tipo == "hardBreak":
            partes.append(" ")
            continue
        if tipo == "placeholder":
            bruto = str(attrs.get("raw") or attrs.get("name") or attrs.get("path") or "").strip()
            if bruto:
                partes.append(f"{{{{{bruto}}}}}")
            continue
        if filhos:
            nested = _texto_inline_preview(filhos)
            if nested:
                partes.append(nested)
    return " ".join(" ".join(partes).split()).strip()


def _formatar_rotulo_campo_preview(valor: Any) -> str:
    bruto = str(valor or "").strip()
    if not bruto:
        return ""
    limpo = bruto.replace("{{", "").replace("}}", "").strip()
    limpo = limpo.split(":")[-1]
    partes = [parte for parte in limpo.replace("-", "_").split(".") if parte]
    chave = str(partes[-1] if partes else limpo).strip().lower()
    if chave in _PREVIEW_FIELD_LABEL_OVERRIDES:
        return _PREVIEW_FIELD_LABEL_OVERRIDES[chave]
    texto = chave.replace("_", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    if not texto:
        return ""
    palavras = []
    for parte in texto.split(" "):
        if parte in {"nr", "epi", "pdf", "ia", "trrf", "rti", "spda", "cli", "json"}:
            palavras.append(parte.upper())
        else:
            palavras.append(parte.capitalize())
    return " ".join(palavras)


def _coletar_chaves_mapeamento_preview(payload: Any) -> list[str]:
    vistos: set[str] = set()
    chaves: list[str] = []

    def visitar(valor: Any) -> None:
        if isinstance(valor, dict):
            chave = str(valor.get("key") or "").strip()
            if chave and chave not in vistos:
                vistos.add(chave)
                chaves.append(chave)
            for item in valor.values():
                visitar(item)
            return
        if isinstance(valor, list):
            for item in valor:
                visitar(item)

    visitar(payload)
    return chaves


def _extrair_resumo_documento_editor(payload: Any) -> tuple[list[str], list[str]]:
    try:
        documento = normalizar_documento_editor(payload if isinstance(payload, dict) else None)
    except ValueError:
        return [], []

    secoes: list[str] = []
    secoes_vistas: set[str] = set()
    campos: list[str] = []
    campos_vistos: set[str] = set()
    fallback_textos: list[str] = []
    fallback_vistos: set[str] = set()

    def registrar_secao(texto: str) -> None:
        resumo = _compactar_texto_preview(texto, limite=60)
        chave = resumo.lower()
        if resumo and chave not in secoes_vistas:
            secoes_vistas.add(chave)
            secoes.append(resumo)

    def registrar_fallback(texto: str) -> None:
        resumo = _compactar_texto_preview(texto, limite=60)
        chave = resumo.lower()
        if resumo and chave not in fallback_vistos:
            fallback_vistos.add(chave)
            fallback_textos.append(resumo)

    def registrar_campo(texto: str) -> None:
        rotulo = _formatar_rotulo_campo_preview(texto)
        chave = rotulo.lower()
        if rotulo and chave not in campos_vistos:
            campos_vistos.add(chave)
            campos.append(rotulo)

    def visitar(node: dict[str, Any]) -> None:
        tipo = str(node.get("type") or "").strip()
        attrs = _mapa_preview(node.get("attrs"))
        filhos = _lista_dicts_preview(node.get("content"))
        if tipo == "heading":
            registrar_secao(_texto_inline_preview(filhos))
        elif tipo in {"paragraph", "bulletList", "orderedList", "table"}:
            registrar_fallback(_texto_inline_preview(filhos))
        elif tipo == "placeholder":
            bruto = str(attrs.get("raw") or attrs.get("name") or attrs.get("path") or "").strip()
            if bruto:
                registrar_campo(bruto)
        for filho in filhos:
            visitar(filho)

    doc = _mapa_preview(documento.get("doc"))
    for node in _lista_dicts_preview(doc.get("content")):
        visitar(node)

    if not secoes:
        secoes = fallback_textos[:4]
    return secoes[:4], campos[:6]


def _resumir_secoes_por_chaves(chaves: list[str]) -> list[str]:
    secoes: list[str] = []
    vistos: set[str] = set()
    for chave in chaves:
        partes = [parte for parte in str(chave or "").strip().split(".") if parte]
        base = partes[0] if partes else str(chave or "").strip()
        rotulo = _formatar_rotulo_campo_preview(base)
        chave_rotulo = rotulo.lower()
        if rotulo and chave_rotulo not in vistos:
            vistos.add(chave_rotulo)
            secoes.append(rotulo)
    return secoes[:4]


def _build_preview_summary(item: TemplateLaudo) -> dict[str, Any]:
    modo_editor = normalizar_modo_editor(getattr(item, "modo_editor", None))
    status_template = normalizar_status_template(
        getattr(item, "status_template", None),
        fallback=STATUS_TEMPLATE_ATIVO if bool(getattr(item, "ativo", False)) else STATUS_TEMPLATE_RASCUNHO,
    )
    chaves_mapeamento = _coletar_chaves_mapeamento_preview(getattr(item, "mapeamento_campos_json", None) or {})
    secoes_editor, campos_editor = _extrair_resumo_documento_editor(getattr(item, "documento_editor_json", None))
    secoes = secoes_editor or _resumir_secoes_por_chaves(chaves_mapeamento)
    campos = campos_editor or [_formatar_rotulo_campo_preview(chave) for chave in chaves_mapeamento[:6]]
    secoes = [secao for secao in secoes if secao][:4]
    campos = [campo for campo in campos if campo][:6]
    if not secoes:
        secoes = [
            "Identificação do laudo",
            "Contexto da inspeção",
            "Resultado técnico",
            "Fechamento e assinatura",
        ]
    if not campos:
        campos = [
            "Cliente",
            "Unidade",
            "Equipamento",
            "Data da inspeção",
            "Responsável pela inspeção",
            "Conclusão",
        ]
    return {
        "status_note": _PREVIEW_STATUS_NOTES.get(status_template, _PREVIEW_STATUS_NOTES[STATUS_TEMPLATE_RASCUNHO]),
        "mode_note": (
            "A base visual nasce no Word e o PDF final sai dessa estrutura."
            if modo_editor == MODO_EDITOR_RICO
            else "A base visual vem de um PDF estruturado pronto para receber o preenchimento."
        ),
        "sections": secoes,
        "fill_fields": campos,
    }


def serializar_template_laudo(item: TemplateLaudo, incluir_mapeamento: bool = False) -> dict[str, Any]:
    modo_editor = normalizar_modo_editor(getattr(item, "modo_editor", None))
    assets = item.assets_json if isinstance(getattr(item, "assets_json", None), list) else []
    status_template = normalizar_status_template(
        getattr(item, "status_template", None),
        fallback=(
            STATUS_TEMPLATE_ATIVO
            if bool(getattr(item, "ativo", False))
            else STATUS_TEMPLATE_RASCUNHO
        ),
    )
    payload: dict[str, Any] = {
        "id": item.id,
        "nome": item.nome,
        "codigo_template": item.codigo_template,
        "versao": item.versao,
        "ativo": bool(item.ativo),
        "base_recomendada_fixa": bool(getattr(item, "base_recomendada_fixa", False)),
        "status_template": status_template,
        "status_template_label": STATUS_TEMPLATE_LABELS.get(status_template, "Rascunho"),
        "modo_editor": modo_editor,
        "is_editor_rico": modo_editor == MODO_EDITOR_RICO,
        "possui_documento_editor": bool(getattr(item, "documento_editor_json", None)),
        "total_assets": len(assets),
        "observacoes": item.observacoes or "",
        "preview_summary": _build_preview_summary(item),
        "criado_em": item.criado_em.isoformat() if item.criado_em else None,
        "atualizado_em": item.atualizado_em.isoformat() if item.atualizado_em else None,
        "criado_por_id": item.criado_por_id,
    }
    if incluir_mapeamento:
        payload["mapeamento_campos_json"] = item.mapeamento_campos_json or {}
        payload["documento_editor_json"] = item.documento_editor_json or {}
        payload["estilo_json"] = item.estilo_json or {}
        payload["assets_json"] = assets
    return payload


def label_status_template(valor: Any) -> str:
    status_normalizado = normalizar_status_template(valor)
    return STATUS_TEMPLATE_LABELS.get(status_normalizado, "Rascunho")


def resumir_texto_auditoria_templates(texto: Any, *, limite: int = 220) -> str:
    resumo = " ".join(str(texto or "").split()).strip()
    if not resumo:
        return ""
    if len(resumo) <= limite:
        return resumo
    return resumo[: max(0, limite - 1)].rstrip() + "…"


def payload_template_auditoria(item: TemplateLaudo) -> dict[str, Any]:
    return {
        "template_id": int(item.id) if getattr(item, "id", None) else None,
        "nome": str(item.nome or ""),
        "codigo_template": str(item.codigo_template or ""),
        "versao": int(item.versao or 1),
        "status_template": normalizar_status_template(getattr(item, "status_template", None)),
        "status_template_label": label_status_template(getattr(item, "status_template", None)),
        "ativo": bool(getattr(item, "ativo", False)),
        "base_recomendada_fixa": bool(getattr(item, "base_recomendada_fixa", False)),
        "modo_editor": normalizar_modo_editor(getattr(item, "modo_editor", None)),
    }


def resumir_templates_auditoria(templates_lote: list[TemplateLaudo], *, limite: int = 4) -> str:
    itens: list[str] = []
    for item in templates_lote[:limite]:
        codigo = str(item.codigo_template or "").strip() or "template"
        itens.append(f"{codigo} v{int(item.versao or 1)}")
    if not itens:
        return "nenhum template"
    if len(templates_lote) > limite:
        itens.append(f"+{len(templates_lote) - limite}")
    return ", ".join(itens)


def registrar_auditoria_templates(
    banco: Session,
    *,
    usuario: Usuario,
    acao: str,
    resumo: str,
    detalhe: str = "",
    payload: dict[str, Any] | None = None,
) -> None:
    registro = RegistroAuditoriaEmpresa(
        empresa_id=int(usuario.empresa_id),
        ator_usuario_id=int(usuario.id) if getattr(usuario, "id", None) else None,
        portal=PORTAL_AUDITORIA_TEMPLATES,
        acao=str(acao or "acao").strip()[:80],
        resumo=resumir_texto_auditoria_templates(resumo, limite=220) or "Ação registrada na biblioteca de templates",
        detalhe=resumir_texto_auditoria_templates(detalhe, limite=1200) or None,
        payload_json=payload or None,
    )
    banco.add(registro)


def listar_auditoria_templates(
    banco: Session,
    *,
    empresa_id: int,
    limite: int = 12,
) -> list[RegistroAuditoriaEmpresa]:
    return (
        banco.query(RegistroAuditoriaEmpresa)
        .filter(
            RegistroAuditoriaEmpresa.empresa_id == int(empresa_id),
            RegistroAuditoriaEmpresa.portal == PORTAL_AUDITORIA_TEMPLATES,
        )
        .order_by(RegistroAuditoriaEmpresa.criado_em.desc(), RegistroAuditoriaEmpresa.id.desc())
        .limit(max(1, min(int(limite or 12), 50)))
        .all()
    )


def serializar_registro_auditoria_templates(registro: RegistroAuditoriaEmpresa) -> dict[str, Any]:
    criado_em = getattr(registro, "criado_em", None)
    ator = getattr(registro, "ator_usuario", None)
    return {
        "id": int(registro.id),
        "acao": str(registro.acao or ""),
        "portal": str(registro.portal or PORTAL_AUDITORIA_TEMPLATES),
        "resumo": str(registro.resumo or ""),
        "detalhe": str(registro.detalhe or ""),
        "payload": registro.payload_json or {},
        "criado_em": criado_em.isoformat() if criado_em else "",
        "criado_em_label": (criado_em.astimezone().strftime("%d/%m/%Y %H:%M") if criado_em else "Agora"),
        "ator_usuario_id": int(registro.ator_usuario_id) if registro.ator_usuario_id else None,
        "ator_nome": getattr(ator, "nome", None) or getattr(ator, "nome_completo", None) or "Sistema",
    }


def enriquecer_versionamento_templates(itens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grupos: dict[str, list[dict[str, Any]]] = {}
    for item in itens:
        codigo = str(item.get("codigo_template") or "").strip()
        if not codigo:
            continue
        grupos.setdefault(codigo, []).append(item)

    for codigo, grupo in grupos.items():
        grupo_ordenado = sorted(
            grupo,
            key=lambda item: (
                int(item.get("versao") or 0),
                int(item.get("id") or 0),
            ),
            reverse=True,
        )
        recomendado, origem_recomendacao = selecionar_base_recomendada_grupo(grupo_ordenado)
        ativo = next((item for item in grupo_ordenado if bool(item.get("ativo"))), None)
        versao_mais_recente = grupo_ordenado[0] if grupo_ordenado else None
        total_word = sum(1 for item in grupo_ordenado if bool(item.get("is_editor_rico")))
        total_pdf = max(0, len(grupo_ordenado) - total_word)
        versoes_disponiveis = [int(item.get("versao") or 0) for item in grupo_ordenado]

        for ordem, item in enumerate(grupo_ordenado, start=1):
            item["grupo_codigo_template"] = codigo
            item["grupo_total_versoes"] = len(grupo_ordenado)
            item["grupo_total_word"] = total_word
            item["grupo_total_pdf"] = total_pdf
            item["grupo_ordem_versao"] = ordem
            item["grupo_versoes_disponiveis"] = versoes_disponiveis
            item["grupo_versao_mais_recente"] = int(versao_mais_recente.get("versao") or 0) if versao_mais_recente else int(item.get("versao") or 0)
            item["grupo_template_ativo_id"] = int(ativo.get("id") or 0) if ativo else None
            item["grupo_template_ativo_versao"] = int(ativo.get("versao") or 0) if ativo else None
            item["grupo_base_recomendada_id"] = int(recomendado.get("id") or 0) if recomendado else int(item.get("id") or 0)
            item["grupo_base_recomendada_versao"] = int(recomendado.get("versao") or 0) if recomendado else int(item.get("versao") or 0)
            item["grupo_base_recomendada_origem"] = origem_recomendacao
            item["grupo_base_recomendada_fixa"] = bool(recomendado.get("base_recomendada_fixa"))
            item["is_base_recomendada"] = int(item.get("id") or 0) == int(recomendado.get("id") or 0)
            item["base_recomendada_origem"] = origem_recomendacao if item["is_base_recomendada"] else None
            item["base_recomendada_motivo"] = motivo_base_recomendada(recomendado if item["is_base_recomendada"] else recomendado)
    return itens


def listar_catalogo_templates_empresa(banco: Session, *, empresa_id: int) -> list[dict[str, Any]]:
    templates_db = (
        banco.query(TemplateLaudo)
        .filter(TemplateLaudo.empresa_id == empresa_id)
        .order_by(
            TemplateLaudo.codigo_template.asc(),
            TemplateLaudo.versao.desc(),
            TemplateLaudo.id.desc(),
        )
        .all()
    )
    metricas_uso = coletar_metricas_uso_templates(banco, empresa_id=int(empresa_id))
    itens: list[dict[str, Any]] = []
    for item in templates_db:
        payload = serializar_template_laudo(item)
        payload.update(
            metricas_uso.get(
                str(item.codigo_template),
                {
                    "uso_total": 0,
                    "uso_em_campo": 0,
                    "uso_aguardando": 0,
                    "ultima_utilizacao_em": None,
                },
            )
        )
        itens.append(payload)

    enriquecer_versionamento_templates(itens)
    return itens


def _formatar_data_operacao_templates(valor_iso: str) -> str:
    texto = str(valor_iso or "").strip()
    if not texto:
        return "-"
    try:
        instante = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return "-"
    return instante.astimezone().strftime("%d/%m/%Y %H:%M")


def resumir_operacao_templates_mesa(
    banco: Session,
    *,
    empresa_id: int,
) -> dict[str, Any]:
    itens = listar_catalogo_templates_empresa(banco, empresa_id=int(empresa_id))
    grupos: dict[str, dict[str, Any]] = {}
    ultimo_uso_operacional = ""

    for item in itens:
        codigo = str(item.get("codigo_template") or "").strip()
        if not codigo:
            continue
        grupo = grupos.setdefault(
            codigo,
            {
                "tem_ativo": False,
                "uso_em_campo": 0,
                "uso_aguardando": 0,
                "base_manual": False,
            },
        )
        grupo["tem_ativo"] = bool(grupo["tem_ativo"]) or bool(item.get("ativo"))
        grupo["uso_em_campo"] = max(int(grupo["uso_em_campo"] or 0), int(item.get("uso_em_campo") or 0))
        grupo["uso_aguardando"] = max(int(grupo["uso_aguardando"] or 0), int(item.get("uso_aguardando") or 0))
        grupo["base_manual"] = bool(grupo["base_manual"]) or (
            bool(item.get("is_base_recomendada"))
            and str(item.get("grupo_base_recomendada_origem") or item.get("base_recomendada_origem") or "").strip().lower()
            == "manual"
        )
        ultimo_uso_item = str(item.get("ultima_utilizacao_em") or "").strip()
        if ultimo_uso_item and (not ultimo_uso_operacional or ultimo_uso_item > ultimo_uso_operacional):
            ultimo_uso_operacional = ultimo_uso_item

    total_ativos = sum(1 for item in itens if bool(item.get("ativo")))
    total_em_teste = sum(1 for item in itens if str(item.get("status_template") or "") == STATUS_TEMPLATE_EM_TESTE)
    total_rascunhos = sum(1 for item in itens if str(item.get("status_template") or "") == STATUS_TEMPLATE_RASCUNHO)
    total_word = sum(1 for item in itens if bool(item.get("is_editor_rico")))
    total_pdf = max(0, len(itens) - total_word)
    total_codigos_sem_ativo = sum(1 for grupo in grupos.values() if not bool(grupo["tem_ativo"]))
    total_codigos_em_operacao = sum(
        1
        for grupo in grupos.values()
        if int(grupo["uso_em_campo"] or 0) > 0 or int(grupo["uso_aguardando"] or 0) > 0
    )
    total_codigos_em_operacao_sem_ativo = sum(
        1
        for grupo in grupos.values()
        if (int(grupo["uso_em_campo"] or 0) > 0 or int(grupo["uso_aguardando"] or 0) > 0)
        and not bool(grupo["tem_ativo"])
    )
    total_bases_manuais = sum(1 for grupo in grupos.values() if bool(grupo["base_manual"]))

    return {
        "total_templates": len(itens),
        "total_codigos": len(grupos),
        "total_ativos": total_ativos,
        "total_em_teste": total_em_teste,
        "total_rascunhos": total_rascunhos,
        "total_word": total_word,
        "total_pdf": total_pdf,
        "total_codigos_sem_ativo": total_codigos_sem_ativo,
        "total_codigos_em_operacao": total_codigos_em_operacao,
        "total_codigos_em_operacao_sem_ativo": total_codigos_em_operacao_sem_ativo,
        "total_bases_manuais": total_bases_manuais,
        "ultima_utilizacao_em": ultimo_uso_operacional or None,
        "ultima_utilizacao_em_label": _formatar_data_operacao_templates(ultimo_uso_operacional),
    }


def listar_auditoria_templates_serializada(
    banco: Session,
    *,
    empresa_id: int,
    limite: int = 12,
) -> list[dict[str, Any]]:
    return [
        serializar_registro_auditoria_templates(item)
        for item in listar_auditoria_templates(
            banco,
            empresa_id=int(empresa_id),
            limite=limite,
        )
    ]


def obter_dados_formulario_preview(
    *,
    banco: Session,
    usuario: Usuario,
    dados: Any,
) -> dict[str, Any]:
    dados_formulario: dict[str, Any] = {}
    laudo_id = getattr(dados, "laudo_id", None)
    dados_payload = getattr(dados, "dados_formulario", None)
    if laudo_id:
        laudo = _obter_laudo_empresa(banco, int(laudo_id), usuario.empresa_id)
        dados_formulario = laudo.dados_formulario or {}
    elif isinstance(dados_payload, dict):
        dados_formulario = dados_payload
    if not dados_formulario and env_str("SCHEMATHESIS_TEST_HINTS", "0").strip() == "1":
        return {
            "informacoes_gerais": {
                "responsavel_pela_inspecao": "Seed Schemathesis",
                "local_inspecao": "Planta Seed",
            },
            "resumo_executivo": "Preview reduzido para contrato automatizado.",
        }
    return dados_formulario


def contexto_templates_padrao(request: Request, usuario: Usuario) -> dict[str, Any]:
    contexto = _contexto_base(request)
    contexto.update(
        {
            "usuario": usuario,
            "mapeamento_cbmgo_padrao_json": json.dumps(
                mapeamento_cbmgo_padrao(),
                ensure_ascii=False,
                indent=2,
            ),
            "dados_preview_exemplo_json": json.dumps(
                {
                    "informacoes_gerais": {
                        "responsavel_pela_inspecao": "Eng. Laura Mendonca",
                        "data_inspecao": datetime.now().strftime("%d/%m/%Y"),
                        "local_inspecao": "Unidade Industrial Tariel",
                        "cliente": "Cliente demonstracao",
                        "unidade": "Planta principal",
                        "equipamento": "Linha de vida TR-204",
                        "nome_inspecao": "Inspecao tecnica pre-preenchida",
                    },
                    "resumo_executivo": "Resumo tecnico preliminar da inspecao com achados principais, bloqueios e orientacao final da mesa.",
                    "conclusao": "Equipamento apto mediante adequacoes pontuais e validacao final em campo.",
                    "recomendacoes": "Reforcar sinalizacao, atualizar registro fotografico e confirmar assinatura do responsavel local.",
                    "trrf_observacoes": "Observacoes TRRF para validacao da mesa.",
                },
                ensure_ascii=False,
                indent=2,
            ),
        }
    )
    return contexto


def marcar_template_status(
    banco: Session,
    *,
    template: TemplateLaudo,
    status_template: str,
) -> None:
    status_normalizado = normalizar_status_template(status_template)
    if status_normalizado == STATUS_TEMPLATE_ATIVO:
        rebaixar_templates_ativos_mesmo_codigo(
            banco,
            empresa_id=int(template.empresa_id),
            codigo_template=str(template.codigo_template),
            template_id_excluir=int(template.id) if template.id else None,
        )
        template.ativo = True
        template.status_template = STATUS_TEMPLATE_ATIVO
        return

    template.ativo = False
    template.status_template = status_normalizado
