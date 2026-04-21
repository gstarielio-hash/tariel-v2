const SOCKET_HOST = "/var/run/postgresql";

function withPostgresqlProtocol(value: string) {
  return value.startsWith("postgres://") ? `postgresql://${value.slice("postgres://".length)}` : value;
}

export function normalizeDatabaseUrl(rawValue: string | undefined) {
  const value = (rawValue ?? "").trim();
  if (!value) {
    throw new Error("DATABASE_URL is required for the Astro + Prisma migration workspace.");
  }

  const normalized = withPostgresqlProtocol(value);

  if (!/^postgresql:\/\/\/[^/?#]+/.test(normalized)) {
    return normalized;
  }

  const databaseName = normalized.slice("postgresql:///".length).split(/[?#]/, 1)[0];
  const currentUser = process.env["USER"] ?? process.env["LOGNAME"];

  if (!currentUser) {
    throw new Error("DATABASE_URL uses local socket shorthand, but USER/LOGNAME is not available to derive the PostgreSQL role.");
  }

  return `postgresql://${encodeURIComponent(currentUser)}@localhost:5432/${databaseName}?host=${encodeURIComponent(SOCKET_HOST)}`;
}
