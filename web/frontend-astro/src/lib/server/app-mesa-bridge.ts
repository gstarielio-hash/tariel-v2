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
