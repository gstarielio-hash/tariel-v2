import type { APIRoute } from "astro";

import {
  getClientErrorMessage,
  getClientReturnPath,
  redirectWithClientNotice,
  requireClientSession,
} from "@/lib/server/client-action-route";
import { createClientSupportReport } from "@/lib/server/client-portal";

export const POST: APIRoute = async (context) => {
  const clientSession = requireClientSession(context);
  const formData = await context.request.formData();
  const returnTo = getClientReturnPath(formData, "/cliente/suporte");

  try {
    const result = await createClientSupportReport({
      companyId: clientSession.user.companyId,
      actorUserId: clientSession.user.id,
      type: String(formData.get("tipo") ?? "feedback") === "bug" ? "bug" : "feedback",
      title: String(formData.get("titulo") ?? ""),
      message: String(formData.get("mensagem") ?? ""),
      replyEmail: String(formData.get("email") ?? ""),
      context: "portal_cliente_v2",
    });

    return redirectWithClientNotice(context, returnTo, {
      tone: "success",
      title: "Protocolo registrado",
      message: `O suporte interno recebeu o protocolo ${result.protocol}.`,
      details: [
        "A trilha auditavel foi registrada no tenant.",
        "Compartilhe o protocolo com a Tariel quando precisar escalar o caso.",
      ],
    });
  } catch (error) {
    return redirectWithClientNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao registrar suporte",
      message: getClientErrorMessage(
        error,
        "Nao foi possivel registrar o protocolo de suporte do tenant.",
      ),
    });
  }
};
