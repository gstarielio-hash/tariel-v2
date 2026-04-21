import { prisma } from "@/lib/server/prisma";

export interface AppPortalReportSummary {
  id: number;
  sector: string;
  template: string;
  reviewStatus: string;
  complianceStatus: string;
  pinned: boolean;
  createdAt: Date;
  updatedAt: Date | null;
  updatedAtLabel: string;
}

export interface AppPortalAuditSummary {
  id: number;
  portal: string;
  action: string;
  summary: string;
  detail: string | null;
  createdAt: Date;
  createdAtLabel: string;
}

export interface AppPortalOverview {
  company: {
    id: number;
    name: string;
    blocked: boolean;
    blockedReason: string | null;
    activePlan: string;
  };
  profile: {
    userId: number;
    name: string;
    email: string;
    phone: string | null;
    accessLevel: number;
    temporaryPasswordActive: boolean;
    lastLoginAt: Date | null;
    lastLoginLabel: string;
  };
  summary: {
    totalReports: number;
    pinnedReports: number;
    reportsLast30Days: number;
    activeSessions: number;
    auditEvents: number;
    latestActivityAt: Date | null;
    latestActivityLabel: string;
  };
  recentReports: AppPortalReportSummary[];
  recentAudit: AppPortalAuditSummary[];
}

export async function getAppPortalOverview(input: {
  userId: number;
  companyId: number;
}): Promise<AppPortalOverview | null> {
  const [user, reportCounts, sessions, recentReports, recentAudit, reportsLast30Days] = await Promise.all([
    prisma.usuarios.findFirst({
      where: {
        id: input.userId,
        empresa_id: input.companyId,
      },
      select: {
        id: true,
        nome_completo: true,
        email: true,
        telefone: true,
        nivel_acesso: true,
        senha_temporaria_ativa: true,
        ultimo_login: true,
        empresas: {
          select: {
            id: true,
            nome_fantasia: true,
            status_bloqueio: true,
            motivo_bloqueio: true,
            plano_ativo: true,
          },
        },
      },
    }),
    prisma.laudos.aggregate({
      where: {
        empresa_id: input.companyId,
        usuario_id: input.userId,
      },
      _count: {
        id: true,
      },
    }),
    prisma.sessoes_ativas.findMany({
      where: {
        usuario_id: input.userId,
        portal: "inspetor",
      },
      orderBy: {
        ultima_atividade_em: "desc",
      },
      select: {
        token: true,
        ultima_atividade_em: true,
      },
    }),
    prisma.laudos.findMany({
      where: {
        empresa_id: input.companyId,
        usuario_id: input.userId,
      },
      orderBy: [
        { pinado: "desc" },
        { atualizado_em: "desc" },
        { criado_em: "desc" },
      ],
      take: 8,
      select: {
        id: true,
        setor_industrial: true,
        tipo_template: true,
        status_revisao: true,
        status_conformidade: true,
        pinado: true,
        criado_em: true,
        atualizado_em: true,
      },
    }),
    prisma.auditoria_empresas.findMany({
      where: {
        empresa_id: input.companyId,
        portal: "inspetor",
        OR: [
          { ator_usuario_id: input.userId },
          { alvo_usuario_id: input.userId },
        ],
      },
      orderBy: {
        criado_em: "desc",
      },
      take: 8,
      select: {
        id: true,
        portal: true,
        acao: true,
        resumo: true,
        detalhe: true,
        criado_em: true,
      },
    }),
    prisma.laudos.count({
      where: {
        empresa_id: input.companyId,
        usuario_id: input.userId,
        criado_em: {
          gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
        },
      },
    }),
  ]);

  if (!user) {
    return null;
  }

  const latestActivityAt = sessions[0]?.ultima_atividade_em ?? user.ultimo_login ?? recentReports[0]?.atualizado_em ?? null;

  return {
    company: {
      id: user.empresas.id,
      name: user.empresas.nome_fantasia,
      blocked: user.empresas.status_bloqueio,
      blockedReason: user.empresas.motivo_bloqueio,
      activePlan: user.empresas.plano_ativo,
    },
    profile: {
      userId: user.id,
      name: user.nome_completo,
      email: user.email,
      phone: user.telefone,
      accessLevel: user.nivel_acesso,
      temporaryPasswordActive: user.senha_temporaria_ativa,
      lastLoginAt: user.ultimo_login,
      lastLoginLabel: formatDateTime(user.ultimo_login, "Sem login registrado"),
    },
    summary: {
      totalReports: reportCounts._count.id,
      pinnedReports: recentReports.filter((report) => report.pinado).length,
      reportsLast30Days,
      activeSessions: sessions.length,
      auditEvents: recentAudit.length,
      latestActivityAt,
      latestActivityLabel: formatRelativeTime(latestActivityAt),
    },
    recentReports: recentReports.map((report) => ({
      id: report.id,
      sector: report.setor_industrial || `Laudo ${report.id}`,
      template: humanizeTemplateName(report.tipo_template),
      reviewStatus: report.status_revisao,
      complianceStatus: report.status_conformidade,
      pinned: report.pinado,
      createdAt: report.criado_em,
      updatedAt: report.atualizado_em,
      updatedAtLabel: formatRelativeTime(report.atualizado_em ?? report.criado_em),
    })),
    recentAudit: recentAudit.map((entry) => ({
      id: entry.id,
      portal: entry.portal || "inspetor",
      action: entry.acao,
      summary: entry.resumo,
      detail: entry.detalhe,
      createdAt: entry.criado_em,
      createdAtLabel: formatDateTime(entry.criado_em),
    })),
  };
}

function humanizeTemplateName(value: string | null | undefined) {
  const normalized = String(value ?? "").trim();

  if (!normalized) {
    return "Template padrao";
  }

  return normalized
    .split(/[_-]+/g)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDateTime(value: Date | null, fallback = "Agora") {
  if (!value) {
    return fallback;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(value);
}

function formatRelativeTime(value: Date | null) {
  if (!value) {
    return "Agora";
  }

  const diffMs = Date.now() - value.getTime();
  const diffMinutes = Math.max(1, Math.round(diffMs / 60_000));

  if (diffMinutes < 60) {
    return `ha ${diffMinutes} min`;
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return `ha ${diffHours} h`;
  }

  const diffDays = Math.round(diffHours / 24);
  if (diffDays === 1) {
    return "Ontem";
  }

  return `ha ${diffDays} dias`;
}
