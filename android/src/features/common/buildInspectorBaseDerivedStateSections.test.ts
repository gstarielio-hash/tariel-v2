import type { MobileLaudoCard } from "../../types/mobile";
import type {
  MobileActivityNotification,
  OfflinePendingMessage,
} from "../chat/types";
import {
  buildInspectorConversationDerivedState,
  buildInspectorHistoryAndOfflineDerivedState,
  buildInspectorLayoutDerivedState,
  buildInspectorSettingsDerivedState,
} from "./buildInspectorBaseDerivedStateSections";

function criarLaudoParcial(
  overrides: Partial<MobileLaudoCard>,
): MobileLaudoCard {
  return {
    id: 42,
    titulo: "Laudo",
    preview: "Resumo",
    pinado: false,
    data_iso: "2026-03-20T10:00:00.000Z",
    data_br: "20/03/2026",
    hora_br: "10:00",
    tipo_template: "TC",
    status_revisao: "ativo",
    status_card: "aguardando",
    status_card_label: "Aguardando",
    permite_edicao: true,
    permite_reabrir: false,
    possui_historico: true,
    ...overrides,
  };
}

function criarPendenciaParcial(
  overrides: Partial<OfflinePendingMessage>,
): OfflinePendingMessage {
  return {
    id: "offline-1",
    channel: "chat",
    operation: "message",
    laudoId: null,
    text: "Mensagem pendente",
    createdAt: "2026-03-20T10:00:00.000Z",
    title: "Pendência",
    attachment: null,
    referenceMessageId: null,
    qualityGateDecision: null,
    attempts: 0,
    lastAttemptAt: "",
    lastError: "",
    nextRetryAt: "",
    aiMode: "detalhado",
    aiSummary: "",
    aiMessagePrefix: "",
    ...overrides,
  };
}

function criarNotificacaoParcial(
  overrides: Partial<MobileActivityNotification>,
): MobileActivityNotification {
  return {
    id: "notif-1",
    kind: "status",
    laudoId: null,
    title: "Atualização",
    body: "Há uma atualização.",
    createdAt: "2026-03-20T10:00:00.000Z",
    unread: true,
    targetThread: "chat",
    ...overrides,
  };
}

