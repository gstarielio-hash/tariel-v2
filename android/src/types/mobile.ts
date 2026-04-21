export type ApiHealthStatus = "checking" | "online" | "offline";
export type MobileChatMode = "curto" | "detalhado" | "deep_research";
export type MobileInspectionEntryModePreference =
  | "chat_first"
  | "evidence_first"
  | "auto_recommended";
export type MobileInspectionEntryModeEffective =
  | "chat_first"
  | "evidence_first";
export type MobileEstadoLaudo =
  | "sem_relatorio"
  | "relatorio_ativo"
  | "aguardando"
  | "ajustes"
  | "aprovado";
export type MobileCaseLifecycleStatus =
  | "analise_livre"
  | "pre_laudo"
  | "laudo_em_coleta"
  | "aguardando_mesa"
  | "em_revisao_mesa"
  | "devolvido_para_correcao"
  | "aprovado"
  | "emitido";
export type MobileCaseWorkflowMode =
  | "analise_livre"
  | "laudo_guiado"
  | "laudo_com_mesa";
export type MobileActiveOwnerRole = "inspetor" | "mesa" | "none";
export type MobileLifecycleTransitionKind =
  | "analysis"
  | "advance"
  | "review"
  | "approval"
  | "correction"
  | "reopen"
  | "issue";
export type MobilePreferredSurface = "chat" | "mesa" | "mobile" | "system";
export type MobileSurfaceAction =
  | "chat_finalize"
  | "chat_reopen"
  | "mesa_approve"
  | "mesa_return"
  | "system_issue";
export type MobileUserPortal = "cliente" | "inspetor" | "revisor";
export type MobileCommercialOperatingModel =
  | "standard"
  | "mobile_single_operator";
export type MobileIdentityRuntimeMode =
  | "standard_role_accounts"
  | "tenant_scoped_portal_grants";

export interface MobilePortalSwitchLink {
  portal: MobileUserPortal;
  label: string;
  url: string;
}

export interface MobileLifecycleTransition {
  target_status: MobileCaseLifecycleStatus;
  transition_kind: MobileLifecycleTransitionKind;
  label: string;
  owner_role: MobileActiveOwnerRole;
  preferred_surface: MobilePreferredSurface;
}

export interface MobileUser {
  id: number;
  nome_completo: string;
  email: string;
  telefone: string;
  foto_perfil_url: string;
  empresa_nome: string;
  empresa_id: number;
  nivel_acesso: number;
  allowed_portals?: MobileUserPortal[];
  allowed_portal_labels?: string[];
  commercial_operating_model?: MobileCommercialOperatingModel;
  commercial_operating_model_label?: string;
  identity_runtime_mode?: MobileIdentityRuntimeMode;
  identity_runtime_note?: string;
  portal_switch_links?: MobilePortalSwitchLink[];
  admin_ceo_governed?: boolean;
}

export interface MobileLoginResponse {
  ok: boolean;
  auth_mode: "bearer";
  access_token: string;
  token_type: "bearer";
  usuario: MobileUser;
}

export interface MobileAccountProfileResponse {
  ok: boolean;
  usuario: MobileUser;
}

export interface MobileAccountPasswordResponse {
  ok: boolean;
  message: string;
}

export interface MobileSupportReportResponse {
  ok: boolean;
  protocolo: string;
  status: string;
}

export interface MobilePushRegistration {
  id: number;
  device_id: string;
  plataforma: string;
  provider: string;
  push_token: string;
  permissao_notificacoes: boolean;
  push_habilitado: boolean;
  token_status: string;
  canal_build: string;
  app_version: string;
  build_number: string;
  device_label: string;
  is_emulator: boolean;
  ultimo_erro: string;
  registered_at: string;
  last_seen_at: string;
}

export interface MobilePushRegistrationResponse {
  ok: boolean;
  registration: MobilePushRegistration;
}

export interface MobileCriticalNotificationsSettings {
  notifica_respostas: boolean;
  notifica_push: boolean;
  som_notificacao: string;
  vibracao_ativa: boolean;
  emails_ativos: boolean;
}

export interface MobileCriticalPrivacySettings {
  mostrar_conteudo_notificacao: boolean;
  ocultar_conteudo_bloqueado: boolean;
  mostrar_somente_nova_mensagem: boolean;
  salvar_historico_conversas: boolean;
  compartilhar_melhoria_ia: boolean;
  retencao_dados: string;
}

