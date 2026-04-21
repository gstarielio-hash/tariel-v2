import { API_BASE_URL } from "../../config/api";
import { buildAndroidOfflineSyncViewV1 } from "../offline/offlineSyncObservability";
import { buildRefreshAction } from "./buildRefreshAction";
import type { ActiveThread } from "../chat/types";

interface BuildInspectorRootOperationalStateInput {
  offlineState: Parameters<typeof buildAndroidOfflineSyncViewV1>[0];
  refreshState: Parameters<typeof buildRefreshAction>[0];
  supportState: {
    abaAtiva: "chat" | "mesa" | "finalizar";
    bootstrapApiBaseUrl: string;
    bootstrapSupportWhatsapp: string;
    cacheUpdatedAt: string;
    carregandoLaudos: boolean;
    carregandoMesa: boolean;
    conversaLaudoId: number | null;
    filaOffline: { unread?: boolean; laudoId?: number | null }[];
    formatarHorarioAtividade: (value: string) => string;
    laudoMesaCarregado: number | null;
    limpandoCache: boolean;
    notificacoes: Array<{
      unread: boolean;
      laudoId: number | null;
      targetThread: ActiveThread;
    }>;
    preferredVoiceId: string;
    sincronizandoAgora: boolean;
    sincronizandoConversa: boolean;
    sincronizandoFilaOffline: boolean;
    sincronizandoMesa: boolean;
    statusAtualizacaoApp: string;
    ultimaLimpezaCacheEm: string;
    voices: Array<{ identifier: string; name: string }>;
    ttsSupported: boolean;
    economiaDados: boolean;
    usoBateria: string;
  };
}

export function buildInspectorRootOperationalState({
  offlineState,
  refreshState,
  supportState,
}: BuildInspectorRootOperationalStateInput) {
  const handleRefresh = buildRefreshAction(refreshState);
  const mesaThreadRenderConfirmada = Boolean(
    supportState.abaAtiva === "mesa" &&
    supportState.conversaLaudoId &&
    supportState.laudoMesaCarregado === supportState.conversaLaudoId &&
    !supportState.carregandoMesa,
  );
  const laudoSelecionadoShellId =
    typeof supportState.conversaLaudoId === "number" &&
    Number.isFinite(supportState.conversaLaudoId) &&
    supportState.conversaLaudoId > 0
      ? Math.round(supportState.conversaLaudoId)
      : null;
  const canalSuporteUrl = supportState.bootstrapSupportWhatsapp.trim();
  const canalSuporteLabel = canalSuporteUrl ? "WhatsApp" : "Canal indisponível";
  const apiEnvironmentLabel = (() => {
    const raw = supportState.bootstrapApiBaseUrl || API_BASE_URL;
    try {
      const parsed = new URL(raw);
      return parsed.host || raw;
    } catch {
      return raw;
    }
  })();
  const preferredVoice =
    supportState.voices.find(
      (voice) => voice.identifier === supportState.preferredVoiceId,
    ) ||
    supportState.voices[0] ||
    null;
  const preferredVoiceLabel =
    preferredVoice?.name ||
    (supportState.ttsSupported ? "Padrão do sistema" : "Indisponível");
  const notificacoesNaoLidas = supportState.notificacoes.filter(
    (item) => item.unread,
  ).length;
  const resumoCentralAtividade = !supportState.notificacoes.length
    ? "Sem eventos"
    : notificacoesNaoLidas
      ? `${notificacoesNaoLidas} nova(s)`
      : `${supportState.notificacoes.length} evento(s)`;
  const resumoCache = supportState.limpandoCache
    ? "Limpando..."
    : supportState.ultimaLimpezaCacheEm
      ? `Limpo ${supportState.formatarHorarioAtividade(
          supportState.ultimaLimpezaCacheEm,
        )}`
      : supportState.cacheUpdatedAt
        ? `Atualizado ${supportState.formatarHorarioAtividade(
            supportState.cacheUpdatedAt,
          )}`
        : "Sem cache local";
  const sincronizandoDados =
    supportState.sincronizandoAgora ||
    supportState.sincronizandoConversa ||
    supportState.sincronizandoMesa ||
    supportState.carregandoLaudos ||
    supportState.sincronizandoFilaOffline;
  const offlineSyncObservability = buildAndroidOfflineSyncViewV1(offlineState);
  const notificacoesMesaLaudoAtual = supportState.notificacoes.filter(
    (item) =>
      item.unread &&
      item.targetThread === "mesa" &&
      item.laudoId === supportState.conversaLaudoId,
  ).length;

  return {
    apiEnvironmentLabel,
    canalSuporteLabel,
    canalSuporteUrl,
    handleRefresh,
    laudoSelecionadoShellId,
    mesaThreadRenderConfirmada,
    notificacoesMesaLaudoAtual,
    offlineSyncObservability,
    preferredVoiceLabel,
    resumoCache,
    resumoCentralAtividade,
    sincronizandoDados,
  };
}
