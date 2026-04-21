import type { MobileReportPackDraftSummary } from "./reportPackHelpers";

export type QualityGateStatusTone = "success" | "accent" | "danger";
export type QualityGateStatusIcon =
  | "check-decagram-outline"
  | "shield-check-outline"
  | "alert-circle-outline";

export interface QualityGateStatusSummary {
  description: string;
  icon: QualityGateStatusIcon;
  label: string;
  tone: QualityGateStatusTone;
}

export interface QualityGateSummaryChip {
  key: string;
  label: string;
}

export function resumoNumero(
  value: string | number | boolean | null | undefined,
): string | null {
  if (typeof value === "number") {
    return String(value);
  }
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  return null;
}

export function rotuloModoValidacao(value: string | null | undefined): string {
  const normalized = String(value || "")
    .trim()
    .toLowerCase();
  if (normalized === "mesa_required") {
    return "Mesa obrigatória";
  }
  if (normalized === "mobile_review_allowed") {
    return "Revisão mobile";
  }
  if (normalized === "mobile_autonomous") {
    return "Autonomia mobile";
  }
  return normalized ? normalized.replace(/_/g, " ") : "Revisão governada";
}

export function buildQualityGateStatusSummary(params: {
  approved: boolean;
  blockingCount: number;
  overrideAvailable: boolean;
}): QualityGateStatusSummary {
  if (params.approved) {
    return {
      description:
        "Checklist, pacote documental e política do caso já permitem seguir para a decisão humana rastreável.",
      icon: "check-decagram-outline",
      label: "Pronto para concluir",
      tone: "success",
    };
  }

  if (params.overrideAvailable) {
    return {
      description:
        "O caso continua bloqueado, mas existe trilha de exceção governada com justificativa interna.",
      icon: "shield-check-outline",
      label: "Exceção governada disponível",
      tone: "accent",
    };
  }

  return {
    description:
      params.blockingCount > 0
        ? "Ainda existem pendências objetivas no pré-laudo ou na política de revisão antes da emissão."
        : "A validação ainda não liberou a emissão governada deste caso.",
    icon: "alert-circle-outline",
    label: "Correção obrigatória",
    tone: "danger",
  };
}

export function buildQualityGateSummaryChips(params: {
  blockingCount: number;
  payloadTemplateName?: string | null;
  reportPackSummary: MobileReportPackDraftSummary | null;
  reviewModeLabel: string;
}): QualityGateSummaryChip[] {
  return [
    {
      key: "template",
      label:
        params.reportPackSummary?.templateLabel ||
        params.payloadTemplateName ||
        "Template",
    },
    {
      key: "review-mode",
      label: params.reviewModeLabel,
    },
    {
      key: "blockers",
      label:
        params.blockingCount > 0
          ? `${params.blockingCount} pendência${params.blockingCount === 1 ? "" : "s"}`
          : "Sem bloqueios",
    },
  ];
}
