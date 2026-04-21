import {
  buildApiUrl,
  construirHeaders,
  extrairMensagemErro,
  fetchComObservabilidade,
  lerJsonSeguro,
} from "./apiCore";
import { androidV2ReadContractsEnabled } from "./mobileV2Config";
import { MobileV2ContractError } from "./mobileV2MesaAdapter";

type JsonRecord = Record<string, unknown>;

export type MobileV2ReadTarget = "feed" | "thread";
export type MobileV2RolloutState =
  | "legacy_only"
  | "pilot_enabled"
  | "candidate_for_promotion"
  | "promoted"
  | "hold"
  | "rollback_forced";

export type MobileV2FallbackReason =
  | "rollout_denied"
  | "legacy_only"
  | "hold"
  | "rollback_forced"
  | "route_disabled"
  | "rollout_unknown"
  | "capabilities_fetch_error"
  | "http_404"
  | "http_error"
  | "parse_error"
  | "visibility_violation"
  | "adapter_error"
  | "unknown";

export type MobileV2UsageMode = "organic_validation";

export interface MobileV2OrganicValidationSurfaceSummary {
  surface: MobileV2ReadTarget;
  suggested_target_ids: number[];
  covered_target_ids: number[];
  missing_target_ids: number[];
  distinct_targets_observed: number;
  coverage_met: boolean;
  targets_available: boolean;
  detail: string | null;
}

export interface MobileV2CapabilitiesResponse {
  ok: boolean;
  contract_name: "MobileInspectorCapabilitiesV2";
  contract_version: "v2";
  capabilities_version: string;
  mobile_v2_reads_enabled: boolean;
  mobile_v2_feed_enabled: boolean;
  mobile_v2_thread_enabled: boolean;
  tenant_allowed: boolean;
  cohort_allowed: boolean;
  reason: string;
  rollout_reason: string;
  source: string;
  feed_reason: string;
  feed_source: string;
  thread_reason: string;
  thread_source: string;
  rollout_bucket: number | null;
  rollout_state: MobileV2RolloutState;
  feed_rollout_state: MobileV2RolloutState;
  thread_rollout_state: MobileV2RolloutState;
  feed_candidate_for_promotion: boolean;
  thread_candidate_for_promotion: boolean;
  feed_promoted: boolean;
  thread_promoted: boolean;
  feed_hold: boolean;
  thread_hold: boolean;
  feed_rollback_forced: boolean;
  thread_rollback_forced: boolean;
  feed_promoted_since: string | null;
  thread_promoted_since: string | null;
  feed_rollout_window_started_at: string | null;
  thread_rollout_window_started_at: string | null;
  feed_rollback_window_until: string | null;
  thread_rollback_window_until: string | null;
  feed_rollback_window_active: boolean;
  thread_rollback_window_active: boolean;
  organic_validation_active: boolean;
  organic_validation_session_id: string | null;
  organic_validation_surfaces: MobileV2ReadTarget[];
  organic_validation_target_suggestions: MobileV2OrganicValidationSurfaceSummary[];
  organic_validation_surface_coverage: MobileV2OrganicValidationSurfaceSummary[];
  organic_validation_has_partial_coverage: boolean;
  organic_validation_targets_ready: boolean;
  operator_validation_run_active: boolean;
  operator_validation_run_id: string | null;
  operator_validation_required_surfaces: MobileV2ReadTarget[];
  mobile_v2_architecture_status?: string | null;
  mobile_v2_architecture_reason?: string | null;
  mobile_v2_legacy_fallback_policy?: string | null;
  mobile_v2_transition_active?: boolean;
}

export interface MobileV2RouteDecision {
  localFlagEnabled: boolean;
  shouldUseV2: boolean;
  reason: string;
  source: string;
  fallbackReason: MobileV2FallbackReason | null;
  capabilities?: MobileV2CapabilitiesResponse;
}

