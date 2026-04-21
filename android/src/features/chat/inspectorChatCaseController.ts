import type { Dispatch, MutableRefObject, SetStateAction } from "react";

import {
  carregarLaudosMobile,
  carregarMensagensLaudo,
  carregarStatusLaudo,
} from "../../config/api";
import type {
  MobileLaudoCard,
  MobileLaudoMensagensResponse,
  MobileLaudoStatusResponse,
  MobileMesaMessage,
  MobileQualityGateResponse,
} from "../../types/mobile";
import type { MobileSessionState } from "../session/sessionTypes";
import {
  guidedInspectionDraftFromMobilePayload,
  type GuidedInspectionDraft,
} from "../inspection/guidedInspection";
import type {
  ActiveThread,
  ChatCaseCreationState,
  ChatState,
  ComposerAttachment,
} from "./types";

interface ChatCaseCacheState {
  laudos: MobileLaudoCard[];
  conversaAtual: ChatState | null;
  conversasPorLaudo: Record<string, ChatState>;
  mesaPorLaudo: Record<string, MobileMesaMessage[]>;
  updatedAt: string;
}

type InspectorChatCaseControllerCurrent<
  TCacheLeitura extends ChatCaseCacheState,
> = {
  session: MobileSessionState | null;
  statusApi: string;
  cacheLeitura: TCacheLeitura;
  conversation: ChatState | null;
  laudosDisponiveis: MobileLaudoCard[];
  laudosFixadosIds: number[];
  historicoOcultoIds: number[];
  laudoMesaCarregado: number | null;
  setConversation: Dispatch<SetStateAction<ChatState | null>>;
  setMessage: Dispatch<SetStateAction<string>>;
  setAttachmentDraft: Dispatch<SetStateAction<ComposerAttachment | null>>;
  setQualityGateLaudoId: Dispatch<SetStateAction<number | null>>;
  setQualityGateLoading: Dispatch<SetStateAction<boolean>>;
  setQualityGateNotice: Dispatch<SetStateAction<string>>;
  setQualityGatePayload: Dispatch<
    SetStateAction<MobileQualityGateResponse | null>
  >;
  setQualityGateReason: Dispatch<SetStateAction<string>>;
  setQualityGateSubmitting: Dispatch<SetStateAction<boolean>>;
  setQualityGateVisible: Dispatch<SetStateAction<boolean>>;
  clearGuidedInspectionDraft: () => void;
  setErrorConversation: Dispatch<SetStateAction<string>>;
  setLaudosDisponiveis: Dispatch<SetStateAction<MobileLaudoCard[]>>;
  setErrorLaudos: Dispatch<SetStateAction<string>>;
  setHighlightedMessageId: Dispatch<SetStateAction<number | null>>;
  setLayoutVersion: Dispatch<SetStateAction<number>>;
  setLoadingConversation: Dispatch<SetStateAction<boolean>>;
  setSyncConversation: Dispatch<SetStateAction<boolean>>;
  setLoadingLaudos: Dispatch<SetStateAction<boolean>>;
  setSendingMessage: Dispatch<SetStateAction<boolean>>;
  setCaseCreationState: Dispatch<SetStateAction<ChatCaseCreationState>>;
  setThreadHomeGuidedTemplatesVisible?: Dispatch<SetStateAction<boolean>>;
  setThreadHomeVisible: Dispatch<SetStateAction<boolean>>;
  setMensagensMesa: Dispatch<SetStateAction<MobileMesaMessage[]>>;
  setErroMesa: Dispatch<SetStateAction<string>>;
  setMensagemMesa: Dispatch<SetStateAction<string>>;
  setAnexoMesaRascunho: Dispatch<SetStateAction<ComposerAttachment | null>>;
  setLaudoMesaCarregado: Dispatch<SetStateAction<number | null>>;
  clearMesaReference: () => void;
  onSetActiveThread: (value: ActiveThread) => void;
  setUsandoCacheOffline: (value: boolean) => void;
  setCacheLeitura: Dispatch<SetStateAction<TCacheLeitura>>;
  aplicarPreferenciasLaudos: (
    itens: MobileLaudoCard[],
    fixadosIds: number[],
    ocultosIds: number[],
  ) => MobileLaudoCard[];
  chaveCacheLaudo: (laudoId: number | null) => string;
  erroSugereModoOffline: (error: unknown) => boolean;
  normalizarConversa: (
    payload: MobileLaudoStatusResponse | MobileLaudoMensagensResponse,
  ) => ChatState;
  criarConversaNova: () => ChatState;
};

interface CreateInspectorChatCaseControllerParams<
  TCacheLeitura extends ChatCaseCacheState,
> {
  paramsRef: MutableRefObject<
    InspectorChatCaseControllerCurrent<TCacheLeitura>
  >;
  chatMessageOffsetsRef: MutableRefObject<Record<number, number>>;
  chatHighlightTimeoutRef: MutableRefObject<ReturnType<
    typeof setTimeout
  > | null>;
  restaurarContextoGuiadoDoCaso: (
    laudoId: number | null,
    laudoCard?: MobileLaudoCard | null,
    draftServidor?: GuidedInspectionDraft | null,
  ) => void;
}

