import { prisma } from "@/lib/server/prisma";

type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";
type CatalogTechnicalStatus = "" | "ready" | "draft" | "deprecated";
type CatalogMaterialLevel = "" | "real_calibrated" | "synthetic" | "none";
type CatalogTab = "visao-geral" | "base" | "oferta" | "calibracao" | "liberacao" | "relatorios";

const CATALOG_TOKEN_PREFIX = "catalog";

const RUNTIME_PREFIX_RULES: Array<[string, string]> = [
  ["nr35_ponto_ancoragem", "nr35_ponto_ancoragem"],
  ["nr35_projeto", "nr35_projeto"],
  ["nr35_montagem", "nr35_montagem"],
  ["nr13", "nr13"],
  ["nr33", "nr33_espaco_confinado"],
  ["nr20", "nr20_instalacoes"],
  ["nr11", "nr11_movimentacao"],
  ["nr10", "rti"],
  ["loto", "loto"],
  ["rti", "rti"],
  ["nr12", "nr12maquinas"],
  ["nr35", "nr35_linha_vida"],
  ["cbmgo", "cbmgo"],
  ["avcb", "avcb"],
  ["spda", "spda"],
  ["pie", "pie"],
];

export interface AdminCatalogListQuery {
  busca?: string | null;
  macroCategoria?: string | null;
  statusTecnico?: string | null;
  materialLevel?: string | null;
  pagina?: string | number | null;
  porPagina?: string | number | null;
}

export interface AdminCatalogFilters {
  busca: string;
  macroCategoria: string;
  statusTecnico: CatalogTechnicalStatus;
  materialLevel: CatalogMaterialLevel;
  pagina: number;
  porPagina: number;
}

export interface AdminCatalogStatusMeta {
  key: string;
  label: string;
  tone: StatusTone;
}

export interface AdminCatalogListItem {
  id: number;
  familyKey: string;
  displayName: string;
  macroCategory: string;
  nrKey: string | null;
  schemaVersion: number;
  classificationLabel: string;
  technicalStatus: AdminCatalogStatusMeta;
  offerLifecycle: AdminCatalogStatusMeta;
  materialLevel: AdminCatalogStatusMeta;
  offerName: string | null;
  packageName: string | null;
  templateDefaultCode: string | null;
  modeCount: number;
  variantCount: number;
  activeReleaseCount: number;
  reportCount: number;
  lastReportAt: Date | null;
  lastReportLabel: string;
  updatedAt: Date | null;
  updatedLabel: string;
}

export interface AdminCatalogListData {
  items: AdminCatalogListItem[];
  totals: {
    totalFamilies: number;
    readyFamilies: number;
    activeOffers: number;
    realCalibratedFamilies: number;
    activeReleases: number;
    totalVariants: number;
  };
  options: {
    macroCategories: string[];
  };
  pagination: {
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
    hasPrev: boolean;
    hasNext: boolean;
    pages: number[];
  };
  filters: AdminCatalogFilters;
}

export interface AdminCatalogVariantItem {
  key: string;
  label: string;
  description: string | null;
  templateCode: string | null;
  runtimeTemplateCode: string | null;
  runtimeTemplateLabel: string;
  selectionToken: string | null;
}

export interface AdminCatalogModeItem {
  id: number;
  key: string;
  label: string;
  description: string | null;
  active: boolean;
  actorLabel: string;
  updatedAt: Date | null;
  updatedLabel: string;
}

export interface AdminCatalogReleaseItem {
  id: number;
  tenantId: number;
  tenantName: string;
  cityState: string | null;
  plan: string;
  releaseStatus: AdminCatalogStatusMeta;
  defaultTemplateCode: string | null;
  modeCount: number;
  templateCount: number;
  variantCount: number;
  observations: string | null;
  allowedTemplates: string[];
  allowedVariants: string[];
  startAt: Date | null;
  startLabel: string;
  endAt: Date | null;
  endLabel: string;
  updatedAt: Date | null;
  updatedLabel: string;
  actorLabel: string;
  governancePreview: string | null;
}

export interface AdminCatalogReportItem {
  id: number;
  companyName: string;
  sector: string;
  reviewStatus: string;
  complianceStatus: string;
  entryMode: string;
  variantLabel: string | null;
  createdAt: Date;
  createdLabel: string;
}

export interface AdminCatalogHistoryItem {
  id: string;
  type: "family" | "offer" | "calibration" | "release";
  typeLabel: string;
  title: string;
  detail: string;
  actorLabel: string;
  when: Date;
  whenLabel: string;
}

