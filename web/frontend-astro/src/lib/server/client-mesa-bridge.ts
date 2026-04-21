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

export interface ClientMesaAttachmentPayload {
  id: number;
  nome: string;
  mime_type: string;
  categoria: string;
  tamanho_bytes: number;
  eh_imagem: boolean;
  url?: string;
}

export interface ClientMesaMessagesPayload {
  itens: ClientMesaMessagePayload[];
  tem_mais: boolean;
  cursor_proximo: number | null;
}

export interface ClientMesaMessagePayload {
  id: number;
  tipo: string;
  item_kind: string;
  message_kind: string;
  pendency_state: string;
  texto: string;
  data: string;
  is_whisper: boolean;
  remetente_id: number | null;
  referencia_mensagem_id?: number;
  anexos?: ClientMesaAttachmentPayload[];
  operational_context?: Record<string, unknown> | null;
}

export interface ClientMesaPackageSectionPayload {
  key: string;
  title: string;
  status: string;
  summary: string | null;
  diff_short: string | null;
  filled_fields: number;
  total_fields: number;
}

export interface ClientMesaPackageCoverageItemPayload {
  evidence_key: string;
  title: string;
  kind: string;
  status: string;
  required: boolean;
  source_status: string | null;
  operational_status: string | null;
  mesa_status: string | null;
  component_type: string | null;
  view_angle: string | null;
  quality_score: number | null;
  coherence_score: number | null;
  replacement_evidence_key: string | null;
  summary: string | null;
  failure_reasons: string[];
}

export interface ClientMesaPackageItemPayload {
  id: number;
  tipo: string;
  item_kind: string;
  message_kind: string;
  pendency_state: string;
  texto: string;
  criado_em: string;
  remetente_id: number | null;
  lida: boolean;
  referencia_mensagem_id: number | null;
  resolvida_em: string | null;
  resolvida_por_id: number | null;
  resolvida_por_nome: string | null;
  anexos: ClientMesaAttachmentPayload[];
}

export interface ClientMesaPackageReviewPayload {
  numero_versao: number;
  origem: string;
  resumo: string | null;
  confianca_geral: string | null;
  criado_em: string;
}

export interface ClientMesaPackagePayload {
  laudo_id: number;
  codigo_hash: string;
  tipo_template: string;
  setor_industrial: string;
  status_revisao: string;
  status_conformidade: string;
  case_status: string;
  case_lifecycle_status: string;
  case_workflow_mode: string;
  active_owner_role: string;
  allowed_next_lifecycle_statuses: string[];
  allowed_surface_actions: string[];
  status_visual_label: string;
  criado_em: string;
  atualizado_em: string | null;
  tempo_em_campo_minutos: number;
  ultima_interacao_em: string | null;
  inspetor_id: number | null;
  revisor_id: number | null;
  parecer_ia: string | null;
  human_override_summary?: {
    latest?: {
      actor_name?: string;
      reason?: string;
      applied_at?: string;
    };
  } | null;
  resumo_mensagens: {
    total: number;
    inspetor: number;
    ia: number;
    mesa: number;
    sistema_outros: number;
  };
  resumo_evidencias: {
    total: number;
    textuais: number;
    fotos: number;
    documentos: number;
  };
  resumo_pendencias: {
    total: number;
    abertas: number;
    resolvidas: number;
  };
  documento_estruturado?: {
    schema_type: string;
    family_key: string | null;
    family_label: string | null;
    summary: string | null;
    review_notes: string | null;
    sections: ClientMesaPackageSectionPayload[];
  } | null;
  coverage_map?: {
    total_required: number;
    total_collected: number;
    total_accepted: number;
    total_missing: number;
    total_irregular: number;
    final_validation_mode: string | null;
    items: ClientMesaPackageCoverageItemPayload[];
  } | null;
  anexo_pack?: {
    total_items: number;
    total_required: number;
    total_present: number;
    missing_required_count: number;
    document_count: number;
    image_count: number;
    virtual_count: number;
    ready_for_issue: boolean;
    missing_items: string[];
  } | null;
  verificacao_publica?: {
    verification_url: string;
    hash_short: string;
    status_visual_label: string | null;
    approved_at: string | null;
  } | null;
  emissao_oficial?: {
    issue_status: string;
    issue_status_label: string;
    ready_for_issue: boolean;
    blocker_count: number;
    already_issued: boolean;
    reissue_recommended: boolean;
    issue_action_label: string | null;
    issue_action_enabled: boolean;
    verification_url: string | null;
  } | null;
  tenant_access_policy?: Record<string, unknown> | null;
  pendencias_abertas: ClientMesaPackageItemPayload[];
  pendencias_resolvidas_recentes: ClientMesaPackageItemPayload[];
  whispers_recentes: ClientMesaPackageItemPayload[];
  revisoes_recentes: ClientMesaPackageReviewPayload[];
}