export interface MobileCriticalPermissionsSettings {
  microfone_permitido: boolean;
  camera_permitida: boolean;
  arquivos_permitidos: boolean;
  notificacoes_permitidas: boolean;
  biometria_permitida: boolean;
}

export interface MobileCriticalAiExperienceSettings {
  modelo_ia: "rápido" | "equilibrado" | "avançado";
  entry_mode_preference?: MobileInspectionEntryModePreference;
  remember_last_case_mode?: boolean;
}

export interface MobileCriticalSettings {
  notificacoes: MobileCriticalNotificationsSettings;
  privacidade: MobileCriticalPrivacySettings;
  permissoes: MobileCriticalPermissionsSettings;
  experiencia_ia: MobileCriticalAiExperienceSettings;
}

export interface MobileCriticalSettingsResponse {
  ok: boolean;
  settings: MobileCriticalSettings;
}

export interface MobileBootstrapResponse {
  ok: boolean;
  app: {
    nome: string;
    portal: string;
    api_base_url: string;
    suporte_whatsapp: string;
  };
  usuario: MobileUser;
}

export interface MobileLaudoListResponse {
  ok: boolean;
  itens: MobileLaudoCard[];
}

export interface MobileOfficialIssueSummary {
  label: string;
  detail: string;
  primary_pdf_diverged: boolean;
  issue_number?: string | null;
  issue_state_label?: string | null;
  primary_pdf_storage_version?: string | null;
  current_primary_pdf_storage_version?: string | null;
}

export interface MobileLaudoCard {
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
  permite_reabrir: boolean;
  possui_historico: boolean;
  case_lifecycle_status?: MobileCaseLifecycleStatus;
  case_workflow_mode?: MobileCaseWorkflowMode;
  active_owner_role?: MobileActiveOwnerRole;
  allowed_next_lifecycle_statuses?: string[];
  allowed_lifecycle_transitions?: MobileLifecycleTransition[];
  allowed_surface_actions?: MobileSurfaceAction[];
  report_pack_draft?: MobileReportPackDraft | null;
  official_issue_summary?: MobileOfficialIssueSummary | null;
  entry_mode_preference?: MobileInspectionEntryModePreference;
  entry_mode_effective?: MobileInspectionEntryModeEffective;
  entry_mode_reason?: string;
}

export interface MobileAttachment {
  id?: number;
  nome?: string;
  nome_original?: string;
  nome_arquivo?: string;
  label?: string;
  mime_type?: string;
  categoria?: string;
  tamanho_bytes?: number;
  eh_imagem?: boolean;
  url?: string;
}

export interface MobileAttachmentPolicy {
  contract_name?: "MobileInspectorAttachmentPolicyV2";
  contract_version?: "v2";
  policy_name: "android_attachment_sync_policy";
  upload_allowed: boolean;
  download_allowed: boolean;
  inline_preview_allowed: boolean;
  supported_categories: string[];
  supported_mime_types: string[];
  visibility_scope?: "inspetor_mobile";
}

export interface MobileChatMessage {
  id: number | null;
  papel: "usuario" | "assistente" | "engenheiro";
  texto: string;
  tipo: string;
  modo?: MobileChatMode | string;
  is_whisper?: boolean;
  remetente_id?: number | null;
  referencia_mensagem_id?: number | null;
  anexos?: MobileAttachment[];
  citacoes?: Array<Record<string, unknown>>;
  confianca_ia?: Record<string, unknown>;
}

export interface MobileGuidedInspectionChecklistItemPayload {
  id: string;
  title: string;
  prompt: string;
  evidence_hint: string;
}

export interface MobileGuidedInspectionEvidenceRefPayload {
  message_id: number;
  step_id: string;
  step_title: string;
  captured_at: string;
  evidence_kind: "chat_message";
  attachment_kind: "none" | "image" | "document" | "mixed";
}

export interface MobileGuidedInspectionMesaHandoffPayload {
  required: boolean;
  review_mode: string;
  reason_code: string;
  recorded_at: string;
  step_id: string;
  step_title: string;
}

export interface MobileGuidedInspectionDraftPayload {
  template_key:
    | "padrao"
    | "avcb"
    | "cbmgo"
    | "loto"
    | "nr11_movimentacao"
    | "nr12maquinas"
    | "nr13"
    | "nr13_calibracao"
    | "nr13_teste_hidrostatico"
    | "nr13_ultrassom"
    | "nr20_instalacoes"
    | "nr33_espaco_confinado"
    | "nr35_linha_vida"
    | "nr35_montagem"
    | "nr35_ponto_ancoragem"
    | "nr35_projeto"
    | "pie"
    | "rti"
    | "spda";
  template_label: string;
  started_at: string;
  current_step_index: number;
  completed_step_ids: string[];
  checklist: MobileGuidedInspectionChecklistItemPayload[];
  evidence_bundle_kind?: "case_thread";
  evidence_refs?: MobileGuidedInspectionEvidenceRefPayload[];
  mesa_handoff?: MobileGuidedInspectionMesaHandoffPayload | null;
}

