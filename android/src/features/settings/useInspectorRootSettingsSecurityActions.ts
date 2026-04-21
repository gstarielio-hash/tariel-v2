import {
  useSettingsSecurityActions,
  type UseSettingsSecurityActionsParams,
} from "./useSettingsSecurityActions";

type SettingsSecurityParams = UseSettingsSecurityActionsParams;

interface UseInspectorRootSettingsSecurityActionsInput {
  accountState: Pick<
    SettingsSecurityParams,
    "emailAtualConta" | "fallbackEmail"
  >;
  actionState: Pick<
    SettingsSecurityParams,
    | "abrirConfirmacaoConfiguracao"
    | "abrirFluxoReautenticacao"
    | "abrirSheetConfiguracao"
    | "compartilharTextoExportado"
    | "executarComReautenticacao"
    | "fecharConfiguracoes"
    | "handleLogout"
    | "openSystemSettings"
    | "registrarEventoSegurancaLocal"
    | "reautenticacaoAindaValida"
    | "showAlert"
  >;
  authState: Pick<
    SettingsSecurityParams,
    | "biometriaLocalSuportada"
    | "biometriaPermitida"
    | "codigo2FA"
    | "codigosRecuperacao"
    | "reautenticacaoExpiraEm"
    | "requireAuthOnOpen"
    | "twoFactorEnabled"
    | "twoFactorMethod"
  >;
  collectionState: Pick<
    SettingsSecurityParams,
    "provedoresConectados" | "sessoesAtivas"
  >;
  setterState: Pick<
    SettingsSecurityParams,
    | "setCodigo2FA"
    | "setCodigosRecuperacao"
    | "setDeviceBiometricsEnabled"
    | "setProvedoresConectados"
    | "setRequireAuthOnOpen"
    | "setSessoesAtivas"
    | "setSettingsSheetNotice"
    | "setTwoFactorEnabled"
    | "setTwoFactorMethod"
  >;
}

export function useInspectorRootSettingsSecurityActions({
  accountState,
  actionState,
  authState,
  collectionState,
  setterState,
}: UseInspectorRootSettingsSecurityActionsInput) {
  return useSettingsSecurityActions({
    biometriaLocalSuportada: authState.biometriaLocalSuportada,
    biometriaPermitida: authState.biometriaPermitida,
    codigosRecuperacao: authState.codigosRecuperacao,
    codigo2FA: authState.codigo2FA,
    emailAtualConta: accountState.emailAtualConta,
    fallbackEmail: accountState.fallbackEmail,
    fecharConfiguracoes: actionState.fecharConfiguracoes,
    handleLogout: actionState.handleLogout,
    provedoresConectados: collectionState.provedoresConectados,
    reautenticacaoExpiraEm: authState.reautenticacaoExpiraEm,
    requireAuthOnOpen: authState.requireAuthOnOpen,
    sessoesAtivas: collectionState.sessoesAtivas,
    twoFactorEnabled: authState.twoFactorEnabled,
    twoFactorMethod: authState.twoFactorMethod,
    abrirConfirmacaoConfiguracao: actionState.abrirConfirmacaoConfiguracao,
    abrirFluxoReautenticacao: actionState.abrirFluxoReautenticacao,
    abrirSheetConfiguracao: actionState.abrirSheetConfiguracao,
    compartilharTextoExportado: actionState.compartilharTextoExportado,
    executarComReautenticacao: actionState.executarComReautenticacao,
    openSystemSettings: actionState.openSystemSettings,
    registrarEventoSegurancaLocal: actionState.registrarEventoSegurancaLocal,
    reautenticacaoAindaValida: actionState.reautenticacaoAindaValida,
    setCodigo2FA: setterState.setCodigo2FA,
    setCodigosRecuperacao: setterState.setCodigosRecuperacao,
    setDeviceBiometricsEnabled: setterState.setDeviceBiometricsEnabled,
    setProvedoresConectados: setterState.setProvedoresConectados,
    setRequireAuthOnOpen: setterState.setRequireAuthOnOpen,
    setSessoesAtivas: setterState.setSessoesAtivas,
    setSettingsSheetNotice: setterState.setSettingsSheetNotice,
    setTwoFactorEnabled: setterState.setTwoFactorEnabled,
    setTwoFactorMethod: setterState.setTwoFactorMethod,
    showAlert: actionState.showAlert,
  });
}
