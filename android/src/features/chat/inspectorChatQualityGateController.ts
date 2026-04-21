import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { Alert } from "react-native";

import {
  carregarGateQualidadeLaudoMobile,
  finalizarLaudoMobile,
  MobileQualityGateError,
} from "../../config/api";
import type {
  MobileChatMode,
  MobileLaudoCard,
  MobileQualityGateResponse,
} from "../../types/mobile";
import { hasMobileUserPortal } from "../common/mobileUserAccess";
import type { MobileSessionState } from "../session/sessionTypes";
import type { ChatAiRequestConfig } from "./preferences";
import {
  QUALITY_GATE_OVERRIDE_MIN_REASON_LENGTH,
  qualityGatePermiteOverride,
  resolverQualityGateRequestedCases,
  resolverQualityGateResponsibilityNotice,
} from "./qualityGateHelpers";
import type { ActiveThread, ChatState, OfflinePendingMessage } from "./types";

type QualityGateControllerCurrent<TOfflineItem extends OfflinePendingMessage> =
  {
    activeThread: ActiveThread;
    session: MobileSessionState | null;
    conversation: ChatState | null;
    laudoMesaCarregado: number | null;
    qualityGateLaudoId: number | null;
    qualityGatePayload: MobileQualityGateResponse | null;
    qualityGateReason: string;
    setErrorConversation: Dispatch<SetStateAction<string>>;
    setQualityGateVisible: Dispatch<SetStateAction<boolean>>;
    setQualityGateLoading: Dispatch<SetStateAction<boolean>>;
    setQualityGateSubmitting: Dispatch<SetStateAction<boolean>>;
    setQualityGateNotice: Dispatch<SetStateAction<string>>;
    setQualityGatePayload: Dispatch<
      SetStateAction<MobileQualityGateResponse | null>
    >;
    setQualityGateLaudoId: Dispatch<SetStateAction<number | null>>;
    setQualityGateReason: Dispatch<SetStateAction<string>>;
    onSetActiveThread: (value: "chat" | "mesa") => void;
    carregarMesaAtual: (
      accessToken: string,
      laudoId: number,
      silencioso?: boolean,
    ) => Promise<void>;
    erroSugereModoOffline: (error: unknown) => boolean;
    setFilaOffline: Dispatch<SetStateAction<TOfflineItem[]>>;
    criarItemFilaOffline: (params: {
      channel: "chat";
      operation?: OfflinePendingMessage["operation"];
      laudoId: number | null;
      text: string;
      title: string;
      attachment: null;
      qualityGateDecision?: OfflinePendingMessage["qualityGateDecision"];
      aiMode: MobileChatMode;
      aiSummary: string;
      aiMessagePrefix: string;
    }) => TOfflineItem;
    aiRequestConfig: ChatAiRequestConfig;
    setStatusApi: (value: "online" | "offline") => void;
  };

type ResolveOperationalLaudoId<TOfflineItem extends OfflinePendingMessage> = (
  current: Pick<
    QualityGateControllerCurrent<TOfflineItem>,
    "conversation" | "qualityGateLaudoId" | "laudoMesaCarregado"
  >,
  options?: { preferQualityGate?: boolean },
) => number | null;

interface CreateInspectorChatQualityGateControllerParams<
  TOfflineItem extends OfflinePendingMessage,
> {
  paramsRef: MutableRefObject<QualityGateControllerCurrent<TOfflineItem>>;
  resolveOperationalLaudoId: ResolveOperationalLaudoId<TOfflineItem>;
  carregarConversaAtual: (
    accessToken: string,
    silencioso?: boolean,
  ) => Promise<ChatState | null>;
  carregarListaLaudos: (
    accessToken: string,
    silencioso?: boolean,
  ) => Promise<MobileLaudoCard[]>;
  restaurarContextoGuiadoDoCaso: (
    laudoId: number | null,
    laudoCard?: MobileLaudoCard | null,
  ) => void;
  abrirLaudoPorId: (accessToken: string, laudoId: number) => Promise<void>;
}

