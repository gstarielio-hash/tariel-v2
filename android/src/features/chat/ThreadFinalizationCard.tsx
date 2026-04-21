import { MaterialCommunityIcons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";

import { colors } from "../../theme/tokens";
import { styles } from "../InspectorMobileApp.styles";
import type {
  ThreadAction,
  ThreadChip,
  ThreadInsight,
  ThreadSpotlight,
} from "./ThreadContextCard";

interface ThreadFinalizationCardProps {
  eyebrow: string;
  title: string;
  description: string;
  spotlight: ThreadSpotlight;
  chips: ThreadChip[];
  actions: ThreadAction[];
  insights: ThreadInsight[];
}

export function ThreadFinalizationCard({
  eyebrow,
  title,
  description,
  spotlight,
  chips,
  actions,
  insights,
}: ThreadFinalizationCardProps) {
  const highlightedInsights = insights.filter((item) =>
    ["next-step", "blockers", "delivery"].includes(item.key),
  );
  const visibleDetailedInsights = (
    highlightedInsights.length ? highlightedInsights : insights
  ).slice(0, 3);

  const renderChip = (item: ThreadChip) => (
    <View
      key={item.key}
      style={[
        styles.threadContextChip,
        item.tone === "accent"
          ? styles.threadContextChipAccent
          : item.tone === "success"
            ? styles.threadContextChipSuccess
            : item.tone === "danger"
              ? styles.threadContextChipDanger
              : null,
      ]}
    >
      <MaterialCommunityIcons
        color={
          item.tone === "accent"
            ? colors.accent
            : item.tone === "success"
              ? colors.success
              : item.tone === "danger"
                ? colors.danger
                : colors.textSecondary
        }
        name={item.icon}
        size={14}
      />
      <Text
        numberOfLines={1}
        style={[
          styles.threadContextChipText,
          item.tone === "accent"
            ? styles.threadContextChipTextAccent
            : item.tone === "success"
              ? styles.threadContextChipTextSuccess
              : item.tone === "danger"
                ? styles.threadContextChipTextDanger
                : null,
        ]}
      >
        {item.label}
      </Text>
    </View>
  );

  const renderAction = (item: ThreadAction) => (
    <Pressable
      key={item.key}
      onPress={item.onPress}
      style={[
        styles.threadActionButton,
        item.tone === "accent"
          ? styles.threadActionButtonAccent
          : item.tone === "success"
            ? styles.threadActionButtonSuccess
            : item.tone === "danger"
              ? styles.threadActionButtonDanger
              : null,
      ]}
      testID={item.testID}
    >
      <MaterialCommunityIcons
        color={
          item.tone === "accent"
            ? colors.accent
            : item.tone === "success"
              ? colors.success
              : item.tone === "danger"
                ? colors.danger
                : colors.textSecondary
        }
        name={item.icon}
        size={15}
      />
      <Text
        numberOfLines={1}
        style={[
          styles.threadActionButtonText,
          item.tone === "accent"
            ? styles.threadActionButtonTextAccent
            : item.tone === "success"
              ? styles.threadActionButtonTextSuccess
              : item.tone === "danger"
                ? styles.threadActionButtonTextDanger
                : null,
        ]}
      >
        {item.label}
      </Text>
    </Pressable>
  );

  const renderInsightSummary = (items: ThreadInsight[]) => (
    <View style={styles.threadInsightSummaryRow}>
      {items.map((item) => (
        <View key={item.key} style={styles.threadInsightSummaryChip}>
          <Text style={styles.threadInsightSummaryLabel}>{item.label}</Text>
          <Text numberOfLines={1} style={styles.threadInsightSummaryValue}>
            {item.value}
          </Text>
        </View>
      ))}
    </View>
  );

  const renderInsights = (items: ThreadInsight[]) => (
    <View style={styles.threadInsightGrid}>
      {items.map((item) => (
        <View
          key={item.key}
          style={[
            styles.threadInsightCard,
            item.tone === "accent"
              ? styles.threadInsightCardAccent
              : item.tone === "success"
                ? styles.threadInsightCardSuccess
                : item.tone === "danger"
                  ? styles.threadInsightCardDanger
                  : null,
          ]}
        >
          <View
            style={[
              styles.threadInsightIcon,
              item.tone === "accent"
                ? styles.threadInsightIconAccent
                : item.tone === "success"
                  ? styles.threadInsightIconSuccess
                  : item.tone === "danger"
                    ? styles.threadInsightIconDanger
                    : null,
            ]}
          >
            <MaterialCommunityIcons
              color={
                item.tone === "accent"
                  ? colors.accent
                  : item.tone === "success"
                    ? colors.success
                    : item.tone === "danger"
                      ? colors.danger
                      : colors.textSecondary
              }
              name={item.icon}
              size={18}
            />
          </View>
          <View style={styles.threadInsightCopy}>
            <Text style={styles.threadInsightLabel}>{item.label}</Text>
            <Text style={styles.threadInsightValue}>{item.value}</Text>
            <Text style={styles.threadInsightDetail}>{item.detail}</Text>
          </View>
        </View>
      ))}
    </View>
  );

  return (
    <View
      style={[styles.threadHeaderCard, styles.threadHeaderFinalizationCard]}
    >
      <View
        style={[
          styles.threadFinalizationHero,
          spotlight.tone === "accent"
            ? styles.threadFinalizationHeroAccent
            : spotlight.tone === "success"
              ? styles.threadFinalizationHeroSuccess
              : spotlight.tone === "danger"
                ? styles.threadFinalizationHeroDanger
                : null,
        ]}
      >
        <View style={styles.threadFinalizationHeroTop}>
          <View style={styles.threadHeaderCopy}>
            {eyebrow ? (
              <Text style={styles.threadEyebrow}>{eyebrow}</Text>
            ) : null}
            <Text style={styles.threadFinalizationTitle}>{title}</Text>
            <Text style={styles.threadFinalizationDescription}>
              {description}
            </Text>
          </View>
          <View
            style={[
              styles.threadSpotlightBadge,
              spotlight.tone === "accent"
                ? styles.threadSpotlightBadgeAccent
                : spotlight.tone === "success"
                  ? styles.threadSpotlightBadgeSuccess
                  : spotlight.tone === "danger"
                    ? styles.threadSpotlightBadgeDanger
                    : null,
            ]}
          >
            <MaterialCommunityIcons
              color={
                spotlight.tone === "accent"
                  ? colors.accent
                  : spotlight.tone === "success"
                    ? colors.success
                    : spotlight.tone === "danger"
                      ? colors.danger
                      : colors.textSecondary
              }
              name={spotlight.icon}
              size={15}
            />
            <Text
              style={[
                styles.threadSpotlightText,
                spotlight.tone === "accent"
                  ? styles.threadSpotlightTextAccent
                  : spotlight.tone === "success"
                    ? styles.threadSpotlightTextSuccess
                    : spotlight.tone === "danger"
                      ? styles.threadSpotlightTextDanger
                      : null,
              ]}
            >
              {spotlight.label}
            </Text>
          </View>
        </View>

        {chips.length ? (
          <View style={styles.threadContextChips}>
            {chips.map((item) => renderChip(item))}
          </View>
        ) : null}
      </View>

      {actions.length ? (
        <View style={styles.threadFinalizationSection}>
          <Text style={styles.threadFinalizationSectionLabel}>
            Próximas ações
          </Text>
          <View style={styles.threadActionRow}>
            {actions.map((item) => renderAction(item))}
          </View>
        </View>
      ) : null}

      {insights.length ? (
        <View style={styles.threadFinalizationSection}>
          <Text style={styles.threadFinalizationSectionLabel}>
            Radar de emissão
          </Text>
          {renderInsightSummary(insights)}
        </View>
      ) : null}

      {visibleDetailedInsights.length ? (
        <View style={styles.threadFinalizationSection}>
          <Text style={styles.threadFinalizationSectionLabel}>
            Pontos críticos
          </Text>
          {renderInsights(visibleDetailedInsights)}
        </View>
      ) : null}
    </View>
  );
}
