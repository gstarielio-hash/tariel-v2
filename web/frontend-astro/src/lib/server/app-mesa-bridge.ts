import { randomUUID } from "node:crypto";

import type { AuthenticatedAppRequest } from "@/lib/server/app-auth";

export interface AppMesaSummaryPayload {
  laudo_id: number;
  estado: string;
  permite_edicao: boolean;
  permite_reabrir: boolean;
  case_lifecycle_status: string;
  case_workflow_mode: string;
  active_owner_role: string;
  status_visual_label: string;
  allowed_next_lifecycle_statuses: string[];
  allowed_lifecycle_transitions: Array<Record<string, unknown>>;
  allowed_surface_actions: string[];
  human_validation_required?: boolean;
  laudo_card: {
    id: number;
    titulo: string;
    preview: string;
    pinado: boolean;
    data_iso: string;
    data_br: string;
    hora_br: string;
    tipo_template: string;
    status_revisao: string;
    status_card: string;
    status_card_label: string;
    permite_edicao: boolean;
    permite_exclusao: boolean;
    permite_reabrir: boolean;
    possui_historico: boolean;
    entry_mode_preference?: string | null;
    entry_mode_effective?: string | null;
    entry_mode_reason?: string | null;
    case_lifecycle_status: string;
    case_workflow_mode: string;
    active_owner_role: string;
    status_visual_label: string;
    allowed_next_lifecycle_statuses: string[];
    allowed_surface_actions: string[];
  } | null;
  resumo: {
    atualizado_em: string;
    total_mensagens: number;
    mensagens_nao_lidas: number;
    pendencias_abertas: number;
    pendencias_resolvidas: number;
    ultima_mensagem_id: number | null;
    ultima_mensagem_em: string;
    ultima_mensagem_preview: string;
    ultima_mensagem_tipo: string;
    ultima_mensagem_remetente_id: number | null;
    ultima_mensagem_client_message_id?: string;
  };
}

export interface AppInspectorTemplateOption {
  value: string;
  label: string;
  group_label?: string | null;
  runtime_template_code?: string | null;
}

export interface AppInspectorStatusPayload {
  estado: string;
  laudo_id: number | null;
  permite_edicao?: boolean;
  permite_reabrir?: boolean;
  status_card?: string | null;
  tipos_relatorio?: Record<string, string>;
  tipo_template_options?: AppInspectorTemplateOption[];
  catalog_governed_mode?: boolean;
  catalog_state?: string | null;
  catalog_permissions?: Record<string, unknown> | null;
  entry_mode_preference?: string | null;
  entry_mode_effective?: string | null;
  entry_mode_reason?: string | null;
  laudo_card?: Record<string, unknown> | null;
}

export interface AppMesaAttachmentPayload {
  id: number;
  nome: string;
  mime_type: string;
  categoria: string;
  tamanho_bytes?: number;
  eh_imagem?: boolean;
}

export interface AppMesaMessagePayload {
  id: number;
  laudo_id?: number;
  tipo: string;
  item_kind: string;
  message_kind: string;
  pendency_state: string;
  texto: string;
  remetente_id: number | null;
  data: string;
  criado_em_iso?: string;
  lida?: boolean;
  resolvida_em?: string;
  resolvida_em_label?: string;
  resolvida_por_nome?: string | null;
  referencia_mensagem_id?: number;
  anexos?: AppMesaAttachmentPayload[];
  operational_context?: Record<string, unknown> | null;
}

export interface AppMesaMessagesPayload {
  laudo_id: number;
  itens: AppMesaMessagePayload[];
  cursor_proximo: number | null;
  cursor_ultimo_id?: number | null;
  tem_mais: boolean;
  estado?: string;
  permite_edicao?: boolean;
  permite_reabrir?: boolean;
  laudo_card?: Record<string, unknown> | null;
  resumo?: Record<string, unknown> | null;
}

export interface AppMesaReplyPayload {
  laudo_id: number;
  mensagem: AppMesaMessagePayload;
  laudo_card?: Record<string, unknown> | null;
  estado?: string;
  permite_edicao?: boolean;
  permite_reabrir?: boolean;
  resumo?: Record<string, unknown> | null;
  request_id?: string;
  idempotent_replay?: boolean;
}

