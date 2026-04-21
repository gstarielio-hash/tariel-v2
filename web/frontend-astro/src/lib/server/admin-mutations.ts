import { Prisma } from "@/generated/prisma/client";

import { prisma } from "@/lib/server/prisma";
import { generateStrongPassword, hashPassword } from "@/lib/server/passwords";
import {
  getAdminTenantCatalogSnapshot,
  parseCatalogSelectionToken,
} from "@/lib/server/admin-tenant-catalog";

const ACCESS_LEVELS = {
  inspector: 1,
  reviewer: 50,
  clientAdmin: 80,
} as const;

const AVAILABLE_PLANS = new Set(["Inicial", "Intermediario", "Ilimitado"]);

type ManagedAccessLevel = (typeof ACCESS_LEVELS)[keyof typeof ACCESS_LEVELS];

interface CredentialResult {
  label: string;
  portal: string;
  email: string;
  password: string;
}

export interface ToggleCompanyBlockResult {
  blocked: boolean;
  companyName: string;
  invalidatedSessions: number;
  reason: string | null;
}

export interface ChangeCompanyPlanResult {
  companyName: string;
  previousPlan: string;
  nextPlan: string;
  alerts: string[];
}

export interface ResetCompanyUserPasswordResult extends CredentialResult {
  companyName: string;
  userName: string;
}

export interface ToggleCompanyUserResult {
  companyName: string;
  userName: string;
  active: boolean;
}

export interface AddCompanyAdminResult extends CredentialResult {
  companyName: string;
  userName: string;
}

export interface CreateCompanyResult {
  companyId: number;
  companyName: string;
  credentials: CredentialResult[];
}

export interface SyncCompanyCatalogPortfolioResult {
  companyName: string;
  selectedCount: number;
  governedMode: boolean;
  activated: string[];
  reactivated: string[];
  deactivated: string[];
}

export interface UpdateCompanyCatalogFamilyReleaseResult {
  companyName: string;
  familyLabel: string;
  releaseStatus: string;
  selectedCount: number;
  activated: string[];
  reactivated: string[];
  deactivated: string[];
}

export interface CreateCompanyInput {
  nome: string;
  cnpj: string;
  emailAdmin: string;
  plano: string;
  segmento?: string;
  cidadeEstado?: string;
  nomeResponsavel?: string;
  observacoes?: string;
  provisionarInspetor?: boolean;
  inspetorNome?: string;
  inspetorEmail?: string;
  inspetorTelefone?: string;
  provisionarRevisor?: boolean;
  revisorNome?: string;
  revisorEmail?: string;
  revisorTelefone?: string;
  revisorCrea?: string;
}

export async function toggleCompanyBlockStatus(
  companyId: number,
  motivo: string,
  confirmUnblock: boolean,
  actorUserId?: number | null,
) {
  const result = await prisma.$transaction(async (tx) => {
    const company = await tx.empresas.findUnique({
      where: { id: companyId },
      select: {
        id: true,
        nome_fantasia: true,
        status_bloqueio: true,
      },
    });

    if (!company) {
      throw new Error("Empresa não encontrada.");
    }

    const now = new Date();

    if (company.status_bloqueio) {
      if (!confirmUnblock) {
        throw new Error("Confirme o desbloqueio da empresa.");
      }

      await tx.empresas.update({
        where: { id: companyId },
        data: {
          status_bloqueio: false,
          bloqueado_em: null,
          motivo_bloqueio: null,
          atualizado_em: now,
        },
      });

      await createAudit(tx, {
        companyId,
        actorUserId,
        action: "empresa_desbloqueada",
        summary: "Empresa desbloqueada pelo painel Astro.",
        detail: `Empresa ${company.nome_fantasia} foi desbloqueada no Admin-CEO migrado.`,
      });

      return {
        blocked: false,
        companyName: company.nome_fantasia,
        invalidatedSessions: 0,
        reason: null,
      } satisfies ToggleCompanyBlockResult;
    }

    const normalizedReason = normalizeRequiredText(motivo, "Motivo do bloqueio", 300);
    const users = await tx.usuarios.findMany({
      where: { empresa_id: companyId },
      select: { id: true },
    });

    await tx.empresas.update({
      where: { id: companyId },
      data: {
        status_bloqueio: true,
        bloqueado_em: now,
        motivo_bloqueio: normalizedReason,
        atualizado_em: now,
      },
    });

    const invalidatedSessions = await tx.sessoes_ativas.deleteMany({
      where: {
        usuario_id: {
          in: users.map((user) => user.id),
        },
      },
    });

    await createAudit(tx, {
      companyId,
      actorUserId,
      action: "empresa_bloqueada",
      summary: "Empresa bloqueada pelo painel Astro.",
      detail: normalizedReason,
      payload: {
        invalidatedSessions: invalidatedSessions.count,
      },
    });

    return {
      blocked: true,
      companyName: company.nome_fantasia,
      invalidatedSessions: invalidatedSessions.count,
      reason: normalizedReason,
    } satisfies ToggleCompanyBlockResult;
  });

  return result;
}

