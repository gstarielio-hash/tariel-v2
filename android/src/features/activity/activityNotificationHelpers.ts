import type { MobileLaudoCard, MobileMesaMessage } from "../../types/mobile";
import {
  descricaoCaseLifecycle,
  mapearLifecycleVisual,
  resolverAllowedLifecycleTransitions,
  resolverAllowedSurfaceActions,
  resolverCaseLifecycleStatus,
  resolverCaseOwnerRole,
  rotuloCaseLifecycle,
  targetThreadCaseLifecycle,
} from "../chat/caseLifecycle";
import type { ActiveThread, MobileActivityNotification } from "../chat/types";
import { resumoMensagemAtividade } from "../common/messagePreviewHelpers";

const MAX_LAUDOS_MONITORADOS_MESA = 6;

function resolverResumoReemissaoPdfOficial(item: MobileLaudoCard): {
  title: string;
  body: string;
} | null {
  const summary = item.official_issue_summary;
  if (!summary?.primary_pdf_diverged) {
    return null;
  }

  const detail =
    String(summary.detail || "").trim() || "PDF emitido divergente";
  return {
    title: String(summary.label || "").trim() || "Reemissão recomendada",
    body: `${item.titulo}: ${detail}. Abra a finalização para reemitir.`,
  };
}

function obterEstadoPendenciaMesa(item: MobileMesaMessage): string {
  if (
    item.pendency_state === "open" ||
    item.pendency_state === "resolved" ||
    item.pendency_state === "not_applicable"
  ) {
    return item.pendency_state;
  }
  const mensagemEhPendencia =
    item.item_kind === "pendency" ||
    item.message_kind === "mesa_pendency" ||
    item.tipo === "humano_eng";
  if (!mensagemEhPendencia) {
    if (item.resolvida_em) {
      return "resolved";
    }
    return "not_applicable";
  }
  return item.resolvida_em ? "resolved" : "open";
}

export function assinaturaStatusLaudo(item: MobileLaudoCard): string {
  const base = [
    item.status_card,
    item.status_revisao,
    item.status_card_label,
    item.permite_reabrir ? "1" : "0",
    item.permite_edicao ? "1" : "0",
  ];
  const lifecycleStatus = resolverCaseLifecycleStatus({ card: item });
  const ownerRole = resolverCaseOwnerRole({
    card: item,
    lifecycleStatus,
  });
  const transitions = resolverAllowedLifecycleTransitions({
    card: item,
    lifecycleStatus,
  }).map((transition) => transition.target_status);
  const surfaceActions = resolverAllowedSurfaceActions({
    card: item,
    lifecycleStatus,
    ownerRole,
  });
  base.push(
    lifecycleStatus,
    ownerRole,
    transitions.join(","),
    surfaceActions.join(","),
  );
  const reissueSummary = item.official_issue_summary;
  if (reissueSummary?.primary_pdf_diverged) {
    base.push(
      "reissue",
      String(reissueSummary.issue_number || ""),
      String(reissueSummary.primary_pdf_storage_version || ""),
      String(reissueSummary.current_primary_pdf_storage_version || ""),
    );
  }
  return base.join("|");
}

export function assinaturaMensagemMesa(item: MobileMesaMessage): string {
  return [
    item.id,
    item.lida ? "1" : "0",
    obterEstadoPendenciaMesa(item),
    item.texto || "",
  ].join("|");
}

