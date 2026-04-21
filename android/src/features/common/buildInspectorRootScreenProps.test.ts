jest.mock("./buildInspectorScreenProps", () => ({
  buildInspectorAuthenticatedLayoutScreenProps: jest.fn(() => ({
    shell: "auth",
  })),
  buildInspectorLoginScreenProps: jest.fn(() => ({
    shell: "login",
  })),
}));

import * as buildInspectorScreenPropsModule from "./buildInspectorScreenProps";
import {
  buildInspectorRootAuthenticatedLayoutProps,
  buildInspectorRootLoginScreenProps,
} from "./buildInspectorRootScreenProps";

describe("buildInspectorRootScreenProps", () => {
  it("encapsula a montagem dos props do layout autenticado", () => {
    const input = {
      baseState: {} as never,
      composerState: {} as never,
      historyState: {} as never,
      sessionState: {} as never,
      shellState: {} as never,
      speechState: {} as never,
      threadContextState: {} as never,
      threadState: {} as never,
    };

    const result = buildInspectorRootAuthenticatedLayoutProps(input);
    const mockedBuildAuthenticated = jest.mocked(
      buildInspectorScreenPropsModule.buildInspectorAuthenticatedLayoutScreenProps,
    );

    expect(mockedBuildAuthenticated).toHaveBeenCalledWith(input);
    expect(result).toEqual({ shell: "auth" });
  });

  it("encapsula a montagem dos props da tela de login", () => {
    const input = {
      authActions: {} as never,
      authState: {} as never,
      baseState: {} as never,
      presentationState: {} as never,
      setIntroVisivel: jest.fn(),
    };

    const result = buildInspectorRootLoginScreenProps(input);
    const mockedBuildLogin = jest.mocked(
      buildInspectorScreenPropsModule.buildInspectorLoginScreenProps,
    );

    expect(mockedBuildLogin).toHaveBeenCalledWith(input);
    expect(result).toEqual({ shell: "login" });
  });
});
