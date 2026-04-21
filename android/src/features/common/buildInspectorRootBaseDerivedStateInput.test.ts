import { buildInspectorRootBaseDerivedStateInput } from "./buildInspectorRootBaseDerivedStateInput";

describe("buildInspectorRootBaseDerivedStateInput", () => {
  it("monta o input do estado derivado compartilhado a partir dos grupos do app raiz", () => {
    const buildHistorySections = jest.fn();
    const formatarHorarioAtividade = jest.fn();
    const formatarTipoTemplateLaudo = jest.fn();
    const obterEscalaDensidade = jest.fn();
    const obterEscalaFonte = jest.fn();
    const podeEditarConversaNoComposer = jest.fn();
    const previewChatLiberadoParaConversa = jest.fn();

    const input = buildInspectorRootBaseDerivedStateInput({
      shellState: {
        abaAtiva: "chat",
        buscaAjuda: "",
        buscaConfiguracoes: "",
        colorScheme: "light",
        filtroConfiguracoes: "todos",
        keyboardHeight: 0,
        session: null,
        statusApi: "online",
        statusAtualizacaoApp: "Atualizado",
        ultimaVerificacaoAtualizacao: "2026-03-30T10:00:00.000Z",
      },
      chatState: {
        anexoMesaRascunho: null,
        anexoRascunho: null,
        carregandoConversa: false,
        carregandoMesa: false,
        conversa: null,
        enviandoMensagem: false,
        enviandoMesa: false,
        mensagem: "",
        mensagemMesa: "",
        mensagensMesa: [],
        preparandoAnexo: false,
      },
      historyAndOfflineState: {
        buscaHistorico: "",
        eventosSeguranca: [],
        filaOffline: [],
        filaSuporteLocal: [],
        filtroEventosSeguranca: "todos",
        filtroFilaOffline: "all",
        filtroHistorico: "todos",
        fixarConversas: true,
        historicoOcultoIds: [],
        laudosDisponiveis: [],
        notificacoes: [],
        pendenciaFilaProntaParaReenvio: jest.fn().mockReturnValue(false),
        prioridadePendenciaOffline: jest.fn().mockReturnValue(0),
      },
      settingsState: {
        arquivosPermitidos: true,
        biometriaPermitida: true,
        cameraPermitida: true,
        codigosRecuperacao: [],
        contaTelefone: "",
        corDestaque: "#123456",
        densidadeInterface: "confortável",
        email: "inspetor@example.com",
        emailAtualConta: "inspetor@example.com",
        estiloResposta: "padrão",
        idiomaResposta: "Português",
        integracoesExternas: [],
        lockTimeout: "5 minutos",
        microfonePermitido: true,
        modeloIa: "equilibrado",
        mostrarConteudoNotificacao: true,
        mostrarSomenteNovaMensagem: false,
        notificacoesPermitidas: true,
        ocultarConteudoBloqueado: false,
        perfilExibicao: "Inspetor",
        perfilNome: "Gabriel",
        planoAtual: "Pro",
        provedoresConectados: [],
        reautenticacaoStatus: "Confirmada",
        recoveryCodesEnabled: false,
        salvarHistoricoConversas: true,
        settingsDrawerPage: "overview",
        settingsDrawerSection: "all",
        sessoesAtivas: [],
        somNotificacao: "Ping",
        sincronizacaoDispositivos: true,
        tamanhoFonte: "médio",
        temaApp: "sistema",
        twoFactorEnabled: false,
        twoFactorMethod: "authenticator",
        uploadArquivosAtivo: true,
      },
      helperState: {
        buildHistorySections,
        formatarHorarioAtividade,
        formatarTipoTemplateLaudo,
        obterEscalaDensidade,
        obterEscalaFonte,
        podeEditarConversaNoComposer,
        previewChatLiberadoParaConversa,
      },
    });

    expect(input.abaAtiva).toBe("chat");
    expect(input.statusApi).toBe("online");
    expect(input.temaApp).toBe("sistema");
    expect(input.email).toBe("inspetor@example.com");
    expect(input.buildHistorySections).toBe(buildHistorySections);
    expect(input.obterEscalaFonte).toBe(obterEscalaFonte);
  });
});
