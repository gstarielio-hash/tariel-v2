import {
  assinaturaMensagemMesa,
  assinaturaStatusLaudo,
  criarNotificacaoMesa,
  criarNotificacaoSistema,
  criarNotificacaoStatusLaudo,
  formatarTipoTemplateLaudo,
  mapearStatusLaudoVisual,
  selecionarLaudosParaMonitoramentoMesa,
} from "./activityNotificationHelpers";

describe("activityNotificationHelpers", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("gera assinaturas e formatacoes canonicas", () => {
    expect(
      assinaturaStatusLaudo({
        status_card: "ajustes",
        status_revisao: "pendente",
        status_card_label: "Ajustes",
        permite_reabrir: true,
        permite_edicao: false,
        case_lifecycle_status: "devolvido_para_correcao",
        active_owner_role: "inspetor",
      } as any),
    ).toBe(
      "ajustes|pendente|Ajustes|1|0|devolvido_para_correcao|inspetor|laudo_em_coleta|chat_reopen",
    );
    expect(
      assinaturaMensagemMesa({
        id: 7,
        lida: true,
        resolvida_em: "",
        texto: "Mesa",
      } as any),
    ).toBe("7|1|not_applicable|Mesa");
    expect(formatarTipoTemplateLaudo("nr12_maquinas")).toBe("Nr12 Maquinas");
    expect(mapearStatusLaudoVisual("ajustes")).toEqual({
      tone: "danger",
      icon: "alert-circle-outline",
    });
    expect(mapearStatusLaudoVisual("emitido")).toEqual({
      tone: "success",
      icon: "file-document-check-outline",
    });
    expect(
      assinaturaStatusLaudo({
        id: 12,
        status_card: "emitido",
        status_revisao: "aprovado",
        status_card_label: "Emitido",
        permite_reabrir: true,
        permite_edicao: false,
        case_lifecycle_status: "emitido",
        active_owner_role: "none",
        allowed_surface_actions: ["chat_reopen"],
        official_issue_summary: {
          label: "Reemissão recomendada",
          detail: "PDF emitido divergente · Emitido v0003 · Atual v0004",
          primary_pdf_diverged: true,
          issue_number: "EO-12",
          primary_pdf_storage_version: "v0003",
          current_primary_pdf_storage_version: "v0004",
        },
      } as any),
    ).toBe(
      "emitido|aprovado|Emitido|1|0|emitido|none|devolvido_para_correcao|chat_reopen|reissue|EO-12|v0003|v0004",
    );
  });

  it("cria notificacoes e seleciona laudos monitorados", () => {
    jest
      .spyOn(Date.prototype, "toISOString")
      .mockReturnValue("2026-03-30T10:00:00.000Z");
    jest.spyOn(Date, "now").mockReturnValue(100);
    jest.spyOn(Math, "random").mockReturnValue(0.5);

    expect(
      criarNotificacaoStatusLaudo({
        id: 5,
        titulo: "Laudo 5",
        status_card: "ajustes",
        status_card_label: "Ajustes",
        status_revisao: "pendente",
        permite_reabrir: true,
        permite_edicao: false,
        case_lifecycle_status: "devolvido_para_correcao",
        active_owner_role: "inspetor",
      } as any),
    ).toMatchObject({
      id: "status:5:ajustes|pendente|Ajustes|1|0|devolvido_para_correcao|inspetor|laudo_em_coleta|chat_reopen",
      targetThread: "chat",
    });
    expect(
      criarNotificacaoStatusLaudo({
        id: 6,
        titulo: "Laudo 6",
        status_card: "emitido",
        status_card_label: "Emitido",
        status_revisao: "aprovado",
        permite_reabrir: true,
        permite_edicao: false,
        case_lifecycle_status: "emitido",
        active_owner_role: "none",
        allowed_surface_actions: ["chat_reopen"],
        official_issue_summary: {
          label: "Reemissão recomendada",
          detail: "PDF emitido divergente · Emitido v0003 · Atual v0004",
          primary_pdf_diverged: true,
          issue_number: "EO-6",
          primary_pdf_storage_version: "v0003",
          current_primary_pdf_storage_version: "v0004",
        },
      } as any),
    ).toMatchObject({
      id: "status:6:emitido|aprovado|Emitido|1|0|emitido|none|devolvido_para_correcao|chat_reopen|reissue|EO-6|v0003|v0004",
      kind: "alerta_critico",
      title: "Reemissão recomendada",
      body: "Laudo 6: PDF emitido divergente · Emitido v0003 · Atual v0004. Abra a finalização para reemitir.",
      targetThread: "finalizar",
    });

    expect(
      criarNotificacaoMesa(
        "mesa_resolvida",
        {
          id: 9,
          laudo_id: 5,
          resolvida_em: "2026-03-30",
          texto: "Tudo certo",
        } as any,
        "Laudo 5",
      ),
    ).toMatchObject({
      id: "mesa:9:mesa_resolvida:resolved",
      title: "Pendência marcada como resolvida",
      targetThread: "mesa",
    });

    expect(
      criarNotificacaoSistema({
        title: "Aviso",
        body: "Corpo",
      }),
    ).toMatchObject({
      id: "system:100:8",
      targetThread: "chat",
    });

    expect(
      selecionarLaudosParaMonitoramentoMesa({
        laudoAtivoId: 3,
        laudos: [
          { id: 1, status_card: "aberto" },
          {
            id: 2,
            status_card: "ajustes",
            case_lifecycle_status: "devolvido_para_correcao",
          },
          {
            id: 3,
            status_card: "aguardando",
            case_lifecycle_status: "aguardando_mesa",
          },
          {
            id: 4,
            status_card: "aberto",
            case_lifecycle_status: "em_revisao_mesa",
          },
        ] as any,
      }),
    ).toEqual([3, 2, 4]);
  });
});
