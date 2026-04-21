import type { InspectorBaseDerivedState } from "../common/buildInspectorBaseDerivedState";
import {
  buildMobileAccessSummary,
  buildMobileHelpTopicsSummary,
  buildMobileIdentityRuntimeNote,
  buildMobileOperationalFootprintSummary,
  resolveMobilePortalSwitchLinks,
} from "../common/mobileUserAccess";
import { buildSettingsSheetBodyRenderer } from "./buildSettingsSheetBodyRenderer";
import { buildSettingsSheetConfirmAction } from "./buildSettingsSheetConfirmAction";

type SettingsSheetBodyParams = Parameters<
  typeof buildSettingsSheetBodyRenderer
>[0];
type SettingsSheetConfirmParams = Parameters<
  typeof buildSettingsSheetConfirmAction
>[0];

type InspectorSettingsSheetBaseState = Pick<
  InspectorBaseDerivedState,
  | "artigosAjudaFiltrados"
  | "integracoesConectadasTotal"
  | "integracoesDisponiveisTotal"
  | "resumoAtualizacaoApp"
  | "resumoFilaSuporteLocal"
  | "resumoSuporteApp"
  | "ultimaVerificacaoAtualizacaoLabel"
  | "workspaceResumoConfiguracao"
>;

interface BuildInspectorRootSettingsSheetPropsInput {
  accountState: Pick<
    SettingsSheetConfirmParams,
    | "contaTelefone"
    | "email"
    | "emailAtualConta"
    | "perfilExibicao"
    | "perfilFotoHint"
    | "perfilFotoUri"
    | "perfilNome"
    | "planoAtual"
    | "session"
    | "sessaoAtual"
    | "telefoneDraft"
  > &
    Pick<SettingsSheetBodyParams, "provedoresConectados">;
  actionsState: Pick<
    SettingsSheetBodyParams,
    | "formatarHorarioAtividade"
    | "formatarStatusReautenticacao"
    | "handleAlternarArtigoAjuda"
    | "handleAlternarIntegracaoExterna"
    | "onAbrirPortalContinuation"
    | "handleRemoverScreenshotBug"
    | "handleSelecionarModeloIa"
    | "handleSelecionarScreenshotBug"
    | "handleSincronizarIntegracaoExterna"
    | "handleToggleUploadArquivos"
  > &
    Pick<
      SettingsSheetConfirmParams,
      | "compartilharTextoExportado"
      | "handleConfirmarSettingsSheetReauth"
      | "notificarConfiguracaoConcluida"
      | "onRegistrarEventoSegurancaLocal"
    >;
  appState: {
    apiEnvironmentLabel: SettingsSheetBodyParams["apiEnvironmentLabel"];
    appBuildLabel: SettingsSheetBodyParams["appBuildLabel"];
    appName: SettingsSheetBodyParams["appName"];
    supportChannelLabel: SettingsSheetBodyParams["supportChannelLabel"];
  };
  backendState: Pick<
    SettingsSheetConfirmParams,
    | "enviarFotoPerfilNoBackend"
    | "enviarRelatoSuporteNoBackend"
    | "onAtualizarPerfilContaNoBackend"
    | "onAtualizarSenhaContaNoBackend"
    | "onPingApi"
    | "onUpdateAccountPhone"
  >;
  baseState: InspectorSettingsSheetBaseState;
  draftState: Pick<
    SettingsSheetBodyParams,
    | "artigoAjudaExpandidoId"
    | "bugAttachmentDraft"
    | "bugDescriptionDraft"
    | "bugEmailDraft"
    | "buscaAjuda"
    | "confirmarSenhaDraft"
    | "feedbackDraft"
    | "integracaoSincronizandoId"
    | "integracoesExternas"
    | "modeloIa"
    | "nomeAutomaticoConversas"
    | "nomeCompletoDraft"
    | "nomeExibicaoDraft"
    | "novaSenhaDraft"
    | "novoEmailDraft"
    | "reauthReason"
    | "reautenticacaoExpiraEm"
    | "retencaoDados"
    | "salvarHistoricoConversas"
    | "senhaAtualDraft"
    | "settingsSheet"
    | "statusApi"
    | "statusAtualizacaoApp"
    | "ultimoTicketSuporte"
    | "uploadArquivosAtivo"
  > &
    Pick<SettingsSheetConfirmParams, "cartaoAtual">;
  settersState: Pick<
    SettingsSheetConfirmParams,
    | "onSetBugAttachmentDraft"
    | "onSetBugDescriptionDraft"
    | "onSetBugEmailDraft"
    | "onSetCartaoAtual"
    | "onSetConfirmarSenhaDraft"
    | "onSetEmailAtualConta"
    | "onSetFeedbackDraft"
    | "onSetFilaSuporteLocal"
    | "onSetNomeCompletoDraft"
    | "onSetNomeExibicaoDraft"
    | "onSetNovaSenhaDraft"
    | "onSetPerfilExibicao"
    | "onSetPerfilFotoHint"
    | "onSetPerfilFotoUri"
    | "onSetPerfilNome"
    | "onSetPlanoAtual"
    | "onSetProvedoresConectados"
    | "onSetSenhaAtualDraft"
    | "onSetSession"
    | "onSetSettingsSheetLoading"
    | "onSetSettingsSheetNotice"
    | "onSetStatusApi"
    | "onSetStatusAtualizacaoApp"
    | "onSetTelefoneDraft"
    | "onSetUltimaVerificacaoAtualizacao"
  > &
    Pick<
      SettingsSheetBodyParams,
      "onSetBuscaAjuda" | "onSetNomeAutomaticoConversas" | "onSetNovoEmailDraft"
    >;
}

