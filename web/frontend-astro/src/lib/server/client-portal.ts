import { randomUUID } from "node:crypto";

import { Prisma } from "@/generated/prisma/client";

import {
  getAdminClientDetail,
  type AdminClientDetailData,
} from "@/lib/server/admin-clients";
import {
  generateStrongPassword,
  hashPassword,
} from "@/lib/server/passwords";
import { prisma } from "@/lib/server/prisma";

const ACCESS_LEVELS = {
  inspector: 1,
  reviewer: 50,
  clientAdmin: 80,
} as const;

const PLAN_OPTIONS = ["Inicial", "Intermediario", "Ilimitado"] as const;

type ClientPlanOption = (typeof PLAN_OPTIONS)[number];
type ClientTeamRole = "inspetor" | "revisor";
type ClientSupportOrigin = "admin" | "chat" | "mesa";

export interface ClientPortalTeamMember {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  crea: string | null;
  accessLevel: number;
  role: ClientTeamRole;
  roleLabel: string;
  portalLabel: string;
  loginUrl: string;
  active: boolean;
  blocked: boolean;
  temporaryPasswordActive: boolean;
  lastLoginAt: Date | null;
  lastLoginLabel: string;
  lastActivityAt: Date | null;
  lastActivityLabel: string;
  sessionCount: number;
}

export interface ClientPortalTeamData {
  detail: AdminClientDetailData;
  members: ClientPortalTeamMember[];
  summary: {
    total: number;
    inspectors: number;
    reviewers: number;
    blocked: number;
    temporaryPasswords: number;
    withSessions: number;
    capacityLabel: string;
  };
}

export interface ClientPortalSupportAuditEntry {
  id: number;
  portal: string;
  action: string;
  summary: string;
  detail: string | null;
  createdAt: Date;
}

export interface ClientPortalSupportPlanCard {
  plan: ClientPlanOption;
  current: boolean;
  movement: "upgrade" | "downgrade" | "same";
  summary: string;
}

export interface ClientPortalSupportData {
  detail: AdminClientDetailData;
  recentAudit: ClientPortalSupportAuditEntry[];
  planCards: ClientPortalSupportPlanCard[];
}

export interface ClientCreateOperationalUserInput {
  companyId: number;
  actorUserId: number;
  role: ClientTeamRole;
  name: string;
  email: string;
  phone?: string | null;
  crea?: string | null;
}

export interface ClientCreateOperationalUserResult {
  companyName: string;
  userId: number;
  userName: string;
  roleLabel: string;
  portalLabel: string;
  loginUrl: string;
  email: string;
  password: string;
}

export interface ClientResetOperationalUserPasswordResult {
  companyName: string;
  userId: number;
  userName: string;
  portalLabel: string;
  loginUrl: string;
  email: string;
  password: string;
}

export interface ClientToggleOperationalUserStatusResult {
  companyName: string;
  userId: number;
  userName: string;
  active: boolean;
}

export interface ClientSupportReportResult {
  protocol: string;
  status: "Recebido";
}

export interface ClientPlanInterestResult {
  currentPlan: ClientPlanOption;
  requestedPlan: ClientPlanOption;
  movement: "upgrade" | "downgrade";
}

export async function getClientPortalOverview(companyId: number) {
  return getAdminClientDetail(companyId);
}

