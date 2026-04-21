import { MaterialCommunityIcons } from "@expo/vector-icons";
import { Text, TextInput, View } from "react-native";

import type {
  ApiHealthStatus,
  MobileQualityGateResponse,
} from "../../types/mobile";
import { colors } from "../../theme/tokens";
import type { MobileReportPackDraftSummary } from "./reportPackHelpers";
import { modalStyles } from "./QualityGateModal.styles";
import type {
  QualityGateStatusSummary,
  QualityGateSummaryChip,
  QualityGateStatusTone,
} from "./qualityGateModalHelpers";
import { QUALITY_GATE_OVERRIDE_MIN_REASON_LENGTH } from "./qualityGateHelpers";

function heroToneStyle(tone: QualityGateStatusTone) {
  if (tone === "success") {
    return modalStyles.summaryHeroSuccess;
  }
  if (tone === "accent") {
    return modalStyles.summaryHeroAccent;
  }
  return modalStyles.summaryHeroDanger;
}

function heroIconStyle(tone: QualityGateStatusTone) {
  if (tone === "success") {
    return modalStyles.summaryHeroIconSuccess;
  }
  if (tone === "accent") {
    return modalStyles.summaryHeroIconAccent;
  }
  return modalStyles.summaryHeroIconDanger;
}

function heroIconColor(tone: QualityGateStatusTone) {
  if (tone === "success") {
    return colors.success;
  }
  if (tone === "accent") {
    return colors.accent;
  }
  return colors.danger;
}

