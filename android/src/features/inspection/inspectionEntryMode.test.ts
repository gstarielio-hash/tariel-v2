import {
  reasonLabelForInspectionEntryMode,
  resolveInspectionEntryMode,
} from "./inspectionEntryMode";

describe("inspectionEntryMode", () => {
  it("honra a preferencia explicita do inspetor", () => {
    expect(
      resolveInspectionEntryMode({
        preference: "evidence_first",
      }),
    ).toEqual({
      effective: "evidence_first",
      preference: "evidence_first",
      reason: "user_preference",
    });
  });

  it("reaproveita o ultimo modo do caso quando automatico e remember estiver ligado", () => {
    expect(
      resolveInspectionEntryMode({
        cards: [
          {
            entry_mode_effective: "evidence_first",
            entry_mode_reason: "last_case_mode",
          },
        ],
        preference: "auto_recommended",
        rememberLastCaseMode: true,
      }),
    ).toEqual({
      effective: "evidence_first",
      preference: "auto_recommended",
      reason: "last_case_mode",
    });
  });

  it("preserva o modo salvo no caso ativo", () => {
    expect(
      resolveInspectionEntryMode({
        activeCase: {
          entry_mode_effective: "chat_first",
          entry_mode_preference: "auto_recommended",
          entry_mode_reason: "existing_case_state",
        },
        cards: [
          {
            entry_mode_effective: "evidence_first",
          },
        ],
        preference: "auto_recommended",
        rememberLastCaseMode: true,
      }),
    ).toEqual({
      effective: "chat_first",
      preference: "auto_recommended",
      reason: "existing_case_state",
    });
  });

  it("mapeia a origem do modo para um rótulo curto", () => {
    expect(reasonLabelForInspectionEntryMode("existing_case_state")).toBe(
      "Modo salvo no caso",
    );
    expect(reasonLabelForInspectionEntryMode("user_preference")).toBe(
      "Preferencia do inspetor",
    );
  });
});
