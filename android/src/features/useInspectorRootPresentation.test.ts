import { renderHook } from "@testing-library/react-native";

const mockBuildInspectorRootDerivedState = jest.fn();
const mockBuildInspectorRootSettingsSurfaceInput = jest.fn();
const mockUseInspectorRootSettingsSurface = jest.fn();
const mockBuildInspectorRootFinalScreenState = jest.fn();

jest.mock("./buildInspectorRootDerivedState", () => ({
  buildInspectorRootDerivedState: (...args: unknown[]) =>
    mockBuildInspectorRootDerivedState(...args),
}));

jest.mock("./settings/buildInspectorRootSettingsSurfaceInput", () => ({
  buildInspectorRootSettingsSurfaceInput: (...args: unknown[]) =>
    mockBuildInspectorRootSettingsSurfaceInput(...args),
}));

jest.mock("./settings/useInspectorRootSettingsSurface", () => ({
  useInspectorRootSettingsSurface: (...args: unknown[]) =>
    mockUseInspectorRootSettingsSurface(...args),
}));

jest.mock("./buildInspectorRootFinalScreenState", () => ({
  buildInspectorRootFinalScreenState: (...args: unknown[]) =>
    mockBuildInspectorRootFinalScreenState(...args),
}));

import { useInspectorRootPresentation } from "./useInspectorRootPresentation";

describe("useInspectorRootPresentation", () => {
  it("orquestra estado derivado, settings surface e composição final da tela", () => {
    const bootstrap = { bootstrap: "ok" } as never;
    const controllers = { controllers: "ok" } as never;
    const derivedState = {
      inspectorBaseDerivedState: { base: "ok" },
    };
    const settingsSurface = { surface: "ok" };
    const finalScreenState = {
      authenticatedLayoutProps: { auth: true },
      loginScreenProps: { login: true },
    };

    mockBuildInspectorRootDerivedState.mockReturnValue(derivedState);
    mockBuildInspectorRootSettingsSurfaceInput.mockReturnValue({
      input: "settings",
    });
    mockUseInspectorRootSettingsSurface.mockReturnValue(settingsSurface);
    mockBuildInspectorRootFinalScreenState.mockReturnValue(finalScreenState);

    const { result } = renderHook(() =>
      useInspectorRootPresentation({
        bootstrap,
        controllers,
      }),
    );

    expect(mockBuildInspectorRootDerivedState).toHaveBeenCalledWith(bootstrap);
    expect(mockBuildInspectorRootSettingsSurfaceInput).toHaveBeenCalledWith({
      bootstrap,
      controllers,
      derivedState,
    });
    expect(mockUseInspectorRootSettingsSurface).toHaveBeenCalledWith({
      input: "settings",
    });
    expect(mockBuildInspectorRootFinalScreenState).toHaveBeenCalledWith({
      bootstrap,
      controllers,
      derivedState,
      settingsSurface,
    });
    expect(result.current).toEqual({
      authenticatedLayoutProps: finalScreenState.authenticatedLayoutProps,
      inspectorBaseDerivedState: derivedState.inspectorBaseDerivedState,
      loginScreenProps: finalScreenState.loginScreenProps,
    });
  });
});
