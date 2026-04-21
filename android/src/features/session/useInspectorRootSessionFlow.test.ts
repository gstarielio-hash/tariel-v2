import { act, renderHook } from "@testing-library/react-native";

jest.mock("../common/inspectorLocalPersistence", () => ({
  lerCacheLeituraLocal: jest.fn(),
  lerEstadoHistoricoLocal: jest.fn(),
  lerFilaOfflineLocal: jest.fn(),
  lerNotificacoesLocais: jest.fn(),
}));

jest.mock("./useInspectorRootSession", () => ({
  useInspectorRootSession: jest.fn(() => ({
    state: {
      carregando: false,
      email: "",
      entrando: false,
      erro: "",
      lembrar: true,
      mostrarSenha: false,
      senha: "",
      loginStage: "idle",
      session: null,
      statusApi: "online",
    },
    actions: {
      bootstrapApp: jest.fn(),
      handleLogin: jest.fn(),
      handleLogout: jest.fn(),
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

import {
  lerCacheLeituraLocal,
  lerEstadoHistoricoLocal,
  lerFilaOfflineLocal,
  lerNotificacoesLocais,
} from "../common/inspectorLocalPersistence";
import { useInspectorRootSession } from "./useInspectorRootSession";
import { useInspectorRootSessionFlow } from "./useInspectorRootSessionFlow";

function criarInput() {
  return {
    bootstrapState: {
      settingsHydrated: true,
      chatHistoryEnabled: true,
      deviceBackupEnabled: true,
      aplicarPreferenciasLaudos: jest.fn((items) => items),
      chaveCacheLaudo: jest.fn((id) => `laudo:${id ?? "rascunho"}`),
      erroSugereModoOffline: jest.fn().mockReturnValue(false),
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
      criarConversaNova: jest.fn(),
      normalizarComposerAttachment: jest.fn(),
      normalizarModoChat: jest.fn(),
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
    resetState: {
      onClearPendingSensitiveAction: jest.fn(),
      onResetSessionBoundSettingsPresentationState: jest.fn(),
      onResetSettingsUi: jest.fn(),
      onSetAbaAtiva: jest.fn(),
      onSetAnexoAbrindoChave: jest.fn(),
      onSetAnexoMesaRascunho: jest.fn(),
      onSetAnexoRascunho: jest.fn(),
      onSetBloqueioAppAtivo: jest.fn(),
      onSetErroMesa: jest.fn(),
      onSetGuidedInspectionDraft: jest.fn(),
      onSetMensagem: jest.fn(),
      onSetMensagemMesa: jest.fn(),
      onSetQualityGateLaudoId: jest.fn(),
      onSetQualityGateLoading: jest.fn(),
      onSetQualityGateNotice: jest.fn(),
      onSetQualityGatePayload: jest.fn(),
      onSetQualityGateReason: jest.fn(),
      onSetQualityGateSubmitting: jest.fn(),
      onSetQualityGateVisible: jest.fn(),
      onSetSincronizandoFilaOffline: jest.fn(),
      onSetSincronizandoItemFilaId: jest.fn(),
    },
  };
}

describe("useInspectorRootSessionFlow", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (lerCacheLeituraLocal as jest.Mock).mockResolvedValue("cache-local");
    (lerEstadoHistoricoLocal as jest.Mock).mockResolvedValue({
      laudosFixadosIds: [],
      historicoOcultoIds: [],
    });
    (lerFilaOfflineLocal as jest.Mock).mockResolvedValue("fila-local");
    (lerNotificacoesLocais as jest.Mock).mockResolvedValue(
      "notificacoes-locais",
    );
  });

  it("encapsula bootstrap readers e callbacks de merge/reset da sessão root", async () => {
    const input = criarInput();
    renderHook(() => useInspectorRootSessionFlow(input));
    const mockedHook = jest.mocked(useInspectorRootSession);
    const params = mockedHook.mock.calls[0][0];

    await act(async () => {
      await params.bootstrapState.lerCacheLeituraLocal("inspetor@tariel.test");
      await params.bootstrapState.lerFilaOfflineLocal("inspetor@tariel.test");
      await params.bootstrapState.lerEstadoHistoricoLocal();
      await params.bootstrapState.lerNotificacoesLocais("inspetor@tariel.test");
    });

    expect(lerCacheLeituraLocal).toHaveBeenCalledWith({
      cacheLeituraVazio: input.bootstrapState.cacheLeituraVazio,
      criarConversaNova: input.bootstrapState.criarConversaNova,
      expectedScope: { email: "inspetor@tariel.test" },
      normalizarComposerAttachment:
        input.bootstrapState.normalizarComposerAttachment,
    });
    expect(lerFilaOfflineLocal).toHaveBeenCalledWith({
      expectedScope: { email: "inspetor@tariel.test" },
      normalizarComposerAttachment:
        input.bootstrapState.normalizarComposerAttachment,
      normalizarModoChat: input.bootstrapState.normalizarModoChat,
    });
    expect(lerEstadoHistoricoLocal).toHaveBeenCalledTimes(1);
    expect(lerNotificacoesLocais).toHaveBeenCalledWith({
      expectedScope: { email: "inspetor@tariel.test" },
    });

    const bootstrap = { id: "bootstrap" } as any;
    act(() => {
      params.callbackState.onApplyBootstrapCache(bootstrap);
      params.callbackState.onAfterLoginSuccess?.();
      void params.callbackState.onResetAfterLogout?.();
    });

    const cacheUpdater = input.setterState.onSetCacheLeitura.mock.calls[0][0];
    expect(typeof cacheUpdater).toBe("function");
    expect(
      cacheUpdater({
        ...input.bootstrapState.cacheLeituraVazio,
        updatedAt: "antigo",
      }).bootstrap,
    ).toBe(bootstrap);
    expect(
      cacheUpdater({
        ...input.bootstrapState.cacheLeituraVazio,
        updatedAt: "antigo",
      }).updatedAt,
    ).not.toBe("antigo");
    expect(input.resetState.onSetBloqueioAppAtivo).toHaveBeenCalledWith(false);
    expect(input.setterState.onSetCacheLeitura).toHaveBeenCalledWith(
      input.bootstrapState.cacheLeituraVazio,
    );
    expect(input.setterState.onSetConversa).toHaveBeenCalledWith(null);
    expect(input.resetState.onSetMensagem).toHaveBeenCalledWith("");
    expect(input.resetState.onSetAnexoRascunho).toHaveBeenCalledWith(null);
    expect(input.resetState.onSetAbaAtiva).toHaveBeenCalledWith("chat");
    expect(input.resetState.onSetGuidedInspectionDraft).toHaveBeenCalledWith(
      null,
    );
    expect(input.setterState.onSetLaudosDisponiveis).toHaveBeenCalledWith([]);
    expect(input.setterState.onSetErroLaudos).toHaveBeenCalledWith("");
    expect(input.setterState.onSetMensagensMesa).toHaveBeenCalledWith([]);
    expect(input.resetState.onSetErroMesa).toHaveBeenCalledWith("");
    expect(input.resetState.onSetMensagemMesa).toHaveBeenCalledWith("");
    expect(input.resetState.onSetAnexoMesaRascunho).toHaveBeenCalledWith(null);
    expect(input.setterState.onSetFilaOffline).toHaveBeenCalledWith([]);
    expect(input.resetState.onSetSincronizandoFilaOffline).toHaveBeenCalledWith(
      false,
    );
    expect(input.resetState.onSetSincronizandoItemFilaId).toHaveBeenCalledWith(
      "",
    );
    expect(input.setterState.onSetLaudoMesaCarregado).toHaveBeenCalledWith(
      null,
    );
    expect(input.setterState.onSetNotificacoes).toHaveBeenCalledWith([]);
    expect(input.resetState.onSetAnexoAbrindoChave).toHaveBeenCalledWith("");
    expect(
      input.resetState.onResetSessionBoundSettingsPresentationState,
    ).toHaveBeenCalledTimes(1);
    expect(input.resetState.onResetSettingsUi).toHaveBeenCalledTimes(1);
    expect(
      input.resetState.onClearPendingSensitiveAction,
    ).toHaveBeenCalledTimes(1);
  });
});
