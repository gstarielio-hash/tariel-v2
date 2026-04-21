import type { ActiveThread } from "../chat/types";
import {
  guidedInspectionDraftToMobilePayload,
  type GuidedInspectionDraft,
} from "../inspection/guidedInspection";

export interface ThreadRouteSnapshot {
  activeThread: ActiveThread;
  conversationLaudoId: number | null;
  guidedInspectionDraft: GuidedInspectionDraft | null;
  threadHomeVisible: boolean;
}

export function buildThreadRouteSnapshot(input: {
  activeThread: ActiveThread;
  conversationLaudoId: number | null;
  guidedInspectionDraft: GuidedInspectionDraft | null;
  threadHomeVisible: boolean;
}): ThreadRouteSnapshot {
  return {
    activeThread: input.activeThread,
    conversationLaudoId: input.conversationLaudoId,
    guidedInspectionDraft: input.guidedInspectionDraft,
    threadHomeVisible: input.threadHomeVisible,
  };
}

function serializeGuidedDraft(
  draft: GuidedInspectionDraft | null | undefined,
): string {
  if (!draft) {
    return "";
  }

  return JSON.stringify(guidedInspectionDraftToMobilePayload(draft));
}

export function threadRouteSnapshotKey(snapshot: ThreadRouteSnapshot): string {
  return [
    snapshot.activeThread,
    snapshot.conversationLaudoId ?? "sem-laudo",
    snapshot.threadHomeVisible ? "home" : "thread",
    serializeGuidedDraft(snapshot.guidedInspectionDraft),
  ].join("|");
}

export function threadRouteSnapshotsEqual(
  left: ThreadRouteSnapshot | null | undefined,
  right: ThreadRouteSnapshot | null | undefined,
): boolean {
  if (!left || !right) {
    return false;
  }

  return threadRouteSnapshotKey(left) === threadRouteSnapshotKey(right);
}
