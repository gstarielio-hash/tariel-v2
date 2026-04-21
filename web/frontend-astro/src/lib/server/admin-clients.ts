import { prisma } from "@/lib/server/prisma";
import {
  getAdminTenantCatalogSnapshot,
  type AdminTenantCatalogSnapshot,
} from "@/lib/server/admin-tenant-catalog";

const ACCESS_LEVELS = {
  inspector: 1,
  reviewer: 50,
  clientAdmin: 80,
} as const;

const PLAN_PRIORITY = {
  Inicial: 0,
  Intermediario: 1,
  Ilimitado: 2,
} as const;

type ClientStatus = "ativo" | "bloqueado" | "pendente";
type ClientHealth = "ok" | "alerta" | "critico";
type SortKey = "nome" | "criacao" | "ultimo_acesso" | "plano" | "saude";
type SortDirection = "asc" | "desc";
type ActivityFilter = "" | "24h" | "7d" | "30d" | "sem_atividade";

export interface AdminClientListQuery {
  nome?: string | null;
  codigo?: string | null;
  plano?: string | null;
  status?: string | null;
  saude?: string | null;
  atividade?: string | null;
  ordenar?: string | null;
  direcao?: string | null;
  pagina?: string | number | null;
  porPagina?: string | number | null;
}

export interface AdminClientListFilters {
  nome: string;
  codigo: string;
  plano: "" | "Inicial" | "Intermediario" | "Ilimitado";
  status: "" | ClientStatus;
  saude: "" | ClientHealth;
  atividade: ActivityFilter;
  ordenar: SortKey;
  direcao: SortDirection;
  pagina: number;
  porPagina: number;
}

export interface AdminClientListItem {
  id: number;
  nomeFantasia: string;
  cnpj: string;
  planoAtivo: string;
  cidadeEstado: string | null;
  criadoEm: Date;
  totalUsuarios: number;
  adminsTotal: number;
  inspetoresTotal: number;
  revisoresTotal: number;
  sessoesAtivasTotal: number;
  usoAtual: number;
  limiteLaudos: number | null;
  usoPercentual: number | null;
  usoLabel: string;
  ultimoAcessoEm: Date | null;
  ultimoAcessoLabel: string;
  totalLaudos: number;
  statusValue: ClientStatus;
  statusLabel: string;
  statusTone: "success" | "warning" | "danger";
  saudeValue: ClientHealth;
  saudeLabel: string;
  saudeTone: "success" | "warning" | "danger";
  saudeRazao: string;
  motivoBloqueio: string | null;
}

