import { MaterialCommunityIcons } from "@expo/vector-icons";
import {
  Animated,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
  type ImageSourcePropType,
  type PanResponderInstance,
} from "react-native";

import { EmptyState } from "../../components/EmptyState";
import { colors } from "../../theme/tokens";
import { styles } from "../InspectorMobileApp.styles";
import { resolverCaseLifecycleStatus } from "../chat/caseLifecycle";
import { HistoryDrawerListItem } from "./HistoryDrawerListItem";
import type {
  HistoryDrawerPanelItem,
  HistoryDrawerSection,
} from "./historyDrawerTypes";

export type {
  HistoryDrawerPanelItem,
  HistoryDrawerSection,
} from "./historyDrawerTypes";

function pluralizeHistoryCases(value: number): string {
  return `${value} caso${value === 1 ? "" : "s"}`;
}

function buildHistorySummaryCounts(items: readonly HistoryDrawerPanelItem[]) {
  return items.reduce(
    (acc, item) => {
      const lifecycleStatus = resolverCaseLifecycleStatus({
        card: {
          ...item,
          tipo_template: item.tipo_template || undefined,
        },
      });
      if (
        lifecycleStatus === "aguardando_mesa" ||
        lifecycleStatus === "em_revisao_mesa"
      ) {
        acc.mesa += 1;
      } else if (
        lifecycleStatus === "emitido" ||
        lifecycleStatus === "aprovado"
      ) {
        acc.concluidos += 1;
      } else {
        acc.emAndamento += 1;
      }
      return acc;
    },
    { concluidos: 0, emAndamento: 0, mesa: 0 },
  );
}

function buildHistorySummaryText(
  items: readonly HistoryDrawerPanelItem[],
  buscaHistorico: string,
): string {
  const totals = buildHistorySummaryCounts(items);

  if (buscaHistorico.trim()) {
    return `${pluralizeHistoryCases(items.length)} encontrados.`;
  }

  return `${totals.emAndamento} em andamento · ${totals.mesa} na mesa · ${totals.concluidos} concluidos`;
}

export interface HistoryDrawerPanelProps<TItem extends HistoryDrawerPanelItem> {
  historyDrawerPanResponder: PanResponderInstance;
  historicoDrawerX: Animated.Value;
  onCloseHistory: () => void;
  onHistorySearchFocusChange: (focused: boolean) => void;
  buscaHistorico: string;
  onBuscaHistoricoChange: (value: string) => void;
  conversasOcultasTotal: number;
  historicoAgrupadoFinal: HistoryDrawerSection<TItem>[];
  laudoSelecionadoId: number | null;
  onSelecionarHistorico: (item: TItem) => void;
  onExcluirConversaHistorico: (item: TItem) => void;
  historicoVazioTitulo: string;
  historicoVazioTexto: string;
  brandMarkSource: ImageSourcePropType;
}

