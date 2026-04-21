import type { APIRoute } from "astro";

import {
  getAppErrorMessage,
  getAppReturnPath,
  redirectWithAppNotice,
  requireAppSession,
} from "@/lib/server/app-action-route";
import { startAppInspection } from "@/lib/server/app-mesa-bridge";

function normalizeEntryModePreference(value: FormDataEntryValue | null) {
  const normalized = String(value ?? "").trim().toLowerCase();

  if (normalized === "chat_first" || normalized === "evidence_first" || normalized === "auto_recommended") {
    return normalized;
  }

  return "auto_recommended";
}

export const POST: APIRoute = async (context) => {
  const appSession = requireAppSession(context);
  const formData = await context.request.formData();
  const returnTo = getAppReturnPath(formData, "/app/mesa");

  try {
    const response = await startAppInspection(appSession, {
      tipoTemplate: String(formData.get("tipoTemplate") ?? ""),
      entryModePreference: normalizeEntryModePreference(formData.get("entryModePreference")),
      cliente: String(formData.get("cliente") ?? ""),
      unidade: String(formData.get("unidade") ?? ""),
      localInspecao: String(formData.get("localInspecao") ?? ""),
      objetivo: String(formData.get("objetivo") ?? ""),
      nomeInspecao: String(formData.get("nomeInspecao") ?? ""),
    });

    return redirectWithAppNotice(context, `/app/mesa?laudo=${response.laudo_id}`, {
      tone: "success",
      title: "Inspecao criada",
      message:
        response.message
        || "A nova inspecao foi aberta na mesa do inspetor e ja pode receber a primeira mensagem.",
      details: [
        `Laudo: ${response.laudo_id}`,
        response.entry_mode_effective
          ? `Modo efetivo: ${response.entry_mode_effective}`
          : "A trilha oficial do caso ja foi aberta no backend Python.",
      ],
    });
  } catch (error) {
    return redirectWithAppNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao criar inspecao",
      message: getAppErrorMessage(
        error,
        "Nao foi possivel abrir uma nova inspecao a partir da mesa do inspetor.",
      ),
    });
  }
};
