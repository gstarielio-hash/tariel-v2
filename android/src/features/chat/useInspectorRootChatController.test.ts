import { renderHook } from "@testing-library/react-native";

const mockAbrirLaudoPorId = jest.fn();
const mockHandleAbrirNovoChat = jest.fn();
const mockHandleIniciarChatLivre = jest.fn();

jest.mock("./useInspectorChatController", () => ({
  useInspectorChatController: jest.fn(() => ({
    actions: {
      abrirLaudoPorId: mockAbrirLaudoPorId,
      abrirReferenciaNoChat: jest.fn(),
      carregarConversaAtual: jest.fn(),
      carregarListaLaudos: jest.fn(),
      handleAbrirColetaGuiadaAtual: jest.fn(),
      handleAbrirNovoChat: mockHandleAbrirNovoChat,
      handleIniciarChatLivre: mockHandleIniciarChatLivre,
      handleEnviarMensagem: jest.fn(),
      handleReabrir: jest.fn(),
      handleSelecionarLaudo: jest.fn(),
      registrarLayoutMensagemChat: jest.fn(),
      resetChatState: jest.fn(),
    },
  })),
}));

import { useInspectorChatController } from "./useInspectorChatController";
import { useInspectorRootChatController } from "./useInspectorRootChatController";

function criarInput() {
  return {
    sessionState: {
      activeThread: "chat" as const,
      aiRequestConfig: {
        model: "equilibrado" as const,
        mode: "detalhado" as const,
        responseStyle: "padrão" as const,
        responseLanguage: "Português" as const,
        memoryEnabled: true,
        learningOptIn: false,
        tone: "profissional" as const,
        temperature: 0.4,
        messagePrefix: "",
        summaryLabel: "IA equilibrada",
        fallbackNotes: [],
      },
      entryModePreference: "auto_recommended" as const,
      rememberLastCaseMode: false,
      session: null,
      sessionLoading: false,
      speechSettings: {
        enabled: false,
        autoTranscribe: false,
        autoReadResponses: false,
        voiceLanguage: "Português" as const,
        speechRate: 1,
        voiceId: "",
      },
      statusApi: "online",
      wifiOnlySync: false,
    },
    conversationState: {
      attachmentDraft: null,
      cacheLeitura: {
        bootstrap: null,
        laudos: [],
        conversaAtual: null,
        conversasPorLaudo: {},
        mesaPorLaudo: {},
        guidedInspectionDrafts: {},
        chatDrafts: {},
        mesaDrafts: {},
        chatAttachmentDrafts: {},
        mesaAttachmentDrafts: {},
        updatedAt: "",
      },
      conversation: null,
      guidedInspectionDraft: null,
      highlightedMessageId: null,
      historicoOcultoIds: [],
      laudoMesaCarregado: null,
      laudosDisponiveis: [],
      laudosFixadosIds: [],
      layoutVersion: 0,
      message: "",
      qualityGateLaudoId: null,
      qualityGatePayload: null,
      qualityGateReason: "",
      scrollRef: {
        current: null,
      },
      threadHomeVisible: true,
    },
    mesaState: {
      carregarMesaAtual: jest.fn().mockResolvedValue(undefined),
      clearGuidedInspectionDraft: jest.fn(),
      clearMesaReference: jest.fn(),
      setAnexoMesaRascunho: jest.fn(),
      setErroMesa: jest.fn(),
      setLaudoMesaCarregado: jest.fn(),
      setMensagemMesa: jest.fn(),
      setMensagensMesa: jest.fn(),
      startGuidedInspection: jest.fn(),
    },
    setterState: {
      onSetActiveThread: jest.fn(),
      setAttachmentDraft: jest.fn(),
      setCacheLeitura: jest.fn(),
      setCaseCreationState: jest.fn(),
      setConversation: jest.fn(),
      setErrorConversation: jest.fn(),
      setErrorLaudos: jest.fn(),
      setFilaOffline: jest.fn(),
      setHighlightedMessageId: jest.fn(),
      setLaudosDisponiveis: jest.fn(),
      setLayoutVersion: jest.fn(),
      setLoadingConversation: jest.fn(),
      setLoadingLaudos: jest.fn(),
      setMessage: jest.fn(),
      setQualityGateLaudoId: jest.fn(),
      setQualityGateLoading: jest.fn(),
      setQualityGateNotice: jest.fn(),
      setQualityGatePayload: jest.fn(),
      setQualityGateReason: jest.fn(),
      setQualityGateSubmitting: jest.fn(),
      setQualityGateVisible: jest.fn(),
      setSendingMessage: jest.fn(),
      setStatusApi: jest.fn(),
      setSyncConversation: jest.fn(),
      setThreadHomeVisible: jest.fn(),
      setUsandoCacheOffline: jest.fn(),
    },
    actionState: {
      aplicarPreferenciasLaudos: jest.fn((itens) => itens),
      atualizarResumoLaudoAtual: jest.fn((estado) => estado),
      chaveCacheLaudo: jest.fn().mockReturnValue("laudo:1"),
      chaveRascunho: jest.fn().mockReturnValue("chat:1"),
      criarConversaNova: jest.fn().mockReturnValue({
        laudoId: null,
        estado: "sem_relatorio",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: null,
        modo: "detalhado",
        mensagens: [],
      }),
      criarItemFilaOffline: jest.fn(),
      criarMensagemAssistenteServidor: jest.fn().mockReturnValue(null),
      erroSugereModoOffline: jest.fn().mockReturnValue(false),
      inferirSetorConversa: jest.fn().mockReturnValue("geral"),
      montarHistoricoParaEnvio: jest.fn().mockReturnValue([]),
      normalizarConversa: jest.fn(),
      normalizarModoChat: jest.fn().mockReturnValue("detalhado"),
      podeEditarConversaNoComposer: jest.fn().mockReturnValue(true),
      textoFallbackAnexo: jest.fn().mockReturnValue("Anexo"),
    },
  };
}

describe("useInspectorRootChatController", () => {
  it("encapsula a composição do chat sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() => useInspectorRootChatController(input));
    const mockedHook = jest.mocked(useInspectorChatController);

    result.current.actions.abrirLaudoPorId("token-1", 88);
    result.current.actions.handleAbrirNovoChat();
    result.current.actions.handleIniciarChatLivre();

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        activeThread: input.sessionState.activeThread,
        cacheLeitura: input.conversationState.cacheLeitura,
        carregarMesaAtual: input.mesaState.carregarMesaAtual,
        setConversation: input.setterState.setConversation,
      }),
    );
    expect(mockAbrirLaudoPorId).toHaveBeenCalledWith("token-1", 88);
    expect(mockHandleAbrirNovoChat).toHaveBeenCalledTimes(1);
    expect(mockHandleIniciarChatLivre).toHaveBeenCalledTimes(1);
  });
});