export async function changeCompanyPlan(companyId: number, requestedPlan: string, actorUserId?: number | null) {
  const nextPlan = normalizePlan(requestedPlan);

  const result = await prisma.$transaction(async (tx) => {
    const [company, limits, managedUsers] = await Promise.all([
      tx.empresas.findUnique({
        where: { id: companyId },
        select: {
          id: true,
          nome_fantasia: true,
          plano_ativo: true,
          mensagens_processadas: true,
        },
      }),
      tx.limites_plano.findUnique({
        where: { plano: nextPlan },
      }),
      tx.usuarios.count({
        where: {
          empresa_id: companyId,
          nivel_acesso: {
            in: [ACCESS_LEVELS.clientAdmin, ACCESS_LEVELS.inspector, ACCESS_LEVELS.reviewer],
          },
        },
      }),
    ]);

    if (!company) {
      throw new Error("Empresa não encontrada.");
    }

    if (!limits) {
      throw new Error("Plano não encontrado.");
    }

    const alerts: string[] = [];

    if (limits.usuarios_max != null && managedUsers > limits.usuarios_max) {
      alerts.push("Total de usuários acima do novo limite.");
    }

    if (limits.laudos_mes != null && company.mensagens_processadas > limits.laudos_mes) {
      alerts.push("Uso atual acima do novo limite mensal.");
    }

    await tx.empresas.update({
      where: { id: companyId },
      data: {
        plano_ativo: nextPlan,
        atualizado_em: new Date(),
      },
    });

    await createAudit(tx, {
      companyId,
      actorUserId,
      action: "empresa_plano_alterado",
      summary: `Plano alterado de ${company.plano_ativo} para ${nextPlan}.`,
      payload: {
        previousPlan: company.plano_ativo,
        nextPlan,
        alerts,
      },
    });

    return {
      companyName: company.nome_fantasia,
      previousPlan: company.plano_ativo,
      nextPlan,
      alerts,
    } satisfies ChangeCompanyPlanResult;
  });

  return result;
}

export async function resetCompanyUserPassword(companyId: number, userId: number, actorUserId?: number | null) {
  const nextPassword = generateStrongPassword();
  const passwordHash = await hashPassword(nextPassword);

  const result = await prisma.$transaction(async (tx) => {
    const user = await getCompanyUserOrThrow(tx, companyId, userId);

    await tx.usuarios.update({
      where: { id: userId },
      data: {
        senha_hash: passwordHash,
        tentativas_login: 0,
        bloqueado_ate: null,
        status_bloqueio: false,
        blocked_reason: null,
        senha_temporaria_ativa: true,
        atualizado_em: new Date(),
      },
    });

    await tx.sessoes_ativas.deleteMany({
      where: {
        usuario_id: userId,
      },
    });

    await createAudit(tx, {
      companyId,
      actorUserId,
      action: "usuario_senha_resetada",
      targetUserId: userId,
      summary: `Senha resetada para ${user.nome_completo}.`,
    });

    return {
      companyName: user.empresas.nome_fantasia,
      userName: user.nome_completo,
      label: user.nome_completo,
      portal: user.nivel_acesso === ACCESS_LEVELS.clientAdmin ? "cliente" : user.nivel_acesso === ACCESS_LEVELS.reviewer ? "revisor" : "inspetor",
      email: user.email,
      password: nextPassword,
    } satisfies ResetCompanyUserPasswordResult;
  });

  return result;
}

export async function toggleCompanyUserStatus(companyId: number, userId: number, actorUserId?: number | null) {
  const result = await prisma.$transaction(async (tx) => {
    const user = await getCompanyUserOrThrow(tx, companyId, userId);
    const nextActive = !user.ativo;

    await tx.usuarios.update({
      where: { id: userId },
      data: {
        ativo: nextActive,
        status_bloqueio: !nextActive ? true : false,
        bloqueado_ate: null,
        tentativas_login: nextActive ? 0 : user.tentativas_login,
        blocked_reason: nextActive ? null : "Bloqueado pelo Admin-CEO migrado.",
        atualizado_em: new Date(),
      },
    });

    await tx.sessoes_ativas.deleteMany({
      where: {
        usuario_id: userId,
      },
    });

    await createAudit(tx, {
      companyId,
      actorUserId,
      action: "usuario_status_alterado",
      targetUserId: userId,
      summary: `${user.nome_completo} foi ${nextActive ? "reativado" : "bloqueado"} pelo painel Astro.`,
    });

    return {
      companyName: user.empresas.nome_fantasia,
      userName: user.nome_completo,
      active: nextActive,
    } satisfies ToggleCompanyUserResult;
  });

  return result;
}

