(() => {
    "use strict";

    const selecionar = (seletor, raiz = document) => raiz.querySelector(seletor);
    const selecionarTodos = (seletor, raiz = document) => Array.from(raiz.querySelectorAll(seletor));

    const removerAlerta = (elemento) => {
        if (!elemento || elemento.dataset.removendo === "true") return;
        elemento.dataset.removendo = "true";
        elemento.classList.add("saindo");
        window.setTimeout(() => elemento.remove(), 250);
    };

    const inicializarAlertas = () => {
        selecionarTodos(".alert").forEach((elemento) => {
            selecionar(".alert-fechar", elemento)?.addEventListener("click", () => removerAlerta(elemento));
            window.setTimeout(() => removerAlerta(elemento), 6000);
        });
    };

    const inicializarAbas = () => {
        const abas = selecionarTodos("[data-admin-tab-target]");
        const paineis = selecionarTodos("[data-admin-tab-panel]");

        const selecionarAba = (alvo) => {
            abas.forEach((aba) => {
                const ativa = aba.dataset.adminTabTarget === alvo;
                aba.setAttribute("aria-selected", ativa ? "true" : "false");
            });
            paineis.forEach((painel) => {
                painel.hidden = painel.dataset.adminTabPanel !== alvo;
            });
        };

        abas.forEach((aba) => {
            aba.addEventListener("click", () => selecionarAba(aba.dataset.adminTabTarget || "resumo"));
        });
        selecionarAba("resumo");
    };

    const copiarTexto = async (texto) => {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(texto);
            return;
        }

        const temp = document.createElement("textarea");
        temp.value = texto;
        temp.setAttribute("readonly", "true");
        temp.style.position = "absolute";
        temp.style.left = "-9999px";
        document.body.appendChild(temp);
        temp.select();
        document.execCommand("copy");
        document.body.removeChild(temp);
    };

    const inicializarCopiaOnboarding = () => {
        const botao = selecionar("[data-copy-onboarding]");
        const feedback = selecionar("[data-copy-feedback]");
        botao?.addEventListener("click", async () => {
            const texto = botao.dataset.copyText || "";
            if (!texto) return;

            try {
                await copiarTexto(texto);
                if (feedback) {
                    feedback.hidden = false;
                    feedback.textContent = "Instrucoes copiadas.";
                    window.setTimeout(() => {
                        feedback.hidden = true;
                    }, 2200);
                }
            } catch (_error) {
                if (feedback) {
                    feedback.hidden = false;
                    feedback.textContent = "Nao foi possivel copiar agora.";
                }
            }
        });
    };

    const criarControladorConfirmacao = () => {
        const dialog = selecionar("#admin-action-dialog-detail");
        const titulo = selecionar("#admin-action-dialog-detail-title");
        const corpo = selecionar("#admin-action-dialog-detail-body");
        const payload = selecionar("#admin-action-dialog-detail-payload");
        const cancelar = selecionar("#admin-action-dialog-detail-cancelar");
        const confirmar = selecionar("#admin-action-dialog-detail-confirmar");
        let acaoPendente = null;

        const fechar = () => {
            dialog?.classList.remove("ativo");
            acaoPendente = null;
        };

        const abrir = ({ tituloTexto, corpoTexto, payloadTexto = "", variante = "primario", onConfirm }) => {
            if (titulo) {
                titulo.textContent = tituloTexto;
            }
            if (corpo) {
                corpo.textContent = corpoTexto;
            }
            if (payload) {
                if (payloadTexto) {
                    payload.textContent = payloadTexto;
                    payload.hidden = false;
                } else {
                    payload.textContent = "";
                    payload.hidden = true;
                }
            }
            if (confirmar) {
                confirmar.className = `btn-admin ${variante === "perigo" ? "perigo" : "primario"}`;
                confirmar.textContent = variante === "perigo" ? "Confirmar ação" : "Confirmar";
            }
            acaoPendente = typeof onConfirm === "function" ? onConfirm : null;
            dialog?.classList.add("ativo");
        };

        cancelar?.addEventListener("click", fechar);
        dialog?.addEventListener("click", (evento) => {
            if (evento.target === dialog) {
                fechar();
            }
        });
        confirmar?.addEventListener("click", () => {
            const acao = acaoPendente;
            fechar();
            acao?.();
        });

        return { abrir };
    };

    const criarControladorBloqueioEmpresa = () => {
        const modal = selecionar("#modal-bloqueio-empresa");
        const fecharBotao = selecionar("#fechar-modal-bloqueio-empresa");
        const cancelarBotao = selecionar("#cancelar-modal-bloqueio-empresa");
        const confirmarBotao = selecionar("#confirmar-modal-bloqueio-empresa");
        const motivoInput = selecionar("#motivo-bloqueio-empresa");
        const erro = selecionar("#erro-modal-bloqueio-empresa");
        let formularioPendente = null;

        const fechar = () => {
            modal?.classList.remove("ativo");
            formularioPendente = null;
            if (erro) {
                erro.textContent = "";
            }
        };

        const abrir = (formulario) => {
            formularioPendente = formulario;
            if (motivoInput) {
                motivoInput.value = "";
                motivoInput.focus();
            }
            if (erro) {
                erro.textContent = "";
            }
            modal?.classList.add("ativo");
        };

        fecharBotao?.addEventListener("click", fechar);
        cancelarBotao?.addEventListener("click", fechar);
        modal?.addEventListener("click", (evento) => {
            if (evento.target === modal) {
                fechar();
            }
        });
        confirmarBotao?.addEventListener("click", () => {
            const motivo = (motivoInput?.value || "").trim();
            if (!motivo) {
                if (erro) {
                    erro.textContent = "Informe o motivo do bloqueio.";
                }
                motivoInput?.focus();
                return;
            }

            if (!formularioPendente) {
                fechar();
                return;
            }

            const motivoHidden = selecionar('input[name="motivo"]', formularioPendente);
            if (motivoHidden) {
                motivoHidden.value = motivo;
            }
            const formulario = formularioPendente;
            fechar();
            formulario.submit();
        });

        return { abrir };
    };

    const inicializarFormulariosBloqueioEmpresa = (confirmacao, bloqueioEmpresa) => {
        selecionarTodos(".js-company-block-form").forEach((formulario) => {
            formulario.addEventListener("submit", (evento) => {
                const bloqueada = formulario.dataset.blocked === "true";
                const empresa = formulario.dataset.empresa || "esta empresa";
                const confirmarDesbloqueio = selecionar('input[name="confirmar_desbloqueio"]', formulario);

                evento.preventDefault();
                if (bloqueada) {
                    confirmacao.abrir({
                        tituloTexto: "Desbloquear empresa",
                        corpoTexto: `Confirme a liberação de ${empresa}. O histórico do bloqueio será preservado.`,
                        payloadTexto: "A empresa volta a aceitar novos logins imediatamente.",
                        onConfirm: () => {
                            if (confirmarDesbloqueio) {
                                confirmarDesbloqueio.value = "1";
                            }
                            formulario.submit();
                        },
                    });
                    return;
                }

                bloqueioEmpresa.abrir(formulario);
            });
        });
    };

    const inicializarFormulariosResetSenha = (confirmacao) => {
        selecionarTodos(".js-reset-form").forEach((formulario) => {
            formulario.addEventListener("submit", (evento) => {
                evento.preventDefault();
                const usuario = formulario.dataset.usuario || "este usuário";
                confirmacao.abrir({
                    tituloTexto: "Forçar troca de senha",
                    corpoTexto: `O próximo acesso de ${usuario} exigirá troca imediata de senha.`,
                    payloadTexto: "Nenhuma senha definitiva será exposta no portal.",
                    onConfirm: () => formulario.submit(),
                });
            });
        });
    };

    const inicializarFormulariosBloqueioUsuario = (confirmacao) => {
        selecionarTodos(".js-user-block-form").forEach((formulario) => {
            formulario.addEventListener("submit", (evento) => {
                evento.preventDefault();
                const usuario = formulario.dataset.usuario || "este usuário";
                const ativo = formulario.dataset.ativo === "true";
                confirmacao.abrir({
                    tituloTexto: ativo ? "Bloquear usuário" : "Reativar usuário",
                    corpoTexto: ativo
                        ? `Bloqueie ${usuario} para encerrar sessões ativas e impedir novos acessos.`
                        : `Reative ${usuario} para restabelecer o acesso operacional.`,
                    payloadTexto: ativo ? "A sessão do usuário será invalidada após a confirmação." : "",
                    variante: ativo ? "perigo" : "primario",
                    onConfirm: () => formulario.submit(),
                });
            });
        });
    };

    const inicializarModalPlano = (confirmacao) => {
        const modal = selecionar("#modal-plano");
        const abrirBotao = selecionar("#btn-abrir-modal-plano");
        const fecharBotao = selecionar("#fechar-modal-plano");
        const cancelarBotao = selecionar("#cancelar-modal-plano");
        const selectPlano = selecionar("#select-plano");
        const formPlano = selecionar("#form-modal-plano");
        const resumo = selecionar("#preview-plano-resumo");
        const usuarios = selecionar("#preview-usuarios");
        const laudos = selecionar("#preview-laudos");
        const integracoes = selecionar("#preview-integracoes");
        const retencao = selecionar("#preview-retencao");
        const alertas = selecionar("#preview-alertas");

        const atualizarPreview = () => {
            const opcao = selectPlano?.selectedOptions?.[0];
            if (!opcao) return;

            if (resumo) {
                resumo.textContent = opcao.dataset.resumo || "Sem preview disponível.";
            }
            if (usuarios) {
                usuarios.textContent = `Usuários: ${opcao.dataset.impactoUsuarios || "Sem alteração"}`;
            }
            if (laudos) {
                laudos.textContent = `Laudos/mês: ${opcao.dataset.impactoLaudos || "Sem alteração"}`;
            }
            if (integracoes) {
                integracoes.textContent = `Integrações: ${opcao.dataset.impactoIntegracoes || "Sem alteração"}`;
            }
            if (retencao) {
                retencao.textContent = `Retenção: ${opcao.dataset.impactoRetencao || "Sem alteração"}`;
            }
            if (alertas) {
                alertas.textContent = opcao.dataset.alertas
                    ? `Alertas: ${opcao.dataset.alertas}`
                    : "Alertas: sem alertas.";
            }
        };

        const fechar = () => {
            modal?.classList.remove("ativo");
            abrirBotao?.setAttribute("aria-expanded", "false");
        };

        const abrir = () => {
            modal?.classList.add("ativo");
            abrirBotao?.setAttribute("aria-expanded", "true");
            atualizarPreview();
            selectPlano?.focus();
        };

        abrirBotao?.addEventListener("click", abrir);
        fecharBotao?.addEventListener("click", fechar);
        cancelarBotao?.addEventListener("click", fechar);
        modal?.addEventListener("click", (evento) => {
            if (evento.target === modal) {
                fechar();
            }
        });
        selectPlano?.addEventListener("change", atualizarPreview);
        atualizarPreview();

        formPlano?.addEventListener("submit", (evento) => {
            evento.preventDefault();
            const opcao = selectPlano?.selectedOptions?.[0];
            const planoNome = opcao?.value || "plano selecionado";
            const resumoPlano = opcao?.dataset.resumo || "Sem preview disponível.";
            confirmacao.abrir({
                tituloTexto: "Confirmar alteração de plano",
                corpoTexto: `Revise o impacto antes de aplicar o plano ${planoNome}.`,
                payloadTexto: resumoPlano,
                onConfirm: () => formPlano.submit(),
            });
        });
    };

    const init = () => {
        inicializarAlertas();
        inicializarAbas();
        inicializarCopiaOnboarding();

        const confirmacao = criarControladorConfirmacao();
        const bloqueioEmpresa = criarControladorBloqueioEmpresa();

        inicializarFormulariosBloqueioEmpresa(confirmacao, bloqueioEmpresa);
        inicializarFormulariosResetSenha(confirmacao);
        inicializarFormulariosBloqueioUsuario(confirmacao);
        inicializarModalPlano(confirmacao);
    };

    init();
})();
