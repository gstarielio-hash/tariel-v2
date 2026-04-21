import { fireEvent, render } from "@testing-library/react-native";
import { Animated, ScrollView } from "react-native";

import {
  HistoryDrawerPanel,
  type HistoryDrawerPanelItem,
  type HistoryDrawerPanelProps,
  type HistoryDrawerSection,
} from "./HistoryDrawerPanel";
import type {
  MobileActiveOwnerRole,
  MobileCaseLifecycleStatus,
  MobileOfficialIssueSummary,
  MobileSurfaceAction,
} from "../../types/mobile";

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

type TestItem = HistoryDrawerPanelItem & {
  case_lifecycle_status?: MobileCaseLifecycleStatus;
  active_owner_role?: MobileActiveOwnerRole;
  allowed_surface_actions?: MobileSurfaceAction[];
  official_issue_summary?: MobileOfficialIssueSummary | null;
  report_pack_draft?: Record<string, unknown> | null;
};

function createItem(id: number): TestItem {
  return {
    id,
    titulo: `Laudo ${id}`,
    preview: "Resumo operacional",
    data_iso: "2026-03-26T10:00:00.000Z",
    status_card: "aguardando",
    status_card_label: "Aguardando",
    pinado: false,
    tipo_template: "TC",
    permite_edicao: true,
    permite_reabrir: false,
  };
}

function createProps(
  overrides: Partial<HistoryDrawerPanelProps<TestItem>> = {},
): HistoryDrawerPanelProps<TestItem> {
  const sections: HistoryDrawerSection<TestItem>[] = [
    {
      key: "hoje",
      title: "Hoje",
      items: [createItem(80), createItem(81)],
    },
  ];
  return {
    brandMarkSource: { uri: "test://brand" },
    buscaHistorico: "",
    conversasOcultasTotal: 0,
    historicoAgrupadoFinal: sections,
    historicoDrawerX: new Animated.Value(0),
    historicoVazioTexto: "Nada aqui",
    historicoVazioTitulo: "Vazio",
    historyDrawerPanResponder: { panHandlers: {} } as never,
    laudoSelecionadoId: null,
    onBuscaHistoricoChange: jest.fn(),
    onCloseHistory: jest.fn(),
    onHistorySearchFocusChange: jest.fn(),
    onExcluirConversaHistorico: jest.fn(),
    onSelecionarHistorico: jest.fn(),
    ...overrides,
  };
}

describe("HistoryDrawerPanel", () => {
  it("expõe markers estáveis para resultados e alvo do histórico", () => {
    const props = createProps({ laudoSelecionadoId: 80 });
    const { getByTestId, getByText } = render(
      <HistoryDrawerPanel {...props} />,
    );

    expect(getByTestId("history-summary-card")).toBeTruthy();
    expect(getByText("Retomada rapida")).toBeTruthy();
    expect(getByTestId("history-results-loaded")).toBeTruthy();
    expect(getByTestId("history-section-hoje")).toBeTruthy();
    expect(getByTestId("history-first-item-button")).toBeTruthy();
    expect(getByTestId("history-item-80")).toBeTruthy();
    expect(getByTestId("history-item-81")).toBeTruthy();
    expect(getByTestId("history-target-visible-80")).toBeTruthy();
    expect(getByTestId("history-item-selected-80")).toBeTruthy();
  });

  it("propaga foco da busca do histórico para o controlador lateral", () => {
    const props = createProps();
    const { getByTestId } = render(<HistoryDrawerPanel {...props} />);

    fireEvent(getByTestId("history-search-input"), "focus");
    fireEvent(getByTestId("history-search-input"), "blur");

    expect(props.onHistorySearchFocusChange).toHaveBeenNthCalledWith(1, true);
    expect(props.onHistorySearchFocusChange).toHaveBeenNthCalledWith(2, false);
  });

  it("expõe marker estável de estado vazio quando não há resultados", () => {
    const props = createProps({
      historicoAgrupadoFinal: [],
    });
    const { getByTestId } = render(<HistoryDrawerPanel {...props} />);

    expect(getByTestId("history-results-empty")).toBeTruthy();
    expect(getByTestId("history-empty-state")).toBeTruthy();
  });

  it("mantém o tap do resultado mesmo com teclado aberto", () => {
    const props = createProps();
    const { UNSAFE_getByType } = render(<HistoryDrawerPanel {...props} />);

    expect(UNSAFE_getByType(ScrollView).props.keyboardShouldPersistTaps).toBe(
      "handled",
    );
  });

  it("exibe resumo canônico do caso no item do histórico", () => {
    const props = createProps({
      historicoAgrupadoFinal: [
        {
          key: "hoje",
          title: "Hoje",
          items: [
            {
              ...createItem(80),
              case_lifecycle_status: "em_revisao_mesa",
              active_owner_role: "mesa",
              allowed_surface_actions: ["mesa_approve"],
              report_pack_draft: {
                modeled: true,
                template_label: "NR35 Linha de Vida",
                guided_context: {
                  asset_label: "Linha de vida cobertura A",
                  location_label: "Bloco 2",
                  checklist_ids: ["identificacao", "ancoragem"],
                  completed_step_ids: ["identificacao"],
                },
                image_slots: [{ slot: "vista_geral", status: "resolved" }],
                items: [
                  {
                    item_codigo: "fixacao",
                    veredito_ia_normativo: "pendente",
                    approved_for_emission: false,
                    missing_evidence: ["status_normativo_nao_confirmado"],
                  },
                ],
                structured_data_candidate: null,
                quality_gates: {
                  checklist_complete: false,
                  required_image_slots_complete: true,
                  critical_items_complete: false,
                  autonomy_ready: false,
                  requires_normative_curation: false,
                  final_validation_mode: "mesa_required",
                },
              },
              official_issue_summary: {
                label: "Reemissão recomendada",
                detail: "PDF emitido divergente · Emitido v0003 · Atual v0004",
                primary_pdf_diverged: true,
                issue_number: "EO-35-1",
                issue_state_label: "Emitido",
                primary_pdf_storage_version: "v0003",
                current_primary_pdf_storage_version: "v0004",
              },
              entry_mode_effective: "evidence_first",
              entry_mode_reason: "user_preference",
            },
          ],
        },
      ],
    });
    const { getByTestId } = render(<HistoryDrawerPanel {...props} />);

    expect(getByTestId("history-item-meta-80").props.children).toBe(
      "Operacao · Mesa avaliadora · Aprovar no mobile",
    );
    expect(getByTestId("history-item-entry-mode-80").props.children).toBe(
      "Entrada · Coleta guiada · Preferencia do inspetor",
    );
    expect(getByTestId("history-item-report-pack-80").props.children).toBe(
      "Pacote · Pre-laudo em montagem · 1/4 blocos",
    );
    expect(getByTestId("history-item-governance-80").props.children).toBe(
      "Governanca · Reemissão recomendada · PDF emitido divergente · Emitido v0003 · Atual v0004",
    );
    expect(getByTestId("history-item-context-80").props.children).toBe(
      "Contexto · Linha de vida cobertura A · Bloco 2",
    );
  });
});