export interface AdminClientListData {
  items: AdminClientListItem[];
  totals: {
    clientesTotal: number;
    ativos: number;
    bloqueados: number;
    pendentes: number;
    alerta: number;
    semAtividade: number;
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
  filters: AdminClientListFilters;
}

export interface AdminClientUserSummary {
  id: number;
  nomeCompleto: string;
  email: string;
  nivelAcesso: number;
  roleLabel: string;
  ativo: boolean;
  statusBloqueio: boolean;
  senhaTemporariaAtiva: boolean;
  ultimoLogin: Date | null;
  ultimoAcessoEm: Date | null;
  ultimoAcessoLabel: string;
  sessionCount: number;
}

export interface AdminClientSessionSummary {
  token: string;
  usuarioId: number;
  usuarioNome: string;
  usuarioEmail: string;
  roleLabel: string;
  portal: string | null;
  ultimaAtividadeEm: Date | null;
  ultimaAtividadeLabel: string;
  expiraEm: Date | null;
  expiraEmLabel: string;
}

export interface AdminClientReportSummary {
  id: number;
  setor: string;
  template: string;
  revisao: string;
  conformidade: string;
  entryMode: string;
  criadoEm: Date;
}

export interface AdminClientAuditSummary {
  id: number;
  portal: string;
  acao: string;
  resumo: string;
  criadoEm: Date;
  atorUsuarioId: number | null;
  alvoUsuarioId: number | null;
}

export interface AdminClientDetailData {
  company: {
    id: number;
    nomeFantasia: string;
    cnpj: string;
    planoAtivo: string;
    cidadeEstado: string | null;
    segmento: string | null;
    nomeResponsavel: string | null;
    observacoes: string | null;
    criadoEm: Date;
    custoGeradoReais: number;
    mensagensProcessadas: number;
    statusBloqueio: boolean;
    motivoBloqueio: string | null;
    adminPolicyJson: unknown;
  };
  status: {
    value: ClientStatus;
    label: string;
    tone: "success" | "warning" | "danger";
    blockedReason: string | null;
  };
  health: {
    value: ClientHealth;
    label: string;
    tone: "success" | "warning" | "danger";
    reason: string;
  };
  firstAccess: {
    hasAdmin: boolean;
    statusLabel: string;
    adminName: string;
    adminEmail: string;
    loginPrefillUrl: string;
    requiresPasswordReset: boolean;
  };
  limits: {
    laudosMes: number | null;
    usuariosMax: number | null;
    uploadDoc: boolean;
    deepResearch: boolean;
    integracoesMax: number | null;
    retencaoDias: number | null;
  };
  summary: {
    totalUsuarios: number;
    adminsTotal: number;
    inspetoresTotal: number;
    revisoresTotal: number;
    sessoesAtivasTotal: number;
    usuariosComSessaoAtiva: number;
    usuariosBloqueados: number;
    trocaSenhaPendente: number;
    totalLaudos: number;
    templates: number;
    activeReleases: number;
    activeSignatories: number;
    totalAuditEvents: number;
    usoAtual: number;
    usoPercentual: number | null;
    usoLabel: string;
    custoTotal: number;
    ultimoAcessoEm: Date | null;
    ultimoAcessoLabel: string;
  };
  catalogPortfolio: AdminTenantCatalogSnapshot;
  admins: AdminClientUserSummary[];
  operationalUsers: AdminClientUserSummary[];
  sessions: AdminClientSessionSummary[];
  recentReports: AdminClientReportSummary[];
  recentAudit: AdminClientAuditSummary[];
}

const dateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

function formatDateTime(value: Date | null | undefined, fallback = "Sem atividade") {
  return value ? dateTimeFormatter.format(value) : fallback;
}

function normalizeDigits(value: string | null | undefined) {
  return String(value ?? "").replace(/\D+/g, "");
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

function normalizePlan(value: string | null | undefined): AdminClientListFilters["plano"] {
  if (value === "Inicial" || value === "Intermediario" || value === "Ilimitado") {
    return value;
  }

  return "";
}

function normalizeStatus(value: string | null | undefined): AdminClientListFilters["status"] {
  if (value === "ativo" || value === "bloqueado" || value === "pendente") {
    return value;
  }

  return "";
}

function normalizeHealth(value: string | null | undefined): AdminClientListFilters["saude"] {
  if (value === "ok" || value === "alerta" || value === "critico") {
    return value;
  }

  return "";
}

function normalizeActivity(value: string | null | undefined): ActivityFilter {
  if (value === "24h" || value === "7d" || value === "30d" || value === "sem_atividade") {
    return value;
  }

  return "";
}

function normalizeSort(value: string | null | undefined): SortKey {
  if (value === "criacao" || value === "ultimo_acesso" || value === "plano" || value === "saude") {
    return value;
  }

  return "nome";
}

function normalizeDirection(value: string | null | undefined): SortDirection {
  return value === "desc" ? "desc" : "asc";
}

function roleLabel(level: number) {
  if (level === ACCESS_LEVELS.clientAdmin) {
    return "Administrador da empresa";
  }

  if (level === ACCESS_LEVELS.reviewer) {
    return "Equipe de analise";
  }

  return "Equipe de campo";
}

function labelLimit(value: number | null | undefined) {
  return value == null ? "Ilimitado" : String(value);
}

function buildUsageLabel(current: number, limit: number | null) {
  return limit == null ? `${current} / Ilimitado` : `${current} / ${labelLimit(limit)}`;
}

function calculateUsagePercentage(current: number, limit: number | null) {
  if (limit == null || limit <= 0) {
    return null;
  }

  return Math.min(999, Math.trunc((current / limit) * 100));
}

function getLatestActivity(dates: Array<Date | null | undefined>) {
  const validDates = dates.filter((value): value is Date => value instanceof Date);

  if (validDates.length === 0) {
    return null;
  }

  return validDates.reduce((latest, current) => (current > latest ? current : latest));
}

function getStatusFromCompany({
  blocked,
  admins,
}: {
  blocked: boolean;
  admins: Array<{ senhaTemporariaAtiva: boolean }>;
}): {
  value: ClientStatus;
  label: string;
  tone: "success" | "warning" | "danger";
} {
  if (blocked) {
    return {
      value: "bloqueado",
      label: "Bloqueado",
      tone: "danger",
    };
  }

  if (admins.length === 0 || admins.some((admin) => admin.senhaTemporariaAtiva)) {
    return {
      value: "pendente",
      label: "Pendente",
      tone: "warning",
    };
  }

  return {
    value: "ativo",
    label: "Ativo",
    tone: "success",
  };
}

function getHealthFromCompany({
  status,
  adminsTotal,
  inspetoresTotal,
  revisoresTotal,
  ultimoAcesso,
  usoPercentual,
}: {
  status: ClientStatus;
  adminsTotal: number;
  inspetoresTotal: number;
  revisoresTotal: number;
  ultimoAcesso: Date | null;
  usoPercentual: number | null;
}): {
  value: ClientHealth;
  label: string;
  tone: "success" | "warning" | "danger";
  reason: string;
} {
  const now = new Date();
  const inactivityThreshold = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

  if (status === "bloqueado") {
    return {
      value: "critico",
      label: "Crítico",
      tone: "danger",
      reason: "Tenant bloqueado",
    };
  }

  if (adminsTotal === 0) {
    return {
      value: "critico",
      label: "Crítico",
      tone: "danger",
      reason: "Sem administrador da empresa configurado",
    };
  }

  if (usoPercentual != null && usoPercentual >= 100) {
    return {
      value: "critico",
      label: "Crítico",
      tone: "danger",
      reason: "Capacidade do plano esgotada",
    };
  }

  if (status === "pendente") {
    return {
      value: "alerta",
      label: "Alerta",
      tone: "warning",
      reason: "Onboarding ou troca de senha pendente",
    };
  }

  if (inspetoresTotal === 0 && revisoresTotal === 0) {
    return {
      value: "alerta",
      label: "Alerta",
      tone: "warning",
      reason: "Sem equipe operacional ativa",
    };
  }

  if (usoPercentual != null && usoPercentual >= 80) {
    return {
      value: "alerta",
      label: "Alerta",
      tone: "warning",
      reason: "Uso acima de 80% do plano",
    };
  }

  if (!ultimoAcesso || ultimoAcesso < inactivityThreshold) {
    return {
      value: "alerta",
      label: "Alerta",
      tone: "warning",
      reason: "Sem atividade recente",
    };
  }

  return {
    value: "ok",
    label: "OK",
    tone: "success",
    reason: "Operação dentro do esperado",
  };
}

function matchesActivity(ultimoAcesso: Date | null, filter: ActivityFilter) {
  if (!filter) {
    return true;
  }

  const now = Date.now();

  if (filter === "sem_atividade") {
    return !ultimoAcesso || ultimoAcesso.getTime() < now - 30 * 24 * 60 * 60 * 1000;
  }

  if (!ultimoAcesso) {
    return false;
  }

  if (filter === "24h") {
    return ultimoAcesso.getTime() >= now - 24 * 60 * 60 * 1000;
  }

  if (filter === "7d") {
    return ultimoAcesso.getTime() >= now - 7 * 24 * 60 * 60 * 1000;
  }

  if (filter === "30d") {
    return ultimoAcesso.getTime() >= now - 30 * 24 * 60 * 60 * 1000;
  }

  return true;
}

function toNumber(value: unknown) {
  if (value == null) {
    return 0;
  }

  if (typeof value === "number") {
    return value;
  }

  if (typeof value === "bigint") {
    return Number(value);
  }

  if (typeof value === "object" && value && "toNumber" in value) {
    const decimalLike = value as { toNumber?: () => number };

    if (typeof decimalLike.toNumber === "function") {
      return decimalLike.toNumber();
    }
  }

  return Number(String(value));
}

function serializeUser(user: {
  id: number;
  nome_completo: string;
  email: string;
  nivel_acesso: number;
  ativo: boolean;
  status_bloqueio: boolean;
  senha_temporaria_ativa: boolean;
  ultimo_login: Date | null;
  sessoes_ativas: Array<{
    ultima_atividade_em: Date;
  }>;
}): AdminClientUserSummary {
  const ultimoAcessoEm = getLatestActivity([
    user.ultimo_login,
    ...user.sessoes_ativas.map((session) => session.ultima_atividade_em),
  ]);

  return {
    id: user.id,
    nomeCompleto: user.nome_completo,
    email: user.email,
    nivelAcesso: user.nivel_acesso,
    roleLabel: roleLabel(user.nivel_acesso),
    ativo: user.ativo,
    statusBloqueio: user.status_bloqueio,
    senhaTemporariaAtiva: user.senha_temporaria_ativa,
    ultimoLogin: user.ultimo_login,
    ultimoAcessoEm,
    ultimoAcessoLabel: formatDateTime(ultimoAcessoEm),
    sessionCount: user.sessoes_ativas.length,
  };
}

export async function getAdminClientList(query: AdminClientListQuery = {}): Promise<AdminClientListData> {
  const filters: AdminClientListFilters = {
    nome: normalizeText(query.nome),
    codigo: normalizeDigits(query.codigo),
    plano: normalizePlan(query.plano),
    status: normalizeStatus(query.status),
    saude: normalizeHealth(query.saude),
    atividade: normalizeActivity(query.atividade),
    ordenar: normalizeSort(query.ordenar),
    direcao: normalizeDirection(query.direcao),
    pagina: normalizePage(query.pagina, 1, 1, 999),
    porPagina: normalizePage(query.porPagina, 20, 5, 100),
  };

  const companies = await prisma.empresas.findMany({
    where: {
      ...(filters.nome
        ? {
            nome_fantasia: {
              contains: filters.nome,
              mode: "insensitive",
            },
          }
        : {}),
      ...(filters.plano ? { plano_ativo: filters.plano } : {}),
      ...(filters.codigo && filters.codigo.length <= 9 ? { id: Number(filters.codigo) } : {}),
    },
    orderBy: [{ nome_fantasia: "asc" }, { id: "asc" }],
    select: {
      id: true,
      nome_fantasia: true,
      cnpj: true,
      plano_ativo: true,
      mensagens_processadas: true,
      status_bloqueio: true,
      motivo_bloqueio: true,
      criado_em: true,
      cidade_estado: true,
    },
  });

  const companyIds = companies.map((company) => company.id);
  const [planLimits, users, reportCounts] = await Promise.all([
    prisma.limites_plano.findMany(),
    companyIds.length > 0
      ? prisma.usuarios.findMany({
          where: {
            empresa_id: {
              in: companyIds,
            },
          },
          orderBy: [{ nivel_acesso: "desc" }, { nome_completo: "asc" }],
          select: {
            id: true,
            empresa_id: true,
            nome_completo: true,
            email: true,
            nivel_acesso: true,
            ativo: true,
            status_bloqueio: true,
            senha_temporaria_ativa: true,
            ultimo_login: true,
            sessoes_ativas: {
              select: {
                ultima_atividade_em: true,
              },
            },
          },
        })
      : Promise.resolve([]),
    companyIds.length > 0
      ? prisma.laudos.groupBy({
          by: ["empresa_id"],
          where: {
            empresa_id: {
              in: companyIds,
            },
          },
          _count: {
            _all: true,
          },
        })
      : Promise.resolve([]),
  ]);

  const limitByPlan = new Map(planLimits.map((item) => [item.plano, item]));
  const reportCountByCompany = new Map(reportCounts.map((item) => [item.empresa_id, item._count._all]));
  const usersByCompany = new Map<number, typeof users>();

  for (const user of users) {
    const current = usersByCompany.get(user.empresa_id) ?? [];
    current.push(user);
    usersByCompany.set(user.empresa_id, current);
  }

  let items: AdminClientListItem[] = companies.map((company) => {
    const companyUsers = usersByCompany.get(company.id) ?? [];
    const admins = companyUsers.filter((user) => user.nivel_acesso === ACCESS_LEVELS.clientAdmin);
    const inspectors = companyUsers.filter((user) => user.nivel_acesso === ACCESS_LEVELS.inspector);
    const reviewers = companyUsers.filter((user) => user.nivel_acesso === ACCESS_LEVELS.reviewer);
    const managedUsers = companyUsers.filter((user) =>
      [ACCESS_LEVELS.clientAdmin, ACCESS_LEVELS.inspector, ACCESS_LEVELS.reviewer].includes(user.nivel_acesso as 1 | 50 | 80),
    );
    const latestActivity = getLatestActivity(
      companyUsers.flatMap((user) => [
        user.ultimo_login,
        ...user.sessoes_ativas.map((session) => session.ultima_atividade_em),
      ]),
    );
    const totalSessions = companyUsers.reduce((sum, user) => sum + user.sessoes_ativas.length, 0);
    const plan = limitByPlan.get(company.plano_ativo);
    const usagePercent = calculateUsagePercentage(company.mensagens_processadas, plan?.laudos_mes ?? null);
    const status = getStatusFromCompany({
      blocked: company.status_bloqueio,
      admins: admins.map((admin) => ({ senhaTemporariaAtiva: admin.senha_temporaria_ativa })),
    });
    const health = getHealthFromCompany({
      status: status.value,
      adminsTotal: admins.length,
      inspetoresTotal: inspectors.length,
      revisoresTotal: reviewers.length,
      ultimoAcesso: latestActivity,
      usoPercentual: usagePercent,
    });

    return {
      id: company.id,
      nomeFantasia: company.nome_fantasia,
      cnpj: company.cnpj,
      planoAtivo: company.plano_ativo,
      cidadeEstado: company.cidade_estado,
      criadoEm: company.criado_em,
      totalUsuarios: managedUsers.length,
      adminsTotal: admins.length,
      inspetoresTotal: inspectors.length,
      revisoresTotal: reviewers.length,
      sessoesAtivasTotal: totalSessions,
      usoAtual: company.mensagens_processadas,
      limiteLaudos: plan?.laudos_mes ?? null,
      usoPercentual: usagePercent,
      usoLabel: buildUsageLabel(company.mensagens_processadas, plan?.laudos_mes ?? null),
      ultimoAcessoEm: latestActivity,
      ultimoAcessoLabel: formatDateTime(latestActivity),
      totalLaudos: reportCountByCompany.get(company.id) ?? 0,
      statusValue: status.value,
      statusLabel: status.label,
      statusTone: status.tone,
      saudeValue: health.value,
      saudeLabel: health.label,
      saudeTone: health.tone,
      saudeRazao: health.reason,
      motivoBloqueio: company.motivo_bloqueio,
    };
  });

  if (filters.codigo && filters.codigo.length > 9) {
    items = items.filter((item) => normalizeDigits(item.cnpj).includes(filters.codigo));
  }

  if (filters.status) {
    items = items.filter((item) => item.statusValue === filters.status);
  }

  if (filters.saude) {
    items = items.filter((item) => item.saudeValue === filters.saude);
  }

  if (filters.atividade) {
    items = items.filter((item) => matchesActivity(item.ultimoAcessoEm, filters.atividade));
  }

  const totals = {
    clientesTotal: items.length,
    ativos: items.filter((item) => item.statusValue === "ativo").length,
    bloqueados: items.filter((item) => item.statusValue === "bloqueado").length,
    pendentes: items.filter((item) => item.statusValue === "pendente").length,
    alerta: items.filter((item) => item.saudeValue !== "ok" && item.statusValue !== "bloqueado").length,
    semAtividade: items.filter((item) => matchesActivity(item.ultimoAcessoEm, "sem_atividade")).length,
  };

  const healthPriority = {
    critico: 0,
    alerta: 1,
    ok: 2,
  } as const;

  items.sort((left, right) => {
    let comparison = 0;

    if (filters.ordenar === "criacao") {
      comparison = left.criadoEm.getTime() - right.criadoEm.getTime();
    } else if (filters.ordenar === "ultimo_acesso") {
      comparison = (left.ultimoAcessoEm?.getTime() ?? 0) - (right.ultimoAcessoEm?.getTime() ?? 0);
    } else if (filters.ordenar === "plano") {
      comparison =
        (PLAN_PRIORITY[left.planoAtivo as keyof typeof PLAN_PRIORITY] ?? 99) -
        (PLAN_PRIORITY[right.planoAtivo as keyof typeof PLAN_PRIORITY] ?? 99);
    } else if (filters.ordenar === "saude") {
      comparison =
        (healthPriority[left.saudeValue] ?? 99) -
        (healthPriority[right.saudeValue] ?? 99);
    } else {
      comparison = left.nomeFantasia.localeCompare(right.nomeFantasia, "pt-BR");
    }

    if (comparison === 0) {
      comparison = left.nomeFantasia.localeCompare(right.nomeFantasia, "pt-BR");
    }

    return filters.direcao === "desc" ? comparison * -1 : comparison;
  });

  const totalPages = Math.max(1, Math.ceil(items.length / filters.porPagina));
  const currentPage = Math.min(filters.pagina, totalPages);
  const startIndex = (currentPage - 1) * filters.porPagina;
  const pagedItems = items.slice(startIndex, startIndex + filters.porPagina);
  const pages = [];

  for (let page = Math.max(1, currentPage - 2); page <= Math.min(totalPages, currentPage + 2); page += 1) {
    pages.push(page);
  }

  return {
    items: pagedItems,
    totals,
    pagination: {
      page: currentPage,
      pageSize: filters.porPagina,
      totalItems: items.length,
      totalPages,
      hasPrev: currentPage > 1,
      hasNext: currentPage < totalPages,
      pages,
    },
    filters: {
      ...filters,
      pagina: currentPage,
    },
  };
}

export async function getAdminClientDetail(companyId: number): Promise<AdminClientDetailData | null> {
  if (!Number.isInteger(companyId) || companyId <= 0) {
    return null;
  }

  const company = await prisma.empresas.findUnique({
    where: {
      id: companyId,
    },
    select: {
      id: true,
      nome_fantasia: true,
      cnpj: true,
      plano_ativo: true,
      cidade_estado: true,
      segmento: true,
      nome_responsavel: true,
      observacoes: true,
      criado_em: true,
      custo_gerado_reais: true,
      mensagens_processadas: true,
      status_bloqueio: true,
      motivo_bloqueio: true,
      admin_cliente_policy_json: true,
    },
  });

  if (!company) {
    return null;
  }

  const [planLimits, users, reportAggregate, recentReports, recentAudit, templatesCount, activeReleases, activeSignatories, catalogPortfolio] =
    await Promise.all([
      prisma.limites_plano.findUnique({
        where: {
          plano: company.plano_ativo,
        },
      }),
      prisma.usuarios.findMany({
        where: {
          empresa_id: companyId,
        },
        orderBy: [{ nivel_acesso: "desc" }, { nome_completo: "asc" }],
        select: {
          id: true,
          nome_completo: true,
          email: true,
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
              portal: true,
              ultima_atividade_em: true,
              expira_em: true,
            },
          },
        },
      }),
      prisma.laudos.aggregate({
        where: {
          empresa_id: companyId,
        },
        _count: {
          id: true,
        },
        _sum: {
          custo_api_reais: true,
        },
      }),
      prisma.laudos.findMany({
        where: {
          empresa_id: companyId,
        },
        orderBy: {
          criado_em: "desc",
        },
        take: 8,
        select: {
          id: true,
          setor_industrial: true,
          tipo_template: true,
          status_revisao: true,
          status_conformidade: true,
          entry_mode_effective: true,
          criado_em: true,
        },
      }),
      prisma.auditoria_empresas.findMany({
        where: {
          empresa_id: companyId,
        },
        orderBy: {
          criado_em: "desc",
        },
        take: 10,
        select: {
          id: true,
          portal: true,
          acao: true,
          resumo: true,
          criado_em: true,
          ator_usuario_id: true,
          alvo_usuario_id: true,
        },
      }),
      prisma.templates_laudo.count({
        where: {
          empresa_id: companyId,
        },
      }),
      prisma.tenant_family_releases.count({
        where: {
          tenant_id: companyId,
          release_status: "active",
        },
      }),
      prisma.signatarios_governados_laudo.count({
        where: {
          tenant_id: companyId,
          ativo: true,
        },
      }),
      getAdminTenantCatalogSnapshot(companyId),
    ]);

