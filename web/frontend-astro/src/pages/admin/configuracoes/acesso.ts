import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  getAdminReturnPath,
  requireAdminStepUp,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { updateAdminAccessSettings } from "@/lib/server/admin-settings-mutations";

export const POST: APIRoute = async (context) => {
  const formData = await context.request.formData();
  const returnTo = getAdminReturnPath(
    formData,
    "/admin/configuracoes?secao=access#secao-access",
  );
  const adminSession = await requireAdminStepUp(context, {
    returnTo,
    message: "Reautenticação necessária para alterar a política de acesso do Admin-CEO.",
  });

  if (adminSession instanceof Response) {
    return adminSession;
  }

  try {
    const result = await updateAdminAccessSettings({
      adminReauthMaxAgeMinutes: String(
        formData.get("admin_reauth_max_age_minutes") ?? "",
      ),
      reason: String(formData.get("motivo_alteracao") ?? ""),
      actorUserId: adminSession.user.id,
    });

    const currentValue = result.changes.find(
      (change) => change.key === "admin_reauth_max_age_minutes",
    )?.after;

    return redirectWithAdminNotice(context, returnTo, {
      tone: "success",
      title: "Politica de acesso atualizada",
      message: "A janela de reautenticacao do Admin-CEO foi salva no painel Astro.",
      details: [
        `Janela efetiva: ${currentValue ?? "n/d"} min`,
        `Motivo registrado: ${result.reason}`,
        `Auditoria vinculada a ${adminSession.user.name}.`,
        "Step-up administrativo validado na sessão atual.",
      ],
    });
  } catch (error) {
    return redirectWithAdminNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao atualizar acesso",
      message: getAdminErrorMessage(
        error,
        "Nao foi possivel atualizar a politica de acesso da plataforma.",
      ),
    });
  }
};
