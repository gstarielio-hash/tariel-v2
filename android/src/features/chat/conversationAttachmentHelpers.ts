import type { MobileAttachment, MobileLaudoCard } from "../../types/mobile";
import { stripEmbeddedChatAiPreferences } from "./preferences";
import type { ComposerAttachment } from "./types";
import { normalizarUrlAnexo } from "./attachmentUtils";

export function normalizarAnexoMensagem(
  payload: unknown,
): MobileAttachment | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const registro = payload as Record<string, unknown>;
  const attachment: MobileAttachment = {
    id: typeof registro.id === "number" ? registro.id : undefined,
    nome: typeof registro.nome === "string" ? registro.nome : undefined,
    nome_original:
      typeof registro.nome_original === "string"
        ? registro.nome_original
        : undefined,
    nome_arquivo:
      typeof registro.nome_arquivo === "string"
        ? registro.nome_arquivo
        : undefined,
    label: typeof registro.label === "string" ? registro.label : undefined,
    mime_type:
      typeof registro.mime_type === "string" ? registro.mime_type : undefined,
    categoria:
      typeof registro.categoria === "string" ? registro.categoria : undefined,
    tamanho_bytes:
      typeof registro.tamanho_bytes === "number"
        ? registro.tamanho_bytes
        : undefined,
    eh_imagem:
      typeof registro.eh_imagem === "boolean" ? registro.eh_imagem : undefined,
    url:
      typeof registro.url === "string"
        ? normalizarUrlAnexo(registro.url)
        : undefined,
  };

  if (
    !attachment.id &&
    !attachment.nome &&
    !attachment.nome_original &&
    !attachment.label &&
    !attachment.url
  ) {
    return null;
  }

  return attachment;
}

export function normalizarLaudoCardResumo<T extends MobileLaudoCard | null>(
  card: T,
): T {
  if (!card) {
    return card;
  }
  return {
    ...card,
    preview: stripEmbeddedChatAiPreferences(card.preview, {
      fallbackHiddenOnly: "Evidência enviada",
    }),
  } as T;
}

export function normalizarComposerAttachment(
  payload: unknown,
): ComposerAttachment | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const registro = payload as Record<string, unknown>;
  if (registro.kind === "image") {
    const dadosImagem =
      typeof registro.dadosImagem === "string" ? registro.dadosImagem : "";
    const previewUri =
      typeof registro.previewUri === "string" ? registro.previewUri : "";
    const fileUri =
      typeof registro.fileUri === "string" ? registro.fileUri : "";
    const mimeType =
      typeof registro.mimeType === "string" ? registro.mimeType : "image/jpeg";
    const label = typeof registro.label === "string" ? registro.label : "";
    const resumo = typeof registro.resumo === "string" ? registro.resumo : "";
    if (!dadosImagem || !previewUri || !fileUri || !label) {
      return null;
    }
    return {
      kind: "image",
      dadosImagem,
      previewUri,
      fileUri,
      mimeType,
      label,
      resumo,
    };
  }

  if (registro.kind === "document") {
    const label = typeof registro.label === "string" ? registro.label : "";
    const resumo = typeof registro.resumo === "string" ? registro.resumo : "";
    const textoDocumento =
      typeof registro.textoDocumento === "string"
        ? registro.textoDocumento
        : "";
    const nomeDocumento =
      typeof registro.nomeDocumento === "string" ? registro.nomeDocumento : "";
    const fileUri =
      typeof registro.fileUri === "string" ? registro.fileUri : "";
    const mimeType =
      typeof registro.mimeType === "string"
        ? registro.mimeType
        : "application/octet-stream";
    if (!label || !nomeDocumento || !fileUri) {
      return null;
    }
    return {
      kind: "document",
      label,
      resumo,
      textoDocumento,
      nomeDocumento,
      chars: typeof registro.chars === "number" ? registro.chars : 0,
      truncado: Boolean(registro.truncado),
      fileUri,
      mimeType,
    };
  }

  return null;
}

export function duplicarComposerAttachment(
  anexo: ComposerAttachment | null,
): ComposerAttachment | null {
  if (!anexo) {
    return null;
  }
  return anexo.kind === "image" ? { ...anexo } : { ...anexo };
}

export function textoFallbackAnexo(anexo: ComposerAttachment | null): string {
  if (!anexo) {
    return "";
  }
  if (anexo.kind === "image") {
    return "Imagem enviada";
  }
  return `Documento: ${anexo.nomeDocumento}`;
}
