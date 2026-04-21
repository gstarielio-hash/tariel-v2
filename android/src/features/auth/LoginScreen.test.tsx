import { render } from "@testing-library/react-native";

import { LoginScreen, type LoginScreenProps } from "./LoginScreen";

jest.mock("@expo/vector-icons", () => {
  const React = require("react");
  const { Text } = require("react-native");
  return {
    MaterialCommunityIcons: ({
      name,
      ...props
    }: {
      name: string;
      [key: string]: unknown;
    }) => React.createElement(Text, props, name),
  };
});

jest.mock("expo-linear-gradient", () => {
  const React = require("react");
  const { View } = require("react-native");
  return {
    LinearGradient: ({ children, ...props }: any) =>
      React.createElement(View, props, children),
  };
});

jest.mock("../common/BrandElements", () => ({
  BrandIntroMark: () => null,
  BrandLaunchOverlay: () => null,
}));

function createProps(
  overrides: Partial<LoginScreenProps> = {},
): LoginScreenProps {
  return {
    accentColor: "#F47B20",
    animacoesAtivas: false,
    appGradientColors: ["#FFFFFF", "#F7F5F1", "#FBFAF7"],
    carregando: false,
    email: "inspetor@tariel.ia",
    emailInputRef: { current: null },
    entrando: false,
    erro: "",
    fontScale: 1,
    introVisivel: false,
    keyboardAvoidingBehavior: "padding",
    keyboardVisible: false,
    loginKeyboardBottomPadding: 0,
    loginKeyboardVerticalOffset: 0,
    mostrarSenha: false,
    onEmailChange: jest.fn(),
    onEmailSubmit: jest.fn(),
    onEsqueciSenha: jest.fn(),
    onIntroDone: jest.fn(),
    onLogin: jest.fn(),
    onLoginSocial: jest.fn(),
    onSenhaChange: jest.fn(),
    onSenhaSubmit: jest.fn(),
    onToggleMostrarSenha: jest.fn(),
    senha: "senha-super-segura",
    senhaInputRef: { current: null },
    ...overrides,
  };
}

describe("LoginScreen", () => {
  it("mantém o login enxuto e sem textos auxiliares ou login social", () => {
    const { queryByText, queryByTestId } = render(
      <LoginScreen {...createProps()} />,
    );

    expect(queryByText("Entre no app mobile")).toBeNull();
    expect(queryByText("Acesso corporativo liberado")).toBeNull();
    expect(queryByText("Portal do inspetor")).toBeNull();
    expect(
      queryByText(/Use o email corporativo liberado pela operação/i),
    ).toBeNull();
    expect(queryByTestId("login-google-button")).toBeNull();
    expect(queryByTestId("login-microsoft-button")).toBeNull();
  });
});
