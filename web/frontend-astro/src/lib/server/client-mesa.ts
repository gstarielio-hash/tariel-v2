import type { AuthenticatedClientRequest } from "@/lib/server/client-auth";
import {
  fetchClientMesaMessages,
  fetchClientMesaPackage,
  fetchClientMesaAttachmentResponse,
  markClientMesaWhispersRead,
  replyToClientMesa,
  replyToClientMesaWithAttachment,
  reviewClientMesaCase,
  updateClientMesaPendency,
  type ClientMesaAttachmentPayload,
  type ClientMesaMessagePayload,
  type ClientMesaPackageCoverageItemPayload,
  type ClientMesaPackageItemPayload,
  type ClientMesaPackagePayload,
  type ClientMesaPackageReviewPayload,
  type ClientMesaPackageSectionPayload,
} from "@/lib/server/client-mesa-bridge";
import {
  getClientPortalMesaData,
  type ClientPortalMesaData,
  type ClientPortalMesaQueueItem,
} from "@/lib/server/client-portal";

export type ClientMesaSection = "overview" | "queue" | "pending" | "reply";

export interface ClientMesaAttachment {
  id: number;
  name: string;
  mimeType: string;
  category: string;
  sizeBytes: number;
  isImage: boolean;
  downloadPath: string;
}

export interface ClientMesaThreadMessage {
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
  attachments: ClientMesaAttachment[];
  operationalContext: Record<string, unknown> | null;
  canTogglePendency: boolean;
  isResolvedPendency: boolean;
}

export interface ClientMesaPackageMessage {
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
  attachments: ClientMesaAttachment[];
}

export interface ClientMesaPackageReview {
  version: number;
  origin: string;
  summary: string | null;
  confidenceLabel: string | null;
  createdAt: Date | null;
  createdAtLabel: string;
}

export interface ClientMesaStructuredSection {
  key: string;
  title: string;
  status: string;
  summary: string | null;
  diffShort: string | null;
  filledFields: number;
  totalFields: number;
}

export interface ClientMesaCoverageItem {
  evidenceKey: string;
  title: string;
  kind: string;
  status: string;
  required: boolean;
  sourceStatus: string | null;
  operationalStatus: string | null;
  mesaStatus: string | null;
  componentType: string | null;
  viewAngle: string | null;
  qualityScore: number | null;
  coherenceScore: number | null;
  replacementEvidenceKey: string | null;
  summary: string | null;
  failureReasons: string[];
}

export interface ClientMesaSelectedPackage {
  laudoId: number;
  codeHash: string;
  templateType: string;
  sector: string;
  reviewStatus: string;
  complianceStatus: string;
  caseStatus: string;
  lifecycleStatus: string;
  workflowMode: string;
  activeOwnerRole: string;
  allowedNextLifecycleStatuses: string[];
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
  humanOverrideLatest: {
    actorName: string;
    reason: string;
    appliedAt: Date | null;
    appliedAtLabel: string;
  } | null;
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
  structuredDocument: {
    schemaType: string;
    familyKey: string | null;
    familyLabel: string | null;
    summary: string | null;
    reviewNotes: string | null;
    sections: ClientMesaStructuredSection[];
  } | null;
  coverage: {
    totalRequired: number;
    totalCollected: number;
    totalAccepted: number;
    totalMissing: number;
    totalIrregular: number;
    finalValidationMode: string | null;
    items: ClientMesaCoverageItem[];
  } | null;
  attachmentPack: {
    totalItems: number;
    totalRequired: number;
    totalPresent: number;
    missingRequiredCount: number;
    documentCount: number;
    imageCount: number;
    virtualCount: number;
    readyForIssue: boolean;
    missingItems: string[];
  } | null;
  publicVerification: {
    verificationUrl: string;
    hashShort: string;
    statusVisualLabel: string | null;
    approvedAt: Date | null;
    approvedAtLabel: string;
  } | null;
  officialIssue: {
    issueStatus: string;
    issueStatusLabel: string;
    readyForIssue: boolean;
    blockerCount: number;
    alreadyIssued: boolean;
    reissueRecommended: boolean;
    issueActionLabel: string | null;
    issueActionEnabled: boolean;
    verificationUrl: string | null;
  } | null;
  openPendencies: ClientMesaPackageMessage[];
  recentResolvedPendencies: ClientMesaPackageMessage[];
  recentWhispers: ClientMesaPackageMessage[];
  recentReviews: ClientMesaPackageReview[];
}

