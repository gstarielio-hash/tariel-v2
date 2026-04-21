import type { APIRoute } from "astro";

import { requireReviewerSession } from "@/lib/server/reviewer-action-route";
import {
  buildReviewerMesaProxyError,
  buildReviewerMesaProxyResponse,
  resolveReviewerMesaInt,
} from "@/lib/server/reviewer-mesa-route";
import { fetchReviewerMesaPackagePdf } from "@/lib/server/reviewer-mesa";

export const GET: APIRoute = async (context) => {
  const reviewerSession = requireReviewerSession(context);
  const laudoId = resolveReviewerMesaInt(context.params.laudoId);

  if (!laudoId) {
    return new Response("Laudo invalido.", { status: 400 });
  }

  try {
    const upstream = await fetchReviewerMesaPackagePdf(reviewerSession, laudoId);
    return buildReviewerMesaProxyResponse(upstream);
  } catch (error) {
    return buildReviewerMesaProxyError(error, "Falha ao exportar o PDF.");
  }
};
