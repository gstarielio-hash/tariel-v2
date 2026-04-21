import { hasFormalCaseWorkflow } from "./caseLifecycle";

describe("hasFormalCaseWorkflow", () => {
  it("mantém o fluxo formal quando o report pack já foi materializado", () => {
    expect(
      hasFormalCaseWorkflow({
        entryModeEffective: "chat_first",
        lifecycleStatus: "laudo_em_coleta",
        workflowMode: "laudo_guiado",
        allowedSurfaceActions: ["chat_finalize"],
        reportPackDraft: {
          template_key: "nr35_linha_vida",
          quality_gates: {
            final_validation_mode: "mesa_required",
          },
        },
      }),
    ).toBe(true);
  });

  it("continua tratando chat-first vazio como fluxo livre", () => {
    expect(
      hasFormalCaseWorkflow({
        entryModeEffective: "chat_first",
        lifecycleStatus: "laudo_em_coleta",
        workflowMode: "laudo_guiado",
        reportPackDraft: {},
      }),
    ).toBe(false);
  });
});
