import * as FileSystem from "expo-file-system/legacy";
import * as IntentLauncher from "expo-intent-launcher";
import * as Sharing from "expo-sharing";
import type { Dispatch, SetStateAction } from "react";
import { Platform } from "react-native";

import type { MobileAttachment } from "../../types/mobile";
import { gateHeavyTransfer } from "./network";
import {
  capturarImagemRascunhoFlow,
  selecionarDocumentoRascunhoFlow,
  selecionarImagemRascunhoFlow,
} from "./attachmentDraftFlows";
import {
  ehImagemAnexo,
  nomeExibicaoAnexo,
  urlAnexoAbsoluta,
} from "./attachmentUtils";
import {
  isImageAttachmentAllowed,
  isDocumentAttachmentAllowed,
  resolveImageAttachmentPolicyLabel,
  resolveDocumentAttachmentPolicyLabel,
} from "./attachmentPolicy";
import type { ActiveThread, ChatState, ComposerAttachment } from "./types";

interface AttachmentPreviewState {
  titulo: string;
  uri: string;
}

const ANDROID_FLAG_GRANT_READ_URI_PERMISSION = 1;

function extrairCabecalhoDownload(
  headers: Record<string, string> | undefined,
  nome: string,
): string {
  if (!headers) {
    return "";
  }

  const alvo = nome.toLowerCase();
  for (const [chave, valor] of Object.entries(headers)) {
    if (chave.toLowerCase() === alvo) {
      return String(valor || "").trim();
    }
  }
  return "";
}

async function validarArquivoBaixado(
  resultado: Awaited<ReturnType<typeof FileSystem.downloadAsync>>,
) {
  const status = Number((resultado as { status?: number }).status || 0);
  const headers = ((resultado as { headers?: Record<string, string> })
    .headers || undefined) as Record<string, string> | undefined;
  const contentType = extrairCabecalhoDownload(headers, "content-type")
    .split(";")[0]
    .trim()
    .toLowerCase();

  if (
    (status >= 400 && status <= 599) ||
    contentType === "application/json" ||
    contentType === "text/plain"
  ) {
    const raw = await FileSystem.readAsStringAsync(resultado.uri);
    await FileSystem.deleteAsync(resultado.uri, { idempotent: true });

    if (raw.trim()) {
      try {
        const payload = JSON.parse(raw) as { detail?: unknown };
        if (typeof payload.detail === "string" && payload.detail.trim()) {
          throw new Error(payload.detail.trim());
        }
      } catch (parseError) {
        if (parseError instanceof Error && parseError.message.trim()) {
          throw parseError;
        }
        throw new Error(raw.trim());
      }
    }

    throw new Error("Esse anexo não está disponível para o app agora.");
  }
}

interface UseAttachmentControllerParams {
  abaAtiva: ActiveThread;
  arquivosPermitidos: boolean;
  autoUploadAttachments: boolean;
  cameraPermitida: boolean;
  conversaAtiva: ChatState | null;
  preparandoAnexo: boolean;
  sessionAccessToken: string | null;
  statusApi: string;
  uploadArquivosAtivo: boolean;
  wifiOnlySync: boolean;
  imageQuality: number;
  disableAggressiveDownloads: boolean;
  erroSugereModoOffline: (erro: unknown) => boolean;
  inferirExtensaoAnexo: (anexo: MobileAttachment) => string;
  montarAnexoDocumentoLocal: (
    asset: import("expo-document-picker").DocumentPickerAsset,
    resumo: string,
  ) => ComposerAttachment;
  montarAnexoDocumentoMesa: (
    asset: import("expo-document-picker").DocumentPickerAsset,
  ) => ComposerAttachment;
  montarAnexoImagem: (
    asset: import("expo-image-picker").ImagePickerAsset,
    resumo: string,
  ) => ComposerAttachment;
  nomeArquivoSeguro: (nome: string, fallback: string) => string;
  onBuildAttachmentKey: (anexo: MobileAttachment, fallback: string) => string;
  onShowAlert: (
    title: string,
    message?: string,
    buttons?: Array<{
      text: string;
      style?: "default" | "cancel" | "destructive";
      onPress?: () => void;
    }>,
  ) => void;
  setAnexosAberto: (value: boolean) => void;
  setAnexoAbrindoChave: Dispatch<SetStateAction<string>>;
  setAnexoMesaRascunho: Dispatch<SetStateAction<ComposerAttachment | null>>;
  setAnexoRascunho: Dispatch<SetStateAction<ComposerAttachment | null>>;
  setErroConversa: (value: string) => void;
  setPreparandoAnexo: (value: boolean) => void;
  setPreviewAnexoImagem: Dispatch<
    SetStateAction<AttachmentPreviewState | null>
  >;
  setStatusApi: (value: "online" | "offline") => void;
}

