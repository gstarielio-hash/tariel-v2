(function () {
    "use strict";

    if (window.TarielClientePortalChatSurface) return;

    window.TarielClientePortalChatSurface = function createTarielClientePortalChatSurface(config = {}) {
        const state = config.state || {};
        const documentRef = config.documentRef || document;
        const $ = typeof config.getById === "function"
            ? config.getById
            : (id) => documentRef.getElementById(id);
        const helpers = config.helpers || {};
        const filters = config.filters || {};

        const api = typeof helpers.api === "function" ? helpers.api : async () => null;
        const escapeAttr = typeof helpers.escapeAttr === "function" ? helpers.escapeAttr : (valor) => String(valor ?? "");
        const escapeHtml = typeof helpers.escapeHtml === "function" ? helpers.escapeHtml : (valor) => String(valor ?? "");
        const feedback = typeof helpers.feedback === "function" ? helpers.feedback : () => null;
        const formatarCapacidadeRestante = typeof helpers.formatarCapacidadeRestante === "function" ? helpers.formatarCapacidadeRestante : () => "";
        const formatarInteiro = typeof helpers.formatarInteiro === "function" ? helpers.formatarInteiro : (valor) => String(Number(valor || 0));
        const horasDesdeAtualizacao = typeof helpers.horasDesdeAtualizacao === "function" ? helpers.horasDesdeAtualizacao : () => 0;
        const laudoBadge = typeof helpers.laudoBadge === "function" ? helpers.laudoBadge : () => "";
        const laudoChatParado = typeof helpers.laudoChatParado === "function" ? helpers.laudoChatParado : () => false;
        const ordenarPorPrioridade = typeof helpers.ordenarPorPrioridade === "function" ? helpers.ordenarPorPrioridade : (lista) => [...(lista || [])];
        const parseDataIso = typeof helpers.parseDataIso === "function" ? helpers.parseDataIso : () => 0;
        const prioridadeChat = typeof helpers.prioridadeChat === "function" ? helpers.prioridadeChat : () => ({ tone: "aprovado", badge: "", acao: "" });
        const renderAnexos = typeof helpers.renderAnexos === "function" ? helpers.renderAnexos : () => "";
        const resumoEsperaHoras = typeof helpers.resumoEsperaHoras === "function" ? helpers.resumoEsperaHoras : () => "";
        const rotuloSituacaoChat = typeof helpers.rotuloSituacaoChat === "function" ? helpers.rotuloSituacaoChat : () => "";
        const texto = typeof helpers.texto === "function" ? helpers.texto : (valor) => (valor == null ? "" : String(valor));
        const textoComQuebras = typeof helpers.textoComQuebras === "function" ? helpers.textoComQuebras : (valor) => escapeHtml(valor);
        const tomCapacidadeEmpresa = typeof helpers.tomCapacidadeEmpresa === "function" ? helpers.tomCapacidadeEmpresa : () => "aprovado";
        const sincronizarUrlDaSecao = typeof helpers.sincronizarUrlDaSecao === "function" ? helpers.sincronizarUrlDaSecao : () => null;
        const variantStatusLaudo = typeof helpers.variantStatusLaudo === "function" ? helpers.variantStatusLaudo : () => "aberto";
        const withBusy = typeof helpers.withBusy === "function" ? helpers.withBusy : async (_target, _busyText, callback) => callback();

        const filtrarLaudosChat = typeof filters.filtrarLaudosChat === "function" ? filters.filtrarLaudosChat : () => [];
        const SECTION_ORDER = Object.freeze(["overview", "new", "queue", "case"]);
        const SECTION_META = Object.freeze({
            overview: Object.freeze({
                title: "Visao geral",
                meta: "Radar e prioridades do chat.",
            }),
            new: Object.freeze({
                title: "Novo laudo",
                meta: "Abertura isolada da conversa ativa.",
            }),
            queue: Object.freeze({
                title: "Fila operacional",
                meta: "Busca e selecao do caso certo.",
            }),
            case: Object.freeze({
                title: "Caso ativo",
                meta: "Contexto e conversa como foco principal.",
            }),
        });
        const TARGET_TO_SECTION = Object.freeze({
            "chat-overview": "overview",
            "chat-resumo-geral": "overview",
            "chat-alertas-operacionais": "overview",
            "chat-triagem": "overview",
            "chat-movimentos": "overview",
            "chat-new": "new",
            "form-chat-laudo": "new",
            "chat-capacidade-nota": "new",
            "btn-chat-laudo-criar": "new",
            "chat-tipo-template": "new",
            "chat-queue": "queue",
            "chat-busca-laudos": "queue",
            "chat-lista-resumo": "queue",
            "lista-chat-laudos": "queue",
            "chat-case": "case",
            "chat-contexto": "case",
            "chat-mensagens": "case",
            "chat-mensagem": "case",
            "form-chat-msg": "case",
            "btn-chat-upload-doc": "case",
            "chat-upload-doc": "case",
            "chat-upload-status": "case",
            "btn-chat-finalizar": "case",
            "btn-chat-reabrir": "case",
        });

        function normalizarSecaoChat(valor) {
            const secao = texto(valor).trim().toLowerCase();
            return SECTION_ORDER.includes(secao) ? secao : "overview";
        }

        function resolverSecaoChatPorTarget(targetId) {
            const alvo = texto(targetId).trim().replace(/^#/, "");
            if (!alvo) return null;
            if (TARGET_TO_SECTION[alvo]) return TARGET_TO_SECTION[alvo];
            return SECTION_ORDER.includes(alvo) ? alvo : null;
        }

        function obterBotoesSecaoChat() {
            return Array.from(documentRef.querySelectorAll("[data-chat-section-tab]"));
        }

        function obterPaineisSecaoChat() {
            return Array.from(documentRef.querySelectorAll("[data-chat-panel]"));
        }

        function definirTextoNoElemento(id, valor) {
            const node = $(id);
            if (!node) return;
            node.textContent = texto(valor);
        }

        function atualizarResumoSecaoChat() {
            const secaoAtiva = normalizarSecaoChat(state.ui?.chatSection || state.ui?.sections?.chat || "overview");
            const definicao = SECTION_META[secaoAtiva] || SECTION_META.overview;
            const nav = documentRef.querySelector('[data-surface-nav="chat"]');
            const empresa = state.bootstrap?.empresa || {};
            const laudos = state.bootstrap?.chat?.laudos || [];
            const laudosFiltrados = filtrarLaudosChat();
            const laudoAtivo = obterLaudoChatSelecionado();
            const laudosRestantes = empresa.laudos_restantes == null
                ? "Contrato sem teto mensal"
                : `${formatarInteiro(Math.max(Number(empresa.laudos_restantes || 0), 0))} laudos restantes`;
            const contagens = {
                overview: `${formatarInteiro(laudos.length)} laudos no radar`,
                new: laudosRestantes,
                queue: `${formatarInteiro(laudosFiltrados.length)} casos na fila`,
                case: texto(laudoAtivo?.titulo || "Sem caso selecionado"),
            };

            if (nav) {
                nav.dataset.surfaceActiveSection = secaoAtiva;
            }
            definirTextoNoElemento("chat-section-summary-title", definicao.title);
            definirTextoNoElemento("chat-section-summary-meta", definicao.meta);
            definirTextoNoElemento("chat-section-count-overview", contagens.overview);
            definirTextoNoElemento("chat-section-count-new", contagens.new);
            definirTextoNoElemento("chat-section-count-queue", contagens.queue);
            definirTextoNoElemento("chat-section-count-case", contagens.case);
        }

        function abrirSecaoChat(secao, { focusTab = false, syncUrl = true } = {}) {
            const secaoAtiva = normalizarSecaoChat(secao || state.ui?.chatSection);
            state.ui.chatSection = secaoAtiva;
            state.ui.sections = state.ui.sections || {};
            state.ui.sections.chat = secaoAtiva;

            const tabAtiva = obterBotoesSecaoChat().find((button) => button.dataset.chatSectionTab === secaoAtiva) || null;
            obterBotoesSecaoChat().forEach((button) => {
                const ativa = button.dataset.chatSectionTab === secaoAtiva;
                button.classList.toggle("is-active", ativa);
                button.setAttribute("aria-selected", ativa ? "true" : "false");
                button.setAttribute("aria-current", ativa ? "page" : "false");
                button.setAttribute("tabindex", ativa ? "0" : "-1");
            });
            obterPaineisSecaoChat().forEach((panel) => {
                panel.hidden = panel.dataset.chatPanel !== secaoAtiva;
            });
            atualizarResumoSecaoChat();

            if (focusTab && tabAtiva) {
                tabAtiva.focus();
            }
            if (syncUrl && state.ui?.tab === "chat") {
                sincronizarUrlDaSecao("chat", secaoAtiva);
            }
            return secaoAtiva;
        }

        function obterLaudoChatSelecionado() {
            return (state.bootstrap?.chat?.laudos || []).find((laudo) => Number(laudo.id) === Number(state.chat.laudoId)) || null;
        }

        function humanizarLifecycleStatus(valor) {
            const mapa = {
                analise_livre: "Analise livre",
                pre_laudo: "Pre-laudo",
                laudo_em_coleta: "Laudo guiado",
                aguardando_mesa: "Aguardando mesa",
                em_revisao_mesa: "Em revisao na mesa",
                devolvido_para_correcao: "Devolvido para correcao",
                aprovado: "Aprovado",
                emitido: "Emitido",
            };
            const chave = texto(valor).trim().toLowerCase();
            return mapa[chave] || "Fluxo legado";
        }

        function humanizarOwnerRole(valor) {
            const mapa = {
                inspetor: "Responsavel: campo",
                mesa: "Responsavel: mesa",
                none: "Responsavel: conclusao",
            };
            const chave = texto(valor).trim().toLowerCase();
            return mapa[chave] || "Responsavel nao definido";
        }

        function laudoAllowedSurfaceActions(laudo) {
            return Array.isArray(laudo?.allowed_surface_actions)
                ? laudo.allowed_surface_actions.map((item) => texto(item).trim()).filter(Boolean)
                : [];
        }

        function laudoHasSurfaceAction(laudo, actionKey) {
            return laudoAllowedSurfaceActions(laudo).includes(texto(actionKey).trim());
        }

        function chatVisibilityPolicy() {
            return state.bootstrap?.tenant_admin_projection?.payload?.visibility_policy || {};
        }

        function chatCaseActionsEnabled() {
            return Boolean(chatVisibilityPolicy().case_actions_enabled);
        }

        function chatReadOnlyMode() {
            const policy = chatVisibilityPolicy();
            return Boolean(policy.case_list_visible) && !Boolean(policy.case_actions_enabled);
        }

        function resumirMomentoIso(valor) {
            const textoIso = texto(valor).trim();
            if (!textoIso) return "";
            return textoIso.replace("T", " ").replace(/\.\d+/, "").replace("+00:00", " UTC");
        }

        function chatHumanOverrideLatest(laudo) {
            const envelope = laudo && typeof laudo.human_override_summary === "object"
                ? laudo.human_override_summary
                : null;
            const latest = envelope && typeof envelope.latest === "object" ? envelope.latest : null;
            return latest && typeof latest === "object" ? latest : null;
        }

        function renderChatHumanOverrideNotice(laudo) {
            const latest = chatHumanOverrideLatest(laudo);
            if (!latest) return "";
            const actorName = texto(latest.actor_name || "Validador humano");
            const reason = texto(latest.reason || "Justificativa interna registrada.");
            const appliedAt = resumirMomentoIso(latest.applied_at);
            return `
                <div class="context-guidance" data-tone="aguardando">
                    <div class="context-guidance-copy">
                        <small>Override humano interno</small>
                        <strong>${escapeHtml(actorName)}${appliedAt ? ` • ${escapeHtml(appliedAt)}` : ""}</strong>
                        <p>${escapeHtml(reason)}</p>
                    </div>
                    <span class="pill" data-kind="priority" data-status="aguardando">Auditável</span>
                </div>
            `;
        }

        function renderChatPolicyHints() {
            const readOnly = chatReadOnlyMode();
            const newHint = $("chat-new-policy-hint");
            const caseHint = $("chat-case-policy-hint");
            const caseNote = $("chat-case-policy-note");
            const messageNote = $("chat-message-policy-note");
            const uploadButton = $("btn-chat-upload-doc");
            const uploadInput = $("chat-upload-doc");
            const textarea = $("chat-mensagem");
            const sendButton = $("btn-chat-msg-enviar");
            const hasCaseSelected = Boolean(state.chat.laudoId);

            if (newHint) {
                newHint.innerHTML = readOnly ? '<span class="hero-chip">Somente acompanhamento</span>' : "";
            }
            if (caseHint) {
                caseHint.innerHTML = readOnly ? '<span class="hero-chip">Somente acompanhamento</span>' : "";
            }

            if (caseNote) {
                caseNote.hidden = !readOnly;
                caseNote.innerHTML = readOnly
                    ? '<div class="form-hint" data-tone="aguardando"><strong>Ações de estado indisponíveis</strong><span>Este tenant permite leitura do caso, mas não permite finalizar nem reabrir laudos pelo portal cliente.</span></div>'
                    : "";
            }

            if (messageNote) {
                messageNote.hidden = !readOnly;
                messageNote.innerHTML = readOnly
                    ? '<div class="form-hint" data-tone="aguardando"><strong>Escrita bloqueada</strong><span>Você pode acompanhar o caso e marcar avisos como lidos, mas não pode enviar mensagem, documento nem abrir novo laudo.</span></div>'
                    : "";
            }

            if (uploadButton) {
                uploadButton.disabled = readOnly || !hasCaseSelected;
            }
            if (uploadInput) {
                uploadInput.disabled = readOnly;
            }
            if (textarea) {
                textarea.disabled = readOnly || !hasCaseSelected;
            }
            if (sendButton) {
                sendButton.disabled = readOnly || !hasCaseSelected;
            }
        }

        function documentoChatPendenteAtivo() {
            return Boolean(texto(state.chat.documentoTexto).trim());
        }

        function limparDocumentoChatPendente() {
            state.chat.documentoTexto = "";
            state.chat.documentoNome = "";
            state.chat.documentoChars = 0;
            state.chat.documentoTruncado = false;
            if ($("chat-upload-doc")) {
                $("chat-upload-doc").value = "";
            }
            renderChatDocumentoPendente();
        }

        function renderChatDocumentoPendente() {
            const container = $("chat-upload-status");
            renderChatPolicyHints();
            if (!container) return;

            if (!documentoChatPendenteAtivo()) {
                container.hidden = true;
                container.innerHTML = "";
                return;
            }

            const nome = texto(state.chat.documentoNome || "documento");
            const chars = Number(state.chat.documentoChars || texto(state.chat.documentoTexto).length || 0);
            const truncado = Boolean(state.chat.documentoTruncado);

            container.hidden = false;
            container.innerHTML = `
                <div class="attachment-list">
                    <div class="attachment-item">
                        <div class="attachment-copy">
                            <span class="attachment-name">${escapeHtml(nome)}</span>
                            <span class="attachment-meta">
                                Documento pronto para envio • ${escapeHtml(formatarInteiro(chars))} caracteres${truncado ? " • resumo truncado" : ""}
                            </span>
                        </div>
                        <button id="btn-chat-upload-limpar" class="btn ghost" type="button">Remover</button>
                    </div>
                </div>
            `;

            $("btn-chat-upload-limpar")?.addEventListener("click", () => {
                limparDocumentoChatPendente();
                feedback("Documento removido do rascunho do chat.");
            });
        }

        async function importarDocumentoChat(arquivo) {
            if (!arquivo) return;
            if (!state.chat.laudoId) {
                if ($("chat-upload-doc")) {
                    $("chat-upload-doc").value = "";
                }
                feedback("Selecione um laudo do chat antes de importar um documento.", true);
                return;
            }

            const botao = $("btn-chat-upload-doc");
            await withBusy(botao, "Lendo...", async () => {
                const formData = new FormData();
                formData.append("arquivo", arquivo);
                const resposta = await api("/cliente/api/chat/upload_doc", {
                    method: "POST",
                    body: formData,
                });

                state.chat.documentoTexto = texto(resposta?.texto || "").trim();
                state.chat.documentoNome = texto(resposta?.nome || arquivo.name || "documento");
                state.chat.documentoChars = Number(resposta?.chars || state.chat.documentoTexto.length || 0);
                state.chat.documentoTruncado = Boolean(resposta?.truncado);
                renderChatDocumentoPendente();
                $("chat-mensagem")?.focus();
                feedback(
                    `${state.chat.documentoNome} pronto para envio no chat da empresa.`,
                    false,
                    "Documento carregado"
                );
            }).catch((erro) => {
                limparDocumentoChatPendente();
                feedback(erro.message || "Falha ao importar documento.", true);
            });
        }

        function renderChatCapacidade() {
            const empresa = state.bootstrap?.empresa;
            const nota = $("chat-capacidade-nota");
            const botao = $("btn-chat-laudo-criar");
            const seletor = $("chat-tipo-template");
            const readOnly = chatReadOnlyMode();
            const templateOptions = Array.isArray(state.bootstrap?.chat?.tipo_template_options)
                ? state.bootstrap.chat.tipo_template_options
                : [];
            const governado = Boolean(state.bootstrap?.chat?.catalog_governed_mode);
            const governadoSemTemplates = governado && templateOptions.length === 0;
            if (!empresa || !nota) return;

            if (seletor && governadoSemTemplates) {
                seletor.innerHTML = "";
                delete seletor.dataset.catalogSignature;
            } else if (seletor && templateOptions.length) {
                const assinatura = JSON.stringify(
                    templateOptions.map((item) => [item?.value, item?.label, item?.group_label])
                );
                if (seletor.dataset.catalogSignature !== assinatura) {
                    const valorAtual = texto(seletor.value).trim();
                    const grupos = new Map();
                    templateOptions.forEach((item) => {
                        const grupo = texto(item?.group_label).trim() || "Catálogo oficial";
                        if (!grupos.has(grupo)) {
                            grupos.set(grupo, []);
                        }
                        grupos.get(grupo).push(item);
                    });

                    seletor.innerHTML = "";
                    grupos.forEach((itens, grupo) => {
                        const optgroup = documentRef.createElement("optgroup");
                        optgroup.label = grupo;
                        itens.forEach((item) => {
                            const option = documentRef.createElement("option");
                            option.value = texto(item?.value).trim();
                            option.textContent = texto(item?.label).trim() || option.value;
                            optgroup.appendChild(option);
                        });
                        seletor.appendChild(optgroup);
                    });

                    const valorValido = templateOptions.some((item) => texto(item?.value).trim() === valorAtual)
                        ? valorAtual
                        : texto(templateOptions[0]?.value).trim();
                    seletor.value = valorValido;
                    seletor.dataset.catalogSignature = assinatura;
                }
            }

            const atingiuTeto = empresa.laudos_mes_limite != null && Number(empresa.laudos_restantes || 0) <= 0;
            const emAtencao = empresa.laudos_mes_limite != null && Number(empresa.laudos_restantes || 0) > 0 && Number(empresa.laudos_restantes || 0) <= 5;
            const planoSugerido = texto(empresa.plano_sugerido).trim();
            const tone = atingiuTeto ? "ajustes" : emAtencao ? "aguardando" : tomCapacidadeEmpresa(empresa);

            nota.innerHTML = `
                ${readOnly
                    ? '<div class="form-hint" data-tone="aguardando"><strong>Somente acompanhamento</strong><span>Este tenant deixa o admin-cliente acompanhar casos visíveis, mas sem abrir novos laudos.</span></div>'
                    : ""}
                <div class="form-hint" data-tone="${tone}">
                    <strong>${atingiuTeto ? "Novos laudos bloqueados pelo plano" : emAtencao ? "Janela mensal quase no limite" : "Abertura de laudo dentro da capacidade"}</strong>
                    <span>${escapeHtml(
                        atingiuTeto
                            ? `${formatarCapacidadeRestante(empresa.laudos_restantes, empresa.laudos_excedente, "laudo", "laudos")}. ${planoSugerido ? `Registre interesse em ${planoSugerido} para liberar novas aberturas.` : "Revise o contrato antes de abrir novos laudos."}`
                            : emAtencao
                            ? `${formatarCapacidadeRestante(empresa.laudos_restantes, empresa.laudos_excedente, "laudo", "laudos")}. ${planoSugerido ? `Vale registrar ${planoSugerido} antes do proximo pico.` : "Monitore a fila antes do proximo pico."}`
                                : governadoSemTemplates
                                    ? "A empresa continua sob liberacao do Admin-CEO, mas nao possui modelos liberados no momento."
                                    : governado
                                    ? "A empresa esta usando os modelos liberados pelo Admin-CEO."
                                    : "O plano atual ainda sustenta novas aberturas de laudo com folga operacional."
                    )}</span>
                    ${planoSugerido && (atingiuTeto || emAtencao)
                        ? `<div class="toolbar-meta"><button class="btn" type="button" data-act="preparar-upgrade" data-origem="chat">Registrar interesse em ${escapeHtml(planoSugerido)}</button></div>`
                        : ""}
                </div>
            `;

            if (botao) {
                botao.disabled = readOnly || atingiuTeto || governadoSemTemplates;
            }
            if (seletor) {
                seletor.disabled = readOnly || atingiuTeto || governadoSemTemplates;
            }
            renderChatPolicyHints();
        }

        function renderChatResumo() {
            const container = $("chat-resumo-geral");
            if (!container) return;

            const laudos = state.bootstrap?.chat?.laudos || [];
            const selecionado = obterLaudoChatSelecionado();
            const prioridade = selecionado ? prioridadeChat(selecionado) : null;

            const abertos = laudos.filter((item) => variantStatusLaudo(item.status_card) === "aberto").length;
            const aguardando = laudos.filter((item) => variantStatusLaudo(item.status_card) === "aguardando").length;
            const ajustes = laudos.filter((item) => variantStatusLaudo(item.status_card) === "ajustes").length;
            const concluidos = laudos.filter((item) => variantStatusLaudo(item.status_card) === "aprovado").length;

            container.innerHTML = `
                <article class="metric-card" data-accent="attention">
                    <small>Acao agora</small>
                    <strong>${formatarInteiro(ajustes)}</strong>
                    <span class="metric-meta">Laudos devolvidos para ajuste e que pedem resposta do time.</span>
                </article>
                <article class="metric-card" data-accent="live">
                    <small>Em operacao</small>
                    <strong>${formatarInteiro(abertos)}</strong>
                    <span class="metric-meta">Conversas abertas e prontas para continuar no chat.</span>
                </article>
                <article class="metric-card" data-accent="waiting">
                    <small>Aguardando mesa</small>
                    <strong>${formatarInteiro(aguardando)}</strong>
                    <span class="metric-meta">Laudos que ja sairam do campo e estao esperando retorno da mesa.</span>
                </article>
                <article class="metric-card" data-accent="${prioridade ? prioridade.tone : "done"}">
                    <small>Foco do laudo selecionado</small>
                    <strong>${escapeHtml(prioridade ? prioridade.badge : "Sem selecao")}</strong>
                    <span class="metric-meta">${escapeHtml(prioridade ? prioridade.acao : `${formatarInteiro(concluidos)} concluidos sem urgencia na fila.`)}</span>
                </article>
            `;
            atualizarResumoSecaoChat();
        }

        function renderChatTriagem() {
            const container = $("chat-triagem");
            const laudos = state.bootstrap?.chat?.laudos || [];
            if (!container) return;

            const ajustes = ordenarPorPrioridade(laudos.filter((item) => variantStatusLaudo(item.status_card) === "ajustes"), prioridadeChat);
            const abertos = ordenarPorPrioridade(laudos.filter((item) => variantStatusLaudo(item.status_card) === "aberto"), prioridadeChat);
            const aguardando = ordenarPorPrioridade(laudos.filter((item) => variantStatusLaudo(item.status_card) === "aguardando"), prioridadeChat);
            const parados = ordenarPorPrioridade(laudos.filter((item) => laudoChatParado(item)), prioridadeChat);
            const filtroAtivo = rotuloSituacaoChat(state.ui.chatSituacao);
            const destaque = ajustes[0] || parados[0] || aguardando[0] || abertos[0] || null;

            container.innerHTML = `
                <div class="toolbar-meta">
                    <button class="btn" type="button" data-act="filtrar-chat-status" data-situacao="ajustes">Ver ajustes</button>
                    <button class="btn" type="button" data-act="filtrar-chat-status" data-situacao="abertos">Ver abertos</button>
                    <button class="btn" type="button" data-act="filtrar-chat-status" data-situacao="aguardando">Ver aguardando mesa</button>
                    <button class="btn" type="button" data-act="filtrar-chat-status" data-situacao="parados">Ver parados</button>
                    <button class="btn ghost" type="button" data-act="limpar-chat-filtro">Limpar filtro rapido</button>
                    ${filtroAtivo ? `<span class="hero-chip">Filtro rapido: ${escapeHtml(filtroAtivo)}</span>` : ""}
                </div>
                ${destaque ? `
                    <article class="activity-item">
                        <div class="activity-head">
                            <div class="activity-copy">
                                <strong>${escapeHtml(destaque.titulo || "Laudo do chat")}</strong>
                                <span class="activity-meta">${escapeHtml(destaque.tipo_template_label || "Inspeção")} • ${escapeHtml(destaque.data_br || "Sem data")}</span>
                            </div>
                            <span class="pill" data-kind="priority" data-status="${escapeAttr(prioridadeChat(destaque).tone)}">${escapeHtml(prioridadeChat(destaque).badge)}</span>
                        </div>
                        <p class="activity-detail">${escapeHtml(prioridadeChat(destaque).acao)}${laudoChatParado(destaque) ? ` ${resumoEsperaHoras(horasDesdeAtualizacao(destaque.atualizado_em))}.` : ""}</p>
                        <div class="toolbar-meta">
                            <button class="btn" type="button" data-act="abrir-prioridade" data-kind="chat-laudo" data-canal="chat" data-laudo="${escapeAttr(String(destaque.id || ""))}" data-target="chat-contexto">Abrir laudo prioritario</button>
                        </div>
                    </article>
                ` : `
                    <div class="empty-state">
                        <strong>Fila do chat controlada</strong>
                        <p>Nenhum laudo pede atenção imediata agora. Use os filtros rápidos se quiser revisar a fila por status.</p>
                    </div>
                `}
            `;
            atualizarResumoSecaoChat();
        }

        function renderChatMovimentos() {
            const container = $("chat-movimentos");
            const laudos = ordenarPorPrioridade(state.bootstrap?.chat?.laudos || [], (item) => ({
                score: parseDataIso(item?.atualizado_em),
            })).slice(0, 3);
            if (!container) return;

            if (!laudos.length) {
                container.innerHTML = `
                    <div class="empty-state">
                        <strong>Sem movimentos recentes no chat</strong>
                        <p>Os laudos mais novos da empresa vao aparecer aqui assim que o chat começar a rodar.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <article class="activity-item">
                    <div class="activity-head">
                        <div class="activity-copy">
                            <strong>Movimentos recentes do chat</strong>
                            <span class="activity-meta">Os ultimos laudos tocados pela empresa no canal operacional.</span>
                        </div>
                        <span class="hero-chip">${formatarInteiro(laudos.length)} recentes</span>
                    </div>
                    <div class="activity-list">
                        ${laudos.map((laudo) => `
                            <article class="activity-item">
                                <div class="activity-head">
                                    <div class="activity-copy">
                                        <strong>${escapeHtml(laudo.titulo || "Laudo do chat")}</strong>
                                        <span class="activity-meta">${escapeHtml(laudo.data_br || "Sem data")} • ${escapeHtml(laudo.tipo_template_label || "Inspecao")}</span>
                                    </div>
                                    <span class="pill" data-kind="priority" data-status="${escapeAttr(prioridadeChat(laudo).tone)}">${escapeHtml(prioridadeChat(laudo).badge)}</span>
                                </div>
                                <p class="activity-detail">${escapeHtml(laudo.preview || "Sem resumo recente no chat.")}</p>
                                <div class="toolbar-meta">
                                    ${laudoChatParado(laudo) ? `<span class="hero-chip">${escapeHtml(resumoEsperaHoras(horasDesdeAtualizacao(laudo.atualizado_em)))}</span>` : ""}
                                    <button class="btn" type="button" data-act="abrir-prioridade" data-kind="chat-laudo" data-canal="chat" data-laudo="${escapeAttr(String(laudo.id || ""))}" data-target="chat-contexto">Abrir laudo</button>
                                </div>
                            </article>
                        `).join("")}
                    </div>
                </article>
            `;
        }

        function renderChatList() {
            const laudos = ordenarPorPrioridade(filtrarLaudosChat(), prioridadeChat);
            const lista = $("lista-chat-laudos");
            const resumo = $("chat-lista-resumo");
            const filtroAtivo = rotuloSituacaoChat(state.ui.chatSituacao);
            if (!lista || !resumo) return;

            resumo.innerHTML = `
                <span class="hero-chip">${formatarInteiro(laudos.length)} laudos visiveis</span>
                <span class="hero-chip">${formatarInteiro((state.bootstrap?.chat?.laudos || []).filter((item) => variantStatusLaudo(item.status_card) === "aberto").length)} abertos</span>
                <span class="hero-chip">${formatarInteiro((state.bootstrap?.chat?.laudos || []).filter((item) => variantStatusLaudo(item.status_card) === "ajustes").length)} em ajuste</span>
                ${filtroAtivo ? `<span class="hero-chip">Filtro rapido: ${escapeHtml(filtroAtivo)}</span>` : ""}
            `;

            if (!laudos.length) {
                lista.innerHTML = `
                    <div class="empty-state">
                        <strong>Nenhum laudo encontrado</strong>
                        <p>Ajuste a busca ou crie um novo laudo para operar o chat por aqui.</p>
                    </div>
                `;
                atualizarResumoSecaoChat();
                return;
            }

            lista.innerHTML = laudos.map((laudo) => `
                <article class="item ${Number(state.chat.laudoId) === Number(laudo.id) ? "active" : ""}" data-chat="${laudo.id}" tabindex="0">
                    <div class="item-head">
                        <strong>${escapeHtml(laudo.titulo)}</strong>
                        ${laudoBadge(laudo.status_card_label, laudo.status_card)}
                    </div>
                    <div class="item-preview">${escapeHtml(laudo.preview || "Sem resumo da conversa ainda.")}</div>
                    <div class="item-footer">
                        <span class="pill" data-kind="priority" data-status="${prioridadeChat(laudo).tone}">${escapeHtml(prioridadeChat(laudo).badge)}</span>
                        <span class="hero-chip">${escapeHtml(laudo.tipo_template_label || "Inspecao")}</span>
                        ${laudoChatParado(laudo) ? `<span class="hero-chip">${escapeHtml(resumoEsperaHoras(horasDesdeAtualizacao(laudo.atualizado_em)))}</span>` : ""}
                        <small>${escapeHtml(laudo.data_br || "Sem data")}</small>
                    </div>
                </article>
            `).join("");
            atualizarResumoSecaoChat();
        }

        function renderChatContext() {
            const alvo = obterLaudoChatSelecionado();
            const contexto = $("chat-contexto");
            const finalizar = $("btn-chat-finalizar");
            const reabrir = $("btn-chat-reabrir");
            const caseActionsEnabled = chatCaseActionsEnabled();
            if (!contexto) return;

            if (!alvo) {
                contexto.innerHTML = `
                    <div class="empty-state">
                        <strong>Selecione um laudo do lado esquerdo</strong>
                        <p>Quando um laudo for selecionado, o contexto operacional e o historico aparecem aqui.</p>
                    </div>
                `;
                if (finalizar) finalizar.disabled = true;
                if (reabrir) reabrir.disabled = true;
                if ($("chat-titulo")) {
                    $("chat-titulo").textContent = "Selecione um laudo";
                }
                renderChatDocumentoPendente();
                atualizarResumoSecaoChat();
                return;
            }

            const prioridade = prioridadeChat(alvo);
            const canFinalize = caseActionsEnabled && laudoHasSurfaceAction(alvo, "chat_finalize");
            const canReopen = caseActionsEnabled && laudoHasSurfaceAction(alvo, "chat_reopen");
            if ($("chat-titulo")) {
                $("chat-titulo").textContent = alvo.titulo || "Laudo selecionado";
            }
            if (finalizar) finalizar.disabled = !canFinalize;
            if (reabrir) reabrir.disabled = !canReopen;

            contexto.innerHTML = `
                <div class="context-card">
                    <div class="context-head">
                        <div>
                            <div class="context-title">${escapeHtml(alvo.titulo)}</div>
                            <div class="context-subtitle">${escapeHtml(alvo.preview || "Sem resumo registrado.")}</div>
                        </div>
                        <div class="context-actions">
                            ${laudoBadge(alvo.status_card_label, alvo.status_card)}
                        </div>
                    </div>
                    <div class="context-grid">
                        <div class="context-block">
                            <small>Modelo atual</small>
                            <strong>${escapeHtml(alvo.tipo_template_label || "Inspecao padrao")}</strong>
                        </div>
                        <div class="context-block">
                            <small>Ultima atualizacao</small>
                            <strong>${escapeHtml(alvo.data_br || "Sem data")}</strong>
                        </div>
                        <div class="context-block">
                            <small>Setor</small>
                            <strong>${escapeHtml(alvo.setor_industrial || "Geral")}</strong>
                        </div>
                        <div class="context-block">
                            <small>Fluxo do caso</small>
                            <strong>${escapeHtml(`${humanizarLifecycleStatus(alvo.case_lifecycle_status)} / ${humanizarOwnerRole(alvo.active_owner_role)}`)}</strong>
                        </div>
                    </div>
                    <div class="context-guidance" data-tone="${prioridade.tone}">
                        <div class="context-guidance-copy">
                            <small>Proximo passo recomendado</small>
                            <strong>${escapeHtml(prioridade.badge)}</strong>
                            <p>${escapeHtml(prioridade.acao)}</p>
                        </div>
                        <span class="pill" data-kind="priority" data-status="${prioridade.tone}">${escapeHtml(prioridade.badge)}</span>
                    </div>
                    ${renderChatHumanOverrideNotice(alvo)}
                    ${laudoChatParado(alvo) ? `
                        <div class="context-guidance" data-tone="aguardando">
                            <div class="context-guidance-copy">
                                <small>Item parado</small>
                                <strong>${escapeHtml(resumoEsperaHoras(horasDesdeAtualizacao(alvo.atualizado_em)))}</strong>
                                <p>Vale retomar este laudo para nao perder ritmo operacional no chat.</p>
                            </div>
                            <span class="pill" data-kind="priority" data-status="aguardando">Retomar</span>
                        </div>
                    ` : ""}
                </div>
            `;
            renderChatDocumentoPendente();
            atualizarResumoSecaoChat();
        }

        function renderChatMensagens() {
            const container = $("chat-mensagens");
            const mensagens = Array.isArray(state.chat.mensagens) ? state.chat.mensagens : [];
            if (!container) return;

            if (!mensagens.length) {
                container.innerHTML = `
                    <div class="empty-state">
                        <strong>Nenhuma mensagem carregada</strong>
                        <p>Assim que voce conversar com o assistente ou com a mesa, o historico aparece aqui.</p>
                    </div>
                `;
                atualizarResumoSecaoChat();
                return;
            }

            container.innerHTML = mensagens.map((mensagem) => {
                const papel = texto(mensagem.papel).toLowerCase();
                const classe = papel === "usuario" ? "msg--usuario" : papel === "assistente" ? "msg--assistente" : "msg--whisper";
                const titulo = papel === "usuario" ? "Usuario" : papel === "assistente" ? "Assistente" : "Mesa";

                return `
                    <article class="msg ${classe}">
                        <div class="msg-head">
                            <div class="msg-meta">
                                <span class="msg-title">${escapeHtml(titulo)}</span>
                                <span class="msg-time">${escapeHtml(mensagem.tipo || "mensagem")}</span>
                            </div>
                        </div>
                        <div class="msg-body">${textoComQuebras(mensagem.texto || "(sem conteudo)")}</div>
                        ${renderAnexos(mensagem.anexos)}
                    </article>
                `;
            }).join("");
            atualizarResumoSecaoChat();
        }

        return {
            abrirSecaoChat,
            documentoChatPendenteAtivo,
            importarDocumentoChat,
            limparDocumentoChatPendente,
            laudoHasSurfaceAction,
            obterLaudoChatSelecionado,
            resolverSecaoChatPorTarget,
            renderChatCapacidade,
            renderChatContext,
            renderChatDocumentoPendente,
            renderChatList,
            renderChatMensagens,
            renderChatMovimentos,
            renderChatResumo,
            renderChatTriagem,
        };
    };
})();
