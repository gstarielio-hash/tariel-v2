import {
  aplicarPreferenciasLaudos,
  buildHistorySections,
  filtrarThreadContextChips,
} from "./historyHelpers";

describe("historyHelpers", () => {
  it("filtra chips nulos", () => {
    expect(filtrarThreadContextChips(["a", null, "b"])).toEqual(["a", "b"]);
  });

  it("aplica preferencias de fixado e oculto", () => {
    expect(
      aplicarPreferenciasLaudos(
        [
          { id: 1, pinado: false, preview: "Oculto" },
          {
            id: 2,
            pinado: false,
            preview:
              "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]",
          },
        ] as any,
        [2],
        [1],
      ),
    ).toEqual([{ id: 2, pinado: true, preview: "Evidência enviada" }]);
  });

  it("agrupa historico por secao cronologica e fixadas", () => {
    const agora = new Date("2026-03-30T10:00:00.000Z");
    jest.useFakeTimers();
    jest.setSystemTime(agora);

    const secoes = buildHistorySections([
      { id: 1, pinado: true, data_iso: "2026-03-30T09:00:00.000Z" },
      { id: 2, pinado: false, data_iso: "2026-03-30T08:00:00.000Z" },
      { id: 3, pinado: false, data_iso: "2026-03-29T08:00:00.000Z" },
      { id: 4, pinado: false, data_iso: "2026-03-20T08:00:00.000Z" },
    ] as any);

    expect(secoes.map((item) => item.key)).toEqual([
      "pinned",
      "today",
      "yesterday",
      "older",
    ]);
    jest.useRealTimers();
  });
});
