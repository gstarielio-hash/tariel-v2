import { useEffect, useState, type MutableRefObject } from "react";
import { Keyboard, Platform } from "react-native";

import { useSidePanelsController } from "./useSidePanelsController";

export interface AttachmentPreviewState {
  titulo: string;
  uri: string;
}

interface ScrollRefLike {
  scrollToEnd: (options?: { animated?: boolean }) => void;
}

interface UseInspectorShellControllerParams {
  appLocked: boolean;
  onClearTransientSettingsPresentationState: () => void;
  onClearTransientSettingsUiPreservingReauth: () => void;
  onResetAfterSessionEnded: () => void;
  resetSettingsNavigation: () => void;
  scrollRef: MutableRefObject<ScrollRefLike | null>;
  sessionActive: boolean;
  sessionLoading: boolean;
}

export function useInspectorShellController({
  appLocked,
  onClearTransientSettingsPresentationState,
  onClearTransientSettingsUiPreservingReauth,
  onResetAfterSessionEnded,
  resetSettingsNavigation,
  scrollRef,
  sessionActive,
  sessionLoading,
}: UseInspectorShellControllerParams) {
  const [centralAtividadeAberta, setCentralAtividadeAberta] = useState(false);
  const [historicoAberto, setHistoricoAberto] = useState(false);
  const [buscaHistorico, setBuscaHistorico] = useState("");
  const [, setHistorySearchFocused] = useState(false);
  const [filaOfflineAberta, setFilaOfflineAberta] = useState(false);
  const [configuracoesAberta, setConfiguracoesAberta] = useState(false);
  const [anexosAberto, setAnexosAberto] = useState(false);
  const [introVisivel, setIntroVisivel] = useState(true);
  const [keyboardHeight, setKeyboardHeight] = useState(0);
  const [previewAnexoImagem, setPreviewAnexoImagem] =
    useState<AttachmentPreviewState | null>(null);

  const sidePanels = useSidePanelsController({
    configuracoesAberta,
    historicoAberto,
    keyboardHeight,
    resetSettingsNavigation,
    setHistorySearchFocused,
    setBuscaHistorico,
    setConfiguracoesAberta,
    setHistoricoAberto,
  });

  useEffect(() => {
    if (!appLocked) {
      return;
    }
    setAnexosAberto(false);
    setCentralAtividadeAberta(false);
    setFilaOfflineAberta(false);
    setPreviewAnexoImagem(null);
    onClearTransientSettingsUiPreservingReauth();
    sidePanels.fecharPaineisLaterais();
  }, [appLocked]);

  useEffect(() => {
    if (sessionActive || sessionLoading) {
      return;
    }

    onResetAfterSessionEnded();
    setPreviewAnexoImagem(null);
    setCentralAtividadeAberta(false);
    onClearTransientSettingsPresentationState();
    sidePanels.resetPainelLateralState();
  }, [sessionActive, sessionLoading]);

  useEffect(() => {
    const showEvent =
      Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvent =
      Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";

    const showSubscription = Keyboard.addListener(showEvent, (event) => {
      setKeyboardHeight(event.endCoordinates.height);
    });
    const hideSubscription = Keyboard.addListener(hideEvent, () => {
      setKeyboardHeight(0);
    });

    return () => {
      showSubscription.remove();
      hideSubscription.remove();
    };
  }, []);

  useEffect(() => {
    if (!sessionActive || keyboardHeight <= 0) {
      return;
    }

    const timeout = setTimeout(() => {
      scrollRef.current?.scrollToEnd({ animated: true });
    }, 120);

    return () => clearTimeout(timeout);
  }, [keyboardHeight, scrollRef, sessionActive]);

  return {
    anexosAberto,
    buscaHistorico,
    centralAtividadeAberta,
    configuracoesAberta,
    filaOfflineAberta,
    historicoAberto,
    introVisivel,
    keyboardHeight,
    previewAnexoImagem,
    setAnexosAberto,
    setBuscaHistorico,
    setCentralAtividadeAberta,
    setFilaOfflineAberta,
    setIntroVisivel,
    setPreviewAnexoImagem,
    ...sidePanels,
  };
}
