// ==========================================
// TARIEL.IA — REVISOR_PAINEL_GOVERNANCA.JS
// Papel: leitura de governança documental e memória operacional no painel do revisor.
// ==========================================

(function () {
    "use strict";

    const NS = window.TarielRevisorPainel;
    if (!NS || NS.__governancaWired__) return;
    NS.__governancaWired__ = true;

    const {
        escapeHtml,
        formatarDataHora,
        userCapabilityEnabled,
        tenantCapabilityReason
    } = NS;

    const IRREGULARITY_TYPE_LABELS = {
        field_reopened: "Campo reaberto",
        block_returned_to_inspector: "Bloco devolvido ao inspetor"
    };

    const IRREGULARITY_STATUS_LABELS = {
        open: "Aberta",
        acknowledged: "Reconhecida",
        resolved: "Resolvida",
        dismissed: "Descartada"
    };

    const humanizarSlugGovernanca = (value) => {
        const text = String(value || "").trim().replace(/_/g, " ");
        if (!text) return "";
        return text.replace(/\b\w/g, (match) => match.toUpperCase());
    };

    const rotuloTrailStatus = (status) => {
        const normalized = String(status || "").trim().toLowerCase();
        if (normalized === "ready") return "Pronto";
        if (normalized === "attention") return "Atencao";
        if (normalized === "blocked") return "Bloqueado";
        return humanizarSlugGovernanca(status || "status");
    };

    const rotuloIrregularityType = (type) =>
        IRREGULARITY_TYPE_LABELS[String(type || "").trim().toLowerCase()] || humanizarSlugGovernanca(type || "irregularidade");

    const rotuloIrregularityStatus = (status) =>
        IRREGULARITY_STATUS_LABELS[String(status || "").trim().toLowerCase()] || humanizarSlugGovernanca(status || "open");

    const resumirHashSha256Governanca = (value, limite = 12) => {
        const texto = String(value || "").trim();
        return texto ? `${texto.slice(0, limite)}...` : "";
    };

    const construirResumoIntegridadePdfOficialMesa = (currentIssue) => {
        if (!currentIssue || typeof currentIssue !== "object") {
            return null;
        }

        const comparisonStatus = String(currentIssue.primary_pdf_comparison_status || "").trim().toLowerCase();
        const diverged = !!currentIssue.primary_pdf_diverged || comparisonStatus === "diverged";
        const frozenVersion = String(currentIssue.primary_pdf_storage_version || "").trim();
        const currentVersion = String(currentIssue.current_primary_pdf_storage_version || "").trim();
        const frozenHash = resumirHashSha256Governanca(currentIssue.primary_pdf_sha256);
        const currentHash = resumirHashSha256Governanca(currentIssue.current_primary_pdf_sha256);
        const meta = [];

        if (frozenVersion) {
            meta.push(`Emitido ${frozenVersion}`);
        }
        if (currentVersion && currentVersion !== frozenVersion) {
            meta.push(`Atual ${currentVersion}`);
        }
        if (frozenHash) {
            meta.push(`Congelado ${frozenHash}`);
        }
        if (currentHash && diverged) {
            meta.push(`Atual ${currentHash}`);
        }

        if (diverged) {
            return {
                title: "Integridade do PDF principal",
                summary: "O PDF atual do caso divergiu do PDF congelado na emissão oficial.",
                chip: "Reemitir",
                tone: "returned",
                meta,
            };
        }

        if (!frozenVersion && !frozenHash && !currentVersion && !currentHash) {
            return null;
        }

        return {
            title: "Integridade do PDF principal",
            summary: "O PDF principal atual continua compatível com a emissão oficial congelada.",
            chip: "Íntegro",
            tone: "accepted",
            meta,
        };
    };

    const renderizarVerificacaoPublicaMesa = (verification) => {
        if (!verification || typeof verification !== "object") {
            return "";
        }
        const verificationUrl = String(verification.verification_url || "");
        const qrImageDataUri = String(verification.qr_image_data_uri || "");
        const statusVisualLabel = String(
            verification.status_visual_label || verification.status_revisao || "-"
        ).trim() || "-";
        return `
            <section class="mesa-operacao-card">
                <header>
                    <div>
                        <h4>Verificação Pública</h4>
                        <p>Hash público e link oficial para conferência documental.</p>
                    </div>
                </header>
                <div class="mesa-operacao-card-kpis">
                    <article>
                        <span>Hash</span>
                        <strong>${escapeHtml(String(verification.hash_short || verification.codigo_hash || "-"))}</strong>
                    </article>
                    <article>
                        <span>Fluxo</span>
                        <strong>${escapeHtml(statusVisualLabel)}</strong>
                    </article>
                    <article>
                        <span>Conformidade</span>
                        <strong>${escapeHtml(String(verification.status_conformidade || "-"))}</strong>
                    </article>
                    <article>
                        <span>Outcome</span>
                        <strong>${escapeHtml(String(verification.document_outcome || "-"))}</strong>
                    </article>
                </div>
                <div class="mesa-operacao-verification-shell">
                    ${qrImageDataUri ? `<img class="mesa-operacao-verification-qr" src="${escapeHtml(qrImageDataUri)}" alt="QR Code de verificacao publica" />` : ""}
                    <div class="mesa-operacao-verification-copy">
                        <div class="mesa-operacao-meta">
                            <span>${escapeHtml(verificationUrl)}</span>
                        </div>
                        ${verificationUrl ? `<a class="mesa-operacao-link" href="${escapeHtml(verificationUrl)}" target="_blank" rel="noopener noreferrer">Abrir verificação pública</a>` : ""}
                    </div>
                </div>
            </section>
        `;
    };

    const renderizarHistoricoRefazerInspetor = (historico) => {
        const itens = Array.isArray(historico) ? historico.slice(0, 6) : [];
        const body = itens.length
            ? `
                <ul class="mesa-operacao-coverage-lista">
                    ${itens.map((item) => {
                        const status = String(item?.status || "open").trim().toLowerCase();
                        const meta = [
                            item?.block_key ? `Bloco: ${humanizarSlugGovernanca(item.block_key)}` : "",
                            item?.evidence_key ? `Evidencia: ${item.evidence_key}` : "",
                            item?.detected_by_user_name ? `Por ${item.detected_by_user_name}` : "",
                            `Detectada em ${formatarDataHora(item?.detected_at)}`
                        ].filter(Boolean).join(" | ");
                        const resolucao = [
                            item?.resolution_mode ? humanizarSlugGovernanca(item.resolution_mode) : "",
                            item?.resolved_by_user_name ? `por ${item.resolved_by_user_name}` : "",
                            item?.resolved_at ? formatarDataHora(item.resolved_at) : ""
                        ].filter(Boolean).join(" ");
                        return `
                            <li class="mesa-operacao-coverage-item ${escapeHtml(status)}">
                                <div class="mesa-operacao-item-topo">
                                    <strong>${escapeHtml(rotuloIrregularityType(item?.irregularity_type))}</strong>
                                    <span class="mesa-operacao-chip ${escapeHtml(status)}">${escapeHtml(rotuloIrregularityStatus(status))}</span>
                                </div>
                                ${item?.summary ? `<p>${escapeHtml(String(item.summary))}</p>` : ""}
                                <div class="mesa-operacao-meta">
                                    ${meta ? `<span>${escapeHtml(meta)}</span>` : ""}
                                    ${resolucao ? `<span>Resolucao: ${escapeHtml(resolucao)}</span>` : ""}
                                    ${item?.resolution_notes ? `<span>${escapeHtml(String(item.resolution_notes))}</span>` : ""}
                                </div>
                            </li>
                        `;
                    }).join("")}
                </ul>
            `
            : '<p class="mesa-operacao-vazio">Nenhum refazer do inspetor foi registrado para este laudo.</p>';

        return `
            <section class="mesa-operacao-card mesa-operacao-card--history">
                <header>
                    <div>
                        <h4>Refazer Inspetor</h4>
                        <p>Historico rastreavel de reaberturas e devolucoes para campo.</p>
                    </div>
                </header>
                ${body}
            </section>
        `;
    };

    const renderizarMemoriaOperacionalFamilia = (memory) => {
        if (!memory || typeof memory !== "object") {
            return `
                <section class="mesa-operacao-card mesa-operacao-card--memory">
                    <header>
                        <div>
                            <h4>Memoria da Familia</h4>
                            <p>Sem memoria consolidada para esta familia ainda.</p>
                        </div>
                    </header>
                    <p class="mesa-operacao-vazio">Os snapshots aprovados e os eventos operacionais passam a fortalecer esta base conforme a operacao cresce.</p>
                </section>
            `;
        }

        const topEvents = Array.isArray(memory.top_event_types) ? memory.top_event_types.slice(0, 4) : [];
        const topIrregularities = Array.isArray(memory.top_open_irregularities) ? memory.top_open_irregularities.slice(0, 4) : [];
        return `
            <section class="mesa-operacao-card mesa-operacao-card--memory">
                <header>
                    <div>
                        <h4>Memoria da Familia</h4>
                        <p>${escapeHtml(humanizarSlugGovernanca(memory.family_key || ""))}</p>
                    </div>
                </header>
                <div class="mesa-operacao-card-kpis">
                    <article>
                        <span>Snapshots aprovados</span>
                        <strong>${escapeHtml(String(memory.approved_snapshot_count || 0))}</strong>
                    </article>
                    <article>
                        <span>Eventos</span>
                        <strong>${escapeHtml(String(memory.operational_event_count || 0))}</strong>
                    </article>
                    <article>
                        <span>Evidencias validadas</span>
                        <strong>${escapeHtml(String(memory.validated_evidence_count || 0))}</strong>
                    </article>
                    <article>
                        <span>Irregularidades abertas</span>
                        <strong>${escapeHtml(String(memory.open_irregularity_count || 0))}</strong>
                    </article>
                </div>
                <div class="mesa-operacao-meta">
                    <span>Ultima aprovacao: ${escapeHtml(formatarDataHora(memory.latest_approved_at))}</span>
                    <span>Ultimo evento: ${escapeHtml(formatarDataHora(memory.latest_event_at))}</span>
                </div>
                <div class="mesa-operacao-inline-lists">
                    <div>
                        <strong>Top eventos</strong>
                        ${topEvents.length
                            ? `<div class="mesa-operacao-inline-tags">${topEvents.map((item) => `<span class="mesa-operacao-inline-tag">${escapeHtml(`${humanizarSlugGovernanca(item.item_key)} (${item.count})`)}</span>`).join("")}</div>`
                            : '<p class="mesa-operacao-vazio">Sem eventos recorrentes suficientes.</p>'}
                    </div>
                    <div>
                        <strong>Top abertas</strong>
                        ${topIrregularities.length
                            ? `<div class="mesa-operacao-inline-tags">${topIrregularities.map((item) => `<span class="mesa-operacao-inline-tag alerta">${escapeHtml(`${humanizarSlugGovernanca(item.item_key)} (${item.count})`)}</span>`).join("")}</div>`
                            : '<p class="mesa-operacao-vazio">Nenhuma irregularidade aberta recorrente.</p>'}
                    </div>
                </div>
            </section>
        `;
    };

    const renderizarAnexoPackMesa = (annexPack) => {
        if (!annexPack || typeof annexPack !== "object") {
            return "";
        }
        const items = Array.isArray(annexPack.items) ? annexPack.items.slice(0, 6) : [];
        return `
            <section class="mesa-operacao-card mesa-operacao-card--coverage">
                <header>
                    <div>
                        <h4>Anexo Pack</h4>
                        <p>Pacote de anexos e artefatos exigidos para a emissão oficial.</p>
                    </div>
                </header>
                <div class="mesa-operacao-card-kpis">
                    <article>
                        <span>Itens</span>
                        <strong>${escapeHtml(String(annexPack.total_items || 0))}</strong>
                    </article>
                    <article>
                        <span>Obrigatórios</span>
                        <strong>${escapeHtml(String(annexPack.total_required || 0))}</strong>
                    </article>
                    <article>
                        <span>Presentes</span>
                        <strong>${escapeHtml(String(annexPack.total_present || 0))}</strong>
                    </article>
                    <article>
                        <span>Pendentes</span>
                        <strong>${escapeHtml(String(annexPack.missing_required_count || 0))}</strong>
                    </article>
                </div>
                ${Array.isArray(annexPack.missing_items) && annexPack.missing_items.length ? `
                    <div class="mesa-operacao-inline-tags">
                        ${annexPack.missing_items.slice(0, 4).map((item) => `
                            <span class="mesa-operacao-inline-tag alerta">${escapeHtml(String(item || ""))}</span>
                        `).join("")}
                    </div>
                ` : ""}
                ${items.length ? `
                    <ul class="mesa-operacao-coverage-lista">
                        ${items.map((item) => {
                            const status = item?.present ? "accepted" : "missing";
                            const meta = [
                                humanizarSlugGovernanca(item?.category || "anexo"),
                                item?.required ? "Obrigatório" : "Opcional",
                                item?.source ? humanizarSlugGovernanca(item.source) : ""
                            ].filter(Boolean).join(" | ");
                            return `
                                <li class="mesa-operacao-coverage-item ${escapeHtml(status)}">
                                    <div class="mesa-operacao-item-topo">
                                        <strong>${escapeHtml(String(item?.label || "Anexo"))}</strong>
                                        <span class="mesa-operacao-chip ${escapeHtml(status)}">${escapeHtml(item?.present ? "Pronto" : "Pendente")}</span>
                                    </div>
                                    ${meta ? `<p>${escapeHtml(meta)}</p>` : ""}
                                    ${item?.summary ? `<div class="mesa-operacao-meta"><span>${escapeHtml(String(item.summary))}</span></div>` : ""}
                                </li>
                            `;
                        }).join("")}
                    </ul>
                ` : '<p class="mesa-operacao-vazio">Sem anexos materializados para este laudo ainda.</p>'}
            </section>
        `;
    };

    const renderizarEmissaoOficialMesa = (officialIssue) => {
        if (!officialIssue || typeof officialIssue !== "object") {
            return "";
        }
        const blockers = Array.isArray(officialIssue.blockers) ? officialIssue.blockers.slice(0, 4) : [];
        const signatories = Array.isArray(officialIssue.signatories) ? officialIssue.signatories.slice(0, 4) : [];
        const eligibleSignatories = signatories.filter((item) => ["ready", "expiring_soon"].includes(String(item?.status || "").trim().toLowerCase()));
        const auditTrail = Array.isArray(officialIssue.audit_trail) ? officialIssue.audit_trail.slice(0, 5) : [];
        const currentIssue = officialIssue.current_issue && typeof officialIssue.current_issue === "object"
            ? officialIssue.current_issue
            : null;
        const reissueOriginNumber = String(currentIssue?.reissue_of_issue_number || "").trim();
        const reissueReasonSummary = String(currentIssue?.reissue_reason_summary || "").trim();
        const documentIntegrity = construirResumoIntegridadePdfOficialMesa(currentIssue);
        const reissueRecommended = !!officialIssue.reissue_recommended;
        const genericReissueWarning = reissueRecommended && (!documentIntegrity || documentIntegrity.tone !== "returned")
            ? {
                title: "Reemissão recomendada",
                summary: "A emissão oficial segue registrada, mas a governança recomenda emitir um novo pacote antes da próxima entrega pública.",
                chip: "Atenção",
                tone: "attention",
                meta: [],
            }
            : null;
        const tone = officialIssue.ready_for_issue ? "accepted" : blockers.length ? "returned" : "attention";
        return `
            <section class="mesa-operacao-card mesa-operacao-card--memory">
                <header>
                    <div>
                        <h4>Emissão Oficial</h4>
                        <p>${escapeHtml(String(officialIssue.issue_status_label || "Governança documental"))}</p>
                    </div>
                </header>
                <div class="mesa-operacao-card-kpis">
                    <article>
                        <span>Status</span>
                        <strong>${escapeHtml(String(officialIssue.issue_status || "-"))}</strong>
                    </article>
                    <article>
                        <span>Compatíveis</span>
                        <strong>${escapeHtml(String(officialIssue.compatible_signatory_count || 0))}</strong>
                    </article>
                    <article>
                        <span>Elegíveis</span>
                        <strong>${escapeHtml(String(officialIssue.eligible_signatory_count || 0))}</strong>
                    </article>
                    <article>
                        <span>Bloqueios</span>
                        <strong>${escapeHtml(String(officialIssue.blocker_count || 0))}</strong>
                    </article>
                </div>
                <div class="mesa-operacao-inline-tags">
                    <span class="mesa-operacao-inline-tag ${escapeHtml(tone)}">${escapeHtml(String(officialIssue.signature_status_label || "Sem leitura de assinatura"))}</span>
                    ${officialIssue.verification_url ? `<span class="mesa-operacao-inline-tag">${escapeHtml(String(officialIssue.verification_url))}</span>` : ""}
                    ${documentIntegrity && documentIntegrity.tone === "returned"
                        ? '<span class="mesa-operacao-inline-tag returned">PDF emitido divergente</span>'
                        : ""}
                    ${genericReissueWarning ? '<span class="mesa-operacao-inline-tag attention">Reemissão recomendada</span>' : ""}
                    <span class="mesa-operacao-inline-tag neutra">ZIP com manifesto e hash SHA-256</span>
                </div>
                ${currentIssue ? `
                    <div class="mesa-operacao-inline-lists">
                        <div>
                            <strong>Emissão congelada</strong>
                            <ul class="mesa-operacao-coverage-lista">
                                <li class="mesa-operacao-coverage-item accepted">
                                    <div class="mesa-operacao-item-topo">
                                        <strong>${escapeHtml(String(currentIssue.issue_number || "Emissão oficial"))}</strong>
                                        <span class="mesa-operacao-chip accepted">${escapeHtml(String(currentIssue.issue_state_label || "Emitido"))}</span>
                                    </div>
                                    <p>${escapeHtml(String(currentIssue.signatory_name || "Signatário não informado"))}${currentIssue.signatory_registration ? ` · ${escapeHtml(String(currentIssue.signatory_registration))}` : ""}</p>
                                    <div class="mesa-operacao-meta">
                                        ${currentIssue.issued_at ? `<span>${escapeHtml(formatarDataHora(currentIssue.issued_at))}</span>` : ""}
                                        ${currentIssue.package_sha256 ? `<span>SHA-256 ${escapeHtml(String(currentIssue.package_sha256).slice(0, 16))}...</span>` : ""}
                                    </div>
                                </li>
                                ${documentIntegrity ? `
                                    <li class="mesa-operacao-coverage-item ${escapeHtml(documentIntegrity.tone)}">
                                        <div class="mesa-operacao-item-topo">
                                            <strong>${escapeHtml(documentIntegrity.title)}</strong>
                                            <span class="mesa-operacao-chip ${escapeHtml(documentIntegrity.tone)}">${escapeHtml(documentIntegrity.chip)}</span>
                                        </div>
                                        <p>${escapeHtml(documentIntegrity.summary)}</p>
                                        ${documentIntegrity.meta.length ? `
                                            <div class="mesa-operacao-meta">
                                                ${documentIntegrity.meta.map((item) => `<span>${escapeHtml(String(item))}</span>`).join("")}
                                            </div>
                                        ` : ""}
                                    </li>
                                ` : ""}
                                ${reissueOriginNumber || reissueReasonSummary ? `
                                    <li class="mesa-operacao-coverage-item accepted">
                                        <div class="mesa-operacao-item-topo">
                                            <strong>Linhagem da emissão</strong>
                                            <span class="mesa-operacao-chip accepted">Reemitido</span>
                                        </div>
                                        <p>${escapeHtml(
                                            reissueOriginNumber
                                                ? `Esta emissão substitui ${reissueOriginNumber}.`
                                                : "Esta emissão substitui uma emissão oficial anterior."
                                        )}</p>
                                        ${reissueReasonSummary ? `
                                            <div class="mesa-operacao-meta">
                                                <span>${escapeHtml(reissueReasonSummary)}</span>
                                            </div>
                                        ` : ""}
                                    </li>
                                ` : ""}
                                ${genericReissueWarning ? `
                                    <li class="mesa-operacao-coverage-item ${escapeHtml(genericReissueWarning.tone)}">
                                        <div class="mesa-operacao-item-topo">
                                            <strong>${escapeHtml(genericReissueWarning.title)}</strong>
                                            <span class="mesa-operacao-chip ${escapeHtml(genericReissueWarning.tone)}">${escapeHtml(genericReissueWarning.chip)}</span>
                                        </div>
                                        <p>${escapeHtml(genericReissueWarning.summary)}</p>
                                    </li>
                                ` : ""}
                            </ul>
                        </div>
                    </div>
                ` : ""}
                ${blockers.length ? `
                    <ul class="mesa-operacao-coverage-lista">
                        ${blockers.map((item) => `
                            <li class="mesa-operacao-coverage-item returned">
                                <div class="mesa-operacao-item-topo">
                                    <strong>${escapeHtml(String(item?.title || "Bloqueio"))}</strong>
                                    <span class="mesa-operacao-chip returned">${escapeHtml(item?.blocking ? "Bloqueante" : "Aviso")}</span>
                                </div>
                                ${item?.message ? `<p>${escapeHtml(String(item.message))}</p>` : ""}
                            </li>
                        `).join("")}
                    </ul>
                ` : '<p class="mesa-operacao-vazio">Sem bloqueios adicionais. A emissão oficial pode seguir.</p>'}
                ${auditTrail.length ? `
                    <div class="mesa-operacao-inline-lists">
                        <div>
                            <strong>Trilha documental</strong>
                            <ul class="mesa-operacao-coverage-lista mesa-operacao-trail-lista">
                                ${auditTrail.map((item) => `
                                    <li class="mesa-operacao-coverage-item ${escapeHtml(String(item?.status || "attention"))}">
                                        <div class="mesa-operacao-item-topo">
                                            <strong>${escapeHtml(String(item?.title || "Evento documental"))}</strong>
                                            <span class="mesa-operacao-chip ${escapeHtml(String(item?.status || "attention"))}">
                                                ${escapeHtml(rotuloTrailStatus(item?.status || "attention"))}
                                            </span>
                                        </div>
                                        ${item?.summary ? `<p>${escapeHtml(String(item.summary))}</p>` : ""}
                                        <div class="mesa-operacao-meta">
                                            ${item?.recorded_at ? `<span>${escapeHtml(formatarDataHora(item.recorded_at))}</span>` : ""}
                                            <span>${item?.blocking ? "Bloqueante" : "Rastreavel"}</span>
                                        </div>
                                    </li>
                                `).join("")}
                            </ul>
                        </div>
                    </div>
                ` : ""}
                ${signatories.length ? `
                    <div class="mesa-operacao-inline-lists">
                        <div>
                            <strong>Signatários governados</strong>
                            <div class="mesa-operacao-inline-tags">
                                ${signatories.map((item) => `
                                    <span class="mesa-operacao-inline-tag ${escapeHtml(String(item?.status || "attention"))}">
                                        ${escapeHtml(`${String(item?.nome || "Signatário")} · ${String(item?.funcao || "")}`)}
                                    </span>
                                `).join("")}
                            </div>
                        </div>
                    </div>
                ` : ""}
                ${(officialIssue.issue_action_enabled && eligibleSignatories.length) || (currentIssue && currentIssue.package_storage_ready) ? `
                    <div class="mesa-operacao-action-rail">
                        ${userCapabilityEnabled("reviewer_issue") ? eligibleSignatories.map((item) => `
                            <button
                                type="button"
                                class="mesa-operacao-inline-tag mesa-operacao-inline-tag--button"
                                data-mesa-action="emitir-oficialmente"
                                data-signatory-id="${escapeHtml(String(item?.id || ""))}"
                                data-signatory-name="${escapeHtml(String(item?.nome || "Signatário"))}"
                                data-current-issue-id="${escapeHtml(String(currentIssue?.id || ""))}"
                                data-current-issue-number="${escapeHtml(String(currentIssue?.issue_number || ""))}"
                            >
                                ${escapeHtml(String(officialIssue.issue_action_label || "Emitir oficialmente"))} · ${escapeHtml(String(item?.nome || "Signatário"))}
                            </button>
                        `).join("") : `
                            <button
                                type="button"
                                class="mesa-operacao-inline-tag mesa-operacao-inline-tag--button"
                                disabled
                                aria-disabled="true"
                                title="${escapeHtml(tenantCapabilityReason("reviewer_issue"))}"
                            >
                                Emissão oficial governada
                            </button>
                        `}
                        ${currentIssue && currentIssue.package_storage_ready && userCapabilityEnabled("reviewer_issue") ? `
                            <button
                                type="button"
                                class="mesa-operacao-inline-tag mesa-operacao-inline-tag--button"
                                data-mesa-action="baixar-emissao-oficial"
                            >
                                Baixar bundle emitido
                            </button>
                        ` : ""}
                    </div>
                ` : ""}
            </section>
        `;
    };

    const renderizarGovernancaPolicyMesa = (policySummary) => {
        if (!policySummary || typeof policySummary !== "object") {
            return "";
        }

        const entitlements = (
            policySummary.tenant_entitlements && typeof policySummary.tenant_entitlements === "object"
                ? policySummary.tenant_entitlements
                : {}
        );
        const familyPolicy = (
            policySummary.family_policy_summary && typeof policySummary.family_policy_summary === "object"
                ? policySummary.family_policy_summary
                : {}
        );
        const redFlags = Array.isArray(policySummary.red_flags) ? policySummary.red_flags.slice(0, 4) : [];
        const allowedModes = Array.isArray(entitlements.allowed_review_modes)
            ? entitlements.allowed_review_modes
            : [];

        return `
            <section class="mesa-operacao-card mesa-operacao-card--policy">
                <header>
                    <div>
                        <h4>Governança da Revisão</h4>
                        <p>Modo efetivo, liberacao da empresa e alertas que endurecem a decisao.</p>
                    </div>
                </header>
                <div class="mesa-operacao-card-kpis">
                    <article>
                        <span>Modo</span>
                        <strong>${escapeHtml(humanizarSlugGovernanca(policySummary.review_mode || "mesa_required"))}</strong>
                    </article>
                    <article>
                        <span>Plano</span>
                        <strong>${escapeHtml(String(entitlements.plan_name || "n/d"))}</strong>
                    </article>
                    <article>
                        <span>Release</span>
                        <strong>${escapeHtml(String(familyPolicy.release_status || "sem release"))}</strong>
                    </article>
                    <article>
                        <span>Red flags</span>
                        <strong>${escapeHtml(String(redFlags.length))}</strong>
                    </article>
                </div>
                <div class="mesa-operacao-meta">
                    ${entitlements.usage_status ? `<span>Uso da empresa: ${escapeHtml(String(entitlements.usage_status))}</span>` : ""}
                    ${allowedModes.length
                        ? `<span>Modos liberados: ${escapeHtml(allowedModes.map((item) => humanizarSlugGovernanca(item)).join(", "))}</span>`
                        : ""}
                </div>
                ${redFlags.length
                    ? `
                        <ul class="mesa-operacao-coverage-lista">
                            ${redFlags.map((item) => {
                                const severity = String(item?.severity || "high").trim().toLowerCase();
                                const tone = severity === "critical" || severity === "high" ? "irregular" : "missing";
                                return `
                                    <li class="mesa-operacao-coverage-item ${escapeHtml(tone)}">
                                        <div class="mesa-operacao-item-topo">
                                            <strong>${escapeHtml(String(item?.title || "Red flag"))}</strong>
                                            <span class="mesa-operacao-chip ${escapeHtml(tone)}">${escapeHtml(humanizarSlugGovernanca(severity))}</span>
                                        </div>
                                        ${item?.message ? `<p>${escapeHtml(String(item.message))}</p>` : ""}
                                        <div class="mesa-operacao-meta">
                                            ${item?.source ? `<span>Fonte: ${escapeHtml(humanizarSlugGovernanca(item.source))}</span>` : ""}
                                            ${item?.blocking ? "<span>Eleva para Mesa</span>" : ""}
                                        </div>
                                    </li>
                                `;
                            }).join("")}
                        </ul>
                    `
                    : '<p class="mesa-operacao-vazio">Sem red flags governadas ativas para este caso.</p>'}
            </section>
        `;
    };

    Object.assign(NS, {
        renderizarVerificacaoPublicaMesa,
        renderizarHistoricoRefazerInspetor,
        renderizarMemoriaOperacionalFamilia,
        renderizarAnexoPackMesa,
        renderizarEmissaoOficialMesa,
        renderizarGovernancaPolicyMesa
    });
})();
