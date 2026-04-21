(function () {
    "use strict";

    const inspectorRuntime = window.TarielInspectorRuntime || null;
    const modules = typeof inspectorRuntime?.resolveModuleBucket === "function"
        ? inspectorRuntime.resolveModuleBucket("TarielInspetorModules")
        : (window.TarielInspetorModules = window.TarielInspetorModules || {});

    modules.registerEntryMode = function registerEntryMode(ctx) {
        const estado = ctx.state;
        const el = ctx.elements;
        const {
            CHAVE_FORCE_HOME_LANDING,
            CHAVE_RETOMADA_HOME_PENDENTE,
            CHAVE_CONTEXTO_VISUAL_LAUDOS,
            LIMITE_CONTEXTO_VISUAL_LAUDOS_STORAGE,
            normalizarContextoVisualSeguro,
            normalizarEntryModeEffective,
            normalizarEntryModeEffectiveOpcional,
            normalizarEntryModePreference,
            normalizarEntryModeReason,
            normalizarLaudoAtualId,
            normalizarThreadTab,
            normalizarTipoTemplate,
        } = ctx.shared;

        function normalizarBooleanoEstado(valor, fallback = false) {
            if (valor === true || valor === false) return valor;
            if (valor == null || valor === "") return !!fallback;

            const texto = String(valor).trim().toLowerCase();
            if (texto === "true" || texto === "1" || texto === "yes") return true;
            if (texto === "false" || texto === "0" || texto === "no") return false;
            return !!fallback;
        }

        function obterBootstrapModoEntrada() {
            const painel = el.painelChat;
            return {
                preferenceDefault: normalizarEntryModePreference(
                    painel?.dataset?.entryModePreferenceDefault,
                    "auto_recommended"
                ),
                rememberLastCaseMode: normalizarBooleanoEstado(
                    painel?.dataset?.entryModeRememberLastCaseMode,
                    false
                ),
                lastCaseMode: normalizarEntryModeEffectiveOpcional(
                    painel?.dataset?.entryModeLastCaseMode
                ),
            };
        }

        function extrairModoEntradaPayload(payload = {}) {
            const body = payload && typeof payload === "object" ? payload : {};
            const card = body.laudo_card || body.laudoCard || body.card || {};

            const preferenceRaw =
                body.entry_mode_preference ??
                body.entryModePreference ??
                card.entry_mode_preference ??
                card.entryModePreference ??
                null;
            const effectiveRaw =
                body.entry_mode_effective ??
                body.entryModeEffective ??
                card.entry_mode_effective ??
                card.entryModeEffective ??
                null;
            const reasonRaw =
                body.entry_mode_reason ??
                body.entryModeReason ??
                card.entry_mode_reason ??
                card.entryModeReason ??
                null;

            return {
                preference: preferenceRaw == null || String(preferenceRaw).trim() === ""
                    ? null
                    : normalizarEntryModePreference(
                        preferenceRaw,
                        estado.entryModePreferenceDefault || "auto_recommended"
                    ),
                effective: effectiveRaw == null || String(effectiveRaw).trim() === ""
                    ? null
                    : normalizarEntryModeEffective(
                        effectiveRaw,
                        estado.entryModeLastCaseMode || "chat_first"
                    ),
                reason: reasonRaw == null || String(reasonRaw).trim() === ""
                    ? null
                    : normalizarEntryModeReason(reasonRaw),
            };
        }

        function rotuloModoEntrada(valor) {
            return normalizarEntryModeEffective(valor) === "evidence_first"
                ? "Evidências primeiro"
                : "Chat primeiro";
        }

        function descreverMotivoModoEntrada(reason) {
            const motivo = normalizarEntryModeReason(reason);
            if (motivo === "user_preference") return "";
            if (motivo === "last_case_mode") {
                return "A preferência automática reaproveitou o último modo efetivo do inspetor.";
            }
            if (motivo === "auto_recommended") {
                return "O sistema recomendou esse início para o caso atual.";
            }
            if (motivo === "family_required_mode") {
                return "A família documental impôs esse modo de abertura.";
            }
            if (motivo === "hard_safety_rule") {
                return "Uma regra de segurança sobrepôs a preferência escolhida.";
            }
            if (motivo === "tenant_policy") {
                return "A política da empresa sobrepôs a preferência escolhida.";
            }
            if (motivo === "role_policy") {
                return "A política do perfil sobrepôs a preferência escolhida.";
            }
            if (motivo === "existing_case_state") {
                return "O caso já estava em andamento nesse fluxo.";
            }
            return "Sem regra mais forte, o produto manteve o fluxo padrão.";
        }

        function atualizarWorkspaceEntryModeNote() {
            if (!el.workspaceEntryModeNote) return;

            const workspaceAtivo = estado.workspaceStage === "inspection" && !!estado.laudoAtualId;
            if (!workspaceAtivo) {
                el.workspaceEntryModeNote.hidden = true;
                el.workspaceEntryModeNote.textContent = "";
                return;
            }

            const fraseBase = `${rotuloModoEntrada(estado.entryModeEffective)} ativo neste caso.`;
            const motivo = descreverMotivoModoEntrada(estado.entryModeReason);
            el.workspaceEntryModeNote.textContent = motivo
                ? `${fraseBase} ${motivo}`
                : fraseBase;
            el.workspaceEntryModeNote.hidden = false;
        }

        function atualizarEstadoModoEntrada(
            payload = {},
            { reset = false, atualizarPadrao = false } = {}
        ) {
            const bootstrap = obterBootstrapModoEntrada();
            if (atualizarPadrao) {
                estado.entryModePreferenceDefault = bootstrap.preferenceDefault;
                estado.entryModeRememberLastCaseMode = bootstrap.rememberLastCaseMode;
                estado.entryModeLastCaseMode = bootstrap.lastCaseMode;
            }

            if (reset) {
                const effectiveFallback = bootstrap.lastCaseMode || "chat_first";
                estado.entryModePreference = bootstrap.preferenceDefault;
                estado.entryModeEffective = normalizarEntryModeEffective(effectiveFallback);
                estado.entryModeReason = bootstrap.lastCaseMode
                    ? "last_case_mode"
                    : "default_product_fallback";
                atualizarWorkspaceEntryModeNote();
                return {
                    preference: estado.entryModePreference,
                    effective: estado.entryModeEffective,
                    reason: estado.entryModeReason,
                };
            }

            const extraido = extrairModoEntradaPayload(payload);
            estado.entryModePreference =
                extraido.preference ||
                estado.entryModePreferenceDefault ||
                bootstrap.preferenceDefault;
            estado.entryModeEffective =
                extraido.effective ||
                estado.entryModeEffective ||
                bootstrap.lastCaseMode ||
                "chat_first";
            estado.entryModeReason =
                extraido.reason ||
                estado.entryModeReason ||
                "default_product_fallback";
            atualizarWorkspaceEntryModeNote();
            return {
                preference: estado.entryModePreference,
                effective: estado.entryModeEffective,
                reason: estado.entryModeReason,
            };
        }

        function modoEntradaEvidenceFirstAtivo() {
            return normalizarEntryModeEffective(estado.entryModeEffective) === "evidence_first";
        }

        function resolverThreadTabInicialPorModoEntrada(payload = {}, fallback = "historico") {
            const contexto = extrairModoEntradaPayload(payload);
            if (contexto.effective === "evidence_first") return "anexos";
            if (contexto.effective === "chat_first") return "conversa";
            return normalizarThreadTab(fallback);
        }

        function normalizarRetomadaHomePendenteSeguro(payload = null) {
            if (!payload || typeof payload !== "object") return null;

            const contextoVisual = normalizarContextoVisualSeguro(payload?.contextoVisual);
            const expiresAt = Number(payload?.expiresAt || 0) || (Date.now() + 10000);

            return {
                laudoId: normalizarLaudoAtualId(payload?.laudoId),
                tipoTemplate: normalizarTipoTemplate(payload?.tipoTemplate || estado.tipoTemplateAtivo),
                contextoVisual,
                expiresAt,
            };
        }

        function retomadaHomePendenteEhValida(payload = null) {
            return !!payload && Number(payload?.expiresAt || 0) > Date.now();
        }

        function sanitizarMapaContextoVisualLaudos(payload = null) {
            if (!payload || typeof payload !== "object") return {};

            const entradas = Object.entries(payload)
                .map(([laudoId, contextoVisual]) => {
                    const id = normalizarLaudoAtualId(laudoId);
                    const contexto = normalizarContextoVisualSeguro(contextoVisual);
                    if (!id || !contexto) return null;
                    return [String(id), contexto];
                })
                .filter(Boolean)
                .sort((atual, proximo) => Number(proximo[0]) - Number(atual[0]))
                .slice(0, LIMITE_CONTEXTO_VISUAL_LAUDOS_STORAGE);

            return Object.fromEntries(entradas);
        }

        function persistirContextoVisualLaudosStorage(payload = null) {
            const mapa = sanitizarMapaContextoVisualLaudos(payload);

            try {
                if (Object.keys(mapa).length) {
                    sessionStorage.setItem(CHAVE_CONTEXTO_VISUAL_LAUDOS, JSON.stringify(mapa));
                } else {
                    sessionStorage.removeItem(CHAVE_CONTEXTO_VISUAL_LAUDOS);
                }
            } catch (_) {
                // armazenamento opcional
            }

            return mapa;
        }

        function lerContextoVisualLaudosStorage() {
            try {
                const bruto = sessionStorage.getItem(CHAVE_CONTEXTO_VISUAL_LAUDOS);
                if (!bruto) return {};
                return sanitizarMapaContextoVisualLaudos(JSON.parse(bruto));
            } catch (_) {
                return {};
            }
        }

        function registrarContextoVisualLaudo(laudoId, contextoVisual = null) {
            const id = normalizarLaudoAtualId(laudoId);
            const contexto = normalizarContextoVisualSeguro(contextoVisual);
            if (!id || !contexto) return null;

            estado.contextoVisualPorLaudo = persistirContextoVisualLaudosStorage({
                ...(estado.contextoVisualPorLaudo && typeof estado.contextoVisualPorLaudo === "object"
                    ? estado.contextoVisualPorLaudo
                    : {}),
                [id]: contexto,
            });

            return contexto;
        }

        function obterContextoVisualLaudoRegistrado(laudoId) {
            const id = normalizarLaudoAtualId(laudoId);
            if (!id) return null;
            return normalizarContextoVisualSeguro(estado.contextoVisualPorLaudo?.[id]);
        }

        function lerRetomadaHomePendenteStorage() {
            try {
                const bruto = sessionStorage.getItem(CHAVE_RETOMADA_HOME_PENDENTE);
                if (!bruto) return null;
                return normalizarRetomadaHomePendenteSeguro(JSON.parse(bruto));
            } catch (_) {
                return null;
            }
        }

        function lerFlagForcaHomeStorage() {
            try {
                return sessionStorage.getItem(CHAVE_FORCE_HOME_LANDING) === "1";
            } catch (_) {
                return false;
            }
        }

        estado.contextoVisualPorLaudo = lerContextoVisualLaudosStorage();

        Object.assign(ctx.shared, {
            atualizarWorkspaceEntryModeNote,
            lerFlagForcaHomeStorage,
            lerContextoVisualLaudosStorage,
            lerRetomadaHomePendenteStorage,
            modoEntradaEvidenceFirstAtivo,
            normalizarRetomadaHomePendenteSeguro,
            obterContextoVisualLaudoRegistrado,
            persistirContextoVisualLaudosStorage,
            registrarContextoVisualLaudo,
            resolverThreadTabInicialPorModoEntrada,
            retomadaHomePendenteEhValida,
            sanitizarMapaContextoVisualLaudos,
        });

        Object.assign(ctx.actions, {
            atualizarEstadoModoEntrada,
            obterContextoVisualLaudoRegistrado,
            registrarContextoVisualLaudo,
        });
    };
})();
