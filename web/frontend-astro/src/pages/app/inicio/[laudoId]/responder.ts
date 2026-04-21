import type { APIRoute } from "astro";

import {
  getAppErrorMessage,
  getAppReturnPath,
  redirectWithAppNotice,
  requireAppSession,
} from "@/lib/server/app-action-route";
import { replyToAppMesa } from "@/lib/server/app-mesa-bridge";

function resolveLaudoId(value: string | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export const POST: APIRoute = async (context) => {
  const appSession = requireAppSession(context);
  const laudoId = resolveLaudoId(context.params.laudoId);
  const fallbackReturnTo = laudoId ? `/app/inicio?laudo=${laudoId}` : "/app/inicio";
  const formData = await context.request.formData();
  const returnTo = getAppReturnPath(formData, fallbackReturnTo);

  if (!laudoId) {
    return redirectWithAppNotice(context, "/app/inicio", {
      tone: "error",
      title: "Laudo invalido",
      message: "Nao foi possivel identificar o laudo para responder a mesa.",
    });
  }

  try {
    const text = String(formData.get("texto") ?? "");
    const referenceMessageId = Number(formData.get("referenciaMensagemId") ?? 0) || null;

    await replyToAppMesa(appSession, {
      laudoId,
      texto: text,
      referenciaMensagemId: referenceMessageId,
    });

    return redirectWithAppNotice(context, returnTo, {
      tone: "success",
      title: "Resposta enviada",
      message: "A resposta operacional foi registrada na thread da mesa.",
      details: [
        `Laudo: ${laudoId}`,
        "A trilha auditavel foi atualizada no backend Python.",
      ],
    });
  } catch (error) {
    return redirectWithAppNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao responder a mesa",
      message: getAppErrorMessage(
        error,
        "Nao foi possivel enviar a resposta para a thread da mesa.",
      ),
    });
  }
};
