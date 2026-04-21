import { MaterialCommunityIcons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";

import { colors } from "../../theme/tokens";
import { styles } from "../InspectorMobileApp.styles";
import type {
  IconName,
  ThreadAction,
  ThreadChip,
  ThreadInsight,
  ThreadSpotlight,
  ThreadTone,
} from "./ThreadContextCard";

function colorForTone(tone: ThreadTone) {
  if (tone === "accent") {
    return colors.accent;
  }
  if (tone === "success") {
    return colors.success;
  }
  if (tone === "danger") {
    return colors.danger;
  }
  return colors.textSecondary;
}

function chipContainerStyleForTone(tone: ThreadTone) {
  if (tone === "accent") {
    return styles.threadContextChipAccent;
  }
  if (tone === "success") {
    return styles.threadContextChipSuccess;
  }
  if (tone === "danger") {
    return styles.threadContextChipDanger;
  }
  return null;
}

function chipTextStyleForTone(tone: ThreadTone) {
  if (tone === "accent") {
    return styles.threadContextChipTextAccent;
  }
  if (tone === "success") {
    return styles.threadContextChipTextSuccess;
  }
  if (tone === "danger") {
    return styles.threadContextChipTextDanger;
  }
  return null;
}

function actionContainerStyleForTone(tone: ThreadTone) {
  if (tone === "accent") {
    return styles.threadActionButtonAccent;
  }
  if (tone === "success") {
    return styles.threadActionButtonSuccess;
  }
  if (tone === "danger") {
    return styles.threadActionButtonDanger;
  }
  return null;
}

function actionTextStyleForTone(tone: ThreadTone) {
  if (tone === "accent") {
    return styles.threadActionButtonTextAccent;
  }
  if (tone === "success") {
    return styles.threadActionButtonTextSuccess;
  }
  if (tone === "danger") {
    return styles.threadActionButtonTextDanger;
  }
  return null;
}

function insightCardStyleForTone(tone: ThreadTone) {
  if (tone === "accent") {
    return styles.threadInsightCardAccent;
  }
  if (tone === "success") {
    return styles.threadInsightCardSuccess;
  }
  if (tone === "danger") {
    return styles.threadInsightCardDanger;
  }
  return null;
}

function insightIconStyleForTone(tone: ThreadTone) {
  if (tone === "accent") {
    return styles.threadInsightIconAccent;
  }
  if (tone === "success") {
    return styles.threadInsightIconSuccess;
  }
  if (tone === "danger") {
    return styles.threadInsightIconDanger;
  }
  return null;
}

function chooserCardStyleForTone(tone: ThreadTone) {
  if (tone === "accent") {
    return styles.threadChooserActionCardAccent;
  }
  if (tone === "success") {
    return styles.threadChooserActionCardSuccess;
  }
  return null;
}

function chooserIconStyleForTone(tone: ThreadTone) {
  if (tone === "accent") {
    return styles.threadChooserActionIconAccent;
  }
  if (tone === "success") {
    return styles.threadChooserActionIconSuccess;
  }
  return null;
}

function spotlightBadgeStyleForTone(tone: ThreadTone) {
  if (tone === "accent") {
    return styles.threadSpotlightBadgeAccent;
  }
  if (tone === "success") {
    return styles.threadSpotlightBadgeSuccess;
  }
  if (tone === "danger") {
    return styles.threadSpotlightBadgeDanger;
  }
  return null;
}

function spotlightTextStyleForTone(tone: ThreadTone) {
  if (tone === "accent") {
    return styles.threadSpotlightTextAccent;
  }
  if (tone === "success") {
    return styles.threadSpotlightTextSuccess;
  }
  if (tone === "danger") {
    return styles.threadSpotlightTextDanger;
  }
  return null;
}

export function ThreadContextChipView(props: {
  compact?: boolean;
  item: ThreadChip;
}) {
  const { compact = false, item } = props;

  return (
    <View
      style={[
        styles.threadContextChip,
        compact ? styles.threadContextChipCompact : null,
        chipContainerStyleForTone(item.tone),
      ]}
    >
      <MaterialCommunityIcons
        color={colorForTone(item.tone)}
        name={item.icon}
        size={compact ? 13 : 14}
      />
      <Text
        numberOfLines={1}
        style={[
          styles.threadContextChipText,
          compact ? styles.threadContextChipTextCompact : null,
          chipTextStyleForTone(item.tone),
        ]}
      >
        {item.label}
      </Text>
    </View>
  );
}

export function ThreadContextActionButton(props: {
  compact?: boolean;
  item: ThreadAction;
}) {
  const { compact = false, item } = props;

  return (
    <Pressable
      onPress={item.onPress}
      style={[
        styles.threadActionButton,
        compact ? styles.threadActionButtonCompact : null,
        actionContainerStyleForTone(item.tone),
      ]}
      testID={item.testID}
    >
      <MaterialCommunityIcons
        color={colorForTone(item.tone)}
        name={item.icon}
        size={compact ? 14 : 15}
      />
      <Text
        numberOfLines={1}
        style={[
          styles.threadActionButtonText,
          compact ? styles.threadActionButtonTextCompact : null,
          actionTextStyleForTone(item.tone),
        ]}
      >
        {item.label}
      </Text>
    </Pressable>
  );
}

export function ThreadContextInsightsGrid(props: { items: ThreadInsight[] }) {
  return (
    <View style={styles.threadInsightGrid}>
      {props.items.map((item) => (
        <View
          key={item.key}
          style={[styles.threadInsightCard, insightCardStyleForTone(item.tone)]}
        >
          <View
            style={[
              styles.threadInsightIcon,
              insightIconStyleForTone(item.tone),
            ]}
          >
            <MaterialCommunityIcons
              color={colorForTone(item.tone)}
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
}

export function ThreadContextChooserActionCard(props: {
  detail: string;
  icon: IconName;
  label: string;
  onPress: () => void;
  testID?: string;
  tone: ThreadTone;
  trailingIcon?: IconName;
}) {
  const { detail, icon, label, onPress, testID, tone, trailingIcon } = props;

  return (
    <Pressable
      onPress={onPress}
      style={[styles.threadChooserActionCard, chooserCardStyleForTone(tone)]}
      testID={testID}
    >
      <View
        style={[styles.threadChooserActionIcon, chooserIconStyleForTone(tone)]}
      >
        <MaterialCommunityIcons
          color={colorForTone(tone)}
          name={icon}
          size={18}
        />
      </View>
      <View style={styles.threadChooserActionCopy}>
        <Text style={styles.threadChooserActionTitle}>{label}</Text>
        <Text style={styles.threadChooserActionDetail}>{detail}</Text>
      </View>
      <MaterialCommunityIcons
        color={colors.textSecondary}
        name={trailingIcon || "chevron-right"}
        size={18}
      />
    </Pressable>
  );
}

export function ThreadContextSpotlightBadge(props: {
  compact?: boolean;
  spotlight: ThreadSpotlight;
}) {
  const { compact = false, spotlight } = props;

  return (
    <View
      style={[
        styles.threadSpotlightBadge,
        compact ? styles.threadSpotlightBadgeCompact : null,
        spotlightBadgeStyleForTone(spotlight.tone),
      ]}
    >
      <MaterialCommunityIcons
        color={colorForTone(spotlight.tone)}
        name={spotlight.icon}
        size={14}
      />
      <Text
        style={[
          styles.threadSpotlightText,
          compact ? styles.threadSpotlightTextCompact : null,
          spotlightTextStyleForTone(spotlight.tone),
        ]}
      >
        {spotlight.label}
      </Text>
    </View>
  );
}
