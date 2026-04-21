import { act, renderHook } from "@testing-library/react-native";
import { useState } from "react";

import type { ActiveThread, ChatState } from "../chat/types";
import {
  type GuidedInspectionDraft,
  isGuidedInspectionComplete,
} from "./guidedInspection";
import { useInspectorRootGuidedInspectionController } from "./useInspectorRootGuidedInspectionController";

function renderGuidedInspectionController(options?: {
  conversation?: ChatState | null;
  initialDraft?: GuidedInspectionDraft | null;
}) {
  const onShowAlert = jest.fn();

  const hook = renderHook(() => {
    const [activeThread, setActiveThread] = useState<ActiveThread>("chat");
    const [conversation] = useState<ChatState | null>(
      options?.conversation ?? null,
    );
    const [draft, setDraft] = useState<GuidedInspectionDraft | null>(
      options?.initialDraft ?? null,
    );
    const [message, setMessage] = useState("");
    const [errorConversation, setErrorConversation] = useState("erro");
    const [threadHomeVisible, setThreadHomeVisible] = useState(true);

    const controller = useInspectorRootGuidedInspectionController({
      actionState: {
        onShowAlert,
      },
      state: {
        activeThread,
        conversation,
        draft,
      },
      setterState: {
        setActiveThread,
        setErrorConversation,
        setGuidedInspectionDraft: setDraft,
        setMessage,
        setThreadHomeVisible,
      },
    });

    return {
      activeThread,
      controller,
      draft,
      errorConversation,
      message,
      onShowAlert,
      threadHomeVisible,
    };
  });

  return hook;
}

describe("useInspectorRootGuidedInspectionController", () => {
  it("inicia a inspecao guiada em chat novo sem poluir o composer", () => {
    const { result } = renderGuidedInspectionController();

    act(() => {
      result.current.controller.actions.handleStartGuidedInspection();
    });

    expect(result.current.activeThread).toBe("chat");
    expect(result.current.errorConversation).toBe("");
    expect(result.current.draft?.templateKey).toBe("padrao");
    expect(result.current.message).toBe("");
    expect(result.current.threadHomeVisible).toBe(false);
  });

  it("bloqueia o inicio guiado quando ha laudo ativo", () => {
    const { result } = renderGuidedInspectionController({
      conversation: {
        estado: "em_andamento",
        laudoId: 41,
        laudoCard: null,
        mensagens: [],
        modo: "curto",
        permiteEdicao: true,
        permiteReabrir: false,
        statusCard: "aberto",
      } as ChatState,
    });

    act(() => {
      result.current.controller.actions.handleStartGuidedInspection();
    });

    expect(result.current.onShowAlert).toHaveBeenCalledWith(
      "Inspecao guiada",
      "Abra um novo chat antes de iniciar uma inspecao guiada.",
    );
    expect(result.current.draft).toBeNull();
  });

  it("permite iniciar o modo guiado quando o fluxo ja limpou o caso ativo", () => {
    const { result } = renderGuidedInspectionController({
      conversation: {
        estado: "em_andamento",
        laudoId: 42,
        laudoCard: null,
        mensagens: [],
        modo: "curto",
        permiteEdicao: true,
        permiteReabrir: false,
        statusCard: "aberto",
      } as ChatState,
    });

    act(() => {
      result.current.controller.actions.handleStartGuidedInspection({
        ignoreActiveConversation: true,
      });
    });

    expect(result.current.draft?.templateKey).toBe("padrao");
    expect(result.current.message).toBe("");
    expect(result.current.onShowAlert).not.toHaveBeenCalled();
  });

  it("resolve o template guiado a partir do tipo do caso ativo", () => {
    const { result } = renderGuidedInspectionController({
      conversation: {
        estado: "relatorio_ativo",
        laudoId: 55,
        laudoCard: {
          id: 55,
          tipo_template: "nr12maquinas",
        },
        mensagens: [],
        modo: "curto",
        permiteEdicao: true,
        permiteReabrir: false,
        statusCard: "aberto",
      } as unknown as ChatState,
    });

    act(() => {
      result.current.controller.actions.handleStartGuidedInspection({
        ignoreActiveConversation: true,
      });
    });

    expect(result.current.draft?.templateKey).toBe("nr12maquinas");
    expect(result.current.draft?.templateLabel).toBe(
      "NR12 Maquinas e Equipamentos",
    );
    expect(result.current.message).toBe("");
  });

  it("resolve aliases canonicos novos ao iniciar o guiado a partir do caso ativo", () => {
    const { result } = renderGuidedInspectionController({
      conversation: {
        estado: "relatorio_ativo",
        laudoId: 56,
        laudoCard: {
          id: 56,
          tipo_template: "nr35_inspecao_ponto_ancoragem",
        },
        mensagens: [],
        modo: "curto",
        permiteEdicao: true,
        permiteReabrir: false,
        statusCard: "aberto",
      } as unknown as ChatState,
    });

    act(() => {
      result.current.controller.actions.handleStartGuidedInspection({
        ignoreActiveConversation: true,
      });
    });

    expect(result.current.draft?.templateKey).toBe("nr35_ponto_ancoragem");
    expect(result.current.draft?.templateLabel).toBe("NR35 Ponto de Ancoragem");
  });

  it("avanca o checklist e permite encerrar o modo guiado", () => {
    const { result } = renderGuidedInspectionController();

    act(() => {
      result.current.controller.actions.handleStartGuidedInspection();
    });
    act(() => {
      result.current.controller.actions.handleAdvanceGuidedInspection();
    });

    expect(result.current.draft?.completedStepIds).toEqual([
      "identificacao_ativo",
    ]);
    expect(result.current.message).toBe("");

    act(() => {
      result.current.controller.actions.handleStopGuidedInspection();
    });

    expect(result.current.draft).toBeNull();
    expect(result.current.threadHomeVisible).toBe(true);
  });

  it("avisa quando o checklist base termina", () => {
    const { result } = renderGuidedInspectionController();

    act(() => {
      result.current.controller.actions.handleStartGuidedInspection();
    });

    for (let index = 0; index < 5; index += 1) {
      act(() => {
        result.current.controller.actions.handleAdvanceGuidedInspection();
      });
    }

    expect(isGuidedInspectionComplete(result.current.draft)).toBe(true);
    expect(result.current.onShowAlert).toHaveBeenCalledWith(
      "Inspecao guiada",
      "Checklist base concluido. Revise as evidencias e gere o rascunho do laudo.",
    );
  });
});
