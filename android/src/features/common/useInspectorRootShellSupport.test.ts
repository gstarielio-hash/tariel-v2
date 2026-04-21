import { renderHook } from "@testing-library/react-native";

jest.mock("../auth/useExternalAccessActions", () => ({
  useExternalAccessActions: jest.fn(() => ({
    handleEsqueciSenha: jest.fn(),
    handleLoginSocial: jest.fn(),
    tentarAbrirUrlExterna: jest.fn(),
  })),
}));

jest.mock("./useInspectorShellController", () => ({
  useInspectorShellController: jest.fn(() => ({
    abrirHistorico: jest.fn(),
    configuracoesAberta: false,
    fecharConfiguracoes: jest.fn(),
  })),
}));

import { useExternalAccessActions } from "../auth/useExternalAccessActions";
import { useInspectorShellController } from "./useInspectorShellController";
import { useInspectorRootShellSupport } from "./useInspectorRootShellSupport";

describe("useInspectorRootShellSupport", () => {
  it("agrega shell lateral e ações externas em um único hook root", () => {
    const input = {
      externalAccessState: {
        email: "inspetor@tariel.test",
        onCanOpenUrl: jest.fn(),
        onOpenUrl: jest.fn(),
        onShowAlert: jest.fn(),
      },
      shellState: {
        appLocked: false,
        onClearTransientSettingsPresentationState: jest.fn(),
        onClearTransientSettingsUiPreservingReauth: jest.fn(),
        onResetAfterSessionEnded: jest.fn(),
        resetSettingsNavigation: jest.fn(),
        scrollRef: { current: null },
        sessionActive: true,
        sessionLoading: false,
      },
    };

    const { result } = renderHook(() =>
      useInspectorRootShellSupport(input as any),
    );

    expect(useInspectorShellController).toHaveBeenCalledWith(input.shellState);
    expect(useExternalAccessActions).toHaveBeenCalledWith(
      input.externalAccessState,
    );
    expect(result.current.configuracoesAberta).toBe(false);
    expect(typeof result.current.handleEsqueciSenha).toBe("function");
    expect(typeof result.current.abrirHistorico).toBe("function");
  });
});
