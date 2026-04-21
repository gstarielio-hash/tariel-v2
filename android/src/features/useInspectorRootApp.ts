import { isMobileAutomationDiagnosticsEnabled } from "../config/mobileAutomationDiagnostics";
import { useInspectorRootBootstrap } from "./useInspectorRootBootstrap";
import { useInspectorRootBackNavigationController } from "./common/useInspectorRootBackNavigationController";
import { useInspectorRootControllers } from "./useInspectorRootControllers";
import { useInspectorRootPresentation } from "./useInspectorRootPresentation";

const AUTOMATION_DIAGNOSTICS_ENABLED = isMobileAutomationDiagnosticsEnabled();

export function useInspectorRootApp() {
  const bootstrap = useInspectorRootBootstrap();
  const controllers = useInspectorRootControllers(bootstrap);
  useInspectorRootBackNavigationController({ bootstrap, controllers });
  const presentation = useInspectorRootPresentation({
    bootstrap,
    controllers,
  });

  return {
    authenticatedLayoutProps: presentation.authenticatedLayoutProps,
    automationDiagnosticsEnabled: AUTOMATION_DIAGNOSTICS_ENABLED,
    hasSession: Boolean(bootstrap.sessionFlow.state.session),
    loginScreenProps: presentation.loginScreenProps,
    pilotAutomationMarkerIds:
      controllers.pilotAutomationController.pilotAutomationMarkerIds,
    pilotAutomationProbeLabel:
      controllers.pilotAutomationController.pilotAutomationProbeLabel,
  };
}
