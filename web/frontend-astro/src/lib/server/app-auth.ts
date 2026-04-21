import { createHash, randomBytes } from "node:crypto";

import { verify as verifyArgon2 } from "@node-rs/argon2";
import type { APIContext } from "astro";

import { hashPassword } from "@/lib/server/passwords";
import { prisma } from "@/lib/server/prisma";

const APP_ACCESS_LEVEL = 1;
const APP_PORTAL = "inspetor";
const APP_SESSION_COOKIE = "tariel_app_session";
const APP_PASSWORD_RESET_COOKIE = "tariel_app_password_reset";
const APP_PASSWORD_RESET_PORTAL = "inspetor_password_change";
const APP_SESSION_TTL_HOURS = readPositiveIntEnv("SESSAO_TTL_HORAS", 8);
const APP_SESSION_REMEMBER_DAYS = readPositiveIntEnv("SESSAO_TTL_LEMBRAR_DIAS", 30);
const APP_SESSION_MAX_PER_USER = readPositiveIntEnv("SESSAO_MAX_POR_USUARIO", 5);
const APP_SESSION_RENEWAL_ENABLED = readBooleanEnv("SESSAO_RENOVACAO_ATIVA", true);
const APP_SESSION_RENEWAL_WINDOW_MINUTES = readPositiveIntEnv("SESSAO_JANELA_RENOVACAO_MINUTOS", 30);
const APP_PASSWORD_RESET_TTL_MINUTES = readPositiveIntEnv("APP_TROCA_SENHA_TTL_MINUTOS", 30);

export interface AuthenticatedAppRequest {
  user: {
    id: number;
    companyId: number;
    companyName: string;
    email: string;
    name: string;
    accessLevel: number;
    accountScope: string;
    accountStatus: string;
    canPasswordLogin: boolean;
    allowedPortals: string[];
    mfaRequired: boolean;
    senhaTemporariaAtiva: boolean;
    companyBlocked: boolean;
    companyBlockedReason: string | null;
  };
  session: {
    token: string;
    expiresAt: Date;
    lastActivityAt: Date;
    remember: boolean;
  };
}

export interface AuthenticatedAppPasswordResetRequest {
  user: AuthenticatedAppRequest["user"];
  session: AuthenticatedAppRequest["session"];
}

export interface AppLoginAttemptInput {
  email: string;
  password: string;
  remember: boolean;
  request: Request;
}

export interface AppLoginAttemptResult {
  ok: boolean;
  error?: string;
  session?: AuthenticatedAppRequest;
  passwordReset?: AuthenticatedAppPasswordResetRequest;
}

export interface CompleteAppPasswordResetInput {
  token: string;
  currentPassword: string;
  nextPassword: string;
  confirmPassword: string;
  request: Request;
}

export interface CompleteAppPasswordResetResult {
  ok: boolean;
  error?: string;
  session?: AuthenticatedAppRequest;
}

export function isAppPath(pathname: string) {
  return pathname === "/app" || pathname.startsWith("/app/");
}

export function isPublicAppPath(pathname: string) {
  return (
    pathname === "/app/login"
    || pathname === "/app/login/entrar"
    || pathname === "/app/trocar-senha"
    || pathname === "/app/trocar-senha/salvar"
  );
}

export function safeAppNextPath(value: string | null | undefined, fallback = "/app/inicio") {
  const normalized = String(value ?? "").trim();

  if (!normalized.startsWith("/app")) {
    return fallback;
  }

  if (
    normalized === "/app"
    || normalized === "/app/"
    || normalized.startsWith("/app/login")
    || normalized.startsWith("/app/trocar-senha")
  ) {
    return fallback;
  }

  return normalized;
}

export function buildAppLoginPath(nextPath: string) {
  const redirectTarget = safeAppNextPath(nextPath, "/app/inicio");
  const search = new URLSearchParams({ next: redirectTarget });
  return `/app/login?${search.toString()}`;
}

