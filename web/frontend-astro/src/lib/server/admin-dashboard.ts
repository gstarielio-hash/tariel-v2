import { prisma } from "@/lib/server/prisma";

export interface AdminWeeklyPoint {
  label: string;
  value: number;
  dateKey: string;
}

export interface AdminRecentCompany {
  id: number;
  name: string;
  plan: string;
  blocked: boolean;
  city: string | null;
  createdAt: Date;
  processedMessages: number;
  generatedCost: number;
}

export interface AdminRecentReport {
  id: number;
  companyName: string;
  sector: string;
  reviewStatus: string;
  complianceStatus: string;
  entryMode: string;
  createdAt: Date;
}

export interface AdminDashboardData {
  connected: boolean;
  generatedAt: Date;
  error: string | null;
  kpis: {
    totalCompanies: number | null;
    activeCompanies: number | null;
    blockedCompanies: number | null;
    activeUsers: number | null;
    adminUsers: number | null;
    totalReports: number | null;
    reportsLast7Days: number | null;
    deepResearchReports: number | null;
    templates: number | null;
    totalRevenue: number | null;
  };
  weeklyReports: AdminWeeklyPoint[];
  recentCompanies: AdminRecentCompany[];
  recentReports: AdminRecentReport[];
}

const weekdayFormatter = new Intl.DateTimeFormat("pt-BR", { weekday: "short" });

function startOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function addDays(date: Date, amount: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + amount);
  return next;
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

function buildWeeklySeries(reportDates: Date[], now = new Date()) {
  const base = startOfDay(now);
  const counts = new Map<string, number>();

  for (const reportDate of reportDates) {
    const dateKey = startOfDay(reportDate).toISOString().slice(0, 10);
    counts.set(dateKey, (counts.get(dateKey) ?? 0) + 1);
  }

  const series: AdminWeeklyPoint[] = [];

  for (let offset = 6; offset >= 0; offset -= 1) {
    const day = addDays(base, -offset);
    const dateKey = day.toISOString().slice(0, 10);
    const weekday = weekdayFormatter.format(day).replace(".", "");
    const label = weekday.slice(0, 1).toUpperCase() + weekday.slice(1);

    series.push({
      label,
      dateKey,
      value: counts.get(dateKey) ?? 0,
    });
  }

  return series;
}

export async function getAdminDashboardData(): Promise<AdminDashboardData> {
  const generatedAt = new Date();
  const windowStart = addDays(startOfDay(generatedAt), -6);

  try {
    const [
      totalCompanies,
      activeCompanies,
      blockedCompanies,
      activeUsers,
      adminUsers,
      totalReports,
      deepResearchReports,
      templates,
      revenueAggregate,
      reportsWindow,
      recentCompanies,
      recentReports,
    ] = await Promise.all([
      prisma.empresas.count(),
      prisma.empresas.count({ where: { status_bloqueio: false } }),
      prisma.empresas.count({ where: { status_bloqueio: true } }),
      prisma.usuarios.count({ where: { ativo: true } }),
      prisma.usuarios.count({ where: { portal_admin_autorizado: true } }),
      prisma.laudos.count(),
      prisma.laudos.count({ where: { is_deep_research: true } }),
      prisma.templates_laudo.count(),
      prisma.empresas.aggregate({
        _sum: {
          custo_gerado_reais: true,
        },
      }),
      prisma.laudos.findMany({
        where: {
          criado_em: {
            gte: windowStart,
          },
        },
        select: {
          criado_em: true,
        },
      }),
      prisma.empresas.findMany({
        orderBy: {
          criado_em: "desc",
        },
        take: 6,
        select: {
          id: true,
          nome_fantasia: true,
          plano_ativo: true,
          status_bloqueio: true,
          cidade_estado: true,
          criado_em: true,
          mensagens_processadas: true,
          custo_gerado_reais: true,
        },
      }),
      prisma.laudos.findMany({
        orderBy: {
          criado_em: "desc",
        },
        take: 7,
        select: {
          id: true,
          setor_industrial: true,
          status_revisao: true,
          status_conformidade: true,
          entry_mode_effective: true,
          criado_em: true,
          empresas: {
            select: {
              nome_fantasia: true,
            },
          },
        },
      }),
    ]);

    return {
      connected: true,
      generatedAt,
      error: null,
      kpis: {
        totalCompanies,
        activeCompanies,
        blockedCompanies,
        activeUsers,
        adminUsers,
        totalReports,
        reportsLast7Days: reportsWindow.length,
        deepResearchReports,
        templates,
        totalRevenue: toNumber(revenueAggregate._sum.custo_gerado_reais),
      },
      weeklyReports: buildWeeklySeries(reportsWindow.map((item) => item.criado_em), generatedAt),
      recentCompanies: recentCompanies.map((company) => ({
        id: company.id,
        name: company.nome_fantasia,
        plan: company.plano_ativo,
        blocked: company.status_bloqueio,
        city: company.cidade_estado,
        createdAt: company.criado_em,
        processedMessages: company.mensagens_processadas,
        generatedCost: toNumber(company.custo_gerado_reais),
      })),
      recentReports: recentReports.map((report) => ({
        id: report.id,
        companyName: report.empresas.nome_fantasia,
        sector: report.setor_industrial,
        reviewStatus: report.status_revisao,
        complianceStatus: report.status_conformidade,
        entryMode: report.entry_mode_effective,
        createdAt: report.criado_em,
      })),
    };
  } catch (error) {
    return {
      connected: false,
      generatedAt,
      error: error instanceof Error ? error.message : "Unexpected Prisma error",
      kpis: {
        totalCompanies: null,
        activeCompanies: null,
        blockedCompanies: null,
        activeUsers: null,
        adminUsers: null,
        totalReports: null,
        reportsLast7Days: null,
        deepResearchReports: null,
        templates: null,
        totalRevenue: null,
      },
      weeklyReports: buildWeeklySeries([], generatedAt),
      recentCompanies: [],
      recentReports: [],
    };
  }
}
