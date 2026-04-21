import type { APIRoute } from "astro";

import {
  getReviewerErrorMessage,
  getReviewerReturnPath,
  redirectWithReviewerNotice,
  requireReviewerSession,
} from "@/lib/server/reviewer-action-route";
import { replyReviewerMesaCase } from "@/lib/server/reviewer-mesa";

function resolveLaudoId(value: string | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export const POST: APIRoute = async (context) => {
  const reviewerSession = requireReviewerSession(context);
  const laudoId = resolveLaudoId(context.params.laudoId);
  const fallbackReturnTo = laudoId ? `/revisao/painel?laudo=${laudoId}` : "/revisao/painel";
  const formData = await context.request.formData();
  const returnTo = getReviewerReturnPath(formData, fallbackReturnTo);

  if (!laudoId) {
    return redirectWithReviewerNotice(context, "/revisao/painel", {
      tone: "error",
      title: "Laudo invalido",
      message: "Nao foi possivel identificar o laudo da mesa para responder.",
    });
  }

  try {
    const rawFile = formData.get("arquivo");
    const file = rawFile instanceof File && rawFile.size > 0 ? rawFile : null;
    const text = String(formData.get("texto") ?? "");
    const referenceMessageId = Number(formData.get("referenciaMensagemId") ?? 0) || null;

    await replyReviewerMesaCase(reviewerSession, {
      laudoId,
      text,
      referenceMessageId,
      file,
    });

    return redirectWithReviewerNotice(context, returnTo, {
      tone: "success",
      title: file ? "Resposta com anexo enviada" : "Resposta enviada",
      message: file
        ? "A mesa recebeu a resposta com o anexo informado."
        : "A resposta operacional foi registrada na thread da revisao.",
      details: [
        `Laudo: ${laudoId}`,
        file ? `Arquivo: ${file.name}` : "A trilha auditavel foi atualizada no backend Python.",
      ],
    });
  } catch (error) {
    return redirectWithReviewerNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao responder a mesa",
      message: getReviewerErrorMessage(
        error,
        "Nao foi possivel enviar a resposta para a thread da mesa avaliadora.",
      ),
    });
  }
};
