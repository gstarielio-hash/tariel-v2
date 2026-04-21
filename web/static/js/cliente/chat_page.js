(function () {
    "use strict";

    if (window.TarielClienteChatPage) return;

    window.TarielClienteChatPage = function createTarielClienteChatPage(config = {}) {
        const state = config.state || {};
        const documentRef = config.documentRef || document;
        const $ = typeof config.getById === "function"
            ? config.getById
            : (id) => documentRef.getElementById(id);
        const helpers = config.helpers || {};
        const actions = config.actions || {};
        const storageKeys = config.storageKeys || {};
        const surfaceModule = config.surfaceModule || {};

        const api = typeof helpers.api === "function" ? helpers.api : async () => null;
        const definirTab = typeof helpers.definirTab === "function" ? helpers.definirTab : () => null;
        const feedback = typeof helpers.feedback === "function" ? helpers.feedback : () => null;
        const perfAsync = typeof helpers.perfAsync === "function" ? helpers.perfAsync : async (_nome, callback) => callback();
        const perfSnapshot = typeof helpers.perfSnapshot === "function" ? helpers.perfSnapshot : () => null;
        const persistirSelecao = typeof helpers.persistirSelecao === "function" ? helpers.persistirSelecao : () => null;
        const texto = typeof helpers.texto === "function" ? helpers.texto : (valor) => (valor == null ? "" : String(valor));
        const withBusy = typeof helpers.withBusy === "function" ? helpers.withBusy : async (_target, _busyText, callback) => callback();

        const bootstrapPortal = typeof actions.bootstrapPortal === "function" ? actions.bootstrapPortal : async () => null;
        const storageChatKey = storageKeys.chat || "tariel.cliente.chat.laudo";

        const abrirSecaoChat = typeof surfaceModule.abrirSecaoChat === "function" ? surfaceModule.abrirSecaoChat : () => "overview";
        const documentoChatPendenteAtivo = typeof surfaceModule.documentoChatPendenteAtivo === "function" ? surfaceModule.documentoChatPendenteAtivo : () => false;
        const importarDocumentoChat = typeof surfaceModule.importarDocumentoChat === "function" ? surfaceModule.importarDocumentoChat : async () => null;
        const limparDocumentoChatPendente = typeof surfaceModule.limparDocumentoChatPendente === "function" ? surfaceModule.limparDocumentoChatPendente : () => null;
        const laudoHasSurfaceAction = typeof surfaceModule.laudoHasSurfaceAction === "function" ? surfaceModule.laudoHasSurfaceAction : () => false;
        const renderChatCapacidade = typeof surfaceModule.renderChatCapacidade === "function" ? surfaceModule.renderChatCapacidade : () => null;
        const renderChatContext = typeof surfaceModule.renderChatContext === "function" ? surfaceModule.renderChatContext : () => null;
        const renderChatDocumentoPendente = typeof surfaceModule.renderChatDocumentoPendente === "function" ? surfaceModule.renderChatDocumentoPendente : () => null;
        const renderChatList = typeof surfaceModule.renderChatList === "function" ? surfaceModule.renderChatList : () => null;
        const renderChatMensagens = typeof surfaceModule.renderChatMensagens === "function" ? surfaceModule.renderChatMensagens : () => null;
        const renderChatMovimentos = typeof surfaceModule.renderChatMovimentos === "function" ? surfaceModule.renderChatMovimentos : () => null;
        const renderChatResumo = typeof surfaceModule.renderChatResumo === "function" ? surfaceModule.renderChatResumo : () => null;
        const renderChatTriagem = typeof surfaceModule.renderChatTriagem === "function" ? surfaceModule.renderChatTriagem : () => null;
        const obterLaudoChatSelecionado = typeof surfaceModule.obterLaudoChatSelecionado === "function" ? surfaceModule.obterLaudoChatSelecionado : () => null;
        const resolverSecaoChatPorTarget = typeof surfaceModule.resolverSecaoChatPorTarget === "function" ? surfaceModule.resolverSecaoChatPorTarget : () => null;

        function chatCaseActionsEnabled() {
            return Boolean(
                state.bootstrap?.tenant_admin_projection?.payload?.visibility_policy?.case_actions_enabled
            );
        }

        function solicitarPoliticaDocumentoEmitidoReabertura(laudo) {
            const lifecycleStatus = texto(laudo?.case_lifecycle_status).trim().toLowerCase();
            if (!["aprovado", "emitido"].includes(lifecycleStatus)) {
                return undefined;
            }

            if (typeof window.confirm !== "function") {
                return { issued_document_policy: "keep_visible" };
            }

            const manterVisivel = window.confirm(
                "Ao reabrir este laudo, deseja manter o PDF final anterior visivel no caso?\n\nOK = manter visivel\nCancelar = escolher outra opcao"
            );

            if (manterVisivel) {
                return { issued_document_policy: "keep_visible" };
            }

            const ocultarDoCaso = window.confirm(
                "Deseja reabrir ocultando o PDF final anterior da area ativa do caso?\n\nOK = ocultar do caso\nCancelar = desistir da reabertura"
            );

            if (!ocultarDoCaso) {
                return null;
            }

            return { issued_document_policy: "hide_from_case" };
        }

        async function loadChat(laudoId, { silencioso = false, force = false } = {}) {
            return perfAsync(
                "cliente.loadChat",
                async () => {
                    const id = Number(laudoId || 0);
                    if (!Number.isFinite(id) || id <= 0) return null;
                    const laudoAnterior = Number(state.chat.laudoId || 0) || null;

                    state.chat.laudoId = id;
                    if (laudoAnterior && laudoAnterior !== id) {
                        state.chat.loadedLaudoId = null;
                        limparDocumentoChatPendente();
                    }
                    persistirSelecao(storageChatKey, id);
                    renderChatResumo();
                    renderChatList();
                    renderChatContext();

                    if (!force && Number(state.chat.loadedLaudoId || 0) === id) {
                        renderChatMensagens();
                        return { itens: state.chat.mensagens || [] };
                    }

                    const payload = await api(`/cliente/api/chat/laudos/${id}/mensagens`);
                    state.chat.mensagens = payload.itens || [];
                    state.chat.loadedLaudoId = id;
                    renderChatMensagens();
                    perfSnapshot(`cliente:chat:${id}`);

                    if (!silencioso && state.ui.tab !== "chat") {
                        feedback("Historico do chat carregado.");
                    }
                    return payload;
                },
                { laudoId: Number(laudoId || 0) || 0, silencioso },
                "function"
            );
        }

        function atualizarBuscaChat(valor) {
            state.ui.chatBusca = valor || "";
            state.ui.chatSituacao = "";
            renderChatTriagem();
            renderChatList();
        }

        function aplicarFiltroChatRapido(situacao) {
            state.ui.chatBusca = "";
            state.ui.chatSituacao = texto(situacao).trim();
            if ($("chat-busca-laudos")) {
                $("chat-busca-laudos").value = "";
            }
            renderChatTriagem();
            renderChatList();
        }

        function limparFiltroChatRapido() {
            state.ui.chatBusca = "";
            state.ui.chatSituacao = "";
            if ($("chat-busca-laudos")) {
                $("chat-busca-laudos").value = "";
            }
            renderChatTriagem();
            renderChatList();
        }

        function bindChatActions() {
            $("form-chat-laudo")?.addEventListener("submit", async (event) => {
                event.preventDefault();
                if (!chatCaseActionsEnabled()) {
                    feedback("Este tenant permite ao admin-cliente apenas acompanhamento, sem agir nos casos.", true);
                    return;
                }
                const empresa = state.bootstrap?.empresa;
                if (empresa?.laudos_mes_limite != null && Number(empresa.laudos_restantes || 0) <= 0) {
                    feedback("O plano atual bloqueou novas aberturas de laudo. Registre interesse comercial antes de continuar.", true);
                    return;
                }
                const button = event.submitter || event.target.querySelector('button[type="submit"]');

                await withBusy(button, "Criando...", async () => {
                    const formData = new FormData();
                    formData.append("tipo_template", $("chat-tipo-template").value);
                    const resposta = await api("/cliente/api/chat/laudos", {
                        method: "POST",
                        body: formData,
                    });
                    await bootstrapPortal({ surface: "chat", force: true });
                    abrirSecaoChat("case");
                    await loadChat(resposta.laudo_id, { silencioso: true });
                    definirTab("chat");
                    feedback("Novo laudo criado para a empresa.");
                }).catch((erro) => feedback(erro.message || "Falha ao criar laudo.", true));
            });

            ["click", "keydown"].forEach((tipoEvento) => {
                $("lista-chat-laudos")?.addEventListener(tipoEvento, async (event) => {
                    const item = event.target.closest("[data-chat]");
                    if (!item) return;
                    if (tipoEvento === "keydown" && event.key !== "Enter" && event.key !== " ") return;
                    if (tipoEvento === "keydown") event.preventDefault();
                    abrirSecaoChat("case");
                    await loadChat(item.dataset.chat).catch((erro) => feedback(erro.message || "Falha ao abrir laudo.", true));
                });
            });

            $("btn-chat-upload-doc")?.addEventListener("click", () => {
                if (!chatCaseActionsEnabled()) {
                    feedback("Este tenant permite ao admin-cliente apenas acompanhamento, sem agir nos casos.", true);
                    return;
                }
                $("chat-upload-doc")?.click();
            });

            $("chat-upload-doc")?.addEventListener("change", async (event) => {
                if (!chatCaseActionsEnabled()) {
                    event.target.value = "";
                    feedback("Este tenant permite ao admin-cliente apenas acompanhamento, sem agir nos casos.", true);
                    return;
                }
                const arquivo = event.target?.files?.[0] || null;
                if (!arquivo) return;
                await importarDocumentoChat(arquivo);
            });

            $("form-chat-msg")?.addEventListener("submit", async (event) => {
                event.preventDefault();
                if (!chatCaseActionsEnabled()) {
                    feedback("Este tenant permite ao admin-cliente apenas acompanhamento, sem agir nos casos.", true);
                    return;
                }
                if (!state.chat.laudoId) {
                    feedback("Selecione um laudo do chat primeiro.", true);
                    return;
                }

                const mensagem = $("chat-mensagem").value.trim();
                if (!mensagem && !documentoChatPendenteAtivo()) {
                    feedback("Escreva uma mensagem ou importe um documento antes de enviar.", true);
                    return;
                }

                const button = event.submitter || event.target.querySelector('button[type="submit"]');
                await withBusy(button, "Enviando...", async () => {
                    const historico = (state.chat.mensagens || [])
                        .filter((item) => item.papel === "usuario" || item.papel === "assistente")
                        .map((item) => ({
                            papel: item.papel,
                            texto: item.texto || "",
                        }))
                        .slice(-20);

                    await api("/cliente/api/chat/mensagem", {
                        method: "POST",
                        body: {
                            laudo_id: state.chat.laudoId,
                            mensagem,
                            historico,
                            setor: "geral",
                            modo: "detalhado",
                            texto_documento: state.chat.documentoTexto || "",
                            nome_documento: state.chat.documentoNome || "",
                        },
                    });
                    $("chat-mensagem").value = "";
                    limparDocumentoChatPendente();
                    await bootstrapPortal({ surface: "chat", force: true });
                    await loadChat(state.chat.laudoId, { silencioso: true, force: true });
                    feedback("Mensagem enviada no chat da empresa.");
                }).catch((erro) => feedback(erro.message || "Falha ao enviar mensagem.", true));
            });

            $("btn-chat-finalizar")?.addEventListener("click", async (event) => {
                if (!chatCaseActionsEnabled()) {
                    feedback("Este tenant permite ao admin-cliente apenas acompanhamento, sem agir nos casos.", true);
                    return;
                }
                if (!state.chat.laudoId) return;
                const button = event.currentTarget;
                const laudoSelecionado = obterLaudoChatSelecionado();
                if (!laudoHasSurfaceAction(laudoSelecionado, "chat_finalize")) {
                    feedback("Este caso ainda nao esta em um ponto valido para finalizacao.", true);
                    return;
                }
                await withBusy(button, "Enviando...", async () => {
                    await api(`/cliente/api/chat/laudos/${state.chat.laudoId}/finalizar`, { method: "POST" });
                    await bootstrapPortal({ surface: "chat", force: true });
                    await loadChat(state.chat.laudoId, { silencioso: true, force: true });
                    feedback("Laudo enviado para a mesa avaliadora.");
                }).catch((erro) => feedback(erro.message || "Falha ao finalizar laudo.", true));
            });

            $("btn-chat-reabrir")?.addEventListener("click", async (event) => {
                if (!chatCaseActionsEnabled()) {
                    feedback("Este tenant permite ao admin-cliente apenas acompanhamento, sem agir nos casos.", true);
                    return;
                }
                if (!state.chat.laudoId) return;
                const button = event.currentTarget;
                const laudoSelecionado = obterLaudoChatSelecionado();
                if (!laudoHasSurfaceAction(laudoSelecionado, "chat_reopen")) {
                    feedback("Este caso ainda nao permite reabertura a partir do portal.", true);
                    return;
                }
                const payloadReabertura = solicitarPoliticaDocumentoEmitidoReabertura(
                    laudoSelecionado
                );
                if (payloadReabertura === null) return;
                await withBusy(button, "Reabrindo...", async () => {
                    await api(`/cliente/api/chat/laudos/${state.chat.laudoId}/reabrir`, {
                        method: "POST",
                        ...(payloadReabertura ? { body: payloadReabertura } : {}),
                    });
                    await bootstrapPortal({ surface: "chat", force: true });
                    await loadChat(state.chat.laudoId, { silencioso: true, force: true });
                    feedback("Laudo reaberto para nova iteracao.");
                }).catch((erro) => feedback(erro.message || "Falha ao reabrir laudo.", true));
            });
        }

        return {
            ...surfaceModule,
            aplicarFiltroChatRapido,
            atualizarBuscaChat,
            bindChatActions,
            limparFiltroChatRapido,
            loadChat,
            renderChatCapacidade,
            renderChatContext,
            renderChatDocumentoPendente,
            renderChatList,
            renderChatMensagens,
            renderChatMovimentos,
            renderChatResumo,
            renderChatTriagem,
            resolverSecaoChatPorTarget,
        };
    };
})();
