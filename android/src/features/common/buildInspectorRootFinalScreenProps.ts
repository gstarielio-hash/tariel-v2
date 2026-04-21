import { buildThreadContextState } from "../chat/buildThreadContextState";
import { buildInspectorSessionModalsRootProps } from "./buildInspectorRootChromeProps";
import {
  buildInspectorRootAuthenticatedLayoutProps,
  buildInspectorRootLoginScreenProps,
} from "./buildInspectorRootScreenProps";

interface BuildInspectorRootFinalScreenPropsInput {
  authenticatedState: Omit<
    Parameters<typeof buildInspectorRootAuthenticatedLayoutProps>[0],
    "shellState" | "threadContextState"
  > & {
    shellState: Omit<
      Parameters<
        typeof buildInspectorRootAuthenticatedLayoutProps
      >[0]["shellState"],
      "sessionModalsStackProps"
    >;
  };
  loginState: Parameters<typeof buildInspectorRootLoginScreenProps>[0];
  sessionModalsState: Parameters<
    typeof buildInspectorSessionModalsRootProps
  >[0];
  threadContextInput: Parameters<typeof buildThreadContextState>[0];
}

export function buildInspectorRootFinalScreenProps({
  authenticatedState,
  loginState,
  sessionModalsState,
  threadContextInput,
}: BuildInspectorRootFinalScreenPropsInput) {
  const sessionModalsStackProps =
    buildInspectorSessionModalsRootProps(sessionModalsState);
  const threadContextState = buildThreadContextState(threadContextInput);
  const authenticatedLayoutProps = buildInspectorRootAuthenticatedLayoutProps({
    ...authenticatedState,
    shellState: {
      ...authenticatedState.shellState,
      sessionModalsStackProps,
    },
    threadContextState,
  });
  const loginScreenProps = buildInspectorRootLoginScreenProps(loginState);

  return {
    authenticatedLayoutProps,
    loginScreenProps,
    sessionModalsStackProps,
    threadContextState,
  };
}
