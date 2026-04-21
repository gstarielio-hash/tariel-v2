import type {
  MobileMesaFeedResponse,
  MobileMesaMensagensResponse,
  MobileMesaReviewCommandPayload,
  MobileMesaReviewDecisionResponse,
  MobileMesaResumoResponse,
  MobileMesaSendResponse,
} from "../types/mobile";
import { getAndroidV2ReadContractsRuntimeSnapshot } from "./mobileV2Config";
import {
  appendMobilePilotRequestAttempt,
  buildMobilePilotRequestTraceSummary,
  classifyMobilePilotRequestFailure,
  type MobilePilotRequestTraceSummary,
  updateMobilePilotRequestTraceSummary,
} from "./mobilePilotRequestTrace";
import {
  MobileV2ContractError,
  mapMobileInspectorFeedV2ToLegacy,
  mapMobileInspectorThreadV2ToLegacy,
  parseMobileInspectorFeedV2,
  parseMobileInspectorThreadV2,
} from "./mobileV2MesaAdapter";
import {
  attachMobileV2ReadRenderMetadata,
  type MobileV2ReadDeliveryMode,
  type MobileV2ReadRenderMetadata,
} from "./mobileV2HumanValidation";
import {
  buildMobileV2AttemptHeaders,
  buildMobileV2FallbackHeaders,
  classifyMobileV2ReadError,
  invalidateMobileV2CapabilitiesCache,
  type MobileV2AttemptMetadata,
  type MobileV2CapabilitiesResponse,
  type MobileV2FallbackReason,
  resolveMobileV2OrganicValidationMetadata,
  resolveMobileV2RouteDecision,
} from "./mobileV2Rollout";
import { registrarEventoObservabilidade } from "./observability";
import {
  buildApiUrl,
  construirHeaders,
  extrairMensagemErro,
  fetchComObservabilidade,
  inferirMimeType,
  lerJsonSeguro,
} from "./apiCore";

const MOBILE_CENTRAL_TRACE_HEADER = "X-Tariel-Mobile-Central-Trace";
const MOBILE_CENTRAL_TRACE_SOURCE_HEADER =
  "X-Tariel-Mobile-Central-Trace-Source";
const MOBILE_CENTRAL_TRACE_SOURCE = "activity_center_feed";

function montarUrlMesa(
  path: string,
  query?: Record<string, string | number | null | undefined>,
): string {
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries(query || {})) {
    if (valor === null || valor === undefined || valueIsEmpty(valor)) {
      continue;
    }
    params.set(chave, String(valor));
  }
  const queryString = params.toString();
  const url = buildApiUrl(path);
  return queryString ? `${url}?${queryString}` : url;
}

function valueIsEmpty(valor: string | number): boolean {
  return typeof valor === "string" && !valor.trim();
}

function construirHeadersMesa(
  accessToken: string,
  requestId?: string | null,
  extra?: HeadersInit,
): Headers {
  return construirHeaders(accessToken, extra, requestId);
}

function resumirErroV2(error: unknown): MobileV2FallbackReason {
  return classifyMobileV2ReadError(error);
}

function normalizarErroAdapterV2(
  error: unknown,
  fallbackMessage: string,
): MobileV2ContractError {
  if (error instanceof MobileV2ContractError) {
    return error;
  }
  return new MobileV2ContractError(
    "adapter_error",
    error instanceof Error ? error.message : fallbackMessage,
  );
}

function montarAttemptMetadata(
  route: "feed" | "thread",
  options?: {
    capabilities?: MobileV2CapabilitiesResponse | null;
    capabilitiesVersion?: string | null;
    rolloutBucket?: number | null;
  },
): MobileV2AttemptMetadata {
  const organicValidation = resolveMobileV2OrganicValidationMetadata(
    route,
    options?.capabilities,
  );
  return {
    route,
    capabilitiesVersion: options?.capabilitiesVersion ?? null,
    rolloutBucket: options?.rolloutBucket ?? null,
    usageMode: organicValidation?.usageMode ?? null,
    validationSessionId: organicValidation?.validationSessionId ?? null,
    operatorRunId: organicValidation?.operatorRunId ?? null,
  };
}

