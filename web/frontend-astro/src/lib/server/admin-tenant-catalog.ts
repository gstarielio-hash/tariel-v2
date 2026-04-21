import { prisma } from "@/lib/server/prisma";

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

export interface AdminTenantCatalogVariantItem {
  selectionToken: string;
  variantKey: string;
  variantLabel: string;
  templateCode: string | null;
  runtimeTemplateCode: string | null;
  runtimeTemplateLabel: string;
  recommendedUse: string | null;
  isActive: boolean;
  isOperational: boolean;
  isSelectableForTenant: boolean;
  availabilityState: "active" | "blocked" | "available" | "unmapped";
  availabilityReason: string | null;
}

export interface AdminTenantCatalogTemplateOption {
  code: string;
  label: string;
}

export interface AdminTenantCatalogReleaseSummary {
  exists: boolean;
  releaseStatus: {
    key: string;
    label: string;
  };
  defaultTemplateCode: string | null;
  allowedTemplates: string[];
  allowedVariants: string[];
  observations: string | null;
}

export interface AdminTenantCatalogFamilyItem {
  familyId: number;
  familyKey: string;
  familyLabel: string;
  familyDescription: string | null;
  groupLabel: string;
  offerId: number;
  offerKey: string | null;
  offerName: string;
  offerPackage: string | null;
  offerDeadlineDays: number | null;
  templateDefaultCode: string | null;
  releaseStatus: {
    key: string;
    label: string;
  };
  templateOptions: AdminTenantCatalogTemplateOption[];
  tenantRelease: AdminTenantCatalogReleaseSummary;
  variants: AdminTenantCatalogVariantItem[];
  activeVariantsCount: number;
}

export interface AdminTenantCatalogSnapshot {
  families: AdminTenantCatalogFamilyItem[];
  activeActivationCount: number;
  activeFamilyCount: number;
  governedMode: boolean;
  managedByAdminCeo: boolean;
  catalogState: "legacy_open" | "managed_empty" | "managed_active";
  availableVariantCount: number;
  operationalVariantCount: number;
}

