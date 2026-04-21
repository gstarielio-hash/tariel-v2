// ==========================================
// TARIEL.IA — REVISOR_PAINEL_CORE.JS
// Papel: núcleo compartilhado do painel do revisor.
// Responsável por:
// - namespace global do painel
// - referências de DOM e estado compartilhado
// - helpers base, anexos, badges e modais
// - utilitários usados pelos módulos da mesa e histórico
// ==========================================

(function () {
    "use strict";

    if (window.__TARIEL_REVISOR_PAINEL_CORE_WIRED__) return;
    window.__TARIEL_REVISOR_PAINEL_CORE_WIRED__ = true;

    const NS = window.TarielRevisorPainel || {};
    window.TarielRevisorPainel = NS;
    const perf = window.TarielPerf || null;

    const medirSync = (name, runner, detail = {}, category = "function") => {
        if (!perf?.measureSync) return runner();
        return perf.measureSync(name, runner, { category, detail });
    };

    const medirAsync = async (name, runner, detail = {}, category = "function") => {
        if (!perf?.measureAsync) return runner();
        return perf.measureAsync(name, runner, { category, detail });
    };

    const snapshotDOM = (label) => {
        if (!perf?.snapshotDOM) return;
        perf.snapshotDOM(label, {
            shell: ".mesa-shell",
            listaLaudos: "#lista-laudos",
            listaWhispers: "#lista-whispers",
            timeline: "#view-timeline",
            resumoDocumento: "#view-structured-document",
            painelMesa: "#mesa-operacao-painel",
            painelAprendizados: "#aprendizados-visuais-painel",
            modalRelatorio: "#modal-relatorio",
            modalPacote: "#modal-pacote",
        });
    };

    perf?.noteModule?.("revisor/revisor_painel_core.js", { readyState: document.readyState });
    const tokenCsrf = document.getElementById("global-csrf")?.value || "";
    const els = {
        body: document.body,
        listaLaudos: document.getElementById("lista-laudos"),
        listaWhispers: document.getElementById("lista-whispers"),
        containerWhispers: document.getElementById("container-whispers"),
        estadoVazio: document.getElementById("estado-vazio"),
        viewContent: document.getElementById("view-content"),
        viewHash: document.getElementById("view-hash"),
        viewMeta: document.getElementById("view-meta"),
        viewCaseSummary: document.getElementById("view-case-summary"),
        viewStructuredDocument: document.getElementById("view-structured-document"),
        viewAcoes: document.getElementById("view-acoes"),
        btnToggleContextoMesa: document.getElementById("btn-toggle-contexto-mesa"),
        btnFecharContextoMesa: document.getElementById("btn-fechar-contexto-mesa"),
        mesaContextPane: document.getElementById("mesa-context-pane"),
        mesaContextPlaceholder: document.getElementById("mesa-context-placeholder"),
        mesaOperacaoPainel: document.getElementById("mesa-operacao-painel"),
        mesaOperacaoConteudo: document.getElementById("mesa-operacao-conteudo"),
        aprendizadosVisuaisPainel: document.getElementById("aprendizados-visuais-painel"),
        aprendizadosVisuaisConteudo: document.getElementById("aprendizados-visuais-conteudo"),
        timeline: document.getElementById("view-timeline"),
        boxResposta: document.getElementById("box-resposta"),
        refAtivaResposta: document.getElementById("ref-ativa-resposta"),
        refAtivaTitulo: document.getElementById("ref-ativa-titulo"),
        refAtivaTexto: document.getElementById("ref-ativa-texto"),
        btnLimparRefAtiva: document.getElementById("btn-limpar-ref-ativa"),
        previewRespostaAnexo: document.getElementById("preview-resposta-anexo"),
        btnAnexoResposta: document.getElementById("btn-anexo-resposta"),
        inputAnexoResposta: document.getElementById("input-anexo-resposta"),
        inputResposta: document.getElementById("input-resposta"),
        btnEnviarMsg: document.getElementById("btn-enviar-msg"),
        modalRelatorio: document.getElementById("modal-relatorio"),
        btnFecharRelatorio: document.getElementById("btn-fechar-relatorio"),
        modalConteudo: document.getElementById("modal-conteudo"),
        modalPacote: document.getElementById("modal-pacote"),
        btnFecharPacote: document.getElementById("btn-fechar-pacote"),
        modalPacoteConteudo: document.getElementById("modal-pacote-conteudo"),
        dialogMotivo: document.getElementById("dialog-motivo"),
        inputMotivo: document.getElementById("input-motivo"),
        btnCancelarMotivo: document.getElementById("btn-cancelar-motivo"),
        btnConfirmarMotivo: document.getElementById("btn-confirmar-motivo"),
        statusFlutuante: document.getElementById("status-flutuante")
    };
    const TENANT_CAPABILITY_REASON_MAP = {
        reviewer_decision:
            "A revisão da Mesa Avaliadora está desabilitada para esta empresa pelo Admin-CEO.",
        reviewer_issue:
            "A emissão oficial está desabilitada para esta empresa pelo Admin-CEO."
    };

    const state = {
        laudoAtivoId: null,
        laudoContextoVersao: 0,
        laudoLoadController: null,
        laudoLoadPromise: null,
        laudoLoadLaudoId: null,
        reviewerCaseViewAtivo: null,
        reviewerCaseViewLaudoId: null,
        reviewerCaseViewPreferred: false,
        jsonEstruturadoAtivo: null,
        pacoteMesaAtivo: null,
        pacoteMesaLaudoId: null,
        pacoteMesaAbortController: null,
        pacoteMesaPromise: null,
        pacoteMesaEmVooLaudoId: null,
        socketWhisper: null,
        wsReconnectTimer: null,
        wsFechamentoManual: false,
        lastFocusedElement: null,
        pendingSend: false,
        referenciaMensagemAtiva: null,
        respostaAnexoPendente: null,
        historicoMensagens: [],
        historicoCursorProximo: null,
        historicoTemMais: false,
        carregandoHistoricoAntigo: false,
        historicoAbortController: null,
        aprendizadosVisuais: [],
        contextoMesaAberto: false,
        tenantAccessPolicy: null
    };

    const LIMITE_PAGINA_HISTORICO = 60;
    const MAX_BYTES_ANEXO_MESA = 12 * 1024 * 1024;
    const MIME_ANEXOS_MESA_PERMITIDOS = new Set([
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]);

    const focusableSelector = [
        'a[href]',
        'button:not([disabled])',
        'textarea:not([disabled])',
        'input:not([disabled])',
        'select:not([disabled])',
        '[tabindex]:not([tabindex="-1"])'
    ].join(",");

    const escapeHtml = (unsafe) =>
        (unsafe || "")
            .toString()
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");

    const nl2br = (text) => escapeHtml(text).replace(/\n/g, "<br>");

    const formatarTamanhoBytes = (totalBytes) => {
        const valor = Number(totalBytes || 0);
        if (!Number.isFinite(valor) || valor <= 0) return "0 KB";
        if (valor >= 1024 * 1024) {
            return `${(valor / (1024 * 1024)).toFixed(1)} MB`;
        }
        return `${Math.max(1, Math.round(valor / 1024))} KB`;
    };

    const normalizarAnexoMensagem = (payload = {}) => {
        const id = Number(payload?.id || 0) || null;
        const nome = String(payload?.nome || "").trim();
        const url = String(payload?.url || "").trim();
        if (!id || !nome || !url) return null;
        return {
            id,
            nome,
            url,
            mime_type: String(payload?.mime_type || "").trim().toLowerCase(),
            categoria: String(payload?.categoria || "").trim().toLowerCase(),
            tamanho_bytes: Number(payload?.tamanho_bytes || 0) || 0,
            eh_imagem: !!payload?.eh_imagem
        };
    };

    const renderizarAnexosMensagem = (anexos = []) => {
        const itens = Array.isArray(anexos) ? anexos.filter(Boolean) : [];
        if (!itens.length) return "";

        return `
            <div class="anexos-mensagem">
                ${itens.map((anexo) => `
                    <a
                        class="anexo-mensagem-link"
                        href="${escapeHtml(anexo?.url || "#")}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        <span class="material-symbols-rounded" aria-hidden="true">${anexo?.eh_imagem ? "image" : "description"}</span>
                        <span class="anexo-mensagem-info">
                            <strong>${escapeHtml(anexo?.nome || "anexo")}</strong>
                            <small>${escapeHtml(formatarTamanhoBytes(anexo?.tamanho_bytes || 0))}</small>
                        </span>
                    </a>
                `).join("")}
            </div>
        `;
    };

    const limparAnexoResposta = () => {
        state.respostaAnexoPendente = null;
        if (els.inputAnexoResposta) {
            els.inputAnexoResposta.value = "";
        }
        if (els.previewRespostaAnexo) {
            els.previewRespostaAnexo.hidden = true;
            els.previewRespostaAnexo.innerHTML = "";
        }
    };

    const renderizarPreviewAnexoResposta = () => {
        const anexo = state.respostaAnexoPendente;
        if (!els.previewRespostaAnexo) return;

        if (!anexo?.arquivo) {
            els.previewRespostaAnexo.hidden = true;
            els.previewRespostaAnexo.innerHTML = "";
            return;
        }

        els.previewRespostaAnexo.hidden = false;
        els.previewRespostaAnexo.innerHTML = `
            <span class="material-symbols-rounded" aria-hidden="true">${anexo.ehImagem ? "image" : "description"}</span>
            <div class="reply-attachment-info">
                <strong>${escapeHtml(anexo.nome)}</strong>
                <small>${escapeHtml(formatarTamanhoBytes(anexo.tamanho))}</small>
            </div>
            <button type="button" class="btn-remover-anexo-chat" aria-label="Remover anexo">×</button>
        `;
    };

    const selecionarAnexoResposta = (arquivo) => {
        if (!arquivo) return;

        const mime = String(arquivo.type || "").trim().toLowerCase();
        if (!MIME_ANEXOS_MESA_PERMITIDOS.has(mime)) {
            showStatus("Use PNG, JPG, WebP, PDF ou DOCX no canal da mesa.", "error");
            return;
        }

        if (arquivo.size > MAX_BYTES_ANEXO_MESA) {
            showStatus("O anexo da mesa deve ter no máximo 12MB.", "error");
            return;
        }

        state.respostaAnexoPendente = {
            arquivo,
            nome: String(arquivo.name || "anexo"),
            tamanho: Number(arquivo.size || 0) || 0,
            mime_type: mime,
            ehImagem: mime.startsWith("image/")
        };
        renderizarPreviewAnexoResposta();
    };

    const sincronizarAnexoRespostaSelecionado = (arquivo = null) => {
        const alvo = arquivo || els.inputAnexoResposta?.files?.[0] || null;
        if (!alvo) {
            limparAnexoResposta();
            return null;
        }

        selecionarAnexoResposta(alvo);
        return state.respostaAnexoPendente;
    };

    const obterArquivoAnexoRespostaSelecionado = () =>
        state.respostaAnexoPendente?.arquivo
        || els.inputAnexoResposta?.files?.[0]
        || null;

    const showStatus = (texto, icone = "info") => {
        if (!els.statusFlutuante) return;
        els.statusFlutuante.innerHTML =
            `<span class="material-symbols-rounded" aria-hidden="true">${icone}</span><span>${escapeHtml(texto)}</span>`;
        els.statusFlutuante.classList.add("mostrar");
        clearTimeout(showStatus._timer);
        showStatus._timer = setTimeout(() => {
            els.statusFlutuante.classList.remove("mostrar");
        }, 3200);
    };

    const resumoMensagem = (texto) => {
        const base = String(texto || "").replace(/\s+/g, " ").trim();
        if (!base) return "Mensagem sem conteúdo";
        return base.length > 140 ? `${base.slice(0, 140)}...` : base;
    };

    const formatarDataHora = (valor) => {
        if (!valor) return "-";
        try {
            const data = new Date(valor);
            if (Number.isNaN(data.getTime())) return "-";
            return data.toLocaleString("pt-BR", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            });
        } catch (_) {
            return "-";
        }
    };

    const ehAbortError = (erro) =>
        erro?.name === "AbortError"
        || erro?.code === DOMException.ABORT_ERR;

    const obterContextoLaudoAtivo = () => ({
        laudoId: Number(state.laudoAtivoId || 0) || null,
        versao: Number(state.laudoContextoVersao || 0) || 0
    });

    const contextoLaudoAindaValido = (contexto) =>
        Number(contexto?.laudoId || 0) > 0
        && Number(state.laudoAtivoId || 0) === Number(contexto.laudoId || 0)
        && Number(state.laudoContextoVersao || 0) === Number(contexto?.versao || 0);

    const cancelarRequisicaoHistorico = () => {
        if (state.historicoAbortController) {
            state.historicoAbortController.abort();
            state.historicoAbortController = null;
        }
        state.carregandoHistoricoAntigo = false;
    };

    const cancelarRequisicaoPacoteMesa = () => {
        if (state.pacoteMesaAbortController) {
            state.pacoteMesaAbortController.abort();
            state.pacoteMesaAbortController = null;
        }
        state.pacoteMesaPromise = null;
        state.pacoteMesaEmVooLaudoId = null;
    };

    const registrarTrocaLaudoAtivo = (laudoId) => {
        state.laudoAtivoId = Number(laudoId || 0) || null;
        state.laudoContextoVersao += 1;
        state.reviewerCaseViewAtivo = null;
        state.reviewerCaseViewLaudoId = null;
        state.reviewerCaseViewPreferred = false;
        state.jsonEstruturadoAtivo = null;
        state.pacoteMesaAtivo = null;
        state.pacoteMesaLaudoId = null;
        cancelarRequisicaoHistorico();
        cancelarRequisicaoPacoteMesa();
        return obterContextoLaudoAtivo();
    };

    const downloadJson = (nomeArquivo, payload) => {
        const nomeSeguro = (nomeArquivo || "pacote_mesa_laudo.json")
            .replace(/[^\w.\-]/g, "_")
            .slice(0, 120);
        const conteudo = JSON.stringify(payload || {}, null, 2);
        const blob = new Blob([conteudo], { type: "application/json;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = nomeSeguro;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    };

    const normalizarMapaBooleano = (valor) => {
        if (!valor || typeof valor !== "object") return {};

        return Object.entries(valor).reduce((acc, [chave, enabled]) => {
            const chaveNormalizada = String(chave || "").trim();
            if (!chaveNormalizada) return acc;
            acc[chaveNormalizada] = !!enabled;
            return acc;
        }, {});
    };

    const normalizarListaTextual = (valores = []) => (
        Array.isArray(valores)
            ? valores.map((item) => String(item || "").trim()).filter(Boolean)
            : []
    );

    const normalizarTenantAccessPolicy = (policy) => {
        const payload = policy && typeof policy === "object" ? policy : {};
        return {
            ...payload,
            portal_entitlements: normalizarMapaBooleano(payload.portal_entitlements),
            capability_entitlements: normalizarMapaBooleano(payload.capability_entitlements),
            user_capability_entitlements: normalizarMapaBooleano(payload.user_capability_entitlements),
            allowed_portals: normalizarListaTextual(payload.allowed_portals),
            allowed_portal_labels: normalizarListaTextual(payload.allowed_portal_labels),
        };
    };

    const sincronizarTenantAccessPolicy = (policy) => {
        if (!policy || typeof policy !== "object") {
            return state.tenantAccessPolicy;
        }

        state.tenantAccessPolicy = normalizarTenantAccessPolicy(policy);
        return state.tenantAccessPolicy;
    };

    const obterTenantAccessPolicyAtual = () => (
        state.tenantAccessPolicy && typeof state.tenantAccessPolicy === "object"
            ? state.tenantAccessPolicy
            : normalizarTenantAccessPolicy({})
    );

    const userCapabilityEnabled = (capability, fallback = true) => {
        const chave = String(capability || "").trim();
        if (!chave) return !!fallback;

        const policy = obterTenantAccessPolicyAtual();
        if (Object.prototype.hasOwnProperty.call(policy.user_capability_entitlements, chave)) {
            return !!policy.user_capability_entitlements[chave];
        }
        if (Object.prototype.hasOwnProperty.call(policy.capability_entitlements, chave)) {
            return !!policy.capability_entitlements[chave];
        }
        return !!fallback;
    };

    const tenantCapabilityReason = (capability) => {
        const chave = String(capability || "").trim();
        return TENANT_CAPABILITY_REASON_MAP[chave]
            || "A ação da mesa está desabilitada para esta empresa pelo Admin-CEO.";
    };

    const obterPacoteMesaLaudo = async ({ forcar = false } = {}) => {
        return medirAsync(
            "revisor.obterPacoteMesaLaudo",
            async () => {
                const contexto = obterContextoLaudoAtivo();
                if (!contexto.laudoId) return null;
                if (!forcar && state.pacoteMesaAtivo && state.pacoteMesaLaudoId === contexto.laudoId) {
                    return state.pacoteMesaAtivo;
                }
                if (!forcar && state.pacoteMesaPromise && state.pacoteMesaEmVooLaudoId === contexto.laudoId) {
                    return state.pacoteMesaPromise;
                }

                cancelarRequisicaoPacoteMesa();
                const controller = new AbortController();
                state.pacoteMesaAbortController = controller;
                state.pacoteMesaEmVooLaudoId = contexto.laudoId;
                const promise = (async () => {
                    try {
                        const res = await fetch(`/revisao/api/laudo/${contexto.laudoId}/pacote`, {
                            headers: { "X-Requested-With": "XMLHttpRequest" },
                            signal: controller.signal
                        });
                        if (!res.ok) {
                            throw new Error(`Falha HTTP ${res.status}`);
                        }

                        const pacote = await res.json();
                        if (controller.signal.aborted || !contextoLaudoAindaValido(contexto)) {
                            return null;
                        }

                        sincronizarTenantAccessPolicy(pacote?.tenant_access_policy);
                        state.pacoteMesaAtivo = pacote;
                        state.pacoteMesaLaudoId = contexto.laudoId;
                        snapshotDOM(`revisor:pacote:${contexto.laudoId}`);
                        return pacote;
                    } finally {
                        if (state.pacoteMesaAbortController === controller) {
                            state.pacoteMesaAbortController = null;
                        }
                        if (state.pacoteMesaPromise === promise) {
                            state.pacoteMesaPromise = null;
                            state.pacoteMesaEmVooLaudoId = null;
                        }
                    }
                })();
                state.pacoteMesaPromise = promise;
                return promise;
            },
            { laudoId: Number(state.laudoAtivoId || 0) || 0, forcar }
        );
    };

    const limparReferenciaMensagemAtiva = () => {
        state.referenciaMensagemAtiva = null;
        if (els.refAtivaResposta) {
            els.refAtivaResposta.hidden = true;
        }
        if (els.refAtivaTexto) {
            els.refAtivaTexto.textContent = "";
        }
    };

    const definirReferenciaMensagemAtiva = (msg) => {
        if (!msg || !Number.isFinite(Number(msg.id))) {
            limparReferenciaMensagemAtiva();
            return;
        }

        const referenciaId = Number(msg.id);
        const referenciaTexto = resumoMensagem(msg.texto);
        state.referenciaMensagemAtiva = {
            id: referenciaId,
            texto: referenciaTexto
        };

        if (els.refAtivaTitulo) {
            els.refAtivaTitulo.textContent = `Respondendo #${referenciaId}`;
        }
        if (els.refAtivaTexto) {
            els.refAtivaTexto.textContent = referenciaTexto;
        }
        if (els.refAtivaResposta) {
            els.refAtivaResposta.hidden = false;
        }
        els.inputResposta?.focus();
    };

    const setActiveItem = (id) => {
        document.querySelectorAll(".js-item-laudo.ativo").forEach((el) => el.classList.remove("ativo"));
        document.querySelectorAll(`.js-item-laudo[data-id="${CSS.escape(String(id))}"]`)
            .forEach((el) => el.classList.add("ativo"));
    };

    const atualizarTextoToggleContextoMesa = () => {
        if (!els.btnToggleContextoMesa) return;
        els.btnToggleContextoMesa.setAttribute("aria-expanded", String(!!state.contextoMesaAberto));
        const rotulo = els.btnToggleContextoMesa.querySelector("span:last-child");
        if (rotulo) {
            rotulo.textContent = state.contextoMesaAberto ? "Ocultar contexto" : "Contexto da revisão";
        }
        const icone = els.btnToggleContextoMesa.querySelector(".material-symbols-rounded");
        if (icone) {
            icone.textContent = state.contextoMesaAberto ? "right_panel_close" : "right_panel_open";
        }
    };

    const sincronizarPlaceholderContextoMesa = () => {
        if (!els.mesaContextPlaceholder) return;
        const painelMesaVisivel = !!els.mesaOperacaoPainel && !els.mesaOperacaoPainel.hidden;
        const painelAprendizadosVisivel = !!els.aprendizadosVisuaisPainel && !els.aprendizadosVisuaisPainel.hidden;
        els.mesaContextPlaceholder.hidden = painelMesaVisivel || painelAprendizadosVisivel;
    };

    const atualizarDrawerContextoMesa = ({ aberto = null } = {}) => {
        const proximoEstado = aberto === null ? !state.contextoMesaAberto : !!aberto;
        state.contextoMesaAberto = proximoEstado;
        els.body?.classList.toggle("mesa-contexto-aberto", proximoEstado);
        atualizarTextoToggleContextoMesa();
        if (els.btnFecharContextoMesa) {
            els.btnFecharContextoMesa.hidden = !proximoEstado;
        }
        sincronizarPlaceholderContextoMesa();
    };

    const textoBadgeWhisper = (total) => {
        const valor = Math.max(0, Number(total || 0) || 0);
        if (valor <= 0) return "0 chamados";
        return valor > 99 ? "99+ chamados" : `${valor} chamado${valor === 1 ? "" : "s"}`;
    };

    const textoBadgePendencia = (total) => {
        const valor = Math.max(0, Number(total || 0) || 0);
        if (valor <= 0) return "0 pend.";
        return valor > 99 ? "99+ pend." : `${valor} pend.`;
    };

    const textoBadgeAprendizado = (total) => {
        const valor = Math.max(0, Number(total || 0) || 0);
        if (valor <= 0) return "0 aprend.";
        return valor > 99 ? "99+ aprend." : `${valor} aprend.`;
    };

    const normalizarCollaborationSummary = (payload = {}, fallback = {}) => {
        const bruto = (
            payload?.collaboration?.summary
            || payload?.collaboration_summary
            || payload?.collaborationSummary
            || payload?.summary
            || payload
            || {}
        );
        const openPendencyCount = Math.max(
            0,
            Number(
                bruto?.open_pendency_count
                ?? bruto?.openPendencyCount
                ?? fallback?.openPendencyCount
                ?? fallback?.pendenciasAbertas
                ?? 0
            ) || 0
        );
        const resolvedPendencyCount = Math.max(
            0,
            Number(
                bruto?.resolved_pendency_count
                ?? bruto?.resolvedPendencyCount
                ?? fallback?.resolvedPendencyCount
                ?? 0
            ) || 0
        );
        const recentWhisperCount = Math.max(
            0,
            Number(
                bruto?.recent_whisper_count
                ?? bruto?.recentWhisperCount
                ?? fallback?.recentWhisperCount
                ?? fallback?.whispersNaoLidos
                ?? 0
            ) || 0
        );
        const unreadWhisperCount = Math.max(
            0,
            Number(
                bruto?.unread_whisper_count
                ?? bruto?.unreadWhisperCount
                ?? fallback?.unreadWhisperCount
                ?? fallback?.whispersNaoLidos
                ?? 0
            ) || 0
        );
        const recentReviewCount = Math.max(
            0,
            Number(
                bruto?.recent_review_count
                ?? bruto?.recentReviewCount
                ?? fallback?.recentReviewCount
                ?? 0
            ) || 0
        );
        const requiresReviewerAttention = (
            bruto?.requires_reviewer_attention
            ?? bruto?.requiresReviewerAttention
            ?? (openPendencyCount > 0 || unreadWhisperCount > 0)
        );
        return {
            openPendencyCount,
            resolvedPendencyCount,
            recentWhisperCount,
            unreadWhisperCount,
            recentReviewCount,
            hasOpenPendencies: Boolean(bruto?.has_open_pendencies ?? bruto?.hasOpenPendencies ?? openPendencyCount > 0),
            hasRecentWhispers: Boolean(bruto?.has_recent_whispers ?? bruto?.hasRecentWhispers ?? recentWhisperCount > 0),
            requiresReviewerAttention: Boolean(requiresReviewerAttention)
        };
    };

    const serializarCollaborationSummary = (summary = {}) => ({
        open_pendency_count: Number(summary.openPendencyCount || 0) || 0,
        resolved_pendency_count: Number(summary.resolvedPendencyCount || 0) || 0,
        recent_whisper_count: Number(summary.recentWhisperCount || 0) || 0,
        unread_whisper_count: Number(summary.unreadWhisperCount || 0) || 0,
        recent_review_count: Number(summary.recentReviewCount || 0) || 0,
        has_open_pendencies: Boolean(summary.hasOpenPendencies),
        has_recent_whispers: Boolean(summary.hasRecentWhispers),
        requires_reviewer_attention: Boolean(summary.requiresReviewerAttention)
    });

    const normalizarCollaborationDelta = (payload = {}) => {
        const bruto = payload?.collaboration_delta || payload?.collaborationDelta || payload || {};
        if (!bruto || typeof bruto !== "object") {
            return null;
        }
        return {
            eventKind: String(bruto?.event_kind || bruto?.eventKind || "").trim(),
            unreadWhisperDelta: Math.max(0, Number(bruto?.unread_whisper_delta ?? bruto?.unreadWhisperDelta ?? 0) || 0),
            recentWhisperDelta: Math.max(0, Number(bruto?.recent_whisper_delta ?? bruto?.recentWhisperDelta ?? 0) || 0),
            requiresReviewerAttention: Boolean(
                bruto?.requires_reviewer_attention ?? bruto?.requiresReviewerAttention ?? false
            )
        };
    };

    const classificarOperacaoLaudo = ({
        caseLifecycleStatus = "",
        activeOwnerRole = "",
        slaStatus = "",
        whispersNaoLidos = 0,
        pendenciasAbertas = 0,
        aprendizadosPendentes = 0
    } = {}) => {
        const lifecycleStatus = String(caseLifecycleStatus || "").trim().toLowerCase();
        const ownerRole = String(activeOwnerRole || "").trim().toLowerCase();
        const sla = String(slaStatus || "").trim();
        const whispers = Math.max(0, Number(whispersNaoLidos || 0) || 0);
        const pendencias = Math.max(0, Number(pendenciasAbertas || 0) || 0);
        const aprendizados = Math.max(0, Number(aprendizadosPendentes || 0) || 0);

        if (whispers > 0) {
            return {
                fila: "responder_agora",
                filaLabel: "Responder agora",
                prioridade: "critica",
                prioridadeLabel: "Prioridade crítica",
                proximaAcao: "Próxima: Responder inspetor"
            };
        }
        if (aprendizados > 0) {
            return {
                fila: "validar_aprendizado",
                filaLabel: "Validar aprendizado",
                prioridade: "alta",
                prioridadeLabel: "Prioridade alta",
                proximaAcao: "Próxima: Validar aprendizado"
            };
        }
        if (pendencias > 0) {
            const prioridade = sla === "sla-critico" ? "alta" : "media";
            return {
                fila: "aguardando_inspetor",
                filaLabel: "Aguardando campo",
                prioridade,
                prioridadeLabel: prioridade === "alta" ? "Prioridade alta" : "Prioridade média",
                proximaAcao: "Próxima: Cobrar retorno do campo"
            };
        }
        if (ownerRole === "mesa" || lifecycleStatus === "aguardando_mesa" || lifecycleStatus === "em_revisao_mesa") {
            return {
                fila: "fechamento_mesa",
                filaLabel: "Fechamento",
                prioridade: "media",
                prioridadeLabel: "Prioridade média",
                proximaAcao: "Próxima: Fechar revisão"
            };
        }
        if (ownerRole === "inspetor") {
            const prioridade = sla === "sla-critico" ? "alta" : sla === "sla-atencao" ? "media" : "baixa";
            return {
                fila: "acompanhamento",
                filaLabel: "Acompanhamento",
                prioridade,
                prioridadeLabel: prioridade === "alta" ? "Prioridade alta" : prioridade === "media" ? "Prioridade média" : "Prioridade baixa",
                proximaAcao: "Próxima: Acompanhar campo"
            };
        }
        return {
            fila: "historico",
            filaLabel: "Histórico",
            prioridade: "baixa",
            prioridadeLabel: "Prioridade baixa",
            proximaAcao: "Próxima: Consultar histórico"
        };
    };

    const atualizarIndicadoresListaLaudo = (laudoId, {
        whispersNaoLidos = null,
        pendenciasAbertas = null,
        aprendizadosPendentes = null,
        caseLifecycleStatus = null,
        activeOwnerRole = null,
        statusVisualLabel = null,
        collaborationSummary = null,
        collaborationDelta = null
    } = {}) => {
        const alvo = Number(laudoId || 0);
        if (!Number.isFinite(alvo) || alvo <= 0) return;

        document.querySelectorAll(`.js-item-laudo[data-id="${CSS.escape(String(alvo))}"]`).forEach((itemEl) => {
            const whispersAtuais = Math.max(0, Number(itemEl.dataset.whispersNaoLidos || 0) || 0);
            const pendenciasAtuais = Math.max(0, Number(itemEl.dataset.pendenciasAbertas || 0) || 0);
            let collaborationFromDataset = null;
            if (itemEl.dataset.collaborationSummary) {
                try {
                    collaborationFromDataset = JSON.parse(itemEl.dataset.collaborationSummary);
                } catch (_erro) {
                    collaborationFromDataset = null;
                }
            }
            const collaborationBase = collaborationSummary
                ? normalizarCollaborationSummary(collaborationSummary, {
                    whispersNaoLidos: whispersAtuais,
                    pendenciasAbertas: pendenciasAtuais
                })
                : normalizarCollaborationSummary(collaborationFromDataset || {}, {
                    whispersNaoLidos: whispersAtuais,
                    pendenciasAbertas: pendenciasAtuais
                });
            const delta = normalizarCollaborationDelta(collaborationDelta);
            let proximoWhispers = whispersNaoLidos;
            let proximoPendencias = pendenciasAbertas;

            if (collaborationSummary) {
                proximoWhispers = collaborationBase.unreadWhisperCount;
                proximoPendencias = collaborationBase.openPendencyCount;
            }

            if ((proximoWhispers === null || proximoWhispers === undefined) && delta) {
                proximoWhispers = whispersAtuais + delta.unreadWhisperDelta;
            }

            let totalWhispers = whispersAtuais;
            if (proximoWhispers !== null && proximoWhispers !== undefined) {
                totalWhispers = Math.max(0, Number(proximoWhispers || 0) || 0);
                itemEl.dataset.whispersNaoLidos = String(totalWhispers);
                const badgeWhisper = itemEl.querySelector(".js-indicador-whispers");
                if (badgeWhisper) {
                    badgeWhisper.hidden = totalWhispers <= 0;
                    badgeWhisper.textContent = textoBadgeWhisper(totalWhispers);
                }
            }

            let totalPendencias = pendenciasAtuais;
            if (proximoPendencias !== null && proximoPendencias !== undefined) {
                totalPendencias = Math.max(0, Number(proximoPendencias || 0) || 0);
                itemEl.dataset.pendenciasAbertas = String(totalPendencias);
                const badgePendencia = itemEl.querySelector(".js-indicador-pendencias");
                if (badgePendencia) {
                    badgePendencia.hidden = totalPendencias <= 0;
                    badgePendencia.textContent = textoBadgePendencia(totalPendencias);
                }
            }

            if (aprendizadosPendentes !== null && aprendizadosPendentes !== undefined) {
                const totalAprendizados = Math.max(0, Number(aprendizadosPendentes || 0) || 0);
                itemEl.dataset.aprendizadosPendentes = String(totalAprendizados);
                const badgeAprendizado = itemEl.querySelector(".js-indicador-aprendizados");
                if (badgeAprendizado) {
                    badgeAprendizado.hidden = totalAprendizados <= 0;
                    badgeAprendizado.textContent = textoBadgeAprendizado(totalAprendizados);
                }
            }

            if (caseLifecycleStatus !== null && caseLifecycleStatus !== undefined) {
                itemEl.dataset.caseLifecycleStatus = String(caseLifecycleStatus || "").trim().toLowerCase();
            }

            if (activeOwnerRole !== null && activeOwnerRole !== undefined) {
                itemEl.dataset.activeOwnerRole = String(activeOwnerRole || "").trim().toLowerCase();
            }

            if (statusVisualLabel !== null && statusVisualLabel !== undefined) {
                const statusLabel = String(statusVisualLabel || "").trim();
                itemEl.dataset.statusVisualLabel = statusLabel;
                const statusVisualEl = itemEl.querySelector(".js-status-visual-label");
                if (statusVisualEl) {
                    statusVisualEl.textContent = statusLabel ? `Fluxo: ${statusLabel}` : "Fluxo: Em analise";
                }
            }

            const totalRecentWhispers = delta
                ? Math.max(0, collaborationBase.recentWhisperCount + delta.recentWhisperDelta)
                : collaborationBase.recentWhisperCount;
            const exigeRevisao = collaborationSummary
                ? collaborationBase.requiresReviewerAttention
                : (
                    (proximoWhispers !== null && proximoWhispers !== undefined)
                    || (proximoPendencias !== null && proximoPendencias !== undefined)
                    || Boolean(delta)
                )
                    ? (totalPendencias > 0 || totalWhispers > 0)
                    : collaborationBase.requiresReviewerAttention;
            const collaborationAtualizada = normalizarCollaborationSummary({
                open_pendency_count: totalPendencias,
                resolved_pendency_count: collaborationBase.resolvedPendencyCount,
                recent_whisper_count: totalRecentWhispers,
                unread_whisper_count: totalWhispers,
                recent_review_count: collaborationBase.recentReviewCount,
                has_open_pendencies: totalPendencias > 0,
                has_recent_whispers: totalRecentWhispers > 0,
                requires_reviewer_attention: exigeRevisao
            });
            itemEl.dataset.collaborationSummary = JSON.stringify(
                serializarCollaborationSummary(collaborationAtualizada)
            );

            const operacao = classificarOperacaoLaudo({
                caseLifecycleStatus: itemEl.dataset.caseLifecycleStatus || "",
                activeOwnerRole: itemEl.dataset.activeOwnerRole || "",
                slaStatus: itemEl.dataset.slaStatus || "",
                whispersNaoLidos: itemEl.dataset.whispersNaoLidos || 0,
                pendenciasAbertas: itemEl.dataset.pendenciasAbertas || 0,
                aprendizadosPendentes: itemEl.dataset.aprendizadosPendentes || 0
            });
            itemEl.dataset.filaOperacional = operacao.fila;
            itemEl.dataset.prioridadeOperacional = operacao.prioridade;

            const badgeFila = itemEl.querySelector(".badge.fila-operacional");
            if (badgeFila) {
                badgeFila.className = `badge fila-operacional ${operacao.fila}`;
                badgeFila.textContent = operacao.filaLabel;
            }

            const badgePrioridade = itemEl.querySelector(".badge.prioridade");
            if (badgePrioridade) {
                badgePrioridade.className = `badge prioridade ${operacao.prioridade}`;
                badgePrioridade.textContent = operacao.prioridadeLabel;
            }

            const proximaAcao = itemEl.querySelector(".js-proxima-acao");
            if (proximaAcao) {
                proximaAcao.textContent = operacao.proximaAcao;
            }
        });
    };

    const ocultarContainerWhispersSeVazio = () => {
        const possuiItens = !!els.listaWhispers?.querySelector?.(".js-item-laudo");
        if (els.containerWhispers) {
            els.containerWhispers.hidden = !possuiItens;
        }
    };

    const removerWhispersDaListaPorLaudo = (laudoId) => {
        const alvo = Number(laudoId || 0);
        if (!Number.isFinite(alvo) || alvo <= 0 || !els.listaWhispers) return;

        els.listaWhispers
            .querySelectorAll(`.js-item-laudo[data-id="${CSS.escape(String(alvo))}"]`)
            .forEach((item) => item.remove());
        ocultarContainerWhispersSeVazio();
    };

    const marcarWhispersComoLidosLaudo = async (laudoId, { silencioso = true } = {}) => {
        return medirAsync(
            "revisor.marcarWhispersComoLidosLaudo",
            async () => {
                const alvo = Number(laudoId || 0);
                if (!Number.isFinite(alvo) || alvo <= 0) return false;

                try {
                    const res = await fetch(`/revisao/api/laudo/${alvo}/marcar-whispers-lidos`, {
                        method: "POST",
                        headers: {
                            "X-CSRF-Token": tokenCsrf,
                            "X-Requested-With": "XMLHttpRequest"
                        }
                    });
                    if (!res.ok) {
                        throw new Error(`Falha HTTP ${res.status}`);
                    }

                    removerWhispersDaListaPorLaudo(alvo);
                    atualizarIndicadoresListaLaudo(alvo, { whispersNaoLidos: 0 });
                    return true;
                } catch (erro) {
                    if (!silencioso) {
                        showStatus("Nao foi possivel marcar os chamados como lidos.", "error");
                    }
                    console.error("[Tariel] Falha ao marcar chamados como lidos:", erro);
                    return false;
                }
            },
            { laudoId: Number(laudoId || 0) || 0, silencioso }
        );
    };

    const irParaMensagemTimeline = (mensagemId) => {
        const alvo = els.timeline?.querySelector?.(`[data-msg-id="${CSS.escape(String(mensagemId))}"]`);
        if (!alvo) return;

        alvo.scrollIntoView({ behavior: "smooth", block: "center" });
        alvo.classList.add("destacada");
        setTimeout(() => alvo.classList.remove("destacada"), 1200);
    };

    const setViewLoading = (texto = "Carregando...") => {
        els.estadoVazio.style.display = "none";
        els.viewContent.hidden = false;
        if (els.viewCaseSummary) {
            els.viewCaseSummary.innerHTML = `
                <div class="view-case-summary-placeholder">${escapeHtml(texto)}</div>
            `;
        }
        if (els.viewStructuredDocument) {
            els.viewStructuredDocument.hidden = true;
            els.viewStructuredDocument.innerHTML = "";
        }
        if (els.mesaOperacaoPainel) {
            els.mesaOperacaoPainel.hidden = true;
        }
        if (els.mesaOperacaoConteudo) {
            els.mesaOperacaoConteudo.innerHTML = "";
        }
        if (els.aprendizadosVisuaisPainel) {
            els.aprendizadosVisuaisPainel.hidden = true;
        }
        if (els.aprendizadosVisuaisConteudo) {
            els.aprendizadosVisuaisConteudo.innerHTML = "";
        }
        state.aprendizadosVisuais = [];
        els.timeline.innerHTML = `<div class="timeline-status">${escapeHtml(texto)}</div>`;
        sincronizarPlaceholderContextoMesa();
    };

    const encontrarMensagemPorId = (mensagemId) => {
        const alvo = Number(mensagemId);
        if (!Number.isFinite(alvo) || alvo <= 0) return null;

        const grupos = [
            state.historicoMensagens,
            state.pacoteMesaAtivo?.pendencias_abertas,
            state.pacoteMesaAtivo?.pendencias_resolvidas_recentes,
            state.pacoteMesaAtivo?.whispers_recentes
        ];

        for (const grupo of grupos) {
            if (!Array.isArray(grupo)) continue;
            const encontrado = grupo.find((item) => Number(item?.id) === alvo);
            if (encontrado) return encontrado;
        }

        return null;
    };

const openModal = (overlay, focusEl = null) => {
        if (!overlay) return;
        state.lastFocusedElement = document.activeElement;
        overlay.classList.add("ativo");
        overlay.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        setTimeout(() => (focusEl || overlay.querySelector(focusableSelector))?.focus(), 0);
    };

    const closeModal = (overlay) => {
        if (!overlay) return;
        overlay.classList.remove("ativo");
        overlay.setAttribute("aria-hidden", "true");

        if (![els.modalRelatorio, els.modalPacote, els.dialogMotivo].some((el) => el.classList.contains("ativo"))) {
            document.body.style.overflow = "";
        }

        state.lastFocusedElement?.focus?.();
    };

    const trapFocus = (overlay, event) => {
        if (event.key !== "Tab" || !overlay.classList.contains("ativo")) return;
        const focaveis = [...overlay.querySelectorAll(focusableSelector)];
        if (!focaveis.length) return;

        const primeiro = focaveis[0];
        const ultimo = focaveis[focaveis.length - 1];

        if (event.shiftKey && document.activeElement === primeiro) {
            event.preventDefault();
            ultimo.focus();
        } else if (!event.shiftKey && document.activeElement === ultimo) {
            event.preventDefault();
            primeiro.focus();
        }
    };

Object.assign(NS, {
    tokenCsrf,
    els,
    state,
    LIMITE_PAGINA_HISTORICO,
    MAX_BYTES_ANEXO_MESA,
    MIME_ANEXOS_MESA_PERMITIDOS,
    focusableSelector,
    escapeHtml,
    nl2br,
    formatarTamanhoBytes,
    normalizarAnexoMensagem,
    renderizarAnexosMensagem,
    limparAnexoResposta,
    renderizarPreviewAnexoResposta,
    selecionarAnexoResposta,
    sincronizarAnexoRespostaSelecionado,
    obterArquivoAnexoRespostaSelecionado,
    showStatus,
    resumoMensagem,
    formatarDataHora,
    ehAbortError,
    obterContextoLaudoAtivo,
    contextoLaudoAindaValido,
    cancelarRequisicaoHistorico,
    cancelarRequisicaoPacoteMesa,
    registrarTrocaLaudoAtivo,
    downloadJson,
    obterPacoteMesaLaudo,
    normalizarTenantAccessPolicy,
    sincronizarTenantAccessPolicy,
    obterTenantAccessPolicyAtual,
    userCapabilityEnabled,
    tenantCapabilityReason,
    limparReferenciaMensagemAtiva,
    definirReferenciaMensagemAtiva,
    setActiveItem,
    atualizarDrawerContextoMesa,
    sincronizarPlaceholderContextoMesa,
    textoBadgeWhisper,
    textoBadgePendencia,
    textoBadgeAprendizado,
    normalizarCollaborationSummary,
    normalizarCollaborationDelta,
    classificarOperacaoLaudo,
    atualizarIndicadoresListaLaudo,
    ocultarContainerWhispersSeVazio,
    removerWhispersDaListaPorLaudo,
    marcarWhispersComoLidosLaudo,
    irParaMensagemTimeline,
    setViewLoading,
    encontrarMensagemPorId,
    openModal,
    closeModal,
    trapFocus
    ,
    medirSync,
    medirAsync,
    snapshotDOM
});

atualizarDrawerContextoMesa({ aberto: false });
})();
