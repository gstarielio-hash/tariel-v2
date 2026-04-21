import { renderHook } from "@testing-library/react-native";

const mockHandleAbrirCentralAtividade = jest.fn();
const mockHandleAbrirNotificacao = jest.fn();

jest.mock("./useActivityCenterController", () => ({
  useActivityCenterController: jest.fn(() => ({
    state: {
      activityCenterDiagnostics: {
        phase: "idle",
        requestDispatched: false,
        requestedTargetIds: [],
        lastError: null,
        lastReadMetadata: null,
        lastRequestTrace: null,
        lastSkipReason: null,
      },
      monitorandoAtividade: false,
    },
    actions: {
      handleAbrirCentralAtividade: mockHandleAbrirCentralAtividade,
      handleAbrirNotificacao: mockHandleAbrirNotificacao,
      registrarNotificacoes: jest.fn(),
    },
  })),
}));

import { useActivityCenterController } from "./useActivityCenterController";
import { useInspectorRootActivityCenterController } from "./useInspectorRootActivityCenterController";

function criarInput() {
  return {
    state: {
      activeThread: "chat" as const,
      conversation: null,
      laudoMesaCarregado: null,
      laudosDisponiveis: [],
      messagesMesa: [],
      monitorIntervalMs: 30000,
      notificationSettings: {
        pushEnabled: true,
        responseAlertsEnabled: true,
        soundEnabled: true,
        vibrationEnabled: true,
        emailEnabled: false,
        soundPreset: "Ping" as const,
        showMessageContent: true,
        hideContentOnLockScreen: false,
        onlyShowNewMessage: false,
        chatCategoryEnabled: true,
        mesaCategoryEnabled: true,
        systemCategoryEnabled: true,
        criticalAlertsEnabled: true,
      },
      notifications: [],
      notificationsPermissionGranted: true,
      session: null,
      sessionLoading: false,
      statusApi: "online",
      syncEnabled: true,
      wifiOnlySync: false,
    },
    actionState: {
      assinaturaMensagemMesa: jest.fn(),
      assinaturaStatusLaudo: jest.fn(),
      carregarMesaAtual: jest.fn().mockResolvedValue(undefined),
      chaveCacheLaudo: jest.fn(),
      criarNotificacaoMesa: jest.fn(),
      criarNotificacaoStatusLaudo: jest.fn(),
      erroSugereModoOffline: jest.fn().mockReturnValue(false),
      onRecoverOnline: jest.fn().mockResolvedValue(undefined),
      openLaudoById: jest.fn().mockResolvedValue(undefined),
      saveNotificationsLocally: jest.fn().mockResolvedValue(undefined),
      selecionarLaudosParaMonitoramentoMesa: jest.fn().mockReturnValue([]),
    },
    setterState: {
      onObserveMesaFeedReadMetadata: jest.fn(),
      onObserveMesaFeedRequestedTargetIds: jest.fn(),
      onSetCacheLaudos: jest.fn(),
      onSetCacheMesa: jest.fn(),
      onSetErroConversaIfEmpty: jest.fn(),
      onSetErroLaudos: jest.fn(),
      onSetLaudoMesaCarregado: jest.fn(),
      onSetLaudosDisponiveis: jest.fn(),
      onSetMensagensMesa: jest.fn(),
      onSetStatusApi: jest.fn(),
      onUpdateCurrentConversationSummary: jest.fn(),
      setActiveThread: jest.fn(),
      setActivityCenterVisible: jest.fn(),
      setNotifications: jest.fn(),
    },
    limitsState: {
      maxNotifications: 10,
    },
  };
}

describe("useInspectorRootActivityCenterController", () => {
  it("encapsula a composição da central de atividade sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() =>
      useInspectorRootActivityCenterController(input),
    );
    const mockedHook = jest.mocked(useActivityCenterController);

    result.current.actions.handleAbrirCentralAtividade();
    result.current.actions.handleAbrirNotificacao({ id: "n1" } as never);

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        monitorIntervalMs: input.state.monitorIntervalMs,
        setNotifications: input.setterState.setNotifications,
        maxNotifications: input.limitsState.maxNotifications,
      }),
    );
    expect(mockHandleAbrirCentralAtividade).toHaveBeenCalledTimes(1);
    expect(mockHandleAbrirNotificacao).toHaveBeenCalledWith({
      id: "n1",
    });
  });
});
