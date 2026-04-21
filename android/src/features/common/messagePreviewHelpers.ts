import type { MobileChatMessage, MobileMesaMessage } from "../../types/mobile";

export function resumoMensagemAtividade(
  texto: string,
  fallback: string,
): string {
  const valor = String(texto || "")
    .trim()
    .replace(/\s+/g, " ");
  if (!valor) {
    return fallback;
  }
  return valor.length > 120 ? `${valor.slice(0, 117)}...` : valor;
}

export function obterResumoReferenciaMensagem(
  referenciaId: number | null | undefined,
  mensagensChat: MobileChatMessage[],
  mensagensMesa: MobileMesaMessage[],
): string {
  const alvo = Number(referenciaId || 0) || null;
  if (!alvo) {
    return "";
  }

  const mensagemChat = mensagensChat.find(
    (item) => Number(item.id || 0) === alvo,
  );
  if (mensagemChat?.texto?.trim()) {
    return resumoMensagemAtividade(mensagemChat.texto, `Mensagem #${alvo}`);
  }

  const mensagemMesa = mensagensMesa.find(
    (item) => Number(item.id || 0) === alvo,
  );
  if (mensagemMesa?.texto?.trim()) {
    return resumoMensagemAtividade(mensagemMesa.texto, `Mensagem #${alvo}`);
  }

  return `Mensagem #${alvo}`;
}
