jest.mock("./observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

import {
  carregarGateQualidadeLaudoMobile,
  enviarMensagemChatMobile,
  finalizarLaudoMobile,
  reabrirLaudoMobile,
  salvarGuidedInspectionDraftMobile,
} from "./chatApi";

function criarResposta(
  body: string,
  init?: { status?: number; contentType?: string },
) {
  const status = init?.status ?? 200;
  const headers = new Headers();
  headers.set("content-type", init?.contentType ?? "application/json");
  return {
    ok: status >= 200 && status < 300,
    status,
    headers,
    text: async () => body,
  } as Response;
}

describe("chatApi", () => {
  const fetchMock = jest.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      value: fetchMock,
    });
  });

  it("normaliza a resposta JSON do chat", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          laudo_id: 42,
          texto: "Resposta pronta",
          modo: "curto",
          citacoes: [{ fonte: "manual" }],
          confianca_ia: { score: 0.91 },
        }),
      ),
    );

    await expect(
      enviarMensagemChatMobile("token-123", {
        mensagem: "oi",
        laudoId: 42,
        modo: "detalhado",
      }),
    ).resolves.toMatchObject({
      laudoId: 42,
      assistantText: "Resposta pronta",
      modo: "curto",
      citacoes: [{ fonte: "manual" }],
      confiancaIa: { score: 0.91 },
    });
  });

  it("agrega eventos SSE do chat em uma resposta final", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        [
          'data: {"laudo_id":77}',
          "",
          'data: {"texto":"Primeira parte "}',
          "",
          'data: {"texto":"segunda parte","citacoes":[{"fonte":"guia"}],"confianca_ia":{"score":0.88}}',
          "",
          "data: [FIM]",
          "",
        ].join("\n"),
        { contentType: "text/event-stream" },
      ),
    );

    await expect(
      enviarMensagemChatMobile("token-123", {
        mensagem: "resuma",
        modo: "deepresearch",
      }),
    ).resolves.toMatchObject({
      laudoId: 77,
      assistantText: "Primeira parte segunda parte",
      modo: "deep_research",
      citacoes: [{ fonte: "guia" }],
      confiancaIa: { score: 0.88 },
    });
  });

  it("envia contexto guiado junto da mesma thread canonica do chat", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          laudo_id: 77,
          texto: "Resposta pronta",
          modo: "detalhado",
        }),
      ),
    );

    await enviarMensagemChatMobile("token-123", {
      mensagem: "Registrar fotos e contexto",
      laudoId: 77,
      guidedInspectionDraft: {
        template_key: "nr35_linha_vida",
        template_label: "NR35 Linha de Vida",
        started_at: "2026-04-06T22:30:00.000Z",
        current_step_index: 1,
        completed_step_ids: ["identificacao_laudo"],
        checklist: [
          {
            id: "identificacao_laudo",
            title: "Identificacao",
            prompt: "registre o ativo",
            evidence_hint: "codigo do ativo",
          },
        ],
        evidence_bundle_kind: "case_thread",
        evidence_refs: [],
        mesa_handoff: null,
      },
      guidedInspectionContext: {
        template_key: "nr35_linha_vida",
        step_id: "contexto_vistoria",
        step_title: "Contexto da vistoria",
        attachment_kind: "image",
      },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"guided_inspection_context"'),
      }),
    );
    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body || "{}"));
    expect(body.guided_inspection_draft?.evidence_bundle_kind).toBe(
      "case_thread",
    );
    expect(body.guided_inspection_context).toEqual({
      template_key: "nr35_linha_vida",
      step_id: "contexto_vistoria",
      step_title: "Contexto da vistoria",
      attachment_kind: "image",
    });
  });

  it("envia preferencias de IA em campo interno separado do texto visivel", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          laudo_id: 12,
          texto: "Resposta pronta",
          modo: "detalhado",
        }),
      ),
    );

    await enviarMensagemChatMobile("token-123", {
      mensagem: "Texto visível",
      preferenciasIaMobile:
        "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]",
      laudoId: 12,
    });

    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body || "{}"));
    expect(body.mensagem).toBe("Texto visível");
    expect(body.preferencias_ia_mobile).toContain("[preferencias_ia_mobile]");
  });

  it("salva o draft guiado canonico do laudo mobile", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          ok: true,
          laudo_id: 21,
          guided_inspection_draft: {
            template_key: "nr35_linha_vida",
            template_label: "NR35 Linha de Vida",
            started_at: "2026-04-06T22:30:00.000Z",
            current_step_index: 2,
            completed_step_ids: ["identificacao_laudo"],
            checklist: [
              {
                id: "identificacao_laudo",
                title: "Identificacao",
                prompt: "registre o ativo",
                evidence_hint: "codigo do ativo",
              },
            ],
          },
        }),
      ),
    );

    await expect(
      salvarGuidedInspectionDraftMobile("token-123", 21, {
        guided_inspection_draft: {
          template_key: "nr35_linha_vida",
          template_label: "NR35 Linha de Vida",
          started_at: "2026-04-06T22:30:00.000Z",
          current_step_index: 2,
          completed_step_ids: ["identificacao_laudo"],
          checklist: [
            {
              id: "identificacao_laudo",
              title: "Identificacao",
              prompt: "registre o ativo",
              evidence_hint: "codigo do ativo",
            },
          ],
        },
      }),
    ).resolves.toMatchObject({
      ok: true,
      laudo_id: 21,
      guided_inspection_draft: {
        template_key: "nr35_linha_vida",
        current_step_index: 2,
      },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        "/app/api/mobile/laudo/21/guided-inspection-draft",
      ),
      expect.objectContaining({
        method: "PUT",
      }),
    );
  });

  it("reabre o laudo com politica explicita para o PDF emitido anterior", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          estado: "relatorio_ativo",
          laudo_id: 21,
          status_card: "aberto",
          permite_edicao: true,
          permite_reabrir: false,
          issued_document_policy_applied: "hide_from_case",
          had_previous_issued_document: true,
          previous_issued_document_visible_in_case: false,
          internal_learning_candidate_registered: true,
          laudo_card: null,
        }),
      ),
    );

    await expect(
      reabrirLaudoMobile("token-123", 21, {
        issued_document_policy: "hide_from_case",
      }),
    ).resolves.toMatchObject({
      estado: "relatorio_ativo",
      issued_document_policy_applied: "hide_from_case",
      previous_issued_document_visible_in_case: false,
    });

    const [, requestInit] = fetchMock.mock.calls[0];
    expect(requestInit.method).toBe("POST");
    expect(requestInit.headers.get("content-type")).toBe("application/json");
    expect(JSON.parse(String(requestInit.body))).toMatchObject({
      issued_document_policy: "hide_from_case",
    });
  });

  it("carrega o quality gate mesmo quando ele volta bloqueado em 422", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          codigo: "GATE_QUALIDADE_REPROVADO",
          aprovado: false,
          mensagem: "Faltam evidências mínimas.",
          tipo_template: "nr13",
          template_nome: "NR13",
          resumo: {
            textos_campo: 1,
            evidencias: 1,
            fotos: 0,
          },
          itens: [],
          faltantes: [
            {
              id: "fotos_essenciais",
              categoria: "foto",
              titulo: "Fotos essenciais da inspeção",
              status: "faltante",
              atual: 0,
              minimo: 2,
              observacao:
                "Envie imagens dos pontos críticos antes de finalizar.",
            },
          ],
          roteiro_template: {
            titulo: "Roteiro obrigatório do template",
            descricao: "Colete o mínimo necessário.",
            itens: [],
          },
          human_override_policy: {
            available: true,
            reason_required: true,
            allowed_override_cases: ["nr_divergence"],
            allowed_override_case_labels: ["Divergência normativa"],
            matched_override_cases: ["nr_divergence"],
            matched_override_case_labels: ["Divergência normativa"],
            overrideable_items: [],
            hard_blockers: [],
            family_key: "nr13",
            responsibility_notice: "A assinatura final continua humana.",
            message: "A exceção governada está disponível.",
          },
        }),
        { status: 422 },
      ),
    );

    await expect(
      carregarGateQualidadeLaudoMobile("token-123", 21),
    ).resolves.toMatchObject({
      aprovado: false,
      human_override_policy: {
        available: true,
      },
      faltantes: [
        expect.objectContaining({
          id: "fotos_essenciais",
        }),
      ],
    });
  });

  it("lança erro estruturado quando a finalização volta bloqueada pelo quality gate", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          codigo: "GATE_QUALIDADE_REPROVADO",
          aprovado: false,
          mensagem: "Finalize bloqueado: faltam itens obrigatórios.",
          tipo_template: "nr13",
          template_nome: "NR13",
          resumo: {},
          itens: [],
          faltantes: [],
          roteiro_template: null,
          human_override_policy: {
            available: true,
            reason_required: true,
            allowed_override_cases: ["nr_divergence"],
            allowed_override_case_labels: ["Divergência normativa"],
            matched_override_cases: ["nr_divergence"],
            matched_override_case_labels: ["Divergência normativa"],
            overrideable_items: [],
            hard_blockers: [],
            family_key: "nr13",
            responsibility_notice: "A assinatura final continua humana.",
            message: "A exceção governada está disponível.",
          },
        }),
        { status: 422 },
      ),
    );

    await expect(
      finalizarLaudoMobile("token-123", 21, {
        qualityGateOverride: {
          enabled: true,
          reason: "Seguindo com justificativa interna detalhada.",
          cases: ["nr_divergence"],
        },
      }),
    ).rejects.toEqual(
      expect.objectContaining({
        name: "MobileQualityGateError",
        stage: "finalize",
        payload: expect.objectContaining({
          aprovado: false,
        }),
      }),
    );
  });

  it("normaliza a resposta de finalização do caso para o app Android", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          success: true,
          message: "Caso enviado para a Mesa Avaliadora a partir do mobile.",
          laudo_id: 31,
          estado: "aguardando",
          status_card: "aguardando",
          permite_reabrir: false,
          review_mode_final: "mesa_required",
          allowed_surface_actions: [],
          laudo_card: {
            id: 31,
            titulo: "Caso 31",
            preview: "",
            pinado: false,
            data_iso: "2026-04-13T12:00:00.000Z",
            data_br: "13/04/2026",
            hora_br: "09:00",
            tipo_template: "nr13",
            status_revisao: "aguardando",
            status_card: "aguardando",
            status_card_label: "Aguardando mesa",
            permite_edicao: false,
            permite_reabrir: false,
            possui_historico: true,
          },
        }),
      ),
    );

    await expect(finalizarLaudoMobile("token-123", 31)).resolves.toMatchObject({
      success: true,
      laudo_id: 31,
      permite_edicao: false,
      status_card: "aguardando",
    });
  });
});