export function HistoryDrawerPanel<TItem extends HistoryDrawerPanelItem>({
  historyDrawerPanResponder,
  historicoDrawerX,
  onCloseHistory,
  onHistorySearchFocusChange,
  buscaHistorico,
  onBuscaHistoricoChange,
  conversasOcultasTotal,
  historicoAgrupadoFinal,
  laudoSelecionadoId,
  onSelecionarHistorico,
  onExcluirConversaHistorico,
  historicoVazioTitulo,
  historicoVazioTexto,
}: HistoryDrawerPanelProps<TItem>) {
  const itensVisiveis = historicoAgrupadoFinal.flatMap(
    (section) => section.items,
  );
  const totals = buildHistorySummaryCounts(itensVisiveis);
  const totalVisiveis = historicoAgrupadoFinal.reduce(
    (total, section) => total + section.items.length,
    0,
  );
  const totalFixados = historicoAgrupadoFinal.reduce(
    (total, section) =>
      total + section.items.filter((item) => item.pinado).length,
    0,
  );
  const totalHistorico = totalVisiveis + conversasOcultasTotal;
  const exibirBusca = totalHistorico > 0 || Boolean(buscaHistorico.trim());

  return (
    <Animated.View
      {...historyDrawerPanResponder.panHandlers}
      style={[
        styles.sidePanelDrawer,
        styles.sidePanelDrawerLeft,
        { transform: [{ translateX: historicoDrawerX }] },
      ]}
      testID="history-drawer"
    >
      <View style={styles.sidePanelHeader}>
        <View style={styles.sidePanelCopy}>
          <Text style={styles.sidePanelTitle}>Histórico</Text>
          <Text style={styles.sidePanelDescription}>Conversas recentes</Text>
        </View>
        <Pressable
          onPress={onCloseHistory}
          style={styles.sidePanelCloseButton}
          testID="close-history-drawer-button"
        >
          <MaterialCommunityIcons
            name="chevron-left"
            size={22}
            color={colors.textPrimary}
          />
        </Pressable>
      </View>

      {exibirBusca ? (
        <View style={styles.historySummaryCard} testID="history-summary-card">
          <View style={styles.historySearchShell}>
            <MaterialCommunityIcons
              name="magnify"
              size={20}
              color={colors.textSecondary}
            />
            <TextInput
              onChangeText={onBuscaHistoricoChange}
              onBlur={() => onHistorySearchFocusChange(false)}
              onFocus={() => onHistorySearchFocusChange(true)}
              placeholder="Buscar histórico"
              placeholderTextColor={colors.textSecondary}
              style={styles.historySearchInput}
              testID="history-search-input"
              value={buscaHistorico}
            />
          </View>
          <View style={styles.historySummaryHeader}>
            <View style={styles.historySummaryCopy}>
              <Text style={styles.historySummaryEyebrow}>
                {buscaHistorico.trim() ? "Busca ativa" : "Retomada rapida"}
              </Text>
              <Text style={styles.historySummaryTitle}>Radar da operação</Text>
            </View>
            <Text style={styles.historySummaryCountLabel}>
              {pluralizeHistoryCases(totalVisiveis)}
            </Text>
          </View>
          <View style={styles.historySummaryMetricGrid}>
            <View style={styles.historySummaryMetricCard}>
              <Text style={styles.historySummaryMetricValue}>
                {totals.emAndamento}
              </Text>
              <Text style={styles.historySummaryMetricLabel}>em andamento</Text>
            </View>
            <View style={styles.historySummaryMetricCard}>
              <Text style={styles.historySummaryMetricValue}>
                {totals.mesa}
              </Text>
              <Text style={styles.historySummaryMetricLabel}>na mesa</Text>
            </View>
            <View style={styles.historySummaryMetricCard}>
              <Text style={styles.historySummaryMetricValue}>
                {totals.concluidos}
              </Text>
              <Text style={styles.historySummaryMetricLabel}>concluidos</Text>
            </View>
          </View>
          <View style={styles.historySummaryPills}>
            <View style={styles.historySummaryPill}>
              <Text style={styles.historySummaryPillText}>
                {totalFixados} fixados
              </Text>
            </View>
            <View style={styles.historySummaryPill}>
              <Text style={styles.historySummaryPillText}>
                {conversasOcultasTotal} ocultos
              </Text>
            </View>
          </View>
          <Text style={styles.historySummaryText}>
            {buildHistorySummaryText(itensVisiveis, buscaHistorico)}
          </Text>
        </View>
      ) : null}

      <ScrollView
        contentContainerStyle={styles.historySections}
        keyboardShouldPersistTaps="handled"
        testID={
          historicoAgrupadoFinal.length
            ? "history-results-loaded"
            : "history-results-empty"
        }
      >
        {historicoAgrupadoFinal.length ? (
          historicoAgrupadoFinal.map((section, sectionIndex) => (
            <View
              key={section.key}
              style={styles.historySection}
              testID={`history-section-${section.key}`}
            >
              <View style={styles.historySectionHeader}>
                <Text style={styles.historySectionTitle}>{section.title}</Text>
                <View style={styles.historySectionCountBadge}>
                  <Text style={styles.historySectionCountText}>
                    {section.items.length}
                  </Text>
                </View>
              </View>
              <View style={styles.historySectionItems}>
                {section.items.map((item, itemIndex) => {
                  const ativo = item.id === laudoSelecionadoId;
                  const isFirstHistoryItem =
                    sectionIndex === 0 && itemIndex === 0;
                  return (
                    <HistoryDrawerListItem
                      key={`history-${section.key}-${item.id}`}
                      ativo={ativo}
                      containerTestID={
                        isFirstHistoryItem
                          ? "history-first-item-button"
                          : undefined
                      }
                      isLastItem={itemIndex === section.items.length - 1}
                      item={item}
                      onExcluir={() => onExcluirConversaHistorico(item)}
                      onSelecionar={() => onSelecionarHistorico(item)}
                      testID={`history-item-${item.id}`}
                    />
                  );
                })}
                <View
                  collapsable={false}
                  pointerEvents="none"
                  style={{ height: 0, opacity: 0, width: 0 }}
                >
                  {section.items.map((item) => {
                    const ativo = item.id === laudoSelecionadoId;
                    return (
                      <View
                        key={`history-marker-${section.key}-${item.id}`}
                        collapsable={false}
                      >
                        <View
                          collapsable={false}
                          testID={`history-target-visible-${item.id}`}
                        />
                        {ativo ? (
                          <View
                            collapsable={false}
                            testID={`history-item-selected-${item.id}`}
                          />
                        ) : null}
                      </View>
                    );
                  })}
                </View>
              </View>
            </View>
          ))
        ) : (
          <View style={styles.historyEmptyState} testID="history-empty-state">
            <EmptyState
              compact
              description={historicoVazioTexto}
              icon="history"
              title={historicoVazioTitulo}
            />
          </View>
        )}
      </ScrollView>
    </Animated.View>
  );
}