export async function addCompanyAdmin(
  companyId: number,
  input: { nome: string; email: string },
  actorUserId?: number | null,
) {
  const email = normalizeEmail(input.email);
  const name = normalizeRequiredText(input.nome, "Nome do administrador", 150);
  const nextPassword = generateStrongPassword();
  const passwordHash = await hashPassword(nextPassword);

  const result = await prisma.$transaction(async (tx) => {
    const company = await tx.empresas.findUnique({
      where: { id: companyId },
      select: {
        id: true,
        nome_fantasia: true,
        plano_ativo: true,
      },
    });

    if (!company) {
      throw new Error("Empresa não encontrada.");
    }

    await ensureUserCapacity(tx, companyId, company.plano_ativo, 1);
    await ensureUniqueEmail(tx, email);

    const createdAt = new Date();
    const user = await tx.usuarios.create({
      data: buildTenantUserCreateInput({
        companyId,
        name,
        email,
        passwordHash,
        accessLevel: ACCESS_LEVELS.clientAdmin,
        createdAt,
        allowedPortals: ["cliente"],
      }),
      select: {
        id: true,
        nome_completo: true,
        email: true,
      },
    });

    await createAudit(tx, {
      companyId,
      actorUserId,
      action: "admin_cliente_adicionado",
      targetUserId: user.id,
      summary: `Administrador ${user.nome_completo} adicionado à empresa.`,
    });

    return {
      companyName: company.nome_fantasia,
      userName: user.nome_completo,
      label: user.nome_completo,
      portal: "cliente",
      email: user.email,
      password: nextPassword,
    } satisfies AddCompanyAdminResult;
  });

  return result;
}

