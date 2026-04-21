import { Text, View } from "react-native";

import { styles } from "../InspectorMobileApp.styles";
import { SettingsPrintRow } from "./SettingsPrimitives";
import type {
  SettingsDrawerPage,
  SettingsSectionKey,
} from "./settingsNavigationMeta";

interface SettingsOverviewQuickActionsSectionProps {
  corDestaqueResumoConfiguracao: string;
  onAbrirPaginaConfiguracoes: (
    page: SettingsDrawerPage,
    section?: SettingsSectionKey | "all",
  ) => void;
  reemissoesRecomendadasTotal: number;
  resumoGovernancaConfiguracao: string;
  settingsPrintDarkMode: boolean;
  temaResumoConfiguracao: string;
  workspaceResumoConfiguracao: string;
}

export function SettingsOverviewQuickActionsSection({
  corDestaqueResumoConfiguracao,
  onAbrirPaginaConfiguracoes,
  reemissoesRecomendadasTotal,
  resumoGovernancaConfiguracao,
  settingsPrintDarkMode,
  temaResumoConfiguracao,
  workspaceResumoConfiguracao,
}: SettingsOverviewQuickActionsSectionProps) {
  return (
    <View style={styles.settingsPrintSectionBlock}>
      <Text
        style={[
          styles.settingsPrintSectionTitle,
          settingsPrintDarkMode ? styles.settingsPrintSectionTitleDark : null,
        ]}
      >
        Ajustes rápidos
      </Text>
      <View
        style={[
          styles.settingsPrintGroupCard,
          settingsPrintDarkMode ? styles.settingsPrintGroupCardDark : null,
        ]}
      >
        <SettingsPrintRow
          darkMode={settingsPrintDarkMode}
          icon="tune-variant"
          infoText="IA, aparência e comportamento operacional do app."
          onPress={() => onAbrirPaginaConfiguracoes("experiencia")}
          testID="settings-print-personalizacao-row"
          title="Experiência"
        />
        <SettingsPrintRow
          darkMode={settingsPrintDarkMode}
          icon="account-circle-outline"
          infoText="Perfil, contato, senha e workspace ativo."
          onPress={() => onAbrirPaginaConfiguracoes("contaAcesso")}
          subtitle={workspaceResumoConfiguracao}
          testID="settings-print-workspace-row"
          title="Conta e acesso"
        />
        <SettingsPrintRow
          darkMode={settingsPrintDarkMode}
          icon="shield-lock-outline"
          infoText="Permissões, privacidade, histórico e proteção local."
          onPress={() => onAbrirPaginaConfiguracoes("seguranca")}
          subtitle={
            reemissoesRecomendadasTotal
              ? resumoGovernancaConfiguracao
              : undefined
          }
          testID="settings-print-seguranca-row"
          title="Segurança e privacidade"
        />
        <SettingsPrintRow
          darkMode={settingsPrintDarkMode}
          icon="brightness-6"
          infoText="Tema, densidade e aparência geral."
          onPress={() => onAbrirPaginaConfiguracoes("experiencia", "aparencia")}
          subtitle={`Tema ${temaResumoConfiguracao} · ${corDestaqueResumoConfiguracao}`}
          testID="settings-print-aparencia-row"
          title="Aparência"
        />
        <SettingsPrintRow
          darkMode={settingsPrintDarkMode}
          icon="bell-outline"
          infoText="Push, som, vibração e privacidade."
          last
          onPress={() =>
            onAbrirPaginaConfiguracoes("experiencia", "notificacoes")
          }
          testID="settings-print-notificacoes-row"
          title="Notificações"
          trailingIcon="chevron-right"
        />
      </View>
    </View>
  );
}
