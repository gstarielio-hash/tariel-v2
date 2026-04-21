import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  getAdminReturnPath,
  parsePositiveAdminParam,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { toggleCompanyUserStatus } from "@/lib/server/admin-mutations";

export const POST: APIRoute = async (context) => {
  const formData = await context.request.formData();
  const companyIdFromParams = Number(context.params.id ?? "");
  const defaultReturnTo =
    Number.isInteger(companyIdFromParams) && companyIdFromParams > 0
      ? `/admin/clientes/${companyIdFromParams}`
      : "/admin/clientes";
  const returnTo = getAdminReturnPath(formData, defaultReturnTo);

  try {
    const companyId = parsePositiveAdminParam(context, "id", "Empresa");
    const userId = parsePositiveAdminParam(context, "usuarioId", "Usuário");
    const result = await toggleCompanyUserStatus(companyId, userId);

    return redirectWithAdminNotice(context, returnTo, {
      tone: "success",
      title: result.active ? "Usuário reativado" : "Usuário bloqueado",
      message: result.active
        ? `${result.userName} foi reativado em ${result.companyName}.`
        : `${result.userName} foi bloqueado em ${result.companyName}.`,
      details: ["As sessões ativas do usuário foram encerradas."],
    });
  } catch (error) {
    return redirectWithAdminNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao atualizar usuário",
      message: getAdminErrorMessage(
        error,
        "Não foi possível alterar o status do usuário.",
      ),
    });
  }
};
