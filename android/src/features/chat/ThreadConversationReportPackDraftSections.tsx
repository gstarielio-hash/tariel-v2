import type { ReactNode } from "react";
import { Pressable, Text, View } from "react-native";

import { styles } from "../InspectorMobileApp.styles";
import type {
  MobileReportPackBlockSummary,
  MobileReportPackExecutiveSummary,
  MobileReportPackFlowSummary,
  MobileReportPackSectionSummary,
  MobileReportPackSlotSummary,
  ReportPackBlockStatus,
} from "./reportPackHelpers";

type AnalysisBasisEntry = {
  key: string;
  title: string;
  summary: string;
};

type ReportPackStatusRowItem = {
  status: ReportPackBlockStatus;
  statusLabel: string;
  summary: string;
  title: string;
};

function toneForReportPackStatus(
  status: ReportPackBlockStatus,
): "success" | "accent" | "danger" {
  if (status === "ready") {
    return "success";
  }
  if (status === "attention") {
    return "accent";
  }
  return "danger";
}

function ReportPackStatusBadge(props: {
  status: ReportPackBlockStatus;
  statusLabel: string;
}) {
  const tone = toneForReportPackStatus(props.status);

  return (
    <View
      style={[
        styles.threadReviewStatusBadge,
        tone === "success"
          ? styles.threadReviewStatusBadgeSuccess
          : tone === "accent"
            ? styles.threadReviewStatusBadgeAccent
            : styles.threadReviewStatusBadgeDanger,
      ]}
    >
      <Text
        style={[
          styles.threadReviewStatusBadgeText,
          tone === "success"
            ? styles.threadReviewStatusBadgeTextSuccess
            : tone === "accent"
              ? styles.threadReviewStatusBadgeTextAccent
              : styles.threadReviewStatusBadgeTextDanger,
        ]}
      >
        {props.statusLabel}
      </Text>
    </View>
  );
}

function ReportPackStatusRow(props: {
  children?: ReactNode;
  item: ReportPackStatusRowItem;
}) {
  const { item } = props;

  return (
    <View style={styles.threadReviewListItem}>
      <ReportPackStatusBadge
        status={item.status}
        statusLabel={item.statusLabel}
      />
      <View style={styles.threadReviewListCopy}>
        <Text style={styles.threadReviewListTitle}>{item.title}</Text>
        <Text style={styles.threadReviewListText}>{item.summary}</Text>
        {props.children}
      </View>
    </View>
  );
}

function ReportPackListSection(props: { children: ReactNode; title: string }) {
  return (
    <View style={styles.threadReviewList}>
      <Text style={styles.threadReviewSectionTitle}>{props.title}</Text>
      {props.children}
    </View>
  );
}

export function ThreadConversationReportPackFlowSection(props: {
  items: MobileReportPackFlowSummary[];
}) {
  const { items } = props;
  if (!items.length) {
    return null;
  }

  return (
    <ReportPackListSection title="Rota canônica">
      {items.map((item) => (
        <ReportPackStatusRow key={`${item.key}-${item.status}`} item={item} />
      ))}
    </ReportPackListSection>
  );
}

export function ThreadConversationReportPackExecutiveSection(props: {
  items: MobileReportPackExecutiveSummary[];
}) {
  const { items } = props;
  if (!items.length) {
    return null;
  }

  return (
    <ReportPackListSection title="Critérios de emissão">
      {items.map((item) => (
        <ReportPackStatusRow key={`${item.key}-${item.status}`} item={item}>
          {item.bullets.map((bullet) => (
            <Text key={bullet} style={styles.threadReviewFootnote}>
              {`- ${bullet}`}
            </Text>
          ))}
        </ReportPackStatusRow>
      ))}
    </ReportPackListSection>
  );
}

export function ThreadConversationReportPackBlocksSection(props: {
  items: MobileReportPackBlockSummary[];
}) {
  const { items } = props;
  if (!items.length) {
    return null;
  }

  return (
    <ReportPackListSection title="Blocos do pré-laudo">
      {items.map((item) => (
        <ReportPackStatusRow key={`${item.key}-${item.status}`} item={item} />
      ))}
    </ReportPackListSection>
  );
}

export function ThreadConversationReportPackDocumentSections(props: {
  items: MobileReportPackSectionSummary[];
}) {
  const { items } = props;
  if (!items.length) {
    return null;
  }

  return (
    <ReportPackListSection title="Seções do documento">
      {items.map((item) => (
        <ReportPackStatusRow
          key={item.key}
          item={{
            status: item.status,
            statusLabel: item.statusLabel,
            summary: item.summary,
            title: item.title,
          }}
        >
          {item.highlights.length ? (
            <Text style={styles.threadReviewFootnote}>
              Campos-chave: {item.highlights.join(" · ")}
            </Text>
          ) : null}
        </ReportPackStatusRow>
      ))}
    </ReportPackListSection>
  );
}

