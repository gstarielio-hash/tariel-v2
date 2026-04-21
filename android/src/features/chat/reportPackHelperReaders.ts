import type {
  MobilePreLaudoAnalysisBasisSummary,
  MobilePreLaudoChecklistGroup,
  MobilePreLaudoDocument,
  MobilePreLaudoDocumentFlowEntry,
  MobilePreLaudoDocumentSection,
  MobilePreLaudoExecutiveSection,
  MobilePreLaudoMinimumEvidence,
  MobilePreLaudoSlot,
} from "../../types/mobile";

import type { ReportPackBlockStatus } from "./reportPackHelperTypes";

export type JsonRecord = Record<string, unknown>;

export function isRecord(value: unknown): value is JsonRecord {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function readRecord(value: unknown): JsonRecord | null {
  return isRecord(value) ? value : null;
}

export function readArrayRecords(value: unknown): JsonRecord[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(
    (item): item is JsonRecord =>
      Boolean(item) && typeof item === "object" && !Array.isArray(item),
  );
}

export function readStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => readText(item)).filter(Boolean);
}

export function readText(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value.trim() : fallback;
}

export function readNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function readBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

export function pickFirstText(...values: unknown[]): string {
  for (const value of values) {
    const text = readText(value);
    if (text) {
      return text;
    }
  }
  return "";
}

export function normalizeLookupKey(value: unknown): string {
  return readText(value)
    .toLowerCase()
    .replace(/[\s_/.-]+/g, "")
    .trim();
}

export function normalizeBlockStatus(value: unknown): ReportPackBlockStatus {
  const normalized = readText(value).toLowerCase();
  if (normalized === "ready") {
    return "ready";
  }
  if (normalized === "attention") {
    return "attention";
  }
  return "pending";
}

export function labelForValidationMode(value: string): string {
  const normalized = value.trim().toLowerCase();
  if (normalized === "mobile_autonomous") {
    return "Autonomia mobile";
  }
  if (normalized === "mobile_review_allowed") {
    return "Revisao mobile";
  }
  if (normalized === "mesa_required") {
    return "Mesa obrigatoria";
  }
  return normalized ? normalized.replace(/_/g, " ") : "Revisao governada";
}

export function labelForBlockStatus(value: ReportPackBlockStatus): string {
  if (value === "ready") {
    return "Pronto";
  }
  if (value === "attention") {
    return "Atencao";
  }
  return "Pendente";
}

export function normalizePreLaudoMinimumEvidence(
  value: unknown,
): MobilePreLaudoMinimumEvidence {
  const record = readRecord(value);
  return {
    fotos: readNumber(record?.fotos),
    documentos: readNumber(record?.documentos),
    textos: readNumber(record?.textos),
  };
}

function normalizePreLaudoSlot(value: unknown): MobilePreLaudoSlot | null {
  const record = readRecord(value);
  if (!record) {
    return null;
  }
  const label = readText(record.label);
  if (!label) {
    return null;
  }
  return {
    slot_id: readText(record.slot_id) || undefined,
    label,
    required: readBoolean(record.required) ?? undefined,
    accepted_types: readStringArray(record.accepted_types),
    binding_path: readText(record.binding_path) || null,
    purpose: readText(record.purpose) || null,
  };
}

function normalizeChecklistGroup(
  value: unknown,
): MobilePreLaudoChecklistGroup | null {
  const record = readRecord(value);
  if (!record) {
    return null;
  }
  const title = readText(record.title);
  if (!title) {
    return null;
  }
  const items = readArrayRecords(record.items).reduce<
    NonNullable<MobilePreLaudoChecklistGroup["items"]>
  >((acc, item) => {
    const itemId = readText(item.item_id);
    const label = readText(item.label);
    if (!itemId || !label) {
      return acc;
    }
    acc.push({
      item_id: itemId,
      label,
      critical: readBoolean(item.critical) ?? undefined,
    });
    return acc;
  }, []);
  return {
    group_id: readText(record.group_id),
    title,
    required: readBoolean(record.required) ?? undefined,
    items,
  };
}

function normalizeDocumentFlowEntry(
  value: unknown,
): MobilePreLaudoDocumentFlowEntry | null {
  const record = readRecord(value);
  if (!record) {
    return null;
  }
  const title = readText(record.title);
  if (!title) {
    return null;
  }
  return {
    key: readText(record.key) || undefined,
    title,
    status: readText(record.status, "pending"),
    status_label: readText(record.status_label) || undefined,
    summary: readText(record.summary) || undefined,
  };
}

