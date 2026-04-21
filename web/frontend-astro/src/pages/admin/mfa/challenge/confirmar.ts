import type { APIRoute } from "astro";

import {
  completeAdminMfaChallenge,
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
    await completeAdminMfaChallenge({
      adminSession,
      code: String(formData.get("codigo") ?? ""),
    });

    return redirectWithAdminNotice(context, consumeAdminNextPathCookie(context.cookies), {
      tone: "success",
      title: "MFA confirmado",
      message: "O codigo TOTP foi aceito e a sessao administrativa esta liberada.",
    });
  } catch (error) {
    return redirectWithAdminNotice(context, "/admin/mfa/challenge", {
      tone: "error",
      title: "Falha ao confirmar MFA",
      message: getAdminErrorMessage(
        error,
        "Nao foi possivel validar o codigo TOTP.",
      ),
    });
  }
};
