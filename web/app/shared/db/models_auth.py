from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Session, relationship, validates

from app.shared.db.contracts import (
    LIMITES_PADRAO,
    LimitePlanoFallback,
    NivelAcesso,
    PlanoEmpresa,
    StatusAprendizadoIa,
    VereditoAprendizadoIa,
    _valores_enum,
)
from app.shared.db.models_base import Base, MixinAuditoria, agora_utc

logger = logging.getLogger("tariel.banco_dados")

_ADMIN_IDENTITY_STATUSES = {
    "invited",
    "active",
    "suspended",
    "blocked",
    "password_reset_required",
}
_ACCOUNT_SCOPES = {"tenant", "platform"}
_ACCOUNT_STATUSES = {"active", "blocked", "pending_activation"}
_PLATFORM_ROLES = {
    "PLATFORM_OWNER",
    "PLATFORM_ADMIN",
    "PLATFORM_FINANCE",
    "PLATFORM_AUDITOR",
    "PLATFORM_SUPPORT_EXCEPTIONAL",
}


class LimitePlano(Base):
    __tablename__ = "limites_plano"
    __table_args__ = (
        CheckConstraint(
            f"plano IN ({', '.join(repr(p.value) for p in PlanoEmpresa)})",
            name="ck_limite_plano_valido",
        ),
        CheckConstraint(
            "laudos_mes IS NULL OR laudos_mes >= 0",
            name="ck_limite_laudos_mes_nao_negativo",
        ),
        CheckConstraint(
            "usuarios_max IS NULL OR usuarios_max >= 0",
            name="ck_limite_usuarios_max_nao_negativo",
        ),
        CheckConstraint(
            "integracoes_max IS NULL OR integracoes_max >= 0",
            name="ck_limite_integracoes_max_nao_negativo",
        ),
        CheckConstraint(
            "retencao_dias IS NULL OR retencao_dias >= 0",
            name="ck_limite_retencao_dias_nao_negativo",
        ),
    )

    plano = Column(String(20), primary_key=True)
    laudos_mes = Column(Integer, nullable=True)
    usuarios_max = Column(Integer, nullable=True)
    upload_doc = Column(Boolean, nullable=False, default=False)
    deep_research = Column(Boolean, nullable=False, default=False)
    integracoes_max = Column(Integer, nullable=True)
    retencao_dias = Column(Integer, nullable=True)

    @validates("plano")
    def _validar_plano(self, _key: str, valor: Any) -> str:
        return PlanoEmpresa.normalizar(valor)

    def __repr__(self) -> str:
        return f"<LimitePlano plano={self.plano!r} laudos_mes={self.laudos_mes}>"

    def laudos_ilimitados(self) -> bool:
        return self.laudos_mes is None

    def usuarios_ilimitados(self) -> bool:
        return self.usuarios_max is None