export interface MobileV2LegacyFallbackMetadata {
  route: MobileV2ReadTarget;
  reason: MobileV2FallbackReason;
  source?: string;
  capabilitiesVersion?: string | null;
  rolloutBucket?: number | null;
  usageMode?: MobileV2UsageMode | null;
  validationSessionId?: string | null;
  operatorRunId?: string | null;
}

export interface MobileV2AttemptMetadata {
  route: MobileV2ReadTarget;
  capabilitiesVersion?: string | null;
  rolloutBucket?: number | null;
  usageMode?: MobileV2UsageMode | null;
  validationSessionId?: string | null;
  operatorRunId?: string | null;
}

const MOBILE_V2_CAPABILITIES_CONTRACT = "MobileInspectorCapabilitiesV2";
export const MOBILE_V2_CAPABILITIES_TTL_MS = 15_000;
export const MOBILE_V2_CAPABILITIES_PILOT_TTL_MS = 5_000;
export const MOBILE_V2_CAPABILITIES_EMERGENCY_TTL_MS = 3_000;
const MOBILE_V2_CAPABILITIES_CACHE_MAX_ENTRIES = 4;
const MOBILE_V2_ATTEMPTED_HEADER = "X-Tariel-Mobile-V2-Attempted";
const MOBILE_V2_ROUTE_HEADER = "X-Tariel-Mobile-V2-Route";
const MOBILE_V2_FALLBACK_REASON_HEADER = "X-Tariel-Mobile-V2-Fallback-Reason";
const MOBILE_V2_GATE_SOURCE_HEADER = "X-Tariel-Mobile-V2-Gate-Source";
const MOBILE_V2_CAPABILITIES_VERSION_HEADER =
  "X-Tariel-Mobile-V2-Capabilities-Version";
const MOBILE_V2_ROLLOUT_BUCKET_HEADER = "X-Tariel-Mobile-V2-Rollout-Bucket";
const MOBILE_V2_USAGE_MODE_HEADER = "X-Tariel-Mobile-Usage-Mode";
const MOBILE_V2_VALIDATION_SESSION_HEADER =
  "X-Tariel-Mobile-Validation-Session";
const MOBILE_V2_OPERATOR_RUN_HEADER = "X-Tariel-Mobile-Operator-Run";
const MOBILE_V2_READ_ALLOWED_STATES = new Set<MobileV2RolloutState>([
  "pilot_enabled",
  "candidate_for_promotion",
  "promoted",
]);
const MOBILE_V2_EMERGENCY_STATES = new Set<MobileV2RolloutState>([
  "hold",
  "rollback_forced",
]);

const capabilitiesCache = new Map<
  string,
  {
    expiresAt: number;
    capabilities: MobileV2CapabilitiesResponse;
  }
>();

class MobileV2CapabilitiesError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "MobileV2CapabilitiesError";
    this.code = code;
  }
}

function erroCapabilities(
  code: string,
  message: string,
): MobileV2CapabilitiesError {
  return new MobileV2CapabilitiesError(code, message);
}

function lerRegistro(value: unknown, label: string): JsonRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw erroCapabilities(
      "invalid_record",
      `${label} invalido no rollout mobile V2.`,
    );
  }
  return value as JsonRecord;
}

function lerBoolean(record: JsonRecord, field: string, label: string): boolean {
  const value = record[field];
  if (typeof value !== "boolean") {
    throw erroCapabilities(
      "invalid_boolean",
      `${label}.${field} precisa ser boolean.`,
    );
  }
  return value;
}

function lerBooleanOpcional(
  record: JsonRecord,
  field: string,
  fallback: boolean,
): boolean {
  const value = record[field];
  return typeof value === "boolean" ? value : fallback;
}

function lerString(record: JsonRecord, field: string, label: string): string {
  const value = record[field];
  if (typeof value !== "string" || !value.trim()) {
    throw erroCapabilities(
      "invalid_string",
      `${label}.${field} precisa ser string.`,
    );
  }
  return value.trim();
}

