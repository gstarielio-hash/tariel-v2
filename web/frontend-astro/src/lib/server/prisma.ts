import "dotenv/config";

import { PrismaPg } from "@prisma/adapter-pg";

import { PrismaClient } from "@/generated/prisma/client";
import { normalizeDatabaseUrl } from "@/lib/server/database-url";

declare global {
  // eslint-disable-next-line no-var
  var __tarielPrisma: PrismaClient | undefined;
}

function createPrismaClient() {
  const connectionString = normalizeDatabaseUrl(process.env["DATABASE_URL"]);
  const adapter = new PrismaPg({ connectionString });

  return new PrismaClient({ adapter });
}

export const prisma = globalThis.__tarielPrisma ?? createPrismaClient();

if (import.meta.env?.DEV) {
  globalThis.__tarielPrisma = prisma;
}
