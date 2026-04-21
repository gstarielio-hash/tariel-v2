import { renderHook } from "@testing-library/react-native";

const mockHandleEditarPerfil = jest.fn();
const mockHandleCentralAjuda = jest.fn();

jest.mock("./useSettingsEntryActions", () => ({
  useSettingsEntryActions: jest.fn(() => ({
    handleUploadFotoPerfil: jest.fn(),
    handleEditarPerfil: mockHandleEditarPerfil,
    handleAlterarEmail: jest.fn(),
    handleAlterarSenha: jest.fn(),
    handleGerenciarPlano: jest.fn(),
    handleHistoricoPagamentos: jest.fn(),
    handleGerenciarPagamento: jest.fn(),
    handleAbrirModeloIa: jest.fn(),
    handleIntegracoesExternas: jest.fn(),
    handlePluginsIa: jest.fn(),
    handlePermissoes: jest.fn(),
    handlePoliticaPrivacidade: jest.fn(),
    handleCentralAjuda: mockHandleCentralAjuda,
    handleReportarProblema: jest.fn(),
    handleEnviarFeedback: jest.fn(),
    handleAbrirSobreApp: jest.fn(),
    handleAlternarArtigoAjuda: jest.fn(),
    handleTermosUso: jest.fn(),
    handleLicencas: jest.fn(),
  })),
}));

import { useSettingsEntryActions } from "./useSettingsEntryActions";
import { useInspectorRootSettingsEntryActions } from "./useInspectorRootSettingsEntryActions";

function criarInput() {
  return {
    accountState: {
      contaTelefone: "(11) 99999-0000",
      emailAtualConta: "inspetor@tariel.test",
      fallbackEmail: "fallback@tariel.test",
      perfilExibicao: "Gabriel",
      perfilNome: "Gabriel Tariel",
    },
    actionState: {
      abrirSheetConfiguracao: jest.fn(),
      handleAbrirPaginaConfiguracoes: jest.fn(),
    },
    setterState: {
      setArtigoAjudaExpandidoId: jest.fn(),
      setBugAttachmentDraft: jest.fn(),
      setBugDescriptionDraft: jest.fn(),
      setBugEmailDraft: jest.fn(),
      setBuscaAjuda: jest.fn(),
      setConfirmarSenhaDraft: jest.fn(),
      setFeedbackDraft: jest.fn(),
      setNomeCompletoDraft: jest.fn(),
      setNomeExibicaoDraft: jest.fn(),
      setNovaSenhaDraft: jest.fn(),
      setNovoEmailDraft: jest.fn(),
      setSenhaAtualDraft: jest.fn(),
      setTelefoneDraft: jest.fn(),
    },
  };
}

describe("useInspectorRootSettingsEntryActions", () => {
  it("encapsula a composição do trilho de entrada das configurações sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() =>
      useInspectorRootSettingsEntryActions(input),
    );
    const mockedHook = jest.mocked(useSettingsEntryActions);

    result.current.handleEditarPerfil();
    result.current.handleCentralAjuda();

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        perfilNome: input.accountState.perfilNome,
        emailAtualConta: input.accountState.emailAtualConta,
        abrirSheetConfiguracao: input.actionState.abrirSheetConfiguracao,
        setNomeCompletoDraft: input.setterState.setNomeCompletoDraft,
      }),
    );
    expect(mockHandleEditarPerfil).toHaveBeenCalledTimes(1);
    expect(mockHandleCentralAjuda).toHaveBeenCalledTimes(1);
  });
});
