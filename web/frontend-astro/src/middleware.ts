import { defineMiddleware } from "astro:middleware";

import {
  buildAdminLoginPath,
  getAdminRequiredTransitionPath,
  isAdminLogoutPath,
  isAdminMfaChallengePath,
  isAdminMfaSetupPath,
  isAdminPath,
  isAdminPasswordChangePath,
  isPublicAdminPath,
  isAdminReauthPath,
  isAdminTransitionPath,
  isSameOriginRequest,
  isStateChangingMethod,
  loadAdminRequestSession,
  safeAdminNextPath,
} from "@/lib/server/admin-auth";

export const onRequest = defineMiddleware(async (context, next) => {
  context.locals.adminSession = null;

  if (isAdminPath(context.url.pathname)) {
    if (isStateChangingMethod(context.request.method) && !isSameOriginRequest(context.request, context.url)) {
      return new Response("Forbidden", { status: 403 });
    }

    const adminSession = await loadAdminRequestSession(context);
    context.locals.adminSession = adminSession;

    if (!adminSession) {
      if (isPublicAdminPath(context.url.pathname)) {
        return next();
      }

      const nextPath = `${context.url.pathname}${context.url.search}`;
      return context.redirect(buildAdminLoginPath(nextPath), 303);
    }

    const requiredTransitionPath = getAdminRequiredTransitionPath(adminSession);

    if (requiredTransitionPath) {
      if (isAdminLogoutPath(context.url.pathname)) {
        return next();
      }

      const canAccessRequiredPath =
        (requiredTransitionPath === "/admin/trocar-senha" && isAdminPasswordChangePath(context.url.pathname))
        || (requiredTransitionPath === "/admin/mfa/setup" && isAdminMfaSetupPath(context.url.pathname))
        || (requiredTransitionPath === "/admin/mfa/challenge" && isAdminMfaChallengePath(context.url.pathname));

      if (!canAccessRequiredPath) {
        return context.redirect(requiredTransitionPath, 303);
      }

      return next();
    }

    if (isPublicAdminPath(context.url.pathname)) {
      if (context.url.pathname === "/admin/login") {
        const nextPath = safeAdminNextPath(context.url.searchParams.get("next"), "/admin/painel");
        return context.redirect(nextPath, 303);
      }

      return next();
    }

    if (isAdminTransitionPath(context.url.pathname) && !isAdminReauthPath(context.url.pathname)) {
      return context.redirect("/admin/painel", 303);
    }

    return next();
  }

  return next();
});
