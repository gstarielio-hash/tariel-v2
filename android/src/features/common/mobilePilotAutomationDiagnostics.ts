import type { MobileV2ReadRenderMetadata } from "../../config/mobileV2HumanValidation";
import type {
  MobilePilotRequestTracePhase,
  MobilePilotRequestRouteMode,
  MobilePilotRequestTraceSummary,
} from "../../config/mobilePilotRequestTrace";

export type ActivityCenterAutomationPhase =
  | "idle"
  | "loading"
  | "settled"
  | "error";

export type ActivityCenterAutomationSkipReason =
  | "already_monitoring"
  | "network_blocked"
  | "no_target"
  | null;

export type ActivityCenterAutomationTerminalState =
  | "no_request"
  | "empty"
  | "loaded_legacy"
  | "loaded_v2"
  | "loaded_unknown"
  | "error";

export interface HistorySelectionAutomationDiagnostics {
  targetTappedId: number | null;
  callbackFiredId: number | null;
  callbackCompletedId: number | null;
  selectionLostId: number | null;
}

export interface RuntimeFlagAutomationDiagnostics {
  enabled: boolean;
  rawValue: string | null;
  source: string | null;
}

export interface ActivityCenterAutomationDiagnostics {
  modalVisible: boolean;
  phase: ActivityCenterAutomationPhase;
  requestDispatched: boolean;
  requestedTargetIds: number[];
  notificationCount: number;
  feedReadMetadata: MobileV2ReadRenderMetadata | null;
  requestTrace: MobilePilotRequestTraceSummary | null;
  skipReason: ActivityCenterAutomationSkipReason;
}

export function createEmptyHistorySelectionAutomationDiagnostics(): HistorySelectionAutomationDiagnostics {
  return {
    targetTappedId: null,
    callbackFiredId: null,
    callbackCompletedId: null,
    selectionLostId: null,
  };
}

function normalizeAutomationId(
  value: number | null | undefined,
): number | null {
  const normalized =
    typeof value === "number" && Number.isFinite(value) && value > 0
      ? Math.round(value)
      : null;
  return normalized;
}

function normalizeRequestedTargetIds(values: readonly number[]): number[] {
  return Array.from(
    new Set(
      values
        .map((item) => Number(item))
        .filter((item) => Number.isFinite(item) && item > 0)
        .map((item) => Math.round(item)),
    ),
  );
}

function formatTerminalStateIdSuffix(
  state: ActivityCenterAutomationTerminalState,
): string {
  switch (state) {
    case "no_request":
      return "no-request";
    case "empty":
      return "empty";
    case "loaded_legacy":
      return "loaded-legacy";
    case "loaded_v2":
      return "loaded-v2";
    case "loaded_unknown":
      return "loaded-unknown";
    case "error":
      return "error";
  }
}

function formatSkipReasonIdSuffix(
  skipReason: ActivityCenterAutomationSkipReason,
): string | null {
  switch (skipReason) {
    case "already_monitoring":
      return "already-monitoring";
    case "network_blocked":
      return "network-blocked";
    case "no_target":
      return "no-target";
    default:
      return null;
  }
}

function formatRequestPhaseIdSuffix(
  phase: MobilePilotRequestTracePhase,
): string {
  switch (phase) {
    case "intent_created":
      return "intent-created";
    case "request_sent":
      return "request-sent";
    case "response_received":
      return "response-received";
    case "request_failed":
      return "request-failed";
    case "request_cancelled":
      return "request-cancelled";
    default:
      return "not-created";
  }
}

function formatRequestRouteIdSuffix(
  routeMode: MobilePilotRequestRouteMode,
): string {
  switch (routeMode) {
    case "legacy":
      return "legacy";
    case "v2":
      return "v2";
    default:
      return "unknown";
  }
}

function formatGenericIdSuffix(
  value: string | null | undefined,
): string | null {
  const normalized = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.:-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || null;
}

function sanitizeProbeValue(
  value: string | number | null | undefined,
  fallback = "none",
): string {
  const normalized = String(value ?? "").trim();
  if (!normalized) {
    return fallback;
  }
  return normalized.replace(/[;\n\r]+/g, ",").slice(0, 180);
}

export function resolveActivityCenterAutomationDeliveryMode(
  activityCenter: ActivityCenterAutomationDiagnostics,
): "legacy" | "not_started" | "unknown" | "v2" {
  const deliveryMode =
    activityCenter.feedReadMetadata?.deliveryMode ||
    activityCenter.requestTrace?.deliveryMode ||
    null;
  if (deliveryMode === "v2") {
    return "v2";
  }
  if (deliveryMode === "legacy") {
    return "legacy";
  }
  if (!activityCenter.requestDispatched) {
    return "not_started";
  }
  return "unknown";
}

