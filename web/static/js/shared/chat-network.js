// ==========================================
// TARIEL.IA — CHAT-NETWORK.JS
// Camada de rede e orquestração do chat.
// Responsável por:
// - estado do relatório
// - SSE / stream de respostas
// - upload de imagem e documento
// - geração de PDF
// - envio de feedback
// - compatibilidade com legado
// ==========================================

(function () {
    "use strict";

    if (window.TarielChatNetwork) return;
    const InspectorRuntime = window.TarielInspectorRuntime || null;
    const sharedGlobals =
        InspectorRuntime?.resolveSharedGlobals?.() || {
            perf: window.TarielPerf || window.TarielCore?.TarielPerf || null,
            caseLifecycle: window.TarielCaseLifecycle,
            inspectorEvents: window.TarielInspectorEvents || null,
        };

    window.TarielChatNetwork = function TarielChatNetworkFactory(config = {}) {
        // =========================================================
        // CONFIGURAÇÃO INJETADA
        // =========================================================
        const {
            log = (...args) => console.log(...args),
            escapeHTML = (valor) => String(valor ?? ""),
            mostrarToast = () => {},
            validarPrefixoBase64 = (valor) => valor,
            sanitizarSetor = (valor) => valor || "geral",
            comCabecalhoCSRF = (headers = {}) => headers,
            criarFormDataComCSRF = () => new FormData(),

            campoMensagem = null,
            btnEnviar = null,
            previewContainer = null,
            inputAnexo = null,
            telaBoasVindas = null,
            setorSelect = null,

            getNomeUsuario = () => "Inspetor",
            getNomeEmpresa = () => "Sua empresa",

            getLaudoAtualId = () => null,
            setLaudoAtualId = () => {},

            getEstadoRelatorio = () => "sem_relatorio",
            setEstadoRelatorio = () => {},

            getHistoricoConversa = () => [],
            setHistoricoConversa = () => {},
            adicionarAoHistorico = () => {},

            getUltimoDiagnosticoBruto = () => "",
            setUltimoDiagnosticoBruto = () => {},

            getIaRespondendo = () => false,
            setIaRespondendo = () => {},

            getArquivoPendente = () => null,
            setArquivoPendente = () => {},

            getImagemBase64Pendente = () => null,
            setImagemBase64Pendente = () => {},

            getTextoDocumentoPendente = () => null,
            setTextoDocumentoPendente = () => {},

            getNomeDocumentoPendente = () => null,
            setNomeDocumentoPendente = () => {},

            getControllerStream = () => null,
            setControllerStream = () => {},

            limparHistoricoChat = () => {},
            limparAreaMensagens = () => {},
            mostrarDigitando = () => {},
            ocultarDigitando = () => {},
            rolarParaBaixo = () => {},
            atualizarEstadoBotao = () => {},
            atualizarContadorChars = () => {},
            atualizarTiquesStatus = () => {},

            criarBolhaIA = () => null,
            mostrarAcoesPosResposta = () => {},
            renderizarAnexosMensagem = () => null,
            renderizarMarkdown = (texto) => escapeHTML(texto),
            renderizarCitacoes = () => {},
            renderizarConfiancaIA = () => {},

            getModoAtual = () => "detalhado",
        } = config;

        // =========================================================
        // CONSTANTES
        // =========================================================
        const MIME_DOCUMENTOS = new Set([
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]);

        const MIME_IMAGENS = new Set([
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/webp",
            "image/gif",
        ]);

        const ROTAS = {
            CHAT: "/app/api/chat",
            STATUS_LAUDO: "/app/api/laudo/status",
            INICIAR_LAUDO: "/app/api/laudo/iniciar",
            CANCELAR_LAUDO: "/app/api/laudo/cancelar",
            UPLOAD_DOC: "/app/api/upload_doc",
            GERAR_PDF: "/app/api/gerar_pdf",
            FEEDBACK: "/app/api/feedback",
        };

        function nomesEventoTariel(nomeOuChave) {
            const helperGlobal = sharedGlobals.inspectorEvents;
            if (typeof helperGlobal?.namesFor === "function") {
                return helperGlobal.namesFor(nomeOuChave);
            }
            return [String(nomeOuChave || "").trim()].filter(Boolean);
        }

        const EVENTOS = {
            LAUDO_CRIADO: nomesEventoTariel("tariel:laudo-criado"),
            RELATORIO_INICIADO: nomesEventoTariel("tariel:relatorio-iniciado"),
            RELATORIO_FINALIZADO: nomesEventoTariel("tariel:relatorio-finalizado"),
            RELATORIO_CANCELADO: nomesEventoTariel("tariel:cancelar-relatorio"),
            ESTADO_RELATORIO: nomesEventoTariel("tariel:estado-relatorio"),
            CMD_SISTEMA: nomesEventoTariel("tariel:disparar-comando-sistema"),
            MESA_STATUS: nomesEventoTariel("tariel:mesa-status"),
            GATE_QUALIDADE_FALHOU: nomesEventoTariel("tariel:gate-qualidade-falhou"),
        };

        const LIMITE_DOC_BYTES = 15 * 1024 * 1024;
        const LIMITE_IMG_BYTES = 10 * 1024 * 1024;
        const TIMEOUT_STREAM_MS = 120000;
        const TIMEOUT_DOC_MS = 60000;
        const TIMEOUT_PDF_MS = 30000;
        const MIN_REPORT_GENERATION_UI_MS = 3000;
        const CACHE_STATUS_RELATORIO_MS = 700;
        const JANELA_SUPRESSAO_ESTADO_RELATORIO_MS = 900;
        const PERF = sharedGlobals.perf;

        // =========================================================
        // ESTADO INTERNO
        // =========================================================
        const estadoInterno = {
            comandoSistemaEmExecucao: false,
            statusRelatorioInflight: null,
            statusRelatorioCache: null,
            ultimaAssinaturaStatusEmitida: "",
            ultimaEmissaoStatusMs: 0,
            ultimaMutacaoEstadoMs: 0,
        };
        let removerListenerComandoSistema = null;

        // =========================================================
        // HELPERS COMPARTILHADOS (UTIL MODULE)
        // =========================================================
        const criarUtils =
            InspectorRuntime?.resolveGlobal?.("TarielChatNetworkUtilsFactory")
            || window.TarielChatNetworkUtilsFactory;
        if (typeof criarUtils !== "function") {
            throw new Error("chat-network-utils.js nao carregado antes de chat-network.js");
        }

        const utils = criarUtils({
            EVENTOS,
            comCabecalhoCSRF,
            criarFormDataComCSRF,
            getEstadoRelatorio,
            getModoAtual,
            getControllerStream,
            setControllerStream,
            getLaudoAtualId,
            setLaudoAtualId,
            setHistoricoConversa,
            setUltimoDiagnosticoBruto,
            setArquivoPendente,
            setImagemBase64Pendente,
            setTextoDocumentoPendente,
            setNomeDocumentoPendente,
            setIaRespondendo,
            ocultarDigitando,
            atualizarEstadoBotao,
            previewContainer,
            inputAnexo,
            telaBoasVindas,
        });

        const {
            limparTimeoutSeguro,
            obterDataAtualBR,
            nomeArquivoLaudo,
            remetenteEhEngenharia,
            normalizarEstadoRelatorio,
            estadoRelatorioLegacy,
            obterModoAtualSeguro,
            criarHeadersJSON,
            criarHeadersSSE,
            criarHeadersSemContentType,
            criarFormDataSeguro,
            extrairErroHTTPDetalhado,
            extrairMensagemErroHTTP,
            criarErroHttp,
            tratarGateQualidadeErroHTTP,
            emitirEvento,
            emitirLaudoCriado,
            emitirRelatorioIniciado,
            emitirRelatorioFinalizado,
            emitirRelatorioCancelado,
            emitirStatusMesa,
            abortarStreamAtivo,
            notificarLaudoCriadoSeMudou,
            limparPreview,
            limparEstadoConversa,
            exibirBoasVindas,
            ocultarBoasVindas,
        } = utils;

        function emitirStatusChat(status = "pronto", texto = "", extra = {}) {
            emitirEvento("tariel:chat-status", {
                status: String(status || "pronto"),
                texto: String(texto || "").trim(),
                ...extra,
            });
        }

        const CaseLifecycle = sharedGlobals.caseLifecycle;
        if (!CaseLifecycle) {
            log("error", "TarielCaseLifecycle não está disponível.");
            return null;
        }

        function clonarPayloadStatusRelatorio(payload) {
            if (!payload || typeof payload !== "object") return null;

            return {
                ...payload,
                allowed_next_lifecycle_statuses: Array.isArray(
                    payload?.allowed_next_lifecycle_statuses
                )
                    ? [...payload.allowed_next_lifecycle_statuses]
                    : [],
                allowed_lifecycle_transitions: Array.isArray(
                    payload?.allowed_lifecycle_transitions
                )
                    ? payload.allowed_lifecycle_transitions.map((item) =>
                        item && typeof item === "object" ? { ...item } : item
                    )
                    : [],
                allowed_surface_actions: Array.isArray(payload?.allowed_surface_actions)
                    ? [...payload.allowed_surface_actions]
                    : [],
                public_verification:
                    payload?.public_verification && typeof payload.public_verification === "object"
                        ? { ...payload.public_verification }
                        : payload?.public_verification ?? null,
                emissao_oficial:
                    payload?.emissao_oficial && typeof payload.emissao_oficial === "object"
                        ? { ...payload.emissao_oficial }
                        : payload?.emissao_oficial ?? null,
                laudo_card: payload?.laudo_card && typeof payload.laudo_card === "object"
                    ? {
                        ...payload.laudo_card,
                        allowed_next_lifecycle_statuses: Array.isArray(
                            payload?.laudo_card?.allowed_next_lifecycle_statuses
                        )
                            ? [...payload.laudo_card.allowed_next_lifecycle_statuses]
                            : [],
                        allowed_lifecycle_transitions: Array.isArray(
                            payload?.laudo_card?.allowed_lifecycle_transitions
                        )
                            ? payload.laudo_card.allowed_lifecycle_transitions.map((item) =>
                                item && typeof item === "object" ? { ...item } : item
                            )
                            : [],
                        allowed_surface_actions: Array.isArray(
                            payload?.laudo_card?.allowed_surface_actions
                        )
                            ? [...payload.laudo_card.allowed_surface_actions]
                            : [],
                    }
                    : payload?.laudo_card ?? null,
            };
        }

        const normalizarCaseLifecycleStatus = (valor) =>
            CaseLifecycle.normalizarCaseLifecycleStatus(valor);
        const normalizarCaseWorkflowMode = (valor) =>
            CaseLifecycle.normalizarCaseWorkflowMode(valor);
        const normalizarActiveOwnerRole = (valor) =>
            CaseLifecycle.normalizarActiveOwnerRole(valor);
        const normalizarAllowedSurfaceActions = (valor = []) =>
            CaseLifecycle.normalizarAllowedSurfaceActions(valor);
        const normalizarAllowedLifecycleTransitions = (valor = []) =>
            CaseLifecycle.normalizarAllowedLifecycleTransitions(valor);

        function normalizarPayloadStatusRelatorio(dados = {}) {
            const estado = normalizarEstadoRelatorio(dados?.estado);
            const laudoId =
                Number(dados?.laudo_id ?? dados?.laudoId ?? dados?.laudoid ?? 0) || null;
            const laudoCard =
                dados?.laudo_card && typeof dados.laudo_card === "object"
                    ? { ...dados.laudo_card }
                    : dados?.laudo_card ?? null;
            const caseLifecycleStatus = normalizarCaseLifecycleStatus(
                dados?.case_lifecycle_status ?? laudoCard?.case_lifecycle_status
            );
            const caseWorkflowMode = normalizarCaseWorkflowMode(
                dados?.case_workflow_mode ?? laudoCard?.case_workflow_mode
            );
            const activeOwnerRole = normalizarActiveOwnerRole(
                dados?.active_owner_role ?? laudoCard?.active_owner_role
            );
            const allowedNextLifecycleStatuses = Array.isArray(
                dados?.allowed_next_lifecycle_statuses
            )
                ? dados.allowed_next_lifecycle_statuses
                : Array.isArray(laudoCard?.allowed_next_lifecycle_statuses)
                    ? laudoCard.allowed_next_lifecycle_statuses
                    : [];
            const allowedLifecycleTransitions = Array.isArray(
                dados?.allowed_lifecycle_transitions
            )
                ? dados.allowed_lifecycle_transitions
                : Array.isArray(laudoCard?.allowed_lifecycle_transitions)
                    ? laudoCard.allowed_lifecycle_transitions
                    : [];
            const allowedSurfaceActions = Array.isArray(dados?.allowed_surface_actions)
                ? dados.allowed_surface_actions
                : Array.isArray(laudoCard?.allowed_surface_actions)
                    ? laudoCard.allowed_surface_actions
                    : [];
            const normalizedAllowedNextLifecycleStatuses = allowedNextLifecycleStatuses
                .map((item) => normalizarCaseLifecycleStatus(item))
                .filter(Boolean);
            const normalizedAllowedLifecycleTransitions = normalizarAllowedLifecycleTransitions(
                allowedLifecycleTransitions
            );
            const normalizedAllowedSurfaceActions = normalizarAllowedSurfaceActions(
                allowedSurfaceActions
            );

            return {
                ...dados,
                estado,
                laudo_id: laudoId,
                laudoId,
                laudoid: laudoId,
                laudo_card: laudoCard,
                status_card: String(
                    dados?.status_card ?? laudoCard?.status_card ?? ""
                ).trim().toLowerCase(),
                permite_edicao:
                    typeof dados?.permite_edicao === "boolean"
                        ? dados.permite_edicao
                        : !!laudoCard?.permite_edicao,
                permite_reabrir:
                    typeof dados?.permite_reabrir === "boolean"
                        ? dados.permite_reabrir
                        : !!laudoCard?.permite_reabrir,
                case_lifecycle_status: caseLifecycleStatus,
                case_workflow_mode: caseWorkflowMode,
                active_owner_role: activeOwnerRole,
                allowed_next_lifecycle_statuses: normalizedAllowedNextLifecycleStatuses,
                allowed_lifecycle_transitions: normalizedAllowedLifecycleTransitions,
                allowed_surface_actions: normalizedAllowedSurfaceActions,
                laudo_card: laudoCard
                    ? {
                        ...laudoCard,
                        case_lifecycle_status: caseLifecycleStatus,
                        case_workflow_mode: caseWorkflowMode,
                        active_owner_role: activeOwnerRole,
                        allowed_next_lifecycle_statuses: normalizedAllowedNextLifecycleStatuses,
                        allowed_lifecycle_transitions: normalizedAllowedLifecycleTransitions,
                        allowed_surface_actions: normalizedAllowedSurfaceActions,
                    }
                    : laudoCard,
            };
        }

        function memorizarStatusRelatorio(payload = null) {
            if (!payload || typeof payload !== "object") {
                estadoInterno.statusRelatorioCache = null;
                return;
            }

            estadoInterno.statusRelatorioCache = {
                at: Date.now(),
                payload: clonarPayloadStatusRelatorio(payload),
            };
        }

        function marcarMutacaoEstadoRelatorio() {
            estadoInterno.ultimaMutacaoEstadoMs = Date.now();
        }

        function construirSnapshotLocalStatusRelatorio() {
            const estadoAtual = normalizarEstadoRelatorio(getEstadoRelatorio?.());
            const laudoAtual = Number(getLaudoAtualId?.() || 0) || null;
            const cachePayload =
                estadoInterno.statusRelatorioCache?.payload &&
                typeof estadoInterno.statusRelatorioCache.payload === "object"
                    ? estadoInterno.statusRelatorioCache.payload
                    : null;

            return normalizarPayloadStatusRelatorio({
                ...(cachePayload || {}),
                estado: estadoAtual,
                laudo_id: laudoAtual,
                laudoId: laudoAtual,
                laudoid: laudoAtual,
            });
        }

        function respostaStatusRelatorioObsoleta(snapshot = {}, requestStartedAt = 0) {
            if (Number(requestStartedAt || 0) >= Number(estadoInterno.ultimaMutacaoEstadoMs || 0)) {
                return false;
            }

            const snapshotAtual = construirSnapshotLocalStatusRelatorio();
            return snapshot.estado !== snapshotAtual.estado
                || snapshot.laudo_id !== snapshotAtual.laudo_id;
        }

        function rearmarEmissaoStatusRelatorio() {
            estadoInterno.ultimaAssinaturaStatusEmitida = "";
            estadoInterno.ultimaEmissaoStatusMs = 0;
        }

        function aplicarSnapshotStatusRelatorio(payload = {}) {
            const snapshot = normalizarPayloadStatusRelatorio(payload);
            const laudoId = snapshot.laudo_id;

            setEstadoRelatorio(snapshot.estado);

            if (laudoId) {
                setLaudoAtualId(laudoId);
            } else if (snapshot.estado === "sem_relatorio") {
                setLaudoAtualId(null);
            }

            return snapshot;
        }

        function obterAssinaturaStatusRelatorio(payload = {}) {
            return [
                String(payload?.estado || ""),
                String(payload?.laudo_id || ""),
                String(payload?.status_card || ""),
                String(payload?.case_lifecycle_status || ""),
                String(payload?.case_workflow_mode || ""),
                String(payload?.active_owner_role || ""),
                String((payload?.allowed_next_lifecycle_statuses || []).join(",")),
                String((payload?.allowed_surface_actions || []).join(",")),
                String(
                    (payload?.allowed_lifecycle_transitions || [])
                        .map((item) =>
                            [
                                item?.target_status || "",
                                item?.transition_kind || "",
                                item?.owner_role || "",
                                item?.preferred_surface || "",
                            ].join(":")
                        )
                        .join(",")
                ),
                payload?.permite_edicao ? "1" : "0",
                payload?.permite_reabrir ? "1" : "0",
            ].join("|");
        }

        function emitirSnapshotStatusRelatorio(payload = {}, { forcar = false } = {}) {
            const snapshot = aplicarSnapshotStatusRelatorio(payload);
            const assinatura = obterAssinaturaStatusRelatorio(snapshot);
            const agora = Date.now();
            const repetida =
                !forcar &&
                assinatura &&
                assinatura === estadoInterno.ultimaAssinaturaStatusEmitida &&
                (agora - estadoInterno.ultimaEmissaoStatusMs) < JANELA_SUPRESSAO_ESTADO_RELATORIO_MS;

            if (repetida) {
                PERF?.count?.("chat_network.status_relatorio.evento_suprimido", 1, {
                    category: "request_churn",
                    detail: {
                        laudoId: snapshot.laudo_id,
                        estado: snapshot.estado,
                    },
                });
                return snapshot;
            }

            estadoInterno.ultimaAssinaturaStatusEmitida = assinatura;
            estadoInterno.ultimaEmissaoStatusMs = agora;

            emitirEvento(EVENTOS.ESTADO_RELATORIO, snapshot);
            if (snapshot?.laudo_card?.id) {
                emitirEvento("tariel:laudo-card-sincronizado", {
                    card: snapshot.laudo_card,
                    selecionar: false,
                });
            }

            return snapshot;
        }

        async function solicitarStatusRelatorioBruto({ forcar = false } = {}) {
            const cache = estadoInterno.statusRelatorioCache;
            const cacheValido =
                !forcar &&
                cache?.payload &&
                (Date.now() - Number(cache.at || 0)) < CACHE_STATUS_RELATORIO_MS;

            if (cacheValido) {
                PERF?.count?.("chat_network.status_relatorio.cache_hit", 1, {
                    category: "request_churn",
                    detail: {
                        laudoId: cache.payload?.laudo_id ?? null,
                    },
                });
                return clonarPayloadStatusRelatorio(cache.payload);
            }

            if (!forcar && estadoInterno.statusRelatorioInflight) {
                PERF?.count?.("chat_network.status_relatorio.inflight_reused", 1, {
                    category: "request_churn",
                });
                return estadoInterno.statusRelatorioInflight;
            }

            const requisicao = (async () => {
                const requestStartedAt = Date.now();
                const response = await fetch(ROTAS.STATUS_LAUDO, {
                    credentials: "same-origin",
                    headers: criarHeadersSemContentType(),
                });

                if (!response.ok) return null;

                const dados = await response.json();
                const snapshot = normalizarPayloadStatusRelatorio(dados);
                if (respostaStatusRelatorioObsoleta(snapshot, requestStartedAt)) {
                    const snapshotAtual = construirSnapshotLocalStatusRelatorio();
                    memorizarStatusRelatorio(snapshotAtual);
                    PERF?.count?.("chat_network.status_relatorio.stale_ignored", 1, {
                        category: "request_churn",
                        detail: {
                            requestEstado: snapshot.estado,
                            requestLaudoId: snapshot.laudo_id,
                            localEstado: snapshotAtual.estado,
                            localLaudoId: snapshotAtual.laudo_id,
                        },
                    });
                    return clonarPayloadStatusRelatorio(snapshotAtual);
                }
                memorizarStatusRelatorio(snapshot);
                return clonarPayloadStatusRelatorio(snapshot);
            })();

            estadoInterno.statusRelatorioInflight = requisicao;
            requisicao.finally(() => {
                if (estadoInterno.statusRelatorioInflight === requisicao) {
                    estadoInterno.statusRelatorioInflight = null;
                }
            });

            return requisicao;
        }

        // =========================================================
        // CHIP / PREVIEW DE DOCUMENTO
        // =========================================================
        function criarChipDocumento(id, nome, estado = "carregando") {
            const chip = document.createElement("div");
            chip.id = id;
            chip.className = "preview-item chip-documento-preview chip-doc-estado";
            chip.setAttribute("aria-label", `Documento ${nome}`);

            const icone = estado === "carregando" ? "hourglass_top" : "description";

            chip.innerHTML = `
                <span class="material-symbols-rounded chip-doc-icone" aria-hidden="true">${icone}</span>
                <span class="chip-doc-nome">${escapeHTML(nome)}</span>
                ${
                    estado === "carregando"
                        ? `<span class="chip-doc-status" aria-live="polite">Extraindo texto...</span>`
                        : `<button class="btn-remover-preview" aria-label="Remover documento" type="button">×</button>`
                }
            `;

            if (estado === "pronto") {
                chip.querySelector(".btn-remover-preview")?.addEventListener("click", limparPreview);
            }

            return chip;
        }

        function atualizarChipDocumento(chipId, nome, estado) {
            const antigo = document.getElementById(chipId);
            if (!antigo) return;

            antigo.replaceWith(criarChipDocumento(chipId, nome, estado));
        }

        // =========================================================
        // UPLOAD DE DOCUMENTO
        // =========================================================
        async function carregarDocumento(arquivo) {
            if (!arquivo) return null;

            limparPreview();
            emitirStatusChat("documento", "Extraindo texto do documento...");

            const chipId = `doc-chip-${Date.now()}`;
            const chip = criarChipDocumento(chipId, arquivo.name, "carregando");

            previewContainer?.appendChild(chip);
            atualizarEstadoBotao();

            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), TIMEOUT_DOC_MS);

            try {
                const formData = criarFormDataSeguro();
                formData.append("arquivo", arquivo);

                const response = await fetch(ROTAS.UPLOAD_DOC, {
                    method: "POST",
                    signal: controller.signal,
                    credentials: "same-origin",
                    headers: criarHeadersSemContentType(),
                    body: formData,
                });

                limparTimeoutSeguro(timeout);

                if (!response.ok) {
                    throw new Error(await extrairMensagemErroHTTP(response));
                }

                const dados = await response.json();
                const textoExtraido = String(dados?.texto || "");

                if (!textoExtraido.trim()) {
                    throw new Error("Documento sem texto extraível.");
                }

                setTextoDocumentoPendente(textoExtraido);
                setNomeDocumentoPendente(arquivo.name);
                setArquivoPendente(arquivo);
                setImagemBase64Pendente(null);

                atualizarChipDocumento(chipId, arquivo.name, "pronto");
                atualizarEstadoBotao();
                campoMensagem?.focus();
                emitirStatusChat("pronto", `${arquivo.name} pronto para uso no chat.`);

                mostrarToast(
                    `${arquivo.name} carregado. ${dados?.chars ?? textoExtraido.length} caracteres extraídos.`,
                    "sucesso",
                    3000
                );

                return dados;
            } catch (erro) {
                limparTimeoutSeguro(timeout);
                chip.remove();

                setTextoDocumentoPendente(null);
                setNomeDocumentoPendente(null);
                setArquivoPendente(null);
                atualizarEstadoBotao();

                if (erro?.name === "AbortError") {
                    emitirStatusChat("erro", "Tempo esgotado no processamento do documento.");
                    mostrarToast("Tempo esgotado ao carregar o documento.", "aviso");
                } else {
                    emitirStatusChat("erro", "Falha ao carregar documento.");
                    mostrarToast(`Falha ao carregar documento: ${erro.message}`, "erro");
                }

                log("error", "Erro no upload de documento:", erro);
                return null;
            }
        }

        function prepararArquivoParaEnvio(arquivo) {
            if (!arquivo) return;

            if (MIME_DOCUMENTOS.has(arquivo.type)) {
                if (arquivo.size > LIMITE_DOC_BYTES) {
                    mostrarToast("Documento muito grande, máx. 15 MB.", "aviso");
                    return;
                }

                carregarDocumento(arquivo);
                return;
            }

            if (!MIME_IMAGENS.has(arquivo.type)) {
                mostrarToast(
                    "Suporte a imagens PNG, JPG, WebP e documentos PDF, DOCX.",
                    "aviso"
                );
                return;
            }

            if (arquivo.size > LIMITE_IMG_BYTES) {
                mostrarToast("Imagem muito grande, máx. 10 MB.", "aviso");
                return;
            }

            limparPreview();

            const leitor = new FileReader();

            leitor.onload = (event) => {
                const resultado = event.target?.result;
                const base64Validado = validarPrefixoBase64(resultado);

                if (!base64Validado) {
                    mostrarToast("Arquivo inválido. Tente uma imagem diferente.", "erro");
                    return;
                }

                setArquivoPendente(arquivo);
                setImagemBase64Pendente(base64Validado);
                setTextoDocumentoPendente(null);
                setNomeDocumentoPendente(null);

                if (!previewContainer) {
                    atualizarEstadoBotao();
                    campoMensagem?.focus();
                    return;
                }

                previewContainer.innerHTML = "";

                const item = document.createElement("div");
                item.className = "preview-item";

                const thumb = document.createElement("img");
                thumb.src = base64Validado;
                thumb.alt = "Preview da evidência";
                thumb.className = "preview-thumb";

                const btnRemover = document.createElement("button");
                btnRemover.type = "button";
                btnRemover.className = "btn-remover-preview";
                btnRemover.setAttribute("aria-label", "Remover imagem");
                btnRemover.textContent = "×";
                btnRemover.addEventListener("click", limparPreview);

                item.appendChild(thumb);
                item.appendChild(btnRemover);
                previewContainer.appendChild(item);

                atualizarEstadoBotao();
                campoMensagem?.focus();
            };

            leitor.onerror = () => {
                mostrarToast("Erro ao ler o arquivo. Tente novamente.", "erro");
                log("error", "FileReader falhou ao processar imagem.");
            };

            leitor.readAsDataURL(arquivo);
        }

        // =========================================================
        // ESTADO DO RELATÓRIO
        // =========================================================
        async function sincronizarEstadoRelatorio(opcoes = {}) {
            try {
                const dados = await solicitarStatusRelatorioBruto(opcoes);
                if (!dados) return null;
                return emitirSnapshotStatusRelatorio(dados, {
                    forcar: opcoes?.forcarEvento === true,
                });
            } catch (erro) {
                log("warn", "Falha ao sincronizar estado do relatório:", erro);
                return null;
            }
        }

        async function consultarStatusRelatorioAtual(opcoes = {}) {
            try {
                const dados = await solicitarStatusRelatorioBruto(opcoes);
                if (!dados) {
                    return {
                        estado: normalizarEstadoRelatorio(getEstadoRelatorio?.()),
                        laudoId: Number(getLaudoAtualId?.() || 0) || null,
                    };
                }
                const snapshot = aplicarSnapshotStatusRelatorio(dados);
                return {
                    estado: snapshot.estado,
                    laudoId: snapshot.laudo_id,
                    permiteEdicao: !!snapshot?.permite_edicao,
                    permiteReabrir: !!snapshot?.permite_reabrir,
                    publicVerification:
                        snapshot?.public_verification && typeof snapshot.public_verification === "object"
                            ? { ...snapshot.public_verification }
                            : null,
                    caseLifecycleStatus: snapshot.case_lifecycle_status || "",
                    caseWorkflowMode: snapshot.case_workflow_mode || "",
                    activeOwnerRole: snapshot.active_owner_role || "",
                    allowedNextLifecycleStatuses: Array.isArray(
                        snapshot.allowed_next_lifecycle_statuses
                    )
                        ? [...snapshot.allowed_next_lifecycle_statuses]
                        : [],
                    allowedLifecycleTransitions: Array.isArray(
                        snapshot.allowed_lifecycle_transitions
                    )
                        ? snapshot.allowed_lifecycle_transitions.map((item) =>
                            item && typeof item === "object" ? { ...item } : item
                        )
                        : [],
                    allowedSurfaceActions: Array.isArray(
                        snapshot.allowed_surface_actions
                    )
                        ? [...snapshot.allowed_surface_actions]
                        : [],
                };
            } catch (_) {
                return {
                    estado: normalizarEstadoRelatorio(getEstadoRelatorio?.()),
                    laudoId: Number(getLaudoAtualId?.() || 0) || null,
                    permiteEdicao: normalizarEstadoRelatorio(getEstadoRelatorio?.()) === "relatorio_ativo",
                    permiteReabrir: false,
                    publicVerification: null,
                    caseLifecycleStatus: "",
                    caseWorkflowMode: "",
                    activeOwnerRole: "",
                    allowedNextLifecycleStatuses: [],
                    allowedLifecycleTransitions: [],
                    allowedSurfaceActions: [],
                };
            }
        }

        async function iniciarRelatorio(tipoTemplate, contextoInicial = null) {
            if (!tipoTemplate) return null;

            const form = criarFormDataSeguro();
            form.append("tipo_template", tipoTemplate);
            form.append("tipotemplate", tipoTemplate);
            const entryModePreference = String(
                contextoInicial?.entryModePreference ||
                contextoInicial?.entry_mode_preference ||
                ""
            ).trim();
            const dadosFormulario = (
                contextoInicial && typeof contextoInicial === "object"
                    ? (contextoInicial.dadosFormulario || contextoInicial)
                    : {}
            );
            if (entryModePreference) {
                form.append("entry_mode_preference", entryModePreference);
            }
            ["cliente", "unidade", "local_inspecao", "objetivo", "nome_inspecao"].forEach((campo) => {
                const valor = String(dadosFormulario?.[campo] || "").trim();
                if (valor) {
                    form.append(campo, valor);
                }
            });

            try {
                const response = await fetch(ROTAS.INICIAR_LAUDO, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: criarHeadersSemContentType(),
                    body: form,
                });

                if (!response.ok) {
                    throw new Error(await extrairMensagemErroHTTP(response));
                }

                const dados = await response.json();
                const laudoId =
                    Number(dados?.laudo_id ?? dados?.laudoId ?? dados?.laudoid ?? 0) || null;

                limparEstadoConversa({ limparLaudoAtual: false });
                limparAreaMensagens();
                ocultarBoasVindas();

                const estadoResposta = normalizarEstadoRelatorio(dados?.estado || "sem_relatorio");
                setEstadoRelatorio(estadoResposta);
                setLaudoAtualId(laudoId);
                marcarMutacaoEstadoRelatorio();

                if (estadoResposta === "relatorio_ativo") {
                    emitirRelatorioIniciado(laudoId, tipoTemplate);
                } else {
                    emitirLaudoCriado(laudoId);
                }

                memorizarStatusRelatorio({
                    ...dados,
                    estado: estadoResposta,
                    laudo_id: laudoId,
                    laudoId,
                    laudoid: laudoId,
                });
                rearmarEmissaoStatusRelatorio();

                mostrarToast(dados?.message ?? "Relatório iniciado!", "sucesso", 4000);
                log("info", `Relatório iniciado. tipo=${tipoTemplate} laudoId=${laudoId}`);

                return {
                    ...dados,
                    estado: estadoResposta,
                    laudo_id: laudoId,
                };
            } catch (erro) {
                mostrarToast(`Falha ao iniciar relatório: ${erro.message}`, "erro");
                log("error", "iniciarRelatorio:", erro);
                return null;
            }
        }

        async function finalizarRelatorioDireto(opcoes = {}) {
            const laudoId = Number(getLaudoAtualId?.() || 0) || null;

            if (!laudoId) {
                mostrarToast("Nenhum relatório ativo para finalizar.", "aviso");
                return null;
            }

            if (getIaRespondendo?.()) {
                mostrarToast("Aguarde a IA terminar antes de finalizar.", "aviso");
                return null;
            }

            const form = criarFormDataSeguro();
            const qualityGateOverride = opcoes?.qualityGateOverride;
            if (qualityGateOverride && typeof qualityGateOverride === "object") {
                if (qualityGateOverride.enabled === true) {
                    form.append("quality_gate_override", "true");
                }
                const reason = String(qualityGateOverride.reason || "").trim();
                if (reason) {
                    form.append("quality_gate_override_reason", reason);
                }
                const cases = Array.isArray(qualityGateOverride.cases)
                    ? qualityGateOverride.cases
                        .map((item) => String(item || "").trim())
                        .filter(Boolean)
                    : [];
                if (cases.length) {
                    form.append("quality_gate_override_cases", cases.join(","));
                }
            }

            try {
                const response = await fetch(`/app/api/laudo/${laudoId}/finalizar`, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: criarHeadersSemContentType(),
                    body: form,
                });

                if (!response.ok) {
                    const detalheErro = await extrairErroHTTPDetalhado(response);
                    tratarGateQualidadeErroHTTP(detalheErro, {
                        origem: "finalizar-direto",
                        laudo_id: laudoId,
                    });
                    throw criarErroHttp(detalheErro);
                }

                const dados = await response.json();
                const estadoResposta = normalizarEstadoRelatorio(dados?.estado || "aguardando");
                setEstadoRelatorio(estadoResposta);
                setLaudoAtualId(laudoId);
                marcarMutacaoEstadoRelatorio();
                if (dados?.laudo_card?.id) {
                    emitirEvento("tariel:laudo-card-sincronizado", {
                        card: dados.laudo_card,
                        selecionar: true,
                    });
                }
                emitirRelatorioFinalizado(laudoId, {
                    estado: estadoResposta,
                    status_card: dados?.status_card || dados?.laudo_card?.status_card || "",
                    case_lifecycle_status: dados?.case_lifecycle_status,
                    case_workflow_mode: dados?.case_workflow_mode,
                    active_owner_role: dados?.active_owner_role,
                    allowed_next_lifecycle_statuses: Array.isArray(
                        dados?.allowed_next_lifecycle_statuses
                    )
                        ? dados.allowed_next_lifecycle_statuses
                        : [],
                    allowed_lifecycle_transitions: Array.isArray(
                        dados?.allowed_lifecycle_transitions
                    )
                        ? dados.allowed_lifecycle_transitions
                        : [],
                    allowed_surface_actions: Array.isArray(dados?.allowed_surface_actions)
                        ? dados.allowed_surface_actions
                        : [],
                    laudo_card: dados?.laudo_card ?? null,
                });
                memorizarStatusRelatorio({
                    ...dados,
                    estado: estadoResposta,
                    laudo_id: laudoId,
                    laudoId,
                    laudoid: laudoId,
                });
                rearmarEmissaoStatusRelatorio();

                mostrarToast(
                    dados?.message ?? "Relatorio enviado para a mesa!",
                    "sucesso",
                    5000
                );

                return dados;
            } catch (erro) {
                mostrarToast(`Falha ao finalizar: ${erro.message}`, "erro");
                log("error", "finalizarRelatorioDireto:", erro);
                return null;
            }
        }

        async function finalizarViaComandoSistema(tipoTemplate = "padrao") {
            const laudoId = Number(getLaudoAtualId?.() || 0) || null;

            if (!laudoId) {
                mostrarToast("Nenhum relatório ativo para finalizar.", "aviso");
                return null;
            }

            if (getIaRespondendo?.()) {
                mostrarToast("Aguarde a IA terminar antes de finalizar.", "aviso");
                return null;
            }

            const comando = `COMANDO_SISTEMA FINALIZARLAUDOAGORA TIPO ${String(
                tipoTemplate || "padrao"
            ).trim().toLowerCase()}`;

            const resposta = await enviarParaIA(
                comando,
                null,
                "geral",
                null,
                null,
                null,
                true
            );

            if (!resposta?.ok) return null;
            const snapshot = await sincronizarEstadoRelatorio();
            emitirRelatorioFinalizado(laudoId, {
                estado: snapshot?.estado || "aguardando",
                status_card: snapshot?.status_card || snapshot?.laudo_card?.status_card || "",
                case_lifecycle_status: snapshot?.case_lifecycle_status || "",
                case_workflow_mode: snapshot?.case_workflow_mode || "",
                active_owner_role: snapshot?.active_owner_role || "",
                allowed_next_lifecycle_statuses: Array.isArray(
                    snapshot?.allowed_next_lifecycle_statuses
                )
                    ? snapshot.allowed_next_lifecycle_statuses
                    : [],
                allowed_lifecycle_transitions: Array.isArray(
                    snapshot?.allowed_lifecycle_transitions
                )
                    ? snapshot.allowed_lifecycle_transitions
                    : [],
                allowed_surface_actions: Array.isArray(snapshot?.allowed_surface_actions)
                    ? snapshot.allowed_surface_actions
                    : [],
                laudo_card: snapshot?.laudo_card ?? null,
            });

            mostrarToast("Relatorio enviado para a mesa!", "sucesso", 5000);

            return resposta;
        }

        async function finalizarRelatorio(opcoes = {}) {
            const tipoTemplate = opcoes?.tipoTemplate || window.tipoTemplateAtivo || "padrao";

            if (opcoes?.direto === true) {
                return finalizarRelatorioDireto(opcoes);
            }

            return finalizarViaComandoSistema(tipoTemplate);
        }

        async function cancelarRelatorio() {
            const laudoIdAtual = Number(getLaudoAtualId?.() || 0) || null;
            const form = criarFormDataSeguro();

            try {
                const response = await fetch(ROTAS.CANCELAR_LAUDO, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: criarHeadersSemContentType(),
                    body: form,
                });

                if (!response.ok) {
                    throw new Error(await extrairMensagemErroHTTP(response));
                }

                const dados = await response.json();

                setEstadoRelatorio("sem_relatorio");
                limparEstadoConversa({ limparLaudoAtual: true });
                limparAreaMensagens();
                exibirBoasVindas();
                marcarMutacaoEstadoRelatorio();
                emitirRelatorioCancelado(laudoIdAtual);
                memorizarStatusRelatorio({
                    ...dados,
                    estado: "sem_relatorio",
                    laudo_id: null,
                    laudoId: null,
                    laudoid: null,
                });
                rearmarEmissaoStatusRelatorio();

                mostrarToast(dados?.message ?? "Relatório cancelado.", "aviso", 3000);
                return dados;
            } catch (erro) {
                log("warn", "cancelarRelatorio:", erro);
                mostrarToast(`Falha ao cancelar relatório: ${erro.message}`, "erro", 3500);
                return null;
            }
        }

        // =========================================================
        // FEEDBACK E PDF
        // =========================================================
        async function enviarFeedback(tipo, textoBolha) {
            try {
                await fetch(ROTAS.FEEDBACK, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: criarHeadersJSON(),
                    body: JSON.stringify({
                        tipo,
                        trecho: String(textoBolha || "").slice(0, 500),
                    }),
                });
            } catch (_) {}
        }

        function dispararDownload(blob, tipo, nomeArquivo) {
            const arquivo = blob instanceof Blob ? blob : new Blob([blob], { type: tipo });
            const url = URL.createObjectURL(arquivo);

            const link = document.createElement("a");
            link.href = url;
            link.download = nomeArquivo;

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            setTimeout(() => URL.revokeObjectURL(url), 10000);
        }

        async function gerarPDF() {
            const diagnostico = String(getUltimoDiagnosticoBruto?.() || "").trim();
            if (!diagnostico) return;

            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), TIMEOUT_PDF_MS);

            try {
                const response = await fetch(ROTAS.GERAR_PDF, {
                    method: "POST",
                    signal: controller.signal,
                    credentials: "same-origin",
                    headers: criarHeadersJSON({
                        Accept: "application/pdf",
                    }),
                    body: JSON.stringify({
                        diagnostico,
                        inspetor: getNomeUsuario(),
                        empresa: getNomeEmpresa(),
                        setor: sanitizarSetor(setorSelect?.value || "geral"),
                        data: obterDataAtualBR(),
                        laudo_id: Number(getLaudoAtualId?.() || 0) || null,
                        tipo_template: String(window.tipoTemplateAtivo || "padrao").trim().toLowerCase(),
                    }),
                });

                limparTimeoutSeguro(timeout);

                if (!response.ok) {
                    throw new Error(await extrairMensagemErroHTTP(response));
                }

                const contentType = response.headers.get("content-type") || "";
                if (!contentType.includes("application/pdf")) {
                    throw new Error("RESPOSTA_NAO_PDF");
                }

                const blob = await response.blob();

                dispararDownload(blob, "application/pdf", nomeArquivoLaudo("pdf"));
            } catch (erro) {
                limparTimeoutSeguro(timeout);

                if (erro?.name === "AbortError") {
                    mostrarToast("A geração do PDF demorou muito. Tente novamente.", "aviso");
                    return;
                }

                log("warn", `PDF backend falhou (${erro.message}). Usando fallback TXT.`);

                const conteudo = [
                    "LAUDO TÉCNICO — TARIEL.IA",
                    `Inspetor: ${getNomeUsuario()}`,
                    `Empresa: ${getNomeEmpresa()}`,
                    `Setor: ${String(sanitizarSetor(setorSelect?.value || "geral")).toUpperCase()}`,
                    `Data: ${obterDataAtualBR()}`,
                    "-".repeat(60),
                    "",
                    diagnostico,
                ].join("\n");

                dispararDownload(
                    new Blob([conteudo], { type: "text/plain;charset=utf-8" }),
                    "text/plain",
                    nomeArquivoLaudo("txt")
                );

                mostrarToast("PDF indisponível. Laudo exportado como .txt.", "aviso", 5000);
            }
        }

        // =========================================================
        // RENDERIZAÇÃO DE ERRO
        // =========================================================
        function criarBolhaErro(mensagem, titulo = "Erro de conexão") {
            const bolha = criarBolhaIA(obterModoAtualSeguro());
            const texto = bolha?.querySelector(".texto-msg");
            const cursor = bolha?.querySelector(".cursor-piscando");

            cursor?.remove();

            if (texto) {
                texto.innerHTML = renderizarMarkdown(`**${titulo}**\n\n${mensagem}`);
            }

            return bolha;
        }

        function classificarErroChat(erro) {
            const textoErro = String(erro?.message || "").trim();
            const ehCodigoHttpCru = /^HTTP_\d+$/i.test(textoErro);

            let titulo = "Erro de conexão";
            let mensagem = "Não foi possível contactar o servidor. Tente novamente.";

            if (erro?.name === "AbortError") {
                return {
                    titulo: "Tempo limite",
                    mensagem: "Conexão encerrada. O tempo limite foi atingido.",
                };
            }

            if (textoErro && !ehCodigoHttpCru) {
                mensagem = textoErro;
            }

            const textoNormalizado = mensagem.toLowerCase();

            if (
                textoNormalizado.includes("use apenas o relatório ativo") ||
                textoNormalizado.includes("não pode receber novas mensagens") ||
                textoNormalizado.includes("não pode ser editado") ||
                textoNormalizado.includes("não pode ser excluído")
            ) {
                titulo = "Ação bloqueada";
            } else if (textoNormalizado.includes("csrf")) {
                titulo = "Sessão expirada";
            } else if (textoNormalizado.includes("acesso negado")) {
                titulo = "Permissão insuficiente";
            }

            return { titulo, mensagem };
        }

        function anexosRespostaValidos(anexos = []) {
            return Array.isArray(anexos) ? anexos.filter((item) => item && typeof item === "object") : [];
        }

        function aguardar(ms = 0) {
            const atraso = Number(ms || 0);
            if (!Number.isFinite(atraso) || atraso <= 0) {
                return Promise.resolve();
            }
            return new Promise((resolve) => window.setTimeout(resolve, atraso));
        }

        function garantirJanelaMinimaRelatorio(requestStartedAtMs = 0) {
            const inicio = Number(requestStartedAtMs || 0);
            if (!Number.isFinite(inicio) || inicio <= 0) {
                return Promise.resolve();
            }
            const restante = Math.max(0, MIN_REPORT_GENERATION_UI_MS - (Date.now() - inicio));
            return aguardar(restante);
        }

        function parecePedidoRelatorioLivre(texto = "") {
            const normalizado = String(texto || "")
                .normalize("NFD")
                .replace(/[\u0300-\u036f]/g, "")
                .trim()
                .toLowerCase();

            if (!normalizado) return false;

            const pedeDocumento = /(relatorio|laudo|pdf)\b/.test(normalizado);
            const pedeGeracao = /\b(gera|gerar|gerado|cria|criar|crie|faca|faz|monta|monte|produza)\b/.test(normalizado)
                || normalizado.includes("em pdf")
                || normalizado.includes("profissional");

            return pedeDocumento && pedeGeracao;
        }

        function respostaPossuiPdf(anexos = []) {
            return anexos.some((item) => {
                const mimeType = String(item?.mime_type || "").trim().toLowerCase();
                const nome = String(item?.nome || item?.filename || item?.titulo || "").trim().toLowerCase();
                return mimeType === "application/pdf" || nome.endsWith(".pdf");
            });
        }

        function consumirObjetoHumano(objeto, tmpId, invisivel) {
            if (tmpId) atualizarTiquesStatus(tmpId, "lido");
            if (invisivel) return true;

            const remetente = String(objeto?.remetente || "").toLowerCase();
            const texto = String(objeto?.texto || "");
            const laudoId = Number(objeto?.laudo_id ?? objeto?.laudoId ?? getLaudoAtualId?.() ?? 0) || null;

            if (remetenteEhEngenharia(remetente) && typeof window.adicionarMensagemNaUI === "function") {
                window.adicionarMensagemNaUI(
                    "engenharia",
                    texto,
                    objeto?.tipo || "humanoeng",
                    {
                        mensagemId: Number(objeto?.mensagem_id ?? objeto?.id ?? 0) || null,
                        referenciaMensagemId: Number(objeto?.referencia_mensagem_id ?? 0) || null,
                    }
                );
                emitirStatusMesa("respondeu", {
                    origem: "mesa",
                    laudoId,
                    preview: texto.slice(0, 120),
                });
                emitirStatusChat("mesa", "Nova interação com a mesa avaliadora.");
            } else {
                mostrarToast("Mensagem enviada para a mesa avaliadora.", "sucesso", 1800);
                emitirStatusMesa("aguardando", {
                    origem: "inspetor",
                    laudoId,
                    preview: texto.slice(0, 120),
                });
                emitirStatusChat("mesa", "Mensagem encaminhada para a mesa avaliadora.");
            }

            return true;
        }

        // =========================================================
        // RESPOSTA JSON DIRETA
        // =========================================================
        async function consumirRespostaJSON(response, opcoes = {}) {
            const {
                invisivel = false,
                tmpId = null,
                modoAtual = "detalhado",
                requestStartedAtMs = 0,
            } = opcoes;

            const dados = await response.json();
            const texto = String(dados?.texto || dados?.mensagem || "");
            const anexosResposta = anexosRespostaValidos(dados?.anexos);
            const ehRelatorioLivre = String(dados?.tipo || "").trim().toLowerCase() === "relatorio_chat_livre";

            if (tmpId) {
                atualizarTiquesStatus(tmpId, "entregue");
            }

            if (!invisivel && ehRelatorioLivre) {
                emitirStatusChat("respondendo", "Gerando relatório técnico...");
                mostrarDigitando("Gerando relatório técnico...");
                await garantirJanelaMinimaRelatorio(requestStartedAtMs);
            }

            ocultarDigitando();

            let elementoIA = null;
            let elementoTexto = null;

            if (!invisivel) {
                elementoIA = criarBolhaIA(modoAtual, {
                    mensagemId: Number(dados?.mensagem_id ?? dados?.id ?? 0) || null,
                });
                elementoTexto = elementoIA?.querySelector(".texto-msg");
            }

            const laudoJson = dados?.laudo_id ?? dados?.laudoId ?? dados?.laudoid ?? null;
            if (laudoJson) {
                notificarLaudoCriadoSeMudou(Number(laudoJson));
            }
            if (dados?.laudo_card?.id) {
                emitirEvento("tariel:laudo-card-sincronizado", {
                    card: dados.laudo_card,
                    selecionar: true,
                });
            }

            if (!invisivel && elementoTexto) {
                elementoTexto.innerHTML = renderizarMarkdown(texto);
            }

            if (!invisivel) {
                setUltimoDiagnosticoBruto(texto);

                if (texto) {
                    adicionarAoHistorico("assistente", texto);
                }

                if (elementoIA) {
                    if (Array.isArray(dados?.citacoes) && dados.citacoes.length) {
                        renderizarCitacoes(elementoIA, dados.citacoes);
                    }
                    if (dados?.confianca_ia && typeof dados.confianca_ia === "object") {
                        renderizarConfiancaIA(elementoIA, dados.confianca_ia);
                    }
                    if (anexosResposta.length) {
                        renderizarAnexosMensagem(elementoIA, anexosResposta, null, {
                            destacarPdfPrincipal:
                                dados?.tipo === "relatorio_chat_livre" || respostaPossuiPdf(anexosResposta),
                        });
                    }

                    if (texto) {
                        mostrarAcoesPosResposta(elementoIA, texto);
                    }
                }
            }

            if (tmpId) {
                atualizarTiquesStatus(tmpId, "lido");
            }

            try {
                await sincronizarEstadoRelatorio();
            } catch (_) {}

            emitirStatusChat("pronto", "Assistente pronto para a próxima interação.");

            return {
                ok: true,
                texto,
                laudoId: getLaudoAtualId?.() || null,
                anexos: anexosResposta,
                citacoes: Array.isArray(dados?.citacoes) ? dados.citacoes : [],
                confianca: dados?.confianca_ia && typeof dados.confianca_ia === "object" ? dados.confianca_ia : null,
            };
        }

        // =========================================================
        // ENVIO PRINCIPAL PARA IA
        // =========================================================
        async function enviarParaIA(
            mensagem,
            dadosImagem = null,
            setor = "geral",
            textoDocumento = null,
            nomeDocumento = null,
            tmpId = null,
            invisivel = false
        ) {
            if (!mensagem && !dadosImagem && !textoDocumento) return null;

            setIaRespondendo(true);
            atualizarEstadoBotao();
            const pedidoRelatorioLivre = parecePedidoRelatorioLivre(mensagem);
            emitirStatusChat(
                "respondendo",
                pedidoRelatorioLivre
                    ? "Gerando relatório técnico..."
                    : "Assistente analisando evidências e contexto..."
            );

            if (!invisivel) {
                mostrarDigitando(
                    pedidoRelatorioLivre
                        ? "Gerando relatório técnico..."
                        : "Assistente analisando evidências e contexto..."
                );
            }

            abortarStreamAtivo();

            const controller = new AbortController();
            setControllerStream(controller);

            const timeout = setTimeout(() => {
                try {
                    controller.__tarielAbortReason = "timeout";
                    controller.abort();
                } catch (_) {}

                log("warn", "Stream SSE cancelado por timeout.");
            }, TIMEOUT_STREAM_MS);

            let elementoIA = null;
            let elementoTexto = null;
            let cursor = null;
            let textoAcumulado = "";
            let anexosPendentes = [];
            let citacoesPendentes = [];
            let confiancaPendente = null;
            let streamCompleto = false;
            let statusFinalChat = "pronto";
            let textoStatusFinal = "Assistente pronto para a próxima interação.";
            const requestStartedAtMs = Date.now();

            const modoAtual = obterModoAtualSeguro();

            try {
                const response = await fetch(ROTAS.CHAT, {
                    method: "POST",
                    signal: controller.signal,
                    credentials: "same-origin",
                    headers: criarHeadersSSE(),
                    body: JSON.stringify({
                        mensagem: mensagem || "",
                        dados_imagem: dadosImagem ? validarPrefixoBase64(dadosImagem) : "",
                        setor: sanitizarSetor(setor || "geral"),
                        historico: (getHistoricoConversa?.() || []).slice(-20),
                        modo: modoAtual,
                        texto_documento: textoDocumento || "",
                        nome_documento: nomeDocumento || "",
                        laudo_id: getLaudoAtualId?.() ? Number(getLaudoAtualId()) : null,
                    }),
                });

                limparTimeoutSeguro(timeout);

                if (!response.ok) {
                    const detalheErro = await extrairErroHTTPDetalhado(response);
                    tratarGateQualidadeErroHTTP(detalheErro, {
                        origem: "chat",
                        laudo_id: Number(getLaudoAtualId?.() || 0) || null,
                    });
                    throw criarErroHttp(detalheErro);
                }

                const contentType = response.headers.get("content-type") || "";

                if (
                    !contentType.includes("text/event-stream") &&
                    !contentType.includes("application/json")
                ) {
                    throw new Error("CONTENT_TYPE_INESPERADO");
                }

                if (contentType.includes("application/json")) {
                    return await consumirRespostaJSON(response, {
                        invisivel,
                        tmpId,
                        modoAtual,
                        requestStartedAtMs,
                    });
                }

                if (tmpId) {
                    atualizarTiquesStatus(tmpId, "entregue");
                }

                ocultarDigitando();

                if (!invisivel) {
                    elementoIA = criarBolhaIA(modoAtual);
                    elementoTexto = elementoIA?.querySelector(".texto-msg");
                    cursor = elementoIA?.querySelector(".cursor-piscando");
                }

                const leitor = response.body?.getReader?.();
                if (!leitor) {
                    throw new Error("STREAM_INDISPONIVEL");
                }

                const decoder = new TextDecoder();
                let buffer = "";

                while (!streamCompleto) {
                    const { done, value } = await leitor.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const linhas = buffer.split(/\r?\n/);
                    buffer = linhas.pop() || "";

                    for (const linha of linhas) {
                        const dadoLimpo = linha.replace(/^data:\s?/, "").trim();
                        if (!dadoLimpo) continue;

                        if (dadoLimpo === "FIM" || dadoLimpo === "[FIM]") {
                            streamCompleto = true;
                            break;
                        }

                        let obj = null;

                        try {
                            obj = JSON.parse(dadoLimpo);
                        } catch (_) {
                            obj = { texto: dadoLimpo };
                        }

                        const laudoSSE = obj?.laudo_id ?? obj?.laudoId ?? obj?.laudoid ?? null;
                        if (laudoSSE) {
                            notificarLaudoCriadoSeMudou(Number(laudoSSE));
                        }
                        if (obj?.laudo_card?.id) {
                            emitirEvento("tariel:laudo-card-sincronizado", {
                                card: obj.laudo_card,
                                selecionar: true,
                            });
                        }

                        if (obj?.tipo && String(obj.tipo).startsWith("humano")) {
                            consumirObjetoHumano(obj, tmpId, invisivel);
                            continue;
                        }

                        if (Array.isArray(obj?.anexos) && obj.anexos.length) {
                            anexosPendentes = anexosRespostaValidos(obj.anexos);

                            if (!invisivel && elementoIA && anexosPendentes.length) {
                                renderizarAnexosMensagem(elementoIA, anexosPendentes, null, {
                                    destacarPdfPrincipal:
                                        obj?.tipo === "relatorio_chat_livre" || respostaPossuiPdf(anexosPendentes),
                                });
                            }
                        }

                        if (Array.isArray(obj?.citacoes) && obj.citacoes.length) {
                            citacoesPendentes = obj.citacoes;

                            if (!invisivel && elementoIA) {
                                renderizarCitacoes(elementoIA, obj.citacoes);
                            }

                            continue;
                        }

                        if (obj?.confianca_ia && typeof obj.confianca_ia === "object") {
                            confiancaPendente = obj.confianca_ia;
                            if (!invisivel && elementoIA) {
                                renderizarConfiancaIA(elementoIA, obj.confianca_ia);
                            }
                            continue;
                        }

                        if (typeof obj?.texto === "string") {
                            textoAcumulado += obj.texto;

                            if (!invisivel && elementoTexto) {
                                elementoTexto.innerHTML = renderizarMarkdown(textoAcumulado);

                                if (cursor) {
                                    elementoTexto.appendChild(cursor);
                                }

                                rolarParaBaixo();
                            }
                        }
                    }
                }

                if (cursor) cursor.remove();

                if (!invisivel) {
                    setUltimoDiagnosticoBruto(textoAcumulado);

                    if (textoAcumulado) {
                        adicionarAoHistorico("assistente", textoAcumulado);
                    }

                    if (elementoIA && textoAcumulado) {
                        if (citacoesPendentes.length) {
                            renderizarCitacoes(elementoIA, citacoesPendentes);
                        }
                        if (confiancaPendente) {
                            renderizarConfiancaIA(elementoIA, confiancaPendente);
                        }
                        if (anexosPendentes.length) {
                            renderizarAnexosMensagem(elementoIA, anexosPendentes, null, {
                                destacarPdfPrincipal: respostaPossuiPdf(anexosPendentes),
                            });
                        }

                        mostrarAcoesPosResposta(elementoIA, textoAcumulado);
                    } else if (elementoIA && anexosPendentes.length) {
                        renderizarAnexosMensagem(elementoIA, anexosPendentes, null, {
                            destacarPdfPrincipal: respostaPossuiPdf(anexosPendentes),
                        });
                    }
                }

                if (tmpId) {
                    atualizarTiquesStatus(tmpId, "lido");
                }

                try {
                    await sincronizarEstadoRelatorio();
                } catch (_) {}

                emitirStatusChat(statusFinalChat, textoStatusFinal);

                return {
                    ok: true,
                    texto: textoAcumulado,
                    laudoId: getLaudoAtualId?.() || null,
                    anexos: anexosPendentes,
                    citacoes: citacoesPendentes,
                    confianca: confiancaPendente,
                };
            } catch (erro) {
                limparTimeoutSeguro(timeout);
                ocultarDigitando();
                cursor?.remove();

                const motivoAbort = String(
                    controller?.__tarielAbortReason
                    || controller?.signal?.reason
                    || ""
                ).trim().toLowerCase();

                if ((erro?.name === "AbortError" || controller?.signal?.aborted) && motivoAbort === "user") {
                    statusFinalChat = "interrompido";
                    textoStatusFinal = "Resposta interrompida pelo inspetor.";
                    emitirStatusChat(statusFinalChat, textoStatusFinal);

                    if (!invisivel && elementoIA && !textoAcumulado.trim()) {
                        elementoIA.remove();
                    }

                    return {
                        ok: false,
                        aborted: true,
                        texto: textoAcumulado,
                    };
                }

                statusFinalChat = "erro";
                textoStatusFinal = motivoAbort === "timeout"
                    ? "Tempo limite atingido na resposta da IA."
                    : "Falha ao gerar a resposta da IA.";
                emitirStatusChat(statusFinalChat, textoStatusFinal);

                const { titulo, mensagem } = classificarErroChat(erro);

                if (!invisivel) {
                    if (elementoTexto) {
                        elementoTexto.innerHTML = renderizarMarkdown(
                            `**${titulo}**\n\n${mensagem}`
                        );
                    } else {
                        criarBolhaErro(mensagem, titulo);
                    }
                } else {
                    const mensagemErro = erro?.gateQualidade
                        ? String(erro?.message || "Gate de qualidade reprovado.")
                        : "Erro ao processar o comando do sistema.";
                    mostrarToast(mensagemErro, "erro");
                }

                log("error", "Erro no stream SSE:", erro);
                return null;
            } finally {
                limparTimeoutSeguro(timeout);
                ocultarDigitando();
                setControllerStream(null);
                setIaRespondendo(false);
                atualizarEstadoBotao();
                rolarParaBaixo();
            }
        }

        // =========================================================
        // COMANDO DE SISTEMA
        // =========================================================
        async function processarEventoComandoSistema(event) {
            const { comando, tipo } = event?.detail || {};
            const comandoNormalizado = String(comando || "").trim().toUpperCase();

            if (
                comandoNormalizado !== "FINALIZARLAUDOAGORA" &&
                comandoNormalizado !== "FINALIZAR_LAUDO_AGORA"
            ) {
                return;
            }

            if (estadoInterno.comandoSistemaEmExecucao) return;

            estadoInterno.comandoSistemaEmExecucao = true;

            try {
                await finalizarViaComandoSistema(tipo || "padrao");
            } finally {
                estadoInterno.comandoSistemaEmExecucao = false;
            }
        }

        // =========================================================
        // PROCESSAMENTO DE ENVIO
        // =========================================================
        async function processarEnvio() {
            const texto = String(campoMensagem?.value || "").trim();
            const imagemBase64Pendente = getImagemBase64Pendente?.();
            const textoDocumentoPendente = getTextoDocumentoPendente?.();
            const nomeDocumentoPendente = getNomeDocumentoPendente?.();

            const temTexto = !!texto;
            const temImagemPronta = !!imagemBase64Pendente;
            const temDocumentoPronto = !!textoDocumentoPendente;

            if (!temTexto && !temImagemPronta && !temDocumentoPronto) return null;
            if (getIaRespondendo?.()) return null;

            if (texto.length > 8000) {
                mostrarToast("Mensagem muito longa. Máximo 8000 caracteres.", "aviso");
                return null;
            }

            const statusRelatorio = await consultarStatusRelatorioAtual();
            const laudoSelecionado = Number(getLaudoAtualId?.() || 0) || null;

            if (
                laudoSelecionado &&
                (statusRelatorio.estado === "aguardando" ||
                    statusRelatorio.estado === "ajustes" ||
                    statusRelatorio.estado === "aprovado")
            ) {
                const mensagemBloqueio = statusRelatorio.estado === "ajustes"
                    ? "Este laudo precisa ser reaberto antes de continuar."
                    : statusRelatorio.estado === "aprovado"
                        ? "Este laudo já foi aprovado e está somente leitura."
                        : "Este laudo está aguardando avaliação e está somente leitura.";
                mostrarToast(mensagemBloqueio, "aviso", 4200);
                return null;
            }

            const setor = setorSelect?.value || "geral";
            ocultarBoasVindas();

            const tmpId = `tmp-${Date.now()}`;
            const imagemParaEnviar = imagemBase64Pendente;
            const textoDocParaEnviar = textoDocumentoPendente;
            const nomeDocParaEnviar = nomeDocumentoPendente;

            if (typeof window.adicionarMensagemInspetor === "function") {
                window.adicionarMensagemInspetor(
                    texto,
                    imagemParaEnviar,
                    nomeDocParaEnviar,
                    tmpId
                );
            }

            const textoHistorico =
                texto ||
                (nomeDocParaEnviar
                    ? `[Documento: ${nomeDocParaEnviar}]`
                    : "[Imagem enviada]");

            if (textoHistorico) {
                adicionarAoHistorico("usuario", textoHistorico);
            }

            if (campoMensagem) {
                campoMensagem.value = "";
                campoMensagem.style.height = "auto";
            }

            atualizarContadorChars();
            limparPreview();

            return enviarParaIA(
                texto,
                imagemParaEnviar,
                setor,
                textoDocParaEnviar,
                nomeDocParaEnviar,
                tmpId,
                false
            );
        }

        // =========================================================
        // EVENTOS DOM DO COMPOSER
        // =========================================================
        function onCampoMensagemInput() {
            this.style.height = "auto";
            this.style.height = `${Math.min(this.scrollHeight, 200)}px`;

            atualizarEstadoBotao();
            atualizarContadorChars();
        }

        function onCampoMensagemKeydown(event) {
            if (event.key === "Enter" && !event.shiftKey && !getIaRespondendo?.()) {
                event.preventDefault();
                processarEnvio();
            }
        }

        function onBtnEnviarClick() {
            if (!getIaRespondendo?.()) {
                processarEnvio();
            }
        }

        // =========================================================
        // API PÚBLICA
        // =========================================================
        const apiPublica = {
            prepararArquivoParaEnvio,
            limparPreview,
            sincronizarEstadoRelatorio,
            iniciarRelatorio,
            finalizarRelatorio,
            finalizarRelatorioDireto,
            cancelarRelatorio,
            enviarFeedback,
            gerarPDF,
            enviarParaIA,
            processarEnvio,

            obterLaudoAtualId() {
                const id = getLaudoAtualId?.();
                return id == null ? null : Number(id);
            },

            obterEstadoRelatorio() {
                return estadoRelatorioLegacy();
            },

            obterEstadoRelatorioNormalizado() {
                return normalizarEstadoRelatorio(getEstadoRelatorio?.());
            },

            obterSnapshotStatusRelatorioAtual() {
                return clonarPayloadStatusRelatorio(
                    construirSnapshotLocalStatusRelatorio()
                );
            },

            destruir() {
                try {
                    removerListenerComandoSistema?.();
                    removerListenerComandoSistema = null;

                    campoMensagem?.removeEventListener("input", onCampoMensagemInput);
                    campoMensagem?.removeEventListener("keydown", onCampoMensagemKeydown);
                    btnEnviar?.removeEventListener("click", onBtnEnviarClick);

                    abortarStreamAtivo();
                } catch (_) {}
            },
        };

        // =========================================================
        // EXPOSIÇÃO GLOBAL / COMPATIBILIDADE
        // =========================================================
        window.TarielAPI = apiPublica;
        window.prepararArquivoParaEnvio = apiPublica.prepararArquivoParaEnvio;
        window.limparPreview = apiPublica.limparPreview;
        window.iniciarRelatorio = apiPublica.iniciarRelatorio;
        window.finalizarRelatorio = apiPublica.finalizarRelatorio;
        window.cancelarRelatorio = apiPublica.cancelarRelatorio;
        window.processarEnvio = apiPublica.processarEnvio;

        // =========================================================
        // BIND INICIAL
        // =========================================================
        removerListenerComandoSistema?.();
        if (typeof window.TarielInspectorEvents?.on === "function") {
            removerListenerComandoSistema = window.TarielInspectorEvents.on(
                "tariel:disparar-comando-sistema",
                processarEventoComandoSistema
            );
        } else {
            EVENTOS.CMD_SISTEMA.forEach((nome) => {
                document.removeEventListener(nome, processarEventoComandoSistema);
                document.addEventListener(nome, processarEventoComandoSistema);
            });
            removerListenerComandoSistema = () => {
                EVENTOS.CMD_SISTEMA.forEach((nome) => {
                    document.removeEventListener(nome, processarEventoComandoSistema);
                });
            };
        }

        campoMensagem?.removeEventListener("input", onCampoMensagemInput);
        campoMensagem?.removeEventListener("keydown", onCampoMensagemKeydown);
        btnEnviar?.removeEventListener("click", onBtnEnviarClick);

        campoMensagem?.addEventListener("input", onCampoMensagemInput);
        campoMensagem?.addEventListener("keydown", onCampoMensagemKeydown);
        btnEnviar?.addEventListener("click", onBtnEnviarClick);

        if (!window.__TARIEL_CHAT_NETWORK_BEFOREUNLOAD_WIRED__) {
            window.__TARIEL_CHAT_NETWORK_BEFOREUNLOAD_WIRED__ = true;

            window.addEventListener(
                "beforeunload",
                () => {
                    try {
                        apiPublica.destruir();
                    } catch (_) {}
                },
                { once: true }
            );
        }

        atualizarEstadoBotao();
        atualizarContadorChars();

        return apiPublica;
    };
})();
