import { renderHook } from "@testing-library/react-native";

const mockHandleLogin = jest.fn();
const mockHandleLogout = jest.fn();

jest.mock("./useInspectorSession", () => ({
  useInspectorSession: jest.fn(() => ({
    state: {
      email: "",
      senha: "",
      lembrar: true,
      mostrarSenha: false,
      statusApi: "online",
      erro: "",
      carregando: false,
      entrando: false,
      loginStage: "idle",
      session: null,
    },
    actions: {
      bootstrapApp: jest.fn(),
      handleLogin: mockHandleLogin,
      handleLogout: mockHandleLogout,
      setCarregando: jest.fn(),
      setEmail: jest.fn(),
      setEntrando: jest.fn(),
      setErro: jest.fn(),
      setLembrar: jest.fn(),
      setMostrarSenha: jest.fn(),
      setSenha: jest.fn(),
      setSession: jest.fn(),
      setStatusApi: jest.fn(),
    },
  })),
}));

import { useInspectorSession } from "./useInspectorSession";
import { useInspectorRootSession } from "./useInspectorRootSession";

function criarInput() {
  return {
    bootstrapState: {
      settingsHydrated: true,
      chatHistoryEnabled: true,
      deviceBackupEnabled: true,
      aplicarPreferenciasLaudos: jest.fn((items) => items),
      chaveCacheLaudo: jest.fn((id) => `laudo:${id ?? "rascunho"}`),
      erroSugereModoOffline: jest.fn().mockReturnValue(false),
      lerCacheLeituraLocal: jest.fn().mockResolvedValue(null),
      lerEstadoHistoricoLocal: jest.fn().mockResolvedValue({
        laudosFixadosIds: [],
        historicoOcultoIds: [],
      }),
      lerFilaOfflineLocal: jest.fn().mockResolvedValue([]),
      lerNotificacoesLocais: jest.fn().mockResolvedValue([]),
      limparCachePorPrivacidade: jest.fn((cache) => cache),
      cacheLeituraVazio: {
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
    },
    setterState: {
      onSetFilaOffline: jest.fn(),
      onSetNotificacoes: jest.fn(),
      onSetCacheLeitura: jest.fn(),
      onSetLaudosFixadosIds: jest.fn(),
      onSetHistoricoOcultoIds: jest.fn(),
      onSetUsandoCacheOffline: jest.fn(),
      onSetLaudosDisponiveis: jest.fn(),
      onSetConversa: jest.fn(),
      onSetMensagensMesa: jest.fn(),
      onSetLaudoMesaCarregado: jest.fn(),
      onSetErroLaudos: jest.fn(),
    },
    callbackState: {
      onApplyBootstrapCache: jest.fn(),
      onAfterLoginSuccess: jest.fn(),
      onResetAfterLogout: jest.fn(),
    },
  };
}

describe("useInspectorRootSession", () => {
  it("encapsula a composição do trilho de sessão sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() => useInspectorRootSession(input));
    const mockedHook = jest.mocked(useInspectorSession);

    result.current.actions.handleLogin();
    result.current.actions.handleLogout();

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        settingsHydrated: input.bootstrapState.settingsHydrated,
        onSetCacheLeitura: input.setterState.onSetCacheLeitura,
        onResetAfterLogout: input.callbackState.onResetAfterLogout,
      }),
    );
    expect(mockHandleLogin).toHaveBeenCalledTimes(1);
    expect(mockHandleLogout).toHaveBeenCalledTimes(1);
  });
});
