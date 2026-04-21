import type {
  MobileActiveOwnerRole,
  MobileAttachmentPolicy,
  MobileCaseLifecycleStatus,
  MobileCaseWorkflowMode,
  MobileChatMode,
  MobileEstadoLaudo,
  MobileLaudoCard,
  MobileLaudoMensagensResponse,
  MobileLaudoStatusResponse,
  MobileLifecycleTransition,
  MobileReportPackDraft,
  MobileReviewPackage,
  MobileSurfaceAction,
} from "../../types/mobile";
import {
  resolverAllowedLifecycleTransitions,
  resolverAllowedNextLifecycleStatuses,
  resolverAllowedSurfaceActions,
} from "./caseLifecycle";
import { normalizarLaudoCardResumo } from "./conversationAttachmentHelpers";
import {
  extrairModoConversaDasMensagens,
  normalizarMensagensChat,
} from "./conversationMessageHelpers";
import { normalizarModoChat } from "./conversationModeHelpers";
import type { ChatState } from "./types";

export function atualizarResumoLaudoAtual<
  T extends {
    estado: MobileEstadoLaudo | string;
    permite_edicao: boolean;
    permite_reabrir: boolean;
    case_lifecycle_status?: MobileCaseLifecycleStatus;
    case_workflow_mode?: MobileCaseWorkflowMode;
    active_owner_role?: MobileActiveOwnerRole;
    allowed_next_lifecycle_statuses?: string[];
    allowed_lifecycle_transitions?: MobileLifecycleTransition[];
    allowed_surface_actions?: MobileSurfaceAction[];
    laudo_card: MobileLaudoCard | null;
    attachment_policy?: MobileAttachmentPolicy | null;
    review_package?: MobileReviewPackage | null;
    report_pack_draft?: MobileReportPackDraft | null;
    modo?: MobileChatMode | string;
  },
>(estadoAtual: ChatState | null, payload: T): ChatState | null {
  if (!estadoAtual) {
    return estadoAtual;
  }

  const laudoCardNormalizado = normalizarLaudoCardResumo(
    payload.laudo_card || estadoAtual.laudoCard,
  );

  const proximoEstadoBase: ChatState = {
    ...estadoAtual,
    estado: payload.estado,
    statusCard: laudoCardNormalizado?.status_card || estadoAtual.statusCard,
    permiteEdicao: Boolean(payload.permite_edicao),
    permiteReabrir: Boolean(payload.permite_reabrir),
    laudoCard: laudoCardNormalizado,
    caseLifecycleStatus:
      payload.case_lifecycle_status ||
      payload.laudo_card?.case_lifecycle_status ||
      estadoAtual.caseLifecycleStatus,
    caseWorkflowMode:
      payload.case_workflow_mode ||
      payload.laudo_card?.case_workflow_mode ||
      estadoAtual.caseWorkflowMode,
    activeOwnerRole:
      payload.active_owner_role ||
      payload.laudo_card?.active_owner_role ||
      estadoAtual.activeOwnerRole,
    allowedNextLifecycleStatuses:
      payload.allowed_next_lifecycle_statuses ||
      payload.laudo_card?.allowed_next_lifecycle_statuses ||
      estadoAtual.allowedNextLifecycleStatuses,
    allowedLifecycleTransitions:
      payload.allowed_lifecycle_transitions ||
      payload.laudo_card?.allowed_lifecycle_transitions ||
      estadoAtual.allowedLifecycleTransitions,
    allowedSurfaceActions:
      payload.allowed_surface_actions ||
      payload.laudo_card?.allowed_surface_actions ||
      estadoAtual.allowedSurfaceActions,
    attachmentPolicy:
      payload.attachment_policy !== undefined
        ? payload.attachment_policy || null
        : estadoAtual.attachmentPolicy || null,
    reportPackDraft:
      payload.report_pack_draft !== undefined
        ? payload.report_pack_draft || null
        : estadoAtual.reportPackDraft || null,
    reviewPackage:
      payload.review_package !== undefined
        ? payload.review_package || null
        : estadoAtual.reviewPackage || null,
    modo: normalizarModoChat(
      payload.modo,
      normalizarModoChat(estadoAtual.modo),
    ),
  };

  return {
    ...proximoEstadoBase,
    allowedLifecycleTransitions: resolverAllowedLifecycleTransitions({
      conversation: proximoEstadoBase,
      card: proximoEstadoBase.laudoCard,
    }),
    allowedNextLifecycleStatuses: resolverAllowedNextLifecycleStatuses({
      conversation: proximoEstadoBase,
      card: proximoEstadoBase.laudoCard,
    }),
    allowedSurfaceActions: resolverAllowedSurfaceActions({
      conversation: proximoEstadoBase,
      card: proximoEstadoBase.laudoCard,
    }),
  };
}

