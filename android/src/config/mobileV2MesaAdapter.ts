import type {
  MobileAttachment,
  MobileAttachmentPolicy,
  MobileLaudoCard,
  MobileMesaFeedItem,
  MobileMesaFeedResponse,
  MobileMesaMessage,
  MobileMesaMensagensResponse,
  MobileMesaResumo,
  MobileReviewPackage,
} from "../types/mobile";
import type {
  MobileInspectorAttachmentPolicyV2,
  MobileInspectorAttachmentV2,
  MobileInspectorActiveOwnerRoleV2,
  MobileInspectorActorRoleV2,
  MobileInspectorCaseCardV2,
  MobileInspectorCaseLifecycleStatusV2,
  MobileInspectorCaseWorkflowModeV2,
  MobileInspectorCollaborationV2,
  MobileInspectorFeedbackPolicyV2,
  MobileInspectorFeedItemV2,
  MobileInspectorFeedV2,
  MobileInspectorInteractionSummaryV2,
  MobileInspectorLifecycleTransitionV2,
  MobileInspectorPreferredSurfaceV2,
  MobileInspectorReviewPackageV2,
  MobileMesaItemKindV2,
  MobileMesaMessageKindV2,
  MobileMesaPendencyStateV2,
  MobileInspectorReviewSignalsV2,
  MobileInspectorSurfaceActionV2,
  MobileInspectorSyncPolicyV2,
  MobileInspectorThreadMessageV2,
  MobileInspectorThreadSyncV2,
  MobileInspectorThreadV2,
  MobileInspectorTransitionKindV2,
  MobileInspectorVisibilityScopeV2,
} from "../types/mobileV2";

type JsonRecord = Record<string, unknown>;

export class MobileV2ContractError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "MobileV2ContractError";
    this.code = code;
  }
}

function erroContrato(code: string, message: string): MobileV2ContractError {
  return new MobileV2ContractError(code, message);
}

function lerRegistro(value: unknown, label: string): JsonRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw erroContrato("invalid_record", `${label} inválido no contrato V2.`);
  }
  return value as JsonRecord;
}

function lerString(record: JsonRecord, field: string, label: string): string {
  const value = record[field];
  if (typeof value !== "string") {
    throw erroContrato(
      "invalid_string",
      `${label}.${field} precisa ser string.`,
    );
  }
  return value;
}

function lerStringOpcional(
  record: JsonRecord,
  field: string,
  fallback = "",
): string {
  const value = record[field];
  return typeof value === "string" ? value : fallback;
}

function lerBoolean(record: JsonRecord, field: string, label: string): boolean {
  const value = record[field];
  if (typeof value !== "boolean") {
    throw erroContrato(
      "invalid_boolean",
      `${label}.${field} precisa ser boolean.`,
    );
  }
  return value;
}

function lerBooleanOpcional(
  record: JsonRecord,
  field: string,
  fallback = false,
): boolean {
  const value = record[field];
  return typeof value === "boolean" ? value : fallback;
}

function lerNumero(record: JsonRecord, field: string, label: string): number {
  const value = record[field];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw erroContrato(
      "invalid_number",
      `${label}.${field} precisa ser número.`,
    );
  }
  return value;
}

function lerNumeroOuNull(record: JsonRecord, field: string): number | null {
  const value = record[field];
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw erroContrato(
      "invalid_nullable_number",
      `${field} precisa ser número ou null.`,
    );
  }
  return value;
}

function lerStringOuNull(record: JsonRecord, field: string): string | null {
  const value = record[field];
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value !== "string") {
    throw erroContrato(
      "invalid_nullable_string",
      `${field} precisa ser string ou null.`,
    );
  }
  return value;
}

function lerMesaItemKindOpcional(
  record: JsonRecord,
  field: string,
  fallback: MobileMesaItemKindV2,
): MobileMesaItemKindV2 {
  const value = lerStringOpcional(record, field);
  if (value === "message" || value === "whisper" || value === "pendency") {
    return value;
  }
  return fallback;
}

function lerMesaMessageKindOpcional(
  record: JsonRecord,
  field: string,
  fallback: MobileMesaMessageKindV2,
): MobileMesaMessageKindV2 {
  const value = lerStringOpcional(record, field);
  if (
    value === "inspector_message" ||
    value === "inspector_whisper" ||
    value === "mesa_pendency" ||
    value === "ai_message" ||
    value === "system_message"
  ) {
    return value;
  }
  return fallback;
}

function lerMesaPendencyStateOpcional(
  record: JsonRecord,
  field: string,
  fallback: MobileMesaPendencyStateV2,
): MobileMesaPendencyStateV2 {
  const value = lerStringOpcional(record, field);
  if (value === "open" || value === "resolved" || value === "not_applicable") {
    return value;
  }
  return fallback;
}

function lerCaseLifecycleStatusOpcional(
  record: JsonRecord,
  field: string,
  fallback: MobileInspectorCaseLifecycleStatusV2,
): MobileInspectorCaseLifecycleStatusV2 {
  const value = lerStringOpcional(record, field);
  if (
    value === "analise_livre" ||
    value === "pre_laudo" ||
    value === "laudo_em_coleta" ||
    value === "aguardando_mesa" ||
    value === "em_revisao_mesa" ||
    value === "devolvido_para_correcao" ||
    value === "aprovado" ||
    value === "emitido"
  ) {
    return value;
  }
  return fallback;
}

function lerCaseWorkflowModeOpcional(
  record: JsonRecord,
  field: string,
  fallback: MobileInspectorCaseWorkflowModeV2,
): MobileInspectorCaseWorkflowModeV2 {
  const value = lerStringOpcional(record, field);
  if (
    value === "analise_livre" ||
    value === "laudo_guiado" ||
    value === "laudo_com_mesa"
  ) {
    return value;
  }
  return fallback;
}

function lerActiveOwnerRoleOpcional(
  record: JsonRecord,
  field: string,
  fallback: MobileInspectorActiveOwnerRoleV2,
): MobileInspectorActiveOwnerRoleV2 {
  const value = lerStringOpcional(record, field);
  if (value === "inspetor" || value === "mesa" || value === "none") {
    return value;
  }
  return fallback;
}

function lerTransitionKindOpcional(
  record: JsonRecord,
  field: string,
  fallback: MobileInspectorTransitionKindV2,
): MobileInspectorTransitionKindV2 {
  const value = lerStringOpcional(record, field);
  if (
    value === "analysis" ||
    value === "advance" ||
    value === "review" ||
    value === "approval" ||
    value === "correction" ||
    value === "reopen" ||
    value === "issue"
  ) {
    return value;
  }
  return fallback;
}

function lerPreferredSurfaceOpcional(
  record: JsonRecord,
  field: string,
  fallback: MobileInspectorPreferredSurfaceV2,
): MobileInspectorPreferredSurfaceV2 {
  const value = lerStringOpcional(record, field);
  if (
    value === "chat" ||
    value === "mesa" ||
    value === "mobile" ||
    value === "system"
  ) {
    return value;
  }
  return fallback;
}

function isOpenPendencyState(
  state: MobileMesaPendencyStateV2 | string | null | undefined,
): boolean {
  return (
    String(state || "")
      .trim()
      .toLowerCase() === "open"
  );
}

function isResolvedPendencyState(
  state: MobileMesaPendencyStateV2 | string | null | undefined,
): boolean {
  return (
    String(state || "")
      .trim()
      .toLowerCase() === "resolved"
  );
}

