import { MaterialCommunityIcons } from "@expo/vector-icons";

import type { MobileChatMode } from "../../types/mobile";
import {
  duplicarComposerAttachment,
  normalizarModoChat,
  textoFallbackAnexo,
} from "../chat/conversationHelpers";
import type { ComposerAttachment, OfflinePendingMessage } from "../chat/types";

function rotuloEtapaGuiadaPendente(
  item: Pick<OfflinePendingMessage, "attachment" | "guidedInspectionDraft">,
): string {
  const draft = item.guidedInspectionDraft;
  if (!draft || !Array.isArray(draft.checklist) || !draft.checklist.length) {
    return "";
  }

  const currentIndex = Math.min(
    Math.max(Number(draft.current_step_index) || 0, 0),
    draft.checklist.length - 1,
  );
  const stepTitle = String(draft.checklist[currentIndex]?.title || "").trim();
  if (!stepTitle) {
    return "";
  }

  if (item.attachment?.kind === "image") {
    return `Imagem da etapa ${stepTitle}`;
  }
  if (item.attachment?.kind === "document") {
    return `Documento da etapa ${stepTitle}`;
  }
  return `Etapa guiada: ${stepTitle}`;
}

export function resumoPendenciaOffline(
  item: Pick<
    OfflinePendingMessage,
    "attachment" | "operation" | "qualityGateDecision" | "text"
  >,
): string {
  if (item.operation === "quality_gate_finalize") {
    return item.qualityGateDecision?.reason
      ? "Finalização com exceção governada"
      : "Finalização do caso pendente";
  }
  if (item.text.trim()) {
    return item.text.trim();
  }
  return textoFallbackAnexo(item.attachment);
}

export function iconePendenciaOffline(
  item: OfflinePendingMessage,
): keyof typeof MaterialCommunityIcons.glyphMap {
  if (item.operation === "quality_gate_finalize") {
    return "check-decagram-outline";
  }
  if (item.channel === "mesa") {
    return item.attachment ? "paperclip" : "clipboard-text-outline";
  }
  if (item.attachment?.kind === "image") {
    return "image-outline";
  }
  if (item.attachment?.kind === "document") {
    return "file-document-outline";
  }
  return "message-processing-outline";
}

export function legendaPendenciaOffline(item: OfflinePendingMessage): string {
  if (item.operation === "quality_gate_finalize") {
    return item.qualityGateDecision?.reason
      ? "Exceção governada pronta para reenviar"
      : "Finalização pronta para reenviar";
  }
  const rotuloGuiado = rotuloEtapaGuiadaPendente(item);
  if (rotuloGuiado) {
    return rotuloGuiado;
  }
  if (item.attachment?.kind === "image") {
    return "Imagem pronta para reenvio";
  }
  if (item.attachment?.kind === "document") {
    return "Documento pronto para reenvio";
  }
  return "Texto pendente para reenviar";
}

export function resumirErroPendenciaOffline(erro: string): string {
  const texto = erro.trim();
  if (!texto) {
    return "";
  }
  return texto.length > 72 ? `${texto.slice(0, 69).trimEnd()}...` : texto;
}

export function calcularBackoffPendenciaOfflineMs(tentativas: number): number {
  if (tentativas <= 1) {
    return 30_000;
  }
  if (tentativas === 2) {
    return 120_000;
  }
  if (tentativas === 3) {
    return 300_000;
  }
  return 600_000;
}

export function pendenciaFilaProntaParaReenvio(
  item: OfflinePendingMessage,
  referencia = Date.now(),
): boolean {
  if (!item.nextRetryAt) {
    return true;
  }
  const proximaTentativa = new Date(item.nextRetryAt).getTime();
  if (Number.isNaN(proximaTentativa)) {
    return true;
  }
  return proximaTentativa <= referencia;
}

export function detalheBackoffPendenciaOffline(
  item: OfflinePendingMessage,
  formatarHorarioAtividade: (dataIso: string) => string,
): string {
  if (!item.nextRetryAt) {
    return "";
  }
  const proximaTentativa = new Date(item.nextRetryAt);
  if (Number.isNaN(proximaTentativa.getTime())) {
    return "";
  }
  return `Próxima tentativa após ${formatarHorarioAtividade(item.nextRetryAt)}`;
}

export function prioridadePendenciaOffline(
  item: OfflinePendingMessage,
): number {
  if (item.lastError) {
    return 0;
  }
  if (pendenciaFilaProntaParaReenvio(item)) {
    return 1;
  }
  return 2;
}

export function rotuloStatusPendenciaOffline(
  item: OfflinePendingMessage,
): string {
  if (item.lastError) {
    return "Com falha";
  }
  if (item.lastAttemptAt) {
    return "Tentado";
  }
  return "Pendente";
}

export function detalheStatusPendenciaOffline(
  item: OfflinePendingMessage,
  formatarHorarioAtividade: (dataIso: string) => string,
): string {
  if (item.lastError) {
    const tentativas =
      item.attempts <= 1 ? "1 tentativa" : `${item.attempts} tentativas`;
    const backoff = detalheBackoffPendenciaOffline(
      item,
      formatarHorarioAtividade,
    );
    return `${tentativas} · ${resumirErroPendenciaOffline(item.lastError)}${backoff ? ` · ${backoff}` : ""}`;
  }
  if (item.lastAttemptAt) {
    return `Última tentativa em ${formatarHorarioAtividade(item.lastAttemptAt)}`;
  }
  return "Aguardando a primeira tentativa de reenvio";
}

export function criarItemFilaOffline(params: {
  channel: OfflinePendingMessage["channel"];
  operation?: OfflinePendingMessage["operation"];
  laudoId: number | null;
  text: string;
  title: string;
  attachment?: ComposerAttachment | null;
  referenceMessageId?: number | null;
  clientMessageId?: string | null;
  qualityGateDecision?: OfflinePendingMessage["qualityGateDecision"];
  guidedInspectionDraft?: OfflinePendingMessage["guidedInspectionDraft"];
  aiMode?: MobileChatMode;
  aiSummary?: string;
  aiMessagePrefix?: string;
}): OfflinePendingMessage {
  return {
    id: `${params.channel}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    channel: params.channel,
    operation: params.operation || "message",
    laudoId: params.laudoId,
    text: params.text.trim(),
    createdAt: new Date().toISOString(),
    title: params.title.trim() || "Mensagem pendente",
    attachment: duplicarComposerAttachment(params.attachment || null),
    referenceMessageId: Number(params.referenceMessageId || 0) || null,
    clientMessageId: String(params.clientMessageId || "").trim() || null,
    qualityGateDecision: params.qualityGateDecision
      ? {
          reason: String(params.qualityGateDecision.reason || "").trim(),
          requestedCases: Array.isArray(
            params.qualityGateDecision.requestedCases,
          )
            ? params.qualityGateDecision.requestedCases
                .map((item) => String(item || "").trim())
                .filter(Boolean)
            : [],
          responsibilityNotice: String(
            params.qualityGateDecision.responsibilityNotice || "",
          ).trim(),
          gateSnapshot: params.qualityGateDecision.gateSnapshot || null,
        }
      : null,
    guidedInspectionDraft: params.guidedInspectionDraft || null,
    attempts: 0,
    lastAttemptAt: "",
    lastError: "",
    nextRetryAt: "",
    aiMode: normalizarModoChat(params.aiMode, "detalhado"),
    aiSummary: String(params.aiSummary || "").trim(),
    aiMessagePrefix: String(params.aiMessagePrefix || "").trim(),
  };
}