export interface ClientMesaSelectedCase {
  item: ClientPortalMesaQueueItem;
  messages: ClientMesaThreadMessage[];
  package: ClientMesaSelectedPackage;
}

export interface ClientMesaWorkspace {
  snapshot: ClientPortalMesaData;
  section: ClientMesaSection;
  searchTerm: string;
  queueCases: ClientPortalMesaQueueItem[];
  historyCases: ClientPortalMesaQueueItem[];
  filteredQueueCases: ClientPortalMesaQueueItem[];
  filteredHistoryCases: ClientPortalMesaQueueItem[];
  filteredCases: ClientPortalMesaQueueItem[];
  pendingCases: ClientPortalMesaQueueItem[];
  selectedCase: ClientMesaSelectedCase | null;
}

const DEFAULT_SECTION: ClientMesaSection = "overview";
const VALID_SECTIONS: ClientMesaSection[] = ["overview", "queue", "pending", "reply"];

export function normalizeClientMesaSection(value: string | null | undefined): ClientMesaSection {
  const normalized = String(value ?? "").trim().toLowerCase();
  return VALID_SECTIONS.includes(normalized as ClientMesaSection)
    ? (normalized as ClientMesaSection)
    : DEFAULT_SECTION;
}

export async function getClientMesaWorkspace(
  clientSession: AuthenticatedClientRequest,
  input: {
    section?: string | null;
    searchTerm?: string | null;
    selectedLaudoId?: number | null;
  },
): Promise<ClientMesaWorkspace | null> {
  const snapshot = await getClientPortalMesaData(clientSession);
  if (!snapshot) {
    return null;
  }

  const section = normalizeClientMesaSection(input.section);
  const searchTerm = String(input.searchTerm ?? "").trim();
  const queueCases = [...snapshot.queue.awaitingReview, ...snapshot.queue.inField];
  const historyCases = [...snapshot.queue.history];
  const allCases = [...queueCases, ...historyCases];
  const filteredQueueCases = queueCases.filter((item) => matchesClientMesaSearch(item, searchTerm));
  const filteredHistoryCases = historyCases.filter((item) => matchesClientMesaSearch(item, searchTerm));
  const filteredCases = allCases.filter((item) => matchesClientMesaSearch(item, searchTerm));
  const pendingCases = filteredCases.filter(
    (item) => item.whispersPending > 0 || item.openPendencies > 0 || item.pendingLearning > 0,
  );

  const selectedItem =
    resolveSelectedClientMesaCase({
      requestedId: input.selectedLaudoId ?? null,
      allCases,
      queueCases: filteredQueueCases,
      pendingCases,
      section,
    }) ?? null;

  if (!selectedItem) {
    return {
      snapshot,
      section,
      searchTerm,
      queueCases,
      historyCases,
      filteredQueueCases,
      filteredHistoryCases,
      filteredCases,
      pendingCases,
      selectedCase: null,
    };
  }

  const [messagesPayload, packagePayload] = await Promise.all([
    fetchClientMesaMessages(clientSession, selectedItem.id),
    fetchClientMesaPackage(clientSession, selectedItem.id),
  ]);

  return {
    snapshot,
    section,
    searchTerm,
    queueCases,
    historyCases,
    filteredQueueCases,
    filteredHistoryCases,
    filteredCases,
    pendingCases,
    selectedCase: {
      item: selectedItem,
      messages: messagesPayload.itens.map((message) => mapClientMesaThreadMessage(selectedItem.id, message)),
      package: mapClientMesaPackage(packagePayload),
    },
  };
}

