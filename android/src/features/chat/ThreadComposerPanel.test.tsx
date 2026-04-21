import { fireEvent, render } from "@testing-library/react-native";

import {
  ThreadComposerPanel,
  type ThreadComposerPanelProps,
} from "./ThreadComposerPanel";

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

function createProps(
  overrides: Partial<ThreadComposerPanelProps> = {},
): ThreadComposerPanelProps {
  return {
    visible: true,
    keyboardVisible: false,
    canReopen: false,
    onReopen: jest.fn(),
    qualityGateVisible: false,
    qualityGateLoading: false,
    qualityGateSubmitting: false,
    qualityGatePayload: null,
    qualityGateReason: "",
    qualityGateNotice: "",
    statusApi: "online",
    onCloseQualityGate: jest.fn(),
    onConfirmQualityGate: jest.fn(),
    onSetQualityGateReason: jest.fn(),
    vendoMesa: false,
    erroMesa: "",
    mensagemMesaReferenciaAtiva: null,
    onLimparReferenciaMesaAtiva: jest.fn(),
    anexoMesaRascunho: null,
    onClearAnexoMesaRascunho: jest.fn(),
    podeAbrirAnexosMesa: false,
    podeUsarComposerMesa: false,
    mensagemMesa: "",
    onSetMensagemMesa: jest.fn(),
    placeholderMesa: "Responder para a mesa",
    podeEnviarMesa: false,
    onEnviarMensagemMesa: jest.fn(),
    enviandoMesa: false,
    showVoiceInputAction: false,
    onVoiceInputPress: jest.fn(),
    voiceInputEnabled: false,
    composerNotice: "",
    anexoRascunho: null,
    onClearAnexoRascunho: jest.fn(),
    podeAbrirAnexosChat: true,
    podeAcionarComposer: true,
    mensagem: "",
    onSetMensagem: jest.fn(),
    placeholderComposer: "Escreva sua mensagem",
    podeEnviarComposer: false,
    onEnviarMensagem: jest.fn(),
    enviandoMensagem: false,
    onAbrirSeletorAnexo: jest.fn(),
    dynamicComposerInputStyle: undefined,
    accentColor: "#0f766e",
    ...overrides,
  };
}

describe("ThreadComposerPanel", () => {
  it("remove o placeholder do composer de chat", () => {
    const { getByTestId } = render(
      <ThreadComposerPanel
        {...createProps({
          placeholderComposer: "Escreva sua mensagem",
        })}
      />,
    );

    expect(getByTestId("chat-composer-input").props.placeholder).toBe("");
  });

  it("expõe markers estáveis para rascunho de imagem no chat", () => {
    const { getByTestId } = render(
      <ThreadComposerPanel
        {...createProps({
          anexoRascunho: {
            kind: "image",
            label: "evidencia.png",
            resumo: "Imagem pronta para a conversa.",
            previewUri: "file:///tmp/evidencia.png",
          },
        })}
      />,
    );

    expect(getByTestId("chat-attachment-draft-card")).toBeTruthy();
    expect(getByTestId("chat-attachment-draft-kind-image")).toBeTruthy();
    expect(getByTestId("chat-attachment-draft-title").props.children).toBe(
      "evidencia.png",
    );
    expect(
      getByTestId("chat-attachment-draft-description").props.children,
    ).toBe("Imagem pronta para a conversa.");
  });

  it("mantém ids estáveis para documento na mesa e permite limpar o rascunho", () => {
    const onClearAnexoMesaRascunho = jest.fn();
    const { getByTestId } = render(
      <ThreadComposerPanel
        {...createProps({
          vendoMesa: true,
          anexoMesaRascunho: {
            kind: "document",
            label: "laudo.pdf",
            resumo: "Documento pronto para a mesa.",
          },
          onClearAnexoMesaRascunho,
          podeAbrirAnexosMesa: true,
          podeUsarComposerMesa: true,
        })}
      />,
    );

    expect(getByTestId("mesa-attachment-draft-card")).toBeTruthy();
    expect(getByTestId("mesa-attachment-draft-kind-document")).toBeTruthy();

    fireEvent.press(getByTestId("mesa-attachment-draft-remove"));

    expect(onClearAnexoMesaRascunho).toHaveBeenCalledTimes(1);
  });
});