export interface MobileGuidedInspectionMessageContextPayload {
  template_key:
    | "padrao"
    | "avcb"
    | "cbmgo"
    | "loto"
    | "nr11_movimentacao"
    | "nr12maquinas"
    | "nr13"
    | "nr13_calibracao"
    | "nr13_teste_hidrostatico"
    | "nr13_ultrassom"
    | "nr20_instalacoes"
    | "nr33_espaco_confinado"
    | "nr35_linha_vida"
    | "nr35_montagem"
    | "nr35_ponto_ancoragem"
    | "nr35_projeto"
    | "pie"
    | "rti"
    | "spda";
  step_id: string;
  step_title: string;
  attachment_kind: "none" | "image" | "document" | "mixed";
}

export interface MobilePreLaudoDocumentFlowEntry {
  key?: string;
  title: string;
  status: string;
  status_label?: string;
  summary?: string;
}

export interface MobilePreLaudoDocumentHighlight {
  path?: string;
  label: string;
}

export interface MobilePreLaudoDocumentSection {
  section_key: string;
  title: string;
  status: string;
  status_label?: string;
  summary: string;
  filled_field_count: number;
  missing_field_count: number;
  total_field_count: number;
  highlights?: MobilePreLaudoDocumentHighlight[];
}

export interface MobilePreLaudoExecutiveSection {
  key: string;
  title: string;
  status: string;
  summary: string;
  bullets?: string[];
}

export interface MobilePreLaudoSlot {
  slot_id?: string;
  label: string;
  required?: boolean;
  accepted_types?: string[];
  binding_path?: string | null;
  purpose?: string | null;
}

export interface MobilePreLaudoChecklistGroupItem {
  item_id: string;
  label: string;
  critical?: boolean;
}

export interface MobilePreLaudoChecklistGroup {
  group_id: string;
  title: string;
  required?: boolean;
  items?: MobilePreLaudoChecklistGroupItem[];
}

export interface MobilePreLaudoMinimumEvidence {
  fotos: number;
  documentos: number;
  textos: number;
}

export interface MobilePreLaudoAnalysisBasisSummary {
  coverage_summary?: string | null;
  photo_summary?: string | null;
  document_summary?: string | null;
  context_summary?: string | null;
}

export interface MobilePreLaudoDocument {
  contract_name?: "MobilePreLaudoDocumentV1";
  contract_version?: "v1";
  family_key?: string | null;
  family_label?: string | null;
  template_key?: string | null;
  template_label?: string | null;
  artifact_snapshot?: Record<string, boolean>;
  document_flow?: MobilePreLaudoDocumentFlowEntry[];
  minimum_evidence?: MobilePreLaudoMinimumEvidence;
  required_slots?: MobilePreLaudoSlot[];
  optional_slots?: MobilePreLaudoSlot[];
  checklist_groups?: MobilePreLaudoChecklistGroup[];
  review_required?: string[];
  executive_sections?: MobilePreLaudoExecutiveSection[];
  document_sections?: MobilePreLaudoDocumentSection[];
  highlighted_sections?: MobilePreLaudoDocumentSection[];
  next_questions?: string[];
  analysis_basis_summary?: MobilePreLaudoAnalysisBasisSummary;
  example_available?: boolean;
}

export interface MobileReportPackOutline {
  status?: string;
  analysis_summary?: string | null;
  ready_for_structured_form?: boolean;
  ready_for_finalization?: boolean;
  final_validation_mode?: string | null;
  filled_field_count?: number;
  missing_field_count?: number;
  missing_highlights?: string[];
  next_questions?: string[];
}

export interface MobileReportPackQualityGateMissingEvidence {
  code?: string;
  message?: string;
}

export interface MobileReportPackQualityGates {
  checklist_complete?: boolean | null;
  required_image_slots_complete?: boolean | null;
  critical_items_complete?: boolean | null;
  requires_normative_curation?: boolean | null;
  autonomy_ready?: boolean | null;
  final_validation_mode?: string | null;
  max_conflict_score?: number | null;
  missing_evidence?: MobileReportPackQualityGateMissingEvidence[];
}

