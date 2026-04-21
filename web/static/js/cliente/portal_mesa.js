(function () {
    "use strict";

    if (window.TarielClientePortalMesa) return;

    window.TarielClientePortalMesa = function createTarielClientePortalMesa(config = {}) {
        const state = config.state || {};
        const documentRef = config.documentRef || document;
        const $ = typeof config.getById === "function"
            ? config.getById
            : (id) => documentRef.getElementById(id);
        const helpers = config.helpers || {};
        const filters = config.filters || {};

        const createSurface = window.TarielClientePortalMesaSurface;
        const createPage = window.TarielClienteMesaPage;

        if (typeof createSurface !== "function") {
            throw new Error("TarielClientePortalMesaSurface indisponivel.");
        }
        if (typeof createPage !== "function") {
            throw new Error("TarielClienteMesaPage indisponivel.");
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
