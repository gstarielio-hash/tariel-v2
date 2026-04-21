(function () {
    "use strict";

    const inspectorRuntime = window.TarielInspectorRuntime || null;
    const modules = typeof inspectorRuntime?.resolveModuleBucket === "function"
        ? inspectorRuntime.resolveModuleBucket("TarielInspetorModules")
        : (window.TarielInspetorModules = window.TarielInspetorModules || {});

    modules.registerModals = function registerModals(ctx) {
        const estado = ctx.state;
        const el = ctx.elements;
        const { mostrarToast, normalizarTipoTemplate, NOMES_TEMPLATES, obterElementosFocaveis, escaparHtml } = ctx.shared;
        const inserirTextoNoComposer = (...args) => ctx.actions.inserirTextoNoComposer?.(...args);
        const GATILHOS_MODAL_NOVA_INSPECAO = '[aria-controls="modal-nova-inspecao"]';

    function tenantCapabilityAtiva(capability, fallback = true) {
        return window.TARIEL?.hasUserCapability?.(capability, fallback) ?? !!fallback;
    }

    function motivoCapacidadeBloqueada(capability) {
        if (String(capability || "").trim() === "inspector_case_create") {
            return "A criação de laudos está desabilitada para esta empresa pelo Admin-CEO.";
        }
        return "A ação está desabilitada para esta empresa pelo Admin-CEO.";
    }

    function obterGatilhosModalNovaInspecao() {
        return Array.from(document.querySelectorAll(GATILHOS_MODAL_NOVA_INSPECAO));
    }

    function sincronizarDisponibilidadeNovaInspecao() {
        const permitido = tenantCapabilityAtiva("inspector_case_create");
        const motivo = permitido ? "" : motivoCapacidadeBloqueada("inspector_case_create");

        obterGatilhosModalNovaInspecao().forEach((botao) => {
            botao.disabled = !permitido;
            botao.setAttribute("aria-disabled", String(!permitido));
            botao.title = motivo;
        });
    }

    function obterTextoCampoModal(campo) {
        return String(campo?.value || "").trim();
    }

    function criarContextoVisualPadrao() {
        return {
            title: "Assistente Tariel IA",
            subtitle: "Conversa inicial • nenhum laudo ativo",
            statusBadge: "CHAT LIVRE",
        };
    }

    function montarTempoWorkspaceResumo(valorIso = "") {
        const texto = String(valorIso || "").trim();
        if (!texto) return "agora";

        try {
            const data = new Date(texto);
            if (Number.isNaN(data.getTime())) return "agora";

            const diffMs = Date.now() - data.getTime();
            const diffMin = Math.max(1, Math.round(diffMs / 60000));
            if (diffMin < 60) return `há ${diffMin}min`;

            const diffHoras = Math.round(diffMin / 60);
            if (diffHoras < 24) return `há ${diffHoras} horas`;

            const diffDias = Math.round(diffHoras / 24);
            return diffDias <= 1 ? "ontem" : `há ${diffDias} dias`;
        } catch (_) {
            return "agora";
        }
    }

    function extrairContextoVisualWorkspace(fonte = {}) {
        const origem = (fonte && typeof fonte === "object") ? fonte : {};
        const card = origem?.laudo_card || origem?.laudoCard || origem?.card || {};
        const titulo = String(
            origem?.workspaceTitle ||
            origem?.homeTitle ||
            origem?.title ||
            card?.display_title ||
            card?.titulo ||
            ""
        ).trim();
        const subtitulo = String(
            origem?.workspaceSubtitle ||
            origem?.homeSubtitle ||
            origem?.subtitle ||
            card?.display_subtitle ||
            card?.subtitle ||
            ""
        ).trim();
        const badge = String(
            origem?.workspaceStatus ||
            origem?.homeStatus ||
            origem?.statusBadge ||
            card?.status_badge ||
            card?.status_card_label ||
            ""
        ).trim();

        const fallback = criarContextoVisualPadrao();
        const contexto = {
            title: titulo || fallback.title,
            subtitle: subtitulo || fallback.subtitle,
            statusBadge: (badge || fallback.statusBadge).toUpperCase(),
        };

        if (!subtitulo && origem?.criado_em_iso) {
            contexto.subtitle = `Laudo em andamento • ${montarTempoWorkspaceResumo(origem.criado_em_iso)}`;
        }

        if (!subtitulo && card?.hora_br) {
            contexto.subtitle = `${contexto.title} • Atualizado às ${card.hora_br}`;
        }

        return contexto;
    }

    function aplicarContextoVisualWorkspace(contexto = {}) {
        const fallback = criarContextoVisualPadrao();
        estado.workspaceVisualContext = {
            title: String(contexto?.title || estado.workspaceVisualContext?.title || fallback.title).trim() || fallback.title,
            subtitle: String(contexto?.subtitle || estado.workspaceVisualContext?.subtitle || fallback.subtitle).trim() || fallback.subtitle,
            statusBadge: String(contexto?.statusBadge || estado.workspaceVisualContext?.statusBadge || fallback.statusBadge).trim().toUpperCase() || fallback.statusBadge,
        };

        if (el.workspaceTituloLaudo) {
            el.workspaceTituloLaudo.textContent = estado.workspaceVisualContext.title;
        }
        if (el.workspaceSubtituloLaudo) {
            el.workspaceSubtituloLaudo.textContent = estado.workspaceVisualContext.subtitle;
        }
        if (el.workspaceStatusBadge) {
            el.workspaceStatusBadge.textContent = estado.workspaceVisualContext.statusBadge;
        }
    }

    function criarContextoVisualDoModal() {
        const equipamento = obterTextoCampoModal(el.inputLocalInspecao);
        const cliente = obterTextoCampoModal(el.inputClienteInspecao);
        const unidade = obterTextoCampoModal(el.inputUnidadeInspecao);
        return {
            title: equipamento || criarContextoVisualPadrao().title,
            subtitle: [cliente, unidade, "Iniciado agora"].filter(Boolean).join(" • "),
            statusBadge: "EM COLETA",
        };
    }

    function normalizarModoEntradaPreferenciaModal(valor, fallback = estado.entryModePreferenceDefault || "auto_recommended") {
        const texto = String(valor || "").trim().toLowerCase();
        if (texto === "chat_first" || texto === "chatfirst" || texto === "conversa") {
            return "chat_first";
        }
        if (
            texto === "evidence_first" ||
            texto === "evidencefirst" ||
            texto === "evidencia" ||
            texto === "evidencias" ||
            texto === "guided" ||
            texto === "checklist"
        ) {
            return "evidence_first";
        }
        if (
            texto === "auto_recommended" ||
            texto === "autorecommended" ||
            texto === "auto" ||
            texto === "automatico" ||
            texto === "automatic"
        ) {
            return "auto_recommended";
        }

        const fallbackNormalizado = String(fallback || "").trim().toLowerCase();
        if (fallbackNormalizado === "chat_first" || fallbackNormalizado === "evidence_first") {
            return fallbackNormalizado;
        }
        return "auto_recommended";
    }

    function obterModoEntradaSelecionadoModal() {
        const selecionado = Array.from(el.entryModeInputs || []).find((input) => input?.checked);
        return normalizarModoEntradaPreferenciaModal(selecionado?.value);
    }

    function selecionarModoEntradaModal(valor) {
        const preferencia = normalizarModoEntradaPreferenciaModal(valor);
        const radios = Array.from(el.entryModeInputs || []);
        if (!radios.length) return preferencia;

        let aplicado = false;
        radios.forEach((input) => {
            if (!input) return;
            const ativo = String(input.value || "").trim() === preferencia;
            input.checked = ativo;
            aplicado = aplicado || ativo;
        });

        if (!aplicado) {
            const fallback = radios.find((input) => String(input?.value || "").trim() === "auto_recommended");
            if (fallback) {
                fallback.checked = true;
                return "auto_recommended";
            }
        }

        return obterModoEntradaSelecionadoModal();
    }

    function atualizarResumoModoEntradaModal() {
        if (!el.modalEntryModeSummary) return;

        const preferencia = obterModoEntradaSelecionadoModal();
        if (preferencia === "chat_first") {
            el.modalEntryModeSummary.textContent =
                "A coleta abre priorizando a conversa técnica e a narrativa do inspetor.";
            return;
        }

        if (preferencia === "evidence_first") {
            el.modalEntryModeSummary.textContent =
                "A coleta abre priorizando anexos, fotos e vínculo de evidências antes da conversa longa.";
            return;
        }

        const ultimoModo = String(estado.entryModeLastCaseMode || "").trim();
        if (estado.entryModeRememberLastCaseMode && ultimoModo) {
            const rotuloUltimoModo = ultimoModo === "evidence_first"
                ? "Evidências primeiro"
                : "Chat primeiro";
            el.modalEntryModeSummary.textContent =
                `O sistema poderá reaproveitar o último modo efetivo (${rotuloUltimoModo}) se não houver regra mais forte.`;
            return;
        }

        el.modalEntryModeSummary.textContent =
            "O sistema escolherá o foco inicial mais adequado se houver regra mais forte.";
    }

    function obterNomeTemplateSelecionadoModal({ fallback = "Modelo técnico" } = {}) {
        const valorSelecionado = String(el.selectTemplate?.value || "").trim();
        if (!valorSelecionado) return fallback;

        const opcaoSelecionada = obterOpcaoSelecionadaTemplate();
        const texto = String(
            opcaoSelecionada?.textContent ||
            NOMES_TEMPLATES[normalizarTipoTemplate(valorSelecionado)] ||
            fallback
        ).trim();

        return texto || fallback;
    }

    function montarNomeAutomaticoInspecao() {
        const modelo = obterNomeTemplateSelecionadoModal({ fallback: "" });
        const cliente = obterTextoCampoModal(el.inputClienteInspecao);
        const unidade = obterTextoCampoModal(el.inputUnidadeInspecao);
        const equipamento = obterTextoCampoModal(el.inputLocalInspecao);
        const partes = [];

        if (equipamento) {
            partes.push(equipamento);
        } else if (modelo) {
            partes.push(modelo);
        }
        if (cliente) partes.push(cliente);
        if (unidade) {
            partes.push(unidade);
        }

        return partes.join(" — ") || "Equipamento — Cliente — Unidade";
    }

    function nomeManualInspecaoEstaAtivo() {
        return !el.inputNomeInspecao?.hidden;
    }

    function obterNomeInspecaoAtual() {
        const nomeManual = obterTextoCampoModal(el.inputNomeInspecao);
        if (nomeManualInspecaoEstaAtivo() && nomeManual) {
            return nomeManual;
        }

        return montarNomeAutomaticoInspecao();
    }

    function atualizarPreviewNomeInspecao() {
        const nomeAtual = obterNomeInspecaoAtual();
        if (el.previewNomeInspecao) {
            el.previewNomeInspecao.textContent = nomeAtual;
        }

        if (nomeManualInspecaoEstaAtivo() && !obterTextoCampoModal(el.inputNomeInspecao)) {
            el.inputNomeInspecao.placeholder = nomeAtual;
        }
    }

    function atualizarToggleNomeInspecao() {
        if (!el.btnEditarNomeInspecao) return;
        el.btnEditarNomeInspecao.textContent = nomeManualInspecaoEstaAtivo()
            ? "Usar automático"
            : "Editar nome";
    }

    function toggleEdicaoNomeInspecao({ forcarVisivel = null } = {}) {
        if (!el.inputNomeInspecao) return;

        const deveMostrar = typeof forcarVisivel === "boolean"
            ? forcarVisivel
            : el.inputNomeInspecao.hidden;

        if (deveMostrar) {
            el.inputNomeInspecao.hidden = false;
            if (!obterTextoCampoModal(el.inputNomeInspecao)) {
                el.inputNomeInspecao.value = montarNomeAutomaticoInspecao();
            }
            atualizarToggleNomeInspecao();
            atualizarPreviewNomeInspecao();
            window.setTimeout(() => {
                el.inputNomeInspecao?.focus?.({ preventScroll: true });
                el.inputNomeInspecao?.select?.();
            }, 0);
            return;
        }

        el.inputNomeInspecao.value = "";
        el.inputNomeInspecao.hidden = true;
        atualizarToggleNomeInspecao();
        atualizarPreviewNomeInspecao();
    }

    function modalNovaInspecaoTemAlteracoes() {
        const modoEntradaPadrao = normalizarModoEntradaPreferenciaModal(
            estado.entryModePreferenceDefault || "auto_recommended"
        );
        return Boolean(
            String(el.selectTemplate?.value || "").trim() ||
            obterTextoCampoModal(el.inputClienteInspecao) ||
            obterTextoCampoModal(el.inputUnidadeInspecao) ||
            obterTextoCampoModal(el.inputLocalInspecao) ||
            obterTextoCampoModal(el.textareaObjetivoInspecao) ||
            obterTextoCampoModal(el.inputNomeInspecao) ||
            obterModoEntradaSelecionadoModal() !== modoEntradaPadrao
        );
    }

    function modalNovaInspecaoEstaValida() {
        return Boolean(
            String(el.selectTemplate?.value || "").trim() &&
            obterTextoCampoModal(el.inputLocalInspecao) &&
            obterTextoCampoModal(el.inputClienteInspecao) &&
            obterTextoCampoModal(el.inputUnidadeInspecao)
        );
    }

    function atualizarEstadoAcaoModalNovaInspecao() {
        if (!el.btnConfirmarInspecao) return;

        const deveDesabilitar = estado.iniciandoInspecao || !modalNovaInspecaoEstaValida();
        el.btnConfirmarInspecao.disabled = deveDesabilitar;
    }

    function montarResumoContextoModal() {
        const cliente = obterTextoCampoModal(el.inputClienteInspecao);
        const unidade = obterTextoCampoModal(el.inputUnidadeInspecao);
        const equipamento = obterTextoCampoModal(el.inputLocalInspecao);
        const objetivo = obterTextoCampoModal(el.textareaObjetivoInspecao);
        const nomeInspecao = obterNomeInspecaoAtual();

        if (!cliente && !unidade && !equipamento && !objetivo) {
            return "";
        }

        const linhas = ["Contexto inicial da inspeção:"];

        if (nomeInspecao) linhas.push(`- Nome sugerido: ${nomeInspecao}`);
        if (equipamento) linhas.push(`- Equipamento: ${equipamento}`);
        if (cliente) linhas.push(`- Cliente: ${cliente}`);
        if (unidade) linhas.push(`- Unidade: ${unidade}`);
        if (objetivo) linhas.push(`- Contexto inicial: ${objetivo}`);

        linhas.push(
            "Com base nesse contexto, estruture checklist técnico, não conformidades, riscos e plano de ação."
        );

        return linhas.join("\n");
    }

    function coletarDadosFormularioNovaInspecao() {
        const payload = {
            cliente: obterTextoCampoModal(el.inputClienteInspecao),
            unidade: obterTextoCampoModal(el.inputUnidadeInspecao),
            local_inspecao: obterTextoCampoModal(el.inputLocalInspecao),
            objetivo: obterTextoCampoModal(el.textareaObjetivoInspecao),
            nome_inspecao: obterNomeInspecaoAtual(),
        };

        return Object.fromEntries(
            Object.entries(payload).filter(([, valor]) => String(valor || "").trim())
        );
    }

    function resetarCamposContextoModal({ manterModelo = false } = {}) {
        if (!manterModelo && el.selectTemplate) {
            selecionarValorSelectTemplateCustom("", {
                emitirEvento: false,
                fechar: false,
                devolverFoco: false,
            });
        }
        if (el.inputClienteInspecao) el.inputClienteInspecao.value = "";
        if (el.inputUnidadeInspecao) el.inputUnidadeInspecao.value = "";
        if (el.inputLocalInspecao) el.inputLocalInspecao.value = "";
        if (el.textareaObjetivoInspecao) el.textareaObjetivoInspecao.value = "";
        if (el.inputNomeInspecao) {
            el.inputNomeInspecao.value = "";
            el.inputNomeInspecao.hidden = true;
        }
        estado.modalNovaInspecaoPrePrompt = "";
        selecionarModoEntradaModal(estado.entryModePreferenceDefault || "auto_recommended");
        atualizarToggleNomeInspecao();
        atualizarPreviewNomeInspecao();
        atualizarResumoModoEntradaModal();
        atualizarEstadoAcaoModalNovaInspecao();
    }

    function valorNumericoSeguro(valor, fallback = 0) {
        const numero = Number(valor);
        return Number.isFinite(numero) ? numero : fallback;
    }

    function textoItemGate(valor, fallback = "—") {
        if (valor === null || valor === undefined) return fallback;
        const texto = String(valor).trim();
        return texto ? texto : fallback;
    }

    function normalizarItemGateQualidade(item = {}) {
        const status = String(item?.status || "").trim().toLowerCase() === "ok" ? "ok" : "faltante";
        return {
            id: textoItemGate(item?.id, ""),
            categoria: textoItemGate(item?.categoria, "campo_critico"),
            titulo: textoItemGate(item?.titulo, "Item de qualidade"),
            status,
            atual: item?.atual,
            minimo: item?.minimo,
            observacao: textoItemGate(item?.observacao, ""),
        };
    }

    function normalizarRoteiroTemplate(payload = {}) {
        const detalhe = payload && typeof payload === "object" ? payload : {};
        return {
            titulo: textoItemGate(detalhe?.titulo, "Roteiro obrigatorio do modelo"),
            descricao: textoItemGate(detalhe?.descricao, ""),
            itens: Array.isArray(detalhe?.itens) ? detalhe.itens : [],
        };
    }

    function normalizarItemRoteiroTemplate(item = {}) {
        return {
            id: textoItemGate(item?.id, ""),
            categoria: textoItemGate(item?.categoria, "coleta"),
            titulo: textoItemGate(item?.titulo, "Ponto obrigatório"),
            descricao: textoItemGate(item?.descricao, ""),
        };
    }

    function rotuloCategoriaRoteiro(categoria = "") {
        const valor = String(categoria || "").trim().toLowerCase();
        if (valor === "campo_critico") return "Campo crítico";
        if (valor === "evidencia") return "Evidência";
        if (valor === "foto") return "Foto";
        if (valor === "ia") return "Assistente";
        if (valor === "formulario") return "Formulário";
        if (valor === "norma") return "Norma";
        return "Coleta";
    }

    function montarMetaItemGate(item) {
        const atual = textoItemGate(item?.atual);
        const minimo = textoItemGate(item?.minimo);

        if (atual === "—" && minimo === "—") return "";
        if (minimo === "—") return `Atual: ${atual}`;
        return `Atual: ${atual} · Mínimo: ${minimo}`;
    }

    function resumoGateQualidade(payload = {}) {
        const resumo = payload?.resumo && typeof payload.resumo === "object" ? payload.resumo : {};
        const textosCampo = valorNumericoSeguro(resumo?.textos_campo);
        const fotos = valorNumericoSeguro(resumo?.fotos);
        const evidencias = valorNumericoSeguro(resumo?.evidencias);
        const respostasIA = valorNumericoSeguro(resumo?.mensagens_ia);
        const mensagem = String(payload?.mensagem || "").trim();

        const linhaResumo = `Coleta atual: ${textosCampo} texto(s), ${fotos} foto(s), ${evidencias} evidencia(s), ${respostasIA} resposta(s) do assistente.`;
        return mensagem ? `${mensagem} ${linhaResumo}` : linhaResumo;
    }

    function renderizarListaGateQualidade(container, itens = [], textoVazio = "Nenhum item.") {
        if (!container) return;

        const listaNormalizada = Array.isArray(itens) ? itens.map(normalizarItemGateQualidade) : [];
        if (!listaNormalizada.length) {
            container.innerHTML = `<li class="item-gate-qualidade item-gate-vazio">${escaparHtml(textoVazio)}</li>`;
            return;
        }

        container.innerHTML = listaNormalizada
            .map((item) => {
                const statusOk = item.status === "ok";
                const icone = statusOk ? "check_circle" : "error";
                const statusTexto = statusOk ? "OK" : "Pendente";
                const meta = montarMetaItemGate(item);
                const observacao = String(item.observacao || "").trim();

                return `
                    <li class="item-gate-qualidade ${statusOk ? "item-gate-ok" : "item-gate-faltante"}">
                        <div class="item-gate-cabecalho">
                            <span class="material-symbols-rounded" aria-hidden="true">${icone}</span>
                            <strong>${escaparHtml(item.titulo)}</strong>
                            <span class="pill-gate-status">${statusTexto}</span>
                        </div>
                        ${meta ? `<p class="item-gate-meta">${escaparHtml(meta)}</p>` : ""}
                        ${observacao ? `<p class="item-gate-obs">${escaparHtml(observacao)}</p>` : ""}
                    </li>
                `;
            })
            .join("");
    }

    function renderizarListaRoteiroTemplate(container, itens = [], textoVazio = "Roteiro indisponível.") {
        if (!container) return;

        const listaNormalizada = Array.isArray(itens) ? itens.map(normalizarItemRoteiroTemplate) : [];
        if (!listaNormalizada.length) {
            container.innerHTML = `<li class="item-gate-qualidade item-gate-vazio">${escaparHtml(textoVazio)}</li>`;
            return;
        }

        container.innerHTML = listaNormalizada
            .map((item) => {
                const descricao = String(item.descricao || "").trim();
                const categoria = rotuloCategoriaRoteiro(item.categoria);

                return `
                    <li class="item-gate-qualidade item-gate-roteiro">
                        <div class="item-gate-cabecalho">
                            <span class="material-symbols-rounded" aria-hidden="true">task_alt</span>
                            <strong>${escaparHtml(item.titulo)}</strong>
                            <span class="pill-gate-status pill-gate-status-roteiro">${escaparHtml(categoria)}</span>
                        </div>
                        ${descricao ? `<p class="item-gate-obs">${escaparHtml(descricao)}</p>` : ""}
                    </li>
                `;
            })
            .join("");
    }

    function normalizarGateOverridePolicy(payload = {}) {
        const detail = payload && typeof payload === "object" ? payload : {};
        const overrideableItems = Array.isArray(detail.overrideable_items)
            ? detail.overrideable_items.filter((item) => item && typeof item === "object")
            : [];
        const hardBlockers = Array.isArray(detail.hard_blockers)
            ? detail.hard_blockers.filter((item) => item && typeof item === "object")
            : [];
        return {
            available: detail.available === true,
            reasonRequired: detail.reason_required !== false,
            matchedOverrideCases: Array.isArray(detail.matched_override_cases)
                ? detail.matched_override_cases.map((item) => String(item || "").trim()).filter(Boolean)
                : [],
            matchedOverrideCaseLabels: Array.isArray(detail.matched_override_case_labels)
                ? detail.matched_override_case_labels.map((item) => String(item || "").trim()).filter(Boolean)
                : [],
            message: String(detail.message || "").trim(),
            responsibilityNotice: String(detail.responsibility_notice || "").trim(),
            validationError: String(detail.validation_error || "").trim(),
            overrideableItems,
            hardBlockers,
        };
    }

    function renderizarListaGateOverrideHumano(container, policy = {}) {
        if (!container) return;

        const items = [];
        if (Array.isArray(policy.overrideableItems)) {
            policy.overrideableItems.forEach((item) => {
                const titulo = String(item?.titulo || "Pendência").trim();
                const labels = Array.isArray(item?.candidate_case_labels)
                    ? item.candidate_case_labels.map((label) => String(label || "").trim()).filter(Boolean)
                    : [];
                items.push({
                    titulo,
                    descricao: labels.join(" · "),
                    tipo: "ok",
                });
            });
        }
        if (!items.length && Array.isArray(policy.matchedOverrideCaseLabels)) {
            policy.matchedOverrideCaseLabels.forEach((label) => {
                const texto = String(label || "").trim();
                if (!texto) return;
                items.push({
                    titulo: texto,
                    descricao: "",
                    tipo: "ok",
                });
            });
        }
        if (!items.length && Array.isArray(policy.hardBlockers)) {
            policy.hardBlockers.forEach((item) => {
                items.push({
                    titulo: String(item?.titulo || "Bloqueio").trim() || "Bloqueio",
                    descricao: "Este ponto ainda exige correção da coleta.",
                    tipo: "blocked",
                });
            });
        }

        if (!items.length) {
            container.innerHTML = '<li class="item-gate-qualidade item-gate-vazio">Nenhuma exceção governada disponível neste momento.</li>';
            return;
        }

        container.innerHTML = items
            .map((item) => `
                <li class="item-gate-qualidade ${item.tipo === "blocked" ? "item-gate-faltante" : "item-gate-ok"}">
                    <div class="item-gate-cabecalho">
                        <span class="material-symbols-rounded" aria-hidden="true">${item.tipo === "blocked" ? "block" : "shield_person"}</span>
                        <strong>${escaparHtml(item.titulo)}</strong>
                    </div>
                    ${item.descricao ? `<p class="item-gate-obs">${escaparHtml(item.descricao)}</p>` : ""}
                </li>
            `)
            .join("");
    }

    function atualizarEstadoBotaoGateOverrideHumano() {
        if (!el.btnGateOverrideContinuar) return;
        const ocupado = estado.gateQualidadeOverrideBusy === true;
        el.btnGateOverrideContinuar.disabled = ocupado;
        el.btnGateOverrideContinuar.textContent = ocupado
            ? "Registrando justificativa..."
            : "Registrar justificativa e continuar";
    }

    async function continuarComOverrideHumanoGateQualidade() {
        const payloadAtual = estado.gateQualidadePayloadAtual || {};
        const policy = normalizarGateOverridePolicy(
            payloadAtual?.human_override_policy || payloadAtual?.humanOverridePolicy || {}
        );
        if (!policy.available) {
            mostrarToast(
                policy.validationError || "Este bloqueio ainda não pode seguir como exceção governada.",
                "aviso",
                3200
            );
            return;
        }

        const justificativa = String(el.textareaGateOverrideJustificativa?.value || "").trim();
        if (justificativa.length < 12) {
            mostrarToast(
                "Informe uma justificativa interna com pelo menos 12 caracteres.",
                "aviso",
                3200
            );
            el.textareaGateOverrideJustificativa?.focus();
            return;
        }

        if (estado.gateQualidadeOverrideBusy) return;
        estado.gateQualidadeOverrideBusy = true;
        atualizarEstadoBotaoGateOverrideHumano();

        try {
            const resposta = await window.TarielAPI?.finalizarRelatorio?.({
                direto: true,
                qualityGateOverride: {
                    enabled: true,
                    reason: justificativa,
                    cases: policy.matchedOverrideCases,
                },
            });
            if (resposta?.success || resposta?.ok) {
                fecharModalGateQualidade();
            }
        } finally {
            estado.gateQualidadeOverrideBusy = false;
            atualizarEstadoBotaoGateOverrideHumano();
        }
    }

    function abrirModalGateQualidade(payload = {}) {
        if (!el.modalGateQualidade) return;

        const tipoTemplate = normalizarTipoTemplate(payload?.tipo_template || estado.tipoTemplateAtivo);
        const nomeTemplate = String(
            payload?.template_nome ||
            NOMES_TEMPLATES[tipoTemplate] ||
            NOMES_TEMPLATES.padrao
        );

        if (el.tituloTemplateGateQualidade) {
            el.tituloTemplateGateQualidade.textContent = nomeTemplate;
        }
        if (el.textoGateQualidadeResumo) {
            el.textoGateQualidadeResumo.textContent = resumoGateQualidade(payload);
        }

        const faltantes = Array.isArray(payload?.faltantes) ? payload.faltantes : [];
        const checklist = Array.isArray(payload?.itens) ? payload.itens : [];
        const roteiroTemplate = normalizarRoteiroTemplate(
            payload?.roteiro_template || payload?.roteiroTemplate || {}
        );
        const overridePolicy = normalizarGateOverridePolicy(
            payload?.human_override_policy || payload?.humanOverridePolicy || {}
        );
        estado.gateQualidadePayloadAtual = payload;
        estado.gateQualidadeOverrideBusy = false;
        atualizarEstadoBotaoGateOverrideHumano();
        if (el.textareaGateOverrideJustificativa) {
            el.textareaGateOverrideJustificativa.value = "";
        }

        if (el.blocoGateRoteiroTemplate) {
            el.blocoGateRoteiroTemplate.hidden = !roteiroTemplate.itens.length;
        }
        if (el.tituloGateRoteiroTemplate) {
            el.tituloGateRoteiroTemplate.textContent = roteiroTemplate.titulo;
        }
        if (el.textoGateRoteiroTemplate) {
            el.textoGateRoteiroTemplate.textContent = roteiroTemplate.descricao;
        }
        renderizarListaRoteiroTemplate(
            el.listaGateRoteiroTemplate,
            roteiroTemplate.itens,
            "O roteiro obrigatorio deste modelo nao foi informado."
        );

        renderizarListaGateQualidade(
            el.listaGateFaltantes,
            faltantes,
            "Nenhum item pendente foi informado pelo servidor."
        );
        renderizarListaGateQualidade(
            el.listaGateChecklist,
            checklist,
            "Checklist indisponível neste momento."
        );
        if (el.blocoGateOverrideHumano) {
            el.blocoGateOverrideHumano.hidden = !(
                overridePolicy.available ||
                overridePolicy.validationError ||
                overridePolicy.message ||
                overridePolicy.hardBlockers.length
            );
        }
        if (el.textoGateOverrideHumano) {
            el.textoGateOverrideHumano.textContent =
                overridePolicy.validationError ||
                overridePolicy.message ||
                "";
        }
        renderizarListaGateOverrideHumano(
            el.listaGateOverrideCasos,
            overridePolicy
        );
        if (el.textoGateOverrideResponsabilidade) {
            el.textoGateOverrideResponsabilidade.textContent =
                overridePolicy.responsibilityNotice || "";
        }
        if (el.textareaGateOverrideJustificativa) {
            el.textareaGateOverrideJustificativa.hidden = !overridePolicy.available;
            el.textareaGateOverrideJustificativa.disabled = !overridePolicy.available;
        }
        if (el.btnGateOverrideContinuar) {
            el.btnGateOverrideContinuar.hidden = !overridePolicy.available;
        }

        estado.ultimoElementoFocado = document.activeElement;

        el.modalGateQualidade.hidden = false;
        el.modalGateQualidade.classList.add("ativo");
        el.modalGateQualidade.setAttribute("aria-hidden", "false");

        document.body.style.overflow = "hidden";

        window.setTimeout(() => {
            if (overridePolicy.available && el.textareaGateOverrideJustificativa && !el.textareaGateOverrideJustificativa.hidden) {
                el.textareaGateOverrideJustificativa.focus();
                return;
            }
            el.btnEntendiGateQualidade?.focus();
        }, 0);
    }

    function fecharModalGateQualidade() {
        if (!el.modalGateQualidade) return;

        el.modalGateQualidade.classList.remove("ativo");
        el.modalGateQualidade.setAttribute("aria-hidden", "true");
        el.modalGateQualidade.hidden = true;

        if (!el.modal?.classList.contains("ativo")) {
            document.body.style.overflow = "";
        }

        estado.gateQualidadePayloadAtual = null;
        estado.gateQualidadeOverrideBusy = false;
        atualizarEstadoBotaoGateOverrideHumano();
        if (el.textareaGateOverrideJustificativa) {
            el.textareaGateOverrideJustificativa.value = "";
        }

        estado.ultimoElementoFocado?.focus?.();
    }

    function tratarTrapFocoModalGate(event) {
        if (event.key !== "Tab" || !el.modalGateQualidade?.classList.contains("ativo")) return;

        const focaveis = obterElementosFocaveis(el.modalGateQualidade);
        if (!focaveis.length) return;

        const primeiro = focaveis[0];
        const ultimo = focaveis[focaveis.length - 1];

        if (event.shiftKey && document.activeElement === primeiro) {
            event.preventDefault();
            ultimo.focus();
            return;
        }

        if (!event.shiftKey && document.activeElement === ultimo) {
            event.preventDefault();
            primeiro.focus();
        }
    }

    function inserirComandoPendenciasNoChat() {
        const aplicado = inserirTextoNoComposer("/pendencias");
        if (aplicado) {
            mostrarToast("Comando /pendencias inserido no chat.", "info", 1800);
            fecharModalGateQualidade();
        }
    }

    function obterOpcaoSelecionadaTemplate() {
        if (!el.selectTemplate) return null;
        const indice = Number(el.selectTemplate.selectedIndex);
        if (Number.isInteger(indice) && indice >= 0) {
            return el.selectTemplate.options[indice] || null;
        }
        return el.selectTemplate.options?.[0] || null;
    }

    function selectTemplateCustomEstaAberto() {
        return !!el.selectTemplateCustom?.classList.contains("aberto");
    }

    function atualizarValorSelectTemplateCustom() {
        if (!el.valorSelectTemplateCustom) return;
        const opcaoSelecionada = obterOpcaoSelecionadaTemplate();
        const valorSelecionado = String(el.selectTemplate?.value || "").trim();
        el.valorSelectTemplateCustom.textContent =
            valorSelecionado
                ? (opcaoSelecionada?.textContent?.trim() || "Selecione um modelo...")
                : "Selecione um modelo...";
    }

    function atualizarEstadoOpcoesSelectTemplateCustom() {
        if (!el.listaSelectTemplateCustom || !el.selectTemplate) return;
        const valorAtual = String(el.selectTemplate.value || "");

        el.listaSelectTemplateCustom
            .querySelectorAll(".modal-select-opcao")
            .forEach((botao) => {
                const selecionada = String(botao.dataset?.valor || "") === valorAtual;
                botao.setAttribute("aria-selected", String(selecionada));
            });
    }

    function renderizarOpcoesSelectTemplateCustom() {
        if (!el.selectTemplate || !el.listaSelectTemplateCustom) return;

        const fragmento = document.createDocumentFragment();
        el.listaSelectTemplateCustom.innerHTML = "";

        const adicionarOpcao = (opcao) => {
            const item = document.createElement("li");
            item.setAttribute("role", "presentation");

            const botao = document.createElement("button");
            botao.type = "button";
            botao.className = "modal-select-opcao";
            botao.setAttribute("role", "option");
            botao.dataset.valor = String(opcao.value || "");
            botao.setAttribute("aria-selected", String(!!opcao.selected));

            if (opcao.disabled) {
                botao.disabled = true;
            }

            const texto = document.createElement("span");
            texto.textContent = opcao.textContent?.trim() || opcao.value || "Sem rótulo";

            const icone = document.createElement("span");
            icone.className = "material-symbols-rounded";
            icone.setAttribute("aria-hidden", "true");
            icone.textContent = "check";

            botao.append(texto, icone);
            item.appendChild(botao);
            fragmento.appendChild(item);
        };

        Array.from(el.selectTemplate.children).forEach((node) => {
            const tag = String(node.tagName || "").toUpperCase();

            if (tag === "OPTGROUP") {
                const titulo = document.createElement("li");
                titulo.className = "modal-select-grupo-label";
                titulo.setAttribute("role", "presentation");
                titulo.textContent = String(node.label || "Categoria");
                fragmento.appendChild(titulo);

                Array.from(node.querySelectorAll("option")).forEach((opcao) => {
                    adicionarOpcao(opcao);
                });
                return;
            }

            if (tag === "OPTION") {
                adicionarOpcao(node);
            }
        });

        el.listaSelectTemplateCustom.appendChild(fragmento);
        atualizarEstadoOpcoesSelectTemplateCustom();
        atualizarValorSelectTemplateCustom();
    }

    function fecharSelectTemplateCustom({ devolverFoco = true } = {}) {
        if (!el.selectTemplateCustom || !el.painelSelectTemplateCustom || !el.btnSelectTemplateCustom) return;
        if (!selectTemplateCustomEstaAberto()) return;

        el.selectTemplateCustom.classList.remove("aberto");
        el.painelSelectTemplateCustom.hidden = true;
        el.btnSelectTemplateCustom.setAttribute("aria-expanded", "false");

        if (devolverFoco) {
            el.btnSelectTemplateCustom.focus();
        }
    }

    function abrirSelectTemplateCustom() {
        if (!el.selectTemplateCustom || !el.painelSelectTemplateCustom || !el.btnSelectTemplateCustom) return;
        if (selectTemplateCustomEstaAberto()) return;

        el.selectTemplateCustom.classList.add("aberto");
        el.painelSelectTemplateCustom.hidden = false;
        el.btnSelectTemplateCustom.setAttribute("aria-expanded", "true");

        const opcaoSelecionada = el.listaSelectTemplateCustom?.querySelector(
            '.modal-select-opcao[aria-selected="true"]:not(:disabled)'
        );
        const primeiraOpcao = el.listaSelectTemplateCustom?.querySelector(
            ".modal-select-opcao:not(:disabled)"
        );
        (opcaoSelecionada || primeiraOpcao)?.focus();
    }

    function selecionarValorSelectTemplateCustom(
        valor,
        { emitirEvento = true, fechar = true, devolverFoco = true } = {}
    ) {
        if (!el.selectTemplate) return;

        const valorLimpo = String(valor || "");
        const existe = Array.from(el.selectTemplate.options || []).some(
            (opcao) => String(opcao.value || "") === valorLimpo
        );

        if (!existe) return;

        const alterou = String(el.selectTemplate.value || "") !== valorLimpo;
        el.selectTemplate.value = valorLimpo;

        atualizarValorSelectTemplateCustom();
        atualizarEstadoOpcoesSelectTemplateCustom();

        if (emitirEvento && alterou) {
            el.selectTemplate.dispatchEvent(new Event("change", { bubbles: true }));
        }

        if (fechar) {
            fecharSelectTemplateCustom({ devolverFoco });
        }
    }

    function moverFocoOpcaoSelectTemplateCustom(direcao = 1, destinoFixo = "") {
        if (!el.listaSelectTemplateCustom) return;

        const opcoes = Array.from(
            el.listaSelectTemplateCustom.querySelectorAll(".modal-select-opcao:not(:disabled)")
        );
        if (!opcoes.length) return;

        if (destinoFixo === "inicio") {
            opcoes[0]?.focus();
            return;
        }

        if (destinoFixo === "fim") {
            opcoes[opcoes.length - 1]?.focus();
            return;
        }

        const atual = document.activeElement?.closest?.(".modal-select-opcao");
        const indiceAtual = opcoes.indexOf(atual);
        const proximoIndice =
            indiceAtual < 0
                ? 0
                : (indiceAtual + direcao + opcoes.length) % opcoes.length;

        opcoes[proximoIndice]?.focus();
    }

    function inicializarSelectTemplateCustom() {
        if (
            !el.selectTemplate ||
            !el.selectTemplateCustom ||
            !el.btnSelectTemplateCustom ||
            !el.painelSelectTemplateCustom ||
            !el.listaSelectTemplateCustom
        ) {
            return;
        }

        renderizarOpcoesSelectTemplateCustom();
        el.selectTemplateCustom.hidden = false;
        el.selectTemplate.classList.add("select-proxy-ativo");
        el.selectTemplate.setAttribute("tabindex", "-1");
        el.selectTemplate.setAttribute("aria-hidden", "true");
        el.painelSelectTemplateCustom.hidden = true;
        el.btnSelectTemplateCustom.setAttribute("aria-expanded", "false");

        el.selectTemplate.addEventListener("change", () => {
            atualizarValorSelectTemplateCustom();
            atualizarEstadoOpcoesSelectTemplateCustom();
        });

        el.btnSelectTemplateCustom.addEventListener("click", () => {
            if (selectTemplateCustomEstaAberto()) {
                fecharSelectTemplateCustom({ devolverFoco: false });
                return;
            }
            abrirSelectTemplateCustom();
        });

        el.btnSelectTemplateCustom.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && selectTemplateCustomEstaAberto()) {
                event.preventDefault();
                fecharSelectTemplateCustom();
                return;
            }

            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                if (!selectTemplateCustomEstaAberto()) {
                    abrirSelectTemplateCustom();
                    return;
                }
                moverFocoOpcaoSelectTemplateCustom(event.key === "ArrowDown" ? 1 : -1);
                return;
            }

            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                if (selectTemplateCustomEstaAberto()) {
                    fecharSelectTemplateCustom({ devolverFoco: false });
                } else {
                    abrirSelectTemplateCustom();
                }
            }
        });

        el.listaSelectTemplateCustom.addEventListener("click", (event) => {
            const botao = event.target?.closest?.(".modal-select-opcao");
            if (!botao || botao.disabled) return;
            selecionarValorSelectTemplateCustom(botao.dataset?.valor || "");
        });

        el.listaSelectTemplateCustom.addEventListener("keydown", (event) => {
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                moverFocoOpcaoSelectTemplateCustom(event.key === "ArrowDown" ? 1 : -1);
                return;
            }

            if (event.key === "Home") {
                event.preventDefault();
                moverFocoOpcaoSelectTemplateCustom(0, "inicio");
                return;
            }

            if (event.key === "End") {
                event.preventDefault();
                moverFocoOpcaoSelectTemplateCustom(0, "fim");
                return;
            }

            if (event.key === "Escape") {
                event.preventDefault();
                fecharSelectTemplateCustom();
                return;
            }

            if (event.key === "Tab") {
                fecharSelectTemplateCustom({ devolverFoco: false });
                return;
            }

            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                const botao = event.target?.closest?.(".modal-select-opcao");
                if (!botao || botao.disabled) return;
                selecionarValorSelectTemplateCustom(botao.dataset?.valor || "");
            }
        });

        document.addEventListener("pointerdown", (event) => {
            if (!selectTemplateCustomEstaAberto()) return;
            if (el.selectTemplateCustom.contains(event.target)) return;
            fecharSelectTemplateCustom({ devolverFoco: false });
        });
    }

    function abrirModalNovaInspecao(config = {}) {
        const configuracao = config instanceof Event ? {} : (config || {});
        if (!el.modal) return;
        if (!tenantCapabilityAtiva("inspector_case_create")) {
            mostrarToast(motivoCapacidadeBloqueada("inspector_case_create"), "aviso", 3200);
            return;
        }

        estado.ultimoElementoFocado = document.activeElement;
        estado.modalNovaInspecaoPrePrompt = String(configuracao?.prePrompt || "").trim();

        resetarCamposContextoModal();

        const tipoPrefill = String(configuracao?.tipoPrefill || "").trim();
        if (tipoPrefill) {
            selecionarValorSelectTemplateCustom(tipoPrefill, {
                emitirEvento: false,
                fechar: false,
                devolverFoco: false,
            });
        }

        atualizarPreviewNomeInspecao();
        atualizarEstadoAcaoModalNovaInspecao();
        sincronizarEstadoVisualNovaInspecao(true);

        el.modal.hidden = false;
        el.modal.classList.add("ativo");
        el.modal.setAttribute("aria-hidden", "false");
        el.btnAbrirModal?.setAttribute("aria-expanded", "true");

        document.body.style.overflow = "hidden";

        window.setTimeout(() => {
            if (tipoPrefill && el.inputClienteInspecao) {
                el.inputClienteInspecao.focus({ preventScroll: true });
                return;
            }
            if (el.btnSelectTemplateCustom && !el.selectTemplateCustom?.hidden) {
                el.btnSelectTemplateCustom.focus();
                return;
            }
            el.selectTemplate?.focus();
        }, 0);
    }

    function fecharModalNovaInspecao({ forcar = false, restaurarFoco = true } = {}) {
        if (!el.modal) return;

        if (!forcar && modalNovaInspecaoTemAlteracoes()) {
            const confirmou = window.confirm("Descartar os dados desta nova inspeção?");
            if (!confirmou) {
                return false;
            }
        }

        el.modal.classList.remove("ativo");
        el.modal.setAttribute("aria-hidden", "true");
        el.modal.hidden = true;
        el.btnAbrirModal?.setAttribute("aria-expanded", "false");
        sincronizarEstadoVisualNovaInspecao(false);

        document.body.style.overflow = "";
        fecharSelectTemplateCustom({ devolverFoco: false });
        resetarCamposContextoModal();
        if (restaurarFoco) {
            estado.ultimoElementoFocado?.focus?.();
        }
        return true;
    }

    function tratarTrapFocoModal(event) {
        if (event.key !== "Tab" || !el.modal?.classList.contains("ativo")) return;

        const focaveis = obterElementosFocaveis(el.modal);
        if (!focaveis.length) return;

        const primeiro = focaveis[0];
        const ultimo = focaveis[focaveis.length - 1];

        if (event.shiftKey && document.activeElement === primeiro) {
            event.preventDefault();
            ultimo.focus();
            return;
        }

        if (!event.shiftKey && document.activeElement === ultimo) {
            event.preventDefault();
            primeiro.focus();
        }
    }

    function sincronizarEstadoVisualNovaInspecao(ativo) {
        const aberto = !!ativo;
        const overlayOwner = aberto ? "new_inspection" : "";

        estado.overlayOwner = overlayOwner;

        document.body.classList.toggle("inspetor-overlay-open", aberto);
        document.body.classList.toggle("inspetor-overlay-new-inspection", aberto);
        document.body.dataset.overlayOwner = overlayOwner;
        document.body.dataset.inspectorOverlayOwner = overlayOwner;

        if (el.overlayHost) {
            el.overlayHost.dataset.overlayActive = aberto ? "true" : "false";
            el.overlayHost.dataset.overlayOwner = overlayOwner;
            el.overlayHost.dataset.inspectorOverlayOwner = overlayOwner;
        }

        if (!el.painelChat) return;

        el.painelChat.dataset.overlayOwner = overlayOwner;
        el.painelChat.dataset.inspectorOverlayOwner = overlayOwner;
        try {
            el.painelChat.inert = aberto;
        } catch (_) {
            if (aberto) {
                el.painelChat.setAttribute("inert", "");
            } else {
                el.painelChat.removeAttribute("inert");
            }
        }
    }

    function bindEventosNovaInspecao() {
        if (estado.eventosNovaInspecaoBound) return;
        estado.eventosNovaInspecaoBound = true;

        const PERF = window.TarielPerf || window.TarielCore?.TarielPerf || null;
        const abrirNovaInspecaoComScreenSync = (...args) =>
            ctx.actions.abrirNovaInspecaoComScreenSync?.(...args);
        const fecharNovaInspecaoComScreenSync = (...args) =>
            ctx.actions.fecharNovaInspecaoComScreenSync?.(...args);
        const iniciarInspecao = (...args) => ctx.actions.iniciarInspecao?.(...args);

        const atualizarModalNovaInspecao = () => {
            atualizarPreviewNomeInspecao();
            atualizarResumoModoEntradaModal();
            atualizarEstadoAcaoModalNovaInspecao();
        };

        el.btnAbrirModal?.addEventListener("click", (event) => {
            event.preventDefault();
            PERF?.begin?.("transition.abrir_nova_inspecao", {
                origem: "btnAbrirModal",
            });
            abrirNovaInspecaoComScreenSync();
        });

        document.querySelectorAll("[data-open-inspecao-modal]").forEach((botao) => {
            botao.addEventListener("click", (event) => {
                event.preventDefault();
                PERF?.begin?.("transition.abrir_nova_inspecao", {
                    origem: botao.id || botao.dataset.openInspecaoModal || "data-open-inspecao-modal",
                });
                abrirNovaInspecaoComScreenSync();
            });
        });

        [el.selectTemplate, el.inputClienteInspecao, el.inputUnidadeInspecao, el.inputLocalInspecao]
            .forEach((campo) => {
                campo?.addEventListener("input", atualizarModalNovaInspecao);
                campo?.addEventListener("change", atualizarModalNovaInspecao);
            });
        el.textareaObjetivoInspecao?.addEventListener("input", atualizarModalNovaInspecao);
        el.entryModeInputs.forEach((input) => {
            input?.addEventListener("change", atualizarModalNovaInspecao);
        });
        el.btnEditarNomeInspecao?.addEventListener("click", () => {
            toggleEdicaoNomeInspecao();
        });
        el.inputNomeInspecao?.addEventListener("input", atualizarPreviewNomeInspecao);

        el.btnFecharModal?.addEventListener("click", () => {
            fecharNovaInspecaoComScreenSync();
        });
        el.btnCancelarModalInspecao?.addEventListener("click", () => {
            fecharNovaInspecaoComScreenSync();
        });
        el.btnFecharModalGateQualidade?.addEventListener("click", fecharModalGateQualidade);
        el.btnEntendiGateQualidade?.addEventListener("click", fecharModalGateQualidade);
        el.btnPreencherGateQualidade?.addEventListener("click", inserirComandoPendenciasNoChat);
        el.btnGateOverrideContinuar?.addEventListener(
            "click",
            continuarComOverrideHumanoGateQualidade
        );

        el.btnConfirmarInspecao?.addEventListener("click", async () => {
            const tipo = String(el.selectTemplate?.value || "").trim();
            const runtimeTipoTemplate = normalizarTipoTemplate(
                el.selectTemplate?.selectedOptions?.[0]?.dataset?.runtimeTemplate || tipo
            );
            if (!tipo || !modalNovaInspecaoEstaValida()) {
                mostrarToast(
                    "Preencha modelo técnico, equipamento, cliente e unidade para iniciar a coleta.",
                    "aviso",
                    2600
                );
                atualizarEstadoAcaoModalNovaInspecao();
                return;
            }

            const contexto = montarResumoContextoModal();
            const prePromptModal = estado.modalNovaInspecaoPrePrompt;
            const contextoVisual = criarContextoVisualDoModal();
            const dadosFormulario = coletarDadosFormularioNovaInspecao();
            const entryModePreference = obterModoEntradaSelecionadoModal();
            aplicarContextoVisualWorkspace(contextoVisual);
            const resposta = await iniciarInspecao(tipo, {
                contextoVisual,
                dadosFormulario,
                entryModePreference,
                runtimeTipoTemplate,
            });
            if (!resposta) return;

            const blocosIniciais = [contexto, prePromptModal].filter(Boolean).join("\n\n");
            if (blocosIniciais && inserirTextoNoComposer(blocosIniciais)) {
                mostrarToast("Contexto da inspeção pronto no campo de mensagem.", "info", 2200);
            }
        });

        el.modal?.addEventListener("click", (event) => {
            if (event.target === el.modal) {
                fecharNovaInspecaoComScreenSync();
            }
        });
        el.modalGateQualidade?.addEventListener("click", (event) => {
            if (event.target === el.modalGateQualidade) {
                fecharModalGateQualidade();
            }
        });

        document.addEventListener("keydown", (event) => {
            if (event.key !== "Escape") return;
            if (el.modal?.classList.contains("ativo") && selectTemplateCustomEstaAberto()) {
                fecharSelectTemplateCustom();
                return;
            }
            if (el.modalGateQualidade?.classList.contains("ativo")) {
                fecharModalGateQualidade();
                return;
            }
            if (el.modal?.classList.contains("ativo")) {
                fecharNovaInspecaoComScreenSync();
            }
        });

        el.modal?.addEventListener("keydown", tratarTrapFocoModal);
        el.modalGateQualidade?.addEventListener("keydown", tratarTrapFocoModalGate);
    }

        sincronizarDisponibilidadeNovaInspecao();

        Object.assign(ctx.actions, {
            obterTextoCampoModal,
            criarContextoVisualPadrao,
            extrairContextoVisualWorkspace,
            aplicarContextoVisualWorkspace,
            criarContextoVisualDoModal,
            normalizarModoEntradaPreferenciaModal,
            obterModoEntradaSelecionadoModal,
            selecionarModoEntradaModal,
            atualizarResumoModoEntradaModal,
            obterNomeTemplateSelecionadoModal,
            montarResumoContextoModal,
            coletarDadosFormularioNovaInspecao,
            atualizarPreviewNomeInspecao,
            toggleEdicaoNomeInspecao,
            modalNovaInspecaoEstaValida,
            resetarCamposContextoModal,
            atualizarEstadoAcaoModalNovaInspecao,
            valorNumericoSeguro,
            textoItemGate,
            normalizarItemGateQualidade,
            normalizarRoteiroTemplate,
            normalizarItemRoteiroTemplate,
            rotuloCategoriaRoteiro,
            montarMetaItemGate,
            resumoGateQualidade,
            renderizarListaGateQualidade,
            renderizarListaRoteiroTemplate,
            normalizarGateOverridePolicy,
            renderizarListaGateOverrideHumano,
            atualizarEstadoBotaoGateOverrideHumano,
            continuarComOverrideHumanoGateQualidade,
            abrirModalGateQualidade,
            fecharModalGateQualidade,
            tratarTrapFocoModalGate,
            inserirComandoPendenciasNoChat,
            obterOpcaoSelecionadaTemplate,
            selectTemplateCustomEstaAberto,
            atualizarValorSelectTemplateCustom,
            atualizarEstadoOpcoesSelectTemplateCustom,
            renderizarOpcoesSelectTemplateCustom,
            fecharSelectTemplateCustom,
            abrirSelectTemplateCustom,
            selecionarValorSelectTemplateCustom,
            moverFocoOpcaoSelectTemplateCustom,
            inicializarSelectTemplateCustom,
            abrirModalNovaInspecao,
            fecharModalNovaInspecao,
            tratarTrapFocoModal,
            bindEventosNovaInspecao,
        });
    };
})();
