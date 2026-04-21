import { Image, Pressable, Text, View } from "react-native";

import type { MobileMesaReviewCommandPayload } from "../../types/mobile";
import { styles } from "../InspectorMobileApp.styles";
import {
  obterTomStatusBloco,
  rotuloStatusBloco,
  rotuloTipoDiffHistorico,
  type ThreadConversationReviewDecisionContext,
  type ThreadConversationReviewPackageSummary,
} from "./ThreadConversationReviewPackageSummary";

type ReviewCommandHandler =
  | ((payload: MobileMesaReviewCommandPayload) => Promise<void>)
  | undefined;

function ReviewPackageActionButton(props: {
  disabled: boolean;
  onPress: () => void;
  testID: string;
  tone: "success" | "accent" | "danger";
  label: string;
}) {
  const toneStyle =
    props.tone === "danger"
      ? styles.threadReviewActionButtonDanger
      : props.tone === "accent"
        ? styles.threadReviewActionButtonAccent
        : styles.threadReviewActionButtonSuccess;
  const toneTextStyle =
    props.tone === "danger"
      ? styles.threadReviewActionButtonTextDanger
      : props.tone === "accent"
        ? styles.threadReviewActionButtonTextAccent
        : styles.threadReviewActionButtonTextSuccess;

  return (
    <Pressable
      accessibilityRole="button"
      disabled={props.disabled}
      onPress={props.onPress}
      style={[
        styles.threadReviewActionButton,
        toneStyle,
        props.disabled ? styles.threadReviewActionButtonDisabled : null,
      ]}
      testID={props.testID}
    >
      <Text style={[styles.threadReviewActionButtonText, toneTextStyle]}>
        {props.label}
      </Text>
    </Pressable>
  );
}

function ReviewPackageStatusBadge(props: {
  label: string;
  tone: "success" | "accent" | "danger";
}) {
  const toneStyle =
    props.tone === "danger"
      ? styles.threadReviewStatusBadgeDanger
      : props.tone === "accent"
        ? styles.threadReviewStatusBadgeAccent
        : styles.threadReviewStatusBadgeSuccess;
  const toneTextStyle =
    props.tone === "danger"
      ? styles.threadReviewStatusBadgeTextDanger
      : props.tone === "accent"
        ? styles.threadReviewStatusBadgeTextAccent
        : styles.threadReviewStatusBadgeTextSuccess;

  return (
    <View style={[styles.threadReviewStatusBadge, toneStyle]}>
      <Text style={[styles.threadReviewStatusBadgeText, toneTextStyle]}>
        {props.label}
      </Text>
    </View>
  );
}

export function ThreadConversationReviewVerificationSection(props: {
  summary: ThreadConversationReviewPackageSummary;
}) {
  const { summary } = props;

  if (!summary.verificationLabel) {
    return null;
  }

  return (
    <View style={styles.threadReviewVerificationShell}>
      {summary.verificationQrUri ? (
        <Image
          source={{ uri: summary.verificationQrUri }}
          style={styles.threadReviewVerificationQr}
          testID="mesa-review-verification-qr"
        />
      ) : null}
      <View style={styles.threadReviewVerificationCopy}>
        <Text style={styles.threadReviewEntitlement}>Verificação pública</Text>
        <Text style={styles.threadReviewFootnote}>
          {summary.verificationLabel}
        </Text>
      </View>
    </View>
  );
}

export function ThreadConversationReviewOfficialIssueSection(props: {
  summary: ThreadConversationReviewPackageSummary;
}) {
  const { summary } = props;

  if (!summary.officialIssueLabel && !summary.annexSummary) {
    return null;
  }

  return (
    <View style={styles.threadReviewList}>
      <Text style={styles.threadReviewSectionTitle}>Emissão oficial</Text>
      <View style={styles.threadReviewListItem}>
        <View style={styles.threadReviewListCopy}>
          <Text style={styles.threadReviewListTitle}>
            {summary.officialIssueLabel}
          </Text>
          {summary.currentOfficialIssueNumber ? (
            <Text style={styles.threadReviewListText}>
              {`${summary.currentOfficialIssueNumber} · ${summary.currentOfficialIssueStateLabel}${
                summary.currentOfficialIssueIssuedAt
                  ? ` · ${summary.currentOfficialIssueIssuedAt}`
                  : ""
              }`}
            </Text>
          ) : null}
          {summary.annexSummary ? (
            <Text style={styles.threadReviewListText}>
              {summary.annexSummary}
            </Text>
          ) : null}
          <Text style={styles.threadReviewListText}>
            {summary.eligibleSignatoryCount > 0
              ? `${summary.eligibleSignatoryCount} signatário(s) elegível(is). ${summary.signatoryStatusLabel}`
              : summary.signatoryStatusLabel}
          </Text>
        </View>
      </View>
      {summary.primaryPdfIntegritySummary ? (
        <View style={styles.threadReviewWarningItem}>
          <Text style={styles.threadReviewWarningTitle}>
            {summary.primaryPdfIntegrityTitle}
          </Text>
          <Text style={styles.threadReviewWarningText}>
            {summary.primaryPdfIntegritySummary}
            {summary.primaryPdfIntegrityVersionDetail
              ? ` ${summary.primaryPdfIntegrityVersionDetail}.`
              : ""}
          </Text>
        </View>
      ) : null}
      {summary.officialIssueBlockers.slice(0, 3).map((item) => (
        <View key={item} style={styles.threadReviewWarningItem}>
          <Text style={styles.threadReviewWarningTitle}>{item}</Text>
        </View>
      ))}
      {summary.annexMissingItems.slice(0, 3).map((item) => (
        <Text key={item} style={styles.threadReviewFootnote}>
          Anexo pendente: {item}
        </Text>
      ))}
      {summary.officialIssueTrail.map((item) => (
        <View
          key={`${item.title}-${item.statusLabel}`}
          style={styles.threadReviewListItem}
        >
          <View style={styles.threadReviewListCopy}>
            <Text style={styles.threadReviewListTitle}>{item.title}</Text>
            <Text style={styles.threadReviewListText}>{item.statusLabel}</Text>
            {item.summary ? (
              <Text style={styles.threadReviewListText}>{item.summary}</Text>
            ) : null}
          </View>
        </View>
      ))}
    </View>
  );
}

