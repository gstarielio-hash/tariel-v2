import { Alert } from "react-native";

import { buildVoiceInputUnavailableMessage } from "../chat/voice";
import {
  CACHE_LEITURA_VAZIO,
  buildLocalPersistenceScopeFromBootstrap,
  salvarCacheLeituraLocal,
} from "../common/inspectorLocalPersistence";
import { pendenciaFilaProntaParaReenvio } from "../offline/offlineQueueHelpers";
import { useInspectorRootSettingsSurface } from "./useInspectorRootSettingsSurface";
import type { InspectorRootBootstrap } from "../useInspectorRootBootstrap";
import type { InspectorRootControllers } from "../useInspectorRootControllers";

interface BuildInspectorRootSettingsToggleStateInput {
  bootstrap: InspectorRootBootstrap;
  controllers: InspectorRootControllers;
}

export function buildInspectorRootSettingsToggleState({
  bootstrap,
  controllers,
}: BuildInspectorRootSettingsToggleStateInput): Parameters<
  typeof useInspectorRootSettingsSurface
>[0]["uiState"]["toggleState"] {
  const persistenceScope = buildLocalPersistenceScopeFromBootstrap(
    bootstrap.sessionFlow.state.session?.bootstrap,
  );
  const localState = bootstrap.localState;
  const settingsBindings = bootstrap.settingsBindings;
  const settingsSupportState = bootstrap.settingsSupportState;
  const sessionFlow = bootstrap.sessionFlow;
  const refsAndBridges = bootstrap.refsAndBridges;
  const reauthActions = bootstrap.reauthActions;

  return {
    actionState: {
      abrirConfirmacaoConfiguracao:
        settingsSupportState.navigationActions.abrirConfirmacaoConfiguracao,
      executarComReautenticacao: reauthActions.executarComReautenticacao,
      onOpenSystemSettings: refsAndBridges.onOpenSystemSettings,
      onSetSettingsSheetNotice:
        settingsSupportState.navigationActions.setSettingsSheetNotice,
      registrarEventoSegurancaLocal:
        settingsSupportState.registrarEventoSegurancaLocal,
      showAlert: Alert.alert,
    },
    cacheState: {
      cacheLeituraVazio: CACHE_LEITURA_VAZIO,
      filaOffline: localState.filaOffline,
      onIsOfflineItemReadyForRetry: pendenciaFilaProntaParaReenvio,
      onSaveReadCacheLocally: (cache) =>
        salvarCacheLeituraLocal(cache, persistenceScope),
      onSyncOfflineQueue:
        controllers.offlineQueueController.actions.sincronizarFilaOffline,
      sessionAccessToken: sessionFlow.state.session?.accessToken || null,
      statusApi: sessionFlow.state.statusApi,
    },
    permissionState: {
      arquivosPermitidos: settingsBindings.security.arquivosPermitidos,
      cameraPermitida: settingsBindings.security.cameraPermitida,
      microfonePermitido: settingsBindings.security.microfonePermitido,
      notificacoesPermitidas:
        settingsBindings.notifications.notificacoesPermitidas,
    },
    setterState: {
      setAnexoMesaRascunho: localState.setAnexoMesaRascunho,
      setAnexoRascunho: localState.setAnexoRascunho,
      setArquivosPermitidos: settingsBindings.security.setArquivosPermitidos,
      setBackupAutomatico: settingsBindings.dataControls.setBackupAutomatico,
      setEntradaPorVoz: settingsBindings.speech.setEntradaPorVoz,
      setMicrofonePermitido: settingsBindings.security.setMicrofonePermitido,
      setMostrarConteudoNotificacao:
        settingsBindings.notifications.setMostrarConteudoNotificacao,
      setMostrarSomenteNovaMensagem:
        settingsBindings.notifications.setMostrarSomenteNovaMensagem,
      setNotificaPush: settingsBindings.notifications.setNotificaPush,
      setNotificacoesPermitidas:
        settingsBindings.notifications.setNotificacoesPermitidas,
      setOcultarConteudoBloqueado:
        settingsBindings.notifications.setOcultarConteudoBloqueado,
      setRespostaPorVoz: settingsBindings.speech.setRespostaPorVoz,
      setSpeechEnabled: settingsBindings.speech.setSpeechEnabled,
      setSincronizacaoDispositivos:
        settingsBindings.dataControls.setSincronizacaoDispositivos,
      setUploadArquivosAtivo:
        settingsBindings.attachments.setUploadArquivosAtivo,
      setVibracaoAtiva: settingsBindings.notifications.setVibracaoAtiva,
    },
    voiceState: {
      voiceInputRuntimeSupported:
        bootstrap.runtimeController.voiceRuntimeState.sttSupported,
      voiceInputUnavailableMessage: buildVoiceInputUnavailableMessage(
        settingsBindings.speech.voiceLanguage,
      ),
    },
  };
}
