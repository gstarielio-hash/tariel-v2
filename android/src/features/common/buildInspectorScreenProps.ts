import type { ComponentProps, Dispatch, SetStateAction } from "react";

import type { BuildLoginScreenPropsInput } from "../auth/buildLoginScreenProps";
import { buildLoginScreenProps } from "../auth/buildLoginScreenProps";
import { LoginScreen } from "../auth/LoginScreen";
import type { InspectorBaseDerivedState } from "./buildInspectorBaseDerivedState";
import { buildAuthenticatedLayoutInput } from "./buildAuthenticatedLayoutInput";
import { buildAuthenticatedLayoutProps } from "./buildAuthenticatedLayoutProps";
import type {
  AuthenticatedLayoutComposerInput,
  AuthenticatedLayoutHistoryInput,
  AuthenticatedLayoutSessionInput,
  AuthenticatedLayoutShellInput,
  AuthenticatedLayoutThreadInput,
} from "./inspectorUiBuilderTypes";
import { InspectorAuthenticatedLayout } from "../InspectorAuthenticatedLayout";
import type { ThreadContextStateResult } from "./inspectorDerivedStateTypes";

type InspectorAuthenticatedBaseState = Pick<
  InspectorBaseDerivedState,
  | "accentColor"
  | "appGradientColors"
  | "chatKeyboardVerticalOffset"
  | "conversaAtiva"
  | "conversaVazia"
  | "conversasOcultasTotal"
  | "dynamicComposerInputStyle"
  | "dynamicMessageBubbleStyle"
  | "dynamicMessageTextStyle"
  | "filaOfflineOrdenada"
  | "fontScale"
  | "headerSafeTopInset"
  | "historicoAgrupadoFinal"
  | "historicoVazioTexto"
  | "historicoVazioTitulo"
  | "keyboardAvoidingBehavior"
  | "keyboardVisible"
  | "laudoSelecionadoId"
  | "mesaAcessoPermitido"
  | "loginKeyboardBottomPadding"
  | "loginKeyboardVerticalOffset"
  | "mesaDisponivel"
  | "mesaIndisponivelDescricao"
  | "mesaIndisponivelTitulo"
  | "mesaTemMensagens"
  | "mensagensVisiveis"
  | "nomeUsuarioExibicao"
  | "notificacoesNaoLidas"
  | "placeholderComposer"
  | "placeholderMesa"
  | "podeAbrirAnexosChat"
  | "podeAbrirAnexosMesa"
  | "podeAcionarComposer"
  | "podeEnviarComposer"
  | "podeEnviarMesa"
  | "podeUsarComposerMesa"
  | "threadKeyboardPaddingBottom"
  | "vendoFinalizacao"
  | "vendoMesa"
>;

type InspectorThreadContextState = Pick<
  ThreadContextStateResult,
  | "chipsContextoThread"
  | "laudoContextDescription"
  | "threadContextLayout"
  | "laudoContextTitle"
  | "mostrarContextoThread"
  | "threadActions"
  | "threadInsights"
  | "threadSpotlight"
>;