export function QualityGateSummaryHero(props: {
  statusSummary: QualityGateStatusSummary;
  summaryChips: QualityGateSummaryChip[];
}) {
  const { statusSummary, summaryChips } = props;

  return (
    <View style={[modalStyles.summaryHero, heroToneStyle(statusSummary.tone)]}>
      <View style={modalStyles.summaryHeroTop}>
        <View
          style={[
            modalStyles.summaryHeroIcon,
            heroIconStyle(statusSummary.tone),
          ]}
        >
          <MaterialCommunityIcons
            color={heroIconColor(statusSummary.tone)}
            name={statusSummary.icon}
            size={18}
          />
        </View>
        <View style={modalStyles.summaryHeroCopy}>
          <Text style={modalStyles.summaryHeroLabel}>
            {statusSummary.label}
          </Text>
          <Text style={modalStyles.summaryHeroDescription}>
            {statusSummary.description}
          </Text>
        </View>
      </View>
      <View style={modalStyles.summaryChipRow}>
        {summaryChips.map((item) => (
          <View key={item.key} style={modalStyles.summaryChip}>
            <Text style={modalStyles.summaryChipText}>{item.label}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

export function QualityGateMetricRow(props: {
  evidenceCount: string | null;
  photoCount: string | null;
  reportPackSummary: MobileReportPackDraftSummary | null;
  textCount: string | null;
}) {
  const { evidenceCount, photoCount, reportPackSummary, textCount } = props;

  return (
    <View style={modalStyles.metricRow}>
      {textCount ? (
        <View style={modalStyles.metricCard}>
          <Text style={modalStyles.metricValue}>{textCount}</Text>
          <Text style={modalStyles.metricLabel}>Registros</Text>
        </View>
      ) : null}
      {evidenceCount ? (
        <View style={modalStyles.metricCard}>
          <Text style={modalStyles.metricValue}>{evidenceCount}</Text>
          <Text style={modalStyles.metricLabel}>Evidências</Text>
        </View>
      ) : null}
      {photoCount ? (
        <View style={modalStyles.metricCard}>
          <Text style={modalStyles.metricValue}>{photoCount}</Text>
          <Text style={modalStyles.metricLabel}>Fotos</Text>
        </View>
      ) : null}
      {reportPackSummary?.totalBlocks ? (
        <View style={modalStyles.metricCard}>
          <Text style={modalStyles.metricValue}>
            {`${reportPackSummary.readyBlocks}/${reportPackSummary.totalBlocks}`}
          </Text>
          <Text style={modalStyles.metricLabel}>Blocos</Text>
        </View>
      ) : null}
    </View>
  );
}

export function QualityGateReportPackSection(props: {
  reportPackSummary: MobileReportPackDraftSummary | null;
}) {
  const { reportPackSummary } = props;
  if (!reportPackSummary) {
    return null;
  }

  return (
    <View style={modalStyles.section} testID="quality-gate-report-pack-section">
      <Text style={modalStyles.sectionTitle}>Prontidão do pré-laudo</Text>
      <Text style={modalStyles.sectionDescription}>
        {`${reportPackSummary.readinessLabel}. ${reportPackSummary.readinessDetail}`}
      </Text>
      <Text style={modalStyles.issueMeta}>
        {`${reportPackSummary.templateLabel} • ${reportPackSummary.finalValidationModeLabel} • conflito ${reportPackSummary.maxConflictScore}`}
      </Text>
      {reportPackSummary.blockSummaries.map((item) => (
        <View key={item.key} style={modalStyles.issueCard}>
          <View style={modalStyles.issueHeader}>
            <Text style={modalStyles.issueTitle}>{item.title}</Text>
            <Text style={modalStyles.issueBadge}>{item.statusLabel}</Text>
          </View>
          <Text style={modalStyles.issueText}>{item.summary}</Text>
        </View>
      ))}
      {reportPackSummary.missingEvidenceMessages.map((item) => (
        <Text key={item} style={modalStyles.sectionDescription}>
          {item}
        </Text>
      ))}
    </View>
  );
}

export function QualityGateMissingItemsSection(props: {
  items: NonNullable<MobileQualityGateResponse["faltantes"]>;
}) {
  const { items } = props;
  if (!items.length) {
    return null;
  }

  return (
    <View style={modalStyles.section}>
      <Text style={modalStyles.sectionTitle}>
        Pendências que ainda bloqueiam o caso
      </Text>
      {items.map((item) => (
        <View key={item.id} style={modalStyles.issueCard}>
          <View style={modalStyles.issueHeader}>
            <Text style={modalStyles.issueTitle}>{item.titulo}</Text>
            <Text style={modalStyles.issueBadge}>Faltante</Text>
          </View>
          <Text style={modalStyles.issueMeta}>
            {item.categoria || "coleta"} • atual {String(item.atual ?? "-")} •
            mínimo {String(item.minimo ?? "-")}
          </Text>
          {!!item.observacao && (
            <Text style={modalStyles.issueText}>{item.observacao}</Text>
          )}
        </View>
      ))}
    </View>
  );
}

export function QualityGateGuideSection(props: {
  payload: MobileQualityGateResponse;
}) {
  const guideItems = props.payload.roteiro_template?.itens || [];
  if (!guideItems.length) {
    return null;
  }

  return (
    <View style={modalStyles.section}>
      <Text style={modalStyles.sectionTitle}>
        Roteiro obrigatório do template
      </Text>
      {!!props.payload.roteiro_template?.descricao && (
        <Text style={modalStyles.sectionDescription}>
          {props.payload.roteiro_template.descricao}
        </Text>
      )}
      {guideItems.map((item) => (
        <View key={item.id} style={modalStyles.guideItem}>
          <MaterialCommunityIcons
            color={colors.accent}
            name="check-circle-outline"
            size={16}
          />
          <View style={modalStyles.guideCopy}>
            <Text style={modalStyles.guideTitle}>{item.titulo}</Text>
            {!!item.descricao && (
              <Text style={modalStyles.guideDescription}>{item.descricao}</Text>
            )}
          </View>
        </View>
      ))}
    </View>
  );
}

export function QualityGateOverrideSection(props: {
  onChangeReason: (value: string) => void;
  payload: MobileQualityGateResponse;
  reason: string;
  reasonRequired: boolean;
}) {
  const { onChangeReason, payload, reason, reasonRequired } = props;

  return (
    <View style={modalStyles.section}>
      <Text style={modalStyles.sectionTitle}>Exceção governada disponível</Text>
      <Text style={modalStyles.sectionDescription}>
        {payload.human_override_policy?.message ||
          "A divergência pode seguir com justificativa interna."}
      </Text>
      {payload.human_override_policy?.matched_override_case_labels?.length ? (
        <View style={modalStyles.caseLabelRow}>
          {payload.human_override_policy.matched_override_case_labels.map(
            (label) => (
              <View key={label} style={modalStyles.caseLabelChip}>
                <Text style={modalStyles.caseLabelText}>{label}</Text>
              </View>
            ),
          )}
        </View>
      ) : null}
      <Text style={modalStyles.responsibilityText}>
        {payload.human_override_policy?.responsibility_notice}
      </Text>
      <TextInput
        multiline
        onChangeText={onChangeReason}
        placeholder="Explique internamente por que o caso seguirá mesmo assim."
        placeholderTextColor={colors.textSecondary}
        style={modalStyles.reasonInput}
        value={reason}
      />
      <Text style={modalStyles.reasonHint}>
        {reasonRequired
          ? `Justificativa interna obrigatória com pelo menos ${QUALITY_GATE_OVERRIDE_MIN_REASON_LENGTH} caracteres.`
          : "Justificativa interna opcional."}
      </Text>
    </View>
  );
}

export function QualityGateCorrectionSection() {
  return (
    <View style={modalStyles.section}>
      <Text style={modalStyles.sectionTitle}>
        Correção necessária antes de seguir
      </Text>
      <Text style={modalStyles.sectionDescription}>
        Ajuste a coleta do caso e volte a validar quando as pendências forem
        resolvidas.
      </Text>
    </View>
  );
}

export function QualityGateOfflineCard(props: { statusApi: ApiHealthStatus }) {
  if (props.statusApi !== "offline") {
    return null;
  }

  return (
    <View style={modalStyles.offlineCard}>
      <MaterialCommunityIcons color={colors.accent} name="wifi-off" size={16} />
      <Text style={modalStyles.offlineText}>
        Se a confirmação falhar por conexão, a finalização pode ficar guardada
        na fila offline.
      </Text>
    </View>
  );
}