export async function loadAppRequestSession(context: Pick<APIContext, "cookies" | "request">) {
  const token = readAppSessionToken(context.cookies);

  if (!token) {
    return null;
  }

  const sessionRow = await prisma.sessoes_ativas.findUnique({
    where: { token },
    select: {
      token: true,
      portal: true,
      expira_em: true,
      ultima_atividade_em: true,
      lembrar: true,
      usuarios: {
        select: appUserSelect,
      },
    },
  });

  if (!sessionRow || sessionRow.portal !== APP_PORTAL) {
    await invalidateSessionToken(token);
    clearAppSessionCookie(context.cookies);
    return null;
  }

  const now = new Date();
  if (sessionRow.expira_em <= now) {
    await invalidateSessionToken(token);
    clearAppSessionCookie(context.cookies);
    return null;
  }

  const hydrated = toAuthenticatedAppRequest(sessionRow);

  if (
    !hydrated
    || !isAppUserEligible(sessionRow.usuarios)
    || isAppUserBlocked(sessionRow.usuarios)
    || !sessionRow.usuarios.can_password_login
    || sessionRow.usuarios.senha_temporaria_ativa
  ) {
    await invalidateSessionToken(token);
    clearAppSessionCookie(context.cookies);
    return null;
  }

  const nextExpiration = resolveSessionExpiration({
    remember: sessionRow.lembrar,
    currentExpiration: sessionRow.expira_em,
    now,
  });

  await prisma.sessoes_ativas.update({
    where: { token },
    data: {
      ultima_atividade_em: now,
      expira_em: nextExpiration,
    },
  });

  applyAppSessionCookie(context.cookies, token, {
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
  } satisfies AuthenticatedAppRequest;
}

export async function loadAppPasswordResetSession(context: Pick<APIContext, "cookies" | "request">) {
  const token = readAppPasswordResetToken(context.cookies);

  if (!token) {
    return null;
  }

  const sessionRow = await prisma.sessoes_ativas.findUnique({
    where: { token },
    select: {
      token: true,
      portal: true,
      expira_em: true,
      ultima_atividade_em: true,
      lembrar: true,
      usuarios: {
        select: appUserSelect,
      },
    },
  });

  if (!sessionRow || sessionRow.portal !== APP_PASSWORD_RESET_PORTAL) {
    await invalidateSessionToken(token);
    clearAppPasswordResetCookie(context.cookies);
    return null;
  }

  const now = new Date();
  if (sessionRow.expira_em <= now) {
    await invalidateSessionToken(token);
    clearAppPasswordResetCookie(context.cookies);
    return null;
  }

  const hydrated = toAuthenticatedAppPasswordResetRequest(sessionRow);

  if (
    !hydrated
    || !isAppUserEligible(sessionRow.usuarios)
    || isAppUserBlocked(sessionRow.usuarios)
    || !sessionRow.usuarios.can_password_login
    || !sessionRow.usuarios.senha_temporaria_ativa
  ) {
    await invalidateSessionToken(token);
    clearAppPasswordResetCookie(context.cookies);
    return null;
  }

  applyAppPasswordResetCookie(context.cookies, token, {
    remember: sessionRow.lembrar,
    secure: context.request.url.startsWith("https://"),
  });

  return hydrated;
}

export async function attemptAppPasswordLogin(
  input: AppLoginAttemptInput,
): Promise<AppLoginAttemptResult> {
  const email = normalizeEmail(input.email);
  const password = String(input.password ?? "");

  if (!email || !password) {
    return {
      ok: false,
      error: "Preencha e-mail e senha.",
    };
  }

  const candidate = await prisma.usuarios.findUnique({
    where: { email },
    select: appUserSelect,
  });

  if (!candidate) {
    return {
      ok: false,
      error: "Credenciais invalidas.",
    };
  }

  const passwordMatches = await verifyPasswordHash(password, candidate.senha_hash);
  if (!passwordMatches) {
    await registerFailedAppPasswordAttempt(candidate.id);
    await createAppIdentityAudit({
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      action: "app_identity_denied",
      reason: "invalid_credentials",
      summary: "Login local negado no portal do inspetor",
      detail: "Credenciais invalidas para o acesso do inspetor em Astro.",
    });
    return {
      ok: false,
      error: "Credenciais invalidas.",
    };
  }

  if (!isAppUserEligible(candidate)) {
    const error = resolveAppPortalMismatchMessage(candidate);
    await createAppIdentityAudit({
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      action: "app_identity_denied",
      reason: "portal_not_authorized",
      summary: "Login local negado no portal do inspetor",
      detail: error,
    });
    return {
      ok: false,
      error,
    };
  }

  if (!candidate.can_password_login) {
    await createAppIdentityAudit({
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      action: "app_identity_denied",
      reason: "password_login_disabled",
      summary: "Login local negado no portal do inspetor",
      detail: "A conta foi reconhecida, mas o login por senha nao esta habilitado para o portal do inspetor.",
    });
    return {
      ok: false,
      error: "Sua conta existe, mas o login por senha nao esta habilitado para este portal.",
    };
  }

  if (isAppUserBlocked(candidate)) {
    const blockedMessage = candidate.empresas.status_bloqueio
      ? "A empresa esta bloqueada. Fale com a Tariel ou com o admin-cliente."
      : "Acesso bloqueado. Contate o administrador da empresa.";

    await createAppIdentityAudit({
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      action: "app_identity_denied",
      reason: "account_blocked",
      summary: "Login local negado no portal do inspetor",
      detail: blockedMessage,
    });

    return {
      ok: false,
      error: blockedMessage,
    };
  }

  if (candidate.mfa_required) {
    return {
      ok: false,
      error: "Sua conta exige MFA TOTP. Esse challenge ainda esta em migracao para o portal do inspetor no Astro.",
    };
  }

  const now = new Date();
  const ip = getRequestIp(input.request);
  const userAgent = getRequestUserAgent(input.request);

  if (candidate.senha_temporaria_ativa) {
    const passwordResetToken = randomBytes(48).toString("base64url");
    const passwordResetExpiration = new Date(now.getTime() + APP_PASSWORD_RESET_TTL_MINUTES * 60 * 1000);

    await prisma.$transaction(async (tx) => {
      await tx.sessoes_ativas.deleteMany({
        where: {
          usuario_id: candidate.id,
          portal: APP_PASSWORD_RESET_PORTAL,
        },
      });

      await tx.usuarios.update({
        where: { id: candidate.id },
        data: {
          tentativas_login: 0,
          bloqueado_ate: null,
          status_bloqueio: false,
          atualizado_em: now,
        },
      });

      await tx.sessoes_ativas.create({
        data: {
          token: passwordResetToken,
          usuario_id: candidate.id,
          criada_em: now,
          expira_em: passwordResetExpiration,
          ultima_atividade_em: now,
          lembrar: input.remember,
          portal: APP_PASSWORD_RESET_PORTAL,
          account_scope: normalizeFlag(candidate.account_scope, "tenant"),
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
          portal: APP_PORTAL,
          acao: "app_password_reset_started",
          resumo: "Primeiro acesso iniciado no portal do inspetor",
          detalhe:
            "Credencial temporaria validada no Astro. O acesso segue para troca obrigatoria de senha antes da sessao final do inspetor.",
          payload_json: {
            provider: "password",
            source_surface: "frontend_astro",
            reason: "temporary_password_validated",
          },
          criado_em: now,
        },
      });
    });

    const passwordReset = toAuthenticatedAppPasswordResetRequest({
      token: passwordResetToken,
      expira_em: passwordResetExpiration,
      ultima_atividade_em: now,
      lembrar: input.remember,
      usuarios: candidate,
    });

    if (!passwordReset) {
      throw new Error("Falha ao hidratar o fluxo de troca de senha do portal do inspetor.");
    }

    return {
      ok: false,
      passwordReset,
    };
  }

  const sessionToken = randomBytes(48).toString("base64url");
  const sessionExpiration = resolveNewSessionExpiration(input.remember, now);

  await prisma.$transaction(async (tx) => {
    const currentSessions = await tx.sessoes_ativas.findMany({
      where: {
        usuario_id: candidate.id,
        portal: APP_PORTAL,
      },
      orderBy: {
        criada_em: "asc",
      },
      select: {
        token: true,
      },
    });

    const overflow = Math.max(currentSessions.length - APP_SESSION_MAX_PER_USER + 1, 0);
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
      where: { id: candidate.id },
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
        portal: APP_PORTAL,
        account_scope: normalizeFlag(candidate.account_scope, "tenant"),
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
        portal: APP_PORTAL,
        acao: "app_login_authenticated",
        resumo: "Login password concluido no portal do inspetor",
        detalhe: "Sessao do inspetor emitida no Astro SSR com persistencia em sessoes_ativas.",
        payload_json: {
          provider: "password",
          source_surface: "frontend_astro",
          next_phase: "inspector_workspace_migration",
        },
        criado_em: now,
      },
    });
  });

  const authenticated = toAuthenticatedAppRequest({
    token: sessionToken,
    expira_em: sessionExpiration,
    ultima_atividade_em: now,
    lembrar: input.remember,
    usuarios: candidate,
  });

  if (!authenticated) {
    throw new Error("Falha ao hidratar a sessao do portal do inspetor criada no Astro.");
  }

  return {
    ok: true,
    session: authenticated,
  };
}

