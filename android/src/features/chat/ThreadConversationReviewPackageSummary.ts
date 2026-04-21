import type {
  MobileLifecycleTransition,
  MobileReviewPackage,
  MobileSurfaceAction,
} from "../../types/mobile";
import {
  descricaoCaseLifecycle,
  normalizarCaseLifecycleStatus,
  resumirCaseSurfaceActions,
  resumirLifecycleTransitions,
  rotuloCaseLifecycle,
  rotuloCaseOwnerRole,
} from "./caseLifecycle";
import {
  lerArrayRegistros,
  lerBooleanOuNull,
  lerNumero,
  lerRegistro,
  lerTexto,
  resumirIntegridadePdfOficial,
} from "./ThreadConversationReviewCardUtils";

function rotuloModoRevisao(reviewMode: string | null | undefined): string {
  const value = String(reviewMode || "")
    .trim()
    .toLowerCase();
  if (value === "mesa_required") {
    return "Mesa obrigatória";
  }
  if (value === "mobile_review_allowed") {
    return "Mobile com revisão";
  }
  if (value === "mobile_autonomous") {
    return "Mobile autônomo";
  }
  return value ? value.replace(/_/g, " ") : "Revisão governada";
}

export function rotuloStatusBloco(reviewStatus: string): string {
  if (reviewStatus === "returned") {
    return "Refazer";
  }
  if (reviewStatus === "attention") {
    return "Atenção";
  }
  if (reviewStatus === "partial") {
    return "Parcial";
  }
  return "Pronto";
}

export function obterTomStatusBloco(
  reviewStatus: string,
): "danger" | "accent" | "success" {
  if (reviewStatus === "returned") {
    return "danger";
  }
  if (reviewStatus === "attention" || reviewStatus === "partial") {
    return "accent";
  }
  return "success";
}

export function rotuloTipoDiffHistorico(changeType: string): string {
  if (changeType === "added") {
    return "novo";
  }
  if (changeType === "removed") {
    return "removido";
  }
  return "alterado";
}

function deduplicarRazoesFalha(items: string[]): string[] {
  const dedup = new Set<string>();
  items.forEach((item) => {
    const normalized = String(item || "")
      .trim()
      .replace(/\s+/g, " ");
    if (normalized) {
      dedup.add(normalized);
    }
  });
  return Array.from(dedup);
}

export type ReviewPackageCaseContext =
  | {
      caseLifecycleStatus?: string;
      activeOwnerRole?: string;
      allowedNextLifecycleStatuses?: string[];
      allowedLifecycleTransitions?: MobileLifecycleTransition[];
      allowedSurfaceActions?: MobileSurfaceAction[];
    }
  | undefined;

