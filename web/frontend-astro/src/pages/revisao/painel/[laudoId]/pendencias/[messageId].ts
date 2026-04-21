import type { APIRoute } from "astro";

import {
  getReviewerErrorMessage,
  getReviewerReturnPath,
  redirectWithReviewerNotice,
  requireReviewerSession,
} from "@/lib/server/reviewer-action-route";
import { toggleReviewerMesaPendency } from "@/lib/server/reviewer-mesa";

function resolvePositiveInt(value: string | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function resolveBoolean(value: FormDataEntryValue | null) {
  const normalized = String(value ?? "").trim().toLowerCase();
  return normalized === "true" || normalized === "1" || normalized === "sim";
}

export const POST: APIRoute = async (context) => {
  const reviewerSession = requireReviewerSession(context);
  const laudoId = resolvePositiveInt(context.params.laudoId);
  const messageId = resolvePositiveInt(context.params.messageId);
  const fallbackReturnTo = laudoId ? `/revisao/painel?laudo=${laudoId}` : "/revisao/painel";
  const formData = await context.request.formData();
  const returnTo = getReviewerReturnPath(formData, fallbackReturnTo);

  if (!laudoId || !messageId) {
    return redirectWithReviewerNotice(context, "/revisao/painel", {
      tone: "error",
      title: "Pendencia invalida",
      message: "Nao foi possivel identificar a pendencia da mesa que seria atualizada.",
    });
  }

  const resolved = resolveBoolean(formData.get("lida"));

  try {
    await toggleReviewerMesaPendency(reviewerSession, {
      laudoId,
      mensagemId: messageId,
      resolved,
    });

    return redirectWithReviewerNotice(context, returnTo, {
      tone: "success",
      title: resolved ? "Pendencia resolvida" : "Pendencia reaberta",
      message: resolved
        ? "A pendencia foi marcada como resolvida no contrato governado da mesa."
        : "A pendencia voltou para a fila ativa da mesa.",
      details: [`Laudo: ${laudoId}`, `Mensagem: ${messageId}`],
    });
  } catch (error) {
    return redirectWithReviewerNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao atualizar pendencia",
      message: getReviewerErrorMessage(
        error,
        "Nao foi possivel atualizar o estado da pendencia na mesa.",
      ),
    });
  }
};
