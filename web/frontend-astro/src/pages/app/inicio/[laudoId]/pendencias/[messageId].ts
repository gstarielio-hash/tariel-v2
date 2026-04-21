import type { APIRoute } from "astro";

import {
  getAppErrorMessage,
  getAppReturnPath,
  redirectWithAppNotice,
  requireAppSession,
} from "@/lib/server/app-action-route";
import { updateAppMesaPendency } from "@/lib/server/app-mesa-bridge";

function resolvePositiveInt(value: string | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function resolveBoolean(value: FormDataEntryValue | null) {
  const normalized = String(value ?? "").trim().toLowerCase();
  return normalized === "true" || normalized === "1" || normalized === "sim";
}

export const POST: APIRoute = async (context) => {
  const appSession = requireAppSession(context);
  const laudoId = resolvePositiveInt(context.params.laudoId);
  const messageId = resolvePositiveInt(context.params.messageId);
  const fallbackReturnTo = laudoId ? `/app/inicio?laudo=${laudoId}` : "/app/inicio";
  const formData = await context.request.formData();
  const returnTo = getAppReturnPath(formData, fallbackReturnTo);

  if (!laudoId || !messageId) {
    return redirectWithAppNotice(context, "/app/inicio", {
      tone: "error",
      title: "Pendencia invalida",
      message: "Nao foi possivel identificar a pendencia da mesa que seria atualizada.",
    });
  }

  const resolved = resolveBoolean(formData.get("lida"));

  try {
    await updateAppMesaPendency(appSession, {
      laudoId,
      mensagemId: messageId,
      lida: resolved,
    });

    return redirectWithAppNotice(context, returnTo, {
      tone: "success",
      title: resolved ? "Pendencia resolvida" : "Pendencia reaberta",
      message: resolved
        ? "A pendencia foi marcada como resolvida no contrato governado da mesa."
        : "A pendencia voltou para a fila ativa da mesa.",
      details: [`Laudo: ${laudoId}`, `Mensagem: ${messageId}`],
    });
  } catch (error) {
    return redirectWithAppNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao atualizar pendencia",
      message: getAppErrorMessage(
        error,
        "Nao foi possivel atualizar o estado da pendencia na mesa.",
      ),
    });
  }
};
