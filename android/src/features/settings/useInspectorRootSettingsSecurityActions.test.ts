import { renderHook } from "@testing-library/react-native";

const mockHandleToggle2FA = jest.fn();
const mockHandleEncerrarSessaoAtual = jest.fn();

jest.mock("./useSettingsSecurityActions", () => ({
  useSettingsSecurityActions: jest.fn(() => ({
    handleAbrirAjustesDoSistema: jest.fn(),
    handleCompartilharCodigosRecuperacao: jest.fn(),
    handleConectarProximoProvedorDisponivel: jest.fn(),
    handleConfirmarCodigo2FA: jest.fn(),
    handleEncerrarOutrasSessoes: jest.fn(),
    handleEncerrarSessao: jest.fn(),
    handleEncerrarSessaoAtual: mockHandleEncerrarSessaoAtual,
    handleEncerrarSessoesSuspeitas: jest.fn(),
    handleGerarCodigosRecuperacao: jest.fn(),
    handleMudarMetodo2FA: jest.fn(),
    handleReautenticacaoSensivel: jest.fn(),
    handleRevisarSessao: jest.fn(),
    handleToggle2FA: mockHandleToggle2FA,
    handleToggleBiometriaNoDispositivo: jest.fn(),
    handleToggleProviderConnection: jest.fn(),
  })),
}));

import { useSettingsSecurityActions } from "./useSettingsSecurityActions";
import { useInspectorRootSettingsSecurityActions } from "./useInspectorRootSettingsSecurityActions";

function criarInput() {
  return {
    accountState: {
      emailAtualConta: "inspetor@tariel.test",
      fallbackEmail: "fallback@tariel.test",
    },
    actionState: {
      abrirConfirmacaoConfiguracao: jest.fn(),
      abrirFluxoReautenticacao: jest.fn(),
      abrirSheetConfiguracao: jest.fn(),
      compartilharTextoExportado: jest.fn().mockResolvedValue(true),
      executarComReautenticacao: jest.fn(),
      fecharConfiguracoes: jest.fn(),
      handleLogout: jest.fn(),
      openSystemSettings: jest.fn(),
      registrarEventoSegurancaLocal: jest.fn(),
      reautenticacaoAindaValida: jest.fn().mockReturnValue(true),
      showAlert: jest.fn(),
    },
    authState: {
      biometriaLocalSuportada: true,
      biometriaPermitida: true,
      codigo2FA: "",
      codigosRecuperacao: [],
      reautenticacaoExpiraEm: "",
      requireAuthOnOpen: false,
      twoFactorEnabled: true,
      twoFactorMethod: "App autenticador" as const,
    },
    collectionState: {
      provedoresConectados: [],
      sessoesAtivas: [],
    },
    setterState: {
      setCodigo2FA: jest.fn(),
      setCodigosRecuperacao: jest.fn(),
      setDeviceBiometricsEnabled: jest.fn(),
      setProvedoresConectados: jest.fn(),
      setRequireAuthOnOpen: jest.fn(),
      setSessoesAtivas: jest.fn(),
      setSettingsSheetNotice: jest.fn(),
      setTwoFactorEnabled: jest.fn(),
      setTwoFactorMethod: jest.fn(),
    },
  };
}

describe("useInspectorRootSettingsSecurityActions", () => {
  it("encapsula a composição do trilho de segurança sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() =>
      useInspectorRootSettingsSecurityActions(input),
    );
    const mockedHook = jest.mocked(useSettingsSecurityActions);

    result.current.handleToggle2FA();
    result.current.handleEncerrarSessaoAtual();

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        emailAtualConta: input.accountState.emailAtualConta,
        twoFactorEnabled: input.authState.twoFactorEnabled,
        provedoresConectados: input.collectionState.provedoresConectados,
        setSessoesAtivas: input.setterState.setSessoesAtivas,
      }),
    );
    expect(mockHandleToggle2FA).toHaveBeenCalledTimes(1);
    expect(mockHandleEncerrarSessaoAtual).toHaveBeenCalledTimes(1);
  });
});
