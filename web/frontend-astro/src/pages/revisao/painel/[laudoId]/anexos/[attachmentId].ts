import type { APIRoute } from "astro";

import { requireReviewerSession } from "@/lib/server/reviewer-action-route";
import {
  buildReviewerMesaProxyError,
  buildReviewerMesaProxyResponse,
  resolveReviewerMesaInt,
} from "@/lib/server/reviewer-mesa-route";
import { fetchReviewerMesaAttachment } from "@/lib/server/reviewer-mesa";

export const GET: APIRoute = async (context) => {
  const reviewerSession = requireReviewerSession(context);
  const laudoId = resolveReviewerMesaInt(context.params.laudoId);
  const attachmentId = resolveReviewerMesaInt(context.params.attachmentId);

  if (!laudoId || !attachmentId) {
    return new Response("Anexo invalido.", { status: 400 });
  }

  try {
    const upstream = await fetchReviewerMesaAttachment(reviewerSession, {
      laudoId,
      anexoId: attachmentId,
    });
    return buildReviewerMesaProxyResponse(upstream);
  } catch (error) {
    return buildReviewerMesaProxyError(error, "Falha ao baixar o anexo.");
  }
};
