import type { Dispatch, MutableRefObject, SetStateAction } from "react";

import type { GuidedInspectionDraft } from "../inspection/guidedInspection";
import { obterGuidedDraftDoCache } from "./inspectorChatGuidedDraftSync";
import type { ChatState } from "./types";

interface NavigationCacheState {
  guidedInspectionDrafts?: Record<string, GuidedInspectionDraft>;
}

type NavigationControllerCurrent<TCacheLeitura extends NavigationCacheState> = {
  session: {
    accessToken: string;
  } | null;
  conversation: ChatState | null;
  cacheLeitura: TCacheLeitura;
  chaveCacheLaudo: (laudoId: number | null) => string;
  startGuidedInspection: (options?: {
    draft?: GuidedInspectionDraft | null;
    ignoreActiveConversation?: boolean;
    tipoTemplate?: string | null;
  }) => void;
  setErrorConversation: Dispatch<SetStateAction<string>>;
  onSetActiveThread: (value: "chat" | "mesa" | "finalizar") => void;
  setHighlightedMessageId: Dispatch<SetStateAction<number | null>>;
  setLayoutVersion: Dispatch<SetStateAction<number>>;
};

interface CreateInspectorChatNavigationControllerParams<
  TCacheLeitura extends NavigationCacheState,
> {
  paramsRef: MutableRefObject<NavigationControllerCurrent<TCacheLeitura>>;
  chatMessageOffsetsRef: MutableRefObject<Record<number, number>>;
  abrirLaudoPorId: (accessToken: string, laudoId: number) => Promise<void>;
}

export function createInspectorChatNavigationController<
  TCacheLeitura extends NavigationCacheState,
>({
  paramsRef,
  chatMessageOffsetsRef,
  abrirLaudoPorId,
}: CreateInspectorChatNavigationControllerParams<TCacheLeitura>) {
  function handleAbrirColetaGuiadaAtual() {
    const current = paramsRef.current;
    current.setErrorConversation("");
    const cachedDraft = obterGuidedDraftDoCache(
      current.cacheLeitura.guidedInspectionDrafts,
      current.chaveCacheLaudo(current.conversation?.laudoId ?? null),
    );
    current.startGuidedInspection({
      draft: cachedDraft,
      ignoreActiveConversation: Boolean(current.conversation?.laudoId),
      tipoTemplate: current.conversation?.laudoCard?.tipo_template || null,
    });
  }

  function registrarLayoutMensagemChat(
    mensagemId: number | null,
    offsetY: number,
  ) {
    const alvo = Number(mensagemId || 0) || null;
    if (!alvo) {
      return;
    }

    if (chatMessageOffsetsRef.current[alvo] === offsetY) {
      return;
    }

    chatMessageOffsetsRef.current[alvo] = offsetY;
    paramsRef.current.setLayoutVersion((estadoAtual) => estadoAtual + 1);
  }

  async function abrirReferenciaNoChat(
    referenciaId: number | null | undefined,
  ) {
    const current = paramsRef.current;
    const alvo = Number(referenciaId || 0) || null;
    if (!alvo) {
      return;
    }

    if (
      !current.conversation?.mensagens.some(
        (item) => Number(item.id || 0) === alvo,
      ) &&
      current.session &&
      current.conversation?.laudoId
    ) {
      await abrirLaudoPorId(
        current.session.accessToken,
        current.conversation.laudoId,
      );
    }

    current.onSetActiveThread("chat");
    current.setHighlightedMessageId(alvo);
  }

  return {
    abrirReferenciaNoChat,
    handleAbrirColetaGuiadaAtual,
    registrarLayoutMensagemChat,
  };
}
