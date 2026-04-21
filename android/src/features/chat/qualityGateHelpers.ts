import type {
  MobileHumanOverrideCandidateItem,
  MobileHumanOverridePolicy,
  MobileQualityGateItem,
  MobileQualityGateResponse,
  MobileQualityGateTemplateGuide,
  MobileQualityGateTemplateItem,
} from "../../types/mobile";

export const QUALITY_GATE_OVERRIDE_MIN_REASON_LENGTH = 12;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function normalizePrimitiveValue(
  value: unknown,
): string | number | boolean | null {
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return value;
  }
  return null;
}

function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const seen = new Set<string>();
  const items: string[] = [];
  value.forEach((item) => {
    const text = String(item || "").trim();
    if (!text) {
      return;
    }
    const key = text.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    items.push(text);
  });
  return items;
}

function normalizeQualityGateItem(
  value: unknown,
): MobileQualityGateItem | null {
  if (!isRecord(value)) {
    return null;
  }
  const id = String(value.id || "").trim();
  const titulo = String(value.titulo || "").trim();
  if (!id || !titulo) {
    return null;
  }
  return {
    id,
    categoria: String(value.categoria || "").trim(),
    titulo,
    status: String(value.status || "").trim() || "faltante",
    atual: normalizePrimitiveValue(value.atual),
    minimo: normalizePrimitiveValue(value.minimo),
    observacao: String(value.observacao || "").trim(),
  };
}

function normalizeTemplateItem(
  value: unknown,
): MobileQualityGateTemplateItem | null {
  if (!isRecord(value)) {
    return null;
  }
  const id = String(value.id || "").trim();
  const titulo = String(value.titulo || "").trim();
  if (!id || !titulo) {
    return null;
  }
  return {
    id,
    categoria: String(value.categoria || "").trim(),
    titulo,
    descricao: String(value.descricao || "").trim(),
    obrigatorio: value.obrigatorio !== false,
  };
}

function normalizeTemplateGuide(
  value: unknown,
): MobileQualityGateTemplateGuide | null {
  if (!isRecord(value)) {
    return null;
  }
  const titulo = String(value.titulo || "").trim();
  const itens = Array.isArray(value.itens)
    ? value.itens
        .map((item) => normalizeTemplateItem(item))
        .filter((item): item is MobileQualityGateTemplateItem => Boolean(item))
    : [];
  if (!titulo && !itens.length) {
    return null;
  }
  return {
    titulo: titulo || "Roteiro obrigatório do template",
    descricao: String(value.descricao || "").trim(),
    itens,
  };
}

function normalizeCandidateItem(
  value: unknown,
): MobileHumanOverrideCandidateItem | null {
  if (!isRecord(value)) {
    return null;
  }
  const id = String(value.id || "").trim();
  const titulo = String(value.titulo || "").trim();
  if (!id || !titulo) {
    return null;
  }
  return {
    id,
    titulo,
    categoria: String(value.categoria || "").trim(),
    candidate_cases: normalizeStringArray(value.candidate_cases),
    candidate_case_labels: normalizeStringArray(value.candidate_case_labels),
  };
}

function normalizeOverridePolicy(
  value: unknown,
): MobileHumanOverridePolicy | null {
  if (!isRecord(value)) {
    return null;
  }
  return {
    available: Boolean(value.available),
    reason_required: Boolean(value.reason_required),
    allowed_override_cases: normalizeStringArray(value.allowed_override_cases),
    allowed_override_case_labels: normalizeStringArray(
      value.allowed_override_case_labels,
    ),
    matched_override_cases: normalizeStringArray(value.matched_override_cases),
    matched_override_case_labels: normalizeStringArray(
      value.matched_override_case_labels,
    ),
    overrideable_items: Array.isArray(value.overrideable_items)
      ? value.overrideable_items
          .map((item) => normalizeCandidateItem(item))
          .filter((item): item is MobileHumanOverrideCandidateItem =>
            Boolean(item),
          )
      : [],
    hard_blockers: Array.isArray(value.hard_blockers)
      ? value.hard_blockers
          .map((item) => normalizeCandidateItem(item))
          .filter((item): item is MobileHumanOverrideCandidateItem =>
            Boolean(item),
          )
      : [],
    family_key: String(value.family_key || "").trim(),
    responsibility_notice: String(value.responsibility_notice || "").trim(),
    message: String(value.message || "").trim(),
    requested: Boolean(value.requested),
    validation_error: String(value.validation_error || "").trim() || undefined,
  };
}

export function normalizarQualityGateResponse(
  value: unknown,
): MobileQualityGateResponse | null {
  if (!isRecord(value)) {
    return null;
  }
  const codigo = String(value.codigo || "").trim();
  const mensagem = String(value.mensagem || "").trim();
  const templateNome = String(value.template_nome || "").trim();
  if (!codigo || !("aprovado" in value)) {
    return null;
  }
  const resumo = isRecord(value.resumo)
    ? (Object.fromEntries(
        Object.entries(value.resumo).map(([key, item]) => [
          key,
          normalizePrimitiveValue(item),
        ]),
      ) as Record<string, string | number | boolean | null | undefined>)
    : {};
  return {
    codigo,
    aprovado: Boolean(value.aprovado),
    mensagem,
    tipo_template: String(value.tipo_template || "").trim(),
    template_nome: templateNome,
    resumo,
    itens: Array.isArray(value.itens)
      ? value.itens
          .map((item) => normalizeQualityGateItem(item))
          .filter((item): item is MobileQualityGateItem => Boolean(item))
      : [],
    faltantes: Array.isArray(value.faltantes)
      ? value.faltantes
          .map((item) => normalizeQualityGateItem(item))
          .filter((item): item is MobileQualityGateItem => Boolean(item))
      : [],
    roteiro_template: normalizeTemplateGuide(value.roteiro_template),
    report_pack_draft: isRecord(value.report_pack_draft)
      ? value.report_pack_draft
      : null,
    review_mode_sugerido:
      String(value.review_mode_sugerido || "").trim() || null,
    human_override_policy: normalizeOverridePolicy(value.human_override_policy),
  };
}

export function qualityGatePermiteOverride(
  payload: MobileQualityGateResponse | null | undefined,
): boolean {
  return Boolean(payload?.human_override_policy?.available);
}

export function resolverQualityGateRequestedCases(
  payload: MobileQualityGateResponse | null | undefined,
): string[] {
  const matched = normalizeStringArray(
    payload?.human_override_policy?.matched_override_cases,
  );
  if (matched.length) {
    return matched;
  }
  return normalizeStringArray(
    payload?.human_override_policy?.allowed_override_cases,
  );
}

export function resolverQualityGateResponsibilityNotice(
  payload: MobileQualityGateResponse | null | undefined,
): string {
  return (
    String(
      payload?.human_override_policy?.responsibility_notice || "",
    ).trim() ||
    "A justificativa fica na trilha interna do caso e a responsabilidade final continua sendo humana."
  );
}
