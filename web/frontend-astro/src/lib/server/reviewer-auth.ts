import { createHash, randomBytes } from "node:crypto";

import { verify as verifyArgon2 } from "@node-rs/argon2";
import type { APIContext } from "astro";

import { prisma } from "@/lib/server/prisma";
import { hashPassword } from "@/lib/server/passwords";

const REVIEWER_ACCESS_LEVEL = 50;
const REVIEWER_PORTAL = "revisor";
const REVIEWER_SESSION_COOKIE = "tariel_reviewer_session";
const REVIEWER_PASSWORD_RESET_COOKIE = "tariel_reviewer_password_reset";
const REVIEWER_PASSWORD_RESET_PORTAL = "revisor_password_change";
const REVIEWER_SESSION_TTL_HOURS = readPositiveIntEnv("SESSAO_TTL_HORAS", 8);
const REVIEWER_SESSION_REMEMBER_DAYS = readPositiveIntEnv("SESSAO_TTL_LEMBRAR_DIAS", 30);
const REVIEWER_SESSION_MAX_PER_USER = readPositiveIntEnv("SESSAO_MAX_POR_USUARIO", 5);
const REVIEWER_SESSION_RENEWAL_ENABLED = readBooleanEnv("SESSAO_RENOVACAO_ATIVA", true);
const REVIEWER_SESSION_RENEWAL_WINDOW_MINUTES = readPositiveIntEnv("SESSAO_JANELA_RENOVACAO_MINUTOS", 30);
const REVIEWER_PASSWORD_RESET_TTL_MINUTES = readPositiveIntEnv("REVISAO_TROCA_SENHA_TTL_MINUTOS", 30);

export interface AuthenticatedReviewerRequest {
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

export interface AuthenticatedReviewerPasswordResetRequest {
  user: AuthenticatedReviewerRequest["user"];
  session: AuthenticatedReviewerRequest["session"];
}

export interface ReviewerLoginAttemptInput {
  email: string;
  password: string;
  remember: boolean;
  request: Request;
}

export interface ReviewerLoginAttemptResult {
  ok: boolean;
  error?: string;
  session?: AuthenticatedReviewerRequest;
  passwordReset?: AuthenticatedReviewerPasswordResetRequest;
}

export interface CompleteReviewerPasswordResetInput {
  token: string;
  currentPassword: string;
  nextPassword: string;
  confirmPassword: string;
  request: Request;
}

export interface CompleteReviewerPasswordResetResult {
  ok: boolean;
  error?: string;
  session?: AuthenticatedReviewerRequest;
}

export function isReviewerPath(pathname: string) {
  return pathname === "/revisao" || pathname.startsWith("/revisao/");
}

export function isPublicReviewerPath(pathname: string) {
  return (
    pathname === "/revisao/login"
    || pathname === "/revisao/login/entrar"
    || pathname === "/revisao/trocar-senha"
    || pathname === "/revisao/trocar-senha/salvar"
  );
}

export function safeReviewerNextPath(value: string | null | undefined, fallback = "/revisao/painel") {
  const normalized = String(value ?? "").trim();

  if (!normalized.startsWith("/revisao")) {
    return fallback;
  }

  if (
    normalized === "/revisao"
    || normalized.startsWith("/revisao/login")
    || normalized.startsWith("/revisao/trocar-senha")
  ) {
    return fallback;
  }

  return normalized;
}

export function buildReviewerLoginPath(nextPath: string) {
  const redirectTarget = safeReviewerNextPath(nextPath, "/revisao/painel");
  const search = new URLSearchParams({ next: redirectTarget });
  return `/revisao/login?${search.toString()}`;
}

export async function loadReviewerRequestSession(context: Pick<APIContext, "cookies" | "request">) {
  const token = readReviewerSessionToken(context.cookies);

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
        select: reviewerUserSelect,
      },
    },
  });

  if (!sessionRow || sessionRow.portal !== REVIEWER_PORTAL) {
    await invalidateSessionToken(token);
    clearReviewerSessionCookie(context.cookies);
    return null;
  }

  const now = new Date();
  if (sessionRow.expira_em <= now) {
    await invalidateSessionToken(token);
    clearReviewerSessionCookie(context.cookies);
    return null;
  }

  const hydrated = toAuthenticatedReviewerRequest(sessionRow);

  if (
    !hydrated
    || !isReviewerUserEligible(sessionRow.usuarios)
    || isReviewerUserBlocked(sessionRow.usuarios)
    || !sessionRow.usuarios.can_password_login
    || sessionRow.usuarios.senha_temporaria_ativa
  ) {
    await invalidateSessionToken(token);
    clearReviewerSessionCookie(context.cookies);
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

  applyReviewerSessionCookie(context.cookies, token, {
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
  } satisfies AuthenticatedReviewerRequest;
}

export async function loadReviewerPasswordResetSession(
  context: Pick<APIContext, "cookies" | "request">,
) {
  const token = readReviewerPasswordResetToken(context.cookies);

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
        select: reviewerUserSelect,
      },
    },
  });

  if (!sessionRow || sessionRow.portal !== REVIEWER_PASSWORD_RESET_PORTAL) {
    await invalidateSessionToken(token);
    clearReviewerPasswordResetCookie(context.cookies);
    return null;
  }

  const now = new Date();
  if (sessionRow.expira_em <= now) {
    await invalidateSessionToken(token);
    clearReviewerPasswordResetCookie(context.cookies);
    return null;
  }

  const hydrated = toAuthenticatedReviewerPasswordResetRequest(sessionRow);

  if (
    !hydrated
    || !isReviewerUserEligible(sessionRow.usuarios)
    || isReviewerUserBlocked(sessionRow.usuarios)
    || !sessionRow.usuarios.can_password_login
    || !sessionRow.usuarios.senha_temporaria_ativa
  ) {
    await invalidateSessionToken(token);
    clearReviewerPasswordResetCookie(context.cookies);
    return null;
  }

  applyReviewerPasswordResetCookie(context.cookies, token, {
    remember: sessionRow.lembrar,
    secure: context.request.url.startsWith("https://"),
  });

  return hydrated;
}

