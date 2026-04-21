jest.mock("../../config/api", () => ({
  carregarFeedMesaMobile: jest.fn(),
  carregarLaudosMobile: jest.fn(),
  carregarMensagensMesaMobile: jest.fn(),
}));

jest.mock("../../config/observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

import {
  carregarFeedMesaMobile,
  carregarLaudosMobile,
  carregarMensagensMesaMobile,
} from "../../config/api";
import { attachMobileV2ReadRenderMetadata } from "../../config/mobileV2HumanValidation";
import { runMonitorActivityFlow } from "./monitorActivityFlow";

describe("runMonitorActivityFlow", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("consulta mensagens da mesa apenas para laudos alterados no feed", async () => {
    (carregarLaudosMobile as jest.Mock).mockResolvedValue({
      itens: [
        {
          id: 21,
          titulo: "Laudo 21",
          status_card: "ajustes",
          status_revisao: "rejeitado",
          status_card_label: "Ajustes",
          permite_edicao: false,
          permite_reabrir: true,
        },
        {
          id: 22,
          titulo: "Laudo 22",
          status_card: "aguardando",
          status_revisao: "aguardando",
          status_card_label: "Aguardando",
          permite_edicao: false,
          permite_reabrir: false,
        },
      ],
    });
    (carregarFeedMesaMobile as jest.Mock).mockResolvedValue(
      attachMobileV2ReadRenderMetadata(
        {
          cursor_atual: "2026-03-21T13:00:00Z",
          laudo_ids: [21, 22],
          itens: [{ laudo_id: 22, resumo: { total_mensagens: 4 } }],
        },
        {
          route: "feed",
          deliveryMode: "v2",
          capabilitiesVersion: "2026-03-26.09j",
          rolloutBucket: 12,
          usageMode: "organic_validation",
          validationSessionId: "orgv_monitor123",
        },
      ),
    );
    (carregarMensagensMesaMobile as jest.Mock).mockResolvedValue({
      laudo_id: 22,
      itens: [],
      cursor_proximo: null,
      tem_mais: false,
      estado: "aguardando",
      permite_edicao: false,
      permite_reabrir: false,
      laudo_card: null,
    });

    const mesaFeedCursorRef = { current: "" };
    const onObserveMesaFeedReadMetadata = jest.fn();
    const onObserveMesaFeedRequestedTargetIds = jest.fn();

    const result = await runMonitorActivityFlow({
      accessToken: "token-123",
      monitorandoAtividade: false,
      conversaLaudoId: 21,
      conversaLaudoTitulo: "Laudo 21",
      sessionUserId: 1,
      assinaturaStatusLaudo: (item) => `${item.id}:${item.status_card}`,
      assinaturaMensagemMesa: (item) => `${item.id}:${item.resolvida_em || ""}`,
      selecionarLaudosParaMonitoramentoMesa: () => [21, 22],
      criarNotificacaoStatusLaudo: (item) => ({ id: `status:${item.id}` }),
      criarNotificacaoMesa: (kind, item) => ({ id: `${kind}:${item.id}` }),
      atualizarResumoLaudoAtual: jest.fn(),
      registrarNotificacoes: jest.fn(),
      erroSugereModoOffline: jest.fn().mockReturnValue(false),
      chaveCacheLaudo: (laudoId) => String(laudoId || ""),
      statusSnapshotRef: { current: {} },
      mesaSnapshotRef: {
        current: {
          21: { 1: "1||" },
          22: { 2: "2||" },
        },
      },
      mesaFeedCursorRef,
      onSetMonitorandoAtividade: jest.fn(),
      onSetLaudosDisponiveis: jest.fn(),
      onSetCacheLaudos: jest.fn(),
      onSetErroLaudos: jest.fn(),
      onSetMensagensMesa: jest.fn(),
      onSetLaudoMesaCarregado: jest.fn(),
      onSetCacheMesa: jest.fn(),
      onSetStatusApi: jest.fn(),
      onSetErroConversaIfEmpty: jest.fn(),
      onObserveMesaFeedReadMetadata,
      onObserveMesaFeedRequestedTargetIds,
    });

    expect(carregarFeedMesaMobile).toHaveBeenCalledWith(
      "token-123",
      expect.objectContaining({
        laudoIds: [21, 22],
        cursorAtualizadoEm: null,
        onRequestTrace: expect.any(Function),
      }),
    );
    expect(carregarMensagensMesaMobile).toHaveBeenCalledTimes(1);
    expect(carregarMensagensMesaMobile).toHaveBeenCalledWith("token-123", 22);
    expect(mesaFeedCursorRef.current).toBe("2026-03-21T13:00:00Z");
    expect(onObserveMesaFeedReadMetadata).toHaveBeenCalledWith(
      expect.objectContaining({
        route: "feed",
        deliveryMode: "v2",
      }),
    );
    expect(onObserveMesaFeedRequestedTargetIds).toHaveBeenCalledWith([21, 22]);
    expect(result).toMatchObject({
      requestDispatched: true,
      requestedTargetIds: [21, 22],
      generatedNotificationsCount: 0,
      errorMessage: null,
      skipReason: null,
      feedRequestTrace: null,
      feedReadMetadata: expect.objectContaining({
        route: "feed",
        deliveryMode: "v2",
      }),
    });
  });

  it("expõe skipReason canonico quando nenhum target elegivel e monitorado", async () => {
    (carregarLaudosMobile as jest.Mock).mockResolvedValue({
      itens: [
        {
          id: 80,
          titulo: "Laudo 80",
          status_card: "aberto",
          status_revisao: "aprovado",
          status_card_label: "Aberto",
          permite_edicao: false,
          permite_reabrir: false,
        },
      ],
    });

    const onObserveMesaFeedReadMetadata = jest.fn();
    const onObserveMesaFeedRequestedTargetIds = jest.fn();

    const result = await runMonitorActivityFlow({
      accessToken: "token-123",
      monitorandoAtividade: false,
      conversaLaudoId: null,
      conversaLaudoTitulo: "",
      sessionUserId: 1,
      assinaturaStatusLaudo: (item) => `${item.id}:${item.status_card}`,
      assinaturaMensagemMesa: (item) => `${item.id}:${item.resolvida_em || ""}`,
      selecionarLaudosParaMonitoramentoMesa: () => [],
      criarNotificacaoStatusLaudo: (item) => ({ id: `status:${item.id}` }),
      criarNotificacaoMesa: (kind, item) => ({ id: `${kind}:${item.id}` }),
      atualizarResumoLaudoAtual: jest.fn(),
      registrarNotificacoes: jest.fn(),
      erroSugereModoOffline: jest.fn().mockReturnValue(false),
      chaveCacheLaudo: (laudoId) => String(laudoId || ""),
      statusSnapshotRef: { current: {} },
      mesaSnapshotRef: { current: {} },
      mesaFeedCursorRef: { current: "" },
      onSetMonitorandoAtividade: jest.fn(),
      onSetLaudosDisponiveis: jest.fn(),
      onSetCacheLaudos: jest.fn(),
      onSetErroLaudos: jest.fn(),
      onSetMensagensMesa: jest.fn(),
      onSetLaudoMesaCarregado: jest.fn(),
      onSetCacheMesa: jest.fn(),
      onSetStatusApi: jest.fn(),
      onSetErroConversaIfEmpty: jest.fn(),
      onObserveMesaFeedReadMetadata,
      onObserveMesaFeedRequestedTargetIds,
    });

    expect(carregarFeedMesaMobile).not.toHaveBeenCalled();
    expect(onObserveMesaFeedRequestedTargetIds).toHaveBeenCalledWith([]);
    expect(onObserveMesaFeedReadMetadata).toHaveBeenCalledWith(null);
    expect(result).toMatchObject({
      requestDispatched: false,
      requestedTargetIds: [],
      skipReason: "no_target",
      generatedNotificationsCount: 0,
      errorMessage: null,
      feedRequestTrace: null,
      feedReadMetadata: null,
    });
  });

  it("propaga o trace da chamada real do feed para o resultado do monitoramento", async () => {
    (carregarLaudosMobile as jest.Mock).mockResolvedValue({
      itens: [
        {
          id: 80,
          titulo: "Laudo 80",
          status_card: "aguardando",
          status_revisao: "aguardando",
          status_card_label: "Aguardando",
          permite_edicao: true,
          permite_reabrir: false,
        },
      ],
    });
    (carregarFeedMesaMobile as jest.Mock).mockImplementation(
      async (
        _token: string,
        payload: { onRequestTrace?: (trace: unknown) => void },
      ) => {
        payload.onRequestTrace?.({
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
          validationSessionId: "orgv_09q",
          operatorRunId: "oprv_09q",
          usageMode: "organic_validation",
          responseStatus: 200,
          backendRequestId: "cid-80",
          failureKind: null,
          failureDetail: null,
          fallbackReason: null,
          deliveryMode: "v2",
        });
        return attachMobileV2ReadRenderMetadata(
          {
            cursor_atual: "2026-03-26T20:00:00Z",
            laudo_ids: [80],
            itens: [],
          },
          {
            route: "feed",
            deliveryMode: "v2",
            capabilitiesVersion: "2026-03-26.09q",
            rolloutBucket: 12,
            usageMode: "organic_validation",
            validationSessionId: "orgv_09q",
          },
        );
      },
    );

    const result = await runMonitorActivityFlow({
      accessToken: "token-123",
      monitorandoAtividade: false,
      conversaLaudoId: 80,
      conversaLaudoTitulo: "Laudo 80",
      sessionUserId: 1,
      assinaturaStatusLaudo: (item) => `${item.id}:${item.status_card}`,
      assinaturaMensagemMesa: (item) => `${item.id}:${item.resolvida_em || ""}`,
      selecionarLaudosParaMonitoramentoMesa: () => [80],
      criarNotificacaoStatusLaudo: (item) => ({ id: `status:${item.id}` }),
      criarNotificacaoMesa: (kind, item) => ({ id: `${kind}:${item.id}` }),
      atualizarResumoLaudoAtual: jest.fn(),
      registrarNotificacoes: jest.fn(),
      erroSugereModoOffline: jest.fn().mockReturnValue(false),
      chaveCacheLaudo: (laudoId) => String(laudoId || ""),
      statusSnapshotRef: { current: {} },
      mesaSnapshotRef: { current: {} },
      mesaFeedCursorRef: { current: "" },
      onSetMonitorandoAtividade: jest.fn(),
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
    });

    expect(result.feedRequestTrace).toMatchObject({
      traceId: "feed-trace-80",
      phase: "response_received",
      actualRoute: "v2",
      responseStatus: 200,
    });
  });
});
