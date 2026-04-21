import { Alert, Linking, useColorScheme } from "react-native";

import {
  CACHE_LEITURA_VAZIO,
  limparCachePorPrivacidade,
} from "./common/inspectorLocalPersistence";
import { useInspectorRootLocalState } from "./common/useInspectorRootLocalState";
import { useInspectorRootRefsAndBridges } from "./common/useInspectorRootRefsAndBridges";
import { useInspectorRootShellSupport } from "./common/useInspectorRootShellSupport";
import { useInspectorRuntimeController } from "./common/useInspectorRuntimeController";
import { aplicarPreferenciasLaudos } from "./history/historyHelpers";
import {
  chaveCacheLaudo,
  criarConversaNova,
  normalizarComposerAttachment,
  normalizarModoChat,
} from "./chat/conversationHelpers";
import { erroSugereModoOffline } from "./common/appSupportHelpers";
import { useInspectorSettingsBindings } from "./settings/useInspectorSettingsBindings";
import { useInspectorRootSettingsReauthActions } from "./settings/useInspectorRootSettingsReauthActions";
import { useInspectorRootSettingsSupportState } from "./settings/useInspectorRootSettingsSupportState";
import { reautenticacaoAindaValida } from "./settings/reauth";
import { useInspectorRootSessionFlow } from "./session/useInspectorRootSessionFlow";

