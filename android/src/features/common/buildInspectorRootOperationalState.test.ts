import { buildInspectorRootOperationalState } from "./buildInspectorRootOperationalState";

describe("buildInspectorRootOperationalState", () => {
  it("centraliza refresh e derivados operacionais finais do root", () => {
    const result = buildInspectorRootOperationalState({
      refreshState: {
        abaAtiva: "mesa",
        carregarConversaAtual: jest.fn(),
        carregarListaLaudos: jest.fn(),
        carregarMesaAtual: jest.fn(),
        conversa: { laudoId: 9 },
        criarNotificacaoSistema: jest.fn(() => ({
          id: "1",
          unread: true,
          title: "ok",
          body: "ok",
          createdAt: "",
          kind: "status",
          laudoId: null,
          targetThread: "chat",
        })),
        filaOffline: [],
        onCanSyncOnCurrentNetwork: jest.fn(),
        onIsOfflineItemReadyForRetry: jest.fn(),
        onPingApi: jest.fn(),
        onRegistrarNotificacoes: jest.fn(),
        onSetErroConversa: jest.fn(),
        onSetErroMesa: jest.fn(),
        onSetSincronizandoAgora: jest.fn(),
        onSetStatusApi: jest.fn(),
        onSetUsandoCacheOffline: jest.fn(),
        session: null,
        sincronizacaoDispositivos: true,
        sincronizarFilaOffline: jest.fn(),
        wifiOnlySync: false,
      },
      offlineState: {
        offlineQueue: [],
        statusApi: "online",
        syncEnabled: true,
        wifiOnlySync: false,
        syncingQueue: false,
        syncingItemId: "",
        isItemReadyForRetry: jest.fn().mockReturnValue(false),
        getPriority: jest.fn().mockReturnValue(0),
      },
      supportState: {
        abaAtiva: "mesa",
        bootstrapApiBaseUrl: "https://api.tariel.test/base",
        bootstrapSupportWhatsapp: "https://wa.me/5511999999999",
        cacheUpdatedAt: "2026-03-30T10:00:00.000Z",
        carregandoLaudos: false,
        carregandoMesa: false,
        conversaLaudoId: 9,
        economiaDados: false,
        filaOffline: [],
        formatarHorarioAtividade: jest.fn().mockReturnValue("agora"),
        laudoMesaCarregado: 9,
        limpandoCache: false,
        notificacoes: [
          {
            unread: true,
            laudoId: 9,
            targetThread: "mesa" as const,
          },
        ],
        preferredVoiceId: "voice-2",
        sincronizandoAgora: false,
        sincronizandoConversa: false,
        sincronizandoFilaOffline: false,
        sincronizandoMesa: false,
        statusAtualizacaoApp: "Atualizado",
        ultimaLimpezaCacheEm: "",
        ttsSupported: true,
        usoBateria: "Otimizado",
        voices: [
          { identifier: "voice-1", name: "Padrão" },
          { identifier: "voice-2", name: "Narrador" },
        ],
      },
    });

    expect(typeof result.handleRefresh).toBe("function");
    expect(result.mesaThreadRenderConfirmada).toBe(true);
    expect(result.laudoSelecionadoShellId).toBe(9);
    expect(result.canalSuporteLabel).toBe("WhatsApp");
    expect(result.apiEnvironmentLabel).toBe("api.tariel.test");
    expect(result.preferredVoiceLabel).toBe("Narrador");
    expect(result.resumoCentralAtividade).toBe("1 nova(s)");
    expect(result.resumoCache).toBe("Atualizado agora");
    expect(result.sincronizandoDados).toBe(false);
    expect(result.notificacoesMesaLaudoAtual).toBe(1);
    expect(result.offlineSyncObservability.contract_name).toBe(
      "android_offline_sync_view",
    );
  });
});