export interface ClientMesaDecisionResponsePayload {
  success: boolean;
  laudo_id: number;
  acao: string;
  status_revisao: string;
  case_status: string;
  case_lifecycle_status: string;
  case_workflow_mode: string;
  active_owner_role: string;
  allowed_next_lifecycle_statuses: string[];
  allowed_surface_actions: string[];
  status_visual_label: string;
  motivo: string;
  idempotent_replay: boolean;
}

export interface ClientMesaReplyPayload {
  success: boolean;
  mensagem?: ClientMesaMessagePayload;
}

export interface ClientMesaPendencyPayload {
  success: boolean;
  mensagem_id: number;
  lida: boolean;
  resolvida_por_id: number | null;
  resolvida_por_nome: string | null;
  resolvida_em: string | null;
  pendencias_abertas: number;
}

export interface ClientMesaWhispersReadPayload {
  success: boolean;
  marcadas: number;
}

const DEFAULT_PYTHON_BACKEND_URL = "http://127.0.0.1:8000";

function resolvePythonBackendBaseUrl() {
  const configured = String(process.env["TARIEL_PYTHON_BACKEND_URL"] ?? "").trim();
  return configured || DEFAULT_PYTHON_BACKEND_URL;
}

function buildBackendUrl(pathname: string) {
  return new URL(pathname, resolvePythonBackendBaseUrl()).toString();
}

function isFormDataBody(body: unknown): body is FormData {
  return typeof FormData !== "undefined" && body instanceof FormData;
}

function isPlainJsonBody(body: unknown): body is Record<string, unknown> {
  return Boolean(body) && typeof body === "object" && !isFormDataBody(body) && !(body instanceof URLSearchParams);
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

async function fetchClientMesaBackend(
  clientSession: AuthenticatedClientRequest,
  pathname: string,
  init: {
    method?: string;
    body?: BodyInit | FormData | Record<string, unknown>;
    accept?: string;
  } = {},
) {
  const headers = new Headers({
    Accept: init.accept ?? "application/json",
    Authorization: `Bearer ${clientSession.session.token}`,
    "X-Client-Request-Id": randomUUID(),
  });

  let body: BodyInit | undefined;
  if (isPlainJsonBody(init.body)) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.body);
  } else if (init.body !== undefined) {
    body = init.body;
  }

  return fetch(buildBackendUrl(pathname), {
    method: init.method ?? "GET",
    headers,
    body,
    cache: "no-store",
  });
}

