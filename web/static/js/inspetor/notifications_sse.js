(function () {
    "use strict";

    const modules = window.TarielInspetorModules = window.TarielInspetorModules || {};

    modules.registerNotifications = function registerNotifications(ctx) {
        const estado = ctx.state;
        const el = ctx.elements;
        const {
            mostrarToast,
            ROTA_SSE_NOTIFICACOES,
            TEMPO_BANNER_MS,
            TEMPO_RECONEXAO_SSE_MS,
            LIMITE_RECONEXAO_SSE_OFFLINE,
            obterLaudoAtivoIdSeguro,
            limparTimerReconexaoSSE,
            fecharSSE,
            limparTimerBanner,
        } = ctx.shared;
        const atualizarConexaoMesaWidget = (...args) => ctx.actions.atualizarConexaoMesaWidget?.(...args);
        const atualizarChatAoVivoComMesa = (...args) => ctx.actions.atualizarChatAoVivoComMesa?.(...args);
        const carregarPendenciasMesa = (...args) => ctx.actions.carregarPendenciasMesa?.(...args);
        const atualizarBadgePendencias = (...args) => ctx.actions.atualizarBadgePendencias?.(...args);
        const atualizarPainelWorkspaceDerivado = (...args) => ctx.actions.atualizarPainelWorkspaceDerivado?.(...args);
        const carregarMensagensMesaWidget = (...args) => ctx.actions.carregarMensagensMesaWidget?.(...args);
        const renderizarResumoOperacionalMesa = (...args) => ctx.actions.renderizarResumoOperacionalMesa?.(...args);
        const atualizarBadgeMesaWidget = (...args) => ctx.actions.atualizarBadgeMesaWidget?.(...args);
        const atualizarStatusMesa = (...args) => ctx.actions.atualizarStatusMesa?.(...args);
        const PERF = window.TarielPerf || window.TarielCore?.TarielPerf || null;

    function contarChurnSSE(nome, detail = {}) {
        PERF?.count?.(nome, 1, {
            category: "request_churn",
            detail,
        });
    }

    function obterScreenInspectorAtual() {
        return String(
            document.body?.dataset?.inspectorBaseScreen
            || document.body?.dataset?.inspectorScreen
            || ""
        ).trim();
    }

    function sseNecessarioNoContextoAtual() {
        if (document.visibilityState === "hidden") {
            return false;
        }

        const laudoAtivo = obterLaudoAtivoIdSeguro();
        if (!laudoAtivo) {
            return false;
        }

        const body = document.body;
        const baseScreen = String(body?.dataset?.inspectorBaseScreen || "").trim();
        const screen = obterScreenInspectorAtual();
        const overlayOwner = String(
            body?.dataset?.inspectorOverlayOwner ||
            body?.dataset?.overlayOwner ||
            ""
        ).trim();

        if (overlayOwner) {
            return false;
        }

        if (baseScreen === "inspection_workspace") {
            return true;
        }

        return (
            screen === "inspection_record" ||
            screen === "inspection_conversation" ||
            screen === "inspection_history" ||
            screen === "inspection_mesa"
        );
    }

    function eventoEhDoLaudoAtivo(laudoIdEvento) {
        const evento = Number(laudoIdEvento || 0) || null;
        const laudoAtivo = Number(obterLaudoAtivoIdSeguro() || 0) || null;
        if (!evento || !laudoAtivo) return true;
        return evento === laudoAtivo;
    }

    function calcularAtrasoReconexao() {
        const multiplicador = Math.max(1, 2 ** Math.max(0, estado.tentativasReconexaoSSE - 1));
        return Math.min(TEMPO_RECONEXAO_SSE_MS * multiplicador, 15000);
    }

    function mostrarBannerEngenharia(texto = "") {
        if (!el.bannerEngenharia || !el.textoBannerEngenharia) return;

        limparTimerBanner();

        const textoLimpo = String(texto || "").trim() || "Nova mensagem recebida...";
        el.textoBannerEngenharia.textContent =
            textoLimpo.length > 60 ? `${textoLimpo.slice(0, 60)}…` : textoLimpo;
        renderizarResumoOperacionalMesa();

        el.bannerEngenharia.hidden = false;

        requestAnimationFrame(() => {
            el.bannerEngenharia.classList.add("mostrar");
        });

        estado.timerBanner = window.setTimeout(() => {
            fecharBannerEngenharia();
        }, TEMPO_BANNER_MS);
    }

    function fecharBannerEngenharia() {
        if (!el.bannerEngenharia) return;

        el.bannerEngenharia.classList.remove("mostrar");
        limparTimerBanner();

        window.setTimeout(() => {
            if (el.bannerEngenharia) {
                el.bannerEngenharia.hidden = true;
            }
        }, 350);
    }

    // =========================================================
    // SSE DE NOTIFICAÇÕES
    // =========================================================

    function eventoEhMensagemEngenharia(dados) {
        return Boolean(
            dados?.texto &&
            (
                dados.tipo === "nova_mensagem_eng" ||
                dados.tipo === "mensagem_eng" ||
                dados.tipo === "whisper_eng"
            )
        );
    }

    function eventoEhAtualizacaoPendenciaMesa(dados) {
        return Boolean(
            dados?.texto &&
            (
                dados.tipo === "pendencia_mesa" ||
                dados.tipo === "pendencia_eng"
            )
        );
    }

    function inicializarNotificacoesSSE(opcoes = {}) {
        if (!("EventSource" in window)) {
            atualizarConexaoMesaWidget("offline", "Navegador sem suporte a SSE");
            return;
        }

        if (!sseNecessarioNoContextoAtual()) {
            fecharSSE();
            limparTimerReconexaoSSE();
            contarChurnSSE("inspetor.sse.suprimido_contexto", {
                laudoId: Number(obterLaudoAtivoIdSeguro() || 0) || null,
                screen: obterScreenInspectorAtual(),
            });
            renderizarResumoOperacionalMesa();
            return null;
        }

        if (estado.fonteSSE && opcoes?.forcar !== true) {
            contarChurnSSE("inspetor.sse.reuso_conexao_ativa", {
                laudoId: Number(obterLaudoAtivoIdSeguro() || 0) || null,
            });
            return estado.fonteSSE;
        }

        fecharSSE();
        atualizarConexaoMesaWidget(
            estado.tentativasReconexaoSSE > 0 ? "reconectando" : "conectado"
        );

        const fonte = new EventSource(ROTA_SSE_NOTIFICACOES);
        estado.fonteSSE = fonte;

        fonte.onopen = () => {
            if (estado.fonteSSE !== fonte) return;
            estado.tentativasReconexaoSSE = 0;
            atualizarConexaoMesaWidget("conectado");
        };

        fonte.onmessage = (event) => {
            if (estado.fonteSSE !== fonte) return;
            try {
                const dados = JSON.parse(event.data);

                if (eventoEhAtualizacaoPendenciaMesa(dados)) {
                    const laudoIdEvento = Number(dados?.laudo_id ?? dados?.laudoId ?? 0) || null;
                    if (!eventoEhDoLaudoAtivo(laudoIdEvento)) {
                        contarChurnSSE("inspetor.sse.evento_pendencia_ignorado", {
                            laudoIdEvento,
                            laudoIdAtivo: Number(obterLaudoAtivoIdSeguro() || 0) || null,
                        });
                        return;
                    }
                    carregarPendenciasMesa({ laudoId: laudoIdEvento, silencioso: true }).catch(() => {});
                    if (laudoIdEvento && estado.mesaWidgetAberto && laudoIdEvento === obterLaudoAtivoIdSeguro()) {
                        carregarMensagensMesaWidget({ silencioso: true }).catch(() => {});
                    }
                    mostrarToast(String(dados.texto || "").trim() || "Pendência da mesa atualizada.", "info", 2200);
                    return;
                }

                if (eventoEhMensagemEngenharia(dados)) {
                    const laudoIdEvento = Number(dados?.laudo_id ?? dados?.laudoId ?? 0) || null;
                    if (!eventoEhDoLaudoAtivo(laudoIdEvento)) {
                        contarChurnSSE("inspetor.sse.evento_mensagem_ignorado", {
                            laudoIdEvento,
                            laudoIdAtivo: Number(obterLaudoAtivoIdSeguro() || 0) || null,
                        });
                        return;
                    }
                    mostrarBannerEngenharia(dados.texto);
                    carregarPendenciasMesa({ laudoId: laudoIdEvento, silencioso: true }).catch(() => {});
                    atualizarChatAoVivoComMesa(dados).catch(() => {});
                    if (!estado.mesaWidgetAberto) {
                        estado.mesaWidgetNaoLidas += 1;
                        atualizarBadgeMesaWidget();
                    }
                    return;
                }

                if (dados?.tipo === "conectado") {
                    estado.tentativasReconexaoSSE = 0;
                    atualizarConexaoMesaWidget("conectado");
                    atualizarPainelWorkspaceDerivado();
                    atualizarBadgePendencias(estado.qtdPendenciasAbertas || 0);
                }
            } catch (erro) {
                console.error("[TARIEL][CHAT_INDEX_PAGE] Falha ao decodificar SSE:", erro);
            }
        };

        fonte.onerror = () => {
            if (estado.fonteSSE !== fonte) return;
            fecharSSE(fonte);
            limparTimerReconexaoSSE();

            estado.tentativasReconexaoSSE += 1;
            const excedeuLimite = estado.tentativasReconexaoSSE > LIMITE_RECONEXAO_SSE_OFFLINE;

            if (excedeuLimite) {
                atualizarConexaoMesaWidget("offline");
                atualizarStatusMesa("offline");
            } else {
                atualizarConexaoMesaWidget("reconectando");
            }

            if (!sseNecessarioNoContextoAtual()) {
                return;
            }

            estado.timerReconexaoSSE = window.setTimeout(() => {
                inicializarNotificacoesSSE();
            }, calcularAtrasoReconexao());
        };

        return fonte;
    }

    // =========================================================

        Object.assign(ctx.actions, {
            mostrarBannerEngenharia,
            fecharBannerEngenharia,
            eventoEhMensagemEngenharia,
            eventoEhAtualizacaoPendenciaMesa,
            inicializarNotificacoesSSE,
        });
    };
})();
