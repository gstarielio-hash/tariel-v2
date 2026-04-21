"""Geração de relatório PDF do chat livre para o portal mobile/web do inspetor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import re
import tempfile
from typing import Any, Sequence

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image
from sqlalchemy.orm import Session

from app.domains.chat.app_context import logger as chat_logger
from app.domains.chat.auth_helpers import usuario_nome
from app.domains.chat.laudo_state_helpers import serializar_card_laudo
from app.domains.chat.learning_helpers import (
    CORRECAO_CHAT_AUTOMATICA_PADRAO,
    DESCRICAO_CHAT_AUTOMATICA_PADRAO,
    normalizar_lista_textos,
)
from app.domains.chat.media_helpers import safe_remove_file
from app.domains.chat.mobile_ai_preferences import limpar_texto_visivel_chat
from app.domains.mesa.attachments import salvar_arquivo_anexo_mesa, serializar_anexos_mesa
from app.shared.database import (
    AnexoMesa,
    AprendizadoVisualIa,
    Laudo,
    MensagemLaudo,
    TipoMensagem,
    Usuario,
    commit_ou_rollback_operacional,
)
from nucleo.gerador_laudos import GeradorLaudos
from nucleo.inspetor.comandos_chat import analisar_pedido_relatorio_chat_livre

REPORT_TITLE = "Laudo Técnico Consolidado"
REPORT_SUBTITLE = "Consolidação profissional dos registros, evidências visuais e análises técnicas disponíveis."
REPORT_KIND_LABEL = "Registro livre assistido"
REPORT_STATUS_LABEL = "Emissão preliminar"
LOW_INFORMATION_CHAT_LINES = {
    "imagem enviada",
    "registro visual anexado.",
    "registro visual anexado",
    "evidencia visual enviada.",
    "evidencia visual enviada",
    "evidencia visual capturada do chat",
    "evidência visual capturada do chat",
}


def _clean_report_markup(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return ""

    text = re.sub(r"\[imagem\]", "Registro visual anexado.", text, flags=re.IGNORECASE)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)

    normalized_lines: list[str] = []
    for raw_line in text.split("\n"):
        line = str(raw_line or "").strip()
        if not line:
            normalized_lines.append("")
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^\*\s+", "- ", line)
        line = re.sub(r"^\-\s+\*\s*", "- ", line)
        line = re.sub(r"^\d+\.\s+\*\s*", "", line)
        line = line.replace("**", "")
        normalized_lines.append(line)

    collapsed = "\n".join(normalized_lines)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
    return collapsed.strip()


def _truncate_text_block(value: str, *, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0].strip()
    return f"{clipped}..."


def _pdf_text(value: Any) -> str:
    text = " ".join(_clean_report_markup(value).split())
    if not text:
        return ""
    return GeradorLaudos._sanitizar_texto_para_pdf(text)


def _multiline_pdf_text(value: Any) -> str:
    raw = _clean_report_markup(value)
    lines = [" ".join(line.strip().split()) for line in raw.split("\n")]
    compact = "\n".join(line for line in lines if line)
    if not compact:
        return ""
    return GeradorLaudos._sanitizar_texto_para_pdf(compact)


def _extract_text_fragments(
    value: Any,
    *,
    limit_fragments: int | None = None,
    fragment_limit: int = 220,
) -> list[str]:
    block = _multiline_pdf_text(value)
    if not block:
        return []

    fragments: list[str] = []
    seen: set[str] = set()
    for raw_line in re.split(r"\n+", block):
        line = str(raw_line or "").strip(" -\t")
        if not line:
            continue
        candidates = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9ÁÀÂÃÉÊÍÓÔÕÚÇ])", line)
        for candidate in candidates:
            clean = str(candidate or "").strip(" -\t")
            clean = re.sub(r"^\d+[\)\.]?\s*", "", clean)
            if not clean or len(clean) < 18:
                continue
            if clean.endswith(":"):
                continue
            if re.match(
                r"^(identifica[cç][aã]o|normas? aplic[aá]veis|refer[eê]ncias? normativas|plano de manuten[cç][aã]o)\b",
                clean,
                flags=re.IGNORECASE,
            ):
                continue
            key = " ".join(clean.lower().split())
            if key in seen:
                continue
            fragments.append(_truncate_text_block(clean, limit=fragment_limit))
            seen.add(key)
            if limit_fragments is not None and len(fragments) >= limit_fragments:
                return fragments
    return fragments


def _format_datetime_label(value: datetime | None) -> str:
    if not isinstance(value, datetime):
        return "-"
    if value.tzinfo is not None:
        return value.astimezone().strftime("%d/%m/%Y %H:%M")
    return value.strftime("%d/%m/%Y %H:%M")


def _normalize_matching_text(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    normalized = normalized.replace("evidência", "evidencia")
    return " ".join(normalized.split())


def _is_low_information_text(value: Any) -> bool:
    normalized = _normalize_matching_text(value)
    if not normalized:
        return True
    if normalized in LOW_INFORMATION_CHAT_LINES:
        return True
    return normalized.startswith("[erro interno]")


class _FreeChatReportPdf(FPDF):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._next_page_mode = "body"
        self._page_modes: dict[int, str] = {}

    def add_mode_page(self, mode: str = "body") -> None:
        self._next_page_mode = mode
        super().add_page()
        self._page_modes[self.page_no()] = mode

    def header(self) -> None:
        page_mode = self._page_modes.get(self.page_no(), self._next_page_mode)
        if page_mode in {"cover", "back"}:
            return

        self.set_font("helvetica", "B", 14)
        self.set_text_color(15, 43, 70)
        self.cell(
            0,
            8,
            _pdf_text(f"Tariel.ia | {REPORT_TITLE}"),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_font("helvetica", "", 9)
        self.set_text_color(90, 90, 90)
        self.cell(
            0,
            5,
            _pdf_text(REPORT_SUBTITLE),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_draw_color(210, 220, 232)
        self.line(12, self.get_y() + 1, 198, self.get_y() + 1)
        self.ln(6)

    def footer(self) -> None:
        page_mode = self._page_modes.get(self.page_no(), self._next_page_mode)
        if page_mode == "cover":
            return

        self.set_y(-12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            5,
            _pdf_text(f"Página {self.page_no()}"),
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
            align="C",
        )


@dataclass(slots=True)
class _TranscriptItem:
    message_id: int
    role: str
    role_label: str
    created_at_label: str
    text: str


@dataclass(slots=True)
class _VisualEvidenceItem:
    file_path: str
    display_name: str
    created_at_label: str
    summary: str
    context_text: str
    technical_analysis: str
    key_points: list[str]
    norm_refs: list[str]
    verdict_label: str


@dataclass(slots=True)
class _ReportOutlineEntry:
    title: str
    page: int


@dataclass(slots=True)
class FreeChatReportGenerationResult:
    message_text: str
    attachment_payload: dict[str, Any]
    message_id: int
    laudo_card_payload: dict[str, Any] | None


def _register_outline_entry(
    outline: list[_ReportOutlineEntry],
    title: str,
    page: int,
) -> None:
    normalized_title = _pdf_text(title)
    if not normalized_title:
        return
    if outline and outline[-1].title == normalized_title and outline[-1].page == int(page):
        return
    outline.append(_ReportOutlineEntry(title=normalized_title, page=int(page)))


def _build_transcript(
    *,
    banco: Session,
    laudo_id: int,
    request_message_id: int,
) -> list[_TranscriptItem]:
    messages = (
        banco.query(MensagemLaudo)
        .filter(
            MensagemLaudo.laudo_id == int(laudo_id),
            ~MensagemLaudo.tipo.in_(
                (
                    TipoMensagem.HUMANO_INSP.value,
                    TipoMensagem.HUMANO_ENG.value,
                )
            ),
        )
        .order_by(MensagemLaudo.id.asc())
        .all()
    )

    transcript: list[_TranscriptItem] = []
    for message in messages:
        visible = limpar_texto_visivel_chat(
            str(getattr(message, "conteudo", "") or ""),
            fallback_hidden_only="Evidência visual enviada."
            if message.tipo == TipoMensagem.USER.value
            else "",
        ).strip()
        if not visible:
            continue

        if (
            int(getattr(message, "id", 0) or 0) == int(request_message_id)
            and analisar_pedido_relatorio_chat_livre(visible)
            and len(visible.split()) <= 8
        ):
            continue

        if message.tipo != TipoMensagem.USER.value and _is_low_information_text(visible):
            continue

        transcript.append(
            _TranscriptItem(
                message_id=int(getattr(message, "id", 0) or 0),
                role="inspetor"
                if message.tipo == TipoMensagem.USER.value
                else "assistente",
                role_label="Inspetor"
                if message.tipo == TipoMensagem.USER.value
                else "IA Tariel",
                created_at_label=_format_datetime_label(getattr(message, "criado_em", None)),
                text=visible,
            )
        )

    return transcript


def _dedupe_text_blocks(
    values: Sequence[str | None],
    *,
    limit: int | None = None,
) -> list[str]:
    blocks: list[str] = []
    seen: set[str] = set()
    for value in values:
        block = _multiline_pdf_text(value)
        if not block:
            continue
        key = " ".join(block.lower().split())
        if key in seen:
            continue
        blocks.append(block)
        seen.add(key)
        if limit is not None and len(blocks) >= limit:
            break
    return blocks


def _clean_evidence_context(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text == CORRECAO_CHAT_AUTOMATICA_PADRAO:
        return ""
    if text.startswith(DESCRICAO_CHAT_AUTOMATICA_PADRAO):
        text = text[len(DESCRICAO_CHAT_AUTOMATICA_PADRAO) :].strip(" .:-")
    if text.lower().startswith("mensagem do inspetor:"):
        text = text.split(":", 1)[1].strip()
    if text.lower().startswith("complemento do inspetor no chat:"):
        text = text.split(":", 1)[1].strip()
    return _multiline_pdf_text(text)


def _best_context_line(
    *,
    laudo: Laudo,
    transcript: list[_TranscriptItem],
    evidences: list[_VisualEvidenceItem] | None = None,
) -> str:
    candidates: list[str | None] = [
        getattr(laudo, "primeira_mensagem", None),
    ]
    candidates.extend(item.text for item in transcript if item.role == "inspetor")
    if evidences:
        for evidence in evidences:
            candidates.append(evidence.context_text)
            candidates.append(evidence.summary)
            candidates.append(evidence.technical_analysis)

    for candidate in candidates:
        normalized = _multiline_pdf_text(candidate)
        if not normalized or _is_low_information_text(normalized):
            continue
        fragments = _extract_text_fragments(normalized, limit_fragments=1, fragment_limit=260)
        if fragments:
            return fragments[0]
        return _truncate_text_block(normalized, limit=260)

    return "Registro técnico com evidências visuais submetidas para consolidação preliminar."


def _format_verdict_label(value: Any) -> str:
    verdict = str(value or "").strip().lower()
    if verdict == "conforme":
        return "Conforme"
    if verdict == "nao_conforme":
        return "Nao conforme"
    if verdict == "ajuste":
        return "Ajuste recomendado"
    if verdict == "duvida":
        return "Analise em aberto"
    return "Sem classificacao"


def _find_assistant_analysis_for_reference(
    transcript: list[_TranscriptItem],
    *,
    reference_message_id: int | None,
) -> str:
    if not reference_message_id:
        return ""

    start_index: int | None = None
    for index, item in enumerate(transcript):
        if item.message_id == int(reference_message_id):
            start_index = index
            break

    if start_index is None:
        return ""

    assistant_blocks: list[str | None] = []
    for item in transcript[start_index + 1 :]:
        if item.role == "inspetor":
            break
        if item.role == "assistente":
            assistant_blocks.append(item.text)
    return "\n\n".join(_dedupe_text_blocks(assistant_blocks, limit=2))


def _build_visual_evidence(
    *,
    banco: Session,
    laudo_id: int,
    transcript: list[_TranscriptItem],
) -> list[_VisualEvidenceItem]:
    rows = (
        banco.query(AprendizadoVisualIa)
        .filter(
            AprendizadoVisualIa.laudo_id == int(laudo_id),
            AprendizadoVisualIa.caminho_arquivo.isnot(None),
        )
        .order_by(AprendizadoVisualIa.criado_em.asc(), AprendizadoVisualIa.id.asc())
        .all()
    )

    evidences: list[_VisualEvidenceItem] = []
    seen_paths: set[str] = set()
    for row in rows:
        path = str(getattr(row, "caminho_arquivo", "") or "").strip()
        if not path or path in seen_paths or not Path(path).is_file():
            continue
        seen_paths.add(path)
        inspector_note = _clean_evidence_context(getattr(row, "correcao_inspetor", None))
        context_note = _clean_evidence_context(getattr(row, "descricao_contexto", None))
        assistant_analysis = _find_assistant_analysis_for_reference(
            transcript,
            reference_message_id=int(getattr(row, "mensagem_referencia_id", 0) or 0)
            or None,
        )
        summary_blocks = _dedupe_text_blocks(
            [
                getattr(row, "resumo", None),
                inspector_note,
                context_note,
            ],
            limit=2,
        )
        technical_blocks = _dedupe_text_blocks(
            [
                getattr(row, "sintese_consolidada", None),
                getattr(row, "parecer_mesa", None),
                assistant_analysis,
            ],
            limit=3,
        )
        summary = summary_blocks[0] if summary_blocks else "Evidência visual anexada ao registro técnico."
        if _is_low_information_text(summary):
            technical_fragments = _extract_text_fragments(
                "\n\n".join(technical_blocks),
                limit_fragments=1,
                fragment_limit=220,
            )
            if technical_fragments:
                summary = technical_fragments[0]
            elif context_note and not _is_low_information_text(context_note):
                summary = _truncate_text_block(context_note, limit=220)
            else:
                summary = "Evidência visual consolidada para análise técnica preliminar."
        evidences.append(
            _VisualEvidenceItem(
                file_path=path,
                display_name=_pdf_text(
                    getattr(row, "imagem_nome_original", None)
                    or Path(path).name
                )
                or "evidencia_chat",
                created_at_label=_format_datetime_label(getattr(row, "criado_em", None)),
                summary=summary,
                context_text=context_note or inspector_note,
                technical_analysis="\n\n".join(technical_blocks),
                key_points=normalizar_lista_textos(
                    getattr(row, "pontos_chave_json", None) or [],
                    limite_itens=6,
                    limite_chars=140,
                ),
                norm_refs=normalizar_lista_textos(
                    getattr(row, "referencias_norma_json", None) or [],
                    limite_itens=5,
                    limite_chars=140,
                ),
                verdict_label=_format_verdict_label(
                    getattr(row, "veredito_mesa", None)
                    or getattr(row, "veredito_inspetor", None)
                ),
            )
        )
    return evidences


def _build_summary_text(
    *,
    laudo: Laudo,
    transcript: list[_TranscriptItem],
    evidences: list[_VisualEvidenceItem],
) -> str:
    findings = _build_consolidated_findings(transcript=transcript, evidences=evidences)
    recommendations = _build_recommendations(
        laudo=laudo,
        transcript=transcript,
        evidences=evidences,
        findings=findings,
    )
    references = _build_normative_references(transcript=transcript, evidences=evidences)
    lines: list[str | None] = [
        (
            "Contexto avaliado: "
            + _best_context_line(laudo=laudo, transcript=transcript, evidences=evidences)
        ),
        (
            f"Escopo consolidado: {len(transcript)} registro(s) textuais relevantes e "
            f"{len(evidences)} evidência(s) visual(is) válidas na data de emissão."
        ),
        (
            "Principais achados: "
            + "; ".join(_truncate_text_block(item, limit=160) for item in findings[:3])
            if findings
            else None
        ),
        (
            "Critérios técnicos citados: "
            + "; ".join(_truncate_text_block(item, limit=140) for item in references[:3])
            if references
            else None
        ),
        f"Conclusão executiva: {_build_conclusion_text(laudo=laudo, findings=findings)}",
        (
            "Encaminhamento sugerido: "
            + "; ".join(_truncate_text_block(item, limit=160) for item in recommendations[:3])
            if recommendations
            else None
        ),
    ]
    return "\n\n".join(_dedupe_text_blocks(lines, limit=6))


def _build_scope_text(
    *,
    laudo: Laudo,
    transcript: list[_TranscriptItem],
    evidences: list[_VisualEvidenceItem],
) -> str:
    user_lines = [item.text for item in transcript if item.role == "inspetor"]
    lines: list[str | None] = [
        "Objetivo: consolidar tecnicamente o material registrado no fluxo livre para apoiar entendimento inicial, triagem técnica e encaminhamento do caso.",
        (
            "Objeto/contexto analisado: "
            + _best_context_line(laudo=laudo, transcript=transcript, evidences=evidences)
        ),
        (
            f"Escopo considerado: {len(transcript)} interação(ões) relevante(s) e "
            f"{len(evidences)} evidência(s) visual(is) incorporada(s)."
            if evidences
            else "Escopo considerado: histórico textual consolidado, sem evidência visual vinculada."
        ),
        (
            "Abrangência: este documento reflete exclusivamente os registros "
            "disponíveis no momento da emissão e não substitui inspeção "
            "complementar, medição instrumental ou validação formal quando "
            "exigidas."
        ),
    ]
    if len(user_lines) > 1:
        lines.append(
            "Complementos relevantes do registro: "
            + " | ".join(
                _truncate_text_block(_multiline_pdf_text(item), limit=180)
                for item in user_lines[1:3]
            )
        )
    return "\n\n".join(_dedupe_text_blocks(lines, limit=4))


def _build_consolidated_findings(
    *,
    transcript: list[_TranscriptItem],
    evidences: list[_VisualEvidenceItem],
) -> list[str]:
    findings: list[str | None] = []
    for evidence in evidences:
        findings.append(_truncate_text_block(evidence.summary, limit=220))
        findings.extend(
            _truncate_text_block(item, limit=180)
            for item in evidence.key_points[:3]
        )
        findings.extend(
            _extract_text_fragments(
                evidence.technical_analysis,
                limit_fragments=2,
                fragment_limit=200,
            )
        )
    if not findings:
        assistant_lines = [item.text for item in transcript if item.role == "assistente"]
        findings.extend(
            fragment
            for item in assistant_lines[-4:]
            for fragment in _extract_text_fragments(item, limit_fragments=2, fragment_limit=220)
        )
    return _dedupe_text_blocks(findings, limit=8)


def _build_normative_references(
    *,
    transcript: list[_TranscriptItem],
    evidences: list[_VisualEvidenceItem],
) -> list[str]:
    references: list[str] = []
    for evidence in evidences:
        references.extend(evidence.norm_refs)
    if not references:
        assistant_lines = [item.text for item in transcript if item.role == "assistente"]
        references.extend(
            line
            for item in assistant_lines[-2:]
            for line in _multiline_pdf_text(item).split("\n")
            if _looks_like_normative_reference(line)
        )
    return _dedupe_text_blocks(references, limit=8)


def _looks_like_normative_reference(value: Any) -> bool:
    line = " ".join(str(value or "").strip().split())
    if not line or len(line) > 180:
        return False
    normalized = line.lower()
    return (
        normalized.startswith(("nr-", "nbr ", "nbr-", "abnt ", "iso ", "iso-", "iec ", "api ", "asme ", "aws ", "norma ", "procedimento ", "manual "))
        or bool(re.match(r"^(item|anexo|clausula|se[cç][aã]o)\s+\d", normalized))
        or (" item " in normalized and any(tag in normalized for tag in ("nr-", "nbr", "norma", "procedimento", "manual", "iso", "api", "asme", "aws")))
    )


def _looks_like_action_item(value: Any) -> bool:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return False
    normalized = text.lower()
    action_prefixes = (
        "verificar",
        "confirmar",
        "comparar",
        "isolar",
        "inspecionar",
        "substituir",
        "revisar",
        "registrar",
        "avaliar",
        "executar",
        "monitorar",
        "bloquear",
        "corrigir",
        "ajustar",
        "limpar",
        "validar",
        "documentar",
        "reinspecionar",
    )
    return (
        normalized.startswith(action_prefixes)
        or "recomenda-se" in normalized
        or "deve ser" in normalized
        or "necessidade de" in normalized
        or "isolamento preventivo" in normalized
        or "revisao imediata" in normalized
    )


def _build_conclusion_text(
    *,
    laudo: Laudo,
    findings: list[str],
) -> str:
    fragments = _extract_text_fragments(
        getattr(laudo, "parecer_ia", None),
        limit_fragments=2,
        fragment_limit=260,
    )
    if fragments:
        return " ".join(fragments)
    if findings:
        return (
            "Os registros disponíveis sustentam uma avaliação técnica preliminar com predominância dos seguintes pontos: "
            + "; ".join(_truncate_text_block(item, limit=150) for item in findings[:2])
            + "."
        )
    return (
        "Os registros disponíveis permitem consolidar uma avaliação técnica preliminar, "
        "sujeita à complementação de campo quando necessária."
    )


def _build_recommendations(
    *,
    laudo: Laudo,
    transcript: list[_TranscriptItem],
    evidences: list[_VisualEvidenceItem],
    findings: list[str],
) -> list[str]:
    recommendations: list[str | None] = []
    for evidence in evidences:
        recommendations.extend(evidence.key_points[:4])
        recommendations.extend(
            fragment
            for fragment in _extract_text_fragments(
                evidence.technical_analysis,
                limit_fragments=3,
                fragment_limit=180,
            )
            if _looks_like_action_item(fragment)
        )

    recommendations.extend(
        fragment
        for fragment in _extract_text_fragments(
            getattr(laudo, "parecer_ia", None),
            limit_fragments=3,
            fragment_limit=180,
        )
        if _looks_like_action_item(fragment)
    )

    if not recommendations and findings:
        recommendations.extend(
            [
                "Confirmar em campo a extensão das condições apontadas no material consolidado.",
                "Registrar identificação, rastreabilidade e evidências complementares dos pontos críticos antes da decisão final.",
                "Submeter os achados relevantes à validação técnica responsável para definição do tratamento aplicável.",
            ]
        )

    return _dedupe_text_blocks(
        [item for item in recommendations if _looks_like_action_item(item) or item in recommendations[:3]],
        limit=6,
    )


def _build_evidence_recommendations(evidence: _VisualEvidenceItem) -> list[str]:
    recommendations: list[str | None] = []
    recommendations.extend(evidence.key_points[:4])
    recommendations.extend(
        fragment
        for fragment in _extract_text_fragments(
            evidence.technical_analysis,
            limit_fragments=3,
            fragment_limit=180,
        )
        if _looks_like_action_item(fragment)
    )
    return _dedupe_text_blocks(
        [item for item in recommendations if _looks_like_action_item(item) or item in recommendations[:3]],
        limit=4,
    )


def _build_analysis_basis_text(
    *,
    laudo: Laudo,
    transcript: list[_TranscriptItem],
    evidences: list[_VisualEvidenceItem],
) -> str:
    references = _build_normative_references(transcript=transcript, evidences=evidences)
    lines: list[str | None] = [
        (
            "Base de análise: correlação entre narrativa do inspetor, "
            "evidências visuais anexadas e síntese técnica já registrada no caso."
        ),
        (
            "Procedimento adotado: consolidação documental do histórico "
            "disponível, com organização dos achados por contexto, evidência, "
            "conclusão e encaminhamento."
        ),
        (
            "Critérios e referências citados no registro: "
            + "; ".join(_truncate_text_block(item, limit=140) for item in references[:4])
            if references
            else (
                "Critérios e referências: não houve citação normativa estruturada "
                "suficiente no material de origem; manter validação técnica "
                "complementar quando aplicável."
            )
        ),
        (
            f"Modalidade de emissão: {REPORT_STATUS_LABEL.lower()}, elaborada a partir de {REPORT_KIND_LABEL.lower()}."
        ),
    ]
    return "\n\n".join(_dedupe_text_blocks(lines, limit=4))


def _build_cover_highlights(
    *,
    laudo: Laudo,
    transcript: list[_TranscriptItem],
    evidences: list[_VisualEvidenceItem],
) -> list[str]:
    findings = _build_consolidated_findings(transcript=transcript, evidences=evidences)
    recommendations = _build_recommendations(
        laudo=laudo,
        transcript=transcript,
        evidences=evidences,
        findings=findings,
    )
    context_line = _truncate_text_block(
        _best_context_line(laudo=laudo, transcript=transcript, evidences=evidences),
        limit=180,
    )
    return _dedupe_text_blocks(
        [
            f"Contexto principal: {context_line}" if context_line else None,
            (
                f"Escopo analisado: {len(transcript)} registro(s) textuais e {len(evidences)} evidência(s) visual(is)."
            ),
            (
                "Achado predominante: "
                + _truncate_text_block(findings[0], limit=180)
                if findings
                else "Achado predominante: material insuficiente para destacar um único ponto crítico."
            ),
            (
                "Encaminhamento inicial: "
                + _truncate_text_block(recommendations[0], limit=180)
                if recommendations
                else "Encaminhamento inicial: manter complementação técnica e validação responsável."
            ),
        ],
        limit=4,
    )


def _write_section_title(pdf: FPDF, title: str) -> None:
    pdf.set_fill_color(15, 43, 70)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(
        0,
        8,
        _pdf_text(f" {title}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
        fill=True,
    )
    pdf.ln(1.5)
    pdf.set_text_color(0, 0, 0)


def _content_width(pdf: FPDF) -> float:
    return max(float(pdf.w - pdf.l_margin - pdf.r_margin), 20.0)


def _write_block(pdf: FPDF, text: str, *, line_height: float = 6) -> None:
    normalized = str(text or "").strip()
    if not normalized:
        return
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(_content_width(pdf), line_height, normalized)


def _write_block_in_box(
    pdf: FPDF,
    text: str,
    *,
    x: float,
    y: float | None = None,
    width: float,
    line_height: float = 6,
) -> float:
    normalized = str(text or "").strip()
    if not normalized:
        return float(y if y is not None else pdf.get_y())
    if y is not None:
        pdf.set_xy(x, y)
    else:
        pdf.set_x(x)
    pdf.multi_cell(width, line_height, normalized)
    return float(pdf.get_y())


def _write_bullet_list(pdf: FPDF, items: list[str]) -> None:
    if not items:
        pdf.set_font("helvetica", "", 10)
        _write_block(pdf, "Nenhum item consolidado foi identificado para esta secao.")
        return

    pdf.set_font("helvetica", "", 10)
    for item in items:
        _write_block(pdf, f"- {_multiline_pdf_text(item)}")
        pdf.ln(0.5)


def _write_metadata(pdf: FPDF, *, laudo: Laudo, usuario: Usuario) -> None:
    empresa_nome = _pdf_text(
        getattr(getattr(usuario, "empresa", None), "nome_fantasia", None)
        or getattr(getattr(usuario, "empresa", None), "nome", None)
        or getattr(getattr(usuario, "empresa", None), "razao_social", None)
        or "Empresa"
    )
    pdf.set_font("helvetica", "", 10)
    metadata_lines = [
        f"Documento: #{int(laudo.id)}",
        f"Responsável pelo registro: {_pdf_text(usuario_nome(usuario)) or 'Inspetor'}",
        f"Empresa: {empresa_nome}",
        f"Contexto declarado: {_pdf_text(getattr(laudo, 'setor_industrial', None)) or 'geral'}",
        f"Modalidade: {REPORT_KIND_LABEL}",
        f"Status da emissão: {REPORT_STATUS_LABEL}",
        f"Data de emissão: {_format_datetime_label(datetime.now().astimezone())}",
    ]
    for line in metadata_lines:
        _write_block(pdf, line)
    pdf.ln(2)


def _write_metadata_in_box(
    pdf: FPDF,
    *,
    laudo: Laudo,
    usuario: Usuario,
    x: float,
    y: float,
    width: float,
    line_height: float = 5.3,
) -> float:
    empresa_nome = _pdf_text(
        getattr(getattr(usuario, "empresa", None), "nome_fantasia", None)
        or getattr(getattr(usuario, "empresa", None), "nome", None)
        or getattr(getattr(usuario, "empresa", None), "razao_social", None)
        or "Empresa"
    )
    metadata_lines = [
        f"Documento: #{int(laudo.id)}",
        f"Responsável pelo registro: {_pdf_text(usuario_nome(usuario)) or 'Inspetor'}",
        f"Empresa: {empresa_nome}",
        f"Contexto declarado: {_pdf_text(getattr(laudo, 'setor_industrial', None)) or 'geral'}",
        f"Modalidade: {REPORT_KIND_LABEL}",
        f"Status da emissão: {REPORT_STATUS_LABEL}",
        f"Data de emissão: {_format_datetime_label(datetime.now().astimezone())}",
    ]
    pdf.set_font("helvetica", "", 9.5)
    current_y = y
    for line in metadata_lines:
        current_y = _write_block_in_box(
            pdf,
            line,
            x=x,
            y=current_y,
            width=width,
            line_height=line_height,
        ) + 0.9
    return current_y


def _write_transcript(pdf: FPDF, transcript: list[_TranscriptItem]) -> None:
    if not transcript:
        pdf.set_font("helvetica", "", 10)
        _write_block(
            pdf,
            _pdf_text("Nenhuma interação textual relevante foi encontrada antes da solicitação do relatório."),
        )
        return

    for item in transcript[:8]:
        pdf.set_font("helvetica", "B", 10)
        _write_block(pdf, _pdf_text(f"{item.role_label} | {item.created_at_label}"))
        pdf.set_font("helvetica", "", 10)
        _write_block(pdf, _truncate_text_block(_multiline_pdf_text(item.text), limit=480))
        pdf.ln(1)
    if len(transcript) > 8:
        pdf.set_font("helvetica", "I", 9)
        _write_block(
            pdf,
            _pdf_text(
                f"Foram registradas {len(transcript)} interações relevantes. Esta seção mostra um extrato resumido."
            ),
        )


def _write_evidence_overview(pdf: FPDF, evidences: list[_VisualEvidenceItem]) -> None:
    pdf.set_font("helvetica", "", 10)
    if not evidences:
        _write_block(
            pdf,
            _pdf_text("Nenhuma evidência visual foi registrada até o momento."),
        )
        return

    _write_block(
        pdf,
        _pdf_text(
            f"Foram consolidadas {len(evidences)} evidência(s) visual(is) vinculada(s) ao registro."
        ),
    )
    pdf.ln(1)
    for index, evidence in enumerate(evidences, start=1):
        _write_block(
            pdf,
            _pdf_text(
                f"{index}. {evidence.display_name} | {evidence.created_at_label} | {evidence.verdict_label}"
            ),
        )
        pdf.set_font("helvetica", "", 10)
        _write_block(pdf, _truncate_text_block(evidence.summary, limit=260))
        if evidence.key_points:
            _write_block(
                pdf,
                _pdf_text(
                    "Pontos observados: "
                    + "; ".join(
                        _truncate_text_block(item, limit=120)
                        for item in evidence.key_points[:3]
                    )
                ),
            )
        pdf.ln(1)


def _render_cover_page(
    pdf: _FreeChatReportPdf,
    *,
    laudo: Laudo,
    usuario: Usuario,
    transcript: list[_TranscriptItem],
    evidences: list[_VisualEvidenceItem],
) -> None:
    pdf.add_mode_page("cover")
    pdf.set_fill_color(15, 43, 70)
    pdf.rect(0, 0, pdf.w, 56, style="F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(16, 18)
    pdf.set_font("helvetica", "B", 24)
    pdf.multi_cell(0, 11, _pdf_text(REPORT_TITLE))
    pdf.ln(2)
    pdf.set_x(16)
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(228, 233, 239)
    pdf.multi_cell(170, 6, _pdf_text(REPORT_SUBTITLE))
    pdf.ln(2)
    pdf.set_x(16)
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(255, 233, 208)
    pdf.cell(0, 6, _pdf_text(REPORT_STATUS_LABEL), ln=1)

    pdf.set_text_color(15, 43, 70)
    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(210, 220, 232)
    pdf.rect(16, 78, 82, 90, style="DF")
    pdf.rect(104, 78, 90, 90, style="DF")
    pdf.set_xy(24, 88)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, _pdf_text("Identificação do Documento"), ln=1)
    _write_metadata_in_box(
        pdf,
        laudo=laudo,
        usuario=usuario,
        x=24,
        y=97,
        width=66,
        line_height=5.0,
    )

    pdf.set_xy(112, 88)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, _pdf_text("Resumo Executivo"), ln=1)
    pdf.set_font("helvetica", "", 9.5)
    highlights = _build_cover_highlights(
        laudo=laudo,
        transcript=transcript,
        evidences=evidences,
    )
    current_y = 97.0
    for item in highlights:
        current_y = _write_block_in_box(
            pdf,
            item,
            x=112,
            y=current_y,
            width=74,
            line_height=5.0,
        ) + 1.4

    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(221, 229, 238)
    pdf.rect(16, 176, 178, 28, style="DF")
    pdf.set_xy(24, 184)
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(15, 43, 70)
    pdf.cell(0, 6, _pdf_text("Diretriz de leitura"), ln=1)
    pdf.ln(1)
    pdf.set_font("helvetica", "", 9.5)
    _write_block(
        pdf,
        _pdf_text(
            "Este laudo organiza o conteúdo em objetivo e escopo, base de análise, achados, conclusão, recomendações, "
            "referências técnicas e anexos de evidência, preservando a rastreabilidade em apêndice próprio."
        ),
        line_height=5.2,
    )


def _render_summary_page(
    pdf: _FreeChatReportPdf,
    *,
    outline: list[_ReportOutlineEntry],
) -> None:
    pdf.add_mode_page("summary")
    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(15, 43, 70)
    pdf.cell(
        0,
        10,
        _pdf_text("Sumário"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(4)
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(45, 45, 45)
    for index, entry in enumerate(outline, start=1):
        title = entry.title
        page_label = str(entry.page)
        available_width = max(_content_width(pdf) - 24, 40)
        title_width = min(pdf.get_string_width(title), available_width)
        dots_width = max(available_width - title_width - pdf.get_string_width(page_label), 10)
        dots_count = max(int(dots_width / pdf.get_string_width(".")), 6)
        dots = "." * dots_count
        _write_block(pdf, f"{index}. {title} {dots} {page_label}")
        pdf.ln(0.5)


def _render_back_cover(
    pdf: _FreeChatReportPdf,
    *,
    laudo: Laudo,
    usuario: Usuario,
) -> None:
    pdf.add_mode_page("back")
    pdf.set_fill_color(15, 43, 70)
    pdf.rect(0, 0, pdf.w, pdf.h, style="F")
    pdf.set_xy(18, 48)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 20)
    pdf.multi_cell(0, 10, _pdf_text("Encerramento"))
    pdf.ln(8)
    pdf.set_font("helvetica", "", 11)
    closing_blocks = [
        (
            "Este documento foi estruturado para leitura técnica profissional, "
            "com separação entre escopo, base de análise, achados, conclusão, "
            "recomendações e anexos."
        ),
        "As informações apresentadas refletem exclusivamente os registros, evidências e análises disponíveis no momento da emissão.",
        "Quando necessário, a validação humana complementar deve permanecer como etapa formal do processo técnico e decisório.",
        f"Documento #{int(laudo.id)} | {_pdf_text(usuario_nome(usuario)) or 'Inspetor'} | {_format_datetime_label(datetime.now().astimezone())}",
    ]
    for block in closing_blocks:
        pdf.multi_cell(170, 7, _pdf_text(block))
        pdf.ln(2)


def _fit_image_box(*, width_px: int, height_px: int, max_width: float, max_height: float) -> tuple[float, float]:
    if width_px <= 0 or height_px <= 0:
        return max_width, min(max_height, max_width)
    ratio = width_px / height_px
    width = max_width
    height = width / ratio if ratio else max_height
    if height > max_height:
        height = max_height
        width = height * ratio if ratio else max_width
    return width, height


def _render_evidence_pages(
    pdf: _FreeChatReportPdf,
    evidences: list[_VisualEvidenceItem],
    temp_files: list[str],
) -> None:
    for index, evidence in enumerate(evidences, start=1):
        pdf.add_mode_page("body")
        _write_section_title(pdf, f"Evidência {index}")
        pdf.set_font("helvetica", "B", 11)
        _write_block(pdf, evidence.display_name)
        pdf.ln(1)
        pdf.set_font("helvetica", "", 10)
        _write_block(pdf, _pdf_text(f"Registro: {evidence.created_at_label}"))
        _write_block(pdf, _pdf_text(f"Classificação: {evidence.verdict_label}"))
        pdf.ln(3)

        image_path = evidence.file_path
        try:
            with Image.open(evidence.file_path) as image:
                width_px, height_px = image.size
                if str(image.format or "").upper() not in {"PNG", "JPEG", "JPG"}:
                    converted = tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=".png",
                    )
                    converted.close()
                    image.convert("RGB").save(converted.name, format="PNG")
                    temp_files.append(converted.name)
                    image_path = converted.name
                image_width, image_height = _fit_image_box(
                    width_px=width_px,
                    height_px=height_px,
                    max_width=180.0,
                    max_height=96.0,
                )
        except Exception:
            pdf.set_text_color(160, 30, 30)
            _write_block(
                pdf,
                _pdf_text("Não foi possível embutir esta evidência visual no PDF."),
            )
            pdf.set_text_color(0, 0, 0)
        else:
            pos_x = max((pdf.w - image_width) / 2, pdf.l_margin)
            pdf.image(image_path, x=pos_x, y=pdf.get_y(), w=image_width, h=image_height)
            pdf.ln(image_height + 4)

        _write_section_title(pdf, "Descrição Consolidada")
        pdf.set_font("helvetica", "", 10)
        _write_block(pdf, _truncate_text_block(evidence.summary, limit=420))
        if evidence.context_text:
            pdf.ln(1)
            _write_section_title(pdf, "Contexto Informado")
            pdf.set_font("helvetica", "", 10)
            _write_block(pdf, _truncate_text_block(evidence.context_text, limit=520))
        if evidence.key_points:
            pdf.ln(1)
            _write_section_title(pdf, "Pontos Relevantes")
            _write_bullet_list(pdf, evidence.key_points[:6])
        if evidence.technical_analysis:
            pdf.ln(1)
            _write_section_title(pdf, "Avaliação Técnica")
            pdf.set_font("helvetica", "", 10)
            _write_block(pdf, _truncate_text_block(evidence.technical_analysis, limit=1400))
        recommendations = _build_evidence_recommendations(evidence)
        if recommendations:
            pdf.ln(1)
            _write_section_title(pdf, "Encaminhamentos Sugeridos")
            _write_bullet_list(pdf, recommendations[:4])
        if evidence.norm_refs:
            pdf.ln(1)
            _write_section_title(pdf, "Critérios e Referências")
            _write_bullet_list(pdf, evidence.norm_refs[:6])


def _render_report_body(
    pdf: _FreeChatReportPdf,
    *,
    laudo: Laudo,
    usuario: Usuario,
    transcript: list[_TranscriptItem],
    evidences: list[_VisualEvidenceItem],
    outline: list[_ReportOutlineEntry],
    temp_files_to_remove: list[str],
) -> None:
    pdf.add_mode_page("body")
    findings = _build_consolidated_findings(
        transcript=transcript,
        evidences=evidences,
    )
    recommendations = _build_recommendations(
        laudo=laudo,
        transcript=transcript,
        evidences=evidences,
        findings=findings,
    )
    normative_refs = _build_normative_references(
        transcript=transcript,
        evidences=evidences,
    )

    _register_outline_entry(outline, "Identificação e Contexto", pdf.page_no())
    _write_section_title(pdf, "Identificação e Contexto")
    _write_metadata(pdf, laudo=laudo, usuario=usuario)
    pdf.ln(2)

    _register_outline_entry(outline, "Objetivo e Escopo", pdf.page_no())
    _write_section_title(pdf, "Objetivo e Escopo")
    pdf.set_font("helvetica", "", 10)
    _write_block(
        pdf,
        _build_scope_text(
            laudo=laudo,
            transcript=transcript,
            evidences=evidences,
        ),
    )
    pdf.ln(2)

    _register_outline_entry(outline, "Base de Análise e Critérios", pdf.page_no())
    _write_section_title(pdf, "Base de Análise e Critérios")
    pdf.set_font("helvetica", "", 10)
    _write_block(
        pdf,
        _build_analysis_basis_text(
            laudo=laudo,
            transcript=transcript,
            evidences=evidences,
        ),
    )
    pdf.ln(2)

    _register_outline_entry(outline, "Síntese Executiva", pdf.page_no())
    _write_section_title(pdf, "Síntese Executiva")
    pdf.set_font("helvetica", "", 10)
    _write_block(
        pdf,
        _build_summary_text(
            laudo=laudo,
            transcript=transcript,
            evidences=evidences,
        ),
    )
    pdf.ln(2)

    _register_outline_entry(outline, "Achados Técnicos", pdf.page_no())
    _write_section_title(pdf, "Achados Técnicos")
    _write_bullet_list(pdf, findings)
    pdf.ln(2)

    _register_outline_entry(outline, "Conclusão Técnica", pdf.page_no())
    _write_section_title(pdf, "Conclusão Técnica")
    pdf.set_font("helvetica", "", 10)
    _write_block(pdf, _build_conclusion_text(laudo=laudo, findings=findings))
    pdf.ln(2)

    _register_outline_entry(outline, "Recomendações e Próximos Passos", pdf.page_no())
    _write_section_title(pdf, "Recomendações e Próximos Passos")
    _write_bullet_list(pdf, recommendations)
    pdf.ln(2)

    if normative_refs:
        _register_outline_entry(outline, "Referências Normativas", pdf.page_no())
        _write_section_title(pdf, "Referências Normativas")
        _write_bullet_list(pdf, normative_refs)
        pdf.ln(2)

    _register_outline_entry(outline, "Resumo das Evidências", pdf.page_no())
    _write_section_title(pdf, "Resumo das Evidências")
    _write_evidence_overview(pdf, evidences)
    pdf.ln(2)

    if evidences:
        _register_outline_entry(outline, "Caderno de Evidências", pdf.page_no() + 1)
        _render_evidence_pages(pdf, evidences, temp_files_to_remove)

    if transcript:
        pdf.add_mode_page("body")
        _register_outline_entry(outline, "Apêndice A | Rastreabilidade do Registro", pdf.page_no())
        _write_section_title(pdf, "Apêndice A | Rastreabilidade do Registro")
        _write_transcript(pdf, transcript)


def _generate_pdf_file(
    *,
    laudo: Laudo,
    usuario: Usuario,
    transcript: list[_TranscriptItem],
    evidences: list[_VisualEvidenceItem],
) -> str:
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_pdf.close()
    temp_files_to_remove: list[str] = []

    def _build_pdf(
        *,
        temp_files: list[str],
        summary_outline: list[_ReportOutlineEntry],
    ) -> tuple[_FreeChatReportPdf, list[_ReportOutlineEntry]]:
        pdf = _FreeChatReportPdf(unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_title(_pdf_text(f"{REPORT_TITLE} #{int(laudo.id)}"))
        outline: list[_ReportOutlineEntry] = []

        _render_cover_page(
            pdf,
            laudo=laudo,
            usuario=usuario,
            transcript=transcript,
            evidences=evidences,
        )
        _render_summary_page(pdf, outline=summary_outline)
        _render_report_body(
            pdf,
            laudo=laudo,
            usuario=usuario,
            transcript=transcript,
            evidences=evidences,
            outline=outline,
            temp_files_to_remove=temp_files,
        )
        _render_back_cover(pdf, laudo=laudo, usuario=usuario)
        return pdf, outline

    try:
        preview_temp_files: list[str] = []
        _, outline = _build_pdf(
            temp_files=preview_temp_files,
            summary_outline=[],
        )
        for path in preview_temp_files:
            safe_remove_file(path)

        pdf, _ = _build_pdf(
            temp_files=temp_files_to_remove,
            summary_outline=outline,
        )

        pdf.output(temp_pdf.name)
        for path in temp_files_to_remove:
            safe_remove_file(path)
        return temp_pdf.name
    except Exception:
        for path in [*temp_files_to_remove, temp_pdf.name]:
            safe_remove_file(path)
        raise


def generate_free_chat_report_result(
    *,
    banco: Session,
    laudo: Laudo,
    usuario: Usuario,
    request_message_id: int,
) -> FreeChatReportGenerationResult:
    transcript = _build_transcript(
        banco=banco,
        laudo_id=int(laudo.id),
        request_message_id=int(request_message_id),
    )
    evidences = _build_visual_evidence(
        banco=banco,
        laudo_id=int(laudo.id),
        transcript=transcript,
    )

    if not transcript and not evidences and not str(getattr(laudo, "parecer_ia", "") or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Envie observações, imagens ou documentos antes de solicitar o relatório em PDF.",
        )

    pdf_path = _generate_pdf_file(
        laudo=laudo,
        usuario=usuario,
        transcript=transcript,
        evidences=evidences,
    )
    try:
        pdf_bytes = Path(pdf_path).read_bytes()
    finally:
        safe_remove_file(pdf_path)

    message_text = (
        "Relatório técnico consolidado gerado em PDF com base nas evidências e observações registradas. "
        "O arquivo está anexado logo abaixo para download."
    )
    assistant_message = MensagemLaudo(
        laudo_id=int(laudo.id),
        remetente_id=int(usuario.id),
        tipo=TipoMensagem.IA.value,
        conteudo=message_text,
        custo_api_reais=Decimal("0.0000"),
    )
    banco.add(assistant_message)
    banco.flush()

    attachment_data = salvar_arquivo_anexo_mesa(
        empresa_id=int(usuario.empresa_id),
        laudo_id=int(laudo.id),
        nome_original=f"relatorio_tecnico_inspecao_{int(laudo.id)}.pdf",
        mime_type="application/pdf",
        conteudo=pdf_bytes,
    )
    attachment = AnexoMesa(
        laudo_id=int(laudo.id),
        mensagem_id=int(assistant_message.id),
        enviado_por_id=int(usuario.id),
        **attachment_data,
    )
    banco.add(attachment)
    laudo.atualizado_em = datetime.now().astimezone()
    banco.flush()
    commit_ou_rollback_operacional(
        banco,
        logger_operacao=chat_logger,
        mensagem_erro="Falha ao persistir o relatório PDF do chat livre.",
    )

    return FreeChatReportGenerationResult(
        message_text=message_text,
        attachment_payload=serializar_anexos_mesa([attachment], portal="app")[0],
        message_id=int(assistant_message.id),
        laudo_card_payload=serializar_card_laudo(banco, laudo),
    )


def build_free_chat_report_response(
    *,
    banco: Session,
    laudo: Laudo,
    usuario: Usuario,
    request_message_id: int,
) -> JSONResponse:
    result = generate_free_chat_report_result(
        banco=banco,
        laudo=laudo,
        usuario=usuario,
        request_message_id=request_message_id,
    )
    return JSONResponse(
        {
            "tipo": "relatorio_chat_livre",
            "texto": result.message_text,
            "mensagem_id": result.message_id,
            "laudo_id": int(laudo.id),
            "laudo_card": result.laudo_card_payload,
            "anexos": [result.attachment_payload],
        }
    )


__all__ = [
    "FreeChatReportGenerationResult",
    "build_free_chat_report_response",
    "generate_free_chat_report_result",
]
