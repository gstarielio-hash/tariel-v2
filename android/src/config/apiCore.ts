import { Platform } from "react-native";

import { registrarEventoObservabilidade } from "./observability";

export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

type RuntimeEnvMap = Record<string, string | undefined>;

function readExpoPublicRuntimeEnv(key: string): string | undefined {
  switch (key) {
    case "EXPO_PUBLIC_API_BASE_URL":
      return process.env.EXPO_PUBLIC_API_BASE_URL;
    case "EXPO_PUBLIC_AUTH_WEB_BASE_URL":
      return process.env.EXPO_PUBLIC_AUTH_WEB_BASE_URL;
    case "EXPO_PUBLIC_AUTH_FORGOT_PASSWORD_URL":
      return process.env.EXPO_PUBLIC_AUTH_FORGOT_PASSWORD_URL;
    case "EXPO_PUBLIC_AUTH_GOOGLE_URL":
      return process.env.EXPO_PUBLIC_AUTH_GOOGLE_URL;
    case "EXPO_PUBLIC_AUTH_MICROSOFT_URL":
      return process.env.EXPO_PUBLIC_AUTH_MICROSOFT_URL;
    default:
      return undefined;
  }
}

function readRuntimeEnv(key: string): string {
  const directRuntimeValue = readExpoPublicRuntimeEnv(key);
  if (typeof directRuntimeValue === "string") {
    return directRuntimeValue.trim();
  }

  const runtimeEnv = (
    globalThis as typeof globalThis & {
      process?: { env?: RuntimeEnvMap };
    }
  ).process?.env;
  const value = runtimeEnv?.[key];
  return typeof value === "string" ? value.trim() : "";
}

function fallbackRandomHex(length: number): string {
  let output = "";
  while (output.length < length) {
    output += Math.floor(Math.random() * Number.MAX_SAFE_INTEGER)
      .toString(16)
      .padStart(14, "0");
  }
  return output.slice(0, length);
}

function randomHex(length: number): string {
  let output = "";
  const runtimeCrypto = globalThis.crypto;

  while (output.length < length) {
    if (runtimeCrypto?.randomUUID) {
      output += runtimeCrypto.randomUUID().replaceAll("-", "");
      continue;
    }
    output += fallbackRandomHex(length);
  }

  return output.slice(0, length);
}

function createRequestId(seed?: string | null): string {
  const normalizedSeed = String(seed || "").trim();
  return normalizedSeed || randomHex(24);
}

function createTraceparent(): string {
  return `00-${randomHex(32)}-${randomHex(16)}-01`;
}

function androidPareceEmulador(): boolean {
  if (Platform.OS !== "android") {
    return false;
  }

  const constants = (Platform.constants || {}) as Record<string, unknown>;
  const fingerprint = String(constants.Fingerprint || "");
  const model = String(constants.Model || "");
  const brand = String(constants.Brand || "");
  const manufacturer = String(constants.Manufacturer || "");
  const product = String(constants.Product || "");
  const hardware = String(constants.Hardware || "");
  const device = String(constants.Device || "");
  const joined = [
    fingerprint,
    model,
    brand,
    manufacturer,
    product,
    hardware,
    device,
  ].join(" ");

  return /generic|sdk|emulator|simulator|goldfish|ranchu/i.test(joined);
}

export function normalizarApiBaseUrl(rawValue: string): string {
  const value = String(rawValue || DEFAULT_API_BASE_URL)
    .trim()
    .replace(/\/+$/, "");

  if (Platform.OS !== "android" || !androidPareceEmulador()) {
    return value;
  }

  // In Android emulators, localhost/127.0.0.1 points to the emulator itself.
  return value.replace(
    /:\/\/(127\.0\.0\.1|localhost)(?=[:/]|$)/i,
    "://10.0.2.2",
  );
}

export const API_BASE_URL = normalizarApiBaseUrl(
  readRuntimeEnv("EXPO_PUBLIC_API_BASE_URL") || DEFAULT_API_BASE_URL,
);

export { readRuntimeEnv };

const HEALTH_CHECK_TIMEOUT_MS = 6_000;

export function buildApiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

export function resolverUrlArquivoApi(rawValue?: string): string {
  const value = String(rawValue || "").trim();
  if (!value) {
    return "";
  }
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  if (value.startsWith("//")) {
    return `https:${value}`;
  }
  if (value.startsWith("/")) {
    return `${API_BASE_URL}${value}`;
  }
  return `${API_BASE_URL}/${value.replace(/^\/+/, "")}`;
}

export function inferirMimeType(nomeArquivo: string): string {
  const nome = String(nomeArquivo || "")
    .trim()
    .toLowerCase();
  if (nome.endsWith(".pdf")) {
    return "application/pdf";
  }
  if (nome.endsWith(".docx")) {
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  }
  if (nome.endsWith(".doc")) {
    return "application/msword";
  }
  return "application/octet-stream";
}

export function construirHeaders(
  accessToken?: string,
  extra?: HeadersInit,
  requestIdSeed?: string | null,
): Headers {
  const headers = new Headers(extra || {});
  const requestId = createRequestId(
    headers.get("X-Client-Request-Id") ||
      headers.get("X-Request-Id") ||
      headers.get("X-Mesa-Client-Trace-Id") ||
      requestIdSeed,
  );
  const correlationId =
    String(headers.get("X-Correlation-ID") || "").trim() || requestId;
  const traceparent =
    String(headers.get("traceparent") || "").trim() || createTraceparent();

  headers.set("Accept", "application/json");
  headers.set("X-Correlation-ID", correlationId);
  headers.set("X-Request-Id", requestId);
  headers.set("X-Client-Request-Id", requestId);
  headers.set(
    "X-Mesa-Client-Trace-Id",
    String(headers.get("X-Mesa-Client-Trace-Id") || "").trim() || requestId,
  );
  headers.set("traceparent", traceparent);
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  return headers;
}

