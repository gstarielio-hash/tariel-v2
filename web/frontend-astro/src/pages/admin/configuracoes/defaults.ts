import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  getAdminReturnPath,
  requireAdminSession,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { updateAdminDefaultSettings } from "@/lib/server/admin-settings-mutations";

export const POST: APIRoute = async (context) => {
  const formData = await context.request.formData();
  const returnTo = getAdminReturnPath(
    formData,
    "/admin/configuracoes?secao=defaults#secao-defaults",
  );
  const adminSession = requireAdminSession(context);

  try {
    const result = await updateAdminDefaultSettings({
      defaultNewTenantPlan: String(formData.get("default_new_tenant_plan") ?? ""),
      reason: String(formData.get("motivo_alteracao") ?? ""),
      actorUserId: adminSession.user.id,
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
        `Auditoria vinculada a ${adminSession.user.name}.`,
        "Step-up administrativo ainda entra na proxima fatia.",
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