export async function createCompany(input: CreateCompanyInput, actorUserId?: number | null) {
  const companyName = normalizeRequiredText(input.nome, "Nome da empresa", 200);
  const cnpj = normalizeCnpj(input.cnpj);
  const plan = normalizePlan(input.plano);
  const adminEmail = normalizeEmail(input.emailAdmin);
  const adminPassword = generateStrongPassword();
  const adminPasswordHash = await hashPassword(adminPassword);

  const provisionInspector = Boolean(input.provisionarInspetor);
  const provisionReviewer = Boolean(input.provisionarRevisor);
  const additionalUsers = Number(provisionInspector) + Number(provisionReviewer) + 1;

  const optionalEmails = new Set<string>([adminEmail]);
  const inspectorEmail = provisionInspector ? normalizeEmail(input.inspetorEmail ?? "") : "";
  const reviewerEmail = provisionReviewer ? normalizeEmail(input.revisorEmail ?? "") : "";

  if (provisionInspector) {
    if (!inspectorEmail) {
      throw new Error("Informe o e-mail da equipe de campo inicial.");
    }

    if (optionalEmails.has(inspectorEmail)) {
      throw new Error("Os e-mails provisionados precisam ser diferentes entre si.");
    }

    optionalEmails.add(inspectorEmail);
  }

  if (provisionReviewer) {
    if (!reviewerEmail) {
      throw new Error("Informe o e-mail da equipe de análise inicial.");
    }

    if (optionalEmails.has(reviewerEmail)) {
      throw new Error("Os e-mails provisionados precisam ser diferentes entre si.");
    }

    optionalEmails.add(reviewerEmail);
  }

  const result = await prisma.$transaction(async (tx) => {
    const existingCompany = await tx.empresas.findFirst({
      where: { cnpj },
      select: { id: true },
    });

    if (existingCompany) {
      throw new Error("CNPJ já cadastrado no sistema.");
    }

    for (const email of optionalEmails) {
      await ensureUniqueEmail(tx, email);
    }

    const planLimits = await tx.limites_plano.findUnique({
      where: { plano: plan },
    });

    if (!planLimits) {
      throw new Error("Plano não encontrado.");
    }

    if (planLimits.usuarios_max != null && additionalUsers > planLimits.usuarios_max) {
      throw new Error(`O plano ${plan} não comporta ${additionalUsers} usuários iniciais.`);
    }

    const createdAt = new Date();
    const company = await tx.empresas.create({
      data: {
        nome_fantasia: companyName,
        cnpj,
        plano_ativo: plan,
        custo_gerado_reais: 0,
        mensagens_processadas: 0,
        status_bloqueio: false,
        escopo_plataforma: false,
        admin_cliente_policy_json: {},
        segmento: normalizeOptionalText(input.segmento, 100),
        cidade_estado: normalizeOptionalText(input.cidadeEstado, 100),
        nome_responsavel: normalizeOptionalText(input.nomeResponsavel, 150),
        observacoes: normalizeOptionalText(input.observacoes),
        criado_em: createdAt,
      },
      select: {
        id: true,
        nome_fantasia: true,
      },
    });

    const credentials: CredentialResult[] = [];
    const adminUser = await tx.usuarios.create({
      data: buildTenantUserCreateInput({
        companyId: company.id,
        name: `Administrador ${companyName}`,
        email: adminEmail,
        passwordHash: adminPasswordHash,
        accessLevel: ACCESS_LEVELS.clientAdmin,
        createdAt,
        allowedPortals: ["cliente"],
      }),
      select: {
        id: true,
        nome_completo: true,
        email: true,
      },
    });

    credentials.push({
      label: adminUser.nome_completo,
      portal: "cliente",
      email: adminUser.email,
      password: adminPassword,
    });

    if (provisionInspector && inspectorEmail) {
      const inspectorPassword = generateStrongPassword();
      const inspectorPasswordHash = await hashPassword(inspectorPassword);
      const inspectorName =
        normalizeOptionalText(input.inspetorNome, 150) || `Equipe de campo ${companyName}`;

      const inspectorUser = await tx.usuarios.create({
        data: buildTenantUserCreateInput({
          companyId: company.id,
          name: inspectorName,
          email: inspectorEmail,
          passwordHash: inspectorPasswordHash,
          accessLevel: ACCESS_LEVELS.inspector,
          createdAt,
          allowedPortals: ["inspetor"],
          phone: normalizeOptionalText(input.inspetorTelefone, 30),
        }),
        select: {
          id: true,
          nome_completo: true,
          email: true,
        },
      });

      credentials.push({
        label: inspectorUser.nome_completo,
        portal: "inspetor",
        email: inspectorUser.email,
        password: inspectorPassword,
      });
    }

    if (provisionReviewer && reviewerEmail) {
      const reviewerPassword = generateStrongPassword();
      const reviewerPasswordHash = await hashPassword(reviewerPassword);
      const reviewerName =
        normalizeOptionalText(input.revisorNome, 150) || `Equipe de análise ${companyName}`;

      const reviewerUser = await tx.usuarios.create({
        data: buildTenantUserCreateInput({
          companyId: company.id,
          name: reviewerName,
          email: reviewerEmail,
          passwordHash: reviewerPasswordHash,
          accessLevel: ACCESS_LEVELS.reviewer,
          createdAt,
          allowedPortals: ["revisor"],
          phone: normalizeOptionalText(input.revisorTelefone, 30),
          crea: normalizeOptionalText(input.revisorCrea, 40),
        }),
        select: {
          id: true,
          nome_completo: true,
          email: true,
        },
      });

      credentials.push({
        label: reviewerUser.nome_completo,
        portal: "revisor",
        email: reviewerUser.email,
        password: reviewerPassword,
      });
    }

    await createAudit(tx, {
      companyId: company.id,
      actorUserId,
      action: "empresa_criada",
      targetUserId: adminUser.id,
      summary: "Empresa provisionada pelo fluxo de onboarding Astro.",
      payload: {
        plan,
        provisionInspector,
        provisionReviewer,
      },
    });

    return {
      companyId: company.id,
      companyName: company.nome_fantasia,
      credentials,
    } satisfies CreateCompanyResult;
  });

  return result;
}