export async function attemptReviewerPasswordLogin(
  input: ReviewerLoginAttemptInput,
): Promise<ReviewerLoginAttemptResult> {
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
    select: reviewerUserSelect,
  });

  if (!candidate) {
    return {
      ok: false,
      error: "Credenciais invalidas.",
    };
  }

  const passwordMatches = await verifyPasswordHash(password, candidate.senha_hash);
  if (!passwordMatches) {
    await registerFailedReviewerPasswordAttempt(candidate.id);
    await createReviewerIdentityAudit({
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      action: "reviewer_identity_denied",
      reason: "invalid_credentials",
      summary: "Login local negado na mesa avaliadora",
      detail: "Credenciais invalidas para o acesso do revisor em Astro.",
    });
    return {
      ok: false,
      error: "Credenciais invalidas.",
    };
  }

  if (!isReviewerUserEligible(candidate)) {
    const error = resolveReviewerPortalMismatchMessage(candidate);
    await createReviewerIdentityAudit({
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      action: "reviewer_identity_denied",
      reason: "portal_not_authorized",
      summary: "Login local negado na mesa avaliadora",
      detail: error,
    });
    return {
      ok: false,
      error,
    };
  }

  if (!candidate.can_password_login) {
    await createReviewerIdentityAudit({
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      action: "reviewer_identity_denied",
      reason: "password_login_disabled",
      summary: "Login local negado na mesa avaliadora",
      detail: "A conta foi reconhecida, mas o login por senha nao esta habilitado para o portal revisor.",
    });
    return {
      ok: false,
      error: "Sua conta existe, mas o login por senha nao esta habilitado para este portal.",
    };
  }

  if (isReviewerUserBlocked(candidate)) {
    const blockedMessage = candidate.empresas.status_bloqueio
      ? "A empresa esta bloqueada. Fale com a Tariel ou com o Admin-CEO."
      : "Acesso bloqueado. Contate o administrador da empresa.";

    await createReviewerIdentityAudit({
      companyId: candidate.empresa_id,
      actorUserId: candidate.id,
      targetUserId: candidate.id,
      email,
      action: "reviewer_identity_denied",
      reason: "account_blocked",
      summary: "Login local negado na mesa avaliadora",
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
      error: "Sua conta exige MFA TOTP. Esse challenge ainda esta em migracao para o portal revisor no Astro.",
    };
  }

  const now = new Date();
  const ip = getRequestIp(input.request);
  const userAgent = getRequestUserAgent(input.request);

  if (candidate.senha_temporaria_ativa) {
    const passwordResetToken = randomBytes(48).toString("base64url");
    const passwordResetExpiration = new Date(
      now.getTime() + REVIEWER_PASSWORD_RESET_TTL_MINUTES * 60 * 1000,
    );

    await prisma.$transaction(async (tx) => {
      await tx.sessoes_ativas.deleteMany({
        where: {
          usuario_id: candidate.id,
          portal: REVIEWER_PASSWORD_RESET_PORTAL,
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
          portal: REVIEWER_PASSWORD_RESET_PORTAL,
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
          portal: REVIEWER_PORTAL,
          acao: "reviewer_password_reset_started",
          resumo: "Primeiro acesso iniciado na mesa avaliadora",
          detalhe:
            "Credencial temporaria validada no Astro. O acesso segue para troca obrigatoria de senha antes da sessao final do revisor.",
          payload_json: {
            provider: "password",
            source_surface: "frontend_astro",
            reason: "temporary_password_validated",
          },
          criado_em: now,
        },
      });
    });

    const passwordReset = toAuthenticatedReviewerPasswordResetRequest({
      token: passwordResetToken,
      expira_em: passwordResetExpiration,
      ultima_atividade_em: now,
      lembrar: input.remember,
      usuarios: candidate,
    });

    if (!passwordReset) {
      throw new Error("Falha ao hidratar o fluxo de troca de senha do portal revisor.");
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
        portal: REVIEWER_PORTAL,
      },
      orderBy: {
        criada_em: "asc",
      },
      select: {
        token: true,
      },
    });

    const overflow = Math.max(currentSessions.length - REVIEWER_SESSION_MAX_PER_USER + 1, 0);
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
        portal: REVIEWER_PORTAL,
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
        portal: REVIEWER_PORTAL,
        acao: "reviewer_login_authenticated",
        resumo: "Login password concluido na mesa avaliadora",
        detalhe: "Sessao do revisor emitida no Astro SSR com persistencia em sessoes_ativas.",
        payload_json: {
          provider: "password",
          source_surface: "frontend_astro",
          next_phase: "review_panel_migration",
        },
        criado_em: now,
      },
    });
  });

  const authenticated = toAuthenticatedReviewerRequest({
    token: sessionToken,
    expira_em: sessionExpiration,
    ultima_atividade_em: now,
    lembrar: input.remember,
    usuarios: candidate,
  });

  if (!authenticated) {
    throw new Error("Falha ao hidratar a sessao do portal revisor criada no Astro.");
  }

  return {
    ok: true,
    session: authenticated,
  };
}

