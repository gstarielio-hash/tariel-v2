import type { APIRoute } from "astro";

import {
  getClientErrorMessage,
  getClientReturnPath,
  redirectWithClientNotice,
  requireClientSession,
} from "@/lib/server/client-action-route";
import { reviewClientMesaCaseDecision } from "@/lib/server/client-mesa";

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
      message: "Não foi possível identificar o laudo da mesa para avaliação.",
    });
  }

  const action = String(formData.get("acao") ?? "").trim().toLowerCase() === "rejeitar" ? "rejeitar" : "aprovar";
  const reason = String(formData.get("motivo") ?? "");

  try {
    const result = await reviewClientMesaCaseDecision(clientSession, {
      laudoId,
      action,
      reason,
    });

    return redirectWithClientNotice(context, returnTo, {
      tone: "success",
      title: action === "aprovar" ? "Laudo aprovado" : "Laudo devolvido",
      message:
        action === "aprovar"
          ? "A decisão da mesa foi registrada pelo portal cliente no boundary Python."
          : "O laudo foi devolvido para correção com justificativa auditável.",
      details: [
        `Estado visual: ${result.status_visual_label}`,
        result.motivo ? `Motivo: ${result.motivo}` : "Sem motivo adicional registrado.",
      ],
    });
  } catch (error) {
    return redirectWithClientNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao avaliar laudo",
      message: getClientErrorMessage(
        error,
        "Não foi possível registrar a decisão da mesa para o laudo selecionado.",
      ),
    });
  }
};
