import { Alert } from "react-native";

import { criarNotificacaoSistema } from "../activity/activityNotificationHelpers";
import { montarAnexoImagem } from "../chat/attachmentFileHelpers";
import {
  compartilharTextoExportado,
  formatarHorarioAtividade,
} from "../common/appSupportHelpers";
import { CACHE_LEITURA_VAZIO } from "../common/inspectorLocalPersistence";
import type { InspectorRootBootstrap } from "../useInspectorRootBootstrap";
import type { InspectorRootControllers } from "../useInspectorRootControllers";
import { useInspectorRootSettingsSurface } from "./useInspectorRootSettingsSurface";

interface BuildInspectorRootSettingsSurfaceOperationsStateInput {
  bootstrap: InspectorRootBootstrap;
  controllers: InspectorRootControllers;
}

export function buildInspectorRootSettingsSurfaceOperationsState({
  bootstrap,
  controllers,
}: BuildInspectorRootSettingsSurfaceOperationsStateInput): Parameters<
  typeof useInspectorRootSettingsSurface
>[0]["operationsState"] {
  const localState = bootstrap.localState;
  const settingsBindings = bootstrap.settingsBindings;
  const settingsSupportState = bootstrap.settingsSupportState;
  const sessionFlow = bootstrap.sessionFlow;
  const shellSupport = bootstrap.shellSupport;
  const runtimeController = bootstrap.runtimeController;
  const reauthActions = bootstrap.reauthActions;

  return {
    actionState: {
      abrirConfirmacaoConfiguracao:
        settingsSupportState.navigationActions.abrirConfirmacaoConfiguracao,
      abrirSheetConfiguracao:
        settingsSupportState.navigationActions.abrirSheetConfiguracao,
      compartilharTextoExportado,
      executarComReautenticacao: reauthActions.executarComReautenticacao,
      fecharConfiguracoes: shellSupport.fecharConfiguracoes,
      handleLogout: sessionFlow.actions.handleLogout,
      onNotificarSistema: (params) => {
        controllers.activityCenterController.actions.registrarNotificacoes([
          criarNotificacaoSistema(params),
        ]);
      },
      registrarEventoSegurancaLocal:
        settingsSupportState.registrarEventoSegurancaLocal,
      showAlert: Alert.alert,
      tentarAbrirUrlExterna: shellSupport.tentarAbrirUrlExterna,
    },
    collectionState: {
      eventosSeguranca: settingsSupportState.presentationState.eventosSeguranca,
      filaSuporteLocal: settingsSupportState.presentationState.filaSuporteLocal,
      integracaoSincronizandoId:
        settingsSupportState.presentationState.integracaoSincronizandoId,
      integracoesExternas:
        settingsSupportState.presentationState.integracoesExternas,
    },
    identityState: {
      canalSuporteUrl: controllers.operationalState.canalSuporteUrl,
      emailAtualConta: settingsBindings.account.emailAtualConta,
      fallbackEmail: sessionFlow.state.email,
      perfilExibicao: settingsBindings.account.perfilExibicao,
      perfilNome: settingsBindings.account.perfilNome,
      sessaoAtualTitulo:
        settingsSupportState.presentationState.sessoesAtivas.find(
          (item) => item.current,
        )?.title || "Dispositivo atual",
    },
    permissionState: {
      arquivosPermitidos: settingsBindings.security.arquivosPermitidos,
      cameraPermitida: settingsBindings.security.cameraPermitida,
      microfonePermitido: settingsBindings.security.microfonePermitido,
      notificacoesPermitidas:
        settingsBindings.notifications.notificacoesPermitidas,
      pushRegistrationLastError:
        controllers.pushRegistrationController.state.lastError,
      pushRegistrationSnapshot:
        controllers.pushRegistrationController.state.registration,
      pushRegistrationStatus:
        controllers.pushRegistrationController.state.syncStatus,
    },
    runtimeState: {
      appRuntime: runtimeController.appRuntime,
      cacheLeituraVazio: CACHE_LEITURA_VAZIO,
      formatarHorarioAtividade,
      limpandoCache: localState.limpandoCache,
      montarScreenshotAnexo: (asset) =>
        montarAnexoImagem(
          asset,
          "Screenshot anexada ao relato de bug para facilitar a reprodução.",
        ),
      offlineSyncObservability:
        controllers.operationalState.offlineSyncObservability,
      resumoAtualizacaoApp:
        settingsSupportState.presentationState.statusAtualizacaoApp,
      statusApi: sessionFlow.state.statusApi,
      statusAtualizacaoApp:
        settingsSupportState.presentationState.statusAtualizacaoApp,
      ultimaVerificacaoAtualizacao:
        settingsSupportState.presentationState.ultimaVerificacaoAtualizacao,
      verificandoAtualizacoes: localState.verificandoAtualizacoes,
    },
    setterState: {
      setBugAttachmentDraft:
        settingsSupportState.presentationActions.setBugAttachmentDraft,
      setCacheLeitura: localState.setCacheLeitura,
      setFilaSuporteLocal:
        settingsSupportState.presentationActions.setFilaSuporteLocal,
      setIntegracaoSincronizandoId:
        settingsSupportState.presentationActions.setIntegracaoSincronizandoId,
      setIntegracoesExternas:
        settingsSupportState.presentationActions.setIntegracoesExternas,
      setLimpandoCache: localState.setLimpandoCache,
      setSettingsSheetNotice:
        settingsSupportState.navigationActions.setSettingsSheetNotice,
      setStatusApi: sessionFlow.actions.setStatusApi,
      setStatusAtualizacaoApp:
        settingsSupportState.presentationActions.setStatusAtualizacaoApp,
      setUltimaLimpezaCacheEm: localState.setUltimaLimpezaCacheEm,
      setUltimaVerificacaoAtualizacao:
        settingsSupportState.presentationActions
          .setUltimaVerificacaoAtualizacao,
      setVerificandoAtualizacoes: localState.setVerificandoAtualizacoes,
    },
  };
}
