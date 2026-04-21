import { act, renderHook } from "@testing-library/react-native";

import {
  listarEventosObservabilidade,
  resumirEventosObservabilidade,
} from "../../config/observability";
import type { ConfirmSheetState } from "./settingsSheetTypes";
import type { ExternalIntegration } from "./useSettingsPresentation";
import { useSettingsOperationsActions } from "./useSettingsOperationsActions";

jest.mock("../../config/observability", () => ({
  listarEventosObservabilidade: jest.fn().mockResolvedValue([]),
  resumirEventosObservabilidade: jest.fn().mockReturnValue({
    total: 0,
    failures: 0,
    latestAt: "",
    averageDurationMs: 0,
    byKind: {
      api: 0,
      offline_queue: 0,
      activity_monitor: 0,
      push: 0,
    },
    failuresByKind: {
      api: 0,
      offline_queue: 0,
      activity_monitor: 0,
      push: 0,
    },
  }),
}));

function criarBaseParams() {
  const integracoesExternas: ExternalIntegration[] = [
    {
      id: "google_drive",
      label: "Google Drive",
      description: "Desc",
      icon: "google",
      connected: false,
      lastSyncAt: "",
    },
  ];

  return {
    appRuntime: {
      versionLabel: "1.0.0",
      buildLabel: "100",
      updateStatusFallback: "Build atual.",
    },
    cacheLeituraVazio: {
      bootstrap: null,
      updatedAt: "",
    },
    canalSuporteUrl: "",
    emailAtualConta: "inspetor@tariel.test",
    eventosSeguranca: [],
    executarComReautenticacao: jest.fn((_: string, onSuccess: () => void) =>
      onSuccess(),
    ),
    fallbackEmail: "fallback@tariel.test",
    fecharConfiguracoes: jest.fn(),
    offlineSyncObservability: {
      contract_name: "android_offline_sync_view" as const,
      contract_version: "v1" as const,
      source_channel: "android" as const,
      projection_payload: {
        queue_totals: {
          total_items: 2,
          ready_items: 1,
          failed_items: 1,
          backoff_items: 0,
          chat_items: 1,
          mesa_items: 1,
          attachment_items: 1,
        },
        sync_capability: {
          status_api: "online" as const,
          sync_enabled: true,
          wifi_only_sync: false,
          blocker: "none" as const,
          can_sync_now: true,
          auto_sync_armed: true,
        },
        sync_activity: {
          syncing_queue: false,
          syncing_item_id: null,
          retry_ready_exists: true,
        },
        items: [],
      },
    },
    filaSuporteLocal: [],
    formatarHorarioAtividade: jest.fn((value: string) => value),
    handleLogout: jest.fn(),
    integracaoSincronizandoId: "" as const,
    integracoesExternas,
    limpandoCache: false,
    microfonePermitido: true,
    cameraPermitida: true,
    arquivosPermitidos: true,
    notificacoesPermitidas: true,
    pushRegistrationLastError: "",
    pushRegistrationSnapshot: null,
    pushRegistrationStatus: "idle",
    abrirConfirmacaoConfiguracao: jest.fn(),
    abrirSheetConfiguracao: jest.fn(),
    perfilExibicao: "Inspetor",
    perfilNome: "Inspetor Tariel",
    registrarEventoSegurancaLocal: jest.fn(),
    reautenticacaoExpiraEm: "",
    reautenticacaoAindaValida: jest.fn().mockReturnValue(true),
    abrirFluxoReautenticacao: jest.fn(),
    resumoAtualizacaoApp: "Sem atualização",
    sessaoAtualTitulo: "Pixel",
    setBugAttachmentDraft: jest.fn(),
    setCacheLeitura: jest.fn(),
    setFilaSuporteLocal: jest.fn(),
    setIntegracaoSincronizandoId: jest.fn(),
    setIntegracoesExternas: jest.fn(),
    setLimpandoCache: jest.fn(),
    setSettingsSheetNotice: jest.fn(),
    setStatusApi: jest.fn(),
    setStatusAtualizacaoApp: jest.fn(),
    setUltimaLimpezaCacheEm: jest.fn(),
    setUltimaVerificacaoAtualizacao: jest.fn(),
    setVerificandoAtualizacoes: jest.fn(),
    settingsSheetNotice: "",
    compartilharTextoExportado: jest.fn().mockResolvedValue(true),
    statusApi: "online" as const,
    statusAtualizacaoApp: "Sem atualização",
    tentarAbrirUrlExterna: jest.fn().mockResolvedValue(true),
    ultimaVerificacaoAtualizacao: "",
    verificandoAtualizacoes: false,
    showAlert: jest.fn(),
    onNotificarSistema: jest.fn(),
    montarScreenshotAnexo: jest.fn(),
  };
}

