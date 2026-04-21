import type {
  MobileReportPackBlockSummary,
  MobileReportPackDraftSummary,
  MobileReportPackSlotSummary,
} from "./reportPackHelperTypes";
import {
  buildBlockSummary,
  buildDocumentSectionSummaries,
  buildExecutiveSummaries,
  buildFlowSummaries,
  buildPolicySlotSummary,
  buildRuntimeSlotSummary,
  resolveRuntimeSlot,
} from "./reportPackSummaryBuilders";
import {
  labelForValidationMode,
  normalizeAnalysisBasisSummary,
  normalizePreLaudoDocument,
  normalizePreLaudoMinimumEvidence,
  readArrayRecords,
  readBoolean,
  readNumber,
  readRecord,
  readStringArray,
  readText,
  pickFirstText,
} from "./reportPackHelperReaders";

export type {
  MobileReportPackBlockSummary,
  MobileReportPackDraftSummary,
  MobileReportPackExecutiveSummary,
  MobileReportPackFlowSummary,
  MobileReportPackSectionSummary,
  MobileReportPackSlotSummary,
  ReportPackBlockStatus,
} from "./reportPackHelperTypes";

export function buildReportPackDraftSummary(
  value: unknown,
): MobileReportPackDraftSummary | null {
  const draft = readRecord(value);
  if (!draft) {
    return null;
  }

  const qualityGates = readRecord(draft.quality_gates);
  const preLaudoOutline = readRecord(draft.pre_laudo_outline);
  const preLaudoDocument = normalizePreLaudoDocument(draft.pre_laudo_document);
  const guidedContext = readRecord(draft.guided_context);
  const evidenceSummary = readRecord(draft.evidence_summary);
  const structuredDataCandidate = readRecord(draft.structured_data_candidate);
  const candidateCaseContext = readRecord(
    structuredDataCandidate?.case_context,
  );
  const candidateIdentification = readRecord(
    structuredDataCandidate?.identificacao,
  );
  const candidateObject = readRecord(structuredDataCandidate?.objeto_inspecao);
  const items = readArrayRecords(draft.items);
  const imageSlots = readArrayRecords(draft.image_slots);
  const missingEvidenceMessages = readArrayRecords(
    qualityGates?.missing_evidence,
  )
    .map((item) => readText(item.message))
    .filter(Boolean)
    .slice(0, 4);
  const nextQuestions = readStringArray(
    preLaudoDocument?.next_questions ?? preLaudoOutline?.next_questions,
  ).slice(0, 4);

  const checklistIds = Array.isArray(guidedContext?.checklist_ids)
    ? guidedContext.checklist_ids.map((item) => readText(item)).filter(Boolean)
    : [];
  const completedStepIds = Array.isArray(guidedContext?.completed_step_ids)
    ? guidedContext.completed_step_ids
        .map((item) => readText(item))
        .filter(Boolean)
    : [];

  const checklistComplete = readBoolean(qualityGates?.checklist_complete);
  const requiredImageSlotsComplete = readBoolean(
    qualityGates?.required_image_slots_complete,
  );
  const criticalItemsComplete = readBoolean(
    qualityGates?.critical_items_complete,
  );
  const requiresNormativeCuration = Boolean(
    qualityGates?.requires_normative_curation,
  );
  const autonomyReady = Boolean(qualityGates?.autonomy_ready);
  const finalValidationMode = readText(qualityGates?.final_validation_mode);
  const readyForStructuredForm = Boolean(
    preLaudoOutline?.ready_for_structured_form,
  );
  const readyForFinalization =
    Boolean(preLaudoOutline?.ready_for_finalization) || autonomyReady;
  const assetLabel = pickFirstText(
    guidedContext?.asset_label,
    guidedContext?.asset_name,
    guidedContext?.ativo_label,
    guidedContext?.ativo_nome,
    guidedContext?.objeto_label,
    guidedContext?.objeto_nome,
    candidateIdentification?.ativo_nome,
    candidateIdentification?.equipamento_nome,
    candidateObject?.nome,
    candidateObject?.identificacao,
  );
  const locationLabel = pickFirstText(
    guidedContext?.location_label,
    guidedContext?.local_label,
    guidedContext?.local_inspecao,
    guidedContext?.area_label,
    guidedContext?.area_nome,
    candidateCaseContext?.local_inspecao,
    candidateCaseContext?.unidade_nome,
    candidateCaseContext?.area,
    candidateIdentification?.localizacao,
  );
  const inspectionObjective = pickFirstText(
    guidedContext?.inspection_objective,
    guidedContext?.objective,
    guidedContext?.objetivo,
    candidateCaseContext?.objetivo,
    candidateCaseContext?.motivo,
    candidateObject?.escopo,
  );
  const inspectionContextLabel = [assetLabel, locationLabel]
    .filter(Boolean)
    .join(" · ");
  const inspectionContextDetail = inspectionObjective
    ? inspectionObjective
    : inspectionContextLabel
      ? "Contexto principal do ativo reaproveitado do fluxo guiado."
      : "";

  const itemPendingCount = items.filter((item) => {
    const verdict = readText(item.veredito_ia_normativo).toLowerCase();
    return (
      verdict === "pendente" ||
      readStringArray(item.missing_evidence).length > 0
    );
  }).length;
  const itemAttentionCount = items.filter((item) => {
    const verdict = readText(item.veredito_ia_normativo).toLowerCase();
    const approved = item.approved_for_emission === true;
    return (
      verdict !== "pendente" &&
      !approved &&
      !readStringArray(item.missing_evidence).length
    );
  }).length;
  const itemReadyCount = Math.max(
    items.length - itemPendingCount - itemAttentionCount,
    0,
  );

  const documentFlowEntries = buildFlowSummaries(
    preLaudoDocument?.document_flow || [],
  );
  const executiveSections = buildExecutiveSummaries(
    preLaudoDocument?.executive_sections || [],
  );
  const documentSections = buildDocumentSectionSummaries(
    preLaudoDocument?.document_sections || [],
  );
  const highlightedDocumentSections = (
    preLaudoDocument?.highlighted_sections?.length
      ? buildDocumentSectionSummaries(preLaudoDocument.highlighted_sections)
      : documentSections.filter((item) => item.status !== "ready")
  ).slice(0, 4);

  const requiredPolicySlots = preLaudoDocument?.required_slots || [];
  const optionalPolicySlots = preLaudoDocument?.optional_slots || [];
  const requiredEvidenceSlots = requiredPolicySlots.length
    ? requiredPolicySlots.map((slot, index) =>
        buildPolicySlotSummary(
          slot,
          resolveRuntimeSlot(slot, imageSlots, index),
          index,
        ),
      )
    : imageSlots
        .map((item, index) => buildRuntimeSlotSummary(item, index))
        .filter((item): item is MobileReportPackSlotSummary => item !== null);
  const optionalEvidenceSlots = optionalPolicySlots.map((slot, index) =>
    buildPolicySlotSummary(slot, null, index),
  );

  const blockSummaries: MobileReportPackBlockSummary[] = [];

  if (documentFlowEntries.length) {
    const readyFlowCount = documentFlowEntries.filter(
      (item) => item.status === "ready",
    ).length;
    const flowStatus =
      readyFlowCount === documentFlowEntries.length
        ? "ready"
        : readyFlowCount > 0
          ? "attention"
          : "pending";
    blockSummaries.push(
      buildBlockSummary(
        "document_flow",
        "Fluxo do documento",
        flowStatus,
        `${readyFlowCount}/${documentFlowEntries.length} etapas canônicas do catálogo prontas.`,
      ),
    );
  }

  if (checklistIds.length || checklistComplete !== null) {
    const totalChecklist = checklistIds.length;
    const checklistSummary =
      totalChecklist > 0
        ? `${Math.min(completedStepIds.length, totalChecklist)}/${totalChecklist} etapas confirmadas.`
        : checklistComplete
          ? "Checklist guiado coerente para o pre-laudo."
          : "Checklist guiado ainda precisa ser concluido.";
    blockSummaries.push(
      buildBlockSummary(
        "guided_checklist",
        "Checklist guiado",
        checklistComplete === true ? "ready" : "pending",
        checklistSummary,
      ),
    );
  }

  if (requiredEvidenceSlots.length || requiredImageSlotsComplete !== null) {
    const resolvedRequiredSlots = requiredEvidenceSlots.filter(
      (item) => item.resolved,
    ).length;
    const imageStatus =
      requiredImageSlotsComplete === true
        ? "ready"
        : resolvedRequiredSlots > 0
          ? "attention"
          : "pending";
    const imageSummary = requiredEvidenceSlots.length
      ? `${resolvedRequiredSlots}/${requiredEvidenceSlots.length} slots obrigatórios resolvidos.`
      : requiredImageSlotsComplete
        ? "Evidencias visuais suficientes para o pre-laudo."
        : "Ainda faltam evidencias visuais obrigatorias.";
    blockSummaries.push(
      buildBlockSummary(
        "image_slots",
        "Fotos obrigatorias",
        imageStatus,
        imageSummary,
      ),
    );
  }

  if (items.length || criticalItemsComplete !== null) {
    const itemStatus =
      itemPendingCount > 0 || criticalItemsComplete === false
        ? "pending"
        : itemAttentionCount > 0
          ? "attention"
          : "ready";
    const itemSummary = items.length
      ? `${itemReadyCount}/${items.length} itens aptos; ${itemPendingCount} pendentes; ${itemAttentionCount} em atencao.`
      : criticalItemsComplete
        ? "Itens criticos consolidados para o pre-laudo."
        : "Itens criticos ainda nao foram consolidados.";
    blockSummaries.push(
      buildBlockSummary(
        "critical_items",
        "Itens criticos",
        itemStatus,
        itemSummary,
      ),
    );
  }

  if (draft.modeled !== undefined || structuredDataCandidate) {
    blockSummaries.push(
      buildBlockSummary(
        "structured_candidate",
        "Estrutura do pre-laudo",
        structuredDataCandidate ? "ready" : "pending",
        structuredDataCandidate
          ? "Payload estruturado pronto para consolidacao interna."
          : "O payload estruturado ainda nao foi materializado.",
      ),
    );
  }

  if (
    requiresNormativeCuration ||
    readNumber(qualityGates?.max_conflict_score) > 0
  ) {
    blockSummaries.push(
      buildBlockSummary(
        "normative_curation",
        "Curadoria normativa",
        requiresNormativeCuration ? "attention" : "ready",
        requiresNormativeCuration
          ? "Ha sinais de conflito normativo que exigem validacao humana."
          : "Sem conflito normativo relevante no pre-laudo.",
      ),
    );
  }

  for (const section of documentSections.slice(0, 6)) {
    blockSummaries.push(
      buildBlockSummary(
        `document_section_${section.key}`,
        section.title,
        section.status,
        section.summary,
      ),
    );
  }

  const readyBlocks = blockSummaries.filter(
    (item) => item.status === "ready",
  ).length;
  const attentionBlocks = blockSummaries.filter(
    (item) => item.status === "attention",
  ).length;
  const pendingBlocks = blockSummaries.filter(
    (item) => item.status === "pending",
  ).length;
  const totalBlocks = blockSummaries.length;
  const highlightedBlocks = blockSummaries
    .filter((item) => item.status !== "ready")
    .slice(0, 4);

  let readinessLabel = "Pre-laudo em montagem";
  if (readyForFinalization) {
    readinessLabel = "Pronto para validar";
  } else if (pendingBlocks === 0 && attentionBlocks === 0) {
    readinessLabel = "Pronto para handoff";
  } else if (pendingBlocks === 0) {
    readinessLabel = "Pronto para mesa";
  }

  const readinessDetail =
    highlightedDocumentSections.length > 0
      ? `${highlightedDocumentSections
          .map((item) => item.title)
          .slice(0, 3)
          .join(" · ")} precisam de acompanhamento.`
      : highlightedBlocks.length > 0
        ? `${highlightedBlocks
            .map((item) => item.title)
            .slice(0, 3)
            .join(" · ")} precisam de acompanhamento.`
        : `Modo final previsto: ${labelForValidationMode(finalValidationMode)}.`;

  return {
    modeled: draft.modeled !== false,
    familyKey: readText(preLaudoDocument?.family_key) || readText(draft.family),
    familyLabel: readText(preLaudoDocument?.family_label),
    templateKey:
      readText(preLaudoDocument?.template_key) || readText(draft.template_key),
    templateLabel:
      readText(preLaudoDocument?.template_label) ||
      readText(draft.template_label) ||
      readText(draft.template_key) ||
      "Pre-laudo incremental",
    assetLabel,
    locationLabel,
    inspectionObjective,
    inspectionContextLabel,
    inspectionContextDetail,
    finalValidationMode,
    finalValidationModeLabel: labelForValidationMode(finalValidationMode),
    autonomyReady,
    readyForStructuredForm,
    readyForFinalization,
    readinessLabel,
    readinessDetail,
    totalBlocks,
    readyBlocks,
    attentionBlocks,
    pendingBlocks,
    evidenceCount: readNumber(evidenceSummary?.evidence_count),
    imageCount: readNumber(evidenceSummary?.image_count),
    textCount: readNumber(evidenceSummary?.text_count),
    missingEvidenceCount: missingEvidenceMessages.length,
    maxConflictScore: readNumber(qualityGates?.max_conflict_score),
    minimumEvidence: normalizePreLaudoMinimumEvidence(
      preLaudoDocument?.minimum_evidence,
    ),
    checklistGroupTitles: (preLaudoDocument?.checklist_groups || [])
      .map((item) => readText(item.title))
      .filter(Boolean)
      .slice(0, 4),
    reviewRequired: (preLaudoDocument?.review_required || [])
      .filter(Boolean)
      .slice(0, 4),
    exampleAvailable: Boolean(preLaudoDocument?.example_available),
    highlightedBlocks,
    blockSummaries,
    documentFlowEntries,
    executiveSections,
    documentSections,
    highlightedDocumentSections,
    requiredEvidenceSlots,
    optionalEvidenceSlots,
    analysisBasisSummary:
      preLaudoDocument?.analysis_basis_summary ||
      normalizeAnalysisBasisSummary(draft.analysis_basis),
    missingEvidenceMessages,
    nextQuestions,
  };
}
