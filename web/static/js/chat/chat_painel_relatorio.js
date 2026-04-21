// ==========================================
// TARIEL CONTROL TOWER — CHAT_PAINEL_RELATORIO.JS
// Papel: fluxo de relatório no painel do chat.
// Responsável por:
// - finalizar inspeção / relatório
// - refletir estado do laudo na UI
// - bloquear/desbloquear composer em modo leitura
// - oferecer reabertura manual após ajustes da mesa
// ==========================================

(function () {
    "use strict";

    const TP = window.TarielChatPainel;
    if (!TP || TP.__relatorioWired__) return;
    TP.__relatorioWired__ = true;
    const PERF = window.TarielPerf || window.TarielCore?.TarielPerf || TP.perf || null;
    const CaseLifecycle = window.TarielCaseLifecycle;

    if (!CaseLifecycle) {
        return;
    }

    PERF?.noteModule?.("chat/chat_painel_relatorio.js", {
        readyState: document.readyState,
    });

    const ESTADOS_LEITURA = new Set(["aguardando", "ajustes", "aprovado"]);
    const TENANT_CAPABILITY_REASONS = {
        inspector_case_finalize:
            "A finalização de laudos está desabilitada para esta empresa pelo Admin-CEO.",
        inspector_send_to_mesa:
            "A conversa com a Mesa Avaliadora está desabilitada para esta empresa pelo Admin-CEO.",
    };

    function ouvirEventoTariel(nome, handler) {
        if (typeof window.TarielInspectorEvents?.on === "function") {
            return window.TarielInspectorEvents.on(nome, handler, {
                target: document,
            });
        }

        document.addEventListener(nome, handler);
        return () => {
            document.removeEventListener(nome, handler);
        };
    }

    function normalizarEstadoRelatorio(valor) {
        const estado = String(valor || "").trim().toLowerCase();

        if (estado === "relatorioativo" || estado === "relatorio_ativo") {
            return "relatorio_ativo";
        }

        if (estado === "semrelatorio" || estado === "sem_relatorio") {
            return "sem_relatorio";
        }

        if (estado === "aguardando" || estado === "aguardando_avaliacao") {
            return "aguardando";
        }

        if (estado === "ajustes" || estado === "aprovado") {
            return estado;
        }

        return estado || "sem_relatorio";
    }

    function tenantCapabilityAtiva(capability, fallback = true) {
        return window.TARIEL?.hasUserCapability?.(capability, fallback) ?? !!fallback;
    }

    function motivoCapacidadeBloqueada(capability) {
        const chave = String(capability || "").trim();
        return TENANT_CAPABILITY_REASONS[chave]
            || "A ação está desabilitada para esta empresa pelo Admin-CEO.";
    }

    const normalizarCaseLifecycleStatus = (valor) =>
        CaseLifecycle.normalizarCaseLifecycleStatus(valor);
    const normalizarActiveOwnerRole = (valor) =>
        CaseLifecycle.normalizarActiveOwnerRole(valor);
    const normalizarSurfaceAction = (valor) =>
        CaseLifecycle.normalizarSurfaceAction(valor);
    const normalizarAllowedSurfaceActions = (valores = []) =>
        CaseLifecycle.normalizarAllowedSurfaceActions(valores);
    const normalizarAllowedLifecycleTransitions = (valores = []) =>
        CaseLifecycle.normalizarAllowedLifecycleTransitions(valores);

    function obterCaseLifecycleStatusSnapshot(snapshotAtual = {}) {
        return normalizarCaseLifecycleStatus(
            snapshotAtual?.case_lifecycle_status ??
            snapshotAtual?.laudo_card?.case_lifecycle_status
        );
    }

    function obterAllowedSurfaceActionsSnapshot(snapshotAtual = {}) {
        const valores = Array.isArray(snapshotAtual?.allowed_surface_actions)
            ? snapshotAtual.allowed_surface_actions
            : Array.isArray(snapshotAtual?.laudo_card?.allowed_surface_actions)
                ? snapshotAtual.laudo_card.allowed_surface_actions
                : [];
        return normalizarAllowedSurfaceActions(valores);
    }

    function obterAllowedLifecycleTransitionsSnapshot(snapshotAtual = {}) {
        const valores = Array.isArray(snapshotAtual?.allowed_lifecycle_transitions)
            ? snapshotAtual.allowed_lifecycle_transitions
            : Array.isArray(snapshotAtual?.laudo_card?.allowed_lifecycle_transitions)
                ? snapshotAtual.laudo_card.allowed_lifecycle_transitions
                : [];
        return normalizarAllowedLifecycleTransitions(valores);
    }

    function snapshotTemContratoAcoes(snapshotAtual = {}) {
        const nextStatuses = Array.isArray(snapshotAtual?.allowed_next_lifecycle_statuses)
            ? snapshotAtual.allowed_next_lifecycle_statuses
            : Array.isArray(snapshotAtual?.laudo_card?.allowed_next_lifecycle_statuses)
                ? snapshotAtual.laudo_card.allowed_next_lifecycle_statuses
                : [];

        return (
            obterAllowedSurfaceActionsSnapshot(snapshotAtual).length > 0 ||
            obterAllowedLifecycleTransitionsSnapshot(snapshotAtual).length > 0 ||
            nextStatuses.length > 0
        );
    }

    function snapshotTemAcaoSurface(snapshotAtual = {}, actionKey = "") {
        const action = normalizarSurfaceAction(actionKey);
        return !!action && obterAllowedSurfaceActionsSnapshot(snapshotAtual).includes(action);
    }

    function resolverEstadoVisualPorLifecycle(lifecycleStatus, fallbackEstado = "") {
        const status = normalizarCaseLifecycleStatus(lifecycleStatus);

        if (
            status === "analise_livre" ||
            status === "pre_laudo" ||
            status === "laudo_em_coleta"
        ) {
            return "relatorio_ativo";
        }

        if (status === "aguardando_mesa" || status === "em_revisao_mesa") {
            return "aguardando";
        }

        if (status === "devolvido_para_correcao") {
            return "ajustes";
        }

        if (status === "aprovado" || status === "emitido") {
            return "aprovado";
        }

        return normalizarEstadoRelatorio(fallbackEstado);
    }

    function resolverPermiteReabrirPorSnapshot(snapshotAtual = {}, fallbackPermiteReabrir = false) {
        if (snapshotTemContratoAcoes(snapshotAtual)) {
            return snapshotTemAcaoSurface(snapshotAtual, "chat_reopen");
        }

        return !!fallbackPermiteReabrir;
    }

    function resolverPermiteFinalizarPorSnapshot(snapshotAtual = {}, fallbackEstado = "") {
        if (snapshotTemContratoAcoes(snapshotAtual)) {
            return snapshotTemAcaoSurface(snapshotAtual, "chat_finalize");
        }

        const estadoNormalizado = normalizarEstadoRelatorio(fallbackEstado);
        return estadoNormalizado === "relatorio_ativo" || estadoNormalizado === "sem_relatorio";
    }

    function obterTipoTemplateAtivo() {
        return String(window.tipoTemplateAtivo || "padrao").trim().toLowerCase() || "padrao";
    }

    function obterLaudoAtualSeguro() {
        const viaApi = window.TarielAPI?.obterLaudoAtualId?.();
        const viaState = TP.state?.laudoAtualId;
        const viaUrl = TP.obterLaudoIdDaURL?.();
        const valor = viaApi || viaState || viaUrl || null;

        const id = Number(valor);
        return Number.isFinite(id) && id > 0 ? id : null;
    }

    function obterEstadoAtualSeguro() {
        const viaApi =
            window.TarielAPI?.obterEstadoRelatorioNormalizado?.() ||
            window.TarielAPI?.obterEstadoRelatorio?.();

        const viaState = TP.state?.estadoRelatorio;
        return normalizarEstadoRelatorio(viaApi || viaState || "sem_relatorio");
    }

    function obterSnapshotStatusRelatorioAtualSeguro() {
        const viaApi = window.TarielAPI?.obterSnapshotStatusRelatorioAtual?.();
        if (viaApi && typeof viaApi === "object") {
            return viaApi;
        }

        return {
            estado: obterEstadoAtualSeguro(),
            laudo_id: obterLaudoAtualSeguro(),
            case_lifecycle_status: "",
            case_workflow_mode: "",
            active_owner_role: "",
            allowed_next_lifecycle_statuses: [],
            allowed_lifecycle_transitions: [],
            allowed_surface_actions: [],
        };
    }

    function homeForcadoAtivo() {
        return !!window.TarielInspectorState?.obterSnapshotEstadoInspectorAtual?.()?.forceHomeLanding
            || document.body.dataset.forceHomeLanding === "true";
    }

    function definirLaudoAtualNoCore(laudoId) {
        const id = Number(laudoId);
        const laudoNormalizado = Number.isFinite(id) && id > 0 ? id : null;

        if (typeof window.TarielInspectorState?.sincronizarEstadoInspector === "function") {
            window.TarielInspectorState.sincronizarEstadoInspector({
                laudoAtualId: laudoNormalizado,
            });
            return;
        }

        TP.sincronizarEstadoPainel?.({ laudoAtualId: laudoNormalizado });
        TP.persistirLaudoAtual?.(laudoNormalizado || "");
        document.body.dataset.laudoAtualId = laudoNormalizado ? String(laudoNormalizado) : "";
    }

    function definirEstadoRelatorioNoCore(estado) {
        const estadoNormalizado = normalizarEstadoRelatorio(estado);

        if (typeof window.TarielInspectorState?.sincronizarEstadoInspector === "function") {
            window.TarielInspectorState.sincronizarEstadoInspector({
                estadoRelatorio: estadoNormalizado,
            });
            return;
        }

        TP.sincronizarEstadoPainel?.({ estadoRelatorio: estadoNormalizado });
        document.body.dataset.estadoRelatorio = estadoNormalizado;
    }

    function obterAvisoBloqueio() {
        return document.getElementById("aviso-laudo-bloqueado");
    }

    function obterTituloAviso() {
        return document.getElementById("aviso-laudo-bloqueado-titulo");
    }

    function obterDescricaoAviso() {
        return document.getElementById("aviso-laudo-bloqueado-descricao");
    }

    function obterBotaoReabrir() {
        return document.getElementById("btn-reabrir-laudo");
    }

    function obterBotoesFinalizar() {
        const botoes = [
            ...Array.from(document.querySelectorAll("[data-finalizar-inspecao]")),
            ...Array.from(document.querySelectorAll("#btn-finalizar-inspecao")),
        ];
        return botoes.filter((botao, indice) => botoes.indexOf(botao) === indice);
    }

    function obterBotaoFinalizar() {
        return obterBotoesFinalizar()[0] || null;
    }

    function solicitarPoliticaDocumentoEmitidoReabertura(snapshotAtual = {}) {
        const lifecycleStatus = normalizarCaseLifecycleStatus(
            snapshotAtual?.case_lifecycle_status ??
            snapshotAtual?.laudo_card?.case_lifecycle_status
        );
        const estadoAtual = normalizarEstadoRelatorio(snapshotAtual?.estado);

        if (lifecycleStatus ? lifecycleStatus !== "emitido" : estadoAtual !== "aprovado") {
            return undefined;
        }

        if (typeof window.confirm !== "function") {
            return { issued_document_policy: "keep_visible" };
        }

        const manterVisivel = window.confirm(
            "Ao reabrir este laudo, deseja manter o PDF final anterior visivel no caso?\n\nOK = manter visivel\nCancelar = escolher outra opcao"
        );

        if (manterVisivel) {
            return { issued_document_policy: "keep_visible" };
        }

        const ocultarDoCaso = window.confirm(
            "Deseja reabrir ocultando o PDF final anterior da area ativa do caso?\n\nOK = ocultar do caso\nCancelar = desistir da reabertura"
        );

        if (!ocultarDoCaso) {
            return null;
        }

        return { issued_document_policy: "hide_from_case" };
    }

    function obterCampoMensagem() {
        return document.getElementById("campo-mensagem");
    }

    function obterMesaWidgetInput() {
        return document.getElementById("mesa-widget-input");
    }

    function obterMesaWidgetBotaoAnexo() {
        return document.getElementById("mesa-widget-btn-anexo");
    }

    function obterMesaWidgetInputAnexo() {
        return document.getElementById("mesa-widget-input-anexo");
    }

    function obterMesaWidgetEnviar() {
        return document.getElementById("mesa-widget-enviar");
    }

    function atualizarAcaoFinalizar({ visivel, desabilitado = false, busy = false, motivo = "" } = {}) {
        const botoes = obterBotoesFinalizar();
        if (!botoes.length) return;
        const capabilityBlocked =
            !!visivel && !tenantCapabilityAtiva("inspector_case_finalize");
        const motivoBloqueio = capabilityBlocked
            ? motivoCapacidadeBloqueada("inspector_case_finalize")
            : String(motivo || "");

        botoes.forEach((btn) => {
            if (!btn.dataset.originalTitle) {
                btn.dataset.originalTitle = btn.getAttribute("title") || "";
            }

            btn.hidden = !visivel;
            btn.disabled = !!desabilitado || capabilityBlocked;
            btn.setAttribute("aria-disabled", String(!!desabilitado || capabilityBlocked));
            btn.setAttribute("aria-busy", String(!!busy));
            btn.title = motivoBloqueio || btn.dataset.originalTitle || "";
        });
    }

    function iaRespondendoAtiva() {
        return !!(
            window.TarielAPI?.estaRespondendo?.() ||
            document.body?.dataset?.iaRespondendo === "true"
        );
    }

    function sincronizarAcaoFinalizarPorAtividadeIA() {
        const snapshotAtual = obterSnapshotStatusRelatorioAtualSeguro();
        const estadoAtual = resolverEstadoVisualPorLifecycle(
            obterCaseLifecycleStatusSnapshot(snapshotAtual),
            snapshotAtual?.estado
        );
        if (!resolverPermiteFinalizarPorSnapshot(snapshotAtual, estadoAtual)) {
            atualizarAcaoFinalizar({ visivel: false });
            return;
        }

        const bloqueadoPorIA = iaRespondendoAtiva();
        atualizarAcaoFinalizar({
            visivel: true,
            desabilitado: bloqueadoPorIA || finalizacaoEmAndamento(),
            busy: finalizacaoEmAndamento(),
            motivo: bloqueadoPorIA
                ? "Aguarde a IA terminar antes de enviar para a mesa."
                : "",
        });
    }

    function configurarCampoMensagemSomenteLeitura(ativo, placeholderBloqueio = "") {
        const campo = obterCampoMensagem();
        if (!campo) return;

        if (!campo.dataset.placeholderOriginal) {
            campo.dataset.placeholderOriginal = campo.getAttribute("placeholder") || "";
        }

        campo.readOnly = !!ativo;
        campo.setAttribute("aria-readonly", String(!!ativo));
        campo.classList.toggle("campo-somente-leitura", !!ativo);

        if (ativo && placeholderBloqueio) {
            campo.setAttribute("placeholder", placeholderBloqueio);
            return;
        }

        campo.setAttribute("placeholder", campo.dataset.placeholderOriginal || "");
    }

    function configurarMesaWidgetSomenteLeitura(ativo, placeholderBloqueio = "") {
        const input = obterMesaWidgetInput();
        const btnAnexo = obterMesaWidgetBotaoAnexo();
        const inputAnexo = obterMesaWidgetInputAnexo();
        const btnEnviar = obterMesaWidgetEnviar();
        const capabilityBlocked = !tenantCapabilityAtiva("inspector_send_to_mesa");
        const placeholderEfetivo = capabilityBlocked
            ? motivoCapacidadeBloqueada("inspector_send_to_mesa")
            : placeholderBloqueio;
        const modoSomenteLeitura = !!ativo || capabilityBlocked;

        if (input) {
            if (!input.dataset.placeholderOriginal) {
                input.dataset.placeholderOriginal = input.getAttribute("placeholder") || "";
            }
            input.disabled = modoSomenteLeitura;
            input.setAttribute("aria-disabled", String(modoSomenteLeitura));
            input.setAttribute(
                "placeholder",
                modoSomenteLeitura && placeholderEfetivo
                    ? placeholderEfetivo
                    : (input.dataset.placeholderOriginal || "")
            );
        }

        if (btnAnexo) {
            btnAnexo.disabled = modoSomenteLeitura;
            btnAnexo.setAttribute("aria-disabled", String(modoSomenteLeitura));
            btnAnexo.title = capabilityBlocked ? placeholderEfetivo : "";
        }

        if (inputAnexo) {
            inputAnexo.disabled = modoSomenteLeitura;
        }

        if (btnEnviar) {
            btnEnviar.disabled = modoSomenteLeitura;
            btnEnviar.setAttribute("aria-disabled", String(modoSomenteLeitura));
            btnEnviar.title = capabilityBlocked ? placeholderEfetivo : "";
        }
    }

    function bloquearUIFinalizacao() {
        document.body.dataset.finalizandoLaudo = "true";
        TP.setRodapeBloqueado?.(true);
        TP.agendarFailsafeFinalizacao?.();
    }

    function desbloquearUIFinalizacao() {
        document.body.dataset.finalizandoLaudo = "false";
        TP.limparFailsafeFinalizacao?.();
        TP.setRodapeBloqueado?.(false);
    }

    function finalizacaoEmAndamento() {
        return document.body.dataset.finalizandoLaudo === "true";
    }

    function ocultarAvisoLaudoBloqueado() {
        const aviso = obterAvisoBloqueio();
        const btnReabrir = obterBotaoReabrir();
        if (aviso) {
            aviso.hidden = true;
            aviso.dataset.status = "";
        }
        if (btnReabrir) {
            btnReabrir.hidden = true;
            btnReabrir.disabled = false;
            btnReabrir.removeAttribute("aria-busy");
        }
    }

    function mostrarAvisoLaudoBloqueado(
        estado,
        { permiteReabrir = false, caseLifecycleStatus = "", activeOwnerRole = "" } = {}
    ) {
        const aviso = obterAvisoBloqueio();
        const titulo = obterTituloAviso();
        const descricao = obterDescricaoAviso();
        const btnReabrir = obterBotaoReabrir();
        if (!aviso || !titulo || !descricao) return;

        const lifecycleStatus = normalizarCaseLifecycleStatus(caseLifecycleStatus);
        const ownerRole = normalizarActiveOwnerRole(activeOwnerRole);

        let tituloTexto = "Laudo em modo leitura";
        let descricaoTexto = "Este laudo está temporariamente bloqueado para novas mensagens.";

        if (estado === "aguardando") {
            tituloTexto = "Laudo aguardando análise da mesa";
            descricaoTexto = ownerRole === "mesa" || lifecycleStatus === "em_revisao_mesa"
                ? "A mesa avaliadora está com a vez neste caso. Novas mensagens ficam bloqueadas até haver retorno."
                : "A mesa avaliadora ainda está revisando este laudo. Novas mensagens ficam bloqueadas até haver retorno.";
        } else if (estado === "ajustes") {
            tituloTexto = "Ajustes solicitados pela mesa";
            descricaoTexto = permiteReabrir
                ? "A mesa respondeu com ajustes. Reabra a inspeção para continuar a conversa e complementar o laudo."
                : "A mesa respondeu com ajustes. A conversa fica bloqueada até a próxima reabertura autorizada.";
        } else if (estado === "aprovado") {
            if (lifecycleStatus === "emitido") {
                tituloTexto = "PDF final emitido";
                descricaoTexto = permiteReabrir
                    ? "O PDF final já foi emitido. O caso fica em leitura até uma nova reabertura autorizada."
                    : "O PDF final já foi emitido e este caso agora está disponível apenas para consulta.";
            } else {
                tituloTexto = "Laudo aprovado pela mesa";
                descricaoTexto = "Este laudo foi aprovado e agora está disponível apenas para consulta.";
            }
        }

        titulo.textContent = tituloTexto;
        descricao.textContent = descricaoTexto;
        aviso.dataset.status = estado;
        aviso.hidden = false;

        if (btnReabrir) {
            btnReabrir.hidden = !permiteReabrir;
        }
    }

    function obterPlaceholderBloqueio(estado, caseLifecycleStatus = "") {
        const lifecycleStatus = normalizarCaseLifecycleStatus(caseLifecycleStatus);
        if (estado === "aguardando") {
            return "Laudo aguardando retorno da mesa avaliadora...";
        }
        if (estado === "ajustes") {
            return "Reabra a inspeção para continuar após os ajustes da mesa...";
        }
        if (estado === "aprovado") {
            if (lifecycleStatus === "emitido") {
                return "PDF final emitido. Este histórico está somente leitura.";
            }
            return "Laudo aprovado. Este histórico está somente leitura.";
        }
        return "";
    }

    function mesaWidgetDeveFicarSomenteLeitura(estado) {
        return ESTADOS_LEITURA.has(normalizarEstadoRelatorio(estado));
    }

    function obterStatusCardPorEstado(estado) {
        if (estado === "relatorio_ativo") return "aberto";
        if (estado === "aguardando") return "aguardando";
        if (estado === "ajustes") return "ajustes";
        if (estado === "aprovado") return "aprovado";
        return null;
    }

    function selecionarCardHistorico(laudoId) {
        const id = Number(laudoId);
        if (!Number.isFinite(id) || id <= 0) return;

        TP.setAtivoNoHistorico?.(id);
        TP.atualizarBreadcrumb?.(id);
        TP.definirLaudoIdNaURL?.(id, { replace: true });
    }

    function aplicarModoLaudoSelecionado({
        laudoId,
        estado,
        permiteReabrir = false,
        caseLifecycleStatus = "",
        activeOwnerRole = "",
        allowedSurfaceActions = [],
        allowedLifecycleTransitions = [],
    } = {}) {
        const id = Number(laudoId);
        if (!Number.isFinite(id) || id <= 0) {
            TP.limparSelecaoAtual?.();
            ocultarAvisoLaudoBloqueado();
            desbloquearUIFinalizacao();
            configurarCampoMensagemSomenteLeitura(false);
            configurarMesaWidgetSomenteLeitura(false);
            atualizarAcaoFinalizar({ visivel: false });
            definirEstadoRelatorioNoCore("sem_relatorio");
            return;
        }

        const estadoBase = normalizarEstadoRelatorio(estado);
        const lifecycleStatus = normalizarCaseLifecycleStatus(caseLifecycleStatus);
        const ownerRole = normalizarActiveOwnerRole(activeOwnerRole);
        const snapshotContrato = {
            estado: estadoBase,
            case_lifecycle_status: lifecycleStatus,
            active_owner_role: ownerRole,
            allowed_surface_actions: normalizarAllowedSurfaceActions(allowedSurfaceActions),
            allowed_lifecycle_transitions: normalizarAllowedLifecycleTransitions(
                allowedLifecycleTransitions
            ),
        };
        const estadoNormalizado = resolverEstadoVisualPorLifecycle(
            lifecycleStatus,
            estadoBase
        );
        const permiteFinalizar = resolverPermiteFinalizarPorSnapshot(
            snapshotContrato,
            estadoNormalizado
        );
        const permiteReabrirEfetivo = resolverPermiteReabrirPorSnapshot(
            snapshotContrato,
            permiteReabrir
        );
        const statusCard = obterStatusCardPorEstado(estadoNormalizado);

        if (typeof window.TarielInspectorState?.sincronizarEstadoInspector === "function") {
            window.TarielInspectorState.sincronizarEstadoInspector({
                forceHomeLanding: false,
            });
        } else {
            document.body.dataset.forceHomeLanding = "false";
        }
        selecionarCardHistorico(id);
        definirLaudoAtualNoCore(id);
        definirEstadoRelatorioNoCore(estadoNormalizado);

        if (statusCard) {
            TP.atualizarBadgeRelatorio?.(id, statusCard);
        }

        if (estadoNormalizado === "relatorio_ativo") {
            ocultarAvisoLaudoBloqueado();
            configurarCampoMensagemSomenteLeitura(false);
            configurarMesaWidgetSomenteLeitura(false);
            atualizarAcaoFinalizar({ visivel: permiteFinalizar, desabilitado: false });
            if (permiteFinalizar) {
                sincronizarAcaoFinalizarPorAtividadeIA();
            }
            desbloquearUIFinalizacao();
            return;
        }

        if (ESTADOS_LEITURA.has(estadoNormalizado)) {
            mostrarAvisoLaudoBloqueado(estadoNormalizado, {
                permiteReabrir: permiteReabrirEfetivo,
                caseLifecycleStatus: lifecycleStatus,
                activeOwnerRole: ownerRole,
            });
            configurarCampoMensagemSomenteLeitura(
                true,
                obterPlaceholderBloqueio(estadoNormalizado, lifecycleStatus)
            );
            configurarMesaWidgetSomenteLeitura(
                mesaWidgetDeveFicarSomenteLeitura(estadoNormalizado),
                mesaWidgetDeveFicarSomenteLeitura(estadoNormalizado)
                    ? obterPlaceholderBloqueio(estadoNormalizado, lifecycleStatus)
                    : ""
            );
            atualizarAcaoFinalizar({ visivel: permiteFinalizar, desabilitado: true });
            desbloquearUIFinalizacao();
            TP.setRodapeBloqueado?.(true);
            return;
        }

        ocultarAvisoLaudoBloqueado();
        configurarCampoMensagemSomenteLeitura(false);
        configurarMesaWidgetSomenteLeitura(false);
        atualizarAcaoFinalizar({ visivel: permiteFinalizar });
        if (permiteFinalizar) {
            sincronizarAcaoFinalizarPorAtividadeIA();
        }
        desbloquearUIFinalizacao();
    }

    async function finalizarInspecaoCompleta() {
        const laudoId = obterLaudoAtualSeguro();
        const tipoTemplate = obterTipoTemplateAtivo();
        const snapshotAtual = obterSnapshotStatusRelatorioAtualSeguro();
        const lifecycleStatusAtual = obterCaseLifecycleStatusSnapshot(snapshotAtual);
        const estadoAtual = resolverEstadoVisualPorLifecycle(
            lifecycleStatusAtual,
            snapshotAtual?.estado ?? obterEstadoAtualSeguro()
        );

        if (!laudoId) {
            TP.toast?.("Não há laudo selecionado para finalizar.", "erro", 3000);
            return null;
        }

        if (iaRespondendoAtiva()) {
            sincronizarAcaoFinalizarPorAtividadeIA();
            TP.toast?.("Aguarde a IA terminar antes de enviar para a mesa.", "aviso", 3000);
            return null;
        }

        if (finalizacaoEmAndamento()) {
            TP.toast?.("A finalização já está em andamento.", "aviso", 2500);
            return null;
        }

        if (!tenantCapabilityAtiva("inspector_case_finalize")) {
            atualizarAcaoFinalizar({
                visivel: true,
                desabilitado: true,
                motivo: motivoCapacidadeBloqueada("inspector_case_finalize"),
            });
            TP.toast?.(motivoCapacidadeBloqueada("inspector_case_finalize"), "aviso", 3200);
            return null;
        }

        if (!resolverPermiteFinalizarPorSnapshot(snapshotAtual, estadoAtual)) {
            TP.toast?.("Somente laudos em coleta podem ser enviados para a mesa.", "aviso", 3000);
            return null;
        }

        TP.log?.("info", `Finalizando laudo ${laudoId} com template ${tipoTemplate}.`);

        const snapshotAntesFinalizacao = snapshotAtual;
        bloquearUIFinalizacao();
        aplicarModoLaudoSelecionado({
            laudoId,
            estado: "aguardando",
            permiteReabrir: false,
            caseLifecycleStatus: "aguardando_mesa",
            allowedSurfaceActions: [],
            allowedLifecycleTransitions: [],
        });

        try {
            const resposta = await window.TarielAPI?.finalizarRelatorio?.({
                tipoTemplate,
                direto: true,
            });

            if (!resposta) {
                throw new Error("FINALIZACAO_SEM_RESPOSTA");
            }

            sincronizarEstadoRelatorioNaUI(resposta);

            TP.emitir?.("tariel:finalizacao-ui-concluida", {
                laudoId,
                tipoTemplate,
            });

            return resposta;
        } catch (erro) {
            TP.log?.("error", "Falha ao finalizar inspeção:", erro);
            aplicarModoLaudoSelecionado({
                laudoId,
                estado: snapshotAntesFinalizacao?.estado ?? "relatorio_ativo",
                permiteReabrir: !!(
                    snapshotAntesFinalizacao?.permite_reabrir ??
                    snapshotAntesFinalizacao?.laudo_card?.permite_reabrir
                ),
                caseLifecycleStatus: obterCaseLifecycleStatusSnapshot(snapshotAntesFinalizacao),
                activeOwnerRole:
                    snapshotAntesFinalizacao?.active_owner_role ??
                    snapshotAntesFinalizacao?.laudo_card?.active_owner_role ??
                    "",
                allowedSurfaceActions: obterAllowedSurfaceActionsSnapshot(snapshotAntesFinalizacao),
                allowedLifecycleTransitions: obterAllowedLifecycleTransitionsSnapshot(
                    snapshotAntesFinalizacao
                ),
            });
            desbloquearUIFinalizacao();
            TP.toast?.("Erro ao tentar finalizar a inspeção.", "erro", 3500);
            return null;
        }
    }

    async function reabrirLaudoAtual() {
        const laudoId = obterLaudoAtualSeguro();
        const btn = obterBotaoReabrir();
        const snapshotAtual = obterSnapshotStatusRelatorioAtualSeguro();
        const estadoAtual = resolverEstadoVisualPorLifecycle(
            obterCaseLifecycleStatusSnapshot(snapshotAtual),
            snapshotAtual?.estado ?? obterEstadoAtualSeguro()
        );
        const permiteReabrir = resolverPermiteReabrirPorSnapshot(
            snapshotAtual,
            !!(snapshotAtual?.permite_reabrir ?? snapshotAtual?.laudo_card?.permite_reabrir)
        );

        if (!laudoId) {
            TP.toast?.("Nenhum laudo selecionado para reabrir.", "aviso", 2600);
            return null;
        }

        if (!permiteReabrir) {
            TP.toast?.("Este laudo não pode ser reaberto neste momento.", "aviso", 2800);
            return null;
        }

        if (!window.TarielAPI?.reabrirLaudo) {
            TP.toast?.("A reabertura do laudo não está disponível agora.", "erro", 3200);
            return null;
        }

        const payloadReabertura = solicitarPoliticaDocumentoEmitidoReabertura(snapshotAtual);
        if (payloadReabertura === null) {
            return null;
        }

        if (btn) {
            btn.disabled = true;
            btn.setAttribute("aria-busy", "true");
        }

        try {
            const resposta = await window.TarielAPI.reabrirLaudo(laudoId, payloadReabertura);
            if (resposta) {
                sincronizarEstadoRelatorioNaUI(resposta);
                TP.toast?.(
                    resposta?.message || "Inspeção reaberta com sucesso.",
                    "sucesso",
                    2400
                );
            }
            return resposta;
        } catch (erro) {
            TP.log?.("error", "Falha ao reabrir laudo:", erro);
            TP.toast?.(
                String(erro?.message || "Não foi possível reabrir este laudo."),
                "erro",
                3200
            );
            return null;
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.removeAttribute("aria-busy");
            }
        }
    }

    function sincronizarEstadoRelatorioNaUI(dados = {}) {
        const snapshotAtual = obterSnapshotStatusRelatorioAtualSeguro();
        const estadoRecebido =
            dados.estado ??
            snapshotAtual?.estado ??
            window.TarielAPI?.obterEstadoRelatorioNormalizado?.() ??
            window.TarielAPI?.obterEstadoRelatorio?.() ??
            TP.state?.estadoRelatorio;

        const laudoIdRecebido =
            dados.laudo_id ??
            dados.laudoId ??
            dados?.laudo_card?.id ??
            snapshotAtual?.laudo_id ??
            snapshotAtual?.laudoId ??
            snapshotAtual?.laudo_card?.id ??
            window.TarielAPI?.obterLaudoAtualId?.() ??
            TP.state?.laudoAtualId ??
            TP.obterLaudoIdDaURL?.();

        const caseLifecycleStatus = normalizarCaseLifecycleStatus(
            dados.case_lifecycle_status ??
            dados?.laudo_card?.case_lifecycle_status ??
            snapshotAtual?.case_lifecycle_status ??
            snapshotAtual?.laudo_card?.case_lifecycle_status
        );
        const activeOwnerRole = normalizarActiveOwnerRole(
            dados.active_owner_role ??
            dados?.laudo_card?.active_owner_role ??
            snapshotAtual?.active_owner_role ??
            snapshotAtual?.laudo_card?.active_owner_role
        );
        const allowedSurfaceActions = normalizarAllowedSurfaceActions(
            Array.isArray(dados.allowed_surface_actions)
                ? dados.allowed_surface_actions
                : Array.isArray(dados?.laudo_card?.allowed_surface_actions)
                    ? dados.laudo_card.allowed_surface_actions
                    : Array.isArray(snapshotAtual?.allowed_surface_actions)
                        ? snapshotAtual.allowed_surface_actions
                        : Array.isArray(snapshotAtual?.laudo_card?.allowed_surface_actions)
                            ? snapshotAtual.laudo_card.allowed_surface_actions
                            : []
        );
        const allowedLifecycleTransitions = normalizarAllowedLifecycleTransitions(
            Array.isArray(dados.allowed_lifecycle_transitions)
                ? dados.allowed_lifecycle_transitions
                : Array.isArray(dados?.laudo_card?.allowed_lifecycle_transitions)
                    ? dados.laudo_card.allowed_lifecycle_transitions
                    : Array.isArray(snapshotAtual?.allowed_lifecycle_transitions)
                        ? snapshotAtual.allowed_lifecycle_transitions
                        : Array.isArray(snapshotAtual?.laudo_card?.allowed_lifecycle_transitions)
                            ? snapshotAtual.laudo_card.allowed_lifecycle_transitions
                            : []
        );
        const estado = resolverEstadoVisualPorLifecycle(
            caseLifecycleStatus,
            estadoRecebido
        );
        const laudoId = Number(laudoIdRecebido) || null;
        const permiteReabrir = !!(
            dados.permite_reabrir ??
            dados?.laudo_card?.permite_reabrir ??
            snapshotAtual?.permite_reabrir ??
            snapshotAtual?.laudo_card?.permite_reabrir
        );

        TP.debug?.("Sincronizando estado do relatório na UI:", {
            estado,
            laudoId,
            permiteReabrir,
            caseLifecycleStatus,
            activeOwnerRole,
            allowedSurfaceActions,
        });

        if (homeForcadoAtivo() && estado !== "sem_relatorio") {
            TP.debug?.("Sincronização automática ignorada por Home forçado.");
            return;
        }

        if (estado === "sem_relatorio") {
            aplicarModoLaudoSelecionado({
                laudoId: null,
                estado,
                permiteReabrir,
                caseLifecycleStatus,
                activeOwnerRole,
                allowedSurfaceActions,
                allowedLifecycleTransitions,
            });
            return;
        }

        aplicarModoLaudoSelecionado({
            laudoId,
            estado,
            permiteReabrir,
            caseLifecycleStatus,
            activeOwnerRole,
            allowedSurfaceActions,
            allowedLifecycleTransitions,
        });
    }

    function handleRelatorioIniciado(evento) {
        const laudoId = Number(
            evento?.detail?.laudoId ||
            evento?.detail?.laudo_id ||
            0
        ) || null;

        if (!laudoId) return;

        TP.debug?.(`Evento de relatório iniciado recebido para laudo ${laudoId}.`);
        aplicarModoLaudoSelecionado({
            laudoId,
            estado: "relatorio_ativo",
            permiteReabrir: false,
            caseLifecycleStatus: "laudo_em_coleta",
            activeOwnerRole: "inspetor",
            allowedSurfaceActions: ["chat_finalize"],
        });
    }

    function handleRelatorioFinalizado(evento) {
        const laudoId = Number(
            evento?.detail?.laudoId ||
            evento?.detail?.laudo_id ||
            0
        ) || obterLaudoAtualSeguro();
        const detail = evento?.detail || {};

        if (!laudoId) {
            desbloquearUIFinalizacao();
            return;
        }

        TP.log?.("info", `Evento de relatório finalizado recebido para laudo ${laudoId}.`);
        if (detail && typeof detail === "object" && (detail.estado || detail.case_lifecycle_status)) {
            sincronizarEstadoRelatorioNaUI({
                ...detail,
                laudo_id: detail.laudo_id ?? detail.laudoId ?? laudoId,
            });
            return;
        }

        aplicarModoLaudoSelecionado({
            laudoId,
            estado: "aguardando",
            permiteReabrir: false,
            caseLifecycleStatus: "aguardando_mesa",
            activeOwnerRole: "mesa",
            allowedSurfaceActions: [],
        });
    }

    function handleRelatorioCancelado() {
        TP.log?.("info", "Evento de cancelamento de relatório recebido.");
        aplicarModoLaudoSelecionado({
            laudoId: null,
            estado: "sem_relatorio",
            permiteReabrir: false,
        });
    }

    function handleEstadoRelatorio(evento) {
        sincronizarEstadoRelatorioNaUI(evento?.detail || {});
    }

    function bindEventosRelatorio() {
        ouvirEventoTariel("tariel:relatorio-iniciado", handleRelatorioIniciado);
        ouvirEventoTariel("tariel:relatorio-finalizado", handleRelatorioFinalizado);
        ouvirEventoTariel("tariel:cancelar-relatorio", handleRelatorioCancelado);
        ouvirEventoTariel("tariel:estado-relatorio", handleEstadoRelatorio);
        ouvirEventoTariel("tariel:chat-status", () => {
            window.requestAnimationFrame(() => {
                sincronizarAcaoFinalizarPorAtividadeIA();
            });
        });

        const btnReabrir = obterBotaoReabrir();
        if (btnReabrir && btnReabrir.dataset.relatorioBound !== "true") {
            btnReabrir.dataset.relatorioBound = "true";
            btnReabrir.addEventListener("click", () => {
                reabrirLaudoAtual();
            });
        }
    }

    function bindFinalizacaoAoUnload() {
        window.addEventListener("pagehide", () => {
            TP.limparFailsafeFinalizacao?.();
            document.body.dataset.finalizandoLaudo = "false";
        });
    }

    if (PERF?.enabled) {
        const finalizarInspecaoCompletaOriginal = finalizarInspecaoCompleta;
        finalizarInspecaoCompleta = async function finalizarInspecaoCompletaComPerf(...args) {
            return PERF.measureAsync(
                "chat_painel_relatorio.finalizarInspecaoCompleta",
                () => finalizarInspecaoCompletaOriginal.apply(this, args),
                {
                    category: "function",
                    detail: {
                        laudoId: obterLaudoAtualSeguro(),
                    },
                }
            );
        };

        const reabrirLaudoAtualOriginal = reabrirLaudoAtual;
        reabrirLaudoAtual = async function reabrirLaudoAtualComPerf(...args) {
            return PERF.measureAsync(
                "chat_painel_relatorio.reabrirLaudoAtual",
                () => reabrirLaudoAtualOriginal.apply(this, args),
                {
                    category: "function",
                    detail: {
                        laudoId: obterLaudoAtualSeguro(),
                    },
                }
            );
        };

        const sincronizarEstadoRelatorioNaUIOriginal = sincronizarEstadoRelatorioNaUI;
        sincronizarEstadoRelatorioNaUI = function sincronizarEstadoRelatorioNaUIComPerf(...args) {
            return PERF.measureSync(
                "chat_painel_relatorio.sincronizarEstadoRelatorioNaUI",
                () => sincronizarEstadoRelatorioNaUIOriginal.apply(this, args),
                {
                    category: "state",
                    detail: {
                        laudoId: obterLaudoAtualSeguro(),
                        estado: obterEstadoAtualSeguro(),
                    },
                }
            );
        };
    }

    TP.registrarBootTask("chat_painel_relatorio", () => {
        bindEventosRelatorio();
        bindFinalizacaoAoUnload();
        sincronizarEstadoRelatorioNaUI();
        return true;
    });

    window.finalizarInspecaoCompleta = finalizarInspecaoCompleta;

    Object.assign(TP, {
        finalizarInspecaoCompleta,
        reabrirLaudoAtual,
        sincronizarEstadoRelatorioNaUI,
        normalizarEstadoRelatorio,
    });
})();
