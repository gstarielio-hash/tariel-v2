(function () {
    "use strict";

    const inspectorRuntime = window.TarielInspectorRuntime || null;
    const modules = typeof inspectorRuntime?.resolveModuleBucket === "function"
        ? inspectorRuntime.resolveModuleBucket("TarielInspetorModules")
        : (window.TarielInspetorModules = window.TarielInspetorModules || {});

    modules.registerWorkspaceDerivatives = function registerWorkspaceDerivatives(ctx) {
        const estado = ctx.state;
        const el = ctx.elements;
        const {
            escaparHtml,
            normalizarThreadTab,
            normalizarWorkspaceStage,
            obterItensCanonicosHistoricoWorkspace,
            pluralizarWorkspace,
        } = ctx.shared;

        function construirResumoHistoricoWorkspace(detail = {}) {
            const payload = detail && typeof detail === "object" ? detail : {};
            const historicoCanonico = obterItensCanonicosHistoricoWorkspace();
            const fallbackHistorico = historicoCanonico.length > 0
                ? historicoCanonico.length
                : ctx.actions.coletarLinhasWorkspace?.().length || 0;
            const totalMensagensReais = Math.max(
                0,
                Number(
                    payload.totalMensagensReais ??
                    payload.total_mensagens_reais ??
                    fallbackHistorico
                ) || 0
            );

            return {
                totalMensagensReais,
                historicoVazio: totalMensagensReais === 0,
                teveFillersSinteticos: false,
                possuiEmptyStateHonesto: totalMensagensReais === 0,
            };
        }

        function espelharResumoHistoricoWorkspaceNoDataset(resumo = {}) {
            const body = document.body;
            const painel = el.painelChat;
            const historicoVazio = resumo.historicoVazio ? "1" : "0";
            const totalMensagensReais = String(Number(resumo.totalMensagensReais || 0) || 0);
            const emptyStateHonesto = resumo.possuiEmptyStateHonesto ? "1" : "0";

            body.dataset.historyEmpty = historicoVazio;
            body.dataset.historyRealCount = totalMensagensReais;
            body.dataset.historySynthetic = "0";
            body.dataset.historyHonestEmpty = emptyStateHonesto;

            if (painel) {
                painel.dataset.historyEmpty = historicoVazio;
                painel.dataset.historyRealCount = totalMensagensReais;
                painel.dataset.historySynthetic = "0";
                painel.dataset.historyHonestEmpty = emptyStateHonesto;
            }
        }

        function sincronizarResumoHistoricoWorkspace(detail = {}) {
            const resumo = construirResumoHistoricoWorkspace(detail);
            estado.historyRealCount = resumo.totalMensagensReais;
            estado.historyEmpty = resumo.historicoVazio;
            estado.historySynthetic = false;
            estado.historyHonestEmpty = resumo.possuiEmptyStateHonesto;
            espelharResumoHistoricoWorkspaceNoDataset(resumo);
            return resumo;
        }

        function construirResumoPendenciasWorkspace(detail = {}) {
            const payload = detail && typeof detail === "object" ? detail : {};
            const laudoId = Number(
                payload.laudoId ??
                payload.laudo_id ??
                estado.laudoPendenciasAtual ??
                0
            ) || 0;
            const totalPendenciasReais = Math.max(
                0,
                Number(
                    payload.totalPendenciasReais ??
                    payload.total_pendencias_reais ??
                    estado.totalPendenciasExibidas ??
                    0
                ) || 0
            );
            const totalPendenciasFiltradas = Math.max(
                0,
                Number(
                    payload.totalPendenciasFiltradas ??
                    payload.total_filtrado ??
                    estado.totalPendenciasFiltradas ??
                    totalPendenciasReais
                ) || 0
            );
            const totalPendenciasAbertas = Math.max(
                0,
                Number(
                    payload.totalPendenciasAbertas ??
                    payload.abertas ??
                    estado.qtdPendenciasAbertas ??
                    0
                ) || 0
            );
            const carregando = Boolean(payload.carregando ?? estado.pendenciasLoading);
            const erro = Boolean(payload.erro ?? estado.pendenciasError);
            const pendenciasVazias = laudoId > 0 && !carregando && !erro && totalPendenciasFiltradas === 0;
            const estadoVisual = erro
                ? "error"
                : carregando
                    ? "loading"
                    : totalPendenciasReais > 0
                        ? "list"
                        : pendenciasVazias
                            ? "empty"
                            : "idle";

            return {
                laudoId,
                totalPendenciasReais,
                totalPendenciasFiltradas,
                totalPendenciasAbertas,
                carregando,
                erro,
                pendenciasVazias,
                tevePlaceholdersSinteticos: false,
                possuiEmptyStateHonesto: estadoVisual === "empty",
                estadoVisual,
            };
        }

        function espelharResumoPendenciasWorkspaceNoDataset(resumo = {}) {
            const body = document.body;
            const painel = el.painelChat;
            const painelPendencias = el.painelPendenciasMesa;
            const totalPendenciasReais = String(Number(resumo.totalPendenciasReais || 0) || 0);
            const totalPendenciasFiltradas = String(Number(resumo.totalPendenciasFiltradas || 0) || 0);
            const totalPendenciasAbertas = String(Number(resumo.totalPendenciasAbertas || 0) || 0);
            const pendenciasVazias = resumo.pendenciasVazias ? "1" : "0";
            const pendenciasErro = resumo.erro ? "1" : "0";
            const pendenciasCarregando = resumo.carregando ? "1" : "0";
            const pendenciasHonestEmpty = resumo.possuiEmptyStateHonesto ? "1" : "0";
            const estadoVisual = String(resumo.estadoVisual || "idle");

            body.dataset.pendenciasCount = totalPendenciasReais;
            body.dataset.pendenciasFilteredTotal = totalPendenciasFiltradas;
            body.dataset.pendenciasOpenCount = totalPendenciasAbertas;
            body.dataset.pendenciasEmpty = pendenciasVazias;
            body.dataset.pendenciasSynthetic = "0";
            body.dataset.pendenciasError = pendenciasErro;
            body.dataset.pendenciasLoading = pendenciasCarregando;
            body.dataset.pendenciasHonestEmpty = pendenciasHonestEmpty;
            body.dataset.pendenciasState = estadoVisual;

            if (painel) {
                painel.dataset.pendenciasCount = totalPendenciasReais;
                painel.dataset.pendenciasFilteredTotal = totalPendenciasFiltradas;
                painel.dataset.pendenciasOpenCount = totalPendenciasAbertas;
                painel.dataset.pendenciasEmpty = pendenciasVazias;
                painel.dataset.pendenciasSynthetic = "0";
                painel.dataset.pendenciasError = pendenciasErro;
                painel.dataset.pendenciasLoading = pendenciasCarregando;
                painel.dataset.pendenciasHonestEmpty = pendenciasHonestEmpty;
                painel.dataset.pendenciasState = estadoVisual;
            }

            if (painelPendencias) {
                painelPendencias.dataset.pendenciasCount = totalPendenciasReais;
                painelPendencias.dataset.pendenciasFilteredTotal = totalPendenciasFiltradas;
                painelPendencias.dataset.pendenciasOpenCount = totalPendenciasAbertas;
                painelPendencias.dataset.pendenciasEmpty = pendenciasVazias;
                painelPendencias.dataset.pendenciasSynthetic = "0";
                painelPendencias.dataset.pendenciasError = pendenciasErro;
                painelPendencias.dataset.pendenciasLoading = pendenciasCarregando;
                painelPendencias.dataset.pendenciasHonestEmpty = pendenciasHonestEmpty;
                painelPendencias.dataset.pendenciasState = estadoVisual;
                painelPendencias.setAttribute("aria-busy", resumo.carregando ? "true" : "false");
            }
        }

        function sincronizarResumoPendenciasWorkspace(detail = {}) {
            const resumo = construirResumoPendenciasWorkspace(detail);
            estado.pendenciasRealCount = resumo.totalPendenciasReais;
            estado.pendenciasFilteredCount = resumo.totalPendenciasFiltradas;
            estado.pendenciasLoading = resumo.carregando;
            estado.pendenciasEmpty = resumo.pendenciasVazias;
            estado.pendenciasSynthetic = false;
            estado.pendenciasHonestEmpty = resumo.possuiEmptyStateHonesto;
            estado.pendenciasError = resumo.erro;
            espelharResumoPendenciasWorkspaceNoDataset(resumo);
            return resumo;
        }

        function atualizarEmptyStateHonestoConversa() {
            if (!el.workspaceConversationEmpty) return;

            const snapshot = ctx.actions.obterSnapshotEstadoInspectorAtual?.() || {};
            const tabAtual = normalizarThreadTab(snapshot.threadTab);
            const stageAtual = normalizarWorkspaceStage(snapshot.workspaceStage);
            const viewAtual = ctx.actions.resolveWorkspaceView?.(
                snapshot.inspectorScreen || ctx.actions.resolveInspectorScreen?.()
            );
            const mostrar =
                stageAtual !== "assistant" &&
                viewAtual === "inspection_conversation" &&
                tabAtual === "conversa" &&
                estado.historyRealCount === 0;

            el.workspaceConversationEmpty.hidden = !mostrar;
            el.workspaceConversationEmpty.setAttribute("aria-hidden", String(!mostrar));
        }

        function extrairMetaLinhaWorkspace(linha) {
            const autor = String(linha?.querySelector(".mensagem-meta strong")?.textContent || "").trim() || "Registro";
            const tempo = String(linha?.querySelector(".mensagem-meta time")?.textContent || "").trim() || "";
            const resumo = String(linha?.querySelector(".texto-msg")?.textContent || "").replace(/\s+/g, " ").trim();
            return { autor, tempo, resumo };
        }

        function coletarAnexosWorkspaceDoDom() {
            const vistos = new Set();
            const itens = [];

            (ctx.actions.coletarLinhasWorkspace?.() || []).forEach((linha, linhaIndex) => {
                const meta = extrairMetaLinhaWorkspace(linha);

                linha.querySelectorAll(".img-anexo").forEach((imagem, imagemIndex) => {
                    const url = String(imagem?.getAttribute("src") || "").trim();
                    if (!url) return;

                    const chave = `img::${url}::${meta.autor}::${meta.tempo}`;
                    if (vistos.has(chave)) return;
                    vistos.add(chave);

                    itens.push({
                        tipo: "imagem",
                        nome: `evidencia-${linhaIndex + 1}-${imagemIndex + 1}.jpg`,
                        url,
                        autor: meta.autor,
                        tempo: meta.tempo,
                        resumo: meta.resumo,
                    });
                });

                linha.querySelectorAll(".mensagem-anexo-chip").forEach((chip) => {
                    const nome = String(chip.querySelector("span:last-child")?.textContent || chip.textContent || "").trim();
                    const icone = String(chip.querySelector(".material-symbols-rounded")?.textContent || "").trim();
                    const url = chip.tagName === "A" ? String(chip.getAttribute("href") || "").trim() : "";
                    const tipo = icone === "image" ? "imagem" : "documento";
                    const chave = `${tipo}::${nome}::${url}::${meta.autor}::${meta.tempo}`;

                    if (!nome || vistos.has(chave)) return;
                    vistos.add(chave);

                    itens.push({
                        tipo,
                        nome,
                        url,
                        autor: meta.autor,
                        tempo: meta.tempo,
                        resumo: meta.resumo,
                    });
                });
            });

            return itens;
        }

        function contarEvidenciasWorkspace() {
            const historico = Array.isArray(window.TarielAPI?.obterHistoricoLaudoAtual?.())
                ? window.TarielAPI.obterHistoricoLaudoAtual()
                : [];

            const mensagensUsuario = historico.filter((item) => String(item?.papel || "").toLowerCase() === "usuario");
            const anexos = coletarAnexosWorkspaceDoDom();
            return Math.max(mensagensUsuario.length + anexos.length, anexos.length, 0);
        }

        function construirAtividadeWorkspace() {
            const itens = [];
            const linhas = ctx.actions.coletarLinhasWorkspace?.() || [];
            const linhasReversas = [...linhas].reverse();

            const ultimaLinhaUsuario = linhasReversas.find((linha) => {
                const autor = extrairMetaLinhaWorkspace(linha).autor.toLowerCase();
                return autor !== "assistente ia" && autor !== "sistema";
            });
            if (ultimaLinhaUsuario) {
                const meta = extrairMetaLinhaWorkspace(ultimaLinhaUsuario);
                const possuiAnexo = !!ultimaLinhaUsuario.querySelector(".mensagem-anexo-chip, .img-anexo");
                itens.push({
                    titulo: possuiAnexo ? "Evidência adicionada" : "Registro atualizado",
                    tempo: meta.tempo || "agora",
                });
            }

            const pendenciaRecente = Array.isArray(estado.pendenciasItens) ? estado.pendenciasItens[0] : null;
            if (pendenciaRecente) {
                const aberta = !pendenciaRecente?.lida;
                itens.push({
                    titulo: aberta ? "Pendência criada" : "Pendência resolvida",
                    tempo: String(
                        pendenciaRecente?.data_label ||
                        pendenciaRecente?.resolvida_em_label ||
                        ""
                    ).trim() || "agora",
                });
            }

            const ultimaLinhaAssistente = linhasReversas.find((linha) => {
                const autor = extrairMetaLinhaWorkspace(linha).autor.toLowerCase();
                return autor === "assistente ia";
            });
            if (ultimaLinhaAssistente) {
                const meta = extrairMetaLinhaWorkspace(ultimaLinhaAssistente);
                itens.push({
                    titulo: "Resumo gerado",
                    tempo: meta.tempo || "agora",
                });
            }

            const primeiraLinha = linhas[0];
            if (primeiraLinha) {
                const meta = extrairMetaLinhaWorkspace(primeiraLinha);
                itens.push({
                    titulo: "Sessão iniciada",
                    tempo: meta.tempo || "agora",
                });
            }

            return itens.slice(0, 4);
        }

        function renderizarAtividadeWorkspace() {
            if (!el.workspaceActivityList) return;

            const atividade = construirAtividadeWorkspace();
            if (!atividade.length) {
                el.workspaceActivityList.innerHTML = `
                    <li>
                        <span></span>
                        <div>
                            <strong>Nenhuma atividade recente</strong>
                            <small>O histórico do laudo aparecerá aqui.</small>
                        </div>
                    </li>
                `;
                return;
            }

            el.workspaceActivityList.innerHTML = atividade
                .map((item) => `
                    <li>
                        <span></span>
                        <div>
                            <strong>${escaparHtml(item.titulo)}</strong>
                            <small>${escaparHtml(item.tempo)}</small>
                        </div>
                    </li>
                `)
                .join("");
        }

        function renderizarProgressoWorkspace() {
            const evidencias = contarEvidenciasWorkspace();
            const pendencias = Number(estado.qtdPendenciasAbertas || 0) || 0;
            const estadoRelatorio = ctx.actions.obterEstadoRelatorioAtualSeguro?.();

            let percentual = Math.min(92, 18 + (evidencias * 12));
            if (pendencias === 0) {
                percentual += 8;
            }
            if (estadoRelatorio === "aguardando") {
                percentual = Math.max(percentual, 85);
            } else if (estadoRelatorio === "aprovado") {
                percentual = 100;
            } else if (estadoRelatorio === "ajustes") {
                percentual = Math.max(percentual, 72);
            }
            percentual = Math.max(12, Math.min(100, percentual));

            if (el.workspaceProgressPercent) {
                el.workspaceProgressPercent.textContent = `${percentual}%`;
            }
            if (el.workspaceProgressBar) {
                el.workspaceProgressCard?.style.setProperty("--workspace-progress-percent", `${percentual}%`);
                el.workspaceProgressCard?.setAttribute("data-progress-state", String(estadoRelatorio || "sem_relatorio"));
                el.workspaceProgressBar.parentElement?.setAttribute("aria-valuenow", String(percentual));
            }
            if (el.workspaceProgressEvidencias) {
                el.workspaceProgressEvidencias.textContent = `${evidencias} ${pluralizarWorkspace(evidencias, "evidência", "evidências")}`;
            }
            if (el.workspaceProgressPendencias) {
                el.workspaceProgressPendencias.textContent = `${pendencias} ${pluralizarWorkspace(pendencias, "pendência", "pendências")}`;
            }
        }

        function renderizarAnexosWorkspace() {
            if (!el.workspaceAnexosGrid || !el.workspaceAnexosPanel) return;

            const anexos = coletarAnexosWorkspaceDoDom();
            const total = anexos.length;
            const rotuloTotal = `${total} ${pluralizarWorkspace(total, "item", "itens")}`;

            if (el.workspaceAnexosCount) {
                el.workspaceAnexosCount.textContent = rotuloTotal;
            }

            if (!total) {
                el.workspaceAnexosGrid.innerHTML = "";
                if (el.workspaceAnexosEmpty) {
                    el.workspaceAnexosEmpty.hidden = false;
                }
                return;
            }

            if (el.workspaceAnexosEmpty) {
                el.workspaceAnexosEmpty.hidden = true;
            }

            el.workspaceAnexosGrid.innerHTML = anexos
                .map((item) => {
                    const icone = item.tipo === "imagem" ? "image" : "description";
                    const tag = item.url ? "a" : "div";
                    const atributos = item.url
                        ? `href="${escaparHtml(item.url)}" target="_blank" rel="noopener noreferrer"`
                        : "";
                    const thumbnail = item.tipo === "imagem" && item.url
                        ? `<img src="${escaparHtml(item.url)}" alt="${escaparHtml(item.nome)}">`
                        : `<span class="material-symbols-rounded" aria-hidden="true">${icone}</span>`;

                    return `
                        <${tag} class="workspace-anexo-card workspace-anexo-card--${item.tipo}" ${atributos}>
                            <div class="workspace-anexo-card__media">${thumbnail}</div>
                            <div class="workspace-anexo-card__body">
                                <strong>${escaparHtml(item.nome)}</strong>
                                <p>${escaparHtml(item.resumo || item.autor || "Registro técnico")}</p>
                                <div class="workspace-anexo-card__meta">
                                    <span>${escaparHtml(item.autor || "Registro")}</span>
                                    <small>${escaparHtml(item.tempo || "agora")}</small>
                                </div>
                            </div>
                        </${tag}>
                    `;
                })
                .join("");
        }

        function atualizarPainelWorkspaceDerivado() {
            if (estado.atualizandoPainelWorkspaceDerivado) {
                estado.atualizarPainelWorkspaceDerivadoPendente = true;
                return;
            }

            estado.atualizandoPainelWorkspaceDerivado = true;

            try {
                sincronizarResumoHistoricoWorkspace();
                sincronizarResumoPendenciasWorkspace();
                ctx.actions.decorarLinhasWorkspace?.();
                renderizarAnexosWorkspace();
                renderizarProgressoWorkspace();
                renderizarAtividadeWorkspace();
                ctx.actions.renderizarContextoIAWorkspace?.();
                ctx.actions.renderizarMesaCardWorkspace?.();
                ctx.actions.renderizarWorkspacePublicVerification?.();
                ctx.actions.renderizarWorkspaceOfficialIssue?.();
                ctx.actions.renderizarResumoExecutivoWorkspace?.();
                ctx.actions.renderizarGovernancaEntradaInspetor?.();
                ctx.actions.renderizarGovernancaHistoricoWorkspace?.();
                ctx.actions.renderizarResumoNavegacaoWorkspace?.();
                ctx.actions.filtrarTimelineWorkspace?.();
            } finally {
                estado.atualizandoPainelWorkspaceDerivado = false;

                if (estado.atualizarPainelWorkspaceDerivadoPendente) {
                    estado.atualizarPainelWorkspaceDerivadoPendente = false;
                    window.requestAnimationFrame(() => {
                        atualizarPainelWorkspaceDerivado();
                    });
                }
            }
        }

        Object.assign(ctx.actions, {
            atualizarEmptyStateHonestoConversa,
            atualizarPainelWorkspaceDerivado,
            contarEvidenciasWorkspace,
            extrairMetaLinhaWorkspace,
            renderizarAnexosWorkspace,
            renderizarAtividadeWorkspace,
            renderizarProgressoWorkspace,
            sincronizarResumoHistoricoWorkspace,
            sincronizarResumoPendenciasWorkspace,
        });
    };
})();