export function buildInspectorRootSettingsSheetProps({
  accountState,
  actionsState,
  appState,
  backendState,
  baseState,
  draftState,
  settersState,
}: BuildInspectorRootSettingsSheetPropsInput) {
  const sessionUser = accountState.session?.bootstrap.usuario;
  const resumoContaAcesso = buildMobileAccessSummary(sessionUser);
  const resumoOperacaoApp = buildMobileOperationalFootprintSummary(sessionUser);
  const identityRuntimeNote = buildMobileIdentityRuntimeNote(sessionUser);
  const portalContinuationLinks = resolveMobilePortalSwitchLinks(sessionUser);
  const topicosAjudaResumo = buildMobileHelpTopicsSummary(sessionUser);

  const handleConfirmarSettingsSheet = buildSettingsSheetConfirmAction({
    bugAttachmentDraft: draftState.bugAttachmentDraft,
    bugDescriptionDraft: draftState.bugDescriptionDraft,
    bugEmailDraft: draftState.bugEmailDraft,
    cartaoAtual: draftState.cartaoAtual,
    compartilharTextoExportado: actionsState.compartilharTextoExportado,
    confirmarSenhaDraft: draftState.confirmarSenhaDraft,
    contaTelefone: accountState.contaTelefone,
    email: accountState.email,
    emailAtualConta: accountState.emailAtualConta,
    enviarFotoPerfilNoBackend: backendState.enviarFotoPerfilNoBackend,
    enviarRelatoSuporteNoBackend: backendState.enviarRelatoSuporteNoBackend,
    feedbackDraft: draftState.feedbackDraft,
    handleConfirmarSettingsSheetReauth:
      actionsState.handleConfirmarSettingsSheetReauth,
    nomeCompletoDraft: draftState.nomeCompletoDraft,
    nomeExibicaoDraft: draftState.nomeExibicaoDraft,
    notificarConfiguracaoConcluida: actionsState.notificarConfiguracaoConcluida,
    novaSenhaDraft: draftState.novaSenhaDraft,
    novoEmailDraft: draftState.novoEmailDraft,
    onAtualizarPerfilContaNoBackend:
      backendState.onAtualizarPerfilContaNoBackend,
    onAtualizarSenhaContaNoBackend: backendState.onAtualizarSenhaContaNoBackend,
    onPingApi: backendState.onPingApi,
    onRegistrarEventoSegurancaLocal:
      actionsState.onRegistrarEventoSegurancaLocal,
    onSetBugAttachmentDraft: settersState.onSetBugAttachmentDraft,
    onSetBugDescriptionDraft: settersState.onSetBugDescriptionDraft,
    onSetBugEmailDraft: settersState.onSetBugEmailDraft,
    onSetCartaoAtual: settersState.onSetCartaoAtual,
    onSetConfirmarSenhaDraft: settersState.onSetConfirmarSenhaDraft,
    onSetEmailAtualConta: settersState.onSetEmailAtualConta,
    onSetFeedbackDraft: settersState.onSetFeedbackDraft,
    onSetFilaSuporteLocal: settersState.onSetFilaSuporteLocal,
    onSetNomeCompletoDraft: settersState.onSetNomeCompletoDraft,
    onSetNomeExibicaoDraft: settersState.onSetNomeExibicaoDraft,
    onSetNovaSenhaDraft: settersState.onSetNovaSenhaDraft,
    onSetPerfilExibicao: settersState.onSetPerfilExibicao,
    onSetPerfilFotoHint: settersState.onSetPerfilFotoHint,
    onSetPerfilFotoUri: settersState.onSetPerfilFotoUri,
    onSetPerfilNome: settersState.onSetPerfilNome,
    onSetPlanoAtual: settersState.onSetPlanoAtual,
    onSetProvedoresConectados: settersState.onSetProvedoresConectados,
    onSetSenhaAtualDraft: settersState.onSetSenhaAtualDraft,
    onSetSession: settersState.onSetSession,
    onSetSettingsSheetLoading: settersState.onSetSettingsSheetLoading,
    onSetSettingsSheetNotice: settersState.onSetSettingsSheetNotice,
    onSetStatusApi: settersState.onSetStatusApi,
    onSetStatusAtualizacaoApp: settersState.onSetStatusAtualizacaoApp,
    onSetTelefoneDraft: settersState.onSetTelefoneDraft,
    onSetUltimaVerificacaoAtualizacao:
      settersState.onSetUltimaVerificacaoAtualizacao,
    onUpdateAccountPhone: backendState.onUpdateAccountPhone,
    perfilExibicao: accountState.perfilExibicao,
    perfilFotoHint: accountState.perfilFotoHint,
    perfilFotoUri: accountState.perfilFotoUri,
    perfilNome: accountState.perfilNome,
    planoAtual: accountState.planoAtual,
    senhaAtualDraft: draftState.senhaAtualDraft,
    session: accountState.session,
    sessaoAtual: accountState.sessaoAtual,
    settingsSheet: draftState.settingsSheet,
    statusApi: draftState.statusApi,
    telefoneDraft: accountState.telefoneDraft,
    workspaceResumoConfiguracao: baseState.workspaceResumoConfiguracao,
  });

  const renderSettingsSheetBody = buildSettingsSheetBodyRenderer({
    apiEnvironmentLabel: appState.apiEnvironmentLabel,
    appBuildLabel: appState.appBuildLabel,
    appName: appState.appName,
    resumoContaAcesso,
    resumoOperacaoApp,
    identityRuntimeNote,
    portalContinuationLinks,
    topicosAjudaResumo,
    artigoAjudaExpandidoId: draftState.artigoAjudaExpandidoId,
    artigosAjudaFiltrados: baseState.artigosAjudaFiltrados,
    bugAttachmentDraft: draftState.bugAttachmentDraft,
    bugDescriptionDraft: draftState.bugDescriptionDraft,
    bugEmailDraft: draftState.bugEmailDraft,
    buscaAjuda: draftState.buscaAjuda,
    cartaoAtual: draftState.cartaoAtual,
    confirmarSenhaDraft: draftState.confirmarSenhaDraft,
    email: accountState.email,
    emailAtualConta: accountState.emailAtualConta,
    feedbackDraft: draftState.feedbackDraft,
    formatarHorarioAtividade: actionsState.formatarHorarioAtividade,
    formatarStatusReautenticacao: actionsState.formatarStatusReautenticacao,
    handleAlternarArtigoAjuda: actionsState.handleAlternarArtigoAjuda,
    handleAlternarIntegracaoExterna:
      actionsState.handleAlternarIntegracaoExterna,
    handleRemoverScreenshotBug: actionsState.handleRemoverScreenshotBug,
    handleSelecionarModeloIa: actionsState.handleSelecionarModeloIa,
    handleSelecionarScreenshotBug: actionsState.handleSelecionarScreenshotBug,
    handleSincronizarIntegracaoExterna:
      actionsState.handleSincronizarIntegracaoExterna,
    handleToggleUploadArquivos: actionsState.handleToggleUploadArquivos,
    integracaoSincronizandoId: draftState.integracaoSincronizandoId,
    integracoesConectadasTotal: baseState.integracoesConectadasTotal,
    integracoesDisponiveisTotal: baseState.integracoesDisponiveisTotal,
    integracoesExternas: draftState.integracoesExternas,
    modeloIa: draftState.modeloIa,
    nomeAutomaticoConversas: draftState.nomeAutomaticoConversas,
    nomeCompletoDraft: draftState.nomeCompletoDraft,
    nomeExibicaoDraft: draftState.nomeExibicaoDraft,
    novaSenhaDraft: draftState.novaSenhaDraft,
    novoEmailDraft: draftState.novoEmailDraft,
    onSetBugDescriptionDraft: settersState.onSetBugDescriptionDraft,
    onSetBugEmailDraft: settersState.onSetBugEmailDraft,
    onSetBuscaAjuda: settersState.onSetBuscaAjuda,
    onSetConfirmarSenhaDraft: settersState.onSetConfirmarSenhaDraft,
    onSetFeedbackDraft: settersState.onSetFeedbackDraft,
    onSetNomeAutomaticoConversas: settersState.onSetNomeAutomaticoConversas,
    onSetNomeCompletoDraft: settersState.onSetNomeCompletoDraft,
    onSetNomeExibicaoDraft: settersState.onSetNomeExibicaoDraft,
    onSetNovaSenhaDraft: settersState.onSetNovaSenhaDraft,
    onSetNovoEmailDraft: settersState.onSetNovoEmailDraft,
    onSetSenhaAtualDraft: settersState.onSetSenhaAtualDraft,
    onSetTelefoneDraft: settersState.onSetTelefoneDraft,
    perfilFotoHint: accountState.perfilFotoHint,
    perfilFotoUri: accountState.perfilFotoUri,
    planoAtual: accountState.planoAtual,
    provedoresConectados: accountState.provedoresConectados,
    reauthReason: draftState.reauthReason,
    reautenticacaoExpiraEm: draftState.reautenticacaoExpiraEm,
    resumoAtualizacaoApp: baseState.resumoAtualizacaoApp,
    resumoFilaSuporteLocal: baseState.resumoFilaSuporteLocal,
    resumoSuporteApp: baseState.resumoSuporteApp,
    retencaoDados: draftState.retencaoDados,
    salvarHistoricoConversas: draftState.salvarHistoricoConversas,
    senhaAtualDraft: draftState.senhaAtualDraft,
    sessaoAtual: accountState.sessaoAtual,
    settingsSheet: draftState.settingsSheet,
    statusApi: draftState.statusApi,
    statusAtualizacaoApp: draftState.statusAtualizacaoApp,
    supportChannelLabel: appState.supportChannelLabel,
    telefoneDraft: accountState.telefoneDraft,
    ultimaVerificacaoAtualizacaoLabel:
      baseState.ultimaVerificacaoAtualizacaoLabel,
    ultimoTicketSuporte: draftState.ultimoTicketSuporte,
    uploadArquivosAtivo: draftState.uploadArquivosAtivo,
    workspaceLabel: baseState.workspaceResumoConfiguracao,
    onAbrirPortalContinuation: actionsState.onAbrirPortalContinuation,
  });

  return {
    handleConfirmarSettingsSheet,
    renderSettingsSheetBody,
  };
}
