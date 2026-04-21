import { renderHook } from "@testing-library/react-native";

const mockHandleAbrirHistorico = jest.fn();
const mockHandleSelecionarHistorico = jest.fn();

jest.mock("./useHistoryController", () => ({
  useHistoryController: jest.fn(() => ({
    handleAbrirHistorico: mockHandleAbrirHistorico,
    handleGerenciarConversasIndividuais: jest.fn(),
    handleAlternarFixadoHistorico: jest.fn(),
    handleExcluirConversaHistorico: jest.fn(),
    handleSelecionarHistorico: mockHandleSelecionarHistorico,
  })),
}));

import { useHistoryController } from "./useHistoryController";
import { useInspectorRootHistoryController } from "./useInspectorRootHistoryController";

function criarInput() {
  return {
    state: {
      conversaAtualLaudoId: null,
      historicoAberto: false,
      historicoAbertoRefAtual: false,
      historicoOcultoIds: [],
      keyboardHeight: 0,
      laudosFixadosIds: [],
      pendingHistoryThreadRoute: null,
    },
    actionState: {
      abrirHistorico: jest.fn(),
      fecharConfiguracoes: jest.fn(),
      fecharHistorico: jest.fn(),
      handleSelecionarLaudo: jest.fn().mockResolvedValue(undefined),
      onCreateNewConversation: jest.fn(),
      onDismissKeyboard: jest.fn(),
      onGetCacheKeyForLaudo: jest.fn((id) => String(id ?? "")),
      onSchedule: jest.fn((callback: () => void) => callback()),
    },
    setterState: {
      setAbaAtiva: jest.fn(),
      setAnexoMesaRascunho: jest.fn(),
      setAnexoRascunho: jest.fn(),
      setCacheLeitura: jest.fn(),
      setConversa: jest.fn(),
      setErroConversa: jest.fn(),
      setErroMesa: jest.fn(),
      setHistoricoOcultoIds: jest.fn(),
      setLaudoMesaCarregado: jest.fn(),
      setLaudosDisponiveis: jest.fn(),
      setLaudosFixadosIds: jest.fn(),
      setMensagem: jest.fn(),
      setMensagemMesa: jest.fn(),
      setMensagensMesa: jest.fn(),
      setNotificacoes: jest.fn(),
      setPendingHistoryThreadRoute: jest.fn(),
      setThreadRouteHistory: jest.fn(),
    },
  };
}

describe("useInspectorRootHistoryController", () => {
  it("encapsula a composição do trilho de histórico sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() =>
      useInspectorRootHistoryController(input),
    );
    const mockedHook = jest.mocked(useHistoryController);

    result.current.handleAbrirHistorico();
    result.current.handleSelecionarHistorico(null);

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        keyboardHeight: input.state.keyboardHeight,
        abrirHistorico: input.actionState.abrirHistorico,
        setConversa: input.setterState.setConversa,
      }),
    );
    expect(mockHandleAbrirHistorico).toHaveBeenCalledTimes(1);
    expect(mockHandleSelecionarHistorico).toHaveBeenCalledWith(null);
  });
});
