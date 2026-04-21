import { render, screen } from "@testing-library/react-native";

const mockUseInspectorRootApp = jest.fn();

jest.mock("./useInspectorRootApp", () => ({
  useInspectorRootApp: () => mockUseInspectorRootApp(),
}));

jest.mock("./common/InspectorAuthenticatedShell", () => ({
  InspectorAuthenticatedShell: ({
    pilotAutomationProbeLabel,
  }: {
    pilotAutomationProbeLabel: string;
  }) => {
    const { Text } = require("react-native");

    return <Text>{`auth:${pilotAutomationProbeLabel}`}</Text>;
  },
}));

jest.mock("./auth/InspectorLoginShell", () => ({
  InspectorLoginShell: () => {
    const { Text } = require("react-native");

    return <Text>login</Text>;
  },
}));

import { InspectorMobileApp } from "./InspectorMobileApp";

describe("InspectorMobileApp", () => {
  it("renderiza o shell autenticado quando existe sessão", () => {
    mockUseInspectorRootApp.mockReturnValue({
      authenticatedLayoutProps: {} as never,
      automationDiagnosticsEnabled: true,
      hasSession: true,
      loginScreenProps: {} as never,
      pilotAutomationMarkerIds: [],
      pilotAutomationProbeLabel: "probe-ok",
    });

    render(<InspectorMobileApp />);

    expect(screen.getByText("auth:probe-ok")).toBeTruthy();
  });

  it("renderiza o shell de login quando não existe sessão", () => {
    mockUseInspectorRootApp.mockReturnValue({
      authenticatedLayoutProps: {} as never,
      automationDiagnosticsEnabled: true,
      hasSession: false,
      loginScreenProps: {} as never,
      pilotAutomationMarkerIds: [],
      pilotAutomationProbeLabel: "probe-ok",
    });

    render(<InspectorMobileApp />);

    expect(screen.getByText("login")).toBeTruthy();
  });
});
