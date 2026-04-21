import type { AuthenticatedAppRequest } from "@/lib/server/app-auth";
import {
  fetchAppInspectorStatus,
  fetchAppMesaMessages,
  fetchAppMesaSummary,
  type AppInspectorStatusPayload,
  type AppMesaMessagePayload,
  type AppMesaMessagesPayload,
  type AppMesaSummaryPayload,
} from "@/lib/server/app-mesa-bridge";
import {
  getAppPortalOverview,
  type AppPortalOverview,
  type AppPortalReportSummary,
} from "@/lib/server/app-portal";

export interface AppWorkspaceData {
  overview: AppPortalOverview;
  inspectorStatus: AppInspectorStatusPayload | null;
  selectedReport: AppPortalReportSummary | null;
  selectedSummary: AppMesaSummaryPayload | null;
  selectedMessages: AppMesaMessagesPayload | null;
  threadPreview: AppMesaMessagePayload[];
  messageIndex: Map<number, AppMesaMessagePayload>;
  referencedMessage: AppMesaMessagePayload | null;
}

export async function getAppWorkspace(
  appSession: AuthenticatedAppRequest,
  input: {
    selectedLaudoId?: number | null;
    selectedReferenceMessageId?: number | null;
  } = {},
): Promise<AppWorkspaceData | null> {
  const [overview, inspectorStatus] = await Promise.all([
    getAppPortalOverview({
      userId: appSession.user.id,
      companyId: appSession.user.companyId,
    }),
    fetchAppInspectorStatus(appSession).catch(() => null),
  ]);

  if (!overview) {
    return null;
  }

  const requestedLaudoId = Number(input.selectedLaudoId ?? 0) || 0;
  const requestedReferenceMessageId = Number(input.selectedReferenceMessageId ?? 0) || 0;
  const activeStatusLaudoId = Number(inspectorStatus?.laudo_id ?? 0) || 0;
  const fallbackReport = overview.recentReports[0] ?? null;
  const selectedReport =
    overview.recentReports.find((report) => report.id === requestedLaudoId)
    ?? overview.recentReports.find((report) => report.id === activeStatusLaudoId)
    ?? fallbackReport;
  const selectedSummary = selectedReport
    ? await fetchAppMesaSummary(appSession, selectedReport.id).catch(() => null)
    : null;
  const selectedMessages = selectedReport
    ? await fetchAppMesaMessages(appSession, selectedReport.id).catch(() => null)
    : null;
  const threadPreview = selectedMessages?.itens.slice(-6).reverse() ?? [];
  const messageIndex = new Map((selectedMessages?.itens ?? []).map((message) => [message.id, message]));
  const referencedMessage = messageIndex.get(requestedReferenceMessageId) ?? null;

  return {
    overview,
    inspectorStatus,
    selectedReport,
    selectedSummary,
    selectedMessages,
    threadPreview,
    messageIndex,
    referencedMessage,
  };
}
