import { createHash, randomBytes } from "node:crypto";

import { verify as verifyArgon2 } from "@node-rs/argon2";
import type { APIContext } from "astro";

import { prisma } from "@/lib/server/prisma";

const ADMIN_ACCESS_LEVEL = 99;
const ADMIN_PORTAL = "admin";
const ADMIN_SESSION_COOKIE = "tariel_admin_session";
const ADMIN_SESSION_TTL_HOURS = readPositiveIntEnv("SESSAO_TTL_HORAS", 8);
const ADMIN_SESSION_REMEMBER_DAYS = readPositiveIntEnv("SESSAO_TTL_LEMBRAR_DIAS", 30);
const ADMIN_SESSION_MAX_PER_USER = readPositiveIntEnv("SESSAO_MAX_POR_USUARIO", 5);
const ADMIN_SESSION_RENEWAL_ENABLED = readBooleanEnv("SESSAO_RENOVACAO_ATIVA", true);
const ADMIN_SESSION_RENEWAL_WINDOW_MINUTES = readPositiveIntEnv("SESSAO_JANELA_RENOVACAO_MINUTOS", 30);

export interface AuthenticatedAdminRequest {
  user: {
    id: number;
    companyId: number;
    companyName: string;
    email: string;
    name: string;
    accessLevel: number;
    accountScope: string;
    accountStatus: string;
    adminIdentityStatus: string;
    canPasswordLogin: boolean;
    portalAdminAuthorized: boolean;
    mfaRequired: boolean;
    senhaTemporariaAtiva: boolean;
  };
  session: {
    token: string;
    expiresAt: Date;
    lastActivityAt: Date;
    remember: boolean;
    mfaLevel: string | null;
    reauthAt: Date | null;
  };
}

export interface AdminLoginAttemptInput {
  email: string;
  password: string;
  remember: boolean;
  request: Request;
}

export interface AdminLoginAttemptResult {
  ok: boolean;
  error?: string;
  session?: AuthenticatedAdminRequest;
}

