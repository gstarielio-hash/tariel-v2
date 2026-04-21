import { Alert } from "react-native";

import type {
  MobileActiveOwnerRole,
  MobileCaseLifecycleStatus,
  MobileCaseWorkflowMode,
  MobileChatMode,
  MobileChatMessage,
  MobileLaudoCard,
  MobileLifecycleTransition,
  MobileReportPackDraft,
  MobileReviewPackage,
  MobileSurfaceAction,
} from "../../types/mobile";
import { normalizarCaseLifecycleStatus } from "./caseLifecycle";

type ConversationLike = {
  laudoId: number | null;
  laudoCard?: MobileLaudoCard | null;
  estado?: string;
  statusCard?: string;
  caseLifecycleStatus?: MobileCaseLifecycleStatus;
  caseWorkflowMode?: MobileCaseWorkflowMode;
  activeOwnerRole?: MobileActiveOwnerRole;
  allowedNextLifecycleStatuses?: string[];
  allowedLifecycleTransitions?: MobileLifecycleTransition[];
  allowedSurfaceActions?: MobileSurfaceAction[];
  reportPackDraft?: MobileReportPackDraft | null;
  reviewPackage?: MobileReviewPackage | null;
  modo?: MobileChatMode | string;
  mensagens?: MobileChatMessage[];
} | null;

export function resolverLaudoIdOperacional(
  current: {
    conversation: ConversationLike;
    qualityGateLaudoId: number | null;
    laudoMesaCarregado: number | null;
  },
  options?: { preferQualityGate?: boolean },
): number | null {
  const candidatos = options?.preferQualityGate
    ? [
        current.qualityGateLaudoId,
        current.conversation?.laudoId,
        current.conversation?.laudoCard?.id,
        current.laudoMesaCarregado,
      ]
    : [
        current.conversation?.laudoId,
        current.conversation?.laudoCard?.id,
        current.laudoMesaCarregado,
        current.qualityGateLaudoId,
      ];
  const laudoId = candidatos.find(
    (value): value is number =>
      typeof value === "number" && Number.isFinite(value) && value > 0,
  );
  return laudoId ?? null;
}

export function conversaTemDocumentoEmitidoAtivo(
  conversa: ConversationLike,
): boolean {
  if (!conversa) {
    return false;
  }

  const lifecycleStatus = String(
    conversa.caseLifecycleStatus ||
      conversa.laudoCard?.case_lifecycle_status ||
      "",
  )
    .trim()
    .toLowerCase();
  const estado = String(conversa.estado || "")
    .trim()
    .toLowerCase();
  const statusCard = String(
    conversa.laudoCard?.status_card || conversa.statusCard || "",
  )
    .trim()
    .toLowerCase();

  const explicitLifecycle = normalizarCaseLifecycleStatus(lifecycleStatus);
  if (explicitLifecycle) {
    return explicitLifecycle === "emitido";
  }

  return estado === "aprovado" || statusCard === "aprovado";
}

export function solicitarPoliticaDocumentoEmitido(): Promise<
  "keep_visible" | "hide_from_case" | null
> {
  return new Promise((resolve) => {
    let resolvido = false;

    const concluir = (
      valor: "keep_visible" | "hide_from_case" | null,
    ): void => {
      if (resolvido) {
        return;
      }
      resolvido = true;
      resolve(valor);
    };

    Alert.alert(
      "Reabrir laudo",
      "Escolha se o PDF final anterior continua visivel no caso ou sai da area ativa durante a reabertura.",
      [
        {
          text: "Cancelar",
          style: "cancel",
          onPress: () => concluir(null),
        },
        {
          text: "Ocultar PDF anterior",
          style: "destructive",
          onPress: () => concluir("hide_from_case"),
        },
        {
          text: "Manter PDF anterior",
          onPress: () => concluir("keep_visible"),
        },
      ],
      {
        cancelable: true,
        onDismiss: () => concluir(null),
      },
    );
  });
}
