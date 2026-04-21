import type { APIRoute } from "astro";

import {
  getAppErrorMessage,
  getAppReturnPath,
  redirectWithAppNotice,
  requireAppSession,
} from "@/lib/server/app-action-route";
import { finalizeAppInspection } from "@/lib/server/app-mesa-bridge";

export const POST: APIRoute = async (context) => {
  const appSession = requireAppSession(context);
  const formData = await context.request.formData();
  const laudoId = Number(context.params.laudoId ?? 0);
  const returnTo = getAppReturnPath(formData, laudoId > 0 ? `/app/mesa?laudo=${laudoId}` : "/app/mesa");

  if (!Number.isInteger(laudoId) || laudoId <= 0) {
    return redirectWithAppNotice(context, "/app/mesa", {
      tone: "error",
      title: "Laudo invalido",
      message: "Nao foi possivel identificar o laudo a ser finalizado.",
    });
  }

  try {
    const response = await finalizeAppInspection(appSession, { laudoId });

    return redirectWithAppNotice(context, `/app/mesa?laudo=${response.laudo_id}`, {
      tone: "success",
      title: "Fluxo finalizado",
      message:
        response.message
        || "O backend consolidou a decisao final deste laudo e atualizou a trilha oficial do caso.",
      details: [
        `Laudo: ${response.laudo_id}`,
        response.review_mode_final
          ? `Modo final: ${response.review_mode_final}`
          : "A decisao final foi aplicada no fluxo oficial.",
      ],
    });
  } catch (error) {
    return redirectWithAppNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao finalizar",
      message: getAppErrorMessage(
        error,
        "Nao foi possivel finalizar o laudo selecionado na mesa do inspetor.",
      ),
    });
  }
};
