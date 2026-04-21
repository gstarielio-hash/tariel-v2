jest.mock("../../config/observability", () => ({
  configureObservability: jest.fn(),
}));

jest.mock("../../config/crashReports", () => ({
  configureCrashReports: jest.fn(),
}));

jest.mock("../chat/voice", () => ({
  buildVoiceInputUnavailableMessage: jest.fn(),
  loadVoiceRuntimeState: jest.fn(),
}));

jest.mock("../system/runtime", () => ({
  getInstalledAppRuntimeInfo: jest.fn(),
}));

import { act, renderHook, waitFor } from "@testing-library/react-native";

import { configureCrashReports } from "../../config/crashReports";
import { configureObservability } from "../../config/observability";
import { createDefaultAppSettings } from "../../settings/schema/defaults";
import { loadVoiceRuntimeState } from "../chat/voice";
import { getInstalledAppRuntimeInfo } from "../system/runtime";
import { useInspectorRuntimeController } from "./useInspectorRuntimeController";

function createSettings() {
  return createDefaultAppSettings();
}

describe("useInspectorRuntimeController", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (loadVoiceRuntimeState as jest.Mock).mockResolvedValue({
      voices: [],
      ttsSupported: false,
      sttSupported: false,
    });
    (getInstalledAppRuntimeInfo as jest.Mock).mockReturnValue({
      appName: "Tariel Inspetor",
      version: "1.2.3",
      build: "321",
      applicationId: "br.test.tariel",
      versionLabel: "1.2.3",
      buildLabel: "build 321",
      updateStatusFallback: "Sem OTA",
    });
  });

  it("configura observabilidade e crash reports a partir das preferencias", async () => {
    const settingsState = createSettings();
    settingsState.dataControls.analyticsOptIn = true;
    settingsState.dataControls.crashReportsOptIn = false;

    renderHook(() =>
      useInspectorRuntimeController({
        conversationLaudoId: null,
        preferredVoiceId: "",
        setPreferredVoiceId: jest.fn(),
        settingsState,
      }),
    );

    await act(async () => {
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(configureObservability).toHaveBeenCalledWith({
        analyticsOptIn: true,
      });
    });
    expect(configureCrashReports).toHaveBeenCalledWith({ enabled: false });
  });

  it("limpa a voz preferida quando o runtime nao expoe o identificador salvo", async () => {
    (loadVoiceRuntimeState as jest.Mock).mockResolvedValue({
      voices: [{ identifier: "voice-b", name: "Voice B", language: "pt-BR" }],
      ttsSupported: true,
      sttSupported: false,
    });
    const setPreferredVoiceId = jest.fn();

    const { result } = renderHook(() =>
      useInspectorRuntimeController({
        conversationLaudoId: 80,
        preferredVoiceId: "voice-a",
        setPreferredVoiceId,
        settingsState: createSettings(),
      }),
    );

    await act(async () => {
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(result.current.voiceRuntimeState.ttsSupported).toBe(true);
    });

    expect(setPreferredVoiceId).toHaveBeenCalledWith("");
    expect(result.current.appRuntime.buildLabel).toBe("build 321");
  });

  it("gera notice de IA quando o resumo muda na mesma thread", async () => {
    const settingsState = createSettings();
    const { result, rerender } = renderHook(
      ({
        currentSettings,
      }: {
        currentSettings: ReturnType<typeof createSettings>;
      }) =>
        useInspectorRuntimeController({
          conversationLaudoId: 90,
          preferredVoiceId: "",
          setPreferredVoiceId: jest.fn(),
          settingsState: currentSettings,
        }),
      {
        initialProps: {
          currentSettings: settingsState,
        },
      },
    );

    await act(async () => {
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(result.current.aiRequestConfig.summaryLabel).toContain(
        "equilibrado",
      );
    });

    const nextSettings = createSettings();
    nextSettings.ai.model = "avançado";

    rerender({
      currentSettings: nextSettings,
    });

    await waitFor(() => {
      expect(result.current.chatAiBehaviorNotice).toContain(
        "Novas mensagens usarão",
      );
    });
  });
});