function lerArray(record: JsonRecord, field: string, label: string): unknown[] {
  const value = record[field];
  if (!Array.isArray(value)) {
    throw erroContrato("invalid_array", `${label}.${field} precisa ser array.`);
  }
  return value;
}

function lerArrayRegistros(
  record: JsonRecord,
  field: string,
  label: string,
): JsonRecord[] {
  return lerArray(record, field, label).map((item, index) =>
    lerRegistro(item, `${label}.${field}[${index}]`),
  );
}

function lerRecordOuNull(record: JsonRecord, field: string): JsonRecord | null {
  const value = record[field];
  if (value === null || value === undefined) {
    return null;
  }
  return lerRegistro(value, field);
}

function lerArrayStringsOpcional(record: JsonRecord, field: string): string[] {
  const value = record[field];
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(
    (item): item is string =>
      typeof item === "string" && item.trim().length > 0,
  );
}

function lerSurfaceActionsOpcional(
  record: JsonRecord,
  field: string,
): MobileInspectorSurfaceActionV2[] {
  return lerArrayStringsOpcional(record, field).filter(
    (item): item is MobileInspectorSurfaceActionV2 =>
      item === "chat_finalize" ||
      item === "chat_reopen" ||
      item === "mesa_approve" ||
      item === "mesa_return" ||
      item === "system_issue",
  );
}

function parseLifecycleTransitions(
  record: JsonRecord,
  field: string,
  label: string,
): MobileInspectorLifecycleTransitionV2[] {
  if (!Array.isArray(record[field])) {
    return [];
  }
  return lerArrayRegistros(record, field, label).map((item) => ({
    target_status: lerCaseLifecycleStatusOpcional(
      item,
      "target_status",
      "analise_livre",
    ),
    transition_kind: lerTransitionKindOpcional(
      item,
      "transition_kind",
      "advance",
    ),
    label: lerStringOpcional(item, "label"),
    owner_role: lerActiveOwnerRoleOpcional(item, "owner_role", "inspetor"),
    preferred_surface: lerPreferredSurfaceOpcional(
      item,
      "preferred_surface",
      "chat",
    ),
  }));
}

function lerVisibilidade(
  record: JsonRecord,
  label: string,
): MobileInspectorVisibilityScopeV2 {
  const value = lerString(record, "visibility_scope", label);
  if (value !== "inspetor_mobile") {
    throw erroContrato(
      "visibility_scope_violation",
      `${label}.visibility_scope fora do escopo do Inspetor.`,
    );
  }
  return value;
}

function lerActorRole(
  record: JsonRecord,
  label: string,
): MobileInspectorActorRoleV2 {
  const value = lerString(record, "actor_role", label);
  if (value !== "inspetor" && value !== "mesa") {
    throw erroContrato(
      "actor_role_violation",
      `${label}.actor_role fora do recorte móvel do Inspetor.`,
    );
  }
  return value;
}

function validarContrato(
  record: JsonRecord,
  label: string,
  contractName: string,
) {
  const actualName = lerString(record, "contract_name", label);
  const actualVersion = lerString(record, "contract_version", label);
  if (actualName !== contractName || actualVersion !== "v2") {
    throw erroContrato(
      "invalid_contract",
      `${label} não corresponde ao contrato público V2 esperado.`,
    );
  }
}

function parseCaseCard(
  value: unknown,
  label: string,
): MobileInspectorCaseCardV2 | null {
  if (value === null || value === undefined) {
    return null;
  }
  const record = lerRegistro(value, label);
  validarContrato(record, label, "MobileInspectorCaseCardV2");
  return {
    contract_name: "MobileInspectorCaseCardV2",
    contract_version: "v2",
    legacy_laudo_id: lerNumeroOuNull(record, "legacy_laudo_id"),
    title: lerStringOpcional(record, "title"),
    preview: lerStringOpcional(record, "preview"),
    template_key: lerStringOpcional(record, "template_key"),
    review_status: lerStringOpcional(record, "review_status"),
    card_status: lerStringOpcional(record, "card_status"),
    card_status_label: lerStringOpcional(record, "card_status_label"),
    date_iso: lerStringOpcional(record, "date_iso"),
    date_display: lerStringOpcional(record, "date_display"),
    time_display: lerStringOpcional(record, "time_display"),
    is_pinned: lerBooleanOpcional(record, "is_pinned"),
    allows_edit: lerBooleanOpcional(record, "allows_edit"),
    allows_reopen: lerBooleanOpcional(record, "allows_reopen"),
    has_history: lerBooleanOpcional(record, "has_history"),
    visibility_scope: lerVisibilidade(record, label),
  };
}

function parseReviewSignals(
  value: unknown,
  label: string,
): MobileInspectorReviewSignalsV2 {
  const record = lerRegistro(value, label);
  validarContrato(record, label, "MobileInspectorReviewSignalsV2");
  return {
    contract_name: "MobileInspectorReviewSignalsV2",
    contract_version: "v2",
    review_visible_to_inspector: lerBoolean(
      record,
      "review_visible_to_inspector",
      label,
    ),
    total_visible_interactions: lerNumero(
      record,
      "total_visible_interactions",
      label,
    ),
    visible_feedback_count: lerNumero(record, "visible_feedback_count", label),
    open_feedback_count: lerNumero(record, "open_feedback_count", label),
    resolved_feedback_count: lerNumero(
      record,
      "resolved_feedback_count",
      label,
    ),
    latest_feedback_message_id: lerNumeroOuNull(
      record,
      "latest_feedback_message_id",
    ),
    latest_feedback_at: lerStringOuNull(record, "latest_feedback_at"),
    visibility_scope: lerVisibilidade(record, label),
  };
}

function parseFeedbackPolicy(
  value: unknown,
  label: string,
): MobileInspectorFeedbackPolicyV2 {
  const record = lerRegistro(value, label);
  validarContrato(record, label, "MobileInspectorFeedbackPolicyV2");
  const policy_name = lerString(record, "policy_name", label);
  if (policy_name !== "android_feedback_sync_policy") {
    throw erroContrato(
      "invalid_feedback_policy_name",
      `${label}.policy_name inválido para o contrato móvel do Inspetor.`,
    );
  }
  const feedback_mode = lerString(record, "feedback_mode", label);
  if (feedback_mode !== "hidden" && feedback_mode !== "visible_feedback_only") {
    throw erroContrato(
      "invalid_feedback_mode",
      `${label}.feedback_mode inválido.`,
    );
  }
  const mesa_internal_details_visible = lerBoolean(
    record,
    "mesa_internal_details_visible",
    label,
  );
  if (mesa_internal_details_visible) {
    throw erroContrato(
      "mesa_internal_details_violation",
      `${label}.mesa_internal_details_visible não pode ser true no canal móvel do Inspetor.`,
    );
  }
  return {
    contract_name: "MobileInspectorFeedbackPolicyV2",
    contract_version: "v2",
    policy_name: "android_feedback_sync_policy",
    feedback_mode,
    feedback_counters_visible: lerBoolean(
      record,
      "feedback_counters_visible",
      label,
    ),
    feedback_message_bodies_visible: lerBoolean(
      record,
      "feedback_message_bodies_visible",
      label,
    ),
    latest_feedback_pointer_visible: lerBoolean(
      record,
      "latest_feedback_pointer_visible",
      label,
    ),
    mesa_internal_details_visible: false,
    visibility_scope: lerVisibilidade(record, label),
  };
}

