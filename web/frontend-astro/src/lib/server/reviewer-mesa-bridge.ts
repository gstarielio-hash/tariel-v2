import { randomUUID } from "node:crypto";

import type { AuthenticatedReviewerRequest } from "@/lib/server/reviewer-auth";

export interface ReviewerMesaAttachmentPayload {
  id: number;
  nome: string;
  mime_type: string;
  categoria: string;
  tamanho_bytes: number;
  eh_imagem: boolean;
  url?: string;
}

export interface ReviewerMesaMessagePayload {
  id: number;
  tipo: string;
  item_kind: string;
  message_kind: string;
  pendency_state: string;
  texto: string;
  data: string;
  is_whisper: boolean;
  remetente_id: number | null;
  referencia_mensagem_id?: number | null;
  anexos?: ReviewerMesaAttachmentPayload[];
  operational_context?: Record<string, unknown> | null;
}

export interface ReviewerMesaMessagesPayload {
  itens: ReviewerMesaMessagePayload[];
  tem_mais: boolean;
  cursor_proximo: number | null;
}

export interface ReviewerMesaPackageItemPayload {
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
  anexos: ReviewerMesaAttachmentPayload[];
}

export interface ReviewerMesaPackageReviewPayload {
  numero_versao: number;
  origem: string;
  resumo: string | null;
  confianca_geral: string | null;
  criado_em: string;
}

export interface ReviewerMesaPackageSectionPayload {
  key: string;
  title: string;
  status: string;
  summary: string | null;
  diff_short: string | null;
  filled_fields: number;
  total_fields: number;
}

