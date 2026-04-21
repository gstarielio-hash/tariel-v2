import type { Dispatch, MutableRefObject, SetStateAction } from "react";

import type { AppSettings } from "../../settings";
import type {
  MobileChatMessage,
  MobileChatMode,
  MobileChatSendResult,
  MobileLaudoCard,
} from "../../types/mobile";
import type { MobileSessionState } from "../session/sessionTypes";
import {
  guidedInspectionDraftToMobilePayload,
  type GuidedInspectionDraft,
} from "../inspection/guidedInspection";
import {
  resolverAllowedLifecycleTransitions,
  resolverAllowedNextLifecycleStatuses,
  resolverAllowedSurfaceActions,
} from "./caseLifecycle";
import { sendInspectorMessageFlow } from "./messageSendFlows";
import { gateHeavyTransfer } from "./network";
import type { ChatAiRequestConfig } from "./preferences";
import type {
  ChatCaseCreationState,
  ChatState,
  ComposerAttachment,
  OfflinePendingMessage,
} from "./types";
import { speakAssistantResponse } from "./voice";

type MessageControllerCurrent<TOfflineItem extends OfflinePendingMessage> = {
  session: MobileSessionState | null;
  conversation: ChatState | null;
  guidedInspectionDraft: GuidedInspectionDraft | null;
  message: string;
  attachmentDraft: ComposerAttachment | null;
  statusApi: string;
  wifiOnlySync: boolean;
  aiRequestConfig: ChatAiRequestConfig;
  speechSettings: AppSettings["speech"];
  setConversation: Dispatch<SetStateAction<ChatState | null>>;
  setMessage: Dispatch<SetStateAction<string>>;
  setAttachmentDraft: Dispatch<SetStateAction<ComposerAttachment | null>>;
  setErrorConversation: Dispatch<SetStateAction<string>>;
  setSendingMessage: Dispatch<SetStateAction<boolean>>;
  setCaseCreationState: Dispatch<SetStateAction<ChatCaseCreationState>>;
  setFilaOffline: Dispatch<SetStateAction<TOfflineItem[]>>;
  setStatusApi: (value: "online" | "offline") => void;
  criarItemFilaOffline: (params: {
    channel: "chat";
    operation?: OfflinePendingMessage["operation"];
    laudoId: number | null;
    text: string;
    title: string;
    attachment: ComposerAttachment | null;
    qualityGateDecision?: OfflinePendingMessage["qualityGateDecision"];
    guidedInspectionDraft?: OfflinePendingMessage["guidedInspectionDraft"];
    aiMode: MobileChatMode;
    aiSummary: string;
    aiMessagePrefix: string;
  }) => TOfflineItem;
  podeEditarConversaNoComposer: (
    conversa: ChatState | null | undefined,
  ) => boolean;
  textoFallbackAnexo: (anexo: ComposerAttachment | null) => string;
  normalizarModoChat: (
    modo: unknown,
    fallback?: MobileChatMode,
  ) => MobileChatMode;
  inferirSetorConversa: (conversa: ChatState | null | undefined) => string;
  montarHistoricoParaEnvio: (
    mensagens: MobileChatMessage[],
  ) => Array<{ papel: "usuario" | "assistente"; texto: string }>;
  criarMensagemAssistenteServidor: (
    resposta: MobileChatSendResult,
  ) => MobileChatMessage | null;
  criarConversaNova: () => ChatState;
  erroSugereModoOffline: (error: unknown) => boolean;
};

interface CreateInspectorChatMessageControllerParams<
  TOfflineItem extends OfflinePendingMessage,
> {
  paramsRef: MutableRefObject<MessageControllerCurrent<TOfflineItem>>;
  carregarConversaAtual: (
    accessToken: string,
    silencioso?: boolean,
  ) => Promise<ChatState | null>;
  carregarListaLaudos: (
    accessToken: string,
    silencioso?: boolean,
  ) => Promise<MobileLaudoCard[]>;
}

type MessageConversationMutationCurrent = {
  conversation: ChatState | null;
  speechSettings: AppSettings["speech"];
  setConversation: Dispatch<SetStateAction<ChatState | null>>;
  setCaseCreationState: Dispatch<SetStateAction<ChatCaseCreationState>>;
  normalizarModoChat: (
    modo: unknown,
    fallback?: MobileChatMode,
  ) => MobileChatMode;
  criarConversaNova: () => ChatState;
};

