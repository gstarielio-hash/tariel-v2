import type { APIRoute } from "astro";

import {
  getReviewerErrorMessage,
  getReviewerReturnPath,
  redirectWithReviewerNotice,
  requireReviewerSession,
} from "@/lib/server/reviewer-action-route";
import { getReviewerMesaReturnFallback, resolveReviewerMesaInt } from "@/lib/server/reviewer-mesa-route";
import { reviewReviewerMesaCaseDecision } from "@/lib/server/reviewer-mesa";

export const POST: APIRoute = async (context) => {
  const reviewerSession = requireReviewerSession(context);
  const laudoId = resolveReviewerMesaInt(context.params.laudoId);
  const fallbackReturnTo = getReviewerMesaReturnFallback(laudoId);
  const formData = await context.request.formData();
  const returnTo = getReviewerReturnPath(formData, fallbackReturnTo);

  if (!laudoId) {
    return redirectWithReviewerNotice(context, "/revisao/painel", {
      tone: "error",
      title: "Laudo invalido",
      message: "Nao foi possivel identificar o laudo da mesa para avaliacao.",
    });
  }

  const action = String(formData.get("acao") ?? "").trim().toLowerCase() === "rejeitar" ? "rejeitar" : "aprovar";
  const reason = String(formData.get("motivo") ?? "");

  try {
    const result = await reviewReviewerMesaCaseDecision(reviewerSession, {
      laudoId,
      action,
      reason,
    });

    return redirectWithReviewerNotice(context, returnTo, {
      tone: "success",
      title: action === "aprovar" ? "Laudo aprovado" : "Laudo devolvido",
      message:
        action === "aprovar"
          ? "A decisao da mesa foi registrada no boundary Python."
          : "O laudo foi devolvido para correcao com justificativa auditavel.",
      details: [
        `Estado visual: ${result.status_visual_label}`,
        result.motivo ? `Motivo: ${result.motivo}` : "Sem motivo adicional registrado.",
      ],
    });
  } catch (error) {
    return redirectWithReviewerNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao avaliar laudo",
      message: getReviewerErrorMessage(
        error,
        "Nao foi possivel registrar a decisao da mesa para o laudo selecionado.",
      ),
    });
  }
};
