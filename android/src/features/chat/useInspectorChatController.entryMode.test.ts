import { act, renderHook } from "@testing-library/react-native";
import { Alert } from "react-native";

jest.mock("../../config/api", () => ({
  carregarGateQualidadeLaudoMobile: jest.fn(),
  carregarLaudosMobile: jest.fn(),
  carregarMensagensLaudo: jest.fn(),
  carregarStatusLaudo: jest.fn(),
  finalizarLaudoMobile: jest.fn(),
  reabrirLaudoMobile: jest.fn(),
  salvarGuidedInspectionDraftMobile: jest.fn(),
}));

jest.mock("./messageSendFlows", () => ({
  sendInspectorMessageFlow: jest.fn(),
}));

jest.mock("./network", () => ({
  gateHeavyTransfer: jest.fn(async () => ({ allowed: true, reason: "" })),
}));

jest.mock("./voice", () => ({
  speakAssistantResponse: jest.fn(),
}));

import {
  carregarGateQualidadeLaudoMobile,
  carregarLaudosMobile,
  carregarMensagensLaudo,
  carregarStatusLaudo,
  finalizarLaudoMobile,
  reabrirLaudoMobile,
  salvarGuidedInspectionDraftMobile,
} from "../../config/api";
import { sendInspectorMessageFlow } from "./messageSendFlows";
import { gateHeavyTransfer } from "./network";
import type {
  MobileLaudoCard,
  MobileQualityGateResponse,
} from "../../types/mobile";
import type { MobileReadCache } from "../common/readCacheTypes";
import type { ChatState, OfflinePendingMessage } from "./types";
import { createGuidedInspectionDraft } from "../inspection/guidedInspection";
import { useInspectorChatController } from "./useInspectorChatController";
import { normalizarConversa, normalizarModoChat } from "./conversationHelpers";

function criarLaudoCard(overrides?: Partial<MobileLaudoCard>): MobileLaudoCard {
  return {
    id: 88,
    titulo: "Laudo 88",
    preview: "preview",
    pinado: false,
    data_iso: "2026-04-06T14:10:00.000Z",
    data_br: "06/04/2026",
    hora_br: "14:10",
    tipo_template: "nr35",
    status_revisao: "em_andamento",
    status_card: "aberto",
    status_card_label: "Em andamento",
    permite_edicao: true,
    permite_reabrir: false,
    possui_historico: true,
    entry_mode_preference: "auto_recommended",
    entry_mode_effective: "evidence_first",
    entry_mode_reason: "existing_case_state",
    ...overrides,
  };
}

function criarCacheLeitura(
  guidedDrafts: MobileReadCache["guidedInspectionDrafts"] = {},
): MobileReadCache {
  return {
    bootstrap: null,
    laudos: [],
    conversaAtual: null,
    conversasPorLaudo: {},
    mesaPorLaudo: {},
    guidedInspectionDrafts: guidedDrafts,
    chatDrafts: {},
    mesaDrafts: {},
    chatAttachmentDrafts: {},
    mesaAttachmentDrafts: {},
    updatedAt: "",
  };
}

