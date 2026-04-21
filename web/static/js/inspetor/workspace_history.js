(function () {
    "use strict";

    const inspectorRuntime = window.TarielInspectorRuntime || null;
    const modules = typeof inspectorRuntime?.resolveModuleBucket === "function"
        ? inspectorRuntime.resolveModuleBucket("TarielInspetorModules")
        : (window.TarielInspetorModules = window.TarielInspetorModules || {});

    modules.registerWorkspaceHistory = function registerWorkspaceHistory(ctx) {
        const estado = ctx.state;
        const el = ctx.elements;
        const {
            escaparHtml,
            normalizarThreadTab,
            pluralizarWorkspace,
        } = ctx.shared;

        function coletarLinhasWorkspace() {
            return ctx.actions.coletarLinhasWorkspace?.() || [];
        }

        function extrairMetaLinhaWorkspace(linha) {
            return ctx.actions.extrairMetaLinhaWorkspace?.(linha) || {
                autor: "Registro",
                tempo: "",
                resumo: "",
            };
        }

        function obterSnapshotEstadoInspectorAtual() {
            return ctx.actions.obterSnapshotEstadoInspectorAtual?.() || {};
        }

        function sincronizarResumoHistoricoWorkspace(detail = {}) {
            return ctx.actions.sincronizarResumoHistoricoWorkspace?.(detail) || null;
        }

        function atualizarEmptyStateHonestoConversa() {
            ctx.actions.atualizarEmptyStateHonestoConversa?.();
        }

        function sincronizarInspectorScreen() {
            ctx.actions.sincronizarInspectorScreen?.();
        }

        function construirResumoGovernancaHistoricoWorkspace() {
            const resumo = ctx.actions.construirResumoGovernancaHistoricoWorkspace?.();
            if (resumo && typeof resumo === "object") {
                return resumo;
            }

            return {
                visible: false,
                title: "Reemissão recomendada",
                detail: "PDF emitido divergente detectado no caso atual.",
                actionLabel: "Abrir reemissão na Mesa",
            };
        }

        function normalizarFiltroChat(valor = "") {
            const filtro = String(valor || "").trim().toLowerCase();
            if (["ia", "inspetor", "mesa", "sistema"].includes(filtro)) return filtro;
            return "todos";
        }

        function normalizarFiltroTipoHistorico(valor = "") {
            const filtro = String(valor || "").trim().toLowerCase();
            if (["mensagens", "eventos", "anexos", "decisoes"].includes(filtro)) return filtro;
            return "todos";
        }

        function obterPapelLinhaWorkspace(linha) {
            const papelDataset = String(linha?.dataset?.messageRole || "").trim().toLowerCase();
            if (papelDataset) return papelDataset;
            if (linha?.classList?.contains("mensagem-sistema")) return "sistema";
            if (linha?.classList?.contains("mensagem-ia")) return "ia";
            if (linha?.classList?.contains("mensagem-origem-mesa")) return "mesa";
            return "inspetor";
        }

        function obterDetalheLinhaWorkspace(linha) {
            const meta = extrairMetaLinhaWorkspace(linha);
            const papel = obterPapelLinhaWorkspace(linha);
            const texto = String(
                linha?.querySelector(".texto-msg")?.textContent ||
                linha?.querySelector(".texto-msg-origem")?.textContent ||
                meta.resumo ||
                ""
            ).replace(/\s+/g, " ").trim();

            return {
                mensagemId: Number(linha?.dataset?.mensagemId || 0) || null,
                autor: String(linha?.dataset?.messageAuthor || meta.autor || "Registro").trim() || "Registro",
                papel,
                tempo: meta.tempo || "",
                texto,
            };
        }

        function obterTextoBuscaLinhaWorkspace(linha) {
            const detalhe = obterDetalheLinhaWorkspace(linha);
            const anexos = Array.from(linha.querySelectorAll(".mensagem-anexo-chip"))
                .map((chip) => String(chip.textContent || "").trim())
                .filter(Boolean);

            return [
                detalhe.autor,
                detalhe.tempo,
                detalhe.papel,
                detalhe.texto,
                ...anexos,
            ]
                .join(" ")
                .toLowerCase();
        }

        function obterDataLinhaWorkspace(linha) {
            const datetime = String(
                linha?.querySelector("time")?.getAttribute("datetime") ||
                linha?.dataset?.createdAt ||
                ""
            ).trim();
            if (!datetime) return null;

            const data = new Date(datetime);
            return Number.isNaN(data.getTime()) ? null : data;
        }

        function obterTipoRegistroHistoricoWorkspace(linha, detalhe = obterDetalheLinhaWorkspace(linha)) {
            const papel = detalhe.papel || obterPapelLinhaWorkspace(linha);
            const texto = String(detalhe.texto || "").trim();
            const possuiAnexos = !!linha?.querySelector?.(".mensagem-anexo-chip, .img-anexo");

            if (papel === "sistema") return "eventos";
            if (papel === "mesa" && /(aprova|rejeita|ajuste|decis|valid|conclus|parecer)/i.test(texto)) {
                return "decisoes";
            }
            if (possuiAnexos && !texto) return "anexos";
            return "mensagens";
        }

        function obterRotuloGrupoHistoricoWorkspace(data = null) {
            if (!(data instanceof Date) || Number.isNaN(data.getTime())) {
                return "Registro técnico";
            }

            const hoje = new Date();
            const inicioHoje = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate());
            const inicioData = new Date(data.getFullYear(), data.getMonth(), data.getDate());
            const diffDias = Math.round((inicioHoje - inicioData) / 86400000);

            if (diffDias === 0) return "Hoje";
            if (diffDias === 1) return "Ontem";

            return new Intl.DateTimeFormat("pt-BR", {
                day: "numeric",
                month: "short",
            }).format(data);
        }

        function obterIconeHistoricoWorkspace(tipo = "mensagens", papel = "inspetor") {
            if (tipo === "anexos") return "attach_file";
            if (tipo === "eventos") return "tune";
            if (tipo === "decisoes") return "gavel";
            if (papel === "ia") return "smart_toy";
            if (papel === "mesa") return "support_agent";
            if (papel === "sistema") return "settings";
            return "person";
        }

        function obterItensCanonicosHistoricoWorkspace() {
            if (Array.isArray(estado.historyCanonicalItems) && estado.historyCanonicalItems.length) {
                return estado.historyCanonicalItems.map((item) => ({ ...item }));
            }

            const viaApi = window.TarielAPI?.obterHistoricoLaudoAtual?.();
            return Array.isArray(viaApi) ? viaApi.map((item) => ({ ...item })) : [];
        }

        function obterPapelItemHistoricoCanonico(item = {}) {
            const papel = String(item?.papel || "").trim().toLowerCase();
            const tipo = String(item?.tipo || "").trim().toLowerCase();

            if (papel === "assistente") return "ia";
            if (papel === "engenheiro") return "mesa";
            if (papel === "usuario") return "inspetor";
            if (papel === "sistema") return "sistema";

            if (tipo.includes("humano_eng") || tipo.includes("engenheiro")) return "mesa";
            if (tipo.includes("humano_insp") || tipo === "user" || tipo === "usuario") return "inspetor";
            if (tipo.includes("system") || tipo.includes("sistema") || tipo.includes("evento")) return "sistema";
            if (tipo.includes("ia") || tipo.includes("assistant")) return "ia";

            return "ia";
        }

        function obterAutorItemHistoricoCanonico(item = {}, papel = obterPapelItemHistoricoCanonico(item)) {
            const candidatos = [
                item?.autor,
                item?.autor_nome,
                item?.nome_autor,
                item?.remetente_nome,
                item?.actor_name,
            ]
                .map((valor) => String(valor || "").trim())
                .filter(Boolean);

            if (candidatos.length) {
                return candidatos[0];
            }

            if (papel === "mesa") return "Mesa";
            if (papel === "inspetor") return "Inspetor";
            if (papel === "sistema") return "Sistema";
            return "Assistente IA";
        }

        function extrairAnexosHistoricoCanonico(item = {}) {
            const anexos = Array.isArray(item?.anexos) ? item.anexos : [];
            return anexos
                .map((anexo, index) => {
                    if (!anexo) return null;

                    if (typeof anexo === "string") {
                        const nome = String(anexo || "").trim();
                        if (!nome) return null;
                        return {
                            nome,
                            url: "",
                            tipo: "documento",
                            chave: `str-${index}-${nome}`,
                        };
                    }

                    const nome = String(
                        anexo?.nome ||
                        anexo?.filename ||
                        anexo?.arquivo_nome ||
                        anexo?.label ||
                        anexo?.titulo ||
                        ""
                    ).trim();
                    const url = String(
                        anexo?.url ||
                        anexo?.download_url ||
                        anexo?.href ||
                        anexo?.path ||
                        ""
                    ).trim();
                    const tipo = anexo?.eh_imagem ? "imagem" : String(anexo?.tipo || "documento").trim().toLowerCase() || "documento";
                    if (!nome && !url) return null;

                    return {
                        nome: nome || `Anexo ${index + 1}`,
                        url,
                        tipo,
                        chave: String(anexo?.id || anexo?.uuid || `${tipo}-${index}-${nome || url}`),
                    };
                })
                .filter(Boolean);
        }

        function obterDataItemHistoricoCanonico(item = {}) {
            const bruto = String(
                item?.criado_em_iso ||
                item?.created_at ||
                item?.data_iso ||
                ""
            ).trim();
            if (!bruto) return null;

            const data = new Date(bruto);
            return Number.isNaN(data.getTime()) ? null : data;
        }

        function obterTipoRegistroHistoricoCanonico(item = {}, papel = obterPapelItemHistoricoCanonico(item), anexos = extrairAnexosHistoricoCanonico(item)) {
            const tipoMensagem = String(item?.tipo || "").trim().toLowerCase();
            const texto = String(item?.texto || "").trim();

            if (papel === "sistema" || tipoMensagem.includes("system") || tipoMensagem.includes("evento")) {
                return "eventos";
            }

            if (papel === "mesa" && /(aprova|rejeita|ajuste|decis|valid|conclus|parecer)/i.test(texto)) {
                return "decisoes";
            }

            if (anexos.length && !texto) {
                return "anexos";
            }

            return "mensagens";
        }

        function construirResumoBuscaHistoricoCanonico(item = {}, papel = "ia", autor = "", anexos = []) {
            return [
                autor,
                papel,
                String(item?.tipo || ""),
                String(item?.texto || ""),
                String(item?.data || ""),
                ...anexos.map((anexo) => String(anexo?.nome || "").trim()),
            ]
                .join(" ")
                .toLowerCase();
        }

        function construirItemHistoricoWorkspaceDoPayload(item = {}, index = 0) {
            const papel = obterPapelItemHistoricoCanonico(item);
            const autor = obterAutorItemHistoricoCanonico(item, papel);
            const anexos = extrairAnexosHistoricoCanonico(item);
            const data = obterDataItemHistoricoCanonico(item);
            const tipo = obterTipoRegistroHistoricoCanonico(item, papel, anexos);
            const texto = String(item?.texto || "").replace(/\s+/g, " ").trim();

            return {
                index,
                sortIndex: index,
                origem: "canonico",
                mensagemId: Number(item?.id ?? item?.mensagem_id ?? 0) || null,
                autor,
                papel,
                tempo: String(item?.data || "").trim(),
                texto,
                anexos,
                tipo,
                data,
                grupo: obterRotuloGrupoHistoricoWorkspace(data),
                icone: obterIconeHistoricoWorkspace(tipo, papel),
                resumoBusca: construirResumoBuscaHistoricoCanonico(item, papel, autor, anexos),
                citacoes: Array.isArray(item?.citacoes) ? item.citacoes : [],
                confiancaIa: item?.confianca_ia && typeof item.confianca_ia === "object"
                    ? { ...item.confianca_ia }
                    : null,
            };
        }

        function construirItemHistoricoWorkspaceDoDom(linha, index = 0) {
            const detalhe = obterDetalheLinhaWorkspace(linha);
            const anexos = Array.from(linha.querySelectorAll(".mensagem-anexo-chip"))
                .map((chip, chipIndex) => {
                    const nome = String(
                        chip.querySelector("span:last-child")?.textContent ||
                        chip.textContent ||
                        ""
                    ).replace(/\s+/g, " ").trim();
                    if (!nome) return null;
                    const url = chip.tagName === "A" ? String(chip.getAttribute("href") || "").trim() : "";
                    return {
                        nome,
                        url,
                        tipo: "documento",
                        chave: `dom-${index}-${chipIndex}-${nome}`,
                    };
                })
                .filter(Boolean);
            const data = obterDataLinhaWorkspace(linha);
            const tipo = obterTipoRegistroHistoricoWorkspace(linha, detalhe);
            const papel = detalhe.papel || obterPapelLinhaWorkspace(linha);

            return {
                index,
                sortIndex: 100000 + index,
                origem: "dom",
                mensagemId: detalhe.mensagemId,
                autor: detalhe.autor,
                papel,
                tempo: detalhe.tempo || "",
                texto: detalhe.texto || "",
                anexos,
                tipo,
                data,
                grupo: obterRotuloGrupoHistoricoWorkspace(data),
                icone: obterIconeHistoricoWorkspace(tipo, papel),
                resumoBusca: obterTextoBuscaLinhaWorkspace(linha),
                citacoes: [],
                confiancaIa: null,
            };
        }

        function coletarItensSuplementaresHistoricoWorkspace(itensCanonicos = []) {
            const idsCanonicos = new Set(
                itensCanonicos
                    .map((item) => Number(item?.mensagemId || 0) || null)
                    .filter(Boolean)
            );
            const assinaturasCanonicas = new Set(
                itensCanonicos.map((item) => [
                    item.papel,
                    item.tempo,
                    item.texto,
                    item.anexos.map((anexo) => anexo?.nome || "").join("|"),
                ].join("::"))
            );

            return coletarLinhasWorkspace()
                .map((linha, index) => construirItemHistoricoWorkspaceDoDom(linha, index))
                .filter((item) => {
                    if (item.papel === "sistema") return true;
                    if (!item.mensagemId) return true;
                    if (!idsCanonicos.has(item.mensagemId)) return true;

                    const assinatura = [
                        item.papel,
                        item.tempo,
                        item.texto,
                        item.anexos.map((anexo) => anexo?.nome || "").join("|"),
                    ].join("::");
                    return !assinaturasCanonicas.has(assinatura);
                });
        }

        function construirItensHistoricoWorkspace() {
            const itensCanonicos = obterItensCanonicosHistoricoWorkspace()
                .map((item, index) => construirItemHistoricoWorkspaceDoPayload(item, index));
            const itensSuplementares = coletarItensSuplementaresHistoricoWorkspace(itensCanonicos);

            return [...itensCanonicos, ...itensSuplementares]
                .sort((a, b) => {
                    const dataA = a.data instanceof Date ? a.data.getTime() : null;
                    const dataB = b.data instanceof Date ? b.data.getTime() : null;

                    if (dataA != null && dataB != null && dataA !== dataB) {
                        return dataA - dataB;
                    }
                    if (dataA != null && dataB == null) return -1;
                    if (dataA == null && dataB != null) return 1;
                    return Number(a.sortIndex || a.index || 0) - Number(b.sortIndex || b.index || 0);
                })
                .map((item, index) => ({
                    ...item,
                    index,
                }));
        }

        function itemHistoricoWorkspaceAtendeFiltros(item, { termo = "", ator = "todos", tipo = "todos" } = {}) {
            const matchAtor = ator === "todos" || item.papel === ator;
            const matchTipo = tipo === "todos" || item.tipo === tipo;
            const matchBusca = !termo || item.resumoBusca.includes(termo);
            return matchAtor && matchTipo && matchBusca;
        }

        function montarAtributosHistoricoWorkspace(item = {}) {
            const tipo = normalizarFiltroTipoHistorico(item.tipo);
            const papel = String(item.papel || "sistema").trim().toLowerCase() || "sistema";
            const atributos = [
                'class="workspace-history-card"',
                'data-history-card="true"',
                `data-history-type="${escaparHtml(tipo)}"`,
                `data-history-role="${escaparHtml(papel)}"`,
            ];

            if (Array.isArray(item.anexos) && item.anexos.length) {
                atributos.push('data-history-has-attachments="true"');
            }
            if (String(item.texto || "").trim()) {
                atributos.push('data-history-has-text="true"');
            }

            return atributos.join(" ");
        }

        function montarRotuloTipoHistoricoWorkspace(tipo = "mensagens") {
            if (tipo === "eventos") return "Evento";
            if (tipo === "anexos") return "Anexo";
            if (tipo === "decisoes") return "Decisão";
            return "Mensagem";
        }

        function montarMetadadosIaHistoricoWorkspace(item = {}) {
            const confianca = item?.confiancaIa && typeof item.confiancaIa === "object"
                ? item.confiancaIa
                : null;
            const citacoes = Array.isArray(item?.citacoes) ? item.citacoes : [];
            const nivel = String(
                confianca?.nivel ||
                confianca?.classificacao ||
                confianca?.faixa ||
                ""
            ).trim();
            const proveniencia = String(
                confianca?.proveniência ||
                confianca?.proveniencia ||
                confianca?.fonte ||
                ""
            ).trim();

            if (!nivel && !proveniencia && !citacoes.length) {
                return "";
            }

            return `
                <details class="workspace-history-card__details">
                    <summary>Metadados IA</summary>
                    <div class="workspace-history-card__details-body">
                        ${nivel ? `<span>${escaparHtml(`Confiança ${nivel}`)}</span>` : ""}
                        ${proveniencia ? `<span>${escaparHtml(`Proveniência ${proveniencia}`)}</span>` : ""}
                        ${citacoes.length ? `<span>${escaparHtml(`${citacoes.length} ${citacoes.length === 1 ? "citação" : "citações"}`)}</span>` : ""}
                    </div>
                </details>
            `;
        }

        function sincronizarEstadoVisualHistoricoWorkspace({ vazio = false } = {}) {
            const estadoVisual = vazio ? "empty" : "ready";
            [el.workspaceHistoryRoot, el.workspaceHistoryViewRoot, el.workspaceHistoryTimeline, el.workspaceHistoryEmpty]
                .forEach((node) => {
                    if (node) {
                        node.dataset.historyState = estadoVisual;
                    }
                });
        }

        function renderizarHistoricoWorkspace(itens = [], { totalMensagensReais = 0 } = {}) {
            estado.historyRenderedItems = Array.isArray(itens) ? itens : [];
            const resumoGovernanca = construirResumoGovernancaHistoricoWorkspace();
            const acaoMesaHistorico = resumoGovernanca.visible
                ? { action: "reissue", label: "Reemissão" }
                : { action: "mesa", label: "Mesa" };

            if (!el.workspaceHistoryTimeline || !el.workspaceHistoryEmpty) return;

            if (!estado.historyRenderedItems.length) {
                el.workspaceHistoryTimeline.innerHTML = "";
                el.workspaceHistoryEmpty.hidden = false;
                sincronizarEstadoVisualHistoricoWorkspace({ vazio: true });
                return;
            }

            el.workspaceHistoryEmpty.hidden = true;
            sincronizarEstadoVisualHistoricoWorkspace({ vazio: false });
            const grupos = [];
            let grupoAtual = null;

            estado.historyRenderedItems.forEach((item, itemIndex) => {
                if (!grupoAtual || grupoAtual.rotulo !== item.grupo) {
                    grupoAtual = {
                        rotulo: item.grupo,
                        itens: [],
                    };
                    grupos.push(grupoAtual);
                }

                grupoAtual.itens.push({ ...item, renderIndex: itemIndex });
            });

            el.workspaceHistoryTimeline.innerHTML = grupos
                .map((grupo) => `
                    <section class="workspace-history-group" data-history-group>
                        <header class="workspace-history-group__header" data-history-group-header>
                            <span>${escaparHtml(grupo.rotulo)}</span>
                        </header>
                        <div class="workspace-history-group__items" data-history-group-items>
                            ${grupo.itens.map((item) => `
                                <article ${montarAtributosHistoricoWorkspace(item)} ${resumoGovernanca.visible ? 'data-history-reissue="true"' : ""}>
                                    <div class="workspace-history-card__icon" aria-hidden="true">
                                        <span class="material-symbols-rounded">${escaparHtml(item.icone)}</span>
                                    </div>
                                    <div class="workspace-history-card__body">
                                        <div class="workspace-history-card__meta">
                                            <div class="workspace-history-card__identity">
                                                <strong>${escaparHtml(item.autor || "Registro")}</strong>
                                                <span>${escaparHtml(montarRotuloTipoHistoricoWorkspace(item.tipo))}</span>
                                            </div>
                                            <small>${escaparHtml(item.tempo || "")}</small>
                                        </div>
                                        ${item.texto ? `<p class="workspace-history-card__text">${escaparHtml(item.texto)}</p>` : ""}
                                        ${item.anexos.length ? `
                                            <div class="workspace-history-card__attachments">
                                                ${item.anexos.map((anexo) => {
                                                    const nome = escaparHtml(String(anexo?.nome || "").trim());
                                                    const url = String(anexo?.url || "").trim();
                                                    return url
                                                        ? `<a class="workspace-history-card__attachment" href="${escaparHtml(url)}" target="_blank" rel="noreferrer">${nome}</a>`
                                                        : `<span class="workspace-history-card__attachment">${nome}</span>`;
                                                }).join("")}
                                            </div>
                                        ` : ""}
                                        ${item.papel === "ia" ? montarMetadadosIaHistoricoWorkspace(item) : ""}
                                        ${item.papel === "sistema" || item.tipo === "eventos" ? "" : `
                                            <div class="workspace-history-card__actions">
                                                <button type="button" class="workspace-history-card__action" data-history-action="copiar" data-history-index="${item.renderIndex}">Copiar</button>
                                                <button type="button" class="workspace-history-card__action" data-history-action="fixar" data-history-index="${item.renderIndex}">Fixar</button>
                                                <details class="workspace-history-card__more">
                                                    <summary>Mais</summary>
                                                    <div class="workspace-history-card__more-menu">
                                                        <button type="button" class="workspace-history-card__action" data-history-action="citar" data-history-index="${item.renderIndex}">Citar</button>
                                                        <button type="button" class="workspace-history-card__action" data-history-action="${acaoMesaHistorico.action}" data-history-index="${item.renderIndex}">${acaoMesaHistorico.label}</button>
                                                    </div>
                                                </details>
                                            </div>
                                        `}
                                    </div>
                                </article>
                            `).join("")}
                        </div>
                    </section>
                `)
                .join("");

            if (totalMensagensReais === 0) {
                el.workspaceHistoryEmpty.hidden = false;
            }
        }

        function resetarFiltrosHistoricoWorkspace() {
            estado.chatBuscaTermo = "";
            estado.chatFiltroTimeline = "todos";
            estado.historyTypeFilter = "todos";

            if (el.chatThreadSearch) {
                el.chatThreadSearch.value = "";
            }

            el.chatFilterButtons.forEach((botao) => {
                const ativo = String(botao.dataset.chatFilter || "") === "todos";
                botao.setAttribute("aria-pressed", ativo ? "true" : "false");
            });

            el.historyTypeFilterButtons.forEach((botao) => {
                const ativo = String(botao.dataset.historyTypeFilter || "") === "todos";
                botao.setAttribute("aria-pressed", ativo ? "true" : "false");
            });
        }

        function obterRotuloFiltroAtorHistoricoWorkspace(filtro = "todos") {
            if (filtro === "inspetor") return "Inspetor";
            if (filtro === "ia") return "IA";
            if (filtro === "mesa") return "Mesa";
            if (filtro === "sistema") return "Sistema";
            return "Todos os atores";
        }

        function obterRotuloFiltroTipoHistoricoWorkspace(filtro = "todos") {
            if (filtro === "mensagens") return "Mensagens";
            if (filtro === "eventos") return "Eventos";
            if (filtro === "anexos") return "Anexos";
            if (filtro === "decisoes") return "Decisões";
            return "Todos os tipos";
        }

        function obterDescricaoFonteHistoricoWorkspace() {
            const canonicosEmEstado = Array.isArray(estado.historyCanonicalItems) ? estado.historyCanonicalItems.length : 0;
            const canonicosViaApi = Array.isArray(window.TarielAPI?.obterHistoricoLaudoAtual?.())
                ? window.TarielAPI.obterHistoricoLaudoAtual().length
                : 0;

            return (canonicosEmEstado > 0 || canonicosViaApi > 0)
                ? "Histórico estruturado"
                : "Registros transitórios";
        }

        function renderizarMetaHistoricoWorkspace({ filteredCount, totalCount } = {}) {
            const totalReal = Math.max(0, Number(totalCount ?? estado.historyRealCount ?? 0) || 0);
            const totalFiltrado = Math.max(0, Number(filteredCount ?? estado.chatResultados ?? totalReal) || 0);
            const filtroAtor = obterRotuloFiltroAtorHistoricoWorkspace(normalizarFiltroChat(estado.chatFiltroTimeline));
            const filtroTipo = obterRotuloFiltroTipoHistoricoWorkspace(normalizarFiltroTipoHistorico(estado.historyTypeFilter));
            const busca = String(estado.chatBuscaTermo || "").trim();
            const partes = [];

            if (filtroAtor !== "Todos os atores") {
                partes.push(filtroAtor);
            }
            if (filtroTipo !== "Todos os tipos") {
                partes.push(filtroTipo);
            }
            if (busca) {
                partes.push(`Busca "${busca}"`);
            }

            if (el.workspaceHistorySource) {
                el.workspaceHistorySource.textContent = obterDescricaoFonteHistoricoWorkspace();
            }
            if (el.workspaceHistoryActiveFilter) {
                el.workspaceHistoryActiveFilter.textContent = partes.length ? partes.join(" • ") : "Todos os registros";
            }
            if (el.workspaceHistoryTotal) {
                el.workspaceHistoryTotal.textContent = `${totalReal} ${pluralizarWorkspace(totalReal, "registro real", "registros reais")}`;
            }
            if (el.chatThreadResults && totalFiltrado > totalReal) {
                el.chatThreadResults.textContent = `${totalReal} ${pluralizarWorkspace(totalReal, "registro", "registros")}`;
            }
        }

        function renderizarResultadosChatWorkspace(total = 0) {
            if (!el.chatThreadResults) return;
            const quantidade = Number(total || 0);
            const tabAtual = normalizarThreadTab(obterSnapshotEstadoInspectorAtual().threadTab);
            if (estado.workspaceStage === "assistant" && quantidade === 0) {
                el.chatThreadResults.textContent = "Nova conversa";
                renderizarMetaHistoricoWorkspace({ filteredCount: quantidade });
                return;
            }
            if (tabAtual === "historico" && Number(estado.historyRealCount || 0) === 0) {
                el.chatThreadResults.textContent = "Histórico vazio";
                renderizarMetaHistoricoWorkspace({ filteredCount: quantidade });
                return;
            }
            el.chatThreadResults.textContent = `${quantidade} ${pluralizarWorkspace(quantidade, "registro", "registros")}`;
            renderizarMetaHistoricoWorkspace({ filteredCount: quantidade });
        }

        function copiarTextoWorkspace(texto = "") {
            const valor = String(texto || "").trim();
            if (!valor) return Promise.reject(new Error("TEXTO_VAZIO"));

            if (navigator.clipboard?.writeText) {
                return navigator.clipboard.writeText(valor);
            }

            return new Promise((resolve, reject) => {
                try {
                    const textarea = document.createElement("textarea");
                    textarea.value = valor;
                    textarea.setAttribute("readonly", "");
                    textarea.style.cssText = "position:fixed;left:-9999px;top:0;";
                    document.body.appendChild(textarea);
                    textarea.select();
                    const copiou = !!document.execCommand?.("copy");
                    document.body.removeChild(textarea);
                    if (copiou) {
                        resolve();
                    } else {
                        reject(new Error("COPY_FALHOU"));
                    }
                } catch (erro) {
                    reject(erro);
                }
            });
        }

        function filtrarTimelineWorkspace() {
            const termo = String(estado.chatBuscaTermo || "").trim().toLowerCase();
            const filtro = normalizarFiltroChat(estado.chatFiltroTimeline);
            const tipo = normalizarFiltroTipoHistorico(estado.historyTypeFilter);
            const itens = construirItensHistoricoWorkspace();
            const totalLinhasReais = itens.length;
            const filtrados = itens.filter((item) => itemHistoricoWorkspaceAtendeFiltros(item, {
                termo,
                ator: filtro,
                tipo,
            }));

            sincronizarResumoHistoricoWorkspace({
                totalMensagensReais: totalLinhasReais,
            });
            estado.chatResultados = filtrados.length;
            renderizarResultadosChatWorkspace(filtrados.length);
            renderizarHistoricoWorkspace(filtrados, {
                totalMensagensReais: totalLinhasReais,
            });

            const landingAssistenteAtivo = estado.workspaceStage === "assistant" && filtrados.length === 0;
            if (el.workspaceAssistantLanding) {
                el.workspaceAssistantLanding.hidden = !landingAssistenteAtivo;
            }

            atualizarEmptyStateHonestoConversa();
            sincronizarInspectorScreen();
        }

        Object.assign(ctx.shared, {
            obterItensCanonicosHistoricoWorkspace,
        });

        Object.assign(ctx.actions, {
            copiarTextoWorkspace,
            filtrarTimelineWorkspace,
            normalizarFiltroChat,
            normalizarFiltroTipoHistorico,
            obterDetalheLinhaWorkspace,
            obterItensCanonicosHistoricoWorkspace,
            obterPapelLinhaWorkspace,
            resetarFiltrosHistoricoWorkspace,
        });
    };
})();
