import { Prisma } from "@/generated/prisma/client";

import { prisma } from "@/lib/server/prisma";

const AVAILABLE_PLANS = new Set(["Inicial", "Intermediario", "Ilimitado"]);

type MutablePlatformSettingKey =
  | "admin_reauth_max_age_minutes"
  | "default_new_tenant_plan";

type MutablePlatformSettingGroup = "access" | "defaults";

type MutablePlatformSettingValue = number | string;
type MutablePlatformSettingSource = "database" | "environment" | "default";

interface MutablePlatformSettingSnapshot {
  value: MutablePlatformSettingValue;
  source: MutablePlatformSettingSource;
}

export interface UpdateAdminPlatformSettingsResult {
  groupKey: MutablePlatformSettingGroup;
  reason: string;
  changes: Array<{
    key: MutablePlatformSettingKey;
    before: MutablePlatformSettingValue;
    beforeSource: MutablePlatformSettingSource;
    after: MutablePlatformSettingValue;
  }>;
}

export async function updateAdminAccessSettings(input: {
  adminReauthMaxAgeMinutes: string;
  reason: string;
}) {
  return updatePlatformSettings({
    groupKey: "access",
    reason: input.reason,
    updates: {
      admin_reauth_max_age_minutes: input.adminReauthMaxAgeMinutes,
    },
  });
}

export async function updateAdminDefaultSettings(input: {
  defaultNewTenantPlan: string;
  reason: string;
}) {
  return updatePlatformSettings({
    groupKey: "defaults",
    reason: input.reason,
    updates: {
      default_new_tenant_plan: input.defaultNewTenantPlan,
    },
  });
}

async function updatePlatformSettings({
  groupKey,
  reason,
  updates,
}: {
  groupKey: MutablePlatformSettingGroup;
  reason: string;
  updates: Partial<Record<MutablePlatformSettingKey, string | number>>;
}) {
  const justification = normalizeRequiredText(reason, "Motivo da alteracao", 300);

  return prisma.$transaction(async (tx) => {
    const platformCompany = await tx.empresas.findFirst({
      where: {
        escopo_plataforma: true,
      },
      orderBy: {
        id: "asc",
      },
      select: {
        id: true,
      },
    });

    if (!platformCompany) {
      throw new Error("Tenant de plataforma nao encontrado para auditar a alteracao.");
    }

    const now = new Date();
    const keys = Object.keys(updates) as MutablePlatformSettingKey[];
    const rows = await tx.configuracoes_plataforma.findMany({
      where: {
        chave: {
          in: keys,
        },
      },
      select: {
        chave: true,
        valor_json: true,
        criado_em: true,
      },
    });
    const rowMap = new Map(rows.map((row) => [row.chave as MutablePlatformSettingKey, row]));
    const changes: UpdateAdminPlatformSettingsResult["changes"] = [];

    for (const key of keys) {
      const before = getSettingSnapshot(key, rowMap.get(key)?.valor_json);
      const after = coerceSettingValue(key, updates[key]);

      if (before.value === after) {
        continue;
      }

      const existing = rowMap.get(key);

      if (existing) {
        await tx.configuracoes_plataforma.update({
          where: { chave: key },
          data: {
            categoria: settingCategory(key),
            valor_json: after,
            motivo_ultima_alteracao: justification,
            atualizada_por_usuario_id: null,
            atualizado_em: now,
          },
        });
      } else {
        await tx.configuracoes_plataforma.create({
          data: {
            chave: key,
            categoria: settingCategory(key),
            valor_json: after,
            motivo_ultima_alteracao: justification,
            atualizada_por_usuario_id: null,
            criado_em: now,
            atualizado_em: now,
          },
        });
      }

      changes.push({
        key,
        before: before.value,
        beforeSource: before.source,
        after,
      });
    }

    if (changes.length === 0) {
      throw new Error("Nenhuma alteracao efetiva foi detectada.");
    }

    await tx.auditoria_empresas.create({
      data: {
        empresa_id: platformCompany.id,
        portal: "admin",
        acao: "platform_setting_updated",
        resumo: groupSummary(groupKey),
        detalhe: groupDetail(groupKey),
        payload_json: {
          group: groupKey,
          reason: justification,
          changes,
          source_surface: "frontend_astro",
          actor_binding: "pending_admin_auth_migration",
        } as Prisma.InputJsonObject,
        criado_em: now,
      },
    });

    return {
      groupKey,
      reason: justification,
      changes,
    } satisfies UpdateAdminPlatformSettingsResult;
  });
}

function settingCategory(key: MutablePlatformSettingKey) {
  return key === "admin_reauth_max_age_minutes" ? "access" : "defaults";
}

function getSettingSnapshot(
  key: MutablePlatformSettingKey,
  rawValue: unknown,
): MutablePlatformSettingSnapshot {
  if (rawValue !== undefined) {
    try {
      return {
        value: coerceSettingValue(key, rawValue),
        source: "database",
      };
    } catch {
      return getSettingDefault(key);
    }
  }

  return getSettingDefault(key);
}

function getSettingDefault(key: MutablePlatformSettingKey): MutablePlatformSettingSnapshot {
  if (key === "admin_reauth_max_age_minutes") {
    const hasEnvironmentOverride = String(process.env["ADMIN_REAUTH_MAX_AGE_MINUTES"] ?? "").trim();

    return {
      value: Math.max(normalizeInteger(process.env["ADMIN_REAUTH_MAX_AGE_MINUTES"], 10), 1),
      source: hasEnvironmentOverride ? "environment" : "default",
    };
  }

  return {
    value: "Inicial",
    source: "default",
  };
}

function coerceSettingValue(key: MutablePlatformSettingKey, value: unknown): MutablePlatformSettingValue {
  if (key === "admin_reauth_max_age_minutes") {
    const normalized = normalizeInteger(value, Number.NaN);

    if (!Number.isInteger(normalized)) {
      throw new Error("Informe um valor numerico valido.");
    }

    if (normalized < 1 || normalized > 120) {
      throw new Error("Informe um valor entre 1 e 120.");
    }

    return normalized;
  }

  return normalizePlan(value);
}

function normalizeInteger(value: unknown, fallback: number) {
  const normalized = Number(value);

  if (!Number.isFinite(normalized)) {
    return fallback;
  }

  return Math.trunc(normalized);
}

function normalizePlan(value: unknown) {
  const normalized = String(value ?? "").trim();

  if (!AVAILABLE_PLANS.has(normalized)) {
    throw new Error("Plano invalido. Use Inicial, Intermediario ou Ilimitado.");
  }

  return normalized;
}

function normalizeRequiredText(value: string, field: string, maxLength: number) {
  const normalized = String(value ?? "").trim();

  if (!normalized) {
    throw new Error(`${field} e obrigatorio.`);
  }

  if (normalized.length > maxLength) {
    throw new Error(`${field} excede ${maxLength} caracteres.`);
  }

  return normalized;
}

function groupSummary(groupKey: MutablePlatformSettingGroup) {
  return groupKey === "access"
    ? "Politica de acesso da plataforma atualizada."
    : "Defaults globais da plataforma atualizados.";
}

function groupDetail(groupKey: MutablePlatformSettingGroup) {
  return groupKey === "access"
    ? "Mudanca de seguranca aplicada ao Admin-CEO pelo painel Astro."
    : "Mudanca aplicada ao onboarding padrao de novos tenants pelo painel Astro.";
}
