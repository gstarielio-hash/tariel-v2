import * as FileSystem from "expo-file-system/legacy";

import type { AppSettings } from "../../settings/schema/types";
import type {
  MobileBootstrapResponse,
  MobileChatMode,
  MobileGuidedInspectionDraftPayload,
  MobileLaudoCard,
  MobileMesaMessage,
  MobileUser,
} from "../../types/mobile";
import {
  HISTORY_UI_STATE_FILE,
  NOTIFICATIONS_FILE,
  OFFLINE_QUEUE_FILE,
  READ_CACHE_FILE,
} from "../InspectorMobileApp.constants";
import type {
  ChatState,
  ComposerAttachment,
  MobileActivityNotification,
  OfflinePendingMessage,
} from "../chat/types";
import { normalizarQualityGateResponse } from "../chat/qualityGateHelpers";
import {
  guidedInspectionDraftFromMobilePayload,
  guidedInspectionDraftToMobilePayload,
  type GuidedInspectionDraft,
} from "../inspection/guidedInspection";
import {
  normalizarMensagemChat,
  normalizarLaudoCardResumo,
} from "../chat/conversationHelpers";
import { stripEmbeddedChatAiPreferences } from "../chat/preferences";
import type { MobileReadCache } from "./readCacheTypes";

export interface LocalHistoryUiState {
  laudosFixadosIds: number[];
  historicoOcultoIds: number[];
}

export interface LocalPersistenceScope {
  email?: string;
  userId?: number | null;
  empresaId?: number | null;
}

interface ScopedLocalEnvelope<TPayload> {
  scope: LocalPersistenceScope | null;
  payload: TPayload;
}

export const CACHE_LEITURA_VAZIO: MobileReadCache = {
  bootstrap: null,
  laudos: [],
  conversaAtual: null,
  conversasPorLaudo: {},
  mesaPorLaudo: {},
  guidedInspectionDrafts: {},
  chatDrafts: {},
  mesaDrafts: {},
  chatAttachmentDrafts: {},
  mesaAttachmentDrafts: {},
  updatedAt: "",
};

function ehRegistro(valor: unknown): valor is Record<string, unknown> {
  return Boolean(valor) && typeof valor === "object" && !Array.isArray(valor);
}

function normalizarGuidedInspectionDraftPersistido(
  value: unknown,
): MobileGuidedInspectionDraftPayload | null {
  const draft = guidedInspectionDraftFromMobilePayload(
    value as MobileGuidedInspectionDraftPayload | null | undefined,
  );
  return draft ? guidedInspectionDraftToMobilePayload(draft) : null;
}

function normalizarScopePersistencia(
  value: unknown,
): LocalPersistenceScope | null {
  if (!ehRegistro(value)) {
    return null;
  }
  const email = String(value.email || "")
    .trim()
    .toLowerCase();
  const userId =
    typeof value.userId === "number" && Number.isFinite(value.userId)
      ? value.userId
      : null;
  const empresaId =
    typeof value.empresaId === "number" && Number.isFinite(value.empresaId)
      ? value.empresaId
      : null;
  if (!email && userId == null && empresaId == null) {
    return null;
  }
  return {
    email: email || undefined,
    userId,
    empresaId,
  };
}

function scopePersistenciaCorresponde(
  expected: LocalPersistenceScope | null | undefined,
  actual: LocalPersistenceScope | null | undefined,
): boolean {
  const expectedScope = normalizarScopePersistencia(expected);
  if (!expectedScope) {
    return true;
  }

  const actualScope = normalizarScopePersistencia(actual);
  if (!actualScope) {
    return false;
  }

  if (
    expectedScope.email &&
    actualScope.email &&
    expectedScope.email !== actualScope.email
  ) {
    return false;
  }
  if (
    expectedScope.userId != null &&
    actualScope.userId != null &&
    expectedScope.userId !== actualScope.userId
  ) {
    return false;
  }
  if (
    expectedScope.empresaId != null &&
    actualScope.empresaId != null &&
    expectedScope.empresaId !== actualScope.empresaId
  ) {
    return false;
  }
  return true;
}

function construirEnvelopePersistencia<TPayload>(
  payload: TPayload,
  scope?: LocalPersistenceScope | null,
): ScopedLocalEnvelope<TPayload> {
  return {
    scope: normalizarScopePersistencia(scope),
    payload,
  };
}

