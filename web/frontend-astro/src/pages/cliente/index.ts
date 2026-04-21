import type { APIRoute } from "astro";

export const GET: APIRoute = async (context) => {
  if (context.locals.clientSession) {
    return context.redirect("/cliente/painel", 303);
  }

  if (context.locals.clientPasswordResetSession) {
    return context.redirect("/cliente/trocar-senha", 303);
  }

  return context.redirect("/cliente/login", 303);
};
