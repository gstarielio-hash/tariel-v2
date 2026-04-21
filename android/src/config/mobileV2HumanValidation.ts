import {
  buildApiUrl,
  construirHeaders,
  extrairMensagemErro,
  fetchComObservabilidade,
  lerJsonSeguro,
} from "./apiCore";
import {
  buildMobileV2AttemptHeaders,
  type MobileV2ReadTarget,
  type MobileV2UsageMode,
} from "./mobileV2Rollout";

const MOBILE_V2_HUMAN_VALIDATION_META_KEY =
  "__tarielMobileV2HumanValidationMeta";
const deliveredHumanValidationAcks = new Set<string>();
const inFlightHumanValidationAcks = new Set<string>();

export type MobileV2ReadDeliveryMode = "v2" | "legacy";

export interface MobileV2ReadRenderMetadata {
  route: MobileV2ReadTarget;
  deliveryMode: MobileV2ReadDeliveryMode;
  capabilitiesVersion?: string | null;
  rolloutBucket?: number | null;
  usageMode?: MobileV2UsageMode | null;
  validationSessionId?: string | null;
  operatorRunId?: string | null;
  suggestedTargetIds?: number[];
}

export interface MobileV2HumanValidationAckPayload {
  session_id: string;
  surface: MobileV2ReadTarget;
  target_id: number;
  checkpoint_kind: "rendered" | "opened" | "viewed";
  delivery_mode: "v2";
  operator_run_id: string;
}

export function attachMobileV2ReadRenderMetadata<T extends object>(
  payload: T,
  metadata: MobileV2ReadRenderMetadata,
): T {
  Object.defineProperty(payload, MOBILE_V2_HUMAN_VALIDATION_META_KEY, {
    configurable: true,
    enumerable: false,
    value: { ...metadata },
    writable: true,
  });
  return payload;
}

export function extractMobileV2ReadRenderMetadata(
  payload: unknown,
): MobileV2ReadRenderMetadata | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const rawValue = Reflect.get(payload, MOBILE_V2_HUMAN_VALIDATION_META_KEY);
  if (!rawValue || typeof rawValue !== "object" || Array.isArray(rawValue)) {
    return null;
  }

  const route =
    rawValue.route === "feed" || rawValue.route === "thread"
      ? rawValue.route
      : null;
  const deliveryMode =
    rawValue.deliveryMode === "v2" || rawValue.deliveryMode === "legacy"
      ? rawValue.deliveryMode
      : null;
  if (!route || !deliveryMode) {
    return null;
  }

  return {
    route,
    deliveryMode,
    capabilitiesVersion:
      typeof rawValue.capabilitiesVersion === "string"
        ? rawValue.capabilitiesVersion
        : null,
    rolloutBucket:
      typeof rawValue.rolloutBucket === "number"
        ? rawValue.rolloutBucket
        : null,
    usageMode:
      rawValue.usageMode === "organic_validation" ? rawValue.usageMode : null,
    validationSessionId:
      typeof rawValue.validationSessionId === "string"
        ? rawValue.validationSessionId
        : null,
    operatorRunId:
      typeof rawValue.operatorRunId === "string"
        ? rawValue.operatorRunId
        : null,
    suggestedTargetIds: Array.isArray(rawValue.suggestedTargetIds)
      ? rawValue.suggestedTargetIds
          .map((item: unknown) =>
            typeof item === "number" && Number.isFinite(item) ? item : null,
          )
          .filter(
            (item: number | null): item is number => item !== null && item > 0,
          )
      : [],
  };
}

function buildHumanValidationAckKey(
  metadata: MobileV2ReadRenderMetadata,
  checkpointKind: string,
  targetId: number,
): string {
  return [
    metadata.validationSessionId || "no-session",
    metadata.route,
    checkpointKind,
    String(targetId),
  ].join(":");
}

export function normalizeHumanAckTargetIds(targetIds: number[]): number[] {
  return Array.from(
    new Set(
      (targetIds || [])
        .map((item) => Number(item))
        .filter((item) => Number.isFinite(item) && item > 0),
    ),
  );
}

