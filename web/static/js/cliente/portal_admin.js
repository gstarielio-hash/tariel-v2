(function () {
    "use strict";

    if (window.TarielClientePortalAdmin) return;

    window.TarielClientePortalAdmin = function createTarielClientePortalAdmin(config = {}) {
        const state = config.state || {};
        const documentRef = config.documentRef || document;
        const windowRef = config.windowRef || window;
        const $ = typeof config.getById === "function"
            ? config.getById
            : (id) => documentRef.getElementById(id);
        const helpers = config.helpers || {};

        const createSurface = window.TarielClientePortalAdminSurface;
        const createPage = window.TarielClientePainelPage;

        if (typeof createSurface !== "function") {
            throw new Error("TarielClientePortalAdminSurface indisponivel.");
        }
        if (typeof createPage !== "function") {
            throw new Error("TarielClientePainelPage indisponivel.");
        }

        const surfaceModule = createSurface({
            ...config,
            documentRef,
            getById: $,
            helpers,
            state,
            windowRef,
        });

        return createPage({
            ...config,
            documentRef,
            getById: $,
            helpers,
            state,
            surfaceModule,
            windowRef,
        });
    };
})();
