// ==========================================
// TARIEL.IA — REVISOR_PAINEL_DOCUMENTO.JS
// Papel: leitura e apresentação do documento estruturado no painel do revisor.
// ==========================================

(function () {
    "use strict";

    const NS = window.TarielRevisorPainel;
    if (!NS || NS.__documentoWired__) return;
    NS.__documentoWired__ = true;

    const {
        els,
        state,
        escapeHtml,
        nl2br
    } = NS;

    const STRUCTURED_DOCUMENT_STATUS_META = {
        filled: { label: "Preenchida", className: "filled" },
        partial: { label: "Parcial", className: "partial" },
        attention: { label: "Atencao", className: "attention" },
        empty: { label: "Vazia", className: "empty" }
    };

    const STRUCTURED_DOCUMENT_SECTION_TITLES = {
        identificacao: "Identificacao",
        caracterizacao_do_equipamento: "Caracterizacao",
        inspecao_visual: "Inspecao visual",
        dispositivos_e_acessorios: "Dispositivos e acessorios",
        dispositivos_e_controles: "Dispositivos e controles",
        documentacao_e_registros: "Documentacao e registros",
        nao_conformidades: "Nao conformidades",
        recomendacoes: "Recomendacoes",
        conclusao: "Conclusao"
    };

    const structuredValueHasContent = (value) => {
        if (value === null || value === undefined) return false;
        if (typeof value === "boolean" || typeof value === "number") return true;
        if (typeof value === "string") return value.trim().length > 0;
        if (Array.isArray(value)) return value.some((item) => structuredValueHasContent(item));
        if (typeof value === "object") return Object.values(value).some((item) => structuredValueHasContent(item));
        return Boolean(value);
    };

    const structuredNormalizeText = (value, maxLength = 180) => {
        if (value === null || value === undefined) return "";
        const raw = String(value).replace(/\s+/g, " ").trim();
        if (!raw) return "";
        if (raw.length <= maxLength) return raw;
        return `${raw.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`;
    };

    const structuredHumanizeKey = (value) => {
        const text = String(value || "").trim().replace(/_/g, " ");
        if (!text) return "";
        return text.replace(/\b\w/g, (match) => match.toUpperCase());
    };

    const structuredJoin = (parts, separator = " | ") => parts.filter(Boolean).join(separator);

    const structuredConclusionLabel = (value) => {
        const status = String(value || "").trim().toLowerCase();
        if (!status) return "";
        const labels = {
            ajuste: "Ajuste",
            aprovado: "Aprovado",
            conforme: "Conforme",
            reprovado: "Reprovado",
            nao_conforme: "Nao conforme",
            bloqueado: "Bloqueado",
            pendente: "Pendente"
        };
        return labels[status] || structuredHumanizeKey(status);
    };

    const structuredArtifactSummary = (value) => {
        if (!value || typeof value !== "object") return "";
        const parts = [];
        if (typeof value.disponivel === "boolean") {
            parts.push(value.disponivel ? "Disponivel" : "Ausente");
        }
        ["descricao", "referencias_texto", "observacao"].forEach((key) => {
            const text = structuredNormalizeText(value[key], 180);
            if (text) parts.push(text);
        });
        return structuredJoin(parts);
    };

    const structuredFlattenSectionEntries = (block) => {
        const entries = [];

        const visit = (value, path = []) => {
            if (!structuredValueHasContent(value)) return;

            if (Array.isArray(value)) {
                const text = value
                    .map((item) => structuredNormalizeText(item, 120))
                    .filter(Boolean)
                    .join(", ");
                if (text) {
                    entries.push({
                        label: structuredHumanizeKey(path[path.length - 1] || "itens"),
                        value: text
                    });
                }
                return;
            }

            if (value && typeof value === "object") {
                const isArtifact = ["disponivel", "descricao", "referencias_texto", "observacao"].some((key) =>
                    Object.prototype.hasOwnProperty.call(value, key)
                );
                if (isArtifact) {
                    const text = structuredArtifactSummary(value);
                    if (text) {
                        entries.push({
                            label: structuredHumanizeKey(path[path.length - 1] || "item"),
                            value: text
                        });
                    }
                    return;
                }

                Object.entries(value).forEach(([key, nestedValue]) => {
                    visit(nestedValue, [...path, key]);
                });
                return;
            }

            if (typeof value === "boolean") {
                entries.push({
                    label: structuredHumanizeKey(path[path.length - 1] || "campo"),
                    value: value ? "Sim" : "Nao"
                });
                return;
            }

            const text = structuredNormalizeText(value, 180);
            if (!text) return;
            entries.push({
                label: structuredHumanizeKey(path[path.length - 1] || "campo"),
                value: text
            });
        };

        visit(block, []);
        return entries;
    };

    const structuredResolveSectionStatus = (key, block, entryCount) => {
        if (!entryCount) return "empty";
        if (key === "nao_conformidades" && block?.ha_nao_conformidades === true) return "attention";
        if (key === "conclusao") {
            const status = String(block?.status || "").trim().toLowerCase();
            if (["ajuste", "reprovado", "nao_conforme", "bloqueado"].includes(status)) {
                return "attention";
            }
        }
        if (entryCount <= 2) return "partial";
        return "filled";
    };

    const structuredSectionSummary = (key, block, entries) => {
        if (key === "nao_conformidades" && block?.ha_nao_conformidades === false) {
            return "Sem nao conformidades estruturadas.";
        }
        if (key === "conclusao") {
            return structuredJoin([
                structuredConclusionLabel(block?.status),
                structuredNormalizeText(block?.conclusao_tecnica, 160)
            ]);
        }
        if (key === "recomendacoes") {
            return structuredNormalizeText(block?.texto, 180);
        }
        if (key === "identificacao") {
            const identificador = Object.entries(block || {}).find(([entryKey, entryValue]) =>
                String(entryKey || "").startsWith("identificacao_") && structuredValueHasContent(entryValue)
            );
            return structuredJoin([
                structuredNormalizeText(identificador?.[1], 120),
                structuredNormalizeText(block?.localizacao, 120),
                structuredNormalizeText(block?.tag_patrimonial, 80)
            ]);
        }
        if (!Array.isArray(entries) || !entries.length) return "";
        return structuredJoin(
            entries.slice(0, 2).map((entry) => `${entry.label}: ${entry.value}`)
        );
    };

    const buildCanonicalReviewDocument = (data) => {
        if (!data || typeof data !== "object") return null;
        if (String(data.schema_type || "").trim().toLowerCase() !== "laudo_output") return null;

        const orderedSectionKeys = [
            "identificacao",
            "caracterizacao_do_equipamento",
            "inspecao_visual",
            "dispositivos_e_acessorios",
            "dispositivos_e_controles",
            "documentacao_e_registros",
            "nao_conformidades",
            "recomendacoes",
            "conclusao"
        ];

        const sections = orderedSectionKeys
            .filter((key) => data[key] && typeof data[key] === "object")
            .map((key) => {
                const block = data[key];
                const entries = structuredFlattenSectionEntries(block);
                return {
                    key,
                    title: STRUCTURED_DOCUMENT_SECTION_TITLES[key] || structuredHumanizeKey(key),
                    status: structuredResolveSectionStatus(key, block, entries.length),
                    summary: structuredSectionSummary(key, block, entries),
                    entries
                };
            });

        return {
            familyKey: String(data.family_key || "").trim(),
            summary: structuredNormalizeText(
                data.resumo_executivo
                    || data?.conclusao?.conclusao_tecnica
                    || data?.conclusao?.justificativa,
                220
            ),
            reviewNotes: structuredNormalizeText(
                data?.mesa_review?.pendencias_resolvidas_texto
                    || data?.mesa_review?.observacoes_mesa
                    || data?.mesa_review?.bloqueios_texto,
                220
            ),
            sections
        };
    };

    const renderStructuredDocumentChip = (status) => {
        const meta = STRUCTURED_DOCUMENT_STATUS_META[String(status || "").trim().toLowerCase()] || STRUCTURED_DOCUMENT_STATUS_META.empty;
        return `<span class="structured-document-chip ${escapeHtml(meta.className)}">${escapeHtml(meta.label)}</span>`;
    };

    const renderStructuredDocumentOverview = (documento) => {
        if (!documento || typeof documento !== "object") return "";
        const sections = Array.isArray(documento.sections) ? documento.sections : [];
        if (!sections.length) return "";

        return `
            <section class="structured-document-overview">
                <header class="structured-document-overview-topo">
                    <div>
                        <span class="structured-document-kicker">
                            ${escapeHtml(String(documento.family_label || documento.family_key || documento.schema_type || "laudo_output"))}
                        </span>
                            <h3>Leitura técnica organizada</h3>
                            <p>${escapeHtml(String(documento.summary || "Documento organizado em blocos técnicos para leitura da mesa."))}</p>
                    </div>
                    ${documento.family_key ? `<span class="structured-document-family-key">${escapeHtml(String(documento.family_key))}</span>` : ""}
                </header>
                ${documento.review_notes ? `<p class="structured-document-review-notes">Mesa: ${escapeHtml(String(documento.review_notes))}</p>` : ""}
                <div class="structured-document-grid">
                    ${sections.map((section) => `
                        <article class="structured-document-card">
                            <div class="structured-document-card-topo">
                                <div>
                                    <h4>${escapeHtml(String(section.title || structuredHumanizeKey(section.key || "secao")))}</h4>
                                    <p>${escapeHtml(String(section.summary || "Sem destaque adicional nesta secao."))}</p>
                                </div>
                                ${renderStructuredDocumentChip(section.status)}
                            </div>
                            <div class="structured-document-card-meta">
                                <span>${escapeHtml(String(section.filled_fields ?? section.entries?.length ?? 0))}/${escapeHtml(String(section.total_fields ?? section.entries?.length ?? 0))} campos preenchidos</span>
                                ${section.diff_short ? `<span>${escapeHtml(String(section.diff_short))}</span>` : "<span>Sem delta recente da mesa.</span>"}
                            </div>
                        </article>
                    `).join("")}
                </div>
            </section>
        `;
    };

    const renderStructuredDocumentInlinePanel = (documento) => {
        if (!documento || typeof documento !== "object") return "";
        const sections = Array.isArray(documento.sections) ? documento.sections : [];
        if (!sections.length) return "";

        return `
            <section class="view-structured-document-panel">
                <header class="view-structured-document-head">
                    <div>
                        <span class="view-structured-document-kicker">
                            ${escapeHtml(String(documento.family_label || documento.familyKey || documento.family_key || documento.schema_type || "laudo_output"))}
                        </span>
                        <h3>Leitura técnica do laudo</h3>
                        <p>${escapeHtml(String(documento.summary || "Painel por seção do laudo para apoiar a revisão."))}</p>
                    </div>
                    ${(documento.familyKey || documento.family_key) ? `<span class="view-structured-document-family-key">${escapeHtml(String(documento.familyKey || documento.family_key))}</span>` : ""}
                </header>
                ${(documento.reviewNotes || documento.review_notes) ? `
                    <p class="view-structured-document-note">
                        Mesa: ${escapeHtml(String(documento.reviewNotes || documento.review_notes))}
                    </p>
                ` : ""}
                <div class="view-structured-document-grid">
                    ${sections.map((section) => `
                        <article class="view-structured-document-card">
                            <div class="view-structured-document-card-topo">
                                <div>
                                    <h4>${escapeHtml(String(section.title || structuredHumanizeKey(section.key || "secao")))}</h4>
                                    <p>${escapeHtml(String(section.summary || "Sem destaque adicional nesta secao."))}</p>
                                </div>
                                ${renderStructuredDocumentChip(section.status)}
                            </div>
                            <div class="view-structured-document-card-meta">
                                <span>${escapeHtml(String(section.filled_fields ?? section.entries?.length ?? 0))}/${escapeHtml(String(section.total_fields ?? section.entries?.length ?? 0))} campos-chave</span>
                                ${section.diff_short ? `<span>${escapeHtml(String(section.diff_short))}</span>` : "<span>Sem observacao curta adicional.</span>"}
                            </div>
                        </article>
                    `).join("")}
                </div>
            </section>
        `;
    };

    const renderizarPainelDocumentoTecnicoInline = (pacote = null) => {
        if (!els.viewStructuredDocument) return;
        if (!state.laudoAtivoId) {
            els.viewStructuredDocument.hidden = true;
            els.viewStructuredDocument.innerHTML = "";
            return;
        }

        const documento = (
            pacote?.documento_estruturado
            || state.pacoteMesaAtivo?.documento_estruturado
            || buildCanonicalReviewDocument(state.jsonEstruturadoAtivo)
            || null
        );
        const html = renderStructuredDocumentInlinePanel(documento);

        if (!html) {
            els.viewStructuredDocument.hidden = true;
            els.viewStructuredDocument.innerHTML = "";
            return;
        }

        els.viewStructuredDocument.hidden = false;
        els.viewStructuredDocument.innerHTML = html;
    };

    const renderizarModalRelatorio = () => {
        if (!state.jsonEstruturadoAtivo) {
            els.modalConteudo.innerHTML = "<p>Sem dados estruturados.</p>";
            return;
        }

        const data = state.jsonEstruturadoAtivo;
        const documentoCanonico = buildCanonicalReviewDocument(data);
        if (documentoCanonico) {
            const secoes = Array.isArray(documentoCanonico.sections) ? documentoCanonico.sections : [];
            els.modalConteudo.innerHTML = `
                <div class="relatorio-canonical-header">
                    <div>
                        <span class="relatorio-canonical-kicker">
                            ${escapeHtml(documentoCanonico.familyKey || "laudo_output")}
                        </span>
                        <h3>Seções organizadas do laudo</h3>
                        <p>Leitura por seção do conteúdo estruturado para revisão técnica.</p>
                    </div>
                    <span class="relatorio-canonical-badge">
                        ${escapeHtml(String(secoes.length))} secao(oes)
                    </span>
                </div>
                ${documentoCanonico.summary ? `
                    <div class="relatorio-resumo">
                        <strong>Resumo executivo:</strong><br>
                        ${nl2br(documentoCanonico.summary)}
                    </div>
                ` : ""}
                ${documentoCanonico.reviewNotes ? `
                    <div class="relatorio-canonical-note">
                        <strong>Mesa:</strong> ${escapeHtml(documentoCanonico.reviewNotes)}
                    </div>
                ` : ""}
                <div class="relatorio-canonical-grid">
                    ${secoes.length ? secoes.map((section) => `
                        <article class="relatorio-section-card">
                            <div class="relatorio-section-topo">
                                <div>
                                    <h3>${escapeHtml(String(section.title || structuredHumanizeKey(section.key || "secao")))}</h3>
                                    <p>${escapeHtml(String(section.summary || "Sem destaque adicional nesta secao."))}</p>
                                </div>
                                ${renderStructuredDocumentChip(section.status)}
                            </div>
                            ${Array.isArray(section.entries) && section.entries.length ? `
                                <div class="relatorio-section-entries">
                                    ${section.entries.slice(0, 8).map((entry) => `
                                        <div class="relatorio-section-entry">
                                            <span>${escapeHtml(String(entry.label || "Campo"))}</span>
                                            <strong>${escapeHtml(String(entry.value || "-"))}</strong>
                                        </div>
                                    `).join("")}
                                    ${section.entries.length > 8 ? `<p class="relatorio-section-more">+${escapeHtml(String(section.entries.length - 8))} campo(s) adicionais neste bloco.</p>` : ""}
                                </div>
                            ` : `<p class="relatorio-section-empty">Sem dados estruturados nesta secao.</p>`}
                        </article>
                    `).join("") : `<p class="relatorio-section-empty">Nenhum bloco tecnico disponivel.</p>`}
                </div>
            `;
            return;
        }

        let html = "";

        if (data.resumo_executivo) {
            html += `
                <div class="relatorio-resumo">
                    <strong>Resumo do assistente:</strong><br>
                    ${nl2br(data.resumo_executivo)}
                </div>
            `;
        }

        const secoes = [
            { k: "seguranca_estrutural", t: "SEGURANÇA ESTRUTURAL" },
            { k: "cmar", t: "CMAR" }
        ];

        secoes.forEach((secao) => {
            const bloco = data[secao.k];
            if (!bloco) return;

            html += `<h3 style="color:var(--cor-secundaria); margin:20px 0 0;">${escapeHtml(secao.t)}</h3>`;
            html += `
                <table class="tabela-relatorio">
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th>Cond</th>
                            <th>Obs</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            Object.entries(bloco).forEach(([chave, valor]) => {
                if (!valor || !valor.condicao) return;
                const cond = String(valor.condicao).toUpperCase();
                const klass = cond === "C" ? "cond-C" : cond === "NC" ? "cond-NC" : "";

                html += `
                    <tr>
                        <td>${escapeHtml(chave.replace(/_/g, " ").toUpperCase())}</td>
                        <td class="${klass}">${escapeHtml(valor.condicao)}</td>
                        <td>${escapeHtml(valor.observacao || "-")}</td>
                    </tr>
                `;
            });

            html += `</tbody></table>`;
        });

        els.modalConteudo.innerHTML = html || "<p>Sem conteúdo estruturado disponível.</p>";
    };

    Object.assign(NS, {
        buildCanonicalReviewDocument,
        renderStructuredDocumentChip,
        renderStructuredDocumentOverview,
        renderizarPainelDocumentoTecnicoInline,
        renderizarModalRelatorio
    });
})();
