(function () {
    "use strict";

    if (window.TarielClientePortalBindings) return;

    window.TarielClientePortalBindings = function createTarielClientePortalBindings(config = {}) {
        const state = config.state || {};
        const documentRef = config.documentRef || document;
        const $ = typeof config.getById === "function"
            ? config.getById
            : (id) => documentRef.getElementById(id);
        const actions = config.actions || {};
        const helpers = config.helpers || {};

        const aplicarFiltroChatRapido = typeof actions.aplicarFiltroChatRapido === "function" ? actions.aplicarFiltroChatRapido : () => null;
        const aplicarFiltroMesaRapido = typeof actions.aplicarFiltroMesaRapido === "function" ? actions.aplicarFiltroMesaRapido : () => null;
        const aplicarFiltroUsuariosRapido = typeof actions.aplicarFiltroUsuariosRapido === "function" ? actions.aplicarFiltroUsuariosRapido : () => null;
        const aplicarFiltrosUsuarios = typeof actions.aplicarFiltrosUsuarios === "function" ? actions.aplicarFiltrosUsuarios : () => null;
        const abrirSecaoAdmin = typeof actions.abrirSecaoAdmin === "function" ? actions.abrirSecaoAdmin : () => "overview";
        const abrirSecaoChat = typeof actions.abrirSecaoChat === "function" ? actions.abrirSecaoChat : () => "overview";
        const abrirSecaoMesa = typeof actions.abrirSecaoMesa === "function" ? actions.abrirSecaoMesa : () => "overview";
        const atualizarBuscaChat = typeof actions.atualizarBuscaChat === "function" ? actions.atualizarBuscaChat : () => null;
        const atualizarBuscaMesa = typeof actions.atualizarBuscaMesa === "function" ? actions.atualizarBuscaMesa : () => null;
        const bootstrapPortal = typeof actions.bootstrapPortal === "function" ? actions.bootstrapPortal : async () => null;
        const focarUsuarioNaTabela = typeof actions.focarUsuarioNaTabela === "function" ? actions.focarUsuarioNaTabela : () => null;
        const limparFiltroChatRapido = typeof actions.limparFiltroChatRapido === "function" ? actions.limparFiltroChatRapido : () => null;
        const limparFiltroMesaRapido = typeof actions.limparFiltroMesaRapido === "function" ? actions.limparFiltroMesaRapido : () => null;
        const limparFiltroUsuariosRapido = typeof actions.limparFiltroUsuariosRapido === "function" ? actions.limparFiltroUsuariosRapido : () => null;
        const loadChat = typeof actions.loadChat === "function" ? actions.loadChat : async () => null;
        const loadMesa = typeof actions.loadMesa === "function" ? actions.loadMesa : async () => null;
        const prepararUpgradeGuiado = typeof actions.prepararUpgradeGuiado === "function" ? actions.prepararUpgradeGuiado : async () => null;
        const registrarInteressePlano = typeof actions.registrarInteressePlano === "function" ? actions.registrarInteressePlano : async () => null;
        const renderPreviewPlano = typeof actions.renderPreviewPlano === "function" ? actions.renderPreviewPlano : () => null;
        const renderUsuarios = typeof actions.renderUsuarios === "function" ? actions.renderUsuarios : () => null;
        const resolverSecaoAdminPorTarget = typeof actions.resolverSecaoAdminPorTarget === "function" ? actions.resolverSecaoAdminPorTarget : () => null;
        const resolverSecaoChatPorTarget = typeof actions.resolverSecaoChatPorTarget === "function" ? actions.resolverSecaoChatPorTarget : () => null;
        const resolverSecaoMesaPorTarget = typeof actions.resolverSecaoMesaPorTarget === "function" ? actions.resolverSecaoMesaPorTarget : () => null;

        const definirTab = typeof helpers.definirTab === "function" ? helpers.definirTab : () => null;
        const feedback = typeof helpers.feedback === "function" ? helpers.feedback : () => null;
        const rotuloSituacaoChat = typeof helpers.rotuloSituacaoChat === "function" ? helpers.rotuloSituacaoChat : (valor) => String(valor ?? "");
        const rotuloSituacaoMesa = typeof helpers.rotuloSituacaoMesa === "function" ? helpers.rotuloSituacaoMesa : (valor) => String(valor ?? "");
        const rotuloSituacaoUsuarios = typeof helpers.rotuloSituacaoUsuarios === "function" ? helpers.rotuloSituacaoUsuarios : (valor) => String(valor ?? "");
        const scrollToPortalSection = typeof helpers.scrollToPortalSection === "function" ? helpers.scrollToPortalSection : () => null;
        const texto = typeof helpers.texto === "function" ? helpers.texto : (valor) => (valor == null ? "" : String(valor));
        const withBusy = typeof helpers.withBusy === "function" ? helpers.withBusy : async (_elemento, _label, callback) => callback();

        function deveUsarNavegacaoNativa(event) {
            return Boolean(
                event.defaultPrevented ||
                event.button !== 0 ||
                event.metaKey ||
                event.ctrlKey ||
                event.shiftKey ||
                event.altKey
            );
        }

        function bindArrowNavigation(selector) {
            documentRef.querySelectorAll(selector).forEach((button) => {
                button.addEventListener("keydown", (event) => {
                    const key = event.key;
                    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(key)) {
                        return;
                    }

                    const grupo = Array.from(button.parentElement?.querySelectorAll(selector) || []);
                    if (grupo.length <= 1) return;

                    event.preventDefault();
                    const indiceAtual = Math.max(grupo.indexOf(button), 0);
                    let proximoIndice = indiceAtual;

                    if (key === "Home") {
                        proximoIndice = 0;
                    } else if (key === "End") {
                        proximoIndice = grupo.length - 1;
                    } else if (key === "ArrowLeft" || key === "ArrowUp") {
                        proximoIndice = (indiceAtual - 1 + grupo.length) % grupo.length;
                    } else if (key === "ArrowRight" || key === "ArrowDown") {
                        proximoIndice = (indiceAtual + 1) % grupo.length;
                    }

                    const destino = grupo[proximoIndice];
                    if (!destino || destino === button) return;
                    destino.focus();
                    destino.click();
                });
            });
        }

        function bindTabs() {
            documentRef.querySelectorAll(".cliente-tab").forEach((link) => {
                link.addEventListener("click", async (event) => {
                    if (deveUsarNavegacaoNativa(event)) {
                        return;
                    }
                    event.preventDefault();
                    const tab = link.dataset.tab || "admin";
                    definirTab(tab);
                    await bootstrapPortal({ surface: tab, carregarDetalhes: true, force: false }).catch((erro) => {
                        feedback(erro.message || "Falha ao carregar a superfície do portal.", true);
                    });
                    scrollToPortalSection(`panel-${tab}`);
                });
            });

            documentRef.querySelectorAll("[data-chat-section-tab]").forEach((button) => {
                button.addEventListener("click", (event) => {
                    if (deveUsarNavegacaoNativa(event)) {
                        return;
                    }
                    event.preventDefault();
                    abrirSecaoChat(button.dataset.chatSectionTab, { focusTab: true });
                });
            });

            documentRef.querySelectorAll("[data-admin-section-tab]").forEach((button) => {
                button.addEventListener("click", (event) => {
                    if (deveUsarNavegacaoNativa(event)) {
                        return;
                    }
                    event.preventDefault();
                    const section = button.dataset.adminSectionTab || "overview";
                    abrirSecaoAdmin(section, { focusTab: true });
                    const alvoPorSecao = {
                        overview: "admin-overview",
                        capacity: "admin-capacity",
                        team: "admin-team",
                        support: "admin-support",
                    };
                    scrollToPortalSection(alvoPorSecao[section] || "panel-admin");
                });
            });

            documentRef.querySelectorAll("[data-mesa-section-tab]").forEach((button) => {
                button.addEventListener("click", (event) => {
                    if (deveUsarNavegacaoNativa(event)) {
                        return;
                    }
                    event.preventDefault();
                    abrirSecaoMesa(button.dataset.mesaSectionTab, { focusTab: true });
                });
            });

            bindArrowNavigation(".cliente-tab");
            bindArrowNavigation("[data-admin-section-tab]");
            bindArrowNavigation("[data-chat-section-tab]");
            bindArrowNavigation("[data-mesa-section-tab]");
        }

        function bindFiltros() {
            $("usuarios-busca")?.addEventListener("input", (event) => {
                state.ui.usuariosBusca = event.target.value || "";
                state.ui.usuariosSituacao = "";
                state.ui.usuarioEmDestaque = null;
                renderUsuarios();
            });

            $("usuarios-filtro-papel")?.addEventListener("change", (event) => {
                state.ui.usuariosPapel = event.target.value || "todos";
                state.ui.usuariosSituacao = "";
                state.ui.usuarioEmDestaque = null;
                renderUsuarios();
            });

            $("chat-busca-laudos")?.addEventListener("input", (event) => {
                atualizarBuscaChat(event.target.value || "");
            });

            $("mesa-busca-laudos")?.addEventListener("input", (event) => {
                atualizarBuscaMesa(event.target.value || "");
            });
        }

        async function handleAbrirPrioridade(button) {
            const kind = button.dataset.kind || "admin-section";
            if (kind === "upgrade") {
                await prepararUpgradeGuiado({
                    origem: button.dataset.origem || "admin",
                    button,
                });
                return;
            }

            if (kind === "chat-laudo") {
                definirTab("chat");
                await bootstrapPortal({ surface: "chat", carregarDetalhes: false, force: false }).catch((erro) => {
                    feedback(erro.message || "Falha ao preparar a superfície do chat.", true);
                });
                abrirSecaoChat("case");
                await loadChat(button.dataset.laudo, { silencioso: true }).catch((erro) => feedback(erro.message || "Falha ao abrir prioridade do chat.", true));
                scrollToPortalSection(button.dataset.target || "chat-contexto");
                return;
            }

            if (kind === "chat-section") {
                definirTab("chat");
                await bootstrapPortal({ surface: "chat", carregarDetalhes: true, force: false }).catch((erro) => {
                    feedback(erro.message || "Falha ao preparar a superfície do chat.", true);
                });
                abrirSecaoChat(resolverSecaoChatPorTarget(button.dataset.target || "") || "overview");
                scrollToPortalSection(button.dataset.target || "chat-overview");
                return;
            }

            if (kind === "mesa-laudo") {
                definirTab("mesa");
                await bootstrapPortal({ surface: "mesa", carregarDetalhes: false, force: false }).catch((erro) => {
                    feedback(erro.message || "Falha ao preparar a superfície da mesa.", true);
                });
                abrirSecaoMesa("reply");
                await loadMesa(button.dataset.laudo, { silencioso: true }).catch((erro) => feedback(erro.message || "Falha ao abrir prioridade da mesa.", true));
                scrollToPortalSection(button.dataset.target || "mesa-contexto");
                return;
            }

            if (kind === "mesa-section") {
                definirTab("mesa");
                await bootstrapPortal({ surface: "mesa", carregarDetalhes: true, force: false }).catch((erro) => {
                    feedback(erro.message || "Falha ao preparar a superfície da mesa.", true);
                });
                abrirSecaoMesa(resolverSecaoMesaPorTarget(button.dataset.target || "") || "overview");
                scrollToPortalSection(button.dataset.target || "mesa-overview");
                return;
            }

            definirTab("admin");
            await bootstrapPortal({ surface: "admin", carregarDetalhes: false, force: false }).catch((erro) => {
                feedback(erro.message || "Falha ao preparar a superfície administrativa.", true);
            });
            const secaoAdmin = kind === "admin-user"
                ? "team"
                : resolverSecaoAdminPorTarget(button.dataset.target || "") || "overview";
            abrirSecaoAdmin(secaoAdmin, { ensureRendered: true });
            if (kind === "admin-user") {
                aplicarFiltrosUsuarios({
                    busca: button.dataset.busca || "",
                    papel: button.dataset.papel || "todos",
                    userId: button.dataset.user || null,
                });
                scrollToPortalSection(button.dataset.target || "lista-usuarios");
                focarUsuarioNaTabela(button.dataset.user, { expandir: true });
                return;
            }

            scrollToPortalSection(button.dataset.target || "panel-admin");
        }

        function handleFiltrarUsuariosStatus(button) {
            const situacao = texto(button.dataset.situacao).trim();
            definirTab("admin");
            abrirSecaoAdmin("team", { ensureRendered: true });
            aplicarFiltroUsuariosRapido(situacao);
            scrollToPortalSection("lista-usuarios");
            feedback(`Equipe filtrada por ${rotuloSituacaoUsuarios(situacao).toLowerCase() || "situacao"}.`);
        }

        function handleLimparFiltroUsuarios() {
            definirTab("admin");
            abrirSecaoAdmin("team", { ensureRendered: true });
            limparFiltroUsuariosRapido();
            scrollToPortalSection("lista-usuarios");
            feedback("Filtro rapido da equipe limpo.");
        }

        function handleFiltrarChatStatus(button) {
            const situacao = texto(button.dataset.situacao).trim();
            definirTab("chat");
            abrirSecaoChat("queue");
            aplicarFiltroChatRapido(situacao);
            scrollToPortalSection("lista-chat-laudos");
            feedback(`Chat filtrado por ${rotuloSituacaoChat(situacao).toLowerCase() || "status"}.`);
        }

        function handleLimparFiltroChat() {
            definirTab("chat");
            abrirSecaoChat("queue");
            limparFiltroChatRapido();
            scrollToPortalSection("lista-chat-laudos");
            feedback("Filtro rapido do chat limpo.");
        }

        function handleFiltrarMesaStatus(button) {
            definirTab("mesa");
            abrirSecaoMesa("queue");
            aplicarFiltroMesaRapido(button.dataset.situacao);
            scrollToPortalSection("lista-mesa-laudos");
            feedback(`Mesa filtrada por ${rotuloSituacaoMesa(state.ui.mesaSituacao).toLowerCase() || "status"}.`);
        }

        function handleLimparFiltroMesa() {
            definirTab("mesa");
            abrirSecaoMesa("queue");
            limparFiltroMesaRapido();
            scrollToPortalSection("lista-mesa-laudos");
            feedback("Filtro rapido da mesa limpo.");
        }

        async function handlePrepararUpgrade(button) {
            await prepararUpgradeGuiado({
                origem: button.dataset.origem || "admin",
                button,
            });
        }

        async function handleRegistrarInteressePlano(button) {
            const plano = button.dataset.plano || "";
            const origem = button.dataset.origem || "admin";
            await withBusy(button, "Registrando...", async () => {
                await registrarInteressePlano(plano, origem);
                await bootstrapPortal({ surface: state.ui?.tab || origem || "admin", force: true });
                const seletor = $("empresa-plano");
                if (seletor && plano) {
                    seletor.value = plano;
                }
                renderPreviewPlano();
                feedback(`Interesse em ${plano} registrado no historico do portal.`, false, "Interesse salvo");
            }).catch((erro) => feedback(erro.message || "Falha ao registrar interesse no plano.", true));
        }

        const actionHandlers = {
            "abrir-prioridade": handleAbrirPrioridade,
            "filtrar-usuarios-status": handleFiltrarUsuariosStatus,
            "limpar-filtro-usuarios": handleLimparFiltroUsuarios,
            "filtrar-chat-status": handleFiltrarChatStatus,
            "limpar-chat-filtro": handleLimparFiltroChat,
            "filtrar-mesa-status": handleFiltrarMesaStatus,
            "limpar-mesa-filtro": handleLimparFiltroMesa,
            "preparar-upgrade": handlePrepararUpgrade,
            "registrar-interesse-plano": handleRegistrarInteressePlano,
        };

        async function dispatchCrossSliceAction(button) {
            const action = button?.dataset?.act || "";
            const handler = actionHandlers[action];
            if (!handler) return;
            await handler(button);
        }

        function bindCrossSliceRouter() {
            documentRef.addEventListener("click", async (event) => {
                const button = event.target?.closest?.("button[data-act]");
                if (!button) return;
                await dispatchCrossSliceAction(button);
            });
        }

        const bindCommercialActions = bindCrossSliceRouter;

        return {
            bindCommercialActions,
            bindCrossSliceRouter,
            bindFiltros,
            bindTabs,
        };
    };
})();
