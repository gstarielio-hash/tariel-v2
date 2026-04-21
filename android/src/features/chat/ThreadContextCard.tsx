import { useEffect, useState } from "react";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";

import { colors } from "../../theme/tokens";
import { styles } from "../InspectorMobileApp.styles";
import { ThreadFinalizationCard } from "./ThreadFinalizationCard";
import {
  ThreadContextActionButton,
  ThreadContextChipView,
  ThreadContextChooserActionCard,
  ThreadContextInsightsGrid,
  ThreadContextSpotlightBadge,
} from "./ThreadContextCardParts";

export type ThreadTone = "accent" | "success" | "danger" | "muted";
export type IconName = keyof typeof MaterialCommunityIcons.glyphMap;

export interface ThreadSpotlight {
  label: string;
  tone: ThreadTone;
  icon: IconName;
}

export interface ThreadChip {
  key: string;
  label: string;
  tone: ThreadTone;
  icon: IconName;
}

export interface ThreadInsight {
  key: string;
  label: string;
  value: string;
  detail: string;
  tone: ThreadTone;
  icon: IconName;
}

export interface ThreadAction {
  key: string;
  label: string;
  tone: ThreadTone;
  icon: IconName;
  onPress: () => void;
  testID?: string;
}

export interface ThreadContextCardProps {
  visible: boolean;
  defaultExpanded?: boolean;
  layout?: "default" | "entry_chooser" | "finalization";
  guidedTemplatesVisible?: boolean;
  eyebrow: string;
  title: string;
  description: string;
  spotlight: ThreadSpotlight;
  chips: ThreadChip[];
  onGuidedTemplatesVisibleChange?: (value: boolean) => void;
  actions?: ThreadAction[];
  insights: ThreadInsight[];
}

