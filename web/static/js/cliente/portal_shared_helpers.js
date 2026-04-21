(function () {
    "use strict";

    if (window.TarielClientePortalSharedHelpers) return;

    window.TarielClientePortalSharedHelpers = function createTarielClientePortalSharedHelpers(config = {}) {
        const state = config.state || {};
        const documentRef = config.documentRef || document;
        const $ = typeof config.getById === "function"
            ? config.getById
            : (id) => documentRef.getElementById(id);
        const helpers = config.helpers || {};

        const escapeAttr = typeof helpers.escapeAttr === "function" ? helpers.escapeAttr : (valor) => String(valor ?? "");
        const escapeHtml = typeof helpers.escapeHtml === "function" ? helpers.escapeHtml : (valor) => String(valor ?? "");
        const formatarBytes = typeof helpers.formatarBytes === "function" ? helpers.formatarBytes : (valor) => String(Number(valor || 0));
        const resumoCanalOperacional = typeof helpers.resumoCanalOperacional === "function" ? helpers.resumoCanalOperacional : (canal) => String(canal ?? "");
        const texto = typeof helpers.texto === "function" ? helpers.texto : (valor) => (valor == null ? "" : String(valor));

        function renderAnexos(anexos) {
            const itens = Array.isArray(anexos) ? anexos : [];
            if (!itens.length) return "";

            return `
                <div class="attachment-list">
                    ${itens.map((anexo) => {
                        const url = texto(anexo.url || "");
                        const link = url
                            ? `<a class="attachment-link" href="${escapeAttr(url)}" target="_blank" rel="noopener noreferrer">Abrir</a>`
                            : `<span class="attachment-link" aria-hidden="true">Disponivel</span>`;

                        return `
                            <div class="attachment-item">
                                <div class="attachment-copy">
                                    <span class="attachment-name">${escapeHtml(anexo.nome || "Anexo")}</span>
                                    <span class="attachment-meta">${escapeHtml(anexo.categoria || "arquivo")} • ${formatarBytes(anexo.tamanho_bytes || 0)}</span>
                                </div>
                                ${link}
                            </div>
                        `;
                    }).join("")}
                </div>
            `;
        }

        function renderAvisosOperacionais(canal, targetId) {
            const container = $(targetId);
            if (!container) return;

            const avisos = (state.bootstrap?.empresa?.avisos_operacionais || []).filter((item) => texto(item?.canal) === canal);
            if (!avisos.length) {
                container.innerHTML = "";
                return;
            }

            container.innerHTML = avisos.map((item) => `
                <div class="context-guidance operational-warning" data-tone="${escapeAttr(item.tone || "aberto")}">
                    <div class="context-guidance-copy">
                        <small>${escapeHtml(resumoCanalOperacional(canal))}</small>
                        <strong>${escapeHtml(item.titulo || item.badge || "Aviso operacional")}</strong>
                        <p>${escapeHtml(item.detalhe || "")}</p>
                        ${item.acao ? `<p>${escapeHtml(item.acao)}</p>` : ""}
                        ${state.bootstrap?.empresa?.plano_sugerido
                            ? `<div class="toolbar-meta"><button class="btn" type="button" data-act="preparar-upgrade" data-origem="${escapeAttr(canal)}">Registrar interesse em ${escapeHtml(state.bootstrap.empresa.plano_sugerido)}</button></div>`
                            : ""}
                    </div>
                    <span class="pill" data-kind="priority" data-status="${escapeAttr(item.tone || "aberto")}">${escapeHtml(item.badge || "Acompanhar")}</span>
                </div>
            `).join("");
        }

        return {
            renderAnexos,
            renderAvisosOperacionais,
        };
    };
})();