function resolveSuggestedTargetIds(
  route: "feed" | "thread",
  capabilities?: MobileV2CapabilitiesResponse | null,
): number[] {
  const row = (capabilities?.organic_validation_target_suggestions || []).find(
    (item) => item.surface === route,
  );
  if (!row) {
    return [];
  }

  return Array.from(
    new Set(
      (row.suggested_target_ids || [])
        .map((item) => Number(item))
        .filter((item) => Number.isFinite(item) && item > 0),
    ),
  );
}

function montarReadRenderMetadata(
  route: "feed" | "thread",
  deliveryMode: MobileV2ReadDeliveryMode,
  options?: {
    capabilities?: MobileV2CapabilitiesResponse | null;
    capabilitiesVersion?: string | null;
    rolloutBucket?: number | null;
  },
): MobileV2ReadRenderMetadata {
  const organicValidation = resolveMobileV2OrganicValidationMetadata(
    route,
    options?.capabilities,
  );
  return {
    route,
    deliveryMode,
    capabilitiesVersion: options?.capabilitiesVersion ?? null,
    rolloutBucket: options?.rolloutBucket ?? null,
    usageMode: organicValidation?.usageMode ?? null,
    validationSessionId: organicValidation?.validationSessionId ?? null,
    operatorRunId: organicValidation?.operatorRunId ?? null,
    suggestedTargetIds: resolveSuggestedTargetIds(route, options?.capabilities),
  };
}

function shouldBlockLegacyFallbackDuringOrganicValidation(
  route: "feed" | "thread",
  capabilities?: MobileV2CapabilitiesResponse | null,
): boolean {
  return Boolean(
    resolveMobileV2OrganicValidationMetadata(route, capabilities)
      ?.validationSessionId,
  );
}

function erroFallbackBloqueadoNaValidacaoOrganica(
  route: "feed" | "thread",
  reason: string,
): MobileV2ContractError {
  return new MobileV2ContractError(
    "http_error",
    `Fallback legado bloqueado para ${route} durante validacao organica (${reason}).`,
  );
}

function erroHttpContratoV2(
  status: number,
  fallbackMessage: string,
  payload: unknown,
): MobileV2ContractError {
  return new MobileV2ContractError(
    status === 404 ? "http_404" : "http_error",
    extrairMensagemErro(payload, fallbackMessage),
  );
}

function registrarLeituraContratoV2(params: {
  name: string;
  ok: boolean;
  detail: string;
}) {
  void registrarEventoObservabilidade({
    kind: "api",
    name: params.name,
    ok: params.ok,
    detail: params.detail,
  });
}

type FeedRequestTraceListener = (trace: MobilePilotRequestTraceSummary) => void;

function addMobileCentralTraceHeaders(
  extra: HeadersInit | undefined,
  requestTrace: MobilePilotRequestTraceSummary | null | undefined,
): Headers {
  const headers = new Headers(extra || {});
  if (!requestTrace) {
    return headers;
  }
  headers.set(MOBILE_CENTRAL_TRACE_HEADER, requestTrace.traceId);
  headers.set(MOBILE_CENTRAL_TRACE_SOURCE_HEADER, MOBILE_CENTRAL_TRACE_SOURCE);
  return headers;
}

function emitFeedRequestTrace(
  current: MobilePilotRequestTraceSummary | null,
  listener: FeedRequestTraceListener | undefined,
  patch: Partial<MobilePilotRequestTraceSummary>,
): MobilePilotRequestTraceSummary | null {
  if (!current) {
    return null;
  }
  const next = updateMobilePilotRequestTraceSummary(current, patch);
  listener?.(next);
  return next;
}

async function carregarMensagensMesaMobileLegacy(
  accessToken: string,
  laudoId: number,
  options?: {
    aposId?: number | null;
    fallbackHeaders?: HeadersInit;
  },
): Promise<MobileMesaMensagensResponse> {
  const response = await fetchComObservabilidade(
    "mesa_mensagens_list",
    montarUrlMesa(`/app/api/laudo/${laudoId}/mesa/mensagens`, {
      apos_id: options?.aposId ?? null,
    }),
    {
      method: "GET",
      headers: construirHeaders(accessToken, options?.fallbackHeaders),
    },
  );

  const payload = await lerJsonSeguro<
    MobileMesaMensagensResponse | { detail?: string }
  >(response);
  if (!response.ok || !payload || !("itens" in payload)) {
    throw new Error(
      extrairMensagemErro(
        payload,
        "Não foi possível carregar a conversa da mesa.",
      ),
    );
  }

  return payload;
}

