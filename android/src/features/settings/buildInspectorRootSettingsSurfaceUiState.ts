import { useInspectorRootSettingsSurface } from "./useInspectorRootSettingsSurface";
import { buildInspectorRootSettingsAccountDeletionState } from "./buildInspectorRootSettingsAccountDeletionState";
import { buildInspectorRootSettingsConfirmExportState } from "./buildInspectorRootSettingsConfirmExportState";
import { buildInspectorRootSettingsToggleState } from "./buildInspectorRootSettingsToggleState";
import { buildInspectorRootSettingsSheetState } from "./buildInspectorRootSettingsSheetState";
import { buildInspectorRootSettingsDrawerState } from "./buildInspectorRootSettingsDrawerState";
import type { InspectorRootBootstrap } from "../useInspectorRootBootstrap";
import type { InspectorRootControllers } from "../useInspectorRootControllers";
import type { InspectorRootPresentationDerivedSnapshot } from "../buildInspectorRootDerivedState";

interface BuildInspectorRootSettingsSurfaceUiStateInput {
  bootstrap: InspectorRootBootstrap;
  controllers: InspectorRootControllers;
  derivedState: InspectorRootPresentationDerivedSnapshot;
}

export function buildInspectorRootSettingsSurfaceUiState({
  bootstrap,
  controllers,
  derivedState,
}: BuildInspectorRootSettingsSurfaceUiStateInput): Parameters<
  typeof useInspectorRootSettingsSurface
>[0]["uiState"] {
  return {
    accountDeletionState: buildInspectorRootSettingsAccountDeletionState({
      bootstrap,
    }),
    confirmExportState: buildInspectorRootSettingsConfirmExportState({
      bootstrap,
    }),
    toggleState: buildInspectorRootSettingsToggleState({
      bootstrap,
      controllers,
    }),
    sheetState: buildInspectorRootSettingsSheetState({
      bootstrap,
      controllers,
      derivedState,
    }),
    drawerState: buildInspectorRootSettingsDrawerState({
      bootstrap,
      controllers,
      derivedState,
    }),
  };
}
