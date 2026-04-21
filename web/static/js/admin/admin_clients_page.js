        (() => {
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

            const modalBloqueio = document.getElementById("modal-bloqueio-empresa-lista");
            const modalBloqueioMotivo = document.getElementById("modal-bloqueio-empresa-lista-motivo");
            const modalBloqueioErro = document.getElementById("modal-bloqueio-empresa-lista-erro");
            const modalBloqueioCancelar = document.getElementById("modal-bloqueio-empresa-lista-cancelar");
            const modalBloqueioConfirmar = document.getElementById("modal-bloqueio-empresa-lista-confirmar");
            const modalAcao = document.getElementById("admin-action-dialog-lista");
            const modalAcaoTitulo = document.getElementById("admin-action-dialog-lista-title");
            const modalAcaoBody = document.getElementById("admin-action-dialog-lista-body");
            const modalAcaoPayload = document.getElementById("admin-action-dialog-lista-payload");
            const modalAcaoCancelar = document.getElementById("admin-action-dialog-lista-cancelar");
            const modalAcaoConfirmar = document.getElementById("admin-action-dialog-lista-confirmar");
            let formBloqueioPendente = null;
            let confirmarAcaoPendente = null;

            const abrirModalBloqueio = (form) => {
                formBloqueioPendente = form;
                if (modalBloqueioMotivo) {
                    modalBloqueioMotivo.value = "";
                    modalBloqueioMotivo.focus();
                }
                if (modalBloqueioErro) {
                    modalBloqueioErro.textContent = "";
                }
                modalBloqueio?.classList.add("ativo");
            };

            const fecharModalBloqueio = () => {
                modalBloqueio?.classList.remove("ativo");
                formBloqueioPendente = null;
                if (modalBloqueioErro) {
                    modalBloqueioErro.textContent = "";
                }
            };

            const abrirConfirmacao = ({ titulo, corpo, payload = "", confirmarLabel = "Confirmar", onConfirm }) => {
                confirmarAcaoPendente = onConfirm;
                if (modalAcaoTitulo) modalAcaoTitulo.textContent = titulo;
                if (modalAcaoBody) modalAcaoBody.textContent = corpo;
                if (modalAcaoConfirmar) modalAcaoConfirmar.textContent = confirmarLabel;
                if (modalAcaoPayload) {
                    const texto = String(payload || "").trim();
                    modalAcaoPayload.hidden = !texto;
                    modalAcaoPayload.textContent = texto;
                }
                modalAcao?.classList.add("ativo");
                modalAcaoCancelar?.focus();
            };

            const fecharConfirmacao = () => {
                modalAcao?.classList.remove("ativo");
                confirmarAcaoPendente = null;
            };

            modalBloqueioCancelar?.addEventListener("click", fecharModalBloqueio);
            modalAcaoCancelar?.addEventListener("click", fecharConfirmacao);
            modalBloqueio?.addEventListener("click", (evento) => {
                if (evento.target === modalBloqueio) {
                    fecharModalBloqueio();
                }
            });
            modalAcao?.addEventListener("click", (evento) => {
                if (evento.target === modalAcao) {
                    fecharConfirmacao();
                }
            });
            modalBloqueioConfirmar?.addEventListener("click", () => {
                const motivo = (modalBloqueioMotivo?.value || "").trim();
                if (!motivo) {
                    if (modalBloqueioErro) {
                        modalBloqueioErro.textContent = "Informe o motivo do bloqueio.";
                    }
                    modalBloqueioMotivo?.focus();
                    return;
                }
                if (!formBloqueioPendente) {
                    fecharModalBloqueio();
                    return;
                }
                const motivoInput = formBloqueioPendente.querySelector('input[name="motivo"]');
                if (motivoInput) {
                    motivoInput.value = motivo;
                }
                const form = formBloqueioPendente;
                fecharModalBloqueio();
                form.submit();
            });
            modalAcaoConfirmar?.addEventListener("click", () => {
                const onConfirm = confirmarAcaoPendente;
                fecharConfirmacao();
                onConfirm?.();
            });

            document.querySelectorAll(".js-block-toggle-form").forEach((form) => {
                form.addEventListener("submit", (evento) => {
                    const blocked = form.dataset.blocked === "true";
                    const empresa = form.dataset.empresa || "esta empresa";
                    const confirmInput = form.querySelector('input[name="confirmar_desbloqueio"]');

                    if (blocked) {
                        evento.preventDefault();
                        abrirConfirmacao({
                            titulo: "Desbloquear empresa",
                            corpo: `O acesso de ${empresa} será restabelecido. O histórico do bloqueio será preservado.`,
                            confirmarLabel: "Desbloquear",
                            onConfirm: () => {
                                if (confirmInput) {
                                    confirmInput.value = "1";
                                }
                                form.submit();
                            },
                        });
                        return;
                    }

                    evento.preventDefault();
                    abrirModalBloqueio(form);
                });
            });

            document.querySelectorAll(".js-reset-form").forEach((form) => {
                form.addEventListener("submit", (evento) => {
                    const empresa = form.dataset.nome || "esta empresa";
                    evento.preventDefault();
                    abrirConfirmacao({
                        titulo: "Forçar troca de senha",
                        corpo: `O admin-cliente de ${empresa} será obrigado a redefinir a senha no próximo acesso.`,
                        confirmarLabel: "Forçar reset",
                        onConfirm: () => form.submit(),
                    });
                });
            });

            document.querySelectorAll(".js-plan-form").forEach((form) => {
                form.addEventListener("submit", (evento) => {
                    const select = form.querySelector('select[name="plano"]');
                    const empresa = form.dataset.empresa || "esta empresa";
                    const option = select?.selectedOptions?.[0];
                    const preview = option?.dataset.preview || "";
                    evento.preventDefault();
                    abrirConfirmacao({
                        titulo: "Alterar plano",
                        corpo: `Revise o impacto antes de aplicar a mudança em ${empresa}.`,
                        payload: preview,
                        confirmarLabel: "Aplicar plano",
                        onConfirm: () => form.submit(),
                    });
                });
            });
        })();
