import type { ChatState, OfflinePendingMessage } from "../chat/types";
import { useOfflineQueueController } from "./useOfflineQueueController";

type OfflineQueueControllerParams = Parameters<
  typeof useOfflineQueueController<ChatState, OfflinePendingMessage>
>[0];

interface UseInspectorRootOfflineQueueControllerInput {
  state: Pick<
    OfflineQueueControllerParams,
    | "activeThread"
    | "conversation"
    | "messagesMesa"
    | "offlineQueue"
    | "session"
    | "sessionLoading"
    | "statusApi"
    | "syncEnabled"
    | "syncingItemId"
    | "syncingQueue"
    | "wifiOnlySync"
  >;
  actionState: Pick<
    OfflineQueueControllerParams,
    | "abrirLaudoPorId"
    | "carregarConversaAtual"
    | "carregarListaLaudos"
    | "carregarMesaAtual"
    | "duplicarComposerAttachment"
    | "erroSugereModoOffline"
    | "handleSelecionarLaudo"
    | "inferirSetorConversa"
    | "isItemReadyForRetry"
    | "montarHistoricoParaEnvio"
    | "normalizarModoChat"
    | "obterResumoReferenciaMensagem"
    | "restoreQualityGateFinalize"
    | "saveQueueLocally"
    | "calcularBackoffMs"
  >;
  setterState: Pick<
    OfflineQueueControllerParams,
    | "setActiveThread"
    | "setAttachmentDraft"
    | "setAttachmentMesaDraft"
    | "setErrorConversation"
    | "setErrorMesa"
    | "setMessage"
    | "setMessageMesa"
    | "setMesaActiveReference"
    | "setOfflineQueue"
    | "setOfflineQueueVisible"
    | "setStatusApi"
    | "setSyncingItemId"
    | "setSyncingQueue"
  >;
}

export function useInspectorRootOfflineQueueController({
  state,
  actionState,
  setterState,
}: UseInspectorRootOfflineQueueControllerInput) {
  return useOfflineQueueController<ChatState, OfflinePendingMessage>({
    session: state.session,
    sessionLoading: state.sessionLoading,
    statusApi: state.statusApi,
    wifiOnlySync: state.wifiOnlySync,
    syncEnabled: state.syncEnabled,
    activeThread: state.activeThread,
    conversation: state.conversation,
    messagesMesa: state.messagesMesa,
    offlineQueue: state.offlineQueue,
    syncingQueue: state.syncingQueue,
    syncingItemId: state.syncingItemId,
    setOfflineQueue: setterState.setOfflineQueue,
    setSyncingQueue: setterState.setSyncingQueue,
    setSyncingItemId: setterState.setSyncingItemId,
    setOfflineQueueVisible: setterState.setOfflineQueueVisible,
    setActiveThread: setterState.setActiveThread,
    setMessage: setterState.setMessage,
    setAttachmentDraft: setterState.setAttachmentDraft,
    setMessageMesa: setterState.setMessageMesa,
    setAttachmentMesaDraft: setterState.setAttachmentMesaDraft,
    setMesaActiveReference: setterState.setMesaActiveReference,
    setErrorConversation: setterState.setErrorConversation,
    setErrorMesa: setterState.setErrorMesa,
    setStatusApi: setterState.setStatusApi,
    saveQueueLocally: actionState.saveQueueLocally,
    carregarListaLaudos: actionState.carregarListaLaudos,
    carregarConversaAtual: actionState.carregarConversaAtual,
    abrirLaudoPorId: actionState.abrirLaudoPorId,
    handleSelecionarLaudo: actionState.handleSelecionarLaudo,
    carregarMesaAtual: actionState.carregarMesaAtual,
    inferirSetorConversa: actionState.inferirSetorConversa,
    montarHistoricoParaEnvio: actionState.montarHistoricoParaEnvio,
    normalizarModoChat: actionState.normalizarModoChat,
    obterResumoReferenciaMensagem: actionState.obterResumoReferenciaMensagem,
    restoreQualityGateFinalize: actionState.restoreQualityGateFinalize,
    erroSugereModoOffline: actionState.erroSugereModoOffline,
    duplicarComposerAttachment: actionState.duplicarComposerAttachment,
    calcularBackoffMs: actionState.calcularBackoffMs,
    isItemReadyForRetry: actionState.isItemReadyForRetry,
  });
}
