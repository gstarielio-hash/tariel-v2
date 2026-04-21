import { fireEvent, render } from "@testing-library/react-native";

import { ThreadHeaderControls } from "./ThreadHeaderControls";

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

describe("ThreadHeaderControls", () => {
  it("oculta a aba Mesa quando a conta não tem esse grant", () => {
    const { queryByTestId, queryByText } = render(
      <ThreadHeaderControls
        chatHasActiveCase
        finalizacaoDisponivel
        filaOfflineTotal={0}
        headerSafeTopInset={0}
        keyboardVisible={false}
        mesaAcessoPermitido={false}
        notificacoesMesaLaudoAtual={2}
        notificacoesNaoLidas={0}
        onOpenChatTab={jest.fn()}
        onOpenFinalizarTab={jest.fn()}
        onOpenHistory={jest.fn()}
        onOpenMesaTab={jest.fn()}
        onOpenNewChat={jest.fn()}
        onOpenSettings={jest.fn()}
        vendoFinalizacao={false}
        vendoMesa={false}
      />,
    );

    expect(queryByTestId("mesa-tab-button")).toBeNull();
    expect(queryByTestId("finalizar-tab-button")).toBeTruthy();
    expect(queryByText("2")).toBeNull();
  });

  it("abre a aba Finalizar quando disponível", () => {
    const onOpenFinalizarTab = jest.fn();
    const { getByTestId } = render(
      <ThreadHeaderControls
        chatHasActiveCase
        finalizacaoDisponivel
        filaOfflineTotal={0}
        headerSafeTopInset={0}
        keyboardVisible={false}
        mesaAcessoPermitido
        notificacoesMesaLaudoAtual={0}
        notificacoesNaoLidas={0}
        onOpenChatTab={jest.fn()}
        onOpenFinalizarTab={onOpenFinalizarTab}
        onOpenHistory={jest.fn()}
        onOpenMesaTab={jest.fn()}
        onOpenNewChat={jest.fn()}
        onOpenSettings={jest.fn()}
        vendoFinalizacao={false}
        vendoMesa={false}
      />,
    );

    fireEvent.press(getByTestId("finalizar-tab-button"));

    expect(onOpenFinalizarTab).toHaveBeenCalled();
  });

  it("mantém o topo inicial limpo quando o chat ainda não abriu um caso", () => {
    const { getByTestId, queryByText } = render(
      <ThreadHeaderControls
        chatHasActiveCase={false}
        finalizacaoDisponivel={false}
        filaOfflineTotal={0}
        headerSafeTopInset={0}
        keyboardVisible={false}
        mesaAcessoPermitido
        notificacoesMesaLaudoAtual={0}
        notificacoesNaoLidas={0}
        onOpenChatTab={jest.fn()}
        onOpenFinalizarTab={jest.fn()}
        onOpenHistory={jest.fn()}
        onOpenMesaTab={jest.fn()}
        onOpenNewChat={jest.fn()}
        onOpenSettings={jest.fn()}
        vendoFinalizacao={false}
        vendoMesa={false}
      />,
    );

    expect(getByTestId("open-new-chat-button")).toBeTruthy();
    expect(queryByText("Novo chat")).toBeNull();
    expect(queryByText("Primeiro envio cria o caso.")).toBeNull();
    expect(queryByText("Caso no 1º envio")).toBeNull();
  });
});
