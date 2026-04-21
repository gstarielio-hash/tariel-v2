import type {
  MobileInspectionEntryModeEffective,
  MobileCaseWorkflowMode,
  MobileLaudoCard,
  MobileLifecycleTransition,
  MobileSurfaceAction,
} from "../../types/mobile";
import type { ChatState } from "./types";

import { rotuloCaseLifecycle } from "./caseLifecycleLabels";
import {
  hasMaterializedReportPackDraft,
  inferirAllowedNextLifecycleStatuses,
  inferirPreferredSurface,
  inferirTransitionKind,
  inferirTransitionOwnerRole,
  normalizarAllowedSurfaceActions,
  normalizarCaseLifecycleStatus,
  normalizarCaseOwnerRole,
  normalizarCaseWorkflowMode,
  preferredSurfaceIsExplicit,
  resolverCaseLifecycleStatusFallback,
  transitionKindIsExplicit,
} from "./caseLifecycleNormalization";
import type {
  CanonicalCaseLifecycleStatus,
  CanonicalCaseOwnerRole,
} from "./caseLifecycleTypes";

export type {
  CanonicalCaseLifecycleStatus,
  CanonicalCaseOwnerRole,
} from "./caseLifecycleTypes";
export {
  descricaoCaseLifecycle,
  mapearLifecycleVisual,
  resumirCaseSurfaceActions,
  resumirLifecycleTransitions,
  rotuloCaseLifecycle,
  rotuloCaseOwnerRole,
  rotuloCaseSurfaceAction,
  targetThreadCaseLifecycle,
} from "./caseLifecycleLabels";
export {
  normalizarAllowedSurfaceActions,
  normalizarCaseLifecycleStatus,
  normalizarCaseOwnerRole,
  normalizarCaseSurfaceAction,
  normalizarCaseWorkflowMode,
} from "./caseLifecycleNormalization";

function normalizarLifecycleTransition(
  value: unknown,
): MobileLifecycleTransition | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const targetStatus = normalizarCaseLifecycleStatus(record.target_status);
  if (!targetStatus) {
    return null;
  }

  const transitionKind = String(record.transition_kind || "")
    .trim()
    .toLowerCase();
  const ownerRole = normalizarCaseOwnerRole(record.owner_role);
  const preferredSurface = String(record.preferred_surface || "")
    .trim()
    .toLowerCase();
  const label = String(record.label || "").trim();

  return {
    target_status: targetStatus,
    transition_kind: transitionKindIsExplicit(transitionKind)
      ? transitionKind
      : inferirTransitionKind(targetStatus),
    label: label || rotuloCaseLifecycle(targetStatus),
    owner_role: ownerRole || inferirTransitionOwnerRole(targetStatus),
    preferred_surface: preferredSurfaceIsExplicit(preferredSurface)
      ? preferredSurface
      : inferirPreferredSurface(targetStatus),
  };
}

export function normalizarAllowedLifecycleTransitions(
  value: unknown,
): MobileLifecycleTransition[] {
  if (!Array.isArray(value)) {
    return [];
  }

  const dedup = new Set<string>();
  const transitions: MobileLifecycleTransition[] = [];
  value.forEach((item) => {
    const normalizado = normalizarLifecycleTransition(item);
    if (!normalizado) {
      return;
    }
    const key = [
      normalizado.target_status,
      normalizado.transition_kind,
      normalizado.owner_role,
      normalizado.preferred_surface,
    ].join(":");
    if (dedup.has(key)) {
      return;
    }
    dedup.add(key);
    transitions.push(normalizado);
  });
  return transitions;
}

export function resolverCaseLifecycleStatus(params: {
  conversation?: ChatState | null;
  card?: Partial<MobileLaudoCard> | null;
  laudoId?: number | null;
  statusCard?: string | null;
  allowsReopen?: boolean | null;
}): CanonicalCaseLifecycleStatus {
  const explicit =
    normalizarCaseLifecycleStatus(params.conversation?.caseLifecycleStatus) ||
    normalizarCaseLifecycleStatus(
      params.conversation?.laudoCard?.case_lifecycle_status,
    ) ||
    normalizarCaseLifecycleStatus(params.card?.case_lifecycle_status);
  if (explicit) {
    return explicit;
  }

  return resolverCaseLifecycleStatusFallback({
    laudoId:
      params.laudoId ??
      params.conversation?.laudoId ??
      params.conversation?.laudoCard?.id ??
      params.card?.id,
    statusCard:
      params.statusCard ||
      params.conversation?.laudoCard?.status_card ||
      params.conversation?.statusCard ||
      params.card?.status_card,
    allowsReopen:
      params.allowsReopen ??
      params.conversation?.permiteReabrir ??
      params.conversation?.laudoCard?.permite_reabrir ??
      params.card?.permite_reabrir,
  });
}

