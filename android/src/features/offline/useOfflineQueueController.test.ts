import { act, renderHook } from "@testing-library/react-native";

import {
  enviarMensagemChatMobile,
  enviarMensagemMesaMobile,
  finalizarLaudoMobile,
} from "../../config/api";
import { registrarEventoObservabilidade } from "../../config/observability";
import type { ChatState, OfflinePendingMessage } from "../chat/types";
import { canSyncOnCurrentNetwork } from "../chat/network";
import { useOfflineQueueController } from "./useOfflineQueueController";

jest.mock("../../config/api", () => ({
  enviarAnexoMesaMobile: jest.fn(),
  enviarMensagemChatMobile: jest.fn(),
  enviarMensagemMesaMobile: jest.fn(),
  finalizarLaudoMobile: jest.fn(),
  uploadDocumentoChatMobile: jest.fn(),
}));

jest.mock("../../config/observability", () => ({
  registrarEventoObservabilidade: jest.fn(),
}));

jest.mock("../chat/network", () => ({
  canSyncOnCurrentNetwork: jest.fn(),
}));

function criarConversa(overrides: Partial<ChatState> = {}): ChatState {
  return {
    laudoId: 21,
    estado: "relatorio_ativo",
    statusCard: "ativo",
    permiteEdicao: true,
    permiteReabrir: false,
    laudoCard: null,
    modo: "detalhado",
    mensagens: [],
    ...overrides,
  };
}

function criarPendencia(
  overrides: Partial<OfflinePendingMessage> = {},
): OfflinePendingMessage {
  return {
    id: "offline-1",
    channel: "chat",
    operation: "message",
    laudoId: 21,
    text: "Mensagem pendente",
    createdAt: "2026-03-20T10:00:00.000Z",
    title: "Laudo 21",
    attachment: null,
    referenceMessageId: null,
    qualityGateDecision: null,
    attempts: 0,
    lastAttemptAt: "",
    lastError: "",
    nextRetryAt: "",
    aiMode: "detalhado",
    aiSummary: "Detalhado",
    aiMessagePrefix: "",
    ...overrides,
  };
}

function criarParams(
  overrides: Partial<
    Parameters<
      typeof useOfflineQueueController<ChatState, OfflinePendingMessage>
    >[0]
  > = {},
): Parameters<
  typeof useOfflineQueueController<ChatState, OfflinePendingMessage>
>[0] {
  return {
    session: {
      accessToken: "token-123",
      bootstrap: {
        ok: true,
        app: {
          nome: "Tariel",
          portal: "inspetor",
          api_base_url: "https://api.tariel.test",
          suporte_whatsapp: "",
        },
        usuario: {
          id: 1,
          nome_completo: "Inspetor",
          email: "inspetor@tariel.test",
          telefone: "",
          foto_perfil_url: "",
          empresa_nome: "Tariel",
          empresa_id: 1,
          nivel_acesso: 3,
        },
      },
    },
    sessionLoading: true,
    statusApi: "offline",
    wifiOnlySync: false,
    syncEnabled: true,
    activeThread: "chat",
    conversation: criarConversa(),
    messagesMesa: [],
    offlineQueue: [criarPendencia()],
    syncingQueue: false,
    syncingItemId: "",
    setOfflineQueue: jest.fn(),
    setSyncingQueue: jest.fn(),
    setSyncingItemId: jest.fn(),
    setOfflineQueueVisible: jest.fn(),
    setActiveThread: jest.fn(),
    setMessage: jest.fn(),
    setAttachmentDraft: jest.fn(),
    setMessageMesa: jest.fn(),
    setAttachmentMesaDraft: jest.fn(),
    setMesaActiveReference: jest.fn(),
    setErrorConversation: jest.fn(),
    setErrorMesa: jest.fn(),
    setStatusApi: jest.fn(),
    saveQueueLocally: jest.fn().mockResolvedValue(undefined),
    carregarListaLaudos: jest.fn().mockResolvedValue([]),
    carregarConversaAtual: jest.fn().mockResolvedValue(criarConversa()),
    abrirLaudoPorId: jest.fn().mockResolvedValue(undefined),
    handleSelecionarLaudo: jest.fn().mockResolvedValue(undefined),
    carregarMesaAtual: jest.fn().mockResolvedValue(undefined),
    inferirSetorConversa: jest.fn().mockReturnValue("geral"),
    montarHistoricoParaEnvio: jest.fn().mockReturnValue([]),
    normalizarModoChat: jest.fn().mockReturnValue("detalhado"),
    obterResumoReferenciaMensagem: jest.fn().mockReturnValue("Resumo"),
    restoreQualityGateFinalize: jest.fn().mockResolvedValue(undefined),
    erroSugereModoOffline: jest.fn().mockReturnValue(false),
    duplicarComposerAttachment: jest.fn((anexo) =>
      anexo ? { ...anexo } : null,
    ),
    calcularBackoffMs: jest.fn().mockReturnValue(30_000),
    isItemReadyForRetry: jest.fn().mockReturnValue(true),
    ...overrides,
  };
}

