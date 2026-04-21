import type { MobileV2ReadDeliveryMode } from "./mobileV2HumanValidation";
import type { MobileV2UsageMode } from "./mobileV2Rollout";

export type MobilePilotRequestTracePhase =
  | "not_created"
  | "intent_created"
  | "request_sent"
  | "response_received"
  | "request_failed"
  | "request_cancelled";

export type MobilePilotRequestRouteMode = "legacy" | "unknown" | "v2";

export interface MobilePilotRequestTraceSummary {
  traceId: string;
  surface: "feed" | "thread";
  method: string;
  contractFlagEnabled: boolean;
  contractFlagRawValue?: string | null;
  contractFlagSource?: string | null;
  routeDecision: MobilePilotRequestRouteMode;
  decisionReason?: string | null;
  decisionSource?: string | null;
  actualRoute: MobilePilotRequestRouteMode;
  attemptSequence: MobilePilotRequestRouteMode[];
  endpointPath: string | null;
  phase: MobilePilotRequestTracePhase;
  targetIds: number[];
  validationSessionId: string | null;
  operatorRunId: string | null;
  usageMode: MobileV2UsageMode | null;
  responseStatus: number | null;
  backendRequestId: string | null;
  failureKind: string | null;
  failureDetail: string | null;
  fallbackReason: string | null;
  deliveryMode: MobileV2ReadDeliveryMode | null;
}

function normalizeTraceToken(value: string | null | undefined): string {
  const normalized = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.:-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || "unknown";
}

function normalizeMethod(value: string | null | undefined): string {
  const normalized = String(value || "GET")
    .trim()
    .toUpperCase();
  return normalized || "GET";
}

function normalizeEndpointPath(
  value: string | null | undefined,
): string | null {
  const normalized = String(value || "").trim();
  return normalized || null;
}

export function normalizePilotRequestTargetIds(
  values: readonly number[],
): number[] {
  return Array.from(
    new Set(
      values
        .map((item) => Number(item))
        .filter((item) => Number.isFinite(item) && item > 0)
        .map((item) => Math.round(item)),
    ),
  );
}

function normalizeRouteMode(
  value: string | null | undefined,
): MobilePilotRequestRouteMode {
  return value === "v2" || value === "legacy" ? value : "unknown";
}

function normalizePhase(
  value: string | null | undefined,
): MobilePilotRequestTracePhase {
  switch (value) {
    case "intent_created":
    case "request_sent":
    case "response_received":
    case "request_failed":
    case "request_cancelled":
      return value;
    default:
      return "not_created";
  }
}

export function generateMobilePilotRequestTraceId(prefix = "central"): string {
  const cryptoUuid = globalThis.crypto?.randomUUID?.();
  if (typeof cryptoUuid === "string" && cryptoUuid.trim()) {
    return `${normalizeTraceToken(prefix)}-${normalizeTraceToken(cryptoUuid)}`.slice(
      0,
      64,
    );
  }

  const timestamp = Date.now().toString(36);
  const randomSegment = Math.random().toString(36).slice(2, 10);
  return `${normalizeTraceToken(prefix)}-${timestamp}-${randomSegment}`.slice(
    0,
    64,
  );
}

export function buildMobilePilotRequestTraceSummary(params: {
  surface: "feed" | "thread";
  contractFlagEnabled: boolean;
  contractFlagRawValue?: string | null;
  contractFlagSource?: string | null;
  routeDecision: MobilePilotRequestRouteMode;
  decisionReason?: string | null;
  decisionSource?: string | null;
  targetIds: number[];
  validationSessionId?: string | null;
  operatorRunId?: string | null;
  usageMode?: MobileV2UsageMode | null;
  traceId?: string | null;
  method?: string | null;
}): MobilePilotRequestTraceSummary {
  return {
    traceId:
      String(params.traceId || "").trim() ||
      generateMobilePilotRequestTraceId(params.surface),
    surface: params.surface,
    method: normalizeMethod(params.method),
    contractFlagEnabled: Boolean(params.contractFlagEnabled),
    contractFlagRawValue:
      params.contractFlagRawValue !== undefined
        ? String(params.contractFlagRawValue || "").trim() || null
        : null,
    contractFlagSource:
      params.contractFlagSource !== undefined
        ? normalizeTraceToken(params.contractFlagSource)
        : null,
    routeDecision: normalizeRouteMode(params.routeDecision),
    decisionReason:
      params.decisionReason !== undefined
        ? normalizeTraceToken(params.decisionReason)
        : null,
    decisionSource:
      params.decisionSource !== undefined
        ? normalizeTraceToken(params.decisionSource)
        : null,
    actualRoute: "unknown",
    attemptSequence: [],
    endpointPath: null,
    phase: "intent_created",
    targetIds: normalizePilotRequestTargetIds(params.targetIds),
    validationSessionId:
      String(params.validationSessionId || "").trim() || null,
    operatorRunId: String(params.operatorRunId || "").trim() || null,
    usageMode:
      params.usageMode === "organic_validation" ? params.usageMode : null,
    responseStatus: null,
    backendRequestId: null,
    failureKind: null,
    failureDetail: null,
    fallbackReason: null,
    deliveryMode: null,
  };
}