export async function syncCompanyCatalogPortfolio(
  companyId: number,
  selectionTokens: string[],
  actorUserId?: number | null,
) {
  const snapshot = await getAdminTenantCatalogSnapshot(companyId);
  const governedByRelease = snapshot.families.some(
    (family) => family.releaseStatus.key !== "draft",
  );
  const lookup = new Map<
    string,
    {
      familyId: number;
      familyKey: string;
      familyLabel: string;
      groupLabel: string;
      offerId: number;
      offerName: string;
      variantKey: string;
      variantLabel: string;
      runtimeTemplateCode: string | null;
      order: number;
      isSelectableForTenant: boolean;
      availabilityReason: string | null;
    }
  >();

  for (const family of snapshot.families) {
    for (const [index, variant] of family.variants.entries()) {
      lookup.set(`${family.familyKey}:${variant.variantKey}`, {
        familyId: family.familyId,
        familyKey: family.familyKey,
        familyLabel: family.familyLabel,
        groupLabel: family.groupLabel,
        offerId: family.offerId,
        offerName: family.offerName,
        variantKey: variant.variantKey,
        variantLabel: variant.variantLabel,
        runtimeTemplateCode: variant.runtimeTemplateCode,
        order: index + 1,
        isSelectableForTenant: variant.isSelectableForTenant,
        availabilityReason: variant.availabilityReason,
      });
    }
  }

  const normalizedSelections = new Set<string>();

  for (const rawToken of selectionTokens) {
    const parsed = parseCatalogSelectionToken(rawToken);

    if (!parsed) {
      throw new Error("Seleção de variante comercial inválida.");
    }

    const key = `${parsed.familyKey}:${parsed.variantKey}`;
    const item = lookup.get(key);

    if (!item) {
      throw new Error("A variante escolhida não está disponível no catálogo oficial.");
    }

    if (!item.isSelectableForTenant) {
      throw new Error(item.availabilityReason || "A variante escolhida não está liberada para este tenant.");
    }

    if (!item.runtimeTemplateCode) {
      throw new Error("A variante escolhida ainda não possui runtime operacional no produto.");
    }

    normalizedSelections.add(key);
  }

  const result = await prisma.$transaction(async (tx) => {
    const company = await tx.empresas.findUnique({
      where: { id: companyId },
      select: {
        id: true,
        nome_fantasia: true,
      },
    });

    if (!company) {
      throw new Error("Empresa não encontrada.");
    }

    const existing = await tx.empresa_catalogo_laudo_ativacoes.findMany({
      where: {
        empresa_id: companyId,
      },
      select: {
        id: true,
        family_key: true,
        variant_key: true,
        ativo: true,
      },
    });

    const existingByKey = new Map(
      existing.map((item) => [`${item.family_key}:${item.variant_key}`, item]),
    );
    const now = new Date();
    const activated: string[] = [];
    const reactivated: string[] = [];
    const deactivated: string[] = [];

    for (const key of normalizedSelections) {
      const item = lookup.get(key);

      if (!item) {
        continue;
      }

      const current = existingByKey.get(key);

      if (!current) {
        await tx.empresa_catalogo_laudo_ativacoes.create({
          data: {
            empresa_id: companyId,
            family_id: item.familyId,
            oferta_id: item.offerId,
            family_key: item.familyKey,
            family_label: item.familyLabel,
            group_label: item.groupLabel,
            offer_name: item.offerName,
            variant_key: item.variantKey,
            variant_label: item.variantLabel,
            variant_ordem: item.order,
            runtime_template_code: item.runtimeTemplateCode ?? "padrao",
            ativo: true,
            criado_em: now,
            atualizado_em: now,
          },
        });

        activated.push(buildSelectionTokenFromKey(key));
        continue;
      }

      await tx.empresa_catalogo_laudo_ativacoes.update({
        where: {
          id: current.id,
        },
        data: {
          family_id: item.familyId,
          oferta_id: item.offerId,
          family_label: item.familyLabel,
          group_label: item.groupLabel,
          offer_name: item.offerName,
          variant_label: item.variantLabel,
          variant_ordem: item.order,
          runtime_template_code: item.runtimeTemplateCode ?? "padrao",
          ativo: true,
          atualizado_em: now,
        },
      });

      if (!current.ativo) {
        reactivated.push(buildSelectionTokenFromKey(key));
      }
    }

    for (const [key, current] of existingByKey.entries()) {
      if (normalizedSelections.has(key) || !current.ativo) {
        continue;
      }

      await tx.empresa_catalogo_laudo_ativacoes.update({
        where: {
          id: current.id,
        },
        data: {
          ativo: false,
          atualizado_em: now,
        },
      });

      deactivated.push(buildSelectionTokenFromKey(key));
    }

    await createAudit(tx, {
      companyId,
      actorUserId,
      action: "tenant_report_catalog_synced",
      summary: "Portfólio comercial de laudos sincronizado para a empresa.",
      detail: `${normalizedSelections.size} variantes ativas no catálogo operacional do cliente.`,
      payload: {
        selected_count: normalizedSelections.size,
        governed_mode: governedByRelease || normalizedSelections.size > 0,
        activated,
        reactivated,
        deactivated,
      },
    });

    return {
      companyName: company.nome_fantasia,
      selectedCount: normalizedSelections.size,
      governedMode: governedByRelease || normalizedSelections.size > 0,
      activated,
      reactivated,
      deactivated,
    } satisfies SyncCompanyCatalogPortfolioResult;
  });

  return result;
}

