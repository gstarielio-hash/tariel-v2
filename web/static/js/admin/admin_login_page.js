(function () {
    "use strict";

    const senhaInput = document.getElementById("senha");
    const msgSenha = document.getElementById("msg-senha");
    const emailInput = document.getElementById("email");
    const msgEmail = document.getElementById("msg-email");
    const avisoRate = document.getElementById("aviso-rate");
    const btnLogin = document.getElementById("btn-login");
    const form = document.getElementById("form-login");
    const authError = document.getElementById("auth-error-admin");
    const LIMITE_TENTATIVAS = 3;
    const BLOQUEIO_MS = 30_000;
    const CHAVE_LS = "tariel_login_tentativas";
    let timerBloqueio = null;

    function setMsg(el, text, tipo) {
        el.textContent = text || "";
        el.className = text ? `auth-inline-message ${tipo}` : "auth-inline-message";
    }

    function validarEmail(v) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim());
    }

    function carregarEstado() {
        try {
            return JSON.parse(localStorage.getItem(CHAVE_LS)) || { count: 0, desde: 0 };
        } catch {
            return { count: 0, desde: 0 };
        }
    }

    function salvarEstado(estado) {
        localStorage.setItem(CHAVE_LS, JSON.stringify(estado));
    }

    function ativarBloqueio(estado) {
        btnLogin.disabled = true;
        clearInterval(timerBloqueio);
        timerBloqueio = setInterval(() => {
            const restante = BLOQUEIO_MS - (Date.now() - estado.desde);
            if (restante <= 0) {
                clearInterval(timerBloqueio);
                btnLogin.disabled = false;
                avisoRate.classList.remove("is-visible");
                avisoRate.textContent = "";
                salvarEstado({ count: 0, desde: 0 });
                btnLogin.textContent = "Acessar";
                return;
            }
            const seg = Math.ceil(restante / 1000);
            avisoRate.classList.add("is-visible");
            avisoRate.textContent = `Muitas tentativas. Aguarde ${seg}s para tentar novamente.`;
            btnLogin.textContent = `Bloqueado (${seg}s)`;
        }, 500);
    }

    function verificarBloqueio() {
        const estado = carregarEstado();
        if (estado.count >= LIMITE_TENTATIVAS) {
            const restante = BLOQUEIO_MS - (Date.now() - estado.desde);
            if (restante > 0) {
                ativarBloqueio(estado);
                return true;
            }
            salvarEstado({ count: 0, desde: 0 });
        }
        return false;
    }

    function classificarErro(texto) {
        const normalizado = String(texto || "").toLowerCase();
        if (!normalizado) return "";
        if (normalizado.includes("mfa") || normalizado.includes("totp")) return "auth-error--info";
        if (normalizado.includes("bloquead")) return "auth-error--warning";
        if (normalizado.includes("autorizad")) return "auth-error--warning";
        return "";
    }

    senhaInput?.addEventListener("keyup", (e) => {
        if (e.getModifierState && e.getModifierState("CapsLock")) {
            setMsg(msgSenha, "Caps Lock ativado.", "aviso");
        } else if (msgSenha.textContent.includes("Caps")) {
            setMsg(msgSenha, "", "");
        }
    });

    emailInput?.addEventListener("blur", () => {
        if (!emailInput.value.trim()) {
            setMsg(msgEmail, "Informe o e-mail corporativo.", "erro");
        } else if (!validarEmail(emailInput.value)) {
            setMsg(msgEmail, "Formato de e-mail inválido.", "erro");
        } else {
            setMsg(msgEmail, "", "");
        }
    });

    senhaInput?.addEventListener("blur", () => {
        if (senhaInput.value.length < 8) {
            setMsg(msgSenha, "A senha deve ter ao menos 8 caracteres.", "erro");
        } else if (!msgSenha.textContent.includes("Caps")) {
            setMsg(msgSenha, "", "");
        }
    });

    verificarBloqueio();

    form?.addEventListener("submit", (e) => {
        if (verificarBloqueio()) {
            e.preventDefault();
            return;
        }

        let ok = true;
        if (!validarEmail(emailInput.value)) {
            setMsg(msgEmail, "Informe um e-mail válido.", "erro");
            ok = false;
        }
        if (senhaInput.value.length < 8) {
            setMsg(msgSenha, "Senha inválida.", "erro");
            ok = false;
        }
        if (!ok) {
            e.preventDefault();
            return;
        }

        const estado = carregarEstado();
        estado.count += 1;
        if (estado.count === 1) {
            estado.desde = Date.now();
        }
        salvarEstado(estado);

        btnLogin.disabled = true;
        btnLogin.textContent = "Verificando...";
    });

    if (document.body.dataset.loginOk === "1") {
        salvarEstado({ count: 0, desde: 0 });
    }

    if (authError) {
        const categoria = classificarErro(authError.textContent);
        if (categoria) {
            authError.classList.add(categoria);
        }
    }
})();
