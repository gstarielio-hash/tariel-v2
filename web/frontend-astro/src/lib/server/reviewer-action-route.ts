import type { APIContext } from "astro";

import type { AuthenticatedReviewerRequest } from "@/lib/server/reviewer-auth";
import { safeReviewerNextPath } from "@/lib/server/reviewer-auth";
import {
  setReviewerNotice,
  type ReviewerNotice,
} from "@/lib/server/reviewer-notice";

export function getReviewerErrorMessage(
  error: unknown,
  fallback = "Falha ao processar a operacao.",
) {
  return error instanceof Error && error.message.trim() ? error.message : fallback;
}

export function requireReviewerSession(context: APIContext): AuthenticatedReviewerRequest {
  const reviewerSession = context.locals.reviewerSession;

  if (!reviewerSession) {
    throw new Error("Sessao do portal revisor invalida.");
  }

  return reviewerSession;
}

export function getReviewerReturnPath(
  formData: FormData,
  fallback: string,
  field = "returnTo",
) {
  return safeReviewerNextPath(formData.get(field)?.toString(), fallback);
}

export function redirectWithReviewerNotice(
  context: APIContext,
  returnTo: string,
  notice: ReviewerNotice,
) {
  setReviewerNotice(context.cookies, notice);
  return context.redirect(returnTo, 303);
}