export interface MobileReportPackEvidenceSummary {
  evidence_count?: number;
  image_count?: number;
  text_count?: number;
}

export interface MobileReportPackDraft {
  [key: string]: unknown;
  modeled?: boolean;
  family?: string;
  family_key?: string;
  template_key?: string;
  template_label?: string;
  guided_context?: Record<string, unknown> | null;
  evidence_summary?: MobileReportPackEvidenceSummary | null;
  structured_data_candidate?: Record<string, unknown> | null;
  quality_gates?: MobileReportPackQualityGates | null;
  pre_laudo_outline?: MobileReportPackOutline | null;
  pre_laudo_document?: MobilePreLaudoDocument | null;
  analysis_basis?: Record<string, unknown> | null;
  image_slots?: Array<Record<string, unknown>>;
  items?: Array<Record<string, unknown>>;
}

export interface MobileReviewPackage {
  review_mode?: string | null;
  review_required?: boolean | null;
  policy_summary?: Record<string, unknown> | null;
  document_readiness?: Record<string, unknown> | null;
  document_blockers?: Array<Record<string, unknown>>;
  revisao_por_bloco?: Record<string, unknown> | null;
  coverage_map?: Record<string, unknown> | null;
  inspection_history?: Record<string, unknown> | null;
  human_override_summary?: Record<string, unknown> | null;
  public_verification?: Record<string, unknown> | null;
  anexo_pack?: Record<string, unknown> | null;
  emissao_oficial?: Record<string, unknown> | null;
  historico_refazer_inspetor?: Array<Record<string, unknown>>;
  memoria_operacional_familia?: Record<string, unknown> | null;
  red_flags?: Array<Record<string, unknown>>;
  tenant_entitlements?: Record<string, unknown> | null;
  allowed_decisions?: string[];
  supports_block_reopen?: boolean;
}

export interface MobileQualityGateItem {
  id: string;
  categoria: string;
  titulo: string;
  status: "ok" | "faltante" | string;
  atual: string | number | boolean | null;
  minimo: string | number | boolean | null;
  observacao: string;
}

export interface MobileQualityGateTemplateItem {
  id: string;
  categoria: string;
  titulo: string;
  descricao: string;
  obrigatorio: boolean;
}

export interface MobileQualityGateTemplateGuide {
  titulo: string;
  descricao: string;
  itens: MobileQualityGateTemplateItem[];
}

export interface MobileHumanOverrideCandidateItem {
  id: string;
  titulo: string;
  categoria: string;
  candidate_cases: string[];
  candidate_case_labels: string[];
}

export interface MobileHumanOverridePolicy {
  available: boolean;
  reason_required: boolean;
  allowed_override_cases: string[];
  allowed_override_case_labels: string[];
  matched_override_cases: string[];
  matched_override_case_labels: string[];
  overrideable_items: MobileHumanOverrideCandidateItem[];
  hard_blockers: MobileHumanOverrideCandidateItem[];
  family_key: string;
  responsibility_notice: string;
  message: string;
  requested?: boolean;
  validation_error?: string;
}

export interface MobileQualityGateResponse {
  codigo: string;
  aprovado: boolean;
  mensagem: string;
  tipo_template: string;
  template_nome: string;
  resumo: Record<string, string | number | boolean | null | undefined>;
  itens: MobileQualityGateItem[];
  faltantes: MobileQualityGateItem[];
  roteiro_template: MobileQualityGateTemplateGuide | null;
  report_pack_draft?: MobileReportPackDraft | null;
  review_mode_sugerido?: string | null;
  human_override_policy?: MobileHumanOverridePolicy | null;
}

export interface MobileQualityGateOverridePayload {
  enabled: boolean;
  reason: string;
  cases?: string[];
}

export interface MobileLaudoReopenRequest {
  issued_document_policy?: "keep_visible" | "hide_from_case";
}

export interface MobileLaudoStatusResponse {
  estado: MobileEstadoLaudo | string;
  laudo_id: number | null;
  status_card: string;
  permite_edicao: boolean;
  permite_reabrir: boolean;
  case_lifecycle_status?: MobileCaseLifecycleStatus;
  case_workflow_mode?: MobileCaseWorkflowMode;
  active_owner_role?: MobileActiveOwnerRole;
  allowed_next_lifecycle_statuses?: string[];
  allowed_lifecycle_transitions?: MobileLifecycleTransition[];
  allowed_surface_actions?: MobileSurfaceAction[];
  attachment_policy?: MobileAttachmentPolicy | null;
  issued_document_policy_applied?: "keep_visible" | "hide_from_case";
  had_previous_issued_document?: boolean;
  previous_issued_document_visible_in_case?: boolean;
  internal_learning_candidate_registered?: boolean;
  laudo_card: MobileLaudoCard | null;
  review_package?: MobileReviewPackage | null;
  modo?: MobileChatMode | string;
  entry_mode_preference?: MobileInspectionEntryModePreference;
  entry_mode_effective?: MobileInspectionEntryModeEffective;
  entry_mode_reason?: string;
  guided_inspection_draft?: MobileGuidedInspectionDraftPayload | null;
  report_pack_draft?: MobileReportPackDraft | null;
}

