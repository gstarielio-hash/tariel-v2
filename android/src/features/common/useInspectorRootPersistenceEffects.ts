import {
  useEffect,
  useMemo,
  useRef,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
} from "react";

import type { AppSettings } from "../../settings/schema/types";
import {
  mergeCriticalSnapshotIntoSettings,
  mergeMobileUserIntoSettings,
  settingsToCriticalSnapshot,
} from "../../settings/repository/settingsRemoteAdapter";
import type { MobileLaudoCard } from "../../types/mobile";
import type {
  MobileActivityNotification,
  OfflinePendingMessage,
} from "../chat/types";
import type { MobileSessionState } from "../session/sessionTypes";
import { useCriticalSettingsSync } from "../settings/useCriticalSettingsSync";
import { formatarStatusReautenticacao } from "../settings/reauth";
import type {
  ConnectedProvider,
  SupportQueueItem,
} from "../settings/useSettingsPresentation";
import type { MobileReadCache } from "./readCacheTypes";

interface SettingsActionsLike {
  updateWith: (updater: (current: AppSettings) => AppSettings) => void;
}

interface UseInspectorRootPersistenceEffectsInput {
  sessionState: {
    carregando: boolean;
    email: string;
    session: MobileSessionState | null;
  };
  settingsState: {
    backupAutomatico: boolean;
    reautenticacaoExpiraEm: string;
    reautenticacaoStatus: string;
    retencaoDados: AppSettings["dataControls"]["retention"];
    salvarHistoricoConversas: boolean;
    settingsActions: SettingsActionsLike;
    settingsDocument: AppSettings;
  };
  dataState: {
    cacheLeitura: MobileReadCache;
    historicoOcultoIds: number[];
    laudosFixadosIds: number[];
  };
  actionState: {
    isReauthenticationStillValid: (expiresAt: string) => boolean;
    onFilterItemsByRetention: <T>(
      items: T[],
      windowMs: number,
      getDate: (item: T) => string,
    ) => T[];
    onGetCacheKeyForLaudo: (laudoId: number | null) => string;
    onGetRetentionWindowMs: (
      retention: AppSettings["dataControls"]["retention"],
    ) => number | null;
    onResetMesaState: () => void;
    onSanitizeReadCacheForPrivacy: (cache: MobileReadCache) => MobileReadCache;
    onSaveHistoryStateLocally: (params: {
      historicoOcultoIds: number[];
      laudosFixadosIds: number[];
    }) => Promise<void>;
    onSaveReadCacheLocally: (cache: MobileReadCache) => Promise<void>;
    registerNotifications: (items: MobileActivityNotification[]) => void;
  };
  setterState: {
    notificationRegistrarRef: MutableRefObject<
      (items: MobileActivityNotification[]) => void
    >;
    setCacheLeitura: Dispatch<SetStateAction<MobileReadCache>>;
    setFilaOffline: Dispatch<SetStateAction<OfflinePendingMessage[]>>;
    setFilaSuporteLocal: Dispatch<SetStateAction<SupportQueueItem[]>>;
    setLaudosDisponiveis: Dispatch<SetStateAction<MobileLaudoCard[]>>;
    setNotificacoes: Dispatch<SetStateAction<MobileActivityNotification[]>>;
    setProvedoresConectados: Dispatch<SetStateAction<ConnectedProvider[]>>;
    setReautenticacaoExpiraEm: Dispatch<SetStateAction<string>>;
    setReautenticacaoStatus: Dispatch<SetStateAction<string>>;
  };
}