export async function completeAppPasswordReset(
  input: CompleteAppPasswordResetInput,
): Promise<CompleteAppPasswordResetResult> {
  const token = String(input.token ?? "").trim();

  if (!token) {
    return {
      ok: false,
      error: "Fluxo de troca de senha invalido ou expirado.",
    };
  }

  const sessionRow = await prisma.sessoes_ativas.findUnique({
    where: { token },
    select: {
      token: true,
      portal: true,
      expira_em: true,
      ultima_atividade_em: true,
      lembrar: true,
      usuarios: {
        select: appUserSelect,
      },
    },
  });

  if (!sessionRow || sessionRow.portal !== APP_PASSWORD_RESET_PORTAL) {
    return {
      ok: false,
      error: "Fluxo de troca de senha invalido ou expirado.",
    };
  }

  if (sessionRow.expira_em <= new Date()) {
    await invalidateSessionToken(token);
    return {
      ok: false,
      error: "Fluxo de troca de senha expirado. Entre novamente com a senha temporaria.",
    };
  }

  const candidate = sessionRow.usuarios;
  if (
    !isAppUserEligible(candidate)
    || isAppUserBlocked(candidate)
    || !candidate.can_password_login
    || !candidate.senha_temporaria_ativa
  ) {
    await invalidateSessionToken(token);
    return {
      ok: false,
      error: "Sua conta nao pode concluir a troca obrigatoria de senha neste momento.",
    };
  }

  const validationError = validateAppPasswordResetInput(
    input.currentPassword,
    input.nextPassword,
    input.confirmPassword,
  );
  if (validationError) {
    return {
      ok: false,
      error: validationError,
    };
  }

  const currentPasswordMatches = await verifyPasswordHash(
    String(input.currentPassword ?? ""),
    candidate.senha_hash,
  );
  if (!currentPasswordMatches) {
    return {
      ok: false,
      error: "Senha temporaria invalida.",
    };
  }

  const now = new Date();
  const ip = getRequestIp(input.request);
  const userAgent = getRequestUserAgent(input.request);
  const nextPasswordHash = await hashPassword(input.nextPassword);
  const sessionToken = randomBytes(48).toString("base64url");
  const sessionExpiration = resolveNewSessionExpiration(sessionRow.lembrar, now);

  await prisma.$transaction(async (tx) => {
    const currentSessions = await tx.sessoes_ativas.findMany({
      where: {
        usuario_id: candidate.id,
        portal: APP_PORTAL,
      },
      orderBy: {
        criada_em: "asc",
      },
      select: {
        token: true,
      },
    });

    const overflow = Math.max(currentSessions.length - APP_SESSION_MAX_PER_USER + 1, 0);
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
      where: { id: candidate.id },
      data: {
        senha_hash: nextPasswordHash,
        senha_temporaria_ativa: false,
        tentativas_login: 0,
        bloqueado_ate: null,
        status_bloqueio: false,
        ultimo_login: now,
        ultimo_login_ip: ip?.slice(0, 45) ?? null,
        atualizado_em: now,
      },
    });

    await tx.sessoes_ativas.deleteMany({
      where: {
        OR: [
          { token },
          {
            usuario_id: candidate.id,
            portal: APP_PASSWORD_RESET_PORTAL,
          },
        ],
      },
    });

    await tx.sessoes_ativas.create({
      data: {
        token: sessionToken,
        usuario_id: candidate.id,
        criada_em: now,
        expira_em: sessionExpiration,
        ultima_atividade_em: now,
        lembrar: sessionRow.lembrar,
        portal: APP_PORTAL,
        account_scope: normalizeFlag(candidate.account_scope, "tenant"),
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
        portal: APP_PORTAL,
        acao: "app_password_reset_completed",
        resumo: "Troca obrigatoria de senha concluida no portal do inspetor",
        detalhe: "Senha temporaria substituida no Astro e sessao oficial do inspetor emitida em Prisma.",
        payload_json: {
          provider: "password",
          source_surface: "frontend_astro",
          reason: "temporary_password_rotated",
        },
        criado_em: now,
      },
    });
  });

  const authenticated = toAuthenticatedAppRequest({
    token: sessionToken,
    expira_em: sessionExpiration,
    ultima_atividade_em: now,
    lembrar: sessionRow.lembrar,
    usuarios: {
      ...candidate,
      senha_temporaria_ativa: false,
    },
  });

  if (!authenticated) {
    throw new Error("Falha ao hidratar a sessao do portal do inspetor apos a troca de senha.");
  }

  return {
    ok: true,
    session: authenticated,
  };
}