export interface MobileLaudoMensagensResponse extends MobileLaudoStatusResponse {
  itens: MobileChatMessage[];
  cursor_proximo: number | null;
  tem_mais: boolean;
  limite: number;
}

export interface MobileLaudoFinalizeResponse extends Partial<MobileLaudoStatusResponse> {
  success: boolean;
  message: string;
  laudo_id: number;
  review_mode_final?: string | null;
  inspection_history?: Record<string, unknown> | null;
  human_override_summary?: Record<string, unknown> | null;
  public_verification?: Record<string, unknown> | null;
  report_pack_draft?: MobileReportPackDraft | null;
}

export interface MobileMesaMessage {
  id: number;
  laudo_id: number;
  tipo: string;
  item_kind?: "message" | "whisper" | "pendency";
  message_kind?:
    | "inspector_message"
    | "inspector_whisper"
    | "mesa_pendency"
    | "ai_message"
    | "system_message";
  pendency_state?: "not_applicable" | "open" | "resolved";
  texto: string;
  remetente_id: number | null;
  data: string;
  criado_em_iso?: string;
  lida: boolean;
  resolvida_em: string;
  resolvida_em_label: string;
  resolvida_por_nome: string;
  entrega_status?: string;
  client_message_id?: string | null;
  referencia_mensagem_id?: number | null;
  operational_context?: Record<string, unknown> | null;
  anexos?: MobileAttachment[];
}

export interface MobileMesaResumo {
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
  ultima_mensagem_client_message_id?: string | null;
}

export interface MobileMesaSyncMeta {
  modo: "full" | "delta" | string;
  apos_id: number | null;
  cursor_ultimo_id: number | null;
}

export interface MobileMesaMensagensResponse extends MobileLaudoStatusResponse {
  itens: MobileMesaMessage[];
  cursor_proximo: number | null;
  cursor_ultimo_id?: number | null;
  tem_mais: boolean;
  resumo?: MobileMesaResumo;
  sync?: MobileMesaSyncMeta;
}

export interface MobileMesaSendResponse extends MobileLaudoStatusResponse {
  laudo_id: number;
  mensagem: MobileMesaMessage;
  resumo?: MobileMesaResumo;
  request_id?: string;
  idempotent_replay?: boolean;
}

export interface MobileMesaReviewCommandPayload {
  command:
    | "enviar_para_mesa"
    | "aprovar_no_mobile"
    | "devolver_no_mobile"
    | "reabrir_bloco";
  block_key?: string | null;
  evidence_key?: string | null;
  title?: string | null;
  reason?: string | null;
  summary?: string | null;
  required_action?: string | null;
  failure_reasons?: string[];
}

export interface MobileMesaReviewDecisionResponse extends MobileLaudoStatusResponse {
  ok: boolean;
  command: string;
  message: string;
  review_mode_final?: string | null;
}

export interface MobileMesaResumoResponse extends MobileLaudoStatusResponse {
  laudo_id: number;
  resumo: MobileMesaResumo;
}

export interface MobileMesaFeedItem extends MobileMesaResumoResponse {}

export interface MobileMesaFeedResponse {
  cursor_atual: string;
  laudo_ids: number[];
  itens: MobileMesaFeedItem[];
}

export interface MobileGuidedInspectionDraftUpdateResponse {
  ok: boolean;
  laudo_id: number;
  guided_inspection_draft: MobileGuidedInspectionDraftPayload | null;
}

export interface MobileChatSendResult {
  laudoId: number | null;
  laudoCard: MobileLaudoCard | null;
  assistantText: string;
  modo: MobileChatMode | string;
  citacoes: Array<Record<string, unknown>>;
  confiancaIa: Record<string, unknown> | null;
  events: Record<string, unknown>[];
}

export interface MobileDocumentUploadResponse {
  texto: string;
  chars: number;
  nome: string;
  truncado: boolean;
}