export function createInspectorChatQualityGateController<
  TOfflineItem extends OfflinePendingMessage,
>({
  paramsRef,
  resolveOperationalLaudoId,
  carregarConversaAtual,
  carregarListaLaudos,
  restaurarContextoGuiadoDoCaso,
  abrirLaudoPorId,
}: CreateInspectorChatQualityGateControllerParams<TOfflineItem>) {
  function fecharQualityGate(resetReason = false) {
    const current = paramsRef.current;
    current.setQualityGateVisible(false);
    current.setQualityGateLoading(false);
    current.setQualityGateSubmitting(false);
    current.setQualityGateNotice("");
    current.setQualityGatePayload(null);
    current.setQualityGateLaudoId(null);
    if (resetReason) {
      current.setQualityGateReason("");
    }
  }

  async function abrirQualityGateComPayload(
    laudoId: number,
    payload: MobileQualityGateResponse,
    options?: {
      preservedReason?: string;
      notice?: string;
    },
  ) {
    const current = paramsRef.current;
    current.setQualityGateLaudoId(laudoId);
    current.setQualityGatePayload(payload);
    current.setQualityGateReason(options?.preservedReason || "");
    current.setQualityGateNotice(options?.notice || "");
    current.setQualityGateVisible(true);
    current.setQualityGateLoading(false);
  }

  async function handleAbrirQualityGate() {
    const current = paramsRef.current;
    const laudoId = resolveOperationalLaudoId(current);
    if (!current.session || !laudoId) {
      return;
    }

    current.setErrorConversation("");
    current.setQualityGateVisible(true);
    current.setQualityGateLoading(true);
    current.setQualityGateSubmitting(false);
    current.setQualityGateNotice("");
    current.setQualityGatePayload(null);
    current.setQualityGateLaudoId(laudoId);

    try {
      const payload = await carregarGateQualidadeLaudoMobile(
        current.session.accessToken,
        laudoId,
      );
      current.setQualityGatePayload(payload);
    } catch (error) {
      if (error instanceof MobileQualityGateError) {
        current.setQualityGatePayload(error.payload);
      } else {
        current.setQualityGateNotice(
          error instanceof Error
            ? error.message
            : "Nao foi possivel carregar o quality gate do caso.",
        );
      }
    } finally {
      current.setQualityGateLoading(false);
    }
  }

  async function aplicarResultadoFinalizacao(
    laudoIdFallback: number | null,
    shouldOpenMesa: boolean,
  ) {
    const current = paramsRef.current;
    const session = current.session;
    if (!session) {
      return;
    }

    const proximaConversa = await carregarConversaAtual(
      session.accessToken,
      true,
    );
    await carregarListaLaudos(session.accessToken, true);
    restaurarContextoGuiadoDoCaso(
      proximaConversa?.laudoId ?? laudoIdFallback,
      proximaConversa?.laudoCard || current.conversation?.laudoCard || null,
    );
    if (
      shouldOpenMesa &&
      hasMobileUserPortal(session.bootstrap.usuario, "revisor") &&
      proximaConversa?.laudoId
    ) {
      current.onSetActiveThread("mesa");
      await current.carregarMesaAtual(
        session.accessToken,
        proximaConversa.laudoId,
        true,
      );
    }
  }

  async function handleConfirmarQualityGate() {
    const current = paramsRef.current;
    const laudoId = resolveOperationalLaudoId(current, {
      preferQualityGate: true,
    });
    const payload = current.qualityGatePayload;
    if (!current.session || !laudoId || !payload) {
      return;
    }

    if (!payload.aprovado && !qualityGatePermiteOverride(payload)) {
      current.setQualityGateNotice(
        payload.human_override_policy?.validation_error ||
          payload.mensagem ||
          "A coleta ainda precisa ser corrigida antes da finalização.",
      );
      return;
    }

    const reason = current.qualityGateReason.trim();
    const requestedCases = resolverQualityGateRequestedCases(payload);
    const overridePayload =
      !payload.aprovado && qualityGatePermiteOverride(payload)
        ? {
            enabled: true,
            reason,
            cases: requestedCases,
          }
        : null;

    if (
      overridePayload &&
      reason.length < QUALITY_GATE_OVERRIDE_MIN_REASON_LENGTH
    ) {
      current.setQualityGateNotice(
        `Informe uma justificativa interna com pelo menos ${QUALITY_GATE_OVERRIDE_MIN_REASON_LENGTH} caracteres.`,
      );
      return;
    }

    current.setQualityGateSubmitting(true);
    current.setQualityGateNotice("");

    try {
      const resposta = await finalizarLaudoMobile(
        current.session.accessToken,
        laudoId,
        {
          qualityGateOverride: overridePayload,
        },
      );
      fecharQualityGate(true);
      await aplicarResultadoFinalizacao(
        resposta.laudo_id ?? laudoId,
        Boolean(
          resposta.review_mode_final &&
          resposta.review_mode_final !== "mobile_autonomous",
        ),
      );
      Alert.alert("Finalização do caso", resposta.message);
    } catch (error) {
      if (error instanceof MobileQualityGateError) {
        current.setQualityGatePayload(error.payload);
        current.setQualityGateNotice(
          error.payload.human_override_policy?.validation_error ||
            error.payload.mensagem ||
            error.message,
        );
        return;
      }

      const message =
        error instanceof Error
          ? error.message
          : "Nao foi possivel finalizar o caso pelo app.";

      if (current.erroSugereModoOffline(error)) {
        current.setFilaOffline((estadoAtual) => [
          ...estadoAtual,
          current.criarItemFilaOffline({
            channel: "chat",
            operation: "quality_gate_finalize",
            laudoId,
            text: reason,
            title:
              current.conversation?.laudoCard?.titulo || `Laudo #${laudoId}`,
            attachment: null,
            qualityGateDecision: {
              reason,
              requestedCases,
              responsibilityNotice:
                resolverQualityGateResponsibilityNotice(payload),
              gateSnapshot: payload,
            },
            aiMode: current.aiRequestConfig.mode,
            aiSummary: current.aiRequestConfig.summaryLabel,
            aiMessagePrefix: current.aiRequestConfig.messagePrefix,
          }),
        ]);
        current.setStatusApi("offline");
        fecharQualityGate(true);
        current.setErrorConversation(
          "Finalização guardada na fila offline. Ela será reenviada quando a conexão voltar.",
        );
        return;
      }

      current.setQualityGateNotice(message);
    } finally {
      current.setQualityGateSubmitting(false);
    }
  }

  async function handleRetomarQualityGateOfflineItem(item: TOfflineItem) {
    const current = paramsRef.current;
    if (!current.session || !item.laudoId) {
      return;
    }
    await abrirLaudoPorId(current.session.accessToken, item.laudoId);
    const gateSnapshot = item.qualityGateDecision?.gateSnapshot || null;
    if (gateSnapshot) {
      await abrirQualityGateComPayload(item.laudoId, gateSnapshot, {
        notice:
          item.lastError ||
          "A finalização continua pendente. Revise a justificativa e tente novamente.",
        preservedReason: item.qualityGateDecision?.reason || "",
      });
      return;
    }
    await handleAbrirQualityGate();
    current.setQualityGateNotice(
      item.lastError ||
        "A finalização continua pendente. O app recarregou o quality gate atual do caso.",
    );
  }

  function handleFecharQualityGate() {
    fecharQualityGate(true);
  }

  return {
    handleAbrirQualityGate,
    handleConfirmarQualityGate,
    handleFecharQualityGate,
    handleRetomarQualityGateOfflineItem,
  };
}
