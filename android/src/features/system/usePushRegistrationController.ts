import { useEffect, useRef, useState } from "react";

import { registrarDispositivoPushMobile } from "../../config/api";
import { registrarEventoObservabilidade } from "../../config/observability";
import type { MobilePushRegistration } from "../../types/mobile";
import {
  buildPushRegistrationPayload,
  mapPushTokenStatusToSyncStatus,
  tokenStatusIsOperational,
  type PushRegistrationSyncStatus,
} from "./pushRegistration";

interface UsePushRegistrationControllerParams {
  accessToken: string | null;
  appVersion: string;
  buildNumber: string;
  notificationsPermissionGranted: boolean;
  pushEnabled: boolean;
  statusApi: "checking" | "online" | "offline";
}

export function usePushRegistrationController(
  params: UsePushRegistrationControllerParams,
) {
  const paramsRef = useRef(params);
  paramsRef.current = params;

  const [syncStatus, setSyncStatus] =
    useState<PushRegistrationSyncStatus>("idle");
  const [registration, setRegistration] =
    useState<MobilePushRegistration | null>(null);
  const [lastError, setLastError] = useState("");
  const [lastSyncedAt, setLastSyncedAt] = useState("");

  async function syncRegistration() {
    const current = paramsRef.current;
    const accessToken = String(current.accessToken || "").trim();
    if (!accessToken) {
      setSyncStatus("idle");
      setRegistration(null);
      setLastError("");
      setLastSyncedAt("");
      return;
    }

    if (current.statusApi === "offline") {
      setSyncStatus(current.pushEnabled ? "waiting_online" : "disabled");
      return;
    }

    const startedAt = Date.now();
    setSyncStatus("syncing");
    setLastError("");

    try {
      const payload = await buildPushRegistrationPayload({
        appVersion: current.appVersion,
        buildNumber: current.buildNumber,
        notificationsPermissionGranted: current.notificationsPermissionGranted,
        pushEnabled: current.pushEnabled,
      });
      const response = await registrarDispositivoPushMobile(
        accessToken,
        payload,
      );
      const nextRegistration = response.registration;
      const nextStatus = mapPushTokenStatusToSyncStatus(
        nextRegistration.token_status,
      );
      setRegistration(nextRegistration);
      setLastError(nextRegistration.ultimo_erro || "");
      setLastSyncedAt(nextRegistration.last_seen_at || "");
      setSyncStatus(nextStatus);
      void registrarEventoObservabilidade({
        kind: "push",
        name: "push_registration_sync",
        ok: tokenStatusIsOperational(nextRegistration.token_status),
        durationMs: Date.now() - startedAt,
        detail: nextRegistration.token_status,
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "push_registration_sync_failed";
      setLastError(message);
      setSyncStatus("error");
      void registrarEventoObservabilidade({
        kind: "push",
        name: "push_registration_sync",
        ok: false,
        durationMs: Date.now() - startedAt,
        detail: message,
      });
    }
  }

  useEffect(() => {
    if (!params.accessToken) {
      setSyncStatus("idle");
      setRegistration(null);
      setLastError("");
      setLastSyncedAt("");
      return;
    }
    void syncRegistration();
  }, [
    params.accessToken,
    params.appVersion,
    params.buildNumber,
    params.notificationsPermissionGranted,
    params.pushEnabled,
    params.statusApi,
  ]);

  return {
    state: {
      lastError,
      lastSyncedAt,
      registration,
      syncStatus,
    },
    actions: {
      syncRegistration,
    },
  };
}
