import { renderHook } from "@testing-library/react-native";

const mockHandleAbrirPermissaoNotificacoes = jest.fn();
const mockHandleDesbloquearAplicativo = jest.fn();

jest.mock("./useAppLockController", () => ({
  useAppLockController: jest.fn(() => ({
    actions: {
      handleAbrirPermissaoNotificacoes: mockHandleAbrirPermissaoNotificacoes,
      handleDesbloquearAplicativo: mockHandleDesbloquearAplicativo,
      handleGerenciarPermissao: jest.fn(),
    },
  })),
}));

import { useAppLockController } from "./useAppLockController";
import { useInspectorRootAppLockController } from "./useInspectorRootAppLockController";

function criarInput() {
  return {
    sessionState: {
      appLocked: false,
      lockTimeout: "imediatamente" as const,
      reauthenticationExpiresAt: "",
      requireAuthOnOpen: true,
      session: null,
      settingsHydrated: true,
    },
    permissionState: {
      biometricsPermissionGranted: true,
      cameraPermissionGranted: true,
      deviceBiometricsEnabled: true,
      filesPermissionGranted: true,
      microphonePermissionGranted: true,
      notificationsPermissionGranted: true,
      pushEnabled: true,
      uploadFilesEnabled: true,
      voiceInputEnabled: true,
    },
    setterState: {
      setAppLocked: jest.fn(),
      setBiometricsPermissionGranted: jest.fn(),
      setCameraPermissionGranted: jest.fn(),
      setDeviceBiometricsEnabled: jest.fn(),
      setFilesPermissionGranted: jest.fn(),
      setMicrophonePermissionGranted: jest.fn(),
      setNotificationsPermissionGranted: jest.fn(),
      setPushEnabled: jest.fn(),
      setUploadFilesEnabled: jest.fn(),
      setVoiceInputEnabled: jest.fn(),
    },
    actionState: {
      isReauthenticationStillValid: jest.fn().mockReturnValue(true),
      openReauthFlow: jest.fn(),
      registerSecurityEvent: jest.fn(),
      resolveLockTimeoutMs: jest.fn().mockReturnValue(0),
    },
  };
}

describe("useInspectorRootAppLockController", () => {
  it("encapsula a composição do app lock sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() =>
      useInspectorRootAppLockController(input),
    );
    const mockedHook = jest.mocked(useAppLockController);

    result.current.actions.handleAbrirPermissaoNotificacoes();
    result.current.actions.handleDesbloquearAplicativo();

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        appLocked: input.sessionState.appLocked,
        pushEnabled: input.permissionState.pushEnabled,
        setAppLocked: input.setterState.setAppLocked,
      }),
    );
    expect(mockHandleAbrirPermissaoNotificacoes).toHaveBeenCalledTimes(1);
    expect(mockHandleDesbloquearAplicativo).toHaveBeenCalledTimes(1);
  });
});
