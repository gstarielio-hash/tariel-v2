import type { ApiHealthStatus } from "../../types/mobile";
import type { OfflinePendingMessage } from "../chat/types";

export type AndroidOfflineSyncBlockerV1 =
  | "none"
  | "empty_queue"
  | "api_offline"
  | "api_checking"
  | "device_sync_disabled"
  | "sync_in_progress"
  | "backoff_only";

export type AndroidOfflineSyncItemKindV1 = "text" | "image" | "document";
export type AndroidOfflineSyncRetryStateV1 =
  | "pending"
  | "retry_ready"
  | "failed"
  | "backoff_wait";

export interface AndroidOfflineSyncQueueTotalsV1 {
  total_items: number;
  ready_items: number;
  failed_items: number;
  backoff_items: number;
  chat_items: number;
  mesa_items: number;
  attachment_items: number;
}

export interface AndroidOfflineSyncCapabilityV1 {
  status_api: ApiHealthStatus;
  sync_enabled: boolean;
  wifi_only_sync: boolean;
  blocker: AndroidOfflineSyncBlockerV1;
  can_sync_now: boolean;
  auto_sync_armed: boolean;
}

export interface AndroidOfflineSyncActivityV1 {
  syncing_queue: boolean;
  syncing_item_id: string | null;
  retry_ready_exists: boolean;
}

export interface AndroidOfflineSyncQueueItemV1 {
  queue_item_id: string;
  channel: OfflinePendingMessage["channel"];
  legacy_laudo_id: number | null;
  item_kind: AndroidOfflineSyncItemKindV1;
  ready_for_retry: boolean;
  retry_state: AndroidOfflineSyncRetryStateV1;
  attempt_count: number;
  created_at: string;
  last_attempt_at: string | null;
  next_retry_at: string | null;
  last_error: string | null;
  client_message_id: string | null;
  reference_message_id: number | null;
  syncing_now: boolean;
}

export interface AndroidOfflineSyncViewV1 {
  contract_name: "android_offline_sync_view";
  contract_version: "v1";
  source_channel: "android";
  projection_payload: {
    queue_totals: AndroidOfflineSyncQueueTotalsV1;
    sync_capability: AndroidOfflineSyncCapabilityV1;
    sync_activity: AndroidOfflineSyncActivityV1;
    items: AndroidOfflineSyncQueueItemV1[];
  };
}

export interface OfflinePendingQueueSummaryV1 {
  ordered_items: OfflinePendingMessage[];
  queue_totals: AndroidOfflineSyncQueueTotalsV1;
  retry_ready_exists: boolean;
}

interface BuildOfflineQueueObservabilityParams {
  offlineQueue: readonly OfflinePendingMessage[];
  statusApi: ApiHealthStatus;
  isItemReadyForRetry: (
    item: OfflinePendingMessage,
    reference?: number,
  ) => boolean;
  getPriority?: (item: OfflinePendingMessage) => number;
  syncEnabled?: boolean;
  wifiOnlySync?: boolean;
  syncingQueue?: boolean;
  syncingItemId?: string;
  referenceTimeMs?: number;
}

function resolveItemKind(
  item: OfflinePendingMessage,
): AndroidOfflineSyncItemKindV1 {
  if (item.attachment?.kind === "image") {
    return "image";
  }
  if (item.attachment?.kind === "document") {
    return "document";
  }
  return "text";
}

function resolveRetryState(
  item: OfflinePendingMessage,
  readyForRetry: boolean,
): AndroidOfflineSyncRetryStateV1 {
  if (item.lastError) {
    return "failed";
  }
  if (readyForRetry) {
    return item.lastAttemptAt ? "retry_ready" : "pending";
  }
  return "backoff_wait";
}

function defaultPriority(
  item: OfflinePendingMessage,
  readyForRetry: boolean,
): number {
  if (item.lastError) {
    return 0;
  }
  if (readyForRetry) {
    return 1;
  }
  return 2;
}