function extrairEnvelopePersistencia<TPayload>(rawValue: unknown): {
  scope: LocalPersistenceScope | null;
  payload: TPayload | unknown;
  enveloped: boolean;
} {
  if (ehRegistro(rawValue) && "payload" in rawValue) {
    return {
      scope: normalizarScopePersistencia(rawValue.scope),
      payload: rawValue.payload,
      enveloped: true,
    };
  }
  return {
    scope: null,
    payload: rawValue,
    enveloped: false,
  };
}

function inferirScopeCacheBootstrap(
  bootstrap: unknown,
): LocalPersistenceScope | null {
  if (!ehRegistro(bootstrap) || !ehRegistro(bootstrap.usuario)) {
    return null;
  }
  const usuario = bootstrap.usuario as Record<string, unknown>;
  return normalizarScopePersistencia({
    email: usuario.email,
    userId: usuario.id,
    empresaId: usuario.empresa_id,
  });
}

export function buildLocalPersistenceScopeFromMobileUser(
  user: MobileUser | null | undefined,
): LocalPersistenceScope | null {
  if (!user) {
    return null;
  }
  return normalizarScopePersistencia({
    email: user.email,
    userId: user.id,
    empresaId: user.empresa_id,
  });
}

export function buildLocalPersistenceScopeFromBootstrap(
  bootstrap: MobileBootstrapResponse | null | undefined,
): LocalPersistenceScope | null {
  return buildLocalPersistenceScopeFromMobileUser(bootstrap?.usuario);
}

function normalizarIdsEstadoHistoricoLocal(valor: unknown): number[] {
  if (!Array.isArray(valor)) {
    return [];
  }

  const ids = valor
    .map((item) => (typeof item === "number" ? item : Number(item)))
    .filter((item): item is number => Number.isInteger(item) && item > 0);

  return Array.from(new Set(ids));
}

function normalizarCacheLeitura(params: {
  cacheLeituraVazio?: MobileReadCache;
  criarConversaNova: () => ChatState;
  normalizarComposerAttachment: (valor: unknown) => ComposerAttachment | null;
  payload: unknown;
}): MobileReadCache {
  const {
    cacheLeituraVazio = CACHE_LEITURA_VAZIO,
    criarConversaNova,
    normalizarComposerAttachment,
    payload,
  } = params;

  if (!payload || typeof payload !== "object") {
    return cacheLeituraVazio;
  }

  const registro = payload as Record<string, unknown>;
  const laudos = Array.isArray(registro.laudos)
    ? (registro.laudos as MobileLaudoCard[]).map((item) =>
        normalizarLaudoCardResumo(item),
      )
    : [];
  const conversaAtual =
    registro.conversaAtual && typeof registro.conversaAtual === "object"
      ? normalizarChatStatePersistido(registro.conversaAtual as ChatState)
      : null;

  const conversasPorLaudo =
    registro.conversasPorLaudo && typeof registro.conversasPorLaudo === "object"
      ? Object.fromEntries(
          Object.entries(
            registro.conversasPorLaudo as Record<string, unknown>,
          ).map(([chave, valor]) => [
            chave,
            valor && typeof valor === "object"
              ? normalizarChatStatePersistido(valor as ChatState)
              : criarConversaNova(),
          ]),
        )
      : {};

  const mesaPorLaudo =
    registro.mesaPorLaudo && typeof registro.mesaPorLaudo === "object"
      ? Object.fromEntries(
          Object.entries(registro.mesaPorLaudo as Record<string, unknown>).map(
            ([chave, valor]) => [
              chave,
              Array.isArray(valor) ? (valor as MobileMesaMessage[]) : [],
            ],
          ),
        )
      : {};

  const guidedInspectionDrafts =
    registro.guidedInspectionDrafts &&
    typeof registro.guidedInspectionDrafts === "object"
      ? Object.fromEntries(
          Object.entries(
            registro.guidedInspectionDrafts as Record<string, unknown>,
          ).filter(([, valor]) => Boolean(valor) && typeof valor === "object"),
        )
      : {};

  const chatDrafts =
    registro.chatDrafts && typeof registro.chatDrafts === "object"
      ? Object.fromEntries(
          Object.entries(registro.chatDrafts as Record<string, unknown>).map(
            ([chave, valor]) => [chave, typeof valor === "string" ? valor : ""],
          ),
        )
      : {};

  const mesaDrafts =
    registro.mesaDrafts && typeof registro.mesaDrafts === "object"
      ? Object.fromEntries(
          Object.entries(registro.mesaDrafts as Record<string, unknown>).map(
            ([chave, valor]) => [chave, typeof valor === "string" ? valor : ""],
          ),
        )
      : {};

  const chatAttachmentDrafts =
    registro.chatAttachmentDrafts &&
    typeof registro.chatAttachmentDrafts === "object"
      ? Object.fromEntries(
          Object.entries(
            registro.chatAttachmentDrafts as Record<string, unknown>,
          )
            .map(([chave, valor]) => [
              chave,
              normalizarComposerAttachment(valor),
            ])
            .filter(([, valor]) => Boolean(valor)),
        )
      : {};

  const mesaAttachmentDrafts =
    registro.mesaAttachmentDrafts &&
    typeof registro.mesaAttachmentDrafts === "object"
      ? Object.fromEntries(
          Object.entries(
            registro.mesaAttachmentDrafts as Record<string, unknown>,
          )
            .map(([chave, valor]) => [
              chave,
              normalizarComposerAttachment(valor),
            ])
            .filter(([, valor]) => Boolean(valor)),
        )
      : {};

  return {
    bootstrap:
      registro.bootstrap && typeof registro.bootstrap === "object"
        ? (registro.bootstrap as MobileBootstrapResponse)
        : null,
    laudos,
    conversaAtual,
    conversasPorLaudo,
    mesaPorLaudo,
    guidedInspectionDrafts: guidedInspectionDrafts as Record<
      string,
      GuidedInspectionDraft
    >,
    chatDrafts,
    mesaDrafts,
    chatAttachmentDrafts: chatAttachmentDrafts as Record<
      string,
      ComposerAttachment
    >,
    mesaAttachmentDrafts: mesaAttachmentDrafts as Record<
      string,
      ComposerAttachment
    >,
    updatedAt: typeof registro.updatedAt === "string" ? registro.updatedAt : "",
  };
}

