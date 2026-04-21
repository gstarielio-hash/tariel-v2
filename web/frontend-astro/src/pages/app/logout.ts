import type { APIRoute } from "astro";

import { destroyAppPasswordResetSession, destroyAppSession } from "@/lib/server/app-auth";

export const POST: APIRoute = async (context) => {
  await destroyAppSession(context);
  await destroyAppPasswordResetSession(context);

  const loginUrl = new URL("/app/login", context.url);
  loginUrl.searchParams.set("sucesso", "Sessao do portal do inspetor encerrada.");
  return context.redirect(loginUrl.toString(), 303);
};
