(function () {
    "use strict";

    const modules = window.TarielInspetorModules = window.TarielInspetorModules || {};

    modules.registerPendencias = function registerPendencias(ctx) {
        const estado = ctx.state;
        const el = ctx.elements;
        const {
            normalizarFiltroPendencias,
            obterLaudoAtivoIdSeguro,
            obterHeadersComCSRF,
            ehAbortError,
            mostrarToast,
            renderizarLinksAnexosMesa,
            normalizarAnexoMesa,
            escaparHtml,
            cancelarCarregamentoPendenciasMesa,
        } = ctx.shared;
        const renderizarResumoOperacionalMesa = (...args) => ctx.actions.renderizarResumoOperacionalMesa?.(...args);
        const atualizarPainelWorkspaceDerivado = (...args) => ctx.actions.atualizarPainelWorkspaceDerivado?.(...args);
        const sincronizarResumoPendenciasWorkspace = (...args) => ctx.actions.sincronizarResumoPendenciasWorkspace?.(...args);
        const PERF = window.TarielPerf || window.TarielCore?.TarielPerf || null;

        PERF?.noteModule?.("inspetor/pendencias.js", {
            readyState: document.readyState,
        });
        const PENDENCIAS_CACHE_SILENCIOSO_MS = 1200;
        const pendenciasEmVoo = new Map();
        const cachePendencias = new Map();
        let chavePendenciasAtiva = "";

        function contarChurnPendencias(nome, detail = {}) {
            PERF?.count?.(nome, 1, {
                category: "request_churn",
                detail,
            });
        }

        function obterScreenInspectorAtual() {
            return String(
                document.body?.dataset?.inspectorBaseScreen
                || document.body?.dataset?.inspectorScreen
                || ""
            ).trim();
        }

        function pendenciasNecessariasNoContextoAtual({ append = false, forcar = false } = {}) {
            if (forcar || append) return true;
            if (document.visibilityState === "hidden") return false;

            return obterScreenInspectorAtual() === "inspection_record";
        }

        function construirChavePendencias({ alvo, filtro, pagina, tamanho, append = false }) {
            return [
                Number(alvo || 0) || 0,
                normalizarFiltroPendencias(filtro || "abertas"),
                Number(pagina || 1) || 1,
                Number(tamanho || 25) || 25,
                append ? "append" : "replace",
            ].join(":");
        }

        function clonarPendenciasResposta(dados = {}) {
            return {
                ...dados,
                pendencias: Array.isArray(dados?.pendencias)
                    ? dados.pendencias.map((item) => (item && typeof item === "object" ? { ...item } : item))
                    : [],
            };
        }

        function obterCachePendencias(chave) {
            const entry = cachePendencias.get(chave);
            if (!entry) return null;

            if ((Date.now() - Number(entry.at || 0)) > PENDENCIAS_CACHE_SILENCIOSO_MS) {
                cachePendencias.delete(chave);
                return null;
            }

            return clonarPendenciasResposta(entry.dados);
        }

        function registrarCachePendencias(chave, dados) {
            cachePendencias.set(chave, {
                at: Date.now(),
                dados: clonarPendenciasResposta(dados),
            });
        }

    function formatarDataPendencia(dataIso = "", fallback = "") {
        if (!dataIso) return fallback || "";

        const data = new Date(dataIso);
        if (Number.isNaN(data.getTime())) return fallback || dataIso;

        return data.toLocaleString("pt-BR", {
            day: "2-digit",
            month: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    function obterTextoVazioPendencias(filtro = "abertas") {
        const filtroNormalizado = normalizarFiltroPendencias(filtro);
        if (filtroNormalizado === "resolvidas") {
            return "Nenhuma pendência resolvida neste laudo.";
        }
        if (filtroNormalizado === "todas") {
            return "Nenhuma pendência enviada pela mesa avaliadora neste laudo.";
        }
        return "Nenhuma pendência aberta neste laudo.";
    }

    function atualizarBotoesFiltroPendencias() {
        const filtroAtivo = normalizarFiltroPendencias(estado.filtroPendencias);
        el.botoesFiltroPendencias.forEach((botao) => {
            const filtroBotao = normalizarFiltroPendencias(botao.dataset?.filtroPendencias);
            const ativo = filtroBotao === filtroAtivo;
            botao.classList.toggle("ativo", ativo);
            botao.setAttribute("aria-pressed", String(ativo));
        });

        if (el.textoVazioPendenciasMesa) {
            const texto = obterTextoVazioPendencias(filtroAtivo);
            if (el.textoVazioPendenciasMesaTexto) {
                el.textoVazioPendenciasMesaTexto.textContent = texto;
            } else {
                el.textoVazioPendenciasMesa.textContent = texto;
            }
        }
    }

    function atualizarTextoErroPendencias(mensagem = "") {
        const texto = String(mensagem || "").trim() || "Não foi possível carregar as pendências da mesa agora.";
        if (el.estadoErroPendenciasMesaTexto) {
            el.estadoErroPendenciasMesaTexto.textContent = texto;
            return;
        }
        if (el.estadoErroPendenciasMesa) {
            el.estadoErroPendenciasMesa.textContent = texto;
        }
    }

    function aplicarEstadoVisualPendencias(opcoes = {}) {
        const {
            loading = false,
            empty = false,
            error = false,
            list = false,
            mensagemErro = "",
        } = opcoes;

        if (el.estadoLoadingPendenciasMesa) {
            el.estadoLoadingPendenciasMesa.hidden = !loading;
            el.estadoLoadingPendenciasMesa.setAttribute("aria-hidden", String(!loading));
        }

        if (el.textoVazioPendenciasMesa) {
            el.textoVazioPendenciasMesa.hidden = !empty;
            el.textoVazioPendenciasMesa.setAttribute("aria-hidden", String(!empty));
        }

        if (el.estadoErroPendenciasMesa) {
            el.estadoErroPendenciasMesa.hidden = !error;
            el.estadoErroPendenciasMesa.setAttribute("aria-hidden", String(!error));
        }

        if (error) {
            atualizarTextoErroPendencias(mensagemErro);
        } else {
            atualizarTextoErroPendencias("");
        }

        if (el.listaPendenciasMesa) {
            el.listaPendenciasMesa.hidden = !list;
        }
    }

    function atualizarResumoPendencias(totalExibidas = 0, totalFiltrado = 0) {
        if (!el.resumoPendenciasMesa) return;

        const exibidas = Math.max(0, Number(totalExibidas || 0));
        const filtradas = Math.max(0, Number(totalFiltrado || 0));

        if (filtradas <= 0) {
            el.resumoPendenciasMesa.hidden = true;
            el.resumoPendenciasMesa.textContent = "";
            return;
        }

        el.resumoPendenciasMesa.hidden = false;
        el.resumoPendenciasMesa.textContent = `Exibindo ${exibidas} de ${filtradas} pendências no filtro atual.`;
    }

    function atualizarControlesPendenciasVisiveis() {
        const laudoAtivo = Number(estado.laudoPendenciasAtual || obterLaudoAtivoIdSeguro() || 0) || null;
        const mostrarControles = !!laudoAtivo;
        const podeMarcarLidas = !!laudoAtivo
            && !estado.pendenciasLoading
            && (Number(estado.qtdPendenciasAbertas || 0) || 0) > 0;
        const podeExportar = !!laudoAtivo && !estado.pendenciasLoading;

        if (el.btnAbrirPendenciasMesa) {
            el.btnAbrirPendenciasMesa.hidden = !mostrarControles;
            if (!mostrarControles) {
                el.btnAbrirPendenciasMesa.setAttribute("aria-expanded", "false");
            }
        }

        if (el.painelPendenciasMesa) {
            el.painelPendenciasMesa.hidden = !mostrarControles;
        }

        if (el.acoesPendenciasMesa) {
            el.acoesPendenciasMesa.hidden = !mostrarControles;
        }

        if (el.filtrosPendenciasMesa) {
            el.filtrosPendenciasMesa.hidden = !mostrarControles;
        }

        if (el.btnMarcarPendenciasLidas) {
            el.btnMarcarPendenciasLidas.disabled = !podeMarcarLidas;
            el.btnMarcarPendenciasLidas.setAttribute("aria-disabled", String(!podeMarcarLidas));
        }

        if (el.btnExportarPendenciasPdf) {
            el.btnExportarPendenciasPdf.disabled = !podeExportar;
            el.btnExportarPendenciasPdf.setAttribute("aria-disabled", String(!podeExportar));
        }
    }

    function atualizarControlesPaginacaoPendencias() {
        const mostrarMais = !!estado.temMaisPendencias && !!estado.laudoPendenciasAtual;

        if (el.btnCarregarMaisPendencias) {
            el.btnCarregarMaisPendencias.hidden = !mostrarMais;
            el.btnCarregarMaisPendencias.disabled = estado.carregandoPendencias;
            el.btnCarregarMaisPendencias.setAttribute("aria-busy", String(estado.carregandoPendencias));
        }
    }

    function limparPainelPendencias() {
        cancelarCarregamentoPendenciasMesa();
        estado.laudoPendenciasAtual = null;
        estado.pendenciasItens = [];
        estado.qtdPendenciasAbertas = 0;
        estado.filtroPendencias = "abertas";
        estado.paginaPendenciasAtual = 1;
        estado.totalPendenciasFiltradas = 0;
        estado.totalPendenciasExibidas = 0;
        estado.temMaisPendencias = false;
        estado.pendenciasLoading = false;
        estado.pendenciasEmpty = false;
        estado.pendenciasHonestEmpty = false;
        estado.pendenciasError = false;
        estado.pendenciasSynthetic = false;
        estado.pendenciasRealCount = 0;
        estado.pendenciasFilteredCount = 0;

        if (el.badgePendenciasMesa) {
            el.badgePendenciasMesa.hidden = true;
            el.badgePendenciasMesa.textContent = "0";
        }

        if (el.listaPendenciasMesa) {
            el.listaPendenciasMesa.innerHTML = "";
            el.listaPendenciasMesa.hidden = true;
        }

        atualizarBotoesFiltroPendencias();

        aplicarEstadoVisualPendencias({
            loading: false,
            empty: false,
            error: false,
            list: false,
        });

        atualizarResumoPendencias(0, 0);
        atualizarControlesPendenciasVisiveis();
        atualizarControlesPaginacaoPendencias();
        sincronizarResumoPendenciasWorkspace({
            laudoId: null,
            totalPendenciasReais: 0,
            totalPendenciasFiltradas: 0,
            totalPendenciasAbertas: 0,
            carregando: false,
            erro: false,
        });
        renderizarResumoOperacionalMesa();
        atualizarPainelWorkspaceDerivado();
    }

    function atualizarBadgePendencias(abertas = 0) {
        const total = Number(abertas || 0);
        estado.qtdPendenciasAbertas = total > 0 ? total : 0;

        if (!el.badgePendenciasMesa) {
            renderizarResumoOperacionalMesa();
            return;
        }

        if (estado.qtdPendenciasAbertas > 0) {
            el.badgePendenciasMesa.hidden = false;
            el.badgePendenciasMesa.textContent = String(estado.qtdPendenciasAbertas);
            renderizarResumoOperacionalMesa();
            return;
        }

        el.badgePendenciasMesa.hidden = true;
        el.badgePendenciasMesa.textContent = "0";
        renderizarResumoOperacionalMesa();
    }

    function renderizarListaPendencias(pendencias = [], append = false) {
        if (!el.listaPendenciasMesa || !el.textoVazioPendenciasMesa) return;

        if (!append) {
            el.listaPendenciasMesa.innerHTML = "";
        }

        if (!pendencias.length) {
            if (!append) {
                atualizarBotoesFiltroPendencias();
                aplicarEstadoVisualPendencias({
                    loading: false,
                    empty: true,
                    error: false,
                    list: false,
                });
            }
            return;
        }

        aplicarEstadoVisualPendencias({
            loading: false,
            empty: false,
            error: false,
            list: true,
        });

        pendencias.forEach((item) => {
            const li = document.createElement("li");
            const aberta = !item?.lida;
            const statusTexto = aberta ? "Aberta" : "Lida";
            const statusClasse = aberta ? "aberta" : "lida";
            const dataLabel = String(item?.data_label || "").trim() || formatarDataPendencia(item?.data || "", "");
            const resolvidaPor = String(item?.resolvida_por_nome || "").trim();
            const resolvidaEm = String(item?.resolvida_em_label || "").trim()
                || formatarDataPendencia(item?.resolvida_em || "", "");
            const infoResolucao = !aberta && (resolvidaPor || resolvidaEm)
                ? `Resolvida por ${escaparHtml(resolvidaPor || "mesa")} ${resolvidaEm ? `em ${escaparHtml(resolvidaEm)}` : ""}`.trim()
                : "";
            const proximaLida = aberta ? "true" : "false";
            const textoAcao = aberta ? "Resolver" : "Reabrir";
            const anexosHtml = renderizarLinksAnexosMesa(
                Array.isArray(item?.anexos)
                    ? item.anexos.map(normalizarAnexoMesa).filter(Boolean)
                    : []
            );

            li.className = `pendencia-item ${aberta ? "aberta" : "lida"}`;
            li.innerHTML = `
                ${String(item?.texto || "").trim() ? `<p class="pendencia-texto">${escaparHtml(item?.texto || "")}</p>` : ""}
                ${anexosHtml}
                <div class="pendencia-meta">
                    <span>#${Number(item?.id || 0) || "-"}</span>
                    <span>${escaparHtml(dataLabel || "")}</span>
                    <span class="pendencia-status ${statusClasse}">${statusTexto}</span>
                    ${infoResolucao ? `<span>${infoResolucao}</span>` : ""}
                </div>
                <div class="pendencia-acoes">
                    <button
                        type="button"
                        class="btn-pendencia-item"
                        data-pendencia-id="${Number(item?.id || 0) || 0}"
                        data-proxima-lida="${proximaLida}"
                    >${textoAcao}</button>
                </div>
            `;
            el.listaPendenciasMesa.appendChild(li);
        });
    }

    function togglePainelPendencias(abrirForcado = null) {
        if (!el.painelPendenciasMesa || !el.btnAbrirPendenciasMesa || el.btnAbrirPendenciasMesa.hidden) {
            return;
        }

        const abrir = abrirForcado === null ? el.painelPendenciasMesa.hidden : !!abrirForcado;
        el.painelPendenciasMesa.hidden = !abrir;
        el.btnAbrirPendenciasMesa.setAttribute("aria-expanded", String(abrir));
    }

    function aplicarDadosPendencias(dados = {}, {
        alvo,
        filtroAplicado,
        paginaSolicitada,
        tamanhoSolicitado,
        append = false,
    } = {}) {
        estado.laudoPendenciasAtual = alvo;
        estado.filtroPendencias = normalizarFiltroPendencias(dados?.filtro || filtroAplicado);
        estado.paginaPendenciasAtual = Number(dados?.pagina || paginaSolicitada) || 1;
        estado.tamanhoPaginaPendencias = Number(dados?.tamanho || tamanhoSolicitado) || 25;
        estado.totalPendenciasFiltradas = Number(dados?.total_filtrado || 0) || 0;
        estado.temMaisPendencias = !!dados?.tem_mais;
        atualizarBotoesFiltroPendencias();

        atualizarBadgePendencias(dados?.abertas || 0);
        const pendencias = Array.isArray(dados?.pendencias) ? dados.pendencias : [];
        estado.pendenciasItens = append
            ? [...(Array.isArray(estado.pendenciasItens) ? estado.pendenciasItens : []), ...pendencias]
            : pendencias;
        renderizarListaPendencias(pendencias, append);

        if (append) {
            estado.totalPendenciasExibidas += pendencias.length;
        } else {
            estado.totalPendenciasExibidas = pendencias.length;
        }

        atualizarResumoPendencias(estado.totalPendenciasExibidas, estado.totalPendenciasFiltradas);
        atualizarControlesPendenciasVisiveis();
        atualizarControlesPaginacaoPendencias();
        sincronizarResumoPendenciasWorkspace({
            laudoId: alvo,
            totalPendenciasReais: estado.totalPendenciasExibidas,
            totalPendenciasFiltradas: estado.totalPendenciasFiltradas,
            totalPendenciasAbertas: estado.qtdPendenciasAbertas,
            carregando: false,
            erro: false,
        });

        renderizarResumoOperacionalMesa();
        atualizarPainelWorkspaceDerivado();

        return dados;
    }

    async function carregarPendenciasMesa(opcoes = {}) {
        const {
            laudoId = null,
            silencioso = false,
            filtro = null,
            append = false,
            pagina = null,
            forcar = false,
        } = opcoes;
        const alvo = Number(laudoId || obterLaudoAtivoIdSeguro() || 0) || null;
        const filtroAplicado = normalizarFiltroPendencias(filtro || estado.filtroPendencias);
        const paginaSolicitada = Number(
            pagina
            || (append ? (estado.paginaPendenciasAtual + 1) : 1)
            || 1
        ) || 1;
        const tamanhoSolicitado = Number(estado.tamanhoPaginaPendencias || 25) || 25;
        const mudouLaudo = Number(estado.laudoPendenciasAtual || 0) !== Number(alvo || 0);

        if (!alvo) {
            limparPainelPendencias();
            return null;
        }

        if (append && !estado.temMaisPendencias) {
            return null;
        }

        if (!pendenciasNecessariasNoContextoAtual({ append, forcar })) {
            contarChurnPendencias("inspetor.pendencias.suprimida_contexto", {
                laudoId: alvo,
                filtro: filtroAplicado,
                append,
                screen: obterScreenInspectorAtual(),
            });
            return null;
        }

        const chave = construirChavePendencias({
            alvo,
            filtro: filtroAplicado,
            pagina: paginaSolicitada,
            tamanho: tamanhoSolicitado,
            append,
        });

        if (!forcar && pendenciasEmVoo.has(chave)) {
            contarChurnPendencias("inspetor.pendencias.inflight_reused", {
                laudoId: alvo,
                filtro: filtroAplicado,
                pagina: paginaSolicitada,
                append,
            });
            return pendenciasEmVoo.get(chave);
        }

        if (!forcar && silencioso && !append) {
            const cache = obterCachePendencias(chave);
            if (cache) {
                contarChurnPendencias("inspetor.pendencias.cache_hit", {
                    laudoId: alvo,
                    filtro: filtroAplicado,
                    pagina: paginaSolicitada,
                });
                return aplicarDadosPendencias(cache, {
                    alvo,
                    filtroAplicado,
                    paginaSolicitada,
                    tamanhoSolicitado,
                    append,
                });
            }
        }

        if (estado.pendenciasAbortController && chavePendenciasAtiva !== chave) {
            cancelarCarregamentoPendenciasMesa();
        }

        const controller = new AbortController();
        chavePendenciasAtiva = chave;
        estado.pendenciasAbortController = controller;
        estado.carregandoPendencias = true;
        estado.pendenciasLoading = true;
        atualizarControlesPaginacaoPendencias();

        if (el.btnAbrirPendenciasMesa) {
            el.btnAbrirPendenciasMesa.hidden = false;
        }
        if (el.painelPendenciasMesa) {
            el.painelPendenciasMesa.hidden = false;
        }

        if (!append) {
            estado.pendenciasItens = [];
            estado.totalPendenciasExibidas = 0;
            estado.totalPendenciasFiltradas = 0;
            estado.temMaisPendencias = false;
            if (mudouLaudo) {
                atualizarBadgePendencias(0);
            }
            if (el.listaPendenciasMesa) {
                el.listaPendenciasMesa.innerHTML = "";
            }
            atualizarResumoPendencias(0, 0);
            atualizarControlesPendenciasVisiveis();
            aplicarEstadoVisualPendencias({
                loading: true,
                empty: false,
                error: false,
                list: false,
            });
            sincronizarResumoPendenciasWorkspace({
                laudoId: alvo,
                totalPendenciasReais: 0,
                totalPendenciasFiltradas: 0,
                totalPendenciasAbertas: estado.qtdPendenciasAbertas,
                carregando: true,
                erro: false,
            });
        } else {
            aplicarEstadoVisualPendencias({
                loading: false,
                empty: false,
                error: false,
                list: Array.isArray(estado.pendenciasItens) && estado.pendenciasItens.length > 0,
            });
            sincronizarResumoPendenciasWorkspace({
                laudoId: alvo,
                totalPendenciasReais: estado.totalPendenciasExibidas,
                totalPendenciasFiltradas: estado.totalPendenciasFiltradas,
                totalPendenciasAbertas: estado.qtdPendenciasAbertas,
                carregando: true,
                erro: false,
            });
        }

        const requisicao = (async () => {
            try {
                const endpoint = new URL(`/app/api/laudo/${alvo}/pendencias`, window.location.origin);
                endpoint.searchParams.set("filtro", filtroAplicado);
                endpoint.searchParams.set("pagina", String(paginaSolicitada));
                endpoint.searchParams.set("tamanho", String(tamanhoSolicitado));

                const response = await fetch(endpoint.toString(), {
                    method: "GET",
                    credentials: "same-origin",
                    headers: obterHeadersComCSRF(),
                    signal: controller.signal,
                });

                if (!response.ok) {
                    throw new Error(`HTTP_${response.status}`);
                }

                const dados = await response.json();
                if (controller.signal.aborted || alvo !== obterLaudoAtivoIdSeguro()) {
                    return null;
                }
                if (!append) {
                    registrarCachePendencias(chave, dados);
                }

                return aplicarDadosPendencias(dados, {
                    alvo,
                    filtroAplicado,
                    paginaSolicitada,
                    tamanhoSolicitado,
                    append,
                });
            } catch (erro) {
            if (ehAbortError(erro)) {
                return null;
            }

            if (!append) {
                estado.pendenciasItens = [];
                estado.totalPendenciasExibidas = 0;
                estado.totalPendenciasFiltradas = 0;
                estado.temMaisPendencias = false;
                atualizarResumoPendencias(0, 0);
                atualizarControlesPendenciasVisiveis();
                aplicarEstadoVisualPendencias({
                    loading: false,
                    empty: false,
                    error: true,
                    list: false,
                    mensagemErro: "Não foi possível carregar as pendências reais deste laudo.",
                });
                sincronizarResumoPendenciasWorkspace({
                    laudoId: alvo,
                    totalPendenciasReais: 0,
                    totalPendenciasFiltradas: 0,
                    totalPendenciasAbertas: estado.qtdPendenciasAbertas,
                    carregando: false,
                    erro: true,
                });
                renderizarResumoOperacionalMesa();
                atualizarPainelWorkspaceDerivado();
            } else {
                sincronizarResumoPendenciasWorkspace({
                    laudoId: alvo,
                    totalPendenciasReais: estado.totalPendenciasExibidas,
                    totalPendenciasFiltradas: estado.totalPendenciasFiltradas,
                    totalPendenciasAbertas: estado.qtdPendenciasAbertas,
                    carregando: false,
                    erro: false,
                });
            }

            if (!silencioso) {
                mostrarToast(
                    append
                        ? "Não foi possível carregar mais pendências."
                        : "Não foi possível carregar as pendências da mesa.",
                    "erro",
                    2500
                );
            }
            return null;
        } finally {
            if (estado.pendenciasAbortController === controller) {
                estado.pendenciasAbortController = null;
            }
            if (chavePendenciasAtiva === chave) {
                chavePendenciasAtiva = "";
            }
            estado.carregandoPendencias = !!estado.pendenciasAbortController;
            estado.pendenciasLoading = estado.carregandoPendencias;
            atualizarControlesPendenciasVisiveis();
            atualizarControlesPaginacaoPendencias();
            }
        })();

        pendenciasEmVoo.set(chave, requisicao);
        requisicao.finally(() => {
            if (pendenciasEmVoo.get(chave) === requisicao) {
                pendenciasEmVoo.delete(chave);
            }
        });

        return requisicao;
    }

    async function marcarPendenciasComoLidas() {
        const laudoId = Number(estado.laudoPendenciasAtual || obterLaudoAtivoIdSeguro() || 0) || null;
        if (!laudoId || !el.btnMarcarPendenciasLidas) return;

        el.btnMarcarPendenciasLidas.disabled = true;
        el.btnMarcarPendenciasLidas.setAttribute("aria-busy", "true");

        try {
            const response = await fetch(`/app/api/laudo/${laudoId}/pendencias/marcar-lidas`, {
                method: "POST",
                credentials: "same-origin",
                headers: obterHeadersComCSRF(),
            });

            if (!response.ok) {
                throw new Error(`HTTP_${response.status}`);
            }

            await carregarPendenciasMesa({
                laudoId,
                silencioso: true,
                filtro: estado.filtroPendencias,
                forcar: true,
            });
            mostrarToast("Pendências marcadas como lidas.", "sucesso", 1800);
        } catch (_) {
            mostrarToast("Falha ao marcar pendências como lidas.", "erro", 2500);
        } finally {
            el.btnMarcarPendenciasLidas.disabled = false;
            el.btnMarcarPendenciasLidas.setAttribute("aria-busy", "false");
        }
    }

    async function atualizarPendenciaIndividual(mensagemId, lida) {
        const laudoId = Number(estado.laudoPendenciasAtual || obterLaudoAtivoIdSeguro() || 0) || null;
        const msgId = Number(mensagemId || 0) || null;

        if (!laudoId || !msgId) return;

        try {
            const response = await fetch(`/app/api/laudo/${laudoId}/pendencias/${msgId}`, {
                method: "PATCH",
                credentials: "same-origin",
                headers: obterHeadersComCSRF({ "Content-Type": "application/json" }),
                body: JSON.stringify({ lida: !!lida }),
            });

            if (!response.ok) {
                throw new Error(`HTTP_${response.status}`);
            }

            await carregarPendenciasMesa({
                laudoId,
                silencioso: true,
                filtro: estado.filtroPendencias,
                forcar: true,
            });
            mostrarToast(lida ? "Pendência marcada como resolvida." : "Pendência reaberta.", "sucesso", 1800);

        } catch (_) {
            mostrarToast("Falha ao atualizar pendência.", "erro", 2500);
        }
    }

    function extrairNomeArquivoContentDisposition(headerValor, fallback = "pendencias.pdf") {
        const valor = String(headerValor || "");
        const matchUtf8 = valor.match(/filename\*=UTF-8''([^;]+)/i);
        if (matchUtf8?.[1]) {
            try {
                return decodeURIComponent(matchUtf8[1]);
            } catch (_) {
                return matchUtf8[1];
            }
        }

        const matchSimples = valor.match(/filename="?([^"]+)"?/i);
        if (matchSimples?.[1]) {
            return matchSimples[1];
        }

        return fallback;
    }

    async function exportarPendenciasPdf() {
        const laudoId = Number(estado.laudoPendenciasAtual || obterLaudoAtivoIdSeguro() || 0) || null;
        if (!laudoId || !el.btnExportarPendenciasPdf) return;

        const filtro = normalizarFiltroPendencias(estado.filtroPendencias);
        const endpoint = new URL(`/app/api/laudo/${laudoId}/pendencias/exportar-pdf`, window.location.origin);
        endpoint.searchParams.set("filtro", filtro);

        el.btnExportarPendenciasPdf.disabled = true;
        el.btnExportarPendenciasPdf.setAttribute("aria-busy", "true");

        try {
            const response = await fetch(endpoint.toString(), {
                method: "GET",
                credentials: "same-origin",
                headers: obterHeadersComCSRF(),
            });

            if (!response.ok) {
                throw new Error(`HTTP_${response.status}`);
            }

            const contentType = String(response.headers.get("content-type") || "").toLowerCase();
            if (!contentType.includes("application/pdf")) {
                throw new Error("INVALID_CONTENT_TYPE");
            }

            const arquivo = await response.blob();
            const nomeArquivo = extrairNomeArquivoContentDisposition(
                response.headers.get("content-disposition"),
                `pendencias_laudo_${laudoId}_${filtro}.pdf`
            );

            const urlTemporaria = URL.createObjectURL(arquivo);
            const link = document.createElement("a");
            link.href = urlTemporaria;
            link.download = nomeArquivo;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(urlTemporaria);

            mostrarToast("PDF de pendências exportado.", "sucesso", 1800);
        } catch (_) {
            mostrarToast("Falha ao exportar PDF de pendências.", "erro", 2500);
        } finally {
            el.btnExportarPendenciasPdf.disabled = false;
            el.btnExportarPendenciasPdf.setAttribute("aria-busy", "false");
        }
    }

        if (PERF?.enabled) {
            const renderizarListaPendenciasOriginal = renderizarListaPendencias;
            renderizarListaPendencias = function renderizarListaPendenciasComPerf(...args) {
                const pendencias = Array.isArray(args[0]) ? args[0] : [];
                const append = args[1] === true;
                return PERF.measureSync(
                    "inspetor.pendencias.renderizarListaPendencias",
                    () => {
                        const resultado = renderizarListaPendenciasOriginal.apply(this, args);
                        PERF.snapshotDOM?.("pendencias:lista-renderizada");
                        return resultado;
                    },
                    {
                        category: "render",
                        detail: {
                            total: pendencias.length,
                            append,
                        },
                    }
                );
            };

            const carregarPendenciasMesaOriginal = carregarPendenciasMesa;
            carregarPendenciasMesa = async function carregarPendenciasMesaComPerf(...args) {
                const opcoes = args[0] && typeof args[0] === "object" ? args[0] : {};
                PERF.begin("transition.carregar_pendencias", {
                    filtro: opcoes.filtro || estado.filtroPendencias,
                    append: opcoes.append === true,
                });
                return PERF.measureAsync(
                    "inspetor.pendencias.carregarPendenciasMesa",
                    async () => {
                        const resultado = await carregarPendenciasMesaOriginal.apply(this, args);
                        PERF.finish("transition.carregar_pendencias", {
                            filtro: opcoes.filtro || estado.filtroPendencias,
                            append: opcoes.append === true,
                        });
                        PERF.snapshotDOM?.("pendencias:carregadas");
                        return resultado;
                    },
                    {
                        category: "function",
                        detail: {
                            laudoId: opcoes.laudoId || obterLaudoAtivoIdSeguro?.() || null,
                            filtro: opcoes.filtro || estado.filtroPendencias,
                            append: opcoes.append === true,
                            silencioso: opcoes.silencioso === true,
                        },
                    }
                );
            };

            const marcarPendenciasComoLidasOriginal = marcarPendenciasComoLidas;
            marcarPendenciasComoLidas = async function marcarPendenciasComoLidasComPerf(...args) {
                return PERF.measureAsync(
                    "inspetor.pendencias.marcarPendenciasComoLidas",
                    () => marcarPendenciasComoLidasOriginal.apply(this, args),
                    {
                        category: "function",
                        detail: {
                            laudoId: obterLaudoAtivoIdSeguro?.() || null,
                        },
                    }
                );
            };

            const exportarPendenciasPdfOriginal = exportarPendenciasPdf;
            exportarPendenciasPdf = async function exportarPendenciasPdfComPerf(...args) {
                return PERF.measureAsync(
                    "inspetor.pendencias.exportarPendenciasPdf",
                    () => exportarPendenciasPdfOriginal.apply(this, args),
                    {
                        category: "function",
                        detail: {
                            laudoId: obterLaudoAtivoIdSeguro?.() || null,
                            filtro: estado.filtroPendencias,
                        },
                    }
                );
            };
        }

        Object.assign(ctx.actions, {
            formatarDataPendencia,
            obterTextoVazioPendencias,
            atualizarBotoesFiltroPendencias,
            atualizarResumoPendencias,
            atualizarControlesPaginacaoPendencias,
            limparPainelPendencias,
            atualizarBadgePendencias,
            renderizarListaPendencias,
            togglePainelPendencias,
            carregarPendenciasMesa,
            marcarPendenciasComoLidas,
            atualizarPendenciaIndividual,
            extrairNomeArquivoContentDisposition,
            exportarPendenciasPdf,
        });
    };
})();
