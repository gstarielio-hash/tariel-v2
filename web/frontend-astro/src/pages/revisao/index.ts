import type { APIRoute } from "astro";

export const GET: APIRoute = async (context) => {
  if (context.locals.reviewerSession) {
    return context.redirect("/revisao/painel", 303);
  }

  if (context.locals.reviewerPasswordResetSession) {
    return context.redirect("/revisao/trocar-senha", 303);
  }

  return context.redirect("/revisao/login", 303);
};
