import type { APIRoute } from "astro";

import {
  applyAdminSessionCookie,
  attemptAdminPasswordLogin,
  clearAdminNextPathCookie,
  safeAdminNextPath,
  setAdminNextPathCookie,
} from "@/lib/server/admin-auth";

export const POST: APIRoute = async (context) => {
  const formData = await context.request.formData();
  const nextPath = safeAdminNextPath(formData.get("next")?.toString(), "/admin/painel");
  const loginPath = new URL("/admin/login", context.url);

  loginPath.searchParams.set("next", nextPath);

  const result = await attemptAdminPasswordLogin({
    email: String(formData.get("email") ?? ""),
    password: String(formData.get("senha") ?? ""),
    remember: String(formData.get("lembrar") ?? "").trim().toLowerCase() === "1",
    request: context.request,
  });

  if (!result.ok || !result.session) {
    clearAdminNextPathCookie(context.cookies);
    loginPath.searchParams.set(
      "erro",
      result.error ?? "Nao foi possivel iniciar a sessao administrativa.",
    );
    return context.redirect(loginPath.toString(), 303);
  }

  applyAdminSessionCookie(context.cookies, result.session.session.token, {
    remember: result.session.session.remember,
    secure: context.url.protocol === "https:",
  });

  if (result.redirectPath) {
    setAdminNextPathCookie(context.cookies, nextPath);
    return context.redirect(result.redirectPath, 303);
  }

  clearAdminNextPathCookie(context.cookies);
  return context.redirect(nextPath, 303);
};
