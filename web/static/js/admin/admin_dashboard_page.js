(function () {
    "use strict";

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
})();
