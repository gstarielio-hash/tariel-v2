import { act, renderHook } from "@testing-library/react-native";

import { useInspectorRootLocalState } from "./useInspectorRootLocalState";

describe("useInspectorRootLocalState", () => {
  it("expõe o estado inicial e setters básicos do root", () => {
    const { result } = renderHook(() =>
      useInspectorRootLocalState({
        cacheLeituraVazio: {
          bootstrap: null,
          laudos: [],
          conversaAtual: null,
          conversasPorLaudo: {},
          mesaPorLaudo: {},
          chatDrafts: {},
          mesaDrafts: {},
          chatAttachmentDrafts: {},
          mesaAttachmentDrafts: {},
          updatedAt: "",
        },
      }),
    );

    expect(result.current.abaAtiva).toBe("chat");
    expect(result.current.filtroFilaOffline).toBe("all");
    expect(result.current.filtroHistorico).toBe("todos");
    expect(result.current.cacheLeitura.laudos).toEqual([]);

    act(() => {
      result.current.setMensagem("teste");
      result.current.setFiltroFilaOffline("mesa");
      result.current.setBloqueioAppAtivo(true);
    });

    expect(result.current.mensagem).toBe("teste");
    expect(result.current.filtroFilaOffline).toBe("mesa");
    expect(result.current.bloqueioAppAtivo).toBe(true);
  });
});