export function ThreadContextCard({
  visible,
  defaultExpanded = false,
  layout = "default",
  guidedTemplatesVisible,
  eyebrow,
  title,
  description,
  spotlight,
  chips,
  onGuidedTemplatesVisibleChange,
  actions = [],
  insights,
}: ThreadContextCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [guidedTemplatesVisibleState, setGuidedTemplatesVisibleState] =
    useState(false);
  const guidedTemplatesExpanded =
    guidedTemplatesVisible ?? guidedTemplatesVisibleState;

  function setGuidedTemplatesVisibility(
    value: boolean | ((current: boolean) => boolean),
  ) {
    const nextValue =
      typeof value === "function" ? value(guidedTemplatesExpanded) : value;

    if (onGuidedTemplatesVisibleChange) {
      onGuidedTemplatesVisibleChange(nextValue);
      return;
    }

    setGuidedTemplatesVisibleState(nextValue);
  }

  useEffect(() => {
    if (!visible) {
      return;
    }
    setExpanded(defaultExpanded);
    setDismissed(false);
  }, [
    actions.length,
    defaultExpanded,
    eyebrow,
    layout,
    spotlight.label,
    title,
    visible,
  ]);

  if (!visible || dismissed) {
    return null;
  }

  const primaryChip = chips[0] ?? null;
  const primaryAction = actions[0] ?? null;
  const visibleChips = expanded ? chips : chips.slice(0, 1);
  const visibleActions = expanded ? actions : actions.slice(0, 1);
  const visibleInsights = expanded ? insights : [];
  const hasMoreContent =
    chips.length > visibleChips.length ||
    actions.length > visibleActions.length ||
    insights.length > visibleInsights.length;

  if (layout === "entry_chooser") {
    const freeChatAction =
      actions.find((item) => item.key === "chat-free-start") || null;
    const guidedTemplateActions = actions.filter((item) =>
      item.key.startsWith("guided-template-"),
    );
    const fallbackActions = actions.filter(
      (item) =>
        item.key !== "chat-free-start" &&
        !item.key.startsWith("guided-template-"),
    );

    return (
      <View style={[styles.threadHeaderCard, styles.threadHeaderChooserCard]}>
        <View style={[styles.threadHeaderCopy, styles.threadHeaderChooserCopy]}>
          {eyebrow ? <Text style={styles.threadEyebrow}>{eyebrow}</Text> : null}
          <Text
            numberOfLines={2}
            style={[styles.threadTitle, styles.threadChooserTitle]}
          >
            {title}
          </Text>
        </View>

        {chips.length ? (
          <View style={styles.threadContextChips}>
            {chips.map((item) => (
              <ThreadContextChipView key={item.key} item={item} />
            ))}
          </View>
        ) : null}

        {insights.length ? (
          <ThreadContextInsightsGrid items={insights} />
        ) : null}

        <View style={styles.threadChooserActionStack}>
          {freeChatAction ? (
            <ThreadContextChooserActionCard
              detail="Fotos, contexto e análise flexível."
              icon={freeChatAction.icon}
              key={freeChatAction.key}
              label={freeChatAction.label}
              onPress={() => {
                setGuidedTemplatesVisibility(false);
                freeChatAction.onPress();
                setDismissed(true);
              }}
              testID={freeChatAction.testID}
              tone={freeChatAction.tone}
            />
          ) : null}

          {guidedTemplateActions.length ? (
            <ThreadContextChooserActionCard
              detail={
                guidedTemplatesExpanded
                  ? "Selecione agora o template técnico desejado."
                  : "Template técnico com coleta orientada."
              }
              icon="clipboard-text-outline"
              key="guided-entry"
              label="Chat guiado"
              onPress={() => {
                setGuidedTemplatesVisibility((current) => !current);
              }}
              testID="guided-entry-open-button"
              tone="accent"
              trailingIcon={
                guidedTemplatesExpanded ? "chevron-up" : "chevron-right"
              }
            />
          ) : null}

          {guidedTemplateActions.length && guidedTemplatesExpanded ? (
            <View style={styles.threadChooserTemplateSection}>
              <Text style={styles.threadChooserTemplateLabel}>
                Template do chat guiado
              </Text>
              <View style={styles.threadChooserTemplateGrid}>
                {guidedTemplateActions.map((item) => (
                  <Pressable
                    key={item.key}
                    onPress={() => {
                      item.onPress();
                      setDismissed(true);
                    }}
                    style={styles.threadChooserTemplateButton}
                    testID={item.testID}
                  >
                    <MaterialCommunityIcons
                      color={colors.accent}
                      name={item.icon}
                      size={16}
                    />
                    <Text style={styles.threadChooserTemplateButtonText}>
                      {item.label}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </View>
          ) : null}

          {fallbackActions.map((item) => (
            <ThreadContextChooserActionCard
              detail="Siga o fluxo sugerido para iniciar a coleta com o contexto certo."
              icon={item.icon}
              key={item.key}
              label={item.label}
              onPress={item.onPress}
              testID={item.testID}
              tone={item.tone}
            />
          ))}
        </View>
      </View>
    );
  }

  if (layout === "finalization") {
    return (
      <ThreadFinalizationCard
        actions={actions}
        chips={chips}
        description={description}
        eyebrow={eyebrow}
        insights={insights}
        spotlight={spotlight}
        title={title}
      />
    );
  }

  return (
    <View style={styles.threadHeaderCard}>
      <View style={styles.threadHeaderTop}>
        <View style={styles.threadHeaderCopy}>
          {eyebrow ? <Text style={styles.threadEyebrow}>{eyebrow}</Text> : null}
          <Text numberOfLines={1} style={styles.threadTitle}>
            {title}
          </Text>
          <Text
            numberOfLines={expanded ? 2 : 1}
            style={styles.threadDescription}
          >
            {description}
          </Text>
        </View>
        <ThreadContextSpotlightBadge compact spotlight={spotlight} />
      </View>

      {!expanded ? (
        primaryChip || primaryAction || hasMoreContent ? (
          <View style={styles.threadCollapsedSummaryRow}>
            {primaryChip ? (
              <ThreadContextChipView compact item={primaryChip} />
            ) : null}
            {primaryAction ? (
              <ThreadContextActionButton compact item={primaryAction} />
            ) : null}
            {hasMoreContent ? (
              <Pressable
                onPress={() => setExpanded(true)}
                style={[
                  styles.threadToggleButton,
                  styles.threadToggleButtonCompact,
                ]}
                testID="thread-context-toggle"
              >
                <Text style={styles.threadToggleButtonText}>Detalhes</Text>
                <MaterialCommunityIcons
                  color={colors.textSecondary}
                  name="chevron-down"
                  size={16}
                />
              </Pressable>
            ) : null}
          </View>
        ) : null
      ) : null}

      {expanded && visibleChips.length ? (
        <View style={styles.threadContextChips}>
          {visibleChips.map((item) => (
            <ThreadContextChipView key={item.key} item={item} />
          ))}
        </View>
      ) : null}

      {expanded && visibleActions.length ? (
        <View style={styles.threadActionRow}>
          {visibleActions.map((item) => (
            <ThreadContextActionButton key={item.key} item={item} />
          ))}
        </View>
      ) : null}

      {expanded && visibleInsights.length ? (
        <ThreadContextInsightsGrid items={visibleInsights} />
      ) : null}

      {expanded ? (
        <Pressable
          onPress={() => setExpanded((current) => !current)}
          style={styles.threadToggleButton}
          testID="thread-context-toggle"
        >
          <Text style={styles.threadToggleButtonText}>Ocultar detalhes</Text>
          <MaterialCommunityIcons
            color={colors.textSecondary}
            name="chevron-up"
            size={16}
          />
        </Pressable>
      ) : null}
    </View>
  );
}