export function resolveActivityCenterAutomationTerminalState(
  activityCenter: ActivityCenterAutomationDiagnostics,
): ActivityCenterAutomationTerminalState | null {
  if (!activityCenter.modalVisible) {
    return null;
  }
  if (activityCenter.phase === "loading") {
    return null;
  }
  if (activityCenter.phase === "error") {
    return "error";
  }
  if (activityCenter.phase !== "settled") {
    return null;
  }
  if (!activityCenter.requestDispatched) {
    return "no_request";
  }
  if (activityCenter.notificationCount <= 0) {
    return "empty";
  }
  const deliveryMode =
    resolveActivityCenterAutomationDeliveryMode(activityCenter);
  if (deliveryMode === "v2") {
    return "loaded_v2";
  }
  if (deliveryMode === "legacy") {
    return "loaded_legacy";
  }
  return "loaded_unknown";
}

export function recordHistorySelectionTap(
  current: HistorySelectionAutomationDiagnostics,
  targetId: number | null,
): HistorySelectionAutomationDiagnostics {
  const normalizedTargetId = normalizeAutomationId(targetId);
  return {
    ...current,
    targetTappedId: normalizedTargetId,
    callbackFiredId: normalizedTargetId,
    callbackCompletedId: null,
    selectionLostId:
      current.selectionLostId === normalizedTargetId
        ? null
        : current.selectionLostId,
  };
}

export function recordHistorySelectionCallbackCompleted(
  current: HistorySelectionAutomationDiagnostics,
  targetId: number | null,
): HistorySelectionAutomationDiagnostics {
  return {
    ...current,
    callbackCompletedId: normalizeAutomationId(targetId),
  };
}

export function syncHistorySelectionWithShell(params: {
  current: HistorySelectionAutomationDiagnostics;
  selectedHistoryItemId: number | null;
  previousSelectedHistoryItemId: number | null;
}): HistorySelectionAutomationDiagnostics {
  const selectedHistoryItemId = normalizeAutomationId(
    params.selectedHistoryItemId,
  );
  if (selectedHistoryItemId) {
    if (params.current.selectionLostId !== selectedHistoryItemId) {
      return params.current;
    }
    return {
      ...params.current,
      selectionLostId: null,
    };
  }

  const previousSelectedHistoryItemId = normalizeAutomationId(
    params.previousSelectedHistoryItemId,
  );
  if (
    previousSelectedHistoryItemId &&
    params.current.callbackCompletedId === previousSelectedHistoryItemId &&
    params.current.selectionLostId !== previousSelectedHistoryItemId
  ) {
    return {
      ...params.current,
      selectionLostId: previousSelectedHistoryItemId,
    };
  }

  return params.current;
}

export function buildPilotAutomationMarkerIds(params: {
  selectedHistoryItemId: number | null;
  historySelection: HistorySelectionAutomationDiagnostics;
  activityCenter: ActivityCenterAutomationDiagnostics;
}): string[] {
  const ids = new Set<string>();
  const selectedHistoryItemId = normalizeAutomationId(
    params.selectedHistoryItemId,
  );
  const targetTappedId = normalizeAutomationId(
    params.historySelection.targetTappedId,
  );
  const callbackFiredId = normalizeAutomationId(
    params.historySelection.callbackFiredId,
  );
  const callbackCompletedId = normalizeAutomationId(
    params.historySelection.callbackCompletedId,
  );
  const selectionLostId = normalizeAutomationId(
    params.historySelection.selectionLostId,
  );

  if (targetTappedId) {
    ids.add(`history-target-tapped-${targetTappedId}`);
  }
  if (callbackFiredId) {
    ids.add(`history-selection-callback-fired-${callbackFiredId}`);
  }
  if (callbackCompletedId) {
    ids.add(`history-selection-callback-completed-${callbackCompletedId}`);
  }

  if (selectedHistoryItemId) {
    ids.add("selected-history-item-marker");
    ids.add(`selected-history-item-id-${selectedHistoryItemId}`);
    ids.add("authenticated-shell-selected-laudo-marker");
    ids.add(`authenticated-shell-selected-laudo-id-${selectedHistoryItemId}`);
    if (callbackCompletedId === selectedHistoryItemId) {
      ids.add(`authenticated-shell-selection-ready-${selectedHistoryItemId}`);
    }
  } else {
    ids.add("selected-history-item-none");
  }
  if (selectionLostId) {
    ids.add(`authenticated-shell-selection-lost-${selectionLostId}`);
  }

  for (const markerId of buildActivityCenterAutomationMarkerIds(
    params.activityCenter,
  )) {
    ids.add(markerId);
  }

  return Array.from(ids);
}

