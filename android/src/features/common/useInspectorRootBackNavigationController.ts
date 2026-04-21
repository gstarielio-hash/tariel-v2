import { useEffect, useMemo, useRef } from "react";
import { BackHandler, Keyboard } from "react-native";

import type { InspectorRootBootstrap } from "../useInspectorRootBootstrap";
import type { InspectorRootControllers } from "../useInspectorRootControllers";
import {
  buildThreadRouteSnapshot,
  threadRouteSnapshotsEqual,
  type ThreadRouteSnapshot,
} from "./threadRouteHistory";

interface UseInspectorRootBackNavigationControllerInput {
  bootstrap: InspectorRootBootstrap;
  controllers: InspectorRootControllers;
}

export function useInspectorRootBackNavigationController({
  bootstrap,
  controllers,
}: UseInspectorRootBackNavigationControllerInput) {
  const { localState, sessionFlow, settingsSupportState, shellSupport } =
    bootstrap;
  const historyWasOpenRef = useRef(false);
  const currentThreadRoute = useMemo(
    () =>
      buildThreadRouteSnapshot({
        activeThread: localState.abaAtiva,
        conversationLaudoId: localState.conversa?.laudoId ?? null,
        guidedInspectionDraft: localState.guidedInspectionDraft,
        threadHomeVisible: localState.threadHomeVisible,
      }),
    [
      localState.abaAtiva,
      localState.conversa?.laudoId,
      localState.guidedInspectionDraft,
      localState.threadHomeVisible,
    ],
  );

  useEffect(() => {
    const justOpenedHistory =
      !historyWasOpenRef.current && shellSupport.historicoAberto;
    const justClosedHistory =
      historyWasOpenRef.current && !shellSupport.historicoAberto;

    if (justOpenedHistory) {
      localState.setPendingHistoryThreadRoute(currentThreadRoute);
    } else if (
      justClosedHistory &&
      localState.pendingHistoryThreadRoute &&
      threadRouteSnapshotsEqual(
        localState.pendingHistoryThreadRoute,
        currentThreadRoute,
      )
    ) {
      localState.setPendingHistoryThreadRoute(null);
    }

    historyWasOpenRef.current = shellSupport.historicoAberto;
  }, [
    currentThreadRoute,
    localState,
    localState.pendingHistoryThreadRoute,
    shellSupport.historicoAberto,
  ]);

  useEffect(() => {
    const restoreThreadRouteSnapshot = async (
      snapshot: ThreadRouteSnapshot,
    ): Promise<void> => {
      const accessToken = sessionFlow.state.session?.accessToken || "";

      if (snapshot.threadHomeVisible) {
        await controllers.chatController.actions.handleAbrirNovoChat();
        return;
      }

      if (snapshot.conversationLaudoId && accessToken) {
        await controllers.chatController.actions.abrirLaudoPorId(
          accessToken,
          snapshot.conversationLaudoId,
        );
        localState.setAbaAtiva(snapshot.activeThread);
        return;
      }

      if (snapshot.guidedInspectionDraft) {
        await controllers.chatController.actions.handleAbrirNovoChat();
        controllers.guidedInspectionController.actions.handleStartGuidedInspection(
          {
            draft: snapshot.guidedInspectionDraft,
            ignoreActiveConversation: true,
            templateKey: snapshot.guidedInspectionDraft.templateKey,
          },
        );
        return;
      }

      await controllers.chatController.actions.handleIniciarChatLivre();
    };

    const subscription = BackHandler.addEventListener(
      "hardwareBackPress",
      () => {
        if (!sessionFlow.state.session) {
          return false;
        }

        if (shellSupport.keyboardHeight > 0) {
          Keyboard.dismiss();
          return true;
        }

        if (shellSupport.previewAnexoImagem) {
          shellSupport.setPreviewAnexoImagem(null);
          return true;
        }

        if (shellSupport.anexosAberto) {
          shellSupport.setAnexosAberto(false);
          return true;
        }

        if (settingsSupportState.navigationState.confirmSheet) {
          settingsSupportState.navigationActions.fecharConfirmacaoConfiguracao();
          return true;
        }

        if (settingsSupportState.navigationState.settingsSheet) {
          settingsSupportState.navigationActions.fecharSheetConfiguracao();
          return true;
        }

        if (localState.qualityGateVisible) {
          localState.setQualityGateVisible(false);
          return true;
        }

        if (shellSupport.centralAtividadeAberta) {
          shellSupport.setCentralAtividadeAberta(false);
          return true;
        }

        if (shellSupport.filaOfflineAberta) {
          shellSupport.setFilaOfflineAberta(false);
          return true;
        }

        if (shellSupport.configuracoesAberta) {
          const settingsNested =
            settingsSupportState.navigationState.settingsDrawerPage !==
              "overview" ||
            settingsSupportState.navigationState.settingsDrawerSection !==
              "all";

          if (settingsNested) {
            settingsSupportState.navigationActions.handleVoltarResumoConfiguracoes();
            return true;
          }

          shellSupport.fecharConfiguracoes();
          return true;
        }

        if (shellSupport.historicoAberto) {
          shellSupport.fecharHistorico({ limparBusca: true });
          return true;
        }

        if (
          localState.threadHomeVisible &&
          localState.threadHomeGuidedTemplatesVisible
        ) {
          localState.setThreadHomeGuidedTemplatesVisible(false);
          return true;
        }

        if (
          localState.abaAtiva === "mesa" ||
          localState.abaAtiva === "finalizar"
        ) {
          localState.setAbaAtiva("chat");
          return true;
        }

        if (localState.guidedInspectionDraft) {
          controllers.guidedInspectionController.actions.handleStopGuidedInspection();
          return true;
        }

        let nextHistory = [...localState.threadRouteHistory];
        while (
          nextHistory.length &&
          threadRouteSnapshotsEqual(
            nextHistory[nextHistory.length - 1],
            currentThreadRoute,
          )
        ) {
          nextHistory = nextHistory.slice(0, -1);
        }

        if (nextHistory.length !== localState.threadRouteHistory.length) {
          localState.setThreadRouteHistory(nextHistory);
        }

        const previousRoute = nextHistory[nextHistory.length - 1];
        if (previousRoute) {
          localState.setThreadRouteHistory(nextHistory.slice(0, -1));
          void restoreThreadRouteSnapshot(previousRoute);
          return true;
        }

        if (!localState.threadHomeVisible) {
          void controllers.chatController.actions.handleAbrirNovoChat();
          return true;
        }

        return false;
      },
    );

    return () => subscription.remove();
  }, [
    controllers,
    currentThreadRoute,
    localState,
    sessionFlow.state.session,
    settingsSupportState.navigationActions,
    settingsSupportState.navigationState.confirmSheet,
    settingsSupportState.navigationState.settingsDrawerPage,
    settingsSupportState.navigationState.settingsDrawerSection,
    settingsSupportState.navigationState.settingsSheet,
    shellSupport,
  ]);
}