function lerStringOpcional(record: JsonRecord, field: string): string | null {
  const value = record[field];
  if (value === null || value === undefined || value === "") {
    return null;
  }
  if (typeof value !== "string") {
    throw erroCapabilities(
      "invalid_string",
      `mobile_v2_capabilities.${field} precisa ser string ou null.`,
    );
  }
  return value.trim() || null;
}

function lerListaStringsOpcional(record: JsonRecord, field: string): string[] {
  const value = record[field];
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
}

function lerListaInteirosOpcional(record: JsonRecord, field: string): number[] {
  const value = record[field];
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) =>
      typeof item === "number" && Number.isFinite(item) ? item : null,
    )
    .filter((item): item is number => item !== null && item > 0)
    .map((item) => Math.trunc(item));
}

function lerNullableNumber(
  record: JsonRecord,
  field: string,
  label: string,
): number | null {
  const value = record[field];
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw erroCapabilities(
      "invalid_number",
      `${label}.${field} precisa ser numero ou null.`,
    );
  }
  return value;
}

function isMobileV2RolloutState(value: string): value is MobileV2RolloutState {
  return (
    value === "legacy_only" ||
    value === "pilot_enabled" ||
    value === "candidate_for_promotion" ||
    value === "promoted" ||
    value === "hold" ||
    value === "rollback_forced"
  );
}

function lerRolloutStateOpcional(
  record: JsonRecord,
  field: string,
  label: string,
): MobileV2RolloutState | null {
  const value = record[field];
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const normalized = typeof value === "string" ? value.trim() : "";
  if (!isMobileV2RolloutState(normalized)) {
    throw erroCapabilities(
      "invalid_rollout_state",
      `${label}.${field} precisa ser um estado de rollout conhecido.`,
    );
  }
  return normalized;
}

function inferirRolloutStateLegado(params: {
  enabled: boolean;
  reason: string;
}): MobileV2RolloutState {
  if (params.reason === "hold") {
    return "hold";
  }
  if (params.reason === "rollback_forced") {
    return "rollback_forced";
  }
  if (params.reason === "promoted") {
    return "promoted";
  }
  if (params.reason === "candidate_for_promotion") {
    return "candidate_for_promotion";
  }
  return params.enabled ? "pilot_enabled" : "legacy_only";
}

function rolloutStateAllowsReads(state: MobileV2RolloutState): boolean {
  return MOBILE_V2_READ_ALLOWED_STATES.has(state);
}

function isMobileV2ReadTarget(value: string): value is MobileV2ReadTarget {
  return value === "feed" || value === "thread";
}

function inferirFallbackRemoto(params: {
  rolloutState: MobileV2RolloutState;
  rolloutReason: string;
  routeState: MobileV2RolloutState;
  routeReason: string;
}): MobileV2FallbackReason {
  if (
    params.routeState === "rollback_forced" ||
    params.routeReason === "rollback_forced" ||
    params.rolloutState === "rollback_forced" ||
    params.rolloutReason === "rollback_forced"
  ) {
    return "rollback_forced";
  }
  if (
    params.routeState === "hold" ||
    params.routeReason === "hold" ||
    params.rolloutState === "hold" ||
    params.rolloutReason === "hold"
  ) {
    return "hold";
  }
  if (
    params.routeState === "legacy_only" ||
    params.routeReason === "legacy_only" ||
    params.rolloutState === "legacy_only" ||
    params.rolloutReason === "legacy_only"
  ) {
    return "legacy_only";
  }
  if (
    params.routeReason === "feed_route_disabled" ||
    params.routeReason === "thread_route_disabled"
  ) {
    return "route_disabled";
  }
  return "rollout_denied";
}

function sanitizeHeaderToken(value: unknown): string {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.:-]+/g, "_")
    .replace(/^[_:.-]+|[_:.-]+$/g, "")
    .slice(0, 80);
}