describe("buildInspectorBaseDerivedStateSections", () => {
  it("prioriza o placeholder de reabertura quando a conversa exige reabrir", () => {
    const state = buildInspectorConversationDerivedState({
      anexoMesaRascunho: null,
      anexoRascunho: null,
      arquivosPermitidos: true,
      abaAtiva: "chat",
      colorScheme: "light",
      conversa: {
        laudoId: 42,
        mensagens: [],
        permiteEdicao: true,
        permiteReabrir: true,
        estado: "relatorio_ativo",
        statusCard: "aguardando",
        laudoCard: criarLaudoParcial({ tipo_template: "normal" }),
        modo: "detalhado",
      },
      corDestaque: "laranja",
      densidadeInterface: "confortável",
      formatarTipoTemplateLaudo: jest.fn().mockReturnValue("Normal"),
      mensagem: "",
      mensagemMesa: "",
      mensagensMesa: [],
      obterEscalaDensidade: jest.fn().mockReturnValue(1),
      obterEscalaFonte: jest.fn().mockReturnValue(1),
      podeEditarConversaNoComposer: jest.fn().mockReturnValue(true),
      preparandoAnexo: false,
      previewChatLiberadoParaConversa: jest.fn().mockReturnValue(false),
      session: null,
      tamanhoFonte: "médio",
      temaApp: "claro",
      uploadArquivosAtivo: true,
      carregandoConversa: false,
      carregandoMesa: false,
      enviandoMensagem: false,
      enviandoMesa: false,
    });

    expect(state.placeholderComposer).toBe("Reabra o laudo para continuar.");
    expect(state.podeEnviarComposer).toBe(false);
    expect(state.vendoMesa).toBe(false);
  });

  it("usa o owner canonico da mesa no placeholder do chat", () => {
    const state = buildInspectorConversationDerivedState({
      anexoMesaRascunho: null,
      anexoRascunho: null,
      arquivosPermitidos: true,
      abaAtiva: "chat",
      colorScheme: "light",
      conversa: {
        laudoId: 42,
        mensagens: [],
        permiteEdicao: false,
        permiteReabrir: false,
        estado: "aguardando",
        statusCard: "aberto",
        caseLifecycleStatus: "em_revisao_mesa",
        activeOwnerRole: "mesa",
        laudoCard: criarLaudoParcial({
          tipo_template: "normal",
          status_card: "aberto",
          case_lifecycle_status: "em_revisao_mesa",
          active_owner_role: "mesa",
        }),
        modo: "detalhado",
      },
      corDestaque: "laranja",
      densidadeInterface: "confortável",
      formatarTipoTemplateLaudo: jest.fn().mockReturnValue("Normal"),
      mensagem: "",
      mensagemMesa: "",
      mensagensMesa: [],
      obterEscalaDensidade: jest.fn().mockReturnValue(1),
      obterEscalaFonte: jest.fn().mockReturnValue(1),
      podeEditarConversaNoComposer: jest.fn().mockReturnValue(false),
      preparandoAnexo: false,
      previewChatLiberadoParaConversa: jest.fn().mockReturnValue(false),
      session: null,
      tamanhoFonte: "médio",
      temaApp: "claro",
      uploadArquivosAtivo: true,
      carregandoConversa: false,
      carregandoMesa: false,
      enviandoMensagem: false,
      enviandoMesa: false,
    });

    expect(state.placeholderComposer).toBe(
      "Caso sob revisão da mesa avaliadora.",
    );
  });

  it("prioriza a ação canônica de reabrir no placeholder do chat", () => {
    const state = buildInspectorConversationDerivedState({
      anexoMesaRascunho: null,
      anexoRascunho: null,
      arquivosPermitidos: true,
      abaAtiva: "chat",
      colorScheme: "light",
      conversa: {
        laudoId: 42,
        mensagens: [],
        permiteEdicao: false,
        permiteReabrir: false,
        estado: "aprovado",
        statusCard: "aprovado",
        caseLifecycleStatus: "emitido",
        activeOwnerRole: "none",
        allowedSurfaceActions: ["chat_reopen"],
        laudoCard: criarLaudoParcial({
          tipo_template: "normal",
          status_card: "aprovado",
          case_lifecycle_status: "emitido",
          active_owner_role: "none",
          allowed_surface_actions: ["chat_reopen"],
        }),
        modo: "detalhado",
      },
      corDestaque: "laranja",
      densidadeInterface: "confortável",
      formatarTipoTemplateLaudo: jest.fn().mockReturnValue("Normal"),
      mensagem: "",
      mensagemMesa: "",
      mensagensMesa: [],
      obterEscalaDensidade: jest.fn().mockReturnValue(1),
      obterEscalaFonte: jest.fn().mockReturnValue(1),
      podeEditarConversaNoComposer: jest.fn().mockReturnValue(false),
      preparandoAnexo: false,
      previewChatLiberadoParaConversa: jest.fn().mockReturnValue(false),
      session: null,
      tamanhoFonte: "médio",
      temaApp: "claro",
      uploadArquivosAtivo: true,
      carregandoConversa: false,
      carregandoMesa: false,
      enviandoMensagem: false,
      enviandoMesa: false,
    });

    expect(state.placeholderComposer).toBe(
      "Reabra o documento emitido para iniciar um novo ciclo.",
    );
  });

  it("usa placeholder curto quando a coleta guiada está ativa", () => {
    const state = buildInspectorConversationDerivedState({
      anexoMesaRascunho: null,
      anexoRascunho: null,
      arquivosPermitidos: true,
      abaAtiva: "chat",
      colorScheme: "light",
      conversa: null,
      corDestaque: "laranja",
      densidadeInterface: "confortável",
      enviandoMensagem: false,
      enviandoMesa: false,
      formatarTipoTemplateLaudo: jest.fn().mockReturnValue("Normal"),
      guidedInspectionDraft: {
        templateKey: "padrao",
        templateLabel: "Inspeção Geral",
        startedAt: "2026-04-13T18:00:00.000Z",
        currentStepIndex: 0,
        completedStepIds: [],
        checklist: [
          {
            id: "identificacao_ativo",
            title: "Identificação do ativo e da área",
            prompt:
              "registre o ativo, setor, local e o motivo tecnico da coleta",
            evidenceHint:
              "nome do ativo, area inspecionada, tag ou referencia principal",
          },
        ],
        evidenceRefs: [],
        evidenceBundleKind: "case_thread",
        mesaHandoff: null,
      },
      mensagem: "",
      mensagemMesa: "",
      mensagensMesa: [],
      obterEscalaDensidade: jest.fn().mockReturnValue(1),
      obterEscalaFonte: jest.fn().mockReturnValue(1),
      podeEditarConversaNoComposer: jest.fn().mockReturnValue(true),
      preparandoAnexo: false,
      previewChatLiberadoParaConversa: jest.fn().mockReturnValue(true),
      session: null,
      tamanhoFonte: "médio",
      temaApp: "claro",
      uploadArquivosAtivo: true,
      carregandoConversa: false,
      carregandoMesa: false,
    });

    expect(state.placeholderComposer).toBe(
      "Identificação do ativo e da área: nome do ativo, area inspecionada, tag ou referencia principal.",
    );
  });

  it("orienta o chat vazio para analise livre com IA", () => {
    const state = buildInspectorConversationDerivedState({
      anexoMesaRascunho: null,
      anexoRascunho: null,
      arquivosPermitidos: true,
      abaAtiva: "chat",
      colorScheme: "light",
      conversa: null,
      corDestaque: "laranja",
      densidadeInterface: "confortável",
      formatarTipoTemplateLaudo: jest.fn().mockReturnValue("Normal"),
      guidedInspectionDraft: null,
      mensagem: "",
      mensagemMesa: "",
      mensagensMesa: [],
      obterEscalaDensidade: jest.fn().mockReturnValue(1),
      obterEscalaFonte: jest.fn().mockReturnValue(1),
      podeEditarConversaNoComposer: jest.fn().mockReturnValue(true),
      preparandoAnexo: false,
      previewChatLiberadoParaConversa: jest.fn().mockReturnValue(true),
      session: null,
      tamanhoFonte: "médio",
      temaApp: "claro",
      uploadArquivosAtivo: true,
      carregandoConversa: false,
      carregandoMesa: false,
      enviandoMensagem: false,
      enviandoMesa: false,
    });

    expect(state.placeholderComposer).toBe(
      "Primeiro envio cria o caso: descreva o item, envie foto ou documento para a IA analisar...",
    );
  });

  it("resume a fila offline e filtra o historico por fixadas", () => {
    jest
      .spyOn(Date, "now")
      .mockReturnValue(new Date("2026-03-20T12:00:00.000Z").getTime());

    const state = buildInspectorHistoryAndOfflineDerivedState({
      buscaHistorico: "",
      buildHistorySections: jest.fn((items) => [
        {
          key: "fixadas",
          title: "Fixadas",
          items,
        },
      ]),
      filaOffline: [
        criarPendenciaParcial({
          id: "mesa-1",
          channel: "mesa",
          createdAt: "2026-03-19T10:00:00.000Z",
          lastError: "timeout",
        }),
        criarPendenciaParcial({
          id: "chat-1",
          channel: "chat",
          createdAt: "2026-03-20T11:00:00.000Z",
          lastError: "",
        }),
      ],
      filtroFilaOffline: "all",
      filtroHistorico: "fixadas",
      fixarConversas: true,
      historicoOcultoIds: [3],
      laudosDisponiveis: [
        criarLaudoParcial({
          id: 1,
          titulo: "Laudo 1",
          preview: "Resumo",
          status_card_label: "Em andamento",
          data_iso: "2026-03-20T11:00:00.000Z",
          pinado: true,
        }),
        criarLaudoParcial({
          id: 2,
          titulo: "Laudo 2",
          preview: "Outro",
          status_card_label: "Concluido",
          data_iso: "2026-03-10T11:00:00.000Z",
          pinado: false,
        }),
      ],
      notificacoes: [
        criarNotificacaoParcial({ unread: true }),
        criarNotificacaoParcial({ id: "notif-2", unread: false }),
      ],
      pendenciaFilaProntaParaReenvio: jest
        .fn()
        .mockImplementation((item) => item.id === "chat-1"),
      prioridadePendenciaOffline: jest
        .fn()
        .mockImplementation((item) => (item.channel === "chat" ? 0 : 1)),
      session: {
        accessToken: "token-123",
        bootstrap: {
          ok: true,
          app: {
            api_base_url: "https://tariel.test",
            nome: "Tariel Inspetor",
            portal: "inspetor",
            suporte_whatsapp: "",
          },
          usuario: {
            id: 7,
            nome_completo: "Inspetor Tariel",
            email: "inspetor@tariel.test",
            telefone: "",
            foto_perfil_url: "",
            empresa_nome: "Empresa A",
            empresa_id: 33,
            nivel_acesso: 1,
            allowed_portals: ["inspetor", "revisor"],
          },
        },
      },
      statusApi: "online",
    });

    expect(
      state.filaOfflineOrdenada.map((item: { id: string }) => item.id),
    ).toEqual(["chat-1", "mesa-1"]);
    expect(state.totalFilaOfflinePronta).toBe(1);
    expect(state.totalFilaOfflineFalha).toBe(1);
    expect(state.resumoFilaOffline).toContain("2 envios pendentes");
    expect(state.historicoAgrupadoFinal).toHaveLength(1);
    expect(state.conversasFixadasTotal).toBe(1);
    expect(state.notificacoesNaoLidas).toBe(1);
  });

  it("permite buscar histórico por resumo canônico do caso", () => {
    const state = buildInspectorHistoryAndOfflineDerivedState({
      buscaHistorico: "mesa avaliadora",
      buildHistorySections: jest.fn((items) => [
        {
          key: "resultado",
          title: "Resultado",
          items,
        },
      ]),
      filaOffline: [],
      filtroFilaOffline: "all",
      filtroHistorico: "todos",
      fixarConversas: false,
      historicoOcultoIds: [],
      laudosDisponiveis: [
        criarLaudoParcial({
          id: 10,
          titulo: "Caso mesa",
          preview: "revisao",
          status_card: "aberto",
          status_card_label: "Em andamento",
          case_lifecycle_status: "em_revisao_mesa",
          active_owner_role: "mesa",
          allowed_surface_actions: ["mesa_approve"],
        }),
        criarLaudoParcial({
          id: 11,
          titulo: "Caso chat",
          preview: "coleta",
          status_card: "aberto",
          status_card_label: "Em andamento",
          case_lifecycle_status: "laudo_em_coleta",
          active_owner_role: "inspetor",
          allowed_surface_actions: ["chat_finalize"],
        }),
      ],
      notificacoes: [],
      pendenciaFilaProntaParaReenvio: jest.fn().mockReturnValue(false),
      prioridadePendenciaOffline: jest.fn().mockReturnValue(0),
      session: null,
      statusApi: "online",
    });

    expect(
      state.historicoAgrupadoFinal[0]?.items.map((item) => item.id),
    ).toEqual([10]);
  });

  it("permite buscar histórico pela prontidão do pré-laudo", () => {
    const state = buildInspectorHistoryAndOfflineDerivedState({
      buscaHistorico: "pre-laudo em montagem",
      buildHistorySections: jest.fn((items) => [
        {
          key: "resultado",
          title: "Resultado",
          items,
        },
      ]),
      filaOffline: [],
      filtroFilaOffline: "all",
      filtroHistorico: "todos",
      fixarConversas: false,
      historicoOcultoIds: [],
      laudosDisponiveis: [
        criarLaudoParcial({
          id: 12,
          titulo: "Caso NR35",
          preview: "coleta guiada",
          status_card: "aberto",
          status_card_label: "Em andamento",
          report_pack_draft: {
            modeled: true,
            template_label: "NR35 Linha de Vida",
            guided_context: {
              checklist_ids: ["identificacao", "ancoragem"],
              completed_step_ids: ["identificacao"],
            },
            image_slots: [{ slot: "vista_geral", status: "resolved" }],
            items: [
              {
                item_codigo: "fixacao",
                veredito_ia_normativo: "pendente",
                approved_for_emission: false,
                missing_evidence: ["status_normativo_nao_confirmado"],
              },
            ],
            structured_data_candidate: null,
            quality_gates: {
              checklist_complete: false,
              required_image_slots_complete: true,
              critical_items_complete: false,
              autonomy_ready: false,
              requires_normative_curation: false,
              final_validation_mode: "mesa_required",
            },
          },
        }),
        criarLaudoParcial({
          id: 13,
          titulo: "Caso emitido",
          preview: "final",
          status_card: "aprovado",
          status_card_label: "Aprovado",
        }),
      ],
      notificacoes: [],
      pendenciaFilaProntaParaReenvio: jest.fn().mockReturnValue(false),
      prioridadePendenciaOffline: jest.fn().mockReturnValue(0),
      session: null,
      statusApi: "online",
    });

    expect(
      state.historicoAgrupadoFinal[0]?.items.map((item) => item.id),
    ).toEqual([12]);
  });

  it("permite buscar histórico pelo alerta de reemissão do PDF oficial", () => {
    const state = buildInspectorHistoryAndOfflineDerivedState({
      buscaHistorico: "reemissão recomendada",
      buildHistorySections: jest.fn((items) => [
        {
          key: "resultado",
          title: "Resultado",
          items,
        },
      ]),
      filaOffline: [],
      filtroFilaOffline: "all",
      filtroHistorico: "todos",
      fixarConversas: false,
      historicoOcultoIds: [],
      laudosDisponiveis: [
        criarLaudoParcial({
          id: 18,
          titulo: "Caso com drift",
          official_issue_summary: {
            label: "Reemissão recomendada",
            detail: "PDF emitido divergente · Emitido v0003 · Atual v0004",
            primary_pdf_diverged: true,
            issue_number: "EO-18",
            issue_state_label: "Emitido",
            primary_pdf_storage_version: "v0003",
            current_primary_pdf_storage_version: "v0004",
          },
        }),
        criarLaudoParcial({
          id: 19,
          titulo: "Caso estável",
        }),
      ],
      notificacoes: [],
      pendenciaFilaProntaParaReenvio: jest.fn().mockReturnValue(false),
      prioridadePendenciaOffline: jest.fn().mockReturnValue(0),
      session: null,
      statusApi: "online",
    });

    expect(
      state.historicoAgrupadoFinal[0]?.items.map((item) => item.id),
    ).toEqual([18]);
  });

  it("prioriza match exato por ID no histórico quando a busca é numérica", () => {
    const state = buildInspectorHistoryAndOfflineDerivedState({
      buscaHistorico: "4",
      buildHistorySections: jest.fn((items) => [
        {
          key: "resultado",
          title: "Resultado",
          items,
        },
      ]),
      filaOffline: [],
      filtroFilaOffline: "all",
      filtroHistorico: "todos",
      fixarConversas: false,
      historicoOcultoIds: [],
      laudosDisponiveis: [
        criarLaudoParcial({
          id: 124,
          titulo: "Caso 124",
          preview: "resultado automatizado 124",
        }),
        criarLaudoParcial({
          id: 4,
          titulo: "Caso alvo",
          preview: "resultado automatizado 4",
        }),
        criarLaudoParcial({
          id: 84,
          titulo: "Caso 84",
          preview: "resultado automatizado 84",
        }),
      ],
      notificacoes: [],
      pendenciaFilaProntaParaReenvio: jest.fn().mockReturnValue(false),
      prioridadePendenciaOffline: jest.fn().mockReturnValue(0),
      session: null,
      statusApi: "online",
    });

    expect(
      state.historicoAgrupadoFinal[0]?.items.map((item) => item.id),
    ).toEqual([4]);
  });

  it("esconde fila e notificações de mesa quando o usuário não tem grant de revisor", () => {
    const state = buildInspectorHistoryAndOfflineDerivedState({
      buscaHistorico: "",
      buildHistorySections: jest.fn((items) => [
        {
          key: "todos",
          title: "Todos",
          items,
        },
      ]),
      filaOffline: [
        criarPendenciaParcial({
          id: "mesa-1",
          channel: "mesa",
        }),
        criarPendenciaParcial({
          id: "chat-1",
          channel: "chat",
        }),
      ],
      filtroFilaOffline: "all",
      filtroHistorico: "todos",
      fixarConversas: false,
      historicoOcultoIds: [],
      laudosDisponiveis: [criarLaudoParcial({ id: 10 })],
      notificacoes: [
        criarNotificacaoParcial({
          id: "notif-chat",
          targetThread: "chat",
          kind: "status",
        }),
        criarNotificacaoParcial({
          id: "notif-mesa",
          targetThread: "mesa",
          kind: "mesa_nova",
        }),
      ],
      pendenciaFilaProntaParaReenvio: jest.fn().mockReturnValue(true),
      prioridadePendenciaOffline: jest.fn().mockReturnValue(0),
      session: {
        accessToken: "token-123",
        bootstrap: {
          ok: true,
          app: {
            api_base_url: "https://tariel.test",
            nome: "Tariel Inspetor",
            portal: "inspetor",
            suporte_whatsapp: "",
          },
          usuario: {
            id: 7,
            nome_completo: "Inspetor Tariel",
            email: "inspetor@tariel.test",
            telefone: "",
            foto_perfil_url: "",
            empresa_nome: "Empresa A",
            empresa_id: 33,
            nivel_acesso: 1,
            allowed_portals: ["inspetor"],
          },
        },
      },
      statusApi: "online",
    });

    expect(state.filaOfflineOrdenada.map((item) => item.id)).toEqual([
      "chat-1",
    ]);
    expect(state.totalFilaOfflineMesa).toBe(0);
    expect(state.notificacoesNaoLidas).toBe(1);
  });

  it("mantém o topo em tela cheia no layout derivado", () => {
    const state = buildInspectorLayoutDerivedState({
      keyboardHeight: 0,
    });

    expect(state.headerSafeTopInset).toBe(0);
  });

  it("resume conta e workspace com grants reais do tenant", () => {
    const state = buildInspectorSettingsDerivedState({
      arquivosPermitidos: true,
      buscaAjuda: "",
      buscaConfiguracoes: "",
      cameraPermitida: true,
      codigosRecuperacao: [],
      contaTelefone: "(11) 99999-0000",
      corDestaque: "laranja",
      densidadeInterface: "confortável",
      email: "inspetor@tariel.test",
      emailAtualConta: "inspetor@tariel.test",
      estiloResposta: "objetivo",
      eventosSeguranca: [],
      filaSuporteLocal: [],
      filtroConfiguracoes: "all",
      filtroEventosSeguranca: "todos",
      formatarHorarioAtividade: jest.fn().mockReturnValue("Agora"),
      formatarTipoTemplateLaudo: jest.fn().mockReturnValue("Laranja"),
      idiomaResposta: "pt-BR",
      integracoesExternas: [],
      lockTimeout: "5min",
      microfonePermitido: true,
      modeloIa: "equilibrado",
      mostrarConteudoNotificacao: false,
      mostrarSomenteNovaMensagem: true,
      notificacoesPermitidas: true,
      ocultarConteudoBloqueado: true,
      perfilExibicao: "Tariel",
      perfilNome: "Inspetor Tariel",
      planoAtual: "Free",
      laudosDisponiveis: [
        criarLaudoParcial({
          id: 90,
          official_issue_summary: {
            label: "Reemissão recomendada",
            detail: "PDF emitido divergente · Emitido v0003 · Atual v0004",
            primary_pdf_diverged: true,
            issue_number: "EO-90",
            issue_state_label: "Emitido",
            primary_pdf_storage_version: "v0003",
            current_primary_pdf_storage_version: "v0004",
          },
        }),
        criarLaudoParcial({ id: 91 }),
      ],
      provedoresConectados: [],
      reautenticacaoStatus: "Não confirmada",
      recoveryCodesEnabled: false,
      salvarHistoricoConversas: true,
      session: {
        accessToken: "token-123",
        bootstrap: {
          ok: true,
          app: {
            api_base_url: "https://tariel.test",
            nome: "Tariel Inspetor",
            portal: "inspetor",
            suporte_whatsapp: "",
          },
          usuario: {
            id: 1,
            nome_completo: "Inspetor Tariel",
            email: "inspetor@tariel.test",
            telefone: "(11) 99999-0000",
            foto_perfil_url: "",
            empresa_nome: "Empresa A",
            empresa_id: 7,
            nivel_acesso: 1,
            allowed_portals: ["inspetor", "revisor", "cliente"],
            commercial_operating_model: "mobile_single_operator",
            commercial_operating_model_label:
              "Mobile principal com operador único",
          },
        },
      },
      settingsDrawerPage: "overview",
      settingsDrawerSection: "all",
      sessoesAtivas: [],
      somNotificacao: "Ping",
      statusAtualizacaoApp: "Atualizado",
      temaApp: "claro",
      twoFactorEnabled: false,
      twoFactorMethod: "app",
      ultimaVerificacaoAtualizacao: "",
      conversasFixadasTotal: 0,
      conversasVisiveisTotal: 0,
      temaEfetivo: "claro",
    } as never);

    expect(state.workspaceResumoConfiguracao).toBe(
      "Empresa A • Mobile principal com operador único",
    );
    expect(state.resumoContaAcesso).toBe(
      "Empresa #7 • Inspetor web/mobile + Mesa Avaliadora + Admin-Cliente • Mobile principal com operador único",
    );
    expect(state.reemissoesRecomendadasTotal).toBe(1);
    expect(state.resumoGovernancaConfiguracao).toBe(
      "1 caso com reemissão recomendada",
    );
  });

  it("remove artigos de ajuda da mesa quando a conta não tem grant de revisor", () => {
    const state = buildInspectorSettingsDerivedState({
      arquivosPermitidos: true,
      buscaAjuda: "",
      buscaConfiguracoes: "",
      cameraPermitida: true,
      codigosRecuperacao: [],
      contaTelefone: "(11) 99999-0000",
      corDestaque: "laranja",
      densidadeInterface: "confortável",
      email: "inspetor@tariel.test",
      emailAtualConta: "inspetor@tariel.test",
      estiloResposta: "objetivo",
      eventosSeguranca: [],
      filaSuporteLocal: [],
      filtroConfiguracoes: "all",
      filtroEventosSeguranca: "todos",
      formatarHorarioAtividade: jest.fn().mockReturnValue("Agora"),
      formatarTipoTemplateLaudo: jest.fn().mockReturnValue("Laranja"),
      idiomaResposta: "pt-BR",
      integracoesExternas: [],
      lockTimeout: "5min",
      microfonePermitido: true,
      modeloIa: "equilibrado",
      mostrarConteudoNotificacao: false,
      mostrarSomenteNovaMensagem: true,
      notificacoesPermitidas: true,
      ocultarConteudoBloqueado: true,
      perfilExibicao: "Tariel",
      perfilNome: "Inspetor Tariel",
      planoAtual: "Free",
      provedoresConectados: [],
      reautenticacaoStatus: "Não confirmada",
      recoveryCodesEnabled: false,
      salvarHistoricoConversas: true,
      session: {
        accessToken: "token-123",
        bootstrap: {
          ok: true,
          app: {
            api_base_url: "https://tariel.test",
            nome: "Tariel Inspetor",
            portal: "inspetor",
            suporte_whatsapp: "",
          },
          usuario: {
            id: 1,
            nome_completo: "Inspetor Tariel",
            email: "inspetor@tariel.test",
            telefone: "(11) 99999-0000",
            foto_perfil_url: "",
            empresa_nome: "Empresa A",
            empresa_id: 7,
            nivel_acesso: 1,
            allowed_portals: ["inspetor"],
          },
        },
      },
      settingsDrawerPage: "overview",
      settingsDrawerSection: "all",
      sessoesAtivas: [],
      somNotificacao: "Ping",
      statusAtualizacaoApp: "Atualizado",
      temaApp: "claro",
      twoFactorEnabled: false,
      twoFactorMethod: "app",
      ultimaVerificacaoAtualizacao: "",
      conversasFixadasTotal: 0,
      conversasVisiveisTotal: 0,
      temaEfetivo: "claro",
    } as never);

    expect(
      state.artigosAjudaFiltrados.some(
        (item) => item.id === "help-mesa-avaliadora",
      ),
    ).toBe(false);
  });
});
