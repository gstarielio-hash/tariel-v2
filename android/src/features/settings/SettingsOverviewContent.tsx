import { Text, View } from "react-native";

import { ProfileAvatarPicker } from "../../settings/components";
import { styles } from "../InspectorMobileApp.styles";
import {
  SettingsOverviewCard,
  SettingsPrintRow,
  SettingsStatusPill,
} from "./SettingsPrimitives";
import { SettingsOverviewNowCard } from "./SettingsOverviewNowCard";
import { SettingsOverviewQuickActionsSection } from "./SettingsOverviewQuickActionsSection";
import { SettingsOverviewSystemSupportSection } from "./SettingsOverviewSystemSupportSection";
import type {
  SettingsDrawerPage,
  SettingsSectionKey,
} from "./settingsNavigationMeta";

interface SettingsOverviewContentProps {
  settingsPrintDarkMode: boolean;
  perfilFotoUri: string;
  iniciaisPerfilConfiguracao: string;
  nomeUsuarioExibicao: string;
  detalheGovernancaConfiguracao: string;
  workspaceResumoConfiguracao: string;
  planoResumoConfiguracao: string;
  contaEmailLabel: string;
  contaTelefoneLabel: string;
  reemissoesRecomendadasTotal: number;
  resumoGovernancaConfiguracao: string;
  temaResumoConfiguracao: string;
  corDestaqueResumoConfiguracao: string;
  onUploadFotoPerfil: () => void;
  onAbrirPaginaConfiguracoes: (
    page: SettingsDrawerPage,
    section?: SettingsSectionKey | "all",
  ) => void;
  onReportarProblema: () => void;
  onFecharConfiguracoes: () => void;
  onLogout: () => void | Promise<void>;
}

