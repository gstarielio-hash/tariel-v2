import { useSettingsStore } from "../../settings/hooks/useSettings";
import type { AppSettings } from "../../settings/schema/types";

export function useInspectorSettingsBindings() {
  const {
    state: settingsState,
    hydrated: settingsHydrated,
    actions: settingsActions,
  } = useSettingsStore();
  const biometriaLocalSuportada = false;

  return {
    store: {
      settingsActions,
      settingsHydrated,
      settingsState,
    },
    account: {
      contaTelefone: settingsState.account.phone,
      emailAtualConta: settingsState.account.email,
      perfilExibicao: settingsState.account.displayName,
      perfilFotoHint: settingsState.account.photoHint,
      perfilFotoUri: settingsState.account.photoUri,
      perfilNome: settingsState.account.fullName,
      setEmailAtualConta: (value: string) =>
        settingsActions.updateAccount({ email: value }),
      setPerfilExibicao: (value: string) =>
        settingsActions.updateAccount({ displayName: value }),
      setPerfilFotoHint: (value: string) =>
        settingsActions.updateAccount({ photoHint: value }),
      setPerfilFotoUri: (value: string) =>
        settingsActions.updateAccount({ photoUri: value }),
      setPerfilNome: (value: string) =>
        settingsActions.updateAccount({ fullName: value }),
    },
    ai: {
      aprendizadoIa: settingsState.ai.learningOptIn,
      compartilharMelhoriaIa: settingsState.ai.learningOptIn,
      entryModePreference: settingsState.ai.entryModePreference,
      estiloResposta: settingsState.ai.responseStyle,
      idiomaResposta: settingsState.ai.responseLanguage,
      memoriaIa: settingsState.ai.memoryEnabled,
      modeloIa: settingsState.ai.model,
      rememberLastCaseMode: settingsState.ai.rememberLastCaseMode,
      setAprendizadoIa: (value: boolean) =>
        settingsActions.updateAi({ learningOptIn: value }),
      setCompartilharMelhoriaIa: (value: boolean) =>
        settingsActions.updateAi({ learningOptIn: value }),
      setEntryModePreference: (
        value: AppSettings["ai"]["entryModePreference"],
      ) => settingsActions.updateAi({ entryModePreference: value }),
      setEstiloResposta: (value: AppSettings["ai"]["responseStyle"]) =>
        settingsActions.updateAi({ responseStyle: value }),
      setIdiomaResposta: (value: AppSettings["ai"]["responseLanguage"]) =>
        settingsActions.updateAi({ responseLanguage: value }),
      setMemoriaIa: (value: boolean) =>
        settingsActions.updateAi({ memoryEnabled: value }),
      setModeloIa: (value: AppSettings["ai"]["model"]) =>
        settingsActions.updateAi({ model: value }),
      setRememberLastCaseMode: (value: boolean) =>
        settingsActions.updateAi({ rememberLastCaseMode: value }),
      setTemperaturaIa: (value: number) =>
        settingsActions.updateAi({ temperature: value }),
      setTomConversa: (value: AppSettings["ai"]["tone"]) =>
        settingsActions.updateAi({ tone: value }),
      temperaturaIa: settingsState.ai.temperature,
      tomConversa: settingsState.ai.tone,
    },
    appearance: {
      animacoesAtivas: settingsState.appearance.animationsEnabled,
      corDestaque: settingsState.appearance.accentColor,
      densidadeInterface: settingsState.appearance.density,
      setAnimacoesAtivas: (value: boolean) =>
        settingsActions.updateAppearance({ animationsEnabled: value }),
      setCorDestaque: (value: AppSettings["appearance"]["accentColor"]) =>
        settingsActions.updateAppearance({ accentColor: value }),
      setDensidadeInterface: (value: AppSettings["appearance"]["density"]) =>
        settingsActions.updateAppearance({ density: value }),
      setTamanhoFonte: (value: AppSettings["appearance"]["fontScale"]) =>
        settingsActions.updateAppearance({ fontScale: value }),
      setTemaApp: (value: AppSettings["appearance"]["theme"]) =>
        settingsActions.updateAppearance({ theme: value }),
      tamanhoFonte: settingsState.appearance.fontScale,
      temaApp: settingsState.appearance.theme,
    },
    notifications: {
      chatCategoryEnabled: settingsState.notifications.chatCategoryEnabled,
      criticalAlertsEnabled: settingsState.notifications.criticalAlertsEnabled,
      emailsAtivos: settingsState.notifications.emailEnabled,
      mesaCategoryEnabled: settingsState.notifications.mesaCategoryEnabled,
      mostrarConteudoNotificacao:
        settingsState.notifications.showMessageContent,
      mostrarSomenteNovaMensagem:
        settingsState.notifications.onlyShowNewMessage,
      notificaPush: settingsState.notifications.pushEnabled,
      notificaRespostas: settingsState.notifications.responseAlertsEnabled,
      notificacoesPermitidas: settingsState.security.notificationsPermission,
      ocultarConteudoBloqueado:
        settingsState.notifications.hideContentOnLockScreen,
      setChatCategoryEnabled: (value: boolean) =>
        settingsActions.updateNotifications({ chatCategoryEnabled: value }),
      setCriticalAlertsEnabled: (value: boolean) =>
        settingsActions.updateNotifications({ criticalAlertsEnabled: value }),
      setEmailsAtivos: (value: boolean) =>
        settingsActions.updateNotifications({ emailEnabled: value }),
      setMesaCategoryEnabled: (value: boolean) =>
        settingsActions.updateNotifications({ mesaCategoryEnabled: value }),
      setMostrarConteudoNotificacao: (value: boolean) =>
        settingsActions.updateNotifications({ showMessageContent: value }),
      setMostrarSomenteNovaMensagem: (value: boolean) =>
        settingsActions.updateNotifications({ onlyShowNewMessage: value }),
      setNotificaPush: (value: boolean) =>
        settingsActions.updateNotifications({ pushEnabled: value }),
      setNotificaRespostas: (value: boolean) =>
        settingsActions.updateNotifications({ responseAlertsEnabled: value }),
      setNotificacoesPermitidas: (value: boolean) =>
        settingsActions.updateSecurity({ notificationsPermission: value }),
      setOcultarConteudoBloqueado: (value: boolean) =>
        settingsActions.updateNotifications({
          hideContentOnLockScreen: value,
        }),
      setSomNotificacao: (value: AppSettings["notifications"]["soundPreset"]) =>
        settingsActions.updateNotifications({
          soundPreset: value,
          soundEnabled: value !== "Silencioso",
        }),
      setSystemCategoryEnabled: (value: boolean) =>
        settingsActions.updateNotifications({ systemCategoryEnabled: value }),
      setVibracaoAtiva: (value: boolean) =>
        settingsActions.updateNotifications({ vibrationEnabled: value }),
      somNotificacao: settingsState.notifications.soundPreset,
      systemCategoryEnabled: settingsState.notifications.systemCategoryEnabled,
      vibracaoAtiva: settingsState.notifications.vibrationEnabled,
    },
    dataControls: {
      analyticsOptIn: settingsState.dataControls.analyticsOptIn,
      autoUploadAttachments: settingsState.dataControls.autoUploadAttachments,
      backupAutomatico: settingsState.dataControls.deviceBackupEnabled,
      crashReportsOptIn: settingsState.dataControls.crashReportsOptIn,
      mediaCompression: settingsState.dataControls.mediaCompression,
      retencaoDados: settingsState.dataControls.retention,
      salvarHistoricoConversas: settingsState.dataControls.chatHistoryEnabled,
      setAnalyticsOptIn: (value: boolean) =>
        settingsActions.updateDataControls({ analyticsOptIn: value }),
      setAutoUploadAttachments: (value: boolean) =>
        settingsActions.updateDataControls({
          autoUploadAttachments: value,
        }),
      setBackupAutomatico: (value: boolean) =>
        settingsActions.updateDataControls({ deviceBackupEnabled: value }),
      setCrashReportsOptIn: (value: boolean) =>
        settingsActions.updateDataControls({ crashReportsOptIn: value }),
      setMediaCompression: (
        value: AppSettings["dataControls"]["mediaCompression"],
      ) => settingsActions.updateDataControls({ mediaCompression: value }),
      setRetencaoDados: (value: AppSettings["dataControls"]["retention"]) =>
        settingsActions.updateDataControls({ retention: value }),
      setSalvarHistoricoConversas: (value: boolean) =>
        settingsActions.updateDataControls({ chatHistoryEnabled: value }),
      setSincronizacaoDispositivos: (value: boolean) =>
        settingsActions.updateDataControls({
          crossDeviceSyncEnabled: value,
        }),
      setWifiOnlySync: (value: boolean) =>
        settingsActions.updateDataControls({ wifiOnlySync: value }),
      sincronizacaoDispositivos:
        settingsState.dataControls.crossDeviceSyncEnabled,
      wifiOnlySync: settingsState.dataControls.wifiOnlySync,
    },
    speech: {
      entradaPorVoz: settingsState.speech.autoTranscribe,
      preferredVoiceId: settingsState.speech.voiceId,
      respostaPorVoz: settingsState.speech.autoReadResponses,
      setEntradaPorVoz: (value: boolean) =>
        settingsActions.updateSpeech({
          autoTranscribe: value,
          enabled: value || settingsState.speech.autoReadResponses,
        }),
      setPreferredVoiceId: (value: string) =>
        settingsActions.updateSpeech({ voiceId: value }),
      setRespostaPorVoz: (value: boolean) =>
        settingsActions.updateSpeech({
          autoReadResponses: value,
          enabled: value || settingsState.speech.autoTranscribe,
        }),
      setSpeechEnabled: (value: boolean) =>
        settingsActions.updateSpeech({
          enabled: value,
          autoTranscribe: value ? settingsState.speech.autoTranscribe : false,
          autoReadResponses: value
            ? settingsState.speech.autoReadResponses
            : false,
        }),
      setSpeechRate: (value: number) =>
        settingsActions.updateSpeech({ speechRate: value }),
      setVoiceLanguage: (value: AppSettings["speech"]["voiceLanguage"]) =>
        settingsActions.updateSpeech({ voiceLanguage: value }),
      speechEnabled: settingsState.speech.enabled,
      speechRate: settingsState.speech.speechRate,
      voiceLanguage: settingsState.speech.voiceLanguage,
    },
    attachments: {
      setUploadArquivosAtivo: (value: boolean) =>
        settingsActions.updateAttachments({ enabled: value }),
      uploadArquivosAtivo: settingsState.attachments.enabled,
    },
    system: {
      economiaDados: settingsState.system.dataSaver,
      idiomaApp: settingsState.system.language,
      regiaoApp: settingsState.system.region,
      setEconomiaDados: (value: boolean) =>
        settingsActions.updateSystem({ dataSaver: value }),
      setIdiomaApp: (value: AppSettings["system"]["language"]) =>
        settingsActions.updateSystem({ language: value }),
      setRegiaoApp: (value: AppSettings["system"]["region"]) =>
        settingsActions.updateSystem({ region: value }),
      setUsoBateria: (value: AppSettings["system"]["batteryMode"]) =>
        settingsActions.updateSystem({ batteryMode: value }),
      usoBateria: settingsState.system.batteryMode,
    },
    security: {
      arquivosPermitidos: settingsState.security.filesPermission,
      biometriaLocalSuportada,
      biometriaPermitida: settingsState.security.biometricsPermission,
      cameraPermitida: settingsState.security.cameraPermission,
      deviceBiometricsEnabled:
        biometriaLocalSuportada &&
        settingsState.security.deviceBiometricsEnabled,
      hideInMultitask: settingsState.security.hideInMultitask,
      lockTimeout: settingsState.security.lockTimeout,
      microfonePermitido: settingsState.security.microphonePermission,
      requireAuthOnOpen: settingsState.security.requireAuthOnOpen,
      setArquivosPermitidos: (value: boolean) =>
        settingsActions.updateSecurity({ filesPermission: value }),
      setBiometriaPermitida: (value: boolean) =>
        settingsActions.updateSecurity({ biometricsPermission: value }),
      setCameraPermitida: (value: boolean) =>
        settingsActions.updateSecurity({ cameraPermission: value }),
      setDeviceBiometricsEnabled: (value: boolean) =>
        settingsActions.updateSecurity({ deviceBiometricsEnabled: value }),
      setHideInMultitask: (value: boolean) =>
        settingsActions.updateSecurity({ hideInMultitask: value }),
      setLockTimeout: (value: AppSettings["security"]["lockTimeout"]) =>
        settingsActions.updateSecurity({ lockTimeout: value }),
      setMicrofonePermitido: (value: boolean) =>
        settingsActions.updateSecurity({ microphonePermission: value }),
      setRequireAuthOnOpen: (value: boolean) =>
        settingsActions.updateSecurity({ requireAuthOnOpen: value }),
    },
  };
}
