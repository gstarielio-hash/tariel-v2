import {
  calcularBackoffPendenciaOfflineMs,
  criarItemFilaOffline,
  detalheStatusPendenciaOffline,
  iconePendenciaOffline,
  legendaPendenciaOffline,
  pendenciaFilaProntaParaReenvio,
  prioridadePendenciaOffline,
  resumoPendenciaOffline,
} from "./offlineQueueHelpers";

describe("offlineQueueHelpers", () => {
  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it("calcula status, resumo e prioridade da pendencia", () => {
    const item = {
      channel: "chat",
      text: "",
      attachment: {
        kind: "document",
        nomeDocumento: "laudo.pdf",
      },
      nextRetryAt: "2026-03-30T12:00:00.000Z",
      lastError: "falha muito longa ".repeat(10),
      attempts: 2,
      lastAttemptAt: "",
    } as any;

    expect(resumoPendenciaOffline(item)).toBe("Documento: laudo.pdf");
    expect(iconePendenciaOffline(item)).toBe("file-document-outline");
    expect(
      pendenciaFilaProntaParaReenvio(item, Date.UTC(2026, 2, 30, 11)),
    ).toBe(false);
    expect(prioridadePendenciaOffline(item)).toBe(0);
    expect(detalheStatusPendenciaOffline(item, () => "30/03 12:00")).toContain(
      "2 tentativas",
    );
  });

  it("cria item de fila com defaults canonicos", () => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date("2026-03-30T10:00:00.000Z"));
    jest.spyOn(Math, "random").mockReturnValue(0.5);

    const item = criarItemFilaOffline({
      channel: "mesa",
      laudoId: 5,
      text: "  Mensagem  ",
      title: "  Pendencia  ",
      aiMode: "curto",
    });

    expect(item.id).toBe("mesa-1774864800000-8");
    expect(item.createdAt).toBe("2026-03-30T10:00:00.000Z");
    expect(item.text).toBe("Mensagem");
    expect(item.title).toBe("Pendencia");
    expect(item.aiMode).toBe("curto");
  });

  it("preserva o snapshot do draft guiado na pendencia offline", () => {
    const item = criarItemFilaOffline({
      channel: "chat",
      laudoId: 12,
      text: "Contexto da vistoria",
      title: "Laudo 12",
      guidedInspectionDraft: {
        template_key: "nr35_linha_vida",
        template_label: "NR35 Linha de Vida",
        started_at: "2026-04-06T22:30:00.000Z",
        current_step_index: 1,
        completed_step_ids: ["identificacao_laudo"],
        checklist: [
          {
            id: "identificacao_laudo",
            title: "Identificacao do ativo e do laudo",
            prompt: "registre unidade, local e tag",
            evidence_hint: "codigo do ativo e local resumido",
          },
          {
            id: "contexto_vistoria",
            title: "Contexto da vistoria",
            prompt: "confirme responsaveis e data",
            evidence_hint: "nomes, data e acompanhamento",
          },
        ],
        evidence_bundle_kind: "case_thread",
        evidence_refs: [],
        mesa_handoff: null,
      },
    });

    expect(item.guidedInspectionDraft?.template_key).toBe("nr35_linha_vida");
    expect(item.guidedInspectionDraft?.current_step_index).toBe(1);
    expect(legendaPendenciaOffline(item)).toBe(
      "Etapa guiada: Contexto da vistoria",
    );
  });

  it("calcula backoff por tentativas", () => {
    expect(calcularBackoffPendenciaOfflineMs(1)).toBe(30_000);
    expect(calcularBackoffPendenciaOfflineMs(2)).toBe(120_000);
    expect(calcularBackoffPendenciaOfflineMs(3)).toBe(300_000);
    expect(calcularBackoffPendenciaOfflineMs(9)).toBe(600_000);
  });
});
