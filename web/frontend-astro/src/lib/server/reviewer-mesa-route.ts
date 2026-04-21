export function resolveReviewerMesaInt(value: string | undefined | null) {
  const parsed = Number(value ?? 0);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export function getReviewerMesaReturnFallback(laudoId: number | null) {
  return laudoId ? `/revisao/painel?laudo=${laudoId}` : "/revisao/painel";
}

export function buildReviewerMesaProxyResponse(upstream: Response) {
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
}

export function buildReviewerMesaProxyError(error: unknown, fallback: string) {
  const detail = error instanceof Error && error.message.trim() ? error.message : fallback;
  return new Response(detail, { status: 502 });
}