export async function replyClientMesaCase(
  clientSession: AuthenticatedClientRequest,
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
    return replyToClientMesaWithAttachment(clientSession, {
      laudoId: input.laudoId,
      arquivo: input.file,
      texto: normalizedText,
      referenciaMensagemId: input.referenceMessageId ?? null,
    });
  }

  return replyToClientMesa(clientSession, {
    laudoId: input.laudoId,
    texto: normalizedText,
    referenciaMensagemId: input.referenceMessageId ?? null,
  });
}

export async function reviewClientMesaCaseDecision(
  clientSession: AuthenticatedClientRequest,
  input: {
    laudoId: number;
    action: "aprovar" | "rejeitar";
    reason?: string;
  },
) {
  return reviewClientMesaCase(clientSession, {
    laudoId: input.laudoId,
    acao: input.action,
    motivo: String(input.reason ?? "").trim(),
  });
}

export async function toggleClientMesaPendency(
  clientSession: AuthenticatedClientRequest,
  input: {
    laudoId: number;
    mensagemId: number;
    resolved: boolean;
  },
) {
  return updateClientMesaPendency(clientSession, {
    laudoId: input.laudoId,
    mensagemId: input.mensagemId,
    lida: input.resolved,
  });
}

export async function syncClientMesaWhispersRead(
  clientSession: AuthenticatedClientRequest,
  laudoId: number,
) {
  return markClientMesaWhispersRead(clientSession, laudoId);
}

export async function fetchClientMesaAttachment(
  clientSession: AuthenticatedClientRequest,
  input: {
    laudoId: number;
    anexoId: number;
  },
) {
  return fetchClientMesaAttachmentResponse(clientSession, input);
}

function resolveSelectedClientMesaCase(input: {
  requestedId: number | null;
  allCases: ClientPortalMesaQueueItem[];
  queueCases: ClientPortalMesaQueueItem[];
  pendingCases: ClientPortalMesaQueueItem[];
  section: ClientMesaSection;
}) {
  const requested = input.requestedId
    ? input.allCases.find((item) => item.id === input.requestedId) ?? null
    : null;

  if (requested) {
    return requested;
  }

  if (input.section === "reply") {
    return input.queueCases[0] ?? null;
  }

  if (input.section === "pending") {
    return input.pendingCases[0] ?? null;
  }

  if (input.section === "queue") {
    return input.queueCases[0] ?? null;
  }

  return null;
}

function matchesClientMesaSearch(item: ClientPortalMesaQueueItem, searchTerm: string) {
  if (!searchTerm) {
    return true;
  }

  const normalizedSearch = normalizeSearch(searchTerm);
  const haystack = [
    item.hashShort,
    item.title,
    item.sector,
    item.reviewStatus,
    item.statusVisualLabel,
    item.operationLabel,
    item.priorityLabel,
    item.nextAction,
    item.inspectorName,
  ]
    .map(normalizeSearch)
    .join(" ");

  return haystack.includes(normalizedSearch);
}

function normalizeSearch(value: string) {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

function mapClientMesaThreadMessage(
  laudoId: number,
  payload: ClientMesaMessagePayload,
): ClientMesaThreadMessage {
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
    attachments: (payload.anexos ?? []).map((attachment) => mapClientMesaAttachment(laudoId, attachment)),
    operationalContext: payload.operational_context ?? null,
    canTogglePendency: payload.message_kind === "mesa_pendency",
    isResolvedPendency: payload.pendency_state === "resolved",
  };
}

function mapClientMesaAttachment(
  laudoId: number,
  attachment: ClientMesaAttachmentPayload,
): ClientMesaAttachment {
  return {
    id: attachment.id,
    name: attachment.nome,
    mimeType: attachment.mime_type,
    category: attachment.categoria,
    sizeBytes: attachment.tamanho_bytes,
    isImage: attachment.eh_imagem,
    downloadPath: `/cliente/mesa/${laudoId}/anexos/${attachment.id}`,
  };
}

