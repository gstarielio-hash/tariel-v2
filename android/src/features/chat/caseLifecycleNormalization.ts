import type {
  MobileCaseWorkflowMode,
  MobileLifecycleTransitionKind,
  MobilePreferredSurface,
  MobileSurfaceAction,
} from "../../types/mobile";

import type {
  CanonicalCaseLifecycleStatus,
  CanonicalCaseOwnerRole,
} from "./caseLifecycleTypes";

const LIFECYCLE_STATUSES = new Set<CanonicalCaseLifecycleStatus>([
  "analise_livre",
  "pre_laudo",
  "laudo_em_coleta",
  "aguardando_mesa",
  "em_revisao_mesa",
  "devolvido_para_correcao",
  "aprovado",
  "emitido",
]);
const WORKFLOW_MODES = new Set<MobileCaseWorkflowMode>([
  "analise_livre",
  "laudo_guiado",
  "laudo_com_mesa",
]);
const SURFACE_ACTIONS = new Set<MobileSurfaceAction>([
  "chat_finalize",
  "chat_reopen",
  "mesa_approve",
  "mesa_return",
  "system_issue",
]);
const TRANSITION_KINDS = new Set<MobileLifecycleTransitionKind>([
  "analysis",
  "advance",
  "review",
  "approval",
  "correction",
  "reopen",
  "issue",
]);
const PREFERRED_SURFACES = new Set<MobilePreferredSurface>([
  "chat",
  "mesa",
  "mobile",
  "system",
]);

export function hasMaterializedReportPackDraft(value: unknown): boolean {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }

  const record = value as Record<string, unknown>;
  return Boolean(
    String(record.template_key || record.template_label || "").trim() ||
    (record.pre_laudo_outline &&
      typeof record.pre_laudo_outline === "object" &&
      !Array.isArray(record.pre_laudo_outline)) ||
    (record.pre_laudo_document &&
      typeof record.pre_laudo_document === "object" &&
      !Array.isArray(record.pre_laudo_document)) ||
    (record.quality_gates &&
      typeof record.quality_gates === "object" &&
      !Array.isArray(record.quality_gates)) ||
    (Array.isArray(record.items) && record.items.length > 0) ||
    (Array.isArray(record.image_slots) && record.image_slots.length > 0) ||
    (record.structured_data_candidate &&
      typeof record.structured_data_candidate === "object" &&
      !Array.isArray(record.structured_data_candidate)),
  );
}

export function normalizarCaseLifecycleStatus(
  value: unknown,
): CanonicalCaseLifecycleStatus | null {
  const text = String(value || "")
    .trim()
    .toLowerCase();
  if (LIFECYCLE_STATUSES.has(text as CanonicalCaseLifecycleStatus)) {
    return text as CanonicalCaseLifecycleStatus;
  }
  return null;
}

export function normalizarCaseOwnerRole(
  value: unknown,
): CanonicalCaseOwnerRole | null {
  const text = String(value || "")
    .trim()
    .toLowerCase();
  if (text === "inspetor" || text === "mesa" || text === "none") {
    return text;
  }
  return null;
}

export function normalizarCaseWorkflowMode(
  value: unknown,
): MobileCaseWorkflowMode | null {
  const text = String(value || "")
    .trim()
    .toLowerCase();
  if (WORKFLOW_MODES.has(text as MobileCaseWorkflowMode)) {
    return text as MobileCaseWorkflowMode;
  }
  return null;
}

export function normalizarCaseSurfaceAction(
  value: unknown,
): MobileSurfaceAction | null {
  const text = String(value || "")
    .trim()
    .toLowerCase();
  if (SURFACE_ACTIONS.has(text as MobileSurfaceAction)) {
    return text as MobileSurfaceAction;
  }
  return null;
}

export function inferirAllowedNextLifecycleStatuses(
  lifecycleStatus: CanonicalCaseLifecycleStatus,
): CanonicalCaseLifecycleStatus[] {
  switch (lifecycleStatus) {
    case "analise_livre":
      return ["pre_laudo", "laudo_em_coleta"];
    case "pre_laudo":
      return ["laudo_em_coleta"];
    case "laudo_em_coleta":
      return ["aguardando_mesa", "aprovado"];
    case "aguardando_mesa":
      return ["em_revisao_mesa", "devolvido_para_correcao", "aprovado"];
    case "em_revisao_mesa":
      return ["devolvido_para_correcao", "aprovado"];
    case "devolvido_para_correcao":
      return ["laudo_em_coleta"];
    case "aprovado":
      return ["emitido", "devolvido_para_correcao"];
    case "emitido":
      return ["devolvido_para_correcao"];
  }
}

export function inferirTransitionKind(
  targetStatus: CanonicalCaseLifecycleStatus,
): MobileLifecycleTransitionKind {
  switch (targetStatus) {
    case "analise_livre":
      return "analysis";
    case "pre_laudo":
    case "laudo_em_coleta":
      return "advance";
    case "aguardando_mesa":
    case "em_revisao_mesa":
      return "review";
    case "devolvido_para_correcao":
      return "correction";
    case "aprovado":
      return "approval";
    case "emitido":
      return "issue";
  }
}

export function inferirPreferredSurface(
  targetStatus: CanonicalCaseLifecycleStatus,
): MobilePreferredSurface {
  switch (targetStatus) {
    case "aguardando_mesa":
    case "em_revisao_mesa":
      return "mesa";
    case "aprovado":
      return "mobile";
    case "emitido":
      return "system";
    default:
      return "chat";
  }
}

export function inferirTransitionOwnerRole(
  targetStatus: CanonicalCaseLifecycleStatus,
): CanonicalCaseOwnerRole {
  switch (targetStatus) {
    case "aguardando_mesa":
    case "em_revisao_mesa":
      return "mesa";
    case "aprovado":
    case "emitido":
      return "none";
    default:
      return "inspetor";
  }
}

export function normalizarAllowedSurfaceActions(
  value: unknown,
): MobileSurfaceAction[] {
  if (!Array.isArray(value)) {
    return [];
  }

  const dedup = new Set<MobileSurfaceAction>();
  value.forEach((item) => {
    const normalizado = normalizarCaseSurfaceAction(item);
    if (normalizado) {
      dedup.add(normalizado);
    }
  });
  return Array.from(dedup);
}

export function resolverCaseLifecycleStatusFallback(params: {
  laudoId?: number | null;
  statusCard?: string | null;
  allowsReopen?: boolean | null;
}): CanonicalCaseLifecycleStatus {
  const laudoId = Number(params.laudoId ?? 0);
  const statusCard = String(params.statusCard || "")
    .trim()
    .toLowerCase();
  const allowsReopen = Boolean(params.allowsReopen);

  if (statusCard === "ajustes" || allowsReopen) {
    return "devolvido_para_correcao";
  }
  if (statusCard === "aguardando") {
    return "aguardando_mesa";
  }
  if (statusCard === "aprovado") {
    return "aprovado";
  }
  if (statusCard === "aberto") {
    return "laudo_em_coleta";
  }
  if (!Number.isFinite(laudoId) || laudoId <= 0) {
    return "analise_livre";
  }
  return "pre_laudo";
}

export function transitionKindIsExplicit(
  value: unknown,
): value is MobileLifecycleTransitionKind {
  return TRANSITION_KINDS.has(value as MobileLifecycleTransitionKind);
}

export function preferredSurfaceIsExplicit(
  value: unknown,
): value is MobilePreferredSurface {
  return PREFERRED_SURFACES.has(value as MobilePreferredSurface);
}
