import type { APIContext } from "astro";

import type { AuthenticatedClientRequest } from "@/lib/server/client-auth";
import { safeClientNextPath } from "@/lib/server/client-auth";
import {
  setClientNotice,
  type ClientNotice,
} from "@/lib/server/client-notice";

export function getClientErrorMessage(
  error: unknown,
  fallback = "Falha ao processar a operação.",
) {
  return error instanceof Error && error.message.trim() ? error.message : fallback;
}

export function requireClientSession(context: APIContext): AuthenticatedClientRequest {
  const clientSession = context.locals.clientSession;

  if (!clientSession) {
    throw new Error("Sessão do portal cliente inválida.");
  }

  return clientSession;
}

export function getClientReturnPath(
  formData: FormData,
  fallback: string,
  field = "returnTo",
) {
  return safeClientNextPath(formData.get(field)?.toString(), fallback);
}

export function redirectWithClientNotice(
  context: APIContext,
  returnTo: string,
  notice: ClientNotice,
) {
  setClientNotice(context.cookies, notice);
  return context.redirect(returnTo, 303);
}