function validarConsistenciaFeedbackPolicy(params: {
  label: string;
  reviewSignals: MobileInspectorReviewSignalsV2;
  feedbackPolicy: MobileInspectorFeedbackPolicyV2;
  latestInteraction: MobileInspectorInteractionSummaryV2 | null;
  unreadCount: number;
  openCount: number;
  resolvedCount: number;
  threadItems?: MobileInspectorThreadMessageV2[];
}) {
  const {
    label,
    reviewSignals,
    feedbackPolicy,
    latestInteraction,
    unreadCount,
    openCount,
    resolvedCount,
    threadItems,
  } = params;
  const shouldExposeFeedback =
    feedbackPolicy.feedback_mode === "visible_feedback_only";
  const hasVisibleFeedbackCount = reviewSignals.visible_feedback_count > 0;

  if (reviewSignals.review_visible_to_inspector !== shouldExposeFeedback) {
    throw erroContrato(
      "feedback_policy_mismatch",
      `${label} tem review_signals incompatível com feedback_policy.`,
    );
  }

  if (!shouldExposeFeedback && hasVisibleFeedbackCount) {
    throw erroContrato(
      "feedback_visibility_mismatch",
      `${label} expõe contagem de feedback incompatível com feedback_policy.`,
    );
  }

  if (!feedbackPolicy.feedback_counters_visible) {
    if (unreadCount !== 0 || openCount !== 0 || resolvedCount !== 0) {
      throw erroContrato(
        "feedback_counter_leak",
        `${label} não pode expor contadores de feedback quando a política é oculta.`,
      );
    }
    if (
      reviewSignals.open_feedback_count !== 0 ||
      reviewSignals.resolved_feedback_count !== 0
    ) {
      throw erroContrato(
        "feedback_signal_counter_leak",
        `${label}.review_signals não pode expor contadores quando a política é oculta.`,
      );
    }
  }

  if (!feedbackPolicy.latest_feedback_pointer_visible) {
    if (latestInteraction?.actor_role === "mesa") {
      throw erroContrato(
        "feedback_pointer_leak",
        `${label} não pode apontar para interação da mesa quando a política é oculta.`,
      );
    }
    if (
      reviewSignals.latest_feedback_message_id !== null ||
      reviewSignals.latest_feedback_at !== null
    ) {
      throw erroContrato(
        "feedback_signal_pointer_leak",
        `${label}.review_signals não pode apontar para feedback oculto da mesa.`,
      );
    }
  }

  if (!feedbackPolicy.feedback_message_bodies_visible) {
    if (threadItems?.some((item) => item.actor_role === "mesa")) {
      throw erroContrato(
        "feedback_message_leak",
        `${label} não pode expor mensagens da mesa quando a política é oculta.`,
      );
    }
  }
}

function parseInteractionSummary(
  value: unknown,
  label: string,
): MobileInspectorInteractionSummaryV2 | null {
  if (value === null || value === undefined) {
    return null;
  }
  const record = lerRegistro(value, label);
  validarContrato(record, label, "MobileInspectorInteractionSummaryV2");
  const pendencyState = lerMesaPendencyStateOpcional(
    record,
    "pendency_state",
    "not_applicable",
  );
  return {
    contract_name: "MobileInspectorInteractionSummaryV2",
    contract_version: "v2",
    interaction_id: lerString(record, "interaction_id", label),
    message_id: lerNumeroOuNull(record, "message_id"),
    actor_role: lerActorRole(record, label),
    actor_kind: lerStringOpcional(record, "actor_kind"),
    origin_kind: lerStringOpcional(record, "origin_kind", "system"),
    content_kind: lerStringOpcional(record, "content_kind"),
    legacy_message_type: lerStringOpcional(record, "legacy_message_type"),
    item_kind: lerMesaItemKindOpcional(record, "item_kind", "message"),
    message_kind: lerMesaMessageKindOpcional(
      record,
      "message_kind",
      "system_message",
    ),
    pendency_state: pendencyState,
    text_preview: lerStringOpcional(record, "text_preview"),
    timestamp: lerString(record, "timestamp", label),
    sender_id: lerNumeroOuNull(record, "sender_id"),
    client_message_id: lerStringOuNull(record, "client_message_id"),
    reference_message_id: lerNumeroOuNull(record, "reference_message_id"),
    operational_context: lerRecordOuNull(record, "operational_context"),
    is_read: lerBooleanOpcional(record, "is_read"),
    has_attachments: lerBooleanOpcional(record, "has_attachments"),
    review_feedback_visible: lerBooleanOpcional(
      record,
      "review_feedback_visible",
    ),
    review_marker_visible: lerBooleanOpcional(record, "review_marker_visible"),
    highlight_marker: lerBooleanOpcional(record, "highlight_marker"),
    pending_open: isOpenPendencyState(pendencyState),
    pending_resolved: isResolvedPendencyState(pendencyState),
    visibility_scope: lerVisibilidade(record, label),
  };
}

function buildDerivedCollaboration(params: {
  reviewSignals: MobileInspectorReviewSignalsV2;
  feedbackPolicy: MobileInspectorFeedbackPolicyV2;
  latestFeedback: MobileInspectorInteractionSummaryV2 | null;
  unreadCount: number;
  openCount: number;
  resolvedCount: number;
}): MobileInspectorCollaborationV2 {
  const latestFeedback = params.feedbackPolicy.latest_feedback_pointer_visible
    ? params.latestFeedback
    : null;
  const unreadCount = params.feedbackPolicy.feedback_counters_visible
    ? params.unreadCount
    : 0;
  const openCount = params.feedbackPolicy.feedback_counters_visible
    ? params.openCount
    : 0;
  const resolvedCount = params.feedbackPolicy.feedback_counters_visible
    ? params.resolvedCount
    : 0;
  return {
    contract_name: "MobileInspectorCollaborationV2",
    contract_version: "v2",
    summary: {
      contract_name: "MobileInspectorCollaborationSummaryV2",
      contract_version: "v2",
      feedback_visible_to_inspector:
        params.reviewSignals.review_visible_to_inspector,
      visible_feedback_count: params.reviewSignals.visible_feedback_count,
      unread_feedback_count: unreadCount,
      open_feedback_count: openCount,
      resolved_feedback_count: resolvedCount,
      latest_feedback_message_id:
        latestFeedback?.message_id ??
        params.reviewSignals.latest_feedback_message_id,
      latest_feedback_at:
        latestFeedback?.timestamp ?? params.reviewSignals.latest_feedback_at,
      latest_feedback_preview: latestFeedback?.text_preview ?? "",
      visibility_scope: "inspetor_mobile",
    },
    latest_feedback: latestFeedback,
    visibility_scope: "inspetor_mobile",
  };
}

