import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  getAdminReturnPath,
  parsePositiveAdminParam,
  requireAdminStepUp,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { toggleCompanyBlockStatus } from "@/lib/server/admin-mutations";

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
    message: "Reautenticação necessária para alterar o bloqueio operacional da empresa.",
  });

  if (adminSession instanceof Response) {
    return adminSession;
  }

  try {
    const companyId = parsePositiveAdminParam(context, "id", "Empresa");
    const result = await toggleCompanyBlockStatus(
      companyId,
      String(formData.get("motivo") ?? ""),
      formData.get("confirmarDesbloqueio") === "1",
      adminSession.user.id,
    );

    return redirectWithAdminNotice(context, returnTo, {
      tone: "success",
      title: result.blocked ? "Empresa bloqueada" : "Empresa desbloqueada",
      message: result.blocked
        ? `${result.companyName} foi bloqueada no painel migrado.`
        : `${result.companyName} voltou a operar na nova stack.`,
      details: result.blocked
        ? [
            `Motivo: ${result.reason ?? "não informado"}`,
            `${result.invalidatedSessions} sessões foram invalidadas.`,
          ]
        : ["O acesso volta a depender apenas das regras normais de autenticação."],
    });
  } catch (error) {
    return redirectWithAdminNotice(context, returnTo, {
      tone: "error",
      title: "Falha no bloqueio",
      message: getAdminErrorMessage(
        error,
        "Não foi possível alterar o status de bloqueio da empresa.",
      ),
    });
  }
};
