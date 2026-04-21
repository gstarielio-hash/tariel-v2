import {
  MobileV2ContractError,
  mapMobileInspectorFeedV2ToLegacy,
  mapMobileInspectorThreadV2ToLegacy,
  parseMobileInspectorFeedV2,
  parseMobileInspectorThreadV2,
} from "./mobileV2MesaAdapter";

function criarFeedPayloadV2(): Record<string, unknown> {
  return {
    contract_name: "MobileInspectorFeedV2",
    contract_version: "v2",
    tenant_id: "tenant-1",
    source_channel: "android_mesa_feed_v2",
    visibility_scope: "inspetor_mobile",
    requested_laudo_ids: [21],
    cursor_current: "2026-03-25T10:31:00Z",
    total_requested_cases: 1,
    returned_item_count: 1,
    timestamp: "2026-03-25T10:31:00Z",
    items: [
      {
        contract_name: "MobileInspectorFeedItemV2",
        contract_version: "v2",
        tenant_id: "tenant-1",
        source_channel: "android_mesa_feed_v2",
        case_id: "case-21",
        legacy_laudo_id: 21,
        thread_id: "thread-21",
        visibility_scope: "inspetor_mobile",
        case_status: "needs_reviewer",
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
            label: "Assumir revisao da mesa",
            owner_role: "mesa",
            preferred_surface: "mesa",
          },
          {
            target_status: "devolvido_para_correcao",
            transition_kind: "correction",
            label: "Devolver para correcao",
            owner_role: "inspetor",
            preferred_surface: "mesa",
          },
          {
            target_status: "aprovado",
            transition_kind: "approval",
            label: "Aprovar caso",
            owner_role: "none",
            preferred_surface: "mesa",
          },
        ],
        allowed_surface_actions: ["mesa_approve", "mesa_return"],
        human_validation_required: true,
        legacy_public_state: "aguardando",
        allows_edit: true,
        allows_reopen: false,
        has_interaction: true,
        updated_at: "2026-03-25T10:31:00Z",
        total_visible_interactions: 2,
        unread_visible_interactions: 1,
        open_feedback_count: 1,
        resolved_feedback_count: 0,
        case_card: {
          contract_name: "MobileInspectorCaseCardV2",
          contract_version: "v2",
          legacy_laudo_id: 21,
          title: "Caldeira B-202",
          preview: "Ajustar item 4",
          template_key: "padrao",
          review_status: "aguardando",
          card_status: "aguardando",
          card_status_label: "Aguardando",
          date_iso: "2026-03-25",
          date_display: "25/03/2026",
          time_display: "10:31",
          is_pinned: false,
          allows_edit: true,
          allows_reopen: false,
          has_history: true,
          visibility_scope: "inspetor_mobile",
        },
        latest_interaction: {
          contract_name: "MobileInspectorInteractionSummaryV2",
          contract_version: "v2",
          interaction_id: "interaction-301",
          message_id: 301,
          actor_role: "mesa",
          actor_kind: "human",
          origin_kind: "human",
          content_kind: "text",
          legacy_message_type: "humano_eng",
          text_preview: "Ajustar item 4",
          timestamp: "2026-03-25T10:31:00Z",
          sender_id: 7,
          client_message_id: null,
          reference_message_id: null,
          is_read: false,
          has_attachments: false,
          review_feedback_visible: true,
          review_marker_visible: true,
          highlight_marker: true,
          pending_open: true,
          pending_resolved: false,
          visibility_scope: "inspetor_mobile",
        },
        review_signals: {
          contract_name: "MobileInspectorReviewSignalsV2",
          contract_version: "v2",
          review_visible_to_inspector: true,
          total_visible_interactions: 2,
          visible_feedback_count: 1,
          open_feedback_count: 1,
          resolved_feedback_count: 0,
          latest_feedback_message_id: 301,
          latest_feedback_at: "2026-03-25T10:31:00Z",
          visibility_scope: "inspetor_mobile",
        },
        feedback_policy: {
          contract_name: "MobileInspectorFeedbackPolicyV2",
          contract_version: "v2",
          policy_name: "android_feedback_sync_policy",
          feedback_mode: "visible_feedback_only",
          feedback_counters_visible: true,
          feedback_message_bodies_visible: true,
          latest_feedback_pointer_visible: true,
          mesa_internal_details_visible: false,
          visibility_scope: "inspetor_mobile",
        },
        collaboration: {
          contract_name: "MobileInspectorCollaborationV2",
          contract_version: "v2",
          summary: {
            contract_name: "MobileInspectorCollaborationSummaryV2",
            contract_version: "v2",
            feedback_visible_to_inspector: true,
            visible_feedback_count: 1,
            unread_feedback_count: 1,
            open_feedback_count: 1,
            resolved_feedback_count: 0,
            latest_feedback_message_id: 301,
            latest_feedback_at: "2026-03-25T10:31:00Z",
            latest_feedback_preview: "Ajustar item 4",
            visibility_scope: "inspetor_mobile",
          },
          latest_feedback: {
            contract_name: "MobileInspectorInteractionSummaryV2",
            contract_version: "v2",
            interaction_id: "interaction-301",
            message_id: 301,
            actor_role: "mesa",
            actor_kind: "human",
            origin_kind: "human",
            content_kind: "text",
            legacy_message_type: "humano_eng",
            text_preview: "Ajustar item 4",
            timestamp: "2026-03-25T10:31:00Z",
            sender_id: 7,
            client_message_id: null,
            reference_message_id: null,
            is_read: false,
            has_attachments: false,
            review_feedback_visible: true,
            review_marker_visible: true,
            highlight_marker: true,
            pending_open: true,
            pending_resolved: false,
            visibility_scope: "inspetor_mobile",
          },
          visibility_scope: "inspetor_mobile",
        },
        provenance_summary: { origin_kind: "human" },
        policy_summary: { android_projection_policy: "operational_only" },
        document_readiness: { ready: false },
        document_blockers: [{ code: "pending_review" }],
      },
    ],
  };
}

