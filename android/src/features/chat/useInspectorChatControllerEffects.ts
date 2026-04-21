import {
  useEffect,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
} from "react";
import type { ScrollView } from "react-native";

import { salvarGuidedInspectionDraftMobile } from "../../config/api";
import type { MobileLaudoCard } from "../../types/mobile";
import {
  guidedInspectionDraftFromMobilePayload,
  guidedInspectionDraftToMobilePayload,
  type GuidedInspectionDraft,
} from "../inspection/guidedInspection";
import { serializarGuidedDraft } from "./inspectorChatGuidedDraftSync";
import type { ChatState, ComposerAttachment } from "./types";

interface GuidedDraftCacheState {
  guidedInspectionDrafts?: Record<string, GuidedInspectionDraft>;
  updatedAt: string;
}

interface UseInspectorChatControllerEffectsParams<
  TCacheLeitura extends GuidedDraftCacheState,
> {
  session: {
    accessToken: string;
  } | null;
  sessionLoading: boolean;
  statusApi: string;
  activeThread: "chat" | "mesa" | "finalizar";
  conversationLaudoId: number | null | undefined;
  conversationMensagensLength: number;
  guidedInspectionDraft: GuidedInspectionDraft | null;
  highlightedMessageId: number | null;
  layoutVersion: number;
  scrollRef: MutableRefObject<ScrollView | null>;
  setMessage: Dispatch<SetStateAction<string>>;
  setAttachmentDraft: Dispatch<SetStateAction<ComposerAttachment | null>>;
  setHighlightedMessageId: Dispatch<SetStateAction<number | null>>;
  setLayoutVersion: Dispatch<SetStateAction<number>>;
  setCacheLeitura: Dispatch<SetStateAction<TCacheLeitura>>;
  setUsandoCacheOffline: (value: boolean) => void;
  clearMesaReference: () => void;
  chaveRascunho: (
    thread: "chat" | "mesa" | "finalizar",
    laudoId: number | null,
  ) => string;
  chaveCacheLaudo: (laudoId: number | null) => string;
  erroSugereModoOffline: (error: unknown) => boolean;
  setStatusApi: (value: "online" | "offline") => void;
  resetChatState: () => void;
  carregarListaLaudos: (
    accessToken: string,
    silencioso?: boolean,
  ) => Promise<MobileLaudoCard[]>;
  carregarConversaAtual: (
    accessToken: string,
    silencioso?: boolean,
  ) => Promise<ChatState | null>;
  chatMessageOffsetsRef: MutableRefObject<Record<number, number>>;
  chatHighlightTimeoutRef: MutableRefObject<ReturnType<
    typeof setTimeout
  > | null>;
  chatDraftKeyRef: MutableRefObject<string>;
  chatAttachmentDraftKeyRef: MutableRefObject<string>;
  guidedDraftCacheKeyRef: MutableRefObject<string>;
  guidedDraftRemoteSyncRef: MutableRefObject<Record<string, string>>;
}

export function useInspectorChatControllerEffects<
  TCacheLeitura extends GuidedDraftCacheState,
