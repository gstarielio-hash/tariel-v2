import type { ComponentProps } from "react";
import { View } from "react-native";

import { InspectorAuthenticatedLayout } from "../InspectorAuthenticatedLayout";

interface InspectorAuthenticatedShellProps {
  authenticatedLayoutProps: ComponentProps<typeof InspectorAuthenticatedLayout>;
  automationDiagnosticsEnabled: boolean;
  pilotAutomationMarkerIds: string[];
  pilotAutomationProbeLabel: string;
}

export function InspectorAuthenticatedShell({
  authenticatedLayoutProps,
  automationDiagnosticsEnabled,
  pilotAutomationMarkerIds,
  pilotAutomationProbeLabel,
}: InspectorAuthenticatedShellProps) {
  return (
    <View style={{ flex: 1 }}>
      {automationDiagnosticsEnabled && pilotAutomationMarkerIds.length ? (
        <View
          accessibilityLabel={pilotAutomationProbeLabel}
          accessible
          collapsable={false}
          pointerEvents="none"
          style={{
            alignItems: "flex-end",
            position: "absolute",
            right: 4,
            top: 4,
            width: 6,
            zIndex: 9999,
          }}
          testID="authenticated-shell-selection-probe"
        >
          {pilotAutomationMarkerIds.map((markerId, index) => (
            <View
              accessibilityLabel={markerId}
              collapsable={false}
              key={markerId}
              testID={markerId}
              style={{
                backgroundColor: "rgba(255,255,255,0.02)",
                borderRadius: 1,
                height: 2,
                marginTop: index === 0 ? 0 : 1,
                width: 2,
              }}
            />
          ))}
        </View>
      ) : null}
      <InspectorAuthenticatedLayout {...authenticatedLayoutProps} />
    </View>
  );
}
