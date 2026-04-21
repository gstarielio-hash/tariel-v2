"""Schemas do domínio Chat/Inspetor.

Separados de `routes.py` para reduzir acoplamento e facilitar evolução
dos módulos (`auth`, `laudo`, `chat`, `mesa`, `pendencias`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

from app.domains.chat.media_helpers import nome_documento_seguro
from app.domains.chat.normalization import normalizar_setor

LIMITE_MSG_CHARS = 8_000
LIMITE_HISTORICO = 20
LIMITE_IMG_BASE64 = 14_500_000
LIMITE_DOC_CHARS = 40_000
LIMITE_FEEDBACK = 500
LIMITE_NOME_DOCUMENTO = 120
LIMITE_GUIDED_CHECKLIST = 20
LIMITE_GUIDED_EVIDENCE_REFS = 80
LIMITE_REVIEW_REASON = 800
LIMITE_PREFERENCIAS_IA_MOBILE = 4_000

GuidedInspectionTemplateKey = Literal[
    "padrao",
    "avcb",
    "cbmgo",
    "loto",
    "nr11_movimentacao",
    "nr12maquinas",
    "nr13",
    "nr13_calibracao",
    "nr13_teste_hidrostatico",
    "nr13_ultrassom",
    "nr20_instalacoes",
    "nr33_espaco_confinado",
    "nr35_linha_vida",
    "nr35_montagem",
    "nr35_ponto_ancoragem",
    "nr35_projeto",
    "pie",
    "rti",
    "spda",
]


class MensagemHistorico(BaseModel):
    papel: Literal["usuario", "assistente"]
    texto: str = Field(..., max_length=LIMITE_MSG_CHARS)

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class DadosChat(BaseModel):
    mensagem: str = Field(default="", max_length=LIMITE_MSG_CHARS)
    preferencias_ia_mobile: str = Field(
        default="",
        max_length=LIMITE_PREFERENCIAS_IA_MOBILE,
    )
    dados_imagem: str = Field(default="", max_length=LIMITE_IMG_BASE64)
    setor: str = Field(default="geral", max_length=50)
    historico: list[MensagemHistorico] = Field(default_factory=list, max_length=LIMITE_HISTORICO)
    modo: Literal["curto", "detalhado", "deep_research"] = Field(default="detalhado")
    entry_mode_preference: Literal["chat_first", "evidence_first", "auto_recommended"] | None = Field(default=None)
    texto_documento: str = Field(default="", max_length=LIMITE_DOC_CHARS)
    nome_documento: str = Field(default="", max_length=LIMITE_NOME_DOCUMENTO)
    laudo_id: int | None = None
    referencia_mensagem_id: int | None = Field(default=None, ge=1)
    guided_inspection_draft: "GuidedInspectionDraftPayload | None" = Field(default=None)
    guided_inspection_context: "GuidedInspectionMessageContextPayload | None" = Field(default=None)

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    @field_validator("setor")
    @classmethod
    def validar_setor(cls, valor: str) -> str:
        return normalizar_setor(valor)

    @field_validator("nome_documento")
    @classmethod
    def validar_nome_documento(cls, valor: str) -> str:
        return nome_documento_seguro(valor)


class DadosMesaMensagem(BaseModel):
    texto: str = Field(..., min_length=1, max_length=LIMITE_MSG_CHARS)
    referencia_mensagem_id: int | None = Field(default=None, ge=1)
    client_message_id: str | None = Field(default=None, min_length=8, max_length=64)

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class DadosMobileReviewCommand(BaseModel):
    command: Literal[
        "enviar_para_mesa",
        "aprovar_no_mobile",
        "devolver_no_mobile",
        "reabrir_bloco",
    ]
    block_key: str | None = Field(default=None, max_length=120)
    evidence_key: str | None = Field(default=None, max_length=160)
    title: str | None = Field(default=None, max_length=180)
    reason: str | None = Field(default=None, max_length=LIMITE_REVIEW_REASON)
    summary: str | None = Field(default=None, max_length=280)
    required_action: str | None = Field(default=None, max_length=280)
    failure_reasons: list[str] = Field(default_factory=list, max_length=10)

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    @field_validator("failure_reasons", mode="before")
    @classmethod
    def validar_failure_reasons(cls, valor: object) -> list[str]:
        if not isinstance(valor, list):
            return []
        vistos: set[str] = set()
        itens: list[str] = []
        for item in valor:
            texto = " ".join(str(item or "").strip().split())
            if not texto:
                continue
            chave = texto.lower()
            if chave in vistos:
                continue
            vistos.add(chave)
            itens.append(texto[:120])
        return itens


class DadosReabrirLaudo(BaseModel):
    issued_document_policy: Literal["keep_visible", "hide_from_case"] = (
        "keep_visible"
    )

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class DadosPDF(BaseModel):
    diagnostico: str = Field(..., min_length=1, max_length=40_000)
    inspetor: str = Field(..., min_length=1, max_length=200)
    empresa: str = Field(default="", max_length=200)
    setor: str = Field(default="geral", max_length=50)
    data: str = Field(default="", max_length=20)
    laudo_id: int | None = Field(default=None, ge=1)
    tipo_template: str = Field(default="", max_length=80)

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    @field_validator("setor")
    @classmethod
    def validar_setor(cls, valor: str) -> str:
        return normalizar_setor(valor)


class DadosPin(BaseModel):
    pinado: StrictBool

    model_config = ConfigDict(extra="ignore")


class GuidedInspectionChecklistItemPayload(BaseModel):
    id: str = Field(..., min_length=1, max_length=80)
    title: str = Field(..., min_length=1, max_length=120)
    prompt: str = Field(..., min_length=1, max_length=600)
    evidence_hint: str = Field(..., min_length=1, max_length=240)

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class GuidedInspectionDraftPayload(BaseModel):
    template_key: GuidedInspectionTemplateKey
    template_label: str = Field(..., min_length=1, max_length=120)
    started_at: str = Field(..., min_length=1, max_length=64)
    current_step_index: int = Field(default=0, ge=0, le=LIMITE_GUIDED_CHECKLIST)
    completed_step_ids: list[str] = Field(
        default_factory=list,
        max_length=LIMITE_GUIDED_CHECKLIST,
    )
    checklist: list[GuidedInspectionChecklistItemPayload] = Field(
        default_factory=list,
        min_length=1,
        max_length=LIMITE_GUIDED_CHECKLIST,
    )
    evidence_bundle_kind: Literal["case_thread"] = Field(default="case_thread")
    evidence_refs: list["GuidedInspectionEvidenceRefPayload"] = Field(
        default_factory=list,
        max_length=LIMITE_GUIDED_EVIDENCE_REFS,
    )
    mesa_handoff: "GuidedInspectionMesaHandoffPayload | None" = Field(default=None)

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    @field_validator("completed_step_ids", mode="before")
    @classmethod
    def validar_completed_step_ids(cls, valor: object) -> list[str]:
        if not isinstance(valor, list):
            return []
        ids: list[str] = []
        vistos: set[str] = set()
        for item in valor:
            step_id = str(item or "").strip()
            if not step_id or step_id in vistos:
                continue
            vistos.add(step_id)
            ids.append(step_id[:80])
        return ids


class DadosGuidedInspectionDraftUpsert(BaseModel):
    guided_inspection_draft: GuidedInspectionDraftPayload | None = Field(default=None)

    model_config = ConfigDict(extra="ignore")


class GuidedInspectionEvidenceRefPayload(BaseModel):
    message_id: int = Field(..., ge=1)
    step_id: str = Field(..., min_length=1, max_length=80)
    step_title: str = Field(..., min_length=1, max_length=120)
    captured_at: str = Field(..., min_length=1, max_length=64)
    evidence_kind: Literal["chat_message"] = Field(default="chat_message")
    attachment_kind: Literal["none", "image", "document", "mixed"] = Field(
        default="none"
    )

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class GuidedInspectionMesaHandoffPayload(BaseModel):
    required: StrictBool = True
    review_mode: str = Field(..., min_length=1, max_length=40)
    reason_code: str = Field(..., min_length=1, max_length=80)
    recorded_at: str = Field(..., min_length=1, max_length=64)
    step_id: str = Field(..., min_length=1, max_length=80)
    step_title: str = Field(..., min_length=1, max_length=120)

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class GuidedInspectionMessageContextPayload(BaseModel):
    template_key: GuidedInspectionTemplateKey
    step_id: str = Field(..., min_length=1, max_length=80)
    step_title: str = Field(..., min_length=1, max_length=120)
    attachment_kind: Literal["none", "image", "document", "mixed"] = Field(
        default="none"
    )

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class DadosPendencia(BaseModel):
    lida: StrictBool = True

    model_config = ConfigDict(extra="ignore")


class DadosFeedback(BaseModel):
    tipo: Literal["positivo", "negativo"]
    trecho: str = Field(default="", max_length=LIMITE_FEEDBACK)

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