export function applyAppSessionCookie(
  cookies: APIContext["cookies"],
  token: string,
  options: {
    remember: boolean;
    secure: boolean;
  },
) {
  applySessionCookie(cookies, APP_SESSION_COOKIE, token, options);
}

export function applyAppPasswordResetCookie(
  cookies: APIContext["cookies"],
  token: string,
  options: {
    remember: boolean;
    secure: boolean;
  },
) {
  cookies.set(APP_PASSWORD_RESET_COOKIE, token, {
    httpOnly: true,
    path: "/",
    sameSite: "lax",
    secure: options.secure,
    maxAge: APP_PASSWORD_RESET_TTL_MINUTES * 60,
  });
}

export async function destroyAppSession(context: Pick<APIContext, "cookies">, token?: string | null) {
  const currentToken = String(token ?? readAppSessionToken(context.cookies) ?? "").trim();

  if (currentToken) {
    await invalidateSessionToken(currentToken);
  }

  clearAppSessionCookie(context.cookies);
}

export async function destroyAppPasswordResetSession(
  context: Pick<APIContext, "cookies">,
  token?: string | null,
) {
  const currentToken = String(token ?? readAppPasswordResetToken(context.cookies) ?? "").trim();

  if (currentToken) {
    await invalidateSessionToken(currentToken);
  }

  clearAppPasswordResetCookie(context.cookies);
}

