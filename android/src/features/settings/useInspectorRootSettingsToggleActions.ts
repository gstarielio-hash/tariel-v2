import type { MobileReadCache } from "../common/readCacheTypes";
import {
  useSettingsToggleActions,
  type UseSettingsToggleActionsParams,
} from "./useSettingsToggleActions";

type SettingsToggleParams = UseSettingsToggleActionsParams<MobileReadCache>;

interface UseInspectorRootSettingsToggleActionsInput {
  actionState: Pick<
    SettingsToggleParams,
    | "abrirConfirmacaoConfiguracao"
    | "executarComReautenticacao"
    | "handleExportarDados"
    | "onOpenSystemSettings"
    | "onSetSettingsSheetNotice"
    | "registrarEventoSegurancaLocal"
    | "showAlert"
  >;
  cacheState: Pick<
    SettingsToggleParams,
    | "cacheLeituraVazio"
    | "filaOffline"
    | "onIsOfflineItemReadyForRetry"
    | "onSaveReadCacheLocally"
    | "onSyncOfflineQueue"
    | "sessionAccessToken"
    | "statusApi"
  >;
  permissionState: Pick<
    SettingsToggleParams,
    | "arquivosPermitidos"
    | "cameraPermitida"
    | "microfonePermitido"
    | "notificacoesPermitidas"
  >;
  setterState: Pick<
    SettingsToggleParams,
    | "setAnexoMesaRascunho"
    | "setAnexoRascunho"
    | "setArquivosPermitidos"
    | "setBackupAutomatico"
    | "setEntradaPorVoz"
    | "setMicrofonePermitido"
    | "setMostrarConteudoNotificacao"
    | "setMostrarSomenteNovaMensagem"
    | "setNotificaPush"
    | "setNotificacoesPermitidas"
    | "setOcultarConteudoBloqueado"
    | "setRespostaPorVoz"
    | "setSpeechEnabled"
    | "setSincronizacaoDispositivos"
    | "setUploadArquivosAtivo"
    | "setVibracaoAtiva"
  >;
  voiceState: Pick<
    SettingsToggleParams,
    "voiceInputRuntimeSupported" | "voiceInputUnavailableMessage"
  >;
}

export function useInspectorRootSettingsToggleActions({
  actionState,
  cacheState,
  permissionState,
  setterState,
  voiceState,
}: UseInspectorRootSettingsToggleActionsInput) {
  return useSettingsToggleActions<MobileReadCache>({
    arquivosPermitidos: permissionState.arquivosPermitidos,
    cacheLeituraVazio: cacheState.cacheLeituraVazio,
    cameraPermitida: permissionState.cameraPermitida,
    executarComReautenticacao: actionState.executarComReautenticacao,
    filaOffline: cacheState.filaOffline,
    microfonePermitido: permissionState.microfonePermitido,
    notificacoesPermitidas: permissionState.notificacoesPermitidas,
    sessionAccessToken: cacheState.sessionAccessToken,
    statusApi: cacheState.statusApi,
    abrirConfirmacaoConfiguracao: actionState.abrirConfirmacaoConfiguracao,
    handleExportarDados: actionState.handleExportarDados,
    onIsOfflineItemReadyForRetry: cacheState.onIsOfflineItemReadyForRetry,
    onOpenSystemSettings: actionState.onOpenSystemSettings,
    onSaveReadCacheLocally: cacheState.onSaveReadCacheLocally,
    onSetSettingsSheetNotice: actionState.onSetSettingsSheetNotice,
    onSyncOfflineQueue: cacheState.onSyncOfflineQueue,
    registrarEventoSegurancaLocal: actionState.registrarEventoSegurancaLocal,
    setAnexoMesaRascunho: setterState.setAnexoMesaRascunho,
    setAnexoRascunho: setterState.setAnexoRascunho,
    setArquivosPermitidos: setterState.setArquivosPermitidos,
    setBackupAutomatico: setterState.setBackupAutomatico,
    setEntradaPorVoz: setterState.setEntradaPorVoz,
    setMicrofonePermitido: setterState.setMicrofonePermitido,
    setMostrarConteudoNotificacao: setterState.setMostrarConteudoNotificacao,
    setMostrarSomenteNovaMensagem: setterState.setMostrarSomenteNovaMensagem,
    setNotificaPush: setterState.setNotificaPush,
    setNotificacoesPermitidas: setterState.setNotificacoesPermitidas,
    setOcultarConteudoBloqueado: setterState.setOcultarConteudoBloqueado,
    setRespostaPorVoz: setterState.setRespostaPorVoz,
    setSpeechEnabled: setterState.setSpeechEnabled,
    setSincronizacaoDispositivos: setterState.setSincronizacaoDispositivos,
    setUploadArquivosAtivo: setterState.setUploadArquivosAtivo,
    setVibracaoAtiva: setterState.setVibracaoAtiva,
    voiceInputRuntimeSupported: voiceState.voiceInputRuntimeSupported,
    voiceInputUnavailableMessage: voiceState.voiceInputUnavailableMessage,
    showAlert: actionState.showAlert,
  });
}
