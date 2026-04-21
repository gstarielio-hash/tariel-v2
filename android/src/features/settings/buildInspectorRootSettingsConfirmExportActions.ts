import { buildSettingsConfirmAndExportActions } from "./buildSettingsConfirmAndExportActions";

type SettingsConfirmExportParams = Parameters<
  typeof buildSettingsConfirmAndExportActions
>[0];

interface BuildInspectorRootSettingsConfirmExportActionsInput {
  accountState: Pick<
    SettingsConfirmExportParams,
    | "email"
    | "emailAtualConta"
    | "perfilExibicao"
    | "perfilNome"
    | "planoAtual"
    | "resumoContaAcesso"
    | "identityRuntimeNote"
    | "portalContinuationSummary"
    | "workspaceResumoConfiguracao"
  >;
  actionState: Pick<
    SettingsConfirmExportParams,
    | "abrirFluxoReautenticacao"
    | "abrirSheetConfiguracao"
    | "compartilharTextoExportado"
    | "executarExclusaoContaLocal"
    | "fecharConfirmacaoConfiguracao"
    | "fecharSheetConfiguracao"
    | "onCreateNewConversation"
    | "onIsValidAiModel"
    | "onRegistrarEventoSegurancaLocal"
    | "reautenticacaoAindaValida"
    | "serializarPayloadExportacao"
  >;
  collectionState: Pick<
    SettingsConfirmExportParams,
    | "eventosSeguranca"
    | "integracoesExternas"
    | "laudosDisponiveis"
    | "notificacoes"
  >;
  draftState: Pick<
    SettingsConfirmExportParams,
    "confirmSheet" | "confirmTextDraft" | "modeloIa" | "reautenticacaoExpiraEm"
  >;
  preferenceState: Pick<
    SettingsConfirmExportParams,
    | "compartilharMelhoriaIa"
    | "corDestaque"
    | "densidadeInterface"
    | "economiaDados"
    | "emailsAtivos"
    | "estiloResposta"
    | "idiomaResposta"
    | "memoriaIa"
    | "mostrarConteudoNotificacao"
    | "mostrarSomenteNovaMensagem"
    | "notificaPush"
    | "notificaRespostas"
    | "ocultarConteudoBloqueado"
    | "retencaoDados"
    | "salvarHistoricoConversas"
    | "tamanhoFonte"
    | "temaApp"
    | "usoBateria"
    | "vibracaoAtiva"
  >;
  settersState: Pick<
    SettingsConfirmExportParams,
    | "limparCachePorPrivacidade"
    | "onSetAnexoMesaRascunho"
    | "onSetAnexoRascunho"
    | "onSetBuscaHistorico"
    | "onSetCacheLeitura"
    | "onSetConversa"
    | "onSetLaudosDisponiveis"
    | "onSetMensagem"
    | "onSetMensagemMesa"
    | "onSetMensagensMesa"
    | "onSetModeloIa"
    | "onSetNotificacoes"
    | "onSetPreviewAnexoImagem"
  >;
}

export function buildInspectorRootSettingsConfirmExportActions({
  accountState,
  actionState,
  collectionState,
  draftState,
  preferenceState,
  settersState,
}: BuildInspectorRootSettingsConfirmExportActionsInput) {
  return buildSettingsConfirmAndExportActions({
    abrirFluxoReautenticacao: actionState.abrirFluxoReautenticacao,
    abrirSheetConfiguracao: actionState.abrirSheetConfiguracao,
    compartilharMelhoriaIa: preferenceState.compartilharMelhoriaIa,
    compartilharTextoExportado: actionState.compartilharTextoExportado,
    confirmSheet: draftState.confirmSheet,
    confirmTextDraft: draftState.confirmTextDraft,
    corDestaque: preferenceState.corDestaque,
    densidadeInterface: preferenceState.densidadeInterface,
    economiaDados: preferenceState.economiaDados,
    email: accountState.email,
    emailAtualConta: accountState.emailAtualConta,
    emailsAtivos: preferenceState.emailsAtivos,
    estiloResposta: preferenceState.estiloResposta,
    eventosSeguranca: collectionState.eventosSeguranca,
    executarExclusaoContaLocal: actionState.executarExclusaoContaLocal,
    fecharConfirmacaoConfiguracao: actionState.fecharConfirmacaoConfiguracao,
    fecharSheetConfiguracao: actionState.fecharSheetConfiguracao,
    integracoesExternas: collectionState.integracoesExternas,
    idiomaResposta: preferenceState.idiomaResposta,
    laudosDisponiveis: collectionState.laudosDisponiveis,
    limparCachePorPrivacidade: settersState.limparCachePorPrivacidade,
    memoriaIa: preferenceState.memoriaIa,
    modeloIa: draftState.modeloIa,
    mostrarConteudoNotificacao: preferenceState.mostrarConteudoNotificacao,
    mostrarSomenteNovaMensagem: preferenceState.mostrarSomenteNovaMensagem,
    notificacoes: collectionState.notificacoes,
    notificaPush: preferenceState.notificaPush,
    notificaRespostas: preferenceState.notificaRespostas,
    ocultarConteudoBloqueado: preferenceState.ocultarConteudoBloqueado,
    onCreateNewConversation: actionState.onCreateNewConversation,
    onIsValidAiModel: actionState.onIsValidAiModel,
    onRegistrarEventoSegurancaLocal:
      actionState.onRegistrarEventoSegurancaLocal,
    onSetAnexoMesaRascunho: settersState.onSetAnexoMesaRascunho,
    onSetAnexoRascunho: settersState.onSetAnexoRascunho,
    onSetBuscaHistorico: settersState.onSetBuscaHistorico,
    onSetCacheLeitura: settersState.onSetCacheLeitura,
    onSetConversa: settersState.onSetConversa,
    onSetLaudosDisponiveis: settersState.onSetLaudosDisponiveis,
    onSetMensagem: settersState.onSetMensagem,
    onSetMensagemMesa: settersState.onSetMensagemMesa,
    onSetMensagensMesa: settersState.onSetMensagensMesa,
    onSetModeloIa: settersState.onSetModeloIa,
    onSetNotificacoes: settersState.onSetNotificacoes,
    onSetPreviewAnexoImagem: settersState.onSetPreviewAnexoImagem,
    perfilExibicao: accountState.perfilExibicao,
    perfilNome: accountState.perfilNome,
    planoAtual: accountState.planoAtual,
    resumoContaAcesso: accountState.resumoContaAcesso,
    identityRuntimeNote: accountState.identityRuntimeNote,
    portalContinuationSummary: accountState.portalContinuationSummary,
    reautenticacaoAindaValida: actionState.reautenticacaoAindaValida,
    reautenticacaoExpiraEm: draftState.reautenticacaoExpiraEm,
    retencaoDados: preferenceState.retencaoDados,
    salvarHistoricoConversas: preferenceState.salvarHistoricoConversas,
    serializarPayloadExportacao: actionState.serializarPayloadExportacao,
    tamanhoFonte: preferenceState.tamanhoFonte,
    temaApp: preferenceState.temaApp,
    usoBateria: preferenceState.usoBateria,
    vibracaoAtiva: preferenceState.vibracaoAtiva,
    workspaceResumoConfiguracao: accountState.workspaceResumoConfiguracao,
  });
}