export function summarizeOfflinePendingQueueV1({
  offlineQueue,
  isItemReadyForRetry,
  getPriority,
  referenceTimeMs = Date.now(),
}: Pick<
  BuildOfflineQueueObservabilityParams,
  "offlineQueue" | "isItemReadyForRetry" | "getPriority" | "referenceTimeMs"
>): OfflinePendingQueueSummaryV1 {
  const readiness = new Map<string, boolean>();
  for (const item of offlineQueue) {
    readiness.set(item.id, isItemReadyForRetry(item, referenceTimeMs));
  }

  const ordered_items = [...offlineQueue].sort((a, b) => {
    const readyA = readiness.get(a.id) ?? false;
    const readyB = readiness.get(b.id) ?? false;
    const priorityA = getPriority ? getPriority(a) : defaultPriority(a, readyA);
    const priorityB = getPriority ? getPriority(b) : defaultPriority(b, readyB);
    if (priorityA !== priorityB) {
      return priorityA - priorityB;
    }
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });

  const total_items = ordered_items.length;
  const ready_items = ordered_items.filter(
    (item) => readiness.get(item.id) ?? false,
  ).length;
  const failed_items = ordered_items.filter((item) =>
    Boolean(item.lastError),
  ).length;
  const backoff_items = ordered_items.filter((item) => {
    const readyForRetry = readiness.get(item.id) ?? false;
    return !readyForRetry && !item.lastError;
  }).length;
  const chat_items = ordered_items.filter(
    (item) => item.channel === "chat",
  ).length;
  const mesa_items = ordered_items.filter(
    (item) => item.channel === "mesa",
  ).length;
  const attachment_items = ordered_items.filter((item) =>
    Boolean(item.attachment),
  ).length;

  return {
    ordered_items,
    queue_totals: {
      total_items,
      ready_items,
      failed_items,
      backoff_items,
      chat_items,
      mesa_items,
      attachment_items,
    },
    retry_ready_exists: ready_items > 0,
  };
}

export function buildAndroidOfflineSyncViewV1({
  offlineQueue,
  statusApi,
  isItemReadyForRetry,
  getPriority,
  syncEnabled = true,
  wifiOnlySync = false,
  syncingQueue = false,
  syncingItemId = "",
  referenceTimeMs = Date.now(),
}: BuildOfflineQueueObservabilityParams): AndroidOfflineSyncViewV1 {
  const summary = summarizeOfflinePendingQueueV1({
    offlineQueue,
    isItemReadyForRetry,
    getPriority,
    referenceTimeMs,
  });
  const syncingItemIdValue = syncingItemId.trim() || null;
  const can_sync_now =
    statusApi === "online" &&
    syncEnabled &&
    summary.retry_ready_exists &&
    !syncingQueue &&
    !syncingItemIdValue;
  const auto_sync_armed =
    statusApi === "online" &&
    syncEnabled &&
    summary.retry_ready_exists &&
    !syncingQueue;

  let blocker: AndroidOfflineSyncBlockerV1 = "none";
  if (!summary.queue_totals.total_items) {
    blocker = "empty_queue";
  } else if (syncingQueue || syncingItemIdValue) {
    blocker = "sync_in_progress";
  } else if (!syncEnabled) {
    blocker = "device_sync_disabled";
  } else if (statusApi === "offline") {
    blocker = "api_offline";
  } else if (statusApi === "checking") {
    blocker = "api_checking";
  } else if (!summary.retry_ready_exists) {
    blocker = "backoff_only";
  }

  return {
    contract_name: "android_offline_sync_view",
    contract_version: "v1",
    source_channel: "android",
    projection_payload: {
      queue_totals: summary.queue_totals,
      sync_capability: {
        status_api: statusApi,
        sync_enabled: syncEnabled,
        wifi_only_sync: wifiOnlySync,
        blocker,
        can_sync_now,
        auto_sync_armed,
      },
      sync_activity: {
        syncing_queue: syncingQueue,
        syncing_item_id: syncingItemIdValue,
        retry_ready_exists: summary.retry_ready_exists,
      },
      items: summary.ordered_items.map((item) => {
        const readyForRetry = isItemReadyForRetry(item, referenceTimeMs);
        return {
          queue_item_id: item.id,
          channel: item.channel,
          legacy_laudo_id: item.laudoId,
          item_kind: resolveItemKind(item),
          ready_for_retry: readyForRetry,
          retry_state: resolveRetryState(item, readyForRetry),
          attempt_count: item.attempts,
          created_at: item.createdAt,
          last_attempt_at: item.lastAttemptAt || null,
          next_retry_at: item.nextRetryAt || null,
          last_error: item.lastError || null,
          client_message_id: item.clientMessageId || null,
          reference_message_id: item.referenceMessageId,
          syncing_now: item.id === syncingItemIdValue,
        };
      }),
    },
  };
}