function criarThreadPayloadV2(): Record<string, unknown> {
  return {
    contract_name: "MobileInspectorThreadV2",
    contract_version: "v2",
    tenant_id: "tenant-1",
    source_channel: "android_mesa_thread_v2",
    case_id: "case-21",
    legacy_laudo_id: 21,
    thread_id: "thread-21",
    visibility_scope: "inspetor_mobile",
    case_status: "needs_reviewer",
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
        label: "Assumir revisao da mesa",
        owner_role: "mesa",
        preferred_surface: "mesa",
      },
      {
        target_status: "devolvido_para_correcao",
        transition_kind: "correction",
        label: "Devolver para correcao",
        owner_role: "inspetor",
        preferred_surface: "mesa",
      },
      {
        target_status: "aprovado",
        transition_kind: "approval",
        label: "Aprovar caso",
        owner_role: "none",
        preferred_surface: "mesa",
      },
    ],
    allowed_surface_actions: ["mesa_approve", "mesa_return"],
    human_validation_required: true,
    legacy_public_state: "aguardando",
    allows_edit: true,
    allows_reopen: false,
    case_card: {
      contract_name: "MobileInspectorCaseCardV2",
      contract_version: "v2",
      legacy_laudo_id: 21,
      title: "Caldeira B-202",
      preview: "Ajustar item 4",
      template_key: "padrao",
      review_status: "aguardando",
      card_status: "aguardando",
      card_status_label: "Aguardando",
      date_iso: "2026-03-25",
      date_display: "25/03/2026",
      time_display: "10:31",
      is_pinned: false,
      allows_edit: true,
      allows_reopen: false,
      has_history: true,
      visibility_scope: "inspetor_mobile",
    },
    total_visible_messages: 2,
    unread_visible_messages: 1,
    open_feedback_count: 1,
    resolved_feedback_count: 0,
    latest_interaction: {
      contract_name: "MobileInspectorInteractionSummaryV2",
      contract_version: "v2",
      interaction_id: "interaction-301",
      message_id: 301,
      actor_role: "mesa",
      actor_kind: "human",
      origin_kind: "human",
      content_kind: "text",
      legacy_message_type: "humano_eng",
      text_preview: "Ajustar item 4",
      timestamp: "2026-03-25T10:31:00Z",
      sender_id: 7,
      client_message_id: null,
      reference_message_id: 300,
      is_read: false,
      has_attachments: false,
      review_feedback_visible: true,
      review_marker_visible: true,
      highlight_marker: true,
      pending_open: true,
      pending_resolved: false,
      visibility_scope: "inspetor_mobile",
    },
    review_signals: {
      contract_name: "MobileInspectorReviewSignalsV2",
      contract_version: "v2",
      review_visible_to_inspector: true,
      total_visible_interactions: 2,
      visible_feedback_count: 1,
      open_feedback_count: 1,
      resolved_feedback_count: 0,
      latest_feedback_message_id: 301,
      latest_feedback_at: "2026-03-25T10:31:00Z",
      visibility_scope: "inspetor_mobile",
    },
    feedback_policy: {
      contract_name: "MobileInspectorFeedbackPolicyV2",
      contract_version: "v2",
      policy_name: "android_feedback_sync_policy",
      feedback_mode: "visible_feedback_only",
      feedback_counters_visible: true,
      feedback_message_bodies_visible: true,
      latest_feedback_pointer_visible: true,
      mesa_internal_details_visible: false,
      visibility_scope: "inspetor_mobile",
    },
    collaboration: {
      contract_name: "MobileInspectorCollaborationV2",
      contract_version: "v2",
      summary: {
        contract_name: "MobileInspectorCollaborationSummaryV2",
        contract_version: "v2",
        feedback_visible_to_inspector: true,
        visible_feedback_count: 1,
        unread_feedback_count: 1,
        open_feedback_count: 1,
        resolved_feedback_count: 0,
        latest_feedback_message_id: 301,
        latest_feedback_at: "2026-03-25T10:31:00Z",
        latest_feedback_preview: "Ajustar item 4",
        visibility_scope: "inspetor_mobile",
      },
      latest_feedback: {
        contract_name: "MobileInspectorInteractionSummaryV2",
        contract_version: "v2",
        interaction_id: "interaction-301",
        message_id: 301,
        actor_role: "mesa",
        actor_kind: "human",
        origin_kind: "human",
        content_kind: "text",
        legacy_message_type: "humano_eng",
        text_preview: "Ajustar item 4",
        timestamp: "2026-03-25T10:31:00Z",
        sender_id: 7,
        client_message_id: null,
        reference_message_id: 300,
        is_read: false,
        has_attachments: false,
        review_feedback_visible: true,
        review_marker_visible: true,
        highlight_marker: true,
        pending_open: true,
        pending_resolved: false,
        visibility_scope: "inspetor_mobile",
      },
      visibility_scope: "inspetor_mobile",
    },
    provenance_summary: { origin_kind: "human" },
    policy_summary: { android_projection_policy: "operational_only" },
    document_readiness: { ready: false },
    document_blockers: [],
    mobile_review_package: {
      contract_name: "MobileInspectorReviewPackageV2",
      contract_version: "v2",
      review_mode: "mesa_required",
      review_required: true,
      policy_summary: { android_projection_policy: "operational_only" },
      document_readiness: { readiness_state: "blocked" },
      document_blockers: [{ blocker_code: "pending_review" }],
      revisao_por_bloco: {
        total_blocks: 2,
        attention_blocks: 1,
        returned_blocks: 1,
      },
      coverage_map: {
        total_required: 5,
        total_accepted: 3,
        total_missing: 1,
        total_irregular: 1,
      },
      inspection_history: {
        source_codigo_hash: "prev001",
        diff: { summary: "2 mudancas" },
      },
      public_verification: {
        verification_url: "/app/public/laudo/verificar/hash001",
        qr_image_data_uri: "data:image/png;base64,ZmFrZQ==",
      },
      anexo_pack: {
        total_items: 4,
        total_present: 4,
        missing_required_count: 0,
      },
      emissao_oficial: {
        issue_status: "ready_for_issue",
        issue_status_label: "Pronto para emissão oficial",
        eligible_signatory_count: 1,
      },
      historico_refazer_inspetor: [{ id: 80, status: "open" }],
      memoria_operacional_familia: {
        family_key: "nr13_inspecao_caldeira",
        approved_snapshot_count: 12,
      },
      red_flags: [],
      tenant_entitlements: null,
      allowed_decisions: [
        "aprovar_no_mobile",
        "enviar_para_mesa",
        "devolver_no_mobile",
      ],
      supports_block_reopen: true,
      visibility_scope: "inspetor_mobile",
    },
    attachment_policy: {
      contract_name: "MobileInspectorAttachmentPolicyV2",
      contract_version: "v2",
      policy_name: "android_attachment_sync_policy",
      upload_allowed: true,
      download_allowed: true,
      inline_preview_allowed: true,
      supported_categories: ["imagem", "documento"],
      supported_mime_types: [
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      ],
      visibility_scope: "inspetor_mobile",
    },
    sync: {
      contract_name: "MobileInspectorThreadSyncV2",
      contract_version: "v2",
      mode: "delta",
      cursor_after_id: 300,
      next_cursor_id: 301,
      cursor_last_message_id: 301,
      has_more: false,
    },
    sync_policy: {
      contract_name: "MobileInspectorSyncPolicyV2",
      contract_version: "v2",
      policy_name: "android_thread_sync_policy",
      mode: "delta",
      offline_queue_supported: true,
      incremental_sync_supported: true,
      attachment_sync_supported: true,
      visibility_scope: "inspetor_mobile",
    },
    timestamp: "2026-03-25T10:31:00Z",
    items: [
      {
        contract_name: "MobileInspectorThreadMessageV2",
        contract_version: "v2",
        interaction_id: "interaction-300",
        message_id: 300,
        actor_role: "inspetor",
        actor_kind: "human",
        origin_kind: "human",
        content_kind: "text",
        legacy_message_type: "humano_insp",
        text_preview: "Seguem os ajustes",
        timestamp: "2026-03-25T10:28:00Z",
        sender_id: 17,
        client_message_id: "mesa:abc123",
        reference_message_id: null,
        is_read: true,
        has_attachments: false,
        review_feedback_visible: false,
        review_marker_visible: false,
        highlight_marker: false,
        pending_open: false,
        pending_resolved: false,
        visibility_scope: "inspetor_mobile",
        content_text: "Seguem os ajustes",
        display_date: "25/03/2026",
        resolved_at: null,
        resolved_at_label: "",
        resolved_by_name: "",
        attachments: [],
        delivery_status: "persisted",
        order_index: 0,
        cursor_id: 300,
        is_delta_item: true,
      },
      {
        contract_name: "MobileInspectorThreadMessageV2",
        contract_version: "v2",
        interaction_id: "interaction-301",
        message_id: 301,
        actor_role: "mesa",
        actor_kind: "human",
        origin_kind: "human",
        content_kind: "attachment",
        legacy_message_type: "humano_eng",
        text_preview: "Ajustar item 4",
        timestamp: "2026-03-25T10:31:00Z",
        sender_id: 7,
        client_message_id: null,
        reference_message_id: 300,
        is_read: false,
        has_attachments: true,
        review_feedback_visible: true,
        review_marker_visible: true,
        highlight_marker: true,
        pending_open: true,
        pending_resolved: false,
        visibility_scope: "inspetor_mobile",
        content_text: "Ajustar item 4",
        display_date: "25/03/2026",
        resolved_at: null,
        resolved_at_label: "",
        resolved_by_name: "",
        attachments: [
          {
            contract_name: "MobileInspectorAttachmentV2",
            contract_version: "v2",
            attachment_id: 9,
            name: "foto.jpg",
            category: "imagem",
            mime_type: "image/jpeg",
            size_bytes: 2048,
            is_image: true,
            download_url: "/app/api/laudo/21/mesa/anexos/9",
            visibility_scope: "inspetor_mobile",
          },
        ],
        delivery_status: "persisted",
        order_index: 1,
        cursor_id: 301,
        is_delta_item: true,
      },
    ],
  };
}

