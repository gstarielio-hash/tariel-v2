import { renderHook } from "@testing-library/react-native";

const mockAbrirFluxoReautenticacao = jest.fn();
const mockHandleExcluirConta = jest.fn();

jest.mock("./useSettingsReauthActions", () => ({
  useSettingsReauthActions: jest.fn(() => ({
    abrirFluxoReautenticacao: mockAbrirFluxoReautenticacao,
    clearPendingSensitiveAction: jest.fn(),
    executarComReautenticacao: jest.fn(),
    handleConfirmarSettingsSheetReauth: jest.fn(),
    handleExcluirConta: mockHandleExcluirConta,
  })),
}));

import { useSettingsReauthActions } from "./useSettingsReauthActions";
import { useInspectorRootSettingsReauthActions } from "./useInspectorRootSettingsReauthActions";

function criarInput() {
  return {
    actionState: {
      abrirConfirmacaoConfiguracao: jest.fn(),
      abrirSheetConfiguracao: jest.fn(),
      fecharSheetConfiguracao: jest.fn(),
      notificarConfiguracaoConcluida: jest.fn(),
      registrarEventoSegurancaLocal: jest.fn(),
      reautenticacaoAindaValida: jest.fn().mockReturnValue(true),
    },
    draftState: {
      reautenticacaoExpiraEm: "",
      settingsSheet: null,
    },
    setterState: {
      setReauthReason: jest.fn(),
      setReautenticacaoExpiraEm: jest.fn(),
      setReautenticacaoStatus: jest.fn(),
      setSettingsSheetLoading: jest.fn(),
      setSettingsSheetNotice: jest.fn(),
    },
  };
}

describe("useInspectorRootSettingsReauthActions", () => {
  it("encapsula a composição do trilho de reautenticação sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() =>
      useInspectorRootSettingsReauthActions(input),
    );
    const mockedHook = jest.mocked(useSettingsReauthActions);

    result.current.abrirFluxoReautenticacao("Confirmar");
    result.current.handleExcluirConta();

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        abrirSheetConfiguracao: input.actionState.abrirSheetConfiguracao,
        reautenticacaoExpiraEm: input.draftState.reautenticacaoExpiraEm,
        setSettingsSheetNotice: input.setterState.setSettingsSheetNotice,
      }),
    );
    expect(mockAbrirFluxoReautenticacao).toHaveBeenCalledWith("Confirmar");
    expect(mockHandleExcluirConta).toHaveBeenCalledTimes(1);
  });
});
