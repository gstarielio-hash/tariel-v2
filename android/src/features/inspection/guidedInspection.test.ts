import {
  advanceGuidedInspectionDraft,
  buildGuidedInspectionMessageContext,
  buildGuidedInspectionPrompt,
  createGuidedInspectionDraft,
  guidedInspectionDraftFromMobilePayload,
  getGuidedInspectionProgress,
  isGuidedInspectionComplete,
  listGuidedInspectionTemplates,
  mergeGuidedInspectionDraftWithRemote,
  resolveGuidedInspectionTemplateKey,
} from "./guidedInspection";

describe("guidedInspection", () => {
  it("cria o rascunho generico como fallback quando o tipo ainda nao foi definido", () => {
    const draft = createGuidedInspectionDraft();

    expect(draft.templateKey).toBe("padrao");
    expect(draft.templateLabel).toBe("Inspecao Geral");
    expect(draft.checklist).toHaveLength(5);
    expect(draft.currentStepIndex).toBe(0);
    expect(buildGuidedInspectionPrompt(draft)).toContain(
      "Etapa 1/5: Identificacao do ativo e da area.",
    );
  });

  it("avanca a etapa atual e move o foco para a proxima", () => {
    const draft = advanceGuidedInspectionDraft(createGuidedInspectionDraft());
    const progress = getGuidedInspectionProgress(draft);

    expect(draft.completedStepIds).toEqual(["identificacao_ativo"]);
    expect(draft.currentStepIndex).toBe(1);
    expect(progress.completedCount).toBe(1);
    expect(progress.currentItem?.id).toBe("contexto_operacao");
  });

  it("fecha o checklist e muda o prompt para consolidacao final", () => {
    let draft = createGuidedInspectionDraft();

    for (let index = 0; index < draft.checklist.length; index += 1) {
      draft = advanceGuidedInspectionDraft(draft);
    }

    expect(isGuidedInspectionComplete(draft)).toBe(true);
    expect(buildGuidedInspectionPrompt(draft)).toContain(
      "Checklist base concluido.",
    );
  });

  it("resolve o template guiado pelo tipo canonicamente normalizado", () => {
    expect(resolveGuidedInspectionTemplateKey("nr35")).toBe("nr35_linha_vida");
    expect(resolveGuidedInspectionTemplateKey("nr12_maquinas")).toBe(
      "nr12maquinas",
    );
    expect(
      resolveGuidedInspectionTemplateKey(
        "nr11_inspecao_movimentacao_armazenagem",
      ),
    ).toBe("nr11_movimentacao");
    expect(resolveGuidedInspectionTemplateKey("nr10_rti")).toBe("rti");
    expect(resolveGuidedInspectionTemplateKey("nr10_loto")).toBe("loto");
    expect(resolveGuidedInspectionTemplateKey("nr10_implantacao_loto")).toBe(
      "loto",
    );
    expect(resolveGuidedInspectionTemplateKey("nr10_inspecao_spda")).toBe(
      "spda",
    );
    expect(
      resolveGuidedInspectionTemplateKey(
        "nr13_calculo_espessura_minima_vaso_pressao",
      ),
    ).toBe("nr13_ultrassom");
    expect(
      resolveGuidedInspectionTemplateKey("nr13_calibracao_valvulas_manometros"),
    ).toBe("nr13_calibracao");
    expect(
      resolveGuidedInspectionTemplateKey("nr35_inspecao_ponto_ancoragem"),
    ).toBe("nr35_ponto_ancoragem");
    expect(
      resolveGuidedInspectionTemplateKey("nr35_montagem_linha_de_vida"),
    ).toBe("nr35_montagem");
    expect(
      resolveGuidedInspectionTemplateKey("nr35_projeto_protecao_queda"),
    ).toBe("nr35_projeto");
    expect(resolveGuidedInspectionTemplateKey("cbmgo_cmar")).toBe("cbmgo");
    expect(resolveGuidedInspectionTemplateKey("")).toBe("padrao");
  });

  it("lista o catalogo guiado expandido preservando os templates legados", () => {
    const templates = listGuidedInspectionTemplates();

    expect(templates).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ key: "rti", label: "NR10 RTI Eletrica" }),
        expect.objectContaining({ key: "loto", label: "NR10 LOTO" }),
        expect.objectContaining({
          key: "nr11_movimentacao",
          label: "NR11 Movimentacao e Armazenagem",
        }),
        expect.objectContaining({
          key: "nr13_teste_hidrostatico",
          label: "NR13 Teste Hidrostatico e Estanqueidade",
        }),
        expect.objectContaining({
          key: "nr35_ponto_ancoragem",
          label: "NR35 Ponto de Ancoragem",
        }),
      ]),
    );
  });

  it("preserva o bundle canonico e a sinalizacao de mesa no round-trip do draft", () => {
    const draft = guidedInspectionDraftFromMobilePayload({
      template_key: "nr35_linha_vida",
      template_label: "NR35 Linha de Vida",
      started_at: "2026-04-06T22:30:00.000Z",
      current_step_index: 1,
      completed_step_ids: ["identificacao_laudo"],
      checklist: [
        {
          id: "identificacao_laudo",
          title: "Identificacao",
          prompt: "registre o ativo",
          evidence_hint: "codigo do ativo",
        },
        {
          id: "contexto_vistoria",
          title: "Contexto da vistoria",
          prompt: "confirme responsaveis",
          evidence_hint: "responsaveis e data",
        },
      ],
      evidence_bundle_kind: "case_thread",
      evidence_refs: [
        {
          message_id: 91,
          step_id: "identificacao_laudo",
          step_title: "Identificacao",
          captured_at: "2026-04-06T22:31:00.000Z",
          evidence_kind: "chat_message",
          attachment_kind: "image",
        },
      ],
      mesa_handoff: {
        required: true,
        review_mode: "mesa_required",
        reason_code: "policy_review_mode",
        recorded_at: "2026-04-06T22:31:30.000Z",
        step_id: "contexto_vistoria",
        step_title: "Contexto da vistoria",
      },
    });

    expect(draft?.evidenceBundleKind).toBe("case_thread");
    expect(draft?.evidenceRefs[0]?.messageId).toBe(91);
    expect(draft?.mesaHandoff?.reviewMode).toBe("mesa_required");
  });

  it("gera o contexto da mensagem guiada a partir da etapa atual", () => {
    const draft = advanceGuidedInspectionDraft(createGuidedInspectionDraft());

    expect(buildGuidedInspectionMessageContext(draft, "document")).toEqual({
      template_key: "padrao",
      step_id: "contexto_operacao",
      step_title: "Contexto da atividade",
      attachment_kind: "document",
    });
  });

  it("mescla o progresso remoto sem perder continuidade offline local", () => {
    const localDraft = advanceGuidedInspectionDraft(
      createGuidedInspectionDraft(),
    );
    const remoteDraft = guidedInspectionDraftFromMobilePayload({
      template_key: "padrao",
      template_label: "Inspecao Geral",
      started_at: "2026-04-06T22:30:00.000Z",
      current_step_index: 2,
      completed_step_ids: ["identificacao_ativo", "contexto_operacao"],
      checklist: createGuidedInspectionDraft().checklist.map((item) => ({
        id: item.id,
        title: item.title,
        prompt: item.prompt,
        evidence_hint: item.evidenceHint,
      })),
      evidence_bundle_kind: "case_thread",
      evidence_refs: [
        {
          message_id: 91,
          step_id: "identificacao_ativo",
          step_title: "Identificacao do ativo e da area",
          captured_at: "2026-04-06T22:31:00.000Z",
          evidence_kind: "chat_message",
          attachment_kind: "image",
        },
        {
          message_id: 92,
          step_id: "contexto_operacao",
          step_title: "Contexto da atividade",
          captured_at: "2026-04-06T22:32:00.000Z",
          evidence_kind: "chat_message",
          attachment_kind: "document",
        },
      ],
      mesa_handoff: null,
    });

    const merged = mergeGuidedInspectionDraftWithRemote(
      localDraft,
      remoteDraft,
    );

    expect(merged?.completedStepIds).toEqual([
      "identificacao_ativo",
      "contexto_operacao",
    ]);
    expect(merged?.currentStepIndex).toBe(2);
    expect(merged?.evidenceRefs).toHaveLength(2);
  });
});
