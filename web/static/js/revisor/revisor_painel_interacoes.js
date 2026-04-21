// ==========================================
// TARIEL.IA — REVISOR_PAINEL_INTERACOES.JS
// Papel: wiring de interações da interface do painel do revisor.
// ==========================================

(function () {
    "use strict";

    const NS = window.TarielRevisorPainel;
    if (!NS || NS.__interacoesWired__) return;
    NS.__interacoesWired__ = true;

    const {
        els,
        state,
        limparAnexoResposta,
        sincronizarAnexoRespostaSelecionado,
        showStatus,
        limparReferenciaMensagemAtiva,
        definirReferenciaMensagemAtiva,
        irParaMensagemTimeline,
        encontrarMensagemPorId,
        atualizarPendenciaMesaOperacional,
        openModal,
        closeModal,
        trapFocus,
        abrirResumoPacoteMesa,
        baixarPacoteMesaJson,
        baixarPacoteMesaPdf,
        baixarPacoteMesaOficial,
        baixarEmissaoOficialCongelada,
        emitirOficialmenteMesa,
        renderizarModalRelatorio,
        carregarLaudo,
        abrirLaudoPorCard,
        enviarMensagemEngenheiro,
        solicitarRefazerCoverageMesaOperacional,
        confirmarDevolucao,
        mostrarHomeMesa,
        ativarTabHomeMesa,
        definirFiltroHomeMesa,
        tenantCapabilityReason
    } = NS;

    const btnHomeMesa = document.getElementById("btn-home-mesa");

    const handleListaClick = (event) => {
        const item = event.target.closest(".js-item-laudo");
        if (!item) return;

        abrirLaudoPorCard(item.dataset.id).catch((erro) => {
            console.error("[Tariel] Falha ao abrir laudo:", erro);
        });
    };

    const handleListaKeydown = (event) => {
        if (event.target.closest("[data-card-action], [data-home-filter], [data-home-tab]")) {
            return;
        }
        const item = event.target.closest(".js-item-laudo");
        if (!item) return;

        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            item.click();
        }
    };

    els.listaLaudos.addEventListener("click", handleListaClick);
    els.listaLaudos.addEventListener("keydown", handleListaKeydown);
    els.listaWhispers.addEventListener("click", handleListaClick);
    els.listaWhispers.addEventListener("keydown", handleListaKeydown);
    els.estadoVazio?.addEventListener("click", (event) => {
        const acaoCard = event.target.closest("[data-card-action]");
        if (acaoCard) {
            event.preventDefault();
            event.stopPropagation();
            const laudoId = acaoCard.dataset.id || acaoCard.closest(".js-item-laudo")?.dataset.id;
            const focarComposer = acaoCard.dataset.cardAction === "reply";
            abrirLaudoPorCard(laudoId, { focarComposer }).catch((erro) => {
                console.error("[Tariel] Falha ao abrir laudo pela home:", erro);
            });
            return;
        }

        const tab = event.target.closest("[data-home-tab]");
        if (tab) {
            ativarTabHomeMesa(tab.dataset.homeTab);
            return;
        }

        const filtro = event.target.closest("[data-home-filter]");
        if (filtro) {
            definirFiltroHomeMesa(filtro.dataset.homeFilter);
            return;
        }

        handleListaClick(event);
    });
    els.estadoVazio?.addEventListener("keydown", handleListaKeydown);
    btnHomeMesa?.addEventListener("click", () => {
        mostrarHomeMesa();
    });
    els.btnToggleContextoMesa?.addEventListener("click", () => {
        NS.atualizarDrawerContextoMesa();
    });
    els.btnFecharContextoMesa?.addEventListener("click", () => {
        NS.atualizarDrawerContextoMesa({ aberto: false });
    });
    els.timeline.addEventListener("click", (event) => {
        const referencia = event.target.closest(".bolha-referencia[data-ref-id]");
        if (!referencia) return;
        const referenciaId = Number(referencia.dataset.refId || 0);
        if (!Number.isFinite(referenciaId) || referenciaId <= 0) return;
        irParaMensagemTimeline(referenciaId);
    });
    els.mesaOperacaoPainel?.addEventListener("click", (event) => {
        const acao = event.target.closest("[data-mesa-action]");
        if (!acao) return;

        if (acao.dataset.mesaAction === "timeline-msg") {
            const mensagemId = Number(acao.dataset.msgId || 0);
            if (Number.isFinite(mensagemId) && mensagemId > 0) {
                irParaMensagemTimeline(mensagemId);
            }
            return;
        }

        if (acao.dataset.mesaAction === "timeline-ref") {
            const referenciaId = Number(acao.dataset.refId || 0);
            if (Number.isFinite(referenciaId) && referenciaId > 0) {
                irParaMensagemTimeline(referenciaId);
            }
            return;
        }

        if (acao.dataset.mesaAction === "responder-item") {
            const mensagemId = Number(acao.dataset.msgId || 0);
            if (!Number.isFinite(mensagemId) || mensagemId <= 0) return;
            const mensagem = encontrarMensagemPorId(mensagemId) || {
                id: mensagemId,
                texto: `Mensagem #${mensagemId}`
            };
            definirReferenciaMensagemAtiva(mensagem);
            els.boxResposta?.scrollIntoView({ behavior: "smooth", block: "nearest" });
            return;
        }

        if (acao.dataset.mesaAction === "alternar-pendencia") {
            const mensagemId = Number(acao.dataset.msgId || 0);
            const proximaLida = String(acao.dataset.proximaLida || "").toLowerCase() === "true";
            if (!Number.isFinite(mensagemId) || mensagemId <= 0) return;
            atualizarPendenciaMesaOperacional(mensagemId, proximaLida);
            return;
        }

        if (acao.dataset.mesaAction === "solicitar-refazer-coverage") {
            solicitarRefazerCoverageMesaOperacional(acao);
            return;
        }

        if (acao.dataset.mesaAction === "emitir-oficialmente") {
            const laudoId = Number(state.laudoAtivoId || 0) || null;
            const signatoryId = Number(acao.dataset.signatoryId || 0) || null;
            const signatoryName = String(acao.dataset.signatoryName || "").trim();
            const expectedCurrentIssueId = Number(acao.dataset.currentIssueId || 0) || null;
            const expectedCurrentIssueNumber = String(acao.dataset.currentIssueNumber || "").trim();
            if (!laudoId || !signatoryId) return;
            acao.disabled = true;
            emitirOficialmenteMesa({
                signatoryId,
                signatoryName,
                expectedCurrentIssueId,
                expectedCurrentIssueNumber,
            })
                .then(() => carregarLaudo(laudoId, { forcar: true, preservarComposer: true }))
                .catch((erro) => {
                    showStatus(
                        String(erro?.message || "").trim() || "Erro ao registrar emissão oficial.",
                        "error"
                    );
                    console.error("[Tariel] Falha ao emitir oficialmente:", erro);
                })
                .finally(() => {
                    acao.disabled = false;
                });
            return;
        }

        if (acao.dataset.mesaAction === "baixar-emissao-oficial") {
            baixarEmissaoOficialCongelada();
        }
    });

    els.btnEnviarMsg.addEventListener("click", enviarMensagemEngenheiro);
    els.btnAnexoResposta?.addEventListener("click", () => {
        els.inputAnexoResposta?.click();
    });
    const sincronizarInputAnexoResposta = (event) => {
        const arquivo = event.target?.files?.[0];
        if (arquivo) {
            sincronizarAnexoRespostaSelecionado?.(arquivo);
            return;
        }
        limparAnexoResposta();
    };
    els.inputAnexoResposta?.addEventListener("input", sincronizarInputAnexoResposta);
    els.inputAnexoResposta?.addEventListener("change", sincronizarInputAnexoResposta);
    els.previewRespostaAnexo?.addEventListener("click", (event) => {
        const remover = event.target.closest(".btn-remover-anexo-chat");
        if (remover) {
            limparAnexoResposta();
        }
    });
    els.btnLimparRefAtiva?.addEventListener("click", limparReferenciaMensagemAtiva);
    els.inputResposta.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            enviarMensagemEngenheiro();
        }
    });

    els.viewAcoes.addEventListener("click", (event) => {
        if (event.target.closest(".js-btn-pacote-resumo")) {
            abrirResumoPacoteMesa();
            return;
        }

        if (event.target.closest(".js-btn-pacote-json")) {
            baixarPacoteMesaJson();
            return;
        }

        if (event.target.closest(".js-btn-pacote-pdf")) {
            baixarPacoteMesaPdf();
            return;
        }

        if (event.target.closest(".js-btn-pacote-oficial")) {
            baixarPacoteMesaOficial();
            return;
        }

        if (event.target.closest(".js-btn-abrir-rel")) {
            renderizarModalRelatorio();
            openModal(els.modalRelatorio, els.btnFecharRelatorio);
            return;
        }

        if (event.target.closest(".js-btn-abrir-dev")) {
            els.inputMotivo.value = "";
            els.inputMotivo.classList.remove("erro");
            openModal(els.dialogMotivo, els.inputMotivo);
        }
    });

    els.viewAcoes.addEventListener("submit", (event) => {
        const form = event.target.closest(".js-form-aprovar");
        if (!form) return;

        const btn = form.querySelector("button[type='submit']");
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<span class="material-symbols-rounded" aria-hidden="true">sync</span><span>Aprovando...</span>`;
        }
    });

    els.btnFecharRelatorio.addEventListener("click", () => closeModal(els.modalRelatorio));
    els.btnFecharPacote.addEventListener("click", () => closeModal(els.modalPacote));
    els.btnCancelarMotivo.addEventListener("click", () => closeModal(els.dialogMotivo));
    els.btnConfirmarMotivo.addEventListener("click", confirmarDevolucao);

    els.modalRelatorio.addEventListener("click", (event) => {
        if (event.target === els.modalRelatorio) closeModal(els.modalRelatorio);
    });

    els.modalPacote.addEventListener("click", (event) => {
        if (event.target === els.modalPacote) closeModal(els.modalPacote);
    });

    els.dialogMotivo.addEventListener("click", (event) => {
        if (event.target === els.dialogMotivo) closeModal(els.dialogMotivo);
    });

    els.modalRelatorio.addEventListener("keydown", (event) => trapFocus(els.modalRelatorio, event));
    els.modalPacote.addEventListener("keydown", (event) => trapFocus(els.modalPacote, event));
    els.dialogMotivo.addEventListener("keydown", (event) => trapFocus(els.dialogMotivo, event));

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        if (els.dialogMotivo.classList.contains("ativo")) closeModal(els.dialogMotivo);
        else if (els.modalPacote.classList.contains("ativo")) closeModal(els.modalPacote);
        else if (els.modalRelatorio.classList.contains("ativo")) closeModal(els.modalRelatorio);
    });

    els.inputMotivo.addEventListener("input", () => {
        els.inputMotivo.classList.remove("erro");
    });
})();
