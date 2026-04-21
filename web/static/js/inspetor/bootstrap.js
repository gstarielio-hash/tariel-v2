(function () {
    "use strict";

    const inspectorRuntime = window.TarielInspectorRuntime || null;
    const modules = typeof inspectorRuntime?.resolveModuleBucket === "function"
        ? inspectorRuntime.resolveModuleBucket("TarielInspetorModules")
        : (window.TarielInspetorModules = window.TarielInspetorModules || {});

    modules.registerBootstrap = function registerBootstrap(ctx) {
        const estado = ctx.state;
        const el = ctx.elements;
        const {
            normalizarLaudoAtualId,
            normalizarEstadoRelatorio,
            estadoRelatorioPossuiContexto,
            fecharSSE,
            limparTimerReconexaoSSE,
        } = ctx.shared;

        async function bootInspector() {
            const {
                atualizarEstadoModoEntrada = () => {},
                selecionarModoEntradaModal = () => "auto_recommended",
                atualizarResumoModoEntradaModal = () => {},
                sincronizarEstadoInspector = () => ({}),
                definirWorkspaceStage = () => {},
                definirModoInspecaoUI = () => {},
                homeForcadoAtivo = () => false,
                atualizarThreadWorkspace = () => {},
                sincronizarVisibilidadeAcoesChatLivre = () => {},
                aplicarMatrizVisibilidadeInspector = () => {},
                filtrarSidebarHistorico = () => {},
                inicializarObservadorSidebarHistorico = () => {},
                renderizarSugestoesComposer = () => {},
                atualizarStatusChatWorkspace = () => {},
                inicializarSelectTemplateCustom = () => {},
                bindEventosModal = () => {},
                bindEventosPagina = () => {},
                bindEventosSistema = () => {},
                atualizarBotoesFiltroPendencias = () => {},
                atualizarBadgeMesaWidget = () => {},
                atualizarConexaoMesaWidget = () => {},
                sincronizarClasseBodyMesaWidget = () => {},
                aplicarHighlightComposer = () => {},
                atualizarVisualComposer = () => {},
                atualizarRecursosComposerWorkspace = () => {},
                sincronizarScrollBackdrop = () => {},
                atualizarPainelWorkspaceDerivado = () => {},
                inicializarObservadorWorkspace = () => {},
                sincronizarInspectorScreen = () => {},
                obterSnapshotEstadoInspectorAtual = () => ({}),
                obterRetomadaHomePendente = () => null,
                obterLaudoIdDaURLInspector = () => null,
                normalizarThreadTab = (valor) => String(valor || "").trim().toLowerCase(),
                aplicarContextoVisualWorkspace = () => {},
                obterContextoVisualLaudoRegistrado = () => null,
                criarContextoVisualPadrao = () => ({}),
                exibirInterfaceInspecaoAtiva = () => {},
                carregarPendenciasMesa = async () => {},
                sincronizarSSEPorContexto = () => {},
                resolverContextoVisualWorkspace = () => ({}),
                registrarContextoVisualLaudo = () => {},
                obterTipoTemplateDoPayload = () => "padrao",
                carregarMensagensMesaWidget = async () => {},
                resetarInterfaceInspecao = () => {},
                restaurarTelaSemRelatorio = () => {},
            } = ctx.actions;

            atualizarEstadoModoEntrada({}, { reset: true, atualizarPadrao: true });
            selecionarModoEntradaModal(estado.entryModePreferenceDefault || "auto_recommended");
            atualizarResumoModoEntradaModal();
            const snapshotInicial = sincronizarEstadoInspector({}, { persistirStorage: false });
            definirWorkspaceStage(snapshotInicial?.workspaceStage || "assistant");
            definirModoInspecaoUI(homeForcadoAtivo() ? "home" : (snapshotInicial?.modoInspecaoUI || "workspace"));
            atualizarThreadWorkspace(
                snapshotInicial?.threadTab ||
                (snapshotInicial?.workspaceStage === "inspection" ? "historico" : "conversa")
            );
            sincronizarVisibilidadeAcoesChatLivre();
            aplicarMatrizVisibilidadeInspector();
            filtrarSidebarHistorico("");
            inicializarObservadorSidebarHistorico();
            renderizarSugestoesComposer();
            atualizarStatusChatWorkspace("pronto", "Assistente pronto");

            if (el.btnMesaWidgetToggle && el.painelMesaWidget) {
                document.body.classList.add("pagina-chat-mesa");
            }

            inicializarSelectTemplateCustom();
            bindEventosModal();
            bindEventosPagina();
            bindEventosSistema();

            atualizarBotoesFiltroPendencias();
            atualizarBadgeMesaWidget();
            atualizarConexaoMesaWidget("conectado");
            sincronizarClasseBodyMesaWidget();
            aplicarHighlightComposer(el.campoMensagem?.value || "");
            atualizarVisualComposer(el.campoMensagem?.value || "");
            atualizarRecursosComposerWorkspace();
            sincronizarScrollBackdrop();
            atualizarPainelWorkspaceDerivado();
            inicializarObservadorWorkspace();

            if (document.documentElement.dataset.inspectorSurfaceMatrixWired !== "true") {
                let syncRaf = 0;
                document.documentElement.dataset.inspectorSurfaceMatrixWired = "true";
                window.addEventListener("resize", () => {
                    if (syncRaf) return;
                    syncRaf = window.requestAnimationFrame(() => {
                        syncRaf = 0;
                        sincronizarInspectorScreen();
                    });
                });
            }

            try {
                const laudoUrlSolicitado = normalizarLaudoAtualId(
                    window.TarielChatPainel?.obterLaudoIdDaURL?.() || obterLaudoIdDaURLInspector() || 0
                );
                const abaUrlSolicitada = normalizarThreadTab(window.TarielChatPainel?.obterThreadTabDaURL?.() || "");
                const dados = await window.TarielAPI?.sincronizarEstadoRelatorio?.();
                const estadoRelatorio = normalizarEstadoRelatorio(dados?.estado);
                const laudoId = Number(dados?.laudo_id ?? dados?.laudoId ?? 0) || null;
                const snapshotAtual = obterSnapshotEstadoInspectorAtual();
                const estadoAtual = normalizarEstadoRelatorio(snapshotAtual?.estadoRelatorio);
                const laudoAtual = normalizarLaudoAtualId(snapshotAtual?.laudoAtualId);
                const laudoIdEfetivo = laudoId || laudoAtual || laudoUrlSolicitado;
                const contextoAutoritativoAtivo = !!laudoIdEfetivo || estadoRelatorioPossuiContexto(estadoRelatorio);

                if (!contextoAutoritativoAtivo && laudoUrlSolicitado && !homeForcadoAtivo()) {
                    const threadTabBoot = abaUrlSolicitada || snapshotAtual?.threadTab || "historico";
                    sincronizarEstadoInspector({
                        laudoAtualId: laudoAtual || laudoUrlSolicitado,
                        modoInspecaoUI: "workspace",
                        workspaceStage: "inspection",
                        threadTab: threadTabBoot,
                        forceHomeLanding: false,
                    });
                    try {
                        await window.TarielAPI?.carregarLaudo?.(laudoUrlSolicitado, {
                            forcar: true,
                            silencioso: true,
                        });
                    } catch (_) {
                        // O bootstrap do workspace continua; a seleção por URL segue responsável
                        // por convergir a interface assim que a API terminar de ficar pronta.
                    }
                    aplicarContextoVisualWorkspace(
                        obterContextoVisualLaudoRegistrado(laudoUrlSolicitado)
                        || criarContextoVisualPadrao()
                    );
                    exibirInterfaceInspecaoAtiva(estado.tipoTemplateAtivo || "padrao");
                    atualizarThreadWorkspace(threadTabBoot, {
                        persistirURL: false,
                        replaceURL: true,
                    });
                    sincronizarInspectorScreen();
                    carregarPendenciasMesa({ laudoId: laudoUrlSolicitado, silencioso: true }).catch(() => {});
                    sincronizarSSEPorContexto();
                    return;
                }

                if (
                    (estadoAtual !== estadoRelatorio || laudoAtual !== laudoIdEfetivo) &&
                    (
                        !!laudoAtual
                        || estadoRelatorioPossuiContexto(estadoAtual)
                        || snapshotAtual?.workspaceStage === "inspection"
                    )
                ) {
                    sincronizarInspectorScreen();
                    sincronizarSSEPorContexto();
                    return;
                }

                sincronizarEstadoInspector({
                    laudoAtualId: laudoIdEfetivo,
                    estadoRelatorio,
                });
                atualizarEstadoModoEntrada(
                    contextoAutoritativoAtivo ? dados : {},
                    { reset: !contextoAutoritativoAtivo }
                );
                const retomadaPendente = obterRetomadaHomePendente();

                if (contextoAutoritativoAtivo) {
                    if (homeForcadoAtivo()) {
                        resetarInterfaceInspecao();
                        return;
                    }
                    const contextoVisualAutoritativo = resolverContextoVisualWorkspace({
                        ...(dados && typeof dados === "object" ? dados : {}),
                        laudo_id: laudoIdEfetivo,
                    });
                    if (laudoIdEfetivo) {
                        registrarContextoVisualLaudo(laudoIdEfetivo, contextoVisualAutoritativo);
                    }
                    aplicarContextoVisualWorkspace(contextoVisualAutoritativo || criarContextoVisualPadrao());
                    exibirInterfaceInspecaoAtiva(obterTipoTemplateDoPayload(dados));
                    if (laudoIdEfetivo) {
                        await carregarPendenciasMesa({ laudoId: laudoIdEfetivo, silencioso: true });
                    }
                    if (estado.mesaWidgetAberto) {
                        await carregarMensagensMesaWidget({ silencioso: true });
                    }
                    sincronizarSSEPorContexto();
                    return;
                }

                if (
                    retomadaPendente &&
                    retomadaPendente.expiresAt > Date.now() &&
                    !homeForcadoAtivo()
                ) {
                    sincronizarEstadoInspector({ forceHomeLanding: false });
                    aplicarContextoVisualWorkspace(retomadaPendente.contextoVisual || criarContextoVisualPadrao());
                    exibirInterfaceInspecaoAtiva(retomadaPendente.tipoTemplate || estado.tipoTemplateAtivo);
                    return;
                }

                if (estadoRelatorio === "sem_relatorio") {
                    restaurarTelaSemRelatorio({ limparTimeline: false });
                    fecharSSE();
                    limparTimerReconexaoSSE();
                }
            } catch (_) {
                // silêncio intencional: a página continua funcional
            }

            sincronizarSSEPorContexto();
        }

        Object.assign(ctx.actions, {
            bootInspector,
        });
    };
})();
