import { Platform } from "react-native";

import {
  APP_BUILD_CHANNEL,
  APP_VERSION_LABEL,
  HELP_CENTER_ARTICLES,
  HISTORY_DRAWER_FILTERS,
} from "../InspectorMobileApp.constants";
import {
  resolverAllowedSurfaceActions,
  hasCaseSurfaceAction,
  resolverCaseLifecycleStatus,
  resolverCaseOwnerRole,
  resumirCaseSurfaceActions,
  rotuloCaseLifecycle,
  rotuloCaseOwnerRole,
} from "../chat/caseLifecycle";
import { buildReportPackDraftSummary } from "../chat/reportPackHelpers";
import {
  SETTINGS_DRAWER_PAGE_META,
  SETTINGS_DRAWER_SECTION_META,
  type SettingsDrawerPage,
  type SettingsSectionKey,
} from "../settings/settingsNavigationMeta";
import { buildSettingsSectionVisibility } from "../settings/settingsSectionVisibility";
import {
  buildMobileAccessSummary,
  filterHelpArticlesByMobileAccess,
  filterNotificationsByMobileAccess,
  filterOfflineQueueByMobileAccess,
  hasMobileUserPortal,
  buildMobileWorkspaceSummary,
} from "./mobileUserAccess";
import { summarizeOfflinePendingQueueV1 } from "../offline/offlineSyncObservability";
import { buildGuidedInspectionPlaceholder } from "../inspection/guidedInspection";
import type {
  InspectorConversationDerivedStateInput,
  InspectorHistoryAndOfflineDerivedStateInput,
  InspectorLayoutDerivedStateInput,
  InspectorSettingsDerivedStateResolvedInput,
} from "./inspectorDerivedStateTypes";
import type { SessionModalsStackFilter } from "./SessionModalsStack";
import { colors, spacing } from "../../theme/tokens";

