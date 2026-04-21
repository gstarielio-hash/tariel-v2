(function () {
    "use strict";

    const PORTAL_WIRED_FLAG = "__TARIEL_CLIENTE_PORTAL_WIRED__";
    const PORTAL_BOOT_STATUS_BOOTING = "booting";
    const PORTAL_BOOT_STATUS_READY = "ready";
    const PORTAL_BOOT_STATUS_FAILED = "failed";
    const PORTAL_BOOT_CONTRACT = Object.freeze({
        name: "cliente/portal",
        version: "2.8",
        entrypoint: "portal.js",
        scriptSelector: 'script[data-portal-contract="cliente"][data-portal-module]',
        scriptOrder: Object.freeze([
            "runtime",
            "priorities",
            "admin",
            "chat",
            "mesa",
            "sharedHelpers",
            "shell",
            "bindings",
            "portal",
        ]),
        optionalGlobals: Object.freeze([
            Object.freeze({
                key: "TarielPerf",
                expectedWhenMeta: "tariel-perf-mode",
                reason: "observabilidade opcional do portal cliente",
            }),
        ]),
        requiredModules: Object.freeze([
            Object.freeze({
                key: "TarielClientePortalRuntime",
                alias: "runtime",
                requiredForBoot: true,
                temporaryCompat: false,
                dependsOnScriptOrder: true,
                exportShape: Object.freeze([
                    "api",
                    "definirTab",
                    "ehAbortError",
                    "escapeAttr",
                    "escapeHtml",
                    "feedback",
                    "formatarBytes",
                    "formatarCapacidadeRestante",
                    "formatarInteiro",
                    "formatarLimitePlano",
                    "formatarPercentual",
                    "formatarVariacao",
                    "lerNumeroPersistido",
                    "normalizarSecao",
                    "perfAsync",
                    "perfSnapshot",
                    "perfSync",
                    "persistirSelecao",
                    "registrarSecaoAtiva",
                    "restaurarTab",
                    "secaoAtualDaUrl",
                    "scrollToPortalSection",
                    "sincronizarTabComUrl",
                    "sincronizarUrlDaTab",
                    "sincronizarUrlDaSecao",
                    "tabAtualDaUrl",
                    "texto",
                    "textoComQuebras",
                    "withBusy",
                ]),
            }),
            Object.freeze({
                key: "TarielClientePortalPriorities",
                alias: "priorities",
                requiredForBoot: true,
                temporaryCompat: false,
                dependsOnScriptOrder: true,
                exportShape: Object.freeze([
                    "construirPrioridadesPortal",
                    "filtrarLaudosChat",
                    "filtrarLaudosMesa",
                    "filtrarUsuarios",
                    "htmlBarrasHistorico",
                    "horasDesdeAtualizacao",
                    "laudoBadge",
                    "laudoChatParado",
                    "laudoMesaParado",
                    "obterNomePapel",
                    "obterPlanoCatalogo",
                    "ordenarPorPrioridade",
                    "parseDataIso",
                    "prioridadeChat",
                    "prioridadeEmpresa",
                    "prioridadeMesa",
                    "prioridadeUsuario",
                    "resumoCanalOperacional",
                    "resumoEsperaHoras",
                    "roleBadge",
                    "rotuloSituacaoChat",
                    "rotuloSituacaoMesa",
                    "rotuloSituacaoUsuarios",
                    "slugPapel",
                    "tomCapacidadeEmpresa",
                    "userStatusBadges",
                    "variantStatusLaudo",
                ]),
            }),
            Object.freeze({
                key: "TarielClientePortalAdmin",
                alias: "admin",
                requiredForBoot: true,
                temporaryCompat: false,
                dependsOnScriptOrder: true,
                exportShape: Object.freeze([
                    "aplicarFiltrosUsuarios",
                    "aplicarFiltroUsuariosRapido",
                    "abrirSecaoAdmin",
                    "bindAdminActions",
                    "focarUsuarioNaTabela",
                    "limparFiltroUsuariosRapido",
                    "prepararUpgradeGuiado",
                    "registrarInteressePlano",
                    "renderAdmin",
                    "renderPreviewPlano",
                    "renderUsuarios",
                    "resolverSecaoAdminPorTarget",
                ]),
            }),
            Object.freeze({
                key: "TarielClientePortalChat",
                alias: "chat",
                requiredForBoot: true,
                temporaryCompat: false,
                dependsOnScriptOrder: true,
                exportShape: Object.freeze([
                    "aplicarFiltroChatRapido",
                    "abrirSecaoChat",
                    "atualizarBuscaChat",
                    "bindChatActions",
                    "limparDocumentoChatPendente",
                    "limparFiltroChatRapido",
                    "loadChat",
                    "renderChatCapacidade",
                    "renderChatContext",
                    "renderChatList",
                    "renderChatMensagens",
                    "renderChatMovimentos",
                    "renderChatResumo",
                    "renderChatTriagem",
                    "resolverSecaoChatPorTarget",
                ]),
            }),
            Object.freeze({
                key: "TarielClientePortalMesa",
                alias: "mesa",
                requiredForBoot: true,
                temporaryCompat: false,
                dependsOnScriptOrder: true,
                exportShape: Object.freeze([
                    "aplicarFiltroMesaRapido",
                    "abrirSecaoMesa",
                    "atualizarBuscaMesa",
                    "bindMesaActions",
                    "cancelarCarregamentoMesa",
                    "limparFiltroMesaRapido",
                    "loadMesa",
                    "renderMesaContext",
                    "renderMesaList",
                    "renderMesaMensagens",
                    "renderMesaMovimentos",
                    "renderMesaResumo",
                    "renderMesaResumoGeral",
                    "renderMesaTriagem",
                    "resolverSecaoMesaPorTarget",
                ]),
            }),
            Object.freeze({
                key: "TarielClientePortalSharedHelpers",
                alias: "sharedHelpers",
                requiredForBoot: true,
                temporaryCompat: false,
                dependsOnScriptOrder: true,
                exportShape: Object.freeze([
                    "renderAnexos",
                    "renderAvisosOperacionais",
                ]),
            }),
            Object.freeze({
                key: "TarielClientePortalShell",
                alias: "shell",
                requiredForBoot: true,
                temporaryCompat: false,
                dependsOnScriptOrder: true,
                exportShape: Object.freeze([
                    "atualizarBadgesTabs",
                    "bootstrapPortal",
                    "renderCentralPrioridades",
                    "renderEverything",
                    "sincronizarSelecoes",
                ]),
            }),
            Object.freeze({
                key: "TarielClientePortalBindings",
                alias: "bindings",
                requiredForBoot: true,
                temporaryCompat: false,
                dependsOnScriptOrder: true,
                exportShape: Object.freeze([
                    "bindCommercialActions",
                    "bindCrossSliceRouter",
                    "bindFiltros",
                    "bindTabs",
                ]),
            }),
        ]),
    });
    const PORTAL_BRIDGE_SPECS = PORTAL_BOOT_CONTRACT.requiredModules;
    const previousBootState = window[PORTAL_WIRED_FLAG];

    if (
        previousBootState === true ||
        previousBootState?.status === PORTAL_BOOT_STATUS_BOOTING ||
        previousBootState?.status === PORTAL_BOOT_STATUS_READY
    ) {
        return;
    }

    const STORAGE_TAB_KEY = "tariel.cliente.tab";
    const STORAGE_CHAT_KEY = "tariel.cliente.chat.laudo";
    const STORAGE_MESA_KEY = "tariel.cliente.mesa.laudo";
    const bodyDataset = document.body?.dataset || {};
    const INITIAL_TAB = ["admin", "chat", "mesa"].includes(bodyDataset.clienteTabInicial)
        ? bodyDataset.clienteTabInicial
        : "admin";
    const INITIAL_ADMIN_SECTION = ["overview", "capacity", "team", "support"].includes(bodyDataset.clienteAdminSectionInicial)
        ? bodyDataset.clienteAdminSectionInicial
        : "overview";
    const INITIAL_CHAT_SECTION = ["overview", "new", "queue", "case"].includes(bodyDataset.clienteChatSectionInicial)
        ? bodyDataset.clienteChatSectionInicial
        : "overview";
    const INITIAL_MESA_SECTION = ["overview", "queue", "pending", "reply"].includes(bodyDataset.clienteMesaSectionInicial)
        ? bodyDataset.clienteMesaSectionInicial
        : "overview";
    const ROUTE_MAP = Object.freeze({
        admin: bodyDataset.clienteRouteAdmin || "/cliente/painel",
        chat: bodyDataset.clienteRouteChat || "/cliente/chat",
        mesa: bodyDataset.clienteRouteMesa || "/cliente/mesa",
    });

    const state = {
        bootstrap: null,
        surface: {
            loaded: {
                admin: false,
                chat: false,
                mesa: false,
            },
        },
        ui: {
            tab: INITIAL_TAB,
            adminSection: INITIAL_ADMIN_SECTION,
            chatSection: INITIAL_CHAT_SECTION,
            mesaSection: INITIAL_MESA_SECTION,
            sections: {
                admin: INITIAL_ADMIN_SECTION,
                chat: INITIAL_CHAT_SECTION,
                mesa: INITIAL_MESA_SECTION,
            },
            feedbackTimer: null,
            usuariosBusca: "",
            usuariosPapel: "todos",
            usuariosSituacao: "",
            adminAuditFilter: "all",
            adminAuditSearch: "",
            chatBusca: "",
            chatSituacao: "",
            mesaBusca: "",
            mesaSituacao: "",
            usuarioEmDestaque: null,
        },
        chat: {
            laudoId: null,
            loadedLaudoId: null,
            mensagens: [],
            documentoTexto: "",
            documentoNome: "",
            documentoChars: 0,
            documentoTruncado: false,
        },
        mesa: {
            laudoId: null,
            loadedLaudoId: null,
            mensagens: [],
            pacote: null,
            loadController: null,
        },
    };

    const $ = (id) => document.getElementById(id);
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
    const perf = window.TarielPerf || null;
    const bootState = {
        status: PORTAL_BOOT_STATUS_BOOTING,
        attempt: Number(previousBootState?.attempt || 0) + 1,
        startedAt: new Date().toISOString(),
        finishedAt: null,
        warnings: [],
        errors: [],
        missingRequired: [],
        missingOptional: [],
        lastError: null,
        modules: {},
        scriptOrder: {
            expected: [...PORTAL_BOOT_CONTRACT.scriptOrder],
            observed: [],
            valid: true,
            duplicates: [],
        },
        contract: {
            name: PORTAL_BOOT_CONTRACT.name,
            version: PORTAL_BOOT_CONTRACT.version,
            entrypoint: PORTAL_BOOT_CONTRACT.entrypoint,
            scriptSelector: PORTAL_BOOT_CONTRACT.scriptSelector,
            scriptOrder: [...PORTAL_BOOT_CONTRACT.scriptOrder],
            requiredModules: PORTAL_BRIDGE_SPECS.map((spec) => ({
                alias: spec.alias,
                key: spec.key,
                requiredForBoot: Boolean(spec.requiredForBoot),
                temporaryCompat: Boolean(spec.temporaryCompat),
                dependsOnScriptOrder: Boolean(spec.dependsOnScriptOrder),
            })),
            optionalGlobals: PORTAL_BOOT_CONTRACT.optionalGlobals.map((spec) => ({
                key: spec.key,
                expectedWhenMeta: spec.expectedWhenMeta,
                reason: spec.reason,
            })),
        },
    };
    const bridgeSpecByAlias = PORTAL_BRIDGE_SPECS.reduce((acc, spec) => {
        acc[spec.alias] = spec;
        return acc;
    }, {});
    const consoleRef = window.console || null;
    const emittedBootCodes = new Set();

    window[PORTAL_WIRED_FLAG] = bootState;

    function emitBootNotice(level, code, message, details = {}) {
        if (emittedBootCodes.has(code)) return;
        emittedBootCodes.add(code);

        const event = {
            level,
            code,
            message,
            details,
            at: new Date().toISOString(),
        };
        if (level === "warn") {
            bootState.warnings.push(event);
            if (typeof consoleRef?.warn === "function") {
                consoleRef.warn(`[cliente/portal.boot:${code}] ${message}`, details);
            }
            return;
        }

        bootState.errors.push(event);
        if (typeof consoleRef?.error === "function") {
            consoleRef.error(`[cliente/portal.boot:${code}] ${message}`, details);
        }
    }

    function formatBootOrder(itens) {
        return Array.isArray(itens) && itens.length ? itens.join(" -> ") : "(nenhuma ordem observada)";
    }

    function markBootReady() {
        bootState.status = PORTAL_BOOT_STATUS_READY;
        bootState.finishedAt = new Date().toISOString();
        bootState.lastError = null;
    }

    function failBoot(reason, options = {}) {
        const { code = "boot-failed", details = {}, rethrow = true } = options;
        const error = reason instanceof Error ? reason : new Error(String(reason || "Falha ao iniciar o portal cliente."));
        bootState.status = PORTAL_BOOT_STATUS_FAILED;
        bootState.finishedAt = new Date().toISOString();
        bootState.lastError = error.message;
        emitBootNotice("error", code, error.message, details);
        if (rethrow) throw error;
        return error;
    }

    function readMetaFlag(name) {
        return document.querySelector(`meta[name="${name}"]`)?.content === "1";
    }

    function validateOptionalGlobals() {
        const missing = PORTAL_BOOT_CONTRACT.optionalGlobals.filter((spec) => {
            if (spec.expectedWhenMeta && !readMetaFlag(spec.expectedWhenMeta)) {
                return false;
            }
            return !window[spec.key];
        });

        bootState.missingOptional = missing.map((spec) => spec.key);
        if (!missing.length) return;

        emitBootNotice(
            "warn",
            "missing-optional-globals",
            `Cliente portal boot contract: globals opcionais ausentes: ${missing.map((spec) => spec.key).join(", ")}.`,
            {
                missing: missing.map((spec) => ({
                    key: spec.key,
                    reason: spec.reason,
                    expectedWhenMeta: spec.expectedWhenMeta || "",
                })),
            }
        );
    }

    function validateTemplateOrder() {
        const observed = [...document.querySelectorAll(PORTAL_BOOT_CONTRACT.scriptSelector)]
            .map((elemento) => elemento.dataset.portalModule || "")
            .filter(Boolean);
        const duplicates = observed.filter((item, index) => observed.indexOf(item) !== index);
        const valid =
            duplicates.length === 0 &&
            observed.length === PORTAL_BOOT_CONTRACT.scriptOrder.length &&
            PORTAL_BOOT_CONTRACT.scriptOrder.every((item, index) => observed[index] === item);

        bootState.scriptOrder.observed = observed;
        bootState.scriptOrder.valid = valid;
        bootState.scriptOrder.duplicates = [...new Set(duplicates)];

        if (valid) return;

        emitBootNotice(
            "warn",
            "template-order-mismatch",
            `Cliente portal boot contract: ordem do template divergente. Esperada: ${formatBootOrder(PORTAL_BOOT_CONTRACT.scriptOrder)}. Observada: ${formatBootOrder(observed)}.`,
            {
                expected: [...PORTAL_BOOT_CONTRACT.scriptOrder],
                observed,
                duplicates: [...new Set(duplicates)],
            }
        );
    }

    function resolveBridgeFactories() {
        const bridgeFactories = PORTAL_BRIDGE_SPECS.reduce((acc, spec) => {
            acc[spec.alias] = window[spec.key];
            return acc;
        }, {});
        const missing = PORTAL_BRIDGE_SPECS.filter((spec) => spec.requiredForBoot && typeof bridgeFactories[spec.alias] !== "function");

        if (!missing.length) {
            return bridgeFactories;
        }

        bootState.missingRequired = missing.map((spec) => spec.key);
        failBoot(
            `Cliente portal boot contract violado: faltam bridges obrigatorias: ${missing.map((spec) => `${spec.key} (${spec.alias})`).join(", ")}. Ordem esperada: ${formatBootOrder(PORTAL_BOOT_CONTRACT.scriptOrder)}.`,
            {
                code: "missing-required-bridges",
                details: {
                    missing: missing.map((spec) => ({
                        alias: spec.alias,
                        key: spec.key,
                    })),
                    expectedOrder: [...PORTAL_BOOT_CONTRACT.scriptOrder],
                },
            }
        );
    }

    function createRequiredModule(alias, factory, config) {
        const spec = bridgeSpecByAlias[alias];
        if (!spec) {
            failBoot(`Cliente portal boot contract violado: especificacao ausente para o modulo ${alias}.`, {
                code: "unknown-module-spec",
                details: { alias },
            });
        }

        if (typeof factory !== "function") {
            failBoot(`Cliente portal boot contract violado: ${spec.key} (${alias}) nao esta disponivel como factory.`, {
                code: `factory-${alias}-missing`,
                details: {
                    alias,
                    bridge: spec.key,
                },
            });
        }

        let moduleApi = null;
        try {
            moduleApi = factory(config);
        } catch (erro) {
            failBoot(
                `Cliente portal boot contract violado: falha ao inicializar ${spec.key} (${alias}). ${erro?.message || ""}`.trim(),
                {
                    code: `factory-${alias}-failed`,
                    details: {
                        alias,
                        bridge: spec.key,
                        errorName: erro?.name || "",
                    },
                }
            );
        }

        if (!moduleApi || typeof moduleApi !== "object") {
            failBoot(`Cliente portal boot contract violado: ${spec.key} (${alias}) nao retornou uma API valida.`, {
                code: `factory-${alias}-invalid`,
                details: {
                    alias,
                    bridge: spec.key,
                },
            });
        }

        const missingExports = spec.exportShape.filter((nome) => typeof moduleApi[nome] !== "function");
        if (missingExports.length) {
            failBoot(
                `Cliente portal boot contract violado: ${spec.key} (${alias}) nao expôs ${missingExports.join(", ")}.`,
                {
                    code: `factory-${alias}-exports`,
                    details: {
                        alias,
                        bridge: spec.key,
                        missingExports,
                    },
                }
            );
        }

        bootState.modules[alias] = {
            bridge: spec.key,
            validatedExports: [...spec.exportShape],
            ready: true,
        };
        return moduleApi;
    }

    validateOptionalGlobals();
    validateTemplateOrder();

    const bridgeFactories = resolveBridgeFactories();

    const createRuntime = bridgeFactories.runtime;
    const createPriorities = bridgeFactories.priorities;
    const createAdmin = bridgeFactories.admin;
    const createChat = bridgeFactories.chat;
    const createMesa = bridgeFactories.mesa;
    const createSharedHelpers = bridgeFactories.sharedHelpers;
    const createShell = bridgeFactories.shell;
    const createBindings = bridgeFactories.bindings;

    const runtimeModule = createRequiredModule("runtime", createRuntime, {
        csrf,
        documentRef: document,
        fetchRef: (...args) => fetch(...args),
        getById: $,
        localStorageRef: window.localStorage,
        historyRef: window.history,
        initialTab: INITIAL_TAB,
        routeMap: ROUTE_MAP,
        perf,
        snapshotSelectors: {
            shell: ".cliente-shell",
            hero: ".cliente-hero",
            tabs: ".cliente-tabs",
            panelAdmin: "#panel-admin",
            panelChat: "#panel-chat",
            panelMesa: "#panel-mesa",
            listaUsuarios: "#lista-usuarios",
            listaChat: "#lista-chat-laudos",
            listaMesa: "#lista-mesa-laudos",
            mensagensChat: "#chat-mensagens",
            mensagensMesa: "#mesa-mensagens",
        },
        state,
        storageKeys: {
            chat: STORAGE_CHAT_KEY,
            mesa: STORAGE_MESA_KEY,
            tab: STORAGE_TAB_KEY,
        },
        locationRef: window.location,
        windowRef: window,
    });

    const {
        api,
        definirTab,
        ehAbortError,
        escapeAttr,
        escapeHtml,
        feedback,
        formatarBytes,
        formatarCapacidadeRestante,
        formatarInteiro,
        formatarLimitePlano,
        formatarPercentual,
        formatarVariacao,
        lerNumeroPersistido,
        normalizarSecao,
        perfAsync,
        perfSnapshot,
        perfSync,
        persistirSelecao,
        registrarSecaoAtiva,
        restaurarTab,
        secaoAtualDaUrl,
        scrollToPortalSection,
        sincronizarTabComUrl,
        sincronizarUrlDaSecao,
        tabAtualDaUrl,
        texto,
        textoComQuebras,
        withBusy,
    } = runtimeModule;

    perf?.noteModule?.("cliente/portal.js", { readyState: document.readyState });

    const prioritiesModule = createRequiredModule("priorities", createPriorities, {
        helpers: {
            escapeAttr,
            escapeHtml,
            formatarCapacidadeRestante,
            formatarInteiro,
            formatarLimitePlano,
            formatarPercentual,
            formatarVariacao,
            texto,
        },
        state,
    });

    const {
        construirPrioridadesPortal,
        filtrarLaudosChat,
        filtrarLaudosMesa,
        filtrarUsuarios,
        htmlBarrasHistorico,
        horasDesdeAtualizacao,
        laudoBadge,
        laudoChatParado,
        laudoMesaParado,
        obterNomePapel,
        obterPlanoCatalogo,
        ordenarPorPrioridade,
        parseDataIso,
        prioridadeChat,
        prioridadeEmpresa,
        prioridadeMesa,
        prioridadeUsuario,
        resumoCanalOperacional,
        resumoEsperaHoras,
        roleBadge,
        rotuloSituacaoChat,
        rotuloSituacaoMesa,
        rotuloSituacaoUsuarios,
        slugPapel,
        tomCapacidadeEmpresa,
        userStatusBadges,
        variantStatusLaudo,
    } = prioritiesModule;

    let bootstrapPortal = async () => null;
    let atualizarBadgesTabs = () => null;

    const sharedHelpersModule = createRequiredModule("sharedHelpers", createSharedHelpers, {
        documentRef: document,
        getById: $,
        helpers: {
            escapeAttr,
            escapeHtml,
            formatarBytes,
            resumoCanalOperacional,
            texto,
        },
        state,
    });

    const {
        renderAnexos,
        renderAvisosOperacionais,
    } = sharedHelpersModule;

    const adminModule = createRequiredModule("admin", createAdmin, {
        actions: {
            bootstrapPortal: (...args) => bootstrapPortal(...args),
        },
        documentRef: document,
        filters: {
            filtrarUsuarios,
        },
        getById: $,
        helpers: {
            api,
            definirTab,
            escapeAttr,
            escapeHtml,
            feedback,
            formatarCapacidadeRestante,
            formatarInteiro,
            formatarLimitePlano,
            formatarPercentual,
            formatarVariacao,
            htmlBarrasHistorico,
            obterNomePapel,
            obterPlanoCatalogo,
            ordenarPorPrioridade,
            parseDataIso,
            prioridadeEmpresa,
            prioridadeUsuario,
            roleBadge,
            slugPapel,
            sincronizarUrlDaSecao,
            texto,
            tomCapacidadeEmpresa,
            userStatusBadges,
            withBusy,
        },
        labels: {
            rotuloSituacaoUsuarios,
        },
        state,
        windowRef: window,
    });

    const {
        aplicarFiltrosUsuarios,
        aplicarFiltroUsuariosRapido,
        abrirSecaoAdmin,
        bindAdminActions,
        focarUsuarioNaTabela,
        limparFiltroUsuariosRapido,
        prepararUpgradeGuiado,
        registrarInteressePlano,
        renderAdmin,
        renderPreviewPlano,
        renderUsuarios,
        resolverSecaoAdminPorTarget,
    } = adminModule;

    const chatModule = createRequiredModule("chat", createChat, {
        actions: {
            bootstrapPortal: (...args) => bootstrapPortal(...args),
        },
        documentRef: document,
        filters: {
            filtrarLaudosChat,
        },
        getById: $,
        helpers: {
            api,
            definirTab,
            escapeAttr,
            escapeHtml,
            feedback,
            formatarCapacidadeRestante,
            formatarInteiro,
            horasDesdeAtualizacao,
            laudoBadge,
            laudoChatParado,
            ordenarPorPrioridade,
            parseDataIso,
            perfAsync,
            perfSnapshot,
            persistirSelecao,
            prioridadeChat,
            renderAnexos,
            resumoEsperaHoras,
            rotuloSituacaoChat,
            sincronizarUrlDaSecao,
            texto,
            textoComQuebras,
            tomCapacidadeEmpresa,
            variantStatusLaudo,
            withBusy,
        },
        state,
        storageKeys: {
            chat: STORAGE_CHAT_KEY,
        },
    });

    const {
        aplicarFiltroChatRapido,
        abrirSecaoChat,
        atualizarBuscaChat,
        bindChatActions,
        limparDocumentoChatPendente,
        limparFiltroChatRapido,
        loadChat,
        renderChatCapacidade,
        renderChatContext,
        renderChatList,
        renderChatMensagens,
        renderChatMovimentos,
        renderChatResumo,
        renderChatTriagem,
        resolverSecaoChatPorTarget,
    } = chatModule;

    const mesaModule = createRequiredModule("mesa", createMesa, {
        actions: {
            atualizarBadgesTabs: (...args) => atualizarBadgesTabs(...args),
            bootstrapPortal: (...args) => bootstrapPortal(...args),
        },
        documentRef: document,
        filters: {
            filtrarLaudosMesa,
        },
        getById: $,
        helpers: {
            api,
            ehAbortError,
            escapeAttr,
            escapeHtml,
            feedback,
            formatarInteiro,
            horasDesdeAtualizacao,
            laudoBadge,
            laudoMesaParado,
            ordenarPorPrioridade,
            parseDataIso,
            perfAsync,
            perfSnapshot,
            persistirSelecao,
            prioridadeMesa,
            renderAnexos,
            resumoEsperaHoras,
            rotuloSituacaoMesa,
            sincronizarUrlDaSecao,
            texto,
            textoComQuebras,
            variantStatusLaudo,
            withBusy,
        },
        state,
        storageKeys: {
            mesa: STORAGE_MESA_KEY,
        },
    });

    const {
        aplicarFiltroMesaRapido,
        abrirSecaoMesa,
        atualizarBuscaMesa,
        bindMesaActions,
        cancelarCarregamentoMesa,
        limparFiltroMesaRapido,
        loadMesa,
        renderMesaContext,
        renderMesaList,
        renderMesaMensagens,
        renderMesaMovimentos,
        renderMesaResumo,
        renderMesaResumoGeral,
        renderMesaTriagem,
        resolverSecaoMesaPorTarget,
    } = mesaModule;

    const shell = createRequiredModule("shell", createShell, {
        actions: {
            cancelarCarregamentoMesa,
            limparDocumentoChatPendente,
            loadChat,
            loadMesa,
        },
        documentRef: document,
        getById: $,
        helpers: {
            abrirSecaoAdmin,
            abrirSecaoChat,
            abrirSecaoMesa,
            api,
            construirPrioridadesPortal,
            escapeAttr,
            escapeHtml,
            formatarInteiro,
            lerNumeroPersistido,
            perfAsync,
            perfSnapshot,
            perfSync,
            persistirSelecao,
            renderAdmin,
            renderAvisosOperacionais,
            renderChatCapacidade,
            renderChatContext,
            renderChatList,
            renderChatMensagens,
            renderChatMovimentos,
            renderChatResumo,
            renderChatTriagem,
            renderMesaContext,
            renderMesaList,
            renderMesaMensagens,
            renderMesaMovimentos,
            renderMesaResumo,
            renderMesaResumoGeral,
            renderMesaTriagem,
            resumoCanalOperacional,
        },
        state,
        storageKeys: {
            chat: STORAGE_CHAT_KEY,
            mesa: STORAGE_MESA_KEY,
        },
    });

    ({ atualizarBadgesTabs, bootstrapPortal } = shell);

    const {
        bindCommercialActions,
        bindFiltros,
        bindTabs,
    } = createRequiredModule("bindings", createBindings, {
        actions: {
            aplicarFiltroChatRapido,
            aplicarFiltroMesaRapido,
            aplicarFiltroUsuariosRapido,
            aplicarFiltrosUsuarios,
            abrirSecaoAdmin,
            abrirSecaoChat,
            abrirSecaoMesa,
            atualizarBuscaChat,
            atualizarBuscaMesa,
            bootstrapPortal: (...args) => bootstrapPortal(...args),
            focarUsuarioNaTabela,
            limparFiltroChatRapido,
            limparFiltroMesaRapido,
            limparFiltroUsuariosRapido,
            loadChat,
            loadMesa,
            prepararUpgradeGuiado,
            registrarInteressePlano,
            renderPreviewPlano,
            renderUsuarios,
            resolverSecaoAdminPorTarget,
            resolverSecaoChatPorTarget,
            resolverSecaoMesaPorTarget,
        },
        documentRef: document,
        getById: $,
        helpers: {
            definirTab,
            feedback,
            rotuloSituacaoChat,
            rotuloSituacaoMesa,
            rotuloSituacaoUsuarios,
            scrollToPortalSection,
            texto,
            withBusy,
        },
        state,
    });

    async function init() {
        return perfAsync(
            "cliente.init",
            async () => {
                try {
                    restaurarTab();
                    bindTabs();
                    bindFiltros();
                    bindAdminActions();
                    bindCommercialActions();
                    bindChatActions();
                    bindMesaActions();
                    window.addEventListener("popstate", () => {
                        const tab = tabAtualDaUrl();
                        if (tab) {
                            const secao = secaoAtualDaUrl(tab);
                            registrarSecaoAtiva(tab, secao);
                            definirTab(tab, false, { fromUrl: true, syncUrl: false });
                            bootstrapPortal({ surface: tab, carregarDetalhes: true, force: false })
                                .then(() => {
                                    if (tab === "admin") {
                                        abrirSecaoAdmin(secao, { ensureRendered: true, syncUrl: false });
                                    } else if (tab === "chat") {
                                        abrirSecaoChat(secao, { syncUrl: false });
                                    } else {
                                        abrirSecaoMesa(secao, { syncUrl: false });
                                    }
                                })
                                .catch((erro) => {
                                    feedback(erro.message || "Falha ao sincronizar a superfície do portal.", true);
                                });
                        }
                    });
                    await bootstrapPortal({ surface: state.ui.tab, carregarDetalhes: true, force: true });
                    sincronizarTabComUrl({ replace: true });
                    perfSnapshot("cliente:init");
                    markBootReady();
                } catch (erro) {
                    failBoot(erro, {
                        code: "init-failed",
                        details: {
                            stage: "cliente.init",
                        },
                        rethrow: false,
                    });
                    feedback(erro.message || "Falha ao carregar o portal admin-cliente.", true);
                }
            },
            { tabInicial: state.ui.tab },
            "boot"
        );
    }

    init();
})();
