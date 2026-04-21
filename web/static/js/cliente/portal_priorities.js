(function () {
    "use strict";

    if (window.TarielClientePortalPriorities) return;

    window.TarielClientePortalPriorities = function createTarielClientePortalPriorities(config = {}) {
        const state = config.state || {};
        const helperFns = config.helpers || {};

        const texto = typeof helperFns.texto === "function" ? helperFns.texto : (valor) => (valor == null ? "" : String(valor));
        const escapeHtml = typeof helperFns.escapeHtml === "function"
            ? helperFns.escapeHtml
            : (valor) => texto(valor)
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;")
                .replaceAll("'", "&#39;");
        const escapeAttr = typeof helperFns.escapeAttr === "function" ? helperFns.escapeAttr : escapeHtml;
        const formatarInteiro = typeof helperFns.formatarInteiro === "function"
            ? helperFns.formatarInteiro
            : (valor) => {
                const numero = Number(valor || 0);
                return Number.isFinite(numero) ? numero.toLocaleString("pt-BR") : "0";
            };
        const formatarPercentual = typeof helperFns.formatarPercentual === "function"
            ? helperFns.formatarPercentual
            : (valor) => {
                if (valor == null || valor === "") return "Ilimitado";
                const numero = Number(valor);
                return Number.isFinite(numero) ? `${numero}%` : "Ilimitado";
            };
        const formatarCapacidadeRestante = typeof helperFns.formatarCapacidadeRestante === "function"
            ? helperFns.formatarCapacidadeRestante
            : (restante, excedente, singular, plural) => {
                const sufixo = Number(restante) === 1 ? singular : plural;
                if (restante == null) return `Sem teto de ${plural}`;
                if (Number(excedente || 0) > 0) {
                    const excesso = Number(excedente || 0);
                    const sufixoExcesso = excesso === 1 ? singular : plural;
                    return `${formatarInteiro(excesso)} ${sufixoExcesso} acima do plano`;
                }
                if (Number(restante) <= 0) return `No limite de ${plural}`;
                return `${formatarInteiro(restante)} ${sufixo} restantes`;
            };
        const formatarLimitePlano = typeof helperFns.formatarLimitePlano === "function"
            ? helperFns.formatarLimitePlano
            : (valor, singular, plural) => {
                if (valor == null || valor === "") return `Sem teto de ${plural}`;
                const numero = Number(valor);
                if (!Number.isFinite(numero)) return `Sem teto de ${plural}`;
                return `${formatarInteiro(numero)} ${numero === 1 ? singular : plural}`;
            };
        const formatarVariacao = typeof helperFns.formatarVariacao === "function"
            ? helperFns.formatarVariacao
            : (valor) => {
                const numero = Number(valor || 0);
                if (!Number.isFinite(numero)) return "0%";
                if (numero > 0) return `+${numero}%`;
                return `${numero}%`;
            };

        function tomCapacidadeEmpresa(empresa) {
            const tone = texto(empresa?.capacidade_tone).trim().toLowerCase();
            if (tone === "aberto" || tone === "aguardando" || tone === "ajustes" || tone === "aprovado") {
                return tone;
            }
            return "aprovado";
        }

        function obterPlanoCatalogo(plano) {
            return (state.bootstrap?.empresa?.planos_catalogo || []).find((item) => texto(item?.plano) === texto(plano)) || null;
        }

        function resumoCanalOperacional(canal) {
            if (canal === "chat") return "Chat";
            if (canal === "mesa") return "Mesa Avaliadora";
            return "Admin";
        }

        function htmlBarrasHistorico(serie, tone) {
            const lista = Array.isArray(serie) ? serie : [];
            const maior = Math.max(...lista.map((item) => Number(item?.total || 0)), 1);
            return `
                <div class="health-bars" data-tone="${escapeAttr(tone || "aberto")}">
                    ${lista.map((item) => {
                        const total = Number(item?.total || 0);
                        const altura = Math.max(10, Math.round((total / maior) * 100));
                        return `
                            <div class="health-bar" title="${escapeAttr(`${item.label}: ${total}`)}">
                                <div class="health-bar-fill${item.atual ? " is-current" : ""}" style="height:${altura}%"></div>
                                <span class="health-bar-value">${escapeHtml(formatarInteiro(total))}</span>
                                <span class="health-bar-label">${escapeHtml(item.label || "")}</span>
                            </div>
                        `;
                    }).join("")}
                </div>
            `;
        }

        function construirPrioridadesPortal() {
            const empresa = state.bootstrap?.empresa;
            const usuarios = state.bootstrap?.usuarios || [];
            const laudosChat = state.bootstrap?.chat?.laudos || [];
            const laudosMesa = state.bootstrap?.mesa?.laudos || [];
            const tenantAdmin = state.bootstrap?.tenant_admin_projection?.payload || null;
            const adminCarregado = Boolean(state.surface?.loaded?.admin);
            const chatCarregado = Boolean(state.surface?.loaded?.chat);
            const mesaCarregada = Boolean(state.surface?.loaded?.mesa);
            const prioridades = [];

            if (!empresa) return prioridades;

            if (empresa.status_bloqueio) {
                prioridades.push({
                    score: 1000,
                    tone: "ajustes",
                    canal: "admin",
                    titulo: "Empresa bloqueada",
                    detalhe: "A operacao central esta bloqueada e isso merece revisao imediata.",
                    acaoLabel: "Abrir Admin",
                    kind: "admin-section",
                    targetId: "empresa-resumo-detalhado",
                });
            }

            if (empresa.capacidade_status === "critico" && texto(empresa.plano_sugerido).trim()) {
                prioridades.push({
                    score: 960,
                    tone: "ajustes",
                    canal: "admin",
                    titulo: "Capacidade comercial no limite",
                    detalhe: empresa.capacidade_acao || "A empresa ja encostou no teto do contrato.",
                    acaoLabel: `Registrar interesse em ${empresa.plano_sugerido}`,
                    kind: "upgrade",
                    origem: empresa.capacidade_gargalo === "laudos" ? "chat" : "admin",
                });
            }

            if (adminCarregado) {
                const primeiroTemporario = ordenarPorPrioridade(
                    usuarios.filter((item) => item?.senha_temporaria_ativa),
                    prioridadeUsuario
                )[0];
                if (primeiroTemporario) {
                    prioridades.push({
                        score: 760,
                        tone: "aguardando",
                        canal: "admin",
                        titulo: "Primeiro acesso pendente",
                        detalhe: `${primeiroTemporario.nome || "Usuario"} ainda precisa concluir a troca de senha para operar.`,
                        acaoLabel: "Revisar equipe",
                        kind: "admin-user",
                        targetId: "lista-usuarios",
                        userId: Number(primeiroTemporario.id),
                        busca: primeiroTemporario.email || primeiroTemporario.nome || "",
                        papel: slugPapel(primeiroTemporario),
                    });
                }

                const primeiroBloqueado = ordenarPorPrioridade(
                    usuarios.filter((item) => !item?.ativo),
                    prioridadeUsuario
                )[0];
                if (primeiroBloqueado) {
                    prioridades.push({
                        score: 720,
                        tone: "ajustes",
                        canal: "admin",
                        titulo: "Acesso bloqueado pede revisao",
                        detalhe: `${primeiroBloqueado.nome || "Usuario"} esta bloqueado e pode estar travando a rotina da empresa.`,
                        acaoLabel: "Abrir equipe",
                        kind: "admin-user",
                        targetId: "lista-usuarios",
                        userId: Number(primeiroBloqueado.id),
                        busca: primeiroBloqueado.email || primeiroBloqueado.nome || "",
                        papel: slugPapel(primeiroBloqueado),
                    });
                }
            } else {
                const totalUsuarios = Number(tenantAdmin?.user_summary?.total_users || 0);
                const usuariosAtivos = Number(tenantAdmin?.user_summary?.active_users || totalUsuarios);
                if (totalUsuarios > usuariosAtivos) {
                    prioridades.push({
                        score: 740,
                        tone: "aguardando",
                        canal: "admin",
                        titulo: "Equipe pede ativacao",
                        detalhe: "Existe diferenca entre contas totais e ativas. Vale revisar acessos, bloqueios ou primeiros logins.",
                        acaoLabel: "Abrir Admin",
                        kind: "admin-section",
                        targetId: "lista-usuarios",
                    });
                }
            }

            if (chatCarregado) {
                const chatUrgente = ordenarPorPrioridade(
                    laudosChat.filter((item) => {
                        const status = variantStatusLaudo(item?.status_card);
                        return status === "ajustes" || status === "aberto" || status === "aguardando";
                    }),
                    prioridadeChat
                )[0];
                if (chatUrgente && prioridadeChat(chatUrgente).tone !== "aprovado") {
                    const prioridade = prioridadeChat(chatUrgente);
                    prioridades.push({
                        score: 680,
                        tone: prioridade.tone,
                        canal: "chat",
                        titulo: chatUrgente.titulo || "Laudo no chat",
                        detalhe: prioridade.acao,
                        acaoLabel: "Abrir laudo",
                        kind: "chat-laudo",
                        laudoId: Number(chatUrgente.id),
                        targetId: "chat-contexto",
                    });
                }
            } else {
                const ajustesChat = Number(tenantAdmin?.review_counts?.sent_back_for_adjustment || 0);
                const chatAbertos = Number(tenantAdmin?.case_counts?.open_cases || 0);
                if (ajustesChat > 0 || chatAbertos > 0) {
                    prioridades.push({
                        score: 670,
                        tone: ajustesChat > 0 ? "ajustes" : "aberto",
                        canal: "chat",
                        titulo: "Fila do chat pede leitura",
                        detalhe: ajustesChat > 0
                            ? `${formatarInteiro(ajustesChat)} caso(s) voltaram para ajuste e merecem triagem no chat.`
                            : `${formatarInteiro(chatAbertos)} caso(s) seguem abertos no canal operacional.`,
                        acaoLabel: "Abrir chat",
                        kind: "chat-section",
                        targetId: "chat-contexto",
                    });
                }
            }

            if (mesaCarregada) {
                const mesaUrgente = ordenarPorPrioridade(
                    laudosMesa.filter((item) => {
                        const prioridade = prioridadeMesa(item);
                        return prioridade.tone !== "aprovado";
                    }),
                    prioridadeMesa
                )[0];
                if (mesaUrgente && prioridadeMesa(mesaUrgente).tone !== "aprovado") {
                    const prioridade = prioridadeMesa(mesaUrgente);
                    prioridades.push({
                        score: 660,
                        tone: prioridade.tone,
                        canal: "mesa",
                        titulo: mesaUrgente.titulo || "Laudo na mesa",
                        detalhe: prioridade.acao,
                        acaoLabel: "Abrir mesa",
                        kind: "mesa-laudo",
                        laudoId: Number(mesaUrgente.id),
                        targetId: "mesa-contexto",
                    });
                }
            } else {
                const pendentesMesa = Number(tenantAdmin?.review_counts?.pending_review || 0);
                const emMesa = Number(tenantAdmin?.review_counts?.in_review || 0);
                if (pendentesMesa > 0 || emMesa > 0) {
                    prioridades.push({
                        score: 650,
                        tone: pendentesMesa > 0 ? "aguardando" : "aberto",
                        canal: "mesa",
                        titulo: "Mesa avaliadora com fila ativa",
                        detalhe: pendentesMesa > 0
                            ? `${formatarInteiro(pendentesMesa)} caso(s) aguardam revisao formal da mesa.`
                            : `${formatarInteiro(emMesa)} caso(s) seguem em revisao ativa pela mesa.`,
                        acaoLabel: "Abrir mesa",
                        kind: "mesa-section",
                        targetId: "mesa-contexto",
                    });
                }
            }

            const resultado = prioridades
                .sort((a, b) => Number(b.score || 0) - Number(a.score || 0))
                .slice(0, 4);

            if (resultado.length) return resultado;

            return [
                {
                    score: 100,
                    tone: "aprovado",
                    canal: "admin",
                    titulo: "Operacao sob controle",
                    detalhe: "Nenhum gargalo critico apareceu agora entre equipe, chat e mesa.",
                    acaoLabel: "Abrir Admin",
                    kind: "admin-section",
                    targetId: "panel-admin",
                },
            ];
        }

        function slugPapel(usuario) {
            const papel = texto(usuario?.papel).toLowerCase();
            if (papel.includes("admin")) return "admin_cliente";
            if (papel.includes("mesa") || papel.includes("revisor")) return "revisor";
            return "inspetor";
        }

        function obterNomePapel(slug) {
            if (slug === "admin_cliente") return "Administrador da empresa";
            if (slug === "revisor") return "Revisao";
            return "Equipe de campo";
        }

        function rotuloSituacaoUsuarios(situacao) {
            if (situacao === "temporarios") return "Primeiros acessos";
            if (situacao === "sem_login") return "Sem login";
            if (situacao === "bloqueados") return "Bloqueados";
            return "";
        }

        function rotuloSituacaoChat(situacao) {
            if (situacao === "ajustes") return "Ação agora";
            if (situacao === "abertos") return "Em operação";
            if (situacao === "aguardando") return "Aguardando mesa";
            if (situacao === "parados") return "Parados";
            if (situacao === "concluidos") return "Concluídos";
            return "";
        }

        function rotuloSituacaoMesa(situacao) {
            if (situacao === "responder") return "Respostas novas";
            if (situacao === "pendencias") return "Pendências abertas";
            if (situacao === "aguardando") return "Pronto para revisar";
            if (situacao === "parados") return "Parados";
            if (situacao === "aprovados") return "Concluídos";
            return "";
        }

        function variantStatusLaudo(status) {
            const valor = texto(status).trim().toLowerCase();
            if (valor === "aguardando" || valor === "ajustes" || valor === "aprovado") {
                return valor;
            }
            return "aberto";
        }

        function parseDataIso(valor) {
            const timestamp = Date.parse(texto(valor));
            return Number.isFinite(timestamp) ? timestamp : 0;
        }

        function horasDesdeAtualizacao(valor) {
            const timestamp = parseDataIso(valor);
            if (!timestamp) return null;
            const diff = Date.now() - timestamp;
            if (!Number.isFinite(diff) || diff < 0) return 0;
            return Math.floor(diff / (1000 * 60 * 60));
        }

        function resumoEsperaHoras(horas) {
            const numero = Number(horas);
            if (!Number.isFinite(numero) || numero <= 0) return "Atualizado agora";
            if (numero < 24) return `Parado ha ${numero}h`;
            const dias = Math.floor(numero / 24);
            return `Parado ha ${dias}d`;
        }

        function laudoChatParado(laudo) {
            const horas = horasDesdeAtualizacao(laudo?.atualizado_em);
            const status = variantStatusLaudo(laudo?.status_card);
            if (horas == null || status === "aprovado") return false;
            return horas >= 48;
        }

        function laudoMesaParado(laudo) {
            const horas = horasDesdeAtualizacao(laudo?.atualizado_em);
            const prioridade = prioridadeMesa(laudo);
            if (horas == null || prioridade.tone === "aprovado") return false;
            return horas >= 24;
        }

        function ordenarPorPrioridade(lista, resolverPrioridade) {
            return [...(Array.isArray(lista) ? lista : [])].sort((a, b) => {
                const prioridadeA = resolverPrioridade(a);
                const prioridadeB = resolverPrioridade(b);
                if (prioridadeB.score !== prioridadeA.score) {
                    return prioridadeB.score - prioridadeA.score;
                }
                return parseDataIso(b?.atualizado_em) - parseDataIso(a?.atualizado_em);
            });
        }

        function prioridadeChat(laudo) {
            const status = variantStatusLaudo(laudo?.status_card);

            if (status === "ajustes") {
                return {
                    score: 400,
                    badge: "Acao agora",
                    tone: "ajustes",
                    acao: "Reabra o laudo e complemente o que a mesa devolveu para ajuste.",
                };
            }

            if (status === "aberto") {
                return {
                    score: 320,
                    badge: "Em operacao",
                    tone: "aberto",
                    acao: "Continue a conversa ou finalize quando o laudo estiver pronto.",
                };
            }

            if (status === "aguardando") {
                return {
                    score: 220,
                    badge: "Aguardando mesa",
                    tone: "aguardando",
                    acao: "Acompanhe o retorno da mesa e prepare a proxima resposta, se necessario.",
                };
            }

            return {
                score: 120,
                badge: "Concluido",
                tone: "aprovado",
                acao: "Sem acao urgente neste laudo agora.",
            };
        }

        function prioridadeMesa(laudo) {
            const pendencias = Number(laudo?.pendencias_abertas || 0);
            const whispers = Number(laudo?.whispers_nao_lidos || 0);
            const status = variantStatusLaudo(laudo?.status_card);

            if (whispers > 0 && pendencias > 0) {
                return {
                    score: 620 + whispers * 12 + pendencias * 8,
                    badge: "Resposta e pendencias",
                    tone: "ajustes",
                    acao: "Leia os chamados novos e trate as pendencias abertas antes da aprovacao.",
                };
            }

            if (whispers > 0) {
                return {
                    score: 560 + whispers * 12,
                    badge: "Responder agora",
                    tone: "aguardando",
                    acao: "Existe retorno novo do time. Responda a mesa antes da fila esfriar.",
                };
            }

            if (pendencias > 0) {
                return {
                    score: 500 + pendencias * 10,
                    badge: "Resolver pendencias",
                    tone: "ajustes",
                    acao: "Feche ou reabra as pendencias tecnicas antes de liberar o laudo.",
                };
            }

            if (status === "aguardando") {
                return {
                    score: 300,
                    badge: "Pronto para revisar",
                    tone: "aguardando",
                    acao: "Avalie este laudo e decida entre aprovar ou devolver para ajustes.",
                };
            }

            if (status === "ajustes") {
                return {
                    score: 240,
                    badge: "Ajustes em campo",
                    tone: "ajustes",
                    acao: "Acompanhe o retorno do time antes da aprovacao final.",
                };
            }

            if (status === "aprovado") {
                return {
                    score: 120,
                    badge: "Concluido",
                    tone: "aprovado",
                    acao: "Sem acao pendente neste laudo.",
                };
            }

            return {
                score: 180,
                badge: "Em preparacao",
                tone: "aberto",
                acao: "O laudo ainda esta sendo preparado pelo time antes da revisao formal.",
            };
        }

        function prioridadeEmpresa(empresa, usuarios) {
            const uso = Number(empresa?.uso_percentual ?? 0);
            const usuariosLista = Array.isArray(usuarios) ? usuarios : [];
            const bloqueados = usuariosLista.filter((item) => !item?.ativo).length;
            const temporarios = usuariosLista.filter((item) => item?.senha_temporaria_ativa).length;
            const capacidadeTone = tomCapacidadeEmpresa(empresa);
            const capacidadeStatus = texto(empresa?.capacidade_status).trim().toLowerCase();
            const sugestaoPlano = texto(empresa?.plano_sugerido).trim();

            if (empresa?.status_bloqueio) {
                return {
                    tone: "ajustes",
                    badge: "Conta bloqueada",
                    acao: "Libere a empresa e revise imediatamente o que esta travando a operacao.",
                };
            }
            if (capacidadeStatus === "critico") {
                return {
                    tone: capacidadeTone,
                    badge: texto(empresa?.capacidade_badge || "Expandir plano agora"),
                    acao: `${texto(empresa?.capacidade_acao || "A empresa chegou no limite contratado.")}${sugestaoPlano ? ` Proximo passo comercial: migrar para ${sugestaoPlano}.` : ""}`,
                };
            }
            if (bloqueados > 0) {
                return {
                    tone: "aguardando",
                    badge: "Revisar acessos bloqueados",
                    acao: "Ha usuarios travados. Confira se isso foi intencional ou se alguem precisa voltar a operar.",
                };
            }
            if (capacidadeStatus === "atencao" || capacidadeStatus === "monitorar") {
                return {
                    tone: capacidadeTone,
                    badge: texto(empresa?.capacidade_badge || "Planejar solicitacao"),
                    acao: `${texto(empresa?.capacidade_acao || "O plano entrou na faixa de atencao.")}${sugestaoPlano ? ` Melhor encaixe agora: ${sugestaoPlano}.` : ""}`,
                };
            }
            if (temporarios > 0 || uso >= 75) {
                return {
                    tone: "aberto",
                    badge: "Acompanhar ativacao",
                    acao: "Existem primeiros acessos pendentes ou o consumo ja entrou na zona de atencao.",
                };
            }
            return {
                tone: "aprovado",
                badge: "Operacao estavel",
                acao: "A empresa esta liberada e a equipe principal ja esta pronta para operar.",
            };
        }

        function prioridadeUsuario(usuario) {
            const papel = slugPapel(usuario);
            const ultimoLogin = parseDataIso(usuario?.ultimo_login);

            if (!usuario?.ativo) {
                return {
                    score: 620,
                    tone: "ajustes",
                    badge: "Acesso bloqueado",
                    acao: "Revise se o bloqueio ainda precisa continuar antes de perder ritmo operacional.",
                };
            }

            if (usuario?.senha_temporaria_ativa) {
                return {
                    score: 560,
                    tone: "aguardando",
                    badge: "Primeiro acesso",
                    acao: "Este usuario ainda precisa concluir a troca obrigatoria de senha.",
                };
            }

            if (!ultimoLogin) {
                return {
                    score: papel === "admin_cliente" ? 500 : 470,
                    tone: "aguardando",
                    badge: "Sem login ainda",
                    acao: "Confirme se a pessoa recebeu o acesso e se ja deveria estar operando.",
                };
            }

            if (papel === "admin_cliente") {
                return {
                    score: 260,
                    tone: "aberto",
                    badge: "Gestao ativa",
                    acao: "Conta administrativa pronta para coordenar empresa, chat e mesa.",
                };
            }

            if (papel === "revisor") {
                return {
                    score: 220,
                    tone: "aberto",
                    badge: "Mesa disponivel",
                    acao: "Usuario de mesa apto para responder chamados, pendencias e aprovacoes.",
                };
            }

            return {
                score: 200,
                tone: "aprovado",
                badge: "Operando",
                acao: "Usuario liberado para tocar o fluxo normal da empresa.",
            };
        }

        function roleBadge(label) {
            return `<span class="pill" data-kind="role">${escapeHtml(label)}</span>`;
        }

        function userStatusBadges(usuario) {
            const badges = [
                `<span class="pill" data-kind="status" data-status="${usuario.ativo ? "ativo" : "bloqueado"}">${usuario.ativo ? "Ativo" : "Bloqueado"}</span>`,
            ];
            if (usuario.senha_temporaria_ativa) {
                badges.push('<span class="pill" data-kind="status" data-status="temporaria">Senha temporaria</span>');
            }
            return badges.join("");
        }

        function laudoBadge(label, status) {
            return `<span class="pill" data-kind="laudo" data-status="${variantStatusLaudo(status)}">${escapeHtml(label || "Sem status")}</span>`;
        }

        function filtrarUsuarios() {
            const usuarios = state.bootstrap?.usuarios || [];
            const busca = state.ui?.usuariosBusca?.trim().toLowerCase() || "";
            const papel = state.ui?.usuariosPapel || "todos";
            const situacao = state.ui?.usuariosSituacao || "";

            return usuarios.filter((usuario) => {
                const combinaPapel = papel === "todos" ? true : slugPapel(usuario) === papel;
                if (!combinaPapel) return false;
                if (situacao === "temporarios" && !usuario.senha_temporaria_ativa) return false;
                if (situacao === "sem_login" && parseDataIso(usuario.ultimo_login)) return false;
                if (situacao === "bloqueados" && usuario.ativo) return false;
                if (!busca) return true;

                const alvo = [
                    usuario.nome,
                    usuario.email,
                    usuario.telefone,
                    usuario.crea,
                    usuario.papel,
                ]
                    .map((item) => texto(item).toLowerCase())
                    .join(" ");
                return alvo.includes(busca);
            });
        }

        function filtrarLaudosChat() {
            const laudos = state.bootstrap?.chat?.laudos || [];
            const busca = state.ui?.chatBusca?.trim().toLowerCase() || "";
            const situacao = state.ui?.chatSituacao || "";

            return laudos.filter((laudo) => {
                const status = variantStatusLaudo(laudo.status_card);
                if (situacao === "ajustes" && status !== "ajustes") return false;
                if (situacao === "abertos" && status !== "aberto") return false;
                if (situacao === "aguardando" && status !== "aguardando") return false;
                if (situacao === "parados" && !laudoChatParado(laudo)) return false;
                if (situacao === "concluidos" && status !== "aprovado") return false;
                if (!busca) return true;

                const alvo = [
                    laudo.titulo,
                    laudo.preview,
                    laudo.status_card_label,
                    laudo.tipo_template_label,
                ]
                    .map((item) => texto(item).toLowerCase())
                    .join(" ");
                return alvo.includes(busca);
            });
        }

        function filtrarLaudosMesa() {
            const laudos = state.bootstrap?.mesa?.laudos || [];
            const busca = state.ui?.mesaBusca?.trim().toLowerCase() || "";
            const situacao = state.ui?.mesaSituacao || "";

            return laudos.filter((laudo) => {
                const prioridade = prioridadeMesa(laudo);
                const status = variantStatusLaudo(laudo.status_card);
                if (situacao === "responder" && Number(laudo?.whispers_nao_lidos || 0) <= 0) return false;
                if (situacao === "pendencias" && Number(laudo?.pendencias_abertas || 0) <= 0) return false;
                if (situacao === "aguardando" && !(status === "aguardando" && Number(laudo?.whispers_nao_lidos || 0) <= 0 && Number(laudo?.pendencias_abertas || 0) <= 0)) return false;
                if (situacao === "parados" && !laudoMesaParado(laudo)) return false;
                if (situacao === "aprovados" && prioridade.tone !== "aprovado") return false;
                if (!busca) return true;

                const alvo = [
                    laudo.titulo,
                    laudo.preview,
                    laudo.status_card_label,
                    laudo.status_visual_label,
                    laudo.status_revisao,
                ]
                    .map((item) => texto(item).toLowerCase())
                    .join(" ");
                return alvo.includes(busca);
            });
        }

        return {
            construirPrioridadesPortal,
            filtrarLaudosChat,
            filtrarLaudosMesa,
            filtrarUsuarios,
            htmlBarrasHistorico,
            horasDesdeAtualizacao,
            laudoBadge,
            laudoChatParado,
            laudoMesaParado,
            obterNomePapel,
            obterPlanoCatalogo,
            ordenarPorPrioridade,
            parseDataIso,
            prioridadeChat,
            prioridadeEmpresa,
            prioridadeMesa,
            prioridadeUsuario,
            resumoCanalOperacional,
            resumoEsperaHoras,
            roleBadge,
            rotuloSituacaoChat,
            rotuloSituacaoMesa,
            rotuloSituacaoUsuarios,
            slugPapel,
            tomCapacidadeEmpresa,
            userStatusBadges,
            variantStatusLaudo,
        };
    };
})();