export function createInspectorChatCaseController<
  TCacheLeitura extends ChatCaseCacheState,
>({
  paramsRef,
  chatMessageOffsetsRef,
  chatHighlightTimeoutRef,
  restaurarContextoGuiadoDoCaso,
}: CreateInspectorChatCaseControllerParams<TCacheLeitura>) {
  function resetChatState() {
    const current = paramsRef.current;
    current.setConversation(null);
    current.setMessage("");
    current.setAttachmentDraft(null);
    current.setQualityGateLaudoId(null);
    current.setQualityGateLoading(false);
    current.setQualityGateNotice("");
    current.setQualityGatePayload(null);
    current.setQualityGateReason("");
    current.setQualityGateSubmitting(false);
    current.setQualityGateVisible(false);
    current.clearGuidedInspectionDraft();
    current.setErrorConversation("");
    current.setLaudosDisponiveis([]);
    current.setErrorLaudos("");
    current.setHighlightedMessageId(null);
    current.setLayoutVersion(0);
    current.setLoadingConversation(false);
    current.setSyncConversation(false);
    current.setLoadingLaudos(false);
    current.setSendingMessage(false);
    current.setCaseCreationState("idle");
    current.setThreadHomeGuidedTemplatesVisible?.(false);
    current.setThreadHomeVisible(true);
    chatMessageOffsetsRef.current = {};
    if (chatHighlightTimeoutRef.current) {
      clearTimeout(chatHighlightTimeoutRef.current);
      chatHighlightTimeoutRef.current = null;
    }
  }

  function limparContextoAtivo() {
    const current = paramsRef.current;
    current.setErrorConversation("");
    current.setErroMesa("");
    current.setMessage("");
    current.setMensagemMesa("");
    current.setAttachmentDraft(null);
    current.setAnexoMesaRascunho(null);
    current.setQualityGateLaudoId(null);
    current.setQualityGateLoading(false);
    current.setQualityGateNotice("");
    current.setQualityGatePayload(null);
    current.setQualityGateReason("");
    current.setQualityGateSubmitting(false);
    current.setQualityGateVisible(false);
    current.setCaseCreationState("idle");
    current.clearGuidedInspectionDraft();
    current.setThreadHomeGuidedTemplatesVisible?.(false);
    current.setThreadHomeVisible(true);
    current.onSetActiveThread("chat");
  }

  function abrirConversaVazia(threadHomeVisible: boolean) {
    const current = paramsRef.current;
    current.setThreadHomeVisible(threadHomeVisible);
    current.setConversation(current.criarConversaNova());
    current.setMensagensMesa([]);
    current.setLaudoMesaCarregado(null);
  }

  async function carregarConversaAtual(
    accessToken: string,
    silencioso = false,
  ): Promise<ChatState | null> {
    const current = paramsRef.current;
    if (silencioso) {
      current.setSyncConversation(true);
    } else {
      current.setLoadingConversation(true);
    }
    current.setErrorConversation("");

    try {
      const status = await carregarStatusLaudo(accessToken);
      let proximaConversa = current.normalizarConversa(status);
      let draftServidor = guidedInspectionDraftFromMobilePayload(
        status.guided_inspection_draft,
      );

      if (status.laudo_id) {
        const historico = await carregarMensagensLaudo(
          accessToken,
          status.laudo_id,
        );
        draftServidor = guidedInspectionDraftFromMobilePayload(
          historico.guided_inspection_draft,
        );
        proximaConversa = current.normalizarConversa(historico);
      }

      current.setConversation(proximaConversa);
      current.setUsandoCacheOffline(false);
      current.setCacheLeitura((estadoAtual) => ({
        ...estadoAtual,
        conversaAtual: proximaConversa,
        conversasPorLaudo: {
          ...estadoAtual.conversasPorLaudo,
          [current.chaveCacheLaudo(proximaConversa.laudoId)]: proximaConversa,
        },
        updatedAt: new Date().toISOString(),
      }));
      if (proximaConversa.laudoId !== current.laudoMesaCarregado) {
        current.setMensagensMesa([]);
        current.setErroMesa("");
        current.setMensagemMesa("");
        current.setLaudoMesaCarregado(null);
      }
      restaurarContextoGuiadoDoCaso(
        proximaConversa.laudoId,
        proximaConversa.laudoCard,
        draftServidor,
      );
      return proximaConversa;
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Nao foi possivel atualizar a conversa do inspetor.";
      const emModoOffline =
        current.statusApi === "offline" || current.erroSugereModoOffline(error);
      const cacheKey = current.chaveCacheLaudo(
        current.conversation?.laudoId ?? null,
      );
      const conversaCache =
        current.cacheLeitura.conversasPorLaudo[cacheKey] ||
        current.cacheLeitura.conversaAtual;
      if (emModoOffline && conversaCache) {
        current.setConversation(conversaCache);
        current.setUsandoCacheOffline(true);
        current.setErrorConversation("");
        restaurarContextoGuiadoDoCaso(
          conversaCache.laudoId,
          conversaCache.laudoCard,
        );
        return conversaCache;
      }
      current.setErrorConversation(message);
      return null;
    } finally {
      current.setLoadingConversation(false);
      current.setSyncConversation(false);
    }
  }

  async function carregarListaLaudos(
    accessToken: string,
    silencioso = false,
  ): Promise<MobileLaudoCard[]> {
    const current = paramsRef.current;
    if (!silencioso) {
      current.setLoadingLaudos(true);
    }
    current.setErrorLaudos("");

    try {
      const payload = await carregarLaudosMobile(accessToken);
      const laudosNormalizados = current.aplicarPreferenciasLaudos(
        payload.itens || [],
        current.laudosFixadosIds,
        current.historicoOcultoIds,
      );
      current.setLaudosDisponiveis(laudosNormalizados);
      current.setUsandoCacheOffline(false);
      current.setCacheLeitura((estadoAtual) => ({
        ...estadoAtual,
        laudos: laudosNormalizados,
        updatedAt: new Date().toISOString(),
      }));
      return laudosNormalizados;
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Nao foi possivel carregar os laudos do inspetor.";
      const emModoOffline =
        current.statusApi === "offline" || current.erroSugereModoOffline(error);
      if (emModoOffline && current.cacheLeitura.laudos.length) {
        const laudosCache = current.aplicarPreferenciasLaudos(
          current.cacheLeitura.laudos,
          current.laudosFixadosIds,
          current.historicoOcultoIds,
        );
        current.setLaudosDisponiveis(laudosCache);
        current.setUsandoCacheOffline(true);
        current.setErrorLaudos("");
        return laudosCache;
      }
      current.setErrorLaudos(message);
      return [];
    } finally {
      current.setLoadingLaudos(false);
    }
  }

  async function abrirLaudoPorId(accessToken: string, laudoId: number) {
    const current = paramsRef.current;
    current.setErrorConversation("");
    current.setErroMesa("");
    current.setMessage("");
    current.setMensagemMesa("");
    current.setAttachmentDraft(null);
    current.setAnexoMesaRascunho(null);
    current.setCaseCreationState("idle");
    current.clearGuidedInspectionDraft();
    current.clearMesaReference();
    current.setLoadingConversation(true);

    try {
      const historico = await carregarMensagensLaudo(accessToken, laudoId);
      const draftServidor = guidedInspectionDraftFromMobilePayload(
        historico.guided_inspection_draft,
      );
      const proximaConversa = current.normalizarConversa(historico);
      current.setThreadHomeVisible(false);
      current.setConversation(proximaConversa);
      current.setUsandoCacheOffline(false);
      current.setCacheLeitura((estadoAtual) => ({
        ...estadoAtual,
        conversaAtual: proximaConversa,
        conversasPorLaudo: {
          ...estadoAtual.conversasPorLaudo,
          [current.chaveCacheLaudo(laudoId)]: proximaConversa,
        },
        updatedAt: new Date().toISOString(),
      }));
      current.setMensagensMesa([]);
      current.setLaudoMesaCarregado(null);
      restaurarContextoGuiadoDoCaso(
        proximaConversa.laudoId,
        proximaConversa.laudoCard,
        draftServidor,
      );
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Nao foi possivel abrir o laudo selecionado.";
      const conversaCache =
        current.cacheLeitura.conversasPorLaudo[
          current.chaveCacheLaudo(laudoId)
        ];
      const emModoOffline =
        current.statusApi === "offline" || current.erroSugereModoOffline(error);
      if (emModoOffline && conversaCache) {
        const mensagensMesa =
          current.cacheLeitura.mesaPorLaudo[current.chaveCacheLaudo(laudoId)] ||
          [];
        current.setConversation(conversaCache);
        current.setMensagensMesa(mensagensMesa);
        current.setLaudoMesaCarregado(mensagensMesa.length ? laudoId : null);
        current.setUsandoCacheOffline(true);
        restaurarContextoGuiadoDoCaso(
          conversaCache.laudoId,
          conversaCache.laudoCard,
        );
        return;
      }
      current.setErrorConversation(message);
    } finally {
      current.setLoadingConversation(false);
    }
  }

  async function handleSelecionarLaudo(card: MobileLaudoCard | null) {
    const current = paramsRef.current;
    if (!current.session) {
      return;
    }

    limparContextoAtivo();

    if (!card) {
      abrirConversaVazia(true);
      return;
    }

    current.setThreadHomeVisible(false);
    await abrirLaudoPorId(current.session.accessToken, card.id);
  }

  async function handleAbrirNovoChat() {
    const current = paramsRef.current;
    if (!current.session) {
      return;
    }

    limparContextoAtivo();
    abrirConversaVazia(true);
  }

  async function handleIniciarChatLivre() {
    const current = paramsRef.current;
    if (!current.session) {
      return;
    }

    limparContextoAtivo();
    abrirConversaVazia(false);
  }

  return {
    abrirLaudoPorId,
    carregarConversaAtual,
    carregarListaLaudos,
    handleAbrirNovoChat,
    handleIniciarChatLivre,
    handleSelecionarLaudo,
    resetChatState,
  };
}
