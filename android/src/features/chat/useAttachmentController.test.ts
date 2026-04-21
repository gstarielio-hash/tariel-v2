jest.mock("expo-file-system/legacy", () => ({
  cacheDirectory: "file:///cache/",
  makeDirectoryAsync: jest.fn(),
  downloadAsync: jest.fn(),
  getContentUriAsync: jest.fn(),
  readAsStringAsync: jest.fn(),
  deleteAsync: jest.fn(),
}));

jest.mock("expo-sharing", () => ({
  isAvailableAsync: jest.fn(),
  shareAsync: jest.fn(),
}));

jest.mock("expo-intent-launcher", () => ({
  startActivityAsync: jest.fn(),
}));

jest.mock("./attachmentDraftFlows", () => ({
  capturarImagemRascunhoFlow: jest.fn(),
  selecionarDocumentoRascunhoFlow: jest.fn(),
  selecionarImagemRascunhoFlow: jest.fn(),
}));

jest.mock("./network", () => ({
  gateHeavyTransfer: jest.fn().mockResolvedValue({
    allowed: true,
    reason: "",
    snapshot: {
      connected: true,
      isWifi: true,
      typeLabel: "wifi",
    },
  }),
}));

import * as FileSystem from "expo-file-system/legacy";
import * as IntentLauncher from "expo-intent-launcher";
import * as Sharing from "expo-sharing";
import { Platform } from "react-native";

import { capturarImagemRascunhoFlow } from "./attachmentDraftFlows";
import { selecionarDocumentoRascunhoFlow } from "./attachmentDraftFlows";
import { selecionarImagemRascunhoFlow } from "./attachmentDraftFlows";
import { useAttachmentController } from "./useAttachmentController";

function criarParams(
  overrides: Partial<Parameters<typeof useAttachmentController>[0]> = {},
): Parameters<typeof useAttachmentController>[0] {
  return {
    abaAtiva: "chat",
    arquivosPermitidos: true,
    autoUploadAttachments: true,
    cameraPermitida: true,
    conversaAtiva: null,
    preparandoAnexo: false,
    sessionAccessToken: "token-123",
    statusApi: "online",
    uploadArquivosAtivo: true,
    wifiOnlySync: false,
    imageQuality: 0.7,
    disableAggressiveDownloads: false,
    erroSugereModoOffline: jest.fn().mockReturnValue(false),
    inferirExtensaoAnexo: jest.fn().mockReturnValue(".pdf"),
    montarAnexoDocumentoLocal: jest.fn(),
    montarAnexoDocumentoMesa: jest.fn(),
    montarAnexoImagem: jest.fn(),
    nomeArquivoSeguro: jest.fn().mockReturnValue("arquivo"),
    onBuildAttachmentKey: jest.fn().mockReturnValue("anexo-1"),
    onShowAlert: jest.fn(),
    setAnexosAberto: jest.fn(),
    setAnexoAbrindoChave: jest.fn(),
    setAnexoMesaRascunho: jest.fn(),
    setAnexoRascunho: jest.fn(),
    setErroConversa: jest.fn(),
    setPreparandoAnexo: jest.fn(),
    setPreviewAnexoImagem: jest.fn(),
    setStatusApi: jest.fn(),
    ...overrides,
  };
}

