// =========================================================================
// TARIEL.IA — UI.JS (VERSÃO AJUSTADA)
// Orquestração: Sidebar, Login/Logout, Notificações, Modo Foco e Suporte
// =========================================================================

(function () {
    "use strict";

    const EM_PRODUCAO =
        window.location.hostname !== "localhost" &&
        window.location.hostname !== "127.0.0.1";

    const MARCADOR_ENG = "eng ";
    const KEY_MODO_FOCO = "tariel_modo_foco";
    const KEY_MODO_RESPOSTA = "tariel_modo_resposta";
    const BREAKPOINT_LAYOUT_INSPETOR_COMPACTO = 1199;
    const TOGGLE_COLOR = "#F47B20";
    const SELETOR_ACAO_HOME = '[data-action="go-home"]';
    const DESTINO_HOME_PADRAO = "/app/?home=1";
    const _toastsAtivos = new Map();
    let _dockRapidoSyncRaf = 0;
    let _dockRapidoObserver = null;
    const PERF = window.TarielPerf || window.TarielCore?.TarielPerf || null;

    PERF?.noteModule?.("shared/ui.js", {
        readyState: document.readyState,
    });

    function log(nivel, ...args) {
        if (EM_PRODUCAO && nivel !== "error") return;
        try {
            (console?.[nivel] ?? console?.log)?.call(console, "[Tariel UI]", ...args);
        } catch (_) { }
    }

    function qs(sel, root = document) {
        return root.querySelector(sel);
    }

    function qsa(sel, root = document) {
        return Array.from(root.querySelectorAll(sel));
    }

    function escapeHTML(str) {
        if (str === null || str === undefined) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#x27;")
            .replace(/\//g, "&#x2F;");
    }

    function obterCampoMensagem() {
        return document.getElementById("campo-mensagem");
    }

    function campoPodeReceberFoco(campo) {
        return !!(
            campo instanceof HTMLElement &&
            !campo.disabled &&
            !campo.hidden &&
            !campo.closest("[hidden], [inert]") &&
            campo.getClientRects().length > 0
        );
    }

    function focarCampoMensagemSemScroll() {
        const campo = obterCampoMensagem();
        if (!campoPodeReceberFoco(campo)) return;

        try {
            campo.focus({ preventScroll: true });
        } catch (_) {
            campo.focus();
        }
    }

    function normalizarScrollShell() {
        if (!document.getElementById("painel-chat")) return;

        const container = document.querySelector(".container-app");
        if (!container) return;

        if (container.scrollTop !== 0) {
            container.scrollTop = 0;
        }
    }

    function ehElementoVisivel(node) {
        return !!(
            node instanceof Element &&
            !node.hidden &&
            !node.closest("[hidden], [inert]") &&
            node.getClientRects().length > 0
        );
    }

    function obterDestinoAcaoHome(alvo = null) {
        const destino = String(
            alvo?.dataset?.homeDestino ||
            alvo?.getAttribute?.("href") ||
            DESTINO_HOME_PADRAO
        ).trim();

        return destino || DESTINO_HOME_PADRAO;
    }

    function solicitarNavegacaoHome({
        origem = "ui",
        destino = DESTINO_HOME_PADRAO,
        preservarContexto = true,
    } = {}) {
        const destinoFinal = String(destino || DESTINO_HOME_PADRAO).trim() || DESTINO_HOME_PADRAO;
        const evento = new CustomEvent("tariel:navigate-home", {
            detail: {
                origem,
                destino: destinoFinal,
                preservarContexto: preservarContexto !== false,
            },
            bubbles: true,
            cancelable: true,
        });

        const tratado = !document.dispatchEvent(evento);
        if (!tratado) {
            window.location.assign(destinoFinal);
        }

        return tratado;
    }

    function obterModoSalvo() {
        try {
            return localStorage.getItem(KEY_MODO_RESPOSTA) || "detalhado";
        } catch (_) {
            return "detalhado";
        }
    }

    function salvarModo(modo) {
        try {
            localStorage.setItem(KEY_MODO_RESPOSTA, modo);
        } catch (_) { }
    }

    function obterModoFocoSalvo() {
        try {
            return localStorage.getItem(KEY_MODO_FOCO) === "true";
        } catch (_) {
            return false;
        }
    }

    function salvarModoFoco(ativo) {
        try {
            localStorage.setItem(KEY_MODO_FOCO, String(ativo));
        } catch (_) { }
    }

    function obterSidebar() {
        return document.getElementById("barra-historico");
    }

    function obterOverlaySidebar() {
        return document.querySelector(".overlay-sidebar");
    }

    function obterContextoTelaInspetor() {
        const body = document.body;
        const screen = String(body?.dataset?.inspectorScreen || "").trim();
        const baseScreen = String(body?.dataset?.inspectorBaseScreen || screen).trim();
        const overlayOwner = String(
            body?.dataset?.inspectorOverlayOwner ||
            body?.dataset?.overlayOwner ||
            ""
        ).trim();

        return { screen, baseScreen, overlayOwner };
    }

    function layoutInspectorCompacto() {
        return window.innerWidth <= BREAKPOINT_LAYOUT_INSPETOR_COMPACTO;
    }

    function dockRapidoPodeAparecer() {
        const visibilidadeDeclarada = String(document.body?.dataset?.inspectorQuickDock || "").trim();
        if (visibilidadeDeclarada === "visible") return true;
        if (visibilidadeDeclarada === "hidden") return false;

        const { baseScreen, overlayOwner } = obterContextoTelaInspetor();
        return layoutInspectorCompacto() && !overlayOwner && (
            baseScreen === "inspection_record" ||
            baseScreen === "inspection_conversation"
        );
    }

    function sidebarPodeAbrirNoContextoAtual() {
        const { overlayOwner } = obterContextoTelaInspetor();
        return !overlayOwner;
    }

    function isMobile() {
        return window.innerWidth <= 768;
    }

    function sidebarEstaAberta(sidebar) {
        if (!sidebar) return false;

        if (isMobile()) {
            return sidebar.classList.contains("aberto") || sidebar.classList.contains("aberta");
        }

        return !sidebar.classList.contains("oculta");
    }

    function definirInteratividadeElemento(elemento, ativo) {
        if (!elemento) return;

        const habilitado = !!ativo;
        try {
            elemento.inert = !habilitado;
        } catch (_) {
            if (habilitado) {
                elemento.removeAttribute("inert");
            } else {
                elemento.setAttribute("inert", "");
            }
        }
    }

    function definirEstadoSidebar(abrir) {
        const btnMenu = document.getElementById("btn-menu");
        const sidebar = obterSidebar();
        const overlay = obterOverlaySidebar();
        const abrirFinal = !!abrir && sidebarPodeAbrirNoContextoAtual();

        if (!sidebar) return;

        if (isMobile()) {
            document.body.classList.remove("sidebar-colapsada");
            sidebar.classList.toggle("aberto", abrirFinal);
            sidebar.classList.toggle("aberta", abrirFinal);
            sidebar.classList.remove("oculta");
            sidebar.hidden = !abrirFinal;
            definirInteratividadeElemento(sidebar, abrirFinal);

            overlay?.classList.toggle("ativo", abrirFinal);
            overlay?.setAttribute("aria-hidden", String(!abrirFinal));
            if (overlay) {
                overlay.hidden = !abrirFinal;
                definirInteratividadeElemento(overlay, abrirFinal);
            }
            document.body.classList.toggle("sidebar-aberta", abrirFinal);
            document.body.style.overflow = abrirFinal ? "hidden" : "";
            sidebar.setAttribute("aria-hidden", String(!abrirFinal));
            btnMenu?.setAttribute("aria-expanded", String(abrirFinal));
            return;
        }

        document.body.classList.toggle("sidebar-colapsada", !abrirFinal);
        sidebar.classList.remove("aberto", "aberta");
        sidebar.classList.toggle("oculta", !abrirFinal);
        sidebar.setAttribute("aria-hidden", String(!abrirFinal));
        sidebar.hidden = false;
        definirInteratividadeElemento(sidebar, abrirFinal);
        btnMenu?.setAttribute("aria-expanded", String(abrirFinal));

        overlay?.classList.remove("ativo");
        overlay?.setAttribute("aria-hidden", "true");
        if (overlay) {
            overlay.hidden = true;
            definirInteratividadeElemento(overlay, false);
        }
        document.body.classList.remove("sidebar-aberta");
        document.body.style.overflow = "";
    }

    function marcarBotaoPressionado(botao, ativo, { color = "", tituloAtivo = "", tituloInativo = "" } = {}) {
        if (!botao) return;
        botao.setAttribute("aria-pressed", String(!!ativo));
        botao.classList.toggle("ativo", !!ativo);
        botao.style.color = ativo && color ? color : "";
        const titulo = ativo ? tituloAtivo : tituloInativo;
        if (titulo) {
            botao.title = titulo;
            botao.setAttribute("aria-label", titulo);
        }
    }

    function definirLoadingBotao(botao, ativo, {
        iconIdle = "",
        labelIdle = "",
        iconLoading = "sync",
        labelLoading = "Processando..."
    } = {}) {
        if (!botao) return;

        if (!botao.dataset.labelIdle && labelIdle) botao.dataset.labelIdle = labelIdle;
        if (!botao.dataset.iconIdle && iconIdle) botao.dataset.iconIdle = iconIdle;

        const finalLabelIdle = botao.dataset.labelIdle || labelIdle || botao.textContent.trim();
        const finalIconIdle = botao.dataset.iconIdle || iconIdle || "";

        botao.disabled = !!ativo;
        botao.setAttribute("aria-busy", String(!!ativo));

        if (ativo) {
            botao.innerHTML = `
                <span class="material-symbols-rounded" aria-hidden="true">${iconLoading}</span>
                <span>${escapeHTML(labelLoading)}</span>
            `;
            return;
        }

        if (finalIconIdle) {
            botao.innerHTML = `
                <span class="material-symbols-rounded" aria-hidden="true">${finalIconIdle}</span>
                <span>${escapeHTML(finalLabelIdle)}</span>
            `;
        } else {
            botao.textContent = finalLabelIdle;
        }
    }

    function fecharSidebarSilencioso() {
        definirEstadoSidebar(false);
    }

    function sincronizarSidebarOverlayPorContexto() {
        if (!sidebarPodeAbrirNoContextoAtual()) {
            fecharSidebarSilencioso();
        }
    }

    function abrirFecharSidebar() {
        const sidebar = obterSidebar();
        if (!sidebar) return;
        if (!sidebarEstaAberta(sidebar) && !sidebarPodeAbrirNoContextoAtual()) {
            return;
        }
        definirEstadoSidebar(!sidebarEstaAberta(sidebar));
    }

    function aplicarModoFoco(ativo) {
        const btnToggle = document.getElementById("btn-toggle-ui");
        const iconeToggle =
            document.getElementById("icone-toggle-ui") ||
            btnToggle?.querySelector(".material-symbols-rounded");

        document.body.classList.toggle("modo-foco", !!ativo);

        if (btnToggle) {
            const txt = ativo ? "Mostrar interface" : "Ocultar interface";
            btnToggle.setAttribute("aria-pressed", String(!!ativo));
            btnToggle.dataset.tooltip = txt;
            btnToggle.title = txt;
        }

        if (iconeToggle) {
            iconeToggle.textContent = ativo ? "left_panel_open" : "left_panel_close";
        }

        salvarModoFoco(!!ativo);
        document.dispatchEvent(new CustomEvent("tariel:focus-mode-changed", {
            detail: { ativo: !!ativo },
            bubbles: true,
        }));
        window.requestAnimationFrame(normalizarScrollShell);
    }

    function homeRapidoEstaDisponivel() {
        const visibilidadeDeclarada = document.body?.dataset?.homeActionVisible;
        if (visibilidadeDeclarada === "true") return true;
        if (visibilidadeDeclarada === "false") return false;

        const { baseScreen, overlayOwner } = obterContextoTelaInspetor();
        if (!overlayOwner && document.body.classList.contains("modo-foco") && baseScreen === "assistant_landing") {
            return true;
        }

        return qsa(SELETOR_ACAO_HOME).some((node) =>
            node.id !== "btn-shell-home" && ehElementoVisivel(node)
        );
    }

    function perfilRapidoEstaDisponivel() {
        const { baseScreen, overlayOwner } = obterContextoTelaInspetor();
        if (overlayOwner) return false;

        return baseScreen === "assistant_landing" || baseScreen === "inspection_workspace";
    }

    function sincronizarDockRapido() {
        const btnHome = document.getElementById("btn-shell-home");
        const btnPerfil = document.getElementById("btn-shell-profile");
        const dockPermitido = dockRapidoPodeAparecer();

        if (btnHome) {
            btnHome.hidden = !dockPermitido || !homeRapidoEstaDisponivel();
        }

        if (btnPerfil) {
            btnPerfil.hidden = !perfilRapidoEstaDisponivel() || !document.getElementById("btn-abrir-perfil-chat");
        }
    }

    function agendarSincronizacaoDockRapido() {
        if (_dockRapidoSyncRaf) return;

        _dockRapidoSyncRaf = window.requestAnimationFrame(() => {
            _dockRapidoSyncRaf = 0;
            sincronizarDockRapido();
        });
    }

    function inicializarDockRapido() {
        const btnHome = document.getElementById("btn-shell-home");
        const btnPerfil = document.getElementById("btn-shell-profile");

        sincronizarDockRapido();
        agendarSincronizacaoDockRapido();

        if (document.documentElement.dataset.uiDockRapidoWired !== "true") {
            document.documentElement.dataset.uiDockRapidoWired = "true";
            window.addEventListener("pageshow", sincronizarDockRapido);
            window.addEventListener("resize", agendarSincronizacaoDockRapido);

            [
                "tariel:laudo-criado",
                "tariel:relatorio-iniciado",
                "tariel:relatorio-finalizado",
                "tariel:cancelar-relatorio",
                "tariel:estado-relatorio",
                "tariel:screen-synced",
            ].forEach((nomeEvento) => {
                document.addEventListener(nomeEvento, agendarSincronizacaoDockRapido);
            });
        }

        if (!_dockRapidoObserver && document.body && typeof MutationObserver === "function") {
            _dockRapidoObserver = new MutationObserver((mutations) => {
                if (mutations.some((mutation) => mutation.target === document.body)) {
                    agendarSincronizacaoDockRapido();
                }
            });
            _dockRapidoObserver.__tarielPerfLabel = "ui.dockRapido";

            _dockRapidoObserver.observe(document.body, {
                attributes: true,
                attributeFilter: [
                    "data-home-action-visible",
                    "data-inspector-screen",
                    "data-inspector-base-screen",
                    "data-inspector-overlay-owner",
                ],
            });
        }

        if (btnHome && btnHome.dataset.uiWired !== "true") {
            btnHome.dataset.uiWired = "true";
            btnHome.addEventListener("click", (event) => {
                event.preventDefault();
                solicitarNavegacaoHome({
                    origem: "shell-quick-action",
                    destino: obterDestinoAcaoHome(btnHome),
                });
            });
        }

        if (btnPerfil && btnPerfil.dataset.uiWired !== "true") {
            btnPerfil.dataset.uiWired = "true";
            btnPerfil.addEventListener("click", () => {
                const alvo = document.getElementById("btn-abrir-perfil-chat");
                if (typeof alvo?.click === "function") {
                    alvo.click();
                }
            });
        }
    }

    function obterModo() {
        return obterModoSalvo();
    }

    function atualizarBotoesModo(modoFinal) {
        qsa(".chip-modo-resposta").forEach((chip) => {
            const ativo = chip.dataset.modo === modoFinal;
            chip.classList.toggle("ativo", ativo);
            chip.setAttribute("aria-pressed", String(ativo));
        });
    }

    function definirModo(modo) {
        const modoFinal = String(modo || "detalhado");
        salvarModo(modoFinal);
        atualizarBotoesModo(modoFinal);

        document.dispatchEvent(
            new CustomEvent("tariel:modo-alterado", {
                detail: { modo: modoFinal },
                bubbles: true,
            })
        );

        return modoFinal;
    }

    function normalizarTextoEngenharia(texto) {
        const base = String(texto || "").trimStart();
        if (!base) return MARCADOR_ENG.trimEnd();
        if (/^eng\b/i.test(base)) return base;
        if (/^@eng\b/i.test(base)) return base.replace(/^@eng\b/i, "eng");
        if (/^@insp\b/i.test(base)) return base.replace(/^@insp\b/i, "eng");
        return `${MARCADOR_ENG}${base}`.trimEnd();
    }

    function possuiMesaWidgetDedicado() {
        const permitidoDataset = String(document.body?.dataset?.mesaWidgetVisible || "").trim();
        const { baseScreen, overlayOwner } = obterContextoTelaInspetor();
        const permitidoNoContexto = permitidoDataset
            ? permitidoDataset === "true"
            : (!overlayOwner && (
                baseScreen === "inspection_record" ||
                baseScreen === "inspection_conversation" ||
                baseScreen === "inspection_mesa"
            ));

        return Boolean(
            permitidoNoContexto &&
            document.getElementById("painel-mesa-widget") &&
            document.getElementById("mesa-widget-input")
        );
    }

    function abrirMesaWidgetDedicado(texto = "") {
        if (!possuiMesaWidgetDedicado()) return false;

        const painel = document.getElementById("painel-mesa-widget");
        const botaoToggle = document.getElementById("btn-mesa-widget-toggle");
        const campoMesa = document.getElementById("mesa-widget-input");

        const aberto =
            botaoToggle?.getAttribute("aria-expanded") === "true" ||
            painel?.classList.contains("aberto") ||
            (painel ? !painel.hidden : false);

        if (!aberto && botaoToggle) {
            botaoToggle.click();
        }

        const sugestao = String(texto || "")
            .replace(/^@?(insp|inspetor|eng|engenharia|revisor|mesa|avaliador|avaliacao)\b\s*[:\-]?\s*/i, "")
            .trim();

        if (campoMesa) {
            if (sugestao && !String(campoMesa.value || "").trim()) {
                campoMesa.value = sugestao;
                campoMesa.dispatchEvent(new Event("input", { bubbles: true }));
            }

            campoMesa.focus();
            if (typeof campoMesa.setSelectionRange === "function") {
                const fim = campoMesa.value.length;
                campoMesa.setSelectionRange(fim, fim);
            }
        }

        if (isMobile()) {
            fecharSidebarSilencioso();
        }

        return true;
    }

    function atualizarEstadoToggleMesa() {
        const campo = obterCampoMensagem();
        const btnToggle = document.getElementById("btn-toggle-humano");
        if (!campo) return;

        const widgetDedicadoAtivo = possuiMesaWidgetDedicado();
        const ativo = widgetDedicadoAtivo ? false : /^eng\b/i.test(campo.value);
        const tituloAtivo = widgetDedicadoAtivo
            ? "Chat da mesa aberto"
            : "Desativar conversa com a mesa";
        const tituloInativo = widgetDedicadoAtivo
            ? "Abrir chat da mesa avaliadora"
            : "Falar com a mesa";

        marcarBotaoPressionado(btnToggle, ativo, {
            color: TOGGLE_COLOR,
            tituloAtivo,
            tituloInativo
        });

    }

    function ativarMesaAvaliadora(texto = "") {
        if (abrirMesaWidgetDedicado(texto)) {
            atualizarEstadoToggleMesa();
            return true;
        }

        const campo = obterCampoMensagem();
        if (!campo) return false;

        campo.value = normalizarTextoEngenharia(texto || campo.value || "");
        campo.dispatchEvent(new Event("input", { bubbles: true }));
        campo.focus();
        campo.setSelectionRange(campo.value.length, campo.value.length);

        atualizarEstadoToggleMesa();

        if (isMobile()) {
            fecharSidebarSilencioso();
        }

        return true;
    }

    function alternarMesaAvaliadora() {
        if (abrirMesaWidgetDedicado()) {
            atualizarEstadoToggleMesa();
            return;
        }

        const campo = obterCampoMensagem();
        if (!campo) return;

        if (/^eng\b/i.test(campo.value)) {
            campo.value = campo.value.replace(/^eng\b\s*/i, "");
        } else {
            campo.value = normalizarTextoEngenharia(campo.value);
        }

        campo.dispatchEvent(new Event("input", { bubbles: true }));
        campo.focus();
        campo.setSelectionRange(campo.value.length, campo.value.length);
        atualizarEstadoToggleMesa();

        if (isMobile()) {
            fecharSidebarSilencioso();
        }
    }

    const TIPOS_TOAST = {
        info: { icon: "info" },
        sucesso: { icon: "check_circle" },
        erro: { icon: "error" },
        aviso: { icon: "warning" },
    };

    function exibirToast(mensagem, tipo = "info", duracaoMs = 3000) {
        const config = TIPOS_TOAST[tipo] ?? TIPOS_TOAST.info;
        const texto = String(mensagem ?? "");
        const chave = `${tipo}:${texto}`;

        if (_toastsAtivos.has(chave)) return;
        _toastsAtivos.set(chave, true);

        let container = document.getElementById("toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "toast-container";
            document.body.appendChild(container);
        }

        const toast = document.createElement("div");
        toast.className = `toast-notificacao toast-${tipo}`;
        toast.setAttribute("role", "status");
        toast.setAttribute("aria-live", "polite");
        toast.innerHTML = `
            <span class="material-symbols-rounded" aria-hidden="true">${config.icon}</span>
            <span>${escapeHTML(texto)}</span>
        `;

        container.appendChild(toast);

        requestAnimationFrame(() => {
            toast.style.opacity = "1";
            toast.style.transform = "translateY(0)";
        });

        let removido = false;

        const remover = () => {
            if (removido) return;
            removido = true;

            toast.style.opacity = "0";
            toast.style.transform = "translateY(8px)";

            setTimeout(() => {
                toast.remove();
                _toastsAtivos.delete(chave);
            }, 300);
        };

        toast.addEventListener("click", remover);
        setTimeout(remover, Math.max(1000, duracaoMs));
    }

    async function executarLogout() {
        if (!confirm("Deseja realmente sair do sistema Tariel.ia?")) return;

        try {
            if (navigator.serviceWorker?.controller) {
                navigator.serviceWorker.controller.postMessage({ tipo: "LIMPAR_CACHE" });
            }
            window.location.replace("/app/logout");
        } catch (_) {
            window.location.replace("/admin/login");
        }
    }

    function inicializarSuporteEngenharia() {
        const campo = obterCampoMensagem();
        const btnToggle = document.getElementById("btn-toggle-humano");

        if (btnToggle && btnToggle.dataset.uiWired !== "true") {
            btnToggle.dataset.uiWired = "true";
            btnToggle.addEventListener("click", alternarMesaAvaliadora);
        }

        campo?.addEventListener("input", atualizarEstadoToggleMesa);

        document.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.altKey && e.key.toLowerCase() === "i") {
                e.preventDefault();
                alternarMesaAvaliadora();
            }
        });

        atualizarEstadoToggleMesa();
    }

    function inicializarMenuLateral() {
        const btnMenu = document.getElementById("btn-menu");
        const sidebar = obterSidebar();
        const overlay = obterOverlaySidebar();

        if (!btnMenu || !sidebar || !overlay) return;

        // Estado inicial correto por viewport:
        // desktop = lateral visível; mobile = lateral fechada.
        definirEstadoSidebar(isMobile() ? false : !sidebar.classList.contains("oculta"));

        if (btnMenu.dataset.uiWired !== "true") {
            btnMenu.dataset.uiWired = "true";
            btnMenu.addEventListener("click", abrirFecharSidebar);
        }

        if (overlay.dataset.uiWired !== "true") {
            overlay.dataset.uiWired = "true";
            overlay.addEventListener("click", fecharSidebarSilencioso);
        }

        document.addEventListener("tariel:screen-synced", sincronizarSidebarOverlayPorContexto);
        sincronizarSidebarOverlayPorContexto();

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && sidebarEstaAberta(sidebar)) {
                fecharSidebarSilencioso();
            }
        });

        let mobileAnterior = isMobile();
        window.addEventListener("resize", () => {
            const mobileAtual = isMobile();
            if (mobileAtual === mobileAnterior) return;

            mobileAnterior = mobileAtual;

            if (mobileAtual) {
                definirEstadoSidebar(false);
                return;
            }

            definirEstadoSidebar(true);
        });
    }

    function inicializarModoFoco() {
        const btnToggle = document.getElementById("btn-toggle-ui");
        if (!btnToggle) return;

        aplicarModoFoco(obterModoFocoSalvo());

        if (btnToggle.dataset.uiWired !== "true") {
            btnToggle.dataset.uiWired = "true";
            btnToggle.addEventListener("click", () => {
                const isAtivo = document.body.classList.contains("modo-foco");
                aplicarModoFoco(!isAtivo);
            });
        }

        document.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "\\") {
                e.preventDefault();
                btnToggle.click();
            }
        });
    }

    function inicializarLogoutForm() {
        qsa(".btn-logout").forEach((btn) => {
            if (btn.dataset.uiWired === "true") return;
            btn.dataset.uiWired = "true";

            btn.addEventListener("click", (e) => {
                e.preventDefault();
                executarLogout();
            });
        });
    }

    function inicializarLoginForm() {
        const btnEntrar = document.getElementById("btn-entrar");
        const form = btnEntrar?.closest("form");
        if (!btnEntrar || !form) return;

        definirLoadingBotao(btnEntrar, false, {
            iconIdle: "login",
            labelIdle: btnEntrar.textContent.trim() || "Entrar"
        });

        if (form.dataset.uiWired === "true") return;
        form.dataset.uiWired = "true";

        form.addEventListener("submit", () => {
            definirLoadingBotao(btnEntrar, true, {
                iconIdle: "login",
                labelIdle: btnEntrar.textContent.trim() || "Entrar",
                iconLoading: "sync",
                labelLoading: "Autenticando..."
            });
        });
    }

    function inicializarPins() {
        // Mantido por compatibilidade.
    }

    function inicializarChipModo() {
        const chips = qsa(".chip-modo-resposta");
        if (!chips.length) return;

        const modoSalvo = obterModo();
        let encontrouModoSalvo = false;

        chips.forEach((chip) => {
            const ativo = chip.dataset.modo === modoSalvo;
            chip.classList.toggle("ativo", ativo);
            chip.setAttribute("aria-pressed", String(ativo));
            if (ativo) encontrouModoSalvo = true;

            if (chip.dataset.uiWired === "true") return;
            chip.dataset.uiWired = "true";

            chip.addEventListener("click", () => {
                if (chip.classList.contains("chip-bloqueado-plano")) {
                    exibirToast("Modo disponível no plano Ilimitado.", "aviso");
                    return;
                }

                definirModo(chip.dataset.modo || "detalhado");
            });
        });

        if (!encontrouModoSalvo) {
            const primeiroDisponivel = chips.find((chip) => !chip.classList.contains("chip-bloqueado-plano"));
            if (primeiroDisponivel) {
                definirModo(primeiroDisponivel.dataset.modo || "detalhado");
            }
        }
    }

    function inicializarChipsSugestao() {
        const container = document.getElementById("sugestoes-rapidas");
        const setorSelect = document.getElementById("setor-industrial");

        const renderizar = () => {
            if (typeof window.TarielUI?.renderizarSugestoes === "function") {
                window.TarielUI.renderizarSugestoes(container);
            }
        };

        setorSelect?.addEventListener("change", renderizar);
        renderizar();
    }

    function inicializarAcaoHome() {
        if (document.documentElement.dataset.uiHomeActionWired === "true") return;
        document.documentElement.dataset.uiHomeActionWired = "true";

        document.addEventListener("click", (event) => {
            const alvo = event.target?.closest?.(SELETOR_ACAO_HOME);
            if (!alvo) return;
            if (alvo.id === "btn-shell-home") return;

            if (
                event.defaultPrevented ||
                event.button !== 0 ||
                event.metaKey ||
                event.ctrlKey ||
                event.shiftKey ||
                event.altKey
            ) {
                return;
            }

            if (alvo.tagName === "A") {
                const href = String(alvo.getAttribute("href") || "").trim();
                const target = String(alvo.getAttribute("target") || "").trim().toLowerCase();
                if (!href || href.startsWith("#") || target === "_blank" || alvo.hasAttribute("download")) {
                    return;
                }
            }

            event.preventDefault();
            solicitarNavegacaoHome({
                origem: alvo.id || alvo.dataset.homeSource || "ui-action",
                destino: obterDestinoAcaoHome(alvo),
            });
        });
    }

    function inicializar() {
        if (document.documentElement.dataset.uiEvents === "wired") return;
        document.documentElement.dataset.uiEvents = "wired";

        log("info", "Iniciando módulos de interface...");

        inicializarMenuLateral();
        inicializarModoFoco();
        inicializarDockRapido();
        inicializarAcaoHome();
        inicializarLoginForm();
        inicializarLogoutForm();
        inicializarPins();
        inicializarChipModo();
        inicializarChipsSugestao();
        inicializarSuporteEngenharia();

        focarCampoMensagemSemScroll();
        window.requestAnimationFrame(normalizarScrollShell);
    }

    if (PERF?.enabled) {
        const inicializarDockRapidoOriginal = inicializarDockRapido;
        inicializarDockRapido = function inicializarDockRapidoComPerf(...args) {
            return PERF.measureSync(
                "ui.inicializarDockRapido",
                () => inicializarDockRapidoOriginal.apply(this, args),
                {
                    category: "boot",
                    detail: {
                        readyState: document.readyState,
                    },
                }
            );
        };

        const inicializarOriginal = inicializar;
        inicializar = function inicializarComPerf(...args) {
            return PERF.measureSync(
                "ui.inicializar",
                () => {
                    const resultado = inicializarOriginal.apply(this, args);
                    PERF.snapshotDOM?.("ui:initialized");
                    return resultado;
                },
                {
                    category: "boot",
                    detail: {
                        readyState: document.readyState,
                    },
                }
            );
        };
    }

    window.TarielUI = {
        exibirToast,
        escapeHTML,
        modoFoco: aplicarModoFoco,
        fecharSidebar: fecharSidebarSilencioso,
        logout: executarLogout,
        obterModo,
        definirModo,
        solicitarNavegacaoHome,
        ativarMesaAvaliadora,
        alternarMesaAvaliadora,
        obterMarcadorMesa: () => MARCADOR_ENG,
    };

    window.exibirToast = exibirToast;
    window.fecharSidebar = fecharSidebarSilencioso;

    document.addEventListener("DOMContentLoaded", inicializar);
})();
