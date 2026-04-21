import { MaterialCommunityIcons } from "@expo/vector-icons";
import {
  Pressable,
  Text,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from "react-native";

import { EmptyState } from "../../components/EmptyState";
import { colors } from "../../theme/tokens";
import type {
  MobileAttachment,
  MobileChatMessage,
  MobileMesaMessage,
} from "../../types/mobile";
import { styles } from "../InspectorMobileApp.styles";
import { MessageAttachmentCard, MessageReferenceCard } from "./MessageCards";

function obterEstadoPendenciaMesa(
  item: MobileMesaMessage,
): "not_applicable" | "open" | "resolved" {
  if (
    item.pendency_state === "open" ||
    item.pendency_state === "resolved" ||
    item.pendency_state === "not_applicable"
  ) {
    return item.pendency_state;
  }
  const mensagemEhMesa =
    item.item_kind === "pendency" ||
    item.message_kind === "mesa_pendency" ||
    item.tipo === "humano_eng";
  if (!mensagemEhMesa) {
    return "not_applicable";
  }
  return item.resolvida_em ? "resolved" : "open";
}

function mensagemMesaEhUsuario(item: MobileMesaMessage): boolean {
  return (
    item.message_kind === "inspector_whisper" ||
    item.message_kind === "inspector_message" ||
    item.item_kind === "whisper" ||
    item.tipo === "humano_insp"
  );
}

function mensagemMesaEhPendencia(item: MobileMesaMessage): boolean {
  return (
    item.item_kind === "pendency" ||
    item.message_kind === "mesa_pendency" ||
    item.tipo === "humano_eng"
  );
}

function obterContextoOperacionalMesa(item: MobileMesaMessage): {
  title: string;
  summary: string;
  requiredAction: string;
  replyModeLabel: string;
  failureReasons: string[];
} | null {
  const raw = item.operational_context;
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const record = raw as Record<string, unknown>;
  if (String(record.task_kind || "").trim() !== "coverage_return_request") {
    return null;
  }
  return {
    title: String(record.title || "").trim() || "Item de cobertura",
    summary: String(record.summary || "").trim(),
    requiredAction: String(record.required_action || "").trim(),
    replyModeLabel:
      String(record.expected_reply_mode_label || "").trim() || "resposta livre",
    failureReasons: Array.isArray(record.failure_reasons)
      ? record.failure_reasons.filter(
          (value): value is string =>
            typeof value === "string" && value.trim().length > 0,
        )
      : [],
  };
}

type ThreadConversationMesaMessageListProps = {
  accentColor: string;
  anexoAbrindoChave: string;
  conversaPermiteEdicao: boolean;
  dynamicMessageBubbleStyle: StyleProp<ViewStyle>;
  dynamicMessageTextStyle: StyleProp<TextStyle>;
  keyboardVisible: boolean;
  mensagensMesa: MobileMesaMessage[];
  mensagensVisiveis: MobileChatMessage[];
  nomeUsuarioExibicao: string;
  obterResumoReferenciaMensagem: (
    referenciaId: number | null,
    mensagensVisiveis: MobileChatMessage[],
    mensagensMesa: MobileMesaMessage[],
  ) => string;
  onAbrirAnexo: (attachment: MobileAttachment) => void;
  onAbrirReferenciaNoChat: (id: number) => void;
  onDefinirReferenciaMesaAtiva: (item: MobileMesaMessage) => void;
  sessionAccessToken: string | null;
  toAttachmentKey: (attachment: MobileAttachment, fallback: string) => string;
};

type MesaMessageSharedProps = Pick<
  ThreadConversationMesaMessageListProps,
  | "anexoAbrindoChave"
  | "dynamicMessageTextStyle"
  | "onAbrirAnexo"
  | "onAbrirReferenciaNoChat"
  | "sessionAccessToken"
  | "toAttachmentKey"
> & {
  item: MobileMesaMessage;
  referenciaId: number | null;
  referenciaPreview: string;
};

function MesaMessageAttachments(
  props: Pick<
    ThreadConversationMesaMessageListProps,
    | "anexoAbrindoChave"
    | "onAbrirAnexo"
    | "sessionAccessToken"
    | "toAttachmentKey"
  > & {
    attachments: MobileAttachment[] | null | undefined;
    messageId: number | string;
  },
) {
  const {
    anexoAbrindoChave,
    attachments,
    messageId,
    onAbrirAnexo,
    sessionAccessToken,
    toAttachmentKey,
  } = props;

  if (!attachments?.length) {
    return null;
  }

  return (
    <View style={styles.messageAttachments}>
      {attachments.map((anexo, anexoIndex) => {
        const fallback = `${messageId}-anexo-${anexoIndex}`;
        return (
          <MessageAttachmentCard
            key={fallback}
            accessToken={sessionAccessToken}
            attachment={anexo}
            onPress={onAbrirAnexo}
            opening={anexoAbrindoChave === toAttachmentKey(anexo, fallback)}
          />
        );
      })}
    </View>
  );
}

function MesaOutgoingMessageBubble(
  props: MesaMessageSharedProps & {
    dynamicMessageBubbleStyle: StyleProp<ViewStyle>;
    nomeAutor: string;
  },
) {
  const {
    anexoAbrindoChave,
    dynamicMessageBubbleStyle,
    dynamicMessageTextStyle,
    item,
    nomeAutor,
    onAbrirAnexo,
    onAbrirReferenciaNoChat,
    referenciaId,
    referenciaPreview,
    sessionAccessToken,
    toAttachmentKey,
  } = props;

  return (
    <View
      style={[
        styles.messageBubble,
        styles.messageBubbleOutgoing,
        dynamicMessageBubbleStyle,
      ]}
    >
      <Text style={[styles.messageAuthor, styles.messageAuthorOutgoing]}>
        {nomeAutor}
      </Text>
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
        {item.texto}
      </Text>
      <MesaMessageAttachments
        anexoAbrindoChave={anexoAbrindoChave}
        attachments={item.anexos}
        messageId={item.id}
        onAbrirAnexo={onAbrirAnexo}
        sessionAccessToken={sessionAccessToken}
        toAttachmentKey={toAttachmentKey}
      />
      <Text style={[styles.messageMeta, styles.messageMetaOutgoing]}>
        {item.data}
        {item.resolvida_em_label
          ? ` • resolvida em ${item.resolvida_em_label}`
          : ""}
      </Text>
    </View>
  );
}

function MesaIncomingMessageBubble(
  props: MesaMessageSharedProps & {
    accentColor: string;
    conversaPermiteEdicao: boolean;
    nomeAutor: string;
    onDefinirReferenciaMesaAtiva: (item: MobileMesaMessage) => void;
  },
) {
  const {
    accentColor,
    anexoAbrindoChave,
    conversaPermiteEdicao,
    dynamicMessageTextStyle,
    item,
    nomeAutor,
    onAbrirAnexo,
    onAbrirReferenciaNoChat,
    onDefinirReferenciaMesaAtiva,
    referenciaId,
    referenciaPreview,
    sessionAccessToken,
    toAttachmentKey,
  } = props;
  const mensagemEhMesa = mensagemMesaEhPendencia(item);
  const estadoPendencia = obterEstadoPendenciaMesa(item);
  const operationalContext = obterContextoOperacionalMesa(item);

  return (
    <View style={styles.messageIncomingCluster}>
      <View style={[styles.messageAvatar, styles.messageAvatarMesa]}>
        <MaterialCommunityIcons
          color={accentColor}
          name="clipboard-text-outline"
          size={16}
        />
      </View>
      <View
        style={[
          styles.messageBubble,
          styles.messageBubbleIncomingShell,
          mensagemEhMesa
            ? styles.messageBubbleEngineering
            : styles.messageBubbleIncoming,
        ]}
      >
        <View style={styles.messageHeaderRow}>
          <Text style={styles.messageAuthor}>{nomeAutor}</Text>
          <View
            style={[
              styles.messageStatusBadge,
              estadoPendencia === "resolved"
                ? styles.messageStatusBadgeSuccess
                : styles.messageStatusBadgeAccent,
            ]}
          >
            <Text
              style={[
                styles.messageStatusBadgeText,
                estadoPendencia === "resolved"
                  ? styles.messageStatusBadgeTextSuccess
                  : styles.messageStatusBadgeTextAccent,
              ]}
            >
              {estadoPendencia === "resolved"
                ? "Resolvida"
                : estadoPendencia === "open"
                  ? "Pendência aberta"
                  : "Mensagem da mesa"}
            </Text>
          </View>
        </View>
        {referenciaId ? (
          <MessageReferenceCard
            messageId={referenciaId}
            onPress={() => onAbrirReferenciaNoChat(referenciaId)}
            preview={referenciaPreview}
          />
        ) : null}
        {operationalContext ? (
          <View style={styles.messageOperationalCard}>
            <Text style={styles.messageOperationalEyebrow}>
              Refazer operacional
            </Text>
            <Text style={styles.messageOperationalTitle}>
              {operationalContext.title}
            </Text>
            {operationalContext.summary ? (
              <Text style={styles.messageOperationalText}>
                {operationalContext.summary}
              </Text>
            ) : null}
            {operationalContext.requiredAction ? (
              <Text style={styles.messageOperationalText}>
                Ação esperada: {operationalContext.requiredAction}
              </Text>
            ) : null}
            <Text style={styles.messageOperationalMeta}>
              Resposta esperada: {operationalContext.replyModeLabel}
            </Text>
            {operationalContext.failureReasons.length ? (
              <Text style={styles.messageOperationalMeta}>
                Motivos: {operationalContext.failureReasons.join(", ")}
              </Text>
            ) : null}
          </View>
        ) : null}
        <Text style={[styles.messageText, dynamicMessageTextStyle]}>
          {item.texto}
        </Text>
        <MesaMessageAttachments
          anexoAbrindoChave={anexoAbrindoChave}
          attachments={item.anexos}
          messageId={item.id}
          onAbrirAnexo={onAbrirAnexo}
          sessionAccessToken={sessionAccessToken}
          toAttachmentKey={toAttachmentKey}
        />
        {conversaPermiteEdicao ? (
          <View style={styles.messageActionRow}>
            <Pressable
              onPress={() => onDefinirReferenciaMesaAtiva(item)}
              style={styles.messageActionButton}
            >
              <MaterialCommunityIcons
                name="reply-outline"
                size={15}
                color={colors.accent}
              />
              <Text style={styles.messageActionText}>
                Responder nesta mensagem
              </Text>
            </Pressable>
          </View>
        ) : null}
        <Text style={styles.messageMeta}>
          {item.data}
          {item.resolvida_em_label
            ? ` • resolvida em ${item.resolvida_em_label}`
            : ""}
        </Text>
      </View>
    </View>
  );
}

export function ThreadConversationMesaMessageList(
  props: ThreadConversationMesaMessageListProps,
) {
  const {
    accentColor,
    anexoAbrindoChave,
    conversaPermiteEdicao,
    dynamicMessageBubbleStyle,
    dynamicMessageTextStyle,
    keyboardVisible,
    mensagensMesa,
    mensagensVisiveis,
    nomeUsuarioExibicao,
    obterResumoReferenciaMensagem,
    onAbrirAnexo,
    onAbrirReferenciaNoChat,
    onDefinirReferenciaMesaAtiva,
    sessionAccessToken,
    toAttachmentKey,
  } = props;

  if (!mensagensMesa.length) {
    return (
      <View
        testID="mesa-thread-empty-state"
        style={[
          styles.threadEmptyState,
          keyboardVisible ? styles.threadEmptyStateKeyboardVisible : null,
        ]}
      >
        <EmptyState
          compact
          description="Quando a mesa responder, os retornos aparecem aqui."
          eyebrow="Mesa"
          icon="message-reply-text-outline"
          title="Nenhum retorno técnico"
        />
      </View>
    );
  }

  return (
    <View testID="mesa-thread-loaded">
      {mensagensMesa.map((item, index) => {
        const mensagemEhUsuario = mensagemMesaEhUsuario(item);
        const nomeAutor = mensagemEhUsuario ? nomeUsuarioExibicao : "Mesa";
        const referenciaId = Number(item.referencia_mensagem_id || 0) || null;
        const referenciaPreview = obterResumoReferenciaMensagem(
          referenciaId,
          mensagensVisiveis,
          mensagensMesa,
        );

        return (
          <View
            key={`${item.id}-${index}`}
            style={[
              styles.messageRow,
              mensagemEhUsuario
                ? styles.messageRowOutgoing
                : styles.messageRowIncoming,
            ]}
          >
            {mensagemEhUsuario ? (
              <MesaOutgoingMessageBubble
                anexoAbrindoChave={anexoAbrindoChave}
                dynamicMessageBubbleStyle={dynamicMessageBubbleStyle}
                dynamicMessageTextStyle={dynamicMessageTextStyle}
                item={item}
                nomeAutor={nomeAutor}
                onAbrirAnexo={onAbrirAnexo}
                onAbrirReferenciaNoChat={onAbrirReferenciaNoChat}
                referenciaId={referenciaId}
                referenciaPreview={referenciaPreview}
                sessionAccessToken={sessionAccessToken}
                toAttachmentKey={toAttachmentKey}
              />
            ) : (
              <MesaIncomingMessageBubble
                accentColor={accentColor}
                anexoAbrindoChave={anexoAbrindoChave}
                conversaPermiteEdicao={conversaPermiteEdicao}
                dynamicMessageTextStyle={dynamicMessageTextStyle}
                item={item}
                nomeAutor={nomeAutor}
                onAbrirAnexo={onAbrirAnexo}
                onAbrirReferenciaNoChat={onAbrirReferenciaNoChat}
                onDefinirReferenciaMesaAtiva={onDefinirReferenciaMesaAtiva}
                referenciaId={referenciaId}
                referenciaPreview={referenciaPreview}
                sessionAccessToken={sessionAccessToken}
                toAttachmentKey={toAttachmentKey}
              />
            )}
          </View>
        );
      })}
    </View>
  );
}
