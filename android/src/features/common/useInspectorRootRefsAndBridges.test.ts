import { act, renderHook } from "@testing-library/react-native";

import { useInspectorRootRefsAndBridges } from "./useInspectorRootRefsAndBridges";

describe("useInspectorRootRefsAndBridges", () => {
  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it("expõe refs e bridges imperativos do root", async () => {
    const onOpenSystemSettings = jest.fn();
    const { result } = renderHook(() =>
      useInspectorRootRefsAndBridges({ onOpenSystemSettings }),
    );

    const carregarListaLaudos = jest.fn(async () => []);
    const registrarNotificacoes = jest.fn();

    act(() => {
      result.current.onRegisterCarregarListaLaudos(carregarListaLaudos);
      result.current.registrarNotificacoesRef.current = registrarNotificacoes;
    });

    await act(async () => {
      await result.current.carregarListaLaudosRef.current("token", true);
    });
    act(() => {
      result.current.onRegistrarNotificacoesViaRef([{ id: "1" } as any]);
    });

    expect(carregarListaLaudos).toHaveBeenCalledWith("token", true);
    expect(registrarNotificacoes).toHaveBeenCalledWith([{ id: "1" }]);

    act(() => {
      result.current.onOpenSystemSettings();
    });
    expect(onOpenSystemSettings).toHaveBeenCalledTimes(1);
  });

  it("agenda callback com timeout", () => {
    jest.useFakeTimers();
    const callback = jest.fn();
    const { result } = renderHook(() =>
      useInspectorRootRefsAndBridges({
        onOpenSystemSettings: jest.fn(),
      }),
    );

    act(() => {
      result.current.onScheduleWithTimeout(callback, 25);
      jest.advanceTimersByTime(25);
    });

    expect(callback).toHaveBeenCalledTimes(1);
  });
});