export function buildInspectorConversationDerivedState(
  input: InspectorConversationDerivedStateInput,
) {
  const {
    anexoMesaRascunho,
    anexoRascunho,
    arquivosPermitidos,
    abaAtiva,
    colorScheme,
    conversa,
    corDestaque,
    densidadeInterface,
    formatarTipoTemplateLaudo,
    guidedInspectionDraft,
    mensagem,
    mensagemMesa,
    mensagensMesa,
    obterEscalaDensidade,
    obterEscalaFonte,
    podeEditarConversaNoComposer,
    preparandoAnexo,
    previewChatLiberadoParaConversa,
    session,
    tamanhoFonte,
    temaApp,
    uploadArquivosAtivo,
    carregandoConversa,
    carregandoMesa,
    enviandoMensagem,
    enviandoMesa,
  } = input;

  const conversaAtiva = conversa;
  const vendoMesa = abaAtiva === "mesa";
  const vendoFinalizacao = abaAtiva === "finalizar";
  const mensagensVisiveis = conversaAtiva?.mensagens || [];
  const mesaAcessoPermitido = hasMobileUserPortal(
    session?.bootstrap.usuario,
    "revisor",
  );
  const mesaDisponivel = Boolean(conversaAtiva?.laudoId);
  const mesaTemMensagens = mesaAcessoPermitido && Boolean(mensagensMesa.length);
  const previewChatLiberado = previewChatLiberadoParaConversa(conversaAtiva);
  const podeEditarConversa = podeEditarConversaNoComposer(conversaAtiva);
  const caseLifecycleStatus = resolverCaseLifecycleStatus({
    conversation: conversaAtiva,
  });
  const activeOwnerRole = resolverCaseOwnerRole({
    conversation: conversaAtiva,
    lifecycleStatus: caseLifecycleStatus,
  });
  const canChatReopen = hasCaseSurfaceAction({
    conversation: conversaAtiva,
    lifecycleStatus: caseLifecycleStatus,
    ownerRole: activeOwnerRole,
    action: "chat_reopen",
  });
  const placeholderComposer =
    canChatReopen && !previewChatLiberado
      ? caseLifecycleStatus === "emitido"
        ? "Reabra o documento emitido para iniciar um novo ciclo."
        : "Reabra o laudo para continuar."
      : guidedInspectionDraft
        ? anexoRascunho
          ? "Adicione um contexto curto para acompanhar a evidência."
          : buildGuidedInspectionPlaceholder(guidedInspectionDraft)
        : activeOwnerRole === "mesa" && conversaAtiva && !podeEditarConversa
          ? "Caso sob revisão da mesa avaliadora."
          : conversaAtiva && !podeEditarConversa
            ? "Laudo em modo leitura."
            : anexoRascunho
              ? "Adicione contexto opcional para ajudar a IA na analise e no relatorio..."
              : conversaAtiva?.laudoId
                ? "Descreva o item, envie foto ou documento para a IA analisar..."
                : "Primeiro envio cria o caso: descreva o item, envie foto ou documento para a IA analisar...";
  const placeholderMesa = !mesaTemMensagens
    ? !mesaAcessoPermitido
      ? "Seu acesso atual no app não inclui a mesa avaliadora."
      : "Aguardando retorno da mesa."
    : canChatReopen
      ? caseLifecycleStatus === "emitido"
        ? "Reabra o caso antes de abrir um novo ciclo com a mesa."
        : "Reabra o caso e ajuste no chat antes de responder à mesa."
      : activeOwnerRole !== "mesa"
        ? "A mesa só recebe respostas quando a etapa dela estiver ativa."
        : conversaAtiva && !conversaAtiva.permiteEdicao
          ? "Laudo em modo leitura."
          : "Escreva uma resposta objetiva para a mesa...";
  const podeAcionarComposer =
    podeEditarConversa &&
    !enviandoMensagem &&
    !carregandoConversa &&
    !preparandoAnexo;
  const podeEnviarComposer = Boolean(
    (mensagem.trim() || anexoRascunho) && podeAcionarComposer,
  );
  const podeUsarComposerMesa =
    Boolean(
      mesaAcessoPermitido && mesaTemMensagens && conversaAtiva?.permiteEdicao,
    ) &&
    !enviandoMesa &&
    !carregandoMesa;
  const podeEnviarMesa = Boolean(
    (mensagemMesa.trim() || anexoMesaRascunho) && podeUsarComposerMesa,
  );
  const fontScale = obterEscalaFonte(tamanhoFonte);
  const densityScale = obterEscalaDensidade(densidadeInterface);
  const accentColor =
    corDestaque === "azul"
      ? "#3366FF"
      : corDestaque === "roxo"
        ? "#7C4DFF"
        : corDestaque === "personalizado"
          ? "#008F7A"
          : colors.accent;
  const temaEfetivo =
    temaApp === "automático"
      ? colorScheme === "dark"
        ? "escuro"
        : "claro"
      : temaApp;
  const appGradientColors: readonly [string, string, ...string[]] =
    temaEfetivo === "escuro"
      ? (["#0B141E", "#121F2D"] as const)
      : ([colors.surfaceCanvas, colors.surfaceSoft, colors.surface] as const);
  const settingsPrintDarkMode = temaEfetivo === "escuro";
  const podeAbrirAnexosChat =
    podeAcionarComposer && uploadArquivosAtivo && arquivosPermitidos;
  const podeAbrirAnexosMesa =
    mesaAcessoPermitido &&
    podeUsarComposerMesa &&
    uploadArquivosAtivo &&
    arquivosPermitidos;
  const dynamicComposerInputStyle = {
    fontSize: 16 * fontScale,
    lineHeight: 22 * fontScale,
    minHeight: 52 * densityScale,
    paddingVertical: Math.max(10, 12 * densityScale),
  };
  const dynamicMessageTextStyle = {
    fontSize: 15 * fontScale,
    lineHeight: 24 * fontScale,
  };
  const dynamicMessageBubbleStyle = {
    paddingHorizontal: 16 * densityScale,
    paddingVertical: 14 * densityScale,
  };
  const laudoSelecionadoId = conversaAtiva?.laudoId ?? null;
  const conversaVazia =
    !vendoMesa &&
    !vendoFinalizacao &&
    !conversaAtiva?.laudoId &&
    !conversaAtiva?.mensagens.length;
  const tipoTemplateAtivoLabel = formatarTipoTemplateLaudo(
    conversaAtiva?.laudoCard?.tipo_template,
  );

  return {
    accentColor,
    appGradientColors,
    conversaAtiva,
    conversaVazia,
    densityScale,
    dynamicComposerInputStyle,
    dynamicMessageBubbleStyle,
    dynamicMessageTextStyle,
    fontScale,
    laudoSelecionadoId,
    mesaAcessoPermitido,
    mesaDisponivel,
    mesaTemMensagens,
    mesaIndisponivelDescricao: mesaAcessoPermitido
      ? "Envie o primeiro registro no chat para criar o caso e liberar este espaço."
      : "O pacote e as permissões atuais desta conta não incluem a mesa avaliadora no app.",
    mesaIndisponivelTitulo: mesaAcessoPermitido
      ? "Mesa disponível após o primeiro laudo"
      : "Mesa indisponível para esta conta",
    mensagensVisiveis,
    placeholderComposer,
    placeholderMesa,
    podeAbrirAnexosChat,
    podeAbrirAnexosMesa,
    podeAcionarComposer,
    podeEditarConversa,
    podeEnviarComposer,
    podeEnviarMesa,
    podeUsarComposerMesa,
    previewChatLiberado,
    settingsPrintDarkMode,
    temaEfetivo,
    tipoTemplateAtivoLabel,
    vendoFinalizacao,
    vendoMesa,
  };
}