function parseCollaboration(
  value: unknown,
  label: string,
  params: {
    reviewSignals: MobileInspectorReviewSignalsV2;
    feedbackPolicy: MobileInspectorFeedbackPolicyV2;
    latestFeedback: MobileInspectorInteractionSummaryV2 | null;
    unreadCount: number;
    openCount: number;
    resolvedCount: number;
  },
): MobileInspectorCollaborationV2 {
  const derived = buildDerivedCollaboration(params);
  if (value === null || value === undefined) {
    return derived;
  }

  const record = lerRegistro(value, label);
  validarContrato(record, label, "MobileInspectorCollaborationV2");
  const summaryRecord = lerRegistro(record.summary, `${label}.summary`);
  validarContrato(
    summaryRecord,
    `${label}.summary`,
    "MobileInspectorCollaborationSummaryV2",
  );
  const latestFeedback = parseInteractionSummary(
    record.latest_feedback,
    `${label}.latest_feedback`,
  );
  const parsed: MobileInspectorCollaborationV2 = {
    contract_name: "MobileInspectorCollaborationV2",
    contract_version: "v2",
    summary: {
      contract_name: "MobileInspectorCollaborationSummaryV2",
      contract_version: "v2",
      feedback_visible_to_inspector: lerBoolean(
        summaryRecord,
        "feedback_visible_to_inspector",
        `${label}.summary`,
      ),
      visible_feedback_count: lerNumero(
        summaryRecord,
        "visible_feedback_count",
        `${label}.summary`,
      ),
      unread_feedback_count: lerNumero(
        summaryRecord,
        "unread_feedback_count",
        `${label}.summary`,
      ),
      open_feedback_count: lerNumero(
        summaryRecord,
        "open_feedback_count",
        `${label}.summary`,
      ),
      resolved_feedback_count: lerNumero(
        summaryRecord,
        "resolved_feedback_count",
        `${label}.summary`,
      ),
      latest_feedback_message_id: lerNumeroOuNull(
        summaryRecord,
        "latest_feedback_message_id",
      ),
      latest_feedback_at: lerStringOuNull(summaryRecord, "latest_feedback_at"),
      latest_feedback_preview: lerStringOpcional(
        summaryRecord,
        "latest_feedback_preview",
      ),
      visibility_scope: lerVisibilidade(summaryRecord, `${label}.summary`),
    },
    latest_feedback: latestFeedback,
    visibility_scope: lerVisibilidade(record, label),
  };

  if (
    parsed.summary.feedback_visible_to_inspector !==
    derived.summary.feedback_visible_to_inspector
  ) {
    throw erroContrato(
      "collaboration_visibility_mismatch",
      `${label}.summary.feedback_visible_to_inspector incompatível com review_signals.`,
    );
  }
  if (
    parsed.summary.visible_feedback_count !==
    derived.summary.visible_feedback_count
  ) {
    throw erroContrato(
      "collaboration_visible_count_mismatch",
      `${label}.summary.visible_feedback_count incompatível com review_signals.`,
    );
  }
  if (
    parsed.summary.unread_feedback_count !==
    derived.summary.unread_feedback_count
  ) {
    throw erroContrato(
      "collaboration_unread_count_mismatch",
      `${label}.summary.unread_feedback_count incompatível com o payload visível.`,
    );
  }
  if (
    parsed.summary.open_feedback_count !== derived.summary.open_feedback_count
  ) {
    throw erroContrato(
      "collaboration_open_count_mismatch",
      `${label}.summary.open_feedback_count incompatível com o payload visível.`,
    );
  }
  if (
    parsed.summary.resolved_feedback_count !==
    derived.summary.resolved_feedback_count
  ) {
    throw erroContrato(
      "collaboration_resolved_count_mismatch",
      `${label}.summary.resolved_feedback_count incompatível com o payload visível.`,
    );
  }
  if (parsed.latest_feedback?.actor_role === "inspetor") {
    throw erroContrato(
      "collaboration_feedback_role_violation",
      `${label}.latest_feedback precisa apontar apenas para feedback visível da mesa.`,
    );
  }
  if (
    parsed.summary.latest_feedback_message_id !==
    (parsed.latest_feedback?.message_id ??
      derived.summary.latest_feedback_message_id)
  ) {
    throw erroContrato(
      "collaboration_feedback_pointer_mismatch",
      `${label}.summary.latest_feedback_message_id incompatível com latest_feedback.`,
    );
  }
  if (
    parsed.summary.latest_feedback_at !==
    (parsed.latest_feedback?.timestamp ?? derived.summary.latest_feedback_at)
  ) {
    throw erroContrato(
      "collaboration_feedback_timestamp_mismatch",
      `${label}.summary.latest_feedback_at incompatível com latest_feedback.`,
    );
  }
  if (
    parsed.summary.latest_feedback_preview !==
    (parsed.latest_feedback?.text_preview ??
      derived.summary.latest_feedback_preview)
  ) {
    throw erroContrato(
      "collaboration_feedback_preview_mismatch",
      `${label}.summary.latest_feedback_preview incompatível com latest_feedback.`,
    );
  }
  return parsed;
}

function parseThreadMessage(
  value: unknown,
  label: string,
): MobileInspectorThreadMessageV2 {
  const record = lerRegistro(value, label);
  validarContrato(record, label, "MobileInspectorThreadMessageV2");
  const pendencyState = lerMesaPendencyStateOpcional(
    record,
    "pendency_state",
    "not_applicable",
  );
  return {
    contract_name: "MobileInspectorThreadMessageV2",
    contract_version: "v2",
    interaction_id: lerString(record, "interaction_id", label),
    message_id: lerNumeroOuNull(record, "message_id"),
    actor_role: lerActorRole(record, label),
    actor_kind: lerStringOpcional(record, "actor_kind"),
    origin_kind: lerStringOpcional(record, "origin_kind", "system"),
    content_kind: lerStringOpcional(record, "content_kind"),
    legacy_message_type: lerStringOpcional(record, "legacy_message_type"),
    item_kind: lerMesaItemKindOpcional(record, "item_kind", "message"),
    message_kind: lerMesaMessageKindOpcional(
      record,
      "message_kind",
      "system_message",
    ),
    pendency_state: pendencyState,
    text_preview: lerStringOpcional(record, "text_preview"),
    timestamp: lerString(record, "timestamp", label),
    sender_id: lerNumeroOuNull(record, "sender_id"),
    client_message_id: lerStringOuNull(record, "client_message_id"),
    reference_message_id: lerNumeroOuNull(record, "reference_message_id"),
    operational_context: lerRecordOuNull(record, "operational_context"),
    is_read: lerBooleanOpcional(record, "is_read"),
    has_attachments: lerBooleanOpcional(record, "has_attachments"),
    review_feedback_visible: lerBooleanOpcional(
      record,
      "review_feedback_visible",
    ),
    review_marker_visible: lerBooleanOpcional(record, "review_marker_visible"),
    highlight_marker: lerBooleanOpcional(record, "highlight_marker"),
    pending_open: isOpenPendencyState(pendencyState),
    pending_resolved: isResolvedPendencyState(pendencyState),
    visibility_scope: lerVisibilidade(record, label),
    content_text: lerStringOpcional(record, "content_text"),
    display_date: lerStringOpcional(record, "display_date"),
    resolved_at: lerStringOuNull(record, "resolved_at"),
    resolved_at_label: lerStringOpcional(record, "resolved_at_label"),
    resolved_by_name: lerStringOpcional(record, "resolved_by_name"),
    attachments: lerArray(record, "attachments", label).map((item, index) =>
      parseAttachment(item, `${label}.attachments[${index}]`),
    ),
    delivery_status: lerStringOpcional(record, "delivery_status", "persisted"),
    order_index: lerNumero(record, "order_index", label),
    cursor_id: lerNumeroOuNull(record, "cursor_id"),
    is_delta_item: lerBooleanOpcional(record, "is_delta_item"),
  };
}