function sanitizeHeaderBucket(value: number | null | undefined): string | null {
  if (!Number.isFinite(value ?? Number.NaN)) {
    return null;
  }
  return String(Math.max(0, Math.min(99, Number(value))));
}

function parseOrganicValidationSurfaceRecord(
  value: unknown,
): MobileV2OrganicValidationSurfaceSummary | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  const record = value as JsonRecord;
  const surface =
    typeof record.surface === "string" ? record.surface.trim() : "";
  if (!isMobileV2ReadTarget(surface)) {
    return null;
  }
  return {
    surface,
    suggested_target_ids: lerListaInteirosOpcional(
      record,
      "suggested_target_ids",
    ),
    covered_target_ids: lerListaInteirosOpcional(record, "covered_target_ids"),
    missing_target_ids: lerListaInteirosOpcional(record, "missing_target_ids"),
    distinct_targets_observed:
      typeof record.distinct_targets_observed === "number" &&
      Number.isFinite(record.distinct_targets_observed)
        ? Math.max(0, Math.trunc(record.distinct_targets_observed))
        : 0,
    coverage_met:
      typeof record.coverage_met === "boolean" ? record.coverage_met : false,
    targets_available:
      typeof record.targets_available === "boolean"
        ? record.targets_available
        : false,
    detail:
      typeof record.detail === "string" && record.detail.trim()
        ? record.detail.trim()
        : null,
  };
}

function lerOrganicValidationSurfaceRows(
  record: JsonRecord,
  field: string,
): MobileV2OrganicValidationSurfaceSummary[] {
  const value = record[field];
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => parseOrganicValidationSurfaceRecord(item))
    .filter(
      (item): item is MobileV2OrganicValidationSurfaceSummary => item !== null,
    );
}

