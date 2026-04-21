import type { APIRoute } from "astro";

import {
  getAppErrorMessage,
  getAppReturnPath,
  redirectWithAppNotice,
  requireAppSession,
} from "@/lib/server/app-action-route";
import { replyToAppMesa, replyToAppMesaWithAttachment } from "@/lib/server/app-mesa-bridge";

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
    const rawFile = formData.get("arquivo");
    const file = rawFile instanceof File && rawFile.size > 0 ? rawFile : null;
    const text = String(formData.get("texto") ?? "");
    const referenceMessageId = Number(formData.get("referenciaMensagemId") ?? 0) || null;
    const normalizedText = text.trim();

    if (!normalizedText && !file) {
      throw new Error("Escreva uma resposta ou selecione um anexo.");
    }

    if (file) {
      await replyToAppMesaWithAttachment(appSession, {
        laudoId,
        arquivo: file,
        texto: normalizedText,
        referenciaMensagemId: referenceMessageId,
      });
    } else {
      await replyToAppMesa(appSession, {
        laudoId,
        texto: normalizedText,
        referenciaMensagemId: referenceMessageId,
      });
    }

    return redirectWithAppNotice(context, returnTo, {
      tone: "success",
      title: file ? "Resposta com anexo enviada" : "Resposta enviada",
      message: file
        ? "A mesa recebeu a resposta operacional com o anexo informado."
        : "A resposta operacional foi registrada na thread da mesa.",
      details: [
        `Laudo: ${laudoId}`,
        file ? `Arquivo: ${file.name}` : "A trilha auditavel foi atualizada no backend Python.",
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
