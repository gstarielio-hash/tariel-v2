import type { APIRoute } from "astro";

import {
  getReviewerErrorMessage,
  getReviewerReturnPath,
  redirectWithReviewerNotice,
  requireReviewerSession,
} from "@/lib/server/reviewer-action-route";
import { requestReviewerMesaCoverageRefazer } from "@/lib/server/reviewer-mesa";

function resolveLaudoId(value: string | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function resolveBoolean(value: FormDataEntryValue | null) {
  const normalized = String(value ?? "").trim().toLowerCase();
  return normalized === "true" || normalized === "1" || normalized === "sim";
}

function resolveString(value: FormDataEntryValue | null, fallback = "") {
  return String(value ?? fallback).trim();
}

export const POST: APIRoute = async (context) => {
  const reviewerSession = requireReviewerSession(context);
  const laudoId = resolveLaudoId(context.params.laudoId);
  const fallbackReturnTo = laudoId ? `/revisao/painel?laudo=${laudoId}` : "/revisao/painel";
  const formData = await context.request.formData();
  const returnTo = getReviewerReturnPath(formData, fallbackReturnTo);

  if (!laudoId) {
    return redirectWithReviewerNotice(context, "/revisao/painel", {
      tone: "error",
      title: "Laudo invalido",
      message: "Nao foi possivel identificar o laudo para solicitar o refazer da evidencia.",
    });
  }

  try {
    const title = resolveString(formData.get("title"), "Evidencia do pacote");
    const kind = resolveString(formData.get("kind"), "evidence");
    const evidenceKey = resolveString(formData.get("evidenceKey"));
    if (!evidenceKey) {
      throw new Error("A chave da evidencia nao foi informada.");
    }

    await requestReviewerMesaCoverageRefazer(reviewerSession, {
      laudoId,
      evidenceKey,
      title,
      kind,
      required: resolveBoolean(formData.get("required")),
      sourceStatus: resolveString(formData.get("sourceStatus")) || null,
      operationalStatus: resolveString(formData.get("operationalStatus")) || null,
      mesaStatus: resolveString(formData.get("mesaStatus")) || null,
      componentType: resolveString(formData.get("componentType")) || null,
      viewAngle: resolveString(formData.get("viewAngle")) || null,
      summary: resolveString(formData.get("summary")) || null,
      failureReasons: resolveString(formData.get("failureReasons"))
        .split("|")
        .map((item) => item.trim())
        .filter(Boolean),
    });

    return redirectWithReviewerNotice(context, returnTo, {
      tone: "success",
      title: "Refazer solicitado",
      message: "A mesa abriu um retorno governado para a evidencia selecionada.",
      details: [`Laudo: ${laudoId}`, `Evidencia: ${title}`],
    });
  } catch (error) {
    return redirectWithReviewerNotice(context, returnTo, {
      tone: "error",
      title: "Falha ao solicitar refazer",
      message: getReviewerErrorMessage(
        error,
        "Nao foi possivel registrar a solicitacao de refazer para esta evidencia.",
      ),
    });
  }
};