function parseAttachment(
  value: unknown,
  label: string,
): MobileInspectorAttachmentV2 {
  const record = lerRegistro(value, label);
  validarContrato(record, label, "MobileInspectorAttachmentV2");
  return {
    contract_name: "MobileInspectorAttachmentV2",
    contract_version: "v2",
    attachment_id: lerNumeroOuNull(record, "attachment_id"),
    name: lerStringOpcional(record, "name"),
    mime_type: lerStringOpcional(record, "mime_type"),
    category: lerStringOpcional(record, "category"),
    size_bytes: lerNumero(record, "size_bytes", label),
    download_url: lerStringOuNull(record, "download_url"),
    is_image: lerBooleanOpcional(record, "is_image"),
    visibility_scope: lerVisibilidade(record, label),
  };
}

function parseThreadSync(
  value: unknown,
  label: string,
): MobileInspectorThreadSyncV2 {
  const record = lerRegistro(value, label);
  validarContrato(record, label, "MobileInspectorThreadSyncV2");
  const mode = lerString(record, "mode", label);
  if (mode !== "full" && mode !== "delta") {
    throw erroContrato("invalid_sync_mode", `${label}.mode inválido.`);
  }
  return {
    contract_name: "MobileInspectorThreadSyncV2",
    contract_version: "v2",
    mode,
    cursor_after_id: lerNumeroOuNull(record, "cursor_after_id"),
    next_cursor_id: lerNumeroOuNull(record, "next_cursor_id"),
    cursor_last_message_id: lerNumeroOuNull(record, "cursor_last_message_id"),
    has_more: lerBooleanOpcional(record, "has_more"),
  };
}

function parseAttachmentPolicy(
  value: unknown,
  label: string,
): MobileInspectorAttachmentPolicyV2 {
  const record = lerRegistro(value, label);
  validarContrato(record, label, "MobileInspectorAttachmentPolicyV2");
  const policyName = lerString(record, "policy_name", label);
  if (policyName !== "android_attachment_sync_policy") {
    throw erroContrato(
      "invalid_attachment_policy_name",
      `${label}.policy_name inválido.`,
    );
  }
  return {
    contract_name: "MobileInspectorAttachmentPolicyV2",
    contract_version: "v2",
    policy_name: policyName,
    upload_allowed: lerBoolean(record, "upload_allowed", label),
    download_allowed: lerBoolean(record, "download_allowed", label),
    inline_preview_allowed: lerBoolean(record, "inline_preview_allowed", label),
    supported_categories: lerArray(record, "supported_categories", label).map(
      (item, index) => {
        if (typeof item !== "string") {
          throw erroContrato(
            "invalid_attachment_category",
            `${label}.supported_categories[${index}] precisa ser string.`,
          );
        }
        return item;
      },
    ),
    supported_mime_types: lerArray(record, "supported_mime_types", label).map(
      (item, index) => {
        if (typeof item !== "string") {
          throw erroContrato(
            "invalid_attachment_mime",
            `${label}.supported_mime_types[${index}] precisa ser string.`,
          );
        }
        return item;
      },
    ),
    visibility_scope: lerVisibilidade(record, label),
  };
}

function parseSyncPolicy(
  value: unknown,
  label: string,
  sync: MobileInspectorThreadSyncV2,
): MobileInspectorSyncPolicyV2 {
  const record = lerRegistro(value, label);
  validarContrato(record, label, "MobileInspectorSyncPolicyV2");
  const mode = lerString(record, "mode", label);
  if (mode !== "full" && mode !== "delta") {
    throw erroContrato("invalid_sync_policy_mode", `${label}.mode inválido.`);
  }
  const policyName = lerString(record, "policy_name", label);
  if (policyName !== "android_thread_sync_policy") {
    throw erroContrato(
      "invalid_sync_policy_name",
      `${label}.policy_name inválido.`,
    );
  }
  if (mode !== sync.mode) {
    throw erroContrato(
      "sync_policy_mode_mismatch",
      `${label}.mode precisa refletir o contrato thread.sync.`,
    );
  }
  return {
    contract_name: "MobileInspectorSyncPolicyV2",
    contract_version: "v2",
    policy_name: policyName,
    mode,
    offline_queue_supported: lerBoolean(
      record,
      "offline_queue_supported",
      label,
    ),
    incremental_sync_supported: lerBoolean(
      record,
      "incremental_sync_supported",
      label,
    ),
    attachment_sync_supported: lerBoolean(
      record,
      "attachment_sync_supported",
      label,
    ),
    visibility_scope: lerVisibilidade(record, label),
  };
}

function parseReviewPackage(
  value: unknown,
  label: string,
): MobileInspectorReviewPackageV2 | null {
  if (value === null || value === undefined) {
    return null;
  }
  const record = lerRegistro(value, label);
  validarContrato(record, label, "MobileInspectorReviewPackageV2");
  return {
    contract_name: "MobileInspectorReviewPackageV2",
    contract_version: "v2",
    review_mode: lerStringOuNull(record, "review_mode"),
    review_required:
      typeof record.review_required === "boolean"
        ? record.review_required
        : null,
    policy_summary: lerRecordOuNull(record, "policy_summary"),
    document_readiness: lerRecordOuNull(record, "document_readiness"),
    document_blockers: lerArrayRegistros(
      record,
      "document_blockers",
      label,
    ).map((item) => ({ ...item })),
    revisao_por_bloco: lerRecordOuNull(record, "revisao_por_bloco"),
    coverage_map: lerRecordOuNull(record, "coverage_map"),
    inspection_history: lerRecordOuNull(record, "inspection_history"),
    human_override_summary: lerRecordOuNull(record, "human_override_summary"),
    public_verification: lerRecordOuNull(record, "public_verification"),
    anexo_pack: lerRecordOuNull(record, "anexo_pack"),
    emissao_oficial: lerRecordOuNull(record, "emissao_oficial"),
    historico_refazer_inspetor: lerArrayRegistros(
      record,
      "historico_refazer_inspetor",
      label,
    ).map((item) => ({ ...item })),
    memoria_operacional_familia: lerRecordOuNull(
      record,
      "memoria_operacional_familia",
    ),
    red_flags: lerArrayRegistros(record, "red_flags", label).map((item) => ({
      ...item,
    })),
    tenant_entitlements: lerRecordOuNull(record, "tenant_entitlements"),
    allowed_decisions: lerArray(record, "allowed_decisions", label).map(
      (item, index) => {
        if (typeof item !== "string") {
          throw erroContrato(
            "invalid_review_allowed_decision",
            `${label}.allowed_decisions[${index}] precisa ser string.`,
          );
        }
        return item;
      },
    ),
    supports_block_reopen: lerBoolean(record, "supports_block_reopen", label),
    visibility_scope: lerVisibilidade(record, label),
  };
}

