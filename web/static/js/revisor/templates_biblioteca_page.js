(() => {
    "use strict";

    const config = window.__TARIEL_TEMPLATE_CONFIG__ || {};
    const csrf = String(
        config.csrfToken ||
        document.querySelector('meta[name="csrf-token"]')?.content ||
        "",
    );
    const STORAGE_KEY = "tariel.reviewdesk.selectedTemplate.v1";

    const els = {
        lista: document.getElementById("lista"),
        statusLista: document.getElementById("status-lista"),
        search: document.getElementById("search-templates"),
        filtroModo: document.getElementById("filter-modo"),
        filtroStatusTemplate: document.getElementById("filter-status-template"),
        sortTemplates: document.getElementById("sort-templates"),
        filtroAtivo: document.getElementById("flt-ativo"),
        filtroRascunho: document.getElementById("flt-rascunho"),
        btnRefresh: document.getElementById("btn-refresh"),
        btnLimparFiltros: document.getElementById("btn-limpar-filtros"),
        metricTotal: document.getElementById("metric-total"),
        metricWord: document.getElementById("metric-word"),
        metricAtivo: document.getElementById("metric-ativo"),
        metricTesting: document.getElementById("metric-testing"),
        metricUsage: document.getElementById("metric-usage"),
        metricLastUse: document.getElementById("metric-last-use") || document.querySelector("[data-metric-last-use]"),
        selectedBanner: document.getElementById("selected-template-banner"),
        selectedName: document.getElementById("selected-template-name"),
        selectedSummary: document.getElementById("selected-template-summary"),
        selectedChip: document.getElementById("selected-template-chip"),
        btnClearSelected: document.getElementById("btn-clear-selected-template"),
        previewModal: document.getElementById("template-preview-modal"),
        previewCode: document.getElementById("preview-modal-code"),
        previewTitle: document.getElementById("preview-modal-title"),
        previewSubtitle: document.getElementById("preview-modal-subtitle"),
        previewStatusNote: document.getElementById("preview-modal-status-note"),
        previewModeNote: document.getElementById("preview-modal-mode-note"),
        previewSections: document.getElementById("preview-modal-sections"),
        previewFields: document.getElementById("preview-modal-fields"),
        previewDocumentName: document.getElementById("preview-modal-document-name"),
        previewLoading: document.getElementById("preview-modal-loading"),
        previewFrame: document.getElementById("preview-modal-frame"),
        previewBaseLink: document.getElementById("link-preview-base"),
        btnChoosePreview: document.getElementById("btn-choose-preview-template"),
        btnClosePreview: document.getElementById("btn-close-template-preview"),
    };

    if (!els.lista) {
        return;
    }

    const parsePreviewPayload = (value) => {
        if (value && typeof value === "object") {
            return value;
        }
        const texto = String(value || "").trim();
        if (!texto) {
            return {};
        }
        try {
            const parsed = JSON.parse(texto);
            return parsed && typeof parsed === "object" ? parsed : {};
        } catch (_) {
            return {};
        }
    };

    const state = {
        itens: [],
        busca: "",
        modo: "todos",
        statusTemplate: "todos",
        ordenacao: "recentes",
        incluirAtivos: true,
        incluirRascunhos: true,
        renderToken: 0,
        thumbCache: new Map(),
        previewBlobUrl: "",
        previewPayload: parsePreviewPayload(config.dadosPreviewExemploJson),
        selectedTemplateId: null,
        selectedSnapshot: null,
    };

    const html = (valor) => String(valor || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");

    const status = (msg = "", tipo = "") => {
        if (!els.statusLista) {
            return;
        }
        els.statusLista.textContent = msg;
        els.statusLista.classList.remove("ok", "err");
        if (tipo === "ok") {
            els.statusLista.classList.add("ok");
        }
        if (tipo === "err") {
            els.statusLista.classList.add("err");
        }
    };

    const erroHttp = async (res) => {
        try {
            const payload = await res.json();
            return payload.detail || payload.erro || `HTTP ${res.status}`;
        } catch (_) {
            return `HTTP ${res.status}`;
        }
    };

    const modoTemplate = (item) => (item?.is_editor_rico ? "word" : "pdf");
    const statusTemplate = (item) => String(item?.status_template || (item?.ativo ? "ativo" : "rascunho"));
    const labelStatusTemplate = (item) => String(item?.status_template_label || statusTemplate(item));
    const codigoTemplate = (item) => String(item?.codigo_template || "").trim();
    const dataAtualizacao = (item) => String(item?.atualizado_em || item?.criado_em || "");
    const dataUltimoUso = (item) => String(item?.ultima_utilizacao_em || "");
    const previewSummary = (item) => (item && typeof item.preview_summary === "object" ? item.preview_summary : {});

    const formatarDataPtBr = (iso) => {
        const data = new Date(String(iso || ""));
        if (!Number.isFinite(data.getTime())) {
            return "-";
        }
        return data.toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        });
    };

    const temasCapa = [
        {
            key: "green",
            className: "theme-green",
            kicker: "Treinamento e rotina",
            subtitle: "Boa leitura para laudos com abertura clara, passos da inspeção e encerramento objetivo.",
            points: ["Objetivo do laudo", "Roteiro da inspeção", "Fechamento claro"],
        },
        {
            key: "blue",
            className: "theme-blue",
            kicker: "Máquinas e verificação",
            subtitle: "Funciona bem quando a mesa precisa enxergar itens técnicos, evidências e conferências de campo.",
            points: ["Checklist técnico", "Pontos de atenção", "Histórico de uso"],
        },
        {
            key: "orange",
            className: "theme-orange",
            kicker: "Obra e operação",
            subtitle: "Ajuda a destacar contexto do local, rotina operacional e riscos principais do trabalho.",
            points: ["Contexto do local", "Riscos principais", "Medidas sugeridas"],
        },
        {
            key: "yellow",
            className: "theme-yellow",
            kicker: "Altura e cuidado",
            subtitle: "Identidade forte para laudos que pedem leitura rápida e foco visual nas orientações críticas.",
            points: ["Itens obrigatórios", "Resumo de atenção", "Fechamento visual"],
        },
        {
            key: "red",
            className: "theme-red",
            kicker: "Inflamáveis e risco",
            subtitle: "Traz peso visual para modelos com risco alto, bloqueios e critérios de segurança.",
            points: ["Risco e bloqueio", "Evidência obrigatória", "Conclusão técnica"],
        },
        {
            key: "copper",
            className: "theme-copper",
            kicker: "Pressão e integridade",
            subtitle: "Aproxima a leitura de laudos industriais com foco em equipamento, integridade e condição de uso.",
            points: ["Equipamento", "Integridade", "Condição final"],
        },
        {
            key: "teal",
            className: "theme-teal",
            kicker: "Processo e fluido",
            subtitle: "Leitura limpa para modelos com rastreio de processo, produto e ambiente operacional.",
            points: ["Processo atual", "Condição de operação", "Fechamento da análise"],
        },
        {
            key: "wine",
            className: "theme-wine",
            kicker: "Espaço e controle",
            subtitle: "Tom mais denso para modelos com ambiente confinado, autorização e prova de segurança.",
            points: ["Cenário do caso", "Provas de segurança", "Liberação final"],
        },
        {
            key: "cyan",
            className: "theme-cyan",
            kicker: "Sinalização e leitura",
            subtitle: "Visual mais leve para laudos de comunicação, orientação e conformidade de campo.",
            points: ["Sinalização", "Padrão exigido", "Leitura objetiva"],
        },
        {
            key: "slate",
            className: "theme-slate",
            kicker: "Base oficial",
            subtitle: "Modelo curinga para estruturas amplas, com foco em clareza e organização da leitura.",
            points: ["Visão geral", "Estrutura pronta", "Conclusão visual"],
        },
    ];

    const codigoVitrine = (codigo) => {
        const valor = String(codigo || "").trim();
        if (!valor) {
            return "MODELO";
        }
        const matchNr = valor.match(/(?:^|[_-])nr[_-]?0*(\d{1,2})(?:[_-]|$)/i) || valor.match(/^nr0*(\d{1,2})/i);
        if (matchNr) {
            return `NR ${Number(matchNr[1])}`;
        }
        const tokens = valor.replaceAll("-", "_").split("_").filter(Boolean);
        const resumo = tokens.slice(0, 2).join(" ").trim();
        return (resumo || valor).toUpperCase();
    };

    const limparTituloModelo = (texto) => String(texto || "")
        .replace(/\btemplate\b/gi, "")
        .replace(/\bmodelo\b/gi, "")
        .replace(/\bvers[aã]o\b/gi, "")
        .replace(/\bv\s*\d+\b/gi, "")
        .replace(/\s{2,}/g, " ")
        .replace(/^[\s\-.,•]+|[\s\-.,•]+$/g, "")
        .trim();

    const tituloCapaGrupo = (grupo) => {
        const candidato = limparTituloModelo(grupo?.recomendada?.nome || "");
        if (candidato) {
            return candidato;
        }
        return String(grupo?.codigo || "").replaceAll("_", " ").trim() || "Modelo sem nome";
    };

    const temaPorCodigo = (codigo) => {
        const valor = String(codigo || "").toLowerCase();
        if (valor.includes("nr35") || valor.includes("altura")) return temasCapa.find((tema) => tema.key === "yellow") || temasCapa[0];
        if (valor.includes("nr33") || valor.includes("espaco_confinado")) return temasCapa.find((tema) => tema.key === "wine") || temasCapa[0];
        if (valor.includes("nr26") || valor.includes("sinalizacao")) return temasCapa.find((tema) => tema.key === "cyan") || temasCapa[0];
        if (valor.includes("nr20") || valor.includes("inflam")) return temasCapa.find((tema) => tema.key === "red") || temasCapa[0];
        if (valor.includes("nr18") || valor.includes("obra") || valor.includes("construcao")) return temasCapa.find((tema) => tema.key === "orange") || temasCapa[0];
        if (valor.includes("nr13") || valor.includes("vaso") || valor.includes("pressao")) return temasCapa.find((tema) => tema.key === "copper") || temasCapa[0];
        if (valor.includes("nr10") || valor.includes("eletric")) return temasCapa.find((tema) => tema.key === "blue") || temasCapa[0];
        if (valor.includes("nr12") || valor.includes("maquina")) return temasCapa.find((tema) => tema.key === "teal") || temasCapa[0];
        if (valor.includes("nr6") || valor.includes("epi")) return temasCapa.find((tema) => tema.key === "blue") || temasCapa[0];
        if (valor.includes("nr5") || valor.includes("cipa")) return temasCapa.find((tema) => tema.key === "green") || temasCapa[0];
        const hash = [...valor].reduce((acc, char) => acc + char.charCodeAt(0), 0);
        return temasCapa[hash % temasCapa.length];
    };

    const labelStatusGaleria = (item) => {
        const mapa = {
            ativo: "Pronto para preencher",
            em_teste: "Em ajuste",
            rascunho: "Em montagem",
            legado: "Versão antiga",
            arquivado: "Arquivado",
        };
        return mapa[statusTemplate(item)] || labelStatusTemplate(item);
    };

    const labelFormatoGaleria = (item) => modoTemplate(item) === "word" ? "Modelo editável" : "Modelo pronto";

    const resumoEstadoPrincipal = (item) => {
        const resumo = previewSummary(item);
        const nota = String(resumo.status_note || "").trim();
        if (nota) {
            return nota;
        }
        return "Modelo pronto para a mesa escolher e revisar.";
    };

    const observacaoUsoGrupo = (grupo) => {
        if (grupo?.ultimoUso) {
            return `Último uso em ${formatarDataPtBr(grupo.ultimoUso)}.`;
        }
        if (Number(grupo?.totalUso || 0) > 0) {
            return `${Number(grupo.totalUso || 0)} uso(s) já registrados.`;
        }
        return "Ainda sem uso real em documentos.";
    };

    const obterItemPorId = (id) => state.itens.find((item) => Number(item.id) === Number(id)) || null;

    const carregarEscolhaSalva = () => {
        try {
            const payload = window.localStorage.getItem(STORAGE_KEY);
            if (!payload) {
                return;
            }
            const parsed = JSON.parse(payload);
            const resolvedId = Number(parsed?.id || 0);
            state.selectedTemplateId = resolvedId > 0 ? resolvedId : null;
            state.selectedSnapshot = parsed && typeof parsed === "object" ? parsed : null;
        } catch (_) {
            state.selectedTemplateId = null;
            state.selectedSnapshot = null;
        }
    };

    const persistirEscolha = () => {
        if (!state.selectedSnapshot) {
            window.localStorage.removeItem(STORAGE_KEY);
            return;
        }
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state.selectedSnapshot));
    };

    const limparEscolha = ({ silent = false } = {}) => {
        state.selectedTemplateId = null;
        state.selectedSnapshot = null;
        persistirEscolha();
        renderSelectedBanner();
        render();
        renderizarMiniaturasVisiveis().catch(() => {});
        if (!silent) {
            status("Escolha do modelo removida.", "ok");
        }
    };

    const salvarEscolha = (item) => {
        if (!item) {
            return;
        }
        state.selectedTemplateId = Number(item.id);
        state.selectedSnapshot = {
            id: Number(item.id),
            nome: String(item.nome || ""),
            codigo_template: String(item.codigo_template || ""),
            versao: Number(item.versao || 1),
            status_template_label: labelStatusGaleria(item),
            modo_editor_label: labelFormatoGaleria(item),
        };
        persistirEscolha();
        renderSelectedBanner();
        render();
        renderizarMiniaturasVisiveis().catch(() => {});
        status("Modelo escolhido para a próxima leitura da mesa.", "ok");
    };

    const renderSelectedBanner = () => {
        if (!els.selectedBanner || !els.selectedName || !els.selectedSummary || !els.selectedChip) {
            return;
        }
        const itemAtual = state.selectedTemplateId ? obterItemPorId(state.selectedTemplateId) : null;
        if (itemAtual) {
            state.selectedSnapshot = {
                id: Number(itemAtual.id),
                nome: String(itemAtual.nome || ""),
                codigo_template: String(itemAtual.codigo_template || ""),
                versao: Number(itemAtual.versao || 1),
                status_template_label: labelStatusGaleria(itemAtual),
                modo_editor_label: labelFormatoGaleria(itemAtual),
            };
            persistirEscolha();
        }
        const snapshot = state.selectedSnapshot;
        if (!snapshot) {
            els.selectedBanner.hidden = true;
            return;
        }
        els.selectedBanner.hidden = false;
        els.selectedName.textContent = `${snapshot.nome || "Modelo sem nome"} · v${Number(snapshot.versao || 1)}`;
        els.selectedSummary.textContent = `A mesa passa a olhar primeiro para ${snapshot.codigo_template || "este modelo"} com base ${snapshot.modo_editor_label || "oficial"}.`;
        els.selectedChip.textContent = `${codigoVitrine(snapshot.codigo_template || "")} · escolhido`;
    };

    const prioridadeBaseRecomendada = (item) => {
        const prioridadeStatus = {
            ativo: 50,
            em_teste: 40,
            rascunho: 30,
            legado: 20,
            arquivado: 10,
        };
        return {
            prioridade: Number(prioridadeStatus[statusTemplate(item)] || 0),
            versao: Number(item?.versao || 0),
            modo: item?.is_editor_rico ? 1 : 0,
            id: Number(item?.id || 0),
        };
    };

    const compararPrioridadeBase = (a, b) => {
        const prioridadeA = prioridadeBaseRecomendada(a);
        const prioridadeB = prioridadeBaseRecomendada(b);
        if (prioridadeA.prioridade !== prioridadeB.prioridade) return prioridadeB.prioridade - prioridadeA.prioridade;
        if (prioridadeA.versao !== prioridadeB.versao) return prioridadeB.versao - prioridadeA.versao;
        if (prioridadeA.modo !== prioridadeB.modo) return prioridadeB.modo - prioridadeA.modo;
        return prioridadeB.id - prioridadeA.id;
    };

    const construirGrupos = (itens) => {
        const grupos = new Map();
        itens.forEach((item) => {
            const codigo = codigoTemplate(item);
            if (!codigo) {
                return;
            }
            if (!grupos.has(codigo)) {
                grupos.set(codigo, []);
            }
            grupos.get(codigo).push(item);
        });

        const listaGrupos = [...grupos.entries()].map(([codigo, itensGrupo]) => {
            const versoes = [...itensGrupo].sort((a, b) => {
                const diffVersao = Number(b.versao || 0) - Number(a.versao || 0);
                if (diffVersao !== 0) return diffVersao;
                return Number(b.id || 0) - Number(a.id || 0);
            });
            const recomendada = versoes.find((item) => !!item.is_base_recomendada) || [...versoes].sort(compararPrioridadeBase)[0] || versoes[0];
            const ativa = versoes.find((item) => !!item.ativo) || null;
            const contratoGrupo = recomendada || versoes[0] || {};
            const ultimaAtualizacao = versoes
                .map((item) => Date.parse(dataAtualizacao(item)))
                .filter((valor) => Number.isFinite(valor))
                .sort((a, b) => b - a)[0] || 0;
            const ultimoUsoValido = versoes
                .map((item) => dataUltimoUso(item))
                .filter((valor) => !!valor)
                .sort((a, b) => Date.parse(String(b || "")) - Date.parse(String(a || "")))[0] || "";
            const totalWord = Number(contratoGrupo.grupo_total_word ?? versoes.filter((item) => item.is_editor_rico).length);
            const totalVersoes = Number(contratoGrupo.grupo_total_versoes ?? versoes.length);
            const totalPdf = Number(contratoGrupo.grupo_total_pdf ?? Math.max(0, totalVersoes - totalWord));
            const totalUso = Number(recomendada?.uso_total || versoes[0]?.uso_total || 0) || 0;

            return {
                codigo,
                itens: versoes,
                recomendada,
                ativa,
                totalVersoes,
                versoesVisiveis: versoes.length,
                totalWord,
                totalPdf,
                totalUso,
                ultimaAtualizacao,
                ultimoUso: ultimoUsoValido,
            };
        });

        listaGrupos.sort((a, b) => {
            if (state.ordenacao === "nome") {
                return String(a.codigo || "").localeCompare(String(b.codigo || ""), "pt-BR", { sensitivity: "base" });
            }
            if (state.ordenacao === "ativos") {
                const ativoA = a.ativa ? 1 : 0;
                const ativoB = b.ativa ? 1 : 0;
                if (ativoA !== ativoB) return ativoB - ativoA;
                return b.ultimaAtualizacao - a.ultimaAtualizacao;
            }
            return b.ultimaAtualizacao - a.ultimaAtualizacao;
        });

        return listaGrupos;
    };

    const atualizarMetricas = () => {
        const total = state.itens.length;
        const totalWord = state.itens.filter((item) => item.is_editor_rico).length;
        const totalAtivo = state.itens.filter((item) => item.ativo).length;
        const totalTesting = state.itens.filter((item) => statusTemplate(item) === "em_teste").length;
        const grupos = construirGrupos(state.itens);
        const totalUso = grupos.reduce((acc, grupo) => acc + (Number(grupo.totalUso || 0) || 0), 0);
        const ultimoUso = [...grupos]
            .filter((grupo) => !!grupo.ultimoUso)
            .sort((a, b) => Date.parse(String(b.ultimoUso || "")) - Date.parse(String(a.ultimoUso || "")))[0];

        if (els.metricTotal) els.metricTotal.textContent = String(total);
        if (els.metricWord) els.metricWord.textContent = String(totalWord);
        if (els.metricAtivo) els.metricAtivo.textContent = String(totalAtivo);
        if (els.metricTesting) els.metricTesting.textContent = String(totalTesting);
        if (els.metricUsage) els.metricUsage.textContent = String(totalUso);
        if (els.metricLastUse) els.metricLastUse.textContent = ultimoUso?.ultimoUso ? formatarDataPtBr(ultimoUso.ultimoUso) : "-";
    };

    const filtrar = () => {
        const filtrados = state.itens.filter((item) => {
            const textoBusca = `${item.nome || ""} ${item.codigo_template || ""}`.toLowerCase();
            if (state.busca && !textoBusca.includes(state.busca)) return false;
            if (state.modo !== "todos" && modoTemplate(item) !== state.modo) return false;
            if (state.statusTemplate !== "todos" && statusTemplate(item) !== state.statusTemplate) return false;

            const st = statusTemplate(item);
            if (!state.incluirAtivos && st === "ativo") return false;
            if (!state.incluirRascunhos && st === "rascunho") return false;
            return true;
        });

        return filtrados;
    };

    const renderSecoes = (item) => {
        const secoes = previewSummary(item).sections || [];
        return secoes.slice(0, 4).map((secao, indice) => `
            <article class="template-preview-section-card">
                <small>Parte ${indice + 1}</small>
                <strong>${html(secao)}</strong>
            </article>
        `).join("");
    };

    const renderCamposIa = (item) => {
        const campos = previewSummary(item).fill_fields || [];
        return campos.slice(0, 6).map((campo) => `
            <span class="template-fill-chip">${html(campo)}</span>
        `).join("");
    };

    const renderVersoesVisiveis = (grupo) => grupo.itens.slice(0, 4).map((item) => `
        <span class="template-version-pill ${statusTemplate(item)} ${Number(item.id) === Number(state.selectedTemplateId || 0) ? "is-selected" : ""}">
            v${Number(item.versao || 1)} · ${html(labelStatusGaleria(item))}
        </span>
    `).join("");

    const render = () => {
        const itens = filtrar();
        const grupos = construirGrupos(itens);
        if (!grupos.length) {
            els.lista.innerHTML = `
                <div class="empty-state">
                    Nenhum modelo apareceu com os filtros atuais.
                </div>
            `;
            return;
        }

        els.lista.innerHTML = grupos.map((grupo, idx) => {
            const recomendada = grupo.recomendada;
            const modo = modoTemplate(recomendada);
            const st = statusTemplate(recomendada);
            const tema = temaPorCodigo(grupo.codigo);
            const tituloCapa = tituloCapaGrupo(grupo);
            const resumoVersoes = grupo.versoesVisiveis === grupo.totalVersoes
                ? `${grupo.totalVersoes} versão${grupo.totalVersoes === 1 ? "" : "ões"}`
                : `${grupo.versoesVisiveis} de ${grupo.totalVersoes} versões visíveis`;
            const escolhido = Number(recomendada.id || 0) === Number(state.selectedTemplateId || 0);
            return `
                <section
                    class="template-group-card ${tema.className} ${escolhido ? "is-selected-model" : ""}"
                    data-codigo-template="${html(grupo.codigo)}"
                    style="--card-index:${idx};"
                >
                    <header class="template-group-head">
                        <div class="template-group-copy">
                            <span class="template-group-code">${html(codigoVitrine(grupo.codigo))}</span>
                            <h3 class="template-group-title">${html(tituloCapa)}</h3>
                            <p class="template-group-meta">
                                ${html(resumoEstadoPrincipal(recomendada))}
                                • ${html(resumoVersoes)}
                                • ${html(observacaoUsoGrupo(grupo))}
                            </p>
                        </div>
                        <div class="template-group-summary">
                            <span class="badge recommended">v${Number(recomendada?.versao || 1)}</span>
                            <span class="badge ${modo}">${modo === "word" ? "WORD" : "PDF"}</span>
                            <span class="badge ${st}">${html(labelStatusGaleria(recomendada))}</span>
                            ${grupo.ativa ? '<span class="badge active_marker">EM USO</span>' : ""}
                            ${escolhido ? '<span class="badge manual_marker">ESCOLHIDO</span>' : ""}
                        </div>
                    </header>

                    <div class="template-group-featured">
                        <div class="template-group-cover">
                            <div class="template-cover-head">
                                <span class="template-cover-code">${html(codigoVitrine(grupo.codigo))}</span>
                                <span class="template-cover-chip">${modo === "word" ? "Word" : "PDF"}</span>
                            </div>
                            <div class="template-cover-main">
                                <span class="template-cover-kicker">${html(tema.kicker)}</span>
                                <strong class="template-cover-title">${html(tituloCapa)}</strong>
                                <p class="template-cover-subtitle">${html(tema.subtitle)}</p>
                                <div class="template-cover-points">
                                    ${tema.points.map((point) => `
                                        <span class="template-cover-point">${html(point)}</span>
                                    `).join("")}
                                </div>
                            </div>
                            <div class="template-cover-footer">
                                <span>${html(labelStatusGaleria(recomendada))}</span>
                                <span>${html(labelFormatoGaleria(recomendada))}</span>
                            </div>
                        </div>

                        <div class="template-featured-body">
                            <div class="template-featured-heading">
                                <span class="template-section-kicker">Documento base</span>
                                <h3 class="template-title">${html(recomendada.nome || "Sem nome")}</h3>
                                <p class="template-meta">${html(recomendada.codigo_template || "")} • v${Number(recomendada.versao || 1)} • ${html(resumoVersoes)}</p>
                            </div>

                            <div class="template-story">
                                <strong>${html(resumoEstadoPrincipal(recomendada))}</strong>
                                <p>${html(String(previewSummary(recomendada).mode_note || "A composição do caso já fica organizada por trás deste visual."))}</p>
                            </div>

                            <div class="template-detail-list">
                                <div>
                                    <strong>Formato</strong>
                                    <span>${html(labelFormatoGaleria(recomendada))}</span>
                                </div>
                                <div>
                                    <strong>Uso total</strong>
                                    <span>${Number(recomendada.uso_total || 0) || 0} documento(s)</span>
                                </div>
                                <div>
                                    <strong>Última atualização</strong>
                                    <span>${formatarDataPtBr(dataAtualizacao(recomendada))}</span>
                                </div>
                                <div>
                                    <strong>Último uso</strong>
                                    <span>${grupo.ultimoUso ? formatarDataPtBr(grupo.ultimoUso) : "Ainda sem uso em campo"}</span>
                                </div>
                            </div>

                            <div class="template-preview-sections">
                                ${renderSecoes(recomendada)}
                            </div>

                            <div class="template-fill-chips">
                                ${renderCamposIa(recomendada)}
                            </div>

                            <p class="template-route-note">A mesa escolhe a base visual. O preenchimento, os campos e as regras ficam organizados nos bastidores.</p>

                            <div class="template-actions">
                                <button class="btn primary js-open-preview" type="button" data-id="${Number(recomendada.id)}">Ver documento</button>
                                <button class="btn ghost js-select-model" type="button" data-id="${Number(recomendada.id)}">${escolhido ? "Modelo escolhido" : "Escolher modelo"}</button>
                                <button class="btn ghost js-open-base" type="button" data-id="${Number(recomendada.id)}">Abrir documento base</button>
                            </div>
                        </div>

                        <div class="template-preview template-preview-featured">
                            <div class="template-overlay-meta">
                                <span class="preview-chip ${modo}">${modo === "word" ? "Editável" : "Pronto"}</span>
                                <span class="preview-chip recommended">${escolhido ? "Escolhido" : "Visualização"}</span>
                            </div>
                            <span class="template-preview-kicker">Visualização do documento</span>
                            <div class="thumb-frame thumb-frame-featured">
                                <canvas class="thumb-canvas" data-template-id="${Number(recomendada.id)}"></canvas>
                            </div>
                            <div class="thumb-loading" data-template-loading="${Number(recomendada.id)}">Carregando miniatura...</div>
                            <p class="template-preview-note">${html(resumoEstadoPrincipal(recomendada))}</p>
                        </div>
                    </div>

                    <div class="template-version-strip">
                        <strong>Versões visíveis</strong>
                        <div class="template-version-pills">
                            ${renderVersoesVisiveis(grupo)}
                        </div>
                    </div>
                </section>
            `;
        }).join("");
    };

    const garantirPdfJs = () => {
        if (!window.pdfjsLib) {
            throw new Error("PDF.js não carregado.");
        }
        if (!window.pdfjsLib.GlobalWorkerOptions.workerSrc) {
            window.pdfjsLib.GlobalWorkerOptions.workerSrc = String(
                config.pdfWorkerUrl || "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js",
            );
        }
    };

    const dimensoesThumb = (canvas) => {
        const frame = canvas.closest(".thumb-frame");
        const largura = Math.max(140, Math.floor(frame?.clientWidth || 160));
        const altura = Math.max(198, Math.floor(largura * (297 / 210)));
        return { largura, altura };
    };

    const desenharDataUrlNoCanvas = async (canvas, dataUrl) => {
        const img = new Image();
        await new Promise((resolve, reject) => {
            img.onload = resolve;
            img.onerror = reject;
            img.src = dataUrl;
        });
        const { largura, altura } = dimensoesThumb(canvas);
        canvas.width = largura;
        canvas.height = altura;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.clearRect(0, 0, largura, altura);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, largura, altura);

        const escala = Math.min(largura / Math.max(1, img.width), altura / Math.max(1, img.height));
        const destinoW = Math.floor(img.width * escala);
        const destinoH = Math.floor(img.height * escala);
        const x = Math.floor((largura - destinoW) / 2);
        const y = Math.floor((altura - destinoH) / 2);
        ctx.drawImage(img, x, y, destinoW, destinoH);
        canvas.classList.add("ready");
    };

    const renderizarThumbTemplate = async (templateId, canvas, loadingEl) => {
        const id = Number(templateId || 0);
        if (!id || !canvas) return;

        const cache = state.thumbCache.get(id);
        if (typeof cache === "string" && cache.startsWith("data:image/")) {
            await desenharDataUrlNoCanvas(canvas, cache);
            if (loadingEl) loadingEl.style.display = "none";
            return;
        }

        try {
            garantirPdfJs();
            const res = await fetch(`/revisao/api/templates-laudo/${id}/arquivo-base`, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const bytes = await res.arrayBuffer();
            const tarefa = window.pdfjsLib.getDocument({ data: bytes });
            const pdf = await tarefa.promise;
            const pagina = await pdf.getPage(1);

            const { largura, altura } = dimensoesThumb(canvas);
            const viewportBase = pagina.getViewport({ scale: 1 });
            const escala = Math.max(0.1, largura / Math.max(1, viewportBase.width));
            const viewport = pagina.getViewport({ scale });

            const canvasTemp = document.createElement("canvas");
            canvasTemp.width = Math.floor(viewport.width);
            canvasTemp.height = Math.floor(viewport.height);
            const ctxTemp = canvasTemp.getContext("2d", { alpha: false });
            if (!ctxTemp) throw new Error("Canvas temporário indisponível.");
            await pagina.render({ canvasContext: ctxTemp, viewport }).promise;

            canvas.width = largura;
            canvas.height = altura;
            const ctx = canvas.getContext("2d", { alpha: false });
            if (!ctx) throw new Error("Canvas context indisponível.");
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, largura, altura);

            const escalaFit = Math.min(
                largura / Math.max(1, canvasTemp.width),
                altura / Math.max(1, canvasTemp.height),
            );
            const destinoW = Math.floor(canvasTemp.width * escalaFit);
            const destinoH = Math.floor(canvasTemp.height * escalaFit);
            const x = Math.floor((largura - destinoW) / 2);
            const y = Math.floor((altura - destinoH) / 2);
            ctx.drawImage(canvasTemp, x, y, destinoW, destinoH);

            canvas.classList.add("ready");
            state.thumbCache.set(id, canvas.toDataURL("image/jpeg", 0.85));
            if (loadingEl) loadingEl.style.display = "none";
        } catch (erro) {
            if (loadingEl) {
                loadingEl.classList.add("error");
                loadingEl.textContent = "Sem miniatura";
            }
            state.thumbCache.set(id, "erro");
            console.warn("[Tariel] Falha ao gerar miniatura do template:", id, erro);
        }
    };

    const renderizarMiniaturasVisiveis = async () => {
        const tokenAtual = ++state.renderToken;
        const canvases = [...els.lista.querySelectorAll(".thumb-canvas[data-template-id]")];
        if (!canvases.length) return;

        const fila = canvases.map((canvas) => ({
            canvas,
            templateId: Number(canvas.dataset.templateId || 0),
            loadingEl: els.lista.querySelector(`[data-template-loading="${canvas.dataset.templateId}"]`),
        }));

        const worker = async () => {
            while (fila.length > 0) {
                if (tokenAtual !== state.renderToken) return;
                const item = fila.shift();
                if (!item) return;
                await renderizarThumbTemplate(item.templateId, item.canvas, item.loadingEl);
            }
        };

        const concorrencia = Math.min(4, fila.length);
        await Promise.all(Array.from({ length: Math.max(1, concorrencia) }, () => worker()));
    };

    const carregar = async () => {
        status("Carregando vitrine da mesa...");
        try {
            const res = await fetch("/revisao/api/templates-laudo", {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (!res.ok) throw new Error(await erroHttp(res));
            const data = await res.json();
            state.itens = Array.isArray(data.itens) ? data.itens : [];
            atualizarMetricas();
            renderSelectedBanner();
            render();
            status(`${state.itens.length} modelo(s) carregados na biblioteca.`, "ok");
            renderizarMiniaturasVisiveis().catch(() => {});
        } catch (erro) {
            els.lista.innerHTML = `<div class="empty-state">Falha ao carregar a biblioteca de modelos.</div>`;
            status(`Erro: ${erro.message}`, "err");
        }
    };

    const fecharPreview = () => {
        if (els.previewModal) {
            els.previewModal.hidden = true;
        }
        if (state.previewBlobUrl) {
            URL.revokeObjectURL(state.previewBlobUrl);
            state.previewBlobUrl = "";
        }
        if (els.previewFrame) {
            els.previewFrame.removeAttribute("src");
        }
    };

    const renderListaModal = (container, itens, fallbackText) => {
        if (!container) {
            return;
        }
        if (!Array.isArray(itens) || !itens.length) {
            container.innerHTML = `<span class="template-preview-side-pill">${html(fallbackText)}</span>`;
            return;
        }
        container.innerHTML = itens.map((item) => `
            <span class="template-preview-side-pill">${html(item)}</span>
        `).join("");
    };

    const carregarPreviewPdf = async (item) => {
        if (!els.previewLoading || !els.previewFrame) {
            return;
        }
        els.previewLoading.hidden = false;
        els.previewLoading.textContent = "Abrindo o documento...";
        els.previewFrame.removeAttribute("src");
        if (state.previewBlobUrl) {
            URL.revokeObjectURL(state.previewBlobUrl);
            state.previewBlobUrl = "";
        }

        const carregarBlobBase = async () => {
            const resBase = await fetch(`/revisao/api/templates-laudo/${Number(item.id)}/arquivo-base`, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (!resBase.ok) {
                throw new Error(await erroHttp(resBase));
            }
            return resBase.blob();
        };

        try {
            const res = await fetch(`/revisao/api/templates-laudo/${Number(item.id)}/preview`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF-Token": csrf,
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify({ dados_formulario: state.previewPayload }),
            });
            let blob;
            if (res.ok) {
                blob = await res.blob();
            } else {
                blob = await carregarBlobBase();
            }
            state.previewBlobUrl = URL.createObjectURL(blob);
            els.previewFrame.src = state.previewBlobUrl;
            els.previewLoading.hidden = true;
        } catch (erro) {
            els.previewLoading.hidden = false;
            els.previewLoading.textContent = `Não foi possível abrir o documento: ${erro.message}`;
        }
    };

    const abrirPreview = async (id) => {
        const item = obterItemPorId(id);
        if (!item || !els.previewModal) {
            return;
        }
        const resumo = previewSummary(item);
        if (els.previewCode) els.previewCode.textContent = codigoVitrine(item.codigo_template || "");
        if (els.previewTitle) els.previewTitle.textContent = String(item.nome || "Laudo pré-pronto");
        if (els.previewSubtitle) {
            els.previewSubtitle.textContent = `${item.codigo_template || "modelo"} · v${Number(item.versao || 1)} · ${labelStatusGaleria(item)}`;
        }
        if (els.previewStatusNote) {
            els.previewStatusNote.textContent = String(resumo.status_note || "Modelo pronto para leitura da mesa.");
        }
        if (els.previewModeNote) {
            els.previewModeNote.textContent = String(resumo.mode_note || "A estrutura por tras completa o laudo sem expor a parte interna.");
        }
        if (els.previewDocumentName) {
            els.previewDocumentName.textContent = `${item.nome || "Documento"} · v${Number(item.versao || 1)}`;
        }
        renderListaModal(els.previewSections, resumo.sections || [], "Estrutura principal do laudo");
        renderListaModal(els.previewFields, resumo.fill_fields || [], "Cliente e dados da inspeção");
        if (els.previewBaseLink) {
            els.previewBaseLink.href = `/revisao/api/templates-laudo/${Number(item.id)}/arquivo-base`;
        }
        if (els.btnChoosePreview) {
            els.btnChoosePreview.dataset.id = String(Number(item.id));
        }
        els.previewModal.hidden = false;
        await carregarPreviewPdf(item);
    };

    const abrirBase = (id) => {
        window.open(`/revisao/api/templates-laudo/${Number(id)}/arquivo-base`, "_blank", "noopener,noreferrer");
    };

    const bind = () => {
        els.search?.addEventListener("input", () => {
            state.busca = String(els.search.value || "").trim().toLowerCase();
            render();
            renderizarMiniaturasVisiveis().catch(() => {});
        });

        els.filtroModo?.addEventListener("change", () => {
            state.modo = String(els.filtroModo.value || "todos");
            render();
            renderizarMiniaturasVisiveis().catch(() => {});
        });

        els.filtroStatusTemplate?.addEventListener("change", () => {
            state.statusTemplate = String(els.filtroStatusTemplate.value || "todos");
            render();
            renderizarMiniaturasVisiveis().catch(() => {});
        });

        els.sortTemplates?.addEventListener("change", () => {
            state.ordenacao = String(els.sortTemplates.value || "recentes");
            render();
            renderizarMiniaturasVisiveis().catch(() => {});
        });

        els.filtroAtivo?.addEventListener("change", () => {
            state.incluirAtivos = !!els.filtroAtivo.checked;
            render();
            renderizarMiniaturasVisiveis().catch(() => {});
        });

        els.filtroRascunho?.addEventListener("change", () => {
            state.incluirRascunhos = !!els.filtroRascunho.checked;
            render();
            renderizarMiniaturasVisiveis().catch(() => {});
        });

        els.btnRefresh?.addEventListener("click", carregar);

        els.btnLimparFiltros?.addEventListener("click", () => {
            state.busca = "";
            state.modo = "todos";
            state.statusTemplate = "todos";
            state.ordenacao = "recentes";
            state.incluirAtivos = true;
            state.incluirRascunhos = true;
            if (els.search) els.search.value = "";
            if (els.filtroModo) els.filtroModo.value = "todos";
            if (els.filtroStatusTemplate) els.filtroStatusTemplate.value = "todos";
            if (els.sortTemplates) els.sortTemplates.value = "recentes";
            if (els.filtroAtivo) els.filtroAtivo.checked = true;
            if (els.filtroRascunho) els.filtroRascunho.checked = true;
            render();
            renderizarMiniaturasVisiveis().catch(() => {});
        });

        els.btnClearSelected?.addEventListener("click", () => limparEscolha({ silent: false }));

        els.lista.addEventListener("click", (ev) => {
            const btnPreview = ev.target.closest(".js-open-preview");
            if (btnPreview) {
                abrirPreview(btnPreview.dataset.id);
                return;
            }

            const btnSelect = ev.target.closest(".js-select-model");
            if (btnSelect) {
                const item = obterItemPorId(btnSelect.dataset.id);
                if (item) {
                    salvarEscolha(item);
                }
                return;
            }

            const btnBase = ev.target.closest(".js-open-base");
            if (btnBase) {
                abrirBase(btnBase.dataset.id);
            }
        });

        els.btnChoosePreview?.addEventListener("click", () => {
            const item = obterItemPorId(els.btnChoosePreview?.dataset.id);
            if (!item) {
                return;
            }
            salvarEscolha(item);
            fecharPreview();
        });

        els.btnClosePreview?.addEventListener("click", fecharPreview);
        els.previewModal?.addEventListener("click", (ev) => {
            if (ev.target === els.previewModal) {
                fecharPreview();
            }
        });

        document.addEventListener("keydown", (ev) => {
            if (ev.key === "Escape" && els.previewModal && !els.previewModal.hidden) {
                fecharPreview();
            }
        });
    };

    carregarEscolhaSalva();
    renderSelectedBanner();
    bind();
    carregar();
})();