export function useInspectorRootBootstrap() {
  const localState = useInspectorRootLocalState({
    cacheLeituraVazio: CACHE_LEITURA_VAZIO,
  });
  const settingsBindings = useInspectorSettingsBindings();
  const runtimeController = useInspectorRuntimeController({
    conversationLaudoId: localState.conversa?.laudoId ?? null,
    preferredVoiceId: settingsBindings.speech.preferredVoiceId,
    setPreferredVoiceId: settingsBindings.speech.setPreferredVoiceId,
    settingsState: settingsBindings.store.settingsState,
  });
  const refsAndBridges = useInspectorRootRefsAndBridges({
    onOpenSystemSettings: Linking.openSettings,
  });
  const colorScheme = useColorScheme();
  const filtroConfiguracoes = "todos" as const;
  const settingsSupportState = useInspectorRootSettingsSupportState();
  const reauthActions = useInspectorRootSettingsReauthActions({
    actionState: {
      abrirConfirmacaoConfiguracao:
        settingsSupportState.navigationActions.abrirConfirmacaoConfiguracao,
      abrirSheetConfiguracao:
        settingsSupportState.navigationActions.abrirSheetConfiguracao,
      fecharSheetConfiguracao:
        settingsSupportState.navigationActions.fecharSheetConfiguracao,
      notificarConfiguracaoConcluida:
        settingsSupportState.navigationActions.notificarConfiguracaoConcluida,
      registrarEventoSegurancaLocal:
        settingsSupportState.registrarEventoSegurancaLocal,
      reautenticacaoAindaValida,
    },
    draftState: {
      reautenticacaoExpiraEm:
        settingsSupportState.presentationState.reautenticacaoExpiraEm,
      settingsSheet: settingsSupportState.navigationState.settingsSheet,
    },
    setterState: {
      setReauthReason: settingsSupportState.presentationActions.setReauthReason,
      setReautenticacaoExpiraEm:
        settingsSupportState.presentationActions.setReautenticacaoExpiraEm,
      setReautenticacaoStatus:
        settingsSupportState.presentationActions.setReautenticacaoStatus,
      setSettingsSheetLoading:
        settingsSupportState.navigationActions.setSettingsSheetLoading,
      setSettingsSheetNotice:
        settingsSupportState.navigationActions.setSettingsSheetNotice,
    },
  });
  const sessionFlow = useInspectorRootSessionFlow({
    bootstrapState: {
      settingsHydrated: settingsBindings.store.settingsHydrated,
      chatHistoryEnabled:
        settingsBindings.store.settingsState.dataControls.chatHistoryEnabled,
      deviceBackupEnabled:
        settingsBindings.store.settingsState.dataControls.deviceBackupEnabled,
      aplicarPreferenciasLaudos,
      chaveCacheLaudo,
      erroSugereModoOffline,
      limparCachePorPrivacidade,
      cacheLeituraVazio: CACHE_LEITURA_VAZIO,
      criarConversaNova,
      normalizarComposerAttachment,
      normalizarModoChat,
    },
    setterState: {
      onSetFilaOffline: localState.setFilaOffline,
      onSetNotificacoes: localState.setNotificacoes,
      onSetCacheLeitura: localState.setCacheLeitura,
      onSetLaudosFixadosIds: localState.setLaudosFixadosIds,
      onSetHistoricoOcultoIds: localState.setHistoricoOcultoIds,
      onSetUsandoCacheOffline: localState.setUsandoCacheOffline,
      onSetLaudosDisponiveis: localState.setLaudosDisponiveis,
      onSetConversa: localState.setConversa,
      onSetMensagensMesa: localState.setMensagensMesa,
      onSetLaudoMesaCarregado: localState.setLaudoMesaCarregado,
      onSetErroLaudos: localState.setErroLaudos,
    },
    resetState: {
      onClearPendingSensitiveAction: reauthActions.clearPendingSensitiveAction,
      onResetSessionBoundSettingsPresentationState:
        settingsSupportState.presentationActions
          .resetSessionBoundSettingsPresentationState,
      onResetSettingsUi: settingsSupportState.navigationActions.resetSettingsUi,
      onSetAbaAtiva: localState.setAbaAtiva,
      onSetAnexoAbrindoChave: localState.setAnexoAbrindoChave,
      onSetAnexoMesaRascunho: localState.setAnexoMesaRascunho,
      onSetAnexoRascunho: localState.setAnexoRascunho,
      onSetBloqueioAppAtivo: localState.setBloqueioAppAtivo,
      onSetErroMesa: localState.setErroMesa,
      onSetGuidedInspectionDraft: localState.setGuidedInspectionDraft,
      onSetMensagem: localState.setMensagem,
      onSetMensagemMesa: localState.setMensagemMesa,
      onSetQualityGateLaudoId: localState.setQualityGateLaudoId,
      onSetQualityGateLoading: localState.setQualityGateLoading,
      onSetQualityGateNotice: localState.setQualityGateNotice,
      onSetQualityGatePayload: localState.setQualityGatePayload,
      onSetQualityGateReason: localState.setQualityGateReason,
      onSetQualityGateSubmitting: localState.setQualityGateSubmitting,
      onSetQualityGateVisible: localState.setQualityGateVisible,
      onSetSincronizandoFilaOffline: localState.setSincronizandoFilaOffline,
      onSetSincronizandoItemFilaId: localState.setSincronizandoItemFilaId,
    },
  });
  const shellSupport = useInspectorRootShellSupport({
    externalAccessState: {
      email: sessionFlow.state.email,
      onCanOpenUrl: Linking.canOpenURL,
      onOpenUrl: Linking.openURL,
      onShowAlert: Alert.alert,
    },
    shellState: {
      appLocked: localState.bloqueioAppAtivo,
      onClearTransientSettingsPresentationState:
        settingsSupportState.presentationActions
          .clearTransientSettingsPresentationState,
      onClearTransientSettingsUiPreservingReauth:
        settingsSupportState.navigationActions
          .clearTransientSettingsUiPreservingReauth,
      onResetAfterSessionEnded: () => {
        localState.setAbaAtiva("chat");
        localState.setAnexoAbrindoChave("");
        localState.setCaseCreationState("idle");
        localState.setGuidedInspectionDraft(null);
        localState.setPendingHistoryThreadRoute(null);
        localState.setQualityGateLaudoId(null);
        localState.setQualityGateNotice("");
        localState.setQualityGatePayload(null);
        localState.setQualityGateReason("");
        localState.setQualityGateVisible(false);
        localState.setThreadHomeVisible(true);
        localState.setThreadHomeGuidedTemplatesVisible(false);
        localState.setThreadRouteHistory([]);
        localState.setUsandoCacheOffline(false);
      },
      resetSettingsNavigation:
        settingsSupportState.navigationActions.resetSettingsNavigation,
      scrollRef: refsAndBridges.scrollRef,
      sessionActive: Boolean(sessionFlow.state.session),
      sessionLoading: sessionFlow.state.carregando,
    },
  });

  return {
    colorScheme,
    filtroConfiguracoes,
    localState,
    reauthActions,
    refsAndBridges,
    runtimeController,
    sessionFlow,
    settingsBindings,
    settingsSupportState,
    shellSupport,
  };
}

export type InspectorRootBootstrap = ReturnType<
  typeof useInspectorRootBootstrap
>;