export function SettingsOverviewContent({
  settingsPrintDarkMode,
  perfilFotoUri,
  iniciaisPerfilConfiguracao,
  nomeUsuarioExibicao,
  detalheGovernancaConfiguracao,
  workspaceResumoConfiguracao,
  planoResumoConfiguracao,
  contaEmailLabel,
  contaTelefoneLabel,
  reemissoesRecomendadasTotal,
  resumoGovernancaConfiguracao,
  temaResumoConfiguracao,
  corDestaqueResumoConfiguracao,
  onUploadFotoPerfil,
  onAbrirPaginaConfiguracoes,
  onReportarProblema,
  onFecharConfiguracoes,
  onLogout,
}: SettingsOverviewContentProps) {
  return (
    <View style={styles.settingsPrintOverview}>
      <View
        style={[
          styles.settingsSummaryCard,
          settingsPrintDarkMode ? styles.settingsSummaryCardDark : null,
        ]}
        testID="settings-overview-summary-card"
      >
        <View style={styles.settingsSummaryTop}>
          <ProfileAvatarPicker
            darkMode={settingsPrintDarkMode}
            fallbackLabel={iniciaisPerfilConfiguracao}
            onPress={onUploadFotoPerfil}
            photoUri={perfilFotoUri}
            testID="settings-overview-profile-photo"
          />
          <View style={styles.settingsSummaryCopy}>
            <Text
              style={[
                styles.settingsSummaryEyebrow,
                settingsPrintDarkMode
                  ? styles.settingsSummaryEyebrowDark
                  : null,
              ]}
            >
              Perfil
            </Text>
            <Text
              style={[
                styles.settingsSummaryName,
                settingsPrintDarkMode ? styles.settingsSummaryNameDark : null,
              ]}
            >
              {nomeUsuarioExibicao}
            </Text>
            <Text
              style={[
                styles.settingsSummaryMeta,
                settingsPrintDarkMode ? styles.settingsSummaryMetaDark : null,
              ]}
            >
              {workspaceResumoConfiguracao}
            </Text>
          </View>
        </View>
        <View style={styles.settingsSummaryChips}>
          <SettingsStatusPill
            label={planoResumoConfiguracao || "Plano sob medida"}
            tone="accent"
          />
          <SettingsStatusPill label={`Tema ${temaResumoConfiguracao}`} />
          <SettingsStatusPill
            label={`Ênfase ${corDestaqueResumoConfiguracao}`}
          />
          <SettingsStatusPill
            label={
              reemissoesRecomendadasTotal
                ? resumoGovernancaConfiguracao
                : "Governança em dia"
            }
            tone={reemissoesRecomendadasTotal ? "danger" : "success"}
          />
        </View>
        <View style={styles.settingsHeroSignalGrid}>
          <View
            style={styles.settingsHeroSignalCard}
            testID="settings-overview-signal-workspace"
          >
            <Text style={styles.settingsHeroSignalLabel}>Workspace</Text>
            <Text style={styles.settingsHeroSignalValue}>
              {workspaceResumoConfiguracao}
            </Text>
          </View>
          <View
            style={styles.settingsHeroSignalCard}
            testID="settings-overview-signal-theme"
          >
            <Text style={styles.settingsHeroSignalLabel}>Ambiente</Text>
            <Text style={styles.settingsHeroSignalValue}>
              {`Tema ${temaResumoConfiguracao} · ${corDestaqueResumoConfiguracao}`}
            </Text>
          </View>
          <View
            style={styles.settingsHeroSignalCard}
            testID="settings-overview-signal-contact"
          >
            <Text style={styles.settingsHeroSignalLabel}>Contato</Text>
            <Text style={styles.settingsHeroSignalValue}>
              {contaEmailLabel}
            </Text>
          </View>
          <View
            style={styles.settingsHeroSignalCard}
            testID="settings-overview-signal-governance"
          >
            <Text style={styles.settingsHeroSignalLabel}>Governança</Text>
            <Text style={styles.settingsHeroSignalValue}>
              {resumoGovernancaConfiguracao}
            </Text>
          </View>
        </View>
      </View>

      <View style={styles.settingsOverviewGrid}>
        <SettingsOverviewCard
          badge="Conta"
          darkMode={settingsPrintDarkMode}
          description="Perfil, acesso e workspace atual."
          icon="briefcase-outline"
          onPress={() => onAbrirPaginaConfiguracoes("contaAcesso")}
          testID="settings-overview-account-card"
          title="Operação ativa"
          tone="accent"
        />
        <SettingsOverviewCard
          badge="Plano"
          darkMode={settingsPrintDarkMode}
          description="Plano atual e superfícies liberadas no mobile."
          icon="star-circle-outline"
          onPress={() => onAbrirPaginaConfiguracoes("contaAcesso")}
          testID="settings-overview-plan-card"
          title="Plano e liberação"
          tone="success"
        />
        <SettingsOverviewCard
          badge="App"
          darkMode={settingsPrintDarkMode}
          description="IA, aparência e notificações."
          icon="tune-variant"
          onPress={() => onAbrirPaginaConfiguracoes("experiencia")}
          testID="settings-overview-experience-card"
          title="Experiência mobile"
        />
        <SettingsOverviewCard
          badge="Revisar"
          darkMode={settingsPrintDarkMode}
          description={
            reemissoesRecomendadasTotal
              ? detalheGovernancaConfiguracao
              : "Permissões, histórico e proteção local."
          }
          icon="shield-outline"
          onPress={() => onAbrirPaginaConfiguracoes("seguranca")}
          testID="settings-overview-security-card"
          title="Segurança e dados"
          tone="danger"
        />
      </View>

      <SettingsOverviewNowCard
        contaEmailLabel={contaEmailLabel}
        contaTelefoneLabel={contaTelefoneLabel}
        detalheGovernancaConfiguracao={detalheGovernancaConfiguracao}
        planoResumoConfiguracao={planoResumoConfiguracao}
        reemissoesRecomendadasTotal={reemissoesRecomendadasTotal}
        resumoGovernancaConfiguracao={resumoGovernancaConfiguracao}
        temaResumoConfiguracao={temaResumoConfiguracao}
        workspaceResumoConfiguracao={workspaceResumoConfiguracao}
      />

      <SettingsOverviewQuickActionsSection
        corDestaqueResumoConfiguracao={corDestaqueResumoConfiguracao}
        reemissoesRecomendadasTotal={reemissoesRecomendadasTotal}
        resumoGovernancaConfiguracao={resumoGovernancaConfiguracao}
        onAbrirPaginaConfiguracoes={onAbrirPaginaConfiguracoes}
        settingsPrintDarkMode={settingsPrintDarkMode}
        temaResumoConfiguracao={temaResumoConfiguracao}
        workspaceResumoConfiguracao={workspaceResumoConfiguracao}
      />

      <SettingsOverviewSystemSupportSection
        onAbrirPaginaConfiguracoes={onAbrirPaginaConfiguracoes}
        onReportarProblema={onReportarProblema}
        settingsPrintDarkMode={settingsPrintDarkMode}
      />

      <View style={styles.settingsPrintSectionBlock}>
        <View
          style={[
            styles.settingsPrintGroupCard,
            settingsPrintDarkMode ? styles.settingsPrintGroupCardDark : null,
          ]}
        >
          <SettingsPrintRow
            danger
            darkMode={settingsPrintDarkMode}
            icon="logout-variant"
            last
            onPress={() => {
              onFecharConfiguracoes();
              void onLogout();
            }}
            testID="settings-print-sair-row"
            title="Sair"
            trailingIcon={null}
          />
        </View>
      </View>
    </View>
  );
}
