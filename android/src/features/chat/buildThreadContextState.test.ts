import { buildThreadContextState } from "./buildThreadContextState";
import { createGuidedInspectionDraft } from "../inspection/guidedInspection";

function criarInput(overrides?: Record<string, unknown>) {
  return {
    caseCreationError: "",
    caseCreationState: "idle" as const,
    conversaAtiva: null,
    entryModePreference: "auto_recommended" as const,
    filtrarThreadContextChips: (items: Array<any>) => items.filter(Boolean),
    guidedInspectionDraft: null,
    laudosDisponiveis: [],
    mapearStatusLaudoVisual: () => ({
      icon: "check-decagram-outline" as const,
      tone: "success" as const,
    }),
    mesaDisponivel: false,
    mesaTemMensagens: false,
    mensagensMesa: [],
    notificacoesMesaLaudoAtual: 0,
    onAdvanceGuidedInspection: jest.fn(),
    onOpenMesaTab: jest.fn(),
    onOpenQualityGate: jest.fn(),
    onResumeGuidedInspection: jest.fn(),
    onStartFreeChat: jest.fn(),
    onStartGuidedInspection: jest.fn(),
    onStopGuidedInspection: jest.fn(),
    rememberLastCaseMode: false,
    resumoFilaOffline: "",
    statusApi: "online" as const,
    threadHomeVisible: true,
    tipoTemplateAtivoLabel: "NR35",
    vendoFinalizacao: false,
    vendoMesa: false,
    ...overrides,
  };
}

