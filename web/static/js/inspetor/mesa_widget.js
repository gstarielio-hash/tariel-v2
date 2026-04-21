(function () {
    "use strict";

    const modules = window.TarielInspetorModules = window.TarielInspetorModules || {};

    modules.registerMesaWidget = function registerMesaWidget(ctx) {
        const estado = ctx.state;
        const el = ctx.elements;
        const {
            mostrarToast,
            escaparHtml,
            formatarTamanhoBytes,
            normalizarAnexoMesa,
            renderizarLinksAnexosMesa,
            resumirTexto,
            normalizarConexaoMesaWidget,
            pluralizarMesa,
            CONFIG_CONEXAO_MESA_WIDGET,
            CONFIG_STATUS_MESA,
            obterLaudoAtivo,
            obterLaudoAtivoIdSeguro,
            obterTokenCsrf,
            emitirSincronizacaoLaudo,
            avisarMesaExigeInspecao,
            extrairMensagemErroHTTP,
            ehAbortError,
            normalizarStatusMesa,
            MAX_BYTES_ANEXO_MESA,
            MIME_ANEXOS_MESA_PERMITIDOS,
            limparTimerFecharMesaWidget,
            cancelarCarregamentoMensagensMesaWidget,
        } = ctx.shared;
        const atualizarContextoWorkspaceAtivo = (...args) => ctx.actions.atualizarContextoWorkspaceAtivo?.(...args);
        const atualizarStatusChatWorkspace = (...args) => ctx.actions.atualizarStatusChatWorkspace?.(...args);
        const atualizarThreadWorkspace = (...args) => ctx.actions.atualizarThreadWorkspace?.(...args);
        const filtrarTimelineWorkspace = (...args) => ctx.actions.filtrarTimelineWorkspace?.(...args);
        const atualizarStatusMesa = (...args) => ctx.actions.atualizarStatusMesa?.(...args);
        const PERF = window.TarielPerf || window.TarielCore?.TarielPerf || null;
        const MESA_WIDGET_GOVERNED_REASON =
            "A conversa com a Mesa Avaliadora está desabilitada para esta empresa pelo Admin-CEO.";

        PERF?.noteModule?.("inspetor/mesa_widget.js", {
            readyState: document.readyState,
        });
        const MESA_WIDGET_CACHE_MS = 1200;
        const mensagensMesaEmVoo = new Map();
        const cacheMensagensMesa = new Map();
        let chaveMensagensMesaAtiva = "";

    function contarChurnMesa(nome, detail = {}) {
        PERF?.count?.(nome, 1, {
            category: "request_churn",
            detail,
        });
    }

    function construirChaveMensagensMesa({ laudoId, cursor = null, append = false }) {
        return [
            Number(laudoId || 0) || 0,
            Number(cursor || 0) || 0,
            append ? "append" : "replace",
        ].join(":");
    }

    function clonarPayloadMensagensMesa(payload = {}) {
        return {
            ...payload,
            itens: Array.isArray(payload?.itens)
                ? payload.itens.map((item) => (item && typeof item === "object" ? { ...item } : item))
                : [],
        };
    }

    function obterCacheMensagensMesa(chave) {
        const entry = cacheMensagensMesa.get(chave);
        if (!entry) return null;

        if ((Date.now() - Number(entry.at || 0)) > MESA_WIDGET_CACHE_MS) {
            cacheMensagensMesa.delete(chave);
            return null;
        }

        return clonarPayloadMensagensMesa(entry.payload);
    }

    function registrarCacheMensagensMesa(chave, payload) {
        cacheMensagensMesa.set(chave, {
            at: Date.now(),
            payload: clonarPayloadMensagensMesa(payload),
        });
    }

    function invalidarCacheMensagensMesa(laudoId = null) {
        const alvo = Number(laudoId || 0) || null;
        if (!alvo) {
            cacheMensagensMesa.clear();
            return;
        }

        for (const chave of cacheMensagensMesa.keys()) {
            if (String(chave).startsWith(`${alvo}:`)) {
                cacheMensagensMesa.delete(chave);
            }
        }
    }

    function limparAnexoMesaWidget() {
        estado.mesaWidgetAnexoPendente = null;
        if (el.mesaWidgetInputAnexo) {
            el.mesaWidgetInputAnexo.value = "";
        }
        if (el.mesaWidgetPreviewAnexo) {
            el.mesaWidgetPreviewAnexo.hidden = true;
            el.mesaWidgetPreviewAnexo.innerHTML = "";
        }
    }

    function renderizarPreviewAnexoMesaWidget() {
        if (!el.mesaWidgetPreviewAnexo) return;

        const anexo = estado.mesaWidgetAnexoPendente;
        if (!anexo?.arquivo) {
            el.mesaWidgetPreviewAnexo.hidden = true;
            el.mesaWidgetPreviewAnexo.innerHTML = "";
            return;
        }

        el.mesaWidgetPreviewAnexo.hidden = false;
        el.mesaWidgetPreviewAnexo.innerHTML = `
            <div class="mesa-widget-preview-item">
                <span class="material-symbols-rounded" aria-hidden="true">${anexo.ehImagem ? "image" : "description"}</span>
                <div class="mesa-widget-preview-item-texto">
                    <strong>${escaparHtml(anexo.nome)}</strong>
                    <small>${escaparHtml(formatarTamanhoBytes(anexo.tamanho))}</small>
                </div>
                <button type="button" class="mesa-widget-preview-remover" aria-label="Remover anexo da mesa">×</button>
            </div>
        `;
    }

    function selecionarAnexoMesaWidget(arquivo) {
        if (!arquivo) return;

        const mime = String(arquivo.type || "").trim().toLowerCase();
        if (!MIME_ANEXOS_MESA_PERMITIDOS.has(mime)) {
            mostrarToast("Use PNG, JPG, WebP, PDF ou DOCX no chat da mesa.", "aviso", 2400);
            return;
        }

        if (arquivo.size > MAX_BYTES_ANEXO_MESA) {
            mostrarToast("O anexo da mesa deve ter no máximo 12MB.", "aviso", 2400);
            return;
        }

        estado.mesaWidgetAnexoPendente = {
            arquivo,
            nome: String(arquivo.name || "anexo"),
            tamanho: Number(arquivo.size || 0) || 0,
            mime_type: mime,
            ehImagem: mime.startsWith("image/"),
        };
        renderizarPreviewAnexoMesaWidget();
    }

    function obterUltimaMensagemMesaOperacional() {
        const mensagens = Array.isArray(estado.mesaWidgetMensagens) ? estado.mesaWidgetMensagens : [];
        return mensagens.length ? mensagens[mensagens.length - 1] : null;
    }

    function medirEstadoScrollMesaWidget() {
        const lista = el.mesaWidgetLista;
        if (!lista) {
            return {
                scrollTop: 0,
                scrollHeight: 0,
                clientHeight: 0,
                pertoDoFim: true,
            };
        }

        const delta = lista.scrollHeight - (lista.scrollTop + lista.clientHeight);
        return {
            scrollTop: lista.scrollTop,
            scrollHeight: lista.scrollHeight,
            clientHeight: lista.clientHeight,
            pertoDoFim: delta <= 48,
        };
    }

    function aplicarScrollMesaWidgetAposRender(
        medicaoAnterior = null,
        { append = false, forcarFim = false } = {}
    ) {
        const lista = el.mesaWidgetLista;
        if (!lista) return;

        window.requestAnimationFrame(() => {
            if (append && medicaoAnterior) {
                const deltaAltura = lista.scrollHeight - Number(medicaoAnterior.scrollHeight || 0);
                lista.scrollTop = Math.max(0, Number(medicaoAnterior.scrollTop || 0) + deltaAltura);
                return;
            }

            const deveIrParaFim = forcarFim || !medicaoAnterior || !!medicaoAnterior.pertoDoFim;
            if (deveIrParaFim) {
                lista.scrollTop = lista.scrollHeight;
            }
        });
    }

    function resumirMensagemOperacionalMesa(mensagem) {
        if (!mensagem || typeof mensagem !== "object") return "";
        const texto = String(
            mensagem?.texto ||
            mensagem?.anexos?.[0]?.nome ||
            ""
        ).trim();
        return texto ? resumirTexto(texto, 92) : "";
    }

    function obterResumoOperacionalMesa() {
        if (!(window.TARIEL?.hasUserCapability?.("inspector_send_to_mesa", true) ?? true)) {
            return {
                status: "governado",
                titulo: "Mesa governada pelo Admin-CEO",
                descricao: MESA_WIDGET_GOVERNED_REASON,
                chipStatus: "Canal governado",
                chipPendencias: "",
                chipNaoLidas: "",
            };
        }

        const conexao = normalizarConexaoMesaWidget(estado.mesaWidgetConexao);
        const pendenciasAbertas = Number(estado.qtdPendenciasAbertas || 0) || 0;
        const naoLidas = Number(estado.mesaWidgetNaoLidas || 0) || 0;
        const widgetAberto = !!estado.mesaWidgetAberto;
        const ultimaMensagem = obterUltimaMensagemMesaOperacional();
        const ultimaMensagemEhMesa =
            ultimaMensagem?.message_kind === "mesa_pendency" ||
            ultimaMensagem?.item_kind === "pendency" ||
            ultimaMensagem?.tipo === "humano_eng";
        const ultimaMensagemEhCampo =
            ultimaMensagem?.message_kind === "inspector_whisper" ||
            ultimaMensagem?.message_kind === "inspector_message" ||
            ultimaMensagem?.tipo === "humano_insp";
        const ultimaMensagemResumo = resumirMensagemOperacionalMesa(ultimaMensagem);
        const ultimaMensagemData = String(ultimaMensagem?.data || "").trim();
        const sufixoData = ultimaMensagemData ? ` Última interação: ${ultimaMensagemData}.` : "";

        if (conexao === "offline") {
            return {
                status: "offline",
                titulo: "Mesa indisponível no momento",
                descricao: "O canal da mesa perdeu conexão. Aguarde a reconexão para retomar o fluxo.",
                chipStatus: "Offline",
                chipPendencias: pendenciasAbertas > 0 ? `${pendenciasAbertas} ${pluralizarMesa(pendenciasAbertas, "pendência aberta")}` : "",
                chipNaoLidas: naoLidas > 0 ? `${naoLidas} ${pluralizarMesa(naoLidas, "retorno novo", "retornos novos")}` : "",
            };
        }

        if (pendenciasAbertas > 0) {
            return {
                status: "pendencia_aberta",
                titulo: `${pendenciasAbertas} ${pluralizarMesa(pendenciasAbertas, "pendência aberta")} da mesa`,
                descricao: ultimaMensagemResumo
                    ? `Última solicitação: ${ultimaMensagemResumo}.${sufixoData}`
                    : `Há item(ns) da mesa aguardando retorno do campo.${sufixoData}`,
                chipStatus: "Pendência aberta",
                chipPendencias: `${pendenciasAbertas} ${pluralizarMesa(pendenciasAbertas, "pendência aberta")}`,
                chipNaoLidas: naoLidas > 0 ? `${naoLidas} ${pluralizarMesa(naoLidas, "retorno novo", "retornos novos")}` : "",
            };
        }

        if (naoLidas > 0) {
            return {
                status: "respondeu",
                titulo: `Mesa respondeu com ${naoLidas} ${pluralizarMesa(naoLidas, "retorno novo", "retornos novos")}`,
                descricao: ultimaMensagemResumo
                    ? `Novo retorno no canal: ${ultimaMensagemResumo}.${sufixoData}`
                    : `Há retorno novo da mesa aguardando leitura.${sufixoData}`,
                chipStatus: "Mesa respondeu",
                chipPendencias: "",
                chipNaoLidas: `${naoLidas} ${pluralizarMesa(naoLidas, "retorno novo", "retornos novos")}`,
            };
        }

        if (ultimaMensagemEhMesa) {
            return {
                status: "respondeu",
                titulo: "Último retorno veio da mesa",
                descricao: ultimaMensagemResumo
                    ? `Mensagem mais recente: ${ultimaMensagemResumo}.${sufixoData}`
                    : `A mesa respondeu por último neste laudo.${sufixoData}`,
                chipStatus: "Mesa respondeu",
                chipPendencias: "",
                chipNaoLidas: "",
            };
        }

        if (ultimaMensagemEhCampo) {
            return {
                status: "aguardando",
                titulo: "Aguardando resposta da mesa",
                descricao: ultimaMensagemResumo
                    ? `Último envio do campo: ${ultimaMensagemResumo}.${sufixoData}`
                    : `O último movimento veio do campo; a mesa ainda não respondeu.${sufixoData}`,
                chipStatus: "Aguardando mesa",
                chipPendencias: "",
                chipNaoLidas: "",
            };
        }

        if (widgetAberto) {
            return {
                status: "canal_ativo",
                titulo: "Canal da revisão aberto",
                descricao: "Use este espaço para alinhar dúvidas, anexos e pendências com a mesa.",
                chipStatus: "Canal ativo",
                chipPendencias: "",
                chipNaoLidas: "",
            };
        }

        const reconectando = conexao === "reconectando";
        return {
            status: "pronta",
            titulo: reconectando ? "Mesa reconectando" : "Canal da revisão disponível",
            descricao: reconectando
                ? "A conexão está sendo retomada. Você ainda pode acompanhar o último contexto do canal."
                : "Abra o canal para alinhar dúvidas, pendências e evidências com a mesa.",
            chipStatus: reconectando ? "Reconectando" : "Canal disponível",
            chipPendencias: "",
            chipNaoLidas: "",
        };
    }

    function renderizarResumoOperacionalMesa() {
        const resumo = obterResumoOperacionalMesa();

        atualizarStatusMesa(resumo.status, resumo.descricao);

        if (el.mesaWidgetResumo) {
            el.mesaWidgetResumo.dataset.statusOperacional = resumo.status;
        }
        if (el.mesaWidgetResumoTitulo) {
            el.mesaWidgetResumoTitulo.textContent = resumo.titulo;
        }
        if (el.mesaWidgetResumoTexto) {
            el.mesaWidgetResumoTexto.textContent = resumo.descricao;
        }
        if (el.mesaWidgetChipStatus) {
            el.mesaWidgetChipStatus.textContent = resumo.chipStatus;
            el.mesaWidgetChipStatus.className = "mesa-widget-chip operacional";
        }
        if (el.mesaWidgetChipPendencias) {
            const visivel = !!resumo.chipPendencias;
            el.mesaWidgetChipPendencias.hidden = !visivel;
            el.mesaWidgetChipPendencias.textContent = visivel ? resumo.chipPendencias : "";
            el.mesaWidgetChipPendencias.className = "mesa-widget-chip pendencias";
        }
        if (el.mesaWidgetChipNaoLidas) {
            const visivel = !!resumo.chipNaoLidas;
            el.mesaWidgetChipNaoLidas.hidden = !visivel;
            el.mesaWidgetChipNaoLidas.textContent = visivel ? resumo.chipNaoLidas : "";
            el.mesaWidgetChipNaoLidas.className = "mesa-widget-chip nao-lidas";
        }

        atualizarContextoWorkspaceAtivo();
    }

    function atualizarEstadoVisualBotaoMesaWidget() {
        if (!el.btnMesaWidgetToggle) return;

        const naoLidas = Number(estado.mesaWidgetNaoLidas || 0);
        const pendenciasAbertas = Number(estado.qtdPendenciasAbertas || 0) || 0;
        const aberto = !!estado.mesaWidgetAberto;
        const conexao = normalizarConexaoMesaWidget(estado.mesaWidgetConexao);
        const resumo = obterResumoOperacionalMesa();
        const capabilityBlocked =
            !(window.TARIEL?.hasUserCapability?.("inspector_send_to_mesa", true) ?? true);
        const alerta = naoLidas > 0 || aberto;

        el.btnMesaWidgetToggle.classList.toggle("is-open", aberto);
        el.btnMesaWidgetToggle.classList.toggle("is-alert", alerta);
        el.btnMesaWidgetToggle.classList.toggle("is-reconnecting", conexao === "reconectando");
        el.btnMesaWidgetToggle.classList.toggle("is-offline", conexao === "offline");
        el.btnMesaWidgetToggle.classList.toggle("is-disabled", capabilityBlocked);
        el.btnMesaWidgetToggle.disabled = capabilityBlocked;
        el.btnMesaWidgetToggle.setAttribute("aria-disabled", String(capabilityBlocked));

        const partes = [aberto ? "Fechar canal da mesa avaliadora" : "Abrir canal da mesa avaliadora"];
        if (resumo?.titulo) {
            partes.push(resumo.titulo);
        }
        if (pendenciasAbertas > 0) {
            partes.push(`${pendenciasAbertas} ${pluralizarMesa(pendenciasAbertas, "pendência aberta")}`);
        }
        if (naoLidas > 0) {
            partes.push(`${Math.min(naoLidas, 99)} mensagem(ns) não lida(s)`);
        }
        if (conexao !== "conectado") {
            partes.push(CONFIG_CONEXAO_MESA_WIDGET[conexao] || "Conexão indisponível");
        }
        el.btnMesaWidgetToggle.setAttribute("aria-label", partes.join(". "));
        el.btnMesaWidgetToggle.title = capabilityBlocked ? MESA_WIDGET_GOVERNED_REASON : "";

        const label = el.btnMesaWidgetToggle.querySelector("[data-mesa-toggle-label]");
        if (label) {
            label.textContent = capabilityBlocked
                ? "Canal governado"
                : (aberto ? "Fechar canal" : "Abrir canal");
        }
    }

    function mesaWidgetPermitidoNoContextoAtual() {
        const body = document.body;
        const permitidoDataset = String(body?.dataset?.mesaWidgetVisible || "").trim();
        if (permitidoDataset === "true") return true;
        if (permitidoDataset === "false") return false;

        const baseScreen = String(
            body?.dataset?.inspectorBaseScreen ||
            body?.dataset?.inspectorScreen ||
            ""
        ).trim();
        const overlayOwner = String(
            body?.dataset?.inspectorOverlayOwner ||
            body?.dataset?.overlayOwner ||
            ""
        ).trim();

        return !overlayOwner && (
            baseScreen === "inspection_history" ||
            baseScreen === "inspection_record" ||
            baseScreen === "inspection_conversation" ||
            baseScreen === "inspection_mesa"
        );
    }

    function sincronizarClasseBodyMesaWidget() {
        const permitido = mesaWidgetPermitidoNoContextoAtual();
        document.body.classList.toggle("mesa-widget-aberto", !!estado.mesaWidgetAberto);
        document.body.classList.toggle("mesa-widget-disponivel", permitido);
        document.body.dataset.mesaWidgetScope = permitido ? "workspace-inspection" : "hidden";
        document.body.dataset.mesaWidgetState = estado.mesaWidgetAberto ? "open" : "closed";

        if (el.painelMesaWidget) {
            el.painelMesaWidget.dataset.widgetScope = permitido ? "workspace-inspection" : "hidden";
            el.painelMesaWidget.dataset.widgetState = estado.mesaWidgetAberto ? "open" : "closed";
            const ariaHidden = !permitido || !estado.mesaWidgetAberto || el.painelMesaWidget.hidden;
            el.painelMesaWidget.setAttribute("aria-hidden", String(ariaHidden));
        }

        if (el.btnMesaWidgetToggle) {
            el.btnMesaWidgetToggle.dataset.primarySurface = permitido ? "rail" : "hidden";
        }
    }

    function atualizarConexaoMesaWidget(status = "conectado", detalhe = "") {
        const conexao = normalizarConexaoMesaWidget(status);
        estado.mesaWidgetConexao = conexao;

        if (el.statusConexaoMesaWidget) {
            el.statusConexaoMesaWidget.dataset.conexao = conexao;
            const textoEstado = CONFIG_CONEXAO_MESA_WIDGET[conexao] || CONFIG_CONEXAO_MESA_WIDGET.conectado;
            const detalheLimpo = String(detalhe || "").trim();
            el.statusConexaoMesaWidget.title = detalheLimpo
                ? `${textoEstado} — ${detalheLimpo.slice(0, 120)}`
                : textoEstado;
        }

        if (el.textoConexaoMesaWidget) {
            el.textoConexaoMesaWidget.textContent =
                CONFIG_CONEXAO_MESA_WIDGET[conexao] || CONFIG_CONEXAO_MESA_WIDGET.conectado;
        }

        atualizarEstadoVisualBotaoMesaWidget();
        renderizarResumoOperacionalMesa();
    }

    function atualizarBadgeMesaWidget() {
        const total = Number(estado.mesaWidgetNaoLidas || 0);
        atualizarEstadoVisualBotaoMesaWidget();
        renderizarResumoOperacionalMesa();
    }

    function limparReferenciaMesaWidget() {
        estado.mesaWidgetReferenciaAtiva = null;
        if (el.mesaWidgetRefAtiva) {
            el.mesaWidgetRefAtiva.hidden = true;
        }
        if (el.mesaWidgetRefTexto) {
            el.mesaWidgetRefTexto.textContent = "";
        }
    }

    function definirReferenciaMesaWidget(mensagem) {
        const referenciaId = Number(mensagem?.id || 0) || null;
        if (!referenciaId) {
            limparReferenciaMesaWidget();
            return;
        }

        const preview = resumirTexto(mensagem?.texto || "");
        estado.mesaWidgetReferenciaAtiva = { id: referenciaId, texto: preview };

        if (el.mesaWidgetRefTitulo) {
            el.mesaWidgetRefTitulo.textContent = `Respondendo #${referenciaId}`;
        }
        if (el.mesaWidgetRefTexto) {
            el.mesaWidgetRefTexto.textContent = preview;
        }
        if (el.mesaWidgetRefAtiva) {
            el.mesaWidgetRefAtiva.hidden = false;
        }
        el.mesaWidgetInput?.focus();
    }

    function normalizarMensagemMesa(payload) {
        const tipo = String(payload?.tipo || "").toLowerCase();
        const id = Number(payload?.id || 0) || null;
        if (!id) return null;
        const anexos = Array.isArray(payload?.anexos)
            ? payload.anexos.map(normalizarAnexoMesa).filter(Boolean)
            : [];
        const resolvidaEm = String(payload?.resolvida_em || "").trim();
        const resolvidaPorNome = String(payload?.resolvida_por_nome || "").trim();
        const resolvidaEmLabel = String(payload?.resolvida_em_label || "").trim();
        const itemKind = String(payload?.item_kind || "").trim().toLowerCase() || "message";
        const messageKind = String(payload?.message_kind || "").trim().toLowerCase() || "system_message";
        const pendencyState = String(payload?.pendency_state || "").trim().toLowerCase() || "not_applicable";
        const lida = !!payload?.lida || !!resolvidaEm;

        return {
            id,
            laudo_id: Number(payload?.laudo_id || 0) || null,
            tipo,
            item_kind: itemKind,
            message_kind: messageKind,
            pendency_state: pendencyState,
            texto: String(payload?.texto || "").trim(),
            data: String(payload?.data || "").trim(),
            remetente_id: Number(payload?.remetente_id || 0) || null,
            referencia_mensagem_id: Number(payload?.referencia_mensagem_id || 0) || null,
            client_message_id: String(payload?.client_message_id || "").trim(),
            lida,
            resolvida_em: resolvidaEm,
            resolvida_em_label: resolvidaEmLabel,
            resolvida_por_nome: resolvidaPorNome,
            anexos,
        };
    }

    function substituirOuAcrescentarMensagemMesa(mensagem) {
        const normalizada = normalizarMensagemMesa(mensagem);
        const mensagemId = Number(normalizada?.id || 0) || null;
        if (!mensagemId) {
            return false;
        }

        const historicoAtual = Array.isArray(estado.mesaWidgetMensagens)
            ? estado.mesaWidgetMensagens
            : [];
        const semDuplicata = historicoAtual.filter(
            (item) => Number(item?.id || 0) !== mensagemId
        );
        estado.mesaWidgetMensagens = [...semDuplicata, normalizada];
        return true;
    }

    function obterMensagemMesaPorId(mensagemId) {
        const alvo = Number(mensagemId || 0) || null;
        if (!alvo) return null;
        return (estado.mesaWidgetMensagens || []).find((item) => Number(item?.id) === alvo) || null;
    }

    function descreverItemMesaWidget(item = {}) {
        const entradaMesa =
            item.message_kind === "mesa_pendency" ||
            item.item_kind === "pendency" ||
            item.tipo === "humano_eng";
        const pendenciaAberta = item.pendency_state === "open";
        const pendenciaResolvida = item.pendency_state === "resolved" || (entradaMesa && !!item.lida);
        const ehWhisper = item.item_kind === "whisper";

        if (entradaMesa && pendenciaAberta) {
            return {
                className: "pendencia-aberta",
                origemLabel: "Mesa",
                pillClass: "pendencia-aberta",
                pillLabel: "Pendência aberta",
                responder: true,
                actionLabel: "Responder à pendência",
            };
        }

        if (entradaMesa && pendenciaResolvida) {
            return {
                className: "pendencia-resolvida",
                origemLabel: "Mesa",
                pillClass: "pendencia-resolvida",
                pillLabel: "Pendência resolvida",
                responder: false,
                actionLabel: "",
            };
        }

        if (entradaMesa) {
            return {
                className: "retorno-mesa",
                origemLabel: "Mesa",
                pillClass: "mensagem-contexto",
                pillLabel: "Retorno da mesa",
                responder: true,
                actionLabel: "Responder à mesa",
            };
        }

        if (ehWhisper) {
            return {
                className: "chamado-campo",
                origemLabel: "Campo",
                pillClass: "mensagem-enviada",
                pillLabel: "Solicitação enviada",
                responder: false,
                actionLabel: "",
            };
        }

        return {
            className: "mensagem-campo",
            origemLabel: "Você",
            pillClass: "mensagem-enviada",
            pillLabel: item.anexos?.length ? "Enviado com anexo" : "Mensagem enviada",
            responder: false,
            actionLabel: "",
        };
    }

    function normalizarPayloadSincronizacaoMesa(payload = {}, laudoId = null) {
        const laudoAtivo = obterLaudoAtivo();
        const laudoPayload = Number(payload?.laudo_id ?? payload?.laudoId ?? payload?.laudo_card?.id ?? 0) || null;
        const estadoPayload = String(payload?.estado || "").trim().toLowerCase();

        if (
            laudoId &&
            laudoAtivo &&
            laudoAtivo === laudoId &&
            laudoPayload === laudoId &&
            estadoPayload === "sem_relatorio"
        ) {
            const payloadNormalizado = { ...payload };
            delete payloadNormalizado.estado;
            return payloadNormalizado;
        }

        return payload;
    }

    async function irParaMensagemPrincipal(mensagemId) {
        const alvo = Number(mensagemId || 0) || null;
        if (!alvo) return false;

        atualizarThreadWorkspace("chat");
        estado.chatBuscaTermo = "";
        estado.chatFiltroTimeline = "todos";
        if (el.chatThreadSearch) {
            el.chatThreadSearch.value = "";
        }
        el.chatFilterButtons.forEach((botao) => {
            const ativo = String(botao.dataset.chatFilter || "") === "todos";
            botao.classList.toggle("is-active", ativo);
            botao.setAttribute("aria-pressed", ativo ? "true" : "false");
        });
        filtrarTimelineWorkspace();

        const seletor = `.linha-mensagem[data-mensagem-id="${alvo}"]`;
        let elemento = document.querySelector(seletor);

        if (!elemento) {
            const laudoId = obterLaudoAtivo();
            const historicoPrincipalVazio = !document.querySelector(".linha-mensagem");
            if (historicoPrincipalVazio && laudoId && typeof window.TarielAPI?.carregarLaudo === "function") {
                try {
                    await window.TarielAPI.carregarLaudo(laudoId, { forcar: true, silencioso: true });
                } catch (_) {}
                elemento = document.querySelector(seletor);
            }
        }

        if (!elemento) {
            mostrarToast("Mensagem de referência não está visível no histórico atual.", "aviso", 2300);
            return false;
        }

        elemento.scrollIntoView({ behavior: "smooth", block: "center" });
        elemento.classList.add("destacar-referencia");
        window.setTimeout(() => elemento.classList.remove("destacar-referencia"), 1400);
        return true;
    }

    function renderizarListaMesaWidget({
        append = false,
        preservarScroll = null,
        forcarFim = false,
    } = {}) {
        if (!el.mesaWidgetLista) return;

        const mensagens = Array.isArray(estado.mesaWidgetMensagens)
            ? estado.mesaWidgetMensagens
            : [];

        el.mesaWidgetLista.innerHTML = "";
        if (!mensagens.length) {
            const vazio = document.createElement("p");
            vazio.className = "texto-vazio-pendencias";
            vazio.textContent = "Sem conversa da mesa neste laudo.";
            el.mesaWidgetLista.appendChild(vazio);
            return;
        }

        for (const item of mensagens) {
            const descricaoItem = descreverItemMesaWidget(item);
            const pendenciaResolvida = item.pendency_state === "resolved" || descricaoItem.className === "pendencia-resolvida";
            const card = document.createElement("article");
            card.className = `mesa-widget-item ${descricaoItem.origemLabel === "Mesa" ? "entrada" : "saida"} mesa-widget-item--${descricaoItem.className}`;
            card.dataset.mensagemId = String(item.id);
            card.dataset.itemKind = String(item.item_kind || "message");
            card.dataset.messageKind = String(item.message_kind || "system_message");
            card.dataset.pendencyState = String(item.pendency_state || "not_applicable");

            const referenciaId = Number(item.referencia_mensagem_id || 0) || null;
            const referenciaMsg = referenciaId ? obterMensagemMesaPorId(referenciaId) : null;
            const referenciaPreview = resumirTexto(referenciaMsg?.texto || `Mensagem #${referenciaId || ""}`);
            const referenciaHtml = referenciaId
                ? `
                    <button type="button" class="mesa-widget-ref-link" data-ir-mensagem-id="${referenciaId}">
                        <strong>Referência #${referenciaId}</strong>
                        <span>${escaparHtml(referenciaPreview)}</span>
                    </button>
                `
                : "";

            const textoMensagem = String(item.texto || "").trim();
            const anexosHtml = renderizarLinksAnexosMesa(item.anexos || []);
            const pillOperacao = `
                <span class="mesa-widget-pill-operacao ${descricaoItem.pillClass}">
                    ${descricaoItem.pillLabel}
                </span>
            `;
            const resolucaoInfo = pendenciaResolvida
                ? `
                    <p class="mesa-widget-resolucao">
                        Resolvida por ${escaparHtml(item.resolvida_por_nome || "mesa")} ${item.resolvida_em_label ? `em ${escaparHtml(item.resolvida_em_label)}` : ""}.
                    </p>
                `
                : "";
            card.innerHTML = `
                <div class="meta">
                    <span>${descricaoItem.origemLabel}</span>
                    <span>${escaparHtml(item.data || "")}</span>
                </div>
                <div class="mesa-widget-pills">
                    ${pillOperacao}
                </div>
                ${referenciaHtml}
                ${textoMensagem ? `<p class="texto">${escaparHtml(textoMensagem)}</p>` : ""}
                ${resolucaoInfo}
                ${anexosHtml}
                ${descricaoItem.responder ? `
                    <div class="acoes">
                        <button type="button" data-responder-mensagem-id="${item.id}">${descricaoItem.actionLabel}</button>
                    </div>
                ` : ""}
            `;

            el.mesaWidgetLista.appendChild(card);
        }

        aplicarScrollMesaWidgetAposRender(preservarScroll, {
            append,
            forcarFim,
        });
    }

    async function carregarMensagensMesaWidget({
        laudoId = null,
        append = false,
        silencioso = false,
        forcarRede = false,
    } = {}) {
        const alvoLaudoId = Number(laudoId || obterLaudoAtivo() || 0) || null;
        if (!alvoLaudoId) return;

        const cursorAtual = append ? (Number(estado.mesaWidgetCursor || 0) || null) : null;
        const chave = construirChaveMensagensMesa({
            laudoId: alvoLaudoId,
            cursor: cursorAtual,
            append,
        });

        if (mensagensMesaEmVoo.has(chave)) {
            contarChurnMesa("inspetor.mesa_widget.inflight_reused", {
                laudoId: alvoLaudoId,
                append,
                cursor: cursorAtual,
            });
            return mensagensMesaEmVoo.get(chave);
        }

        if (forcarRede && !append) {
            invalidarCacheMensagensMesa(alvoLaudoId);
        }

        if (silencioso && !append && !forcarRede) {
            const cache = obterCacheMensagensMesa(chave);
            if (cache) {
                contarChurnMesa("inspetor.mesa_widget.cache_hit", {
                    laudoId: alvoLaudoId,
                });
                const payloadCache = cache?.dados || cache || {};
                const itensCache = Array.isArray(payloadCache?.itens) ? payloadCache.itens : [];
                const normalizadosCache = itensCache
                    .map(normalizarMensagemMesa)
                    .filter(Boolean);

                estado.mesaWidgetMensagens = [...normalizadosCache];
                estado.mesaWidgetCursor = Number(payloadCache?.cursor_proximo || 0) || null;
                estado.mesaWidgetTemMais = !!payloadCache?.tem_mais;
                if (el.mesaWidgetCarregarMais) {
                    el.mesaWidgetCarregarMais.hidden = !estado.mesaWidgetTemMais;
                }
                renderizarListaMesaWidget({
                    append: false,
                    preservarScroll: medirEstadoScrollMesaWidget(),
                    forcarFim: false,
                });
                renderizarResumoOperacionalMesa();
                return payloadCache;
            }
        }

        if (estado.mesaWidgetAbortController && chaveMensagensMesaAtiva !== chave) {
            cancelarCarregamentoMensagensMesaWidget();
        }
        const controller = new AbortController();
        chaveMensagensMesaAtiva = chave;
        estado.mesaWidgetAbortController = controller;
        estado.mesaWidgetCarregando = true;
        if (el.mesaWidgetCarregarMais) {
            el.mesaWidgetCarregarMais.disabled = true;
        }

        const requisicao = (async () => {
            try {
                const params = new URLSearchParams();
                params.set("limite", "40");
                if (append && Number(estado.mesaWidgetCursor || 0) > 0) {
                    params.set("cursor", String(estado.mesaWidgetCursor));
                }

                const resposta = await fetch(`/app/api/laudo/${alvoLaudoId}/mesa/mensagens?${params.toString()}`, {
                    credentials: "same-origin",
                    headers: {
                        "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    signal: controller.signal,
                });

                if (!resposta.ok) {
                    throw new Error(`HTTP_${resposta.status}`);
                }

                const dados = await resposta.json();
                const payload = dados?.dados || dados || {};
                const itens = Array.isArray(payload?.itens) ? payload.itens : [];
                const normalizados = itens
                    .map(normalizarMensagemMesa)
                    .filter(Boolean);

                if (controller.signal.aborted || alvoLaudoId !== obterLaudoAtivo()) {
                    return;
                }

                emitirSincronizacaoLaudo(payload, { selecionar: false });
                if (!append) {
                    registrarCacheMensagensMesa(chave, { dados: payload });
                }

                const medicaoScroll = medirEstadoScrollMesaWidget();

                if (append) {
                    estado.mesaWidgetMensagens = [...normalizados, ...estado.mesaWidgetMensagens];
                } else {
                    estado.mesaWidgetMensagens = [...normalizados];
                }

                estado.mesaWidgetCursor = Number(payload?.cursor_proximo || 0) || null;
                estado.mesaWidgetTemMais = !!payload?.tem_mais;

                if (el.mesaWidgetCarregarMais) {
                    el.mesaWidgetCarregarMais.hidden = !estado.mesaWidgetTemMais;
                }

                renderizarListaMesaWidget({
                    append,
                    preservarScroll: medicaoScroll,
                    forcarFim: !append,
                });
                renderizarResumoOperacionalMesa();
                return payload;
            } catch (erro) {
            if (ehAbortError(erro)) {
                return;
            }
            if (!silencioso) {
                mostrarToast("Não foi possível carregar o chat da mesa.", "aviso", 2400);
            }
        } finally {
            if (estado.mesaWidgetAbortController === controller) {
                estado.mesaWidgetAbortController = null;
            }
            if (chaveMensagensMesaAtiva === chave) {
                chaveMensagensMesaAtiva = "";
            }
            estado.mesaWidgetCarregando = !!estado.mesaWidgetAbortController;
            if (el.mesaWidgetCarregarMais) {
                el.mesaWidgetCarregarMais.disabled = estado.mesaWidgetCarregando;
            }
            }
        })();

        mensagensMesaEmVoo.set(chave, requisicao);
        requisicao.finally(() => {
            if (mensagensMesaEmVoo.get(chave) === requisicao) {
                mensagensMesaEmVoo.delete(chave);
            }
        });

        return requisicao;
    }

    async function enviarMensagemMesaWidget() {
        const laudoId = obterLaudoAtivo();
        const texto = String(el.mesaWidgetInput?.value || "").trim();
        const anexoPendente = estado.mesaWidgetAnexoPendente?.arquivo || null;

        if (!(window.TARIEL?.hasUserCapability?.("inspector_send_to_mesa", true) ?? true)) {
            mostrarToast(MESA_WIDGET_GOVERNED_REASON, "aviso", 2800);
            return;
        }

        if (!laudoId) {
            avisarMesaExigeInspecao();
            return;
        }

        if (!texto && !anexoPendente) {
            mostrarToast("Digite uma mensagem ou selecione um anexo para a mesa avaliadora.", "aviso", 2200);
            return;
        }

        const referenciaId = Number(estado.mesaWidgetReferenciaAtiva?.id || 0) || null;

        el.mesaWidgetEnviar?.setAttribute("aria-busy", "true");
        if (el.mesaWidgetEnviar) {
            el.mesaWidgetEnviar.disabled = true;
        }

        try {
            let resposta;
            if (anexoPendente) {
                const form = new FormData();
                form.set("arquivo", anexoPendente);
                if (texto) {
                    form.set("texto", texto);
                }
                if (referenciaId) {
                    form.set("referencia_mensagem_id", String(referenciaId));
                }

                resposta = await fetch(`/app/api/laudo/${laudoId}/mesa/anexo`, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Accept": "application/json",
                        "X-CSRF-Token": obterTokenCsrf(),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: form,
                });
            } else {
                resposta = await fetch(`/app/api/laudo/${laudoId}/mesa/mensagem`, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRF-Token": obterTokenCsrf(),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: JSON.stringify({
                        texto,
                        referencia_mensagem_id: referenciaId || null,
                    }),
                });
            }

            if (!resposta.ok) {
                const detalhe = await extrairMensagemErroHTTP(
                    resposta,
                    `HTTP_${resposta.status}`
                );
                throw new Error(detalhe);
            }

            const dados = await resposta.json().catch(() => ({}));
            const payload = dados?.dados || dados || {};
            const payloadSincronizado = normalizarPayloadSincronizacaoMesa(payload, laudoId);
            emitirSincronizacaoLaudo(payloadSincronizado, { selecionar: false });

            const manterWorkspaceAtivo =
                document.body?.dataset?.inspecaoUi === "workspace" &&
                obterLaudoAtivo() === laudoId;

            if (!manterWorkspaceAtivo) {
                await window.TarielAPI?.sincronizarEstadoRelatorio?.();
            }

            el.mesaWidgetInput.value = "";
            limparReferenciaMesaWidget();
            limparAnexoMesaWidget();

            if (obterLaudoAtivo() === laudoId) {
                await carregarMensagensMesaWidget({ laudoId, silencioso: false, forcarRede: true });
            }
        } catch (erro) {
            const detalhe = String(erro?.message || "").trim();
            mostrarToast(
                detalhe || "Falha ao enviar mensagem para a mesa.",
                "erro",
                2600
            );
        } finally {
            el.mesaWidgetEnviar?.removeAttribute("aria-busy");
            if (el.mesaWidgetEnviar) {
                el.mesaWidgetEnviar.disabled = false;
            }
            el.mesaWidgetInput?.focus();
        }
    }

    async function abrirMesaWidget() {
        const laudoId = obterLaudoAtivo();
        if (!(window.TARIEL?.hasUserCapability?.("inspector_send_to_mesa", true) ?? true)) {
            mostrarToast(MESA_WIDGET_GOVERNED_REASON, "aviso", 2800);
            atualizarEstadoVisualBotaoMesaWidget();
            return;
        }
        if (!laudoId) {
            avisarMesaExigeInspecao();
            return;
        }

        limparTimerFecharMesaWidget();
        estado.mesaWidgetAberto = true;
        estado.mesaWidgetNaoLidas = 0;
        sincronizarClasseBodyMesaWidget();
        atualizarBadgeMesaWidget();
        renderizarResumoOperacionalMesa();

        if (el.painelMesaWidget) {
            el.painelMesaWidget.hidden = false;
            el.painelMesaWidget.classList.remove("fechando");
            requestAnimationFrame(() => {
                el.painelMesaWidget?.classList.add("aberto");
            });
        }
        if (el.btnMesaWidgetToggle) {
            el.btnMesaWidgetToggle.setAttribute("aria-expanded", "true");
        }
        atualizarEstadoVisualBotaoMesaWidget();

        carregarMensagensMesaWidget({ silencioso: true }).catch(() => {});
        el.mesaWidgetInput?.focus();
    }

    function fecharMesaWidget() {
        if (
            el.painelMesaWidget?.dataset?.workspaceEmbedded === "true" &&
            typeof window.TarielInspectorState?.atualizarThreadWorkspace === "function"
        ) {
            window.TarielInspectorState.atualizarThreadWorkspace("historico");
            return;
        }

        estado.mesaWidgetAberto = false;
        sincronizarClasseBodyMesaWidget();
        limparTimerFecharMesaWidget();
        renderizarResumoOperacionalMesa();
        if (el.painelMesaWidget) {
            el.painelMesaWidget.classList.remove("aberto");
            el.painelMesaWidget.classList.add("fechando");
            estado.timerFecharMesaWidget = window.setTimeout(() => {
                if (el.painelMesaWidget) {
                    el.painelMesaWidget.hidden = true;
                    el.painelMesaWidget.classList.remove("fechando");
                }
                estado.timerFecharMesaWidget = null;
            }, 220);
        }
        if (el.btnMesaWidgetToggle) {
            el.btnMesaWidgetToggle.setAttribute("aria-expanded", "false");
        }
        atualizarEstadoVisualBotaoMesaWidget();
    }

    async function toggleMesaWidget() {
        if (estado.mesaWidgetAberto) {
            fecharMesaWidget();
            return;
        }
        await abrirMesaWidget();
    }

    async function atualizarChatAoVivoComMesa(dadosEvento) {
        const laudoEvento = Number(dadosEvento?.laudo_id ?? dadosEvento?.laudoId ?? 0) || null;
        const laudoAtivo = obterLaudoAtivo();
        if (!laudoEvento || !laudoAtivo || laudoEvento !== laudoAtivo) {
            return;
        }

        const mensagemEvento = dadosEvento?.mensagem;
        const medicaoScroll = medirEstadoScrollMesaWidget();
        if (mensagemEvento && substituirOuAcrescentarMensagemMesa(mensagemEvento)) {
            renderizarListaMesaWidget({
                append: false,
                preservarScroll: medicaoScroll,
                forcarFim: false,
            });
            renderizarResumoOperacionalMesa();
        }

        const texto = String(dadosEvento?.texto || "").trim();
        const historicoPrincipalVazio = !document.querySelector(".linha-mensagem");
        if (!texto && historicoPrincipalVazio && typeof window.TarielAPI?.carregarLaudo === "function") {
            try {
                await window.TarielAPI.carregarLaudo(laudoEvento, { forcar: true, silencioso: true });
            } catch (_) {}
        }

        await carregarMensagensMesaWidget({
            laudoId: laudoEvento,
            silencioso: true,
            forcarRede: true,
        });
    }

        if (PERF?.enabled) {
            const carregarMensagensMesaWidgetOriginal = carregarMensagensMesaWidget;
            carregarMensagensMesaWidget = async function carregarMensagensMesaWidgetComPerf(...args) {
                const opcoes = args[0] && typeof args[0] === "object" ? args[0] : {};
                return PERF.measureAsync(
                    "inspetor.mesaWidget.carregarMensagensMesaWidget",
                    async () => {
                        const resultado = await carregarMensagensMesaWidgetOriginal.apply(this, args);
                        PERF.snapshotDOM?.("mesa-widget:mensagens-carregadas");
                        return resultado;
                    },
                    {
                        category: "function",
                        detail: {
                            laudoId: opcoes.laudoId || obterLaudoAtivoIdSeguro?.() || null,
                            append: opcoes.append === true,
                            silencioso: opcoes.silencioso === true,
                        },
                    }
                );
            };

            const enviarMensagemMesaWidgetOriginal = enviarMensagemMesaWidget;
            enviarMensagemMesaWidget = async function enviarMensagemMesaWidgetComPerf(...args) {
                return PERF.measureAsync(
                    "inspetor.mesaWidget.enviarMensagemMesaWidget",
                    () => enviarMensagemMesaWidgetOriginal.apply(this, args),
                    {
                        category: "function",
                        detail: {
                            laudoId: obterLaudoAtivoIdSeguro?.() || null,
                            textoTamanho: String(el.mesaWidgetInput?.value || "").length,
                            possuiAnexo: !!estado.mesaWidgetAnexoPendente,
                        },
                    }
                );
            };

            const abrirMesaWidgetOriginal = abrirMesaWidget;
            abrirMesaWidget = async function abrirMesaWidgetComPerf(...args) {
                PERF.begin("transition.abrir_mesa_widget", {
                    laudoId: obterLaudoAtivoIdSeguro?.() || null,
                });
                return PERF.measureAsync(
                    "inspetor.mesaWidget.abrirMesaWidget",
                    async () => {
                        const resultado = await abrirMesaWidgetOriginal.apply(this, args);
                        PERF.finish("transition.abrir_mesa_widget", {
                            laudoId: obterLaudoAtivoIdSeguro?.() || null,
                        });
                        PERF.snapshotDOM?.("mesa-widget:aberto");
                        return resultado;
                    },
                    {
                        category: "transition",
                        detail: {
                            laudoId: obterLaudoAtivoIdSeguro?.() || null,
                        },
                    }
                );
            };

            const fecharMesaWidgetOriginal = fecharMesaWidget;
            fecharMesaWidget = function fecharMesaWidgetComPerf(...args) {
                return PERF.measureSync(
                    "inspetor.mesaWidget.fecharMesaWidget",
                    () => fecharMesaWidgetOriginal.apply(this, args),
                    {
                        category: "function",
                        detail: {
                            laudoId: obterLaudoAtivoIdSeguro?.() || null,
                        },
                    }
                );
            };
        }

        Object.assign(ctx.actions, {
            limparAnexoMesaWidget,
            renderizarPreviewAnexoMesaWidget,
            selecionarAnexoMesaWidget,
            obterUltimaMensagemMesaOperacional,
            resumirMensagemOperacionalMesa,
            obterResumoOperacionalMesa,
            renderizarResumoOperacionalMesa,
            atualizarEstadoVisualBotaoMesaWidget,
            sincronizarClasseBodyMesaWidget,
            atualizarConexaoMesaWidget,
            atualizarBadgeMesaWidget,
            limparReferenciaMesaWidget,
            definirReferenciaMesaWidget,
            normalizarMensagemMesa,
            obterMensagemMesaPorId,
            irParaMensagemPrincipal,
            renderizarListaMesaWidget,
            carregarMensagensMesaWidget,
            enviarMensagemMesaWidget,
            abrirMesaWidget,
            fecharMesaWidget,
            toggleMesaWidget,
            atualizarChatAoVivoComMesa,
        });
    };
})();
