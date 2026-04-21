import { useInspectorRootAppLockController } from "./security/useInspectorRootAppLockController";
import { reautenticacaoAindaValida } from "./settings/reauth";
import {
  buildLocalPersistenceScopeFromBootstrap,
  filtrarItensPorRetencao,
  limparCachePorPrivacidade,
  obterJanelaRetencaoMs,
  salvarCacheLeituraLocal,
  salvarEstadoHistoricoLocal,
} from "./common/inspectorLocalPersistence";
import { sanitizeReadCacheByMobileAccess } from "./common/mobileUserAccess";
import { chaveCacheLaudo } from "./chat/conversationHelpers";
import { obterTimeoutBloqueioMs } from "./common/appSupportHelpers";
import { useInspectorRootPersistenceEffects } from "./common/useInspectorRootPersistenceEffects";
import { usePushRegistrationController } from "./system/usePushRegistrationController";
import type { InspectorRootBootstrap } from "./useInspectorRootBootstrap";
import type { InspectorRootConversationControllers } from "./useInspectorRootConversationControllers";
import type { InspectorRootOperationalControllers } from "./useInspectorRootOperationalControllers";

interface UseInspectorRootSecurityAndPersistenceInput {
  bootstrap: InspectorRootBootstrap;
  conversationControllers: InspectorRootConversationControllers;
  operationalControllers: InspectorRootOperationalControllers;
}

