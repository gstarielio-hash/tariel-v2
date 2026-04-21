import type { APIRoute } from "astro";

export const GET: APIRoute = async (context) => {
  if (context.locals.appSession) {
    return context.redirect("/app/inicio", 303);
  }

  if (context.locals.appPasswordResetSession) {
    return context.redirect("/app/trocar-senha", 303);
  }

  return context.redirect("/app/login", 303);
};