export interface AppMesaPendencyPayload {
  ok: boolean;
  laudo_id: number;
  mensagem_id: number;
  lida: boolean;
  resolvida_por_id: number | null;
  resolvida_por_nome: string | null;
  resolvida_em: string;
}

export interface AppInspectionStartPayload {
  success: boolean;
  laudo_id: number;
  hash?: string;
  message?: string;
  estado: string;
  tipo_template?: string;
  catalog_governed_mode?: boolean;
  catalog_selection_token?: string | null;
  catalog_family_key?: string | null;
  catalog_variant_key?: string | null;
  entry_mode_preference?: string | null;
  entry_mode_effective?: string | null;
  entry_mode_reason?: string | null;
  laudo_card?: Record<string, unknown> | null;
}

export interface AppInspectionPreviewInput {
  diagnostico: string;
  inspetor: string;
  empresa?: string;
  setor?: string;
  data?: string;
  laudoId?: number | null;
  tipoTemplate?: string | null;
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

async function fetchAppMesaBackend(
  appSession: AuthenticatedAppRequest,
  pathname: string,
  init: {
    method?: string;
    body?: BodyInit | FormData | Record<string, unknown>;
    accept?: string;
  } = {},
) {
  const headers = new Headers({
    Accept: init.accept ?? "application/json",
    Authorization: `Bearer ${appSession.session.token}`,
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

async function expectAppMesaJson<T>(
  appSession: AuthenticatedAppRequest,
  pathname: string,
  init: {
    method?: string;
    body?: BodyInit | FormData | Record<string, unknown>;
    accept?: string;
    errorPrefix: string;
  },
): Promise<T> {
  const response = await fetchAppMesaBackend(appSession, pathname, init);

  if (!response.ok) {
    const detail = await extractBackendError(response);
    throw new Error(
      `${init.errorPrefix} (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return (await response.json()) as T;
}

export async function fetchAppMesaSummary(
  appSession: AuthenticatedAppRequest,
  laudoId: number,
): Promise<AppMesaSummaryPayload> {
  const response = await fetch(buildBackendUrl(`/app/api/laudo/${laudoId}/mesa/resumo`), {
    method: "GET",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${appSession.session.token}`,
      "X-Client-Request-Id": randomUUID(),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await extractBackendError(response);
    throw new Error(
      `Python inspector mesa summary failed (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return (await response.json()) as AppMesaSummaryPayload;
}

export async function fetchAppMesaMessages(
  appSession: AuthenticatedAppRequest,
  laudoId: number,
): Promise<AppMesaMessagesPayload> {
  const response = await fetch(buildBackendUrl(`/app/api/laudo/${laudoId}/mesa/mensagens`), {
    method: "GET",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${appSession.session.token}`,
      "X-Client-Request-Id": randomUUID(),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await extractBackendError(response);
    throw new Error(
      `Python inspector mesa messages failed (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return (await response.json()) as AppMesaMessagesPayload;
}

export async function fetchAppInspectorStatus(
  appSession: AuthenticatedAppRequest,
): Promise<AppInspectorStatusPayload> {
  return expectAppMesaJson<AppInspectorStatusPayload>(appSession, "/app/api/laudo/status", {
    method: "GET",
    errorPrefix: "Python inspector status failed",
  });
}

export async function replyToAppMesa(
  appSession: AuthenticatedAppRequest,
  input: {
    laudoId: number;
    texto: string;
    referenciaMensagemId?: number | null;
  },
): Promise<AppMesaReplyPayload> {
  const normalizedText = String(input.texto ?? "").trim();

  if (!normalizedText) {
    throw new Error("Escreva uma resposta para a mesa.");
  }

  return expectAppMesaJson<AppMesaReplyPayload>(
    appSession,
    `/app/api/laudo/${input.laudoId}/mesa/mensagem`,
    {
      method: "POST",
      body: {
      texto: normalizedText,
      referencia_mensagem_id: input.referenciaMensagemId ?? null,
      },
      errorPrefix: "Python inspector mesa reply failed",
    },
  );
}

export async function startAppInspection(
  appSession: AuthenticatedAppRequest,
  input: {
    tipoTemplate: string;
    entryModePreference?: string | null;
    cliente?: string | null;
    unidade?: string | null;
    localInspecao?: string | null;
    objetivo?: string | null;
    nomeInspecao?: string | null;
  },
): Promise<AppInspectionStartPayload> {
  const tipoTemplate = String(input.tipoTemplate ?? "").trim();

  if (!tipoTemplate) {
    throw new Error("Selecione um modelo tecnico para iniciar a inspecao.");
  }

  const formData = new FormData();
  formData.set("tipo_template", tipoTemplate);
  formData.set("tipotemplate", tipoTemplate);

  const entryModePreference = String(input.entryModePreference ?? "").trim();
  if (entryModePreference) {
    formData.set("entry_mode_preference", entryModePreference);
  }

  const optionalFields = {
    cliente: input.cliente,
    unidade: input.unidade,
    local_inspecao: input.localInspecao,
    objetivo: input.objetivo,
    nome_inspecao: input.nomeInspecao,
  } as const;

  for (const [field, value] of Object.entries(optionalFields)) {
    const normalized = String(value ?? "").trim();
    if (normalized) {
      formData.set(field, normalized);
    }
  }

  return expectAppMesaJson<AppInspectionStartPayload>(appSession, "/app/api/laudo/iniciar", {
    method: "POST",
    body: formData,
    errorPrefix: "Python inspector start inspection failed",
  });
}

export async function fetchAppInspectionPreviewResponse(
  appSession: AuthenticatedAppRequest,
  input: AppInspectionPreviewInput,
) {
  const diagnostico = String(input.diagnostico ?? "").trim();

  if (!diagnostico) {
    throw new Error("Ainda nao ha diagnostico suficiente para gerar a pre-visualizacao.");
  }

  const response = await fetchAppMesaBackend(appSession, "/app/api/gerar_pdf", {
    method: "POST",
    body: {
      diagnostico,
      inspetor: String(input.inspetor ?? "").trim() || "Inspetor",
      empresa: String(input.empresa ?? "").trim(),
      setor: String(input.setor ?? "").trim() || "geral",
      data: String(input.data ?? "").trim(),
      laudo_id: input.laudoId ?? null,
      tipo_template: String(input.tipoTemplate ?? "").trim(),
    },
    accept: "application/pdf",
  });

  if (!response.ok) {
    const detail = await extractBackendError(response);
    throw new Error(
      `Python inspector preview failed (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return response;
}

export async function replyToAppMesaWithAttachment(
  appSession: AuthenticatedAppRequest,
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

  return expectAppMesaJson<AppMesaReplyPayload>(
    appSession,
    `/app/api/laudo/${input.laudoId}/mesa/anexo`,
    {
      method: "POST",
      body: formData,
      errorPrefix: "Python inspector mesa attachment reply failed",
    },
  );
}

export async function updateAppMesaPendency(
  appSession: AuthenticatedAppRequest,
  input: {
    laudoId: number;
    mensagemId: number;
    lida: boolean;
  },
): Promise<AppMesaPendencyPayload> {
  const response = await fetch(
    buildBackendUrl(`/app/api/laudo/${input.laudoId}/pendencias/${input.mensagemId}`),
    {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${appSession.session.token}`,
        "Content-Type": "application/json",
        "X-Client-Request-Id": randomUUID(),
      },
      body: JSON.stringify({
        lida: input.lida,
      }),
      cache: "no-store",
    },
  );

  if (!response.ok) {
    const detail = await extractBackendError(response);
    throw new Error(
      `Python inspector mesa pendency failed (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return (await response.json()) as AppMesaPendencyPayload;
}

export async function fetchAppMesaAttachmentResponse(
  appSession: AuthenticatedAppRequest,
  input: {
    laudoId: number;
    anexoId: number;
  },
) {
  const response = await fetchAppMesaBackend(
    appSession,
    `/app/api/laudo/${input.laudoId}/mesa/anexos/${input.anexoId}`,
    {
      accept: "*/*",
    },
  );

  if (!response.ok) {
    const detail = await extractBackendError(response);
    throw new Error(
      `Python inspector mesa attachment failed (${response.status} ${response.statusText})${detail ? `: ${detail}` : ""}`,
    );
  }

  return response;
}
