import type {
  MobileChatMode,
  MobileChatMessage,
  MobileChatSendResult,
  MobileDocumentUploadResponse,
  MobileGuidedInspectionDraftPayload,
  MobileGuidedInspectionMessageContextPayload,
  MobileGuidedInspectionDraftUpdateResponse,
  MobileLaudoFinalizeResponse,
  MobileLaudoListResponse,
  MobileLaudoMensagensResponse,
  MobileLaudoReopenRequest,
  MobileQualityGateOverridePayload,
  MobileQualityGateResponse,
  MobileLaudoStatusResponse,
} from "../types/mobile";
import { normalizarQualityGateResponse } from "../features/chat/qualityGateHelpers";
import {
  buildApiUrl,
  construirHeaders,
  extrairMensagemErro,
  fetchComObservabilidade,
  inferirMimeType,
  lerJsonSeguro,
} from "./apiCore";

function extrairEventosSse(raw: string): Record<string, unknown>[] {
  return raw
    .split(/\r?\n\r?\n/g)
    .flatMap((bloco) =>
      bloco
        .split(/\r?\n/g)
        .map((linha) => linha.trim())
        .filter((linha) => linha.startsWith("data:"))
        .map((linha) => linha.slice(5).trim()),
    )
    .filter((linha) => linha && linha !== "[FIM]")
    .flatMap((linha) => {
      try {
        const payload = JSON.parse(linha);
        return payload && typeof payload === "object"
          ? [payload as Record<string, unknown>]
          : [];
      } catch {
        return [];
      }
    });
}

function normalizarModoChat(modo: unknown): MobileChatMode {
  const value = String(modo || "")
    .trim()
    .toLowerCase();
  if (value === "curto") {
    return "curto";
  }
  if (value === "deep_research" || value === "deepresearch") {
    return "deep_research";
  }
  return "detalhado";
}

function extrairCitacoes(payload: unknown): Array<Record<string, unknown>> {
  if (!Array.isArray(payload)) {
    return [];
  }
  return payload.filter(
    (item): item is Record<string, unknown> =>
      Boolean(item) && typeof item === "object" && !Array.isArray(item),
  );
}

function extrairConfiancaIa(payload: unknown): Record<string, unknown> | null {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return null;
  }
  return payload as Record<string, unknown>;
}

function normalizarRespostaFinalizacaoLaudo(
  payload: MobileLaudoFinalizeResponse,
): MobileLaudoFinalizeResponse {
  return {
    ...payload,
    permite_edicao:
      payload.permite_edicao ??
      payload.laudo_card?.permite_edicao ??
      Boolean(payload.allowed_surface_actions?.includes("chat_finalize")),
    permite_reabrir:
      payload.permite_reabrir ?? payload.laudo_card?.permite_reabrir ?? false,
    estado:
      payload.estado || payload.laudo_card?.status_revisao || "aguardando",
    status_card:
      payload.status_card || payload.laudo_card?.status_card || "aguardando",
  };
}

export class MobileQualityGateError extends Error {
  payload: MobileQualityGateResponse;

  stage: "load" | "finalize";

  constructor(
    payload: MobileQualityGateResponse,
    stage: "load" | "finalize",
    fallbackMessage: string,
  ) {
    super(payload.mensagem || fallbackMessage);
    this.name = "MobileQualityGateError";
    this.payload = payload;
    this.stage = stage;
  }
}

export async function carregarLaudosMobile(
  accessToken: string,
): Promise<MobileLaudoListResponse> {
  const response = await fetchComObservabilidade(
    "mobile_laudos_list",
    buildApiUrl("/app/api/mobile/laudos"),
    {
      method: "GET",
      headers: construirHeaders(accessToken),
    },
  );

  const payload = await lerJsonSeguro<
    MobileLaudoListResponse | { detail?: string }
  >(response);
  if (!response.ok || !payload || !("itens" in payload)) {
    throw new Error(
      extrairMensagemErro(
        payload,
        "Não foi possível carregar os laudos do inspetor.",
      ),
    );
  }

  return payload;
}

export async function carregarStatusLaudo(
  accessToken: string,
): Promise<MobileLaudoStatusResponse> {
  const response = await fetchComObservabilidade(
    "laudo_status",
    buildApiUrl("/app/api/laudo/status"),
    {
      method: "GET",
      headers: construirHeaders(accessToken),
    },
  );

  const payload = await lerJsonSeguro<
    MobileLaudoStatusResponse | { detail?: string }
  >(response);
  if (!response.ok || !payload || !("estado" in payload)) {
    throw new Error(
      extrairMensagemErro(
        payload,
        "Não foi possível carregar o status do laudo.",
      ),
    );
  }

  return payload;
}