export async function completeReviewerPasswordReset(
  input: CompleteReviewerPasswordResetInput,
): Promise<CompleteReviewerPasswordResetResult> {
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
        select: reviewerUserSelect,
      },
    },
  });

  if (!sessionRow || sessionRow.portal !== REVIEWER_PASSWORD_RESET_PORTAL) {
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
    !isReviewerUserEligible(candidate)
    || isReviewerUserBlocked(candidate)
    || !candidate.senha_temporaria_ativa
  ) {
    await invalidateSessionToken(token);
    return {
      ok: false,
      error: "Sua conta nao pode concluir a troca obrigatoria de senha neste momento.",
    };
  }

  const validationError = validateReviewerPasswordResetInput(
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
        portal: REVIEWER_PORTAL,
      },
      orderBy: {
        criada_em: "asc",
      },
      select: {
        token: true,
      },
    });

    const overflow = Math.max(currentSessions.length - REVIEWER_SESSION_MAX_PER_USER + 1, 0);
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
            portal: REVIEWER_PASSWORD_RESET_PORTAL,
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
        portal: REVIEWER_PORTAL,
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
        portal: REVIEWER_PORTAL,
        acao: "reviewer_password_reset_completed",
        resumo: "Troca obrigatoria de senha concluida na mesa avaliadora",
        detalhe: "Senha temporaria substituida no Astro e sessao oficial do revisor emitida em Prisma.",
        payload_json: {
          provider: "password",
          source_surface: "frontend_astro",
          reason: "temporary_password_rotated",
        },
        criado_em: now,
      },
    });
  });

  const authenticated = toAuthenticatedReviewerRequest({
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
    throw new Error("Falha ao hidratar a sessao do portal revisor apos a troca de senha.");
  }

  return {
    ok: true,
    session: authenticated,
  };
}

