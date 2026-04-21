import type { APIRoute } from "astro";

import {
  getReviewerErrorMessage,
  getReviewerReturnPath,
  redirectWithReviewerNotice,
  requireReviewerSession,
} from "@/lib/server/reviewer-action-route";
import { syncReviewerMesaWhispersRead } from "@/lib/server/reviewer-mesa";

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
      message: "Nao foi possivel identificar o laudo para sincronizar os whispers.",
    });
  }

  try {
    const result = await syncReviewerMesaWhispersRead(reviewerSession, laudoId);

    return redirectWithReviewerNotice(context, returnTo, {
      tone: "success",
      title: "Whispers sincronizados",
      message: "Os whispers pendentes foram marcados como lidos para este laudo.",
      details: [`Itens atualizados: ${result.marcadas}`],
    });
  } catch (error) {
    return redirectWithReviewerNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao sincronizar whispers",
      message: getReviewerErrorMessage(
        error,
        "Nao foi possivel marcar os whispers como lidos neste momento.",
      ),
    });
  }
};
