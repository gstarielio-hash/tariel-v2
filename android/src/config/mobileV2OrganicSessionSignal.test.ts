jest.mock("./observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

import {
  buildMobileV2AttemptHeaders,
  buildMobileV2FallbackHeaders,
  parseMobileV2Capabilities,
  resolveMobileV2OrganicValidationMetadata,
} from "./mobileV2Rollout";

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
    thread_rollout_state: "promoted",
    feed_candidate_for_promotion: false,
    thread_candidate_for_promotion: false,
    feed_promoted: true,
    thread_promoted: true,
    feed_hold: false,
    thread_hold: false,
    feed_rollback_forced: false,
    thread_rollback_forced: false,
    organic_validation_active: true,
    organic_validation_session_id: "orgv_abcd1234ef56",
    organic_validation_surfaces: ["feed", "thread"],
    organic_validation_target_suggestions: [
      {
        surface: "feed",
        suggested_target_ids: [101],
        covered_target_ids: [],
        missing_target_ids: [101],
        distinct_targets_observed: 0,
        coverage_met: false,
        targets_available: true,
        detail: "targets_suggested",
      },
      {
        surface: "thread",
        suggested_target_ids: [202],
        covered_target_ids: [],
        missing_target_ids: [202],
        distinct_targets_observed: 0,
        coverage_met: false,
        targets_available: true,
        detail: "targets_suggested",
      },
    ],
    organic_validation_surface_coverage: [],
    organic_validation_has_partial_coverage: false,
    organic_validation_targets_ready: true,
    ...(overrides || {}),
  };
}

describe("mobileV2OrganicSessionSignal", () => {
  it("parseia a sessao organica ativa vinda do gate remoto", () => {
    expect(parseMobileV2Capabilities(payloadCapabilities())).toMatchObject({
      organic_validation_active: true,
      organic_validation_session_id: "orgv_abcd1234ef56",
      organic_validation_surfaces: ["feed", "thread"],
      organic_validation_targets_ready: true,
      organic_validation_target_suggestions: [
        expect.objectContaining({
          surface: "feed",
          suggested_target_ids: [101],
        }),
        expect.objectContaining({
          surface: "thread",
          suggested_target_ids: [202],
        }),
      ],
    });
  });

  it("resolve metadados e headers da sessao organica so para a superficie ativa", () => {
    const capabilities = parseMobileV2Capabilities(
      payloadCapabilities({
        organic_validation_surfaces: ["thread"],
      }),
    );

    const threadMetadata = resolveMobileV2OrganicValidationMetadata(
      "thread",
      capabilities,
    );
    const feedMetadata = resolveMobileV2OrganicValidationMetadata(
      "feed",
      capabilities,
    );

    expect(threadMetadata).toEqual({
      usageMode: "organic_validation",
      validationSessionId: "orgv_abcd1234ef56",
    });
    expect(feedMetadata).toBeNull();

    const attemptHeaders = new Headers(
      buildMobileV2AttemptHeaders({
        route: "thread",
        capabilitiesVersion: capabilities.capabilities_version,
        rolloutBucket: capabilities.rollout_bucket,
        usageMode: threadMetadata?.usageMode ?? null,
        validationSessionId: threadMetadata?.validationSessionId ?? null,
      }),
    );
    expect(attemptHeaders.get("X-Tariel-Mobile-Usage-Mode")).toBe(
      "organic_validation",
    );
    expect(attemptHeaders.get("X-Tariel-Mobile-Validation-Session")).toBe(
      "orgv_abcd1234ef56",
    );

    const fallbackHeaders = new Headers(
      buildMobileV2FallbackHeaders({
        route: "thread",
        reason: "http_404",
        source: "v2_read",
        capabilitiesVersion: capabilities.capabilities_version,
        rolloutBucket: capabilities.rollout_bucket,
        usageMode: threadMetadata?.usageMode ?? null,
        validationSessionId: threadMetadata?.validationSessionId ?? null,
      }),
    );
    expect(fallbackHeaders.get("X-Tariel-Mobile-Usage-Mode")).toBe(
      "organic_validation",
    );
    expect(fallbackHeaders.get("X-Tariel-Mobile-Validation-Session")).toBe(
      "orgv_abcd1234ef56",
    );
  });

  it("nao emite metadados quando a sessao organica nao esta ativa", () => {
    const capabilities = parseMobileV2Capabilities(
      payloadCapabilities({
        organic_validation_active: false,
        organic_validation_session_id: null,
        organic_validation_surfaces: [],
      }),
    );

    expect(
      resolveMobileV2OrganicValidationMetadata("feed", capabilities),
    ).toBeNull();
    expect(
      buildMobileV2AttemptHeaders({
        route: "feed",
        capabilitiesVersion: capabilities.capabilities_version,
        rolloutBucket: capabilities.rollout_bucket,
      }),
    ).toEqual({
      "X-Tariel-Mobile-V2-Attempted": "1",
      "X-Tariel-Mobile-V2-Route": "feed",
      "X-Tariel-Mobile-V2-Capabilities-Version": "2026-03-25.09e",
      "X-Tariel-Mobile-V2-Rollout-Bucket": "12",
    });
  });
});
