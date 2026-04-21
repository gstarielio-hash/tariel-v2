import { Alert, Keyboard } from "react-native";

import {
  chaveAnexo,
  inferirExtensaoAnexo,
  montarAnexoDocumentoLocal,
  montarAnexoDocumentoMesa,
  montarAnexoImagem,
  nomeArquivoSeguro,
} from "./chat/attachmentFileHelpers";
import {
  atualizarResumoLaudoAtual,
  chaveCacheLaudo,
  chaveRascunho,
  criarConversaNova,
  criarMensagemAssistenteServidor,
  inferirSetorConversa,
  montarHistoricoParaEnvio,
  normalizarConversa,
  normalizarModoChat,
  podeEditarConversaNoComposer,
  textoFallbackAnexo,
} from "./chat/conversationHelpers";
import { useInspectorRootAttachmentController } from "./chat/useInspectorRootAttachmentController";
import { useInspectorRootChatController } from "./chat/useInspectorRootChatController";
import { useInspectorRootVoiceInputController } from "./chat/useInspectorRootVoiceInputController";
import { buildVoiceInputUnavailableMessage } from "./chat/voice";
import { erroSugereModoOffline } from "./common/appSupportHelpers";
import { useInspectorRootHistoryController } from "./history/useInspectorRootHistoryController";
import { aplicarPreferenciasLaudos } from "./history/historyHelpers";
import { useInspectorRootGuidedInspectionController } from "./inspection/useInspectorRootGuidedInspectionController";
import { useInspectorRootMesaController } from "./mesa/useInspectorRootMesaController";
import { criarItemFilaOffline } from "./offline/offlineQueueHelpers";
import type { InspectorRootBootstrap } from "./useInspectorRootBootstrap";