describe("useAttachmentController", () => {
  const originalPlatformOs = Platform.OS;

  beforeEach(() => {
    Object.defineProperty(Platform, "OS", {
      configurable: true,
      value: "android",
    });
  });

  afterEach(() => {
    Object.defineProperty(Platform, "OS", {
      configurable: true,
      value: originalPlatformOs,
    });
    jest.clearAllMocks();
    jest.restoreAllMocks();
  });

  it("impede abrir o seletor quando uploads estao desativados", () => {
    const params = criarParams({
      uploadArquivosAtivo: false,
    });

    const controller = useAttachmentController(params);

    controller.handleAbrirSeletorAnexo();

    expect(params.onShowAlert).toHaveBeenCalledWith(
      "Uploads desativados",
      "O envio de arquivos está desligado nas preferências do app. Reative em Configurações > Recursos avançados.",
    );
    expect(params.setAnexosAberto).not.toHaveBeenCalled();
  });

  it("avisa quando a camera esta indisponivel", async () => {
    const params = criarParams({
      cameraPermitida: false,
    });

    const controller = useAttachmentController(params);

    await controller.handleEscolherAnexo("camera");

    expect(params.setAnexosAberto).toHaveBeenCalledWith(false);
    expect(params.onShowAlert).toHaveBeenCalledWith(
      "Câmera indisponível",
      "Ative a câmera em Configurações > Permissões para anexar fotos.",
    );
    expect(capturarImagemRascunhoFlow).not.toHaveBeenCalled();
  });

  it("bloqueia imagem quando a politica canonica fecha uploads", async () => {
    const params = criarParams({
      conversaAtiva: {
        laudoId: 88,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: null,
        attachmentPolicy: {
          policy_name: "android_attachment_sync_policy",
          upload_allowed: false,
          download_allowed: true,
          inline_preview_allowed: true,
          supported_categories: ["imagem", "documento"],
          supported_mime_types: ["image/png", "application/pdf"],
        },
        modo: "detalhado",
        mensagens: [],
      },
    });

    const controller = useAttachmentController(params);

    await controller.handleEscolherAnexo("galeria");

    expect(params.onShowAlert).toHaveBeenCalledWith(
      "Imagem indisponível",
      "Uploads bloqueados pela politica ativa deste caso.",
    );
    expect(selecionarImagemRascunhoFlow).not.toHaveBeenCalled();
  });

  it("bloqueia documento no chat livre antes do caso existir", async () => {
    const params = criarParams();

    const controller = useAttachmentController(params);

    await controller.handleEscolherAnexo("documento");

    expect(params.setAnexosAberto).toHaveBeenCalledWith(false);
    expect(params.onShowAlert).toHaveBeenCalledWith(
      "Documento indisponível",
      "Documentos liberam quando o caso ja estiver em coleta ou laudo.",
    );
  });

  it("mantem documento disponivel quando o caso formal ja existe", async () => {
    const params = criarParams({
      conversaAtiva: {
        laudoId: 88,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: null,
        modo: "detalhado",
        mensagens: [],
      },
    });

    const controller = useAttachmentController(params);

    await controller.handleEscolherAnexo("documento");

    expect(selecionarDocumentoRascunhoFlow).toHaveBeenCalled();
    expect(params.onShowAlert).not.toHaveBeenCalledWith(
      "Documento indisponível",
      expect.anything(),
    );
  });

  it("prioriza a politica canonica do backend quando ela libera documento", async () => {
    const params = criarParams({
      conversaAtiva: {
        laudoId: 88,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: null,
        attachmentPolicy: {
          policy_name: "android_attachment_sync_policy",
          upload_allowed: true,
          download_allowed: true,
          inline_preview_allowed: true,
          supported_categories: ["imagem", "documento"],
          supported_mime_types: ["image/png", "application/pdf"],
        },
        reviewPackage: {
          tenant_entitlements: {
            upload_doc: false,
          },
        },
        modo: "detalhado",
        mensagens: [],
      },
    });

    const controller = useAttachmentController(params);

    await controller.handleEscolherAnexo("documento");

    expect(selecionarDocumentoRascunhoFlow).toHaveBeenCalled();
    expect(params.onShowAlert).not.toHaveBeenCalledWith(
      "Documento indisponível",
      expect.any(String),
    );
  });

  it("bloqueia documento quando a politica canonica remove a categoria documental", async () => {
    const params = criarParams({
      conversaAtiva: {
        laudoId: 88,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: null,
        attachmentPolicy: {
          policy_name: "android_attachment_sync_policy",
          upload_allowed: true,
          download_allowed: true,
          inline_preview_allowed: true,
          supported_categories: ["imagem"],
          supported_mime_types: ["image/png"],
        },
        modo: "detalhado",
        mensagens: [],
      },
    });

    const controller = useAttachmentController(params);

    await controller.handleEscolherAnexo("documento");

    expect(params.onShowAlert).toHaveBeenCalledWith(
      "Documento indisponível",
      "Este caso aceita somente imagens no app; documento nao faz parte da politica ativa.",
    );
    expect(selecionarDocumentoRascunhoFlow).not.toHaveBeenCalled();
  });

  it("abre uma imagem em preview sem baixar arquivo", async () => {
    const params = criarParams();

    const controller = useAttachmentController(params);

    await controller.handleAbrirAnexo({
      id: 1,
      nome: "evidencia",
      mime_type: "image/png",
      categoria: "imagem",
      url: "https://tariel.test/evidencia.png",
      eh_imagem: true,
    });

    expect(params.setPreviewAnexoImagem).toHaveBeenCalledWith({
      titulo: "evidencia",
      uri: "https://tariel.test/evidencia.png",
    });
    expect(FileSystem.downloadAsync).not.toHaveBeenCalled();
  });

  it("baixa e abre anexos nao visuais no android", async () => {
    const params = criarParams();
    (FileSystem.downloadAsync as jest.Mock).mockResolvedValue({
      uri: "file:///cache/arquivo.pdf",
    });
    (FileSystem.getContentUriAsync as jest.Mock).mockResolvedValue(
      "content://tariel/arquivo.pdf",
    );
    (IntentLauncher.startActivityAsync as jest.Mock).mockResolvedValue({
      resultCode: -1,
    });
    (Sharing.isAvailableAsync as jest.Mock).mockResolvedValue(true);

    const controller = useAttachmentController(params);

    await controller.handleAbrirAnexo({
      id: 1,
      nome: "relatorio",
      mime_type: "application/pdf",
      categoria: "documento",
      url: "/revisao/api/laudo/80/mesa/anexos/101",
      eh_imagem: false,
    });

    expect(params.setAnexoAbrindoChave).toHaveBeenCalledWith("anexo-1");
    expect(FileSystem.downloadAsync).toHaveBeenCalledWith(
      expect.stringContaining("/app/api/laudo/80/mesa/anexos/101"),
      expect.stringContaining("arquivo.pdf"),
      {
        headers: {
          Authorization: "Bearer token-123",
        },
      },
    );
    expect(FileSystem.getContentUriAsync).toHaveBeenCalledWith(
      "file:///cache/arquivo.pdf",
    );
    expect(IntentLauncher.startActivityAsync).toHaveBeenCalledWith(
      "android.intent.action.VIEW",
      {
        data: "content://tariel/arquivo.pdf",
        flags: 1,
      },
    );
    expect(Sharing.shareAsync).not.toHaveBeenCalled();
  });

  it("tenta abertura com mime explicito quando a primeira tentativa simples falha", async () => {
    const params = criarParams();
    (FileSystem.downloadAsync as jest.Mock).mockResolvedValue({
      uri: "file:///cache/arquivo.pdf",
    });
    (FileSystem.getContentUriAsync as jest.Mock).mockResolvedValue(
      "content://tariel/arquivo.pdf",
    );
    (IntentLauncher.startActivityAsync as jest.Mock)
      .mockRejectedValueOnce(new Error("plain view failed"))
      .mockResolvedValueOnce({
        resultCode: -1,
      });

    const controller = useAttachmentController(params);

    await controller.handleAbrirAnexo({
      id: 1,
      nome: "relatorio",
      mime_type: "application/pdf",
      categoria: "documento",
      url: "https://tariel.test/relatorio.pdf",
      eh_imagem: false,
    });

    expect(IntentLauncher.startActivityAsync).toHaveBeenNthCalledWith(
      1,
      "android.intent.action.VIEW",
      {
        data: "content://tariel/arquivo.pdf",
        flags: 1,
      },
    );
    expect(IntentLauncher.startActivityAsync).toHaveBeenNthCalledWith(
      2,
      "android.intent.action.VIEW",
      {
        data: "content://tariel/arquivo.pdf",
        type: "application/pdf",
        flags: 1,
      },
    );
    expect(Sharing.shareAsync).not.toHaveBeenCalled();
  });

  it("usa compartilhamento como fallback quando o android nao consegue abrir o documento", async () => {
    const params = criarParams();
    (FileSystem.downloadAsync as jest.Mock).mockResolvedValue({
      uri: "file:///cache/arquivo.pdf",
    });
    (FileSystem.getContentUriAsync as jest.Mock).mockResolvedValue(
      "content://tariel/arquivo.pdf",
    );
    (IntentLauncher.startActivityAsync as jest.Mock).mockRejectedValue(
      new Error("no viewer"),
    );
    (Sharing.isAvailableAsync as jest.Mock).mockResolvedValue(true);

    const controller = useAttachmentController(params);

    await controller.handleAbrirAnexo({
      id: 1,
      nome: "relatorio",
      mime_type: "application/pdf",
      categoria: "documento",
      url: "https://tariel.test/relatorio.pdf",
      eh_imagem: false,
    });

    expect(Sharing.shareAsync).toHaveBeenCalledWith(
      "file:///cache/arquivo.pdf",
      {
        mimeType: "application/pdf",
        dialogTitle: "Abrir relatorio",
      },
    );
  });

  it("interrompe a abertura quando o backend devolve JSON no lugar do pdf", async () => {
    const params = criarParams();
    (FileSystem.downloadAsync as jest.Mock).mockResolvedValue({
      uri: "file:///cache/arquivo.pdf",
      status: 403,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
      },
    });
    (FileSystem.readAsStringAsync as jest.Mock).mockResolvedValue(
      '{"detail":"Acesso restrito à Engenharia/Revisão."}',
    );

    const controller = useAttachmentController(params);

    await controller.handleAbrirAnexo({
      id: 1,
      nome: "relatorio",
      mime_type: "application/pdf",
      categoria: "documento",
      url: "/revisao/api/laudo/80/mesa/anexos/101",
      eh_imagem: false,
    });

    expect(FileSystem.deleteAsync).toHaveBeenCalledWith(
      "file:///cache/arquivo.pdf",
      { idempotent: true },
    );
    expect(IntentLauncher.startActivityAsync).not.toHaveBeenCalled();
    expect(Sharing.shareAsync).not.toHaveBeenCalled();
    expect(params.onShowAlert).toHaveBeenCalledWith(
      "Anexo",
      "Acesso restrito à Engenharia/Revisão.",
    );
  });
});