  const serializedUsers = users.map(serializeUser);
  const admins = serializedUsers.filter((user) => user.nivelAcesso === ACCESS_LEVELS.clientAdmin);
  const operationalUsers = serializedUsers.filter((user) =>
    [ACCESS_LEVELS.inspector, ACCESS_LEVELS.reviewer].includes(user.nivelAcesso as 1 | 50),
  );
  const inspectorsTotal = serializedUsers.filter((user) => user.nivelAcesso === ACCESS_LEVELS.inspector).length;
  const reviewersTotal = serializedUsers.filter((user) => user.nivelAcesso === ACCESS_LEVELS.reviewer).length;
  const latestActivity = getLatestActivity(serializedUsers.map((user) => user.ultimoAcessoEm));
  const usagePercent = calculateUsagePercentage(company.mensagens_processadas, planLimits?.laudos_mes ?? null);
  const status = getStatusFromCompany({
    blocked: company.status_bloqueio,
    admins: admins.map((admin) => ({ senhaTemporariaAtiva: admin.senhaTemporariaAtiva })),
  });
  const health = getHealthFromCompany({
    status: status.value,
    adminsTotal: admins.length,
    inspetoresTotal: inspectorsTotal,
    revisoresTotal: reviewersTotal,
    ultimoAcesso: latestActivity,
    usoPercentual: usagePercent,
  });

