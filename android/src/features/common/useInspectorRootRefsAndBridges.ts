import { useRef } from "react";
import type { ScrollView, TextInput } from "react-native";

import type { MobileLaudoCard } from "../../types/mobile";
import type { MobileActivityNotification } from "../chat/types";

export function useInspectorRootRefsAndBridges(params: {
  onOpenSystemSettings: () => void | Promise<void>;
}) {
  const scrollRef = useRef<ScrollView | null>(null);
  const carregarListaLaudosRef = useRef<
    (accessToken: string, silencioso?: boolean) => Promise<MobileLaudoCard[]>
  >(async () => []);
  const emailInputRef = useRef<TextInput | null>(null);
  const senhaInputRef = useRef<TextInput | null>(null);
  const registrarNotificacoesRef = useRef<
    (items: MobileActivityNotification[]) => void
  >(() => undefined);

  return {
    carregarListaLaudosRef,
    emailInputRef,
    onOpenSystemSettings: () => {
      void params.onOpenSystemSettings();
    },
    onRegistrarNotificacoesViaRef: (items: MobileActivityNotification[]) => {
      registrarNotificacoesRef.current(items);
    },
    onRegisterCarregarListaLaudos: (
      handler: (
        accessToken: string,
        silencioso?: boolean,
      ) => Promise<MobileLaudoCard[]>,
    ) => {
      carregarListaLaudosRef.current = handler;
    },
    onScheduleWithTimeout: (callback: () => void, delayMs: number) => {
      setTimeout(callback, delayMs);
    },
    registrarNotificacoesRef,
    scrollRef,
    senhaInputRef,
  };
}
