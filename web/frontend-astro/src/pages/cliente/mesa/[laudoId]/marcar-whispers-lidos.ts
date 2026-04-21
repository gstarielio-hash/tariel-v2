import type { APIRoute } from "astro";

import {
  getClientErrorMessage,
  getClientReturnPath,
  redirectWithClientNotice,
  requireClientSession,
} from "@/lib/server/client-action-route";
import { syncClientMesaWhispersRead } from "@/lib/server/client-mesa";

function resolveLaudoId(value: string | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export const POST: APIRoute = async (context) => {
  const clientSession = requireClientSession(context);
  const laudoId = resolveLaudoId(context.params.laudoId);
  const fallbackReturnTo = laudoId ? `/cliente/mesa?sec=reply&laudo=${laudoId}` : "/cliente/mesa?sec=reply";
  const formData = await context.request.formData();
  const returnTo = getClientReturnPath(formData, fallbackReturnTo);

  if (!laudoId) {
    return redirectWithClientNotice(context, "/cliente/mesa?sec=reply", {
      tone: "error",
      title: "Laudo inválido",
      message: "Não foi possível identificar o laudo para sincronizar os whispers.",
    });
  }

  try {
    const result = await syncClientMesaWhispersRead(clientSession, laudoId);

    return redirectWithClientNotice(context, returnTo, {
      tone: "success",
      title: "Whispers sincronizados",
      message: "Os whispers pendentes foram marcados como lidos para este laudo.",
      details: [`Itens atualizados: ${result.marcadas}`],
    });
  } catch (error) {
    return redirectWithClientNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao sincronizar whispers",
      message: getClientErrorMessage(
        error,
        "Não foi possível marcar os whispers como lidos neste momento.",
      ),
    });
  }
};