function aplicarMensagemOtimista(
  current: MessageConversationMutationCurrent,
  mensagemOtimista: MobileChatMessage,
  modoAtivo: MobileChatMode,
) {
  current.setConversation((estadoAtual) => ({
    laudoId: estadoAtual?.laudoId || null,
    estado: estadoAtual?.estado || "sem_relatorio",
    statusCard: estadoAtual?.statusCard || "aberto",
    permiteEdicao: estadoAtual?.permiteEdicao ?? true,
    permiteReabrir: estadoAtual?.permiteReabrir ?? false,
    laudoCard: estadoAtual?.laudoCard || null,
    caseLifecycleStatus: estadoAtual?.caseLifecycleStatus,
    caseWorkflowMode: estadoAtual?.caseWorkflowMode,
    activeOwnerRole: estadoAtual?.activeOwnerRole,
    allowedNextLifecycleStatuses: estadoAtual?.allowedNextLifecycleStatuses,
    allowedLifecycleTransitions: estadoAtual?.allowedLifecycleTransitions,
    allowedSurfaceActions: estadoAtual?.allowedSurfaceActions,
    attachmentPolicy: estadoAtual?.attachmentPolicy || null,
    reportPackDraft: estadoAtual?.reportPackDraft || null,
    reviewPackage: estadoAtual?.reviewPackage || null,
    modo: current.normalizarModoChat(estadoAtual?.modo, modoAtivo),
    mensagens: [...(estadoAtual?.mensagens || []), mensagemOtimista],
  }));
}

function aplicarRespostaAssistente(
  current: MessageConversationMutationCurrent,
  params: {
    creatingNewCase: boolean;
    respostaChat: MobileChatSendResult;
    mensagemAssistenteServidor: MobileChatMessage | null;
  },
) {
  const { creatingNewCase, respostaChat, mensagemAssistenteServidor } = params;
  const createdLaudoId =
    respostaChat.laudoId ?? current.conversation?.laudoId ?? null;
  current.setCaseCreationState(
    creatingNewCase && createdLaudoId ? "created" : "idle",
  );
  current.setConversation((estadoAtual) => {
    const base = estadoAtual || current.criarConversaNova();
    const proximaConversaBase = {
      ...base,
      laudoId: respostaChat.laudoId ?? base.laudoId,
      statusCard: respostaChat.laudoCard?.status_card || base.statusCard,
      laudoCard: respostaChat.laudoCard || base.laudoCard,
      caseLifecycleStatus:
        respostaChat.laudoCard?.case_lifecycle_status ||
        base.caseLifecycleStatus,
      caseWorkflowMode:
        respostaChat.laudoCard?.case_workflow_mode || base.caseWorkflowMode,
      activeOwnerRole:
        respostaChat.laudoCard?.active_owner_role || base.activeOwnerRole,
      allowedNextLifecycleStatuses:
        respostaChat.laudoCard?.allowed_next_lifecycle_statuses ||
        base.allowedNextLifecycleStatuses,
      allowedLifecycleTransitions:
        respostaChat.laudoCard?.allowed_lifecycle_transitions ||
        base.allowedLifecycleTransitions,
      allowedSurfaceActions:
        respostaChat.laudoCard?.allowed_surface_actions ||
        base.allowedSurfaceActions,
      reportPackDraft: base.reportPackDraft || null,
      modo: current.normalizarModoChat(
        respostaChat.modo,
        current.normalizarModoChat(base.modo),
      ),
      mensagens: mensagemAssistenteServidor
        ? [...base.mensagens, mensagemAssistenteServidor]
        : base.mensagens,
    };

    return {
      ...proximaConversaBase,
      allowedLifecycleTransitions: resolverAllowedLifecycleTransitions({
        conversation: proximaConversaBase,
        card: proximaConversaBase.laudoCard,
      }),
      allowedNextLifecycleStatuses: resolverAllowedNextLifecycleStatuses({
        conversation: proximaConversaBase,
        card: proximaConversaBase.laudoCard,
      }),
      allowedSurfaceActions: resolverAllowedSurfaceActions({
        conversation: proximaConversaBase,
        card: proximaConversaBase.laudoCard,
      }),
    };
  });
  void speakAssistantResponse({
    text: respostaChat.assistantText,
    speech: current.speechSettings,
  });
}

export function createInspectorChatMessageController<
  TOfflineItem extends OfflinePendingMessage,
