import { Alert } from "react-native";

import { useInspectorRootSettingsSurface } from "./useInspectorRootSettingsSurface";
import type { InspectorRootBootstrap } from "../useInspectorRootBootstrap";

interface BuildInspectorRootSettingsAccountDeletionStateInput {
  bootstrap: InspectorRootBootstrap;
}

export function buildInspectorRootSettingsAccountDeletionState({
  bootstrap,
}: BuildInspectorRootSettingsAccountDeletionStateInput): Parameters<
  typeof useInspectorRootSettingsSurface
>[0]["uiState"]["accountDeletionState"] {
  const localState = bootstrap.localState;
  const settingsBindings = bootstrap.settingsBindings;
  const settingsSupportState = bootstrap.settingsSupportState;
  const sessionFlow = bootstrap.sessionFlow;
  const shellSupport = bootstrap.shellSupport;

  return {
    fecharConfiguracoes: shellSupport.fecharConfiguracoes,
    handleLogout: sessionFlow.actions.handleLogout,
    onResetSettingsPresentationAfterAccountDeletion:
      settingsSupportState.presentationActions
        .resetSettingsPresentationAfterAccountDeletion,
    onSetAppLoading: sessionFlow.actions.setCarregando,
    onSetAprendizadoIa: settingsBindings.ai.setAprendizadoIa,
    onSetAnimacoesAtivas: settingsBindings.appearance.setAnimacoesAtivas,
    onSetArquivosPermitidos: settingsBindings.security.setArquivosPermitidos,
    onSetAutoUploadAttachments:
      settingsBindings.dataControls.setAutoUploadAttachments,
    onSetBackupAutomatico: settingsBindings.dataControls.setBackupAutomatico,
    onSetBiometriaPermitida: settingsBindings.security.setBiometriaPermitida,
    onSetCameraPermitida: settingsBindings.security.setCameraPermitida,
    onSetChatCategoryEnabled:
      settingsBindings.notifications.setChatCategoryEnabled,
    onSetCompartilharMelhoriaIa: settingsBindings.ai.setCompartilharMelhoriaIa,
    onSetCorDestaque: settingsBindings.appearance.setCorDestaque,
    onSetCriticalAlertsEnabled:
      settingsBindings.notifications.setCriticalAlertsEnabled,
    onSetDensidadeInterface: settingsBindings.appearance.setDensidadeInterface,
    onSetDeviceBiometricsEnabled:
      settingsBindings.security.setDeviceBiometricsEnabled,
    onSetEconomiaDados: settingsBindings.system.setEconomiaDados,
    onSetEmail: sessionFlow.actions.setEmail,
    onSetEmailAtualConta: settingsBindings.account.setEmailAtualConta,
    onSetEmailsAtivos: settingsBindings.notifications.setEmailsAtivos,
    onSetEntradaPorVoz: settingsBindings.speech.setEntradaPorVoz,
    onSetEstiloResposta: settingsBindings.ai.setEstiloResposta,
    onSetFixarConversas:
      settingsSupportState.presentationActions.setFixarConversas,
    onSetHideInMultitask: settingsBindings.security.setHideInMultitask,
    onSetHistoricoOcultoIds: localState.setHistoricoOcultoIds,
    onSetIdiomaApp: settingsBindings.system.setIdiomaApp,
    onSetIdiomaResposta: settingsBindings.ai.setIdiomaResposta,
    onSetLaudosFixadosIds: localState.setLaudosFixadosIds,
    onSetLockTimeout: settingsBindings.security.setLockTimeout,
    onSetMediaCompression: settingsBindings.dataControls.setMediaCompression,
    onSetMemoriaIa: settingsBindings.ai.setMemoriaIa,
    onSetMesaCategoryEnabled:
      settingsBindings.notifications.setMesaCategoryEnabled,
    onSetMicrofonePermitido: settingsBindings.security.setMicrofonePermitido,
    onSetModeloIa: settingsBindings.ai.setModeloIa,
    onSetMostrarConteudoNotificacao:
      settingsBindings.notifications.setMostrarConteudoNotificacao,
    onSetMostrarSomenteNovaMensagem:
      settingsBindings.notifications.setMostrarSomenteNovaMensagem,
    onSetNomeAutomaticoConversas:
      settingsSupportState.presentationActions.setNomeAutomaticoConversas,
    onSetNotificaPush: settingsBindings.notifications.setNotificaPush,
    onSetNotificaRespostas: settingsBindings.notifications.setNotificaRespostas,
    onSetNotificacoesPermitidas:
      settingsBindings.notifications.setNotificacoesPermitidas,
    onSetOcultarConteudoBloqueado:
      settingsBindings.notifications.setOcultarConteudoBloqueado,
    onSetPerfilExibicao: settingsBindings.account.setPerfilExibicao,
    onSetPerfilFotoHint: settingsBindings.account.setPerfilFotoHint,
    onSetPerfilFotoUri: settingsBindings.account.setPerfilFotoUri,
    onSetPerfilNome: settingsBindings.account.setPerfilNome,
    onSetPreferredVoiceId: settingsBindings.speech.setPreferredVoiceId,
    onSetRegiaoApp: settingsBindings.system.setRegiaoApp,
    onSetRequireAuthOnOpen: settingsBindings.security.setRequireAuthOnOpen,
    onSetRespostaPorVoz: settingsBindings.speech.setRespostaPorVoz,
    onSetRetencaoDados: settingsBindings.dataControls.setRetencaoDados,
    onSetSalvarHistoricoConversas:
      settingsBindings.dataControls.setSalvarHistoricoConversas,
    onSetSincronizacaoDispositivos:
      settingsBindings.dataControls.setSincronizacaoDispositivos,
    onSetSomNotificacao: settingsBindings.notifications.setSomNotificacao,
    onSetSpeechRate: settingsBindings.speech.setSpeechRate,
    onSetSystemCategoryEnabled:
      settingsBindings.notifications.setSystemCategoryEnabled,
    onSetTamanhoFonte: settingsBindings.appearance.setTamanhoFonte,
    onSetTemperaturaIa: settingsBindings.ai.setTemperaturaIa,
    onSetTemaApp: settingsBindings.appearance.setTemaApp,
    onSetTomConversa: settingsBindings.ai.setTomConversa,
    onSetUploadArquivosAtivo:
      settingsBindings.attachments.setUploadArquivosAtivo,
    onSetUsoBateria: settingsBindings.system.setUsoBateria,
    onSetVibracaoAtiva: settingsBindings.notifications.setVibracaoAtiva,
    onSetVoiceLanguage: settingsBindings.speech.setVoiceLanguage,
    onShowAlert: Alert.alert,
  };
}
