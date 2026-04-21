import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  getAdminReturnPath,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { updateAdminDefaultSettings } from "@/lib/server/admin-settings-mutations";

export const POST: APIRoute = async (context) => {
  const formData = await context.request.formData();
  const returnTo = getAdminReturnPath(
    formData,
    "/admin/configuracoes?secao=defaults#secao-defaults",
  );

  try {
    const result = await updateAdminDefaultSettings({
      defaultNewTenantPlan: String(formData.get("default_new_tenant_plan") ?? ""),
      reason: String(formData.get("motivo_alteracao") ?? ""),
    });

    const currentValue = result.changes.find(
      (change) => change.key === "default_new_tenant_plan",
    )?.after;

    return redirectWithAdminNotice(context, returnTo, {
      tone: "success",
      title: "Defaults atualizados",
      message: "O plano padrao do onboarding foi salvo no painel Astro.",
      details: [
        `Plano inicial efetivo: ${currentValue ?? "n/d"}`,
        `Motivo registrado: ${result.reason}`,
        "Auditoria salva no tenant de plataforma.",
        "Vinculo de ator ainda pendente ate a migracao da autenticacao admin.",
      ],
    });
  } catch (error) {
    return redirectWithAdminNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao atualizar defaults",
      message: getAdminErrorMessage(
        error,
        "Nao foi possivel atualizar os defaults globais da plataforma.",
      ),
    });
  }
};
