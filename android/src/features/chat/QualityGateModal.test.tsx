import { render } from "@testing-library/react-native";

import { QualityGateModal } from "./QualityGateModal";

jest.mock("@expo/vector-icons", () => {
  const React = require("react");
  const { Text } = require("react-native");
  return {
    MaterialCommunityIcons: ({
      name,
      ...props
    }: {
      name: string;
      [key: string]: unknown;
    }) => React.createElement(Text, props, name),
  };
});

describe("QualityGateModal", () => {
  it("renderiza a prontidao do pre-laudo quando o report pack draft existe", () => {
    const { getByTestId, getByText } = render(
      <QualityGateModal
        visible
        loading={false}
        submitting={false}
        statusApi="online"
        payload={{
          codigo: "quality_gate_blocked",
          aprovado: false,
          mensagem: "Valide a trilha antes de finalizar.",
          tipo_template: "nr35",
          template_nome: "NR35 Linha de Vida",
          resumo: {
            textos_campo: 3,
            evidencias: 4,
            fotos: 1,
          },
          itens: [],
          faltantes: [],
          roteiro_template: null,
          report_pack_draft: {
            modeled: true,
            template_label: "NR35 Linha de Vida",
            guided_context: {
              checklist_ids: ["identificacao", "ancoragem", "conclusao"],
              completed_step_ids: ["identificacao"],
            },
            image_slots: [
              { slot: "vista_geral", status: "resolved" },
              { slot: "ponto_superior", status: "pending" },
            ],
            items: [
              {
                item_codigo: "fixacao",
                veredito_ia_normativo: "C",
                approved_for_emission: true,
                missing_evidence: [],
              },
              {
                item_codigo: "cabo",
                veredito_ia_normativo: "pendente",
                approved_for_emission: false,
                missing_evidence: ["status_normativo_nao_confirmado"],
              },
            ],
            structured_data_candidate: null,
            quality_gates: {
              checklist_complete: false,
              required_image_slots_complete: false,
              critical_items_complete: false,
              autonomy_ready: false,
              requires_normative_curation: true,
              max_conflict_score: 82,
              final_validation_mode: "mesa_required",
              missing_evidence: [
                {
                  message: "Ainda faltam evidencias visuais obrigatorias.",
                },
              ],
            },
          },
          review_mode_sugerido: "mesa_required",
          human_override_policy: null,
        }}
        reason=""
        notice=""
        onClose={jest.fn()}
        onConfirm={jest.fn()}
        onChangeReason={jest.fn()}
      />,
    );

    expect(getByTestId("quality-gate-report-pack-section")).toBeTruthy();
    expect(getByText("Correção obrigatória")).toBeTruthy();
    expect(getByText("Prontidão do pré-laudo")).toBeTruthy();
    expect(getByText("0/5")).toBeTruthy();
    expect(getByText("Blocos")).toBeTruthy();
    expect(getByText("Checklist guiado")).toBeTruthy();
    expect(getByText("Curadoria normativa")).toBeTruthy();
    expect(
      getByText("Ainda faltam evidencias visuais obrigatorias."),
    ).toBeTruthy();
  });
});
