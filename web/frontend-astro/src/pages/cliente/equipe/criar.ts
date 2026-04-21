import type { APIRoute } from "astro";

import {
  getClientErrorMessage,
  getClientReturnPath,
  redirectWithClientNotice,
  requireClientSession,
} from "@/lib/server/client-action-route";
import { createClientOperationalUser } from "@/lib/server/client-portal";

export const POST: APIRoute = async (context) => {
  const clientSession = requireClientSession(context);
  const formData = await context.request.formData();
  const returnTo = getClientReturnPath(formData, "/cliente/equipe");

  try {
    const result = await createClientOperationalUser({
      companyId: clientSession.user.companyId,
      actorUserId: clientSession.user.id,
      role: String(formData.get("papel") ?? "inspetor") === "revisor" ? "revisor" : "inspetor",
      name: String(formData.get("nome") ?? ""),
      email: String(formData.get("email") ?? ""),
      phone: String(formData.get("telefone") ?? ""),
      crea: String(formData.get("crea") ?? ""),
    });

    return redirectWithClientNotice(context, returnTo, {
      tone: "success",
      title: "Usuario criado",
      message: `${result.userName} foi provisionado com credencial temporaria no portal cliente.`,
      details: [
        `Empresa: ${result.companyName}`,
        `Perfil: ${result.roleLabel}`,
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
            "Compartilhe a senha por canal seguro e exija a troca no primeiro acesso.",
          ],
        },
      ],
    });
  } catch (error) {
    return redirectWithClientNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao criar usuario",
      message: getClientErrorMessage(
        error,
        "Nao foi possivel provisionar o usuario operacional no portal cliente.",
      ),
    });
  }
};
