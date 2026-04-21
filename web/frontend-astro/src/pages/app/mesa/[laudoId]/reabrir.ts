import type { APIRoute } from "astro";

import {
  getAppErrorMessage,
  getAppReturnPath,
  redirectWithAppNotice,
  requireAppSession,
} from "@/lib/server/app-action-route";
import { reopenAppInspection } from "@/lib/server/app-mesa-bridge";

function normalizeIssuedDocumentPolicy(value: FormDataEntryValue | null) {
  const normalized = String(value ?? "").trim().toLowerCase();

  if (normalized === "hide_from_case" || normalized === "keep_visible") {
    return normalized;
  }

  return "keep_visible";
}

export const POST: APIRoute = async (context) => {
  const appSession = requireAppSession(context);
  const formData = await context.request.formData();
  const laudoId = Number(context.params.laudoId ?? 0);
  const returnTo = getAppReturnPath(formData, laudoId > 0 ? `/app/mesa?laudo=${laudoId}` : "/app/mesa");

  if (!Number.isInteger(laudoId) || laudoId <= 0) {
    return redirectWithAppNotice(context, "/app/mesa", {
      tone: "error",
      title: "Laudo invalido",
      message: "Nao foi possivel identificar o laudo a ser reaberto.",
    });
  }

  try {
    const response = await reopenAppInspection(appSession, {
      laudoId,
      issuedDocumentPolicy: normalizeIssuedDocumentPolicy(formData.get("issuedDocumentPolicy")),
    });

    return redirectWithAppNotice(context, `/app/mesa?laudo=${response.laudo_id}`, {
      tone: "success",
      title: "Inspecao reaberta",
      message: response.message || "O caso voltou para edicao e ja pode receber novos ajustes.",
      details: [
        `Laudo: ${response.laudo_id}`,
        response.issued_document_policy_applied
          ? `Politica do documento emitido: ${response.issued_document_policy_applied}`
          : "A politica padrao de reabertura foi aplicada.",
      ],
    });
  } catch (error) {
    return redirectWithAppNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao reabrir",
      message: getAppErrorMessage(
        error,
        "Nao foi possivel reabrir o laudo selecionado na mesa do inspetor.",
      ),
    });
  }
};
