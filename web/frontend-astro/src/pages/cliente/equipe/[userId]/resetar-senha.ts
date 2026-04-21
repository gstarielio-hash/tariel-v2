import type { APIRoute } from "astro";

import {
  getClientErrorMessage,
  getClientReturnPath,
  redirectWithClientNotice,
  requireClientSession,
} from "@/lib/server/client-action-route";
import { resetClientOperationalUserPassword } from "@/lib/server/client-portal";

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
    const result = await resetClientOperationalUserPassword(
      clientSession.user.companyId,
      userId,
      clientSession.user.id,
    );

    return redirectWithClientNotice(context, returnTo, {
      tone: "success",
      title: "Senha temporaria regenerada",
      message: `${result.userName} recebeu uma nova credencial temporaria no portal cliente.`,
      details: [
        `Empresa: ${result.companyName}`,
        `Login inicial via ${result.loginUrl}`,
      ],
      credentials: [
        {
          label: result.userName,
          portal: result.portalLabel,
          email: result.email,
          password: result.password,
          notes: [
            `Acesse por ${result.loginUrl}.`,
            "O proximo login exigira troca obrigatoria de senha.",
          ],
        },
      ],
    });
  } catch (error) {
    return redirectWithClientNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao resetar senha",
      message: getClientErrorMessage(
        error,
        "Nao foi possivel emitir uma nova senha temporaria para esta conta.",
      ),
    });
  }
};