export function parseMobileInspectorFeedV2(
  payload: unknown,
): MobileInspectorFeedV2 {
  const record = lerRegistro(payload, "feed");
  validarContrato(record, "feed", "MobileInspectorFeedV2");
  const items = lerArray(record, "items", "feed").map((item, index) => {
    const itemRecord = lerRegistro(item, `feed.items[${index}]`);
    validarContrato(
      itemRecord,
      `feed.items[${index}]`,
      "MobileInspectorFeedItemV2",
    );
    const visibility_scope = lerVisibilidade(
      itemRecord,
      `feed.items[${index}]`,
    );
    const latest_interaction = parseInteractionSummary(
      itemRecord.latest_interaction,
      `feed.items[${index}].latest_interaction`,
    );
    const review_signals = parseReviewSignals(
      itemRecord.review_signals,
      `feed.items[${index}].review_signals`,
    );
    const feedback_policy = parseFeedbackPolicy(
      itemRecord.feedback_policy,
      `feed.items[${index}].feedback_policy`,
    );
    const unread_visible_interactions = lerNumero(
      itemRecord,
      "unread_visible_interactions",
      `feed.items[${index}]`,
    );
    const open_feedback_count = lerNumero(
      itemRecord,
      "open_feedback_count",
      `feed.items[${index}]`,
    );
    const resolved_feedback_count = lerNumero(
      itemRecord,
      "resolved_feedback_count",
      `feed.items[${index}]`,
    );
    validarConsistenciaFeedbackPolicy({
      label: `feed.items[${index}]`,
      reviewSignals: review_signals,
      feedbackPolicy: feedback_policy,
      latestInteraction: latest_interaction,
      unreadCount: unread_visible_interactions,
      openCount: open_feedback_count,
      resolvedCount: resolved_feedback_count,
    });
    const collaboration = parseCollaboration(
      itemRecord.collaboration,
      `feed.items[${index}].collaboration`,
      {
        reviewSignals: review_signals,
        feedbackPolicy: feedback_policy,
        latestFeedback:
          latest_interaction?.actor_role === "mesa" ? latest_interaction : null,
        unreadCount: unread_visible_interactions,
        openCount: open_feedback_count,
        resolvedCount: resolved_feedback_count,
      },
    );
    return {
      contract_name: "MobileInspectorFeedItemV2",
      contract_version: "v2",
      tenant_id: lerString(itemRecord, "tenant_id", `feed.items[${index}]`),
      source_channel: lerStringOpcional(itemRecord, "source_channel"),
      case_id: lerStringOuNull(itemRecord, "case_id"),
      legacy_laudo_id: lerNumeroOuNull(itemRecord, "legacy_laudo_id"),
      thread_id: lerStringOuNull(itemRecord, "thread_id"),
      visibility_scope,
      case_status: lerStringOpcional(itemRecord, "case_status"),
      case_lifecycle_status: lerCaseLifecycleStatusOpcional(
        itemRecord,
        "case_lifecycle_status",
        "analise_livre",
      ),
      case_workflow_mode: lerCaseWorkflowModeOpcional(
        itemRecord,
        "case_workflow_mode",
        "analise_livre",
      ),
      active_owner_role: lerActiveOwnerRoleOpcional(
        itemRecord,
        "active_owner_role",
        "inspetor",
      ),
      allowed_next_lifecycle_statuses: lerArrayStringsOpcional(
        itemRecord,
        "allowed_next_lifecycle_statuses",
      ),
      allowed_lifecycle_transitions: parseLifecycleTransitions(
        itemRecord,
        "allowed_lifecycle_transitions",
        `feed.items[${index}]`,
      ),
      allowed_surface_actions: lerSurfaceActionsOpcional(
        itemRecord,
        "allowed_surface_actions",
      ),
      human_validation_required: lerBooleanOpcional(
        itemRecord,
        "human_validation_required",
      ),
      legacy_public_state: lerStringOpcional(itemRecord, "legacy_public_state"),
      allows_edit: lerBooleanOpcional(itemRecord, "allows_edit"),
      allows_reopen: lerBooleanOpcional(itemRecord, "allows_reopen"),
      has_interaction: lerBooleanOpcional(itemRecord, "has_interaction"),
      case_card: parseCaseCard(
        itemRecord.case_card,
        `feed.items[${index}].case_card`,
      ),
      updated_at: lerStringOuNull(itemRecord, "updated_at"),
      total_visible_interactions: lerNumero(
        itemRecord,
        "total_visible_interactions",
        `feed.items[${index}]`,
      ),
      unread_visible_interactions,
      open_feedback_count,
      resolved_feedback_count,
      latest_interaction,
      review_signals,
      feedback_policy,
      collaboration,
      provenance_summary: lerRecordOuNull(itemRecord, "provenance_summary"),
      policy_summary: lerRecordOuNull(itemRecord, "policy_summary"),
      document_readiness: lerRecordOuNull(itemRecord, "document_readiness"),
      document_blockers: lerArrayRegistros(
        itemRecord,
        "document_blockers",
        `feed.items[${index}]`,
      ).map((blocker) => ({ ...blocker })),
    } satisfies MobileInspectorFeedItemV2;
  });

  return {
    contract_name: "MobileInspectorFeedV2",
    contract_version: "v2",
    tenant_id: lerString(record, "tenant_id", "feed"),
    source_channel: lerStringOpcional(record, "source_channel"),
    visibility_scope: lerVisibilidade(record, "feed"),
    requested_laudo_ids: lerArray(record, "requested_laudo_ids", "feed").map(
      (value, index) => {
        if (typeof value !== "number" || !Number.isFinite(value)) {
          throw erroContrato(
            "invalid_requested_laudo_ids",
            `feed.requested_laudo_ids[${index}] precisa ser número.`,
          );
        }
        return value;
      },
    ),
    cursor_current: lerStringOpcional(record, "cursor_current"),
    total_requested_cases: lerNumero(record, "total_requested_cases", "feed"),
    returned_item_count: lerNumero(record, "returned_item_count", "feed"),
    items,
    timestamp: lerString(record, "timestamp", "feed"),
  };
}

