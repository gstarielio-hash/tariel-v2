import type { Dispatch, SetStateAction } from "react";

import type { MobileLaudoCard } from "../../types/mobile";
import type { ComposerAttachment } from "../chat/types";
import {
  buildThreadRouteSnapshot,
  threadRouteSnapshotsEqual,
  type ThreadRouteSnapshot,
} from "../common/threadRouteHistory";

interface HistoryCacheLike {
  laudos: MobileLaudoCard[];
  conversasPorLaudo: Record<string, unknown>;
  mesaPorLaudo: Record<string, unknown>;
  updatedAt: string;
}

interface HistoryNotificationLike {
  laudoId: number | null;
}

interface UseHistoryControllerParams<
  TConversation,
  TCache extends HistoryCacheLike,
  TMesaMessage,
  TNotification extends HistoryNotificationLike,
> {
  keyboardHeight: number;
  historicoAberto: boolean;
  historicoAbertoRefAtual: boolean;
  pendingHistoryThreadRoute: ThreadRouteSnapshot | null;
  conversaAtualLaudoId: number | null;
  historicoOcultoIds: number[];
  laudosFixadosIds: number[];
  fecharHistorico: (options?: {
    limparBusca?: boolean;
    manterOverlay?: boolean;
  }) => void;
  abrirHistorico: () => void;
  fecharConfiguracoes: (options?: { manterOverlay?: boolean }) => void;
  handleSelecionarLaudo: (card: MobileLaudoCard | null) => Promise<void>;
  onCreateNewConversation: () => TConversation;
  onDismissKeyboard: () => void;
  onGetCacheKeyForLaudo: (laudoId: number | null) => string;
  onSchedule: (callback: () => void, delayMs: number) => void;
  setAbaAtiva: (value: "chat" | "mesa") => void;
  setAnexoMesaRascunho: (value: ComposerAttachment | null) => void;
  setAnexoRascunho: (value: ComposerAttachment | null) => void;
  setCacheLeitura: (updater: (current: TCache) => TCache) => void;
  setConversa: (value: TConversation | null) => void;
  setErroConversa: (value: string) => void;
  setErroMesa: (value: string) => void;
  setHistoricoOcultoIds: Dispatch<SetStateAction<number[]>>;
  setLaudoMesaCarregado: (value: null) => void;
  setLaudosDisponiveis: (
    updater: (current: MobileLaudoCard[]) => MobileLaudoCard[],
  ) => void;
  setLaudosFixadosIds: Dispatch<SetStateAction<number[]>>;
  setMensagem: (value: string) => void;
  setMensagemMesa: (value: string) => void;
  setMensagensMesa: (value: TMesaMessage[]) => void;
  setNotificacoes: (
    updater: (current: TNotification[]) => TNotification[],
  ) => void;
  setPendingHistoryThreadRoute: Dispatch<
    SetStateAction<ThreadRouteSnapshot | null>
  >;
  setThreadRouteHistory: Dispatch<SetStateAction<ThreadRouteSnapshot[]>>;
}

export function useHistoryController<
  TConversation,
  TCache extends HistoryCacheLike,
  TMesaMessage,
  TNotification extends HistoryNotificationLike,