export function applyReviewerSessionCookie(
  cookies: APIContext["cookies"],
  token: string,
  options: {
    remember: boolean;
    secure: boolean;
  },
) {
  applySessionCookie(cookies, REVIEWER_SESSION_COOKIE, token, {
    remember: options.remember,
    secure: options.secure,
  });
}

export function applyReviewerPasswordResetCookie(
  cookies: APIContext["cookies"],
  token: string,
  options: {
    remember: boolean;
    secure: boolean;
  },
) {
  cookies.set(REVIEWER_PASSWORD_RESET_COOKIE, token, {
    httpOnly: true,
    path: "/",
    sameSite: "lax",
    secure: options.secure,
    maxAge: REVIEWER_PASSWORD_RESET_TTL_MINUTES * 60,
  });
}

export async function destroyReviewerSession(context: Pick<APIContext, "cookies">, token?: string | null) {
  const currentToken = String(token ?? readReviewerSessionToken(context.cookies) ?? "").trim();

  if (currentToken) {
    await invalidateSessionToken(currentToken);
  }

  clearReviewerSessionCookie(context.cookies);
}

export function readReviewerSessionToken(cookies: APIContext["cookies"]) {
  return String(cookies.get(REVIEWER_SESSION_COOKIE)?.value ?? "").trim() || null;
}

export function readReviewerPasswordResetToken(cookies: APIContext["cookies"]) {
  return String(cookies.get(REVIEWER_PASSWORD_RESET_COOKIE)?.value ?? "").trim() || null;
}

export function clearReviewerSessionCookie(cookies: APIContext["cookies"]) {
  cookies.delete(REVIEWER_SESSION_COOKIE, { path: "/" });
}

export function clearReviewerPasswordResetCookie(cookies: APIContext["cookies"]) {
  cookies.delete(REVIEWER_PASSWORD_RESET_COOKIE, { path: "/" });
}

const reviewerUserSelect = {
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

function toAuthenticatedReviewerRequest(
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
      canPasswordLogin: Boolean(user.can_password_login),
      allowedPortals: parseAllowedPortals(user.allowed_portals_json),
      mfaRequired: Boolean(user.mfa_required),
      senhaTemporariaAtiva: Boolean(user.senha_temporaria_ativa),
      companyBlocked: Boolean(user.empresas.status_bloqueio),
      companyBlockedReason: user.empresas.motivo_bloqueio,
    },
    session: {
      token: sessionRow.token,
      expiresAt: sessionRow.expira_em,
      lastActivityAt: sessionRow.ultima_atividade_em,
      remember: Boolean(sessionRow.lembrar),
    },
  } satisfies AuthenticatedReviewerRequest;
}

function toAuthenticatedReviewerPasswordResetRequest(
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

  const hydrated = toAuthenticatedReviewerRequest({
    token: sessionRow.token,
    expira_em: sessionRow.expira_em,
    ultima_atividade_em: sessionRow.ultima_atividade_em,
    lembrar: sessionRow.lembrar,
    usuarios: sessionRow.usuarios,
  });

  if (!hydrated) {
    return null;
  }

  return {
    user: hydrated.user,
    session: hydrated.session,
  } satisfies AuthenticatedReviewerPasswordResetRequest;
}

function isReviewerUserEligible(user: {
  nivel_acesso: number;
  account_scope: string;
  account_status: string;
  allowed_portals_json: unknown;
}) {
  return (
    Number(user.nivel_acesso) === REVIEWER_ACCESS_LEVEL
    && normalizeFlag(user.account_scope, "tenant") !== "platform"
    && normalizeFlag(user.account_status, "active") === "active"
    && reviewerPortalAuthorized(user.allowed_portals_json, Number(user.nivel_acesso))
  );
}

