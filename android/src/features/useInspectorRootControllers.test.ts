import { renderHook } from "@testing-library/react-native";

const mockUseInspectorRootConversationControllers = jest.fn();
const mockUseInspectorRootOperationalControllers = jest.fn();
const mockUseInspectorRootSecurityAndPersistence = jest.fn();

jest.mock("./useInspectorRootConversationControllers", () => ({
  useInspectorRootConversationControllers: (...args: unknown[]) =>
    mockUseInspectorRootConversationControllers(...args),
}));

jest.mock("./useInspectorRootOperationalControllers", () => ({
  useInspectorRootOperationalControllers: (...args: unknown[]) =>
    mockUseInspectorRootOperationalControllers(...args),
}));

jest.mock("./useInspectorRootSecurityAndPersistence", () => ({
  useInspectorRootSecurityAndPersistence: (...args: unknown[]) =>
    mockUseInspectorRootSecurityAndPersistence(...args),
}));

import { useInspectorRootControllers } from "./useInspectorRootControllers";

describe("useInspectorRootControllers", () => {
  it("costura os trilhos de conversa, operação e segurança/persistência", () => {
    const bootstrap = { bootstrap: "ok" } as never;
    const conversationControllers = { chatController: { id: "chat" } };
    const operationalControllers = { operationalState: { id: "ops" } };
    const securityAndPersistence = { appLockController: { id: "lock" } };

    mockUseInspectorRootConversationControllers.mockReturnValue(
      conversationControllers,
    );
    mockUseInspectorRootOperationalControllers.mockReturnValue(
      operationalControllers,
    );
    mockUseInspectorRootSecurityAndPersistence.mockReturnValue(
      securityAndPersistence,
    );

    const { result } = renderHook(() => useInspectorRootControllers(bootstrap));

    expect(mockUseInspectorRootConversationControllers).toHaveBeenCalledWith(
      bootstrap,
    );
    expect(mockUseInspectorRootOperationalControllers).toHaveBeenCalledWith({
      bootstrap,
      conversationControllers,
    });
    expect(mockUseInspectorRootSecurityAndPersistence).toHaveBeenCalledWith({
      bootstrap,
      conversationControllers,
      operationalControllers,
    });
    expect(result.current).toEqual({
      ...conversationControllers,
      ...operationalControllers,
      ...securityAndPersistence,
    });
  });
});
