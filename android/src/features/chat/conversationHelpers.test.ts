import {
  atualizarResumoLaudoAtual,
  chaveCacheLaudo,
  chaveRascunho,
  criarConversaNova,
  criarMensagemAssistenteServidor,
  inferirSetorConversa,
  montarHistoricoParaEnvio,
  normalizarComposerAttachment,
  normalizarConversa,
  normalizarMensagemChat,
  normalizarModoChat,
  podeEditarConversaNoComposer,
  previewChatLiberadoParaConversa,
  sanitizarTextoMensagemChat,
  textoFallbackAnexo,
} from "./conversationHelpers";

describe("conversationHelpers", () => {
  it("normaliza modos e cria chave de rascunho", () => {
    expect(normalizarModoChat("deepResearch")).toBe("deep_research");
    expect(normalizarModoChat("curto")).toBe("curto");
    expect(normalizarModoChat("desconhecido", "curto")).toBe("curto");
    expect(chaveCacheLaudo(17)).toBe("laudo:17");
    expect(chaveRascunho("mesa", 17)).toBe("mesa:laudo:17");
  });

  it("normaliza anexos e fallback textual", () => {
    const anexo = normalizarComposerAttachment({
      kind: "document",
      label: "Laudo",
      nomeDocumento: "laudo.pdf",
      fileUri: "file://laudo.pdf",
    });

    expect(anexo).toEqual({
      kind: "document",
      label: "Laudo",
      resumo: "",
      textoDocumento: "",
      nomeDocumento: "laudo.pdf",
      chars: 0,
      truncado: false,
      fileUri: "file://laudo.pdf",
      mimeType: "application/octet-stream",
    });
    expect(textoFallbackAnexo(anexo)).toBe("Documento: laudo.pdf");
    expect(normalizarComposerAttachment({ kind: "image" })).toBeNull();
  });

  it("normaliza conversa e resumo do laudo atual", () => {
    const conversa = normalizarConversa({
      laudo_id: 23,
      estado: "em_andamento",
      status_card: "aguardando_revisao",
      permite_edicao: false,
      permite_reabrir: true,
      case_lifecycle_status: "aguardando_mesa",
      case_workflow_mode: "laudo_com_mesa",
      active_owner_role: "mesa",
      allowed_next_lifecycle_statuses: [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
      ],
      allowed_lifecycle_transitions: [
        {
          target_status: "em_revisao_mesa",
          transition_kind: "review",
          label: "Mesa em revisão",
          owner_role: "mesa",
          preferred_surface: "mesa",
        },
        {
          target_status: "aprovado",
          transition_kind: "approval",
          label: "Aprovado",
          owner_role: "none",
          preferred_surface: "mobile",
        },
      ],
      allowed_surface_actions: ["mesa_approve", "mesa_return"],
      attachment_policy: {
        policy_name: "android_attachment_sync_policy",
        upload_allowed: true,
        download_allowed: true,
        inline_preview_allowed: true,
        supported_categories: ["imagem", "documento"],
        supported_mime_types: ["image/png", "application/pdf"],
      },
      laudo_card: {
        id: 23,
        titulo: "Laudo 23",
        status_card: "aguardando_revisao",
        status_card_label: "Aguardando revisao",
        status_revisao: "pendente",
        permite_reabrir: true,
        permite_edicao: false,
        data_iso: "2026-03-30T10:00:00.000Z",
        case_lifecycle_status: "aguardando_mesa",
        case_workflow_mode: "laudo_com_mesa",
        active_owner_role: "mesa",
        allowed_next_lifecycle_statuses: [
          "em_revisao_mesa",
          "devolvido_para_correcao",
          "aprovado",
        ],
        allowed_lifecycle_transitions: [
          {
            target_status: "em_revisao_mesa",
            transition_kind: "review",
            label: "Mesa em revisão",
            owner_role: "mesa",
            preferred_surface: "mesa",
          },
          {
            target_status: "aprovado",
            transition_kind: "approval",
            label: "Aprovado",
            owner_role: "none",
            preferred_surface: "mobile",
          },
        ],
        allowed_surface_actions: ["mesa_approve", "mesa_return"],
      },
      review_package: {
        review_mode: "mesa_required",
        coverage_map: { total_required: 4, total_accepted: 2 },
      },
      report_pack_draft: {
        template_label: "NR35 Linha de Vida",
        quality_gates: {
          final_validation_mode: "mesa_required",
          checklist_complete: false,
        },
      },
      modo: "",
      itens: [
        {
          id: 1,
          papel: "assistente",
          texto: "Resposta",
          tipo: "assistant",
          modo: "curto",
        },
      ],
    } as any);

    expect(conversa.modo).toBe("curto");
    expect(conversa.reviewPackage?.review_mode).toBe("mesa_required");
    expect(conversa.caseLifecycleStatus).toBe("aguardando_mesa");
    expect(conversa.caseWorkflowMode).toBe("laudo_com_mesa");
    expect(conversa.activeOwnerRole).toBe("mesa");
    expect(conversa.allowedNextLifecycleStatuses).toEqual([
      "em_revisao_mesa",
      "devolvido_para_correcao",
      "aprovado",
    ]);
    expect(
      conversa.allowedLifecycleTransitions?.map((item) => item.target_status),
    ).toEqual(["em_revisao_mesa", "aprovado"]);
    expect(conversa.allowedSurfaceActions).toEqual([
      "mesa_approve",
      "mesa_return",
    ]);
    expect(conversa.attachmentPolicy?.supported_categories).toEqual([
      "imagem",
      "documento",
    ]);
    expect((conversa.reportPackDraft as any)?.template_label).toBe(
      "NR35 Linha de Vida",
    );

    const atualizado = atualizarResumoLaudoAtual(conversa, {
      estado: "aprovado",
      permite_edicao: true,
      permite_reabrir: false,
      case_lifecycle_status: "emitido",
      case_workflow_mode: "laudo_guiado",
      active_owner_role: "none",
      allowed_next_lifecycle_statuses: ["devolvido_para_correcao"],
      allowed_lifecycle_transitions: [
        {
          target_status: "devolvido_para_correcao",
          transition_kind: "reopen",
          label: "Devolvido para correção",
          owner_role: "inspetor",
          preferred_surface: "chat",
        },
      ],
      allowed_surface_actions: ["chat_reopen"],
      laudo_card: {
        id: 23,
        titulo: "Laudo 23",
        status_card: "finalizado",
        status_card_label: "Finalizado",
        status_revisao: "aprovado",
        permite_reabrir: false,
        permite_edicao: true,
        data_iso: "2026-03-30T10:00:00.000Z",
        case_lifecycle_status: "emitido",
        case_workflow_mode: "laudo_guiado",
        active_owner_role: "none",
        allowed_next_lifecycle_statuses: ["devolvido_para_correcao"],
        allowed_lifecycle_transitions: [
          {
            target_status: "devolvido_para_correcao",
            transition_kind: "reopen",
            label: "Devolvido para correção",
            owner_role: "inspetor",
            preferred_surface: "chat",
          },
        ],
        allowed_surface_actions: ["chat_reopen"],
      } as any,
      attachment_policy: {
        policy_name: "android_attachment_sync_policy",
        upload_allowed: true,
        download_allowed: true,
        inline_preview_allowed: true,
        supported_categories: ["imagem"],
        supported_mime_types: ["image/png"],
      },
      review_package: {
        review_mode: "mobile_review_allowed",
        coverage_map: { total_required: 4, total_accepted: 4 },
      },
      report_pack_draft: {
        template_label: "NR35 Linha de Vida",
        quality_gates: {
          final_validation_mode: "mobile_autonomous",
          checklist_complete: true,
        },
      },
      modo: "detalhado",
    });

    expect(atualizado?.estado).toBe("aprovado");
    expect(atualizado?.statusCard).toBe("finalizado");
    expect(atualizado?.permiteEdicao).toBe(true);
    expect(atualizado?.caseLifecycleStatus).toBe("emitido");
    expect(atualizado?.caseWorkflowMode).toBe("laudo_guiado");
    expect(atualizado?.activeOwnerRole).toBe("none");
    expect(atualizado?.allowedNextLifecycleStatuses).toEqual([
      "devolvido_para_correcao",
    ]);
    expect(
      atualizado?.allowedLifecycleTransitions?.map(
        (item) => item.target_status,
      ),
    ).toEqual(["devolvido_para_correcao"]);
    expect(atualizado?.allowedSurfaceActions).toEqual(["chat_reopen"]);
    expect(atualizado?.attachmentPolicy?.supported_categories).toEqual([
      "imagem",
    ]);
    expect(atualizado?.reviewPackage?.review_mode).toBe(
      "mobile_review_allowed",
    );
    expect((atualizado?.reportPackDraft as any)?.quality_gates).toEqual({
      final_validation_mode: "mobile_autonomous",
      checklist_complete: true,
    });
  });

  it("monta historico util e mensagem do assistente", () => {
    expect(
      sanitizarTextoMensagemChat(
        "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]",
        {
          papel: "usuario",
        },
      ),
    ).toBe("Evidência enviada");
    expect(
      normalizarMensagemChat({
        id: 10,
        papel: "usuario",
        texto:
          "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]\n\nPergunta",
        tipo: "user",
        anexos: [
          {
            id: 7,
            nome: "relatorio.pdf",
            mime_type: "application/pdf",
            categoria: "documento",
            eh_imagem: false,
            url: "/revisao/api/laudo/77/mesa/anexos/7",
          },
        ],
      } as any),
    ).toMatchObject({
      texto: "Pergunta",
      anexos: [
        expect.objectContaining({
          url: "/app/api/laudo/77/mesa/anexos/7",
        }),
      ],
    });

    const mensagens = [
      { papel: "sistema", texto: "ignorar" },
      { papel: "usuario", texto: "  pergunta  " },
      { papel: "assistente", texto: " resposta " },
      {
        papel: "usuario",
        texto:
          "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]",
      },
      { papel: "assistente", texto: " " },
    ] as any;

    expect(montarHistoricoParaEnvio(mensagens)).toEqual([
      { papel: "usuario", texto: "pergunta" },
      { papel: "assistente", texto: "resposta" },
      { papel: "usuario", texto: "Evidência enviada" },
    ]);

    expect(
      sanitizarTextoMensagemChat(
        "[Erro] 400 INVALIDARGUMENT: {'error': {'code': 400, 'message': 'API key expired. Please renew the API key.', 'status': 'INVALIDARGUMENT', 'details': [{'@type': 'type.googleapis.com/google.rpc.ErrorInfo', 'reason': 'API_KEY_INVALID'}]}}",
        {
          papel: "assistente",
        },
      ),
    ).toBe(
      "A IA está temporariamente indisponível neste ambiente. Tente novamente em instantes.",
    );

    const nowSpy = jest.spyOn(Date, "now").mockReturnValue(100);
    expect(
      criarMensagemAssistenteServidor({
        assistantText: " ok ",
        modo: "curto",
        citacoes: ["A"],
        confiancaIa: 0.8,
        events: [
          {
            anexos: [
              {
                id: 9,
                nome: "relatorio_chat_livre_77.pdf",
                mime_type: "application/pdf",
                categoria: "documento",
                eh_imagem: false,
                url: "/revisao/api/laudo/77/mesa/anexos/9",
              },
            ],
          },
        ],
      } as any),
    ).toEqual({
      id: 101,
      papel: "assistente",
      texto: "ok",
      tipo: "assistant",
      modo: "curto",
      anexos: [
        {
          id: 9,
          nome: "relatorio_chat_livre_77.pdf",
          mime_type: "application/pdf",
          categoria: "documento",
          eh_imagem: false,
          url: "/app/api/laudo/77/mesa/anexos/9",
        },
      ],
      citacoes: ["A"],
      confianca_ia: 0.8,
    });
    expect(
      criarMensagemAssistenteServidor({
        assistantText:
          "[Erro] 400 INVALIDARGUMENT: {'error': {'message': 'API key expired. Please renew the API key.', 'details': [{'@type': 'type.googleapis.com/google.rpc.ErrorInfo'}]}}",
        modo: "curto",
        citacoes: [],
        confiancaIa: null,
        events: [],
      } as any),
    ).toEqual({
      id: 101,
      papel: "assistente",
      texto:
        "A IA está temporariamente indisponível neste ambiente. Tente novamente em instantes.",
      tipo: "assistant",
      modo: "curto",
      anexos: undefined,
      citacoes: undefined,
      confianca_ia: undefined,
    });
    nowSpy.mockRestore();
  });

  it("controla preview e edicao da conversa", () => {
    const nova = criarConversaNova();
    expect(previewChatLiberadoParaConversa(nova)).toBe(true);
    expect(podeEditarConversaNoComposer(nova)).toBe(true);

    const bloqueada = {
      ...nova,
      laudoId: 44,
      permiteEdicao: false,
      mensagens: [{ id: 1, papel: "assistente", texto: "msg" }],
      laudoCard: { tipo_template: "nr12" },
    } as any;

    expect(previewChatLiberadoParaConversa(bloqueada)).toBe(false);
    expect(podeEditarConversaNoComposer(bloqueada)).toBe(false);
    expect(inferirSetorConversa(bloqueada)).toBe("nr12");
  });

  it("infere o setor a partir dos novos templates guiados", () => {
    expect(
      inferirSetorConversa({
        laudoCard: { tipo_template: "nr11_movimentacao" },
      } as any),
    ).toBe("nr11");
    expect(
      inferirSetorConversa({
        laudoCard: { tipo_template: "nr13_ultrassom" },
      } as any),
    ).toBe("nr13");
    expect(
      inferirSetorConversa({
        laudoCard: { tipo_template: "nr20_instalacoes" },
      } as any),
    ).toBe("nr20");
    expect(
      inferirSetorConversa({
        laudoCard: { tipo_template: "nr33_espaco_confinado" },
      } as any),
    ).toBe("nr33");
    expect(
      inferirSetorConversa({
        laudoCard: { tipo_template: "nr35_ponto_ancoragem" },
      } as any),
    ).toBe("nr35");
  });
});