async function carregarMensagensMesaMobileV2(
  accessToken: string,
  laudoId: number,
  options?: {
    aposId?: number | null;
    requestHeaders?: HeadersInit;
  },
): Promise<MobileMesaMensagensResponse> {
  const response = await fetchComObservabilidade(
    "mesa_mensagens_v2_list",
    montarUrlMesa(`/app/api/mobile/v2/laudo/${laudoId}/mesa/mensagens`, {
      apos_id: options?.aposId ?? null,
    }),
    {
      method: "GET",
      headers: construirHeaders(accessToken, options?.requestHeaders),
    },
  );

  const payload = await lerJsonSeguro<unknown | { detail?: string }>(response);
  if (!response.ok || !payload) {
    throw erroHttpContratoV2(
      response.status,
      "Não foi possível carregar a conversa da mesa no contrato V2.",
      payload,
    );
  }

  try {
    return mapMobileInspectorThreadV2ToLegacy(
      parseMobileInspectorThreadV2(payload),
    );
  } catch (error) {
    throw normalizarErroAdapterV2(
      error,
      "Nao foi possivel adaptar a thread da mesa no contrato V2.",
    );
  }
}

export async function carregarMensagensMesaMobile(
  accessToken: string,
  laudoId: number,
  options?: {
    aposId?: number | null;
  },
): Promise<MobileMesaMensagensResponse> {
  if (!getAndroidV2ReadContractsRuntimeSnapshot().enabled) {
    return carregarMensagensMesaMobileLegacy(accessToken, laudoId, options);
  }

  const gateDecision = await resolveMobileV2RouteDecision(
    accessToken,
    "thread",
  );
  if (!gateDecision.shouldUseV2) {
    const fallbackReason = gateDecision.fallbackReason ?? "rollout_unknown";
    registrarLeituraContratoV2({
      name: "mesa_thread_v2_read",
      ok: true,
      detail: `fallback_legacy:${fallbackReason}`,
    });
    try {
      const legacyPayload = await carregarMensagensMesaMobileLegacy(
        accessToken,
        laudoId,
        {
          ...options,
          fallbackHeaders: buildMobileV2FallbackHeaders({
            route: "thread",
            reason: fallbackReason,
            source: gateDecision.source,
            capabilitiesVersion:
              gateDecision.capabilities?.capabilities_version ?? null,
            rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
            usageMode:
              resolveMobileV2OrganicValidationMetadata(
                "thread",
                gateDecision.capabilities,
              )?.usageMode ?? null,
            validationSessionId:
              resolveMobileV2OrganicValidationMetadata(
                "thread",
                gateDecision.capabilities,
              )?.validationSessionId ?? null,
            operatorRunId:
              resolveMobileV2OrganicValidationMetadata(
                "thread",
                gateDecision.capabilities,
              )?.operatorRunId ?? null,
          }),
        },
      );
      return attachMobileV2ReadRenderMetadata(
        legacyPayload,
        montarReadRenderMetadata("thread", "legacy", {
          capabilities: gateDecision.capabilities ?? null,
          capabilitiesVersion:
            gateDecision.capabilities?.capabilities_version ?? null,
          rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
        }),
      );
    } catch (legacyError) {
      registrarLeituraContratoV2({
        name: "mesa_thread_v2_read",
        ok: false,
        detail: `legacy_failed:${resumirErroV2(legacyError)}`,
      });
      throw legacyError;
    }
  }

  try {
    const payload = await carregarMensagensMesaMobileV2(accessToken, laudoId, {
      ...options,
      requestHeaders: buildMobileV2AttemptHeaders(
        montarAttemptMetadata("thread", {
          capabilities: gateDecision.capabilities ?? null,
          capabilitiesVersion:
            gateDecision.capabilities?.capabilities_version ?? null,
          rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
        }),
      ),
    });
    registrarLeituraContratoV2({
      name: "mesa_thread_v2_read",
      ok: true,
      detail: "used_v2",
    });
    return attachMobileV2ReadRenderMetadata(
      payload,
      montarReadRenderMetadata("thread", "v2", {
        capabilities: gateDecision.capabilities ?? null,
        capabilitiesVersion:
          gateDecision.capabilities?.capabilities_version ?? null,
        rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
      }),
    );
  } catch (error) {
    invalidateMobileV2CapabilitiesCache(accessToken);
    const fallbackReason = resumirErroV2(error);
    if (
      shouldBlockLegacyFallbackDuringOrganicValidation(
        "thread",
        gateDecision.capabilities,
      )
    ) {
      registrarLeituraContratoV2({
        name: "mesa_thread_v2_read",
        ok: false,
        detail: `organic_validation_blocked:${fallbackReason}`,
      });
      throw erroFallbackBloqueadoNaValidacaoOrganica("thread", fallbackReason);
    }
    const detail = `fallback_legacy:${fallbackReason}`;
    registrarLeituraContratoV2({
      name: "mesa_thread_v2_read",
      ok: true,
      detail,
    });
    try {
      const legacyPayload = await carregarMensagensMesaMobileLegacy(
        accessToken,
        laudoId,
        {
          ...options,
          fallbackHeaders: buildMobileV2FallbackHeaders({
            route: "thread",
            reason: resumirErroV2(error),
            source: "v2_read",
            capabilitiesVersion:
              gateDecision.capabilities?.capabilities_version ?? null,
            rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
            usageMode:
              resolveMobileV2OrganicValidationMetadata(
                "thread",
                gateDecision.capabilities,
              )?.usageMode ?? null,
            validationSessionId:
              resolveMobileV2OrganicValidationMetadata(
                "thread",
                gateDecision.capabilities,
              )?.validationSessionId ?? null,
            operatorRunId:
              resolveMobileV2OrganicValidationMetadata(
                "thread",
                gateDecision.capabilities,
              )?.operatorRunId ?? null,
          }),
        },
      );
      return attachMobileV2ReadRenderMetadata(
        legacyPayload,
        montarReadRenderMetadata("thread", "legacy", {
          capabilities: gateDecision.capabilities ?? null,
          capabilitiesVersion:
            gateDecision.capabilities?.capabilities_version ?? null,
          rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
        }),
      );
    } catch (legacyError) {
      registrarLeituraContratoV2({
        name: "mesa_thread_v2_read",
        ok: false,
        detail: `legacy_failed:${resumirErroV2(legacyError)}`,
      });
      throw legacyError;
    }
  }
}

