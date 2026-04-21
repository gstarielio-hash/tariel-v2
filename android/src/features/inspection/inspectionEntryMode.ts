import type {
  MobileInspectionEntryModeEffective,
  MobileInspectionEntryModePreference,
  MobileLaudoCard,
} from "../../types/mobile";

export interface InspectionEntryModeResolution {
  effective: MobileInspectionEntryModeEffective;
  preference: MobileInspectionEntryModePreference;
  reason: string;
}

interface InspectionEntryModeStateLike {
  entry_mode_effective?: MobileInspectionEntryModeEffective | null;
  entry_mode_preference?: MobileInspectionEntryModePreference | null;
  entry_mode_reason?: string | null;
}

interface ResolveInspectionEntryModeInput {
  activeCase?: InspectionEntryModeStateLike | null;
  cards?: InspectionEntryModeStateLike[] | MobileLaudoCard[];
  includeActiveCase?: boolean;
  preference?: MobileInspectionEntryModePreference | null;
  rememberLastCaseMode?: boolean;
}

function normalizePreference(
  value: MobileInspectionEntryModePreference | null | undefined,
): MobileInspectionEntryModePreference {
  if (
    value === "chat_first" ||
    value === "evidence_first" ||
    value === "auto_recommended"
  ) {
    return value;
  }
  return "auto_recommended";
}

function findLastCaseMode(
  cards: ResolveInspectionEntryModeInput["cards"],
): InspectionEntryModeStateLike | null {
  if (!Array.isArray(cards)) {
    return null;
  }
  return (
    cards.find(
      (item) =>
        item?.entry_mode_effective === "chat_first" ||
        item?.entry_mode_effective === "evidence_first",
    ) || null
  );
}

export function reasonLabelForInspectionEntryMode(reason: string): string {
  switch (reason) {
    case "existing_case_state":
      return "Modo salvo no caso";
    case "user_preference":
      return "Preferencia do inspetor";
    case "last_case_mode":
      return "Ultimo caso retomado";
    default:
      return "Padrao operacional";
  }
}

export function resolveInspectionEntryMode({
  activeCase,
  cards = [],
  includeActiveCase = true,
  preference,
  rememberLastCaseMode = false,
}: ResolveInspectionEntryModeInput): InspectionEntryModeResolution {
  const normalizedPreference = normalizePreference(preference);
  if (
    includeActiveCase &&
    activeCase?.entry_mode_effective &&
    (activeCase.entry_mode_effective === "chat_first" ||
      activeCase.entry_mode_effective === "evidence_first")
  ) {
    return {
      effective: activeCase.entry_mode_effective,
      preference: normalizePreference(
        activeCase.entry_mode_preference || normalizedPreference,
      ),
      reason: activeCase.entry_mode_reason || "existing_case_state",
    };
  }

  if (normalizedPreference === "chat_first") {
    return {
      effective: "chat_first",
      preference: normalizedPreference,
      reason: "user_preference",
    };
  }

  if (normalizedPreference === "evidence_first") {
    return {
      effective: "evidence_first",
      preference: normalizedPreference,
      reason: "user_preference",
    };
  }

  if (rememberLastCaseMode) {
    const lastCase = findLastCaseMode(cards);
    if (lastCase?.entry_mode_effective) {
      return {
        effective: lastCase.entry_mode_effective,
        preference: normalizedPreference,
        reason: lastCase.entry_mode_reason || "last_case_mode",
      };
    }
  }

  return {
    effective: "chat_first",
    preference: normalizedPreference,
    reason: "default_product_fallback",
  };
}
