import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useEffect, type RefObject } from "react";
import {
  ActivityIndicator,
  ScrollView,
  Text,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from "react-native";

import {
  AssistantCitationList,
  AssistantMessageContent,
} from "../../components/AssistantRichMessage";
import { EmptyState } from "../../components/EmptyState";
import { colors } from "../../theme/tokens";
import type {
  MobileAttachment,
  MobileChatMessage,
  MobileMesaMessage,
  MobileReportPackDraft,
  MobileReviewPackage,
  MobileSurfaceAction,
} from "../../types/mobile";
import { styles } from "../InspectorMobileApp.styles";
import { MessageAttachmentCard, MessageReferenceCard } from "./MessageCards";
import { ehImagemAnexo } from "./attachmentUtils";
import { stripEmbeddedChatAiPreferences } from "./preferences";
import { renderizarReportPackDraftCard } from "./ThreadConversationReportPackDraftCard";
import { renderizarDocumentoEmitidoCard } from "./ThreadConversationIssuedDocumentCard";

interface ThreadConversationChatSurfaceProps {
  carregandoConversa: boolean;
  conversaVazia: boolean;
  keyboardVisible: boolean;
  threadKeyboardPaddingBottom: number;
  scrollRef: RefObject<ScrollView | null>;
  fluxoFormalAtivo: boolean;
  reviewPackage?: MobileReviewPackage | null;
  reportPackDraft?: MobileReportPackDraft | null;
  caseLifecycleStatus?: string;
  allowedSurfaceActions?: MobileSurfaceAction[];
  onAbrirMesaTab?: () => void;
  onAbrirQualityGate?: () => void | Promise<void>;
  onUsarPerguntaPreLaudo?: (value: string) => void;
  mensagensVisiveis: MobileChatMessage[];
  mensagensMesa: MobileMesaMessage[];
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
  mensagemChatDestacadaId: number | null;
  onRegistrarLayoutMensagemChat: (id: number | null, y: number) => void;
  dynamicMessageBubbleStyle: StyleProp<ViewStyle>;
  dynamicMessageTextStyle: StyleProp<TextStyle>;
  enviandoMensagem: boolean;
}

function buildLatestAssistantDocumentAttachmentKey(
  mensagens: MobileChatMessage[],
): string {
  let latestKey = "";

  mensagens.forEach((mensagem, messageIndex) => {
    if (mensagem.papel !== "assistente" || !Array.isArray(mensagem.anexos)) {
      return;
    }

    mensagem.anexos.forEach((anexo, attachmentIndex) => {
      if (ehImagemAnexo(anexo)) {
        return;
      }
      latestKey = `${mensagem.id ?? `msg-${messageIndex}`}:${attachmentIndex}`;
    });
  });

  return latestKey;
}

export function ThreadConversationChatSurface({
  carregandoConversa,
  conversaVazia,
  keyboardVisible,
  threadKeyboardPaddingBottom,
  scrollRef,
  fluxoFormalAtivo,
  reviewPackage,
  reportPackDraft,
  caseLifecycleStatus,
  allowedSurfaceActions,
  onAbrirMesaTab,
  onAbrirQualityGate,
  onUsarPerguntaPreLaudo,
  mensagensVisiveis,
  mensagensMesa,
  obterResumoReferenciaMensagem,
  onAbrirReferenciaNoChat,
  sessionAccessToken,
  onAbrirAnexo,
  anexoAbrindoChave,
  toAttachmentKey,
  mensagemChatDestacadaId,
  onRegistrarLayoutMensagemChat,
  dynamicMessageBubbleStyle,
  dynamicMessageTextStyle,
  enviandoMensagem,
}: ThreadConversationChatSurfaceProps) {
  const normalizarTextoRenderizado = (
    texto: string,
    options: { mensagemEhUsuario: boolean },
  ) =>
    stripEmbeddedChatAiPreferences(texto, {
      fallbackHiddenOnly: options.mensagemEhUsuario ? "Evidência enviada" : "",
    });

  useEffect(() => {
    if (mensagemChatDestacadaId) {
      return;
    }
    const timer = setTimeout(() => {
      scrollRef.current?.scrollToEnd({ animated: false });
    }, 80);
    return () => clearTimeout(timer);
  }, [
    carregandoConversa,
    mensagemChatDestacadaId,
    mensagensVisiveis.length,
    scrollRef,
  ]);

  if (carregandoConversa) {
    return (
      <View style={styles.loadingState}>
        <ActivityIndicator color={colors.accent} size="large" />
        <Text style={styles.loadingText}>
          Carregando a conversa do inspetor...
        </Text>
      </View>
    );
  }

  if (conversaVazia) {
    return (
      <View
        style={[
          styles.threadEmptyState,
          keyboardVisible ? styles.threadEmptyStateKeyboardVisible : null,
        ]}
      >
        <EmptyState compact icon="message-processing-outline" />
      </View>
    );
  }

  const latestAssistantDocumentAttachmentKey =
    buildLatestAssistantDocumentAttachmentKey(mensagensVisiveis);

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
      testID="chat-thread-surface"
    >
      {fluxoFormalAtivo
        ? renderizarDocumentoEmitidoCard(reviewPackage, caseLifecycleStatus)
        : null}
      {fluxoFormalAtivo
        ? renderizarReportPackDraftCard(reportPackDraft, {
            canFinalize: Boolean(
              allowedSurfaceActions?.includes("chat_finalize"),
            ),
            mode: "chat",
            onAbrirMesaTab,
            onAbrirQualityGate,
            onUsarPerguntaPreLaudo,
          })
        : null}
      {mensagensVisiveis.map((item, index) => {
        const mensagemEhUsuario = item.papel === "usuario";
        const mensagemEhEngenharia = item.papel === "engenheiro";
        const mensagemEhAssistente = item.papel === "assistente";
        const textoRenderizado = normalizarTextoRenderizado(item.texto, {
          mensagemEhUsuario,
        });
        const nomeAutor = mensagemEhEngenharia ? "Mesa" : "";
        const referenciaId = Number(item.referencia_mensagem_id || 0) || null;
        const referenciaPreview = obterResumoReferenciaMensagem(
          referenciaId,
          mensagensVisiveis,
          mensagensMesa,
        );
        const mensagemDestacada = Boolean(
          item.id && item.id === mensagemChatDestacadaId,
        );

        return (
          <View
            key={`${item.id ?? "placeholder"}-${index}`}
            onLayout={(event) =>
              onRegistrarLayoutMensagemChat(item.id, event.nativeEvent.layout.y)
            }
            style={[
              styles.messageRow,
              mensagemEhUsuario
                ? styles.messageRowOutgoing
                : styles.messageRowIncoming,
            ]}
          >
            {mensagemEhUsuario ? (
              <View
                style={[
                  styles.messageBubble,
                  styles.messageBubbleOutgoing,
                  mensagemDestacada ? styles.messageBubbleReferenced : null,
                ]}
              >
                {referenciaId ? (
                  <MessageReferenceCard
                    messageId={referenciaId}
                    onPress={() => onAbrirReferenciaNoChat(referenciaId)}
                    preview={referenciaPreview}
                    variant="outgoing"
                  />
                ) : null}
                <Text
                  style={[
                    styles.messageText,
                    styles.messageTextOutgoing,
                    dynamicMessageTextStyle,
                  ]}
                >
                  {textoRenderizado === "[imagem]"
                    ? "Imagem enviada"
                    : textoRenderizado}
                </Text>
                {item.anexos?.length ? (
                  <View style={styles.messageAttachments}>
                    {item.anexos.map((anexo, anexoIndex) => {
                      return (
                        <MessageAttachmentCard
                          key={`${item.id ?? "msg"}-anexo-${anexoIndex}`}
                          accessToken={sessionAccessToken}
                          attachment={anexo}
                          onPress={onAbrirAnexo}
                          opening={
                            anexoAbrindoChave ===
                            toAttachmentKey(
                              anexo,
                              `${item.id ?? "msg"}-anexo-${anexoIndex}`,
                            )
                          }
                        />
                      );
                    })}
                  </View>
                ) : null}
                {item.citacoes?.length ? (
                  <Text
                    style={[styles.messageMeta, styles.messageMetaOutgoing]}
                  >
                    {item.citacoes.length} referência
                    {item.citacoes.length > 1 ? "s" : ""} anexada
                  </Text>
                ) : null}
              </View>
            ) : (
              <View
                style={[
                  styles.messageIncomingCluster,
                  !mensagemEhEngenharia
                    ? styles.messageIncomingClusterAssistant
                    : null,
                ]}
              >
                {mensagemEhEngenharia ? (
                  <View
                    style={[
                      styles.messageAvatar,
                      styles.messageAvatarEngineering,
                    ]}
                  >
                    <MaterialCommunityIcons
                      color={colors.accent}
                      name="clipboard-check-outline"
                      size={16}
                    />
                  </View>
                ) : null}
                <View
                  style={[
                    styles.messageBubble,
                    styles.messageBubbleIncomingShell,
                    !mensagemEhEngenharia
                      ? styles.messageBubbleIncomingAssistant
                      : null,
                    mensagemEhEngenharia
                      ? styles.messageBubbleEngineering
                      : styles.messageBubbleIncoming,
                    mensagemDestacada ? styles.messageBubbleReferenced : null,
                    dynamicMessageBubbleStyle,
                  ]}
                >
                  {mensagemEhEngenharia ? (
                    <View style={styles.messageHeaderRow}>
                      <Text style={styles.messageAuthor}>{nomeAutor}</Text>
                      <View
                        style={[
                          styles.messageStatusBadge,
                          styles.messageStatusBadgeAccent,
                        ]}
                      >
                        <Text
                          style={[
                            styles.messageStatusBadgeText,
                            styles.messageStatusBadgeTextAccent,
                          ]}
                        >
                          Mesa
                        </Text>
                      </View>
                    </View>
                  ) : null}
                  {referenciaId ? (
                    <MessageReferenceCard
                      messageId={referenciaId}
                      onPress={() => onAbrirReferenciaNoChat(referenciaId)}
                      preview={referenciaPreview}
                    />
                  ) : null}
                  {mensagemEhAssistente ? (
                    <AssistantMessageContent
                      text={
                        textoRenderizado === "[imagem]"
                          ? "Imagem enviada"
                          : textoRenderizado
                      }
                      textStyle={[styles.messageText, dynamicMessageTextStyle]}
                    />
                  ) : (
                    <Text style={[styles.messageText, dynamicMessageTextStyle]}>
                      {textoRenderizado === "[imagem]"
                        ? "Imagem enviada"
                        : textoRenderizado}
                    </Text>
                  )}
                  {item.anexos?.length ? (
                    <View style={styles.messageAttachments}>
                      {item.anexos.map((anexo, anexoIndex) => {
                        const attachmentKey = `${
                          item.id ?? `msg-${index}`
                        }:${anexoIndex}`;
                        const latestAssistantDocumentAttachment =
                          mensagemEhAssistente &&
                          !ehImagemAnexo(anexo) &&
                          attachmentKey ===
                            latestAssistantDocumentAttachmentKey;

                        return (
                          <MessageAttachmentCard
                            key={`${item.id ?? "msg"}-anexo-${anexoIndex}`}
                            accessToken={sessionAccessToken}
                            attachment={anexo}
                            onPress={onAbrirAnexo}
                            opening={
                              anexoAbrindoChave ===
                              toAttachmentKey(
                                anexo,
                                `${item.id ?? "msg"}-anexo-${anexoIndex}`,
                              )
                            }
                            testID={
                              latestAssistantDocumentAttachment
                                ? "chat-last-assistant-document-attachment"
                                : undefined
                            }
                          />
                        );
                      })}
                    </View>
                  ) : null}
                  {mensagemEhAssistente ? (
                    <AssistantCitationList citations={item.citacoes} />
                  ) : item.citacoes?.length ? (
                    <Text style={styles.messageMeta}>
                      {item.citacoes.length} referência
                      {item.citacoes.length > 1 ? "s" : ""} anexada
                    </Text>
                  ) : null}
                </View>
              </View>
            )}
          </View>
        );
      })}

      {enviandoMensagem ? (
        <View style={styles.typingRow} testID="chat-thread-typing">
          <View style={styles.typingBubble}>
            <ActivityIndicator color={colors.accent} size="small" />
            <Text style={styles.typingText}>
              Assistente está respondendo...
            </Text>
          </View>
        </View>
      ) : null}
    </ScrollView>
  );
}
