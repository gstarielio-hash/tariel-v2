// ==========================================
// TARIEL.IA — REVISOR_PAINEL_APRENDIZADOS.JS
// Papel: revisão e validação dos aprendizados visuais do laudo.
// ==========================================

(function () {
    "use strict";

    const NS = window.TarielRevisorPainel;
    if (!NS || NS.__aprendizadosWired__) return;
    NS.__aprendizadosWired__ = true;

    const {
        els,
        state,
        escapeHtml,
        nl2br,
        formatarDataHora,
        medirSync,
        sincronizarPlaceholderContextoMesa,
        snapshotDOM
    } = NS;

    const LABEL_STATUS = {
        rascunho_inspetor: "Rascunho do Inspetor",
        validado_mesa: "Validado pela Mesa",
        rejeitado_mesa: "Rejeitado pela Mesa"
    };

    const LABEL_VEREDITO = {
        conforme: "Conforme",
        nao_conforme: "Não conforme",
        ajuste: "Ajuste",
        duvida: "Dúvida"
    };

    const normalizarLista = (valor) => Array.isArray(valor) ? valor.filter(Boolean).map((item) => String(item).trim()).filter(Boolean) : [];

    const contarStatus = (itens = []) => itens.reduce((acc, item) => {
        const status = String(item?.status || "rascunho_inspetor");
        acc.total += 1;
        if (status === "validado_mesa") acc.validados += 1;
        else if (status === "rejeitado_mesa") acc.rejeitados += 1;
        else acc.rascunhos += 1;
        return acc;
    }, { total: 0, rascunhos: 0, validados: 0, rejeitados: 0 });

    const renderizarTagsAprendizado = (rotulo, itens, classeExtra = "") => {
        const lista = normalizarLista(itens);
        if (!lista.length) return "";
        return `
            <div class="aprendizado-tags-grupo ${classeExtra}">
                <span class="aprendizado-tags-rotulo">${escapeHtml(rotulo)}</span>
                <div class="aprendizado-tags-lista">
                    ${lista.map((item) => `<span class="aprendizado-tag">${escapeHtml(item)}</span>`).join("")}
                </div>
            </div>
        `;
    };

    const renderizarMetadadosAprendizado = (item) => {
        const itens = [];
        if (Number(item?.mensagem_referencia_id || 0) > 0) {
            itens.push(`<button type="button" class="aprendizado-meta-link" data-aprendizado-action="timeline-ref" data-ref-id="${Number(item.mensagem_referencia_id)}">Mensagem #${Number(item.mensagem_referencia_id)}</button>`);
        }
        if (item?.criado_em) {
            itens.push(`<span>Criado em ${escapeHtml(formatarDataHora(item.criado_em))}</span>`);
        }
        if (item?.validado_em) {
            itens.push(`<span>Revisado em ${escapeHtml(formatarDataHora(item.validado_em))}</span>`);
        }
        return itens.length ? `<div class="aprendizado-meta">${itens.join("")}</div>` : "";
    };

    const renderizarCardAprendizado = (item) => {
        const status = String(item?.status || "rascunho_inspetor");
        const vereditoAtual = String(item?.veredito_mesa || item?.veredito_inspetor || "");
        const resumo = String(item?.resumo || "Aprendizado visual").trim() || "Aprendizado visual";
        const correcaoInspetor = String(item?.correcao_inspetor || "").trim();
        const sinteseMesa = String(item?.sintese_consolidada || item?.parecer_mesa || "").trim();
        const descricao = String(item?.descricao_contexto || "").trim();
        const imagemUrl = String(item?.imagem_url || "").trim();
        const nomeImagem = String(item?.imagem_nome_original || "evidencia").trim() || "evidencia";
        const editorAberto = status === "rascunho_inspetor";
        const tituloEditor = editorAberto ? "Validar aprendizado" : "Revisar decisão";
        const descricaoEditor = editorAberto
            ? "Defina o veredito final e a sintese que deve ficar registrada para orientar casos parecidos."
            : "Abra apenas se precisar ajustar a decisão já registrada pela mesa.";

        return `
            <article class="aprendizado-card" data-aprendizado-id="${Number(item.id)}">
                <div class="aprendizado-card-topo">
                    <div class="aprendizado-card-media ${imagemUrl ? "tem-imagem" : "sem-imagem"}">
                        ${imagemUrl
                            ? `<a href="${escapeHtml(imagemUrl)}" target="_blank" rel="noopener noreferrer" class="aprendizado-card-thumb-link" aria-label="Abrir evidência ${escapeHtml(nomeImagem)}"><img src="${escapeHtml(imagemUrl)}" alt="${escapeHtml(nomeImagem)}" class="aprendizado-card-thumb"></a>`
                            : `<span class="material-symbols-rounded" aria-hidden="true">image</span>`}
                    </div>
                    <div class="aprendizado-card-head">
                        <div class="aprendizado-card-head-topo">
                            <div>
                                <h3>${escapeHtml(resumo)}</h3>
                                <p>${escapeHtml(LABEL_STATUS[status] || "Aprendizado visual")}</p>
                            </div>
                            <span class="aprendizado-status ${escapeHtml(status)}">${escapeHtml(LABEL_STATUS[status] || status)}</span>
                        </div>
                        ${renderizarMetadadosAprendizado(item)}
                    </div>
                </div>

                <div class="aprendizado-card-corpo">
                    <section class="aprendizado-bloco">
                        <header>
                            <span class="material-symbols-rounded" aria-hidden="true">construction</span>
                            <strong>Leitura do campo</strong>
                        </header>
                        <p>${correcaoInspetor ? nl2br(correcaoInspetor) : "Sem correção textual explícita do inspetor."}</p>
                    </section>
                    <section class="aprendizado-bloco aprendizado-bloco-mesa">
                        <header>
                            <span class="material-symbols-rounded" aria-hidden="true">rule</span>
                            <strong>Referência final da mesa</strong>
                        </header>
                        <p>${sinteseMesa ? nl2br(sinteseMesa) : "Ainda sem sintese consolidada da mesa."}</p>
                    </section>
                </div>

                ${descricao ? `<div class="aprendizado-contexto">${nl2br(descricao)}</div>` : ""}
                <div class="aprendizado-tags-wrap">
                    ${renderizarTagsAprendizado("Pontos-chave", item?.pontos_chave)}
                    ${renderizarTagsAprendizado("Normas", item?.referencias_norma, "normas")}
                </div>

                <details class="aprendizado-editor" ${editorAberto ? "open" : ""}>
                    <summary class="aprendizado-editor-resumo">
                        <div class="aprendizado-editor-resumo-texto">
                            <strong>${escapeHtml(tituloEditor)}</strong>
                            <span>${escapeHtml(descricaoEditor)}</span>
                        </div>
                        <span class="material-symbols-rounded" aria-hidden="true">expand_more</span>
                    </summary>

                    <div class="aprendizado-formulario">
                        <div class="aprendizado-form-grid">
                            <label class="aprendizado-campo">
                                <span>Resumo final</span>
                                <input
                                    type="text"
                                    class="js-aprendizado-resumo-final"
                                    maxlength="240"
                                    value="${escapeHtml(String(item?.resumo || ""))}"
                                    placeholder="Resumo curto para a base"
                                >
                            </label>
                            <label class="aprendizado-campo">
                                <span>Veredito final</span>
                                <select class="js-aprendizado-veredito">
                                    <option value="">Selecionar</option>
                                    ${Object.entries(LABEL_VEREDITO).map(([valor, rotulo]) => `
                                        <option value="${escapeHtml(valor)}" ${vereditoAtual === valor ? "selected" : ""}>${escapeHtml(rotulo)}</option>
                                    `).join("")}
                                </select>
                            </label>
                        </div>

                        <label class="aprendizado-campo">
                            <span>Sintese validada para uso futuro</span>
                            <textarea class="js-aprendizado-sintese" rows="3" placeholder="Descreva a regra final que deve ser reutilizada.">${escapeHtml(String(item?.sintese_consolidada || ""))}</textarea>
                        </label>

                        <label class="aprendizado-campo">
                            <span>Observação da mesa</span>
                            <textarea class="js-aprendizado-parecer" rows="2" placeholder="Notas internas da validação.">${escapeHtml(String(item?.parecer_mesa || ""))}</textarea>
                        </label>

                        <div class="aprendizado-acoes">
                            ${imagemUrl ? `<a href="${escapeHtml(imagemUrl)}" target="_blank" rel="noopener noreferrer" class="btn btn-ver aprendizado-btn-link">
                                <span class="material-symbols-rounded" aria-hidden="true">open_in_new</span>
                                <span>Ver imagem</span>
                            </a>` : ""}
                            <button type="button" class="btn btn-ver aprendizado-btn-link" data-aprendizado-action="timeline-ref" data-ref-id="${Number(item?.mensagem_referencia_id || 0) || ""}" ${Number(item?.mensagem_referencia_id || 0) > 0 ? "" : "disabled"}>
                                <span class="material-symbols-rounded" aria-hidden="true">forum</span>
                                <span>Ir para contexto</span>
                            </button>
                            <button type="button" class="btn btn-rejeitar js-aprendizado-rejeitar" data-aprendizado-action="rejeitar">
                                <span class="material-symbols-rounded" aria-hidden="true">close</span>
                                <span>Rejeitar</span>
                            </button>
                            <button type="button" class="btn btn-aprovar js-aprendizado-aprovar" data-aprendizado-action="aprovar">
                                <span class="material-symbols-rounded" aria-hidden="true">check</span>
                                <span>Validar</span>
                            </button>
                        </div>
                    </div>
                </details>
            </article>
        `;
    };

    const renderizarPainelAprendizadosVisuais = (itens = []) => {
        medirSync("revisor.renderizarPainelAprendizadosVisuais", () => {
            const lista = Array.isArray(itens) ? itens : [];
            state.aprendizadosVisuais = [...lista];

            if (!els.aprendizadosVisuaisPainel || !els.aprendizadosVisuaisConteudo) return;

            if (!lista.length) {
                els.aprendizadosVisuaisPainel.hidden = true;
                els.aprendizadosVisuaisConteudo.innerHTML = "";
                sincronizarPlaceholderContextoMesa?.();
                return;
            }

            const resumo = contarStatus(lista);
            els.aprendizadosVisuaisConteudo.innerHTML = `
                <div class="aprendizados-topo">
                    <div>
                        <h3>Aprendizados Visuais</h3>
                        <p>Revise o que foi capturado no chat e valide o que deve ficar registrado para consultas futuras.</p>
                    </div>
                    <div class="aprendizados-resumo">
                        <span><strong>${escapeHtml(String(resumo.total))}</strong> total</span>
                        <span><strong>${escapeHtml(String(resumo.rascunhos))}</strong> rascunho(s)</span>
                        <span><strong>${escapeHtml(String(resumo.validados))}</strong> validado(s)</span>
                        <span><strong>${escapeHtml(String(resumo.rejeitados))}</strong> rejeitado(s)</span>
                    </div>
                </div>
                <div class="aprendizados-lista">
                    ${lista.map((item) => renderizarCardAprendizado(item)).join("")}
                </div>
            `;
            els.aprendizadosVisuaisPainel.hidden = false;
            sincronizarPlaceholderContextoMesa?.();
            snapshotDOM(`revisor:aprendizados:${Number(state.laudoAtivoId || 0) || 0}`);
        }, { laudoId: Number(state.laudoAtivoId || 0) || 0, total: Array.isArray(itens) ? itens.length : 0 }, "render");
    };

    Object.assign(NS, {
        renderizarPainelAprendizadosVisuais
    });
})();
