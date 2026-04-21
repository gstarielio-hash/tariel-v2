import { useInspectorRootSettingsSurface } from "./useInspectorRootSettingsSurface";
import type { InspectorRootBootstrap } from "../useInspectorRootBootstrap";
import type { InspectorRootControllers } from "../useInspectorRootControllers";
import type { InspectorRootPresentationDerivedSnapshot } from "../buildInspectorRootDerivedState";
import { buildInspectorRootSettingsSurfaceEntryState } from "./buildInspectorRootSettingsSurfaceEntryState";
import { buildInspectorRootSettingsSurfaceOperationsState } from "./buildInspectorRootSettingsSurfaceOperationsState";
import { buildInspectorRootSettingsSurfaceSecurityState } from "./buildInspectorRootSettingsSurfaceSecurityState";
import { buildInspectorRootSettingsSurfaceUiState } from "./buildInspectorRootSettingsSurfaceUiState";

interface BuildInspectorRootSettingsSurfaceInputInput {
  bootstrap: InspectorRootBootstrap;
  controllers: InspectorRootControllers;
  derivedState: InspectorRootPresentationDerivedSnapshot;
}

export function buildInspectorRootSettingsSurfaceInput({
  bootstrap,
  controllers,
  derivedState,
}: BuildInspectorRootSettingsSurfaceInputInput): Parameters<
  typeof useInspectorRootSettingsSurface
>[0] {
  return {
    entryState: buildInspectorRootSettingsSurfaceEntryState({
      bootstrap,
    }),
    operationsState: buildInspectorRootSettingsSurfaceOperationsState({
      bootstrap,
      controllers,
    }),
    securityState: buildInspectorRootSettingsSurfaceSecurityState({
      bootstrap,
    }),
    uiState: buildInspectorRootSettingsSurfaceUiState({
      bootstrap,
      controllers,
      derivedState,
    }),
  };
}
