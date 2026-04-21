import type { OfflinePendingMessage } from "./types";
import type { MobileReadCache } from "../common/readCacheTypes";
import { useInspectorChatController } from "./useInspectorChatController";

type InspectorChatControllerParams = Parameters<
  typeof useInspectorChatController<OfflinePendingMessage, MobileReadCache>
>[0];

interface UseInspectorRootChatControllerInput {
  sessionState: Pick<
    InspectorChatControllerParams,
    | "activeThread"
    | "aiRequestConfig"
    | "entryModePreference"
    | "rememberLastCaseMode"
    | "session"
    | "sessionLoading"
    | "speechSettings"
    | "statusApi"
    | "wifiOnlySync"
  >;
  conversationState: Pick<
    InspectorChatControllerParams,
    | "attachmentDraft"
    | "cacheLeitura"
    | "conversation"
    | "guidedInspectionDraft"
    | "highlightedMessageId"
    | "historicoOcultoIds"
    | "laudoMesaCarregado"
    | "laudosDisponiveis"
    | "laudosFixadosIds"
    | "layoutVersion"
    | "message"
    | "qualityGateLaudoId"
    | "qualityGatePayload"
    | "qualityGateReason"
    | "scrollRef"
  >;
  mesaState: Pick<
    InspectorChatControllerParams,
    | "carregarMesaAtual"
    | "clearMesaReference"
    | "clearGuidedInspectionDraft"
    | "setAnexoMesaRascunho"
    | "setErroMesa"
    | "setLaudoMesaCarregado"
    | "setMensagemMesa"
    | "setMensagensMesa"
    | "startGuidedInspection"
  >;
  setterState: Pick<
    InspectorChatControllerParams,
    | "onSetActiveThread"
    | "setAttachmentDraft"
    | "setCacheLeitura"
    | "setCaseCreationState"
    | "setConversation"
    | "setErrorConversation"
    | "setErrorLaudos"
    | "setFilaOffline"
    | "setHighlightedMessageId"
    | "setLaudosDisponiveis"
    | "setLayoutVersion"
    | "setLoadingConversation"
    | "setLoadingLaudos"
    | "setMessage"
    | "setQualityGateLaudoId"
    | "setQualityGateLoading"
    | "setQualityGateNotice"
    | "setQualityGatePayload"
    | "setQualityGateReason"
    | "setQualityGateSubmitting"
    | "setQualityGateVisible"
    | "setSendingMessage"
    | "setStatusApi"
    | "setSyncConversation"
    | "setThreadHomeGuidedTemplatesVisible"
    | "setThreadHomeVisible"
    | "setUsandoCacheOffline"
  >;
  actionState: Pick<
    InspectorChatControllerParams,
    | "aplicarPreferenciasLaudos"
    | "atualizarResumoLaudoAtual"
    | "chaveCacheLaudo"
    | "chaveRascunho"
    | "criarConversaNova"
    | "criarItemFilaOffline"
    | "criarMensagemAssistenteServidor"
    | "erroSugereModoOffline"
    | "inferirSetorConversa"
    | "montarHistoricoParaEnvio"
    | "normalizarConversa"
    | "normalizarModoChat"
    | "podeEditarConversaNoComposer"
    | "textoFallbackAnexo"
  >;
}

