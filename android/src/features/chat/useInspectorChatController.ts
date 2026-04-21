import {
  useRef,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
} from "react";
import { Alert, type ScrollView } from "react-native";

import { reabrirLaudoMobile } from "../../config/api";
import type {
  MobileActiveOwnerRole,
  MobileAttachmentPolicy,
  MobileChatMessage,
  MobileChatMode,
  MobileChatSendResult,
  MobileCaseLifecycleStatus,
  MobileCaseWorkflowMode,
  MobileEstadoLaudo,
  MobileLaudoCard,
  MobileLifecycleTransition,
  MobileLaudoMensagensResponse,
  MobileQualityGateResponse,
  MobileReportPackDraft,
  MobileLaudoStatusResponse,
  MobileMesaMessage,
  MobileSurfaceAction,
} from "../../types/mobile";
import { type AppSettings } from "../../settings";
import { createInspectorChatCaseController } from "./inspectorChatCaseController";
import { createInspectorChatMessageController } from "./inspectorChatMessageController";
import { createInspectorChatNavigationController } from "./inspectorChatNavigationController";
import { createInspectorChatQualityGateController } from "./inspectorChatQualityGateController";
import { restaurarContextoGuiadoDoCaso } from "./inspectorChatGuidedDraftSync";
import {
  conversaTemDocumentoEmitidoAtivo,
  resolverLaudoIdOperacional,
  solicitarPoliticaDocumentoEmitido,
} from "./inspectorChatReopen";
import { useInspectorChatControllerEffects } from "./useInspectorChatControllerEffects";
import type {
  ActiveThread,
  ChatCaseCreationState,
  ChatState,
  ComposerAttachment,
  OfflinePendingMessage,
} from "./types";
import type { ChatAiRequestConfig } from "./preferences";
import type { MobileSessionState } from "../session/sessionTypes";
import { type GuidedInspectionDraft } from "../inspection/guidedInspection";
import type { StartGuidedInspectionOptions } from "../inspection/useInspectorRootGuidedInspectionController";

interface ChatCacheState {
  laudos: MobileLaudoCard[];
  conversaAtual: ChatState | null;
  conversasPorLaudo: Record<string, ChatState>;
  mesaPorLaudo: Record<string, MobileMesaMessage[]>;
  guidedInspectionDrafts?: Record<string, GuidedInspectionDraft>;
  updatedAt: string;
}

interface UpdateConversationSummaryPayload {
  estado: MobileEstadoLaudo | string;
  permite_edicao: boolean;
  permite_reabrir: boolean;
  case_lifecycle_status?: MobileCaseLifecycleStatus;
  case_workflow_mode?: MobileCaseWorkflowMode;
  active_owner_role?: MobileActiveOwnerRole;
  allowed_next_lifecycle_statuses?: string[];
  allowed_lifecycle_transitions?: MobileLifecycleTransition[];
  allowed_surface_actions?: MobileSurfaceAction[];
  attachment_policy?: MobileAttachmentPolicy | null;
  laudo_card: MobileLaudoCard | null;
  report_pack_draft?: MobileReportPackDraft | null;
  modo?: MobileChatMode | string;
}

interface UseInspectorChatControllerParams<
  TOfflineItem extends OfflinePendingMessage,
  TCacheLeitura extends ChatCacheState,