export function readAppSessionToken(cookies: APIContext["cookies"]) {
  return String(cookies.get(APP_SESSION_COOKIE)?.value ?? "").trim() || null;
}

export function readAppPasswordResetToken(cookies: APIContext["cookies"]) {
  return String(cookies.get(APP_PASSWORD_RESET_COOKIE)?.value ?? "").trim() || null;
}

export function clearAppSessionCookie(cookies: APIContext["cookies"]) {
  cookies.delete(APP_SESSION_COOKIE, { path: "/" });
}

export function clearAppPasswordResetCookie(cookies: APIContext["cookies"]) {
  cookies.delete(APP_PASSWORD_RESET_COOKIE, { path: "/" });
}

const appUserSelect = {
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
  empresas: {
    select: {
      nome_fantasia: true,
      status_bloqueio: true,
      motivo_bloqueio: true,
    },
  },
} as const;

function toAuthenticatedAppRequest(
  sessionRow:
    | {
        token: string;
        expira_em: Date;
        ultima_atividade_em: Date;
        lembrar: boolean;
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
          empresas: {
            nome_fantasia: string;
            status_bloqueio: boolean;
            motivo_bloqueio: string | null;
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
      canPasswordLogin: user.can_password_login,
      allowedPortals: parseAllowedPortals(user.allowed_portals_json),
      mfaRequired: user.mfa_required,
      senhaTemporariaAtiva: user.senha_temporaria_ativa,
      companyBlocked: Boolean(user.empresas.status_bloqueio),
      companyBlockedReason: user.empresas.motivo_bloqueio,
    },
    session: {
      token: sessionRow.token,
      expiresAt: sessionRow.expira_em,
      lastActivityAt: sessionRow.ultima_atividade_em,
      remember: sessionRow.lembrar,
    },
  } satisfies AuthenticatedAppRequest;
}

