import type { ComponentProps } from "react";
import {
  Animated,
  KeyboardAvoidingView,
  ScrollView,
  Text,
  View,
  type GestureResponderHandlers,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { SafeAreaView } from "react-native-safe-area-context";

import type { MobileLaudoCard } from "../types/mobile";
import { styles } from "./InspectorMobileApp.styles";
import { ThreadComposerPanel } from "./chat/ThreadComposerPanel";
import { ThreadConversationPane } from "./chat/ThreadConversationPane";
import { ThreadContextCard } from "./chat/ThreadContextCard";
import { ThreadHeaderControls } from "./chat/ThreadHeaderControls";
import { BrandLaunchOverlay } from "./common/BrandElements";
import {
  SessionModalsStack,
  type SessionModalsStackProps,
} from "./common/SessionModalsStack";
import { SidePanelsOverlay } from "./common/SidePanelsOverlay";
import {
  HistoryDrawerPanel,
  type HistoryDrawerPanelProps,
} from "./history/HistoryDrawerPanel";
import { SettingsDrawerPanel } from "./settings/SettingsDrawerPanel";

interface InspectorAuthenticatedLayoutProps {
  accentColor: string;
  animacoesAtivas: boolean;
  appGradientColors: readonly [string, string, ...string[]];
  chatKeyboardVerticalOffset: number;
  drawerOverlayOpacity: Animated.Value;
  erroConversa: string;
  erroLaudos: string;
  historyEdgePanHandlers: GestureResponderHandlers;
  historyOpen: boolean;
  introVisivel: boolean;
  keyboardAvoidingBehavior: "padding" | "height" | undefined;
  keyboardVisible: boolean;
  onClosePanels: () => void;
  onIntroDone: () => void;
  settingsDrawerVisible: boolean;
  settingsEdgePanHandlers: GestureResponderHandlers;
  settingsOpen: boolean;
  threadContextVisible: boolean;
  vendoFinalizacao: boolean;
  vendoMesa: boolean;
  mesaTemMensagens: boolean;
  threadHeaderControlsProps: ComponentProps<typeof ThreadHeaderControls>;
  threadContextCardProps: Omit<
    ComponentProps<typeof ThreadContextCard>,
    "visible"
  >;
  threadConversationPaneProps: ComponentProps<typeof ThreadConversationPane>;
  threadComposerPanelProps: Omit<
    ComponentProps<typeof ThreadComposerPanel>,
    "visible"
  >;
  historyDrawerPanelProps: HistoryDrawerPanelProps<MobileLaudoCard>;
  settingsDrawerPanelProps: ComponentProps<typeof SettingsDrawerPanel>;
  sessionModalsStackProps: SessionModalsStackProps;
}

export function InspectorAuthenticatedLayout({
  accentColor,
  animacoesAtivas,
  appGradientColors,
  chatKeyboardVerticalOffset,
  drawerOverlayOpacity,
  erroConversa,
  erroLaudos,
  historyEdgePanHandlers,
  historyOpen,
  introVisivel,
  keyboardAvoidingBehavior,
  keyboardVisible,
  onClosePanels,
  onIntroDone,
  settingsDrawerVisible,
  settingsEdgePanHandlers,
  settingsOpen,
  threadContextVisible,
  vendoFinalizacao,
  vendoMesa,
  mesaTemMensagens,
  threadHeaderControlsProps,
  threadContextCardProps,
  threadConversationPaneProps,
  threadComposerPanelProps,
  historyDrawerPanelProps,
  settingsDrawerPanelProps,
  sessionModalsStackProps,
}: InspectorAuthenticatedLayoutProps) {
  const entryChooserVisible =
    threadContextVisible && threadContextCardProps.layout === "entry_chooser";
  const mostrarPainelResumo =
    threadContextVisible &&
    (vendoFinalizacao || threadContextCardProps.layout === "entry_chooser");
  const ocultarComposer =
    vendoFinalizacao || threadContextCardProps.layout === "entry_chooser";

  return (
    <LinearGradient colors={appGradientColors} style={styles.gradient}>
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView
          style={styles.keyboard}
          behavior={keyboardAvoidingBehavior}
          keyboardVerticalOffset={chatKeyboardVerticalOffset}
        >
          <View style={styles.chatLayout}>
            <ThreadHeaderControls {...threadHeaderControlsProps} />

            <View
              style={[
                styles.chatPanel,
                keyboardVisible ? styles.chatPanelKeyboardVisible : null,
              ]}
            >
              {!!erroLaudos && (
                <Text style={styles.errorText}>{erroLaudos}</Text>
              )}
              {!!erroConversa && (
                <Text style={styles.errorText}>{erroConversa}</Text>
              )}

              <View
                style={[
                  styles.threadBody,
                  entryChooserVisible ? styles.threadBodyEntryChooser : null,
                  keyboardVisible ? styles.threadBodyKeyboardVisible : null,
                ]}
              >
                {mostrarPainelResumo ? (
                  <ScrollView
                    style={styles.threadScroll}
                    contentContainerStyle={[
                      styles.threadContent,
                      entryChooserVisible && !keyboardVisible
                        ? styles.threadContentEntryChooser
                        : null,
                      keyboardVisible ? styles.threadContentKeyboard : null,
                      keyboardVisible
                        ? {
                            paddingBottom:
                              threadConversationPaneProps.threadKeyboardPaddingBottom,
                          }
                        : null,
                    ]}
                    keyboardShouldPersistTaps="handled"
                    showsVerticalScrollIndicator={false}
                    testID="thread-context-pane"
                  >
                    <ThreadContextCard
                      {...threadContextCardProps}
                      defaultExpanded={vendoFinalizacao}
                      visible
                    />
                  </ScrollView>
                ) : (
                  <ThreadConversationPane {...threadConversationPaneProps} />
                )}
              </View>

              <ThreadComposerPanel
                {...threadComposerPanelProps}
                vendoMesa={vendoMesa}
                visible={!ocultarComposer && (!vendoMesa || mesaTemMensagens)}
              />
            </View>
          </View>

          <SidePanelsOverlay
            anyPanelOpen={historyOpen || settingsOpen}
            drawerOverlayOpacity={drawerOverlayOpacity}
            historyEdgePanHandlers={historyEdgePanHandlers}
            historyOpen={historyOpen}
            keyboardVisible={keyboardVisible}
            onClosePanels={onClosePanels}
            renderHistoryDrawer={() => (
              <HistoryDrawerPanel {...historyDrawerPanelProps} />
            )}
            renderSettingsDrawer={() =>
              settingsDrawerVisible ? (
                <SettingsDrawerPanel {...settingsDrawerPanelProps} />
              ) : null
            }
            settingsEdgePanHandlers={settingsEdgePanHandlers}
            settingsOpen={settingsOpen}
          />

          <SessionModalsStack {...sessionModalsStackProps} />
        </KeyboardAvoidingView>
      </SafeAreaView>
      <BrandLaunchOverlay
        accentColor={accentColor}
        animationsEnabled={animacoesAtivas}
        onDone={onIntroDone}
        visible={introVisivel}
      />
    </LinearGradient>
  );
}
