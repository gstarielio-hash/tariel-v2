const mockRenderSettingsSheetBody = jest.fn(() => null);
const mockHandleConfirmarSettingsSheet = jest.fn().mockResolvedValue(undefined);
const mockBuildSettingsSheetBodyRenderer = jest.fn(
  (_params: unknown) => mockRenderSettingsSheetBody,
);

jest.mock("./buildSettingsSheetBodyRenderer", () => ({
  buildSettingsSheetBodyRenderer: (params: unknown) =>
    mockBuildSettingsSheetBodyRenderer(params),
}));

jest.mock("./buildSettingsSheetConfirmAction", () => ({
  buildSettingsSheetConfirmAction: jest.fn(
    () => mockHandleConfirmarSettingsSheet,
  ),
}));

import { buildInspectorRootSettingsSheetProps } from "./buildInspectorRootSettingsSheetProps";

function criarInput() {
  return {
    accountState: {
      contaTelefone: "(11) 99999-0000",
      email: "inspetor@tariel.test",
      emailAtualConta: "conta@tariel.test",
      perfilExibicao: "Gabriel",
      perfilFotoHint: "GT",
      perfilFotoUri: "https://tariel.test/avatar.png",
      perfilNome: "Gabriel Tariel",
      planoAtual: "Pro" as const,
      provedoresConectados: [],
      session: {
        bootstrap: {
          usuario: {
            id: 33,
            nome_completo: "Gabriel Tariel",
            email: "inspetor@tariel.test",
            telefone: "(11) 99999-0000",
            foto_perfil_url: "",
            empresa_nome: "Empresa A",
            empresa_id: 7,
            nivel_acesso: 1,
            allowed_portals: ["inspetor", "revisor", "cliente"],
            commercial_operating_model: "mobile_single_operator",
            commercial_operating_model_label:
              "Mobile principal com operador único",
            identity_runtime_note:
              "A conta principal do tenant pode receber multiplas superficies conforme o cadastro definido no Admin-CEO.",
            portal_switch_links: [
              {
                portal: "inspetor",
                label: "Inspetor web/mobile",
                url: "/app/",
              },
              {
                portal: "revisor",
                label: "Mesa Avaliadora",
                url: "/revisao/painel",
              },
            ],
          },
        },
      } as never,
      sessaoAtual: null,
      telefoneDraft: "(11) 99999-0000",
    },
    actionsState: {
      compartilharTextoExportado: jest.fn(),
      formatarHorarioAtividade: jest.fn().mockReturnValue("agora"),
      formatarStatusReautenticacao: jest.fn().mockReturnValue("ativa"),
      handleAlternarArtigoAjuda: jest.fn(),
      handleAlternarIntegracaoExterna: jest.fn(),
      handleConfirmarSettingsSheetReauth: jest.fn().mockResolvedValue(true),
      onAbrirPortalContinuation: jest.fn().mockResolvedValue(undefined),
      handleRemoverScreenshotBug: jest.fn(),
      handleSelecionarModeloIa: jest.fn(),
      handleSelecionarScreenshotBug: jest.fn(),
      handleSincronizarIntegracaoExterna: jest.fn(),
      handleToggleUploadArquivos: jest.fn(),
      notificarConfiguracaoConcluida: jest.fn(),
      onRegistrarEventoSegurancaLocal: jest.fn(),
    },
    appState: {
      apiEnvironmentLabel: "api.tariel.test",
      appBuildLabel: "2026.03.30",
      appName: "Tariel Inspetor",
      supportChannelLabel: "WhatsApp",
    },
    backendState: {
      enviarFotoPerfilNoBackend: jest.fn(),
      enviarRelatoSuporteNoBackend: jest.fn(),
      onAtualizarPerfilContaNoBackend: jest.fn(),
      onAtualizarSenhaContaNoBackend: jest.fn(),
      onPingApi: jest.fn(),
      onUpdateAccountPhone: jest.fn(),
    },
    baseState: {
      artigosAjudaFiltrados: [
        {
          id: "help-1",
          title: "Primeiros passos",
          category: "Conta",
          estimatedRead: "2 min",
          summary: "Resumo",
          body: "Conteúdo",
        },
      ],
      integracoesConectadasTotal: 0,
      integracoesDisponiveisTotal: 1,
      resumoAtualizacaoApp: "Atualizado",
      resumoFilaSuporteLocal: "Sem pendências",
      resumoSuporteApp: "Operacional",
      ultimaVerificacaoAtualizacaoLabel: "Hoje",
      workspaceResumoConfiguracao: "Tariel",
    } as never,
    draftState: {
      artigoAjudaExpandidoId: "",
      bugAttachmentDraft: null,
      bugDescriptionDraft: "",
      bugEmailDraft: "",
      buscaAjuda: "",
      cartaoAtual: "Mastercard final 1034" as const,
      confirmarSenhaDraft: "",
      feedbackDraft: "",
      integracaoSincronizandoId: "",
      integracoesExternas: [],
      modeloIa: "equilibrado" as const,
      nomeAutomaticoConversas: true,
      nomeCompletoDraft: "Gabriel Tariel",
      nomeExibicaoDraft: "Gabriel",
      novaSenhaDraft: "",
      novoEmailDraft: "",
      reauthReason: "",
      reautenticacaoExpiraEm: "",
      retencaoDados: "90 dias",
      salvarHistoricoConversas: true,
      senhaAtualDraft: "",
      settingsSheet: {
        kind: "updates",
        title: "Atualizações",
        subtitle: "Resumo",
      } as const,
      statusApi: "online" as const,
      statusAtualizacaoApp: "up-to-date",
      ultimoTicketSuporte: null,
      uploadArquivosAtivo: true,
    },
    settersState: {
      onSetBugAttachmentDraft: jest.fn(),
      onSetBugDescriptionDraft: jest.fn(),
      onSetBugEmailDraft: jest.fn(),
      onSetBuscaAjuda: jest.fn(),
      onSetCartaoAtual: jest.fn(),
      onSetConfirmarSenhaDraft: jest.fn(),
      onSetEmailAtualConta: jest.fn(),
      onSetFeedbackDraft: jest.fn(),
      onSetFilaSuporteLocal: jest.fn(),
      onSetNomeAutomaticoConversas: jest.fn(),
      onSetNomeCompletoDraft: jest.fn(),
      onSetNomeExibicaoDraft: jest.fn(),
      onSetNovaSenhaDraft: jest.fn(),
      onSetNovoEmailDraft: jest.fn(),
      onSetPerfilExibicao: jest.fn(),
      onSetPerfilFotoHint: jest.fn(),
      onSetPerfilFotoUri: jest.fn(),
      onSetPerfilNome: jest.fn(),
      onSetPlanoAtual: jest.fn(),
      onSetProvedoresConectados: jest.fn(),
      onSetSenhaAtualDraft: jest.fn(),
      onSetSession: jest.fn(),
      onSetSettingsSheetLoading: jest.fn(),
      onSetSettingsSheetNotice: jest.fn(),
      onSetStatusApi: jest.fn(),
      onSetStatusAtualizacaoApp: jest.fn(),
      onSetTelefoneDraft: jest.fn(),
      onSetUltimaVerificacaoAtualizacao: jest.fn(),
    },
  };
}

