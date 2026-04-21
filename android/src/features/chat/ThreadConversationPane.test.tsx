import { fireEvent, render } from "@testing-library/react-native";

import { ThreadConversationPane } from "./ThreadConversationPane";

jest.mock("@expo/vector-icons", () => {
  const React = require("react");
  const { Text } = require("react-native");
  return {
    MaterialCommunityIcons: ({
      name,
      ...props
    }: {
      name: string;
      [key: string]: unknown;
    }) => React.createElement(Text, props, name),
  };
});

const baseProps = {
  accentColor: "#0f172a",
  anexoAbrindoChave: "",
  brandMarkSource: { uri: "test://brand" },
  carregandoConversa: false,
  carregandoMesa: false,
  conversaPermiteEdicao: false,
  conversaVazia: false,
  dynamicMessageBubbleStyle: null,
  dynamicMessageTextStyle: null,
  enviandoMensagem: false,
  keyboardVisible: false,
  mesaAcessoPermitido: true,
  mesaDisponivel: true,
  mesaIndisponivelDescricao:
    "Envie o primeiro registro no chat para liberar este espaço.",
  mesaIndisponivelTitulo: "Mesa disponível após o primeiro laudo",
  mensagemChatDestacadaId: null,
  mensagensMesa: [],
  mensagensVisiveis: [],
  nomeUsuarioExibicao: "Inspetor Demo",
  obterResumoReferenciaMensagem: () => "",
  onAbrirAnexo: jest.fn(),
  onAbrirReferenciaNoChat: jest.fn(),
  onDefinirReferenciaMesaAtiva: jest.fn(),
  onRegistrarLayoutMensagemChat: jest.fn(),
  reportPackDraft: null,
  reviewPackage: null,
  scrollRef: { current: null },
  sessionAccessToken: null,
  threadKeyboardPaddingBottom: 0,
  toAttachmentKey: () => "",
  vendoMesa: true,
};

