import { pingApi } from "../config/api";
import { MAX_NOTIFICATIONS } from "./InspectorMobileApp.constants";
import { useInspectorRootActivityCenterController } from "./activity/useInspectorRootActivityCenterController";
import {
  assinaturaMensagemMesa,
  assinaturaStatusLaudo,
  criarNotificacaoMesa,
  criarNotificacaoSistema,
  criarNotificacaoStatusLaudo,
  selecionarLaudosParaMonitoramentoMesa,
} from "./activity/activityNotificationHelpers";
import {
  atualizarResumoLaudoAtual,
  chaveCacheLaudo,
  duplicarComposerAttachment,
  inferirSetorConversa,
  montarHistoricoParaEnvio,
  normalizarModoChat,
} from "./chat/conversationHelpers";
import { canSyncOnCurrentNetwork } from "./chat/network";
import {
  erroSugereModoOffline,
  formatarHorarioAtividade,
  obterIntervaloMonitoramentoMs,
} from "./common/appSupportHelpers";
import { obterResumoReferenciaMensagem } from "./common/messagePreviewHelpers";
import { buildInspectorRootOperationalState } from "./common/buildInspectorRootOperationalState";
import { usePilotAutomationController } from "./common/usePilotAutomationController";
import { useInspectorRootOfflineQueueController } from "./offline/useInspectorRootOfflineQueueController";
import {
  calcularBackoffPendenciaOfflineMs,
  pendenciaFilaProntaParaReenvio,
  prioridadePendenciaOffline,
} from "./offline/offlineQueueHelpers";
import {
  buildLocalPersistenceScopeFromBootstrap,
  salvarFilaOfflineLocal,
  salvarNotificacoesLocais,
} from "./common/inspectorLocalPersistence";
import {
  filterNotificationsByMobileAccess,
  filterOfflineQueueByMobileAccess,
  hasMobileUserPortal,
} from "./common/mobileUserAccess";
import type { InspectorRootBootstrap } from "./useInspectorRootBootstrap";
import type { InspectorRootConversationControllers } from "./useInspectorRootConversationControllers";

async function podeSincronizarNaRedeAtual(
  wifiOnlySync: boolean,
): Promise<boolean> {
  return canSyncOnCurrentNetwork(wifiOnlySync);
}

interface UseInspectorRootOperationalControllersInput {
  bootstrap: InspectorRootBootstrap;
  conversationControllers: InspectorRootConversationControllers;
}

