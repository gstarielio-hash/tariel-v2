import type { APIRoute } from "astro";

import { destroyClientSession } from "@/lib/server/client-auth";

export const POST: APIRoute = async (context) => {
  await destroyClientSession(context);
  return context.redirect(
    "/cliente/login?sucesso=Sessao%20encerrada%20no%20portal%20cliente.",
    303,
  );
};
