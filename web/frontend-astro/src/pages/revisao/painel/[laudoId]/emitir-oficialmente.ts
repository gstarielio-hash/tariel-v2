import type { APIRoute } from "astro";

import {
  getReviewerErrorMessage,
  getReviewerReturnPath,
  redirectWithReviewerNotice,
  requireReviewerSession,
} from "@/lib/server/reviewer-action-route";
import { issueReviewerMesaOfficial } from "@/lib/server/reviewer-mesa";

function resolvePositiveInt(value: string | undefined | null) {
  const parsed = Number(value ?? 0);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export const POST: APIRoute = async (context) => {
  const reviewerSession = requireReviewerSession(context);
  const laudoId = resolvePositiveInt(context.params.laudoId);
  const fallbackReturnTo = laudoId ? `/revisao/painel?laudo=${laudoId}` : "/revisao/painel";
  const formData = await context.request.formData();
  const returnTo = getReviewerReturnPath(formData, fallbackReturnTo);

  if (!laudoId) {
    return redirectWithReviewerNotice(context, "/revisao/painel", {
      tone: "error",
      title: "Laudo invalido",
      message: "Nao foi possivel identificar o laudo para emissao oficial.",
    });
  }

  const signatoryId = resolvePositiveInt(formData.get("signatoryId")?.toString() ?? null);

  if (!signatoryId) {
    return redirectWithReviewerNotice(context, returnTo, {
      tone: "error",
      title: "Signatario obrigatorio",
      message: "Selecione um signatario elegivel antes de emitir oficialmente.",
    });
  }

  try {
    const result = await issueReviewerMesaOfficial(reviewerSession, {
      laudoId,
      signatoryId,
      expectedCurrentIssueId: resolvePositiveInt(formData.get("expectedCurrentIssueId")?.toString() ?? null),
      expectedCurrentIssueNumber: String(formData.get("expectedCurrentIssueNumber") ?? "").trim() || null,
    });

    return redirectWithReviewerNotice(context, returnTo, {
      tone: "success",
      title: result.reissued ? "Reemissao registrada" : "Emissao registrada",
      message: result.idempotent_replay
        ? "A emissao oficial ja existia para este estado do laudo e foi reaproveitada."
        : result.reissued
          ? "A reemissao oficial foi registrada com sucesso."
          : "A emissao oficial foi registrada com sucesso.",
      details: [
        result.issue_number ? `Emissao: ${result.issue_number}` : "Numero da emissao nao informado.",
        result.superseded_issue_number
          ? `Substituiu: ${result.superseded_issue_number}`
          : "Nenhuma emissao anterior foi substituida.",
      ],
    });
  } catch (error) {
    return redirectWithReviewerNotice(context, returnTo, {
      tone: "error",
      title: "Falha na emissao oficial",
      message: getReviewerErrorMessage(
        error,
        "Nao foi possivel registrar a emissao oficial neste momento.",
      ),
    });
  }
};
