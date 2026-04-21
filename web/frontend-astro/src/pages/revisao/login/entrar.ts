import type { APIRoute } from "astro";

import {
  applyReviewerPasswordResetCookie,
  applyReviewerSessionCookie,
  attemptReviewerPasswordLogin,
  safeReviewerNextPath,
} from "@/lib/server/reviewer-auth";

export const POST: APIRoute = async (context) => {
  const formData = await context.request.formData();
  const nextPath = safeReviewerNextPath(formData.get("next")?.toString(), "/revisao/painel");
  const loginPath = new URL("/revisao/login", context.url);

  loginPath.searchParams.set("next", nextPath);

  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  if (email) {
    loginPath.searchParams.set("email", email);
  }

  if (String(formData.get("primeiro_acesso") ?? "").trim() === "1") {
    loginPath.searchParams.set("primeiro_acesso", "1");
  }

  const result = await attemptReviewerPasswordLogin({
    email,
    password: String(formData.get("senha") ?? ""),
    remember: String(formData.get("lembrar") ?? "").trim().toLowerCase() === "1",
    request: context.request,
  });

  if (result.passwordReset) {
    applyReviewerPasswordResetCookie(context.cookies, result.passwordReset.session.token, {
      remember: result.passwordReset.session.remember,
      secure: context.url.protocol === "https:",
    });
    return context.redirect("/revisao/trocar-senha", 303);
  }

  if (!result.ok || !result.session) {
    loginPath.searchParams.set(
      "erro",
      result.error ?? "Nao foi possivel iniciar a sessao do portal revisor.",
    );
    return context.redirect(loginPath.toString(), 303);
  }

  applyReviewerSessionCookie(context.cookies, result.session.session.token, {
    remember: result.session.session.remember,
    secure: context.url.protocol === "https:",
  });

  return context.redirect(nextPath, 303);
};
