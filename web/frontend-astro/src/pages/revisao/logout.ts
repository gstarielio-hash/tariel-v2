import type { APIRoute } from "astro";

import { destroyReviewerSession, readReviewerSessionToken } from "@/lib/server/reviewer-auth";

export const POST: APIRoute = async (context) => {
  await destroyReviewerSession(context, readReviewerSessionToken(context.cookies));

  const loginUrl = new URL("/revisao/login", context.url);
  loginUrl.searchParams.set("sucesso", "Sessao do portal revisor encerrada.");
  return context.redirect(loginUrl.toString(), 303);
};
