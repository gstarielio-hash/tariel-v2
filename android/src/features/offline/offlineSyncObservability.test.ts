import type { OfflinePendingMessage } from "../chat/types";
import {
  buildAndroidOfflineSyncViewV1,
  summarizeOfflinePendingQueueV1,
} from "./offlineSyncObservability";

function criarPendencia(
  overrides: Partial<OfflinePendingMessage> = {},
): OfflinePendingMessage {
  return {
    id: "offline-1",
    channel: "chat",
    operation: "message",
    laudoId: 21,
    text: "Mensagem pendente",
    createdAt: "2026-03-20T10:00:00.000Z",
    title: "Laudo 21",
    attachment: null,
    referenceMessageId: null,
    clientMessageId: null,
    qualityGateDecision: null,
    attempts: 0,
    lastAttemptAt: "",
    lastError: "",
    nextRetryAt: "",
    aiMode: "detalhado",
    aiSummary: "Detalhado",
    aiMessagePrefix: "",
    ...overrides,
  };
}

describe("offlineSyncObservability", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("resume a fila com ordenacao estavel e contagens observaveis", () => {
    jest
      .spyOn(Date, "now")
      .mockReturnValue(new Date("2026-03-20T12:00:00.000Z").getTime());

    const summary = summarizeOfflinePendingQueueV1({
      offlineQueue: [
        criarPendencia({
          id: "mesa-falha",
          channel: "mesa",
          createdAt: "2026-03-19T10:00:00.000Z",
          lastError: "timeout",
          nextRetryAt: "2026-03-20T12:05:00.000Z",
        }),
        criarPendencia({
          id: "chat-pronta",
          channel: "chat",
          createdAt: "2026-03-20T11:00:00.000Z",
          attachment: {
            kind: "image",
            label: "Foto",
            resumo: "Imagem",
            dadosImagem: "base64",
            previewUri: "file:///preview.png",
            fileUri: "file:///imagem.png",
            mimeType: "image/png",
          },
        }),
        criarPendencia({
          id: "chat-backoff",
          channel: "chat",
          createdAt: "2026-03-20T09:00:00.000Z",
          nextRetryAt: "2026-03-20T12:05:00.000Z",
        }),
      ],
      isItemReadyForRetry: (item, referencia = Date.now()) => {
        if (!item.nextRetryAt) {
          return true;
        }
        return new Date(item.nextRetryAt).getTime() <= referencia;
      },
      getPriority: (item) => {
        if (item.lastError) {
          return 0;
        }
        if (!item.nextRetryAt) {
          return 1;
        }
        return 2;
      },
    });

    expect(summary.ordered_items.map((item) => item.id)).toEqual([
      "mesa-falha",
      "chat-pronta",
      "chat-backoff",
    ]);
    expect(summary.queue_totals).toEqual({
      total_items: 3,
      ready_items: 1,
      failed_items: 1,
      backoff_items: 1,
      chat_items: 2,
      mesa_items: 1,
      attachment_items: 1,
    });
    expect(summary.retry_ready_exists).toBe(true);
  });

  it("materializa o contrato com blocker e atividade de sync", () => {
    jest
      .spyOn(Date, "now")
      .mockReturnValue(new Date("2026-03-20T12:00:00.000Z").getTime());

    const view = buildAndroidOfflineSyncViewV1({
      offlineQueue: [
        criarPendencia({
          id: "chat-backoff",
          nextRetryAt: "2026-03-20T12:05:00.000Z",
        }),
        criarPendencia({
          id: "mesa-falha",
          channel: "mesa",
          lastError: "sem internet",
          nextRetryAt: "2026-03-20T12:05:00.000Z",
        }),
      ],
      statusApi: "online",
      syncEnabled: true,
      wifiOnlySync: true,
      syncingQueue: false,
      syncingItemId: "mesa-falha",
      isItemReadyForRetry: (item, referencia = Date.now()) => {
        if (!item.nextRetryAt) {
          return true;
        }
        return new Date(item.nextRetryAt).getTime() <= referencia;
      },
    });

    expect(view.contract_name).toBe("android_offline_sync_view");
    expect(view.projection_payload.queue_totals.total_items).toBe(2);
    expect(view.projection_payload.sync_capability.blocker).toBe(
      "sync_in_progress",
    );
    expect(view.projection_payload.sync_capability.can_sync_now).toBe(false);
    expect(view.projection_payload.sync_capability.wifi_only_sync).toBe(true);
    expect(view.projection_payload.sync_activity.syncing_item_id).toBe(
      "mesa-falha",
    );
    expect(view.projection_payload.items[0]).toEqual(
      expect.objectContaining({
        queue_item_id: "mesa-falha",
        retry_state: "failed",
        ready_for_retry: false,
        syncing_now: true,
      }),
    );
  });
});
