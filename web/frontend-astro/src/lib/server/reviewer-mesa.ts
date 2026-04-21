import type { AuthenticatedReviewerRequest } from "@/lib/server/reviewer-auth";
import {
  fetchReviewerMesaAttachmentResponse,
  fetchReviewerMesaMessages,
  fetchReviewerMesaPackage,
  markReviewerMesaWhispersRead,
  replyToReviewerMesa,
  replyToReviewerMesaWithAttachment,
  reviewReviewerMesaCase,
  updateReviewerMesaPendency,
  type ReviewerMesaAttachmentPayload,
  type ReviewerMesaMessagePayload,
  type ReviewerMesaPackageItemPayload,
  type ReviewerMesaPackagePayload,
} from "@/lib/server/reviewer-mesa-bridge";
import {
  fetchReviewerPanelSnapshot,
  type ReviewQueueDashboardProjection,
  type ReviewQueueItemPayload,
} from "@/lib/server/reviewer-panel-bridge";

export interface ReviewerMesaAttachment {
  id: number;
  name: string;
  mimeType: string;
  category: string;
  sizeBytes: number;
  isImage: boolean;
  downloadPath: string;
}

export interface ReviewerMesaThreadMessage {
  id: number;
  legacyType: string;
  itemKind: string;
  messageKind: string;
  pendencyState: string;
  text: string;
  createdAtLabel: string;
  isWhisper: boolean;
  senderId: number | null;
  referenceMessageId: number | null;
  attachments: ReviewerMesaAttachment[];
  operationalContext: Record<string, unknown> | null;
  canTogglePendency: boolean;
  isResolvedPendency: boolean;
}

export interface ReviewerMesaPackageMessage {
  id: number;
  legacyType: string;
  itemKind: string;
  messageKind: string;
  pendencyState: string;
  text: string;
  createdAt: Date | null;
  createdAtLabel: string;
  senderId: number | null;
  referenceMessageId: number | null;
  resolvedAt: Date | null;
  resolvedAtLabel: string | null;
  resolvedById: number | null;
  resolvedByName: string | null;
  read: boolean;
  attachments: ReviewerMesaAttachment[];
}

export interface ReviewerMesaSelectedPackage {
  laudoId: number;
  codeHash: string;
  templateType: string;
  sector: string;
  reviewStatus: string;
  complianceStatus: string;
  lifecycleStatus: string;
  workflowMode: string;
  activeOwnerRole: string;
  allowedSurfaceActions: string[];
  statusVisualLabel: string;
  createdAt: Date | null;
  createdAtLabel: string;
  updatedAt: Date | null;
  updatedAtLabel: string;
  lastInteractionAt: Date | null;
  lastInteractionLabel: string;
  fieldTimeMinutes: number;
  aiSummary: string | null;
  messageSummary: {
    total: number;
    inspector: number;
    ai: number;
    mesa: number;
    systemOthers: number;
  };
  evidenceSummary: {
    total: number;
    text: number;
    images: number;
    documents: number;
  };
  pendencySummary: {
    total: number;
    open: number;
    resolved: number;
  };
  openPendencies: ReviewerMesaPackageMessage[];
  recentResolvedPendencies: ReviewerMesaPackageMessage[];
  recentWhispers: ReviewerMesaPackageMessage[];
}

export interface ReviewerMesaSelectedCase {
  item: ReviewQueueItemPayload;
  messages: ReviewerMesaThreadMessage[];
  package: ReviewerMesaSelectedPackage;
}

export interface ReviewerMesaWorkspace {
  projection: ReviewQueueDashboardProjection;
  searchTerm: string;
  operationFilter: string;
  learningFilter: string;
  activeCases: ReviewQueueItemPayload[];
  historyCases: ReviewQueueItemPayload[];
  filteredCases: ReviewQueueItemPayload[];
  pendingCases: ReviewQueueItemPayload[];
  selectedCase: ReviewerMesaSelectedCase | null;
}

