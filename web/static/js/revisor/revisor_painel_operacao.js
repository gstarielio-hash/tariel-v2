// ==========================================
// TARIEL.IA — REVISOR_PAINEL_OPERACAO.JS
// Papel: renderização operacional da mesa no painel do revisor.
// ==========================================

(function () {
    "use strict";

    const NS = window.TarielRevisorPainel;
    if (!NS || NS.__operacaoWired__) return;
    NS.__operacaoWired__ = true;

    const {
        els,
        state,
        escapeHtml,
        formatarDataHora,
        normalizarAnexoMensagem,
        renderizarAnexosMensagem,
        resumoMensagem,
        normalizarCollaborationSummary,
        atualizarIndicadoresListaLaudo,
        sincronizarPlaceholderContextoMesa,
        medirSync,
        snapshotDOM,
        renderizarPainelDocumentoTecnicoInline
    } = NS;

    const obterItemKindMesa = (item) => {
        const valor = String(item?.item_kind || "").trim().toLowerCase();
        if (valor === "pendency" || valor === "whisper" || valor === "message") {
            return valor;
        }
        const tipoLegacy = String(item?.tipo || "").trim().toLowerCase();
        if (tipoLegacy === "humano_eng") return "pendency";
        if (tipoLegacy === "humano_insp") return "whisper";
        return "message";
    };

    const obterPendencyStateMesa = (item) => {
        const valor = String(item?.pendency_state || "").trim().toLowerCase();
        if (valor === "open" || valor === "resolved" || valor === "not_applicable") {
            return valor;
        }
        if (obterItemKindMesa(item) !== "pendency") {
            return "not_applicable";
        }
        return String(item?.resolvida_em || "").trim() ? "resolved" : "open";
    };

    const resolverTipoOperacaoMesa = (item, tipo) => {
        if (tipo === "whisper") return "whisper";
        if (tipo === "resolvida") return "resolvida";
        if (tipo === "aberta") return "aberta";
        const itemKind = obterItemKindMesa(item);
        if (itemKind === "whisper") return "whisper";
        return obterPendencyStateMesa(item) === "resolved" ? "resolvida" : "aberta";
    };

    const renderizarItemOperacaoMesa = (item, { tipo = "aberta", permitirResponder = false } = {}) => {
        const tipoResolvido = resolverTipoOperacaoMesa(item, tipo);
        const mensagemId = Number(item?.id || 0);
        const referenciaId = Number(item?.referencia_mensagem_id || 0);
        const dataBase = tipoResolvido === "resolvida" ? item?.resolvida_em : item?.criado_em;
        const dataLabel = formatarDataHora(dataBase || item?.criado_em);
        const anexos = Array.isArray(item?.anexos) ? item.anexos.map(normalizarAnexoMensagem).filter(Boolean) : [];
        const texto = resumoMensagem(item?.texto || (anexos.length ? "Anexo enviado" : ""));
        const resolvedorNome = String(item?.resolvida_por_nome || "").trim();
        const titulo = tipoResolvido === "whisper"
            ? `Chamado #${mensagemId || "-"}`
            : `Mensagem #${mensagemId || "-"}`;
        const chipTexto = tipoResolvido === "resolvida"
            ? "Resolvida"
            : tipoResolvido === "whisper"
                ? "Chamado"
                : "Aberta";
        const subtitulo = tipoResolvido === "resolvida"
            ? `Resolvida em ${escapeHtml(dataLabel)}`
            : `Criada em ${escapeHtml(dataLabel)}`;
        const contextoBotao = referenciaId > 0
            ? `
                <button type="button" class="btn-mesa-acao" data-mesa-action="timeline-ref" data-ref-id="${referenciaId}">
                    <span class="material-symbols-rounded" aria-hidden="true">format_quote</span>
                    <span>Ver contexto</span>
                </button>
            `
            : "";
        const responderBotao = permitirResponder && mensagemId > 0
            ? `
                <button type="button" class="btn-mesa-acao" data-mesa-action="responder-item" data-msg-id="${mensagemId}">
                    <span class="material-symbols-rounded" aria-hidden="true">reply</span>
                    <span>Responder</span>
                </button>
            `
            : "";
        const botaoPendencia = mensagemId > 0 && tipoResolvido !== "whisper"
            ? `
                <button
                    type="button"
                    class="btn-mesa-acao"
                    data-mesa-action="alternar-pendencia"
                    data-msg-id="${mensagemId}"
                    data-proxima-lida="${tipoResolvido === "aberta" ? "true" : "false"}"
                >
                    <span class="material-symbols-rounded" aria-hidden="true">${tipoResolvido === "aberta" ? "task_alt" : "restart_alt"}</span>
                    <span>${tipoResolvido === "aberta" ? "Marcar resolvida" : "Reabrir"}</span>
                </button>
            `
            : "";

        return `
            <li class="mesa-operacao-item ${escapeHtml(tipoResolvido)}">
                <div class="mesa-operacao-item-topo">
                    <strong>${escapeHtml(titulo)}</strong>
                    <span class="mesa-operacao-chip ${escapeHtml(tipoResolvido)}">${escapeHtml(chipTexto)}</span>
                </div>
                <p>${escapeHtml(texto)}</p>
                ${renderizarAnexosMensagem(anexos)}
                <div class="mesa-operacao-meta">
                    <span>${subtitulo}</span>
                    ${referenciaId > 0 ? `<span>Ref. #${escapeHtml(String(referenciaId))}</span>` : "<span>Sem referência explícita</span>"}
                    ${tipoResolvido === "resolvida" && resolvedorNome ? `<span>Resolvida por ${escapeHtml(resolvedorNome)}</span>` : ""}
                </div>
                <div class="mesa-operacao-acoes">
                    <button type="button" class="btn-mesa-acao" data-mesa-action="timeline-msg" data-msg-id="${mensagemId}">
                        <span class="material-symbols-rounded" aria-hidden="true">forum</span>
                        <span>Ir para historico</span>
                    </button>
                    ${contextoBotao}
                    ${botaoPendencia}
                    ${responderBotao}
                </div>
            </li>
        `;
    };

    const renderizarColunaOperacaoMesa = ({
        titulo,
        itens = [],
        tipo = "aberta",
        mensagemVazia,
        permitirResponder = false
    }) => {
        const lista = Array.isArray(itens) ? itens : [];
        const corpo = lista.length
            ? `
                <ul class="mesa-operacao-lista">
                    ${lista.slice(0, 5).map((item) => renderizarItemOperacaoMesa(item, { tipo, permitirResponder })).join("")}
                </ul>
            `
            : `<p class="mesa-operacao-vazio">${escapeHtml(mensagemVazia || "Sem registros no momento.")}</p>`;

        return `
            <section class="mesa-operacao-coluna">
                <header>
                    <h4>${escapeHtml(titulo)}</h4>
                    <span class="mesa-operacao-contagem">${escapeHtml(String(lista.length))}</span>
                </header>
                ${corpo}
            </section>
        `;
    };

    const obterResumoStatusOperacaoMesa = (collaboration) => {
        const abertas = Number(collaboration?.openPendencyCount || 0) || 0;
        const resolvidas = Number(collaboration?.resolvedPendencyCount || 0) || 0;

        if (abertas > 0) {
            return {
                icone: "assignment_late",
                rotulo: abertas === 1 ? "1 pendência aberta" : `${abertas} pendências abertas`,
                descricao: "Há itens da mesa aguardando retorno do campo neste laudo.",
            };
        }

        if (resolvidas > 0) {
            return {
                icone: "task_alt",
                rotulo: "Fluxo com resoluções recentes",
                descricao: "A mesa já recebeu retorno do campo e não há pendências abertas agora.",
            };
        }

        return {
            icone: "hourglass_top",
            rotulo: "Canal em triagem",
            descricao: "Sem pendencias abertas no momento. Acompanhe novas mensagens e chamados do laudo.",
        };
    };

    const renderizarPainelMesaOperacional = (pacote) => {
        medirSync("revisor.renderizarPainelMesaOperacional", () => {
            if (!els.mesaOperacaoPainel || !els.mesaOperacaoConteudo) return;

            if (!pacote || typeof pacote !== "object") {
                els.mesaOperacaoPainel.hidden = true;
                els.mesaOperacaoConteudo.innerHTML = "";
                renderizarPainelDocumentoTecnicoInline(null);
                sincronizarPlaceholderContextoMesa?.();
                return;
            }

            const resumoPendencias = pacote.resumo_pendencias || {};
            const ultimaInteracao = formatarDataHora(pacote.ultima_interacao_em);
            const criadoEm = formatarDataHora(pacote.criado_em);
            const totalWhispersRecentes = Array.isArray(pacote.whispers_recentes) ? pacote.whispers_recentes.length : 0;
            const collaboration = normalizarCollaborationSummary(pacote, {
                pendenciasAbertas: Number(resumoPendencias.abertas || 0) || 0,
                resolvedPendencyCount: Number(resumoPendencias.resolvidas || 0) || 0,
                recentWhisperCount: totalWhispersRecentes
            });
            const totalWhispers = collaboration.recentWhisperCount;
            const statusOperacional = obterResumoStatusOperacaoMesa(collaboration);
            atualizarIndicadoresListaLaudo(state.laudoAtivoId, {
                collaborationSummary: pacote?.collaboration?.summary || {
                    open_pendency_count: collaboration.openPendencyCount,
                    resolved_pendency_count: collaboration.resolvedPendencyCount,
                    recent_whisper_count: collaboration.recentWhisperCount,
                    unread_whisper_count: collaboration.unreadWhisperCount,
                    recent_review_count: collaboration.recentReviewCount,
                    has_open_pendencies: collaboration.hasOpenPendencies,
                    has_recent_whispers: collaboration.hasRecentWhispers,
                    requires_reviewer_attention: collaboration.requiresReviewerAttention
                }
            });

            els.mesaOperacaoConteudo.innerHTML = `
                <div class="mesa-operacao-topo">
                    <div>
                        <h3>Operação da Mesa</h3>
                        <p>${escapeHtml(statusOperacional.descricao)}</p>
                    </div>
                    <span class="mesa-operacao-tag">
                        <span class="material-symbols-rounded" aria-hidden="true">${escapeHtml(statusOperacional.icone)}</span>
                        <span>${escapeHtml(statusOperacional.rotulo)}</span>
                    </span>
                </div>

                <div class="mesa-operacao-resumo">
                    <article class="mesa-operacao-kpi">
                        <span>Pendências abertas</span>
                        <strong>${escapeHtml(String(collaboration.openPendencyCount || 0))}</strong>
                        <small>Mensagens da mesa ainda em aberto para o inspetor.</small>
                    </article>
                    <article class="mesa-operacao-kpi">
                        <span>Resolvidas</span>
                        <strong>${escapeHtml(String(collaboration.resolvedPendencyCount || 0))}</strong>
                        <small>Itens já encerrados pelo fluxo em campo.</small>
                    </article>
                    <article class="mesa-operacao-kpi">
                        <span>Última interação</span>
                        <strong>${escapeHtml(ultimaInteracao)}</strong>
                        <small>Laudo iniciado em ${escapeHtml(criadoEm)}.</small>
                    </article>
                    <article class="mesa-operacao-kpi">
                        <span>Tempo em campo</span>
                        <strong>${escapeHtml(String(pacote.tempo_em_campo_minutos || 0))} min</strong>
                        <small>${escapeHtml(String(totalWhispers))} chamado(s) recente(s) no canal.</small>
                    </article>
                </div>

                <div class="mesa-operacao-insights">
                    ${NS.renderizarGovernancaPolicyMesa?.(pacote.policy_summary) || ""}
                    ${NS.renderizarRevisaoPorBlocoMesa?.(pacote.revisao_por_bloco) || ""}
                    ${NS.renderizarCoverageMapMesa?.(pacote.coverage_map) || ""}
                    ${NS.renderizarHistoricoInspecaoMesa?.(pacote.historico_inspecao) || ""}
                    ${NS.renderizarVerificacaoPublicaMesa?.(pacote.verificacao_publica) || ""}
                    ${NS.renderizarAnexoPackMesa?.(pacote.anexo_pack) || ""}
                    ${NS.renderizarEmissaoOficialMesa?.(pacote.emissao_oficial) || ""}
                    ${NS.renderizarHistoricoRefazerInspetor?.(pacote.historico_refazer_inspetor) || ""}
                    ${NS.renderizarMemoriaOperacionalFamilia?.(pacote.memoria_operacional_familia) || ""}
                </div>

                <div class="mesa-operacao-grid">
                    ${renderizarColunaOperacaoMesa({
                        titulo: "Pendências abertas",
                        itens: pacote.pendencias_abertas,
                        tipo: "aberta",
                        mensagemVazia: "Nenhuma pendência aberta neste momento.",
                        permitirResponder: true
                    })}
                    ${renderizarColunaOperacaoMesa({
                        titulo: "Resolvidas recentes",
                        itens: pacote.pendencias_resolvidas_recentes,
                        tipo: "resolvida",
                        mensagemVazia: "Ainda não há resoluções recentes para este laudo.",
                        permitirResponder: false
                    })}
                    ${renderizarColunaOperacaoMesa({
                        titulo: "Chamados recentes",
                        itens: pacote.whispers_recentes,
                        tipo: "whisper",
                        mensagemVazia: "Nenhum chamado recente registrado.",
                        permitirResponder: true
                    })}
                </div>
            `;

            els.mesaOperacaoPainel.hidden = false;
            renderizarPainelDocumentoTecnicoInline(pacote);
            sincronizarPlaceholderContextoMesa?.();
            snapshotDOM(`revisor:painel-mesa:${Number(state.laudoAtivoId || 0) || 0}`);
        }, { laudoId: Number(state.laudoAtivoId || 0) || 0 }, "render");
    };

    Object.assign(NS, {
        renderizarItemOperacaoMesa,
        renderizarColunaOperacaoMesa,
        obterResumoStatusOperacaoMesa,
        renderizarPainelMesaOperacional
    });
})();
