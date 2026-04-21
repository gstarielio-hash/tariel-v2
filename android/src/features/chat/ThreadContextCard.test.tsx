import { fireEvent, render } from "@testing-library/react-native";

import { ThreadContextCard } from "./ThreadContextCard";

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

describe("ThreadContextCard", () => {
  it("apresenta o chooser inicial em torno do chat first", () => {
    const onStartNr35 = jest.fn();
    const { getAllByText, getByText, queryByText } = render(
      <ThreadContextCard
        visible
        layout="entry_chooser"
        eyebrow=""
        title="Por onde começar?"
        description="Escolha um modo para iniciar."
        spotlight={{
          label: "Chat livre como padrão",
          tone: "success",
          icon: "message-processing-outline",
        }}
        chips={[]}
        actions={[
          {
            key: "chat-free-start",
            label: "Chat livre",
            tone: "success",
            icon: "message-processing-outline",
            onPress: jest.fn(),
          },
          {
            key: "guided-template-nr35_linha_vida",
            label: "NR35 Linha de Vida",
            tone: "accent",
            icon: "ladder",
            onPress: onStartNr35,
            testID: "guided-inspection-template-nr35_linha_vida-button",
          },
          {
            key: "guided-template-nr13",
            label: "NR13",
            tone: "accent",
            icon: "gauge",
            onPress: jest.fn(),
            testID: "guided-inspection-template-nr13-button",
          },
        ]}
        insights={[]}
      />,
    );

    expect(getByText("Por onde começar?")).toBeTruthy();
    expect(getAllByText("Chat livre").length).toBeGreaterThan(0);
    expect(queryByText("Escolha um modo para iniciar.")).toBeNull();
    expect(getByText("Fotos, contexto e análise flexível.")).toBeTruthy();
    expect(getByText("Chat guiado")).toBeTruthy();
    expect(queryByText("Laudo no 1º envio")).toBeNull();
    expect(queryByText("Chat do inspetor")).toBeNull();
  });

  it("abre a lista de templates guiados e dispara o template escolhido", () => {
    const onStartNr35 = jest.fn();
    const { getByTestId, getByText, queryByText } = render(
      <ThreadContextCard
        visible
        layout="entry_chooser"
        eyebrow=""
        title="Por onde começar?"
        description="Escolha um modo para iniciar."
        spotlight={{
          label: "IA recomenda guiado",
          tone: "accent",
          icon: "robot-outline",
        }}
        chips={[]}
        actions={[
          {
            key: "chat-free-start",
            label: "Chat livre",
            tone: "success",
            icon: "message-processing-outline",
            onPress: jest.fn(),
          },
          {
            key: "guided-template-nr35_linha_vida",
            label: "NR35 Linha de Vida",
            tone: "accent",
            icon: "ladder",
            onPress: onStartNr35,
            testID: "guided-inspection-template-nr35_linha_vida-button",
          },
          {
            key: "guided-template-nr13",
            label: "NR13",
            tone: "accent",
            icon: "gauge",
            onPress: jest.fn(),
            testID: "guided-inspection-template-nr13-button",
          },
        ]}
        insights={[]}
      />,
    );

    expect(queryByText("NR35 Linha de Vida")).toBeNull();
    expect(getByText("Template técnico com coleta orientada.")).toBeTruthy();

    fireEvent.press(getByTestId("guided-entry-open-button"));

    expect(getByText("Template do chat guiado")).toBeTruthy();
    expect(
      getByText("Selecione agora o template técnico desejado."),
    ).toBeTruthy();
    expect(getByText("NR35 Linha de Vida")).toBeTruthy();
    expect(getByText("NR13")).toBeTruthy();

    fireEvent.press(
      getByTestId("guided-inspection-template-nr35_linha_vida-button"),
    );

    expect(onStartNr35).toHaveBeenCalledTimes(1);
  });

  it("aceita controle externo da abertura dos templates guiados", () => {
    const onGuidedTemplatesVisibleChange = jest.fn();
    const { getByTestId, getByText } = render(
      <ThreadContextCard
        visible
        layout="entry_chooser"
        guidedTemplatesVisible
        eyebrow=""
        title="Por onde começar?"
        description="Escolha um modo para iniciar."
        spotlight={{
          label: "IA recomenda guiado",
          tone: "accent",
          icon: "robot-outline",
        }}
        chips={[]}
        actions={[
          {
            key: "chat-free-start",
            label: "Chat livre",
            tone: "success",
            icon: "message-processing-outline",
            onPress: jest.fn(),
          },
          {
            key: "guided-template-nr35_linha_vida",
            label: "NR35 Linha de Vida",
            tone: "accent",
            icon: "ladder",
            onPress: jest.fn(),
            testID: "guided-inspection-template-nr35_linha_vida-button",
          },
        ]}
        insights={[]}
        onGuidedTemplatesVisibleChange={onGuidedTemplatesVisibleChange}
      />,
    );

    expect(getByText("Template do chat guiado")).toBeTruthy();

    fireEvent.press(getByTestId("guided-entry-open-button"));

    expect(onGuidedTemplatesVisibleChange).toHaveBeenCalledWith(false);
  });

  it("renderiza o agregado operacional no chooser inicial quando há reemissão pendente", () => {
    const { getAllByText, getByText } = render(
      <ThreadContextCard
        visible
        layout="entry_chooser"
        eyebrow=""
        title="Por onde começar?"
        description="Escolha um modo para iniciar."
        spotlight={{
          label: "Chat livre como padrão",
          tone: "success",
          icon: "message-processing-outline",
        }}
        chips={[
          {
            key: "governance-reissue",
            label: "2 reemissões recomendadas",
            tone: "danger",
            icon: "alert-circle-outline",
          },
        ]}
        actions={[
          {
            key: "chat-free-start",
            label: "Chat livre",
            tone: "success",
            icon: "message-processing-outline",
            onPress: jest.fn(),
          },
        ]}
        insights={[
          {
            key: "governance-reissue",
            label: "Governança",
            value: "2 reemissões recomendadas",
            detail:
              "Há 2 casos com PDF oficial divergente no mobile. Revise o histórico ou a central de atividade para reemitir os documentos.",
            tone: "danger",
            icon: "alert-circle-outline",
          },
        ]}
      />,
    );

    expect(getAllByText("2 reemissões recomendadas").length).toBeGreaterThan(0);
    expect(getByText("Governança")).toBeTruthy();
    expect(
      getByText(
        "Há 2 casos com PDF oficial divergente no mobile. Revise o histórico ou a central de atividade para reemitir os documentos.",
      ),
    ).toBeTruthy();
  });

  it("abre compacto por padrão e expande detalhes sob demanda", () => {
    const { getByTestId, getByText, queryByText } = render(
      <ThreadContextCard
        visible
        eyebrow="Chat do inspetor"
        title="Inspecao Geral"
        description="A IA guia a coleta no chat enquanto voce confirma as evidencias obrigatorias do template."
        spotlight={{
          label: "IA conduzindo coleta",
          tone: "accent",
          icon: "robot-outline",
        }}
        chips={[
          {
            key: "steps",
            label: "0/5 etapas",
            tone: "accent",
            icon: "counter",
          },
          {
            key: "template",
            label: "Inspecao Geral",
            tone: "muted",
            icon: "clipboard-text-outline",
          },
          {
            key: "mesa",
            label: "Mesa requerida",
            tone: "danger",
            icon: "alert-outline",
          },
        ]}
        actions={[
          {
            key: "guided-advance",
            label: "Avancar etapa",
            tone: "accent",
            icon: "arrow-right",
            onPress: jest.fn(),
          },
          {
            key: "guided-stop",
            label: "Voltar ao chat",
            tone: "muted",
            icon: "message-outline",
            onPress: jest.fn(),
          },
          {
            key: "finish",
            label: "Finalizar caso",
            tone: "success",
            icon: "check",
            onPress: jest.fn(),
          },
        ]}
        insights={[
          {
            key: "progress",
            label: "Progresso",
            value: "0/5",
            detail: "5 etapas restantes.",
            tone: "accent",
            icon: "format-list-checks",
          },
          {
            key: "bundle",
            label: "Pre-laudo",
            value: "0/5 blocos",
            detail: "Checklist guiado e fotos obrigatorias pendentes.",
            tone: "muted",
            icon: "file-document-outline",
          },
          {
            key: "mesa",
            label: "Mesa",
            value: "Obrigatória",
            detail: "A politica ativa exige revisão humana.",
            tone: "danger",
            icon: "account-check-outline",
          },
        ]}
      />,
    );

    expect(getByText("Detalhes")).toBeTruthy();
    expect(getByText("Avancar etapa")).toBeTruthy();
    expect(queryByText("Mesa requerida")).toBeNull();
    expect(queryByText("Finalizar caso")).toBeNull();
    expect(queryByText("A politica ativa exige revisão humana.")).toBeNull();

    fireEvent.press(getByTestId("thread-context-toggle"));

    expect(getByText("Mesa requerida")).toBeTruthy();
    expect(getByText("Finalizar caso")).toBeTruthy();
    expect(getByText("A politica ativa exige revisão humana.")).toBeTruthy();
  });

  it("renderiza Finalizar como superfície dedicada sem depender do toggle", () => {
    const { getAllByText, getByText, queryByTestId } = render(
      <ThreadContextCard
        visible
        layout="finalization"
        eyebrow="Finalizacao do caso"
        title="Linha de vida cobertura A"
        description="Revise a rota de aprovação, o pacote documental e a emissão antes de concluir."
        spotlight={{
          label: "Pronto para decisão humana",
          tone: "success",
          icon: "check-decagram-outline",
        }}
        chips={[
          {
            key: "outcome",
            label: "Saída: laudo formal",
            tone: "accent",
            icon: "file-document-outline",
          },
          {
            key: "review",
            label: "Mesa obrigatória",
            tone: "danger",
            icon: "clipboard-alert-outline",
          },
        ]}
        actions={[
          {
            key: "open-mesa",
            label: "Abrir Mesa",
            tone: "danger",
            icon: "clipboard-alert-outline",
            onPress: jest.fn(),
          },
          {
            key: "finish",
            label: "Finalizar caso",
            tone: "success",
            icon: "check",
            onPress: jest.fn(),
          },
        ]}
        insights={[
          {
            key: "delivery",
            label: "Entrega final",
            value: "PDF governado",
            detail:
              "A entrega estavel deste fluxo e o PDF final revisado por humano.",
            tone: "accent",
            icon: "file-document-outline",
          },
          {
            key: "validation",
            label: "Validacao humana",
            value: "Mesa obrigatória",
            detail:
              "A politica ativa exige passagem pela Mesa antes da emissão.",
            tone: "danger",
            icon: "account-check-outline",
          },
        ]}
      />,
    );

    expect(getByText("Abrir Mesa")).toBeTruthy();
    expect(getByText("Finalizar caso")).toBeTruthy();
    expect(getAllByText("PDF governado").length).toBeGreaterThan(0);
    expect(queryByTestId("thread-context-toggle")).toBeNull();
  });
});
