jest.mock("../../config/api", () => ({
  registrarDispositivoPushMobile: jest.fn(),
}));

jest.mock("../../config/observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

jest.mock("./pushRegistration", () => ({
  buildPushRegistrationPayload: jest.fn(),
  mapPushTokenStatusToSyncStatus: jest.fn(),
  tokenStatusIsOperational: jest.fn(),
}));

import { act, renderHook, waitFor } from "@testing-library/react-native";

import { registrarDispositivoPushMobile } from "../../config/api";
import { registrarEventoObservabilidade } from "../../config/observability";
import type { MobilePushRegistration } from "../../types/mobile";
import {
  buildPushRegistrationPayload,
  mapPushTokenStatusToSyncStatus,
  tokenStatusIsOperational,
} from "./pushRegistration";
import { usePushRegistrationController } from "./usePushRegistrationController";

function criarRegistroPush(
  overrides: Partial<MobilePushRegistration> = {},
): MobilePushRegistration {
  return {
    id: 7,
    device_id: "device-123",
    plataforma: "android",
    provider: "expo",
    push_token: "ExponentPushToken[test-123]",
    permissao_notificacoes: true,
    push_habilitado: true,
    token_status: "registered",
    canal_build: "preview",
    app_version: "1.2.3",
    build_number: "321",
    device_label: "Google Pixel 8",
    is_emulator: false,
    ultimo_erro: "",
    registered_at: "2026-03-30T12:00:00.000Z",
    last_seen_at: "2026-03-30T12:00:05.000Z",
    ...overrides,
  };
}

function criarParams(
  overrides: Partial<Parameters<typeof usePushRegistrationController>[0]> = {},
): Parameters<typeof usePushRegistrationController>[0] {
  return {
    accessToken: "token-123",
    appVersion: "1.2.3",
    buildNumber: "321",
    notificationsPermissionGranted: true,
    pushEnabled: true,
    statusApi: "online",
    ...overrides,
  };
}

describe("usePushRegistrationController", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (buildPushRegistrationPayload as jest.Mock).mockResolvedValue({
      device_id: "device-123",
      plataforma: "android",
      provider: "expo",
      push_token: "ExponentPushToken[test-123]",
      permissao_notificacoes: true,
      push_habilitado: true,
      token_status: "registered",
      canal_build: "preview",
      app_version: "1.2.3",
      build_number: "321",
      device_label: "Google Pixel 8",
      is_emulator: false,
      ultimo_erro: "",
    });
    (registrarDispositivoPushMobile as jest.Mock).mockResolvedValue({
      ok: true,
      registration: criarRegistroPush(),
    });
    (mapPushTokenStatusToSyncStatus as jest.Mock).mockReturnValue("registered");
    (tokenStatusIsOperational as jest.Mock).mockReturnValue(true);
  });

  it("reseta o estado quando não existe access token", async () => {
    const { result } = renderHook(() =>
      usePushRegistrationController(criarParams({ accessToken: null })),
    );

    await waitFor(() => {
      expect(result.current.state.syncStatus).toBe("idle");
    });
    expect(buildPushRegistrationPayload).not.toHaveBeenCalled();
    expect(registrarDispositivoPushMobile).not.toHaveBeenCalled();
    expect(result.current.state.registration).toBeNull();
    expect(result.current.state.lastError).toBe("");
  });

  it("aguarda online antes de sincronizar quando a API está offline", async () => {
    const { result } = renderHook(() =>
      usePushRegistrationController(criarParams({ statusApi: "offline" })),
    );

    await waitFor(() => {
      expect(result.current.state.syncStatus).toBe("waiting_online");
    });
    expect(buildPushRegistrationPayload).not.toHaveBeenCalled();
    expect(registrarDispositivoPushMobile).not.toHaveBeenCalled();
  });

  it("sincroniza o registro push e publica observabilidade quando o backend responde", async () => {
    const { result } = renderHook(() =>
      usePushRegistrationController(criarParams()),
    );

    await waitFor(() => {
      expect(result.current.state.syncStatus).toBe("registered");
    });
    expect(buildPushRegistrationPayload).toHaveBeenCalledWith({
      appVersion: "1.2.3",
      buildNumber: "321",
      notificationsPermissionGranted: true,
      pushEnabled: true,
    });
    expect(registrarDispositivoPushMobile).toHaveBeenCalledWith("token-123", {
      device_id: "device-123",
      plataforma: "android",
      provider: "expo",
      push_token: "ExponentPushToken[test-123]",
      permissao_notificacoes: true,
      push_habilitado: true,
      token_status: "registered",
      canal_build: "preview",
      app_version: "1.2.3",
      build_number: "321",
      device_label: "Google Pixel 8",
      is_emulator: false,
      ultimo_erro: "",
    });
    expect(result.current.state.registration).toEqual(criarRegistroPush());
    expect(result.current.state.lastSyncedAt).toBe("2026-03-30T12:00:05.000Z");
    expect(result.current.state.lastError).toBe("");
    expect(registrarEventoObservabilidade).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "push",
        name: "push_registration_sync",
        ok: true,
        detail: "registered",
      }),
    );
  });

  it("marca erro quando a sincronização falha", async () => {
    (registrarDispositivoPushMobile as jest.Mock).mockRejectedValue(
      new Error("backend indisponivel"),
    );

    const { result } = renderHook(() =>
      usePushRegistrationController(criarParams()),
    );

    await waitFor(() => {
      expect(result.current.state.syncStatus).toBe("error");
    });
    expect(result.current.state.lastError).toBe("backend indisponivel");
    expect(registrarEventoObservabilidade).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "push",
        name: "push_registration_sync",
        ok: false,
        detail: "backend indisponivel",
      }),
    );

    await act(async () => {
      await result.current.actions.syncRegistration();
    });
    expect(registrarDispositivoPushMobile).toHaveBeenCalledTimes(2);
  });
});
