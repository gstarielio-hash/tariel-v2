import {
  appendMobilePilotRequestAttempt,
  buildMobilePilotRequestTraceSummary,
  classifyMobilePilotRequestFailure,
  updateMobilePilotRequestTraceSummary,
} from "./mobilePilotRequestTrace";

describe("mobilePilotRequestTrace", () => {
  it("cria um resumo canônico do trace da central", () => {
    const trace = buildMobilePilotRequestTraceSummary({
      surface: "feed",
      contractFlagEnabled: true,
      routeDecision: "v2",
      targetIds: [80, 80, 21],
      validationSessionId: "orgv_09q",
      operatorRunId: "oprv_09q",
      usageMode: "organic_validation",
      traceId: "feed-trace-80",
    });

    expect(trace).toMatchObject({
      traceId: "feed-trace-80",
      surface: "feed",
      contractFlagEnabled: true,
      routeDecision: "v2",
      actualRoute: "unknown",
      phase: "intent_created",
      targetIds: [80, 21],
      validationSessionId: "orgv_09q",
      operatorRunId: "oprv_09q",
      usageMode: "organic_validation",
      deliveryMode: null,
    });
  });

  it("acumula tentativas e atualiza status final do request", () => {
    const created = buildMobilePilotRequestTraceSummary({
      surface: "feed",
      contractFlagEnabled: true,
      routeDecision: "v2",
      targetIds: [80],
      traceId: "feed-trace-80",
    });
    const attempted = appendMobilePilotRequestAttempt(created, "v2");
    const updated = updateMobilePilotRequestTraceSummary(attempted, {
      phase: "response_received",
      responseStatus: 200,
      endpointPath: "/app/api/mobile/v2/mesa/feed?laudo_ids=80",
      backendRequestId: "cid-80",
      deliveryMode: "v2",
    });

    expect(updated).toMatchObject({
      actualRoute: "v2",
      attemptSequence: ["v2"],
      phase: "response_received",
      responseStatus: 200,
      backendRequestId: "cid-80",
      deliveryMode: "v2",
    });
  });

  it("classifica cancelamento e falha de rede de forma estável", () => {
    const abortError = new Error("The user aborted");
    abortError.name = "AbortError";

    expect(classifyMobilePilotRequestFailure(abortError)).toMatchObject({
      phase: "request_cancelled",
      failureKind: "cancelled",
    });

    expect(
      classifyMobilePilotRequestFailure(new Error("Network request failed")),
    ).toMatchObject({
      phase: "request_failed",
      failureKind: "request_failed",
    });
  });
});
