(function () {
    "use strict";

    if (window.TarielClientePortalRuntime) return;

    window.TarielClientePortalRuntime = function createTarielClientePortalRuntime(config = {}) {
        const state = config.state || {};
        const documentRef = config.documentRef || document;
        const windowRef = config.windowRef || window;
        const getById = typeof config.getById === "function"
            ? config.getById
            : (id) => documentRef.getElementById(id);
        const fetchRef = typeof config.fetchRef === "function"
            ? config.fetchRef
            : (...args) => window.fetch(...args);
        const historyRef = config.historyRef || windowRef.history;
        const locationRef = config.locationRef || windowRef.location;
        const localStorageRef = config.localStorageRef || windowRef.localStorage;
        const perf = config.perf || null;
        const csrf = String(config.csrf || "");
        const storageKeys = config.storageKeys || {};
        const snapshotSelectors = {
            shell: ".cliente-shell",
            hero: ".cliente-hero",
            tabs: ".cliente-tabs",
            panelAdmin: "#panel-admin",
            panelChat: "#panel-chat",
            panelMesa: "#panel-mesa",
            listaUsuarios: "#lista-usuarios",
            listaChat: "#lista-chat-laudos",
            listaMesa: "#lista-mesa-laudos",
            mensagensChat: "#chat-mensagens",
            mensagensMesa: "#mesa-mensagens",
            ...(config.snapshotSelectors || {}),
        };

        function perfSync(name, runner, detail = {}, category = "function") {
            if (!perf?.measureSync) return runner();
            return perf.measureSync(name, runner, { category, detail });
        }

        async function perfAsync(name, runner, detail = {}, category = "function") {
            if (!perf?.measureAsync) return runner();
            return perf.measureAsync(name, runner, { category, detail });
        }

        function perfSnapshot(label) {
            if (!perf?.snapshotDOM) return;
            perf.snapshotDOM(label, snapshotSelectors);
        }

        function texto(valor) {
            if (valor == null) return "";
            return String(valor);
        }

        const routeMap = Object.freeze({
            admin: texto(config.routeMap?.admin).trim() || "/cliente/painel",
            chat: texto(config.routeMap?.chat).trim() || "/cliente/chat",
            mesa: texto(config.routeMap?.mesa).trim() || "/cliente/mesa",
        });
        const sectionDefinitions = Object.freeze({
            admin: Object.freeze({
                default: "overview",
                aliases: Object.freeze({
                    planos: "capacity",
                    equipe: "team",
                    governanca: "support",
                }),
                values: Object.freeze(["overview", "capacity", "team", "support"]),
            }),
            chat: Object.freeze({
                default: "overview",
                aliases: Object.freeze({}),
                values: Object.freeze(["overview", "new", "queue", "case"]),
            }),
            mesa: Object.freeze({
                default: "overview",
                aliases: Object.freeze({}),
                values: Object.freeze(["overview", "queue", "pending", "reply"]),
            }),
            ...(config.sectionDefinitions || {}),
        });
        const initialTab = (() => {
            const candidato = texto(config.initialTab).trim().toLowerCase();
            if (candidato === "admin" || candidato === "chat" || candidato === "mesa") {
                return candidato;
            }
            return "admin";
        })();

        function ehAbortError(erro) {
            return erro?.name === "AbortError" || erro?.code === windowRef.DOMException?.ABORT_ERR;
        }

        function escapeHtml(valor) {
            return texto(valor)
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;")
                .replaceAll("'", "&#39;");
        }

        function escapeAttr(valor) {
            return escapeHtml(valor);
        }

        function textoComQuebras(valor) {
            return escapeHtml(valor).replaceAll("\n", "<br>");
        }

        function formatarInteiro(valor) {
            const numero = Number(valor || 0);
            return Number.isFinite(numero) ? numero.toLocaleString("pt-BR") : "0";
        }

        function formatarPercentual(valor) {
            if (valor == null || valor === "") return "Ilimitado";
            const numero = Number(valor);
            return Number.isFinite(numero) ? `${numero}%` : "Ilimitado";
        }

        function formatarCapacidadeRestante(restante, excedente, singular, plural) {
            const sufixo = Number(restante) === 1 ? singular : plural;
            if (restante == null) return `Sem teto de ${plural}`;
            if (Number(excedente || 0) > 0) {
                const excesso = Number(excedente || 0);
                const sufixoExcesso = excesso === 1 ? singular : plural;
                return `${formatarInteiro(excesso)} ${sufixoExcesso} acima do plano`;
            }
            if (Number(restante) <= 0) return `No limite de ${plural}`;
            return `${formatarInteiro(restante)} ${sufixo} restantes`;
        }

        function formatarLimitePlano(valor, singular, plural) {
            if (valor == null || valor === "") return `Sem teto de ${plural}`;
            const numero = Number(valor);
            if (!Number.isFinite(numero)) return `Sem teto de ${plural}`;
            return `${formatarInteiro(numero)} ${numero === 1 ? singular : plural}`;
        }

        function formatarVariacao(valor) {
            const numero = Number(valor || 0);
            if (!Number.isFinite(numero)) return "0%";
            if (numero > 0) return `+${numero}%`;
            return `${numero}%`;
        }

        function formatarBytes(valor) {
            const numero = Number(valor || 0);
            if (!Number.isFinite(numero) || numero <= 0) return "0 B";
            const unidades = ["B", "KB", "MB", "GB"];
            let idx = 0;
            let atual = numero;
            while (atual >= 1024 && idx < unidades.length - 1) {
                atual /= 1024;
                idx += 1;
            }
            const casas = atual >= 10 || idx === 0 ? 0 : 1;
            return `${atual.toFixed(casas).replace(".", ",")} ${unidades[idx]}`;
        }

        function scrollToPortalSection(id) {
            const alvo = id ? getById(id) : null;
            if (!alvo) return;
            try {
                const tabsShell = documentRef.querySelector(".cliente-tabs-shell");
                const offset = (tabsShell?.offsetHeight || 0) + 12;
                const topoAlvo = windowRef.scrollY + alvo.getBoundingClientRect().top - offset;
                windowRef.scrollTo({ top: Math.max(topoAlvo, 0), behavior: "smooth" });
            } catch (_) {
                alvo.scrollIntoView();
            }
        }

        function feedback(mensagem, erro = false, titulo = "") {
            const box = getById("feedback");
            if (!box) return;

            box.innerHTML = `
                <strong class="feedback-title">${escapeHtml(titulo || (erro ? "Algo precisa de atencao" : "Atualizacao concluida"))}</strong>
                <div class="feedback-message">${escapeHtml(mensagem)}</div>
            `;
            box.dataset.kind = erro ? "error" : "success";
            box.dataset.visible = "true";

            if (state.ui?.feedbackTimer) {
                windowRef.clearTimeout(state.ui.feedbackTimer);
            }

            state.ui.feedbackTimer = windowRef.setTimeout(() => {
                box.dataset.visible = "false";
            }, erro ? 5200 : 3600);
        }

        async function api(url, options = {}) {
            return perfAsync(
                "cliente.api",
                async () => {
                    const opts = {
                        method: "GET",
                        cache: "no-store",
                        credentials: "same-origin",
                        ...options,
                        headers: {
                            "Accept": "application/json",
                            "X-CSRF-Token": csrf,
                            ...(options.headers || {}),
                        },
                    };

                    if (opts.body && !(opts.body instanceof FormData) && typeof opts.body !== "string") {
                        opts.headers["Content-Type"] = "application/json";
                        opts.body = JSON.stringify(opts.body);
                    }

                    const response = await fetchRef(url, opts);
                    const contentType = response.headers.get("content-type") || "";
                    const data = contentType.includes("application/json")
                        ? await response.json()
                        : await response.text();

                    if (!response.ok) {
                        const detail = typeof data === "string" ? data : data?.detail || JSON.stringify(data);
                        throw new Error(detail || "Falha na operacao.");
                    }

                    return data;
                },
                {
                    url: String(url || ""),
                    method: String(options?.method || "GET").toUpperCase(),
                },
                "state"
            );
        }

        async function withBusy(target, busyText, callback) {
            const button = target || null;
            const original = button ? button.textContent : "";

            if (button) {
                button.disabled = true;
                button.dataset.busy = "true";
                if (busyText) button.textContent = busyText;
            }

            try {
                return await callback();
            } finally {
                if (button) {
                    button.disabled = false;
                    button.dataset.busy = "false";
                    if (busyText) button.textContent = original;
                }
            }
        }

        function persistirTab(nome) {
            try {
                localStorageRef.setItem(storageKeys.tab || "tariel.cliente.tab", nome);
            } catch (_) {}
        }

        function _normalizarPath(valor) {
            const path = texto(valor).trim() || "/";
            if (path.length > 1 && path.endsWith("/")) {
                return path.replace(/\/+$/, "");
            }
            return path;
        }

        function obterSecaoPadrao(surface) {
            return sectionDefinitions[surface]?.default || "overview";
        }

        function normalizarSecao(surface, valor) {
            const secaoBruta = texto(valor).trim().toLowerCase();
            const definicao = sectionDefinitions[surface] || sectionDefinitions.admin;
            const secao = definicao.aliases?.[secaoBruta] || secaoBruta;
            if (definicao.values.includes(secao)) {
                return secao;
            }
            return definicao.default || "overview";
        }

        function registrarSecaoAtiva(surface, secao) {
            const surfaceAtiva = surface === "chat" || surface === "mesa" ? surface : "admin";
            const secaoAtiva = normalizarSecao(surfaceAtiva, secao);
            state.ui.sections = state.ui.sections || {};
            state.ui.sections[surfaceAtiva] = secaoAtiva;
            if (surfaceAtiva === "admin") {
                state.ui.adminSection = secaoAtiva;
            } else if (surfaceAtiva === "chat") {
                state.ui.chatSection = secaoAtiva;
            } else {
                state.ui.mesaSection = secaoAtiva;
            }
            return secaoAtiva;
        }

        function tabAtualDaUrl() {
            const atual = _normalizarPath(locationRef?.pathname || "");
            if (atual === _normalizarPath(routeMap.chat)) return "chat";
            if (atual === _normalizarPath(routeMap.mesa)) return "mesa";
            if (atual === _normalizarPath(routeMap.admin)) return "admin";
            return null;
        }

        function secaoAtualDaUrl(surface = tabAtualDaUrl() || state.ui?.tab || initialTab || "admin") {
            try {
                const params = new URLSearchParams(locationRef?.search || "");
                return normalizarSecao(surface, params.get("sec") || params.get("secao"));
            } catch (_) {
                return obterSecaoPadrao(surface);
            }
        }

        function _urlDaSurface(nome, secao) {
            const rota = routeMap[nome];
            if (!rota) return "";
            const url = new URL(rota, locationRef?.origin || windowRef.location.origin);
            url.searchParams.set("sec", normalizarSecao(nome, secao));
            const query = url.searchParams.toString();
            return `${url.pathname}${query ? `?${query}` : ""}`;
        }

        function sincronizarUrlDaTab(nome, { replace = false, section = null } = {}) {
            if (!historyRef || !locationRef || typeof historyRef.pushState !== "function") return;
            const destino = _urlDaSurface(nome, section || state.ui?.sections?.[nome] || obterSecaoPadrao(nome));
            if (!destino) return;

            const urlAtual = `${_normalizarPath(locationRef.pathname || "")}${locationRef.search || ""}`;
            if (urlAtual === destino) return;

            const metodo = replace ? "replaceState" : "pushState";
            if (typeof historyRef[metodo] !== "function") return;
            historyRef[metodo]({ clienteTab: nome, clienteSec: normalizarSecao(nome, section || state.ui?.sections?.[nome]) }, "", destino);
        }

        function sincronizarUrlDaSecao(surface, secao, { replace = false } = {}) {
            registrarSecaoAtiva(surface, secao);
            sincronizarUrlDaTab(surface, { replace, section: secao });
        }

        function persistirSelecao(chave, valor) {
            try {
                if (valor) {
                    localStorageRef.setItem(chave, String(valor));
                } else {
                    localStorageRef.removeItem(chave);
                }
            } catch (_) {}
        }

        function lerNumeroPersistido(chave) {
            try {
                const valor = Number(localStorageRef.getItem(chave) || 0);
                return Number.isFinite(valor) && valor > 0 ? valor : null;
            } catch (_) {
                return null;
            }
        }

        function restaurarTab() {
            const tabPorUrl = tabAtualDaUrl();
            if (tabPorUrl) {
                state.ui.tab = tabPorUrl;
                return;
            }

            if (initialTab) {
                state.ui.tab = initialTab;
                return;
            }

            try {
                const salvo = localStorageRef.getItem(storageKeys.tab || "tariel.cliente.tab");
                if (salvo === "admin" || salvo === "chat" || salvo === "mesa") {
                    state.ui.tab = salvo;
                }
            } catch (_) {}
        }

        function definirTab(nome, persistir = true, options = {}) {
            perfSync("cliente.definirTab", () => {
                const tab = nome === "chat" || nome === "mesa" ? nome : "admin";
                const secao = options.fromUrl
                    ? secaoAtualDaUrl(tab)
                    : normalizarSecao(tab, options.section || state.ui?.sections?.[tab] || obterSecaoPadrao(tab));
                state.ui.tab = tab;
                registrarSecaoAtiva(tab, secao);
                if (persistir) persistirTab(tab);
                if (options.syncUrl !== false) {
                    sincronizarUrlDaTab(tab, { replace: Boolean(options.replaceUrl), section: secao });
                }

                documentRef.querySelectorAll(".cliente-tab").forEach((button) => {
                    const ativa = button.dataset.tab === tab;
                    button.classList.toggle("active", ativa);
                    button.setAttribute("aria-selected", String(ativa));
                    button.setAttribute("aria-current", ativa ? "page" : "false");
                });

                documentRef.querySelectorAll(".panel").forEach((panel) => {
                    panel.classList.toggle("active", panel.id === `panel-${tab}`);
                });
                perfSnapshot(`cliente:tab:${tab}`);
            }, { tab: nome, persistir }, "transition");
        }

        function sincronizarTabComUrl({ replace = false } = {}) {
            const tab = tabAtualDaUrl() || initialTab || "admin";
            definirTab(tab, false, { fromUrl: true, syncUrl: false });
            if (replace) {
                sincronizarUrlDaTab(tab, { replace: true, section: secaoAtualDaUrl(tab) });
            }
            return tab;
        }

        return {
            api,
            definirTab,
            ehAbortError,
            escapeAttr,
            escapeHtml,
            feedback,
            formatarBytes,
            formatarCapacidadeRestante,
            formatarInteiro,
            formatarLimitePlano,
            formatarPercentual,
            formatarVariacao,
            lerNumeroPersistido,
            normalizarSecao,
            perfAsync,
            perfSnapshot,
            perfSync,
            persistirSelecao,
            persistirTab,
            registrarSecaoAtiva,
            restaurarTab,
            secaoAtualDaUrl,
            scrollToPortalSection,
            sincronizarTabComUrl,
            sincronizarUrlDaTab,
            sincronizarUrlDaSecao,
            tabAtualDaUrl,
            texto,
            textoComQuebras,
            withBusy,
        };
    };
})();
