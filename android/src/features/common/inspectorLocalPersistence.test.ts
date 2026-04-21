jest.mock("expo-file-system/legacy", () => ({
  readAsStringAsync: jest.fn(),
  writeAsStringAsync: jest.fn(),
  deleteAsync: jest.fn(),
}));

import * as FileSystem from "expo-file-system/legacy";

import {
  CACHE_LEITURA_VAZIO,
  buildLocalPersistenceScopeFromBootstrap,
  filtrarItensPorRetencao,
  lerCacheLeituraLocal,
  lerFilaOfflineLocal,
  lerEstadoHistoricoLocal,
  lerNotificacoesLocais,
  limparCachePorPrivacidade,
  obterJanelaRetencaoMs,
  salvarCacheLeituraLocal,
  salvarFilaOfflineLocal,
  salvarNotificacoesLocais,
} from "./inspectorLocalPersistence";

describe("inspectorLocalPersistence", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("lê e normaliza o estado local do histórico", async () => {
    (FileSystem.readAsStringAsync as jest.Mock).mockResolvedValue(
      JSON.stringify({
        laudosFixadosIds: [1, "2", 2, "invalido"],
        historicoOcultoIds: ["4", 4, 0],
      }),
    );

    const estado = await lerEstadoHistoricoLocal();

    expect(estado).toEqual({
      laudosFixadosIds: [1, 2],
      historicoOcultoIds: [4],
    });
  });

  it("lê a fila offline local com normalização mínima", async () => {
    (FileSystem.readAsStringAsync as jest.Mock).mockResolvedValue(
      JSON.stringify({
        scope: {
          email: "inspetor@tariel.test",
          userId: 7,
          empresaId: 3,
        },
        payload: [
          {
            id: "offline-1",
            channel: "mesa",
            operation: "message",
            text: "Mensagem",
            title: "Pendência",
            aiMode: "curto",
            guidedInspectionDraft: {
              template_key: "nr35_linha_vida",
              template_label: "NR35 Linha de Vida",
              started_at: "2026-04-06T22:30:00.000Z",
              current_step_index: 1,
              completed_step_ids: ["identificacao_laudo"],
              checklist: [
                {
                  id: "identificacao_laudo",
                  title: "Identificacao do ativo e do laudo",
                  prompt: "registre unidade, local e tag",
                  evidence_hint: "codigo do ativo e local resumido",
                },
                {
                  id: "contexto_vistoria",
                  title: "Contexto da vistoria",
                  prompt: "confirme responsaveis e data",
                  evidence_hint: "nomes, data e acompanhamento",
                },
              ],
            },
          },
        ],
      }),
    );

    const fila = await lerFilaOfflineLocal({
      expectedScope: { email: "inspetor@tariel.test" },
      normalizarComposerAttachment: () => null,
      normalizarModoChat: (modo) => (modo === "curto" ? "curto" : "detalhado"),
    });

    expect(fila).toHaveLength(1);
    expect(fila[0]?.channel).toBe("mesa");
    expect(fila[0]?.aiMode).toBe("curto");
    expect(fila[0]?.guidedInspectionDraft?.template_key).toBe(
      "nr35_linha_vida",
    );
  });

  it("sanitiza cache de conversa e previews com preferências vazadas", async () => {
    (FileSystem.readAsStringAsync as jest.Mock).mockResolvedValue(
      JSON.stringify({
        scope: {
          email: "inspetor@tariel.test",
          userId: 7,
          empresaId: 3,
        },
        payload: {
          laudos: [
            {
              id: 7,
              titulo: "Laudo",
              preview:
                "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]",
            },
          ],
          conversaAtual: {
            laudoId: 7,
            estado: "relatorio_ativo",
            statusCard: "aberto",
            permiteEdicao: true,
            permiteReabrir: false,
            laudoCard: {
              id: 7,
              titulo: "Laudo",
              preview:
                "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]",
            },
            modo: "detalhado",
            mensagens: [
              {
                id: 1,
                papel: "usuario",
                texto:
                  "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]\n\nTexto útil",
                tipo: "user",
              },
            ],
          },
        },
      }),
    );

    const cache = await lerCacheLeituraLocal({
      criarConversaNova: () => ({
        laudoId: null,
        estado: "sem_relatorio",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: null,
        modo: "detalhado",
        mensagens: [],
      }),
      expectedScope: { email: "inspetor@tariel.test" },
      normalizarComposerAttachment: () => null,
    });

    expect(cache.laudos[0]?.preview).toBe("Evidência enviada");
    expect(cache.conversaAtual?.laudoCard?.preview).toBe("Evidência enviada");
    expect(cache.conversaAtual?.mensagens[0]?.texto).toBe("Texto útil");
  });

  it("apaga o arquivo de cache quando não há conteúdo útil", async () => {
    await salvarCacheLeituraLocal(CACHE_LEITURA_VAZIO);

    expect(FileSystem.deleteAsync).toHaveBeenCalledTimes(1);
    expect(FileSystem.writeAsStringAsync).not.toHaveBeenCalled();
  });

  it("salva e lê notificações locais com normalização mínima", async () => {
    await salvarNotificacoesLocais(
      [
        {
          id: "notif-1",
          kind: "status",
          laudoId: 9,
          title: "Atualização",
          body: "Corpo",
          createdAt: "2026-03-30T10:00:00.000Z",
          unread: true,
          targetThread: "chat",
        },
      ],
      {
        email: "inspetor@tariel.test",
        userId: 7,
        empresaId: 3,
      },
    );

    expect(FileSystem.writeAsStringAsync).toHaveBeenCalledTimes(1);
    expect(
      JSON.parse(
        (FileSystem.writeAsStringAsync as jest.Mock).mock.calls[0]?.[1],
      ),
    ).toEqual(
      expect.objectContaining({
        scope: expect.objectContaining({
          email: "inspetor@tariel.test",
          userId: 7,
          empresaId: 3,
        }),
      }),
    );

    (FileSystem.readAsStringAsync as jest.Mock).mockResolvedValue(
      JSON.stringify({
        scope: {
          email: "inspetor@tariel.test",
          userId: 7,
          empresaId: 3,
        },
        payload: [
          {
            id: "notif-1",
            title: "Atualização",
            body: "Corpo",
            createdAt: "2026-03-30T10:00:00.000Z",
            unread: true,
          },
        ],
      }),
    );

    const notificacoes = await lerNotificacoesLocais({
      expectedScope: { email: "inspetor@tariel.test" },
    });

    expect(notificacoes).toHaveLength(1);
    expect(notificacoes[0]?.targetThread).toBe("chat");
  });

  it("apaga o arquivo da fila offline quando a coleção fica vazia", async () => {
    await salvarFilaOfflineLocal([]);

    expect(FileSystem.deleteAsync).toHaveBeenCalledTimes(1);
  });

  it("lê o cache local com normalização e sanitiza por privacidade", async () => {
    const bootstrap = {
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
    };
    (FileSystem.readAsStringAsync as jest.Mock).mockResolvedValue(
      JSON.stringify({
        scope: {
          email: "inspetor@tariel.test",
          userId: 7,
          empresaId: 3,
        },
        payload: {
          bootstrap,
          laudos: [{ id: 7, titulo: "Laudo" }],
          updatedAt: "2026-03-30T10:00:00.000Z",
        },
      }),
    );

    const cache = await lerCacheLeituraLocal({
      criarConversaNova: () => ({
        laudoId: null,
        estado: "sem_relatorio",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: null,
        modo: "detalhado",
        mensagens: [],
      }),
      expectedScope: { email: "inspetor@tariel.test" },
      normalizarComposerAttachment: () => null,
    });

    expect(cache.laudos).toHaveLength(1);
    expect(limparCachePorPrivacidade(cache).bootstrap).toEqual(bootstrap);
    expect(limparCachePorPrivacidade(cache).laudos).toEqual([]);
  });

  it("ignora fila e notificações locais de outra identidade", async () => {
    (FileSystem.readAsStringAsync as jest.Mock).mockResolvedValue(
      JSON.stringify({
        scope: {
          email: "outra@tariel.test",
          userId: 99,
          empresaId: 88,
        },
        payload: [
          {
            id: "notif-1",
            title: "Atualização",
            body: "Corpo",
            createdAt: "2026-03-30T10:00:00.000Z",
            unread: true,
          },
        ],
      }),
    );

    const notificacoes = await lerNotificacoesLocais({
      expectedScope: { email: "inspetor@tariel.test" },
    });

    expect(notificacoes).toEqual([]);
  });

  it("constrói o scope persistido a partir do bootstrap mobile", () => {
    expect(
      buildLocalPersistenceScopeFromBootstrap({
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
      }),
    ).toEqual({
      email: "inspetor@tariel.test",
      userId: 7,
      empresaId: 3,
    });
  });

  it("calcula a janela e filtra itens por retenção", () => {
    const agora = Date.now();
    jest.spyOn(Date, "now").mockReturnValue(agora);

    const itens = [
      { createdAt: new Date(agora - 10_000).toISOString() },
      { createdAt: new Date(agora - 40 * 24 * 60 * 60 * 1000).toISOString() },
    ];

    const janelaMs = obterJanelaRetencaoMs("30 dias");
    const filtrados = filtrarItensPorRetencao(
      itens,
      janelaMs,
      (item) => item.createdAt,
    );

    expect(janelaMs).toBe(30 * 24 * 60 * 60 * 1000);
    expect(filtrados).toHaveLength(1);
  });
});
