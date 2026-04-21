(function () {
    "use strict";

    const inspectorRuntime = window.TarielInspectorRuntime || null;
    const modules = typeof inspectorRuntime?.resolveModuleBucket === "function"
        ? inspectorRuntime.resolveModuleBucket("TarielInspetorModules")
        : (window.TarielInspetorModules = window.TarielInspetorModules || {});

    modules.registerWorkspaceNavigation = function registerWorkspaceNavigation(ctx) {
        const estado = ctx.state;
        const el = ctx.elements;
        const {
            NOMES_TEMPLATES,
            normalizarContextoVisualSeguro,
            normalizarModoInspecaoUI,
            normalizarWorkspaceStage,
        } = ctx.shared;

        function detailPossuiContextoVisual(detail = {}) {
            return ctx.actions.detailPossuiContextoVisual?.(detail) === true;
        }

        function extrairContextoVisualWorkspace(detail = {}) {
            return ctx.actions.extrairContextoVisualWorkspace?.(detail) || null;
        }

        function obterContextoVisualLaudoRegistrado(laudoId) {
            return ctx.actions.obterContextoVisualLaudoRegistrado?.(laudoId) || null;
        }

        function obterRetomadaHomePendente() {
            return ctx.actions.obterRetomadaHomePendente?.() || null;
        }

        function criarContextoVisualPadrao() {
            return ctx.actions.criarContextoVisualPadrao?.() || {
                title: "Assistente Tariel IA",
                subtitle: "Conversa inicial • nenhum laudo ativo",
                statusBadge: "CHAT LIVRE",
            };
        }

        function sincronizarEstadoInspector(overrides = {}, options = {}) {
            return ctx.actions.sincronizarEstadoInspector?.(overrides, options) || {};
        }

        function atualizarCopyWorkspaceStage(stage = "inspection") {
            ctx.actions.atualizarCopyWorkspaceStage?.(stage);
        }

        function atualizarControlesWorkspaceStage() {
            ctx.actions.atualizarControlesWorkspaceStage?.();
        }

        function aplicarContextoVisualWorkspace(contexto = null) {
            ctx.actions.aplicarContextoVisualWorkspace?.(contexto);
        }

        function obterContextoVisualAssistente() {
            return ctx.actions.obterContextoVisualAssistente?.() || criarContextoVisualPadrao();
        }

        function atualizarPainelWorkspaceDerivado() {
            ctx.actions.atualizarPainelWorkspaceDerivado?.();
        }

        function conversaWorkspaceModoChatAtivo() {
            return ctx.actions.conversaWorkspaceModoChatAtivo?.() === true;
        }

        function obterResumoOperacionalMesa() {
            return ctx.actions.obterResumoOperacionalMesa?.() || {
                status: "pronta",
                titulo: "Mesa disponível",
                descricao: "",
                chipStatus: "",
                chipPendencias: "",
                chipNaoLidas: "",
            };
        }

        function limparFluxoNovoChatFocado() {
            ctx.actions.limparFluxoNovoChatFocado?.();
        }

        function atualizarNomeTemplateAtivo(tipo) {
            ctx.actions.atualizarNomeTemplateAtivo?.(tipo);
        }

        function carregarContextoFixadoWorkspace() {
            ctx.actions.carregarContextoFixadoWorkspace?.();
        }

        function renderizarResumoOperacionalMesa() {
            ctx.actions.renderizarResumoOperacionalMesa?.();
        }

        function renderizarSugestoesComposer() {
            ctx.actions.renderizarSugestoesComposer?.();
        }

        function atualizarStatusChatWorkspace(status = "pronto", texto = "") {
            ctx.actions.atualizarStatusChatWorkspace?.(status, texto);
        }

        function definirRetomadaHomePendente(payload = null) {
            ctx.actions.definirRetomadaHomePendente?.(payload);
        }

        function atualizarEstadoModoEntrada(payload = {}, options = {}) {
            ctx.actions.atualizarEstadoModoEntrada?.(payload, options);
        }

        function resetarFiltrosHistoricoWorkspace() {
            ctx.actions.resetarFiltrosHistoricoWorkspace?.();
        }

        function atualizarThreadWorkspace(tab = "conversa", options = {}) {
            ctx.actions.atualizarThreadWorkspace?.(tab, options);
        }

        function limparPainelPendencias() {
            ctx.actions.limparPainelPendencias?.();
        }

        function fecharSlashCommandPalette() {
            ctx.actions.fecharSlashCommandPalette?.();
        }

        function homeForcadoAtivo() {
            return ctx.actions.homeForcadoAtivo?.() === true;
        }

        function resolverContextoVisualWorkspace(detail = {}) {
            const laudoId = Number(
                detail?.laudo_id ??
                detail?.laudoId ??
                detail?.laudo_card?.id ??
                0
            ) || null;

            if (detailPossuiContextoVisual(detail)) {
                return extrairContextoVisualWorkspace(detail);
            }

            const contextoRegistrado = obterContextoVisualLaudoRegistrado(laudoId);
            if (contextoRegistrado) {
                return contextoRegistrado;
            }

            const retomadaPendente = obterRetomadaHomePendente();
            return (
                normalizarContextoVisualSeguro?.(retomadaPendente?.contextoVisual) ||
                normalizarContextoVisualSeguro?.(estado.workspaceVisualContext) ||
                criarContextoVisualPadrao()
            );
        }

        function definirWorkspaceStage(stage = "assistant") {
            const proximoStage = typeof normalizarWorkspaceStage === "function"
                ? normalizarWorkspaceStage(stage)
                : String(stage || "assistant").trim().toLowerCase() || "assistant";
            sincronizarEstadoInspector({ workspaceStage: proximoStage }, { persistirStorage: false });

            atualizarCopyWorkspaceStage(proximoStage);
            atualizarControlesWorkspaceStage();
        }

        function atualizarContextoWorkspaceAtivo() {
            if (estado.workspaceStage === "assistant") {
                aplicarContextoVisualWorkspace(obterContextoVisualAssistente());
                atualizarCopyWorkspaceStage("assistant");
                atualizarPainelWorkspaceDerivado();
                return;
            }

            if (conversaWorkspaceModoChatAtivo()) {
                aplicarContextoVisualWorkspace();
                atualizarCopyWorkspaceStage("inspection");
                atualizarPainelWorkspaceDerivado();
                return;
            }

            const nomeTemplate = NOMES_TEMPLATES[estado.tipoTemplateAtivo] || NOMES_TEMPLATES.padrao;
            const resumoMesa = obterResumoOperacionalMesa();
            const evidenceFirstAtivo = !!ctx.shared.modoEntradaEvidenceFirstAtivo?.();

            aplicarContextoVisualWorkspace();
            atualizarCopyWorkspaceStage("inspection");
            if (el.rodapeContextoTitulo) {
                el.rodapeContextoTitulo.textContent = evidenceFirstAtivo
                    ? `Registrar evidências primeiro em ${nomeTemplate}`
                    : `Registrar evidências em ${nomeTemplate}`;
            }
            if (el.rodapeContextoStatus) {
                el.rodapeContextoStatus.textContent = evidenceFirstAtivo
                    ? "Comece por anexos, fotos e provas do caso. O chat segue disponível para justificar a coleta."
                    : resumoMesa.descricao;
            }

            atualizarPainelWorkspaceDerivado();
            ctx.shared.atualizarWorkspaceEntryModeNote?.();
        }

        function definirModoInspecaoUI(modo = "home") {
            const proximoModo = typeof normalizarModoInspecaoUI === "function"
                ? normalizarModoInspecaoUI(modo)
                : "home";
            sincronizarEstadoInspector({ modoInspecaoUI: proximoModo }, { persistirStorage: false });
            atualizarControlesWorkspaceStage();

            if (proximoModo !== "workspace") {
                if (estado.mesaWidgetAberto || !el.painelMesaWidget?.hidden) {
                    ctx.actions.fecharMesaWidget?.();
                } else if (el.btnMesaWidgetToggle) {
                    el.btnMesaWidgetToggle.setAttribute("aria-expanded", "false");
                }
                ctx.actions.limparReferenciaMesaWidget?.();
                ctx.actions.limparAnexoMesaWidget?.();
            }

            atualizarContextoWorkspaceAtivo();
        }

        function exibirInterfaceInspecaoAtiva(tipo) {
            limparFluxoNovoChatFocado();
            definirWorkspaceStage("inspection");
            atualizarNomeTemplateAtivo(tipo);
            carregarContextoFixadoWorkspace();
            definirModoInspecaoUI("workspace");
            renderizarResumoOperacionalMesa();
            renderizarSugestoesComposer();

            const statusAtual = estado.chatStatusIA && typeof estado.chatStatusIA === "object"
                ? estado.chatStatusIA
                : { status: "pronto", texto: "Assistente pronto" };
            atualizarStatusChatWorkspace(statusAtual.status, statusAtual.texto);
        }

        function exibirLandingAssistenteIA({ limparTimeline = false } = {}) {
            definirRetomadaHomePendente(null);
            limparFluxoNovoChatFocado();
            atualizarEstadoModoEntrada({}, { reset: true });
            estado.contextoFixado = [];
            estado.chatStatusIA = {
                status: "pronto",
                texto: "Assistente pronto",
            };

            if (limparTimeline) {
                window.TarielAPI?.limparAreaMensagens?.();
            }

            resetarFiltrosHistoricoWorkspace();

            definirWorkspaceStage("assistant");
            aplicarContextoVisualWorkspace(obterContextoVisualAssistente());
            definirModoInspecaoUI("workspace");
            atualizarThreadWorkspace("conversa");
            limparPainelPendencias();
            fecharSlashCommandPalette();
            renderizarResumoOperacionalMesa();
            renderizarSugestoesComposer();
            atualizarStatusChatWorkspace("pronto", "Assistente pronto");
        }

        function restaurarTelaSemRelatorio({ limparTimeline = false } = {}) {
            if (homeForcadoAtivo()) {
                resetarInterfaceInspecao();
                return;
            }

            exibirLandingAssistenteIA({ limparTimeline });
        }

        function resetarInterfaceInspecao() {
            definirRetomadaHomePendente(null);
            limparFluxoNovoChatFocado();
            atualizarEstadoModoEntrada({}, { reset: true });
            estado.contextoFixado = [];
            estado.chatStatusIA = {
                status: "pronto",
                texto: "Assistente pronto",
            };
            resetarFiltrosHistoricoWorkspace();
            definirWorkspaceStage("assistant");
            definirModoInspecaoUI("home");
            atualizarThreadWorkspace("conversa");
            atualizarHistoricoHomeExpandido(false);
            renderizarResumoOperacionalMesa();
            limparPainelPendencias();
            fecharSlashCommandPalette();
            atualizarStatusChatWorkspace("pronto", "Assistente pronto");
        }

        function atualizarHistoricoHomeExpandido(expandir = false) {
            const extras = Array.isArray(el.historicoHomeExtras) ? el.historicoHomeExtras : [];
            const expandido = !!expandir && extras.length > 0;

            extras.forEach((bloco) => {
                if (!bloco) return;
                if (expandido) {
                    bloco.removeAttribute("hidden");
                } else {
                    bloco.setAttribute("hidden", "");
                }
            });

            if (el.btnHomeToggleHistoricoCompleto) {
                el.btnHomeToggleHistoricoCompleto.setAttribute("aria-expanded", expandido ? "true" : "false");
                el.btnHomeToggleHistoricoCompleto.textContent = expandido
                    ? "Mostrar menos"
                    : "Ver todos";
            }
        }

        function rolarParaHistoricoHome({ expandir = false } = {}) {
            if (expandir) {
                atualizarHistoricoHomeExpandido(true);
            }

            if (!el.secaoHomeRecentes) return;

            try {
                el.secaoHomeRecentes.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                });
            } catch (_) {
                el.secaoHomeRecentes.scrollIntoView();
            }
        }

        Object.assign(ctx.actions, {
            atualizarContextoWorkspaceAtivo,
            atualizarHistoricoHomeExpandido,
            definirModoInspecaoUI,
            definirWorkspaceStage,
            exibirInterfaceInspecaoAtiva,
            exibirLandingAssistenteIA,
            resolverContextoVisualWorkspace,
            restaurarTelaSemRelatorio,
            resetarInterfaceInspecao,
            rolarParaHistoricoHome,
        });
    };
})();