export function buildActivityCenterAutomationMarkerIds(
  activityCenter: ActivityCenterAutomationDiagnostics,
): string[] {
  if (!activityCenter.modalVisible) {
    return [];
  }

  const ids = new Set<string>();
  ids.add("activity-center-open");

  const requestedTargetIds = normalizeRequestedTargetIds(
    activityCenter.requestedTargetIds,
  );
  if (activityCenter.requestDispatched) {
    ids.add("activity-center-request-dispatched");
    for (const targetId of requestedTargetIds) {
      ids.add(`activity-center-request-target-${targetId}`);
    }
  } else {
    ids.add("activity-center-request-not-started");
  }

  if (activityCenter.phase === "loading") {
    ids.add("activity-center-state-loading");
    return Array.from(ids);
  }

  if (activityCenter.requestTrace) {
    ids.add("activity-center-request-trace-present");
    ids.add(
      `activity-center-request-phase-${formatRequestPhaseIdSuffix(activityCenter.requestTrace.phase)}`,
    );
    ids.add(
      `activity-center-request-route-decision-${formatRequestRouteIdSuffix(activityCenter.requestTrace.routeDecision)}`,
    );
    ids.add(
      `activity-center-request-actual-route-${formatRequestRouteIdSuffix(activityCenter.requestTrace.actualRoute)}`,
    );
    ids.add(
      activityCenter.requestTrace.contractFlagEnabled
        ? "activity-center-request-flag-enabled"
        : "activity-center-request-flag-disabled",
    );
    const failureKindIdSuffix = formatGenericIdSuffix(
      activityCenter.requestTrace.failureKind,
    );
    if (failureKindIdSuffix) {
      ids.add(`activity-center-request-failure-${failureKindIdSuffix}`);
    }
    const fallbackReasonIdSuffix = formatGenericIdSuffix(
      activityCenter.requestTrace.fallbackReason,
    );
    if (fallbackReasonIdSuffix) {
      ids.add(`activity-center-request-fallback-${fallbackReasonIdSuffix}`);
    }
  }

  const terminalState =
    resolveActivityCenterAutomationTerminalState(activityCenter);
  if (terminalState) {
    ids.add("activity-center-terminal-state");
    ids.add(
      `activity-center-terminal-state-${formatTerminalStateIdSuffix(terminalState)}`,
    );
    switch (terminalState) {
      case "no_request":
        ids.add("activity-center-state-no-request");
        break;
      case "empty":
        ids.add("activity-center-state-empty");
        break;
      case "loaded_legacy":
        ids.add("activity-center-state-loaded");
        ids.add("activity-center-state-loaded-legacy");
        break;
      case "loaded_v2":
        ids.add("activity-center-state-loaded");
        ids.add("activity-center-state-loaded-v2");
        break;
      case "loaded_unknown":
        ids.add("activity-center-state-loaded");
        ids.add("activity-center-state-loaded-unknown");
        break;
      case "error":
        ids.add("activity-center-state-error");
        break;
    }
  }

  const deliveryMode =
    resolveActivityCenterAutomationDeliveryMode(activityCenter);
  if (deliveryMode === "v2") {
    ids.add("activity-center-feed-v2-served");
    ids.add("activity-center-feed-v2-ready");
    for (const targetId of requestedTargetIds) {
      ids.add(`activity-center-feed-v2-target-${targetId}`);
    }
  } else if (deliveryMode === "legacy") {
    ids.add("activity-center-feed-legacy-served");
  } else if (deliveryMode === "unknown") {
    ids.add("activity-center-feed-delivery-unknown");
  }

  const skipReasonIdSuffix = formatSkipReasonIdSuffix(
    activityCenter.skipReason,
  );
  if (skipReasonIdSuffix) {
    ids.add(`activity-center-skip-${skipReasonIdSuffix}`);
  }

  return Array.from(ids);
}