export function isAdminPath(pathname: string) {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

export function isPublicAdminPath(pathname: string) {
  return pathname === "/admin/login" || pathname === "/admin/login/entrar";
}

export function safeAdminNextPath(value: string | null | undefined, fallback = "/admin/painel") {
  const normalized = String(value ?? "").trim();

  if (!normalized.startsWith("/admin")) {
    return fallback;
  }

  if (normalized === "/admin" || normalized.startsWith("/admin/login")) {
    return fallback;
  }

  return normalized;
}

export function buildAdminLoginPath(nextPath: string) {
  const redirectTarget = safeAdminNextPath(nextPath, "/admin/painel");
  const search = new URLSearchParams({ next: redirectTarget });

  return `/admin/login?${search.toString()}`;
}

export function isStateChangingMethod(method: string) {
  return method === "POST" || method === "PUT" || method === "PATCH" || method === "DELETE";
}

export function isSameOriginRequest(request: Request, url: URL) {
  const origin = String(request.headers.get("origin") ?? "").trim();

  if (!origin) {
    return true;
  }

  try {
    return new URL(origin).origin === url.origin;
  } catch {
    return false;
  }
}

export async function loadAdminRequestSession(context: Pick<APIContext, "cookies" | "request">) {
  const token = readAdminSessionToken(context.cookies);

  if (!token) {
    return null;
  }

  const sessionRow = await prisma.sessoes_ativas.findUnique({
    where: {
      token,
    },
    select: {
      token: true,
      expira_em: true,
      ultima_atividade_em: true,
      lembrar: true,
      mfa_level: true,
      reauth_at: true,
      usuarios: {
        select: adminUserSelect,
      },
    },
  });

  if (!sessionRow) {
    clearAdminSessionCookie(context.cookies);
    return null;
  }

  const now = new Date();

  if (sessionRow.expira_em <= now) {
    await invalidateAdminSessionToken(token);
    clearAdminSessionCookie(context.cookies);
    return null;
  }

  const hydrated = toAuthenticatedAdminRequest(sessionRow);

  if (
    !hydrated ||
    !isAdminUserEligible(sessionRow.usuarios) ||
    !isAdminIdentityActive(sessionRow.usuarios) ||
    !sessionRow.usuarios.can_password_login ||
    sessionRow.usuarios.senha_temporaria_ativa ||
    isAdminUserBlocked(sessionRow.usuarios)
  ) {
    await invalidateAdminSessionToken(token);
    clearAdminSessionCookie(context.cookies);
    return null;
  }

  const nextExpiration = resolveSessionExpiration({
    remember: sessionRow.lembrar,
    currentExpiration: sessionRow.expira_em,
    now,
  });

  await prisma.sessoes_ativas.update({
    where: {
      token,
    },
    data: {
      ultima_atividade_em: now,
      expira_em: nextExpiration,
    },
  });

  applyAdminSessionCookie(context.cookies, token, {
    remember: sessionRow.lembrar,
    secure: context.request.url.startsWith("https://"),
  });

  return {
    ...hydrated,
    session: {
      ...hydrated.session,
      expiresAt: nextExpiration,
      lastActivityAt: now,
    },
  } satisfies AuthenticatedAdminRequest;
}

export async function attemptAdminPasswordLogin(
  input: AdminLoginAttemptInput,
): Promise<AdminLoginAttemptResult> {
  const email = normalizeEmail(input.email);
  const password = String(input.password ?? "");

  if (!email || !password) {
    return {
      ok: false,
      error: "Preencha e-mail e senha.",
    };
  }

  const candidate = await prisma.usuarios.findUnique({
    where: {
      email,
    },
    select: adminUserSelect,
  });

  if (!candidate) {
    await createAdminIdentityAudit({
      action: "admin_identity_denied",
      email,
      reason: "invalid_credentials",
      summary: "Login local negado no Admin-CEO",
      detail: "Credenciais invalidas para o acesso administrativo em Astro.",
    });

    return {
      ok: false,
      error: "Credenciais inválidas.",
    };
  }

  const passwordMatches = await verifyPasswordHash(password, candidate.senha_hash);

  if (!passwordMatches) {
    await registerFailedAdminPasswordAttempt(candidate.id);
    await createAdminIdentityAudit({
      action: "admin_identity_denied",
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      reason: "invalid_credentials",
      summary: "Login local negado no Admin-CEO",
      detail: "Credenciais invalidas para o acesso administrativo em Astro.",
    });

    return {
      ok: false,
      error: "Credenciais inválidas.",
    };
  }

  if (!isAdminUserEligible(candidate)) {
    await createAdminIdentityAudit({
      action: "admin_identity_denied",
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      reason: "portal_not_authorized",
      summary: "Login local negado no Admin-CEO",
      detail:
        "Sua identidade foi confirmada, mas este e-mail não está autorizado para o portal Admin-CEO. Area restrita ao Admin-CEO. Para admins-cliente, use /cliente/login.",
    });

    return {
      ok: false,
      error:
        "Sua identidade foi confirmada, mas este e-mail nao esta autorizado para o portal Admin-CEO. Para admins-cliente, use /cliente/login.",
    };
  }

  if (!candidate.can_password_login) {
    await createAdminIdentityAudit({
      action: "admin_identity_denied",
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      reason: "password_login_disabled",
      summary: "Login local negado no Admin-CEO",
      detail: "O metodo senha nao esta liberado para este operador da plataforma no Astro.",
    });

    return {
      ok: false,
      error: "Sua conta esta autorizada, mas o login por senha nao esta habilitado para o Admin-CEO.",
    };
  }

  if (!isAdminIdentityActive(candidate)) {
    await createAdminIdentityAudit({
      action: "admin_identity_denied",
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      reason: candidate.admin_identity_status,
      summary: "Login local negado no Admin-CEO",
      detail: "A identidade administrativa existe, mas esta sem autorizacao ativa para o portal Admin-CEO.",
    });

    return {
      ok: false,
      error: "Sua identidade administrativa existe, mas esta sem autorizacao ativa para o portal Admin-CEO.",
    };
  }

  if (isAdminUserBlocked(candidate)) {
    await createAdminIdentityAudit({
      action: "admin_identity_denied",
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      reason: "account_blocked",
      summary: "Login local negado no Admin-CEO",
      detail: "Conta administrativa bloqueada para o portal Admin-CEO no Astro.",
    });

    return {
      ok: false,
      error: "Conta bloqueada. Contate o suporte.",
    };
  }

  if (candidate.senha_temporaria_ativa) {
    return {
      ok: false,
      error:
        "Sua conta exige troca de senha temporaria. Esse fluxo ainda permanece no legado e sera migrado na proxima fatia.",
    };
  }

  if (candidate.mfa_required) {
    return {
      ok: false,
      error:
        "Sua conta exige MFA TOTP. O challenge ainda esta em migracao para o Astro; use temporariamente o fluxo legado ate a proxima fatia.",
    };
  }

  const now = new Date();
  const sessionToken = randomBytes(48).toString("base64url");
  const sessionExpiration = resolveNewSessionExpiration(input.remember, now);
  const ip = getRequestIp(input.request);
  const userAgent = getRequestUserAgent(input.request);

  await prisma.$transaction(async (tx) => {
    const currentSessions = await tx.sessoes_ativas.findMany({
      where: {
        usuario_id: candidate.id,
      },
      orderBy: {
        criada_em: "asc",
      },
      select: {
        token: true,
      },
    });

    const overflow = Math.max(currentSessions.length - ADMIN_SESSION_MAX_PER_USER + 1, 0);

    if (overflow > 0) {
      await tx.sessoes_ativas.deleteMany({
        where: {
          token: {
            in: currentSessions.slice(0, overflow).map((session) => session.token),
          },
        },
      });
    }

    await tx.usuarios.update({
      where: {
        id: candidate.id,
      },
      data: {
        tentativas_login: 0,
        bloqueado_ate: null,
        status_bloqueio: false,
        ultimo_login: now,
        ultimo_login_ip: ip?.slice(0, 45) ?? null,
        atualizado_em: now,
      },
    });

    await tx.sessoes_ativas.create({
      data: {
        token: sessionToken,
        usuario_id: candidate.id,
        criada_em: now,
        expira_em: sessionExpiration,
        ultima_atividade_em: now,
        lembrar: input.remember,
        portal: ADMIN_PORTAL,
        account_scope: "platform",
        device_id: getRequestDeviceId(input.request, ip, userAgent),
        mfa_level: null,
        reauth_at: null,
        ip_hash: null,
        user_agent_hash: null,
      },
    });

    await tx.auditoria_empresas.create({
      data: {
        empresa_id: candidate.empresa_id,
        ator_usuario_id: candidate.id,
        alvo_usuario_id: candidate.id,
        portal: ADMIN_PORTAL,
        acao: "admin_login_authenticated",
        resumo: "Login password concluido no Admin-CEO",
        detalhe: "Sessao administrativa emitida no Astro SSR com persistencia em sessoes_ativas.",
        payload_json: {
          provider: "password",
          reason: "login_completed",
          source_surface: "frontend_astro",
          next_phase: "admin_mfa_and_reauth",
        },
        criado_em: now,
      },
    });
  });

  const authenticated = toAuthenticatedAdminRequest({
    token: sessionToken,
    expira_em: sessionExpiration,
    ultima_atividade_em: now,
    lembrar: input.remember,
    mfa_level: null,
    reauth_at: null,
    usuarios: candidate,
  });

  if (!authenticated) {
    throw new Error("Falha ao hidratar a sessao administrativa criada no Astro.");
  }

  return {
    ok: true,
    session: authenticated,
  };
}

export function applyAdminSessionCookie(
  cookies: APIContext["cookies"],
  token: string,
  options: {
    remember: boolean;
    secure: boolean;
  },
) {
  const cookieOptions = {
    httpOnly: true,
    path: "/",
    sameSite: "lax" as const,
    secure: options.secure,
  };

  if (options.remember) {
    cookies.set(ADMIN_SESSION_COOKIE, token, {
      ...cookieOptions,
      maxAge: ADMIN_SESSION_REMEMBER_DAYS * 24 * 60 * 60,
    });
    return;
  }

  cookies.set(ADMIN_SESSION_COOKIE, token, cookieOptions);
}

export async function destroyAdminSession(context: Pick<APIContext, "cookies">, token?: string | null) {
  const currentToken = String(token ?? readAdminSessionToken(context.cookies) ?? "").trim();

  if (currentToken) {
    await invalidateAdminSessionToken(currentToken);
  }

  clearAdminSessionCookie(context.cookies);
}

export function readAdminSessionToken(cookies: APIContext["cookies"]) {
  return String(cookies.get(ADMIN_SESSION_COOKIE)?.value ?? "").trim() || null;
}

export function clearAdminSessionCookie(cookies: APIContext["cookies"]) {
  cookies.delete(ADMIN_SESSION_COOKIE, {
    path: "/",
  });
}

const adminUserSelect = {
  id: true,
  empresa_id: true,
  nome_completo: true,
  email: true,
  senha_hash: true,
  nivel_acesso: true,
  ativo: true,
  tentativas_login: true,
  bloqueado_ate: true,
  status_bloqueio: true,
  senha_temporaria_ativa: true,
  account_scope: true,
  account_status: true,
  allowed_portals_json: true,
  mfa_required: true,
  can_password_login: true,
  portal_admin_autorizado: true,
  admin_identity_status: true,
  empresas: {
    select: {
      nome_fantasia: true,
      escopo_plataforma: true,
      status_bloqueio: true,
    },
  },
} as const;

function toAuthenticatedAdminRequest(
  sessionRow:
    | {
        token: string;
        expira_em: Date;
        ultima_atividade_em: Date;
        lembrar: boolean;
        mfa_level: string | null;
        reauth_at: Date | null;
        usuarios: {
          id: number;
          empresa_id: number;
          nome_completo: string;
          email: string;
          senha_hash: string;
          nivel_acesso: number;
          ativo: boolean;
          tentativas_login: number;
          bloqueado_ate: Date | null;
          status_bloqueio: boolean;
          senha_temporaria_ativa: boolean;
          account_scope: string;
          account_status: string;
          allowed_portals_json: unknown;
          mfa_required: boolean;
          can_password_login: boolean;
          portal_admin_autorizado: boolean;
          admin_identity_status: string;
          empresas: {
            nome_fantasia: string;
            escopo_plataforma: boolean;
            status_bloqueio: boolean;
          };
        };
      }
    | null,
) {
  if (!sessionRow) {
    return null;
  }

  const user = sessionRow.usuarios;

  return {
    user: {
      id: user.id,
      companyId: user.empresa_id,
      companyName: user.empresas.nome_fantasia,
      email: user.email,
      name: user.nome_completo,
      accessLevel: user.nivel_acesso,
      accountScope: normalizeFlag(user.account_scope, "tenant"),
      accountStatus: normalizeFlag(user.account_status, "active"),
      adminIdentityStatus: normalizeFlag(user.admin_identity_status, "active"),
      canPasswordLogin: Boolean(user.can_password_login),
      portalAdminAuthorized: portalAdminAuthorized(user.portal_admin_autorizado, user.allowed_portals_json),
      mfaRequired: Boolean(user.mfa_required),
      senhaTemporariaAtiva: Boolean(user.senha_temporaria_ativa),
    },
    session: {
      token: sessionRow.token,
      expiresAt: sessionRow.expira_em,
      lastActivityAt: sessionRow.ultima_atividade_em,
      remember: Boolean(sessionRow.lembrar),
      mfaLevel: normalizeOptionalFlag(sessionRow.mfa_level),
      reauthAt: sessionRow.reauth_at,
    },
  } satisfies AuthenticatedAdminRequest;
}

function isAdminUserEligible(user: {
  nivel_acesso: number;
  account_scope: string;
  account_status: string;
  allowed_portals_json: unknown;
  portal_admin_autorizado: boolean;
  empresas: {
    escopo_plataforma: boolean;
  };
}) {
  return (
    Number(user.nivel_acesso) === ADMIN_ACCESS_LEVEL &&
    userHasPlatformScope(user.account_scope, user.empresas.escopo_plataforma) &&
    normalizeFlag(user.account_status, "active") === "active" &&
    portalAdminAuthorized(user.portal_admin_autorizado, user.allowed_portals_json)
  );
}

function isAdminIdentityActive(user: { admin_identity_status: string }) {
  return new Set(["active", "password_reset_required"]).has(
    normalizeFlag(user.admin_identity_status, "active"),
  );
}

function isAdminUserBlocked(user: {
  ativo: boolean;
  status_bloqueio: boolean;
  bloqueado_ate: Date | null;
  accountScope?: string;
  account_scope?: string;
  companyStatusBloqueio?: boolean;
  companyName?: string;
  empresas?: {
    status_bloqueio: boolean;
  };
}) {
  if (!user.ativo) {
    return true;
  }

  const blockedUntil = user.bloqueado_ate;

  if (user.status_bloqueio) {
    if (!blockedUntil) {
      return true;
    }

    if (blockedUntil > new Date()) {
      return true;
    }
  }

  const scope = normalizeFlag(
    user.accountScope ?? user.account_scope ?? "tenant",
    "tenant",
  );

  if (scope !== "platform" && Boolean(user.empresas?.status_bloqueio ?? user.companyStatusBloqueio)) {
    return true;
  }

  return false;
}

async function verifyPasswordHash(password: string, hash: string) {
  const normalizedHash = String(hash ?? "").trim();

  if (!normalizedHash) {
    return false;
  }

  if (normalizedHash.startsWith("$argon2")) {
    try {
      return await verifyArgon2(normalizedHash, password);
    } catch {
      return false;
    }
  }

  return false;
}

async function registerFailedAdminPasswordAttempt(userId: number) {
  const current = await prisma.usuarios.findUnique({
    where: {
      id: userId,
    },
    select: {
      tentativas_login: true,
    },
  });

  if (!current) {
    return;
  }

  const attempts = Number(current.tentativas_login ?? 0) + 1;
  const shouldBlock = attempts >= 5;
  const blockedUntil = shouldBlock ? new Date(Date.now() + 15 * 60 * 1000) : null;

  await prisma.usuarios.update({
    where: {
      id: userId,
    },
    data: {
      tentativas_login: attempts,
      bloqueado_ate: blockedUntil,
      status_bloqueio: shouldBlock ? true : undefined,
      atualizado_em: new Date(),
    },
  });
}

async function createAdminIdentityAudit({
  companyId,
  actorUserId,
  targetUserId,
  action,
  summary,
  detail,
  email,
  reason,
}: {
  companyId?: number;
  actorUserId?: number;
  targetUserId?: number;
  action: string;
  summary: string;
  detail: string;
  email: string;
  reason: string;
}) {
  const resolvedCompanyId = companyId ?? (await getPlatformCompanyId());

  if (!resolvedCompanyId) {
    return;
  }

  await prisma.auditoria_empresas.create({
    data: {
      empresa_id: resolvedCompanyId,
      ator_usuario_id: actorUserId ?? null,
      alvo_usuario_id: targetUserId ?? null,
      portal: ADMIN_PORTAL,
      acao: action,
      resumo: summary.slice(0, 220),
      detalhe: detail.slice(0, 5_000),
      payload_json: {
        email,
        reason,
        provider: "password",
        source_surface: "frontend_astro",
      },
      criado_em: new Date(),
    },
  });
}

async function getPlatformCompanyId() {
  const platformCompany = await prisma.empresas.findFirst({
    where: {
      escopo_plataforma: true,
    },
    orderBy: {
      id: "asc",
    },
    select: {
      id: true,
    },
  });

  return platformCompany?.id ?? null;
}

async function invalidateAdminSessionToken(token: string) {
  await prisma.sessoes_ativas.deleteMany({
    where: {
      token,
    },
  });
}

function resolveSessionExpiration({
  remember,
  currentExpiration,
  now,
}: {
  remember: boolean;
  currentExpiration: Date;
  now: Date;
}) {
  if (!ADMIN_SESSION_RENEWAL_ENABLED) {
    return currentExpiration;
  }

  const renewalWindowMs = ADMIN_SESSION_RENEWAL_WINDOW_MINUTES * 60 * 1000;

  if (currentExpiration.getTime() - now.getTime() > renewalWindowMs) {
    return currentExpiration;
  }

  return resolveNewSessionExpiration(remember, now);
}

function resolveNewSessionExpiration(remember: boolean, now = new Date()) {
  const ttlMs = remember
    ? ADMIN_SESSION_REMEMBER_DAYS * 24 * 60 * 60 * 1000
    : ADMIN_SESSION_TTL_HOURS * 60 * 60 * 1000;

  return new Date(now.getTime() + ttlMs);
}

function userHasPlatformScope(accountScope: string, companyIsPlatform: boolean) {
  return normalizeFlag(accountScope, "tenant") === "platform" || companyIsPlatform;
}

function portalAdminAuthorized(portalFlag: boolean, allowedPortalsRaw: unknown) {
  const allowedPortals = parseAllowedPortals(allowedPortalsRaw);

  if (allowedPortals.length > 0) {
    return Boolean(portalFlag) && allowedPortals.includes(ADMIN_PORTAL);
  }

  return Boolean(portalFlag);
}

function parseAllowedPortals(value: unknown) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => String(item ?? "").trim().toLowerCase())
    .filter(Boolean);
}