>({
  paramsRef,
  carregarConversaAtual,
  carregarListaLaudos,
}: CreateInspectorChatMessageControllerParams<TOfflineItem>) {
  async function handleEnviarMensagem() {
    const current = paramsRef.current;
    if (!current.session) {
      return;
    }

    const snapshotConversa = current.conversation;
    const creatingNewCase = !snapshotConversa?.laudoId;
    const gateAnexo = await gateHeavyTransfer({
      wifiOnlySync: current.wifiOnlySync,
      requiresHeavyTransfer: Boolean(current.attachmentDraft),
      blockedMessage:
        "Anexos foram guardados na fila local e so seguem quando houver Wi-Fi.",
    });
    if (current.attachmentDraft && !gateAnexo.allowed) {
      current.setCaseCreationState(creatingNewCase ? "queued_offline" : "idle");
      current.setFilaOffline((estadoAtual) => [
        ...estadoAtual,
        current.criarItemFilaOffline({
          channel: "chat",
          laudoId: snapshotConversa?.laudoId ?? null,
          text: current.message.trim(),
          title: snapshotConversa?.laudoCard?.titulo || "Nova inspecao",
          attachment: current.attachmentDraft,
          guidedInspectionDraft: current.guidedInspectionDraft
            ? guidedInspectionDraftToMobilePayload(
                current.guidedInspectionDraft,
              )
            : null,
          aiMode: current.aiRequestConfig.mode,
          aiSummary: current.aiRequestConfig.summaryLabel,
          aiMessagePrefix: current.aiRequestConfig.messagePrefix,
        }),
      ]);
      current.setMessage("");
      current.setAttachmentDraft(null);
      current.setErrorConversation(
        gateAnexo.reason || "Envio local guardado para sincronizar depois.",
      );
      return;
    }

    current.setCaseCreationState(creatingNewCase ? "creating" : "idle");

    await sendInspectorMessageFlow<TOfflineItem>({
      mensagem: current.message,
      anexoAtual: current.attachmentDraft,
      snapshotConversa,
      guidedInspectionDraft: current.guidedInspectionDraft,
      aiRequestConfig: current.aiRequestConfig,
      sessionAccessToken: current.session.accessToken,
      statusApi: current.statusApi,
      podeEditarConversaNoComposer: current.podeEditarConversaNoComposer,
      textoFallbackAnexo: current.textoFallbackAnexo,
      normalizarModoChat: current.normalizarModoChat,
      inferirSetorConversa: current.inferirSetorConversa,
      montarHistoricoParaEnvio: current.montarHistoricoParaEnvio,
      criarMensagemAssistenteServidor: current.criarMensagemAssistenteServidor,
      carregarConversaAtual: async () => {
        await carregarConversaAtual(current.session!.accessToken, true);
      },
      carregarListaLaudos: async () => {
        await carregarListaLaudos(current.session!.accessToken, true);
      },
      erroSugereModoOffline: current.erroSugereModoOffline,
      criarItemFilaOffline: current.criarItemFilaOffline,
      onSetMensagem: current.setMessage,
      onSetAnexoRascunho: current.setAttachmentDraft,
      onSetErroConversa: current.setErrorConversation,
      onSetEnviandoMensagem: current.setSendingMessage,
      onApplyOptimisticMessage: (mensagemOtimista, modoAtivo) => {
        aplicarMensagemOtimista(current, mensagemOtimista, modoAtivo);
      },
      onApplyAssistantResponse: (respostaChat, mensagemAssistenteServidor) => {
        aplicarRespostaAssistente(current, {
          creatingNewCase,
          respostaChat,
          mensagemAssistenteServidor,
        });
      },
      onReverterConversa: () => {
        current.setCaseCreationState("idle");
        current.setConversation(snapshotConversa);
      },
      onQueueOfflineItem: (itemFila) => {
        if (creatingNewCase) {
          current.setCaseCreationState("queued_offline");
        }
        current.setFilaOffline((estadoAtual) => [...estadoAtual, itemFila]);
      },
      onSetStatusOffline: () => {
        current.setStatusApi("offline");
      },
      onRestoreDraft: (texto, anexo) => {
        if (creatingNewCase) {
          current.setCaseCreationState("error");
        }
        current.setMessage(texto);
        current.setAttachmentDraft(anexo);
      },
    });
  }

  return { handleEnviarMensagem };
}
