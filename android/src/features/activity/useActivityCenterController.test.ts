jest.mock("./monitorActivityFlow", () => ({
  runMonitorActivityFlow: jest.fn(),
}));

jest.mock("../chat/network", () => ({
  canSyncOnCurrentNetwork: jest.fn(),
}));

jest.mock("../../config/api", () => ({
  pingApi: jest.fn(),
}));

jest.mock("../chat/notifications", () => ({
  initializeNotificationsRuntime: jest.fn(),
  scheduleLocalActivityNotification: jest.fn(),
  syncNotificationChannels: jest.fn(),
}));

jest.mock("../../config/observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

import { act, renderHook, waitFor } from "@testing-library/react-native";

import { canSyncOnCurrentNetwork } from "../chat/network";
import { runMonitorActivityFlow } from "./monitorActivityFlow";
import { useActivityCenterController } from "./useActivityCenterController";

function createParams(
  overrides: Partial<Parameters<typeof useActivityCenterController>[0]> = {},
): Parameters<typeof useActivityCenterController>[0] {
  return {
    session: {
      accessToken: "token-123",
      bootstrap: {
        ok: true,
        app: {
          nome: "Tariel Inspetor",
          portal: "inspetor",
          api_base_url: "http://127.0.0.1:8000",
          suporte_whatsapp: "",
        },
        usuario: {
          id: 7,
          nome_completo: "Inspetor Demo",
          email: "inspetor@empresa-a.test",
          telefone: "",
          foto_perfil_url: "",
          empresa_nome: "Empresa Demo (DEV)",
          empresa_id: 1,
          nivel_acesso: 5,
        },
      },
    },
    sessionLoading: false,
    statusApi: "online",
    wifiOnlySync: false,
    syncEnabled: false,
    activeThread: "chat",
    conversation: {
      laudoId: 80,
      laudoCard: {
        id: 80,
        titulo: "Laudo 80",
        preview: "Preview 80",
        pinado: false,
        data_iso: "2026-03-26T18:00:00.000Z",
        data_br: "26/03/2026",
        hora_br: "18:00",
        tipo_template: "padrao",
        status_card: "aguardando",
        status_revisao: "aguardando",
        status_card_label: "Aguardando",
        permite_edicao: true,
        permite_reabrir: false,
        possui_historico: true,
      },
    },
    laudosDisponiveis: [],
    laudoMesaCarregado: null,
    messagesMesa: [],
    monitorIntervalMs: 30000,
    notifications: [],
    notificationSettings: {
      pushEnabled: true,
      responseAlertsEnabled: true,
      soundEnabled: true,
      vibrationEnabled: true,
      emailEnabled: false,
      soundPreset: "Ping",
      showMessageContent: true,
      hideContentOnLockScreen: false,
      onlyShowNewMessage: false,
      chatCategoryEnabled: true,
      mesaCategoryEnabled: true,
      systemCategoryEnabled: true,
      criticalAlertsEnabled: true,
    } as Parameters<
      typeof useActivityCenterController
    >[0]["notificationSettings"],
    notificationsPermissionGranted: true,
    setNotifications: jest.fn(),
    setActivityCenterVisible: jest.fn(),
    openLaudoById: jest.fn(),
    setActiveThread: jest.fn(),
    carregarMesaAtual: jest.fn(),
    onRecoverOnline: jest.fn(),
    saveNotificationsLocally: jest.fn(),
    assinaturaStatusLaudo: (item) => `${item.id}:${item.status_card}`,
    assinaturaMensagemMesa: (item) => `${item.id}:${item.resolvida_em || ""}`,
    selecionarLaudosParaMonitoramentoMesa: () => [80],
    criarNotificacaoStatusLaudo: (item) => ({
      id: `status:${item.id}`,
      kind: "status",
      laudoId: item.id,
      title: item.titulo,
      body: item.status_card_label,
      createdAt: "2026-03-26T18:00:00.000Z",
      unread: true,
      targetThread: "chat",
    }),
    criarNotificacaoMesa: (kind, item, tituloLaudo) => ({
      id: `${kind}:${item.id}`,
      kind,
      laudoId: item.laudo_id,
      title: tituloLaudo,
      body: item.texto,
      createdAt: "2026-03-26T18:00:00.000Z",
      unread: true,
      targetThread: "mesa",
    }),
    erroSugereModoOffline: jest.fn().mockReturnValue(false),
    chaveCacheLaudo: (laudoId) => String(laudoId || ""),
    onUpdateCurrentConversationSummary: jest.fn(),
    onSetLaudosDisponiveis: jest.fn(),
    onSetCacheLaudos: jest.fn(),
    onSetErroLaudos: jest.fn(),
    onSetMensagensMesa: jest.fn(),
    onSetLaudoMesaCarregado: jest.fn(),
    onSetCacheMesa: jest.fn(),
    onSetStatusApi: jest.fn(),
    onSetErroConversaIfEmpty: jest.fn(),
    onObserveMesaFeedReadMetadata: jest.fn(),
    onObserveMesaFeedRequestedTargetIds: jest.fn(),
    maxNotifications: 10,
    ...overrides,
  };
}

describe("useActivityCenterController", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (canSyncOnCurrentNetwork as jest.Mock).mockResolvedValue(true);
    (runMonitorActivityFlow as jest.Mock).mockResolvedValue({
      requestDispatched: false,
      requestedTargetIds: [],
      feedReadMetadata: null,
      feedRequestTrace: null,
      generatedNotificationsCount: 0,
      errorMessage: null,
      skipReason: null,
    });
  });

  it("dispara um ciclo de monitoramento logo ao abrir a central de atividade", async () => {
    const params = createParams();
    const { result } = renderHook(() => useActivityCenterController(params));

    act(() => {
      result.current.actions.handleAbrirCentralAtividade();
    });

    expect(result.current.state.activityCenterDiagnostics.phase).toBe(
      "loading",
    );
    await waitFor(() => {
      expect(runMonitorActivityFlow).toHaveBeenCalledTimes(1);
    });
    expect(params.setActivityCenterVisible).toHaveBeenCalledWith(true);
    expect(runMonitorActivityFlow).toHaveBeenCalledWith(
      expect.objectContaining({
        accessToken: "token-123",
        onObserveMesaFeedRequestedTargetIds:
          params.onObserveMesaFeedRequestedTargetIds,
      }),
    );
  });

  it("materializa o diagnostico terminal da central com targets pedidos e metadata", async () => {
    (runMonitorActivityFlow as jest.Mock).mockResolvedValue({
      requestDispatched: true,
      requestedTargetIds: [80],
      feedReadMetadata: {
        route: "feed",
        deliveryMode: "v2",
        capabilitiesVersion: "2026-03-26.09n",
        rolloutBucket: 12,
        usageMode: "organic_validation",
        validationSessionId: "orgv_09n",
        operatorRunId: "oprv_09n",
      },
      feedRequestTrace: {
        traceId: "feed-trace-80",
        surface: "feed",
        method: "GET",
        contractFlagEnabled: true,
        routeDecision: "v2",
        actualRoute: "v2",
        attemptSequence: ["v2"],
        endpointPath: "/app/api/mobile/v2/mesa/feed?laudo_ids=80",
        phase: "response_received",
        targetIds: [80],
        validationSessionId: "orgv_09n",
        operatorRunId: "oprv_09n",
        usageMode: "organic_validation",
        responseStatus: 200,
        backendRequestId: "cid-80",
        failureKind: null,
        failureDetail: null,
        fallbackReason: null,
        deliveryMode: "v2",
      },
      generatedNotificationsCount: 0,
      errorMessage: null,
      skipReason: null,
    });
    const params = createParams();
    const { result } = renderHook(() => useActivityCenterController(params));

    act(() => {
      result.current.actions.handleAbrirCentralAtividade();
    });

    await waitFor(() => {
      expect(result.current.state.activityCenterDiagnostics.phase).toBe(
        "settled",
      );
    });
    expect(result.current.state.activityCenterDiagnostics).toMatchObject({
      requestDispatched: true,
      requestedTargetIds: [80],
      lastError: null,
      lastSkipReason: null,
      lastReadMetadata: expect.objectContaining({
        deliveryMode: "v2",
        route: "feed",
      }),
      lastRequestTrace: expect.objectContaining({
        traceId: "feed-trace-80",
        actualRoute: "v2",
      }),
    });
  });

  it("expõe o motivo do terminal sem request quando nao ha alvo elegivel", async () => {
    (runMonitorActivityFlow as jest.Mock).mockResolvedValue({
      requestDispatched: false,
      requestedTargetIds: [],
      feedReadMetadata: null,
      feedRequestTrace: null,
      generatedNotificationsCount: 0,
      errorMessage: null,
      skipReason: "no_target",
    });
    const params = createParams();
    const { result } = renderHook(() => useActivityCenterController(params));

    act(() => {
      result.current.actions.handleAbrirCentralAtividade();
    });

    await waitFor(() => {
      expect(result.current.state.activityCenterDiagnostics.phase).toBe(
        "settled",
      );
    });
    expect(result.current.state.activityCenterDiagnostics).toMatchObject({
      requestDispatched: false,
      requestedTargetIds: [],
      lastSkipReason: "no_target",
    });
  });

  it("semeia alerta crítico quando um laudo já chega com reemissão recomendada", async () => {
    const params = createParams({
      laudosDisponiveis: [
        {
          id: 91,
          titulo: "Laudo 91",
          preview: "PDF emitido divergente",
          pinado: false,
          data_iso: "2026-03-26T18:00:00.000Z",
          data_br: "26/03/2026",
          hora_br: "18:00",
          tipo_template: "nr35",
          status_card: "emitido",
          status_revisao: "aprovado",
          status_card_label: "Emitido",
          permite_edicao: false,
          permite_reabrir: true,
          possui_historico: true,
          official_issue_summary: {
            label: "Reemissão recomendada",
            detail: "PDF emitido divergente · Emitido v0003 · Atual v0004",
            primary_pdf_diverged: true,
            issue_number: "EO-91",
            primary_pdf_storage_version: "v0003",
            current_primary_pdf_storage_version: "v0004",
          },
        },
      ],
      criarNotificacaoStatusLaudo: (item) => ({
        id: `status:${item.id}:critical`,
        kind: "alerta_critico",
        laudoId: item.id,
        title: "Reemissão recomendada",
        body: item.titulo,
        createdAt: "2026-03-26T18:00:00.000Z",
        unread: true,
        targetThread: "finalizar",
      }),
    });

    renderHook(() => useActivityCenterController(params));

    await waitFor(() => {
      expect(params.setNotifications).toHaveBeenCalled();
    });
    const updater = (params.setNotifications as jest.Mock).mock
      .calls[0]?.[0] as (
      current: Array<Record<string, unknown>>,
    ) => Array<Record<string, unknown>>;
    expect(
      updater([]).map((item) => ({
        id: item.id,
        kind: item.kind,
        targetThread: item.targetThread,
      })),
    ).toEqual([
      {
        id: "status:91:critical",
        kind: "alerta_critico",
        targetThread: "finalizar",
      },
    ]);
  });
});
