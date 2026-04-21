import { useExternalAccessActions } from "../auth/useExternalAccessActions";
import { useInspectorShellController } from "./useInspectorShellController";

interface UseInspectorRootShellSupportInput {
  externalAccessState: Parameters<typeof useExternalAccessActions>[0];
  shellState: Parameters<typeof useInspectorShellController>[0];
}

export function useInspectorRootShellSupport({
  externalAccessState,
  shellState,
}: UseInspectorRootShellSupportInput) {
  const shell = useInspectorShellController(shellState);
  const externalAccess = useExternalAccessActions(externalAccessState);

  return {
    ...shell,
    ...externalAccess,
  };
}