export async function updateCompanyCatalogFamilyRelease(input: {
  companyId: number;
  familyKey: string;
  releaseStatus: string;
  defaultTemplateCode?: string | null;
  observacoes?: string | null;
  allowedTemplates?: string[];
  allowedVariants?: string[];
  actorUserId?: number | null;
}) {
  const companyId = input.companyId;
  const familyKey = normalizeCatalogKey(input.familyKey, 120);
  const releaseStatus = normalizeReleaseStatus(input.releaseStatus);
  const snapshot = await getAdminTenantCatalogSnapshot(companyId);
  const family = snapshot.families.find((item) => item.familyKey === familyKey);

  if (!family) {
    throw new Error("Família do catálogo não encontrada para esta empresa.");
  }

  const templateLookup = new Map(
    family.templateOptions.map((option) => [option.code, option]),
  );
  const variantLookup = new Map(
    family.variants.map((variant, index) => [
      `${family.familyKey}:${variant.variantKey}`,
      {
        ...variant,
        order: index + 1,
      },
    ]),
  );
  const allowedTemplates = new Set<string>();

  for (const rawTemplate of input.allowedTemplates ?? []) {
    const code = normalizeCatalogKey(rawTemplate, 80);

    if (!code) {
      continue;
    }

    if (!templateLookup.has(code)) {
      throw new Error("Template fora do catálogo operacional desta família.");
    }

    allowedTemplates.add(code);
  }

  const allowedVariantKeys = new Set<string>();
  const allowedVariants = new Set<string>();

  for (const rawToken of input.allowedVariants ?? []) {
    const parsed = parseCatalogSelectionToken(rawToken);

    if (!parsed || parsed.familyKey !== family.familyKey) {
      throw new Error("Seleção de variante inválida para esta família.");
    }

    const key = `${parsed.familyKey}:${parsed.variantKey}`;
    const variant = variantLookup.get(key);

    if (!variant) {
      throw new Error("A variante escolhida não pertence à família selecionada.");
    }

    if (!variant.runtimeTemplateCode) {
      throw new Error("A variante escolhida ainda não possui runtime operacional.");
    }

    if (releaseStatus === "active" && allowedTemplates.size > 0 && !allowedTemplates.has(variant.runtimeTemplateCode)) {
      throw new Error("Existe variante marcada com runtime fora dos templates liberados.");
    }

    allowedVariantKeys.add(key);
    allowedVariants.add(variant.selectionToken);
  }

  const defaultTemplateCode = normalizeOptionalCatalogKey(input.defaultTemplateCode, 120);

  if (defaultTemplateCode && !templateLookup.has(defaultTemplateCode)) {
    throw new Error("Template default fora das opções operacionais desta família.");
  }

  const observations = normalizeOptionalText(input.observacoes);

  const result = await prisma.$transaction(async (tx) => {
    const [company, existingRelease, existingActivations] = await Promise.all([
      tx.empresas.findUnique({
        where: { id: companyId },
        select: {
          id: true,
          nome_fantasia: true,
        },
      }),
      tx.tenant_family_releases.findFirst({
        where: {
          tenant_id: companyId,
          family_id: family.familyId,
        },
        select: {
          id: true,
          start_at: true,
        },
      }),
      tx.empresa_catalogo_laudo_ativacoes.findMany({
        where: {
          empresa_id: companyId,
          family_key: family.familyKey,
        },
        select: {
          id: true,
          family_key: true,
          variant_key: true,
          ativo: true,
        },
      }),
    ]);

    if (!company) {
      throw new Error("Empresa não encontrada.");
    }

    const now = new Date();

    if (existingRelease) {
      await tx.tenant_family_releases.update({
        where: {
          id: existingRelease.id,
        },
        data: {
          offer_id: family.offerId,
          allowed_templates_json: allowedTemplates.size > 0 ? Array.from(allowedTemplates) : Prisma.DbNull,
          allowed_variants_json: allowedVariants.size > 0 ? Array.from(allowedVariants) : Prisma.DbNull,
          default_template_code: defaultTemplateCode,
          release_status: releaseStatus,
          start_at: releaseStatus === "active" ? existingRelease.start_at ?? now : existingRelease.start_at,
          end_at: releaseStatus === "paused" || releaseStatus === "expired" ? now : null,
          observacoes: observations,
          atualizado_em: now,
        },
      });
    } else {
      await tx.tenant_family_releases.create({
        data: {
          tenant_id: companyId,
          family_id: family.familyId,
          offer_id: family.offerId,
          allowed_offers_json: family.offerKey ? [family.offerKey] : Prisma.DbNull,
          allowed_templates_json: allowedTemplates.size > 0 ? Array.from(allowedTemplates) : Prisma.DbNull,
          allowed_variants_json: allowedVariants.size > 0 ? Array.from(allowedVariants) : Prisma.DbNull,
          default_template_code: defaultTemplateCode,
          release_status: releaseStatus,
          start_at: releaseStatus === "active" ? now : null,
          end_at: releaseStatus === "paused" || releaseStatus === "expired" ? now : null,
          observacoes: observations,
          criado_em: now,
          atualizado_em: now,
        },
      });
    }

    const existingByKey = new Map(
      existingActivations.map((item) => [`${item.family_key}:${item.variant_key}`, item]),
    );
    const activeTargetKeys = releaseStatus === "active" ? allowedVariantKeys : new Set<string>();
    const activated: string[] = [];
    const reactivated: string[] = [];
    const deactivated: string[] = [];

    for (const key of activeTargetKeys) {
      const variant = variantLookup.get(key);

      if (!variant) {
        continue;
      }

      const current = existingByKey.get(key);

      if (!current) {
        await tx.empresa_catalogo_laudo_ativacoes.create({
          data: {
            empresa_id: companyId,
            family_id: family.familyId,
            oferta_id: family.offerId,
            family_key: family.familyKey,
            family_label: family.familyLabel,
            group_label: family.groupLabel,
            offer_name: family.offerName,
            variant_key: variant.variantKey,
            variant_label: variant.variantLabel,
            variant_ordem: variant.order,
            runtime_template_code: variant.runtimeTemplateCode ?? "padrao",
            ativo: true,
            criado_em: now,
            atualizado_em: now,
          },
        });

        activated.push(variant.selectionToken);
        continue;
      }

      await tx.empresa_catalogo_laudo_ativacoes.update({
        where: {
          id: current.id,
        },
        data: {
          family_id: family.familyId,
          oferta_id: family.offerId,
          family_label: family.familyLabel,
          group_label: family.groupLabel,
          offer_name: family.offerName,
          variant_label: variant.variantLabel,
          variant_ordem: variant.order,
          runtime_template_code: variant.runtimeTemplateCode ?? "padrao",
          ativo: true,
          atualizado_em: now,
        },
      });

      if (!current.ativo) {
        reactivated.push(variant.selectionToken);
      }
    }

    for (const [key, current] of existingByKey.entries()) {
      if (activeTargetKeys.has(key) || !current.ativo) {
        continue;
      }

      await tx.empresa_catalogo_laudo_ativacoes.update({
        where: {
          id: current.id,
        },
        data: {
          ativo: false,
          atualizado_em: now,
        },
      });

      deactivated.push(buildSelectionTokenFromKey(key));
    }

    await createAudit(tx, {
      companyId,
      actorUserId: input.actorUserId,
      action: "tenant_family_release_updated",
      summary: `Liberação da família ${family.familyLabel} atualizada para a empresa.`,
      detail: `${releaseStatus} com ${activeTargetKeys.size} variantes ativas.`,
      payload: {
        family_key: family.familyKey,
        family_label: family.familyLabel,
        release_status: releaseStatus,
        default_template_code: defaultTemplateCode,
        selected_count: activeTargetKeys.size,
        activated,
        reactivated,
        deactivated,
      },
    });

    return {
      companyName: company.nome_fantasia,
      familyLabel: family.familyLabel,
      releaseStatus,
      selectedCount: activeTargetKeys.size,
      activated,
      reactivated,
      deactivated,
    } satisfies UpdateCompanyCatalogFamilyReleaseResult;
  });

  return result;
}

