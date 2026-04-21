import type { APIRoute } from "astro";

import {
  getClientErrorMessage,
  getClientReturnPath,
  redirectWithClientNotice,
  requireClientSession,
} from "@/lib/server/client-action-route";
import { toggleClientOperationalUserStatus } from "@/lib/server/client-portal";

export const POST: APIRoute = async (context) => {
  const clientSession = requireClientSession(context);
  const userId = Number(context.params.userId ?? "");

  if (!Number.isInteger(userId) || userId <= 0) {
    return redirectWithClientNotice(context, "/cliente/equipe", {
      tone: "error",
      title: "Usuario invalido",
      message: "Nao foi possivel identificar a conta operacional selecionada.",
    });
  }

  const formData = await context.request.formData();
  const returnTo = getClientReturnPath(formData, "/cliente/equipe");

  try {
    const result = await toggleClientOperationalUserStatus(
      clientSession.user.companyId,
      userId,
      clientSession.user.id,
    );

    return redirectWithClientNotice(context, returnTo, {
      tone: "success",
      title: result.active ? "Conta reativada" : "Conta bloqueada",
      message: `${result.userName} foi ${result.active ? "reativado" : "bloqueado"} no portal cliente.`,
      details: [`Empresa: ${result.companyName}`],
    });
  } catch (error) {
    return redirectWithClientNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao alterar bloqueio",
      message: getClientErrorMessage(
        error,
        "Nao foi possivel alterar o status da conta operacional.",
      ),
    });
  }
};
