import { render } from "@testing-library/react-native";

jest.mock("@expo/vector-icons", () => ({
  MaterialCommunityIcons: "MaterialCommunityIcons",
}));

import {
  ActivityCenterModal,
  AttachmentPickerModal,
} from "./OperationalModals";

const baseProps = {
  visible: true,
  onClose: jest.fn(),
  monitorandoAtividade: false,
  notificacoes: [],
  onAbrirNotificacao: jest.fn(),
  formatarHorarioAtividade: jest.fn().mockReturnValue("18:00"),
  automationDiagnosticsEnabled: true,
};

describe("ActivityCenterModal", () => {
  it("materializa um terminal no_request canonico dentro do modal", () => {
    const { getByTestId } = render(
      <ActivityCenterModal
        {...baseProps}
        activityCenterAutomationDiagnostics={{
          modalVisible: true,
          phase: "settled",
          requestDispatched: false,
          requestedTargetIds: [],
          notificationCount: 0,
          feedReadMetadata: null,
          requestTrace: null,
          skipReason: "no_target",
        }}
      />,
    );

    expect(getByTestId("activity-center-terminal-state")).toBeTruthy();
    expect(
      getByTestId("activity-center-terminal-state-no-request"),
    ).toBeTruthy();
    expect(getByTestId("activity-center-state-no-request")).toBeTruthy();
    expect(getByTestId("activity-center-request-not-started")).toBeTruthy();
    expect(getByTestId("activity-center-skip-no-target")).toBeTruthy();
    expect(
      getByTestId("activity-center-automation-probe").props.accessibilityLabel,
    ).toContain("terminal_state=no_request");
  });

  it("materializa request v2 vazio com markers terminais e de entrega", () => {
    const { getByTestId } = render(
      <ActivityCenterModal
        {...baseProps}
        activityCenterAutomationDiagnostics={{
          modalVisible: true,
          phase: "settled",
          requestDispatched: true,
          requestedTargetIds: [80, 80],
          notificationCount: 0,
          feedReadMetadata: {
            route: "feed",
            deliveryMode: "v2",
            capabilitiesVersion: "2026-03-26.09p",
            rolloutBucket: 12,
            usageMode: "organic_validation",
            validationSessionId: "orgv_09p",
            operatorRunId: "oprv_09p",
          },
          requestTrace: null,
          skipReason: null,
        }}
      />,
    );

    expect(getByTestId("activity-center-terminal-state-empty")).toBeTruthy();
    expect(getByTestId("activity-center-state-empty")).toBeTruthy();
    expect(getByTestId("activity-center-request-dispatched")).toBeTruthy();
    expect(getByTestId("activity-center-request-target-80")).toBeTruthy();
    expect(getByTestId("activity-center-feed-v2-served")).toBeTruthy();
    expect(getByTestId("activity-center-feed-v2-target-80")).toBeTruthy();
  });
});

describe("AttachmentPickerModal", () => {
  it("renderiza documento bloqueado com contexto de politica", () => {
    const { getByTestId, getByText } = render(
      <AttachmentPickerModal
        visible
        onClose={jest.fn()}
        onChoose={jest.fn()}
        options={[
          {
            key: "camera",
            title: "Camera",
            detail: "Capture a evidencia na hora.",
            icon: "camera-outline",
            enabled: true,
          },
          {
            key: "documento",
            title: "Documento",
            detail:
              "Documentos liberam quando o caso ja estiver em coleta ou laudo.",
            icon: "file-document-outline",
            enabled: false,
          },
        ]}
      />,
    );

    expect(getByTestId("attachment-picker-option-documento")).toBeTruthy();
    expect(
      getByText(
        "Documentos liberam quando o caso ja estiver em coleta ou laudo.",
      ),
    ).toBeTruthy();
  });
});
