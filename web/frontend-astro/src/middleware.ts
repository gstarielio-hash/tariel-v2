import { defineMiddleware } from "astro:middleware";

import {
  buildAppLoginPath,
  isAppPath,
  isPublicAppPath,
  loadAppPasswordResetSession,
  loadAppRequestSession,
  safeAppNextPath,
} from "@/lib/server/app-auth";
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
import {
  buildReviewerLoginPath,
  isPublicReviewerPath,
  isReviewerPath,
  loadReviewerPasswordResetSession,
  loadReviewerRequestSession,
  safeReviewerNextPath,
} from "@/lib/server/reviewer-auth";

export const onRequest = defineMiddleware(async (context, next) => {
  context.locals.appSession = null;
  context.locals.appPasswordResetSession = null;
  context.locals.adminSession = null;
  context.locals.clientSession = null;
  context.locals.clientPasswordResetSession = null;
  context.locals.reviewerSession = null;
  context.locals.reviewerPasswordResetSession = null;

  if (isAppPath(context.url.pathname)) {
    if (isStateChangingMethod(context.request.method) && !isSameOriginRequest(context.request, context.url)) {
      return new Response("Forbidden", { status: 403 });
    }

    const appSession = await loadAppRequestSession(context);
    const appPasswordResetSession = appSession ? null : await loadAppPasswordResetSession(context);
    context.locals.appSession = appSession;
    context.locals.appPasswordResetSession = appPasswordResetSession;

    const isAppPasswordChangePath =
      context.url.pathname === "/app/trocar-senha"
      || context.url.pathname === "/app/trocar-senha/salvar";
    const isAppLogoutPath = context.url.pathname === "/app/logout";

    if (appPasswordResetSession) {
      if (isAppPasswordChangePath || isAppLogoutPath) {
        return next();
      }

      return context.redirect("/app/trocar-senha", 303);
    }

    if (!appSession) {
      if (isPublicAppPath(context.url.pathname)) {
        return next();
      }

      const nextPath = `${context.url.pathname}${context.url.search}`;
      return context.redirect(buildAppLoginPath(nextPath), 303);
    }

    if (isPublicAppPath(context.url.pathname)) {
      if (context.url.pathname === "/app/login") {
        const nextPath = safeAppNextPath(context.url.searchParams.get("next"), "/app/inicio");
        return context.redirect(nextPath, 303);
      }

      return context.redirect("/app/inicio", 303);
    }

    if (isAppPasswordChangePath) {
      return context.redirect("/app/inicio", 303);
    }

    return next();
  }

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

  if (isReviewerPath(context.url.pathname)) {
    if (isStateChangingMethod(context.request.method) && !isSameOriginRequest(context.request, context.url)) {
      return new Response("Forbidden", { status: 403 });
    }

    const reviewerSession = await loadReviewerRequestSession(context);
    const reviewerPasswordResetSession = reviewerSession ? null : await loadReviewerPasswordResetSession(context);
    context.locals.reviewerSession = reviewerSession;
    context.locals.reviewerPasswordResetSession = reviewerPasswordResetSession;

    const isReviewerPasswordChangePath =
      context.url.pathname === "/revisao/trocar-senha"
      || context.url.pathname === "/revisao/trocar-senha/salvar";
    const isReviewerLogoutPath = context.url.pathname === "/revisao/logout";

    if (reviewerPasswordResetSession) {
      if (isReviewerPasswordChangePath || isReviewerLogoutPath) {
        return next();
      }

      return context.redirect("/revisao/trocar-senha", 303);
    }

    if (!reviewerSession) {
      if (isPublicReviewerPath(context.url.pathname)) {
        return next();
      }

      const nextPath = `${context.url.pathname}${context.url.search}`;
      return context.redirect(buildReviewerLoginPath(nextPath), 303);
    }

    if (isPublicReviewerPath(context.url.pathname)) {
      if (context.url.pathname === "/revisao/login") {
        const nextPath = safeReviewerNextPath(context.url.searchParams.get("next"), "/revisao/painel");
        return context.redirect(nextPath, 303);
      }

      return context.redirect("/revisao/painel", 303);
    }

    if (isReviewerPasswordChangePath) {
      return context.redirect("/revisao/painel", 303);
    }

    return next();
  }

  return next();
});