function toAuthenticatedAppPasswordResetRequest(
  sessionRow:
    | {
        token: string;
        expira_em: Date;
        ultima_atividade_em: Date;
        lembrar: boolean;
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
          empresas: {
            nome_fantasia: string;
            status_bloqueio: boolean;
            motivo_bloqueio: string | null;
          };
        };
      }
    | null,
) {
  const hydrated = toAuthenticatedAppRequest(sessionRow);
  if (!hydrated) {
    return null;
  }

  return {
    user: hydrated.user,
    session: hydrated.session,
  } satisfies AuthenticatedAppPasswordResetRequest;
}

function isAppUserEligible(user: {
  nivel_acesso: number;
  account_scope: string;
  account_status: string;
  allowed_portals_json: unknown;
}) {
  return (
    Number(user.nivel_acesso) === APP_ACCESS_LEVEL
    && normalizeFlag(user.account_scope, "tenant") !== "platform"
    && normalizeFlag(user.account_status, "active") === "active"
    && appPortalAuthorized(user.allowed_portals_json, Number(user.nivel_acesso))
  );
}

function isAppUserBlocked(user: {
  ativo: boolean;
  status_bloqueio: boolean;
  bloqueado_ate: Date | null;
  empresas: {
    status_bloqueio: boolean;
  };
}) {
  if (!user.ativo) {
    return true;
  }

  if (Boolean(user.empresas.status_bloqueio)) {
    return true;
  }

  if (!user.status_bloqueio) {
    return false;
  }

  if (!user.bloqueado_ate) {
    return true;
  }

  return user.bloqueado_ate > new Date();
}

function appPortalAuthorized(allowedPortalsRaw: unknown, accessLevel: number) {
  const allowedPortals = parseAllowedPortals(allowedPortalsRaw);

  if (allowedPortals.length > 0) {
    return allowedPortals.includes(APP_PORTAL);
  }

  return accessLevel === APP_ACCESS_LEVEL;
}

function resolveAppPortalMismatchMessage(user: {
  nivel_acesso: number;
  allowed_portals_json: unknown;
  account_scope: string;
}) {
  if (normalizeFlag(user.account_scope, "tenant") === "platform") {
    return "Esta credencial pertence ao portal da Tariel em /admin/login.";
  }

  const allowedPortals = parseAllowedPortals(user.allowed_portals_json);

  if (allowedPortals.includes("cliente") && !allowedPortals.includes(APP_PORTAL)) {
    return "Esta credencial deve acessar /cliente/login.";
  }

  if (allowedPortals.includes("revisor") && !allowedPortals.includes(APP_PORTAL)) {
    return "Esta credencial deve acessar /revisao/login.";
  }

  if (allowedPortals.includes("admin")) {
    return "Esta credencial pertence ao portal da Tariel em /admin/login.";
  }

  if (Number(user.nivel_acesso) === 50) {
    return "Esta credencial deve acessar /revisao/login.";
  }

  if (Number(user.nivel_acesso) === 80) {
    return "Esta credencial deve acessar /cliente/login.";
  }

  return "Acesso negado para este portal.";
}

function validateAppPasswordResetInput(
  currentPassword: string,
  nextPassword: string,
  confirmPassword: string,
) {
  const current = String(currentPassword ?? "");
  const next = String(nextPassword ?? "");
  const confirm = String(confirmPassword ?? "");

  if (!current || !next || !confirm) {
    return "Preencha senha atual, nova senha e confirmacao.";
  }

  if (next !== confirm) {
    return "A confirmacao da nova senha nao confere.";
  }

  if (next.length < 8) {
    return "A nova senha deve ter no minimo 8 caracteres.";
  }

  if (next === current) {
    return "A nova senha deve ser diferente da senha temporaria.";
  }

  return "";
}

async function verifyPasswordHash(password: string, hash: string) {
  const normalizedHash = String(hash ?? "").trim();

  if (!normalizedHash || !normalizedHash.startsWith("$argon2")) {
    return false;
  }

  try {
    return await verifyArgon2(normalizedHash, password);
  } catch {
    return false;
  }
}

