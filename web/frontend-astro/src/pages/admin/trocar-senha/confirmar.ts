import type { APIRoute } from "astro";

import {
  completeAdminPasswordChange,
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
    const result = await completeAdminPasswordChange({
      adminSession,
      currentPassword: String(formData.get("senha_atual") ?? ""),
      nextPassword: String(formData.get("nova_senha") ?? ""),
      confirmPassword: String(formData.get("confirmar_senha") ?? ""),
    });

    if (result.redirectPath) {
      return redirectWithAdminNotice(context, result.redirectPath, {
        tone: "info",
        title: "Senha atualizada",
        message: result.notice,
      });
    }

    return redirectWithAdminNotice(context, consumeAdminNextPathCookie(context.cookies), {
      tone: "success",
      title: "Senha definitiva salva",
      message: result.notice,
    });
  } catch (error) {
    return redirectWithAdminNotice(context, "/admin/trocar-senha", {
      tone: "error",
      title: "Falha ao atualizar senha",
      message: getAdminErrorMessage(
        error,
        "Nao foi possivel concluir a troca obrigatoria de senha.",
      ),
    });
  }
};
