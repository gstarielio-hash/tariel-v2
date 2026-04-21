import { useAttachmentController } from "./useAttachmentController";

type AttachmentControllerParams = Parameters<typeof useAttachmentController>[0];

interface UseInspectorRootAttachmentControllerInput {
  accessState: Pick<
    AttachmentControllerParams,
    | "abaAtiva"
    | "arquivosPermitidos"
    | "cameraPermitida"
    | "conversaAtiva"
    | "sessionAccessToken"
    | "statusApi"
    | "uploadArquivosAtivo"
    | "wifiOnlySync"
  >;
  policyState: Pick<
    AttachmentControllerParams,
    | "autoUploadAttachments"
    | "disableAggressiveDownloads"
    | "erroSugereModoOffline"
    | "imageQuality"
    | "preparandoAnexo"
  >;
  builderState: Pick<
    AttachmentControllerParams,
    | "inferirExtensaoAnexo"
    | "montarAnexoDocumentoLocal"
    | "montarAnexoDocumentoMesa"
    | "montarAnexoImagem"
    | "nomeArquivoSeguro"
    | "onBuildAttachmentKey"
    | "onShowAlert"
  >;
  setterState: Pick<
    AttachmentControllerParams,
    | "setAnexosAberto"
    | "setAnexoAbrindoChave"
    | "setAnexoMesaRascunho"
    | "setAnexoRascunho"
    | "setErroConversa"
    | "setPreparandoAnexo"
    | "setPreviewAnexoImagem"
    | "setStatusApi"
  >;
}

export function useInspectorRootAttachmentController({
  accessState,
  policyState,
  builderState,
  setterState,
}: UseInspectorRootAttachmentControllerInput) {
  return useAttachmentController({
    abaAtiva: accessState.abaAtiva,
    arquivosPermitidos: accessState.arquivosPermitidos,
    autoUploadAttachments: policyState.autoUploadAttachments,
    cameraPermitida: accessState.cameraPermitida,
    conversaAtiva: accessState.conversaAtiva,
    preparandoAnexo: policyState.preparandoAnexo,
    sessionAccessToken: accessState.sessionAccessToken,
    statusApi: accessState.statusApi,
    uploadArquivosAtivo: accessState.uploadArquivosAtivo,
    wifiOnlySync: accessState.wifiOnlySync,
    imageQuality: policyState.imageQuality,
    disableAggressiveDownloads: policyState.disableAggressiveDownloads,
    erroSugereModoOffline: policyState.erroSugereModoOffline,
    inferirExtensaoAnexo: builderState.inferirExtensaoAnexo,
    montarAnexoDocumentoLocal: builderState.montarAnexoDocumentoLocal,
    montarAnexoDocumentoMesa: builderState.montarAnexoDocumentoMesa,
    montarAnexoImagem: builderState.montarAnexoImagem,
    nomeArquivoSeguro: builderState.nomeArquivoSeguro,
    onBuildAttachmentKey: builderState.onBuildAttachmentKey,
    onShowAlert: builderState.onShowAlert,
    setAnexosAberto: setterState.setAnexosAberto,
    setAnexoAbrindoChave: setterState.setAnexoAbrindoChave,
    setAnexoMesaRascunho: setterState.setAnexoMesaRascunho,
    setAnexoRascunho: setterState.setAnexoRascunho,
    setErroConversa: setterState.setErroConversa,
    setPreparandoAnexo: setterState.setPreparandoAnexo,
    setPreviewAnexoImagem: setterState.setPreviewAnexoImagem,
    setStatusApi: setterState.setStatusApi,
  });
}