export interface ReviewerMesaCoverageItemPayload {
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

export interface ReviewerMesaPackagePayload {
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
    sections: ReviewerMesaPackageSectionPayload[];
  } | null;
  coverage_map?: {
    total_required: number;
    total_collected: number;
    total_accepted: number;
    total_missing: number;
    total_irregular: number;
    final_validation_mode: string | null;
    items: ReviewerMesaCoverageItemPayload[];
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
  pendencias_abertas: ReviewerMesaPackageItemPayload[];
  pendencias_resolvidas_recentes: ReviewerMesaPackageItemPayload[];
  whispers_recentes: ReviewerMesaPackageItemPayload[];
  revisoes_recentes: ReviewerMesaPackageReviewPayload[];
}

export interface ReviewerMesaDecisionResponsePayload {
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

export interface ReviewerMesaReplyPayload {
  success: boolean;
  mensagem?: ReviewerMesaMessagePayload;
}

export interface ReviewerMesaPendencyPayload {
  success: boolean;
  mensagem_id: number;
  lida: boolean;
  resolvida_por_id: number | null;
  resolvida_por_nome: string | null;
  resolvida_em: string | null;
  pendencias_abertas: number;
}

export interface ReviewerMesaWhispersReadPayload {
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

async function fetchReviewerMesaBackend(
  reviewerSession: AuthenticatedReviewerRequest,
  pathname: string,
  init: {
    method?: string;
    body?: BodyInit | FormData | Record<string, unknown>;
    accept?: string;
  } = {},
) {
  const headers = new Headers({
    Accept: init.accept ?? "application/json",
    Authorization: `Bearer ${reviewerSession.session.token}`,
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

async function expectReviewerMesaJson<T>(
  reviewerSession: AuthenticatedReviewerRequest,
  pathname: string,
  init: {
    method?: string;
    body?: BodyInit | FormData | Record<string, unknown>;
    accept?: string;
    errorPrefix: string;
  },
): Promise<T> {
  const response = await fetchReviewerMesaBackend(reviewerSession, pathname, init);

  if (!response.ok) {
    const detail = await extractBackendError(response);
    throw new Error(
      `${init.errorPrefix} (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return (await response.json()) as T;
}

export async function fetchReviewerMesaMessages(
  reviewerSession: AuthenticatedReviewerRequest,
  laudoId: number,
): Promise<ReviewerMesaMessagesPayload> {
  return expectReviewerMesaJson<ReviewerMesaMessagesPayload>(
    reviewerSession,
    `/revisao/api/laudo/${laudoId}/mensagens`,
    {
      errorPrefix: "Python reviewer mesa messages failed",
    },
  );
}

export async function fetchReviewerMesaPackage(
  reviewerSession: AuthenticatedReviewerRequest,
  laudoId: number,
): Promise<ReviewerMesaPackagePayload> {
  return expectReviewerMesaJson<ReviewerMesaPackagePayload>(
    reviewerSession,
    `/revisao/api/laudo/${laudoId}/pacote`,
    {
      errorPrefix: "Python reviewer mesa package failed",
    },
  );
}

export async function replyToReviewerMesa(
  reviewerSession: AuthenticatedReviewerRequest,
  input: {
    laudoId: number;
    texto: string;
    referenciaMensagemId?: number | null;
  },
) {
  return expectReviewerMesaJson<ReviewerMesaReplyPayload>(
    reviewerSession,
    `/revisao/api/laudo/${input.laudoId}/responder`,
    {
      method: "POST",
      body: {
        texto: input.texto,
        referencia_mensagem_id: input.referenciaMensagemId ?? null,
      },
      errorPrefix: "Python reviewer mesa reply failed",
    },
  );
}

export async function replyToReviewerMesaWithAttachment(
  reviewerSession: AuthenticatedReviewerRequest,
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

  return expectReviewerMesaJson<ReviewerMesaReplyPayload>(
    reviewerSession,
    `/revisao/api/laudo/${input.laudoId}/responder-anexo`,
    {
      method: "POST",
      body: formData,
      errorPrefix: "Python reviewer mesa attachment reply failed",
    },
  );
}

export async function reviewReviewerMesaCase(
  reviewerSession: AuthenticatedReviewerRequest,
  input: {
    laudoId: number;
    acao: "aprovar" | "rejeitar";
    motivo?: string;
  },
) {
  const formData = new FormData();
  formData.set("acao", input.acao);
  if (input.motivo?.trim()) {
    formData.set("motivo", input.motivo.trim());
  }

  return expectReviewerMesaJson<ReviewerMesaDecisionResponsePayload>(
    reviewerSession,
    `/revisao/api/laudo/${input.laudoId}/avaliar`,
    {
      method: "POST",
      body: formData,
      errorPrefix: "Python reviewer mesa decision failed",
    },
  );
}

export async function updateReviewerMesaPendency(
  reviewerSession: AuthenticatedReviewerRequest,
  input: {
    laudoId: number;
    mensagemId: number;
    lida: boolean;
  },
) {
  return expectReviewerMesaJson<ReviewerMesaPendencyPayload>(
    reviewerSession,
    `/revisao/api/laudo/${input.laudoId}/pendencias/${input.mensagemId}`,
    {
      method: "PATCH",
      body: {
        lida: input.lida,
      },
      errorPrefix: "Python reviewer mesa pendency failed",
    },
  );
}

export async function markReviewerMesaWhispersRead(
  reviewerSession: AuthenticatedReviewerRequest,
  laudoId: number,
) {
  return expectReviewerMesaJson<ReviewerMesaWhispersReadPayload>(
    reviewerSession,
    `/revisao/api/laudo/${laudoId}/marcar-whispers-lidos`,
    {
      method: "POST",
      body: new FormData(),
      errorPrefix: "Python reviewer mesa whispers read failed",
    },
  );
}

export async function fetchReviewerMesaAttachmentResponse(
  reviewerSession: AuthenticatedReviewerRequest,
  input: {
    laudoId: number;
    anexoId: number;
  },
) {
  const response = await fetchReviewerMesaBackend(
    reviewerSession,
    `/revisao/api/laudo/${input.laudoId}/mesa/anexos/${input.anexoId}`,
    {
      accept: "*/*",
    },
  );

  if (!response.ok) {
    const detail = await extractBackendError(response);
    throw new Error(
      `Python reviewer mesa attachment failed (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return response;
}
