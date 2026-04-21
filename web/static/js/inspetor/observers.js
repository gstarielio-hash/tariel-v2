(function () {
    "use strict";

    const inspectorRuntime = window.TarielInspectorRuntime || null;
    const modules = typeof inspectorRuntime?.resolveModuleBucket === "function"
        ? inspectorRuntime.resolveModuleBucket("TarielInspetorModules")
        : (window.TarielInspetorModules = window.TarielInspetorModules || {});

    modules.registerObservers = function registerObservers(ctx) {
        const el = ctx.elements;

        let observerSidebarHistorico = null;
        let syncSidebarLaudosRaf = 0;
        let observerWorkspace = null;
        let observerWorkspaceRaf = 0;

        function agendarSincronizacaoSidebarLaudos(preferida) {
            if (syncSidebarLaudosRaf) return;

            syncSidebarLaudosRaf = window.requestAnimationFrame(() => {
                syncSidebarLaudosRaf = 0;
                ctx.actions.sincronizarSidebarLaudosTabs?.(preferida);
            });
        }

        function inicializarObservadorSidebarHistorico() {
            if (!el.sidebarHistoricoLista || observerSidebarHistorico) return;

            observerSidebarHistorico = new MutationObserver(() => {
                agendarSincronizacaoSidebarLaudos();
            });
            observerSidebarHistorico.__tarielPerfLabel = "chat_index_page.sidebarHistorico";

            observerSidebarHistorico.observe(el.sidebarHistoricoLista, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ["hidden", "style", "class"],
            });
        }

        function inicializarObservadorWorkspace() {
            const areaMensagens = document.getElementById("area-mensagens");
            if (!areaMensagens || observerWorkspace) return;
            el.areaMensagens = areaMensagens;

            observerWorkspace = new MutationObserver(() => {
                if (observerWorkspaceRaf) {
                    window.cancelAnimationFrame(observerWorkspaceRaf);
                }

                observerWorkspaceRaf = window.requestAnimationFrame(() => {
                    observerWorkspaceRaf = 0;
                    ctx.actions.atualizarPainelWorkspaceDerivado?.();
                    ctx.actions.sincronizarInspectorScreen?.();
                    ctx.actions.promoverPrimeiraMensagemNovoChatSePronta?.();
                });
            });
            observerWorkspace.__tarielPerfLabel = "chat_index_page.workspace";

            observerWorkspace.observe(areaMensagens, {
                childList: true,
                subtree: true,
            });
        }

        function limparObserversInspector() {
            if (syncSidebarLaudosRaf) {
                window.cancelAnimationFrame(syncSidebarLaudosRaf);
                syncSidebarLaudosRaf = 0;
            }
            if (observerWorkspaceRaf) {
                window.cancelAnimationFrame(observerWorkspaceRaf);
                observerWorkspaceRaf = 0;
            }

            observerWorkspace?.disconnect?.();
            observerWorkspace = null;
            observerSidebarHistorico?.disconnect?.();
            observerSidebarHistorico = null;
        }

        Object.assign(ctx.actions, {
            inicializarObservadorSidebarHistorico,
            inicializarObservadorWorkspace,
            limparObserversInspector,
        });
    };
})();
