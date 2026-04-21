import { useInspectorRootConversationControllers } from "./useInspectorRootConversationControllers";
import { useInspectorRootOperationalControllers } from "./useInspectorRootOperationalControllers";
import { useInspectorRootSecurityAndPersistence } from "./useInspectorRootSecurityAndPersistence";
import type { InspectorRootBootstrap } from "./useInspectorRootBootstrap";

export function useInspectorRootControllers(bootstrap: InspectorRootBootstrap) {
  const conversationControllers =
    useInspectorRootConversationControllers(bootstrap);
  const operationalControllers = useInspectorRootOperationalControllers({
    bootstrap,
    conversationControllers,
  });
  const securityAndPersistence = useInspectorRootSecurityAndPersistence({
    bootstrap,
    conversationControllers,
    operationalControllers,
  });

  return {
    ...conversationControllers,
    ...operationalControllers,
    ...securityAndPersistence,
  };
}

export type InspectorRootControllers = ReturnType<
  typeof useInspectorRootControllers
>;
