import { buildInspectorRootDerivedState } from "./buildInspectorRootDerivedState";
import { buildInspectorRootFinalScreenState } from "./buildInspectorRootFinalScreenState";
import { buildInspectorRootSettingsSurfaceInput } from "./settings/buildInspectorRootSettingsSurfaceInput";
import { useInspectorRootSettingsSurface } from "./settings/useInspectorRootSettingsSurface";
import type { InspectorRootBootstrap } from "./useInspectorRootBootstrap";
import type { InspectorRootControllers } from "./useInspectorRootControllers";

interface UseInspectorRootPresentationInput {
  bootstrap: InspectorRootBootstrap;
  controllers: InspectorRootControllers;
}

export function useInspectorRootPresentation({
  bootstrap,
  controllers,
}: UseInspectorRootPresentationInput) {
  const derivedState = buildInspectorRootDerivedState(bootstrap);
  const settingsSurface = useInspectorRootSettingsSurface(
    buildInspectorRootSettingsSurfaceInput({
      bootstrap,
      controllers,
      derivedState,
    }),
  );
  const finalScreenState = buildInspectorRootFinalScreenState({
    bootstrap,
    controllers,
    derivedState,
    settingsSurface,
  });

  return {
    authenticatedLayoutProps: finalScreenState.authenticatedLayoutProps,
    inspectorBaseDerivedState: derivedState.inspectorBaseDerivedState,
    loginScreenProps: finalScreenState.loginScreenProps,
  };
}