export function ThreadConversationReviewDiffSection(props: {
  summary: ThreadConversationReviewPackageSummary;
}) {
  const { summary } = props;

  if (!summary.diffHighlights.length) {
    return null;
  }

  return (
    <View style={styles.threadReviewList}>
      <Text style={styles.threadReviewSectionTitle}>Diff entre emissões</Text>
      {summary.diffBlockHighlights.map((item) => (
        <View
          key={`${item.title}-${item.totalChanges}`}
          style={styles.threadReviewListItem}
        >
          <View style={styles.threadReviewListCopy}>
            <Text style={styles.threadReviewListTitle}>{item.title}</Text>
            <Text style={styles.threadReviewListText}>
              {item.totalChanges > 0
                ? `${item.totalChanges} delta(s) estáveis neste bloco.`
                : "Sem delta consolidado neste bloco."}
            </Text>
            {item.summary ? (
              <Text style={styles.threadReviewListText}>{item.summary}</Text>
            ) : null}
            {item.fields.map((field) => (
              <Text
                key={`${item.title}-${field.label}-${field.changeType}`}
                style={styles.threadReviewFootnote}
              >
                {field.label}: {field.previousValue} → {field.currentValue}
              </Text>
            ))}
          </View>
        </View>
      ))}
      {summary.diffHighlights.map((item) => (
        <View
          key={`${item.label}-${item.changeType}`}
          style={styles.threadReviewListItem}
        >
          <ReviewPackageStatusBadge
            label={rotuloTipoDiffHistorico(item.changeType)}
            tone={
              item.changeType === "removed"
                ? "danger"
                : item.changeType === "added"
                  ? "success"
                  : "accent"
            }
          />
          <View style={styles.threadReviewListCopy}>
            <Text style={styles.threadReviewListTitle}>{item.label}</Text>
            <Text style={styles.threadReviewListText}>
              Antes: {item.previousValue}
            </Text>
            <Text style={styles.threadReviewListText}>
              Agora: {item.currentValue}
            </Text>
          </View>
        </View>
      ))}
    </View>
  );
}

export function ThreadConversationReviewRedFlagsSection(props: {
  summary: ThreadConversationReviewPackageSummary;
}) {
  const { summary } = props;

  if (!summary.topRedFlags.length) {
    return null;
  }

  return (
    <View style={styles.threadReviewWarnings}>
      {summary.topRedFlags.map((item) => (
        <View
          key={item.code || item.title}
          style={styles.threadReviewWarningItem}
        >
          <Text style={styles.threadReviewWarningTitle}>{item.title}</Text>
          {item.message ? (
            <Text style={styles.threadReviewWarningText}>{item.message}</Text>
          ) : null}
        </View>
      ))}
    </View>
  );
}

export function ThreadConversationReviewDecisionFocusSection(props: {
  decisionContext: ThreadConversationReviewDecisionContext;
  summary: ThreadConversationReviewPackageSummary;
}) {
  const { decisionContext, summary } = props;

  if (
    !decisionContext.requiredAction ||
    (!summary.highlightedBlocks.length && !summary.topRedFlags.length)
  ) {
    return null;
  }

  return (
    <View style={styles.threadReviewList}>
      <Text style={styles.threadReviewSectionTitle}>Foco da decisão</Text>
      <View style={styles.threadReviewListItem}>
        <View style={styles.threadReviewListCopy}>
          <Text style={styles.threadReviewListTitle}>
            {decisionContext.title}
          </Text>
          <Text style={styles.threadReviewListText}>
            {decisionContext.requiredAction}
          </Text>
          {decisionContext.failureReasons.map((item) => (
            <Text key={item} style={styles.threadReviewFootnote}>
              Sinalização: {item}
            </Text>
          ))}
        </View>
      </View>
    </View>
  );
}