export function useInspectorRootPersistenceEffects({
  sessionState,
  settingsState,
  dataState,
  actionState,
  setterState,
}: UseInspectorRootPersistenceEffectsInput) {
  const actionStateRef = useRef(actionState);
  actionStateRef.current = actionState;
  const setterStateRef = useRef(setterState);
  setterStateRef.current = setterState;
  const settingsActionsRef = useRef(settingsState.settingsActions);
  settingsActionsRef.current = settingsState.settingsActions;
  const snapshotConfiguracoesCriticasAtuais = useMemo(
    () => settingsToCriticalSnapshot(settingsState.settingsDocument),
    [settingsState.settingsDocument],
  );

  useEffect(() => {
    const sessionUser = sessionState.session?.bootstrap.usuario;
    if (!sessionUser) {
      return;
    }

    settingsActionsRef.current.updateWith((current) =>
      mergeMobileUserIntoSettings(current, sessionUser),
    );
    setterStateRef.current.setProvedoresConectados((estadoAtual) => {
      let houveMudanca = false;
      const proximoEstado = estadoAtual.map((provider) => {
        if (!provider.connected || provider.email || !sessionUser.email) {
          return provider;
        }
        houveMudanca = true;
        return {
          ...provider,
          email: sessionUser.email,
        };
      });
      return houveMudanca ? proximoEstado : estadoAtual;
    });
  }, [sessionState.session]);

  useCriticalSettingsSync({
    accessToken: sessionState.session?.accessToken,
    carregando: sessionState.carregando,
    snapshotAtual: snapshotConfiguracoesCriticasAtuais,
    aplicarSnapshot: (snapshot) => {
      settingsActionsRef.current.updateWith((current) =>
        mergeCriticalSnapshotIntoSettings(current, snapshot),
      );
    },
    onLoadError: (error) => {
      console.warn(
        "Falha ao carregar configuracoes criticas da conta no backend.",
        error,
      );
    },
    onSaveError: (error) => {
      console.warn(
        "Falha ao sincronizar configuracoes criticas da conta no backend.",
        error,
      );
    },
  });

  setterState.notificationRegistrarRef.current =
    actionState.registerNotifications;

  useEffect(() => {
    if (sessionState.carregando) {
      return;
    }
    void actionStateRef.current.onSaveHistoryStateLocally({
      laudosFixadosIds: dataState.laudosFixadosIds,
      historicoOcultoIds: dataState.historicoOcultoIds,
    });
  }, [
    dataState.historicoOcultoIds,
    dataState.laudosFixadosIds,
    sessionState.carregando,
  ]);

  useEffect(() => {
    if (sessionState.carregando) {
      return;
    }
    if (!settingsState.backupAutomatico) {
      void actionStateRef.current.onSaveReadCacheLocally({
        ...dataState.cacheLeitura,
        ...{
          bootstrap: null,
          laudos: [],
          conversaAtual: null,
          conversasPorLaudo: {},
          mesaPorLaudo: {},
          guidedInspectionDrafts: {},
          chatDrafts: {},
          mesaDrafts: {},
          chatAttachmentDrafts: {},
          mesaAttachmentDrafts: {},
          updatedAt: "",
        },
      });
      return;
    }
    void actionStateRef.current.onSaveReadCacheLocally(
      settingsState.salvarHistoricoConversas
        ? dataState.cacheLeitura
        : actionStateRef.current.onSanitizeReadCacheForPrivacy(
            dataState.cacheLeitura,
          ),
    );
  }, [
    dataState.cacheLeitura,
    sessionState.carregando,
    settingsState.backupAutomatico,
    settingsState.salvarHistoricoConversas,
  ]);

  useEffect(() => {
    if (sessionState.carregando || settingsState.salvarHistoricoConversas) {
      return;
    }

    setterStateRef.current.setCacheLeitura((estadoAtual) => {
      const possuiHistorico =
        Boolean(estadoAtual.conversaAtual) ||
        estadoAtual.laudos.length > 0 ||
        Object.keys(estadoAtual.conversasPorLaudo).length > 0 ||
        Object.keys(estadoAtual.mesaPorLaudo).length > 0 ||
        Object.keys(estadoAtual.guidedInspectionDrafts || {}).length > 0 ||
        Object.keys(estadoAtual.chatDrafts).length > 0 ||
        Object.keys(estadoAtual.mesaDrafts).length > 0 ||
        Object.keys(estadoAtual.chatAttachmentDrafts).length > 0 ||
        Object.keys(estadoAtual.mesaAttachmentDrafts).length > 0;

      if (!possuiHistorico) {
        return estadoAtual;
      }

      return actionStateRef.current.onSanitizeReadCacheForPrivacy(estadoAtual);
    });
  }, [sessionState.carregando, settingsState.salvarHistoricoConversas]);

  useEffect(() => {
    if (!settingsState.reautenticacaoExpiraEm) {
      if (settingsState.reautenticacaoStatus !== "Não confirmada") {
        setterState.setReautenticacaoStatus("Não confirmada");
      }
      return;
    }

    if (
      !actionStateRef.current.isReauthenticationStillValid(
        settingsState.reautenticacaoExpiraEm,
      )
    ) {
      setterStateRef.current.setReautenticacaoExpiraEm("");
      setterStateRef.current.setReautenticacaoStatus("Não confirmada");
      return;
    }

    setterStateRef.current.setReautenticacaoStatus(
      formatarStatusReautenticacao(settingsState.reautenticacaoExpiraEm),
    );
    const timeout = setTimeout(
      () => {
        setterStateRef.current.setReautenticacaoExpiraEm("");
        setterStateRef.current.setReautenticacaoStatus("Não confirmada");
      },
      Math.max(
        0,
        new Date(settingsState.reautenticacaoExpiraEm).getTime() - Date.now(),
      ),
    );

    return () => clearTimeout(timeout);
  }, [
    settingsState.reautenticacaoExpiraEm,
    settingsState.reautenticacaoStatus,
  ]);

  useEffect(() => {
    const janelaMs = actionStateRef.current.onGetRetentionWindowMs(
      settingsState.retencaoDados,
    );
    if (!janelaMs) {
      return;
    }

    setterStateRef.current.setNotificacoes((estadoAtual) =>
      actionStateRef.current.onFilterItemsByRetention(
        estadoAtual,
        janelaMs,
        (item) => item.createdAt,
      ),
    );
    setterStateRef.current.setFilaSuporteLocal((estadoAtual) =>
      actionStateRef.current.onFilterItemsByRetention(
        estadoAtual,
        janelaMs,
        (item) => item.createdAt,
      ),
    );
    setterStateRef.current.setFilaOffline((estadoAtual) =>
      actionStateRef.current.onFilterItemsByRetention(
        estadoAtual,
        janelaMs,
        (item) => item.createdAt,
      ),
    );
    setterStateRef.current.setLaudosDisponiveis((estadoAtual) =>
      actionStateRef.current.onFilterItemsByRetention(
        estadoAtual,
        janelaMs,
        (item) => item.data_iso,
      ),
    );
    setterStateRef.current.setCacheLeitura((estadoAtual) => {
      const laudosFiltrados = actionStateRef.current.onFilterItemsByRetention(
        estadoAtual.laudos,
        janelaMs,
        (item) => item.data_iso,
      );
      const idsPermitidos = new Set(
        laudosFiltrados.map((item) =>
          actionStateRef.current.onGetCacheKeyForLaudo(item.id),
        ),
      );
      const filtrarPorIds = <T>(mapa: Record<string, T>): Record<string, T> =>
        Object.fromEntries(
          Object.entries(mapa).filter(([chave]) => idsPermitidos.has(chave)),
        );
      const conversaAtualValida =
        estadoAtual.conversaAtual?.laudoId &&
        !idsPermitidos.has(
          actionStateRef.current.onGetCacheKeyForLaudo(
            estadoAtual.conversaAtual.laudoId,
          ),
        )
          ? null
          : estadoAtual.conversaAtual;

      return {
        ...estadoAtual,
        laudos: laudosFiltrados,
        conversaAtual: conversaAtualValida,
        conversasPorLaudo: filtrarPorIds(estadoAtual.conversasPorLaudo),
        mesaPorLaudo: filtrarPorIds(estadoAtual.mesaPorLaudo),
        guidedInspectionDrafts: filtrarPorIds(
          estadoAtual.guidedInspectionDrafts || {},
        ),
        chatDrafts: filtrarPorIds(estadoAtual.chatDrafts),
        mesaDrafts: filtrarPorIds(estadoAtual.mesaDrafts),
        chatAttachmentDrafts: filtrarPorIds(estadoAtual.chatAttachmentDrafts),
        mesaAttachmentDrafts: filtrarPorIds(estadoAtual.mesaAttachmentDrafts),
      };
    });
  }, [settingsState.retencaoDados]);

  useEffect(() => {
    if (sessionState.session || sessionState.carregando) {
      return;
    }

    actionStateRef.current.onResetMesaState();
  }, [sessionState.carregando, sessionState.session]);

  useEffect(() => {
    if (sessionState.carregando || !sessionState.session) {
      return;
    }

    setterStateRef.current.setCacheLeitura((estadoAtual) => {
      const possuiRascunhos =
        Object.keys(estadoAtual.guidedInspectionDrafts || {}).length > 0 ||
        Object.keys(estadoAtual.chatDrafts).length > 0 ||
        Object.keys(estadoAtual.mesaDrafts).length > 0 ||
        Object.keys(estadoAtual.chatAttachmentDrafts).length > 0 ||
        Object.keys(estadoAtual.mesaAttachmentDrafts).length > 0;
      if (!possuiRascunhos) {
        return estadoAtual;
      }
      return {
        ...estadoAtual,
        guidedInspectionDrafts: {},
        chatDrafts: {},
        mesaDrafts: {},
        chatAttachmentDrafts: {},
        mesaAttachmentDrafts: {},
        updatedAt: new Date().toISOString(),
      };
    });
  }, [sessionState.carregando, sessionState.session]);
}
