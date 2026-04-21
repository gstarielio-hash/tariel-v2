import { isMobileAutomationDiagnosticsEnabled } from "../config/mobileAutomationDiagnostics";
import { buildInspectorRootFinalScreenProps } from "./common/buildInspectorRootFinalScreenProps";
import { formatarHorarioAtividade } from "./common/appSupportHelpers";
import { obterResumoReferenciaMensagem } from "./common/messagePreviewHelpers";
import { mapearStatusLaudoVisual } from "./activity/activityNotificationHelpers";
import { buildAttachmentPickerOptions } from "./chat/attachmentPolicy";
import { chaveAnexo } from "./chat/attachmentFileHelpers";
import { filtrarThreadContextChips } from "./history/historyHelpers";
import {
  detalheStatusPendenciaOffline,
  iconePendenciaOffline,
  legendaPendenciaOffline,
  pendenciaFilaProntaParaReenvio,
  resumoPendenciaOffline,
  rotuloStatusPendenciaOffline,
} from "./offline/offlineQueueHelpers";
import type { InspectorRootBootstrap } from "./useInspectorRootBootstrap";
import type { InspectorRootControllers } from "./useInspectorRootControllers";
import type { InspectorRootPresentationDerivedSnapshot } from "./buildInspectorRootDerivedState";
import { useInspectorRootSettingsSurface } from "./settings/useInspectorRootSettingsSurface";

interface BuildInspectorRootFinalScreenStateInput {
  bootstrap: InspectorRootBootstrap;
  controllers: InspectorRootControllers;
  derivedState: InspectorRootPresentationDerivedSnapshot;
  settingsSurface: ReturnType<typeof useInspectorRootSettingsSurface>;
}

