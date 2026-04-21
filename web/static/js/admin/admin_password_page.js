        (() => {
            "use strict";

            document.querySelectorAll("[data-password-toggle]").forEach((botao) => {
                const targetId = botao.getAttribute("data-password-target");
                const input = targetId ? document.getElementById(targetId) : null;
                if (!input) return;

                botao.addEventListener("click", () => {
                    const visivel = input.type === "text";
                    input.type = visivel ? "password" : "text";
                    botao.setAttribute("aria-pressed", String(!visivel));
                    const icone = botao.querySelector(".material-symbols-rounded");
                    if (icone) icone.textContent = visivel ? "visibility" : "visibility_off";
                    input.focus();
                });
            });

            document.querySelectorAll("[data-auth-form]").forEach((form) => {
                form.addEventListener("submit", () => {
                    const botao = form.querySelector(".auth-button");
                    if (!botao) return;
                    botao.disabled = true;
                    botao.innerHTML = "<span>Atualizando...</span>";
                });
            });
        })();
