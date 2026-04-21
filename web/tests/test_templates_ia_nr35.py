from __future__ import annotations

from app.domains.chat.templates_ai import (
    MAPA_COMPONENTES_NR35_LINHA_VIDA,
    TITULOS_SECOES_NR35_LINHA_VIDA,
    ComponentesInspecionadosNR35LinhaVida,
    RelatorioNR35LinhaVida,
    obter_schema_template_ia,
)


def _item(condicao: str = "C", observacao: str = "") -> dict[str, str]:
    return {"condicao": condicao, "observacao": observacao}


def test_relatorio_nr35_linha_vida_aceita_payload_minimo() -> None:
    payload = {
        "informacoes_gerais": {
            "unidade": "Catalao - GO",
            "local": "Catalao - GO",
            "contratante": "Caramuru Alimentos S/A",
            "contratada": "ATY Service LTDA",
            "data_vistoria": "2026-02-17",
        },
        "objeto_inspecao": {
            "identificacao_linha_vida": "WF-MC-115-04-23 LINHA DE VIDA - CAIXA DE EXPEDICAO",
            "tipo_linha_vida": "Horizontal",
            "escopo_inspecao": "Inspecao periodica da linha de vida da caixa de expedicao.",
        },
        "componentes_inspecionados": {
            "fixacao_dos_pontos": _item("NA", "Trecho soterrado na base."),
            "condicao_cabo_aco": _item("NA"),
            "condicao_esticador": _item("NA"),
            "condicao_sapatilha": _item("NA"),
            "condicao_olhal": _item("NA"),
            "condicao_grampos": _item("NA"),
        },
        "conclusao": {
            "status": "Pendente",
            "proxima_inspecao_periodica": "Fevereiro de 2027",
            "observacoes": "Linha de vida pendente por estar soterrada.",
        },
        "resumo_executivo": "Linha de vida pendente por impossibilidade de inspecao integral do trecho soterrado.",
    }

    relatorio = RelatorioNR35LinhaVida(**payload)

    assert relatorio.objeto_inspecao.tipo_linha_vida == "Horizontal"
    assert relatorio.componentes_inspecionados.fixacao_dos_pontos.condicao == "N/A"
    assert relatorio.conclusao.status == "Pendente"


def test_relatorio_nr35_linha_vida_suporta_fotos_e_status_aprovado() -> None:
    payload = {
        "informacoes_gerais": {
            "unidade": "Orizona - GO",
            "local": "Orizona - GO",
            "contratante": "Caramuru Alimentos S/A",
            "contratada": "ATY Service LTDA",
            "engenheiro_responsavel": "Wellington Pedro dos Santos",
            "inspetor_lider": "Marcel Renato Silva",
            "numero_laudo_fabricante": "MC-CRMR-0032",
            "numero_laudo_inspecao": "AT-IN-OZ-001-01-26",
            "art_numero": "1020260044697",
            "data_vistoria": "2026-01-29",
        },
        "objeto_inspecao": {
            "identificacao_linha_vida": "MC-CRMRSS-0977 ESCADA DE ACESSO AO ELEVADOR 01",
            "tipo_linha_vida": "Vertical",
            "escopo_inspecao": "Diagnostico geral da linha de vida e de seus acessorios.",
        },
        "componentes_inspecionados": {
            "fixacao_dos_pontos": _item(),
            "condicao_cabo_aco": _item(),
            "condicao_esticador": _item(),
            "condicao_sapatilha": _item(),
            "condicao_olhal": _item(),
            "condicao_grampos": _item(),
        },
        "registros_fotograficos": [
            {
                "titulo": "Ponto inferior com esticador",
                "legenda": "Conjunto inferior sem avarias visiveis.",
                "referencia_anexo": "foto_001.jpg",
            },
            {
                "titulo": "Ponto superior",
                "legenda": "Ponto superior em boas condicoes visuais.",
                "referencia_anexo": "foto_002.jpg",
            },
        ],
        "conclusao": {
            "status": "Aprovado",
            "proxima_inspecao_periodica": "Janeiro de 2027",
            "observacoes": "Linha de vida em conformidade com os requisitos observados em campo.",
        },
        "resumo_executivo": "Linha de vida aprovada, com componentes e acessorios em conformidade visual no momento da vistoria.",
    }

    relatorio = RelatorioNR35LinhaVida(**payload)

    assert relatorio.informacoes_gerais.numero_laudo_inspecao == "AT-IN-OZ-001-01-26"
    assert len(relatorio.registros_fotograficos) == 2
    assert relatorio.conclusao.status == "Aprovado"


def test_obter_schema_template_ia_resolve_aliases_nr35() -> None:
    assert obter_schema_template_ia("nr35") is RelatorioNR35LinhaVida
    assert obter_schema_template_ia("nr35_linha_vida") is RelatorioNR35LinhaVida
    assert obter_schema_template_ia("nr35_usina") is RelatorioNR35LinhaVida
    assert obter_schema_template_ia("padrao") is None


def test_mapa_nr35_cobre_campos_do_schema() -> None:
    campos_componentes = set(ComponentesInspecionadosNR35LinhaVida.model_fields.keys())

    assert campos_componentes.issubset(set(MAPA_COMPONENTES_NR35_LINHA_VIDA.keys()))
    assert set(TITULOS_SECOES_NR35_LINHA_VIDA.keys()) == {
        "informacoes_gerais",
        "objeto_inspecao",
        "componentes_inspecionados",
        "conclusao",
    }
