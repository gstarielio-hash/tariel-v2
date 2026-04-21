import {
  buildInspectorAuthenticatedLayoutScreenProps,
  buildInspectorLoginScreenProps,
} from "./buildInspectorScreenProps";

describe("buildInspectorScreenProps", () => {
  it("monta os props autenticados a partir do estado derivado e do contexto da thread", () => {
    const setIntroVisivel = jest.fn();
    const setMensagem = jest.fn();
    const setMensagemMesa = jest.fn();
    const setAnexoRascunho = jest.fn();
    const setAnexoMesaRascunho = jest.fn();
    const handleAbrirQualityGate = jest.fn();
    const handleConfirmarQualityGate = jest.fn();

    const props = buildInspectorAuthenticatedLayoutScreenProps({
      baseState: {
        accentColor: "#FF6B00",
        appGradientColors: ["#111111", "#222222", "#333333"],
        chatKeyboardVerticalOffset: 24,
        conversaAtiva: null,
        conversaVazia: true,
        conversasOcultasTotal: 3,
        dynamicComposerInputStyle: {
          fontSize: 16,
          lineHeight: 22,
          minHeight: 48,
          paddingVertical: 12,
        },
        dynamicMessageBubbleStyle: {
          paddingHorizontal: 14,
          paddingVertical: 10,
        },
        dynamicMessageTextStyle: {
          fontSize: 15,
          lineHeight: 22,
        },
        filaOfflineOrdenada: [
          {
            id: "offline-1",
            channel: "chat",
            operation: "message",
            laudoId: 12,
            text: "Pendência",
            createdAt: "2026-03-30T10:00:00.000Z",
            title: "Pendência",
            attachment: null,
            referenceMessageId: null,
            qualityGateDecision: null,
            attempts: 0,
            lastAttemptAt: "",
            lastError: "",
            nextRetryAt: "",
            aiMode: "detalhado",
            aiSummary: "",
            aiMessagePrefix: "",
          },
        ],
        fontScale: 1,
        headerSafeTopInset: 32,
        historicoAgrupadoFinal: [],
        historicoVazioTexto: "Sem histórico",
        historicoVazioTitulo: "Nada por aqui",
        keyboardAvoidingBehavior: "padding",
        keyboardVisible: false,
        laudoSelecionadoId: 12,
        loginKeyboardBottomPadding: 18,
        loginKeyboardVerticalOffset: 12,
        mesaAcessoPermitido: true,
        mesaDisponivel: true,
        mesaIndisponivelDescricao:
          "Envie o primeiro registro no chat para liberar este espaço.",
        mesaIndisponivelTitulo: "Mesa disponível após o primeiro laudo",
        mesaTemMensagens: true,
        mensagensVisiveis: [],
        nomeUsuarioExibicao: "Gabriel",
        notificacoesNaoLidas: 2,
        placeholderComposer: "Digite sua mensagem",
        placeholderMesa: "Responder à mesa",
        podeAbrirAnexosChat: true,
        podeAbrirAnexosMesa: true,
        podeAcionarComposer: true,
        podeEnviarComposer: true,
        podeEnviarMesa: true,
        podeUsarComposerMesa: true,
        threadKeyboardPaddingBottom: 44,
        vendoFinalizacao: false,
        vendoMesa: true,
      },
      composerState: {
        anexoAbrindoChave: "",
        anexoMesaRascunho: null,
        anexoRascunho: null,
        carregandoConversa: false,
        carregandoMesa: false,
        enviandoMensagem: false,
        enviandoMesa: false,
        erroMesa: "",
        handleAbrirQualityGate,
        handleAbrirSeletorAnexo: jest.fn(),
        handleConfirmarQualityGate,
        handleEnviarMensagem: jest.fn(),
        handleEnviarMensagemMesa: jest.fn(),
        handleFecharQualityGate: jest.fn(),
        handleReabrir: jest.fn(),
        limparReferenciaMesaAtiva: jest.fn(),
        mensagem: "",
        mensagemMesa: "",
        mensagemMesaReferenciaAtiva: null,
        qualityGateLoading: false,
        qualityGateNotice: "",
        qualityGatePayload: null,
        qualityGateReason: "",
        qualityGateSubmitting: false,
        qualityGateVisible: false,
        setAnexoMesaRascunho,
        setAnexoRascunho,
        setMensagem,
        setMensagemMesa,
        setQualityGateReason: jest.fn(),
      },
      historyState: {
        buscaHistorico: "",
        fecharHistorico: jest.fn(),
        handleAbrirHistorico: jest.fn(),
        handleExcluirConversaHistorico: jest.fn(),
        handleSelecionarHistorico: jest.fn(),
        historicoAberto: false,
        historicoDrawerX: {} as never,
        historyDrawerPanResponder: { panHandlers: {} } as never,
        historyEdgePanResponder: { panHandlers: { test: "ok" } } as never,
        setHistorySearchFocused: jest.fn(),
        setBuscaHistorico: jest.fn(),
      },
      sessionState: {
        scrollRef: { current: null },
        sessionAccessToken: "token-auth-123",
        setAbaAtiva: jest.fn(),
      },
      shellState: {
        animacoesAtivas: true,
        composerNotice: "Modo IA ativo",
        configuracoesAberta: false,
        drawerOverlayOpacity: {} as never,
        erroConversa: "",
        erroLaudos: "",
        fecharPaineisLaterais: jest.fn(),
        introVisivel: true,
        onVoiceInputPress: jest.fn(),
        sessionModalsStackProps: {} as never,
        statusApi: "online",
        setIntroVisivel,
        settingsDrawerPanelProps: {
          accentColor: "#FF6B00",
          appBuildChannel: "preview",
          appVersionLabel: "1.0.0",
          cardSections: [],
          currentPage: "overview",
          currentSection: "overview",
          drawerOffsetX: {} as never,
          inOverview: true,
          isPageVisible: jest.fn(),
          isSectionVisible: jest.fn(),
          onBackToOverview: jest.fn(),
          onClose: jest.fn(),
          onOpenOfflineQueue: jest.fn(),
          onOpenPage: jest.fn(),
          onOpenSection: jest.fn(),
          pageSections: [],
          panResponder: { panHandlers: {} } as never,
          printDarkMode: false,
          sectionMenuActive: false,
          subtitle: "",
          themeSummary: "",
          title: "Configurações",
          totalVisibleSections: 0,
          visibleGroups: [],
        } as never,
        settingsEdgePanResponder: { panHandlers: {} } as never,
      },
      speechState: {
        entradaPorVoz: true,
        microfonePermitido: false,
        speechEnabled: true,
      },
      threadContextState: {
        chipsContextoThread: [],
        laudoContextDescription: "Descrição",
        threadContextLayout: "default",
        laudoContextTitle: "Laudo 12",
        mostrarContextoThread: true,
        threadActions: [],
        threadInsights: [],
        threadSpotlight: {
          icon: "message-reply-text-outline",
          label: "Mesa ativa",
          tone: "accent",
        },
      },
      threadState: {
        abrirReferenciaNoChat: jest.fn(),
        chaveAnexo: jest.fn().mockReturnValue("att-1"),
        definirReferenciaMesaAtiva: jest.fn(),
        handleAbrirAnexo: jest.fn(),
        handleAbrirConfiguracoes: jest.fn(),
        handleAbrirNovoChat: jest.fn(),
        handleExecutarComandoRevisaoMobile: jest.fn(),
        handleUsarPerguntaPreLaudo: jest.fn(),
        mensagemChatDestacadaId: 77,
        mensagensMesa: [],
        notificacoesMesaLaudoAtual: 1,
        obterResumoReferenciaMensagem: jest.fn().mockReturnValue("Resumo"),
        registrarLayoutMensagemChat: jest.fn(),
      },
    });

    expect(props.accentColor).toBe("#FF6B00");
    expect(props.historyDrawerPanelProps.conversasOcultasTotal).toBe(3);
    expect(props.historyEdgePanHandlers).toEqual({ test: "ok" });
    expect(props.threadComposerPanelProps.showVoiceInputAction).toBe(true);
    expect(props.threadComposerPanelProps.voiceInputEnabled).toBe(false);
    expect(props.threadConversationPaneProps.onAbrirQualityGate).toBe(
      handleAbrirQualityGate,
    );
    expect(props.threadConversationPaneProps.sessionAccessToken).toBe(
      "token-auth-123",
    );
    expect(props.threadContextVisible).toBe(true);
  });

  it("mantem o card de contexto visivel no chat do inspetor quando a thread pede contexto", () => {
    const props = buildInspectorAuthenticatedLayoutScreenProps({
      baseState: {
        accentColor: "#FF6B00",
        appGradientColors: ["#111111", "#222222", "#333333"],
        chatKeyboardVerticalOffset: 24,
        conversaAtiva: null,
        conversaVazia: true,
        conversasOcultasTotal: 0,
        dynamicComposerInputStyle: {
          fontSize: 16,
          lineHeight: 22,
          minHeight: 48,
          paddingVertical: 12,
        },
        dynamicMessageBubbleStyle: {
          paddingHorizontal: 14,
          paddingVertical: 10,
        },
        dynamicMessageTextStyle: {
          fontSize: 15,
          lineHeight: 22,
        },
        filaOfflineOrdenada: [],
        fontScale: 1,
        headerSafeTopInset: 32,
        historicoAgrupadoFinal: [],
        historicoVazioTexto: "Sem histórico",
        historicoVazioTitulo: "Nada por aqui",
        keyboardAvoidingBehavior: "padding",
        keyboardVisible: false,
        laudoSelecionadoId: null,
        loginKeyboardBottomPadding: 18,
        loginKeyboardVerticalOffset: 12,
        mesaAcessoPermitido: false,
        mesaDisponivel: false,
        mesaIndisponivelDescricao:
          "O pacote atual não inclui a mesa avaliadora no app.",
        mesaIndisponivelTitulo: "Mesa indisponível para esta conta",
        mesaTemMensagens: false,
        mensagensVisiveis: [],
        nomeUsuarioExibicao: "Gabriel",
        notificacoesNaoLidas: 0,
        placeholderComposer: "Digite sua mensagem",
        placeholderMesa: "Responder à mesa",
        podeAbrirAnexosChat: true,
        podeAbrirAnexosMesa: false,
        podeAcionarComposer: true,
        podeEnviarComposer: true,
        podeEnviarMesa: false,
        podeUsarComposerMesa: false,
        threadKeyboardPaddingBottom: 44,
        vendoFinalizacao: false,
        vendoMesa: false,
      },
      composerState: {
        anexoAbrindoChave: "",
        anexoMesaRascunho: null,
        anexoRascunho: null,
        carregandoConversa: false,
        carregandoMesa: false,
        enviandoMensagem: false,
        enviandoMesa: false,
        erroMesa: "",
        handleAbrirQualityGate: jest.fn(),
        handleAbrirSeletorAnexo: jest.fn(),
        handleConfirmarQualityGate: jest.fn(),
        handleEnviarMensagem: jest.fn(),
        handleEnviarMensagemMesa: jest.fn(),
        handleFecharQualityGate: jest.fn(),
        handleReabrir: jest.fn(),
        limparReferenciaMesaAtiva: jest.fn(),
        mensagem: "",
        mensagemMesa: "",
        mensagemMesaReferenciaAtiva: null,
        qualityGateLoading: false,
        qualityGateNotice: "",
        qualityGatePayload: null,
        qualityGateReason: "",
        qualityGateSubmitting: false,
        qualityGateVisible: false,
        setAnexoMesaRascunho: jest.fn(),
        setAnexoRascunho: jest.fn(),
        setMensagem: jest.fn(),
        setMensagemMesa: jest.fn(),
        setQualityGateReason: jest.fn(),
      },
      historyState: {
        buscaHistorico: "",
        fecharHistorico: jest.fn(),
        handleAbrirHistorico: jest.fn(),
        handleExcluirConversaHistorico: jest.fn(),
        handleSelecionarHistorico: jest.fn(),
        historicoAberto: false,
        historicoDrawerX: {} as never,
        historyDrawerPanResponder: { panHandlers: {} } as never,
        historyEdgePanResponder: { panHandlers: {} } as never,
        setHistorySearchFocused: jest.fn(),
        setBuscaHistorico: jest.fn(),
      },
      sessionState: {
        scrollRef: { current: null },
        sessionAccessToken: "token-auth-456",
        setAbaAtiva: jest.fn(),
      },
      shellState: {
        animacoesAtivas: true,
        composerNotice: "",
        configuracoesAberta: false,
        drawerOverlayOpacity: {} as never,
        erroConversa: "",
        erroLaudos: "",
        fecharPaineisLaterais: jest.fn(),
        introVisivel: false,
        onVoiceInputPress: jest.fn(),
        sessionModalsStackProps: {} as never,
        statusApi: "online",
        setIntroVisivel: jest.fn(),
        settingsDrawerPanelProps: {} as never,
        settingsEdgePanResponder: { panHandlers: {} } as never,
      },
      speechState: {
        entradaPorVoz: false,
        microfonePermitido: false,
        speechEnabled: false,
      },
      threadContextState: {
        chipsContextoThread: [],
        laudoContextDescription:
          "Converse normalmente ou inicie uma inspecao guiada.",
        threadContextLayout: "entry_chooser",
        laudoContextTitle: "Nova inspeção",
        mostrarContextoThread: true,
        threadActions: [],
        threadInsights: [],
        threadSpotlight: {
          icon: "plus-circle-outline",
          label: "Nova inspeção",
          tone: "success",
        },
      },
      threadState: {
        abrirReferenciaNoChat: jest.fn(),
        chaveAnexo: jest.fn().mockReturnValue("att-chat"),
        definirReferenciaMesaAtiva: jest.fn(),
        handleAbrirAnexo: jest.fn(),
        handleAbrirConfiguracoes: jest.fn(),
        handleAbrirNovoChat: jest.fn(),
        handleExecutarComandoRevisaoMobile: jest.fn(),
        handleUsarPerguntaPreLaudo: jest.fn(),
        mensagemChatDestacadaId: null,
        mensagensMesa: [],
        notificacoesMesaLaudoAtual: 0,
        obterResumoReferenciaMensagem: jest.fn().mockReturnValue(""),
        registrarLayoutMensagemChat: jest.fn(),
      },
    });

    expect(props.threadContextVisible).toBe(true);
    expect(props.vendoFinalizacao).toBe(false);
    expect(props.vendoMesa).toBe(false);
  });

  it("monta os props de login com o estado base compartilhado", () => {
    const setEmail = jest.fn();
    const setMostrarSenha = jest.fn();
    const setSenha = jest.fn();
    const setIntroVisivel = jest.fn();

    const props = buildInspectorLoginScreenProps({
      authActions: {
        handleEsqueciSenha: jest.fn(),
        handleLogin: jest.fn(),
        handleLoginSocial: jest.fn(),
      },
      authState: {
        carregando: false,
        email: "inspetor@tariel.test",
        emailInputRef: { current: null },
        entrando: false,
        erro: "",
        loginStage: "idle",
        mostrarSenha: false,
        senha: "segredo",
        senhaInputRef: { current: null },
        statusApi: "online",
        setEmail,
        setMostrarSenha,
        setSenha,
      },
      baseState: {
        accentColor: "#FF6B00",
        appGradientColors: ["#111111", "#222222", "#333333"],
        fontScale: 1.1,
        keyboardAvoidingBehavior: "padding",
        keyboardVisible: true,
        loginKeyboardBottomPadding: 24,
        loginKeyboardVerticalOffset: 14,
      },
      presentationState: {
        animacoesAtivas: true,
        automationDiagnosticsEnabled: true,
        introVisivel: true,
      },
      setIntroVisivel,
    });

    props.onEmailChange("novo@tariel.test");
    props.onSenhaChange("outra");
    props.onToggleMostrarSenha();
    props.onIntroDone();

    expect(props.loginKeyboardBottomPadding).toBe(24);
    expect(props.accentColor).toBe("#FF6B00");
    expect(props.loginAutomationProbeLabel).toContain("pilot_login_probe");
    expect(setEmail).toHaveBeenCalledWith("novo@tariel.test");
    expect(setSenha).toHaveBeenCalledWith("outra");
    expect(setMostrarSenha).toHaveBeenCalled();
    expect(setIntroVisivel).toHaveBeenCalledWith(false);
  });
});
