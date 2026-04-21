import { MaterialCommunityIcons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";

import { colors } from "../../theme/tokens";
import { styles } from "../InspectorMobileApp.styles";

interface SettingsDrawerHeaderProps {
  settingsDrawerInOverview: boolean;
  settingsPrintDarkMode: boolean;
  settingsDrawerTitle: string;
  settingsDrawerSubtitle: string;
  onCloseOrBackPress: () => void;
}

export function SettingsDrawerHeader({
  settingsDrawerInOverview,
  settingsPrintDarkMode,
  settingsDrawerTitle,
  settingsDrawerSubtitle,
  onCloseOrBackPress,
}: SettingsDrawerHeaderProps) {
  const headerTitle = settingsDrawerInOverview
    ? "Configurações"
    : settingsDrawerTitle;
  const headerSubtitle = settingsDrawerInOverview
    ? "Conta, app e operação em campo."
    : settingsDrawerSubtitle;

  return (
    <View style={styles.sidePanelHeader}>
      <View style={styles.sidePanelCopy}>
        <Text
          style={[
            styles.sidePanelTitle,
            settingsDrawerInOverview ? styles.sidePanelTitlePrint : null,
            settingsDrawerInOverview && settingsPrintDarkMode
              ? styles.sidePanelTitlePrintDark
              : null,
          ]}
        >
          {headerTitle}
        </Text>
        {headerSubtitle ? (
          <Text
            style={[
              styles.sidePanelDescription,
              settingsDrawerInOverview
                ? styles.sidePanelDescriptionPrint
                : null,
              settingsDrawerInOverview && settingsPrintDarkMode
                ? styles.sidePanelDescriptionPrintDark
                : null,
            ]}
          >
            {headerSubtitle}
          </Text>
        ) : null}
      </View>
      <Pressable
        onPress={onCloseOrBackPress}
        style={[
          styles.sidePanelCloseButton,
          settingsDrawerInOverview ? styles.sidePanelCloseButtonPrint : null,
          settingsDrawerInOverview && settingsPrintDarkMode
            ? styles.sidePanelCloseButtonPrintDark
            : null,
        ]}
        testID={
          settingsDrawerInOverview
            ? "close-settings-drawer-button"
            : "settings-drawer-back-button"
        }
      >
        <MaterialCommunityIcons
          name={settingsDrawerInOverview ? "close" : "chevron-left"}
          size={22}
          color={colors.textPrimary}
        />
      </Pressable>
    </View>
  );
}
