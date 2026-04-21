import { useAppLockController } from "./useAppLockController";

type AppLockControllerParams = Parameters<typeof useAppLockController>[0];

interface UseInspectorRootAppLockControllerInput {
  sessionState: Pick<
    AppLockControllerParams,
    | "appLocked"
    | "lockTimeout"
    | "reauthenticationExpiresAt"
    | "requireAuthOnOpen"
    | "session"
    | "settingsHydrated"
  >;
  permissionState: Pick<
    AppLockControllerParams,
    | "biometricsPermissionGranted"
    | "cameraPermissionGranted"
    | "deviceBiometricsEnabled"
    | "filesPermissionGranted"
    | "microphonePermissionGranted"
    | "notificationsPermissionGranted"
    | "pushEnabled"
    | "uploadFilesEnabled"
    | "voiceInputEnabled"
  >;
  setterState: Pick<
    AppLockControllerParams,
    | "setAppLocked"
    | "setBiometricsPermissionGranted"
    | "setCameraPermissionGranted"
    | "setDeviceBiometricsEnabled"
    | "setFilesPermissionGranted"
    | "setMicrophonePermissionGranted"
    | "setNotificationsPermissionGranted"
    | "setPushEnabled"
    | "setUploadFilesEnabled"
    | "setVoiceInputEnabled"
  >;
  actionState: Pick<
    AppLockControllerParams,
    | "isReauthenticationStillValid"
    | "openReauthFlow"
    | "registerSecurityEvent"
    | "resolveLockTimeoutMs"
  >;
}

export function useInspectorRootAppLockController({
  sessionState,
  permissionState,
  setterState,
  actionState,
}: UseInspectorRootAppLockControllerInput) {
  return useAppLockController({
    appLocked: sessionState.appLocked,
    session: sessionState.session,
    settingsHydrated: sessionState.settingsHydrated,
    requireAuthOnOpen: sessionState.requireAuthOnOpen,
    lockTimeout: sessionState.lockTimeout,
    reauthenticationExpiresAt: sessionState.reauthenticationExpiresAt,
    deviceBiometricsEnabled: permissionState.deviceBiometricsEnabled,
    microphonePermissionGranted: permissionState.microphonePermissionGranted,
    cameraPermissionGranted: permissionState.cameraPermissionGranted,
    filesPermissionGranted: permissionState.filesPermissionGranted,
    notificationsPermissionGranted:
      permissionState.notificationsPermissionGranted,
    biometricsPermissionGranted: permissionState.biometricsPermissionGranted,
    pushEnabled: permissionState.pushEnabled,
    uploadFilesEnabled: permissionState.uploadFilesEnabled,
    voiceInputEnabled: permissionState.voiceInputEnabled,
    setMicrophonePermissionGranted: setterState.setMicrophonePermissionGranted,
    setCameraPermissionGranted: setterState.setCameraPermissionGranted,
    setFilesPermissionGranted: setterState.setFilesPermissionGranted,
    setNotificationsPermissionGranted:
      setterState.setNotificationsPermissionGranted,
    setBiometricsPermissionGranted: setterState.setBiometricsPermissionGranted,
    setPushEnabled: setterState.setPushEnabled,
    setDeviceBiometricsEnabled: setterState.setDeviceBiometricsEnabled,
    setUploadFilesEnabled: setterState.setUploadFilesEnabled,
    setVoiceInputEnabled: setterState.setVoiceInputEnabled,
    setAppLocked: setterState.setAppLocked,
    isReauthenticationStillValid: actionState.isReauthenticationStillValid,
    resolveLockTimeoutMs: actionState.resolveLockTimeoutMs,
    openReauthFlow: actionState.openReauthFlow,
    registerSecurityEvent: actionState.registerSecurityEvent,
  });
}
