import type { APIRoute } from "astro";

import { requireAppSession } from "@/lib/server/app-action-route";
import {
  fetchAppInspectionPreviewResponse,
  fetchAppMesaMessages,
  fetchAppMesaSummary,
} from "@/lib/server/app-mesa-bridge";

function resolveLaudoId(value: string | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function buildPreviewDiagnostic(input: {
  summaryText: string;
  messageLines: string[];
  templateLabel: string;
  sectorLabel: string;
}) {
  const blocks = [
    `Template tecnico: ${input.templateLabel || "padrao"}`,
    `Equipamento ou setor: ${input.sectorLabel || "geral"}`,
    input.summaryText,
    input.messageLines.length > 0
      ? ["Trechos recentes da thread:", ...input.messageLines.map((line) => `- ${line}`)].join("\n")
      : "",
  ].filter(Boolean);

  return blocks.join("\n\n").trim();
}

export const GET: APIRoute = async (context) => {
  const appSession = requireAppSession(context);
  const laudoId = resolveLaudoId(context.params.laudoId);

  if (!laudoId) {
    return new Response("Laudo invalido.", { status: 400 });
  }

  try {
    const [summary, messages] = await Promise.all([
      fetchAppMesaSummary(appSession, laudoId),
      fetchAppMesaMessages(appSession, laudoId).catch(() => null),
    ]);

    const recentMessages = (messages?.itens ?? []).slice(-8);
    const messageLines = recentMessages
      .map((message) => String(message.texto ?? "").trim())
      .filter(Boolean)
      .slice(0, 8);

    const summaryText = [
      summary.laudo_card?.titulo || "",
      summary.laudo_card?.preview || "",
      `Status: ${summary.status_visual_label || "nao informado"}`,
      `Workflow: ${summary.case_workflow_mode || "nao informado"}`,
      `Dono atual: ${summary.active_owner_role || "nao informado"}`,
      `Mensagens: ${summary.resumo.total_mensagens}`,
      `Pendencias abertas: ${summary.resumo.pendencias_abertas}`,
      summary.resumo.ultima_mensagem_preview || "",
    ]
      .filter(Boolean)
      .join("\n");

    const diagnostico = buildPreviewDiagnostic({
      summaryText,
      messageLines,
      templateLabel: summary.laudo_card?.tipo_template || summary.laudo_card?.titulo || "padrao",
      sectorLabel: summary.laudo_card?.titulo || `Laudo ${laudoId}`,
    });

    const response = await fetchAppInspectionPreviewResponse(appSession, {
      diagnostico,
      inspetor: appSession.user.name,
      empresa: appSession.user.companyName,
      setor: summary.laudo_card?.titulo || "geral",
      data: new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(new Date()),
      laudoId,
      tipoTemplate: summary.laudo_card?.tipo_template || null,
    });

    const headers = new Headers(response.headers);
    headers.set("Content-Disposition", `inline; filename="preview_laudo_${laudoId}.pdf"`);
    return new Response(response.body, {
      status: response.status,
      headers,
    });
  } catch (error) {
    const message = error instanceof Error && error.message.trim()
      ? error.message
      : "Nao foi possivel gerar a pre-visualizacao.";
    return new Response(message, { status: 500 });
  }
};
