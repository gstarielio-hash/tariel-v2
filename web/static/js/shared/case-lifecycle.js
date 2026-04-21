(function () {
    "use strict";

    if (window.TarielCaseLifecycle) {
        return;
    }

    function normalizarCaseLifecycleStatus(valor) {
        const status = String(valor || "").trim().toLowerCase();
        if (
            status === "analise_livre" ||
            status === "pre_laudo" ||
            status === "laudo_em_coleta" ||
            status === "aguardando_mesa" ||
            status === "em_revisao_mesa" ||
            status === "devolvido_para_correcao" ||
            status === "aprovado" ||
            status === "emitido"
        ) {
            return status;
        }

        return "";
    }

    function normalizarAllowedNextLifecycleStatuses(valores = []) {
        if (!Array.isArray(valores)) {
            return [];
        }

        return valores
            .map((item) => normalizarCaseLifecycleStatus(item))
            .filter(Boolean);
    }

    function normalizarCaseWorkflowMode(valor) {
        const modo = String(valor || "").trim().toLowerCase();
        if (
            modo === "analise_livre" ||
            modo === "laudo_guiado" ||
            modo === "laudo_com_mesa"
        ) {
            return modo;
        }

        return "";
    }

    function normalizarActiveOwnerRole(valor) {
        const role = String(valor || "").trim().toLowerCase();
        if (role === "inspetor" || role === "mesa" || role === "none") {
            return role;
        }

        return "";
    }

    function normalizarLifecycleTransitionKind(valor) {
        const kind = String(valor || "").trim().toLowerCase();
        if (
            kind === "analysis" ||
            kind === "advance" ||
            kind === "review" ||
            kind === "approval" ||
            kind === "correction" ||
            kind === "reopen" ||
            kind === "issue"
        ) {
            return kind;
        }

        return "";
    }

    function normalizarPreferredSurface(valor) {
        const surface = String(valor || "").trim().toLowerCase();
        if (
            surface === "chat" ||
            surface === "mesa" ||
            surface === "mobile" ||
            surface === "system"
        ) {
            return surface;
        }

        return "";
    }

    function normalizarSurfaceAction(valor) {
        const action = String(valor || "").trim().toLowerCase();
        if (
            action === "chat_finalize" ||
            action === "chat_reopen" ||
            action === "mesa_approve" ||
            action === "mesa_return" ||
            action === "system_issue"
        ) {
            return action;
        }

        return "";
    }

    function normalizarAllowedSurfaceActions(valores = []) {
        if (!Array.isArray(valores)) {
            return [];
        }

        return Array.from(
            new Set(
                valores
                    .map((item) => normalizarSurfaceAction(item))
                    .filter(Boolean)
            )
        );
    }

    function normalizarAllowedLifecycleTransitions(valores = []) {
        if (!Array.isArray(valores)) {
            return [];
        }

        const dedup = new Set();
        return valores
            .map((item) => {
                if (!item || typeof item !== "object") {
                    return null;
                }

                const targetStatus = normalizarCaseLifecycleStatus(item.target_status);
                if (!targetStatus) {
                    return null;
                }

                const normalized = {
                    target_status: targetStatus,
                    transition_kind: normalizarLifecycleTransitionKind(item.transition_kind),
                    label: String(item.label || "").trim(),
                    owner_role: normalizarActiveOwnerRole(item.owner_role),
                    preferred_surface: normalizarPreferredSurface(item.preferred_surface),
                };
                const key = [
                    normalized.target_status,
                    normalized.transition_kind,
                    normalized.owner_role,
                    normalized.preferred_surface,
                ].join("|");
                if (dedup.has(key)) {
                    return null;
                }
                dedup.add(key);
                return normalized;
            })
            .filter(Boolean);
    }

    window.TarielCaseLifecycle = {
        normalizarCaseLifecycleStatus,
        normalizarAllowedNextLifecycleStatuses,
        normalizarCaseWorkflowMode,
        normalizarActiveOwnerRole,
        normalizarLifecycleTransitionKind,
        normalizarPreferredSurface,
        normalizarSurfaceAction,
        normalizarAllowedSurfaceActions,
        normalizarAllowedLifecycleTransitions,
    };
})();