>({
  session,
  sessionLoading,
  statusApi,
  activeThread,
  conversationLaudoId,
  conversationMensagensLength,
  guidedInspectionDraft,
  highlightedMessageId,
  layoutVersion,
  scrollRef,
  setMessage,
  setAttachmentDraft,
  setHighlightedMessageId,
  setLayoutVersion,
  setCacheLeitura,
  setUsandoCacheOffline,
  clearMesaReference,
  chaveRascunho,
  chaveCacheLaudo,
  erroSugereModoOffline,
  setStatusApi,
  resetChatState,
  carregarListaLaudos,
  carregarConversaAtual,
  chatMessageOffsetsRef,
  chatHighlightTimeoutRef,
  chatDraftKeyRef,
  chatAttachmentDraftKeyRef,
  guidedDraftCacheKeyRef,
  guidedDraftRemoteSyncRef,
}: UseInspectorChatControllerEffectsParams<TCacheLeitura>) {
  useEffect(() => {
    if (!session) {
      chatDraftKeyRef.current = "";
      chatAttachmentDraftKeyRef.current = "";
      guidedDraftCacheKeyRef.current = "";
      guidedDraftRemoteSyncRef.current = {};
      if (sessionLoading) {
        return;
      }
      resetChatState();
      setUsandoCacheOffline(false);
      return;
    }

    void carregarListaLaudos(session.accessToken);
    if (conversationLaudoId) {
      void carregarConversaAtual(session.accessToken);
    }
  }, [session, sessionLoading]);

  useEffect(() => {
    chatMessageOffsetsRef.current = {};
    setLayoutVersion(0);
    setHighlightedMessageId(null);
  }, [conversationLaudoId]);

  useEffect(() => {
    clearMesaReference();
  }, [conversationLaudoId]);

  useEffect(() => {
    if (activeThread !== "chat" || !highlightedMessageId) {
      return;
    }

    const offsetY = chatMessageOffsetsRef.current[highlightedMessageId];
    if (typeof offsetY !== "number") {
      return;
    }

    const scrollTimeout = setTimeout(() => {
      scrollRef.current?.scrollTo({
        y: Math.max(offsetY - 112, 0),
        animated: true,
      });
    }, 120);

    if (chatHighlightTimeoutRef.current) {
      clearTimeout(chatHighlightTimeoutRef.current);
    }
    chatHighlightTimeoutRef.current = setTimeout(() => {
      setHighlightedMessageId((estadoAtual) =>
        estadoAtual === highlightedMessageId ? null : estadoAtual,
      );
      chatHighlightTimeoutRef.current = null;
    }, 1800);

    return () => clearTimeout(scrollTimeout);
  }, [
    activeThread,
    conversationMensagensLength,
    highlightedMessageId,
    layoutVersion,
    scrollRef,
  ]);

  useEffect(() => {
    return () => {
      if (chatHighlightTimeoutRef.current) {
        clearTimeout(chatHighlightTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!session) {
      return;
    }

    const chatKey = conversationLaudoId
      ? chaveRascunho("chat", conversationLaudoId)
      : "";
    if (chatDraftKeyRef.current !== chatKey) {
      chatDraftKeyRef.current = chatKey;
      setMessage("");
      setAttachmentDraft(null);
    }
    chatAttachmentDraftKeyRef.current = chatKey;
  }, [
    chaveRascunho,
    conversationLaudoId,
    session,
    setAttachmentDraft,
    setMessage,
  ]);

  useEffect(() => {
    if (!session) {
      return;
    }

    const nextKey = chaveCacheLaudo(conversationLaudoId ?? null);
    const previousKey = guidedDraftCacheKeyRef.current;
    const draftFallbackKey = chaveCacheLaudo(null);
    guidedDraftCacheKeyRef.current = nextKey;
    setCacheLeitura((estadoAtual) => {
      const drafts = { ...(estadoAtual.guidedInspectionDrafts || {}) };
      let changed = false;

      const currentDraft = guidedInspectionDraft;
      const storedDraft = drafts[nextKey];
      if (currentDraft) {
        if (storedDraft !== currentDraft) {
          drafts[nextKey] = currentDraft;
          changed = true;
        }

        if (
          previousKey &&
          previousKey !== nextKey &&
          previousKey === draftFallbackKey &&
          drafts[previousKey]
        ) {
          delete drafts[previousKey];
          changed = true;
        }
      }

      if (!changed) {
        return estadoAtual;
      }

      return {
        ...estadoAtual,
        guidedInspectionDrafts: drafts,
        updatedAt: new Date().toISOString(),
      };
    });
  }, [
    chaveCacheLaudo,
    conversationLaudoId,
    guidedInspectionDraft,
    session,
    setCacheLeitura,
  ]);

  useEffect(() => {
    if (
      !session ||
      statusApi === "offline" ||
      !conversationLaudoId ||
      !guidedInspectionDraft
    ) {
      return;
    }

    const cacheKey = chaveCacheLaudo(conversationLaudoId);
    const serializedDraft = serializarGuidedDraft(guidedInspectionDraft);
    if (!serializedDraft) {
      return;
    }
    if (guidedDraftRemoteSyncRef.current[cacheKey] === serializedDraft) {
      return;
    }

    let cancelled = false;
    void salvarGuidedInspectionDraftMobile(
      session.accessToken,
      conversationLaudoId,
      {
        guided_inspection_draft: guidedInspectionDraftToMobilePayload(
          guidedInspectionDraft,
        ),
      },
    )
      .then((response) => {
        if (cancelled) {
          return;
        }

        const draftSalvo = guidedInspectionDraftFromMobilePayload(
          response.guided_inspection_draft,
        );
        if (draftSalvo) {
          guidedDraftRemoteSyncRef.current[cacheKey] =
            serializarGuidedDraft(draftSalvo);
        } else {
          delete guidedDraftRemoteSyncRef.current[cacheKey];
        }
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        if (erroSugereModoOffline(error)) {
          setStatusApi("offline");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    chaveCacheLaudo,
    conversationLaudoId,
    erroSugereModoOffline,
    guidedInspectionDraft,
    session,
    setStatusApi,
    statusApi,
  ]);
}
