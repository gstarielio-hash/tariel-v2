(function () {
    "use strict";

    if (window.TarielClienteMesaPage) return;

    window.TarielClienteMesaPage = function createTarielClienteMesaPage(config = {}) {
        const state = config.state || {};
        const documentRef = config.documentRef || document;
        const $ = typeof config.getById === "function"
            ? config.getById
            : (id) => documentRef.getElementById(id);
        const helpers = config.helpers || {};
        const actions = config.actions || {};
        const storageKeys = config.storageKeys || {};
        const surfaceModule = config.surfaceModule || {};

        const api = typeof helpers.api === "function" ? helpers.api : async () => null;
        const ehAbortError = typeof helpers.ehAbortError === "function" ? helpers.ehAbortError : () => false;
        const feedback = typeof helpers.feedback === "function" ? helpers.feedback : () => null;
        const perfAsync = typeof helpers.perfAsync === "function" ? helpers.perfAsync : async (_nome, callback) => callback();
        const perfSnapshot = typeof helpers.perfSnapshot === "function" ? helpers.perfSnapshot : () => null;
        const persistirSelecao = typeof helpers.persistirSelecao === "function" ? helpers.persistirSelecao : () => null;
        const texto = typeof helpers.texto === "function" ? helpers.texto : (valor) => (valor == null ? "" : String(valor));
        const withBusy = typeof helpers.withBusy === "function" ? helpers.withBusy : async (_target, _busyText, callback) => callback();

        const atualizarBadgesTabs = typeof actions.atualizarBadgesTabs === "function" ? actions.atualizarBadgesTabs : () => null;
        const bootstrapPortal = typeof actions.bootstrapPortal === "function" ? actions.bootstrapPortal : async () => null;
        const storageMesaKey = storageKeys.mesa || "tariel.cliente.mesa.laudo";

        const abrirSecaoMesa = typeof surfaceModule.abrirSecaoMesa === "function" ? surfaceModule.abrirSecaoMesa : () => "overview";
        const laudoHasSurfaceAction = typeof surfaceModule.laudoHasSurfaceAction === "function" ? surfaceModule.laudoHasSurfaceAction : () => false;
        const obterLaudoMesaPorId = typeof surfaceModule.obterLaudoMesaPorId === "function" ? surfaceModule.obterLaudoMesaPorId : () => null;
        const resolverSecaoMesaPorTarget = typeof surfaceModule.resolverSecaoMesaPorTarget === "function" ? surfaceModule.resolverSecaoMesaPorTarget : () => null;
        const renderMesaContext = typeof surfaceModule.renderMesaContext === "function" ? surfaceModule.renderMesaContext : () => null;
        const renderMesaList = typeof surfaceModule.renderMesaList === "function" ? surfaceModule.renderMesaList : () => null;
        const renderMesaMensagens = typeof surfaceModule.renderMesaMensagens === "function" ? surfaceModule.renderMesaMensagens : () => null;
        const renderMesaMovimentos = typeof surfaceModule.renderMesaMovimentos === "function" ? surfaceModule.renderMesaMovimentos : () => null;
        const renderMesaResumo = typeof surfaceModule.renderMesaResumo === "function" ? surfaceModule.renderMesaResumo : () => null;
        const renderMesaResumoGeral = typeof surfaceModule.renderMesaResumoGeral === "function" ? surfaceModule.renderMesaResumoGeral : () => null;
        const renderMesaTriagem = typeof surfaceModule.renderMesaTriagem === "function" ? surfaceModule.renderMesaTriagem : () => null;

        function mesaCaseActionsEnabled() {
            return Boolean(
                state.bootstrap?.tenant_admin_projection?.payload?.visibility_policy?.case_actions_enabled
            );
        }

        function cancelarCarregamentoMesa() {
            if (!state.mesa?.loadController) return;
            state.mesa.loadController.abort();
            state.mesa.loadController = null;
        }

        async function loadMesa(laudoId, { silencioso = false, force = false } = {}) {
            return perfAsync(
                "cliente.loadMesa",
                async () => {
                    const id = Number(laudoId || 0);
                    if (!Number.isFinite(id) || id <= 0) return null;

                    cancelarCarregamentoMesa();
                    if (!force && Number(state.mesa.loadedLaudoId || 0) === id && state.mesa.pacote) {
                        state.mesa.laudoId = id;
                        persistirSelecao(storageMesaKey, id);
                        renderMesaResumoGeral();
                        renderMesaList();
                        renderMesaContext();
                        renderMesaMensagens();
                        renderMesaResumo();
                        return {
                            mensagens: { itens: state.mesa.mensagens || [] },
                            pacote: state.mesa.pacote,
                        };
                    }

                    const controller = new AbortController();
                    state.mesa.loadController = controller;
                    state.mesa.laudoId = id;
                    state.mesa.loadedLaudoId = null;
                    persistirSelecao(storageMesaKey, id);
                    renderMesaResumoGeral();
                    renderMesaList();
                    renderMesaContext();
                    state.mesa.mensagens = [];
                    state.mesa.pacote = null;
                    renderMesaMensagens();
                    renderMesaResumo();

                    try {
                        const [mensagens, pacote] = await Promise.all([
                            api(`/cliente/api/mesa/laudos/${id}/mensagens`, { signal: controller.signal }),
                            api(`/cliente/api/mesa/laudos/${id}/pacote`, { signal: controller.signal }),
                        ]);

                        if (controller.signal.aborted || Number(state.mesa.laudoId || 0) !== id) {
                            return null;
                        }

                        state.mesa.mensagens = mensagens.itens || [];
                        state.mesa.pacote = pacote || null;
                        state.mesa.loadedLaudoId = id;
                        renderMesaMensagens();
                        renderMesaResumo();
                        perfSnapshot(`cliente:mesa:${id}`);

                        const alvo = obterLaudoMesaPorId(id);
                        if (Number(alvo?.whispers_nao_lidos || 0) > 0) {
                            api(`/cliente/api/mesa/laudos/${id}/marcar-whispers-lidos`, { method: "POST" }).catch(() => null);
                            if (state.bootstrap?.mesa?.laudos) {
                                state.bootstrap.mesa.laudos = state.bootstrap.mesa.laudos.map((item) =>
                                    Number(item.id) === id ? { ...item, whispers_nao_lidos: 0 } : item
                                );
                                renderMesaResumoGeral();
                                renderMesaList();
                                renderMesaContext();
                                atualizarBadgesTabs();
                            }
                        }

                        if (!silencioso && state.ui.tab !== "mesa") {
                            feedback("Fila da mesa sincronizada.");
                        }
                        return { mensagens, pacote };
                    } catch (erro) {
                        if (ehAbortError(erro)) {
                            return null;
                        }
                        throw erro;
                    } finally {
                        if (state.mesa.loadController === controller) {
                            state.mesa.loadController = null;
                        }
                    }
                },
                { laudoId: Number(laudoId || 0) || 0, silencioso },
                "function"
            );
        }

        function atualizarBuscaMesa(valor) {
            state.ui.mesaBusca = valor || "";
            state.ui.mesaSituacao = "";
            renderMesaTriagem();
            renderMesaList();
        }

        function aplicarFiltroMesaRapido(situacao) {
            state.ui.mesaBusca = "";
            state.ui.mesaSituacao = texto(situacao).trim();
            if ($("mesa-busca-laudos")) {
                $("mesa-busca-laudos").value = "";
            }
            renderMesaTriagem();
            renderMesaList();
        }

        function limparFiltroMesaRapido() {
            state.ui.mesaBusca = "";
            state.ui.mesaSituacao = "";
            if ($("mesa-busca-laudos")) {
                $("mesa-busca-laudos").value = "";
            }
            renderMesaTriagem();
            renderMesaList();
        }

        function bindMesaActions() {
            ["click", "keydown"].forEach((tipoEvento) => {
                $("lista-mesa-laudos")?.addEventListener(tipoEvento, async (event) => {
                    const item = event.target.closest("[data-mesa]");
                    if (!item) return;
                    if (tipoEvento === "keydown" && event.key !== "Enter" && event.key !== " ") return;
                    if (tipoEvento === "keydown") event.preventDefault();
                    abrirSecaoMesa("reply");
                    await loadMesa(item.dataset.mesa).catch((erro) => feedback(erro.message || "Falha ao abrir laudo da mesa.", true));
                });
            });

            $("form-mesa-msg")?.addEventListener("submit", async (event) => {
                event.preventDefault();
                if (!mesaCaseActionsEnabled()) {
                    feedback("Este tenant permite ao admin-cliente apenas acompanhamento, sem agir nos casos.", true);
                    return;
                }
                const laudoId = Number(state.mesa.laudoId || 0) || null;
                if (!laudoId) {
                    feedback("Selecione um laudo da mesa primeiro.", true);
                    return;
                }

                const resposta = $("mesa-resposta").value.trim();
                const arquivo = $("mesa-arquivo").files?.[0] || null;
                if (!resposta && !arquivo) {
                    feedback("Escreva uma resposta ou selecione um anexo.", true);
                    return;
                }

                const button = event.submitter || event.target.querySelector('button[type="submit"]');
                await withBusy(button, "Respondendo...", async () => {
                    if (arquivo) {
                        const formData = new FormData();
                        formData.append("arquivo", arquivo);
                        formData.append("texto", resposta);
                        await api(`/cliente/api/mesa/laudos/${laudoId}/responder-anexo`, {
                            method: "POST",
                            body: formData,
                        });
                    } else {
                        await api(`/cliente/api/mesa/laudos/${laudoId}/responder`, {
                            method: "POST",
                            body: { texto: resposta },
                        });
                    }

                    $("mesa-resposta").value = "";
                    $("mesa-arquivo").value = "";
                    await bootstrapPortal({ surface: "mesa", force: true });
                    if (Number(state.mesa.laudoId || 0) === laudoId) {
                        await loadMesa(laudoId, { silencioso: true, force: true });
                    }
                    feedback("Resposta registrada na mesa avaliadora.");
                }).catch((erro) => feedback(erro.message || "Falha ao responder a mesa.", true));
            });

            $("mesa-mensagens")?.addEventListener("click", async (event) => {
                const button = event.target.closest('[data-act="toggle-pendencia"]');
                const laudoId = Number(state.mesa.laudoId || 0) || null;
                if (!button || !laudoId) return;
                if (!mesaCaseActionsEnabled()) {
                    feedback("Este tenant permite ao admin-cliente apenas acompanhamento, sem agir nos casos.", true);
                    return;
                }

                const resolvida = button.dataset.lida === "1";
                await withBusy(button, resolvida ? "Reabrindo..." : "Resolvendo...", async () => {
                    await api(`/cliente/api/mesa/laudos/${laudoId}/pendencias/${button.dataset.id}`, {
                        method: "PATCH",
                        body: { lida: !resolvida },
                    });
                    await bootstrapPortal({ surface: "mesa", force: true });
                    if (Number(state.mesa.laudoId || 0) === laudoId) {
                        await loadMesa(laudoId, { silencioso: true, force: true });
                    }
                    feedback(resolvida ? "Pendencia reaberta." : "Pendencia marcada como resolvida.");
                }).catch((erro) => feedback(erro.message || "Falha ao atualizar pendencia.", true));
            });

            $("btn-mesa-aprovar")?.addEventListener("click", async (event) => {
                if (!mesaCaseActionsEnabled()) {
                    feedback("Este tenant permite ao admin-cliente apenas acompanhamento, sem agir nos casos.", true);
                    return;
                }
                const laudoId = Number(state.mesa.laudoId || 0) || null;
                if (!laudoId) return;
                const laudoSelecionado = obterLaudoMesaPorId(laudoId);
                if (!laudoHasSurfaceAction(laudoSelecionado, "mesa_approve")) {
                    feedback("Este caso ainda nao esta pronto para aprovacao pela mesa.", true);
                    return;
                }
                const button = event.currentTarget;
                await withBusy(button, "Aprovando...", async () => {
                    await api(`/cliente/api/mesa/laudos/${laudoId}/avaliar`, {
                        method: "POST",
                        body: { acao: "aprovar", motivo: "" },
                    });
                    await bootstrapPortal({ surface: "mesa", force: true });
                    if (Number(state.mesa.laudoId || 0) === laudoId) {
                        await loadMesa(laudoId, { silencioso: true, force: true });
                    }
                    feedback("Laudo aprovado pela mesa.");
                }).catch((erro) => feedback(erro.message || "Falha ao aprovar laudo.", true));
            });

            $("btn-mesa-rejeitar")?.addEventListener("click", async (event) => {
                if (!mesaCaseActionsEnabled()) {
                    feedback("Este tenant permite ao admin-cliente apenas acompanhamento, sem agir nos casos.", true);
                    return;
                }
                const laudoId = Number(state.mesa.laudoId || 0) || null;
                if (!laudoId) return;
                const laudoSelecionado = obterLaudoMesaPorId(laudoId);
                if (!laudoHasSurfaceAction(laudoSelecionado, "mesa_return")) {
                    feedback("Este caso ainda nao permite devolucao para correcao.", true);
                    return;
                }

                const motivo = $("mesa-motivo").value.trim();
                if (!motivo) {
                    feedback("Informe o motivo antes de devolver para ajustes.", true);
                    return;
                }

                const button = event.currentTarget;
                await withBusy(button, "Devolvendo...", async () => {
                    await api(`/cliente/api/mesa/laudos/${laudoId}/avaliar`, {
                        method: "POST",
                        body: { acao: "rejeitar", motivo },
                    });
                    await bootstrapPortal({ surface: "mesa", force: true });
                    if (Number(state.mesa.laudoId || 0) === laudoId) {
                        await loadMesa(laudoId, { silencioso: true, force: true });
                    }
                    feedback("Laudo devolvido para ajustes.");
                }).catch((erro) => feedback(erro.message || "Falha ao rejeitar laudo.", true));
            });
        }

        return {
            ...surfaceModule,
            aplicarFiltroMesaRapido,
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
        };
    };
})();