export async function getClientPortalTeamData(companyId: number): Promise<ClientPortalTeamData | null> {
  const detail = await getAdminClientDetail(companyId);

  if (!detail) {
    return null;
  }

  const users = await prisma.usuarios.findMany({
    where: {
      empresa_id: companyId,
      nivel_acesso: {
        in: [ACCESS_LEVELS.inspector, ACCESS_LEVELS.reviewer],
      },
    },
    orderBy: [{ nivel_acesso: "desc" }, { nome_completo: "asc" }],
    select: {
      id: true,
      nome_completo: true,
      email: true,
      telefone: true,
      crea: true,
      nivel_acesso: true,
      ativo: true,
      status_bloqueio: true,
      senha_temporaria_ativa: true,
      ultimo_login: true,
      sessoes_ativas: {
        orderBy: {
          ultima_atividade_em: "desc",
        },
        select: {
          token: true,
          ultima_atividade_em: true,
        },
      },
    },
  });

  const members = users.map((user) => {
    const role = roleFromAccessLevel(user.nivel_acesso);
    const latestActivity = user.sessoes_ativas[0]?.ultima_atividade_em ?? null;

    return {
      id: user.id,
      name: user.nome_completo,
      email: user.email,
      phone: normalizeNullableText(user.telefone),
      crea: normalizeNullableText(user.crea),
      accessLevel: user.nivel_acesso,
      role,
      roleLabel: roleMeta(role).label,
      portalLabel: roleMeta(role).portalLabel,
      loginUrl: roleMeta(role).loginUrl,
      active: Boolean(user.ativo),
      blocked: !user.ativo || Boolean(user.status_bloqueio),
      temporaryPasswordActive: Boolean(user.senha_temporaria_ativa),
      lastLoginAt: user.ultimo_login,
      lastLoginLabel: formatDateTime(user.ultimo_login, "Nunca acessou"),
      lastActivityAt: latestActivity,
      lastActivityLabel: formatDateTime(latestActivity, "Sem sessão recente"),
      sessionCount: user.sessoes_ativas.length,
    } satisfies ClientPortalTeamMember;
  });

  const withSessions = members.filter((member) => member.sessionCount > 0).length;
  const userLimit = detail.limits.usuariosMax;
  const capacityLabel =
    userLimit == null
      ? `${detail.summary.totalUsuarios} usuários ativos sem teto contratual exposto.`
      : `${detail.summary.totalUsuarios} de ${userLimit} usuários do plano em uso.`;

  return {
    detail,
    members,
    summary: {
      total: members.length,
      inspectors: members.filter((member) => member.role === "inspetor").length,
      reviewers: members.filter((member) => member.role === "revisor").length,
      blocked: members.filter((member) => member.blocked).length,
      temporaryPasswords: members.filter((member) => member.temporaryPasswordActive).length,
      withSessions,
      capacityLabel,
    },
  };
}

export async function getClientPortalSupportData(companyId: number): Promise<ClientPortalSupportData | null> {
  const detail = await getAdminClientDetail(companyId);

  if (!detail) {
    return null;
  }

  const recentAudit = await prisma.auditoria_empresas.findMany({
    where: {
      empresa_id: companyId,
    },
    orderBy: {
      criado_em: "desc",
    },
    take: 18,
    select: {
      id: true,
      portal: true,
      acao: true,
      resumo: true,
      detalhe: true,
      criado_em: true,
    },
  });

  return {
    detail,
    recentAudit: recentAudit.map((entry) => ({
      id: entry.id,
      portal: entry.portal,
      action: entry.acao,
      summary: entry.resumo,
      detail: entry.detalhe,
      createdAt: entry.criado_em,
    })),
    planCards: PLAN_OPTIONS.map((plan) => ({
      plan,
      current: plan === detail.company.planoAtivo,
      movement: describePlanMovement(detail.company.planoAtivo, plan),
      summary: summarizePlanMovement(detail.company.planoAtivo, plan),
    })),
  };
}

export async function buildClientDiagnosticSnapshot(companyId: number) {
  const [overview, team, support] = await Promise.all([
    getClientPortalOverview(companyId),
    getClientPortalTeamData(companyId),
    getClientPortalSupportData(companyId),
  ]);

  if (!overview || !team || !support) {
    return null;
  }

  return {
    generatedAt: new Date().toISOString(),
    company: overview.company,
    status: overview.status,
    health: overview.health,
    summary: overview.summary,
    firstAccess: overview.firstAccess,
    limits: overview.limits,
    team: {
      summary: team.summary,
      members: team.members,
    },
    support: {
      planCards: support.planCards,
      recentAudit: support.recentAudit,
    },
    recentReports: overview.recentReports,
    catalogPortfolio: overview.catalogPortfolio,
  };
}

