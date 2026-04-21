import type { MobileChatMode } from "../../types/mobile";
import type { ActiveThread, ChatState } from "./types";

export function chaveCacheLaudo(laudoId: number | null): string {
  return laudoId ? `laudo:${laudoId}` : "rascunho";
}

export function chaveRascunho(
  thread: ActiveThread,
  laudoId: number | null,
): string {
  return `${thread}:${chaveCacheLaudo(laudoId)}`;
}

export function normalizarModoChat(
  modo: unknown,
  fallback: MobileChatMode = "detalhado",
): MobileChatMode {
  const valor = String(modo || "")
    .trim()
    .toLowerCase();
  if (valor === "curto") {
    return "curto";
  }
  if (valor === "deep_research" || valor === "deepresearch") {
    return "deep_research";
  }
  if (valor === "detalhado") {
    return "detalhado";
  }
  return fallback;
}

export function inferirSetorConversa(
  conversa: ChatState | null | undefined,
): string {
  const tipoTemplate = String(conversa?.laudoCard?.tipo_template || "")
    .trim()
    .toLowerCase();

  if (tipoTemplate === "rti" || tipoTemplate === "nr10_rti") {
    return "rti";
  }
  if (
    tipoTemplate === "spda" ||
    tipoTemplate === "pie" ||
    tipoTemplate === "loto"
  ) {
    return tipoTemplate;
  }
  if (tipoTemplate === "cbmgo" || tipoTemplate === "avcb") {
    return "avcb";
  }
  if (tipoTemplate.startsWith("nr11")) {
    return "nr11";
  }
  if (
    tipoTemplate === "nr12" ||
    tipoTemplate === "nr12_maquinas" ||
    tipoTemplate === "nr12maquinas" ||
    tipoTemplate.startsWith("nr12_")
  ) {
    return "nr12";
  }
  if (
    tipoTemplate === "nr13" ||
    tipoTemplate === "nr13_caldeira" ||
    tipoTemplate.startsWith("nr13_")
  ) {
    return "nr13";
  }
  if (tipoTemplate === "nr10" || tipoTemplate.startsWith("nr10_")) {
    return "nr10";
  }
  if (tipoTemplate.startsWith("nr20")) {
    return "nr20";
  }
  if (tipoTemplate.startsWith("nr33")) {
    return "nr33";
  }
  if (tipoTemplate === "nr35" || tipoTemplate.startsWith("nr35_")) {
    return "nr35";
  }
  return "geral";
}
