import {
  buildChatAiRequestConfig,
  describeChatAiBehaviorChange,
  mapAiModelToChatMode,
  stripEmbeddedChatAiPreferences,
} from "./preferences";
import { createDefaultAppSettings } from "../../settings/schema/defaults";

describe("chat preferences", () => {
  it("maps AI models to supported chat modes", () => {
    expect(mapAiModelToChatMode("rápido")).toBe("curto");
    expect(mapAiModelToChatMode("equilibrado")).toBe("detalhado");
    expect(mapAiModelToChatMode("avançado")).toBe("deep_research");
  });

  it("mantem o contexto de IA interno e limpa vazamento legados", () => {
    const settings = createDefaultAppSettings();
    const config = buildChatAiRequestConfig({
      ...settings.ai,
      model: "avançado",
      responseLanguage: "Português",
      responseStyle: "detalhado",
      tone: "técnico",
      temperature: 0.2,
      memoryEnabled: false,
    });

    expect(config.messagePrefix).toContain("[preferencias_ia_mobile]");
    expect(config.messagePrefix).toContain("responda em Português");
    expect(config.messagePrefix).toContain("use tom técnico");
    expect(
      stripEmbeddedChatAiPreferences(
        `${config.messagePrefix}\n\nVerifique a ancoragem.`,
      ),
    ).toBe("Verifique a ancoragem.");
    expect(
      stripEmbeddedChatAiPreferences(config.messagePrefix, {
        fallbackHiddenOnly: "Evidência enviada",
      }),
    ).toBe("Evidência enviada");
    expect(config.mode).toBe("deep_research");
  });

  it("summarizes behavior changes only when the summary changes", () => {
    expect(describeChatAiBehaviorChange("A", "A")).toBe("");
    expect(describeChatAiBehaviorChange("", "B")).toBe("");
    expect(describeChatAiBehaviorChange("curto", "detalhado")).toContain(
      "detalhado",
    );
  });
});