export async function getReviewerMesaWorkspace(
  reviewerSession: AuthenticatedReviewerRequest,
  input: {
    searchTerm?: string | null;
    operationFilter?: string | null;
    learningFilter?: string | null;
    selectedLaudoId?: number | null;
  },
) {
  const searchTerm = String(input.searchTerm ?? "").trim();
  const operationFilter = String(input.operationFilter ?? "").trim().toLowerCase();
  const learningFilter = String(input.learningFilter ?? "").trim().toLowerCase();
  const params = new URLSearchParams();
  if (searchTerm) params.set("q", searchTerm);
  if (operationFilter) params.set("operacao", operationFilter);
  if (learningFilter) params.set("aprendizados", learningFilter);

  const projection = await fetchReviewerPanelSnapshot(reviewerSession, params);
  const activeCases = [
    ...projection.payload.queue_sections.em_andamento,
    ...projection.payload.queue_sections.aguardando_avaliacao,
  ];
  const historyCases = [...projection.payload.queue_sections.historico];
  const filteredCases = [...activeCases, ...historyCases];
  const pendingCases = filteredCases.filter(
    (item) => item.whispers_nao_lidos > 0 || item.pendencias_abertas > 0 || item.aprendizados_pendentes > 0,
  );
  const selectedItem = resolveSelectedReviewerMesaCase({
    requestedId: input.selectedLaudoId ?? null,
    activeCases,
    historyCases,
    pendingCases,
  });

  if (!selectedItem) {
    return {
      projection,
      searchTerm,
      operationFilter,
      learningFilter,
      activeCases,
      historyCases,
      filteredCases,
      pendingCases,
      selectedCase: null,
    } satisfies ReviewerMesaWorkspace;
  }

  const [messagesPayload, packagePayload] = await Promise.all([
    fetchReviewerMesaMessages(reviewerSession, selectedItem.id),
    fetchReviewerMesaPackage(reviewerSession, selectedItem.id),
  ]);

  return {
    projection,
    searchTerm,
    operationFilter,
    learningFilter,
    activeCases,
    historyCases,
    filteredCases,
    pendingCases,
    selectedCase: {
      item: selectedItem,
      messages: messagesPayload.itens.map((message) => mapReviewerMesaThreadMessage(selectedItem.id, message)),
      package: mapReviewerMesaPackage(packagePayload),
    },
  } satisfies ReviewerMesaWorkspace;
}

export async function replyReviewerMesaCase(
  reviewerSession: AuthenticatedReviewerRequest,
  input: {
    laudoId: number;
    text: string;
    referenceMessageId?: number | null;
    file?: File | null;
  },
) {
  const normalizedText = String(input.text ?? "").trim();

  if (!normalizedText && !input.file) {
    throw new Error("Escreva uma resposta ou selecione um anexo.");
  }

  if (input.file) {
    return replyToReviewerMesaWithAttachment(reviewerSession, {
      laudoId: input.laudoId,
      arquivo: input.file,
      texto: normalizedText,
      referenciaMensagemId: input.referenceMessageId ?? null,
    });
  }

  return replyToReviewerMesa(reviewerSession, {
    laudoId: input.laudoId,
    texto: normalizedText,
    referenciaMensagemId: input.referenceMessageId ?? null,
  });
}

export async function reviewReviewerMesaCaseDecision(
  reviewerSession: AuthenticatedReviewerRequest,
  input: {
    laudoId: number;
    action: "aprovar" | "rejeitar";
    reason?: string;
  },
) {
  return reviewReviewerMesaCase(reviewerSession, {
    laudoId: input.laudoId,
    acao: input.action,
    motivo: String(input.reason ?? "").trim(),
  });
}

export async function toggleReviewerMesaPendency(
  reviewerSession: AuthenticatedReviewerRequest,
  input: {
    laudoId: number;
    mensagemId: number;
    resolved: boolean;
  },
) {
  return updateReviewerMesaPendency(reviewerSession, {
    laudoId: input.laudoId,
    mensagemId: input.mensagemId,
    lida: input.resolved,
  });
}

export async function syncReviewerMesaWhispersRead(
  reviewerSession: AuthenticatedReviewerRequest,
  laudoId: number,
) {
  return markReviewerMesaWhispersRead(reviewerSession, laudoId);
}

export async function fetchReviewerMesaAttachment(
  reviewerSession: AuthenticatedReviewerRequest,
  input: {
    laudoId: number;
    anexoId: number;
  },
) {
  return fetchReviewerMesaAttachmentResponse(reviewerSession, input);
}

function resolveSelectedReviewerMesaCase(input: {
  requestedId: number | null;
  activeCases: ReviewQueueItemPayload[];
  historyCases: ReviewQueueItemPayload[];
  pendingCases: ReviewQueueItemPayload[];
}) {
  if (input.requestedId) {
    const requested = [...input.activeCases, ...input.historyCases].find((item) => item.id === input.requestedId);
    if (requested) {
      return requested;
    }
  }

  return input.pendingCases[0] ?? input.activeCases[0] ?? input.historyCases[0] ?? null;
}

function mapReviewerMesaThreadMessage(
  laudoId: number,
  payload: ReviewerMesaMessagePayload,
): ReviewerMesaThreadMessage {
  return {
    id: payload.id,
    legacyType: payload.tipo,
    itemKind: payload.item_kind,
    messageKind: payload.message_kind,
    pendencyState: payload.pendency_state,
    text: payload.texto,
    createdAtLabel: payload.data,
    isWhisper: Boolean(payload.is_whisper),
    senderId: payload.remetente_id ?? null,
    referenceMessageId: payload.referencia_mensagem_id ?? null,
    attachments: (payload.anexos ?? []).map((attachment) => mapReviewerMesaAttachment(laudoId, attachment)),
    operationalContext: payload.operational_context ?? null,
    canTogglePendency: payload.message_kind === "mesa_pendency",
    isResolvedPendency: payload.pendency_state === "resolved",
  };
}

