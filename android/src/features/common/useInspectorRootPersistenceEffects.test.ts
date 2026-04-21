import { renderHook } from "@testing-library/react-native";

jest.mock("../settings/useCriticalSettingsSync", () => ({
  useCriticalSettingsSync: jest.fn(),
}));

import { createDefaultAppSettings } from "../../settings/schema/defaults";
import { useCriticalSettingsSync } from "../settings/useCriticalSettingsSync";
import { useInspectorRootPersistenceEffects } from "./useInspectorRootPersistenceEffects";

function criarSettingsDocument() {
  return {
    ...createDefaultAppSettings(),
    account: {
      ...createDefaultAppSettings().account,
      email: "conta@example.com",
      fullName: "Gabriel",
      displayName: "Gabriel",
    },
    dataControls: {
      ...createDefaultAppSettings().dataControls,
      retention: "30 dias" as const,
    },
  };
}

function criarInput() {
  return {
    sessionState: {
      carregando: false,
      email: "inspetor@example.com",
      session: {
        accessToken: "token-123",
        bootstrap: {
          ok: true,
          app: {
            api_base_url: "https://api.example.com",
            nome: "Tariel",
            portal: "inspetor",
            suporte_whatsapp: "",
          },
          usuario: {
            id: 1,
            email: "inspetor@example.com",
            nome_completo: "Gabriel Silva",
            telefone: "",
            foto_perfil_url: "",
            empresa_nome: "Tariel",
            empresa_id: 7,
            nivel_acesso: 1,
          },
        },
      },
    },
    settingsState: {
      backupAutomatico: true,
      reautenticacaoExpiraEm: "",
      reautenticacaoStatus: "Pendente",
      retencaoDados: "30 dias" as const,
      salvarHistoricoConversas: true,
      settingsActions: {
        updateWith: jest.fn(),
      },
      settingsDocument: criarSettingsDocument(),
    },
    dataState: {
      cacheLeitura: {
        bootstrap: null,
        laudos: [],
        conversaAtual: null,
        conversasPorLaudo: {},
        mesaPorLaudo: {},
        chatDrafts: {},
        mesaDrafts: {},
        chatAttachmentDrafts: {},
        mesaAttachmentDrafts: {},
        updatedAt: "",
      },
      historicoOcultoIds: [7],
      laudosFixadosIds: [9],
    },
    actionState: {
      isReauthenticationStillValid: jest.fn().mockReturnValue(false),
      onFilterItemsByRetention: jest.fn((items) => items),
      onGetCacheKeyForLaudo: jest
        .fn()
        .mockImplementation((id) => `laudo:${id}`),
      onGetRetentionWindowMs: jest.fn().mockReturnValue(null),
      onResetMesaState: jest.fn(),
      onSanitizeReadCacheForPrivacy: jest.fn((cache) => cache),
      onSaveHistoryStateLocally: jest.fn().mockResolvedValue(undefined),
      onSaveReadCacheLocally: jest.fn().mockResolvedValue(undefined),
      registerNotifications: jest.fn(),
    },
    setterState: {
      notificationRegistrarRef: {
        current: jest.fn(),
      },
      setCacheLeitura: jest.fn(),
      setFilaOffline: jest.fn(),
      setFilaSuporteLocal: jest.fn(),
      setLaudosDisponiveis: jest.fn(),
      setNotificacoes: jest.fn(),
      setProvedoresConectados: jest.fn(),
      setReautenticacaoExpiraEm: jest.fn(),
      setReautenticacaoStatus: jest.fn(),
    },
  };
}

describe("useInspectorRootPersistenceEffects", () => {
  it("encapsula a sincronização crítica e os efeitos locais do app raiz", () => {
    const input = criarInput();

    renderHook(() => useInspectorRootPersistenceEffects(input));

    const mockedUseCriticalSettingsSync = jest.mocked(useCriticalSettingsSync);

    expect(mockedUseCriticalSettingsSync).toHaveBeenCalledWith(
      expect.objectContaining({
        accessToken: "token-123",
        carregando: false,
      }),
    );
    expect(
      input.settingsState.settingsActions.updateWith,
    ).toHaveBeenCalledTimes(1);
    expect(input.setterState.setProvedoresConectados).toHaveBeenCalledTimes(1);
    expect(input.actionState.onSaveHistoryStateLocally).toHaveBeenCalledWith({
      historicoOcultoIds: [7],
      laudosFixadosIds: [9],
    });
    expect(input.setterState.notificationRegistrarRef.current).toBe(
      input.actionState.registerNotifications,
    );
    expect(input.setterState.setReautenticacaoStatus).toHaveBeenCalledWith(
      "Não confirmada",
    );
  });

  it("nao reaplica o merge da sessao quando apenas wrappers sao recriados", () => {
    const input = criarInput();
    const { rerender } = renderHook<
      ReturnType<typeof useInspectorRootPersistenceEffects>,
      { currentInput: ReturnType<typeof criarInput> }
    >(({ currentInput }) => useInspectorRootPersistenceEffects(currentInput), {
      initialProps: {
        currentInput: input,
      },
    });

    const proximoInput = {
      ...input,
      actionState: {
        ...input.actionState,
      },
      setterState: {
        ...input.setterState,
      },
      settingsState: {
        ...input.settingsState,
        settingsActions: {
          ...input.settingsState.settingsActions,
        },
      },
    };

    rerender({ currentInput: proximoInput });

    expect(
      input.settingsState.settingsActions.updateWith,
    ).toHaveBeenCalledTimes(1);
    expect(input.setterState.setProvedoresConectados).toHaveBeenCalledTimes(1);
  });
});