export async function carregarMensagensLaudo(
  accessToken: string,
  laudoId: number,
): Promise<MobileLaudoMensagensResponse> {
  const response = await fetchComObservabilidade(
    "laudo_mensagens_list",
    buildApiUrl(`/app/api/laudo/${laudoId}/mensagens`),
    {
      method: "GET",
      headers: construirHeaders(accessToken),
    },
  );

  const payload = await lerJsonSeguro<
    MobileLaudoMensagensResponse | { detail?: string }
  >(response);
  if (!response.ok || !payload || !("itens" in payload)) {
    throw new Error(
      extrairMensagemErro(
        payload,
        "Não foi possível carregar o histórico do laudo.",
      ),
    );
  }

  return payload;
}

export async function carregarGateQualidadeLaudoMobile(
  accessToken: string,
  laudoId: number,
): Promise<MobileQualityGateResponse> {
  const response = await fetchComObservabilidade(
    "laudo_quality_gate",
    buildApiUrl(`/app/api/laudo/${laudoId}/gate-qualidade`),
    {
      method: "GET",
      headers: construirHeaders(accessToken),
    },
  );

  const payload = await lerJsonSeguro<
    MobileQualityGateResponse | { detail?: string }
  >(response);
  const gatePayload = normalizarQualityGateResponse(payload);

  if (gatePayload) {
    return gatePayload;
  }

  throw new Error(
    extrairMensagemErro(
      payload,
      "Não foi possível validar o quality gate deste caso.",
    ),
  );
}

export async function salvarGuidedInspectionDraftMobile(
  accessToken: string,
  laudoId: number,
  payload: {
    guided_inspection_draft: MobileGuidedInspectionDraftPayload | null;
  },
): Promise<MobileGuidedInspectionDraftUpdateResponse> {
  const response = await fetchComObservabilidade(
    "mobile_guided_inspection_draft_save",
    buildApiUrl(`/app/api/mobile/laudo/${laudoId}/guided-inspection-draft`),
    {
      method: "PUT",
      headers: construirHeaders(accessToken, {
        "Content-Type": "application/json",
      }),
      body: JSON.stringify(payload),
    },
  );

  const jsonPayload = await lerJsonSeguro<
    MobileGuidedInspectionDraftUpdateResponse | { detail?: string }
  >(response);
  if (!response.ok || !jsonPayload || !("ok" in jsonPayload)) {
    throw new Error(
      extrairMensagemErro(
        jsonPayload,
        "Nao foi possivel salvar o draft guiado do laudo.",
      ),
    );
  }

  return jsonPayload;
}

export async function enviarMensagemChatMobile(
  accessToken: string,
  payload: {
    mensagem: string;
    preferenciasIaMobile?: string;
    dadosImagem?: string;
    setor?: string;
    textoDocumento?: string;
    nomeDocumento?: string;
    laudoId?: number | null;
    modo?: MobileChatMode | string;
    guidedInspectionDraft?: MobileGuidedInspectionDraftPayload | null;
    guidedInspectionContext?: MobileGuidedInspectionMessageContextPayload | null;
    historico?:
      | Array<{ papel: "usuario" | "assistente"; texto: string }>
      | MobileChatMessage[];
  },
): Promise<MobileChatSendResult> {
  const modo = normalizarModoChat(payload.modo);
  const response = await fetchComObservabilidade(
    "chat_send",
    buildApiUrl("/app/api/chat"),
    {
      method: "POST",
      headers: construirHeaders(accessToken, {
        "Content-Type": "application/json",
      }),
      body: JSON.stringify({
        mensagem: payload.mensagem,
        preferencias_ia_mobile: payload.preferenciasIaMobile || "",
        dados_imagem: payload.dadosImagem || "",
        setor: (payload.setor || "geral").trim() || "geral",
        texto_documento: payload.textoDocumento || "",
        nome_documento: payload.nomeDocumento || "",
        laudo_id: payload.laudoId ?? undefined,
        guided_inspection_draft: payload.guidedInspectionDraft || undefined,
        guided_inspection_context: payload.guidedInspectionContext || undefined,
        modo,
        historico: (payload.historico || []).map((item) => ({
          papel: item.papel,
          texto: item.texto,
        })),
      }),
    },
  );

  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) {
    const erroJson = await lerJsonSeguro<{ detail?: string }>(response);
    throw new Error(
      extrairMensagemErro(
        erroJson,
        "Não foi possível enviar a mensagem do chat.",
      ),
    );
  }

  if (contentType.includes("application/json")) {
    const jsonPayload =
      (await lerJsonSeguro<Record<string, unknown>>(response)) || {};
    return {
      laudoId:
        typeof jsonPayload.laudo_id === "number"
          ? jsonPayload.laudo_id
          : (payload.laudoId ?? null),
      laudoCard:
        jsonPayload.laudo_card && typeof jsonPayload.laudo_card === "object"
          ? (jsonPayload.laudo_card as MobileChatSendResult["laudoCard"])
          : null,
      assistantText:
        typeof jsonPayload.texto === "string" ? jsonPayload.texto : "",
      modo: normalizarModoChat(jsonPayload.modo ?? modo),
      citacoes: extrairCitacoes(jsonPayload.citacoes),
      confiancaIa: extrairConfiancaIa(jsonPayload.confianca_ia),
      events: [jsonPayload],
    };
  }

  const raw = await response.text();
  const events = extrairEventosSse(raw);

  let laudoId = payload.laudoId ?? null;
  let laudoCard: MobileChatSendResult["laudoCard"] = null;
  let assistantText = "";
  let citacoes: Array<Record<string, unknown>> = [];
  let confiancaIa: Record<string, unknown> | null = null;

  for (const event of events) {
    if (typeof event.laudo_id === "number") {
      laudoId = event.laudo_id;
    }
    if (event.laudo_card && typeof event.laudo_card === "object") {
      laudoCard = event.laudo_card as MobileChatSendResult["laudoCard"];
    }
    if (typeof event.texto === "string") {
      assistantText += event.texto;
    }
    if (event.citacoes !== undefined) {
      citacoes = extrairCitacoes(event.citacoes);
    }
    if (event.confianca_ia !== undefined) {
      confiancaIa = extrairConfiancaIa(event.confianca_ia);
    }
  }

  return {
    laudoId,
    laudoCard,
    assistantText: assistantText.trim(),
    modo,
    citacoes,
    confiancaIa,
    events,
  };
}

