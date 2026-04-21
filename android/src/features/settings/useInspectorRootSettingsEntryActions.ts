import {
  useSettingsEntryActions,
  type UseSettingsEntryActionsParams,
} from "./useSettingsEntryActions";

type SettingsEntryParams = UseSettingsEntryActionsParams;

interface UseInspectorRootSettingsEntryActionsInput {
  accountState: Pick<
    SettingsEntryParams,
    | "contaTelefone"
    | "emailAtualConta"
    | "fallbackEmail"
    | "perfilExibicao"
    | "perfilNome"
  >;
  actionState: Pick<
    SettingsEntryParams,
    "abrirSheetConfiguracao" | "handleAbrirPaginaConfiguracoes"
  >;
  setterState: Pick<
    SettingsEntryParams,
    | "setArtigoAjudaExpandidoId"
    | "setBugAttachmentDraft"
    | "setBugDescriptionDraft"
    | "setBugEmailDraft"
    | "setBuscaAjuda"
    | "setConfirmarSenhaDraft"
    | "setFeedbackDraft"
    | "setNomeCompletoDraft"
    | "setNomeExibicaoDraft"
    | "setNovaSenhaDraft"
    | "setNovoEmailDraft"
    | "setSenhaAtualDraft"
    | "setTelefoneDraft"
  >;
}

export function useInspectorRootSettingsEntryActions({
  accountState,
  actionState,
  setterState,
}: UseInspectorRootSettingsEntryActionsInput) {
  return useSettingsEntryActions({
    perfilNome: accountState.perfilNome,
    perfilExibicao: accountState.perfilExibicao,
    contaTelefone: accountState.contaTelefone,
    emailAtualConta: accountState.emailAtualConta,
    fallbackEmail: accountState.fallbackEmail,
    abrirSheetConfiguracao: actionState.abrirSheetConfiguracao,
    handleAbrirPaginaConfiguracoes: actionState.handleAbrirPaginaConfiguracoes,
    setNomeCompletoDraft: setterState.setNomeCompletoDraft,
    setNomeExibicaoDraft: setterState.setNomeExibicaoDraft,
    setTelefoneDraft: setterState.setTelefoneDraft,
    setNovoEmailDraft: setterState.setNovoEmailDraft,
    setSenhaAtualDraft: setterState.setSenhaAtualDraft,
    setNovaSenhaDraft: setterState.setNovaSenhaDraft,
    setConfirmarSenhaDraft: setterState.setConfirmarSenhaDraft,
    setBuscaAjuda: setterState.setBuscaAjuda,
    setArtigoAjudaExpandidoId: setterState.setArtigoAjudaExpandidoId,
    setBugDescriptionDraft: setterState.setBugDescriptionDraft,
    setBugEmailDraft: setterState.setBugEmailDraft,
    setBugAttachmentDraft: setterState.setBugAttachmentDraft,
    setFeedbackDraft: setterState.setFeedbackDraft,
  });
}
