// ==========================================
// TARIEL CONTROL TOWER — API-CORE.JS
// Base compartilhada: logs, CSRF, escape, toast,
// validações simples e utilitários de ambiente.
// ==========================================

(function () {
    "use strict";

    if (window.TarielCore) return;

    const EM_PRODUCAO =
        window.location.hostname !== "localhost" &&
        window.location.hostname !== "127.0.0.1";

    function lerConfigBoot() {
        try {
            if (window.TARIEL && typeof window.TARIEL === "object") {
                return window.TARIEL;
            }
        } catch (_) {}

        try {
            const cfgEl = document.getElementById("tariel-boot");
            if (!cfgEl) return {};
            return JSON.parse(cfgEl.textContent || "{}");
        } catch (_) {
            return {};
        }
    }

    function perfPermitidoPeloBackend() {
        try {
            if (window.__TARIEL_DISABLE_PERF__ === true) {
                return false;
            }
        } catch (_) {}

        try {
            const metaModoPerf = document.querySelector('meta[name="tariel-perf-mode"]');
            if (metaModoPerf) {
                return String(metaModoPerf.content || "").trim() === "1";
            }
        } catch (_) {}

        const cfg = lerConfigBoot();
        return Boolean(cfg?.perfMode);
    }

    function resolverPerfAtivo() {
        if (!perfPermitidoPeloBackend()) {
            return false;
        }

        let viaQuery = false;
        let viaStorage = false;

        try {
            viaQuery = new URL(window.location.href).searchParams.get("perf") === "1";
        } catch (_) {}

        try {
            if (viaQuery) {
                localStorage.setItem("tarielPerf", "1");
            }
            viaStorage = localStorage.getItem("tarielPerf") === "1";
        } catch (_) {}

        return viaQuery || viaStorage;
    }

    function resolverDebugAtivo() {
        if (EM_PRODUCAO) {
            return false;
        }

        try {
            if (window.__TARIEL_DEBUG__ === true) {
                return true;
            }
        } catch (_) {}

        let viaQuery = false;
        let viaStorage = false;

        try {
            viaQuery = new URL(window.location.href).searchParams.get("debug") === "1";
        } catch (_) {}

        try {
            if (viaQuery) {
                localStorage.setItem("tarielDebug", "1");
            }
            viaStorage = localStorage.getItem("tarielDebug") === "1";
        } catch (_) {}

        return viaQuery || viaStorage;
    }

    const PERF_ATIVO = resolverPerfAtivo();
    const DEBUG_ATIVO = resolverDebugAtivo();
    const LOGS_UNICOS = new Set();

    function criarTarielPerf() {
        if (window.TarielPerf) return window.TarielPerf;

        if (!PERF_ATIVO) {
            const noopPerf = {
                enabled: false,
                mark: () => null,
                markOnce: () => false,
                start: () => null,
                end: () => 0,
                begin: () => null,
                finish: () => 0,
                count: () => 0,
                noteModule: () => null,
                snapshotDOM: () => null,
                measureSync: (_name, runner) => (typeof runner === "function" ? runner() : undefined),
                measureAsync: async (_name, runner) => (typeof runner === "function" ? runner() : undefined),
                getReport: () => ({ enabled: false }),
                clear: () => null,
                printSummary: () => ({ enabled: false }),
                topFunctions: () => [],
                topNetwork: () => [],
                topLongTasks: () => [],
                fetchBackendSummary: async () => ({ enabled: false, ok: false, reason: "perf_disabled" }),
                fetchBackendReport: async () => ({ enabled: false, ok: false, reason: "perf_disabled" }),
                resetBackendSummary: async () => ({ enabled: false, ok: false, reason: "perf_disabled" }),
            };
            window.TarielPerf = noopPerf;
            return noopPerf;
        }

        const LIMITE_PADRAO = 300;
        const LIMITE_RECURSOS = 500;
        const LIMITE_AMOSTRAS = 1200;
        const defaultDomRegions = Object.freeze({
            sidebar: "#barra-historico, #sidebar",
            portal: '[data-screen-root="portal"]',
            workspace: '[data-screen-root="workspace"]',
            areaMensagens: "#area-mensagens",
            railDireito: ".chat-dashboard-rail",
            modalNovaInspecao: "#modal-nova-inspecao",
            listaLaudos: "#lista-historico",
            listaPendencias: "#lista-pendencias-mesa, #painel-pendencias-mesa",
        });

        const state = {
            sessionId: `perf-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
            startedAt: typeof performance?.now === "function" ? performance.now() : Date.now(),
            enabled: true,
            seq: 0,
            marks: [],
            modules: [],
            samples: [],
            network: [],
            resources: [],
            paints: [],
            largestContentfulPaint: [],
            layoutShifts: [],
            longTasks: [],
            domSnapshots: [],
            navigation: {},
            pending: new Map(),
            once: new Set(),
            counters: new Map(),
            aggregates: new Map(),
            listeners: {
                total: 0,
                duplicates: 0,
                byType: new Map(),
                recent: [],
            },
            observers: {
                total: 0,
                callbacks: 0,
                byLabel: new Map(),
                recent: [],
            },
            storage: {
                writes: [],
                totals: new Map(),
            },
        };

        const targetIds = new WeakMap();
        const listenerIds = new WeakMap();
        const responseMeta = new WeakMap();
        let targetSeq = 0;
        let listenerSeq = 0;

        function now() {
            return typeof performance?.now === "function" ? performance.now() : Date.now();
        }

        function limitarArray(lista, item, limite = LIMITE_PADRAO) {
            if (!Array.isArray(lista)) return;
            lista.push(item);
            if (lista.length > limite) {
                lista.splice(0, lista.length - limite);
            }
        }

        function arredondar(valor) {
            const numero = Number(valor);
            return Number.isFinite(numero) ? Number(numero.toFixed(3)) : null;
        }

        function normalizarDetail(detail = {}) {
            if (!detail || typeof detail !== "object") return {};
            return { ...detail };
        }

        function aggregate(category, name, durationMs = 0, extra = {}) {
            const key = `${category}:${name}`;
            const atual = state.aggregates.get(key) || {
                category,
                name,
                count: 0,
                totalMs: 0,
                avgMs: 0,
                maxMs: 0,
                minMs: null,
                lastMs: 0,
                lastDetail: null,
                failures: 0,
            };

            const duration = Math.max(0, Number(durationMs) || 0);
            atual.count += 1;
            atual.totalMs += duration;
            atual.avgMs = atual.totalMs / atual.count;
            atual.maxMs = Math.max(atual.maxMs, duration);
            atual.minMs = atual.minMs == null ? duration : Math.min(atual.minMs, duration);
            atual.lastMs = duration;
            atual.lastDetail = normalizarDetail(extra);
            if (extra?.failed) {
                atual.failures += 1;
            }

            state.aggregates.set(key, atual);
            return atual;
        }

        function describeNode(target) {
            if (target === window) return "window";
            if (target === document) return "document";
            if (target === document.body) return "body";
            if (!(target instanceof Element)) {
                return target?.constructor?.name || typeof target;
            }

            const tag = String(target.tagName || "").toLowerCase();
            const id = target.id ? `#${target.id}` : "";
            const classes = String(target.className || "")
                .trim()
                .split(/\s+/)
                .filter(Boolean)
                .slice(0, 2)
                .map((classe) => `.${classe}`)
                .join("");

            return `${tag}${id}${classes}`;
        }

        function getTargetId(target) {
            if (!target || (typeof target !== "object" && typeof target !== "function")) {
                return "primitive";
            }
            if (!targetIds.has(target)) {
                targetSeq += 1;
                targetIds.set(target, `t${targetSeq}`);
            }
            return targetIds.get(target);
        }

        function getListenerId(listener) {
            if (!listener || (typeof listener !== "function" && typeof listener !== "object")) {
                return "none";
            }
            if (!listenerIds.has(listener)) {
                listenerSeq += 1;
                listenerIds.set(listener, `l${listenerSeq}`);
            }
            return listenerIds.get(listener);
        }

        function estimateBodyBytes(body) {
            if (body == null) return null;
            if (typeof body === "string") return body.length;
            if (body instanceof Blob) return body.size;
            if (body instanceof ArrayBuffer) return body.byteLength;
            if (ArrayBuffer.isView(body)) return body.byteLength;
            if (body instanceof URLSearchParams) return String(body).length;
            return null;
        }

        function safePerformanceMark(name) {
            try {
                performance.mark(name);
            } catch (_) {}
        }

        function mark(name, detail = {}) {
            const entry = {
                name: String(name || "mark"),
                atMs: arredondar(now()),
                detail: normalizarDetail(detail),
            };
            limitarArray(state.marks, entry, LIMITE_AMOSTRAS);
            safePerformanceMark(`tariel:${entry.name}`);
            return entry;
        }

        function markOnce(name, detail = {}) {
            const key = String(name || "mark");
            if (state.once.has(key)) return false;
            state.once.add(key);
            mark(key, detail);
            return true;
        }

        function start(name, { category = "function", detail = {} } = {}) {
            return {
                id: `${String(name || category)}#${++state.seq}`,
                name: String(name || "sample"),
                category: String(category || "function"),
                detail: normalizarDetail(detail),
                startedAt: now(),
                ended: false,
            };
        }

        function end(token, extra = {}) {
            if (!token || token.ended) return 0;
            token.ended = true;

            const durationMs = Math.max(0, now() - token.startedAt);
            const sample = {
                id: token.id,
                category: token.category,
                name: token.name,
                durationMs: arredondar(durationMs),
                startedAt: arredondar(token.startedAt),
                detail: {
                    ...token.detail,
                    ...normalizarDetail(extra),
                },
            };

            limitarArray(state.samples, sample, LIMITE_AMOSTRAS);
            aggregate(token.category, token.name, durationMs, sample.detail);

            if (token.category === "network") {
                limitarArray(state.network, sample, LIMITE_AMOSTRAS);
            }

            return durationMs;
        }

        function measureSync(name, runner, { category = "function", detail = {} } = {}) {
            const token = start(name, { category, detail });
            try {
                return runner();
            } catch (error) {
                end(token, {
                    failed: true,
                    error: String(error?.message || error || "erro"),
                });
                throw error;
            } finally {
                end(token);
            }
        }

        async function measureAsync(name, runner, { category = "function", detail = {} } = {}) {
            const token = start(name, { category, detail });
            try {
                const resultado = await runner();
                end(token);
                return resultado;
            } catch (error) {
                end(token, {
                    failed: true,
                    error: String(error?.message || error || "erro"),
                });
                throw error;
            }
        }

        function begin(name, detail = {}) {
            const chave = String(name || "transition");
            const token = start(chave, {
                category: "transition",
                detail,
            });
            state.pending.set(chave, token);
            mark(`${chave}:begin`, detail);
            return token;
        }

        function finish(name, extra = {}) {
            const chave = String(name || "transition");
            const token = state.pending.get(chave);
            if (!token) return 0;

            state.pending.delete(chave);
            mark(`${chave}:end`, extra);
            return end(token, extra);
        }

        function count(name, delta = 1, { category = "counter", detail = {} } = {}) {
            const chave = `${category}:${String(name || "counter")}`;
            const valorAtual = Number(state.counters.get(chave) || 0);
            const proximo = valorAtual + Number(delta || 0);
            state.counters.set(chave, proximo);
            aggregate(category, String(name || "counter"), 0, {
                ...normalizarDetail(detail),
                value: proximo,
            });
            return proximo;
        }

        function noteModule(name, detail = {}) {
            const entry = {
                name: String(name || "module"),
                atMs: arredondar(now()),
                detail: normalizarDetail(detail),
            };
            limitarArray(state.modules, entry, LIMITE_PADRAO);
            return entry;
        }

        function firstElement(selector) {
            if (!selector) return null;
            try {
                return document.querySelector(selector);
            } catch (_) {
                return null;
            }
        }

        function countNodes(root) {
            if (!(root instanceof Element)) return 0;
            return 1 + root.querySelectorAll("*").length;
        }

        function snapshotDOM(label = "snapshot", regions = defaultDomRegions) {
            const snapshot = {
                label: String(label || "snapshot"),
                atMs: arredondar(now()),
                regions: {},
            };

            Object.entries(regions || defaultDomRegions).forEach(([nome, selector]) => {
                const root = firstElement(selector);
                snapshot.regions[nome] = {
                    selector,
                    present: !!root,
                    visible: !!(
                        root &&
                        !root.hidden &&
                        !root.closest?.("[hidden], [inert]") &&
                        root.getClientRects().length > 0
                    ),
                    nodeCount: countNodes(root),
                    childElementCount: root?.childElementCount ?? 0,
                    scrollHeight: root?.scrollHeight ?? 0,
                    clientHeight: root?.clientHeight ?? 0,
                    scrollWidth: root?.scrollWidth ?? 0,
                    clientWidth: root?.clientWidth ?? 0,
                };
            });

            limitarArray(state.domSnapshots, snapshot, LIMITE_PADRAO);
            return snapshot;
        }

        function topByCategory(category, limit = 10) {
            return Array.from(state.aggregates.values())
                .filter((item) => item.category === category)
                .sort((a, b) => b.totalMs - a.totalMs)
                .slice(0, Math.max(1, Number(limit) || 10))
                .map((item) => ({
                    ...item,
                    totalMs: arredondar(item.totalMs),
                    avgMs: arredondar(item.avgMs),
                    maxMs: arredondar(item.maxMs),
                    minMs: arredondar(item.minMs),
                    lastMs: arredondar(item.lastMs),
                }));
        }

        function getReport() {
            return {
                enabled: true,
                sessionId: state.sessionId,
                url: window.location.href,
                generatedAt: new Date().toISOString(),
                navigation: { ...state.navigation },
                modules: [...state.modules],
                marks: [...state.marks],
                samples: [...state.samples],
                functions: topByCategory("function", 200),
                stateSync: topByCategory("state", 200),
                renders: topByCategory("render", 200),
                transitions: topByCategory("transition", 200),
                boot: topByCategory("boot", 200),
                network: [...state.network],
                resources: [...state.resources],
                paints: [...state.paints],
                largestContentfulPaint: [...state.largestContentfulPaint],
                layoutShifts: [...state.layoutShifts],
                longTasks: [...state.longTasks],
                domSnapshots: [...state.domSnapshots],
                listeners: {
                    total: state.listeners.total,
                    duplicates: state.listeners.duplicates,
                    byType: Array.from(state.listeners.byType.entries()).map(([type, total]) => ({
                        type,
                        total,
                    })),
                    recent: [...state.listeners.recent],
                },
                observers: {
                    total: state.observers.total,
                    callbacks: state.observers.callbacks,
                    byLabel: Array.from(state.observers.byLabel.entries()).map(([label, total]) => ({
                        label,
                        total,
                    })),
                    recent: [...state.observers.recent],
                },
                storage: {
                    totals: Array.from(state.storage.totals.entries()).map(([key, total]) => ({
                        key,
                        total,
                    })),
                    writes: [...state.storage.writes],
                },
                counters: Array.from(state.counters.entries()).map(([key, value]) => ({ key, value })),
            };
        }

        function topFunctions(limit = 12) {
            return [
                ...topByCategory("function", limit),
                ...topByCategory("state", limit),
                ...topByCategory("render", limit),
                ...topByCategory("boot", limit),
            ]
                .sort((a, b) => b.totalMs - a.totalMs)
                .slice(0, Math.max(1, Number(limit) || 12));
        }

        function topNetwork(limit = 12) {
            return [...state.network]
                .sort((a, b) => (b.durationMs || 0) - (a.durationMs || 0))
                .slice(0, Math.max(1, Number(limit) || 12));
        }

        function topLongTasks(limit = 12) {
            return [...state.longTasks]
                .sort((a, b) => (b.durationMs || 0) - (a.durationMs || 0))
                .slice(0, Math.max(1, Number(limit) || 12));
        }

        function clear() {
            state.marks.length = 0;
            state.modules.length = 0;
            state.samples.length = 0;
            state.network.length = 0;
            state.resources.length = 0;
            state.paints.length = 0;
            state.largestContentfulPaint.length = 0;
            state.layoutShifts.length = 0;
            state.longTasks.length = 0;
            state.domSnapshots.length = 0;
            state.pending.clear();
            state.once.clear();
            state.counters.clear();
            state.aggregates.clear();
            state.listeners.byType.clear();
            state.listeners.recent.length = 0;
            state.listeners.total = 0;
            state.listeners.duplicates = 0;
            state.observers.byLabel.clear();
            state.observers.recent.length = 0;
            state.observers.total = 0;
            state.observers.callbacks = 0;
            state.storage.totals.clear();
            state.storage.writes.length = 0;
        }

        async function fetchBackendPerf(url, init = {}) {
            try {
                const response = await fetch(url, {
                    credentials: "same-origin",
                    headers: {
                        Accept: "application/json",
                        ...(init.headers || {}),
                    },
                    ...init,
                });
                const text = await response.text();
                let data = null;

                try {
                    data = text ? JSON.parse(text) : {};
                } catch (_) {
                    data = { raw: text };
                }

                if (!response.ok) {
                    return {
                        ok: false,
                        status: response.status,
                        data,
                    };
                }

                return {
                    ok: true,
                    status: response.status,
                    data,
                };
            } catch (error) {
                return {
                    ok: false,
                    error: error?.message || String(error || "Erro ao consultar backend"),
                };
            }
        }

        async function fetchBackendSummary() {
            return fetchBackendPerf("/debug-perf/summary");
        }

        async function fetchBackendReport() {
            return fetchBackendPerf("/debug-perf/report");
        }

        async function resetBackendSummary() {
            return fetchBackendPerf("/debug-perf/reset", {
                method: "POST",
            });
        }

        function printSummary() {
            const summary = {
                navigation: state.navigation,
                topFunctions: topFunctions(),
                topNetwork: topNetwork(),
                topLongTasks: topLongTasks(),
                listenerDuplicates: state.listeners.duplicates,
                observerCallbacks: state.observers.callbacks,
                domSnapshots: state.domSnapshots.slice(-3),
            };

            try {
                console.groupCollapsed("[TarielPerf] Summary");
                console.log(summary.navigation);
                if (summary.topFunctions.length) console.table(summary.topFunctions);
                if (summary.topNetwork.length) console.table(summary.topNetwork);
                if (summary.topLongTasks.length) console.table(summary.topLongTasks);
                console.log("listenerDuplicates:", summary.listenerDuplicates);
                console.log("observerCallbacks:", summary.observerCallbacks);
                console.log("domSnapshots:", summary.domSnapshots);
                console.groupEnd();
            } catch (_) {}

            return summary;
        }

        function captureNavigation() {
            try {
                const navigation = performance.getEntriesByType("navigation")[0];
                if (!navigation) return;
                state.navigation = {
                    type: navigation.type,
                    domContentLoadedMs: arredondar(navigation.domContentLoadedEventEnd),
                    loadMs: arredondar(navigation.loadEventEnd),
                    responseStartMs: arredondar(navigation.responseStart),
                    responseEndMs: arredondar(navigation.responseEnd),
                    transferSize: navigation.transferSize || 0,
                    encodedBodySize: navigation.encodedBodySize || 0,
                    decodedBodySize: navigation.decodedBodySize || 0,
                };
            } catch (_) {}
        }

        function patchPerformanceObserver() {
            if (typeof PerformanceObserver !== "function") return;

            const observers = [
                ["longtask", (entry) => {
                    limitarArray(state.longTasks, {
                        name: entry.name || "longtask",
                        durationMs: arredondar(entry.duration),
                        startTimeMs: arredondar(entry.startTime),
                    }, LIMITE_PADRAO);
                }],
                ["paint", (entry) => {
                    limitarArray(state.paints, {
                        name: entry.name,
                        startTimeMs: arredondar(entry.startTime),
                    }, LIMITE_PADRAO);
                }],
                ["largest-contentful-paint", (entry) => {
                    limitarArray(state.largestContentfulPaint, {
                        startTimeMs: arredondar(entry.startTime),
                        size: entry.size || 0,
                    }, LIMITE_PADRAO);
                }],
                ["layout-shift", (entry) => {
                    if (entry.hadRecentInput) return;
                    limitarArray(state.layoutShifts, {
                        startTimeMs: arredondar(entry.startTime),
                        value: entry.value || 0,
                    }, LIMITE_PADRAO);
                }],
                ["resource", (entry) => {
                    limitarArray(state.resources, {
                        name: entry.name,
                        initiatorType: entry.initiatorType,
                        durationMs: arredondar(entry.duration),
                        transferSize: entry.transferSize || 0,
                        encodedBodySize: entry.encodedBodySize || 0,
                    }, LIMITE_RECURSOS);
                }],
            ];

            observers.forEach(([tipo, handler]) => {
                try {
                    const observer = new PerformanceObserver((list) => {
                        list.getEntries().forEach(handler);
                    });
                    observer.observe({ type: tipo, buffered: true });
                } catch (_) {}
            });
        }

        function patchFetch() {
            if (typeof window.fetch !== "function" || window.fetch.__tarielPerfWrapped__) return;

            const originalFetch = window.fetch.bind(window);
            const originalJson = Response.prototype.json;
            const originalText = Response.prototype.text;
            const originalBlob = Response.prototype.blob;
            const originalArrayBuffer = Response.prototype.arrayBuffer;
            const originalClone = Response.prototype.clone;

            function describeRequest(input, init = {}) {
                const request = input instanceof Request ? input : null;
                const url = String(init?.url || request?.url || input || "");
                const method = String(init?.method || request?.method || "GET").toUpperCase();
                const body = init?.body;
                return {
                    url,
                    method,
                    requestBytes: estimateBodyBytes(body),
                };
            }

            function patchResponseReader(methodName, original) {
                Response.prototype[methodName] = function tarielPerfResponseReader(...args) {
                    const meta = responseMeta.get(this);
                    return measureAsync(
                        `response.${methodName}`,
                        async () => original.apply(this, args),
                        {
                            category: "network",
                            detail: {
                                phase: "body",
                                url: meta?.url || "",
                                method: meta?.method || "",
                                status: meta?.status || 0,
                                responseId: meta?.responseId || "",
                            },
                        }
                    );
                };
            }

            Response.prototype.clone = function tarielPerfClone(...args) {
                const clone = originalClone.apply(this, args);
                const meta = responseMeta.get(this);
                if (meta) {
                    responseMeta.set(clone, { ...meta, cloned: true });
                }
                return clone;
            };

            patchResponseReader("json", originalJson);
            patchResponseReader("text", originalText);
            patchResponseReader("blob", originalBlob);
            patchResponseReader("arrayBuffer", originalArrayBuffer);

            window.fetch = function tarielPerfFetch(input, init = {}) {
                const meta = describeRequest(input, init);
                const token = start(`fetch:${meta.method} ${meta.url}`, {
                    category: "network",
                    detail: {
                        type: "fetch",
                        url: meta.url,
                        method: meta.method,
                        requestBytes: meta.requestBytes,
                    },
                });

                mark("network.fetch.start", {
                    url: meta.url,
                    method: meta.method,
                });

                return originalFetch(input, init)
                    .then((response) => {
                        const responseId = `resp-${++state.seq}`;
                        const contentLength = Number(response.headers.get("content-length") || 0) || null;
                        responseMeta.set(response, {
                            responseId,
                            url: meta.url,
                            method: meta.method,
                            status: response.status,
                            contentLength,
                        });
                        end(token, {
                            status: response.status,
                            ok: response.ok,
                            responseId,
                            contentLength,
                            ttfbApproxMs: arredondar(now() - token.startedAt),
                        });
                        return response;
                    })
                    .catch((error) => {
                        end(token, {
                            failed: true,
                            url: meta.url,
                            method: meta.method,
                            error: String(error?.message || error || "erro de fetch"),
                        });
                        throw error;
                    });
            };

            window.fetch.__tarielPerfWrapped__ = true;
        }

        function patchXHR() {
            if (typeof XMLHttpRequest !== "function" || XMLHttpRequest.prototype.__tarielPerfWrapped__) return;

            const originalOpen = XMLHttpRequest.prototype.open;
            const originalSend = XMLHttpRequest.prototype.send;

            XMLHttpRequest.prototype.open = function tarielPerfXHROpen(method, url, ...rest) {
                this.__tarielPerfMeta = {
                    method: String(method || "GET").toUpperCase(),
                    url: String(url || ""),
                };
                return originalOpen.call(this, method, url, ...rest);
            };

            XMLHttpRequest.prototype.send = function tarielPerfXHRSend(body) {
                const meta = this.__tarielPerfMeta || {
                    method: "GET",
                    url: "",
                };
                const token = start(`xhr:${meta.method} ${meta.url}`, {
                    category: "network",
                    detail: {
                        type: "xhr",
                        url: meta.url,
                        method: meta.method,
                        requestBytes: estimateBodyBytes(body),
                    },
                });

                this.addEventListener("loadend", () => {
                    end(token, {
                        status: this.status,
                        ok: this.status >= 200 && this.status < 400,
                        responseBytes: Number(this.getResponseHeader?.("content-length") || 0) || null,
                    });
                }, { once: true });

                return originalSend.call(this, body);
            };

            XMLHttpRequest.prototype.__tarielPerfWrapped__ = true;
        }

        function patchEventTargets() {
            if (typeof EventTarget !== "function" || EventTarget.prototype.__tarielPerfWrapped__) return;

            const originalAddEventListener = EventTarget.prototype.addEventListener;
            const vistos = new Map();

            EventTarget.prototype.addEventListener = function tarielPerfAddEventListener(type, listener, options) {
                const targetLabel = describeNode(this);
                const capture = typeof options === "boolean" ? options : !!options?.capture;
                const chave = `${getTargetId(this)}|${String(type)}|${getListenerId(listener)}|${capture ? "capture" : "bubble"}`;

                state.listeners.total += 1;
                state.listeners.byType.set(String(type), Number(state.listeners.byType.get(String(type)) || 0) + 1);

                const duplicado = vistos.has(chave);

                if (duplicado) {
                    state.listeners.duplicates += 1;
                } else {
                    vistos.set(chave, true);
                }

                limitarArray(state.listeners.recent, {
                    type: String(type),
                    target: targetLabel,
                    duplicate: duplicado,
                }, LIMITE_PADRAO);

                return originalAddEventListener.call(this, type, listener, options);
            };

            EventTarget.prototype.__tarielPerfWrapped__ = true;
        }

        function patchMutationObserver() {
            if (typeof window.MutationObserver !== "function" || window.MutationObserver.__tarielPerfWrapped__) return;

            const NativeMutationObserver = window.MutationObserver;

            window.MutationObserver = class TarielPerfMutationObserver extends NativeMutationObserver {
                constructor(callback) {
                    const observerId = `mo-${++state.seq}`;
                    const wrappedCallback = (mutations, observer) => {
                        const token = start(`observer:${observer.__tarielPerfLabel || observerId}`, {
                            category: "observer",
                            detail: {
                                mutationCount: Array.isArray(mutations) ? mutations.length : 0,
                            },
                        });
                        state.observers.callbacks += 1;
                        const label = String(observer.__tarielPerfLabel || observerId);
                        state.observers.byLabel.set(label, Number(state.observers.byLabel.get(label) || 0) + 1);

                        try {
                            return callback(mutations, observer);
                        } finally {
                            end(token, {
                                mutationCount: Array.isArray(mutations) ? mutations.length : 0,
                                label,
                            });
                            limitarArray(state.observers.recent, {
                                id: observerId,
                                label,
                                mutationCount: Array.isArray(mutations) ? mutations.length : 0,
                            }, LIMITE_PADRAO);
                        }
                    };

                    super(wrappedCallback);
                    state.observers.total += 1;
                    this.__tarielPerfLabel = observerId;
                }

                observe(target, options) {
                    limitarArray(state.observers.recent, {
                        id: this.__tarielPerfLabel,
                        action: "observe",
                        target: describeNode(target),
                        options: normalizarDetail(options),
                    }, LIMITE_PADRAO);
                    return super.observe(target, options);
                }
            };

            window.MutationObserver.__tarielPerfWrapped__ = true;
        }

        function patchStorage() {
            if (typeof Storage !== "function" || Storage.prototype.__tarielPerfWrapped__) return;

            const originalSetItem = Storage.prototype.setItem;
            const originalRemoveItem = Storage.prototype.removeItem;

            Storage.prototype.setItem = function tarielPerfSetItem(key, value) {
                const token = start(`storage:setItem:${String(key)}`, {
                    category: "storage",
                    detail: {
                        key: String(key),
                        bucket: this === localStorage ? "localStorage" : "sessionStorage",
                        size: String(value ?? "").length,
                    },
                });
                try {
                    return originalSetItem.call(this, key, value);
                } finally {
                    const bucket = this === localStorage ? "localStorage" : "sessionStorage";
                    end(token, { bucket });
                    const chave = `${bucket}:${String(key)}`;
                    state.storage.totals.set(chave, Number(state.storage.totals.get(chave) || 0) + 1);
                    limitarArray(state.storage.writes, {
                        action: "setItem",
                        bucket,
                        key: String(key),
                        atMs: arredondar(now()),
                    }, LIMITE_PADRAO);
                }
            };

            Storage.prototype.removeItem = function tarielPerfRemoveItem(key) {
                const bucket = this === localStorage ? "localStorage" : "sessionStorage";
                const token = start(`storage:removeItem:${String(key)}`, {
                    category: "storage",
                    detail: {
                        key: String(key),
                        bucket,
                    },
                });
                try {
                    return originalRemoveItem.call(this, key);
                } finally {
                    end(token, { bucket });
                    const chave = `${bucket}:${String(key)}`;
                    state.storage.totals.set(chave, Number(state.storage.totals.get(chave) || 0) + 1);
                    limitarArray(state.storage.writes, {
                        action: "removeItem",
                        bucket,
                        key: String(key),
                        atMs: arredondar(now()),
                    }, LIMITE_PADRAO);
                }
            };

            Storage.prototype.__tarielPerfWrapped__ = true;
        }

        const api = {
            enabled: true,
            mark,
            markOnce,
            start,
            end,
            begin,
            finish,
            count,
            noteModule,
            snapshotDOM,
            measureSync,
            measureAsync,
            getReport,
            clear,
            printSummary,
            topFunctions,
            topNetwork,
            topLongTasks,
            fetchBackendSummary,
            fetchBackendReport,
            resetBackendSummary,
        };

        window.TarielPerf = api;
        captureNavigation();
        patchPerformanceObserver();
        patchFetch();
        patchXHR();
        patchEventTargets();
        patchMutationObserver();
        patchStorage();

        mark("perf.enabled", {
            mode: "backend_and_query_or_localStorage",
        });
        noteModule("shared/api-core.js", {
            readyState: document.readyState,
        });
        markOnce("boot.document.interactive", {
            readyState: document.readyState,
        });
        snapshotDOM("boot:eager");

        document.addEventListener("DOMContentLoaded", () => {
            captureNavigation();
            markOnce("boot.dom_content_loaded", {
                readyState: document.readyState,
            });
            snapshotDOM("boot:dom-content-loaded");
        }, { once: true });

        window.addEventListener("load", () => {
            captureNavigation();
            markOnce("boot.window_load", {
                readyState: document.readyState,
            });
            snapshotDOM("boot:window-load");
        }, { once: true });

        return api;
    }

    const TarielPerf = criarTarielPerf();

    function debug(...args) {
        if (EM_PRODUCAO || !DEBUG_ATIVO) return;

        try {
            (console?.debug ?? console?.log)?.call(console, "[Tariel]", ...args);
        } catch (_) {}
    }

    function log(nivel, ...args) {
        const nivelNormalizado = String(nivel || "log").trim().toLowerCase() || "log";
        if (EM_PRODUCAO && nivelNormalizado !== "error") return;
        if (!EM_PRODUCAO && !DEBUG_ATIVO && ["debug", "info", "log"].includes(nivelNormalizado)) {
            return;
        }

        try {
            if (EM_PRODUCAO) {
                console.error("[Tariel]", args[0] ?? "Erro");
                return;
            }
            (console?.[nivelNormalizado] ?? console?.log)?.call(console, "[Tariel]", ...args);
        } catch (_) { }
    }

    function logOnce(chave, nivel, ...args) {
        const key = String(chave || "").trim();
        if (!key) {
            log(nivel, ...args);
            return true;
        }

        if (LOGS_UNICOS.has(key)) {
            return false;
        }

        LOGS_UNICOS.add(key);

        if (String(nivel || "").trim().toLowerCase() === "debug") {
            debug(...args);
            return true;
        }

        log(nivel, ...args);
        return true;
    }

    function obterCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content?.trim() ?? "";
    }

    const CSRF_TOKEN = obterCSRFToken();

    if (!CSRF_TOKEN) {
        log("warn", "CSRF token não encontrado.");
    }

    function escapeHTML(str) {
        if (str === null || str === undefined) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    let _toastTimer = null;
    let _toastEl = null;

    const ICONES_TOAST = {
        sucesso: "check_circle",
        erro: "error",
        aviso: "warning",
        info: "info",
    };

    function _obterToastEl() {
        if (_toastEl?.isConnected) return _toastEl;
        if (!document.body) return null;

        _toastEl = document.createElement("div");
        _toastEl.className = "toast-notificacao";
        _toastEl.setAttribute("role", "status");
        _toastEl.setAttribute("aria-live", "polite");
        document.body.appendChild(_toastEl);

        return _toastEl;
    }

    function mostrarToast(mensagem, tipo = "erro", duracaoMs = 4000) {
        if (typeof window.exibirToast === "function") {
            window.exibirToast(String(mensagem ?? ""), tipo, duracaoMs);
            return;
        }

        const el = _obterToastEl();
        if (!el) return;

        const icone = ICONES_TOAST[tipo] ?? "info";
        const tempo = Number.isFinite(duracaoMs) ? Math.max(1000, duracaoMs) : 4000;

        el.className = `toast-notificacao toast-${tipo}`;
        el.innerHTML = `
            <span class="material-symbols-rounded" aria-hidden="true">${icone}</span>
            <span>${escapeHTML(mensagem)}</span>
        `;

        clearTimeout(_toastTimer);
        el.classList.remove("visivel");
        void el.offsetWidth;
        el.classList.add("visivel");

        _toastTimer = setTimeout(() => {
            el.classList.remove("visivel");
        }, tempo);
    }

    function comCabecalhoCSRF(headers = {}) {
        const token = obterCSRFToken();
        return {
            ...headers,
            ...(token ? { "X-CSRF-Token": token } : {}),
        };
    }

    function criarFormDataComCSRF(extra = {}) {
        const form = new FormData();
        const token = obterCSRFToken();

        if (token) form.append("csrf_token", token);

        Object.entries(extra).forEach(([chave, valor]) => {
            if (valor !== undefined && valor !== null) {
                form.append(chave, valor);
            }
        });

        return form;
    }

    function validarPrefixoBase64(base64) {
        if (typeof base64 !== "string") return "";

        const valor = base64.trim();
        const prefixos = [
            "data:image/jpeg;base64,",
            "data:image/jpg;base64,",
            "data:image/png;base64,",
            "data:image/webp;base64,",
            "data:image/gif;base64,",
        ];

        return prefixos.some((p) => valor.startsWith(p)) ? valor : "";
    }

    const SETORES_VALIDOS = new Set([
        "geral",
        "eletrica",
        "mecanica",
        "caldeiraria",
        "spda",
        "loto",
        "nr10",
        "nr12",
        "nr13",
        "nr35",
        "avcb",
        "pie",
        "rti",
    ]);

    function sanitizarSetor(setor) {
        const valor = String(setor || "").trim().toLowerCase();
        return SETORES_VALIDOS.has(valor) ? valor : "geral";
    }

    const EVENTOS_TARIEL = Object.freeze({
        API_PRONTA: Object.freeze({
            canonical: "tariel:api-pronta",
            aliases: Object.freeze([]),
            modules: Object.freeze([
                "web/static/js/shared/api.js",
                "web/static/js/chat/chat_painel_core.js",
            ]),
        }),
        LAUDO_CRIADO: Object.freeze({
            canonical: "tariel:laudo-criado",
            aliases: Object.freeze(["tariellaudo-criado"]),
            modules: Object.freeze([
                "web/static/js/shared/chat-network.js",
                "web/static/js/shared/api.js",
                "web/static/js/chat/chat_painel_laudos.js",
                "web/static/js/shared/ui.js",
            ]),
        }),
        LAUDO_SELECIONADO: Object.freeze({
            canonical: "tariel:laudo-selecionado",
            aliases: Object.freeze([]),
            modules: Object.freeze([
                "web/static/js/chat/chat_painel_laudos.js",
                "web/static/js/chat/chat_index_page.js",
                "web/static/js/shared/api.js",
                "web/static/js/chat/chat_painel_core.js",
            ]),
        }),
        LAUDO_CARD_SINCRONIZADO: Object.freeze({
            canonical: "tariel:laudo-card-sincronizado",
            aliases: Object.freeze([]),
            modules: Object.freeze([
                "web/static/js/shared/chat-network.js",
                "web/static/js/shared/api.js",
                "web/static/js/chat/chat_painel_laudos.js",
                "web/static/js/chat/chat_index_page.js",
            ]),
        }),
        ESTADO_RELATORIO: Object.freeze({
            canonical: "tariel:estado-relatorio",
            aliases: Object.freeze(["tarielestado-relatorio"]),
            modules: Object.freeze([
                "web/static/js/shared/chat-network.js",
                "web/static/js/shared/api.js",
                "web/static/js/chat/chat_index_page.js",
                "web/static/js/chat/chat_painel_core.js",
                "web/static/js/chat/chat_painel_relatorio.js",
                "web/static/js/shared/ui.js",
            ]),
        }),
        RELATORIO_INICIADO: Object.freeze({
            canonical: "tariel:relatorio-iniciado",
            aliases: Object.freeze(["tarielrelatorio-iniciado"]),
            modules: Object.freeze([
                "web/static/js/shared/chat-network.js",
                "web/static/js/shared/api.js",
                "web/static/js/chat/chat_index_page.js",
                "web/static/js/chat/chat_painel_relatorio.js",
                "web/static/js/chat/chat_painel_laudos.js",
                "web/static/js/shared/ui.js",
            ]),
        }),
        RELATORIO_FINALIZADO: Object.freeze({
            canonical: "tariel:relatorio-finalizado",
            aliases: Object.freeze(["tarielrelatorio-finalizado"]),
            modules: Object.freeze([
                "web/static/js/shared/chat-network.js",
                "web/static/js/shared/api.js",
                "web/static/js/chat/chat_index_page.js",
                "web/static/js/chat/chat_painel_relatorio.js",
                "web/static/js/chat/chat_painel_laudos.js",
                "web/static/js/shared/ui.js",
            ]),
        }),
        CANCELAR_RELATORIO: Object.freeze({
            canonical: "tariel:cancelar-relatorio",
            aliases: Object.freeze(["tarielrelatorio-cancelado"]),
            modules: Object.freeze([
                "web/static/js/shared/chat-network.js",
                "web/static/js/chat/chat_index_page.js",
                "web/static/js/chat/chat_painel_relatorio.js",
                "web/static/js/chat/chat_painel_laudos.js",
                "web/static/js/shared/ui.js",
            ]),
        }),
        HISTORICO_LAUDO_RENDERIZADO: Object.freeze({
            canonical: "tariel:historico-laudo-renderizado",
            aliases: Object.freeze(["tarielhistorico-laudo-renderizado"]),
            modules: Object.freeze([
                "web/static/js/shared/api.js",
                "web/static/js/chat/chat_index_page.js",
            ]),
        }),
        MESA_AVALIADORA_ATIVADA: Object.freeze({
            canonical: "tariel:mesa-avaliadora-ativada",
            aliases: Object.freeze(["tarielmesa-avaliadora-ativada"]),
            modules: Object.freeze([
                "web/static/js/chat/chat_painel_mesa.js",
                "web/static/js/chat/chat_index_page.js",
            ]),
        }),
        ATIVAR_MESA_AVALIADORA: Object.freeze({
            canonical: "tariel:ativar-mesa-avaliadora",
            aliases: Object.freeze(["tarielativar-mesa-avaliadora"]),
            modules: Object.freeze([
                "web/static/js/chat/chat_painel_mesa.js",
            ]),
        }),
        MESA_STATUS: Object.freeze({
            canonical: "tariel:mesa-status",
            aliases: Object.freeze(["tarielmesa-status"]),
            modules: Object.freeze([
                "web/static/js/shared/chat-network.js",
                "web/static/js/chat/chat_index_page.js",
            ]),
        }),
        GATE_QUALIDADE_FALHOU: Object.freeze({
            canonical: "tariel:gate-qualidade-falhou",
            aliases: Object.freeze(["tarielgate-qualidade-falhou"]),
            modules: Object.freeze([
                "web/static/js/shared/chat-network.js",
                "web/static/js/chat/chat_index_page.js",
            ]),
        }),
        DISPARAR_COMANDO_SISTEMA: Object.freeze({
            canonical: "tariel:disparar-comando-sistema",
            aliases: Object.freeze(["tarieldisparar-comando-sistema"]),
            modules: Object.freeze([
                "web/static/js/shared/chat-network.js",
                "web/static/js/shared/api.js",
            ]),
        }),
        RELATORIO_FINALIZACAO_FALHOU: Object.freeze({
            canonical: "tariel:relatorio-finalizacao-falhou",
            aliases: Object.freeze(["tarielrelatorio-finalizacao-falhou"]),
            modules: Object.freeze([
                "web/static/js/shared/api.js",
            ]),
        }),
        THREAD_TAB_ALTERADA: Object.freeze({
            canonical: "tariel:thread-tab-alterada",
            aliases: Object.freeze([]),
            modules: Object.freeze([
                "web/static/js/chat/chat_painel_laudos.js",
                "web/static/js/chat/chat_index_page.js",
            ]),
        }),
        SCREEN_SYNCED: Object.freeze({
            canonical: "tariel:screen-synced",
            aliases: Object.freeze([]),
            modules: Object.freeze([
                "web/static/js/chat/chat_index_page.js",
                "web/static/js/shared/ui.js",
                "web/static/js/inspetor/mesa_widget.js",
            ]),
        }),
        NAVIGATE_HOME: Object.freeze({
            canonical: "tariel:navigate-home",
            aliases: Object.freeze([]),
            modules: Object.freeze([
                "web/static/js/shared/ui.js",
                "web/static/js/chat/chat_index_page.js",
            ]),
        }),
    });

    const EVENTOS_TARIEL_POR_NOME = Object.create(null);
    Object.entries(EVENTOS_TARIEL).forEach(([key, config]) => {
        const definition = Object.freeze({
            key,
            canonical: config.canonical,
            aliases: Object.freeze([...(config.aliases || [])]),
            modules: Object.freeze([...(config.modules || [])]),
        });

        EVENTOS_TARIEL_POR_NOME[key] = definition;
        EVENTOS_TARIEL_POR_NOME[definition.canonical] = definition;
        definition.aliases.forEach((alias) => {
            EVENTOS_TARIEL_POR_NOME[alias] = definition;
        });
    });

    const AVISOS_EVENTO_LEGADO = new Set();
    const PREFIXO_EVENTO_LEGADO = "[Tariel][Eventos]";
    let sequenciaEventoTariel = 0;

    function resolverEventoTariel(nomeOuChave) {
        const nome = String(nomeOuChave || "").trim();
        if (!nome) {
            return Object.freeze({
                key: null,
                canonical: "",
                aliases: Object.freeze([]),
                modules: Object.freeze([]),
            });
        }

        const definition = EVENTOS_TARIEL_POR_NOME[nome];
        if (definition) return definition;

        return Object.freeze({
            key: null,
            canonical: nome,
            aliases: Object.freeze([]),
            modules: Object.freeze([]),
        });
    }

    function listarNomesEventoTariel(nomeOuChave, { incluirAliases = true } = {}) {
        const definition = resolverEventoTariel(nomeOuChave);
        return [
            definition.canonical,
            ...(incluirAliases ? definition.aliases : []),
        ].filter(Boolean);
    }

    function marcarDebugEventoLegado(alias, canonical, canal) {
        const root = document.documentElement;
        const body = document.body;
        const alvo = body || root;
        if (!alvo) return;

        alvo.dataset.inspectorLegacyEventCompat = "true";
        alvo.dataset.inspectorLegacyEventAlias = String(alias || "");
        alvo.dataset.inspectorLegacyEventCanonical = String(canonical || "");
        alvo.dataset.inspectorLegacyEventChannel = String(canal || "");
    }

    function avisarEventoLegado(alias, canonical, canal) {
        const chave = `${canal}:${alias}:${canonical}`;
        if (AVISOS_EVENTO_LEGADO.has(chave)) return;
        AVISOS_EVENTO_LEGADO.add(chave);
        marcarDebugEventoLegado(alias, canonical, canal);

        if (!EM_PRODUCAO) {
            logOnce(
                `legacy-event:${chave}`,
                "debug",
                `${PREFIXO_EVENTO_LEGADO} alias legado em uso (${canal}): ${alias} -> ${canonical}`
            );
        }
    }

    function prepararDetalheEventoTariel(detail, canonical) {
        if (!detail || typeof detail !== "object") return detail;
        if (!Object.isExtensible(detail)) return detail;

        if (!Object.prototype.hasOwnProperty.call(detail, "__tarielCanonicalEventId")) {
            Object.defineProperty(detail, "__tarielCanonicalEventId", {
                value: `${canonical || "tariel:evento"}:${Date.now()}:${sequenciaEventoTariel += 1}`,
                enumerable: false,
                configurable: true,
            });
        }

        if (!Object.prototype.hasOwnProperty.call(detail, "__tarielCanonicalEventName")) {
            Object.defineProperty(detail, "__tarielCanonicalEventName", {
                value: String(canonical || ""),
                enumerable: false,
                configurable: true,
            });
        }

        return detail;
    }

    function emitirEventoTariel(nomesOuChave, detail = {}, options = {}) {
        const {
            target = document,
            bubbles = true,
            emitirAliases = true,
        } = options || {};

        const entradas = Array.isArray(nomesOuChave) ? nomesOuChave : [nomesOuChave];
        const canonicosEmitidos = new Set();

        entradas
            .map((entrada) => resolverEventoTariel(entrada))
            .forEach((definition) => {
                if (!definition.canonical || canonicosEmitidos.has(definition.canonical)) return;
                canonicosEmitidos.add(definition.canonical);

                const payload = prepararDetalheEventoTariel(detail, definition.canonical);
                target.dispatchEvent(
                    new CustomEvent(definition.canonical, {
                        detail: payload,
                        bubbles,
                    })
                );

                if (!emitirAliases) return;

                definition.aliases.forEach((alias) => {
                    avisarEventoLegado(alias, definition.canonical, "dispatch");
                    target.dispatchEvent(
                        new CustomEvent(alias, {
                            detail: payload,
                            bubbles,
                        })
                    );
                });
            });
    }

    function construirAssinaturaEventoTariel(canonical, detail) {
        if (detail && typeof detail === "object") {
            const eventId = detail.__tarielCanonicalEventId;
            if (eventId) return `${canonical}|${eventId}`;

            const partes = [
                detail.laudoId ?? detail.laudo_id ?? detail.laudoid ?? "",
                detail.estado_normalizado ?? detail.estado ?? detail.state ?? "",
                detail.status ?? "",
                detail.tipoTemplate ?? detail.tipo_template ?? "",
                detail.tab ?? "",
                detail.comando ?? "",
                detail.origem ?? "",
            ];
            return `${canonical}|${partes.join("|")}`;
        }

        return `${canonical}|${String(detail ?? "")}`;
    }

    function ouvirEventoTariel(nomeOuChave, handler, options = {}) {
        if (typeof handler !== "function") {
            return () => {};
        }

        const {
            target = document,
            aceitarAliases = true,
            listenerOptions = false,
            dedupeMs = 80,
        } = options || {};

        const definition = resolverEventoTariel(nomeOuChave);
        const nomes = [
            definition.canonical,
            ...(aceitarAliases ? definition.aliases : []),
        ].filter(Boolean);
        const vistosRecentemente = new Map();

        const wrapped = (event) => {
            const tipoRecebido = String(event?.type || definition.canonical || "");
            const detalhe = event?.detail;

            if (tipoRecebido && tipoRecebido !== definition.canonical) {
                avisarEventoLegado(tipoRecebido, definition.canonical, "listen");
            }

            if (definition.aliases.length > 0) {
                const assinatura = construirAssinaturaEventoTariel(definition.canonical, detalhe);
                const agora = Date.now();
                const anterior = vistosRecentemente.get(assinatura);
                if (anterior && agora - anterior <= dedupeMs) {
                    return;
                }
                vistosRecentemente.set(assinatura, agora);

                if (vistosRecentemente.size > 50) {
                    vistosRecentemente.forEach((instante, chave) => {
                        if (agora - instante > dedupeMs * 4) {
                            vistosRecentemente.delete(chave);
                        }
                    });
                }
            }

            handler(event);
        };

        nomes.forEach((nome) => {
            target.addEventListener(nome, wrapped, listenerOptions);
        });

        return () => {
            nomes.forEach((nome) => {
                target.removeEventListener(nome, wrapped, listenerOptions);
            });
        };
    }

    const TarielInspectorEvents = {
        REGISTRY: EVENTOS_TARIEL,
        resolve: resolverEventoTariel,
        namesFor: listarNomesEventoTariel,
        emit: emitirEventoTariel,
        on: ouvirEventoTariel,
    };

    window.TarielInspectorEvents = TarielInspectorEvents;

    window.TarielCore = {
        EM_PRODUCAO,
        DEBUG_ATIVO,
        CSRF_TOKEN,
        ICONES_TOAST,
        SETORES_VALIDOS,
        TarielPerf,
        EVENTOS_TARIEL,
        log,
        debug,
        logOnce,
        escapeHTML,
        mostrarToast,
        validarPrefixoBase64,
        sanitizarSetor,
        comCabecalhoCSRF,
        criarFormDataComCSRF,
        obterCSRFToken,
        resolverEventoTariel,
        listarNomesEventoTariel,
        emitirEventoTariel,
        ouvirEventoTariel,
    };
})();