export async function enviarMensagemMesaMobile(
  accessToken: string,
  laudoId: number,
  texto: string,
  referenciaMensagemId?: number | null,
  clientMessageId?: string | null,
): Promise<MobileMesaSendResponse> {
  const response = await fetchComObservabilidade(
    "mesa_send_text",
    buildApiUrl(`/app/api/laudo/${laudoId}/mesa/mensagem`),
    {
      method: "POST",
      headers: construirHeadersMesa(accessToken, clientMessageId, {
        "Content-Type": "application/json",
      }),
      body: JSON.stringify({
        texto,
        referencia_mensagem_id: referenciaMensagemId ?? null,
        client_message_id: clientMessageId ?? null,
      }),
    },
  );

  const payload = await lerJsonSeguro<
    MobileMesaSendResponse | { detail?: string }
  >(response);
  if (!response.ok || !payload || !("mensagem" in payload)) {
    throw new Error(
      extrairMensagemErro(
        payload,
        "Não foi possível responder à mesa pelo app.",
      ),
    );
  }

  return payload;
}

export async function executarComandoRevisaoMobile(
  accessToken: string,
  laudoId: number,
  payload: MobileMesaReviewCommandPayload,
): Promise<MobileMesaReviewDecisionResponse> {
  const response = await fetchComObservabilidade(
    "mesa_mobile_review_command",
    buildApiUrl(`/app/api/laudo/${laudoId}/mobile-review-command`),
    {
      method: "POST",
      headers: construirHeadersMesa(accessToken, undefined, {
        "Content-Type": "application/json",
      }),
      body: JSON.stringify({
        command: payload.command,
        block_key: payload.block_key ?? null,
        evidence_key: payload.evidence_key ?? null,
        title: payload.title ?? null,
        reason: payload.reason ?? null,
        summary: payload.summary ?? null,
        required_action: payload.required_action ?? null,
        failure_reasons: payload.failure_reasons ?? [],
      }),
    },
  );

  const corpo = await lerJsonSeguro<
    MobileMesaReviewDecisionResponse | { detail?: string }
  >(response);
  if (!response.ok || !corpo || !("ok" in corpo)) {
    throw new Error(
      extrairMensagemErro(
        corpo,
        "Não foi possível executar o comando de revisão no mobile.",
      ),
    );
  }

  return corpo;
}

