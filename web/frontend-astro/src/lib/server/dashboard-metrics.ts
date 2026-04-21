import { prisma } from "@/lib/server/prisma";

export interface MigrationMetrics {
  connected: boolean;
  source: string;
  companies: number | null;
  users: number | null;
  reports: number | null;
  templates: number | null;
  error: string | null;
}

export async function getMigrationMetrics(): Promise<MigrationMetrics> {
  try {
    const [companies, users, reports, templates] = await Promise.all([
      prisma.empresas.count(),
      prisma.usuarios.count(),
      prisma.laudos.count(),
      prisma.templates_laudo.count(),
    ]);

    return {
      connected: true,
      source: "PostgreSQL atual via Prisma 7",
      companies,
      users,
      reports,
      templates,
      error: null,
    };
  } catch (error) {
    return {
      connected: false,
      source: "PostgreSQL atual via Prisma 7",
      companies: null,
      users: null,
      reports: null,
      templates: null,
      error: error instanceof Error ? error.message : "Unexpected Prisma error",
    };
  }
}
