import { useState } from "react";

import type { MobileV2ReadRenderMetadata } from "../../config/mobileV2HumanValidation";
import type {
  MobileLaudoCard,
  MobileMesaMessage,
  MobileQualityGateResponse,
} from "../../types/mobile";
import type {
  ActiveThread,
  ChatCaseCreationState,
  ChatState,
  ComposerAttachment,
  MessageReferenceState,
  MobileActivityNotification,
  OfflinePendingMessage,
} from "../chat/types";
import type { GuidedInspectionDraft } from "../inspection/guidedInspection";
import type { MobileReadCache } from "./readCacheTypes";
import type { ThreadRouteSnapshot } from "./threadRouteHistory";

export type OfflineQueueFilter = "all" | "chat" | "mesa";
type HistoryDrawerFilter = "todos" | "fixadas" | "recentes";

export function useInspectorRootLocalState(params: {
  cacheLeituraVazio: MobileReadCache;
}) {
  const [conversa, setConversa] = useState<ChatState | null>(null);
  const [abaAtiva, setAbaAtiva] = useState<ActiveThread>("chat");
  const [laudosDisponiveis, setLaudosDisponiveis] = useState<MobileLaudoCard[]>(
    [],
  );
  const [carregandoLaudos, setCarregandoLaudos] = useState(false);
  const [erroLaudos, setErroLaudos] = useState("");
  const [carregandoConversa, setCarregandoConversa] = useState(false);
  const [sincronizandoConversa, setSincronizandoConversa] = useState(false);
  const [mensagem, setMensagem] = useState("");
  const [anexoRascunho, setAnexoRascunho] = useState<ComposerAttachment | null>(
    null,
  );
  const [erroConversa, setErroConversa] = useState("");
  const [caseCreationState, setCaseCreationState] =
    useState<ChatCaseCreationState>("idle");
  const [threadHomeVisible, setThreadHomeVisible] = useState(true);
  const [
    threadHomeGuidedTemplatesVisible,
    setThreadHomeGuidedTemplatesVisible,
  ] = useState(false);
  const [pendingHistoryThreadRoute, setPendingHistoryThreadRoute] =
    useState<ThreadRouteSnapshot | null>(null);
  const [threadRouteHistory, setThreadRouteHistory] = useState<
    ThreadRouteSnapshot[]
  >([]);
  const [guidedInspectionDraft, setGuidedInspectionDraft] =
    useState<GuidedInspectionDraft | null>(null);
  const [enviandoMensagem, setEnviandoMensagem] = useState(false);
  const [preparandoAnexo, setPreparandoAnexo] = useState(false);
  const [mensagensMesa, setMensagensMesa] = useState<MobileMesaMessage[]>([]);
  const [erroMesa, setErroMesa] = useState("");
  const [mensagemMesa, setMensagemMesa] = useState("");
  const [anexoMesaRascunho, setAnexoMesaRascunho] =
    useState<ComposerAttachment | null>(null);
  const [mensagemMesaReferenciaAtiva, setMensagemMesaReferenciaAtiva] =
    useState<MessageReferenceState | null>(null);
  const [carregandoMesa, setCarregandoMesa] = useState(false);
  const [sincronizandoMesa, setSincronizandoMesa] = useState(false);
  const [enviandoMesa, setEnviandoMesa] = useState(false);
  const [laudoMesaCarregado, setLaudoMesaCarregado] = useState<number | null>(
    null,
  );
  const [anexoAbrindoChave, setAnexoAbrindoChave] = useState("");
  const [mensagemChatDestacadaId, setMensagemChatDestacadaId] = useState<
    number | null
  >(null);
  const [layoutMensagensChatVersao, setLayoutMensagensChatVersao] = useState(0);
  const [qualityGateVisible, setQualityGateVisible] = useState(false);
  const [qualityGateLoading, setQualityGateLoading] = useState(false);
  const [qualityGateSubmitting, setQualityGateSubmitting] = useState(false);
  const [qualityGateLaudoId, setQualityGateLaudoId] = useState<number | null>(
    null,
  );
  const [qualityGatePayload, setQualityGatePayload] =
    useState<MobileQualityGateResponse | null>(null);
  const [qualityGateReason, setQualityGateReason] = useState("");
  const [qualityGateNotice, setQualityGateNotice] = useState("");
  const [filaOffline, setFilaOffline] = useState<OfflinePendingMessage[]>([]);
  const [sincronizandoFilaOffline, setSincronizandoFilaOffline] =
    useState(false);
  const [sincronizandoItemFilaId, setSincronizandoItemFilaId] = useState("");
  const [notificacoes, setNotificacoes] = useState<
    MobileActivityNotification[]
  >([]);
  const [cacheLeitura, setCacheLeitura] = useState<MobileReadCache>(
    params.cacheLeituraVazio,
  );
  const [, setUsandoCacheOffline] = useState(false);
  const [ultimoMetaLeituraFeedMesa, setUltimoMetaLeituraFeedMesa] =
    useState<MobileV2ReadRenderMetadata | null>(null);
  const [ultimosAlvosConsultadosFeedMesa, setUltimosAlvosConsultadosFeedMesa] =
    useState<number[]>([]);
  const [ultimoMetaLeituraThreadMesa, setUltimoMetaLeituraThreadMesa] =
    useState<MobileV2ReadRenderMetadata | null>(null);
  const [filtroHistorico] = useState<HistoryDrawerFilter>("todos");
  const [filtroFilaOffline, setFiltroFilaOffline] =
    useState<OfflineQueueFilter>("all");
  const [verificandoAtualizacoes, setVerificandoAtualizacoes] = useState(false);
  const [sincronizandoAgora, setSincronizandoAgora] = useState(false);
  const [limpandoCache, setLimpandoCache] = useState(false);
  const [ultimaLimpezaCacheEm, setUltimaLimpezaCacheEm] = useState("");
  const [laudosFixadosIds, setLaudosFixadosIds] = useState<number[]>([]);
  const [historicoOcultoIds, setHistoricoOcultoIds] = useState<number[]>([]);
  const [buscaConfiguracoes] = useState("");
  const [bloqueioAppAtivo, setBloqueioAppAtivo] = useState(false);

  return {
    abaAtiva,
    anexoAbrindoChave,
    anexoMesaRascunho,
    anexoRascunho,
    bloqueioAppAtivo,
    buscaConfiguracoes,
    cacheLeitura,
    carregandoConversa,
    carregandoLaudos,
    carregandoMesa,
    caseCreationState,
    conversa,
    enviandoMensagem,
    enviandoMesa,
    erroConversa,
    erroLaudos,
    erroMesa,
    filaOffline,
    filtroFilaOffline,
    filtroHistorico,
    guidedInspectionDraft,
    historicoOcultoIds,
    laudoMesaCarregado,
    laudosDisponiveis,
    laudosFixadosIds,
    layoutMensagensChatVersao,
    limpandoCache,
    mensagem,
    mensagemChatDestacadaId,
    mensagemMesa,
    mensagemMesaReferenciaAtiva,
    mensagensMesa,
    notificacoes,
    pendingHistoryThreadRoute,
    preparandoAnexo,
    qualityGateLaudoId,
    qualityGateLoading,
    qualityGateNotice,
    qualityGatePayload,
    qualityGateReason,
    qualityGateSubmitting,
    qualityGateVisible,
    threadRouteHistory,
    threadHomeVisible,
    threadHomeGuidedTemplatesVisible,
    setAbaAtiva,
    setAnexoAbrindoChave,
    setAnexoMesaRascunho,
    setAnexoRascunho,
    setBloqueioAppAtivo,
    setCacheLeitura,
    setCarregandoConversa,
    setCarregandoLaudos,
    setCarregandoMesa,
    setCaseCreationState,
    setConversa,
    setEnviandoMensagem,
    setEnviandoMesa,
    setErroConversa,
    setErroLaudos,
    setErroMesa,
    setFilaOffline,
    setFiltroFilaOffline,
    setGuidedInspectionDraft,
    setHistoricoOcultoIds,
    setLaudoMesaCarregado,
    setLaudosDisponiveis,
    setLaudosFixadosIds,
    setLayoutMensagensChatVersao,
    setLimpandoCache,
    setMensagem,
    setMensagemChatDestacadaId,
    setMensagemMesa,
    setMensagemMesaReferenciaAtiva,
    setMensagensMesa,
    setNotificacoes,
    setPendingHistoryThreadRoute,
    setPreparandoAnexo,
    setQualityGateLaudoId,
    setQualityGateLoading,
    setQualityGateNotice,
    setQualityGatePayload,
    setQualityGateReason,
    setQualityGateSubmitting,
    setQualityGateVisible,
    setThreadRouteHistory,
    setThreadHomeVisible,
    setThreadHomeGuidedTemplatesVisible,
    setSincronizandoAgora,
    setSincronizandoConversa,
    setSincronizandoFilaOffline,
    setSincronizandoItemFilaId,
    setSincronizandoMesa,
    setUltimaLimpezaCacheEm,
    setUltimoMetaLeituraFeedMesa,
    setUltimoMetaLeituraThreadMesa,
    setUltimosAlvosConsultadosFeedMesa,
    setUsandoCacheOffline,
    setVerificandoAtualizacoes,
    sincronizandoAgora,
    sincronizandoConversa,
    sincronizandoFilaOffline,
    sincronizandoItemFilaId,
    sincronizandoMesa,
    ultimaLimpezaCacheEm,
    ultimoMetaLeituraFeedMesa,
    ultimoMetaLeituraThreadMesa,
    ultimosAlvosConsultadosFeedMesa,
    verificandoAtualizacoes,
  };
}
