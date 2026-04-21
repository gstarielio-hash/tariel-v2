import type { APIRoute } from "astro";

import {
  applyAppSessionCookie,
  clearAppPasswordResetCookie,
  completeAppPasswordReset,
  readAppPasswordResetToken,
} from "@/lib/server/app-auth";

export const POST: APIRoute = async (context) => {
  const token = readAppPasswordResetToken(context.cookies);
  const formData = await context.request.formData();

  const result = await completeAppPasswordReset({
    token: token ?? "",
    currentPassword: String(formData.get("senhaAtual") ?? ""),
    nextPassword: String(formData.get("novaSenha") ?? ""),
    confirmPassword: String(formData.get("confirmarSenha") ?? ""),
    request: context.request,
  });

  if (!result.ok || !result.session) {
    const target = new URL("/app/trocar-senha", context.url);
    target.searchParams.set(
      "erro",
      result.error ?? "Nao foi possivel concluir a troca obrigatoria de senha do inspetor.",
    );
    return context.redirect(target.toString(), 303);
  }

  clearAppPasswordResetCookie(context.cookies);
  applyAppSessionCookie(context.cookies, result.session.session.token, {
    remember: result.session.session.remember,
    secure: context.url.protocol === "https:",
  });

  const target = new URL("/app/inicio", context.url);
  target.searchParams.set("sucesso", "Primeiro acesso concluido. Sessao oficial do inspetor ativa.");
  return context.redirect(target.toString(), 303);
};