interface BuildInspectorAuthenticatedLayoutScreenPropsInput {
  baseState: InspectorAuthenticatedBaseState;
  composerState: Pick<
    AuthenticatedLayoutComposerInput,
    | "anexoAbrindoChave"
    | "anexoMesaRascunho"
    | "anexoRascunho"
    | "carregandoConversa"
    | "carregandoMesa"
    | "enviandoMensagem"
    | "enviandoMesa"
    | "erroMesa"
    | "handleAbrirQualityGate"
    | "handleAbrirSeletorAnexo"
    | "handleConfirmarQualityGate"
    | "handleEnviarMensagem"
    | "handleEnviarMensagemMesa"
    | "handleFecharQualityGate"
    | "handleReabrir"
    | "limparReferenciaMesaAtiva"
    | "mensagem"
    | "mensagemMesa"
    | "mensagemMesaReferenciaAtiva"
    | "qualityGateLoading"
    | "qualityGateNotice"
    | "qualityGatePayload"
    | "qualityGateReason"
    | "qualityGateSubmitting"
    | "qualityGateVisible"
    | "setAnexoMesaRascunho"
    | "setAnexoRascunho"
    | "setMensagem"
    | "setMensagemMesa"
    | "setQualityGateReason"
  >;
  historyState: Pick<
    AuthenticatedLayoutHistoryInput,
    | "buscaHistorico"
    | "fecharHistorico"
    | "handleAbrirHistorico"
    | "handleExcluirConversaHistorico"
    | "handleSelecionarHistorico"
    | "historicoAberto"
    | "historicoDrawerX"
    | "historyDrawerPanResponder"
    | "historyEdgePanResponder"
    | "setHistorySearchFocused"
    | "setBuscaHistorico"
  >;
  sessionState: Pick<
    AuthenticatedLayoutSessionInput,
    "scrollRef" | "setAbaAtiva"
  > & {
    sessionAccessToken: string;
  };
  shellState: Pick<
    AuthenticatedLayoutShellInput,
    | "animacoesAtivas"
    | "composerNotice"
    | "configuracoesAberta"
    | "drawerOverlayOpacity"
    | "erroConversa"
    | "erroLaudos"
    | "fecharPaineisLaterais"
    | "introVisivel"
    | "onVoiceInputPress"
    | "sessionModalsStackProps"
    | "statusApi"
    | "setIntroVisivel"
    | "settingsDrawerPanelProps"
    | "settingsEdgePanResponder"
  >;
  speechState: {
    entradaPorVoz: boolean;
    microfonePermitido: boolean;
    speechEnabled: boolean;
  };
  threadContextState: InspectorThreadContextState;
  threadState: Pick<
    AuthenticatedLayoutThreadInput,
    | "abrirReferenciaNoChat"
    | "chaveAnexo"
    | "definirReferenciaMesaAtiva"
    | "handleAbrirAnexo"
    | "handleAbrirConfiguracoes"
    | "handleAbrirNovoChat"
    | "handleExecutarComandoRevisaoMobile"
    | "handleUsarPerguntaPreLaudo"
    | "guidedTemplatesVisible"
    | "mensagemChatDestacadaId"
    | "mensagensMesa"
    | "notificacoesMesaLaudoAtual"
    | "obterResumoReferenciaMensagem"
    | "onGuidedTemplatesVisibleChange"
    | "registrarLayoutMensagemChat"
  >;
}

interface BuildInspectorLoginScreenPropsInput {
  authActions: Pick<
    BuildLoginScreenPropsInput,
    "handleEsqueciSenha" | "handleLogin" | "handleLoginSocial"
  >;
  authState: Pick<
    BuildLoginScreenPropsInput,
    | "carregando"
    | "email"
    | "emailInputRef"
    | "entrando"
    | "erro"
    | "loginStage"
    | "mostrarSenha"
    | "senha"
    | "senhaInputRef"
    | "statusApi"
  > & {
    setEmail: Dispatch<SetStateAction<string>>;
    setMostrarSenha: Dispatch<SetStateAction<boolean>>;
    setSenha: Dispatch<SetStateAction<string>>;
  };
  baseState: Pick<
    InspectorBaseDerivedState,
    | "accentColor"
    | "appGradientColors"
    | "fontScale"
    | "keyboardAvoidingBehavior"
    | "keyboardVisible"
    | "loginKeyboardBottomPadding"
    | "loginKeyboardVerticalOffset"
  >;
  presentationState: {
    animacoesAtivas: boolean;
    automationDiagnosticsEnabled: boolean;
    introVisivel: boolean;
  };
  setIntroVisivel: Dispatch<SetStateAction<boolean>>;
}

export function buildInspectorAuthenticatedLayoutScreenProps({
  baseState,
  composerState,
  historyState,
  sessionState,
  shellState,
  speechState,
  threadContextState,
  threadState,
}: BuildInspectorAuthenticatedLayoutScreenPropsInput): ComponentProps<
  typeof InspectorAuthenticatedLayout