describe("buildThreadContextState", () => {
  it("mostra o seletor inicial entre chat livre e inspecao guiada", () => {
    const onStartGuidedInspection = jest.fn();
    const state = buildThreadContextState(
      criarInput({
        onStartGuidedInspection,
      }) as never,
    );

    expect(state.mostrarContextoThread).toBe(true);
    expect(state.threadContextLayout).toBe("entry_chooser");
    expect(state.laudoContextTitle).toBe("Por onde começar?");
    expect(state.threadSpotlight.label).toBe("Chat livre como padrão");
    expect(state.threadInsights).toEqual([]);
    expect(state.chipsContextoThread).toEqual([]);
    expect(state.threadActions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "chat-free-start",
          label: "Chat livre",
        }),
        expect.objectContaining({
          key: "guided-template-rti",
          label: "NR10 RTI Eletrica",
        }),
        expect.objectContaining({
          key: "guided-template-loto",
          label: "NR10 LOTO",
        }),
        expect.objectContaining({
          key: "guided-template-nr35_linha_vida",
          label: "NR35 Inspecao de Linha de Vida",
        }),
        expect.objectContaining({
          key: "guided-template-nr13",
          label: "NR13 Inspecoes e Integridade",
        }),
      ]),
    );
    expect(state.laudoContextDescription).toBe("Escolha um modo para iniciar.");

    const nr35Action = state.threadActions.find(
      (item) => item.key === "guided-template-nr35_linha_vida",
    );
    expect(nr35Action).toBeTruthy();

    nr35Action?.onPress();

    expect(onStartGuidedInspection).toHaveBeenCalledWith("nr35_linha_vida");
  });

  it("esconde a home e libera o composer depois que o chat livre foi escolhido", () => {
    const state = buildThreadContextState(
      criarInput({
        conversaAtiva: {
          laudoId: null,
          estado: "sem_relatorio",
          statusCard: "aberto",
          permiteEdicao: true,
          permiteReabrir: false,
          laudoCard: null,
          modo: "detalhado",
          mensagens: [],
        },
        threadHomeVisible: false,
      }) as never,
    );

    expect(state.mostrarContextoThread).toBe(false);
    expect(state.threadContextLayout).toBe("default");
  });

  it("troca o contexto para checklist guiado quando o draft esta ativo", () => {
    const draft = createGuidedInspectionDraft();
    draft.evidenceRefs = [
      {
        messageId: 90,
        stepId: "identificacao_ativo",
        stepTitle: "Identificacao do ativo e da area",
        capturedAt: "2026-04-06T22:31:00.000Z",
        evidenceKind: "chat_message",
        attachmentKind: "image",
      },
    ];
    draft.mesaHandoff = {
      required: true,
      reviewMode: "mesa_required",
      reasonCode: "policy_review_mode",
      recordedAt: "2026-04-06T22:31:30.000Z",
      stepId: "identificacao_ativo",
      stepTitle: "Identificacao do ativo e da area",
    };
    const state = buildThreadContextState(
      criarInput({
        guidedInspectionDraft: draft,
      }) as never,
    );

    expect(state.laudoContextTitle).toBe("Inspecao Geral");
    expect(state.threadSpotlight.label).toBe("IA conduzindo coleta");
    expect(state.threadInsights[0]?.value).toBe("0/5");
    expect(state.chipsContextoThread).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "mesa-handoff",
          label: "Mesa requerida",
        }),
      ]),
    );
    expect(state.threadInsights).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ key: "bundle", value: "1 evid." }),
        expect.objectContaining({
          key: "ultima-evidencia",
          value: "Identificacao do ativo e da area",
        }),
        expect.objectContaining({ key: "mesa", value: "Mesa obrigatória" }),
      ]),
    );
    expect(state.threadActions).toEqual([
      expect.objectContaining({ key: "guided-advance" }),
      expect.objectContaining({ key: "guided-stop" }),
    ]);
  });

  it("expõe o estado de criação do caso enquanto o primeiro envio está em processamento", () => {
    const state = buildThreadContextState(
      criarInput({
        caseCreationState: "creating" as const,
        conversaAtiva: {
          laudoId: null,
          estado: "sem_relatorio",
          statusCard: "aberto",
          permiteEdicao: true,
          permiteReabrir: false,
          laudoCard: null,
          modo: "detalhado",
          mensagens: [
            {
              id: 1,
              papel: "usuario",
              texto: "Abrir inspeção",
              tipo: "user",
            },
          ],
        },
      }) as never,
    );

    expect(state.threadContextLayout).toBe("default");
    expect(state.laudoContextTitle).toBe("Criando caso...");
    expect(state.threadSpotlight.label).toBe("Criando caso");
    expect(state.chipsContextoThread).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "creation-state",
          label: "1º envio em processamento",
        }),
      ]),
    );
    expect(state.threadInsights).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "case-creation",
          value: "Em processamento",
        }),
      ]),
    );
    expect(state.threadActions).toEqual([]);
  });

  it("expõe quando a criação do caso ficou aguardando sincronização offline", () => {
    const state = buildThreadContextState(
      criarInput({
        caseCreationState: "queued_offline" as const,
        resumoFilaOffline: "1 pendência pronta para sincronizar",
        statusApi: "offline" as const,
      }) as never,
    );

    expect(state.laudoContextTitle).toBe("Caso aguardando sincronização");
    expect(state.threadSpotlight.label).toBe("Aguardando rede");
    expect(state.chipsContextoThread).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "creation-state",
          label: "Caso no próximo sync",
        }),
      ]),
    );
    expect(state.threadInsights).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "case-creation",
          value: "Na fila local",
        }),
      ]),
    );
    expect(state.threadActions).toEqual([]);
  });

  it("destaca falha de criação do caso sem esconder o retry manual", () => {
    const onStartGuidedInspection = jest.fn();
    const state = buildThreadContextState(
      criarInput({
        caseCreationError: "Falha ao criar o caso.",
        caseCreationState: "error" as const,
        onStartGuidedInspection,
      }) as never,
    );

    expect(state.laudoContextTitle).toBe("Falha ao criar caso");
    expect(state.threadSpotlight.label).toBe("Falha no 1º envio");
    expect(state.threadInsights).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "case-creation",
          value: "Falhou",
        }),
      ]),
    );
    expect(state.threadActions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ key: "chat-free-start" }),
        expect.objectContaining({
          key: "guided-template-nr11_movimentacao",
        }),
      ]),
    );

    const nr35Action = state.threadActions.find(
      (item) => item.key === "guided-template-nr35_linha_vida",
    );
    nr35Action?.onPress();
    expect(onStartGuidedInspection).toHaveBeenCalledWith("nr35_linha_vida");
  });

  it("mantém o chat livre fora da trilha formal mesmo com metadado auxiliar no payload", () => {
    const state = buildThreadContextState(
      criarInput({
        conversaAtiva: {
          laudoId: 41,
          estado: "relatorio_ativo",
          statusCard: "aberto",
          permiteEdicao: true,
          permiteReabrir: false,
          caseLifecycleStatus: "pre_laudo",
          caseWorkflowMode: "laudo_guiado",
          allowedSurfaceActions: [],
          laudoCard: {
            id: 41,
            titulo: "Chat livre 41",
            preview: "Resumo livre",
            pinado: false,
            data_iso: "2026-04-14T10:00:00.000Z",
            data_br: "14/04/2026",
            hora_br: "10:00",
            tipo_template: "padrao",
            status_revisao: "ativo",
            status_card: "aberto",
            status_card_label: "Em andamento",
            permite_edicao: true,
            permite_reabrir: false,
            possui_historico: true,
            case_lifecycle_status: "pre_laudo",
            case_workflow_mode: "laudo_guiado",
            entry_mode_effective: "chat_first",
          },
          reportPackDraft: {} as never,
          reviewPackage: {
            emissao_oficial: {
              current_issue: {
                issue_number: "TAR-20260414-000041",
              },
            },
          } as never,
          modo: "detalhado",
          mensagens: [],
        },
      }) as never,
    );

    expect(state.threadSpotlight.label).toBe("Chat livre ativo");
    expect(state.chipsContextoThread).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "status",
          label: "Chat livre",
        }),
      ]),
    );
    expect(state.threadInsights).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "mode",
          value: "Chat livre",
        }),
      ]),
    );
    expect(
      state.threadInsights.find((item) => item.key === "report-pack"),
    ).toBeUndefined();
    expect(
      state.threadInsights.find((item) => item.key === "inspection-context"),
    ).toBeUndefined();
    expect(
      state.threadActions.find((item) => item.key === "chat-quality-gate"),
    ).toBeUndefined();
  });

  it("abre a mesa nativa quando o handoff guiado exige revisão humana e o checklist está concluído", () => {
    const draft = createGuidedInspectionDraft();
    draft.completedStepIds = draft.checklist.map((item) => item.id);
    draft.currentStepIndex = draft.checklist.length - 1;
    draft.mesaHandoff = {
      required: true,
      reviewMode: "mesa_required",
      reasonCode: "policy_review_mode",
      recordedAt: "2026-04-06T22:31:30.000Z",
      stepId: draft.checklist[0]!.id,
      stepTitle: draft.checklist[0]!.title,
    };
    const onOpenMesaTab = jest.fn();

    const state = buildThreadContextState(
      criarInput({
        guidedInspectionDraft: draft,
        mesaDisponivel: true,
        onOpenMesaTab,
      }) as never,
    );

    expect(state.threadInsights).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "mesa",
          value: "Mesa obrigatória",
          detail: expect.stringContaining(
            "A política ativa do tenant exige revisão humana antes da emissão.",
          ),
        }),
      ]),
    );
    expect(state.threadActions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "guided-open-mesa",
          label: "Abrir Mesa",
          onPress: onOpenMesaTab,
        }),
      ]),
    );
  });

  it("prioriza a coleta guiada no estado vazio quando o modo efetivo cai para evidence_first", () => {
    const state = buildThreadContextState(
      criarInput({
        laudosDisponiveis: [
          {
            entry_mode_effective: "evidence_first",
            entry_mode_reason: "last_case_mode",
            id: 91,
          },
        ],
        rememberLastCaseMode: true,
      }) as never,
    );

    expect(state.threadContextLayout).toBe("entry_chooser");
    expect(state.laudoContextTitle).toBe("Por onde começar?");
    expect(state.threadSpotlight.label).toBe("IA recomenda guiado");
    expect(state.chipsContextoThread).toEqual([]);
    expect(state.threadActions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "chat-free-start",
          label: "Chat livre",
        }),
        expect.objectContaining({
          key: "guided-template-nr35_linha_vida",
          label: "NR35 Inspecao de Linha de Vida",
        }),
      ]),
    );
  });

  it("leva o agregado de reemissão para a home operacional antes de abrir um caso", () => {
    const state = buildThreadContextState(
      criarInput({
        laudosDisponiveis: [
          {
            id: 201,
            official_issue_summary: {
              label: "Reemissão recomendada",
              detail: "PDF emitido divergente · Emitido v0003 · Atual v0004",
              primary_pdf_diverged: true,
              issue_number: "EO-201",
              issue_state_label: "Emitido",
              primary_pdf_storage_version: "v0003",
              current_primary_pdf_storage_version: "v0004",
            },
          },
          {
            id: 202,
            official_issue_summary: {
              label: "Reemissão recomendada",
              detail: "PDF emitido divergente · Emitido v0002 · Atual v0003",
              primary_pdf_diverged: true,
              issue_number: "EO-202",
              issue_state_label: "Emitido",
              primary_pdf_storage_version: "v0002",
              current_primary_pdf_storage_version: "v0003",
            },
          },
        ],
      }) as never,
    );

    expect(state.threadContextLayout).toBe("entry_chooser");
    expect(state.chipsContextoThread).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "governance-reissue",
          label: "2 reemissões recomendadas",
        }),
      ]),
    );
    expect(state.threadInsights).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "governance-reissue",
          label: "Governança",
          value: "2 reemissões recomendadas",
          tone: "danger",
        }),
      ]),
    );
  });

  it("oferece retomada guiada ao reabrir um caso ativo em evidence_first", () => {
    const onResumeGuidedInspection = jest.fn();
    const state = buildThreadContextState(
      criarInput({
        conversaAtiva: {
          estado: "relatorio_ativo",
          laudoId: 77,
          laudoCard: {
            entry_mode_effective: "evidence_first",
            entry_mode_reason: "existing_case_state",
            hora_br: "14:10",
            data_br: "06/04/2026",
            status_card_label: "Em andamento",
          },
          mensagens: [],
          modo: "detalhado",
          permiteEdicao: true,
          permiteReabrir: false,
          statusCard: "aberto",
        },
        onResumeGuidedInspection,
      }) as never,
    );

    expect(state.threadSpotlight.label).toBe("Coleta guiada preferida");
    expect(state.threadActions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "guided-resume",
          label: "Retomar coleta guiada",
          onPress: onResumeGuidedInspection,
        }),
      ]),
    );
  });

  it("prioriza o lifecycle canonico quando o caso esta com a mesa", () => {
    const state = buildThreadContextState(
      criarInput({
        conversaAtiva: {
          estado: "aguardando",
          laudoId: 91,
          laudoCard: {
            titulo: "Caso 91",
            status_card: "aberto",
            status_card_label: "Em andamento",
            case_lifecycle_status: "em_revisao_mesa",
            active_owner_role: "mesa",
          },
          mensagens: [],
          modo: "detalhado",
          permiteEdicao: false,
          permiteReabrir: false,
          statusCard: "aberto",
          caseLifecycleStatus: "em_revisao_mesa",
          activeOwnerRole: "mesa",
        },
      }) as never,
    );

    expect(state.threadSpotlight.label).toBe("Mesa em revisão");
    expect(state.threadInsights[0]).toEqual(
      expect.objectContaining({
        label: "Lifecycle",
        value: "Mesa em revisão",
      }),
    );
  });

  it("destaca documento emitido e reabertura como novo ciclo", () => {
    const state = buildThreadContextState(
      criarInput({
        conversaAtiva: {
          estado: "aprovado",
          laudoId: 95,
          laudoCard: {
            titulo: "Caso 95",
            status_card: "aprovado",
            status_card_label: "Aprovado",
            case_lifecycle_status: "emitido",
            active_owner_role: "none",
          },
          mensagens: [],
          modo: "detalhado",
          permiteEdicao: false,
          permiteReabrir: true,
          statusCard: "aprovado",
          caseLifecycleStatus: "emitido",
          activeOwnerRole: "none",
        },
      }) as never,
    );

    expect(state.threadSpotlight.label).toBe("Documento emitido");
    expect(state.chipsContextoThread).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "reabrir",
          label: "Reabra para novo ciclo",
        }),
      ]),
    );
  });

  it("prioriza a ação canônica de reabrir mesmo sem o flag legado", () => {
    const state = buildThreadContextState(
      criarInput({
        conversaAtiva: {
          estado: "aprovado",
          laudoId: 96,
          laudoCard: {
            titulo: "Caso 96",
            status_card: "aprovado",
            status_card_label: "Aprovado",
            case_lifecycle_status: "emitido",
            active_owner_role: "none",
            allowed_surface_actions: ["chat_reopen"],
          },
          mensagens: [],
          modo: "detalhado",
          permiteEdicao: false,
          permiteReabrir: false,
          statusCard: "aprovado",
          caseLifecycleStatus: "emitido",
          activeOwnerRole: "none",
          allowedSurfaceActions: ["chat_reopen"],
        },
      }) as never,
    );

    expect(state.threadSpotlight.label).toBe("Documento emitido");
    expect(state.chipsContextoThread).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "reabrir",
          label: "Reabra para novo ciclo",
        }),
      ]),
    );
  });

  it("expõe a finalização canônica do caso quando o chat permite encerrar", () => {
    const onOpenQualityGate = jest.fn();
    const state = buildThreadContextState(
      criarInput({
        conversaAtiva: {
          estado: "relatorio_ativo",
          laudoId: 104,
          laudoCard: {
            titulo: "Caso 104",
            status_card: "aberto",
            status_card_label: "Em andamento",
            case_lifecycle_status: "laudo_em_coleta",
            active_owner_role: "inspetor",
            allowed_surface_actions: ["chat_finalize"],
          },
          mensagens: [],
          modo: "detalhado",
          permiteEdicao: true,
          permiteReabrir: false,
          statusCard: "aberto",
          caseLifecycleStatus: "laudo_em_coleta",
          activeOwnerRole: "inspetor",
          allowedSurfaceActions: ["chat_finalize"],
        },
        onOpenQualityGate,
      }) as never,
    );

    expect(state.threadActions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "chat-quality-gate",
          label: "Finalizar caso",
          onPress: expect.any(Function),
        }),
      ]),
    );
    const action = state.threadActions.find(
      (item) => item.key === "chat-quality-gate",
    );
    action?.onPress();
    expect(onOpenQualityGate).toHaveBeenCalled();
  });

  it("mostra a prontidão do pre-laudo por blocos no contexto do caso", () => {
    const state = buildThreadContextState(
      criarInput({
        conversaAtiva: {
          estado: "relatorio_ativo",
          laudoId: 108,
          laudoCard: {
            titulo: "Caso 108",
            status_card: "aberto",
            status_card_label: "Em andamento",
            hora_br: "16:40",
            data_br: "13/04/2026",
            tipo_template: "NR35",
            case_lifecycle_status: "laudo_em_coleta",
            active_owner_role: "inspetor",
          },
          mensagens: [],
          modo: "detalhado",
          permiteEdicao: true,
          permiteReabrir: false,
          statusCard: "aberto",
          caseLifecycleStatus: "laudo_em_coleta",
          activeOwnerRole: "inspetor",
          reportPackDraft: {
            modeled: true,
            template_label: "NR35 Linha de Vida",
            guided_context: {
              asset_label: "Linha de vida cobertura A",
              location_label: "Bloco 2",
              inspection_objective:
                "Validar ancoragem principal antes da liberacao.",
              checklist_ids: ["identificacao", "ancoragem", "conclusao"],
              completed_step_ids: ["identificacao"],
            },
            image_slots: [
              { slot: "vista_geral", status: "resolved" },
              { slot: "ponto_superior", status: "pending" },
            ],
            items: [
              {
                item_codigo: "fixacao",
                veredito_ia_normativo: "C",
                approved_for_emission: true,
                missing_evidence: [],
              },
              {
                item_codigo: "cabo",
                veredito_ia_normativo: "pendente",
                approved_for_emission: false,
                missing_evidence: ["status_normativo_nao_confirmado"],
              },
            ],
            structured_data_candidate: null,
            quality_gates: {
              checklist_complete: false,
              required_image_slots_complete: false,
              critical_items_complete: false,
              autonomy_ready: false,
              requires_normative_curation: true,
              final_validation_mode: "mesa_required",
            },
          },
        },
      }) as never,
    );

    expect(state.threadInsights).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "report-pack",
          label: "Pre-laudo",
          value: "0/5 blocos",
          detail: expect.stringContaining("Pre-laudo em montagem"),
          tone: "accent",
        }),
        expect.objectContaining({
          key: "inspection-context",
          label: "Ativo",
          value: "Linha de vida cobertura A · Bloco 2",
        }),
      ]),
    );
  });

  it("transforma a aba Finalizar em uma superfície dedicada de fechamento", () => {
    const onOpenQualityGate = jest.fn();
    const onOpenMesaTab = jest.fn();
    const state = buildThreadContextState(
      criarInput({
        conversaAtiva: {
          estado: "relatorio_ativo",
          laudoId: 120,
          laudoCard: {
            titulo: "Linha de vida cobertura A",
            status_card: "aberto",
            status_card_label: "Em andamento",
            case_lifecycle_status: "laudo_em_coleta",
            active_owner_role: "inspetor",
            allowed_surface_actions: ["chat_finalize"],
          },
          mensagens: [],
          modo: "detalhado",
          permiteEdicao: true,
          permiteReabrir: false,
          statusCard: "aberto",
          caseLifecycleStatus: "laudo_em_coleta",
          activeOwnerRole: "inspetor",
          allowedSurfaceActions: ["chat_finalize"],
          reportPackDraft: {
            quality_gates: {
              final_validation_mode: "mesa_required",
              autonomy_ready: false,
              missing_evidence: [{ message: "Falta foto obrigatoria." }],
            },
            items: [
              {
                item_codigo: "fixacao",
                veredito_ia_normativo: "pendente",
                approved_for_emission: false,
                missing_evidence: ["status_normativo_nao_confirmado"],
              },
            ],
          },
          reviewPackage: {
            review_mode: "mesa_required",
            review_required: true,
            document_blockers: [{ blocker_code: "pending_review" }],
            emissao_oficial: {
              eligible_signatory_count: 1,
              signature_status_label: "Signatario governado pronto",
            },
          },
        },
        mesaDisponivel: true,
        onOpenMesaTab,
        onOpenQualityGate,
        vendoFinalizacao: true,
      }) as never,
    );

    expect(state.threadContextLayout).toBe("finalization");
    expect(state.threadSpotlight.label).toBe("Pendências antes do PDF");
    expect(state.chipsContextoThread).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "outcome",
          label: "Saída: laudo formal",
        }),
        expect.objectContaining({
          key: "review-mode",
          label: "Mesa obrigatória",
        }),
      ]),
    );
    expect(state.threadInsights).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "final-output",
          value: "Laudo formal",
        }),
        expect.objectContaining({
          key: "human-validation",
          value: "Mesa obrigatória",
        }),
        expect.objectContaining({
          key: "next-step",
          value: "Corrigir e revisar",
        }),
      ]),
    );
    expect(state.threadActions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "finalization-open-mesa",
          label: "Abrir Mesa",
          onPress: onOpenMesaTab,
        }),
        expect.objectContaining({
          key: "chat-quality-gate",
          label: "Finalizar caso",
          onPress: expect.any(Function),
        }),
      ]),
    );
  });

  it("mostra emissão governada em curso quando o PDF já entrou no trilho oficial", () => {
    const state = buildThreadContextState(
      criarInput({
        conversaAtiva: {
          estado: "aprovado",
          laudoId: 99,
          laudoCard: {
            id: 99,
            titulo: "Laudo 99",
            preview: "Resumo",
            pinado: false,
            data_iso: "2026-04-14T10:00:00.000Z",
            data_br: "14/04/2026",
            hora_br: "10:00",
            tipo_template: "nr35",
            status_revisao: "aprovado",
            status_card: "aprovado",
            status_card_label: "Aprovado",
            permite_edicao: false,
            permite_reabrir: false,
            possui_historico: true,
            case_lifecycle_status: "aprovado",
            active_owner_role: "none",
            allowed_surface_actions: [],
          },
          mensagens: [],
          modo: "detalhado",
          permiteEdicao: false,
          permiteReabrir: false,
          statusCard: "aprovado",
          caseLifecycleStatus: "aprovado",
          activeOwnerRole: "none",
          allowedSurfaceActions: [],
          reportPackDraft: {
            quality_gates: {
              final_validation_mode: "mobile_autonomous",
              autonomy_ready: true,
              missing_evidence: [],
            },
            items: [],
          },
          reviewPackage: {
            review_mode: "mobile_autonomous",
            review_required: false,
            document_blockers: [],
            emissao_oficial: {
              current_issue: {
                issue_number: "TAR-20260414-000099",
                issue_state_label: "Assinando",
                issued_at: "2026-04-14T15:03:00+00:00",
              },
            },
            public_verification: {
              verification_url: "/app/public/laudo/verificar/hash099",
            },
          },
        },
        vendoFinalizacao: true,
      }) as never,
    );

    expect(state.threadSpotlight.label).toBe("Emissão em curso");
    expect(state.threadInsights).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "delivery",
          value: "TAR-20260414-000099",
        }),
        expect.objectContaining({
          key: "verification",
          value: "Link disponível",
        }),
        expect.objectContaining({
          key: "next-step",
          value: "Acompanhar emissão",
        }),
      ]),
    );
  });

  it("prioriza reemissão quando o PDF atual diverge da emissão oficial congelada", () => {
    const state = buildThreadContextState(
      criarInput({
        conversaAtiva: {
          estado: "aprovado",
          laudoId: 101,
          laudoCard: {
            id: 101,
            titulo: "Laudo 101",
            preview: "Resumo",
            pinado: false,
            data_iso: "2026-04-14T10:00:00.000Z",
            data_br: "14/04/2026",
            hora_br: "10:00",
            tipo_template: "nr35",
            status_revisao: "aprovado",
            status_card: "aprovado",
            status_card_label: "Aprovado",
            permite_edicao: false,
            permite_reabrir: false,
            possui_historico: true,
            case_lifecycle_status: "aprovado",
            active_owner_role: "none",
            allowed_surface_actions: [],
          },
          mensagens: [],
          modo: "detalhado",
          permiteEdicao: false,
          permiteReabrir: false,
          statusCard: "aprovado",
          caseLifecycleStatus: "aprovado",
          activeOwnerRole: "none",
          allowedSurfaceActions: [],
          reportPackDraft: {
            quality_gates: {
              final_validation_mode: "mobile_autonomous",
              autonomy_ready: true,
              missing_evidence: [],
            },
            items: [],
          },
          reviewPackage: {
            review_mode: "mobile_autonomous",
            review_required: false,
            document_blockers: [],
            emissao_oficial: {
              reissue_recommended: true,
              current_issue: {
                issue_number: "TAR-20260414-000101",
                issue_state_label: "Emitido",
                issued_at: "2026-04-14T15:03:00+00:00",
                primary_pdf_diverged: true,
                primary_pdf_storage_version: "v0003",
                current_primary_pdf_storage_version: "v0004",
              },
            },
            public_verification: {
              verification_url: "/app/public/laudo/verificar/hash101",
            },
          },
        },
        vendoFinalizacao: true,
      }) as never,
    );

    expect(state.threadSpotlight.label).toBe("Reemissão recomendada");
    expect(state.threadInsights).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "delivery",
          detail: expect.stringContaining("PDF atual divergiu do emitido"),
        }),
        expect.objectContaining({
          key: "next-step",
          value: "Reemitir documento",
        }),
      ]),
    );
  });
});
