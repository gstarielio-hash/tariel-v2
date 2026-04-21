// ==========================================
// TARIEL.IA — REVISOR_PAINEL_PACOTE.JS
// Papel: ações de pacote técnico e emissão oficial no painel do revisor.
// ==========================================

(function () {
    "use strict";

    const NS = window.TarielRevisorPainel;
    if (!NS || NS.__pacoteWired__) return;
    NS.__pacoteWired__ = true;

    const {
        tokenCsrf,
        els,
        state,
        escapeHtml,
        formatarDataHora,
        normalizarAnexoMensagem,
        resumoMensagem,
        showStatus,
        downloadJson,
        obterPacoteMesaLaudo,
        openModal,
        ehAbortError,
        obterContextoLaudoAtivo,
        contextoLaudoAindaValido,
        userCapabilityEnabled,
        tenantCapabilityReason,
        renderStructuredDocumentOverview,
        medirSync,
        medirAsync,
        snapshotDOM
    } = NS;

    const renderListaPacote = (itens, mensagemVazia) => {
        if (!Array.isArray(itens) || !itens.length) {
            return `<li>${escapeHtml(mensagemVazia || "Sem registros no momento.")}</li>`;
        }

        return itens.slice(0, 8).map((item) => {
            const anexos = Array.isArray(item?.anexos) ? item.anexos.map(normalizarAnexoMensagem).filter(Boolean) : [];
            const texto = resumoMensagem(item?.texto || (anexos.length ? "Anexo enviado" : ""));
            const data = formatarDataHora(item?.criado_em);
            const tipo = String(item?.tipo || "mensagem");
            const status = item?.resolvida_em
                ? `Resolvida em ${formatarDataHora(item.resolvida_em)}`
                : "Aberta";
            const infoAnexos = anexos.length
                ? `<span class="meta">Anexos: ${escapeHtml(anexos.map((anexo) => anexo.nome).join(", "))}</span>`
                : "";

            return `
                <li>
                    <strong>#${escapeHtml(String(item?.id || "-"))} · ${escapeHtml(tipo)}</strong><br>
                    ${escapeHtml(texto)}
                    <span class="meta">${escapeHtml(data)} · ${escapeHtml(status)}</span>
                    ${infoAnexos}
                </li>
            `;
        }).join("");
    };

    const renderizarModalPacote = (pacote) => {
        if (!pacote || typeof pacote !== "object") {
            els.modalPacoteConteudo.innerHTML = "<p>Pacote técnico indisponível para este laudo.</p>";
            return;
        }

        const resumoMensagens = pacote.resumo_mensagens || {};
        const resumoEvidencias = pacote.resumo_evidencias || {};
        const resumoPendencias = pacote.resumo_pendencias || {};
        const hashCurto = String(pacote.codigo_hash || "").slice(-6) || "-";
        const documentoEstruturado = pacote.documento_estruturado || null;

        els.modalPacoteConteudo.innerHTML = `
            <div class="pacote-meta">
                <strong>Laudo #${escapeHtml(hashCurto)}</strong> ·
                Modelo ${escapeHtml(String(pacote.tipo_template || "").toUpperCase())} ·
                Setor ${escapeHtml(String(pacote.setor_industrial || "-"))} ·
                Última interação: ${escapeHtml(formatarDataHora(pacote.ultima_interacao_em))}
            </div>

            <div class="pacote-grid">
                <section class="pacote-card">
                    <h4>Mensagens</h4>
                    <div class="pacote-kpi"><span>Total</span><strong>${escapeHtml(String(resumoMensagens.total || 0))}</strong></div>
                    <div class="pacote-kpi"><span>Inspetor</span><span>${escapeHtml(String(resumoMensagens.inspetor || 0))}</span></div>
                    <div class="pacote-kpi"><span>Assistente</span><span>${escapeHtml(String(resumoMensagens.ia || 0))}</span></div>
                    <div class="pacote-kpi"><span>Mesa</span><span>${escapeHtml(String(resumoMensagens.mesa || 0))}</span></div>
                </section>

                <section class="pacote-card">
                    <h4>Evidências</h4>
                    <div class="pacote-kpi"><span>Total</span><strong>${escapeHtml(String(resumoEvidencias.total || 0))}</strong></div>
                    <div class="pacote-kpi"><span>Textuais</span><span>${escapeHtml(String(resumoEvidencias.textuais || 0))}</span></div>
                    <div class="pacote-kpi"><span>Fotos</span><span>${escapeHtml(String(resumoEvidencias.fotos || 0))}</span></div>
                    <div class="pacote-kpi"><span>Documentos</span><span>${escapeHtml(String(resumoEvidencias.documentos || 0))}</span></div>
                </section>

                <section class="pacote-card">
                    <h4>Pendências</h4>
                    <div class="pacote-kpi"><span>Total</span><strong>${escapeHtml(String(resumoPendencias.total || 0))}</strong></div>
                    <div class="pacote-kpi"><span>Abertas</span><span>${escapeHtml(String(resumoPendencias.abertas || 0))}</span></div>
                    <div class="pacote-kpi"><span>Resolvidas</span><span>${escapeHtml(String(resumoPendencias.resolvidas || 0))}</span></div>
                    <div class="pacote-kpi"><span>Tempo em campo</span><span>${escapeHtml(String(pacote.tempo_em_campo_minutos || 0))} min</span></div>
                </section>
            </div>

            ${renderStructuredDocumentOverview(documentoEstruturado)}

            <h3 style="margin:0 0 10px; color:var(--cor-secundaria);">Pendências Abertas</h3>
            <ul class="pacote-lista">${renderListaPacote(pacote.pendencias_abertas, "Sem pendências abertas.")}</ul>

            <h3 style="margin:18px 0 10px; color:var(--cor-secundaria);">Chamados Recentes</h3>
            <ul class="pacote-lista">${renderListaPacote(pacote.whispers_recentes, "Sem chamados registrados.")}</ul>
        `;
    };

    const acionarDownloadMesa = (url) => {
        const link = document.createElement("a");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener";
        document.body.appendChild(link);
        link.click();
        link.remove();
    };

    const abrirResumoPacoteMesa = async () => {
        return medirAsync("revisor.abrirResumoPacoteMesa", async () => {
            const contexto = obterContextoLaudoAtivo();
            if (!contexto.laudoId) return;
            try {
                showStatus("Carregando pacote técnico...", "sync");
                const pacote = await obterPacoteMesaLaudo({ forcar: true });
                if (!contextoLaudoAindaValido(contexto) || !pacote) {
                    return;
                }
                renderizarModalPacote(pacote);
                openModal(els.modalPacote, els.btnFecharPacote);
                snapshotDOM(`revisor:modal-pacote:${contexto.laudoId}`);
            } catch (erro) {
                if (ehAbortError(erro) || !contextoLaudoAindaValido(contexto)) {
                    return;
                }
                showStatus("Erro ao carregar pacote técnico.", "error");
                console.error("[Tariel] Falha ao carregar pacote técnico:", erro);
            }
        }, { laudoId: Number(state.laudoAtivoId || 0) || 0 });
    };

    const baixarPacoteMesaJson = async () => {
        return medirAsync("revisor.baixarPacoteMesaJson", async () => {
            const contexto = obterContextoLaudoAtivo();
            if (!contexto.laudoId) return;
            try {
                const pacote = await obterPacoteMesaLaudo({ forcar: false });
                if (!pacote) return;
                const hashCurto = String(pacote.codigo_hash || state.laudoAtivoId).slice(-6);
                downloadJson(`pacote_mesa_${hashCurto}.json`, pacote);
                showStatus("Dados do caso baixados.", "download_done");
            } catch (erro) {
                if (ehAbortError(erro) || !contextoLaudoAindaValido(contexto)) {
                    return;
                }
                showStatus("Erro ao baixar pacote de dados.", "error");
                console.error("[Tariel] Falha ao baixar pacote de dados:", erro);
            }
        }, { laudoId: Number(state.laudoAtivoId || 0) || 0 });
    };

    const baixarPacoteMesaPdf = () => {
        medirSync("revisor.baixarPacoteMesaPdf", () => {
            const contexto = obterContextoLaudoAtivo();
            if (!contexto.laudoId) return;
            if (!userCapabilityEnabled("reviewer_decision")) {
                showStatus(tenantCapabilityReason("reviewer_decision"), "warning");
                return;
            }
            acionarDownloadMesa(`/revisao/api/laudo/${contexto.laudoId}/pacote/exportar-pdf`);
            showStatus("Gerando PDF do pacote...", "picture_as_pdf");
        }, { laudoId: Number(state.laudoAtivoId || 0) || 0 });
    };

    const baixarPacoteMesaOficial = () => {
        medirSync("revisor.baixarPacoteMesaOficial", () => {
            const contexto = obterContextoLaudoAtivo();
            if (!contexto.laudoId) return;
            if (!userCapabilityEnabled("reviewer_issue")) {
                showStatus(tenantCapabilityReason("reviewer_issue"), "warning");
                return;
            }
            acionarDownloadMesa(`/revisao/api/laudo/${contexto.laudoId}/pacote/exportar-oficial`);
            showStatus("Gerando ZIP oficial...", "folder_zip");
        }, { laudoId: Number(state.laudoAtivoId || 0) || 0 });
    };

    const baixarEmissaoOficialCongelada = () => {
        medirSync("revisor.baixarEmissaoOficialCongelada", () => {
            const contexto = obterContextoLaudoAtivo();
            if (!contexto.laudoId) return;
            if (!userCapabilityEnabled("reviewer_issue")) {
                showStatus(tenantCapabilityReason("reviewer_issue"), "warning");
                return;
            }
            acionarDownloadMesa(`/revisao/api/laudo/${contexto.laudoId}/emissao-oficial/download`);
            showStatus("Baixando bundle oficial congelado...", "folder_zip");
        }, { laudoId: Number(state.laudoAtivoId || 0) || 0 });
    };

    const emitirOficialmenteMesa = async ({
        signatoryId,
        signatoryName,
        expectedCurrentIssueId,
        expectedCurrentIssueNumber
    } = {}) => {
        return medirAsync("revisor.emitirOficialmenteMesa", async () => {
            const contexto = obterContextoLaudoAtivo();
            if (!contexto.laudoId) return null;
            if (!userCapabilityEnabled("reviewer_issue")) {
                showStatus(tenantCapabilityReason("reviewer_issue"), "warning");
                return null;
            }
            const response = await fetch(`/revisao/api/laudo/${contexto.laudoId}/emissao-oficial`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF-Token": tokenCsrf,
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: JSON.stringify({
                    signatory_id: Number(signatoryId || 0) || null,
                    expected_current_issue_id: Number(expectedCurrentIssueId || 0) || null,
                    expected_current_issue_number: String(expectedCurrentIssueNumber || "").trim() || null
                })
            });
            const payload = await response.json().catch(() => null);
            if (!response.ok) {
                throw new Error(payload?.detail || `Falha HTTP ${response.status}`);
            }
            const rotulo = signatoryName ? ` com ${signatoryName}` : "";
            const supersededIssueNumber = String(payload?.superseded_issue_number || "").trim();
            showStatus(
                payload?.idempotent_replay
                    ? (
                        supersededIssueNumber
                            ? `Reemissão oficial já existia${rotulo}, substituindo ${supersededIssueNumber}.`
                            : `Emissão oficial já existia${rotulo}.`
                    )
                    : (
                        payload?.reissued
                            ? `Reemissão oficial registrada${rotulo}, substituindo ${supersededIssueNumber || "a emissão anterior"}.`
                            : `Emissão oficial registrada${rotulo}.`
                    ),
                "task_alt"
            );
            return payload;
        }, { laudoId: Number(state.laudoAtivoId || 0) || 0 });
    };

    Object.assign(NS, {
        renderListaPacote,
        renderizarModalPacote,
        abrirResumoPacoteMesa,
        baixarPacoteMesaJson,
        baixarPacoteMesaPdf,
        baixarPacoteMesaOficial,
        baixarEmissaoOficialCongelada,
        emitirOficialmenteMesa
    });
})();
