import type {
  MobileActiveOwnerRole,
  MobileCaseLifecycleStatus,
  MobileLifecycleTransition,
  MobileOfficialIssueSummary,
  MobileReportPackDraft,
  MobileSurfaceAction,
} from "../../types/mobile";
import {
  resolverAllowedLifecycleTransitions,
  resolverAllowedSurfaceActions,
  resolverCaseLifecycleStatus,
  resolverCaseOwnerRole,
  resumirCaseSurfaceActions,
  resumirLifecycleTransitions,
  rotuloCaseLifecycle,
  rotuloCaseOwnerRole,
} from "../chat/caseLifecycle";
import { buildReportPackDraftSummary } from "../chat/reportPackHelpers";
import type { SettingsSecurityEventPayload } from "./settingsConfirmActions";
import type { SettingsSheetState } from "./settingsSheetTypes";

interface ExportIntegrationItem {
  id: string;
  label: string;
  connected: boolean;
  lastSyncAt: string;
}

interface ExportLaudoItem {
  id: number;
  titulo: string;
  status_card?: string;
  status_card_label: string;
  data_iso: string;
  case_lifecycle_status?: MobileCaseLifecycleStatus;
  active_owner_role?: MobileActiveOwnerRole;
  allowed_lifecycle_transitions?: MobileLifecycleTransition[];
  allowed_surface_actions?: MobileSurfaceAction[];
  report_pack_draft?: MobileReportPackDraft | null;
  official_issue_summary?: MobileOfficialIssueSummary | null;
  permite_reabrir?: boolean;
  permite_edicao?: boolean;
}

interface ExportNotificationItem {
  title: string;
  body: string;
  createdAt: string;
  unread: boolean;
}

export interface RunExportDataFlowParams {
  formato: "JSON" | "PDF" | "TXT";
  reautenticacaoExpiraEm: string;
  reautenticacaoAindaValida: (value: string) => boolean;
  abrirFluxoReautenticacao: (motivo: string, onSuccess?: () => void) => void;
  registrarEventoSegurancaLocal: (
    payload: SettingsSecurityEventPayload,
  ) => void;
  abrirSheetConfiguracao: (payload: SettingsSheetState) => void;
  perfilNome: string;
  perfilExibicao: string;
  emailAtualConta: string;
  email: string;
  planoAtual: string;
  workspaceResumoConfiguracao: string;
  resumoContaAcesso: string;
  identityRuntimeNote: string;
  portalContinuationSummary: string;
  modeloIa: string;
  estiloResposta: string;
  idiomaResposta: string;
  temaApp: string;
  tamanhoFonte: string;
  densidadeInterface: string;
  corDestaque: string;
  memoriaIa: boolean;
  aprendizadoIa: boolean;
  economiaDados: boolean;
  usoBateria: string;
  notificaPush: boolean;
  notificaRespostas: boolean;
  emailsAtivos: boolean;
  vibracaoAtiva: boolean;
  mostrarConteudoNotificacao: boolean;
  mostrarSomenteNovaMensagem: boolean;
  salvarHistoricoConversas: boolean;
  compartilharMelhoriaIa: boolean;
  retencaoDados: string;
  ocultarConteudoBloqueado: boolean;
  integracoesExternas: ExportIntegrationItem[];
  laudosDisponiveis: ExportLaudoItem[];
  notificacoes: ExportNotificationItem[];
  eventosSeguranca: unknown[];
  serializarPayloadExportacao: (payload: unknown) => string;
  compartilharTextoExportado: (params: {
    extension: "json" | "txt";
    content: string;
    prefixo: string;
  }) => Promise<boolean>;
}

function buildOfficialIssueExportFields(
  summary?: MobileOfficialIssueSummary | null,
) {
  const governanceStatus = String(summary?.label || "").trim();
  const governanceDetail = String(summary?.detail || "").trim();
  const governanceIssueNumber = String(summary?.issue_number || "").trim();

  return {
    reissueRecommended: Boolean(summary?.primary_pdf_diverged),
    governanceStatus,
    governanceDetail,
    governanceIssueNumber,
  };
}

