import { renderHook } from "@testing-library/react-native";

const mockCarregarMesaAtual = jest.fn();
const mockResetMesaState = jest.fn();

jest.mock("./useMesaController", () => ({
  useMesaController: jest.fn(() => ({
    actions: {
      carregarMesaAtual: mockCarregarMesaAtual,
      definirReferenciaMesaAtiva: jest.fn(),
      handleExecutarComandoRevisaoMobile: jest.fn(),
      handleEnviarMensagemMesa: jest.fn(),
      limparReferenciaMesaAtiva: jest.fn(),
      resetMesaState: mockResetMesaState,
    },
  })),
}));

import { useMesaController } from "./useMesaController";
import { useInspectorRootMesaController } from "./useInspectorRootMesaController";

function criarInput() {
  return {
    state: {
      activeThread: "mesa" as const,
      attachmentDraft: null,
      conversation: null,
      laudoMesaCarregado: null,
      messageMesa: "",
      messagesMesa: [],
      session: null,
      statusApi: "online",
      wifiOnlySync: false,
    },
    refState: {
      carregarListaLaudosRef: {
        current: jest.fn().mockResolvedValue([]),
      },
      scrollRef: {
        current: null,
      },
    },
    cacheState: {
      cacheLeitura: {
        bootstrap: null,
        laudos: [],
        conversaAtual: null,
        conversasPorLaudo: {},
        mesaPorLaudo: {},
        chatDrafts: {},
        mesaDrafts: {},
        chatAttachmentDrafts: {},
        mesaAttachmentDrafts: {},
        updatedAt: "",
      },
      chaveCacheLaudo: jest.fn().mockReturnValue("laudo:1"),
      chaveRascunho: jest.fn().mockReturnValue("mesa:1"),
      textoFallbackAnexo: jest.fn().mockReturnValue("Anexo"),
    },
    actionState: {
      activeReference: null,
      atualizarResumoLaudoAtual: jest.fn((estado) => estado),
      criarItemFilaOffline: jest.fn(),
      erroSugereModoOffline: jest.fn().mockReturnValue(false),
      onObserveMesaThreadReadMetadata: jest.fn(),
    },
    setterState: {
      setActiveReference: jest.fn(),
      setAttachmentDraft: jest.fn(),
      setCacheLeitura: jest.fn(),
      setConversation: jest.fn(),
      setErrorMesa: jest.fn(),
      setFilaOffline: jest.fn(),
      setLaudoMesaCarregado: jest.fn(),
      setLoadingMesa: jest.fn(),
      setMessageMesa: jest.fn(),
      setMessagesMesa: jest.fn(),
      setSendingMesa: jest.fn(),
      setStatusApi: jest.fn(),
      setSyncMesa: jest.fn(),
      setUsandoCacheOffline: jest.fn(),
    },
  };
}

describe("useInspectorRootMesaController", () => {
  it("encapsula a composição da mesa sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() => useInspectorRootMesaController(input));
    const mockedHook = jest.mocked(useMesaController);

    result.current.actions.carregarMesaAtual("token-1", 99, true);
    result.current.actions.resetMesaState();

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        activeThread: input.state.activeThread,
        cacheLeitura: input.cacheState.cacheLeitura,
        scrollRef: input.refState.scrollRef,
        setMessagesMesa: input.setterState.setMessagesMesa,
      }),
    );
    expect(mockCarregarMesaAtual).toHaveBeenCalledWith("token-1", 99, true);
    expect(mockResetMesaState).toHaveBeenCalledTimes(1);
  });
});