export function parseMobileV2Capabilities(
  payload: unknown,
): MobileV2CapabilitiesResponse {
  const record = lerRegistro(payload, "mobile_v2_capabilities");
  const contractName = lerString(
    record,
    "contract_name",
    "mobile_v2_capabilities",
  );
  const contractVersion = lerString(
    record,
    "contract_version",
    "mobile_v2_capabilities",
  );
  if (
    contractName !== MOBILE_V2_CAPABILITIES_CONTRACT ||
    contractVersion !== "v2"
  ) {
    throw erroCapabilities(
      "invalid_contract",
      "Rollout mobile V2 retornou um contrato inesperado.",
    );
  }

  const mobileV2ReadsEnabled = lerBoolean(
    record,
    "mobile_v2_reads_enabled",
    "mobile_v2_capabilities",
  );
  const mobileV2FeedEnabled = lerBoolean(
    record,
    "mobile_v2_feed_enabled",
    "mobile_v2_capabilities",
  );
  const mobileV2ThreadEnabled = lerBoolean(
    record,
    "mobile_v2_thread_enabled",
    "mobile_v2_capabilities",
  );
  const reason = lerString(record, "reason", "mobile_v2_capabilities");
  const feedReason = lerString(record, "feed_reason", "mobile_v2_capabilities");
  const threadReason = lerString(
    record,
    "thread_reason",
    "mobile_v2_capabilities",
  );
  const rolloutState =
    lerRolloutStateOpcional(
      record,
      "rollout_state",
      "mobile_v2_capabilities",
    ) ??
    inferirRolloutStateLegado({
      enabled: mobileV2ReadsEnabled,
      reason,
    });
  const feedRolloutState =
    lerRolloutStateOpcional(
      record,
      "feed_rollout_state",
      "mobile_v2_capabilities",
    ) ??
    inferirRolloutStateLegado({
      enabled: mobileV2FeedEnabled,
      reason: feedReason,
    });
  const threadRolloutState =
    lerRolloutStateOpcional(
      record,
      "thread_rollout_state",
      "mobile_v2_capabilities",
    ) ??
    inferirRolloutStateLegado({
      enabled: mobileV2ThreadEnabled,
      reason: threadReason,
    });
  const organicValidationSurfaces = lerListaStringsOpcional(
    record,
    "organic_validation_surfaces",
  ).filter(isMobileV2ReadTarget);

  return {
    ok: lerBoolean(record, "ok", "mobile_v2_capabilities"),
    contract_name: MOBILE_V2_CAPABILITIES_CONTRACT,
    contract_version: "v2",
    capabilities_version: lerString(
      record,
      "capabilities_version",
      "mobile_v2_capabilities",
    ),
    mobile_v2_reads_enabled: mobileV2ReadsEnabled,
    mobile_v2_feed_enabled: mobileV2FeedEnabled,
    mobile_v2_thread_enabled: mobileV2ThreadEnabled,
    tenant_allowed: lerBoolean(
      record,
      "tenant_allowed",
      "mobile_v2_capabilities",
    ),
    cohort_allowed: lerBoolean(
      record,
      "cohort_allowed",
      "mobile_v2_capabilities",
    ),
    reason,
    rollout_reason: lerString(
      record,
      "rollout_reason",
      "mobile_v2_capabilities",
    ),
    source: lerString(record, "source", "mobile_v2_capabilities"),
    feed_reason: feedReason,
    feed_source: lerString(record, "feed_source", "mobile_v2_capabilities"),
    thread_reason: threadReason,
    thread_source: lerString(record, "thread_source", "mobile_v2_capabilities"),
    rollout_bucket: lerNullableNumber(
      record,
      "rollout_bucket",
      "mobile_v2_capabilities",
    ),
    rollout_state: rolloutState,
    feed_rollout_state: feedRolloutState,
    thread_rollout_state: threadRolloutState,
    feed_candidate_for_promotion: lerBooleanOpcional(
      record,
      "feed_candidate_for_promotion",
      feedRolloutState === "candidate_for_promotion",
    ),
    thread_candidate_for_promotion: lerBooleanOpcional(
      record,
      "thread_candidate_for_promotion",
      threadRolloutState === "candidate_for_promotion",
    ),
    feed_promoted: lerBooleanOpcional(
      record,
      "feed_promoted",
      feedRolloutState === "promoted",
    ),
    thread_promoted: lerBooleanOpcional(
      record,
      "thread_promoted",
      threadRolloutState === "promoted",
    ),
    feed_hold: lerBooleanOpcional(
      record,
      "feed_hold",
      feedRolloutState === "hold",
    ),
    thread_hold: lerBooleanOpcional(
      record,
      "thread_hold",
      threadRolloutState === "hold",
    ),
    feed_rollback_forced: lerBooleanOpcional(
      record,
      "feed_rollback_forced",
      feedRolloutState === "rollback_forced",
    ),
    thread_rollback_forced: lerBooleanOpcional(
      record,
      "thread_rollback_forced",
      threadRolloutState === "rollback_forced",
    ),
    feed_promoted_since: lerStringOpcional(record, "feed_promoted_since"),
    thread_promoted_since: lerStringOpcional(record, "thread_promoted_since"),
    feed_rollout_window_started_at: lerStringOpcional(
      record,
      "feed_rollout_window_started_at",
    ),
    thread_rollout_window_started_at: lerStringOpcional(
      record,
      "thread_rollout_window_started_at",
    ),
    feed_rollback_window_until: lerStringOpcional(
      record,
      "feed_rollback_window_until",
    ),
    thread_rollback_window_until: lerStringOpcional(
      record,
      "thread_rollback_window_until",
    ),
    feed_rollback_window_active: lerBooleanOpcional(
      record,
      "feed_rollback_window_active",
      false,
    ),
    thread_rollback_window_active: lerBooleanOpcional(
      record,
      "thread_rollback_window_active",
      false,
    ),
    organic_validation_active: lerBooleanOpcional(
      record,
      "organic_validation_active",
      false,
    ),
    organic_validation_session_id: lerStringOpcional(
      record,
      "organic_validation_session_id",
    ),
    organic_validation_surfaces: organicValidationSurfaces,
    organic_validation_target_suggestions: lerOrganicValidationSurfaceRows(
      record,
      "organic_validation_target_suggestions",
    ),
    organic_validation_surface_coverage: lerOrganicValidationSurfaceRows(
      record,
      "organic_validation_surface_coverage",
    ),
    organic_validation_has_partial_coverage: lerBooleanOpcional(
      record,
      "organic_validation_has_partial_coverage",
      false,
    ),
    organic_validation_targets_ready: lerBooleanOpcional(
      record,
      "organic_validation_targets_ready",
      false,
    ),
    operator_validation_run_active: lerBooleanOpcional(
      record,
      "operator_validation_run_active",
      false,
    ),
    operator_validation_run_id: lerStringOpcional(
      record,
      "operator_validation_run_id",
    ),
    operator_validation_required_surfaces: lerListaStringsOpcional(
      record,
      "operator_validation_required_surfaces",
    ).filter(isMobileV2ReadTarget),
    mobile_v2_architecture_status: lerStringOpcional(
      record,
      "mobile_v2_architecture_status",
    ),
    mobile_v2_architecture_reason: lerStringOpcional(
      record,
      "mobile_v2_architecture_reason",
    ),
    mobile_v2_legacy_fallback_policy: lerStringOpcional(
      record,
      "mobile_v2_legacy_fallback_policy",
    ),
    mobile_v2_transition_active: lerBooleanOpcional(
      record,
      "mobile_v2_transition_active",
      false,
    ),
  };
}

