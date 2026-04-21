import { useVoiceInputController } from "./useVoiceInputController";

type VoiceInputControllerParams = Parameters<typeof useVoiceInputController>[0];

interface UseInspectorRootVoiceInputControllerInput {
  capabilityState: Pick<
    VoiceInputControllerParams,
    | "entradaPorVoz"
    | "microfonePermitido"
    | "speechEnabled"
    | "voiceInputUnavailableMessage"
    | "voiceRuntimeSupported"
  >;
  voiceState: Pick<VoiceInputControllerParams, "preferredVoiceId" | "voices">;
  actionState: Pick<
    VoiceInputControllerParams,
    | "onOpenSystemSettings"
    | "onSetMicrofonePermitido"
    | "onSetPreferredVoiceId"
    | "onShowAlert"
  >;
}

export function useInspectorRootVoiceInputController({
  capabilityState,
  voiceState,
  actionState,
}: UseInspectorRootVoiceInputControllerInput) {
  return useVoiceInputController({
    entradaPorVoz: capabilityState.entradaPorVoz,
    microfonePermitido: capabilityState.microfonePermitido,
    preferredVoiceId: voiceState.preferredVoiceId,
    speechEnabled: capabilityState.speechEnabled,
    voiceInputUnavailableMessage: capabilityState.voiceInputUnavailableMessage,
    voiceRuntimeSupported: capabilityState.voiceRuntimeSupported,
    voices: voiceState.voices,
    onOpenSystemSettings: actionState.onOpenSystemSettings,
    onSetMicrofonePermitido: actionState.onSetMicrofonePermitido,
    onSetPreferredVoiceId: actionState.onSetPreferredVoiceId,
    onShowAlert: actionState.onShowAlert,
  });
}
