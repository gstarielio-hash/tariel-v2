import type { Dispatch, SetStateAction } from "react";

import type {
  MobileChatMode,
  MobileQualityGateResponse,
} from "../../types/mobile";
import type { ChatState, ComposerAttachment } from "../chat/types";
import {
  lerCacheLeituraLocal,
  lerEstadoHistoricoLocal,
  lerFilaOfflineLocal,
  lerNotificacoesLocais,
} from "../common/inspectorLocalPersistence";
import type { MobileReadCache } from "../common/readCacheTypes";
import type { GuidedInspectionDraft } from "../inspection/guidedInspection";
import { useInspectorRootSession } from "./useInspectorRootSession";
import type { UseInspectorSessionParams } from "./useInspectorSession";

interface UseInspectorRootSessionFlowInput {
  bootstrapState: Pick<
    UseInspectorSessionParams,
    | "settingsHydrated"
    | "chatHistoryEnabled"
    | "deviceBackupEnabled"
    | "aplicarPreferenciasLaudos"
    | "chaveCacheLaudo"
    | "erroSugereModoOffline"
    | "limparCachePorPrivacidade"
    | "cacheLeituraVazio"
  > & {
    criarConversaNova: () => ChatState;
    normalizarComposerAttachment: (valor: unknown) => ComposerAttachment | null;
    normalizarModoChat: (
      modo: unknown,
      fallback?: MobileChatMode,
    ) => MobileChatMode;
  };
  setterState: Omit<
    Pick<
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
    >,
    "onSetCacheLeitura"
  > & {
    onSetCacheLeitura: Dispatch<SetStateAction<MobileReadCache>>;
  };
  resetState: {
    onClearPendingSensitiveAction: () => void;
    onResetSessionBoundSettingsPresentationState: () => void;
    onResetSettingsUi: () => void;
    onSetAbaAtiva: (value: "chat" | "mesa") => void;
    onSetAnexoAbrindoChave: (value: string) => void;
    onSetAnexoMesaRascunho: (value: ComposerAttachment | null) => void;
    onSetAnexoRascunho: (value: ComposerAttachment | null) => void;
    onSetBloqueioAppAtivo: (value: boolean) => void;
    onSetErroMesa: (value: string) => void;
    onSetGuidedInspectionDraft: (value: GuidedInspectionDraft | null) => void;
    onSetMensagem: (value: string) => void;
    onSetMensagemMesa: (value: string) => void;
    onSetQualityGateLaudoId: (value: number | null) => void;
    onSetQualityGateLoading: (value: boolean) => void;
    onSetQualityGateNotice: (value: string) => void;
    onSetQualityGatePayload: (value: MobileQualityGateResponse | null) => void;
    onSetQualityGateReason: (value: string) => void;
    onSetQualityGateSubmitting: (value: boolean) => void;
    onSetQualityGateVisible: (value: boolean) => void;
    onSetSincronizandoFilaOffline: (value: boolean) => void;
    onSetSincronizandoItemFilaId: (value: string) => void;
  };
}

export function useInspectorRootSessionFlow({
  bootstrapState,
  setterState,
  resetState,
}: UseInspectorRootSessionFlowInput) {
  return useInspectorRootSession({
    bootstrapState: {
      settingsHydrated: bootstrapState.settingsHydrated,
      chatHistoryEnabled: bootstrapState.chatHistoryEnabled,
      deviceBackupEnabled: bootstrapState.deviceBackupEnabled,
      aplicarPreferenciasLaudos: bootstrapState.aplicarPreferenciasLaudos,
      chaveCacheLaudo: bootstrapState.chaveCacheLaudo,
      erroSugereModoOffline: bootstrapState.erroSugereModoOffline,
      lerCacheLeituraLocal: (expectedEmail) =>
        lerCacheLeituraLocal({
          cacheLeituraVazio: bootstrapState.cacheLeituraVazio,
          criarConversaNova: bootstrapState.criarConversaNova,
          expectedScope: expectedEmail ? { email: expectedEmail } : null,
          normalizarComposerAttachment:
            bootstrapState.normalizarComposerAttachment,
        }),
      lerEstadoHistoricoLocal,
      lerFilaOfflineLocal: (expectedEmail) =>
        lerFilaOfflineLocal({
          expectedScope: expectedEmail ? { email: expectedEmail } : null,
          normalizarComposerAttachment:
            bootstrapState.normalizarComposerAttachment,
          normalizarModoChat: bootstrapState.normalizarModoChat,
        }),
      lerNotificacoesLocais: (expectedEmail) =>
        lerNotificacoesLocais({
          expectedScope: expectedEmail ? { email: expectedEmail } : null,
        }),
      limparCachePorPrivacidade: bootstrapState.limparCachePorPrivacidade,
      cacheLeituraVazio: bootstrapState.cacheLeituraVazio,
    },
    setterState: {
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
    },
    callbackState: {
      onApplyBootstrapCache: (bootstrap) => {
        setterState.onSetCacheLeitura((estadoAtual) => ({
          ...estadoAtual,
          bootstrap,
          updatedAt: new Date().toISOString(),
        }));
      },
      onAfterLoginSuccess: () => {
        resetState.onSetBloqueioAppAtivo(false);
      },
      onResetAfterLogout: () => {
        setterState.onSetCacheLeitura(bootstrapState.cacheLeituraVazio);
        setterState.onSetConversa(null);
        resetState.onSetMensagem("");
        resetState.onSetAnexoRascunho(null);
        resetState.onSetAbaAtiva("chat");
        resetState.onSetGuidedInspectionDraft(null);
        setterState.onSetLaudosDisponiveis([]);
        setterState.onSetErroLaudos("");
        setterState.onSetMensagensMesa([]);
        resetState.onSetErroMesa("");
        resetState.onSetMensagemMesa("");
        resetState.onSetAnexoMesaRascunho(null);
        resetState.onSetQualityGateLaudoId(null);
        resetState.onSetQualityGateLoading(false);
        resetState.onSetQualityGateNotice("");
        resetState.onSetQualityGatePayload(null);
        resetState.onSetQualityGateReason("");
        resetState.onSetQualityGateSubmitting(false);
        resetState.onSetQualityGateVisible(false);
        setterState.onSetFilaOffline([]);
        resetState.onSetSincronizandoFilaOffline(false);
        resetState.onSetSincronizandoItemFilaId("");
        setterState.onSetLaudoMesaCarregado(null);
        setterState.onSetNotificacoes([]);
        resetState.onSetAnexoAbrindoChave("");
        resetState.onResetSessionBoundSettingsPresentationState();
        resetState.onSetBloqueioAppAtivo(false);
        resetState.onResetSettingsUi();
        resetState.onClearPendingSensitiveAction();
      },
    },
  });
}