function normalizeSlug(value: unknown, maxLength: number) {
  const normalized = String(value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

  return normalized.slice(0, maxLength);
}

function buildCatalogSelectionToken(familyKey: string, variantKey: string) {
  const family = normalizeSlug(familyKey, 120);
  const variant = normalizeSlug(variantKey, 80);

  if (!family || !variant) {
    throw new Error("Family key e variant key são obrigatórios.");
  }

  return `${CATALOG_TOKEN_PREFIX}:${family}:${variant}`;
}

export function parseCatalogSelectionToken(value: unknown) {
  const normalized = String(value ?? "").trim().toLowerCase();

  if (!normalized.startsWith(`${CATALOG_TOKEN_PREFIX}:`)) {
    return null;
  }

  const parts = normalized.split(":");

  if (parts.length !== 3) {
    return null;
  }

  const familyKey = normalizeSlug(parts[1], 120);
  const variantKey = normalizeSlug(parts[2], 80);

  if (!familyKey || !variantKey) {
    return null;
  }

  return { familyKey, variantKey };
}

function resolveRuntimeTemplateCode({
  familyKey,
  templateCode,
  variantKey,
}: {
  familyKey: string;
  templateCode: string | null;
  variantKey: string;
}) {
  const normalizedTemplate = normalizeSlug(templateCode, 80);

  if (normalizedTemplate) {
    return normalizedTemplate;
  }

  const normalizedFamily = normalizeSlug(familyKey, 120);
  const normalizedVariant = normalizeSlug(variantKey, 80);
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

function runtimeTemplateLabel(value: string | null) {
  return value ? value : "Nao operacional";
}

function releaseStatusMeta(value: string | null | undefined) {
  const normalized = String(value ?? "").trim().toLowerCase() || "draft";

  switch (normalized) {
    case "active":
      return { key: "active", label: "Liberado" };
    case "paused":
      return { key: "paused", label: "Pausado" };
    case "expired":
      return { key: "expired", label: "Expirado" };
    default:
      return { key: "draft", label: "Rascunho" };
  }
}

function normalizeVariants(
  familyKey: string,
  offerName: string,
  templateDefaultCode: string | null,
  rawVariants: unknown,
) {
  const variants = Array.isArray(rawVariants)
    ? rawVariants.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && !Array.isArray(item))
    : [];

  if (variants.length > 0) {
    return variants.map((variant, index) => {
      const variantKey =
        normalizeSlug(variant["variant_key"], 80) ||
        normalizeSlug(variant["key"], 80) ||
        normalizeSlug(variant["slug"], 80) ||
        `variant_${index + 1}`;
      const templateCode = normalizeSlug(variant["template_code"], 80) || null;

      return {
        variantKey,
        variantLabel:
          String(
            variant["nome_exibicao"] ??
              variant["label"] ??
              variant["display_name"] ??
              "Variante",
          ).trim() || "Variante",
        templateCode,
        recommendedUse:
          String(variant["uso_recomendado"] ?? variant["description"] ?? "").trim() || null,
        order: Number(variant["ordem"] ?? index + 1) || index + 1,
        runtimeTemplateCode: resolveRuntimeTemplateCode({
          familyKey,
          templateCode,
          variantKey,
        }),
      };
    });
  }

  const fallbackVariantKey = normalizeSlug(templateDefaultCode, 80) || "padrao";

  return [
    {
      variantKey: fallbackVariantKey,
      variantLabel: "Modelo principal",
      templateCode: normalizeSlug(templateDefaultCode, 80) || null,
      recommendedUse: `Modelo principal da oferta ${offerName}.`,
      order: 1,
      runtimeTemplateCode: resolveRuntimeTemplateCode({
        familyKey,
        templateCode: normalizeSlug(templateDefaultCode, 80) || null,
        variantKey: fallbackVariantKey,
      }),
    },
  ];
}

export async function getAdminTenantCatalogSnapshot(companyId: number): Promise<AdminTenantCatalogSnapshot> {
  const [families, activations] = await Promise.all([
    prisma.familias_laudo_catalogo.findMany({
      where: {
        status_catalogo: "publicado",
      },
      orderBy: [{ macro_categoria: "asc" }, { nome_exibicao: "asc" }],
      select: {
        id: true,
        family_key: true,
        nome_exibicao: true,
        descricao: true,
        macro_categoria: true,
        familias_laudo_ofertas_comerciais: {
          select: {
            id: true,
            nome_oferta: true,
            offer_key: true,
            pacote_comercial: true,
            prazo_padrao_dias: true,
            lifecycle_status: true,
            template_default_code: true,
            variantes_json: true,
          },
        },
        tenant_family_releases: {
          where: {
            tenant_id: companyId,
          },
          take: 1,
          select: {
            release_status: true,
            default_template_code: true,
            observacoes: true,
            allowed_templates_json: true,
            allowed_variants_json: true,
          },
        },
      },
    }),
    prisma.empresa_catalogo_laudo_ativacoes.findMany({
      where: {
        empresa_id: companyId,
      },
      select: {
        id: true,
        family_key: true,
        variant_key: true,
        ativo: true,
      },
    }),
  ]);

  const activeActivationMap = new Map(
    activations
      .filter((activation) => activation.ativo)
      .map((activation) => [
        `${normalizeSlug(activation.family_key, 120)}:${normalizeSlug(activation.variant_key, 80)}`,
        activation,
      ]),
  );

  let availableVariantCount = 0;
  let operationalVariantCount = 0;

  const snapshotFamilies: AdminTenantCatalogFamilyItem[] = families.flatMap((family) => {
      const offer = family.familias_laudo_ofertas_comerciais;

      if (!offer || String(offer.lifecycle_status ?? "").trim().toLowerCase() !== "active") {
        return [];
      }

      const tenantRelease = family.tenant_family_releases[0] ?? null;
      const allowedTemplates = new Set(
        (Array.isArray(tenantRelease?.allowed_templates_json) ? tenantRelease?.allowed_templates_json : [])
          .map((item) => normalizeSlug(item, 80))
          .filter(Boolean),
      );
      const allowedVariants = new Set(
        (Array.isArray(tenantRelease?.allowed_variants_json) ? tenantRelease?.allowed_variants_json : [])
          .map((item) => String(item ?? "").trim().toLowerCase())
          .filter(Boolean),
      );
      const normalizedFamilyKey = String(family.family_key).trim().toLowerCase();
      const normalizedTemplateDefault = normalizeSlug(offer.template_default_code, 80) || null;
      const variants: AdminTenantCatalogVariantItem[] = normalizeVariants(
        normalizedFamilyKey,
        String(offer.nome_oferta || family.nome_exibicao),
        normalizedTemplateDefault,
        offer.variantes_json,
      )
        .sort((left, right) => left.order - right.order || left.variantLabel.localeCompare(right.variantLabel, "pt-BR"))
        .map((variant): AdminTenantCatalogVariantItem => {
          const selectionToken = buildCatalogSelectionToken(normalizedFamilyKey, variant.variantKey);
          const runtimeCode = variant.runtimeTemplateCode;
          const activationKey = `${normalizedFamilyKey}:${variant.variantKey}`;
          const isActive = activeActivationMap.has(activationKey);
          const isOperational = Boolean(runtimeCode);
          let availabilityReason: string | null = null;

          if (tenantRelease && releaseStatusMeta(tenantRelease.release_status).key !== "active") {
            availabilityReason = "Liberacao da familia inativa para este tenant.";
          } else if (
            allowedVariants.size > 0 &&
            !allowedVariants.has(selectionToken) &&
            !allowedVariants.has(variant.variantKey)
          ) {
            availabilityReason = "Variante fora da liberacao ativa do tenant.";
          } else if (allowedTemplates.size > 0 && runtimeCode && !allowedTemplates.has(runtimeCode)) {
            availabilityReason = "Template fora da liberacao ativa do tenant.";
          }

          availableVariantCount += 1;

          if (isOperational) {
            operationalVariantCount += 1;
          }

          return {
            selectionToken,
            variantKey: variant.variantKey,
            variantLabel: variant.variantLabel,
            templateCode: variant.templateCode,
            runtimeTemplateCode: runtimeCode,
            runtimeTemplateLabel: runtimeTemplateLabel(runtimeCode),
            recommendedUse: variant.recommendedUse,
            isActive,
            isOperational,
            isSelectableForTenant: isOperational && availabilityReason == null,
            availabilityState: isActive
              ? "active"
              : availabilityReason
                ? "blocked"
                : isOperational
                  ? "available"
                  : "unmapped",
            availabilityReason,
          };
        });
      const templateOptions = Array.from(
        variants.reduce((map, variant) => {
          if (!variant.runtimeTemplateCode) {
            return map;
          }

          if (!map.has(variant.runtimeTemplateCode)) {
            map.set(variant.runtimeTemplateCode, {
              code: variant.runtimeTemplateCode,
              label: variant.runtimeTemplateLabel,
            });
          }

          return map;
        }, new Map<string, AdminTenantCatalogTemplateOption>()),
      )
        .map(([, option]) => option)
        .sort((left, right) => left.label.localeCompare(right.label, "pt-BR"));
      const allowedVariantTokens = variants
        .filter(
          (variant) =>
            allowedVariants.has(variant.selectionToken) || allowedVariants.has(variant.variantKey),
        )
        .map((variant) => variant.selectionToken);

      return [{
        familyId: family.id,
        familyKey: normalizedFamilyKey,
        familyLabel: family.nome_exibicao,
        familyDescription: String(family.descricao ?? "").trim() || null,
        groupLabel:
          String(family.macro_categoria ?? "").trim() ||
          String(offer.pacote_comercial ?? "").trim() ||
          "Catalogo oficial",
        offerId: offer.id,
        offerKey: String(offer.offer_key ?? "").trim() || null,
        offerName: String(offer.nome_oferta || family.nome_exibicao),
        offerPackage: String(offer.pacote_comercial ?? "").trim() || null,
        offerDeadlineDays: offer.prazo_padrao_dias ?? null,
        templateDefaultCode: normalizedTemplateDefault,
        releaseStatus: releaseStatusMeta(tenantRelease?.release_status),
        templateOptions,
        tenantRelease: {
          exists: Boolean(tenantRelease),
          releaseStatus: releaseStatusMeta(tenantRelease?.release_status),
          defaultTemplateCode: normalizeSlug(tenantRelease?.default_template_code, 120) || null,
          allowedTemplates: Array.from(allowedTemplates),
          allowedVariants: allowedVariantTokens,
          observations: String(tenantRelease?.observacoes ?? "").trim() || null,
        },
        variants,
        activeVariantsCount: variants.filter((variant) => variant.isActive).length,
      }];
    });

  const managedByAdminCeo = activations.length > 0 || snapshotFamilies.some((family) => family.releaseStatus.key !== "draft");
  const activeActivationCount = snapshotFamilies.reduce(
    (total, family) => total + family.activeVariantsCount,
    0,
  );

  return {
    families: snapshotFamilies,
    activeActivationCount,
    activeFamilyCount: snapshotFamilies.filter((family) => family.activeVariantsCount > 0).length,
    governedMode: managedByAdminCeo,
    managedByAdminCeo,
    catalogState: activeActivationCount > 0 ? "managed_active" : managedByAdminCeo ? "managed_empty" : "legacy_open",
    availableVariantCount,
    operationalVariantCount,
  };
}