export interface AdminCatalogFamilyDetail {
  family: {
    id: number;
    familyKey: string;
    displayName: string;
    description: string | null;
    macroCategory: string;
    nrKey: string | null;
    schemaVersion: number;
    catalogStatus: string;
    classificationLabel: string;
    technicalStatus: AdminCatalogStatusMeta;
    createdAt: Date;
    createdLabel: string;
    updatedAt: Date | null;
    updatedLabel: string;
    actorLabel: string;
  };
  offer: null | {
    name: string;
    description: string | null;
    packageName: string | null;
    templateDefaultCode: string | null;
    prazoPadraoDias: number | null;
    ativoComercial: boolean;
    version: number;
    showcaseEnabled: boolean;
    lifecycle: AdminCatalogStatusMeta;
    materialLevel: AdminCatalogStatusMeta;
    scopeItems: string[];
    exclusionItems: string[];
    minimumInputs: string[];
    variants: AdminCatalogVariantItem[];
    flagsPreview: string | null;
    actorLabel: string;
    updatedAt: Date | null;
    updatedLabel: string;
  };
  calibration: {
    status: AdminCatalogStatusMeta;
    referenceSource: string | null;
    summary: string | null;
    changedLanguageNotes: string | null;
    changedFields: string[];
    attachments: string[];
    actorLabel: string;
    lastCalibratedAt: Date | null;
    lastCalibratedLabel: string;
    rawPreview: string | null;
  };
  base: {
    outputSections: Array<{
      key: string;
      title: string;
      fieldCount: number;
      required: boolean;
    }>;
    requiredSlots: string[];
    optionalSlots: string[];
    reviewRules: string[];
    blockingConditions: string[];
    outputFieldCount: number;
    reviewPolicyPreview: string | null;
    evidencePolicyPreview: string | null;
    outputSchemaPreview: string | null;
    governancePreview: string | null;
  };
  modes: AdminCatalogModeItem[];
  releases: AdminCatalogReleaseItem[];
  recentReports: AdminCatalogReportItem[];
  history: AdminCatalogHistoryItem[];
  summary: {
    modeCount: number;
    variantCount: number;
    releaseCount: number;
    activeReleaseCount: number;
    reportCount: number;
    lastReportAt: Date | null;
    lastReportLabel: string;
    lastUpdatedAt: Date | null;
    lastUpdatedLabel: string;
  };
}

const dateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

function formatDateTime(value: Date | null | undefined, fallback = "Sem registro") {
  return value ? dateTimeFormatter.format(value) : fallback;
}

function normalizeText(value: string | null | undefined) {
  return String(value ?? "").trim();
}

function normalizePage(value: string | number | null | undefined, defaultValue: number, minValue: number, maxValue: number) {
  const parsed = Number(value);

  if (!Number.isFinite(parsed)) {
    return defaultValue;
  }

  return Math.min(maxValue, Math.max(minValue, Math.trunc(parsed)));
}

