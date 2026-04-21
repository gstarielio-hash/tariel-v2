import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  getAdminReturnPath,
  parsePositiveAdminParam,
  requireAdminStepUp,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { resetCompanyUserPassword } from "@/lib/server/admin-mutations";

export const POST: APIRoute = async (context) => {
  const formData = await context.request.formData();
  const companyIdFromParams = Number(context.params.id ?? "");
  const defaultReturnTo =
    Number.isInteger(companyIdFromParams) && companyIdFromParams > 0
      ? `/admin/clientes/${companyIdFromParams}`
      : "/admin/clientes";
  const returnTo = getAdminReturnPath(formData, defaultReturnTo);
  const adminSession = await requireAdminStepUp(context, {
    returnTo,
    message: "Reautenticação necessária para resetar a senha de um usuário da empresa.",
  });

  if (adminSession instanceof Response) {
    return adminSession;
  }

  try {
    const companyId = parsePositiveAdminParam(context, "id", "Empresa");
    const userId = parsePositiveAdminParam(context, "usuarioId", "Usuário");
    const result = await resetCompanyUserPassword(companyId, userId, adminSession.user.id);

    return redirectWithAdminNotice(context, returnTo, {
      tone: "success",
      title: "Senha resetada",
      message: `${result.userName} recebeu uma nova senha temporária em ${result.companyName}.`,
      details: ["As sessões anteriores foram invalidadas automaticamente."],
      credentials: [
        {
          label: result.label,
          portal: result.portal,
          email: result.email,
          password: result.password,
          notes: ["Usuário obrigado a trocar a senha no próximo login."],
        },
      ],
    });
  } catch (error) {
    return redirectWithAdminNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao resetar senha",
      message: getAdminErrorMessage(
        error,
        "Não foi possível resetar a senha do usuário.",
      ),
    });
  }
};