export async function createClientOperationalUser(
  input: ClientCreateOperationalUserInput,
): Promise<ClientCreateOperationalUserResult> {
  const role = normalizeRole(input.role);
  const accessLevel = role === "inspetor" ? ACCESS_LEVELS.inspector : ACCESS_LEVELS.reviewer;
  const companyId = normalizePositiveInt(input.companyId, "Empresa");
  const actorUserId = normalizePositiveInt(input.actorUserId, "Operador");
  const name = normalizeRequiredText(input.name, "Nome", 150);
  const email = normalizeEmail(input.email);
  const phone = normalizeOptionalText(input.phone, 30);
  const crea = normalizeOptionalText(input.crea, 40);
  const password = generateStrongPassword();
  const passwordHash = await hashPassword(password);

  return prisma.$transaction(async (tx) => {
    const company = await tx.empresas.findUnique({
      where: {
        id: companyId,
      },
      select: {
        id: true,
        nome_fantasia: true,
        plano_ativo: true,
      },
    });

    if (!company) {
      throw new Error("Empresa não encontrada.");
    }

    await ensureUniqueEmail(tx, email);
    await ensureUserCapacity(tx, company.id, company.plano_ativo, 1);

    const now = new Date();
    const created = await tx.usuarios.create({
      data: {
        empresa_id: company.id,
        nome_completo: name,
        email,
        telefone: phone,
        crea: crea,
        senha_hash: passwordHash,
        nivel_acesso: accessLevel,
        ativo: true,
        tentativas_login: 0,
        status_bloqueio: false,
        blocked_reason: null,
        senha_temporaria_ativa: true,
        criado_em: now,
        atualizado_em: now,
        account_scope: "tenant",
        account_status: "active",
        allowed_portals_json: [roleMeta(role).portalKey],
        mfa_required: false,
        can_password_login: true,
        can_google_login: false,
        can_microsoft_login: false,
        portal_admin_autorizado: false,
        admin_identity_status: "active",
      },
      select: {
        id: true,
        nome_completo: true,
        email: true,
      },
    });

    await createClientAudit(tx, {
      companyId: company.id,
      actorUserId,
      action: "usuario_criado",
      targetUserId: created.id,
      summary: `${roleMeta(role).label} ${created.nome_completo} criado no portal cliente.`,
      detail: `Cadastro emitido com acesso inicial via ${roleMeta(role).portalLabel.toLowerCase()}.`,
      payload: {
        role,
        login_url: roleMeta(role).loginUrl,
      },
    });

    return {
      companyName: company.nome_fantasia,
      userId: created.id,
      userName: created.nome_completo,
      roleLabel: roleMeta(role).label,
      portalLabel: roleMeta(role).portalLabel,
      loginUrl: roleMeta(role).loginUrl,
      email: created.email,
      password,
    } satisfies ClientCreateOperationalUserResult;
  });
}

export async function resetClientOperationalUserPassword(
  companyId: number,
  userId: number,
  actorUserId: number,
): Promise<ClientResetOperationalUserPasswordResult> {
  const nextPassword = generateStrongPassword();
  const passwordHash = await hashPassword(nextPassword);

  return prisma.$transaction(async (tx) => {
    const user = await getOperationalUserOrThrow(tx, companyId, userId);

    await tx.usuarios.update({
      where: {
        id: user.id,
      },
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
        usuario_id: user.id,
      },
    });

    await createClientAudit(tx, {
      companyId,
      actorUserId,
      action: "senha_resetada",
      targetUserId: user.id,
      summary: `Senha temporária regenerada para ${user.nome_completo}.`,
      detail: "O próximo login exigirá troca obrigatória de senha no portal correspondente.",
      payload: {
        login_url: roleMeta(roleFromAccessLevel(user.nivel_acesso)).loginUrl,
      },
    });

    return {
      companyName: user.empresas.nome_fantasia,
      userId: user.id,
      userName: user.nome_completo,
      portalLabel: roleMeta(roleFromAccessLevel(user.nivel_acesso)).portalLabel,
      loginUrl: roleMeta(roleFromAccessLevel(user.nivel_acesso)).loginUrl,
      email: user.email,
      password: nextPassword,
    } satisfies ClientResetOperationalUserPasswordResult;
  });
}

export async function toggleClientOperationalUserStatus(
  companyId: number,
  userId: number,
  actorUserId: number,
): Promise<ClientToggleOperationalUserStatusResult> {
  return prisma.$transaction(async (tx) => {
    const user = await getOperationalUserOrThrow(tx, companyId, userId);
    const nextActive = !user.ativo;

    await tx.usuarios.update({
      where: {
        id: user.id,
      },
      data: {
        ativo: nextActive,
        status_bloqueio: !nextActive,
        bloqueado_ate: null,
        tentativas_login: nextActive ? 0 : user.tentativas_login,
        blocked_reason: nextActive ? null : "Bloqueado pelo admin-cliente migrado.",
        atualizado_em: new Date(),
      },
    });

    await tx.sessoes_ativas.deleteMany({
      where: {
        usuario_id: user.id,
      },
    });

    await createClientAudit(tx, {
      companyId,
      actorUserId,
      action: "usuario_bloqueio_alterado",
      targetUserId: user.id,
      summary: `${user.nome_completo} foi ${nextActive ? "reativado" : "bloqueado"} no portal cliente.`,
    });

    return {
      companyName: user.empresas.nome_fantasia,
      userId: user.id,
      userName: user.nome_completo,
      active: nextActive,
    } satisfies ClientToggleOperationalUserStatusResult;
  });
}

