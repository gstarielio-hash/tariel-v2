(function () {
    "use strict";

    const selecionar = (selector, scope = document) => scope.querySelector(selector);
    const selecionarTodos = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

    const parseListaJson = (value, fallback) => {
        try {
            const parsed = JSON.parse(value || "");
            return Array.isArray(parsed) ? parsed : fallback;
        } catch (_error) {
            return fallback;
        }
    };

    const focusFirstInteractive = (container) => {
        if (!container) return;
        const focusable = container.querySelector(
            'input:not([type="hidden"]), select, textarea, button, a[href], [tabindex]:not([tabindex="-1"])',
        );
        focusable?.focus();
    };

    const detectarContextosDaPagina = () => ({
        showroomCatalogo: Boolean(
            document.body?.classList.contains("admin-body--catalog-showroom") ||
                selecionar("[data-catalog-drawer]") ||
                selecionar(".js-open-catalog-preview"),
        ),
        detalheFamilia: Boolean(selecionar('[data-catalog-family-tabs="true"]')),
    });

    const removerAlerta = (alerta) => {
        if (!alerta || alerta.dataset.removendo === "true") return;
        alerta.dataset.removendo = "true";
        alerta.classList.add("saindo");
        window.setTimeout(() => alerta.remove(), 250);
    };

    const inicializarAlertas = () => {
        selecionarTodos(".alert").forEach((alerta) => {
            selecionar(".alert-fechar", alerta)?.addEventListener("click", () => removerAlerta(alerta));
            window.setTimeout(() => removerAlerta(alerta), 6000);
        });
    };

    const ensureDisclosureFromHash = () => {
        const hash = String(window.location.hash || "").replace(/^#/, "");
        if (!hash) return;
        const target = document.getElementById(hash);
        const disclosure = target?.closest("details");
        if (disclosure) {
            disclosure.open = true;
            return;
        }
        if (target?.matches("details")) {
            target.open = true;
        }
    };

    const inicializarTabsCatalogo = () => {
        const tabLinks = selecionarTodos("[data-catalog-tab-link]");
        if (!tabLinks.length) {
            return true;
        }

        const knownKeys = new Set(tabLinks.map((link) => String(link.dataset.catalogTab || "").trim()));
        const normalizarChave = (value) => {
            const key = String(value || "").trim().replace(/^#/, "");
            return knownKeys.has(key) ? key : null;
        };

        const url = new URL(window.location.href);
        const queryTab = normalizarChave(url.searchParams.get("tab"));
        const hashTab = normalizarChave(url.hash);

        if (hashTab && hashTab !== queryTab) {
            url.searchParams.set("tab", hashTab);
            window.location.replace(url.toString());
            return false;
        }

        if (queryTab && hashTab !== queryTab) {
            url.hash = queryTab;
            window.history.replaceState({}, "", url.toString());
        }

        const moveTab = (currentKey, direction) => {
            const keys = tabLinks.map((link) => link.dataset.catalogTab);
            const currentIndex = Math.max(keys.indexOf(currentKey), 0);
            if (direction === "home") return keys[0];
            if (direction === "end") return keys[keys.length - 1];
            return keys[(currentIndex + direction + keys.length) % keys.length];
        };

        tabLinks.forEach((link) => {
            link.addEventListener("keydown", (event) => {
                let targetKey = null;
                if (event.key === "ArrowRight" || event.key === "ArrowDown") targetKey = moveTab(link.dataset.catalogTab, 1);
                if (event.key === "ArrowLeft" || event.key === "ArrowUp") targetKey = moveTab(link.dataset.catalogTab, -1);
                if (event.key === "Home") targetKey = moveTab(link.dataset.catalogTab, "home");
                if (event.key === "End") targetKey = moveTab(link.dataset.catalogTab, "end");
                if (!targetKey) return;
                event.preventDefault();
                const next = tabLinks.find((item) => item.dataset.catalogTab === targetKey);
                if (!next) return;
                next.focus();
                window.location.assign(next.href);
            });
        });

        return true;
    };

    const inicializarDrawers = () => {
        const drawers = selecionarTodos("[data-catalog-drawer]");
        if (!drawers.length) return;

        const closeAllDrawers = () => {
            drawers.forEach((drawer) => {
                drawer.hidden = true;
            });
            document.body.classList.remove("catalog-drawer-open");
        };

        const openDrawer = (name) => {
            const drawer = drawers.find((item) => item.dataset.catalogDrawer === name);
            if (!drawer) return;
            drawers.forEach((item) => {
                item.hidden = item !== drawer;
            });
            drawer.hidden = false;
            document.body.classList.add("catalog-drawer-open");
            focusFirstInteractive(selecionar(".catalog-drawer__panel", drawer));
        };

        selecionarTodos("[data-catalog-open-drawer]").forEach((button) => {
            button.addEventListener("click", () => openDrawer(button.dataset.catalogOpenDrawer));
        });

        selecionarTodos("[data-catalog-close-drawer]").forEach((button) => {
            button.addEventListener("click", () => closeAllDrawers());
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closeAllDrawers();
            }
        });
    };

    const inicializarDisclosureLinks = () => {
        selecionarTodos("[data-catalog-open-disclosure]").forEach((button) => {
            button.addEventListener("click", () => {
                const disclosure = document.getElementById(button.dataset.catalogOpenDisclosure || "");
                if (!disclosure) return;
                disclosure.open = true;
                disclosure.scrollIntoView({ behavior: "smooth", block: "start" });
                focusFirstInteractive(disclosure);
            });
        });

        ensureDisclosureFromHash();
        window.addEventListener("hashchange", ensureDisclosureFromHash);
    };

    const inicializarOverflowMenus = () => {
        document.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) return;
            selecionarTodos(".catalog-overflow[open]").forEach((details) => {
                if (!details.contains(target)) {
                    details.removeAttribute("open");
                }
            });
        });
    };

    const preencherListaDeChips = (host, items) => {
        if (!host) return;
        host.innerHTML = "";
        items.filter(Boolean).forEach((item) => {
            const chip = document.createElement("span");
            chip.textContent = String(item);
            host.appendChild(chip);
        });
    };

    const preencherCardsDeSecao = (host, sections) => {
        if (!host) return;
        host.innerHTML = "";
        sections.forEach((section) => {
            const card = document.createElement("article");
            card.className = "catalog-preview-modal__section-card";

            const head = document.createElement("div");
            head.className = "catalog-preview-modal__status-row";

            const title = document.createElement("strong");
            title.textContent = String(section?.title || "Bloco do laudo");
            head.appendChild(title);

            const status = document.createElement("span");
            const tone = String(section?.status?.tone || "idle").trim() || "idle";
            status.className = `catalog-status catalog-status--${tone}`;
            status.textContent = String(section?.status?.label || "Em montagem");
            head.appendChild(status);

            const body = document.createElement("p");
            const bullets = Array.isArray(section?.bullets) ? section.bullets : [];
            body.textContent = String(bullets[0] || "Esse trecho aparece pronto para orientar o preenchimento.");

            card.appendChild(head);
            card.appendChild(body);
            host.appendChild(card);
        });
    };

    const preencherCamposPreview = (host, fields) => {
        if (!host) return;
        host.innerHTML = "";
        fields.forEach((field) => {
            const chip = document.createElement("span");
            chip.textContent = String(field?.label || field?.slot_id || "Campo guiado");
            host.appendChild(chip);
        });
        if (!host.children.length) {
            const chip = document.createElement("span");
            chip.textContent = "Campos guiados pela estrutura oficial";
            host.appendChild(chip);
        }
    };

    const classesDeTomDoPreview = [
        "catalog-family-card--slate",
        "catalog-family-card--green",
        "catalog-family-card--blue",
        "catalog-family-card--amber",
        "catalog-family-card--red",
        "catalog-family-card--copper",
        "catalog-family-card--orange",
        "catalog-family-card--teal",
        "catalog-family-card--cyan",
        "catalog-family-card--wine",
        "catalog-family-card--yellow",
    ];

    const obterReferenciasDoPreviewModal = (previewModal) => ({
        modal: previewModal,
        dialog: document.getElementById("catalog-preview-dialog"),
        frame: document.getElementById("catalog-preview-frame"),
        loading: document.getElementById("catalog-preview-loading"),
        code: document.getElementById("catalog-preview-code"),
        status: document.getElementById("catalog-preview-status"),
        title: document.getElementById("catalog-preview-title"),
        subtitle: document.getElementById("catalog-preview-subtitle"),
        meta: document.getElementById("catalog-preview-meta"),
        objectiveTitle: document.getElementById("catalog-preview-objective-title"),
        objectiveText: document.getElementById("catalog-preview-objective-text"),
        sections: document.getElementById("catalog-preview-sections"),
        fields: document.getElementById("catalog-preview-fields"),
        features: document.getElementById("catalog-preview-features"),
        note: document.getElementById("catalog-preview-note"),
        openTab: document.getElementById("catalog-preview-open-tab"),
        openFamily: document.getElementById("catalog-preview-open-family"),
    });

    const preencherConteudoDoPreviewModal = (previewRefs, button) => {
        const meta = parseListaJson(button.dataset.previewMeta, []);
        const sections = parseListaJson(button.dataset.previewSections, []);
        const fields = parseListaJson(button.dataset.previewFields, []);
        const features = parseListaJson(button.dataset.previewFeatures, []);
        const toneClass = String(button.dataset.previewTone || "").trim();
        const previewUrl = String(button.dataset.previewUrl || "").trim();
        const familyUrl = String(button.dataset.previewFamilyUrl || "").trim();
        const statusTone = String(button.dataset.previewStatusTone || "idle").trim() || "idle";

        classesDeTomDoPreview.forEach((className) => previewRefs.dialog?.classList.remove(className));
        if (toneClass && previewRefs.dialog) previewRefs.dialog.classList.add(toneClass);

        if (previewRefs.code) previewRefs.code.textContent = String(button.dataset.previewCode || "LAUDO");
        if (previewRefs.title) {
            previewRefs.title.textContent = String(button.dataset.previewTitle || "Prévia oficial do laudo");
        }
        if (previewRefs.subtitle) {
            previewRefs.subtitle.textContent = String(
                button.dataset.previewSubtitle || "Abra o modelo para ver como ele se apresenta antes do preenchimento.",
            );
        }
        if (previewRefs.note) {
            previewRefs.note.textContent = String(button.dataset.previewNote || "Modelo demonstrativo pronto para vitrine.");
        }
        if (previewRefs.objectiveTitle) {
            previewRefs.objectiveTitle.textContent = String(button.dataset.previewObjectiveTitle || "Objetivo do modelo");
        }
        if (previewRefs.objectiveText) {
            previewRefs.objectiveText.textContent = String(
                button.dataset.previewObjectiveText || "Mostrar como este laudo aparece antes do preenchimento final.",
            );
        }
        if (previewRefs.status) {
            previewRefs.status.className = `catalog-status catalog-status--${statusTone}`;
            previewRefs.status.textContent = String(button.dataset.previewStatusLabel || "Em montagem");
        }
        if (previewRefs.openTab) previewRefs.openTab.href = previewUrl || familyUrl || "/admin/catalogo-laudos";
        if (previewRefs.openFamily) previewRefs.openFamily.href = familyUrl || "/admin/catalogo-laudos";

        preencherListaDeChips(previewRefs.meta, meta);
        preencherCardsDeSecao(previewRefs.sections, sections);
        preencherCamposPreview(previewRefs.fields, fields);
        preencherListaDeChips(previewRefs.features, features);

        return previewUrl;
    };

    const carregarFrameDoPreviewModal = (previewRefs, previewUrl, registrarTimeoutLento) => {
        if (previewRefs.loading) {
            previewRefs.loading.hidden = false;
            previewRefs.loading.textContent = "Abrindo a visualização do documento...";
        }
        previewRefs.frame?.removeAttribute("src");

        if (!previewRefs.frame || !previewUrl) {
            if (previewRefs.loading) {
                previewRefs.loading.hidden = false;
                previewRefs.loading.textContent = "Prévia indisponível neste momento.";
            }
            return;
        }

        const separator = previewUrl.includes("?") ? "&" : "?";
        previewRefs.frame.src = `${previewUrl}${separator}visualizacao=modal#toolbar=0&navpanes=0&scrollbar=0&view=FitH`;
        registrarTimeoutLento();
    };

    const inicializarPreviewModal = () => {
        const previewModal = document.getElementById("catalog-preview-modal");
        if (!previewModal) return;

        const previewRefs = obterReferenciasDoPreviewModal(previewModal);
        let lastFocusedElement = null;
        let previewLoadTimer = 0;
        const limparTimeoutDeCarregamento = () => {
            if (!previewLoadTimer) return;
            window.clearTimeout(previewLoadTimer);
            previewLoadTimer = 0;
        };

        const closePreview = () => {
            if (previewRefs.modal.hidden) return;
            previewRefs.modal.hidden = true;
            document.body.classList.remove("catalog-preview-open");
            previewRefs.frame?.removeAttribute("src");
            limparTimeoutDeCarregamento();
            if (previewRefs.loading) previewRefs.loading.hidden = true;
            if (lastFocusedElement instanceof HTMLElement) {
                lastFocusedElement.focus();
            }
        };

        const openPreview = (button) => {
            if (!(button instanceof HTMLElement)) return;
            lastFocusedElement = document.activeElement;
            const previewUrl = preencherConteudoDoPreviewModal(previewRefs, button);

            previewRefs.modal.hidden = false;
            document.body.classList.add("catalog-preview-open");
            selecionar(".catalog-preview-modal__close", previewRefs.modal)?.focus();

            limparTimeoutDeCarregamento();
            carregarFrameDoPreviewModal(previewRefs, previewUrl, () => {
                previewLoadTimer = window.setTimeout(() => {
                    if (previewRefs.loading && !previewRefs.loading.hidden) {
                        previewRefs.loading.textContent = "A visualização está demorando. Se preferir, use 'Abrir em aba'.";
                    }
                }, 4500);
            });
        };

        selecionarTodos(".js-open-catalog-preview").forEach((button) => {
            button.addEventListener("click", () => openPreview(button));
        });

        previewRefs.frame?.addEventListener("load", () => {
            limparTimeoutDeCarregamento();
            if (previewRefs.loading) previewRefs.loading.hidden = true;
        });

        selecionarTodos("[data-catalog-close-preview='true']", previewRefs.modal).forEach((button) => {
            button.addEventListener("click", () => closePreview());
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && !previewRefs.modal.hidden) {
                closePreview();
            }
        });
    };

    const criarBotaoRemover = (onClick) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "catalog-list-editor__remove";
        button.textContent = "Remover";
        button.addEventListener("click", onClick);
        return button;
    };

    const hidratarEditorJson = (hidden) => parseListaJson(hidden?.value, []);

    const criarPersistenciaDoEditorDeStrings = (hidden, rowsHost) => () => {
        const values = selecionarTodos("input[data-string-item]", rowsHost)
            .map((input) => String(input.value || "").trim())
            .filter(Boolean);
        hidden.value = JSON.stringify(values);
    };

    const criarLinhaEditorDeStrings = (editor, value, rowsHost, persist) => {
        const row = document.createElement("div");
        row.className = "catalog-list-editor__row";

        const input = document.createElement("input");
        input.type = "text";
        input.value = value;
        input.placeholder = editor.dataset.placeholder || "";
        input.setAttribute("data-string-item", "true");
        input.addEventListener("input", persist);

        row.appendChild(input);
        row.appendChild(
            criarBotaoRemover(() => {
                row.remove();
                persist();
            }),
        );
        rowsHost.appendChild(row);
        persist();
    };

    const inicializarEditorDeStrings = () => {
        selecionarTodos('[data-list-editor="strings"]').forEach((editor) => {
            const hidden = selecionar('input[type="hidden"]', editor);
            const rowsHost = selecionar("[data-list-editor-rows]", editor);
            const draft = selecionar("[data-list-editor-draft]", editor);
            const addButton = selecionar("[data-list-editor-add]", editor);
            if (!hidden || !rowsHost || !draft || !addButton) return;

            const persist = criarPersistenciaDoEditorDeStrings(hidden, rowsHost);
            hidratarEditorJson(hidden).forEach((value) => criarLinhaEditorDeStrings(editor, String(value || ""), rowsHost, persist));
            addButton.addEventListener("click", () => {
                const value = String(draft.value || "").trim();
                criarLinhaEditorDeStrings(editor, value, rowsHost, persist);
                draft.value = "";
                draft.focus();
            });
            draft.addEventListener("keydown", (event) => {
                if (event.key !== "Enter") return;
                event.preventDefault();
                addButton.click();
            });
            persist();
        });
    };

    const criarPersistenciaDoEditorDeVariantes = (hidden, rowsHost) => () => {
        const values = selecionarTodos(".catalog-variant-editor__row", rowsHost)
            .map((row, index) => ({
                variant_key: String(selecionar('[data-variant-field="variant_key"]', row)?.value || "").trim(),
                nome_exibicao: String(selecionar('[data-variant-field="nome_exibicao"]', row)?.value || "").trim(),
                template_code: String(selecionar('[data-variant-field="template_code"]', row)?.value || "").trim(),
                uso_recomendado: String(selecionar('[data-variant-field="uso_recomendado"]', row)?.value || "").trim(),
                ordem: index + 1,
            }))
            .filter((item) => item.variant_key || item.nome_exibicao || item.template_code || item.uso_recomendado);
        hidden.value = JSON.stringify(values);
    };

    const criarCampoEditorDeVariantes = (placeholder, field, value, persist) => {
        const input = document.createElement("input");
        input.type = "text";
        input.placeholder = placeholder;
        input.value = value;
        input.setAttribute("data-variant-field", field);
        input.addEventListener("input", persist);
        return input;
    };

    const criarLinhaEditorDeVariantes = (value, rowsHost, persist) => {
        const row = document.createElement("div");
        row.className = "catalog-variant-editor__row";
        row.appendChild(criarCampoEditorDeVariantes("codigo da opcao", "variant_key", value.variant_key || "", persist));
        row.appendChild(criarCampoEditorDeVariantes("nome visivel", "nome_exibicao", value.nome_exibicao || "", persist));
        row.appendChild(criarCampoEditorDeVariantes("modelo", "template_code", value.template_code || "", persist));
        row.appendChild(criarCampoEditorDeVariantes("quando usar", "uso_recomendado", value.uso_recomendado || "", persist));
        row.appendChild(
            criarBotaoRemover(() => {
                row.remove();
                persist();
            }),
        );
        rowsHost.appendChild(row);
        persist();
    };

    const inicializarEditorDeVariantes = () => {
        selecionarTodos('[data-list-editor="variants"]').forEach((editor) => {
            const hidden = selecionar('input[type="hidden"]', editor);
            const rowsHost = selecionar("[data-variant-editor-rows]", editor);
            const addButton = selecionar("[data-variant-editor-add]", editor);
            if (!hidden || !rowsHost || !addButton) return;

            const persist = criarPersistenciaDoEditorDeVariantes(hidden, rowsHost);
            hidratarEditorJson(hidden).forEach((value) => criarLinhaEditorDeVariantes(value || {}, rowsHost, persist));
            addButton.addEventListener("click", () => criarLinhaEditorDeVariantes({}, rowsHost, persist));
            persist();
        });
    };

    const niveisDeSeveridadeDeRedFlags = [
        ["low", "Baixa"],
        ["medium", "Média"],
        ["high", "Alta"],
        ["critical", "Crítica"],
    ];

    const criarPersistenciaDoEditorDeRedFlags = (hidden, rowsHost) => () => {
        const values = selecionarTodos(".catalog-red-flag-editor__row", rowsHost)
            .map((row) => ({
                code: String(selecionar('[data-red-flag-field="code"]', row)?.value || "").trim(),
                title: String(selecionar('[data-red-flag-field="title"]', row)?.value || "").trim(),
                severity: String(selecionar('[data-red-flag-field="severity"]', row)?.value || "high").trim(),
                blocking: Boolean(selecionar('[data-red-flag-field="blocking"]', row)?.checked),
                when_missing_required_evidence: Boolean(
                    selecionar('[data-red-flag-field="when_missing_required_evidence"]', row)?.checked,
                ),
                source: String(selecionar('[data-red-flag-field="source"]', row)?.value || "family_policy").trim(),
                message: String(selecionar('[data-red-flag-field="message"]', row)?.value || "").trim(),
            }))
            .filter((item) => item.title || item.message || item.code);
        hidden.value = JSON.stringify(values);
    };

    const criarInputEditorDeRedFlags = (field, placeholder, value, persist) => {
        const input = document.createElement("input");
        input.type = "text";
        input.placeholder = placeholder;
        input.value = value;
        input.setAttribute("data-red-flag-field", field);
        input.addEventListener("input", persist);
        return input;
    };

    const criarSelectEditorDeRedFlags = (field, value, persist) => {
        const select = document.createElement("select");
        select.setAttribute("data-red-flag-field", field);
        niveisDeSeveridadeDeRedFlags.forEach(([optionValue, optionLabel]) => {
            const option = document.createElement("option");
            option.value = optionValue;
            option.textContent = optionLabel;
            if (optionValue === value) option.selected = true;
            select.appendChild(option);
        });
        select.addEventListener("change", persist);
        return select;
    };

    const criarCheckboxEditorDeRedFlags = (field, labelText, checked, persist) => {
        const label = document.createElement("label");
        label.className = "catalog-red-flag-editor__check";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.checked = Boolean(checked);
        input.setAttribute("data-red-flag-field", field);
        input.addEventListener("change", persist);

        const text = document.createElement("span");
        text.textContent = labelText;

        label.appendChild(input);
        label.appendChild(text);
        return label;
    };

    const criarMensagemEditorDeRedFlags = (value, persist) => {
        const textarea = document.createElement("textarea");
        textarea.placeholder = "Mensagem que sera mostrada para a operacao";
        textarea.value = value;
        textarea.setAttribute("data-red-flag-field", "message");
        textarea.rows = 3;
        textarea.addEventListener("input", persist);
        return textarea;
    };

    const criarLinhaEditorDeRedFlags = (value, rowsHost, persist) => {
        const row = document.createElement("div");
        row.className = "catalog-red-flag-editor__row";

        const grid = document.createElement("div");
        grid.className = "catalog-red-flag-editor__grid";
        grid.appendChild(criarInputEditorDeRedFlags("code", "codigo interno", value.code || "", persist));
        grid.appendChild(criarInputEditorDeRedFlags("title", "titulo do alerta", value.title || "", persist));
        grid.appendChild(criarSelectEditorDeRedFlags("severity", value.severity || "high", persist));
        grid.appendChild(criarInputEditorDeRedFlags("source", "origem", value.source || "family_policy", persist));
        grid.appendChild(criarMensagemEditorDeRedFlags(value.message || "", persist));

        const toggles = document.createElement("div");
        toggles.className = "catalog-red-flag-editor__toggles";
        toggles.appendChild(criarCheckboxEditorDeRedFlags("blocking", "Bloqueante", value.blocking !== false, persist));
        toggles.appendChild(
            criarCheckboxEditorDeRedFlags(
                "when_missing_required_evidence",
                "So quando faltar evidencia obrigatoria",
                Boolean(value.when_missing_required_evidence),
                persist,
            ),
        );
        grid.appendChild(toggles);

        row.appendChild(grid);
        row.appendChild(
            criarBotaoRemover(() => {
                row.remove();
                persist();
            }),
        );
        rowsHost.appendChild(row);
        persist();
    };

    const inicializarEditorDeRedFlags = () => {
        selecionarTodos('[data-list-editor="red-flags"]').forEach((editor) => {
            const hidden = selecionar('input[type="hidden"]', editor);
            const rowsHost = selecionar("[data-red-flag-editor-rows]", editor);
            const addButton = selecionar("[data-red-flag-editor-add]", editor);
            if (!hidden || !rowsHost || !addButton) return;

            const persist = criarPersistenciaDoEditorDeRedFlags(hidden, rowsHost);
            hidratarEditorJson(hidden).forEach((value) => criarLinhaEditorDeRedFlags(value || {}, rowsHost, persist));
            addButton.addEventListener("click", () =>
                criarLinhaEditorDeRedFlags({ blocking: true, severity: "high", source: "family_policy" }, rowsHost, persist),
            );
            persist();
        });
    };

    const inicializarPaginaShowroomCatalogo = () => {
        inicializarDrawers();
        inicializarOverflowMenus();
        inicializarPreviewModal();
    };

    const inicializarPaginaDetalheFamilia = () => {
        if (!inicializarTabsCatalogo()) {
            return false;
        }
        inicializarDisclosureLinks();
        inicializarEditorDeStrings();
        inicializarEditorDeVariantes();
        inicializarEditorDeRedFlags();
        return true;
    };

    const init = () => {
        inicializarAlertas();
        const contextos = detectarContextosDaPagina();

        if (contextos.showroomCatalogo) {
            inicializarPaginaShowroomCatalogo();
        }

        if (contextos.detalheFamilia && !inicializarPaginaDetalheFamilia()) {
            return;
        }
    };

    init();
})();