export function buildInspectorHistoryAndOfflineDerivedState(
  input: InspectorHistoryAndOfflineDerivedStateInput,
) {
  const {
    buscaHistorico,
    buildHistorySections,
    filaOffline,
    filtroFilaOffline,
    filtroHistorico,
    fixarConversas,
    historicoOcultoIds,
    laudosDisponiveis,
    notificacoes,
    pendenciaFilaProntaParaReenvio,
    prioridadePendenciaOffline,
    session,
    statusApi,
  } = input;

  const filaOfflineVisivel = filterOfflineQueueByMobileAccess(
    filaOffline,
    session?.bootstrap.usuario,
  );
  const notificacoesVisiveis = filterNotificationsByMobileAccess(
    notificacoes,
    session?.bootstrap.usuario,
  );

  const offlineQueueSummary = summarizeOfflinePendingQueueV1({
    offlineQueue: filaOfflineVisivel,
    isItemReadyForRetry: pendenciaFilaProntaParaReenvio,
    getPriority: prioridadePendenciaOffline,
  });
  const filaOfflineOrdenada = offlineQueueSummary.ordered_items;
  const totalFilaOfflineFalha = offlineQueueSummary.queue_totals.failed_items;
  const totalFilaOfflinePronta = offlineQueueSummary.queue_totals.ready_items;
  const totalFilaOfflineEmEspera =
    offlineQueueSummary.queue_totals.backoff_items;
  const totalFilaOfflineChat = offlineQueueSummary.queue_totals.chat_items;
  const totalFilaOfflineMesa = offlineQueueSummary.queue_totals.mesa_items;
  const filtrosFilaOffline: SessionModalsStackFilter[] = [
    { key: "all", label: "Tudo", count: filaOfflineOrdenada.length },
    { key: "chat", label: "Chat", count: totalFilaOfflineChat },
    { key: "mesa", label: "Mesa", count: totalFilaOfflineMesa },
  ];
  const filaOfflineFiltrada =
    filtroFilaOffline === "all"
      ? filaOfflineOrdenada
      : filaOfflineOrdenada.filter(
          (item) => item.channel === filtroFilaOffline,
        );
  const chipsResumoFilaOffline = [
    {
      key: "falha",
      label: "Falha",
      count: totalFilaOfflineFalha,
      tone: "danger" as const,
    },
    {
      key: "pronta",
      label: "Prontas",
      count: totalFilaOfflinePronta,
      tone: "accent" as const,
    },
    {
      key: "espera",
      label: "Backoff",
      count: totalFilaOfflineEmEspera,
      tone: "muted" as const,
    },
  ].filter((item) => item.count > 0);
  const termoHistorico = buscaHistorico.trim().toLowerCase();
  const termoHistoricoEhIdExato = /^\d+$/.test(termoHistorico);
  const laudosOrdenadosHistorico = [...laudosDisponiveis].sort(
    (a, b) => new Date(b.data_iso).getTime() - new Date(a.data_iso).getTime(),
  );
  const existeMatchExatoPorId =
    termoHistoricoEhIdExato &&
    laudosOrdenadosHistorico.some((item) => String(item.id) === termoHistorico);
  const historicoFiltrado = laudosOrdenadosHistorico.filter((item) => {
    if (!termoHistorico) {
      return true;
    }
    if (existeMatchExatoPorId) {
      return String(item.id) === termoHistorico;
    }
    const lifecycleStatus = resolverCaseLifecycleStatus({ card: item });
    const ownerRole = resolverCaseOwnerRole({
      card: item,
      lifecycleStatus,
    });
    const actionSummary = resumirCaseSurfaceActions(
      resolverAllowedSurfaceActions({
        card: item,
        lifecycleStatus,
        ownerRole,
      }),
      2,
    );
    const reportPackSummary = buildReportPackDraftSummary(
      item.report_pack_draft,
    );
    const alvo = [
      item.titulo,
      item.preview,
      item.status_card_label,
      rotuloCaseLifecycle(lifecycleStatus),
      rotuloCaseOwnerRole(ownerRole),
      actionSummary,
      reportPackSummary?.readinessLabel,
      reportPackSummary?.finalValidationModeLabel,
      reportPackSummary?.templateLabel,
      reportPackSummary?.inspectionContextLabel,
      reportPackSummary?.inspectionContextDetail,
      reportPackSummary?.totalBlocks
        ? `${reportPackSummary.readyBlocks}/${reportPackSummary.totalBlocks} blocos`
        : "",
      item.official_issue_summary?.label,
      item.official_issue_summary?.detail,
      item.official_issue_summary?.issue_number,
      item.official_issue_summary?.primary_pdf_storage_version,
      item.official_issue_summary?.current_primary_pdf_storage_version,
      item.id,
    ]
      .join(" ")
      .toLowerCase();
    return alvo.includes(termoHistorico);
  });
  const conversasFixadasTotal = laudosDisponiveis.filter(
    (item) => item.pinado,
  ).length;
  const conversasVisiveisTotal = laudosDisponiveis.length;
  const conversasOcultasTotal = historicoOcultoIds.length;
  const agoraReferenciaHistorico = Date.now();
  const totalHistoricoRecentes = laudosDisponiveis.filter((item) => {
    const timestamp = new Date(item.data_iso).getTime();
    if (Number.isNaN(timestamp)) {
      return false;
    }
    return agoraReferenciaHistorico - timestamp <= 7 * 24 * 60 * 60 * 1000;
  }).length;
  const historicoBase = historicoFiltrado.filter((item) => {
    if (filtroHistorico === "fixadas") {
      return item.pinado;
    }
    if (filtroHistorico === "recentes") {
      const timestamp = new Date(item.data_iso).getTime();
      return (
        !Number.isNaN(timestamp) &&
        agoraReferenciaHistorico - timestamp <= 7 * 24 * 60 * 60 * 1000
      );
    }
    return true;
  });
  const historicoAgrupadoFinal = buildHistorySections(
    fixarConversas
      ? [...historicoBase].sort((a, b) => Number(b.pinado) - Number(a.pinado))
      : historicoBase,
  );
  const filtrosHistoricoComContagem = HISTORY_DRAWER_FILTERS.map((item) => ({
    ...item,
    count:
      item.key === "fixadas"
        ? conversasFixadasTotal
        : item.key === "recentes"
          ? totalHistoricoRecentes
          : conversasVisiveisTotal,
  }));
  const resumoHistoricoDrawer =
    filtroHistorico === "fixadas"
      ? `${conversasFixadasTotal} conversa${conversasFixadasTotal === 1 ? "" : "s"} fixada${conversasFixadasTotal === 1 ? "" : "s"}`
      : filtroHistorico === "recentes"
        ? `${totalHistoricoRecentes} conversa${totalHistoricoRecentes === 1 ? "" : "s"} recente${totalHistoricoRecentes === 1 ? "" : "s"}`
        : `${conversasVisiveisTotal} conversa${conversasVisiveisTotal === 1 ? "" : "s"} visíve${conversasVisiveisTotal === 1 ? "l" : "is"}`;
  const historicoVazioTitulo = buscaHistorico.trim()
    ? "Nada encontrado"
    : filtroHistorico === "fixadas"
      ? "Nenhum laudo fixado"
      : filtroHistorico === "recentes"
        ? "Nada recente"
        : "Nenhum histórico ainda";
  const historicoVazioTexto = buscaHistorico.trim()
    ? "Tente outro termo."
    : filtroHistorico === "fixadas"
      ? "Fixe os mais importantes para retomar rápido."
      : filtroHistorico === "recentes"
        ? "Novos laudos aparecem aqui automaticamente."
        : "Inicie um laudo para vê-lo aqui.";
  const resumoFilaOffline = !filaOfflineOrdenada.length
    ? ""
    : filaOfflineOrdenada.length === 1
      ? `1 envio pendente${statusApi === "offline" ? " aguardando conexão" : totalFilaOfflinePronta ? " pronto para reenviar" : " em backoff"}`
      : `${filaOfflineOrdenada.length} envios pendentes${statusApi === "offline" ? " aguardando conexão" : totalFilaOfflineFalha ? ` (${totalFilaOfflineFalha} com falha)` : totalFilaOfflineEmEspera && totalFilaOfflinePronta ? ` (${totalFilaOfflinePronta} prontos, ${totalFilaOfflineEmEspera} em backoff)` : totalFilaOfflinePronta ? " prontos para reenviar" : " em backoff"}`;
  const resumoFilaOfflineFiltrada =
    filtroFilaOffline === "all"
      ? resumoFilaOffline
      : filaOfflineFiltrada.length
        ? `${filaOfflineFiltrada.length} pendência${filaOfflineFiltrada.length > 1 ? "s" : ""} ${filaOfflineFiltrada.length > 1 ? "visíveis" : "visível"} em ${filtroFilaOffline === "chat" ? "Chat" : "Mesa"}`
        : `Nenhuma pendência em ${filtroFilaOffline === "chat" ? "Chat" : "Mesa"}`;
  const podeSincronizarFilaOffline =
    statusApi === "online" && totalFilaOfflinePronta > 0;
  const notificacoesNaoLidas = notificacoesVisiveis.filter(
    (item) => item.unread,
  ).length;

  return {
    chipsResumoFilaOffline,
    conversasFixadasTotal,
    conversasOcultasTotal,
    conversasVisiveisTotal,
    filaOfflineFiltrada,
    filaOfflineOrdenada,
    filtrosFilaOffline,
    filtrosHistoricoComContagem,
    historicoAgrupadoFinal,
    historicoFiltrado,
    historicoVazioTexto,
    historicoVazioTitulo,
    notificacoesNaoLidas,
    podeSincronizarFilaOffline,
    resumoFilaOffline,
    resumoFilaOfflineFiltrada,
    resumoHistoricoDrawer,
    totalFilaOfflineChat,
    totalFilaOfflineEmEspera,
    totalFilaOfflineFalha,
    totalFilaOfflineMesa,
    totalFilaOfflinePronta,
  };
}

