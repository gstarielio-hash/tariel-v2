import { pingApi } from "../../config/api";
import {
  compartilharTextoExportado,
  formatarHorarioAtividade,
} from "../common/appSupportHelpers";
import { useInspectorRootSettingsSurface } from "./useInspectorRootSettingsSurface";
import {
  enviarFotoPerfilNoBackend,
  enviarRelatoSuporteNoBackend,
  atualizarPerfilContaNoBackend,
  atualizarSenhaContaNoBackend,
} from "./settingsBackend";
import { formatarStatusReautenticacao } from "./reauth";
import type { InspectorRootBootstrap } from "../useInspectorRootBootstrap";
import type { InspectorRootControllers } from "../useInspectorRootControllers";
import type { InspectorRootPresentationDerivedSnapshot } from "../buildInspectorRootDerivedState";

interface BuildInspectorRootSettingsSheetStateInput {
  bootstrap: InspectorRootBootstrap;
  controllers: InspectorRootControllers;
  derivedState: InspectorRootPresentationDerivedSnapshot;
}

export function buildInspectorRootSettingsSheetState({
  bootstrap,
  controllers,
  derivedState,
}: BuildInspectorRootSettingsSheetStateInput): Parameters<
  typeof useInspectorRootSettingsSurface
>[0]["uiState"]["sheetState"] {
  const settingsBindings = bootstrap.settingsBindings;
  const settingsSupportState = bootstrap.settingsSupportState;
  const sessionFlow = bootstrap.sessionFlow;
  const runtimeController = bootstrap.runtimeController;
  const reauthActions = bootstrap.reauthActions;

  return {
    accountState: {
      contaTelefone: settingsBindings.account.contaTelefone,
      email: sessionFlow.state.email,
      emailAtualConta: settingsBindings.account.emailAtualConta,
      perfilExibicao: settingsBindings.account.perfilExibicao,
      perfilFotoHint: settingsBindings.account.perfilFotoHint,
      perfilFotoUri: settingsBindings.account.perfilFotoUri,
      perfilNome: settingsBindings.account.perfilNome,
      planoAtual: settingsSupportState.presentationState.planoAtual,
      provedoresConectados:
        settingsSupportState.presentationState.provedoresConectados,
      session: sessionFlow.state.session,
      sessaoAtual: derivedState.sessaoAtual,
      telefoneDraft: settingsSupportState.presentationState.telefoneDraft,
    },
    actionsState: {
      compartilharTextoExportado,
      formatarHorarioAtividade,
      formatarStatusReautenticacao,
      handleConfirmarSettingsSheetReauth:
        reauthActions.handleConfirmarSettingsSheetReauth,
      onAbrirPortalContinuation: async (url, label) => {
        const abriu = await bootstrap.shellSupport.tentarAbrirUrlExterna(url);
        if (!abriu) {
          settingsSupportState.navigationActions.setSettingsSheetNotice(
            `Não foi possível abrir ${label} agora.`,
          );
        }
      },
      notificarConfiguracaoConcluida:
        settingsSupportState.navigationActions.notificarConfiguracaoConcluida,
      onRegistrarEventoSegurancaLocal:
        settingsSupportState.registrarEventoSegurancaLocal,
    },
    appState: {
      apiEnvironmentLabel: controllers.operationalState.apiEnvironmentLabel,
      appBuildLabel: runtimeController.appRuntime.buildLabel,
      appName:
        sessionFlow.state.session?.bootstrap.app.nome || "Tariel Inspetor",
      supportChannelLabel: controllers.operationalState.canalSuporteLabel,
    },
    backendState: {
      enviarFotoPerfilNoBackend,
      enviarRelatoSuporteNoBackend,
      onAtualizarPerfilContaNoBackend: atualizarPerfilContaNoBackend,
      onAtualizarSenhaContaNoBackend: atualizarSenhaContaNoBackend,
      onPingApi: pingApi,
      onUpdateAccountPhone: (value) =>
        settingsBindings.store.settingsActions.updateAccount({ phone: value }),
    },
    baseState: derivedState.inspectorBaseDerivedState,
    draftState: {
      artigoAjudaExpandidoId:
        settingsSupportState.presentationState.artigoAjudaExpandidoId,
      bugAttachmentDraft:
        settingsSupportState.presentationState.bugAttachmentDraft,
      bugDescriptionDraft:
        settingsSupportState.presentationState.bugDescriptionDraft,
      bugEmailDraft: settingsSupportState.presentationState.bugEmailDraft,
      buscaAjuda: settingsSupportState.presentationState.buscaAjuda,
      cartaoAtual: settingsSupportState.presentationState.cartaoAtual,
      confirmarSenhaDraft:
        settingsSupportState.presentationState.confirmarSenhaDraft,
      feedbackDraft: settingsSupportState.presentationState.feedbackDraft,
      integracaoSincronizandoId:
        settingsSupportState.presentationState.integracaoSincronizandoId,
      integracoesExternas:
        settingsSupportState.presentationState.integracoesExternas,
      modeloIa: settingsBindings.ai.modeloIa,
      nomeAutomaticoConversas:
        settingsSupportState.presentationState.nomeAutomaticoConversas,
      nomeCompletoDraft:
        settingsSupportState.presentationState.nomeCompletoDraft,
      nomeExibicaoDraft:
        settingsSupportState.presentationState.nomeExibicaoDraft,
      novaSenhaDraft: settingsSupportState.presentationState.novaSenhaDraft,
      novoEmailDraft: settingsSupportState.presentationState.novoEmailDraft,
      reauthReason: settingsSupportState.presentationState.reauthReason,
      reautenticacaoExpiraEm:
        settingsSupportState.presentationState.reautenticacaoExpiraEm,
      retencaoDados: settingsBindings.dataControls.retencaoDados,
      salvarHistoricoConversas:
        settingsBindings.dataControls.salvarHistoricoConversas,
      senhaAtualDraft: settingsSupportState.presentationState.senhaAtualDraft,
      settingsSheet: settingsSupportState.navigationState.settingsSheet,
      statusApi: sessionFlow.state.statusApi,
      statusAtualizacaoApp:
        settingsSupportState.presentationState.statusAtualizacaoApp,
      ultimoTicketSuporte: derivedState.ultimoTicketSuporte,
      uploadArquivosAtivo: settingsBindings.attachments.uploadArquivosAtivo,
    },
    settersState: {
      onSetBugAttachmentDraft:
        settingsSupportState.presentationActions.setBugAttachmentDraft,
      onSetBugDescriptionDraft:
        settingsSupportState.presentationActions.setBugDescriptionDraft,
      onSetBugEmailDraft:
        settingsSupportState.presentationActions.setBugEmailDraft,
      onSetBuscaAjuda: settingsSupportState.presentationActions.setBuscaAjuda,
      onSetCartaoAtual: settingsSupportState.presentationActions.setCartaoAtual,
      onSetConfirmarSenhaDraft:
        settingsSupportState.presentationActions.setConfirmarSenhaDraft,
      onSetEmailAtualConta: settingsBindings.account.setEmailAtualConta,
      onSetFeedbackDraft:
        settingsSupportState.presentationActions.setFeedbackDraft,
      onSetFilaSuporteLocal:
        settingsSupportState.presentationActions.setFilaSuporteLocal,
      onSetNomeAutomaticoConversas:
        settingsSupportState.presentationActions.setNomeAutomaticoConversas,
      onSetNomeCompletoDraft:
        settingsSupportState.presentationActions.setNomeCompletoDraft,
      onSetNomeExibicaoDraft:
        settingsSupportState.presentationActions.setNomeExibicaoDraft,
      onSetNovaSenhaDraft:
        settingsSupportState.presentationActions.setNovaSenhaDraft,
      onSetNovoEmailDraft:
        settingsSupportState.presentationActions.setNovoEmailDraft,
      onSetPerfilExibicao: settingsBindings.account.setPerfilExibicao,
      onSetPerfilFotoHint: settingsBindings.account.setPerfilFotoHint,
      onSetPerfilFotoUri: settingsBindings.account.setPerfilFotoUri,
      onSetPerfilNome: settingsBindings.account.setPerfilNome,
      onSetPlanoAtual: settingsSupportState.presentationActions.setPlanoAtual,
      onSetProvedoresConectados:
        settingsSupportState.presentationActions.setProvedoresConectados,
      onSetSenhaAtualDraft:
        settingsSupportState.presentationActions.setSenhaAtualDraft,
      onSetSession: sessionFlow.actions.setSession,
      onSetSettingsSheetLoading:
        settingsSupportState.navigationActions.setSettingsSheetLoading,
      onSetSettingsSheetNotice:
        settingsSupportState.navigationActions.setSettingsSheetNotice,
      onSetStatusApi: sessionFlow.actions.setStatusApi,
      onSetStatusAtualizacaoApp:
        settingsSupportState.presentationActions.setStatusAtualizacaoApp,
      onSetTelefoneDraft:
        settingsSupportState.presentationActions.setTelefoneDraft,
      onSetUltimaVerificacaoAtualizacao:
        settingsSupportState.presentationActions
          .setUltimaVerificacaoAtualizacao,
    },
  };
}
