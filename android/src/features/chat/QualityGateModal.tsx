import { MaterialCommunityIcons } from "@expo/vector-icons";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";

import type {
  ApiHealthStatus,
  MobileQualityGateResponse,
} from "../../types/mobile";
import { colors } from "../../theme/tokens";
import { modalStyles } from "./QualityGateModal.styles";
import {
  QualityGateCorrectionSection,
  QualityGateGuideSection,
  QualityGateMetricRow,
  QualityGateMissingItemsSection,
  QualityGateOfflineCard,
  QualityGateOverrideSection,
  QualityGateReportPackSection,
  QualityGateSummaryHero,
} from "./QualityGateModalSections";
import {
  QUALITY_GATE_OVERRIDE_MIN_REASON_LENGTH,
  qualityGatePermiteOverride,
} from "./qualityGateHelpers";
import {
  buildQualityGateStatusSummary,
  buildQualityGateSummaryChips,
  resumoNumero,
  rotuloModoValidacao,
} from "./qualityGateModalHelpers";
import { buildReportPackDraftSummary } from "./reportPackHelpers";

interface QualityGateModalProps {
  visible: boolean;
  loading: boolean;
  submitting: boolean;
  statusApi: ApiHealthStatus;
  payload: MobileQualityGateResponse | null;
  reason: string;
  notice: string;
  onClose: () => void;
  onConfirm: () => void;
  onChangeReason: (value: string) => void;
}

export function QualityGateModal({
  visible,
  loading,
  submitting,
  statusApi,
  payload,
  reason,
  notice,
  onClose,
  onConfirm,
  onChangeReason,
}: QualityGateModalProps) {
  const overrideAvailable = qualityGatePermiteOverride(payload);
  const approved = Boolean(payload?.aprovado);
  const reasonRequired = Boolean(
    payload?.human_override_policy?.reason_required,
  );
  const trimmedReason = reason.trim();
  const canConfirm =
    !loading &&
    !submitting &&
    Boolean(payload) &&
    (approved ||
      (overrideAvailable &&
        (!reasonRequired ||
          trimmedReason.length >= QUALITY_GATE_OVERRIDE_MIN_REASON_LENGTH)));
  const primaryLabel = approved
    ? "Finalizar caso"
    : overrideAvailable
      ? "Seguir com exceção"
      : "Voltar ao caso";
  const title = approved
    ? "Checklist pronto para finalizar"
    : "Quality gate do caso";
  const missingItems = payload?.faltantes || [];
  const reportPackSummary = buildReportPackDraftSummary(
    payload?.report_pack_draft,
  );
  const textCount = resumoNumero(payload?.resumo?.textos_campo);
  const evidenceCount = resumoNumero(payload?.resumo?.evidencias);
  const photoCount = resumoNumero(payload?.resumo?.fotos);
  const reviewModeLabel = rotuloModoValidacao(
    reportPackSummary?.finalValidationMode || payload?.review_mode_sugerido,
  );
  const blockingCount = Math.max(
    missingItems.length,
    (reportPackSummary?.pendingBlocks || 0) +
      (reportPackSummary?.missingEvidenceCount || 0),
  );
  const statusSummary = buildQualityGateStatusSummary({
    approved,
    blockingCount,
    overrideAvailable,
  });
  const summaryChips = buildQualityGateSummaryChips({
    blockingCount,
    payloadTemplateName: payload?.template_nome,
    reportPackSummary,
    reviewModeLabel,
  });

  return (
    <Modal
      animationType="slide"
      onRequestClose={onClose}
      transparent
      visible={visible}
    >
      <View style={modalStyles.backdrop}>
        <View style={modalStyles.card}>
          <View style={modalStyles.header}>
            <View style={modalStyles.headerCopy}>
              <Text style={modalStyles.eyebrow}>quality gate</Text>
              <Text style={modalStyles.title}>{title}</Text>
              <Text style={modalStyles.description}>
                {notice.trim() ||
                  payload?.mensagem ||
                  "Valide a trilha do caso antes de concluir a emissão."}
              </Text>
            </View>
            <Pressable onPress={onClose} style={modalStyles.closeButton}>
              <MaterialCommunityIcons
                color={colors.textPrimary}
                name="close"
                size={18}
              />
            </Pressable>
          </View>

          {loading ? (
            <View style={modalStyles.loadingState}>
              <ActivityIndicator color={colors.accent} size="small" />
              <Text style={modalStyles.loadingText}>
                Validando checklist e política do caso...
              </Text>
            </View>
          ) : payload ? (
            <ScrollView contentContainerStyle={modalStyles.scrollContent}>
              <QualityGateSummaryHero
                statusSummary={statusSummary}
                summaryChips={summaryChips}
              />
              <QualityGateMetricRow
                evidenceCount={evidenceCount}
                photoCount={photoCount}
                reportPackSummary={reportPackSummary}
                textCount={textCount}
              />
              <QualityGateReportPackSection
                reportPackSummary={reportPackSummary}
              />
              <QualityGateMissingItemsSection items={missingItems} />
              <QualityGateGuideSection payload={payload} />
              {overrideAvailable ? (
                <QualityGateOverrideSection
                  onChangeReason={onChangeReason}
                  payload={payload}
                  reason={reason}
                  reasonRequired={reasonRequired}
                />
              ) : null}
              {!payload.aprovado && !overrideAvailable ? (
                <QualityGateCorrectionSection />
              ) : null}
              <QualityGateOfflineCard statusApi={statusApi} />
            </ScrollView>
          ) : (
            <View style={modalStyles.emptyState}>
              <Text style={modalStyles.emptyText}>
                Não foi possível carregar o quality gate deste caso agora.
              </Text>
            </View>
          )}

          <View style={modalStyles.footer}>
            <Pressable onPress={onClose} style={modalStyles.secondaryButton}>
              <Text style={modalStyles.secondaryButtonText}>Fechar</Text>
            </Pressable>
            <Pressable
              accessibilityState={{ disabled: !canConfirm }}
              onPress={() => {
                if (!canConfirm) {
                  return;
                }
                onConfirm();
              }}
              style={[
                modalStyles.primaryButton,
                !canConfirm ? modalStyles.primaryButtonDisabled : null,
              ]}
            >
              {submitting ? (
                <ActivityIndicator color={colors.white} size="small" />
              ) : (
                <Text style={modalStyles.primaryButtonText}>
                  {primaryLabel}
                </Text>
              )}
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}