function classificarErroCapabilities(error: unknown): string {
  if (error instanceof MobileV2CapabilitiesError) {
    if (error.code === "remote_gate_http_404") {
      return "http_404";
    }
    if (error.code === "remote_gate_http_error") {
      return "http_error";
    }
    if (error.code.startsWith("invalid_")) {
      return "parse_error";
    }
    return sanitizeHeaderToken(error.code) || "unknown";
  }
  if (error instanceof Error) {
    return "http_error";
  }
  return "unknown";
}

function getCachedCapabilities(
  accessToken: string,
): MobileV2CapabilitiesResponse | null {
  const cached = capabilitiesCache.get(accessToken);
  if (!cached) {
    return null;
  }
  if (Date.now() >= cached.expiresAt) {
    capabilitiesCache.delete(accessToken);
    return null;
  }
  return cached.capabilities;
}

function resolveCapabilitiesTtlMs(
  capabilities: MobileV2CapabilitiesResponse,
): number {
  return MOBILE_V2_EMERGENCY_STATES.has(capabilities.rollout_state) ||
    MOBILE_V2_EMERGENCY_STATES.has(capabilities.feed_rollout_state) ||
    MOBILE_V2_EMERGENCY_STATES.has(capabilities.thread_rollout_state)
    ? MOBILE_V2_CAPABILITIES_EMERGENCY_TTL_MS
    : capabilities.organic_validation_active ||
        capabilities.operator_validation_run_active ||
        capabilities.feed_rollback_window_active ||
        capabilities.thread_rollback_window_active
      ? MOBILE_V2_CAPABILITIES_PILOT_TTL_MS
      : MOBILE_V2_CAPABILITIES_TTL_MS;
}

export function resolveMobileV2OrganicValidationMetadata(
  route: MobileV2ReadTarget,
  capabilities?: MobileV2CapabilitiesResponse | null,
): {
  usageMode: MobileV2UsageMode;
  validationSessionId: string;
  operatorRunId?: string | null;
} | null {
  if (!capabilities?.organic_validation_active) {
    return null;
  }
  const sessionId = sanitizeHeaderToken(
    capabilities.organic_validation_session_id,
  );
  if (!sessionId) {
    return null;
  }
  if (!capabilities.organic_validation_surfaces.includes(route)) {
    return null;
  }
  const operatorRunId =
    capabilities.operator_validation_run_active &&
    capabilities.operator_validation_required_surfaces.includes(route)
      ? sanitizeHeaderToken(capabilities.operator_validation_run_id)
      : null;
  return {
    usageMode: "organic_validation",
    validationSessionId: sessionId,
    ...(operatorRunId ? { operatorRunId } : {}),
  };
}

