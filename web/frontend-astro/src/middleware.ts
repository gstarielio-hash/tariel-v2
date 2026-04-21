import { defineMiddleware } from "astro:middleware";

import {
  buildAdminLoginPath,
  isAdminPath,
  isPublicAdminPath,
  isSameOriginRequest,
  isStateChangingMethod,
  loadAdminRequestSession,
  safeAdminNextPath,
} from "@/lib/server/admin-auth";

export const onRequest = defineMiddleware(async (context, next) => {
  context.locals.adminSession = null;

  if (!isAdminPath(context.url.pathname)) {
    return next();
  }

  if (isStateChangingMethod(context.request.method) && !isSameOriginRequest(context.request, context.url)) {
    return new Response("Forbidden", { status: 403 });
  }

  const adminSession = await loadAdminRequestSession(context);
  context.locals.adminSession = adminSession;

  if (isPublicAdminPath(context.url.pathname)) {
    if (adminSession && context.url.pathname === "/admin/login") {
      const nextPath = safeAdminNextPath(context.url.searchParams.get("next"), "/admin/painel");
      return context.redirect(nextPath, 303);
    }

    return next();
  }

  if (!adminSession) {
    const nextPath = `${context.url.pathname}${context.url.search}`;
    return context.redirect(buildAdminLoginPath(nextPath), 303);
  }

  return next();
});