export function ThreadConversationReviewActionsSection(props: {
  decisionContext: ThreadConversationReviewDecisionContext;
  onExecutarComandoRevisaoMobile: ReviewCommandHandler;
  reviewCommandBusy: boolean;
  summary: ThreadConversationReviewPackageSummary;
}) {
  const {
    decisionContext,
    onExecutarComandoRevisaoMobile,
    reviewCommandBusy,
    summary,
  } = props;
  const actionDisabled = reviewCommandBusy || !onExecutarComandoRevisaoMobile;

  if (!summary.allowedDecisions.length) {
    return null;
  }

  return (
    <View style={styles.threadReviewActionsRail}>
      {summary.allowedDecisions.includes("aprovar_no_mobile") &&
      (!summary.surfaceActionsKnown ||
        summary.allowedSurfaceActions.includes("mesa_approve")) ? (
        <ReviewPackageActionButton
          disabled={actionDisabled}
          label="Aprovar no mobile"
          onPress={() => {
            void onExecutarComandoRevisaoMobile?.({
              command: "aprovar_no_mobile",
            });
          }}
          testID="mesa-review-action-approve"
          tone="success"
        />
      ) : null}
      {summary.allowedDecisions.includes("enviar_para_mesa") ? (
        <ReviewPackageActionButton
          disabled={actionDisabled}
          label="Enviar para Mesa"
          onPress={() => {
            void onExecutarComandoRevisaoMobile?.({
              command: "enviar_para_mesa",
            });
          }}
          testID="mesa-review-action-send"
          tone="accent"
        />
      ) : null}
      {summary.allowedDecisions.includes("devolver_no_mobile") &&
      (!summary.surfaceActionsKnown ||
        summary.allowedSurfaceActions.includes("mesa_return")) ? (
        <ReviewPackageActionButton
          disabled={actionDisabled}
          label="Devolver para ajuste"
          onPress={() => {
            void onExecutarComandoRevisaoMobile?.({
              command: "devolver_no_mobile",
              block_key: decisionContext.blockKey,
              title: decisionContext.title,
              reason: decisionContext.reason,
              summary: decisionContext.summary,
              required_action: decisionContext.requiredAction,
              failure_reasons: decisionContext.failureReasons,
            });
          }}
          testID="mesa-review-action-return"
          tone="danger"
        />
      ) : null}
    </View>
  );
}

export function ThreadConversationReviewHighlightedBlocksSection(props: {
  onExecutarComandoRevisaoMobile: ReviewCommandHandler;
  reviewCommandBusy: boolean;
  summary: ThreadConversationReviewPackageSummary;
}) {
  const { onExecutarComandoRevisaoMobile, reviewCommandBusy, summary } = props;
  const actionDisabled = reviewCommandBusy || !onExecutarComandoRevisaoMobile;

  if (!summary.highlightedBlocks.length) {
    return null;
  }

  return (
    <View style={styles.threadReviewList}>
      {summary.highlightedBlocks.map((item) => {
        const tone = obterTomStatusBloco(item.reviewStatus);

        return (
          <View
            key={item.blockKey || item.title}
            style={styles.threadReviewListItem}
          >
            <ReviewPackageStatusBadge
              label={rotuloStatusBloco(item.reviewStatus)}
              tone={tone}
            />
            <View style={styles.threadReviewListCopy}>
              <Text style={styles.threadReviewListTitle}>{item.title}</Text>
              {item.recommendedAction ? (
                <Text style={styles.threadReviewListText}>
                  {item.recommendedAction}
                </Text>
              ) : null}
              {summary.supportsBlockReopen ? (
                <Pressable
                  accessibilityRole="button"
                  disabled={actionDisabled}
                  onPress={() => {
                    void onExecutarComandoRevisaoMobile?.({
                      command: "reabrir_bloco",
                      block_key: item.blockKey,
                      title: item.title,
                      reason:
                        item.recommendedAction ||
                        `Reabrir bloco ${item.title} para revalidacao.`,
                      summary:
                        item.recommendedAction ||
                        `Bloco ${item.title} reaberto na revisão mobile.`,
                    });
                  }}
                  style={[
                    styles.threadReviewInlineAction,
                    actionDisabled
                      ? styles.threadReviewInlineActionDisabled
                      : null,
                  ]}
                  testID={`mesa-review-reopen-block-${item.blockKey || item.title}`}
                >
                  <Text style={styles.threadReviewInlineActionText}>
                    Reabrir bloco
                  </Text>
                </Pressable>
              ) : null}
            </View>
          </View>
        );
      })}
    </View>
  );
}
