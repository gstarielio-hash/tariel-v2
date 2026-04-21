import type { Dispatch, MutableRefObject, SetStateAction } from "react";

import type { MobileLaudoCard } from "../../types/mobile";
import { resolveInspectionEntryMode } from "../inspection/inspectionEntryMode";
import {
  guidedInspectionDraftToMobilePayload,
  mergeGuidedInspectionDraftWithRemote,
  type GuidedInspectionDraft,
} from "../inspection/guidedInspection";
import type { AppSettings } from "../../settings";
import type { StartGuidedInspectionOptions } from "../inspection/useInspectorRootGuidedInspectionController";

interface GuidedDraftCacheState {
  guidedInspectionDrafts?: Record<string, GuidedInspectionDraft>;
}

export function serializarGuidedDraft(
  draft: GuidedInspectionDraft | null | undefined,
): string {
  if (!draft) {
    return "";
  }
  return JSON.stringify(guidedInspectionDraftToMobilePayload(draft));
}

export function obterGuidedDraftDoCache(
  guidedInspectionDrafts: Record<string, GuidedInspectionDraft> | undefined,
  cacheKey: string,
): GuidedInspectionDraft | null {
  return guidedInspectionDrafts?.[cacheKey] || null;
}

export function sincronizarGuidedDraftRemotoNoCache<
  TCacheLeitura extends GuidedDraftCacheState,
>(params: {
  laudoId: number | null;
  cacheLeitura: TCacheLeitura;
  chaveCacheLaudo: (laudoId: number | null) => string;
  setCacheLeitura: Dispatch<SetStateAction<TCacheLeitura>>;
  guidedDraftRemoteSyncRef: MutableRefObject<Record<string, string>>;
  draftServidor: GuidedInspectionDraft | null;
}): GuidedInspectionDraft | null {
  if (!params.laudoId) {
    return null;
  }

  const cacheKey = params.chaveCacheLaudo(params.laudoId);
  const draftCacheado = obterGuidedDraftDoCache(
    params.cacheLeitura.guidedInspectionDrafts,
    cacheKey,
  );
  if (!params.draftServidor) {
    delete params.guidedDraftRemoteSyncRef.current[cacheKey];
    return draftCacheado;
  }

  const serializedServidor = serializarGuidedDraft(params.draftServidor);
  if (draftCacheado) {
    const draftMesclado = mergeGuidedInspectionDraftWithRemote(
      draftCacheado,
      params.draftServidor,
    );
    const serializedMesclado = serializarGuidedDraft(draftMesclado);
    if (serializedMesclado === serializedServidor) {
      params.guidedDraftRemoteSyncRef.current[cacheKey] = serializedServidor;
    }
    if (serializedMesclado !== serializarGuidedDraft(draftCacheado)) {
      params.setCacheLeitura((estadoAtual) => ({
        ...estadoAtual,
        guidedInspectionDrafts: {
          ...(estadoAtual.guidedInspectionDrafts || {}),
          [cacheKey]: draftMesclado,
        },
        updatedAt: new Date().toISOString(),
      }));
    }
    return draftMesclado;
  }

  params.guidedDraftRemoteSyncRef.current[cacheKey] = serializedServidor;
  params.setCacheLeitura((estadoAtual) => ({
    ...estadoAtual,
    guidedInspectionDrafts: {
      ...(estadoAtual.guidedInspectionDrafts || {}),
      [cacheKey]: params.draftServidor!,
    },
    updatedAt: new Date().toISOString(),
  }));
  return params.draftServidor;
}

export function restaurarContextoGuiadoDoCaso<
  TCacheLeitura extends GuidedDraftCacheState,
>(params: {
  laudoId: number | null;
  laudoCard: MobileLaudoCard | null | undefined;
  draftServidor?: GuidedInspectionDraft | null;
  cacheLeitura: TCacheLeitura;
  laudosDisponiveis: MobileLaudoCard[];
  chaveCacheLaudo: (laudoId: number | null) => string;
  setCacheLeitura: Dispatch<SetStateAction<TCacheLeitura>>;
  guidedDraftRemoteSyncRef: MutableRefObject<Record<string, string>>;
  entryModePreference?: AppSettings["ai"]["entryModePreference"];
  rememberLastCaseMode?: boolean;
  clearGuidedInspectionDraft: () => void;
  startGuidedInspection: (options?: StartGuidedInspectionOptions) => void;
}) {
  const restoredDraft = sincronizarGuidedDraftRemotoNoCache({
    laudoId: params.laudoId,
    cacheLeitura: params.cacheLeitura,
    chaveCacheLaudo: params.chaveCacheLaudo,
    setCacheLeitura: params.setCacheLeitura,
    guidedDraftRemoteSyncRef: params.guidedDraftRemoteSyncRef,
    draftServidor: params.draftServidor || null,
  });
  const entryMode = resolveInspectionEntryMode({
    activeCase: params.laudoCard,
    cards: params.laudosDisponiveis,
    preference: params.entryModePreference,
    rememberLastCaseMode: params.rememberLastCaseMode,
  });

  if (entryMode.effective !== "evidence_first") {
    params.clearGuidedInspectionDraft();
    return entryMode;
  }

  if (restoredDraft) {
    params.startGuidedInspection({
      draft: restoredDraft,
      ignoreActiveConversation: true,
      tipoTemplate: params.laudoCard?.tipo_template || null,
    });
    return entryMode;
  }

  params.startGuidedInspection({
    ignoreActiveConversation: true,
    tipoTemplate: params.laudoCard?.tipo_template || null,
  });
  return entryMode;
}
