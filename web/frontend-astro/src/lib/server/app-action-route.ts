import type { APIContext } from "astro";

import type { AuthenticatedAppRequest } from "@/lib/server/app-auth";
import { safeAppNextPath } from "@/lib/server/app-auth";
import { setAppNotice, type AppNotice } from "@/lib/server/app-notice";

export function getAppErrorMessage(error: unknown, fallback = "Falha ao processar a operacao.") {
  return error instanceof Error && error.message.trim() ? error.message : fallback;
}

export function requireAppSession(context: APIContext): AuthenticatedAppRequest {
  const appSession = context.locals.appSession;

  if (!appSession) {
    throw new Error("Sessao do portal do inspetor invalida.");
  }

  return appSession;
}

export function getAppReturnPath(formData: FormData, fallback: string, field = "returnTo") {
  return safeAppNextPath(formData.get(field)?.toString(), fallback);
}

export function redirectWithAppNotice(context: APIContext, returnTo: string, notice: AppNotice) {
  setAppNotice(context.cookies, notice);
  return context.redirect(returnTo, 303);
}
