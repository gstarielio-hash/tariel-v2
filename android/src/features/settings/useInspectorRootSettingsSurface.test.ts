import { renderHook } from "@testing-library/react-native";

const mockEntryActions = {
  handleAbrirModeloIa: jest.fn(),
  handleAbrirSobreApp: jest.fn(),
  handleAlterarEmail: jest.fn(),
  handleAlterarSenha: jest.fn(),
  handleAlternarArtigoAjuda: jest.fn(),
  handleCentralAjuda: jest.fn(),
  handleEditarPerfil: jest.fn(),
  handleEnviarFeedback: jest.fn(),
  handleLicencas: jest.fn(),
  handlePermissoes: jest.fn(),
  handlePoliticaPrivacidade: jest.fn(),
  handleReportarProblema: jest.fn(),
  handleTermosUso: jest.fn(),
  handleUploadFotoPerfil: jest.fn(),
};

const mockOperationsActions = {
  handleAbrirCanalSuporte: jest.fn(),
  handleAlternarIntegracaoExterna: jest.fn(),
  handleApagarHistoricoConfiguracoes: jest.fn(),
  handleDetalhesSegurancaArquivos: jest.fn(),
  handleExportarDiagnosticoApp: jest.fn(),
  handleLimparCache: jest.fn(),
  handleLimparTodasConversasConfig: jest.fn(),
  handleLimparFilaSuporteLocal: jest.fn(),
  handleRemoverScreenshotBug: jest.fn(),
  handleSelecionarScreenshotBug: jest.fn(),
  handleSincronizarIntegracaoExterna: jest.fn(),
  handleSolicitarLogout: jest.fn(),
  handleVerificarAtualizacoes: jest.fn(),
};

const mockSecurityActions = {
  handleAbrirAjustesDoSistema: jest.fn(),
  handleCompartilharCodigosRecuperacao: jest.fn(),
  handleConfirmarCodigo2FA: jest.fn(),
  handleEncerrarOutrasSessoes: jest.fn(),
  handleEncerrarSessao: jest.fn(),
  handleEncerrarSessaoAtual: jest.fn(),
  handleEncerrarSessoesSuspeitas: jest.fn(),
  handleGerarCodigosRecuperacao: jest.fn(),
  handleMudarMetodo2FA: jest.fn(),
  handleReautenticacaoSensivel: jest.fn(),
  handleRevisarSessao: jest.fn(),
  handleToggle2FA: jest.fn(),
  handleToggleBiometriaNoDispositivo: jest.fn(),
  handleToggleProviderConnection: jest.fn(),
};

const mockUiResult = {
  handleConfirmarAcaoCritica: jest.fn(),
  handleConfirmarSettingsSheet: jest.fn(),
  renderSettingsSheetBody: jest.fn(),
  settingsDrawerPanelProps: { drawer: "ok" },
};

jest.mock("./useInspectorRootSettingsEntryActions", () => ({
  useInspectorRootSettingsEntryActions: jest.fn(() => mockEntryActions),
}));

jest.mock("./useInspectorRootSettingsOperationsActions", () => ({
  useInspectorRootSettingsOperationsActions: jest.fn(
    () => mockOperationsActions,
  ),
}));

jest.mock("./useInspectorRootSettingsSecurityActions", () => ({
  useInspectorRootSettingsSecurityActions: jest.fn(() => mockSecurityActions),
}));

jest.mock("./useInspectorRootSettingsUi", () => ({
  useInspectorRootSettingsUi: jest.fn(() => mockUiResult),
}));

import { useInspectorRootSettingsEntryActions } from "./useInspectorRootSettingsEntryActions";
import { useInspectorRootSettingsOperationsActions } from "./useInspectorRootSettingsOperationsActions";
import { useInspectorRootSettingsSecurityActions } from "./useInspectorRootSettingsSecurityActions";
import { useInspectorRootSettingsUi } from "./useInspectorRootSettingsUi";
import { useInspectorRootSettingsSurface } from "./useInspectorRootSettingsSurface";

describe("useInspectorRootSettingsSurface", () => {
  it("consolida entry, operations, security e ui na superfície root de settings", () => {
    const input = {
      entryState: {
        accountState: {},
        actionState: {},
        setterState: {},
      },
      operationsState: {
        actionState: {},
        collectionState: {},
        identityState: {},
        permissionState: {},
        runtimeState: {},
        setterState: {},
      },
      securityState: {
        accountState: {},
        actionState: {},
        authState: {},
        collectionState: {},
        setterState: {},
      },
      uiState: {
        accountDeletionState: {},
        confirmExportState: {},
        toggleState: {},
        sheetState: {
          accountState: {},
          actionsState: {},
          appState: {},
          backendState: {},
          baseState: {},
          draftState: {},
          settersState: {},
        },
        drawerState: {
          accountState: {},
          baseState: {},
          experienceState: {},
          navigationState: {},
          securityState: {},
          supportAndSystemState: {},
        },
      },
    };

    const { result } = renderHook(() =>
      useInspectorRootSettingsSurface(input as any),
    );

    expect(useInspectorRootSettingsEntryActions).toHaveBeenCalledWith(
      input.entryState,
    );
    expect(useInspectorRootSettingsOperationsActions).toHaveBeenCalledWith(
      input.operationsState,
    );
    expect(useInspectorRootSettingsSecurityActions).toHaveBeenCalledWith(
      input.securityState,
    );
    expect(useInspectorRootSettingsUi).toHaveBeenCalledWith(
      expect.objectContaining({
        sheetState: expect.objectContaining({
          actionsState: expect.objectContaining({
            handleAlternarArtigoAjuda:
              mockEntryActions.handleAlternarArtigoAjuda,
            handleAlternarIntegracaoExterna:
              mockOperationsActions.handleAlternarIntegracaoExterna,
            handleRemoverScreenshotBug:
              mockOperationsActions.handleRemoverScreenshotBug,
          }),
        }),
        drawerState: expect.objectContaining({
          accountState: expect.objectContaining({
            handleAlterarEmail: mockEntryActions.handleAlterarEmail,
            handleSolicitarLogout: mockOperationsActions.handleSolicitarLogout,
          }),
          securityState: expect.objectContaining({
            handleApagarHistoricoConfiguracoes:
              mockOperationsActions.handleApagarHistoricoConfiguracoes,
            handleConfirmarCodigo2FA:
              mockSecurityActions.handleConfirmarCodigo2FA,
            handleLimparCache: mockOperationsActions.handleLimparCache,
          }),
          supportAndSystemState: expect.objectContaining({
            handleAbrirAjustesDoSistema:
              mockSecurityActions.handleAbrirAjustesDoSistema,
            handleAbrirCanalSuporte:
              mockOperationsActions.handleAbrirCanalSuporte,
            handlePermissoes: mockEntryActions.handlePermissoes,
          }),
        }),
      }),
    );
    expect(result.current).toBe(mockUiResult);
  });
});
