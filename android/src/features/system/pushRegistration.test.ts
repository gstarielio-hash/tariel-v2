jest.mock("expo-constants", () => ({
  __esModule: true,
  default: {
    easConfig: {
      projectId: "project-123",
    },
    expoConfig: {
      extra: {
        eas: {
          projectId: "project-123",
        },
      },
    },
  },
}));

jest.mock("expo-notifications", () => ({
  getExpoPushTokenAsync: jest.fn(),
}));

jest.mock("../session/sessionStorage", () => ({
  readSecureItem: jest.fn(),
  writeSecureItem: jest.fn(),
}));

import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

import { readSecureItem, writeSecureItem } from "../session/sessionStorage";
import {
  buildPushRegistrationPayload,
  mapPushTokenStatusToSyncStatus,
  tokenStatusIsOperational,
} from "./pushRegistration";

const originalPlatformOs = Platform.OS;
const originalPlatformConstants = Platform.constants;

function setPlatformState(params: {
  os: "android" | "ios";
  constants?: Record<string, unknown>;
}) {
  Object.defineProperty(Platform, "OS", {
    configurable: true,
    value: params.os,
  });
  Object.defineProperty(Platform, "constants", {
    configurable: true,
    value: params.constants || {},
  });
}

describe("pushRegistration", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setPlatformState({
      os: "android",
      constants: {
        Brand: "Google",
        Manufacturer: "Google",
        Model: "Pixel 8",
        Fingerprint: "google/pixel/device:14/UP1A/dev-keys",
      },
    });
    (readSecureItem as jest.Mock).mockResolvedValue(null);
    (writeSecureItem as jest.Mock).mockResolvedValue(undefined);
    (Notifications.getExpoPushTokenAsync as jest.Mock).mockResolvedValue({
      data: "ExponentPushToken[test-123]",
    });
    (
      Constants as {
        easConfig?: { projectId?: string };
      }
    ).easConfig = { projectId: "project-123" };
    (
      Constants as unknown as {
        expoConfig?: {
          name?: string;
          slug?: string;
          extra?: { eas?: { projectId?: string } };
        };
      }
    ).expoConfig = {
      name: "Tariel Inspetor",
      slug: "tariel-inspetor",
      extra: {
        eas: {
          projectId: "project-123",
        },
      },
    };
  });

  afterAll(() => {
    Object.defineProperty(Platform, "OS", {
      configurable: true,
      value: originalPlatformOs,
    });
    Object.defineProperty(Platform, "constants", {
      configurable: true,
      value: originalPlatformConstants,
    });
  });

  it("materializa payload registrado quando consegue obter token Expo", async () => {
    const payload = await buildPushRegistrationPayload({
      appVersion: "1.2.3",
      buildNumber: "321",
      notificationsPermissionGranted: true,
      pushEnabled: true,
    });

    expect(payload.device_id).toContain("android-");
    expect(writeSecureItem).toHaveBeenCalledTimes(1);
    expect(Notifications.getExpoPushTokenAsync).toHaveBeenCalledWith({
      projectId: "project-123",
    });
    expect(payload).toMatchObject({
      plataforma: "android",
      provider: "expo",
      token_status: "registered",
      push_token: "ExponentPushToken[test-123]",
      permissao_notificacoes: true,
      push_habilitado: true,
      app_version: "1.2.3",
      build_number: "321",
      is_emulator: false,
      ultimo_erro: "",
    });
    expect(payload.device_label).toBe("Google Pixel 8");
  });

  it("preserva device_id salvo e nao consulta token quando push está desligado", async () => {
    (readSecureItem as jest.Mock).mockResolvedValue("device-stable-123");

    const payload = await buildPushRegistrationPayload({
      appVersion: "1.2.3",
      buildNumber: "321",
      notificationsPermissionGranted: true,
      pushEnabled: false,
    });

    expect(payload.device_id).toBe("device-stable-123");
    expect(writeSecureItem).not.toHaveBeenCalled();
    expect(Notifications.getExpoPushTokenAsync).not.toHaveBeenCalled();
    expect(payload.token_status).toBe("disabled");
    expect(payload.push_token).toBe("");
  });

  it("marca unsupported em emulador Android sem tentar materializar token", async () => {
    setPlatformState({
      os: "android",
      constants: {
        Brand: "generic",
        Manufacturer: "Genymotion",
        Model: "sdk_gphone64_x86_64",
        Fingerprint: "generic/sdk/generic:14/UP1A/test-keys",
      },
    });

    const payload = await buildPushRegistrationPayload({
      appVersion: "1.2.3",
      buildNumber: "321",
      notificationsPermissionGranted: true,
      pushEnabled: true,
    });

    expect(Notifications.getExpoPushTokenAsync).not.toHaveBeenCalled();
    expect(payload.token_status).toBe("unsupported");
    expect(payload.is_emulator).toBe(true);
    expect(payload.ultimo_erro).toBe("push_native_unsupported_on_emulator");
  });

  it("mapeia estados operacionais e degradados do token", () => {
    expect(mapPushTokenStatusToSyncStatus("registered")).toBe("registered");
    expect(mapPushTokenStatusToSyncStatus("disabled")).toBe("disabled");
    expect(mapPushTokenStatusToSyncStatus("permission_denied")).toBe(
      "permission_denied",
    );
    expect(mapPushTokenStatusToSyncStatus("missing_project_id")).toBe(
      "unsupported",
    );
    expect(mapPushTokenStatusToSyncStatus("unavailable")).toBe(
      "waiting_online",
    );
    expect(mapPushTokenStatusToSyncStatus("token_error")).toBe("error");

    expect(tokenStatusIsOperational("registered")).toBe(true);
    expect(tokenStatusIsOperational("disabled")).toBe(true);
    expect(tokenStatusIsOperational("permission_denied")).toBe(true);
    expect(tokenStatusIsOperational("unsupported")).toBe(true);
    expect(tokenStatusIsOperational("missing_project_id")).toBe(true);
    expect(tokenStatusIsOperational("token_error")).toBe(false);
  });
});