export async function createClientSupportReport(input: {
  companyId: number;
  actorUserId: number;
  type: "bug" | "feedback";
  title?: string | null;
  message: string;
  replyEmail?: string | null;
  context?: string | null;
}) {
  const companyId = normalizePositiveInt(input.companyId, "Empresa");
  const actorUserId = normalizePositiveInt(input.actorUserId, "Operador");
  const type = input.type === "bug" ? "bug" : "feedback";
  const title = normalizeOptionalText(input.title, 120);
  const message = normalizeRequiredText(input.message, "Mensagem", 4_000);
  const replyEmail = normalizeOptionalEmail(input.replyEmail);
  const contextLabel = normalizeOptionalText(input.context, 500);
  const protocol = `CLI-${randomUUID().replace(/-/g, "").slice(0, 8).toUpperCase()}`;

  await prisma.$transaction(async (tx) => {
    await ensureCompanyExists(tx, companyId);
    await createClientAudit(tx, {
      companyId,
      actorUserId,
      action: "suporte_reportado",
      summary: `Relato de suporte ${type} registrado com protocolo ${protocol}.`,
      detail: title ?? message.slice(0, 220),
      payload: {
        protocol,
        type,
        reply_email: replyEmail,
        context: contextLabel,
      },
    });
  });

  return {
    protocol,
    status: "Recebido",
  } satisfies ClientSupportReportResult;
}

export async function registerClientPlanInterest(input: {
  companyId: number;
  actorUserId: number;
  requestedPlan: ClientPlanOption;
  origin: ClientSupportOrigin;
}) {
  const companyId = normalizePositiveInt(input.companyId, "Empresa");
  const actorUserId = normalizePositiveInt(input.actorUserId, "Operador");
  const requestedPlan = normalizePlanOption(input.requestedPlan);
  const origin = normalizeSupportOrigin(input.origin);

  return prisma.$transaction(async (tx) => {
    const company = await tx.empresas.findUnique({
      where: {
        id: companyId,
      },
      select: {
        id: true,
        plano_ativo: true,
      },
    });

    if (!company) {
      throw new Error("Empresa não encontrada.");
    }

    const currentPlan = normalizePlanOption(company.plano_ativo);

    if (requestedPlan === currentPlan) {
      throw new Error("Selecione um plano diferente do atual.");
    }

    const movement = describePlanMovement(currentPlan, requestedPlan);

    if (movement === "same") {
      throw new Error("Selecione um plano diferente do atual.");
    }

    await createClientAudit(tx, {
      companyId,
      actorUserId,
      action: "plano_interesse_registrado",
      summary: `Interesse registrado em migrar de ${currentPlan} para ${requestedPlan}.`,
      detail: `Origem ${origin}. Solicitação encaminhada para análise comercial da Tariel.`,
      payload: {
        current_plan: currentPlan,
        requested_plan: requestedPlan,
        origin,
        movement,
      },
    });

    return {
      currentPlan,
      requestedPlan,
      movement,
    } satisfies ClientPlanInterestResult;
  });
}

function normalizePositiveInt(value: number, field: string) {
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`${field} inválido.`);
  }

  return value;
}

function normalizeRequiredText(value: string | null | undefined, field: string, maxLength: number) {
  const normalized = String(value ?? "").trim();

  if (!normalized) {
    throw new Error(`${field} é obrigatório.`);
  }

  if (normalized.length > maxLength) {
    throw new Error(`${field} excede ${maxLength} caracteres.`);
  }

  return normalized;
}

function normalizeOptionalText(value: string | null | undefined, maxLength: number) {
  const normalized = String(value ?? "").trim();
  return normalized ? normalized.slice(0, maxLength) : null;
}

function normalizeNullableText(value: string | null | undefined) {
  const normalized = String(value ?? "").trim();
  return normalized || null;
}

function normalizeEmail(value: string | null | undefined) {
  const normalized = String(value ?? "").trim().toLowerCase();

  if (!normalized || !normalized.includes("@")) {
    throw new Error("Informe um e-mail válido.");
  }

  if (normalized.length > 254) {
    throw new Error("O e-mail excede 254 caracteres.");
  }

  return normalized;
}

function normalizeOptionalEmail(value: string | null | undefined) {
  const normalized = String(value ?? "").trim().toLowerCase();

  if (!normalized) {
    return null;
  }

  return normalizeEmail(normalized);
}

function normalizeRole(value: string | null | undefined): ClientTeamRole {
  return value === "revisor" ? "revisor" : "inspetor";
}

function normalizePlanOption(value: string | null | undefined): ClientPlanOption {
  if (value === "Inicial" || value === "Intermediario" || value === "Ilimitado") {
    return value;
  }

  throw new Error("Plano inválido.");
}

