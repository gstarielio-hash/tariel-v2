import { Alert } from "react-native";

import { compartilharTextoExportado } from "../common/appSupportHelpers";
import type { InspectorRootBootstrap } from "../useInspectorRootBootstrap";
import { useInspectorRootSettingsSurface } from "./useInspectorRootSettingsSurface";
import { reautenticacaoAindaValida } from "./reauth";

interface BuildInspectorRootSettingsSurfaceSecurityStateInput {
  bootstrap: InspectorRootBootstrap;
}

export function buildInspectorRootSettingsSurfaceSecurityState({
  bootstrap,
}: BuildInspectorRootSettingsSurfaceSecurityStateInput): Parameters<
  typeof useInspectorRootSettingsSurface
>[0]["securityState"] {
  const settingsBindings = bootstrap.settingsBindings;
  const settingsSupportState = bootstrap.settingsSupportState;
  const sessionFlow = bootstrap.sessionFlow;
  const shellSupport = bootstrap.shellSupport;
  const refsAndBridges = bootstrap.refsAndBridges;
  const reauthActions = bootstrap.reauthActions;

  return {
    accountState: {
      emailAtualConta: settingsBindings.account.emailAtualConta,
      fallbackEmail: sessionFlow.state.email,
    },
    actionState: {
      abrirConfirmacaoConfiguracao:
        settingsSupportState.navigationActions.abrirConfirmacaoConfiguracao,
      abrirFluxoReautenticacao: reauthActions.abrirFluxoReautenticacao,
      abrirSheetConfiguracao:
        settingsSupportState.navigationActions.abrirSheetConfiguracao,
      compartilharTextoExportado,
      executarComReautenticacao: reauthActions.executarComReautenticacao,
      fecharConfiguracoes: shellSupport.fecharConfiguracoes,
      handleLogout: sessionFlow.actions.handleLogout,
      openSystemSettings: refsAndBridges.onOpenSystemSettings,
      registrarEventoSegurancaLocal:
        settingsSupportState.registrarEventoSegurancaLocal,
      reautenticacaoAindaValida,
      showAlert: Alert.alert,
    },
    authState: {
      biometriaLocalSuportada:
        settingsBindings.security.biometriaLocalSuportada,
      biometriaPermitida: settingsBindings.security.biometriaPermitida,
      codigo2FA: settingsSupportState.presentationState.codigo2FA,
      codigosRecuperacao:
        settingsSupportState.presentationState.codigosRecuperacao,
      reautenticacaoExpiraEm:
        settingsSupportState.presentationState.reautenticacaoExpiraEm,
      requireAuthOnOpen: settingsBindings.security.requireAuthOnOpen,
      twoFactorEnabled: settingsSupportState.presentationState.twoFactorEnabled,
      twoFactorMethod: settingsSupportState.presentationState.twoFactorMethod,
    },
    collectionState: {
      provedoresConectados:
        settingsSupportState.presentationState.provedoresConectados,
      sessoesAtivas: settingsSupportState.presentationState.sessoesAtivas,
    },
    setterState: {
      setCodigo2FA: settingsSupportState.presentationActions.setCodigo2FA,
      setCodigosRecuperacao:
        settingsSupportState.presentationActions.setCodigosRecuperacao,
      setDeviceBiometricsEnabled:
        settingsBindings.security.setDeviceBiometricsEnabled,
      setProvedoresConectados:
        settingsSupportState.presentationActions.setProvedoresConectados,
      setRequireAuthOnOpen: settingsBindings.security.setRequireAuthOnOpen,
      setSessoesAtivas:
        settingsSupportState.presentationActions.setSessoesAtivas,
      setSettingsSheetNotice:
        settingsSupportState.navigationActions.setSettingsSheetNotice,
      setTwoFactorEnabled:
        settingsSupportState.presentationActions.setTwoFactorEnabled,
      setTwoFactorMethod:
        settingsSupportState.presentationActions.setTwoFactorMethod,
    },
  };
}