> {
  return buildAuthenticatedLayoutProps(
    buildAuthenticatedLayoutInput({
      shell: {
        accentColor: baseState.accentColor,
        animacoesAtivas: shellState.animacoesAtivas,
        appGradientColors: baseState.appGradientColors,
        chatKeyboardVerticalOffset: baseState.chatKeyboardVerticalOffset,
        composerNotice: shellState.composerNotice,
        configuracoesAberta: shellState.configuracoesAberta,
        drawerOverlayOpacity: shellState.drawerOverlayOpacity,
        erroConversa: shellState.erroConversa,
        erroLaudos: shellState.erroLaudos,
        fecharPaineisLaterais: shellState.fecharPaineisLaterais,
        introVisivel: shellState.introVisivel,
        keyboardAvoidingBehavior: baseState.keyboardAvoidingBehavior,
        keyboardVisible: baseState.keyboardVisible,
        onVoiceInputPress: shellState.onVoiceInputPress,
        sessionModalsStackProps: shellState.sessionModalsStackProps,
        statusApi: shellState.statusApi,
        setIntroVisivel: shellState.setIntroVisivel,
        settingsDrawerPanelProps: shellState.settingsDrawerPanelProps,
        settingsEdgePanResponder: shellState.settingsEdgePanResponder,
        vendoFinalizacao: baseState.vendoFinalizacao,
        vendoMesa: baseState.vendoMesa,
      },
      history: {
        buscaHistorico: historyState.buscaHistorico,
        conversasOcultasTotal: baseState.conversasOcultasTotal,
        fecharHistorico: historyState.fecharHistorico,
        handleAbrirHistorico: historyState.handleAbrirHistorico,
        handleExcluirConversaHistorico:
          historyState.handleExcluirConversaHistorico,
        handleSelecionarHistorico: historyState.handleSelecionarHistorico,
        historicoAberto: historyState.historicoAberto,
        historicoAgrupadoFinal: baseState.historicoAgrupadoFinal,
        historicoDrawerX: historyState.historicoDrawerX,
        historicoVazioTexto: baseState.historicoVazioTexto,
        historicoVazioTitulo: baseState.historicoVazioTitulo,
        historyDrawerPanResponder: historyState.historyDrawerPanResponder,
        historyEdgePanResponder: historyState.historyEdgePanResponder,
        laudoSelecionadoId: baseState.laudoSelecionadoId,
        setHistorySearchFocused: historyState.setHistorySearchFocused,
        setBuscaHistorico: historyState.setBuscaHistorico,
      },
      thread: {
        abrirReferenciaNoChat: threadState.abrirReferenciaNoChat,
        chaveAnexo: threadState.chaveAnexo,
        chipsContextoThread: threadContextState.chipsContextoThread,
        conversaAtiva: baseState.conversaAtiva,
        conversaVazia: baseState.conversaVazia,
        definirReferenciaMesaAtiva: threadState.definirReferenciaMesaAtiva,
        dynamicMessageBubbleStyle: baseState.dynamicMessageBubbleStyle,
        dynamicMessageTextStyle: baseState.dynamicMessageTextStyle,
        filaOfflineOrdenada: baseState.filaOfflineOrdenada,
        handleAbrirAnexo: threadState.handleAbrirAnexo,
        handleAbrirConfiguracoes: threadState.handleAbrirConfiguracoes,
        handleAbrirNovoChat: threadState.handleAbrirNovoChat,
        handleExecutarComandoRevisaoMobile:
          threadState.handleExecutarComandoRevisaoMobile,
        handleUsarPerguntaPreLaudo: threadState.handleUsarPerguntaPreLaudo,
        guidedTemplatesVisible: threadState.guidedTemplatesVisible,
        headerSafeTopInset: baseState.headerSafeTopInset,
        laudoContextDescription: threadContextState.laudoContextDescription,
        threadContextLayout: threadContextState.threadContextLayout,
        laudoContextTitle: threadContextState.laudoContextTitle,
        mesaAcessoPermitido: baseState.mesaAcessoPermitido,
        mesaDisponivel: baseState.mesaDisponivel,
        mesaIndisponivelDescricao: baseState.mesaIndisponivelDescricao,
        mesaIndisponivelTitulo: baseState.mesaIndisponivelTitulo,
        mesaTemMensagens: baseState.mesaTemMensagens,
        mensagemChatDestacadaId: threadState.mensagemChatDestacadaId,
        mensagensMesa: threadState.mensagensMesa,
        mensagensVisiveis: baseState.mensagensVisiveis,
        mostrarContextoThread: threadContextState.mostrarContextoThread,
        nomeUsuarioExibicao: baseState.nomeUsuarioExibicao,
        notificacoesMesaLaudoAtual: threadState.notificacoesMesaLaudoAtual,
        notificacoesNaoLidas: baseState.notificacoesNaoLidas,
        onGuidedTemplatesVisibleChange:
          threadState.onGuidedTemplatesVisibleChange,
        obterResumoReferenciaMensagem:
          threadState.obterResumoReferenciaMensagem,
        registrarLayoutMensagemChat: threadState.registrarLayoutMensagemChat,
        threadActions: threadContextState.threadActions,
        threadInsights: threadContextState.threadInsights,
        threadKeyboardPaddingBottom: baseState.threadKeyboardPaddingBottom,
        threadSpotlight: threadContextState.threadSpotlight,
        vendoFinalizacao: baseState.vendoFinalizacao,
      },
      composer: {
        anexoAbrindoChave: composerState.anexoAbrindoChave,
        anexoMesaRascunho: composerState.anexoMesaRascunho,
        anexoRascunho: composerState.anexoRascunho,
        carregandoConversa: composerState.carregandoConversa,
        carregandoMesa: composerState.carregandoMesa,
        dynamicComposerInputStyle: baseState.dynamicComposerInputStyle,
        enviandoMensagem: composerState.enviandoMensagem,
        enviandoMesa: composerState.enviandoMesa,
        erroMesa: composerState.erroMesa,
        handleAbrirQualityGate: composerState.handleAbrirQualityGate,
        handleAbrirSeletorAnexo: composerState.handleAbrirSeletorAnexo,
        handleConfirmarQualityGate: composerState.handleConfirmarQualityGate,
        handleEnviarMensagem: composerState.handleEnviarMensagem,
        handleEnviarMensagemMesa: composerState.handleEnviarMensagemMesa,
        handleFecharQualityGate: composerState.handleFecharQualityGate,
        handleReabrir: composerState.handleReabrir,
        limparReferenciaMesaAtiva: composerState.limparReferenciaMesaAtiva,
        mensagem: composerState.mensagem,
        mensagemMesa: composerState.mensagemMesa,
        mensagemMesaReferenciaAtiva: composerState.mensagemMesaReferenciaAtiva,
        placeholderComposer: baseState.placeholderComposer,
        placeholderMesa: baseState.placeholderMesa,
        podeAbrirAnexosChat: baseState.podeAbrirAnexosChat,
        podeAbrirAnexosMesa: baseState.podeAbrirAnexosMesa,
        podeAcionarComposer: baseState.podeAcionarComposer,
        podeEnviarComposer: baseState.podeEnviarComposer,
        podeEnviarMesa: baseState.podeEnviarMesa,
        podeUsarComposerMesa: baseState.podeUsarComposerMesa,
        qualityGateLoading: composerState.qualityGateLoading,
        qualityGateNotice: composerState.qualityGateNotice,
        qualityGatePayload: composerState.qualityGatePayload,
        qualityGateReason: composerState.qualityGateReason,
        qualityGateSubmitting: composerState.qualityGateSubmitting,
        qualityGateVisible: composerState.qualityGateVisible,
        setAnexoMesaRascunho: composerState.setAnexoMesaRascunho,
        setAnexoRascunho: composerState.setAnexoRascunho,
        setMensagem: composerState.setMensagem,
        setMensagemMesa: composerState.setMensagemMesa,
        setQualityGateReason: composerState.setQualityGateReason,
        showVoiceInputAction:
          speechState.speechEnabled && speechState.entradaPorVoz,
        voiceInputEnabled:
          speechState.speechEnabled &&
          speechState.entradaPorVoz &&
          speechState.microfonePermitido,
      },
      session: {
        scrollRef: sessionState.scrollRef,
        sessionAccessToken: sessionState.sessionAccessToken,
        setAbaAtiva: sessionState.setAbaAtiva,
      },
    }),
  );
}