describe("buildInspectorRootSettingsSheetProps", () => {
  it("monta render e confirmação do settings sheet a partir dos grupos do root", async () => {
    const input = criarInput();
    const props = buildInspectorRootSettingsSheetProps(input);

    expect(props.renderSettingsSheetBody()).toBeNull();

    await props.handleConfirmarSettingsSheet();

    expect(mockBuildSettingsSheetBodyRenderer).toHaveBeenCalledWith(
      expect.objectContaining({
        resumoContaAcesso:
          "Empresa #7 • Inspetor web/mobile + Mesa Avaliadora + Admin-Cliente • Mobile principal com operador único",
        resumoOperacaoApp:
          "Admin-Cliente da empresa, chat do inspetor, mesa avaliadora, histórico, fila offline e configurações do app.",
        identityRuntimeNote:
          "A conta principal do tenant pode receber multiplas superficies conforme o cadastro definido no Admin-CEO.",
        portalContinuationLinks: [
          expect.objectContaining({
            label: "Inspetor web/mobile",
            destinationPath: "/app/",
          }),
          expect.objectContaining({
            label: "Mesa Avaliadora",
            destinationPath: "/revisao/painel",
          }),
        ],
        topicosAjudaResumo: "acesso, inspeção, mesa e offline",
      }),
    );
    expect(mockRenderSettingsSheetBody).toHaveBeenCalledTimes(1);
    expect(mockHandleConfirmarSettingsSheet).toHaveBeenCalledTimes(1);
    expect(
      input.actionsState.handleConfirmarSettingsSheetReauth,
    ).not.toHaveBeenCalled();
  });
});
