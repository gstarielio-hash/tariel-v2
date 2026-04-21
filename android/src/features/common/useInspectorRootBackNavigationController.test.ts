import { renderHook } from "@testing-library/react-native";
import { BackHandler } from "react-native";

import { useInspectorRootBackNavigationController } from "./useInspectorRootBackNavigationController";
import type { ThreadRouteSnapshot } from "./threadRouteHistory";

const mockAddEventListener = jest.fn();
const mockKeyboardDismiss = jest.fn();
let capturedBackHandler: null | (() => boolean) = null;

function criarInput(overrides?: {
  localState?: Record<string, unknown>;
  shellSupport?: Record<string, unknown>;
  settingsSupportState?: Record<string, unknown>;
}) {
  const localState = {
    abaAtiva: "chat",
    conversa: null,
    guidedInspectionDraft: null,
    pendingHistoryThreadRoute: null,
    qualityGateVisible: false,
    setAbaAtiva: jest.fn(),
    setPendingHistoryThreadRoute: jest.fn(),
    setQualityGateVisible: jest.fn(),
    setThreadHomeGuidedTemplatesVisible: jest.fn(),
    setThreadRouteHistory: jest.fn(),
    threadHomeVisible: true,
    threadHomeGuidedTemplatesVisible: false,
    threadRouteHistory: [] as ThreadRouteSnapshot[],
    ...overrides?.localState,
  };
  const shellSupport = {
    anexosAberto: false,
    centralAtividadeAberta: false,
    configuracoesAberta: false,
    fecharConfiguracoes: jest.fn(),
    fecharHistorico: jest.fn(),
    filaOfflineAberta: false,
    historicoAberto: false,
    keyboardHeight: 0,
    previewAnexoImagem: null,
    setAnexosAberto: jest.fn(),
    setCentralAtividadeAberta: jest.fn(),
    setFilaOfflineAberta: jest.fn(),
    setPreviewAnexoImagem: jest.fn(),
    ...overrides?.shellSupport,
  };
  const settingsSupportState = {
    navigationActions: {
      fecharConfirmacaoConfiguracao: jest.fn(),
      fecharSheetConfiguracao: jest.fn(),
      handleVoltarResumoConfiguracoes: jest.fn(),
    },
    navigationState: {
      confirmSheet: null,
      settingsDrawerPage: "overview",
      settingsDrawerSection: "all",
      settingsSheet: null,
    },
    ...overrides?.settingsSupportState,
  };

  return {
    bootstrap: {
      localState,
      sessionFlow: {
        state: {
          session: {
            accessToken: "token-123",
          },
        },
      },
      settingsSupportState,
      shellSupport,
    } as any,
    controllers: {
      chatController: {
        actions: {
          abrirLaudoPorId: jest.fn().mockResolvedValue(undefined),
          handleAbrirNovoChat: jest.fn().mockResolvedValue(undefined),
          handleIniciarChatLivre: jest.fn().mockResolvedValue(undefined),
        },
      },
      guidedInspectionController: {
        actions: {
          handleStartGuidedInspection: jest.fn(),
          handleStopGuidedInspection: jest.fn(),
        },
      },
    } as any,
  };
}

describe("useInspectorRootBackNavigationController", () => {
  beforeEach(() => {
    capturedBackHandler = null;
    mockAddEventListener.mockReset();
    mockKeyboardDismiss.mockReset();
    mockAddEventListener.mockImplementation(
      (_eventName: string, handler: () => boolean) => {
        capturedBackHandler = handler;
        return {
          remove: jest.fn(),
        };
      },
    );
    jest
      .spyOn(BackHandler, "addEventListener")
      .mockImplementation(
        (
          eventName: "hardwareBackPress",
          handler: () => boolean | null | undefined,
        ) =>
          mockAddEventListener(
            eventName,
            handler as () => boolean,
          ) as ReturnType<typeof BackHandler.addEventListener>,
      );
    jest
      .spyOn(require("react-native").Keyboard, "dismiss")
      .mockImplementation(() => {
        mockKeyboardDismiss();
      });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("fecha o histórico antes de deixar o Android sair do app", () => {
    const input = criarInput({
      shellSupport: {
        historicoAberto: true,
      },
    });

    renderHook(() => useInspectorRootBackNavigationController(input));

    expect(capturedBackHandler?.()).toBe(true);
    expect(input.bootstrap.shellSupport.fecharHistorico).toHaveBeenCalledWith({
      limparBusca: true,
    });
  });

  it("volta da Mesa para o chat antes de navegar para trás", () => {
    const input = criarInput({
      localState: {
        abaAtiva: "mesa",
        conversa: { laudoId: 44 },
        threadHomeVisible: false,
      },
    });

    renderHook(() => useInspectorRootBackNavigationController(input));

    expect(capturedBackHandler?.()).toBe(true);
    expect(input.bootstrap.localState.setAbaAtiva).toHaveBeenCalledWith("chat");
  });

  it("restaura a rota anterior empilhada ao sair de uma conversa aberta pelo histórico", () => {
    const input = criarInput({
      localState: {
        conversa: { laudoId: 20 },
        threadHomeVisible: false,
        threadRouteHistory: [
          {
            activeThread: "chat",
            conversationLaudoId: 10,
            guidedInspectionDraft: null,
            threadHomeVisible: false,
          },
        ],
      },
    });

    renderHook(() => useInspectorRootBackNavigationController(input));

    expect(capturedBackHandler?.()).toBe(true);
    expect(
      input.controllers.chatController.actions.abrirLaudoPorId,
    ).toHaveBeenCalledWith("token-123", 10);
    expect(
      input.bootstrap.localState.setThreadRouteHistory,
    ).toHaveBeenCalledWith([]);
  });

  it("fecha primeiro a lista de templates do chat guiado antes de sair da home", () => {
    const input = criarInput({
      localState: {
        threadHomeGuidedTemplatesVisible: true,
      },
    });

    renderHook(() => useInspectorRootBackNavigationController(input));

    expect(capturedBackHandler?.()).toBe(true);
    expect(
      input.bootstrap.localState.setThreadHomeGuidedTemplatesVisible,
    ).toHaveBeenCalledWith(false);
  });

  it("encerra o modo guiado antes de sair da thread quando ainda existe draft ativo", () => {
    const input = criarInput({
      localState: {
        conversa: { laudoId: 44 },
        guidedInspectionDraft: {
          templateKey: "nr13",
        },
        threadHomeVisible: false,
      },
    });

    renderHook(() => useInspectorRootBackNavigationController(input));

    expect(capturedBackHandler?.()).toBe(true);
    expect(
      input.controllers.guidedInspectionController.actions
        .handleStopGuidedInspection,
    ).toHaveBeenCalledTimes(1);
    expect(
      input.controllers.chatController.actions.handleAbrirNovoChat,
    ).not.toHaveBeenCalled();
  });

  it("permite o comportamento padrão do Android quando já está na home", () => {
    const input = criarInput();

    renderHook(() => useInspectorRootBackNavigationController(input));

    expect(capturedBackHandler?.()).toBe(false);
    expect(BackHandler.addEventListener).toHaveBeenCalled();
  });
});
