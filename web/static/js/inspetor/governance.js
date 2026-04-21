(function () {
    "use strict";

    const inspectorRuntime = window.TarielInspectorRuntime || null;
    const modules = typeof inspectorRuntime?.resolveModuleBucket === "function"
        ? inspectorRuntime.resolveModuleBucket("TarielInspetorModules")
        : (window.TarielInspetorModules = window.TarielInspetorModules || {});

    modules.registerGovernance = function registerGovernance(ctx) {
        const el = ctx.elements;
        const {
            normalizarCaseLifecycleStatusSeguro,
            normalizarEmissaoOficialSeguro,
            obterPayloadStatusRelatorioWorkspaceAtual,
            workspaceHasSurfaceAction,
            workspaceTemContratoLifecycle,
        } = ctx.shared;

        function humanizarMarcadorWorkspace(valor = "") {
            return String(valor || "")
                .trim()
                .replace(/[_-]+/g, " ")
                .replace(/\s+/g, " ")
                .replace(/\b\w/g, (letra) => letra.toUpperCase());
        }

        function lifecyclePermiteVerificacaoPublicaWorkspace(valor = "") {
            const status = normalizarCaseLifecycleStatusSeguro(valor);
            return status === "aprovado" || status === "emitido";
        }

        function lifecycleBloqueiaEnvioMesaWorkspace(valor = "") {
            const status = normalizarCaseLifecycleStatusSeguro(valor);
            return (
                status === "aguardando_mesa" ||
                status === "em_revisao_mesa" ||
                status === "aprovado" ||
                status === "emitido"
            );
        }

        function obterRotuloAcaoFinalizacaoWorkspace(valor = "") {
            const status = normalizarCaseLifecycleStatusSeguro(valor);
            if (status === "devolvido_para_correcao") {
                return "Reenviar para Mesa";
            }
            return "Enviar para Mesa";
        }

        function workspacePermiteFinalizacao(snapshot = null) {
            if (workspaceTemContratoLifecycle(snapshot)) {
                return workspaceHasSurfaceAction(snapshot, "chat_finalize");
            }

            return !lifecycleBloqueiaEnvioMesaWorkspace(
                snapshot?.case_lifecycle_status ?? snapshot?.laudo_card?.case_lifecycle_status
            );
        }

        function construirMetaVerificacaoPublicaWorkspace(lifecycleStatus, verification = null) {
            const partes = [];
            if (verification?.hashShort) {
                partes.push(`Hash ${verification.hashShort}`);
            }
            partes.push(
                normalizarCaseLifecycleStatusSeguro(lifecycleStatus) === "emitido"
                    ? "PDF final emitido"
                    : "Pronto para emissão"
            );
            if (verification?.statusVisualLabel) {
                partes.push(verification.statusVisualLabel);
            }
            if (verification?.statusConformidade) {
                partes.push(verification.statusConformidade);
            } else if (verification?.documentOutcome) {
                partes.push(humanizarMarcadorWorkspace(verification.documentOutcome));
            } else if (verification?.statusRevisao) {
                partes.push(humanizarMarcadorWorkspace(verification.statusRevisao));
            }
            return partes.join(" • ");
        }

        function construirResumoEmissaoOficialWorkspace(officialIssue = null) {
            if (!officialIssue) {
                return {
                    title: "Aguardando governança documental",
                    meta: "A etapa oficial de emissão ainda não começou.",
                    chip: "PENDENTE",
                    tone: "neutral",
                };
            }

            const currentIssue = officialIssue.currentIssue;
            const primeiroBloqueio = Array.isArray(officialIssue.blockers) ? officialIssue.blockers[0] : null;

            if (currentIssue) {
                const primaryPdfDiverged = !!(
                    currentIssue.primary_pdf_diverged ||
                    String(currentIssue.primary_pdf_comparison_status || "").trim().toLowerCase() === "diverged"
                );
                const frozenVersion = String(currentIssue.primary_pdf_storage_version || "").trim();
                const currentVersion = String(currentIssue.current_primary_pdf_storage_version || "").trim();
                const documentSummary = primaryPdfDiverged
                    ? [
                        "PDF atual divergiu do emitido",
                        frozenVersion && currentVersion && frozenVersion !== currentVersion
                            ? `${frozenVersion} → ${currentVersion}`
                            : currentVersion && currentVersion !== frozenVersion
                                ? `Atual ${currentVersion}`
                                : frozenVersion
                                    ? `Emitido ${frozenVersion}`
                                    : "",
                    ].filter(Boolean).join(" • ")
                    : officialIssue.reissueRecommended
                        ? "Reemissão recomendada"
                        : "";
                return {
                    title: String(currentIssue.issue_number || officialIssue.issueStatusLabel || "Emissão oficial ativa"),
                    meta: [
                        currentIssue.signatory_name || "",
                        currentIssue.signatory_registration || "",
                        documentSummary,
                    ].filter(Boolean).join(" • ") || "Pacote emitido e congelado.",
                    chip: primaryPdfDiverged || officialIssue.reissueRecommended ? "REEMITIR" : "EMITIDO",
                    tone: primaryPdfDiverged || officialIssue.reissueRecommended ? "warning" : "accepted",
                };
            }

            if (officialIssue.readyForIssue) {
                return {
                    title: String(officialIssue.issueStatusLabel || "Pronto para emissão oficial"),
                    meta: [
                        officialIssue.issueActionLabel || "Emitir oficialmente",
                        officialIssue.eligibleSignatoryCount
                            ? `${officialIssue.eligibleSignatoryCount} signatário(s) elegível(is)`
                            : "",
                    ].filter(Boolean).join(" • "),
                    chip: "PRONTO",
                    tone: "accepted",
                };
            }

            return {
                title: String(officialIssue.issueStatusLabel || "Bloqueado por governança"),
                meta: String(primeiroBloqueio?.message || "A emissão oficial ainda tem bloqueios pendentes."),
                chip: officialIssue.blockerCount ? `${officialIssue.blockerCount} BLOQ.` : "PENDENTE",
                tone: "neutral",
            };
        }

        function resumirReemissaoRecomendadaPortal(total = 0) {
            const quantidade = Number(total || 0);
            return quantidade === 1
                ? "1 caso com reemissão recomendada"
                : `${quantidade} casos com reemissão recomendada`;
        }

        function detalharReemissaoRecomendadaPortal(total = 0) {
            return Number(total || 0) === 1
                ? "PDF oficial divergente detectado no ponto de entrada do inspetor."
                : "PDF oficial divergente detectado em casos já emitidos do inspetor.";
        }

        function coletarResumoGovernancaPortal() {
            const itens = Array.from(
                document.querySelectorAll("[data-home-laudo-id][data-official-issue-diverged='true']")
            );
            const laudosDivergentes = new Set();
            itens.forEach((item) => {
                const laudoId = Number(item.dataset.homeLaudoId || 0) || 0;
                if (laudoId > 0) {
                    laudosDivergentes.add(laudoId);
                }
            });
            const total = laudosDivergentes.size;
            return {
                visible: total > 0,
                reissueRecommendedCount: total,
                label: resumirReemissaoRecomendadaPortal(total),
                detail: detalharReemissaoRecomendadaPortal(total),
            };
        }

        function renderizarGovernancaEntradaInspetor() {
            const resumo = coletarResumoGovernancaPortal();

            if (el.portalGovernanceSummary) {
                el.portalGovernanceSummary.hidden = !resumo.visible;
            }
            if (el.portalGovernanceSummaryTitle) {
                el.portalGovernanceSummaryTitle.textContent = resumo.label;
            }
            if (el.portalGovernanceSummaryDetail) {
                el.portalGovernanceSummaryDetail.textContent = resumo.detail;
            }

            if (el.workspaceAssistantGovernance) {
                el.workspaceAssistantGovernance.hidden = !resumo.visible;
            }
            if (el.workspaceAssistantGovernanceTitle) {
                el.workspaceAssistantGovernanceTitle.textContent = resumo.label;
            }
            if (el.workspaceAssistantGovernanceDetail) {
                el.workspaceAssistantGovernanceDetail.textContent = resumo.detail;
            }
        }

        function construirResumoGovernancaHistoricoWorkspace() {
            const snapshot = obterPayloadStatusRelatorioWorkspaceAtual();
            const officialIssue = normalizarEmissaoOficialSeguro(snapshot?.emissao_oficial);
            const currentIssue = officialIssue?.currentIssue;
            const primaryPdfDiverged = !!(
                currentIssue?.primary_pdf_diverged ||
                String(currentIssue?.primary_pdf_comparison_status || "").trim().toLowerCase() === "diverged"
            );

            if (!primaryPdfDiverged) {
                return {
                    visible: false,
                    title: "Reemissão recomendada",
                    detail: "PDF emitido divergente detectado no caso atual.",
                    actionLabel: "Abrir reemissão na Mesa",
                };
            }

            const frozenVersion = String(currentIssue?.primary_pdf_storage_version || "").trim();
            const currentVersion = String(currentIssue?.current_primary_pdf_storage_version || "").trim();
            const versionSummary = (
                frozenVersion && currentVersion && frozenVersion !== currentVersion
                    ? `${frozenVersion} → ${currentVersion}`
                    : currentVersion && currentVersion !== frozenVersion
                        ? `Atual ${currentVersion}`
                        : frozenVersion
                            ? `Emitido ${frozenVersion}`
                            : ""
            );

            return {
                visible: true,
                title: "Reemissão recomendada",
                detail: [
                    "PDF emitido divergente",
                    versionSummary,
                    String(currentIssue?.issue_number || "").trim(),
                ].filter(Boolean).join(" • "),
                actionLabel: "Abrir reemissão na Mesa",
            };
        }

        function renderizarGovernancaHistoricoWorkspace() {
            const resumo = construirResumoGovernancaHistoricoWorkspace();

            if (el.workspaceHistoryGovernance) {
                el.workspaceHistoryGovernance.hidden = !resumo.visible;
            }
            if (el.workspaceHistoryGovernanceTitle) {
                el.workspaceHistoryGovernanceTitle.textContent = resumo.title;
            }
            if (el.workspaceHistoryGovernanceDetail) {
                el.workspaceHistoryGovernanceDetail.textContent = resumo.detail;
            }
            if (el.btnWorkspaceHistoryReissue) {
                el.btnWorkspaceHistoryReissue.textContent = resumo.actionLabel;
            }
        }

        Object.assign(ctx.actions, {
            lifecyclePermiteVerificacaoPublicaWorkspace,
            obterRotuloAcaoFinalizacaoWorkspace,
            workspacePermiteFinalizacao,
            construirMetaVerificacaoPublicaWorkspace,
            construirResumoEmissaoOficialWorkspace,
            construirResumoGovernancaHistoricoWorkspace,
            renderizarGovernancaEntradaInspetor,
            renderizarGovernancaHistoricoWorkspace,
        });
    };
})();