export function useAttachmentController({
  abaAtiva,
  arquivosPermitidos,
  autoUploadAttachments,
  cameraPermitida,
  conversaAtiva,
  preparandoAnexo,
  sessionAccessToken,
  statusApi,
  uploadArquivosAtivo,
  wifiOnlySync,
  imageQuality,
  disableAggressiveDownloads,
  erroSugereModoOffline,
  inferirExtensaoAnexo,
  montarAnexoDocumentoLocal,
  montarAnexoDocumentoMesa,
  montarAnexoImagem,
  nomeArquivoSeguro,
  onBuildAttachmentKey,
  onShowAlert,
  setAnexosAberto,
  setAnexoAbrindoChave,
  setAnexoMesaRascunho,
  setAnexoRascunho,
  setErroConversa,
  setPreparandoAnexo,
  setPreviewAnexoImagem,
  setStatusApi,
}: UseAttachmentControllerParams) {
  const documentoPermitido = isDocumentAttachmentAllowed({
    activeThread: abaAtiva,
    conversation: conversaAtiva,
  });
  const imagemPermitidaPelaPolitica = isImageAttachmentAllowed({
    conversation: conversaAtiva,
  });
  const detalhePoliticaImagem = resolveImageAttachmentPolicyLabel({
    conversation: conversaAtiva,
  });
  const detalhePoliticaDocumento = resolveDocumentAttachmentPolicyLabel({
    activeThread: abaAtiva,
    conversation: conversaAtiva,
  });

  function handleAbrirSeletorAnexo() {
    if (!uploadArquivosAtivo) {
      onShowAlert(
        "Uploads desativados",
        "O envio de arquivos está desligado nas preferências do app. Reative em Configurações > Recursos avançados.",
      );
      return;
    }
    if (!arquivosPermitidos) {
      onShowAlert(
        "Arquivos bloqueados",
        "O acesso a arquivos foi desativado neste dispositivo. Ajuste isso em Configurações > Permissões.",
      );
      return;
    }
    setAnexosAberto(true);
  }

  async function handleSelecionarImagem() {
    if (!sessionAccessToken) {
      return;
    }

    await selecionarImagemRascunhoFlow({
      abaAtiva,
      preparandoAnexo,
      uploadArquivosAtivo,
      imageQuality,
      arquivosPermitidos,
      montarAnexoImagem,
      onSetAnexoMesaRascunho: setAnexoMesaRascunho,
      onSetAnexoRascunho: setAnexoRascunho,
      onSetErroConversa: setErroConversa,
      onSetPreparandoAnexo: setPreparandoAnexo,
    });
  }

  async function handleCapturarImagem() {
    if (!sessionAccessToken) {
      return;
    }

    await capturarImagemRascunhoFlow({
      abaAtiva,
      preparandoAnexo,
      uploadArquivosAtivo,
      imageQuality,
      cameraPermitida,
      montarAnexoImagem,
      onSetAnexoMesaRascunho: setAnexoMesaRascunho,
      onSetAnexoRascunho: setAnexoRascunho,
      onSetErroConversa: setErroConversa,
      onSetPreparandoAnexo: setPreparandoAnexo,
    });
  }

  async function handleSelecionarDocumento() {
    if (!sessionAccessToken) {
      return;
    }

    const gateDocumento = await gateHeavyTransfer({
      wifiOnlySync,
      requiresHeavyTransfer: autoUploadAttachments,
      blockedMessage:
        "O upload automático de documentos está restrito ao Wi-Fi neste dispositivo.",
    });
    const autoUploadDocuments = autoUploadAttachments && gateDocumento.allowed;
    if (autoUploadAttachments && !gateDocumento.allowed) {
      setErroConversa(
        gateDocumento.reason ||
          "Documento será mantido localmente até haver uma rede adequada.",
      );
    }

    await selecionarDocumentoRascunhoFlow({
      abaAtiva,
      preparandoAnexo,
      uploadArquivosAtivo,
      imageQuality,
      arquivosPermitidos,
      autoUploadDocuments,
      sessionAccessToken,
      statusApi,
      erroSugereModoOffline,
      montarAnexoDocumentoLocal,
      montarAnexoDocumentoMesa,
      onSetAnexoMesaRascunho: setAnexoMesaRascunho,
      onSetAnexoRascunho: setAnexoRascunho,
      onSetErroConversa: setErroConversa,
      onSetPreparandoAnexo: setPreparandoAnexo,
      onSetStatusOffline: () => {
        setStatusApi("offline");
      },
    });
  }

  async function handleEscolherAnexo(
    opcao: "camera" | "galeria" | "documento",
  ) {
    setAnexosAberto(false);
    if (!uploadArquivosAtivo) {
      return;
    }
    if (opcao === "camera" && !cameraPermitida) {
      onShowAlert(
        "Câmera indisponível",
        "Ative a câmera em Configurações > Permissões para anexar fotos.",
      );
      return;
    }
    if (
      (opcao === "camera" || opcao === "galeria") &&
      !imagemPermitidaPelaPolitica
    ) {
      onShowAlert(
        "Imagem indisponível",
        detalhePoliticaImagem ||
          "Uploads bloqueados pela politica ativa deste caso.",
      );
      return;
    }
    if (opcao !== "camera" && !arquivosPermitidos) {
      onShowAlert(
        "Arquivos indisponíveis",
        "Ative o acesso a arquivos em Configurações > Permissões.",
      );
      return;
    }
    if (opcao === "camera") {
      await handleCapturarImagem();
      return;
    }
    if (opcao === "galeria") {
      await handleSelecionarImagem();
      return;
    }
    if (!documentoPermitido) {
      onShowAlert("Documento indisponível", detalhePoliticaDocumento);
      return;
    }
    await handleSelecionarDocumento();
  }

  async function handleAbrirAnexo(anexo: MobileAttachment) {
    if (!sessionAccessToken) {
      return;
    }

    const absoluteUrl = urlAnexoAbsoluta(anexo.url);
    if (!absoluteUrl) {
      onShowAlert(
        "Anexo",
        "Esse anexo ainda não está disponível para abertura no app.",
      );
      return;
    }

    if (ehImagemAnexo(anexo)) {
      setPreviewAnexoImagem({
        titulo: nomeExibicaoAnexo(anexo, "Imagem"),
        uri: absoluteUrl,
      });
      return;
    }

    const key = onBuildAttachmentKey(anexo, "anexo");
    setAnexoAbrindoChave(key);

    try {
      const gateDownload = await gateHeavyTransfer({
        wifiOnlySync,
        requiresHeavyTransfer: disableAggressiveDownloads,
        blockedMessage:
          "O download deste anexo aguarda Wi-Fi por causa da economia de dados ativa.",
      });
      if (!gateDownload.allowed) {
        onShowAlert(
          "Anexo",
          gateDownload.reason ||
            "Esse anexo precisa de uma rede adequada para abrir.",
        );
        return;
      }

      const baseDir = `${FileSystem.cacheDirectory || ""}tariel-anexos`;
      await FileSystem.makeDirectoryAsync(baseDir, { intermediates: true });

      const extensao = inferirExtensaoAnexo(anexo);
      const nomeBase = nomeArquivoSeguro(
        nomeExibicaoAnexo(anexo, "anexo"),
        `anexo${extensao}`,
      );
      const nomeFinal =
        extensao && !nomeBase.toLowerCase().endsWith(extensao.toLowerCase())
          ? `${nomeBase}${extensao}`
          : nomeBase;
      const destino = `${baseDir}/${Date.now()}-${nomeFinal}`;

      const resultado = await FileSystem.downloadAsync(absoluteUrl, destino, {
        headers: {
          Authorization: `Bearer ${sessionAccessToken}`,
        },
      });
      await validarArquivoBaixado(resultado);

      if (Platform.OS === "android") {
        let androidOpenError: unknown = null;
        try {
          const contentUri = await FileSystem.getContentUriAsync(resultado.uri);
          await IntentLauncher.startActivityAsync(
            "android.intent.action.VIEW",
            {
              data: contentUri,
              flags: ANDROID_FLAG_GRANT_READ_URI_PERMISSION,
            },
          );
          return;
        } catch (error) {
          androidOpenError = error;
        }

        try {
          const contentUri = await FileSystem.getContentUriAsync(resultado.uri);
          await IntentLauncher.startActivityAsync(
            "android.intent.action.VIEW",
            {
              data: contentUri,
              type: anexo.mime_type || undefined,
              flags: ANDROID_FLAG_GRANT_READ_URI_PERMISSION,
            },
          );
          return;
        } catch (error) {
          androidOpenError = androidOpenError || error;
          console.warn("attachment_open_android_failed", androidOpenError);
        }
      }

      const sharingDisponivel = await Sharing.isAvailableAsync();
      if (!sharingDisponivel) {
        onShowAlert("Anexo pronto", `Arquivo salvo em ${resultado.uri}`);
        return;
      }

      await Sharing.shareAsync(resultado.uri, {
        mimeType: anexo.mime_type || undefined,
        dialogTitle: `Abrir ${nomeExibicaoAnexo(anexo, "anexo")}`,
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Não foi possível abrir o anexo no app.";
      onShowAlert("Anexo", message);
    } finally {
      setAnexoAbrindoChave((estadoAtual) =>
        estadoAtual === key ? "" : estadoAtual,
      );
    }
  }

  return {
    handleAbrirAnexo,
    handleAbrirSeletorAnexo,
    handleCapturarImagem,
    handleEscolherAnexo,
    handleSelecionarDocumento,
    handleSelecionarImagem,
  };
}