export function resolverCaseOwnerRole(params: {
  conversation?: ChatState | null;
  card?: Partial<MobileLaudoCard> | null;
  lifecycleStatus?: CanonicalCaseLifecycleStatus | null;
}): CanonicalCaseOwnerRole {
  const explicit =
    normalizarCaseOwnerRole(params.conversation?.activeOwnerRole) ||
    normalizarCaseOwnerRole(
      params.conversation?.laudoCard?.active_owner_role,
    ) ||
    normalizarCaseOwnerRole(params.card?.active_owner_role);
  if (explicit) {
    return explicit;
  }

  const lifecycle =
    params.lifecycleStatus || resolverCaseLifecycleStatus(params);
  if (lifecycle === "aguardando_mesa" || lifecycle === "em_revisao_mesa") {
    return "mesa";
  }
  if (lifecycle === "aprovado" || lifecycle === "emitido") {
    return "none";
  }
  return "inspetor";
}

export function resolverAllowedNextLifecycleStatuses(params: {
  conversation?: ChatState | null;
  card?: Partial<MobileLaudoCard> | null;
  lifecycleStatus?: CanonicalCaseLifecycleStatus | null;
}): CanonicalCaseLifecycleStatus[] {
  const explicitFromConversation = Array.isArray(
    params.conversation?.allowedNextLifecycleStatuses,
  )
    ? params.conversation?.allowedNextLifecycleStatuses || []
    : [];
  const explicitFromCard = Array.isArray(
    params.card?.allowed_next_lifecycle_statuses,
  )
    ? params.card?.allowed_next_lifecycle_statuses || []
    : [];

  const explicit = [...explicitFromConversation, ...explicitFromCard]
    .map((item) => normalizarCaseLifecycleStatus(item))
    .filter((item): item is CanonicalCaseLifecycleStatus => item !== null);
  if (explicit.length) {
    return Array.from(new Set(explicit));
  }

  const transitions = normalizarAllowedLifecycleTransitions(
    params.conversation?.allowedLifecycleTransitions ||
      params.conversation?.laudoCard?.allowed_lifecycle_transitions ||
      params.card?.allowed_lifecycle_transitions,
  );
  if (transitions.length) {
    return Array.from(new Set(transitions.map((item) => item.target_status)));
  }

  const lifecycleStatus =
    params.lifecycleStatus || resolverCaseLifecycleStatus(params);
  return inferirAllowedNextLifecycleStatuses(lifecycleStatus);
}

export function resolverAllowedLifecycleTransitions(params: {
  conversation?: ChatState | null;
  card?: Partial<MobileLaudoCard> | null;
  lifecycleStatus?: CanonicalCaseLifecycleStatus | null;
}): MobileLifecycleTransition[] {
  const explicit = normalizarAllowedLifecycleTransitions(
    params.conversation?.allowedLifecycleTransitions ||
      params.conversation?.laudoCard?.allowed_lifecycle_transitions ||
      params.card?.allowed_lifecycle_transitions,
  );
  if (explicit.length) {
    return explicit;
  }

  return resolverAllowedNextLifecycleStatuses(params).map((targetStatus) => ({
    target_status: targetStatus,
    transition_kind: inferirTransitionKind(targetStatus),
    label: rotuloCaseLifecycle(targetStatus),
    owner_role: inferirTransitionOwnerRole(targetStatus),
    preferred_surface: inferirPreferredSurface(targetStatus),
  }));
}

