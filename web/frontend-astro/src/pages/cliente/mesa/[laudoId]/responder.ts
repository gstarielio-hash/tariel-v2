import type { APIRoute } from "astro";

import {
  getClientErrorMessage,
  getClientReturnPath,
  redirectWithClientNotice,
  requireClientSession,
} from "@/lib/server/client-action-route";
import { replyClientMesaCase } from "@/lib/server/client-mesa";

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
      message: "Não foi possível identificar o laudo da mesa para responder.",
    });
  }

  try {
    const rawFile = formData.get("arquivo");
    const file = rawFile instanceof File && rawFile.size > 0 ? rawFile : null;
    const text = String(formData.get("texto") ?? "");
    const referenceMessageId = Number(formData.get("referenciaMensagemId") ?? 0) || null;

    await replyClientMesaCase(clientSession, {
      laudoId,
      text,
      referenceMessageId,
      file,
    });

    return redirectWithClientNotice(context, returnTo, {
      tone: "success",
      title: file ? "Resposta com anexo enviada" : "Resposta enviada",
      message: file
        ? "A mesa recebeu a resposta do tenant com o anexo informado."
        : "A resposta operacional foi registrada na thread da mesa.",
      details: [
        `Laudo: ${laudoId}`,
        file ? `Arquivo: ${file.name}` : "A trilha auditável foi atualizada no backend Python.",
      ],
    });
  } catch (error) {
    return redirectWithClientNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao responder a mesa",
      message: getClientErrorMessage(
        error,
        "Não foi possível enviar a resposta para a mesa avaliadora.",
      ),
    });
  }
};
