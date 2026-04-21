jest.mock("./observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

import {
  __resetMobileV2CapabilitiesCacheForTests,
  buildMobileV2FallbackHeaders,
  invalidateMobileV2CapabilitiesCache,
  MOBILE_V2_CAPABILITIES_EMERGENCY_TTL_MS,
  MOBILE_V2_CAPABILITIES_TTL_MS,
  parseMobileV2Capabilities,
  resolveMobileV2RouteDecision,
} from "./mobileV2Rollout";

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

function payloadCapabilities(overrides?: Record<string, unknown>) {
  return {
    ok: true,
    contract_name: "MobileInspectorCapabilitiesV2",
    contract_version: "v2",
    capabilities_version: "2026-03-25.09c",
    mobile_v2_reads_enabled: true,
    mobile_v2_feed_enabled: true,
    mobile_v2_thread_enabled: true,
    tenant_allowed: true,
    cohort_allowed: false,
    reason: "tenant_allowlisted",
    rollout_reason: "tenant_allowlisted",
    source: "tenant_allowlist",
    feed_reason: "tenant_allowlisted",
    feed_source: "tenant_allowlist",
    thread_reason: "tenant_allowlisted",
    thread_source: "tenant_allowlist",
    rollout_bucket: 12,
    rollout_state: "pilot_enabled",
    feed_rollout_state: "pilot_enabled",
    thread_rollout_state: "pilot_enabled",
    feed_candidate_for_promotion: false,
    thread_candidate_for_promotion: false,
    feed_promoted: false,
    thread_promoted: false,
    feed_hold: false,
    thread_hold: false,
    feed_rollback_forced: false,
    thread_rollback_forced: false,
    operator_validation_run_active: false,
    operator_validation_run_id: null,
    operator_validation_required_surfaces: [],
    ...(overrides || {}),
  };
}

describe("mobileV2Rollout", () => {
  const fetchMock = jest.fn();
  const envOriginal = { ...process.env };
  let dateNowSpy: jest.SpyInstance<number, []> | null = null;

  beforeEach(() => {
    fetchMock.mockReset();
    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      value: fetchMock,
    });
    process.env = { ...envOriginal };
    process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED = "1";
    __resetMobileV2CapabilitiesCacheForTests();
    dateNowSpy = jest.spyOn(Date, "now").mockReturnValue(1_000);
  });

  afterEach(() => {
    dateNowSpy?.mockRestore();
    dateNowSpy = null;
  });

  afterAll(() => {
    process.env = envOriginal;
    __resetMobileV2CapabilitiesCacheForTests();
  });

  it("parseia o contrato de capabilities do mobile V2", () => {
    expect(parseMobileV2Capabilities(payloadCapabilities())).toMatchObject({
      capabilities_version: "2026-03-25.09c",
      mobile_v2_reads_enabled: true,
      mobile_v2_feed_enabled: true,
      mobile_v2_thread_enabled: true,
      tenant_allowed: true,
      rollout_bucket: 12,
      rollout_state: "pilot_enabled",
      feed_rollout_state: "pilot_enabled",
      thread_rollout_state: "pilot_enabled",
      operator_validation_run_active: false,
      operator_validation_run_id: null,
    });
  });

  it("aceita a decisao arquitetural canonica publicada pelo backend", () => {
    expect(
      parseMobileV2Capabilities(
        payloadCapabilities({
          mobile_v2_architecture_status: "closed_with_guardrails",
          mobile_v2_architecture_reason:
            "all_required_surfaces_promoted_and_healthy",
          mobile_v2_legacy_fallback_policy: "guardrail_only",
          mobile_v2_transition_active: false,
        }),
      ),
    ).toMatchObject({
      mobile_v2_architecture_status: "closed_with_guardrails",
      mobile_v2_architecture_reason:
        "all_required_surfaces_promoted_and_healthy",
      mobile_v2_legacy_fallback_policy: "guardrail_only",
      mobile_v2_transition_active: false,
    });
  });

  it("preserva o sinal discreto de operator run vindo do gate remoto", () => {
    expect(
      parseMobileV2Capabilities(
        payloadCapabilities({
          operator_validation_run_active: true,
          operator_validation_run_id: "oprv_demo123",
          operator_validation_required_surfaces: ["feed", "thread"],
        }),
      ),
    ).toMatchObject({
      operator_validation_run_active: true,
      operator_validation_run_id: "oprv_demo123",
      operator_validation_required_surfaces: ["feed", "thread"],
    });
  });

  it("derruba para legado quando o gate remoto desliga a rota da thread", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify(
          payloadCapabilities({
            mobile_v2_thread_enabled: false,
            thread_reason: "thread_route_disabled",
            thread_source: "route_flag",
          }),
        ),
      ),
    );

    await expect(
      resolveMobileV2RouteDecision("token-123", "thread"),
    ).resolves.toMatchObject({
      shouldUseV2: false,
      reason: "thread_route_disabled",
      source: "route_flag",
      fallbackReason: "route_disabled",
    });
  });

  it("respeita hold explicito por superficie mesmo com boolean legado inconsistente", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify(
          payloadCapabilities({
            mobile_v2_feed_enabled: true,
            feed_reason: "hold",
            feed_rollout_state: "hold",
            feed_hold: true,
          }),
        ),
      ),
    );

    await expect(
      resolveMobileV2RouteDecision("token-123", "feed"),
    ).resolves.toMatchObject({
      shouldUseV2: false,
      reason: "hold",
      fallbackReason: "hold",
    });
  });

  it("preserva legacy_only explicito quando o rollout inteiro volta ao legado", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify(
          payloadCapabilities({
            mobile_v2_reads_enabled: false,
            mobile_v2_feed_enabled: false,
            mobile_v2_thread_enabled: false,
            reason: "legacy_only",
            rollout_reason: "legacy_only",
            rollout_state: "legacy_only",
            feed_reason: "legacy_only",
            feed_rollout_state: "legacy_only",
            thread_reason: "legacy_only",
            thread_rollout_state: "legacy_only",
          }),
        ),
      ),
    );

    await expect(
      resolveMobileV2RouteDecision("token-legacy", "feed"),
    ).resolves.toMatchObject({
      shouldUseV2: false,
      reason: "legacy_only",
      fallbackReason: "legacy_only",
    });
  });

  it("aceita candidate_for_promotion sem quebrar o fluxo do app", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify(
          payloadCapabilities({
            feed_rollout_state: "candidate_for_promotion",
            feed_candidate_for_promotion: true,
          }),
        ),
      ),
    );

    await expect(
      resolveMobileV2RouteDecision("token-123", "feed"),
    ).resolves.toMatchObject({
      shouldUseV2: true,
      capabilities: expect.objectContaining({
        feed_rollout_state: "candidate_for_promotion",
        feed_candidate_for_promotion: true,
      }),
    });
  });

  it("derruba para legado quando o gate remoto falha", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(JSON.stringify({ detail: "indisponivel" }), {
        status: 503,
      }),
    );

    await expect(
      resolveMobileV2RouteDecision("token-123", "feed"),
    ).resolves.toMatchObject({
      shouldUseV2: false,
      reason: "remote_gate_error",
      source: "http_error",
      fallbackReason: "capabilities_fetch_error",
    });
  });

  it("mantem cache curto com TTL explicito e refaz o gate apos expirar", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(criarResposta(JSON.stringify(payloadCapabilities()))),
    );

    await resolveMobileV2RouteDecision("token-ttl", "feed");
    expect(fetchMock).toHaveBeenCalledTimes(1);

    dateNowSpy?.mockReturnValue(1_000 + MOBILE_V2_CAPABILITIES_TTL_MS - 10);
    await resolveMobileV2RouteDecision("token-ttl", "thread");
    expect(fetchMock).toHaveBeenCalledTimes(1);

    dateNowSpy?.mockReturnValue(1_000 + MOBILE_V2_CAPABILITIES_TTL_MS + 10);
    await resolveMobileV2RouteDecision("token-ttl", "feed");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("encurta o cache quando backend devolve hold ou rollback_forced", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(
        criarResposta(
          JSON.stringify(
            payloadCapabilities({
              mobile_v2_feed_enabled: false,
              feed_reason: "rollback_forced",
              feed_rollout_state: "rollback_forced",
              feed_rollback_forced: true,
              rollout_state: "hold",
            }),
          ),
        ),
      ),
    );

    await resolveMobileV2RouteDecision("token-emergency", "feed");
    expect(fetchMock).toHaveBeenCalledTimes(1);

    dateNowSpy?.mockReturnValue(
      1_000 + MOBILE_V2_CAPABILITIES_EMERGENCY_TTL_MS - 10,
    );
    await resolveMobileV2RouteDecision("token-emergency", "feed");
    expect(fetchMock).toHaveBeenCalledTimes(1);

    dateNowSpy?.mockReturnValue(
      1_000 + MOBILE_V2_CAPABILITIES_EMERGENCY_TTL_MS + 10,
    );
    await resolveMobileV2RouteDecision("token-emergency", "feed");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("permite invalidacao previsivel do cache por sessao", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(criarResposta(JSON.stringify(payloadCapabilities()))),
    );

    await resolveMobileV2RouteDecision("token-session", "feed");
    expect(fetchMock).toHaveBeenCalledTimes(1);

    invalidateMobileV2CapabilitiesCache("token-session");
    await resolveMobileV2RouteDecision("token-session", "feed");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("monta headers discretos para observabilidade do fallback", () => {
    expect(
      buildMobileV2FallbackHeaders({
        route: "feed",
        reason: "rollout_denied",
        source: "cohort bucket#42",
        capabilitiesVersion: "2026-03-25.09c",
        rolloutBucket: 42,
      }),
    ).toEqual({
      "x-tariel-mobile-v2-attempted": "1",
      "x-tariel-mobile-v2-route": "feed",
      "x-tariel-mobile-v2-capabilities-version": "2026-03-25.09c",
      "x-tariel-mobile-v2-rollout-bucket": "42",
      "x-tariel-mobile-v2-fallback-reason": "rollout_denied",
      "x-tariel-mobile-v2-gate-source": "cohort_bucket_42",
    });
  });
});
