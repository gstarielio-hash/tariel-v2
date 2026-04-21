jest.mock("../../settings/hooks/useSettings", () => ({
  useSettingsStore: jest.fn(),
}));

import { act, renderHook } from "@testing-library/react-native";

import { createDefaultAppSettings } from "../../settings/schema/defaults";
import { useSettingsStore } from "../../settings/hooks/useSettings";
import { useInspectorSettingsBindings } from "./useInspectorSettingsBindings";

function createStoreState() {
  const state = createDefaultAppSettings();
  state.ai.learningOptIn = true;
  state.security.deviceBiometricsEnabled = true;
  return state;
}

function createStoreValue() {
  return {
    hydrated: true,
    state: createStoreState(),
    actions: {
      replaceAll: jest.fn(),
      reset: jest.fn(),
      updateAppearance: jest.fn(),
      updateAi: jest.fn(),
      updateNotifications: jest.fn(),
      updateSpeech: jest.fn(),
      updateDataControls: jest.fn(),
      updateSystem: jest.fn(),
      updateAccount: jest.fn(),
      updateAttachments: jest.fn(),
      updateSecurity: jest.fn(),
      updateWith: jest.fn(),
    },
  };
}

describe("useInspectorSettingsBindings", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("expõe aliases e duplicatas de leitura sem alterar a semântica", () => {
    const store = createStoreValue();
    (useSettingsStore as jest.Mock).mockReturnValue(store);

    const { result } = renderHook(() => useInspectorSettingsBindings());

    expect(result.current.store.settingsHydrated).toBe(true);
    expect(result.current.account.perfilNome).toBe(
      store.state.account.fullName,
    );
    expect(result.current.ai.aprendizadoIa).toBe(true);
    expect(result.current.ai.compartilharMelhoriaIa).toBe(true);
    expect(result.current.ai.entryModePreference).toBe("chat_first");
    expect(result.current.ai.rememberLastCaseMode).toBe(false);
    expect(result.current.security.biometriaLocalSuportada).toBe(false);
    expect(result.current.security.deviceBiometricsEnabled).toBe(false);
  });

  it("preserva setters acoplados de notificações e fala", () => {
    const store = createStoreValue();
    (useSettingsStore as jest.Mock).mockReturnValue(store);

    const { result } = renderHook(() => useInspectorSettingsBindings());

    act(() => {
      result.current.notifications.setSomNotificacao("Silencioso");
      result.current.speech.setSpeechEnabled(false);
      result.current.speech.setEntradaPorVoz(true);
      result.current.speech.setRespostaPorVoz(true);
      result.current.ai.setEntryModePreference("evidence_first");
      result.current.ai.setRememberLastCaseMode(true);
    });

    expect(store.actions.updateNotifications).toHaveBeenCalledWith({
      soundPreset: "Silencioso",
      soundEnabled: false,
    });
    expect(store.actions.updateSpeech).toHaveBeenNthCalledWith(1, {
      enabled: false,
      autoTranscribe: false,
      autoReadResponses: false,
    });
    expect(store.actions.updateSpeech).toHaveBeenNthCalledWith(2, {
      autoTranscribe: true,
      enabled: true,
    });
    expect(store.actions.updateSpeech).toHaveBeenNthCalledWith(3, {
      autoReadResponses: true,
      enabled: true,
    });
    expect(store.actions.updateAi).toHaveBeenCalledWith({
      entryModePreference: "evidence_first",
    });
    expect(store.actions.updateAi).toHaveBeenCalledWith({
      rememberLastCaseMode: true,
    });
  });
});
