(function () {
    "use strict";

    if (window.TarielClientePortalAdminSurface) return;

    window.TarielClientePortalAdminSurface = function createTarielClientePortalAdminSurface(config = {}) {
        const state = config.state || {};
        const documentRef = config.documentRef || document;
        const windowRef = config.windowRef || window;
        const $ = typeof config.getById === "function"
            ? config.getById
            : (id) => documentRef.getElementById(id);
        const helpers = config.helpers || {};
        const filters = config.filters || {};
        const labels = config.labels || {};

        const escapeAttr = typeof helpers.escapeAttr === "function" ? helpers.escapeAttr : (valor) => String(valor ?? "");
        const escapeHtml = typeof helpers.escapeHtml === "function" ? helpers.escapeHtml : (valor) => String(valor ?? "");
        const formatarCapacidadeRestante = typeof helpers.formatarCapacidadeRestante === "function" ? helpers.formatarCapacidadeRestante : () => "";
        const formatarInteiro = typeof helpers.formatarInteiro === "function" ? helpers.formatarInteiro : (valor) => String(Number(valor || 0));
        const formatarLimitePlano = typeof helpers.formatarLimitePlano === "function" ? helpers.formatarLimitePlano : () => "";
        const formatarPercentual = typeof helpers.formatarPercentual === "function" ? helpers.formatarPercentual : () => "";
        const formatarVariacao = typeof helpers.formatarVariacao === "function" ? helpers.formatarVariacao : () => "";
        const htmlBarrasHistorico = typeof helpers.htmlBarrasHistorico === "function" ? helpers.htmlBarrasHistorico : () => "";
        const obterNomePapel = typeof helpers.obterNomePapel === "function" ? helpers.obterNomePapel : (valor) => String(valor ?? "");
        const obterPlanoCatalogo = typeof helpers.obterPlanoCatalogo === "function" ? helpers.obterPlanoCatalogo : () => null;
        const ordenarPorPrioridade = typeof helpers.ordenarPorPrioridade === "function" ? helpers.ordenarPorPrioridade : (lista) => [...(lista || [])];
        const parseDataIso = typeof helpers.parseDataIso === "function" ? helpers.parseDataIso : () => 0;
        const prioridadeEmpresa = typeof helpers.prioridadeEmpresa === "function" ? helpers.prioridadeEmpresa : () => ({ tone: "aprovado", badge: "", acao: "" });
        const prioridadeUsuario = typeof helpers.prioridadeUsuario === "function" ? helpers.prioridadeUsuario : () => ({ tone: "aprovado", badge: "", acao: "", score: 0 });
        const roleBadge = typeof helpers.roleBadge === "function" ? helpers.roleBadge : () => "";
        const slugPapel = typeof helpers.slugPapel === "function" ? helpers.slugPapel : () => "inspetor";
        const texto = typeof helpers.texto === "function" ? helpers.texto : (valor) => (valor == null ? "" : String(valor));
        const tomCapacidadeEmpresa = typeof helpers.tomCapacidadeEmpresa === "function" ? helpers.tomCapacidadeEmpresa : () => "aprovado";
        const userStatusBadges = typeof helpers.userStatusBadges === "function" ? helpers.userStatusBadges : () => "";
        const sincronizarUrlDaSecao = typeof helpers.sincronizarUrlDaSecao === "function" ? helpers.sincronizarUrlDaSecao : () => null;

        const filtrarUsuarios = typeof filters.filtrarUsuarios === "function" ? filters.filtrarUsuarios : () => [];
        const rotuloSituacaoUsuarios = typeof labels.rotuloSituacaoUsuarios === "function" ? labels.rotuloSituacaoUsuarios : () => "";

        const STAGE_IDS = Object.freeze({
            overview: "admin-overview",
            capacity: "admin-capacity",
            team: "admin-team",
            support: "admin-support",
        });
        const STAGE_ORDER = Object.freeze(["overview", "capacity", "team", "support"]);
        const SECTION_META = Object.freeze({
            overview: Object.freeze({
                title: "Resumo",
                meta: "Panorama, saude e proximo foco da empresa.",
            }),
            capacity: Object.freeze({
                title: "Plano e capacidade",
                meta: "Limites, folga e historico comercial da empresa.",
            }),
            team: Object.freeze({
                title: "Equipe",
                meta: "Criacao, ativacao e manutencao dos acessos da empresa.",
            }),
            support: Object.freeze({
                title: "Suporte",
                meta: "Diagnostico, protocolo e trilha recente da empresa.",
            }),
        });
        const AUDIT_FILTERS = Object.freeze([
            Object.freeze({ key: "all", label: "Tudo", description: "Historico completo da empresa" }),
            Object.freeze({ key: "admin", label: "Painel", description: "Plano, equipe e acesso" }),
            Object.freeze({ key: "support", label: "Suporte", description: "Protocolos e diagnostico" }),
            Object.freeze({ key: "chat", label: "Chat", description: "Movimentos operacionais do chat" }),
            Object.freeze({ key: "mesa", label: "Mesa", description: "Pendencias e respostas da mesa" }),
            Object.freeze({ key: "team", label: "Equipe", description: "Criacao e manutencao de usuarios" }),
        ]);
        const TARGET_TO_SECTION = Object.freeze({
            "admin-overview": "overview",
            "admin-resumo-geral": "overview",
            "admin-executive-brief": "overview",
            "empresa-cards": "overview",
            "admin-saude-resumo": "overview",
            "admin-saude-historico": "overview",
            "admin-capacity": "capacity",
            "admin-capacity-brief": "capacity",
            "admin-planos": "capacity",
            "admin-planos-box": "capacity",
            "empresa-resumo-detalhado": "capacity",
            "empresa-alerta-capacidade": "capacity",
            "plano-impacto-preview": "capacity",
            "admin-planos-historico": "capacity",
            "form-plano": "capacity",
            "empresa-plano": "capacity",
            "btn-plano-registrar": "capacity",
            "admin-team": "team",
            "admin-team-brief": "team",
            "admin-equipe": "team",
            "admin-equipe-criacao": "team",
            "admin-equipe-onboarding": "team",
            "form-usuario": "team",
            "usuario-capacidade-nota": "team",
            "btn-usuario-criar": "team",
            "admin-onboarding-resumo": "team",
            "admin-onboarding-lista": "team",
            "admin-equipe-lista": "team",
            "usuarios-busca": "team",
            "usuarios-filtro-papel": "team",
            "usuarios-resumo": "team",
            "lista-usuarios": "team",
            "usuarios-vazio": "team",
            "admin-support": "support",
            "admin-support-brief": "support",
            "admin-governanca": "support",
            "admin-suporte": "support",
            "admin-support-policy": "support",
            "admin-support-protocol": "support",
            "admin-diagnostico-resumo": "support",
            "btn-exportar-diagnostico": "support",
            "btn-whatsapp-suporte": "support",
            "form-suporte-cliente": "support",
            "admin-auditoria": "support",
            "admin-auditoria-filtros": "support",
            "admin-auditoria-busca": "support",
            "admin-audit-overview": "support",
            "admin-auditoria-lista": "support",
        });
        const queuedStages = new Map();

        function normalizarSecaoAdmin(valor) {
            const secao = texto(valor).trim().toLowerCase();
            if (secao === "planos") return "capacity";
            if (secao === "equipe") return "team";
            if (secao === "governanca") return "support";
            return STAGE_ORDER.includes(secao) ? secao : "overview";
        }

        function resolverSecaoAdminPorTarget(targetId) {
            const alvo = texto(targetId).trim().replace(/^#/, "");
            if (!alvo) return null;
            if (TARGET_TO_SECTION[alvo]) return TARGET_TO_SECTION[alvo];
            return STAGE_ORDER.includes(alvo) ? alvo : null;
        }

        function obterBotoesSecaoAdmin() {
            return Array.from(documentRef.querySelectorAll("[data-admin-section-tab]"));
        }

        function obterPaineisSecaoAdmin() {
            return Array.from(documentRef.querySelectorAll("[data-admin-panel]"));
        }

        function obterTenantAdminPayload() {
            return state.bootstrap?.tenant_admin_projection?.payload || null;
        }

        function formatarRotuloLista(lista, { fallback = "nao definido" } = {}) {
            const itens = Array.isArray(lista)
                ? lista
                    .map((item) => texto(item).trim())
                    .filter(Boolean)
                : [];
            if (!itens.length) return fallback;
            if (itens.length === 1) return itens[0];
            if (itens.length === 2) return `${itens[0]} e ${itens[1]}`;
            return `${itens.slice(0, -1).join(", ")} e ${itens[itens.length - 1]}`;
        }

        function obterGovernancaOperacionalTenant() {
            const tenantAdmin = obterTenantAdminPayload();
            const policy = tenantAdmin?.visibility_policy || {};
            const usuariosOperacionais = Array.isArray(state.bootstrap?.usuarios) ? state.bootstrap.usuarios : [];
            const enabled = Boolean(policy?.shared_mobile_operator_enabled)
                && texto(policy?.commercial_operating_model).trim() === "mobile_single_operator";
            const limitValue = Number(policy?.contract_operational_user_limit);
            const operationalUserLimit = Number.isFinite(limitValue) && limitValue > 0 ? limitValue : null;
            const slotsInUseValue = Number(policy?.operational_identity_slots_in_use);
            const operationalUsersInUse = Number.isFinite(slotsInUseValue) && slotsInUseValue >= 0
                ? slotsInUseValue
                : usuariosOperacionais.length;
            const operationalUsersRemaining = operationalUserLimit == null
                ? null
                : Math.max(operationalUserLimit - operationalUsersInUse, 0);
            const operationalUsersExcess = operationalUserLimit == null
                ? 0
                : Math.max(operationalUsersInUse - operationalUserLimit, 0);
            const surfaceSet = Array.isArray(policy?.shared_mobile_operator_surface_set)
                ? policy.shared_mobile_operator_surface_set.map((item) => texto(item).trim()).filter(Boolean)
                : [];
            const surfaceLabels = surfaceSet.map((item) => {
                if (item === "mobile") return "App mobile";
                if (item === "inspetor_web") return "Portal de campo";
                if (item === "mesa_web") return "Portal de revisao";
                return item.replaceAll("_", " ");
            });
            const assignablePortalSet = Array.isArray(policy?.tenant_assignable_portal_set)
                ? policy.tenant_assignable_portal_set.map((item) => texto(item).trim()).filter(Boolean)
                : ["inspetor", "revisor"];
            return {
                enabled,
                operatingModel: texto(policy?.commercial_operating_model).trim() || "standard",
                operatingModelLabel: enabled ? "Mobile principal com operador único" : "Operação padrão",
                operationalUserLimit,
                operationalUsersInUse,
                operationalUsersRemaining,
                operationalUsersExcess,
                operationalUsersAtLimit: operationalUserLimit != null && operationalUsersInUse >= operationalUserLimit,
                sharedMobileOperatorWebInspectorEnabled: Boolean(policy?.shared_mobile_operator_web_inspector_enabled),
                sharedMobileOperatorWebReviewEnabled: Boolean(policy?.shared_mobile_operator_web_review_enabled),
                operationalUserCrossPortalEnabled: Boolean(policy?.operational_user_cross_portal_enabled),
                operationalUserAdminPortalEnabled: Boolean(policy?.operational_user_admin_portal_enabled),
                assignablePortalSet,
                surfaceSet,
                surfaceLabels,
                surfacesSummary: formatarRotuloLista(surfaceLabels, { fallback: "App mobile" }),
                identityNote: enabled
                    ? "A conta principal pode concentrar o portal da empresa, o campo, a revisao e o mobile conforme as liberacoes contratadas."
                    : "Cada pessoa segue a combinacao de acessos liberada para esta empresa.",
            };
        }

        function marcarEstadoStage(stage, status) {
            const node = $(STAGE_IDS[stage]);
            if (!node) return;
            node.dataset.stageState = status;
        }

        function limparStageAgendado(stage) {
            const registro = queuedStages.get(stage);
            if (!registro) return;
            if (Number.isFinite(registro.timeoutId)) {
                windowRef.clearTimeout(registro.timeoutId);
            }
            if (typeof registro.cancelIdle === "function") {
                registro.cancelIdle();
            }
            queuedStages.delete(stage);
        }

        function definirTextoNoElemento(id, valor) {
            const node = $(id);
            if (!node) return;
            node.textContent = texto(valor);
        }

        function preencherHtmlNoElemento(id, html) {
            const node = $(id);
            if (!node) return;
            node.innerHTML = html;
        }

        function normalizarFiltroAuditoriaAdmin(valor) {
            const filtro = texto(valor).trim().toLowerCase();
            if (!filtro || filtro === "all" || filtro === "todos") return "all";
            return AUDIT_FILTERS.some((item) => item.key === filtro) ? filtro : "all";
        }

        function obterAuditoriaAdmin() {
            return Array.isArray(state.bootstrap?.auditoria?.itens) ? state.bootstrap.auditoria.itens : [];
        }

        function obterSpotlightSecaoAdmin(secaoAtiva) {
            const empresa = state.bootstrap?.empresa || {};
            const tenantAdmin = obterTenantAdminPayload();
            const auditoriaResumo = state.bootstrap?.auditoria?.resumo || {};
            const categorias = auditoriaResumo.categories || {};
            const totalUsuarios = Number(tenantAdmin?.user_summary?.total_users || empresa.usuarios_em_uso || empresa.total_usuarios || 0);
            const revisoesAtivas = Number(tenantAdmin?.review_counts?.pending_review || 0)
                + Number(tenantAdmin?.review_counts?.in_review || 0);
            const itens = {
                overview: {
                    title: "Pulso executivo da empresa",
                    meta: "Visao resumida de folga, operacao e proximo foco administrativo antes de entrar nas camadas mais detalhadas.",
                    chips: [
                        `${formatarInteiro(Number(tenantAdmin?.case_counts?.open_cases || 0))} casos abertos`,
                        `${formatarInteiro(totalUsuarios)} perfis monitorados`,
                        `${formatarInteiro(revisoesAtivas)} revisoes em curso`,
                    ],
                },
                capacity: {
                    title: "Capacidade comercial com leitura rapida",
                    meta: "Limites, folga, historico e sugestao comercial aparecem juntos, sem misturar essa decisao com a rotina operacional.",
                    chips: [
                        empresa.laudos_restantes == null ? "Laudos sem teto" : `${formatarInteiro(empresa.laudos_restantes)} laudos livres`,
                        empresa.usuarios_restantes == null ? "Usuarios sem teto" : `${formatarInteiro(empresa.usuarios_restantes)} vagas livres`,
                        texto(empresa.plano_sugerido).trim() ? `Plano sugerido ${texto(empresa.plano_sugerido).trim()}` : "Sem upgrade sugerido",
                    ],
                },
                team: {
                    title: "Equipe com ativacao e manutencao no mesmo mapa",
                    meta: "Criacao, primeiros acessos e bloqueios ficam legiveis sem transformar a tela em uma parede de cadastros.",
                    chips: [
                        `${formatarInteiro(totalUsuarios)} acessos da empresa`,
                        `${formatarInteiro((state.bootstrap?.usuarios || []).filter((item) => item?.senha_temporaria_ativa).length)} primeiros acessos`,
                        `${formatarInteiro((state.bootstrap?.usuarios || []).filter((item) => !item?.ativo).length)} bloqueados`,
                    ],
                },
                support: {
                    title: "Suporte governado e historico consultavel",
                    meta: "Diagnostico, politica de suporte e auditoria fina ficam no mesmo contexto para acelerar leitura e exportacao.",
                    chips: [
                        `${formatarInteiro(Number(categorias.support || 0))} eventos de suporte`,
                        `${formatarInteiro(Number(categorias.chat || 0) + Number(categorias.mesa || 0))} eventos operacionais`,
                        `${formatarInteiro(obterAuditoriaAdmin().length)} itens no historico`,
                    ],
                },
            };
            return itens[secaoAtiva] || itens.overview;
        }

        function obterResumoAuditoriaFiltrada(itens) {
            const categories = {
                support: 0,
                access: 0,
                commercial: 0,
                team: 0,
                chat: 0,
                mesa: 0,
            };
            const scopes = {
                admin: 0,
                chat: 0,
                mesa: 0,
            };
            itens.forEach((item) => {
                const categoria = texto(item?.categoria).trim().toLowerCase() || "support";
                const scope = texto(item?.scope).trim().toLowerCase() || "admin";
                if (Object.prototype.hasOwnProperty.call(categories, categoria)) {
                    categories[categoria] += 1;
                }
                if (Object.prototype.hasOwnProperty.call(scopes, scope)) {
                    scopes[scope] += 1;
                }
            });
            return { categories, scopes, total: itens.length };
        }

        function agruparAuditoriaPorDia(itens) {
            const grupos = new Map();
            itens.forEach((item) => {
                const iso = texto(item?.criado_em).trim();
                const label = iso ? iso.slice(0, 10) : texto(item?.criado_em_label).trim().slice(0, 10);
                const chave = label || "sem-data";
                if (!grupos.has(chave)) {
                    grupos.set(chave, []);
                }
                grupos.get(chave).push(item);
            });
            return Array.from(grupos.entries()).map(([dateKey, rows]) => ({ dateKey, rows }));
        }

        function obterAuditoriaFiltrada() {
            const filtro = normalizarFiltroAuditoriaAdmin(state.ui?.adminAuditFilter);
            const busca = texto(state.ui?.adminAuditSearch).trim().toLowerCase();
            let itens = obterAuditoriaAdmin();

            if (filtro !== "all") {
                itens = itens.filter((item) => {
                    const categoria = texto(item?.categoria).trim().toLowerCase();
                    const scope = texto(item?.scope).trim().toLowerCase();
                    if (filtro === "support") return categoria === "support";
                    if (filtro === "team") return categoria === "team";
                    return scope === filtro;
                });
            }
            if (!busca) return itens;
            return itens.filter((item) => {
                const payload = item?.payload && typeof item.payload === "object"
                    ? Object.values(item.payload).join(" ")
                    : "";
                const corpus = [
                    item?.resumo,
                    item?.detalhe,
                    item?.acao,
                    item?.ator_nome,
                    item?.categoria_label,
                    item?.scope_label,
                    payload,
                ].join(" ").toLowerCase();
                return corpus.includes(busca);
            });
        }

        function atualizarResumoSecaoAdmin() {
            const secaoAtiva = normalizarSecaoAdmin(state.ui?.adminSection || state.ui?.sections?.admin || "overview");
            const definicao = SECTION_META[secaoAtiva] || SECTION_META.overview;
            const nav = documentRef.querySelector('[data-surface-nav="admin"]');
            const empresa = state.bootstrap?.empresa || {};
            const tenantAdmin = obterTenantAdminPayload();
            const auditoria = Array.isArray(state.bootstrap?.auditoria?.itens) ? state.bootstrap.auditoria.itens : [];
            const totalUsuarios = Number(tenantAdmin?.user_summary?.total_users || empresa.usuarios_em_uso || empresa.total_usuarios || 0);
            const laudosNoMes = Number(empresa.laudos_mes_atual || 0);
            const laudosRestantes = empresa.laudos_restantes == null
                ? "Contrato sem teto mensal"
                : `${formatarInteiro(Math.max(Number(empresa.laudos_restantes || 0), 0))} laudos restantes`;
            const contagens = {
                overview: `${formatarInteiro(laudosNoMes)} laudos no mes`,
                capacity: laudosRestantes,
                team: `${formatarInteiro(totalUsuarios)} perfis operacionais`,
                support: `${formatarInteiro(auditoria.length)} eventos recentes`,
            };

            if (nav) {
                nav.dataset.surfaceActiveSection = secaoAtiva;
            }
            definirTextoNoElemento("admin-section-summary-title", definicao.title);
            definirTextoNoElemento("admin-section-summary-meta", definicao.meta);
            const spotlight = obterSpotlightSecaoAdmin(secaoAtiva);
            definirTextoNoElemento("admin-stage-spotlight-title", spotlight.title);
            definirTextoNoElemento("admin-stage-spotlight-meta", spotlight.meta);
            preencherHtmlNoElemento(
                "admin-stage-spotlight-kpis",
                (spotlight.chips || [])
                    .filter(Boolean)
                    .map((chip) => `<span class="hero-chip">${escapeHtml(chip)}</span>`)
                    .join("")
            );
            definirTextoNoElemento("admin-section-count-overview", contagens.overview);
            definirTextoNoElemento("admin-section-count-capacity", contagens.capacity);
            definirTextoNoElemento("admin-section-count-team", contagens.team);
            definirTextoNoElemento("admin-section-count-support", contagens.support);
        }

        function abrirSecaoAdmin(secao, { focusTab = false, ensureRendered = true, syncUrl = true } = {}) {
            const secaoAtiva = normalizarSecaoAdmin(secao || state.ui?.adminSection);
            state.ui.adminSection = secaoAtiva;
            state.ui.sections = state.ui.sections || {};
            state.ui.sections.admin = secaoAtiva;

            const tabAtiva = obterBotoesSecaoAdmin().find((button) => button.dataset.adminSectionTab === secaoAtiva) || null;
            obterBotoesSecaoAdmin().forEach((button) => {
                const ativa = button.dataset.adminSectionTab === secaoAtiva;
                button.classList.toggle("is-active", ativa);
                button.setAttribute("aria-selected", ativa ? "true" : "false");
                button.setAttribute("aria-current", ativa ? "page" : "false");
                button.setAttribute("tabindex", ativa ? "0" : "-1");
            });
            obterPaineisSecaoAdmin().forEach((panel) => {
                panel.hidden = panel.dataset.adminPanel !== secaoAtiva;
            });
            atualizarResumoSecaoAdmin();

            if (ensureRendered && $(STAGE_IDS[secaoAtiva])?.dataset?.stageState !== "ready") {
                renderAdminStage(secaoAtiva, { force: true });
            }
            if (focusTab && tabAtiva) {
                tabAtiva.focus();
            }
            if (syncUrl && state.ui?.tab === "admin") {
                sincronizarUrlDaSecao("admin", secaoAtiva);
            }
            return secaoAtiva;
        }

        function renderEmpresaCards() {
            const empresa = state.bootstrap?.empresa;
            if (!empresa) return;
            const tenantAdmin = obterTenantAdminPayload();
            const governance = obterGovernancaOperacionalTenant();
            const prioridade = prioridadeEmpresa(empresa, state.bootstrap?.usuarios || []);
            const capacidadeTone = tomCapacidadeEmpresa(empresa);
            const usoValor = empresa.uso_percentual == null
                ? "Sem teto comercial neste contrato"
                : `${formatarInteiro(empresa.laudos_mes_atual || 0)} laudos no mes`;
            const resumoUsuarios = formatarCapacidadeRestante(empresa.usuarios_restantes, empresa.usuarios_excedente, "vaga", "vagas");
            const resumoLaudos = formatarCapacidadeRestante(empresa.laudos_restantes, empresa.laudos_excedente, "laudo", "laudos");
            const progresso = empresa.uso_percentual == null ? 18 : Math.max(6, Math.min(100, Number(empresa.uso_percentual || 0)));
            const riscoLabel = texto(empresa.capacidade_badge || "Capacidade estavel");
            const riscoMensagem = texto(empresa.capacidade_acao || "A empresa ainda tem folga operacional dentro do plano.");
            const planoSugerido = texto(empresa.plano_sugerido).trim();
            const alertaCapacidade = $("empresa-alerta-capacidade");
            const notaCapacidadeUsuario = $("usuario-capacidade-nota");
            const botaoCriarUsuario = $("btn-usuario-criar");
            const formUsuario = $("form-usuario");
            const pacoteOperacionalResumo = governance.enabled
                ? `${governance.operatingModelLabel}. ${formatarInteiro(governance.operationalUsersInUse)} de ${formatarInteiro(governance.operationalUserLimit)} conta operacional ocupada.`
                : "Perfis operacionais seguem a regra padrão contratada para esta empresa.";

            $("empresa-cards").innerHTML = `
                <article class="metric-card" data-accent="${empresa.status_bloqueio ? "attention" : "done"}">
                    <small>Plano em operacao</small>
                    <strong>${escapeHtml(empresa.plano_ativo)}</strong>
                    <span class="metric-meta">${empresa.status_bloqueio ? "Empresa bloqueada" : "Empresa liberada para operar"}</span>
                </article>
                <article class="metric-card" data-accent="${empresa.usuarios_restantes === 0 && empresa.usuarios_max != null ? "attention" : "live"}">
                    <small>Equipe em uso</small>
                    <strong>${formatarInteiro(tenantAdmin?.user_summary?.total_users || empresa.usuarios_em_uso || empresa.total_usuarios)}</strong>
                    <span class="metric-meta">${resumoUsuarios}. ${formatarInteiro(empresa.admins_cliente)} administradores da empresa, ${formatarInteiro(empresa.inspetores)} pessoas de campo e ${formatarInteiro(empresa.revisores)} pessoas de revisao.</span>
                </article>
                <article class="metric-card" data-accent="${empresa.laudos_restantes === 0 && empresa.laudos_mes_limite != null ? "attention" : "aberto"}">
                    <small>Laudos deste mes</small>
                    <strong>${formatarInteiro(empresa.laudos_mes_atual || 0)}</strong>
                    <span class="metric-meta">${resumoLaudos}. ${empresa.laudos_mes_limite == null ? "Contrato sem limite mensal fixo." : `Limite de ${formatarInteiro(empresa.laudos_mes_limite)} laudos.`}</span>
                </article>
                <article class="metric-card" data-accent="${capacidadeTone}">
                    <small>Folga comercial</small>
                    <strong>${formatarPercentual(empresa.uso_percentual)}</strong>
                    <span class="metric-meta">${usoValor}. ${escapeHtml(riscoLabel)}</span>
                </article>
            `;

            $("empresa-resumo-detalhado").innerHTML = `
                <div class="stack">
                    <div class="status-strip">
                        <span class="pill" data-kind="laudo" data-status="${empresa.status_bloqueio ? "ajustes" : "aberto"}">${empresa.status_bloqueio ? "Conta bloqueada" : "Operacao liberada"}</span>
                        <span class="pill" data-kind="role">CNPJ ${escapeHtml(empresa.cnpj || "nao informado")}</span>
                    </div>
                    <div class="usage-strip">
                        <div class="context-head">
                            <div>
                                <small>Consumo mensal monitorado</small>
                                <strong>${formatarInteiro(empresa.laudos_mes_atual || 0)} laudos criados neste mes</strong>
                            </div>
                            <span class="pill" data-kind="laudo" data-status="${capacidadeTone}">${formatarPercentual(empresa.uso_percentual)}</span>
                        </div>
                        <div class="progress-track"><div class="progress-bar" data-progress="${escapeAttr(String(progresso))}"></div></div>
                        <div class="toolbar-meta">
                            <span class="hero-chip">Limite mensal: ${empresa.laudos_mes_limite == null ? "sem teto" : formatarInteiro(empresa.laudos_mes_limite)}</span>
                            <span class="hero-chip">Laudos restantes: ${empresa.laudos_restantes == null ? "sem teto" : formatarInteiro(empresa.laudos_restantes)}</span>
                            <span class="hero-chip">Limite de usuarios: ${empresa.usuarios_max == null ? "sem teto" : formatarInteiro(empresa.usuarios_max)}</span>
                            <span class="hero-chip">Vagas restantes: ${empresa.usuarios_restantes == null ? "sem teto" : formatarInteiro(empresa.usuarios_restantes)}</span>
                        </div>
                    </div>
                    <div class="context-grid">
                        <div class="context-block">
                            <small>Equipe ocupando o plano</small>
                            <strong>${formatarInteiro(tenantAdmin?.user_summary?.total_users || empresa.usuarios_em_uso || empresa.total_usuarios)}</strong>
                        </div>
                        <div class="context-block">
                            <small>Margem de usuarios</small>
                            <strong>${escapeHtml(resumoUsuarios)}</strong>
                        </div>
                        <div class="context-block">
                            <small>Laudos na janela atual</small>
                            <strong>${formatarInteiro(empresa.laudos_mes_atual || 0)}</strong>
                        </div>
                        <div class="context-block">
                            <small>Margem do mes</small>
                            <strong>${escapeHtml(resumoLaudos)}</strong>
                        </div>
                    </div>
                    <div class="chip-list">
                        <span class="feature-chip" data-enabled="${empresa.upload_doc ? "true" : "false"}">Envio de documentos ${empresa.upload_doc ? "ativo" : "indisponivel"}</span>
                        <span class="feature-chip" data-enabled="${empresa.deep_research ? "true" : "false"}">Analise aprofundada ${empresa.deep_research ? "ativa" : "indisponivel"}</span>
                        <span class="feature-chip" data-enabled="true">Responsavel ${escapeHtml(empresa.nome_responsavel || "nao informado")}</span>
                        <span class="feature-chip" data-enabled="true">Base ${escapeHtml(empresa.cidade_estado || "nao informada")}</span>
                        <span class="feature-chip" data-enabled="true">Processamento acumulado ${formatarInteiro(empresa.mensagens_processadas || 0)}</span>
                        <span class="feature-chip" data-enabled="${governance.enabled ? "true" : "false"}">Modelo operacional ${escapeHtml(governance.operatingModelLabel)}</span>
                        <span class="feature-chip" data-enabled="${governance.enabled ? "true" : "false"}">${escapeHtml(governance.enabled ? `Continuidades: ${governance.surfacesSummary}` : "Equipe distribuida por perfis da empresa")}</span>
                    </div>
                    <div class="context-guidance" data-tone="${prioridade.tone}">
                        <div class="context-guidance-copy">
                            <small>Proximo foco da administracao</small>
                            <strong>${escapeHtml(prioridade.badge)}</strong>
                            <p>${escapeHtml(prioridade.acao)}</p>
                        </div>
                        <span class="pill" data-kind="priority" data-status="${prioridade.tone}">${escapeHtml(prioridade.badge)}</span>
                    </div>
                </div>
            `;
            const barraProgresso = documentRef.querySelector("#empresa-resumo-detalhado .progress-bar");
            if (barraProgresso) {
                barraProgresso.style.width = `${progresso}%`;
            }

            const plano = $("empresa-plano");
            if (plano) {
                plano.innerHTML = (empresa.planos_disponiveis || [])
                    .map((item) => `<option value="${escapeAttr(item)}" ${item === empresa.plano_ativo ? "selected" : ""}>${escapeHtml(item)}</option>`)
                    .join("");
            }

            if (alertaCapacidade) {
                const recomendacaoUpgrade = planoSugerido
                    ? `Migrar para ${planoSugerido} tende a aliviar primeiro ${empresa.capacidade_gargalo === "usuarios" ? "a equipe" : "a fila mensal de laudos"}.`
                    : "O plano atual ja e o topo da escada comercial configurada.";
                alertaCapacidade.innerHTML = `
                    <div class="context-guidance capacity-alert" data-tone="${capacidadeTone}">
                        <div class="context-guidance-copy">
                            <small>Capacidade e proximo passo comercial</small>
                            <strong>${escapeHtml(riscoLabel)}</strong>
                            <p>${escapeHtml(riscoMensagem)}</p>
                            <p>${escapeHtml(planoSugerido ? `${empresa.plano_sugerido_motivo || recomendacaoUpgrade}` : recomendacaoUpgrade)}</p>
                        </div>
                        <div class="capacity-alert-side">
                            <span class="pill" data-kind="priority" data-status="${capacidadeTone}">${escapeHtml(riscoLabel)}</span>
                            <span class="hero-chip">${planoSugerido ? `Plano sugerido: ${escapeHtml(planoSugerido)}` : "Sem solicitacao imediata"}</span>
                        </div>
                    </div>
                `;
            }

            if (notaCapacidadeUsuario) {
                const limiteUsuariosAtingido = empresa.usuarios_max != null && Number(empresa.usuarios_restantes || 0) <= 0;
                const limitePacoteAtingido = governance.enabled && governance.operationalUsersAtLimit;
                const bloqueioCriacao = Boolean(limiteUsuariosAtingido || limitePacoteAtingido);
                const notaTitulo = limitePacoteAtingido
                    ? "Operador unico ja ocupado"
                    : limiteUsuariosAtingido
                        ? "Equipe no teto do plano"
                        : governance.enabled
                            ? "Pacote com conta principal unificada"
                            : "Capacidade para novos usuarios";
                const notaDetalhe = limitePacoteAtingido
                    ? `${governance.operatingModelLabel}: ${formatarInteiro(governance.operationalUsersInUse)} de ${formatarInteiro(governance.operationalUserLimit)} conta operacional em uso. A administracao da empresa nao entra nessa conta.`
                    : limiteUsuariosAtingido
                        ? `${resumoUsuarios}. ${planoSugerido ? `Registre interesse em ${planoSugerido} antes de ampliar a equipe.` : "Revise o contrato antes de ampliar a equipe."}`
                        : governance.enabled
                            ? `Este pacote permite ${formatarInteiro(governance.operationalUserLimit)} conta operacional e continuidade em ${governance.surfacesSummary}. ${governance.identityNote}`
                            : `${resumoUsuarios}. ${planoSugerido && (empresa.capacidade_status === "atencao" || empresa.capacidade_status === "monitorar") ? `Se a fila crescer, o melhor encaixe passa a ser ${planoSugerido}.` : "Ainda existe folga para ampliar a equipe com seguranca."}`;
                notaCapacidadeUsuario.innerHTML = `
                    <div class="form-hint" data-tone="${bloqueioCriacao ? "ajustes" : governance.enabled ? "aguardando" : capacidadeTone}">
                        <strong>${escapeHtml(notaTitulo)}</strong>
                        <span>${escapeHtml(notaDetalhe)}</span>
                    </div>
                `;
                if (botaoCriarUsuario) {
                    botaoCriarUsuario.disabled = bloqueioCriacao;
                }
                if (formUsuario) {
                    formUsuario.dataset.operationalPackageMode = governance.operatingModel;
                    formUsuario.dataset.operationalPackageAtLimit = bloqueioCriacao ? "true" : "false";
                    formUsuario.dataset.operationalPackageSummary = pacoteOperacionalResumo;
                }
            }
        }

        function renderAdminResumo() {
            const container = $("admin-resumo-geral");
            const empresa = state.bootstrap?.empresa;
            const usuarios = state.bootstrap?.usuarios || [];
            if (!container || !empresa) return;
            const tenantAdmin = obterTenantAdminPayload();

            const bloqueados = usuarios.filter((item) => !item.ativo).length;
            const temporarios = usuarios.filter((item) => item.senha_temporaria_ativa).length;
            const semLogin = usuarios.filter((item) => !parseDataIso(item.ultimo_login)).length;
            const prioridade = prioridadeEmpresa(empresa, usuarios);
            const capacidadeTone = tomCapacidadeEmpresa(empresa);
            const resumoUsuarios = formatarCapacidadeRestante(empresa.usuarios_restantes, empresa.usuarios_excedente, "vaga", "vagas");
            const resumoLaudos = formatarCapacidadeRestante(empresa.laudos_restantes, empresa.laudos_excedente, "laudo", "laudos");
            const planoSugerido = texto(empresa.plano_sugerido).trim();
            const totalCasos = Number(tenantAdmin?.case_counts?.total_cases || state.bootstrap?.chat?.laudos?.length || 0);
            const casosAbertos = Number(tenantAdmin?.case_counts?.open_cases || 0);
            const revisoesAtivas = Number(tenantAdmin?.review_counts?.pending_review || 0)
                + Number(tenantAdmin?.review_counts?.in_review || 0);

            container.innerHTML = `
                <article class="metric-card" data-accent="attention">
                    <small>Acesso pedindo revisao</small>
                    <strong>${formatarInteiro(bloqueados)}</strong>
                    <span class="metric-meta">Usuarios bloqueados que podem travar operacao, escalonamento ou atendimento.</span>
                </article>
                <article class="metric-card" data-accent="waiting">
                    <small>Primeiros acessos</small>
                    <strong>${formatarInteiro(temporarios)}</strong>
                    <span class="metric-meta">${formatarInteiro(semLogin)} contas ainda nao registraram login no portal.</span>
                </article>
                <article class="metric-card" data-accent="${empresa.usuarios_restantes === 0 && empresa.usuarios_max != null ? "attention" : "live"}">
                    <small>Margem de equipe</small>
                    <strong>${empresa.usuarios_restantes == null ? "Livre" : formatarInteiro(empresa.usuarios_restantes)}</strong>
                    <span class="metric-meta">${escapeHtml(resumoUsuarios)} dentro do plano ${escapeHtml(empresa.plano_ativo)}.</span>
                </article>
                <article class="metric-card" data-accent="${capacidadeTone}">
                    <small>Janela de laudos</small>
                    <strong>${empresa.laudos_restantes == null ? "Livre" : formatarInteiro(empresa.laudos_restantes)}</strong>
                    <span class="metric-meta">${escapeHtml(resumoLaudos)}. ${formatarInteiro(totalCasos)} casos monitorados, ${formatarInteiro(casosAbertos)} ainda abertos.</span>
                </article>
                <article class="metric-card" data-accent="${prioridade.tone}">
                    <small>Foco da administracao</small>
                    <strong>${escapeHtml(prioridade.badge)}</strong>
                    <span class="metric-meta">${escapeHtml(prioridade.acao)} ${formatarInteiro(revisoesAtivas)} casos seguem em fila de revisao.${planoSugerido ? ` Proximo plano sugerido: ${escapeHtml(planoSugerido)}.` : ""}</span>
                </article>
            `;
        }

        function renderOverviewBrief() {
            const container = $("admin-executive-brief");
            const empresa = state.bootstrap?.empresa;
            if (!container || !empresa) return;
            const tenantAdmin = obterTenantAdminPayload();
            const prioridade = prioridadeEmpresa(empresa, state.bootstrap?.usuarios || []);
            const totalCasos = Number(tenantAdmin?.case_counts?.total_cases || 0);
            const casosAbertos = Number(tenantAdmin?.case_counts?.open_cases || 0);
            const revisoesAtivas = Number(tenantAdmin?.review_counts?.pending_review || 0)
                + Number(tenantAdmin?.review_counts?.in_review || 0);

            container.innerHTML = `
                <article class="stage-brief-card" data-tone="${escapeAttr(prioridade.tone || "aprovado")}">
                    <div class="stage-brief-card__copy">
                        <span class="stage-brief-card__eyebrow">Resumo executivo</span>
                        <strong>${escapeHtml(prioridade.badge || "Empresa sob controle")}</strong>
                        <p>${escapeHtml(prioridade.acao || "A operacao da empresa segue visivel em uma regua unica de capacidade, equipe e suporte.")}</p>
                    </div>
                    <div class="stage-brief-card__metrics">
                        <div class="context-block">
                            <small>Casos monitorados</small>
                            <strong>${escapeHtml(formatarInteiro(totalCasos))}</strong>
                        </div>
                        <div class="context-block">
                            <small>Casos abertos</small>
                            <strong>${escapeHtml(formatarInteiro(casosAbertos))}</strong>
                        </div>
                        <div class="context-block">
                            <small>Revisoes em curso</small>
                            <strong>${escapeHtml(formatarInteiro(revisoesAtivas))}</strong>
                        </div>
                    </div>
                    <div class="stage-brief-card__actions">
                        <button class="btn" type="button" data-act="abrir-prioridade" data-kind="admin-section" data-canal="admin" data-target="admin-saude-resumo" data-origem="admin">Ver pulso da operacao</button>
                        <button class="btn ghost" type="button" data-act="abrir-prioridade" data-kind="admin-section" data-canal="admin" data-target="admin-capacity-brief" data-origem="admin">Abrir capacidade</button>
                    </div>
                </article>
            `;
        }

        function renderCapacityBrief() {
            const container = $("admin-capacity-brief");
            const empresa = state.bootstrap?.empresa;
            if (!container || !empresa) return;
            const planoSugerido = texto(empresa.plano_sugerido).trim();
            const capacidadeTone = tomCapacidadeEmpresa(empresa);

            container.innerHTML = `
                <article class="stage-brief-card" data-tone="${escapeAttr(capacidadeTone)}">
                    <div class="stage-brief-card__copy">
                        <span class="stage-brief-card__eyebrow">Leitura comercial</span>
                        <strong>${escapeHtml(texto(empresa.capacidade_badge).trim() || "Capacidade monitorada")}</strong>
                        <p>${escapeHtml(texto(empresa.capacidade_acao).trim() || "Use o resumo abaixo para entender impacto, folga e proximo passo comercial sem reabrir a tela em blocos concorrentes.")}</p>
                    </div>
                    <div class="stage-brief-card__metrics">
                        <div class="context-block">
                            <small>Laudos restantes</small>
                            <strong>${empresa.laudos_restantes == null ? "Livre" : escapeHtml(formatarInteiro(empresa.laudos_restantes))}</strong>
                        </div>
                        <div class="context-block">
                            <small>Usuarios restantes</small>
                            <strong>${empresa.usuarios_restantes == null ? "Livre" : escapeHtml(formatarInteiro(empresa.usuarios_restantes))}</strong>
                        </div>
                        <div class="context-block">
                            <small>Plano sugerido</small>
                            <strong>${escapeHtml(planoSugerido || "Sem upgrade")}</strong>
                        </div>
                    </div>
                    <div class="stage-brief-card__actions">
                        ${planoSugerido
                            ? `<button class="btn primary" type="button" data-act="preparar-upgrade" data-origem="admin">Registrar interesse em ${escapeHtml(planoSugerido)}</button>`
                            : `<button class="btn" type="button" data-act="abrir-prioridade" data-kind="admin-section" data-canal="admin" data-target="admin-planos-historico" data-origem="admin">Ver historico comercial</button>`}
                    </div>
                </article>
            `;
        }

        function renderTeamBrief() {
            const container = $("admin-team-brief");
            const usuarios = state.bootstrap?.usuarios || [];
            if (!container) return;
            const governance = obterGovernancaOperacionalTenant();
            const total = usuarios.length;
            const semLogin = usuarios.filter((item) => !parseDataIso(item?.ultimo_login)).length;
            const temporarios = usuarios.filter((item) => item?.senha_temporaria_ativa).length;
            const bloqueados = usuarios.filter((item) => !item?.ativo).length;
            const tone = governance.enabled && governance.operationalUsersAtLimit
                ? "aguardando"
                : bloqueados > 0
                    ? "ajustes"
                    : temporarios > 0
                        ? "aguardando"
                        : "aprovado";
            const resumoOperacional = governance.enabled
                ? `${formatarInteiro(governance.operationalUsersInUse)} de ${formatarInteiro(governance.operationalUserLimit)} conta operacional ocupada. Continuidade prevista em ${governance.surfacesSummary}.`
                : "A equipe segue distribuida com a ativacao concluida para os perfis ativos.";

            container.innerHTML = `
                <article class="stage-brief-card" data-tone="${escapeAttr(tone)}">
                    <div class="stage-brief-card__copy">
                        <span class="stage-brief-card__eyebrow">Operacao da equipe</span>
                        <strong>${governance.enabled
                            ? "Pacote contratual com operador unico"
                            : bloqueados > 0
                                ? "Existem acessos travando a rotina"
                                : semLogin > 0
                                    ? "A ativacao ainda pede conclusao"
                                    : "Equipe principal estabilizada"}</strong>
                        <p>${escapeHtml(
                            governance.enabled
                                ? `${resumoOperacional} ${governance.identityNote}`
                                : bloqueados > 0
                                ? `${formatarInteiro(bloqueados)} cadastros bloqueados podem segurar atendimento ou revisao.`
                                : semLogin > 0
                                    ? `${formatarInteiro(semLogin)} usuarios ainda nao acessaram o portal depois da criacao.`
                                    : "A equipe segue distribuida com a ativacao concluida para os perfis ativos."
                        )}</p>
                    </div>
                    <div class="stage-brief-card__metrics">
                        <div class="context-block">
                            <small>Total operacional</small>
                            <strong>${escapeHtml(formatarInteiro(total))}</strong>
                        </div>
                        <div class="context-block">
                            <small>Primeiros acessos</small>
                            <strong>${escapeHtml(formatarInteiro(temporarios))}</strong>
                        </div>
                        <div class="context-block">
                            <small>Bloqueados</small>
                            <strong>${escapeHtml(formatarInteiro(bloqueados))}</strong>
                        </div>
                        <div class="context-block">
                            <small>${escapeHtml(governance.enabled ? "Superficies liberadas" : "Modelo atual")}</small>
                            <strong>${escapeHtml(governance.enabled ? governance.surfacesSummary : "Perfis distribuidos")}</strong>
                        </div>
                    </div>
                    <div class="stage-brief-card__actions">
                        <button class="btn" type="button" data-act="abrir-prioridade" data-kind="admin-section" data-canal="admin" data-target="admin-onboarding-lista" data-origem="admin">Abrir ativacao</button>
                        <button class="btn ghost" type="button" data-act="abrir-prioridade" data-kind="admin-section" data-canal="admin" data-target="lista-usuarios" data-origem="admin">Revisar equipe completa</button>
                    </div>
                </article>
            `;
        }

        function renderSupportBrief() {
            const container = $("admin-support-brief");
            if (!container) return;
            const tenantAdmin = obterTenantAdminPayload();
            const visibilityPolicy = tenantAdmin?.visibility_policy || {};
            const auditoria = obterAuditoriaFiltrada();
            const suporteRecente = auditoria.find((item) => texto(item?.categoria).trim().toLowerCase() === "support");
            const tone = texto(visibilityPolicy.exceptional_support_access).trim() === "disabled" ? "ajustes" : "aberto";

            container.innerHTML = `
                <article class="stage-brief-card" data-tone="${escapeAttr(tone)}">
                    <div class="stage-brief-card__copy">
                        <span class="stage-brief-card__eyebrow">Suporte governado</span>
                        <strong>${escapeHtml(
                            texto(visibilityPolicy.exceptional_support_access).trim() === "disabled"
                                ? "Suporte excepcional desabilitado"
                                : "Suporte excepcional sob aprovacao e registro"
                        )}</strong>
                        <p>${escapeHtml(
                            suporteRecente?.resumo
                                || "O portal mostra politica de acesso, diagnostico exportavel e o historico recente sem abrir evidencia tecnica bruta por padrao."
                        )}</p>
                    </div>
                    <div class="stage-brief-card__metrics">
                        <div class="context-block">
                            <small>Itens no historico</small>
                            <strong>${escapeHtml(formatarInteiro(obterAuditoriaAdmin().length))}</strong>
                        </div>
                        <div class="context-block">
                            <small>Suporte recente</small>
                            <strong>${suporteRecente?.payload?.protocolo ? escapeHtml(suporteRecente.payload.protocolo) : "Sem protocolo"}</strong>
                        </div>
                        <div class="context-block">
                            <small>Escopo maximo</small>
                            <strong>${escapeHtml(texto(visibilityPolicy.exceptional_support_scope_level).replaceAll("_", " ") || "administrative")}</strong>
                        </div>
                    </div>
                    <div class="stage-brief-card__actions">
                        <button class="btn" type="button" data-act="abrir-prioridade" data-kind="admin-section" data-canal="admin" data-target="admin-auditoria-lista" data-origem="admin">Abrir historico</button>
                        <button class="btn ghost" type="button" data-act="abrir-prioridade" data-kind="admin-section" data-canal="admin" data-target="form-suporte-cliente" data-origem="admin">Registrar suporte</button>
                    </div>
                </article>
            `;
        }

        function renderSaudeEmpresa() {
            const empresa = state.bootstrap?.empresa;
            const resumo = $("admin-saude-resumo");
            const historico = $("admin-saude-historico");
            const saude = empresa?.saude_operacional;
            if (!empresa || !resumo || !historico || !saude) return;

            resumo.innerHTML = `
                <article class="metric-card" data-accent="${escapeAttr(saude.tone || "aprovado")}">
                    <small>Status da operacao</small>
                    <strong>${escapeHtml(saude.status || "Sem leitura")}</strong>
                    <span class="metric-meta">${escapeHtml(saude.texto || "Sem observacoes adicionais.")}</span>
                </article>
                <article class="metric-card" data-accent="${escapeAttr(saude.tendencia_tone || "aberto")}">
                    <small>Tendencia mensal</small>
                    <strong>${escapeHtml(saude.tendencia_rotulo || "Estavel")}</strong>
                    <span class="metric-meta">${escapeHtml(formatarVariacao(saude.variacao_mensal_percentual || 0))} em relacao ao mes anterior.</span>
                </article>
                <article class="metric-card" data-accent="live">
                    <small>Equipe ativa em 14 dias</small>
                    <strong>${escapeHtml(formatarInteiro(saude.usuarios_login_recente || 0))}</strong>
                    <span class="metric-meta">${escapeHtml(formatarInteiro(saude.usuarios_sem_login_recente || 0))} ainda nao apareceram na janela recente.</span>
                </article>
                <article class="metric-card" data-accent="waiting">
                    <small>Movimentos comerciais</small>
                    <strong>${escapeHtml(formatarInteiro(saude.eventos_comerciais_60d || 0))}</strong>
                    <span class="metric-meta">${escapeHtml(formatarInteiro(saude.primeiros_acessos_pendentes || 0))} primeiros acessos ainda pedem conclusao.</span>
                </article>
            `;

            historico.innerHTML = `
                <article class="health-card">
                    <div class="context-guidance" data-tone="${escapeAttr(saude.tendencia_tone || "aberto")}">
                        <div class="context-guidance-copy">
                            <small>Ultimos 6 meses</small>
                            <strong>${escapeHtml(saude.tendencia_rotulo || "Ritmo estavel")}</strong>
                            <p>Mes atual: ${escapeHtml(formatarInteiro(saude.laudos_mes_atual || 0))} laudos. Mes anterior: ${escapeHtml(formatarInteiro(saude.laudos_mes_anterior || 0))}.</p>
                        </div>
                        <span class="pill" data-kind="priority" data-status="${escapeAttr(saude.tendencia_tone || "aberto")}">${escapeHtml(formatarVariacao(saude.variacao_mensal_percentual || 0))}</span>
                    </div>
                    ${htmlBarrasHistorico(saude.historico_mensal || [], saude.tendencia_tone || "aberto")}
                </article>
                <article class="health-card">
                    <div class="context-guidance" data-tone="${escapeAttr(saude.tone || "aprovado")}">
                        <div class="context-guidance-copy">
                            <small>Pulso dos ultimos 14 dias</small>
                            <strong>${escapeHtml(saude.status || "Sem leitura")}</strong>
                            <p>${escapeHtml(formatarInteiro(saude.usuarios_login_recente || 0))} pessoas usaram o portal recentemente, com ${escapeHtml(formatarInteiro(saude.mix_equipe?.inspetores || 0))} pessoas de campo e ${escapeHtml(formatarInteiro(saude.mix_equipe?.revisores || 0))} pessoas de revisao no mix.</p>
                        </div>
                        <span class="pill" data-kind="priority" data-status="${escapeAttr(saude.tone || "aprovado")}">${escapeHtml(formatarInteiro(saude.eventos_comerciais_60d || 0))} eventos</span>
                    </div>
                    ${htmlBarrasHistorico(saude.historico_diario || [], saude.tone || "aprovado")}
                </article>
            `;
        }

        function renderSuporteDiagnostico() {
            const container = $("admin-diagnostico-resumo");
            const policyContainer = $("admin-support-policy");
            const protocolContainer = $("admin-support-protocol");
            const portal = state.bootstrap?.portal;
            const empresa = state.bootstrap?.empresa;
            if (!container || !portal || !empresa) return;
            const tenantAdmin = obterTenantAdminPayload();
            const visibilityPolicy = tenantAdmin?.visibility_policy || null;
            const governance = obterGovernancaOperacionalTenant();
            const auditoria = obterAuditoriaAdmin();
            const suporteRecente = auditoria.find((item) => texto(item?.categoria).trim().toLowerCase() === "support");

            const whatsapp = texto(portal.suporte_whatsapp).trim();
            const ambiente = texto(portal.ambiente).trim() || "producao";
            const diagnosticoUrl = texto(portal.diagnostico_url).trim() || "/cliente/api/diagnostico";
            const totalAuditoria = auditoria.length;
            const auditoriaResumo = state.bootstrap?.auditoria?.resumo || {};
            const categorias = auditoriaResumo.categories || {};
            const supportModeLabels = {
                disabled: "desabilitado",
                approval_required: "com aprovacao previa",
                incident_controlled: "em incidente controlado",
            };
            const supportScopeLabels = {
                metadata_only: "metadados administrativos",
                administrative: "suporte administrativo",
                tenant_diagnostic: "diagnostico da empresa",
            };
            const technicalAccessLabels = {
                surface_scoped_operational: "superficies operacionais auditadas",
            };
            const auditScopeLabels = {
                tenant_operational_timeline: "historico operacional da empresa",
            };

            container.innerHTML = `
                <span>Ambiente: ${escapeHtml(ambiente)}</span>
                <span>Diagnostico: ${escapeHtml(diagnosticoUrl)}</span>
                <span>Auditoria visivel: ${escapeHtml(formatarInteiro(totalAuditoria))} itens</span>
                <span>Suporte: ${escapeHtml(whatsapp || "nao configurado")}</span>
                <span>Visibilidade tecnica: ${escapeHtml(
                    technicalAccessLabels[visibilityPolicy?.technical_access_mode] || "nao definida"
                )}</span>
                <span>Evidencia bruta: ${escapeHtml(
                    visibilityPolicy?.raw_evidence_access === "not_granted_by_projection"
                        ? "fora da projecao gerencial"
                        : "nao definida"
                )}</span>
                <span>Escopo de auditoria: ${escapeHtml(
                    auditScopeLabels[visibilityPolicy?.audit_scope] || "nao definido"
                )}</span>
                <span>Politica de suporte: ${escapeHtml(
                    supportModeLabels[visibilityPolicy?.exceptional_support_access] || "nao definida"
                )}</span>
                <span>Modelo operacional: ${escapeHtml(governance.operatingModelLabel)}</span>
                <span>Continuidade prevista: ${escapeHtml(governance.surfacesSummary)}</span>
                <span>Escopo maximo de suporte: ${escapeHtml(
                    supportScopeLabels[visibilityPolicy?.exceptional_support_scope_level] || "nao definido"
                )}</span>
                <span>Eventos de equipe/comercial: ${escapeHtml(
                    formatarInteiro(
                        Number(categorias.access || 0) + Number(categorias.commercial || 0) + Number(categorias.team || 0)
                    )
                )}</span>
                <span>Eventos de suporte/chat/mesa: ${escapeHtml(
                    formatarInteiro(
                        Number(categorias.support || 0) + Number(categorias.chat || 0) + Number(categorias.mesa || 0)
                    )
                )}</span>
            `;

            if (policyContainer) {
                policyContainer.innerHTML = `
                    <article class="support-policy-card">
                        <small>Visibilidade tecnica</small>
                        <strong>${escapeHtml(technicalAccessLabels[visibilityPolicy?.technical_access_mode] || "nao definida")}</strong>
                        <span>Evidencia bruta ${visibilityPolicy?.raw_evidence_access === "not_granted_by_projection" ? "fica fora da projecao gerencial" : "nao definida"}.</span>
                    </article>
                    <article class="support-policy-card">
                        <small>Suporte excepcional</small>
                        <strong>${escapeHtml(supportModeLabels[visibilityPolicy?.exceptional_support_access] || "nao definida")}</strong>
                        <span>Escopo maximo ${escapeHtml(supportScopeLabels[visibilityPolicy?.exceptional_support_scope_level] || "nao definido")}.</span>
                    </article>
                    <article class="support-policy-card">
                        <small>Escopo de auditoria</small>
                        <strong>${escapeHtml(auditScopeLabels[visibilityPolicy?.audit_scope] || "nao definido")}</strong>
                        <span>${escapeHtml(formatarInteiro(totalAuditoria))} itens recentes disponiveis para leitura da empresa.</span>
                    </article>
                    <article class="support-policy-card">
                        <small>Pacote operacional</small>
                        <strong>${escapeHtml(governance.operatingModelLabel)}</strong>
                        <span>${escapeHtml(
                            governance.enabled
                                ? `${formatarInteiro(governance.operationalUsersInUse)} de ${formatarInteiro(governance.operationalUserLimit)} conta operacional ocupada. Continuidade em ${governance.surfacesSummary}.`
                                : "Sem limite contratual de operador unico nesta empresa."
                        )}</span>
                    </article>
                `;
            }

            if (protocolContainer) {
                protocolContainer.innerHTML = `
                    <div class="support-protocol__copy">
                        <span class="support-protocol__eyebrow">Protocolo e janela de suporte</span>
                        <strong>${escapeHtml(suporteRecente?.payload?.protocolo || "Nenhum protocolo recente")}</strong>
                        <p>${escapeHtml(
                            suporteRecente?.detalhe
                                || "Quando houver novo relato, o numero de protocolo e o historico do caso ficam visiveis aqui sem expor evidencia tecnica bruta."
                        )}</p>
                    </div>
                    <div class="support-protocol__status">
                        <span class="pill" data-kind="priority" data-status="${visibilityPolicy?.exceptional_support_access === "disabled" ? "ajustes" : "aberto"}">${escapeHtml(
                            visibilityPolicy?.exceptional_support_step_up_required ? "step-up exigido" : "step-up opcional"
                        )}</span>
                        <span class="hero-chip">${escapeHtml(
                            visibilityPolicy?.exceptional_support_approval_required ? "aprovacao obrigatoria" : "aprovacao contextual"
                        )}</span>
                        <span class="hero-chip">janela maxima ${escapeHtml(formatarInteiro(visibilityPolicy?.exceptional_support_max_duration_minutes || 0))} min</span>
                    </div>
                `;
            }

            const botaoWhatsapp = $("btn-whatsapp-suporte");
            if (botaoWhatsapp) {
                botaoWhatsapp.disabled = !whatsapp;
            }
        }

        function renderOnboardingEquipe() {
            const resumo = $("admin-onboarding-resumo");
            const lista = $("admin-onboarding-lista");
            const usuarios = state.bootstrap?.usuarios || [];
            if (!resumo || !lista) return;

            const temporarios = ordenarPorPrioridade(
                usuarios.filter((item) => item?.senha_temporaria_ativa),
                prioridadeUsuario
            );
            const semLogin = ordenarPorPrioridade(
                usuarios.filter((item) => !parseDataIso(item?.ultimo_login)),
                prioridadeUsuario
            );
            const bloqueados = ordenarPorPrioridade(
                usuarios.filter((item) => !item?.ativo),
                prioridadeUsuario
            );
            const revisoresSemLogin = semLogin.filter((item) => slugPapel(item) === "revisor");

            resumo.innerHTML = `
                <article class="metric-card" data-accent="waiting">
                    <small>Primeiros acessos</small>
                    <strong>${formatarInteiro(temporarios.length)}</strong>
                    <span class="metric-meta">Usuarios com senha temporaria ainda pendente de ativacao.</span>
                </article>
                <article class="metric-card" data-accent="aberto">
                    <small>Sem login</small>
                    <strong>${formatarInteiro(semLogin.length)}</strong>
                    <span class="metric-meta">Cadastros criados que ainda nao entraram nenhuma vez.</span>
                </article>
                <article class="metric-card" data-accent="attention">
                    <small>Bloqueados</small>
                    <strong>${formatarInteiro(bloqueados.length)}</strong>
                    <span class="metric-meta">Acessos travados que podem segurar a operacao da empresa.</span>
                </article>
                <article class="metric-card" data-accent="live">
                    <small>Mesa sem login</small>
                    <strong>${formatarInteiro(revisoresSemLogin.length)}</strong>
                    <span class="metric-meta">Pessoas da revisao que ainda nao ativaram o acesso.</span>
                </article>
            `;

            const pendenciasMap = new Map();
            [...temporarios, ...bloqueados, ...semLogin].forEach((item) => {
                if (item?.id != null) pendenciasMap.set(Number(item.id), item);
            });
            const pendencias = ordenarPorPrioridade([...pendenciasMap.values()], prioridadeUsuario).slice(0, 4);

            const quickActions = `
                <div class="toolbar-meta">
                    <button class="btn" type="button" data-act="filtrar-usuarios-status" data-situacao="temporarios">Ver primeiros acessos</button>
                    <button class="btn" type="button" data-act="filtrar-usuarios-status" data-situacao="sem_login">Ver sem login</button>
                    <button class="btn" type="button" data-act="filtrar-usuarios-status" data-situacao="bloqueados">Ver bloqueados</button>
                    <button class="btn ghost" type="button" data-act="limpar-filtro-usuarios">Limpar filtro rapido</button>
                </div>
            `;

            if (!pendencias.length) {
                lista.innerHTML = `
                    <div class="empty-state">
                        <strong>Equipe principal ativada</strong>
                        <p>Nao ha ativacao pendente agora. Novos primeiros acessos e bloqueios vao aparecer aqui.</p>
                    </div>
                    ${quickActions}
                `;
                return;
            }

            lista.innerHTML = `
                ${quickActions}
                ${pendencias.map((usuario) => {
                    const prioridade = prioridadeUsuario(usuario);
                    const papel = slugPapel(usuario);
                    const detalhe =
                        !usuario.ativo
                            ? `${usuario.nome || "Usuario"} esta bloqueado e pode estar segurando a rotina da empresa.`
                            : usuario.senha_temporaria_ativa
                                ? `${usuario.nome || "Usuario"} ainda precisa concluir o primeiro acesso.`
                                : `${usuario.nome || "Usuario"} foi criado, mas ainda nao entrou nenhuma vez.`;

                    return `
                        <article class="activity-item">
                            <div class="activity-head">
                                <div class="activity-copy">
                                    <strong>${escapeHtml(usuario.nome || "Usuario")}</strong>
                                    <span class="activity-meta">${escapeHtml(usuario.email || "Sem e-mail")} • ${escapeHtml(obterNomePapel(papel))}</span>
                                </div>
                                <span class="pill" data-kind="priority" data-status="${escapeAttr(prioridade.tone)}">${escapeHtml(prioridade.badge)}</span>
                            </div>
                            <p class="activity-detail">${escapeHtml(detalhe)}</p>
                            <div class="toolbar-meta">
                                ${!usuario.ativo
                                    ? `<button class="btn" type="button" data-act="toggle-user" data-user="${escapeAttr(String(usuario.id || ""))}">Desbloquear agora</button>`
                                    : `<button class="btn" type="button" data-act="reset-user" data-user="${escapeAttr(String(usuario.id || ""))}">Gerar nova senha</button>`}
                                <button
                                    class="btn"
                                    type="button"
                                    data-act="abrir-prioridade"
                                    data-kind="admin-user"
                                    data-canal="admin"
                                    data-target="lista-usuarios"
                                    data-user="${escapeAttr(String(usuario.id || ""))}"
                                    data-busca="${escapeAttr(usuario.email || usuario.nome || "")}"
                                    data-papel="${escapeAttr(papel)}"
                                >Abrir cadastro</button>
                            </div>
                        </article>
                    `;
                }).join("")}
            `;
        }

        function renderAdminAuditoria() {
            const container = $("admin-auditoria-lista");
            const filtersContainer = $("admin-auditoria-filtros");
            const overviewContainer = $("admin-audit-overview");
            const searchInput = $("admin-auditoria-busca");
            if (!container) return;

            const todosItens = obterAuditoriaAdmin();
            const filtroAtual = normalizarFiltroAuditoriaAdmin(state.ui?.adminAuditFilter);
            const buscaAtual = texto(state.ui?.adminAuditSearch).trim();
            const itens = obterAuditoriaFiltrada();
            const resumo = obterResumoAuditoriaFiltrada(itens);

            if (searchInput && searchInput.value !== buscaAtual) {
                searchInput.value = buscaAtual;
            }

            if (overviewContainer) {
                overviewContainer.innerHTML = `
                    <article class="metric-card" data-accent="live">
                        <small>Itens visiveis</small>
                        <strong>${escapeHtml(formatarInteiro(resumo.total))}</strong>
                        <span class="metric-meta">${buscaAtual ? "Resultado apos busca e filtro atual." : "Historico atual conforme a secao selecionada."}</span>
                    </article>
                    <article class="metric-card" data-accent="aberto">
                        <small>Foco administrativo</small>
                        <strong>${escapeHtml(formatarInteiro(
                            Number(resumo.categories.team || 0) + Number(resumo.categories.access || 0) + Number(resumo.categories.commercial || 0)
                        ))}</strong>
                        <span class="metric-meta">Equipe, acesso e comercial dentro do recorte atual.</span>
                    </article>
                    <article class="metric-card" data-accent="waiting">
                        <small>Suporte e operacao</small>
                        <strong>${escapeHtml(formatarInteiro(
                            Number(resumo.categories.support || 0) + Number(resumo.categories.chat || 0) + Number(resumo.categories.mesa || 0)
                        ))}</strong>
                        <span class="metric-meta">Protocolos, chat e mesa sob o mesmo trilho cronologico.</span>
                    </article>
                    <article class="metric-card" data-accent="aprovado">
                        <small>Escopo dominante</small>
                        <strong>${escapeHtml(
                            resumo.scopes.chat > resumo.scopes.admin && resumo.scopes.chat >= resumo.scopes.mesa
                                ? "Chat"
                                : resumo.scopes.mesa > resumo.scopes.admin
                                    ? "Mesa"
                                    : "Painel"
                        )}</strong>
                        <span class="metric-meta">${escapeHtml(formatarInteiro(todosItens.length))} itens totais na empresa antes do recorte.</span>
                    </article>
                `;
            }

            if (filtersContainer) {
                filtersContainer.innerHTML = AUDIT_FILTERS.map((item) => `
                    <button
                        class="audit-filter${item.key === filtroAtual ? " is-active" : ""}"
                        type="button"
                        data-audit-filter="${escapeAttr(item.key)}"
                        aria-pressed="${item.key === filtroAtual ? "true" : "false"}"
                        title="${escapeAttr(item.description)}"
                    >
                        <span>${escapeHtml(item.label)}</span>
                        <small>${escapeHtml(item.description)}</small>
                    </button>
                `).join("");
            }

            if (!todosItens.length) {
                container.innerHTML = `
                    <div class="empty-state">
                        <strong>Nenhuma atividade registrada ainda</strong>
                        <p>As alteracoes de plano, equipe e acesso passam a aparecer aqui conforme o portal for sendo usado.</p>
                    </div>
                `;
                return;
            }

            if (!itens.length) {
                container.innerHTML = `
                    <div class="empty-state">
                        <strong>Nenhum evento encontrado nesse recorte</strong>
                        <p>${escapeHtml(
                            buscaAtual
                                ? `A busca "${buscaAtual}" nao encontrou eventos dentro do filtro atual.`
                                : "Troque o filtro para recuperar outro trecho do historico operacional."
                        )}</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = agruparAuditoriaPorDia(itens).map((grupo) => `
                <section class="activity-group">
                    <header class="activity-group__header">
                        <span class="activity-group__eyebrow">${escapeHtml(grupo.dateKey === "sem-data" ? "Sem data" : grupo.dateKey.split("-").reverse().join("/"))}</span>
                        <strong>${escapeHtml(formatarInteiro(grupo.rows.length))} eventos</strong>
                    </header>
                    <div class="activity-group__items">
                        ${grupo.rows.map((item) => `
                            <article class="activity-item">
                                <div class="activity-head">
                                    <div class="activity-copy">
                                        <strong>${escapeHtml(item.resumo || "Ação registrada")}</strong>
                                        <span class="activity-meta">${escapeHtml(item.categoria_label || "Geral")} • ${escapeHtml(item.scope_label || "Painel")} • Por ${escapeHtml(item.ator_nome || "Sistema")} • ${escapeHtml(item.criado_em_label || "Agora")}</span>
                                    </div>
                                    <span class="pill" data-kind="priority" data-status="${escapeAttr(item.categoria === "support" ? "aguardando" : item.scope === "chat" || item.scope === "mesa" ? "aberto" : "aprovado")}">${escapeHtml(texto(item.acao || "evento").replaceAll("_", " "))}</span>
                                </div>
                                ${item.detalhe ? `<p class="activity-detail">${escapeHtml(item.detalhe)}</p>` : ""}
                                <div class="toolbar-meta">
                                    ${item.payload?.protocolo ? `<span class="hero-chip">Protocolo ${escapeHtml(item.payload.protocolo)}</span>` : ""}
                                    ${item.alvo_nome ? `<span class="hero-chip">Alvo ${escapeHtml(item.alvo_nome)}</span>` : ""}
                                    ${item.payload?.contexto ? `<span class="hero-chip">${escapeHtml(item.payload.contexto)}</span>` : ""}
                                </div>
                            </article>
                        `).join("")}
                    </div>
                </section>
            `).join("");
        }

        function renderHistoricoPlanos() {
            const container = $("admin-planos-historico");
            if (!container) return;

            const itens = (state.bootstrap?.auditoria?.itens || []).filter((item) => {
                const acao = texto(item?.acao);
                return acao === "plano_interesse_registrado" || acao === "plano_alterado";
            });
            if (!itens.length) {
                container.innerHTML = `
                    <div class="empty-state">
                        <strong>Nenhuma solicitacao comercial registrada ainda</strong>
                        <p>Quando o portal registrar interesse em um novo plano, o impacto esperado fica listado aqui para consulta rapida.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = itens.map((item) => {
                const payload = item.payload || {};
                const antes = texto(payload.plano_anterior || "").trim();
                const depois = texto(payload.plano_sugerido || payload.plano_novo || "").trim();
                const impacto = texto(payload.impacto_resumido || item.detalhe || "").trim();
                const acao = texto(item.acao);
                const rotuloMovimento = acao === "plano_interesse_registrado"
                    ? "solicitacao"
                    : texto(payload.movimento || "plano");
                return `
                    <article class="activity-item">
                        <div class="activity-head">
                            <div class="activity-copy">
                                <strong>${escapeHtml(item.resumo || "Solicitacao comercial")}</strong>
                                <span class="activity-meta">Por ${escapeHtml(item.ator_nome || "Sistema")} • ${escapeHtml(item.criado_em_label || "Agora")}</span>
                            </div>
                            <span class="pill" data-kind="priority" data-status="aberto">${escapeHtml(rotuloMovimento)}</span>
                        </div>
                        <p class="activity-detail">${escapeHtml(impacto || "Impacto nao informado.")}</p>
                        <div class="toolbar-meta">
                            <span class="hero-chip">${antes ? `Antes: ${escapeHtml(antes)}` : "Antes nao informado"}</span>
                            <span class="hero-chip">${depois ? `Depois: ${escapeHtml(depois)}` : "Depois nao informado"}</span>
                        </div>
                    </article>
                `;
            }).join("");
        }

        function renderPreviewPlano() {
            const container = $("plano-impacto-preview");
            const empresa = state.bootstrap?.empresa;
            const seletor = $("empresa-plano");
            const botao = $("btn-plano-registrar");
            if (!container || !empresa || !seletor) return;

            const planoSelecionado = obterPlanoCatalogo(seletor.value) || obterPlanoCatalogo(empresa.plano_ativo);
            if (!planoSelecionado) {
                container.innerHTML = "";
                if (botao) botao.disabled = false;
                return;
            }

            const ehAtual = texto(planoSelecionado.plano) === texto(empresa.plano_ativo);
            const movimento = texto(planoSelecionado.movimento || (ehAtual ? "manter" : "upgrade"));
            const tone = ehAtual ? "aprovado" : movimento === "downgrade" ? "aguardando" : "aberto";
            const chips = [];
            chips.push(`<span class="hero-chip">Usuarios: ${escapeHtml(formatarLimitePlano(planoSelecionado.usuarios_max, "vaga", "vagas"))}</span>`);
            chips.push(`<span class="hero-chip">Laudos/mes: ${escapeHtml(formatarLimitePlano(planoSelecionado.laudos_mes, "laudo", "laudos"))}</span>`);
            chips.push(`<span class="hero-chip">${planoSelecionado.upload_doc ? "Envio de documentos liberado" : "Envio de documentos indisponivel"}</span>`);
            chips.push(`<span class="hero-chip">${planoSelecionado.deep_research ? "Analise aprofundada liberada" : "Analise aprofundada indisponivel"}</span>`);
            const acoes = ehAtual
                ? ""
                : `
                    <div class="toolbar-meta toolbar-meta--section">
                        <button class="btn" type="button" data-act="registrar-interesse-plano" data-origem="admin" data-plano="${escapeAttr(planoSelecionado.plano)}">Registrar interesse neste plano</button>
                    </div>
                `;

            container.innerHTML = `
                <div class="context-guidance" data-tone="${tone}">
                    <div class="context-guidance-copy">
                        <small>${ehAtual ? "Plano atual em vigor" : "Impacto esperado da solicitacao"}</small>
                        <strong>${escapeHtml(planoSelecionado.plano)}</strong>
                        <p>${escapeHtml(ehAtual
                            ? `Este plano sustenta hoje ${state.bootstrap?.empresa?.capacidade_badge ? state.bootstrap.empresa.capacidade_badge.toLowerCase() : "a operacao atual"}.`
                            : planoSelecionado.resumo_impacto || "Sem alteracao material detectada.")}</p>
                        ${ehAtual ? "" : `<p>A solicitacao fica registrada para a empresa, mas a mudanca comercial final e concluida pela Tariel.</p>`}
                    </div>
                    <span class="pill" data-kind="priority" data-status="${tone}">${escapeHtml(ehAtual ? "Plano atual" : movimento)}</span>
                </div>
                <div class="toolbar-meta toolbar-meta--section">
                    ${chips.join("")}
                </div>
                ${acoes}
            `;

            if (botao) {
                botao.disabled = ehAtual;
            }
        }

        function labelPortalUsuario(portal) {
            const valor = texto(portal).trim().toLowerCase();
            if (valor === "cliente") return "Portal da empresa";
            if (valor === "inspetor") return "Campo web + mobile";
            if (valor === "revisor") return "Revisao";
            return valor || "Portal";
        }

        function htmlPortalGrantChips(usuario) {
            const labels = Array.isArray(usuario?.allowed_portal_labels) && usuario.allowed_portal_labels.length
                ? usuario.allowed_portal_labels
                : (Array.isArray(usuario?.allowed_portals) ? usuario.allowed_portals.map(labelPortalUsuario) : []);
            return labels.map((label) => `<span class="hero-chip">${escapeHtml(label)}</span>`).join("");
        }

        function htmlPortalGrantEditor(usuario, governance) {
            const baseRole = slugPapel(usuario);
            const currentPortals = new Set(Array.isArray(usuario?.allowed_portals) ? usuario.allowed_portals : []);
            const canGrantCross = Boolean(governance.operationalUserCrossPortalEnabled);
            const canGrantCliente = Boolean(governance.operationalUserAdminPortalEnabled);
            const controls = [
                {
                    portal: "inspetor",
                    label: "Campo web + mobile",
                    checked: currentPortals.has("inspetor") || baseRole === "inspetor",
                    disabled: true,
                },
                {
                    portal: "revisor",
                    label: "Revisao",
                    checked: currentPortals.has("revisor") || baseRole === "revisor",
                    disabled: baseRole === "revisor" ? true : !canGrantCross,
                },
                {
                    portal: "cliente",
                    label: "Portal da empresa",
                    checked: currentPortals.has("cliente"),
                    disabled: !canGrantCliente,
                },
            ];
            return `
                <div class="stack">
                    <small>Superficies liberadas</small>
                    <div class="user-grid">
                        ${controls.map((item) => `
                            <label>
                                <input
                                    type="checkbox"
                                    data-user="${usuario.id}"
                                    data-field="allowed_portals"
                                    data-portal="${escapeAttr(item.portal)}"
                                    ${item.checked ? "checked" : ""}
                                    ${item.disabled ? "disabled" : ""}
                                >
                                ${escapeHtml(item.label)}
                            </label>
                        `).join("")}
                    </div>
                </div>
            `;
        }

        function renderUsuarios() {
            const usuarios = ordenarPorPrioridade(filtrarUsuarios(), prioridadeUsuario);
            const tbody = $("lista-usuarios");
            const vazio = $("usuarios-vazio");
            const resumo = $("usuarios-resumo");
            if (!tbody || !vazio || !resumo) return;

            const governance = obterGovernancaOperacionalTenant();
            const totalTemporarios = (state.bootstrap?.usuarios || []).filter((item) => item.senha_temporaria_ativa).length;
            const totalBloqueados = (state.bootstrap?.usuarios || []).filter((item) => !item.ativo).length;
            const totalSemLogin = (state.bootstrap?.usuarios || []).filter((item) => !parseDataIso(item.ultimo_login)).length;
            const rotuloFiltroRapido = rotuloSituacaoUsuarios(state.ui.usuariosSituacao) || "";
            resumo.innerHTML = `
                <span class="hero-chip">${formatarInteiro(usuarios.length)} visiveis agora</span>
                <span class="hero-chip">${formatarInteiro(totalTemporarios)} com senha temporaria</span>
                <span class="hero-chip">${formatarInteiro(totalBloqueados)} bloqueados</span>
                <span class="hero-chip">${formatarInteiro(totalSemLogin)} sem login</span>
                <span class="hero-chip">${formatarInteiro((state.bootstrap?.usuarios || []).filter((item) => item.ativo).length)} ativos</span>
                ${governance.enabled ? `<span class="hero-chip">Pacote: ${escapeHtml(formatarInteiro(governance.operationalUsersInUse))}/${escapeHtml(formatarInteiro(governance.operationalUserLimit))} operador</span>` : ""}
                ${rotuloFiltroRapido ? `<span class="hero-chip">Filtro rapido: ${escapeHtml(rotuloFiltroRapido)}</span>` : ""}
            `;

            if (!usuarios.length) {
                tbody.innerHTML = "";
                vazio.hidden = false;
                return;
            }

            vazio.hidden = true;
            tbody.innerHTML = usuarios.map((usuario) => {
                const papel = obterNomePapel(slugPapel(usuario));
                const ultimoLogin = escapeHtml(usuario.ultimo_login_label || "Nunca");
                const prioridade = prioridadeUsuario(usuario);
                const emDestaque = Number(state.ui.usuarioEmDestaque || 0) === Number(usuario.id);

                return `
                    <tr data-user-row="${usuario.id}"${emDestaque ? ' class="user-row-highlight"' : ""}>
                        <td>
                            <div class="user-main">
                                <div class="user-primary">
                                    <span class="user-name">${escapeHtml(usuario.nome || "Usuario")}</span>
                                    ${roleBadge(papel)}
                                    ${userStatusBadges(usuario)}
                                    <span class="pill" data-kind="priority" data-status="${prioridade.tone}">${escapeHtml(prioridade.badge)}</span>
                                </div>
                                <div class="user-email">${escapeHtml(usuario.email)}</div>
                                <div class="toolbar-meta">
                                    <span class="hero-chip">${usuario.telefone ? escapeHtml(usuario.telefone) : "Sem telefone"}</span>
                                    ${slugPapel(usuario) === "revisor"
                                        ? `<span class="hero-chip">${usuario.crea ? `CREA ${escapeHtml(usuario.crea)}` : "Sem CREA"}</span>`
                                        : ""}
                                    ${htmlPortalGrantChips(usuario)}
                                </div>
                                <details class="user-editor">
                                    <summary class="user-editor-toggle">Editar dados deste usuario</summary>
                                    <div class="user-grid">
                                        <label>Nome<input data-field="nome" data-user="${usuario.id}" value="${escapeAttr(usuario.nome || "")}"></label>
                                        <label>E-mail<input data-field="email" data-user="${usuario.id}" type="email" value="${escapeAttr(usuario.email || "")}"></label>
                                        <label>Telefone<input data-field="telefone" data-user="${usuario.id}" value="${escapeAttr(usuario.telefone || "")}" placeholder="Telefone"></label>
                                        ${slugPapel(usuario) === "revisor"
                                            ? `<label>CREA<input data-field="crea" data-user="${usuario.id}" value="${escapeAttr(usuario.crea || "")}" placeholder="CREA"></label>`
                                            : ""}
                                    </div>
                                    ${htmlPortalGrantEditor(usuario, governance)}
                                </details>
                            </div>
                        </td>
                        <td>
                            <div class="stack">
                                <div class="context-block">
                                    <small>Papel operacional</small>
                                    <strong>${escapeHtml(papel)}</strong>
                                </div>
                                <div class="context-block">
                                    <small>Ultimo login</small>
                                    <strong>${ultimoLogin}</strong>
                                </div>
                                <div class="context-guidance" data-tone="${prioridade.tone}">
                                    <div class="context-guidance-copy">
                                        <small>Foco deste cadastro</small>
                                        <strong>${escapeHtml(prioridade.badge)}</strong>
                                        <p>${escapeHtml(prioridade.acao)}</p>
                                    </div>
                                </div>
                            </div>
                        </td>
                        <td>
                            <div class="user-actions">
                                <button class="btn" data-act="save-user" data-user="${usuario.id}" type="button">Salvar cadastro</button>
                                <button class="btn" data-act="toggle-user" data-user="${usuario.id}" type="button">${usuario.ativo ? "Bloquear acesso" : "Desbloquear acesso"}</button>
                                <button class="btn ghost" data-act="reset-user" data-user="${usuario.id}" type="button">Gerar senha temporaria</button>
                                <button class="btn ghost" data-act="delete-user" data-user="${usuario.id}" type="button">Excluir cadastro</button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join("");
        }

        function renderAdminStage(stage, { force = false } = {}) {
            const targetStage = normalizarSecaoAdmin(stage);
            limparStageAgendado(targetStage);
            marcarEstadoStage(targetStage, "rendering");

            if (targetStage === "overview") {
                renderOverviewBrief();
                renderAdminResumo();
                renderEmpresaCards();
                renderSaudeEmpresa();
            } else if (targetStage === "capacity") {
                renderCapacityBrief();
                renderPreviewPlano();
                renderHistoricoPlanos();
            } else if (targetStage === "team") {
                renderTeamBrief();
                renderOnboardingEquipe();
                renderUsuarios();
            } else {
                renderSupportBrief();
                renderAdminAuditoria();
                renderSuporteDiagnostico();
            }

            if (force) {
                marcarEstadoStage(targetStage, "ready");
                return;
            }
            marcarEstadoStage(targetStage, "ready");
        }

        function agendarStage(stage, delay) {
            if (!STAGE_ORDER.includes(stage)) return;
            limparStageAgendado(stage);
            marcarEstadoStage(stage, "queued");

            const timeoutId = windowRef.setTimeout(() => {
                if (typeof windowRef.requestIdleCallback === "function") {
                    const idleId = windowRef.requestIdleCallback(() => {
                        renderAdminStage(stage, { force: true });
                    }, { timeout: 240 });
                    queuedStages.set(stage, {
                        cancelIdle: () => windowRef.cancelIdleCallback(idleId),
                    });
                    return;
                }
                renderAdminStage(stage, { force: true });
            }, delay);

            queuedStages.set(stage, { timeoutId });
        }

        function renderAdmin() {
            const secaoAtiva = abrirSecaoAdmin(state.ui?.adminSection || "overview", { ensureRendered: false });
            renderAdminStage(secaoAtiva, { force: true });
            atualizarResumoSecaoAdmin();
            STAGE_ORDER.filter((stage) => stage !== secaoAtiva).forEach((stage, index) => {
                agendarStage(stage, 36 + (index * 44));
            });
        }

        return {
            abrirSecaoAdmin,
            obterGovernancaOperacionalTenant,
            renderAdmin,
            renderAdminAuditoria,
            renderAdminResumo,
            renderEmpresaCards,
            renderHistoricoPlanos,
            renderOnboardingEquipe,
            renderPreviewPlano,
            renderSaudeEmpresa,
            renderSuporteDiagnostico,
            renderUsuarios,
            resolverSecaoAdminPorTarget,
        };
    };
})();
