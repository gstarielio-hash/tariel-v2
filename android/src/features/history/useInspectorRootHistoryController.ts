import type { MobileMesaMessage } from "../../types/mobile";
import type { ChatState, MobileActivityNotification } from "../chat/types";
import type { MobileReadCache } from "../common/readCacheTypes";
import { useHistoryController } from "./useHistoryController";

type HistoryControllerParams = Parameters<
  typeof useHistoryController<
    ChatState,
    MobileReadCache,
    MobileMesaMessage,
    MobileActivityNotification
  >
>[0];

interface UseInspectorRootHistoryControllerInput {
  state: Pick<
    HistoryControllerParams,
    | "conversaAtualLaudoId"
    | "historicoOcultoIds"
    | "historicoAberto"
    | "historicoAbertoRefAtual"
    | "keyboardHeight"
    | "laudosFixadosIds"
    | "pendingHistoryThreadRoute"
  >;
  actionState: Pick<
    HistoryControllerParams,
    | "abrirHistorico"
    | "fecharConfiguracoes"
    | "fecharHistorico"
    | "handleSelecionarLaudo"
    | "onCreateNewConversation"
    | "onDismissKeyboard"
    | "onGetCacheKeyForLaudo"
    | "onSchedule"
  >;
  setterState: Pick<
    HistoryControllerParams,
    | "setAbaAtiva"
    | "setAnexoMesaRascunho"
    | "setAnexoRascunho"
    | "setCacheLeitura"
    | "setConversa"
    | "setErroConversa"
    | "setErroMesa"
    | "setHistoricoOcultoIds"
    | "setLaudoMesaCarregado"
    | "setLaudosDisponiveis"
    | "setLaudosFixadosIds"
    | "setMensagem"
    | "setMensagemMesa"
    | "setMensagensMesa"
    | "setNotificacoes"
    | "setPendingHistoryThreadRoute"
    | "setThreadRouteHistory"
  >;
}

export function useInspectorRootHistoryController({
  state,
  actionState,
  setterState,
}: UseInspectorRootHistoryControllerInput) {
  return useHistoryController<
    ChatState,
    MobileReadCache,
    MobileMesaMessage,
    MobileActivityNotification
  >({
    keyboardHeight: state.keyboardHeight,
    historicoAberto: state.historicoAberto,
    historicoAbertoRefAtual: state.historicoAbertoRefAtual,
    conversaAtualLaudoId: state.conversaAtualLaudoId,
    historicoOcultoIds: state.historicoOcultoIds,
    laudosFixadosIds: state.laudosFixadosIds,
    pendingHistoryThreadRoute: state.pendingHistoryThreadRoute,
    fecharHistorico: actionState.fecharHistorico,
    abrirHistorico: actionState.abrirHistorico,
    fecharConfiguracoes: actionState.fecharConfiguracoes,
    handleSelecionarLaudo: actionState.handleSelecionarLaudo,
    onCreateNewConversation: actionState.onCreateNewConversation,
    onDismissKeyboard: actionState.onDismissKeyboard,
    onGetCacheKeyForLaudo: actionState.onGetCacheKeyForLaudo,
    onSchedule: actionState.onSchedule,
    setAbaAtiva: setterState.setAbaAtiva,
    setAnexoMesaRascunho: setterState.setAnexoMesaRascunho,
    setAnexoRascunho: setterState.setAnexoRascunho,
    setCacheLeitura: setterState.setCacheLeitura,
    setConversa: setterState.setConversa,
    setErroConversa: setterState.setErroConversa,
    setErroMesa: setterState.setErroMesa,
    setHistoricoOcultoIds: setterState.setHistoricoOcultoIds,
    setLaudoMesaCarregado: setterState.setLaudoMesaCarregado,
    setLaudosDisponiveis: setterState.setLaudosDisponiveis,
    setLaudosFixadosIds: setterState.setLaudosFixadosIds,
    setMensagem: setterState.setMensagem,
    setMensagemMesa: setterState.setMensagemMesa,
    setMensagensMesa: setterState.setMensagensMesa,
    setNotificacoes: setterState.setNotificacoes,
    setPendingHistoryThreadRoute: setterState.setPendingHistoryThreadRoute,
    setThreadRouteHistory: setterState.setThreadRouteHistory,
  });
}
