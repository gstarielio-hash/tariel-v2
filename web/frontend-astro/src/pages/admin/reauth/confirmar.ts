import type { APIRoute } from "astro";

import {
  completeAdminReauth,
  safeAdminNextPath,
} from "@/lib/server/admin-auth";
import {
  getAdminErrorMessage,
  requireAdminSession,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";

export const POST: APIRoute = async (context) => {
  const adminSession = requireAdminSession(context);
  const formData = await context.request.formData();
  const returnTo = safeAdminNextPath(formData.get("returnTo")?.toString(), "/admin/painel");

  try {
    const result = await completeAdminReauth({
      adminSession,
      code: String(formData.get("codigo") ?? ""),
    });

    return redirectWithAdminNotice(context, returnTo, {
      tone: "success",
      title: "Reautenticacao concluida",
      message: `A sessao critica foi renovada por ${result.maxAgeMinutes} minuto(s).`,
      details: ["Reenvie a acao na tela de origem para concluir a mutacao."],
    });
  } catch (error) {
    return redirectWithAdminNotice(context, `/admin/reauth?returnTo=${encodeURIComponent(returnTo)}`, {
      tone: "error",
      title: "Falha na reautenticacao",
      message: getAdminErrorMessage(
        error,
        "Nao foi possivel validar o codigo TOTP para a acao critica.",
      ),
    });
  }
};
