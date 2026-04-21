import type { APIRoute } from "astro";

import {
  completeAdminMfaSetup,
  consumeAdminNextPathCookie,
} from "@/lib/server/admin-auth";
import {
  getAdminErrorMessage,
  requireAdminSession,
  redirectWithAdminNotice,
} from "@/lib/server/admin-action-route";

export const POST: APIRoute = async (context) => {
  const adminSession = requireAdminSession(context);
  const formData = await context.request.formData();

  try {
    await completeAdminMfaSetup({
      adminSession,
      code: String(formData.get("codigo") ?? ""),
    });

    return redirectWithAdminNotice(context, consumeAdminNextPathCookie(context.cookies), {
      tone: "success",
      title: "MFA configurado",
      message: "O TOTP foi cadastrado e a sessao administrativa agora esta liberada.",
    });
  } catch (error) {
    return redirectWithAdminNotice(context, "/admin/mfa/setup", {
      tone: "error",
      title: "Falha ao configurar MFA",
      message: getAdminErrorMessage(
        error,
        "Nao foi possivel concluir o cadastro do TOTP.",
      ),
    });
  }
};
