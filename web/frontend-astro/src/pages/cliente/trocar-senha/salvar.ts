import type { APIRoute } from "astro";

import {
  applyClientSessionCookie,
  clearClientPasswordResetCookie,
  completeClientPasswordReset,
} from "@/lib/server/client-auth";

export const POST: APIRoute = async (context) => {
  const passwordResetSession = context.locals.clientPasswordResetSession;

  if (!passwordResetSession) {
    return context.redirect(
      "/cliente/login?erro=Fluxo%20de%20troca%20de%20senha%20invalido%20ou%20expirado.",
      303,
    );
  }

  const formData = await context.request.formData();
  const result = await completeClientPasswordReset({
    token: passwordResetSession.session.token,
    currentPassword: String(formData.get("senhaAtual") ?? ""),
    nextPassword: String(formData.get("novaSenha") ?? ""),
    confirmPassword: String(formData.get("confirmarSenha") ?? ""),
    request: context.request,
  });

  if (!result.ok || !result.session) {
    const errorPath = new URL("/cliente/trocar-senha", context.url);
    errorPath.searchParams.set(
      "erro",
      result.error ?? "Nao foi possivel concluir a troca obrigatoria de senha.",
    );
    return context.redirect(errorPath.toString(), 303);
  }

  clearClientPasswordResetCookie(context.cookies);
  applyClientSessionCookie(context.cookies, result.session.session.token, {
    remember: result.session.session.remember,
    secure: context.url.protocol === "https:",
  });

  return context.redirect("/cliente/painel?sucesso=Senha%20atualizada%20com%20sucesso.", 303);
};