export function buildThreadConversationReviewPackageSummary(
  reviewPackage: MobileReviewPackage | null | undefined,
  caseContext?: ReviewPackageCaseContext,
) {
  if (!reviewPackage) {
    return null;
  }

  const lifecycleStatus =
    normalizarCaseLifecycleStatus(caseContext?.caseLifecycleStatus) ||
    "analise_livre";
  const ownerRoleRaw = String(caseContext?.activeOwnerRole || "")
    .trim()
    .toLowerCase();
  const ownerRole =
    ownerRoleRaw === "mesa" || ownerRoleRaw === "none"
      ? ownerRoleRaw
      : "inspetor";
  const ownerLabel = rotuloCaseOwnerRole(ownerRole);
  const allowedLifecycleTransitions = Array.isArray(
    caseContext?.allowedLifecycleTransitions,
  )
    ? caseContext.allowedLifecycleTransitions
    : [];
  const nextLifecycleSummary = allowedLifecycleTransitions.length
    ? resumirLifecycleTransitions(allowedLifecycleTransitions)
    : Array.isArray(caseContext?.allowedNextLifecycleStatuses)
      ? caseContext.allowedNextLifecycleStatuses
          .map((item) => {
            const lifecycle = normalizarCaseLifecycleStatus(item);
            return lifecycle ? rotuloCaseLifecycle(lifecycle) : "";
          })
          .filter(Boolean)
          .slice(0, 3)
          .join(" · ")
      : "";
  const allowedSurfaceActions = Array.isArray(
    caseContext?.allowedSurfaceActions,
  )
    ? caseContext.allowedSurfaceActions
    : [];
  const surfaceActionSummary = resumirCaseSurfaceActions(allowedSurfaceActions);

  const coverageMap = lerRegistro(reviewPackage.coverage_map);
  const revisaoPorBloco = lerRegistro(reviewPackage.revisao_por_bloco);
  const memoriaOperacional = lerRegistro(
    reviewPackage.memoria_operacional_familia,
  );
  const tenantEntitlements = lerRegistro(reviewPackage.tenant_entitlements);
  const inspectionHistory = lerRegistro(reviewPackage.inspection_history);
  const inspectionDiff = lerRegistro(inspectionHistory?.diff);
  const humanOverrideEnvelope = lerRegistro(
    reviewPackage.human_override_summary,
  );
  const humanOverrideLatest =
    lerRegistro(humanOverrideEnvelope?.latest) ||
    lerRegistro(inspectionHistory?.human_override_summary);
  const verification = lerRegistro(reviewPackage.public_verification);
  const anexoPack = lerRegistro(reviewPackage.anexo_pack);
  const emissaoOficial = lerRegistro(reviewPackage.emissao_oficial);
  const emissaoAtual = lerRegistro(emissaoOficial?.current_issue);
  const issueIntegrity = resumirIntegridadePdfOficial(
    emissaoOficial,
    emissaoAtual,
  );
  const redFlags = lerArrayRegistros(reviewPackage.red_flags).map((item) => ({
    code: lerTexto(item.code),
    title: lerTexto(item.title, "Red flag"),
    message: lerTexto(item.message),
    severity: lerTexto(item.severity, "high"),
  }));
  const historyItems = lerArrayRegistros(
    reviewPackage.historico_refazer_inspetor,
  );
  const baseDiffHighlights = lerArrayRegistros(inspectionDiff?.highlights).map(
    (item) => ({
      label: lerTexto(item.label, "Campo"),
      changeType: lerTexto(item.change_type, "changed"),
      previousValue: lerTexto(item.previous_value, "vazio"),
      currentValue: lerTexto(item.current_value, "vazio"),
    }),
  );
  const identityDiffHighlights = lerArrayRegistros(
    inspectionDiff?.identity_highlights,
  ).map((item) => ({
    label: lerTexto(item.label, "Campo"),
    changeType: lerTexto(item.change_type, "changed"),
    previousValue: lerTexto(item.previous_value, "vazio"),
    currentValue: lerTexto(item.current_value, "vazio"),
  }));
  const diffBlockHighlights = lerArrayRegistros(
    inspectionDiff?.block_highlights,
  ).map((item) => ({
    title: lerTexto(item.title, "Bloco"),
    summary: lerTexto(item.summary),
    totalChanges: lerNumero(item.total_changes),
    fields: lerArrayRegistros(item.fields)
      .map((field) => ({
        label: lerTexto(field.label, "Campo"),
        changeType: lerTexto(field.change_type, "changed"),
        previousValue: lerTexto(field.previous_value, "vazio"),
        currentValue: lerTexto(field.current_value, "vazio"),
      }))
      .slice(0, 2),
  }));
  const officialIssueTrail = lerArrayRegistros(emissaoOficial?.audit_trail).map(
    (item) => ({
      title: lerTexto(item.title, "Evento documental"),
      statusLabel: lerTexto(item.status_label, "Rastreável"),
      summary: lerTexto(item.summary),
    }),
  );
  const blockItems = lerArrayRegistros(revisaoPorBloco?.items).map((item) => ({
    blockKey: lerTexto(item.block_key),
    title: lerTexto(item.title, "Bloco"),
    reviewStatus: lerTexto(item.review_status, "ready"),
    recommendedAction: lerTexto(item.recommended_action),
  }));

  let entitlementMessage = "";
  if (tenantEntitlements) {
    if (Boolean(tenantEntitlements.mobile_autonomous_allowed)) {
      entitlementMessage =
        "Tenant habilitado para autonomia mobile nesta familia.";
    } else if (Boolean(tenantEntitlements.mobile_review_allowed)) {
      entitlementMessage =
        "Tenant habilitado para revisão mobile governada, com escalonamento opcional.";
    } else if (tenantEntitlements.family_release_active === false) {
      entitlementMessage =
        "Liberação da família inativa para este tenant; o caso sobe para Mesa.";
    } else {
      entitlementMessage =
        "Política do tenant mantém decisão final governada pela Mesa.";
    }
  }

  return {
    modeLabel: rotuloModoRevisao(reviewPackage.review_mode),
    lifecycleLabel: rotuloCaseLifecycle(lifecycleStatus),
    lifecycleDescription: descricaoCaseLifecycle(lifecycleStatus),
    ownerLabel,
    nextLifecycleSummary,
    surfaceActionSummary,
    surfaceActionsKnown: allowedSurfaceActions.length > 0,
    allowedSurfaceActions,
    reviewRequired: lerBooleanOuNull(reviewPackage.review_required),
    blockerCount: Array.isArray(reviewPackage.document_blockers)
      ? reviewPackage.document_blockers.length
      : 0,
    totalRequired: lerNumero(coverageMap?.total_required),
    totalAccepted: lerNumero(coverageMap?.total_accepted),
    totalMissing: lerNumero(coverageMap?.total_missing),
    totalIrregular: lerNumero(coverageMap?.total_irregular),
    returnedBlocks: lerNumero(revisaoPorBloco?.returned_blocks),
    attentionBlocks: lerNumero(revisaoPorBloco?.attention_blocks),
    historyCount: historyItems.length,
    approvedCount: lerNumero(memoriaOperacional?.approved_snapshot_count),
    redFlagCount: redFlags.length,
    entitlementMessage,
    humanOverrideReason: lerTexto(humanOverrideLatest?.reason),
    humanOverrideActor: lerTexto(humanOverrideLatest?.actor_name),
    humanOverrideWhen: lerTexto(humanOverrideLatest?.applied_at),
    humanOverrideCount: humanOverrideEnvelope
      ? lerNumero(humanOverrideEnvelope?.count)
      : 0,
    topRedFlags: redFlags.slice(0, 3),
    inspectionHistorySummary: lerTexto(
      lerRegistro(inspectionHistory?.diff)?.summary,
    ),
    inspectionHistorySource: [
      lerTexto(inspectionHistory?.source_codigo_hash),
      lerTexto(inspectionHistory?.matched_by),
    ]
      .filter(Boolean)
      .join(" · "),
    verificationLabel: lerTexto(verification?.verification_url),
    verificationQrUri: lerTexto(verification?.qr_image_data_uri),
    annexSummary: anexoPack
      ? `${lerNumero(anexoPack.total_present)}/${lerNumero(anexoPack.total_items)} anexos prontos`
      : "",
    annexMissingItems: Array.isArray(anexoPack?.missing_items)
      ? anexoPack.missing_items.filter(
          (item): item is string =>
            typeof item === "string" && item.trim().length > 0,
        )
      : [],
    officialIssueLabel: lerTexto(
      emissaoOficial?.issue_status_label,
      "Emissão oficial governada",
    ),
    currentOfficialIssueNumber: lerTexto(emissaoAtual?.issue_number),
    currentOfficialIssueStateLabel: lerTexto(
      emissaoAtual?.issue_state_label,
      "Emitido",
    ),
    currentOfficialIssueIssuedAt: lerTexto(emissaoAtual?.issued_at),
    officialIssueBlockers: lerArrayRegistros(emissaoOficial?.blockers).map(
      (item) => lerTexto(item.title || item.message, "Bloqueio de emissão"),
    ),
    eligibleSignatoryCount: lerNumero(emissaoOficial?.eligible_signatory_count),
    signatoryStatusLabel: lerTexto(
      emissaoOficial?.signature_status_label,
      "Sem leitura de assinatura",
    ),
    primaryPdfDiverged: issueIntegrity.diverged,
    primaryPdfIntegrityTitle: issueIntegrity.title,
    primaryPdfIntegritySummary: issueIntegrity.summary,
    primaryPdfIntegrityVersionDetail: issueIntegrity.versionDetail,
    officialIssueTrail: officialIssueTrail.slice(0, 4),
    allowedDecisions: Array.isArray(reviewPackage.allowed_decisions)
      ? reviewPackage.allowed_decisions.filter(
          (item): item is string =>
            typeof item === "string" && item.trim().length > 0,
        )
      : [],
    supportsBlockReopen: Boolean(reviewPackage.supports_block_reopen),
    diffHighlights: (identityDiffHighlights.length
      ? identityDiffHighlights
      : baseDiffHighlights
    ).slice(0, 3),
    diffBlockHighlights: diffBlockHighlights.slice(0, 2),
    highlightedBlocks: blockItems
      .filter(
        (item) =>
          item.reviewStatus === "returned" || item.reviewStatus === "attention",
      )
      .slice(0, 3),
  };
}

