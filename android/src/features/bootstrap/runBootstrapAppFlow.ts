import type {
  MobileBootstrapResponse,
  MobileLaudoCard,
} from "../../types/mobile";
import type {
  MobileActivityNotification,
  OfflinePendingMessage,
} from "../chat/types";
import type { MobileReadCache } from "../common/readCacheTypes";
import type { MobileSessionState } from "../session/sessionTypes";

interface RunBootstrapAppFlowParams {
  aplicarPreferenciasLaudos: (
    itens: MobileLaudoCard[],
    fixadosIds: number[],
    ocultosIds: number[],
  ) => MobileLaudoCard[];
  carregarBootstrapMobile: (
    accessToken: string,
  ) => Promise<MobileBootstrapResponse>;
  erroSugereModoOffline: (error: unknown) => boolean;
  chatHistoryEnabled: boolean;
  deviceBackupEnabled: boolean;
  lerCacheLeituraLocal: (
    expectedEmail?: string | null,
  ) => Promise<MobileReadCache>;
  lerEstadoHistoricoLocal: () => Promise<{
    laudosFixadosIds: number[];
    historicoOcultoIds: number[];
  }>;
  lerFilaOfflineLocal: (
    expectedEmail?: string | null,
  ) => Promise<OfflinePendingMessage[]>;
  lerNotificacoesLocais: (
    expectedEmail?: string | null,
  ) => Promise<MobileActivityNotification[]>;
  limparCachePorPrivacidade: (cache: MobileReadCache) => MobileReadCache;
  obterItemSeguro: (key: string) => Promise<string | null>;
  pingApi: () => Promise<boolean>;
  removeToken: () => Promise<void>;
  CACHE_LEITURA_VAZIO: MobileReadCache;
  EMAIL_KEY: string;
  TOKEN_KEY: string;
  onSetStatusApi: (status: "online" | "offline") => void;
  onSetEmail: (email: string) => void;
  onSetFilaOffline: (itens: OfflinePendingMessage[]) => void;
  onSetNotificacoes: (itens: MobileActivityNotification[]) => void;
  onSetCacheLeitura: (cache: MobileReadCache) => void;
  onSetLaudosFixadosIds: (ids: number[]) => void;
  onSetHistoricoOcultoIds: (ids: number[]) => void;
  onMergeCacheBootstrap: (bootstrap: MobileBootstrapResponse) => void;
  onSetSession: (session: MobileSessionState) => void;
  onSetUsandoCacheOffline: (value: boolean) => void;
  onSetLaudosDisponiveis: (itens: MobileLaudoCard[]) => void;
  onSetErroLaudos: (value: string) => void;
}

export async function runBootstrapAppFlow({
  aplicarPreferenciasLaudos,
  carregarBootstrapMobile,
  chatHistoryEnabled,
  deviceBackupEnabled,
  erroSugereModoOffline,
  lerCacheLeituraLocal,
  lerEstadoHistoricoLocal,
  lerFilaOfflineLocal,
  lerNotificacoesLocais,
  limparCachePorPrivacidade,
  obterItemSeguro,
  pingApi,
  removeToken,
  CACHE_LEITURA_VAZIO,
  EMAIL_KEY,
  TOKEN_KEY,
  onSetStatusApi,
  onSetEmail,
  onSetFilaOffline,
  onSetNotificacoes,
  onSetCacheLeitura,
  onSetLaudosFixadosIds,
  onSetHistoricoOcultoIds,
  onMergeCacheBootstrap,
  onSetSession,
  onSetUsandoCacheOffline,
  onSetLaudosDisponiveis,
  onSetErroLaudos,
}: RunBootstrapAppFlowParams) {
  const [online, savedEmail, savedToken, estadoHistoricoLocal] =
    await Promise.all([
      pingApi(),
      obterItemSeguro(EMAIL_KEY),
      obterItemSeguro(TOKEN_KEY),
      lerEstadoHistoricoLocal(),
    ]);

  const [filaLocal, notificacoesLocais, cacheLocal] = await Promise.all([
    lerFilaOfflineLocal(savedEmail),
    lerNotificacoesLocais(savedEmail),
    lerCacheLeituraLocal(savedEmail),
  ]);

  onSetStatusApi(online ? "online" : "offline");
  if (savedEmail) {
    onSetEmail(savedEmail);
  }
  onSetFilaOffline(filaLocal);
  onSetNotificacoes(notificacoesLocais);
  onSetLaudosFixadosIds(estadoHistoricoLocal.laudosFixadosIds);
  onSetHistoricoOcultoIds(estadoHistoricoLocal.historicoOcultoIds);
  onSetCacheLeitura(
    !deviceBackupEnabled
      ? CACHE_LEITURA_VAZIO
      : !chatHistoryEnabled
        ? limparCachePorPrivacidade(cacheLocal)
        : cacheLocal,
  );

  if (!savedToken) {
    return;
  }

  try {
    const bootstrap = await carregarBootstrapMobile(savedToken);
    onSetUsandoCacheOffline(false);
    onMergeCacheBootstrap(bootstrap);
    onSetSession({ accessToken: savedToken, bootstrap });
  } catch (error) {
    const erroOffline = !online || erroSugereModoOffline(error);
    if (erroOffline && cacheLocal.bootstrap) {
      const laudosCache = aplicarPreferenciasLaudos(
        cacheLocal.laudos,
        estadoHistoricoLocal.laudosFixadosIds,
        estadoHistoricoLocal.historicoOcultoIds,
      );

      onSetSession({
        accessToken: savedToken,
        bootstrap: cacheLocal.bootstrap,
      });
      onSetLaudosDisponiveis(laudosCache);
      onSetUsandoCacheOffline(true);
      if (!laudosCache.length) {
        onSetErroLaudos("Sem internet. Nenhum laudo salvo localmente ainda.");
      }
      return;
    }

    if (!erroOffline) {
      await removeToken();
    }
  }
}