export function ThreadConversationReportPackEvidenceSlotsSection(props: {
  items: MobileReportPackSlotSummary[];
}) {
  const { items } = props;
  if (!items.length) {
    return null;
  }

  return (
    <ReportPackListSection title="Slots de evidência">
      {items.map((item) => (
        <ReportPackStatusRow
          key={item.key}
          item={{
            status: item.status,
            statusLabel: item.statusLabel,
            summary: item.summary,
            title: item.label,
          }}
        >
          {item.acceptedTypes.length ? (
            <Text style={styles.threadReviewFootnote}>
              Aceita: {item.acceptedTypes.join(", ")}
            </Text>
          ) : null}
          {item.bindingPath ? (
            <Text style={styles.threadReviewFootnote}>
              Vincula em: {item.bindingPath}
            </Text>
          ) : null}
        </ReportPackStatusRow>
      ))}
    </ReportPackListSection>
  );
}

export function ThreadConversationReportPackAnalysisBasisSection(props: {
  items: AnalysisBasisEntry[];
}) {
  const { items } = props;
  if (!items.length) {
    return null;
  }

  return (
    <ReportPackListSection title="Base analítica">
      {items.map((item) => (
        <View key={item.key} style={styles.threadReviewListItem}>
          <View style={styles.threadReviewListCopy}>
            <Text style={styles.threadReviewListTitle}>{item.title}</Text>
            <Text style={styles.threadReviewListText}>{item.summary}</Text>
          </View>
        </View>
      ))}
    </ReportPackListSection>
  );
}

export function ThreadConversationReportPackMissingEvidenceNotes(props: {
  items: string[];
}) {
  const { items } = props;
  if (!items.length) {
    return null;
  }

  return (
    <>
      {items.map((item) => (
        <Text key={item} style={styles.threadReviewFootnote}>
          Evidência faltante: {item}
        </Text>
      ))}
    </>
  );
}

export function ThreadConversationReportPackReviewRequiredSection(props: {
  items: string[];
}) {
  const { items } = props;
  if (!items.length) {
    return null;
  }

  return (
    <ReportPackListSection title="Revisão obrigatória">
      {items.map((item) => (
        <Text key={item} style={styles.threadReviewFootnote}>
          {`- ${item}`}
        </Text>
      ))}
    </ReportPackListSection>
  );
}

export function ThreadConversationReportPackActionsSection(props: {
  onAbrirMesaTab?: () => void;
  onAbrirQualityGate?: () => void | Promise<void>;
  showFinalizeAction: boolean;
  showOpenMesaAction: boolean;
  testID: string;
}) {
  const {
    onAbrirMesaTab,
    onAbrirQualityGate,
    showFinalizeAction,
    showOpenMesaAction,
    testID,
  } = props;

  if (!showFinalizeAction && !showOpenMesaAction) {
    return null;
  }

  return (
    <View style={styles.threadReviewActionsRail}>
      {showFinalizeAction ? (
        <Pressable
          accessibilityRole="button"
          onPress={() => {
            void onAbrirQualityGate?.();
          }}
          style={[
            styles.threadReviewActionButton,
            styles.threadReviewActionButtonSuccess,
          ]}
          testID={`${testID}-open-quality-gate`}
        >
          <Text
            style={[
              styles.threadReviewActionButtonText,
              styles.threadReviewActionButtonTextSuccess,
            ]}
          >
            Validar e finalizar
          </Text>
        </Pressable>
      ) : null}
      {showOpenMesaAction ? (
        <Pressable
          accessibilityRole="button"
          onPress={onAbrirMesaTab}
          style={[
            styles.threadReviewActionButton,
            styles.threadReviewActionButtonDanger,
          ]}
          testID={`${testID}-open-mesa`}
        >
          <Text
            style={[
              styles.threadReviewActionButtonText,
              styles.threadReviewActionButtonTextDanger,
            ]}
          >
            Abrir Mesa
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}

export function ThreadConversationReportPackNextQuestionsSection(props: {
  items: string[];
  onUsarPerguntaPreLaudo?: (value: string) => void;
  showQuestionActions: boolean;
  testID: string;
}) {
  const { items, onUsarPerguntaPreLaudo, showQuestionActions, testID } = props;
  if (!items.length) {
    return null;
  }

  return (
    <ReportPackListSection title="Próximas confirmações">
      {items.map((item, index) =>
        showQuestionActions ? (
          <Pressable
            key={item}
            accessibilityRole="button"
            onPress={() => onUsarPerguntaPreLaudo?.(item)}
            style={styles.threadReviewInlineAction}
            testID={`${testID}-next-question-${index}`}
          >
            <Text style={styles.threadReviewInlineActionText}>{item}</Text>
          </Pressable>
        ) : (
          <Text key={item} style={styles.threadReviewFootnote}>
            {`- ${item}`}
          </Text>
        ),
      )}
    </ReportPackListSection>
  );
}
