"""Helpers de perfil e preferências do portal/app do inspetor."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.settings import env_str
from app.domains.chat.auth_helpers import usuario_nome
from app.domains.chat.laudo_state_helpers import (
    CARD_STATUS_LABELS,
    CacheResumoLaudoRequest,
    criar_cache_resumo_laudos,
    laudo_possui_historico_visivel,
    laudo_tem_interacao,
    obter_estado_api_laudo,
    precarregar_interacoes_laudos,
    serializar_card_laudo,
)
from app.domains.chat.normalization import nome_template_humano
from app.domains.chat.normalization import normalizar_email
from app.domains.chat.session_helpers import obter_contexto_inicial_laudo_sessao
from app.shared.database import (
    EmissaoOficialLaudo,
    Laudo,
    MensagemLaudo,
    PreferenciaMobileUsuario,
    TipoMensagem,
    Usuario,
)
from app.shared.official_issue_package import serialize_official_issue_record
from app.shared.db.contracts import EntryModeEffective, EntryModePreference
from app.shared.tenant_admin_policy import (
    summarize_tenant_admin_operational_package,
    summarize_tenant_admin_policy,
    tenant_admin_user_portal_label,
)
from app.shared.tenant_entitlement_guard import tenant_access_policy_for_user
from app.shared.tenant_report_catalog import build_tenant_template_option_snapshot
from app.shared.security import (
    PORTAL_INSPETOR,
    definir_sessao_portal,
    nivel_acesso_sessao_portal,
    obter_dados_sessao_portal,
    usuario_portal_switch_links,
    usuario_portais_habilitados,
)
from app.v2.adapters.android_case_view import adapt_inspector_case_view_projection_to_android_case
from app.v2.case_runtime import build_technical_case_context_bundle
from app.v2.contracts.projections import build_inspector_case_view_projection
from app.v2.provenance import (
    build_inspector_content_origin_summary,
    load_message_origin_counters,
)
from app.v2.runtime import (
    actor_role_from_user,
    v2_android_case_adapter_enabled,
    v2_document_facade_enabled,
    v2_document_shadow_enabled,
    v2_policy_engine_enabled,
    v2_provenance_enabled,
)

logger = logging.getLogger(__name__)

PASTA_FOTOS_PERFIL = Path(env_str("PASTA_UPLOADS_PERFIS", "static/uploads/perfis")).expanduser()
MIME_FOTO_PERMITIDOS = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
MAX_FOTO_PERFIL_BYTES = 4 * 1024 * 1024

SONS_NOTIFICACAO_PERMITIDOS = {"Ping", "Sino curto", "Silencioso"}
RETENCAO_DADOS_PERMITIDA = {"30 dias", "90 dias", "1 ano", "Até excluir"}
MODELOS_IA_PERMITIDOS = {"rápido", "equilibrado", "avançado"}
CONFIGURACOES_CRITICAS_MOBILE_PADRAO: dict[str, dict[str, object]] = {
    "notificacoes": {
        "notifica_respostas": True,
        "notifica_push": True,
        "som_notificacao": "Ping",
        "vibracao_ativa": True,
        "emails_ativos": False,
    },
    "privacidade": {
        "mostrar_conteudo_notificacao": False,
        "ocultar_conteudo_bloqueado": True,
        "mostrar_somente_nova_mensagem": True,
        "salvar_historico_conversas": True,
        "compartilhar_melhoria_ia": False,
        "retencao_dados": "90 dias",
    },
    "permissoes": {
        "microfone_permitido": True,
        "camera_permitida": True,
        "arquivos_permitidos": True,
        "notificacoes_permitidas": True,
        "biometria_permitida": True,
    },
    "experiencia_ia": {
        "modelo_ia": "equilibrado",
        "entry_mode_preference": EntryModePreference.AUTO_RECOMMENDED.value,
        "remember_last_case_mode": False,
    },
}

MODELOS_TECNICOS_PORTAL: tuple[dict[str, str], ...] = (
    {
        "titulo": "Caldeira Industrial",
        "badge": "RECOMENDADO",
        "descricao": "Inspeção completa de caldeiras e vasos de pressão conforme NR-13",
        "duracao": "~2h de inspeção",
        "icone": "bolt",
        "status": "cyan",
        "tipo": "nr13",
        "preprompt": "Inicie inspeção NR-13 para caldeiras e vasos de pressão. Quero não conformidades, riscos e plano de ação.",
    },
    {
        "titulo": "Ponte Rolante",
        "badge": "",
        "descricao": "Análise estrutural e funcional de equipamentos de elevação",
        "duracao": "~1.5h de inspeção",
        "icone": "query_stats",
        "status": "purple",
        "tipo": "nr12maquinas",
        "preprompt": "Inicie análise estrutural e funcional de equipamentos de elevação com foco em criticidade e conformidade.",
    },
    {
        "titulo": "Instalação Elétrica",
        "badge": "",
        "descricao": "Verificação de conformidade elétrica e proteções",
        "duracao": "~1h de inspeção",
        "icone": "electric_bolt",
        "status": "warning",
        "tipo": "rti",
        "preprompt": "Inicie análise RTI da instalação elétrica. Vou enviar fotos e medições para laudo com recomendações.",
    },
)

_MODELO_PORTAL_RUNTIME_META = {
    "loto": {"icone": "lock", "status": "warning", "duracao": "Liberado pela empresa"},
    "nr11_movimentacao": {"icone": "forklift", "status": "purple", "duracao": "Liberado pela empresa"},
    "nr13": {"icone": "bolt", "status": "cyan", "duracao": "Liberado pela empresa"},
    "nr13_calibracao": {"icone": "speed", "status": "cyan", "duracao": "Liberado pela empresa"},
    "nr13_teste_hidrostatico": {"icone": "opacity", "status": "cyan", "duracao": "Liberado pela empresa"},
    "nr13_ultrassom": {"icone": "straighten", "status": "cyan", "duracao": "Liberado pela empresa"},
    "nr12maquinas": {"icone": "query_stats", "status": "purple", "duracao": "Liberado pela empresa"},
    "nr20_instalacoes": {"icone": "local_gas_station", "status": "warning", "duracao": "Liberado pela empresa"},
    "nr33_espaco_confinado": {"icone": "sensor_door", "status": "purple", "duracao": "Liberado pela empresa"},
    "rti": {"icone": "electric_bolt", "status": "warning", "duracao": "Liberado pela empresa"},
    "pie": {"icone": "power", "status": "warning", "duracao": "Liberado pela empresa"},
    "spda": {"icone": "electric_bolt", "status": "warning", "duracao": "Liberado pela empresa"},
    "cbmgo": {"icone": "fire_extinguisher", "status": "cyan", "duracao": "Liberado pela empresa"},
    "avcb": {"icone": "local_fire_department", "status": "cyan", "duracao": "Liberado pela empresa"},
    "nr35_linha_vida": {"icone": "construction", "status": "purple", "duracao": "Liberado pela empresa"},
    "nr35_montagem": {"icone": "handyman", "status": "purple", "duracao": "Liberado pela empresa"},
    "nr35_ponto_ancoragem": {"icone": "anchor", "status": "purple", "duracao": "Liberado pela empresa"},
    "nr35_projeto": {"icone": "description", "status": "purple", "duracao": "Liberado pela empresa"},
    "padrao": {"icone": "tune", "status": "purple", "duracao": "Uso livre"},
}


@dataclass(frozen=True, slots=True)
class ContextoPreferenciaModoEntradaUsuario:
    entry_mode_preference: str
    remember_last_case_mode: bool
    last_case_mode: str | None = None

def email_valido_basico(email: str) -> bool:
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def normalizar_telefone(telefone: str) -> str:
    valor = str(telefone or "").strip()
    if not valor:
        return ""
    valor = re.sub(r"[^0-9()+\-\s]", "", valor)
    return valor[:30]


def _registro(valor: object) -> dict[str, object]:
    if isinstance(valor, dict):
        return valor
    return {}


def _normalizar_bool(valor: object, padrao: bool) -> bool:
    return valor if isinstance(valor, bool) else padrao


def _normalizar_texto_opcao(valor: object, opcoes: set[str], padrao: str) -> str:
    texto = str(valor or "").strip()
    if texto in opcoes:
        return texto
    return padrao


def _normalizar_entry_mode_preference(valor: object, padrao: str) -> str:
    try:
        return EntryModePreference.normalizar(valor)
    except ValueError:
        return padrao


def _normalizar_entry_mode_effective_opcional(valor: object) -> str | None:
    if valor in (None, ""):
        return None
    try:
        return EntryModeEffective.normalizar(valor)
    except ValueError:
        return None


def normalizar_configuracoes_criticas_mobile(payload: object) -> dict[str, dict[str, object]]:
    base = _registro(payload)
    notificacoes_raw = _registro(base.get("notificacoes"))
    privacidade_raw = _registro(base.get("privacidade"))
    permissoes_raw = _registro(base.get("permissoes"))
    experiencia_ia_raw = _registro(base.get("experiencia_ia"))

    notificacoes: dict[str, object] = {
        "notifica_respostas": _normalizar_bool(
            notificacoes_raw.get("notifica_respostas"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["notificacoes"]["notifica_respostas"]),
        ),
        "notifica_push": _normalizar_bool(
            notificacoes_raw.get("notifica_push"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["notificacoes"]["notifica_push"]),
        ),
        "som_notificacao": _normalizar_texto_opcao(
            notificacoes_raw.get("som_notificacao"),
            SONS_NOTIFICACAO_PERMITIDOS,
            str(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["notificacoes"]["som_notificacao"]),
        ),
        "vibracao_ativa": _normalizar_bool(
            notificacoes_raw.get("vibracao_ativa"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["notificacoes"]["vibracao_ativa"]),
        ),
        "emails_ativos": _normalizar_bool(
            notificacoes_raw.get("emails_ativos"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["notificacoes"]["emails_ativos"]),
        ),
    }

    privacidade: dict[str, object] = {
        "mostrar_conteudo_notificacao": _normalizar_bool(
            privacidade_raw.get("mostrar_conteudo_notificacao"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["privacidade"]["mostrar_conteudo_notificacao"]),
        ),
        "ocultar_conteudo_bloqueado": _normalizar_bool(
            privacidade_raw.get("ocultar_conteudo_bloqueado"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["privacidade"]["ocultar_conteudo_bloqueado"]),
        ),
        "mostrar_somente_nova_mensagem": _normalizar_bool(
            privacidade_raw.get("mostrar_somente_nova_mensagem"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["privacidade"]["mostrar_somente_nova_mensagem"]),
        ),
        "salvar_historico_conversas": _normalizar_bool(
            privacidade_raw.get("salvar_historico_conversas"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["privacidade"]["salvar_historico_conversas"]),
        ),
        "compartilhar_melhoria_ia": _normalizar_bool(
            privacidade_raw.get("compartilhar_melhoria_ia"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["privacidade"]["compartilhar_melhoria_ia"]),
        ),
        "retencao_dados": _normalizar_texto_opcao(
            privacidade_raw.get("retencao_dados"),
            RETENCAO_DADOS_PERMITIDA,
            str(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["privacidade"]["retencao_dados"]),
        ),
    }

    permissoes: dict[str, object] = {
        "microfone_permitido": _normalizar_bool(
            permissoes_raw.get("microfone_permitido"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["permissoes"]["microfone_permitido"]),
        ),
        "camera_permitida": _normalizar_bool(
            permissoes_raw.get("camera_permitida"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["permissoes"]["camera_permitida"]),
        ),
        "arquivos_permitidos": _normalizar_bool(
            permissoes_raw.get("arquivos_permitidos"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["permissoes"]["arquivos_permitidos"]),
        ),
        "notificacoes_permitidas": _normalizar_bool(
            permissoes_raw.get("notificacoes_permitidas"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["permissoes"]["notificacoes_permitidas"]),
        ),
        "biometria_permitida": _normalizar_bool(
            permissoes_raw.get("biometria_permitida"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["permissoes"]["biometria_permitida"]),
        ),
    }

    experiencia_ia: dict[str, object] = {
        "modelo_ia": _normalizar_texto_opcao(
            experiencia_ia_raw.get("modelo_ia"),
            MODELOS_IA_PERMITIDOS,
            str(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["experiencia_ia"]["modelo_ia"]),
        ),
        "entry_mode_preference": _normalizar_entry_mode_preference(
            experiencia_ia_raw.get("entry_mode_preference"),
            str(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["experiencia_ia"]["entry_mode_preference"]),
        ),
        "remember_last_case_mode": _normalizar_bool(
            experiencia_ia_raw.get("remember_last_case_mode"),
            bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["experiencia_ia"]["remember_last_case_mode"]),
        ),
    }

    return {
        "notificacoes": notificacoes,
        "privacidade": privacidade,
        "permissoes": permissoes,
        "experiencia_ia": experiencia_ia,
    }


def serializar_preferencias_mobile_usuario(preferencia: PreferenciaMobileUsuario | None) -> dict[str, dict[str, object]]:
    if not preferencia:
        return normalizar_configuracoes_criticas_mobile(CONFIGURACOES_CRITICAS_MOBILE_PADRAO)
    return normalizar_configuracoes_criticas_mobile(
        {
            "notificacoes": preferencia.notificacoes_json,
            "privacidade": preferencia.privacidade_json,
            "permissoes": preferencia.permissoes_json,
            "experiencia_ia": preferencia.experiencia_ia_json,
        }
    )


def serializar_perfil_usuario(usuario: Usuario) -> dict[str, str]:
    return {
        "nome_completo": str(usuario.nome_completo or "").strip(),
        "email": str(usuario.email or "").strip(),
        "telefone": str(getattr(usuario, "telefone", "") or "").strip(),
        "foto_perfil_url": str(getattr(usuario, "foto_perfil_url", "") or "").strip(),
        "empresa_nome": str(getattr(getattr(usuario, "empresa", None), "nome_fantasia", "") or "Sua empresa").strip(),
    }


def serializar_usuario_mobile(usuario: Usuario) -> dict[str, object]:
    perfil = serializar_perfil_usuario(usuario)
    tenant_policy = getattr(getattr(usuario, "empresa", None), "admin_cliente_policy_json", None)
    policy_summary = summarize_tenant_admin_policy(tenant_policy)
    operational_package = summarize_tenant_admin_operational_package(tenant_policy)
    allowed_portals = list(usuario_portais_habilitados(usuario))
    return {
        "id": int(usuario.id),
        "nome_completo": perfil["nome_completo"],
        "email": perfil["email"],
        "telefone": perfil["telefone"],
        "foto_perfil_url": perfil["foto_perfil_url"],
        "empresa_nome": perfil["empresa_nome"],
        "empresa_id": int(usuario.empresa_id or 0),
        "nivel_acesso": int(usuario.nivel_acesso),
        "allowed_portals": allowed_portals,
        "allowed_portal_labels": [
            tenant_admin_user_portal_label(portal) for portal in allowed_portals
        ],
        "commercial_operating_model": str(
            policy_summary.get("operating_model") or "standard"
        ),
        "commercial_operating_model_label": str(
            policy_summary.get("operating_model_label") or "Operação padrão"
        ),
        "identity_runtime_mode": str(
            operational_package.get("identity_runtime_mode")
            or "standard_role_accounts"
        ),
        "identity_runtime_note": str(
            operational_package.get("identity_runtime_note") or ""
        ),
        "portal_switch_links": usuario_portal_switch_links(usuario),
        "admin_ceo_governed": bool(
            policy_summary.get("admin_cliente_governs_operational_profile", True)
        ),
        "tenant_access_policy": tenant_access_policy_for_user(usuario),
    }


def _caminho_foto_perfil_local(url_foto: str | None) -> Path | None:
    valor = str(url_foto or "").strip()
    if not valor.startswith("/static/uploads/perfis/"):
        return None

    base = PASTA_FOTOS_PERFIL.resolve()
    caminho = Path(valor.lstrip("/")).resolve()
    if base == caminho or base in caminho.parents:
        return caminho
    return None


def _remover_foto_perfil_antiga(url_foto: str | None) -> None:
    caminho = _caminho_foto_perfil_local(url_foto)
    if not caminho:
        return
    try:
        if caminho.exists() and caminho.is_file():
            caminho.unlink()
    except Exception:
        logger.warning("Falha ao remover foto de perfil antiga.", exc_info=True)


def atualizar_nome_sessao_inspetor(request: Request, usuario: Usuario) -> None:
    dados_sessao = obter_dados_sessao_portal(request.session, portal=PORTAL_INSPETOR)
    token = dados_sessao.get("token")
    if not token:
        return

    definir_sessao_portal(
        request.session,
        portal=PORTAL_INSPETOR,
        token=token,
        usuario_id=usuario.id,
        empresa_id=usuario.empresa_id,
        nivel_acesso=nivel_acesso_sessao_portal(PORTAL_INSPETOR) or int(usuario.nivel_acesso),
        nome=usuario_nome(usuario),
    )


def atualizar_perfil_usuario_em_banco(
    *,
    usuario: Usuario,
    banco: Session,
    nome_completo: str,
    email_bruto: str,
    telefone_bruto: str,
) -> None:
    nome = str(nome_completo or "").strip()
    email = normalizar_email(str(email_bruto or ""))
    telefone = normalizar_telefone(str(telefone_bruto or ""))

    if len(nome) < 3:
        raise HTTPException(status_code=400, detail="Informe um nome com pelo menos 3 caracteres.")

    if not email or not email_valido_basico(email):
        raise HTTPException(status_code=400, detail="Informe um e-mail válido.")

    usuario_conflito = banco.scalar(
        select(Usuario).where(
            Usuario.email == email,
            Usuario.id != usuario.id,
        )
    )
    if usuario_conflito:
        raise HTTPException(status_code=409, detail="Este e-mail já está em uso por outro usuário.")

    usuario.nome_completo = nome[:150]
    usuario.email = email[:254]
    usuario.telefone = telefone or None

    banco.flush()
    banco.refresh(usuario)


async def atualizar_foto_perfil_usuario_em_banco(
    *,
    usuario: Usuario,
    banco: Session,
    foto: UploadFile,
) -> None:
    mime = str(foto.content_type or "").strip().lower()
    if mime not in MIME_FOTO_PERMITIDOS:
        raise HTTPException(status_code=415, detail="Formato inválido. Use PNG, JPG ou WebP.")

    conteudo = await foto.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo de foto vazio.")
    if len(conteudo) > MAX_FOTO_PERFIL_BYTES:
        raise HTTPException(status_code=413, detail="A foto deve ter no máximo 4MB.")

    extensao_por_mime = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    extensao = extensao_por_mime.get(mime, ".jpg")

    pasta_empresa = PASTA_FOTOS_PERFIL / str(usuario.empresa_id)
    pasta_empresa.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"user_{usuario.id}_{uuid.uuid4().hex[:16]}{extensao}"
    caminho_destino = pasta_empresa / nome_arquivo
    caminho_destino.write_bytes(conteudo)

    _remover_foto_perfil_antiga(getattr(usuario, "foto_perfil_url", None))
    usuario.foto_perfil_url = f"/static/uploads/perfis/{usuario.empresa_id}/{nome_arquivo}"
    banco.flush()
    banco.refresh(usuario)


def obter_preferencia_mobile_usuario(banco: Session, *, usuario_id: int) -> PreferenciaMobileUsuario | None:
    return banco.scalar(select(PreferenciaMobileUsuario).where(PreferenciaMobileUsuario.usuario_id == int(usuario_id)))


def obter_contexto_preferencia_modo_entrada_usuario(
    banco: Session,
    *,
    usuario_id: int,
) -> ContextoPreferenciaModoEntradaUsuario:
    preferencia = obter_preferencia_mobile_usuario(banco, usuario_id=int(usuario_id))
    experiencia_ia = _registro(serializar_preferencias_mobile_usuario(preferencia).get("experiencia_ia"))
    entry_mode_preference = _normalizar_entry_mode_preference(
        experiencia_ia.get("entry_mode_preference"),
        str(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["experiencia_ia"]["entry_mode_preference"]),
    )
    remember_last_case_mode = _normalizar_bool(
        experiencia_ia.get("remember_last_case_mode"),
        bool(CONFIGURACOES_CRITICAS_MOBILE_PADRAO["experiencia_ia"]["remember_last_case_mode"]),
    )

    last_case_mode: str | None = None
    if remember_last_case_mode:
        ultimo_modo = banco.scalar(
            select(Laudo.entry_mode_effective)
            .where(
                Laudo.usuario_id == int(usuario_id),
                Laudo.entry_mode_effective.is_not(None),
            )
            .order_by(func.coalesce(Laudo.atualizado_em, Laudo.criado_em).desc(), Laudo.id.desc())
            .limit(1)
        )
        last_case_mode = _normalizar_entry_mode_effective_opcional(ultimo_modo)

    return ContextoPreferenciaModoEntradaUsuario(
        entry_mode_preference=entry_mode_preference,
        remember_last_case_mode=remember_last_case_mode,
        last_case_mode=last_case_mode,
    )


def salvar_configuracoes_criticas_mobile_usuario(
    banco: Session,
    *,
    usuario: Usuario,
    payload: object,
) -> dict[str, dict[str, object]]:
    configuracoes = normalizar_configuracoes_criticas_mobile(payload)
    preferencia = obter_preferencia_mobile_usuario(banco, usuario_id=int(usuario.id))
    if not preferencia:
        preferencia = PreferenciaMobileUsuario(usuario_id=usuario.id)
        banco.add(preferencia)

    preferencia.notificacoes_json = configuracoes["notificacoes"]
    preferencia.privacidade_json = configuracoes["privacidade"]
    preferencia.permissoes_json = configuracoes["permissoes"]
    preferencia.experiencia_ia_json = configuracoes["experiencia_ia"]
    banco.flush()
    banco.refresh(preferencia)

    logger.info(
        "Preferencias mobile criticas atualizadas | usuario_id=%s | notificacoes=%s | privacidade=%s | permissoes=%s | experiencia_ia=%s",
        usuario.id,
        preferencia.notificacoes_json,
        preferencia.privacidade_json,
        preferencia.permissoes_json,
        preferencia.experiencia_ia_json,
    )

    return serializar_preferencias_mobile_usuario(preferencia)


def listar_cards_laudos_mobile_inspetor(
    banco: Session,
    *,
    request: Request | None = None,
    usuario: Usuario,
    limite: int = 30,
) -> list[dict[str, object]]:
    laudos = list(
        banco.scalars(
            select(Laudo)
            .where(
                Laudo.empresa_id == usuario.empresa_id,
                Laudo.usuario_id == usuario.id,
            )
            .order_by(func.coalesce(Laudo.atualizado_em, Laudo.criado_em).desc(), Laudo.id.desc())
            .limit(max(1, int(limite)))
        ).all()
    )
    cache = criar_cache_resumo_laudos()
    precarregar_interacoes_laudos(
        banco,
        [getattr(laudo, "id", None) for laudo in laudos],
        cache=cache,
    )
    laudos_visiveis = [
        laudo
        for laudo in laudos
        if laudo_possui_historico_visivel(banco, laudo, cache=cache) or laudo.status_revisao != "rascunho"
    ]
    official_issue_summaries = _load_mobile_official_issue_alerts(
        banco,
        laudos=laudos_visiveis,
    )
    cards_legados = []
    for laudo in laudos_visiveis:
        card = {
            **serializar_card_laudo(banco, laudo, cache=cache),
            "report_pack_draft": getattr(laudo, "report_pack_draft_json", None),
        }
        official_issue_summary = official_issue_summaries.get(int(laudo.id))
        if official_issue_summary is not None:
            card["official_issue_summary"] = official_issue_summary
        cards_legados.append(card)
    if not v2_android_case_adapter_enabled():
        return cards_legados

    resultados_adapter: list[dict[str, object]] = []
    cards_publicos: list[dict[str, object]] = []
    compat_count = 0

    for laudo, card in zip(laudos_visiveis, cards_legados, strict=False):
        provenance_summary = None
        policy_decision = None
        document_facade = None
        card_context = card if isinstance(card, dict) else {}

        if v2_provenance_enabled():
            try:
                message_counters = load_message_origin_counters(
                    banco,
                    laudo_id=int(getattr(laudo, "id", 0) or 0) or None,
                )
                provenance_summary = build_inspector_content_origin_summary(
                    laudo=laudo,
                    message_counters=message_counters,
                    has_active_report=True,
                )
            except Exception:
                logger.debug("Falha ao derivar provenance mobile no V2.", exc_info=True)

        legacy_payload = {
            "estado": obter_estado_api_laudo(banco, laudo, cache=cache),
            "laudo_id": int(laudo.id),
            "status_card": card["status_card"],
            "permite_reabrir": card["permite_reabrir"],
            "tem_interacao": laudo_tem_interacao(banco, int(laudo.id), cache=cache),
            "laudo_card": card,
            "case_lifecycle_status": card_context.get("case_lifecycle_status"),
            "case_workflow_mode": card_context.get("case_workflow_mode"),
            "active_owner_role": card_context.get("active_owner_role"),
            "allowed_next_lifecycle_statuses": card_context.get("allowed_next_lifecycle_statuses"),
            "allowed_lifecycle_transitions": card_context.get("allowed_lifecycle_transitions"),
            "allowed_surface_actions": card_context.get("allowed_surface_actions"),
        }
        runtime_bundle = build_technical_case_context_bundle(
            banco=banco,
            usuario=usuario,
            laudo=laudo,
            legacy_payload=legacy_payload,
            source_channel="android_api",
            template_key=getattr(laudo, "tipo_template", None),
            family_key=getattr(laudo, "catalog_family_key", None),
            variant_key=getattr(laudo, "catalog_variant_key", None),
            laudo_type=getattr(laudo, "tipo_template", None),
            document_type=getattr(laudo, "tipo_template", None),
            provenance_summary=provenance_summary,
            current_review_status=getattr(laudo, "status_revisao", None),
            has_form_data=bool(getattr(laudo, "dados_formulario", None)),
            has_ai_draft=bool(str(getattr(laudo, "parecer_ia", "") or "").strip()),
            report_pack_draft=getattr(laudo, "report_pack_draft_json", None),
            include_policy_decision=v2_policy_engine_enabled(),
            include_document_facade=v2_document_facade_enabled(),
            attach_document_shadow=v2_document_shadow_enabled(),
            allow_partial_failures=True,
        )
        case_snapshot = runtime_bundle.case_snapshot
        assert case_snapshot is not None
        policy_decision = runtime_bundle.policy_decision
        document_facade = runtime_bundle.document_facade

        inspector_projection = build_inspector_case_view_projection(
            case_snapshot=case_snapshot,
            actor_id=usuario.id,
            actor_role=actor_role_from_user(usuario),
            source_channel="android_api",
            allows_edit=bool(card.get("permite_edicao")),
            has_interaction=bool(legacy_payload["tem_interacao"]),
            report_types={str(card.get("tipo_template") or "padrao"): nome_template_humano(str(card.get("tipo_template") or "padrao"))},
            laudo_card=card,
            policy_decision=policy_decision,
            document_facade=document_facade,
        )
        adapted = adapt_inspector_case_view_projection_to_android_case(
            projection=inspector_projection,
            expected_legacy_payload=card,
        )

        if adapted.compatibility.compatible:
            compat_count += 1
            cards_publicos.append(adapted.payload)
        else:
            logger.debug(
                "V2 android case adapter divergiu | laudo_id=%s | divergences=%s",
                laudo.id,
                ",".join(adapted.compatibility.divergences),
            )
            cards_publicos.append(card)

        resultados_adapter.append(
            {
                "laudo_id": int(laudo.id),
                "projection": inspector_projection.model_dump(mode="python"),
                "compatible": adapted.compatibility.compatible,
                "divergences": adapted.compatibility.divergences,
                "used_projection": adapted.compatibility.compatible,
                "provenance": (
                    provenance_summary.model_dump(mode="python")
                    if provenance_summary is not None
                    else None
                ),
                "policy": (
                    policy_decision.summary.model_dump(mode="python")
                    if policy_decision is not None
                    else None
                ),
                "document_facade": (
                    document_facade.model_dump(mode="python")
                    if document_facade is not None
                    else None
                ),
                "android_adapter": adapted.model_dump(mode="python"),
            }
        )

    if request is not None:
        request.state.v2_android_case_adapter_results = resultados_adapter
        request.state.v2_android_case_adapter_summary = {
            "total": len(resultados_adapter),
            "compatible": compat_count,
            "divergent": len(resultados_adapter) - compat_count,
            "used_projection": compat_count,
        }

    return cards_publicos


def _build_mobile_official_issue_alert(
    record: EmissaoOficialLaudo | None,
) -> dict[str, object] | None:
    payload = serialize_official_issue_record(record)
    if not isinstance(payload, dict) or not bool(payload.get("primary_pdf_diverged")):
        return None

    frozen_version = str(payload.get("primary_pdf_storage_version") or "").strip()
    current_version = str(payload.get("current_primary_pdf_storage_version") or "").strip()
    version_bits = []
    if frozen_version:
        version_bits.append(f"Emitido {frozen_version}")
    if current_version:
        version_bits.append(f"Atual {current_version}")
    detail = "PDF emitido divergente"
    if version_bits:
        detail = f"{detail} · {' · '.join(version_bits)}"

    return {
        "label": "Reemissão recomendada",
        "detail": detail,
        "issue_number": payload.get("issue_number"),
        "issue_state_label": payload.get("issue_state_label"),
        "primary_pdf_diverged": True,
        "primary_pdf_storage_version": frozen_version or None,
        "current_primary_pdf_storage_version": current_version or None,
    }


def _load_mobile_official_issue_alerts(
    banco: Session,
    *,
    laudos: list[Laudo],
) -> dict[int, dict[str, object]]:
    laudo_ids = [int(getattr(laudo, "id", 0) or 0) for laudo in laudos if int(getattr(laudo, "id", 0) or 0) > 0]
    if not laudo_ids:
        return {}

    records = list(
        banco.scalars(
            select(EmissaoOficialLaudo)
            .options(selectinload(EmissaoOficialLaudo.laudo))
            .where(
                EmissaoOficialLaudo.laudo_id.in_(laudo_ids),
                EmissaoOficialLaudo.issue_state == "issued",
            )
            .order_by(
                EmissaoOficialLaudo.laudo_id.asc(),
                EmissaoOficialLaudo.issued_at.desc(),
                EmissaoOficialLaudo.id.desc(),
            )
        ).all()
    )

    alerts_by_laudo: dict[int, dict[str, object]] = {}
    seen_laudo_ids: set[int] = set()
    for record in records:
        laudo_id = int(getattr(record, "laudo_id", 0) or 0)
        if laudo_id <= 0 or laudo_id in seen_laudo_ids:
            continue
        seen_laudo_ids.add(laudo_id)
        alert_payload = _build_mobile_official_issue_alert(record)
        if alert_payload is not None:
            alerts_by_laudo[laudo_id] = alert_payload
    return alerts_by_laudo


def _build_portal_governance_summary(
    official_issue_summaries: dict[int, dict[str, object]] | None,
) -> dict[str, object]:
    total = len(official_issue_summaries or {})
    resumo = f"{total} {_pluralizar_portal(total, 'caso com reemissão recomendada', 'casos com reemissão recomendada')}"
    detalhe = (
        "PDF oficial divergente detectado no ponto de entrada do inspetor."
        if total == 1
        else "PDF oficial divergente detectado em casos já emitidos do inspetor."
    )
    return {
        "visible": total > 0,
        "reissue_recommended_count": total,
        "label": resumo,
        "detail": detalhe,
    }


def listar_laudos_recentes_portal_inspetor(
    banco: Session,
    *,
    request: Request | None = None,
    usuario: Usuario,
    limite_consulta: int = 40,
    limite_resultado: int = 20,
    resumo_cache: CacheResumoLaudoRequest | None = None,
) -> list[Laudo]:
    cache = resumo_cache or criar_cache_resumo_laudos()
    laudos_consulta = list(
        banco.scalars(
            select(Laudo)
            .where(
                Laudo.empresa_id == usuario.empresa_id,
                Laudo.usuario_id == usuario.id,
            )
            .order_by(
                Laudo.pinado.desc(),
                Laudo.criado_em.desc(),
            )
            .limit(max(1, int(limite_consulta)))
        ).all()
    )
    precarregar_interacoes_laudos(
        banco,
        [getattr(laudo, "id", None) for laudo in laudos_consulta],
        cache=cache,
    )

    laudos_recentes: list[Laudo] = []
    for laudo in laudos_consulta:
        if not (
            laudo_possui_historico_visivel(banco, laudo, cache=cache)
            or _laudo_possui_contexto_inicial_portal(request, laudo)
        ):
            continue
        resumo_card = serializar_card_laudo(banco, laudo, cache=cache)
        setattr(laudo, "card_status", resumo_card["status_card"])
        setattr(laudo, "card_status_label", resumo_card["status_card_label"])
        laudos_recentes.append(laudo)
        if len(laudos_recentes) >= max(1, int(limite_resultado)):
            break
    return laudos_recentes


def _dados_formulario_laudo(laudo: Laudo) -> dict[str, object]:
    dados = getattr(laudo, "dados_formulario", None)
    return dados if isinstance(dados, dict) else {}


def _dados_formulario_portal(
    request: Request | None,
    laudo: Laudo,
) -> dict[str, object]:
    raw_session_data = obter_contexto_inicial_laudo_sessao(
        request,
        laudo_id=getattr(laudo, "id", None),
    ) or {}
    dados_sessao: dict[str, object] = {
        str(key): value for key, value in raw_session_data.items()
    }
    dados_banco = _dados_formulario_laudo(laudo)
    if not dados_sessao:
        return dados_banco
    if not dados_banco:
        return dados_sessao
    merged_payload: dict[str, object] = {
        **dados_sessao,
        **dados_banco,
    }
    return merged_payload


def _laudo_possui_contexto_inicial_portal(
    request: Request | None,
    laudo: Laudo,
) -> bool:
    dados = _dados_formulario_portal(request, laudo)
    return bool(
        _texto_formulario(dados, "local_inspecao", "equipamento", "nome_equipamento", "nome_inspecao")
        or _texto_formulario(dados, "cliente", "empresa")
        or _texto_formulario(dados, "unidade", "planta", "setor")
        or _texto_formulario(dados, "objetivo", "contexto_inicial")
    )


def _texto_formulario(dados: dict[str, object], *chaves: str) -> str:
    for chave in chaves:
        valor = str(dados.get(chave) or "").strip()
        if valor:
            return valor
    return ""


def _tempo_relativo_portal(valor: datetime | None) -> str:
    if not valor:
        return "agora"

    referencia = valor.astimezone()
    agora = datetime.now(referencia.tzinfo)
    diff_segundos = max(0, int((agora - referencia).total_seconds()))
    diff_minutos = max(1, round(diff_segundos / 60))

    if diff_minutos < 60:
        return f"há {diff_minutos}min"

    diff_horas = round(diff_minutos / 60)
    if diff_horas < 24:
        return f"há {diff_horas} horas"

    diff_dias = round(diff_horas / 24)
    if diff_dias == 1:
        return "ontem"

    return f"há {diff_dias} dias"


def _pluralizar_portal(total: int, singular: str, plural: str) -> str:
    return singular if int(total) == 1 else plural


def _status_portal_visual(status_card: str) -> tuple[str, str]:
    mapa = {
        "aberto": ("EM COLETA", "coleta"),
        "aguardando": ("MESA", "mesa"),
        "ajustes": ("AJUSTES", "mesa"),
        "aprovado": ("CONCLUÍDO", "concluido"),
    }
    return mapa.get(str(status_card or "").strip().lower(), ("EM COLETA", "coleta"))


def _evidencias_por_laudo(
    banco: Session,
    *,
    laudo_ids: list[int],
) -> dict[int, int]:
    ids_validos = [int(laudo_id) for laudo_id in laudo_ids if int(laudo_id or 0) > 0]
    if not ids_validos:
        return {}

    linhas = (
        banco.query(MensagemLaudo.laudo_id, func.count(MensagemLaudo.id))
        .filter(
            MensagemLaudo.laudo_id.in_(ids_validos),
            MensagemLaudo.tipo == TipoMensagem.USER.value,
        )
        .group_by(MensagemLaudo.laudo_id)
        .all()
    )
    return {int(laudo_id): int(total or 0) for laudo_id, total in linhas}


def serializar_laudo_portal_inspetor(
    banco: Session,
    *,
    laudo: Laudo,
    request: Request | None = None,
    empresa_nome: str = "",
    evidencias_por_laudo: dict[int, int] | None = None,
    resumo_cache: CacheResumoLaudoRequest | None = None,
    official_issue_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    dados = _dados_formulario_portal(request, laudo)
    resumo = serializar_card_laudo(banco, laudo, cache=resumo_cache)
    status_card = str(resumo.get("status_card") or "").strip().lower() or "aberto"
    if status_card == "oculto" and _laudo_possui_contexto_inicial_portal(request, laudo):
        status_card = "aberto"
    status_card_label = str(resumo.get("status_card_label") or "").strip() or CARD_STATUS_LABELS.get(status_card, "Laudo")
    badge, status_visual = _status_portal_visual(status_card)
    referencia_tempo = getattr(laudo, "atualizado_em", None) or getattr(laudo, "criado_em", None)
    referencia_local = referencia_tempo.astimezone() if referencia_tempo else None
    data_iso = referencia_local.strftime("%Y-%m-%d") if referencia_local else ""
    data_br = referencia_local.strftime("%d/%m/%Y") if referencia_local else ""

    titulo = (
        _texto_formulario(dados, "local_inspecao", "equipamento", "nome_equipamento", "nome_inspecao")
        or str(getattr(laudo, "setor_industrial", "") or "").strip()
        or nome_template_humano(str(getattr(laudo, "tipo_template", "padrao") or "padrao"))
    )
    cliente = _texto_formulario(dados, "cliente", "empresa")
    unidade = _texto_formulario(dados, "unidade", "planta", "setor")
    subtitulo = " - ".join([parte for parte in [cliente, unidade] if parte]).strip()
    if not subtitulo:
        subtitulo = str(empresa_nome or "").strip() or nome_template_humano(str(getattr(laudo, "tipo_template", "padrao") or "padrao"))

    evidencias = int((evidencias_por_laudo or {}).get(int(laudo.id), 0) or 0)
    if evidencias <= 0 and str(getattr(laudo, "primeira_mensagem", "") or "").strip():
        evidencias = 1

    payload = {
        "id": int(laudo.id),
        "titulo": titulo,
        "subtitulo": subtitulo,
        "tempo": _tempo_relativo_portal(referencia_tempo),
        "badge": badge,
        "status": status_visual,
        "pinado": bool(resumo.get("pinado", False)),
        "status_revisao": str(resumo.get("status_revisao") or ""),
        "card_status": status_card,
        "card_status_label": status_card_label or badge,
        "data_iso": data_iso,
        "data_br": data_br,
        "evidencias": f"{evidencias} {_pluralizar_portal(evidencias, 'evidência', 'evidências')}",
        "tipo": str(getattr(laudo, "tipo_template", "padrao") or "padrao"),
        "workspace_title": titulo,
        "workspace_subtitle": f"{subtitulo} • Iniciado {_tempo_relativo_portal(getattr(laudo, 'criado_em', None))}",
        "workspace_status": badge,
        "entry_mode_preference": str(resumo.get("entry_mode_preference") or ""),
        "entry_mode_effective": str(resumo.get("entry_mode_effective") or ""),
        "entry_mode_reason": str(resumo.get("entry_mode_reason") or ""),
    }
    if official_issue_summary is not None:
        payload["official_issue_summary"] = official_issue_summary
    return payload


def montar_contexto_portal_inspetor(
    banco: Session,
    *,
    request: Request | None = None,
    usuario: Usuario,
    laudos_recentes: list[Laudo] | None = None,
    resumo_cache: CacheResumoLaudoRequest | None = None,
) -> dict[str, object]:
    cache = resumo_cache or criar_cache_resumo_laudos()
    empresa_nome = str(getattr(getattr(usuario, "empresa", None), "nome_fantasia", "") or "").strip()
    tenant_access_policy = tenant_access_policy_for_user(usuario)
    contexto_modo_entrada = obter_contexto_preferencia_modo_entrada_usuario(
        banco,
        usuario_id=int(usuario.id),
    )
    laudos_todos = list(
        banco.scalars(
            select(Laudo)
            .where(
                Laudo.empresa_id == usuario.empresa_id,
                Laudo.usuario_id == usuario.id,
            )
            .order_by(
                Laudo.pinado.desc(),
                func.coalesce(Laudo.atualizado_em, Laudo.criado_em).desc(),
                Laudo.id.desc(),
            )
        ).all()
    )
    precarregar_interacoes_laudos(
        banco,
        [getattr(laudo, "id", None) for laudo in laudos_todos],
        cache=cache,
    )

    laudos_visiveis = [
        laudo
        for laudo in laudos_todos
        if (
            laudo_possui_historico_visivel(banco, laudo, cache=cache)
            or _laudo_possui_contexto_inicial_portal(request, laudo)
        )
    ]
    evidencias_map = _evidencias_por_laudo(
        banco,
        laudo_ids=[int(laudo.id) for laudo in laudos_visiveis],
    )
    official_issue_summaries = _load_mobile_official_issue_alerts(
        banco,
        laudos=laudos_visiveis,
    )

    agora = datetime.now().astimezone()
    ativos = 0
    aguardando = 0
    concluidos_mes = 0
    usos_modelos_mes: Counter[str] = Counter()

    for laudo in laudos_visiveis:
        resumo = serializar_card_laudo(banco, laudo, cache=cache)
        status_card = str(resumo.get("status_card") or "").strip().lower()
        tipo_template = str(getattr(laudo, "tipo_template", "padrao") or "padrao")
        referencia_mes = getattr(laudo, "atualizado_em", None) or getattr(laudo, "criado_em", None)
        if referencia_mes:
            referencia_local = referencia_mes.astimezone()
            if referencia_local.year == agora.year and referencia_local.month == agora.month:
                usos_modelos_mes[tipo_template] += 1

        if status_card in {"aberto", "ajustes"}:
            ativos += 1
        elif status_card == "aguardando":
            aguardando += 1

        if status_card == "aprovado" and referencia_mes:
            referencia_local = referencia_mes.astimezone()
            if referencia_local.year == agora.year and referencia_local.month == agora.month:
                concluidos_mes += 1

    laudos_base = [
        laudo
        for laudo in (laudos_recentes or laudos_visiveis[:20])
        if (
            laudo_possui_historico_visivel(banco, laudo, cache=cache)
            or _laudo_possui_contexto_inicial_portal(request, laudo)
        )
    ]
    official_issue_summaries_portal = {
        int(laudo.id): official_issue_summaries[int(laudo.id)]
        for laudo in laudos_base
        if int(laudo.id) in official_issue_summaries
    }
    laudos_portal_cards = [
        serializar_laudo_portal_inspetor(
            banco,
            laudo=laudo,
            request=request,
            empresa_nome=empresa_nome,
            evidencias_por_laudo=evidencias_map,
            resumo_cache=cache,
            official_issue_summary=official_issue_summaries_portal.get(int(laudo.id)),
        )
        for laudo in laudos_base
    ]

    template_snapshot = build_tenant_template_option_snapshot(banco, empresa_id=int(usuario.empresa_id))
    tipos_template_portal = list(template_snapshot.get("options") or [])

    modelos_portal = []
    if bool(template_snapshot.get("governed_mode")):
        for opcao in tipos_template_portal:
            runtime_template_code = str(opcao.get("runtime_template_code") or "padrao").strip().lower() or "padrao"
            meta_visual = _MODELO_PORTAL_RUNTIME_META.get(runtime_template_code, _MODELO_PORTAL_RUNTIME_META["padrao"])
            usos = int(usos_modelos_mes.get(runtime_template_code, 0))
            modelos_portal.append(
                {
                    "titulo": str(opcao.get("variant_label") or opcao.get("label") or nome_template_humano(runtime_template_code)),
                    "badge": "LIBERADO",
                    "descricao": str(opcao.get("offer_name") or opcao.get("family_label") or nome_template_humano(runtime_template_code)),
                    "duracao": meta_visual["duracao"],
                    "icone": meta_visual["icone"],
                    "status": meta_visual["status"],
                    "tipo": str(opcao.get("value") or runtime_template_code),
                    "runtime_tipo": runtime_template_code,
                    "preprompt": (
                        f"Inicie {str(opcao.get('label') or nome_template_humano(runtime_template_code))}. "
                        "Quero checklist técnico, riscos, não conformidades e plano de ação."
                    ),
                    "meta": f"{usos} {_pluralizar_portal(usos, 'uso', 'usos')} este mês • {str(opcao.get('group_label') or meta_visual['duracao'])}",
                }
            )
    else:
        for modelo in MODELOS_TECNICOS_PORTAL:
            usos = int(usos_modelos_mes.get(str(modelo["tipo"]), 0))
            modelos_portal.append(
                {
                    **modelo,
                    "runtime_tipo": str(modelo["tipo"]),
                    "meta": f"{usos} {_pluralizar_portal(usos, 'uso', 'usos')} este mês • {modelo['duracao']}",
                }
            )

    return {
        "cards_status": [
            {"valor": str(ativos), "label": "Inspeções Ativas", "icone": "description", "status": "cyan"},
            {"valor": str(aguardando), "label": "Aguardando Mesa", "icone": "hourglass_top", "status": "purple"},
            {"valor": str(concluidos_mes), "label": "Concluídos no Mês", "icone": "trending_up", "status": "success"},
        ],
        "laudos_sidebar": laudos_portal_cards,
        "laudos_portal_cards": laudos_portal_cards,
        "portal_governance_summary": _build_portal_governance_summary(official_issue_summaries_portal),
        "modelos_portal": modelos_portal,
        "tipos_template_portal": tipos_template_portal,
        "catalog_governed_mode": bool(template_snapshot.get("governed_mode")),
        "catalog_state": str(template_snapshot.get("catalog_state") or "legacy_open"),
        "catalog_permissions": dict(template_snapshot.get("permissions") or {}),
        "entry_mode_preference_default": contexto_modo_entrada.entry_mode_preference,
        "entry_mode_remember_last_case_mode": contexto_modo_entrada.remember_last_case_mode,
        "entry_mode_last_case_mode": contexto_modo_entrada.last_case_mode,
        "portal_switch_links": usuario_portal_switch_links(
            usuario,
            portal_atual=PORTAL_INSPETOR,
        ),
        "tenant_access_policy": tenant_access_policy,
    }