function normalizeEmail(value: string) {
  return String(value ?? "").trim().toLowerCase().slice(0, 254);
}

function normalizeFlag(value: string | null | undefined, fallback: string) {
  return String(value ?? fallback).trim().toLowerCase() || fallback;
}

function normalizeOptionalFlag(value: string | null | undefined) {
  const normalized = String(value ?? "").trim().toLowerCase();

  return normalized || null;
}

function getRequestIp(request: Request) {
  const forwardedFor = String(request.headers.get("x-forwarded-for") ?? "")
    .split(",", 1)[0]
    ?.trim();
  const realIp = String(request.headers.get("x-real-ip") ?? "").trim();

  return forwardedFor || realIp || null;
}

function getRequestUserAgent(request: Request) {
  return String(request.headers.get("user-agent") ?? "").trim() || null;
}

function getRequestDeviceId(request: Request, ip: string | null, userAgent: string | null) {
  const headerDeviceId = String(request.headers.get("x-device-id") ?? "").trim();

  if (headerDeviceId) {
    return headerDeviceId.slice(0, 120);
  }

  const digest = createHash("sha256")
    .update(`${userAgent ?? ""}|${ip ?? ""}`, "utf-8")
    .digest("hex");

  return digest.slice(0, 32);
}

function readPositiveIntEnv(key: string, fallback: number) {
  const rawValue = Number(process.env[key] ?? "");

  if (!Number.isFinite(rawValue) || rawValue <= 0) {
    return fallback;
  }

  return Math.trunc(rawValue);
}

function readBooleanEnv(key: string, fallback: boolean) {
  const rawValue = String(process.env[key] ?? "").trim().toLowerCase();

  if (!rawValue) {
    return fallback;
  }

  return rawValue === "1" || rawValue === "true" || rawValue === "yes" || rawValue === "on";
}
