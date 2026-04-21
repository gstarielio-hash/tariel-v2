import { buildInspectorSessionModalsRootProps } from "./buildInspectorRootChromeProps";

describe("buildInspectorRootChromeProps", () => {
  it("monta os session modals usando o estado derivado compartilhado", () => {
    const props = buildInspectorSessionModalsRootProps({
      activityAndLockState: {
        activityCenterAutomationDiagnostics: {
          modalVisible: true,
          phase: "settled",
          requestDispatched: false,
          requestedTargetIds: [],
          notificationCount: 0,
          feedReadMetadata: null,
          requestTrace: null,
          skipReason: "no_target",
        },
        automationDiagnosticsEnabled: true,
        bloqueioAppAtivo: false,
        centralAtividadeAberta: true,
        deviceBiometricsEnabled: true,
        formatarHorarioAtividade: jest.fn().mockReturnValue("agora"),
        handleAbrirNotificacao: jest.fn(),
        handleDesbloquearAplicativo: jest.fn(),
        handleLogout: jest.fn(),
        monitorandoAtividade: false,
        notificacoes: [],
        session: null,
        setCentralAtividadeAberta: jest.fn(),
      },
      attachmentState: {
        anexosAberto: false,
        attachmentPickerOptions: [],
        handleEscolherAnexo: jest.fn(),
        previewAnexoImagem: null,
        setAnexosAberto: jest.fn(),
        setPreviewAnexoImagem: jest.fn(),
      },
      baseState: {
        filaOfflineFiltrada: [],
        filaOfflineOrdenada: [
          {
            id: "offline-1",
            channel: "chat",
            operation: "message",
            laudoId: 99,
            text: "Pendência",
            createdAt: "2026-03-30T10:00:00.000Z",
            title: "Pendência",
            attachment: null,
            referenceMessageId: null,
            qualityGateDecision: null,
            attempts: 0,
            lastAttemptAt: "",
            lastError: "",
            nextRetryAt: "",
            aiMode: "detalhado",
            aiSummary: "",
            aiMessagePrefix: "",
          },
        ],
        filtrosFilaOffline: [{ key: "all", label: "Tudo", count: 1 }],
        podeSincronizarFilaOffline: true,
        resumoFilaOfflineFiltrada: "1 pendência",
      },
      offlineQueueState: {
        detalheStatusPendenciaOffline: jest.fn().mockReturnValue("Aguardando"),
        filaOfflineAberta: true,
        filtroFilaOffline: "all",
        handleRetomarItemFilaOffline: jest.fn(),
        iconePendenciaOffline: jest.fn().mockReturnValue("clock-outline"),
        legendaPendenciaOffline: jest.fn().mockReturnValue("Pendente"),
        pendenciaFilaProntaParaReenvio: jest.fn().mockReturnValue(true),
        removerItemFilaOffline: jest.fn(),
        resumoPendenciaOffline: jest.fn().mockReturnValue("Resumo"),
        rotuloStatusPendenciaOffline: jest.fn().mockReturnValue("Pronto"),
        setFilaOfflineAberta: jest.fn(),
        setFiltroFilaOffline: jest.fn(),
        sincronizacaoDispositivos: true,
        sincronizarFilaOffline: jest.fn(),
        sincronizarItemFilaOffline: jest.fn(),
        sincronizandoFilaOffline: false,
        sincronizandoItemFilaId: "",
        statusApi: "online",
      },
      settingsState: {
        confirmSheet: null,
        confirmTextDraft: "",
        fecharConfirmacaoConfiguracao: jest.fn(),
        fecharSheetConfiguracao: jest.fn(),
        handleConfirmarAcaoCritica: jest.fn(),
        handleConfirmarSettingsSheet: jest.fn(),
        renderSettingsSheetBody: jest.fn().mockReturnValue(null),
        setConfirmTextDraft: jest.fn(),
        settingsSheet: null,
        settingsSheetLoading: false,
        settingsSheetNotice: "",
      },
    });

    expect(props.activityCenterVisible).toBe(true);
    expect(props.automationDiagnosticsEnabled).toBe(true);
    expect(props.offlineQueueVisible).toBe(true);
    expect(props.filaOfflineOrdenadaTotal).toBe(1);
    expect(props.podeSincronizarFilaOffline).toBe(true);
    expect(props.resumoFilaOfflineFiltrada).toBe("1 pendência");
  });
});