function normalizeCatalogSlug(value: unknown, maxLength: number) {
  const normalized = String(value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

  return normalized.slice(0, maxLength);
}

function buildCatalogSelectionToken(familyKey: string | null | undefined, variantKey: string) {
  const family = normalizeCatalogSlug(familyKey, 120);
  const variant = normalizeCatalogSlug(variantKey, 80);

  if (!family || !variant) {
    return null;
  }

  return `${CATALOG_TOKEN_PREFIX}:${family}:${variant}`;
}

function resolveRuntimeTemplateCode({
  familyKey,
  templateCode,
  variantKey,
}: {
  familyKey: string | null | undefined;
  templateCode: string | null;
  variantKey: string;
}) {
  const normalizedTemplate = normalizeCatalogSlug(templateCode, 80);

  if (normalizedTemplate) {
    return normalizedTemplate;
  }

  const normalizedFamily = normalizeCatalogSlug(familyKey, 120);
  const normalizedVariant = normalizeCatalogSlug(variantKey, 80);
  const candidates = [normalizedFamily, normalizedVariant].filter(Boolean);

  for (const candidate of candidates) {
    for (const [prefix, runtime] of RUNTIME_PREFIX_RULES) {
      if (candidate.startsWith(prefix)) {
        return runtime;
      }
    }
  }

  return normalizedVariant || normalizedFamily || null;
}

function normalizeTechnicalStatus(value: string | null | undefined): CatalogTechnicalStatus {
  if (value === "ready" || value === "draft" || value === "deprecated") {
    return value;
  }

  return "";
}

function normalizeMaterialLevel(value: string | null | undefined): CatalogMaterialLevel {
  if (value === "real_calibrated" || value === "synthetic" || value === "none") {
    return value;
  }

  return "";
}

export function normalizeCatalogTab(value: string | null | undefined): CatalogTab {
  if (
    value === "visao-geral" ||
    value === "base" ||
    value === "oferta" ||
    value === "calibracao" ||
    value === "liberacao" ||
    value === "relatorios"
  ) {
    return value;
  }

  return "visao-geral";
}

function buildPages(currentPage: number, totalPages: number) {
  if (totalPages <= 1) {
    return [1];
  }

  const start = Math.max(1, currentPage - 2);
  const end = Math.min(totalPages, currentPage + 2);
  const pages: number[] = [];

  for (let page = start; page <= end; page += 1) {
    pages.push(page);
  }

  if (pages[0] !== 1) {
    pages.unshift(1);
  }

  if (pages[pages.length - 1] !== totalPages) {
    pages.push(totalPages);
  }

  return [...new Set(pages)];
}

function toArray(value: unknown) {
  return Array.isArray(value) ? value : [];
}

function toRecord(value: unknown) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function toString(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function toTitleCaseToken(value: string | null | undefined, fallback = "Nao informado") {
  const normalized = normalizeText(value);

  if (!normalized) {
    return fallback;
  }

  return normalized
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.slice(0, 1).toUpperCase() + part.slice(1))
    .join(" ");
}

function actorLabel(user: { nome_completo?: string | null; email?: string | null } | null | undefined, fallback = "Sistema Tariel") {
  const name = normalizeText(user?.nome_completo);

  if (name) {
    return name;
  }

  const email = normalizeText(user?.email);
  return email || fallback;
}

function jsonPreview(value: unknown) {
  if (value == null) {
    return null;
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function toLabelList(value: unknown, preferredKeys: string[]) {
  return toArray(value)
    .map((item) => {
      if (typeof item === "string") {
        return normalizeText(item);
      }

      const record = toRecord(item);

      if (!record) {
        return null;
      }

      for (const key of preferredKeys) {
        const candidate = toString(record[key]);

        if (candidate) {
          return candidate;
        }
      }

      return jsonPreview(record);
    })
    .filter((item): item is string => Boolean(item));
}

function toVariantItems(
  value: unknown,
  options?: {
    familyKey?: string | null;
    templateDefaultCode?: string | null;
  },
): AdminCatalogVariantItem[] {
  const familyKey = normalizeCatalogSlug(options?.familyKey, 120) || null;
  const defaultTemplateCode = normalizeCatalogSlug(options?.templateDefaultCode, 80) || null;

  return toArray(value)
    .map((item, index) => {
      if (typeof item === "string") {
        const label = normalizeText(item);

        if (!label) {
          return null;
        }

        return {
          key: label,
          label,
          description: null,
          templateCode: defaultTemplateCode,
          runtimeTemplateCode: resolveRuntimeTemplateCode({
            familyKey,
            templateCode: defaultTemplateCode,
            variantKey: label,
          }),
          runtimeTemplateLabel: toTitleCaseToken(
            resolveRuntimeTemplateCode({
              familyKey,
              templateCode: defaultTemplateCode,
              variantKey: label,
            }),
            "Nao operacional",
          ),
          selectionToken: buildCatalogSelectionToken(familyKey, label),
        };
      }

      const record = toRecord(item);

      if (!record) {
        return null;
      }

      const key =
        toString(record["variant_key"]) ||
        toString(record["key"]) ||
        toString(record["slug"]) ||
        `variant-${index + 1}`;
      const label =
        toString(record["label"]) ||
        toString(record["nome"]) ||
        toString(record["nome_exibicao"]) ||
        toString(record["display_name"]) ||
        key;
      const description =
        toString(record["description"]) ||
        toString(record["descricao"]) ||
        toString(record["summary"]) ||
        null;
      const templateCode = normalizeCatalogSlug(record["template_code"], 80) || defaultTemplateCode;
      const runtimeTemplateCode = resolveRuntimeTemplateCode({
        familyKey,
        templateCode,
        variantKey: key,
      });

      return {
        key,
        label,
        description,
        templateCode,
        runtimeTemplateCode,
        runtimeTemplateLabel: toTitleCaseToken(runtimeTemplateCode, "Nao operacional"),
        selectionToken: buildCatalogSelectionToken(familyKey, key),
      };
    })
    .filter((item): item is AdminCatalogVariantItem => Boolean(item));
}

function getLatestDate(values: Array<Date | null | undefined>) {
  const validDates = values.filter((value): value is Date => value instanceof Date);

  if (validDates.length === 0) {
    return null;
  }

  return validDates.reduce((latest, current) => (current > latest ? current : latest));
}

function technicalStatusMeta(value: string | null | undefined): AdminCatalogStatusMeta {
  switch (normalizeText(value).toLowerCase()) {
    case "ready":
      return { key: "ready", label: "Pronta", tone: "success" };
    case "deprecated":
      return { key: "deprecated", label: "Arquivada", tone: "danger" };
    default:
      return { key: normalizeText(value).toLowerCase() || "draft", label: "Rascunho", tone: "warning" };
  }
}

function offerLifecycleMeta(value: string | null | undefined): AdminCatalogStatusMeta {
  switch (normalizeText(value).toLowerCase()) {
    case "active":
      return { key: "active", label: "Oferta ativa", tone: "success" };
    case "paused":
      return { key: "paused", label: "Oferta pausada", tone: "warning" };
    case "archived":
      return { key: "archived", label: "Oferta arquivada", tone: "danger" };
    default:
      return { key: normalizeText(value).toLowerCase() || "draft", label: "Oferta em definicao", tone: "neutral" };
  }
}

function materialLevelKey(value: string | null | undefined) {
  const normalized = normalizeText(value).toLowerCase();

  if (normalized === "real_calibrated" || normalized === "synthetic") {
    return normalized;
  }

  return "none";
}

function materialLevelMeta(value: string | null | undefined): AdminCatalogStatusMeta {
  switch (materialLevelKey(value)) {
    case "real_calibrated":
      return { key: "real_calibrated", label: "Material real", tone: "success" };
    case "synthetic":
      return { key: "synthetic", label: "Sintetica", tone: "warning" };
    default:
      return { key: "none", label: "Sem calibracao", tone: "neutral" };
  }
}

function releaseStatusMeta(value: string | null | undefined): AdminCatalogStatusMeta {
  switch (normalizeText(value).toLowerCase()) {
    case "active":
      return { key: "active", label: "Liberada", tone: "success" };
    case "paused":
      return { key: "paused", label: "Pausada", tone: "warning" };
    case "archived":
      return { key: "archived", label: "Arquivada", tone: "danger" };
    default:
      return { key: normalizeText(value).toLowerCase() || "draft", label: "Em preparo", tone: "neutral" };
  }
}

function classificationLabel(value: string | null | undefined) {
  switch (normalizeText(value).toLowerCase()) {
    case "family":
      return "Familia oficial";
    case "template":
      return "Template";
    default:
      return toTitleCaseToken(value);
  }
}

function parseOutputSections(value: unknown) {
  return toArray(toRecord(value)?.["sections"]).map((section, index) => {
    const record = toRecord(section);
    const fields = toArray(record?.["fields"]);
    const key = toString(record?.["section_id"]) || `section-${index + 1}`;
    const title = toString(record?.["title"]) || toTitleCaseToken(key, `Secao ${index + 1}`);

    return {
      key,
      title,
      fieldCount: fields.length,
      required: Boolean(record?.["required"]),
    };
  });
}

function parseRequiredSlots(value: unknown, key: "required_slots" | "optional_slots") {
  return toArray(toRecord(value)?.[key])
    .map((slot, index) => {
      const record = toRecord(slot);
      const label =
        toString(record?.["label"]) ||
        toString(record?.["slot_id"]) ||
        `Slot ${index + 1}`;

      return label;
    })
    .filter(Boolean);
}

export async function getAdminCatalogList(query: AdminCatalogListQuery = {}): Promise<AdminCatalogListData> {
  const filters: AdminCatalogFilters = {
    busca: normalizeText(query.busca),
    macroCategoria: normalizeText(query.macroCategoria),
    statusTecnico: normalizeTechnicalStatus(query.statusTecnico),
    materialLevel: normalizeMaterialLevel(query.materialLevel),
    pagina: normalizePage(query.pagina, 1, 1, 999),
    porPagina: normalizePage(query.porPagina, 12, 6, 48),
  };

  const [familyOptions, families] = await Promise.all([
    prisma.familias_laudo_catalogo.findMany({
      where: {
        catalog_classification: "family",
      },
      select: {
        macro_categoria: true,
      },
      orderBy: {
        macro_categoria: "asc",
      },
    }),
    prisma.familias_laudo_catalogo.findMany({
      where: {
        catalog_classification: "family",
        ...(filters.busca
          ? {
              OR: [
                {
                  family_key: {
                    contains: filters.busca,
                    mode: "insensitive",
                  },
                },
                {
                  nome_exibicao: {
                    contains: filters.busca,
                    mode: "insensitive",
                  },
                },
                {
                  macro_categoria: {
                    contains: filters.busca,
                    mode: "insensitive",
                  },
                },
              ],
            }
          : {}),
        ...(filters.macroCategoria ? { macro_categoria: filters.macroCategoria } : {}),
        ...(filters.statusTecnico ? { technical_status: filters.statusTecnico } : {}),
      },
      orderBy: [{ macro_categoria: "asc" }, { nome_exibicao: "asc" }],
      select: {
        id: true,
        family_key: true,
        nome_exibicao: true,
        macro_categoria: true,
        nr_key: true,
        schema_version: true,
        technical_status: true,
        catalog_classification: true,
        criado_em: true,
        atualizado_em: true,
        familias_laudo_ofertas_comerciais: {
          select: {
            nome_oferta: true,
            pacote_comercial: true,
            lifecycle_status: true,
            material_level: true,
            template_default_code: true,
            variantes_json: true,
            atualizado_em: true,
          },
        },
        familias_laudo_calibracoes: {
          select: {
            calibration_status: true,
            last_calibrated_at: true,
          },
        },
        familias_laudo_modos_tecnicos: {
          select: {
            id: true,
            ativo: true,
          },
        },
        tenant_family_releases: {
          select: {
            id: true,
            release_status: true,
            criado_em: true,
            atualizado_em: true,
          },
        },
      },
    }),
  ]);

  const familyKeys = families.map((family) => family.family_key).filter(Boolean);
  const reportStats = familyKeys.length
    ? await prisma.laudos.groupBy({
        by: ["catalog_family_key"],
        where: {
          catalog_family_key: {
            in: familyKeys,
          },
        },
        _count: {
          _all: true,
        },
        _max: {
          criado_em: true,
        },
      })
    : [];

  const reportMap = new Map(
    reportStats.map((stat) => [
      String(stat.catalog_family_key ?? ""),
      {
        count: stat._count._all,
        lastCreatedAt: stat._max.criado_em,
      },
    ]),
  );

  const mapped = families
    .map((family) => {
      const offer = family.familias_laudo_ofertas_comerciais;
      const calibration = family.familias_laudo_calibracoes;
      const reportInfo = reportMap.get(family.family_key);
      const variants = toVariantItems(offer?.variantes_json, {
        familyKey: family.family_key,
        templateDefaultCode: offer?.template_default_code,
      });
      const material = materialLevelMeta(offer?.material_level ?? calibration?.calibration_status);

      if (filters.materialLevel && material.key !== filters.materialLevel) {
        return null;
      }

      const releases = family.tenant_family_releases;
      const activeReleaseCount = releases.filter((item) => normalizeText(item.release_status).toLowerCase() === "active").length;
      const updatedAt = getLatestDate([
        family.atualizado_em,
        family.criado_em,
        offer?.atualizado_em,
        calibration?.last_calibrated_at,
        ...releases.map((release) => release.atualizado_em ?? release.criado_em),
        reportInfo?.lastCreatedAt,
      ]);

      return {
        id: family.id,
        familyKey: family.family_key,
        displayName: family.nome_exibicao,
        macroCategory: family.macro_categoria ?? "Sem macro",
        nrKey: family.nr_key,
        schemaVersion: family.schema_version,
        classificationLabel: classificationLabel(family.catalog_classification),
        technicalStatus: technicalStatusMeta(family.technical_status),
        offerLifecycle: offerLifecycleMeta(offer?.lifecycle_status),
        materialLevel: material,
        offerName: offer?.nome_oferta ?? null,
        packageName: offer?.pacote_comercial ?? null,
        templateDefaultCode: offer?.template_default_code ?? null,
        modeCount: family.familias_laudo_modos_tecnicos.filter((mode) => mode.ativo).length,
        variantCount: variants.length,
        activeReleaseCount,
        reportCount: reportInfo?.count ?? 0,
        lastReportAt: reportInfo?.lastCreatedAt ?? null,
        lastReportLabel: formatDateTime(reportInfo?.lastCreatedAt, "Sem laudos emitidos"),
        updatedAt,
        updatedLabel: formatDateTime(updatedAt),
      } satisfies AdminCatalogListItem;
    })
    .filter((item): item is AdminCatalogListItem => Boolean(item));

  const totalItems = mapped.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / filters.porPagina));
  const currentPage = Math.min(filters.pagina, totalPages);
  const start = (currentPage - 1) * filters.porPagina;
  const items = mapped.slice(start, start + filters.porPagina);

  return {
    items,
    totals: {
      totalFamilies: mapped.length,
      readyFamilies: mapped.filter((item) => item.technicalStatus.key === "ready").length,
      activeOffers: mapped.filter((item) => item.offerLifecycle.key === "active").length,
      realCalibratedFamilies: mapped.filter((item) => item.materialLevel.key === "real_calibrated").length,
      activeReleases: mapped.reduce((total, item) => total + item.activeReleaseCount, 0),
      totalVariants: mapped.reduce((total, item) => total + item.variantCount, 0),
    },
    options: {
      macroCategories: [
        ...new Set(
          familyOptions
            .map((item) => item.macro_categoria)
            .filter((item): item is string => Boolean(item)),
        ),
      ],
    },
    pagination: {
      page: currentPage,
      pageSize: filters.porPagina,
      totalItems,
      totalPages,
      hasPrev: currentPage > 1,
      hasNext: currentPage < totalPages,
      pages: buildPages(currentPage, totalPages),
    },
    filters: {
      ...filters,
      pagina: currentPage,
    },
  };
}

export async function getAdminCatalogFamilyDetail(familyKey: string): Promise<AdminCatalogFamilyDetail | null> {
  const normalizedFamilyKey = normalizeText(familyKey).toLowerCase();

  if (!normalizedFamilyKey) {
    return null;
  }

  const [family, reportCount, recentReports] = await Promise.all([
    prisma.familias_laudo_catalogo.findFirst({
      where: {
        family_key: normalizedFamilyKey,
        catalog_classification: "family",
      },
      select: {
        id: true,
        family_key: true,
        nome_exibicao: true,
        descricao: true,
        macro_categoria: true,
        nr_key: true,
        schema_version: true,
        technical_status: true,
        status_catalogo: true,
        catalog_classification: true,
        review_policy_json: true,
        evidence_policy_json: true,
        output_schema_seed_json: true,
        governance_metadata_json: true,
        criado_em: true,
        atualizado_em: true,
        usuarios: {
          select: {
            nome_completo: true,
            email: true,
          },
        },
        familias_laudo_ofertas_comerciais: {
          select: {
            id: true,
            nome_oferta: true,
            descricao_comercial: true,
            pacote_comercial: true,
            prazo_padrao_dias: true,
            ativo_comercial: true,
            versao_oferta: true,
            lifecycle_status: true,
            material_level: true,
            showcase_enabled: true,
            template_default_code: true,
            escopo_json: true,
            exclusoes_json: true,
            insumos_minimos_json: true,
            variantes_json: true,
            flags_json: true,
            criado_em: true,
            atualizado_em: true,
            usuarios: {
              select: {
                nome_completo: true,
                email: true,
              },
            },
          },
        },
        familias_laudo_calibracoes: {
          select: {
            calibration_status: true,
            reference_source: true,
            summary_of_adjustments: true,
            changed_language_notes: true,
            changed_fields_json: true,
            attachments_json: true,
            last_calibrated_at: true,
            criado_em: true,
            atualizado_em: true,
            usuarios: {
              select: {
                nome_completo: true,
                email: true,
              },
            },
          },
        },
        familias_laudo_modos_tecnicos: {
          orderBy: [{ ativo: "desc" }, { nome_exibicao: "asc" }],
          select: {
            id: true,
            mode_key: true,
            nome_exibicao: true,
            descricao: true,
            ativo: true,
            criado_em: true,
            atualizado_em: true,
            usuarios: {
              select: {
                nome_completo: true,
                email: true,
              },
            },
          },
        },
        tenant_family_releases: {
          orderBy: [{ tenant_id: "asc" }],
          select: {
            id: true,
            tenant_id: true,
            default_template_code: true,
            release_status: true,
            start_at: true,
            end_at: true,
            observacoes: true,
            allowed_modes_json: true,
            allowed_templates_json: true,
            allowed_variants_json: true,
            governance_policy_json: true,
            criado_em: true,
            atualizado_em: true,
            usuarios: {
              select: {
                nome_completo: true,
                email: true,
              },
            },
            empresas: {
              select: {
                id: true,
                nome_fantasia: true,
                cidade_estado: true,
                plano_ativo: true,
              },
            },
          },
        },
      },
    }),
    prisma.laudos.count({
      where: {
        catalog_family_key: normalizedFamilyKey,
      },
    }),
    prisma.laudos.findMany({
      where: {
        catalog_family_key: normalizedFamilyKey,
      },
      orderBy: {
        criado_em: "desc",
      },
      take: 8,
      select: {
        id: true,
        setor_industrial: true,
        status_revisao: true,
        status_conformidade: true,
        entry_mode_effective: true,
        catalog_variant_label: true,
        catalog_variant_key: true,
        criado_em: true,
        empresas: {
          select: {
            nome_fantasia: true,
          },
        },
      },
    }),
  ]);

  if (!family) {
    return null;
  }

  const offer = family.familias_laudo_ofertas_comerciais;
  const calibration = family.familias_laudo_calibracoes;
  const outputSections = parseOutputSections(family.output_schema_seed_json);
  const variants = toVariantItems(offer?.variantes_json, {
    familyKey: family.family_key,
    templateDefaultCode: offer?.template_default_code,
  });
  const reviewRules = toLabelList(toRecord(family.review_policy_json)?.["review_required"], []);
  const blockingConditions = toLabelList(toRecord(family.review_policy_json)?.["blocking_conditions"], []);
  const requiredSlots = parseRequiredSlots(family.evidence_policy_json, "required_slots");
  const optionalSlots = parseRequiredSlots(family.evidence_policy_json, "optional_slots");
  const modes = family.familias_laudo_modos_tecnicos.map((mode) => ({
    id: mode.id,
    key: mode.mode_key,
    label: mode.nome_exibicao,
    description: mode.descricao,
    active: mode.ativo,
    actorLabel: actorLabel(mode.usuarios),
    updatedAt: mode.atualizado_em ?? mode.criado_em,
    updatedLabel: formatDateTime(mode.atualizado_em ?? mode.criado_em),
  }));
  const releases = family.tenant_family_releases.map((release) => ({
    id: release.id,
    tenantId: release.tenant_id,
    tenantName: release.empresas.nome_fantasia,
    cityState: release.empresas.cidade_estado,
    plan: release.empresas.plano_ativo,
    releaseStatus: releaseStatusMeta(release.release_status),
    defaultTemplateCode: release.default_template_code,
    modeCount: toArray(release.allowed_modes_json).length,
    templateCount: toArray(release.allowed_templates_json).length,
    variantCount: toArray(release.allowed_variants_json).length,
    observations: normalizeText(release.observacoes) || null,
    allowedTemplates: toArray(release.allowed_templates_json)
      .map((item) => normalizeCatalogSlug(item, 80))
      .filter((item): item is string => Boolean(item)),
    allowedVariants: variants
      .filter((variant) => {
        const allowed = toArray(release.allowed_variants_json)
          .map((item) => String(item ?? "").trim().toLowerCase())
          .filter(Boolean);

        return Boolean(
          variant.selectionToken &&
            (allowed.includes(variant.selectionToken) || allowed.includes(variant.key.toLowerCase())),
        );
      })
      .map((variant) => variant.selectionToken!)
      .filter(Boolean),
    startAt: release.start_at,
    startLabel: formatDateTime(release.start_at, "Imediato"),
    endAt: release.end_at,
    endLabel: formatDateTime(release.end_at, "Sem expiracao"),
    updatedAt: release.atualizado_em ?? release.criado_em,
    updatedLabel: formatDateTime(release.atualizado_em ?? release.criado_em),
    actorLabel: actorLabel(release.usuarios),
    governancePreview: jsonPreview(release.governance_policy_json),
  }));
  const lastReportAt = recentReports[0]?.criado_em ?? null;
  const lastUpdatedAt = getLatestDate([
    family.atualizado_em,
    family.criado_em,
    offer?.atualizado_em,
    offer?.criado_em,
    calibration?.last_calibrated_at,
    calibration?.atualizado_em,
    ...releases.map((release) => release.updatedAt),
    lastReportAt,
  ]);

  const history: AdminCatalogHistoryItem[] = [
    {
      id: `family-${family.id}`,
      type: "family" as const,
      typeLabel: "Familia",
      title: "Familia catalogada",
      detail: `${family.nome_exibicao} ficou em ${technicalStatusMeta(family.technical_status).label.toLowerCase()}.`,
      actorLabel: actorLabel(family.usuarios),
      when: family.atualizado_em ?? family.criado_em,
      whenLabel: formatDateTime(family.atualizado_em ?? family.criado_em),
    },
    ...(offer
      ? [
          {
            id: `offer-${offer.id}`,
            type: "offer" as const,
            typeLabel: "Oferta",
            title: "Pacote comercial atualizado",
            detail: `${offer.nome_oferta} esta em ${offerLifecycleMeta(offer.lifecycle_status).label.toLowerCase()}.`,
            actorLabel: actorLabel(offer.usuarios),
            when: offer.atualizado_em ?? offer.criado_em,
            whenLabel: formatDateTime(offer.atualizado_em ?? offer.criado_em),
          },
        ]
      : []),
    ...(calibration?.last_calibrated_at
      ? [
          {
            id: `calibration-${family.id}`,
            type: "calibration" as const,
            typeLabel: "Calibracao",
            title: "Material e validacao revisados",
            detail: materialLevelMeta(offer?.material_level ?? calibration.calibration_status).label,
            actorLabel: actorLabel(calibration.usuarios),
            when: calibration.last_calibrated_at,
            whenLabel: formatDateTime(calibration.last_calibrated_at),
          },
        ]
      : []),
    ...releases.map((release) => ({
      id: `release-${release.id}`,
      type: "release" as const,
      typeLabel: "Liberacao",
      title: "Tenant liberado para uso",
      detail: `${release.tenantName} em ${release.releaseStatus.label.toLowerCase()}.`,
      actorLabel: release.actorLabel,
      when: release.updatedAt ?? new Date(),
      whenLabel: release.updatedLabel,
    })),
  ].sort((left, right) => right.when.getTime() - left.when.getTime());

  return {
    family: {
      id: family.id,
      familyKey: family.family_key,
      displayName: family.nome_exibicao,
      description: normalizeText(family.descricao) || null,
      macroCategory: family.macro_categoria ?? "Sem macro",
      nrKey: family.nr_key,
      schemaVersion: family.schema_version,
      catalogStatus: family.status_catalogo,
      classificationLabel: classificationLabel(family.catalog_classification),
      technicalStatus: technicalStatusMeta(family.technical_status),
      createdAt: family.criado_em,
      createdLabel: formatDateTime(family.criado_em),
      updatedAt: family.atualizado_em,
      updatedLabel: formatDateTime(family.atualizado_em ?? family.criado_em),
      actorLabel: actorLabel(family.usuarios),
    },
    offer: offer
      ? {
          name: offer.nome_oferta,
          description: normalizeText(offer.descricao_comercial) || null,
          packageName: normalizeText(offer.pacote_comercial) || null,
          templateDefaultCode: normalizeText(offer.template_default_code) || null,
          prazoPadraoDias: offer.prazo_padrao_dias,
          ativoComercial: offer.ativo_comercial,
          version: offer.versao_oferta,
          showcaseEnabled: offer.showcase_enabled,
          lifecycle: offerLifecycleMeta(offer.lifecycle_status),
          materialLevel: materialLevelMeta(offer.material_level),
          scopeItems: toLabelList(offer.escopo_json, ["label", "title", "name"]),
          exclusionItems: toLabelList(offer.exclusoes_json, ["label", "title", "name"]),
          minimumInputs: toLabelList(offer.insumos_minimos_json, ["label", "title", "name", "field_id", "slot_id"]),
          variants,
          flagsPreview: jsonPreview(offer.flags_json),
          actorLabel: actorLabel(offer.usuarios),
          updatedAt: offer.atualizado_em ?? offer.criado_em,
          updatedLabel: formatDateTime(offer.atualizado_em ?? offer.criado_em),
        }
      : null,
    calibration: {
      status: materialLevelMeta(offer?.material_level ?? calibration?.calibration_status),
      referenceSource: normalizeText(calibration?.reference_source) || null,
      summary: normalizeText(calibration?.summary_of_adjustments) || null,
      changedLanguageNotes: normalizeText(calibration?.changed_language_notes) || null,
      changedFields: toLabelList(calibration?.changed_fields_json, []),
      attachments: toLabelList(calibration?.attachments_json, ["label", "name", "path"]),
      actorLabel: actorLabel(calibration?.usuarios),
      lastCalibratedAt: calibration?.last_calibrated_at ?? null,
      lastCalibratedLabel: formatDateTime(calibration?.last_calibrated_at, "Sem calibracao registrada"),
      rawPreview: jsonPreview({
        calibration_status: calibration?.calibration_status ?? null,
        reference_source: calibration?.reference_source ?? null,
        changed_fields_json: calibration?.changed_fields_json ?? null,
        attachments_json: calibration?.attachments_json ?? null,
      }),
    },
    base: {
      outputSections,
      requiredSlots,
      optionalSlots,
      reviewRules,
      blockingConditions,
      outputFieldCount: outputSections.reduce((total, section) => total + section.fieldCount, 0),
      reviewPolicyPreview: jsonPreview(family.review_policy_json),
      evidencePolicyPreview: jsonPreview(family.evidence_policy_json),
      outputSchemaPreview: jsonPreview(family.output_schema_seed_json),
      governancePreview: jsonPreview(family.governance_metadata_json),
    },
    modes,
    releases,
    recentReports: recentReports.map((report) => ({
      id: report.id,
      companyName: report.empresas.nome_fantasia,
      sector: report.setor_industrial,
      reviewStatus: report.status_revisao,
      complianceStatus: report.status_conformidade,
      entryMode: report.entry_mode_effective,
      variantLabel: normalizeText(report.catalog_variant_label) || normalizeText(report.catalog_variant_key) || null,
      createdAt: report.criado_em,
      createdLabel: formatDateTime(report.criado_em),
    })),
    history,
    summary: {
      modeCount: modes.length,
      variantCount: variants.length,
      releaseCount: releases.length,
      activeReleaseCount: releases.filter((release) => release.releaseStatus.key === "active").length,
      reportCount,
      lastReportAt,
      lastReportLabel: formatDateTime(lastReportAt, "Sem laudos emitidos"),
      lastUpdatedAt,
      lastUpdatedLabel: formatDateTime(lastUpdatedAt),
    },
  };
}
