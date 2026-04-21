import { act, renderHook } from "@testing-library/react-native";
import { Animated, Keyboard } from "react-native";

import { useInspectorShellController } from "./useInspectorShellController";

type KeyboardListener = (event: {
  endCoordinates: {
    height: number;
  };
}) => void;

describe("useInspectorShellController", () => {
  const keyboardListeners = new Map<string, KeyboardListener | (() => void)>();

  beforeEach(() => {
    keyboardListeners.clear();
    jest.useFakeTimers();
    jest.spyOn(Animated, "timing").mockReturnValue({
      start: (callback?: (result: { finished: boolean }) => void) =>
        callback?.({ finished: true }),
    } as never);
    jest.spyOn(Animated, "parallel").mockReturnValue({
      start: (callback?: (result: { finished: boolean }) => void) =>
        callback?.({ finished: true }),
    } as never);
    jest.spyOn(Keyboard, "addListener").mockImplementation(((
      eventName: string,
      listener: KeyboardListener | (() => void),
    ) => {
      keyboardListeners.set(eventName, listener);
      return {
        remove: () => {
          keyboardListeners.delete(eventName);
        },
      } as never;
    }) as unknown as typeof Keyboard.addListener);
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  function createParams(
    overrides: Partial<Parameters<typeof useInspectorShellController>[0]> = {},
  ): Parameters<typeof useInspectorShellController>[0] {
    return {
      appLocked: false,
      onClearTransientSettingsPresentationState: jest.fn(),
      onClearTransientSettingsUiPreservingReauth: jest.fn(),
      onResetAfterSessionEnded: jest.fn(),
      resetSettingsNavigation: jest.fn(),
      scrollRef: {
        current: {
          scrollToEnd: jest.fn(),
        },
      },
      sessionActive: true,
      sessionLoading: false,
      ...overrides,
    };
  }

  it("fecha a apresentacao transitória quando o app fica bloqueado", () => {
    const params = createParams();
    const { result, rerender } = renderHook(
      (currentParams: Parameters<typeof useInspectorShellController>[0]) =>
        useInspectorShellController(currentParams),
      { initialProps: params },
    );

    act(() => {
      result.current.setAnexosAberto(true);
      result.current.setCentralAtividadeAberta(true);
      result.current.setFilaOfflineAberta(true);
      result.current.setPreviewAnexoImagem({
        titulo: "preview",
        uri: "file:///preview.png",
      });
      result.current.abrirHistorico();
    });

    rerender({
      ...params,
      appLocked: true,
    });

    expect(
      params.onClearTransientSettingsUiPreservingReauth,
    ).toHaveBeenCalled();
    expect(result.current.anexosAberto).toBe(false);
    expect(result.current.centralAtividadeAberta).toBe(false);
    expect(result.current.filaOfflineAberta).toBe(false);
    expect(result.current.previewAnexoImagem).toBeNull();
    expect(result.current.historicoAberto).toBe(false);
  });

  it("reseta o shell transitório quando a sessão some", () => {
    const params = createParams();
    const { result, rerender } = renderHook(
      (currentParams: Parameters<typeof useInspectorShellController>[0]) =>
        useInspectorShellController(currentParams),
      { initialProps: params },
    );

    act(() => {
      result.current.setCentralAtividadeAberta(true);
      result.current.setPreviewAnexoImagem({
        titulo: "preview",
        uri: "file:///preview.png",
      });
      result.current.abrirHistorico();
    });

    rerender({
      ...params,
      sessionActive: false,
      sessionLoading: false,
    });

    expect(params.onResetAfterSessionEnded).toHaveBeenCalled();
    expect(params.onClearTransientSettingsPresentationState).toHaveBeenCalled();
    expect(result.current.centralAtividadeAberta).toBe(false);
    expect(result.current.previewAnexoImagem).toBeNull();
    expect(result.current.historicoAberto).toBe(false);
  });

  it("monitora teclado e rola a conversa quando há sessão ativa", () => {
    const params = createParams();
    const { result } = renderHook(() => useInspectorShellController(params));

    const showListener =
      keyboardListeners.get("keyboardWillShow") ||
      keyboardListeners.get("keyboardDidShow");
    const hideListener =
      keyboardListeners.get("keyboardWillHide") ||
      keyboardListeners.get("keyboardDidHide");

    act(() => {
      (showListener as KeyboardListener)({
        endCoordinates: {
          height: 320,
        },
      });
    });

    expect(result.current.keyboardHeight).toBe(320);

    act(() => {
      jest.advanceTimersByTime(120);
    });

    expect(params.scrollRef.current?.scrollToEnd).toHaveBeenCalledWith({
      animated: true,
    });

    act(() => {
      (hideListener as () => void)();
    });

    expect(result.current.keyboardHeight).toBe(0);
  });
});
