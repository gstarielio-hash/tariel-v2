import type {
  MobilePreLaudoAnalysisBasisSummary,
  MobilePreLaudoMinimumEvidence,
} from "../../types/mobile";

export type ReportPackBlockStatus = "ready" | "attention" | "pending";

export interface MobileReportPackBlockSummary {
  key: string;
  title: string;
  status: ReportPackBlockStatus;
  statusLabel: string;
  summary: string;
}

export interface MobileReportPackFlowSummary {
  key: string;
  title: string;
  status: ReportPackBlockStatus;
  statusLabel: string;
  summary: string;
}

export interface MobileReportPackSectionSummary {
  key: string;
  title: string;
  status: ReportPackBlockStatus;
  statusLabel: string;
  summary: string;
  filledFieldCount: number;
  missingFieldCount: number;
  totalFieldCount: number;
  highlights: string[];
}

export interface MobileReportPackExecutiveSummary {
  key: string;
  title: string;
  status: ReportPackBlockStatus;
  statusLabel: string;
  summary: string;
  bullets: string[];
}

export interface MobileReportPackSlotSummary {
  key: string;
  label: string;
  status: ReportPackBlockStatus;
  statusLabel: string;
  required: boolean;
  acceptedTypes: string[];
  bindingPath: string;
  purpose: string;
  summary: string;
  resolved: boolean;
}

export interface MobileReportPackDraftSummary {
  modeled: boolean;
  familyKey: string;
  familyLabel: string;
  templateKey: string;
  templateLabel: string;
  assetLabel: string;
  locationLabel: string;
  inspectionObjective: string;
  inspectionContextLabel: string;
  inspectionContextDetail: string;
  finalValidationMode: string;
  finalValidationModeLabel: string;
  autonomyReady: boolean;
  readyForStructuredForm: boolean;
  readyForFinalization: boolean;
  readinessLabel: string;
  readinessDetail: string;
  totalBlocks: number;
  readyBlocks: number;
  attentionBlocks: number;
  pendingBlocks: number;
  evidenceCount: number;
  imageCount: number;
  textCount: number;
  missingEvidenceCount: number;
  maxConflictScore: number;
  minimumEvidence: MobilePreLaudoMinimumEvidence;
  checklistGroupTitles: string[];
  reviewRequired: string[];
  exampleAvailable: boolean;
  highlightedBlocks: MobileReportPackBlockSummary[];
  blockSummaries: MobileReportPackBlockSummary[];
  documentFlowEntries: MobileReportPackFlowSummary[];
  executiveSections: MobileReportPackExecutiveSummary[];
  documentSections: MobileReportPackSectionSummary[];
  highlightedDocumentSections: MobileReportPackSectionSummary[];
  requiredEvidenceSlots: MobileReportPackSlotSummary[];
  optionalEvidenceSlots: MobileReportPackSlotSummary[];
  analysisBasisSummary: MobilePreLaudoAnalysisBasisSummary;
  missingEvidenceMessages: string[];
  nextQuestions: string[];
}