> {
  session: MobileSessionState | null;
  sessionLoading: boolean;
  activeThread: ActiveThread;
  entryModePreference?: AppSettings["ai"]["entryModePreference"];
  rememberLastCaseMode?: boolean;
  statusApi: string;
  wifiOnlySync: boolean;
  aiRequestConfig: ChatAiRequestConfig;
  speechSettings: AppSettings["speech"];
  cacheLeitura: TCacheLeitura;
  conversation: ChatState | null;
  guidedInspectionDraft: GuidedInspectionDraft | null;
  setConversation: Dispatch<SetStateAction<ChatState | null>>;
  laudosDisponiveis: MobileLaudoCard[];
  setLaudosDisponiveis: Dispatch<SetStateAction<MobileLaudoCard[]>>;
  laudosFixadosIds: number[];
  historicoOcultoIds: number[];
  laudoMesaCarregado: number | null;
  setLaudoMesaCarregado: Dispatch<SetStateAction<number | null>>;
  setMensagensMesa: Dispatch<SetStateAction<MobileMesaMessage[]>>;
  setErroMesa: Dispatch<SetStateAction<string>>;
  setMensagemMesa: Dispatch<SetStateAction<string>>;
  setAnexoMesaRascunho: Dispatch<SetStateAction<ComposerAttachment | null>>;
  clearMesaReference: () => void;
  clearGuidedInspectionDraft: () => void;
  startGuidedInspection: (options?: StartGuidedInspectionOptions) => void;
  onSetActiveThread: (value: ActiveThread) => void;
  message: string;
  setMessage: Dispatch<SetStateAction<string>>;
  attachmentDraft: ComposerAttachment | null;
  setAttachmentDraft: Dispatch<SetStateAction<ComposerAttachment | null>>;
  setErrorConversation: Dispatch<SetStateAction<string>>;
  qualityGateLaudoId: number | null;
  qualityGatePayload: MobileQualityGateResponse | null;
  qualityGateReason: string;
  setQualityGateLaudoId: Dispatch<SetStateAction<number | null>>;
  setQualityGateLoading: Dispatch<SetStateAction<boolean>>;
  setQualityGateNotice: Dispatch<SetStateAction<string>>;
  setQualityGatePayload: Dispatch<
    SetStateAction<MobileQualityGateResponse | null>
  >;
  setQualityGateReason: Dispatch<SetStateAction<string>>;
  setQualityGateSubmitting: Dispatch<SetStateAction<boolean>>;
  setQualityGateVisible: Dispatch<SetStateAction<boolean>>;
  setSendingMessage: Dispatch<SetStateAction<boolean>>;
  setLoadingConversation: Dispatch<SetStateAction<boolean>>;
  setSyncConversation: Dispatch<SetStateAction<boolean>>;
  setLoadingLaudos: Dispatch<SetStateAction<boolean>>;
  setErrorLaudos: Dispatch<SetStateAction<string>>;
  setThreadHomeGuidedTemplatesVisible?: Dispatch<SetStateAction<boolean>>;
  setThreadHomeVisible: Dispatch<SetStateAction<boolean>>;
  highlightedMessageId: number | null;
  setHighlightedMessageId: Dispatch<SetStateAction<number | null>>;
  layoutVersion: number;
  setLayoutVersion: Dispatch<SetStateAction<number>>;
  setCaseCreationState: Dispatch<SetStateAction<ChatCaseCreationState>>;
  scrollRef: MutableRefObject<ScrollView | null>;
  setFilaOffline: Dispatch<SetStateAction<TOfflineItem[]>>;
  setStatusApi: (value: "online" | "offline") => void;
  setUsandoCacheOffline: (value: boolean) => void;
  setCacheLeitura: Dispatch<SetStateAction<TCacheLeitura>>;
  carregarMesaAtual: (
    accessToken: string,
    laudoId: number,
    silencioso?: boolean,
  ) => Promise<void>;
  aplicarPreferenciasLaudos: (
    itens: MobileLaudoCard[],
    fixadosIds: number[],
    ocultosIds: number[],
  ) => MobileLaudoCard[];
  chaveCacheLaudo: (laudoId: number | null) => string;
  chaveRascunho: (thread: ActiveThread, laudoId: number | null) => string;
  erroSugereModoOffline: (error: unknown) => boolean;
  normalizarConversa: (
    payload: MobileLaudoStatusResponse | MobileLaudoMensagensResponse,
  ) => ChatState;
  atualizarResumoLaudoAtual: (
    estadoAtual: ChatState | null,
    payload: UpdateConversationSummaryPayload,
  ) => ChatState | null;
  criarConversaNova: () => ChatState;
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
}

export function useInspectorChatController<
  TOfflineItem extends OfflinePendingMessage,
  TCacheLeitura extends ChatCacheState,
