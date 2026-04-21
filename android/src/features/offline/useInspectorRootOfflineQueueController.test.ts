import { renderHook } from "@testing-library/react-native";

const mockSincronizarFilaOffline = jest.fn();
const mockRemoverItemFilaOffline = jest.fn();

jest.mock("./useOfflineQueueController", () => ({
  useOfflineQueueController: jest.fn(() => ({
    actions: {
      handleRetomarItemFilaOffline: jest.fn(),
      removerItemFilaOffline: mockRemoverItemFilaOffline,
      sincronizarFilaOffline: mockSincronizarFilaOffline,
      sincronizarItemFilaOffline: jest.fn(),
    },
  })),
}));

import { useOfflineQueueController } from "./useOfflineQueueController";
import { useInspectorRootOfflineQueueController } from "./useInspectorRootOfflineQueueController";

function criarInput() {
  return {
    state: {
      activeThread: "chat" as const,
      conversation: null,
      messagesMesa: [],
      offlineQueue: [],
      session: null,
      sessionLoading: false,
      statusApi: "online",
      syncEnabled: true,
      syncingItemId: "",
      syncingQueue: false,
      wifiOnlySync: false,
    },
    actionState: {
      abrirLaudoPorId: jest.fn().mockResolvedValue(undefined),
      carregarConversaAtual: jest.fn().mockResolvedValue(null),
      carregarListaLaudos: jest.fn().mockResolvedValue([]),
      carregarMesaAtual: jest.fn().mockResolvedValue(undefined),
      duplicarComposerAttachment: jest.fn((item) => item),
      erroSugereModoOffline: jest.fn().mockReturnValue(false),
      handleSelecionarLaudo: jest.fn().mockResolvedValue(undefined),
      inferirSetorConversa: jest.fn().mockReturnValue("geral"),
      isItemReadyForRetry: jest.fn().mockReturnValue(true),
      montarHistoricoParaEnvio: jest.fn().mockReturnValue([]),
      normalizarModoChat: jest.fn().mockReturnValue("detalhado"),
      obterResumoReferenciaMensagem: jest.fn().mockReturnValue("Resumo"),
      restoreQualityGateFinalize: jest.fn().mockResolvedValue(undefined),
      saveQueueLocally: jest.fn().mockResolvedValue(undefined),
      calcularBackoffMs: jest.fn().mockReturnValue(30_000),
    },
    setterState: {
      setActiveThread: jest.fn(),
      setAttachmentDraft: jest.fn(),
      setAttachmentMesaDraft: jest.fn(),
      setErrorConversation: jest.fn(),
      setErrorMesa: jest.fn(),
      setMessage: jest.fn(),
      setMessageMesa: jest.fn(),
      setMesaActiveReference: jest.fn(),
      setOfflineQueue: jest.fn(),
      setOfflineQueueVisible: jest.fn(),
      setStatusApi: jest.fn(),
      setSyncingItemId: jest.fn(),
      setSyncingQueue: jest.fn(),
    },
  };
}

describe("useInspectorRootOfflineQueueController", () => {
  it("encapsula a composição da fila offline sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() =>
      useInspectorRootOfflineQueueController(input),
    );
    const mockedHook = jest.mocked(useOfflineQueueController);

    result.current.actions.sincronizarFilaOffline("token-123", true);
    result.current.actions.removerItemFilaOffline("offline-1");

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        activeThread: input.state.activeThread,
        carregarListaLaudos: input.actionState.carregarListaLaudos,
        setOfflineQueue: input.setterState.setOfflineQueue,
      }),
    );
    expect(mockSincronizarFilaOffline).toHaveBeenCalledWith("token-123", true);
    expect(mockRemoverItemFilaOffline).toHaveBeenCalledWith("offline-1");
  });
});
