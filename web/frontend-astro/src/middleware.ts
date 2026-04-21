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
import {
  buildClientLoginPath,
  isClientPath,
  isPublicClientPath,
  loadClientPasswordResetSession,
  loadClientRequestSession,
  safeClientNextPath,
} from "@/lib/server/client-auth";

export const onRequest = defineMiddleware(async (context, next) => {
  context.locals.adminSession = null;
  context.locals.clientSession = null;
  context.locals.clientPasswordResetSession = null;

  if (isClientPath(context.url.pathname)) {
    if (isStateChangingMethod(context.request.method) && !isSameOriginRequest(context.request, context.url)) {
      return new Response("Forbidden", { status: 403 });
    }

    const clientSession = await loadClientRequestSession(context);
    const clientPasswordResetSession = clientSession ? null : await loadClientPasswordResetSession(context);
    context.locals.clientSession = clientSession;
    context.locals.clientPasswordResetSession = clientPasswordResetSession;

    const isClientPasswordChangePath =
      context.url.pathname === "/cliente/trocar-senha"
      || context.url.pathname === "/cliente/trocar-senha/salvar";
    const isClientLogoutPath = context.url.pathname === "/cliente/logout";

    if (clientPasswordResetSession) {
      if (isClientPasswordChangePath || isClientLogoutPath) {
        return next();
      }

      return context.redirect("/cliente/trocar-senha", 303);
    }

    if (!clientSession) {
      if (isPublicClientPath(context.url.pathname)) {
        return next();
      }

      const nextPath = `${context.url.pathname}${context.url.search}`;
      return context.redirect(buildClientLoginPath(nextPath), 303);
    }

    if (isPublicClientPath(context.url.pathname)) {
      if (context.url.pathname === "/cliente/login") {
        const nextPath = safeClientNextPath(context.url.searchParams.get("next"), "/cliente/painel");
        return context.redirect(nextPath, 303);
      }

      return context.redirect("/cliente/painel", 303);
    }

    if (isClientPasswordChangePath) {
      return context.redirect("/cliente/painel", 303);
    }

    return next();
  }

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