>({
  keyboardHeight,
  historicoAberto,
  historicoAbertoRefAtual,
  pendingHistoryThreadRoute,
  conversaAtualLaudoId,
  fecharHistorico,
  abrirHistorico,
  fecharConfiguracoes,
  handleSelecionarLaudo,
  onCreateNewConversation,
  onDismissKeyboard,
  onGetCacheKeyForLaudo,
  onSchedule,
  setAbaAtiva,
  setAnexoMesaRascunho,
  setAnexoRascunho,
  setCacheLeitura,
  setConversa,
  setErroConversa,
  setErroMesa,
  setHistoricoOcultoIds,
  setLaudoMesaCarregado,
  setLaudosDisponiveis,
  setLaudosFixadosIds,
  setMensagem,
  setMensagemMesa,
  setMensagensMesa,
  setNotificacoes,
  setPendingHistoryThreadRoute,
  setThreadRouteHistory,
}: UseHistoryControllerParams<
  TConversation,
  TCache,
  TMesaMessage,
  TNotification
>) {
  function atualizarLaudosLocais(
    transform: (itens: MobileLaudoCard[]) => MobileLaudoCard[],
  ) {
    setLaudosDisponiveis((estadoAtual) => {
      const proximosLaudos = transform(estadoAtual);
      setCacheLeitura((cacheAtual) => ({
        ...cacheAtual,
        laudos: transform(cacheAtual.laudos),
        updatedAt: new Date().toISOString(),
      }));
      return proximosLaudos;
    });
  }

  function handleAbrirHistorico() {
    if (keyboardHeight > 0) {
      onDismissKeyboard();
      return;
    }
    if (historicoAberto || historicoAbertoRefAtual) {
      setPendingHistoryThreadRoute(null);
      fecharHistorico({ limparBusca: true });
      return;
    }
    abrirHistorico();
  }

  function handleGerenciarConversasIndividuais() {
    fecharConfiguracoes();
    onSchedule(() => {
      abrirHistorico();
    }, 180);
  }

  function handleAlternarFixadoHistorico(card: MobileLaudoCard) {
    const vaiFixar = !card.pinado;
    setLaudosFixadosIds((estadoAtual) =>
      vaiFixar
        ? Array.from(new Set([...estadoAtual, card.id]))
        : estadoAtual.filter((item) => item !== card.id),
    );
    atualizarLaudosLocais((itens) =>
      itens.map((item) =>
        item.id === card.id ? { ...item, pinado: vaiFixar } : item,
      ),
    );
  }

  function handleExcluirConversaHistorico(card: MobileLaudoCard) {
    setHistoricoOcultoIds((estadoAtual) =>
      Array.from(new Set([...estadoAtual, card.id])),
    );
    setLaudosFixadosIds((estadoAtual) =>
      estadoAtual.filter((item) => item !== card.id),
    );
    atualizarLaudosLocais((itens) =>
      itens.filter((item) => item.id !== card.id),
    );
    setCacheLeitura((estadoAtual) => {
      const chave = onGetCacheKeyForLaudo(card.id);
      const { [chave]: _chatRemovido, ...restoConversas } =
        estadoAtual.conversasPorLaudo;
      const { [chave]: _mesaRemovida, ...restoMesa } = estadoAtual.mesaPorLaudo;
      return {
        ...estadoAtual,
        laudos: estadoAtual.laudos.filter((item) => item.id !== card.id),
        conversasPorLaudo: restoConversas,
        mesaPorLaudo: restoMesa,
        updatedAt: new Date().toISOString(),
      };
    });
    setNotificacoes((estadoAtual) =>
      estadoAtual.filter((item) => item.laudoId !== card.id),
    );
    if (conversaAtualLaudoId === card.id) {
      setConversa(onCreateNewConversation());
      setMensagensMesa([]);
      setMensagem("");
      setMensagemMesa("");
      setAnexoRascunho(null);
      setAnexoMesaRascunho(null);
      setErroMesa("");
      setErroConversa("");
      setLaudoMesaCarregado(null);
    }
  }

  async function handleSelecionarHistorico(card: MobileLaudoCard | null) {
    if (pendingHistoryThreadRoute) {
      const destinationRoute = buildThreadRouteSnapshot({
        activeThread: "chat",
        conversationLaudoId: card?.id ?? null,
        guidedInspectionDraft: null,
        threadHomeVisible: !card,
      });

      if (
        !threadRouteSnapshotsEqual(pendingHistoryThreadRoute, destinationRoute)
      ) {
        setThreadRouteHistory((current) => [
          ...current,
          pendingHistoryThreadRoute,
        ]);
      }

      setPendingHistoryThreadRoute(null);
    }

    fecharHistorico({ limparBusca: true });
    setAbaAtiva("chat");
    await handleSelecionarLaudo(card);
  }

  return {
    handleAbrirHistorico,
    handleGerenciarConversasIndividuais,
    handleAlternarFixadoHistorico,
    handleExcluirConversaHistorico,
    handleSelecionarHistorico,
  };
}
