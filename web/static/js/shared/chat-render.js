// ==========================================
// TARIEL CONTROL TOWER — CHAT-RENDER.JS
// Renderização visual do chat.
// Responsável por:
// - bolhas de mensagem
// - markdown
// - blocos de código
// - citações normativas
// - ações pós-resposta
// - mensagens humanas / engenharia
// ==========================================

(function () {
    "use strict";

    // Evita inicialização duplicada do arquivo.
    if (window.__TARIEL_CHAT_RENDER_WIRED__) return;
    window.__TARIEL_CHAT_RENDER_WIRED__ = true;
    const PERF_GLOBAL = window.TarielPerf || window.TarielCore?.TarielPerf || null;

    PERF_GLOBAL?.noteModule?.("shared/chat-render.js", {
        readyState: document.readyState,
    });

    window.TarielChatRender = function criarChatRender(deps = {}) {
        // =========================================================
        // DEPENDÊNCIAS EXTERNAS
        // =========================================================
        const {
            areaMensagens = null,
            escapeHTML = (valor) =>
                String(valor ?? "")
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#39;"),
            mostrarToast = () => {},
            validarPrefixoBase64 = () => "",
            rolarParaBaixo = () => {},
            getNomeUsuario = () => "Usuário",
            getNomeEmpresa = () => "Empresa",
            getUltimoDiagnosticoBruto = () => "",
            getHistoricoConversa = () => [],
            getIaRespondendo = () => false,
            getEstadoRelatorio = () => "sem_relatorio",
            getSetorAtual = () => "geral",
            getUltimaMensagemUsuario = () => "",
            enviarParaIA = () => null,
            finalizarRelatorio = () => null,
            preencherCampoMensagem = () => {},
            enviarFeedback = () => null,
            gerarPDF = () => null,
        } = deps;

        if (!areaMensagens) {
            console.warn("[Tariel] TarielChatRender inicializado sem areaMensagens. Módulo desativado em fail-safe.");
            return null;
        }
        const PERF = PERF_GLOBAL;

        // Remove handler anterior caso a factory seja recriada no mesmo container.
        if (typeof areaMensagens.__tarielRenderClickHandler === "function") {
            areaMensagens.removeEventListener("click", areaMensagens.__tarielRenderClickHandler);
        }

        areaMensagens.dataset.tarielRenderBound = "true";

        // =========================================================
        // CONSTANTES
        // =========================================================
        const REGEX = {
            MENCOES_ENG: /@(eng|engenharia|revisor)\b/gi,
            MENCOES_INSP: /@(insp|inspetor)\b/gi,
        };

        // =========================================================
        // UTILITÁRIOS
        // =========================================================

        function textoSeguro(valor) {
            return valor == null ? "" : String(valor);
        }

        function historicoSeguro() {
            const historico = getHistoricoConversa?.();
            return Array.isArray(historico) ? historico : [];
        }

        function normalizarModo(modo) {
            const valor = String(modo || "").trim().toLowerCase();

            if (valor === "deep_research" || valor === "deepresearch") {
                return "deepresearch";
            }

            if (valor === "curto") {
                return "curto";
            }

            return "detalhado";
        }

        function normalizarEstadoRelatorio(valor) {
            const estado = String(valor || "").trim().toLowerCase();

            if (estado === "relatorioativo" || estado === "relatorio_ativo") {
                return "relatorio_ativo";
            }

            if (estado === "semrelatorio" || estado === "sem_relatorio") {
                return "sem_relatorio";
            }

            if (estado === "aguardando" || estado === "aguardando_avaliacao") {
                return "aguardando";
            }

            return estado || "sem_relatorio";
        }

        function ehWhisper(texto) {
            if (typeof texto !== "string") return false;
            return /^@(eng|engenharia|revisor|insp|inspetor)\b/i.test(texto.trim());
        }

        function quebrasDeLinhaParaBr(texto) {
            return String(texto || "").replace(/\n/g, "<br>");
        }

        function destacarMencoes(htmlEscapado) {
            return String(htmlEscapado || "")
                .replace(REGEX.MENCOES_ENG, '<strong class="tag-whisper tag-eng">$&</strong>')
                .replace(REGEX.MENCOES_INSP, '<strong class="tag-whisper tag-insp">$&</strong>');
        }

        function obterUltimaMensagemUsuarioSeguro() {
            const viaGetter = textoSeguro(getUltimaMensagemUsuario?.()).trim();
            if (viaGetter) return viaGetter;

            const historico = historicoSeguro();
            for (let i = historico.length - 1; i >= 0; i--) {
                const item = historico[i];
                const papel = String(item?.papel || item?.role || "").trim().toLowerCase();
                const texto = textoSeguro(item?.texto || item?.content || "").trim();

                if (papel === "usuario" && texto) {
                    return texto;
                }
            }

            return "";
        }

        function textoRepresentaErroResposta(texto = "") {
            const valor = textoSeguro(texto).trim().toLowerCase();
            if (!valor) return false;

            return valor.startsWith("[erro]")
                || valor.includes("permission_denied")
                || valor.includes("http_");
        }

        function markupAvatarTariel() {
            return `<span class="workspace-message-avatar__brand" aria-hidden="true">T</span>`;
        }

        function copiarTexto(texto) {
            const valor = textoSeguro(texto);
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

        function emitirAcaoMensagem(tipo, detail = {}) {
            document.dispatchEvent(new CustomEvent(`tariel:mensagem-${tipo}`, {
                detail,
                bubbles: true,
            }));
        }

        function montarDetalheMensagem(elemento, texto = "") {
            const linha = elemento?.closest?.(".linha-mensagem") || elemento;
            const autor = textoSeguro(
                linha?.dataset?.messageAuthor
                || linha?.querySelector?.(".mensagem-meta strong")?.textContent
            ).trim() || "Registro";
            const papel = textoSeguro(
                linha?.dataset?.messageRole
                || (linha?.classList?.contains("mensagem-sistema")
                    ? "sistema"
                    : linha?.classList?.contains("mensagem-origem-mesa")
                        ? "mesa"
                        : linha?.classList?.contains("mensagem-ia")
                            ? "ia"
                            : "inspetor")
            ).trim().toLowerCase() || "registro";
            const mensagemId = Number(linha?.dataset?.mensagemId || 0) || null;
            const conteudo = textoSeguro(
                texto
                || linha?.querySelector?.(".texto-msg")?.textContent
                || linha?.querySelector?.(".texto-msg-origem")?.textContent
            ).replace(/\s+/g, " ").trim();

            return {
                mensagemId,
                autor,
                papel,
                texto: conteudo,
            };
        }

        function criarBotaoAcao(icone, rotulo, handler) {
            const btn = document.createElement("button");
            btn.className = "btn-acao-msg workspace-message-action";
            btn.type = "button";

            btn.innerHTML = rotulo
                ? `<span class="material-symbols-rounded" aria-hidden="true">${icone}</span><span>${escapeHTML(rotulo)}</span>`
                : `<span class="material-symbols-rounded" aria-hidden="true">${icone}</span>`;

            if (!rotulo) {
                btn.classList.add("workspace-message-action--icon-only");
                btn.setAttribute("aria-label", icone.replace(/_/g, " "));
            }

            btn.addEventListener("click", handler);
            return btn;
        }

        function normalizarPapelMensagem(papel = "") {
            const valor = textoSeguro(papel).trim().toLowerCase();

            if (valor === "inspetor" || valor === "usuario" || valor === "user") {
                return "user";
            }

            if (valor === "mesa" || valor === "engenharia" || valor === "revisor") {
                return "mesa";
            }

            if (valor === "sistema" || valor === "system") {
                return "system";
            }

            return "assistant";
        }

        function aplicarEstruturaMensagemWorkspace(linha, papel = "") {
            if (!linha) return { linha: null, conteudo: null, avatar: null, corpo: null };

            const papelNormalizado = normalizarPapelMensagem(papel || linha.dataset.messageRole);
            linha.classList.add("workspace-message-row");
            linha.classList.remove(
                "workspace-message-row--assistant",
                "workspace-message-row--user",
                "workspace-message-row--mesa",
                "workspace-message-row--system"
            );

            if (papelNormalizado === "user") {
                linha.classList.add("workspace-message-row--user");
            } else if (papelNormalizado === "mesa") {
                linha.classList.add("workspace-message-row--mesa");
            } else if (papelNormalizado === "system") {
                linha.classList.add("workspace-message-row--system");
            } else {
                linha.classList.add("workspace-message-row--assistant");
            }

            linha.dataset.messageVariant = papelNormalizado;

            const conteudo = linha.querySelector(".conteudo-mensagem");
            if (conteudo) {
                conteudo.classList.add("workspace-message-shell");
            }

            const avatar = linha.querySelector(".avatar");
            if (avatar) {
                avatar.classList.add("workspace-message-avatar");
            }

            const corpo = linha.querySelector(".corpo-texto");
            if (corpo) {
                corpo.classList.add("workspace-message-card");
                corpo.querySelectorAll(".mensagem-meta").forEach((meta) => {
                    meta.classList.add("workspace-message-meta");
                });
                corpo.querySelectorAll(".texto-msg, .texto-msg-origem").forEach((blocoTexto) => {
                    blocoTexto.classList.add("workspace-message-body");
                });
                corpo.querySelectorAll(".bloco-referencia-chat").forEach((referencia) => {
                    referencia.classList.add("workspace-message-reference");
                });
                corpo.querySelectorAll(".mensagem-anexos").forEach((anexos) => {
                    anexos.classList.add("workspace-message-attachments");
                });
                corpo.querySelectorAll(".mensagem-anexo-chip").forEach((chip) => {
                    chip.classList.add("workspace-message-attachment");
                });
            }

            return {
                linha,
                conteudo,
                avatar,
                corpo,
            };
        }

        function criarBlocoReferenciaMensagem(referenciaId, referenciaTexto = "") {
            const idNumerico = Number(referenciaId);
            if (!Number.isFinite(idNumerico) || idNumerico <= 0) return null;

            const bloco = document.createElement("button");
            bloco.type = "button";
            bloco.className = "bloco-referencia-chat workspace-message-reference";
            bloco.dataset.refId = String(idNumerico);
            bloco.setAttribute("aria-label", `Ir para mensagem #${idNumerico}`);

            const textoPreview = textoSeguro(referenciaTexto || "");
            const preview = textoPreview
                ? (textoPreview.length > 140 ? `${textoPreview.slice(0, 140)}...` : textoPreview)
                : `Mensagem #${idNumerico}`;

            bloco.innerHTML = `
                <span class="material-symbols-rounded" aria-hidden="true">reply</span>
                <span class="ref-conteudo">
                    <strong>Respondendo #${idNumerico}</strong>
                    <span>${escapeHTML(preview)}</span>
                </span>
            `;
            return bloco;
        }

        function formatarTempoRelativo(valorIso = "", fallback = "") {
            const iso = textoSeguro(valorIso).trim();
            const fallbackSeguro = textoSeguro(fallback).trim();
            if (!iso) return fallbackSeguro;

            try {
                const data = new Date(iso);
                if (Number.isNaN(data.getTime())) return fallbackSeguro;

                const diffMs = Math.max(0, Date.now() - data.getTime());
                const diffMin = Math.max(1, Math.round(diffMs / 60000));

                if (diffMin < 60) {
                    return `há ${diffMin}min`;
                }

                const diffHoras = Math.round(diffMin / 60);
                if (diffHoras < 24) {
                    return `há ${diffHoras} hora${diffHoras > 1 ? "s" : ""}`;
                }

                const diffDias = Math.round(diffHoras / 24);
                return diffDias <= 1 ? "ontem" : `há ${diffDias} dias`;
            } catch (_) {
                return fallbackSeguro;
            }
        }

        function criarMetaMensagem({ autor = "", tempo = "", destaque = "", dateTime = "" } = {}) {
            const meta = document.createElement("div");
            meta.className = "mensagem-meta workspace-message-meta";

            const titulo = document.createElement("strong");
            titulo.textContent = textoSeguro(autor).trim() || "Registro";
            meta.appendChild(titulo);

            const destaqueSeguro = textoSeguro(destaque).trim();
            if (destaqueSeguro) {
                const etiqueta = document.createElement("span");
                etiqueta.className = "mensagem-meta__tag";
                etiqueta.textContent = destaqueSeguro;
                meta.appendChild(etiqueta);
            }

            const tempoSeguro = textoSeguro(tempo).trim();
            if (tempoSeguro) {
                const relogio = document.createElement("time");
                relogio.textContent = tempoSeguro;
                if (textoSeguro(dateTime).trim()) {
                    relogio.dateTime = textoSeguro(dateTime).trim();
                }
                meta.appendChild(relogio);
            }

            return meta;
        }

        function ehAnexoPdf(item = {}) {
            const mimeType = textoSeguro(item?.mime_type).trim().toLowerCase();
            const nome = textoSeguro(item?.nome || item?.filename || item?.titulo).trim().toLowerCase();
            return mimeType === "application/pdf" || nome.endsWith(".pdf");
        }

        function criarBlocoAnexosMensagem(anexos = [], nomeDoc = null, opcoes = {}) {
            const opts = (opcoes && typeof opcoes === "object") ? opcoes : {};
            const destacarPdfPrincipal = opts.destacarPdfPrincipal === true;
            const rotuloPdfPrincipal = textoSeguro(opts.rotuloPdfPrincipal).trim() || "Baixar relatório em PDF";
            const itens = [];
            const vistos = new Set();

            if (textoSeguro(nomeDoc).trim()) {
                itens.push({
                    nome: textoSeguro(nomeDoc).trim(),
                    url: "",
                    eh_imagem: false,
                    eh_pdf: false,
                    destaque_principal: false,
                });
            }

            if (Array.isArray(anexos)) {
                anexos.forEach((item) => {
                    if (!item || typeof item !== "object") return;

                    const nome = textoSeguro(item?.nome || item?.filename || item?.titulo).trim();
                    const url = textoSeguro(item?.url || item?.href).trim();
                    const mimeType = textoSeguro(item?.mime_type).trim().toLowerCase();
                    const ehImagem = !!item?.eh_imagem || mimeType.startsWith("image/");
                    const ehPdf = ehAnexoPdf(item);

                    if (!nome && !url) return;

                    itens.push({
                        nome: nome || (ehImagem ? "imagem" : "anexo"),
                        url,
                        eh_imagem: ehImagem,
                        eh_pdf: ehPdf,
                        destaque_principal: false,
                    });
                });
            }

            const normalizados = itens.filter((item) => {
                const chave = `${textoSeguro(item?.url)}::${textoSeguro(item?.nome)}`;
                if (vistos.has(chave)) return false;
                vistos.add(chave);
                return true;
            });

            if (!normalizados.length) return null;

            if (destacarPdfPrincipal) {
                const pdfPrincipal = normalizados.find((item) => item?.eh_pdf && textoSeguro(item?.url).trim());
                if (pdfPrincipal) {
                    pdfPrincipal.destaque_principal = true;
                    if (
                        !textoSeguro(pdfPrincipal.nome).trim()
                        || /^relatorio_tecnico_inspecao_\d+\.pdf$/i.test(textoSeguro(pdfPrincipal.nome).trim())
                    ) {
                        pdfPrincipal.nome = rotuloPdfPrincipal;
                    }
                }
            }

            const bloco = document.createElement("div");
            bloco.className = "mensagem-anexos workspace-message-attachments";

            normalizados.forEach((anexo) => {
                const icone = anexo.eh_imagem ? "image" : (anexo.eh_pdf ? "picture_as_pdf" : "description");
                const url = textoSeguro(anexo.url).trim();
                const nome = textoSeguro(anexo.nome).trim() || "anexo";
                const chip = url ? document.createElement("a") : document.createElement("span");

                chip.className = "mensagem-anexo-chip workspace-message-attachment";
                if (anexo.eh_pdf) {
                    chip.classList.add("workspace-message-attachment--pdf");
                }
                if (anexo.destaque_principal) {
                    chip.classList.add("workspace-message-attachment--report");
                }
                if (url) {
                    chip.href = url;
                    chip.target = "_blank";
                    chip.rel = "noopener noreferrer";
                }

                if (anexo.destaque_principal) {
                    chip.innerHTML = `
                        <span class="material-symbols-rounded" aria-hidden="true">${icone}</span>
                        <span class="workspace-message-attachment__content">
                            <strong>${escapeHTML(nome)}</strong>
                            <small>abre o PDF em nova aba</small>
                        </span>
                    `;
                } else {
                    chip.innerHTML = `
                        <span class="material-symbols-rounded" aria-hidden="true">${icone}</span>
                        <span>${escapeHTML(nome)}</span>
                    `;
                }

                bloco.appendChild(chip);
            });

            return bloco;
        }

        function renderizarAnexosMensagem(elementoMensagem, anexos = [], nomeDoc = null, opcoes = {}) {
            const linha = elementoMensagem?.closest?.(".linha-mensagem") || elementoMensagem;
            if (!linha) return null;

            const { corpo } = aplicarEstruturaMensagemWorkspace(
                linha,
                linha.dataset?.messageRole || "ia"
            );
            if (!corpo) return null;

            corpo.querySelectorAll('.mensagem-anexos[data-render-source="runtime"]').forEach((bloco) => {
                bloco.remove();
            });

            const blocoAnexos = criarBlocoAnexosMensagem(anexos, nomeDoc, opcoes);
            if (!blocoAnexos) return null;

            blocoAnexos.dataset.renderSource = "runtime";
            const acoes = corpo.querySelector(".workspace-message-actions, .acoes-mensagem");
            if (acoes) {
                corpo.insertBefore(blocoAnexos, acoes);
            } else {
                corpo.appendChild(blocoAnexos);
            }

            return blocoAnexos;
        }

        // =========================================================
        // RENDERIZAÇÃO DE MENSAGENS
        // =========================================================

        function ocultarEmptyStateHonestoConversa() {
            const emptyState = document.getElementById("workspace-conversation-empty");
            if (!emptyState) return;
            emptyState.hidden = true;
            emptyState.setAttribute("aria-hidden", "true");
        }

        function adicionarMensagemInspetor(
            texto,
            imagemBase64,
            nomeDoc = null,
            idMensagem = null,
            opcoes = {}
        ) {
            const opts = (opcoes && typeof opcoes === "object") ? opcoes : {};
            const whisper = ehWhisper(texto);
            const tempoMensagem = formatarTempoRelativo(opts.criadoEmIso, opts.dataLabel);

            const linha = document.createElement("div");
            linha.className = `linha-mensagem mensagem-inspetor workspace-message-row workspace-message-row--user${whisper ? " whisper-msg" : ""}`;
            linha.dataset.messageRole = "inspetor";
            linha.dataset.messageAuthor = textoSeguro(getNomeUsuario?.() || "João Silva").trim() || "João Silva";
            ocultarEmptyStateHonestoConversa();

            const mensagemIdPersistida = Number(opts.mensagemId);
            if (Number.isFinite(mensagemIdPersistida) && mensagemIdPersistida > 0) {
                linha.dataset.mensagemId = String(mensagemIdPersistida);
            } else if (idMensagem) {
                linha.dataset.mensagemId = String(idMensagem);
                linha.dataset.tmpId = String(idMensagem);
            }

            const avatar = document.createElement("div");
            avatar.className = "avatar workspace-message-avatar";
            avatar.setAttribute("aria-hidden", "true");
            avatar.innerHTML = `
                <span class="material-symbols-rounded">
                    ${whisper ? "headset_mic" : "person"}
                </span>
            `;

            if (whisper) {
                avatar.style.background = "#F47B20";
                avatar.style.color = "#fff";
            }

            const corpo = document.createElement("div");
            corpo.className = "corpo-texto workspace-message-card";

            corpo.appendChild(criarMetaMensagem({
                autor: textoSeguro(getNomeUsuario?.() || "João Silva"),
                tempo: tempoMensagem,
                destaque: whisper ? "Mesa Avaliadora" : "",
                dateTime: opts.criadoEmIso,
            }));

            const blocoReferencia = criarBlocoReferenciaMensagem(
                opts.referenciaMensagemId,
                opts.referenciaTexto
            );
            if (blocoReferencia) {
                corpo.appendChild(blocoReferencia);
            }

            if (nomeDoc) {
                corpo.dataset.temDocumentoPrincipal = "true";
            }

            if (imagemBase64) {
                const base64Validado = validarPrefixoBase64(imagemBase64);

                if (base64Validado) {
                    const img = document.createElement("img");
                    img.src = base64Validado;
                    img.alt = "Evidência enviada";
                    img.className = "img-anexo";
                    corpo.appendChild(img);
                }
            }

            if (texto) {
                const blocoTexto = document.createElement("div");
                blocoTexto.className = "texto-msg workspace-message-body";
                blocoTexto.innerHTML = quebrasDeLinhaParaBr(destacarMencoes(escapeHTML(texto)));
                corpo.appendChild(blocoTexto);
            }

            const blocoAnexos = criarBlocoAnexosMensagem(opts.anexos, nomeDoc);
            if (blocoAnexos) {
                corpo.appendChild(blocoAnexos);
            }

            if (idMensagem && !opts.omitirStatusEntrega) {
                const tiques = document.createElement("span");
                tiques.className = "tiques-status status-enviado";
                tiques.setAttribute("aria-hidden", "true");
                corpo.appendChild(tiques);
            }

            const conteudo = document.createElement("div");
            conteudo.className = "conteudo-mensagem workspace-message-shell";
            conteudo.appendChild(avatar);
            conteudo.appendChild(corpo);

            linha.appendChild(conteudo);
            aplicarEstruturaMensagemWorkspace(linha, "inspetor");
            areaMensagens.appendChild(linha);

            rolarParaBaixo();
            return linha;
        }

        function criarBolhaIA(modo = "detalhado", opcoes = {}) {
            const modoNormalizado = normalizarModo(modo);
            const opts = (opcoes && typeof opcoes === "object") ? opcoes : {};
            const autor = textoSeguro(opts.autor).trim() || "Tariel IA";
            const ehSistema = autor.toLowerCase() === "sistema";
            const tempoMensagem = formatarTempoRelativo(opts.criadoEmIso, opts.dataLabel);

            const linha = document.createElement("div");
            linha.className = `linha-mensagem workspace-message-row ${ehSistema ? "mensagem-sistema workspace-message-row--system" : "mensagem-ia workspace-message-row--assistant"}`;
            linha.dataset.messageRole = ehSistema ? "sistema" : "ia";
            linha.dataset.messageAuthor = autor;
            const mensagemIdPersistida = Number(opts.mensagemId);
            if (Number.isFinite(mensagemIdPersistida) && mensagemIdPersistida > 0) {
                linha.dataset.mensagemId = String(mensagemIdPersistida);
            }
            ocultarEmptyStateHonestoConversa();

            const textoMsg = document.createElement("div");
            textoMsg.className = "texto-msg workspace-message-body";

            const cursor = document.createElement("span");
            cursor.className = "cursor-piscando";
            cursor.setAttribute("aria-hidden", "true");
            cursor.textContent = "▍";

            const corpo = document.createElement("div");
            corpo.className = "corpo-texto workspace-message-card";
            corpo.appendChild(criarMetaMensagem({
                autor,
                tempo: tempoMensagem,
                dateTime: opts.criadoEmIso,
            }));

            if (!ehSistema && modoNormalizado === "deepresearch") {
                const badge = document.createElement("span");
                badge.className = "badge-modo badge-deep-research";
                badge.setAttribute("aria-label", "Modo Deep Research");
                badge.innerHTML = `
                    <span class="material-symbols-rounded" aria-hidden="true">search</span>
                    Deep Research
                `;
                corpo.appendChild(badge);
            } else if (!ehSistema && modoNormalizado === "curto") {
                const badge = document.createElement("span");
                badge.className = "badge-modo badge-modo-curto";
                badge.setAttribute("aria-label", "Modo curto");
                badge.innerHTML = `
                    <span class="material-symbols-rounded" aria-hidden="true">compress</span>
                    Curto
                `;
                corpo.appendChild(badge);
            }

            corpo.appendChild(textoMsg);
            corpo.appendChild(cursor);

            const avatar = document.createElement("div");
            avatar.className = "avatar workspace-message-avatar";
            avatar.setAttribute("aria-hidden", "true");
            avatar.innerHTML = ehSistema
                ? `<span class="material-symbols-rounded">info</span>`
                : markupAvatarTariel();

            const conteudo = document.createElement("div");
            conteudo.className = "conteudo-mensagem workspace-message-shell";
            conteudo.appendChild(avatar);
            conteudo.appendChild(corpo);

            linha.appendChild(conteudo);
            aplicarEstruturaMensagemWorkspace(linha, ehSistema ? "sistema" : "ia");
            areaMensagens.appendChild(linha);

            rolarParaBaixo();
            return linha;
        }

        function adicionarMensagemNaUI(remetente, texto, tipo, opcoes = {}) {
            const opts = (opcoes && typeof opcoes === "object") ? opcoes : {};
            const remetenteNormalizado = textoSeguro(remetente).toLowerCase();
            const tipoNormalizado = textoSeguro(tipo).toLowerCase();

            const ehEngenharia =
                remetenteNormalizado.includes("engenh") ||
                remetenteNormalizado.includes("mesa") ||
                remetenteNormalizado.includes("revisor") ||
                tipoNormalizado === "humano_eng" ||
                tipoNormalizado === "humanoeng";
            const titulo = ehEngenharia ? "Mesa Avaliadora" : (textoSeguro(remetente).trim() || "Inspetor");

            const linha = document.createElement("div");
            linha.className = `linha-mensagem workspace-message-row ${ehEngenharia ? "mensagem-origem-mesa whisper-eng workspace-message-row--mesa" : "mensagem-inspetor whisper-insp workspace-message-row--user"}`;
            linha.dataset.messageRole = ehEngenharia ? "mesa" : "inspetor";
            linha.dataset.messageAuthor = titulo;
            ocultarEmptyStateHonestoConversa();
            const mensagemIdPersistida = Number(opts.mensagemId);
            if (Number.isFinite(mensagemIdPersistida) && mensagemIdPersistida > 0) {
                linha.dataset.mensagemId = String(mensagemIdPersistida);
            }

            const avatarIcone = ehEngenharia ? "engineering" : "person";
            const origemClasse = ehEngenharia ? "origem-mesa" : "origem-insp";
            const blocoReferencia = criarBlocoReferenciaMensagem(
                opts.referenciaMensagemId,
                opts.referenciaTexto
            );
            const tempoMensagem = formatarTempoRelativo(opts.criadoEmIso, opts.dataLabel);

            linha.innerHTML = `
                <div class="conteudo-mensagem workspace-message-shell">
                    <div class="avatar avatar-origem workspace-message-avatar ${origemClasse}">
                        <span class="material-symbols-rounded">${avatarIcone}</span>
                    </div>
                    <div class="corpo-texto workspace-message-card">
                        <div class="mensagem-meta workspace-message-meta nome-remetente-origem ${origemClasse}">
                            <strong>${escapeHTML(titulo)}</strong>
                            ${tempoMensagem ? `<time${textoSeguro(opts.criadoEmIso).trim() ? ` datetime="${escapeHTML(textoSeguro(opts.criadoEmIso).trim())}"` : ""}>${escapeHTML(tempoMensagem)}</time>` : ""}
                        </div>
                        <div class="texto-msg texto-msg-origem workspace-message-body ${origemClasse}">
                            ${quebrasDeLinhaParaBr(destacarMencoes(escapeHTML(textoSeguro(texto))))}
                        </div>
                    </div>
                </div>
            `;

            if (blocoReferencia) {
                const corpo = linha.querySelector(".corpo-texto");
                corpo?.insertBefore(blocoReferencia, corpo.querySelector(".texto-msg"));
            }

            aplicarEstruturaMensagemWorkspace(linha, ehEngenharia ? "mesa" : "inspetor");
            areaMensagens.appendChild(linha);
            rolarParaBaixo();

            return linha;
        }

        // =========================================================
        // AÇÕES PÓS-RESPOSTA
        // =========================================================

        function mostrarAcoesPosResposta(elementoIA, textoBolha) {
            if (!elementoIA) return;

            const { corpo } = aplicarEstruturaMensagemWorkspace(
                elementoIA,
                elementoIA.dataset?.messageRole || "ia"
            );
            if (!corpo) return;

            elementoIA.querySelectorAll(".acoes-mensagem, .workspace-message-actions").forEach((bloco) => {
                bloco.remove();
            });

            const acoes = document.createElement("div");
            acoes.className = "acoes-mensagem workspace-message-actions workspace-message-actions--assistant";
            acoes.setAttribute("role", "toolbar");
            acoes.setAttribute("aria-label", "Ações da resposta");

            const obterTextoBase = () => textoSeguro(textoBolha || getUltimoDiagnosticoBruto?.());
            if (textoRepresentaErroResposta(obterTextoBase())) {
                return;
            }

            const btnCopiar = criarBotaoAcao("content_copy", "Copiar", async () => {
                const texto = obterTextoBase();
                if (!texto) return;

                try {
                    await copiarTexto(texto);

                    const icone = btnCopiar.querySelector(".material-symbols-rounded");
                    const rotulo = btnCopiar.querySelector("span:last-child");

                    if (icone) icone.textContent = "check";
                    if (rotulo) rotulo.textContent = "Copiado!";

                    btnCopiar.classList.add("copiado");

                    setTimeout(() => {
                        if (icone) icone.textContent = "content_copy";
                        if (rotulo) rotulo.textContent = "Copiar";
                        btnCopiar.classList.remove("copiado");
                    }, 2000);
                } catch (_) {
                    mostrarToast("Não foi possível copiar. Use Ctrl+A e Ctrl+C.", "aviso");
                }
            });

            const btnPdf = criarBotaoAcao("picture_as_pdf", "PDF", () => {
                const texto = obterTextoBase();
                if (!texto) return;
                gerarPDF?.();
            });

            const btnCitar = criarBotaoAcao("format_quote", "Citar", () => {
                const detalhe = montarDetalheMensagem(elementoIA, obterTextoBase());
                if (!detalhe.texto) return;
                emitirAcaoMensagem("citar", detalhe);
            });

            const btnMesa = criarBotaoAcao("support_agent", "Mesa", () => {
                const detalhe = montarDetalheMensagem(elementoIA, obterTextoBase());
                if (!detalhe.texto) return;
                emitirAcaoMensagem("enviar-mesa", detalhe);
            });

            const btnFixar = criarBotaoAcao("keep", "Fixar", () => {
                const detalhe = montarDetalheMensagem(elementoIA, obterTextoBase());
                if (!detalhe.texto) return;
                emitirAcaoMensagem("fixar-contexto", detalhe);
            });

            let btnCurtir;
            let btnDescurtir;

            btnCurtir = criarBotaoAcao("thumb_up", "", () => {
                const ativo = btnCurtir.getAttribute("aria-pressed") === "true";
                const iconeCurtir = btnCurtir.querySelector(".material-symbols-rounded");
                const iconeDescurtir = btnDescurtir.querySelector(".material-symbols-rounded");

                btnCurtir.setAttribute("aria-pressed", String(!ativo));
                btnDescurtir.setAttribute("aria-pressed", "false");

                if (iconeCurtir) iconeCurtir.style.color = ativo ? "" : "var(--badge-conforme)";
                if (iconeDescurtir) iconeDescurtir.style.color = "";

                if (!ativo) {
                    mostrarToast("Feedback registrado.", "sucesso", 2000);
                    enviarFeedback?.("positivo", obterTextoBase());
                }
            });

            btnCurtir.setAttribute("aria-pressed", "false");
            btnCurtir.setAttribute("aria-label", "Resposta útil");
            btnCurtir.title = "Útil";

            btnDescurtir = criarBotaoAcao("thumb_down", "", () => {
                const ativo = btnDescurtir.getAttribute("aria-pressed") === "true";
                const iconeDescurtir = btnDescurtir.querySelector(".material-symbols-rounded");
                const iconeCurtir = btnCurtir.querySelector(".material-symbols-rounded");

                btnDescurtir.setAttribute("aria-pressed", String(!ativo));
                btnCurtir.setAttribute("aria-pressed", "false");

                if (iconeDescurtir) iconeDescurtir.style.color = ativo ? "" : "#ef5350";
                if (iconeCurtir) iconeCurtir.style.color = "";

                if (!ativo) {
                    mostrarToast("Feedback registrado.", "info", 2500);
                    enviarFeedback?.("negativo", obterTextoBase());
                }
            });

            btnDescurtir.setAttribute("aria-pressed", "false");
            btnDescurtir.setAttribute("aria-label", "Resposta não útil");
            btnDescurtir.title = "Não útil";

            const btnEditar = criarBotaoAcao("edit", "", () => {
                if (getIaRespondendo?.()) return;

                const ultimaMensagem = obterUltimaMensagemUsuarioSeguro();
                if (!ultimaMensagem) return;

                preencherCampoMensagem?.(ultimaMensagem);

                const campo = document.getElementById("campo-mensagem");
                if (campo && !String(campo.value || "").trim()) {
                    campo.value = ultimaMensagem;
                    campo.dispatchEvent(new Event("input", { bubbles: true }));
                }

                mostrarToast("Mensagem carregada para edição.", "info", 2000);
            });

            btnEditar.setAttribute("aria-label", "Editar último prompt");
            btnEditar.title = "Editar prompt";

            const btnRegenerar = criarBotaoAcao("refresh", "", async () => {
                if (getIaRespondendo?.()) return;

                const ultimaMensagem = obterUltimaMensagemUsuarioSeguro();
                if (!ultimaMensagem) return;

                try {
                    const resposta = await Promise.resolve(
                        enviarParaIA?.(ultimaMensagem, null, getSetorAtual?.() || "geral")
                    );

                    if (resposta?.ok) {
                        elementoIA.remove();
                    } else {
                        mostrarToast("Não foi possível regenerar a resposta.", "erro");
                    }
                } catch (_) {
                    mostrarToast("Não foi possível regenerar a resposta.", "erro");
                }
            });

            btnRegenerar.setAttribute("aria-label", "Regenerar resposta");
            btnRegenerar.title = "Regenerar";

            const btnContinuar = criarBotaoAcao("play_arrow", "", async () => {
                if (getIaRespondendo?.()) return;

                try {
                    await Promise.resolve(
                        enviarParaIA?.(
                            "Continue a resposta anterior exatamente do ponto em que parou, mantendo o mesmo contexto técnico.",
                            null,
                            getSetorAtual?.() || "geral"
                        )
                    );
                } catch (_) {
                    mostrarToast("Não foi possível continuar a resposta.", "erro");
                }
            });

            btnContinuar.setAttribute("aria-label", "Continuar resposta");
            btnContinuar.title = "Continuar";

            acoes.appendChild(btnCopiar);
            acoes.appendChild(btnPdf);
            acoes.appendChild(btnCitar);
            acoes.appendChild(btnMesa);
            acoes.appendChild(btnFixar);
            acoes.appendChild(btnCurtir);
            acoes.appendChild(btnDescurtir);
            acoes.appendChild(btnEditar);
            acoes.appendChild(btnContinuar);
            acoes.appendChild(btnRegenerar);

            if (normalizarEstadoRelatorio(getEstadoRelatorio?.()) === "relatorio_ativo") {
                const btnFinalizar = criarBotaoAcao("send", "Finalizar", () => {
                    finalizarRelatorio?.();
                });

                btnFinalizar.className = "btn-acao-msg workspace-message-action workspace-message-action--primary btn-finalizar-relatorio";
                btnFinalizar.setAttribute("aria-label", "Finalizar e enviar para a mesa");
                btnFinalizar.title = "Enviar para revisão";

                acoes.appendChild(btnFinalizar);
            }

            corpo.appendChild(acoes);
        }

        function renderizarConfiancaIA(elementoIA, payload) {
            if (!elementoIA || !payload || typeof payload !== "object") return;

            const corpo = elementoIA.querySelector(".corpo-texto");
            if (!corpo) return;

            const textoResposta = textoSeguro(corpo.querySelector(".texto-msg")?.textContent || "");
            if (textoRepresentaErroResposta(textoResposta)) {
                corpo.querySelector(".bloco-confianca-ia")?.remove();
                return;
            }

            corpo.querySelector(".bloco-confianca-ia")?.remove();

            const mapaNivel = {
                alta: "Alta",
                media: "Média",
                baixa: "Baixa",
            };

            const nivelGeral = String(payload?.geral || "media").trim().toLowerCase();
            const nivelGeralValido = mapaNivel[nivelGeral] ? nivelGeral : "media";

            const secoes = Array.isArray(payload?.secoes)
                ? payload.secoes.filter((item) => item && typeof item === "object").slice(0, 6)
                : [];

            const pontos = Array.isArray(payload?.pontos_validacao_humana)
                ? payload.pontos_validacao_humana
                    .map((item) => String(item || "").trim())
                    .filter(Boolean)
                    .slice(0, 4)
                : [];

            const bloco = document.createElement("div");
            bloco.className = "bloco-confianca-ia";
            bloco.setAttribute("role", "status");
            bloco.setAttribute("aria-live", "polite");

            const secoesHtml = secoes
                .map((secao) => {
                    const titulo = escapeHTML(String(secao?.titulo || "Seção"));
                    const nivel = String(secao?.confianca || "media").trim().toLowerCase();
                    const nivelValido = mapaNivel[nivel] ? nivel : "media";

                    return `
                        <li>
                            <span class="confianca-secao-titulo">${titulo}</span>
                            <span class="confianca-badge badge-${nivelValido}">${mapaNivel[nivelValido]}</span>
                        </li>
                    `;
                })
                .join("");

            const pontosHtml = pontos
                .map((item) => `<li>${escapeHTML(item)}</li>`)
                .join("");

            bloco.innerHTML = `
                <div class="confianca-cabecalho">
                    <span class="material-symbols-rounded" aria-hidden="true">verified_user</span>
                    <strong>Confiança da IA</strong>
                    <span class="confianca-badge badge-${nivelGeralValido}">${mapaNivel[nivelGeralValido]}</span>
                </div>
                ${
                    secoesHtml
                        ? `<ul class="lista-confianca-secoes">${secoesHtml}</ul>`
                        : ""
                }
                ${
                    pontosHtml
                        ? `
                            <div class="confianca-validacao-humana">
                                <span class="titulo-validacao">Validação humana recomendada:</span>
                                <ul>${pontosHtml}</ul>
                            </div>
                        `
                        : ""
                }
            `;

            corpo.appendChild(bloco);
            rolarParaBaixo();
        }

        // =========================================================
        // CITAÇÕES NORMATIVAS
        // =========================================================

        function renderizarCitacoes(elementoIA, citacoes) {
            if (!elementoIA || !Array.isArray(citacoes) || citacoes.length === 0) return;

            const corpo = elementoIA.querySelector(".corpo-texto");
            if (!corpo) return;

            corpo.querySelector(".bloco-citacoes")?.remove();

            const citacoesValidas = citacoes.filter((citacao) => citacao && typeof citacao === "object");
            if (!citacoesValidas.length) return;

            const bloco = document.createElement("div");
            bloco.className = "bloco-citacoes";
            bloco.setAttribute("role", "complementary");
            bloco.setAttribute("aria-label", "Referências normativas citadas");

            const titulo = document.createElement("div");
            titulo.className = "citacoes-titulo";
            titulo.innerHTML = `
                <span class="material-symbols-rounded" aria-hidden="true">menu_book</span>
                Referências Normativas
            `;
            bloco.appendChild(titulo);

            const lista = document.createElement("ul");
            lista.className = "citacoes-lista";

            citacoesValidas.forEach((citacao) => {
                const norma = escapeHTML(textoSeguro(citacao.norma || citacao.referencia || ""));
                const artigo = escapeHTML(textoSeguro(citacao.artigo || ""));
                const trecho = escapeHTML(textoSeguro(citacao.trecho || ""));

                if (!norma && !trecho) return;

                const item = document.createElement("li");
                item.className = "citacao-item";
                item.innerHTML = `
                    <span class="citacao-norma">${norma}${artigo ? ` — ${artigo}` : ""}</span>
                    ${trecho ? `<span class="citacao-trecho">${trecho}</span>` : ""}
                `;

                lista.appendChild(item);
            });

            if (!lista.children.length) return;

            bloco.appendChild(lista);
            corpo.appendChild(bloco);
            rolarParaBaixo();
        }

        // =========================================================
        // SYNTAX HIGHLIGHT SIMPLES
        // =========================================================

        function aplicarSyntaxHighlight(code, lang) {
            const aliases = {
                js: "javascript",
                ts: "typescript",
                py: "python",
                sh: "bash",
                shell: "bash",
                yml: "yaml",
            };

            const linguagemBruta = String(lang || "").toLowerCase();
            const linguagem = aliases[linguagemBruta] || linguagemBruta;

            const suportadas = new Set([
                "javascript",
                "typescript",
                "python",
                "bash",
                "json",
                "css",
                "sql",
                "yaml",
            ]);

            let texto = escapeHTML(textoSeguro(code));
            if (!suportadas.has(linguagem)) return texto;

            const stashes = [];

            function guardar(valor) {
                const idx = stashes.push(valor) - 1;
                return `__TOKEN_${idx}__`;
            }

            if (["javascript", "typescript", "css"].includes(linguagem)) {
                texto = texto.replace(/\/\/[^\n]*/g, (m) =>
                    guardar(`<span class="sh-comment">${m}</span>`)
                );
            }

            if (["python", "bash", "yaml"].includes(linguagem)) {
                texto = texto.replace(/#[^\n]*/g, (m) =>
                    guardar(`<span class="sh-comment">${m}</span>`)
                );
            }

            texto = texto.replace(
                /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)/g,
                (m) => guardar(`<span class="sh-string">${m}</span>`)
            );

            const palavrasPorLinguagem = {
                javascript: [
                    "const", "let", "var", "function", "return", "if", "else", "for", "while",
                    "switch", "case", "break", "continue", "class", "extends", "new", "this",
                    "super", "typeof", "instanceof", "in", "of", "import", "export", "from",
                    "default", "async", "await", "try", "catch", "finally", "throw", "null",
                    "undefined", "true", "false"
                ],
                typescript: [
                    "const", "let", "var", "function", "return", "if", "else", "for", "while",
                    "switch", "case", "break", "continue", "class", "extends", "new", "this",
                    "super", "typeof", "instanceof", "in", "of", "import", "export", "from",
                    "default", "async", "await", "try", "catch", "finally", "throw", "null",
                    "undefined", "true", "false", "interface", "type", "implements", "public",
                    "private", "protected", "readonly"
                ],
                python: [
                    "def", "return", "if", "elif", "else", "for", "while", "break", "continue",
                    "class", "import", "from", "as", "try", "except", "finally", "raise",
                    "with", "lambda", "pass", "yield", "None", "True", "False", "and", "or",
                    "not", "in", "is", "async", "await"
                ],
                bash: [
                    "if", "then", "else", "fi", "for", "do", "done", "case", "esac",
                    "function", "return", "in"
                ],
                json: ["true", "false", "null"],
                css: ["display", "position", "color", "background", "border", "padding", "margin", "font-size", "grid", "flex"],
                sql: [
                    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "DELETE",
                    "CREATE", "ALTER", "DROP", "TABLE", "JOIN", "LEFT", "RIGHT", "INNER",
                    "OUTER", "ON", "GROUP", "ORDER", "BY", "HAVING", "LIMIT", "AS",
                    "DISTINCT", "SET"
                ],
                yaml: ["true", "false", "null"],
            };

            const palavras = palavrasPorLinguagem[linguagem] || [];

            if (palavras.length) {
                const kw = palavras
                    .map((palavra) => palavra.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
                    .join("|");

                const flags = linguagem === "sql" ? "gi" : "g";
                texto = texto.replace(
                    new RegExp(`\\b(${kw})\\b`, flags),
                    '<span class="sh-keyword">$1</span>'
                );
            }

            texto = texto.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="sh-number">$1</span>');
            texto = texto.replace(/__TOKEN_(\d+)__/g, (_, idx) => stashes[Number(idx)] || "");

            return texto;
        }

        // =========================================================
        // MARKDOWN
        // =========================================================

        function formatarInline(texto) {
            if (!texto) return "";

            let html = texto;

            html = html.replace(/`([^`\n]+)`/g, "<code>$1</code>");
            html = html.replace(/\*\*([^\n*][\s\S]*?[^\n*]?)\*\*/g, "<strong>$1</strong>");
            html = html.replace(/(^|[^\*])\*([^\n*][\s\S]*?[^\n*]?)\*(?!\*)/g, "$1<em>$2</em>");

            return destacarMencoes(html);
        }

        function parseTabela(linhas, inicio) {
            const linhaCabecalho = linhas[inicio] ?? "";
            const linhaSeparadora = linhas[inicio + 1] ?? "";

            if (!/^\s*\|.*\|\s*$/.test(linhaCabecalho)) return null;
            if (!/^\s*\|?[\s:\-|\t]+\|?\s*$/.test(linhaSeparadora)) return null;

            function dividirLinha(linha) {
                const t = linha.trim().replace(/^\|/, "").replace(/\|$/, "");
                return t.split("|").map((c) => c.trim());
            }

            const cabecalho = dividirLinha(linhaCabecalho);
            if (!cabecalho.length) return null;

            const corpo = [];
            let i = inicio + 2;

            while (i < linhas.length && /^\s*\|.*\|\s*$/.test(linhas[i])) {
                corpo.push(dividirLinha(linhas[i]));
                i++;
            }

            const htmlCab = cabecalho.map((c) => `<th>${formatarInline(c)}</th>`).join("");
            const htmlBody = corpo
                .map((colunas) => {
                    const tds = colunas.map((c) => `<td>${formatarInline(c)}</td>`).join("");
                    return `<tr>${tds}</tr>`;
                })
                .join("");

            return {
                html: `<table><thead><tr>${htmlCab}</tr></thead><tbody>${htmlBody}</tbody></table>`,
                nextIndex: i - 1,
            };
        }

        function renderizarMarkdown(texto) {
            if (!texto) return "";

            const blocosCodigo = [];
            let base = textoSeguro(texto).replace(/\r\n/g, "\n");

            base = base.replace(/```([a-zA-Z0-9_+-]+)?\n?([\s\S]*?)```/g, (_, lang, code) => {
                const idx = blocosCodigo.push({
                    lang: textoSeguro(lang || "").trim(),
                    code: textoSeguro(code || "").replace(/\n$/, ""),
                }) - 1;

                return `__BLOCO_CODIGO_${idx}__`;
            });

            base = escapeHTML(base);

            const linhas = base.split("\n");
            const saida = [];

            let emUl = false;
            let emOl = false;

            function fecharListas() {
                if (emUl) {
                    saida.push("</ul>");
                    emUl = false;
                }

                if (emOl) {
                    saida.push("</ol>");
                    emOl = false;
                }
            }

            for (let i = 0; i < linhas.length; i++) {
                const linha = linhas[i];
                const trim = linha.trim();

                if (/^__BLOCO_CODIGO_\d+__$/.test(trim)) {
                    fecharListas();
                    saida.push(trim);
                    continue;
                }

                const tabela = parseTabela(linhas, i);
                if (tabela) {
                    fecharListas();
                    saida.push(tabela.html);
                    i = tabela.nextIndex;
                    continue;
                }

                const h3 = linha.match(/^###\s+(.*)$/);
                if (h3) {
                    fecharListas();
                    saida.push(`<h3>${formatarInline(h3[1])}</h3>`);
                    continue;
                }

                const h2 = linha.match(/^##\s+(.*)$/);
                if (h2) {
                    fecharListas();
                    saida.push(`<h2>${formatarInline(h2[1])}</h2>`);
                    continue;
                }

                const h1 = linha.match(/^#\s+(.*)$/);
                if (h1) {
                    fecharListas();
                    saida.push(`<h1>${formatarInline(h1[1])}</h1>`);
                    continue;
                }

                const itemUl = linha.match(/^\s*[-*]\s+(.*)$/);
                if (itemUl) {
                    if (emOl) {
                        saida.push("</ol>");
                        emOl = false;
                    }

                    if (!emUl) {
                        saida.push("<ul>");
                        emUl = true;
                    }

                    saida.push(`<li>${formatarInline(itemUl[1])}</li>`);
                    continue;
                }

                const itemOl = linha.match(/^\s*\d+\.\s+(.*)$/);
                if (itemOl) {
                    if (emUl) {
                        saida.push("</ul>");
                        emUl = false;
                    }

                    if (!emOl) {
                        saida.push("<ol>");
                        emOl = true;
                    }

                    saida.push(`<li>${formatarInline(itemOl[1])}</li>`);
                    continue;
                }

                if (!trim) {
                    fecharListas();

                    if (saida.length && saida[saida.length - 1] !== "<br>") {
                        saida.push("<br>");
                    }

                    continue;
                }

                fecharListas();
                saida.push(`${formatarInline(linha)}<br>`);
            }

            fecharListas();

            let html = saida.join("");
            html = html.replace(/(?:<br>){3,}/g, "<br><br>");

            html = html.replace(/__BLOCO_CODIGO_(\d+)__/g, (_, idx) => {
                const bloco = blocosCodigo[Number(idx)];
                if (!bloco) return "";

                const labelLang = bloco.lang || "código";
                const codigoDestacado = aplicarSyntaxHighlight(bloco.code, bloco.lang);

                return `
                    <div class="bloco-codigo" data-bloco-codigo="${idx}">
                        <div class="bloco-codigo-header">
                            <span class="bloco-codigo-lang">${escapeHTML(labelLang)}</span>
                            <button
                                class="btn-copiar-codigo"
                                type="button"
                                data-codigo-idx="${idx}"
                                aria-label="Copiar código"
                                title="Copiar código"
                            >
                                <span class="material-symbols-rounded" aria-hidden="true">content_copy</span>
                                Copiar
                            </button>
                        </div>
                        <pre><code>${codigoDestacado}</code></pre>
                    </div>
                `;
            });

            return html.replace(/^(<br>)+|(<br>)+$/g, "");
        }

        // =========================================================
        // EVENTOS INTERNOS DO RENDER
        // =========================================================

        async function onAreaMensagensClick(event) {
            const btn = event.target.closest(".btn-copiar-codigo");
            if (!btn) return;

            const bloco = btn.closest(".bloco-codigo");
            if (!bloco) return;

            const code = bloco.querySelector("pre code")?.textContent ?? "";
            if (!code) return;

            try {
                await copiarTexto(code);

                btn.classList.add("copiado");
                btn.setAttribute("aria-label", "Código copiado");
                btn.setAttribute("title", "Código copiado");
                btn.innerHTML = `
                    <span class="material-symbols-rounded" aria-hidden="true">check</span>
                    Copiado
                `;

                setTimeout(() => {
                    btn.classList.remove("copiado");
                    btn.setAttribute("aria-label", "Copiar código");
                    btn.setAttribute("title", "Copiar código");
                    btn.innerHTML = `
                        <span class="material-symbols-rounded" aria-hidden="true">content_copy</span>
                        Copiar
                    `;
                }, 2000);
            } catch (_) {
                mostrarToast("Não foi possível copiar o código.", "aviso");
            }
        }

        if (PERF?.enabled) {
            const adicionarMensagemInspetorOriginal = adicionarMensagemInspetor;
            adicionarMensagemInspetor = function adicionarMensagemInspetorComPerf(...args) {
                return PERF.measureSync(
                    "chat_render.adicionarMensagemInspetor",
                    () => adicionarMensagemInspetorOriginal.apply(this, args),
                    {
                        category: "render",
                        detail: {
                            textoTamanho: String(args[0] || "").length,
                            possuiImagem: !!args[1],
                            possuiDocumento: !!args[2],
                        },
                    }
                );
            };

            const criarBolhaIAOriginal = criarBolhaIA;
            criarBolhaIA = function criarBolhaIAComPerf(...args) {
                return PERF.measureSync(
                    "chat_render.criarBolhaIA",
                    () => criarBolhaIAOriginal.apply(this, args),
                    {
                        category: "render",
                        detail: {
                            modo: String(args[0] || "detalhado"),
                        },
                    }
                );
            };

            const adicionarMensagemNaUIOriginal = adicionarMensagemNaUI;
            adicionarMensagemNaUI = function adicionarMensagemNaUIComPerf(...args) {
                return PERF.measureSync(
                    "chat_render.adicionarMensagemNaUI",
                    () => adicionarMensagemNaUIOriginal.apply(this, args),
                    {
                        category: "render",
                        detail: {
                            remetente: String(args[0] || ""),
                            tipo: String(args[2] || ""),
                        },
                    }
                );
            };

            const mostrarAcoesPosRespostaOriginal = mostrarAcoesPosResposta;
            mostrarAcoesPosResposta = function mostrarAcoesPosRespostaComPerf(...args) {
                return PERF.measureSync(
                    "chat_render.mostrarAcoesPosResposta",
                    () => mostrarAcoesPosRespostaOriginal.apply(this, args),
                    {
                        category: "render",
                        detail: {
                            textoTamanho: String(args[1] || "").length,
                        },
                    }
                );
            };

            const renderizarConfiancaIAOriginal = renderizarConfiancaIA;
            renderizarConfiancaIA = function renderizarConfiancaIAComPerf(...args) {
                return PERF.measureSync(
                    "chat_render.renderizarConfiancaIA",
                    () => renderizarConfiancaIAOriginal.apply(this, args),
                    {
                        category: "render",
                    }
                );
            };

            const renderizarCitacoesOriginal = renderizarCitacoes;
            renderizarCitacoes = function renderizarCitacoesComPerf(...args) {
                const citacoes = Array.isArray(args[1]) ? args[1] : [];
                return PERF.measureSync(
                    "chat_render.renderizarCitacoes",
                    () => renderizarCitacoesOriginal.apply(this, args),
                    {
                        category: "render",
                        detail: {
                            total: citacoes.length,
                        },
                    }
                );
            };
        }

        areaMensagens.__tarielRenderClickHandler = onAreaMensagensClick;
        areaMensagens.addEventListener("click", onAreaMensagensClick);

        window.adicionarMensagemNaUI = adicionarMensagemNaUI;
        window.adicionarMensagemInspetor = adicionarMensagemInspetor;

        return {
            adicionarMensagemInspetor,
            criarBolhaIA,
            adicionarMensagemNaUI,
            mostrarAcoesPosResposta,
            renderizarAnexosMensagem,
            renderizarConfiancaIA,
            renderizarCitacoes,
            renderizarMarkdown,
            obterHistoricoSeguro: historicoSeguro,

            destruir() {
                areaMensagens.removeEventListener("click", onAreaMensagensClick);

                if (areaMensagens.__tarielRenderClickHandler === onAreaMensagensClick) {
                    delete areaMensagens.__tarielRenderClickHandler;
                }

                if (window.adicionarMensagemNaUI === adicionarMensagemNaUI) {
                    try {
                        delete window.adicionarMensagemNaUI;
                    } catch (_) {
                        window.adicionarMensagemNaUI = undefined;
                    }
                }

                if (window.adicionarMensagemInspetor === adicionarMensagemInspetor) {
                    try {
                        delete window.adicionarMensagemInspetor;
                    } catch (_) {
                        window.adicionarMensagemInspetor = undefined;
                    }
                }
            },
        };
    };
})();
