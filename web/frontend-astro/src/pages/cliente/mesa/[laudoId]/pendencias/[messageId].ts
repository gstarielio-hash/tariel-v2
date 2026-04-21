import type { APIRoute } from "astro";

import {
  getClientErrorMessage,
  getClientReturnPath,
  redirectWithClientNotice,
  requireClientSession,
} from "@/lib/server/client-action-route";
import { toggleClientMesaPendency } from "@/lib/server/client-mesa";

function resolvePositiveInt(value: string | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function resolveBoolean(value: FormDataEntryValue | null) {
  const normalized = String(value ?? "").trim().toLowerCase();
  return normalized === "true" || normalized === "1" || normalized === "sim";
}

export const POST: APIRoute = async (context) => {
  const clientSession = requireClientSession(context);
  const laudoId = resolvePositiveInt(context.params.laudoId);
  const messageId = resolvePositiveInt(context.params.messageId);
  const fallbackReturnTo = laudoId ? `/cliente/mesa?sec=reply&laudo=${laudoId}` : "/cliente/mesa?sec=reply";
  const formData = await context.request.formData();
  const returnTo = getClientReturnPath(formData, fallbackReturnTo);

  if (!laudoId || !messageId) {
    return redirectWithClientNotice(context, "/cliente/mesa?sec=reply", {
      tone: "error",
      title: "Pendência inválida",
      message: "Não foi possível identificar a pendência da mesa que seria atualizada.",
    });
  }

  const resolved = resolveBoolean(formData.get("lida"));

  try {
    await toggleClientMesaPendency(clientSession, {
      laudoId,
      mensagemId: messageId,
      resolved,
    });

    return redirectWithClientNotice(context, returnTo, {
      tone: "success",
      title: resolved ? "Pendência resolvida" : "Pendência reaberta",
      message: resolved
        ? "A pendência foi marcada como resolvida no contrato governado da mesa."
        : "A pendência voltou para a fila ativa da mesa.",
      details: [`Laudo: ${laudoId}`, `Mensagem: ${messageId}`],
    });
  } catch (error) {
    return redirectWithClientNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao atualizar pendência",
      message: getClientErrorMessage(
        error,
        "Não foi possível atualizar o estado da pendência na mesa.",
      ),
    });
  }
};
