import { useEffect, useMemo, useRef, useState } from "react";

import {
  acknowledgeMobileV2HumanValidationRender,
  type MobileV2ReadRenderMetadata,
} from "../../config/mobileV2HumanValidation";
import { getAndroidV2ReadContractsRuntimeSnapshot } from "../../config/mobileV2Config";
import type { MobileLaudoCard } from "../../types/mobile";
import type { ActivityCenterDiagnostics as ActivityCenterControllerDiagnostics } from "../activity/useActivityCenterController";
import type { MobileActivityNotification } from "../chat/types";
import {
  buildPilotAutomationMarkerIds,
  buildPilotAutomationProbeLabel,
  createEmptyHistorySelectionAutomationDiagnostics,
  recordHistorySelectionCallbackCompleted,
  recordHistorySelectionTap,
  syncHistorySelectionWithShell,
  type ActivityCenterAutomationDiagnostics,
} from "./mobilePilotAutomationDiagnostics";

interface UsePilotAutomationControllerParams {
  activityCenterDiagnostics: ActivityCenterControllerDiagnostics;
  centralAtividadeAberta: boolean;
  handleSelecionarHistorico: (item: MobileLaudoCard) => Promise<void>;
  laudoMesaCarregado: number | null;
  mesaThreadRenderConfirmada: boolean;
  notificacoes: MobileActivityNotification[];
  selectedHistoryItemId: number | null;
  sessionAccessToken: string | null;
  sessionLoading: boolean;
  ultimoMetaLeituraFeedMesa: MobileV2ReadRenderMetadata | null;
  ultimoMetaLeituraThreadMesa: MobileV2ReadRenderMetadata | null;
  ultimosAlvosConsultadosFeedMesa: number[];
}

function normalizePositiveInteger(
  value: number | null | undefined,
): number | null {
  return typeof value === "number" && Number.isFinite(value) && value > 0
    ? Math.round(value)
    : null;
}

