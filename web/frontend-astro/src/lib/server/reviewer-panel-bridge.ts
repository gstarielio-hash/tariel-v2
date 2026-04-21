import { randomUUID } from "node:crypto";

import type { AuthenticatedReviewerRequest } from "@/lib/server/reviewer-auth";

export interface ReviewQueueDashboardProjection {
  contract_name: "ReviewQueueDashboardProjectionV1";
  contract_version: string;
  projection_name: "ReviewQueueDashboardProjectionV1";
  projection_audience: "review_queue_web";
  projection_type: "review_queue_projection";
  payload: {
    filter_summary: {
      inspector_id: number | null;
      search_query: string;
      learning_filter: string;
      operation_filter: string;
    };
    queue_summary: {
      in_field_count: number;
      awaiting_review_count: number;
      recent_history_count: number;
      whisper_pending_count: number;
      total_pending_learning: number;
      total_open_pendencies: number;
      total_pending_whispers: number;
      observed_case_ids: string[];
    };
    operation_totals: {
      responder_agora: number;
      validar_aprendizado: number;
      aguardando_inspetor: number;
      fechamento_mesa: number;
      acompanhamento: number;
    };
    template_operation_summary: {
      total_templates: number;
      total_codigos: number;
      total_ativos: number;
      total_em_teste: number;
      total_rascunhos: number;
      total_word: number;
      total_pdf: number;
      total_codigos_sem_ativo: number;
      total_codigos_em_operacao: number;
      total_codigos_em_operacao_sem_ativo: number;
      total_bases_manuais: number;
      ultima_utilizacao_em: string | null;
      ultima_utilizacao_em_label: string;
    };
    pending_whispers_preview: Array<{
      laudo_id: number;
      hash: string;
      texto: string;
      timestamp: string;
      case_lifecycle_status: string;
      active_owner_role: string;
      status_visual_label: string;
      collaboration_summary?: {
        open_pendency_count: number;
        unread_whisper_count: number;
        requires_reviewer_attention: boolean;
      } | null;
    }>;
    queue_sections: {
      em_andamento: ReviewQueueItemPayload[];
      aguardando_avaliacao: ReviewQueueItemPayload[];
      historico: ReviewQueueItemPayload[];
    };
  };
}

export interface ReviewQueueItemPayload {
  id: number;
  queue_section: "em_andamento" | "aguardando_avaliacao" | "historico";
  hash_curto: string;
  primeira_mensagem: string;
  setor_industrial: string;
  status_revisao: string;
  atualizado_em: string | null;
  criado_em: string | null;
  inspetor_nome: string;
  whispers_nao_lidos: number;
  pendencias_abertas: number;
  aprendizados_pendentes: number;
  tempo_em_campo: string;
  tempo_em_campo_status: string;
  fila_operacional: string;
  fila_operacional_label: string;
  prioridade_operacional: string;
  prioridade_operacional_label: string;
  proxima_acao: string;
  case_status: string;
  case_lifecycle_status: string;
  case_workflow_mode: string;
  active_owner_role: string;
  allowed_next_lifecycle_statuses: string[];
  allowed_surface_actions: string[];
  status_visual_label: string;
}

const DEFAULT_PYTHON_BACKEND_URL = "http://127.0.0.1:8000";

function resolvePythonBackendBaseUrl() {
  const configured = String(process.env["TARIEL_PYTHON_BACKEND_URL"] ?? "").trim();
  return configured || DEFAULT_PYTHON_BACKEND_URL;
}

function buildBackendUrl(pathname: string) {
  return new URL(pathname, resolvePythonBackendBaseUrl()).toString();
}

async function extractBackendError(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: unknown; message?: unknown }
      | null;
    const detail = payload?.detail ?? payload?.message;
    if (typeof detail === "string" && detail.trim()) {
      return detail.trim();
    }
  }

  const detail = await response.text().catch(() => "");
  return detail.trim();
}

export async function fetchReviewerPanelSnapshot(
  reviewerSession: AuthenticatedReviewerRequest,
  params: URLSearchParams,
) {
  const pathname = `/revisao/api/painel/snapshot${params.toString() ? `?${params.toString()}` : ""}`;
  const response = await fetch(buildBackendUrl(pathname), {
    method: "GET",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${reviewerSession.session.token}`,
      "X-Client-Request-Id": randomUUID(),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await extractBackendError(response);
    throw new Error(
      `Python review panel snapshot failed (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return (await response.json()) as ReviewQueueDashboardProjection;
}
