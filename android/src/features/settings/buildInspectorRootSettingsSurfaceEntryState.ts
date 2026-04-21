import { useInspectorRootSettingsSurface } from "./useInspectorRootSettingsSurface";
import type { InspectorRootBootstrap } from "../useInspectorRootBootstrap";

interface BuildInspectorRootSettingsSurfaceEntryStateInput {
  bootstrap: InspectorRootBootstrap;
}

export function buildInspectorRootSettingsSurfaceEntryState({
  bootstrap,
}: BuildInspectorRootSettingsSurfaceEntryStateInput): Parameters<
  typeof useInspectorRootSettingsSurface
>[0]["entryState"] {
  const settingsBindings = bootstrap.settingsBindings;
  const settingsSupportState = bootstrap.settingsSupportState;
  const sessionFlow = bootstrap.sessionFlow;

  return {
    accountState: {
      contaTelefone: settingsBindings.account.contaTelefone,
      emailAtualConta: settingsBindings.account.emailAtualConta,
      fallbackEmail: sessionFlow.state.email,
      perfilExibicao: settingsBindings.account.perfilExibicao,
      perfilNome: settingsBindings.account.perfilNome,
    },
    actionState: {
      abrirSheetConfiguracao:
        settingsSupportState.navigationActions.abrirSheetConfiguracao,
      handleAbrirPaginaConfiguracoes:
        settingsSupportState.navigationActions.handleAbrirPaginaConfiguracoes,
    },
    setterState: {
      setArtigoAjudaExpandidoId:
        settingsSupportState.presentationActions.setArtigoAjudaExpandidoId,
      setBugAttachmentDraft:
        settingsSupportState.presentationActions.setBugAttachmentDraft,
      setBugDescriptionDraft:
        settingsSupportState.presentationActions.setBugDescriptionDraft,
      setBugEmailDraft:
        settingsSupportState.presentationActions.setBugEmailDraft,
      setBuscaAjuda: settingsSupportState.presentationActions.setBuscaAjuda,
      setConfirmarSenhaDraft:
        settingsSupportState.presentationActions.setConfirmarSenhaDraft,
      setFeedbackDraft:
        settingsSupportState.presentationActions.setFeedbackDraft,
      setNomeCompletoDraft:
        settingsSupportState.presentationActions.setNomeCompletoDraft,
      setNomeExibicaoDraft:
        settingsSupportState.presentationActions.setNomeExibicaoDraft,
      setNovaSenhaDraft:
        settingsSupportState.presentationActions.setNovaSenhaDraft,
      setNovoEmailDraft:
        settingsSupportState.presentationActions.setNovoEmailDraft,
      setSenhaAtualDraft:
        settingsSupportState.presentationActions.setSenhaAtualDraft,
      setTelefoneDraft:
        settingsSupportState.presentationActions.setTelefoneDraft,
    },
  };
}
