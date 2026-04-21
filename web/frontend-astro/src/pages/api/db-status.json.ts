import type { APIRoute } from "astro";

import { getMigrationMetrics } from "@/lib/server/dashboard-metrics";

export const GET: APIRoute = async () => {
  const metrics = await getMigrationMetrics();

  return new Response(JSON.stringify(metrics, null, 2), {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
    status: metrics.connected ? 200 : 503,
  });
};
