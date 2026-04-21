jest.mock("expo-file-system/legacy", () => ({
  readAsStringAsync: jest.fn(),
  writeAsStringAsync: jest.fn(),
  deleteAsync: jest.fn(),
}));

import * as FileSystem from "expo-file-system/legacy";

import { buildInspectorRootSettingsToggleState } from "./buildInspectorRootSettingsToggleState";

function criarInput() {
  return {
    bootstrap: {
      localState: {
        filaOffline: [],
        setAnexoMesaRascunho: jest.fn(),
        setAnexoRascunho: jest.fn(),
      },
      refsAndBridges: {
        onOpenSystemSettings: jest.fn(),
      },
      reauthActions: {
        executarComReautenticacao: jest.fn(),
      },
      runtimeController: {
        voiceRuntimeState: {
          sttSupported: true,
        },
      },
      sessionFlow: {
        state: {
          session: {
            accessToken: "token-123",
            bootstrap: {
              ok: true,
              app: {
                nome: "Tariel",
                portal: "inspetor",
                api_base_url: "https://api.tariel.test",
                suporte_whatsapp: "",
              },
              usuario: {
                id: 7,
                email: "inspetor@tariel.test",
                nome_completo: "Inspetor Tariel",
                telefone: "",
                foto_perfil_url: "",
                empresa_nome: "Tariel",
                empresa_id: 3,
                nivel_acesso: 1,
              },
            },
          },
        },
      },
      settingsBindings: {
        attachments: {
          setUploadArquivosAtivo: jest.fn(),
        },
        dataControls: {
          setBackupAutomatico: jest.fn(),
          setSincronizacaoDispositivos: jest.fn(),
        },
        notifications: {
          notificacoesPermitidas: true,
          setMostrarConteudoNotificacao: jest.fn(),
          setMostrarSomenteNovaMensagem: jest.fn(),
          setNotificaPush: jest.fn(),
          setNotificacoesPermitidas: jest.fn(),
          setOcultarConteudoBloqueado: jest.fn(),
          setVibracaoAtiva: jest.fn(),
        },
        security: {
          arquivosPermitidos: true,
          cameraPermitida: true,
          microfonePermitido: true,
          setArquivosPermitidos: jest.fn(),
          setMicrofonePermitido: jest.fn(),
        },
        speech: {
          setEntradaPorVoz: jest.fn(),
          setRespostaPorVoz: jest.fn(),
          setSpeechEnabled: jest.fn(),
        },
      },
      settingsSupportState: {
        navigationActions: {
          abrirConfirmacaoConfiguracao: jest.fn(),
          setSettingsSheetNotice: jest.fn(),
        },
        registrarEventoSegurancaLocal: jest.fn(),
      },
    },
    controllers: {
      offlineQueueController: {
        actions: {
          sincronizarFilaOffline: jest.fn(),
        },
      },
    },
  };
}

describe("buildInspectorRootSettingsToggleState", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("salva o cache local com o escopo da sessão atual", async () => {
    const input = criarInput();
    const state = buildInspectorRootSettingsToggleState(input as any);
    const cache = {
      bootstrap: input.bootstrap.sessionFlow.state.session.bootstrap,
      laudos: [
        {
          id: 7,
          titulo: "Laudo",
          preview: "Resumo",
          pinado: false,
          data_iso: "2026-04-13T10:00:00.000Z",
          data_br: "13/04/2026",
          hora_br: "10:00",
          tipo_template: "TC",
          status_revisao: "ativo",
          status_card: "aguardando",
          status_card_label: "Aguardando",
          permite_edicao: true,
          permite_reabrir: false,
          possui_historico: true,
        },
      ],
      conversaAtual: null,
      conversasPorLaudo: {},
      mesaPorLaudo: {},
      guidedInspectionDrafts: {},
      chatDrafts: {},
      mesaDrafts: {},
      chatAttachmentDrafts: {},
      mesaAttachmentDrafts: {},
      updatedAt: "2026-04-13T10:00:00.000Z",
    };

    await state.cacheState.onSaveReadCacheLocally(cache);

    expect(FileSystem.writeAsStringAsync).toHaveBeenCalledTimes(1);
    expect(
      JSON.parse(
        (FileSystem.writeAsStringAsync as jest.Mock).mock.calls[0]?.[1],
      ),
    ).toEqual(
      expect.objectContaining({
        scope: {
          email: "inspetor@tariel.test",
          userId: 7,
          empresaId: 3,
        },
        payload: expect.objectContaining({
          laudos: expect.arrayContaining([expect.objectContaining({ id: 7 })]),
        }),
      }),
    );
  });
});