  const sessions: AdminClientSessionSummary[] = users.flatMap((user) =>
    user.sessoes_ativas.map((session) => ({
      token: session.token,
      usuarioId: user.id,
      usuarioNome: user.nome_completo,
      usuarioEmail: user.email,
      roleLabel: roleLabel(user.nivel_acesso),
      portal: session.portal,
      ultimaAtividadeEm: session.ultima_atividade_em,
      ultimaAtividadeLabel: formatDateTime(session.ultima_atividade_em),
      expiraEm: session.expira_em,
      expiraEmLabel: formatDateTime(session.expira_em, "Sem expiração"),
    })),
  );

  const firstAdmin = admins[0] ?? null;

  return {
    company: {
      id: company.id,
      nomeFantasia: company.nome_fantasia,
      cnpj: company.cnpj,
      planoAtivo: company.plano_ativo,
      cidadeEstado: company.cidade_estado,
      segmento: company.segmento,
      nomeResponsavel: company.nome_responsavel,
      observacoes: company.observacoes,
      criadoEm: company.criado_em,
      custoGeradoReais: toNumber(company.custo_gerado_reais),
      mensagensProcessadas: company.mensagens_processadas,
      statusBloqueio: company.status_bloqueio,
      motivoBloqueio: company.motivo_bloqueio,
      adminPolicyJson: company.admin_cliente_policy_json,
    },
    status: {
      value: status.value,
      label: status.label,
      tone: status.tone,
      blockedReason: company.motivo_bloqueio,
    },
    health: {
      value: health.value,
      label: health.label,
      tone: health.tone,
      reason: health.reason,
    },
    firstAccess: {
      hasAdmin: Boolean(firstAdmin),
      statusLabel: firstAdmin
        ? firstAdmin.senhaTemporariaAtiva
          ? "Primeiro acesso pendente"
          : "Acesso inicial concluido"
        : "Primeiro acesso ainda nao preparado",
      adminName: firstAdmin?.nomeCompleto ?? "Responsavel da empresa",
      adminEmail: firstAdmin?.email ?? "",
      loginPrefillUrl: firstAdmin?.email
        ? `/cliente/login?email=${encodeURIComponent(firstAdmin.email)}&primeiro_acesso=1`
        : "/cliente/login",
      requiresPasswordReset: Boolean(firstAdmin?.senhaTemporariaAtiva),
    },
    limits: {
      laudosMes: planLimits?.laudos_mes ?? null,
      usuariosMax: planLimits?.usuarios_max ?? null,
      uploadDoc: planLimits?.upload_doc ?? false,
      deepResearch: planLimits?.deep_research ?? false,
      integracoesMax: planLimits?.integracoes_max ?? null,
      retencaoDias: planLimits?.retencao_dias ?? null,
    },
    summary: {
      totalUsuarios: serializedUsers.length,
      adminsTotal: admins.length,
      inspetoresTotal: inspectorsTotal,
      revisoresTotal: reviewersTotal,
      sessoesAtivasTotal: sessions.length,
      usuariosComSessaoAtiva: new Set(sessions.map((session) => session.usuarioId)).size,
      usuariosBloqueados: serializedUsers.filter((user) => !user.ativo || user.statusBloqueio).length,
      trocaSenhaPendente: serializedUsers.filter((user) => user.senhaTemporariaAtiva).length,
      totalLaudos: reportAggregate._count.id,
      templates: templatesCount,
      activeReleases: activeReleases,
      activeSignatories: activeSignatories,
      totalAuditEvents: recentAudit.length,
      usoAtual: company.mensagens_processadas,
      usoPercentual: usagePercent,
      usoLabel: buildUsageLabel(company.mensagens_processadas, planLimits?.laudos_mes ?? null),
      custoTotal: toNumber(reportAggregate._sum.custo_api_reais),
      ultimoAcessoEm: latestActivity,
      ultimoAcessoLabel: formatDateTime(latestActivity),
    },
    catalogPortfolio,
    admins,
    operationalUsers,
    sessions: sessions.sort((left, right) => (right.ultimaAtividadeEm?.getTime() ?? 0) - (left.ultimaAtividadeEm?.getTime() ?? 0)),
    recentReports: recentReports.map((report) => ({
      id: report.id,
      setor: report.setor_industrial,
      template: report.tipo_template,
      revisao: report.status_revisao,
      conformidade: report.status_conformidade,
      entryMode: report.entry_mode_effective,
      criadoEm: report.criado_em,
    })),
    recentAudit: recentAudit.map((audit) => ({
      id: audit.id,
      portal: audit.portal,
      acao: audit.acao,
      resumo: audit.resumo,
      criadoEm: audit.criado_em,
      atorUsuarioId: audit.ator_usuario_id,
      alvoUsuarioId: audit.alvo_usuario_id,
    })),
  };
}
