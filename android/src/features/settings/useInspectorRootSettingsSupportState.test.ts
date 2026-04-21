import { renderHook } from "@testing-library/react-native";

jest.mock("./useSettingsPresentation", () => ({
  useSettingsPresentation: jest.fn(),
}));

jest.mock("./useSettingsNavigation", () => ({
  useSettingsNavigation: jest.fn(),
}));

jest.mock("../security/useSecurityEventLog", () => ({
  useSecurityEventLog: jest.fn(),
}));

import { useSecurityEventLog } from "../security/useSecurityEventLog";
import { useInspectorRootSettingsSupportState } from "./useInspectorRootSettingsSupportState";
import { useSettingsNavigation } from "./useSettingsNavigation";
import { useSettingsPresentation } from "./useSettingsPresentation";

describe("useInspectorRootSettingsSupportState", () => {
  it("agrega presentation, navigation e security event log em um unico hook root", () => {
    const setEventosSeguranca = jest.fn();
    const registrarEventoSegurancaLocal = jest.fn();
    const presentationResult = {
      state: {
        eventosSeguranca: [],
      },
      actions: {
        setEventosSeguranca,
      },
    };
    const navigationResult = {
      state: {
        settingsDrawerPage: "overview",
      },
      actions: {
        handleAbrirPaginaConfiguracoes: jest.fn(),
      },
    };

    jest
      .mocked(useSettingsPresentation)
      .mockReturnValue(presentationResult as any);
    jest.mocked(useSettingsNavigation).mockReturnValue(navigationResult as any);
    jest.mocked(useSecurityEventLog).mockReturnValue({
      registrarEventoSegurancaLocal,
    });

    const { result } = renderHook(() => useInspectorRootSettingsSupportState());

    expect(useSettingsPresentation).toHaveBeenCalledTimes(1);
    expect(useSettingsNavigation).toHaveBeenCalledTimes(1);
    expect(useSecurityEventLog).toHaveBeenCalledWith({
      setEventosSeguranca,
    });
    expect(result.current.presentationState).toBe(presentationResult.state);
    expect(result.current.presentationActions).toBe(presentationResult.actions);
    expect(result.current.navigationState).toBe(navigationResult.state);
    expect(result.current.navigationActions).toBe(navigationResult.actions);
    expect(result.current.registrarEventoSegurancaLocal).toBe(
      registrarEventoSegurancaLocal,
    );
  });
});