export function useInspectorRootOperationalControllers({
  bootstrap,
  conversationControllers,
}: UseInspectorRootOperationalControllersInput) {
  const sessionUser = bootstrap.sessionFlow.state.session?.bootstrap.usuario;
  const mesaAccessGranted = hasMobileUserPortal(sessionUser, "revisor");
  const persistenceScope = buildLocalPersistenceScopeFromBootstrap(
    bootstrap.sessionFlow.state.session?.bootstrap,
  );
  const offlineQueueForSession = filterOfflineQueueByMobileAccess(
    bootstrap.localState.filaOffline,
    sessionUser,
  );
  const notificationsForSession = filterNotificationsByMobileAccess(
    bootstrap.localState.notificacoes,
    sessionUser,
  );
  const messagesMesaForSession = mesaAccessGranted
    ? bootstrap.localState.mensagensMesa
    : [];
  const offlineQueueController = useInspectorRootOfflineQueueController({
    state: {
      activeThread: bootstrap.localState.abaAtiva,
      conversation: bootstrap.localState.conversa,
      messagesMesa: messagesMesaForSession,
      offlineQueue: offlineQueueForSession,
      session: bootstrap.sessionFlow.state.session,
      sessionLoading: bootstrap.sessionFlow.state.carregando,
      statusApi: bootstrap.sessionFlow.state.statusApi,
      syncEnabled:
        bootstrap.settingsBindings.dataControls.sincronizacaoDispositivos,
      syncingItemId: bootstrap.localState.sincronizandoItemFilaId,
      syncingQueue: bootstrap.localState.sincronizandoFilaOffline,
      wifiOnlySync: bootstrap.settingsBindings.dataControls.wifiOnlySync,
    },
    actionState: {
      abrirLaudoPorId:
        conversationControllers.chatController.actions.abrirLaudoPorId,
      carregarConversaAtual:
        conversationControllers.chatController.actions.carregarConversaAtual,
      carregarListaLaudos:
        conversationControllers.chatController.actions.carregarListaLaudos,
      carregarMesaAtual:
        conversationControllers.mesaController.actions.carregarMesaAtual,
      duplicarComposerAttachment,
      erroSugereModoOffline,
      handleSelecionarLaudo:
        conversationControllers.chatController.actions.handleSelecionarLaudo,
      inferirSetorConversa,
      isItemReadyForRetry: pendenciaFilaProntaParaReenvio,
      montarHistoricoParaEnvio,
      normalizarModoChat,
      obterResumoReferenciaMensagem,
      restoreQualityGateFinalize:
        conversationControllers.chatController.actions
          .handleRetomarQualityGateOfflineItem,
      saveQueueLocally: (items) =>
        salvarFilaOfflineLocal(
          filterOfflineQueueByMobileAccess(items, sessionUser),
          persistenceScope,
        ),
      calcularBackoffMs: calcularBackoffPendenciaOfflineMs,
    },
    setterState: {
      setActiveThread: bootstrap.localState.setAbaAtiva,
      setAttachmentDraft: bootstrap.localState.setAnexoRascunho,
      setAttachmentMesaDraft: bootstrap.localState.setAnexoMesaRascunho,
      setErrorConversation: bootstrap.localState.setErroConversa,
      setErrorMesa: bootstrap.localState.setErroMesa,
      setMessage: bootstrap.localState.setMensagem,
      setMessageMesa: bootstrap.localState.setMensagemMesa,
      setMesaActiveReference:
        bootstrap.localState.setMensagemMesaReferenciaAtiva,
      setOfflineQueue: bootstrap.localState.setFilaOffline,
      setOfflineQueueVisible: bootstrap.shellSupport.setFilaOfflineAberta,
      setStatusApi: bootstrap.sessionFlow.actions.setStatusApi,
      setSyncingItemId: bootstrap.localState.setSincronizandoItemFilaId,
      setSyncingQueue: bootstrap.localState.setSincronizandoFilaOffline,
    },
  });

  const operationalState = buildInspectorRootOperationalState({
    offlineState: {
      offlineQueue: offlineQueueForSession,
      statusApi: bootstrap.sessionFlow.state.statusApi,
      syncEnabled:
        bootstrap.settingsBindings.dataControls.sincronizacaoDispositivos,
      wifiOnlySync: bootstrap.settingsBindings.dataControls.wifiOnlySync,
      syncingQueue: bootstrap.localState.sincronizandoFilaOffline,
      syncingItemId: bootstrap.localState.sincronizandoItemFilaId,
      isItemReadyForRetry: pendenciaFilaProntaParaReenvio,
      getPriority: prioridadePendenciaOffline,
    },
    refreshState: {
      abaAtiva: bootstrap.localState.abaAtiva,
      carregarConversaAtual:
        conversationControllers.chatController.actions.carregarConversaAtual,
      carregarListaLaudos:
        conversationControllers.chatController.actions.carregarListaLaudos,
      carregarMesaAtual:
        conversationControllers.mesaController.actions.carregarMesaAtual,
      conversa: bootstrap.localState.conversa,
      criarNotificacaoSistema,
      filaOffline: bootstrap.localState.filaOffline,
      onCanSyncOnCurrentNetwork: podeSincronizarNaRedeAtual,
      onIsOfflineItemReadyForRetry: pendenciaFilaProntaParaReenvio,
      onPingApi: pingApi,
      onRegistrarNotificacoes:
        bootstrap.refsAndBridges.onRegistrarNotificacoesViaRef,
      onSetErroConversa: bootstrap.localState.setErroConversa,
      onSetErroMesa: bootstrap.localState.setErroMesa,
      onSetSincronizandoAgora: bootstrap.localState.setSincronizandoAgora,
      onSetStatusApi: bootstrap.sessionFlow.actions.setStatusApi,
      onSetUsandoCacheOffline: bootstrap.localState.setUsandoCacheOffline,
      session: bootstrap.sessionFlow.state.session,
      sincronizacaoDispositivos:
        bootstrap.settingsBindings.dataControls.sincronizacaoDispositivos,
      sincronizarFilaOffline:
        offlineQueueController.actions.sincronizarFilaOffline,
      wifiOnlySync: bootstrap.settingsBindings.dataControls.wifiOnlySync,
    },
    supportState: {
      abaAtiva: bootstrap.localState.abaAtiva,
      bootstrapApiBaseUrl:
        bootstrap.sessionFlow.state.session?.bootstrap.app.api_base_url || "",
      bootstrapSupportWhatsapp:
        bootstrap.sessionFlow.state.session?.bootstrap.app.suporte_whatsapp ||
        "",
      cacheUpdatedAt: bootstrap.localState.cacheLeitura.updatedAt,
      carregandoLaudos: bootstrap.localState.carregandoLaudos,
      carregandoMesa: bootstrap.localState.carregandoMesa,
      conversaLaudoId: bootstrap.localState.conversa?.laudoId ?? null,
      economiaDados: bootstrap.settingsBindings.system.economiaDados,
      filaOffline: offlineQueueForSession,
      formatarHorarioAtividade,
      laudoMesaCarregado: bootstrap.localState.laudoMesaCarregado,
      limpandoCache: bootstrap.localState.limpandoCache,
      notificacoes: notificationsForSession,
      preferredVoiceId: bootstrap.settingsBindings.speech.preferredVoiceId,
      sincronizandoAgora: bootstrap.localState.sincronizandoAgora,
      sincronizandoConversa: bootstrap.localState.sincronizandoConversa,
      sincronizandoFilaOffline: bootstrap.localState.sincronizandoFilaOffline,
      sincronizandoMesa: bootstrap.localState.sincronizandoMesa,
      statusAtualizacaoApp:
        bootstrap.settingsSupportState.presentationState.statusAtualizacaoApp,
      ultimaLimpezaCacheEm: bootstrap.localState.ultimaLimpezaCacheEm,
      ttsSupported: bootstrap.runtimeController.voiceRuntimeState.ttsSupported,
      usoBateria: bootstrap.settingsBindings.system.usoBateria,
      voices: bootstrap.runtimeController.voiceRuntimeState.voices,
    },
  });

  const activityCenterController = useInspectorRootActivityCenterController({
    state: {
      activeThread: bootstrap.localState.abaAtiva,
      conversation: bootstrap.localState.conversa,
      laudoMesaCarregado: bootstrap.localState.laudoMesaCarregado,
      laudosDisponiveis: bootstrap.localState.laudosDisponiveis,
      messagesMesa: messagesMesaForSession,
      monitorIntervalMs: obterIntervaloMonitoramentoMs(
        bootstrap.settingsBindings.system.economiaDados,
        bootstrap.settingsBindings.system.usoBateria,
      ),
      notificationSettings:
        bootstrap.settingsBindings.store.settingsState.notifications,
      notifications: notificationsForSession,
      notificationsPermissionGranted:
        bootstrap.settingsBindings.notifications.notificacoesPermitidas,
      session: bootstrap.sessionFlow.state.session,
      sessionLoading: bootstrap.sessionFlow.state.carregando,
      statusApi: bootstrap.sessionFlow.state.statusApi,
      syncEnabled:
        bootstrap.settingsBindings.dataControls.sincronizacaoDispositivos,
      wifiOnlySync: bootstrap.settingsBindings.dataControls.wifiOnlySync,
    },
    actionState: {
      assinaturaMensagemMesa,
      assinaturaStatusLaudo,
      carregarMesaAtual:
        conversationControllers.mesaController.actions.carregarMesaAtual,
      chaveCacheLaudo,
      criarNotificacaoMesa,
      criarNotificacaoStatusLaudo,
      erroSugereModoOffline,
      onRecoverOnline: operationalState.handleRefresh,
      openLaudoById:
        conversationControllers.chatController.actions.abrirLaudoPorId,
      saveNotificationsLocally: (items) =>
        salvarNotificacoesLocais(
          filterNotificationsByMobileAccess(items, sessionUser),
          persistenceScope,
        ),
      selecionarLaudosParaMonitoramentoMesa,
    },
    setterState: {
      onObserveMesaFeedReadMetadata:
        bootstrap.localState.setUltimoMetaLeituraFeedMesa,
      onObserveMesaFeedRequestedTargetIds:
        bootstrap.localState.setUltimosAlvosConsultadosFeedMesa,
      onSetCacheLaudos: (proximosLaudos) => {
        bootstrap.localState.setCacheLeitura((estadoAtual) => ({
          ...estadoAtual,
          laudos: proximosLaudos,
          updatedAt: new Date().toISOString(),
        }));
      },
      onSetCacheMesa: (cacheMesaAtualizado) => {
        bootstrap.localState.setCacheLeitura((estadoAtual) => ({
          ...estadoAtual,
          mesaPorLaudo: {
            ...estadoAtual.mesaPorLaudo,
            ...cacheMesaAtualizado,
          },
          updatedAt: new Date().toISOString(),
        }));
      },
      onSetErroConversaIfEmpty: (message) => {
        bootstrap.localState.setErroConversa(
          (estadoAtual) => estadoAtual || message,
        );
      },
      onSetErroLaudos: bootstrap.localState.setErroLaudos,
      onSetLaudoMesaCarregado: bootstrap.localState.setLaudoMesaCarregado,
      onSetLaudosDisponiveis: bootstrap.localState.setLaudosDisponiveis,
      onSetMensagensMesa: bootstrap.localState.setMensagensMesa,
      onSetStatusApi: bootstrap.sessionFlow.actions.setStatusApi,
      onUpdateCurrentConversationSummary: (payload) => {
        bootstrap.localState.setConversa((estadoAtual) =>
          atualizarResumoLaudoAtual(estadoAtual, payload),
        );
      },
      setActiveThread: bootstrap.localState.setAbaAtiva,
      setActivityCenterVisible:
        bootstrap.shellSupport.setCentralAtividadeAberta,
      setNotifications: bootstrap.localState.setNotificacoes,
    },
    limitsState: {
      maxNotifications: MAX_NOTIFICATIONS,
    },
  });

  const pilotAutomationController = usePilotAutomationController({
    activityCenterDiagnostics:
      activityCenterController.state.activityCenterDiagnostics,
    centralAtividadeAberta: bootstrap.shellSupport.centralAtividadeAberta,
    handleSelecionarHistorico:
      conversationControllers.historyController.handleSelecionarHistorico,
    laudoMesaCarregado: bootstrap.localState.laudoMesaCarregado,
    mesaThreadRenderConfirmada: operationalState.mesaThreadRenderConfirmada,
    notificacoes: bootstrap.localState.notificacoes,
    selectedHistoryItemId: operationalState.laudoSelecionadoShellId,
    sessionAccessToken:
      bootstrap.sessionFlow.state.session?.accessToken || null,
    sessionLoading: bootstrap.sessionFlow.state.carregando,
    ultimoMetaLeituraFeedMesa: bootstrap.localState.ultimoMetaLeituraFeedMesa,
    ultimoMetaLeituraThreadMesa:
      bootstrap.localState.ultimoMetaLeituraThreadMesa,
    ultimosAlvosConsultadosFeedMesa:
      bootstrap.localState.ultimosAlvosConsultadosFeedMesa,
  });

  return {
    activityCenterController,
    offlineQueueController,
    operationalState,
    pilotAutomationController,
  };
}

export type InspectorRootOperationalControllers = ReturnType<
  typeof useInspectorRootOperationalControllers
>;
