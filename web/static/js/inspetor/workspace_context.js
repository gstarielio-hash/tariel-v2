(function () {
    "use strict";

    const inspectorRuntime = window.TarielInspectorRuntime || null;
    const modules = typeof inspectorRuntime?.resolveModuleBucket === "function"
        ? inspectorRuntime.resolveModuleBucket("TarielInspetorModules")
        : (window.TarielInspetorModules = window.TarielInspetorModules || {});

    modules.registerWorkspaceContext = function registerWorkspaceContext(ctx) {
        const estado = ctx.state;
        const el = ctx.elements;
        const {
            NOMES_TEMPLATES,
            escaparHtml,
            mostrarToast,
            pluralizarWorkspace,
            resumirTexto,
            obterLaudoAtivoIdSeguro,
        } = ctx.shared;

        function coletarLinhasWorkspace() {
            return ctx.actions.coletarLinhasWorkspace?.() || [];
        }

        function contarEvidenciasWorkspace() {
            return ctx.actions.contarEvidenciasWorkspace?.() || 0;
        }

        function copiarTextoWorkspace(texto = "") {
            return ctx.actions.copiarTextoWorkspace?.(texto)
                || Promise.reject(new Error("COPY_UNAVAILABLE"));
        }

        function obterDetalheLinhaWorkspace(linha) {
            return ctx.actions.obterDetalheLinhaWorkspace?.(linha) || {
                mensagemId: null,
                autor: "Registro",
                papel: "inspetor",
                tempo: "",
                texto: "",
            };
        }

        function obterPapelLinhaWorkspace(linha) {
            return ctx.actions.obterPapelLinhaWorkspace?.(linha) || "inspetor";
        }

        function obterResumoOperacionalMesa() {
            return ctx.actions.obterResumoOperacionalMesa?.() || {
                status: "pronta",
                titulo: "Mesa disponível",
                descricao: "",
                chipStatus: "",
                chipPendencias: "",
                chipNaoLidas: "",
            };
        }

        function obterChaveContextoFixadoWorkspace() {
            const laudoId = obterLaudoAtivoIdSeguro();
            return `tariel_workspace_contexto_fixado_${laudoId || "ativo"}`;
        }

        function persistirContextoFixadoWorkspace() {
            try {
                localStorage.setItem(
                    obterChaveContextoFixadoWorkspace(),
                    JSON.stringify(Array.isArray(estado.contextoFixado) ? estado.contextoFixado : [])
                );
            } catch (_) {
                // armazenamento local opcional
            }
        }

        function carregarContextoFixadoWorkspace() {
            try {
                const bruto = localStorage.getItem(obterChaveContextoFixadoWorkspace());
                const itens = JSON.parse(bruto || "[]");
                estado.contextoFixado = Array.isArray(itens) ? itens.filter(Boolean).slice(0, 8) : [];
            } catch (_) {
                estado.contextoFixado = [];
            }
        }

        function obterResumoSinteseIAWorkspace() {
            const bruto = String(window.TarielAPI?.obterUltimoDiagnosticoBruto?.() || "").trim();
            if (bruto) {
                return resumirTexto(bruto, 180);
            }

            const linhas = coletarLinhasWorkspace();
            for (let i = linhas.length - 1; i >= 0; i -= 1) {
                const linha = linhas[i];
                if (obterPapelLinhaWorkspace(linha) !== "ia") continue;
                const texto = obterDetalheLinhaWorkspace(linha).texto;
                if (texto) return resumirTexto(texto, 180);
            }

            return "A última resposta consolidada da IA aparecerá aqui.";
        }

        function obterOperacaoWorkspace() {
            const subtitulo = String(estado.workspaceVisualContext?.subtitle || "").trim();
            if (!subtitulo) return "Operação não identificada";
            return subtitulo.split("•")[0].trim() || subtitulo;
        }

        function montarResumoContextoIAWorkspace() {
            const titulo = String(estado.workspaceVisualContext?.title || "Registro Técnico").trim();
            const operacao = obterOperacaoWorkspace();
            const modelo = NOMES_TEMPLATES[estado.tipoTemplateAtivo] || NOMES_TEMPLATES.padrao;
            const evidencias = contarEvidenciasWorkspace();
            const pendencias = Number(estado.qtdPendenciasAbertas || 0) || 0;
            const sintese = obterResumoSinteseIAWorkspace();
            const fixados = (estado.contextoFixado || [])
                .slice(0, 3)
                .map((item) => `- ${item.autor}: ${item.texto}`)
                .join("\n");

            return [
                `Equipamento: ${titulo}`,
                `Operação: ${operacao}`,
                `Modelo: ${modelo}`,
                `Evidências: ${evidencias}`,
                `Pendências: ${pendencias}`,
                `Síntese atual: ${sintese}`,
                fixados ? `Contexto fixado:\n${fixados}` : "",
            ]
                .filter(Boolean)
                .join("\n");
        }

        function renderizarContextoIAWorkspace() {
            const evidencias = contarEvidenciasWorkspace();
            const pendencias = Number(estado.qtdPendenciasAbertas || 0) || 0;
            const modelo = NOMES_TEMPLATES[estado.tipoTemplateAtivo] || NOMES_TEMPLATES.padrao;
            const operacao = obterOperacaoWorkspace();
            const resumoMesa = obterResumoOperacionalMesa();

            if (el.workspaceContextTemplate) {
                el.workspaceContextTemplate.textContent = modelo;
            }
            if (el.workspaceContextEvidencias) {
                el.workspaceContextEvidencias.textContent = String(evidencias);
            }
            if (el.workspaceContextPendencias) {
                el.workspaceContextPendencias.textContent = String(pendencias);
            }
            if (el.workspaceContextMesa) {
                el.workspaceContextMesa.textContent = resumoMesa.chipStatus || resumoMesa.titulo;
            }
            if (el.workspaceContextEquipment) {
                el.workspaceContextEquipment.textContent = String(estado.workspaceVisualContext?.title || "Registro Técnico");
            }
            if (el.workspaceContextOperation) {
                el.workspaceContextOperation.textContent = operacao;
            }
            if (el.workspaceContextSummary) {
                el.workspaceContextSummary.textContent = obterResumoSinteseIAWorkspace();
            }

            const fixados = Array.isArray(estado.contextoFixado) ? estado.contextoFixado : [];
            if (el.workspacePinnedCard) {
                const mostrarCardFixado = fixados.length > 0;
                el.workspacePinnedCard.hidden = !mostrarCardFixado;
                el.workspacePinnedCard.setAttribute("aria-hidden", String(!mostrarCardFixado));
            }
            if (el.workspaceContextPinnedCount) {
                el.workspaceContextPinnedCount.textContent = `${fixados.length} ${pluralizarWorkspace(fixados.length, "item", "itens")}`;
            }
            if (el.workspaceContextPinnedList) {
                if (!fixados.length) {
                    el.workspaceContextPinnedList.innerHTML = `
                        <p class="workspace-context-pinned-empty">
                            Fixe mensagens importantes para manter fatos críticos sempre à vista.
                        </p>
                    `;
                } else {
                    el.workspaceContextPinnedList.innerHTML = fixados
                        .map((item, index) => `
                            <article class="workspace-context-pin">
                                <div class="workspace-context-pin__meta">
                                    <strong>${escaparHtml(item.autor || "Registro")}</strong>
                                    <span>${escaparHtml(item.papel || "contexto")}</span>
                                </div>
                                <p>${escaparHtml(item.texto || "")}</p>
                                <button type="button" class="workspace-context-pin__remove" data-context-remove-index="${index}">
                                    Remover
                                </button>
                            </article>
                        `)
                        .join("");
                }
            }
        }

        function fixarContextoWorkspace(detail = {}) {
            const textoBase = String(detail?.texto || "").trim() || (
                Array.isArray(detail?.anexos)
                    ? detail.anexos.map((anexo) => String(anexo?.nome || "").trim()).filter(Boolean).join(" • ")
                    : ""
            );
            const texto = resumirTexto(textoBase, 220);
            if (!texto) return;

            const existente = (estado.contextoFixado || []).find((item) => {
                const itemId = Number(item?.mensagemId || 0) || null;
                const alvoId = Number(detail?.mensagemId || 0) || null;
                return (itemId && alvoId && itemId === alvoId) || String(item?.texto || "") === texto;
            });

            if (existente) {
                mostrarToast("Esse contexto já está fixado.", "info", 1800);
                return;
            }

            estado.contextoFixado = [
                {
                    mensagemId: Number(detail?.mensagemId || 0) || null,
                    autor: String(detail?.autor || "Registro").trim() || "Registro",
                    papel: String(detail?.papel || "contexto").trim() || "contexto",
                    texto,
                },
                ...(Array.isArray(estado.contextoFixado) ? estado.contextoFixado : []),
            ].slice(0, 8);

            persistirContextoFixadoWorkspace();
            renderizarContextoIAWorkspace();
            mostrarToast("Trecho fixado no contexto da IA.", "sucesso", 1800);
        }

        function removerContextoFixadoWorkspace(index) {
            const alvo = Number(index);
            if (!Number.isFinite(alvo) || alvo < 0) return;
            estado.contextoFixado = (estado.contextoFixado || []).filter((_, idx) => idx !== alvo);
            persistirContextoFixadoWorkspace();
            renderizarContextoIAWorkspace();
        }

        function limparContextoFixadoWorkspace() {
            estado.contextoFixado = [];
            persistirContextoFixadoWorkspace();
            renderizarContextoIAWorkspace();
        }

        async function copiarResumoContextoWorkspace() {
            try {
                await copiarTextoWorkspace(montarResumoContextoIAWorkspace());
                mostrarToast("Resumo operacional copiado.", "sucesso", 1800);
            } catch (_) {
                mostrarToast("Não foi possível copiar o resumo agora.", "aviso", 2200);
            }
        }

        function atualizarStatusChatWorkspace(status = "pronto", texto = "") {
            const normalizado = ["respondendo", "documento", "interrompido", "erro", "mesa", "pronto"]
                .includes(String(status || "").trim().toLowerCase())
                ? String(status).trim().toLowerCase()
                : "pronto";

            estado.chatStatusIA = {
                status: normalizado,
                texto: String(texto || "").trim() || "Assistente pronto",
            };
        }

        function renderizarMesaCardWorkspace() {
            const resumo = obterResumoOperacionalMesa();
            const evidencias = contarEvidenciasWorkspace();
            const pendencias = Number(estado.qtdPendenciasAbertas || 0) || 0;
            const naoLidas = Number(estado.mesaWidgetNaoLidas || 0) || 0;
            const modelo = NOMES_TEMPLATES[estado.tipoTemplateAtivo] || NOMES_TEMPLATES.padrao;
            const operacao = obterOperacaoWorkspace();
            const equipamento = String(estado.workspaceVisualContext?.title || "Registro técnico").trim() || "Registro técnico";
            const ultimoMovimento = resumo.descricao || "Sem atualização recente.";
            let proximoPasso = "Use o canal para alinhar dúvidas ou anexar novas evidências.";

            if (pendencias > 0) {
                proximoPasso = "Responda às pendências abertas para destravar a revisão.";
            } else if (naoLidas > 0) {
                proximoPasso = "Leia o retorno mais recente da mesa e ajuste o laudo se necessário.";
            } else if (resumo.status === "aguardando") {
                proximoPasso = "Aguarde a resposta da mesa ou complemente o caso com novo contexto.";
            }

            if (el.workspaceMesaCardText) {
                el.workspaceMesaCardText.textContent = resumo.descricao;
            }
            if (el.workspaceMesaCardStatus) {
                el.workspaceMesaCardStatus.textContent = resumo.chipStatus || resumo.titulo;
                el.workspaceMesaCardStatus.dataset.mesaStatus = String(resumo.status || "pronta");
            }
            if (el.workspaceMesaCardUnread) {
                el.workspaceMesaCardUnread.hidden = naoLidas <= 0;
                el.workspaceMesaCardUnread.textContent = naoLidas > 99 ? "99+ novas" : `${naoLidas} novas`;
            }
            if (el.workspaceMesaStageStatus) {
                el.workspaceMesaStageStatus.textContent = resumo.chipStatus || resumo.titulo;
            }
            if (el.workspaceMesaStagePendencias) {
                el.workspaceMesaStagePendencias.textContent = String(pendencias);
            }
            if (el.workspaceMesaStageEvidencias) {
                el.workspaceMesaStageEvidencias.textContent = String(evidencias);
            }
            if (el.workspaceMesaStageUnread) {
                el.workspaceMesaStageUnread.textContent = String(naoLidas);
            }
            if (el.workspaceMesaStageSummary) {
                el.workspaceMesaStageSummary.textContent = resumo.descricao;
            }
            if (el.workspaceMesaStageNextStep) {
                el.workspaceMesaStageNextStep.textContent = proximoPasso;
            }
            if (el.workspaceMesaStageTemplate) {
                el.workspaceMesaStageTemplate.textContent = modelo;
            }
            if (el.workspaceMesaStageOperation) {
                el.workspaceMesaStageOperation.textContent = operacao;
            }
            if (el.workspaceMesaStageEquipment) {
                el.workspaceMesaStageEquipment.textContent = equipamento;
            }
            if (el.workspaceMesaStageLastMovement) {
                el.workspaceMesaStageLastMovement.textContent = ultimoMovimento;
            }
        }

        Object.assign(ctx.actions, {
            atualizarStatusChatWorkspace,
            carregarContextoFixadoWorkspace,
            copiarResumoContextoWorkspace,
            fixarContextoWorkspace,
            limparContextoFixadoWorkspace,
            montarResumoContextoIAWorkspace,
            removerContextoFixadoWorkspace,
            renderizarContextoIAWorkspace,
            renderizarMesaCardWorkspace,
        });
    };
})();
