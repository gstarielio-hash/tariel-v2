import { Text, View } from "react-native";

import { styles } from "../InspectorMobileApp.styles";
import { SettingsPrintRow } from "./SettingsPrimitives";
import type {
  SettingsDrawerPage,
  SettingsSectionKey,
} from "./settingsNavigationMeta";

interface SettingsOverviewSystemSupportSectionProps {
  onAbrirPaginaConfiguracoes: (
    page: SettingsDrawerPage,
    section?: SettingsSectionKey | "all",
  ) => void;
  onReportarProblema: () => void;
  settingsPrintDarkMode: boolean;
}

export function SettingsOverviewSystemSupportSection({
  onAbrirPaginaConfiguracoes,
  onReportarProblema,
  settingsPrintDarkMode,
}: SettingsOverviewSystemSupportSectionProps) {
  return (
    <View style={styles.settingsPrintSectionBlock}>
      <Text
        style={[
          styles.settingsPrintSectionTitle,
          settingsPrintDarkMode ? styles.settingsPrintSectionTitleDark : null,
        ]}
      >
        Sistema e suporte
      </Text>
      <View
        style={[
          styles.settingsPrintGroupCard,
          settingsPrintDarkMode ? styles.settingsPrintGroupCardDark : null,
        ]}
      >
        <SettingsPrintRow
          darkMode={settingsPrintDarkMode}
          icon="microphone-outline"
          infoText="Voz, microfone e ditado."
          onPress={() =>
            onAbrirPaginaConfiguracoes("sistemaSuporte", "recursosAvancados")
          }
          testID="settings-print-fala-row"
          title="Fala"
        />
        <SettingsPrintRow
          darkMode={settingsPrintDarkMode}
          icon="apps"
          infoText="Sistema, atividade, manutenção e suporte."
          onPress={() => onAbrirPaginaConfiguracoes("sistemaSuporte")}
          testID="settings-print-aplicativos-row"
          title="Sistema e suporte"
        />
        <SettingsPrintRow
          darkMode={settingsPrintDarkMode}
          icon="database-cog-outline"
          infoText="Histórico, retenção, exportação e privacidade."
          onPress={() =>
            onAbrirPaginaConfiguracoes("seguranca", "dadosConversas")
          }
          testID="settings-print-data-controls-row"
          title="Controles de dados"
        />
        <SettingsPrintRow
          darkMode={settingsPrintDarkMode}
          icon="bug-outline"
          infoText="Enviar problema para análise."
          onPress={onReportarProblema}
          testID="settings-print-bug-row"
          title="Informar bug"
        />
        <SettingsPrintRow
          darkMode={settingsPrintDarkMode}
          icon="information-outline"
          infoText="Informações do app e ajuda."
          last
          onPress={() =>
            onAbrirPaginaConfiguracoes("sistemaSuporte", "suporte")
          }
          testID="settings-print-sobre-row"
          title="Sobre"
        />
      </View>
    </View>
  );
}
