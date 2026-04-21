jest.mock("./observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

import {
  __resetMobileV2CapabilitiesCacheForTests,
  MOBILE_V2_CAPABILITIES_PILOT_TTL_MS,
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
    capabilities_version: "2026-03-25.09e",
    mobile_v2_reads_enabled: true,
    mobile_v2_feed_enabled: true,
    mobile_v2_thread_enabled: true,
    tenant_allowed: true,
    cohort_allowed: false,
    reason: "promoted",
    rollout_reason: "promoted",
    source: "tenant_state_override",
    feed_reason: "promoted",
    feed_source: "surface_state_override",
    thread_reason: "promoted",
    thread_source: "surface_state_override",
    rollout_bucket: 12,
    rollout_state: "promoted",
    feed_rollout_state: "promoted",
    thread_rollout_state: "pilot_enabled",
    feed_candidate_for_promotion: false,
    thread_candidate_for_promotion: false,
    feed_promoted: true,
    thread_promoted: false,
    feed_hold: false,
    thread_hold: false,
    feed_rollback_forced: false,
    thread_rollback_forced: false,
    feed_promoted_since: "2026-03-25T22:40:00Z",
    thread_promoted_since: null,
    feed_rollout_window_started_at: "2026-03-25T22:40:00Z",
    thread_rollout_window_started_at: null,
    feed_rollback_window_until: "2026-03-26T22:40:00Z",
    thread_rollback_window_until: null,
    feed_rollback_window_active: true,
    thread_rollback_window_active: false,
    ...(overrides || {}),
  };
}

describe("mobileV2PilotRollout", () => {
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

  it("parseia promoted_since e a janela de rollback do piloto", () => {
    expect(parseMobileV2Capabilities(payloadCapabilities())).toMatchObject({
      feed_promoted_since: "2026-03-25T22:40:00Z",
      feed_rollout_window_started_at: "2026-03-25T22:40:00Z",
      feed_rollback_window_until: "2026-03-26T22:40:00Z",
      feed_rollback_window_active: true,
    });
  });

  it("encurta o cache quando a superficie promovida ainda esta na janela de rollback", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(criarResposta(JSON.stringify(payloadCapabilities()))),
    );

    await resolveMobileV2RouteDecision("token-pilot", "feed");
    expect(fetchMock).toHaveBeenCalledTimes(1);

    dateNowSpy?.mockReturnValue(
      1_000 + MOBILE_V2_CAPABILITIES_PILOT_TTL_MS - 10,
    );
    await resolveMobileV2RouteDecision("token-pilot", "thread");
    expect(fetchMock).toHaveBeenCalledTimes(1);

    dateNowSpy?.mockReturnValue(
      1_000 + MOBILE_V2_CAPABILITIES_PILOT_TTL_MS + 10,
    );
    await resolveMobileV2RouteDecision("token-pilot", "feed");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("derruba para legado quando o piloto promovido entra em hold apos o refresh do gate", async () => {
    fetchMock
      .mockResolvedValueOnce(
        criarResposta(JSON.stringify(payloadCapabilities())),
      )
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify(
            payloadCapabilities({
              mobile_v2_feed_enabled: false,
              feed_reason: "hold",
              feed_source: "surface_state_override",
              feed_rollout_state: "hold",
              feed_promoted: false,
              feed_hold: true,
              feed_rollback_window_active: true,
            }),
          ),
        ),
      );

    await expect(
      resolveMobileV2RouteDecision("token-pilot-hold", "feed"),
    ).resolves.toMatchObject({
      shouldUseV2: true,
      capabilities: expect.objectContaining({
        feed_rollout_state: "promoted",
      }),
    });

    dateNowSpy?.mockReturnValue(
      1_000 + MOBILE_V2_CAPABILITIES_PILOT_TTL_MS + 10,
    );

    await expect(
      resolveMobileV2RouteDecision("token-pilot-hold", "feed"),
    ).resolves.toMatchObject({
      shouldUseV2: false,
      reason: "hold",
      fallbackReason: "hold",
    });
  });
});
