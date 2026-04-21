import {
  ActivityIndicator,
  ScrollView,
  Text,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from "react-native";
import type { RefObject } from "react";

import { EmptyState } from "../../components/EmptyState";
import type {
  MobileAttachment,
  MobileChatMessage,
  MobileLifecycleTransition,
  MobileMesaMessage,
  MobileMesaReviewCommandPayload,
  MobileReportPackDraft,
  MobileReviewPackage,
  MobileSurfaceAction,
} from "../../types/mobile";
import { styles } from "../InspectorMobileApp.styles";
import { ThreadConversationMesaMessageList } from "./ThreadConversationMesaMessageList";
import { renderizarReportPackDraftCard } from "./ThreadConversationReportPackDraftCard";
import { renderizarReviewPackageMesa } from "./ThreadConversationReviewPackageCard";

interface ThreadConversationMesaSurfaceProps {
  carregandoMesa: boolean;
  mensagensMesa: MobileMesaMessage[];
  reportPackDraft?: MobileReportPackDraft | null;
  reviewPackage?: MobileReviewPackage | null;
  caseLifecycleStatus?: string;
  activeOwnerRole?: string;
  allowedNextLifecycleStatuses?: string[];
  allowedLifecycleTransitions?: MobileLifecycleTransition[];
  allowedSurfaceActions?: MobileSurfaceAction[];
  mesaAcessoPermitido: boolean;
  mesaDisponivel: boolean;
  mesaIndisponivelDescricao: string;
  mesaIndisponivelTitulo: string;
  scrollRef: RefObject<ScrollView | null>;
  keyboardVisible: boolean;
  threadKeyboardPaddingBottom: number;
  nomeUsuarioExibicao: string;
  mensagensVisiveis: MobileChatMessage[];
  obterResumoReferenciaMensagem: (
    referenciaId: number | null,
    mensagensVisiveis: MobileChatMessage[],
    mensagensMesa: MobileMesaMessage[],
  ) => string;
  onAbrirReferenciaNoChat: (id: number) => void;
  sessionAccessToken: string | null;
  onAbrirAnexo: (attachment: MobileAttachment) => void;
  anexoAbrindoChave: string;
  toAttachmentKey: (attachment: MobileAttachment, fallback: string) => string;
  conversaPermiteEdicao: boolean;
  onDefinirReferenciaMesaAtiva: (item: MobileMesaMessage) => void;
  accentColor: string;
  dynamicMessageBubbleStyle: StyleProp<ViewStyle>;
  dynamicMessageTextStyle: StyleProp<TextStyle>;
  onExecutarComandoRevisaoMobile?: (
    payload: MobileMesaReviewCommandPayload,
  ) => Promise<void>;
  reviewCommandBusy?: boolean;
}

export function ThreadConversationMesaSurface({
  carregandoMesa,
  mensagensMesa,
  reportPackDraft,
  reviewPackage,
  caseLifecycleStatus,
  activeOwnerRole,
  allowedNextLifecycleStatuses,
  allowedLifecycleTransitions,
  allowedSurfaceActions,
  mesaAcessoPermitido,
  mesaDisponivel,
  mesaIndisponivelDescricao,
  mesaIndisponivelTitulo,
  scrollRef,
  keyboardVisible,
  threadKeyboardPaddingBottom,
  nomeUsuarioExibicao,
  mensagensVisiveis,
  obterResumoReferenciaMensagem,
  onAbrirReferenciaNoChat,
  sessionAccessToken,
  onAbrirAnexo,
  anexoAbrindoChave,
  toAttachmentKey,
  conversaPermiteEdicao,
  onDefinirReferenciaMesaAtiva,
  accentColor,
  dynamicMessageBubbleStyle,
  dynamicMessageTextStyle,
  onExecutarComandoRevisaoMobile,
  reviewCommandBusy = false,
}: ThreadConversationMesaSurfaceProps) {
  if (!mesaAcessoPermitido) {
    return (
      <View
        testID="mesa-thread-surface"
        style={[
          styles.threadEmptyState,
          keyboardVisible ? styles.threadEmptyStateKeyboardVisible : null,
        ]}
      >
        <View testID="mesa-thread-blocked">
          <EmptyState
            compact
            description={mesaIndisponivelDescricao}
            eyebrow="Mesa"
            icon="shield-lock-outline"
            tone="default"
            title={mesaIndisponivelTitulo}
          />
        </View>
      </View>
    );
  }

  if (carregandoMesa && !mensagensMesa.length) {
    return (
      <View testID="mesa-thread-surface" style={styles.loadingState}>
        <View testID="mesa-thread-loading">
          <ActivityIndicator color={accentColor} size="large" />
          <Text style={styles.loadingText}>
            Abrindo a conversa com a mesa...
          </Text>
        </View>
      </View>
    );
  }

  if (!mesaDisponivel) {
    return (
      <View
        testID="mesa-thread-surface"
        style={[
          styles.threadEmptyState,
          keyboardVisible ? styles.threadEmptyStateKeyboardVisible : null,
        ]}
      >
        <View testID="mesa-thread-unavailable">
          <EmptyState
            compact
            description={mesaIndisponivelDescricao}
            eyebrow="Mesa"
            icon="clipboard-clock-outline"
            tone="accent"
            title={mesaIndisponivelTitulo}
          />
        </View>
      </View>
    );
  }

  return (
    <ScrollView
      ref={scrollRef}
      style={styles.threadScroll}
      contentContainerStyle={[
        styles.threadContent,
        keyboardVisible ? styles.threadContentKeyboard : null,
        keyboardVisible ? { paddingBottom: threadKeyboardPaddingBottom } : null,
      ]}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
      testID="mesa-thread-surface"
    >
      {renderizarReviewPackageMesa(
        reviewPackage,
        {
          caseLifecycleStatus,
          activeOwnerRole,
          allowedNextLifecycleStatuses,
          allowedLifecycleTransitions,
          allowedSurfaceActions,
        },
        onExecutarComandoRevisaoMobile,
        reviewCommandBusy,
      ) ||
        renderizarReportPackDraftCard(reportPackDraft, {
          mode: "mesa",
          testID: "mesa-report-pack-card",
        })}
      <ThreadConversationMesaMessageList
        accentColor={accentColor}
        anexoAbrindoChave={anexoAbrindoChave}
        conversaPermiteEdicao={conversaPermiteEdicao}
        dynamicMessageBubbleStyle={dynamicMessageBubbleStyle}
        dynamicMessageTextStyle={dynamicMessageTextStyle}
        keyboardVisible={keyboardVisible}
        mensagensMesa={mensagensMesa}
        mensagensVisiveis={mensagensVisiveis}
        nomeUsuarioExibicao={nomeUsuarioExibicao}
        obterResumoReferenciaMensagem={obterResumoReferenciaMensagem}
        onAbrirAnexo={onAbrirAnexo}
        onAbrirReferenciaNoChat={onAbrirReferenciaNoChat}
        onDefinirReferenciaMesaAtiva={onDefinirReferenciaMesaAtiva}
        sessionAccessToken={sessionAccessToken}
        toAttachmentKey={toAttachmentKey}
      />
    </ScrollView>
  );
}
