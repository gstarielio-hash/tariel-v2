import type {
  MobilePreLaudoDocumentFlowEntry,
  MobilePreLaudoDocumentSection,
  MobilePreLaudoExecutiveSection,
  MobilePreLaudoSlot,
} from "../../types/mobile";

import type {
  MobileReportPackBlockSummary,
  MobileReportPackExecutiveSummary,
  MobileReportPackFlowSummary,
  MobileReportPackSectionSummary,
  MobileReportPackSlotSummary,
  ReportPackBlockStatus,
} from "./reportPackHelperTypes";
import {
  type JsonRecord,
  labelForBlockStatus,
  normalizeBlockStatus,
  normalizeLookupKey,
  pickFirstText,
  readBoolean,
  readRecord,
  readStringArray,
  readText,
} from "./reportPackHelperReaders";

export function buildBlockSummary(
  key: string,
  title: string,
  status: ReportPackBlockStatus,
  summary: string,
): MobileReportPackBlockSummary {
  return {
    key,
    title,
    status,
    statusLabel: labelForBlockStatus(status),
    summary,
  };
}

export function buildFlowSummaries(
  entries: MobilePreLaudoDocumentFlowEntry[],
): MobileReportPackFlowSummary[] {
  return entries.map((item, index) => {
    const status = normalizeBlockStatus(item.status);
    return {
      key: item.key || `flow-${index}`,
      title: item.title,
      status,
      statusLabel: item.status_label || labelForBlockStatus(status),
      summary:
        item.summary ||
        `${item.title} ${status === "ready" ? "pronto" : "pendente"} no catálogo.`,
    };
  });
}

export function buildDocumentSectionSummaries(
  sections: MobilePreLaudoDocumentSection[],
): MobileReportPackSectionSummary[] {
  return sections.map((item) => {
    const status = normalizeBlockStatus(item.status);
    const highlights = (item.highlights || [])
      .map((highlight) => readText(highlight.label))
      .filter(Boolean)
      .slice(0, 3);
    return {
      key: item.section_key,
      title: item.title,
      status,
      statusLabel: item.status_label || labelForBlockStatus(status),
      summary:
        item.summary ||
        `${item.filled_field_count}/${item.total_field_count} campos preenchidos.`,
      filledFieldCount: item.filled_field_count,
      missingFieldCount: item.missing_field_count,
      totalFieldCount: item.total_field_count,
      highlights,
    };
  });
}

export function buildExecutiveSummaries(
  sections: MobilePreLaudoExecutiveSection[],
): MobileReportPackExecutiveSummary[] {
  return sections.map((item) => {
    const status = normalizeBlockStatus(item.status);
    return {
      key: item.key,
      title: item.title,
      status,
      statusLabel: labelForBlockStatus(status),
      summary: item.summary,
      bullets: (item.bullets || []).filter(Boolean).slice(0, 3),
    };
  });
}

export function resolveRuntimeSlot(
  policySlot: MobilePreLaudoSlot,
  runtimeSlots: JsonRecord[],
  index: number,
): JsonRecord | null {
  const policyKey = normalizeLookupKey(
    policySlot.slot_id || policySlot.binding_path || policySlot.label,
  );
  if (policyKey) {
    const matched = runtimeSlots.find((item) => {
      const runtimeKeys = [
        normalizeLookupKey(item.slot),
        normalizeLookupKey(item.title),
        normalizeLookupKey(item.step_id),
      ].filter(Boolean);
      return runtimeKeys.includes(policyKey);
    });
    if (matched) {
      return matched;
    }
  }
  return runtimeSlots[index] || null;
}

export function buildPolicySlotSummary(
  slot: MobilePreLaudoSlot,
  runtimeSlot: JsonRecord | null,
  index: number,
): MobileReportPackSlotSummary {
  const runtimeStatus = normalizeBlockStatus(runtimeSlot?.status);
  const required = slot.required !== false;
  const resolved = runtimeStatus === "ready";
  const title = readText(runtimeSlot?.title);
  const resolvedCaption = readText(runtimeSlot?.resolved_caption);
  const summary = resolved
    ? pickFirstText(
        resolvedCaption,
        title,
        slot.purpose,
        "Evidencia vinculada ao slot canônico.",
      )
    : pickFirstText(
        slot.purpose,
        title,
        "Ainda falta evidência para este slot canônico.",
      );
  return {
    key: slot.slot_id || `slot-${index}`,
    label: slot.label,
    status: runtimeSlot ? runtimeStatus : "pending",
    statusLabel: labelForBlockStatus(runtimeSlot ? runtimeStatus : "pending"),
    required,
    acceptedTypes: (slot.accepted_types || []).slice(0, 4),
    bindingPath: slot.binding_path || "",
    purpose: slot.purpose || "",
    summary,
    resolved,
  };
}

export function buildRuntimeSlotSummary(
  value: unknown,
  index: number,
): MobileReportPackSlotSummary | null {
  const record = readRecord(value);
  if (!record) {
    return null;
  }
  const status = normalizeBlockStatus(record.status);
  const label = pickFirstText(record.title, record.slot);
  if (!label) {
    return null;
  }
  const resolvedCaption = readText(record.resolved_caption);
  const missingEvidence = readStringArray(record.missing_evidence);
  return {
    key: readText(record.slot) || `runtime-slot-${index}`,
    label,
    status,
    statusLabel: labelForBlockStatus(status),
    required: readBoolean(record.required) ?? true,
    acceptedTypes: [],
    bindingPath: readText(record.step_id),
    purpose: "",
    summary:
      resolvedCaption ||
      (missingEvidence.length
        ? `Pendência: ${missingEvidence.join(", ")}.`
        : status === "ready"
          ? "Evidência visual consolidada."
          : "Slot visual ainda não resolvido."),
    resolved: status === "ready",
  };
}
