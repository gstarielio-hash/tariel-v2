import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  getAdminReturnPath,
  parsePositiveAdminParam,
  requireAdminStepUp,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { syncCompanyCatalogPortfolio } from "@/lib/server/admin-mutations";

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
    message: "Reautenticação necessária para sincronizar o portfólio comercial do tenant.",
  });

  if (adminSession instanceof Response) {
    return adminSession;
  }

  try {
    const companyId = parsePositiveAdminParam(context, "id", "Empresa");
    const selectionTokens = formData
      .getAll("catalog_variant")
      .map((value) => String(value ?? "").trim())
      .filter(Boolean);
    const result = await syncCompanyCatalogPortfolio(companyId, selectionTokens, adminSession.user.id);

    return redirectWithAdminNotice(context, returnTo, {
      tone: "success",
      title: result.selectedCount > 0 ? "Portfólio sincronizado" : "Portfólio limpo",
      message:
        result.selectedCount > 0
          ? `${result.companyName} agora opera com ${result.selectedCount} modelo(s) ativo(s) no catálogo.`
          : result.governedMode
            ? "Portfólio limpo. A empresa permanece governada pelo Admin-CEO, sem modelos liberados."
            : "Portfólio limpo. A empresa voltou ao modo legado, sem catálogo ativo.",
      details: [
        `Ativadas: ${result.activated.length}`,
        `Reativadas: ${result.reactivated.length}`,
        `Desativadas: ${result.deactivated.length}`,
      ],
    });
  } catch (error) {
    return redirectWithAdminNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao sincronizar portfólio",
      message: getAdminErrorMessage(
        error,
        "Não foi possível sincronizar o portfólio comercial de laudos.",
      ),
    });
  }
};
