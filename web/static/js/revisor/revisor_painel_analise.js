// ==========================================
// TARIEL.IA — REVISOR_PAINEL_ANALISE.JS
// Papel: leitura analítica do contexto operacional no painel do revisor.
// ==========================================

(function () {
    "use strict";

    const NS = window.TarielRevisorPainel;
    if (!NS || NS.__analiseWired__) return;
    NS.__analiseWired__ = true;

    const {
        escapeHtml,
        formatarDataHora
    } = NS;

    const COVERAGE_STATUS_LABELS = {
        accepted: "Aceita",
        irregular: "Irregular",
        missing: "Faltando",
        collected: "Coletada",
        pending: "Pendente"
    };

    const COVERAGE_KIND_LABELS = {
        image_slot: "Imagem obrigatoria",
        gate_requirement: "Gate operacional",
        structured_form: "Formulario",
        normative_item: "Item normativo",
        gate: "Gate"
    };

    const OPERATIONAL_STATUS_LABELS = {
        ok: "OK operacional",
        irregular: "Irregular",
        replaced: "Substituida",
        pending: "Pendente"
    };

    const MESA_STATUS_LABELS = {
        accepted: "Aceita pela Mesa",
        rejected: "Rejeitada pela Mesa",
        needs_recheck: "Revalidar",
        not_reviewed: "Nao revisada"
    };

    const BLOCK_REVIEW_STATUS_LABELS = {
        returned: "Devolvido",
        attention: "Atencao",
        partial: "Parcial",
        ready: "Pronto",
        empty: "Vazio"
    };

    const humanizarSlugAnalise = (value) => {
        const text = String(value || "").trim().replace(/_/g, " ");
        if (!text) return "";
        return text.replace(/\b\w/g, (match) => match.toUpperCase());
    };

    const rotuloCoverageStatus = (status) =>
        COVERAGE_STATUS_LABELS[String(status || "").trim().toLowerCase()] || humanizarSlugAnalise(status || "pending");

    const rotuloCoverageKind = (kind) =>
        COVERAGE_KIND_LABELS[String(kind || "").trim().toLowerCase()] || humanizarSlugAnalise(kind || "item");

    const rotuloOperationalStatus = (status) =>
        OPERATIONAL_STATUS_LABELS[String(status || "").trim().toLowerCase()] || humanizarSlugAnalise(status || "pending");

    const rotuloMesaStatus = (status) =>
        MESA_STATUS_LABELS[String(status || "").trim().toLowerCase()] || humanizarSlugAnalise(status || "not_reviewed");

    const rotuloRevisaoBlocoStatus = (status) =>
        BLOCK_REVIEW_STATUS_LABELS[String(status || "").trim().toLowerCase()] || humanizarSlugAnalise(status || "empty");

    const rotuloTipoDiffHistorico = (status) => {
        const normalized = String(status || "").trim().toLowerCase();
        if (normalized === "added") return "Novo";
        if (normalized === "removed") return "Removido";
        return "Alterado";
    };

    const renderizarRevisaoPorBlocoMesa = (reviewByBlock) => {
        if (!reviewByBlock || typeof reviewByBlock !== "object") {
            return `
                <section class="mesa-operacao-card mesa-operacao-card--block-review">
                    <header>
                        <div>
                            <h4>Revisão por seção</h4>
                            <p>Sem leitura consolidada por bloco para este laudo ainda.</p>
                        </div>
                    </header>
                    <p class="mesa-operacao-vazio">A revisão por seção aparece quando o documento do caso e o contexto operacional já podem ser comparados.</p>
                </section>
            `;
        }

        const items = Array.isArray(reviewByBlock.items) ? reviewByBlock.items.slice(0, 8) : [];
        const body = items.length
            ? `
                <ul class="mesa-operacao-coverage-lista">
                    ${items.map((item) => {
                        const status = String(item?.review_status || "empty").trim().toLowerCase();
                        const meta = [
                            `Documento: ${humanizarSlugAnalise(item?.document_status || "empty")}`,
                            `${Number(item?.filled_fields || 0)}/${Number(item?.total_fields || 0)} campos`,
                            Number(item?.coverage_total || 0) > 0 ? `${Number(item.coverage_total)} evidência(s) relacionadas` : "",
                            Number(item?.coverage_alert_count || 0) > 0 ? `${Number(item.coverage_alert_count)} alerta(s)` : "",
                            Number(item?.open_pendency_count || 0) > 0 ? `${Number(item.open_pendency_count)} pendencia(s)` : "",
                            Number(item?.open_return_count || 0) > 0 ? `${Number(item.open_return_count)} refazer(es)` : ""
                        ].filter(Boolean).join(" | ");
                        const detalhes = [
                            item?.summary || "",
                            item?.diff_short ? `Destaque: ${item.diff_short}` : "",
                            item?.latest_return_at ? `Ultimo retorno: ${formatarDataHora(item.latest_return_at)}` : "",
                            item?.recommended_action ? `Acao: ${item.recommended_action}` : ""
                        ].filter(Boolean).join(" | ");
                        return `
                            <li class="mesa-operacao-coverage-item ${escapeHtml(status)}">
                                <div class="mesa-operacao-item-topo">
                                    <strong>${escapeHtml(String(item?.title || "Bloco"))}</strong>
                                    <span class="mesa-operacao-chip ${escapeHtml(status)}">${escapeHtml(rotuloRevisaoBlocoStatus(status))}</span>
                                </div>
                                ${meta ? `<p>${escapeHtml(meta)}</p>` : ""}
                                ${detalhes ? `<div class="mesa-operacao-meta"><span>${escapeHtml(detalhes)}</span></div>` : ""}
                            </li>
                        `;
                    }).join("")}
                </ul>
            `
            : '<p class="mesa-operacao-vazio">Nenhum bloco relevante foi materializado para revisao.</p>';

        return `
            <section class="mesa-operacao-card mesa-operacao-card--block-review">
                <header>
                    <div>
                        <h4>Revisão por seção</h4>
                        <p>Leitura operacional das seções do laudo, cruzando documento, evidências e devoluções ao campo.</p>
                    </div>
                </header>
                <div class="mesa-operacao-card-kpis">
                    <article>
                        <span>Blocos</span>
                        <strong>${escapeHtml(String(reviewByBlock.total_blocks || 0))}</strong>
                    </article>
                    <article>
                        <span>Prontos</span>
                        <strong>${escapeHtml(String(reviewByBlock.ready_blocks || 0))}</strong>
                    </article>
                    <article>
                        <span>Atencao</span>
                        <strong>${escapeHtml(String(reviewByBlock.attention_blocks || 0))}</strong>
                    </article>
                    <article>
                        <span>Devolvidos</span>
                        <strong>${escapeHtml(String(reviewByBlock.returned_blocks || 0))}</strong>
                    </article>
                </div>
                ${body}
            </section>
        `;
    };

    const renderizarCoverageMapMesa = (coverageMap) => {
        if (!coverageMap || typeof coverageMap !== "object") {
            return `
                <section class="mesa-operacao-card mesa-operacao-card--coverage">
                    <header>
                        <div>
                            <h4>Checklist de evidências</h4>
                            <p>Sem estrutura de evidências calculada para este laudo.</p>
                        </div>
                    </header>
                    <p class="mesa-operacao-vazio">Este checklist aparece quando o caso já tem evidências rastreáveis o bastante para revisão.</p>
                </section>
            `;
        }

        const items = Array.isArray(coverageMap.items) ? coverageMap.items.slice(0, 6) : [];
        const validationMode = String(coverageMap.final_validation_mode || "").trim();
        const body = items.length
            ? `
                <ul class="mesa-operacao-coverage-lista">
                    ${items.map((item) => {
                        const status = String(item?.status || "pending").trim().toLowerCase();
                        const requiredTag = item?.required
                            ? '<span class="mesa-operacao-inline-tag">Obrigatoria</span>'
                            : '<span class="mesa-operacao-inline-tag neutra">Opcional</span>';
                        const meta = [
                            rotuloCoverageKind(item?.kind),
                            item?.component_type ? `Componente: ${item.component_type}` : "",
                            item?.view_angle ? `Angulo: ${item.view_angle}` : "",
                            item?.quality_score !== null && item?.quality_score !== undefined ? `Qualidade ${item.quality_score}` : "",
                            item?.coherence_score !== null && item?.coherence_score !== undefined ? `Coerencia ${item.coherence_score}` : "",
                            item?.operational_status ? rotuloOperationalStatus(item.operational_status) : "",
                            item?.mesa_status ? rotuloMesaStatus(item.mesa_status) : ""
                        ].filter(Boolean).join(" | ");
                        const detalhes = [
                            item?.summary || "",
                            Array.isArray(item?.failure_reasons) && item.failure_reasons.length
                                ? `Alertas: ${item.failure_reasons.join(", ")}`
                                : "",
                            item?.replacement_evidence_key ? `Substituicao: ${item.replacement_evidence_key}` : ""
                        ].filter(Boolean).join(" | ");
                        const botaoRefazer = status !== "accepted"
                            ? `
                                <div class="mesa-operacao-item-acoes">
                                    <button
                                        type="button"
                                        class="btn-mesa-acao"
                                        data-mesa-action="solicitar-refazer-coverage"
                                        data-evidence-key="${escapeHtml(String(item?.evidence_key || ""))}"
                                        data-title="${escapeHtml(String(item?.title || "Item de cobertura"))}"
                                        data-kind="${escapeHtml(String(item?.kind || "coverage_item"))}"
                                        data-required="${item?.required ? "true" : "false"}"
                                        data-source-status="${escapeHtml(String(item?.source_status || ""))}"
                                        data-operational-status="${escapeHtml(String(item?.operational_status || ""))}"
                                        data-mesa-status="${escapeHtml(String(item?.mesa_status || ""))}"
                                        data-component-type="${escapeHtml(String(item?.component_type || ""))}"
                                        data-view-angle="${escapeHtml(String(item?.view_angle || ""))}"
                                        data-summary="${escapeHtml(String(item?.summary || ""))}"
                                        data-failure-reasons="${escapeHtml(encodeURIComponent(JSON.stringify(Array.isArray(item?.failure_reasons) ? item.failure_reasons : [])))}"
                                    >
                                        <span class="material-symbols-rounded" aria-hidden="true">assignment_return</span>
                                        <span>Solicitar ajuste ao inspetor</span>
                                    </button>
                                </div>
                            `
                            : "";
                        return `
                            <li class="mesa-operacao-coverage-item ${escapeHtml(status)}">
                                <div class="mesa-operacao-item-topo">
                                    <strong>${escapeHtml(String(item?.title || "Cobertura"))}</strong>
                                    <span class="mesa-operacao-chip ${escapeHtml(status)}">${escapeHtml(rotuloCoverageStatus(status))}</span>
                                </div>
                                <div class="mesa-operacao-inline-tags">
                                    ${requiredTag}
                                    ${validationMode ? `<span class="mesa-operacao-inline-tag">${escapeHtml(validationMode)}</span>` : ""}
                                </div>
                                ${meta ? `<p>${escapeHtml(meta)}</p>` : ""}
                                ${detalhes ? `<div class="mesa-operacao-meta"><span>${escapeHtml(detalhes)}</span></div>` : ""}
                                ${botaoRefazer}
                            </li>
                        `;
                    }).join("")}
                </ul>
            `
            : '<p class="mesa-operacao-vazio">Nenhum item de cobertura materializado para este laudo.</p>';

        return `
            <section class="mesa-operacao-card mesa-operacao-card--coverage">
                <header>
                    <div>
                        <h4>Checklist de evidências</h4>
                        <p>O que este caso exige, o que já foi coletado e o que ainda trava a aprovação.</p>
                    </div>
                </header>
                <div class="mesa-operacao-card-kpis">
                    <article>
                        <span>Obrigatorias</span>
                        <strong>${escapeHtml(String(coverageMap.total_required || 0))}</strong>
                    </article>
                    <article>
                        <span>Coletadas</span>
                        <strong>${escapeHtml(String(coverageMap.total_collected || 0))}</strong>
                    </article>
                    <article>
                        <span>Aceitas</span>
                        <strong>${escapeHtml(String(coverageMap.total_accepted || 0))}</strong>
                    </article>
                    <article>
                        <span>Alertas</span>
                        <strong>${escapeHtml(String((coverageMap.total_missing || 0) + (coverageMap.total_irregular || 0)))}</strong>
                    </article>
                </div>
                ${body}
            </section>
        `;
    };

    const renderizarHistoricoInspecaoMesa = (history) => {
        if (!history || typeof history !== "object") {
            return `
                <section class="mesa-operacao-card">
                    <header>
                        <div>
                            <h4>Histórico de Inspeção</h4>
                            <p>Sem base aprovada anterior compatível para esta família ainda.</p>
                        </div>
                    </header>
                    <p class="mesa-operacao-vazio">O clone e o diff entre emissões aparecem quando já existe pelo menos um caso aprovado da mesma família.</p>
                </section>
            `;
        }

        const diff = history.diff && typeof history.diff === "object" ? history.diff : {};
        const highlights = Array.isArray(diff.highlights) ? diff.highlights.slice(0, 4) : [];
        const identityHighlights = Array.isArray(diff.identity_highlights) ? diff.identity_highlights.slice(0, 4) : [];
        const blockHighlights = Array.isArray(diff.block_highlights) ? diff.block_highlights.slice(0, 3) : [];
        const diffCounters = [
            { label: "Mudanças", value: diff.changed_count || 0, tone: "attention" },
            { label: "Novos", value: diff.added_count || 0, tone: "accepted" },
            { label: "Removidos", value: diff.removed_count || 0, tone: "returned" },
        ].filter((item) => Number(item.value || 0) > 0);
        return `
            <section class="mesa-operacao-card">
                <header>
                    <div>
                        <h4>Histórico de Inspeção</h4>
                        <p>Comparação com a última inspeção aprovada compatível com este caso.</p>
                    </div>
                </header>
                <div class="mesa-operacao-card-kpis">
                    <article>
                        <span>Base anterior</span>
                        <strong>${escapeHtml(String(history.source_codigo_hash || history.source_laudo_id || "-"))}</strong>
                    </article>
                    <article>
                        <span>Match</span>
                        <strong>${escapeHtml(humanizarSlugAnalise(history.matched_by || "family_recency"))}</strong>
                    </article>
                    <article>
                        <span>Clone seguro</span>
                        <strong>${escapeHtml(String(history.prefilled_field_count || 0))}</strong>
                    </article>
                    <article>
                        <span>Diff</span>
                        <strong>${escapeHtml(String(diff.total_changes || (diff.changed_count || 0) + (diff.added_count || 0) + (diff.removed_count || 0)))}</strong>
                    </article>
                </div>
                ${diff.summary ? `<p>${escapeHtml(String(diff.summary || ""))}</p>` : ""}
                ${history.approved_at ? `<div class="mesa-operacao-meta"><span>Base aprovada em ${escapeHtml(formatarDataHora(history.approved_at))}</span></div>` : ""}
                ${diffCounters.length ? `
                    <div class="mesa-operacao-inline-tags">
                        ${diffCounters.map((item) => `
                            <span class="mesa-operacao-inline-tag ${escapeHtml(String(item.tone || "neutra"))}">
                                ${escapeHtml(String(item.label || "Diff"))}: ${escapeHtml(String(item.value || 0))}
                            </span>
                        `).join("")}
                    </div>
                ` : ""}
                ${blockHighlights.length ? `
                    <div class="mesa-operacao-inline-lists">
                        <div>
                            <strong>Blocos alterados</strong>
                            <ul class="mesa-operacao-coverage-lista mesa-operacao-diff-lista">
                                ${blockHighlights.map((item) => `
                                    <li class="mesa-operacao-coverage-item attention mesa-operacao-diff-item">
                                        <div class="mesa-operacao-item-topo">
                                            <strong>${escapeHtml(String(item?.title || "Bloco"))}</strong>
                                            <span class="mesa-operacao-chip attention">${escapeHtml(String(item?.total_changes || 0))} delta(s)</span>
                                        </div>
                                        ${item?.summary ? `<p>${escapeHtml(String(item.summary))}</p>` : ""}
                                        <div class="mesa-operacao-inline-tags">
                                            <span class="mesa-operacao-inline-tag attention">Alterados: ${escapeHtml(String(item?.changed_count || 0))}</span>
                                            ${Number(item?.added_count || 0) > 0 ? `<span class="mesa-operacao-inline-tag accepted">Novos: ${escapeHtml(String(item.added_count || 0))}</span>` : ""}
                                            ${Number(item?.removed_count || 0) > 0 ? `<span class="mesa-operacao-inline-tag returned">Removidos: ${escapeHtml(String(item.removed_count || 0))}</span>` : ""}
                                            ${Number(item?.identity_change_count || 0) > 0 ? `<span class="mesa-operacao-inline-tag">Criticos: ${escapeHtml(String(item.identity_change_count || 0))}</span>` : ""}
                                        </div>
                                        ${Array.isArray(item?.fields) && item.fields.length ? `
                                            <div class="mesa-operacao-diff-fields">
                                                ${item.fields.slice(0, 3).map((field) => `
                                                    <article>
                                                        <span>${escapeHtml(rotuloTipoDiffHistorico(field?.change_type || "changed"))}</span>
                                                        <strong>${escapeHtml(String(field?.label || "Campo"))}</strong>
                                                        <p>${escapeHtml(String(field?.previous_value || "vazio"))} → ${escapeHtml(String(field?.current_value || "vazio"))}</p>
                                                    </article>
                                                `).join("")}
                                            </div>
                                        ` : ""}
                                    </li>
                                `).join("")}
                            </ul>
                        </div>
                    </div>
                ` : ""}
                ${identityHighlights.length ? `
                    <div class="mesa-operacao-inline-lists">
                        <div>
                            <strong>Campos críticos</strong>
                            <ul class="mesa-operacao-coverage-lista mesa-operacao-diff-lista">
                                ${identityHighlights.map((item) => `
                                    <li class="mesa-operacao-coverage-item attention mesa-operacao-diff-item ${escapeHtml(String(item?.change_type || "changed"))}">
                                        <div class="mesa-operacao-item-topo">
                                            <strong>${escapeHtml(String(item?.label || "Campo"))}</strong>
                                            <span class="mesa-operacao-chip attention">${escapeHtml(rotuloTipoDiffHistorico(item?.change_type || "changed"))}</span>
                                        </div>
                                        <div class="mesa-operacao-meta">
                                            <span>${escapeHtml(String(item?.path || ""))}</span>
                                        </div>
                                        <div class="mesa-operacao-diff-values">
                                            <article>
                                                <span>Antes</span>
                                                <strong>${escapeHtml(String(item?.previous_value || "vazio"))}</strong>
                                            </article>
                                            <article>
                                                <span>Agora</span>
                                                <strong>${escapeHtml(String(item?.current_value || "vazio"))}</strong>
                                            </article>
                                        </div>
                                    </li>
                                `).join("")}
                            </ul>
                        </div>
                    </div>
                ` : ""}
                ${!blockHighlights.length && !identityHighlights.length && highlights.length ? `
                    <ul class="mesa-operacao-coverage-lista mesa-operacao-diff-lista">
                        ${highlights.map((item) => `
                            <li class="mesa-operacao-coverage-item attention mesa-operacao-diff-item ${escapeHtml(String(item?.change_type || "changed"))}">
                                <div class="mesa-operacao-item-topo">
                                    <strong>${escapeHtml(String(item?.label || "Campo"))}</strong>
                                    <span class="mesa-operacao-chip attention">${escapeHtml(rotuloTipoDiffHistorico(item?.change_type || "changed"))}</span>
                                </div>
                                <div class="mesa-operacao-meta">
                                    <span>${escapeHtml(String(item?.path || ""))}</span>
                                </div>
                                <div class="mesa-operacao-diff-values">
                                    <article>
                                        <span>Antes</span>
                                        <strong>${escapeHtml(String(item?.previous_value || "vazio"))}</strong>
                                    </article>
                                    <article>
                                        <span>Agora</span>
                                        <strong>${escapeHtml(String(item?.current_value || "vazio"))}</strong>
                                    </article>
                                </div>
                            </li>
                        `).join("")}
                    </ul>
                ` : (!blockHighlights.length && !identityHighlights.length ? '<p class="mesa-operacao-vazio">Sem diferenças estáveis relevantes em relação à base aprovada anterior.</p>' : "")}
            </section>
        `;
    };

    Object.assign(NS, {
        renderizarRevisaoPorBlocoMesa,
        renderizarCoverageMapMesa,
        renderizarHistoricoInspecaoMesa
    });
})();
