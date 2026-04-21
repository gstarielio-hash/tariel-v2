import type { APIRoute } from "astro";

import {
  getAdminErrorMessage,
  getAdminReturnPath,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";
import { updateAdminAccessSettings } from "@/lib/server/admin-settings-mutations";

export const POST: APIRoute = async (context) => {
  const formData = await context.request.formData();
  const returnTo = getAdminReturnPath(
    formData,
    "/admin/configuracoes?secao=access#secao-access",
  );

  try {
    const result = await updateAdminAccessSettings({
      adminReauthMaxAgeMinutes: String(
        formData.get("admin_reauth_max_age_minutes") ?? "",
      ),
      reason: String(formData.get("motivo_alteracao") ?? ""),
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
        "Auditoria salva no tenant de plataforma.",
        "Vinculo de ator ainda pendente ate a migracao da autenticacao admin.",
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
