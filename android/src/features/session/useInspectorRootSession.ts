import {
  useInspectorSession,
  type UseInspectorSessionParams,
} from "./useInspectorSession";

interface UseInspectorRootSessionInput {
  bootstrapState: Pick<
    UseInspectorSessionParams,
    | "settingsHydrated"
    | "chatHistoryEnabled"
    | "deviceBackupEnabled"
    | "aplicarPreferenciasLaudos"
    | "chaveCacheLaudo"
    | "erroSugereModoOffline"
    | "lerCacheLeituraLocal"
    | "lerEstadoHistoricoLocal"
    | "lerFilaOfflineLocal"
    | "lerNotificacoesLocais"
    | "limparCachePorPrivacidade"
    | "cacheLeituraVazio"
  >;
  setterState: Pick<
    UseInspectorSessionParams,
    | "onSetFilaOffline"
    | "onSetNotificacoes"
    | "onSetCacheLeitura"
    | "onSetLaudosFixadosIds"
    | "onSetHistoricoOcultoIds"
    | "onSetUsandoCacheOffline"
    | "onSetLaudosDisponiveis"
    | "onSetConversa"
    | "onSetMensagensMesa"
    | "onSetLaudoMesaCarregado"
    | "onSetErroLaudos"
  >;
  callbackState: Pick<
    UseInspectorSessionParams,
    "onApplyBootstrapCache" | "onAfterLoginSuccess" | "onResetAfterLogout"
  >;
}

export function useInspectorRootSession({
  bootstrapState,
  setterState,
  callbackState,
}: UseInspectorRootSessionInput) {
  return useInspectorSession({
    settingsHydrated: bootstrapState.settingsHydrated,
    chatHistoryEnabled: bootstrapState.chatHistoryEnabled,
    deviceBackupEnabled: bootstrapState.deviceBackupEnabled,
    aplicarPreferenciasLaudos: bootstrapState.aplicarPreferenciasLaudos,
    chaveCacheLaudo: bootstrapState.chaveCacheLaudo,
    erroSugereModoOffline: bootstrapState.erroSugereModoOffline,
    lerCacheLeituraLocal: bootstrapState.lerCacheLeituraLocal,
    lerEstadoHistoricoLocal: bootstrapState.lerEstadoHistoricoLocal,
    lerFilaOfflineLocal: bootstrapState.lerFilaOfflineLocal,
    lerNotificacoesLocais: bootstrapState.lerNotificacoesLocais,
    limparCachePorPrivacidade: bootstrapState.limparCachePorPrivacidade,
    cacheLeituraVazio: bootstrapState.cacheLeituraVazio,
    onSetFilaOffline: setterState.onSetFilaOffline,
    onSetNotificacoes: setterState.onSetNotificacoes,
    onSetCacheLeitura: setterState.onSetCacheLeitura,
    onSetLaudosFixadosIds: setterState.onSetLaudosFixadosIds,
    onSetHistoricoOcultoIds: setterState.onSetHistoricoOcultoIds,
    onSetUsandoCacheOffline: setterState.onSetUsandoCacheOffline,
    onSetLaudosDisponiveis: setterState.onSetLaudosDisponiveis,
    onSetConversa: setterState.onSetConversa,
    onSetMensagensMesa: setterState.onSetMensagensMesa,
    onSetLaudoMesaCarregado: setterState.onSetLaudoMesaCarregado,
    onSetErroLaudos: setterState.onSetErroLaudos,
    onApplyBootstrapCache: callbackState.onApplyBootstrapCache,
    onAfterLoginSuccess: callbackState.onAfterLoginSuccess,
    onResetAfterLogout: callbackState.onResetAfterLogout,
  });
}