export function updateMobilePilotRequestTraceSummary(
  current: MobilePilotRequestTraceSummary,
  patch: Partial<MobilePilotRequestTraceSummary>,
): MobilePilotRequestTraceSummary {
  const attemptSequence =
    patch.attemptSequence !== undefined
      ? patch.attemptSequence
      : current.attemptSequence;
  return {
    ...current,
    ...patch,
    traceId: String(patch.traceId || current.traceId).trim() || current.traceId,
    method: normalizeMethod(patch.method || current.method),
    contractFlagRawValue:
      patch.contractFlagRawValue !== undefined
        ? String(patch.contractFlagRawValue || "").trim() || null
        : (current.contractFlagRawValue ?? null),
    contractFlagSource:
      patch.contractFlagSource !== undefined
        ? patch.contractFlagSource === null
          ? null
          : normalizeTraceToken(patch.contractFlagSource)
        : (current.contractFlagSource ?? null),
    routeDecision: normalizeRouteMode(
      patch.routeDecision || current.routeDecision,
    ),
    decisionReason:
      patch.decisionReason !== undefined
        ? patch.decisionReason === null
          ? null
          : normalizeTraceToken(patch.decisionReason)
        : (current.decisionReason ?? null),
    decisionSource:
      patch.decisionSource !== undefined
        ? patch.decisionSource === null
          ? null
          : normalizeTraceToken(patch.decisionSource)
        : (current.decisionSource ?? null),
    actualRoute: normalizeRouteMode(patch.actualRoute || current.actualRoute),
    attemptSequence: Array.from(
      new Set(
        (attemptSequence || [])
          .map((item) => normalizeRouteMode(item))
          .filter((item) => item !== "unknown"),
      ),
    ),
    endpointPath: normalizeEndpointPath(
      patch.endpointPath !== undefined
        ? patch.endpointPath
        : current.endpointPath,
    ),
    phase: normalizePhase(patch.phase || current.phase),
    targetIds: normalizePilotRequestTargetIds(
      patch.targetIds || current.targetIds,
    ),
    validationSessionId:
      patch.validationSessionId !== undefined
        ? String(patch.validationSessionId || "").trim() || null
        : current.validationSessionId,
    operatorRunId:
      patch.operatorRunId !== undefined
        ? String(patch.operatorRunId || "").trim() || null
        : current.operatorRunId,
    usageMode:
      patch.usageMode !== undefined
        ? patch.usageMode === "organic_validation"
          ? patch.usageMode
          : null
        : current.usageMode,
    responseStatus:
      typeof patch.responseStatus === "number" &&
      Number.isFinite(patch.responseStatus)
        ? Math.round(patch.responseStatus)
        : patch.responseStatus === null
          ? null
          : current.responseStatus,
    backendRequestId:
      patch.backendRequestId !== undefined
        ? String(patch.backendRequestId || "").trim() || null
        : current.backendRequestId,
    failureKind:
      patch.failureKind !== undefined
        ? patch.failureKind === null
          ? null
          : normalizeTraceToken(patch.failureKind)
        : current.failureKind,
    failureDetail:
      patch.failureDetail !== undefined
        ? String(patch.failureDetail || "")
            .trim()
            .slice(0, 180) || null
        : current.failureDetail,
    fallbackReason:
      patch.fallbackReason !== undefined
        ? patch.fallbackReason === null
          ? null
          : normalizeTraceToken(patch.fallbackReason)
        : current.fallbackReason,
    deliveryMode:
      patch.deliveryMode === "legacy" || patch.deliveryMode === "v2"
        ? patch.deliveryMode
        : patch.deliveryMode === null
          ? null
          : current.deliveryMode,
  };
}

export function appendMobilePilotRequestAttempt(
  current: MobilePilotRequestTraceSummary,
  routeMode: MobilePilotRequestRouteMode,
): MobilePilotRequestTraceSummary {
  if (routeMode === "unknown") {
    return current;
  }
  return updateMobilePilotRequestTraceSummary(current, {
    actualRoute: routeMode,
    attemptSequence: [...current.attemptSequence, routeMode],
  });
}

export function classifyMobilePilotRequestFailure(error: unknown): {
  failureDetail: string;
  failureKind: string;
  phase: MobilePilotRequestTracePhase;
} {
  const detail =
    error instanceof Error
      ? String(error.message || error.name || "request_failed")
      : "request_failed";
  const normalizedDetail = detail.trim() || "request_failed";
  const errorName =
    error instanceof Error
      ? String(error.name || "")
          .trim()
          .toLowerCase()
      : "";
  const cancelled =
    errorName === "aborterror" || /abort|cancel/i.test(normalizedDetail);

  return {
    phase: cancelled ? "request_cancelled" : "request_failed",
    failureKind: cancelled ? "cancelled" : "request_failed",
    failureDetail: normalizedDetail.slice(0, 180),
  };
}