describe("mobileV2MesaAdapter", () => {
  it("parseia e adapta o feed V2 para o payload legado sem alterar a UI", () => {
    const payload = parseMobileInspectorFeedV2(criarFeedPayloadV2());
    const legado = mapMobileInspectorFeedV2ToLegacy(payload);

    expect(payload.items[0]?.collaboration.summary.unread_feedback_count).toBe(
      1,
    );
    expect(payload.items[0]?.collaboration.latest_feedback?.message_id).toBe(
      301,
    );
    expect(payload.items[0]?.case_lifecycle_status).toBe("aguardando_mesa");
    expect(payload.items[0]?.case_workflow_mode).toBe("laudo_com_mesa");
    expect(payload.items[0]?.active_owner_role).toBe("mesa");
    expect(payload.items[0]?.allowed_next_lifecycle_statuses).toEqual([
      "em_revisao_mesa",
      "devolvido_para_correcao",
      "aprovado",
    ]);
    expect(payload.items[0]?.allowed_surface_actions).toEqual([
      "mesa_approve",
      "mesa_return",
    ]);
    expect(
      payload.items[0]?.allowed_lifecycle_transitions.map(
        (item) => item.target_status,
      ),
    ).toEqual(["em_revisao_mesa", "devolvido_para_correcao", "aprovado"]);

    expect(legado).toMatchObject({
      cursor_atual: "2026-03-25T10:31:00Z",
      laudo_ids: [21],
      itens: [
        {
          laudo_id: 21,
          estado: "aguardando",
          permite_edicao: true,
          permite_reabrir: false,
          resumo: {
            total_mensagens: 2,
            mensagens_nao_lidas: 1,
            pendencias_abertas: 1,
            pendencias_resolvidas: 0,
            ultima_mensagem_id: 301,
            ultima_mensagem_preview: "Ajustar item 4",
          },
        },
      ],
    });
    expect(legado.itens[0].laudo_card?.titulo).toBe("Caldeira B-202");
    expect("policy_summary" in legado.itens[0]).toBe(false);
    expect("document_readiness" in legado.itens[0]).toBe(false);
  });

  it("aceita feed V2 com politica visivel e zero feedback exposto", () => {
    const bruto = criarFeedPayloadV2();
    const itens = bruto.items as Array<Record<string, unknown>>;
    itens[0] = {
      ...itens[0],
      latest_interaction: {
        ...((itens[0].latest_interaction as Record<string, unknown>) || {}),
        actor_role: "inspetor",
        message_id: 300,
        text_preview: "Rascunho salvo pelo inspetor",
        timestamp: "2026-03-25T10:28:00Z",
        sender_id: 17,
        review_feedback_visible: false,
        review_marker_visible: false,
        highlight_marker: false,
        pending_open: false,
        pending_resolved: false,
      },
      unread_visible_interactions: 0,
      open_feedback_count: 0,
      resolved_feedback_count: 0,
      review_signals: {
        ...((itens[0].review_signals as Record<string, unknown>) || {}),
        visible_feedback_count: 0,
        open_feedback_count: 0,
        resolved_feedback_count: 0,
        latest_feedback_message_id: null,
        latest_feedback_at: null,
      },
      collaboration: {
        contract_name: "MobileInspectorCollaborationV2",
        contract_version: "v2",
        summary: {
          contract_name: "MobileInspectorCollaborationSummaryV2",
          contract_version: "v2",
          feedback_visible_to_inspector: true,
          visible_feedback_count: 0,
          unread_feedback_count: 0,
          open_feedback_count: 0,
          resolved_feedback_count: 0,
          latest_feedback_message_id: null,
          latest_feedback_at: null,
          latest_feedback_preview: "",
          visibility_scope: "inspetor_mobile",
        },
        latest_feedback: null,
        visibility_scope: "inspetor_mobile",
      },
    };

    const payload = parseMobileInspectorFeedV2(bruto);
    const legado = mapMobileInspectorFeedV2ToLegacy(payload);

    expect(payload.items[0]?.review_signals.visible_feedback_count).toBe(0);
    expect(payload.items[0]?.collaboration.latest_feedback).toBeNull();
    expect(legado.itens[0]?.resumo).toMatchObject({
      mensagens_nao_lidas: 0,
      pendencias_abertas: 0,
      pendencias_resolvidas: 0,
    });
  });

  it("parseia e adapta a thread V2 preservando sync incremental e anexos", () => {
    const payload = parseMobileInspectorThreadV2(criarThreadPayloadV2());
    const legado = mapMobileInspectorThreadV2ToLegacy(payload);

    expect(payload.collaboration.summary.open_feedback_count).toBe(1);
    expect(payload.collaboration.latest_feedback?.message_id).toBe(301);
    expect(payload.attachment_policy.policy_name).toBe(
      "android_attachment_sync_policy",
    );
    expect(payload.mobile_review_package?.review_mode).toBe("mesa_required");
    expect(payload.mobile_review_package?.anexo_pack).toMatchObject({
      total_items: 4,
    });
    expect(payload.mobile_review_package?.emissao_oficial).toMatchObject({
      issue_status: "ready_for_issue",
    });
    expect(payload.mobile_review_package?.allowed_decisions).toContain(
      "enviar_para_mesa",
    );
    expect(payload.case_lifecycle_status).toBe("aguardando_mesa");
    expect(payload.case_workflow_mode).toBe("laudo_com_mesa");
    expect(payload.active_owner_role).toBe("mesa");
    expect(payload.allowed_next_lifecycle_statuses).toEqual([
      "em_revisao_mesa",
      "devolvido_para_correcao",
      "aprovado",
    ]);
    expect(payload.allowed_surface_actions).toEqual([
      "mesa_approve",
      "mesa_return",
    ]);
    expect(
      payload.allowed_lifecycle_transitions.map((item) => item.target_status),
    ).toEqual(["em_revisao_mesa", "devolvido_para_correcao", "aprovado"]);
    expect(payload.sync_policy.mode).toBe("delta");
    expect(payload.items[1]?.attachments[0]?.contract_name).toBe(
      "MobileInspectorAttachmentV2",
    );

    expect(legado).toMatchObject({
      laudo_id: 21,
      cursor_proximo: 301,
      cursor_ultimo_id: 301,
      tem_mais: false,
      estado: "aguardando",
      sync: {
        modo: "delta",
        apos_id: 300,
        cursor_ultimo_id: 301,
      },
      resumo: {
        total_mensagens: 2,
        mensagens_nao_lidas: 1,
        pendencias_abertas: 1,
      },
      review_package: {
        review_mode: "mesa_required",
        review_required: true,
        supports_block_reopen: true,
      },
    });
    expect(legado.itens).toHaveLength(2);
    expect(legado.itens[1]).toMatchObject({
      id: 301,
      tipo: "humano_eng",
      texto: "Ajustar item 4",
      referencia_mensagem_id: 300,
      anexos: [{ id: 9, nome: "foto.jpg", categoria: "imagem" }],
    });
    expect(legado.review_package?.coverage_map).toMatchObject({
      total_required: 5,
      total_accepted: 3,
    });
    expect(legado.attachment_policy).toMatchObject({
      policy_name: "android_attachment_sync_policy",
      supported_categories: ["imagem", "documento"],
    });
    expect(legado.review_package?.anexo_pack).toMatchObject({
      total_items: 4,
    });
    expect(legado.review_package?.emissao_oficial).toMatchObject({
      issue_status: "ready_for_issue",
    });
  });

  it("preserva o contexto operacional estruturado no mapeamento legado da thread", () => {
    const bruto = criarThreadPayloadV2();
    const itens = bruto.items as Array<Record<string, unknown>>;
    itens[1] = {
      ...itens[1],
      operational_context: {
        task_kind: "coverage_return_request",
        title: "Foto da placa",
        required_action: "Reenviar imagem nitida da placa.",
        expected_reply_mode_label: "imagem obrigatória",
      },
    };

    const legado = mapMobileInspectorThreadV2ToLegacy(
      parseMobileInspectorThreadV2(bruto),
    );

    expect(legado.itens[1].operational_context).toMatchObject({
      task_kind: "coverage_return_request",
      title: "Foto da placa",
    });
  });

  it("bloqueia payload V2 que viole a visibilidade do papel Inspetor", () => {
    const payload = criarThreadPayloadV2();
    const items = payload.items as Array<Record<string, unknown>>;
    items[1] = {
      ...items[1],
      actor_role: "ia",
    };

    expect(() => parseMobileInspectorThreadV2(payload)).toThrow(
      MobileV2ContractError,
    );
  });

  it("bloqueia leak de feedback da mesa quando a política móvel está oculta", () => {
    const payload = criarThreadPayloadV2();
    payload.latest_interaction = {
      ...(payload.latest_interaction as Record<string, unknown>),
      actor_role: "inspetor",
      message_id: 300,
      text_preview: "Seguem os ajustes",
      timestamp: "2026-03-25T10:28:00Z",
      sender_id: 17,
      client_message_id: "mesa:abc123",
      reference_message_id: null,
      is_read: true,
      review_feedback_visible: false,
      review_marker_visible: false,
      highlight_marker: false,
      pending_open: false,
      pending_resolved: false,
    };
    payload.review_signals = {
      ...(payload.review_signals as Record<string, unknown>),
      review_visible_to_inspector: false,
      visible_feedback_count: 0,
      open_feedback_count: 0,
      resolved_feedback_count: 0,
      latest_feedback_message_id: null,
      latest_feedback_at: null,
    };
    payload.feedback_policy = {
      contract_name: "MobileInspectorFeedbackPolicyV2",
      contract_version: "v2",
      policy_name: "android_feedback_sync_policy",
      feedback_mode: "hidden",
      feedback_counters_visible: false,
      feedback_message_bodies_visible: false,
      latest_feedback_pointer_visible: false,
      mesa_internal_details_visible: false,
      visibility_scope: "inspetor_mobile",
    };
    payload.unread_visible_messages = 0;
    payload.open_feedback_count = 0;
    payload.resolved_feedback_count = 0;

    expect(() => parseMobileInspectorThreadV2(payload)).toThrow(
      MobileV2ContractError,
    );
  });
});
