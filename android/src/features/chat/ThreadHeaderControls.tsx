import { MaterialCommunityIcons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";

import { colors } from "../../theme/tokens";
import { styles } from "../InspectorMobileApp.styles";

export interface ThreadHeaderControlsProps {
  chatHasActiveCase: boolean;
  finalizacaoDisponivel: boolean;
  headerSafeTopInset: number;
  keyboardVisible: boolean;
  mesaAcessoPermitido: boolean;
  onOpenNewChat: () => void;
  onOpenHistory: () => void;
  onOpenFinalizarTab: () => void;
  onOpenSettings: () => void;
  notificacoesNaoLidas: number;
  filaOfflineTotal: number;
  vendoFinalizacao: boolean;
  vendoMesa: boolean;
  onOpenChatTab: () => void;
  onOpenMesaTab: () => void;
  notificacoesMesaLaudoAtual: number;
}

export function ThreadHeaderControls({
  chatHasActiveCase,
  finalizacaoDisponivel,
  headerSafeTopInset,
  keyboardVisible,
  mesaAcessoPermitido,
  onOpenNewChat,
  onOpenHistory,
  onOpenFinalizarTab,
  onOpenSettings,
  notificacoesNaoLidas,
  filaOfflineTotal,
  vendoFinalizacao,
  vendoMesa,
  onOpenChatTab,
  onOpenMesaTab,
  notificacoesMesaLaudoAtual,
}: ThreadHeaderControlsProps) {
  type HeaderChip = {
    key: string;
    icon: keyof typeof MaterialCommunityIcons.glyphMap;
    label: string;
    accent: boolean;
  };

  const totalBadge = notificacoesNaoLidas + filaOfflineTotal;
  const blankChatEntry = !vendoMesa && !vendoFinalizacao && !chatHasActiveCase;
  const eyebrow = vendoFinalizacao
    ? "Entrega técnica"
    : vendoMesa
      ? "Mesa avaliadora"
      : blankChatEntry
        ? "Nova inspeção"
        : "Inspeção ativa";
  const title = vendoFinalizacao ? "Finalizar" : vendoMesa ? "Mesa" : "Chat";
  const compactHeader = keyboardVisible;
  const showNewChatShortcut = !vendoMesa && !vendoFinalizacao;
  const subtitle = vendoFinalizacao
    ? "Revise tudo do caso antes da conclusão."
    : vendoMesa
      ? notificacoesMesaLaudoAtual
        ? `${notificacoesMesaLaudoAtual} retorno${notificacoesMesaLaudoAtual === 1 ? "" : "s"} novo${notificacoesMesaLaudoAtual === 1 ? "" : "s"} da mesa.`
        : ""
      : blankChatEntry
        ? "Envie fotos, documentos ou contexto para iniciar a inspeção."
        : filaOfflineTotal
          ? `${filaOfflineTotal} pendência${filaOfflineTotal === 1 ? "" : "s"} pronta${filaOfflineTotal === 1 ? "" : "s"} para sincronizar.`
          : chatHasActiveCase
            ? "Fotos, contexto e anexos entram direto na análise e no laudo."
            : "";
  const statusChips = (
    vendoFinalizacao
      ? []
      : vendoMesa
        ? [
            notificacoesMesaLaudoAtual
              ? {
                  key: "mesa-novas",
                  icon: "bell-ring-outline" as const,
                  label: `${notificacoesMesaLaudoAtual} nova${notificacoesMesaLaudoAtual === 1 ? "" : "s"}`,
                  accent: true,
                }
              : null,
          ].filter(Boolean)
        : [
            filaOfflineTotal
              ? {
                  key: "chat-offline",
                  icon: "cloud-upload-outline" as const,
                  label: `${filaOfflineTotal} offline`,
                  accent: true,
                }
              : null,
          ].filter(Boolean)
  ) as HeaderChip[];

  return (
    <>
      <View
        style={[
          styles.chatHeader,
          headerSafeTopInset ? { paddingTop: headerSafeTopInset + 12 } : null,
          compactHeader ? styles.chatHeaderCompact : null,
        ]}
      >
        <View style={styles.cleanHeaderTopRow}>
          <Pressable
            hitSlop={12}
            onPress={onOpenHistory}
            style={[
              styles.cleanNavButton,
              compactHeader ? styles.cleanNavButtonCompact : null,
            ]}
            testID="open-history-button"
          >
            <MaterialCommunityIcons
              color={colors.textPrimary}
              name="menu"
              size={22}
            />
          </Pressable>

          {blankChatEntry ? (
            <View style={styles.cleanHeaderSpacer} />
          ) : (
            <View
              style={[
                styles.cleanHeaderCopy,
                compactHeader ? styles.cleanHeaderCopyCompact : null,
              ]}
            >
              {!compactHeader ? (
                <Text style={styles.cleanHeaderEyebrow}>{eyebrow}</Text>
              ) : null}
              <Text
                style={[
                  styles.cleanHeaderTitle,
                  compactHeader ? styles.cleanHeaderTitleCompact : null,
                ]}
              >
                {title}
              </Text>
              {subtitle && !compactHeader ? (
                <Text style={styles.cleanHeaderSubtitle}>{subtitle}</Text>
              ) : null}
            </View>
          )}

          <View style={styles.cleanHeaderActions}>
            {showNewChatShortcut ? (
              <Pressable
                hitSlop={12}
                onPress={onOpenNewChat}
                style={[
                  styles.cleanNavButton,
                  compactHeader ? styles.cleanNavButtonCompact : null,
                ]}
                testID="open-new-chat-button"
              >
                <MaterialCommunityIcons
                  color={colors.textPrimary}
                  name="square-edit-outline"
                  size={20}
                />
              </Pressable>
            ) : null}
            <Pressable
              hitSlop={12}
              onPress={onOpenSettings}
              style={[
                styles.cleanNavButton,
                compactHeader ? styles.cleanNavButtonCompact : null,
              ]}
              testID="open-settings-button"
            >
              <MaterialCommunityIcons
                color={colors.textPrimary}
                name="dots-horizontal"
                size={20}
              />
              {totalBadge ? (
                <View style={styles.cleanNavBadge}>
                  <Text style={styles.cleanNavBadgeText}>
                    {Math.min(totalBadge, 9)}
                    {totalBadge > 9 ? "+" : ""}
                  </Text>
                </View>
              ) : null}
            </Pressable>
          </View>
        </View>

        {!!statusChips.length && !compactHeader ? (
          <View style={styles.cleanHeaderStatusRow}>
            <View style={styles.cleanHeaderChipRail}>
              {statusChips.map((item) => (
                <View
                  key={item.key}
                  style={[
                    styles.cleanHeaderChip,
                    item.accent ? styles.cleanHeaderChipAccent : null,
                  ]}
                >
                  <MaterialCommunityIcons
                    color={item.accent ? colors.accent : colors.textSecondary}
                    name={item.icon}
                    size={14}
                  />
                  <Text
                    style={[
                      styles.cleanHeaderChipText,
                      item.accent ? styles.cleanHeaderChipTextAccent : null,
                    ]}
                  >
                    {item.label}
                  </Text>
                </View>
              ))}
            </View>
          </View>
        ) : null}
      </View>

      {blankChatEntry ? null : (
        <View
          style={[
            styles.cleanTabShell,
            compactHeader ? styles.cleanTabShellCompact : null,
          ]}
        >
          <View
            style={[
              styles.threadTabs,
              compactHeader ? styles.threadTabsCompact : null,
            ]}
          >
            <Pressable
              onPress={onOpenChatTab}
              style={[
                styles.threadTab,
                compactHeader ? styles.threadTabCompact : null,
                !vendoMesa && !vendoFinalizacao ? styles.threadTabActive : null,
              ]}
              testID="chat-tab-button"
            >
              <MaterialCommunityIcons
                color={
                  !vendoMesa && !vendoFinalizacao
                    ? colors.textPrimary
                    : colors.textSecondary
                }
                name="message-processing-outline"
                size={16}
              />
              <Text
                style={[
                  styles.threadTabText,
                  compactHeader ? styles.threadTabTextCompact : null,
                  !vendoMesa && !vendoFinalizacao
                    ? styles.threadTabTextActive
                    : null,
                ]}
              >
                Chat
              </Text>
            </Pressable>
            {mesaAcessoPermitido ? (
              <Pressable
                onPress={onOpenMesaTab}
                style={[
                  styles.threadTab,
                  compactHeader ? styles.threadTabCompact : null,
                  vendoMesa ? styles.threadTabActive : null,
                ]}
                testID="mesa-tab-button"
              >
                <MaterialCommunityIcons
                  color={vendoMesa ? colors.textPrimary : colors.textSecondary}
                  name="clipboard-text-outline"
                  size={16}
                />
                <Text
                  style={[
                    styles.threadTabText,
                    compactHeader ? styles.threadTabTextCompact : null,
                    vendoMesa ? styles.threadTabTextActive : null,
                  ]}
                >
                  Mesa
                </Text>
                {notificacoesMesaLaudoAtual ? (
                  <View
                    style={[
                      styles.threadTabBadge,
                      vendoMesa ? styles.threadTabBadgeActive : null,
                    ]}
                  >
                    <Text
                      style={[
                        styles.threadTabBadgeText,
                        vendoMesa ? styles.threadTabBadgeTextActive : null,
                      ]}
                    >
                      {notificacoesMesaLaudoAtual > 9
                        ? "9+"
                        : notificacoesMesaLaudoAtual}
                    </Text>
                  </View>
                ) : null}
              </Pressable>
            ) : null}
            {finalizacaoDisponivel ? (
              <Pressable
                onPress={onOpenFinalizarTab}
                style={[
                  styles.threadTab,
                  compactHeader ? styles.threadTabCompact : null,
                  vendoFinalizacao ? styles.threadTabActive : null,
                ]}
                testID="finalizar-tab-button"
              >
                <MaterialCommunityIcons
                  color={
                    vendoFinalizacao ? colors.textPrimary : colors.textSecondary
                  }
                  name="check-decagram-outline"
                  size={16}
                />
                <Text
                  style={[
                    styles.threadTabText,
                    compactHeader ? styles.threadTabTextCompact : null,
                    vendoFinalizacao ? styles.threadTabTextActive : null,
                  ]}
                >
                  Finalizar
                </Text>
              </Pressable>
            ) : null}
          </View>
        </View>
      )}
    </>
  );
}
