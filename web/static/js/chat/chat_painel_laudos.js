// ==========================================
// TARIEL CONTROL TOWER — CHAT_PAINEL_LAUDOS.JS
// Papel: seleção de laudos, breadcrumb, estado da URL,
// persistência do laudo atual e carga inicial.
//
// Dependência:
// - window.TarielChatPainel (core)
//
// Responsável por:
// - marcar item ativo no histórico
// - criar/atualizar breadcrumb do laudo
// - controlar tabs do workspace (conversa / historico / anexos / mesa)
// - persistir laudo atual
// - sincronizar URL ?laudo=
// - carregar laudo inicial
// - atualizar badge visual de status do relatório
// ==========================================

(function () {
    "use strict";

    const TP = window.TarielChatPainel;
    if (!TP || TP.__laudosWired__) return;
    TP.__laudosWired__ = true;
    const PERF = window.TarielPerf || window.TarielCore?.TarielPerf || TP.perf || null;
    const CaseLifecycle = window.TarielCaseLifecycle;

    if (!CaseLifecycle) {
        return;
    }

    PERF?.noteModule?.("chat/chat_painel_laudos.js", {
        readyState: document.readyState,
    });

    const STATE_LOCAL = {
        popStateBound: false,
        navBound: false,
        threadNavWarned: false,
        eventosLaudosBound: false,
        tentativaLaudoInicialTimer: null,
        laudoSelecionadoEmFluxo: null,
        ultimaSelecaoAssinatura: "",
        ultimaSelecaoAt: 0,
    };

    const STATUS_CARD = {
        aberto: "Aberto",
        aguardando: "Aguardando",
        ajustes: "Ajustes",
        aprovado: "Aprovado",
    };

    // =========================================================
    // HELPERS LOCAIS
    // =========================================================

    function normalizarEstadoRelatorio(valor) {
        const estado = String(valor || "").trim().toLowerCase();

        if (estado === "relatorioativo" || estado === "relatorio_ativo") {
            return "relatorio_ativo";
        }

        if (estado === "semrelatorio" || estado === "sem_relatorio") {
            return "sem_relatorio";
        }

        if (estado === "aguardando" || estado === "aguardando_avaliacao") {
            return "aguardando";
        }

        if (estado === "ajustes" || estado === "aprovado") {
            return estado;
        }

        return estado || "sem_relatorio";
    }

    function normalizarThreadTabLocal(valor, fallback = "historico") {
        const bruto = String(valor || "").trim().toLowerCase();
        if (bruto === "chat" || bruto === "conversa") return "conversa";
        if (bruto === "history" || bruto === "historico") return "historico";
        if (bruto === "attachments" || bruto === "anexos") return "anexos";
        if (bruto === "mesa") return "mesa";
        const fallbackNormalizado = String(fallback || "").trim().toLowerCase();
        if (fallbackNormalizado === "chat" || fallbackNormalizado === "conversa") return "conversa";
        if (fallbackNormalizado === "attachments" || fallbackNormalizado === "anexos") return "anexos";
        if (fallbackNormalizado === "mesa") return "mesa";
        return "historico";
    }

    function normalizarEntryModeEffectiveLocal(valor) {
        const bruto = String(valor || "").trim().toLowerCase();
        if (bruto === "evidence_first" || bruto === "evidencefirst" || bruto === "evidencia") {
            return "evidence_first";
        }
        if (bruto === "chat_first" || bruto === "chatfirst" || bruto === "conversa") {
            return "chat_first";
        }
        return "";
    }

    function aplicarModoEntradaDataset(item, payload = {}) {
        if (!item?.dataset) return;

        const detail = payload && typeof payload === "object" ? payload : {};
        const preference = String(
            detail.entry_mode_preference ??
            detail.entryModePreference ??
            item.dataset.entryModePreference ??
            ""
        ).trim();
        const effective = normalizarEntryModeEffectiveLocal(
            detail.entry_mode_effective ??
            detail.entryModeEffective ??
            item.dataset.entryModeEffective ??
            ""
        );
        const reason = String(
            detail.entry_mode_reason ??
            detail.entryModeReason ??
            item.dataset.entryModeReason ??
            ""
        ).trim();

        item.dataset.entryModePreference = preference;
        item.dataset.entryModeEffective = effective;
        item.dataset.entryModeReason = reason;
    }

    function extrairModoEntradaItem(item) {
        if (!item?.dataset) {
            return {
                entry_mode_preference: "",
                entry_mode_effective: "",
                entry_mode_reason: "",
            };
        }

        return {
            entry_mode_preference: String(item.dataset.entryModePreference || "").trim(),
            entry_mode_effective: normalizarEntryModeEffectiveLocal(item.dataset.entryModeEffective || ""),
            entry_mode_reason: String(item.dataset.entryModeReason || "").trim(),
        };
    }

    function resolverPayloadModoEntradaSelecao(opts = {}, item = null) {
        const detail = opts && typeof opts === "object" ? opts : {};
        const itemPayload = extrairModoEntradaItem(item);

        return {
            entry_mode_preference: String(
                detail.entry_mode_preference ??
                detail.entryModePreference ??
                itemPayload.entry_mode_preference ??
                ""
            ).trim(),
            entry_mode_effective: normalizarEntryModeEffectiveLocal(
                detail.entry_mode_effective ??
                detail.entryModeEffective ??
                itemPayload.entry_mode_effective ??
                ""
            ),
            entry_mode_reason: String(
                detail.entry_mode_reason ??
                detail.entryModeReason ??
                itemPayload.entry_mode_reason ??
                ""
            ).trim(),
        };
    }

    function resolverThreadTabInicialPorModoEntrada(payload = {}, fallback = "historico") {
        const detail = payload && typeof payload === "object" ? payload : {};
        const effective = normalizarEntryModeEffectiveLocal(
            detail.entry_mode_effective ??
            detail.entryModeEffective ??
            detail.effective ??
            ""
        );
        if (effective === "evidence_first") return "anexos";
        if (effective === "chat_first") return "conversa";
        return normalizarThreadTabLocal(fallback, "historico");
    }

    function obterSidebar() {
        return document.getElementById("barra-historico");
    }

    function fecharSidebarMobile() {
        const sidebar = obterSidebar();
        const overlay = document.getElementById("overlay-sidebar");

        if (window.innerWidth >= 768) return;

        sidebar?.classList.remove("aberta", "aberto");
        overlay?.classList.remove("ativo");
        document.body.classList.remove("sidebar-aberta");
    }

    function definirLaudoAtualNoCore(laudoId) {
        const id = laudoId ? Number(laudoId) : null;
        const idValido = Number.isFinite(id) && id > 0 ? id : null;

        if (typeof window.TarielInspectorState?.sincronizarEstadoInspector === "function") {
            window.TarielInspectorState.sincronizarEstadoInspector({
                laudoAtualId: idValido,
            });
            return;
        }

        TP.sincronizarEstadoPainel?.({ laudoAtualId: idValido });
        TP.persistirLaudoAtual(idValido || "");
        document.body.dataset.laudoAtualId = idValido ? String(idValido) : "";
    }

    function obterEstadoRelatorioAtual() {
        if (window.TarielAPI?.obterEstadoRelatorioNormalizado) {
            return normalizarEstadoRelatorio(
                window.TarielAPI.obterEstadoRelatorioNormalizado()
            );
        }

        if (window.TarielAPI?.obterEstadoRelatorio) {
            return normalizarEstadoRelatorio(
                window.TarielAPI.obterEstadoRelatorio()
            );
        }

        return normalizarEstadoRelatorio(TP.state.estadoRelatorio);
    }

    function obterLaudoAtivoNaApi() {
        const valor = window.TarielAPI?.obterLaudoAtualId?.();
        const id = Number(valor);
        return Number.isFinite(id) && id > 0 ? id : null;
    }

    // =========================================================
    // HISTÓRICO DINÂMICO / STATUS VISUAL
    // =========================================================

    function escaparHTMLLocal(valor) {
        return TP.escaparHTML?.(valor) ?? String(valor ?? "");
    }

    function normalizarStatusCard(status) {
        const valor = String(status || "").trim().toLowerCase();

        if (valor === "ativo" || valor === "relatorio_ativo") return "aberto";
        if (valor === "aguardando_aval") return "aguardando";
        if (valor === "rejeitado") return "ajustes";
        if (STATUS_CARD[valor]) return valor;
        return "aberto";
    }

    const normalizarCaseLifecycleStatus = (status) =>
        CaseLifecycle.normalizarCaseLifecycleStatus(status);
    const normalizarActiveOwnerRole = (valor) =>
        CaseLifecycle.normalizarActiveOwnerRole(valor);
    const normalizarAllowedSurfaceActions = (valores = []) =>
        CaseLifecycle.normalizarAllowedSurfaceActions(valores);

    function obterStatusVisualCard(status, lifecycleStatus = "") {
        const lifecycle = normalizarCaseLifecycleStatus(lifecycleStatus);
        if (lifecycle === "analise_livre") {
            return { variant: "aberto", label: "Análise livre" };
        }
        if (lifecycle === "pre_laudo") {
            return { variant: "aberto", label: "Pré-laudo" };
        }
        if (lifecycle === "laudo_em_coleta") {
            return { variant: "aberto", label: "Em coleta" };
        }
        if (lifecycle === "aguardando_mesa") {
            return { variant: "aguardando", label: "Aguardando mesa" };
        }
        if (lifecycle === "em_revisao_mesa") {
            return { variant: "aguardando", label: "Mesa em revisão" };
        }
        if (lifecycle === "devolvido_para_correcao") {
            return { variant: "ajustes", label: "Correção" };
        }
        if (lifecycle === "aprovado") {
            return { variant: "aprovado", label: "Aprovado" };
        }
        if (lifecycle === "emitido") {
            return { variant: "aprovado", label: "Emitido" };
        }

        const normalizado = normalizarStatusCard(status);
        return {
            variant: normalizado,
            label: STATUS_CARD[normalizado] || "Aberto",
        };
    }

    function obterLabelStatusCard(status) {
        const normalizado = normalizarStatusCard(status);
        return STATUS_CARD[normalizado] || "Aberto";
    }

    function obterRotuloOwnerRole(role = "") {
        const normalizado = normalizarActiveOwnerRole(role);
        if (normalizado === "inspetor") return "Responsável: campo";
        if (normalizado === "mesa") return "Responsável: mesa";
        if (normalizado === "none") return "Responsável: conclusão";
        return "";
    }

    function obterRotuloSurfaceAction(action = "") {
        const normalizado = String(action || "").trim().toLowerCase();
        if (normalizado === "chat_finalize") return "Próxima ação: enviar para mesa";
        if (normalizado === "chat_reopen") return "Próxima ação: reabrir no chat";
        if (normalizado === "mesa_approve") return "Próxima ação: aprovar na mesa";
        if (normalizado === "mesa_return") return "Próxima ação: devolver para correção";
        if (normalizado === "system_issue") return "Próxima ação: emitir PDF final";
        return "";
    }

    function obterAcaoPrimariaCard(card = {}) {
        const actions = normalizarAllowedSurfaceActions(card.allowed_surface_actions);
        const prioridade = [
            "chat_reopen",
            "chat_finalize",
            "mesa_return",
            "mesa_approve",
            "system_issue",
        ];

        for (const action of prioridade) {
            if (actions.includes(action)) {
                return action;
            }
        }

        return actions[0] || "";
    }

    function construirMetaCanonicaCard(card = {}) {
        const partes = [];
        const ownerLabel = obterRotuloOwnerRole(card.active_owner_role);
        const actionLabel = obterRotuloSurfaceAction(obterAcaoPrimariaCard(card));

        if (ownerLabel) {
            partes.push(ownerLabel);
        }
        if (actionLabel) {
            partes.push(actionLabel);
        }

        return partes.join(" • ");
    }

    function atualizarMetaCanonicaItem(item, card = {}) {
        if (!item) return;
        const container = item.querySelector(".texto-laudo-historico");
        if (!container) return;

        let metaEl = container.querySelector(".meta-canonica-laudo");
        if (!metaEl) {
            metaEl = document.createElement("small");
            metaEl.className = "meta-canonica-laudo";
            container.appendChild(metaEl);
        }

        const texto = construirMetaCanonicaCard(card);
        metaEl.textContent = texto;
        metaEl.hidden = !texto;
    }

    function construirNotaGovernancaOficial(summary = null) {
        if (!summary || typeof summary !== "object") {
            return {
                visible: false,
                label: "",
                detail: "",
                issueNumber: "",
                openThreadTab: "conversa",
            };
        }

        return {
            visible: true,
            label: String(summary.label || "").trim() || "Reemissão recomendada",
            detail: String(summary.detail || "").trim(),
            issueNumber: String(summary.issue_number || "").trim(),
            openThreadTab: "mesa",
        };
    }

    function atualizarGovernancaOficialItem(item, card = {}) {
        if (!item || !Object.prototype.hasOwnProperty.call(card, "official_issue_summary")) {
            return;
        }

        const container = item.querySelector(".texto-laudo-historico");
        if (!container) return;

        const governance = construirNotaGovernancaOficial(card.official_issue_summary);
        item.dataset.officialIssueDiverged = governance.visible ? "true" : "false";
        item.dataset.officialIssueLabel = governance.label;
        item.dataset.officialIssueDetail = governance.detail;
        item.dataset.officialIssueNumber = governance.issueNumber;
        item.dataset.openThreadTab = governance.openThreadTab;

        let noteEl = container.querySelector(".inspetor-sidebar-report__governance");
        if (!noteEl) {
            noteEl = document.createElement("small");
            noteEl.className = "inspetor-sidebar-report__governance";
            noteEl.setAttribute("aria-label", "Reemissão recomendada");

            const iconEl = document.createElement("span");
            iconEl.className = "material-symbols-rounded";
            iconEl.setAttribute("aria-hidden", "true");
            iconEl.textContent = "warning";

            const labelEl = document.createElement("span");
            labelEl.className = "inspetor-sidebar-report__governance-label";

            const actionEl = document.createElement("span");
            actionEl.className = "inspetor-sidebar-report__governance-action";

            noteEl.appendChild(iconEl);
            noteEl.appendChild(labelEl);
            noteEl.appendChild(actionEl);
            container.appendChild(noteEl);
        }

        const labelEl = noteEl.querySelector(".inspetor-sidebar-report__governance-label");
        const actionEl = noteEl.querySelector(".inspetor-sidebar-report__governance-action");
        if (labelEl) {
            labelEl.textContent = governance.label;
        }
        if (actionEl) {
            actionEl.textContent = governance.visible ? "Abrir pela Mesa" : "";
        }
        noteEl.hidden = !governance.visible;
    }

    function getListaHistorico() {
        return document.getElementById("lista-historico");
    }

    function getEstadoVazioHistorico() {
        return document.getElementById("estado-vazio-historico");
    }

    function alternarEstadoVazioHistorico() {
        const lista = getListaHistorico();
        const estadoVazio = getEstadoVazioHistorico();
        if (!lista || !estadoVazio) return;

        const possuiItens = !!lista.querySelector(".item-historico[data-laudo-id]");
        estadoVazio.hidden = possuiItens;
    }

    function atualizarPillStatusItem(item, status, lifecycleStatus = "") {
        if (!item) return;

        const visual = obterStatusVisualCard(status, lifecycleStatus);
        item.dataset.cardStatus = visual.variant;
        item.dataset.caseLifecycleStatus = normalizarCaseLifecycleStatus(lifecycleStatus);

        const pill = item.querySelector(".pill-status-laudo");
        if (!pill) return;

        pill.className = `pill-status-laudo pill-status-${visual.variant}`;
        pill.textContent = visual.label;
    }

    function atualizarPreviewItem(item, preview, horaBr = "") {
        if (!item) return;
        const container = item.querySelector(".texto-laudo-historico");
        if (!container) return;

        let previewEl = container.querySelector(".preview-mensagem");
        if (!previewEl) {
            previewEl = document.createElement("span");
            previewEl.className = "preview-mensagem";
            container.appendChild(previewEl);
        }

        const texto = String(preview || "").trim();
        previewEl.textContent = texto || horaBr || "";
    }

    function criarBotaoAcaoLaudo({ acao, title, icone, pinado = false }) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `btn-acao-laudo ${acao === "pin" ? "btn-pin-laudo" : "btn-deletar-laudo"}`;
        btn.dataset.acaoLaudo = acao;
        btn.title = title;
        btn.setAttribute("aria-label", title);

        if (acao === "pin") {
            btn.setAttribute("aria-pressed", String(!!pinado));
        }

        const icon = document.createElement("span");
        icon.className = "material-symbols-rounded";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = icone;
        btn.appendChild(icon);

        return btn;
    }

    function obterIconeSetor(titulo) {
        const chave = String(titulo || "").trim().toLowerCase();
        if (chave.includes("avcb") || chave.includes("bombeiro")) return "local_fire_department";
        if (chave.includes("nr-12") || chave.includes("nr12")) return "precision_manufacturing";
        if (chave.includes("nr-13") || chave.includes("nr13")) return "warehouse";
        if (chave.includes("rti") || chave.includes("elétrica") || chave.includes("eletrica")) return "bolt";
        if (chave.includes("spda")) return "thunderstorm";
        if (chave.includes("pie")) return "schema";
        if (chave.includes("loto")) return "lock";
        return "history";
    }

    function obterOuCriarSecaoPinados(lista) {
        let secao = document.getElementById("secao-laudos-pinados");
        if (secao) return secao;

        secao = document.createElement("section");
        secao.id = "secao-laudos-pinados";
        secao.className = "secao-pinados";
        secao.dataset.sidebarLaudosSection = "fixados";
        secao.setAttribute("aria-label", "Laudos fixados");
        secao.hidden = true;
        secao.innerHTML = `
            <div class="secao-pinados-titulo">
                <span class="material-symbols-rounded" aria-hidden="true">keep</span>
                Fixados
            </div>
        `;
        lista.appendChild(secao);
        return secao;
    }

    function obterOuCriarSecaoHistorico(lista) {
        let secao = document.getElementById("secao-laudos-historico");
        if (secao) return secao;

        secao = document.createElement("section");
        secao.id = "secao-laudos-historico";
        secao.className = "secao-laudos-historico";
        secao.dataset.sidebarLaudosSection = "recentes";
        secao.setAttribute("aria-label", "Laudos recentes");
        lista.appendChild(secao);
        return secao;
    }

    function obterOuCriarGrupoData(secaoHistorico, dataIso, dataBr) {
        let grupo = secaoHistorico.querySelector(`.grupo-data[data-data="${CSS.escape(String(dataIso))}"]`);
        if (grupo) return grupo.querySelector(".grupo-data-lista");

        grupo = document.createElement("section");
        grupo.className = "grupo-data";
        grupo.dataset.data = String(dataIso || "");
        grupo.innerHTML = `
            <div class="grupo-data-header">${escaparHTMLLocal(dataBr || "")}</div>
            <div class="grupo-data-lista"></div>
        `;

        const grupos = Array.from(secaoHistorico.querySelectorAll(".grupo-data"));
        const existenteMaisNovo = grupos.find((el) => String(el.dataset.data || "") < String(dataIso || ""));
        if (existenteMaisNovo) {
            secaoHistorico.insertBefore(grupo, existenteMaisNovo);
        } else {
            secaoHistorico.appendChild(grupo);
        }

        return grupo.querySelector(".grupo-data-lista");
    }

    function formatarDataIsoBr(dataIso) {
        const valor = String(dataIso || "").trim();
        const partes = valor.split("-");
        if (partes.length === 3) {
            const [ano, mes, dia] = partes;
            return `${dia}/${mes}/${ano}`;
        }
        return new Date().toLocaleDateString("pt-BR");
    }

    function itemHistoricoEhPinado(item) {
        if (!item) return false;

        return (
            item.dataset.pinado === "true" ||
            item.classList.contains("pinado") ||
            item.classList.contains("pinned") ||
            item.classList.contains("laudo-pinado")
        );
    }

    function normalizarEstruturaHistoricoExistente() {
        const lista = getListaHistorico();
        if (!lista) return;

        const itensDiretos = Array.from(lista.children).filter((node) =>
            node?.matches?.(".item-historico[data-laudo-id]")
        );

        if (!itensDiretos.length) {
            normalizarSecoesHistorico(lista);
            alternarEstadoVazioHistorico();
            return;
        }

        itensDiretos.forEach((item) => {
            const dataIso = String(item.dataset.data || "").trim();
            const dataBr = formatarDataIsoBr(dataIso);

            if (itemHistoricoEhPinado(item)) {
                const secaoPinados = obterOuCriarSecaoPinados(lista);
                secaoPinados.hidden = false;
                secaoPinados.appendChild(item);
                return;
            }

            const secaoHistorico = obterOuCriarSecaoHistorico(lista);
            secaoHistorico.hidden = false;
            const grupoLista = obterOuCriarGrupoData(secaoHistorico, dataIso, dataBr);
            grupoLista.appendChild(item);
        });

        normalizarSecoesHistorico(lista);
        alternarEstadoVazioHistorico();
    }

    function normalizarSecoesHistorico(lista) {
        if (!lista) return;

        const secaoPinados = document.getElementById("secao-laudos-pinados");
        if (secaoPinados) {
            secaoPinados.hidden = !secaoPinados.querySelector(".item-historico[data-laudo-id]");
        }

        const secaoHistorico = document.getElementById("secao-laudos-historico");
        if (secaoHistorico) {
            secaoHistorico.querySelectorAll(".grupo-data").forEach((grupo) => {
                if (!grupo.querySelector(".item-historico[data-laudo-id]")) {
                    grupo.remove();
                }
            });
            secaoHistorico.hidden = !secaoHistorico.querySelector(".item-historico[data-laudo-id]");
        }
    }

    function criarItemHistorico(card) {
        const item = document.createElement("div");
        item.className = "inspetor-sidebar-report item-historico";
        item.setAttribute("role", "button");
        item.setAttribute("tabindex", "0");
        item.dataset.laudoId = String(card.id);
        item.dataset.pinado = String(!!card.pinado);
        item.dataset.openThreadTab = "conversa";
        item.dataset.data = String(card.data_iso || "");
        item.dataset.permiteExclusao = String(!!card.permite_exclusao);
        item.dataset.cardStatus = normalizarStatusCard(card.status_card);
        item.dataset.activeOwnerRole = normalizarActiveOwnerRole(card.active_owner_role);
        item.dataset.allowedSurfaceActions = normalizarAllowedSurfaceActions(
            card.allowed_surface_actions
        ).join(",");
        item.dataset.caseLifecycleStatus = normalizarCaseLifecycleStatus(
            card.case_lifecycle_status
        );
        aplicarModoEntradaDataset(item, card);
        item.title = `Abrir laudo ${card.titulo || ""}`.trim();
        item.setAttribute("aria-label", item.title || "Abrir laudo");

        if (card.pinado) {
            item.classList.add("pinado");
        }

        const icon = document.createElement("span");
        icon.className = "material-symbols-rounded inspetor-sidebar-report__icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = obterIconeSetor(card.titulo);

        const texto = document.createElement("span");
        texto.className = "texto-laudo-historico inspetor-sidebar-report__copy";

        const titulo = document.createElement("span");
        titulo.textContent = String(card.titulo || "Inspeção");
        texto.appendChild(titulo);

        const preview = document.createElement("span");
        preview.className = "preview-mensagem";
        preview.textContent = String(card.preview || card.hora_br || "");
        texto.appendChild(preview);
        const metaCanonica = document.createElement("small");
        metaCanonica.className = "meta-canonica-laudo";
        texto.appendChild(metaCanonica);

        const pill = document.createElement("span");
        pill.className = "pill-status-laudo";

        const side = document.createElement("span");
        side.className = "inspetor-sidebar-report__side";

        const actions = document.createElement("span");
        actions.className = "inspetor-sidebar-report__actions";

        const botaoPin = criarBotaoAcaoLaudo({
            acao: "pin",
            title: card.pinado ? "Desafixar laudo" : "Fixar laudo",
            icone: card.pinado ? "keep" : "push_pin",
            pinado: !!card.pinado,
        });
        const botaoDelete = criarBotaoAcaoLaudo({
            acao: "delete",
            title: "Excluir laudo",
            icone: "delete",
        });
        actions.appendChild(botaoPin);
        actions.appendChild(botaoDelete);
        side.appendChild(pill);
        side.appendChild(actions);

        item.appendChild(icon);
        item.appendChild(texto);
        item.appendChild(side);

        atualizarPillStatusItem(item, card.status_card, card.case_lifecycle_status);
        atualizarMetaCanonicaItem(item, card);
        atualizarGovernancaOficialItem(item, card);
        return item;
    }

    function anexarItemHistorico(card) {
        const lista = getListaHistorico();
        if (!lista) return null;

        const item = criarItemHistorico(card);
        if (card.pinado) {
            const secaoPinados = obterOuCriarSecaoPinados(lista);
            secaoPinados.hidden = false;
            const titulo = secaoPinados.querySelector(".secao-pinados-titulo");
            secaoPinados.insertBefore(item, titulo?.nextSibling || null);
        } else {
            const secaoHistorico = obterOuCriarSecaoHistorico(lista);
            secaoHistorico.hidden = false;
            const grupoLista = obterOuCriarGrupoData(secaoHistorico, card.data_iso, card.data_br);
            grupoLista.prepend(item);
        }

        alternarEstadoVazioHistorico();
        return item;
    }

    function sincronizarCardLaudo(card, opts = {}) {
        const { selecionar = false } = opts;
        const id = Number(card?.id || 0);
        if (!id) return null;

        let item = TP.getItemHistoricoPorId(id);
        if (!item) {
            item = anexarItemHistorico(card);
        }
        if (!item) return null;

        item.dataset.pinado = String(!!card.pinado);
        item.dataset.data = String(card.data_iso || item.dataset.data || "");
        item.dataset.permiteExclusao = String(
            typeof card.permite_exclusao === "boolean"
                ? card.permite_exclusao
                : item.dataset.permiteExclusao === "true"
        );
        item.dataset.activeOwnerRole = normalizarActiveOwnerRole(
            card.active_owner_role || item.dataset.activeOwnerRole || ""
        );
        item.dataset.allowedSurfaceActions = normalizarAllowedSurfaceActions(
            Array.isArray(card.allowed_surface_actions)
                ? card.allowed_surface_actions
                : String(item.dataset.allowedSurfaceActions || "")
                    .split(",")
                    .map((itemAcao) => itemAcao.trim())
                    .filter(Boolean)
        ).join(",");
        item.dataset.caseLifecycleStatus = normalizarCaseLifecycleStatus(
            card.case_lifecycle_status || item.dataset.caseLifecycleStatus || ""
        );
        aplicarModoEntradaDataset(item, card);
        item.querySelector(".texto-laudo-historico span:first-child").textContent = String(
            card.titulo || "Inspeção"
        );
        atualizarPreviewItem(item, card.preview, card.hora_br);
        atualizarMetaCanonicaItem(item, {
            ...card,
            active_owner_role: item.dataset.activeOwnerRole,
            allowed_surface_actions: String(item.dataset.allowedSurfaceActions || "")
                .split(",")
                .map((itemAcao) => itemAcao.trim())
                .filter(Boolean),
        });
        atualizarGovernancaOficialItem(item, card);
        atualizarPillStatusItem(
            item,
            card.status_card,
            card.case_lifecycle_status || item.dataset.caseLifecycleStatus || ""
        );

        const icone = item.querySelector(".material-symbols-rounded");
        if (icone) {
            icone.textContent = obterIconeSetor(card.titulo);
        }

        if (!!card.pinado !== item.classList.contains("pinado")) {
            item.classList.toggle("pinado", !!card.pinado);
        }

        if (selecionar) {
            setAtivoNoHistorico(id);
        }

        alternarEstadoVazioHistorico();
        return item;
    }

    function reposicionarItemHistoricoPorPin(laudoId, pinado) {
        const lista = getListaHistorico();
        const item = TP.getItemHistoricoPorId(laudoId);
        if (!lista || !item) return null;

        const dataIso = String(item.dataset.data || "");
        const dataBr = formatarDataIsoBr(dataIso);

        if (pinado) {
            const secaoPinados = obterOuCriarSecaoPinados(lista);
            secaoPinados.hidden = false;
            const titulo = secaoPinados.querySelector(".secao-pinados-titulo");
            secaoPinados.insertBefore(item, titulo?.nextSibling || null);
        } else {
            const secaoHistorico = obterOuCriarSecaoHistorico(lista);
            secaoHistorico.hidden = false;
            const grupoLista = obterOuCriarGrupoData(secaoHistorico, dataIso, dataBr);
            grupoLista.prepend(item);
        }

        normalizarSecoesHistorico(lista);
        alternarEstadoVazioHistorico();
        return item;
    }

    function atualizarBadgeRelatorio(laudoId, status, lifecycleStatus = "") {
        const item = TP.getItemHistoricoPorId(laudoId);
        if (!item) return;
        atualizarPillStatusItem(item, status, lifecycleStatus);
    }

    function limparBadgesRelatorio(status = null) {
        if (!status) return;
        const normalizado = normalizarStatusCard(status);
        TP.qsa(`.item-historico[data-card-status="${normalizado}"]`).forEach((item) => {
            atualizarPillStatusItem(item, "aberto");
        });
    }

    // =========================================================
    // ITEM ATIVO NO HISTÓRICO
    // =========================================================

    function setAtivoNoHistorico(laudoId) {
        TP.limparSelecaoAtual();

        const item = TP.getItemHistoricoPorId(laudoId);
        if (!item) return false;

        item.classList.add("ativo");
        item.setAttribute("aria-current", "true");

        const reduzMovimento = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;

        item.scrollIntoView({
            block: "nearest",
            behavior: reduzMovimento ? "auto" : "smooth",
        });

        return true;
    }

    // =========================================================
    // THREAD NAV
    // =========================================================

    function garantirThreadNav() {
        const nav = TP.qs(".thread-nav");
        if (!nav) {
            if (!STATE_LOCAL.threadNavWarned) {
                STATE_LOCAL.threadNavWarned = true;
                TP.log(
                    "warn",
                    "Toolbar do workspace não encontrada. A partial compartilhada continua sendo a autoridade estrutural de .thread-nav."
                );
            }
            return null;
        }

        if (nav.dataset.threadNavBound !== "true") {
            nav.addEventListener("click", (event) => {
                const btn = event.target.closest(".thread-tab[data-tab]");
                if (!btn) return;

                selecionarThreadTab(btn.dataset.tab || "conversa");
            });
            nav.dataset.threadNavBound = "true";
            STATE_LOCAL.navBound = true;
        }

        return nav;
    }

    function selecionarThreadTab(tab, options = {}) {
        const {
            emit = true,
            persistirURL = true,
            replaceURL = false,
        } = options && typeof options === "object" ? options : {};
        const bruto = String(tab || "conversa").trim().toLowerCase();
        const valor =
            bruto === "chat" ? "conversa"
                : bruto === "history" ? "historico"
                    : bruto === "attachments" ? "anexos"
                        : bruto;
        const nav = garantirThreadNav();
        const tabs = nav?.querySelectorAll(".thread-tab[data-tab]") || [];

        tabs.forEach((btn) => {
            const ativo = btn.dataset.tab === valor;
            btn.classList.toggle("ativo", ativo);
            btn.setAttribute("aria-selected", String(ativo));
        });

        if (typeof window.TarielInspectorState?.sincronizarEstadoInspector === "function") {
            window.TarielInspectorState.sincronizarEstadoInspector({
                threadTab: valor,
            }, {
                persistirStorage: false,
            });
        } else {
            document.body.dataset.threadTab = valor;
        }

        if (emit) {
            TP.emitir("tariel:thread-tab-alterada", {
                tab: valor,
                persistirURL,
                replaceURL,
            });
        }
    }

    function atualizarBreadcrumb(laudoId) {
        void laudoId;
        // Compatibilidade intencional: o topo do workspace agora usa header
        // compartilhado com ação única de Home, sem breadcrumb interno.
    }

    // =========================================================
    // LAUDO INICIAL
    // =========================================================

    function urlSolicitaTelaInicial() {
        try {
            const url = new URL(window.location.href);
            return url.searchParams.get("home") === "1" && !url.searchParams.get("laudo");
        } catch (_) {
            return false;
        }
    }

    function consumirFlagTelaInicial() {
        let viaUrl = false;
        let viaSessao = false;

        try {
            viaUrl = urlSolicitaTelaInicial();
            viaSessao = sessionStorage.getItem("tariel_force_home_landing") === "1";
            if (viaSessao) {
                sessionStorage.removeItem("tariel_force_home_landing");
            }
        } catch (_) {
            // silêncio intencional
        }

        if (viaUrl) {
            try {
                const url = new URL(window.location.href);
                url.searchParams.delete("home");
                history.replaceState(history.state || {}, "", url.toString());
            } catch (_) {
                // silêncio intencional
            }
        }

        const forcarTelaInicial = viaUrl || viaSessao;

        if (typeof window.TarielInspectorState?.sincronizarEstadoInspector === "function") {
            window.TarielInspectorState.sincronizarEstadoInspector({
                forceHomeLanding: forcarTelaInicial,
            }, {
                persistirStorage: false,
            });
        } else {
            document.body.dataset.forceHomeLanding = forcarTelaInicial ? "true" : "false";
        }

        return forcarTelaInicial;
    }

    function obterLaudoInicial() {
        if (consumirFlagTelaInicial()) {
            return "";
        }

        const laudoAutoritativo = Number(
            window.TarielInspectorState?.obterSnapshotEstadoInspectorAtual?.()?.laudoAtualId ||
            window.TarielAPI?.obterLaudoAtualId?.() ||
            TP.state?.laudoAtualId ||
            0
        );
        if (Number.isFinite(laudoAutoritativo) && laudoAutoritativo > 0) {
            return String(laudoAutoritativo);
        }

        return TP.obterLaudoIdDaURL() || "";
    }

    function tentarSelecionarLaudoInicial(laudoId, tentativa = 0) {
        if (!laudoId) return;

        const id = Number(laudoId);
        if (!Number.isFinite(id) || id <= 0) return;

        const apiPronta = document.body.dataset.apiEvents === "wired";

        if (apiPronta) {
            selecionarLaudo(id, {
                atualizarURL: true,
                replaceURL: true,
                origem: "boot",
                ignorarBloqueioRelatorio: true,
                threadTab: TP.obterThreadTabDaURL?.() || "",
                forcarCarregamento: true,
            });
            return;
        }

        if (tentativa >= TP.config.BOOT_RETRIES_MAX) {
            TP.log(
                "warn",
                "API ou item do histórico não ficaram prontos a tempo para carregar o laudo inicial."
            );
            return;
        }

        clearTimeout(STATE_LOCAL.tentativaLaudoInicialTimer);
        STATE_LOCAL.tentativaLaudoInicialTimer = setTimeout(() => {
            tentarSelecionarLaudoInicial(id, tentativa + 1);
        }, TP.config.BOOT_RETRY_MS);
    }

    // =========================================================
    // SELEÇÃO DE LAUDO
    // =========================================================

    function selecionarLaudo(laudoId, opts = {}) {
        const {
            atualizarURL = true,
            replaceURL = false,
            origem = "ui",
            ignorarBloqueioRelatorio = false,
            threadTab = "",
            forcarCarregamento = false,
        } = opts;

        const id = Number(laudoId);
        if (!Number.isFinite(id) || id <= 0) return false;
        void ignorarBloqueioRelatorio;
        const itemHistorico = TP.getItemHistoricoPorId(id);
        const modoEntradaPayload = resolverPayloadModoEntradaSelecao(opts, itemHistorico);
        const threadTabResolvida = String(threadTab || "").trim()
            ? normalizarThreadTabLocal(threadTab, "historico")
            : resolverThreadTabInicialPorModoEntrada(modoEntradaPayload, "historico");
        const laudoApiAtivoAntes = obterLaudoAtivoNaApi();
        const laudoPainelAtivoAntes = Number(TP.state?.laudoAtualId || 0) || null;
        const historicoJaCarregado = !!document.querySelector(".linha-mensagem, .controle-historico-antigo");
        const agora = Date.now();
        const assinaturaSelecao = `${id}:${String(origem || "ui").trim() || "ui"}`;
        const selecaoRecente =
            assinaturaSelecao === STATE_LOCAL.ultimaSelecaoAssinatura
            && (agora - Number(STATE_LOCAL.ultimaSelecaoAt || 0)) < 900;
        const selecaoJaAtiva =
            historicoJaCarregado &&
            (laudoApiAtivoAntes === id || laudoPainelAtivoAntes === id);
        const fluxoJaAtivo = STATE_LOCAL.laudoSelecionadoEmFluxo === id;

        TP.log("info", `Selecionando laudo: ${id}`, { origem });

        if (typeof window.TarielInspectorState?.sincronizarEstadoInspector === "function") {
            window.TarielInspectorState.sincronizarEstadoInspector({
                forceHomeLanding: false,
            });
        } else {
            document.body.dataset.forceHomeLanding = "false";
        }

        definirLaudoAtualNoCore(id);
        selecionarThreadTab(threadTabResolvida, {
            persistirURL: false,
            replaceURL,
        });
        setAtivoNoHistorico(id);
        atualizarBreadcrumb(id);

        if (atualizarURL) {
            TP.definirLaudoIdNaURL(id, {
                replace: replaceURL,
                threadTab: threadTabResolvida,
            });
        }

        fecharSidebarMobile();

        if ((!forcarCarregamento && selecaoJaAtiva) || selecaoRecente || fluxoJaAtivo) {
            PERF?.count?.("chat_painel_laudos.selecao_suprimida", 1, {
                category: "request_churn",
                detail: {
                    laudoId: id,
                    origem,
                    selecaoJaAtiva,
                    selecaoRecente,
                    fluxoJaAtivo,
                    forcarCarregamento,
                },
            });
            return true;
        }

        STATE_LOCAL.laudoSelecionadoEmFluxo = id;
        STATE_LOCAL.ultimaSelecaoAssinatura = assinaturaSelecao;
        STATE_LOCAL.ultimaSelecaoAt = agora;

        TP.emitir("tariel:laudo-selecionado", {
            laudoId: id,
            origem,
            threadTab: threadTabResolvida,
            forcarCarregamento,
            ...modoEntradaPayload,
        });
        window.setTimeout(() => {
            if (STATE_LOCAL.laudoSelecionadoEmFluxo === id) {
                STATE_LOCAL.laudoSelecionadoEmFluxo = null;
            }
        }, 0);

        return true;
    }

    // =========================================================
    // POPSTATE
    // =========================================================

    function wirePopState() {
        if (STATE_LOCAL.popStateBound) return;
        STATE_LOCAL.popStateBound = true;

        window.addEventListener("popstate", (event) => {
            const laudoId = event.state?.laudoId || TP.obterLaudoIdDaURL();
            const threadTab = event.state?.threadTab || TP.obterThreadTabDaURL?.() || "";
            if (!laudoId) return;

            selecionarLaudo(laudoId, {
                atualizarURL: false,
                origem: "popstate",
                ignorarBloqueioRelatorio: true,
                threadTab,
            });
        });
    }

    // =========================================================
    // EVENTOS DE SISTEMA
    // =========================================================

    function wireEventosLaudos() {
        if (STATE_LOCAL.eventosLaudosBound) return;
        STATE_LOCAL.eventosLaudosBound = true;

        document.addEventListener("tariel:laudo-criado", (event) => {
            const laudoId = Number(event.detail?.laudoId || 0);
            if (!laudoId) return;

            setTimeout(() => {
                atualizarBreadcrumb(laudoId);
                definirLaudoAtualNoCore(laudoId);
                TP.definirLaudoIdNaURL(laudoId, {
                    replace: true,
                    threadTab: TP.obterThreadTabDaURL?.() || "conversa",
                });
            }, 350);
        });

        document.addEventListener("tariel:relatorio-iniciado", (event) => {
            const laudoId = Number(event.detail?.laudoId || 0);
            if (!laudoId) return;

            limparBadgesRelatorio("ativo");
            atualizarBadgeRelatorio(laudoId, "ativo");
            definirLaudoAtualNoCore(laudoId);
        });

        document.addEventListener("tariel:relatorio-finalizado", (event) => {
            const laudoId = Number(event.detail?.laudoId || 0);
            const lifecycleStatus =
                event.detail?.case_lifecycle_status ??
                event.detail?.laudo_card?.case_lifecycle_status ??
                "";
            const statusCard =
                event.detail?.status_card ??
                event.detail?.laudo_card?.status_card ??
                "aguardando";

            if (!laudoId) return;

            atualizarBadgeRelatorio(laudoId, statusCard, lifecycleStatus);
        });

        document.addEventListener("tariel:cancelar-relatorio", () => {
            // o card continua existindo normalmente no histórico
        });

        document.addEventListener("tariel:laudo-card-sincronizado", (event) => {
            const card = event.detail?.card;
            if (!card?.id) return;
            sincronizarCardLaudo(card, {
                selecionar: !!event.detail?.selecionar,
            });
        });

        window.addEventListener("pagehide", () => {
            clearTimeout(STATE_LOCAL.tentativaLaudoInicialTimer);
        });
    }

    if (PERF?.enabled) {
        const selecionarThreadTabOriginal = selecionarThreadTab;
        selecionarThreadTab = function selecionarThreadTabComPerf(...args) {
            const bruto = String(args[0] || "conversa").trim().toLowerCase() || "conversa";
            const tab =
                bruto === "chat" ? "conversa"
                    : bruto === "history" ? "historico"
                        : bruto === "attachments" ? "anexos"
                            : bruto;
            PERF.begin(`transition.thread_tab.${tab}`, {
                tab,
            });

            return PERF.measureSync(
                "chat_painel_laudos.selecionarThreadTab",
                () => selecionarThreadTabOriginal.apply(this, args),
                {
                    category: "transition",
                    detail: {
                        tab,
                    },
                }
            );
        };

        const selecionarLaudoOriginal = selecionarLaudo;
        selecionarLaudo = function selecionarLaudoComPerf(...args) {
            const laudoId = Number(args[0] || 0) || null;
            const opts = args[1] && typeof args[1] === "object" ? args[1] : {};
            const origem = String(opts.origem || "ui").trim() || "ui";
            PERF.begin("transition.abrir_laudo", {
                laudoId,
                origem,
            });

            return PERF.measureSync(
                "chat_painel_laudos.selecionarLaudo",
                () => {
                    const resultado = selecionarLaudoOriginal.apply(this, args);
                    if (resultado === false) {
                        PERF.finish("transition.abrir_laudo", {
                            laudoId,
                            origem,
                            failed: true,
                        });
                    }
                    return resultado;
                },
                {
                    category: "transition",
                    detail: {
                        laudoId,
                        origem,
                        atualizarURL: opts.atualizarURL !== false,
                    },
                }
            );
        };
    }

    // =========================================================
    // BOOT
    // =========================================================

    TP.registrarBootTask("chat_painel_laudos", () => {
        const laudoInicial = obterLaudoInicial();
        const abaInicial = TP.obterThreadTabDaURL?.() || (laudoInicial ? "historico" : "conversa");
        garantirThreadNav();
        selecionarThreadTab(abaInicial, {
            emit: false,
            persistirURL: false,
            replaceURL: true,
        });
        wirePopState();
        wireEventosLaudos();
        normalizarEstruturaHistoricoExistente();

        if (!laudoInicial) return true;

        requestAnimationFrame(() => {
            const id = Number(laudoInicial);
            if (!Number.isFinite(id) || id <= 0) return;

            definirLaudoAtualNoCore(id);
            setAtivoNoHistorico(id);
            atualizarBreadcrumb(id);
            tentarSelecionarLaudoInicial(id);
        });

        return true;
    });

    // =========================================================
    // EXPORTS
    // =========================================================

    Object.assign(TP, {
        atualizarBadgeRelatorio,
        limparBadgesRelatorio,
        sincronizarCardLaudo,
        normalizarEstruturaHistoricoExistente,
        setAtivoNoHistorico,
        selecionarThreadTab,
        garantirThreadNav,
        atualizarBreadcrumb,
        obterLaudoInicial,
        selecionarLaudo,
        reposicionarItemHistoricoPorPin,
        wirePopState,
        tentarSelecionarLaudoInicial,
        normalizarEstadoRelatorio,
    });
})();
