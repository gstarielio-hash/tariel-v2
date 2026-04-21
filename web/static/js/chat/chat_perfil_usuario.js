// ==========================================
// TARIEL CONTROL TOWER — CHAT_PERFIL_USUARIO.JS
// Perfil do inspetor no chat:
// - abrir/fechar modal de perfil
// - atualizar nome, e-mail e telefone
// - upload de foto de perfil
// - sincronizar dados na sidebar
// ==========================================

(function () {
    "use strict";

    if (window.__TARIEL_CHAT_PERFIL_USUARIO_WIRED__) return;
    window.__TARIEL_CHAT_PERFIL_USUARIO_WIRED__ = true;

    const MAX_FOTO_BYTES = 4 * 1024 * 1024;
    const MIMES_FOTO_PERMITIDOS = new Set([
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    ]);

    const el = {
        btnAbrirPerfil: document.getElementById("btn-abrir-perfil-chat"),
        nomeUsuarioCard: document.querySelector("#btn-abrir-perfil-chat .inspetor-user-card__copy strong"),
        papelUsuarioCard: document.querySelector("#btn-abrir-perfil-chat .inspetor-user-card__copy span"),
        avatarUsuarioCard: document.querySelector("#btn-abrir-perfil-chat .inspetor-user-card__avatar"),
        btnShellProfile: document.getElementById("btn-shell-profile"),
        workspaceGreetingNames: Array.from(document.querySelectorAll("[data-workspace-user-greeting-name]")),

        modal: document.getElementById("modal-perfil-chat"),
        btnFecharModal: document.getElementById("btn-fechar-modal-perfil"),
        btnCancelarModal: document.getElementById("btn-cancelar-modal-perfil"),
        btnSalvarPerfil: document.getElementById("btn-salvar-perfil-chat"),
        feedback: document.getElementById("perfil-chat-feedback"),

        avatarPreview: document.getElementById("perfil-avatar-preview"),
        avatarIniciais: document.getElementById("perfil-avatar-iniciais"),
        btnTrocarFoto: document.getElementById("btn-trocar-foto-perfil"),
        inputFoto: document.getElementById("input-foto-perfil"),

        inputNome: document.getElementById("input-perfil-nome"),
        inputEmail: document.getElementById("input-perfil-email"),
        inputTelefone: document.getElementById("input-perfil-telefone"),
    };

    if (!el.btnAbrirPerfil || !el.modal) return;

    const estado = {
        carregandoPerfilRemoto: false,
        salvandoPerfil: false,
        enviandoFoto: false,
        salvamentoPendenteAposFoto: false,
        perfilSujo: false,
        revisaoEdicaoPerfil: 0,
        requisicaoPerfilAtiva: 0,
        ultimoPerfil: null,
        ultimoElementoFocado: null,
        overflowAnteriorBody: "",
    };

    const SELETOR_FOCAVEIS = [
        "button:not([disabled])",
        "[href]",
        "input:not([disabled]):not([type='hidden'])",
        "select:not([disabled])",
        "textarea:not([disabled])",
        "[tabindex]:not([tabindex='-1'])",
    ].join(", ");

    function tokenCsrf() {
        return document.querySelector('meta[name="csrf-token"]')?.content || "";
    }

    function mostrarToast(mensagem, tipo = "info", duracao = 3200) {
        if (typeof window.mostrarToast === "function") {
            window.mostrarToast(mensagem, tipo, duracao);
        }
    }

    function obterIniciais(nome) {
        const texto = String(nome || "").trim();
        if (!texto) return "US";

        const partes = texto.split(/\s+/).filter(Boolean);
        if (!partes.length) return "US";
        if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();

        return `${partes[0][0] || ""}${partes[partes.length - 1][0] || ""}`.toUpperCase() || "US";
    }

    function limparFeedback() {
        if (!el.feedback) return;
        el.feedback.textContent = "";
        el.feedback.classList.remove("erro", "sucesso", "info");
    }

    function definirFeedback(texto, tipo = "info") {
        if (!el.feedback) return;
        el.feedback.textContent = String(texto || "");
        el.feedback.classList.remove("erro", "sucesso", "info");
        el.feedback.classList.add(tipo);
    }

    function operacaoPerfilEmCurso() {
        return !!(
            estado.carregandoPerfilRemoto ||
            estado.salvandoPerfil ||
            estado.enviandoFoto
        );
    }

    function sincronizarBotaoSalvarPerfil() {
        if (!el.btnSalvarPerfil) return;
        el.btnSalvarPerfil.disabled = !!(estado.salvandoPerfil || estado.enviandoFoto);
        el.btnSalvarPerfil.setAttribute("aria-busy", String(!!estado.salvandoPerfil));
    }

    function registrarEdicaoPerfil() {
        estado.perfilSujo = true;
        estado.revisaoEdicaoPerfil += 1;
    }

    function renderAvatar(target, { nome = "", foto = "" } = {}) {
        if (!target) return;

        const nomeLimpo = String(nome || "").trim();
        const fotoLimpa = String(foto || "").trim();
        const iniciais = obterIniciais(nomeLimpo);

        target.dataset.iniciais = iniciais;
        target.classList.toggle("possui-foto", !!fotoLimpa);

        if (fotoLimpa) {
            target.innerHTML = "";
            const img = document.createElement("img");
            img.src = fotoLimpa;
            img.alt = `Foto de perfil de ${nomeLimpo || "usuário"}`;
            img.loading = "lazy";
            img.decoding = "async";
            target.appendChild(img);
            return;
        }

        target.textContent = iniciais;
    }

    function obterPrimeiroNome(nome) {
        const texto = String(nome || "").trim();
        if (!texto) return "Inspetor";
        return texto.split(/\s+/).filter(Boolean)[0] || "Inspetor";
    }

    function obterAvatarShell() {
        if (!el.btnShellProfile) return null;

        let avatar = el.btnShellProfile.querySelector(".shell-profile-avatar");
        if (avatar) return avatar;

        el.btnShellProfile.innerHTML = "";
        avatar = document.createElement("span");
        avatar.className = "shell-profile-avatar";
        avatar.setAttribute("aria-hidden", "true");
        el.btnShellProfile.appendChild(avatar);
        return avatar;
    }

    function aplicarPerfilNoShell(perfil) {
        if (!el.btnShellProfile) return;

        const dados = perfil || {};
        const nome = String(dados.nome_completo || "Usuário").trim() || "Usuário";
        const avatar = obterAvatarShell();

        renderAvatar(avatar, {
            nome,
            foto: dados.foto_perfil_url || "",
        });

        el.btnShellProfile.dataset.tooltip = nome;
        el.btnShellProfile.title = `Perfil de ${nome}`;
        el.btnShellProfile.setAttribute("aria-label", `Abrir perfil de ${nome}`);
    }

    function atualizarSaudacaoWorkspace(nome = "") {
        const primeiroNome = obterPrimeiroNome(nome);

        el.workspaceGreetingNames.forEach((node) => {
            if (!node) return;
            node.textContent = primeiroNome;
        });
    }

    function renderAvatarModal({ nome = "", foto = "" } = {}) {
        if (!el.avatarPreview) return;
        const iniciais = obterIniciais(nome);

        el.avatarPreview.classList.toggle("possui-foto", !!foto);
        el.avatarPreview.innerHTML = "";

        if (foto) {
            const img = document.createElement("img");
            img.src = foto;
            img.alt = `Foto de perfil de ${nome || "usuário"}`;
            img.loading = "lazy";
            img.decoding = "async";
            el.avatarPreview.appendChild(img);
            return;
        }

        const span = document.createElement("span");
        span.id = "perfil-avatar-iniciais";
        span.textContent = iniciais;
        el.avatarPreview.appendChild(span);
    }

    function abrirModalPerfil() {
        limparFeedback();
        estado.ultimoElementoFocado = document.activeElement instanceof HTMLElement
            ? document.activeElement
            : null;
        estado.overflowAnteriorBody = document.body.style.overflow || "";
        el.modal.hidden = false;
        el.modal.setAttribute("aria-hidden", "false");
        el.modal.classList.add("ativo");
        document.body.style.overflow = "hidden";
        window.requestAnimationFrame(() => {
            el.inputNome?.focus();
        });
    }

    function restaurarFocoAnterior() {
        try {
            estado.ultimoElementoFocado?.focus?.();
        } catch (_) {
            // silêncio intencional
        }
    }

    function obterFocaveisModal() {
        if (!el.modal) return [];
        return Array.from(el.modal.querySelectorAll(SELETOR_FOCAVEIS))
            .filter((item) => item instanceof HTMLElement && !item.hidden && item.offsetParent !== null);
    }

    function fecharModalPerfil() {
        el.modal.classList.remove("ativo");
        el.modal.setAttribute("aria-hidden", "true");
        el.modal.hidden = true;
        document.body.style.overflow = estado.overflowAnteriorBody || "";
        estado.overflowAnteriorBody = "";
        limparFeedback();
        el.inputFoto && (el.inputFoto.value = "");
        restaurarFocoAnterior();
    }

    function preencherCampos(perfil) {
        const dados = perfil || {};
        el.inputNome && (el.inputNome.value = String(dados.nome_completo || ""));
        el.inputEmail && (el.inputEmail.value = String(dados.email || ""));
        el.inputTelefone && (el.inputTelefone.value = String(dados.telefone || ""));
        estado.perfilSujo = false;
        estado.revisaoEdicaoPerfil += 1;
        renderAvatarModal({
            nome: dados.nome_completo || "",
            foto: dados.foto_perfil_url || "",
        });
    }

    function perfilDoDataset() {
        return {
            nome_completo: el.btnAbrirPerfil?.dataset?.nome || "",
            email: el.btnAbrirPerfil?.dataset?.email || "",
            telefone: el.btnAbrirPerfil?.dataset?.telefone || "",
            foto_perfil_url: el.btnAbrirPerfil?.dataset?.fotoUrl || "",
        };
    }

    function aplicarPerfilNaSidebar(perfil) {
        const dados = perfil || {};

        if (el.btnAbrirPerfil) {
            el.btnAbrirPerfil.dataset.nome = String(dados.nome_completo || "");
            el.btnAbrirPerfil.dataset.email = String(dados.email || "");
            el.btnAbrirPerfil.dataset.telefone = String(dados.telefone || "");
            el.btnAbrirPerfil.dataset.fotoUrl = String(dados.foto_perfil_url || "");
        }

        if (el.nomeUsuarioCard) {
            el.nomeUsuarioCard.textContent = String(dados.nome_completo || "Usuário");
        }

        if (el.papelUsuarioCard && !String(el.papelUsuarioCard.textContent || "").trim()) {
            el.papelUsuarioCard.textContent = "Inspetor";
        }

        renderAvatar(el.avatarUsuarioCard, {
            nome: dados.nome_completo || "",
            foto: dados.foto_perfil_url || "",
        });

        aplicarPerfilNoShell(dados);
        atualizarSaudacaoWorkspace(dados.nome_completo || "");
    }

    async function carregarPerfilRemoto() {
        try {
            const resposta = await fetch("/app/api/perfil", {
                method: "GET",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (!resposta.ok) return null;
            return await resposta.json();
        } catch (_) {
            return null;
        }
    }

    async function abrirComDadosAtualizados() {
        if (operacaoPerfilEmCurso()) return;

        const requisicaoId = estado.requisicaoPerfilAtiva + 1;
        estado.requisicaoPerfilAtiva = requisicaoId;
        estado.carregandoPerfilRemoto = true;
        sincronizarBotaoSalvarPerfil();
        abrirModalPerfil();
        preencherCampos(perfilDoDataset());
        const revisaoAntesDaCarga = estado.revisaoEdicaoPerfil;
        definirFeedback("Carregando dados...", "info");

        const payload = await carregarPerfilRemoto();
        if (requisicaoId !== estado.requisicaoPerfilAtiva) {
            estado.carregandoPerfilRemoto = false;
            sincronizarBotaoSalvarPerfil();
            return;
        }

        if (payload?.ok && payload?.perfil) {
            estado.ultimoPerfil = payload.perfil;
            const edicaoMudouDuranteCarga =
                estado.perfilSujo ||
                estado.revisaoEdicaoPerfil !== revisaoAntesDaCarga;

            if (!edicaoMudouDuranteCarga) {
                preencherCampos(payload.perfil);
                aplicarPerfilNaSidebar(payload.perfil);
                limparFeedback();
            } else {
                renderAvatarModal({
                    nome: String(el.inputNome?.value || payload.perfil.nome_completo || ""),
                    foto: payload.perfil.foto_perfil_url || "",
                });
                definirFeedback("Dados remotos carregados. Mantendo sua edição atual.", "info");
            }
        } else {
            definirFeedback("Usando dados locais do perfil.", "info");
        }

        estado.carregandoPerfilRemoto = false;
        sincronizarBotaoSalvarPerfil();
    }

    function validarPerfil(dados) {
        const nome = String(dados?.nome_completo || "").trim();
        const email = String(dados?.email || "").trim();

        if (nome.length < 3) {
            return "Informe um nome com pelo menos 3 caracteres.";
        }

        if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            return "Informe um e-mail válido.";
        }

        return "";
    }

    async function salvarPerfil() {
        if (estado.enviandoFoto) {
            estado.salvamentoPendenteAposFoto = true;
            definirFeedback("Finalizando envio da foto e salvando os dados do perfil...", "info");
            return;
        }

        if (estado.salvandoPerfil) return;

        estado.requisicaoPerfilAtiva += 1;

        const payload = {
            nome_completo: String(el.inputNome?.value || "").trim(),
            email: String(el.inputEmail?.value || "").trim(),
            telefone: String(el.inputTelefone?.value || "").trim(),
        };

        const erro = validarPerfil(payload);
        if (erro) {
            definirFeedback(erro, "erro");
            return;
        }

        estado.salvandoPerfil = true;
        sincronizarBotaoSalvarPerfil();
        definirFeedback("Salvando perfil...", "info");

        try {
            const resposta = await fetch("/app/api/perfil", {
                method: "PUT",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRF-Token": tokenCsrf(),
                },
                body: JSON.stringify(payload),
            });

            const dados = await resposta.json().catch(() => ({}));
            if (!resposta.ok || !dados?.ok) {
                throw new Error(String(dados?.erro || dados?.detail || "Falha ao salvar perfil."));
            }

            estado.ultimoPerfil = dados.perfil;
            aplicarPerfilNaSidebar(dados.perfil);
            preencherCampos(dados.perfil);
            definirFeedback("Perfil atualizado com sucesso.", "sucesso");
            mostrarToast("Perfil atualizado.", "sucesso", 2200);
        } catch (erroSalvar) {
            definirFeedback(String(erroSalvar?.message || "Falha ao salvar perfil."), "erro");
        } finally {
            estado.salvandoPerfil = false;
            sincronizarBotaoSalvarPerfil();
        }
    }

    async function enviarFotoPerfil(arquivo) {
        if (!arquivo) return;

        if (!MIMES_FOTO_PERMITIDOS.has(String(arquivo.type || "").toLowerCase())) {
            definirFeedback("Use PNG, JPG ou WebP para foto de perfil.", "erro");
            return;
        }

        if (arquivo.size > MAX_FOTO_BYTES) {
            definirFeedback("A foto deve ter no máximo 4MB.", "erro");
            return;
        }

        const form = new FormData();
        form.append("foto", arquivo);

        estado.enviandoFoto = true;
        sincronizarBotaoSalvarPerfil();
        definirFeedback("Enviando foto...", "info");
        let fotoAtualizada = false;

        try {
            const resposta = await fetch("/app/api/perfil/foto", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRF-Token": tokenCsrf(),
                },
                body: form,
            });

            const dados = await resposta.json().catch(() => ({}));
            if (!resposta.ok || !dados?.ok) {
                throw new Error(String(dados?.erro || dados?.detail || "Falha ao enviar foto."));
            }
            fotoAtualizada = true;

            const perfilAtualizado = {
                ...(estado.ultimoPerfil || perfilDoDataset()),
                foto_perfil_url: dados.foto_perfil_url || "",
            };

            estado.ultimoPerfil = perfilAtualizado;
            aplicarPerfilNaSidebar(perfilAtualizado);
            renderAvatarModal({
                nome: perfilAtualizado.nome_completo || el.inputNome?.value || "",
                foto: perfilAtualizado.foto_perfil_url || "",
            });
            definirFeedback("Foto atualizada com sucesso.", "sucesso");
            mostrarToast("Foto de perfil atualizada.", "sucesso", 2200);
        } catch (erroFoto) {
            estado.salvamentoPendenteAposFoto = false;
            definirFeedback(String(erroFoto?.message || "Falha ao enviar foto."), "erro");
        } finally {
            estado.enviandoFoto = false;
            sincronizarBotaoSalvarPerfil();
            el.inputFoto && (el.inputFoto.value = "");
        }

        if (fotoAtualizada && (estado.salvamentoPendenteAposFoto || estado.perfilSujo)) {
            estado.salvamentoPendenteAposFoto = false;
            definirFeedback("Foto enviada. Salvando dados do perfil...", "info");
            await salvarPerfil();
        }
    }

    function bindEventos() {
        el.btnAbrirPerfil?.addEventListener("click", (event) => {
            event.preventDefault();
            abrirComDadosAtualizados();
        });

        el.btnFecharModal?.addEventListener("click", fecharModalPerfil);
        el.btnCancelarModal?.addEventListener("click", fecharModalPerfil);
        el.btnSalvarPerfil?.addEventListener("click", salvarPerfil);

        [el.inputNome, el.inputEmail, el.inputTelefone].forEach((campo) => {
            campo?.addEventListener("input", () => {
                registrarEdicaoPerfil();
            });
            campo?.addEventListener("change", () => {
                registrarEdicaoPerfil();
            });
        });

        el.btnTrocarFoto?.addEventListener("click", () => {
            el.inputFoto?.click();
        });

        el.inputFoto?.addEventListener("change", () => {
            const arquivo = el.inputFoto?.files?.[0];
            if (!arquivo) return;
            enviarFotoPerfil(arquivo);
        });

        el.modal?.addEventListener("click", (event) => {
            if (event.target === el.modal) {
                fecharModalPerfil();
            }
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && el.modal?.classList.contains("ativo")) {
                event.preventDefault();
                fecharModalPerfil();
            }
        });

        el.modal?.addEventListener("keydown", (event) => {
            if (event.key !== "Tab" || !el.modal?.classList.contains("ativo")) return;

            const focaveis = obterFocaveisModal();
            if (!focaveis.length) return;

            const primeiro = focaveis[0];
            const ultimo = focaveis[focaveis.length - 1];

            if (event.shiftKey && document.activeElement === primeiro) {
                event.preventDefault();
                ultimo.focus();
                return;
            }

            if (!event.shiftKey && document.activeElement === ultimo) {
                event.preventDefault();
                primeiro.focus();
            }
        });
    }

    function boot() {
        const inicial = perfilDoDataset();
        estado.ultimoPerfil = inicial;
        aplicarPerfilNaSidebar(inicial);
        sincronizarBotaoSalvarPerfil();
        bindEventos();
    }

    boot();
})();
