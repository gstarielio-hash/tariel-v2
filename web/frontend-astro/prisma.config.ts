import "dotenv/config";
import { defineConfig } from "prisma/config";

import { normalizeDatabaseUrl } from "./src/lib/server/database-url";

const fallbackDatabaseUrl = "postgresql://placeholder:placeholder@localhost:5432/placeholder?schema=public";

export default defineConfig({
  schema: "prisma/schema.prisma",
  migrations: {
    path: "prisma/migrations",
  },
  datasource: {
    url: process.env["DATABASE_URL"] ? normalizeDatabaseUrl(process.env["DATABASE_URL"]) : fallbackDatabaseUrl,
  },
});
