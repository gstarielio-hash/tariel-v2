import { buildAccountDeletionAction } from "./buildAccountDeletionAction";
import { buildInspectorRootSettingsConfirmExportActions } from "./buildInspectorRootSettingsConfirmExportActions";
import { buildInspectorRootSettingsDrawerProps } from "./buildInspectorRootSettingsDrawerProps";
import { buildInspectorRootSettingsSheetProps } from "./buildInspectorRootSettingsSheetProps";
import { useInspectorRootSettingsToggleActions } from "./useInspectorRootSettingsToggleActions";

type InspectorRootSettingsConfirmExportInput = Parameters<
  typeof buildInspectorRootSettingsConfirmExportActions
>[0];

type InspectorRootSettingsToggleInput = Parameters<
  typeof useInspectorRootSettingsToggleActions
>[0];

type InspectorRootSettingsSheetInput = Parameters<
  typeof buildInspectorRootSettingsSheetProps
>[0];

type InspectorRootSettingsDrawerInput = Parameters<
  typeof buildInspectorRootSettingsDrawerProps
>[0];

interface UseInspectorRootSettingsUiInput {
  accountDeletionState: Parameters<typeof buildAccountDeletionAction>[0];
  confirmExportState: Omit<
    InspectorRootSettingsConfirmExportInput,
    "actionState"
  > & {
    actionState: Omit<
      InspectorRootSettingsConfirmExportInput["actionState"],
      "executarExclusaoContaLocal"
    >;
  };
  drawerState: Omit<
    InspectorRootSettingsDrawerInput,
    "experienceState" | "securityState"
  > & {
    experienceState: Omit<
      InspectorRootSettingsDrawerInput["experienceState"],
      | "handleToggleEntradaPorVoz"
      | "handleToggleNotificaPush"
      | "handleToggleRespostaPorVoz"
      | "handleToggleSpeechEnabled"
      | "handleToggleVibracao"
    >;
    securityState: Omit<
      InspectorRootSettingsDrawerInput["securityState"],
      | "handleExcluirConta"
      | "handleExportarAntesDeExcluirConta"
      | "handleExportarDados"
      | "handleReportarAtividadeSuspeita"
      | "handleRevisarPermissoesCriticas"
      | "handleToggleBackupAutomatico"
      | "handleToggleMostrarConteudoNotificacao"
      | "handleToggleMostrarSomenteNovaMensagem"
      | "handleToggleOcultarConteudoBloqueado"
      | "handleToggleSincronizacaoDispositivos"
    >;
  };
  sheetState: Omit<InspectorRootSettingsSheetInput, "actionsState"> & {
    actionsState: Omit<
      InspectorRootSettingsSheetInput["actionsState"],
      "handleSelecionarModeloIa" | "handleToggleUploadArquivos"
    >;
  };
  toggleState: Omit<InspectorRootSettingsToggleInput, "actionState"> & {
    actionState: Omit<
      InspectorRootSettingsToggleInput["actionState"],
      "handleExportarDados"
    >;
  };
}

export function useInspectorRootSettingsUi({
  accountDeletionState,
  confirmExportState,
  drawerState,
  sheetState,
  toggleState,
}: UseInspectorRootSettingsUiInput) {
  const executarExclusaoContaLocal =
    buildAccountDeletionAction(accountDeletionState);
  const {
    handleConfirmarAcaoCritica,
    handleExportarDados,
    handleSelecionarModeloIa,
  } = buildInspectorRootSettingsConfirmExportActions({
    ...confirmExportState,
    actionState: {
      ...confirmExportState.actionState,
      executarExclusaoContaLocal,
    },
  });
  const toggleActions = useInspectorRootSettingsToggleActions({
    ...toggleState,
    actionState: {
      ...toggleState.actionState,
      handleExportarDados,
    },
  });
  const { handleConfirmarSettingsSheet, renderSettingsSheetBody } =
    buildInspectorRootSettingsSheetProps({
      ...sheetState,
      actionsState: {
        ...sheetState.actionsState,
        handleSelecionarModeloIa,
        handleToggleUploadArquivos: toggleActions.handleToggleUploadArquivos,
      },
    });
  const settingsDrawerPanelProps = buildInspectorRootSettingsDrawerProps({
    ...drawerState,
    securityState: {
      ...drawerState.securityState,
      handleExcluirConta: executarExclusaoContaLocal,
      handleExportarAntesDeExcluirConta:
        toggleActions.handleExportarAntesDeExcluirConta,
      handleExportarDados,
      handleReportarAtividadeSuspeita:
        toggleActions.handleReportarAtividadeSuspeita,
      handleRevisarPermissoesCriticas:
        toggleActions.handleRevisarPermissoesCriticas,
      handleToggleBackupAutomatico: toggleActions.handleToggleBackupAutomatico,
      handleToggleMostrarConteudoNotificacao:
        toggleActions.handleToggleMostrarConteudoNotificacao,
      handleToggleMostrarSomenteNovaMensagem:
        toggleActions.handleToggleMostrarSomenteNovaMensagem,
      handleToggleOcultarConteudoBloqueado:
        toggleActions.handleToggleOcultarConteudoBloqueado,
      handleToggleSincronizacaoDispositivos:
        toggleActions.handleToggleSincronizacaoDispositivos,
    },
    experienceState: {
      ...drawerState.experienceState,
      handleToggleEntradaPorVoz: toggleActions.handleToggleEntradaPorVoz,
      handleToggleNotificaPush: toggleActions.handleToggleNotificaPush,
      handleToggleRespostaPorVoz: toggleActions.handleToggleRespostaPorVoz,
      handleToggleSpeechEnabled: toggleActions.handleToggleSpeechEnabled,
      handleToggleVibracao: toggleActions.handleToggleVibracao,
    },
  });

  return {
    ...toggleActions,
    executarExclusaoContaLocal,
    handleConfirmarAcaoCritica,
    handleConfirmarSettingsSheet,
    handleExportarDados,
    handleSelecionarModeloIa,
    renderSettingsSheetBody,
    settingsDrawerPanelProps,
  };
}
