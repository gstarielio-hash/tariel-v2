export type MobileInspectorVisibilityScopeV2 = "inspetor_mobile";
export type MobileInspectorActorRoleV2 = "inspetor" | "mesa";
export type MobileInspectorCaseLifecycleStatusV2 =
  | "analise_livre"
  | "pre_laudo"
  | "laudo_em_coleta"
  | "aguardando_mesa"
  | "em_revisao_mesa"
  | "devolvido_para_correcao"
  | "aprovado"
  | "emitido";
export type MobileInspectorCaseWorkflowModeV2 =
  | "analise_livre"
  | "laudo_guiado"
  | "laudo_com_mesa";
export type MobileInspectorActiveOwnerRoleV2 = "inspetor" | "mesa" | "none";
export type MobileInspectorTransitionKindV2 =
  | "analysis"
  | "advance"
  | "review"
  | "approval"
  | "correction"
  | "reopen"
  | "issue";
export type MobileInspectorPreferredSurfaceV2 =
  | "chat"
  | "mesa"
  | "mobile"
  | "system";
export type MobileInspectorSurfaceActionV2 =
  | "chat_finalize"
  | "chat_reopen"
  | "mesa_approve"
  | "mesa_return"
  | "system_issue";
export type MobileMesaItemKindV2 = "message" | "whisper" | "pendency";
export type MobileMesaMessageKindV2 =
  | "inspector_message"
  | "inspector_whisper"
  | "mesa_pendency"
  | "ai_message"
  | "system_message";
export type MobileMesaPendencyStateV2 = "not_applicable" | "open" | "resolved";

export interface MobileInspectorCaseCardV2 {
  contract_name: "MobileInspectorCaseCardV2";
  contract_version: "v2";
  legacy_laudo_id: number | null;
  title: string;
  preview: string;
  template_key: string;
  review_status: string;
  card_status: string;
  card_status_label: string;
  date_iso: string;
  date_display: string;
  time_display: string;
  is_pinned: boolean;
  allows_edit: boolean;
  allows_reopen: boolean;
  has_history: boolean;
  visibility_scope: MobileInspectorVisibilityScopeV2;
}

export interface MobileInspectorReviewSignalsV2 {
  contract_name: "MobileInspectorReviewSignalsV2";
  contract_version: "v2";
  review_visible_to_inspector: boolean;
  total_visible_interactions: number;
  visible_feedback_count: number;
  open_feedback_count: number;
  resolved_feedback_count: number;
  latest_feedback_message_id: number | null;
  latest_feedback_at: string | null;
  visibility_scope: MobileInspectorVisibilityScopeV2;
}

export interface MobileInspectorFeedbackPolicyV2 {
  contract_name: "MobileInspectorFeedbackPolicyV2";
  contract_version: "v2";
  policy_name: "android_feedback_sync_policy";
  feedback_mode: "hidden" | "visible_feedback_only";
  feedback_counters_visible: boolean;
  feedback_message_bodies_visible: boolean;
  latest_feedback_pointer_visible: boolean;
  mesa_internal_details_visible: false;
  visibility_scope: MobileInspectorVisibilityScopeV2;
}

export interface MobileInspectorInteractionSummaryV2 {
  contract_name: "MobileInspectorInteractionSummaryV2";
  contract_version: "v2";
  interaction_id: string;
  message_id: number | null;
  actor_role: MobileInspectorActorRoleV2;
  actor_kind: string;
  origin_kind: string;
  content_kind: string;
  legacy_message_type: string;
  item_kind: MobileMesaItemKindV2;
  message_kind: MobileMesaMessageKindV2;
  pendency_state: MobileMesaPendencyStateV2;
  text_preview: string;
  timestamp: string;
  sender_id: number | null;
  client_message_id: string | null;
  reference_message_id: number | null;
  operational_context?: Record<string, unknown> | null;
  is_read: boolean;
  has_attachments: boolean;
  review_feedback_visible: boolean;
  review_marker_visible: boolean;
  highlight_marker: boolean;
  pending_open: boolean;
  pending_resolved: boolean;
  visibility_scope: MobileInspectorVisibilityScopeV2;
}