function criarParams(
  overrides?: Partial<
    Parameters<
      typeof useInspectorChatController<OfflinePendingMessage, MobileReadCache>
    >[0]
  >,
) {
  const startGuidedInspection = jest.fn();
  const cacheLeitura = criarCacheLeitura();

  return {
    session: {
      accessToken: "token-123",
      bootstrap: {
        ok: true,
        app: {
          nome: "Tariel",
          portal: "inspetor",
          api_base_url: "https://tariel.test",
          suporte_whatsapp: "",
        },
        usuario: {
          id: 1,
          nome_completo: "Gabriel",
          email: "gabriel@tariel.test",
          telefone: "",
          foto_perfil_url: "",
          empresa_nome: "Tariel",
          empresa_id: 1,
          nivel_acesso: 1,
        },
      },
    },
    sessionLoading: false,
    activeThread: "chat" as const,
    entryModePreference: "auto_recommended" as const,
    rememberLastCaseMode: true,
    statusApi: "online",
    wifiOnlySync: false,
    aiRequestConfig: {
      model: "equilibrado" as const,
      mode: "detalhado" as const,
      responseStyle: "padrão" as const,
      responseLanguage: "Português" as const,
      memoryEnabled: true,
      learningOptIn: false,
      tone: "profissional" as const,
      temperature: 0.2,
      messagePrefix: "",
      summaryLabel: "IA",
      fallbackNotes: [],
    },
    speechSettings: {
      enabled: false,
      autoTranscribe: false,
      autoReadResponses: false,
      voiceLanguage: "Português" as const,
      speechRate: 1,
      voiceId: "",
    },
    cacheLeitura,
    conversation: null,
    guidedInspectionDraft: null,
    setConversation: jest.fn(),
    laudosDisponiveis: [],
    setLaudosDisponiveis: jest.fn(),
    laudosFixadosIds: [],
    historicoOcultoIds: [],
    laudoMesaCarregado: null,
    setLaudoMesaCarregado: jest.fn(),
    setMensagensMesa: jest.fn(),
    setErroMesa: jest.fn(),
    setMensagemMesa: jest.fn(),
    setAnexoMesaRascunho: jest.fn(),
    clearMesaReference: jest.fn(),
    clearGuidedInspectionDraft: jest.fn(),
    startGuidedInspection,
    onSetActiveThread: jest.fn(),
    message: "",
    setMessage: jest.fn(),
    attachmentDraft: null,
    setAttachmentDraft: jest.fn(),
    setErrorConversation: jest.fn(),
    qualityGateLaudoId: null,
    qualityGatePayload: null,
    qualityGateReason: "",
    setQualityGateLaudoId: jest.fn(),
    setQualityGateLoading: jest.fn(),
    setQualityGateNotice: jest.fn(),
    setQualityGatePayload: jest.fn(),
    setQualityGateReason: jest.fn(),
    setQualityGateSubmitting: jest.fn(),
    setQualityGateVisible: jest.fn(),
    setSendingMessage: jest.fn(),
    setLoadingConversation: jest.fn(),
    setSyncConversation: jest.fn(),
    setLoadingLaudos: jest.fn(),
    setErrorLaudos: jest.fn(),
    setThreadHomeVisible: jest.fn(),
    highlightedMessageId: null,
    setHighlightedMessageId: jest.fn(),
    layoutVersion: 0,
    setLayoutVersion: jest.fn(),
    setCaseCreationState: jest.fn(),
    scrollRef: { current: null },
    setFilaOffline: jest.fn(),
    setStatusApi: jest.fn(),
    setUsandoCacheOffline: jest.fn(),
    setCacheLeitura: jest.fn(),
    carregarMesaAtual: jest.fn(),
    aplicarPreferenciasLaudos: jest.fn((itens) => itens),
    chaveCacheLaudo: jest.fn((laudoId) => `laudo:${laudoId ?? "rascunho"}`),
    chaveRascunho: jest.fn(
      (thread, laudoId) => `${thread}:${laudoId ?? "rascunho"}`,
    ),
    erroSugereModoOffline: jest.fn(() => false),
    normalizarConversa,
    atualizarResumoLaudoAtual: jest.fn((estado) => estado),
    criarConversaNova: jest.fn(() => ({
      laudoId: null,
      estado: "sem_relatorio",
      statusCard: "aberto",
      permiteEdicao: true,
      permiteReabrir: false,
      laudoCard: null,
      modo: "detalhado",
      mensagens: [],
    })),
    podeEditarConversaNoComposer: jest.fn(() => true),
    textoFallbackAnexo: jest.fn(() => "Anexo"),
    normalizarModoChat,
    inferirSetorConversa: jest.fn(() => "geral"),
    montarHistoricoParaEnvio: jest.fn(() => []),
    criarMensagemAssistenteServidor: jest.fn(() => null),
    criarItemFilaOffline: jest.fn(
      (params) =>
        ({
          id: "offline-1",
          channel: params.channel,
          operation: params.operation || "message",
          laudoId: params.laudoId,
          text: params.text,
          createdAt: new Date().toISOString(),
          title: params.title,
          attachment: params.attachment,
          referenceMessageId: null,
          qualityGateDecision: params.qualityGateDecision || null,
          attempts: 0,
          lastAttemptAt: "",
          lastError: "",
          nextRetryAt: "",
          aiMode: params.aiMode,
          aiSummary: params.aiSummary,
          aiMessagePrefix: params.aiMessagePrefix,
        }) satisfies OfflinePendingMessage,
    ),
    ...overrides,
  };
}

