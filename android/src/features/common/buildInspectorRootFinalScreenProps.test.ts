jest.mock("../chat/buildThreadContextState", () => ({
  buildThreadContextState: jest.fn(() => ({
    thread: "context",
  })),
}));

jest.mock("./buildInspectorRootChromeProps", () => ({
  buildInspectorSessionModalsRootProps: jest.fn(() => ({
    chrome: "session-modals",
  })),
}));

jest.mock("./buildInspectorRootScreenProps", () => ({
  buildInspectorRootAuthenticatedLayoutProps: jest.fn(() => ({
    shell: "auth",
  })),
  buildInspectorRootLoginScreenProps: jest.fn(() => ({
    shell: "login",
  })),
}));

import { buildThreadContextState } from "../chat/buildThreadContextState";
import { buildInspectorRootFinalScreenProps } from "./buildInspectorRootFinalScreenProps";
import { buildInspectorSessionModalsRootProps } from "./buildInspectorRootChromeProps";
import {
  buildInspectorRootAuthenticatedLayoutProps,
  buildInspectorRootLoginScreenProps,
} from "./buildInspectorRootScreenProps";

describe("buildInspectorRootFinalScreenProps", () => {
  it("encadeia chrome, contexto de thread e props finais de tela fora do root", () => {
    const input = {
      authenticatedState: {
        baseState: {} as never,
        composerState: {} as never,
        historyState: {} as never,
        sessionState: {} as never,
        shellState: {} as never,
        speechState: {} as never,
        threadState: {} as never,
      },
      loginState: {
        authActions: {} as never,
        authState: {} as never,
        baseState: {} as never,
        presentationState: {} as never,
        setIntroVisivel: jest.fn(),
      },
      sessionModalsState: {
        activityAndLockState: {} as never,
        attachmentState: {} as never,
        baseState: {} as never,
        offlineQueueState: {} as never,
        settingsState: {} as never,
      },
      threadContextInput: {
        conversaAtiva: null,
      } as never,
    };

    const result = buildInspectorRootFinalScreenProps(input);

    expect(buildInspectorSessionModalsRootProps).toHaveBeenCalledWith(
      input.sessionModalsState,
    );
    expect(buildThreadContextState).toHaveBeenCalledWith(
      input.threadContextInput,
    );
    expect(buildInspectorRootAuthenticatedLayoutProps).toHaveBeenCalledWith(
      expect.objectContaining({
        shellState: expect.objectContaining({
          sessionModalsStackProps: { chrome: "session-modals" },
        }),
        threadContextState: { thread: "context" },
      }),
    );
    expect(buildInspectorRootLoginScreenProps).toHaveBeenCalledWith(
      input.loginState,
    );
    expect(result.authenticatedLayoutProps).toEqual({ shell: "auth" });
    expect(result.loginScreenProps).toEqual({ shell: "login" });
    expect(result.sessionModalsStackProps).toEqual({
      chrome: "session-modals",
    });
    expect(result.threadContextState).toEqual({ thread: "context" });
  });
});