export async function enviarAnexoMesaMobile(
  accessToken: string,
  laudoId: number,
  payload: {
    uri: string;
    nome: string;
    mimeType?: string;
    texto?: string;
    referenciaMensagemId?: number | null;
    clientMessageId?: string | null;
  },
): Promise<MobileMesaSendResponse> {
  const formData = new FormData();
  formData.append("arquivo", {
    uri: payload.uri,
    name: payload.nome,
    type: payload.mimeType || inferirMimeType(payload.nome),
  } as unknown as Blob);
  formData.append("texto", payload.texto || "");
  if (payload.referenciaMensagemId) {
    formData.append(
      "referencia_mensagem_id",
      String(payload.referenciaMensagemId),
    );
  }
  if (payload.clientMessageId) {
    formData.append("client_message_id", payload.clientMessageId);
  }

  const response = await fetchComObservabilidade(
    "mesa_send_attachment",
    buildApiUrl(`/app/api/laudo/${laudoId}/mesa/anexo`),
    {
      method: "POST",
      headers: construirHeadersMesa(accessToken, payload.clientMessageId),
      body: formData,
    },
  );

  const corpo = await lerJsonSeguro<
    MobileMesaSendResponse | { detail?: string }
  >(response);
  if (!response.ok || !corpo || !("mensagem" in corpo)) {
    throw new Error(
      extrairMensagemErro(
        corpo,
        "Não foi possível enviar o anexo para a mesa.",
      ),
    );
  }

  return corpo;
}

export async function carregarResumoMesaMobile(
  accessToken: string,
  laudoId: number,
): Promise<MobileMesaResumoResponse> {
  const response = await fetchComObservabilidade(
    "mesa_resumo_get",
    buildApiUrl(`/app/api/laudo/${laudoId}/mesa/resumo`),
    {
      method: "GET",
      headers: construirHeaders(accessToken),
    },
  );

  const payload = await lerJsonSeguro<
    MobileMesaResumoResponse | { detail?: string }
  >(response);
  if (!response.ok || !payload || !("resumo" in payload)) {
    throw new Error(
      extrairMensagemErro(
        payload,
        "Não foi possível carregar o resumo da mesa.",
      ),
    );
  }

  return payload;
}

async function carregarFeedMesaMobileLegacy(
  accessToken: string,
  payload: {
    laudoIds: number[];
    cursorAtualizadoEm?: string | null;
    fallbackHeaders?: HeadersInit;
    onRequestTrace?: FeedRequestTraceListener;
    requestTrace?: MobilePilotRequestTraceSummary | null;
  },
): Promise<MobileMesaFeedResponse> {
  let requestTrace = payload.requestTrace ?? null;
  const url = montarUrlMesa("/app/api/mobile/mesa/feed", {
    laudo_ids: payload.laudoIds.join(","),
    cursor_atualizado_em: payload.cursorAtualizadoEm ?? null,
  });
  const response = await fetchComObservabilidade(
    "mesa_feed_list",
    url,
    {
      method: "GET",
      headers: construirHeaders(
        accessToken,
        addMobileCentralTraceHeaders(payload.fallbackHeaders, requestTrace),
      ),
    },
    requestTrace
      ? {
          onRequestSent: ({ method, path }) => {
            requestTrace = emitFeedRequestTrace(
              appendMobilePilotRequestAttempt(requestTrace!, "legacy"),
              payload.onRequestTrace,
              {
                endpointPath: path,
                method,
                phase: "request_sent",
              },
            );
          },
          onResponseReceived: ({ path, response }) => {
            const responseHeaders = response?.headers;
            requestTrace = emitFeedRequestTrace(
              requestTrace,
              payload.onRequestTrace,
              {
                actualRoute: "legacy",
                backendRequestId:
                  responseHeaders?.get("x-request-id") ||
                  responseHeaders?.get("x-correlation-id") ||
                  null,
                deliveryMode: "legacy",
                endpointPath: path,
                phase: "response_received",
                responseStatus:
                  typeof response?.status === "number" ? response.status : null,
              },
            );
          },
          onRequestFailed: ({ error, path }) => {
            const failure = classifyMobilePilotRequestFailure(error);
            requestTrace = emitFeedRequestTrace(
              requestTrace,
              payload.onRequestTrace,
              {
                actualRoute: "legacy",
                endpointPath: path,
                failureDetail: failure.failureDetail,
                failureKind: failure.failureKind,
                phase: failure.phase,
              },
            );
          },
        }
      : undefined,
  );

  const corpo = await lerJsonSeguro<
    MobileMesaFeedResponse | { detail?: string }
  >(response);
  if (!response.ok || !corpo || !("itens" in corpo)) {
    throw new Error(
      extrairMensagemErro(corpo, "Não foi possível carregar o feed da mesa."),
    );
  }

  return corpo;
}