function normalizeDocumentSection(
  value: unknown,
): MobilePreLaudoDocumentSection | null {
  const record = readRecord(value);
  if (!record) {
    return null;
  }
  const sectionKey = readText(record.section_key);
  const title = readText(record.title);
  if (!sectionKey || !title) {
    return null;
  }
  const highlights = readArrayRecords(record.highlights).reduce<
    NonNullable<MobilePreLaudoDocumentSection["highlights"]>
  >((acc, item) => {
    const label = readText(item.label);
    if (!label) {
      return acc;
    }
    acc.push({
      path: readText(item.path) || undefined,
      label,
    });
    return acc;
  }, []);
  return {
    section_key: sectionKey,
    title,
    status: readText(record.status, "pending"),
    status_label: readText(record.status_label) || undefined,
    summary: readText(record.summary),
    filled_field_count: readNumber(record.filled_field_count),
    missing_field_count: readNumber(record.missing_field_count),
    total_field_count: readNumber(record.total_field_count),
    highlights,
  };
}

function normalizeExecutiveSection(
  value: unknown,
): MobilePreLaudoExecutiveSection | null {
  const record = readRecord(value);
  if (!record) {
    return null;
  }
  const key = readText(record.key);
  const title = readText(record.title);
  if (!key || !title) {
    return null;
  }
  return {
    key,
    title,
    status: readText(record.status, "pending"),
    summary: readText(record.summary),
    bullets: readStringArray(record.bullets),
  };
}

export function normalizeAnalysisBasisSummary(
  value: unknown,
): MobilePreLaudoAnalysisBasisSummary {
  const record = readRecord(value);
  return {
    coverage_summary: readText(record?.coverage_summary) || null,
    photo_summary: readText(record?.photo_summary) || null,
    document_summary: readText(record?.document_summary) || null,
    context_summary: readText(record?.context_summary) || null,
  };
}

export function normalizePreLaudoDocument(
  value: unknown,
): MobilePreLaudoDocument | null {
  const record = readRecord(value);
  if (!record) {
    return null;
  }
  return {
    contract_name:
      readText(record.contract_name) === "MobilePreLaudoDocumentV1"
        ? "MobilePreLaudoDocumentV1"
        : undefined,
    contract_version:
      readText(record.contract_version) === "v1" ? "v1" : undefined,
    family_key: readText(record.family_key) || null,
    family_label: readText(record.family_label) || null,
    template_key: readText(record.template_key) || null,
    template_label: readText(record.template_label) || null,
    artifact_snapshot: readRecord(record.artifact_snapshot) as
      | Record<string, boolean>
      | undefined,
    document_flow: readArrayRecords(record.document_flow)
      .map((item) => normalizeDocumentFlowEntry(item))
      .filter((item): item is MobilePreLaudoDocumentFlowEntry => item !== null),
    minimum_evidence: normalizePreLaudoMinimumEvidence(record.minimum_evidence),
    required_slots: readArrayRecords(record.required_slots)
      .map((item) => normalizePreLaudoSlot(item))
      .filter((item): item is MobilePreLaudoSlot => item !== null),
    optional_slots: readArrayRecords(record.optional_slots)
      .map((item) => normalizePreLaudoSlot(item))
      .filter((item): item is MobilePreLaudoSlot => item !== null),
    checklist_groups: readArrayRecords(record.checklist_groups)
      .map((item) => normalizeChecklistGroup(item))
      .filter((item): item is MobilePreLaudoChecklistGroup => item !== null),
    review_required: readStringArray(record.review_required),
    executive_sections: readArrayRecords(record.executive_sections)
      .map((item) => normalizeExecutiveSection(item))
      .filter((item): item is MobilePreLaudoExecutiveSection => item !== null),
    document_sections: readArrayRecords(record.document_sections)
      .map((item) => normalizeDocumentSection(item))
      .filter((item): item is MobilePreLaudoDocumentSection => item !== null),
    highlighted_sections: readArrayRecords(record.highlighted_sections)
      .map((item) => normalizeDocumentSection(item))
      .filter((item): item is MobilePreLaudoDocumentSection => item !== null),
    next_questions: readStringArray(record.next_questions),
    analysis_basis_summary: normalizeAnalysisBasisSummary(
      record.analysis_basis_summary,
    ),
    example_available: Boolean(record.example_available),
  };
}