function normalizarChatStatePersistido(state: ChatState): ChatState {
  return {
    ...state,
    laudoCard: normalizarLaudoCardResumo(state.laudoCard || null),
    mensagens: Array.isArray(state.mensagens)
      ? state.mensagens
          .map((item) => normalizarMensagemChat(item))
          .filter((item): item is NonNullable<typeof item> => item !== null)
      : [],
  };
}

export async function lerCacheLeituraLocal(params: {
  cacheLeituraVazio?: MobileReadCache;
  criarConversaNova: () => ChatState;
  expectedScope?: LocalPersistenceScope | null;
  normalizarComposerAttachment: (valor: unknown) => ComposerAttachment | null;
}): Promise<MobileReadCache> {
  try {
    const valor = await FileSystem.readAsStringAsync(READ_CACHE_FILE);
    const rawPayload = JSON.parse(valor);
    const envelope =
      extrairEnvelopePersistencia<Record<string, unknown>>(rawPayload);
    const payloadScope = envelope.enveloped
      ? envelope.scope
      : inferirScopeCacheBootstrap(
          ehRegistro(envelope.payload) ? envelope.payload.bootstrap : null,
        );
    if (!scopePersistenciaCorresponde(params.expectedScope, payloadScope)) {
      return params.cacheLeituraVazio || CACHE_LEITURA_VAZIO;
    }
    return normalizarCacheLeitura({
      ...params,
      payload: envelope.payload,
    });
  } catch {
    return params.cacheLeituraVazio || CACHE_LEITURA_VAZIO;
  }
}

