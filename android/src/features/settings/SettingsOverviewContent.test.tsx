import { fireEvent, render } from "@testing-library/react-native";

import { SettingsOverviewContent } from "./SettingsOverviewContent";

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

function createProps() {
  return {
    contaEmailLabel: "conta@tariel.test",
    contaTelefoneLabel: "(11) 99999-0000",
    corDestaqueResumoConfiguracao: "Laranja",
    detalheGovernancaConfiguracao:
      "PDF oficial divergente em 2 casos disponíveis no mobile.",
    iniciaisPerfilConfiguracao: "GT",
    nomeUsuarioExibicao: "Gabriel",
    onAbrirPaginaConfiguracoes: jest.fn(),
    onFecharConfiguracoes: jest.fn(),
    onLogout: jest.fn(),
    onReportarProblema: jest.fn(),
    onUploadFotoPerfil: jest.fn(),
    perfilFotoUri: "",
    planoResumoConfiguracao: "Plano Pro",
    reemissoesRecomendadasTotal: 2,
    resumoGovernancaConfiguracao: "2 casos com reemissão recomendada",
    settingsPrintDarkMode: false,
    temaResumoConfiguracao: "Claro",
    workspaceResumoConfiguracao: "Tariel • Operador único",
  };
}

describe("SettingsOverviewContent", () => {
  it("resume conta e atalhos do mobile no overview", () => {
    const props = createProps();
    const { getAllByText, getByTestId } = render(
      <SettingsOverviewContent {...props} />,
    );

    expect(getByTestId("settings-overview-summary-card")).toBeTruthy();
    expect(getByTestId("settings-overview-signal-workspace")).toBeTruthy();
    expect(getByTestId("settings-overview-signal-theme")).toBeTruthy();
    expect(getByTestId("settings-overview-signal-contact")).toBeTruthy();
    expect(getByTestId("settings-overview-signal-governance")).toBeTruthy();
    expect(getByTestId("settings-overview-account-card")).toBeTruthy();
    expect(getByTestId("settings-overview-plan-card")).toBeTruthy();
    expect(getByTestId("settings-overview-contact-card")).toBeTruthy();
    expect(getByTestId("settings-overview-governance")).toBeTruthy();
    expect(getAllByText("Plano Pro").length).toBeGreaterThan(0);
    expect(getAllByText("Tariel • Operador único").length).toBeGreaterThan(0);
    expect(
      getAllByText("2 casos com reemissão recomendada").length,
    ).toBeGreaterThan(0);
  });

  it("abre o destino certo a partir dos cards rápidos", () => {
    const props = createProps();
    const { getByTestId } = render(<SettingsOverviewContent {...props} />);

    fireEvent.press(getByTestId("settings-overview-security-card"));

    expect(props.onAbrirPaginaConfiguracoes).toHaveBeenCalledWith("seguranca");
  });

  it("fecha o drawer e solicita logout ao sair", () => {
    const props = createProps();
    const { getByTestId } = render(<SettingsOverviewContent {...props} />);

    fireEvent.press(getByTestId("settings-print-sair-row"));

    expect(props.onFecharConfiguracoes).toHaveBeenCalled();
    expect(props.onLogout).toHaveBeenCalled();
  });
});