export interface MobileInspectorCollaborationSummaryV2 {
  contract_name: "MobileInspectorCollaborationSummaryV2";
  contract_version: "v2";
  feedback_visible_to_inspector: boolean;
  visible_feedback_count: number;
  unread_feedback_count: number;
  open_feedback_count: number;
  resolved_feedback_count: number;
  latest_feedback_message_id: number | null;
  latest_feedback_at: string | null;
  latest_feedback_preview: string;
  visibility_scope: MobileInspectorVisibilityScopeV2;
}

export interface MobileInspectorCollaborationV2 {
  contract_name: "MobileInspectorCollaborationV2";
  contract_version: "v2";
  summary: MobileInspectorCollaborationSummaryV2;
  latest_feedback: MobileInspectorInteractionSummaryV2 | null;
  visibility_scope: MobileInspectorVisibilityScopeV2;
}

export interface MobileInspectorAttachmentV2 {
  contract_name: "MobileInspectorAttachmentV2";
  contract_version: "v2";
  attachment_id: number | null;
  name: string;
  mime_type: string;
  category: string;
  size_bytes: number;
  download_url: string | null;
  is_image: boolean;
  visibility_scope: MobileInspectorVisibilityScopeV2;
}

export interface MobileInspectorAttachmentPolicyV2 {
  contract_name: "MobileInspectorAttachmentPolicyV2";
  contract_version: "v2";
  policy_name: "android_attachment_sync_policy";
  upload_allowed: boolean;
  download_allowed: boolean;
  inline_preview_allowed: boolean;
  supported_categories: string[];
  supported_mime_types: string[];
  visibility_scope: MobileInspectorVisibilityScopeV2;
}

export interface MobileInspectorReviewPackageV2 {
  contract_name: "MobileInspectorReviewPackageV2";
  contract_version: "v2";
  review_mode: string | null;
  review_required: boolean | null;
  policy_summary: Record<string, unknown> | null;
  document_readiness: Record<string, unknown> | null;
  document_blockers: Array<Record<string, unknown>>;
  revisao_por_bloco: Record<string, unknown> | null;
  coverage_map: Record<string, unknown> | null;
  inspection_history: Record<string, unknown> | null;
  human_override_summary: Record<string, unknown> | null;
  public_verification: Record<string, unknown> | null;
  anexo_pack: Record<string, unknown> | null;
  emissao_oficial: Record<string, unknown> | null;
  historico_refazer_inspetor: Array<Record<string, unknown>>;
  memoria_operacional_familia: Record<string, unknown> | null;
  red_flags: Array<Record<string, unknown>>;
  tenant_entitlements: Record<string, unknown> | null;
  allowed_decisions: string[];
  supports_block_reopen: boolean;
  visibility_scope: MobileInspectorVisibilityScopeV2;
}

export interface MobileInspectorLifecycleTransitionV2 {
  target_status: MobileInspectorCaseLifecycleStatusV2;
  transition_kind: MobileInspectorTransitionKindV2;
  label: string;
  owner_role: MobileInspectorActiveOwnerRoleV2;
  preferred_surface: MobileInspectorPreferredSurfaceV2;
}

export interface MobileInspectorFeedItemV2 {
  contract_name: "MobileInspectorFeedItemV2";
  contract_version: "v2";
  tenant_id: string;
  source_channel: string;
  case_id: string | null;
  legacy_laudo_id: number | null;
  thread_id: string | null;
  visibility_scope: MobileInspectorVisibilityScopeV2;
  case_status: string;
  case_lifecycle_status: MobileInspectorCaseLifecycleStatusV2;
  case_workflow_mode: MobileInspectorCaseWorkflowModeV2;
  active_owner_role: MobileInspectorActiveOwnerRoleV2;
  allowed_next_lifecycle_statuses: string[];
  allowed_lifecycle_transitions: MobileInspectorLifecycleTransitionV2[];
  allowed_surface_actions: MobileInspectorSurfaceActionV2[];
  human_validation_required: boolean;
  legacy_public_state: string;
  allows_edit: boolean;
  allows_reopen: boolean;
  has_interaction: boolean;
  case_card: MobileInspectorCaseCardV2 | null;
  updated_at: string | null;
  total_visible_interactions: number;
  unread_visible_interactions: number;
  open_feedback_count: number;
  resolved_feedback_count: number;
  latest_interaction: MobileInspectorInteractionSummaryV2 | null;
  review_signals: MobileInspectorReviewSignalsV2;
  feedback_policy: MobileInspectorFeedbackPolicyV2;
  collaboration: MobileInspectorCollaborationV2;
  provenance_summary: Record<string, unknown> | null;
  policy_summary: Record<string, unknown> | null;
  document_readiness: Record<string, unknown> | null;
  document_blockers: Array<Record<string, unknown>>;
}