export function parseMobileInspectorThreadV2(
  payload: unknown,
): MobileInspectorThreadV2 {
  const record = lerRegistro(payload, "thread");
  validarContrato(record, "thread", "MobileInspectorThreadV2");
  const items = lerArray(record, "items", "thread")
    .map((item, index) => parseThreadMessage(item, `thread.items[${index}]`))
    .sort(
      (a, b) =>
        a.order_index - b.order_index ||
        a.timestamp.localeCompare(b.timestamp) ||
        (a.message_id || 0) - (b.message_id || 0),
    );
  const latest_interaction = parseInteractionSummary(
    record.latest_interaction,
    "thread.latest_interaction",
  );
  const review_signals = parseReviewSignals(
    record.review_signals,
    "thread.review_signals",
  );
  const feedback_policy = parseFeedbackPolicy(
    record.feedback_policy,
    "thread.feedback_policy",
  );
  const unread_visible_messages = lerNumero(
    record,
    "unread_visible_messages",
    "thread",
  );
  const open_feedback_count = lerNumero(
    record,
    "open_feedback_count",
    "thread",
  );
  const resolved_feedback_count = lerNumero(
    record,
    "resolved_feedback_count",
    "thread",
  );
  validarConsistenciaFeedbackPolicy({
    label: "thread",
    reviewSignals: review_signals,
    feedbackPolicy: feedback_policy,
    latestInteraction: latest_interaction,
    unreadCount: unread_visible_messages,
    openCount: open_feedback_count,
    resolvedCount: resolved_feedback_count,
    threadItems: items,
  });
  const collaboration = parseCollaboration(
    record.collaboration,
    "thread.collaboration",
    {
      reviewSignals: review_signals,
      feedbackPolicy: feedback_policy,
      latestFeedback:
        latest_interaction?.actor_role === "mesa" ? latest_interaction : null,
      unreadCount: unread_visible_messages,
      openCount: open_feedback_count,
      resolvedCount: resolved_feedback_count,
    },
  );
  const sync = parseThreadSync(record.sync, "thread.sync");

  return {
    contract_name: "MobileInspectorThreadV2",
    contract_version: "v2",
    tenant_id: lerString(record, "tenant_id", "thread"),
    source_channel: lerStringOpcional(record, "source_channel"),
    case_id: lerStringOuNull(record, "case_id"),
    legacy_laudo_id: lerNumeroOuNull(record, "legacy_laudo_id"),
    thread_id: lerStringOuNull(record, "thread_id"),
    visibility_scope: lerVisibilidade(record, "thread"),
    case_status: lerStringOpcional(record, "case_status"),
    case_lifecycle_status: lerCaseLifecycleStatusOpcional(
      record,
      "case_lifecycle_status",
      "analise_livre",
    ),
    case_workflow_mode: lerCaseWorkflowModeOpcional(
      record,
      "case_workflow_mode",
      "analise_livre",
    ),
    active_owner_role: lerActiveOwnerRoleOpcional(
      record,
      "active_owner_role",
      "inspetor",
    ),
    allowed_next_lifecycle_statuses: lerArrayStringsOpcional(
      record,
      "allowed_next_lifecycle_statuses",
    ),
    allowed_lifecycle_transitions: parseLifecycleTransitions(
      record,
      "allowed_lifecycle_transitions",
      "thread",
    ),
    allowed_surface_actions: lerSurfaceActionsOpcional(
      record,
      "allowed_surface_actions",
    ),
    human_validation_required: lerBooleanOpcional(
      record,
      "human_validation_required",
    ),
    legacy_public_state: lerStringOpcional(record, "legacy_public_state"),
    allows_edit: lerBooleanOpcional(record, "allows_edit"),
    allows_reopen: lerBooleanOpcional(record, "allows_reopen"),
    case_card: parseCaseCard(record.case_card, "thread.case_card"),
    total_visible_messages: lerNumero(
      record,
      "total_visible_messages",
      "thread",
    ),
    unread_visible_messages,
    open_feedback_count,
    resolved_feedback_count,
    latest_interaction,
    review_signals,
    feedback_policy,
    collaboration,
    provenance_summary: lerRecordOuNull(record, "provenance_summary"),
    policy_summary: lerRecordOuNull(record, "policy_summary"),
    document_readiness: lerRecordOuNull(record, "document_readiness"),
    document_blockers: lerArrayRegistros(
      record,
      "document_blockers",
      "thread",
    ).map((blocker) => ({ ...blocker })),
    mobile_review_package: parseReviewPackage(
      record.mobile_review_package,
      "thread.mobile_review_package",
    ),
    attachment_policy: parseAttachmentPolicy(
      record.attachment_policy,
      "thread.attachment_policy",
    ),
    sync,
    sync_policy: parseSyncPolicy(
      record.sync_policy,
      "thread.sync_policy",
      sync,
    ),
    items,
    timestamp: lerString(record, "timestamp", "thread"),
  };
}

function mapReviewPackageToLegacy(
  value: MobileInspectorReviewPackageV2 | null,
): MobileReviewPackage | null {
  if (!value) {
    return null;
  }
  return {
    review_mode: value.review_mode,
    review_required: value.review_required,
    policy_summary: value.policy_summary ?? null,
    document_readiness: value.document_readiness ?? null,
    document_blockers: value.document_blockers.map((item) => ({ ...item })),
    revisao_por_bloco: value.revisao_por_bloco
      ? { ...value.revisao_por_bloco }
      : null,
    coverage_map: value.coverage_map ? { ...value.coverage_map } : null,
    inspection_history: value.inspection_history
      ? { ...value.inspection_history }
      : null,
    human_override_summary: value.human_override_summary
      ? { ...value.human_override_summary }
      : null,
    public_verification: value.public_verification
      ? { ...value.public_verification }
      : null,
    anexo_pack: value.anexo_pack ? { ...value.anexo_pack } : null,
    emissao_oficial: value.emissao_oficial
      ? { ...value.emissao_oficial }
      : null,
    historico_refazer_inspetor: value.historico_refazer_inspetor.map(
      (item) => ({
        ...item,
      }),
    ),
    memoria_operacional_familia: value.memoria_operacional_familia
      ? { ...value.memoria_operacional_familia }
      : null,
    red_flags: value.red_flags.map((item) => ({ ...item })),
    tenant_entitlements: value.tenant_entitlements
      ? { ...value.tenant_entitlements }
      : null,
    allowed_decisions: [...value.allowed_decisions],
    supports_block_reopen: value.supports_block_reopen,
  };
}

function mapAttachmentPolicyToLegacy(
  value: MobileInspectorAttachmentPolicyV2 | null,
): MobileAttachmentPolicy | null {
  if (!value) {
    return null;
  }
  return {
    contract_name: value.contract_name,
    contract_version: value.contract_version,
    policy_name: value.policy_name,
    upload_allowed: value.upload_allowed,
    download_allowed: value.download_allowed,
    inline_preview_allowed: value.inline_preview_allowed,
    supported_categories: [...value.supported_categories],
    supported_mime_types: [...value.supported_mime_types],
    visibility_scope: value.visibility_scope,
  };
}

function mapCaseCardToLegacy(
  card: MobileInspectorCaseCardV2 | null,
  fallbackLaudoId: number | null,
): MobileLaudoCard | null {
  if (!card) {
    return null;
  }
  const id = card.legacy_laudo_id ?? fallbackLaudoId;
  if (typeof id !== "number" || !Number.isFinite(id)) {
    throw erroContrato(
      "missing_legacy_laudo_id",
      "Case card V2 sem legacy_laudo_id para compatibilidade com a UI atual.",
    );
  }
  return {
    id,
    titulo: card.title,
    preview: card.preview,
    pinado: card.is_pinned,
    data_iso: card.date_iso,
    data_br: card.date_display,
    hora_br: card.time_display,
    tipo_template: card.template_key,
    status_revisao: card.review_status,
    status_card: card.card_status,
    status_card_label: card.card_status_label,
    permite_edicao: card.allows_edit,
    permite_reabrir: card.allows_reopen,
    possui_historico: card.has_history,
  };
}

function mapAnexoToLegacy(
  value: MobileInspectorAttachmentV2,
): MobileAttachment {
  return {
    id: value.attachment_id ?? undefined,
    nome: value.name || undefined,
    mime_type: value.mime_type || undefined,
    categoria: value.category || undefined,
    tamanho_bytes: Number.isFinite(value.size_bytes)
      ? value.size_bytes
      : undefined,
    eh_imagem: value.is_image,
    url: value.download_url || undefined,
  };
}

function mapResumoLegacy(params: {
  updatedAt: string;
  totalMensagens: number;
  mensagensNaoLidas: number;
  pendenciasAbertas: number;
  pendenciasResolvidas: number;
  latestInteraction: MobileInspectorInteractionSummaryV2 | null;
}): MobileMesaResumo {
  const latest = params.latestInteraction;
  return {
    atualizado_em: params.updatedAt,
    total_mensagens: params.totalMensagens,
    mensagens_nao_lidas: params.mensagensNaoLidas,
    pendencias_abertas: params.pendenciasAbertas,
    pendencias_resolvidas: params.pendenciasResolvidas,
    ultima_mensagem_id: latest?.message_id ?? null,
    ultima_mensagem_em: latest?.timestamp ?? "",
    ultima_mensagem_preview: latest?.text_preview ?? "",
    ultima_mensagem_tipo: latest?.legacy_message_type ?? "",
    ultima_mensagem_remetente_id: latest?.sender_id ?? null,
    ultima_mensagem_client_message_id: latest?.client_message_id ?? undefined,
  };
}

