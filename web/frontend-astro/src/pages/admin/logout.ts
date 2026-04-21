import type { APIRoute } from "astro";

import { destroyAdminSession, readAdminSessionToken } from "@/lib/server/admin-auth";

export const POST: APIRoute = async (context) => {
  await destroyAdminSession(context, readAdminSessionToken(context.cookies));

  const loginUrl = new URL("/admin/login", context.url);
  loginUrl.searchParams.set("sucesso", "Sessao administrativa encerrada.");

  return context.redirect(loginUrl.toString(), 303);
};
