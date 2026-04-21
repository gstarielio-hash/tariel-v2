(function () {
    "use strict";

    const inspectorRuntime = window.TarielInspectorRuntime || null;
    const modules = typeof inspectorRuntime?.resolveModuleBucket === "function"
        ? inspectorRuntime.resolveModuleBucket("TarielInspetorModules")
        : (window.TarielInspetorModules = window.TarielInspetorModules || {});

    modules.registerSystemEvents = function registerSystemEvents(ctx) {
        const estado = ctx.state;
        const {
            ouvirEventoTariel,
            normalizarStatusMesa,
            normalizarEstadoRelatorio,
            normalizarLaudoAtualId,
            estadoRelatorioPossuiContexto,
            cancelarCarregamentoMensagensMesaWidget,
        } = ctx.shared;

        function bindSystemEvents() {
            if (estado.systemEventsBound) return;
            estado.systemEventsBound = true;

            const {
                abrirModalGateQualidade = () => {},
                atualizarBadgeMesaWidget = () => {},
                atualizarEstadoModoEntrada = () => {},
                atualizarPainelWorkspaceDerivado = () => {},
                atualizarThreadWorkspace = () => {},
                aplicarContextoVisualWorkspace = () => {},
                carregarContextoFixadoWorkspace = () => {},
                carregarMensagensMesaWidget = async () => {},
                carregarPendenciasMesa = async () => {},
                criarContextoVisualPadrao = () => ({}),
                definirRetomadaHomePendente = () => {},
                exibirConversaFocadaNovoChat = () => {},
                exibirInterfaceInspecaoAtiva = () => {},
                fecharMesaWidget = () => {},
                fecharModalGateQualidade = () => {},
                fluxoNovoChatFocadoAtivoOuPendente = () => false,
                homeForcadoAtivo = () => false,
                limparAnexoMesaWidget = () => {},
                limparReferenciaMesaWidget = () => {},
                mostrarBannerEngenharia = () => {},
                obterLaudoIdDaURLInspector = () => null,
                obterRetomadaHomePendente = () => null,
                obterSnapshotEstadoInspectorAtual = () => ({}),
                obterTipoTemplateDoPayload = () => "padrao",
                promoverPrimeiraMensagemNovoChatSePronta = () => {},
                registrarContextoVisualLaudo = () => {},
                registrarUltimoPayloadStatusRelatorioWorkspace = () => {},
                renderizarResumoOperacionalMesa = () => {},
                resolverContextoVisualWorkspace = () => ({}),
                restaurarTelaSemRelatorio = () => {},
                sincronizarEstadoInspector = () => {},
                sincronizarResumoHistoricoWorkspace = () => {},
                sincronizarSSEPorContexto = () => {},
                sincronizarSidebarLaudosTabs = () => {},
            } = ctx.actions;

            const onRelatorioIniciado = (event) => {
                const laudoId = Number(event?.detail?.laudoId ?? event?.detail?.laudo_id ?? 0) || null;
                registrarUltimoPayloadStatusRelatorioWorkspace(event?.detail || null);
                atualizarEstadoModoEntrada(event?.detail || {});
                sincronizarEstadoInspector({
                    laudoAtualId: laudoId,
                    estadoRelatorio: event?.detail?.estado_normalizado ?? event?.detail?.estado ?? "relatorio_ativo",
                    forceHomeLanding: false,
                    modoInspecaoUI: "workspace",
                    workspaceStage: "inspection",
                });
                aplicarContextoVisualWorkspace(resolverContextoVisualWorkspace(event?.detail || {}));
                carregarContextoFixadoWorkspace();
                if (fluxoNovoChatFocadoAtivoOuPendente()) {
                    exibirConversaFocadaNovoChat({
                        tipoTemplate: obterTipoTemplateDoPayload(event?.detail || {}),
                    });
                } else {
                    exibirInterfaceInspecaoAtiva(
                        obterTipoTemplateDoPayload(event?.detail || {})
                    );
                }
                carregarPendenciasMesa({ laudoId, silencioso: true }).catch(() => {});
                cancelarCarregamentoMensagensMesaWidget();
                estado.mesaWidgetMensagens = [];
                estado.mesaWidgetCursor = null;
                estado.mesaWidgetTemMais = false;
                estado.mesaWidgetNaoLidas = 0;
                limparAnexoMesaWidget();
                atualizarBadgeMesaWidget();
                if (estado.mesaWidgetAberto) {
                    carregarMensagensMesaWidget({ laudoId, silencioso: true }).catch(() => {});
                }
                sincronizarSSEPorContexto();
            };

            const onRelatorioFinalizado = (event) => {
                const laudoId = Number(event?.detail?.laudoId ?? event?.detail?.laudo_id ?? 0) || null;
                registrarUltimoPayloadStatusRelatorioWorkspace(event?.detail || null);
                atualizarEstadoModoEntrada(event?.detail || {});
                sincronizarEstadoInspector({
                    laudoAtualId: laudoId,
                    estadoRelatorio: event?.detail?.estado_normalizado ?? event?.detail?.estado ?? "aguardando",
                    modoInspecaoUI: "workspace",
                    workspaceStage: "inspection",
                });
                fecharModalGateQualidade();
                aplicarContextoVisualWorkspace(resolverContextoVisualWorkspace(event?.detail || {}));
                carregarContextoFixadoWorkspace();
                if (fluxoNovoChatFocadoAtivoOuPendente()) {
                    exibirConversaFocadaNovoChat({
                        tipoTemplate: obterTipoTemplateDoPayload(event?.detail || {}),
                    });
                } else {
                    exibirInterfaceInspecaoAtiva(obterTipoTemplateDoPayload(event?.detail || {}));
                }
                carregarPendenciasMesa({ laudoId, silencioso: true }).catch(() => {});
                if (estado.mesaWidgetAberto) {
                    carregarMensagensMesaWidget({ laudoId, silencioso: true }).catch(() => {});
                }
                sincronizarSSEPorContexto();
            };

            const onRelatorioCancelado = () => {
                registrarUltimoPayloadStatusRelatorioWorkspace(null);
                atualizarEstadoModoEntrada({}, { reset: true });
                sincronizarEstadoInspector({
                    laudoAtualId: null,
                    estadoRelatorio: "sem_relatorio",
                });
                fecharModalGateQualidade();
                cancelarCarregamentoMensagensMesaWidget();
                restaurarTelaSemRelatorio({ limparTimeline: true });
                estado.mesaWidgetMensagens = [];
                estado.mesaWidgetCursor = null;
                estado.mesaWidgetTemMais = false;
                estado.mesaWidgetNaoLidas = 0;
                limparAnexoMesaWidget();
                atualizarBadgeMesaWidget();
                limparReferenciaMesaWidget();
                fecharMesaWidget();
            };

            const onMesaAtivada = () => {
                renderizarResumoOperacionalMesa();
            };

            const onMesaStatus = (event) => {
                const status = normalizarStatusMesa(event?.detail?.status);
                const preview = String(event?.detail?.preview || "").trim();
                if (status === "respondeu" && preview) {
                    mostrarBannerEngenharia(preview);
                } else {
                    renderizarResumoOperacionalMesa();
                }

                if (status === "respondeu" || status === "aguardando") {
                    carregarPendenciasMesa({ silencioso: true }).catch(() => {});
                    if (estado.mesaWidgetAberto) {
                        carregarMensagensMesaWidget({ silencioso: true }).catch(() => {});
                    }
                }
            };

            const onLaudoSelecionado = (event) => {
                const laudoId = Number(event?.detail?.laudoId ?? event?.detail?.laudo_id ?? 0) || null;
                if (!laudoId) return;
                registrarUltimoPayloadStatusRelatorioWorkspace(event?.detail || null);
                atualizarEstadoModoEntrada(event?.detail || {});
                sincronizarEstadoInspector({
                    laudoAtualId: laudoId,
                    forceHomeLanding: false,
                });
                carregarContextoFixadoWorkspace();
                if (fluxoNovoChatFocadoAtivoOuPendente()) {
                    aplicarContextoVisualWorkspace(resolverContextoVisualWorkspace(event?.detail || {}));
                    exibirConversaFocadaNovoChat({
                        tipoTemplate: obterTipoTemplateDoPayload(event?.detail || {}),
                    });
                }
                const retomadaPendente = obterRetomadaHomePendente();
                if (
                    !fluxoNovoChatFocadoAtivoOuPendente() &&
                    retomadaPendente &&
                    retomadaPendente.expiresAt > Date.now() &&
                    (!retomadaPendente.laudoId || retomadaPendente.laudoId === laudoId)
                ) {
                    aplicarContextoVisualWorkspace(
                        retomadaPendente.contextoVisual || resolverContextoVisualWorkspace(event?.detail || {})
                    );
                    exibirInterfaceInspecaoAtiva(
                        retomadaPendente.tipoTemplate || obterTipoTemplateDoPayload(event?.detail || {})
                    );
                }
                carregarPendenciasMesa({ laudoId, silencioso: true }).catch(() => {});
                cancelarCarregamentoMensagensMesaWidget();
                estado.mesaWidgetMensagens = [];
                estado.mesaWidgetCursor = null;
                estado.mesaWidgetTemMais = false;
                estado.mesaWidgetNaoLidas = 0;
                atualizarBadgeMesaWidget();
                if (estado.mesaWidgetAberto) {
                    carregarMensagensMesaWidget({ laudoId, silencioso: true }).catch(() => {});
                }
                sincronizarSSEPorContexto();
            };

            const onEstadoRelatorio = (event) => {
                const detail = event?.detail || {};
                registrarUltimoPayloadStatusRelatorioWorkspace(detail);
                const estadoRelatorio = normalizarEstadoRelatorio(detail.estado);
                const laudoId = Number(detail?.laudo_id ?? detail?.laudoId ?? 0) || null;
                const snapshotAtual = obterSnapshotEstadoInspectorAtual();
                const laudoIdEfetivo =
                    laudoId ||
                    normalizarLaudoAtualId(snapshotAtual?.laudoAtualId) ||
                    obterLaudoIdDaURLInspector();
                const contextoAutoritativoAtivo =
                    !!laudoIdEfetivo || estadoRelatorioPossuiContexto(estadoRelatorio);
                atualizarEstadoModoEntrada(
                    contextoAutoritativoAtivo ? detail : {},
                    { reset: !contextoAutoritativoAtivo }
                );
                sincronizarEstadoInspector({
                    laudoAtualId: laudoIdEfetivo,
                    estadoRelatorio,
                });
                const retomadaPendente = obterRetomadaHomePendente();
                const retomadaAtiva =
                    !!retomadaPendente &&
                    retomadaPendente.expiresAt > Date.now() &&
                    (
                        !retomadaPendente.laudoId ||
                        !laudoIdEfetivo ||
                        retomadaPendente.laudoId === laudoIdEfetivo
                    );

                if (homeForcadoAtivo() && estadoRelatorio !== "sem_relatorio") {
                    return;
                }

                if (contextoAutoritativoAtivo) {
                    definirRetomadaHomePendente(null);
                    const contextoVisualAutoritativo = resolverContextoVisualWorkspace({
                        ...(detail && typeof detail === "object" ? detail : {}),
                        laudo_id: laudoIdEfetivo,
                    });
                    if (laudoIdEfetivo) {
                        registrarContextoVisualLaudo(laudoIdEfetivo, contextoVisualAutoritativo);
                    }
                    aplicarContextoVisualWorkspace(contextoVisualAutoritativo);
                    carregarContextoFixadoWorkspace();
                    if (fluxoNovoChatFocadoAtivoOuPendente()) {
                        exibirConversaFocadaNovoChat({
                            tipoTemplate: obterTipoTemplateDoPayload(detail),
                        });
                    } else {
                        exibirInterfaceInspecaoAtiva(obterTipoTemplateDoPayload(detail));
                    }
                    carregarPendenciasMesa({ laudoId: laudoIdEfetivo, silencioso: true }).catch(() => {});
                    sincronizarSSEPorContexto();
                    return;
                }

                if (retomadaAtiva) {
                    sincronizarEstadoInspector({ forceHomeLanding: false });
                    aplicarContextoVisualWorkspace(retomadaPendente.contextoVisual || criarContextoVisualPadrao());
                    exibirInterfaceInspecaoAtiva(retomadaPendente.tipoTemplate || estado.tipoTemplateAtivo);
                    return;
                }

                definirRetomadaHomePendente(null);
                restaurarTelaSemRelatorio({ limparTimeline: true });
            };

            const onGateQualidadeFalhou = (event) => {
                abrirModalGateQualidade(event?.detail || {});
            };

            const onHistoricoLaudoRenderizado = (event) => {
                const detail = event?.detail || {};
                estado.historyCanonicalItems = Array.isArray(detail.itens)
                    ? detail.itens.map((item) => ({ ...item }))
                    : [];
                sincronizarResumoHistoricoWorkspace(detail);
                atualizarPainelWorkspaceDerivado();
                sincronizarSidebarLaudosTabs();
                promoverPrimeiraMensagemNovoChatSePronta();
            };

            const onThreadTabAlterada = (event) => {
                atualizarThreadWorkspace(event?.detail?.tab || "conversa", {
                    persistirURL: event?.detail?.persistirURL === true,
                    replaceURL: event?.detail?.replaceURL === true,
                });
            };

            ouvirEventoTariel("tariel:relatorio-iniciado", onRelatorioIniciado);
            ouvirEventoTariel("tariel:relatorio-finalizado", onRelatorioFinalizado);
            ouvirEventoTariel("tariel:cancelar-relatorio", onRelatorioCancelado);
            ouvirEventoTariel("tariel:mesa-avaliadora-ativada", onMesaAtivada);
            ouvirEventoTariel("tariel:mesa-status", onMesaStatus);
            ouvirEventoTariel("tariel:laudo-selecionado", onLaudoSelecionado);
            ouvirEventoTariel("tariel:estado-relatorio", onEstadoRelatorio);
            ouvirEventoTariel("tariel:gate-qualidade-falhou", onGateQualidadeFalhou);
            ouvirEventoTariel("tariel:historico-laudo-renderizado", onHistoricoLaudoRenderizado);
            ouvirEventoTariel("tariel:thread-tab-alterada", onThreadTabAlterada);
        }

        Object.assign(ctx.actions, {
            bindSystemEvents,
        });
    };
})();