export function buildInspectorSettingsDerivedState(
  input: InspectorSettingsDerivedStateResolvedInput,
) {
  const {
    arquivosPermitidos,
    buscaAjuda,
    buscaConfiguracoes,
    cameraPermitida,
    codigosRecuperacao,
    contaTelefone,
    corDestaque,
    densidadeInterface,
    email,
    emailAtualConta,
    estiloResposta,
    eventosSeguranca,
    filaSuporteLocal,
    filtroConfiguracoes,
    filtroEventosSeguranca,
    formatarHorarioAtividade,
    formatarTipoTemplateLaudo,
    idiomaResposta,
    integracoesExternas,
    lockTimeout,
    microfonePermitido,
    modeloIa,
    mostrarConteudoNotificacao,
    mostrarSomenteNovaMensagem,
    notificacoesPermitidas,
    ocultarConteudoBloqueado,
    perfilExibicao,
    perfilNome,
    planoAtual,
    laudosDisponiveis,
    provedoresConectados,
    reautenticacaoStatus,
    recoveryCodesEnabled,
    salvarHistoricoConversas,
    session,
    settingsDrawerPage,
    settingsDrawerSection,
    sessoesAtivas,
    somNotificacao,
    statusAtualizacaoApp,
    temaApp,
    twoFactorEnabled,
    twoFactorMethod,
    ultimaVerificacaoAtualizacao,

    conversasFixadasTotal,
    conversasVisiveisTotal,
    temaEfetivo,
  } = input;

  const nomeUsuarioExibicao =
    perfilExibicao.trim() || perfilNome.trim() || "Você";
  const perfilNomeCompleto = perfilNome.trim() || "Inspetor Tariel";
  const perfilExibicaoLabel = perfilExibicao.trim() || perfilNomeCompleto;
  const contaEmailLabel = emailAtualConta || email || "Sem email cadastrado";
  const contaTelefoneLabel =
    contaTelefone?.trim() ||
    session?.bootstrap.usuario.telefone?.trim() ||
    "Não informado";
  const iniciaisPerfilConfiguracao =
    nomeUsuarioExibicao
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((parte: string) => parte.charAt(0).toUpperCase())
      .join("") || "TU";
  const temaResumoConfiguracao =
    temaApp === "automático"
      ? `Sistema (${temaEfetivo === "escuro" ? "Escuro" : "Claro"})`
      : temaApp === "claro"
        ? "Claro"
        : "Escuro";
  const corDestaqueResumoConfiguracao =
    corDestaque === "laranja"
      ? "Padrão"
      : formatarTipoTemplateLaudo(corDestaque);
  const planoResumoConfiguracao = planoAtual === "Pro" ? "Plus" : planoAtual;
  const workspaceResumoConfiguracao = buildMobileWorkspaceSummary(
    session?.bootstrap.usuario,
  );
  const resumoContaAcesso = buildMobileAccessSummary(
    session?.bootstrap.usuario,
  );
  const reemissoesRecomendadasTotal = (laudosDisponiveis ?? []).filter(
    (item) => item.official_issue_summary?.primary_pdf_diverged,
  ).length;
  const resumoGovernancaConfiguracao = reemissoesRecomendadasTotal
    ? `${reemissoesRecomendadasTotal} caso${reemissoesRecomendadasTotal === 1 ? "" : "s"} com reemissão recomendada`
    : "Nenhum caso com reemissão recomendada";
  const detalheGovernancaConfiguracao = reemissoesRecomendadasTotal
    ? `PDF oficial divergente em ${reemissoesRecomendadasTotal} caso${reemissoesRecomendadasTotal === 1 ? "" : "s"} disponível${reemissoesRecomendadasTotal === 1 ? "" : "is"} no mobile.`
    : "Nenhum PDF oficial divergente nos casos disponíveis no mobile.";
  const provedoresConectadosTotal = provedoresConectados.filter(
    (item) => item.connected,
  ).length;
  const provedoresDisponiveisTotal = provedoresConectados.filter(
    (item) => !item.connected,
  ).length;
  const integracoesConectadasTotal = integracoesExternas.filter(
    (item) => item.connected,
  ).length;
  const integracoesDisponiveisTotal = integracoesExternas.length;
  const existeProvedorDisponivel = provedoresDisponiveisTotal > 0;
  const provedorPrimario = session ? "Senha" : "Credencial principal";
  const ultimoEventoProvedor =
    eventosSeguranca.find((item) => item.type === "provider")?.status ||
    "Sem vínculo recente";
  const ultimoEventoSessao =
    eventosSeguranca.find(
      (item) => item.type === "session" || item.type === "login",
    )?.status || "Sem revisão recente";
  const sessaoAtual = sessoesAtivas.find((item) => item.current) || null;
  const outrasSessoesAtivas = sessoesAtivas.filter((item) => !item.current);
  const sessoesSuspeitasTotal = sessoesAtivas.filter(
    (item) => item.suspicious,
  ).length;
  const resumoMetodosConta =
    provedoresConectadosTotal > 0
      ? `${provedoresConectadosTotal} método${provedoresConectadosTotal > 1 ? "s" : ""} conectado${provedoresConectadosTotal > 1 ? "s" : ""}`
      : "Somente credencial principal";
  const resumoAlertaMetodosConta =
    provedoresConectadosTotal <= 1
      ? "Cadastre outro método antes de remover o acesso atual."
      : `${provedoresDisponiveisTotal} provedor(es) ainda podem ser vinculados a esta conta.`;
  const resumoSessaoAtual = sessaoAtual
    ? `${sessaoAtual.title} • ${sessaoAtual.location}`
    : "Nenhuma sessão ativa identificada";
  const resumoBlindagemSessoes = sessoesSuspeitasTotal
    ? `${sessoesSuspeitasTotal} sessão(ões) marcadas como suspeitas pedem revisão imediata.`
    : "Nenhuma sessão suspeita no momento. O acesso está consistente entre os dispositivos.";
  const resumoDadosConversas = salvarHistoricoConversas
    ? `${conversasVisiveisTotal} conversa${conversasVisiveisTotal === 1 ? "" : "s"} visíve${conversasVisiveisTotal === 1 ? "l" : "is"} • ${conversasFixadasTotal} fixada${conversasFixadasTotal === 1 ? "" : "s"}`
    : "Histórico desativado para novas conversas";
  const resumo2FAStatus = twoFactorEnabled
    ? `${twoFactorMethod} ativo`
    : "Proteção adicional desativada";
  const resumo2FAFootnote = twoFactorEnabled
    ? `A conta exige ${twoFactorMethod} para ações sensíveis e logins protegidos.`
    : "Ative o 2FA para elevar a proteção da conta e reduzir risco de acesso indevido.";
  const resumoCodigosRecuperacao = recoveryCodesEnabled
    ? codigosRecuperacao.length
      ? `${codigosRecuperacao.length} códigos gerados`
      : "Pronto para gerar códigos"
    : "Códigos desativados";
  const permissoesReais = [
    microfonePermitido,
    cameraPermitida,
    arquivosPermitidos,
    notificacoesPermitidas,
  ];
  const permissoesNegadasTotal = permissoesReais.filter((item) => !item).length;
  const permissoesAtivasTotal = permissoesReais.filter(Boolean).length;
  const resumoPermissoes = `${permissoesAtivasTotal} de ${permissoesReais.length} permissões liberadas`;
  const resumoPermissoesCriticas = permissoesNegadasTotal
    ? `${permissoesNegadasTotal} permissão(ões) ainda precisam de revisão`
    : "Todas as permissões principais já estão liberadas";
  const resumoPrivacidadeNotificacoes = mostrarSomenteNovaMensagem
    ? 'Somente "Nova mensagem" aparece nas notificações.'
    : ocultarConteudoBloqueado
      ? "Prévia bloqueada na tela bloqueada."
      : mostrarConteudoNotificacao
        ? "Prévia completa habilitada quando o sistema permitir."
        : "Notificações com prévia reduzida.";
  const previewPrivacidadeNotificacao = mostrarSomenteNovaMensagem
    ? "Assistente • Nova mensagem"
    : !mostrarConteudoNotificacao || ocultarConteudoBloqueado
      ? "Assistente • Mensagem protegida"
      : "Assistente • Laudo 204 precisa de revisão da mesa";
  const resumoExcluirConta = `${sessoesAtivas.length} sessões serão invalidadas • ${conversasVisiveisTotal} conversas visíveis nesta conta`;
  const resumoSuporteApp = `${APP_VERSION_LABEL} • ${APP_BUILD_CHANNEL}`;
  const ultimaVerificacaoAtualizacaoLabel = ultimaVerificacaoAtualizacao
    ? formatarHorarioAtividade(ultimaVerificacaoAtualizacao)
    : "Nunca verificado";
  const resumoAtualizacaoApp = ultimaVerificacaoAtualizacao
    ? `${ultimaVerificacaoAtualizacaoLabel} • ${statusAtualizacaoApp}`
    : statusAtualizacaoApp;
  const artigosAjudaDisponiveis = filterHelpArticlesByMobileAccess(
    HELP_CENTER_ARTICLES,
    session?.bootstrap.usuario,
  );
  const artigosAjudaFiltrados = artigosAjudaDisponiveis.filter((article) => {
    const termo = buscaAjuda.trim().toLowerCase();
    if (!termo) {
      return true;
    }
    const alvo =
      `${article.title} ${article.category} ${article.summary} ${article.body}`.toLowerCase();
    return alvo.includes(termo);
  });
  const ultimoTicketSuporte = filaSuporteLocal[0] || null;
  const ultimoTicketSuporteResumo = ultimoTicketSuporte
    ? {
        kind: ultimoTicketSuporte.kind,
        createdAtLabel: formatarHorarioAtividade(ultimoTicketSuporte.createdAt),
      }
    : null;
  const ticketsBugTotal = filaSuporteLocal.filter(
    (item) => item.kind === "bug",
  ).length;
  const ticketsFeedbackTotal = filaSuporteLocal.filter(
    (item) => item.kind === "feedback",
  ).length;
  const ticketsComAnexoTotal = filaSuporteLocal.filter((item) =>
    Boolean(item.attachmentUri),
  ).length;
  const resumoFilaSuporteLocal = filaSuporteLocal.length
    ? `${filaSuporteLocal.length} item(ns) locais • ${ticketsBugTotal} bug(s) • ${ticketsFeedbackTotal} feedback(s) • ${ticketsComAnexoTotal} com anexo`
    : "Sem itens na fila local";
  const temPrioridadesConfiguracao = permissoesNegadasTotal > 0;
  const eventosSegurancaFiltrados = eventosSeguranca.filter((item) => {
    if (filtroEventosSeguranca === "todos") {
      return true;
    }
    if (filtroEventosSeguranca === "críticos") {
      return item.critical;
    }
    return item.type === "login" || item.type === "session";
  });
  const {
    buscaConfiguracoesNormalizada,
    mostrarSecaoConfiguracao,
    mostrarGrupoContaAcesso,
    mostrarGrupoExperiencia,
    mostrarGrupoSeguranca,
    mostrarGrupoSistema,
    totalSecoesConfiguracaoVisiveis,
    totalSecoesContaAcesso,
    totalSecoesExperiencia,
    totalSecoesSeguranca,
    totalSecoesSistema,
    totalPrioridadesAbertas,
    resumoBuscaConfiguracoes,
  } = buildSettingsSectionVisibility({
    buscaConfiguracoes,
    filtroConfiguracoes,
    perfilNomeCompleto,
    contaEmailLabel,
    modeloIa,
    estiloResposta,
    idiomaResposta,
    temaApp,
    tamanhoFonte: input.tamanhoFonte,
    densidadeInterface,
    corDestaque,
    somNotificacao,
    provedorPrimario,
    resumoSessaoAtual,
    resumoBlindagemSessoes,
    resumo2FAStatus,
    lockTimeout,
    reautenticacaoStatus,
    totalEventosSeguranca: eventosSeguranca.length,
    resumoDadosConversas,
    resumoPermissoes,
    resumoPrivacidadeNotificacoes,
    resumoExcluirConta,
    appVersionLabel: APP_VERSION_LABEL,
    appBuildChannel: APP_BUILD_CHANNEL,
    resumoFilaSuporteLocal,
    twoFactorEnabled,
    provedoresConectadosTotal,
    permissoesNegadasTotal,
    sessoesSuspeitasTotal,
  });
  const settingsDrawerInOverview = settingsDrawerPage === "overview";
  const settingsDrawerPageKey = settingsDrawerPage as Exclude<
    SettingsDrawerPage,
    "overview"
  >;
  const settingsDrawerSectionKey = settingsDrawerSection as
    | SettingsSectionKey
    | "all";
  const settingsDrawerShowingSearchResults =
    settingsDrawerInOverview && Boolean(buscaConfiguracoesNormalizada);
  const settingsDrawerShowingOverviewCards =
    settingsDrawerInOverview && !settingsDrawerShowingSearchResults;
  const settingsDrawerMatchesPage = (page: string) =>
    settingsDrawerPage === page || settingsDrawerShowingSearchResults;
  const settingsDrawerPageSections = settingsDrawerInOverview
    ? []
    : SETTINGS_DRAWER_PAGE_META[settingsDrawerPageKey].sections.filter(
        (item: SettingsSectionKey) => mostrarSecaoConfiguracao(item),
      );
  const settingsDrawerSectionMenuAtiva =
    !settingsDrawerInOverview &&
    settingsDrawerSectionKey === "all" &&
    settingsDrawerPageSections.length > 1;
  const settingsDrawerCurrentSectionMeta =
    !settingsDrawerInOverview && settingsDrawerSectionKey !== "all"
      ? SETTINGS_DRAWER_SECTION_META[settingsDrawerSectionKey]
      : null;
  const settingsDrawerTitle = settingsDrawerInOverview
    ? "Configurações"
    : settingsDrawerCurrentSectionMeta
      ? settingsDrawerCurrentSectionMeta.title
      : SETTINGS_DRAWER_PAGE_META[settingsDrawerPageKey].title;
  const settingsDrawerSubtitle = settingsDrawerInOverview
    ? "Ajuste o app e acesse as ações rápidas do inspetor em um só lugar."
    : settingsDrawerCurrentSectionMeta
      ? settingsDrawerCurrentSectionMeta.subtitle
      : SETTINGS_DRAWER_PAGE_META[settingsDrawerPageKey].subtitle;
  const settingsDrawerMatchesSection = (
    page: string,
    section: SettingsSectionKey,
  ) =>
    settingsDrawerMatchesPage(page) &&
    mostrarSecaoConfiguracao(section) &&
    !settingsDrawerSectionMenuAtiva &&
    (settingsDrawerSectionKey === "all" ||
      settingsDrawerSectionKey === section);

  return {
    artigosAjudaFiltrados,
    buscaConfiguracoesNormalizada,
    contaEmailLabel,
    contaTelefoneLabel,
    corDestaqueResumoConfiguracao,
    detalheGovernancaConfiguracao,
    eventosSegurancaFiltrados,
    existeProvedorDisponivel,
    iniciaisPerfilConfiguracao,
    integracoesConectadasTotal,
    integracoesDisponiveisTotal,
    mostrarGrupoContaAcesso,
    mostrarGrupoExperiencia,
    mostrarGrupoSeguranca,
    mostrarGrupoSistema,
    nomeUsuarioExibicao,
    outrasSessoesAtivas,
    perfilExibicaoLabel,
    perfilNomeCompleto,
    permissoesNegadasTotal,
    planoResumoConfiguracao,
    previewPrivacidadeNotificacao,
    provedoresConectadosTotal,
    provedorPrimario,
    reemissoesRecomendadasTotal,
    resumo2FAFootnote,
    resumo2FAStatus,
    resumoAlertaMetodosConta,
    resumoAtualizacaoApp,
    resumoBlindagemSessoes,
    resumoBuscaConfiguracoes,
    resumoCodigosRecuperacao,
    resumoContaAcesso,
    resumoDadosConversas,
    resumoExcluirConta,
    resumoFilaSuporteLocal,
    resumoGovernancaConfiguracao,
    resumoMetodosConta,
    resumoPermissoes,
    resumoPermissoesCriticas,
    resumoPrivacidadeNotificacoes,
    resumoSessaoAtual,
    resumoSuporteApp,
    sessaoAtual,
    settingsDrawerInOverview,
    settingsDrawerMatchesPage,
    settingsDrawerMatchesSection,
    settingsDrawerPageSections,
    settingsDrawerSectionMenuAtiva,
    settingsDrawerShowingOverviewCards,
    settingsDrawerShowingSearchResults,
    settingsDrawerSubtitle,
    settingsDrawerTitle,
    sessoesSuspeitasTotal,
    temaResumoConfiguracao,
    temPrioridadesConfiguracao,
    ticketsBugTotal,
    ticketsFeedbackTotal,
    totalPrioridadesAbertas,
    totalSecoesConfiguracaoVisiveis,
    totalSecoesContaAcesso,
    totalSecoesExperiencia,
    totalSecoesSeguranca,
    totalSecoesSistema,
    ultimaVerificacaoAtualizacaoLabel,
    ultimoEventoProvedor,
    ultimoEventoSessao,
    ultimoTicketSuporte,
    ultimoTicketSuporteResumo,
    workspaceResumoConfiguracao,
  };
}

export function buildInspectorLayoutDerivedState(
  input: InspectorLayoutDerivedStateInput,
) {
  const { keyboardHeight } = input;

  const keyboardVisible = keyboardHeight > 0;
  const keyboardAvoidingBehavior: "padding" | "height" =
    Platform.OS === "ios" ? "padding" : "height";
  const loginKeyboardVerticalOffset = Platform.OS === "ios" ? 18 : 0;
  const chatKeyboardVerticalOffset = Platform.OS === "ios" ? 8 : 0;
  const headerSafeTopInset = 0;
  const loginKeyboardBottomPadding =
    Platform.OS === "android" && keyboardVisible
      ? Math.max(spacing.xxl, keyboardHeight + spacing.xl)
      : keyboardVisible
        ? spacing.xl
        : spacing.xxl;
  const threadKeyboardPaddingBottom = keyboardVisible ? spacing.sm : spacing.md;

  return {
    chatKeyboardVerticalOffset,
    headerSafeTopInset,
    keyboardAvoidingBehavior,
    keyboardVisible,
    loginKeyboardBottomPadding,
    loginKeyboardVerticalOffset,
    threadKeyboardPaddingBottom,
  };
}