export interface MobileInspectorFeedV2 {
  contract_name: "MobileInspectorFeedV2";
  contract_version: "v2";
  tenant_id: string;
  source_channel: string;
  visibility_scope: MobileInspectorVisibilityScopeV2;
  requested_laudo_ids: number[];
  cursor_current: string;
  total_requested_cases: number;
  returned_item_count: number;
  items: MobileInspectorFeedItemV2[];
  timestamp: string;
}

export type MobileInspectorThreadMessageV2 = Omit<
  MobileInspectorInteractionSummaryV2,
  "contract_name"
> & {
  contract_name: "MobileInspectorThreadMessageV2";
  content_text: string;
  display_date: string;
  resolved_at: string | null;
  resolved_at_label: string;
  resolved_by_name: string;
  attachments: MobileInspectorAttachmentV2[];
  delivery_status: string;
  order_index: number;
  cursor_id: number | null;
  is_delta_item: boolean;
};

export interface MobileInspectorThreadSyncV2 {
  contract_name: "MobileInspectorThreadSyncV2";
  contract_version: "v2";
  mode: "full" | "delta";
  cursor_after_id: number | null;
  next_cursor_id: number | null;
  cursor_last_message_id: number | null;
  has_more: boolean;
}

export interface MobileInspectorSyncPolicyV2 {
  contract_name: "MobileInspectorSyncPolicyV2";
  contract_version: "v2";
  policy_name: "android_thread_sync_policy";
  mode: "full" | "delta";
  offline_queue_supported: boolean;
  incremental_sync_supported: boolean;
  attachment_sync_supported: boolean;
  visibility_scope: MobileInspectorVisibilityScopeV2;
}

export interface MobileInspectorThreadV2 {
  contract_name: "MobileInspectorThreadV2";
  contract_version: "v2";
  tenant_id: string;
  source_channel: string;
  case_id: string | null;
  legacy_laudo_id: number | null;
  thread_id: string | null;
  visibility_scope: MobileInspectorVisibilityScopeV2;
  case_status: string;
  case_lifecycle_status: MobileInspectorCaseLifecycleStatusV2;
  case_workflow_mode: MobileInspectorCaseWorkflowModeV2;
  active_owner_role: MobileInspectorActiveOwnerRoleV2;
  allowed_next_lifecycle_statuses: string[];
  allowed_lifecycle_transitions: MobileInspectorLifecycleTransitionV2[];
  allowed_surface_actions: MobileInspectorSurfaceActionV2[];
  human_validation_required: boolean;
  legacy_public_state: string;
  allows_edit: boolean;
  allows_reopen: boolean;
  case_card: MobileInspectorCaseCardV2 | null;
  total_visible_messages: number;
  unread_visible_messages: number;
  open_feedback_count: number;
  resolved_feedback_count: number;
  latest_interaction: MobileInspectorInteractionSummaryV2 | null;
  review_signals: MobileInspectorReviewSignalsV2;
  feedback_policy: MobileInspectorFeedbackPolicyV2;
  collaboration: MobileInspectorCollaborationV2;
  provenance_summary: Record<string, unknown> | null;
  policy_summary: Record<string, unknown> | null;
  document_readiness: Record<string, unknown> | null;
  document_blockers: Array<Record<string, unknown>>;
  mobile_review_package: MobileInspectorReviewPackageV2 | null;
  attachment_policy: MobileInspectorAttachmentPolicyV2;
  sync: MobileInspectorThreadSyncV2;
  sync_policy: MobileInspectorSyncPolicyV2;
  items: MobileInspectorThreadMessageV2[];
  timestamp: string;
}
