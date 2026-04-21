import type { OfflinePendingMessage } from "../chat/types";
import type { MobileReadCache } from "../common/readCacheTypes";
import { useMesaController } from "./useMesaController";

type MesaControllerParams = Parameters<
  typeof useMesaController<OfflinePendingMessage, MobileReadCache>
>[0];

interface UseInspectorRootMesaControllerInput {
  state: Pick<
    MesaControllerParams,
    | "activeThread"
    | "attachmentDraft"
    | "conversation"
    | "laudoMesaCarregado"
    | "messageMesa"
    | "messagesMesa"
    | "session"
    | "statusApi"
    | "wifiOnlySync"
  >;
  refState: Pick<MesaControllerParams, "carregarListaLaudosRef" | "scrollRef">;
  cacheState: Pick<
    MesaControllerParams,
    "cacheLeitura" | "chaveCacheLaudo" | "chaveRascunho" | "textoFallbackAnexo"
  >;
  actionState: Pick<
    MesaControllerParams,
    | "activeReference"
    | "atualizarResumoLaudoAtual"
    | "criarItemFilaOffline"
    | "erroSugereModoOffline"
    | "onObserveMesaThreadReadMetadata"
  >;
  setterState: Pick<
    MesaControllerParams,
    | "setActiveReference"
    | "setAttachmentDraft"
    | "setCacheLeitura"
    | "setConversation"
    | "setErrorMesa"
    | "setFilaOffline"
    | "setLaudoMesaCarregado"
    | "setLoadingMesa"
    | "setMessageMesa"
    | "setMessagesMesa"
    | "setSendingMesa"
    | "setStatusApi"
    | "setSyncMesa"
    | "setUsandoCacheOffline"
  >;
}

export function useInspectorRootMesaController({
  state,
  refState,
  cacheState,
  actionState,
  setterState,
}: UseInspectorRootMesaControllerInput) {
  return useMesaController<OfflinePendingMessage, MobileReadCache>({
    session: state.session,
    activeThread: state.activeThread,
    conversation: state.conversation,
    statusApi: state.statusApi,
    wifiOnlySync: state.wifiOnlySync,
    messageMesa: state.messageMesa,
    attachmentDraft: state.attachmentDraft,
    activeReference: actionState.activeReference,
    messagesMesa: state.messagesMesa,
    setMessagesMesa: setterState.setMessagesMesa,
    setErrorMesa: setterState.setErrorMesa,
    setMessageMesa: setterState.setMessageMesa,
    setAttachmentDraft: setterState.setAttachmentDraft,
    setActiveReference: setterState.setActiveReference,
    setLoadingMesa: setterState.setLoadingMesa,
    setSyncMesa: setterState.setSyncMesa,
    setSendingMesa: setterState.setSendingMesa,
    laudoMesaCarregado: state.laudoMesaCarregado,
    setLaudoMesaCarregado: setterState.setLaudoMesaCarregado,
    scrollRef: refState.scrollRef,
    carregarListaLaudosRef: refState.carregarListaLaudosRef,
    setFilaOffline: setterState.setFilaOffline,
    setStatusApi: setterState.setStatusApi,
    cacheLeitura: cacheState.cacheLeitura,
    setCacheLeitura: setterState.setCacheLeitura,
    setUsandoCacheOffline: setterState.setUsandoCacheOffline,
    setConversation: setterState.setConversation,
    chaveCacheLaudo: cacheState.chaveCacheLaudo,
    chaveRascunho: cacheState.chaveRascunho,
    erroSugereModoOffline: actionState.erroSugereModoOffline,
    textoFallbackAnexo: cacheState.textoFallbackAnexo,
    criarItemFilaOffline: actionState.criarItemFilaOffline,
    atualizarResumoLaudoAtual: actionState.atualizarResumoLaudoAtual,
    onObserveMesaThreadReadMetadata:
      actionState.onObserveMesaThreadReadMetadata,
  });
}