describe("useInspectorChatController entry mode", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (gateHeavyTransfer as jest.Mock).mockResolvedValue({
      allowed: true,
      reason: "",
    });
    (carregarStatusLaudo as jest.Mock).mockResolvedValue({
      estado: "sem_relatorio",
      laudo_id: null,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: null,
      modo: "detalhado",
    });
    (carregarLaudosMobile as jest.Mock).mockResolvedValue({
      ok: true,
      itens: [],
    });
    (salvarGuidedInspectionDraftMobile as jest.Mock).mockResolvedValue({
      ok: true,
      laudo_id: 88,
      guided_inspection_draft: null,
    });
    (carregarGateQualidadeLaudoMobile as jest.Mock).mockResolvedValue({
      codigo: "GATE_QUALIDADE_OK",
      aprovado: true,
      mensagem: "Gate aprovado.",
      tipo_template: "padrao",
      template_nome: "Padrão",
      resumo: {},
      itens: [],
      faltantes: [],
      roteiro_template: null,
      human_override_policy: null,
    });
    (finalizarLaudoMobile as jest.Mock).mockResolvedValue({
      success: true,
      laudo_id: 88,
      message: "Caso enviado para a Mesa Avaliadora a partir do mobile.",
      estado: "aguardando",
      status_card: "aguardando",
      permite_edicao: false,
      permite_reabrir: false,
      laudo_card: null,
    });
  });

  it("restaura o draft guiado do caso ao selecionar um laudo evidence_first", async () => {
    const draft = createGuidedInspectionDraft();
    const laudoCard = criarLaudoCard();
    const params = criarParams({
      cacheLeitura: criarCacheLeitura({
        "laudo:88": draft,
      }),
    });
    (carregarMensagensLaudo as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 88,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: laudoCard,
      modo: "detalhado",
      itens: [],
      cursor_proximo: null,
      tem_mais: false,
      limite: 50,
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleSelecionarLaudo(laudoCard);
    });

    expect(params.startGuidedInspection).toHaveBeenCalledWith({
      draft,
      ignoreActiveConversation: true,
      tipoTemplate: "nr35",
    });
  });

  it("na inicializacao da sessao hidrata a lista sem autoabrir o caso atual", async () => {
    const params = criarParams({
      conversation: null,
    });
    (carregarStatusLaudo as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 88,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: criarLaudoCard(),
      modo: "detalhado",
    });

    renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {});

    expect(carregarLaudosMobile).toHaveBeenCalledWith("token-123");
    expect(carregarStatusLaudo).not.toHaveBeenCalled();
    expect(params.startGuidedInspection).not.toHaveBeenCalled();
    expect(params.setConversation).not.toHaveBeenCalled();
  });

  it("recarrega a thread ativa na inicializacao quando ja existe laudo aberto em runtime", async () => {
    const laudoCard = criarLaudoCard();
    const params = criarParams({
      conversation: {
        laudoId: 88,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard,
        modo: "detalhado",
        mensagens: [],
      },
    });
    (carregarStatusLaudo as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 88,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: laudoCard,
      modo: "detalhado",
    });
    (carregarMensagensLaudo as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 88,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: laudoCard,
      modo: "detalhado",
      itens: [],
      cursor_proximo: null,
      tem_mais: false,
      limite: 50,
    });

    renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {});

    expect(carregarStatusLaudo).toHaveBeenCalledWith("token-123");
    expect(carregarMensagensLaudo).toHaveBeenCalledWith("token-123", 88);
  });

  it("restaura o draft guiado vindo do backend quando o cache local nao existe", async () => {
    const draft = createGuidedInspectionDraft();
    const laudoCard = criarLaudoCard({ id: 109, tipo_template: "nr13" });
    const params = criarParams();
    let cacheAtual = params.cacheLeitura;
    params.setCacheLeitura = jest.fn((updater) => {
      cacheAtual =
        typeof updater === "function" ? updater(cacheAtual) : updater;
    });
    (carregarMensagensLaudo as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 109,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: laudoCard,
      modo: "detalhado",
      guided_inspection_draft: {
        template_key: draft.templateKey,
        template_label: draft.templateLabel,
        started_at: draft.startedAt,
        current_step_index: draft.currentStepIndex,
        completed_step_ids: draft.completedStepIds,
        checklist: draft.checklist.map((item) => ({
          id: item.id,
          title: item.title,
          prompt: item.prompt,
          evidence_hint: item.evidenceHint,
        })),
      },
      itens: [],
      cursor_proximo: null,
      tem_mais: false,
      limite: 50,
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleSelecionarLaudo(laudoCard);
    });

    expect(params.startGuidedInspection).toHaveBeenCalledWith({
      draft,
      ignoreActiveConversation: true,
      tipoTemplate: "nr13",
    });
    expect(cacheAtual.guidedInspectionDrafts?.["laudo:109"]).toEqual(draft);
  });

  it("mescla o bundle remoto do draft guiado sem perder o progresso local", async () => {
    const draftLocal = createGuidedInspectionDraft();
    draftLocal.currentStepIndex = 1;
    draftLocal.completedStepIds = ["identificacao_ativo"];
    const laudoCard = criarLaudoCard({ id: 205, tipo_template: "padrao" });
    let cacheAtual = criarCacheLeitura({
      "laudo:205": draftLocal,
    });
    const params = criarParams({
      cacheLeitura: cacheAtual,
    });
    params.setCacheLeitura = jest.fn((updater) => {
      cacheAtual =
        typeof updater === "function" ? updater(cacheAtual) : updater;
    });
    (carregarMensagensLaudo as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 205,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: laudoCard,
      modo: "detalhado",
      guided_inspection_draft: {
        template_key: draftLocal.templateKey,
        template_label: draftLocal.templateLabel,
        started_at: draftLocal.startedAt,
        current_step_index: draftLocal.currentStepIndex,
        completed_step_ids: draftLocal.completedStepIds,
        checklist: draftLocal.checklist.map((item) => ({
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
        ],
        mesa_handoff: {
          required: true,
          review_mode: "mesa_required",
          reason_code: "policy_review_mode",
          recorded_at: "2026-04-06T22:31:30.000Z",
          step_id: "identificacao_ativo",
          step_title: "Identificacao do ativo e da area",
        },
      },
      itens: [],
      cursor_proximo: null,
      tem_mais: false,
      limite: 50,
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleSelecionarLaudo(laudoCard);
    });

    expect(cacheAtual.guidedInspectionDrafts?.["laudo:205"]).toMatchObject({
      currentStepIndex: 1,
      completedStepIds: ["identificacao_ativo"],
      evidenceRefs: [
        expect.objectContaining({ messageId: 91, attachmentKind: "image" }),
      ],
      mesaHandoff: expect.objectContaining({ reviewMode: "mesa_required" }),
    });
  });

  it("abre a coleta guiada do template do caso quando nao existe draft cacheado", async () => {
    const laudoCard = criarLaudoCard({ id: 99, tipo_template: "nr12maquinas" });
    const params = criarParams();
    (carregarMensagensLaudo as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 99,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: laudoCard,
      modo: "detalhado",
      itens: [],
      cursor_proximo: null,
      tem_mais: false,
      limite: 50,
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleSelecionarLaudo(laudoCard);
    });

    expect(params.startGuidedInspection).toHaveBeenCalledWith({
      ignoreActiveConversation: true,
      tipoTemplate: "nr12maquinas",
    });
  });

  it("permite alternar explicitamente o caso atual para coleta guiada sem duplicar laudo", () => {
    const draft = createGuidedInspectionDraft();
    const params = criarParams({
      cacheLeitura: criarCacheLeitura({
        "laudo:88": draft,
      }),
      conversation: {
        laudoId: 88,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: criarLaudoCard(),
        modo: "detalhado",
        mensagens: [],
      },
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    act(() => {
      result.current.actions.handleAbrirColetaGuiadaAtual();
    });

    expect(params.startGuidedInspection).toHaveBeenCalledWith({
      draft,
      ignoreActiveConversation: true,
      tipoTemplate: "nr35",
    });
  });

  it("preserva o draft guiado cacheado ao sair do modo guiado no mesmo caso", async () => {
    const draft = createGuidedInspectionDraft();
    let cacheAtual = criarCacheLeitura({
      "laudo:88": draft,
    });
    const params = criarParams({
      cacheLeitura: cacheAtual,
      conversation: {
        laudoId: 88,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: criarLaudoCard(),
        modo: "detalhado",
        mensagens: [],
      },
      guidedInspectionDraft: null,
    });
    params.setCacheLeitura = jest.fn((updater) => {
      cacheAtual =
        typeof updater === "function" ? updater(cacheAtual) : updater;
    });

    renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {});

    expect(cacheAtual.guidedInspectionDrafts?.["laudo:88"]).toEqual(draft);
  });

  it("sincroniza o draft guiado canonico quando o caso ja tem laudo_id", async () => {
    const draft = createGuidedInspectionDraft();
    const params = criarParams({
      conversation: {
        laudoId: 88,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: criarLaudoCard(),
        modo: "detalhado",
        mensagens: [],
      },
      guidedInspectionDraft: draft,
    });
    (salvarGuidedInspectionDraftMobile as jest.Mock).mockResolvedValue({
      ok: true,
      laudo_id: 88,
      guided_inspection_draft: {
        template_key: draft.templateKey,
        template_label: draft.templateLabel,
        started_at: draft.startedAt,
        current_step_index: draft.currentStepIndex,
        completed_step_ids: draft.completedStepIds,
        checklist: draft.checklist.map((item) => ({
          id: item.id,
          title: item.title,
          prompt: item.prompt,
          evidence_hint: item.evidenceHint,
        })),
        evidence_bundle_kind: "case_thread",
        evidence_refs: [],
        mesa_handoff: null,
      },
    });

    renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {});

    expect(salvarGuidedInspectionDraftMobile).toHaveBeenCalledWith(
      "token-123",
      88,
      {
        guided_inspection_draft: {
          template_key: draft.templateKey,
          template_label: draft.templateLabel,
          started_at: draft.startedAt,
          current_step_index: draft.currentStepIndex,
          completed_step_ids: draft.completedStepIds,
          checklist: draft.checklist.map((item) => ({
            id: item.id,
            title: item.title,
            prompt: item.prompt,
            evidence_hint: item.evidenceHint,
          })),
          evidence_bundle_kind: "case_thread",
          evidence_refs: [],
          mesa_handoff: null,
        },
      },
    );
  });

  it("reaproveita o mesmo fluxo de envio do chat quando a coleta guiada esta ativa", async () => {
    const draft = createGuidedInspectionDraft();
    const params = criarParams({
      conversation: {
        laudoId: 88,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: criarLaudoCard(),
        modo: "detalhado",
        mensagens: [],
      },
      guidedInspectionDraft: draft,
      message: "Registrar etapa atual",
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleEnviarMensagem();
    });

    expect(sendInspectorMessageFlow).toHaveBeenCalledWith(
      expect.objectContaining({
        snapshotConversa: expect.objectContaining({ laudoId: 88 }),
        guidedInspectionDraft: draft,
      }),
    );
  });

  it("guarda o snapshot guiado quando a evidencia entra na fila offline local", async () => {
    (gateHeavyTransfer as jest.Mock).mockResolvedValue({
      allowed: false,
      reason: "Wi-Fi necessario para anexos.",
    });
    const draft = createGuidedInspectionDraft();
    const criarItemFilaOffline = jest.fn(
      (params) =>
        ({
          id: "offline-1",
          channel: params.channel,
          operation: params.operation || "message",
          laudoId: params.laudoId,
          text: params.text,
          createdAt: new Date().toISOString(),
          title: params.title,
          attachment: params.attachment,
          referenceMessageId: null,
          qualityGateDecision: params.qualityGateDecision || null,
          guidedInspectionDraft: params.guidedInspectionDraft || null,
          attempts: 0,
          lastAttemptAt: "",
          lastError: "",
          nextRetryAt: "",
          aiMode: params.aiMode,
          aiSummary: params.aiSummary,
          aiMessagePrefix: params.aiMessagePrefix,
        }) satisfies OfflinePendingMessage,
    );
    const params = criarParams({
      conversation: {
        laudoId: 88,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: criarLaudoCard(),
        modo: "detalhado",
        mensagens: [],
      },
      guidedInspectionDraft: draft,
      message: "Registrar etapa atual",
      attachmentDraft: {
        kind: "image",
        label: "Foto",
        resumo: "Vista geral",
        dadosImagem: "base64",
        previewUri: "file:///preview.png",
        fileUri: "file:///imagem.png",
        mimeType: "image/png",
      },
      criarItemFilaOffline,
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleEnviarMensagem();
    });

    const queueUpdater = (params.setFilaOffline as jest.Mock).mock
      .calls[0]?.[0] as (
      current: OfflinePendingMessage[],
    ) => OfflinePendingMessage[];
    const queuedItems = queueUpdater([]);

    expect(criarItemFilaOffline).toHaveBeenCalledWith(
      expect.objectContaining({
        guidedInspectionDraft: expect.objectContaining({
          template_key: "padrao",
          current_step_index: 0,
        }),
      }),
    );
    expect(queuedItems[0]?.guidedInspectionDraft?.template_key).toBe("padrao");
  });

  it("marca a criação do caso durante o primeiro envio e confirma quando o laudo nasce", async () => {
    const setCaseCreationState = jest.fn();
    const setConversation = jest.fn();
    const params = criarParams({
      conversation: {
        laudoId: null,
        estado: "sem_relatorio",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: null,
        modo: "detalhado",
        mensagens: [],
      },
      message: "Abrir inspeção",
      setCaseCreationState,
      setConversation,
    });
    (sendInspectorMessageFlow as jest.Mock).mockImplementation(async (args) => {
      args.onApplyOptimisticMessage(
        {
          id: 1201,
          papel: "usuario",
          texto: "Abrir inspeção",
          tipo: "texto",
        },
        "detalhado",
      );
      args.onApplyAssistantResponse(
        {
          laudoId: 144,
          laudoCard: criarLaudoCard({
            id: 144,
            status_card: "aberto",
            status_card_label: "Em andamento",
          }),
          assistantText: "Caso aberto.",
          modo: "detalhado",
          citacoes: [],
          confiancaIa: null,
          events: [],
        },
        null,
      );
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleEnviarMensagem();
    });

    expect(setCaseCreationState).toHaveBeenNthCalledWith(1, "creating");
    expect(setCaseCreationState).toHaveBeenNthCalledWith(2, "created");
  });

  it("marca que a criação do caso ficou pendente na fila local quando o primeiro envio é barrado offline", async () => {
    (gateHeavyTransfer as jest.Mock).mockResolvedValue({
      allowed: false,
      reason: "Wi-Fi necessario para anexos.",
    });
    const setCaseCreationState = jest.fn();
    const params = criarParams({
      conversation: {
        laudoId: null,
        estado: "sem_relatorio",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: null,
        modo: "detalhado",
        mensagens: [],
      },
      message: "Abrir inspeção offline",
      attachmentDraft: {
        kind: "image",
        label: "Foto",
        resumo: "Vista geral",
        dadosImagem: "base64",
        previewUri: "file:///preview.png",
        fileUri: "file:///imagem.png",
        mimeType: "image/png",
      },
      setCaseCreationState,
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleEnviarMensagem();
    });

    expect(setCaseCreationState).toHaveBeenCalledWith("queued_offline");
  });

  it("marca erro quando o primeiro envio falha antes de criar o caso", async () => {
    const setCaseCreationState = jest.fn();
    const params = criarParams({
      conversation: {
        laudoId: null,
        estado: "sem_relatorio",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: null,
        modo: "detalhado",
        mensagens: [],
      },
      message: "Abrir inspeção",
      setCaseCreationState,
    });
    (sendInspectorMessageFlow as jest.Mock).mockImplementation(async (args) => {
      args.onRestoreDraft("Abrir inspeção", null);
      args.onSetErroConversa("Falha ao criar o caso.");
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleEnviarMensagem();
    });

    expect(setCaseCreationState).toHaveBeenNthCalledWith(1, "creating");
    expect(setCaseCreationState).toHaveBeenNthCalledWith(2, "error");
  });

  it("preserva o lifecycle canonico durante o envio otimista e a resposta do chat", async () => {
    const conversation: ChatState = {
      laudoId: 88,
      estado: "relatorio_ativo",
      statusCard: "aberto",
      permiteEdicao: true,
      permiteReabrir: false,
      laudoCard: criarLaudoCard({
        status_card: "aberto",
        status_card_label: "Em andamento",
        case_lifecycle_status: "laudo_em_coleta",
        case_workflow_mode: "laudo_guiado",
        active_owner_role: "inspetor",
        allowed_next_lifecycle_statuses: ["aguardando_mesa", "aprovado"],
        allowed_lifecycle_transitions: [
          {
            target_status: "aguardando_mesa",
            transition_kind: "review",
            label: "Aguardando mesa",
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
        allowed_surface_actions: ["chat_finalize"],
      }),
      caseLifecycleStatus: "laudo_em_coleta",
      caseWorkflowMode: "laudo_guiado",
      activeOwnerRole: "inspetor",
      allowedNextLifecycleStatuses: ["aguardando_mesa", "aprovado"],
      allowedLifecycleTransitions: [
        {
          target_status: "aguardando_mesa",
          transition_kind: "review",
          label: "Aguardando mesa",
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
      allowedSurfaceActions: ["chat_finalize"],
      reviewPackage: null,
      modo: "detalhado",
      mensagens: [],
    };
    const setConversation = jest.fn();
    const params = criarParams({
      conversation,
      message: "Atualizacao da inspeção",
      setConversation,
    });
    (sendInspectorMessageFlow as jest.Mock).mockImplementation(async (args) => {
      args.onApplyOptimisticMessage(
        {
          id: 901,
          papel: "usuario",
          texto: "Atualizacao da inspeção",
          tipo: "texto",
        },
        "detalhado",
      );
      args.onApplyAssistantResponse(
        {
          laudoId: 88,
          laudoCard: criarLaudoCard({
            status_card: "aguardando",
            status_card_label: "Aguardando",
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
            ],
            allowed_surface_actions: ["mesa_approve", "mesa_return"],
          }),
          assistantText: "Caso enviado para a mesa.",
          modo: "detalhado",
          citacoes: [],
          confiancaIa: null,
          events: [],
        },
        null,
      );
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleEnviarMensagem();
    });

    const conversationUpdaters = setConversation.mock.calls
      .map((call) => call[0])
      .filter(
        (
          value,
        ): value is (
          current: typeof conversation | null,
        ) => typeof conversation => typeof value === "function",
      );

    const optimisticUpdater = conversationUpdaters[0] as (
      current: typeof conversation | null,
    ) => typeof conversation;
    const optimisticState = optimisticUpdater(conversation);
    expect(optimisticState.caseLifecycleStatus).toBe("laudo_em_coleta");
    expect(optimisticState.caseWorkflowMode).toBe("laudo_guiado");
    expect(optimisticState.activeOwnerRole).toBe("inspetor");
    expect(optimisticState.allowedNextLifecycleStatuses).toEqual([
      "aguardando_mesa",
      "aprovado",
    ]);
    expect(
      optimisticState.allowedLifecycleTransitions?.map(
        (item) => item.target_status,
      ),
    ).toEqual(["aguardando_mesa", "aprovado"]);
    expect(optimisticState.allowedSurfaceActions).toEqual(["chat_finalize"]);

    const assistantUpdater = conversationUpdaters[1] as (
      current: typeof conversation | null,
    ) => typeof conversation;
    const assistantState = assistantUpdater(conversation);
    expect(assistantState.caseLifecycleStatus).toBe("aguardando_mesa");
    expect(assistantState.caseWorkflowMode).toBe("laudo_com_mesa");
    expect(assistantState.activeOwnerRole).toBe("mesa");
    expect(assistantState.allowedNextLifecycleStatuses).toEqual([
      "em_revisao_mesa",
      "devolvido_para_correcao",
      "aprovado",
    ]);
    expect(
      assistantState.allowedLifecycleTransitions?.map(
        (item) => item.target_status,
      ),
    ).toEqual(["em_revisao_mesa", "devolvido_para_correcao", "aprovado"]);
    expect(assistantState.allowedSurfaceActions).toEqual([
      "mesa_approve",
      "mesa_return",
    ]);
  });

  it("solicita a politica do PDF anterior ao reabrir um caso emitido", async () => {
    const alertSpy = jest
      .spyOn(Alert, "alert")
      .mockImplementation((_title, _message, buttons) => {
        const botaoOcultar = Array.isArray(buttons)
          ? buttons.find((button) => button.text === "Ocultar PDF anterior")
          : null;
        botaoOcultar?.onPress?.();
      });
    const params = criarParams({
      conversation: {
        laudoId: 88,
        estado: "aprovado",
        statusCard: "aprovado",
        permiteEdicao: false,
        permiteReabrir: true,
        laudoCard: criarLaudoCard({
          status_card: "aprovado",
          status_card_label: "Aprovado",
          case_lifecycle_status: "emitido",
          case_workflow_mode: "laudo_guiado",
          active_owner_role: "none",
          allowed_next_lifecycle_statuses: ["devolvido_para_correcao"],
          permite_edicao: false,
          permite_reabrir: true,
        }),
        caseLifecycleStatus: "emitido",
        caseWorkflowMode: "laudo_guiado",
        activeOwnerRole: "none",
        allowedNextLifecycleStatuses: ["devolvido_para_correcao"],
        modo: "detalhado",
        mensagens: [],
      },
    });
    (reabrirLaudoMobile as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 88,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      issued_document_policy_applied: "hide_from_case",
      had_previous_issued_document: true,
      previous_issued_document_visible_in_case: false,
      internal_learning_candidate_registered: true,
      laudo_card: criarLaudoCard({
        status_card: "aberto",
        status_card_label: "Em andamento",
        permite_edicao: true,
        permite_reabrir: false,
      }),
      modo: "detalhado",
    });
    (carregarStatusLaudo as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 88,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: criarLaudoCard({
        status_card: "aberto",
        status_card_label: "Em andamento",
        permite_edicao: true,
        permite_reabrir: false,
      }),
      modo: "detalhado",
    });
    (carregarMensagensLaudo as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 88,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: criarLaudoCard({
        status_card: "aberto",
        status_card_label: "Em andamento",
        permite_edicao: true,
        permite_reabrir: false,
      }),
      modo: "detalhado",
      itens: [],
      cursor_proximo: null,
      tem_mais: false,
      limite: 50,
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleReabrir();
    });

    expect(alertSpy).toHaveBeenCalled();
    expect(reabrirLaudoMobile).toHaveBeenCalledWith("token-123", 88, {
      issued_document_policy: "hide_from_case",
    });

    alertSpy.mockRestore();
  });

  it("nao solicita politica de PDF ao reabrir um caso apenas aprovado", async () => {
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation(jest.fn());
    const params = criarParams({
      conversation: {
        laudoId: 88,
        estado: "aprovado",
        statusCard: "aprovado",
        permiteEdicao: false,
        permiteReabrir: true,
        laudoCard: criarLaudoCard({
          status_card: "aprovado",
          status_card_label: "Aprovado",
          case_lifecycle_status: "aprovado",
          case_workflow_mode: "laudo_guiado",
          active_owner_role: "none",
          allowed_next_lifecycle_statuses: [
            "emitido",
            "devolvido_para_correcao",
          ],
          permite_edicao: false,
          permite_reabrir: true,
        }),
        caseLifecycleStatus: "aprovado",
        caseWorkflowMode: "laudo_guiado",
        activeOwnerRole: "none",
        allowedNextLifecycleStatuses: ["emitido", "devolvido_para_correcao"],
        modo: "detalhado",
        mensagens: [],
      },
    });
    (reabrirLaudoMobile as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 88,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: criarLaudoCard({
        status_card: "aberto",
        status_card_label: "Em andamento",
        permite_edicao: true,
        permite_reabrir: false,
      }),
      modo: "detalhado",
    });
    (carregarStatusLaudo as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 88,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: criarLaudoCard({
        status_card: "aberto",
        status_card_label: "Em andamento",
        permite_edicao: true,
        permite_reabrir: false,
      }),
      modo: "detalhado",
    });
    (carregarMensagensLaudo as jest.Mock).mockResolvedValue({
      estado: "relatorio_ativo",
      laudo_id: 88,
      status_card: "aberto",
      permite_edicao: true,
      permite_reabrir: false,
      laudo_card: criarLaudoCard({
        status_card: "aberto",
        status_card_label: "Em andamento",
        permite_edicao: true,
        permite_reabrir: false,
      }),
      modo: "detalhado",
      itens: [],
      cursor_proximo: null,
      tem_mais: false,
      limite: 50,
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleReabrir();
    });

    expect(alertSpy).not.toHaveBeenCalled();
    expect(reabrirLaudoMobile).toHaveBeenCalledWith("token-123", 88, undefined);

    alertSpy.mockRestore();
  });

  it("abre o quality gate usando o id do laudoCard quando a conversa ainda nao hidratou laudoId", async () => {
    const payload: MobileQualityGateResponse = {
      codigo: "blocked",
      aprovado: false,
      mensagem: "Ainda existem pendencias.",
      tipo_template: "nr35_linha_vida",
      template_nome: "NR-35 Linha de Vida",
      resumo: {
        evidencias: 4,
      },
      itens: [],
      faltantes: [],
      roteiro_template: null,
      report_pack_draft: null,
      review_mode_sugerido: "mesa_required",
      human_override_policy: null,
    };
    const params = criarParams({
      conversation: {
        laudoId: null,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: criarLaudoCard({
          id: 144,
          report_pack_draft: null,
        }),
        modo: "detalhado",
        mensagens: [],
      },
    });
    (carregarGateQualidadeLaudoMobile as jest.Mock).mockResolvedValue(payload);

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleAbrirQualityGate();
    });

    expect(params.setQualityGateVisible).toHaveBeenCalledWith(true);
    expect(params.setQualityGateLaudoId).toHaveBeenCalledWith(144);
    expect(carregarGateQualidadeLaudoMobile).toHaveBeenCalledWith(
      "token-123",
      144,
    );
    expect(params.setQualityGatePayload).toHaveBeenCalledWith(payload);
  });

  it("confirma a finalizacao usando o qualityGateLaudoId quando a conversa perde o laudoId", async () => {
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation(jest.fn());
    const payload: MobileQualityGateResponse = {
      codigo: "approved",
      aprovado: true,
      mensagem: "Caso pronto para finalizar.",
      tipo_template: "nr35_linha_vida",
      template_nome: "NR-35 Linha de Vida",
      resumo: {
        evidencias: 4,
      },
      itens: [],
      faltantes: [],
      roteiro_template: null,
      report_pack_draft: null,
      review_mode_sugerido: "mobile_autonomous",
      human_override_policy: null,
    };
    const params = criarParams({
      conversation: {
        laudoId: null,
        estado: "relatorio_ativo",
        statusCard: "aberto",
        permiteEdicao: true,
        permiteReabrir: false,
        laudoCard: criarLaudoCard({
          id: 144,
          report_pack_draft: null,
        }),
        modo: "detalhado",
        mensagens: [],
      },
      qualityGateLaudoId: 144,
      qualityGatePayload: payload,
    });
    (finalizarLaudoMobile as jest.Mock).mockResolvedValue({
      success: true,
      message: "Caso finalizado com sucesso.",
      laudo_id: 144,
      review_mode_final: "mobile_autonomous",
    });
    (carregarStatusLaudo as jest.Mock).mockResolvedValue({
      estado: "aprovado",
      laudo_id: 144,
      status_card: "aprovado",
      permite_edicao: false,
      permite_reabrir: true,
      laudo_card: criarLaudoCard({
        id: 144,
        status_card: "aprovado",
        status_card_label: "Aprovado",
        permite_edicao: false,
        permite_reabrir: true,
      }),
      modo: "detalhado",
    });
    (carregarMensagensLaudo as jest.Mock).mockResolvedValue({
      estado: "aprovado",
      laudo_id: 144,
      status_card: "aprovado",
      permite_edicao: false,
      permite_reabrir: true,
      laudo_card: criarLaudoCard({
        id: 144,
        status_card: "aprovado",
        status_card_label: "Aprovado",
        permite_edicao: false,
        permite_reabrir: true,
      }),
      modo: "detalhado",
      itens: [],
      cursor_proximo: null,
      tem_mais: false,
      limite: 50,
    });

    const { result } = renderHook(() =>
      useInspectorChatController<OfflinePendingMessage, MobileReadCache>(
        params,
      ),
    );

    await act(async () => {
      await result.current.actions.handleConfirmarQualityGate();
    });

    expect(finalizarLaudoMobile).toHaveBeenCalledWith("token-123", 144, {
      qualityGateOverride: null,
    });
    expect(params.setQualityGateVisible).toHaveBeenCalledWith(false);

    alertSpy.mockRestore();
  });
});
