import type { APIContext } from "astro";

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

export function redirectWithAdminNotice(
  context: APIContext,
  returnTo: string,
  notice: AdminNotice,
) {
  setAdminNotice(context.cookies, notice);
  return context.redirect(returnTo, 303);
}
