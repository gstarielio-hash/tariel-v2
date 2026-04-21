import { InspectorLoginShell } from "./auth/InspectorLoginShell";
import { InspectorAuthenticatedShell } from "./common/InspectorAuthenticatedShell";
import { useInspectorRootApp } from "./useInspectorRootApp";

export function InspectorMobileApp() {
  const {
    authenticatedLayoutProps,
    automationDiagnosticsEnabled,
    hasSession,
    loginScreenProps,
    pilotAutomationMarkerIds,
    pilotAutomationProbeLabel,
  } = useInspectorRootApp();

  if (hasSession) {
    return (
      <InspectorAuthenticatedShell
        authenticatedLayoutProps={authenticatedLayoutProps}
        automationDiagnosticsEnabled={automationDiagnosticsEnabled}
        pilotAutomationMarkerIds={pilotAutomationMarkerIds}
        pilotAutomationProbeLabel={pilotAutomationProbeLabel}
      />
    );
  }

  return <InspectorLoginShell loginScreenProps={loginScreenProps} />;
}