function mapThreadMessageAsSummary(
  message: MobileInspectorThreadMessageV2,
): MobileInspectorInteractionSummaryV2 {
  return {
    contract_name: "MobileInspectorInteractionSummaryV2",
    contract_version: message.contract_version,
    interaction_id: message.interaction_id,
    message_id: message.message_id,
    actor_role: message.actor_role,
    actor_kind: message.actor_kind,
    origin_kind: message.origin_kind,
    content_kind: message.content_kind,
    legacy_message_type: message.legacy_message_type,
    item_kind: message.item_kind,
    message_kind: message.message_kind,
    pendency_state: message.pendency_state,
    text_preview: message.text_preview,
    timestamp: message.timestamp,
    sender_id: message.sender_id,
    client_message_id: message.client_message_id,
    reference_message_id: message.reference_message_id,
    operational_context: message.operational_context ?? null,
    is_read: message.is_read,
    has_attachments: message.has_attachments,
    review_feedback_visible: message.review_feedback_visible,
    review_marker_visible: message.review_marker_visible,
    highlight_marker: isOpenPendencyState(message.pendency_state),
    pending_open: isOpenPendencyState(message.pendency_state),
    pending_resolved: isResolvedPendencyState(message.pendency_state),
    visibility_scope: message.visibility_scope,
  };
}

function ajustarContadoresParaVisibilidade(
  reviewSignals: MobileInspectorReviewSignalsV2,
  counts: {
    unread: number;
    open: number;
    resolved: number;
  },
) {
  if (reviewSignals.review_visible_to_inspector) {
    return counts;
  }
  return {
    unread: 0,
    open: 0,
    resolved: 0,
  };
}

function mapThreadMessageToLegacy(
  message: MobileInspectorThreadMessageV2,
  legacyLaudoId: number,
): MobileMesaMessage {
  const id = message.message_id ?? message.cursor_id;
  if (typeof id !== "number" || !Number.isFinite(id)) {
    throw erroContrato(
      "missing_message_id",
      "Mensagem V2 sem message_id/cursor_id para compatibilidade com a UI atual.",
    );
  }
  return {
    id,
    laudo_id: legacyLaudoId,
    tipo: message.legacy_message_type,
    item_kind: message.item_kind,
    message_kind: message.message_kind,
    pendency_state: message.pendency_state,
    texto: message.content_text || message.text_preview,
    remetente_id: message.sender_id,
    data: message.display_date,
    criado_em_iso: message.timestamp,
    lida: message.is_read,
    resolvida_em: message.resolved_at || "",
    resolvida_em_label: message.resolved_at_label,
    resolvida_por_nome: message.resolved_by_name,
    entrega_status: message.delivery_status || "persisted",
    client_message_id: message.client_message_id ?? undefined,
    referencia_mensagem_id: message.reference_message_id ?? undefined,
    operational_context: message.operational_context ?? undefined,
    anexos: message.attachments.map((item) => mapAnexoToLegacy(item)),
  };
}

export function mapMobileInspectorFeedV2ToLegacy(
  payload: MobileInspectorFeedV2,
): MobileMesaFeedResponse {
  const itens: MobileMesaFeedItem[] = payload.items.map((item) => {
    const legacyLaudoId = item.legacy_laudo_id;
    if (typeof legacyLaudoId !== "number" || !Number.isFinite(legacyLaudoId)) {
      throw erroContrato(
        "missing_legacy_laudo_id",
        "Feed V2 sem legacy_laudo_id não pode alimentar a UI legada.",
      );
    }
    const counters = ajustarContadoresParaVisibilidade(item.review_signals, {
      unread: item.collaboration.summary.unread_feedback_count,
      open: item.collaboration.summary.open_feedback_count,
      resolved: item.collaboration.summary.resolved_feedback_count,
    });
    return {
      laudo_id: legacyLaudoId,
      estado: item.legacy_public_state || "sem_relatorio",
      status_card:
        item.case_card?.card_status ||
        item.case_status ||
        item.legacy_public_state ||
        "sem_relatorio",
      permite_edicao: item.allows_edit,
      permite_reabrir: item.allows_reopen,
      laudo_card: mapCaseCardToLegacy(item.case_card, legacyLaudoId),
      resumo: mapResumoLegacy({
        updatedAt: item.updated_at || item.latest_interaction?.timestamp || "",
        totalMensagens: item.total_visible_interactions,
        mensagensNaoLidas: counters.unread,
        pendenciasAbertas: counters.open,
        pendenciasResolvidas: counters.resolved,
        latestInteraction: item.latest_interaction,
      }),
    };
  });

  return {
    cursor_atual: payload.cursor_current,
    laudo_ids: payload.requested_laudo_ids,
    itens,
  };
}

export function mapMobileInspectorThreadV2ToLegacy(
  payload: MobileInspectorThreadV2,
): MobileMesaMensagensResponse {
  const legacyLaudoId = payload.legacy_laudo_id;
  if (typeof legacyLaudoId !== "number" || !Number.isFinite(legacyLaudoId)) {
    throw erroContrato(
      "missing_legacy_laudo_id",
      "Thread V2 sem legacy_laudo_id não pode alimentar a UI legada.",
    );
  }
  const counters = ajustarContadoresParaVisibilidade(payload.review_signals, {
    unread: payload.collaboration.summary.unread_feedback_count,
    open: payload.collaboration.summary.open_feedback_count,
    resolved: payload.collaboration.summary.resolved_feedback_count,
  });
  const latestInteraction =
    payload.latest_interaction ||
    (payload.items.length
      ? mapThreadMessageAsSummary(payload.items[payload.items.length - 1])
      : null);

  return {
    laudo_id: legacyLaudoId,
    itens: payload.items.map((item) =>
      mapThreadMessageToLegacy(item, legacyLaudoId),
    ),
    cursor_proximo: payload.sync.next_cursor_id,
    cursor_ultimo_id: payload.sync.cursor_last_message_id,
    tem_mais: payload.sync.has_more,
    estado: payload.legacy_public_state || "sem_relatorio",
    status_card:
      payload.case_card?.card_status ||
      payload.case_status ||
      payload.legacy_public_state ||
      "sem_relatorio",
    permite_edicao: payload.allows_edit,
    permite_reabrir: payload.allows_reopen,
    laudo_card: mapCaseCardToLegacy(payload.case_card, legacyLaudoId),
    attachment_policy: mapAttachmentPolicyToLegacy(payload.attachment_policy),
    review_package: mapReviewPackageToLegacy(payload.mobile_review_package),
    resumo: mapResumoLegacy({
      updatedAt: latestInteraction?.timestamp || "",
      totalMensagens: payload.total_visible_messages,
      mensagensNaoLidas: counters.unread,
      pendenciasAbertas: counters.open,
      pendenciasResolvidas: counters.resolved,
      latestInteraction,
    }),
    sync: {
      modo: payload.sync.mode,
      apos_id: payload.sync.cursor_after_id,
      cursor_ultimo_id: payload.sync.cursor_last_message_id,
    },
  };
}
