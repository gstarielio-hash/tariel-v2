import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  getAdminReturnPath,
  parsePositiveAdminParam,
  requireAdminStepUp,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { addCompanyAdmin } from "@/lib/server/admin-mutations";

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
    message: "Reautenticação necessária para provisionar um novo admin-cliente.",
  });

  if (adminSession instanceof Response) {
    return adminSession;
  }

  try {
    const companyId = parsePositiveAdminParam(context, "id", "Empresa");
    const result = await addCompanyAdmin(companyId, {
      nome: String(formData.get("nome") ?? ""),
      email: String(formData.get("email") ?? ""),
    }, adminSession.user.id);

    return redirectWithAdminNotice(context, returnTo, {
      tone: "success",
      title: "Admin cliente criado",
      message: `${result.userName} já pode acessar o portal do cliente para ${result.companyName}.`,
      details: ["A senha abaixo é temporária e aparece apenas uma vez."],
      credentials: [
        {
          label: result.label,
          portal: result.portal,
          email: result.email,
          password: result.password,
          notes: ["Forçar troca de senha no primeiro acesso."],
        },
      ],
    });
  } catch (error) {
    return redirectWithAdminNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao criar admin cliente",
      message: getAdminErrorMessage(
        error,
        "Não foi possível provisionar um novo admin cliente.",
      ),
    });
  }
};