function normalizeCnpj(value: string) {
  const digits = String(value ?? "").replace(/\D+/g, "");

  if (digits.length !== 14) {
    throw new Error("CNPJ inválido. Informe 14 dígitos.");
  }

  return digits;
}

function normalizeEmail(value: string) {
  const normalized = String(value ?? "").trim().toLowerCase();

  if (!normalized || !normalized.includes("@")) {
    throw new Error("Informe um e-mail válido.");
  }

  if (normalized.length > 254) {
    throw new Error("E-mail excede 254 caracteres.");
  }

  return normalized;
}

function normalizePlan(value: string) {
  const normalized = String(value ?? "").trim();

  if (!AVAILABLE_PLANS.has(normalized)) {
    throw new Error("Plano inválido. Use Inicial, Intermediario ou Ilimitado.");
  }

  return normalized;
}

function normalizeReleaseStatus(value: string) {
  const normalized = String(value ?? "").trim().toLowerCase();

  if (normalized === "draft" || normalized === "active" || normalized === "paused" || normalized === "expired") {
    return normalized;
  }

  throw new Error("Status de liberação inválido.");
}

function normalizeCatalogKey(value: string | null | undefined, maxLength: number) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, maxLength);
}

function normalizeOptionalCatalogKey(value: string | null | undefined, maxLength: number) {
  const normalized = normalizeCatalogKey(value, maxLength);

  return normalized || null;
}