function setCachedCapabilities(
  accessToken: string,
  capabilities: MobileV2CapabilitiesResponse,
): void {
  if (
    !capabilitiesCache.has(accessToken) &&
    capabilitiesCache.size >= MOBILE_V2_CAPABILITIES_CACHE_MAX_ENTRIES
  ) {
    const oldestKey = capabilitiesCache.keys().next().value;
    if (oldestKey) {
      capabilitiesCache.delete(oldestKey);
    }
  }
  capabilitiesCache.set(accessToken, {
    expiresAt: Date.now() + resolveCapabilitiesTtlMs(capabilities),
    capabilities,
  });
}

export function invalidateMobileV2CapabilitiesCache(
  accessToken?: string | null,
): void {
  const token = String(accessToken || "").trim();
  if (!token) {
    capabilitiesCache.clear();
    return;
  }
  capabilitiesCache.delete(token);
}

async function carregarMobileV2Capabilities(
  accessToken: string,
  options?: { forceRefresh?: boolean },
): Promise<MobileV2CapabilitiesResponse> {
  if (!options?.forceRefresh) {
    const cached = getCachedCapabilities(accessToken);
    if (cached) {
      return cached;
    }
  } else {
    invalidateMobileV2CapabilitiesCache(accessToken);
  }

  const response = await fetchComObservabilidade(
    "mesa_v2_capabilities_get",
    buildApiUrl("/app/api/mobile/v2/capabilities"),
    {
      method: "GET",
      headers: construirHeaders(accessToken),
    },
  );

  const payload = await lerJsonSeguro<unknown | { detail?: string }>(response);
  if (!response.ok || !payload) {
    throw erroCapabilities(
      response.status === 404
        ? "remote_gate_http_404"
        : "remote_gate_http_error",
      extrairMensagemErro(
        payload,
        "Nao foi possivel resolver o gate remoto do mobile V2.",
      ),
    );
  }

  const parsed = parseMobileV2Capabilities(payload);
  setCachedCapabilities(accessToken, parsed);
  return parsed;
}

export async function resolveMobileV2RouteDecision(
  accessToken: string,
  target: MobileV2ReadTarget,
  options?: { forceRefresh?: boolean },
): Promise<MobileV2RouteDecision> {
  if (!androidV2ReadContractsEnabled()) {
    return {
      localFlagEnabled: false,
      shouldUseV2: false,
      reason: "local_flag_off",
      source: "local_flag",
      fallbackReason: null,
    };
  }

  try {
    const capabilities = await carregarMobileV2Capabilities(
      accessToken,
      options,
    );
    const routeEnabled =
      target === "feed"
        ? capabilities.mobile_v2_feed_enabled
        : capabilities.mobile_v2_thread_enabled;
    const routeState =
      target === "feed"
        ? capabilities.feed_rollout_state
        : capabilities.thread_rollout_state;
    const routeReason =
      target === "feed" ? capabilities.feed_reason : capabilities.thread_reason;
    const routeSource =
      target === "feed" ? capabilities.feed_source : capabilities.thread_source;
    const fallbackReason = inferirFallbackRemoto({
      rolloutState: capabilities.rollout_state,
      rolloutReason: capabilities.reason,
      routeState,
      routeReason,
    });

    if (!capabilities.mobile_v2_reads_enabled) {
      return {
        localFlagEnabled: true,
        shouldUseV2: false,
        reason: capabilities.reason,
        source: capabilities.source,
        fallbackReason,
        capabilities,
      };
    }

    if (!routeEnabled || !rolloutStateAllowsReads(routeState)) {
      return {
        localFlagEnabled: true,
        shouldUseV2: false,
        reason: rolloutStateAllowsReads(routeState) ? routeReason : routeState,
        source: routeSource,
        fallbackReason,
        capabilities,
      };
    }

    return {
      localFlagEnabled: true,
      shouldUseV2: true,
      reason: "enabled",
      source: routeSource,
      fallbackReason: null,
      capabilities,
    };
  } catch (error) {
    return {
      localFlagEnabled: true,
      shouldUseV2: false,
      reason: "remote_gate_error",
      source: classificarErroCapabilities(error),
      fallbackReason: "capabilities_fetch_error",
    };
  }
}