export function extrairMensagemErro(
  payload: unknown,
  fallback: string,
): string {
  if (payload && typeof payload === "object") {
    const detalhe = Reflect.get(payload, "detail");
    if (typeof detalhe === "string" && detalhe.trim()) {
      return detalhe.trim();
    }
  }
  return fallback;
}

export async function lerJsonSeguro<T>(response: Response): Promise<T | null> {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  const raw = await response.text();
  if (!raw.trim()) {
    return null;
  }
  return JSON.parse(raw) as T;
}

function normalizarPathObservabilidade(url: string): string {
  try {
    const parsed = new URL(url);
    return `${parsed.pathname}${parsed.search}`;
  } catch {
    return String(url || "").replace(/^https?:\/\/[^/]+/i, "");
  }
}

export interface FetchObservabilityLifecyclePayload {
  method: string;
  path: string;
  url: string;
}

export interface FetchObservabilityFailurePayload extends FetchObservabilityLifecyclePayload {
  cancelled: boolean;
  error: unknown;
}

export interface FetchObservabilityResponsePayload extends FetchObservabilityLifecyclePayload {
  response: Response;
}

export interface FetchObservabilityLifecycle {
  onRequestFailed?: (payload: FetchObservabilityFailurePayload) => void;
  onRequestSent?: (payload: FetchObservabilityLifecyclePayload) => void;
  onResponseReceived?: (payload: FetchObservabilityResponsePayload) => void;
}

export interface FetchObservabilityOptions {
  timeoutMs?: number;
}

function createAbortSignalWithTimeout(
  parentSignal: AbortSignal | null | undefined,
  timeoutMs: number | undefined,
): {
  cleanup: () => void;
  didTimeout: () => boolean;
  signal: AbortSignal | undefined;
} {
  const normalizedTimeout =
    typeof timeoutMs === "number" && Number.isFinite(timeoutMs) && timeoutMs > 0
      ? Math.round(timeoutMs)
      : null;

  if (!parentSignal && !normalizedTimeout) {
    return {
      cleanup: () => undefined,
      didTimeout: () => false,
      signal: undefined,
    };
  }

  if (!normalizedTimeout) {
    return {
      cleanup: () => undefined,
      didTimeout: () => false,
      signal: parentSignal || undefined,
    };
  }

  const controller = new AbortController();
  let timedOut = false;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  const abortFromParent = () => {
    if (!controller.signal.aborted) {
      controller.abort(parentSignal?.reason);
    }
  };

  if (parentSignal?.aborted) {
    abortFromParent();
  } else if (parentSignal) {
    parentSignal.addEventListener("abort", abortFromParent, { once: true });
  }

  timeoutId = setTimeout(() => {
    timedOut = true;
    if (!controller.signal.aborted) {
      controller.abort(
        new Error(`Request timed out after ${normalizedTimeout}ms.`),
      );
    }
  }, normalizedTimeout);

  return {
    cleanup: () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      if (parentSignal) {
        parentSignal.removeEventListener("abort", abortFromParent);
      }
    },
    didTimeout: () => timedOut,
    signal: controller.signal,
  };
}

export async function fetchComObservabilidade(
  metricName: string,
  url: string,
  init?: RequestInit,
  lifecycle?: FetchObservabilityLifecycle,
  options?: FetchObservabilityOptions,
): Promise<Response> {
  const startedAt = Date.now();
  const method = String(init?.method || "GET").toUpperCase();
  const path = normalizarPathObservabilidade(url);
  const timeoutMs =
    typeof options?.timeoutMs === "number" && Number.isFinite(options.timeoutMs)
      ? Math.max(1, Math.round(options.timeoutMs))
      : undefined;
  const abortContext = createAbortSignalWithTimeout(init?.signal, timeoutMs);
  const nextInit = abortContext.signal
    ? { ...init, signal: abortContext.signal }
    : init;

  try {
    lifecycle?.onRequestSent?.({ method, path, url });
    const response = await fetch(url, nextInit);
    lifecycle?.onResponseReceived?.({ method, path, response, url });
    void registrarEventoObservabilidade({
      kind: "api",
      name: metricName,
      ok: response.ok,
      method,
      path,
      httpStatus: response.status,
      durationMs: Date.now() - startedAt,
      detail: response.ok ? "ok" : `http_${response.status}`,
    });
    return response;
  } catch (error) {
    const detail = abortContext.didTimeout()
      ? `timeout_${timeoutMs}ms`
      : error instanceof Error
        ? error.message
        : "fetch_error";
    lifecycle?.onRequestFailed?.({
      method,
      path,
      url,
      error,
      cancelled:
        abortContext.didTimeout() ||
        (error instanceof Error &&
          (String(error.name || "")
            .trim()
            .toLowerCase() === "aborterror" ||
            /abort|cancel/i.test(String(error.message || "")))),
    });
    void registrarEventoObservabilidade({
      kind: "api",
      name: metricName,
      ok: false,
      method,
      path,
      durationMs: Date.now() - startedAt,
      detail,
    });
    throw error;
  } finally {
    abortContext.cleanup();
  }
}

export async function pingApi(): Promise<boolean> {
  try {
    const response = await fetchComObservabilidade(
      "health_check",
      buildApiUrl("/health"),
      undefined,
      undefined,
      { timeoutMs: HEALTH_CHECK_TIMEOUT_MS },
    );
    return response.ok;
  } catch {
    return false;
  }
}
