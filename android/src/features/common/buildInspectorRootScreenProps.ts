import {
  buildInspectorAuthenticatedLayoutScreenProps,
  buildInspectorLoginScreenProps,
} from "./buildInspectorScreenProps";

type BuildInspectorAuthenticatedLayoutRootPropsInput = Parameters<
  typeof buildInspectorAuthenticatedLayoutScreenProps
>[0];

type BuildInspectorLoginRootPropsInput = Parameters<
  typeof buildInspectorLoginScreenProps
>[0];

export function buildInspectorRootAuthenticatedLayoutProps(
  input: BuildInspectorAuthenticatedLayoutRootPropsInput,
) {
  return buildInspectorAuthenticatedLayoutScreenProps(input);
}

export function buildInspectorRootLoginScreenProps(
  input: BuildInspectorLoginRootPropsInput,
) {
  return buildInspectorLoginScreenProps(input);
}