export function buildActivityCenterAutomationProbeLabel(
  activityCenter: ActivityCenterAutomationDiagnostics,
): string {
  const requestedTargets = normalizeRequestedTargetIds(
    activityCenter.requestedTargetIds,
  );
  const terminalState =
    resolveActivityCenterAutomationTerminalState(activityCenter) || "none";
  const deliveryMode =
    resolveActivityCenterAutomationDeliveryMode(activityCenter);
  const requestTrace = activityCenter.requestTrace;

  return [
    "pilot_activity_center_probe",
    `phase=${activityCenter.phase}`,
    `terminal_state=${terminalState}`,
    `request_dispatched=${activityCenter.requestDispatched ? "true" : "false"}`,
    `requested_targets=${
      requestedTargets.length ? requestedTargets.join(",") : "none"
    }`,
    `delivery=${deliveryMode}`,
    `notification_count=${Math.max(0, Math.round(activityCenter.notificationCount))}`,
    `skip_reason=${activityCenter.skipReason || "none"}`,
    `request_phase=${requestTrace?.phase || "not_created"}`,
    `request_trace_id=${sanitizeProbeValue(requestTrace?.traceId)}`,
    `request_flag_enabled=${
      requestTrace
        ? requestTrace.contractFlagEnabled
          ? "true"
          : "false"
        : "unknown"
    }`,
    `request_flag_raw_value=${sanitizeProbeValue(requestTrace?.contractFlagRawValue)}`,
    `request_flag_source=${sanitizeProbeValue(requestTrace?.contractFlagSource)}`,
    `request_route_decision=${requestTrace?.routeDecision || "unknown"}`,
    `request_decision_reason=${sanitizeProbeValue(requestTrace?.decisionReason)}`,
    `request_decision_source=${sanitizeProbeValue(requestTrace?.decisionSource)}`,
    `request_actual_route=${requestTrace?.actualRoute || "unknown"}`,
    `request_attempt_sequence=${sanitizeProbeValue(
      requestTrace?.attemptSequence?.join("|") || "none",
    )}`,
    `request_endpoint_path=${sanitizeProbeValue(requestTrace?.endpointPath)}`,
    `request_status=${
      typeof requestTrace?.responseStatus === "number"
        ? String(requestTrace.responseStatus)
        : "none"
    }`,
    `request_failure_kind=${sanitizeProbeValue(requestTrace?.failureKind)}`,
    `request_fallback_reason=${sanitizeProbeValue(requestTrace?.fallbackReason)}`,
    `request_backend_request_id=${sanitizeProbeValue(
      requestTrace?.backendRequestId,
    )}`,
    `request_validation_session=${sanitizeProbeValue(
      requestTrace?.validationSessionId,
    )}`,
    `request_operator_run=${sanitizeProbeValue(requestTrace?.operatorRunId)}`,
  ].join(";");
}

export function buildPilotAutomationProbeLabel(params: {
  selectedHistoryItemId: number | null;
  historySelection: HistorySelectionAutomationDiagnostics;
  activityCenter: ActivityCenterAutomationDiagnostics;
  runtimeFlag: RuntimeFlagAutomationDiagnostics;
}): string {
  const selectedHistoryItemId = normalizeAutomationId(
    params.selectedHistoryItemId,
  );
  const targetTappedId = normalizeAutomationId(
    params.historySelection.targetTappedId,
  );
  const callbackFiredId = normalizeAutomationId(
    params.historySelection.callbackFiredId,
  );
  const callbackCompletedId = normalizeAutomationId(
    params.historySelection.callbackCompletedId,
  );
  const selectionLostId = normalizeAutomationId(
    params.historySelection.selectionLostId,
  );
  const selectionReadyId =
    selectedHistoryItemId && callbackCompletedId === selectedHistoryItemId
      ? selectedHistoryItemId
      : null;
  const feedDeliveryMode = resolveActivityCenterAutomationDeliveryMode(
    params.activityCenter,
  );
  const terminalState =
    resolveActivityCenterAutomationTerminalState(params.activityCenter) ||
    "none";

  return [
    "pilot_selection_probe",
    `target_tapped=${targetTappedId || "none"}`,
    `callback_fired=${callbackFiredId || "none"}`,
    `callback_completed=${callbackCompletedId || "none"}`,
    `selected_laudo_id=${selectedHistoryItemId || "none"}`,
    `selection_ready=${selectionReadyId || "none"}`,
    `selection_lost=${selectionLostId || "none"}`,
    `runtime_flag_enabled=${params.runtimeFlag.enabled ? "true" : "false"}`,
    `runtime_flag_raw_value=${sanitizeProbeValue(params.runtimeFlag.rawValue)}`,
    `runtime_flag_source=${sanitizeProbeValue(params.runtimeFlag.source)}`,
    `activity_center_phase=${params.activityCenter.phase}`,
    `activity_center_terminal_state=${terminalState}`,
    `activity_center_delivery=${feedDeliveryMode}`,
    `activity_center_skip_reason=${params.activityCenter.skipReason || "none"}`,
  ].join(";");
}