function mapClientMesaPackage(payload: ClientMesaPackagePayload): ClientMesaSelectedPackage {
  return {
    laudoId: payload.laudo_id,
    codeHash: payload.codigo_hash,
    templateType: payload.tipo_template,
    sector: payload.setor_industrial,
    reviewStatus: payload.status_revisao,
    complianceStatus: payload.status_conformidade,
    caseStatus: payload.case_status,
    lifecycleStatus: payload.case_lifecycle_status,
    workflowMode: payload.case_workflow_mode,
    activeOwnerRole: payload.active_owner_role,
    allowedNextLifecycleStatuses: [...payload.allowed_next_lifecycle_statuses],
    allowedSurfaceActions: [...payload.allowed_surface_actions],
    statusVisualLabel: payload.status_visual_label,
    createdAt: parseDateOrNull(payload.criado_em),
    createdAtLabel: formatDateTime(parseDateOrNull(payload.criado_em), "Sem criação"),
    updatedAt: parseDateOrNull(payload.atualizado_em),
    updatedAtLabel: formatDateTime(parseDateOrNull(payload.atualizado_em), "Sem atualização"),
    lastInteractionAt: parseDateOrNull(payload.ultima_interacao_em),
    lastInteractionLabel: formatDateTime(parseDateOrNull(payload.ultima_interacao_em), "Sem interação recente"),
    fieldTimeMinutes: payload.tempo_em_campo_minutos,
    aiSummary: payload.parecer_ia || null,
    humanOverrideLatest: mapHumanOverride(payload),
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
    structuredDocument: payload.documento_estruturado
      ? {
          schemaType: payload.documento_estruturado.schema_type,
          familyKey: payload.documento_estruturado.family_key,
          familyLabel: payload.documento_estruturado.family_label,
          summary: payload.documento_estruturado.summary,
          reviewNotes: payload.documento_estruturado.review_notes,
          sections: payload.documento_estruturado.sections.map(mapClientMesaStructuredSection),
        }
      : null,
    coverage: payload.coverage_map
      ? {
          totalRequired: payload.coverage_map.total_required,
          totalCollected: payload.coverage_map.total_collected,
          totalAccepted: payload.coverage_map.total_accepted,
          totalMissing: payload.coverage_map.total_missing,
          totalIrregular: payload.coverage_map.total_irregular,
          finalValidationMode: payload.coverage_map.final_validation_mode,
          items: payload.coverage_map.items.map(mapClientMesaCoverageItem),
        }
      : null,
    attachmentPack: payload.anexo_pack
      ? {
          totalItems: payload.anexo_pack.total_items,
          totalRequired: payload.anexo_pack.total_required,
          totalPresent: payload.anexo_pack.total_present,
          missingRequiredCount: payload.anexo_pack.missing_required_count,
          documentCount: payload.anexo_pack.document_count,
          imageCount: payload.anexo_pack.image_count,
          virtualCount: payload.anexo_pack.virtual_count,
          readyForIssue: payload.anexo_pack.ready_for_issue,
          missingItems: [...payload.anexo_pack.missing_items],
        }
      : null,
    publicVerification: payload.verificacao_publica
      ? {
          verificationUrl: payload.verificacao_publica.verification_url,
          hashShort: payload.verificacao_publica.hash_short,
          statusVisualLabel: payload.verificacao_publica.status_visual_label,
          approvedAt: parseDateOrNull(payload.verificacao_publica.approved_at),
          approvedAtLabel: formatDateTime(parseDateOrNull(payload.verificacao_publica.approved_at), "Sem aprovação"),
        }
      : null,
    officialIssue: payload.emissao_oficial
      ? {
          issueStatus: payload.emissao_oficial.issue_status,
          issueStatusLabel: payload.emissao_oficial.issue_status_label,
          readyForIssue: payload.emissao_oficial.ready_for_issue,
          blockerCount: payload.emissao_oficial.blocker_count,
          alreadyIssued: payload.emissao_oficial.already_issued,
          reissueRecommended: payload.emissao_oficial.reissue_recommended,
          issueActionLabel: payload.emissao_oficial.issue_action_label,
          issueActionEnabled: payload.emissao_oficial.issue_action_enabled,
          verificationUrl: payload.emissao_oficial.verification_url,
        }
      : null,
    openPendencies: payload.pendencias_abertas.map((item) => mapClientMesaPackageMessage(payload.laudo_id, item)),
    recentResolvedPendencies: payload.pendencias_resolvidas_recentes.map((item) =>
      mapClientMesaPackageMessage(payload.laudo_id, item),
    ),
    recentWhispers: payload.whispers_recentes.map((item) => mapClientMesaPackageMessage(payload.laudo_id, item)),
    recentReviews: payload.revisoes_recentes.map(mapClientMesaReview),
  };
}