describe("useOfflineQueueController", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("retoma uma pendencia de chat restaurando a thread e removendo o item da fila", async () => {
    const attachment = {
      kind: "image" as const,
      label: "Imagem",
      resumo: "Anexo",
      dadosImagem: "base64",
      previewUri: "file:///preview.png",
      fileUri: "file:///imagem.png",
      mimeType: "image/png",
    };
    const item = criarPendencia({
      text: "Retomar conversa",
      attachment,
    });
    const params = criarParams({
      offlineQueue: [item],
    });

    const { result } = renderHook(() => useOfflineQueueController(params));

    await act(async () => {
      await result.current.actions.handleRetomarItemFilaOffline(item);
    });

    expect(params.setOfflineQueueVisible).toHaveBeenCalledWith(false);
    expect(params.setActiveThread).toHaveBeenCalledWith("chat");
    expect(params.abrirLaudoPorId).toHaveBeenCalledWith("token-123", 21);
    expect(params.setMessage).toHaveBeenCalledWith("Retomar conversa");
    expect(params.setAttachmentDraft).toHaveBeenCalledWith({ ...attachment });

    const removerUpdater = (params.setOfflineQueue as jest.Mock).mock
      .calls[0]?.[0] as
      | ((current: OfflinePendingMessage[]) => OfflinePendingMessage[])
      | undefined;
    expect(
      removerUpdater?.([item, criarPendencia({ id: "offline-2" })]),
    ).toEqual([criarPendencia({ id: "offline-2" })]);
  });

  it("marca erro, backoff e modo offline quando o reenvio individual falha", async () => {
    jest
      .spyOn(Date, "now")
      .mockReturnValue(new Date("2026-03-20T12:00:00.000Z").getTime());
    (canSyncOnCurrentNetwork as jest.Mock).mockResolvedValue(true);
    (enviarMensagemChatMobile as jest.Mock).mockRejectedValue(
      new Error("sem internet"),
    );

    const item = criarPendencia({
      laudoId: null,
    });
    const params = criarParams({
      offlineQueue: [item],
      erroSugereModoOffline: jest.fn().mockReturnValue(true),
    });

    const { result } = renderHook(() => useOfflineQueueController(params));

    await act(async () => {
      await result.current.actions.sincronizarItemFilaOffline(item);
    });

    expect(params.setSyncingItemId).toHaveBeenNthCalledWith(1, "offline-1");
    expect(params.setSyncingItemId).toHaveBeenLastCalledWith("");
    expect(params.setErrorConversation).toHaveBeenCalledWith("sem internet");
    expect(params.setStatusApi).toHaveBeenCalledWith("offline");

    const primeiraAtualizacao = (params.setOfflineQueue as jest.Mock).mock
      .calls[0]?.[0] as (
      current: OfflinePendingMessage[],
    ) => OfflinePendingMessage[];
    const segundaAtualizacao = (params.setOfflineQueue as jest.Mock).mock
      .calls[1]?.[0] as (
      current: OfflinePendingMessage[],
    ) => OfflinePendingMessage[];
    const aposTentativa = primeiraAtualizacao([item])[0];
    const aposErro = segundaAtualizacao([aposTentativa])[0];

    expect(aposTentativa?.attempts).toBe(1);
    expect(aposTentativa?.lastError).toBe("");
    expect(aposErro?.lastError).toBe("sem internet");
    expect(aposErro?.nextRetryAt).toBe("2026-03-20T12:00:30.000Z");
    expect(registrarEventoObservabilidade).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "offline_queue",
        ok: false,
      }),
    );
  });

  it("sincroniza uma finalização pendente com exceção governada", async () => {
    (canSyncOnCurrentNetwork as jest.Mock).mockResolvedValue(true);
    (finalizarLaudoMobile as jest.Mock).mockResolvedValue({
      success: true,
      laudo_id: 21,
      message: "Caso enviado para a Mesa Avaliadora a partir do mobile.",
    });

    const item = criarPendencia({
      operation: "quality_gate_finalize",
      text: "Justificativa interna detalhada.",
      qualityGateDecision: {
        reason: "Justificativa interna detalhada.",
        requestedCases: ["nr_divergence"],
        responsibilityNotice: "A responsabilidade final continua humana.",
        gateSnapshot: {
          codigo: "GATE_QUALIDADE_REPROVADO",
          aprovado: false,
          mensagem: "Bloqueado",
          tipo_template: "nr13",
          template_nome: "NR13",
          resumo: {},
          itens: [],
          faltantes: [],
          roteiro_template: null,
          human_override_policy: null,
        },
      },
    });
    const params = criarParams({
      offlineQueue: [item],
    });

    const { result } = renderHook(() => useOfflineQueueController(params));

    await act(async () => {
      await result.current.actions.sincronizarItemFilaOffline(item);
    });

    expect(finalizarLaudoMobile).toHaveBeenCalledWith("token-123", 21, {
      qualityGateOverride: {
        enabled: true,
        reason: "Justificativa interna detalhada.",
        cases: ["nr_divergence"],
      },
    });
  });

  it("sincroniza uma pendencia de chat com sucesso e atualiza a lista local", async () => {
    (canSyncOnCurrentNetwork as jest.Mock).mockResolvedValue(true);
    (enviarMensagemChatMobile as jest.Mock).mockResolvedValue({
      laudoId: 99,
    });

    const item = criarPendencia();
    const params = criarParams({
      offlineQueue: [item],
    });

    const { result } = renderHook(() => useOfflineQueueController(params));

    await act(async () => {
      await result.current.actions.sincronizarItemFilaOffline(item);
    });

    expect(params.carregarListaLaudos).toHaveBeenCalledWith("token-123", true);
    expect(params.carregarConversaAtual).toHaveBeenCalledWith(
      "token-123",
      true,
    );

    const removerUpdater = (params.setOfflineQueue as jest.Mock).mock
      .calls[1]?.[0] as
      | ((current: OfflinePendingMessage[]) => OfflinePendingMessage[])
      | undefined;
    expect(removerUpdater?.([item])).toEqual([]);
    expect(registrarEventoObservabilidade).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "offline_queue",
        ok: true,
      }),
    );
  });

  it("reenvia contexto guiado do caso ao sincronizar uma evidencia offline", async () => {
    (canSyncOnCurrentNetwork as jest.Mock).mockResolvedValue(true);
    (enviarMensagemChatMobile as jest.Mock).mockResolvedValue({
      laudoId: 21,
    });

    const item = criarPendencia({
      text: "Contexto da vistoria",
      guidedInspectionDraft: {
        template_key: "nr35_linha_vida",
        template_label: "NR35 Linha de Vida",
        started_at: "2026-04-06T22:30:00.000Z",
        current_step_index: 1,
        completed_step_ids: ["identificacao_laudo"],
        checklist: [
          {
            id: "identificacao_laudo",
            title: "Identificacao do ativo e do laudo",
            prompt: "registre unidade, local e tag",
            evidence_hint: "codigo do ativo e local resumido",
          },
          {
            id: "contexto_vistoria",
            title: "Contexto da vistoria",
            prompt: "confirme responsaveis e data",
            evidence_hint: "nomes, data e acompanhamento",
          },
        ],
        evidence_bundle_kind: "case_thread",
        evidence_refs: [],
        mesa_handoff: null,
      },
      attachment: {
        kind: "image",
        label: "Foto",
        resumo: "Vista geral",
        dadosImagem: "base64",
        previewUri: "file:///preview.png",
        fileUri: "file:///imagem.png",
        mimeType: "image/png",
      },
    });
    const params = criarParams({
      offlineQueue: [item],
    });

    const { result } = renderHook(() => useOfflineQueueController(params));

    await act(async () => {
      await result.current.actions.sincronizarItemFilaOffline(item);
    });

    expect(enviarMensagemChatMobile).toHaveBeenCalledWith(
      "token-123",
      expect.objectContaining({
        guidedInspectionDraft: item.guidedInspectionDraft,
        guidedInspectionContext: {
          template_key: "nr35_linha_vida",
          step_id: "contexto_vistoria",
          step_title: "Contexto da vistoria",
          attachment_kind: "image",
        },
      }),
    );
  });

  it("reenvia pendencia da mesa preservando clientMessageId", async () => {
    (canSyncOnCurrentNetwork as jest.Mock).mockResolvedValue(true);
    (enviarMensagemMesaMobile as jest.Mock).mockResolvedValue({
      laudo_id: 21,
      mensagem: { id: 77 },
    });

    const item = criarPendencia({
      channel: "mesa",
      clientMessageId: "mesa:offline:1",
    });
    const params = criarParams({
      activeThread: "mesa",
      offlineQueue: [item],
    });

    const { result } = renderHook(() => useOfflineQueueController(params));

    await act(async () => {
      await result.current.actions.sincronizarItemFilaOffline(item);
    });

    expect(enviarMensagemMesaMobile).toHaveBeenCalledWith(
      "token-123",
      21,
      "Mensagem pendente",
      null,
      "mesa:offline:1",
    );
  });
});
