jest.mock("expo-file-system/legacy", () => ({
  cacheDirectory: "file:///cache/",
  documentDirectory: "file:///documents/",
  makeDirectoryAsync: jest.fn(),
  writeAsStringAsync: jest.fn(),
}));

jest.mock("expo-sharing", () => ({
  isAvailableAsync: jest.fn(),
  shareAsync: jest.fn(),
}));

import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";

import {
  compartilharTextoExportado,
  construirUrlCanalSuporte,
  ehOpcaoValida,
  erroSugereModoOffline,
  formatarHorarioAtividade,
  obterEscalaDensidade,
  obterEscalaFonte,
  obterIntervaloMonitoramentoMs,
  obterTimeoutBloqueioMs,
  serializarPayloadExportacao,
} from "./appSupportHelpers";

describe("appSupportHelpers", () => {
  afterEach(() => {
    jest.restoreAllMocks();
    jest.clearAllMocks();
  });

  it("valida opcoes, urls e serializacao", () => {
    expect(ehOpcaoValida("b", ["a", "b"] as const)).toBe(true);
    expect(ehOpcaoValida("c", ["a", "b"] as const)).toBe(false);
    expect(construirUrlCanalSuporte("62999999999")).toBe(
      "https://wa.me/62999999999",
    );
    expect(serializarPayloadExportacao({ ok: true })).toContain('"ok": true');
  });

  it("resolve escala, timeout e heuristica offline", () => {
    expect(obterIntervaloMonitoramentoMs(true, "Desempenho")).toBe(60_000);
    expect(obterIntervaloMonitoramentoMs(false, "Otimizado")).toBe(40_000);
    expect(obterEscalaFonte("grande")).toBe(1.08);
    expect(obterEscalaDensidade("compacta")).toBe(0.9);
    expect(obterTimeoutBloqueioMs("5 minutos")).toBe(300_000);
    expect(erroSugereModoOffline("Network request failed")).toBe(true);
    expect(erroSugereModoOffline("erro local")).toBe(false);
  });

  it("formata horario de atividade", () => {
    expect(formatarHorarioAtividade("invalido")).toBe("agora");
    expect(formatarHorarioAtividade("2026-03-30T10:05:00.000Z")).toMatch(
      /\d{2}\/\d{2}, \d{2}:\d{2}/,
    );
  });

  it("exporta texto e compartilha quando disponivel", async () => {
    jest
      .spyOn(Date.prototype, "toISOString")
      .mockReturnValue("2026-03-30T10:00:00.000Z");
    (Sharing.isAvailableAsync as jest.Mock).mockResolvedValue(true);

    const ok = await compartilharTextoExportado({
      extension: "json",
      content: "{}",
      prefixo: "diagnostico",
    });

    expect(ok).toBe(true);
    expect(FileSystem.makeDirectoryAsync).toHaveBeenCalledWith(
      "file:///cache/tariel-exports",
      { intermediates: true },
    );
    expect(FileSystem.writeAsStringAsync).toHaveBeenCalledWith(
      "file:///cache/tariel-exports/diagnostico-2026-03-30T10-00-00-000Z.json",
      "{}",
    );
    expect(Sharing.shareAsync).toHaveBeenCalled();
  });
});