export async function lerFilaOfflineLocal(params: {
  expectedScope?: LocalPersistenceScope | null;
  normalizarComposerAttachment: (valor: unknown) => ComposerAttachment | null;
  normalizarModoChat: (
    modo: unknown,
    fallback?: MobileChatMode,
  ) => MobileChatMode;
}): Promise<OfflinePendingMessage[]> {
  try {
    const valor = await FileSystem.readAsStringAsync(OFFLINE_QUEUE_FILE);
    const envelope = extrairEnvelopePersistencia<unknown>(JSON.parse(valor));
    if (!scopePersistenciaCorresponde(params.expectedScope, envelope.scope)) {
      return [];
    }
    const payload = envelope.payload;
    if (!Array.isArray(payload)) {
      return [];
    }
    return payload
      .filter((item) => item && typeof item === "object")
      .map((item) => {
        const registro = item as Record<string, unknown>;
        const channel: OfflinePendingMessage["channel"] =
          registro.channel === "mesa" ? "mesa" : "chat";
        const operation: OfflinePendingMessage["operation"] =
          registro.operation === "quality_gate_finalize"
            ? "quality_gate_finalize"
            : "message";
        return {
          id: String(registro.id || ""),
          channel,
          operation,
          laudoId:
            typeof registro.laudoId === "number" ? registro.laudoId : null,
          text: stripEmbeddedChatAiPreferences(
            String(registro.text || "").trim(),
            {
              fallbackHiddenOnly:
                channel === "chat" && operation === "message"
                  ? "Evidência enviada"
                  : "",
            },
          ),
          createdAt: String(registro.createdAt || ""),
          title: String(registro.title || "").trim() || "Mensagem pendente",
          attachment: params.normalizarComposerAttachment(registro.attachment),
          referenceMessageId:
            typeof registro.referenceMessageId === "number"
              ? registro.referenceMessageId
              : null,
          clientMessageId:
            typeof registro.clientMessageId === "string" &&
            registro.clientMessageId.trim()
              ? registro.clientMessageId.trim()
              : null,
          qualityGateDecision:
            registro.qualityGateDecision &&
            typeof registro.qualityGateDecision === "object"
              ? {
                  reason: String(
                    (registro.qualityGateDecision as Record<string, unknown>)
                      .reason || "",
                  ).trim(),
                  requestedCases: Array.isArray(
                    (registro.qualityGateDecision as Record<string, unknown>)
                      .requestedCases,
                  )
                    ? (
                        (
                          registro.qualityGateDecision as Record<
                            string,
                            unknown
                          >
                        ).requestedCases as unknown[]
                      )
                        .map((item: unknown) => String(item || "").trim())
                        .filter(Boolean)
                    : [],
                  responsibilityNotice: String(
                    (registro.qualityGateDecision as Record<string, unknown>)
                      .responsibilityNotice || "",
                  ).trim(),
                  gateSnapshot: normalizarQualityGateResponse(
                    (registro.qualityGateDecision as Record<string, unknown>)
                      .gateSnapshot,
                  ),
                }
              : null,
          guidedInspectionDraft: normalizarGuidedInspectionDraftPersistido(
            registro.guidedInspectionDraft,
          ),
          attempts:
            typeof registro.attempts === "number"
              ? Math.max(0, registro.attempts)
              : 0,
          lastAttemptAt: String(registro.lastAttemptAt || ""),
          lastError: String(registro.lastError || "").trim(),
          nextRetryAt: String(registro.nextRetryAt || ""),
          aiMode: params.normalizarModoChat(registro.aiMode, "detalhado"),
          aiSummary: String(registro.aiSummary || "").trim(),
          aiMessagePrefix: String(registro.aiMessagePrefix || "").trim(),
        };
      })
      .filter(
        (item) =>
          item.id &&
          (item.operation === "quality_gate_finalize" ||
            Boolean(item.text || item.attachment)),
      );
  } catch {
    return [];
  }
}

export async function salvarCacheLeituraLocal(
  cache: MobileReadCache,
  scope?: LocalPersistenceScope | null,
): Promise<void> {
  try {
    const temConteudo =
      Boolean(cache.bootstrap) ||
      Boolean(cache.conversaAtual) ||
      cache.laudos.length > 0 ||
      Object.keys(cache.conversasPorLaudo).length > 0 ||
      Object.keys(cache.mesaPorLaudo).length > 0 ||
      Object.keys(cache.guidedInspectionDrafts || {}).length > 0 ||
      Object.keys(cache.chatDrafts).length > 0 ||
      Object.keys(cache.mesaDrafts).length > 0 ||
      Object.keys(cache.chatAttachmentDrafts).length > 0 ||
      Object.keys(cache.mesaAttachmentDrafts).length > 0;

    if (!temConteudo) {
      await FileSystem.deleteAsync(READ_CACHE_FILE, {
        idempotent: true,
      });
      return;
    }

    await FileSystem.writeAsStringAsync(
      READ_CACHE_FILE,
      JSON.stringify(construirEnvelopePersistencia(cache, scope)),
    );
  } catch (error) {
    console.warn("Falha ao salvar o cache de leitura local.", error);
  }
}

export async function salvarFilaOfflineLocal(
  fila: OfflinePendingMessage[],
  scope?: LocalPersistenceScope | null,
): Promise<void> {
  try {
    if (!fila.length) {
      await FileSystem.deleteAsync(OFFLINE_QUEUE_FILE, {
        idempotent: true,
      });
      return;
    }
    await FileSystem.writeAsStringAsync(
      OFFLINE_QUEUE_FILE,
      JSON.stringify(construirEnvelopePersistencia(fila, scope)),
    );
  } catch (error) {
    console.warn("Falha ao salvar fila offline local.", error);
  }
}

