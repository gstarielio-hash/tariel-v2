import { useEffect, useRef, useState } from "react";

import {
  carregarBootstrapMobile,
  loginInspectorMobile,
  logoutInspectorMobile,
  pingApi,
} from "../../config/api";
import { invalidateMobileV2CapabilitiesCache } from "../../config/mobileV2Rollout";
import type {
  MobileBootstrapResponse,
  MobileLaudoCard,
  MobileMesaMessage,
} from "../../types/mobile";
import type {
  ChatState,
  MobileActivityNotification,
  OfflinePendingMessage,
} from "../chat/types";
import type { MobileReadCache } from "../common/readCacheTypes";
import { EMAIL_KEY, TOKEN_KEY } from "../InspectorMobileApp.constants";
import { runBootstrapAppFlow } from "../bootstrap/runBootstrapAppFlow";
import {
  removeSecureItem,
  readSecureItem,
  writeSecureItem,
} from "./sessionStorage";
import type { InspectorSessionState, MobileSessionState } from "./sessionTypes";

const SESSION_PERSISTENCE_TIMEOUT_MS = 4_000;

function withTimeout<T>(
  promise: Promise<T> | T,
  timeoutMs: number,
  timeoutMessage: string,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(timeoutMessage));
    }, timeoutMs);

    Promise.resolve(promise).then(
      (value) => {
        clearTimeout(timeoutId);
        resolve(value);
      },
      (error) => {
        clearTimeout(timeoutId);
        reject(error);
      },
    );
  });
}

interface LocalHistoryUiStateSnapshot {
  laudosFixadosIds: number[];
  historicoOcultoIds: number[];
}

export interface UseInspectorSessionParams {
  settingsHydrated: boolean;
  chatHistoryEnabled: boolean;
  deviceBackupEnabled: boolean;
  aplicarPreferenciasLaudos: (
    itens: MobileLaudoCard[],
    fixadosIds: number[],
    ocultosIds: number[],
  ) => MobileLaudoCard[];
  chaveCacheLaudo: (laudoId: number | null) => string;
  erroSugereModoOffline: (error: unknown) => boolean;
  lerCacheLeituraLocal: (
    expectedEmail?: string | null,
  ) => Promise<MobileReadCache>;
  lerEstadoHistoricoLocal: () => Promise<LocalHistoryUiStateSnapshot>;
  lerFilaOfflineLocal: (
    expectedEmail?: string | null,
  ) => Promise<OfflinePendingMessage[]>;
  lerNotificacoesLocais: (
    expectedEmail?: string | null,
  ) => Promise<MobileActivityNotification[]>;
  limparCachePorPrivacidade: (cache: MobileReadCache) => MobileReadCache;
  cacheLeituraVazio: MobileReadCache;
  onSetFilaOffline: (items: OfflinePendingMessage[]) => void;
  onSetNotificacoes: (items: MobileActivityNotification[]) => void;
  onSetCacheLeitura: (cache: MobileReadCache) => void;
  onSetLaudosFixadosIds: (ids: number[]) => void;
  onSetHistoricoOcultoIds: (ids: number[]) => void;
  onSetUsandoCacheOffline: (value: boolean) => void;
  onSetLaudosDisponiveis: (items: MobileLaudoCard[]) => void;
  onSetConversa: (conversa: ChatState | null) => void;
  onSetMensagensMesa: (items: MobileMesaMessage[]) => void;
  onSetLaudoMesaCarregado: (laudoId: number | null) => void;
  onSetErroLaudos: (value: string) => void;
  onApplyBootstrapCache: (bootstrap: MobileBootstrapResponse) => void;
  onAfterLoginSuccess?: () => void;
  onResetAfterLogout?: () => void | Promise<void>;
}