export function useInspectorRootSecurityAndPersistence({
  bootstrap,
  conversationControllers,
  operationalControllers,
}: UseInspectorRootSecurityAndPersistenceInput) {
  const sessionUser = bootstrap.sessionFlow.state.session?.bootstrap.usuario;
  const persistenceScope = buildLocalPersistenceScopeFromBootstrap(
    bootstrap.sessionFlow.state.session?.bootstrap,
  );
  const appLockController = useInspectorRootAppLockController({
    sessionState: {
      appLocked: bootstrap.localState.bloqueioAppAtivo,
      lockTimeout: bootstrap.settingsBindings.security.lockTimeout,
      reauthenticationExpiresAt:
        bootstrap.settingsSupportState.presentationState.reautenticacaoExpiraEm,
      requireAuthOnOpen: bootstrap.settingsBindings.security.requireAuthOnOpen,
      session: bootstrap.sessionFlow.state.session,
      settingsHydrated: bootstrap.settingsBindings.store.settingsHydrated,
    },
    permissionState: {
      biometricsPermissionGranted:
        bootstrap.settingsBindings.security.biometriaPermitida,
      cameraPermissionGranted:
        bootstrap.settingsBindings.security.cameraPermitida,
      deviceBiometricsEnabled:
        bootstrap.settingsBindings.security.deviceBiometricsEnabled,
      filesPermissionGranted:
        bootstrap.settingsBindings.security.arquivosPermitidos,
      microphonePermissionGranted:
        bootstrap.settingsBindings.security.microfonePermitido,
      notificationsPermissionGranted:
        bootstrap.settingsBindings.notifications.notificacoesPermitidas,
      pushEnabled: bootstrap.settingsBindings.notifications.notificaPush,
      uploadFilesEnabled:
        bootstrap.settingsBindings.attachments.uploadArquivosAtivo,
      voiceInputEnabled: bootstrap.settingsBindings.speech.entradaPorVoz,
    },
    setterState: {
      setAppLocked: bootstrap.localState.setBloqueioAppAtivo,
      setBiometricsPermissionGranted:
        bootstrap.settingsBindings.security.setBiometriaPermitida,
      setCameraPermissionGranted:
        bootstrap.settingsBindings.security.setCameraPermitida,
      setDeviceBiometricsEnabled:
        bootstrap.settingsBindings.security.setDeviceBiometricsEnabled,
      setFilesPermissionGranted:
        bootstrap.settingsBindings.security.setArquivosPermitidos,
      setMicrophonePermissionGranted:
        bootstrap.settingsBindings.security.setMicrofonePermitido,
      setNotificationsPermissionGranted:
        bootstrap.settingsBindings.notifications.setNotificacoesPermitidas,
      setPushEnabled: bootstrap.settingsBindings.notifications.setNotificaPush,
      setUploadFilesEnabled:
        bootstrap.settingsBindings.attachments.setUploadArquivosAtivo,
      setVoiceInputEnabled: bootstrap.settingsBindings.speech.setEntradaPorVoz,
    },
    actionState: {
      isReauthenticationStillValid: reautenticacaoAindaValida,
      openReauthFlow: bootstrap.reauthActions.abrirFluxoReautenticacao,
      registerSecurityEvent:
        bootstrap.settingsSupportState.registrarEventoSegurancaLocal,
      resolveLockTimeoutMs: obterTimeoutBloqueioMs,
    },
  });

  const pushRegistrationController = usePushRegistrationController({
    accessToken: bootstrap.sessionFlow.state.session?.accessToken || null,
    appVersion: bootstrap.runtimeController.appRuntime.versionLabel,
    buildNumber: bootstrap.runtimeController.appRuntime.buildLabel,
    notificationsPermissionGranted:
      bootstrap.settingsBindings.notifications.notificacoesPermitidas,
    pushEnabled: bootstrap.settingsBindings.notifications.notificaPush,
    statusApi: bootstrap.sessionFlow.state.statusApi,
  });

  useInspectorRootPersistenceEffects({
    sessionState: {
      carregando: bootstrap.sessionFlow.state.carregando,
      email: bootstrap.sessionFlow.state.email,
      session: bootstrap.sessionFlow.state.session,
    },
    settingsState: {
      backupAutomatico:
        bootstrap.settingsBindings.dataControls.backupAutomatico,
      reautenticacaoExpiraEm:
        bootstrap.settingsSupportState.presentationState.reautenticacaoExpiraEm,
      reautenticacaoStatus:
        bootstrap.settingsSupportState.presentationState.reautenticacaoStatus,
      retencaoDados: bootstrap.settingsBindings.dataControls.retencaoDados,
      salvarHistoricoConversas:
        bootstrap.settingsBindings.dataControls.salvarHistoricoConversas,
      settingsActions: bootstrap.settingsBindings.store.settingsActions,
      settingsDocument: bootstrap.settingsBindings.store.settingsState,
    },
    dataState: {
      cacheLeitura: bootstrap.localState.cacheLeitura,
      historicoOcultoIds: bootstrap.localState.historicoOcultoIds,
      laudosFixadosIds: bootstrap.localState.laudosFixadosIds,
    },
    actionState: {
      isReauthenticationStillValid: reautenticacaoAindaValida,
      onFilterItemsByRetention: filtrarItensPorRetencao,
      onGetCacheKeyForLaudo: chaveCacheLaudo,
      onGetRetentionWindowMs: obterJanelaRetencaoMs,
      onResetMesaState:
        conversationControllers.mesaController.actions.resetMesaState,
      onSanitizeReadCacheForPrivacy: limparCachePorPrivacidade,
      onSaveHistoryStateLocally: salvarEstadoHistoricoLocal,
      onSaveReadCacheLocally: (cache) =>
        salvarCacheLeituraLocal(
          sanitizeReadCacheByMobileAccess(cache, sessionUser),
          persistenceScope,
        ),
      registerNotifications:
        operationalControllers.activityCenterController.actions
          .registrarNotificacoes,
    },
    setterState: {
      notificationRegistrarRef:
        bootstrap.refsAndBridges.registrarNotificacoesRef,
      setCacheLeitura: bootstrap.localState.setCacheLeitura,
      setFilaOffline: bootstrap.localState.setFilaOffline,
      setFilaSuporteLocal:
        bootstrap.settingsSupportState.presentationActions.setFilaSuporteLocal,
      setLaudosDisponiveis: bootstrap.localState.setLaudosDisponiveis,
      setNotificacoes: bootstrap.localState.setNotificacoes,
      setProvedoresConectados:
        bootstrap.settingsSupportState.presentationActions
          .setProvedoresConectados,
      setReautenticacaoExpiraEm:
        bootstrap.settingsSupportState.presentationActions
          .setReautenticacaoExpiraEm,
      setReautenticacaoStatus:
        bootstrap.settingsSupportState.presentationActions
          .setReautenticacaoStatus,
    },
  });

  return {
    appLockController,
    pushRegistrationController,
  };
}