export function useInspectorRootConversationControllers(
  bootstrap: InspectorRootBootstrap,
) {
  const mesaController = useInspectorRootMesaController({
    state: {
      activeThread: bootstrap.localState.abaAtiva,
      attachmentDraft: bootstrap.localState.anexoMesaRascunho,
      conversation: bootstrap.localState.conversa,
      laudoMesaCarregado: bootstrap.localState.laudoMesaCarregado,
      messageMesa: bootstrap.localState.mensagemMesa,
      messagesMesa: bootstrap.localState.mensagensMesa,
      session: bootstrap.sessionFlow.state.session,
      statusApi: bootstrap.sessionFlow.state.statusApi,
      wifiOnlySync: bootstrap.settingsBindings.dataControls.wifiOnlySync,
    },
    refState: {
      carregarListaLaudosRef: bootstrap.refsAndBridges.carregarListaLaudosRef,
      scrollRef: bootstrap.refsAndBridges.scrollRef,
    },
    cacheState: {
      cacheLeitura: bootstrap.localState.cacheLeitura,
      chaveCacheLaudo,
      chaveRascunho,
      textoFallbackAnexo,
    },
    actionState: {
      activeReference: bootstrap.localState.mensagemMesaReferenciaAtiva,
      atualizarResumoLaudoAtual,
      criarItemFilaOffline,
      erroSugereModoOffline,
      onObserveMesaThreadReadMetadata:
        bootstrap.localState.setUltimoMetaLeituraThreadMesa,
    },
    setterState: {
      setActiveReference: bootstrap.localState.setMensagemMesaReferenciaAtiva,
      setAttachmentDraft: bootstrap.localState.setAnexoMesaRascunho,
      setCacheLeitura: bootstrap.localState.setCacheLeitura,
      setConversation: bootstrap.localState.setConversa,
      setErrorMesa: bootstrap.localState.setErroMesa,
      setFilaOffline: bootstrap.localState.setFilaOffline,
      setLaudoMesaCarregado: bootstrap.localState.setLaudoMesaCarregado,
      setLoadingMesa: bootstrap.localState.setCarregandoMesa,
      setMessageMesa: bootstrap.localState.setMensagemMesa,
      setMessagesMesa: bootstrap.localState.setMensagensMesa,
      setSendingMesa: bootstrap.localState.setEnviandoMesa,
      setStatusApi: bootstrap.sessionFlow.actions.setStatusApi,
      setSyncMesa: bootstrap.localState.setSincronizandoMesa,
      setUsandoCacheOffline: bootstrap.localState.setUsandoCacheOffline,
    },
  });

  const guidedInspectionController = useInspectorRootGuidedInspectionController(
    {
      actionState: {
        onShowAlert: (title, message) => {
          Alert.alert(title, message);
        },
      },
      state: {
        activeThread: bootstrap.localState.abaAtiva,
        conversation: bootstrap.localState.conversa,
        draft: bootstrap.localState.guidedInspectionDraft,
      },
      setterState: {
        setActiveThread: bootstrap.localState.setAbaAtiva,
        setErrorConversation: bootstrap.localState.setErroConversa,
        setGuidedInspectionDraft: bootstrap.localState.setGuidedInspectionDraft,
        setMessage: bootstrap.localState.setMensagem,
        setThreadHomeVisible: bootstrap.localState.setThreadHomeVisible,
      },
    },
  );

  const chatController = useInspectorRootChatController({
    sessionState: {
      activeThread: bootstrap.localState.abaAtiva,
      aiRequestConfig: bootstrap.runtimeController.aiRequestConfig,
      entryModePreference: bootstrap.settingsBindings.ai.entryModePreference,
      rememberLastCaseMode: bootstrap.settingsBindings.ai.rememberLastCaseMode,
      session: bootstrap.sessionFlow.state.session,
      sessionLoading: bootstrap.sessionFlow.state.carregando,
      speechSettings: bootstrap.settingsBindings.store.settingsState.speech,
      statusApi: bootstrap.sessionFlow.state.statusApi,
      wifiOnlySync: bootstrap.settingsBindings.dataControls.wifiOnlySync,
    },
    conversationState: {
      attachmentDraft: bootstrap.localState.anexoRascunho,
      cacheLeitura: bootstrap.localState.cacheLeitura,
      conversation: bootstrap.localState.conversa,
      guidedInspectionDraft: bootstrap.localState.guidedInspectionDraft,
      highlightedMessageId: bootstrap.localState.mensagemChatDestacadaId,
      historicoOcultoIds: bootstrap.localState.historicoOcultoIds,
      laudoMesaCarregado: bootstrap.localState.laudoMesaCarregado,
      laudosDisponiveis: bootstrap.localState.laudosDisponiveis,
      laudosFixadosIds: bootstrap.localState.laudosFixadosIds,
      layoutVersion: bootstrap.localState.layoutMensagensChatVersao,
      message: bootstrap.localState.mensagem,
      qualityGateLaudoId: bootstrap.localState.qualityGateLaudoId,
      qualityGatePayload: bootstrap.localState.qualityGatePayload,
      qualityGateReason: bootstrap.localState.qualityGateReason,
      scrollRef: bootstrap.refsAndBridges.scrollRef,
    },
    mesaState: {
      carregarMesaAtual: mesaController.actions.carregarMesaAtual,
      clearMesaReference: mesaController.actions.limparReferenciaMesaAtiva,
      clearGuidedInspectionDraft: () =>
        bootstrap.localState.setGuidedInspectionDraft(null),
      setAnexoMesaRascunho: bootstrap.localState.setAnexoMesaRascunho,
      setErroMesa: bootstrap.localState.setErroMesa,
      setLaudoMesaCarregado: bootstrap.localState.setLaudoMesaCarregado,
      setMensagemMesa: bootstrap.localState.setMensagemMesa,
      setMensagensMesa: bootstrap.localState.setMensagensMesa,
      startGuidedInspection:
        guidedInspectionController.actions.handleStartGuidedInspection,
    },
    setterState: {
      onSetActiveThread: bootstrap.localState.setAbaAtiva,
      setAttachmentDraft: bootstrap.localState.setAnexoRascunho,
      setCacheLeitura: bootstrap.localState.setCacheLeitura,
      setCaseCreationState: bootstrap.localState.setCaseCreationState,
      setConversation: bootstrap.localState.setConversa,
      setErrorConversation: bootstrap.localState.setErroConversa,
      setErrorLaudos: bootstrap.localState.setErroLaudos,
      setFilaOffline: bootstrap.localState.setFilaOffline,
      setHighlightedMessageId: bootstrap.localState.setMensagemChatDestacadaId,
      setLaudosDisponiveis: bootstrap.localState.setLaudosDisponiveis,
      setLayoutVersion: bootstrap.localState.setLayoutMensagensChatVersao,
      setLoadingConversation: bootstrap.localState.setCarregandoConversa,
      setLoadingLaudos: bootstrap.localState.setCarregandoLaudos,
      setMessage: bootstrap.localState.setMensagem,
      setQualityGateLaudoId: bootstrap.localState.setQualityGateLaudoId,
      setQualityGateLoading: bootstrap.localState.setQualityGateLoading,
      setQualityGateNotice: bootstrap.localState.setQualityGateNotice,
      setQualityGatePayload: bootstrap.localState.setQualityGatePayload,
      setQualityGateReason: bootstrap.localState.setQualityGateReason,
      setQualityGateSubmitting: bootstrap.localState.setQualityGateSubmitting,
      setQualityGateVisible: bootstrap.localState.setQualityGateVisible,
      setSendingMessage: bootstrap.localState.setEnviandoMensagem,
      setStatusApi: bootstrap.sessionFlow.actions.setStatusApi,
      setSyncConversation: bootstrap.localState.setSincronizandoConversa,
      setThreadHomeGuidedTemplatesVisible:
        bootstrap.localState.setThreadHomeGuidedTemplatesVisible,
      setThreadHomeVisible: bootstrap.localState.setThreadHomeVisible,
      setUsandoCacheOffline: bootstrap.localState.setUsandoCacheOffline,
    },
    actionState: {
      aplicarPreferenciasLaudos,
      atualizarResumoLaudoAtual,
      chaveCacheLaudo,
      chaveRascunho,
      criarConversaNova,
      criarItemFilaOffline,
      criarMensagemAssistenteServidor,
      erroSugereModoOffline,
      inferirSetorConversa,
      montarHistoricoParaEnvio,
      normalizarConversa,
      normalizarModoChat,
      podeEditarConversaNoComposer,
      textoFallbackAnexo,
    },
  });
  bootstrap.refsAndBridges.onRegisterCarregarListaLaudos(
    chatController.actions.carregarListaLaudos,
  );

  const attachmentController = useInspectorRootAttachmentController({
    accessState: {
      abaAtiva: bootstrap.localState.abaAtiva,
      arquivosPermitidos:
        bootstrap.settingsBindings.security.arquivosPermitidos,
      cameraPermitida: bootstrap.settingsBindings.security.cameraPermitida,
      conversaAtiva: bootstrap.localState.conversa,
      sessionAccessToken:
        bootstrap.sessionFlow.state.session?.accessToken || null,
      statusApi: bootstrap.sessionFlow.state.statusApi,
      uploadArquivosAtivo:
        bootstrap.settingsBindings.attachments.uploadArquivosAtivo,
      wifiOnlySync: bootstrap.settingsBindings.dataControls.wifiOnlySync,
    },
    policyState: {
      autoUploadAttachments:
        bootstrap.settingsBindings.dataControls.autoUploadAttachments,
      disableAggressiveDownloads:
        bootstrap.runtimeController.attachmentHandlingPolicy
          .disableAggressiveDownloads,
      erroSugereModoOffline,
      imageQuality:
        bootstrap.runtimeController.attachmentHandlingPolicy.imageQuality,
      preparandoAnexo: bootstrap.localState.preparandoAnexo,
    },
    builderState: {
      inferirExtensaoAnexo,
      montarAnexoDocumentoLocal,
      montarAnexoDocumentoMesa,
      montarAnexoImagem,
      nomeArquivoSeguro,
      onBuildAttachmentKey: chaveAnexo,
      onShowAlert: Alert.alert,
    },
    setterState: {
      setAnexosAberto: bootstrap.shellSupport.setAnexosAberto,
      setAnexoAbrindoChave: bootstrap.localState.setAnexoAbrindoChave,
      setAnexoMesaRascunho: bootstrap.localState.setAnexoMesaRascunho,
      setAnexoRascunho: bootstrap.localState.setAnexoRascunho,
      setErroConversa: bootstrap.localState.setErroConversa,
      setPreparandoAnexo: bootstrap.localState.setPreparandoAnexo,
      setPreviewAnexoImagem: bootstrap.shellSupport.setPreviewAnexoImagem,
      setStatusApi: bootstrap.sessionFlow.actions.setStatusApi,
    },
  });

  const voiceInputController = useInspectorRootVoiceInputController({
    capabilityState: {
      entradaPorVoz: bootstrap.settingsBindings.speech.entradaPorVoz,
      microfonePermitido:
        bootstrap.settingsBindings.security.microfonePermitido,
      speechEnabled: bootstrap.settingsBindings.speech.speechEnabled,
      voiceInputUnavailableMessage: buildVoiceInputUnavailableMessage(
        bootstrap.settingsBindings.speech.voiceLanguage,
      ),
      voiceRuntimeSupported:
        bootstrap.runtimeController.voiceRuntimeState.sttSupported,
    },
    voiceState: {
      preferredVoiceId: bootstrap.settingsBindings.speech.preferredVoiceId,
      voices: bootstrap.runtimeController.voiceRuntimeState.voices,
    },
    actionState: {
      onOpenSystemSettings: bootstrap.refsAndBridges.onOpenSystemSettings,
      onSetMicrofonePermitido:
        bootstrap.settingsBindings.security.setMicrofonePermitido,
      onSetPreferredVoiceId:
        bootstrap.settingsBindings.speech.setPreferredVoiceId,
      onShowAlert: Alert.alert,
    },
  });

  const historyController = useInspectorRootHistoryController({
    state: {
      conversaAtualLaudoId: bootstrap.localState.conversa?.laudoId ?? null,
      historicoOcultoIds: bootstrap.localState.historicoOcultoIds,
      historicoAberto: bootstrap.shellSupport.historicoAberto,
      historicoAbertoRefAtual:
        bootstrap.shellSupport.historicoAbertoRef.current,
      keyboardHeight: bootstrap.shellSupport.keyboardHeight,
      laudosFixadosIds: bootstrap.localState.laudosFixadosIds,
      pendingHistoryThreadRoute: bootstrap.localState.pendingHistoryThreadRoute,
    },
    actionState: {
      abrirHistorico: bootstrap.shellSupport.abrirHistorico,
      fecharConfiguracoes: bootstrap.shellSupport.fecharConfiguracoes,
      fecharHistorico: bootstrap.shellSupport.fecharHistorico,
      handleSelecionarLaudo: chatController.actions.handleSelecionarLaudo,
      onCreateNewConversation: criarConversaNova,
      onDismissKeyboard: Keyboard.dismiss,
      onGetCacheKeyForLaudo: chaveCacheLaudo,
      onSchedule: bootstrap.refsAndBridges.onScheduleWithTimeout,
    },
    setterState: {
      setAbaAtiva: bootstrap.localState.setAbaAtiva,
      setAnexoMesaRascunho: bootstrap.localState.setAnexoMesaRascunho,
      setAnexoRascunho: bootstrap.localState.setAnexoRascunho,
      setCacheLeitura: bootstrap.localState.setCacheLeitura,
      setConversa: bootstrap.localState.setConversa,
      setErroConversa: bootstrap.localState.setErroConversa,
      setErroMesa: bootstrap.localState.setErroMesa,
      setHistoricoOcultoIds: bootstrap.localState.setHistoricoOcultoIds,
      setLaudoMesaCarregado: bootstrap.localState.setLaudoMesaCarregado,
      setLaudosDisponiveis: bootstrap.localState.setLaudosDisponiveis,
      setLaudosFixadosIds: bootstrap.localState.setLaudosFixadosIds,
      setMensagem: bootstrap.localState.setMensagem,
      setMensagemMesa: bootstrap.localState.setMensagemMesa,
      setMensagensMesa: bootstrap.localState.setMensagensMesa,
      setNotificacoes: bootstrap.localState.setNotificacoes,
      setPendingHistoryThreadRoute:
        bootstrap.localState.setPendingHistoryThreadRoute,
      setThreadRouteHistory: bootstrap.localState.setThreadRouteHistory,
    },
  });

  return {
    attachmentController,
    chatController,
    guidedInspectionController,
    historyController,
    mesaController,
    voiceInputController,
  };
}

export type InspectorRootConversationControllers = ReturnType<
  typeof useInspectorRootConversationControllers
>;