function isReviewerUserBlocked(user: {
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

function reviewerPortalAuthorized(allowedPortalsRaw: unknown, accessLevel: number) {
  const allowedPortals = parseAllowedPortals(allowedPortalsRaw);

  if (allowedPortals.length > 0) {
    return allowedPortals.includes(REVIEWER_PORTAL);
  }

  return accessLevel === REVIEWER_ACCESS_LEVEL;
}

function resolveReviewerPortalMismatchMessage(user: {
  nivel_acesso: number;
  allowed_portals_json: unknown;
  account_scope: string;
}) {
  if (normalizeFlag(user.account_scope, "tenant") === "platform") {
    return "Esta credencial pertence ao portal da Tariel em /admin/login.";
  }

  const allowedPortals = parseAllowedPortals(user.allowed_portals_json);

  if (allowedPortals.includes("cliente") && !allowedPortals.includes(REVIEWER_PORTAL)) {
    return "Esta credencial deve acessar /cliente/login.";
  }

  if (allowedPortals.includes("inspetor") && !allowedPortals.includes(REVIEWER_PORTAL)) {
    return "Esta credencial deve acessar /app/login.";
  }

  if (allowedPortals.includes("admin")) {
    return "Esta credencial pertence ao portal da Tariel em /admin/login.";
  }

  if (Number(user.nivel_acesso) === 1) {
    return "Esta credencial deve acessar /app/login.";
  }

  if (Number(user.nivel_acesso) === 80) {
    return "Esta credencial deve acessar /cliente/login.";
  }

  return "Acesso negado para este portal.";
}

function validateReviewerPasswordResetInput(
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

async function registerFailedReviewerPasswordAttempt(userId: number) {
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

async function createReviewerIdentityAudit({
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
      portal: REVIEWER_PORTAL,
      acao: action,
      resumo: summary,
      detalhe: detail,
      payload_json: {
        email,
        reason,
        source_surface: "frontend_astro",
      },
      criado_em: new Date(),
    },
  });
}

function normalizeEmail(value: string) {
  return String(value ?? "").trim().toLowerCase();
}

function normalizeFlag(value: unknown, fallback: string) {
  const normalized = String(value ?? "").trim().toLowerCase();
  return normalized || fallback;
}

function parseAllowedPortals(value: unknown) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item ?? "").trim().toLowerCase()).filter(Boolean);
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

function resolveNewSessionExpiration(remember: boolean, now: Date) {
  const hours = remember ? REVIEWER_SESSION_REMEMBER_DAYS * 24 : REVIEWER_SESSION_TTL_HOURS;
  return new Date(now.getTime() + hours * 60 * 60 * 1000);
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
  if (!REVIEWER_SESSION_RENEWAL_ENABLED) {
    return currentExpiration;
  }

  const renewalWindow = REVIEWER_SESSION_RENEWAL_WINDOW_MINUTES * 60 * 1000;
  if (currentExpiration.getTime() - now.getTime() > renewalWindow) {
    return currentExpiration;
  }

  return resolveNewSessionExpiration(remember, now);
}

function getRequestIp(request: Request) {
  return String(request.headers.get("x-forwarded-for") ?? "").split(",")[0]?.trim() || null;
}

function getRequestUserAgent(request: Request) {
  return String(request.headers.get("user-agent") ?? "").trim() || null;
}

function getRequestDeviceId(request: Request, ip: string | null, userAgent: string | null) {
  const base = [
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
  cookies.set(cookieName, token, {
    httpOnly: true,
    path: "/",
    sameSite: "lax",
    secure: options.secure,
    maxAge: (options.remember ? REVIEWER_SESSION_REMEMBER_DAYS * 24 : REVIEWER_SESSION_TTL_HOURS) * 60 * 60,
  });
}

async function invalidateSessionToken(token: string) {
  await prisma.sessoes_ativas.deleteMany({
    where: { token },
  });
}
