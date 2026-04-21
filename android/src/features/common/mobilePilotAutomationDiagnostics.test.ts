import {
  buildActivityCenterAutomationMarkerIds,
  buildActivityCenterAutomationProbeLabel,
  buildPilotAutomationMarkerIds,
  buildPilotAutomationProbeLabel,
  recordHistorySelectionCallbackCompleted,
  recordHistorySelectionTap,
  resolveActivityCenterAutomationTerminalState,
  syncHistorySelectionWithShell,
} from "./mobilePilotAutomationDiagnostics";

const emptyHistorySelection = {
  targetTappedId: null,
  callbackFiredId: null,
  callbackCompletedId: null,
  selectionLostId: null,
} as const;

describe("mobilePilotAutomationDiagnostics", () => {
  it("expõe marker inequívoco quando um laudo foi realmente selecionado", () => {
    const ids = buildPilotAutomationMarkerIds({
      selectedHistoryItemId: 80,
      historySelection: {
        targetTappedId: 80,
        callbackFiredId: 80,
        callbackCompletedId: 80,
        selectionLostId: null,
      },
      activityCenter: {
        modalVisible: false,
        phase: "idle",
        requestDispatched: false,
        requestedTargetIds: [],
        notificationCount: 0,
        feedReadMetadata: null,
        requestTrace: null,
        skipReason: null,
      },
    });

    expect(ids).toContain("selected-history-item-marker");
    expect(ids).toContain("selected-history-item-id-80");
    expect(ids).toContain("history-target-tapped-80");
    expect(ids).toContain("history-selection-callback-fired-80");
    expect(ids).toContain("history-selection-callback-completed-80");
    expect(ids).toContain("authenticated-shell-selected-laudo-id-80");
    expect(ids).toContain("authenticated-shell-selection-ready-80");
    expect(ids).not.toContain("selected-history-item-none");
  });

  it("expõe estado terminal vazio da central quando nenhum request elegível saiu", () => {
    const ids = buildPilotAutomationMarkerIds({
      selectedHistoryItemId: null,
      historySelection: emptyHistorySelection,
      activityCenter: {
        modalVisible: true,
        phase: "settled",
        requestDispatched: false,
        requestedTargetIds: [],
        notificationCount: 0,
        feedReadMetadata: null,
        requestTrace: null,
        skipReason: "no_target",
      },
    });

    expect(ids).toContain("activity-center-open");
    expect(ids).toContain("activity-center-request-not-started");
    expect(ids).toContain("activity-center-terminal-state");
    expect(ids).toContain("activity-center-terminal-state-no-request");
    expect(ids).toContain("activity-center-state-no-request");
    expect(ids).toContain("activity-center-skip-no-target");
  });

  it("expõe markers V2 da central com targets monitorados", () => {
    const ids = buildPilotAutomationMarkerIds({
      selectedHistoryItemId: 80,
      historySelection: {
        targetTappedId: 80,
        callbackFiredId: 80,
        callbackCompletedId: 80,
        selectionLostId: null,
      },
      activityCenter: {
        modalVisible: true,
        phase: "settled",
        requestDispatched: true,
        requestedTargetIds: [80, 80],
        notificationCount: 1,
        feedReadMetadata: {
          route: "feed",
          deliveryMode: "v2",
          capabilitiesVersion: "2026-03-26.09n",
          rolloutBucket: 12,
          usageMode: "organic_validation",
          validationSessionId: "orgv_09n",
          operatorRunId: "oprv_09n",
        },
        requestTrace: null,
        skipReason: null,
      },
    });

    expect(ids).toContain("activity-center-request-dispatched");
    expect(ids).toContain("activity-center-request-target-80");
    expect(ids).toContain("activity-center-state-loaded");
    expect(ids).toContain("activity-center-state-loaded-v2");
    expect(ids).toContain("activity-center-terminal-state-loaded-v2");
    expect(ids).toContain("activity-center-feed-v2-served");
    expect(ids).toContain("activity-center-feed-v2-ready");
    expect(ids).toContain("activity-center-feed-v2-target-80");
  });

  it("marca explicitamente quando a seleção foi perdida após atualização do shell", () => {
    const ids = buildPilotAutomationMarkerIds({
      selectedHistoryItemId: null,
      historySelection: {
        targetTappedId: 80,
        callbackFiredId: 80,
        callbackCompletedId: 80,
        selectionLostId: 80,
      },
      activityCenter: {
        modalVisible: false,
        phase: "idle",
        requestDispatched: false,
        requestedTargetIds: [],
        notificationCount: 0,
        feedReadMetadata: null,
        requestTrace: null,
        skipReason: null,
      },
    });

    expect(ids).toContain("history-selection-callback-fired-80");
    expect(ids).toContain("history-selection-callback-completed-80");
    expect(ids).toContain("authenticated-shell-selection-lost-80");
  });

  it("gera um resumo parseável do probe de seleção", () => {
    const label = buildPilotAutomationProbeLabel({
      selectedHistoryItemId: 80,
      historySelection: {
        targetTappedId: 80,
        callbackFiredId: 80,
        callbackCompletedId: 80,
        selectionLostId: null,
      },
      activityCenter: {
        modalVisible: false,
        phase: "idle",
        requestDispatched: false,
        requestedTargetIds: [],
        notificationCount: 0,
        feedReadMetadata: null,
        requestTrace: null,
        skipReason: null,
      },
      runtimeFlag: {
        enabled: true,
        rawValue: "1",
        source: "expo_public_env",
      },
    });

    expect(label).toContain("pilot_selection_probe");
    expect(label).toContain("target_tapped=80");
    expect(label).toContain("callback_fired=80");
    expect(label).toContain("callback_completed=80");
    expect(label).toContain("selected_laudo_id=80");
    expect(label).toContain("selection_ready=80");
    expect(label).toContain("runtime_flag_enabled=true");
    expect(label).toContain("runtime_flag_raw_value=1");
    expect(label).toContain("runtime_flag_source=expo_public_env");
    expect(label).toContain("activity_center_terminal_state=none");
  });

  it("atualiza o diagnóstico quando o callback do histórico dispara e completa", () => {
    const tapped = recordHistorySelectionTap(
      {
        targetTappedId: null,
        callbackFiredId: null,
        callbackCompletedId: null,
        selectionLostId: 80,
      },
      80,
    );
    const completed = recordHistorySelectionCallbackCompleted(tapped, 80);

    expect(tapped.targetTappedId).toBe(80);
    expect(tapped.callbackFiredId).toBe(80);
    expect(tapped.selectionLostId).toBeNull();
    expect(completed.callbackCompletedId).toBe(80);
  });

  it("marca perda quando o shell deixa de expor o laudo confirmado", () => {
    const synced = syncHistorySelectionWithShell({
      current: {
        targetTappedId: 80,
        callbackFiredId: 80,
        callbackCompletedId: 80,
        selectionLostId: null,
      },
      selectedHistoryItemId: null,
      previousSelectedHistoryItemId: 80,
    });

    expect(synced.selectionLostId).toBe(80);
  });

  it("resolve terminal state vazio quando houve request sem itens", () => {
    const terminalState = resolveActivityCenterAutomationTerminalState({
      modalVisible: true,
      phase: "settled",
      requestDispatched: true,
      requestedTargetIds: [80],
      notificationCount: 0,
      feedReadMetadata: {
        route: "feed",
        deliveryMode: "v2",
        capabilitiesVersion: "2026-03-26.09p",
        rolloutBucket: 12,
        usageMode: "organic_validation",
        validationSessionId: "orgv_09p",
      },
      requestTrace: null,
      skipReason: null,
    });

    expect(terminalState).toBe("empty");
  });

  it("gera probe canonico da central com terminal vazio e request v2", () => {
    const ids = buildActivityCenterAutomationMarkerIds({
      modalVisible: true,
      phase: "settled",
      requestDispatched: true,
      requestedTargetIds: [80, 80],
      notificationCount: 0,
      feedReadMetadata: {
        route: "feed",
        deliveryMode: "v2",
        capabilitiesVersion: "2026-03-26.09p",
        rolloutBucket: 12,
        usageMode: "organic_validation",
        validationSessionId: "orgv_09p",
      },
      requestTrace: null,
      skipReason: null,
    });
    const label = buildActivityCenterAutomationProbeLabel({
      modalVisible: true,
      phase: "settled",
      requestDispatched: true,
      requestedTargetIds: [80, 80],
      notificationCount: 0,
      feedReadMetadata: {
        route: "feed",
        deliveryMode: "v2",
        capabilitiesVersion: "2026-03-26.09p",
        rolloutBucket: 12,
        usageMode: "organic_validation",
        validationSessionId: "orgv_09p",
      },
      requestTrace: null,
      skipReason: null,
    });

    expect(ids).toContain("activity-center-terminal-state-empty");
    expect(ids).toContain("activity-center-request-dispatched");
    expect(ids).toContain("activity-center-request-target-80");
    expect(ids).toContain("activity-center-feed-v2-served");
    expect(label).toContain("pilot_activity_center_probe");
    expect(label).toContain("terminal_state=empty");
    expect(label).toContain("delivery=v2");
    expect(label).toContain("requested_targets=80");
  });

  it("expõe o trace da central quando a chamada foi criada mas ainda não chegou ao backend", () => {
    const ids = buildActivityCenterAutomationMarkerIds({
      modalVisible: true,
      phase: "settled",
      requestDispatched: true,
      requestedTargetIds: [80],
      notificationCount: 0,
      feedReadMetadata: null,
      requestTrace: {
        traceId: "feed-trace-80",
        surface: "feed",
        method: "GET",
        contractFlagEnabled: true,
        contractFlagRawValue: "1",
        contractFlagSource: "expo_public_env",
        routeDecision: "v2",
        decisionReason: "enabled",
        decisionSource: "surface_state_override",
        actualRoute: "v2",
        attemptSequence: ["v2"],
        endpointPath: "/app/api/mobile/v2/mesa/feed?laudo_ids=80",
        phase: "request_sent",
        targetIds: [80],
        validationSessionId: "orgv_09q",
        operatorRunId: "oprv_09q",
        usageMode: "organic_validation",
        responseStatus: null,
        backendRequestId: null,
        failureKind: null,
        failureDetail: null,
        fallbackReason: null,
        deliveryMode: null,
      },
      skipReason: null,
    });
    const label = buildActivityCenterAutomationProbeLabel({
      modalVisible: true,
      phase: "settled",
      requestDispatched: true,
      requestedTargetIds: [80],
      notificationCount: 0,
      feedReadMetadata: null,
      requestTrace: {
        traceId: "feed-trace-80",
        surface: "feed",
        method: "GET",
        contractFlagEnabled: true,
        contractFlagRawValue: "1",
        contractFlagSource: "expo_public_env",
        routeDecision: "v2",
        decisionReason: "enabled",
        decisionSource: "surface_state_override",
        actualRoute: "v2",
        attemptSequence: ["v2"],
        endpointPath: "/app/api/mobile/v2/mesa/feed?laudo_ids=80",
        phase: "request_sent",
        targetIds: [80],
        validationSessionId: "orgv_09q",
        operatorRunId: "oprv_09q",
        usageMode: "organic_validation",
        responseStatus: null,
        backendRequestId: null,
        failureKind: null,
        failureDetail: null,
        fallbackReason: null,
        deliveryMode: null,
      },
      skipReason: null,
    });

    expect(ids).toContain("activity-center-request-trace-present");
    expect(ids).toContain("activity-center-request-phase-request-sent");
    expect(ids).toContain("activity-center-request-route-decision-v2");
    expect(ids).toContain("activity-center-request-actual-route-v2");
    expect(ids).toContain("activity-center-request-flag-enabled");
    expect(label).toContain("request_trace_id=feed-trace-80");
    expect(label).toContain("request_phase=request_sent");
    expect(label).toContain("request_flag_raw_value=1");
    expect(label).toContain("request_flag_source=expo_public_env");
    expect(label).toContain("request_route_decision=v2");
    expect(label).toContain("request_decision_reason=enabled");
    expect(label).toContain("request_decision_source=surface_state_override");
    expect(label).toContain("request_actual_route=v2");
  });
});
