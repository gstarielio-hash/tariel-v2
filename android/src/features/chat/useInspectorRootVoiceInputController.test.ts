import { renderHook } from "@testing-library/react-native";

const mockHandleVoiceInputPress = jest.fn();
const mockOnCyclePreferredVoice = jest.fn();

jest.mock("./useVoiceInputController", () => ({
  useVoiceInputController: jest.fn(() => ({
    handleAbrirAjudaDitado: jest.fn(),
    handleVoiceInputPress: mockHandleVoiceInputPress,
    onCyclePreferredVoice: mockOnCyclePreferredVoice,
  })),
}));

import { useVoiceInputController } from "./useVoiceInputController";
import { useInspectorRootVoiceInputController } from "./useInspectorRootVoiceInputController";

function criarInput() {
  return {
    capabilityState: {
      entradaPorVoz: true,
      microfonePermitido: true,
      speechEnabled: true,
      voiceInputUnavailableMessage: "Use o teclado por voz do sistema.",
      voiceRuntimeSupported: true,
    },
    voiceState: {
      preferredVoiceId: "voz-1",
      voices: [{ identifier: "voz-1" }, { identifier: "voz-2" }],
    },
    actionState: {
      onOpenSystemSettings: jest.fn(),
      onSetMicrofonePermitido: jest.fn(),
      onSetPreferredVoiceId: jest.fn(),
      onShowAlert: jest.fn(),
    },
  };
}

describe("useInspectorRootVoiceInputController", () => {
  it("encapsula a composição do trilho de voz sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() =>
      useInspectorRootVoiceInputController(input),
    );
    const mockedHook = jest.mocked(useVoiceInputController);

    result.current.handleVoiceInputPress();
    result.current.onCyclePreferredVoice();

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        entradaPorVoz: input.capabilityState.entradaPorVoz,
        preferredVoiceId: input.voiceState.preferredVoiceId,
        onShowAlert: input.actionState.onShowAlert,
      }),
    );
    expect(mockHandleVoiceInputPress).toHaveBeenCalledTimes(1);
    expect(mockOnCyclePreferredVoice).toHaveBeenCalledTimes(1);
  });
});
