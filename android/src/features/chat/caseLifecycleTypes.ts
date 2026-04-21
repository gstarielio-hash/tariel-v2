import type {
  MobileActiveOwnerRole,
  MobileCaseLifecycleStatus,
} from "../../types/mobile";

export type CanonicalCaseLifecycleStatus = MobileCaseLifecycleStatus;
export type CanonicalCaseOwnerRole = MobileActiveOwnerRole;

export type CaseVisualTone = "success" | "danger" | "accent" | "muted";
export type CaseVisualIcon =
  | "message-processing-outline"
  | "file-document-edit-outline"
  | "clipboard-clock-outline"
  | "alert-circle-outline"
  | "check-decagram-outline"
  | "file-document-check-outline";
