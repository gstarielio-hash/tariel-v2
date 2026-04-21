import { useCallback } from "react";
import type { Dispatch, SetStateAction } from "react";

import type { ActiveThread, ChatState } from "../chat/types";
import {
  advanceGuidedInspectionDraft,
  createGuidedInspectionDraft,
  getGuidedInspectionProgress,
  type GuidedInspectionDraft,
  type GuidedInspectionTemplateKey,
  resolveGuidedInspectionTemplateKey,
} from "./guidedInspection";

interface UseInspectorRootGuidedInspectionControllerInput {
  actionState: {
    onShowAlert: (title: string, message: string) => void;
  };
  state: {
    activeThread: ActiveThread;
    conversation: ChatState | null;
    draft: GuidedInspectionDraft | null;
  };
  setterState: {
    setActiveThread: Dispatch<SetStateAction<ActiveThread>>;
    setErrorConversation: Dispatch<SetStateAction<string>>;
    setGuidedInspectionDraft: Dispatch<
      SetStateAction<GuidedInspectionDraft | null>
    >;
    setMessage: Dispatch<SetStateAction<string>>;
    setThreadHomeVisible: Dispatch<SetStateAction<boolean>>;
  };
}

export interface StartGuidedInspectionOptions {
  draft?: GuidedInspectionDraft | null;
  ignoreActiveConversation?: boolean;
  templateKey?: GuidedInspectionTemplateKey | null;
  tipoTemplate?: string | null;
}

export function useInspectorRootGuidedInspectionController({
  actionState,
  state,
  setterState,
}: UseInspectorRootGuidedInspectionControllerInput) {
  const handleStartGuidedInspection = useCallback(
    (options?: StartGuidedInspectionOptions) => {
      if (state.conversation?.laudoId && !options?.ignoreActiveConversation) {
        actionState.onShowAlert(
          "Inspecao guiada",
          "Abra um novo chat antes de iniciar uma inspecao guiada.",
        );
        return;
      }

      const resolvedTemplateKey =
        options?.templateKey ||
        resolveGuidedInspectionTemplateKey(
          options?.tipoTemplate ||
            state.conversation?.laudoCard?.tipo_template ||
            state.draft?.templateKey,
        );
      const nextDraft =
        options?.draft ||
        (state.draft?.templateKey === resolvedTemplateKey
          ? state.draft
          : null) ||
        createGuidedInspectionDraft(resolvedTemplateKey);
      setterState.setActiveThread("chat");
      setterState.setGuidedInspectionDraft(nextDraft);
      setterState.setThreadHomeVisible(false);
      setterState.setErrorConversation("");
      setterState.setMessage("");
    },
    [actionState, setterState, state.conversation?.laudoId, state.draft],
  );

  const handleAdvanceGuidedInspection = useCallback(() => {
    if (!state.draft) {
      return;
    }

    const nextDraft = advanceGuidedInspectionDraft(state.draft);
    const nextProgress = getGuidedInspectionProgress(nextDraft);
    setterState.setGuidedInspectionDraft(nextDraft);
    setterState.setErrorConversation("");
    setterState.setMessage("");

    if (nextProgress.isComplete) {
      actionState.onShowAlert(
        "Inspecao guiada",
        "Checklist base concluido. Revise as evidencias e gere o rascunho do laudo.",
      );
    }
  }, [actionState, setterState, state.draft]);

  const handleStopGuidedInspection = useCallback(() => {
    setterState.setGuidedInspectionDraft(null);
    if (!state.conversation?.laudoId) {
      setterState.setThreadHomeVisible(true);
    }
    setterState.setErrorConversation("");
  }, [setterState, state.conversation?.laudoId]);

  return {
    actions: {
      handleAdvanceGuidedInspection,
      handleStartGuidedInspection,
      handleStopGuidedInspection,
    },
  };
}