function mapReviewerMesaPackage(payload: ReviewerMesaPackagePayload): ReviewerMesaSelectedPackage {
  return {
    laudoId: payload.laudo_id,
    codeHash: payload.codigo_hash,
    templateType: payload.tipo_template,
    sector: payload.setor_industrial,
    reviewStatus: payload.status_revisao,
    complianceStatus: payload.status_conformidade,
    lifecycleStatus: payload.case_lifecycle_status,
    workflowMode: payload.case_workflow_mode,
    activeOwnerRole: payload.active_owner_role,
    allowedSurfaceActions: [...payload.allowed_surface_actions],
    statusVisualLabel: payload.status_visual_label,
    createdAt: parseDateOrNull(payload.criado_em),
    createdAtLabel: formatDateTime(parseDateOrNull(payload.criado_em), "Sem criacao"),
    updatedAt: parseDateOrNull(payload.atualizado_em),
    updatedAtLabel: formatDateTime(parseDateOrNull(payload.atualizado_em), "Sem atualizacao"),
    lastInteractionAt: parseDateOrNull(payload.ultima_interacao_em),
    lastInteractionLabel: formatDateTime(parseDateOrNull(payload.ultima_interacao_em), "Sem interacao recente"),
    fieldTimeMinutes: payload.tempo_em_campo_minutos,
    aiSummary: payload.parecer_ia || null,
    messageSummary: {
      total: payload.resumo_mensagens.total,
      inspector: payload.resumo_mensagens.inspetor,
      ai: payload.resumo_mensagens.ia,
      mesa: payload.resumo_mensagens.mesa,
      systemOthers: payload.resumo_mensagens.sistema_outros,
    },
    evidenceSummary: {
      total: payload.resumo_evidencias.total,
      text: payload.resumo_evidencias.textuais,
      images: payload.resumo_evidencias.fotos,
      documents: payload.resumo_evidencias.documentos,
    },
    pendencySummary: {
      total: payload.resumo_pendencias.total,
      open: payload.resumo_pendencias.abertas,
      resolved: payload.resumo_pendencias.resolvidas,
    },
    openPendencies: payload.pendencias_abertas.map((item) => mapReviewerMesaPackageMessage(payload.laudo_id, item)),
    recentResolvedPendencies: payload.pendencias_resolvidas_recentes.map((item) =>
      mapReviewerMesaPackageMessage(payload.laudo_id, item),
    ),
    recentWhispers: payload.whispers_recentes.map((item) => mapReviewerMesaPackageMessage(payload.laudo_id, item)),
  };
}

function mapReviewerMesaPackageMessage(
  laudoId: number,
  payload: ReviewerMesaPackageItemPayload,
): ReviewerMesaPackageMessage {
  const createdAt = parseDateOrNull(payload.criado_em);
  const resolvedAt = parseDateOrNull(payload.resolvida_em);

  return {
    id: payload.id,
    legacyType: payload.tipo,
    itemKind: payload.item_kind,
    messageKind: payload.message_kind,
    pendencyState: payload.pendency_state,
    text: payload.texto,
    createdAt,
    createdAtLabel: formatDateTime(createdAt, "Sem data"),
    senderId: payload.remetente_id ?? null,
    referenceMessageId: payload.referencia_mensagem_id ?? null,
    resolvedAt,
    resolvedAtLabel: resolvedAt ? formatDateTime(resolvedAt, "") : null,
    resolvedById: payload.resolvida_por_id ?? null,
    resolvedByName: payload.resolvida_por_nome ?? null,
    read: Boolean(payload.lida),
    attachments: payload.anexos.map((attachment) => mapReviewerMesaAttachment(laudoId, attachment)),
  };
}

function mapReviewerMesaAttachment(
  laudoId: number,
  attachment: ReviewerMesaAttachmentPayload,
): ReviewerMesaAttachment {
  return {
    id: attachment.id,
    name: attachment.nome,
    mimeType: attachment.mime_type,
    category: attachment.categoria,
    sizeBytes: attachment.tamanho_bytes,
    isImage: attachment.eh_imagem,
    downloadPath: `/revisao/painel/${laudoId}/anexos/${attachment.id}`,
  };
}

function parseDateOrNull(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDateTime(value: Date | null, fallback: string) {
  if (!value) {
    return fallback;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(value);
}
