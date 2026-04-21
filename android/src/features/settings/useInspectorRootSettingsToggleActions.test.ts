import { renderHook } from "@testing-library/react-native";

const mockHandleToggleBackupAutomatico = jest.fn();
const mockHandleToggleUploadArquivos = jest.fn();

jest.mock("./useSettingsToggleActions", () => ({
  useSettingsToggleActions: jest.fn(() => ({
    handleExportarAntesDeExcluirConta: jest.fn(),
    handleReportarAtividadeSuspeita: jest.fn(),
    handleRevisarPermissoesCriticas: jest.fn(),
    handleToggleBackupAutomatico: mockHandleToggleBackupAutomatico,
    handleToggleEntradaPorVoz: jest.fn(),
    handleToggleMostrarConteudoNotificacao: jest.fn(),
    handleToggleMostrarSomenteNovaMensagem: jest.fn(),
    handleToggleNotificaPush: jest.fn(),
    handleToggleOcultarConteudoBloqueado: jest.fn(),
    handleToggleRespostaPorVoz: jest.fn(),
    handleToggleSincronizacaoDispositivos: jest.fn(),
    handleToggleSpeechEnabled: jest.fn(),
    handleToggleUploadArquivos: mockHandleToggleUploadArquivos,
    handleToggleVibracao: jest.fn(),
  })),
}));

import { useSettingsToggleActions } from "./useSettingsToggleActions";
import { useInspectorRootSettingsToggleActions } from "./useInspectorRootSettingsToggleActions";

function criarInput() {
  return {
    actionState: {
      abrirConfirmacaoConfiguracao: jest.fn(),
      executarComReautenticacao: jest.fn(),
      handleExportarDados: jest.fn(),
      onOpenSystemSettings: jest.fn(),
      onSetSettingsSheetNotice: jest.fn(),
      registrarEventoSegurancaLocal: jest.fn(),
      showAlert: jest.fn(),
    },
    cacheState: {
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
      filaOffline: [],
      onIsOfflineItemReadyForRetry: jest.fn().mockReturnValue(false),
      onSaveReadCacheLocally: jest.fn().mockResolvedValue(undefined),
      onSyncOfflineQueue: jest.fn().mockResolvedValue(undefined),
      sessionAccessToken: "token-123",
      statusApi: "online" as const,
    },
    permissionState: {
      arquivosPermitidos: true,
      cameraPermitida: false,
      microfonePermitido: true,
      notificacoesPermitidas: false,
    },
    setterState: {
      setAnexoMesaRascunho: jest.fn(),
      setAnexoRascunho: jest.fn(),
      setArquivosPermitidos: jest.fn(),
      setBackupAutomatico: jest.fn(),
      setEntradaPorVoz: jest.fn(),
      setMicrofonePermitido: jest.fn(),
      setMostrarConteudoNotificacao: jest.fn(),
      setMostrarSomenteNovaMensagem: jest.fn(),
      setNotificaPush: jest.fn(),
      setNotificacoesPermitidas: jest.fn(),
      setOcultarConteudoBloqueado: jest.fn(),
      setRespostaPorVoz: jest.fn(),
      setSpeechEnabled: jest.fn(),
      setSincronizacaoDispositivos: jest.fn(),
      setUploadArquivosAtivo: jest.fn(),
      setVibracaoAtiva: jest.fn(),
    },
    voiceState: {
      voiceInputRuntimeSupported: true,
      voiceInputUnavailableMessage: "Use o teclado por voz do sistema.",
    },
  };
}

describe("useInspectorRootSettingsToggleActions", () => {
  it("encapsula a composição do trilho toggle do root sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() =>
      useInspectorRootSettingsToggleActions(input),
    );
    const mockedHook = jest.mocked(useSettingsToggleActions);

    result.current.handleToggleBackupAutomatico(true);
    result.current.handleToggleUploadArquivos(true);

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        arquivosPermitidos: input.permissionState.arquivosPermitidos,
        sessionAccessToken: input.cacheState.sessionAccessToken,
        handleExportarDados: input.actionState.handleExportarDados,
        setBackupAutomatico: input.setterState.setBackupAutomatico,
      }),
    );
    expect(mockHandleToggleBackupAutomatico).toHaveBeenCalledWith(true);
    expect(mockHandleToggleUploadArquivos).toHaveBeenCalledWith(true);
  });
});
