import type { APIRoute } from "astro";

import { requireReviewerSession } from "@/lib/server/reviewer-action-route";
import { fetchReviewerMesaFrozenOfficialBundle } from "@/lib/server/reviewer-mesa";

function resolveLaudoId(value: string | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export const GET: APIRoute = async (context) => {
  const reviewerSession = requireReviewerSession(context);
  const laudoId = resolveLaudoId(context.params.laudoId);

  if (!laudoId) {
    return new Response("Laudo invalido.", { status: 400 });
  }

  try {
    const upstream = await fetchReviewerMesaFrozenOfficialBundle(reviewerSession, laudoId);
    const headers = new Headers();
    for (const headerName of [
      "content-type",
      "content-length",
      "content-disposition",
      "cache-control",
      "etag",
      "last-modified",
    ]) {
      const value = upstream.headers.get(headerName);
      if (value) {
        headers.set(headerName, value);
      }
    }

    return new Response(upstream.body, {
      status: upstream.status,
      headers,
    });
  } catch (error) {
    const detail =
      error instanceof Error && error.message.trim()
        ? error.message
        : "Falha ao baixar o bundle oficial congelado.";
    return new Response(detail, { status: 502 });
  }
};