export function normalizarConversa(
  payload: MobileLaudoStatusResponse | MobileLaudoMensagensResponse,
): ChatState {
  const mensagens = normalizarMensagensChat(
    "itens" in payload ? payload.itens : [],
  );
  const laudoCardNormalizado = normalizarLaudoCardResumo(
    payload.laudo_card || null,
  );
  const conversaBase: ChatState = {
    laudoId: payload.laudo_id ?? null,
    estado: payload.estado,
    statusCard: payload.status_card || "aberto",
    permiteEdicao: Boolean(payload.permite_edicao),
    permiteReabrir: Boolean(payload.permite_reabrir),
    laudoCard: laudoCardNormalizado,
    caseLifecycleStatus:
      payload.case_lifecycle_status ||
      laudoCardNormalizado?.case_lifecycle_status,
    caseWorkflowMode:
      payload.case_workflow_mode || laudoCardNormalizado?.case_workflow_mode,
    activeOwnerRole:
      payload.active_owner_role || laudoCardNormalizado?.active_owner_role,
    allowedNextLifecycleStatuses:
      payload.allowed_next_lifecycle_statuses ||
      laudoCardNormalizado?.allowed_next_lifecycle_statuses,
    allowedLifecycleTransitions:
      payload.allowed_lifecycle_transitions ||
      laudoCardNormalizado?.allowed_lifecycle_transitions,
    allowedSurfaceActions:
      payload.allowed_surface_actions ||
      laudoCardNormalizado?.allowed_surface_actions,
    attachmentPolicy: payload.attachment_policy || null,
    reportPackDraft: payload.report_pack_draft || null,
    reviewPackage: payload.review_package || null,
    modo: normalizarModoChat(
      payload.modo,
      extrairModoConversaDasMensagens(mensagens),
    ),
    mensagens,
  };

  return {
    ...conversaBase,
    allowedLifecycleTransitions: resolverAllowedLifecycleTransitions({
      conversation: conversaBase,
      card: conversaBase.laudoCard,
    }),
    allowedNextLifecycleStatuses: resolverAllowedNextLifecycleStatuses({
      conversation: conversaBase,
      card: conversaBase.laudoCard,
    }),
    allowedSurfaceActions: resolverAllowedSurfaceActions({
      conversation: conversaBase,
      card: conversaBase.laudoCard,
    }),
  };
}

export function criarConversaNova(): ChatState {
  const conversaNovaBase: ChatState = {
    laudoId: null,
    estado: "sem_relatorio",
    statusCard: "aberto",
    permiteEdicao: true,
    permiteReabrir: false,
    laudoCard: null,
    caseLifecycleStatus: "analise_livre",
    caseWorkflowMode: "analise_livre",
    activeOwnerRole: "inspetor",
    allowedNextLifecycleStatuses: ["pre_laudo", "laudo_em_coleta"],
    allowedLifecycleTransitions: [],
    allowedSurfaceActions: [],
    attachmentPolicy: null,
    reportPackDraft: null,
    reviewPackage: null,
    modo: "detalhado",
    mensagens: [],
  };

  return {
    ...conversaNovaBase,
    allowedLifecycleTransitions: resolverAllowedLifecycleTransitions({
      conversation: conversaNovaBase,
    }),
    allowedNextLifecycleStatuses: resolverAllowedNextLifecycleStatuses({
      conversation: conversaNovaBase,
    }),
    allowedSurfaceActions: resolverAllowedSurfaceActions({
      conversation: conversaNovaBase,
    }),
  };
}

export function previewChatLiberadoParaConversa(
  conversa: ChatState | null | undefined,
): boolean {
  return Boolean(
    conversa &&
    (!conversa.laudoId ||
      (!conversa.permiteEdicao && !conversa.mensagens.length)),
  );
}

export function podeEditarConversaNoComposer(
  conversa: ChatState | null | undefined,
): boolean {
  return (
    !conversa ||
    conversa.permiteEdicao ||
    previewChatLiberadoParaConversa(conversa)
  );
}
