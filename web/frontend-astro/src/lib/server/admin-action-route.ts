import type { APIContext } from "astro";

import {
  adminSessionNeedsStepUp,
  type AuthenticatedAdminRequest,
} from "@/lib/server/admin-auth";
import {
  safeAdminReturnPath,
  setAdminNotice,
  type AdminNotice,
} from "@/lib/server/admin-notice";

export function parsePositiveAdminParam(
  context: APIContext,
  key: string,
  label: string,
) {
  const value = Number(context.params[key] ?? "");

  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`${label} inválido.`);
  }

  return value;
}

export function getAdminReturnPath(
  formData: FormData,
  fallback: string,
  field = "returnTo",
) {
  return safeAdminReturnPath(formData.get(field), fallback);
}

export function getAdminErrorMessage(
  error: unknown,
  fallback = "Falha ao processar a operação.",
) {
  return error instanceof Error && error.message.trim() ? error.message : fallback;
}

export function requireAdminSession(context: APIContext): AuthenticatedAdminRequest {
  const adminSession = context.locals.adminSession;

  if (!adminSession) {
    throw new Error("Sessão administrativa inválida.");
  }

  return adminSession;
}

export async function requireAdminStepUp(
  context: APIContext,
  input: {
    returnTo: string;
    message: string;
  },
) {
  const adminSession = requireAdminSession(context);
  const needsStepUp = await adminSessionNeedsStepUp(adminSession);

  if (!needsStepUp) {
    return adminSession;
  }

  setAdminNotice(context.cookies, {
    tone: "error",
    title: "Reautenticação necessária",
    message: input.message,
    details: ["Confirme o código TOTP para liberar a próxima ação crítica."],
  });

  const reauthUrl = new URL("/admin/reauth", context.url);
  reauthUrl.searchParams.set("returnTo", safeAdminReturnPath(input.returnTo, "/admin/painel"));

  return context.redirect(reauthUrl.toString(), 303);
}

export function redirectWithAdminNotice(
  context: APIContext,
  returnTo: string,
  notice: AdminNotice,
) {
  setAdminNotice(context.cookies, notice);
  return context.redirect(returnTo, 303);
}
