import { act, renderHook } from "@testing-library/react-native";
import { Animated } from "react-native";

import { useSidePanelsController } from "./useSidePanelsController";

describe("useSidePanelsController", () => {
  beforeEach(() => {
    jest.spyOn(Animated, "timing").mockReturnValue({
      start: (callback?: (result: { finished: boolean }) => void) =>
        callback?.({ finished: true }),
    } as never);
    jest.spyOn(Animated, "parallel").mockReturnValue({
      start: (callback?: (result: { finished: boolean }) => void) =>
        callback?.({ finished: true }),
    } as never);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  function createParams(
    overrides: Partial<Parameters<typeof useSidePanelsController>[0]> = {},
  ): Parameters<typeof useSidePanelsController>[0] {
    return {
      configuracoesAberta: false,
      historicoAberto: true,
      keyboardHeight: 0,
      resetSettingsNavigation: jest.fn(),
      setHistorySearchFocused: jest.fn(),
      setBuscaHistorico: jest.fn(),
      setConfiguracoesAberta: jest.fn(),
      setHistoricoAberto: jest.fn(),
      ...overrides,
    };
  }

  it("mantem o drawer de historico aberto quando o teclado sobe pela busca do proprio historico", () => {
    const params = createParams();
    const { result, rerender } = renderHook(
      (currentParams: Parameters<typeof useSidePanelsController>[0]) =>
        useSidePanelsController(currentParams),
      { initialProps: params },
    );

    act(() => {
      result.current.setHistorySearchFocused(true);
    });

    rerender({
      ...params,
      keyboardHeight: 320,
    });

    expect(params.setHistoricoAberto).not.toHaveBeenCalled();
    expect(params.setBuscaHistorico).not.toHaveBeenCalled();
  });

  it("fecha o drawer de configuracoes quando o teclado sobe fora do historico", () => {
    const params = createParams({
      configuracoesAberta: true,
      historicoAberto: false,
    });
    const { rerender } = renderHook(
      (currentParams: Parameters<typeof useSidePanelsController>[0]) =>
        useSidePanelsController(currentParams),
      { initialProps: params },
    );

    rerender({
      ...params,
      keyboardHeight: 280,
    });

    expect(params.setConfiguracoesAberta).toHaveBeenCalledWith(false);
    expect(params.resetSettingsNavigation).toHaveBeenCalled();
  });
});
