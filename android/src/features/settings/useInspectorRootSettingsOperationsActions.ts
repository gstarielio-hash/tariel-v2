import type { MobileReadCache } from "../common/readCacheTypes";
import { useSettingsOperationsActions } from "./useSettingsOperationsActions";

type SettingsOperationsParams = Parameters<
  typeof useSettingsOperationsActions<MobileReadCache>
>[0];

interface UseInspectorRootSettingsOperationsActionsInput {
  actionState: Pick<
    SettingsOperationsParams,
    | "abrirConfirmacaoConfiguracao"
    | "abrirSheetConfiguracao"
    | "compartilharTextoExportado"
    | "executarComReautenticacao"
    | "fecharConfiguracoes"
    | "handleLogout"
    | "onNotificarSistema"
    | "registrarEventoSegurancaLocal"
    | "showAlert"
    | "tentarAbrirUrlExterna"
  >;
  collectionState: Pick<
    SettingsOperationsParams,
    | "eventosSeguranca"
    | "filaSuporteLocal"
    | "integracaoSincronizandoId"
    | "integracoesExternas"
  >;
  identityState: Pick<
    SettingsOperationsParams,
    | "canalSuporteUrl"
    | "emailAtualConta"
    | "fallbackEmail"
    | "perfilExibicao"
    | "perfilNome"
    | "sessaoAtualTitulo"
  >;
  permissionState: Pick<
    SettingsOperationsParams,
    | "arquivosPermitidos"
    | "cameraPermitida"
    | "microfonePermitido"
    | "notificacoesPermitidas"
    | "pushRegistrationLastError"
    | "pushRegistrationSnapshot"
    | "pushRegistrationStatus"
  >;
  runtimeState: Pick<
    SettingsOperationsParams,
    | "appRuntime"
    | "cacheLeituraVazio"
    | "formatarHorarioAtividade"
    | "limpandoCache"
    | "montarScreenshotAnexo"
    | "offlineSyncObservability"
    | "resumoAtualizacaoApp"
    | "statusApi"
    | "statusAtualizacaoApp"
    | "ultimaVerificacaoAtualizacao"
    | "verificandoAtualizacoes"
  >;
  setterState: Pick<
    SettingsOperationsParams,
    | "setBugAttachmentDraft"
    | "setCacheLeitura"
    | "setFilaSuporteLocal"
    | "setIntegracaoSincronizandoId"
    | "setIntegracoesExternas"
    | "setLimpandoCache"
    | "setSettingsSheetNotice"
    | "setStatusApi"
    | "setStatusAtualizacaoApp"
    | "setUltimaLimpezaCacheEm"
    | "setUltimaVerificacaoAtualizacao"
    | "setVerificandoAtualizacoes"
  >;
}

export function useInspectorRootSettingsOperationsActions({
  actionState,
  collectionState,
  identityState,
  permissionState,
  runtimeState,
  setterState,
}: UseInspectorRootSettingsOperationsActionsInput) {
  return useSettingsOperationsActions<MobileReadCache>({
    appRuntime: runtimeState.appRuntime,
    cacheLeituraVazio: runtimeState.cacheLeituraVazio,
    canalSuporteUrl: identityState.canalSuporteUrl,
    emailAtualConta: identityState.emailAtualConta,
    eventosSeguranca: collectionState.eventosSeguranca,
    executarComReautenticacao: actionState.executarComReautenticacao,
    fallbackEmail: identityState.fallbackEmail,
    fecharConfiguracoes: actionState.fecharConfiguracoes,
    offlineSyncObservability: runtimeState.offlineSyncObservability,
    filaSuporteLocal: collectionState.filaSuporteLocal,
    formatarHorarioAtividade: runtimeState.formatarHorarioAtividade,
    handleLogout: actionState.handleLogout,
    integracaoSincronizandoId: collectionState.integracaoSincronizandoId,
    integracoesExternas: collectionState.integracoesExternas,
    limpandoCache: runtimeState.limpandoCache,
    microfonePermitido: permissionState.microfonePermitido,
    cameraPermitida: permissionState.cameraPermitida,
    arquivosPermitidos: permissionState.arquivosPermitidos,
    notificacoesPermitidas: permissionState.notificacoesPermitidas,
    pushRegistrationLastError: permissionState.pushRegistrationLastError,
    pushRegistrationSnapshot: permissionState.pushRegistrationSnapshot,
    pushRegistrationStatus: permissionState.pushRegistrationStatus,
    abrirConfirmacaoConfiguracao: actionState.abrirConfirmacaoConfiguracao,
    abrirSheetConfiguracao: actionState.abrirSheetConfiguracao,
    perfilExibicao: identityState.perfilExibicao,
    perfilNome: identityState.perfilNome,
    registrarEventoSegurancaLocal: actionState.registrarEventoSegurancaLocal,
    resumoAtualizacaoApp: runtimeState.resumoAtualizacaoApp,
    sessaoAtualTitulo: identityState.sessaoAtualTitulo,
    setBugAttachmentDraft: setterState.setBugAttachmentDraft,
    setCacheLeitura: setterState.setCacheLeitura,
    setFilaSuporteLocal: setterState.setFilaSuporteLocal,
    setIntegracaoSincronizandoId: setterState.setIntegracaoSincronizandoId,
    setIntegracoesExternas: setterState.setIntegracoesExternas,
    setLimpandoCache: setterState.setLimpandoCache,
    setSettingsSheetNotice: setterState.setSettingsSheetNotice,
    setStatusApi: setterState.setStatusApi,
    setStatusAtualizacaoApp: setterState.setStatusAtualizacaoApp,
    setUltimaLimpezaCacheEm: setterState.setUltimaLimpezaCacheEm,
    setUltimaVerificacaoAtualizacao:
      setterState.setUltimaVerificacaoAtualizacao,
    setVerificandoAtualizacoes: setterState.setVerificandoAtualizacoes,
    compartilharTextoExportado: actionState.compartilharTextoExportado,
    statusApi: runtimeState.statusApi,
    statusAtualizacaoApp: runtimeState.statusAtualizacaoApp,
    tentarAbrirUrlExterna: actionState.tentarAbrirUrlExterna,
    ultimaVerificacaoAtualizacao: runtimeState.ultimaVerificacaoAtualizacao,
    verificandoAtualizacoes: runtimeState.verificandoAtualizacoes,
    showAlert: actionState.showAlert,
    onNotificarSistema: actionState.onNotificarSistema,
    montarScreenshotAnexo: runtimeState.montarScreenshotAnexo,
  });
}