describe("ThreadConversationPane", () => {
  it("expõe marker estável quando a conta não tem acesso à mesa", () => {
    const { getByTestId, getByText } = render(
      <ThreadConversationPane
        {...baseProps}
        mesaAcessoPermitido={false}
        mesaIndisponivelDescricao="O pacote atual não inclui a mesa no app."
        mesaIndisponivelTitulo="Mesa indisponível para esta conta"
      />,
    );

    expect(getByTestId("mesa-thread-surface")).toBeTruthy();
    expect(getByTestId("mesa-thread-blocked")).toBeTruthy();
    expect(getByText("Mesa indisponível para esta conta")).toBeTruthy();
  });

  it("expõe marker estável da superfície Mesa vazia", () => {
    const { getByTestId } = render(<ThreadConversationPane {...baseProps} />);

    expect(getByTestId("mesa-thread-surface")).toBeTruthy();
    expect(getByTestId("mesa-thread-empty-state")).toBeTruthy();
  });

  it("expõe marker estável da superfície Mesa carregada", () => {
    const { getByTestId } = render(
      <ThreadConversationPane
        {...baseProps}
        conversaPermiteEdicao
        mensagensMesa={[
          {
            anexos: [],
            data: "agora",
            id: 1,
            laudo_id: 80,
            lida: true,
            referencia_mensagem_id: null,
            remetente_id: 7,
            resolvida_em: "",
            resolvida_em_label: "",
            resolvida_por_nome: "",
            texto: "Retorno técnico",
            tipo: "humano_eng",
          },
        ]}
      />,
    );

    expect(getByTestId("mesa-thread-surface")).toBeTruthy();
    expect(getByTestId("mesa-thread-loaded")).toBeTruthy();
  });

  it("renderiza o card de revisão operacional quando o pacote está disponível", () => {
    const { getAllByText, getByTestId, getByText } = render(
      <ThreadConversationPane
        {...baseProps}
        activeOwnerRole="mesa"
        allowedNextLifecycleStatuses={["devolvido_para_correcao", "aprovado"]}
        allowedLifecycleTransitions={[
          {
            target_status: "devolvido_para_correcao",
            transition_kind: "correction",
            label: "Devolvido para correção",
            owner_role: "inspetor",
            preferred_surface: "chat",
          },
          {
            target_status: "aprovado",
            transition_kind: "approval",
            label: "Aprovado",
            owner_role: "none",
            preferred_surface: "mobile",
          },
        ]}
        allowedSurfaceActions={["mesa_approve", "mesa_return"]}
        caseLifecycleStatus="em_revisao_mesa"
        reviewPackage={{
          review_mode: "mesa_required",
          review_required: true,
          document_blockers: [{ code: "pending_review" }],
          coverage_map: {
            total_required: 5,
            total_accepted: 3,
            total_missing: 1,
            total_irregular: 1,
          },
          revisao_por_bloco: {
            attention_blocks: 1,
            returned_blocks: 1,
            items: [
              {
                block_key: "identificacao",
                title: "Identificação",
                review_status: "returned",
                recommended_action: "Revisar a foto da placa.",
              },
            ],
          },
          historico_refazer_inspetor: [{ id: 1 }],
          memoria_operacional_familia: {
            approved_snapshot_count: 12,
          },
          red_flags: [
            {
              code: "missing_required_evidence",
              title: "Evidência obrigatória pendente",
              message: "Ainda existem evidências obrigatórias faltantes.",
            },
          ],
          tenant_entitlements: {
            mobile_review_allowed: false,
          },
          inspection_history: {
            source_codigo_hash: "prev001",
            matched_by: "asset_identity",
            diff: {
              summary: "2 mudancas",
              block_highlights: [
                {
                  title: "Identificação",
                  total_changes: 2,
                  summary: "2 alterado(s)",
                  fields: [
                    {
                      label: "Identificação / Tag",
                      change_type: "changed",
                      previous_value: "TAG-001",
                      current_value: "TAG-002",
                    },
                  ],
                },
              ],
              identity_highlights: [
                {
                  label: "Identificação / Tag",
                  change_type: "changed",
                  previous_value: "TAG-001",
                  current_value: "TAG-002",
                },
              ],
              highlights: [
                {
                  label: "Identificação / Tag",
                  change_type: "changed",
                  previous_value: "TAG-001",
                  current_value: "TAG-002",
                },
              ],
            },
          },
          human_override_summary: {
            count: 1,
            latest: {
              actor_name: "Inspetor Demo",
              applied_at: "2026-04-13T18:00:00+00:00",
              reason:
                "Inspeção seguiu com base na validação humana e nas evidências textuais rastreáveis.",
            },
          },
          public_verification: {
            verification_url: "/app/public/laudo/verificar/hash001",
            qr_image_data_uri: "data:image/png;base64,ZmFrZQ==",
          },
          anexo_pack: {
            total_items: 4,
            total_present: 4,
            missing_items: [],
          },
          emissao_oficial: {
            issue_status_label: "Pronto para emissão oficial",
            eligible_signatory_count: 1,
            signature_status_label: "Signatário governado pronto",
            reissue_recommended: true,
            current_issue: {
              issue_number: "TAR-20260410-000123",
              issue_state_label: "Emitido",
              issued_at: "2026-04-10T13:40:00+00:00",
              primary_pdf_diverged: true,
              primary_pdf_storage_version: "v0003",
              current_primary_pdf_storage_version: "v0004",
            },
            blockers: [],
            audit_trail: [
              {
                title: "Aprovação governada",
                status_label: "Pronto",
                summary: "A Mesa confirmou o laudo para emissão oficial.",
              },
            ],
          },
          allowed_decisions: ["enviar_para_mesa", "devolver_no_mobile"],
          supports_block_reopen: true,
        }}
      />,
    );

    expect(getByTestId("mesa-review-package-card")).toBeTruthy();
    expect(getByTestId("mesa-review-verification-qr")).toBeTruthy();
    expect(getByText("Mesa obrigatória")).toBeTruthy();
    expect(getByText("Mesa em revisão")).toBeTruthy();
    expect(getByText("Mesa avaliadora")).toBeTruthy();
    expect(
      getByText("Próximas transições: Devolvido para correção · Aprovado"),
    ).toBeTruthy();
    expect(
      getByText("Ações canônicas: Aprovar no mobile · Devolver no mobile"),
    ).toBeTruthy();
    expect(getAllByText("Revisar a foto da placa.").length).toBeGreaterThan(0);
    expect(getByText("Evidência obrigatória pendente")).toBeTruthy();
    expect(getByText("Foco da decisão")).toBeTruthy();
    expect(getByText("Sinalização: missing_required_evidence")).toBeTruthy();
    expect(getByText("Emissão oficial")).toBeTruthy();
    expect(getByText("Pronto para emissão oficial")).toBeTruthy();
    expect(
      getByText("TAR-20260410-000123 · Emitido · 2026-04-10T13:40:00+00:00"),
    ).toBeTruthy();
    expect(getByText("PDF emitido divergente")).toBeTruthy();
    expect(
      getByText(
        "O PDF atual do caso divergiu do documento congelado na emissão oficial. Emitido v0003 · Atual v0004.",
      ),
    ).toBeTruthy();
    expect(getByText("Aprovação governada")).toBeTruthy();
    expect(getByText("Diff entre emissões")).toBeTruthy();
    expect(getAllByText("Identificação").length).toBeGreaterThan(0);
    expect(getByText("Identificação / Tag")).toBeTruthy();
    expect(getByText("Antes: TAG-001")).toBeTruthy();
    expect(getByText("Agora: TAG-002")).toBeTruthy();
    expect(
      getByText(
        "Override humano interno por Inspetor Demo em 2026-04-13T18:00:00+00:00: Inspeção seguiu com base na validação humana e nas evidências textuais rastreáveis.",
      ),
    ).toBeTruthy();
  });

  it("oculta ação de aprovação quando a ação canônica não inclui mesa_approve", () => {
    const { queryByTestId } = render(
      <ThreadConversationPane
        {...baseProps}
        activeOwnerRole="mesa"
        allowedSurfaceActions={["mesa_return"]}
        caseLifecycleStatus="em_revisao_mesa"
        reviewPackage={{
          review_mode: "mesa_required",
          allowed_decisions: ["aprovar_no_mobile", "devolver_no_mobile"],
        }}
      />,
    );

    expect(queryByTestId("mesa-review-action-approve")).toBeNull();
    expect(queryByTestId("mesa-review-action-return")).toBeTruthy();
  });

  it("aciona comandos de revisão mobile a partir do card operacional", () => {
    const onExecutarComandoRevisaoMobile = jest
      .fn()
      .mockResolvedValue(undefined);
    const { getByTestId } = render(
      <ThreadConversationPane
        {...baseProps}
        onExecutarComandoRevisaoMobile={onExecutarComandoRevisaoMobile}
        reviewPackage={{
          review_mode: "mobile_review_allowed",
          review_required: false,
          document_blockers: [],
          coverage_map: {
            total_required: 3,
            total_accepted: 2,
            total_missing: 1,
            total_irregular: 0,
          },
          revisao_por_bloco: {
            attention_blocks: 1,
            returned_blocks: 0,
            items: [
              {
                block_key: "identificacao",
                title: "Identificação",
                review_status: "attention",
                recommended_action: "Revalidar a identificação técnica.",
              },
            ],
          },
          historico_refazer_inspetor: [],
          memoria_operacional_familia: {
            approved_snapshot_count: 8,
          },
          red_flags: [],
          tenant_entitlements: {
            mobile_review_allowed: true,
            mobile_autonomous_allowed: false,
          },
          allowed_decisions: [
            "aprovar_no_mobile",
            "enviar_para_mesa",
            "devolver_no_mobile",
          ],
          supports_block_reopen: true,
        }}
      />,
    );

    fireEvent.press(getByTestId("mesa-review-action-approve"));
    fireEvent.press(getByTestId("mesa-review-action-send"));
    fireEvent.press(getByTestId("mesa-review-action-return"));
    fireEvent.press(getByTestId("mesa-review-reopen-block-identificacao"));

    expect(onExecutarComandoRevisaoMobile).toHaveBeenNthCalledWith(1, {
      command: "aprovar_no_mobile",
    });
    expect(onExecutarComandoRevisaoMobile).toHaveBeenNthCalledWith(2, {
      command: "enviar_para_mesa",
    });
    expect(onExecutarComandoRevisaoMobile).toHaveBeenNthCalledWith(3, {
      command: "devolver_no_mobile",
      block_key: "identificacao",
      title: "Identificação",
      reason: "Revalidar a identificação técnica.",
      summary:
        "A revisão mobile devolveu o bloco Identificação para ajuste antes da conclusão.",
      required_action: "Revalidar a identificação técnica.",
      failure_reasons: [],
    });
    expect(onExecutarComandoRevisaoMobile).toHaveBeenNthCalledWith(4, {
      command: "reabrir_bloco",
      block_key: "identificacao",
      title: "Identificação",
      reason: "Revalidar a identificação técnica.",
      summary: "Revalidar a identificação técnica.",
    });
  });

  it("inclui red flags no payload de devolução quando a revisão já sinaliza divergências", () => {
    const onExecutarComandoRevisaoMobile = jest
      .fn()
      .mockResolvedValue(undefined);
    const { getByTestId } = render(
      <ThreadConversationPane
        {...baseProps}
        onExecutarComandoRevisaoMobile={onExecutarComandoRevisaoMobile}
        reviewPackage={{
          review_mode: "mesa_required",
          allowed_decisions: ["devolver_no_mobile"],
          red_flags: [
            {
              code: "nr_divergence",
              title: "Divergência com NR",
              message: "O texto proposto não bate com a base normativa.",
            },
          ],
          revisao_por_bloco: {
            attention_blocks: 1,
            returned_blocks: 0,
            items: [
              {
                block_key: "normas",
                title: "Normas aplicáveis",
                review_status: "attention",
                recommended_action:
                  "Revisar a base normativa antes de concluir.",
              },
            ],
          },
        }}
      />,
    );

    fireEvent.press(getByTestId("mesa-review-action-return"));

    expect(onExecutarComandoRevisaoMobile).toHaveBeenCalledWith({
      command: "devolver_no_mobile",
      block_key: "normas",
      title: "Normas aplicáveis",
      reason: "Revisar a base normativa antes de concluir.",
      summary:
        "A revisão mobile devolveu o bloco Normas aplicáveis para ajuste antes da conclusão.",
      required_action: "Revisar a base normativa antes de concluir.",
      failure_reasons: ["nr_divergence", "Divergência com NR"],
    });
  });

  it("renderiza o pre-laudo canônico dentro da thread do chat com ações operacionais", () => {
    const onAbrirMesaTab = jest.fn();
    const onAbrirQualityGate = jest.fn();
    const onUsarPerguntaPreLaudo = jest.fn();
    const { getByTestId, getByText } = render(
      <ThreadConversationPane
        {...baseProps}
        allowedSurfaceActions={["chat_finalize"]}
        caseLifecycleStatus="laudo_em_coleta"
        onAbrirMesaTab={onAbrirMesaTab}
        onAbrirQualityGate={onAbrirQualityGate}
        onUsarPerguntaPreLaudo={onUsarPerguntaPreLaudo}
        vendoMesa={false}
        conversaVazia={false}
        mensagensVisiveis={[
          {
            id: 1,
            papel: "assistente",
            texto: "Pré-laudo em consolidação.",
            tipo: "assistant",
            citacoes: [],
          },
        ]}
        reportPackDraft={{
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
            max_conflict_score: 82,
            final_validation_mode: "mesa_required",
            missing_evidence: [
              {
                message: "Ainda faltam evidencias visuais obrigatorias.",
              },
            ],
          },
          pre_laudo_outline: {
            ready_for_structured_form: true,
            ready_for_finalization: false,
            next_questions: [
              "Confirme a conclusão técnica da ancoragem principal.",
            ],
          },
          pre_laudo_document: {
            family_key: "nr35_inspecao_linha_de_vida",
            family_label: "NR35 Linha de Vida",
            template_key: "nr35",
            template_label: "NR35 Linha de Vida",
            minimum_evidence: {
              fotos: 2,
              documentos: 1,
              textos: 1,
            },
            document_flow: [
              {
                key: "family_schema",
                title: "Base da família",
                status: "ready",
                status_label: "Pronto",
                summary: "Base pronta no catálogo.",
              },
            ],
            executive_sections: [
              {
                key: "conclusao_e_emissao",
                title: "Conclusão e emissão",
                status: "attention",
                summary: "Ainda existem pendências antes da finalização.",
                bullets: [
                  "Conclusão técnica precisa estar fechada para emissão.",
                ],
              },
            ],
            document_sections: [
              {
                section_key: "conclusao",
                title: "Conclusão",
                status: "attention",
                status_label: "Em andamento",
                summary: "2/5 campos preenchidos; revisão parcial.",
                filled_field_count: 2,
                missing_field_count: 3,
                total_field_count: 5,
                highlights: [
                  {
                    path: "conclusao.resultado",
                    label: "Conclusão / Resultado",
                  },
                ],
              },
            ],
            highlighted_sections: [
              {
                section_key: "conclusao",
                title: "Conclusão",
                status: "attention",
                status_label: "Em andamento",
                summary: "2/5 campos preenchidos; revisão parcial.",
                filled_field_count: 2,
                missing_field_count: 3,
                total_field_count: 5,
                highlights: [
                  {
                    path: "conclusao.resultado",
                    label: "Conclusão / Resultado",
                  },
                ],
              },
            ],
            required_slots: [
              {
                slot_id: "foto_ponto_superior",
                label: "Foto do ponto superior",
                required: true,
                accepted_types: ["image/jpeg"],
                binding_path: "registros_fotograficos.ponto_superior",
                purpose: "Registrar o ponto superior com contexto técnico.",
              },
            ],
            review_required: ["Revisão humana obrigatória para emissão."],
            next_questions: [
              "Confirme a conclusão técnica da ancoragem principal.",
            ],
            analysis_basis_summary: {
              coverage_summary: "1 de 2 fotos obrigatórias vinculadas.",
              photo_summary:
                "Existe foto geral, falta close do ponto superior.",
              context_summary:
                "Ativo identificado como Linha de vida cobertura A.",
            },
            example_available: true,
          },
          evidence_summary: {
            evidence_count: 4,
            image_count: 1,
            text_count: 3,
          },
        }}
      />,
    );

    expect(getByTestId("chat-report-pack-card")).toBeTruthy();
    expect(getByText("pré-laudo canônico")).toBeTruthy();
    expect(getByText("Rota canônica")).toBeTruthy();
    expect(getByText("Seções do documento")).toBeTruthy();
    expect(getByText("Slots de evidência")).toBeTruthy();
    expect(getByText("Validar e finalizar")).toBeTruthy();
    expect(getByText("Abrir Mesa")).toBeTruthy();

    fireEvent.press(getByTestId("chat-report-pack-card-next-question-0"));
    fireEvent.press(getByTestId("chat-report-pack-card-open-quality-gate"));
    fireEvent.press(getByTestId("chat-report-pack-card-open-mesa"));

    expect(onUsarPerguntaPreLaudo).toHaveBeenCalledWith(
      "Confirme a conclusão técnica da ancoragem principal.",
    );
    expect(onAbrirQualityGate).toHaveBeenCalled();
    expect(onAbrirMesaTab).toHaveBeenCalled();
  });

  it("destaca o documento emitido na thread quando o caso já tem emissão oficial", () => {
    const { getByTestId, getByText } = render(
      <ThreadConversationPane
        {...baseProps}
        vendoMesa={false}
        conversaVazia={false}
        caseLifecycleStatus="emitido"
        mensagensVisiveis={[
          {
            id: 1,
            papel: "assistente",
            texto: "Documento emitido.",
            tipo: "assistant",
            citacoes: [],
          },
        ]}
        reviewPackage={{
          emissao_oficial: {
            reissue_recommended: true,
            current_issue: {
              issue_number: "TAR-20260413-000321",
              issue_state_label: "Emitido",
              issued_at: "2026-04-13T18:45:00+00:00",
              primary_pdf_diverged: true,
              primary_pdf_storage_version: "v0003",
              current_primary_pdf_storage_version: "v0004",
            },
          },
          public_verification: {
            verification_url: "/app/public/laudo/verificar/hash321",
          },
        }}
      />,
    );

    expect(getByTestId("chat-issued-document-card")).toBeTruthy();
    expect(getByText("TAR-20260413-000321")).toBeTruthy();
    expect(getByText("PDF emitido divergente")).toBeTruthy();
    expect(
      getByText(
        "O PDF atual do caso divergiu do documento congelado na emissão oficial. Emitido v0003 · Atual v0004.",
      ),
    ).toBeTruthy();
    expect(
      getByText("Verificação pública: /app/public/laudo/verificar/hash321"),
    ).toBeTruthy();
  });

  it("não mostra cards formais quando o caso segue em análise livre", () => {
    const { queryByTestId, queryByText } = render(
      <ThreadConversationPane
        {...baseProps}
        vendoMesa={false}
        caseLifecycleStatus="pre_laudo"
        caseWorkflowMode="laudo_guiado"
        entryModeEffective="chat_first"
        conversaVazia={false}
        mensagensVisiveis={[
          {
            id: 1,
            papel: "assistente",
            texto: "Resposta livre da IA.",
            tipo: "assistant",
            citacoes: [],
          },
        ]}
        reportPackDraft={{} as never}
        reviewPackage={
          {
            emissao_oficial: {
              current_issue: {
                issue_number: "TAR-20260413-000999",
              },
            },
          } as never
        }
      />,
    );

    expect(queryByTestId("chat-report-pack-card")).toBeNull();
    expect(queryByTestId("chat-issued-document-card")).toBeNull();
    expect(queryByText("pré-laudo canônico")).toBeNull();
    expect(queryByText("documento emitido")).toBeNull();
  });

  it("sanitiza preferencias internas vazadas na renderizacao do chat", () => {
    const { queryByText, getByText } = render(
      <ThreadConversationPane
        {...baseProps}
        vendoMesa={false}
        conversaVazia={false}
        mensagensVisiveis={[
          {
            id: 1,
            papel: "usuario",
            texto:
              "[preferencias_ia_mobile]\nresponda em Português\n[/preferencias_ia_mobile]",
            tipo: "user",
            citacoes: [],
          },
        ]}
      />,
    );

    expect(getByText("Evidência enviada")).toBeTruthy();
    expect(queryByText("[preferencias_ia_mobile]")).toBeNull();
  });

  it("expõe a superfície principal do chat e marca o último PDF da assistente", () => {
    const { getByTestId, queryAllByTestId } = render(
      <ThreadConversationPane
        {...baseProps}
        vendoMesa={false}
        conversaVazia={false}
        mensagensVisiveis={[
          {
            id: 1,
            papel: "assistente",
            texto: "Primeiro PDF.",
            tipo: "assistant",
            citacoes: [],
            anexos: [
              {
                id: 100,
                nome_original: "relatorio_antigo.pdf",
                mime_type: "application/pdf",
                categoria: "documento",
                url: "/app/api/laudo/80/mesa/anexos/100",
              },
            ],
          },
          {
            id: 2,
            papel: "assistente",
            texto: "PDF mais recente.",
            tipo: "assistant",
            citacoes: [],
            anexos: [
              {
                id: 101,
                nome_original: "relatorio_chat_livre_80.pdf",
                mime_type: "application/pdf",
                categoria: "documento",
                url: "/app/api/laudo/80/mesa/anexos/101",
              },
            ],
          },
        ]}
        sessionAccessToken="token-demo"
      />,
    );

    expect(getByTestId("chat-thread-surface")).toBeTruthy();
    expect(getByTestId("chat-last-assistant-document-attachment")).toBeTruthy();
    expect(
      queryAllByTestId("chat-last-assistant-document-attachment"),
    ).toHaveLength(1);
  });
});
