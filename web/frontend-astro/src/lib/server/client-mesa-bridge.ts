import { randomUUID } from "node:crypto";

import type { AuthenticatedClientRequest } from "@/lib/server/client-auth";

interface ClientMesaQueueSummaryPayload {
  in_field_count: number;
  awaiting_review_count: number;
  recent_history_count: number;
  whisper_pending_count: number;
  total_pending_learning: number;
  total_open_pendencies: number;
  total_pending_whispers: number;
  observed_case_ids: string[];
}

interface ClientMesaQueueItemPayload {
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

interface ClientMesaQueueProjectionPayload {
  queue_summary: ClientMesaQueueSummaryPayload;
  queue_sections: {
    em_andamento: ClientMesaQueueItemPayload[];
    aguardando_avaliacao: ClientMesaQueueItemPayload[];
    historico: ClientMesaQueueItemPayload[];
  };
}

interface ClientMesaReviewerPayload {
  id: number;
  name: string;
  email: string;
  portal_label: string;
  active: boolean;
  blocked: boolean;
  temporary_password_active: boolean;
  last_login_at: string | null;
  last_login_label: string;
  last_activity_at: string | null;
  last_activity_label: string;
  session_count: number;
}

interface ClientMesaAuditPayload {
  id: number;
  portal: string;
  action: string;
  category: string;
  scope: string;
  summary: string;
  detail: string;
  actor_name: string;
  target_name: string;
  created_at: string | null;
  created_at_label: string;
}

export interface ClientMesaBackendProjection {
  contract_name: "ClientMesaDashboardProjectionV1";
  contract_version: string;
  payload: {
    tenant_summary: {
      company_id: number;
      company_name: string;
      active_plan: string;
      blocked: boolean;
      health_label: string;
      health_tone: string;
      health_text: string;
      total_reports: number;
    };
    reviewer_summary: {
      total: number;
      active: number;
      blocked: number;
      with_recent_sessions: number;
      first_access_pending: number;
    };
    review_status_totals: {
      drafts: number;
      waiting_review: number;
      approved: number;
      rejected: number;
      other_statuses: number;
    };
    reviewers: ClientMesaReviewerPayload[];
    recent_audit: ClientMesaAuditPayload[];
    audit_summary: {
      total?: number;
      categories?: Record<string, number>;
      scopes?: Record<string, number>;
    };
    review_queue_projection: {
      contract_name: "ReviewQueueDashboardProjectionV1";
      contract_version: string;
      payload: ClientMesaQueueProjectionPayload;
    };
  };
}

const DEFAULT_PYTHON_BACKEND_URL = "http://127.0.0.1:8000";

function resolvePythonBackendBaseUrl() {
  const configured = String(process.env["TARIEL_PYTHON_BACKEND_URL"] ?? "").trim();

  return configured || DEFAULT_PYTHON_BACKEND_URL;
}

function buildBackendUrl(pathname: string) {
  return new URL(pathname, resolvePythonBackendBaseUrl()).toString();
}

export async function fetchClientMesaBackendProjection(
  clientSession: AuthenticatedClientRequest,
): Promise<ClientMesaBackendProjection> {
  const response = await fetch(buildBackendUrl("/cliente/api/mesa/snapshot"), {
    method: "GET",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${clientSession.session.token}`,
      "X-Client-Request-Id": randomUUID(),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(
      `Python mesa snapshot failed (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return (await response.json()) as ClientMesaBackendProjection;
}
