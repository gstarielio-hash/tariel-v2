import { renderHook } from "@testing-library/react-native";

const mockHandleSolicitarLogout = jest.fn();
const mockHandleExportarDiagnosticoApp = jest.fn();

jest.mock("./useSettingsOperationsActions", () => ({
  useSettingsOperationsActions: jest.fn(() => ({
    handleAbrirCanalSuporte: jest.fn(),
    handleAlternarIntegracaoExterna: jest.fn(),
    handleApagarHistoricoConfiguracoes: jest.fn(),
    handleDetalhesSegurancaArquivos: jest.fn(),
    handleExportarDiagnosticoApp: mockHandleExportarDiagnosticoApp,
    handleLimparCache: jest.fn(),
    handleLimparTodasConversasConfig: jest.fn(),
    handleLimparFilaSuporteLocal: jest.fn(),
    handleRemoverScreenshotBug: jest.fn(),
    handleSelecionarScreenshotBug: jest.fn(),
    handleSincronizarIntegracaoExterna: jest.fn(),
    handleSolicitarLogout: mockHandleSolicitarLogout,
    handleVerificarAtualizacoes: jest.fn(),
  })),
}));

import { useSettingsOperationsActions } from "./useSettingsOperationsActions";
import { useInspectorRootSettingsOperationsActions } from "./useInspectorRootSettingsOperationsActions";

function criarInput() {
  return {
    actionState: {
      abrirConfirmacaoConfiguracao: jest.fn(),
      abrirSheetConfiguracao: jest.fn(),
      compartilharTextoExportado: jest.fn().mockResolvedValue(true),
      executarComReautenticacao: jest.fn(),
      fecharConfiguracoes: jest.fn(),
      handleLogout: jest.fn(),
      onNotificarSistema: jest.fn(),
      registrarEventoSegurancaLocal: jest.fn(),
      showAlert: jest.fn(),
      tentarAbrirUrlExterna: jest.fn().mockResolvedValue(true),
    },
    collectionState: {
      eventosSeguranca: [],
      filaSuporteLocal: [],
      integracaoSincronizandoId: "" as const,
      integracoesExternas: [],
    },
    identityState: {
      canalSuporteUrl: "",
      emailAtualConta: "inspetor@tariel.test",
      fallbackEmail: "fallback@tariel.test",
      perfilExibicao: "Gabriel",
      perfilNome: "Gabriel Tariel",
      sessaoAtualTitulo: "Pixel",
    },
    permissionState: {
      arquivosPermitidos: true,
      cameraPermitida: true,
      microfonePermitido: true,
      notificacoesPermitidas: true,
      pushRegistrationLastError: "",
      pushRegistrationSnapshot: null,
      pushRegistrationStatus: "idle",
    },
    runtimeState: {
      appRuntime: {
        versionLabel: "1.0.0",
        buildLabel: "100",
        updateStatusFallback: "Build atual.",
      },
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
      formatarHorarioAtividade: jest.fn((value: string) => value),
      limpandoCache: false,
      montarScreenshotAnexo: jest.fn(),
      offlineSyncObservability: {
        contract_name: "android_offline_sync_view" as const,
        contract_version: "v1" as const,
        source_channel: "android" as const,
        projection_payload: {
          queue_totals: {
            total_items: 0,
            ready_items: 0,
            failed_items: 0,
            backoff_items: 0,
            chat_items: 0,
            mesa_items: 0,
            attachment_items: 0,
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
            retry_ready_exists: false,
          },
          items: [],
        },
      },
      resumoAtualizacaoApp: "Sem atualização",
      statusApi: "online" as const,
      statusAtualizacaoApp: "Sem atualização",
      ultimaVerificacaoAtualizacao: "",
      verificandoAtualizacoes: false,
    },
    setterState: {
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
    },
  };
}

describe("useInspectorRootSettingsOperationsActions", () => {
  it("encapsula a composição do trilho operacional sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() =>
      useInspectorRootSettingsOperationsActions(input),
    );
    const mockedHook = jest.mocked(useSettingsOperationsActions);

    result.current.handleSolicitarLogout();
    result.current.handleExportarDiagnosticoApp();

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        appRuntime: input.runtimeState.appRuntime,
        emailAtualConta: input.identityState.emailAtualConta,
        compartilharTextoExportado:
          input.actionState.compartilharTextoExportado,
        setStatusApi: input.setterState.setStatusApi,
      }),
    );
    expect(mockHandleSolicitarLogout).toHaveBeenCalledTimes(1);
    expect(mockHandleExportarDiagnosticoApp).toHaveBeenCalledTimes(1);
  });
});