describe("useSettingsOperationsActions", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("abre confirmacao para solicitar logout e executa onConfirm", () => {
    const base = criarBaseParams();

    const { result } = renderHook(() => useSettingsOperationsActions(base));

    act(() => {
      result.current.handleSolicitarLogout();
    });

    const config = base.abrirConfirmacaoConfiguracao.mock.calls[0]?.[0] as
      | ConfirmSheetState
      | undefined;

    expect(config?.title).toBe("Sair da conta");

    act(() => {
      config?.onConfirm?.();
    });

    expect(base.fecharConfiguracoes).toHaveBeenCalled();
    expect(base.handleLogout).toHaveBeenCalled();
  });

  it("executa reautenticacao antes de abrir confirmacoes criticas", () => {
    const base = criarBaseParams();

    const { result } = renderHook(() => useSettingsOperationsActions(base));

    act(() => {
      result.current.handleApagarHistoricoConfiguracoes();
      result.current.handleLimparTodasConversasConfig();
    });

    expect(base.executarComReautenticacao).toHaveBeenCalledTimes(2);
    expect(base.abrirConfirmacaoConfiguracao).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        kind: "clearHistory",
      }),
    );
    expect(base.abrirConfirmacaoConfiguracao).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        kind: "clearConversations",
      }),
    );
  });

  it("alterna integracao externa e atualiza aviso local", () => {
    const base = criarBaseParams();

    const { result } = renderHook(() => useSettingsOperationsActions(base));

    act(() => {
      result.current.handleAlternarIntegracaoExterna(
        base.integracoesExternas[0],
      );
    });

    expect(base.setIntegracoesExternas).toHaveBeenCalledTimes(1);
    const updater = base.setIntegracoesExternas.mock.calls[0]?.[0] as (
      current: typeof base.integracoesExternas,
    ) => typeof base.integracoesExternas;
    const atualizado = updater(base.integracoesExternas);
    expect(atualizado[0]?.connected).toBe(true);
    expect(base.registrarEventoSegurancaLocal).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Google Drive conectada",
      }),
    );
    expect(base.setSettingsSheetNotice).toHaveBeenCalledWith(
      "Google Drive conectada com sucesso.",
    );
  });

  it("limpa a fila local de suporte via confirmacao", () => {
    const base = criarBaseParams();

    const { result } = renderHook(() => useSettingsOperationsActions(base));

    act(() => {
      result.current.handleLimparFilaSuporteLocal();
    });

    const config = base.abrirConfirmacaoConfiguracao.mock.calls[0]?.[0] as
      | ConfirmSheetState
      | undefined;
    expect(config?.confirmLabel).toBe("Limpar fila");

    act(() => {
      config?.onConfirm?.();
    });

    expect(base.setFilaSuporteLocal).toHaveBeenCalledWith([]);
    expect(base.registrarEventoSegurancaLocal).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Fila local de suporte limpa",
      }),
    );
  });

  it("exporta o diagnostico com o snapshot observavel da fila offline", async () => {
    const base = criarBaseParams();
    (listarEventosObservabilidade as jest.Mock).mockResolvedValue([]);
    (resumirEventosObservabilidade as jest.Mock).mockReturnValue({
      total: 3,
      failures: 1,
      latestAt: "2026-03-30T12:00:00.000Z",
      averageDurationMs: 120,
      byKind: {
        api: 1,
        offline_queue: 2,
        activity_monitor: 0,
        push: 0,
      },
      failuresByKind: {
        api: 0,
        offline_queue: 1,
        activity_monitor: 0,
        push: 0,
      },
    });

    const { result } = renderHook(() => useSettingsOperationsActions(base));

    await act(async () => {
      await result.current.handleExportarDiagnosticoApp();
    });

    expect(base.compartilharTextoExportado).toHaveBeenCalledWith(
      expect.objectContaining({
        content: expect.stringContaining(
          "Fila offline (resumo): prontas=1, falha=1, backoff=0, chat=1, mesa=1, anexos=1",
        ),
      }),
    );
    expect(base.compartilharTextoExportado).toHaveBeenCalledWith(
      expect.objectContaining({
        content: expect.stringContaining(
          "Fila offline (capacidade): api=online, sync=on, wifi_only=off, blocker=none, pode_sincronizar=sim, auto_sync=sim",
        ),
      }),
    );
  });
});