export async function runExportDataFlow({
  formato,
  reautenticacaoExpiraEm,
  reautenticacaoAindaValida,
  abrirFluxoReautenticacao,
  registrarEventoSegurancaLocal,
  abrirSheetConfiguracao,
  perfilNome,
  perfilExibicao,
  emailAtualConta,
  email,
  planoAtual,
  workspaceResumoConfiguracao,
  resumoContaAcesso,
  identityRuntimeNote,
  portalContinuationSummary,
  modeloIa,
  estiloResposta,
  idiomaResposta,
  temaApp,
  tamanhoFonte,
  densidadeInterface,
  corDestaque,
  memoriaIa,
  aprendizadoIa,
  economiaDados,
  usoBateria,
  notificaPush,
  notificaRespostas,
  emailsAtivos,
  vibracaoAtiva,
  mostrarConteudoNotificacao,
  mostrarSomenteNovaMensagem,
  salvarHistoricoConversas,
  compartilharMelhoriaIa,
  retencaoDados,
  ocultarConteudoBloqueado,
  integracoesExternas,
  laudosDisponiveis,
  notificacoes,
  eventosSeguranca,
  serializarPayloadExportacao,
  compartilharTextoExportado,
}: RunExportDataFlowParams) {
  if (!reautenticacaoAindaValida(reautenticacaoExpiraEm)) {
    abrirFluxoReautenticacao(
      `Confirme sua identidade para exportar os dados do inspetor em ${formato}.`,
      () => {
        void runExportDataFlow({
          formato,
          reautenticacaoExpiraEm,
          reautenticacaoAindaValida,
          abrirFluxoReautenticacao,
          registrarEventoSegurancaLocal,
          abrirSheetConfiguracao,
          perfilNome,
          perfilExibicao,
          emailAtualConta,
          email,
          planoAtual,
          workspaceResumoConfiguracao,
          resumoContaAcesso,
          identityRuntimeNote,
          portalContinuationSummary,
          modeloIa,
          estiloResposta,
          idiomaResposta,
          temaApp,
          tamanhoFonte,
          densidadeInterface,
          corDestaque,
          memoriaIa,
          aprendizadoIa,
          economiaDados,
          usoBateria,
          notificaPush,
          notificaRespostas,
          emailsAtivos,
          vibracaoAtiva,
          mostrarConteudoNotificacao,
          mostrarSomenteNovaMensagem,
          salvarHistoricoConversas,
          compartilharMelhoriaIa,
          retencaoDados,
          ocultarConteudoBloqueado,
          integracoesExternas,
          laudosDisponiveis,
          notificacoes,
          eventosSeguranca,
          serializarPayloadExportacao,
          compartilharTextoExportado,
        });
      },
    );
    return;
  }

  registrarEventoSegurancaLocal({
    title: "Exportação de dados solicitada",
    meta: `Formato ${formato} com verificação adicional pendente`,
    status: "Agora",
    type: "data",
    critical: true,
  });

  if (formato === "PDF") {
    abrirSheetConfiguracao({
      kind: "privacy",
      title: `Exportar em ${formato}`,
      subtitle: `Revise o conteúdo desta exportação em ${formato} antes de gerar o arquivo final para compartilhar.`,
    });
    return;
  }

  const laudos = laudosDisponiveis.map((item) => {
    const lifecycleStatus = resolverCaseLifecycleStatus({
      card: item,
      statusCard: item.status_card,
      allowsReopen: item.permite_reabrir,
    });
    const ownerRole = resolverCaseOwnerRole({
      card: item,
      lifecycleStatus,
    });
    const allowedTransitions = resolverAllowedLifecycleTransitions({
      card: item,
      lifecycleStatus,
    });
    const allowedSurfaceActions = resolverAllowedSurfaceActions({
      card: item,
      lifecycleStatus,
      ownerRole,
    });
    const reportPackSummary = buildReportPackDraftSummary(
      item.report_pack_draft,
    );
    const officialIssueFields = buildOfficialIssueExportFields(
      item.official_issue_summary,
    );

    return {
      id: item.id,
      titulo: item.titulo,
      status: item.status_card_label,
      lifecycle: rotuloCaseLifecycle(lifecycleStatus),
      owner: rotuloCaseOwnerRole(ownerRole),
      nextTransitions: resumirLifecycleTransitions(allowedTransitions),
      allowedActions: resumirCaseSurfaceActions(allowedSurfaceActions),
      reportPackReadiness: reportPackSummary?.readinessLabel || "",
      reportPackCoverage: reportPackSummary?.totalBlocks
        ? `${reportPackSummary.readyBlocks}/${reportPackSummary.totalBlocks} blocos`
        : "",
      reportPackValidationMode:
        reportPackSummary?.finalValidationModeLabel || "",
      reportPackInspectionContext:
        reportPackSummary?.inspectionContextLabel || "",
      atualizadoEm: item.data_iso,
      ...officialIssueFields,
    };
  });
  const reissueRecommendedCount = laudos.filter(
    (item) => item.reissueRecommended,
  ).length;

  const payload = {
    exportedAt: new Date().toISOString(),
    account: {
      nome: perfilNome || perfilExibicao || "Inspetor Tariel",
      exibicao: perfilExibicao || perfilNome || "Inspetor",
      email: emailAtualConta || email || "",
      plano: planoAtual,
      workspace: workspaceResumoConfiguracao,
      access: resumoContaAcesso,
      identityRuntimeNote,
      portalContinuationSummary,
    },
    settings: {
      modeloIa,
      estiloResposta,
      idiomaResposta,
      temaApp,
      tamanhoFonte,
      densidadeInterface,
      corDestaque,
      memoriaIa,
      aprendizadoIa,
      economiaDados,
      usoBateria,
      notificacoes: {
        push: notificaPush,
        respostas: notificaRespostas,
        email: emailsAtivos,
        vibracao: vibracaoAtiva,
        preview: mostrarConteudoNotificacao,
        somenteNovaMensagem: mostrarSomenteNovaMensagem,
      },
      privacidade: {
        salvarHistoricoConversas,
        compartilharMelhoriaIa,
        retencaoDados,
        ocultarConteudoBloqueado,
      },
      integracoes: integracoesExternas.map((item) => ({
        id: item.id,
        label: item.label,
        connected: item.connected,
        lastSyncAt: item.lastSyncAt,
      })),
    },
    operationalSummary: {
      totalCases: laudos.length,
      reissueRecommendedCount,
    },
    laudos,
    notifications: notificacoes.map((item) => ({
      title: item.title,
      body: item.body,
      createdAt: item.createdAt,
      unread: item.unread,
    })),
    securityEvents: eventosSeguranca,
  };

  const conteudo =
    formato === "JSON"
      ? serializarPayloadExportacao(payload)
      : [
          "Tariel Inspetor - Exportação de dados",
          `Gerado em: ${new Date().toLocaleString("pt-BR")}`,
          "",
          `Conta: ${payload.account.nome}`,
          `Email: ${payload.account.email}`,
          `Plano: ${payload.account.plano}`,
          `Workspace: ${payload.account.workspace}`,
          `Acesso: ${payload.account.access}`,
          payload.account.identityRuntimeNote
            ? `Runtime de identidade: ${payload.account.identityRuntimeNote}`
            : "",
          payload.account.portalContinuationSummary
            ? `Continuidade web: ${payload.account.portalContinuationSummary}`
            : "",
          "",
          `Laudos sincronizados: ${payload.laudos.length}`,
          `Reemissões recomendadas: ${payload.operationalSummary.reissueRecommendedCount}`,
          `Notificações locais: ${payload.notifications.length}`,
          `Eventos de segurança: ${payload.securityEvents.length}`,
          "",
          "Resumo canônico dos casos:",
          ...payload.laudos
            .slice(0, 5)
            .map(
              (item) =>
                `- ${item.titulo}: ${item.lifecycle} · ${item.owner}${item.allowedActions ? ` · ${item.allowedActions}` : ""}${
                  item.reportPackReadiness
                    ? ` · ${item.reportPackReadiness}`
                    : ""
                }${item.reportPackCoverage ? ` · ${item.reportPackCoverage}` : ""}${
                  item.reportPackValidationMode
                    ? ` · ${item.reportPackValidationMode}`
                    : ""
                }${
                  item.reportPackInspectionContext
                    ? ` · ${item.reportPackInspectionContext}`
                    : ""
                }${item.governanceStatus ? ` · ${item.governanceStatus}` : ""}${
                  item.governanceDetail ? ` · ${item.governanceDetail}` : ""
                }`,
            ),
          "",
          "Preferências principais:",
          `- Modelo IA: ${payload.settings.modeloIa}`,
          `- Estilo: ${payload.settings.estiloResposta}`,
          `- Tema: ${payload.settings.temaApp}`,
          `- Cor de destaque: ${payload.settings.corDestaque}`,
          `- Histórico salvo: ${payload.settings.privacidade.salvarHistoricoConversas ? "sim" : "não"}`,
          `- Integrações conectadas: ${payload.settings.integracoes.filter((item) => item.connected).length}/${payload.settings.integracoes.length}`,
        ].join("\n");

  const exportado = await compartilharTextoExportado({
    extension: formato === "JSON" ? "json" : "txt",
    content: conteudo,
    prefixo: `tariel-inspetor-${formato.toLowerCase()}`,
  });

  if (exportado) {
    registrarEventoSegurancaLocal({
      title: "Dados exportados",
      meta: `Arquivo ${formato} gerado localmente`,
      status: "Agora",
      type: "data",
    });
    return;
  }

  abrirSheetConfiguracao({
    kind: "privacy",
    title: `Exportar em ${formato}`,
    subtitle: `O histórico já está organizado para exportação em ${formato} assim que esse formato estiver habilitado para a sua conta.`,
  });
}
