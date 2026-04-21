// ==========================================
// TARIEL.IA — REVISOR_PAINEL_APRENDIZADOS_ACTIONS.JS
// Papel: mutações e ações do painel de aprendizados visuais.
// ==========================================

(function () {
    "use strict";

    const NS = window.TarielRevisorPainel;
    if (!NS || NS.__aprendizadosActionsWired__) return;
    NS.__aprendizadosActionsWired__ = true;

    const {
        tokenCsrf,
        els,
        state,
        irParaMensagemTimeline,
        showStatus,
        medirAsync
    } = NS;

    const normalizarLista = (valor) =>
        Array.isArray(valor)
            ? valor.filter(Boolean).map((item) => String(item).trim()).filter(Boolean)
            : [];

    const encontrarAprendizadoPorId = (aprendizadoId) =>
        (state.aprendizadosVisuais || []).find((item) => Number(item?.id || 0) === Number(aprendizadoId)) || null;

    const bloquearCardAprendizado = (card, bloqueado) => {
        if (!card) return;
        card.classList.toggle("is-saving", !!bloqueado);
        card.querySelectorAll("button, input, textarea, select").forEach((elemento) => {
            elemento.disabled = !!bloqueado;
        });
    };

    const restaurarBotoesCard = (card) => {
        if (!card) return;
        card.classList.remove("is-saving");
        card.querySelectorAll("button, input, textarea, select").forEach((elemento) => {
            elemento.disabled = false;
        });
    };

    const montarPayloadValidacao = (item, card, acao) => {
        const resumoFinal = card.querySelector(".js-aprendizado-resumo-final")?.value?.trim() || "";
        const sintese = card.querySelector(".js-aprendizado-sintese")?.value?.trim() || "";
        const parecer = card.querySelector(".js-aprendizado-parecer")?.value?.trim() || "";
        const veredito = card.querySelector(".js-aprendizado-veredito")?.value?.trim() || "";
        const fallbackSintese = sintese || parecer || String(item?.correcao_inspetor || "").trim() || String(item?.resumo || "").trim();

        return {
            acao,
            resumo_final: resumoFinal || String(item?.resumo || "").trim(),
            sintese_consolidada: acao === "aprovar" ? fallbackSintese : sintese,
            parecer_mesa: parecer || (acao === "rejeitar" ? "Rejeitado pela mesa após revisão visual." : ""),
            veredito_mesa: veredito || String(item?.veredito_mesa || item?.veredito_inspetor || "").trim() || null,
            pontos_chave: normalizarLista(item?.pontos_chave),
            referencias_norma: normalizarLista(item?.referencias_norma),
            marcacoes: Array.isArray(item?.marcacoes) ? item.marcacoes : []
        };
    };

    const validarAprendizadoVisual = async (aprendizadoId, acao, card) => {
        return medirAsync("revisor.validarAprendizadoVisual", async () => {
            const item = encontrarAprendizadoPorId(aprendizadoId);
            if (!item || !state.laudoAtivoId || !card) return;

            const botaoAcionado = card.querySelector(acao === "aprovar" ? ".js-aprendizado-aprovar" : ".js-aprendizado-rejeitar");
            const labelOriginal = botaoAcionado ? botaoAcionado.innerHTML : "";
            bloquearCardAprendizado(card, true);
            if (botaoAcionado) {
                botaoAcionado.innerHTML = acao === "aprovar"
                    ? `<span class="material-symbols-rounded" aria-hidden="true">sync</span><span>Validando...</span>`
                    : `<span class="material-symbols-rounded" aria-hidden="true">sync</span><span>Rejeitando...</span>`;
            }

            try {
                const res = await fetch(`/revisao/api/aprendizados/${aprendizadoId}/validar`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRF-Token": tokenCsrf,
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: JSON.stringify(montarPayloadValidacao(item, card, acao))
                });

                if (!res.ok) {
                    let detalhe = `Falha HTTP ${res.status}`;
                    try {
                        const payload = await res.json();
                        detalhe = String(payload?.detail || detalhe);
                    } catch (_) {
                        // noop
                    }
                    throw new Error(detalhe);
                }

                showStatus(
                    acao === "aprovar" ? "Aprendizado visual validado pela mesa." : "Aprendizado visual rejeitado pela mesa.",
                    acao === "aprovar" ? "rule" : "cancel"
                );

                if (typeof NS.carregarLaudo === "function") {
                    await NS.carregarLaudo(state.laudoAtivoId, { preservarComposer: true });
                }
            } catch (erro) {
                if (botaoAcionado) {
                    botaoAcionado.innerHTML = labelOriginal;
                }
                restaurarBotoesCard(card);
                showStatus(erro?.message || "Erro ao validar aprendizado visual.", "error");
                console.error("[Tariel] Falha ao validar aprendizado visual:", erro);
            }
        }, { aprendizadoId: Number(aprendizadoId || 0) || 0, acao: String(acao || "") });
    };

    els.aprendizadosVisuaisPainel?.addEventListener("click", (event) => {
        const acao = event.target.closest("[data-aprendizado-action]");
        if (!acao) return;

        if (acao.dataset.aprendizadoAction === "timeline-ref") {
            const referenciaId = Number(acao.dataset.refId || 0);
            if (Number.isFinite(referenciaId) && referenciaId > 0) {
                irParaMensagemTimeline(referenciaId);
            }
            return;
        }

        const card = event.target.closest(".aprendizado-card");
        const aprendizadoId = Number(card?.dataset?.aprendizadoId || 0);
        if (!Number.isFinite(aprendizadoId) || aprendizadoId <= 0) return;

        if (acao.dataset.aprendizadoAction === "aprovar") {
            validarAprendizadoVisual(aprendizadoId, "aprovar", card);
            return;
        }

        if (acao.dataset.aprendizadoAction === "rejeitar") {
            validarAprendizadoVisual(aprendizadoId, "rejeitar", card);
        }
    });
})();
