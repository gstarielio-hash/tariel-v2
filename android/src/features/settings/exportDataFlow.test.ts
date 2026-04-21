import {
  runExportDataFlow,
  type RunExportDataFlowParams,
} from "./exportDataFlow";

function criarParams(): RunExportDataFlowParams {
  return {
    formato: "JSON",
    reautenticacaoExpiraEm: "2099-01-01T00:00:00.000Z",
    reautenticacaoAindaValida: jest.fn().mockReturnValue(true),
    abrirFluxoReautenticacao: jest.fn(),
    registrarEventoSegurancaLocal: jest.fn(),
    abrirSheetConfiguracao: jest.fn(),
    perfilNome: "Gabriel",
    perfilExibicao: "Gabriel",
    emailAtualConta: "gabriel@tariel.test",
    email: "gabriel@tariel.test",
    planoAtual: "pro",
    workspaceResumoConfiguracao:
      "Empresa A • Mobile principal com operador único",
    resumoContaAcesso:
      "Empresa #33 • Inspetor web/mobile + Mesa Avaliadora + Admin-Cliente • Mobile principal com operador único",
    identityRuntimeNote:
      "A conta principal do tenant pode receber multiplas superficies conforme o cadastro definido no Admin-CEO.",
    portalContinuationSummary:
      "Inspetor web/mobile (/app/) • Mesa Avaliadora (/revisao/painel) • Admin-Cliente (/cliente/painel)",
    modeloIa: "equilibrado",
    estiloResposta: "detalhado",
    idiomaResposta: "pt-BR",
    temaApp: "claro",
    tamanhoFonte: "médio",
    densidadeInterface: "confortável",
    corDestaque: "laranja",
    memoriaIa: true,
    aprendizadoIa: true,
    economiaDados: false,
    usoBateria: "equilibrado",
    notificaPush: true,
    notificaRespostas: true,
    emailsAtivos: true,
    vibracaoAtiva: true,
    mostrarConteudoNotificacao: true,
    mostrarSomenteNovaMensagem: false,
    salvarHistoricoConversas: true,
    compartilharMelhoriaIa: true,
    retencaoDados: "90_dias",
    ocultarConteudoBloqueado: false,
    integracoesExternas: [],
    laudosDisponiveis: [
      {
        id: 88,
        titulo: "Caso 88",
        status_card: "aguardando",
        status_card_label: "Aguardando",
        data_iso: "2026-04-13T10:00:00.000Z",
        case_lifecycle_status: "aguardando_mesa" as const,
        active_owner_role: "mesa" as const,
        allowed_lifecycle_transitions: [
          {
            target_status: "em_revisao_mesa" as const,
            transition_kind: "review" as const,
            label: "Mesa em revisão",
            owner_role: "mesa" as const,
            preferred_surface: "mesa" as const,
          },
        ],
        allowed_surface_actions: ["mesa_approve", "mesa_return"],
        official_issue_summary: {
          label: "Reemissão recomendada",
          detail: "PDF emitido divergente · Emitido v0003 · Atual v0004",
          primary_pdf_diverged: true,
          issue_number: "EO-88",
          primary_pdf_storage_version: "v0003",
          current_primary_pdf_storage_version: "v0004",
        },
        report_pack_draft: {
          modeled: true,
          template_label: "NR35 Linha de Vida",
          guided_context: {
            asset_label: "Linha de vida cobertura A",
            location_label: "Bloco 2",
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
            max_conflict_score: 82,
            final_validation_mode: "mesa_required",
            missing_evidence: [],
          },
        },
        permite_reabrir: false,
        permite_edicao: false,
      },
    ],
    notificacoes: [],
    eventosSeguranca: [],
    serializarPayloadExportacao: jest.fn((payload) => JSON.stringify(payload)),
    compartilharTextoExportado: jest.fn().mockResolvedValue(true),
  };
}

describe("exportDataFlow", () => {
  it("inclui resumo canônico dos casos no payload exportado em JSON", async () => {
    const params = criarParams();

    await runExportDataFlow(params);

    const serializarPayloadExportacaoMock =
      params.serializarPayloadExportacao as jest.Mock;
    const serializedPayload =
      serializarPayloadExportacaoMock.mock.calls[0]?.[0];

    expect(serializedPayload.laudos).toEqual([
      expect.objectContaining({
        id: 88,
        titulo: "Caso 88",
        lifecycle: "Aguardando mesa",
        owner: "Mesa avaliadora",
        nextTransitions: "Mesa em revisão",
        allowedActions: "Aprovar no mobile · Devolver no mobile",
        reportPackReadiness: "Pre-laudo em montagem",
        reportPackCoverage: "0/5 blocos",
        reportPackValidationMode: "Mesa obrigatoria",
        reportPackInspectionContext: "Linha de vida cobertura A · Bloco 2",
        reissueRecommended: true,
        governanceStatus: "Reemissão recomendada",
        governanceDetail:
          "PDF emitido divergente · Emitido v0003 · Atual v0004",
        governanceIssueNumber: "EO-88",
      }),
    ]);
    expect(serializedPayload.operationalSummary).toEqual({
      totalCases: 1,
      reissueRecommendedCount: 1,
    });
    expect(serializedPayload.account).toEqual(
      expect.objectContaining({
        workspace: "Empresa A • Mobile principal com operador único",
        access:
          "Empresa #33 • Inspetor web/mobile + Mesa Avaliadora + Admin-Cliente • Mobile principal com operador único",
        identityRuntimeNote:
          "A conta principal do tenant pode receber multiplas superficies conforme o cadastro definido no Admin-CEO.",
        portalContinuationSummary:
          "Inspetor web/mobile (/app/) • Mesa Avaliadora (/revisao/painel) • Admin-Cliente (/cliente/painel)",
      }),
    );
  });

  it("inclui o resumo canônico dos casos no conteúdo TXT", async () => {
    const params = criarParams();
    params.formato = "TXT";

    await runExportDataFlow(params);

    expect(params.compartilharTextoExportado).toHaveBeenCalledWith(
      expect.objectContaining({
        extension: "txt",
        content: expect.stringContaining(
          "Caso 88: Aguardando mesa · Mesa avaliadora · Aprovar no mobile · Devolver no mobile · Pre-laudo em montagem · 0/5 blocos · Mesa obrigatoria · Linha de vida cobertura A · Bloco 2 · Reemissão recomendada · PDF emitido divergente · Emitido v0003 · Atual v0004",
        ),
      }),
    );
    expect(params.compartilharTextoExportado).toHaveBeenCalledWith(
      expect.objectContaining({
        content: expect.stringContaining("Reemissões recomendadas: 1"),
      }),
    );
    expect(params.compartilharTextoExportado).toHaveBeenCalledWith(
      expect.objectContaining({
        content: expect.stringContaining(
          "Acesso: Empresa #33 • Inspetor web/mobile + Mesa Avaliadora + Admin-Cliente • Mobile principal com operador único",
        ),
      }),
    );
    expect(params.compartilharTextoExportado).toHaveBeenCalledWith(
      expect.objectContaining({
        content: expect.stringContaining(
          "Continuidade web: Inspetor web/mobile (/app/) • Mesa Avaliadora (/revisao/painel) • Admin-Cliente (/cliente/painel)",
        ),
      }),
    );
  });
});