export function buildInspectorLoginScreenProps({
  authActions,
  authState,
  baseState,
  presentationState,
  setIntroVisivel,
}: BuildInspectorLoginScreenPropsInput): ComponentProps<typeof LoginScreen> {
  return buildLoginScreenProps({
    accentColor: baseState.accentColor,
    animacoesAtivas: presentationState.animacoesAtivas,
    automationDiagnosticsEnabled:
      presentationState.automationDiagnosticsEnabled,
    appGradientColors: baseState.appGradientColors,
    carregando: authState.carregando,
    email: authState.email,
    emailInputRef: authState.emailInputRef,
    entrando: authState.entrando,
    erro: authState.erro,
    fontScale: baseState.fontScale,
    handleEsqueciSenha: authActions.handleEsqueciSenha,
    handleLogin: authActions.handleLogin,
    handleLoginSocial: authActions.handleLoginSocial,
    introVisivel: presentationState.introVisivel,
    keyboardAvoidingBehavior: baseState.keyboardAvoidingBehavior,
    keyboardVisible: baseState.keyboardVisible,
    loginStage: authState.loginStage,
    loginKeyboardBottomPadding: baseState.loginKeyboardBottomPadding,
    loginKeyboardVerticalOffset: baseState.loginKeyboardVerticalOffset,
    mostrarSenha: authState.mostrarSenha,
    senha: authState.senha,
    senhaInputRef: authState.senhaInputRef,
    statusApi: authState.statusApi,
    setEmail: authState.setEmail,
    setIntroVisivel,
    setMostrarSenha: authState.setMostrarSenha,
    setSenha: authState.setSenha,
  });
}
