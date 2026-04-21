(function () {
    "use strict";

    if (window.TarielClientePortalShell) return;

    window.TarielClientePortalShell = function createTarielClientePortalShell(config = {}) {
        const state = config.state || {};
        const documentRef = config.documentRef || document;
        const $ = typeof config.getById === "function"
            ? config.getById
            : (id) => documentRef.getElementById(id);
        const actions = config.actions || {};
        const helpers = config.helpers || {};
        const storageKeys = config.storageKeys || {};

        const api = typeof helpers.api === "function" ? helpers.api : async () => null;
        const abrirSecaoAdmin = typeof helpers.abrirSecaoAdmin === "function" ? helpers.abrirSecaoAdmin : () => "overview";
        const abrirSecaoChat = typeof helpers.abrirSecaoChat === "function" ? helpers.abrirSecaoChat : () => "overview";
        const abrirSecaoMesa = typeof helpers.abrirSecaoMesa === "function" ? helpers.abrirSecaoMesa : () => "overview";
        const construirPrioridadesPortal = typeof helpers.construirPrioridadesPortal === "function" ? helpers.construirPrioridadesPortal : () => [];
        const escapeAttr = typeof helpers.escapeAttr === "function" ? helpers.escapeAttr : (valor) => String(valor ?? "");
        const escapeHtml = typeof helpers.escapeHtml === "function" ? helpers.escapeHtml : (valor) => String(valor ?? "");
        const formatarInteiro = typeof helpers.formatarInteiro === "function" ? helpers.formatarInteiro : (valor) => String(Number(valor || 0));
        const formatarPercentual = typeof helpers.formatarPercentual === "function" ? helpers.formatarPercentual : (valor) => String(valor ?? "");
        const lerNumeroPersistido = typeof helpers.lerNumeroPersistido === "function" ? helpers.lerNumeroPersistido : () => null;
        const perfAsync = typeof helpers.perfAsync === "function" ? helpers.perfAsync : async (_nome, callback) => callback();
        const perfSnapshot = typeof helpers.perfSnapshot === "function" ? helpers.perfSnapshot : () => null;
        const perfSync = typeof helpers.perfSync === "function" ? helpers.perfSync : (_nome, callback) => callback();
        const persistirSelecao = typeof helpers.persistirSelecao === "function" ? helpers.persistirSelecao : () => null;
        const prioridadeEmpresa = typeof helpers.prioridadeEmpresa === "function" ? helpers.prioridadeEmpresa : () => ({ tone: "aprovado", badge: "", acao: "" });
        const renderAdmin = typeof helpers.renderAdmin === "function" ? helpers.renderAdmin : () => null;
        const renderAvisosOperacionais = typeof helpers.renderAvisosOperacionais === "function" ? helpers.renderAvisosOperacionais : () => null;
        const renderChatCapacidade = typeof helpers.renderChatCapacidade === "function" ? helpers.renderChatCapacidade : () => null;
        const renderChatContext = typeof helpers.renderChatContext === "function" ? helpers.renderChatContext : () => null;
        const renderChatList = typeof helpers.renderChatList === "function" ? helpers.renderChatList : () => null;
        const renderChatMensagens = typeof helpers.renderChatMensagens === "function" ? helpers.renderChatMensagens : () => null;
        const renderChatMovimentos = typeof helpers.renderChatMovimentos === "function" ? helpers.renderChatMovimentos : () => null;
        const renderChatResumo = typeof helpers.renderChatResumo === "function" ? helpers.renderChatResumo : () => null;
        const renderChatTriagem = typeof helpers.renderChatTriagem === "function" ? helpers.renderChatTriagem : () => null;
        const renderMesaContext = typeof helpers.renderMesaContext === "function" ? helpers.renderMesaContext : () => null;
        const renderMesaList = typeof helpers.renderMesaList === "function" ? helpers.renderMesaList : () => null;
        const renderMesaMensagens = typeof helpers.renderMesaMensagens === "function" ? helpers.renderMesaMensagens : () => null;
        const renderMesaMovimentos = typeof helpers.renderMesaMovimentos === "function" ? helpers.renderMesaMovimentos : () => null;
        const renderMesaResumo = typeof helpers.renderMesaResumo === "function" ? helpers.renderMesaResumo : () => null;
        const renderMesaResumoGeral = typeof helpers.renderMesaResumoGeral === "function" ? helpers.renderMesaResumoGeral : () => null;
        const renderMesaTriagem = typeof helpers.renderMesaTriagem === "function" ? helpers.renderMesaTriagem : () => null;
        const resumoCanalOperacional = typeof helpers.resumoCanalOperacional === "function" ? helpers.resumoCanalOperacional : (canal) => String(canal ?? "");
        const texto = typeof helpers.texto === "function" ? helpers.texto : (valor) => (valor == null ? "" : String(valor));

        const cancelarCarregamentoMesa = typeof actions.cancelarCarregamentoMesa === "function" ? actions.cancelarCarregamentoMesa : () => null;
        const limparDocumentoChatPendente = typeof actions.limparDocumentoChatPendente === "function" ? actions.limparDocumentoChatPendente : () => null;
        const loadChat = typeof actions.loadChat === "function" ? actions.loadChat : async () => null;
        const loadMesa = typeof actions.loadMesa === "function" ? actions.loadMesa : async () => null;

        const storageChatKey = storageKeys.chat || "tariel.cliente.chat.laudo";
        const storageMesaKey = storageKeys.mesa || "tariel.cliente.mesa.laudo";

        function normalizarSurface(surface) {
            return surface === "chat" || surface === "mesa" ? surface : "admin";
        }

        function surfaceJaCarregada(surface) {
            return Boolean(state.surface?.loaded?.[normalizarSurface(surface)]);
        }

        function marcarSurfaceCarregada(surface) {
            if (!state.surface?.loaded) return;
            state.surface.loaded[normalizarSurface(surface)] = true;
        }

        function mergeBootstrapPayload(payload) {
            const atual = state.bootstrap || {};
            const proximo = { ...atual };

            if (payload?.portal) proximo.portal = payload.portal;
            if (payload?.empresa) proximo.empresa = payload.empresa;
            if (payload?.tenant_admin_projection) {
                proximo.tenant_admin_projection = payload.tenant_admin_projection;
            }
            if (Object.prototype.hasOwnProperty.call(payload || {}, "usuarios")) {
                proximo.usuarios = Array.isArray(payload?.usuarios) ? payload.usuarios : [];
            }
            if (Object.prototype.hasOwnProperty.call(payload || {}, "auditoria")) {
                proximo.auditoria = payload?.auditoria || { itens: [] };
            }
            if (payload?.chat) {
                proximo.chat = {
                    ...(atual.chat || {}),
                    ...payload.chat,
                };
            }
            if (payload?.mesa) {
                proximo.mesa = {
                    ...(atual.mesa || {}),
                    ...payload.mesa,
                };
            }

            state.bootstrap = proximo;
        }

        function atualizarBadgesTabs() {
            const bootstrap = state.bootstrap;
            if (!bootstrap) return;
            const tenantAdmin = bootstrap.tenant_admin_projection?.payload || null;

            const totalUsuarios = Number(tenantAdmin?.user_summary?.total_users || bootstrap.usuarios?.length || 0);
            const totalLaudosChat = Number(tenantAdmin?.case_counts?.total_cases || bootstrap.chat?.laudos?.length || 0);
            const totalMesaQuente = Number(
                (tenantAdmin?.review_counts?.pending_review || 0)
                + (tenantAdmin?.review_counts?.in_review || 0)
            ) || (bootstrap.mesa?.laudos || []).filter(
                (item) => Number(item.pendencias_abertas || 0) > 0 || Number(item.whispers_nao_lidos || 0) > 0
            ).length;

            $("tab-admin-count").textContent = formatarInteiro(totalUsuarios);
            $("tab-chat-count").textContent = formatarInteiro(totalLaudosChat);
            $("tab-mesa-count").textContent = formatarInteiro(totalMesaQuente || bootstrap.mesa?.laudos?.length || 0);
        }

        function sincronizarSelecoes() {
            if (surfaceJaCarregada("chat")) {
                const idsChat = new Set((state.bootstrap?.chat?.laudos || []).map((item) => Number(item.id)));
                if (!idsChat.has(Number(state.chat.laudoId))) {
                    state.chat.laudoId = lerNumeroPersistido(storageChatKey);
                }
                if (!idsChat.has(Number(state.chat.laudoId))) {
                    state.chat.laudoId = (state.bootstrap?.chat?.laudos || [])[0]?.id || null;
                }
                persistirSelecao(storageChatKey, state.chat.laudoId);
                if (!state.chat.laudoId) {
                    state.chat.loadedLaudoId = null;
                    state.chat.mensagens = [];
                    limparDocumentoChatPendente();
                }
            }

            if (surfaceJaCarregada("mesa")) {
                const idsMesa = new Set((state.bootstrap?.mesa?.laudos || []).map((item) => Number(item.id)));
                if (!idsMesa.has(Number(state.mesa.laudoId))) {
                    state.mesa.laudoId = lerNumeroPersistido(storageMesaKey);
                }
                if (!idsMesa.has(Number(state.mesa.laudoId))) {
                    state.mesa.laudoId = (state.bootstrap?.mesa?.laudos || [])[0]?.id || null;
                }
                persistirSelecao(storageMesaKey, state.mesa.laudoId);
                if (!state.mesa.laudoId) {
                    state.mesa.loadedLaudoId = null;
                    cancelarCarregamentoMesa();
                    state.mesa.mensagens = [];
                    state.mesa.pacote = null;
                }
            }
        }

        function renderCentralPrioridades() {
            const container = $("hero-prioridades");
            if (!container) return;

            const prioridades = construirPrioridadesPortal();
            container.innerHTML = prioridades.map((item, indice) => `
                <article class="priority-item" data-tone="${escapeAttr(item.tone || "aberto")}">
                    <div class="priority-head">
                        <span class="pill" data-kind="priority" data-status="${escapeAttr(item.tone || "aberto")}">P${indice + 1}</span>
                        <span class="hero-chip">${escapeHtml(resumoCanalOperacional(item.canal))}</span>
                    </div>
                    <div class="priority-copy">
                        <strong>${escapeHtml(item.titulo || "Prioridade")}</strong>
                        <p>${escapeHtml(item.detalhe || "")}</p>
                    </div>
                    <button
                        class="btn"
                        type="button"
                        data-act="abrir-prioridade"
                        data-kind="${escapeAttr(item.kind || "admin-section")}"
                        data-canal="${escapeAttr(item.canal || "admin")}"
                        data-laudo="${item.laudoId ? escapeAttr(String(item.laudoId)) : ""}"
                        data-target="${escapeAttr(item.targetId || "")}"
                        data-origem="${escapeAttr(item.origem || item.canal || "admin")}"
                        data-user="${item.userId ? escapeAttr(String(item.userId)) : ""}"
                        data-busca="${escapeAttr(item.busca || "")}"
                        data-papel="${escapeAttr(item.papel || "todos")}"
                    >${escapeHtml(item.acaoLabel || "Abrir")}</button>
                </article>
            `).join("");
        }

        function definirHeroCommand(prioridade) {
            const button = $("hero-command-action");
            const title = $("hero-command-title");
            const meta = $("hero-command-meta");
            if (!button || !title || !meta) return;

            if (!prioridade) {
                button.textContent = "Abrir foco da empresa";
                button.dataset.kind = "admin-section";
                button.dataset.canal = "admin";
                button.dataset.target = "admin-resumo-geral";
                button.dataset.origem = "admin";
                button.dataset.laudo = "";
                button.dataset.user = "";
                button.dataset.busca = "";
                button.dataset.papel = "";
                title.textContent = "Abrir frente prioritaria da empresa";
                meta.textContent = "O portal segue pronto para aprofundar capacidade, equipe, suporte ou historico operacional a partir do console administrativo.";
                return;
            }

            button.textContent = prioridade.acaoLabel || "Abrir prioridade";
            button.dataset.kind = prioridade.kind || "admin-section";
            button.dataset.canal = prioridade.canal || "admin";
            button.dataset.target = prioridade.targetId || "";
            button.dataset.origem = prioridade.origem || prioridade.canal || "admin";
            button.dataset.laudo = prioridade.laudoId ? String(prioridade.laudoId) : "";
            button.dataset.user = prioridade.userId ? String(prioridade.userId) : "";
            button.dataset.busca = prioridade.busca || "";
            button.dataset.papel = prioridade.papel || "";
            title.textContent = prioridade.titulo || "Abrir prioridade";
            meta.textContent = prioridade.detalhe || "Abra a frente operacional mais sensivel sem trocar de contexto.";
        }

        function renderHeroExecutive() {
            const empresa = state.bootstrap?.empresa;
            const tenantAdmin = state.bootstrap?.tenant_admin_projection?.payload || null;
            if (!empresa) return;

            const visibilityPolicy = tenantAdmin?.visibility_policy || {};
            const mobileSingleOperator = Boolean(visibilityPolicy?.shared_mobile_operator_enabled)
                && texto(visibilityPolicy?.commercial_operating_model).trim() === "mobile_single_operator";
            const operationalUsers = Array.isArray(state.bootstrap?.usuarios) ? state.bootstrap.usuarios.length : 0;
            const operationalLimitRaw = Number(visibilityPolicy?.contract_operational_user_limit);
            const operationalLimit = Number.isFinite(operationalLimitRaw) && operationalLimitRaw > 0
                ? operationalLimitRaw
                : null;
            const operationalSurfaceLabels = Array.isArray(visibilityPolicy?.shared_mobile_operator_surface_set)
                ? visibilityPolicy.shared_mobile_operator_surface_set.map((item) => {
                    if (item === "mobile") return "App mobile";
                    if (item === "inspetor_web") return "Portal Inspetor";
                    if (item === "mesa_web") return "Portal Mesa";
                    return texto(item).replaceAll("_", " ");
                }).filter(Boolean)
                : [];
            const operationalSurfaceSummary = operationalSurfaceLabels.length
                ? operationalSurfaceLabels.join(", ")
                : "App mobile";
            const prioridades = construirPrioridadesPortal();
            const prioridadeTop = prioridades[0] || null;
            const prioridadeResumo = prioridadeEmpresa(empresa, state.bootstrap?.usuarios || []);
            const totalUsuarios = Number(tenantAdmin?.user_summary?.total_users || state.bootstrap?.usuarios?.length || 0);
            const usuariosAtivos = Number(tenantAdmin?.user_summary?.active_users || 0);
            const casosAbertos = Number(tenantAdmin?.case_counts?.open_cases || 0);
            const revisoesAtivas = Number(tenantAdmin?.review_counts?.pending_review || 0)
                + Number(tenantAdmin?.review_counts?.in_review || 0);
            const totalAuditoria = Number(state.bootstrap?.auditoria?.itens?.length || 0);
            const usoPercentual = empresa.uso_percentual == null ? "Sem teto" : formatarPercentual(empresa.uso_percentual);
            const suggestedPlan = texto(empresa.plano_sugerido).trim();

            const focusTitle = $("hero-focus-title");
            const focusMeta = $("hero-focus-meta");
            const kpiStrip = $("hero-executive-kpis");
            const planHealth = $("hero-plan-health");
            if (focusTitle) {
                focusTitle.textContent = prioridadeTop?.titulo || prioridadeResumo.badge || "Leitura executiva pronta";
            }
            if (focusMeta) {
                focusMeta.textContent = prioridadeTop?.detalhe
                    || prioridadeResumo.acao
                    || "Capacidade, equipe, suporte e operacao seguem alinhados em uma shell unica.";
            }
            if (kpiStrip) {
                kpiStrip.innerHTML = `
                    <article class="hero-kpi-card">
                        <small>Plano em vigor</small>
                        <strong>${escapeHtml(empresa.plano_ativo || "Nao informado")}</strong>
                        <span>${escapeHtml(usoPercentual)} de uso acompanhado na empresa.</span>
                    </article>
                    <article class="hero-kpi-card">
                        <small>Equipe ativa</small>
                        <strong>${escapeHtml(formatarInteiro(usuariosAtivos || totalUsuarios))}</strong>
                        <span>${escapeHtml(
                            mobileSingleOperator
                                ? `${formatarInteiro(operationalUsers)} de ${formatarInteiro(operationalLimit || 1)} conta operacional ocupada.`
                                : `${formatarInteiro(totalUsuarios)} perfis operacionais sob a mesma governanca.`
                        )}</span>
                    </article>
                    <article class="hero-kpi-card">
                        <small>Casos abertos</small>
                        <strong>${escapeHtml(formatarInteiro(casosAbertos))}</strong>
                        <span>${escapeHtml(formatarInteiro(revisoesAtivas))} casos em revisao ou resposta.</span>
                    </article>
                    <article class="hero-kpi-card">
                        <small>Trilha auditavel</small>
                        <strong>${escapeHtml(formatarInteiro(totalAuditoria))}</strong>
                        <span>${suggestedPlan ? `Plano sugerido: ${escapeHtml(suggestedPlan)}.` : "Suporte, equipe e comercial sob historico operacional."}</span>
                    </article>
                `;
            }
            if (planHealth) {
                planHealth.innerHTML = `
                    <div class="hero-status">
                        <small>Uso do contrato</small>
                        <strong>${escapeHtml(usoPercentual)}</strong>
                        <span>${empresa.laudos_restantes == null ? "Sem teto mensal configurado." : `${escapeHtml(formatarInteiro(empresa.laudos_restantes))} laudos ainda livres nesta janela.`}</span>
                    </div>
                    <div class="hero-status">
                        <small>Margem de equipe</small>
                        <strong>${mobileSingleOperator
                            ? escapeHtml(`${formatarInteiro(operationalUsers)}/${formatarInteiro(operationalLimit || 1)}`)
                            : empresa.usuarios_restantes == null
                                ? "Livre"
                                : escapeHtml(formatarInteiro(empresa.usuarios_restantes))}</strong>
                        <span>${escapeHtml(
                            mobileSingleOperator
                                ? "Admin-Cliente nao entra nessa conta operacional."
                                : `${formatarInteiro(totalUsuarios)} perfis em operacao hoje.`
                        )}</span>
                    </div>
                    <div class="hero-status">
                        <small>Modelo operacional</small>
                        <strong>${escapeHtml(mobileSingleOperator ? "Operador unico" : "Operacao padrao")}</strong>
                        <span>${escapeHtml(
                            mobileSingleOperator
                                ? `Continuidade prevista em ${operationalSurfaceSummary}.`
                                : "Perfis distribuidos conforme o contrato da empresa."
                        )}</span>
                    </div>
                    <div class="hero-status">
                        <small>Politica de suporte</small>
                        <strong>${visibilityPolicy?.exceptional_support_access === "disabled" ? "Fechada" : "Governada"}</strong>
                        <span>Diagnostico administrativo e trilha recente a um clique.</span>
                    </div>
                `;
            }
            definirHeroCommand(prioridadeTop);
        }

        function renderAdminSurface() {
            if (!surfaceJaCarregada("admin")) return;
            renderAdmin();
            abrirSecaoAdmin(state.ui?.adminSection || state.ui?.sections?.admin || "overview", { ensureRendered: false, syncUrl: false });
        }

        function renderChatSurface() {
            if (!surfaceJaCarregada("chat")) return;
            renderChatResumo();
            renderChatTriagem();
            renderChatMovimentos();
            renderChatCapacidade();
            renderAvisosOperacionais("chat", "chat-alertas-operacionais");
            renderChatList();
            renderChatContext();
            renderChatMensagens();
            abrirSecaoChat(state.ui?.chatSection || state.ui?.sections?.chat || "overview", { syncUrl: false });
        }

        function renderMesaSurface() {
            if (!surfaceJaCarregada("mesa")) return;
            renderMesaResumoGeral();
            renderMesaTriagem();
            renderMesaMovimentos();
            renderAvisosOperacionais("mesa", "mesa-alertas-operacionais");
            renderMesaList();
            renderMesaContext();
            renderMesaResumo();
            renderMesaMensagens();
            abrirSecaoMesa(state.ui?.mesaSection || state.ui?.sections?.mesa || "overview", { syncUrl: false });
        }

        function renderSurface(surface) {
            const surfaceAtiva = normalizarSurface(surface);
            if (surfaceAtiva === "admin") {
                renderAdminSurface();
                return;
            }
            if (surfaceAtiva === "chat") {
                renderChatSurface();
                return;
            }
            renderMesaSurface();
        }

        function renderEverything({ surface = state.ui?.tab } = {}) {
            perfSync("cliente.renderEverything", () => {
                if (!state.bootstrap) return;
                atualizarBadgesTabs();
                renderCentralPrioridades();
                renderHeroExecutive();
                renderSurface(surface);
                perfSnapshot(`cliente:render:${normalizarSurface(surface)}`);
            }, { surface: normalizarSurface(surface), tab: state.ui.tab }, "render");
        }

        async function bootstrapPortal({ surface = state.ui?.tab, carregarDetalhes = false, force = true } = {}) {
            return perfAsync(
                "cliente.bootstrapPortal",
                async () => {
                    const surfaceAtiva = normalizarSurface(surface);
                    if (force || !state.bootstrap || !surfaceJaCarregada(surfaceAtiva)) {
                        const payload = await api(`/cliente/api/bootstrap?surface=${encodeURIComponent(surfaceAtiva)}`);
                        mergeBootstrapPayload(payload);
                        marcarSurfaceCarregada(surfaceAtiva);
                    }

                    sincronizarSelecoes();
                    renderEverything({ surface: state.ui?.tab || surfaceAtiva });

                    if (!carregarDetalhes) return;
                    if (normalizarSurface(state.ui?.tab) !== surfaceAtiva) return;

                    if (surfaceAtiva === "chat" && state.chat.laudoId) {
                        await loadChat(state.chat.laudoId, { silencioso: true });
                    }
                    if (surfaceAtiva === "mesa" && state.mesa.laudoId) {
                        await loadMesa(state.mesa.laudoId, { silencioso: true });
                    }
                    perfSnapshot("cliente:bootstrapPortal");
                },
                { carregarDetalhes, force, surface: normalizarSurface(surface) },
                "boot"
            );
        }

        return {
            atualizarBadgesTabs,
            bootstrapPortal,
            renderHeroExecutive,
            renderCentralPrioridades,
            renderEverything,
            sincronizarSelecoes,
        };
    };
})();