function normalizeRequiredText(value: string, field: string, maxLength: number) {
  const normalized = String(value ?? "").trim();

  if (!normalized) {
    throw new Error(`${field} é obrigatório.`);
  }

  if (normalized.length > maxLength) {
    throw new Error(`${field} excede ${maxLength} caracteres.`);
  }

  return normalized;
}

function normalizeOptionalText(value: string | null | undefined, maxLength = 5_000) {
  const normalized = String(value ?? "").trim();

  if (!normalized) {
    return null;
  }

  return normalized.slice(0, maxLength);
}

function buildSelectionTokenFromKey(value: string) {
  const [familyKey = "", variantKey = ""] = String(value ?? "").split(":");

  return `catalog:${familyKey}:${variantKey}`;
}

function buildTenantUserCreateInput({
  companyId,
  name,
  email,
  passwordHash,
  accessLevel,
  createdAt,
  allowedPortals,
  phone,
  crea,
}: {
  companyId: number;
  name: string;
  email: string;
  passwordHash: string;
  accessLevel: ManagedAccessLevel;
  createdAt: Date;
  allowedPortals: string[];
  phone?: string | null;
  crea?: string | null;
}) {
  return {
    empresa_id: companyId,
    nome_completo: name,
    email,
    telefone: phone ?? null,
    crea: crea ?? null,
    senha_hash: passwordHash,
    nivel_acesso: accessLevel,
    ativo: true,
    tentativas_login: 0,
    status_bloqueio: false,
    senha_temporaria_ativa: true,
    criado_em: createdAt,
    account_scope: "tenant",
    account_status: "active",
    allowed_portals_json: allowedPortals,
    mfa_required: false,
    can_password_login: true,
    can_google_login: false,
    can_microsoft_login: false,
    portal_admin_autorizado: false,
    admin_identity_status: "active",
  };
}

async function ensureUniqueEmail(tx: PrismaTransaction, email: string) {
  const existingUser = await tx.usuarios.findFirst({
    where: { email },
    select: { id: true },
  });

  if (existingUser) {
    throw new Error("E-mail já cadastrado.");
  }
}

async function ensureUserCapacity(tx: PrismaTransaction, companyId: number, plan: string, additionalUsers = 1) {
  const [limits, totalUsers] = await Promise.all([
    tx.limites_plano.findUnique({
      where: { plano: plan },
    }),
    tx.usuarios.count({
      where: { empresa_id: companyId },
    }),
  ]);

  if (!limits) {
    throw new Error("Plano não encontrado.");
  }

  if (limits.usuarios_max != null && totalUsers + additionalUsers > limits.usuarios_max) {
    throw new Error(`Limite de usuários do plano atingido (${limits.usuarios_max}).`);
  }
}

async function getCompanyUserOrThrow(tx: PrismaTransaction, companyId: number, userId: number) {
  const user = await tx.usuarios.findFirst({
    where: {
      id: userId,
      empresa_id: companyId,
    },
    select: {
      id: true,
      nome_completo: true,
      email: true,
      ativo: true,
      tentativas_login: true,
      nivel_acesso: true,
      empresas: {
        select: {
          nome_fantasia: true,
        },
      },
    },
  });

  if (!user) {
    throw new Error("Usuário da empresa não encontrado.");
  }

  return user;
}

async function createAudit(
  tx: PrismaTransaction,
  {
    companyId,
    actorUserId,
    action,
    summary,
    detail,
    payload,
    targetUserId,
  }: {
    companyId: number;
    actorUserId?: number | null;
    action: string;
    summary: string;
    detail?: string;
    payload?: Prisma.InputJsonObject;
    targetUserId?: number;
  },
) {
  await tx.auditoria_empresas.create({
    data: {
      empresa_id: companyId,
      ator_usuario_id: actorUserId ?? null,
      alvo_usuario_id: targetUserId ?? null,
      portal: "admin",
      acao: action,
      resumo: summary.slice(0, 220),
      detalhe: detail ? detail.slice(0, 5_000) : null,
      payload_json: payload,
      criado_em: new Date(),
    },
  });
}

type PrismaTransaction = Parameters<Parameters<typeof prisma.$transaction>[0]>[0];
