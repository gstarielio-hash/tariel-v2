import { renderHook } from "@testing-library/react-native";

const mockHandleAbrirAnexo = jest.fn();
const mockHandleEscolherAnexo = jest.fn();

jest.mock("./useAttachmentController", () => ({
  useAttachmentController: jest.fn(() => ({
    handleAbrirAnexo: mockHandleAbrirAnexo,
    handleAbrirSeletorAnexo: jest.fn(),
    handleEscolherAnexo: mockHandleEscolherAnexo,
  })),
}));

import { useAttachmentController } from "./useAttachmentController";
import { useInspectorRootAttachmentController } from "./useInspectorRootAttachmentController";

function criarInput() {
  return {
    accessState: {
      abaAtiva: "chat" as const,
      arquivosPermitidos: true,
      cameraPermitida: true,
      conversaAtiva: null,
      sessionAccessToken: "token-123",
      statusApi: "online",
      uploadArquivosAtivo: true,
      wifiOnlySync: false,
    },
    policyState: {
      autoUploadAttachments: true,
      disableAggressiveDownloads: false,
      erroSugereModoOffline: jest.fn().mockReturnValue(false),
      imageQuality: 0.7,
      preparandoAnexo: false,
    },
    builderState: {
      inferirExtensaoAnexo: jest.fn().mockReturnValue(".pdf"),
      montarAnexoDocumentoLocal: jest.fn(),
      montarAnexoDocumentoMesa: jest.fn(),
      montarAnexoImagem: jest.fn(),
      nomeArquivoSeguro: jest.fn().mockReturnValue("arquivo"),
      onBuildAttachmentKey: jest.fn().mockReturnValue("anexo-1"),
      onShowAlert: jest.fn(),
    },
    setterState: {
      setAnexosAberto: jest.fn(),
      setAnexoAbrindoChave: jest.fn(),
      setAnexoMesaRascunho: jest.fn(),
      setAnexoRascunho: jest.fn(),
      setErroConversa: jest.fn(),
      setPreparandoAnexo: jest.fn(),
      setPreviewAnexoImagem: jest.fn(),
      setStatusApi: jest.fn(),
    },
  };
}

describe("useInspectorRootAttachmentController", () => {
  it("encapsula a composição do trilho de anexos sem alterar os handlers finais", () => {
    const input = criarInput();
    const { result } = renderHook(() =>
      useInspectorRootAttachmentController(input),
    );
    const mockedHook = jest.mocked(useAttachmentController);

    result.current.handleAbrirAnexo({ id: 1 } as never);
    result.current.handleEscolherAnexo("documento");

    expect(mockedHook).toHaveBeenCalledWith(
      expect.objectContaining({
        abaAtiva: input.accessState.abaAtiva,
        sessionAccessToken: input.accessState.sessionAccessToken,
        imageQuality: input.policyState.imageQuality,
        onBuildAttachmentKey: input.builderState.onBuildAttachmentKey,
      }),
    );
    expect(mockHandleAbrirAnexo).toHaveBeenCalledTimes(1);
    expect(mockHandleEscolherAnexo).toHaveBeenCalledWith("documento");
  });
});
