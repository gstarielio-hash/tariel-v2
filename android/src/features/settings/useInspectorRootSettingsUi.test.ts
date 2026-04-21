import { renderHook } from "@testing-library/react-native";

const mockExecutarExclusaoContaLocal = jest.fn();
const mockHandleConfirmarAcaoCritica = jest.fn();
const mockHandleExportarDados = jest.fn();
const mockHandleSelecionarModeloIa = jest.fn();
const mockHandleConfirmarSettingsSheet = jest.fn();
const mockRenderSettingsSheetBody = jest.fn();
const mockToggleActions = {
  handleExportarAntesDeExcluirConta: jest.fn(),
  handleReportarAtividadeSuspeita: jest.fn(),
  handleRevisarPermissoesCriticas: jest.fn(),
  handleToggleBackupAutomatico: jest.fn(),
  handleToggleEntradaPorVoz: jest.fn(),
  handleToggleMostrarConteudoNotificacao: jest.fn(),
  handleToggleMostrarSomenteNovaMensagem: jest.fn(),
  handleToggleNotificaPush: jest.fn(),
  handleToggleOcultarConteudoBloqueado: jest.fn(),
  handleToggleRespostaPorVoz: jest.fn(),
  handleToggleSincronizacaoDispositivos: jest.fn(),
  handleToggleSpeechEnabled: jest.fn(),
  handleToggleUploadArquivos: jest.fn(),
  handleToggleVibracao: jest.fn(),
};

jest.mock("./buildAccountDeletionAction", () => ({
  buildAccountDeletionAction: jest.fn(() => mockExecutarExclusaoContaLocal),
}));

jest.mock("./buildInspectorRootSettingsConfirmExportActions", () => ({
  buildInspectorRootSettingsConfirmExportActions: jest.fn(() => ({
    handleConfirmarAcaoCritica: mockHandleConfirmarAcaoCritica,
    handleExportarDados: mockHandleExportarDados,
    handleSelecionarModeloIa: mockHandleSelecionarModeloIa,
  })),
}));

jest.mock("./useInspectorRootSettingsToggleActions", () => ({
  useInspectorRootSettingsToggleActions: jest.fn(() => mockToggleActions),
}));

jest.mock("./buildInspectorRootSettingsSheetProps", () => ({
  buildInspectorRootSettingsSheetProps: jest.fn(() => ({
    handleConfirmarSettingsSheet: mockHandleConfirmarSettingsSheet,
    renderSettingsSheetBody: mockRenderSettingsSheetBody,
  })),
}));

jest.mock("./buildInspectorRootSettingsDrawerProps", () => ({
  buildInspectorRootSettingsDrawerProps: jest.fn(() => ({
    drawer: "ok",
  })),
}));

import { buildAccountDeletionAction } from "./buildAccountDeletionAction";
import { buildInspectorRootSettingsConfirmExportActions } from "./buildInspectorRootSettingsConfirmExportActions";
import { buildInspectorRootSettingsDrawerProps } from "./buildInspectorRootSettingsDrawerProps";
import { buildInspectorRootSettingsSheetProps } from "./buildInspectorRootSettingsSheetProps";
import { useInspectorRootSettingsToggleActions } from "./useInspectorRootSettingsToggleActions";
import { useInspectorRootSettingsUi } from "./useInspectorRootSettingsUi";

describe("useInspectorRootSettingsUi", () => {
  it("encapsula account deletion, confirm/export, toggles, sheet e drawer em um único hook root", () => {
    const input = {
      accountDeletionState: {
        fecharConfiguracoes: jest.fn(),
      },
      confirmExportState: {
        accountState: {},
        actionState: {
          abrirFluxoReautenticacao: jest.fn(),
        },
        collectionState: {},
        draftState: {},
        preferenceState: {},
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
      sheetState: {
        accountState: {},
        actionsState: {},
        appState: {},
        backendState: {},
        baseState: {},
        draftState: {},
        settersState: {},
      },
      toggleState: {
        actionState: {},
        cacheState: {},
        permissionState: {},
        setterState: {},
        voiceState: {},
      },
    };

    const { result } = renderHook(() =>
      useInspectorRootSettingsUi(input as any),
    );

    expect(buildAccountDeletionAction).toHaveBeenCalledWith(
      input.accountDeletionState,
    );
    expect(useInspectorRootSettingsToggleActions).toHaveBeenCalledWith(
      expect.objectContaining({
        ...input.toggleState,
        actionState: expect.objectContaining({
          handleExportarDados: mockHandleExportarDados,
        }),
      }),
    );
    expect(buildInspectorRootSettingsConfirmExportActions).toHaveBeenCalledWith(
      expect.objectContaining({
        actionState: expect.objectContaining({
          executarExclusaoContaLocal: mockExecutarExclusaoContaLocal,
        }),
      }),
    );
    expect(buildInspectorRootSettingsSheetProps).toHaveBeenCalledWith(
      expect.objectContaining({
        actionsState: expect.objectContaining({
          handleSelecionarModeloIa: mockHandleSelecionarModeloIa,
          handleToggleUploadArquivos:
            mockToggleActions.handleToggleUploadArquivos,
        }),
      }),
    );
    expect(buildInspectorRootSettingsDrawerProps).toHaveBeenCalledWith(
      expect.objectContaining({
        securityState: expect.objectContaining({
          handleExcluirConta: mockExecutarExclusaoContaLocal,
          handleExportarDados: mockHandleExportarDados,
        }),
        experienceState: expect.objectContaining({
          handleToggleEntradaPorVoz:
            mockToggleActions.handleToggleEntradaPorVoz,
        }),
      }),
    );
    expect(result.current.settingsDrawerPanelProps).toEqual({ drawer: "ok" });
    expect(result.current.handleConfirmarAcaoCritica).toBe(
      mockHandleConfirmarAcaoCritica,
    );
    expect(result.current.handleConfirmarSettingsSheet).toBe(
      mockHandleConfirmarSettingsSheet,
    );
    expect(result.current.renderSettingsSheetBody).toBe(
      mockRenderSettingsSheetBody,
    );
  });
});
