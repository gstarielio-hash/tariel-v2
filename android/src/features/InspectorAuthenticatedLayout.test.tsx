import { render } from "@testing-library/react-native";

import { InspectorAuthenticatedLayout } from "./InspectorAuthenticatedLayout";

jest.mock("expo-linear-gradient", () => {
  const React = require("react");
  const { View } = require("react-native");
  return {
    LinearGradient: ({ children, ...props }: any) =>
      React.createElement(View, props, children),
  };
});

jest.mock("./chat/ThreadHeaderControls", () => ({
  ThreadHeaderControls: () => {
    const React = require("react");
    const { Text } = require("react-native");
    return React.createElement(Text, { testID: "thread-header-controls" });
  },
}));

jest.mock("./chat/ThreadContextCard", () => ({
  ThreadContextCard: ({ visible }: { visible?: boolean }) => {
    const React = require("react");
    const { Text } = require("react-native");
    return visible
      ? React.createElement(Text, { testID: "thread-context-card" })
      : null;
  },
}));

jest.mock("./chat/ThreadConversationPane", () => ({
  ThreadConversationPane: () => {
    const React = require("react");
    const { Text } = require("react-native");
    return React.createElement(Text, { testID: "thread-conversation-pane" });
  },
}));

jest.mock("./chat/ThreadComposerPanel", () => ({
  ThreadComposerPanel: ({ visible }: { visible?: boolean }) => {
    const React = require("react");
    const { Text } = require("react-native");
    return visible
      ? React.createElement(Text, { testID: "thread-composer-panel" })
      : null;
  },
}));

jest.mock("./common/BrandElements", () => ({
  BrandLaunchOverlay: () => null,
}));

jest.mock("./common/SessionModalsStack", () => ({
  SessionModalsStack: () => null,
}));

jest.mock("./common/SidePanelsOverlay", () => ({
  SidePanelsOverlay: () => null,
}));

jest.mock("./history/HistoryDrawerPanel", () => ({
  HistoryDrawerPanel: () => null,
}));

jest.mock("./settings/SettingsDrawerPanel", () => ({
  SettingsDrawerPanel: () => null,
}));

function criarProps() {
  return {
    accentColor: "#FF6B00",
    animacoesAtivas: true,
    appGradientColors: ["#111111", "#222222", "#333333"] as const,
    chatKeyboardVerticalOffset: 24,
    drawerOverlayOpacity: { interpolate: jest.fn() } as never,
    erroConversa: "",
    erroLaudos: "",
    historyEdgePanHandlers: {},
    historyOpen: false,
    introVisivel: false,
    keyboardAvoidingBehavior: "padding" as const,
    keyboardVisible: false,
    mesaTemMensagens: false,
    onClosePanels: jest.fn(),
    onIntroDone: jest.fn(),
    settingsDrawerVisible: false,
    settingsEdgePanHandlers: {},
    settingsOpen: false,
    threadContextVisible: true,
    vendoFinalizacao: false,
    vendoMesa: false,
    threadHeaderControlsProps: {} as never,
    threadContextCardProps: {
      actions: [],
      chips: [],
      description: "Escolha um modo para iniciar.",
      eyebrow: "",
      insights: [],
      layout: "entry_chooser" as "default" | "entry_chooser" | "finalization",
      spotlight: {
        icon: "message-processing-outline" as const,
        label: "Chat livre",
        tone: "success" as const,
      },
      title: "Por onde começar?",
    },
    threadConversationPaneProps: {
      threadKeyboardPaddingBottom: 44,
    } as never,
    threadComposerPanelProps: {} as never,
    historyDrawerPanelProps: {} as never,
    settingsDrawerPanelProps: {} as never,
    sessionModalsStackProps: {} as never,
  };
}

describe("InspectorAuthenticatedLayout", () => {
  it("oculta o composer no chooser inicial da thread", () => {
    const { queryByTestId } = render(
      <InspectorAuthenticatedLayout {...criarProps()} />,
    );

    expect(queryByTestId("thread-context-card")).toBeTruthy();
    expect(queryByTestId("thread-composer-panel")).toBeNull();
  });

  it("mostra o composer novamente após sair do chooser inicial", () => {
    const props = criarProps();
    props.threadContextCardProps = {
      ...props.threadContextCardProps,
      layout: "default" as "default" | "entry_chooser" | "finalization",
    };

    const { getByTestId } = render(<InspectorAuthenticatedLayout {...props} />);

    expect(getByTestId("thread-conversation-pane")).toBeTruthy();
    expect(getByTestId("thread-composer-panel")).toBeTruthy();
  });
});
