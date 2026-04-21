// ==========================================
// TARIEL.IA — APP_SHELL.JS
// Shell global da aplicação.
// Responsável por:
// - ler config inicial do backend
// - expor config global imutável
// - status de rede
// - bloqueios por plano
// - restrição de upload por plano
// - toggle global da sidebar
// - service worker
// - toast global simples
// ==========================================

(function () {
    "use strict";

    // Evita bind duplicado se o script for carregado mais de uma vez.
    if (window.__TARIEL_APP_SHELL_WIRED__) return;
    window.__TARIEL_APP_SHELL_WIRED__ = true;

    const EM_DESENVOLVIMENTO_LOCAL =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1";
    const PREFIXO_CACHE_SW = "tariel-";
    const CHAVE_SW_RESET_LOCAL = "tariel_sw_local_reset";

    // =========================================================
    // CONFIGURAÇÃO INICIAL
    // =========================================================

    function normalizarListaTextual(valores) {
        if (!Array.isArray(valores)) return [];
        return valores
            .map((item) => String(item || "").trim())
            .filter(Boolean);
    }

    function normalizarMapaBooleano(valor) {
        if (!valor || typeof valor !== "object") return {};

        return Object.entries(valor).reduce((acc, [chave, enabled]) => {
            const chaveNormalizada = String(chave || "").trim();
            if (!chaveNormalizada) return acc;
            acc[chaveNormalizada] = !!enabled;
            return acc;
        }, {});
    }

    function normalizarTenantAccessPolicy(rawPolicy) {
        const policy = rawPolicy && typeof rawPolicy === "object" ? rawPolicy : {};
        const portalEntitlements = normalizarMapaBooleano(policy.portal_entitlements);
        const capabilityEntitlements = normalizarMapaBooleano(policy.capability_entitlements);
        const userCapabilityEntitlements = normalizarMapaBooleano(policy.user_capability_entitlements);
        const allowedPortals = normalizarListaTextual(policy.allowed_portals);
        const allowedPortalLabels = normalizarListaTextual(policy.allowed_portal_labels);

        return {
            raw: {
                ...policy,
                portal_entitlements: portalEntitlements,
                capability_entitlements: capabilityEntitlements,
                user_capability_entitlements: userCapabilityEntitlements,
                allowed_portals: allowedPortals,
                allowed_portal_labels: allowedPortalLabels,
            },
            portalEntitlements,
            capabilityEntitlements,
            userCapabilityEntitlements,
            allowedPortals,
            allowedPortalLabels,
            governedByAdminCeo: !!policy.governed_by_admin_ceo,
        };
    }

    function tenantPolicyCapabilityEnabled(policy, capability, fallback = true) {
        const chave = String(capability || "").trim();
        if (!chave) return !!fallback;

        if (Object.prototype.hasOwnProperty.call(policy.userCapabilityEntitlements, chave)) {
            return !!policy.userCapabilityEntitlements[chave];
        }

        if (Object.prototype.hasOwnProperty.call(policy.capabilityEntitlements, chave)) {
            return !!policy.capabilityEntitlements[chave];
        }

        return !!fallback;
    }

    function tenantPolicyPortalEnabled(policy, portal, fallback = true) {
        const chave = String(portal || "").trim();
        if (!chave) return !!fallback;

        if (Object.prototype.hasOwnProperty.call(policy.portalEntitlements, chave)) {
            return !!policy.portalEntitlements[chave];
        }

        if (policy.allowedPortals.length) {
            return policy.allowedPortals.includes(chave);
        }

        return !!fallback;
    }

    function lerConfigInicial() {
        const cfgEl = document.getElementById("tariel-boot");

        if (!cfgEl) return {};

        try {
            return JSON.parse(cfgEl.textContent || "{}");
        } catch (_) {
            return {};
        }
    }

    function exporConfigGlobal(cfg) {
        const tenantAccessPolicy = normalizarTenantAccessPolicy(cfg.tenantAccessPolicy);

        window.TARIEL = Object.freeze({
            csrfToken: cfg.csrfToken ?? "",
            usuario: cfg.usuarioNome ?? "Usuário",
            empresa: cfg.empresaNome ?? "",
            laudosMesUsados: cfg.laudosMesUsados ?? 0,
            laudosMesLimite: cfg.laudosMesLimite ?? null,
            planoUploadDoc: cfg.planoUploadDoc ?? true,
            deep_research_disponivel: cfg.deepResearchDisponivel ?? false,
            estadoRelatorio: cfg.estadoRelatorio ?? "sem_relatorio",
            laudoAtivoId: cfg.laudoAtivoId ?? null,
            suporteWhatsapp: cfg.suporteWhatsapp ?? "5516999999999",
            ambiente: cfg.ambiente ?? "producao",
            governedByAdminCeo: tenantAccessPolicy.governedByAdminCeo,
            tenantAccessPolicy: Object.freeze({ ...tenantAccessPolicy.raw }),
            allowedPortals: Object.freeze([...tenantAccessPolicy.allowedPortals]),
            allowedPortalLabels: Object.freeze([...tenantAccessPolicy.allowedPortalLabels]),
            portalEntitlements: Object.freeze({ ...tenantAccessPolicy.portalEntitlements }),
            capabilityEntitlements: Object.freeze({ ...tenantAccessPolicy.capabilityEntitlements }),
            userCapabilityEntitlements: Object.freeze({ ...tenantAccessPolicy.userCapabilityEntitlements }),
            hasPortalAccess(portal, fallback = true) {
                return tenantPolicyPortalEnabled(tenantAccessPolicy, portal, fallback);
            },
            hasUserCapability(capability, fallback = true) {
                return tenantPolicyCapabilityEnabled(tenantAccessPolicy, capability, fallback);
            }
        });
    }

    function registrarCompatibilidadeLegada() {
        try {
            const aside = document.getElementById("barra-historico");

            if (aside && !("_sidebarEl" in document)) {
                Object.defineProperty(document, "_sidebarEl", {
                    value: aside,
                    writable: false,
                    configurable: true
                });
            }
        } catch (_) {
            // Silencioso por compatibilidade
        }
    }

    // =========================================================
    // TOAST GLOBAL
    // =========================================================

    function instalarToastGlobal() {
        window.mostrarToast = function (mensagem, tipo = "info", duracao = 3500) {
            const cores = {
                info: { bg: "#0F2B46", border: "rgba(244,123,32,.5)" },
                sucesso: { bg: "#1F7A3E", border: "rgba(74,222,128,.5)" },
                erro: { bg: "#7F1D1D", border: "rgba(248,113,113,.5)" },
                aviso: { bg: "#5A3A00", border: "rgba(255,202,40,.45)" }
            };

            const cor = cores[tipo] ?? cores.info;
            const el = document.createElement("div");

            el.className = "toast-runtime";
            el.setAttribute("role", "status");
            el.setAttribute("aria-live", "polite");
            el.style.background = cor.bg;
            el.style.border = `1px solid ${cor.border}`;
            el.textContent = String(mensagem || "");

            document.body.appendChild(el);

            requestAnimationFrame(() => {
                el.style.opacity = "1";
                el.style.transform = "translateX(-50%) translateY(0)";
            });

            window.setTimeout(() => {
                el.style.opacity = "0";
                el.style.transform = "translateX(-50%) translateY(8px)";
                el.addEventListener("transitionend", () => el.remove(), { once: true });
            }, duracao);
        };
    }

    // =========================================================
    // STATUS DE REDE
    // =========================================================

    function wireStatusRede() {
        const barraRede = document.getElementById("barra-status-rede");
        const textoStatusRede = document.getElementById("texto-status-rede");

        if (!barraRede || !textoStatusRede) return;

        let timerRede = null;

        function limparTimerRede() {
            if (!timerRede) return;
            clearTimeout(timerRede);
            timerRede = null;
        }

        function mostrarStatusRede({ online }) {
            limparTimerRede();

            barraRede.classList.add("visivel");
            barraRede.classList.toggle("online", !!online);
            barraRede.classList.toggle("offline", !online);

            textoStatusRede.textContent = online
                ? "Conexão restaurada"
                : "Sem conexão com a internet — verifique o Wi-Fi";

            if (online) {
                timerRede = window.setTimeout(() => {
                    barraRede.classList.remove("visivel", "online");
                }, 2500);
            }
        }

        if (!navigator.onLine) {
            mostrarStatusRede({ online: false });
        }

        window.addEventListener("online", () => mostrarStatusRede({ online: true }));
        window.addEventListener("offline", () => mostrarStatusRede({ online: false }));
    }

    // =========================================================
    // BLOQUEIOS POR PLANO
    // =========================================================

    function aplicarBloqueioPorLimiteDePlano() {
        if (
            window.TARIEL.laudosMesLimite === null ||
            window.TARIEL.laudosMesUsados < window.TARIEL.laudosMesLimite
        ) {
            return;
        }

        const campoMensagem = document.getElementById("campo-mensagem");
        const btnEnviar = document.getElementById("btn-enviar");

        if (campoMensagem) {
            campoMensagem.disabled = true;
            campoMensagem.placeholder = "Limite atingido. Faça upgrade em /app/planos.";
        }

        if (btnEnviar) {
            btnEnviar.disabled = true;
        }
    }

    function aplicarRestricaoUploadPorPlano() {
        if (window.TARIEL.planoUploadDoc) return;

        const inputAnexo = document.getElementById("input-anexo");
        const btnAnexo = document.getElementById("btn-anexo");

        if (inputAnexo) {
            inputAnexo.accept = "image/png,image/jpeg,image/jpg,image/webp";
            inputAnexo.dataset.apenasImagens = "true";
        }

        if (btnAnexo && !btnAnexo.querySelector("[data-badge-plano]")) {
            btnAnexo.title = "Apenas imagens permitidas (PDF requer plano superior)";

            const badge = document.createElement("span");
            badge.dataset.badgePlano = "pdf-bloqueado";
            badge.className = "badge-plano-bloqueado";
            badge.textContent = "PDF";
            badge.title = "Indisponível no plano atual";

            btnAnexo.appendChild(badge);
        }
    }

    // =========================================================
    // SIDEBAR GLOBAL
    // =========================================================

    function wireToggleSidebarGlobal() {
        const btnToggle = document.getElementById("btn-toggle-ui");
        const btnMenu = document.getElementById("btn-menu");
        const sidebar = document.getElementById("barra-historico");
        const overlay = document.getElementById("overlay-sidebar");

        if (!sidebar) return;

        // A página principal do chat possui um módulo dedicado (ui.js) para
        // menu lateral + modo foco. Evitamos competir por eventos/estado aqui.
        if (document.getElementById("painel-chat")) {
            const mobile = window.matchMedia("(max-width: 768px)").matches;
            sidebar.classList.remove("aberta", "aberto");
            document.body.classList.remove("sidebar-aberta");
            document.body.classList.remove("sidebar-colapsada");
            overlay?.classList.remove("ativo");

            sidebar.setAttribute("aria-hidden", mobile ? "true" : "false");
            overlay?.setAttribute("aria-hidden", "true");
            btnMenu?.setAttribute("aria-expanded", "false");
            btnToggle?.setAttribute("aria-expanded", "false");
            return;
        }

        const iconToggle = btnToggle?.querySelector(".material-symbols-rounded");
        const emMobile = () => window.matchMedia("(max-width: 768px)").matches;

        function atualizarEstadoSidebar(aberta) {
            const mobile = emMobile();

            if (mobile) {
                document.body.classList.remove("sidebar-colapsada");
                sidebar.classList.toggle("aberta", aberta);
                sidebar.classList.toggle("aberto", aberta);
                sidebar.classList.remove("oculta");
                overlay?.classList.toggle("ativo", aberta);
                document.body.classList.toggle("sidebar-aberta", aberta);
            } else {
                document.body.classList.toggle("sidebar-colapsada", !aberta);
                sidebar.classList.remove("aberta", "aberto");
                sidebar.classList.toggle("oculta", !aberta);
                overlay?.classList.remove("ativo");
                document.body.classList.remove("sidebar-aberta");
            }

            btnToggle?.setAttribute("aria-expanded", String(aberta));
            btnMenu?.setAttribute("aria-expanded", String(aberta));

            if (iconToggle) {
                iconToggle.textContent = aberta ? "menu_open" : "menu";
            }

            overlay?.setAttribute("aria-hidden", String(!(mobile && aberta)));

            sidebar.setAttribute("aria-hidden", String(!aberta));
        }

        function alternarSidebar() {
            const abertaAtual = emMobile()
                ? sidebar.classList.contains("aberta")
                : !sidebar.classList.contains("oculta");
            const aberta = !abertaAtual;
            atualizarEstadoSidebar(aberta);
        }

        btnToggle?.addEventListener("click", alternarSidebar);
        btnMenu?.addEventListener("click", alternarSidebar);

        overlay?.addEventListener("click", () => {
            atualizarEstadoSidebar(false);
            btnToggle?.focus();
        });

        document.addEventListener("keydown", (event) => {
            const estaAberta = emMobile()
                ? sidebar.classList.contains("aberta")
                : !sidebar.classList.contains("oculta");

            if (event.key === "Escape" && estaAberta) {
                atualizarEstadoSidebar(false);
                btnToggle?.focus();
            }
        });

        atualizarEstadoSidebar(emMobile() ? false : !sidebar.classList.contains("oculta"));
    }

    // =========================================================
    // SERVICE WORKER
    // =========================================================

    function serviceWorkerEhTarielApp(scopeOuScript = "") {
        const valor = String(scopeOuScript || "");
        return valor.includes("/app/") || valor.includes("/app/trabalhador_servico.js");
    }

    function obterScriptURLServiceWorker(registro = null) {
        return String(
            registro?.active?.scriptURL ||
            registro?.waiting?.scriptURL ||
            registro?.installing?.scriptURL ||
            ""
        );
    }

    function controladorTarielAtivo() {
        return serviceWorkerEhTarielApp(navigator.serviceWorker?.controller?.scriptURL || "");
    }

    function lerFlagResetSWLocal() {
        try {
            return sessionStorage.getItem(CHAVE_SW_RESET_LOCAL) === "1";
        } catch (_) {
            return false;
        }
    }

    function gravarFlagResetSWLocal(ativo) {
        try {
            if (ativo) {
                sessionStorage.setItem(CHAVE_SW_RESET_LOCAL, "1");
            } else {
                sessionStorage.removeItem(CHAVE_SW_RESET_LOCAL);
            }
        } catch (_) {}
    }

    async function limparCachesTarielSW() {
        if (!("caches" in window)) return 0;

        try {
            const nomes = await caches.keys();
            const alvo = nomes.filter((nome) => String(nome || "").startsWith(PREFIXO_CACHE_SW));
            await Promise.all(alvo.map((nome) => caches.delete(nome)));
            return alvo.length;
        } catch (_) {
            return 0;
        }
    }

    async function desativarServiceWorkerEmLocalhost() {
        window.__TARIEL_SW_DISABLED_IN_DEV__ = true;

        let registrosTariel = [];

        try {
            const registros = await navigator.serviceWorker.getRegistrations();
            registrosTariel = registros.filter((registro) => (
                serviceWorkerEhTarielApp(registro.scope) ||
                serviceWorkerEhTarielApp(obterScriptURLServiceWorker(registro))
            ));

            await Promise.all(registrosTariel.map((registro) => registro.unregister().catch(() => false)));
        } catch (_) {}

        await limparCachesTarielSW();

        const resetJaExecutado = lerFlagResetSWLocal();
        if ((controladorTarielAtivo() || registrosTariel.length > 0) && !resetJaExecutado) {
            gravarFlagResetSWLocal(true);
            window.location.reload();
            return true;
        }

        gravarFlagResetSWLocal(false);
        return false;
    }

    function wireServiceWorker() {
        if (!("serviceWorker" in navigator)) return;

        if (EM_DESENVOLVIMENTO_LOCAL) {
            void desativarServiceWorkerEmLocalhost();
            return;
        }

        const toastSW = document.getElementById("toast-sw");
        const btnAtualizarSW = document.getElementById("btn-atualizar-sw");
        const btnFecharSW = document.getElementById("btn-fechar-sw");

        let swRegistrado = null;
        let recarregandoPorSW = false;

        function mostrarToastSW() {
            toastSW?.classList.add("visivel");
        }

        function ocultarToastSW() {
            toastSW?.classList.remove("visivel");
        }

        window.addEventListener("load", async () => {
            try {
                const reg = await navigator.serviceWorker.register(
                    "/app/trabalhador_servico.js",
                    { scope: "/app/" }
                );

                swRegistrado = reg;

                reg.addEventListener("updatefound", () => {
                    const novoSW = reg.installing;
                    if (!novoSW) return;

                    novoSW.addEventListener("statechange", () => {
                        if (
                            novoSW.state === "installed" &&
                            navigator.serviceWorker.controller
                        ) {
                            mostrarToastSW();
                        }
                    });
                });

                document.addEventListener("visibilitychange", () => {
                    if (document.visibilityState === "visible") {
                        reg.update().catch(() => {});
                    }
                });
            } catch (_) {
                console.warn("[Tariel] Service Worker indisponível — app continua funcionando.");
            }
        });

        btnAtualizarSW?.addEventListener("click", () => {
            const waiting = swRegistrado?.waiting;
            if (!waiting) return;

            waiting.postMessage({ type: "SKIP_WAITING" });

            navigator.serviceWorker.addEventListener("controllerchange", () => {
                if (recarregandoPorSW) return;
                recarregandoPorSW = true;
                window.location.reload();
            }, { once: true });
        });

        btnFecharSW?.addEventListener("click", ocultarToastSW);
    }

    // =========================================================
    // BOOT
    // =========================================================

    function boot() {
        const cfg = lerConfigInicial();

        exporConfigGlobal(cfg);
        registrarCompatibilidadeLegada();
        instalarToastGlobal();
        wireStatusRede();
        aplicarBloqueioPorLimiteDePlano();
        aplicarRestricaoUploadPorPlano();
        wireToggleSidebarGlobal();
        wireServiceWorker();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
