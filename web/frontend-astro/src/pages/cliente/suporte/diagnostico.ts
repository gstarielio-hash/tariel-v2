import type { APIRoute } from "astro";

import { requireClientSession } from "@/lib/server/client-action-route";
import { buildClientDiagnosticSnapshot } from "@/lib/server/client-portal";

export const GET: APIRoute = async (context) => {
  const clientSession = requireClientSession(context);
  const snapshot = await buildClientDiagnosticSnapshot(clientSession.user.companyId);

  if (!snapshot) {
    return new Response("Snapshot do tenant nao encontrado.", {
      status: 404,
    });
  }

  return new Response(JSON.stringify(snapshot, null, 2), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Disposition": `attachment; filename="tariel-cliente-diagnostico-${clientSession.user.companyId}.json"`,
      "Cache-Control": "no-store",
    },
  });
};
