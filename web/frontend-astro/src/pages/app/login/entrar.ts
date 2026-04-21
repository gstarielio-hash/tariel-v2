import type { APIRoute } from "astro";

import {
  applyAppPasswordResetCookie,
  applyAppSessionCookie,
  attemptAppPasswordLogin,
  safeAppNextPath,
} from "@/lib/server/app-auth";

export const POST: APIRoute = async (context) => {
  const formData = await context.request.formData();
  const nextPath = safeAppNextPath(formData.get("next")?.toString(), "/app/inicio");
  const loginPath = new URL("/app/login", context.url);

  loginPath.searchParams.set("next", nextPath);

  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  if (email) {
    loginPath.searchParams.set("email", email);
  }

  if (String(formData.get("primeiro_acesso") ?? "").trim() === "1") {
    loginPath.searchParams.set("primeiro_acesso", "1");
  }

  const result = await attemptAppPasswordLogin({
    email,
    password: String(formData.get("senha") ?? ""),
    remember: String(formData.get("lembrar") ?? "").trim().toLowerCase() === "1",
    request: context.request,
  });

  if (result.passwordReset) {
    applyAppPasswordResetCookie(context.cookies, result.passwordReset.session.token, {
      remember: result.passwordReset.session.remember,
      secure: context.url.protocol === "https:",
    });
    return context.redirect("/app/trocar-senha", 303);
  }

  if (!result.ok || !result.session) {
    loginPath.searchParams.set(
      "erro",
      result.error ?? "Nao foi possivel iniciar a sessao do portal do inspetor.",
    );
    return context.redirect(loginPath.toString(), 303);
  }

  applyAppSessionCookie(context.cookies, result.session.session.token, {
    remember: result.session.session.remember,
    secure: context.url.protocol === "https:",
  });

  return context.redirect(nextPath, 303);
};
