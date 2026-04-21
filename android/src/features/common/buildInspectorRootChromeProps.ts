import type { InspectorBaseDerivedState } from "./buildInspectorBaseDerivedState";
import { buildInspectorSessionModalsInput } from "./buildInspectorSessionModalsInput";
import { buildInspectorSessionModalsStackProps } from "./buildInspectorSessionModalsStackProps";
import type {
  InspectorSessionModalsActivityAndLockInput,
  InspectorSessionModalsAttachmentInput,
  InspectorSessionModalsOfflineQueueInput,
  InspectorSessionModalsSettingsInput,
} from "./inspectorUiBuilderTypes";

type InspectorSessionModalsBaseState = Pick<
  InspectorBaseDerivedState,
  | "filaOfflineFiltrada"
  | "filaOfflineOrdenada"
  | "filtrosFilaOffline"
  | "podeSincronizarFilaOffline"
  | "resumoFilaOfflineFiltrada"
>;

interface BuildInspectorSessionModalsStackRootPropsInput {
  activityAndLockState: Pick<
    InspectorSessionModalsActivityAndLockInput,
    | "activityCenterAutomationDiagnostics"
    | "bloqueioAppAtivo"
    | "centralAtividadeAberta"
    | "deviceBiometricsEnabled"
    | "formatarHorarioAtividade"
    | "handleAbrirNotificacao"
    | "handleDesbloquearAplicativo"
    | "handleLogout"
    | "monitorandoAtividade"
    | "notificacoes"
    | "session"
    | "setCentralAtividadeAberta"
  > & {
    automationDiagnosticsEnabled: boolean;
  };
  attachmentState: InspectorSessionModalsAttachmentInput;
  baseState: InspectorSessionModalsBaseState;
  offlineQueueState: Pick<
    InspectorSessionModalsOfflineQueueInput,
    | "detalheStatusPendenciaOffline"
    | "filaOfflineAberta"
    | "filtroFilaOffline"
    | "handleRetomarItemFilaOffline"
    | "iconePendenciaOffline"
    | "legendaPendenciaOffline"
    | "pendenciaFilaProntaParaReenvio"
    | "removerItemFilaOffline"
    | "resumoPendenciaOffline"
    | "rotuloStatusPendenciaOffline"
    | "setFilaOfflineAberta"
    | "setFiltroFilaOffline"
    | "sincronizacaoDispositivos"
    | "sincronizarFilaOffline"
    | "sincronizarItemFilaOffline"
    | "sincronizandoFilaOffline"
    | "sincronizandoItemFilaId"
    | "statusApi"
  >;
  settingsState: InspectorSessionModalsSettingsInput;
}

export function buildInspectorSessionModalsRootProps({
  activityAndLockState,
  attachmentState,
  baseState,
  offlineQueueState,
  settingsState,
}: BuildInspectorSessionModalsStackRootPropsInput): ReturnType<
  typeof buildInspectorSessionModalsStackProps
> {
  return buildInspectorSessionModalsStackProps(
    buildInspectorSessionModalsInput({
      activityAndLock: {
        activityCenterAutomationDiagnostics:
          activityAndLockState.activityCenterAutomationDiagnostics,
        automationDiagnosticsEnabled:
          activityAndLockState.automationDiagnosticsEnabled,
        bloqueioAppAtivo: activityAndLockState.bloqueioAppAtivo,
        centralAtividadeAberta: activityAndLockState.centralAtividadeAberta,
        deviceBiometricsEnabled: activityAndLockState.deviceBiometricsEnabled,
        formatarHorarioAtividade: activityAndLockState.formatarHorarioAtividade,
        handleAbrirNotificacao: activityAndLockState.handleAbrirNotificacao,
        handleDesbloquearAplicativo:
          activityAndLockState.handleDesbloquearAplicativo,
        handleLogout: activityAndLockState.handleLogout,
        monitorandoAtividade: activityAndLockState.monitorandoAtividade,
        notificacoes: activityAndLockState.notificacoes,
        session: activityAndLockState.session,
        setCentralAtividadeAberta:
          activityAndLockState.setCentralAtividadeAberta,
      },
      attachment: attachmentState,
      offlineQueue: {
        detalheStatusPendenciaOffline:
          offlineQueueState.detalheStatusPendenciaOffline,
        filaOfflineAberta: offlineQueueState.filaOfflineAberta,
        filaOfflineFiltrada: baseState.filaOfflineFiltrada,
        filaOfflineOrdenada: baseState.filaOfflineOrdenada,
        filtroFilaOffline: offlineQueueState.filtroFilaOffline,
        filtrosFilaOffline: baseState.filtrosFilaOffline,
        handleRetomarItemFilaOffline:
          offlineQueueState.handleRetomarItemFilaOffline,
        iconePendenciaOffline: offlineQueueState.iconePendenciaOffline,
        legendaPendenciaOffline: offlineQueueState.legendaPendenciaOffline,
        pendenciaFilaProntaParaReenvio:
          offlineQueueState.pendenciaFilaProntaParaReenvio,
        podeSincronizarFilaOffline: baseState.podeSincronizarFilaOffline,
        removerItemFilaOffline: offlineQueueState.removerItemFilaOffline,
        resumoFilaOfflineFiltrada: baseState.resumoFilaOfflineFiltrada,
        resumoPendenciaOffline: offlineQueueState.resumoPendenciaOffline,
        rotuloStatusPendenciaOffline:
          offlineQueueState.rotuloStatusPendenciaOffline,
        setFilaOfflineAberta: offlineQueueState.setFilaOfflineAberta,
        setFiltroFilaOffline: offlineQueueState.setFiltroFilaOffline,
        sincronizacaoDispositivos: offlineQueueState.sincronizacaoDispositivos,
        sincronizarFilaOffline: offlineQueueState.sincronizarFilaOffline,
        sincronizarItemFilaOffline:
          offlineQueueState.sincronizarItemFilaOffline,
        sincronizandoFilaOffline: offlineQueueState.sincronizandoFilaOffline,
        sincronizandoItemFilaId: offlineQueueState.sincronizandoItemFilaId,
        statusApi: offlineQueueState.statusApi,
      },
      settings: settingsState,
    }),
  );
}