export function resolverAllowedSurfaceActions(params: {
  conversation?: ChatState | null;
  card?: Partial<MobileLaudoCard> | null;
  lifecycleStatus?: CanonicalCaseLifecycleStatus | null;
  ownerRole?: CanonicalCaseOwnerRole | null;
}): MobileSurfaceAction[] {
  const explicit = normalizarAllowedSurfaceActions(
    params.conversation?.allowedSurfaceActions ||
      params.conversation?.laudoCard?.allowed_surface_actions ||
      params.card?.allowed_surface_actions,
  );
  if (explicit.length) {
    return explicit;
  }

  const lifecycleStatus =
    params.lifecycleStatus || resolverCaseLifecycleStatus(params);
  const ownerRole = params.ownerRole || resolverCaseOwnerRole(params);
  const laudoId = Number(
    params.conversation?.laudoId ??
      params.conversation?.laudoCard?.id ??
      params.card?.id ??
      0,
  );
  const allowsEdit = Boolean(
    params.conversation?.permiteEdicao ??
    params.conversation?.laudoCard?.permite_edicao ??
    params.card?.permite_edicao,
  );
  const allowsReopen = Boolean(
    params.conversation?.permiteReabrir ??
    params.conversation?.laudoCard?.permite_reabrir ??
    params.card?.permite_reabrir,
  );
  const dedup = new Set<MobileSurfaceAction>();

  if (lifecycleStatus === "analise_livre") {
    return [];
  }

  if (
    laudoId > 0 &&
    allowsEdit &&
    ownerRole !== "mesa" &&
    lifecycleStatus !== "aprovado" &&
    lifecycleStatus !== "emitido"
  ) {
    dedup.add("chat_finalize");
  }
  if (
    allowsReopen ||
    lifecycleStatus === "aprovado" ||
    lifecycleStatus === "emitido"
  ) {
    dedup.add("chat_reopen");
  }
  if (ownerRole === "mesa") {
    dedup.add("mesa_approve");
    dedup.add("mesa_return");
  }
  if (lifecycleStatus === "aprovado") {
    dedup.add("system_issue");
  }

  return Array.from(dedup);
}

export function hasCaseSurfaceAction(params: {
  conversation?: ChatState | null;
  card?: Partial<MobileLaudoCard> | null;
  lifecycleStatus?: CanonicalCaseLifecycleStatus | null;
  ownerRole?: CanonicalCaseOwnerRole | null;
  action: MobileSurfaceAction;
}): boolean {
  return resolverAllowedSurfaceActions(params).includes(params.action);
}

export function hasFormalCaseWorkflow(params: {
  conversation?: ChatState | null;
  card?: Partial<MobileLaudoCard> | null;
  workflowMode?: MobileCaseWorkflowMode | string | null;
  lifecycleStatus?: CanonicalCaseLifecycleStatus | string | null;
  allowedSurfaceActions?: MobileSurfaceAction[] | null;
  entryModeEffective?: MobileInspectionEntryModeEffective | string | null;
  reportPackDraft?: unknown;
}): boolean {
  const entryModeEffective = String(
    params.entryModeEffective ||
      params.conversation?.laudoCard?.entry_mode_effective ||
      params.card?.entry_mode_effective ||
      "",
  )
    .trim()
    .toLowerCase();
  const workflowMode =
    normalizarCaseWorkflowMode(params.workflowMode) ||
    normalizarCaseWorkflowMode(params.conversation?.caseWorkflowMode) ||
    normalizarCaseWorkflowMode(
      params.conversation?.laudoCard?.case_workflow_mode,
    ) ||
    normalizarCaseWorkflowMode(params.card?.case_workflow_mode);
  const lifecycleStatus =
    normalizarCaseLifecycleStatus(params.lifecycleStatus) ||
    resolverCaseLifecycleStatus({
      conversation: params.conversation,
      card: params.card,
    });
  if (
    lifecycleStatus === "aguardando_mesa" ||
    lifecycleStatus === "em_revisao_mesa" ||
    lifecycleStatus === "devolvido_para_correcao" ||
    lifecycleStatus === "aprovado" ||
    lifecycleStatus === "emitido"
  ) {
    return true;
  }

  if (
    hasMaterializedReportPackDraft(
      params.reportPackDraft ?? params.conversation?.reportPackDraft,
    )
  ) {
    return true;
  }

  if (entryModeEffective === "chat_first") {
    return false;
  }

  if (workflowMode === "laudo_guiado" || workflowMode === "laudo_com_mesa") {
    return true;
  }

  if (lifecycleStatus !== "analise_livre") {
    return true;
  }

  const explicitActions = normalizarAllowedSurfaceActions(
    params.allowedSurfaceActions,
  );
  if (explicitActions.length) {
    return true;
  }

  return (
    resolverAllowedSurfaceActions({
      conversation: params.conversation,
      card: params.card,
      lifecycleStatus,
    }).length > 0
  );
}