export function shouldSendHumanAck(params: {
  surface: MobileV2ReadTarget;
  readMetadata: MobileV2ReadRenderMetadata | null;
  accessToken: string | null;
  targetIds: number[];
}): boolean {
  const metadata = params.readMetadata;
  const accessToken = String(params.accessToken || "").trim();
  const targetIds = normalizeHumanAckTargetIds(params.targetIds);

  return Boolean(
    accessToken &&
    metadata &&
    metadata.route === params.surface &&
    metadata.deliveryMode === "v2" &&
    metadata.usageMode === "organic_validation" &&
    metadata.validationSessionId &&
    targetIds.length,
  );
}

export function buildHumanAckPayload(params: {
  surface: MobileV2ReadTarget;
  metadata: MobileV2ReadRenderMetadata;
  targetId: number;
  checkpointKind: "rendered" | "opened" | "viewed";
}): MobileV2HumanValidationAckPayload {
  return {
    session_id: String(params.metadata.validationSessionId || "").trim(),
    surface: params.surface,
    target_id: params.targetId,
    checkpoint_kind: params.checkpointKind,
    delivery_mode: "v2",
    operator_run_id: String(params.metadata.operatorRunId || "").trim(),
  };
}

export async function acknowledgeMobileV2HumanValidationRender(params: {
  accessToken: string | null;
  surface: MobileV2ReadTarget;
  readMetadata: MobileV2ReadRenderMetadata | null;
  targetIds: number[];
  checkpointKind?: "rendered" | "opened" | "viewed";
}): Promise<boolean> {
  const checkpointKind = params.checkpointKind ?? "rendered";
  const metadata = params.readMetadata;
  const accessToken = String(params.accessToken || "").trim();
  const targetIds = normalizeHumanAckTargetIds(params.targetIds);

  if (
    !shouldSendHumanAck({
      surface: params.surface,
      readMetadata: metadata,
      accessToken,
      targetIds,
    }) ||
    !metadata
  ) {
    return false;
  }

  let acknowledged = false;

  for (const targetId of targetIds) {
    const ackKey = buildHumanValidationAckKey(
      metadata,
      checkpointKind,
      targetId,
    );
    if (
      deliveredHumanValidationAcks.has(ackKey) ||
      inFlightHumanValidationAcks.has(ackKey)
    ) {
      continue;
    }

    const attemptHeaders = buildMobileV2AttemptHeaders({
      route: params.surface,
      capabilitiesVersion: metadata.capabilitiesVersion ?? null,
      rolloutBucket: metadata.rolloutBucket ?? null,
      usageMode: metadata.usageMode ?? null,
      validationSessionId: metadata.validationSessionId ?? null,
      operatorRunId: metadata.operatorRunId ?? null,
    });
    const headers = new Headers(construirHeaders(accessToken, attemptHeaders));
    headers.set("Content-Type", "application/json");
    inFlightHumanValidationAcks.add(ackKey);

    try {
      const ackPayload = buildHumanAckPayload({
        surface: params.surface,
        metadata,
        targetId,
        checkpointKind,
      });
      const response = await fetchComObservabilidade(
        "mesa_v2_human_validation_ack",
        buildApiUrl("/app/api/mobile/v2/organic-validation/ack"),
        {
          method: "POST",
          headers,
          body: JSON.stringify(ackPayload),
        },
      );
      const payload = await lerJsonSeguro<{ detail?: string }>(response);
      if (!response.ok) {
        throw new Error(
          extrairMensagemErro(
            payload,
            "Nao foi possivel confirmar a validacao humana do mobile V2.",
          ),
        );
      }
      deliveredHumanValidationAcks.add(ackKey);
      acknowledged = true;
    } catch {
      // A confirmacao humana e auxiliar; falhas nao podem afetar a UX.
    } finally {
      inFlightHumanValidationAcks.delete(ackKey);
    }
  }

  return acknowledged;
}

export function __resetMobileV2HumanValidationRuntimeForTests(): void {
  deliveredHumanValidationAcks.clear();
  inFlightHumanValidationAcks.clear();
}
