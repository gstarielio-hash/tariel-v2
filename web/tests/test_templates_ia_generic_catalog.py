from __future__ import annotations

from app.domains.chat.templates_ai import (
    RelatorioTecnicoCatalogado,
    obter_schema_template_ia,
)


def test_obter_schema_template_ia_resolve_templates_guiados_catalogados() -> None:
    assert obter_schema_template_ia("loto") is RelatorioTecnicoCatalogado
    assert obter_schema_template_ia("nr10_inspecao_spda") is RelatorioTecnicoCatalogado
    assert obter_schema_template_ia("nr13_calibracao") is RelatorioTecnicoCatalogado
    assert obter_schema_template_ia("nr35_projeto_protecao_queda") is RelatorioTecnicoCatalogado


def test_relatorio_tecnico_catalogado_aceita_payload_basico() -> None:
    payload = {
        "resumo_executivo": "Coleta guiada consolidada com rastreabilidade técnica mínima.",
        "identificacao": {
            "objeto_principal": "Sistema piloto",
            "localizacao": "Área técnica",
            "codigo_interno": "TAG-001",
            "referencia_principal": {
                "disponivel": True,
                "referencias_texto": "IMG_001",
            },
        },
        "escopo_servico": {
            "tipo_entrega": "inspecao_tecnica",
            "modo_execucao": "in_loco",
            "ativo_tipo": "sistema",
            "resumo_escopo": "Escopo consolidado do template guiado.",
        },
        "execucao_servico": {
            "metodo_aplicado": "Checklist guiado com revisão técnica.",
            "condicoes_observadas": "Condição geral regular.",
            "parametros_relevantes": "Sem parâmetros críticos pendentes.",
            "evidencia_execucao": {
                "disponivel": True,
                "referencias_texto": "IMG_002",
            },
        },
        "evidencias_e_anexos": {
            "evidencia_principal": {
                "disponivel": True,
                "referencias_texto": "IMG_003",
            },
            "evidencia_complementar": {
                "disponivel": False,
            },
            "documento_base": {
                "disponivel": False,
            },
        },
        "conclusao": {
            "status": "ajuste",
            "conclusao_tecnica": "Caso consolidado para revisão.",
            "justificativa": "Há pendências pontuais sem bloqueio estrutural.",
        },
    }

    relatorio = RelatorioTecnicoCatalogado(**payload)

    assert relatorio.identificacao.objeto_principal == "Sistema piloto"
    assert relatorio.execucao_servico.evidencia_execucao.disponivel is True
    assert relatorio.conclusao.status == "ajuste"
