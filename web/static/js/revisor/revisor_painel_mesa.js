// ==========================================
// TARIEL.IA — REVISOR_PAINEL_MESA.JS
// Papel: operação da mesa e pacote técnico no painel do revisor.
// ==========================================

(function () {
    "use strict";

    const NS = window.TarielRevisorPainel;
    if (!NS || NS.__mesaWired__) return;
    NS.__mesaWired__ = true;

    const {
        tokenCsrf,
        els,
        state,
        showStatus,
        obterPacoteMesaLaudo,
        atualizarIndicadoresListaLaudo,
        ehAbortError,
        obterContextoLaudoAtivo,
        contextoLaudoAindaValido,
        medirAsync,
    } = NS;

    const adaptarReviewerCaseViewParaPainelMesa = (projection) => {
        const payload = (
            projection?.payload && typeof projection.payload === "object"
                ? projection.payload
                : projection
        );
        if (!payload || typeof payload !== "object") {
            return null;
        }
        return {
            codigo_hash: payload.codigo_hash,
            tipo_template: payload.tipo_template,
            setor_industrial: payload.setor_industrial,
            criado_em: payload.created_at,
            ultima_interacao_em: payload.last_interaction_at,
            tempo_em_campo_minutos: Number(payload.field_time_minutes || 0) || 0,
            resumo_pendencias: payload.summary_pending || {},
            revisao_por_bloco: payload.revisao_por_bloco || null,
            coverage_map: payload.coverage_map || null,
            historico_inspecao: payload.inspection_history || payload.historico_inspecao || null,
            verificacao_publica: payload.public_verification || payload.verificacao_publica || null,
            anexo_pack: payload.anexo_pack || null,
            emissao_oficial: payload.emissao_oficial || null,
            historico_refazer_inspetor: Array.isArray(payload.historico_refazer_inspetor)
                ? payload.historico_refazer_inspetor
                : [],
            memoria_operacional_familia: payload.memoria_operacional_familia || null,
            policy_summary: payload.policy_summary || null,
            collaboration: payload.collaboration || null,
            pendencias_abertas: Array.isArray(payload.open_pendencies) ? payload.open_pendencies : [],
            pendencias_resolvidas_recentes: Array.isArray(payload.recent_resolved_pendencies)
                ? payload.recent_resolved_pendencies
                : [],
            whispers_recentes: Array.isArray(payload.recent_whispers) ? payload.recent_whispers : []
        };
    };

    const atualizarPendenciaMesaOperacional = async (mensagemId, lida) => {
        return medirAsync("revisor.atualizarPendenciaMesaOperacional", async () => {
            const contexto = obterContextoLaudoAtivo();
            const laudoId = Number(contexto.laudoId || 0);
            const msgId = Number(mensagemId || 0);
            if (!Number.isFinite(laudoId) || laudoId <= 0 || !Number.isFinite(msgId) || msgId <= 0) {
                return;
            }

            try {
                const res = await fetch(`/revisao/api/laudo/${laudoId}/pendencias/${msgId}`, {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRF-Token": tokenCsrf,
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: JSON.stringify({ lida: !!lida })
                });
                if (!res.ok) {
                    throw new Error(`Falha HTTP ${res.status}`);
                }

                const payload = await res.json();
                if (!contextoLaudoAindaValido(contexto)) {
                    return;
                }
                atualizarIndicadoresListaLaudo(laudoId, {
                    pendenciasAbertas: Number(payload?.pendencias_abertas || 0) || 0
                });
                await carregarPainelMesaOperacional({ forcar: true });
                showStatus(
                    lida ? "Pendência marcada como resolvida." : "Pendência reaberta.",
                    lida ? "task_alt" : "restart_alt"
                );
            } catch (erro) {
                showStatus("Erro ao atualizar pendência da mesa.", "error");
                console.error("[Tariel] Falha ao atualizar pendência da mesa:", erro);
            }
        }, { mensagemId: Number(mensagemId || 0) || 0, lida: !!lida });
    };

    const carregarPainelMesaOperacional = async ({ forcar = false } = {}) => {
        return medirAsync("revisor.carregarPainelMesaOperacional", async () => {
            const contexto = obterContextoLaudoAtivo();
            if (!els.mesaOperacaoPainel || !els.mesaOperacaoConteudo || !contexto.laudoId) return;

            if (
                !forcar
                && state.reviewerCaseViewPreferred
                && state.reviewerCaseViewLaudoId === contexto.laudoId
            ) {
                const pacotePreferencial = adaptarReviewerCaseViewParaPainelMesa(state.reviewerCaseViewAtivo);
                if (pacotePreferencial) {
                    NS.renderizarPainelMesaOperacional?.(pacotePreferencial);
                    return;
                }
            }

            els.mesaOperacaoPainel.hidden = false;
            els.mesaOperacaoConteudo.innerHTML = `
                <div class="mesa-operacao-topo">
                    <div>
                        <h3>Operação da Mesa</h3>
                        <p>Carregando pendencias, resolucoes e chamados do laudo...</p>
                    </div>
                </div>
            `;

            try {
                const pacote = await obterPacoteMesaLaudo({ forcar });
                if (!contextoLaudoAindaValido(contexto)) {
                    return;
                }
                NS.renderizarPainelMesaOperacional?.(pacote);
            } catch (erro) {
                if (ehAbortError(erro) || !contextoLaudoAindaValido(contexto)) {
                    return;
                }
                els.mesaOperacaoConteudo.innerHTML = `
                    <div class="mesa-operacao-topo">
                        <div>
                            <h3>Operação da Mesa</h3>
                            <p>Não foi possível carregar o pacote operacional da mesa agora.</p>
                        </div>
                    </div>
                `;
                console.error("[Tariel] Falha ao renderizar painel operacional da mesa:", erro);
            }
        }, { laudoId: Number(state.laudoAtivoId || 0) || 0, forcar });
    };

    Object.assign(NS, {
        atualizarPendenciaMesaOperacional,
        carregarPainelMesaOperacional
    });
})();
