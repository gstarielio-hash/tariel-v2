jest.mock("../InspectorAuthenticatedLayout", () => ({
  InspectorAuthenticatedLayout: jest.fn(() => null),
}));

import { render } from "@testing-library/react-native";
import * as inspectorAuthenticatedLayoutModule from "../InspectorAuthenticatedLayout";
import { InspectorAuthenticatedShell } from "./InspectorAuthenticatedShell";

describe("InspectorAuthenticatedShell", () => {
  it("renderiza o probe de automação e o layout autenticado", () => {
    const { getByTestId } = render(
      <InspectorAuthenticatedShell
        authenticatedLayoutProps={{} as never}
        automationDiagnosticsEnabled
        pilotAutomationMarkerIds={["probe-1", "probe-2"]}
        pilotAutomationProbeLabel="probe-label"
      />,
    );
    const mockedLayout = jest.mocked(
      inspectorAuthenticatedLayoutModule.InspectorAuthenticatedLayout,
    );

    expect(getByTestId("authenticated-shell-selection-probe")).toBeTruthy();
    expect(getByTestId("probe-1")).toBeTruthy();
    expect(getByTestId("probe-2")).toBeTruthy();
    expect(mockedLayout).toHaveBeenCalledTimes(1);
  });
});