export function usePilotAutomationController(
  params: UsePilotAutomationControllerParams,
) {
  const [historySelectionDiagnostics, setHistorySelectionDiagnostics] =
    useState(createEmptyHistorySelectionAutomationDiagnostics);
  const previousSelectedHistoryItemRef = useRef<number | null>(null);

  const alvosHumanConfirmadosFeed = useMemo(
    () =>
      Array.from(
        new Set(
          [
            ...params.notificacoes
              .filter(
                (item) =>
                  item.targetThread === "mesa" &&
                  typeof item.laudoId === "number" &&
                  item.laudoId > 0,
              )
              .map((item) => Number(item.laudoId)),
            ...params.ultimosAlvosConsultadosFeedMesa,
            ...(Array.isArray(
              params.ultimoMetaLeituraFeedMesa?.suggestedTargetIds,
            )
              ? params.ultimoMetaLeituraFeedMesa.suggestedTargetIds
              : []),
          ]
            .map((item) => Number(item))
            .filter((item) => Number.isFinite(item) && item > 0),
        ),
      ),
    [
      params.notificacoes,
      params.ultimoMetaLeituraFeedMesa,
      params.ultimosAlvosConsultadosFeedMesa,
    ],
  );

  const activityCenterAutomationDiagnostics =
    useMemo<ActivityCenterAutomationDiagnostics>(
      () => ({
        modalVisible: params.centralAtividadeAberta,
        phase: params.activityCenterDiagnostics.phase,
        requestDispatched: params.activityCenterDiagnostics.requestDispatched,
        requestedTargetIds:
          params.activityCenterDiagnostics.requestedTargetIds.length > 0
            ? params.activityCenterDiagnostics.requestedTargetIds
            : params.ultimosAlvosConsultadosFeedMesa,
        notificationCount: params.notificacoes.length,
        feedReadMetadata:
          params.activityCenterDiagnostics.lastReadMetadata ||
          params.ultimoMetaLeituraFeedMesa,
        requestTrace: params.activityCenterDiagnostics.lastRequestTrace,
        skipReason: params.activityCenterDiagnostics.lastSkipReason,
      }),
      [
        params.activityCenterDiagnostics.lastReadMetadata,
        params.activityCenterDiagnostics.lastRequestTrace,
        params.activityCenterDiagnostics.lastSkipReason,
        params.activityCenterDiagnostics.phase,
        params.activityCenterDiagnostics.requestDispatched,
        params.activityCenterDiagnostics.requestedTargetIds,
        params.centralAtividadeAberta,
        params.notificacoes.length,
        params.ultimoMetaLeituraFeedMesa,
        params.ultimosAlvosConsultadosFeedMesa,
      ],
    );

  const runtimeFlagAutomationDiagnostics = useMemo(() => {
    const runtimeFlag = getAndroidV2ReadContractsRuntimeSnapshot();
    return {
      enabled: runtimeFlag.enabled,
      rawValue: runtimeFlag.rawValue,
      source: runtimeFlag.source,
    };
  }, []);

  const pilotAutomationMarkerIds = useMemo(
    () =>
      buildPilotAutomationMarkerIds({
        selectedHistoryItemId: params.selectedHistoryItemId,
        historySelection: historySelectionDiagnostics,
        activityCenter: activityCenterAutomationDiagnostics,
      }),
    [
      activityCenterAutomationDiagnostics,
      historySelectionDiagnostics,
      params.selectedHistoryItemId,
    ],
  );

  const pilotAutomationProbeLabel = useMemo(
    () =>
      buildPilotAutomationProbeLabel({
        selectedHistoryItemId: params.selectedHistoryItemId,
        historySelection: historySelectionDiagnostics,
        activityCenter: activityCenterAutomationDiagnostics,
        runtimeFlag: runtimeFlagAutomationDiagnostics,
      }),
    [
      activityCenterAutomationDiagnostics,
      historySelectionDiagnostics,
      params.selectedHistoryItemId,
      runtimeFlagAutomationDiagnostics,
    ],
  );

  useEffect(() => {
    setHistorySelectionDiagnostics((current) =>
      syncHistorySelectionWithShell({
        current,
        selectedHistoryItemId: params.selectedHistoryItemId,
        previousSelectedHistoryItemId: previousSelectedHistoryItemRef.current,
      }),
    );
    previousSelectedHistoryItemRef.current = params.selectedHistoryItemId;
  }, [params.selectedHistoryItemId]);

  useEffect(() => {
    if (!params.sessionAccessToken || !params.centralAtividadeAberta) {
      return;
    }
    if (!alvosHumanConfirmadosFeed.length) {
      return;
    }

    const timeout = setTimeout(() => {
      void acknowledgeMobileV2HumanValidationRender({
        accessToken: params.sessionAccessToken,
        surface: "feed",
        readMetadata: params.ultimoMetaLeituraFeedMesa,
        targetIds: alvosHumanConfirmadosFeed,
      });
    }, 120);

    return () => clearTimeout(timeout);
  }, [
    alvosHumanConfirmadosFeed,
    params.centralAtividadeAberta,
    params.sessionAccessToken,
    params.ultimoMetaLeituraFeedMesa,
  ]);

  useEffect(() => {
    if (
      !params.sessionAccessToken ||
      !params.laudoMesaCarregado ||
      !params.mesaThreadRenderConfirmada
    ) {
      return;
    }
    const laudoMesaCarregado = params.laudoMesaCarregado;

    const timeout = setTimeout(() => {
      void acknowledgeMobileV2HumanValidationRender({
        accessToken: params.sessionAccessToken,
        surface: "thread",
        readMetadata: params.ultimoMetaLeituraThreadMesa,
        targetIds: [laudoMesaCarregado],
      });
    }, 120);

    return () => clearTimeout(timeout);
  }, [
    params.laudoMesaCarregado,
    params.mesaThreadRenderConfirmada,
    params.sessionAccessToken,
    params.ultimoMetaLeituraThreadMesa,
  ]);

  useEffect(() => {
    if (params.sessionAccessToken || params.sessionLoading) {
      return;
    }

    setHistorySelectionDiagnostics(
      createEmptyHistorySelectionAutomationDiagnostics(),
    );
    previousSelectedHistoryItemRef.current = null;
  }, [params.sessionAccessToken, params.sessionLoading]);

  async function handleSelecionarHistoricoComDiagnostico(
    item: MobileLaudoCard,
  ) {
    const targetId = normalizePositiveInteger(item.id);

    setHistorySelectionDiagnostics((current) =>
      recordHistorySelectionTap(current, targetId),
    );

    try {
      await params.handleSelecionarHistorico(item);
      setHistorySelectionDiagnostics((current) =>
        recordHistorySelectionCallbackCompleted(current, targetId),
      );
    } catch (error) {
      setHistorySelectionDiagnostics((current) =>
        recordHistorySelectionCallbackCompleted(current, null),
      );
      throw error;
    }
  }

  return {
    activityCenterAutomationDiagnostics,
    handleSelecionarHistoricoComDiagnostico,
    pilotAutomationMarkerIds,
    pilotAutomationProbeLabel,
  };
}