export type ThreadConversationReviewPackageSummary = NonNullable<
  ReturnType<typeof buildThreadConversationReviewPackageSummary>
>;

export function buildThreadConversationReviewDecisionContext(summary: {
  highlightedBlocks: Array<{
    blockKey: string;
    title: string;
    reviewStatus: string;
    recommendedAction: string;
  }>;
  topRedFlags: Array<{
    code: string;
    title: string;
    message: string;
    severity: string;
  }>;
}) {
  const prioritizedBlock =
    summary.highlightedBlocks.find(
      (item) => item.reviewStatus === "returned",
    ) ||
    summary.highlightedBlocks[0] ||
    null;
  const failureReasons = deduplicarRazoesFalha([
    ...summary.topRedFlags
      .map((item) => String(item.code || "").trim())
      .filter(Boolean),
    ...summary.topRedFlags
      .map((item) => String(item.title || "").trim())
      .filter(Boolean),
  ]).slice(0, 3);
  const requiredAction =
    String(prioritizedBlock?.recommendedAction || "").trim() ||
    String(summary.topRedFlags[0]?.message || "").trim() ||
    String(summary.topRedFlags[0]?.title || "").trim() ||
    "Revisar os pontos sinalizados antes da conclusão.";
  const title =
    String(prioritizedBlock?.title || "").trim() ||
    (summary.topRedFlags.length ? "Revisão governada" : "Ajuste operacional");

  return {
    blockKey: prioritizedBlock?.blockKey || null,
    title,
    requiredAction,
    failureReasons,
    reason:
      requiredAction ||
      "Caso devolvido para ajuste na revisão mobile antes da conclusão.",
    summary: prioritizedBlock
      ? `A revisão mobile devolveu o bloco ${title} para ajuste antes da conclusão.`
      : "A revisão mobile devolveu o caso para ajuste antes da conclusão.",
  };
}

export type ThreadConversationReviewDecisionContext = ReturnType<
  typeof buildThreadConversationReviewDecisionContext
>;