export function formatarTipoTemplateLaudo(
  value: string | null | undefined,
): string {
  const texto = String(value || "").trim();
  if (!texto) {
    return "Laudo padrão";
  }

  return texto
    .replace(/[_-]+/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .map(
      (parte) => parte.charAt(0).toUpperCase() + parte.slice(1).toLowerCase(),
    )
    .join(" ");
}

export function criarNotificacaoStatusLaudo(
  item: MobileLaudoCard,
): MobileActivityNotification {
  const reissueSummary = resolverResumoReemissaoPdfOficial(item);
  if (reissueSummary) {
    return {
      id: `status:${item.id}:${assinaturaStatusLaudo(item)}`,
      kind: "alerta_critico",
      laudoId: item.id,
      title: reissueSummary.title,
      body: reissueSummary.body,
      createdAt: new Date().toISOString(),
      unread: true,
      targetThread: "finalizar",
    };
  }

  const lifecycleStatus = resolverCaseLifecycleStatus({ card: item });
  const ownerRole = resolverCaseOwnerRole({
    card: item,
    lifecycleStatus,
  });
  const lifecycleLabel = rotuloCaseLifecycle(lifecycleStatus);
  const lifecycleDetail = descricaoCaseLifecycle(lifecycleStatus);
  const mapaTitulo: Record<string, string> = {
    analise_livre: "Caso em análise livre",
    pre_laudo: "Caso em pré-laudo",
    laudo_em_coleta: "Laudo em coleta",
    aguardando_mesa: "Caso enviado para a mesa",
    em_revisao_mesa: "Mesa revisando o caso",
    devolvido_para_correcao: "Caso devolvido para correção",
    aprovado: "Caso aprovado",
    emitido: "Documento final emitido",
  };

  return {
    id: `status:${item.id}:${assinaturaStatusLaudo(item)}`,
    kind: "status",
    laudoId: item.id,
    title: mapaTitulo[lifecycleStatus] || "Status do laudo atualizado",
    body: `${item.titulo} agora está em ${lifecycleLabel.toLowerCase()}. ${lifecycleDetail}${ownerRole === "mesa" ? " Acompanhe a mesa no app." : ""}`,
    createdAt: new Date().toISOString(),
    unread: true,
    targetThread: targetThreadCaseLifecycle(lifecycleStatus),
  };
}

export function criarNotificacaoMesa(
  kind: "status" | "mesa_nova" | "mesa_resolvida" | "mesa_reaberta",
  mensagemMesa: MobileMesaMessage,
  tituloLaudo: string,
): MobileActivityNotification {
  const mapaTitulo: Record<
    "status" | "mesa_nova" | "mesa_resolvida" | "mesa_reaberta",
    string
  > = {
    status: "Atividade da mesa",
    mesa_nova: "Nova mensagem da mesa",
    mesa_resolvida: "Pendência marcada como resolvida",
    mesa_reaberta: "Pendência reaberta pela mesa",
  };
  const fallback =
    kind === "mesa_resolvida"
      ? "A mesa marcou uma pendência como resolvida."
      : kind === "mesa_reaberta"
        ? "A mesa reabriu uma pendência para novo ajuste."
        : "A mesa enviou uma nova atualização.";

  return {
    id:
      kind === "mesa_nova"
        ? `mesa:${mensagemMesa.id}`
        : `mesa:${mensagemMesa.id}:${kind}:${obterEstadoPendenciaMesa(mensagemMesa)}`,
    kind,
    laudoId: mensagemMesa.laudo_id,
    title: mapaTitulo[kind],
    body: `${tituloLaudo}: ${resumoMensagemAtividade(mensagemMesa.texto, fallback)}`,
    createdAt: new Date().toISOString(),
    unread: true,
    targetThread: "mesa",
  };
}

export function criarNotificacaoSistema(params: {
  title: string;
  body: string;
  kind?: "system" | "alerta_critico";
  laudoId?: number | null;
  targetThread?: ActiveThread;
}): MobileActivityNotification {
  const kind = params.kind || "system";
  return {
    id: `${kind}:${Date.now()}:${Math.random().toString(16).slice(2, 7)}`,
    kind,
    laudoId: params.laudoId ?? null,
    title: params.title,
    body: params.body,
    createdAt: new Date().toISOString(),
    unread: true,
    targetThread: params.targetThread || "chat",
  };
}

export function selecionarLaudosParaMonitoramentoMesa(params: {
  laudos: MobileLaudoCard[];
  laudoAtivoId: number | null;
}): number[] {
  const ids: number[] = [];

  if (params.laudoAtivoId) {
    ids.push(params.laudoAtivoId);
  }

  for (const item of params.laudos) {
    if (ids.length >= MAX_LAUDOS_MONITORADOS_MESA) {
      break;
    }
    if (ids.includes(item.id)) {
      continue;
    }
    const lifecycleStatus = resolverCaseLifecycleStatus({ card: item });
    const ownerRole = resolverCaseOwnerRole({
      card: item,
      lifecycleStatus,
    });
    if (ownerRole === "mesa" || lifecycleStatus === "devolvido_para_correcao") {
      ids.push(item.id);
    }
  }

  return ids;
}

export function mapearStatusLaudoVisual(statusCard: string) {
  return mapearLifecycleVisual(statusCard);
}
