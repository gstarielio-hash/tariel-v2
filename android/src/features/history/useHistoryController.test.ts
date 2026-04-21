import type { MobileLaudoCard } from "../../types/mobile";
import type { ThreadRouteSnapshot } from "../common/threadRouteHistory";
import { useHistoryController } from "./useHistoryController";

interface TestHistoryCache {
  laudos: MobileLaudoCard[];
  conversasPorLaudo: Record<string, unknown>;
  mesaPorLaudo: Record<string, unknown>;
  updatedAt: string;
}

function criarCard(overrides: Partial<MobileLaudoCard> = {}): MobileLaudoCard {
  return {
    id: 10,
    titulo: "Laudo 10",
    preview: "Resumo",
    pinado: false,
    data_iso: "2026-03-20T10:00:00.000Z",
    data_br: "20/03/2026",
    hora_br: "10:00",
    tipo_template: "TC",
    status_revisao: "ativo",
    status_card: "aguardando",
    status_card_label: "Aguardando",
    permite_edicao: true,
    permite_reabrir: false,
    possui_historico: true,
    ...overrides,
  };
}

function criarParams(
  overrides: Partial<
    Parameters<
      typeof useHistoryController<
        string,
        TestHistoryCache,
        string,
        { laudoId: number | null }
      >
    >[0]
  > = {},
): Parameters<
  typeof useHistoryController<
    string,
    TestHistoryCache,
    string,
    { laudoId: number | null }
  >
>[0] {
  return {
    keyboardHeight: 0,
    historicoAberto: false,
    historicoAbertoRefAtual: false,
    pendingHistoryThreadRoute: null,
    conversaAtualLaudoId: null,
    historicoOcultoIds: [],
    laudosFixadosIds: [],
    fecharHistorico: jest.fn(),
    abrirHistorico: jest.fn(),
    fecharConfiguracoes: jest.fn(),
    handleSelecionarLaudo: jest.fn().mockResolvedValue(undefined),
    onCreateNewConversation: jest.fn().mockReturnValue("nova-conversa"),
    onDismissKeyboard: jest.fn(),
    onGetCacheKeyForLaudo: jest.fn((id) => String(id ?? "")),
    onSchedule: jest.fn((callback: () => void) => callback()),
    setAbaAtiva: jest.fn(),
    setAnexoMesaRascunho: jest.fn(),
    setAnexoRascunho: jest.fn(),
    setCacheLeitura: jest.fn(),
    setConversa: jest.fn(),
    setErroConversa: jest.fn(),
    setErroMesa: jest.fn(),
    setHistoricoOcultoIds: jest.fn(),
    setLaudoMesaCarregado: jest.fn(),
    setLaudosDisponiveis: jest.fn(),
    setLaudosFixadosIds: jest.fn(),
    setMensagem: jest.fn(),
    setMensagemMesa: jest.fn(),
    setMensagensMesa: jest.fn(),
    setNotificacoes: jest.fn(),
    setPendingHistoryThreadRoute: jest.fn(),
    setThreadRouteHistory: jest.fn(),
    ...overrides,
  };
}

