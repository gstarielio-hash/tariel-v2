import {
  obterResumoReferenciaMensagem,
  resumoMensagemAtividade,
} from "./messagePreviewHelpers";

describe("messagePreviewHelpers", () => {
  it("resume mensagem com fallback e limite", () => {
    expect(resumoMensagemAtividade("   ", "fallback")).toBe("fallback");
    expect(resumoMensagemAtividade("a".repeat(130), "fallback")).toHaveLength(
      120,
    );
  });

  it("prioriza a mensagem referenciada em chat ou mesa", () => {
    expect(
      obterResumoReferenciaMensagem(
        7,
        [{ id: 7, texto: "Mensagem do chat" }] as any,
        [{ id: 7, texto: "Mensagem da mesa" }] as any,
      ),
    ).toBe("Mensagem do chat");

    expect(
      obterResumoReferenciaMensagem(8, [], [
        { id: 8, texto: "Mensagem da mesa" },
      ] as any),
    ).toBe("Mensagem da mesa");

    expect(obterResumoReferenciaMensagem(9, [], [])).toBe("Mensagem #9");
  });
});