export function buildMobileV2AttemptHeaders(
  metadata?: MobileV2AttemptMetadata,
): HeadersInit | undefined {
  if (!metadata) {
    return undefined;
  }
  const headers: Record<string, string> = {
    [MOBILE_V2_ATTEMPTED_HEADER]: "1",
    [MOBILE_V2_ROUTE_HEADER]: metadata.route,
  };
  const capabilitiesVersion = sanitizeHeaderToken(metadata.capabilitiesVersion);
  if (capabilitiesVersion) {
    headers[MOBILE_V2_CAPABILITIES_VERSION_HEADER] = capabilitiesVersion;
  }
  const rolloutBucket = sanitizeHeaderBucket(metadata.rolloutBucket);
  if (rolloutBucket) {
    headers[MOBILE_V2_ROLLOUT_BUCKET_HEADER] = rolloutBucket;
  }
  const usageMode = sanitizeHeaderToken(metadata.usageMode);
  if (usageMode) {
    headers[MOBILE_V2_USAGE_MODE_HEADER] = usageMode;
  }
  const validationSessionId = sanitizeHeaderToken(metadata.validationSessionId);
  if (validationSessionId) {
    headers[MOBILE_V2_VALIDATION_SESSION_HEADER] = validationSessionId;
  }
  const operatorRunId = sanitizeHeaderToken(metadata.operatorRunId);
  if (operatorRunId) {
    headers[MOBILE_V2_OPERATOR_RUN_HEADER] = operatorRunId;
  }
  return headers;
}

export function buildMobileV2FallbackHeaders(
  metadata?: MobileV2LegacyFallbackMetadata,
): HeadersInit | undefined {
  if (!metadata) {
    return undefined;
  }

  const headers = new Headers(
    buildMobileV2AttemptHeaders({
      route: metadata.route,
      capabilitiesVersion: metadata.capabilitiesVersion,
      rolloutBucket: metadata.rolloutBucket,
      usageMode: metadata.usageMode,
      validationSessionId: metadata.validationSessionId,
      operatorRunId: metadata.operatorRunId,
    }),
  );
  headers.set(MOBILE_V2_FALLBACK_REASON_HEADER, metadata.reason);
  const gateSource = sanitizeHeaderToken(metadata.source);
  if (gateSource) {
    headers.set(MOBILE_V2_GATE_SOURCE_HEADER, gateSource);
  }
  return Object.fromEntries(headers.entries());
}

export function classifyMobileV2ReadError(
  error: unknown,
): MobileV2FallbackReason {
  if (error instanceof MobileV2ContractError) {
    if (error.code === "http_404") {
      return "http_404";
    }
    if (error.code === "http_error") {
      return "http_error";
    }
    if (
      error.code === "visibility_scope_violation" ||
      error.code === "actor_role_violation"
    ) {
      return "visibility_violation";
    }
    if (error.code === "adapter_error") {
      return "adapter_error";
    }
    if (error.code.startsWith("invalid_")) {
      return "parse_error";
    }
    return "unknown";
  }
  if (error instanceof Error) {
    return "http_error";
  }
  return "unknown";
}

export function __resetMobileV2CapabilitiesCacheForTests(): void {
  capabilitiesCache.clear();
}