export async function lerNotificacoesLocais(params?: {
  expectedScope?: LocalPersistenceScope | null;
}): Promise<MobileActivityNotification[]> {
  try {
    const valor = await FileSystem.readAsStringAsync(NOTIFICATIONS_FILE);
    const envelope = extrairEnvelopePersistencia<unknown>(JSON.parse(valor));
    if (!scopePersistenciaCorresponde(params?.expectedScope, envelope.scope)) {
      return [];
    }
    const payload = envelope.payload;
    if (!Array.isArray(payload)) {
      return [];
    }
    return payload
      .filter((item) => item && typeof item === "object")
      .map((item) => {
        const registro = item as Record<string, unknown>;
        return {
          id: String(registro.id || ""),
          kind:
            registro.kind === "mesa_nova" ||
            registro.kind === "mesa_resolvida" ||
            registro.kind === "mesa_reaberta"
              ? registro.kind
              : "status",
          laudoId:
            typeof registro.laudoId === "number" ? registro.laudoId : null,
          title: String(registro.title || "").trim() || "Atividade do inspetor",
          body: String(registro.body || "").trim(),
          createdAt:
            String(registro.createdAt || "") || new Date().toISOString(),
          unread: Boolean(registro.unread),
          targetThread: registro.targetThread === "mesa" ? "mesa" : "chat",
        } as MobileActivityNotification;
      })
      .filter((item) => item.id && item.title);
  } catch {
    return [];
  }
}

export async function salvarNotificacoesLocais(
  notificacoes: MobileActivityNotification[],
  scope?: LocalPersistenceScope | null,
): Promise<void> {
  try {
    if (!notificacoes.length) {
      await FileSystem.deleteAsync(NOTIFICATIONS_FILE, {
        idempotent: true,
      });
      return;
    }
    await FileSystem.writeAsStringAsync(
      NOTIFICATIONS_FILE,
      JSON.stringify(construirEnvelopePersistencia(notificacoes, scope)),
    );
  } catch (error) {
    console.warn("Falha ao salvar a central de atividade local.", error);
  }
}

export async function lerEstadoHistoricoLocal(): Promise<LocalHistoryUiState> {
  try {
    const valor = await FileSystem.readAsStringAsync(HISTORY_UI_STATE_FILE);
    const payload = JSON.parse(valor);
    if (!ehRegistro(payload)) {
      return { laudosFixadosIds: [], historicoOcultoIds: [] };
    }
    return {
      laudosFixadosIds: normalizarIdsEstadoHistoricoLocal(
        payload.laudosFixadosIds,
      ),
      historicoOcultoIds: normalizarIdsEstadoHistoricoLocal(
        payload.historicoOcultoIds,
      ),
    };
  } catch {
    return { laudosFixadosIds: [], historicoOcultoIds: [] };
  }
}

export async function salvarEstadoHistoricoLocal(
  estado: LocalHistoryUiState,
): Promise<void> {
  try {
    await FileSystem.writeAsStringAsync(
      HISTORY_UI_STATE_FILE,
      JSON.stringify({
        laudosFixadosIds: Array.from(new Set(estado.laudosFixadosIds)),
        historicoOcultoIds: Array.from(new Set(estado.historicoOcultoIds)),
      }),
    );
  } catch (error) {
    console.warn("Falha ao salvar o estado local do histórico.", error);
  }
}

export function limparCachePorPrivacidade(
  cache: MobileReadCache,
  cacheLeituraVazio: MobileReadCache = CACHE_LEITURA_VAZIO,
): MobileReadCache {
  return {
    ...cacheLeituraVazio,
    bootstrap: cache.bootstrap,
    updatedAt: new Date().toISOString(),
  };
}

export function obterJanelaRetencaoMs(
  value: AppSettings["dataControls"]["retention"],
): number | null {
  if (value === "30 dias") {
    return 30 * 24 * 60 * 60 * 1000;
  }
  if (value === "90 dias") {
    return 90 * 24 * 60 * 60 * 1000;
  }
  if (value === "1 ano") {
    return 365 * 24 * 60 * 60 * 1000;
  }
  return null;
}

export function filtrarItensPorRetencao<T>(
  items: T[],
  janelaMs: number | null,
  getDateIso: (item: T) => string,
): T[] {
  if (!janelaMs) {
    return items;
  }
  const limite = Date.now() - janelaMs;
  return items.filter((item) => {
    const valor = new Date(getDateIso(item)).getTime();
    if (Number.isNaN(valor)) {
      return true;
    }
    return valor >= limite;
  });
}