async function carregarFeedMesaMobileV2(
  accessToken: string,
  payload: {
    laudoIds: number[];
    cursorAtualizadoEm?: string | null;
    onRequestTrace?: FeedRequestTraceListener;
    requestHeaders?: HeadersInit;
    requestTrace?: MobilePilotRequestTraceSummary | null;
  },
): Promise<MobileMesaFeedResponse> {
  let requestTrace = payload.requestTrace ?? null;
  const url = montarUrlMesa("/app/api/mobile/v2/mesa/feed", {
    laudo_ids: payload.laudoIds.join(","),
    cursor_atualizado_em: payload.cursorAtualizadoEm ?? null,
  });
  const response = await fetchComObservabilidade(
    "mesa_feed_v2_list",
    url,
    {
      method: "GET",
      headers: construirHeaders(
        accessToken,
        addMobileCentralTraceHeaders(payload.requestHeaders, requestTrace),
      ),
    },
    requestTrace
      ? {
          onRequestSent: ({ method, path }) => {
            requestTrace = emitFeedRequestTrace(
              appendMobilePilotRequestAttempt(requestTrace!, "v2"),
              payload.onRequestTrace,
              {
                endpointPath: path,
                method,
                phase: "request_sent",
              },
            );
          },
          onResponseReceived: ({ path, response }) => {
            const responseHeaders = response?.headers;
            requestTrace = emitFeedRequestTrace(
              requestTrace,
              payload.onRequestTrace,
              {
                actualRoute: "v2",
                backendRequestId:
                  responseHeaders?.get("x-request-id") ||
                  responseHeaders?.get("x-correlation-id") ||
                  null,
                endpointPath: path,
                phase: "response_received",
                responseStatus:
                  typeof response?.status === "number" ? response.status : null,
              },
            );
          },
          onRequestFailed: ({ error, path }) => {
            const failure = classifyMobilePilotRequestFailure(error);
            requestTrace = emitFeedRequestTrace(
              requestTrace,
              payload.onRequestTrace,
              {
                actualRoute: "v2",
                endpointPath: path,
                failureDetail: failure.failureDetail,
                failureKind: failure.failureKind,
                phase: failure.phase,
              },
            );
          },
        }
      : undefined,
  );

  const corpo = await lerJsonSeguro<unknown | { detail?: string }>(response);
  if (!response.ok || !corpo) {
    throw erroHttpContratoV2(
      response.status,
      "Não foi possível carregar o feed da mesa no contrato V2.",
      corpo,
    );
  }

  try {
    return mapMobileInspectorFeedV2ToLegacy(parseMobileInspectorFeedV2(corpo));
  } catch (error) {
    throw normalizarErroAdapterV2(
      error,
      "Nao foi possivel adaptar o feed da mesa no contrato V2.",
    );
  }
}

