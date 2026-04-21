(function () {
    "use strict";

    const STORAGE_KEY = "tariel-admin-settings-active-section";

    const removerAlerta = (el) => {
        if (!el || el.dataset.removendo === "true") return;
        el.dataset.removendo = "true";
        el.classList.add("saindo");
        window.setTimeout(() => el.remove(), 250);
    };

    document.querySelectorAll(".alert").forEach((el) => {
        el.querySelector(".alert-fechar")?.addEventListener("click", () => removerAlerta(el));
        window.setTimeout(() => removerAlerta(el), 6000);
    });

    const tabs = Array.from(document.querySelectorAll("[data-config-tab]"));
    const panels = Array.from(document.querySelectorAll("[data-config-panel]"));
    const select = document.querySelector("[data-config-select]");

    if (!tabs.length || !panels.length) {
        return;
    }

    const panelByKey = new Map(panels.map((panel) => [panel.dataset.configPanel, panel]));
    const tabByKey = new Map(tabs.map((tab) => [tab.dataset.configTab, tab]));

    const normalizarChave = (value) => {
        const key = String(value || "")
            .trim()
            .replace(/^#/, "")
            .replace(/^config-/, "");
        return panelByKey.has(key) ? key : null;
    };

    const salvarChave = (key) => {
        try {
            window.sessionStorage.setItem(STORAGE_KEY, key);
        } catch (_error) {
            // Ignora indisponibilidade de storage no navegador.
        }
    };

    const restaurarChave = () => {
        try {
            return normalizarChave(window.sessionStorage.getItem(STORAGE_KEY));
        } catch (_error) {
            return null;
        }
    };

    const updateHash = (key) => {
        const url = new URL(window.location.href);
        url.hash = key ? `config-${key}` : "";
        window.history.replaceState({}, "", url.toString());
    };

    const ativarSecao = (key, options = {}) => {
        const {
            persist = true,
            reflectHash = true,
            focusTab = false,
        } = options;
        const normalized = normalizarChave(key) || tabs[0].dataset.configTab;

        tabs.forEach((tab) => {
            const active = tab.dataset.configTab === normalized;
            tab.classList.toggle("is-active", active);
            tab.setAttribute("aria-selected", active ? "true" : "false");
            tab.setAttribute("tabindex", active ? "0" : "-1");
            if (active && focusTab) {
                tab.focus();
            }
        });

        panels.forEach((panel) => {
            panel.hidden = panel.dataset.configPanel !== normalized;
        });

        if (select) {
            select.value = normalized;
        }

        if (persist) {
            salvarChave(normalized);
        }

        if (reflectHash) {
            updateHash(normalized);
        }
    };

    const proximaChave = (currentKey, direction) => {
        const keys = tabs.map((tab) => tab.dataset.configTab);
        const currentIndex = Math.max(keys.indexOf(currentKey), 0);
        if (direction === "home") return keys[0];
        if (direction === "end") return keys[keys.length - 1];
        const nextIndex = (currentIndex + direction + keys.length) % keys.length;
        return keys[nextIndex];
    };

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            ativarSecao(tab.dataset.configTab, { focusTab: false });
        });

        tab.addEventListener("keydown", (event) => {
            let targetKey = null;
            if (event.key === "ArrowRight" || event.key === "ArrowDown") {
                targetKey = proximaChave(tab.dataset.configTab, 1);
            } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
                targetKey = proximaChave(tab.dataset.configTab, -1);
            } else if (event.key === "Home") {
                targetKey = proximaChave(tab.dataset.configTab, "home");
            } else if (event.key === "End") {
                targetKey = proximaChave(tab.dataset.configTab, "end");
            }

            if (!targetKey) return;
            event.preventDefault();
            ativarSecao(targetKey, { focusTab: true });
        });
    });

    select?.addEventListener("change", (event) => {
        ativarSecao(event.target.value, { focusTab: false });
    });

    window.addEventListener("hashchange", () => {
        const hashed = normalizarChave(window.location.hash);
        if (hashed) {
            ativarSecao(hashed, { persist: true, reflectHash: false, focusTab: false });
        }
    });

    const initialKey =
        normalizarChave(window.location.hash) ||
        restaurarChave() ||
        tabs[0].dataset.configTab;
    ativarSecao(initialKey, {
        persist: true,
        reflectHash: Boolean(normalizarChave(window.location.hash)),
        focusTab: false,
    });
})();
