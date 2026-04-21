const mockHandleConfirmarAcaoCritica = jest.fn();
const mockHandleExportarDados = jest.fn();
const mockHandleSelecionarModeloIa = jest.fn();

jest.mock("./buildSettingsConfirmAndExportActions", () => ({
  buildSettingsConfirmAndExportActions: jest.fn(() => ({
    handleConfirmarAcaoCritica: mockHandleConfirmarAcaoCritica,
    handleExportarDados: mockHandleExportarDados,
    handleSelecionarModeloIa: mockHandleSelecionarModeloIa,
  })),
}));

import { buildSettingsConfirmAndExportActions } from "./buildSettingsConfirmAndExportActions";
import { buildInspectorRootSettingsConfirmExportActions } from "./buildInspectorRootSettingsConfirmExportActions";

function criarInput() {
  return {
    accountState: {
      email: "inspetor@tariel.test",
      emailAtualConta: "conta@tariel.test",
      perfilExibicao: "Gabriel",
      perfilNome: "Gabriel Tariel",
      planoAtual: "Pro",
      resumoContaAcesso: "Empresa #7 • Inspetor web/mobile + Mesa Avaliadora",
      identityRuntimeNote:
        "A conta principal do tenant pode receber multiplas superficies conforme o cadastro definido no Admin-CEO.",
      portalContinuationSummary:
        "Inspetor web/mobile (/app/) • Mesa Avaliadora (/revisao/painel)",
      workspaceResumoConfiguracao: "Empresa A • Operação padrão",
    },
    actionState: {
      abrirFluxoReautenticacao: jest.fn(),
      abrirSheetConfiguracao: jest.fn(),
      compartilharTextoExportado: jest.fn().mockResolvedValue(true),
      executarExclusaoContaLocal: jest.fn().mockResolvedValue(undefined),
      fecharConfirmacaoConfiguracao: jest.fn(),
      fecharSheetConfiguracao: jest.fn(),
      onCreateNewConversation: jest.fn(),
      onIsValidAiModel: jest.fn().mockReturnValue(true),
      onRegistrarEventoSegurancaLocal: jest.fn(),
      reautenticacaoAindaValida: jest.fn().mockReturnValue(true),
      serializarPayloadExportacao: jest.fn().mockReturnValue("{}"),
    },
    collectionState: {
      eventosSeguranca: [],
      integracoesExternas: [],
      laudosDisponiveis: [],
      notificacoes: [],
    },
    draftState: {
      confirmSheet: null,
      confirmTextDraft: "CONFIRMAR",
      modeloIa: "equilibrado" as const,
      reautenticacaoExpiraEm: "2026-03-30T12:00:00Z",
    },
    preferenceState: {
      compartilharMelhoriaIa: true,
      corDestaque: "azul",
      densidadeInterface: "compacta",
      economiaDados: false,
      emailsAtivos: true,
      estiloResposta: "objetivo",
      idiomaResposta: "pt-BR",
      memoriaIa: true,
      mostrarConteudoNotificacao: true,
      mostrarSomenteNovaMensagem: false,
      notificaPush: true,
      notificaRespostas: true,
      ocultarConteudoBloqueado: false,
      retencaoDados: "90 dias",
      salvarHistoricoConversas: true,
      tamanhoFonte: "media",
      temaApp: "sistema",
      usoBateria: "equilibrado",
      vibracaoAtiva: true,
    },
    settersState: {
      limparCachePorPrivacidade: jest.fn((cache) => cache),
      onSetAnexoMesaRascunho: jest.fn(),
      onSetAnexoRascunho: jest.fn(),
      onSetBuscaHistorico: jest.fn(),
      onSetCacheLeitura: jest.fn(),
      onSetConversa: jest.fn(),
      onSetLaudosDisponiveis: jest.fn(),
      onSetMensagem: jest.fn(),
      onSetMensagemMesa: jest.fn(),
      onSetMensagensMesa: jest.fn(),
      onSetModeloIa: jest.fn(),
      onSetNotificacoes: jest.fn(),
      onSetPreviewAnexoImagem: jest.fn(),
    },
  };
}

describe("buildInspectorRootSettingsConfirmExportActions", () => {
  it("encapsula o trilho de confirm/export do root sem alterar os handlers finais", () => {
    const input = criarInput();
    const props = buildInspectorRootSettingsConfirmExportActions(input);
    const mockedBuilder = jest.mocked(buildSettingsConfirmAndExportActions);

    props.handleConfirmarAcaoCritica();
    props.handleExportarDados("JSON");
    props.handleSelecionarModeloIa("equilibrado");

    expect(mockedBuilder).toHaveBeenCalledWith(
      expect.objectContaining({
        email: input.accountState.email,
        modeloIa: input.draftState.modeloIa,
        integracoesExternas: input.collectionState.integracoesExternas,
        compartilharTextoExportado:
          input.actionState.compartilharTextoExportado,
        portalContinuationSummary: input.accountState.portalContinuationSummary,
        onSetConversa: input.settersState.onSetConversa,
      }),
    );
    expect(mockHandleConfirmarAcaoCritica).toHaveBeenCalledTimes(1);
    expect(mockHandleExportarDados).toHaveBeenCalledWith("JSON");
    expect(mockHandleSelecionarModeloIa).toHaveBeenCalledWith("equilibrado");
  });
});
