jest.mock("../../config/mobileV2HumanValidation", () => ({
  acknowledgeMobileV2HumanValidationRender: jest.fn(),
}));

jest.mock("../../config/mobileV2Config", () => ({
  getAndroidV2ReadContractsRuntimeSnapshot: jest.fn(() => ({
    enabled: true,
    rawValue: "1",
    source: "expo_public_env",
  })),
}));

import { act, renderHook } from "@testing-library/react-native";

import { acknowledgeMobileV2HumanValidationRender } from "../../config/mobileV2HumanValidation";
import type { MobileLaudoCard } from "../../types/mobile";
import { usePilotAutomationController } from "./usePilotAutomationController";

function createLaudoCard(id: number): MobileLaudoCard {
  return {
    id,
    titulo: `Laudo ${id}`,
    preview: `Preview ${id}`,
    pinado: false,
    data_iso: "2026-03-30T10:00:00.000Z",
    data_br: "30/03/2026",
    hora_br: "10:00",
    tipo_template: "padrao",
    status_card: "aguardando",
    status_revisao: "aguardando",
    status_card_label: "Aguardando",
    permite_edicao: true,
    permite_reabrir: false,
    possui_historico: true,
  };
}

function createParams(
  overrides: Partial<Parameters<typeof usePilotAutomationController>[0]> = {},
): Parameters<typeof usePilotAutomationController>[0] {
  return {
    activityCenterDiagnostics: {
      phase: "idle",
      requestDispatched: false,
      requestedTargetIds: [],
      lastError: null,
      lastReadMetadata: null,
      lastRequestTrace: null,
      lastSkipReason: null,
    },
    centralAtividadeAberta: false,
    handleSelecionarHistorico: jest.fn().mockResolvedValue(undefined),
    laudoMesaCarregado: null,
    mesaThreadRenderConfirmada: false,
    notificacoes: [],
    selectedHistoryItemId: null,
    sessionAccessToken: "token-123",
    sessionLoading: false,
    ultimoMetaLeituraFeedMesa: null,
    ultimoMetaLeituraThreadMesa: null,
    ultimosAlvosConsultadosFeedMesa: [],
    ...overrides,
  };
}

describe("usePilotAutomationController", () => {
  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it("marca a selecao como pronta quando o shell confirma o laudo apos o callback", async () => {
    const handleSelecionarHistorico = jest.fn().mockResolvedValue(undefined);
    const params = createParams({ handleSelecionarHistorico });
    const { result, rerender } = renderHook(
      (currentParams: Parameters<typeof usePilotAutomationController>[0]) =>
        usePilotAutomationController(currentParams),
      { initialProps: params },
    );
    const laudo = createLaudoCard(80);

    await act(async () => {
      await result.current.handleSelecionarHistoricoComDiagnostico(laudo);
    });

    rerender({
      ...params,
      handleSelecionarHistorico,
      selectedHistoryItemId: 80,
    });

    expect(handleSelecionarHistorico).toHaveBeenCalledWith(laudo);
    expect(result.current.pilotAutomationMarkerIds).toContain(
      "authenticated-shell-selection-ready-80",
    );
    expect(result.current.pilotAutomationProbeLabel).toContain(
      "callback_completed=80",
    );
  });

  it("confirma o render humano do feed com alvos deduplicados", () => {
    jest.useFakeTimers();
    const { result } = renderHook(() =>
      usePilotAutomationController(
        createParams({
          centralAtividadeAberta: true,
          notificacoes: [
            {
              id: "mesa-80",
              kind: "mesa_nova",
              laudoId: 80,
              title: "Mesa 80",
              body: "Nova mensagem",
              createdAt: "2026-03-30T10:00:00.000Z",
              unread: true,
              targetThread: "mesa",
            },
            {
              id: "mesa-81",
              kind: "mesa_nova",
              laudoId: 81,
              title: "Mesa 81",
              body: "Nova mensagem",
              createdAt: "2026-03-30T10:01:00.000Z",
              unread: true,
              targetThread: "mesa",
            },
          ],
          ultimoMetaLeituraFeedMesa: {
            route: "feed",
            deliveryMode: "v2",
            capabilitiesVersion: "2026-03-30.01a",
            rolloutBucket: 7,
            usageMode: "organic_validation",
            validationSessionId: "orgv_01a",
            suggestedTargetIds: [82, 83],
          },
          ultimosAlvosConsultadosFeedMesa: [81, 82],
        }),
      ),
    );

    expect(
      result.current.activityCenterAutomationDiagnostics.modalVisible,
    ).toBe(true);

    act(() => {
      jest.advanceTimersByTime(120);
    });

    expect(acknowledgeMobileV2HumanValidationRender).toHaveBeenCalledWith(
      expect.objectContaining({
        accessToken: "token-123",
        surface: "feed",
        targetIds: [80, 81, 82, 83],
      }),
    );
  });

  it("confirma o render humano da thread da mesa quando o caso esta carregado", () => {
    jest.useFakeTimers();
    renderHook(() =>
      usePilotAutomationController(
        createParams({
          laudoMesaCarregado: 91,
          mesaThreadRenderConfirmada: true,
          ultimoMetaLeituraThreadMesa: {
            route: "thread",
            deliveryMode: "v2",
            capabilitiesVersion: "2026-03-30.01b",
            rolloutBucket: 9,
            usageMode: "organic_validation",
            validationSessionId: "orgv_01b",
            operatorRunId: "oprv_01b",
          },
        }),
      ),
    );

    act(() => {
      jest.advanceTimersByTime(120);
    });

    expect(acknowledgeMobileV2HumanValidationRender).toHaveBeenCalledWith(
      expect.objectContaining({
        accessToken: "token-123",
        surface: "thread",
        targetIds: [91],
      }),
    );
  });
});
