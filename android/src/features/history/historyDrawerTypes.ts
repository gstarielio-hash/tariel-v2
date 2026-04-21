import type {
  MobileActiveOwnerRole,
  MobileCaseLifecycleStatus,
  MobileInspectionEntryModeEffective,
  MobileInspectionEntryModePreference,
  MobileLifecycleTransition,
  MobileOfficialIssueSummary,
  MobileReportPackDraft,
  MobileSurfaceAction,
} from "../../types/mobile";

export interface HistoryDrawerSection<TItem extends HistoryDrawerPanelItem> {
  key: string;
  title: string;
  items: TItem[];
}

export interface HistoryDrawerPanelItem {
  id: number;
  titulo: string;
  preview: string;
  data_iso: string;
  status_card: string;
  status_card_label: string;
  pinado: boolean;
  tipo_template: string | null;
  permite_edicao: boolean;
  permite_reabrir: boolean;
  case_lifecycle_status?: MobileCaseLifecycleStatus;
  active_owner_role?: MobileActiveOwnerRole;
  allowed_lifecycle_transitions?: MobileLifecycleTransition[];
  allowed_surface_actions?: MobileSurfaceAction[];
  report_pack_draft?: MobileReportPackDraft | null;
  official_issue_summary?: MobileOfficialIssueSummary | null;
  entry_mode_preference?: MobileInspectionEntryModePreference;
  entry_mode_effective?: MobileInspectionEntryModeEffective;
  entry_mode_reason?: string;
}