export async function carregarFeedMesaMobile(
  accessToken: string,
  payload: {
    laudoIds: number[];
    cursorAtualizadoEm?: string | null;
    onRequestTrace?: FeedRequestTraceListener;
  },
): Promise<MobileMesaFeedResponse> {
  const contractFlag = getAndroidV2ReadContractsRuntimeSnapshot();
  const contractFlagEnabled = contractFlag.enabled;
  const notifyRequestTrace = payload.onRequestTrace;

  const emitTrace = (trace: MobilePilotRequestTraceSummary) => {
    notifyRequestTrace?.(trace);
    return trace;
  };

  if (!contractFlagEnabled) {
    let requestTrace = emitTrace(
      buildMobilePilotRequestTraceSummary({
        surface: "feed",
        contractFlagEnabled: false,
        contractFlagRawValue: contractFlag.rawValue,
        contractFlagSource: contractFlag.source,
        routeDecision: "legacy",
        decisionReason: "local_flag_off",
        decisionSource: "local_flag",
        targetIds: payload.laudoIds,
      }),
    );
    requestTrace = emitTrace(
      updateMobilePilotRequestTraceSummary(requestTrace, {
        fallbackReason: "local_flag_off",
      }),
    );
    const legacyPayload = await carregarFeedMesaMobileLegacy(accessToken, {
      ...payload,
      onRequestTrace: (next) => {
        requestTrace = emitTrace(next);
      },
      requestTrace,
    });
    emitTrace(
      updateMobilePilotRequestTraceSummary(requestTrace, {
        actualRoute: "legacy",
        deliveryMode: "legacy",
      }),
    );
    return legacyPayload;
  }

  const gateDecision = await resolveMobileV2RouteDecision(accessToken, "feed");
  const organicValidation = resolveMobileV2OrganicValidationMetadata(
    "feed",
    gateDecision.capabilities,
  );
  let requestTrace = emitTrace(
    buildMobilePilotRequestTraceSummary({
      surface: "feed",
      contractFlagEnabled: true,
      contractFlagRawValue: contractFlag.rawValue,
      contractFlagSource: contractFlag.source,
      routeDecision: gateDecision.shouldUseV2 ? "v2" : "legacy",
      decisionReason: gateDecision.reason,
      decisionSource: gateDecision.source,
      targetIds: payload.laudoIds,
      validationSessionId: organicValidation?.validationSessionId ?? null,
      operatorRunId: organicValidation?.operatorRunId ?? null,
      usageMode: organicValidation?.usageMode ?? null,
    }),
  );
  if (!gateDecision.shouldUseV2) {
    const fallbackReason = gateDecision.fallbackReason ?? "rollout_unknown";
    registrarLeituraContratoV2({
      name: "mesa_feed_v2_read",
      ok: true,
      detail: `fallback_legacy:${fallbackReason}`,
    });
    try {
      const legacyPayload = await carregarFeedMesaMobileLegacy(accessToken, {
        ...payload,
        fallbackHeaders: buildMobileV2FallbackHeaders({
          route: "feed",
          reason: fallbackReason,
          source: gateDecision.source,
          capabilitiesVersion:
            gateDecision.capabilities?.capabilities_version ?? null,
          rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
          usageMode:
            resolveMobileV2OrganicValidationMetadata(
              "feed",
              gateDecision.capabilities,
            )?.usageMode ?? null,
          validationSessionId:
            resolveMobileV2OrganicValidationMetadata(
              "feed",
              gateDecision.capabilities,
            )?.validationSessionId ?? null,
          operatorRunId:
            resolveMobileV2OrganicValidationMetadata(
              "feed",
              gateDecision.capabilities,
            )?.operatorRunId ?? null,
        }),
        onRequestTrace: (next) => {
          requestTrace = emitTrace(next);
        },
        requestTrace: updateMobilePilotRequestTraceSummary(requestTrace, {
          decisionReason: gateDecision.reason,
          decisionSource: gateDecision.source,
          fallbackReason,
        }),
      });
      emitTrace(
        updateMobilePilotRequestTraceSummary(requestTrace, {
          actualRoute: "legacy",
          deliveryMode: "legacy",
          fallbackReason,
        }),
      );
      return attachMobileV2ReadRenderMetadata(
        legacyPayload,
        montarReadRenderMetadata("feed", "legacy", {
          capabilities: gateDecision.capabilities ?? null,
          capabilitiesVersion:
            gateDecision.capabilities?.capabilities_version ?? null,
          rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
        }),
      );
    } catch (legacyError) {
      registrarLeituraContratoV2({
        name: "mesa_feed_v2_read",
        ok: false,
        detail: `legacy_failed:${resumirErroV2(legacyError)}`,
      });
      throw legacyError;
    }
  }

  try {
    const response = await carregarFeedMesaMobileV2(accessToken, {
      ...payload,
      requestHeaders: buildMobileV2AttemptHeaders(
        montarAttemptMetadata("feed", {
          capabilities: gateDecision.capabilities ?? null,
          capabilitiesVersion:
            gateDecision.capabilities?.capabilities_version ?? null,
          rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
        }),
      ),
      onRequestTrace: (next) => {
        requestTrace = emitTrace(next);
      },
      requestTrace,
    });
    registrarLeituraContratoV2({
      name: "mesa_feed_v2_read",
      ok: true,
      detail: "used_v2",
    });
    emitTrace(
      updateMobilePilotRequestTraceSummary(requestTrace, {
        actualRoute: "v2",
        deliveryMode: "v2",
      }),
    );
    return attachMobileV2ReadRenderMetadata(
      response,
      montarReadRenderMetadata("feed", "v2", {
        capabilities: gateDecision.capabilities ?? null,
        capabilitiesVersion:
          gateDecision.capabilities?.capabilities_version ?? null,
        rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
      }),
    );
  } catch (error) {
    const fallbackReason = resumirErroV2(error);
    requestTrace = emitTrace(
      updateMobilePilotRequestTraceSummary(requestTrace, {
        actualRoute: "v2",
        failureDetail:
          error instanceof Error ? error.message : String(fallbackReason),
        failureKind: fallbackReason,
        fallbackReason,
      }),
    );
    invalidateMobileV2CapabilitiesCache(accessToken);
    if (
      shouldBlockLegacyFallbackDuringOrganicValidation(
        "feed",
        gateDecision.capabilities,
      )
    ) {
      registrarLeituraContratoV2({
        name: "mesa_feed_v2_read",
        ok: false,
        detail: `organic_validation_blocked:${fallbackReason}`,
      });
      throw erroFallbackBloqueadoNaValidacaoOrganica("feed", fallbackReason);
    }
    registrarLeituraContratoV2({
      name: "mesa_feed_v2_read",
      ok: true,
      detail: `fallback_legacy:${fallbackReason}`,
    });
    try {
      const legacyPayload = await carregarFeedMesaMobileLegacy(accessToken, {
        ...payload,
        fallbackHeaders: buildMobileV2FallbackHeaders({
          route: "feed",
          reason: fallbackReason,
          source: "v2_read",
          capabilitiesVersion:
            gateDecision.capabilities?.capabilities_version ?? null,
          rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
          usageMode:
            resolveMobileV2OrganicValidationMetadata(
              "feed",
              gateDecision.capabilities,
            )?.usageMode ?? null,
          validationSessionId:
            resolveMobileV2OrganicValidationMetadata(
              "feed",
              gateDecision.capabilities,
            )?.validationSessionId ?? null,
          operatorRunId:
            resolveMobileV2OrganicValidationMetadata(
              "feed",
              gateDecision.capabilities,
            )?.operatorRunId ?? null,
        }),
        onRequestTrace: (next) => {
          requestTrace = emitTrace(next);
        },
        requestTrace,
      });
      emitTrace(
        updateMobilePilotRequestTraceSummary(requestTrace, {
          actualRoute: "legacy",
          deliveryMode: "legacy",
          fallbackReason,
        }),
      );
      return attachMobileV2ReadRenderMetadata(
        legacyPayload,
        montarReadRenderMetadata("feed", "legacy", {
          capabilities: gateDecision.capabilities ?? null,
          capabilitiesVersion:
            gateDecision.capabilities?.capabilities_version ?? null,
          rolloutBucket: gateDecision.capabilities?.rollout_bucket ?? null,
        }),
      );
    } catch (legacyError) {
      registrarLeituraContratoV2({
        name: "mesa_feed_v2_read",
        ok: false,
        detail: `legacy_failed:${resumirErroV2(legacyError)}`,
      });
      emitTrace(
        updateMobilePilotRequestTraceSummary(requestTrace, {
          failureDetail:
            legacyError instanceof Error
              ? legacyError.message
              : String(resumirErroV2(legacyError)),
          failureKind: resumirErroV2(legacyError),
        }),
      );
      throw legacyError;
    }
  }
}