async function expectClientMesaJson<T>(
  clientSession: AuthenticatedClientRequest,
  pathname: string,
  init: {
    method?: string;
    body?: BodyInit | FormData | Record<string, unknown>;
    accept?: string;
    errorPrefix: string;
  },
): Promise<T> {
  const response = await fetchClientMesaBackend(clientSession, pathname, init);

  if (!response.ok) {
    const detail = await extractBackendError(response);
    throw new Error(
      `${init.errorPrefix} (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return (await response.json()) as T;
}

export async function fetchClientMesaBackendProjection(
  clientSession: AuthenticatedClientRequest,
): Promise<ClientMesaBackendProjection> {
  return expectClientMesaJson<ClientMesaBackendProjection>(clientSession, "/cliente/api/mesa/snapshot", {
    errorPrefix: "Python mesa snapshot failed",
  });
}

export async function fetchClientMesaMessages(
  clientSession: AuthenticatedClientRequest,
  laudoId: number,
): Promise<ClientMesaMessagesPayload> {
  return expectClientMesaJson<ClientMesaMessagesPayload>(
    clientSession,
    `/cliente/api/mesa/laudos/${laudoId}/mensagens`,
    {
      errorPrefix: "Python mesa messages failed",
    },
  );
}

export async function fetchClientMesaPackage(
  clientSession: AuthenticatedClientRequest,
  laudoId: number,
): Promise<ClientMesaPackagePayload> {
  return expectClientMesaJson<ClientMesaPackagePayload>(
    clientSession,
    `/cliente/api/mesa/laudos/${laudoId}/pacote`,
    {
      errorPrefix: "Python mesa package failed",
    },
  );
}

export async function replyToClientMesa(
  clientSession: AuthenticatedClientRequest,
  input: {
    laudoId: number;
    texto: string;
    referenciaMensagemId?: number | null;
  },
) {
  return expectClientMesaJson<ClientMesaReplyPayload>(
    clientSession,
    `/cliente/api/mesa/laudos/${input.laudoId}/responder`,
    {
      method: "POST",
      body: {
        texto: input.texto,
        referencia_mensagem_id: input.referenciaMensagemId ?? null,
      },
      errorPrefix: "Python mesa reply failed",
    },
  );
}

export async function replyToClientMesaWithAttachment(
  clientSession: AuthenticatedClientRequest,
  input: {
    laudoId: number;
    arquivo: File;
    texto?: string;
    referenciaMensagemId?: number | null;
  },
) {
  const formData = new FormData();
  formData.set("arquivo", input.arquivo);
  if (input.texto?.trim()) {
    formData.set("texto", input.texto.trim());
  }
  if (input.referenciaMensagemId) {
    formData.set("referencia_mensagem_id", String(input.referenciaMensagemId));
  }

  return expectClientMesaJson<ClientMesaReplyPayload>(
    clientSession,
    `/cliente/api/mesa/laudos/${input.laudoId}/responder-anexo`,
    {
      method: "POST",
      body: formData,
      errorPrefix: "Python mesa attachment reply failed",
    },
  );
}

export async function reviewClientMesaCase(
  clientSession: AuthenticatedClientRequest,
  input: {
    laudoId: number;
    acao: "aprovar" | "rejeitar";
    motivo?: string;
  },
) {
  return expectClientMesaJson<ClientMesaDecisionResponsePayload>(
    clientSession,
    `/cliente/api/mesa/laudos/${input.laudoId}/avaliar`,
    {
      method: "POST",
      body: {
        acao: input.acao,
        motivo: input.motivo ?? "",
      },
      errorPrefix: "Python mesa decision failed",
    },
  );
}

export async function updateClientMesaPendency(
  clientSession: AuthenticatedClientRequest,
  input: {
    laudoId: number;
    mensagemId: number;
    lida: boolean;
  },
) {
  return expectClientMesaJson<ClientMesaPendencyPayload>(
    clientSession,
    `/cliente/api/mesa/laudos/${input.laudoId}/pendencias/${input.mensagemId}`,
    {
      method: "PATCH",
      body: {
        lida: input.lida,
      },
      errorPrefix: "Python mesa pendency update failed",
    },
  );
}

export async function markClientMesaWhispersRead(
  clientSession: AuthenticatedClientRequest,
  laudoId: number,
) {
  return expectClientMesaJson<ClientMesaWhispersReadPayload>(
    clientSession,
    `/cliente/api/mesa/laudos/${laudoId}/marcar-whispers-lidos`,
    {
      method: "POST",
      errorPrefix: "Python mesa whisper sync failed",
    },
  );
}

export async function fetchClientMesaAttachmentResponse(
  clientSession: AuthenticatedClientRequest,
  input: {
    laudoId: number;
    anexoId: number;
  },
) {
  const response = await fetchClientMesaBackend(
    clientSession,
    `/cliente/api/mesa/laudos/${input.laudoId}/anexos/${input.anexoId}`,
    {
      accept: "*/*",
    },
  );

  if (!response.ok) {
    const detail = await extractBackendError(response);
    throw new Error(
      `Python mesa attachment failed (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return response;
}
