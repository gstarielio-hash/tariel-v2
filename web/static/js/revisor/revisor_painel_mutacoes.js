// ==========================================
// TARIEL.IA — REVISOR_PAINEL_MUTACOES.JS
// Papel: mutações operacionais do painel do revisor.
// ==========================================

(function () {
    "use strict";

    const NS = window.TarielRevisorPainel;
    if (!NS || NS.__mutacoesWired__) return;
    NS.__mutacoesWired__ = true;

    const {
        tokenCsrf,
        els,
        state,
        limparAnexoResposta,
        sincronizarAnexoRespostaSelecionado,
        obterArquivoAnexoRespostaSelecionado,
        showStatus,
        limparReferenciaMensagemAtiva,
        renderMessageBubble,
        renderTimeline,
        medirAsync,
        carregarLaudo,
        substituirOuAcrescentarMensagemNoHistorico
    } = NS;

    const enviarMensagemEngenheiro = async () => {
        const texto = els.inputResposta.value.trim();
        const anexoPendente =
            obterArquivoAnexoRespostaSelecionado?.()
            || state.respostaAnexoPendente?.arquivo
            || null;
        const laudoId = Number(state.laudoAtivoId || 0) || null;
        return medirAsync("revisor.enviarMensagemEngenheiro", async () => {
            if ((!texto && !anexoPendente) || !laudoId || state.pendingSend) return;
            const referenciaMensagemId = Number(state.referenciaMensagemAtiva?.id) || null;

            if (anexoPendente && !state.respostaAnexoPendente) {
                sincronizarAnexoRespostaSelecionado?.(anexoPendente);
            }

            state.pendingSend = true;
            els.btnEnviarMsg.disabled = true;
            els.inputResposta.disabled = true;
            if (els.btnAnexoResposta) {
                els.btnAnexoResposta.disabled = true;
            }

            const bubble = renderMessageBubble({
                tipo: "humano_eng",
                texto,
                referencia_mensagem_id: referenciaMensagemId,
                data: "Enviando...",
                anexos: state.respostaAnexoPendente ? [{
                    id: -1,
                    nome: state.respostaAnexoPendente.nome,
                    url: "#",
                    eh_imagem: state.respostaAnexoPendente.ehImagem,
                    tamanho_bytes: state.respostaAnexoPendente.tamanho
                }] : []
            }, true);

            if (bubble) {
                els.timeline.appendChild(bubble);
                els.timeline.scrollTop = els.timeline.scrollHeight;
            }

            try {
                let res;
                let respostaPayload = null;
                if (anexoPendente) {
                    const form = new FormData();
                    form.set("arquivo", anexoPendente);
                    if (texto) {
                        form.set("texto", texto);
                    }
                    if (referenciaMensagemId) {
                        form.set("referencia_mensagem_id", String(referenciaMensagemId));
                    }

                    res = await fetch(`/revisao/api/laudo/${laudoId}/responder-anexo`, {
                        method: "POST",
                        headers: {
                            "X-CSRF-Token": tokenCsrf,
                            "X-Requested-With": "XMLHttpRequest"
                        },
                        body: form
                    });
                } else {
                    res = await fetch(`/revisao/api/laudo/${laudoId}/responder`, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRF-Token": tokenCsrf,
                            "X-Requested-With": "XMLHttpRequest"
                        },
                        body: JSON.stringify({
                            texto,
                            referencia_mensagem_id: referenciaMensagemId
                        })
                    });
                }

                if (!res.ok) {
                    throw new Error(`Falha HTTP ${res.status}`);
                }

                respostaPayload = await res.json().catch(() => null);

                if (Number(state.laudoAtivoId || 0) === laudoId) {
                    els.inputResposta.value = "";
                    const mensagemConfirmada = respostaPayload?.mensagem;
                    if (mensagemConfirmada && substituirOuAcrescentarMensagemNoHistorico(mensagemConfirmada)) {
                        renderTimeline({ rolarParaFim: true });
                    }
                    limparReferenciaMensagemAtiva();
                    limparAnexoResposta();
                    await carregarLaudo(laudoId, { forcar: true });
                }
                showStatus("Mensagem enviada para o inspetor.", "send");
            } catch (erro) {
                showStatus("Erro ao enviar mensagem.", "error");
                console.error("[Tariel] Falha ao responder:", erro);
                if (Number(state.laudoAtivoId || 0) === laudoId) {
                    await carregarLaudo(laudoId, { preservarComposer: true });
                }
            } finally {
                state.pendingSend = false;
                els.btnEnviarMsg.disabled = false;
                els.inputResposta.disabled = false;
                if (els.btnAnexoResposta) {
                    els.btnAnexoResposta.disabled = false;
                }
                els.inputResposta.focus();
            }
        }, { laudoId: Number(state.laudoAtivoId || 0) || 0, hasTexto: !!texto, hasAnexo: !!anexoPendente });
    };

    const lerFailureReasonsCoverage = (rawValue) => {
        const bruto = String(rawValue || "").trim();
        if (!bruto) return [];
        try {
            const decoded = decodeURIComponent(bruto);
            const parsed = JSON.parse(decoded);
            return Array.isArray(parsed) ? parsed.filter((item) => typeof item === "string" && item.trim()) : [];
        } catch (_erro) {
            return [];
        }
    };

    const solicitarRefazerCoverageMesaOperacional = async (elemento) => {
        const laudoId = Number(state.laudoAtivoId || 0) || null;
        const evidenceKey = String(elemento?.dataset?.evidenceKey || "").trim();
        if (!laudoId || !evidenceKey) return;

        const payload = {
            evidence_key: evidenceKey,
            title: String(elemento.dataset.title || "Item de cobertura").trim(),
            kind: String(elemento.dataset.kind || "coverage_item").trim(),
            required: String(elemento.dataset.required || "").toLowerCase() === "true",
            source_status: String(elemento.dataset.sourceStatus || "").trim() || null,
            operational_status: String(elemento.dataset.operationalStatus || "").trim() || null,
            mesa_status: String(elemento.dataset.mesaStatus || "").trim() || null,
            component_type: String(elemento.dataset.componentType || "").trim() || null,
            view_angle: String(elemento.dataset.viewAngle || "").trim() || null,
            summary: String(elemento.dataset.summary || "").trim() || null,
            failure_reasons: lerFailureReasonsCoverage(elemento.dataset.failureReasons)
        };

        elemento.disabled = true;
        try {
            const res = await fetch(`/revisao/api/laudo/${laudoId}/coverage/solicitar-refazer`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF-Token": tokenCsrf,
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: JSON.stringify(payload)
            });
            if (!res.ok) {
                throw new Error(`Falha HTTP ${res.status}`);
            }

            const resposta = await res.json().catch(() => null);
            if (Number(state.laudoAtivoId || 0) === laudoId) {
                const mensagem = resposta?.mensagem;
                if (mensagem && substituirOuAcrescentarMensagemNoHistorico(mensagem)) {
                    renderTimeline({ rolarParaFim: true });
                }
                await carregarLaudo(laudoId, { forcar: true, preservarComposer: true });
            }
            showStatus("Refazer enviado ao inspetor.", "send");
        } catch (erro) {
            showStatus("Erro ao devolver item de coverage.", "error");
            console.error("[Tariel] Falha ao solicitar refazer de coverage:", erro);
        } finally {
            elemento.disabled = false;
        }
    };

    const confirmarDevolucao = async () => {
        return medirAsync("revisor.confirmarDevolucao", async () => {
            const motivo = els.inputMotivo.value.trim();
            const laudoId = Number(state.laudoAtivoId || 0) || null;
            if (!motivo || !laudoId) {
                els.inputMotivo.classList.add("erro");
                els.inputMotivo.focus();
                return;
            }

            els.btnConfirmarMotivo.disabled = true;
            els.btnConfirmarMotivo.textContent = "Devolvendo...";

            try {
                const fd = new FormData();
                fd.append("csrf_token", tokenCsrf);
                fd.append("acao", "rejeitar");
                fd.append("motivo", motivo);

                const res = await fetch(`/revisao/api/laudo/${laudoId}/avaliar`, {
                    method: "POST",
                    body: fd
                });

                if (!res.ok) {
                    throw new Error(`Falha HTTP ${res.status}`);
                }

                window.location.reload();
            } catch (erro) {
                els.btnConfirmarMotivo.disabled = false;
                els.btnConfirmarMotivo.textContent = "Confirmar Devolução";
                showStatus("Erro ao devolver laudo.", "error");
                console.error("[Tariel] Falha ao devolver:", erro);
            }
        }, { laudoId: Number(state.laudoAtivoId || 0) || 0 });
    };

    Object.assign(NS, {
        enviarMensagemEngenheiro,
        solicitarRefazerCoverageMesaOperacional,
        confirmarDevolucao
    });
})();
