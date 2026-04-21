import type { APIRoute } from "astro";

import {
  getClientErrorMessage,
  getClientReturnPath,
  redirectWithClientNotice,
  requireClientSession,
} from "@/lib/server/client-action-route";
import { registerClientPlanInterest } from "@/lib/server/client-portal";

export const POST: APIRoute = async (context) => {
  const clientSession = requireClientSession(context);
  const formData = await context.request.formData();
  const returnTo = getClientReturnPath(formData, "/cliente/suporte");

  try {
    const result = await registerClientPlanInterest({
      companyId: clientSession.user.companyId,
      actorUserId: clientSession.user.id,
      requestedPlan: String(formData.get("plano") ?? "Inicial") as "Inicial" | "Intermediario" | "Ilimitado",
      origin: String(formData.get("origem") ?? "admin") as "admin" | "chat" | "mesa",
    });

    return redirectWithClientNotice(context, returnTo, {
      tone: "success",
      title: "Interesse comercial registrado",
      message: `A mudanca de ${result.currentPlan} para ${result.requestedPlan} foi registrada para analise.`,
      details: [
        `Movimento identificado: ${result.movement === "upgrade" ? "upgrade" : "downgrade"}.`,
        "Nenhuma troca de plano foi executada automaticamente no tenant.",
      ],
    });
  } catch (error) {
    return redirectWithClientNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao registrar interesse",
      message: getClientErrorMessage(
        error,
        "Nao foi possivel registrar a solicitacao comercial deste tenant.",
      ),
    });
  }
};
