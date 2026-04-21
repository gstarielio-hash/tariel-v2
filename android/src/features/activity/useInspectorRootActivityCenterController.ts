import type { ChatState, MobileActivityNotification } from "../chat/types";
import { useActivityCenterController } from "./useActivityCenterController";

type ActivityCenterControllerParams = Parameters<
  typeof useActivityCenterController<ChatState, MobileActivityNotification>
>[0];

interface UseInspectorRootActivityCenterControllerInput {
  state: Pick<
    ActivityCenterControllerParams,
    | "activeThread"
    | "conversation"
    | "laudoMesaCarregado"
    | "laudosDisponiveis"
    | "messagesMesa"
    | "monitorIntervalMs"
    | "notificationSettings"
    | "notifications"
    | "notificationsPermissionGranted"
    | "session"
    | "sessionLoading"
    | "statusApi"
    | "syncEnabled"
    | "wifiOnlySync"
  >;
  actionState: Pick<
    ActivityCenterControllerParams,
    | "assinaturaMensagemMesa"
    | "assinaturaStatusLaudo"
    | "carregarMesaAtual"
    | "chaveCacheLaudo"
    | "criarNotificacaoMesa"
    | "criarNotificacaoStatusLaudo"
    | "erroSugereModoOffline"
    | "onRecoverOnline"
    | "openLaudoById"
    | "saveNotificationsLocally"
    | "selecionarLaudosParaMonitoramentoMesa"
  >;
  setterState: Pick<
    ActivityCenterControllerParams,
    | "onObserveMesaFeedReadMetadata"
    | "onObserveMesaFeedRequestedTargetIds"
    | "onSetCacheLaudos"
    | "onSetCacheMesa"
    | "onSetErroConversaIfEmpty"
    | "onSetErroLaudos"
    | "onSetLaudoMesaCarregado"
    | "onSetLaudosDisponiveis"
    | "onSetMensagensMesa"
    | "onSetStatusApi"
    | "onUpdateCurrentConversationSummary"
    | "setActiveThread"
    | "setActivityCenterVisible"
    | "setNotifications"
  >;
  limitsState: Pick<ActivityCenterControllerParams, "maxNotifications">;
}

export function useInspectorRootActivityCenterController({
  state,
  actionState,
  setterState,
  limitsState,
}: UseInspectorRootActivityCenterControllerInput) {
  return useActivityCenterController<ChatState, MobileActivityNotification>({
    session: state.session,
    sessionLoading: state.sessionLoading,
    statusApi: state.statusApi,
    wifiOnlySync: state.wifiOnlySync,
    syncEnabled: state.syncEnabled,
    activeThread: state.activeThread,
    conversation: state.conversation,
    laudosDisponiveis: state.laudosDisponiveis,
    laudoMesaCarregado: state.laudoMesaCarregado,
    messagesMesa: state.messagesMesa,
    monitorIntervalMs: state.monitorIntervalMs,
    notifications: state.notifications,
    notificationSettings: state.notificationSettings,
    notificationsPermissionGranted: state.notificationsPermissionGranted,
    setNotifications: setterState.setNotifications,
    setActivityCenterVisible: setterState.setActivityCenterVisible,
    openLaudoById: actionState.openLaudoById,
    setActiveThread: setterState.setActiveThread,
    carregarMesaAtual: actionState.carregarMesaAtual,
    onRecoverOnline: actionState.onRecoverOnline,
    saveNotificationsLocally: actionState.saveNotificationsLocally,
    assinaturaStatusLaudo: actionState.assinaturaStatusLaudo,
    assinaturaMensagemMesa: actionState.assinaturaMensagemMesa,
    selecionarLaudosParaMonitoramentoMesa:
      actionState.selecionarLaudosParaMonitoramentoMesa,
    criarNotificacaoStatusLaudo: actionState.criarNotificacaoStatusLaudo,
    criarNotificacaoMesa: actionState.criarNotificacaoMesa,
    erroSugereModoOffline: actionState.erroSugereModoOffline,
    chaveCacheLaudo: actionState.chaveCacheLaudo,
    onUpdateCurrentConversationSummary:
      setterState.onUpdateCurrentConversationSummary,
    onSetLaudosDisponiveis: setterState.onSetLaudosDisponiveis,
    onSetCacheLaudos: setterState.onSetCacheLaudos,
    onSetErroLaudos: setterState.onSetErroLaudos,
    onSetMensagensMesa: setterState.onSetMensagensMesa,
    onSetLaudoMesaCarregado: setterState.onSetLaudoMesaCarregado,
    onSetCacheMesa: setterState.onSetCacheMesa,
    onSetStatusApi: setterState.onSetStatusApi,
    onSetErroConversaIfEmpty: setterState.onSetErroConversaIfEmpty,
    onObserveMesaFeedReadMetadata: setterState.onObserveMesaFeedReadMetadata,
    onObserveMesaFeedRequestedTargetIds:
      setterState.onObserveMesaFeedRequestedTargetIds,
    maxNotifications: limitsState.maxNotifications,
  });
}
