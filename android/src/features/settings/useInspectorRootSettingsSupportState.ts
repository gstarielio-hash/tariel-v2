import { useSecurityEventLog } from "../security/useSecurityEventLog";
import { useSettingsNavigation } from "./useSettingsNavigation";
import { useSettingsPresentation } from "./useSettingsPresentation";

export function useInspectorRootSettingsSupportState() {
  const { state: presentationState, actions: presentationActions } =
    useSettingsPresentation();
  const { registrarEventoSegurancaLocal } = useSecurityEventLog({
    setEventosSeguranca: presentationActions.setEventosSeguranca,
  });
  const { state: navigationState, actions: navigationActions } =
    useSettingsNavigation();

  return {
    navigationActions,
    navigationState,
    presentationActions,
    presentationState,
    registrarEventoSegurancaLocal,
  };
}
