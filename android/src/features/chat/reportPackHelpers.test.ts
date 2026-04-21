import { buildReportPackDraftSummary } from "./reportPackHelpers";

describe("reportPackHelpers", () => {
  it("resume a prontidao do pre-laudo por blocos", () => {
    const summary = buildReportPackDraftSummary({
      modeled: true,
      template_label: "NR35 Linha de Vida",
      guided_context: {
        asset_label: "Linha de vida cobertura A",
        location_label: "Bloco 2",
        inspection_objective: "Validar ancoragem principal antes da liberacao.",
        checklist_ids: [
          "identificacao_laudo",
          "contexto_vistoria",
          "componentes_inspecionados",
        ],
        completed_step_ids: ["identificacao_laudo", "contexto_vistoria"],
      },
      image_slots: [
        { slot: "vista_geral", status: "resolved" },
        { slot: "ponto_superior", status: "pending" },
      ],
      items: [
        {
          item_codigo: "fixacao",
          titulo: "Fixacao",
          veredito_ia_normativo: "C",
          approved_for_emission: true,
          missing_evidence: [],
        },
        {
          item_codigo: "cabo",
          titulo: "Cabo de aco",
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
        missing_evidence: [
          {
            message: "Ainda faltam evidencias visuais obrigatorias.",
          },
        ],
      },
      evidence_summary: {
        evidence_count: 4,
        image_count: 1,
        text_count: 3,
      },
    });

    expect(summary?.templateLabel).toBe("NR35 Linha de Vida");
    expect(summary?.inspectionContextLabel).toBe(
      "Linha de vida cobertura A · Bloco 2",
    );
    expect(summary?.inspectionContextDetail).toContain(
      "Validar ancoragem principal",
    );
    expect(summary?.finalValidationModeLabel).toBe("Mesa obrigatoria");
    expect(summary?.pendingBlocks).toBeGreaterThan(0);
    expect(summary?.attentionBlocks).toBeGreaterThan(0);
    expect(summary?.highlightedBlocks.map((item) => item.title)).toEqual(
      expect.arrayContaining([
        "Checklist guiado",
        "Fotos obrigatorias",
        "Itens criticos",
      ]),
    );
    expect(summary?.readinessLabel).toBe("Pre-laudo em montagem");
  });

  it("marca autonomia quando todos os blocos estao prontos", () => {
    const summary = buildReportPackDraftSummary({
      modeled: true,
      template_label: "CBMGO",
      guided_context: {
        checklist_ids: ["identificacao", "conclusao"],
        completed_step_ids: ["identificacao", "conclusao"],
      },
      image_slots: [{ slot: "fachada", status: "resolved" }],
      items: [
        {
          item_codigo: "seguranca_estrutural.paredes",
          titulo: "Paredes",
          veredito_ia_normativo: "C",
          approved_for_emission: true,
          missing_evidence: [],
        },
      ],
      structured_data_candidate: { familia: "cbmgo" },
      quality_gates: {
        checklist_complete: true,
        required_image_slots_complete: true,
        critical_items_complete: true,
        autonomy_ready: true,
        requires_normative_curation: false,
        max_conflict_score: 12,
        final_validation_mode: "mobile_autonomous",
        missing_evidence: [],
      },
      evidence_summary: {
        evidence_count: 6,
        image_count: 1,
        text_count: 5,
      },
    });

    expect(summary?.autonomyReady).toBe(true);
    expect(summary?.readinessLabel).toBe("Pronto para validar");
    expect(summary?.pendingBlocks).toBe(0);
    expect(summary?.attentionBlocks).toBe(0);
  });

  it("aproveita o pre-laudo canonico vindo do catalogo admin para o mobile", () => {
    const summary = buildReportPackDraftSummary({
      modeled: true,
      template_label: "NR35 Linha de Vida",
      quality_gates: {
        autonomy_ready: false,
        final_validation_mode: "mesa_required",
        max_conflict_score: 18,
        missing_evidence: [],
      },
      pre_laudo_outline: {
        ready_for_structured_form: true,
        next_questions: [
          "Envie a foto obrigatoria de ponto superior.",
          "Confirme a conclusao final do caso.",
        ],
      },
      pre_laudo_document: {
        family_key: "nr35_inspecao_linha_de_vida",
        family_label: "NR35 Linha de Vida",
        template_key: "nr35",
        minimum_evidence: {
          fotos: 3,
          documentos: 1,
          textos: 1,
        },
        document_flow: [
          { title: "Base da família", status: "ready" },
          { title: "Modelo base", status: "ready" },
          { title: "Documento base", status: "ready" },
          { title: "Exemplo de documento", status: "pending" },
        ],
        document_sections: [
          {
            section_key: "identificacao",
            title: "Identificacao",
            status: "ready",
            filled_field_count: 6,
            total_field_count: 6,
            summary: "6/6 campos preenchidos.",
          },
          {
            section_key: "conclusao",
            title: "Conclusao",
            status: "attention",
            filled_field_count: 2,
            total_field_count: 5,
            summary: "2/5 campos preenchidos; revisão parcial.",
          },
        ],
        required_slots: [
          {
            slot_id: "foto_ponto_superior",
            label: "Foto do ponto superior",
            required: true,
            accepted_types: ["image/jpeg"],
            binding_path: "registros_fotograficos.ponto_superior",
            purpose: "Registrar o ponto superior.",
          },
        ],
        analysis_basis_summary: {
          coverage_summary: "2 de 3 fotos obrigatórias vinculadas.",
        },
        next_questions: [
          "Envie a foto obrigatoria de ponto superior.",
          "Confirme a conclusao final do caso.",
        ],
        review_required: ["Mesa valida a emissão final."],
        example_available: true,
      },
    });

    expect(summary?.familyKey).toBe("nr35_inspecao_linha_de_vida");
    expect(summary?.familyLabel).toBe("NR35 Linha de Vida");
    expect(summary?.minimumEvidence.fotos).toBe(3);
    expect(summary?.readyForStructuredForm).toBe(true);
    expect(summary?.blockSummaries.map((item) => item.title)).toEqual(
      expect.arrayContaining(["Fluxo do documento", "Conclusao"]),
    );
    expect(summary?.requiredEvidenceSlots[0]).toMatchObject({
      label: "Foto do ponto superior",
      bindingPath: "registros_fotograficos.ponto_superior",
    });
    expect(summary?.analysisBasisSummary.coverage_summary).toBe(
      "2 de 3 fotos obrigatórias vinculadas.",
    );
    expect(summary?.reviewRequired).toEqual(["Mesa valida a emissão final."]);
    expect(summary?.exampleAvailable).toBe(true);
    expect(summary?.nextQuestions).toEqual([
      "Envie a foto obrigatoria de ponto superior.",
      "Confirme a conclusao final do caso.",
    ]);
  });
});