>(params: UseInspectorChatControllerParams<TOfflineItem, TCacheLeitura>) {
  const paramsRef = useRef(params);
  paramsRef.current = params;
  const chatMessageOffsetsRef = useRef<Record<number, number>>({});
  const chatHighlightTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const chatDraftKeyRef = useRef("");
  const chatAttachmentDraftKeyRef = useRef("");
  const guidedDraftCacheKeyRef = useRef("");
  const guidedDraftRemoteSyncRef = useRef<Record<string, string>>({});

  const restaurarContextoGuiadoAtual = (
    laudoId: number | null,
    laudoCard: MobileLaudoCard | null | undefined,
    draftServidor?: GuidedInspectionDraft | null,
  ) =>
    restaurarContextoGuiadoDoCaso({
      laudoId,
      laudoCard,
      draftServidor,
      cacheLeitura: paramsRef.current.cacheLeitura,
      laudosDisponiveis: paramsRef.current.laudosDisponiveis,
      chaveCacheLaudo: paramsRef.current.chaveCacheLaudo,
      setCacheLeitura: paramsRef.current.setCacheLeitura,
      guidedDraftRemoteSyncRef,
      entryModePreference: paramsRef.current.entryModePreference,
      rememberLastCaseMode: paramsRef.current.rememberLastCaseMode,
      clearGuidedInspectionDraft: paramsRef.current.clearGuidedInspectionDraft,
      startGuidedInspection: paramsRef.current.startGuidedInspection,
    });

  const {
    abrirLaudoPorId,
    carregarConversaAtual,
    carregarListaLaudos,
    handleAbrirNovoChat,
    handleIniciarChatLivre,
    handleSelecionarLaudo,
    resetChatState,
  } = createInspectorChatCaseController<TCacheLeitura>({
    paramsRef,
    chatMessageOffsetsRef,
    chatHighlightTimeoutRef,
    restaurarContextoGuiadoDoCaso: restaurarContextoGuiadoAtual,
  });

  async function handleReabrir() {
    const current = paramsRef.current;
    const laudoId = resolverLaudoIdOperacional(current);
    if (!current.session || !laudoId) {
      return;
    }

    try {
      const issuedDocumentPolicy = conversaTemDocumentoEmitidoAtivo(
        current.conversation,
      )
        ? await solicitarPoliticaDocumentoEmitido()
        : undefined;

      if (issuedDocumentPolicy === null) {
        return;
      }

      await reabrirLaudoMobile(
        current.session.accessToken,
        laudoId,
        issuedDocumentPolicy
          ? { issued_document_policy: issuedDocumentPolicy }
          : undefined,
      );
      const proximaConversa = await carregarConversaAtual(
        current.session.accessToken,
        true,
      );
      await carregarListaLaudos(current.session.accessToken, true);
      restaurarContextoGuiadoAtual(
        proximaConversa?.laudoId ?? null,
        proximaConversa?.laudoCard,
      );
      if (current.activeThread === "mesa" && proximaConversa?.laudoId) {
        await current.carregarMesaAtual(
          current.session.accessToken,
          proximaConversa.laudoId,
          true,
        );
      }
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Nao foi possivel reabrir o laudo.";
      Alert.alert("Reabrir laudo", message);
    }
  }

  const qualityGateController =
    createInspectorChatQualityGateController<TOfflineItem>({
      paramsRef,
      resolveOperationalLaudoId: resolverLaudoIdOperacional,
      carregarConversaAtual,
      carregarListaLaudos,
      restaurarContextoGuiadoDoCaso: restaurarContextoGuiadoAtual,
      abrirLaudoPorId,
    });

  const { handleEnviarMensagem } =
    createInspectorChatMessageController<TOfflineItem>({
      paramsRef,
      carregarConversaAtual,
      carregarListaLaudos,
    });
  const {
    abrirReferenciaNoChat,
    handleAbrirColetaGuiadaAtual,
    registrarLayoutMensagemChat,
  } = createInspectorChatNavigationController<TCacheLeitura>({
    paramsRef,
    chatMessageOffsetsRef,
    abrirLaudoPorId,
  });

  useInspectorChatControllerEffects<TCacheLeitura>({
    session: params.session,
    sessionLoading: params.sessionLoading,
    statusApi: params.statusApi,
    activeThread: params.activeThread,
    conversationLaudoId: params.conversation?.laudoId,
    conversationMensagensLength: params.conversation?.mensagens.length ?? 0,
    guidedInspectionDraft: params.guidedInspectionDraft,
    highlightedMessageId: params.highlightedMessageId,
    layoutVersion: params.layoutVersion,
    scrollRef: params.scrollRef,
    setMessage: params.setMessage,
    setAttachmentDraft: params.setAttachmentDraft,
    setHighlightedMessageId: params.setHighlightedMessageId,
    setLayoutVersion: params.setLayoutVersion,
    setCacheLeitura: params.setCacheLeitura,
    setUsandoCacheOffline: params.setUsandoCacheOffline,
    clearMesaReference: params.clearMesaReference,
    chaveRascunho: params.chaveRascunho,
    chaveCacheLaudo: params.chaveCacheLaudo,
    erroSugereModoOffline: params.erroSugereModoOffline,
    setStatusApi: params.setStatusApi,
    resetChatState,
    carregarListaLaudos,
    carregarConversaAtual,
    chatMessageOffsetsRef,
    chatHighlightTimeoutRef,
    chatDraftKeyRef,
    chatAttachmentDraftKeyRef,
    guidedDraftCacheKeyRef,
    guidedDraftRemoteSyncRef,
  });

  return {
    actions: {
      handleAbrirColetaGuiadaAtual,
      handleAbrirQualityGate: qualityGateController.handleAbrirQualityGate,
      abrirLaudoPorId,
      abrirReferenciaNoChat,
      carregarConversaAtual,
      carregarListaLaudos,
      handleAbrirNovoChat,
      handleIniciarChatLivre,
      handleConfirmarQualityGate:
        qualityGateController.handleConfirmarQualityGate,
      handleEnviarMensagem,
      handleFecharQualityGate: qualityGateController.handleFecharQualityGate,
      handleReabrir,
      handleRetomarQualityGateOfflineItem:
        qualityGateController.handleRetomarQualityGateOfflineItem,
      handleSelecionarLaudo,
      registrarLayoutMensagemChat,
      resetChatState,
    },
  };
}
