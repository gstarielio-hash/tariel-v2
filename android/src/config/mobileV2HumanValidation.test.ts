jest.mock("./observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

import {
  __resetMobileV2HumanValidationRuntimeForTests,
  acknowledgeMobileV2HumanValidationRender,
  attachMobileV2ReadRenderMetadata,
  buildHumanAckPayload,
  extractMobileV2ReadRenderMetadata,
  shouldSendHumanAck,
} from "./mobileV2HumanValidation";

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

describe("mobileV2HumanValidation", () => {
  const fetchMock = jest.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      value: fetchMock,
    });
    __resetMobileV2HumanValidationRuntimeForTests();
  });

  afterAll(() => {
    __resetMobileV2HumanValidationRuntimeForTests();
  });

  it("anexa e extrai metadados internos de leitura para render humano", () => {
    const payload = attachMobileV2ReadRenderMetadata(
      { laudo_id: 21, itens: [] },
      {
        route: "thread",
        deliveryMode: "v2",
        capabilitiesVersion: "2026-03-26.09j",
        rolloutBucket: 12,
        usageMode: "organic_validation",
        validationSessionId: "orgv_human123456",
        operatorRunId: "oprv_human123456",
        suggestedTargetIds: [21, 22],
      },
    );

    expect(extractMobileV2ReadRenderMetadata(payload)).toEqual({
      route: "thread",
      deliveryMode: "v2",
      capabilitiesVersion: "2026-03-26.09j",
      rolloutBucket: 12,
      usageMode: "organic_validation",
      validationSessionId: "orgv_human123456",
      operatorRunId: "oprv_human123456",
      suggestedTargetIds: [21, 22],
    });
    expect(JSON.stringify(payload)).toBe('{"laudo_id":21,"itens":[]}');
  });

  it("envia ack discreto quando ha leitura V2 sob sessao organica ativa", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          ok: true,
          duplicate: false,
          checkpoint: { surface: "thread", target_id: 21 },
        }),
      ),
    );

    await expect(
      acknowledgeMobileV2HumanValidationRender({
        accessToken: "token-123",
        surface: "thread",
        readMetadata: {
          route: "thread",
          deliveryMode: "v2",
          capabilitiesVersion: "2026-03-26.09j",
          rolloutBucket: 12,
          usageMode: "organic_validation",
          validationSessionId: "orgv_human123456",
          operatorRunId: "oprv_human123456",
        },
        targetIds: [21],
      }),
    ).resolves.toBe(true);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/app/api/mobile/v2/organic-validation/ack",
    );
    const [, requestInit] = fetchMock.mock.calls[0];
    expect(requestInit.method).toBe("POST");
    expect(requestInit.headers.get("X-Tariel-Mobile-Validation-Session")).toBe(
      "orgv_human123456",
    );
    expect(requestInit.headers.get("X-Tariel-Mobile-Operator-Run")).toBe(
      "oprv_human123456",
    );
    expect(JSON.parse(String(requestInit.body))).toMatchObject({
      session_id: "orgv_human123456",
      surface: "thread",
      target_id: 21,
      checkpoint_kind: "rendered",
      delivery_mode: "v2",
      operator_run_id: "oprv_human123456",
    });
  });

  it("exige leitura V2 valida e alvos canonicos antes de enviar ack", () => {
    expect(
      shouldSendHumanAck({
        accessToken: "token-123",
        surface: "feed",
        readMetadata: {
          route: "feed",
          deliveryMode: "legacy",
          capabilitiesVersion: "2026-03-26.09m",
          rolloutBucket: 12,
          usageMode: "organic_validation",
          validationSessionId: "orgv_feed123456",
        },
        targetIds: [80],
      }),
    ).toBe(false);

    expect(
      shouldSendHumanAck({
        accessToken: "token-123",
        surface: "thread",
        readMetadata: {
          route: "thread",
          deliveryMode: "v2",
          capabilitiesVersion: "2026-03-26.09m",
          rolloutBucket: 12,
          usageMode: "organic_validation",
          validationSessionId: "orgv_thread123",
          operatorRunId: "oprv_thread123",
        },
        targetIds: [0, 80, 80],
      }),
    ).toBe(true);

    expect(
      buildHumanAckPayload({
        surface: "thread",
        metadata: {
          route: "thread",
          deliveryMode: "v2",
          capabilitiesVersion: "2026-03-26.09m",
          rolloutBucket: 12,
          usageMode: "organic_validation",
          validationSessionId: "orgv_thread123",
          operatorRunId: "oprv_thread123",
        },
        targetId: 80,
        checkpointKind: "rendered",
      }),
    ).toEqual({
      session_id: "orgv_thread123",
      surface: "thread",
      target_id: 80,
      checkpoint_kind: "rendered",
      delivery_mode: "v2",
      operator_run_id: "oprv_thread123",
    });
  });

  it("nao envia ack sem sessao organica valida e ignora falhas sem quebrar", async () => {
    await expect(
      acknowledgeMobileV2HumanValidationRender({
        accessToken: "token-123",
        surface: "feed",
        readMetadata: {
          route: "feed",
          deliveryMode: "legacy",
          capabilitiesVersion: "2026-03-26.09j",
          rolloutBucket: 12,
          usageMode: null,
          validationSessionId: null,
        },
        targetIds: [21],
      }),
    ).resolves.toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();

    fetchMock.mockRejectedValueOnce(new Error("network down"));
    await expect(
      acknowledgeMobileV2HumanValidationRender({
        accessToken: "token-123",
        surface: "feed",
        readMetadata: {
          route: "feed",
          deliveryMode: "v2",
          capabilitiesVersion: "2026-03-26.09j",
          rolloutBucket: 12,
          usageMode: "organic_validation",
          validationSessionId: "orgv_human654321",
          operatorRunId: "oprv_human654321",
        },
        targetIds: [31],
      }),
    ).resolves.toBe(false);
  });
});