class Empresa(MixinAuditoria, Base):
    __tablename__ = "empresas"
    __table_args__ = (
        CheckConstraint(
            f"plano_ativo IN ({', '.join(repr(p.value) for p in PlanoEmpresa)})",
            name="ck_empresa_plano_valido",
        ),
        CheckConstraint(
            "custo_gerado_reais >= 0",
            name="ck_empresa_custo_nao_negativo",
        ),
        CheckConstraint(
            "mensagens_processadas >= 0",
            name="ck_empresa_msgs_nao_negativo",
        ),
        CheckConstraint(
            "LENGTH(REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '')) = 14",
            name="ck_empresa_cnpj_tamanho",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    nome_fantasia = Column(String(200), nullable=False, index=True)
    cnpj = Column(String(18), nullable=False, unique=True, index=True)
    plano_ativo = Column(String(20), nullable=False, default=PlanoEmpresa.INICIAL.value)
    custo_gerado_reais = Column(
        Numeric(12, 4),
        nullable=False,
        default=0,
    )
    mensagens_processadas = Column(Integer, nullable=False, default=0)
    escopo_plataforma = Column(Boolean, nullable=False, default=False)
    status_bloqueio = Column(Boolean, nullable=False, default=False)
    bloqueado_em = Column(DateTime(timezone=True), nullable=True)
    motivo_bloqueio = Column(String(300), nullable=True)
    admin_cliente_policy_json = Column(JSON, nullable=True)
    segmento = Column(String(100), nullable=True)
    cidade_estado = Column(String(100), nullable=True)
    nome_responsavel = Column(String(150), nullable=True)
    observacoes = Column(Text, nullable=True)

    usuarios = relationship(
        "Usuario",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )
    laudos = relationship(
        "Laudo",
        back_populates="empresa",
        passive_deletes=True,
    )
    templates_laudo = relationship(
        "TemplateLaudo",
        back_populates="empresa",
        passive_deletes=True,
    )
    auditoria_registros = relationship(
        "RegistroAuditoriaEmpresa",
        back_populates="empresa",
        passive_deletes=True,
    )
    push_mobile_dispositivos = relationship(
        "DispositivoPushMobile",
        back_populates="empresa",
        passive_deletes=True,
    )
    aprendizados_visuais_ia = relationship(
        "AprendizadoVisualIa",
        back_populates="empresa",
        passive_deletes=True,
    )

    @validates("plano_ativo")
    def _validar_plano_ativo(self, _key: str, valor: Any) -> str:
        return PlanoEmpresa.normalizar(valor)

    def __repr__(self) -> str:
        return f"<Empresa id={self.id} nome={self.nome_fantasia!r} plano={self.plano_ativo}>"

    @property
    def plano_normalizado(self) -> str:
        return PlanoEmpresa.normalizar(self.plano_ativo)

    @property
    def esta_bloqueada(self) -> bool:
        return bool(self.status_bloqueio)

    @property
    def eh_tenant_plataforma(self) -> bool:
        return bool(self.escopo_plataforma)

    def obter_limites(self, banco: Session) -> LimitePlano | LimitePlanoFallback:
        plano_normalizado = PlanoEmpresa.normalizar(self.plano_ativo)
        limite = banco.get(LimitePlano, plano_normalizado)
        if limite:
            return limite

        logger.warning(
            "LimitePlano não encontrado para plano=%r. Usando fallback.",
            plano_normalizado,
        )
        padrao = LIMITES_PADRAO.get(
            plano_normalizado,
            LIMITES_PADRAO[PlanoEmpresa.INICIAL.value],
        )
        return LimitePlanoFallback(
            plano=plano_normalizado,
            laudos_mes=padrao["laudos_mes"],
            usuarios_max=padrao["usuarios_max"],
            upload_doc=padrao["upload_doc"],
            deep_research=padrao["deep_research"],
            integracoes_max=padrao["integracoes_max"],
            retencao_dias=padrao["retencao_dias"],
        )


class Usuario(MixinAuditoria, Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            (f"nivel_acesso IN ({int(NivelAcesso.INSPETOR)}, {int(NivelAcesso.REVISOR)}, {int(NivelAcesso.ADMIN_CLIENTE)}, {int(NivelAcesso.DIRETORIA)})"),
            name="ck_usuario_nivel_acesso_valido",
        ),
        CheckConstraint(
            "admin_identity_status IN ('invited', 'active', 'suspended', 'blocked', 'password_reset_required')",
            name="ck_usuario_admin_identity_status_valido",
        ),
        CheckConstraint(
            "account_scope IN ('tenant', 'platform')",
            name="ck_usuario_account_scope_valido",
        ),
        CheckConstraint(
            "account_status IN ('active', 'blocked', 'pending_activation')",
            name="ck_usuario_account_status_valido",
        ),
        CheckConstraint(
            "tentativas_login >= 0",
            name="ck_usuario_tentativas_nao_negativo",
        ),
        Index("ix_usuario_empresa_email", "empresa_id", "email"),
        Index("ix_usuario_admin_portal_autorizado", "portal_admin_autorizado", "email"),
        Index("ix_usuario_platform_scope_status", "account_scope", "account_status", "empresa_id"),
        UniqueConstraint(
            "admin_identity_provider",
            "admin_identity_subject",
            name="uq_usuario_admin_identity_subject",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome_completo = Column(String(150), nullable=False)
    email = Column(String(254), nullable=False, unique=True, index=True)
    telefone = Column(String(30), nullable=True)
    foto_perfil_url = Column(String(512), nullable=True)
    crea = Column(String(40), nullable=True)
    senha_hash = Column(String(256), nullable=False)
    nivel_acesso = Column(Integer, nullable=False, default=int(NivelAcesso.INSPETOR))
    ativo = Column(Boolean, nullable=False, default=True)
    tentativas_login = Column(Integer, nullable=False, default=0)
    bloqueado_ate = Column(DateTime(timezone=True), nullable=True)
    ultimo_login = Column(DateTime(timezone=True), nullable=True)
    ultimo_login_ip = Column(String(45), nullable=True)
    status_bloqueio = Column(Boolean, nullable=False, default=False)
    senha_temporaria_ativa = Column(Boolean, nullable=False, default=False)
    account_scope = Column(String(20), nullable=False, default="tenant")
    account_status = Column(String(30), nullable=False, default="active")
    allowed_portals_json = Column(JSON, nullable=False, default=list)
    platform_role = Column(String(40), nullable=True)
    mfa_required = Column(Boolean, nullable=False, default=False)
    mfa_secret_b32 = Column(String(80), nullable=True)
    mfa_enrolled_at = Column(DateTime(timezone=True), nullable=True)
    can_password_login = Column(Boolean, nullable=False, default=True)
    can_google_login = Column(Boolean, nullable=False, default=False)
    can_microsoft_login = Column(Boolean, nullable=False, default=False)
    blocked_reason = Column(String(300), nullable=True)
    portal_admin_autorizado = Column(Boolean, nullable=False, default=False)
    admin_identity_status = Column(String(40), nullable=False, default="active")
    admin_identity_provider = Column(String(30), nullable=True)
    admin_identity_subject = Column(String(255), nullable=True)
    admin_identity_verified_em = Column(DateTime(timezone=True), nullable=True)

    empresa = relationship("Empresa", back_populates="usuarios")
    laudos = relationship(
        "Laudo",
        foreign_keys="Laudo.usuario_id",
        back_populates="usuario",
    )
    templates_laudo_criados = relationship(
        "TemplateLaudo",
        foreign_keys="TemplateLaudo.criado_por_id",
        back_populates="criado_por",
    )
    preferencias_mobile = relationship(
        "PreferenciaMobileUsuario",
        uselist=False,
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    push_mobile_dispositivos = relationship(
        "DispositivoPushMobile",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    aprendizados_visuais_criados = relationship(
        "AprendizadoVisualIa",
        foreign_keys="AprendizadoVisualIa.criado_por_id",
        back_populates="criado_por",
    )
    aprendizados_visuais_validados = relationship(
        "AprendizadoVisualIa",
        foreign_keys="AprendizadoVisualIa.validado_por_id",
        back_populates="validado_por",
    )

    @validates("nivel_acesso")
    def _validar_nivel_acesso(self, _key: str, valor: Any) -> int:
        return NivelAcesso.normalizar(valor)

    @validates("admin_identity_status")
    def _validar_admin_identity_status(self, _key: str, valor: Any) -> str:
        status = str(valor or "active").strip().lower()
        if status not in _ADMIN_IDENTITY_STATUSES:
            raise ValueError("Status de identidade admin inválido.")
        return status

    @validates("account_scope")
    def _validar_account_scope(self, _key: str, valor: Any) -> str:
        scope = str(valor or "tenant").strip().lower() or "tenant"
        if scope not in _ACCOUNT_SCOPES:
            raise ValueError("Escopo de conta inválido.")
        return scope

    @validates("account_status")
    def _validar_account_status(self, _key: str, valor: Any) -> str:
        status = str(valor or "active").strip().lower() or "active"
        if status not in _ACCOUNT_STATUSES:
            raise ValueError("Status da conta inválido.")
        return status

    @validates("platform_role")
    def _validar_platform_role(self, _key: str, valor: Any) -> str | None:
        if valor in (None, ""):
            return None
        role = str(valor).strip().upper()
        if role not in _PLATFORM_ROLES:
            raise ValueError("Papel de plataforma inválido.")
        return role

    def __repr__(self) -> str:
        return f"<Usuario id={self.id} email={self.email!r} nivel={self.nivel_acesso}>"

    @property
    def nome(self) -> str:
        return self.nome_completo or f"Usuário #{self.id}"

    @property
    def eh_inspetor(self) -> bool:
        return int(self.nivel_acesso) == int(NivelAcesso.INSPETOR)

    @property
    def eh_revisor(self) -> bool:
        return int(self.nivel_acesso) == int(NivelAcesso.REVISOR)

    @property
    def eh_admin_cliente(self) -> bool:
        return int(self.nivel_acesso) == int(NivelAcesso.ADMIN_CLIENTE)

    @property
    def eh_revisor_ou_superior(self) -> bool:
        return int(self.nivel_acesso) in {
            int(NivelAcesso.REVISOR),
            int(NivelAcesso.DIRETORIA),
        }

    @property
    def eh_diretoria(self) -> bool:
        return int(self.nivel_acesso) == int(NivelAcesso.DIRETORIA)

    @property
    def tem_autorizacao_explicita_admin(self) -> bool:
        return bool(self.portal_admin_autorizado)

    @property
    def allowed_portals(self) -> tuple[str, ...]:
        bruto = getattr(self, "allowed_portals_json", None)
        if not isinstance(bruto, list):
            return tuple()
        return tuple(str(item or "").strip().lower() for item in bruto if str(item or "").strip())

    @property
    def account_scope_normalizado(self) -> str:
        return str(self.account_scope or "tenant").strip().lower() or "tenant"

    @property
    def account_status_normalizado(self) -> str:
        return str(self.account_status or "active").strip().lower() or "active"

    @property
    def conta_plataforma_ativa(self) -> bool:
        return self.account_scope_normalizado == "platform" and self.account_status_normalizado == "active"

    @property
    def mfa_configurado(self) -> bool:
        return bool(self.mfa_secret_b32 and self.mfa_enrolled_at)

    @property
    def pode_login_local(self) -> bool:
        return bool(self.can_password_login)

    @property
    def pode_login_google(self) -> bool:
        return bool(self.can_google_login)

    @property
    def pode_login_microsoft(self) -> bool:
        return bool(self.can_microsoft_login)

    @property
    def identidade_admin_status(self) -> str:
        return str(self.admin_identity_status or "active").strip().lower() or "active"

    @property
    def identidade_admin_ativa(self) -> bool:
        return self.identidade_admin_status in {"active", "password_reset_required"}

    def esta_bloqueado(self) -> bool:
        if self.bloqueado_ate is None:
            return False
        return agora_utc() < self.bloqueado_ate

    def registrar_login_sucesso(self, ip: str | None = None) -> None:
        self.tentativas_login = 0
        self.bloqueado_ate = None
        self.status_bloqueio = False
        self.ultimo_login = agora_utc()
        self.ultimo_login_ip = (ip or "")[:45] or None

    def incrementar_tentativa_falha(self, max_tentativas: int = 5) -> bool:
        self.tentativas_login += 1
        if self.tentativas_login >= max_tentativas:
            self.bloqueado_ate = agora_utc() + timedelta(minutes=15)
            self.status_bloqueio = True
            return True
        return False


class PreferenciaMobileUsuario(MixinAuditoria, Base):
    __tablename__ = "preferencias_mobile_usuarios"
    __table_args__ = (
        UniqueConstraint("usuario_id", name="uq_preferencias_mobile_usuario"),
        Index("ix_preferencias_mobile_usuario", "usuario_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    notificacoes_json = Column(JSON, nullable=False, default=dict)
    privacidade_json = Column(JSON, nullable=False, default=dict)
    permissoes_json = Column(JSON, nullable=False, default=dict)
    experiencia_ia_json = Column(JSON, nullable=False, default=dict)

    usuario = relationship("Usuario", back_populates="preferencias_mobile")

    def __repr__(self) -> str:
        return f"<PreferenciaMobileUsuario id={self.id} usuario_id={self.usuario_id}>"


class DispositivoPushMobile(MixinAuditoria, Base):
    __tablename__ = "dispositivos_push_mobile"
    __table_args__ = (
        UniqueConstraint(
            "usuario_id",
            "device_id",
            "plataforma",
            name="uq_push_mobile_usuario_device_plataforma",
        ),
        Index("ix_push_mobile_empresa_last_seen", "empresa_id", "last_seen_at"),
        Index("ix_push_mobile_usuario_status", "usuario_id", "token_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    empresa_id = Column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id = Column(String(120), nullable=False)
    plataforma = Column(String(20), nullable=False, default="android")
    provider = Column(String(20), nullable=False, default="expo")
    push_token = Column(String(255), nullable=True)
    permissao_notificacoes = Column(Boolean, nullable=False, default=False)
    push_habilitado = Column(Boolean, nullable=False, default=False)
    token_status = Column(String(40), nullable=False, default="unavailable")
    canal_build = Column(String(60), nullable=True)
    app_version = Column(String(40), nullable=True)
    build_number = Column(String(40), nullable=True)
    device_label = Column(String(120), nullable=True)
    is_emulator = Column(Boolean, nullable=False, default=False)
    ultimo_erro = Column(String(220), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=agora_utc)

    usuario = relationship("Usuario", back_populates="push_mobile_dispositivos")
    empresa = relationship("Empresa", back_populates="push_mobile_dispositivos")

    def __repr__(self) -> str:
        return (
            f"<DispositivoPushMobile id={self.id} usuario_id={self.usuario_id} "
            f"plataforma={self.plataforma!r} device_id={self.device_id!r}>"
        )


class AprendizadoVisualIa(MixinAuditoria, Base):
    __tablename__ = "aprendizados_visuais_ia"
    __table_args__ = (
        Index("ix_aprendizado_visual_empresa_status", "empresa_id", "status", "validado_em"),
        Index("ix_aprendizado_visual_laudo_criado", "laudo_id", "criado_em"),
        Index("ix_aprendizado_visual_setor_status", "empresa_id", "setor_industrial", "status"),
        Index("ix_aprendizado_visual_ref_msg", "mensagem_referencia_id"),
        Index("ix_aprendizado_visual_sha", "imagem_sha256"),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    laudo_id = Column(
        Integer,
        ForeignKey("laudos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mensagem_referencia_id = Column(
        Integer,
        ForeignKey("mensagens_laudo.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    criado_por_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    validado_por_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    setor_industrial = Column(String(100), nullable=False, default="geral")
    resumo = Column(String(240), nullable=False)
    descricao_contexto = Column(Text, nullable=True)
    correcao_inspetor = Column(Text, nullable=False)
    parecer_mesa = Column(Text, nullable=True)
    sintese_consolidada = Column(Text, nullable=True)
    pontos_chave_json = Column(JSON, nullable=False, default=list)
    referencias_norma_json = Column(JSON, nullable=False, default=list)
    marcacoes_json = Column(JSON, nullable=False, default=list)
    status = Column(
        SAEnum(StatusAprendizadoIa, values_callable=_valores_enum, native_enum=False),
        nullable=False,
        default=StatusAprendizadoIa.RASCUNHO_INSPETOR.value,
    )
    veredito_inspetor = Column(
        SAEnum(VereditoAprendizadoIa, values_callable=_valores_enum, native_enum=False),
        nullable=False,
        default=VereditoAprendizadoIa.DUVIDA.value,
    )
    veredito_mesa = Column(
        SAEnum(VereditoAprendizadoIa, values_callable=_valores_enum, native_enum=False),
        nullable=True,
    )
    imagem_url = Column(String(600), nullable=True)
    imagem_nome_original = Column(String(160), nullable=True)
    imagem_mime_type = Column(String(120), nullable=True)
    imagem_sha256 = Column(String(64), nullable=True)
    caminho_arquivo = Column(String(600), nullable=True)
    validado_em = Column(DateTime(timezone=True), nullable=True)

    empresa = relationship("Empresa", back_populates="aprendizados_visuais_ia")
    laudo = relationship("Laudo", back_populates="aprendizados_visuais_ia")
    mensagem_referencia = relationship("MensagemLaudo", foreign_keys=[mensagem_referencia_id])
    criado_por = relationship("Usuario", foreign_keys=[criado_por_id], back_populates="aprendizados_visuais_criados")
    validado_por = relationship("Usuario", foreign_keys=[validado_por_id], back_populates="aprendizados_visuais_validados")

    @validates("status")
    def _validar_status(self, _key: str, valor: Any) -> str:
        return StatusAprendizadoIa.normalizar(valor)

    @validates("veredito_inspetor")
    def _validar_veredito_inspetor(self, _key: str, valor: Any) -> str:
        return VereditoAprendizadoIa.normalizar(valor)

    @validates("veredito_mesa")
    def _validar_veredito_mesa(self, _key: str, valor: Any) -> str | None:
        if valor in (None, ""):
            return None
        return VereditoAprendizadoIa.normalizar(valor)

    def __repr__(self) -> str:
        return f"<AprendizadoVisualIa id={self.id} laudo_id={self.laudo_id} status={self.status!r}>"


class RegistroAuditoriaEmpresa(MixinAuditoria, Base):
    __tablename__ = "auditoria_empresas"
    __table_args__ = (
        Index("ix_auditoria_empresa_criada", "empresa_id", "criado_em"),
        Index("ix_auditoria_empresa_portal", "empresa_id", "portal"),
        Index("ix_auditoria_ator_criada", "ator_usuario_id", "criado_em"),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ator_usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    alvo_usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    portal = Column(String(30), nullable=False, default="cliente")
    acao = Column(String(80), nullable=False)
    resumo = Column(String(220), nullable=False)
    detalhe = Column(Text, nullable=True)
    payload_json = Column(JSON, nullable=True)

    empresa = relationship("Empresa", back_populates="auditoria_registros")
    ator_usuario = relationship("Usuario", foreign_keys=[ator_usuario_id])
    alvo_usuario = relationship("Usuario", foreign_keys=[alvo_usuario_id])

    def __repr__(self) -> str:
        return f"<RegistroAuditoriaEmpresa id={self.id} empresa_id={self.empresa_id} acao={self.acao!r} portal={self.portal!r}>"


class ConfiguracaoPlataforma(MixinAuditoria, Base):
    __tablename__ = "configuracoes_plataforma"
    __table_args__ = (
        Index("ix_configuracao_plataforma_categoria", "categoria"),
        Index("ix_configuracao_plataforma_atualizada_por", "atualizada_por_usuario_id"),
    )

    chave = Column(String(80), primary_key=True)
    categoria = Column(String(40), nullable=False, default="governanca")
    valor_json = Column(JSON, nullable=True)
    motivo_ultima_alteracao = Column(String(300), nullable=True)
    atualizada_por_usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    atualizada_por_usuario = relationship("Usuario", foreign_keys=[atualizada_por_usuario_id])

    def __repr__(self) -> str:
        return f"<ConfiguracaoPlataforma chave={self.chave!r} categoria={self.categoria!r}>"


class SessaoAtiva(Base):
    __tablename__ = "sessoes_ativas"
    __table_args__ = (
        Index("ix_sessao_usuario_criada", "usuario_id", "criada_em"),
        Index("ix_sessao_expira", "expira_em"),
    )

    token = Column(String(180), primary_key=True)
    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criada_em = Column(
        DateTime(timezone=True),
        nullable=False,
        default=agora_utc,
    )
    expira_em = Column(
        DateTime(timezone=True),
        nullable=False,
    )
    ultima_atividade_em = Column(
        DateTime(timezone=True),
        nullable=False,
        default=agora_utc,
    )
    lembrar = Column(Boolean, nullable=False, default=False)
    portal = Column(String(30), nullable=True)
    account_scope = Column(String(20), nullable=True)
    device_id = Column(String(120), nullable=True)
    mfa_level = Column(String(30), nullable=True)
    reauth_at = Column(DateTime(timezone=True), nullable=True)
    ip_hash = Column(String(64), nullable=True)
    user_agent_hash = Column(String(64), nullable=True)

    def __repr__(self) -> str:
        return f"<SessaoAtiva usuario_id={self.usuario_id} expira_em={self.expira_em}>"
