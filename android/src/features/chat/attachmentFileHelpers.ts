import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";

import type { MobileAttachment } from "../../types/mobile";
import { nomeExibicaoAnexo } from "./attachmentUtils";
import type { ComposerAttachment } from "./types";

export function nomeArquivoSeguro(nome: string, fallback: string): string {
  const base = String(nome || "").trim();
  const semSeparadores = base
    .replace(/[\\/:*?"<>|]+/g, "-")
    .replace(/\s+/g, " ")
    .trim();
  return semSeparadores || fallback;
}

export function inferirExtensaoAnexo(anexo: MobileAttachment): string {
  const nome = nomeExibicaoAnexo(anexo, "anexo").toLowerCase();
  const correspondencias = [
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".pdf",
    ".docx",
    ".doc",
  ];

  for (const extensao of correspondencias) {
    if (nome.endsWith(extensao)) {
      return extensao;
    }
  }

  const mime = String(anexo.mime_type || "").toLowerCase();
  if (mime.includes("png")) {
    return ".png";
  }
  if (mime.includes("jpeg") || mime.includes("jpg")) {
    return ".jpg";
  }
  if (mime.includes("webp")) {
    return ".webp";
  }
  if (mime.includes("pdf")) {
    return ".pdf";
  }
  if (mime.includes("wordprocessingml") || mime.includes("docx")) {
    return ".docx";
  }
  if (mime.includes("msword")) {
    return ".doc";
  }
  return "";
}

export function chaveAnexo(anexo: MobileAttachment, fallback: string): string {
  const partes = [
    anexo.id,
    anexo.url,
    anexo.nome,
    anexo.nome_original,
    anexo.label,
  ]
    .map((parte) => String(parte ?? "").trim())
    .filter(Boolean);

  return partes.join(":") || fallback;
}

export function montarAnexoImagem(
  asset: ImagePicker.ImagePickerAsset,
  resumo: string,
): ComposerAttachment {
  if (!asset.base64) {
    throw new Error("Não foi possível preparar a imagem selecionada.");
  }

  const mimeType = (asset.mimeType || "image/jpeg").replace(
    "image/jpg",
    "image/jpeg",
  );
  const nomeArquivo =
    asset.fileName?.trim() ||
    `evidencia-${Date.now()}.${mimeType.includes("png") ? "png" : mimeType.includes("webp") ? "webp" : "jpg"}`;

  return {
    kind: "image",
    label: nomeArquivo,
    resumo,
    dadosImagem: `data:${mimeType};base64,${asset.base64}`,
    previewUri: asset.uri,
    fileUri: asset.uri,
    mimeType,
  };
}

export function montarAnexoDocumentoLocal(
  asset: DocumentPicker.DocumentPickerAsset,
  resumo: string,
): ComposerAttachment {
  return {
    kind: "document",
    label: asset.name,
    resumo,
    textoDocumento: "",
    nomeDocumento: asset.name,
    chars: 0,
    truncado: false,
    fileUri: asset.uri,
    mimeType: asset.mimeType || "application/octet-stream",
  };
}

export function montarAnexoDocumentoMesa(
  asset: DocumentPicker.DocumentPickerAsset,
): ComposerAttachment {
  return montarAnexoDocumentoLocal(
    asset,
    "Documento pronto para seguir direto para a mesa avaliadora.",
  );
}