describe("useHistoryController", () => {
  it("fecha o historico quando ele ja esta aberto", () => {
    const params = criarParams({
      historicoAberto: true,
    });

    const controller = useHistoryController(params);

    controller.handleAbrirHistorico();

    expect(params.fecharHistorico).toHaveBeenCalledWith({ limparBusca: true });
    expect(params.abrirHistorico).not.toHaveBeenCalled();
  });

  it("agenda a abertura do historico ao sair de configuracoes", () => {
    const params = criarParams();

    const controller = useHistoryController(params);

    controller.handleGerenciarConversasIndividuais();

    expect(params.fecharConfiguracoes).toHaveBeenCalled();
    expect(params.onSchedule).toHaveBeenCalledWith(expect.any(Function), 180);
    expect(params.abrirHistorico).toHaveBeenCalled();
  });

  it("alterna o fixado de um laudo e atualiza a lista local", () => {
    const params = criarParams();
    const card = criarCard();

    const controller = useHistoryController(params);

    controller.handleAlternarFixadoHistorico(card);

    const fixadosUpdater = (params.setLaudosFixadosIds as jest.Mock).mock
      .calls[0]?.[0] as (current: number[]) => number[];
    expect(fixadosUpdater([])).toEqual([10]);

    const laudosUpdater = (params.setLaudosDisponiveis as jest.Mock).mock
      .calls[0]?.[0] as (current: MobileLaudoCard[]) => MobileLaudoCard[];
    const proximo = laudosUpdater([card]);
    expect(proximo[0]?.pinado).toBe(true);
  });

  it("remove a conversa do historico e reseta a thread ativa quando necessario", () => {
    const params = criarParams({
      conversaAtualLaudoId: 10,
    });
    const card = criarCard();

    const controller = useHistoryController(params);

    controller.handleExcluirConversaHistorico(card);

    const ocultosUpdater = (params.setHistoricoOcultoIds as jest.Mock).mock
      .calls[0]?.[0] as (current: number[]) => number[];
    expect(ocultosUpdater([])).toEqual([10]);

    const notificationsUpdater = (params.setNotificacoes as jest.Mock).mock
      .calls[0]?.[0] as (
      current: Array<{ laudoId: number | null }>,
    ) => Array<{ laudoId: number | null }>;
    expect(notificationsUpdater([{ laudoId: 10 }, { laudoId: 11 }])).toEqual([
      { laudoId: 11 },
    ]);

    expect(params.setConversa).toHaveBeenCalledWith("nova-conversa");
    expect(params.setMensagensMesa).toHaveBeenCalledWith([]);
    expect(params.setMensagem).toHaveBeenCalledWith("");
    expect(params.setMensagemMesa).toHaveBeenCalledWith("");
    expect(params.setAnexoRascunho).toHaveBeenCalledWith(null);
    expect(params.setAnexoMesaRascunho).toHaveBeenCalledWith(null);
    expect(params.setErroMesa).toHaveBeenCalledWith("");
    expect(params.setErroConversa).toHaveBeenCalledWith("");
    expect(params.setLaudoMesaCarregado).toHaveBeenCalledWith(null);
  });

  it("acumula ids ocultos quando várias exclusões acontecem em sequência", () => {
    const params = criarParams();
    const controller = useHistoryController(params);

    controller.handleExcluirConversaHistorico(criarCard({ id: 10 }));
    controller.handleExcluirConversaHistorico(criarCard({ id: 11 }));

    const firstUpdater = (params.setHistoricoOcultoIds as jest.Mock).mock
      .calls[0]?.[0] as (current: number[]) => number[];
    const secondUpdater = (params.setHistoricoOcultoIds as jest.Mock).mock
      .calls[1]?.[0] as (current: number[]) => number[];

    expect(firstUpdater([])).toEqual([10]);
    expect(secondUpdater([10])).toEqual([10, 11]);
  });

  it("seleciona um item do historico abrindo a thread de chat", async () => {
    const params = criarParams();
    const card = criarCard();

    const controller = useHistoryController(params);

    await controller.handleSelecionarHistorico(card);

    expect(params.fecharHistorico).toHaveBeenCalledWith({ limparBusca: true });
    expect(params.setAbaAtiva).toHaveBeenCalledWith("chat");
    expect(params.handleSelecionarLaudo).toHaveBeenCalledWith(card);
  });

  it("empilha a rota anterior quando a seleção do histórico muda a thread atual", async () => {
    const pendingRoute: ThreadRouteSnapshot = {
      activeThread: "mesa",
      conversationLaudoId: 10,
      guidedInspectionDraft: null,
      threadHomeVisible: false,
    };
    const params = criarParams({
      pendingHistoryThreadRoute: pendingRoute,
    });
    const card = criarCard({ id: 20 });

    const controller = useHistoryController(params);

    await controller.handleSelecionarHistorico(card);

    const historyUpdater = (params.setThreadRouteHistory as jest.Mock).mock
      .calls[0]?.[0] as (
      current: ThreadRouteSnapshot[],
    ) => ThreadRouteSnapshot[];

    expect(historyUpdater([])).toEqual([pendingRoute]);
    expect(params.setPendingHistoryThreadRoute).toHaveBeenCalledWith(null);
  });
});
