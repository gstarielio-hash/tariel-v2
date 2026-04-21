(function () {
    "use strict";

    if (window.TarielClientePortalChat) return;

    window.TarielClientePortalChat = function createTarielClientePortalChat(config = {}) {
        const state = config.state || {};
        const documentRef = config.documentRef || document;
        const $ = typeof config.getById === "function"
            ? config.getById
            : (id) => documentRef.getElementById(id);
        const helpers = config.helpers || {};
        const filters = config.filters || {};

        const createSurface = window.TarielClientePortalChatSurface;
        const createPage = window.TarielClienteChatPage;

        if (typeof createSurface !== "function") {
            throw new Error("TarielClientePortalChatSurface indisponivel.");
        }
        if (typeof createPage !== "function") {
            throw new Error("TarielClienteChatPage indisponivel.");
        }

        const surfaceModule = createSurface({
            ...config,
            documentRef,
            filters,
            getById: $,
            helpers,
            state,
        });

        return createPage({
            ...config,
            documentRef,
            filters,
            getById: $,
            helpers,
            state,
            surfaceModule,
        });
    };
})();