export function buildInspectorRootFinalScreenState({
  bootstrap,
  controllers,
  derivedState,
  settingsSurface,
}: BuildInspectorRootFinalScreenStateInput) {
  const automationDiagnosticsEnabled = isMobileAutomationDiagnosticsEnabled();
  const localState = bootstrap.localState;
  const settingsBindings = bootstrap.settingsBindings;
  const settingsSupportState = bootstrap.settingsSupportState;
  const sessionFlow = bootstrap.sessionFlow;
  const shellSupport = bootstrap.shellSupport;
  const runtimeController = bootstrap.runtimeController;
  const refsAndBridges = bootstrap.refsAndBridges;

  return buildInspectorRootFinalScreenProps({
    authenticatedState: {
      baseState: derivedState.inspectorBaseDerivedState,
      composerState: {
        anexoAbrindoChave: localState.anexoAbrindoChave,
        anexoMesaRascunho: localState.anexoMesaRascunho,
        anexoRascunho: localState.anexoRascunho,
        carregandoConversa: localState.carregandoConversa,
        carregandoMesa: localState.carregandoMesa,
        enviandoMensagem: localState.enviandoMensagem,
        enviandoMesa: localState.enviandoMesa,
        erroMesa: localState.erroMesa,
        handleAbrirQualityGate:
          controllers.chatController.actions.handleAbrirQualityGate,
        handleAbrirSeletorAnexo:
          controllers.attachmentController.handleAbrirSeletorAnexo,
        handleConfirmarQualityGate:
          controllers.chatController.actions.handleConfirmarQualityGate,
        handleEnviarMensagem:
          controllers.chatController.actions.handleEnviarMensagem,
        handleEnviarMensagemMesa:
          controllers.mesaController.actions.handleEnviarMensagemMesa,
        handleFecharQualityGate:
          controllers.chatController.actions.handleFecharQualityGate,
        handleReabrir: controllers.chatController.actions.handleReabrir,
        limparReferenciaMesaAtiva:
          controllers.mesaController.actions.limparReferenciaMesaAtiva,
        mensagem: localState.mensagem,
        mensagemMesa: localState.mensagemMesa,
        mensagemMesaReferenciaAtiva: localState.mensagemMesaReferenciaAtiva,
        qualityGateLoading: localState.qualityGateLoading,
        qualityGateNotice: localState.qualityGateNotice,
        qualityGatePayload: localState.qualityGatePayload,
        qualityGateReason: localState.qualityGateReason,
        qualityGateSubmitting: localState.qualityGateSubmitting,
        qualityGateVisible: localState.qualityGateVisible,
        setAnexoMesaRascunho: localState.setAnexoMesaRascunho,
        setAnexoRascunho: localState.setAnexoRascunho,
        setMensagem: localState.setMensagem,
        setMensagemMesa: localState.setMensagemMesa,
        setQualityGateReason: localState.setQualityGateReason,
      },
      historyState: {
        buscaHistorico: shellSupport.buscaHistorico,
        fecharHistorico: shellSupport.fecharHistorico,
        handleAbrirHistorico:
          controllers.historyController.handleAbrirHistorico,
        handleExcluirConversaHistorico:
          controllers.historyController.handleExcluirConversaHistorico,
        handleSelecionarHistorico:
          controllers.pilotAutomationController
            .handleSelecionarHistoricoComDiagnostico,
        historicoAberto: shellSupport.historicoAberto,
        historicoDrawerX: shellSupport.historicoDrawerX,
        historyDrawerPanResponder: shellSupport.historyDrawerPanResponder,
        historyEdgePanResponder: shellSupport.historyEdgePanResponder,
        setHistorySearchFocused: shellSupport.setHistorySearchFocused,
        setBuscaHistorico: shellSupport.setBuscaHistorico,
      },
      sessionState: {
        scrollRef: refsAndBridges.scrollRef,
        sessionAccessToken: sessionFlow.state.session?.accessToken || "",
        setAbaAtiva: localState.setAbaAtiva,
      },
      shellState: {
        animacoesAtivas: settingsBindings.appearance.animacoesAtivas,
        composerNotice: runtimeController.chatAiBehaviorNotice,
        configuracoesAberta: shellSupport.configuracoesAberta,
        drawerOverlayOpacity: shellSupport.drawerOverlayOpacity,
        erroConversa: localState.erroConversa,
        erroLaudos: localState.erroLaudos,
        fecharPaineisLaterais: shellSupport.fecharPaineisLaterais,
        introVisivel: shellSupport.introVisivel,
        onVoiceInputPress:
          controllers.voiceInputController.handleVoiceInputPress,
        statusApi: sessionFlow.state.statusApi,
        setIntroVisivel: shellSupport.setIntroVisivel,
        settingsDrawerPanelProps: settingsSurface.settingsDrawerPanelProps,
        settingsEdgePanResponder: shellSupport.settingsEdgePanResponder,
      },
      speechState: {
        entradaPorVoz: settingsBindings.speech.entradaPorVoz,
        microfonePermitido: settingsBindings.security.microfonePermitido,
        speechEnabled: settingsBindings.speech.speechEnabled,
      },
      threadState: {
        abrirReferenciaNoChat:
          controllers.chatController.actions.abrirReferenciaNoChat,
        chaveAnexo,
        definirReferenciaMesaAtiva:
          controllers.mesaController.actions.definirReferenciaMesaAtiva,
        handleAbrirAnexo: controllers.attachmentController.handleAbrirAnexo,
        handleAbrirConfiguracoes: shellSupport.handleAbrirConfiguracoes,
        handleAbrirNovoChat:
          controllers.chatController.actions.handleAbrirNovoChat,
        handleExecutarComandoRevisaoMobile:
          controllers.mesaController.actions.handleExecutarComandoRevisaoMobile,
        handleUsarPerguntaPreLaudo: (value) => {
          localState.setAbaAtiva("chat");
          localState.setMensagem(value);
        },
        guidedTemplatesVisible: localState.threadHomeGuidedTemplatesVisible,
        mensagemChatDestacadaId: localState.mensagemChatDestacadaId,
        mensagensMesa: localState.mensagensMesa,
        notificacoesMesaLaudoAtual:
          controllers.operationalState.notificacoesMesaLaudoAtual,
        onGuidedTemplatesVisibleChange:
          localState.setThreadHomeGuidedTemplatesVisible,
        obterResumoReferenciaMensagem,
        registrarLayoutMensagemChat:
          controllers.chatController.actions.registrarLayoutMensagemChat,
      },
    },
    loginState: {
      authActions: {
        handleEsqueciSenha: shellSupport.handleEsqueciSenha,
        handleLogin: sessionFlow.actions.handleLogin,
        handleLoginSocial: shellSupport.handleLoginSocial,
      },
      authState: {
        carregando: sessionFlow.state.carregando,
        email: sessionFlow.state.email,
        emailInputRef: refsAndBridges.emailInputRef,
        entrando: sessionFlow.state.entrando,
        erro: sessionFlow.state.erro,
        loginStage: sessionFlow.state.loginStage,
        mostrarSenha: sessionFlow.state.mostrarSenha,
        senha: sessionFlow.state.senha,
        senhaInputRef: refsAndBridges.senhaInputRef,
        statusApi: sessionFlow.state.statusApi,
        setEmail: sessionFlow.actions.setEmail,
        setMostrarSenha: sessionFlow.actions.setMostrarSenha,
        setSenha: sessionFlow.actions.setSenha,
      },
      baseState: derivedState.inspectorBaseDerivedState,
      presentationState: {
        animacoesAtivas: settingsBindings.appearance.animacoesAtivas,
        automationDiagnosticsEnabled,
        introVisivel: shellSupport.introVisivel,
      },
      setIntroVisivel: shellSupport.setIntroVisivel,
    },
    sessionModalsState: {
      activityAndLockState: {
        activityCenterAutomationDiagnostics:
          controllers.pilotAutomationController
            .activityCenterAutomationDiagnostics,
        automationDiagnosticsEnabled,
        bloqueioAppAtivo: localState.bloqueioAppAtivo,
        centralAtividadeAberta: shellSupport.centralAtividadeAberta,
        deviceBiometricsEnabled:
          settingsBindings.security.deviceBiometricsEnabled,
        formatarHorarioAtividade,
        handleAbrirNotificacao:
          controllers.activityCenterController.actions.handleAbrirNotificacao,
        handleDesbloquearAplicativo:
          controllers.appLockController.actions.handleDesbloquearAplicativo,
        handleLogout: sessionFlow.actions.handleLogout,
        monitorandoAtividade:
          controllers.activityCenterController.state.monitorandoAtividade,
        notificacoes: localState.notificacoes,
        session: sessionFlow.state.session,
        setCentralAtividadeAberta: shellSupport.setCentralAtividadeAberta,
      },
      attachmentState: {
        anexosAberto: shellSupport.anexosAberto,
        attachmentPickerOptions: buildAttachmentPickerOptions({
          activeThread: localState.abaAtiva,
          conversation: derivedState.conversaAtiva,
        }),
        handleEscolherAnexo:
          controllers.attachmentController.handleEscolherAnexo,
        previewAnexoImagem: shellSupport.previewAnexoImagem,
        setAnexosAberto: shellSupport.setAnexosAberto,
        setPreviewAnexoImagem: shellSupport.setPreviewAnexoImagem,
      },
      baseState: derivedState.inspectorBaseDerivedState,
      offlineQueueState: {
        detalheStatusPendenciaOffline: (item) =>
          detalheStatusPendenciaOffline(item, formatarHorarioAtividade),
        filaOfflineAberta: shellSupport.filaOfflineAberta,
        filtroFilaOffline: localState.filtroFilaOffline,
        handleRetomarItemFilaOffline:
          controllers.offlineQueueController.actions
            .handleRetomarItemFilaOffline,
        iconePendenciaOffline,
        legendaPendenciaOffline,
        pendenciaFilaProntaParaReenvio,
        removerItemFilaOffline:
          controllers.offlineQueueController.actions.removerItemFilaOffline,
        resumoPendenciaOffline,
        rotuloStatusPendenciaOffline,
        setFilaOfflineAberta: shellSupport.setFilaOfflineAberta,
        setFiltroFilaOffline: localState.setFiltroFilaOffline,
        sincronizacaoDispositivos:
          settingsBindings.dataControls.sincronizacaoDispositivos,
        sincronizarFilaOffline:
          controllers.offlineQueueController.actions.sincronizarFilaOffline,
        sincronizarItemFilaOffline:
          controllers.offlineQueueController.actions.sincronizarItemFilaOffline,
        sincronizandoFilaOffline: localState.sincronizandoFilaOffline,
        sincronizandoItemFilaId: localState.sincronizandoItemFilaId,
        statusApi: sessionFlow.state.statusApi,
      },
      settingsState: {
        confirmSheet: settingsSupportState.navigationState.confirmSheet,
        confirmTextDraft: settingsSupportState.navigationState.confirmTextDraft,
        fecharConfirmacaoConfiguracao:
          settingsSupportState.navigationActions.fecharConfirmacaoConfiguracao,
        fecharSheetConfiguracao:
          settingsSupportState.navigationActions.fecharSheetConfiguracao,
        handleConfirmarAcaoCritica: settingsSurface.handleConfirmarAcaoCritica,
        handleConfirmarSettingsSheet:
          settingsSurface.handleConfirmarSettingsSheet,
        renderSettingsSheetBody: settingsSurface.renderSettingsSheetBody,
        setConfirmTextDraft:
          settingsSupportState.navigationActions.setConfirmTextDraft,
        settingsSheet: settingsSupportState.navigationState.settingsSheet,
        settingsSheetLoading:
          settingsSupportState.navigationState.settingsSheetLoading,
        settingsSheetNotice:
          settingsSupportState.navigationState.settingsSheetNotice,
      },
    },
    threadContextInput: {
      caseCreationError: localState.erroConversa,
      caseCreationState: localState.caseCreationState,
      conversaAtiva: derivedState.conversaAtiva,
      entryModePreference: settingsBindings.ai.entryModePreference,
      filtrarThreadContextChips,
      mapearStatusLaudoVisual,
      laudosDisponiveis: localState.laudosDisponiveis,
      mesaDisponivel: derivedState.mesaDisponivel,
      mesaTemMensagens: derivedState.mesaTemMensagens,
      mensagensMesa: localState.mensagensMesa,
      notificacoesMesaLaudoAtual:
        controllers.operationalState.notificacoesMesaLaudoAtual,
      resumoFilaOffline: derivedState.resumoFilaOffline,
      statusApi: sessionFlow.state.statusApi,
      threadHomeVisible: localState.threadHomeVisible,
      tipoTemplateAtivoLabel: derivedState.tipoTemplateAtivoLabel,
      guidedInspectionDraft: bootstrap.localState.guidedInspectionDraft,
      onAdvanceGuidedInspection:
        controllers.guidedInspectionController.actions
          .handleAdvanceGuidedInspection,
      onOpenMesaTab: () => {
        localState.setAbaAtiva("mesa");
      },
      onOpenQualityGate:
        controllers.chatController.actions.handleAbrirQualityGate,
      onResumeGuidedInspection:
        controllers.chatController.actions.handleAbrirColetaGuiadaAtual,
      onStartFreeChat: () => {
        void controllers.chatController.actions.handleIniciarChatLivre();
      },
      onStartGuidedInspection: (templateKey = "nr35_linha_vida") => {
        controllers.guidedInspectionController.actions.handleStartGuidedInspection(
          {
            templateKey,
          },
        );
      },
      onStopGuidedInspection:
        controllers.guidedInspectionController.actions
          .handleStopGuidedInspection,
      rememberLastCaseMode: settingsBindings.ai.rememberLastCaseMode,
      vendoMesa: derivedState.vendoMesa,
      vendoFinalizacao: derivedState.vendoFinalizacao,
    },
  });
}