async function registerFailedAppPasswordAttempt(userId: number) {
  const current = await prisma.usuarios.findUnique({
    where: { id: userId },
    select: { tentativas_login: true },
  });

  if (!current) {
    return;
  }

  const attempts = Number(current.tentativas_login ?? 0) + 1;
  const shouldBlock = attempts >= 5;
  const blockedUntil = shouldBlock ? new Date(Date.now() + 15 * 60 * 1000) : null;

  await prisma.usuarios.update({
    where: { id: userId },
    data: {
      tentativas_login: attempts,
      bloqueado_ate: blockedUntil,
      status_bloqueio: shouldBlock ? true : undefined,
      atualizado_em: new Date(),
    },
  });
}

async function createAppIdentityAudit({
  companyId,
  actorUserId,
  targetUserId,
  action,
  summary,
  detail,
  email,
  reason,
}: {
  companyId: number;
  actorUserId?: number;
  targetUserId?: number;
  action: string;
  summary: string;
  detail: string;
  email: string;
  reason: string;
}) {
  await prisma.auditoria_empresas.create({
    data: {
      empresa_id: companyId,
      ator_usuario_id: actorUserId ?? null,
      alvo_usuario_id: targetUserId ?? null,
      portal: APP_PORTAL,
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

function normalizeEmail(value: string) {
  return String(value ?? "").trim().toLowerCase().slice(0, 254);
}

function normalizeFlag(value: unknown, fallback: string) {
  return String(value ?? fallback).trim().toLowerCase() || fallback;
}

function parseAllowedPortals(value: unknown) {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item ?? "").trim().toLowerCase())
      .filter(Boolean);
  }

  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return parsed
          .map((item) => String(item ?? "").trim().toLowerCase())
          .filter(Boolean);
      }
    } catch {
      return [];
    }
  }

  return [];
}

function readPositiveIntEnv(name: string, fallback: number) {
  const raw = Number(process.env[name] ?? fallback);
  return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : fallback;
}

function readBooleanEnv(name: string, fallback: boolean) {
  const raw = String(process.env[name] ?? "").trim().toLowerCase();
  if (!raw) {
    return fallback;
  }

  return raw === "1" || raw === "true" || raw === "sim" || raw === "yes" || raw === "on";
}

function resolveNewSessionExpiration(remember: boolean, now = new Date()) {
  const ttlMs = remember
    ? APP_SESSION_REMEMBER_DAYS * 24 * 60 * 60 * 1000
    : APP_SESSION_TTL_HOURS * 60 * 60 * 1000;

  return new Date(now.getTime() + ttlMs);
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
  if (!APP_SESSION_RENEWAL_ENABLED) {
    return currentExpiration;
  }

  const renewalWindowMs = APP_SESSION_RENEWAL_WINDOW_MINUTES * 60 * 1000;

  if (currentExpiration.getTime() - now.getTime() > renewalWindowMs) {
    return currentExpiration;
  }

  return resolveNewSessionExpiration(remember, now);
}

function getRequestIp(request: Request) {
  const forwardedFor = String(request.headers.get("x-forwarded-for") ?? "").split(",", 1)[0]?.trim();
  const realIp = String(request.headers.get("x-real-ip") ?? "").trim();

  return forwardedFor || realIp || null;
}

function getRequestUserAgent(request: Request) {
  return String(request.headers.get("user-agent") ?? "").trim() || null;
}

function getRequestDeviceId(request: Request, ip: string | null, userAgent: string | null) {
  const base = [
    String(request.headers.get("x-device-id") ?? "").trim(),
    String(request.headers.get("sec-ch-ua-platform") ?? "").trim(),
    String(request.headers.get("sec-ch-ua") ?? "").trim(),
    ip ?? "",
    userAgent ?? "",
  ].join("|");

  return createHash("sha256").update(base).digest("hex");
}

function applySessionCookie(
  cookies: APIContext["cookies"],
  cookieName: string,
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
    cookies.set(cookieName, token, {
      ...cookieOptions,
      maxAge: APP_SESSION_REMEMBER_DAYS * 24 * 60 * 60,
    });
    return;
  }

  cookies.set(cookieName, token, cookieOptions);
}

async function invalidateSessionToken(token: string) {
  await prisma.sessoes_ativas.deleteMany({
    where: { token },
  });
}
