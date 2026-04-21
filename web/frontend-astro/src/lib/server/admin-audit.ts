import { prisma } from "@/lib/server/prisma";

type AuditCategory = "access" | "commercial" | "team" | "support" | "chat" | "mesa" | "general";
type AuditScope = "admin" | "chat" | "mesa";

export interface AdminAuditQuery {
  empresaId?: string | number | null;
  limite?: string | number | null;
}

export interface AdminAuditFilters {
  empresaId: number | null;
  limite: number;
}

export interface AdminAuditItem {
  id: number;
  companyId: number;
  companyName: string;
  portal: string;
  action: string;
  summary: string;
  detail: string | null;
  category: AuditCategory;
  categoryLabel: string;
  scope: AuditScope;
  scopeLabel: string;
  createdAt: Date;
  createdLabel: string;
  actorUserId: number | null;
  actorName: string;
  targetUserId: number | null;
  targetName: string | null;
  payload: unknown;
  payloadPreview: string | null;
}

export interface AdminAuditData {
  items: AdminAuditItem[];
  filters: AdminAuditFilters;
  summary: {
    total: number;
    categories: Record<AuditCategory, number>;
    scopes: Record<AuditScope, number>;
  };
}

const dateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

const CATEGORY_LABELS: Record<AuditCategory, string> = {
  access: "Acesso",
  commercial: "Comercial",
  team: "Equipe",
  support: "Suporte",
  chat: "Chat",
  mesa: "Mesa",
  general: "Geral",
};

const SCOPE_LABELS: Record<AuditScope, string> = {
  admin: "Painel",
  chat: "Chat",
  mesa: "Mesa",
};

function normalizePositiveInteger(value: string | number | null | undefined) {
  const parsed = Number(value);

  if (!Number.isInteger(parsed) || parsed <= 0) {
    return null;
  }

  return parsed;
}

function normalizeLimit(value: string | number | null | undefined) {
  const parsed = Number(value);

  if (!Number.isFinite(parsed)) {
    return 30;
  }

  return Math.max(1, Math.min(100, Math.trunc(parsed)));
}

function classifyAuditAction(action: string): {
  category: AuditCategory;
  scope: AuditScope;
} {
  const normalized = String(action ?? "").trim().toLowerCase();

  if (normalized.startsWith("chat_")) {
    return { category: "chat", scope: "chat" };
  }

  if (normalized.startsWith("mesa_")) {
    return { category: "mesa", scope: "mesa" };
  }

  if (normalized.startsWith("plano_") || normalized.includes("_plano_") || normalized.includes("catalog")) {
    return { category: "commercial", scope: "admin" };
  }

  if (normalized.startsWith("usuario_") || normalized.startsWith("admin_cliente_")) {
    return { category: "team", scope: "admin" };
  }

  if (normalized.startsWith("senha_") || normalized.includes("login") || normalized.includes("mfa")) {
    return { category: "access", scope: "admin" };
  }

  if (normalized.startsWith("suporte_")) {
    return { category: "support", scope: "admin" };
  }

  return { category: "general", scope: "admin" };
}

function actorName(user: { nome_completo?: string | null; email?: string | null } | null | undefined, fallback = "Sistema") {
  const name = String(user?.nome_completo ?? "").trim();

  if (name) {
    return name;
  }

  const email = String(user?.email ?? "").trim();
  return email || fallback;
}

function targetName(user: { nome_completo?: string | null; email?: string | null } | null | undefined) {
  const name = String(user?.nome_completo ?? "").trim();

  if (name) {
    return name;
  }

  const email = String(user?.email ?? "").trim();
  return email || null;
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

export async function getAdminAuditData(query: AdminAuditQuery = {}): Promise<AdminAuditData> {
  const filters: AdminAuditFilters = {
    empresaId: normalizePositiveInteger(query.empresaId),
    limite: normalizeLimit(query.limite),
  };

  const items = await prisma.auditoria_empresas.findMany({
    where: {
      portal: "admin",
      ...(filters.empresaId ? { empresa_id: filters.empresaId } : {}),
    },
    orderBy: [{ criado_em: "desc" }, { id: "desc" }],
    take: filters.limite,
    select: {
      id: true,
      empresa_id: true,
      portal: true,
      acao: true,
      resumo: true,
      detalhe: true,
      payload_json: true,
      criado_em: true,
      ator_usuario_id: true,
      alvo_usuario_id: true,
      empresas: {
        select: {
          nome_fantasia: true,
        },
      },
      usuarios_auditoria_empresas_ator_usuario_idTousuarios: {
        select: {
          nome_completo: true,
          email: true,
        },
      },
      usuarios_auditoria_empresas_alvo_usuario_idTousuarios: {
        select: {
          nome_completo: true,
          email: true,
        },
      },
    },
  });

  const summary = {
    total: items.length,
    categories: {
      access: 0,
      commercial: 0,
      team: 0,
      support: 0,
      chat: 0,
      mesa: 0,
      general: 0,
    } satisfies Record<AuditCategory, number>,
    scopes: {
      admin: 0,
      chat: 0,
      mesa: 0,
    } satisfies Record<AuditScope, number>,
  };

  const serializedItems = items.map((item) => {
    const classification = classifyAuditAction(item.acao);
    summary.categories[classification.category] += 1;
    summary.scopes[classification.scope] += 1;

    return {
      id: item.id,
      companyId: item.empresa_id,
      companyName: item.empresas.nome_fantasia || `Empresa #${item.empresa_id}`,
      portal: item.portal,
      action: item.acao,
      summary: item.resumo,
      detail: String(item.detalhe ?? "").trim() || null,
      category: classification.category,
      categoryLabel: CATEGORY_LABELS[classification.category],
      scope: classification.scope,
      scopeLabel: SCOPE_LABELS[classification.scope],
      createdAt: item.criado_em,
      createdLabel: dateTimeFormatter.format(item.criado_em),
      actorUserId: item.ator_usuario_id ?? null,
      actorName: actorName(item.usuarios_auditoria_empresas_ator_usuario_idTousuarios),
      targetUserId: item.alvo_usuario_id ?? null,
      targetName: targetName(item.usuarios_auditoria_empresas_alvo_usuario_idTousuarios),
      payload: item.payload_json,
      payloadPreview: jsonPreview(item.payload_json),
    } satisfies AdminAuditItem;
  });

  return {
    items: serializedItems,
    filters,
    summary,
  };
}
