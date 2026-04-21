jest.mock("./observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

import {
  carregarFeedMesaMobile,
  carregarMensagensMesaMobile,
  executarComandoRevisaoMobile,
  enviarMensagemMesaMobile,
} from "./mesaApi";
import { extractMobileV2ReadRenderMetadata } from "./mobileV2HumanValidation";
import { __resetMobileV2CapabilitiesCacheForTests } from "./mobileV2Rollout";

function criarResposta(
  body: string,
  init?: { status?: number; contentType?: string },
) {
  const status = init?.status ?? 200;
  const headers = new Headers();
  headers.set("content-type", init?.contentType ?? "application/json");
  return {
    ok: status >= 200 && status < 300,
    status,
    headers,
    text: async () => body,
  } as Response;
}

function payloadCapabilities(overrides?: Record<string, unknown>) {
  return {
    ok: true,
    contract_name: "MobileInspectorCapabilitiesV2",
    contract_version: "v2",
    capabilities_version: "2026-03-25.09c",
    mobile_v2_reads_enabled: true,
    mobile_v2_feed_enabled: true,
    mobile_v2_thread_enabled: true,
    tenant_allowed: true,
    cohort_allowed: false,
    reason: "tenant_allowlisted",
    rollout_reason: "tenant_allowlisted",
    source: "tenant_allowlist",
    feed_reason: "tenant_allowlisted",
    feed_source: "tenant_allowlist",
    thread_reason: "tenant_allowlisted",
    thread_source: "tenant_allowlist",
    rollout_bucket: 12,
    rollout_state: "pilot_enabled",
    feed_rollout_state: "pilot_enabled",
    thread_rollout_state: "pilot_enabled",
    feed_candidate_for_promotion: false,
    thread_candidate_for_promotion: false,
    feed_promoted: false,
    thread_promoted: false,
    feed_hold: false,
    thread_hold: false,
    feed_rollback_forced: false,
    thread_rollback_forced: false,
    operator_validation_run_active: false,
    operator_validation_run_id: null,
    operator_validation_required_surfaces: [],
    ...(overrides || {}),
  };
}

describe("mesaApi", () => {
  const fetchMock = jest.fn();
  const envOriginal = { ...process.env };

  beforeEach(() => {
    fetchMock.mockReset();
    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      value: fetchMock,
    });
    process.env = { ...envOriginal };
    delete process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED;
    __resetMobileV2CapabilitiesCacheForTests();
  });

  afterAll(() => {
    process.env = envOriginal;
    __resetMobileV2CapabilitiesCacheForTests();
  });

  it("carrega mensagens da mesa com sync incremental", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          laudo_id: 21,
          itens: [],
          cursor_proximo: null,
          cursor_ultimo_id: 44,
          tem_mais: false,
          estado: "relatorio_ativo",
          permite_edicao: true,
          permite_reabrir: false,
          laudo_card: null,
          resumo: {
            atualizado_em: "2026-03-21T10:00:00Z",
            total_mensagens: 4,
            mensagens_nao_lidas: 1,
            pendencias_abertas: 1,
            pendencias_resolvidas: 0,
            ultima_mensagem_id: 44,
            ultima_mensagem_em: "2026-03-21T10:00:00Z",
            ultima_mensagem_preview: "Mesa",
            ultima_mensagem_tipo: "humano_eng",
            ultima_mensagem_remetente_id: 7,
          },
          sync: {
            modo: "delta",
            apos_id: 40,
            cursor_ultimo_id: 44,
          },
        }),
      ),
    );

    await expect(
      carregarMensagensMesaMobile("token-123", 21, { aposId: 40 }),
    ).resolves.toMatchObject({
      laudo_id: 21,
      cursor_ultimo_id: 44,
      sync: { modo: "delta", apos_id: 40 },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/app/api/laudo/21/mesa/mensagens?apos_id=40"),
      expect.any(Object),
    );
  });

  it("envia mensagem da mesa com client_message_id e correlacao", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          laudo_id: 21,
          estado: "relatorio_ativo",
          permite_edicao: true,
          permite_reabrir: false,
          laudo_card: null,
          mensagem: {
            id: 99,
            laudo_id: 21,
            tipo: "humano_insp",
            texto: "Resposta",
            remetente_id: 1,
            data: "21/03 10:00",
            lida: true,
            resolvida_em: "",
            resolvida_em_label: "",
            resolvida_por_nome: "",
            client_message_id: "mesa:abc123",
          },
        }),
      ),
    );

    await enviarMensagemMesaMobile(
      "token-123",
      21,
      "Resposta",
      44,
      "mesa:abc123",
    );

    const [, requestInit] = fetchMock.mock.calls[0];
    expect(requestInit.headers.get("X-Client-Request-Id")).toBe("mesa:abc123");
    expect(requestInit.headers.get("X-Correlation-ID")).toBe("mesa:abc123");
    expect(requestInit.headers.get("X-Request-Id")).toBe("mesa:abc123");
    expect(requestInit.headers.get("X-Mesa-Client-Trace-Id")).toBe(
      "mesa:abc123",
    );
    expect(requestInit.headers.get("traceparent")).toMatch(
      /^00-[0-9a-f]{32}-[0-9a-f]{16}-0[01]$/,
    );
    expect(JSON.parse(String(requestInit.body))).toMatchObject({
      texto: "Resposta",
      referencia_mensagem_id: 44,
      client_message_id: "mesa:abc123",
    });
  });

  it("executa comando de revisão mobile com payload canônico", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          ok: true,
          command: "reabrir_bloco",
          message: "Bloco reaberto na revisão mobile.",
          laudo_id: 21,
          estado: "relatorio_ativo",
          status_card: "aberto",
          permite_edicao: true,
          permite_reabrir: false,
          laudo_card: null,
        }),
      ),
    );

    await expect(
      executarComandoRevisaoMobile("token-123", 21, {
        command: "reabrir_bloco",
        block_key: "identificacao",
        title: "Identificação",
        reason: "Revalidar a identificação técnica.",
      }),
    ).resolves.toMatchObject({
      ok: true,
      command: "reabrir_bloco",
      laudo_id: 21,
    });

    const [, requestInit] = fetchMock.mock.calls[0];
    expect(requestInit.method).toBe("POST");
    expect(requestInit.headers.get("content-type")).toBe("application/json");
    expect(JSON.parse(String(requestInit.body))).toMatchObject({
      command: "reabrir_bloco",
      block_key: "identificacao",
      title: "Identificação",
      reason: "Revalidar a identificação técnica.",
    });
  });

  it("carrega o feed resumido da mesa para os laudos monitorados", async () => {
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          cursor_atual: "2026-03-21T11:00:00Z",
          laudo_ids: [21, 22],
          itens: [{ laudo_id: 22, resumo: { total_mensagens: 3 } }],
        }),
      ),
    );

    await expect(
      carregarFeedMesaMobile("token-123", {
        laudoIds: [21, 22],
        cursorAtualizadoEm: "2026-03-21T10:00:00Z",
      }),
    ).resolves.toMatchObject({
      cursor_atual: "2026-03-21T11:00:00Z",
      laudo_ids: [21, 22],
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        "/app/api/mobile/mesa/feed?laudo_ids=21%2C22&cursor_atualizado_em=2026-03-21T10%3A00%3A00Z",
      ),
      expect.any(Object),
    );
  });

  it("propaga trace id canônico no request legado da central quando a flag local está desligada", async () => {
    const traces: Array<Record<string, unknown>> = [];
    fetchMock.mockResolvedValue(
      criarResposta(
        JSON.stringify({
          cursor_atual: "2026-03-21T11:00:00Z",
          laudo_ids: [80],
          itens: [],
        }),
      ),
    );

    await carregarFeedMesaMobile("token-123", {
      laudoIds: [80],
      onRequestTrace: (trace) => {
        traces.push(trace as unknown as Record<string, unknown>);
      },
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, requestInit] = fetchMock.mock.calls[0];
    expect(requestInit.headers.get("X-Tariel-Mobile-Central-Trace")).toMatch(
      /^feed-/,
    );
    expect(
      requestInit.headers.get("X-Tariel-Mobile-Central-Trace-Source"),
    ).toBe("activity_center_feed");
    expect(traces[0]).toMatchObject({
      contractFlagEnabled: false,
      contractFlagRawValue: null,
      contractFlagSource: "expo_public_env",
      decisionReason: "local_flag_off",
      decisionSource: "local_flag",
      phase: "intent_created",
      routeDecision: "legacy",
      targetIds: [80],
    });
    expect(traces.at(-1)).toMatchObject({
      actualRoute: "legacy",
      deliveryMode: "legacy",
      fallbackReason: "local_flag_off",
      phase: "response_received",
      responseStatus: 200,
    });
  });

  it("materializa o rawValue da flag no trace quando o feed entra elegível para V2", async () => {
    process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED = "1";
    const traces: Array<Record<string, unknown>> = [];
    fetchMock
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify(
            payloadCapabilities({
              feed_reason: "promoted",
              feed_source: "surface_state_override",
              feed_rollout_state: "promoted",
            }),
          ),
        ),
      )
      .mockRejectedValueOnce(new Error("falha_v2"))
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify({
            cursor_atual: "2026-03-27T10:00:00Z",
            laudo_ids: [80],
            itens: [],
          }),
        ),
      );

    await carregarFeedMesaMobile("token-123", {
      laudoIds: [80],
      onRequestTrace: (trace) => {
        traces.push(trace as unknown as Record<string, unknown>);
      },
    });

    expect(traces[0]).toMatchObject({
      contractFlagEnabled: true,
      contractFlagRawValue: "1",
      contractFlagSource: "expo_public_env",
      routeDecision: "v2",
      decisionReason: "enabled",
      decisionSource: "surface_state_override",
      targetIds: [80],
    });
  });

  it("usa o contrato publico V2 da thread quando a flag local esta ativa", async () => {
    process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED = "1";
    fetchMock
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify(
            payloadCapabilities({
              organic_validation_active: true,
              organic_validation_session_id: "orgv_threadcase123",
              organic_validation_surfaces: ["thread"],
              organic_validation_target_suggestions: [
                {
                  surface: "thread",
                  suggested_target_ids: [21],
                  covered_target_ids: [],
                  missing_target_ids: [21],
                  distinct_targets_observed: 0,
                  coverage_met: false,
                  targets_available: true,
                  detail: "targets_suggested",
                },
              ],
              organic_validation_surface_coverage: [],
              organic_validation_has_partial_coverage: false,
              organic_validation_targets_ready: true,
              operator_validation_run_active: true,
              operator_validation_run_id: "oprv_threadcase123",
              operator_validation_required_surfaces: ["thread"],
            }),
          ),
        ),
      )
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify({
            contract_name: "MobileInspectorThreadV2",
            contract_version: "v2",
            tenant_id: "tenant-1",
            source_channel: "android_mesa_thread_v2",
            case_id: "case-21",
            legacy_laudo_id: 21,
            thread_id: "thread-21",
            visibility_scope: "inspetor_mobile",
            case_status: "needs_reviewer",
            legacy_public_state: "aguardando",
            allows_edit: true,
            allows_reopen: false,
            case_card: null,
            total_visible_messages: 1,
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
              total_visible_interactions: 1,
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
            provenance_summary: null,
            policy_summary: null,
            document_readiness: null,
            document_blockers: [],
            mobile_review_package: {
              contract_name: "MobileInspectorReviewPackageV2",
              contract_version: "v2",
              review_mode: "mesa_required",
              review_required: true,
              policy_summary: null,
              document_readiness: { readiness_state: "blocked" },
              document_blockers: [{ blocker_code: "pending_review" }],
              revisao_por_bloco: { returned_blocks: 1, attention_blocks: 1 },
              coverage_map: { total_required: 5, total_accepted: 3 },
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
              historico_refazer_inspetor: [{ id: 1, status: "open" }],
              memoria_operacional_familia: {
                family_key: "nr13_inspecao_caldeira",
                approved_snapshot_count: 12,
              },
              red_flags: [],
              tenant_entitlements: null,
              allowed_decisions: ["enviar_para_mesa", "devolver_no_mobile"],
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
              cursor_after_id: 40,
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
                content_text: "Ajustar item 4",
                display_date: "25/03/2026",
                resolved_at: null,
                resolved_at_label: "",
                resolved_by_name: "",
                attachments: [],
                delivery_status: "persisted",
                order_index: 0,
                cursor_id: 301,
                is_delta_item: true,
              },
            ],
          }),
        ),
      );

    const payload = await carregarMensagensMesaMobile("token-123", 21, {
      aposId: 40,
    });

    expect(payload).toMatchObject({
      laudo_id: 21,
      cursor_ultimo_id: 301,
      sync: { modo: "delta", apos_id: 40 },
      itens: [{ id: 301, tipo: "humano_eng", referencia_mensagem_id: 300 }],
      review_package: {
        review_mode: "mesa_required",
        review_required: true,
      },
    });
    expect(payload.review_package?.coverage_map).toMatchObject({
      total_required: 5,
      total_accepted: 3,
    });
    expect(payload.review_package?.anexo_pack).toMatchObject({
      total_items: 4,
    });
    expect(payload.review_package?.emissao_oficial).toMatchObject({
      issue_status: "ready_for_issue",
    });
    expect(extractMobileV2ReadRenderMetadata(payload)).toEqual({
      route: "thread",
      deliveryMode: "v2",
      capabilitiesVersion: "2026-03-25.09c",
      rolloutBucket: 12,
      usageMode: "organic_validation",
      validationSessionId: "orgv_threadcase123",
      operatorRunId: "oprv_threadcase123",
      suggestedTargetIds: [21],
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/app/api/mobile/v2/capabilities",
    );
    expect(fetchMock).toHaveBeenLastCalledWith(
      expect.stringContaining(
        "/app/api/mobile/v2/laudo/21/mesa/mensagens?apos_id=40",
      ),
      expect.any(Object),
    );
    const [, requestInit] = fetchMock.mock.calls[1];
    expect(requestInit.headers.get("X-Tariel-Mobile-V2-Attempted")).toBe("1");
    expect(requestInit.headers.get("X-Tariel-Mobile-V2-Route")).toBe("thread");
    expect(
      requestInit.headers.get("X-Tariel-Mobile-V2-Capabilities-Version"),
    ).toBe("2026-03-25.09c");
    expect(requestInit.headers.get("X-Tariel-Mobile-V2-Rollout-Bucket")).toBe(
      "12",
    );
    expect(requestInit.headers.get("X-Tariel-Mobile-Usage-Mode")).toBe(
      "organic_validation",
    );
    expect(requestInit.headers.get("X-Tariel-Mobile-Validation-Session")).toBe(
      "orgv_threadcase123",
    );
    expect(requestInit.headers.get("X-Tariel-Mobile-Operator-Run")).toBe(
      "oprv_threadcase123",
    );
  });

  it("bloqueia fallback legado da thread durante validacao organica ativa", async () => {
    process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED = "1";
    fetchMock
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify(
            payloadCapabilities({
              organic_validation_active: true,
              organic_validation_session_id: "orgv_threadblocked123",
              organic_validation_surfaces: ["thread"],
              organic_validation_target_suggestions: [
                {
                  surface: "thread",
                  suggested_target_ids: [21],
                  covered_target_ids: [],
                  missing_target_ids: [21],
                  distinct_targets_observed: 0,
                  coverage_met: false,
                  targets_available: true,
                  detail: "targets_suggested",
                },
              ],
              organic_validation_surface_coverage: [],
              organic_validation_has_partial_coverage: false,
              organic_validation_targets_ready: true,
              operator_validation_run_active: true,
              operator_validation_run_id: "oprv_threadblocked123",
              operator_validation_required_surfaces: ["thread"],
            }),
          ),
        ),
      )
      .mockRejectedValueOnce(new Error("falha_transiente_v2"));

    await expect(carregarMensagensMesaMobile("token-123", 21)).rejects.toThrow(
      "Fallback legado bloqueado para thread durante validacao organica (http_error).",
    );

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/app/api/mobile/v2/capabilities",
    );
    expect(fetchMock.mock.calls[1][0]).toContain(
      "/app/api/mobile/v2/laudo/21/mesa/mensagens",
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).includes("/app/api/laudo/21/mesa/mensagens"),
      ),
    ).toBe(false);
  });

  it("usa legado quando o gate remoto desliga o feed V2", async () => {
    process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED = "1";
    fetchMock
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify(
            payloadCapabilities({
              mobile_v2_feed_enabled: false,
              feed_reason: "feed_route_disabled",
              feed_source: "route_flag",
              organic_validation_active: true,
              organic_validation_session_id: "orgv_feedgate123",
              organic_validation_surfaces: ["feed"],
              organic_validation_target_suggestions: [
                {
                  surface: "feed",
                  suggested_target_ids: [21],
                  covered_target_ids: [],
                  missing_target_ids: [21],
                  distinct_targets_observed: 0,
                  coverage_met: false,
                  targets_available: true,
                  detail: "targets_suggested",
                },
              ],
              organic_validation_surface_coverage: [],
              organic_validation_has_partial_coverage: false,
              organic_validation_targets_ready: true,
              operator_validation_run_active: true,
              operator_validation_run_id: "oprv_feedgate123",
              operator_validation_required_surfaces: ["feed"],
            }),
          ),
        ),
      )
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify({
            cursor_atual: "2026-03-21T11:00:00Z",
            laudo_ids: [21, 22],
            itens: [{ laudo_id: 22, resumo: { total_mensagens: 3 } }],
          }),
        ),
      );

    const resposta = await carregarFeedMesaMobile("token-123", {
      laudoIds: [21, 22],
      cursorAtualizadoEm: "2026-03-21T10:00:00Z",
    });

    expect(resposta).toMatchObject({
      cursor_atual: "2026-03-21T11:00:00Z",
      laudo_ids: [21, 22],
    });
    expect(extractMobileV2ReadRenderMetadata(resposta)).toEqual({
      route: "feed",
      deliveryMode: "legacy",
      capabilitiesVersion: "2026-03-25.09c",
      rolloutBucket: 12,
      usageMode: "organic_validation",
      validationSessionId: "orgv_feedgate123",
      operatorRunId: "oprv_feedgate123",
      suggestedTargetIds: [21],
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/app/api/mobile/v2/capabilities",
    );
    expect(fetchMock.mock.calls[1][0]).toContain("/app/api/mobile/mesa/feed");
    const [, requestInit] = fetchMock.mock.calls[1];
    expect(requestInit.headers.get("X-Tariel-Mobile-V2-Attempted")).toBe("1");
    expect(requestInit.headers.get("X-Tariel-Mobile-V2-Fallback-Reason")).toBe(
      "route_disabled",
    );
    expect(
      requestInit.headers.get("X-Tariel-Mobile-V2-Capabilities-Version"),
    ).toBe("2026-03-25.09c");
    expect(requestInit.headers.get("X-Tariel-Mobile-V2-Rollout-Bucket")).toBe(
      "12",
    );
    expect(requestInit.headers.get("X-Tariel-Mobile-Usage-Mode")).toBe(
      "organic_validation",
    );
    expect(requestInit.headers.get("X-Tariel-Mobile-Validation-Session")).toBe(
      "orgv_feedgate123",
    );
    expect(requestInit.headers.get("X-Tariel-Mobile-Operator-Run")).toBe(
      "oprv_feedgate123",
    );
  });

  it("usa legado quando o capabilities sinaliza rollback_forced para a thread", async () => {
    process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED = "1";
    fetchMock
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify(
            payloadCapabilities({
              mobile_v2_thread_enabled: true,
              thread_reason: "rollback_forced",
              thread_rollout_state: "rollback_forced",
              thread_rollback_forced: true,
            }),
          ),
        ),
      )
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify({
            laudo_id: 21,
            itens: [],
            cursor_proximo: null,
            cursor_ultimo_id: 44,
            tem_mais: false,
            estado: "relatorio_ativo",
            permite_edicao: true,
            permite_reabrir: false,
            laudo_card: null,
            resumo: {
              atualizado_em: "2026-03-21T10:00:00Z",
              total_mensagens: 4,
              mensagens_nao_lidas: 1,
              pendencias_abertas: 1,
              pendencias_resolvidas: 0,
              ultima_mensagem_id: 44,
              ultima_mensagem_em: "2026-03-21T10:00:00Z",
              ultima_mensagem_preview: "Mesa",
              ultima_mensagem_tipo: "humano_eng",
              ultima_mensagem_remetente_id: 7,
            },
            sync: {
              modo: "full",
              apos_id: null,
              cursor_ultimo_id: 44,
            },
          }),
        ),
      );

    await expect(
      carregarMensagensMesaMobile("token-123", 21),
    ).resolves.toMatchObject({
      laudo_id: 21,
      cursor_ultimo_id: 44,
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/app/api/mobile/v2/capabilities",
    );
    expect(fetchMock.mock.calls[1][0]).toContain(
      "/app/api/laudo/21/mesa/mensagens",
    );
    const [, requestInit] = fetchMock.mock.calls[1];
    expect(requestInit.headers.get("X-Tariel-Mobile-V2-Fallback-Reason")).toBe(
      "rollback_forced",
    );
  });

  it("faz fallback do feed V2 para o legado quando o endpoint responde 404", async () => {
    process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED = "1";
    fetchMock
      .mockResolvedValueOnce(
        criarResposta(JSON.stringify(payloadCapabilities())),
      )
      .mockResolvedValueOnce(
        criarResposta(JSON.stringify({ detail: "not found" }), { status: 404 }),
      )
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify({
            cursor_atual: "2026-03-21T11:00:00Z",
            laudo_ids: [21, 22],
            itens: [{ laudo_id: 22, resumo: { total_mensagens: 3 } }],
          }),
        ),
      );

    await expect(
      carregarFeedMesaMobile("token-123", {
        laudoIds: [21, 22],
        cursorAtualizadoEm: "2026-03-21T10:00:00Z",
      }),
    ).resolves.toMatchObject({
      cursor_atual: "2026-03-21T11:00:00Z",
      laudo_ids: [21, 22],
    });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/app/api/mobile/v2/capabilities",
    );
    expect(fetchMock.mock.calls[1][0]).toContain(
      "/app/api/mobile/v2/mesa/feed",
    );
    expect(fetchMock.mock.calls[2][0]).toContain("/app/api/mobile/mesa/feed");
    const [, requestInit] = fetchMock.mock.calls[2];
    expect(requestInit.headers.get("X-Tariel-Mobile-V2-Fallback-Reason")).toBe(
      "http_404",
    );
    expect(
      requestInit.headers.get("X-Tariel-Mobile-V2-Capabilities-Version"),
    ).toBe("2026-03-25.09c");
    expect(requestInit.headers.get("X-Tariel-Mobile-V2-Rollout-Bucket")).toBe(
      "12",
    );
  });

  it("expõe o trace do feed quando a central tenta V2 e cai em fallback legado", async () => {
    process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED = "1";
    const traces: Array<Record<string, unknown>> = [];
    fetchMock
      .mockResolvedValueOnce(
        criarResposta(JSON.stringify(payloadCapabilities())),
      )
      .mockResolvedValueOnce(
        criarResposta(JSON.stringify({ detail: "not found" }), { status: 404 }),
      )
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify({
            cursor_atual: "2026-03-21T11:00:00Z",
            laudo_ids: [80],
            itens: [],
          }),
        ),
      );

    await carregarFeedMesaMobile("token-123", {
      laudoIds: [80],
      onRequestTrace: (trace) => {
        traces.push(trace as unknown as Record<string, unknown>);
      },
    });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    const [, requestInit] = fetchMock.mock.calls[1];
    expect(requestInit.headers.get("X-Tariel-Mobile-Central-Trace")).toMatch(
      /^feed-/,
    );
    expect(traces[0]).toMatchObject({
      contractFlagEnabled: true,
      routeDecision: "v2",
      phase: "intent_created",
    });
    expect(traces.at(-1)).toMatchObject({
      actualRoute: "legacy",
      attemptSequence: ["v2", "legacy"],
      deliveryMode: "legacy",
      fallbackReason: "http_404",
      phase: "response_received",
      responseStatus: 200,
    });
  });

  it("invalida o cache de capabilities depois de fallback do feed V2", async () => {
    process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED = "1";
    fetchMock
      .mockResolvedValueOnce(
        criarResposta(JSON.stringify(payloadCapabilities())),
      )
      .mockResolvedValueOnce(
        criarResposta(JSON.stringify({ detail: "not found" }), { status: 404 }),
      )
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify({
            cursor_atual: "2026-03-21T11:00:00Z",
            laudo_ids: [21],
            itens: [{ laudo_id: 21, resumo: { total_mensagens: 3 } }],
          }),
        ),
      )
      .mockResolvedValueOnce(
        criarResposta(JSON.stringify(payloadCapabilities())),
      )
      .mockResolvedValueOnce(
        criarResposta(JSON.stringify({ detail: "not found" }), { status: 404 }),
      )
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify({
            cursor_atual: "2026-03-21T11:10:00Z",
            laudo_ids: [21],
            itens: [{ laudo_id: 21, resumo: { total_mensagens: 4 } }],
          }),
        ),
      );

    await carregarFeedMesaMobile("token-123", {
      laudoIds: [21],
      cursorAtualizadoEm: "2026-03-21T10:00:00Z",
    });
    await carregarFeedMesaMobile("token-123", {
      laudoIds: [21],
      cursorAtualizadoEm: "2026-03-21T10:10:00Z",
    });

    expect(fetchMock).toHaveBeenCalledTimes(6);
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/app/api/mobile/v2/capabilities",
    );
    expect(fetchMock.mock.calls[3][0]).toContain(
      "/app/api/mobile/v2/capabilities",
    );
  });

  it("faz fallback da thread V2 para o legado quando o payload viola a visibilidade do Inspetor", async () => {
    process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED = "1";
    fetchMock
      .mockResolvedValueOnce(
        criarResposta(JSON.stringify(payloadCapabilities())),
      )
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify({
            contract_name: "MobileInspectorThreadV2",
            contract_version: "v2",
            tenant_id: "tenant-1",
            source_channel: "android_mesa_thread_v2",
            case_id: "case-21",
            legacy_laudo_id: 21,
            thread_id: "thread-21",
            visibility_scope: "inspetor_mobile",
            case_status: "needs_reviewer",
            legacy_public_state: "aguardando",
            allows_edit: true,
            allows_reopen: false,
            case_card: null,
            total_visible_messages: 1,
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
              total_visible_interactions: 1,
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
            provenance_summary: null,
            policy_summary: null,
            document_readiness: null,
            document_blockers: [],
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
              mode: "full",
              cursor_after_id: null,
              next_cursor_id: null,
              cursor_last_message_id: 301,
              has_more: false,
            },
            sync_policy: {
              contract_name: "MobileInspectorSyncPolicyV2",
              contract_version: "v2",
              policy_name: "android_thread_sync_policy",
              mode: "full",
              offline_queue_supported: true,
              incremental_sync_supported: false,
              attachment_sync_supported: true,
              visibility_scope: "inspetor_mobile",
            },
            timestamp: "2026-03-25T10:31:00Z",
            items: [
              {
                contract_name: "MobileInspectorThreadMessageV2",
                contract_version: "v2",
                interaction_id: "interaction-301",
                message_id: 301,
                actor_role: "ia",
                actor_kind: "ai",
                origin_kind: "ai",
                content_kind: "text",
                legacy_message_type: "ia",
                text_preview: "Sugestão interna",
                timestamp: "2026-03-25T10:31:00Z",
                sender_id: 7,
                client_message_id: null,
                reference_message_id: null,
                is_read: false,
                has_attachments: false,
                review_feedback_visible: false,
                review_marker_visible: false,
                highlight_marker: false,
                pending_open: false,
                pending_resolved: false,
                visibility_scope: "inspetor_mobile",
                content_text: "Sugestão interna",
                display_date: "25/03/2026",
                resolved_at: null,
                resolved_at_label: "",
                resolved_by_name: "",
                attachments: [],
                delivery_status: "persisted",
                order_index: 0,
                cursor_id: 301,
                is_delta_item: false,
              },
            ],
          }),
        ),
      )
      .mockResolvedValueOnce(
        criarResposta(
          JSON.stringify({
            laudo_id: 21,
            itens: [],
            cursor_proximo: null,
            cursor_ultimo_id: 44,
            tem_mais: false,
            estado: "relatorio_ativo",
            permite_edicao: true,
            permite_reabrir: false,
            laudo_card: null,
            resumo: {
              atualizado_em: "2026-03-21T10:00:00Z",
              total_mensagens: 4,
              mensagens_nao_lidas: 1,
              pendencias_abertas: 1,
              pendencias_resolvidas: 0,
              ultima_mensagem_id: 44,
              ultima_mensagem_em: "2026-03-21T10:00:00Z",
              ultima_mensagem_preview: "Mesa",
              ultima_mensagem_tipo: "humano_eng",
              ultima_mensagem_remetente_id: 7,
            },
            sync: {
              modo: "full",
              apos_id: null,
              cursor_ultimo_id: 44,
            },
          }),
        ),
      );

    await expect(
      carregarMensagensMesaMobile("token-123", 21),
    ).resolves.toMatchObject({
      laudo_id: 21,
      cursor_ultimo_id: 44,
      resumo: { total_mensagens: 4 },
    });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/app/api/mobile/v2/capabilities",
    );
    expect(fetchMock.mock.calls[1][0]).toContain(
      "/app/api/mobile/v2/laudo/21/mesa/mensagens",
    );
    expect(fetchMock.mock.calls[2][0]).toContain(
      "/app/api/laudo/21/mesa/mensagens",
    );
    const [, requestInit] = fetchMock.mock.calls[2];
    expect(requestInit.headers.get("X-Tariel-Mobile-V2-Fallback-Reason")).toBe(
      "visibility_violation",
    );
    expect(
      requestInit.headers.get("X-Tariel-Mobile-V2-Capabilities-Version"),
    ).toBe("2026-03-25.09c");
    expect(requestInit.headers.get("X-Tariel-Mobile-V2-Rollout-Bucket")).toBe(
      "12",
    );
  });
});