function mapHumanOverride(payload: ClientMesaPackagePayload) {
  const latest = payload.human_override_summary?.latest;
  if (!latest) {
    return null;
  }

  const appliedAt = parseDateOrNull(latest.applied_at);
  return {
    actorName: String(latest.actor_name ?? "").trim() || "Validador humano",
    reason: String(latest.reason ?? "").trim() || "Justificativa auditável registrada.",
    appliedAt,
    appliedAtLabel: formatDateTime(appliedAt, "Sem timestamp"),
  };
}

function mapClientMesaStructuredSection(
  section: ClientMesaPackageSectionPayload,
): ClientMesaStructuredSection {
  return {
    key: section.key,
    title: section.title,
    status: section.status,
    summary: section.summary,
    diffShort: section.diff_short,
    filledFields: section.filled_fields,
    totalFields: section.total_fields,
  };
}

function mapClientMesaCoverageItem(
  item: ClientMesaPackageCoverageItemPayload,
): ClientMesaCoverageItem {
  return {
    evidenceKey: item.evidence_key,
    title: item.title,
    kind: item.kind,
    status: item.status,
    required: item.required,
    sourceStatus: item.source_status,
    operationalStatus: item.operational_status,
    mesaStatus: item.mesa_status,
    componentType: item.component_type,
    viewAngle: item.view_angle,
    qualityScore: item.quality_score,
    coherenceScore: item.coherence_score,
    replacementEvidenceKey: item.replacement_evidence_key,
    summary: item.summary,
    failureReasons: [...item.failure_reasons],
  };
}

function mapClientMesaPackageMessage(
  laudoId: number,
  item: ClientMesaPackageItemPayload,
): ClientMesaPackageMessage {
  const createdAt = parseDateOrNull(item.criado_em);
  const resolvedAt = parseDateOrNull(item.resolvida_em);

  return {
    id: item.id,
    legacyType: item.tipo,
    itemKind: item.item_kind,
    messageKind: item.message_kind,
    pendencyState: item.pendency_state,
    text: item.texto,
    createdAt,
    createdAtLabel: formatDateTime(createdAt, "Sem data"),
    senderId: item.remetente_id ?? null,
    referenceMessageId: item.referencia_mensagem_id ?? null,
    resolvedAt,
    resolvedAtLabel: resolvedAt ? formatDateTime(resolvedAt, "Sem resolução") : null,
    resolvedById: item.resolvida_por_id ?? null,
    resolvedByName: item.resolvida_por_nome ?? null,
    read: Boolean(item.lida),
    attachments: (item.anexos ?? []).map((attachment) => mapClientMesaAttachment(laudoId, attachment)),
  };
}

function mapClientMesaReview(review: ClientMesaPackageReviewPayload): ClientMesaPackageReview {
  const createdAt = parseDateOrNull(review.criado_em);
  return {
    version: review.numero_versao,
    origin: review.origem,
    summary: review.resumo,
    confidenceLabel: review.confianca_geral,
    createdAt,
    createdAtLabel: formatDateTime(createdAt, "Sem revisão"),
  };
}

function parseDateOrNull(value: string | null | undefined) {
  const normalized = String(value ?? "").trim();
  if (!normalized) {
    return null;
  }

  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDateTime(value: Date | null | undefined, fallback: string) {
  if (!value) {
    return fallback;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(value);
}
