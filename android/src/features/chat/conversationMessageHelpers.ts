import type {
  MobileAttachment,
  MobileChatMessage,
  MobileChatMode,
  MobileChatSendResult,
} from "../../types/mobile";
import { stripEmbeddedChatAiPreferences } from "./preferences";
import { normalizarAnexoMensagem } from "./conversationAttachmentHelpers";
import { normalizarModoChat } from "./conversationModeHelpers";

export function sanitizarTextoMensagemChat(
  texto: string,
  options?: { papel?: MobileChatMessage["papel"] },
): string {
  const papel = options?.papel || "usuario";
  const textoSanitizado = stripEmbeddedChatAiPreferences(texto, {
    fallbackHiddenOnly: papel === "usuario" ? "Evidência enviada" : "",
  });

  if (papel !== "assistente") {
    return textoSanitizado;
  }

  return sanitizarFalhaOperacionalAssistente(textoSanitizado);
}

function sanitizarFalhaOperacionalAssistente(texto: string): string {
  const conteudo = texto.trim();
  if (!conteudo) {
    return conteudo;
  }

  const conteudoNormalizado = conteudo.toLowerCase();
  const erroBrutoGemini =
    (conteudoNormalizado.includes("[erro]") ||
      conteudoNormalizado.includes("**[erro]**")) &&
    (conteudoNormalizado.includes("api key expired") ||
      conteudoNormalizado.includes("apikeyinvalid") ||
      conteudoNormalizado.includes("invalidargument") ||
      conteudoNormalizado.includes("google.rpc") ||
      conteudoNormalizado.includes("generativelanguage.googleapis.com"));

  if (erroBrutoGemini) {
    return "A IA está temporariamente indisponível neste ambiente. Tente novamente em instantes.";
  }

  if (
    conteudoNormalizado.includes("[limite de taxa]") ||
    conteudoNormalizado.includes("rate limit")
  ) {
    return "A IA está com muitas requisições agora. Tente novamente em instantes.";
  }

  if (
    conteudoNormalizado.includes("[serviço indisponível]") ||
    conteudoNormalizado.includes("[servico indisponivel]") ||
    conteudoNormalizado.includes("[erro interno]")
  ) {
    return "A IA está temporariamente indisponível. Tente novamente em instantes.";
  }

  return conteudo;
}

export function normalizarMensagemChat(
  mensagem: MobileChatMessage,
): MobileChatMessage | null {
  const texto = sanitizarTextoMensagemChat(mensagem.texto, {
    papel: mensagem.papel,
  });
  if (!texto) {
    return null;
  }
  return {
    ...mensagem,
    texto,
    anexos: Array.isArray(mensagem.anexos)
      ? mensagem.anexos
          .map((item) => normalizarAnexoMensagem(item))
          .filter((item): item is MobileAttachment => item !== null)
      : mensagem.anexos,
  };
}

export function normalizarMensagensChat(
  mensagens: MobileChatMessage[],
): MobileChatMessage[] {
  return mensagens
    .map((mensagem) => normalizarMensagemChat(mensagem))
    .filter((mensagem): mensagem is MobileChatMessage => mensagem !== null);
}

function extrairAnexosMensagemAssistente(
  resposta: MobileChatSendResult,
): MobileAttachment[] | undefined {
  const events = Array.isArray(resposta.events) ? resposta.events : [];
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (!Array.isArray(event?.anexos)) {
      continue;
    }
    const anexos = event.anexos
      .map((item) => normalizarAnexoMensagem(item))
      .filter((item): item is MobileAttachment => item !== null);
    if (anexos.length) {
      return anexos;
    }
  }
  return undefined;
}

export function montarHistoricoParaEnvio(
  mensagens: MobileChatMessage[],
): Array<{ papel: "usuario" | "assistente"; texto: string }> {
  return mensagens
    .filter(
      (mensagem) =>
        (mensagem.papel === "usuario" || mensagem.papel === "assistente") &&
        typeof mensagem.texto === "string" &&
        mensagem.texto.trim(),
    )
    .slice(-20)
    .map((mensagem) => {
      const papel: "usuario" | "assistente" =
        mensagem.papel === "usuario" ? "usuario" : "assistente";
      return {
        papel,
        texto: sanitizarTextoMensagemChat(mensagem.texto, { papel }).trim(),
      };
    })
    .filter((mensagem) => Boolean(mensagem.texto));
}

export function extrairModoConversaDasMensagens(
  mensagens: MobileChatMessage[],
): MobileChatMode {
  for (let index = mensagens.length - 1; index >= 0; index -= 1) {
    const mensagem = mensagens[index];
    if (typeof mensagem?.modo === "string" && mensagem.modo.trim()) {
      return normalizarModoChat(mensagem.modo);
    }
  }
  return "detalhado";
}

export function criarMensagemAssistenteServidor(
  resposta: MobileChatSendResult,
): MobileChatMessage | null {
  const texto = sanitizarTextoMensagemChat(resposta.assistantText, {
    papel: "assistente",
  }).trim();
  if (!texto) {
    return null;
  }

  return {
    id: Date.now() + 1,
    papel: "assistente",
    texto,
    tipo: "assistant",
    modo: normalizarModoChat(resposta.modo),
    anexos: extrairAnexosMensagemAssistente(resposta),
    citacoes: resposta.citacoes.length ? resposta.citacoes : undefined,
    confianca_ia: resposta.confiancaIa || undefined,
  };
}
