import { render } from "@testing-library/react-native";

import { SettingsExperienceNotificationsSection } from "./SettingsExperienceSections";
import { SettingsPlanSheetContent } from "./SettingsSheetAccountContent";
import {
  SettingsFeedbackSheetContent,
  SettingsHelpSheetContent,
} from "./SettingsSheetSupportContent";

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

describe("settings governance surfaces", () => {
  it("oculta a categoria Mesa quando o grant não existe", () => {
    const { getByText, queryByText } = render(
      <SettingsExperienceNotificationsSection
        chatCategoryEnabled
        criticalAlertsEnabled
        emailsAtivos
        mesaCategoryEnabled
        notificaPush
        notificaRespostas
        notificacoesPermitidas
        onAbrirPermissaoNotificacoes={jest.fn()}
        onSetChatCategoryEnabled={jest.fn()}
        onSetCriticalAlertsEnabled={jest.fn()}
        onSetEmailsAtivos={jest.fn()}
        onSetMesaCategoryEnabled={jest.fn()}
        onSetNotificaRespostas={jest.fn()}
        onSetSomNotificacao={jest.fn()}
        onSetSystemCategoryEnabled={jest.fn()}
        onToggleNotificaPush={jest.fn()}
        onToggleVibracao={jest.fn()}
        showMesaCategory={false}
        somNotificacao="Ping"
        systemCategoryEnabled
        vibracaoAtiva
      />,
    );

    expect(getByText("Categoria Chat")).toBeTruthy();
    expect(queryByText("Categoria Mesa")).toBeNull();
  });

  it("mostra acesso governado e operação ativa no sheet de plano", () => {
    const onAbrirPortalContinuation = jest.fn();
    const { getByText } = render(
      <SettingsPlanSheetContent
        identityRuntimeNote="A conta principal do tenant pode receber multiplas superficies conforme o cadastro definido no Admin-CEO."
        onAbrirPortalContinuation={onAbrirPortalContinuation}
        planoAtual="Plus"
        portalContinuationLinks={[
          {
            label: "Mesa Avaliadora",
            url: "https://tariel-web-free.onrender.com/revisao/painel",
            destinationPath: "/revisao/painel",
          },
        ]}
        resumoContaAcesso="Empresa #7 • Inspetor web/mobile + Admin-Cliente"
        resumoOperacaoApp="Admin-Cliente da empresa, chat do inspetor, histórico, fila offline e configurações do app."
      />,
    );

    expect(getByText("Acesso governado")).toBeTruthy();
    expect(
      getByText("Empresa #7 • Inspetor web/mobile + Admin-Cliente"),
    ).toBeTruthy();
    expect(
      getByText(
        "Admin-Cliente da empresa, chat do inspetor, histórico, fila offline e configurações do app.",
      ),
    ).toBeTruthy();
    expect(getByText("Runtime de identidade")).toBeTruthy();
    expect(
      getByText("Continuidade web disponível em /revisao/painel."),
    ).toBeTruthy();
  });

  it("usa o contexto real de grants nas folhas de ajuda e feedback", () => {
    const help = render(
      <SettingsHelpSheetContent
        artigoAjudaExpandidoId=""
        artigosAjudaFiltrados={[]}
        buscaAjuda=""
        emailAtualConta="conta@tariel.test"
        emailLogin="inspetor@tariel.test"
        formatarHorarioAtividade={() => "agora"}
        onAlternarArtigoAjuda={jest.fn()}
        onBuscaAjudaChange={jest.fn()}
        resumoAtualizacaoApp="Atualizado"
        resumoContaAcesso="Empresa #7 • Inspetor web/mobile + Mesa Avaliadora"
        resumoFilaSuporteLocal="Sem pendências"
        resumoOperacaoApp="chat do inspetor, mesa avaliadora, histórico, fila offline e configurações do app."
        resumoSuporteApp="Preview"
        topicosAjudaResumo="inspeção, mesa, offline e segurança"
        ultimoTicketSuporte={null}
      />,
    );

    expect(
      help.getByPlaceholderText(
        "Buscar por inspeção, mesa, offline e segurança...",
      ),
    ).toBeTruthy();
    expect(help.getByText("Escopo do acesso")).toBeTruthy();
    expect(
      help.getByText("Empresa #7 • Inspetor web/mobile + Mesa Avaliadora"),
    ).toBeTruthy();

    const feedback = render(
      <SettingsFeedbackSheetContent
        feedbackDraft=""
        formatarHorarioAtividade={() => "agora"}
        onFeedbackDraftChange={jest.fn()}
        resumoContaAcesso="Empresa #7 • Inspetor web/mobile + Mesa Avaliadora"
        resumoFilaSuporteLocal="Sem pendências"
        resumoOperacaoApp="chat do inspetor, mesa avaliadora, histórico, fila offline e configurações do app."
        ultimoTicketSuporte={null}
      />,
    );

    expect(
      feedback.getByText(
        "chat do inspetor, mesa avaliadora, histórico, fila offline e configurações do app.",
      ),
    ).toBeTruthy();
    expect(
      feedback.getByText("Empresa #7 • Inspetor web/mobile + Mesa Avaliadora"),
    ).toBeTruthy();
  });
});
