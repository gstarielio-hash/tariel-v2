// ==========================================
// TARIEL.IA — PAINEL_REVISOR_PAGE.JS
// Papel: bootstrap do painel do revisor.
// Responsável por:
// - websocket de chamados
// - carregamento do laudo ativo
// - binds de eventos da interface
// ==========================================

(function () {
    "use strict";

    const NS = window.TarielRevisorPainel;
    if (!NS || NS.__indexWired__) return;
    NS.__indexWired__ = true;

    const {
        tokenCsrf,
        els,
        state,
        limparAnexoResposta,
        selecionarAnexoResposta,
        sincronizarAnexoRespostaSelecionado,
        obterArquivoAnexoRespostaSelecionado,
        showStatus,
        limparReferenciaMensagemAtiva,
        definirReferenciaMensagemAtiva,
        setActiveItem,
        atualizarDrawerContextoMesa,
        normalizarCollaborationSummary,
        atualizarIndicadoresListaLaudo,
        marcarWhispersComoLidosLaudo,
        irParaMensagemTimeline,
        setViewLoading,
        encontrarMensagemPorId,
        carregarPainelMesaOperacional,
        renderMessageBubble,
        renderWhisperItem,
        renderActionButtons,
        carregarHistoricoMensagens,
        normalizarRespostaHistorico,
        renderTimeline,
        atualizarPendenciaMesaOperacional,
        renderizarPainelAprendizadosVisuais,
        openModal,
        closeModal,
        trapFocus,
        medirSync,
        medirAsync,
        snapshotDOM,
        escapeHtml,
        formatarDataHora,
        abrirResumoPacoteMesa,
        baixarPacoteMesaJson,
        baixarPacoteMesaPdf,
        baixarPacoteMesaOficial,
        baixarEmissaoOficialCongelada,
        emitirOficialmenteMesa,
        renderizarModalRelatorio,
        renderizarPainelDocumentoTecnicoInline,
        ehAbortError,
        registrarTrocaLaudoAtivo,
        contextoLaudoAindaValido,
        sincronizarTenantAccessPolicy,
        userCapabilityEnabled,
        tenantCapabilityReason
    } = NS;

    const pendingCollaborationRefreshByLaudo = new Map();
    const pendingHistoricoConvergenceTimersByLaudo = new Map();
    const btnHomeMesa = document.getElementById("btn-home-mesa");
    const viewportDesktopMesa = () => window.matchMedia("(min-width: 981px)").matches;
    const estadoHomeMesa = {
        tab: null,
        filter: "all"
    };

    const FILA_LABELS = {
        responder_agora: "Responder agora",
        validar_aprendizado: "Validar aprendizado",
        aguardando_inspetor: "Aguardando campo",
        fechamento_mesa: "Fechamento",
        acompanhamento: "Acompanhamento",
        historico: "Histórico"
    };

    const PRIORIDADE_LABELS = {
        critica: "Crítica",
        alta: "Alta",
        media: "Média",
        baixa: "Baixa"
    };

    const formatarTipoTemplate = (valor) => {
        const texto = String(valor || "").trim();
        if (!texto) return "Padrão";
        return texto
            .replace(/[_-]+/g, " ")
            .replace(/\s+/g, " ")
            .trim()
            .replace(/\b\w/g, (letra) => letra.toUpperCase());
    };

    const obterBucketHomeMesa = (item) => {
        const fila = String(item?.dataset?.filaOperacional || "").trim();
        if (fila === "responder_agora" || fila === "validar_aprendizado") {
            return "responder_agora";
        }
        if (fila === "fechamento_mesa") {
            return "aguardando_avaliacao";
        }
        if (fila === "aguardando_inspetor" || fila === "acompanhamento") {
            return "acompanhamento";
        }
        return "historico";
    };

    const filtrarHomeMesa = (item, filtro) => {
        if (!item || !filtro || filtro === "all") return true;
        const whispers = Math.max(0, Number(item.dataset.whispersNaoLidos || 0) || 0);
        const pendencias = Math.max(0, Number(item.dataset.pendenciasAbertas || 0) || 0);
        const aprendizados = Math.max(0, Number(item.dataset.aprendizadosPendentes || 0) || 0);
        const prioridade = String(item.dataset.prioridadeOperacional || "").trim();

        if (filtro === "whispers") return whispers > 0;
        if (filtro === "pendencias") return pendencias > 0;
        if (filtro === "prioridade") return prioridade === "critica" || prioridade === "alta";
        if (filtro === "aprendizados") return aprendizados > 0;
        return true;
    };

    const sincronizarFiltroHomeMesa = () => {
        const tabAtiva = estadoHomeMesa.tab;
        if (!els.estadoVazio || !tabAtiva) return;

        els.estadoVazio
            .querySelectorAll("[data-home-filter]")
            .forEach((chip) => {
                const ativo = chip.dataset.homeFilter === estadoHomeMesa.filter;
                chip.classList.toggle("is-active", ativo);
                chip.setAttribute("aria-pressed", String(ativo));
            });

        els.estadoVazio
            .querySelectorAll("[data-home-panel]")
            .forEach((panel) => {
                const cards = [...panel.querySelectorAll(".mesa-home-card")];
                const filtroVazio = panel.querySelector(".mesa-home-filter-empty");
                let visiveis = 0;

                cards.forEach((card) => {
                    const pertenceTab = obterBucketHomeMesa(card) === panel.dataset.homePanel;
                    const corresponde = pertenceTab && filtrarHomeMesa(card, estadoHomeMesa.filter);
                    card.hidden = !corresponde;
                    if (corresponde) visiveis += 1;
                });

                if (filtroVazio) {
                    const painelAtivo = panel.dataset.homePanel === tabAtiva;
                    filtroVazio.hidden = !(painelAtivo && visiveis === 0 && cards.length > 0);
                }
            });
    };

    const definirFiltroHomeMesa = (filtro) => {
        estadoHomeMesa.filter = String(filtro || "all").trim() || "all";
        sincronizarFiltroHomeMesa();
    };

    const renderizarResumoCasoAberto = (dados = {}) => {
        if (!els.viewCaseSummary) return;

        const laudoId = Number(dados?.id || state.laudoAtivoId || 0) || 0;
        const seletorLaudo = `[data-id="${CSS.escape(String(laudoId))}"]`;
        const origem = document.querySelector(`.mesa-queue-item${seletorLaudo}`)
            || document.querySelector(`.mesa-home-card${seletorLaudo}`)
            || document.querySelector(`.js-item-laudo${seletorLaudo}`);
        const fila = String(origem?.dataset?.filaOperacional || "").trim();
        const prioridade = String(origem?.dataset?.prioridadeOperacional || "").trim();
        const whispers = Math.max(0, Number(origem?.dataset?.whispersNaoLidos || 0) || 0);
        const pendencias = Math.max(0, Number(origem?.dataset?.pendenciasAbertas || 0) || 0);
        const aprendizados = Math.max(0, Number(origem?.dataset?.aprendizadosPendentes || 0) || 0);
        const inspetor = String(origem?.dataset?.inspetorNome || "").trim() || "Inspetor não identificado";
        const setor = String(origem?.dataset?.setorIndustrial || dados?.setor || "").trim() || "Setor não informado";
        const proximaAcao = String(origem?.dataset?.proximaAcao || "").trim() || "Abrir caso e definir o próximo passo";
        const tempoEmCampo = String(origem?.dataset?.tempoEmCampo || "").trim();
        const template = formatarTipoTemplate(dados?.tipo_template);
        const status = String(
            origem?.dataset?.statusVisualLabel
            || dados?.status_visual_label
            || ""
        ).trim() || "Em analise";
        const criadoEm = String(dados?.criado_em || "").trim() || formatarDataHora(new Date());

        els.viewCaseSummary.innerHTML = `
            <div class="view-case-summary-head">
                <div>
                    <span class="view-case-summary-kicker">${escapeHtml(setor)}</span>
                    <strong>Resumo executivo do caso</strong>
                </div>
                <span class="view-case-summary-status">${escapeHtml(status)}</span>
            </div>
            <div class="view-case-summary-pills">
                <span class="view-case-summary-pill">${escapeHtml(template)}</span>
                <span class="view-case-summary-pill">${escapeHtml(FILA_LABELS[fila] || "Operação")}</span>
                <span class="view-case-summary-pill">Prioridade ${escapeHtml(PRIORIDADE_LABELS[prioridade] || "Média")}</span>
                <span class="view-case-summary-pill">${escapeHtml(inspetor)}</span>
                <span class="view-case-summary-pill">${tempoEmCampo ? `Em campo há ${escapeHtml(tempoEmCampo)}` : `Criado em ${escapeHtml(criadoEm)}`}</span>
            </div>
            <div class="view-case-summary-grid">
                <article class="view-case-summary-card">
                    <span>Próxima ação</span>
                    <strong>${escapeHtml(proximaAcao)}</strong>
                </article>
                <article class="view-case-summary-card">
                    <span>Chamados</span>
                    <strong>${escapeHtml(String(whispers))}</strong>
                </article>
                <article class="view-case-summary-card">
                    <span>Pendências</span>
                    <strong>${escapeHtml(String(pendencias))}</strong>
                </article>
                <article class="view-case-summary-card">
                    <span>Aprendizados</span>
                    <strong>${escapeHtml(String(aprendizados))}</strong>
                </article>
            </div>
        `;
    };

    const focarRespostaCaso = () => {
        els.boxResposta?.scrollIntoView({ behavior: "smooth", block: "end" });
        els.inputResposta?.focus();
    };

    const atualizarEstadoHomeMesa = (ativa) => {
        els.body?.classList.toggle("mesa-home-ativa", !!ativa);
    };

    const ativarTabHomeMesa = (chave) => {
        const tabAlvo = String(chave || "").trim();
        if (!tabAlvo || !els.estadoVazio) return;
        estadoHomeMesa.tab = tabAlvo;

        els.estadoVazio
            .querySelectorAll("[data-home-tab]")
            .forEach((tab) => {
                const ativo = tab.dataset.homeTab === tabAlvo;
                tab.classList.toggle("is-active", ativo);
                tab.setAttribute("aria-selected", String(ativo));
            });

        els.estadoVazio
            .querySelectorAll("[data-home-panel]")
            .forEach((panel) => {
                const ativo = panel.dataset.homePanel === tabAlvo;
                panel.classList.toggle("is-active", ativo);
                panel.hidden = !ativo;
            });

        sincronizarFiltroHomeMesa();
    };

    const mostrarHomeMesa = () => {
        registrarTrocaLaudoAtivo(null);
        limparConvergenciaHistoricoAgendada();
        limparReferenciaMensagemAtiva();
        limparAnexoResposta();
        atualizarDrawerContextoMesa({ aberto: false });
        setActiveItem(null);

        if (els.viewContent) {
            els.viewContent.hidden = true;
        }
        if (els.estadoVazio) {
            els.estadoVazio.style.display = "";
        }
        if (els.viewCaseSummary) {
            els.viewCaseSummary.innerHTML = `
                <div class="view-case-summary-placeholder">
                    Abra um laudo para ver status, prioridade, próxima ação e o contexto operacional resumido.
                </div>
            `;
        }
        if (els.viewStructuredDocument) {
            els.viewStructuredDocument.hidden = true;
            els.viewStructuredDocument.innerHTML = "";
        }
        atualizarEstadoHomeMesa(true);
        sincronizarFiltroHomeMesa();
    };

    const substituirOuAcrescentarMensagemNoHistorico = (mensagem) => {
        const mensagemId = Number(mensagem?.id || 0) || null;
        if (!mensagemId) return false;

        const historicoAtual = Array.isArray(state.historicoMensagens)
            ? state.historicoMensagens
            : [];
        const semDuplicata = historicoAtual.filter(
            (item) => Number(item?.id || 0) !== mensagemId
        );
        state.historicoMensagens = [...semDuplicata, mensagem];
        return true;
    };

    const extrairCollaborationSummaryDoSnapshot = (snapshot) => {
        const fromProjection = snapshot?.reviewer_case_view?.payload?.collaboration?.summary;
        if (fromProjection && typeof fromProjection === "object") {
            return fromProjection;
        }
        const fromLegacy = snapshot?.collaboration?.summary;
        if (fromLegacy && typeof fromLegacy === "object") {
            return fromLegacy;
        }
        return null;
    };

    const extrairCaseStatusVisualDoSnapshot = (snapshot) => {
        if (!snapshot || typeof snapshot !== "object") {
            return null;
        }
        return {
            caseLifecycleStatus: String(snapshot.case_lifecycle_status || "").trim().toLowerCase(),
            activeOwnerRole: String(snapshot.active_owner_role || "").trim().toLowerCase(),
            statusVisualLabel: String(snapshot.status_visual_label || "").trim()
        };
    };

    const limparConvergenciaHistoricoAgendada = (laudoId = null) => {
        const alvo = Number(laudoId || 0) || null;
        if (!alvo) {
            pendingHistoricoConvergenceTimersByLaudo.forEach((timers) => {
                (Array.isArray(timers) ? timers : []).forEach((timerId) => {
                    window.clearTimeout(timerId);
                });
            });
            pendingHistoricoConvergenceTimersByLaudo.clear();
            return;
        }

        const timers = pendingHistoricoConvergenceTimersByLaudo.get(alvo);
        (Array.isArray(timers) ? timers : []).forEach((timerId) => {
            window.clearTimeout(timerId);
        });
        pendingHistoricoConvergenceTimersByLaudo.delete(alvo);
    };

    const agendarConvergenciaHistoricoLaudo = (laudoId, { delaysMs = [250, 1100, 2600] } = {}) => {
        const alvo = Number(laudoId || 0) || null;
        if (!alvo) return;

        limparConvergenciaHistoricoAgendada(alvo);
        const timers = (Array.isArray(delaysMs) ? delaysMs : [])
            .map((delay) => Math.max(0, Number(delay || 0) || 0))
            .map((delay) => window.setTimeout(() => {
                if (Number(state.laudoAtivoId || 0) !== alvo) {
                    return;
                }
                carregarHistoricoMensagens({ appendAntigas: false }).catch(() => {});
            }, delay));

        pendingHistoricoConvergenceTimersByLaudo.set(alvo, timers);
    };

    const sincronizarIndicadoresLaudoViaSnapshot = async (laudoId) => {
        const alvo = Number(laudoId || 0);
        if (!Number.isFinite(alvo) || alvo <= 0) return;
        if (pendingCollaborationRefreshByLaudo.has(alvo)) {
            await pendingCollaborationRefreshByLaudo.get(alvo);
            return;
        }

        const promise = (async () => {
            const params = new URLSearchParams();
            params.set("incluir_historico", "false");
            const resposta = await fetch(`/revisao/api/laudo/${alvo}/completo?${params.toString()}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" }
            });
            if (!resposta.ok) return;
            const payload = await resposta.json();
            const collaborationSummary = extrairCollaborationSummaryDoSnapshot(payload);
            const caseStatusVisual = extrairCaseStatusVisualDoSnapshot(payload);
            if (!collaborationSummary && !caseStatusVisual) return;
            atualizarIndicadoresListaLaudo(alvo, {
                collaborationSummary,
                caseLifecycleStatus: caseStatusVisual?.caseLifecycleStatus || null,
                activeOwnerRole: caseStatusVisual?.activeOwnerRole || null,
                statusVisualLabel: caseStatusVisual?.statusVisualLabel || null,
                collaborationDelta: null,
                whispersNaoLidos: null
            });
        })();

        pendingCollaborationRefreshByLaudo.set(alvo, promise);
        try {
            await promise;
        } finally {
            pendingCollaborationRefreshByLaudo.delete(alvo);
        }
    };

    const inicializarWebSocket = () => {
        return medirSync("revisor.inicializarWebSocket", () => {
            clearTimeout(state.wsReconnectTimer);

            if (
                state.socketWhisper
                && (
                    state.socketWhisper.readyState === WebSocket.OPEN
                    || state.socketWhisper.readyState === WebSocket.CONNECTING
                )
            ) {
                return;
            }

            const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
            const wsUrl = `${protocolo}//${window.location.host}/revisao/ws/whispers`;
            const socket = new WebSocket(wsUrl);
            state.wsFechamentoManual = false;
            state.socketWhisper = socket;

            socket.addEventListener("open", () => {
                if (state.socketWhisper !== socket) return;
                console.info("[Tariel] Canal de chamados conectado.");
            });

            socket.addEventListener("message", (evento) => {
                if (state.socketWhisper !== socket) return;
                try {
                    const dados = JSON.parse(evento.data);
                    if (dados?.tipo === "erro") {
                        showStatus(
                            String(dados?.detail || tenantCapabilityReason("reviewer_decision") || "Canal governado."),
                            "warning"
                        );
                        return;
                    }
                    if (!dados?.laudo_id) return;

                    const laudoAtivo = Number(state.laudoAtivoId || 0);
                    const laudoEvento = Number(dados.laudo_id || 0);
                    if (laudoAtivo > 0 && laudoAtivo === laudoEvento) {
                        const mensagemEvento = dados?.mensagem;
                        if (mensagemEvento && substituirOuAcrescentarMensagemNoHistorico(mensagemEvento)) {
                            renderTimeline({ rolarParaFim: true });
                        }
                        agendarConvergenciaHistoricoLaudo(laudoEvento, {
                            delaysMs: mensagemEvento ? [200, 900, 2200] : [0, 900, 2200]
                        });
                        carregarPainelMesaOperacional({ forcar: true }).catch(() => {});
                        sincronizarIndicadoresLaudoViaSnapshot(laudoEvento).catch(() => {});
                        carregarLaudo(laudoEvento, { forcar: true, preservarComposer: true }).catch(() => {});
                        showStatus("Novo chamado recebido no laudo aberto.", "notifications_active");
                        return;
                    }

                    if (els.containerWhispers) {
                        els.containerWhispers.hidden = false;
                    }

                    const existente = els.listaWhispers.querySelector(`[data-id="${CSS.escape(String(dados.laudo_id))}"]`);
                    if (existente) {
                        existente.remove();
                    }

                    els.listaWhispers.prepend(renderWhisperItem(dados));
                    const collaborationSummaryBruta = (
                        dados?.collaboration_summary
                        || dados?.collaborationSummary
                        || dados?.collaboration?.summary
                        || null
                    );
                    const collaborationSummary = collaborationSummaryBruta
                        ? normalizarCollaborationSummary(collaborationSummaryBruta)
                        : null;
                    atualizarIndicadoresListaLaudo(laudoEvento, {
                        collaborationSummary,
                        collaborationDelta: null,
                        whispersNaoLidos: null
                    });
                    sincronizarIndicadoresLaudoViaSnapshot(laudoEvento).catch(() => {});
                    showStatus("Novo chamado recebido.", "notifications_active");
                    snapshotDOM(`revisor:whisper:${laudoEvento}`);
                } catch (erro) {
                    console.error("[Tariel] Erro ao processar chamado:", erro);
                }
            });

            socket.addEventListener("close", (evento) => {
                if (state.socketWhisper === socket) {
                    state.socketWhisper = null;
                }
                if (state.wsFechamentoManual) {
                    return;
                }
                if (evento?.code === 4403 && !userCapabilityEnabled("reviewer_decision")) {
                    showStatus(tenantCapabilityReason("reviewer_decision"), "warning");
                    return;
                }
                console.info("[Tariel] WebSocket fechado; tentando reconectar...");
                state.wsReconnectTimer = setTimeout(inicializarWebSocket, 5000);
            });

            socket.addEventListener("error", () => {
                if (state.socketWhisper !== socket) return;
                if (socket.readyState < WebSocket.CLOSING) {
                    socket.close();
                }
            });
        }, { laudoAtivoId: Number(state.laudoAtivoId || 0) || 0 }, "boot");
    };

    const finalizarWebSocket = () => {
        clearTimeout(state.wsReconnectTimer);
        state.wsFechamentoManual = true;
        const socket = state.socketWhisper;
        state.socketWhisper = null;
        if (socket && socket.readyState < WebSocket.CLOSING) {
            socket.close();
        }
    };

    const carregarLaudo = async (id, { forcar = false, preservarComposer = false } = {}) => {
        return medirAsync("revisor.carregarLaudo", async () => {
            const laudoId = Number(id || 0);
            if (!Number.isFinite(laudoId) || laudoId <= 0) return;
            if (!forcar && state.laudoLoadPromise && state.laudoLoadLaudoId === laudoId) {
                return state.laudoLoadPromise;
            }

            limparConvergenciaHistoricoAgendada(laudoId);

            if (state.laudoLoadController && state.laudoLoadLaudoId !== laudoId) {
                state.laudoLoadController.abort();
            }
            const controller = new AbortController();
            state.laudoLoadController = controller;
            state.laudoLoadLaudoId = laudoId;

            const contexto = registrarTrocaLaudoAtivo(laudoId);
            if (!preservarComposer) {
                limparReferenciaMensagemAtiva();
            }
            setActiveItem(laudoId);
            setViewLoading();
            atualizarEstadoHomeMesa(false);
            atualizarDrawerContextoMesa({ aberto: viewportDesktopMesa() });

            const promise = (async () => {
                try {
                    const params = new URLSearchParams();
                    params.set("incluir_historico", "true");
                    const res = await fetch(`/revisao/api/laudo/${laudoId}/completo?${params.toString()}`, {
                        headers: { "X-Requested-With": "XMLHttpRequest" },
                        signal: controller.signal
                    });

                    if (!res.ok) {
                        throw new Error(`Falha HTTP ${res.status}`);
                    }

                    const dados = await res.json();
                    if (controller.signal.aborted || !contextoLaudoAindaValido(contexto)) {
                        return;
                    }
                    sincronizarTenantAccessPolicy(dados?.tenant_access_policy);

                    state.reviewerCaseViewAtivo = (
                        dados?.reviewer_case_view && typeof dados.reviewer_case_view === "object"
                    ) ? dados.reviewer_case_view : null;
                    state.reviewerCaseViewLaudoId = (
                        state.reviewerCaseViewAtivo && dados?.reviewer_case_view_preferred
                    ) ? laudoId : null;
                    state.reviewerCaseViewPreferred = !!(
                        state.reviewerCaseViewAtivo
                        && dados?.reviewer_case_view_preferred
                    );
                    state.jsonEstruturadoAtivo = dados.dados_formulario || null;
                    state.aprendizadosVisuais = Array.isArray(dados.aprendizados_visuais) ? [...dados.aprendizados_visuais] : [];
                    const paginaHistoricoInicial = normalizarRespostaHistorico({
                        itens: Array.isArray(dados.historico) ? dados.historico : [],
                        cursor_proximo: dados?.historico_paginado?.cursor_proximo,
                        tem_mais: dados?.historico_paginado?.tem_mais
                    });
                    state.historicoMensagens = [...paginaHistoricoInicial.itens];
                    state.historicoCursorProximo = paginaHistoricoInicial.cursor_proximo;
                    state.historicoTemMais = !!paginaHistoricoInicial.tem_mais;
                    state.carregandoHistoricoAntigo = false;
                    if (!preservarComposer) {
                        limparAnexoResposta();
                    }
                    const aprendizadosPendentes = state.aprendizadosVisuais.filter(
                        (item) => String(item?.status || "") === "rascunho_inspetor"
                    ).length;

                    els.viewHash.textContent = `Inspeção #${dados.hash}`;
                    els.viewMeta.textContent = `Modelo: ${formatarTipoTemplate(dados.tipo_template)} | Setor: ${String(dados.setor || "nao informado")} | Criado: ${dados.criado_em}`;

                    renderActionButtons(dados);
                    renderTimeline({ rolarParaFim: true });
                    atualizarIndicadoresListaLaudo(laudoId, {
                        aprendizadosPendentes,
                        caseLifecycleStatus: dados?.case_lifecycle_status || null,
                        activeOwnerRole: dados?.active_owner_role || null,
                        statusVisualLabel: dados?.status_visual_label || null
                    });
                    renderizarPainelAprendizadosVisuais(state.aprendizadosVisuais);
                    await carregarPainelMesaOperacional({ forcar: false });
                    renderizarResumoCasoAberto(dados);
                    renderizarPainelDocumentoTecnicoInline?.();
                    if (controller.signal.aborted || !contextoLaudoAindaValido(contexto)) {
                        return;
                    }
                    await marcarWhispersComoLidosLaudo(laudoId, { silencioso: true });
                    snapshotDOM(`revisor:laudo:${laudoId}`);
                    els.inputResposta.focus();
                } catch (erro) {
                    if (ehAbortError(erro) || !contextoLaudoAindaValido(contexto)) {
                        return;
                    }
                    els.timeline.innerHTML = `<div class="timeline-status erro">Erro ao carregar laudo.</div>`;
                    console.error("[Tariel] Falha ao carregar laudo:", erro);
                } finally {
                    if (state.laudoLoadController === controller) {
                        state.laudoLoadController = null;
                    }
                    if (state.laudoLoadPromise === promise) {
                        state.laudoLoadPromise = null;
                    }
                    if (state.laudoLoadLaudoId === laudoId) {
                        state.laudoLoadLaudoId = null;
                    }
                }
            })();
            state.laudoLoadPromise = promise;
            return promise;
        }, { laudoId: Number(id || 0) || 0 });
    };

    const abrirLaudoPorCard = async (id, { focarComposer = false } = {}) => {
        const laudoId = Number(id || 0);
        if (!Number.isFinite(laudoId) || laudoId <= 0) return;
        await carregarLaudo(laudoId);
        if (focarComposer) {
            focarRespostaCaso();
        }
    };

    window.addEventListener("pagehide", finalizarWebSocket);
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible" && (!state.socketWhisper || state.socketWhisper.readyState > 1)) {
            inicializarWebSocket();
        }
    });

    document.addEventListener("DOMContentLoaded", () => {
        inicializarWebSocket();
        ativarTabHomeMesa(els.estadoVazio?.dataset?.homeTabInicial || "responder_agora");
        atualizarEstadoHomeMesa(true);
        atualizarDrawerContextoMesa({ aberto: viewportDesktopMesa() });
        sincronizarFiltroHomeMesa();
        snapshotDOM("revisor:dom-content-loaded");
    });

    window.addEventListener("resize", () => {
        atualizarDrawerContextoMesa({ aberto: viewportDesktopMesa() && !!state.laudoAtivoId });
    });

    window.addEventListener("load", () => {
        snapshotDOM("revisor:window-load");
    }, { once: true });


    Object.assign(NS, {
        inicializarWebSocket,
        finalizarWebSocket,
        carregarLaudo,
        abrirLaudoPorCard,
        substituirOuAcrescentarMensagemNoHistorico,
        mostrarHomeMesa,
        ativarTabHomeMesa,
        definirFiltroHomeMesa
    });
})();
