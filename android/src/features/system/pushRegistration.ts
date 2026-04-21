import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

import type { MobilePushRegistrationPayload } from "../../config/pushApi";
import { APP_BUILD_CHANNEL } from "../InspectorMobileApp.constants";
import { readSecureItem, writeSecureItem } from "../session/sessionStorage";

const PUSH_DEVICE_ID_KEY = "tariel_inspetor_push_device_id";

function normalizeText(value: unknown, fallback = ""): string {
  const text = String(value || "").trim();
  return text || fallback;
}

function androidPareceEmulador(): boolean {
  if (Platform.OS !== "android") {
    return false;
  }

  const constants = (Platform.constants || {}) as Record<string, unknown>;
  const fingerprint = String(constants.Fingerprint || "");
  const model = String(constants.Model || "");
  const brand = String(constants.Brand || "");
  const manufacturer = String(constants.Manufacturer || "");
  const product = String(constants.Product || "");
  const hardware = String(constants.Hardware || "");
  const device = String(constants.Device || "");
  const joined = [
    fingerprint,
    model,
    brand,
    manufacturer,
    product,
    hardware,
    device,
  ].join(" ");

  return /generic|sdk|emulator|simulator|goldfish|ranchu/i.test(joined);
}

function resolveDeviceLabel(): string {
  const constants = (Platform.constants || {}) as Record<string, unknown>;
  const model = normalizeText(constants.Model);
  const brand = normalizeText(constants.Brand);
  const manufacturer = normalizeText(constants.Manufacturer);
  return [manufacturer || brand, model].filter(Boolean).join(" ").trim();
}

function resolveExpoProjectId(): string {
  const easProjectId =
    normalizeText(
      (Constants as { easConfig?: { projectId?: string } }).easConfig
        ?.projectId,
    ) ||
    normalizeText(
      (
        Constants.expoConfig?.extra as
          | { eas?: { projectId?: string } }
          | undefined
      )?.eas?.projectId,
    ) ||
    normalizeText(process.env.EXPO_PUBLIC_EAS_PROJECT_ID);
  return easProjectId;
}

async function resolvePushDeviceId(): Promise<string> {
  const existing = normalizeText(await readSecureItem(PUSH_DEVICE_ID_KEY));
  if (existing) {
    return existing;
  }

  const generated = [
    Platform.OS,
    Date.now().toString(36),
    Math.random().toString(36).slice(2, 10),
  ].join("-");
  await writeSecureItem(PUSH_DEVICE_ID_KEY, generated);
  return generated;
}

function describePushTokenError(error: unknown): string {
  if (error instanceof Error) {
    return normalizeText(error.message, "erro_token_push");
  }
  return "erro_token_push";
}

export type PushRegistrationSyncStatus =
  | "idle"
  | "syncing"
  | "registered"
  | "disabled"
  | "permission_denied"
  | "waiting_online"
  | "unsupported"
  | "error";

export interface BuildPushRegistrationPayloadInput {
  appVersion: string;
  buildNumber: string;
  notificationsPermissionGranted: boolean;
  pushEnabled: boolean;
}

export async function buildPushRegistrationPayload({
  appVersion,
  buildNumber,
  notificationsPermissionGranted,
  pushEnabled,
}: BuildPushRegistrationPayloadInput): Promise<MobilePushRegistrationPayload> {
  const plataforma = Platform.OS === "ios" ? "ios" : "android";
  const isEmulator = androidPareceEmulador();
  const device_id = await resolvePushDeviceId();
  const provider = "expo" as const;
  const device_label = resolveDeviceLabel();

  let push_token = "";
  let token_status = "unavailable";
  let ultimo_erro = "";

  if (!pushEnabled) {
    token_status = "disabled";
  } else if (!notificationsPermissionGranted) {
    token_status = "permission_denied";
  } else if (isEmulator) {
    token_status = "unsupported";
    ultimo_erro = "push_native_unsupported_on_emulator";
  } else {
    const projectId = resolveExpoProjectId();
    if (!projectId) {
      token_status = "missing_project_id";
      ultimo_erro = "expo_project_id_missing";
    } else {
      try {
        const tokenResponse = await Notifications.getExpoPushTokenAsync({
          projectId,
        });
        push_token = normalizeText(tokenResponse.data);
        if (push_token) {
          token_status = "registered";
        } else {
          token_status = "token_error";
          ultimo_erro = "expo_push_token_empty";
        }
      } catch (error) {
        token_status = "token_error";
        ultimo_erro = describePushTokenError(error);
      }
    }
  }

  return {
    device_id,
    plataforma,
    provider,
    push_token,
    permissao_notificacoes: notificationsPermissionGranted,
    push_habilitado: pushEnabled,
    token_status,
    canal_build: APP_BUILD_CHANNEL,
    app_version: normalizeText(appVersion),
    build_number: normalizeText(buildNumber),
    device_label,
    is_emulator: isEmulator,
    ultimo_erro,
  };
}

export function mapPushTokenStatusToSyncStatus(
  tokenStatus: string,
): PushRegistrationSyncStatus {
  switch (String(tokenStatus || "").trim()) {
    case "registered":
      return "registered";
    case "disabled":
      return "disabled";
    case "permission_denied":
      return "permission_denied";
    case "unsupported":
    case "missing_project_id":
      return "unsupported";
    case "unavailable":
      return "waiting_online";
    default:
      return "error";
  }
}

export function tokenStatusIsOperational(tokenStatus: string): boolean {
  return [
    "registered",
    "disabled",
    "permission_denied",
    "unsupported",
    "missing_project_id",
  ].includes(String(tokenStatus || "").trim());
}
