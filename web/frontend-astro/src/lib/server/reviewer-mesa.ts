import type { AuthenticatedReviewerRequest } from "@/lib/server/reviewer-auth";
import {
  fetchReviewerMesaAttachmentResponse,
  fetchReviewerMesaFrozenOfficialBundleResponse,
  fetchReviewerMesaMessages,
  fetchReviewerMesaOfficialZipResponse,
  fetchReviewerMesaPackage,
  fetchReviewerMesaPackagePdfResponse,
  issueReviewerMesaOfficially,
  markReviewerMesaWhispersRead,
  replyToReviewerMesa,
  replyToReviewerMesaWithAttachment,
  requestReviewerMesaCoverageReturn,
  reviewReviewerMesaCase,
  updateReviewerMesaPendency,
  type ReviewerMesaAttachmentPayload,
  type ReviewerMesaCoverageItemPayload,
  type ReviewerMesaMessagePayload,
  type ReviewerMesaPackageItemPayload,
  type ReviewerMesaPackagePayload,
  type ReviewerMesaPackageSectionPayload,
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

export interface ReviewerMesaStructuredSection {
  key: string;
  title: string;
  status: string;
  summary: string | null;
  diffShort: string | null;
  filledFields: number;
  totalFields: number;
}

export interface ReviewerMesaCoverageItem {
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

export interface ReviewerMesaOfficialSignatory {
  id: number;
  name: string;
  role: string;
  registration: string | null;
  validUntil: Date | null;
  validUntilLabel: string;
  status: string;
  statusLabel: string;
  active: boolean;
  notes: string | null;
}

export interface ReviewerMesaOfficialCurrentIssue {
  id: number;
  issueNumber: string | null;
  issueState: string;
  issueStateLabel: string;
  issuedAt: Date | null;
  issuedAtLabel: string;
  packageSha256: string | null;
  packageStorageReady: boolean;
  signatoryName: string | null;
  signatoryRegistration: string | null;
  primaryPdfDiverged: boolean;
  reissueOfIssueId: number | null;
  reissueOfIssueNumber: string | null;
  reissueReasonCodes: string[];
  reissueReasonSummary: string | null;
}

export interface ReviewerMesaOfficialBlocker {
  code: string;
  title: string;
  message: string;
  blocking: boolean;
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
  structuredDocument: {
    schemaType: string;
    familyKey: string | null;
    familyLabel: string | null;
    summary: string | null;
    reviewNotes: string | null;
    sections: ReviewerMesaStructuredSection[];
  } | null;
  coverage: {
    totalRequired: number;
    totalCollected: number;
    totalAccepted: number;
    totalMissing: number;
    totalIrregular: number;
    finalValidationMode: string | null;
    items: ReviewerMesaCoverageItem[];
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
    requiresHumanSignature: boolean;
    compatibleSignatoryCount: number;
    eligibleSignatoryCount: number;
    blockerCount: number;
    signatureStatus: string | null;
    signatureStatusLabel: string | null;
    alreadyIssued: boolean;
    reissueRecommended: boolean;
    issueActionLabel: string | null;
    issueActionEnabled: boolean;
    verificationUrl: string | null;
    signatories: ReviewerMesaOfficialSignatory[];
    blockers: ReviewerMesaOfficialBlocker[];
    currentIssue: ReviewerMesaOfficialCurrentIssue | null;
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

export async function requestReviewerMesaCoverageRefazer(
  reviewerSession: AuthenticatedReviewerRequest,
  input: {
    laudoId: number;
    evidenceKey: string;
    title: string;
    kind: string;
    required: boolean;
    sourceStatus?: string | null;
    operationalStatus?: string | null;
    mesaStatus?: string | null;
    componentType?: string | null;
    viewAngle?: string | null;
    summary?: string | null;
    failureReasons?: string[];
  },
) {
  return requestReviewerMesaCoverageReturn(reviewerSession, input);
}

export async function fetchReviewerMesaPackagePdf(
  reviewerSession: AuthenticatedReviewerRequest,
  laudoId: number,
) {
  return fetchReviewerMesaPackagePdfResponse(reviewerSession, laudoId);
}

export async function fetchReviewerMesaOfficialZip(
  reviewerSession: AuthenticatedReviewerRequest,
  laudoId: number,
) {
  return fetchReviewerMesaOfficialZipResponse(reviewerSession, laudoId);
}

export async function issueReviewerMesaOfficial(
  reviewerSession: AuthenticatedReviewerRequest,
  input: {
    laudoId: number;
    signatoryId?: number | null;
    expectedCurrentIssueId?: number | null;
    expectedCurrentIssueNumber?: string | null;
  },
) {
  return issueReviewerMesaOfficially(reviewerSession, input);
}

export async function fetchReviewerMesaFrozenOfficialBundle(
  reviewerSession: AuthenticatedReviewerRequest,
  laudoId: number,
) {
  return fetchReviewerMesaFrozenOfficialBundleResponse(reviewerSession, laudoId);
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
    structuredDocument: payload.documento_estruturado
      ? {
          schemaType: payload.documento_estruturado.schema_type,
          familyKey: payload.documento_estruturado.family_key,
          familyLabel: payload.documento_estruturado.family_label,
          summary: payload.documento_estruturado.summary,
          reviewNotes: payload.documento_estruturado.review_notes,
          sections: payload.documento_estruturado.sections.map(mapReviewerMesaStructuredSection),
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
          items: payload.coverage_map.items.map(mapReviewerMesaCoverageItem),
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
          approvedAtLabel: formatDateTime(parseDateOrNull(payload.verificacao_publica.approved_at), "Sem aprovacao"),
        }
      : null,
    officialIssue: payload.emissao_oficial
      ? {
          issueStatus: payload.emissao_oficial.issue_status,
          issueStatusLabel: payload.emissao_oficial.issue_status_label,
          readyForIssue: payload.emissao_oficial.ready_for_issue,
          requiresHumanSignature: payload.emissao_oficial.requires_human_signature,
          compatibleSignatoryCount: payload.emissao_oficial.compatible_signatory_count,
          eligibleSignatoryCount: payload.emissao_oficial.eligible_signatory_count,
          blockerCount: payload.emissao_oficial.blocker_count,
          signatureStatus: payload.emissao_oficial.signature_status ?? null,
          signatureStatusLabel: payload.emissao_oficial.signature_status_label ?? null,
          alreadyIssued: payload.emissao_oficial.already_issued,
          reissueRecommended: payload.emissao_oficial.reissue_recommended,
          issueActionLabel: payload.emissao_oficial.issue_action_label,
          issueActionEnabled: payload.emissao_oficial.issue_action_enabled,
          verificationUrl: payload.emissao_oficial.verification_url,
          signatories: (payload.emissao_oficial.signatories ?? []).map(mapReviewerMesaOfficialSignatory),
          blockers: (payload.emissao_oficial.blockers ?? []).map((item) => ({
            code: item.code,
            title: item.title,
            message: item.message,
            blocking: Boolean(item.blocking),
          })),
          currentIssue: payload.emissao_oficial.current_issue
            ? mapReviewerMesaOfficialCurrentIssue(payload.emissao_oficial.current_issue)
            : null,
        }
      : null,
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

function mapReviewerMesaStructuredSection(
  section: ReviewerMesaPackageSectionPayload,
): ReviewerMesaStructuredSection {
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

function mapReviewerMesaCoverageItem(
  item: ReviewerMesaCoverageItemPayload,
): ReviewerMesaCoverageItem {
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

function mapReviewerMesaOfficialSignatory(item: {
  id: number;
  nome: string;
  funcao: string;
  registro_profissional?: string | null;
  valid_until?: string | null;
  status: string;
  status_label: string;
  ativo: boolean;
  observacoes?: string | null;
}): ReviewerMesaOfficialSignatory {
  const validUntil = parseDateOrNull(item.valid_until);
  return {
    id: item.id,
    name: item.nome,
    role: item.funcao,
    registration: item.registro_profissional ?? null,
    validUntil,
    validUntilLabel: formatDateTime(validUntil, "Sem validade informada"),
    status: item.status,
    statusLabel: item.status_label,
    active: Boolean(item.ativo),
    notes: item.observacoes ?? null,
  };
}

function mapReviewerMesaOfficialCurrentIssue(item: {
  id: number;
  issue_number?: string | null;
  issue_state: string;
  issue_state_label: string;
  issued_at?: string | null;
  package_sha256?: string | null;
  package_storage_ready: boolean;
  signatory_name?: string | null;
  signatory_registration?: string | null;
  primary_pdf_diverged: boolean;
  reissue_of_issue_id?: number | null;
  reissue_of_issue_number?: string | null;
  reissue_reason_codes: string[];
  reissue_reason_summary?: string | null;
}): ReviewerMesaOfficialCurrentIssue {
  const issuedAt = parseDateOrNull(item.issued_at);
  return {
    id: item.id,
    issueNumber: item.issue_number ?? null,
    issueState: item.issue_state,
    issueStateLabel: item.issue_state_label,
    issuedAt,
    issuedAtLabel: formatDateTime(issuedAt, "Sem emissao registrada"),
    packageSha256: item.package_sha256 ?? null,
    packageStorageReady: Boolean(item.package_storage_ready),
    signatoryName: item.signatory_name ?? null,
    signatoryRegistration: item.signatory_registration ?? null,
    primaryPdfDiverged: Boolean(item.primary_pdf_diverged),
    reissueOfIssueId: item.reissue_of_issue_id ?? null,
    reissueOfIssueNumber: item.reissue_of_issue_number ?? null,
    reissueReasonCodes: [...item.reissue_reason_codes],
    reissueReasonSummary: item.reissue_reason_summary ?? null,
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
