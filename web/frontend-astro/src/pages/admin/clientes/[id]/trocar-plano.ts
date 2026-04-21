import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  getAdminReturnPath,
  parsePositiveAdminParam,
  requireAdminStepUp,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { changeCompanyPlan } from "@/lib/server/admin-mutations";

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
    message: "Reautenticação necessária para alterar o plano comercial da empresa.",
  });

  if (adminSession instanceof Response) {
    return adminSession;
  }

  try {
    const companyId = parsePositiveAdminParam(context, "id", "Empresa");
    const result = await changeCompanyPlan(
      companyId,
      String(formData.get("plano") ?? ""),
      adminSession.user.id,
    );

    return redirectWithAdminNotice(context, returnTo, {
      tone: "success",
      title: "Plano atualizado",
      message: `${result.companyName} agora está no plano ${result.nextPlan}.`,
      details: [
        `Plano anterior: ${result.previousPlan}`,
        `Plano atual: ${result.nextPlan}`,
        ...result.alerts,
      ],
    });
  } catch (error) {
    return redirectWithAdminNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao trocar plano",
      message: getAdminErrorMessage(
        error,
        "Não foi possível atualizar o plano da empresa.",
      ),
    });
  }
};