export function useInspectorRootChatController({
  sessionState,
  conversationState,
  mesaState,
  setterState,
  actionState,
}: UseInspectorRootChatControllerInput) {
  return useInspectorChatController<OfflinePendingMessage, MobileReadCache>({
    session: sessionState.session,
    sessionLoading: sessionState.sessionLoading,
    activeThread: sessionState.activeThread,
    entryModePreference: sessionState.entryModePreference,
    rememberLastCaseMode: sessionState.rememberLastCaseMode,
    statusApi: sessionState.statusApi,
    wifiOnlySync: sessionState.wifiOnlySync,
    aiRequestConfig: sessionState.aiRequestConfig,
    speechSettings: sessionState.speechSettings,
    cacheLeitura: conversationState.cacheLeitura,
    conversation: conversationState.conversation,
    guidedInspectionDraft: conversationState.guidedInspectionDraft,
    qualityGateLaudoId: conversationState.qualityGateLaudoId,
    qualityGatePayload: conversationState.qualityGatePayload,
    qualityGateReason: conversationState.qualityGateReason,
    setConversation: setterState.setConversation,
    laudosDisponiveis: conversationState.laudosDisponiveis,
    setLaudosDisponiveis: setterState.setLaudosDisponiveis,
    laudosFixadosIds: conversationState.laudosFixadosIds,
    historicoOcultoIds: conversationState.historicoOcultoIds,
    laudoMesaCarregado: conversationState.laudoMesaCarregado,
    setLaudoMesaCarregado: mesaState.setLaudoMesaCarregado,
    setMensagensMesa: mesaState.setMensagensMesa,
    setErroMesa: mesaState.setErroMesa,
    setMensagemMesa: mesaState.setMensagemMesa,
    setAnexoMesaRascunho: mesaState.setAnexoMesaRascunho,
    clearMesaReference: mesaState.clearMesaReference,
    clearGuidedInspectionDraft: mesaState.clearGuidedInspectionDraft,
    startGuidedInspection: mesaState.startGuidedInspection,
    onSetActiveThread: setterState.onSetActiveThread,
    message: conversationState.message,
    setMessage: setterState.setMessage,
    attachmentDraft: conversationState.attachmentDraft,
    setAttachmentDraft: setterState.setAttachmentDraft,
    setCaseCreationState: setterState.setCaseCreationState,
    setErrorConversation: setterState.setErrorConversation,
    setQualityGateLaudoId: setterState.setQualityGateLaudoId,
    setQualityGateLoading: setterState.setQualityGateLoading,
    setQualityGateNotice: setterState.setQualityGateNotice,
    setQualityGatePayload: setterState.setQualityGatePayload,
    setQualityGateReason: setterState.setQualityGateReason,
    setQualityGateSubmitting: setterState.setQualityGateSubmitting,
    setQualityGateVisible: setterState.setQualityGateVisible,
    setSendingMessage: setterState.setSendingMessage,
    setLoadingConversation: setterState.setLoadingConversation,
    setSyncConversation: setterState.setSyncConversation,
    setLoadingLaudos: setterState.setLoadingLaudos,
    setErrorLaudos: setterState.setErrorLaudos,
    setThreadHomeGuidedTemplatesVisible:
      setterState.setThreadHomeGuidedTemplatesVisible,
    setThreadHomeVisible: setterState.setThreadHomeVisible,
    highlightedMessageId: conversationState.highlightedMessageId,
    setHighlightedMessageId: setterState.setHighlightedMessageId,
    layoutVersion: conversationState.layoutVersion,
    setLayoutVersion: setterState.setLayoutVersion,
    scrollRef: conversationState.scrollRef,
    setFilaOffline: setterState.setFilaOffline,
    setStatusApi: setterState.setStatusApi,
    setUsandoCacheOffline: setterState.setUsandoCacheOffline,
    setCacheLeitura: setterState.setCacheLeitura,
    carregarMesaAtual: mesaState.carregarMesaAtual,
    aplicarPreferenciasLaudos: actionState.aplicarPreferenciasLaudos,
    chaveCacheLaudo: actionState.chaveCacheLaudo,
    chaveRascunho: actionState.chaveRascunho,
    erroSugereModoOffline: actionState.erroSugereModoOffline,
    normalizarConversa: actionState.normalizarConversa,
    atualizarResumoLaudoAtual: actionState.atualizarResumoLaudoAtual,
    criarConversaNova: actionState.criarConversaNova,
    podeEditarConversaNoComposer: actionState.podeEditarConversaNoComposer,
    textoFallbackAnexo: actionState.textoFallbackAnexo,
    normalizarModoChat: actionState.normalizarModoChat,
    inferirSetorConversa: actionState.inferirSetorConversa,
    montarHistoricoParaEnvio: actionState.montarHistoricoParaEnvio,
    criarMensagemAssistenteServidor:
      actionState.criarMensagemAssistenteServidor,
    criarItemFilaOffline: actionState.criarItemFilaOffline,
  });
}
