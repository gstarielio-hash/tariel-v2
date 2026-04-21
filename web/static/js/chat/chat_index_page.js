// ==========================================
// TARIEL CONTROL TOWER — CHAT_INDEX_PAGE.JS
// Página principal do chat.
// Responsável por:
// - modal de nova inspeção
// - barra de sessão ativa
// - ações rápidas
// - destaque visual do textarea
// - banner de resposta da engenharia
// - SSE de notificações da página
// ==========================================

(function () {
    "use strict";

    const InspectorRuntime = window.TarielInspectorRuntime || null;
    if (typeof InspectorRuntime?.guardOnce === "function") {
        if (!InspectorRuntime.guardOnce("chat_index_page")) return;
    } else {
        if (window.__TARIEL_CHAT_INDEX_PAGE_WIRED__) return;
        window.__TARIEL_CHAT_INDEX_PAGE_WIRED__ = true;
    }

    // =========================================================
    // CONSTANTES
    // =========================================================
    const ROTA_SSE_NOTIFICACOES = "/app/api/notificacoes/sse";
    const TEMPO_BANNER_MS = 8000;
    const TEMPO_RECONEXAO_SSE_MS = 5000;
    const BREAKPOINT_LAYOUT_INSPETOR_COMPACTO = 1199;
    const sharedGlobals =
        InspectorRuntime?.resolveSharedGlobals?.() || {
            perf: window.TarielPerf || window.TarielCore?.TarielPerf || null,
            caseLifecycle: window.TarielCaseLifecycle,
        };
    const PERF = sharedGlobals.perf;
    const CaseLifecycle = sharedGlobals.caseLifecycle;

    if (!CaseLifecycle) {
        return;
    }

    PERF?.noteModule?.("chat/chat_index_page.js", {
        readyState: document.readyState,
    });

    const NOMES_TEMPLATES = {
        avcb: "Laudo AVCB (Projeto e Conformidade)",
        cbmgo: "Checklist Bombeiros GO (CMAR / Estrutura)",
        nr12maquinas: "Laudo de Adequação NR-12",
        nr13: "Inspeção NR-13 (Caldeiras e Vasos)",
        rti: "RTI - Instalações Elétricas",
        pie: "PIE - Prontuário Elétrico",
        spda: "Inspeção SPDA — NBR 5419",
        padrao: "Inspeção Geral",
    };

    const CONFIG_STATUS_MESA = {
        pronta: {
            icone: "support_agent",
            texto: "Mesa pronta",
        },
        canal_ativo: {
            icone: "alternate_email",
            texto: "Canal da mesa ativo",
        },
        aguardando: {
            icone: "hourglass_top",
            texto: "Aguardando mesa",
        },
        respondeu: {
            icone: "mark_chat_read",
            texto: "Mesa respondeu",
        },
        pendencia_aberta: {
            icone: "assignment_late",
            texto: "Pendência aberta",
        },
        offline: {
            icone: "wifi_off",
            texto: "Mesa indisponível",
        },
    };

    const CONFIG_CONEXAO_MESA_WIDGET = {
        conectado: "Conectado",
        reconectando: "Reconectando",
        offline: "Offline",
    };

    const EM_PRODUCAO =
        window.location.hostname !== "localhost" &&
        window.location.hostname !== "127.0.0.1";
    const LIMITE_RECONEXAO_SSE_OFFLINE = 3;
    const MAX_BYTES_ANEXO_MESA = 12 * 1024 * 1024;
    const CHAVE_FORCE_HOME_LANDING = "tariel_force_home_landing";
    const CHAVE_RETOMADA_HOME_PENDENTE = "tariel_workspace_retomada_home_pendente";
    const CHAVE_CONTEXTO_VISUAL_LAUDOS = "tariel_workspace_contexto_visual_laudos";
    const LIMITE_CONTEXTO_VISUAL_LAUDOS_STORAGE = 50;
    const MENSAGEM_MESA_EXIGE_INSPECAO =
        "A conversa com a mesa avaliadora só é permitida após iniciar uma nova inspeção.";
    const MIME_ANEXOS_MESA_PERMITIDOS = new Set([
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]);

    const COMANDOS_SLASH = [
        {
            id: "resumir",
            titulo: "Resumir coleta",
            descricao: "Gera um resumo técnico curto com fatos confirmados, lacunas e próximos passos.",
            prompt: "Resuma a coleta atual em tópicos objetivos, destacando fatos confirmados, riscos observados, lacunas de evidência e próximo passo recomendado.",
            atalho: "/resumir",
            sugestao: true,
            icone: "notes",
        },
        {
            id: "pendencias",
            titulo: "Mapear pendências",
            descricao: "Lista o que ainda falta para fechar a inspeção com prioridade operacional.",
            prompt: "Liste as pendências atuais desta inspeção em ordem de prioridade operacional, indicando o que falta coletar, o motivo e o impacto no envio para a mesa.",
            atalho: "/pendencias",
            sugestao: true,
            icone: "assignment_late",
        },
        {
            id: "proxima-pergunta",
            titulo: "Próxima pergunta",
            descricao: "Sugere a melhor próxima pergunta técnica para avançar a coleta.",
            prompt: "Com base no histórico atual, qual é a próxima pergunta técnica mais útil para avançar esta inspeção com qualidade auditável?",
            atalho: "/proxima-pergunta",
            sugestao: true,
            icone: "help",
        },
        {
            id: "plano-acao",
            titulo: "Plano de ação",
            descricao: "Organiza um plano de coleta com sequência prática para o inspetor.",
            prompt: "Monte um plano de ação curto para concluir esta inspeção, com sequência prática de coleta, anexos necessários e pontos que precisam de validação da mesa.",
            atalho: "/plano-acao",
            sugestao: false,
            icone: "checklist",
        },
        {
            id: "nao-conformidades",
            titulo: "Não conformidades",
            descricao: "Extrai potenciais não conformidades e classifica por criticidade.",
            prompt: "A partir do histórico atual, identifique potenciais não conformidades, classifique por criticidade e aponte quais evidências sustentam cada uma.",
            atalho: "/nao-conformidades",
            sugestao: true,
            icone: "warning",
        },
        {
            id: "gerar-conclusao",
            titulo: "Gerar conclusão",
            descricao: "Redige uma conclusão preliminar profissional com ressalvas auditáveis.",
            prompt: "Redija uma conclusão preliminar profissional desta inspeção, separando condições observadas, limitações de evidência, pendências e recomendação para envio à mesa.",
            atalho: "/gerar-conclusao",
            sugestao: true,
            icone: "article",
        },
        {
            id: "mesa",
            titulo: "Enviar resumo para a mesa",
            descricao: "Abre o canal da mesa com uma minuta pronta para validação.",
            prompt: "",
            atalho: "/mesa",
            sugestao: true,
            icone: "support_agent",
        },
    ];

    const SUGESTOES_ENTRADA_ASSISTENTE = Object.freeze([
        {
            id: "guided-inspection",
            titulo: "Iniciar inspeção guiada",
            prioridade: "primary",
            prompt: "Quero iniciar uma inspeção guiada. Me ajude a estruturar o contexto inicial e o que devo coletar primeiro.",
        },
        {
            id: "structure-context",
            titulo: "Estruturar contexto",
            prioridade: "secondary",
            prompt: "Vou te passar o contexto do equipamento e do cenário. Estruture a sessão técnica e diga o que preciso observar primeiro.",
        },
        {
            id: "technical-question",
            titulo: "Dúvida técnica",
            prioridade: "secondary",
            prompt: "Tenho uma dúvida técnica. Me responda de forma objetiva, auditável e com os critérios que preciso verificar em campo.",
        },
    ]);

    const CONTEXTO_WORKSPACE_ASSISTENTE = Object.freeze({
        title: "Assistente Tariel IA",
        subtitle: "Conversa inicial • nenhum laudo ativo",
        statusBadge: "CHAT LIVRE",
    });

    const COPY_WORKSPACE_STAGE = Object.freeze({
        assistant: {
            eyebrow: "Chat livre",
            headline: "Novo Chat",
            description:
                "Descreva o equipamento, o cenário ou a dúvida técnica. A primeira mensagem abre o contexto do laudo.",
            placeholder: "Descreva o equipamento, o cenário ou a dúvida técnica",
            contextTitle: "Envie a primeira mensagem",
            contextStatus: "A IA organiza o laudo enquanto voce descreve o cenario.",
        },
        inspection: {
            eyebrow: "Sessão técnica em andamento",
            headline: "Registro Técnico",
            description:
                "Documente evidências, anexe arquivos e interaja com o assistente técnico.",
            placeholder: "Descreva a evidência, anexe arquivos ou use / para comandos",
        },
        focusedConversation: {
            eyebrow: "Chat livre",
            headline: "Conversa com a IA",
            description:
                "Continue a conversa normalmente. O fluxo funcional do laudo segue o comportamento atual em segundo plano.",
            placeholder: "Escreva a continuação da conversa",
            contextTitle: "Conversa com a IA",
            contextStatus: "A conversa segue focada no histórico e no composer.",
        },
    });

    // =========================================================
    // ESTADO LOCAL DA PÁGINA
    // =========================================================
    const estado = {
        tipoTemplateAtivo: "padrao",
        statusMesa: "pronta",
        laudoAtualId: null,
        estadoRelatorio: "sem_relatorio",
        modoInspecaoUI: "workspace",
        workspaceStage: "assistant",
        inspectorScreen: "assistant_landing",
        inspectorBaseScreen: "assistant_landing",
        threadTab: "conversa",
        forceHomeLanding: false,
        homeActionVisible: false,
        overlayOwner: "",
        assistantLandingFirstSendPending: false,
        freeChatConversationActive: false,
        workspaceVisualContext: { ...CONTEXTO_WORKSPACE_ASSISTENTE },
        contextoVisualPorLaudo: {},
        ultimoStatusRelatorioPayload: null,
        workspaceRailExpanded: true,
        workspaceRailAccordionState: Object.create(null),
        workspaceRailViewKey: "",
        pendenciasItens: [],
        carregandoPendencias: false,
        laudoPendenciasAtual: null,
        qtdPendenciasAbertas: 0,
        filtroPendencias: "abertas",
        paginaPendenciasAtual: 1,
        tamanhoPaginaPendencias: 25,
        totalPendenciasFiltradas: 0,
        totalPendenciasExibidas: 0,
        temMaisPendencias: false,
        pendenciasAbortController: null,
        pendenciasRealCount: 0,
        pendenciasFilteredCount: 0,
        pendenciasLoading: false,
        pendenciasEmpty: false,
        pendenciasSynthetic: false,
        pendenciasHonestEmpty: false,
        pendenciasError: false,
        fonteSSE: null,
        timerBanner: null,
        timerReconexaoSSE: null,
        ultimoElementoFocado: null,
        iniciandoInspecao: false,
        finalizandoInspecao: false,
        mesaWidgetAberto: false,
        mesaWidgetCarregando: false,
        mesaWidgetMensagens: [],
        mesaWidgetCursor: null,
        mesaWidgetTemMais: false,
        mesaWidgetAbortController: null,
        mesaWidgetReferenciaAtiva: null,
        mesaWidgetAnexoPendente: null,
        mesaWidgetNaoLidas: 0,
        mesaWidgetConexao: "conectado",
        systemEventsBound: false,
        tentativasReconexaoSSE: 0,
        timerFecharMesaWidget: null,
        retomadaHomePendente: null,
        modalNovaInspecaoPrePrompt: "",
        entryModePreferenceDefault: "auto_recommended",
        entryModeRememberLastCaseMode: false,
        entryModeLastCaseMode: null,
        entryModePreference: "auto_recommended",
        entryModeEffective: "chat_first",
        entryModeReason: "default_product_fallback",
        termoBuscaSidebar: "",
        sidebarLaudosTab: "recentes",
        chatBuscaTermo: "",
        chatFiltroTimeline: "todos",
        historyTypeFilter: "todos",
        chatResultados: 0,
        chatStatusIA: {
            status: "pronto",
            texto: "Assistente pronto",
        },
        atualizandoPainelWorkspaceDerivado: false,
        atualizarPainelWorkspaceDerivadoPendente: false,
        contextoFixado: [],
        historicoPrompts: [],
        indiceHistoricoPrompt: -1,
        rascunhoHistoricoPrompt: "",
        slashIndiceAtivo: 0,
        historyRealCount: 0,
        historyEmpty: true,
        historySynthetic: false,
        historyHonestEmpty: false,
        historyRenderedItems: [],
        historyCanonicalItems: [],
        snapshotEstadoInspector: null,
        snapshotEstadoInspectorOrigem: {},
        divergenciasEstadoInspector: {},
    };

    // Compatibilidade com trechos legados do projeto.
    window.tipoTemplateAtivo = estado.tipoTemplateAtivo;

    // =========================================================
    // REFERÊNCIAS DOS ELEMENTOS DA PÁGINA
    // =========================================================
    const el = {
        modal: document.getElementById("modal-nova-inspecao"),
        overlayHost: document.getElementById("inspetor-overlay-host"),
        btnAbrirModal: document.getElementById("btn-abrir-modal-novo"),
        btnFecharModal: document.querySelector("#modal-nova-inspecao .btn-fechar-modal"),
        btnConfirmarInspecao: document.getElementById("btn-confirmar-inspecao"),
        selectTemplate: document.getElementById("select-template-inspecao"),
        selectTemplateCustom: document.getElementById("select-template-custom"),
        btnSelectTemplateCustom: document.getElementById("btn-select-template-custom"),
        valorSelectTemplateCustom: document.getElementById("valor-select-template-custom"),
        painelSelectTemplateCustom: document.getElementById("painel-select-template-custom"),
        listaSelectTemplateCustom: document.getElementById("lista-select-template-custom"),
        inputClienteInspecao: document.getElementById("input-cliente-inspecao"),
        inputUnidadeInspecao: document.getElementById("input-unidade-inspecao"),
        inputLocalInspecao: document.getElementById("input-local-inspecao"),
        textareaObjetivoInspecao: document.getElementById("textarea-objetivo-inspecao"),
        entryModeInputs: Array.from(document.querySelectorAll('input[name="entry-mode-preference"]')),
        modalEntryModeSummary: document.getElementById("modal-entry-mode-summary"),
        previewNomeInspecao: document.getElementById("preview-nome-inspecao"),
        btnEditarNomeInspecao: document.getElementById("btn-editar-nome-inspecao"),
        inputNomeInspecao: document.getElementById("input-nome-inspecao"),
        btnCancelarModalInspecao: document.getElementById("btn-cancelar-modal-inspecao"),
        modalGateQualidade: document.getElementById("modal-gate-qualidade"),
        btnFecharModalGateQualidade: document.getElementById("btn-fechar-modal-gate-qualidade"),
        btnEntendiGateQualidade: document.getElementById("btn-entendi-gate-qualidade"),
        btnPreencherGateQualidade: document.getElementById("btn-gate-preencher-no-chat"),
        tituloTemplateGateQualidade: document.getElementById("titulo-gate-template"),
        textoGateQualidadeResumo: document.getElementById("texto-gate-qualidade-resumo"),
        blocoGateRoteiroTemplate: document.getElementById("bloco-gate-roteiro-template"),
        tituloGateRoteiroTemplate: document.getElementById("titulo-gate-roteiro-template"),
        textoGateRoteiroTemplate: document.getElementById("texto-gate-roteiro-template"),
        listaGateRoteiroTemplate: document.getElementById("lista-gate-roteiro-template"),
        listaGateFaltantes: document.getElementById("lista-gate-faltantes"),
        listaGateChecklist: document.getElementById("lista-gate-checklist"),
        blocoGateOverrideHumano: document.getElementById("bloco-gate-override-humano"),
        textoGateOverrideHumano: document.getElementById("texto-gate-override-humano"),
        listaGateOverrideCasos: document.getElementById("lista-gate-override-casos"),
        textareaGateOverrideJustificativa: document.getElementById("textarea-gate-override-justificativa"),
        textoGateOverrideResponsabilidade: document.getElementById("texto-gate-override-responsabilidade"),
        btnGateOverrideContinuar: document.getElementById("btn-gate-override-continuar"),

        telaBoasVindas: document.getElementById("tela-boas-vindas"),
        painelChat: document.getElementById("painel-chat"),
        portalScreenRoot: document.querySelector('[data-screen-root="portal"]'),
        workspaceScreenRoot: document.querySelector('[data-screen-root="workspace"]'),
        mesaWidgetScreenRoot: document.querySelector('[data-screen-root="mesa-widget"]'),
        workspaceAssistantViewRoot: document.querySelector('[data-workspace-view-root="assistant_landing"]'),
        workspaceHistoryViewRoot: document.querySelector('[data-workspace-view-root="inspection_history"]'),
        workspaceRecordViewRoot: document.querySelector('[data-workspace-view-root="inspection_record"]'),
        workspaceConversationViewRoot: document.querySelector('[data-workspace-view-root="inspection_conversation"]'),
        workspaceMesaViewRoot: document.querySelector('[data-workspace-view-root="inspection_mesa"]'),
        workspaceHistoryRoot: document.querySelector("[data-workspace-history-root]"),
        workspaceHeader: document.querySelector("[data-workspace-header]"),
        chatThreadToolbar: document.querySelector(".chat-thread-toolbar"),
        threadNav: document.querySelector(".thread-nav"),
        chatDashboardRail: document.querySelector(".chat-dashboard-rail"),
        workspaceTituloLaudo: document.getElementById("workspace-titulo-laudo"),
        workspaceSubtituloLaudo: document.getElementById("workspace-subtitulo-laudo"),
        workspaceStatusBadge: document.getElementById("workspace-status-badge"),
        workspaceEyebrow: document.getElementById("workspace-eyebrow"),
        workspaceHeadline: document.getElementById("workspace-headline"),
        workspaceDescription: document.getElementById("workspace-description"),
        workspaceEntryModeNote: document.getElementById("workspace-entry-mode-note"),
        workspaceSummaryState: document.getElementById("workspace-summary-state"),
        workspaceSummaryEvidencias: document.getElementById("workspace-summary-evidencias"),
        workspaceSummaryPendencias: document.getElementById("workspace-summary-pendencias"),
        workspaceSummaryMesa: document.getElementById("workspace-summary-mesa"),
        workspacePublicVerification: document.getElementById("workspace-public-verification"),
        workspacePublicVerificationTitle: document.getElementById("workspace-public-verification-title"),
        workspacePublicVerificationMeta: document.getElementById("workspace-public-verification-meta"),
        workspacePublicVerificationLink: document.getElementById("workspace-public-verification-link"),
        btnWorkspaceCopyVerification: document.getElementById("btn-workspace-copy-verification"),
        workspaceOfficialIssue: document.getElementById("workspace-official-issue"),
        workspaceOfficialIssueTitle: document.getElementById("workspace-official-issue-title"),
        workspaceOfficialIssueMeta: document.getElementById("workspace-official-issue-meta"),
        workspaceOfficialIssueChip: document.getElementById("workspace-official-issue-chip"),
        workspaceNavCaption: document.getElementById("workspace-nav-caption"),
        workspaceNavStatus: document.getElementById("workspace-nav-status"),
        workspaceAssistantLanding: document.getElementById("workspace-assistant-landing"),
        workspaceAssistantGovernance: document.getElementById("workspace-assistant-governance"),
        workspaceAssistantGovernanceTitle: document.getElementById("workspace-assistant-governance-title"),
        workspaceAssistantGovernanceDetail: document.getElementById("workspace-assistant-governance-detail"),
        btnAssistantLandingOpenInspecaoModal: document.getElementById("btn-assistant-landing-open-inspecao-modal"),
        btnSidebarOpenInspecaoModal: document.getElementById("btn-sidebar-open-inspecao-modal"),
        btnWorkspaceOpenInspecaoModal: document.getElementById("btn-workspace-open-inspecao-modal"),
        painelPendenciasMesa: document.getElementById("painel-pendencias-mesa"),
        listaPendenciasMesa: document.getElementById("lista-pendencias-mesa"),
        estadoLoadingPendenciasMesa: document.getElementById("estado-loading-pendencias-mesa"),
        textoVazioPendenciasMesa: document.getElementById("texto-vazio-pendencias-mesa"),
        textoVazioPendenciasMesaTexto: document.querySelector("#texto-vazio-pendencias-mesa [data-pendencias-empty-text]"),
        estadoErroPendenciasMesa: document.getElementById("estado-erro-pendencias-mesa"),
        estadoErroPendenciasMesaTexto: document.querySelector("#estado-erro-pendencias-mesa [data-pendencias-error-text]"),
        resumoPendenciasMesa: document.getElementById("resumo-pendencias-mesa"),
        acoesPendenciasMesa: document.querySelector("#painel-pendencias-mesa .acoes-pendencias"),
        filtrosPendenciasMesa: document.querySelector("#painel-pendencias-mesa .filtros-pendencias"),
        btnExportarPendenciasPdf: document.getElementById("btn-exportar-pendencias-pdf"),
        btnCarregarMaisPendencias: document.getElementById("btn-carregar-mais-pendencias"),
        botoesFiltroPendencias: Array.from(document.querySelectorAll("[data-filtro-pendencias]")),
        btnMarcarPendenciasLidas: document.getElementById("btn-marcar-pendencias-lidas"),
        btnFecharPendenciasMesa: document.getElementById("btn-fechar-pendencias-mesa"),
        btnFinalizarInspecao: document.getElementById("btn-finalizar-inspecao"),
        botoesFinalizarInspecao: Array.from(document.querySelectorAll("[data-finalizar-inspecao]")),
        btnRailFinalizarInspecao: document.getElementById("btn-rail-finalizar-inspecao"),
        btnWorkspaceToggleRail: document.getElementById("btn-workspace-toggle-rail"),
        btnWorkspacePreview: document.getElementById("btn-workspace-preview"),
        rodapeEntrada: document.querySelector(".rodape-entrada"),
        areaMensagens: document.getElementById("area-mensagens"),
        rodapeContextoTitulo: document.getElementById("rodape-contexto-titulo"),
        rodapeContextoStatus: document.getElementById("rodape-contexto-status"),
        btnIrFimChat: document.getElementById("btn-ir-fim-chat"),
        btnHomeVerHistorico: document.getElementById("btn-home-ver-historico"),
        btnHomeToggleHistoricoCompleto: document.getElementById("btn-home-toggle-historico-completo"),
        secaoHomeRecentes: document.getElementById("secao-home-recentes"),
        portalGovernanceSummary: document.getElementById("portal-governance-summary"),
        portalGovernanceSummaryTitle: document.getElementById("portal-governance-summary-title"),
        portalGovernanceSummaryDetail: document.getElementById("portal-governance-summary-detail"),
        historicoHomeExtras: Array.from(document.querySelectorAll("[data-home-historico-extra]")),
        botoesHomeLaudosRecentes: Array.from(document.querySelectorAll("[data-home-laudo-id]")),
        botoesAbrirChatLivre: Array.from(document.querySelectorAll('[data-action="open-assistant-chat"]')),
        inputBuscaHistorico: document.getElementById("busca-historico-input"),
        sidebarHistoricoLista: document.getElementById("lista-historico"),
        sidebarBuscaVazio: document.getElementById("estado-vazio-historico"),
        sidebarLaudosTabButtons: Array.from(document.querySelectorAll("[data-sidebar-laudos-tab-trigger]")),

        campoMensagem: document.getElementById("campo-mensagem"),
        btnEnviar: document.getElementById("btn-enviar"),
        btnAnexo: document.getElementById("btn-anexo"),
        btnFotoRapida: document.getElementById("btn-foto-rapida"),
        composerAttachmentTriggerButtons: Array.from(document.querySelectorAll("[data-composer-attachment-trigger]")),
        btnToggleHumano: document.getElementById("btn-toggle-humano"),
        backdropHighlight: document.getElementById("highlight-backdrop"),
        pilulaEntrada: document.querySelector(".pilula-entrada"),

        bannerEngenharia: document.getElementById("banner-notificacao-engenharia"),
        textoBannerEngenharia: document.getElementById("texto-previa-notificacao"),
        btnFecharBanner: document.querySelector(".btn-fechar-banner"),

        botoesAcoesRapidas: Array.from(document.querySelectorAll(".btn-acao-rapida")),

        btnMesaWidgetToggle: document.getElementById("btn-mesa-widget-toggle"),
        painelMesaWidget: document.getElementById("painel-mesa-widget"),
        btnFecharMesaWidget: document.getElementById("btn-fechar-mesa-widget"),
        statusConexaoMesaWidget: document.getElementById("status-conexao-mesa-widget"),
        textoConexaoMesaWidget: document.getElementById("texto-conexao-mesa-widget"),
        mesaWidgetResumo: document.getElementById("mesa-widget-resumo"),
        mesaWidgetResumoTitulo: document.getElementById("mesa-widget-resumo-titulo"),
        mesaWidgetResumoTexto: document.getElementById("mesa-widget-resumo-texto"),
        mesaWidgetChipStatus: document.getElementById("mesa-widget-chip-status"),
        mesaWidgetChipPendencias: document.getElementById("mesa-widget-chip-pendencias"),
        mesaWidgetChipNaoLidas: document.getElementById("mesa-widget-chip-nao-lidas"),
        mesaWidgetLista: document.getElementById("mesa-widget-lista"),
        mesaWidgetPreviewAnexo: document.getElementById("mesa-widget-preview-anexo"),
        mesaWidgetInput: document.getElementById("mesa-widget-input"),
        mesaWidgetBtnAnexo: document.getElementById("mesa-widget-btn-anexo"),
        mesaWidgetBtnFoto: document.getElementById("mesa-widget-btn-foto"),
        mesaWidgetInputAnexo: document.getElementById("mesa-widget-input-anexo"),
        mesaWidgetEnviar: document.getElementById("mesa-widget-enviar"),
        mesaWidgetCarregarMais: document.getElementById("mesa-widget-carregar-mais"),
        mesaWidgetRefAtiva: document.getElementById("mesa-widget-ref-ativa"),
        mesaWidgetRefTitulo: document.getElementById("mesa-widget-ref-titulo"),
        mesaWidgetRefTexto: document.getElementById("mesa-widget-ref-texto"),
        mesaWidgetRefLimpar: document.getElementById("mesa-widget-ref-limpar"),
        workspaceAnexosPanel: document.getElementById("workspace-anexos-panel"),
        workspaceAnexosGrid: document.getElementById("workspace-anexos-grid"),
        workspaceAnexosEmpty: document.getElementById("workspace-anexos-empty"),
        workspaceAnexosCount: document.getElementById("workspace-anexos-count"),
        workspaceHistoryTimeline: document.querySelector("[data-history-timeline]"),
        workspaceHistoryEmpty: document.querySelector("[data-history-empty]"),
        botoesWorkspaceHistoryContinue: Array.from(document.querySelectorAll("[data-history-continue]")),
        workspaceHistorySource: document.getElementById("workspace-history-source"),
        workspaceHistoryActiveFilter: document.getElementById("workspace-history-active-filter"),
        workspaceHistoryTotal: document.getElementById("workspace-history-total"),
        workspaceHistoryGovernance: document.getElementById("workspace-history-governance"),
        workspaceHistoryGovernanceTitle: document.getElementById("workspace-history-governance-title"),
        workspaceHistoryGovernanceDetail: document.getElementById("workspace-history-governance-detail"),
        btnWorkspaceHistoryReissue: document.getElementById("btn-workspace-history-reissue"),
        workspaceMesaStage: document.getElementById("workspace-mesa-stage"),
        workspaceMesaWidgetHost: document.getElementById("workspace-mesa-widget-host"),
        workspaceMesaStageStatus: document.getElementById("workspace-mesa-stage-status"),
        workspaceMesaStagePendencias: document.getElementById("workspace-mesa-stage-pendencias"),
        workspaceMesaStageEvidencias: document.getElementById("workspace-mesa-stage-evidencias"),
        workspaceMesaStageUnread: document.getElementById("workspace-mesa-stage-unread"),
        workspaceMesaStageSummary: document.getElementById("workspace-mesa-stage-summary"),
        workspaceMesaStageNextStep: document.getElementById("workspace-mesa-stage-next-step"),
        workspaceMesaStageTemplate: document.getElementById("workspace-mesa-stage-template"),
        workspaceMesaStageOperation: document.getElementById("workspace-mesa-stage-operation"),
        workspaceMesaStageEquipment: document.getElementById("workspace-mesa-stage-equipment"),
        workspaceMesaStageLastMovement: document.getElementById("workspace-mesa-stage-last-movement"),
        workspaceProgressCard: document.getElementById("workspace-progress-card"),
        workspaceProgressPercent: document.getElementById("workspace-progress-percent"),
        workspaceProgressBar: document.getElementById("workspace-progress-bar"),
        workspaceProgressEvidencias: document.getElementById("workspace-progress-evidencias"),
        workspaceProgressPendencias: document.getElementById("workspace-progress-pendencias"),
        workspaceActivityList: document.getElementById("workspace-activity-list"),
        chatThreadSearch: document.querySelector("[data-workspace-history-search]"),
        chatThreadResults: document.getElementById("chat-thread-results"),
        workspaceConversationEmpty: document.getElementById("workspace-conversation-empty"),
        workspaceChannelTabButtons: Array.from(document.querySelectorAll("[data-workspace-channel-tab]")),
        chatFilterButtons: Array.from(document.querySelectorAll("[data-chat-filter]")),
        historyTypeFilterButtons: Array.from(document.querySelectorAll("[data-history-type-filter]")),
        workspaceRailThreadTabButtons: Array.from(document.querySelectorAll("[data-rail-thread-tab]")),
        workspaceRailToggleButtons: Array.from(document.querySelectorAll("[data-rail-toggle]")),
        btnWorkspacePreviewRail: document.getElementById("btn-workspace-preview-rail"),
        composerSuggestions: document.getElementById("composer-suggestions"),
        slashCommandPalette: document.getElementById("slash-command-palette"),
        workspaceContextTemplate: document.getElementById("workspace-context-template"),
        workspaceContextEvidencias: document.getElementById("workspace-context-evidencias"),
        workspaceContextPendencias: document.getElementById("workspace-context-pendencias"),
        workspaceContextMesa: document.getElementById("workspace-context-mesa"),
        workspaceContextEquipment: document.getElementById("workspace-context-equipment"),
        workspaceContextOperation: document.getElementById("workspace-context-operation"),
        workspaceContextSummary: document.getElementById("workspace-context-summary"),
        workspacePinnedCard: document.getElementById("workspace-pinned-card"),
        workspaceContextPinnedCount: document.getElementById("workspace-context-pinned-count"),
        workspaceContextPinnedList: document.getElementById("workspace-context-pinned-list"),
        btnWorkspaceContextCopy: document.getElementById("btn-workspace-context-copy"),
        btnWorkspaceContextClear: document.getElementById("btn-workspace-context-clear"),
        workspaceMesaCardText: document.getElementById("workspace-mesa-card-text"),
        workspaceMesaCardStatus: document.getElementById("workspace-mesa-card-status"),
        workspaceMesaCardUnread: document.getElementById("workspace-mesa-card-unread"),
    };

    const avisosEstadoInspector = new Set();
    const divergenciasEstadoInspector = new Map();
    let sincronizandoInspectorScreen = false;
    let sincronizacaoInspectorScreenPendente = false;
    let syncInspectorScreenRaf = 0;
    const mesaWidgetDockOriginal = el.painelMesaWidget?.parentElement || null;

    // =========================================================
    // UTILITÁRIOS
    // =========================================================

    function mostrarToast(mensagem, tipo = "info", duracao = 3000) {
        if (typeof window.mostrarToast === "function") {
            window.mostrarToast(mensagem, tipo, duracao);
        }
    }

    function debugRuntime(...args) {
        if (EM_PRODUCAO) return;

        if (typeof window.TarielCore?.debug === "function") {
            window.TarielCore.debug(...args);
            return;
        }
    }

    function logOnceRuntime(chave, nivel, ...args) {
        if (typeof window.TarielCore?.logOnce === "function") {
            window.TarielCore.logOnce(chave, nivel, ...args);
            return;
        }

        const key = String(chave || "").trim();
        if (!key || avisosEstadoInspector.has(key)) return;
        avisosEstadoInspector.add(key);

        try {
            (console?.[nivel] ?? console?.log)?.call(console, "[TARIEL][CHAT_INDEX_PAGE]", ...args);
        } catch (_) {}
    }

    function emitirEventoTariel(nome, detail = {}) {
        if (typeof window.TarielInspectorEvents?.emit === "function") {
            window.TarielInspectorEvents.emit(nome, detail, {
                target: document,
                bubbles: true,
            });
            return;
        }

        document.dispatchEvent(new CustomEvent(nome, {
            detail,
            bubbles: true,
        }));
    }

    function ouvirEventoTariel(nome, handler) {
        if (typeof window.TarielInspectorEvents?.on === "function") {
            return window.TarielInspectorEvents.on(nome, handler, {
                target: document,
            });
        }

        document.addEventListener(nome, handler);
        return () => {
            document.removeEventListener(nome, handler);
        };
    }

    function obterResumoPerfInspector(snapshot = estado.snapshotEstadoInspector || null) {
        const payload = snapshot && typeof snapshot === "object" ? snapshot : {};
        return {
            screen: String(
                payload.inspectorScreen ||
                document.body?.dataset?.inspectorScreen ||
                ""
            ).trim(),
            baseScreen: String(
                payload.inspectorBaseScreen ||
                document.body?.dataset?.inspectorBaseScreen ||
                ""
            ).trim(),
            modoInspecaoUI: String(
                payload.modoInspecaoUI ||
                document.body?.dataset?.inspecaoUi ||
                ""
            ).trim(),
            workspaceStage: String(
                payload.workspaceStage ||
                document.body?.dataset?.workspaceStage ||
                ""
            ).trim(),
            threadTab: String(
                payload.threadTab ||
                document.body?.dataset?.threadTab ||
                ""
            ).trim(),
            laudoAtualId: Number(
                payload.laudoAtualId ||
                document.body?.dataset?.laudoAtualId ||
                0
            ) || null,
        };
    }

    function reportarProntidaoInspector(snapshot = estado.snapshotEstadoInspector || null) {
        if (!PERF?.enabled) return;

        const resumo = obterResumoPerfInspector(snapshot);
        const portalVisivel = !!(
            el.portalScreenRoot &&
            !el.portalScreenRoot.hidden &&
            el.portalScreenRoot.getClientRects().length > 0
        );
        const workspaceVisivel = !!(
            el.workspaceScreenRoot &&
            !el.workspaceScreenRoot.hidden &&
            el.workspaceScreenRoot.getClientRects().length > 0
        );
        const composerUtilizavel = !!(
            el.campoMensagem &&
            !el.campoMensagem.disabled &&
            el.campoMensagem.getClientRects().length > 0
        );

        if (portalVisivel) {
            PERF.markOnce("inspetor.portal.usable", resumo);
        }
        if (workspaceVisivel) {
            PERF.markOnce("inspetor.workspace.usable", resumo);
        }
        if (composerUtilizavel) {
            PERF.markOnce("inspetor.composer.usable", resumo);
        }
    }

    function normalizarTipoTemplate(tipo) {
        const valor = String(tipo || "padrao").trim().toLowerCase();

        if (valor === "nr12" || valor === "nr12_maquinas") return "nr12maquinas";
        if (valor === "nr13_caldeira") return "nr13";
        if (valor === "nr10_rti") return "rti";
        return valor || "padrao";
    }

    function normalizarContextoVisualSeguro(contexto = null) {
        if (!contexto || typeof contexto !== "object") return null;

        const title = String(contexto.title || "").trim();
        const subtitle = String(contexto.subtitle || "").trim();
        const statusBadge = String(contexto.statusBadge || "").trim();

        if (!title && !subtitle && !statusBadge) return null;

        return {
            title,
            subtitle,
            statusBadge,
        };
    }

    const normalizarCaseLifecycleStatusSeguro = (valor) =>
        CaseLifecycle.normalizarCaseLifecycleStatus(valor);

    function obterBadgeLifecycleCase(valor) {
        const status = normalizarCaseLifecycleStatusSeguro(valor);
        if (status === "analise_livre") return "ANÁLISE LIVRE";
        if (status === "pre_laudo") return "PRÉ-LAUDO";
        if (status === "laudo_em_coleta") return "EM COLETA";
        if (status === "aguardando_mesa") return "AGUARDANDO MESA";
        if (status === "em_revisao_mesa") return "MESA EM REVISÃO";
        if (status === "devolvido_para_correcao") return "CORREÇÃO";
        if (status === "aprovado") return "APROVADO";
        if (status === "emitido") return "EMITIDO";
        return "";
    }

    const normalizarActiveOwnerRoleSeguro = (valor) =>
        CaseLifecycle.normalizarActiveOwnerRole(valor);
    const normalizarSurfaceActionSeguro = (valor) =>
        CaseLifecycle.normalizarSurfaceAction(valor);
    const normalizarAllowedSurfaceActionsSeguro = (valores = []) =>
        CaseLifecycle.normalizarAllowedSurfaceActions(valores);
    const normalizarAllowedLifecycleTransitionsSeguro = (valores = []) =>
        CaseLifecycle.normalizarAllowedLifecycleTransitions(valores);

    function workspaceAllowedSurfaceActions(snapshot = null) {
        const valores = Array.isArray(snapshot?.allowed_surface_actions)
            ? snapshot.allowed_surface_actions
            : Array.isArray(snapshot?.laudo_card?.allowed_surface_actions)
                ? snapshot.laudo_card.allowed_surface_actions
                : [];
        return normalizarAllowedSurfaceActionsSeguro(valores);
    }

    function workspaceAllowedLifecycleTransitions(snapshot = null) {
        const valores = Array.isArray(snapshot?.allowed_lifecycle_transitions)
            ? snapshot.allowed_lifecycle_transitions
            : Array.isArray(snapshot?.laudo_card?.allowed_lifecycle_transitions)
                ? snapshot.laudo_card.allowed_lifecycle_transitions
                : [];
        return normalizarAllowedLifecycleTransitionsSeguro(valores);
    }

    function workspaceTemContratoLifecycle(snapshot = null) {
        const nextStatuses = Array.isArray(snapshot?.allowed_next_lifecycle_statuses)
            ? snapshot.allowed_next_lifecycle_statuses
            : Array.isArray(snapshot?.laudo_card?.allowed_next_lifecycle_statuses)
                ? snapshot.laudo_card.allowed_next_lifecycle_statuses
                : [];

        return (
            workspaceAllowedSurfaceActions(snapshot).length > 0 ||
            workspaceAllowedLifecycleTransitions(snapshot).length > 0 ||
            nextStatuses.length > 0
        );
    }

    function workspaceHasSurfaceAction(snapshot = null, actionKey = "") {
        const action = normalizarSurfaceActionSeguro(actionKey);
        return !!action && workspaceAllowedSurfaceActions(snapshot).includes(action);
    }

    function normalizarPublicVerificationSeguro(payload = null) {
        if (!payload || typeof payload !== "object") return null;

        const verificationUrl = String(
            payload.verification_url || payload.verificationUrl || ""
        ).trim();
        const hashShort = String(
            payload.hash_short || payload.hashShort || payload.codigo_hash || ""
        ).trim();
        const statusVisualLabel = String(
            payload.status_visual_label || payload.statusVisualLabel || ""
        ).trim();
        const statusRevisao = String(
            payload.status_revisao || payload.statusRevisao || ""
        ).trim();
        const caseLifecycleStatus = String(
            payload.case_lifecycle_status || payload.caseLifecycleStatus || ""
        ).trim();
        const activeOwnerRole = String(
            payload.active_owner_role || payload.activeOwnerRole || ""
        ).trim();
        const statusConformidade = String(
            payload.status_conformidade || payload.statusConformidade || ""
        ).trim();
        const documentOutcome = String(
            payload.document_outcome || payload.documentOutcome || ""
        ).trim();

        if (!verificationUrl && !hashShort) return null;

        return {
            verificationUrl,
            hashShort,
            statusVisualLabel,
            statusRevisao,
            caseLifecycleStatus,
            activeOwnerRole,
            statusConformidade,
            documentOutcome,
        };
    }

    function normalizarEmissaoOficialSeguro(payload = null) {
        if (!payload || typeof payload !== "object") return null;

        const currentIssue = payload.current_issue && typeof payload.current_issue === "object"
            ? { ...payload.current_issue }
            : null;
        const issueStatus = String(payload.issue_status || "").trim();
        const issueStatusLabel = String(payload.issue_status_label || "").trim();

        if (!issueStatus && !issueStatusLabel && !currentIssue) return null;

        return {
            issueStatus,
            issueStatusLabel,
            issueActionLabel: String(payload.issue_action_label || "").trim(),
            blockerCount: Number(payload.blocker_count || 0) || 0,
            eligibleSignatoryCount: Number(payload.eligible_signatory_count || 0) || 0,
            readyForIssue: !!payload.ready_for_issue,
            reissueRecommended: !!payload.reissue_recommended,
            alreadyIssued: !!payload.already_issued,
            currentIssue,
            blockers: Array.isArray(payload.blockers) ? payload.blockers : [],
        };
    }

    function clonarPayloadStatusRelatorioWorkspace(payload = null) {
        if (!payload || typeof payload !== "object") return null;

        return {
            ...payload,
            allowed_next_lifecycle_statuses: Array.isArray(payload?.allowed_next_lifecycle_statuses)
                ? [...payload.allowed_next_lifecycle_statuses]
                : [],
            allowed_lifecycle_transitions: Array.isArray(payload?.allowed_lifecycle_transitions)
                ? payload.allowed_lifecycle_transitions.map((item) =>
                    item && typeof item === "object" ? { ...item } : item
                )
                : [],
            allowed_surface_actions: Array.isArray(payload?.allowed_surface_actions)
                ? [...payload.allowed_surface_actions]
                : [],
            public_verification:
                payload?.public_verification && typeof payload.public_verification === "object"
                    ? { ...payload.public_verification }
                    : payload?.public_verification ?? null,
            emissao_oficial:
                payload?.emissao_oficial && typeof payload.emissao_oficial === "object"
                    ? { ...payload.emissao_oficial }
                    : payload?.emissao_oficial ?? null,
            laudo_card:
                payload?.laudo_card && typeof payload.laudo_card === "object"
                    ? {
                        ...payload.laudo_card,
                        allowed_next_lifecycle_statuses: Array.isArray(
                            payload?.laudo_card?.allowed_next_lifecycle_statuses
                        )
                            ? [...payload.laudo_card.allowed_next_lifecycle_statuses]
                            : [],
                        allowed_lifecycle_transitions: Array.isArray(
                            payload?.laudo_card?.allowed_lifecycle_transitions
                        )
                            ? payload.laudo_card.allowed_lifecycle_transitions.map((item) =>
                                item && typeof item === "object" ? { ...item } : item
                            )
                            : [],
                        allowed_surface_actions: Array.isArray(
                            payload?.laudo_card?.allowed_surface_actions
                        )
                            ? [...payload.laudo_card.allowed_surface_actions]
                            : [],
                    }
                    : payload?.laudo_card ?? null,
        };
    }

    function registrarUltimoPayloadStatusRelatorioWorkspace(payload = null) {
        estado.ultimoStatusRelatorioPayload = clonarPayloadStatusRelatorioWorkspace(payload);
        return estado.ultimoStatusRelatorioPayload;
    }

    function obterPayloadStatusRelatorioWorkspaceAtual() {
        const snapshot = clonarPayloadStatusRelatorioWorkspace(
            window.TarielAPI?.obterSnapshotStatusRelatorioAtual?.() || null
        );
        const fallback = clonarPayloadStatusRelatorioWorkspace(estado.ultimoStatusRelatorioPayload);
        const mergedLaudoCard = (
            snapshot?.laudo_card && typeof snapshot.laudo_card === "object"
        ) || (
            fallback?.laudo_card && typeof fallback.laudo_card === "object"
        )
            ? {
                ...(fallback?.laudo_card && typeof fallback.laudo_card === "object"
                    ? fallback.laudo_card
                    : {}),
                ...(snapshot?.laudo_card && typeof snapshot.laudo_card === "object"
                    ? snapshot.laudo_card
                    : {}),
            }
            : (snapshot?.laudo_card ?? fallback?.laudo_card ?? null);

        if (!snapshot && !fallback) {
            return {};
        }

        const allowedNextLifecycleStatuses = (
            Array.isArray(snapshot?.allowed_next_lifecycle_statuses)
                ? snapshot.allowed_next_lifecycle_statuses
                : Array.isArray(snapshot?.laudo_card?.allowed_next_lifecycle_statuses)
                    ? snapshot.laudo_card.allowed_next_lifecycle_statuses
                    : Array.isArray(fallback?.allowed_next_lifecycle_statuses)
                        ? fallback.allowed_next_lifecycle_statuses
                        : Array.isArray(fallback?.laudo_card?.allowed_next_lifecycle_statuses)
                            ? fallback.laudo_card.allowed_next_lifecycle_statuses
                            : []
        )
            .map((item) => normalizarCaseLifecycleStatusSeguro(item))
            .filter(Boolean);
        const allowedLifecycleTransitions = normalizarAllowedLifecycleTransitionsSeguro(
            Array.isArray(snapshot?.allowed_lifecycle_transitions)
                ? snapshot.allowed_lifecycle_transitions
                : Array.isArray(snapshot?.laudo_card?.allowed_lifecycle_transitions)
                    ? snapshot.laudo_card.allowed_lifecycle_transitions
                    : Array.isArray(fallback?.allowed_lifecycle_transitions)
                        ? fallback.allowed_lifecycle_transitions
                        : Array.isArray(fallback?.laudo_card?.allowed_lifecycle_transitions)
                            ? fallback.laudo_card.allowed_lifecycle_transitions
                            : []
        );
        const allowedSurfaceActions = normalizarAllowedSurfaceActionsSeguro(
            Array.isArray(snapshot?.allowed_surface_actions)
                ? snapshot.allowed_surface_actions
                : Array.isArray(snapshot?.laudo_card?.allowed_surface_actions)
                    ? snapshot.laudo_card.allowed_surface_actions
                    : Array.isArray(fallback?.allowed_surface_actions)
                        ? fallback.allowed_surface_actions
                        : Array.isArray(fallback?.laudo_card?.allowed_surface_actions)
                            ? fallback.laudo_card.allowed_surface_actions
                            : []
        );
        const caseLifecycleStatus = normalizarCaseLifecycleStatusSeguro(
            snapshot?.case_lifecycle_status ||
            snapshot?.laudo_card?.case_lifecycle_status ||
            fallback?.case_lifecycle_status ||
            fallback?.laudo_card?.case_lifecycle_status ||
            ""
        );
        const caseWorkflowMode = String(
            snapshot?.case_workflow_mode ||
            snapshot?.laudo_card?.case_workflow_mode ||
            fallback?.case_workflow_mode ||
            fallback?.laudo_card?.case_workflow_mode ||
            ""
        ).trim().toLowerCase();
        const activeOwnerRole = normalizarActiveOwnerRoleSeguro(
            snapshot?.active_owner_role ||
            snapshot?.laudo_card?.active_owner_role ||
            fallback?.active_owner_role ||
            fallback?.laudo_card?.active_owner_role ||
            ""
        );

        return {
            ...(fallback || {}),
            ...(snapshot || {}),
            public_verification:
                snapshot?.public_verification ??
                fallback?.public_verification ??
                null,
            emissao_oficial:
                snapshot?.emissao_oficial ??
                fallback?.emissao_oficial ??
                null,
            laudo_card: mergedLaudoCard
                ? {
                    ...mergedLaudoCard,
                    case_lifecycle_status: caseLifecycleStatus,
                    case_workflow_mode: caseWorkflowMode,
                    active_owner_role: activeOwnerRole,
                    allowed_next_lifecycle_statuses: allowedNextLifecycleStatuses,
                    allowed_lifecycle_transitions: allowedLifecycleTransitions,
                    allowed_surface_actions: allowedSurfaceActions,
                }
                : null,
            case_lifecycle_status: caseLifecycleStatus,
            case_workflow_mode: caseWorkflowMode,
            active_owner_role: activeOwnerRole,
            allowed_next_lifecycle_statuses: allowedNextLifecycleStatuses,
            allowed_lifecycle_transitions: allowedLifecycleTransitions,
            allowed_surface_actions: allowedSurfaceActions,
        };
    }

    function normalizarLaudoAtualId(valor) {
        const id = Number(valor);
        return Number.isFinite(id) && id > 0 ? id : null;
    }

    function normalizarModoInspecaoUI(valor) {
        return String(valor || "").trim().toLowerCase() === "home" ? "home" : "workspace";
    }

    function normalizarWorkspaceStage(valor) {
        return String(valor || "").trim().toLowerCase() === "inspection" ? "inspection" : "assistant";
    }

    function normalizarThreadTab(valor) {
        const normalizado = String(valor || "").trim().toLowerCase();
        if (normalizado === "chat" || normalizado === "conversa") return "conversa";
        if (normalizado === "history" || normalizado === "historico") return "historico";
        if (normalizado === "attachments" || normalizado === "anexos") return "anexos";
        if (normalizado === "mesa") return "mesa";
        return "conversa";
    }

    function normalizarEntryModePreference(valor, fallback = "auto_recommended") {
        const normalizado = String(valor || "").trim().toLowerCase();
        if (normalizado === "chat_first" || normalizado === "chatfirst" || normalizado === "conversa") {
            return "chat_first";
        }
        if (
            normalizado === "evidence_first" ||
            normalizado === "evidencefirst" ||
            normalizado === "evidencia" ||
            normalizado === "evidencias" ||
            normalizado === "guided" ||
            normalizado === "checklist"
        ) {
            return "evidence_first";
        }
        if (
            normalizado === "auto_recommended" ||
            normalizado === "autorecommended" ||
            normalizado === "auto" ||
            normalizado === "automatico" ||
            normalizado === "automatic"
        ) {
            return "auto_recommended";
        }

        const fallbackNormalizado = String(fallback || "").trim().toLowerCase();
        if (fallbackNormalizado === "chat_first" || fallbackNormalizado === "evidence_first") {
            return fallbackNormalizado;
        }
        return "auto_recommended";
    }

    function normalizarEntryModeEffective(valor, fallback = "chat_first") {
        const normalizado = String(valor || "").trim().toLowerCase();
        if (normalizado === "evidence_first" || normalizado === "evidencefirst" || normalizado === "evidencia") {
            return "evidence_first";
        }
        if (normalizado === "chat_first" || normalizado === "chatfirst" || normalizado === "conversa") {
            return "chat_first";
        }
        return String(fallback || "").trim().toLowerCase() === "evidence_first"
            ? "evidence_first"
            : "chat_first";
    }

    function normalizarEntryModeEffectiveOpcional(valor) {
        if (valor == null || String(valor || "").trim() === "") return null;
        return normalizarEntryModeEffective(valor);
    }

    function normalizarEntryModeReason(valor, fallback = "default_product_fallback") {
        const normalizado = String(valor || "").trim().toLowerCase();
        if (
            [
                "hard_safety_rule",
                "family_required_mode",
                "tenant_policy",
                "role_policy",
                "user_preference",
                "last_case_mode",
                "auto_recommended",
                "default_product_fallback",
                "existing_case_state",
            ].includes(normalizado)
        ) {
            return normalizado;
        }
        return String(fallback || "").trim().toLowerCase() || "default_product_fallback";
    }

    function normalizarOverlayOwner(valor) {
        return String(valor || "").trim().toLowerCase() === "new_inspection"
            ? "new_inspection"
            : "";
    }

    function normalizarBooleanoEstado(valor, fallback = false) {
        if (valor === true || valor === false) return valor;
        if (valor == null || valor === "") return !!fallback;

        const texto = String(valor).trim().toLowerCase();
        if (texto === "true" || texto === "1" || texto === "yes") return true;
        if (texto === "false" || texto === "0" || texto === "no") return false;
        return !!fallback;
    }

    function atualizarWorkspaceEntryModeNote() {
        return ctx.shared.atualizarWorkspaceEntryModeNote?.();
    }

    function atualizarEstadoModoEntrada(
        payload = {},
        { reset = false, atualizarPadrao = false } = {}
    ) {
        return ctx.actions.atualizarEstadoModoEntrada?.(payload, {
            reset,
            atualizarPadrao,
        }) || {
            preference: estado.entryModePreference,
            effective: estado.entryModeEffective,
            reason: estado.entryModeReason,
        };
    }

    function modoEntradaEvidenceFirstAtivo() {
        return !!ctx.shared.modoEntradaEvidenceFirstAtivo?.();
    }

    function resolverThreadTabInicialPorModoEntrada(payload = {}, fallback = "historico") {
        return ctx.shared.resolverThreadTabInicialPorModoEntrada?.(payload, fallback)
            || normalizarThreadTab(fallback);
    }

    function normalizarRetomadaHomePendenteSeguro(payload = null) {
        return ctx.shared.normalizarRetomadaHomePendenteSeguro?.(payload) || null;
    }

    function retomadaHomePendenteEhValida(payload = null) {
        return !!ctx.shared.retomadaHomePendenteEhValida?.(payload);
    }

    function sanitizarMapaContextoVisualLaudos(payload = null) {
        return ctx.shared.sanitizarMapaContextoVisualLaudos?.(payload) || {};
    }

    function persistirContextoVisualLaudosStorage(payload = null) {
        return ctx.shared.persistirContextoVisualLaudosStorage?.(payload) || {};
    }

    function lerContextoVisualLaudosStorage() {
        return ctx.shared.lerContextoVisualLaudosStorage?.() || {};
    }

    function registrarContextoVisualLaudo(laudoId, contextoVisual = null) {
        return ctx.actions.registrarContextoVisualLaudo?.(laudoId, contextoVisual) || null;
    }

    function obterContextoVisualLaudoRegistrado(laudoId) {
        return ctx.actions.obterContextoVisualLaudoRegistrado?.(laudoId) || null;
    }

    function lerRetomadaHomePendenteStorage() {
        return ctx.shared.lerRetomadaHomePendenteStorage?.() || null;
    }

    function lerFlagForcaHomeStorage() {
        return !!ctx.shared.lerFlagForcaHomeStorage?.();
    }

    estado.contextoVisualPorLaudo = {};

    function paginaSolicitaHomeLandingViaURL() {
        try {
            const url = new URL(window.location.href);
            return url.searchParams.get("home") === "1" && !url.searchParams.get("laudo");
        } catch (_) {
            return false;
        }
    }

    function obterLaudoIdDaURLInspector() {
        try {
            const valor = new URL(window.location.href).searchParams.get("laudo");
            return normalizarLaudoAtualId(valor);
        } catch (_) {
            return null;
        }
    }

    function obterThreadTabDaURLInspector() {
        try {
            const valor = new URL(window.location.href).searchParams.get("aba");
            return valor ? normalizarThreadTab(valor) : undefined;
        } catch (_) {
            return undefined;
        }
    }

    function obterSnapshotCompatCoreInspector() {
        const legado = window.TarielChatPainel?.state || {};

        return {
            laudoAtualId: normalizarLaudoAtualId(legado.laudoAtualId),
            estadoRelatorio: normalizarEstadoRelatorio(
                legado.estadoRelatorio ?? "sem_relatorio"
            ),
        };
    }

    function obterSnapshotCompatApiInspector() {
        const snapshot = window.TarielAPI?.obterSnapshotEstadoCompat?.();

        return {
            laudoAtualId: normalizarLaudoAtualId(
                snapshot?.laudoAtualId ?? null
            ),
            estadoRelatorio: normalizarEstadoRelatorio(
                snapshot?.estadoRelatorio ?? "sem_relatorio"
            ),
        };
    }

    function obterSnapshotDatasetInspector() {
        const body = document.body;
        const painel = el.painelChat;

        return {
            laudoAtualId: normalizarLaudoAtualId(
                painel?.dataset?.laudoAtualId ??
                body?.dataset?.laudoAtualId ??
                null
            ),
            estadoRelatorio: normalizarEstadoRelatorio(
                painel?.dataset?.estadoRelatorio ??
                body?.dataset?.estadoRelatorio ??
                "sem_relatorio"
            ),
            modoInspecaoUI: normalizarModoInspecaoUI(
                painel?.dataset?.inspecaoUi ??
                body?.dataset?.inspecaoUi ??
                "workspace"
            ),
            workspaceStage: normalizarWorkspaceStage(
                painel?.dataset?.workspaceStage ??
                body?.dataset?.workspaceStage ??
                "assistant"
            ),
            threadTab: normalizarThreadTab(
                body?.dataset?.threadTab ??
                painel?.dataset?.threadTab ??
                "conversa"
            ),
            forceHomeLanding: normalizarBooleanoEstado(body?.dataset?.forceHomeLanding, false),
            overlayOwner: normalizarOverlayOwner(
                body?.dataset?.inspectorOverlayOwner ??
                body?.dataset?.overlayOwner ??
                painel?.dataset?.inspectorOverlayOwner ??
                ""
            ),
            assistantLandingFirstSendPending: normalizarBooleanoEstado(
                painel?.dataset?.assistantLandingFirstSendPending ??
                body?.dataset?.assistantLandingFirstSendPending,
                false
            ),
            freeChatConversationActive: normalizarBooleanoEstado(
                painel?.dataset?.freeChatConversationActive ??
                body?.dataset?.freeChatConversationActive,
                false
            ),
        };
    }

    function obterSnapshotSSRInspector() {
        const painel = el.painelChat;

        return {
            laudoAtualId: normalizarLaudoAtualId(
                window.TARIEL?.laudoAtivoId ??
                painel?.dataset?.laudoAtualId ??
                null
            ),
            estadoRelatorio: normalizarEstadoRelatorio(
                window.TARIEL?.estadoRelatorio ??
                painel?.dataset?.estadoRelatorio ??
                "sem_relatorio"
            ),
            modoInspecaoUI: normalizarModoInspecaoUI(
                painel?.dataset?.inspecaoUi ?? "workspace"
            ),
            workspaceStage: normalizarWorkspaceStage(
                painel?.dataset?.workspaceStage ?? "assistant"
            ),
            inspectorScreen: String(painel?.dataset?.inspectorScreen || "").trim().toLowerCase(),
        };
    }

    function obterSnapshotStorageInspector() {
        return {
            laudoAtualId: normalizarLaudoAtualId(
                window.TarielChatPainel?.obterLaudoPersistido?.()
            ),
            urlLaudoAtualId: obterLaudoIdDaURLInspector(),
            urlThreadTab: obterThreadTabDaURLInspector(),
            forceHomeLanding: lerFlagForcaHomeStorage() || paginaSolicitaHomeLandingViaURL(),
            retomadaHomePendente: lerRetomadaHomePendenteStorage(),
        };
    }

    function obterSnapshotMemoriaInspector() {
        const snapshot =
            estado.snapshotEstadoInspector && typeof estado.snapshotEstadoInspector === "object"
                ? estado.snapshotEstadoInspector
                : null;
        if (!snapshot) return null;

        return {
            laudoAtualId: normalizarLaudoAtualId(snapshot.laudoAtualId),
            estadoRelatorio: normalizarEstadoRelatorio(snapshot.estadoRelatorio ?? "sem_relatorio"),
            modoInspecaoUI: normalizarModoInspecaoUI(snapshot.modoInspecaoUI ?? estado.modoInspecaoUI),
            workspaceStage: normalizarWorkspaceStage(snapshot.workspaceStage ?? estado.workspaceStage),
            threadTab: normalizarThreadTab(snapshot.threadTab ?? estado.threadTab),
            forceHomeLanding: normalizarBooleanoEstado(snapshot.forceHomeLanding, false),
            overlayOwner: normalizarOverlayOwner(snapshot.overlayOwner),
            assistantLandingFirstSendPending: normalizarBooleanoEstado(
                snapshot.assistantLandingFirstSendPending,
                false
            ),
            freeChatConversationActive: normalizarBooleanoEstado(
                snapshot.freeChatConversationActive,
                false
            ),
            retomadaHomePendente: retomadaHomePendenteEhValida(snapshot.retomadaHomePendente)
                ? normalizarRetomadaHomePendenteSeguro(snapshot.retomadaHomePendente)
                : null,
        };
    }

    function obterSnapshotBootstrapInspector() {
        const ssr = obterSnapshotSSRInspector();
        const dataset = obterSnapshotDatasetInspector();
        const storage = obterSnapshotStorageInspector();

        return {
            laudoAtualId: normalizarLaudoAtualId(
                ssr.laudoAtualId ??
                dataset.laudoAtualId ??
                storage.urlLaudoAtualId ??
                storage.laudoAtualId ??
                null
            ),
            estadoRelatorio: normalizarEstadoRelatorio(
                ssr.estadoRelatorio ??
                dataset.estadoRelatorio ??
                "sem_relatorio"
            ),
            modoInspecaoUI: normalizarModoInspecaoUI(
                ssr.modoInspecaoUI ??
                dataset.modoInspecaoUI ??
                "workspace"
            ),
            workspaceStage: normalizarWorkspaceStage(
                ssr.workspaceStage ??
                dataset.workspaceStage ??
                "assistant"
            ),
            threadTab: normalizarThreadTab(
                storage.urlThreadTab ??
                dataset.threadTab ??
                "conversa"
            ),
            forceHomeLanding: !!(dataset.forceHomeLanding || storage.forceHomeLanding),
            overlayOwner: normalizarOverlayOwner(dataset.overlayOwner),
            assistantLandingFirstSendPending: !!dataset.assistantLandingFirstSendPending,
            freeChatConversationActive: !!dataset.freeChatConversationActive,
            retomadaHomePendente: retomadaHomePendenteEhValida(storage.retomadaHomePendente)
                ? normalizarRetomadaHomePendenteSeguro(storage.retomadaHomePendente)
                : null,
        };
    }

    function escolherCampoEstadoInspector(candidatos = [], { fallback = null, aceitarNulo = false } = {}) {
        for (const candidato of candidatos) {
            if (!candidato || !Object.prototype.hasOwnProperty.call(candidato, "value")) {
                continue;
            }

            const valor = candidato.value;
            if (valor === undefined) continue;
            if (valor === null && !aceitarNulo) continue;

            return {
                value: valor,
                source: String(candidato.source || "desconhecido"),
            };
        }

        return {
            value: fallback,
            source: "fallback",
        };
    }

    function registrarDivergenciaEstadoInspector(campo, mapaFontes = {}, valorEscolhido) {
        const entradas = Object.entries(mapaFontes)
            .map(([origem, valor]) => [origem, valor])
            .filter(([, valor]) => valor !== undefined && valor !== null && valor !== "");

        const valoresDistintos = [...new Set(entradas.map(([, valor]) => JSON.stringify(valor)))];
        const divergente = valoresDistintos.length > 1;

        if (!divergente) {
            divergenciasEstadoInspector.delete(campo);
            return false;
        }

        if (!EM_PRODUCAO) {
            const chaveAviso = `${campo}:${valoresDistintos.join("|")}`;
            const agora = Date.now();
            const anterior = divergenciasEstadoInspector.get(campo);

            if (!anterior || anterior.key !== chaveAviso) {
                divergenciasEstadoInspector.set(campo, {
                    key: chaveAviso,
                    count: 1,
                    firstAt: agora,
                    warned: false,
                });
                debugRuntime(`[INSPECTOR_STATE] Divergência transitória detectada em ${campo}.`, {
                    escolhido: valorEscolhido,
                    fontes: mapaFontes,
                });
                return true;
            }

            anterior.count += 1;

            if (!anterior.warned && (anterior.count >= 3 || (agora - anterior.firstAt) >= 1200)) {
                anterior.warned = true;
                logOnceRuntime(`inspector-state:${chaveAviso}`, "warn", `[INSPECTOR_STATE] Divergência persistente em ${campo}.`, {
                    escolhido: valorEscolhido,
                    fontes: mapaFontes,
                    ocorrencias: anterior.count,
                    persistenciaMs: agora - anterior.firstAt,
                });
            }
        }

        return divergente;
    }

    function resolverInspectorBaseScreenPorSnapshot(snapshot = {}) {
        if (snapshot.modoInspecaoUI === "home") {
            return "portal_dashboard";
        }

        if (snapshot.workspaceStage === "assistant") {
            return "assistant_landing";
        }

        return "inspection_workspace";
    }

    function resolverEstadoAutoritativoInspector(overrides = {}) {
        const payload = overrides && typeof overrides === "object" ? overrides : {};
        const memoria = obterSnapshotMemoriaInspector();
        const core = obterSnapshotCompatCoreInspector();
        const api = obterSnapshotCompatApiInspector();
        const dataset = obterSnapshotDatasetInspector();
        const ssr = obterSnapshotSSRInspector();
        const storage = obterSnapshotStorageInspector();
        const bootstrap = memoria || obterSnapshotBootstrapInspector();
        const autoridadeDisponivel = !!memoria;

        const urlLaudoAtualId = normalizarLaudoAtualId(storage.urlLaudoAtualId);
        let forceHomeLandingInfo = escolherCampoEstadoInspector([
            {
                source: "override",
                value: Object.prototype.hasOwnProperty.call(payload, "forceHomeLanding")
                    ? normalizarBooleanoEstado(payload.forceHomeLanding, false)
                    : undefined,
            },
            { source: "memory", value: memoria?.forceHomeLanding },
            { source: "dataset", value: autoridadeDisponivel ? undefined : dataset.forceHomeLanding },
            { source: "storage", value: autoridadeDisponivel ? undefined : storage.forceHomeLanding },
            { source: "bootstrap", value: bootstrap.forceHomeLanding },
        ], { fallback: false });

        if (
            !Object.prototype.hasOwnProperty.call(payload, "forceHomeLanding")
            && urlLaudoAtualId
            && !paginaSolicitaHomeLandingViaURL()
        ) {
            forceHomeLandingInfo = {
                value: false,
                source: "url-laudo",
            };
        }

        const ignorarRetomadaPersistidaLaudo = !!forceHomeLandingInfo.value
            && !Object.prototype.hasOwnProperty.call(payload, "laudoAtualId");

        const laudoInfo = escolherCampoEstadoInspector([
            {
                source: "override",
                value: Object.prototype.hasOwnProperty.call(payload, "laudoAtualId")
                    ? normalizarLaudoAtualId(payload.laudoAtualId)
                    : undefined,
            },
            { source: "memory", value: memoria?.laudoAtualId },
            { source: "ssr", value: autoridadeDisponivel ? undefined : ssr.laudoAtualId },
            { source: "dataset", value: autoridadeDisponivel ? undefined : dataset.laudoAtualId },
            {
                source: "url",
                value: (autoridadeDisponivel || ignorarRetomadaPersistidaLaudo)
                    ? undefined
                    : storage.urlLaudoAtualId,
            },
            {
                source: "storage",
                value: (autoridadeDisponivel || ignorarRetomadaPersistidaLaudo)
                    ? undefined
                    : storage.laudoAtualId,
            },
            {
                source: "bootstrap",
                value: ignorarRetomadaPersistidaLaudo
                    ? undefined
                    : bootstrap.laudoAtualId,
            },
        ], { fallback: null, aceitarNulo: true });

        const estadoRelatorioInfo = escolherCampoEstadoInspector([
            {
                source: "override",
                value: Object.prototype.hasOwnProperty.call(payload, "estadoRelatorio")
                    ? normalizarEstadoRelatorio(payload.estadoRelatorio)
                    : undefined,
            },
            { source: "memory", value: memoria?.estadoRelatorio },
            { source: "ssr", value: autoridadeDisponivel ? undefined : ssr.estadoRelatorio },
            { source: "dataset", value: autoridadeDisponivel ? undefined : dataset.estadoRelatorio },
            { source: "bootstrap", value: bootstrap.estadoRelatorio },
        ], { fallback: "sem_relatorio" });

        let modoInfo = escolherCampoEstadoInspector([
            {
                source: "override",
                value: Object.prototype.hasOwnProperty.call(payload, "modoInspecaoUI")
                    ? normalizarModoInspecaoUI(payload.modoInspecaoUI)
                    : undefined,
            },
            { source: "memory", value: memoria?.modoInspecaoUI },
            { source: "ssr", value: autoridadeDisponivel ? undefined : ssr.modoInspecaoUI },
            { source: "dataset", value: autoridadeDisponivel ? undefined : dataset.modoInspecaoUI },
            { source: "bootstrap", value: bootstrap.modoInspecaoUI },
        ], { fallback: "workspace" });

        if (!Object.prototype.hasOwnProperty.call(payload, "modoInspecaoUI") && forceHomeLandingInfo.value) {
            modoInfo = { value: "home", source: "forceHomeLanding" };
        }

        if (
            !Object.prototype.hasOwnProperty.call(payload, "modoInspecaoUI")
            && urlLaudoAtualId
            && !forceHomeLandingInfo.value
        ) {
            modoInfo = { value: "workspace", source: "url-laudo" };
        }

        const workspaceStageDerivado = (
            estadoRelatorioPossuiContexto(estadoRelatorioInfo.value) || !!laudoInfo.value
        )
            ? "inspection"
            : "assistant";

        let workspaceStageInfo = escolherCampoEstadoInspector([
            {
                source: "override",
                value: Object.prototype.hasOwnProperty.call(payload, "workspaceStage")
                    ? normalizarWorkspaceStage(payload.workspaceStage)
                    : undefined,
            },
            { source: "memory", value: memoria?.workspaceStage },
            { source: "ssr", value: autoridadeDisponivel ? undefined : ssr.workspaceStage },
            { source: "dataset", value: autoridadeDisponivel ? undefined : dataset.workspaceStage },
            { source: "bootstrap", value: bootstrap.workspaceStage },
            { source: "derived", value: workspaceStageDerivado },
        ], { fallback: "assistant" });

        if (
            !Object.prototype.hasOwnProperty.call(payload, "workspaceStage") &&
            modoInfo.value !== "home" &&
            workspaceStageInfo.value !== "inspection" &&
            workspaceStageDerivado === "inspection"
        ) {
            workspaceStageInfo = {
                value: "inspection",
                source: "derived-context",
            };
        }

        if (
            !Object.prototype.hasOwnProperty.call(payload, "workspaceStage") &&
            modoInfo.value === "home"
        ) {
            workspaceStageInfo = { value: "assistant", source: "home-mode" };
        }

        const threadTabInfo = escolherCampoEstadoInspector([
            {
                source: "override",
                value: Object.prototype.hasOwnProperty.call(payload, "threadTab")
                    ? normalizarThreadTab(payload.threadTab)
                    : undefined,
            },
            { source: "memory", value: memoria?.threadTab },
            {
                source: "url",
                value: storage.urlThreadTab,
            },
            { source: "dataset", value: autoridadeDisponivel ? undefined : dataset.threadTab },
            { source: "bootstrap", value: bootstrap.threadTab },
        ], { fallback: "conversa" });

        if (
            !Object.prototype.hasOwnProperty.call(payload, "threadTab") &&
            workspaceStageInfo.value !== "inspection"
        ) {
            threadTabInfo.value = "conversa";
            threadTabInfo.source = "assistant-stage";
        }

        const overlayOwnerInfo = escolherCampoEstadoInspector([
            {
                source: "override",
                value: Object.prototype.hasOwnProperty.call(payload, "overlayOwner")
                    ? normalizarOverlayOwner(payload.overlayOwner)
                    : undefined,
            },
            {
                source: "modal",
                value: modalNovaInspecaoEstaAberta() ? "new_inspection" : undefined,
            },
            { source: "memory", value: memoria?.overlayOwner },
            { source: "dataset", value: autoridadeDisponivel ? undefined : dataset.overlayOwner },
            { source: "bootstrap", value: bootstrap.overlayOwner },
        ], { fallback: "", aceitarNulo: true });

        const assistantLandingFirstSendPendingInfo = escolherCampoEstadoInspector([
            {
                source: "override",
                value: Object.prototype.hasOwnProperty.call(payload, "assistantLandingFirstSendPending")
                    ? normalizarBooleanoEstado(payload.assistantLandingFirstSendPending, false)
                    : undefined,
            },
            { source: "memory", value: memoria?.assistantLandingFirstSendPending },
            { source: "dataset", value: autoridadeDisponivel ? undefined : dataset.assistantLandingFirstSendPending },
            { source: "bootstrap", value: bootstrap.assistantLandingFirstSendPending },
        ], { fallback: false });

        const freeChatConversationActiveInfo = escolherCampoEstadoInspector([
            {
                source: "override",
                value: Object.prototype.hasOwnProperty.call(payload, "freeChatConversationActive")
                    ? normalizarBooleanoEstado(payload.freeChatConversationActive, false)
                    : undefined,
            },
            { source: "memory", value: memoria?.freeChatConversationActive },
            { source: "dataset", value: autoridadeDisponivel ? undefined : dataset.freeChatConversationActive },
            { source: "bootstrap", value: bootstrap.freeChatConversationActive },
        ], { fallback: false });

        const retomadaInfo = escolherCampoEstadoInspector([
            {
                source: "override",
                value: Object.prototype.hasOwnProperty.call(payload, "retomadaHomePendente")
                    ? normalizarRetomadaHomePendenteSeguro(payload.retomadaHomePendente)
                    : undefined,
            },
            {
                source: "memory",
                value: retomadaHomePendenteEhValida(memoria?.retomadaHomePendente)
                    ? memoria.retomadaHomePendente
                    : undefined,
            },
            {
                source: "storage",
                value: autoridadeDisponivel
                    ? undefined
                    : (
                        retomadaHomePendenteEhValida(storage.retomadaHomePendente)
                            ? storage.retomadaHomePendente
                            : undefined
                    ),
            },
            {
                source: "bootstrap",
                value: retomadaHomePendenteEhValida(bootstrap.retomadaHomePendente)
                    ? bootstrap.retomadaHomePendente
                    : undefined,
            },
        ], { fallback: null, aceitarNulo: true });

        const snapshotBase = {
            laudoAtualId: laudoInfo.value,
            estadoRelatorio: estadoRelatorioInfo.value,
            modoInspecaoUI: modoInfo.value,
            workspaceStage: workspaceStageInfo.value,
            threadTab: threadTabInfo.value,
            forceHomeLanding: !!forceHomeLandingInfo.value,
            overlayOwner: overlayOwnerInfo.value,
            assistantLandingFirstSendPending: !!assistantLandingFirstSendPendingInfo.value,
            freeChatConversationActive: !!freeChatConversationActiveInfo.value,
            retomadaHomePendente: retomadaInfo.value,
        };

        const inspectorBaseScreen = resolverInspectorBaseScreenPorSnapshot(snapshotBase);
        const inspectorScreen = snapshotBase.overlayOwner === "new_inspection"
            ? "new_inspection"
            : inspectorBaseScreen;
        const homeActionVisible = snapshotBase.overlayOwner !== "new_inspection" && (
            inspectorBaseScreen === "inspection_workspace" ||
            inspectorBaseScreen === "assistant_landing"
        );

        const divergenciaLaudo = autoridadeDisponivel
            ? {
                api: api.laudoAtualId,
                core: core.laudoAtualId,
                dataset: dataset.laudoAtualId,
            }
            : {
                api: api.laudoAtualId,
                core: core.laudoAtualId,
                dataset: dataset.laudoAtualId,
                ssr: ssr.laudoAtualId,
                url: storage.urlLaudoAtualId,
                storage: storage.laudoAtualId,
            };
        const divergenciaEstado = autoridadeDisponivel
            ? {
                api: api.estadoRelatorio,
                core: core.estadoRelatorio,
                dataset: dataset.estadoRelatorio,
            }
            : {
                api: api.estadoRelatorio,
                core: core.estadoRelatorio,
                dataset: dataset.estadoRelatorio,
                ssr: ssr.estadoRelatorio,
            };

        const divergencias = {
            laudoAtualId: registrarDivergenciaEstadoInspector(
                "laudoAtualId",
                divergenciaLaudo,
                laudoInfo.value
            ),
            estadoRelatorio: registrarDivergenciaEstadoInspector(
                "estadoRelatorio",
                divergenciaEstado,
                estadoRelatorioInfo.value
            ),
        };

        return {
            ...snapshotBase,
            inspectorBaseScreen,
            inspectorScreen,
            homeActionVisible,
            sources: {
                laudoAtualId: laudoInfo.source,
                estadoRelatorio: estadoRelatorioInfo.source,
                modoInspecaoUI: modoInfo.source,
                workspaceStage: workspaceStageInfo.source,
                threadTab: threadTabInfo.source,
                forceHomeLanding: forceHomeLandingInfo.source,
                overlayOwner: overlayOwnerInfo.source,
                assistantLandingFirstSendPending: assistantLandingFirstSendPendingInfo.source,
                freeChatConversationActive: freeChatConversationActiveInfo.source,
                retomadaHomePendente: retomadaInfo.source,
                inspectorBaseScreen: "derived",
                inspectorScreen: "derived",
                homeActionVisible: "derived",
            },
            divergencias,
        };
    }

    function espelharEstadoInspectorCompat(snapshot = {}) {
        const payloadCompat = {
            laudoAtualId: snapshot.laudoAtualId,
            estadoRelatorio: snapshot.estadoRelatorio,
        };

        if (typeof window.TarielChatPainel?.sincronizarEstadoPainel === "function") {
            window.TarielChatPainel.sincronizarEstadoPainel(payloadCompat);
        } else if (window.TarielChatPainel?.state) {
            window.TarielChatPainel.state.laudoAtualId = snapshot.laudoAtualId;
            window.TarielChatPainel.state.estadoRelatorio = snapshot.estadoRelatorio;
        }

        if (typeof window.TarielAPI?.sincronizarEstadoCompat === "function") {
            window.TarielAPI.sincronizarEstadoCompat(payloadCompat);
        }
    }

    function espelharEstadoInspectorNoDataset(snapshot = {}) {
        const body = document.body;
        const painel = el.painelChat;
        const overlayHost = el.overlayHost;
        const divergente = Object.values(snapshot.divergencias || {}).some(Boolean);

        body.dataset.laudoAtualId = snapshot.laudoAtualId ? String(snapshot.laudoAtualId) : "";
        body.dataset.estadoRelatorio = String(snapshot.estadoRelatorio || "sem_relatorio");
        body.dataset.inspecaoUi = String(snapshot.modoInspecaoUI || "workspace");
        body.dataset.workspaceStage = String(snapshot.workspaceStage || "assistant");
        body.dataset.threadTab = String(snapshot.threadTab || "conversa");
        body.dataset.forceHomeLanding = snapshot.forceHomeLanding ? "true" : "false";
        body.dataset.inspectorScreen = String(snapshot.inspectorScreen || "");
        body.dataset.inspectorBaseScreen = String(snapshot.inspectorBaseScreen || "");
        body.dataset.inspectorOverlayOwner = String(snapshot.overlayOwner || "");
        body.dataset.homeActionVisible = snapshot.homeActionVisible ? "true" : "false";
        body.dataset.assistantLandingFirstSendPending = snapshot.assistantLandingFirstSendPending ? "true" : "false";
        body.dataset.freeChatConversationActive = snapshot.freeChatConversationActive ? "true" : "false";
        body.dataset.inspectorStateDivergence = divergente ? "true" : "false";

        if (painel) {
            painel.dataset.laudoAtualId = snapshot.laudoAtualId ? String(snapshot.laudoAtualId) : "";
            painel.dataset.estadoRelatorio = String(snapshot.estadoRelatorio || "sem_relatorio");
            painel.dataset.inspecaoUi = String(snapshot.modoInspecaoUI || "workspace");
            painel.dataset.workspaceStage = String(snapshot.workspaceStage || "assistant");
            painel.dataset.threadTab = String(snapshot.threadTab || "conversa");
            painel.dataset.forceHomeLanding = snapshot.forceHomeLanding ? "true" : "false";
            painel.dataset.inspectorScreen = String(snapshot.inspectorScreen || "");
            painel.dataset.inspectorBaseScreen = String(snapshot.inspectorBaseScreen || "");
            painel.dataset.inspectorOverlayOwner = String(snapshot.overlayOwner || "");
            painel.dataset.homeActionVisible = snapshot.homeActionVisible ? "true" : "false";
            painel.dataset.assistantLandingFirstSendPending = snapshot.assistantLandingFirstSendPending ? "true" : "false";
            painel.dataset.freeChatConversationActive = snapshot.freeChatConversationActive ? "true" : "false";
            painel.dataset.inspectorStateDivergence = divergente ? "true" : "false";
        }

        if (overlayHost) {
            overlayHost.dataset.inspectorScreen = String(snapshot.inspectorScreen || "");
            overlayHost.dataset.inspectorBaseScreen = String(snapshot.inspectorBaseScreen || "");
            overlayHost.dataset.overlayOwner = String(snapshot.overlayOwner || "");
            overlayHost.dataset.freeChatConversationActive = snapshot.freeChatConversationActive ? "true" : "false";
        }

        sincronizarConversationVariantNoDom(snapshot);
    }

    function espelharEstadoInspectorNoStorage(snapshot = {}, opts = {}) {
        const persistirStorage = opts.persistirStorage !== false;
        if (!persistirStorage) return;

        persistirContextoVisualLaudosStorage(estado.contextoVisualPorLaudo);

        try {
            if (snapshot.forceHomeLanding) {
                sessionStorage.setItem(CHAVE_FORCE_HOME_LANDING, "1");
            } else {
                sessionStorage.removeItem(CHAVE_FORCE_HOME_LANDING);
            }
        } catch (_) {
            // armazenamento opcional
        }

        try {
            if (snapshot.retomadaHomePendente) {
                sessionStorage.setItem(
                    CHAVE_RETOMADA_HOME_PENDENTE,
                    JSON.stringify(snapshot.retomadaHomePendente)
                );
            } else {
                sessionStorage.removeItem(CHAVE_RETOMADA_HOME_PENDENTE);
            }
        } catch (_) {
            // armazenamento opcional
        }

        try {
            if (snapshot.laudoAtualId && !snapshot.forceHomeLanding) {
                window.TarielChatPainel?.persistirLaudoAtual?.(snapshot.laudoAtualId);
            } else {
                window.TarielChatPainel?.persistirLaudoAtual?.("");
            }
        } catch (_) {
            // armazenamento opcional
        }
    }

    function emitirEstadoInspectorSincronizado(snapshot = {}) {
        emitirEventoTariel("tariel:inspector-state-sincronizado", {
            snapshot: { ...snapshot },
            laudoAtualId: snapshot.laudoAtualId ?? null,
            estadoRelatorio: snapshot.estadoRelatorio || "sem_relatorio",
            workspaceStage: snapshot.workspaceStage || "assistant",
            threadTab: snapshot.threadTab || "conversa",
            inspectorScreen: snapshot.inspectorScreen || "",
        });
    }

    function aplicarSnapshotEstadoInspector(snapshot = {}, opts = {}) {
        estado.laudoAtualId = snapshot.laudoAtualId;
        estado.estadoRelatorio = snapshot.estadoRelatorio;
        estado.modoInspecaoUI = snapshot.modoInspecaoUI;
        estado.workspaceStage = snapshot.workspaceStage;
        estado.threadTab = snapshot.threadTab;
        estado.forceHomeLanding = !!snapshot.forceHomeLanding;
        estado.overlayOwner = snapshot.overlayOwner;
        estado.assistantLandingFirstSendPending = !!snapshot.assistantLandingFirstSendPending;
        estado.freeChatConversationActive = !!snapshot.freeChatConversationActive;
        estado.inspectorBaseScreen = snapshot.inspectorBaseScreen;
        estado.inspectorScreen = snapshot.inspectorScreen;
        estado.homeActionVisible = !!snapshot.homeActionVisible;
        estado.retomadaHomePendente = snapshot.retomadaHomePendente;
        estado.snapshotEstadoInspector = { ...snapshot };
        estado.snapshotEstadoInspectorOrigem = { ...(snapshot.sources || {}) };
        estado.divergenciasEstadoInspector = { ...(snapshot.divergencias || {}) };
        if (window.TarielInspectorState && typeof window.TarielInspectorState === "object") {
            window.TarielInspectorState.state = { ...snapshot };
        }

        espelharEstadoInspectorNoDataset(snapshot);

        if (opts.espelharCompat !== false) {
            espelharEstadoInspectorCompat(snapshot);
        }

        espelharEstadoInspectorNoStorage(snapshot, opts);

        if (opts.syncScreen !== false && !sincronizandoInspectorScreen) {
            if (syncInspectorScreenRaf) {
                window.cancelAnimationFrame(syncInspectorScreenRaf);
            }

            syncInspectorScreenRaf = window.requestAnimationFrame(() => {
                syncInspectorScreenRaf = 0;
                sincronizarInspectorScreen();
            });
        }

        if (opts.emitirEvento !== false) {
            emitirEstadoInspectorSincronizado(snapshot);
        }

        return snapshot;
    }

    function sincronizarEstadoInspector(overrides = {}, opts = {}) {
        const snapshot = resolverEstadoAutoritativoInspector(overrides);
        return aplicarSnapshotEstadoInspector(snapshot, opts);
    }

    function obterSnapshotEstadoInspectorAtual() {
        if (estado.snapshotEstadoInspector) {
            return { ...estado.snapshotEstadoInspector };
        }

        return resolverEstadoAutoritativoInspector();
    }

    window.TarielInspectorState = Object.assign(
        window.TarielInspectorState || {},
        {
            resolverEstadoAutoritativoInspector,
            sincronizarEstadoInspector,
            obterSnapshotEstadoInspectorAtual,
            atualizarThreadWorkspace,
            state: estado.snapshotEstadoInspector ? { ...estado.snapshotEstadoInspector } : null,
        }
    );

    function definirRetomadaHomePendente(payload = null) {
        const snapshot = sincronizarEstadoInspector({
            retomadaHomePendente: payload ? normalizarRetomadaHomePendenteSeguro(payload) : null,
        });

        return snapshot.retomadaHomePendente;
    }

    function obterRetomadaHomePendente() {
        const snapshot = resolverEstadoAutoritativoInspector();
        return snapshot.retomadaHomePendente;
    }

    function normalizarEstadoRelatorio(valor) {
        const estadoBruto = String(valor || "").trim().toLowerCase();

        if (estadoBruto === "relatorioativo" || estadoBruto === "relatorio_ativo") {
            return "relatorio_ativo";
        }

        if (estadoBruto === "semrelatorio" || estadoBruto === "sem_relatorio") {
            return "sem_relatorio";
        }

        if (estadoBruto === "aguardando" || estadoBruto === "aguardando_avaliacao") {
            return "aguardando";
        }

        if (estadoBruto === "ajustes" || estadoBruto === "aprovado") {
            return estadoBruto;
        }

        return estadoBruto || "sem_relatorio";
    }

    function estadoRelatorioPossuiContexto(valor) {
        return normalizarEstadoRelatorio(valor) !== "sem_relatorio";
    }

    function obterContextoVisualAssistente() {
        return { ...CONTEXTO_WORKSPACE_ASSISTENTE };
    }

    function landingNovoChatAtivo(snapshot = obterSnapshotEstadoInspectorAtual()) {
        const payload = snapshot && typeof snapshot === "object" ? snapshot : {};
        const baseScreen = payload.inspectorBaseScreen || resolverInspectorBaseScreenPorSnapshot(payload);

        return normalizarModoInspecaoUI(payload.modoInspecaoUI) === "workspace"
            && baseScreen === "assistant_landing";
    }

    function conversaNovoChatFocadaAtiva(snapshot = obterSnapshotEstadoInspectorAtual()) {
        if (!normalizarBooleanoEstado(snapshot?.freeChatConversationActive, false)) {
            return false;
        }

        return !obterBaseRealConversaNovoChat(snapshot).pronta;
    }

    function obterTotalMensagensReaisWorkspace(snapshot = obterSnapshotEstadoInspectorAtual()) {
        const payload = snapshot && typeof snapshot === "object" ? snapshot : {};
        const totalHistorico = Math.max(
            0,
            Number(
                payload.historyRealCount ??
                estado.historyRealCount ??
                document.body?.dataset?.historyRealCount ??
                0
            ) || 0
        );

        return Math.max(totalHistorico, coletarLinhasWorkspace().length);
    }

    function conversaWorkspaceModoChatAtivo(
        screen = estado.inspectorScreen || resolveInspectorScreen(),
        snapshot = obterSnapshotEstadoInspectorAtual()
    ) {
        const payload = snapshot && typeof snapshot === "object" ? snapshot : {};
        const screenAtual = screen || payload.inspectorScreen || payload.inspectorBaseScreen || resolveInspectorScreen();
        const workspaceView = resolveWorkspaceView(screenAtual);
        const laudoAtivoId = normalizarLaudoAtualId(
            payload.laudoAtualId ??
            estado.laudoAtualId ??
            obterLaudoAtivoIdSeguro()
        );
        const estadoRelatorio = normalizarEstadoRelatorio(
            payload.estadoRelatorio ??
            estado.estadoRelatorio ??
            obterEstadoRelatorioAtualSeguro()
        );

        if (laudoAtivoId || estadoRelatorioPossuiContexto(estadoRelatorio)) {
            return false;
        }

        return normalizarModoInspecaoUI(payload.modoInspecaoUI) === "workspace"
            && workspaceView === "inspection_conversation"
            && (
                normalizarBooleanoEstado(payload.freeChatConversationActive, false)
                || obterTotalMensagensReaisWorkspace(payload) > 0
            );
    }

    function fluxoNovoChatFocadoAtivoOuPendente(snapshot = obterSnapshotEstadoInspectorAtual()) {
        return conversaNovoChatFocadaAtiva(snapshot)
            || !!normalizarBooleanoEstado(snapshot?.assistantLandingFirstSendPending, false);
    }

    function conversaNovoChatFocadaVisivel(
        screen = estado.inspectorScreen || resolveInspectorScreen(),
        snapshot = obterSnapshotEstadoInspectorAtual()
    ) {
        if (!conversaNovoChatFocadaAtiva(snapshot)) {
            return false;
        }

        return resolveWorkspaceView(screen) === "inspection_conversation";
    }

    function resolverConversationVariant(snapshot = obterSnapshotEstadoInspectorAtual()) {
        const payload = snapshot && typeof snapshot === "object" ? snapshot : {};
        const screen = payload.inspectorScreen || payload.inspectorBaseScreen || resolverInspectorBaseScreenPorSnapshot(payload);
        return conversaWorkspaceModoChatAtivo(screen, payload)
            ? "focused"
            : "technical";
    }

    function aplicarConversationVariantElemento(elemento, variant = "technical") {
        if (!elemento) return;
        elemento.dataset.conversationVariant = String(variant || "technical");
    }

    function sincronizarURLConversaFocada(
        variant = "technical",
        snapshot = obterSnapshotEstadoInspectorAtual()
    ) {
        if (variant !== "focused") {
            return;
        }

        try {
            const url = new URL(window.location.href);
            const laudoAtivo = normalizarLaudoAtualId(
                snapshot?.laudoAtualId ??
                obterLaudoAtivoIdSeguro() ??
                estado.laudoAtualId
            );
            const laudoAtualNaURL = url.searchParams.get("laudo") || "";
            const abaAtualNaURL = normalizarThreadTab(url.searchParams.get("aba") || "");

            if (!laudoAtivo && !laudoAtualNaURL && !abaAtualNaURL && !url.searchParams.get("home")) {
                return;
            }

            if (laudoAtivo) {
                url.searchParams.set("laudo", String(laudoAtivo));
                url.searchParams.set("aba", "conversa");
            } else {
                url.searchParams.delete("laudo");
                url.searchParams.delete("aba");
            }
            url.searchParams.delete("home");

            history.replaceState({
                ...(history.state && typeof history.state === "object" ? history.state : {}),
                laudoId: laudoAtivo,
                threadTab: "conversa",
            }, "", url.toString());
        } catch (_) {
            // silêncio intencional
        }
    }

    function sincronizarConversationVariantNoDom(snapshot = obterSnapshotEstadoInspectorAtual()) {
        const variant = resolverConversationVariant(snapshot);

        aplicarConversationVariantElemento(document.body, variant);
        aplicarConversationVariantElemento(el.painelChat, variant);
        aplicarConversationVariantElemento(el.workspaceScreenRoot, variant);
        aplicarConversationVariantElemento(el.workspaceHeader, variant);
        aplicarConversationVariantElemento(el.workspaceConversationViewRoot, variant);
        aplicarConversationVariantElemento(el.chatThreadToolbar, variant);
        aplicarConversationVariantElemento(el.rodapeEntrada, variant);
        aplicarConversationVariantElemento(el.areaMensagens || document.getElementById("area-mensagens"), variant);
        sincronizarURLConversaFocada(variant, snapshot);

        return variant;
    }

    function podeArmarPrimeiroEnvioNovoChat() {
        if (!el.campoMensagem || !el.btnEnviar) return false;
        if (!landingNovoChatAtivo()) return false;

        const texto = String(el.campoMensagem.value || "").trim();
        const iaRespondendo = document.body?.dataset?.iaRespondendo === "true"
            || String(el.btnEnviar.dataset?.action || "").trim().toLowerCase() === "stop";

        if (!texto || texto.startsWith("/") || iaRespondendo) {
            return false;
        }

        return true;
    }

    function armarPrimeiroEnvioNovoChatPendente() {
        if (!podeArmarPrimeiroEnvioNovoChat()) {
            return false;
        }

        const snapshot = obterSnapshotEstadoInspectorAtual();
        if (snapshot.assistantLandingFirstSendPending) {
            return true;
        }

        sincronizarEstadoInspector({
            assistantLandingFirstSendPending: true,
            freeChatConversationActive: false,
        }, {
            persistirStorage: false,
        });

        return true;
    }

    function limparFluxoNovoChatFocado() {
        const snapshot = obterSnapshotEstadoInspectorAtual();
        if (!snapshot.assistantLandingFirstSendPending && !snapshot.freeChatConversationActive) {
            return false;
        }

        sincronizarEstadoInspector({
            assistantLandingFirstSendPending: false,
            freeChatConversationActive: false,
        }, {
            persistirStorage: false,
        });

        return true;
    }

    function obterBaseRealConversaNovoChat(snapshot = obterSnapshotEstadoInspectorAtual()) {
        const totalMensagensReais = coletarLinhasWorkspace().length;
        const temContextoReal =
            !!normalizarLaudoAtualId(snapshot?.laudoAtualId) ||
            estadoRelatorioPossuiContexto(snapshot?.estadoRelatorio);

        return {
            totalMensagensReais,
            temContextoReal,
            pronta: totalMensagensReais > 0 || temContextoReal,
        };
    }

    function exibirConversaFocadaNovoChat({ tipoTemplate = estado.tipoTemplateAtivo, focarComposer = false } = {}) {
        const tipoNormalizado = normalizarTipoTemplate(tipoTemplate);
        const totalMensagensReais = coletarLinhasWorkspace().length;

        sincronizarResumoHistoricoWorkspace({ totalMensagensReais });
        sincronizarEstadoInspector({
            forceHomeLanding: false,
            modoInspecaoUI: "workspace",
            workspaceStage: "inspection",
            threadTab: "conversa",
            overlayOwner: "",
            assistantLandingFirstSendPending: false,
            freeChatConversationActive: true,
        }, {
            persistirStorage: false,
        });

        atualizarNomeTemplateAtivo(tipoNormalizado);
        atualizarControlesWorkspaceStage();
        atualizarContextoWorkspaceAtivo();
        atualizarThreadWorkspace("conversa");
        renderizarSugestoesComposer();
        atualizarStatusChatWorkspace(estado.chatStatusIA.status, estado.chatStatusIA.texto);

        if (focarComposer) {
            focarComposerInspector();
        }

        return true;
    }

    function promoverPrimeiraMensagemNovoChatSePronta({ forcar = false, focarComposer = false } = {}) {
        const snapshot = obterSnapshotEstadoInspectorAtual();
        if (!fluxoNovoChatFocadoAtivoOuPendente(snapshot)) {
            return false;
        }

        const base = obterBaseRealConversaNovoChat(snapshot);
        if (!forcar && !snapshot.freeChatConversationActive && !base.pronta) {
            return false;
        }

        return exibirConversaFocadaNovoChat({ focarComposer });
    }

    function normalizarFiltroPendencias(valor) {
        const filtro = String(valor || "").trim().toLowerCase();
        if (filtro === "abertas" || filtro === "resolvidas" || filtro === "todas") {
            return filtro;
        }
        return "abertas";
    }

    function obterEstadoRelatorioAtualSeguro() {
        return normalizarEstadoRelatorio(
            obterSnapshotEstadoInspectorAtual().estadoRelatorio || "sem_relatorio"
        );
    }

    function escaparHtml(texto = "") {
        return String(texto)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function formatarTamanhoBytes(totalBytes) {
        const valor = Number(totalBytes || 0);
        if (!Number.isFinite(valor) || valor <= 0) return "0 KB";
        if (valor >= 1024 * 1024) {
            return `${(valor / (1024 * 1024)).toFixed(1)} MB`;
        }
        return `${Math.max(1, Math.round(valor / 1024))} KB`;
    }

    function normalizarAnexoMesa(payload = {}) {
        const id = Number(payload?.id || 0) || null;
        const nome = String(payload?.nome || "").trim();
        const mimeType = String(payload?.mime_type || "").trim().toLowerCase();
        const categoria = String(payload?.categoria || "").trim().toLowerCase();
        const url = String(payload?.url || "").trim();
        if (!id || !nome || !url) return null;
        return {
            id,
            nome,
            mime_type: mimeType,
            categoria,
            url,
            tamanho_bytes: Number(payload?.tamanho_bytes || 0) || 0,
            eh_imagem: !!payload?.eh_imagem,
        };
    }

    function renderizarLinksAnexosMesa(anexos = []) {
        const itens = Array.isArray(anexos) ? anexos.filter(Boolean) : [];
        if (!itens.length) return "";

        return `
            <div class="mesa-widget-anexos">
                ${itens.map((anexo) => `
                    <a
                        class="anexo-mesa-link ${anexo?.eh_imagem ? "imagem" : "documento"}"
                        href="${escaparHtml(anexo?.url || "#")}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        <span class="material-symbols-rounded" aria-hidden="true">${anexo?.eh_imagem ? "image" : "description"}</span>
                        <span class="anexo-mesa-link-texto">
                            <strong>${escaparHtml(anexo?.nome || "anexo")}</strong>
                            <small>${escaparHtml(formatarTamanhoBytes(anexo?.tamanho_bytes || 0))}</small>
                        </span>
                    </a>
                `).join("")}
            </div>
        `;
    }

    function pluralizarWorkspace(total, singular, plural) {
        return Number(total || 0) === 1 ? singular : plural;
    }

    function obterSecaoSidebarLaudos(tab) {
        if (tab === "fixados") return document.getElementById("secao-laudos-pinados");
        if (tab === "recentes") return document.getElementById("secao-laudos-historico");
        return null;
    }

    function itemSidebarHistoricoEstaVisivel(item) {
        return !!item && !item.hidden && item.style.display !== "none";
    }

    function contarItensVisiveisSecaoSidebar(secao) {
        if (!secao) return 0;

        return Array.from(secao.querySelectorAll(".item-historico[data-laudo-id]"))
            .filter((item) => itemSidebarHistoricoEstaVisivel(item))
            .length;
    }

    function resolverSidebarLaudosTab(preferida = estado.sidebarLaudosTab) {
        const pinados = contarItensVisiveisSecaoSidebar(obterSecaoSidebarLaudos("fixados"));
        const recentes = contarItensVisiveisSecaoSidebar(obterSecaoSidebarLaudos("recentes"));

        if (preferida === "fixados" && pinados > 0) {
            return {
                ativa: "fixados",
                pinados,
                recentes,
            };
        }

        if (preferida === "recentes" && recentes > 0) {
            return {
                ativa: "recentes",
                pinados,
                recentes,
            };
        }

        if (recentes > 0) {
            return {
                ativa: "recentes",
                pinados,
                recentes,
            };
        }

        if (pinados > 0) {
            return {
                ativa: "fixados",
                pinados,
                recentes,
            };
        }

        return {
            ativa: preferida === "fixados" ? "fixados" : "recentes",
            pinados,
            recentes,
        };
    }

    function sincronizarSidebarLaudosTabs(preferida = estado.sidebarLaudosTab) {
        const sidebar = document.getElementById("barra-historico");
        const secaoPinados = obterSecaoSidebarLaudos("fixados");
        const secaoRecentes = obterSecaoSidebarLaudos("recentes");
        const resumo = resolverSidebarLaudosTab(preferida);
        const ativa = resumo.ativa;
        const usaAbas = Array.isArray(el.sidebarLaudosTabButtons) && el.sidebarLaudosTabButtons.length > 0;
        const totalItens = el.sidebarHistoricoLista
            ? el.sidebarHistoricoLista.querySelectorAll(".item-historico[data-laudo-id]").length
            : 0;

        estado.sidebarLaudosTab = ativa;
        if (sidebar && !usaAbas) {
            sidebar.dataset.sidebarLaudosView = "all";
        } else if (sidebar) {
            sidebar.dataset.sidebarLaudosView = ativa;
        }

        if (!usaAbas) {
            const totalVisiveis = resumo.pinados + resumo.recentes;

            if (secaoPinados) {
                secaoPinados.hidden = resumo.pinados === 0;
            }

            if (secaoRecentes) {
                secaoRecentes.hidden = resumo.recentes === 0;
            }

            return {
                ...resumo,
                totalItens,
                visiveisNaAbaAtiva: totalVisiveis,
            };
        }

        el.sidebarLaudosTabButtons.forEach((botao) => {
            const tab = String(botao.dataset.sidebarLaudosTabTrigger || "").trim().toLowerCase();
            const ativo = tab === ativa;
            const habilitado = tab === "fixados" ? resumo.pinados > 0 : resumo.recentes > 0;
            botao.classList.toggle("is-active", ativo);
            botao.setAttribute("aria-selected", ativo ? "true" : "false");
            botao.disabled = !habilitado;
            botao.setAttribute("aria-disabled", habilitado ? "false" : "true");
        });

        if (secaoPinados) {
            secaoPinados.hidden = resumo.pinados === 0 || ativa !== "fixados";
        }

        if (secaoRecentes) {
            secaoRecentes.hidden = resumo.recentes === 0 || ativa !== "recentes";
        }

        return {
            ...resumo,
            totalItens,
            visiveisNaAbaAtiva: ativa === "fixados" ? resumo.pinados : resumo.recentes,
        };
    }

    function filtrarSidebarHistorico(termo = "") {
        const termoNormalizado = String(termo || "").trim().toLowerCase();
        estado.termoBuscaSidebar = termoNormalizado;
        const itens = el.sidebarHistoricoLista
            ? Array.from(el.sidebarHistoricoLista.querySelectorAll(".inspetor-sidebar-report, .item-historico"))
            : [];

        let visiveis = 0;
        itens.forEach((item) => {
            const texto = String(item.textContent || "").trim().toLowerCase();
            const match = !termoNormalizado || texto.includes(termoNormalizado);
            item.hidden = !match;
            if (match) {
                visiveis += 1;
            }
        });

        const resumoTabs = sincronizarSidebarLaudosTabs(estado.sidebarLaudosTab);

        if (el.sidebarBuscaVazio) {
            const semItens = resumoTabs.totalItens === 0;
            const semResultados = termoNormalizado && resumoTabs.visiveisNaAbaAtiva === 0 && visiveis === 0;
            el.sidebarBuscaVazio.hidden = !(semItens || semResultados);
        }
    }

    function obterListaComandosSlash(query = "") {
        const termo = String(query || "").trim().toLowerCase();
        if (!termo) return [...COMANDOS_SLASH];
        return COMANDOS_SLASH.filter((comando) => {
            const universo = [
                comando.id,
                comando.titulo,
                comando.descricao,
                comando.atalho,
            ].join(" ").toLowerCase();
            return universo.includes(termo);
        });
    }

    function fecharSlashCommandPalette() {
        estado.slashIndiceAtivo = 0;
        if (el.slashCommandPalette) {
            el.slashCommandPalette.hidden = true;
            el.slashCommandPalette.innerHTML = "";
        }
    }

    function renderizarSlashCommandPalette(query = "") {
        if (!el.slashCommandPalette) return;

        const lista = obterListaComandosSlash(query);
        if (!lista.length) {
            el.slashCommandPalette.hidden = false;
            el.slashCommandPalette.innerHTML = `
                <div class="slash-command-item is-active">
                    <div>
                        <strong>Nenhum comando encontrado</strong>
                        <p>Tente /resumir, /pendencias, /mesa ou /gerar-conclusao.</p>
                    </div>
                    <kbd>Esc</kbd>
                </div>
            `;
            return;
        }

        estado.slashIndiceAtivo = Math.max(0, Math.min(estado.slashIndiceAtivo, lista.length - 1));
        el.slashCommandPalette.hidden = false;
        el.slashCommandPalette.innerHTML = lista
            .map((comando, index) => `
                <button
                    type="button"
                    class="slash-command-item${index === estado.slashIndiceAtivo ? " is-active" : ""}"
                    data-slash-command="${escaparHtml(comando.id)}"
                >
                    <div>
                        <strong>${escaparHtml(comando.atalho)}</strong>
                        <p>${escaparHtml(comando.descricao)}</p>
                    </div>
                    <kbd>${escaparHtml(comando.titulo)}</kbd>
                </button>
            `)
            .join("");
    }

    function definirValorComposer(texto = "", { substituir = true } = {}) {
        if (!el.campoMensagem) return false;

        const valorNovo = String(texto || "").trim();
        if (!valorNovo) return false;

        el.campoMensagem.value = substituir
            ? valorNovo
            : [String(el.campoMensagem.value || "").trim(), valorNovo].filter(Boolean).join("\n");
        el.campoMensagem.dispatchEvent(new Event("input", { bubbles: true }));

        try {
            el.campoMensagem.focus({ preventScroll: true });
        } catch (_) {
            el.campoMensagem.focus();
        }

        if (typeof el.campoMensagem.setSelectionRange === "function") {
            const fim = el.campoMensagem.value.length;
            el.campoMensagem.setSelectionRange(fim, fim);
        }

        return true;
    }

    async function abrirMesaComContexto(detail = {}) {
        if (!obterLaudoAtivoIdSeguro()) {
            avisarMesaExigeInspecao();
            return;
        }

        atualizarThreadWorkspace("mesa", {
            persistirURL: true,
            replaceURL: true,
        });
        await abrirMesaWidget();

        const mensagemId = Number(detail?.mensagemId || 0) || null;
        const textoBase = String(detail?.texto || "").trim();
        if (mensagemId && textoBase) {
            definirReferenciaMesaWidget({
                id: mensagemId,
                texto: textoBase,
            });
        }

        if (el.mesaWidgetInput) {
            const mensagem = String(detail?.mensagem || "").trim() || (
                textoBase
                    ? `Preciso de validação da mesa sobre este trecho:\n\n"${textoBase}"`
                    : "Solicito validação da mesa para este laudo."
            );
            el.mesaWidgetInput.value = mensagem;
            el.mesaWidgetInput.dispatchEvent(new Event("input", { bubbles: true }));
            el.mesaWidgetInput.focus();
        }

        atualizarStatusChatWorkspace("mesa", "Canal da mesa pronto para revisão.");
        mostrarToast("Canal da mesa aberto com contexto aplicado.", "sucesso", 1800);
    }

    function montarMensagemReemissaoWorkspace(detail = {}) {
        const resumoGovernanca = construirResumoGovernancaHistoricoWorkspace();
        const partes = ["Solicito revisão para reemissão do documento oficial deste caso."];

        if (resumoGovernanca.visible && resumoGovernanca.detail) {
            partes.push(resumoGovernanca.detail);
        }

        const textoBase = String(detail?.texto || "").trim();
        if (textoBase) {
            partes.push(`Trecho de apoio:\n\n"${textoBase}"`);
        }

        return partes.join("\n\n");
    }

    async function abrirReemissaoWorkspace(detail = {}) {
        await abrirMesaComContexto({
            ...detail,
            mensagem: montarMensagemReemissaoWorkspace(detail),
        });
    }

    function obterEntradaReemissaoWorkspace(detail = {}) {
        const snapshot = obterSnapshotEstadoInspectorAtual();
        const laudoAtivoId = normalizarLaudoAtualId(snapshot?.laudoAtualId);
        const resumoGovernanca = construirResumoGovernancaHistoricoWorkspace();

        if (!laudoAtivoId || !estadoRelatorioPossuiContexto(snapshot?.estadoRelatorio) || !resumoGovernanca.visible) {
            return null;
        }

        return {
            ...detail,
            laudoId: laudoAtivoId,
            resumoGovernanca,
            texto: String(detail?.texto || "").trim(),
        };
    }

    function limparComposerWorkspace() {
        if (!el.campoMensagem) return;
        el.campoMensagem.value = "";
        el.campoMensagem.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function obterTextoDeApoioComposer() {
        const texto = String(el.campoMensagem?.value || "").trim();
        if (!texto || texto.startsWith("/")) {
            return "";
        }
        return texto;
    }

    function redirecionarEntradaParaReemissaoWorkspace(detail = {}) {
        const entrada = obterEntradaReemissaoWorkspace(detail);
        if (!entrada) return false;

        if (detail?.limparComposer) {
            limparComposerWorkspace();
        }

        abrirReemissaoWorkspace(entrada).catch(() => {});
        return true;
    }

    function executarComandoSlash(comandoId, { origem = "palette" } = {}) {
        const comando = COMANDOS_SLASH.find((item) => item.id === comandoId);
        if (!comando) return false;

        fecharSlashCommandPalette();

        if (comando.id === "mesa") {
            const redirecionado = redirecionarEntradaParaReemissaoWorkspace({
                origem: `slash_${origem}`,
                texto: obterTextoDeApoioComposer(),
                limparComposer: true,
            });
            if (!redirecionado) {
                abrirMesaComContexto({
                    mensagem: `Solicito validação da mesa sobre este laudo.\n\n${montarResumoContextoIAWorkspace()}`,
                }).catch(() => {});
            }
            if (el.campoMensagem) {
                el.campoMensagem.value = "";
                el.campoMensagem.dispatchEvent(new Event("input", { bubbles: true }));
            }
            return true;
        }

        const aplicado = definirValorComposer(comando.prompt, { substituir: true });
        if (aplicado && origem !== "atalho") {
            mostrarToast(`${comando.atalho} aplicado no composer.`, "info", 1800);
        }
        return aplicado;
    }

    function renderizarSugestoesComposer() {
        if (!el.composerSuggestions) return;

        if (resolveWorkspaceView() === "assistant_landing") {
            const sugestoesEntrada = SUGESTOES_ENTRADA_ASSISTENTE.slice(0, 3);
            el.composerSuggestions.innerHTML = sugestoesEntrada
                .map((sugestao) => `
                    <button
                        type="button"
                        class="composer-suggestion composer-suggestion--entry"
                        data-suggestion-text="${escaparHtml(sugestao.prompt)}"
                        data-suggestion-priority="${escaparHtml(sugestao.prioridade || "secondary")}"
                    >
                        <span>${escaparHtml(sugestao.titulo)}</span>
                    </button>
                `)
                .join("");
            return;
        }

        if (conversaWorkspaceModoChatAtivo()) {
            el.composerSuggestions.innerHTML = "";
            return;
        }

        const resumoGovernanca = construirResumoGovernancaHistoricoWorkspace();
        const sugestoes = COMANDOS_SLASH
            .filter((comando) => comando.sugestao)
            .filter((comando) => !resumoGovernanca.visible || comando.id !== "mesa")
            .slice(0, resumoGovernanca.visible ? 2 : 3);
        const sugestoesMarkup = [];

        if (resumoGovernanca.visible) {
            sugestoesMarkup.push(`
                <button
                    type="button"
                    class="composer-suggestion composer-suggestion--warning"
                    data-suggestion-action="reissue"
                >
                    <span class="material-symbols-rounded" aria-hidden="true">warning</span>
                    <span>${escaparHtml(resumoGovernanca.actionLabel || "Abrir reemissão na Mesa")}</span>
                </button>
            `);
        }

        sugestoesMarkup.push(...sugestoes.map((comando) => `
                <button
                    type="button"
                    class="composer-suggestion"
                    data-suggestion-command="${escaparHtml(comando.id)}"
                >
                    <span class="material-symbols-rounded" aria-hidden="true">${escaparHtml(comando.icone)}</span>
                    <span>${escaparHtml(comando.titulo)}</span>
                </button>
            `));

        el.composerSuggestions.innerHTML = sugestoesMarkup.join("");
    }

    function atualizarRecursosComposerWorkspace() {
        const valor = String(el.campoMensagem?.value || "").trimStart();
        if (valor.startsWith("/")) {
            renderizarSlashCommandPalette(valor.slice(1));
        } else {
            fecharSlashCommandPalette();
        }
    }

    function registrarPromptHistorico(texto = "") {
        const valor = String(texto || "").trim();
        if (!valor) return;

        estado.historicoPrompts = [
            valor,
            ...(estado.historicoPrompts || []).filter((item) => item !== valor),
        ].slice(0, 20);
        estado.indiceHistoricoPrompt = -1;
        estado.rascunhoHistoricoPrompt = "";
    }

    function navegarHistoricoPrompts(direcao = -1) {
        const historico = Array.isArray(estado.historicoPrompts) ? estado.historicoPrompts : [];
        if (!historico.length || !el.campoMensagem) return false;

        if (estado.indiceHistoricoPrompt === -1) {
            estado.rascunhoHistoricoPrompt = String(el.campoMensagem.value || "");
        }

        const proximoIndice = estado.indiceHistoricoPrompt + direcao;
        if (proximoIndice < -1 || proximoIndice >= historico.length) return false;

        estado.indiceHistoricoPrompt = proximoIndice;
        const proximoValor = proximoIndice === -1
            ? estado.rascunhoHistoricoPrompt
            : historico[proximoIndice];

        el.campoMensagem.value = proximoValor;
        el.campoMensagem.dispatchEvent(new Event("input", { bubbles: true }));
        return true;
    }

    function onCampoMensagemWorkspaceKeydown(event) {
        const valor = String(el.campoMensagem?.value || "").trimStart();
        const paletteAberto = !el.slashCommandPalette?.hidden && valor.startsWith("/");

        if (paletteAberto) {
            const lista = obterListaComandosSlash(valor.slice(1));

            if (event.key === "ArrowDown") {
                event.preventDefault();
                event.stopImmediatePropagation();
                estado.slashIndiceAtivo = Math.min(
                    Math.max(lista.length - 1, 0),
                    estado.slashIndiceAtivo + 1
                );
                renderizarSlashCommandPalette(valor.slice(1));
                return;
            }

            if (event.key === "ArrowUp") {
                event.preventDefault();
                event.stopImmediatePropagation();
                estado.slashIndiceAtivo = Math.max(0, estado.slashIndiceAtivo - 1);
                renderizarSlashCommandPalette(valor.slice(1));
                return;
            }

            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.stopImmediatePropagation();
                const comando = lista[estado.slashIndiceAtivo] || lista[0];
                if (comando) {
                    executarComandoSlash(comando.id);
                }
                return;
            }

            if (event.key === "Escape") {
                fecharSlashCommandPalette();
                return;
            }
        }

        if (event.altKey && event.key === "ArrowUp") {
            if (navegarHistoricoPrompts(1)) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
            return;
        }

        if (event.altKey && event.key === "ArrowDown") {
            if (navegarHistoricoPrompts(-1)) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
            return;
        }

        if (
            event.key === "Enter" &&
            !event.shiftKey &&
            !event.altKey &&
            !event.ctrlKey &&
            !event.metaKey
        ) {
            const textoComposer = obterTextoDeApoioComposer();
            if (textoComposer && redirecionarEntradaParaReemissaoWorkspace({
                origem: "composer_enter",
                texto: textoComposer,
                limparComposer: true,
            })) {
                event.preventDefault();
                event.stopImmediatePropagation();
                return;
            }
            prepararComposerParaEnvioModoEntrada();
            armarPrimeiroEnvioNovoChatPendente();
        }
    }

    function prepararComposerParaEnvioModoEntrada() {
        if (!modoEntradaEvidenceFirstAtivo()) return;

        const snapshot = obterSnapshotEstadoInspectorAtual();
        if (snapshot.workspaceStage !== "inspection") return;

        const viewAtual = resolveWorkspaceView(snapshot.inspectorScreen || resolveInspectorScreen());
        if (viewAtual !== "inspection_record") return;

        atualizarThreadWorkspace("conversa", {
            persistirURL: true,
            replaceURL: true,
        });
    }

    function citarMensagemWorkspace(detail = {}) {
        const texto = String(detail?.texto || "").trim() || (
            Array.isArray(detail?.anexos)
                ? detail.anexos.map((anexo) => String(anexo?.nome || "").trim()).filter(Boolean).join(" • ")
                : ""
        );
        if (!texto) return;

        const autor = String(detail?.autor || "Registro").trim() || "Registro";
        definirValorComposer(`> ${autor}: ${texto}`, { substituir: false });
        mostrarToast("Trecho citado no composer.", "info", 1800);
    }

    function normalizarPapelLinhaWorkspace(linha) {
        if (!linha) return "assistant";
        if (linha.classList.contains("mensagem-sistema")) return "system";
        if (linha.classList.contains("mensagem-origem-mesa")) return "mesa";
        if (linha.classList.contains("mensagem-inspetor") || linha.classList.contains("mensagem-usuario")) return "user";
        return "assistant";
    }

    function aplicarModifierLinhaWorkspace(linha, papel = "assistant") {
        if (!linha) return;

        linha.classList.add("workspace-message-row");
        linha.classList.remove(
            "workspace-message-row--assistant",
            "workspace-message-row--user",
            "workspace-message-row--mesa",
            "workspace-message-row--system"
        );

        if (papel === "user") {
            linha.classList.add("workspace-message-row--user");
        } else if (papel === "mesa") {
            linha.classList.add("workspace-message-row--mesa");
        } else if (papel === "system") {
            linha.classList.add("workspace-message-row--system");
        } else {
            linha.classList.add("workspace-message-row--assistant");
        }

        linha.dataset.messageVariant = papel;
    }

    function normalizarEstruturaLinhaWorkspace(linha) {
        if (!linha) return { papel: "assistant", corpo: null };

        const papel = normalizarPapelLinhaWorkspace(linha);
        aplicarModifierLinhaWorkspace(linha, papel);

        const shell = linha.querySelector(".conteudo-mensagem");
        if (shell) {
            shell.classList.add("workspace-message-shell");
        }

        const avatar = linha.querySelector(".avatar");
        if (avatar) {
            avatar.classList.add("workspace-message-avatar");
        }

        const corpo = linha.querySelector(".corpo-texto");
        if (!corpo) {
            return { papel, corpo: null };
        }

        corpo.classList.add("workspace-message-card");
        corpo.querySelectorAll(".mensagem-meta").forEach((meta) => {
            meta.classList.add("workspace-message-meta");
        });
        corpo.querySelectorAll(".texto-msg, .texto-msg-origem").forEach((blocoTexto) => {
            blocoTexto.classList.add("workspace-message-body");
        });
        corpo.querySelectorAll(".bloco-referencia-chat").forEach((referencia) => {
            referencia.classList.add("workspace-message-reference");
        });
        corpo.querySelectorAll(".mensagem-anexos").forEach((anexos) => {
            anexos.classList.add("workspace-message-attachments");
        });
        corpo.querySelectorAll(".mensagem-anexo-chip").forEach((chip) => {
            chip.classList.add("workspace-message-attachment");
        });

        const blocosAcoes = Array.from(linha.querySelectorAll(".acoes-mensagem, .workspace-message-actions"));
        let blocoPrincipal = null;
        blocosAcoes.forEach((bloco) => {
            if (!blocoPrincipal) {
                blocoPrincipal = bloco;
                return;
            }
            bloco.remove();
        });

        if (blocoPrincipal) {
            blocoPrincipal.classList.add("workspace-message-actions");
            blocoPrincipal.querySelectorAll(".sep-acao").forEach((separador) => {
                separador.remove();
            });
            blocoPrincipal.querySelectorAll(".btn-acao-msg, .workspace-message-action").forEach((botao) => {
                botao.classList.add("workspace-message-action");
                const spans = botao.querySelectorAll("span");
                if (spans.length <= 1) {
                    botao.classList.add("workspace-message-action--icon-only");
                }
            });
            if (blocoPrincipal.parentElement !== corpo) {
                corpo.appendChild(blocoPrincipal);
            }
        }

        return { papel, corpo };
    }

    function criarBotaoAcaoWorkspace(icone, rotulo, nomeEvento, detalhe) {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "workspace-message-action";
        botao.dataset.workspaceAction = nomeEvento;
        botao.innerHTML = `
            <span class="material-symbols-rounded" aria-hidden="true">${icone}</span>
            <span>${escaparHtml(rotulo)}</span>
        `;
        botao.addEventListener("click", () => {
            document.dispatchEvent(new CustomEvent(`tariel:mensagem-${nomeEvento}`, {
                detail: detalhe,
                bubbles: true,
            }));
        });
        return botao;
    }

    function decorarLinhasWorkspace() {
        coletarLinhasWorkspace().forEach((linha) => {
            const { papel, corpo } = normalizarEstruturaLinhaWorkspace(linha);
            if (!corpo || papel === "assistant" || papel === "system") return;
            if (linha.querySelector(".workspace-message-actions")) return;

            const detalhe = obterDetalheLinhaWorkspace(linha);
            if (!detalhe.texto) return;

            const acoes = document.createElement("div");
            acoes.className = `workspace-message-actions workspace-message-actions--${papel}`;
            acoes.appendChild(criarBotaoAcaoWorkspace("content_copy", "Copiar", "copiar", detalhe));
            acoes.appendChild(criarBotaoAcaoWorkspace("format_quote", "Citar", "citar", detalhe));
            acoes.appendChild(criarBotaoAcaoWorkspace("support_agent", "Mesa", "enviar-mesa", detalhe));
            acoes.appendChild(criarBotaoAcaoWorkspace("keep", "Fixar", "fixar-contexto", detalhe));
            corpo.appendChild(acoes);
        });
    }

    function coletarLinhasWorkspace() {
        return Array.from(document.querySelectorAll("#area-mensagens .linha-mensagem"))
            .filter((linha) => linha.id !== "indicador-digitando");
    }

    function atualizarThreadWorkspace(tab = "conversa", options = {}) {
        const { persistirURL = false, replaceURL = false } = options && typeof options === "object"
            ? options
            : {};
        const tabNormalizada = normalizarThreadTab(tab);

        sincronizarEstadoInspector({
            threadTab: tabNormalizada,
            ...(tabNormalizada !== "conversa"
                ? {
                    assistantLandingFirstSendPending: false,
                    freeChatConversationActive: false,
                }
                : {}),
        }, { persistirStorage: false });

        if (typeof window.TarielChatPainel?.selecionarThreadTab === "function") {
            window.TarielChatPainel.selecionarThreadTab(tabNormalizada, { emit: false });
        }
        if (persistirURL && typeof window.TarielChatPainel?.definirThreadTabNaURL === "function") {
            window.TarielChatPainel.definirThreadTabNaURL(tabNormalizada, {
                replace: replaceURL,
                laudoId: obterLaudoAtivoIdSeguro() || estado.laudoAtualId || null,
            });
        }
        if (el.workspaceAnexosPanel) {
            el.workspaceAnexosPanel.setAttribute(
                "aria-hidden",
                String(tabNormalizada !== "anexos")
            );
        }

        if (tabNormalizada === "anexos") {
            renderizarAnexosWorkspace();
        } else if (tabNormalizada === "historico") {
            filtrarTimelineWorkspace();
        }

        renderizarResumoNavegacaoWorkspace();
        sincronizarInspectorScreen();
        window.requestAnimationFrame(() => {
            atualizarControlesWorkspaceStage();
        });
    }

    function montarDiagnosticoPreviewWorkspace() {
        const diagnosticoAtual = String(window.TarielAPI?.obterUltimoDiagnosticoBruto?.() || "").trim();
        if (diagnosticoAtual) {
            return diagnosticoAtual;
        }

        const linhas = coletarLinhasWorkspace();
        if (!linhas.length) {
            return "";
        }

        const titulo = String(estado.workspaceVisualContext?.title || "Registro Técnico").trim();
        const subtitulo = String(estado.workspaceVisualContext?.subtitle || "").trim();
        const pendencias = Number(estado.qtdPendenciasAbertas || 0) || 0;
        const evidencias = contarEvidenciasWorkspace();
        const blocos = [
            `Registro Técnico: ${titulo}`,
            subtitulo || "Sem subtítulo operacional disponível.",
            `Evidências mapeadas: ${evidencias}`,
            `Pendências abertas: ${pendencias}`,
            "",
            "Resumo auditável da sessão:",
        ];

        linhas.slice(-12).forEach((linha) => {
            const meta = extrairMetaLinhaWorkspace(linha);
            const resumo = String(meta.resumo || "").trim();
            if (!resumo) return;

            const prefixo = [meta.autor, meta.tempo].filter(Boolean).join(" • ");
            blocos.push(`- ${prefixo ? `${prefixo}: ` : ""}${resumo}`);
        });

        return blocos.join("\n").trim();
    }

    async function abrirPreviewWorkspace() {
        const diagnostico = montarDiagnosticoPreviewWorkspace();
        if (!diagnostico) {
            mostrarToast("Ainda não há pré-visualização disponível para este laudo.", "aviso", 2600);
            return;
        }

        const laudoId = Number(obterLaudoAtivoIdSeguro() || 0) || null;
        const response = await fetch("/app/api/gerar_pdf", {
            method: "POST",
            credentials: "same-origin",
            headers: obterHeadersComCSRF({
                Accept: "application/pdf",
                "Content-Type": "application/json",
            }),
            body: JSON.stringify({
                diagnostico,
                inspetor: String(window.TARIEL?.usuario || "Inspetor"),
                empresa: String(window.TARIEL?.empresa || "Empresa"),
                setor: "geral",
                data: new Date().toLocaleDateString("pt-BR"),
                laudo_id: laudoId,
                tipo_template: String(estado.tipoTemplateAtivo || "padrao"),
            }),
        });

        if (!response.ok) {
            throw new Error(await extrairMensagemErroHTTP(response, "Falha ao abrir a pré-visualização."));
        }

        const contentType = String(response.headers.get("content-type") || "").toLowerCase();
        if (!contentType.includes("application/pdf")) {
            throw new Error("Resposta inválida para pré-visualização.");
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const previewTab = window.open(url, "_blank", "noopener,noreferrer");

        if (!previewTab) {
            const link = document.createElement("a");
            link.href = url;
            link.download = `preview_laudo_${laudoId || "tariel"}.pdf`;
            document.body.appendChild(link);
            link.click();
            link.remove();
        }

        window.setTimeout(() => URL.revokeObjectURL(url), 45000);
    }
    function obterElementosFocaveis(container) {
        if (!container) return [];

        return Array.from(
            container.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            )
        ).filter((node) =>
            !node.disabled &&
            !node.hidden &&
            !node.classList?.contains("select-proxy-ativo") &&
            node.getClientRects().length > 0
        );
    }

    function limparTimerBanner() {
        if (!estado.timerBanner) return;
        window.clearTimeout(estado.timerBanner);
        estado.timerBanner = null;
    }

    function limparTimerReconexaoSSE() {
        if (!estado.timerReconexaoSSE) return;
        window.clearTimeout(estado.timerReconexaoSSE);
        estado.timerReconexaoSSE = null;
    }

    function limparTimerFecharMesaWidget() {
        if (!estado.timerFecharMesaWidget) return;
        window.clearTimeout(estado.timerFecharMesaWidget);
        estado.timerFecharMesaWidget = null;
    }

    function ehAbortError(erro) {
        return erro?.name === "AbortError" || erro?.code === DOMException.ABORT_ERR;
    }

    function cancelarCarregamentoPendenciasMesa() {
        if (!estado.pendenciasAbortController) return;
        estado.pendenciasAbortController.abort();
        estado.pendenciasAbortController = null;
        estado.carregandoPendencias = false;
    }

    function cancelarCarregamentoMensagensMesaWidget() {
        if (!estado.mesaWidgetAbortController) return;
        estado.mesaWidgetAbortController.abort();
        estado.mesaWidgetAbortController = null;
        estado.mesaWidgetCarregando = false;
    }

    function fecharSSE(fonte = estado.fonteSSE) {
        if (!fonte) return;

        try {
            fonte.close();
        } catch (_) {
            // silêncio intencional
        }

        if (estado.fonteSSE === fonte) {
            estado.fonteSSE = null;
        }
    }

    function definirBotaoIniciarCarregando(ativo) {
        if (!el.btnConfirmarInspecao) return;

        const rotulo = ativo ? "Criando..." : "Criar Inspeção";
        const alvoTexto = el.btnConfirmarInspecao.querySelector("span:last-child");
        if (alvoTexto) {
            alvoTexto.textContent = rotulo;
        } else {
            el.btnConfirmarInspecao.textContent = rotulo;
        }
        el.btnConfirmarInspecao.setAttribute("aria-busy", String(!!ativo));
        atualizarEstadoAcaoModalNovaInspecao();
    }

    function definirBotaoFinalizarCarregando(ativo) {
        const botoes = el.botoesFinalizarInspecao?.length
            ? el.botoesFinalizarInspecao
            : (el.btnFinalizarInspecao ? [el.btnFinalizarInspecao] : []);

        botoes.forEach((botao) => {
            botao.disabled = !!ativo;
            botao.setAttribute("aria-busy", String(!!ativo));
        });
        sincronizarRotuloAcaoFinalizacaoWorkspace({ carregando: !!ativo });
    }

    function definirBotaoPreviewCarregando(ativo) {
        [el.btnWorkspacePreview, el.btnWorkspacePreviewRail].forEach((botao) => {
            if (!botao) return;
            botao.disabled = !!ativo;
            botao.setAttribute("aria-busy", String(!!ativo));
            botao.textContent = ativo ? "Gerando..." : "Pré-visualizar";
        });
    }

    function definirBotaoLaudoCarregando(botao, ativo) {
        if (!botao) return;

        botao.disabled = !!ativo;
        botao.setAttribute("aria-busy", String(!!ativo));
    }

    function normalizarStatusMesa(valor) {
        const status = String(valor || "").trim().toLowerCase();

        if (!status) return "pronta";
        if (status === "canal" || status === "ativo") return "canal_ativo";
        if (status === "pendencia" || status === "pendencia_aberta") return "pendencia_aberta";

        return CONFIG_STATUS_MESA[status] ? status : "pronta";
    }

    function obterLaudoAtivo() {
        return Number(window.TarielAPI?.obterLaudoAtualId?.() || 0) || null;
    }

    function avisarMesaExigeInspecao() {
        mostrarToast(MENSAGEM_MESA_EXIGE_INSPECAO, "aviso", 3200);
    }

    function emitirSincronizacaoLaudo(payload = {}, { selecionar = false } = {}) {
        const laudoId = Number(
            payload?.laudo_id ??
            payload?.laudoId ??
            payload?.laudo_card?.id ??
            0
        ) || null;
        const payloadSincronizado = laudoId
            ? enriquecerPayloadLaudoComContextoVisual(
                payload,
                obterContextoVisualLaudoRegistrado(laudoId)
            )
            : payload;
        registrarUltimoPayloadStatusRelatorioWorkspace(payloadSincronizado);

        if (payloadSincronizado?.laudo_card?.id) {
            emitirEventoTariel("tariel:laudo-card-sincronizado", {
                card: payloadSincronizado.laudo_card,
                selecionar,
            });
        }

        if (!payloadSincronizado?.estado) return;

        emitirEventoTariel("tariel:estado-relatorio", {
            estado: payloadSincronizado.estado,
            laudo_id: payloadSincronizado.laudo_id ?? payloadSincronizado.laudoId ?? payloadSincronizado?.laudo_card?.id ?? null,
            permite_reabrir: !!payloadSincronizado.permite_reabrir,
            permite_edicao: !!payloadSincronizado.permite_edicao,
            status_card: payloadSincronizado.status_card || payloadSincronizado?.laudo_card?.status_card || "",
            case_lifecycle_status:
                payloadSincronizado.case_lifecycle_status ??
                payloadSincronizado?.laudo_card?.case_lifecycle_status ??
                "",
            case_workflow_mode:
                payloadSincronizado.case_workflow_mode ??
                payloadSincronizado?.laudo_card?.case_workflow_mode ??
                "",
            active_owner_role:
                payloadSincronizado.active_owner_role ??
                payloadSincronizado?.laudo_card?.active_owner_role ??
                "",
            allowed_next_lifecycle_statuses:
                payloadSincronizado.allowed_next_lifecycle_statuses ??
                payloadSincronizado?.laudo_card?.allowed_next_lifecycle_statuses ??
                [],
            allowed_lifecycle_transitions:
                payloadSincronizado.allowed_lifecycle_transitions ??
                payloadSincronizado?.laudo_card?.allowed_lifecycle_transitions ??
                [],
            allowed_surface_actions:
                payloadSincronizado.allowed_surface_actions ??
                payloadSincronizado?.laudo_card?.allowed_surface_actions ??
                [],
            entry_mode_preference:
                payloadSincronizado.entry_mode_preference ??
                payloadSincronizado.entryModePreference ??
                payloadSincronizado?.laudo_card?.entry_mode_preference ??
                null,
            entry_mode_effective:
                payloadSincronizado.entry_mode_effective ??
                payloadSincronizado.entryModeEffective ??
                payloadSincronizado?.laudo_card?.entry_mode_effective ??
                null,
            entry_mode_reason:
                payloadSincronizado.entry_mode_reason ??
                payloadSincronizado.entryModeReason ??
                payloadSincronizado?.laudo_card?.entry_mode_reason ??
                null,
            public_verification:
                payloadSincronizado.public_verification ??
                null,
            emissao_oficial:
                payloadSincronizado.emissao_oficial ??
                null,
        });
    }

    function obterTokenCsrf() {
        return document.querySelector('meta[name="csrf-token"]')?.content || "";
    }

    function limparEstadoHomeNoCliente() {
        try {
            localStorage.removeItem("tariel_laudo_atual");
        } catch (_) {
            // silêncio intencional
        }

        try {
            const url = new URL(window.location.href);
            url.searchParams.delete("laudo");
            url.searchParams.delete("aba");
            history.replaceState({ laudoId: null, threadTab: null }, "", url.toString());
        } catch (_) {
            // silêncio intencional
        }

        sincronizarEstadoInspector({
            laudoAtualId: null,
            forceHomeLanding: false,
        }, {
            persistirStorage: false,
        });
    }

    async function desativarContextoAtivoParaHome() {
        const laudoAtivo = obterLaudoAtivo();
        const estadoAtual = obterEstadoRelatorioAtualSeguro();

        if (!laudoAtivo && estadoAtual !== "relatorio_ativo") {
            return true;
        }

        try {
            const resposta = await fetch("/app/api/laudo/desativar", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Accept": "application/json",
                    "X-CSRF-Token": obterTokenCsrf(),
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            return resposta.ok;
        } catch (_) {
            return false;
        }
    }

    function marcarForcaTelaInicial() {
        sincronizarEstadoInspector({ forceHomeLanding: true });
    }

    function paginaSolicitaHomeLanding() {
        const snapshot = obterSnapshotEstadoInspectorAtual();
        return !!snapshot.forceHomeLanding || lerFlagForcaHomeStorage() || paginaSolicitaHomeLandingViaURL();
    }

    function limparForcaTelaInicial() {
        sincronizarEstadoInspector({ forceHomeLanding: false });

        try {
            const url = new URL(window.location.href);
            if (url.searchParams.get("home") === "1") {
                url.searchParams.delete("home");
                history.replaceState(history.state || {}, "", url.toString());
            }
        } catch (_) {
            // silêncio intencional
        }
    }

    function homeForcadoAtivo() {
        return !!obterSnapshotEstadoInspectorAtual().forceHomeLanding || paginaSolicitaHomeLandingViaURL();
    }

    function entradaChatLivreDisponivel(snapshot = obterSnapshotEstadoInspectorAtual()) {
        return !normalizarLaudoAtualId(snapshot?.laudoAtualId) && !estadoRelatorioPossuiContexto(snapshot?.estadoRelatorio);
    }

    function origemChatLivreEhPortal(origem = "") {
        return String(origem || "").trim() === "portal-open-chat";
    }

    function resolverDisponibilidadeBotaoChatLivre(botao, snapshot = obterSnapshotEstadoInspectorAtual()) {
        if (!botao) return false;

        if (origemChatLivreEhPortal(botao.dataset.inspectorEntry)) {
            return true;
        }

        return entradaChatLivreDisponivel(snapshot);
    }

    function modoFocoPodePromoverPortalParaChat(snapshot = obterSnapshotEstadoInspectorAtual()) {
        if (!document.body.classList.contains("modo-foco")) {
            return false;
        }

        const screenBase = String(
            snapshot?.inspectorBaseScreen ||
            resolveInspectorBaseScreen()
        ).trim();
        if (screenBase !== "portal_dashboard") {
            return false;
        }

        if (String(snapshot?.overlayOwner || "").trim()) {
            return false;
        }

        const laudoId = normalizarLaudoAtualId(
            snapshot?.laudoAtualId ??
            estado.laudoAtualId ??
            obterLaudoAtivoIdSeguro()
        );
        const estadoRelatorio = normalizarEstadoRelatorio(
            snapshot?.estadoRelatorio ??
            estado.estadoRelatorio ??
            obterEstadoRelatorioAtualSeguro()
        );
        const workspaceStage = normalizarWorkspaceStage(
            snapshot?.workspaceStage ??
            estado.workspaceStage
        );

        return !laudoId
            && !estadoRelatorioPossuiContexto(estadoRelatorio)
            && workspaceStage === "assistant";
    }

    function sincronizarVisibilidadeAcoesChatLivre(snapshot = obterSnapshotEstadoInspectorAtual()) {
        const botoes = Array.isArray(el.botoesAbrirChatLivre) ? el.botoesAbrirChatLivre : [];
        let algumDisponivel = false;

        botoes.forEach((botao) => {
            if (!botao) return;
            const disponivel = resolverDisponibilidadeBotaoChatLivre(botao, snapshot);
            botao.hidden = !disponivel;
            botao.disabled = !disponivel;
            botao.setAttribute("aria-hidden", String(!disponivel));
            algumDisponivel = algumDisponivel || disponivel;
        });

        return algumDisponivel;
    }

    function layoutInspectorCompacto() {
        return window.innerWidth <= BREAKPOINT_LAYOUT_INSPETOR_COMPACTO;
    }

    function resolverMatrizVisibilidadeInspector(screen = resolveInspectorScreen(), snapshot = obterSnapshotEstadoInspectorAtual()) {
        const screenBase = screen === "new_inspection"
            ? (snapshot.inspectorBaseScreen || resolveInspectorBaseScreen())
            : (snapshot.inspectorBaseScreen || screen);
        const overlayAtivo = screen === "new_inspection" || snapshot.overlayOwner === "new_inspection";
        const compacto = layoutInspectorCompacto();
        const portalAtivo = screenBase === "portal_dashboard";
        const assistantAtivo = screenBase === "assistant_landing";
        const inspectionAtivo = [
            "inspection_workspace",
            "inspection_conversation",
            "inspection_history",
            "inspection_record",
            "inspection_mesa",
        ].includes(screenBase);
        const workspaceView = resolveWorkspaceView(screen);
        const laudoAtivoId = normalizarLaudoAtualId(
            snapshot?.laudoAtualId
            ?? estado.laudoAtualId
            ?? obterLaudoAtivoIdSeguro()
        );
        const conversaLivreFocada =
            workspaceView === "inspection_conversation" &&
            conversaWorkspaceModoChatAtivo(screen, snapshot);
        const chatLivreDisponivel = entradaChatLivreDisponivel(snapshot);
        const quickDock = !overlayAtivo && compacto && (
            assistantAtivo ||
            (inspectionAtivo && workspaceView !== "inspection_mesa" && !conversaLivreFocada)
        )
            ? "visible"
            : "hidden";
        const contextRail = inspectionAtivo && workspaceView !== "inspection_mesa" && !conversaLivreFocada && !overlayAtivo && !compacto
            ? "visible"
            : "hidden";
        const mesaEntry = inspectionAtivo && workspaceView !== "inspection_mesa" && !conversaLivreFocada && !overlayAtivo
            ? (compacto ? "composer" : "rail")
            : "hidden";
        const finalizeEntry = inspectionAtivo && workspaceView !== "inspection_mesa" && !overlayAtivo && !!laudoAtivoId
            ? "header"
            : "hidden";
        let novaInspecaoEntry = "hidden";
        if (portalAtivo && !overlayAtivo) {
            novaInspecaoEntry = "portal";
        } else if ((assistantAtivo || inspectionAtivo) && !overlayAtivo) {
            novaInspecaoEntry = "header";
        }

        let abrirChatEntry = "hidden";
        if (portalAtivo && !overlayAtivo) {
            abrirChatEntry = "portal";
        } else if (screen === "new_inspection" && chatLivreDisponivel) {
            abrirChatEntry = "modal";
        }

        return {
            screen,
            screenBase,
            workspaceView,
            overlayAtivo,
            compacto,
            portalAtivo,
            assistantAtivo,
            inspectionAtivo,
            quickDock,
            contextRail,
            mesaWidget: inspectionAtivo && !conversaLivreFocada && !overlayAtivo ? "contextual" : "hidden",
            novaInspecaoEntry,
            abrirChatEntry,
            landingNewInspection: assistantAtivo && !overlayAtivo ? "visible" : "hidden",
            workspaceHeaderNewInspection: (assistantAtivo || inspectionAtivo) && !overlayAtivo ? "visible" : "hidden",
            sidebarNewInspection: "hidden",
            headerFinalize: finalizeEntry === "header" ? "visible" : "hidden",
            railFinalize: finalizeEntry === "rail" ? "visible" : "hidden",
            mesaEntry,
            operationalShortcuts: inspectionAtivo && workspaceView !== "inspection_mesa" && !conversaLivreFocada && !overlayAtivo
                ? "inspection"
                : (assistantAtivo && !overlayAtivo ? "assistant" : "hidden"),
        };
    }

    function aplicarMatrizVisibilidadeInspector(screen = resolveInspectorScreen(), snapshot = obterSnapshotEstadoInspectorAtual()) {
        const matriz = resolverMatrizVisibilidadeInspector(screen, snapshot);
        const body = document.body;
        const painel = el.painelChat;
        const mesaEntry = matriz.mesaEntry;
        const finalizeEntry = matriz.headerFinalize === "visible"
            ? "header"
            : (matriz.railFinalize === "visible" ? "rail" : "hidden");

        body.dataset.inspectorCompactLayout = matriz.compacto ? "true" : "false";
        body.dataset.inspectorQuickDock = matriz.quickDock;
        body.dataset.inspectorContextRail = matriz.contextRail;
        body.dataset.inspectorMesaEntry = mesaEntry;
        body.dataset.inspectorMesaWidgetSurface = matriz.mesaWidget;
        body.dataset.inspectorFinalizeEntry = finalizeEntry;
        body.dataset.inspectorNovaInspecaoEntry = matriz.novaInspecaoEntry;
        body.dataset.inspectorAbrirChatEntry = matriz.abrirChatEntry;
        body.dataset.inspectorOperationalShortcuts = matriz.operationalShortcuts;

        if (painel) {
            painel.dataset.inspectorCompactLayout = matriz.compacto ? "true" : "false";
            painel.dataset.inspectorQuickDock = matriz.quickDock;
            painel.dataset.inspectorContextRail = matriz.contextRail;
            painel.dataset.inspectorMesaEntry = mesaEntry;
            painel.dataset.inspectorMesaWidgetSurface = matriz.mesaWidget;
            painel.dataset.inspectorFinalizeEntry = finalizeEntry;
            painel.dataset.inspectorNovaInspecaoEntry = matriz.novaInspecaoEntry;
            painel.dataset.inspectorAbrirChatEntry = matriz.abrirChatEntry;
            painel.dataset.inspectorOperationalShortcuts = matriz.operationalShortcuts;
        }

        if (el.btnSidebarOpenInspecaoModal) {
            const visivel = matriz.sidebarNewInspection === "visible";
            el.btnSidebarOpenInspecaoModal.hidden = !visivel;
            el.btnSidebarOpenInspecaoModal.setAttribute("aria-hidden", String(!visivel));
        }
        if (el.btnWorkspaceOpenInspecaoModal) {
            const visivel = matriz.workspaceHeaderNewInspection === "visible";
            el.btnWorkspaceOpenInspecaoModal.hidden = !visivel;
            el.btnWorkspaceOpenInspecaoModal.setAttribute("aria-hidden", String(!visivel));
        }
        if (el.btnAssistantLandingOpenInspecaoModal) {
            const visivel = matriz.landingNewInspection === "visible";
            el.btnAssistantLandingOpenInspecaoModal.hidden = !visivel;
            el.btnAssistantLandingOpenInspecaoModal.setAttribute("aria-hidden", String(!visivel));
        }
        if (el.btnFinalizarInspecao) {
            const visivel = matriz.headerFinalize === "visible";
            el.btnFinalizarInspecao.hidden = !visivel;
            el.btnFinalizarInspecao.setAttribute("aria-hidden", String(!visivel));
        }
        if (el.btnRailFinalizarInspecao) {
            const visivel = matriz.railFinalize === "visible";
            el.btnRailFinalizarInspecao.hidden = !visivel;
            el.btnRailFinalizarInspecao.setAttribute("aria-hidden", String(!visivel));
        }
        if (el.btnMesaWidgetToggle) {
            const visivel = matriz.mesaEntry === "rail";
            el.btnMesaWidgetToggle.hidden = !visivel;
            el.btnMesaWidgetToggle.setAttribute("aria-hidden", String(!visivel));
        }
        if (el.btnToggleHumano) {
            const visivel = matriz.mesaEntry === "composer";
            el.btnToggleHumano.hidden = !visivel;
            el.btnToggleHumano.setAttribute("aria-hidden", String(!visivel));
        }

        return matriz;
    }

    function modalNovaInspecaoEstaAberta() {
        return Boolean(el.modal && !el.modal.hidden && el.modal.classList.contains("ativo"));
    }

    function resolveInspectorBaseScreen() {
        return resolverInspectorBaseScreenPorSnapshot(obterSnapshotEstadoInspectorAtual());
    }

    function definirRootAtivo(root, ativo) {
        if (!root) return;

        const deveAtivar = !!ativo;
        root.dataset.active = deveAtivar ? "true" : "false";
        root.setAttribute("aria-hidden", String(!deveAtivar));

        if (deveAtivar) {
            root.removeAttribute("hidden");
        } else {
            root.setAttribute("hidden", "");
        }

        try {
            root.inert = !deveAtivar;
        } catch (_) {
            if (deveAtivar) {
                root.removeAttribute("inert");
            } else {
                root.setAttribute("inert", "");
            }
        }
    }

    function resolveInspectorScreen() {
        return obterSnapshotEstadoInspectorAtual().inspectorScreen || resolveInspectorBaseScreen();
    }

    function resolveWorkspaceView(screen = estado.inspectorScreen || resolveInspectorScreen()) {
        const snapshot = obterSnapshotEstadoInspectorAtual();
        const screenBase = screen === "new_inspection"
            ? snapshot.inspectorBaseScreen || resolveInspectorBaseScreen()
            : screen;

        if (screenBase === "assistant_landing") {
            return "assistant_landing";
        }

        if ([
            "inspection_conversation",
            "inspection_history",
            "inspection_record",
            "inspection_mesa",
        ].includes(screenBase)) {
            return screenBase;
        }

        if (screenBase !== "inspection_workspace") {
            return "inspection_history";
        }

        const threadTabAtual = normalizarThreadTab(snapshot.threadTab);
        if (threadTabAtual === "anexos") return "inspection_record";
        if (threadTabAtual === "mesa") return "inspection_mesa";
        if (threadTabAtual === "historico") return "inspection_history";
        return "inspection_conversation";
    }

    function workspaceViewSuportaRail(view = resolveWorkspaceView()) {
        return view === "inspection_history"
            || view === "inspection_record"
            || view === "inspection_conversation";
    }

    function resolveWorkspaceRailVisibility(screen = estado.inspectorScreen || resolveInspectorScreen()) {
        if (screen === "new_inspection") {
            return false;
        }

        const snapshot = obterSnapshotEstadoInspectorAtual();
        if (conversaWorkspaceModoChatAtivo(screen, snapshot)) {
            return false;
        }

        const view = resolveWorkspaceView(screen);
        return workspaceViewSuportaRail(view) && !!estado.workspaceRailExpanded;
    }

    function atualizarBotaoWorkspaceRail({
        chromeTecnicoOperacional = false,
        layoutCompacto = layoutInspectorCompacto(),
        view = resolveWorkspaceView(),
        railVisivel = resolveWorkspaceRailVisibility(),
    } = {}) {
        if (!el.btnWorkspaceToggleRail) return;

        const railDisponivel = chromeTecnicoOperacional && !layoutCompacto && workspaceViewSuportaRail(view);
        const icone = el.btnWorkspaceToggleRail.querySelector(".material-symbols-rounded");
        const rotulo = el.btnWorkspaceToggleRail.querySelector("span:last-child");

        el.btnWorkspaceToggleRail.hidden = !railDisponivel;
        el.btnWorkspaceToggleRail.setAttribute("aria-expanded", railVisivel ? "true" : "false");

        if (icone) {
            icone.textContent = railVisivel ? "right_panel_close" : "right_panel_open";
        }
        if (rotulo) {
            rotulo.textContent = railVisivel ? "Fechar painel" : "Painel";
        }
    }

    function resolveMesaWidgetDisponibilidade(screen = estado.inspectorScreen || resolveInspectorScreen()) {
        if (screen === "new_inspection") {
            return false;
        }

        const snapshot = obterSnapshotEstadoInspectorAtual();
        if (conversaWorkspaceModoChatAtivo(screen, snapshot)) {
            return false;
        }

        const laudoId = normalizarLaudoAtualId(
            snapshot?.laudoAtualId ??
            estado.laudoAtualId ??
            obterLaudoAtivoIdSeguro()
        );
        if (!laudoId) {
            return false;
        }

        const view = resolveWorkspaceView(screen);
        return [
            "inspection_history",
            "inspection_record",
            "inspection_conversation",
            "inspection_mesa",
        ].includes(view);
    }

    function contextoTecnicoPrecisaRefresh(snapshot = obterSnapshotEstadoInspectorAtual()) {
        const screenBase = snapshot?.inspectorBaseScreen || resolveInspectorBaseScreen();
        return screenBase === "inspection_workspace";
    }

    function contextoPrecisaSSE(snapshot = obterSnapshotEstadoInspectorAtual()) {
        const screenBase = snapshot?.inspectorBaseScreen || resolveInspectorBaseScreen();
        const laudoId = normalizarLaudoAtualId(
            snapshot?.laudoAtualId
            ?? estado.laudoAtualId
            ?? obterLaudoAtivoIdSeguro()
        );

        if (!laudoId) {
            return false;
        }

        return screenBase === "inspection_workspace";
    }

    function sincronizarSSEPorContexto(opcoes = {}) {
        if (!contextoPrecisaSSE()) {
            fecharSSE();
            limparTimerReconexaoSSE();
            PERF?.count?.("inspetor.sse.suprimido_orquestrador", 1, {
                category: "request_churn",
                detail: {
                    laudoId: obterLaudoAtivoIdSeguro(),
                    screen: resolveInspectorBaseScreen(),
                },
            });
            return false;
        }

        inicializarNotificacoesSSE(opcoes);
        return true;
    }

    function resolverEstadoPadraoAcordeoesRail(view = resolveWorkspaceView()) {
        if (view === "inspection_history") {
            return {
                history: true,
                progress: false,
                context: false,
                pendencias: false,
                mesa: false,
                pinned: false,
            };
        }

        if (view === "inspection_record") {
            return {
                progress: false,
                context: false,
                pendencias: false,
                mesa: false,
                pinned: false,
            };
        }

        if (view === "inspection_mesa") {
            return {
                progress: false,
                context: false,
                pendencias: false,
                mesa: true,
                pinned: false,
            };
        }

        return {
            history: false,
            progress: false,
            context: false,
            pendencias: false,
            mesa: false,
            pinned: false,
        };
    }

    function sincronizarAcordeoesRailWorkspace(view = resolveWorkspaceView()) {
        const estadoPadrao = resolverEstadoPadraoAcordeoesRail(view);
        const mudouView = estado.workspaceRailViewKey !== view;
        const estadoAtual = (
            estado.workspaceRailAccordionState &&
            typeof estado.workspaceRailAccordionState === "object"
        ) ? estado.workspaceRailAccordionState : Object.create(null);
        const botoes = Array.isArray(el.workspaceRailToggleButtons) ? el.workspaceRailToggleButtons : [];

        if (mudouView) {
            estado.workspaceRailAccordionState = { ...estadoPadrao };
            estado.workspaceRailViewKey = view;
        } else {
            estado.workspaceRailAccordionState = {
                ...estadoPadrao,
                ...estadoAtual,
            };
        }

        botoes.forEach((botao) => {
            const chave = String(botao?.dataset?.railToggle || "").trim();
            if (!chave) return;

            const aberto = !!estado.workspaceRailAccordionState?.[chave];
            aplicarEstadoAcordeaoRailWorkspace(botao, aberto, { persist: false });
        });
    }

    function aplicarEstadoAcordeaoRailWorkspace(botao, aberto, { persist = true } = {}) {
        if (!botao) return;

        const chave = String(botao.dataset.railToggle || "").trim();
        if (!chave) return;

        const corpo = document.querySelector(`[data-rail-body="${CSS.escape(chave)}"]`);
        const card = botao.closest(".technical-record-card");
        const expandido = aberto ? "true" : "false";

        botao.setAttribute("aria-expanded", expandido);
        botao.dataset.expanded = expandido;

        if (card) {
            card.dataset.collapsed = aberto ? "false" : "true";
        }
        if (corpo) {
            corpo.hidden = !aberto;
            corpo.dataset.expanded = expandido;
        }
        if (persist) {
            estado.workspaceRailAccordionState = {
                ...(estado.workspaceRailAccordionState && typeof estado.workspaceRailAccordionState === "object"
                    ? estado.workspaceRailAccordionState
                    : {}),
                [chave]: !!aberto,
            };
        }
    }

    function sincronizarMesaStageWorkspace(view = resolveWorkspaceView(), mesaWidgetPermitido = resolveMesaWidgetDisponibilidade()) {
        if (!el.painelMesaWidget) return;

        const hostMesaWorkspace = el.workspaceMesaWidgetHost || el.workspaceMesaStage;

        const embutirNoWorkspace =
            mesaWidgetPermitido &&
            view === "inspection_mesa" &&
            hostMesaWorkspace;
        const estavaEmbutido = el.painelMesaWidget.dataset.workspaceEmbedded === "true";

        if (embutirNoWorkspace) {
            if (el.painelMesaWidget.parentElement !== hostMesaWorkspace) {
                hostMesaWorkspace.appendChild(el.painelMesaWidget);
            }

            el.painelMesaWidget.dataset.workspaceEmbedded = "true";
            el.painelMesaWidget.hidden = false;
            el.painelMesaWidget.classList.remove("fechando");
            el.painelMesaWidget.classList.add("aberto", "painel-mesa-widget--workspace");
            estado.mesaWidgetAberto = true;
            if (el.btnMesaWidgetToggle) {
                el.btnMesaWidgetToggle.setAttribute("aria-expanded", "true");
            }
            atualizarEstadoVisualBotaoMesaWidget();

            if (!estavaEmbutido) {
                carregarMensagensMesaWidget({ silencioso: true }).catch(() => {});
            }

            return;
        }

        if (mesaWidgetDockOriginal && el.painelMesaWidget.parentElement !== mesaWidgetDockOriginal) {
            mesaWidgetDockOriginal.appendChild(el.painelMesaWidget);
        }

        el.painelMesaWidget.dataset.workspaceEmbedded = "false";
        el.painelMesaWidget.classList.remove("painel-mesa-widget--workspace");

        if (estavaEmbutido) {
            estado.mesaWidgetAberto = false;
            el.painelMesaWidget.hidden = true;
            el.painelMesaWidget.classList.remove("aberto", "fechando");
            if (el.btnMesaWidgetToggle) {
                el.btnMesaWidgetToggle.setAttribute("aria-expanded", "false");
            }
            atualizarEstadoVisualBotaoMesaWidget();
        }
    }

    function sincronizarWorkspaceRail(screen = estado.inspectorScreen || resolveInspectorScreen()) {
        const view = resolveWorkspaceView(screen);
        const railVisivel = resolveWorkspaceRailVisibility(screen);
        const layout = railVisivel ? "thread-with-rail" : "thread-only";

        document.body.dataset.workspaceView = view;
        document.body.dataset.workspaceRailVisible = railVisivel ? "true" : "false";

        if (el.painelChat) {
            el.painelChat.dataset.workspaceView = view;
            el.painelChat.dataset.workspaceRailVisible = railVisivel ? "true" : "false";
        }

        if (el.workspaceScreenRoot) {
            el.workspaceScreenRoot.dataset.workspaceView = view;
            el.workspaceScreenRoot.dataset.workspaceLayout = layout;
            el.workspaceScreenRoot.dataset.workspaceRailVisible = railVisivel ? "true" : "false";
        }

        if (el.chatDashboardRail) {
            el.chatDashboardRail.hidden = !railVisivel;
            el.chatDashboardRail.dataset.workspaceRailVisible = railVisivel ? "true" : "false";
            el.chatDashboardRail.setAttribute("aria-hidden", String(!railVisivel));
        }

        sincronizarAcordeoesRailWorkspace(view);

        return railVisivel;
    }

    function sincronizarWidgetsGlobaisWorkspace(screen = estado.inspectorScreen || resolveInspectorScreen()) {
        const mesaWidgetPermitido = resolveMesaWidgetDisponibilidade(screen);
        const view = resolveWorkspaceView(screen);
        const mesaIncorporada = view === "inspection_mesa";

        document.body.dataset.mesaWidgetVisible = mesaWidgetPermitido ? "true" : "false";

        if (el.painelChat) {
            el.painelChat.dataset.mesaWidgetVisible = mesaWidgetPermitido ? "true" : "false";
        }

        if (el.mesaWidgetScreenRoot) {
            el.mesaWidgetScreenRoot.dataset.widgetAllowed = mesaWidgetPermitido ? "true" : "false";
            definirRootAtivo(el.mesaWidgetScreenRoot, mesaWidgetPermitido && !mesaIncorporada);
        }

        if (el.painelMesaWidget) {
            el.painelMesaWidget.dataset.widgetAllowed = mesaWidgetPermitido ? "true" : "false";
            const ariaHidden = !mesaWidgetPermitido || el.painelMesaWidget.hidden;
            el.painelMesaWidget.setAttribute("aria-hidden", String(ariaHidden));
        }

        sincronizarMesaStageWorkspace(view, mesaWidgetPermitido);

        if (!mesaWidgetPermitido) {
            if (estado.mesaWidgetAberto || !el.painelMesaWidget?.hidden) {
                fecharMesaWidget();
            } else if (el.btnMesaWidgetToggle) {
                el.btnMesaWidgetToggle.setAttribute("aria-expanded", "false");
            }
        }

        sincronizarClasseBodyMesaWidget();
        return mesaWidgetPermitido;
    }

    function sincronizarWorkspaceViews(screen = estado.inspectorScreen || resolveInspectorScreen()) {
        const view = resolveWorkspaceView(screen);
        const chromeTecnicoVisivel =
            view !== "assistant_landing" &&
            !conversaWorkspaceModoChatAtivo(screen, obterSnapshotEstadoInspectorAtual());

        definirRootAtivo(el.workspaceAssistantViewRoot, view === "assistant_landing");
        definirRootAtivo(el.workspaceHistoryViewRoot, view === "inspection_history");
        definirRootAtivo(el.workspaceRecordViewRoot, view === "inspection_record");
        definirRootAtivo(el.workspaceConversationViewRoot, view === "inspection_conversation");
        definirRootAtivo(el.workspaceMesaViewRoot, view === "inspection_mesa");

        if (!el.threadNav) {
            el.threadNav = document.querySelector(".thread-nav");
        }

        if (el.threadNav) {
            el.threadNav.hidden = !chromeTecnicoVisivel;
            el.threadNav.setAttribute("aria-hidden", String(!chromeTecnicoVisivel));
        }

        if (el.workspaceHistoryViewRoot) {
            el.workspaceHistoryViewRoot.dataset.historyFocus = view === "inspection_history" ? "reading" : "idle";
        }

        if (el.workspaceHistoryRoot) {
            el.workspaceHistoryRoot.dataset.historyFocus = view === "inspection_history" ? "reading" : "idle";
        }

        if (el.workspaceAnexosPanel) {
            const anexosVisiveis = view === "inspection_record";
            el.workspaceAnexosPanel.hidden = !anexosVisiveis;
            el.workspaceAnexosPanel.setAttribute("aria-hidden", String(!anexosVisiveis));
        }

        atualizarEmptyStateHonestoConversa();

        return view;
    }

    function sincronizarInspectorScreen() {
        if (sincronizandoInspectorScreen) {
            sincronizacaoInspectorScreenPendente = true;
            return estado.inspectorScreen || resolveInspectorBaseScreen();
        }

        sincronizandoInspectorScreen = true;

        try {
            const snapshot = sincronizarEstadoInspector({}, {
                persistirStorage: false,
                syncScreen: false,
            });
            const screen = snapshot.inspectorScreen;
            const baseScreen = snapshot.inspectorBaseScreen;
            const workspaceAtivo = baseScreen !== "portal_dashboard";
            const overlayOwner = snapshot.overlayOwner;

            definirRootAtivo(el.portalScreenRoot, baseScreen === "portal_dashboard");
            definirRootAtivo(el.workspaceScreenRoot, workspaceAtivo);
            sincronizarWorkspaceViews(screen);
            const railVisible = sincronizarWorkspaceRail(screen);
            const mesaWidgetVisible = sincronizarWidgetsGlobaisWorkspace(screen);
            const chatLivreDisponivel = sincronizarVisibilidadeAcoesChatLivre(snapshot);
            const matrizVisibilidade = aplicarMatrizVisibilidadeInspector(screen, snapshot);

            document.dispatchEvent(new CustomEvent("tariel:screen-synced", {
                detail: {
                    screen,
                    baseScreen,
                    overlayOwner,
                    workspaceAtivo,
                    homeActionVisible: !!snapshot.homeActionVisible,
                    chatLivreDisponivel,
                    compactLayout: matrizVisibilidade.compacto,
                    quickDock: matrizVisibilidade.quickDock,
                    contextRail: matrizVisibilidade.contextRail,
                    mesaEntry: matrizVisibilidade.mesaEntry,
                    finalizeEntry: matrizVisibilidade.headerFinalize === "visible" ? "header" : (
                        matrizVisibilidade.railFinalize === "visible" ? "rail" : "hidden"
                    ),
                    novaInspecaoEntry: matrizVisibilidade.novaInspecaoEntry,
                    abrirChatEntry: matrizVisibilidade.abrirChatEntry,
                    railVisible,
                    mesaWidgetVisible,
                },
                bubbles: true,
            }));

            return screen;
        } finally {
            sincronizandoInspectorScreen = false;

            if (sincronizacaoInspectorScreenPendente) {
                sincronizacaoInspectorScreenPendente = false;
                window.requestAnimationFrame(() => {
                    sincronizarInspectorScreen();
                });
            }
        }
    }

    async function navegarParaHome(destino = "/app/?home=1", { preservarContexto = true } = {}) {
        const homeDestino = String(destino || "/app/?home=1").trim() || "/app/?home=1";
        let desativou = true;

        if (!preservarContexto) {
            desativou = await desativarContextoAtivoParaHome();
        }

        if (!desativou && !preservarContexto) {
            mostrarToast(
                "Não foi possível limpar o contexto ativo. Recarregando a central.",
                "aviso",
                2400
            );
        }

        definirRetomadaHomePendente(null);
        limparEstadoHomeNoCliente();
        if (preservarContexto) {
            marcarForcaTelaInicial();
        }
        window.location.assign(homeDestino);
    }

    function processarAcaoHome(detail = {}) {
        const destino = String(detail?.destino || "/app/?home=1").trim() || "/app/?home=1";
        navegarParaHome(destino, {
            preservarContexto: detail?.preservarContexto !== false,
        });
    }

    function resumirTexto(texto, limite = 140) {
        const base = String(texto || "").replace(/\s+/g, " ").trim();
        if (!base) return "Mensagem sem conteúdo";
        return base.length > limite ? `${base.slice(0, limite)}...` : base;
    }

    function normalizarConexaoMesaWidget(valor) {
        const status = String(valor || "").trim().toLowerCase();
        if (status === "reconectando") return "reconectando";
        if (status === "offline") return "offline";
        return "conectado";
    }

    function pluralizarMesa(total, singular, plural) {
        return Number(total || 0) === 1 ? singular : (plural || `${singular}s`);
    }

    function atualizarStatusMesa(status = "pronta", detalhe = "") {
        const statusNormalizado = normalizarStatusMesa(status);
        estado.statusMesa = statusNormalizado;
        estado.statusMesaDescricao = String(detalhe || "").trim();
    }

    function atualizarStatusMesaPorComposer(modoMarcador) {
        if (modoMarcador === "insp") {
            if (estado.statusMesa !== "aguardando" && estado.statusMesa !== "respondeu") {
                atualizarStatusMesa("canal_ativo");
            }
            return;
        }

        if (estado.statusMesa === "canal_ativo") {
        }
    }

    function obterTipoTemplateDoPayload(dados = {}) {
        return normalizarTipoTemplate(
            dados?.tipoTemplate ||
            dados?.tipo_template ||
            dados?.template ||
            estado.tipoTemplateAtivo
        );
    }

    function inserirTextoNoComposer(texto) {
        const textoLimpo = String(texto || "").trim();

        if (!el.campoMensagem || !textoLimpo) {
            return false;
        }

        const valorAtual = String(el.campoMensagem.value || "").trim();
        el.campoMensagem.value = valorAtual ? `${valorAtual}\n${textoLimpo}` : textoLimpo;

        el.campoMensagem.dispatchEvent(new Event("input", { bubbles: true }));
        el.campoMensagem.dispatchEvent(new Event("change", { bubbles: true }));
        try {
            el.campoMensagem.focus({ preventScroll: true });
        } catch (_) {
            el.campoMensagem.focus();
        }

        if (typeof el.campoMensagem.setSelectionRange === "function") {
            const fim = el.campoMensagem.value.length;
            el.campoMensagem.setSelectionRange(fim, fim);
        }

        return true;
    }

    function aplicarPrePromptDaAcaoRapida(botao) {
        const texto = String(botao?.dataset?.preprompt || "").trim();
        return inserirTextoNoComposer(texto);
    }

    function obterLaudoAtivoIdSeguro() {
        return normalizarLaudoAtualId(obterSnapshotEstadoInspectorAtual().laudoAtualId);
    }

    function obterHeadersComCSRF(extra = {}) {
        const base = { Accept: "application/json", ...extra };

        if (window.TarielCore?.comCabecalhoCSRF) {
            return window.TarielCore.comCabecalhoCSRF(base);
        }

        const tokenMeta = document.querySelector('meta[name="csrf-token"]')?.content?.trim() || "";
        return tokenMeta ? { ...base, "X-CSRF-Token": tokenMeta } : base;
    }

    async function extrairMensagemErroHTTP(resposta, fallback = "") {
        if (!resposta) return String(fallback || "").trim();

        try {
            const tipoConteudo = String(resposta.headers?.get("content-type") || "").toLowerCase();

            if (tipoConteudo.includes("application/json")) {
                const payload = await resposta.json();
                const detalhe =
                    payload?.detail ??
                    payload?.erro ??
                    payload?.mensagem ??
                    payload?.message ??
                    "";

                if (typeof detalhe === "string" && detalhe.trim()) {
                    return detalhe.trim();
                }

                if (Array.isArray(detalhe) && detalhe.length > 0) {
                    return String(
                        detalhe
                            .map((item) => String(item?.msg || item || "").trim())
                            .filter(Boolean)
                            .join(" | ")
                    ).trim();
                }
            } else {
                const bruto = String(await resposta.text()).trim();
                if (bruto) {
                    return bruto.slice(0, 240);
                }
            }
        } catch (_) {
            // Fallback silencioso.
        }

        return String(fallback || `Falha HTTP ${resposta.status || ""}`).trim();
    }

    // =========================================================
    // MÓDULOS DO PORTAL DO INSPETOR
    // =========================================================

    const REGISTROS_MODULOS_INSPETOR = Object.freeze([
        "registerBootstrap",
        "registerEntryMode",
        "registerModals",
        "registerObservers",
        "registerPendencias",
        "registerMesaWidget",
        "registerNotifications",
        "registerSystemEvents",
        "registerUiBindings",
        "registerGovernance",
        "registerWorkspaceOverview",
        "registerWorkspaceHistory",
        "registerWorkspaceContext",
        "registerWorkspaceNavigation",
        "registerWorkspaceReportFlow",
        "registerWorkspaceDerivatives",
    ]);

    const noop = () => {};
    const noopAsync = async () => null;
    const noopFalse = () => false;
    const noopNull = () => null;

    function criarResumoMesaPadraoInspetor() {
        return {
            status: "pronta",
            titulo: "Mesa disponível",
            descricao: "",
            chipStatus: "",
            chipPendencias: "",
            chipNaoLidas: "",
        };
    }

    function criarContextoVisualPadraoInspetor() {
        return {
            title: "Assistente Tariel IA",
            subtitle: "Conversa inicial • nenhum laudo ativo",
            statusBadge: "CHAT LIVRE",
        };
    }

    function criarSharedRuntimeInspetor() {
        return {
            ROTA_SSE_NOTIFICACOES,
            TEMPO_BANNER_MS,
            TEMPO_RECONEXAO_SSE_MS,
            NOMES_TEMPLATES,
            COMANDOS_SLASH,
            CONFIG_STATUS_MESA,
            CONFIG_CONEXAO_MESA_WIDGET,
            LIMITE_RECONEXAO_SSE_OFFLINE,
            MAX_BYTES_ANEXO_MESA,
            MIME_ANEXOS_MESA_PERMITIDOS,
            CHAVE_FORCE_HOME_LANDING,
            CHAVE_RETOMADA_HOME_PENDENTE,
            CHAVE_CONTEXTO_VISUAL_LAUDOS,
            LIMITE_CONTEXTO_VISUAL_LAUDOS_STORAGE,
            CONTEXTO_WORKSPACE_ASSISTENTE,
            emitirEventoTariel,
            mostrarToast,
            ouvirEventoTariel,
            escaparHtml,
            normalizarTipoTemplate,
            normalizarContextoVisualSeguro,
            normalizarModoInspecaoUI,
            normalizarFiltroPendencias,
            normalizarLaudoAtualId,
            normalizarEstadoRelatorio,
            normalizarThreadTab,
            normalizarWorkspaceStage,
            normalizarEntryModePreference,
            normalizarEntryModeEffective,
            normalizarEntryModeEffectiveOpcional,
            normalizarEntryModeReason,
            normalizarCaseLifecycleStatusSeguro,
            normalizarEmissaoOficialSeguro,
            normalizarPublicVerificationSeguro,
            estadoRelatorioPossuiContexto,
            obterLaudoAtivoIdSeguro,
            obterPayloadStatusRelatorioWorkspaceAtual,
            obterHeadersComCSRF,
            extrairMensagemErroHTTP,
            obterElementosFocaveis,
            formatarTamanhoBytes,
            normalizarAnexoMesa,
            renderizarLinksAnexosMesa,
            pluralizarMesa,
            resumirTexto,
            normalizarConexaoMesaWidget,
            normalizarStatusMesa,
            pluralizarWorkspace,
            obterLaudoAtivo,
            obterItensCanonicosHistoricoWorkspace: () => {
                const viaApi = window.TarielAPI?.obterHistoricoLaudoAtual?.();
                return Array.isArray(viaApi) ? viaApi.map((item) => ({ ...item })) : [];
            },
            obterTokenCsrf,
            emitirSincronizacaoLaudo,
            avisarMesaExigeInspecao,
            ehAbortError,
            limparTimerBanner,
            limparTimerReconexaoSSE,
            limparTimerFecharMesaWidget,
            cancelarCarregamentoPendenciasMesa,
            cancelarCarregamentoMensagensMesaWidget,
            fecharSSE,
            workspaceHasSurfaceAction,
            workspaceTemContratoLifecycle,
        };
    }

    function criarAcoesPadraoRuntimeInspetor() {
        return {
            aplicarContextoVisualWorkspace: noop,
            abrirMesaWidget: noop,
            abrirModalGateQualidade: noop,
            abrirModalNovaInspecao: noop,
            abrirLaudoPeloHome: noopAsync,
            abrirNovaInspecaoComScreenSync: noop,
            atualizarBotoesFiltroPendencias: noop,
            atualizarConexaoMesaWidget: noop,
            atualizarEstadoAcaoModalNovaInspecao: noop,
            atualizarEstadoVisualBotaoMesaWidget: noop,
            atualizarBadgeMesaWidget: noop,
            atualizarChatAoVivoComMesa: noop,
            atualizarContextoWorkspaceAtivo: noop,
            atualizarControlesWorkspaceStage: noop,
            atualizarCopyWorkspaceStage: noop,
            atualizarEmptyStateHonestoConversa: noop,
            atualizarPendenciaIndividual: noop,
            atualizarPainelWorkspaceDerivado: noop,
            atualizarPreviewNomeInspecao: noop,
            atualizarStatusChatWorkspace: noop,
            atualizarHistoricoHomeExpandido: noop,
            atualizarNomeTemplateAtivo: noop,
            carregarMensagensMesaWidget: noopAsync,
            carregarPendenciasMesa: noopAsync,
            carregarContextoFixadoWorkspace: noop,
            copiarResumoContextoWorkspace: noopAsync,
            conversaWorkspaceModoChatAtivo: noopFalse,
            criarContextoVisualDoModal: criarContextoVisualPadraoInspetor,
            criarContextoVisualPadrao: criarContextoVisualPadraoInspetor,
            continuarComOverrideHumanoGateQualidade: noopAsync,
            definirModoInspecaoUI: noop,
            definirBotaoFinalizarCarregando: noop,
            definirBotaoIniciarCarregando: noop,
            definirReferenciaMesaWidget: noop,
            definirWorkspaceStage: noop,
            detailPossuiContextoVisual: noopFalse,
            enriquecerPayloadLaudoComContextoVisual: (payload) => payload,
            enviarMensagemMesaWidget: noopAsync,
            exportarPendenciasPdf: noopAsync,
            extrairContextoVisualWorkspace: criarContextoVisualPadraoInspetor,
            exibirInterfaceInspecaoAtiva: noop,
            exibirLandingAssistenteIA: noop,
            fecharBannerEngenharia: noop,
            fecharMesaWidget: noop,
            fecharModalGateQualidade: noop,
            fecharModalNovaInspecao: noop,
            fecharNovaInspecaoComScreenSync: () => true,
            fecharSlashCommandPalette: noop,
            fecharSelectTemplateCustom: noop,
            filtrarTimelineWorkspace: noop,
            bindEventosNovaInspecao: noop,
            inicializarNotificacoesSSE: noop,
            inicializarSelectTemplateCustom: noop,
            iniciarInspecao: noopAsync,
            inserirComandoPendenciasNoChat: noop,
            irParaMensagemPrincipal: noopAsync,
            fixarContextoWorkspace: noop,
            limparAnexoMesaWidget: noop,
            limparContextoFixadoWorkspace: noop,
            limparForcaTelaInicial: noop,
            limparFluxoNovoChatFocado: noop,
            limparPainelPendencias: noop,
            limparReferenciaMesaWidget: noop,
            marcarPendenciasComoLidas: noopAsync,
            modalNovaInspecaoEstaAberta: noopFalse,
            modalNovaInspecaoEstaValida: noopFalse,
            montarResumoContextoModal: () => "",
            montarResumoContextoIAWorkspace: () => "",
            coletarDadosFormularioNovaInspecao: () => ({}),
            copiarTextoWorkspace: noopAsync,
            construirMetaVerificacaoPublicaWorkspace: () => "",
            construirResumoEmissaoOficialWorkspace: () => ({
                title: "Aguardando governança documental",
                meta: "A etapa oficial de emissão ainda não começou.",
                chip: "PENDENTE",
                tone: "neutral",
            }),
            construirResumoGovernancaHistoricoWorkspace: () => ({
                visible: false,
                title: "Reemissão recomendada",
                detail: "PDF emitido divergente detectado no caso atual.",
                actionLabel: "Abrir reemissão na Mesa",
            }),
            lifecyclePermiteVerificacaoPublicaWorkspace: noopFalse,
            mostrarBannerEngenharia: noop,
            normalizarFiltroChat: (valor) => String(valor || "").trim().toLowerCase(),
            normalizarFiltroTipoHistorico: (valor) => String(valor || "").trim().toLowerCase(),
            obterModoEntradaSelecionadoModal: () => "auto_recommended",
            obterContextoVisualAssistente: criarContextoVisualPadraoInspetor,
            obterDetalheLinhaWorkspace: () => ({
                mensagemId: null,
                autor: "Registro",
                papel: "inspetor",
                tempo: "",
                texto: "",
            }),
            obterMensagemMesaPorId: noopNull,
            obterItensCanonicosHistoricoWorkspace: () => [],
            obterPapelLinhaWorkspace: () => "inspetor",
            obterResumoOperacionalMesa: criarResumoMesaPadraoInspetor,
            obterRotuloAcaoFinalizacaoWorkspace: () => "Enviar para Mesa",
            renderizarResumoOperacionalMesa: noop,
            renderizarGovernancaEntradaInspetor: noop,
            renderizarGovernancaHistoricoWorkspace: noop,
            renderizarContextoIAWorkspace: noop,
            renderizarMesaCardWorkspace: noop,
            renderizarResumoExecutivoWorkspace: noop,
            renderizarResumoNavegacaoWorkspace: noop,
            selecionarModoEntradaModal: () => "auto_recommended",
            selecionarAnexoMesaWidget: noop,
            selectTemplateCustomEstaAberto: noopFalse,
            sincronizarClasseBodyMesaWidget: noop,
            toggleEdicaoNomeInspecao: noop,
            togglePainelPendencias: noop,
            toggleMesaWidget: noop,
            tratarTrapFocoModal: noop,
            tratarTrapFocoModalGate: noop,
            atualizarResumoModoEntradaModal: noop,
            bootInspector: noopAsync,
            inicializarObservadorSidebarHistorico: noop,
            inicializarObservadorWorkspace: noop,
            limparObserversInspector: noop,
            bindSystemEvents: noop,
            bindUiBindings: noop,
            contarEvidenciasWorkspace: () => 0,
            extrairMetaLinhaWorkspace: () => ({ autor: "", tempo: "", resumo: "" }),
            renderizarAnexosWorkspace: noop,
            renderizarAtividadeWorkspace: noop,
            renderizarWorkspaceOfficialIssue: noop,
            renderizarWorkspacePublicVerification: noop,
            renderizarProgressoWorkspace: noop,
            resolverContextoVisualWorkspace: criarContextoVisualPadraoInspetor,
            resetarFiltrosHistoricoWorkspace: noop,
            restaurarTelaSemRelatorio: noop,
            removerContextoFixadoWorkspace: noop,
            resetarInterfaceInspecao: noop,
            rolarParaHistoricoHome: noop,
            sincronizarRotuloAcaoFinalizacaoWorkspace: noop,
            workspacePermiteFinalizacao: noopFalse,
        };
    }

    function criarRuntimeInspetor() {
        return {
            state: estado,
            elements: el,
            shared: criarSharedRuntimeInspetor(),
            actions: criarAcoesPadraoRuntimeInspetor(),
        };
    }

    function registrarModulosInspetor(ctx) {
        const modulosInspetor = window.TarielInspetorModules || {};

        REGISTROS_MODULOS_INSPETOR.forEach((nomeRegistro) => {
            const registrar = modulosInspetor[nomeRegistro];
            if (typeof registrar === "function") {
                try {
                    registrar(ctx);
                } catch (erro) {
                    logOnceRuntime(`inspetor-modulo-falha:${nomeRegistro}`, "warn", `Falha ao registrar módulo do inspetor: ${nomeRegistro}`, erro);
                }
                return;
            }

            debugRuntime(`Módulo do inspetor não carregado: ${nomeRegistro}`);
        });
    }

    const ctx = criarRuntimeInspetor();
    window.TarielInspetorRuntime = ctx;
    registrarModulosInspetor(ctx);

    const {
        aplicarContextoVisualWorkspace,
        abrirMesaWidget,
        abrirModalGateQualidade,
        abrirModalNovaInspecao,
        atualizarBotoesFiltroPendencias,
        atualizarConexaoMesaWidget,
        atualizarEstadoAcaoModalNovaInspecao,
        atualizarEstadoVisualBotaoMesaWidget,
        atualizarBadgeMesaWidget,
        atualizarChatAoVivoComMesa,
        atualizarEmptyStateHonestoConversa,
        atualizarPainelWorkspaceDerivado,
        atualizarPendenciaIndividual,
        atualizarPreviewNomeInspecao,
        atualizarStatusChatWorkspace,
        atualizarContextoWorkspaceAtivo,
        atualizarHistoricoHomeExpandido,
        carregarMensagensMesaWidget,
        carregarPendenciasMesa,
        carregarContextoFixadoWorkspace,
        contarEvidenciasWorkspace,
        copiarResumoContextoWorkspace,
        criarContextoVisualDoModal,
        criarContextoVisualPadrao,
        construirMetaVerificacaoPublicaWorkspace,
        construirResumoEmissaoOficialWorkspace,
        construirResumoGovernancaHistoricoWorkspace,
        continuarComOverrideHumanoGateQualidade,
        extrairMetaLinhaWorkspace,
        definirReferenciaMesaWidget,
        enviarMensagemMesaWidget,
        exportarPendenciasPdf,
        extrairContextoVisualWorkspace,
        fecharBannerEngenharia,
        fecharMesaWidget,
        fecharModalGateQualidade,
        fecharModalNovaInspecao,
        exibirInterfaceInspecaoAtiva,
        exibirLandingAssistenteIA,
        fecharSelectTemplateCustom,
        inicializarNotificacoesSSE,
        inicializarSelectTemplateCustom,
        inserirComandoPendenciasNoChat,
        irParaMensagemPrincipal,
        lifecyclePermiteVerificacaoPublicaWorkspace,
        fixarContextoWorkspace,
        limparAnexoMesaWidget,
        limparContextoFixadoWorkspace,
        limparPainelPendencias,
        limparReferenciaMesaWidget,
        marcarPendenciasComoLidas,
        modalNovaInspecaoEstaValida,
        montarResumoContextoModal,
        montarResumoContextoIAWorkspace,
        coletarDadosFormularioNovaInspecao,
        copiarTextoWorkspace,
        mostrarBannerEngenharia,
        normalizarFiltroChat,
        normalizarFiltroTipoHistorico,
        obterModoEntradaSelecionadoModal,
        obterDetalheLinhaWorkspace,
        obterMensagemMesaPorId,
        obterItensCanonicosHistoricoWorkspace,
        obterPapelLinhaWorkspace,
        obterRotuloAcaoFinalizacaoWorkspace,
        obterResumoOperacionalMesa,
        renderizarAnexosWorkspace,
        renderizarAtividadeWorkspace,
        renderizarContextoIAWorkspace,
        renderizarGovernancaEntradaInspetor,
        renderizarGovernancaHistoricoWorkspace,
        renderizarMesaCardWorkspace,
        renderizarProgressoWorkspace,
        renderizarResumoExecutivoWorkspace,
        renderizarResumoNavegacaoWorkspace,
        renderizarResumoOperacionalMesa,
        renderizarWorkspaceOfficialIssue,
        renderizarWorkspacePublicVerification,
        restaurarTelaSemRelatorio,
        resetarFiltrosHistoricoWorkspace,
        resetarInterfaceInspecao,
        removerContextoFixadoWorkspace,
        resolverContextoVisualWorkspace,
        rolarParaHistoricoHome,
        selecionarModoEntradaModal,
        selecionarAnexoMesaWidget,
        selectTemplateCustomEstaAberto,
        sincronizarRotuloAcaoFinalizacaoWorkspace,
        sincronizarResumoHistoricoWorkspace,
        sincronizarResumoPendenciasWorkspace,
        sincronizarClasseBodyMesaWidget,
        toggleEdicaoNomeInspecao,
        togglePainelPendencias,
        toggleMesaWidget,
        tratarTrapFocoModal,
        tratarTrapFocoModalGate,
        definirModoInspecaoUI,
        definirWorkspaceStage,
        atualizarResumoModoEntradaModal,
        workspacePermiteFinalizacao,
    } = ctx.actions;

    function atualizarNomeTemplateAtivo(tipo) {
        const tipoNormalizado = normalizarTipoTemplate(tipo);

        estado.tipoTemplateAtivo = tipoNormalizado;
        window.tipoTemplateAtivo = tipoNormalizado;

        atualizarContextoWorkspaceAtivo();
    }

    function abrirNovaInspecaoComScreenSync(config = {}) {
        abrirModalNovaInspecao(config);
        sincronizarInspectorScreen();
    }

    function fecharNovaInspecaoComScreenSync(opcoes = {}) {
        const resultado = fecharModalNovaInspecao(opcoes);
        sincronizarInspectorScreen();
        return resultado;
    }

    function atualizarCopyWorkspaceStage(stage = "inspection") {
        const copyInspecao = modoEntradaEvidenceFirstAtivo()
            ? {
                ...COPY_WORKSPACE_STAGE.inspection,
                headline: "Registro por evidências",
                description:
                    "Priorize anexos, fotos e provas do caso. Use o chat para contextualizar e fechar a narrativa técnica.",
                placeholder: "Descreva a evidência, o item verificado ou o anexo enviado",
            }
            : COPY_WORKSPACE_STAGE.inspection;
        const copy = stage === "assistant"
            ? COPY_WORKSPACE_STAGE.assistant
            : (
                conversaWorkspaceModoChatAtivo()
                    ? COPY_WORKSPACE_STAGE.focusedConversation
                    : copyInspecao
            );

        if (el.workspaceEyebrow) {
            el.workspaceEyebrow.textContent = copy.eyebrow;
        }
        if (el.workspaceHeadline) {
            el.workspaceHeadline.textContent = copy.headline;
        }
        if (el.workspaceDescription) {
            el.workspaceDescription.textContent = copy.description;
        }
        if (el.campoMensagem) {
            el.campoMensagem.placeholder = copy.placeholder;
        }
        if (stage === "assistant") {
            if (el.rodapeContextoTitulo) {
                el.rodapeContextoTitulo.textContent = copy.contextTitle;
            }
            if (el.rodapeContextoStatus) {
                el.rodapeContextoStatus.textContent = copy.contextStatus;
            }
        }
        atualizarWorkspaceEntryModeNote();
    }

    function atualizarControlesWorkspaceStage() {
        const screenBase = resolveInspectorBaseScreen();
        const viewAtual = resolveWorkspaceView(screenBase);
        const workspaceAtivo = screenBase !== "portal_dashboard";
        const assistantAtivo = workspaceAtivo && screenBase === "assistant_landing";
        const inspectionAtivo = workspaceAtivo && [
            "inspection_workspace",
            "inspection_conversation",
            "inspection_history",
            "inspection_record",
            "inspection_mesa",
        ].includes(screenBase);
        const overlayAtivo = modalNovaInspecaoEstaAberta();
        const layoutCompacto = layoutInspectorCompacto();
        const laudoAtivoId = normalizarLaudoAtualId(
            obterSnapshotEstadoInspectorAtual()?.laudoAtualId
            ?? estado.laudoAtualId
            ?? obterLaudoAtivoIdSeguro()
        );
        const chromeTecnicoOperacional =
            workspaceAtivo &&
            !assistantAtivo &&
            !overlayAtivo &&
            !conversaWorkspaceModoChatAtivo(screenBase, obterSnapshotEstadoInspectorAtual());
        const finalizacaoVisivel =
            workspaceAtivo &&
            !assistantAtivo &&
            !overlayAtivo &&
            !!laudoAtivoId &&
            viewAtual !== "inspection_mesa" &&
            workspacePermiteFinalizacao(obterPayloadStatusRelatorioWorkspaceAtual());
        const railVisivel = chromeTecnicoOperacional && !layoutCompacto && resolveWorkspaceRailVisibility(screenBase);
        const composerVisivel =
            workspaceAtivo &&
            !overlayAtivo &&
            (
                assistantAtivo ||
                viewAtual === "inspection_conversation" ||
                (viewAtual === "inspection_record" && modoEntradaEvidenceFirstAtivo())
            );

        if (el.rodapeEntrada) {
            el.rodapeEntrada.hidden = !composerVisivel;
        }
        if (el.btnIrFimChat) {
            el.btnIrFimChat.hidden = !chromeTecnicoOperacional || viewAtual !== "inspection_conversation";
        }
        if (el.btnMesaWidgetToggle) {
            el.btnMesaWidgetToggle.hidden = !chromeTecnicoOperacional;
        }
        atualizarBotaoWorkspaceRail({
            chromeTecnicoOperacional,
            layoutCompacto,
            view: viewAtual,
            railVisivel,
        });
        if (el.btnWorkspacePreview) {
            el.btnWorkspacePreview.hidden = !chromeTecnicoOperacional || railVisivel || viewAtual === "inspection_history";
        }
        if (el.btnWorkspacePreviewRail) {
            el.btnWorkspacePreviewRail.hidden = !railVisivel || viewAtual === "inspection_mesa";
        }
        if (el.btnFinalizarInspecao) {
            el.btnFinalizarInspecao.hidden = !finalizacaoVisivel;
        }
        sincronizarRotuloAcaoFinalizacaoWorkspace();
        if (el.btnWorkspaceOpenInspecaoModal) {
            el.btnWorkspaceOpenInspecaoModal.hidden = !workspaceAtivo || (!assistantAtivo && !inspectionAtivo) || overlayAtivo;
        }
        if (el.workspaceAssistantLanding) {
            el.workspaceAssistantLanding.hidden = !assistantAtivo || coletarLinhasWorkspace().length > 0;
        }
        atualizarWorkspaceEntryModeNote();

        sincronizarInspectorScreen();
    }

    function focarComposerInspector() {
        if (
            !(el.campoMensagem instanceof HTMLElement) ||
            el.campoMensagem.hidden ||
            el.campoMensagem.closest?.("[hidden], [inert]") ||
            el.campoMensagem.getClientRects().length === 0
        ) {
            return;
        }

        window.requestAnimationFrame(() => {
            window.requestAnimationFrame(() => {
                if (
                    !(el.campoMensagem instanceof HTMLElement) ||
                    el.campoMensagem.hidden ||
                    el.campoMensagem.closest?.("[hidden], [inert]") ||
                    el.campoMensagem.getClientRects().length === 0
                ) {
                    return;
                }

                try {
                    el.campoMensagem.focus({ preventScroll: true });
                } catch (_) {
                    el.campoMensagem.focus();
                }

                if (typeof el.campoMensagem.setSelectionRange === "function") {
                    const fim = el.campoMensagem.value.length;
                    el.campoMensagem.setSelectionRange(fim, fim);
                }
            });
        });
    }

    function detailPossuiContextoVisual(detail = {}) {
        const payload = detail && typeof detail === "object" ? detail : {};
        const card = payload?.laudo_card || payload?.laudoCard || payload?.card || {};

        return Boolean(
            payload?.workspaceTitle ||
            payload?.homeTitle ||
            payload?.title ||
            payload?.workspaceSubtitle ||
            payload?.homeSubtitle ||
            payload?.subtitle ||
            payload?.workspaceStatus ||
            payload?.homeStatus ||
            payload?.statusBadge ||
            payload?.case_lifecycle_status ||
            card?.display_title ||
            card?.titulo ||
            card?.display_subtitle ||
            card?.subtitle ||
            card?.status_badge ||
            card?.status_card_label ||
            card?.case_lifecycle_status
        );
    }

    function enriquecerCardLaudoComContextoVisual(card = {}, contextoVisual = null) {
        const contexto = normalizarContextoVisualSeguro(contextoVisual);
        const payload = card && typeof card === "object" ? { ...card } : {};
        if (!contexto) return payload;

        const titulo = String(contexto.title || payload.display_title || payload.titulo || "").trim();
        const subtitulo = String(contexto.subtitle || payload.display_subtitle || payload.subtitle || "").trim();
        const badge = String(
            contexto.statusBadge ||
            payload.status_badge ||
            obterBadgeLifecycleCase(payload.case_lifecycle_status) ||
            payload.status_card_label ||
            ""
        ).trim();

        if (titulo) {
            payload.titulo = titulo;
            payload.display_title = titulo;
        }
        if (subtitulo) {
            payload.display_subtitle = subtitulo;
            payload.subtitle = subtitulo;
            if (!String(payload.preview || "").trim()) {
                payload.preview = subtitulo;
            }
        }
        if (badge) {
            payload.status_badge = badge.toUpperCase();
        }

        return payload;
    }

    function enriquecerPayloadLaudoComContextoVisual(payload = {}, contextoVisual = null) {
        const contexto = normalizarContextoVisualSeguro(contextoVisual);
        const base = payload && typeof payload === "object" ? { ...payload } : {};
        if (!contexto) return base;

        if (base.laudo_card && typeof base.laudo_card === "object") {
            base.laudo_card = enriquecerCardLaudoComContextoVisual(base.laudo_card, contexto);
        }

        if (!base.workspaceTitle) {
            base.workspaceTitle = contexto.title;
        }
        if (!base.workspaceSubtitle) {
            base.workspaceSubtitle = contexto.subtitle;
        }
        if (!base.workspaceStatus) {
            base.workspaceStatus = contexto.statusBadge;
        }

        return base;
    }

    function abrirChatLivreInspector({ origem = "chat_free_entry" } = {}) {
        const origemNormalizada = String(origem || "chat_free_entry").trim() || "chat_free_entry";
        const snapshotAtual = obterSnapshotEstadoInspectorAtual();
        if (redirecionarEntradaParaReemissaoWorkspace({ origem: origemNormalizada })) {
            return false;
        }
        const veioDoPortal = origemChatLivreEhPortal(origemNormalizada);
        if (!veioDoPortal && !entradaChatLivreDisponivel(snapshotAtual)) {
            sincronizarVisibilidadeAcoesChatLivre(snapshotAtual);
            mostrarToast("O chat livre só fica disponível quando não existe laudo ativo.", "info", 2200);
            return false;
        }

        fecharModalGateQualidade();

        if (modalNovaInspecaoEstaAberta()) {
            fecharNovaInspecaoComScreenSync({ forcar: true, restaurarFoco: false });
        }

        limparForcaTelaInicial();
        sincronizarEstadoInspector({
            laudoAtualId: null,
            estadoRelatorio: "sem_relatorio",
            forceHomeLanding: false,
            modoInspecaoUI: "workspace",
            workspaceStage: "assistant",
            threadTab: "conversa",
            overlayOwner: "",
            assistantLandingFirstSendPending: false,
            freeChatConversationActive: false,
        }, {
            persistirStorage: false,
        });
        exibirLandingAssistenteIA({ limparTimeline: false });

        const screenFinal = sincronizarInspectorScreen();
        focarComposerInspector();
        emitirEventoTariel("tariel:assistant-chat-opened", {
            origem: origemNormalizada,
            screen: screenFinal,
        });

        return screenFinal === "assistant_landing";
    }

    function promoverPortalParaChatNoModoFoco({ origem = "focus_mode_toggle" } = {}) {
        const snapshotAtual = obterSnapshotEstadoInspectorAtual();
        if (!modoFocoPodePromoverPortalParaChat(snapshotAtual)) {
            return false;
        }

        return abrirChatLivreInspector({ origem });
    }

    // =========================================================
    // HIGHLIGHT / ESTADO VISUAL DO COMPOSER
    // =========================================================

    function obterModoMarcador(texto = "") {
        const valor = String(texto || "").trimStart();

        if (/^@insp\b/i.test(valor)) return "insp";
        if (/^eng\b/i.test(valor) || /^@eng\b/i.test(valor)) return "eng";

        return "";
    }

    function atualizarVisualComposer(texto = "") {
        const modo = obterModoMarcador(texto);

        el.campoMensagem?.classList.toggle("modo-humano-ativo", modo === "insp");
        el.campoMensagem?.classList.toggle("modo-eng-ativo", modo === "eng");

        el.pilulaEntrada?.classList.toggle("estado-insp", modo === "insp");
        el.pilulaEntrada?.classList.toggle("estado-eng", modo === "eng");

        atualizarStatusMesaPorComposer(modo);
    }

    function aplicarHighlightComposer(texto = "") {
        if (el.backdropHighlight) {
            el.backdropHighlight.innerHTML = "";
        }
        atualizarVisualComposer(texto);
    }

    function sincronizarScrollBackdrop() {
        return;
    }

    // =========================================================
    // BANNER TEMPORÁRIO DA ENGENHARIA
    // =========================================================


    Object.assign(ctx.actions, {
        abrirChatLivreInspector,
        abrirMesaComContexto,
        abrirNovaInspecaoComScreenSync,
        abrirPreviewWorkspace,
        abrirReemissaoWorkspace,
        aplicarEstadoAcordeaoRailWorkspace,
        aplicarMatrizVisibilidadeInspector,
        aplicarHighlightComposer,
        aplicarPrePromptDaAcaoRapida,
        armarPrimeiroEnvioNovoChatPendente,
        atualizarContextoWorkspaceAtivo,
        atualizarControlesWorkspaceStage,
        atualizarCopyWorkspaceStage,
        atualizarEstadoModoEntrada: ctx.actions.atualizarEstadoModoEntrada,
        atualizarHistoricoHomeExpandido,
        atualizarEmptyStateHonestoConversa: ctx.actions.atualizarEmptyStateHonestoConversa,
        atualizarNomeTemplateAtivo,
        atualizarPainelWorkspaceDerivado: ctx.actions.atualizarPainelWorkspaceDerivado,
        atualizarRecursosComposerWorkspace,
        atualizarStatusChatWorkspace,
        atualizarStatusMesa,
        atualizarThreadWorkspace,
        bindEventosModal,
        bindEventosNovaInspecao: ctx.actions.bindEventosNovaInspecao,
        bindEventosPagina,
        bindEventosSistema,
        bindSystemEvents: ctx.actions.bindSystemEvents,
        bootInspector: ctx.actions.bootInspector,
        carregarContextoFixadoWorkspace,
        fecharNovaInspecaoComScreenSync,
        filtrarSidebarHistorico,
        filtrarTimelineWorkspace: ctx.actions.filtrarTimelineWorkspace,
        fixarContextoWorkspace,
        focarComposerInspector,
        inserirTextoNoComposer,
        citarMensagemWorkspace,
        coletarLinhasWorkspace,
        copiarResumoContextoWorkspace,
        copiarTextoWorkspace: ctx.actions.copiarTextoWorkspace,
        conversaWorkspaceModoChatAtivo,
        criarContextoVisualPadrao,
        detailPossuiContextoVisual,
        definirBotaoFinalizarCarregando,
        definirBotaoIniciarCarregando,
        definirBotaoLaudoCarregando,
        definirBotaoPreviewCarregando,
        definirRetomadaHomePendente,
        definirModoInspecaoUI,
        definirWorkspaceStage,
        enriquecerPayloadLaudoComContextoVisual,
        executarComandoSlash,
        estadoRelatorioPossuiContexto,
        exibirConversaFocadaNovoChat,
        exibirInterfaceInspecaoAtiva,
        fecharSlashCommandPalette,
        fluxoNovoChatFocadoAtivoOuPendente,
        homeForcadoAtivo,
        limparContextoFixadoWorkspace,
        limparForcaTelaInicial,
        limparFluxoNovoChatFocado,
        limparObserversInspector: ctx.actions.limparObserversInspector,
        montarResumoContextoIAWorkspace,
        modalNovaInspecaoEstaAberta,
        contarEvidenciasWorkspace: ctx.actions.contarEvidenciasWorkspace,
        decorarLinhasWorkspace,
        extrairMetaLinhaWorkspace: ctx.actions.extrairMetaLinhaWorkspace,
        normalizarFiltroChat: ctx.actions.normalizarFiltroChat,
        normalizarFiltroTipoHistorico: ctx.actions.normalizarFiltroTipoHistorico,
        normalizarLaudoAtualId,
        normalizarEstadoRelatorio,
        normalizarThreadTab,
        obterContextoVisualAssistente,
        obterEstadoRelatorioAtualSeguro,
        obterLaudoIdDaURLInspector,
        obterRetomadaHomePendente,
        obterSnapshotEstadoInspectorAtual,
        obterTextoDeApoioComposer,
        obterTipoTemplateDoPayload,
        obterContextoVisualLaudoRegistrado: ctx.actions.obterContextoVisualLaudoRegistrado,
        onCampoMensagemWorkspaceKeydown,
        prepararComposerParaEnvioModoEntrada,
        processarAcaoHome,
        promoverPortalParaChatNoModoFoco,
        promoverPrimeiraMensagemNovoChatSePronta,
        registrarPromptHistorico,
        registrarContextoVisualLaudo: ctx.actions.registrarContextoVisualLaudo,
        registrarUltimoPayloadStatusRelatorioWorkspace,
        redirecionarEntradaParaReemissaoWorkspace,
        removerContextoFixadoWorkspace,
        renderizarAnexosWorkspace: ctx.actions.renderizarAnexosWorkspace,
        renderizarAtividadeWorkspace: ctx.actions.renderizarAtividadeWorkspace,
        renderizarContextoIAWorkspace,
        renderizarGovernancaEntradaInspetor,
        renderizarGovernancaHistoricoWorkspace,
        renderizarMesaCardWorkspace,
        renderizarProgressoWorkspace: ctx.actions.renderizarProgressoWorkspace,
        renderizarResumoExecutivoWorkspace,
        renderizarResumoNavegacaoWorkspace,
        resetarFiltrosHistoricoWorkspace: ctx.actions.resetarFiltrosHistoricoWorkspace,
        renderizarSugestoesComposer,
        renderizarWorkspaceOfficialIssue,
        renderizarWorkspacePublicVerification,
        resolverContextoVisualWorkspace,
        restaurarTelaSemRelatorio,
        resolveInspectorScreen,
        resolveWorkspaceView,
        rolarParaHistoricoHome,
        resetarInterfaceInspecao,
        sincronizarInspectorScreen,
        sincronizarEstadoInspector,
        sincronizarResumoHistoricoWorkspace: ctx.actions.sincronizarResumoHistoricoWorkspace,
        sincronizarResumoPendenciasWorkspace: ctx.actions.sincronizarResumoPendenciasWorkspace,
        sincronizarScrollBackdrop,
        sincronizarSSEPorContexto,
        sincronizarSidebarLaudosTabs,
        sincronizarVisibilidadeAcoesChatLivre,
        workspaceViewSuportaRail,
        atualizarVisualComposer,
        inicializarObservadorSidebarHistorico: ctx.actions.inicializarObservadorSidebarHistorico,
        inicializarObservadorWorkspace: ctx.actions.inicializarObservadorWorkspace,
    });
    function bindEventosModal() {
        ctx.actions.bindEventosNovaInspecao?.();
        ctx.actions.bindUiBindings?.();
    }

    function bindEventosPagina() {
        ctx.actions.bindUiBindings?.();
    }

    function bindEventosSistema() {
        ctx.actions.bindSystemEvents?.();

        const onModoFocoAlterado = (event) => {
            if (event?.detail?.ativo !== true) {
                return;
            }

            promoverPortalParaChatNoModoFoco({ origem: "focus_mode_toggle" });
        };

        document.addEventListener("tariel:focus-mode-changed", onModoFocoAlterado);

        window.addEventListener("pagehide", () => {
            fecharSSE();
            limparTimerReconexaoSSE();
            limparTimerFecharMesaWidget();
            limparTimerBanner();
            cancelarCarregamentoPendenciasMesa();
            cancelarCarregamentoMensagensMesaWidget();
            atualizarConexaoMesaWidget("offline");
            ctx.actions.limparObserversInspector?.();
        });

        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "hidden") {
                fecharSSE();
                limparTimerReconexaoSSE();
                return;
            }

            if (!estado.fonteSSE) {
                limparTimerReconexaoSSE();
                sincronizarSSEPorContexto();
            }

            if (contextoTecnicoPrecisaRefresh()) {
                carregarPendenciasMesa({ silencioso: true }).catch(() => {});
            }
        });
    }

    if (PERF?.enabled) {
        const resolverInspectorBaseScreenPorSnapshotOriginal = resolverInspectorBaseScreenPorSnapshot;
        resolverInspectorBaseScreenPorSnapshot = function resolverInspectorBaseScreenPorSnapshotComPerf(...args) {
            const snapshot = args[0] && typeof args[0] === "object" ? args[0] : {};
            return PERF.measureSync(
                "inspetor.resolverInspectorBaseScreenPorSnapshot",
                () => resolverInspectorBaseScreenPorSnapshotOriginal.apply(this, args),
                {
                    category: "state",
                    detail: {
                        modoInspecaoUI: snapshot.modoInspecaoUI || "",
                        workspaceStage: snapshot.workspaceStage || "",
                        overlayOwner: snapshot.overlayOwner || "",
                    },
                }
            );
        };

        const resolverEstadoAutoritativoInspectorOriginal = resolverEstadoAutoritativoInspector;
        resolverEstadoAutoritativoInspector = function resolverEstadoAutoritativoInspectorComPerf(...args) {
            const overrides = args[0] && typeof args[0] === "object" ? args[0] : {};
            return PERF.measureSync(
                "inspetor.resolverEstadoAutoritativoInspector",
                () => resolverEstadoAutoritativoInspectorOriginal.apply(this, args),
                {
                    category: "state",
                    detail: {
                        overrideKeys: Object.keys(overrides),
                    },
                }
            );
        };

        const espelharEstadoInspectorNoDatasetOriginal = espelharEstadoInspectorNoDataset;
        espelharEstadoInspectorNoDataset = function espelharEstadoInspectorNoDatasetComPerf(...args) {
            const snapshot = args[0] && typeof args[0] === "object" ? args[0] : {};
            PERF.count("inspetor.dataset.sync", 1, {
                category: "counter",
                detail: {
                    screen: snapshot.inspectorScreen || "",
                    baseScreen: snapshot.inspectorBaseScreen || "",
                },
            });
            return PERF.measureSync(
                "inspetor.espelharEstadoInspectorNoDataset",
                () => espelharEstadoInspectorNoDatasetOriginal.apply(this, args),
                {
                    category: "state",
                    detail: {
                        screen: snapshot.inspectorScreen || "",
                        baseScreen: snapshot.inspectorBaseScreen || "",
                    },
                }
            );
        };

        const espelharEstadoInspectorNoStorageOriginal = espelharEstadoInspectorNoStorage;
        espelharEstadoInspectorNoStorage = function espelharEstadoInspectorNoStorageComPerf(...args) {
            const snapshot = args[0] && typeof args[0] === "object" ? args[0] : {};
            const opts = args[1] && typeof args[1] === "object" ? args[1] : {};
            PERF.count("inspetor.storage.sync", 1, {
                category: "counter",
                detail: {
                    persistirStorage: opts.persistirStorage !== false,
                },
            });
            return PERF.measureSync(
                "inspetor.espelharEstadoInspectorNoStorage",
                () => espelharEstadoInspectorNoStorageOriginal.apply(this, args),
                {
                    category: "storage",
                    detail: {
                        laudoAtualId: snapshot.laudoAtualId || null,
                        persistirStorage: opts.persistirStorage !== false,
                    },
                }
            );
        };

        const sincronizarEstadoInspectorOriginal = sincronizarEstadoInspector;
        sincronizarEstadoInspector = function sincronizarEstadoInspectorComPerf(...args) {
            const overrides = args[0] && typeof args[0] === "object" ? args[0] : {};
            const opts = args[1] && typeof args[1] === "object" ? args[1] : {};
            return PERF.measureSync(
                "inspetor.sincronizarEstadoInspector",
                () => {
                    const snapshot = sincronizarEstadoInspectorOriginal.apply(this, args);
                    reportarProntidaoInspector(snapshot);
                    return snapshot;
                },
                {
                    category: "state",
                    detail: {
                        overrideKeys: Object.keys(overrides),
                        persistirStorage: opts.persistirStorage !== false,
                    },
                }
            );
        };

        if (window.TarielInspectorState) {
            window.TarielInspectorState.resolverEstadoAutoritativoInspector = resolverEstadoAutoritativoInspector;
            window.TarielInspectorState.sincronizarEstadoInspector = sincronizarEstadoInspector;
            window.TarielInspectorState.atualizarThreadWorkspace = atualizarThreadWorkspace;
        }

        const exibirConversaFocadaNovoChatOriginal = exibirConversaFocadaNovoChat;
        exibirConversaFocadaNovoChat = function exibirConversaFocadaNovoChatComPerf(...args) {
            return PERF.measureSync(
                "inspetor.exibirConversaFocadaNovoChat",
                () => {
                    const resultado = exibirConversaFocadaNovoChatOriginal.apply(this, args);
                    PERF.finish("transition.primeira_mensagem_novo_chat", obterResumoPerfInspector());
                    reportarProntidaoInspector();
                    PERF.snapshotDOM?.("inspetor:focused-conversation");
                    return resultado;
                },
                {
                    category: "transition",
                    detail: obterResumoPerfInspector(),
                }
            );
        };

        const promoverPrimeiraMensagemNovoChatSeProntaOriginal = promoverPrimeiraMensagemNovoChatSePronta;
        promoverPrimeiraMensagemNovoChatSePronta = function promoverPrimeiraMensagemNovoChatSeProntaComPerf(...args) {
            const opcoes = args[0] && typeof args[0] === "object" ? args[0] : {};
            return PERF.measureSync(
                "inspetor.promoverPrimeiraMensagemNovoChatSePronta",
                () => promoverPrimeiraMensagemNovoChatSeProntaOriginal.apply(this, args),
                {
                    category: "transition",
                    detail: {
                        forcar: opcoes.forcar === true,
                        focarComposer: opcoes.focarComposer === true,
                        ...obterResumoPerfInspector(),
                    },
                }
            );
        };

        const atualizarPainelWorkspaceDerivadoOriginal = atualizarPainelWorkspaceDerivado;
        atualizarPainelWorkspaceDerivado = function atualizarPainelWorkspaceDerivadoComPerf(...args) {
            return PERF.measureSync(
                "inspetor.atualizarPainelWorkspaceDerivado",
                () => atualizarPainelWorkspaceDerivadoOriginal.apply(this, args),
                {
                    category: "render",
                    detail: obterResumoPerfInspector(),
                }
            );
        };

        const atualizarThreadWorkspaceOriginal = atualizarThreadWorkspace;
        atualizarThreadWorkspace = function atualizarThreadWorkspaceComPerf(...args) {
            const tab = String(args[0] || "conversa").trim().toLowerCase() || "conversa";
            return PERF.measureSync(
                "inspetor.atualizarThreadWorkspace",
                () => {
                    const resultado = atualizarThreadWorkspaceOriginal.apply(this, args);
                    PERF.finish(`transition.thread_tab.${tab}`, {
                        tab,
                        ...obterResumoPerfInspector(),
                    });
                    reportarProntidaoInspector();
                    return resultado;
                },
                {
                    category: "render",
                    detail: {
                        tab,
                        ...obterResumoPerfInspector(),
                    },
                }
            );
        };

        const aplicarMatrizVisibilidadeInspectorOriginal = aplicarMatrizVisibilidadeInspector;
        aplicarMatrizVisibilidadeInspector = function aplicarMatrizVisibilidadeInspectorComPerf(...args) {
            return PERF.measureSync(
                "inspetor.aplicarMatrizVisibilidadeInspector",
                () => aplicarMatrizVisibilidadeInspectorOriginal.apply(this, args),
                {
                    category: "state",
                    detail: obterResumoPerfInspector(args[1]),
                }
            );
        };

        const resolveInspectorScreenOriginal = resolveInspectorScreen;
        resolveInspectorScreen = function resolveInspectorScreenComPerf(...args) {
            return PERF.measureSync(
                "inspetor.resolveInspectorScreen",
                () => resolveInspectorScreenOriginal.apply(this, args),
                {
                    category: "state",
                    detail: obterResumoPerfInspector(),
                }
            );
        };

        const sincronizarWorkspaceRailOriginal = sincronizarWorkspaceRail;
        sincronizarWorkspaceRail = function sincronizarWorkspaceRailComPerf(...args) {
            return PERF.measureSync(
                "inspetor.sincronizarWorkspaceRail",
                () => sincronizarWorkspaceRailOriginal.apply(this, args),
                {
                    category: "state",
                    detail: obterResumoPerfInspector(),
                }
            );
        };

        const sincronizarWidgetsGlobaisWorkspaceOriginal = sincronizarWidgetsGlobaisWorkspace;
        sincronizarWidgetsGlobaisWorkspace = function sincronizarWidgetsGlobaisWorkspaceComPerf(...args) {
            return PERF.measureSync(
                "inspetor.sincronizarWidgetsGlobaisWorkspace",
                () => sincronizarWidgetsGlobaisWorkspaceOriginal.apply(this, args),
                {
                    category: "state",
                    detail: obterResumoPerfInspector(),
                }
            );
        };

        const sincronizarInspectorScreenOriginal = sincronizarInspectorScreen;
        sincronizarInspectorScreen = function sincronizarInspectorScreenComPerf(...args) {
            return PERF.measureSync(
                "inspetor.sincronizarInspectorScreen",
                () => {
                    const screen = sincronizarInspectorScreenOriginal.apply(this, args);
                    reportarProntidaoInspector();
                    PERF.snapshotDOM?.(`inspetor:screen:${String(screen || "unknown")}`);
                    if (screen === "assistant_landing") {
                        PERF.finish("transition.novo_chat", {
                            ...obterResumoPerfInspector(),
                            screen,
                        });
                    }
                    if (screen === "new_inspection") {
                        PERF.finish("transition.abrir_nova_inspecao", {
                            ...obterResumoPerfInspector(),
                            screen,
                        });
                    }
                    return screen;
                },
                {
                    category: "state",
                    detail: obterResumoPerfInspector(),
                }
            );
        };

        const abrirChatLivreInspectorOriginal = abrirChatLivreInspector;
        abrirChatLivreInspector = function abrirChatLivreInspectorComPerf(...args) {
            const payload = args[0] && typeof args[0] === "object" ? args[0] : {};
            return PERF.measureSync(
                "inspetor.abrirChatLivreInspector",
                () => abrirChatLivreInspectorOriginal.apply(this, args),
                {
                    category: "transition",
                    detail: {
                        origem: payload.origem || "chat_free_entry",
                        ...obterResumoPerfInspector(),
                    },
                }
            );
        };

        const abrirNovaInspecaoComScreenSyncOriginal = abrirNovaInspecaoComScreenSync;
        abrirNovaInspecaoComScreenSync = function abrirNovaInspecaoComScreenSyncComPerf(...args) {
            const payload = args[0] && typeof args[0] === "object" ? args[0] : {};
            return PERF.measureSync(
                "inspetor.abrirNovaInspecaoComScreenSync",
                () => abrirNovaInspecaoComScreenSyncOriginal.apply(this, args),
                {
                    category: "transition",
                    detail: {
                        tipoPrefill: payload.tipoPrefill || "",
                        possuiPrePrompt: !!String(payload.prePrompt || "").trim(),
                        ...obterResumoPerfInspector(),
                    },
                }
            );
        };
    }

    // =========================================================
    // BOOT
    // =========================================================

    async function boot() {
        await ctx.actions.bootInspector?.();
    }

    if (PERF?.enabled) {
        const bootOriginal = boot;
        boot = async function bootComPerf(...args) {
            PERF.begin("transition.boot_inspetor", {
                readyState: document.readyState,
            });
            return PERF.measureAsync(
                "inspetor.boot",
                async () => {
                    const resultado = await bootOriginal.apply(this, args);
                    reportarProntidaoInspector();
                    PERF.finish("transition.boot_inspetor", obterResumoPerfInspector());
                    PERF.snapshotDOM?.("inspetor:boot-final");
                    return resultado;
                },
                {
                    category: "boot",
                    detail: {
                        readyState: document.readyState,
                    },
                }
            );
        };
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