export async function uploadDocumentoChatMobile(
  accessToken: string,
  payload: {
    uri: string;
    nome: string;
    mimeType?: string;
  },
): Promise<MobileDocumentUploadResponse> {
  const formData = new FormData();
  formData.append("arquivo", {
    uri: payload.uri,
    name: payload.nome,
    type: payload.mimeType || inferirMimeType(payload.nome),
  } as unknown as Blob);

  const response = await fetchComObservabilidade(
    "chat_upload_doc",
    buildApiUrl("/app/api/upload_doc"),
    {
      method: "POST",
      headers: construirHeaders(accessToken),
      body: formData,
    },
  );

  const corpo = await lerJsonSeguro<
    MobileDocumentUploadResponse | { detail?: string }
  >(response);
  if (!response.ok || !corpo || !("texto" in corpo)) {
    throw new Error(
      extrairMensagemErro(
        corpo,
        "Não foi possível preparar o documento para o chat.",
      ),
    );
  }

  return corpo;
}

export async function reabrirLaudoMobile(
  accessToken: string,
  laudoId: number,
  reopenRequest?: MobileLaudoReopenRequest,
): Promise<MobileLaudoStatusResponse> {
  const body = reopenRequest ? JSON.stringify(reopenRequest) : undefined;
  const response = await fetchComObservabilidade(
    "laudo_reabrir",
    buildApiUrl(`/app/api/laudo/${laudoId}/reabrir`),
    {
      method: "POST",
      headers: construirHeaders(
        accessToken,
        body ? { "content-type": "application/json" } : undefined,
      ),
      body,
    },
  );

  const payload = await lerJsonSeguro<
    MobileLaudoStatusResponse | { detail?: string }
  >(response);
  if (!response.ok || !payload || !("estado" in payload)) {
    throw new Error(
      extrairMensagemErro(payload, "Não foi possível reabrir o laudo."),
    );
  }

  return payload;
}

export async function finalizarLaudoMobile(
  accessToken: string,
  laudoId: number,
  payload?: {
    qualityGateOverride?: MobileQualityGateOverridePayload | null;
  },
): Promise<MobileLaudoFinalizeResponse> {
  const override = payload?.qualityGateOverride;
  const requestBody = override
    ? JSON.stringify({
        quality_gate_override: Boolean(override.enabled),
        quality_gate_override_reason: override.reason || "",
        quality_gate_override_cases: Array.isArray(override.cases)
          ? override.cases
          : [],
      })
    : undefined;
  const response = await fetchComObservabilidade(
    "laudo_finalizar",
    buildApiUrl(`/app/api/laudo/${laudoId}/finalizar`),
    {
      method: "POST",
      headers: construirHeaders(
        accessToken,
        requestBody ? { "content-type": "application/json" } : undefined,
      ),
      body: requestBody,
    },
  );

  const jsonPayload = await lerJsonSeguro<
    | MobileLaudoFinalizeResponse
    | MobileQualityGateResponse
    | { detail?: string }
  >(response);
  const gatePayload = normalizarQualityGateResponse(jsonPayload);
  if (gatePayload) {
    throw new MobileQualityGateError(
      gatePayload,
      "finalize",
      "O quality gate ainda bloqueia a finalização deste caso.",
    );
  }

  if (!response.ok || !jsonPayload || !("success" in jsonPayload)) {
    throw new Error(
      extrairMensagemErro(
        jsonPayload,
        "Não foi possível finalizar o caso pelo app.",
      ),
    );
  }

  return normalizarRespostaFinalizacaoLaudo(jsonPayload);
}
