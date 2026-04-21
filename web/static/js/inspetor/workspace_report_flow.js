(function () {
    "use strict";

    const inspectorRuntime = window.TarielInspectorRuntime || null;
    const modules = typeof inspectorRuntime?.resolveModuleBucket === "function"
        ? inspectorRuntime.resolveModuleBucket("TarielInspetorModules")
        : (window.TarielInspetorModules = window.TarielInspetorModules || {});

    modules.registerWorkspaceReportFlow = function registerWorkspaceReportFlow(ctx) {
        const estado = ctx.state;
        const {
            emitirEventoTariel,
            emitirSincronizacaoLaudo,
            mostrarToast,
            normalizarThreadTab,
            normalizarTipoTemplate,
        } = ctx.shared;

        function limparForcaTelaInicial() {
            ctx.actions.limparForcaTelaInicial?.();
        }

        function definirRetomadaHomePendente(payload = null) {
            ctx.actions.definirRetomadaHomePendente?.(payload);
        }

        function registrarContextoVisualLaudo(laudoId, contextoVisual = null) {
            ctx.actions.registrarContextoVisualLaudo?.(laudoId, contextoVisual);
        }

        function aplicarContextoVisualWorkspace(contextoVisual = null) {
            ctx.actions.aplicarContextoVisualWorkspace?.(contextoVisual);
        }

        function criarContextoVisualPadrao() {
            return ctx.actions.criarContextoVisualPadrao?.() || {
                title: "Assistente Tariel IA",
                subtitle: "Conversa inicial • nenhum laudo ativo",
                statusBadge: "CHAT LIVRE",
            };
        }

        function atualizarEstadoModoEntrada(payload = {}, options = {}) {
            ctx.actions.atualizarEstadoModoEntrada?.(payload, options);
        }

        function sincronizarEstadoInspector(overrides = {}, options = {}) {
            return ctx.actions.sincronizarEstadoInspector?.(overrides, options) || {};
        }

        function exibirInterfaceInspecaoAtiva(tipo) {
            ctx.actions.exibirInterfaceInspecaoAtiva?.(tipo);
        }

        function atualizarThreadWorkspace(tab = "conversa", options = {}) {
            ctx.actions.atualizarThreadWorkspace?.(tab, options);
        }

        function carregarPendenciasMesa(payload = {}) {
            return ctx.actions.carregarPendenciasMesa?.(payload) || Promise.resolve(null);
        }

        function modalNovaInspecaoEstaAberta() {
            return ctx.actions.modalNovaInspecaoEstaAberta?.() === true;
        }

        function fecharNovaInspecaoComScreenSync(options = {}) {
            return ctx.actions.fecharNovaInspecaoComScreenSync?.(options);
        }

        function definirBotaoIniciarCarregando(ativo) {
            ctx.actions.definirBotaoIniciarCarregando?.(ativo);
        }

        function definirBotaoFinalizarCarregando(ativo) {
            ctx.actions.definirBotaoFinalizarCarregando?.(ativo);
        }

        function enriquecerPayloadLaudoComContextoVisual(payload = {}, contextoVisual = null) {
            return ctx.actions.enriquecerPayloadLaudoComContextoVisual?.(payload, contextoVisual) || payload;
        }

        function resolverThreadTabInicialPorModoEntrada(payload = {}, fallback = "historico") {
            return ctx.shared.resolverThreadTabInicialPorModoEntrada?.(payload, fallback)
                || normalizarThreadTab(fallback);
        }

        async function abrirLaudoPeloHome(
            laudoId,
            origem = "home_recent",
            tipoTemplate = "padrao",
            contextoVisual = null,
            threadTabPreferida = "",
            modoEntradaPayload = null
        ) {
            const id = Number(laudoId || 0) || null;
            if (!id) {
                mostrarToast("Nenhum laudo recente disponível para continuar.", "aviso", 2600);
                return false;
            }

            limparForcaTelaInicial();
            const tipoNormalizado = normalizarTipoTemplate(tipoTemplate);
            const payloadModoEntrada = modoEntradaPayload && typeof modoEntradaPayload === "object"
                ? { ...modoEntradaPayload }
                : {};
            const threadTabInicial = String(threadTabPreferida || "").trim()
                ? normalizarThreadTab(threadTabPreferida)
                : resolverThreadTabInicialPorModoEntrada(payloadModoEntrada, "historico");
            definirRetomadaHomePendente({
                laudoId: id,
                tipoTemplate: tipoNormalizado,
                contextoVisual: contextoVisual || null,
                expiresAt: Date.now() + 6000,
            });
            registrarContextoVisualLaudo(id, contextoVisual);
            aplicarContextoVisualWorkspace(contextoVisual || criarContextoVisualPadrao());
            atualizarEstadoModoEntrada(payloadModoEntrada);
            sincronizarEstadoInspector({
                laudoAtualId: id,
                forceHomeLanding: false,
                modoInspecaoUI: "workspace",
                workspaceStage: "inspection",
                threadTab: threadTabInicial,
                overlayOwner: "",
                assistantLandingFirstSendPending: false,
                freeChatConversationActive: false,
            }, {
                persistirStorage: false,
            });

            if (typeof window.TarielChatPainel?.selecionarLaudo === "function") {
                const ok = !!window.TarielChatPainel.selecionarLaudo(id, {
                    atualizarURL: true,
                    origem,
                    threadTab: threadTabInicial,
                    ignorarBloqueioRelatorio: true,
                    ...payloadModoEntrada,
                });
                if (ok) {
                    exibirInterfaceInspecaoAtiva(tipoNormalizado);
                    atualizarThreadWorkspace(threadTabInicial, {
                        persistirURL: true,
                        replaceURL: true,
                    });
                    carregarPendenciasMesa({ laudoId: id, silencioso: true }).catch(() => {});
                }
                return ok;
            }

            try {
                if (typeof window.TarielAPI?.carregarLaudo === "function") {
                    await window.TarielAPI.carregarLaudo(id, {
                        forcar: true,
                        silencioso: true,
                    });
                }

                emitirEventoTariel?.("tariel:laudo-selecionado", {
                    laudoId: id,
                    origem,
                    threadTab: threadTabInicial,
                    ...payloadModoEntrada,
                });
                exibirInterfaceInspecaoAtiva(tipoNormalizado);
                atualizarThreadWorkspace(threadTabInicial, {
                    persistirURL: true,
                    replaceURL: true,
                });
                carregarPendenciasMesa({ laudoId: id, silencioso: true }).catch(() => {});
                return true;
            } catch (erro) {
                mostrarToast("Não foi possível abrir esse laudo agora.", "erro", 2800);
                return false;
            }
        }

        async function iniciarInspecao(
            tipo,
            { contextoVisual = null, dadosFormulario = null, entryModePreference = null, runtimeTipoTemplate = null } = {}
        ) {
            if (estado.iniciandoInspecao) return null;

            const tipoSubmissao = String(tipo || "padrao").trim() || "padrao";
            const tipoNormalizado = normalizarTipoTemplate(runtimeTipoTemplate || tipoSubmissao);
            limparForcaTelaInicial();

            if (!window.TarielAPI?.iniciarRelatorio) {
                mostrarToast("A API do chat ainda não está pronta.", "erro", 3000);
                return null;
            }

            estado.iniciandoInspecao = true;
            definirBotaoIniciarCarregando(true);

            try {
                const respostaBruta = await window.TarielAPI.iniciarRelatorio(tipoSubmissao, {
                    dadosFormulario,
                    entryModePreference,
                });
                const resposta = enriquecerPayloadLaudoComContextoVisual(
                    respostaBruta,
                    contextoVisual
                );

                if (!resposta) {
                    return null;
                }

                if (modalNovaInspecaoEstaAberta()) {
                    fecharNovaInspecaoComScreenSync({ forcar: true, restaurarFoco: false });
                }

                const laudoId = Number(resposta?.laudo_id ?? resposta?.laudoId ?? 0) || null;
                registrarContextoVisualLaudo(laudoId, contextoVisual);
                atualizarEstadoModoEntrada(resposta, { atualizarPadrao: true });
                emitirSincronizacaoLaudo?.(resposta, { selecionar: true });
                const threadTabInicial = resolverThreadTabInicialPorModoEntrada(resposta, "historico");

                definirRetomadaHomePendente({
                    laudoId,
                    tipoTemplate: tipoNormalizado,
                    contextoVisual: contextoVisual || null,
                    expiresAt: Date.now() + 15000,
                });

                if (laudoId) {
                    await abrirLaudoPeloHome(
                        laudoId,
                        "new_inspection",
                        tipoNormalizado,
                        contextoVisual || null,
                        threadTabInicial
                    );
                    return resposta;
                }

                exibirInterfaceInspecaoAtiva(tipoNormalizado);
                return resposta;
            } finally {
                estado.iniciandoInspecao = false;
                definirBotaoIniciarCarregando(false);
            }
        }

        async function finalizarInspecao() {
            if (estado.finalizandoInspecao) return null;

            if (
                window.TarielAPI?.estaRespondendo?.() ||
                document.body?.dataset?.iaRespondendo === "true"
            ) {
                mostrarToast("Aguarde a IA terminar antes de enviar para a mesa.", "aviso", 2600);
                return null;
            }

            const confirmou = window.confirm(
                "Deseja encerrar a coleta? O laudo será gerado e enviado para a mesa avaliadora."
            );

            if (!confirmou) return null;

            estado.finalizandoInspecao = true;
            definirBotaoFinalizarCarregando(true);

            try {
                if (typeof window.finalizarInspecaoCompleta === "function") {
                    return await window.finalizarInspecaoCompleta();
                }

                if (window.TarielAPI?.finalizarRelatorio) {
                    return await window.TarielAPI.finalizarRelatorio({ direto: true });
                }

                mostrarToast("A finalização do relatório não está disponível.", "erro", 3000);
                return null;
            } finally {
                estado.finalizandoInspecao = false;
                definirBotaoFinalizarCarregando(false);
            }
        }

        Object.assign(ctx.actions, {
            abrirLaudoPeloHome,
            finalizarInspecao,
            iniciarInspecao,
        });
    };
})();
