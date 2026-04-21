import { useEffect, useMemo, useRef, useState } from "react";

import { configureCrashReports } from "../../config/crashReports";
import { configureObservability } from "../../config/observability";
import type { AppSettings } from "../../settings";
import {
  buildAttachmentHandlingPolicy,
  type AttachmentHandlingPolicy,
} from "../chat/attachments";
import {
  buildChatAiRequestConfig,
  describeChatAiBehaviorChange,
  type ChatAiRequestConfig,
} from "../chat/preferences";
import { loadVoiceRuntimeState, type VoiceRuntimeState } from "../chat/voice";
import {
  getInstalledAppRuntimeInfo,
  type InstalledAppRuntimeInfo,
} from "../system/runtime";

interface UseInspectorRuntimeControllerParams {
  conversationLaudoId: number | null;
  preferredVoiceId: string;
  setPreferredVoiceId: (value: string) => void;
  settingsState: AppSettings;
}

const EMPTY_VOICE_RUNTIME_STATE: VoiceRuntimeState = {
  voices: [],
  ttsSupported: false,
  sttSupported: false,
};

function buildConversationRuntimeKey(laudoId: number | null): string {
  return typeof laudoId === "number" && Number.isFinite(laudoId) && laudoId > 0
    ? `laudo:${Math.round(laudoId)}`
    : "laudo:none";
}

export function useInspectorRuntimeController({
  conversationLaudoId,
  preferredVoiceId,
  setPreferredVoiceId,
  settingsState,
}: UseInspectorRuntimeControllerParams): {
  aiRequestConfig: ChatAiRequestConfig;
  appRuntime: InstalledAppRuntimeInfo;
  attachmentHandlingPolicy: AttachmentHandlingPolicy;
  chatAiBehaviorNotice: string;
  voiceRuntimeState: VoiceRuntimeState;
} {
  const [voiceRuntimeState, setVoiceRuntimeState] = useState<VoiceRuntimeState>(
    EMPTY_VOICE_RUNTIME_STATE,
  );
  const [chatAiBehaviorNotice, setChatAiBehaviorNotice] = useState("");
  const aiBehaviorByThreadRef = useRef<Record<string, string>>({});

  const appRuntime = useMemo(() => getInstalledAppRuntimeInfo(), []);
  const attachmentHandlingPolicy = useMemo(
    () => buildAttachmentHandlingPolicy(settingsState),
    [settingsState],
  );
  const aiRequestConfig = useMemo(
    () => buildChatAiRequestConfig(settingsState.ai),
    [settingsState.ai],
  );

  useEffect(() => {
    configureObservability({
      analyticsOptIn: settingsState.dataControls.analyticsOptIn,
    });
  }, [settingsState.dataControls.analyticsOptIn]);

  useEffect(() => {
    configureCrashReports({
      enabled: settingsState.dataControls.crashReportsOptIn,
    });
  }, [settingsState.dataControls.crashReportsOptIn]);

  useEffect(() => {
    let ativo = true;
    void loadVoiceRuntimeState(settingsState.speech.voiceLanguage).then(
      (runtime) => {
        if (!ativo) {
          return;
        }
        setVoiceRuntimeState(runtime);
        if (
          preferredVoiceId &&
          !runtime.voices.some((voice) => voice.identifier === preferredVoiceId)
        ) {
          setPreferredVoiceId("");
        }
      },
    );
    return () => {
      ativo = false;
    };
  }, [
    preferredVoiceId,
    setPreferredVoiceId,
    settingsState.speech.voiceLanguage,
  ]);

  useEffect(() => {
    const threadKey = buildConversationRuntimeKey(conversationLaudoId);
    const previousSummary = aiBehaviorByThreadRef.current[threadKey] || "";
    const nextSummary = aiRequestConfig.summaryLabel;
    setChatAiBehaviorNotice(
      describeChatAiBehaviorChange(previousSummary, nextSummary),
    );
    aiBehaviorByThreadRef.current[threadKey] = nextSummary;
  }, [aiRequestConfig.summaryLabel, conversationLaudoId]);

  return {
    aiRequestConfig,
    appRuntime,
    attachmentHandlingPolicy,
    chatAiBehaviorNotice,
    voiceRuntimeState,
  };
}