function normalizeSupportOrigin(value: string | null | undefined): ClientSupportOrigin {
  if (value === "chat" || value === "mesa") {
    return value;
  }

  return "admin";
}

function roleFromAccessLevel(value: number): ClientTeamRole {
  return Number(value) === ACCESS_LEVELS.reviewer ? "revisor" : "inspetor";
}

function roleMeta(role: ClientTeamRole) {
  if (role === "revisor") {
    return {
      label: "Mesa Avaliadora",
      portalLabel: "Mesa Avaliadora",
      portalKey: "revisor",
      loginUrl: "/revisao/login",
    };
  }

  return {
    label: "Equipe de campo",
    portalLabel: "Inspetor web + mobile",
    portalKey: "inspetor",
    loginUrl: "/app/login",
  };
}

function describePlanMovement(currentPlan: string, requestedPlan: ClientPlanOption) {
  if (currentPlan === requestedPlan) {
    return "same";
  }

  return planRank(requestedPlan) > planRank(currentPlan) ? "upgrade" : "downgrade";
}

function summarizePlanMovement(currentPlan: string, requestedPlan: ClientPlanOption) {
  const movement = describePlanMovement(currentPlan, requestedPlan);

  if (movement === "same") {
    return "Plano já ativo no tenant.";
  }

  if (movement === "upgrade") {
    return `Migração sugerida de ${currentPlan} para ${requestedPlan} para abrir mais capacidade operacional.`;
  }

  return `Mudança de ${currentPlan} para ${requestedPlan} para adequar custo e operação ao volume atual.`;
}

function planRank(value: string) {
  switch (value) {
    case "Inicial":
      return 0;
    case "Intermediario":
      return 1;
    case "Ilimitado":
      return 2;
    default:
      return 0;
  }
}

function formatDateTime(value: Date | null | undefined, fallback: string) {
  if (!value) {
    return fallback;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(value);
}

async function ensureCompanyExists(tx: PrismaTransaction, companyId: number) {
  const company = await tx.empresas.findUnique({
    where: {
      id: companyId,
    },
    select: {
      id: true,
    },
  });

  if (!company) {
    throw new Error("Empresa não encontrada.");
  }
}

async function ensureUniqueEmail(tx: PrismaTransaction, email: string) {
  const existingUser = await tx.usuarios.findFirst({
    where: {
      email,
    },
    select: {
      id: true,
    },
  });

  if (existingUser) {
    throw new Error("E-mail já cadastrado.");
  }
}

async function ensureUserCapacity(
  tx: PrismaTransaction,
  companyId: number,
  plan: string,
  additionalUsers: number,
) {
  const [limits, totalUsers] = await Promise.all([
    tx.limites_plano.findUnique({
      where: {
        plano: plan,
      },
    }),
    tx.usuarios.count({
      where: {
        empresa_id: companyId,
      },
    }),
  ]);

  if (!limits) {
    throw new Error("Plano da empresa não encontrado.");
  }

  if (limits.usuarios_max != null && totalUsers + additionalUsers > limits.usuarios_max) {
    throw new Error(`Limite de usuários do plano atingido (${limits.usuarios_max}).`);
  }
}

async function getOperationalUserOrThrow(
  tx: PrismaTransaction,
  companyId: number,
  userId: number,
) {
  const user = await tx.usuarios.findFirst({
    where: {
      id: userId,
      empresa_id: companyId,
      nivel_acesso: {
        in: [ACCESS_LEVELS.inspector, ACCESS_LEVELS.reviewer],
      },
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
    throw new Error("Usuário operacional não encontrado para esta empresa.");
  }

  return user;
}

async function createClientAudit(
  tx: PrismaTransaction,
  input: {
    companyId: number;
    actorUserId: number;
    action: string;
    summary: string;
    detail?: string | null;
    targetUserId?: number | null;
    payload?: Record<string, unknown>;
  },
) {
  await tx.auditoria_empresas.create({
    data: {
      empresa_id: input.companyId,
      ator_usuario_id: input.actorUserId,
      alvo_usuario_id: input.targetUserId ?? null,
      portal: "cliente",
      acao: input.action,
      resumo: input.summary.slice(0, 220),
      detalhe: input.detail ? input.detail.slice(0, 5_000) : null,
      payload_json: (input.payload ?? null) as Prisma.InputJsonValue,
      criado_em: new Date(),
    },
  });
}

type PrismaTransaction = Parameters<Parameters<typeof prisma.$transaction>[0]>[0];
