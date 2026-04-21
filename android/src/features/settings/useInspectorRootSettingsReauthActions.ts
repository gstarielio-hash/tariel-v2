import {
  useSettingsReauthActions,
  type UseSettingsReauthActionsParams,
} from "./useSettingsReauthActions";

type SettingsReauthParams = UseSettingsReauthActionsParams;

interface UseInspectorRootSettingsReauthActionsInput {
  actionState: Pick<
    SettingsReauthParams,
    | "abrirConfirmacaoConfiguracao"
    | "abrirSheetConfiguracao"
    | "fecharSheetConfiguracao"
    | "notificarConfiguracaoConcluida"
    | "registrarEventoSegurancaLocal"
    | "reautenticacaoAindaValida"
  >;
  draftState: Pick<
    SettingsReauthParams,
    "reautenticacaoExpiraEm" | "settingsSheet"
  >;
  setterState: Pick<
    SettingsReauthParams,
    | "setReauthReason"
    | "setReautenticacaoExpiraEm"
    | "setReautenticacaoStatus"
    | "setSettingsSheetLoading"
    | "setSettingsSheetNotice"
  >;
}

export function useInspectorRootSettingsReauthActions({
  actionState,
  draftState,
  setterState,
}: UseInspectorRootSettingsReauthActionsInput) {
  return useSettingsReauthActions({
    abrirConfirmacaoConfiguracao: actionState.abrirConfirmacaoConfiguracao,
    abrirSheetConfiguracao: actionState.abrirSheetConfiguracao,
    fecharSheetConfiguracao: actionState.fecharSheetConfiguracao,
    notificarConfiguracaoConcluida: actionState.notificarConfiguracaoConcluida,
    registrarEventoSegurancaLocal: actionState.registrarEventoSegurancaLocal,
    reautenticacaoExpiraEm: draftState.reautenticacaoExpiraEm,
    settingsSheet: draftState.settingsSheet,
    reautenticacaoAindaValida: actionState.reautenticacaoAindaValida,
    setReauthReason: setterState.setReauthReason,
    setReautenticacaoExpiraEm: setterState.setReautenticacaoExpiraEm,
    setReautenticacaoStatus: setterState.setReautenticacaoStatus,
    setSettingsSheetLoading: setterState.setSettingsSheetLoading,
    setSettingsSheetNotice: setterState.setSettingsSheetNotice,
  });
}