export function useInspectorSession(params: UseInspectorSessionParams) {
  const paramsRef = useRef(params);
  paramsRef.current = params;

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [lembrar, setLembrar] = useState(true);
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [statusApi, setStatusApi] =
    useState<InspectorSessionState["statusApi"]>("checking");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [entrando, setEntrando] = useState(false);
  const [loginStage, setLoginStage] =
    useState<InspectorSessionState["loginStage"]>("idle");
  const [session, setSession] = useState<MobileSessionState | null>(null);

  async function bootstrapApp() {
    const current = paramsRef.current;
    setCarregando(true);
    setErro("");
    invalidateMobileV2CapabilitiesCache();
    await runBootstrapAppFlow({
      aplicarPreferenciasLaudos: current.aplicarPreferenciasLaudos,
      carregarBootstrapMobile,
      chatHistoryEnabled: current.chatHistoryEnabled,
      deviceBackupEnabled: current.deviceBackupEnabled,
      erroSugereModoOffline: current.erroSugereModoOffline,
      lerCacheLeituraLocal: current.lerCacheLeituraLocal,
      lerEstadoHistoricoLocal: current.lerEstadoHistoricoLocal,
      lerFilaOfflineLocal: current.lerFilaOfflineLocal,
      lerNotificacoesLocais: current.lerNotificacoesLocais,
      limparCachePorPrivacidade: current.limparCachePorPrivacidade,
      obterItemSeguro: readSecureItem,
      pingApi,
      removeToken: async () => {
        await removeSecureItem(TOKEN_KEY);
      },
      CACHE_LEITURA_VAZIO: current.cacheLeituraVazio,
      EMAIL_KEY,
      TOKEN_KEY,
      onSetStatusApi: setStatusApi,
      onSetEmail: setEmail,
      onSetFilaOffline: current.onSetFilaOffline,
      onSetNotificacoes: current.onSetNotificacoes,
      onSetCacheLeitura: current.onSetCacheLeitura,
      onSetLaudosFixadosIds: current.onSetLaudosFixadosIds,
      onSetHistoricoOcultoIds: current.onSetHistoricoOcultoIds,
      onMergeCacheBootstrap: current.onApplyBootstrapCache,
      onSetSession: setSession,
      onSetUsandoCacheOffline: current.onSetUsandoCacheOffline,
      onSetLaudosDisponiveis: current.onSetLaudosDisponiveis,
      onSetErroLaudos: current.onSetErroLaudos,
    });
    setCarregando(false);
  }

  useEffect(() => {
    if (!params.settingsHydrated) {
      return;
    }
    void bootstrapApp();
  }, [params.settingsHydrated]);

  async function handleLogin() {
    if (!email.trim() || !senha.trim()) {
      setErro("Preencha e-mail e senha para entrar no app.");
      setLoginStage("error");
      return;
    }

    const current = paramsRef.current;
    setEntrando(true);
    setErro("");
    setLoginStage("authenticating");

    try {
      const login = await loginInspectorMobile(email, senha, lembrar);
      setLoginStage("loading_bootstrap");
      const bootstrap = await carregarBootstrapMobile(login.access_token);
      invalidateMobileV2CapabilitiesCache(login.access_token);

      setSenha("");
      current.onSetUsandoCacheOffline(false);
      current.onApplyBootstrapCache(bootstrap);
      current.onAfterLoginSuccess?.();
      setSession({ accessToken: login.access_token, bootstrap });
      setLoginStage("persisting_session");

      const emailLimpo = email.trim();
      void Promise.allSettled(
        lembrar
          ? [
              withTimeout(
                writeSecureItem(TOKEN_KEY, login.access_token),
                SESSION_PERSISTENCE_TIMEOUT_MS,
                "Tempo limite excedido ao persistir o token local.",
              ),
              withTimeout(
                writeSecureItem(EMAIL_KEY, emailLimpo),
                SESSION_PERSISTENCE_TIMEOUT_MS,
                "Tempo limite excedido ao persistir o e-mail local.",
              ),
            ]
          : [
              withTimeout(
                removeSecureItem(TOKEN_KEY),
                SESSION_PERSISTENCE_TIMEOUT_MS,
                "Tempo limite excedido ao limpar o token local.",
              ),
              withTimeout(
                removeSecureItem(EMAIL_KEY),
                SESSION_PERSISTENCE_TIMEOUT_MS,
                "Tempo limite excedido ao limpar o e-mail local.",
              ),
            ],
      ).then((results) => {
        const errors = results
          .map((result) =>
            result.status === "rejected" ? result.reason : null,
          )
          .filter((item): item is unknown => item !== null);
        if (errors.length) {
          console.warn("Falha ao persistir a sessão local do app.", errors[0]);
        }
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Falha ao autenticar no app.";
      setErro(message);
      setLoginStage("error");
    } finally {
      setEntrando(false);
    }
  }

  async function handleLogout() {
    const current = paramsRef.current;
    try {
      if (session) {
        await logoutInspectorMobile(session.accessToken);
      }
    } catch {
      // Mantem a saida local mesmo se o backend ja tiver expirado o token.
    } finally {
      await removeSecureItem(TOKEN_KEY);
      invalidateMobileV2CapabilitiesCache(session?.accessToken ?? null);
      setSession(null);
      await current.onResetAfterLogout?.();
    }
  }

  return {
    state: {
      email,
      senha,
      lembrar,
      mostrarSenha,
      statusApi,
      erro,
      carregando,
      entrando,
      loginStage,
      session,
    } satisfies InspectorSessionState,
    actions: {
      bootstrapApp,
      handleLogin,
      handleLogout,
      setCarregando,
      setEmail,
      setEntrando,
      setErro,
      setLembrar,
      setMostrarSenha,
      setSenha,
      setSession,
      setStatusApi,
    },
  };
}
