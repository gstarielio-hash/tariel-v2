# ruff: noqa: E501
from __future__ import annotations

from types import SimpleNamespace

import app.domains.chat.catalog_pdf_templates as catalog_pdf_templates
from app.domains.chat.catalog_pdf_templates import (
    RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
    ResolvedPdfTemplateRef,
    build_catalog_pdf_payload,
    has_viable_legacy_preview_overlay_for_pdf_template,
    materialize_catalog_payload_for_laudo,
    materialize_runtime_document_editor_json,
    materialize_runtime_style_json_for_pdf_template,
    resolve_runtime_field_mapping_for_pdf_template,
    resolve_pdf_template_for_laudo,
    should_use_rich_runtime_preview_for_pdf_template,
)
from app.shared.database import StatusRevisao
from nucleo.template_editor_word import MODO_EDITOR_RICO


def _template_ref(
    *,
    family_key: str,
    template_code: str,
    source_kind: str = "catalog_canonical_seed",
    modo_editor: str = MODO_EDITOR_RICO,
    arquivo_pdf_base: str = "",
    documento_editor_json: dict[str, object] | None = None,
    estilo_json: dict[str, object] | None = None,
    mapeamento_campos_json: dict[str, object] | None = None,
) -> ResolvedPdfTemplateRef:
    return ResolvedPdfTemplateRef(
        source_kind=source_kind,
        family_key=family_key,
        template_id=None,
        codigo_template=template_code,
        versao=1,
        modo_editor=modo_editor,
        arquivo_pdf_base=arquivo_pdf_base,
        documento_editor_json=documento_editor_json or {},
        estilo_json=estilo_json or {},
        assets_json=[],
        mapeamento_campos_json=mapeamento_campos_json or {},
    )


def _heading_texts(documento_editor_json: dict[str, object]) -> list[str]:
    headings: list[str] = []
    doc = documento_editor_json.get("doc") if isinstance(documento_editor_json, dict) else None
    stack = list(doc.get("content") if isinstance(doc, dict) and isinstance(doc.get("content"), list) else [])
    while stack:
        node = stack.pop(0)
        if not isinstance(node, dict):
            continue
        if str(node.get("type") or "") == "heading":
            heading = "".join(
                str(part.get("text") or "")
                for part in node.get("content", [])
                if isinstance(part, dict) and str(part.get("type") or "") == "text"
            ).strip()
            if heading:
                headings.append(heading)
        content = node.get("content")
        if isinstance(content, list):
            stack[:0] = content
    return headings


def test_build_catalog_pdf_payload_materializa_nr13_vaso_pressao_legado() -> None:
    laudo = SimpleNamespace(
        id=42,
        catalog_family_key="nr13_inspecao_vaso_pressao",
        catalog_family_label="NR13 · Vaso de Pressao",
        catalog_variant_label="Premium campo",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="utilidades",
        parecer_ia="Inspecao visual com corrosao superficial localizada e sem vazamentos aparentes.",
        primeira_mensagem="Inspecao em vaso vertical VP-204",
        motivo_rejeicao=None,
        dados_formulario={
            "informacoes_gerais": {"local_inspecao": "Casa de utilidades - Bloco B"},
            "nome_equipamento": "Vaso vertical VP-204",
            "tag_patrimonial": "TAG-VP-204",
            "placa_identificacao": "Placa parcialmente legivel com confirmacao no prontuario.",
            "condicao_operacao": True,
            "condicao_geral": "Estrutura geral sem deformacoes aparentes, com pintura desgastada.",
            "integridade_aparente": "Integridade aparente preservada nas superficies visiveis.",
            "acessibilidade_para_inspecao": "Acesso frontal adequado e lateral parcialmente restrita.",
            "pontos_de_corrosao": "Corrosao superficial proxima ao suporte inferior.",
            "vazamentos": "Nao foram observados sinais aparentes de vazamento.",
            "dispositivos_de_seguranca": "Valvula de seguranca registrada visualmente.",
            "manometro": "Manometro com visor legivel.",
            "valvula_seguranca": "Valvula instalada e acessivel para leitura local.",
            "suportes": "Base e suportes aparentam estabilidade visual adequada.",
            "prontuario": "DOC_014 - prontuario_vp204.pdf",
            "certificado": "Nao apresentado",
            "relatorio_anterior": "DOC_015 - relatorio_anterior_2025.pdf",
            "observacoes": "Manter acompanhamento do ponto de corrosao identificado.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr13_inspecao_vaso_pressao",
            template_code="nr13_vaso_pressao",
        ),
        diagnostico="Resumo executivo do caso piloto NR13 para vaso de pressao.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR13",
        data="09/04/2026",
    )

    assert payload["identificacao"]["identificacao_do_vaso"] == "Vaso vertical VP-204"
    assert payload["identificacao"]["tag_patrimonial"] == "TAG-VP-204"
    assert payload["delivery_package"]["package_kind"] == "tariel_pdf_delivery_bundle"
    assert payload["delivery_package"]["delivery_mode"] == "client_pdf_filled"
    assert "pdf_final" in payload["delivery_package"]["artifacts"]
    assert payload["caracterizacao_do_equipamento"]["condicao_de_operacao_no_momento"] == "em_operacao"
    assert payload["inspecao_visual"]["pontos_de_corrosao"]["descricao"] == "Corrosao superficial proxima ao suporte inferior."
    assert payload["dispositivos_e_acessorios"]["manometro"]["descricao"] == "Manometro com visor legivel."
    assert payload["documentacao_e_registros"]["prontuario"]["referencias_texto"] == "DOC_014 - prontuario_vp204.pdf"
    assert payload["documentacao_e_registros"]["certificado"]["disponivel"] is False
    assert payload["nao_conformidades"]["ha_nao_conformidades"] is True
    assert payload["nao_conformidades"]["ha_nao_conformidades_texto"] == "Sim"
    assert payload["conclusao"]["status"] == "ajuste"


def test_build_catalog_pdf_payload_materializa_nr13_caldeira_e_preserva_canonico() -> None:
    laudo = SimpleNamespace(
        id=99,
        catalog_family_key="nr13_inspecao_caldeira",
        catalog_family_label="NR13 · Caldeira",
        catalog_variant_label="Premium campo",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="utilidades",
        parecer_ia="Caldeira com painel operacional registrado e marcas leves de fuligem na exaustao.",
        primeira_mensagem="Inspecao inicial em casa de caldeiras",
        motivo_rejeicao=None,
        dados_formulario={
            "schema_type": "laudo_output",
            "family_key": "nr13_inspecao_caldeira",
            "identificacao": {
                "identificacao_da_caldeira": "Caldeira canonica CAL-01",
            },
            "documentacao_e_registros": {
                "prontuario": {
                    "referencias_texto": "DOC_021 - prontuario_caldeira_cal01.pdf",
                }
            },
            "local_inspecao": "Casa de caldeiras, unidade norte",
            "painel_comandos": "Painel frontal e comandos principais registrados durante a inspecao.",
            "indicador_nivel": "Indicador de nivel visivel na frente operacional.",
            "pontos_fuligem": "Marca leve de fuligem em trecho aparente da exaustao.",
            "isolamento_termico": "Desgaste localizado do revestimento externo do isolamento termico.",
            "queimador": "Frente do sistema termico registrada sem improvisacao aparente.",
            "certificado": "Nao apresentado",
            "relatorio_anterior": "DOC_022 - relatorio_anterior_2025.pdf",
            "ha_nao_conformidades": True,
            "observacoes": "Programar recomposicao do revestimento externo do isolamento termico.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr13_inspecao_caldeira",
            template_code="nr13_caldeira",
        ),
        diagnostico="Resumo executivo do caso piloto NR13 para caldeira.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR13",
        data="09/04/2026",
    )

    assert payload["identificacao"]["identificacao_da_caldeira"] == "Caldeira canonica CAL-01"
    assert payload["documentacao_e_registros"]["prontuario"]["referencias_texto"] == "DOC_021 - prontuario_caldeira_cal01.pdf"
    assert payload["inspecao_visual"]["pontos_de_vazamento_ou_fuligem"]["descricao"] == "Marca leve de fuligem em trecho aparente da exaustao."
    assert payload["dispositivos_e_controles"]["painel_e_comandos"]["descricao"] == "Painel frontal e comandos principais registrados durante a inspecao."
    assert payload["dispositivos_e_controles"]["queimador_ou_sistema_termico"]["descricao"] == "Frente do sistema termico registrada sem improvisacao aparente."
    assert payload["nao_conformidades"]["ha_nao_conformidades"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert "Prontuario:" in str(payload["mesa_review"]["pendencias_resolvidas_texto"] or "")


def test_build_catalog_pdf_payload_materializa_nr10_instalacoes_eletricas() -> None:
    laudo = SimpleNamespace(
        id=314,
        catalog_family_key="nr10_inspecao_instalacoes_eletricas",
        catalog_family_label="NR10 · Instalacoes eletricas",
        catalog_variant_label="Prime site",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="metalurgia",
        parecer_ia="Foi identificado aquecimento localizado no borne principal e lacuna de identificacao em circuitos secundarios.",
        primeira_mensagem="Inspecao inicial no painel eletrico QGBT-07 da area de prensas",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Area de prensas - painel QGBT-07",
            "objeto_principal": "Painel eletrico QGBT-07",
            "codigo_interno": "QGBT-07",
            "referencia_principal": "IMG_301 - frontal do QGBT-07",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao visual com apoio de termografia e checklist NR10.",
            "condicoes_gerais": "Painel com aquecimento localizado nas conexoes do disjuntor principal.",
            "termografia": "Registro termografico apontou elevacao localizada no borne principal.",
            "quadro_principal": "QGBT-07 com alimentacao das prensas e da iluminacao de emergencia.",
            "circuitos_criticos": "Prensas 1 e 2, iluminacao de emergencia e exaustao.",
            "aterramento": "Barramento PE presente, com necessidade de reaperto em derivacao secundaria.",
            "protecao_eletrica": "Disjuntores identificados, sem seletividade documental anexada.",
            "evidencia_principal": "IMG_302 - hotspot no borne principal",
            "evidencia_complementar": "IMG_303 - barramento de aterramento",
            "pie": "DOC_041 - pie_planta_prensas.pdf",
            "diagrama_unifilar": "DOC_042 - diagrama_qgbt07.pdf",
            "rti": "RTI-2026-07",
            "descricao_pontos_atencao": "Aquecimento anormal no borne principal e identificacao parcial dos circuitos secundarios.",
            "observacoes": "Programar reaperto, revisar identificacao dos circuitos e atualizar o prontuario eletrico.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr10_inspecao_instalacoes_eletricas",
            template_code="nr10_inspecao_instalacoes_eletricas",
        ),
        diagnostico="Resumo executivo do caso piloto NR10 para painel eletrico.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR10",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Painel eletrico QGBT-07"
    assert payload["identificacao"]["codigo_interno"] == "QGBT-07"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_301 - frontal do QGBT-07"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "painel_eletrico"
    assert "termografia" in str(payload["execucao_servico"]["metodo_aplicado"]).lower()
    assert "Aterramento:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_041 - pie_planta_prensas.pdf"
    assert "PIE:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "Diagrama:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao_texto"] == "Sim"
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr10_prontuario_instalacoes_eletricas() -> None:
    laudo = SimpleNamespace(
        id=315,
        catalog_family_key="nr10_prontuario_instalacoes_eletricas",
        catalog_family_label="NR10 · Prontuario instalacoes eletricas",
        catalog_variant_label="Prime documental",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="metalurgia",
        parecer_ia="Prontuario consolidado, mas ainda depende de anexar a ART de atualizacao do diagrama unifilar.",
        primeira_mensagem="Consolidacao do prontuario eletrico do painel QGBT-07 da area de prensas",
        motivo_rejeicao=None,
        dados_formulario={
            "localizacao": "Area de prensas - painel QGBT-07",
            "objeto_principal": "Prontuario eletrico do painel QGBT-07",
            "codigo_interno": "PRT-QGBT-07",
            "numero_prontuario": "PRT-QGBT-07",
            "referencia_principal": "DOC_301 - indice_prontuario_qgbt07.pdf",
            "modo_execucao": "analise documental",
            "metodo_aplicado": "Consolidacao documental do prontuario NR10 com validacao do indice, diagramas e inventario de circuitos.",
            "status_documentacao": "Documentacao principal consolidada com pendencia na ART da ultima revisao.",
            "inventario_instalacoes": "DOC_302 - inventario_circuitos_qgbt07.xlsx",
            "diagrama_unifilar": "DOC_303 - diagrama_qgbt07_rev04.pdf",
            "prontuario": "DOC_301 - indice_prontuario_qgbt07.pdf",
            "pie": "DOC_304 - pie_prensas_rev02.pdf",
            "procedimento_trabalho": "DOC_305 - procedimento_intervencao_qgbt07.pdf",
            "memorial_descritivo": "DOC_306 - memorial_qgbt07.pdf",
            "art_numero": "ART 2026-00411",
            "evidencia_principal": "DOC_303 - diagrama_qgbt07_rev04.pdf",
            "evidencia_complementar": "DOC_302 - inventario_circuitos_qgbt07.xlsx",
            "descricao_pontos_atencao": "Pendencia de anexar a ART de atualizacao do diagrama unifilar revisado.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Anexar a ART da revisao do diagrama, atualizar o indice e reemitir o prontuario.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr10_prontuario_instalacoes_eletricas",
            template_code="nr10_prontuario_instalacoes_eletricas",
        ),
        diagnostico="Resumo executivo do caso piloto NR10 para prontuario eletrico.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR10",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Prontuario eletrico do painel QGBT-07"
    assert payload["identificacao"]["codigo_interno"] == "PRT-QGBT-07"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "DOC_301 - indice_prontuario_qgbt07.pdf"
    assert payload["escopo_servico"]["tipo_entrega"] == "pacote_documental"
    assert payload["escopo_servico"]["modo_execucao"] == "analise_documental"
    assert payload["escopo_servico"]["ativo_tipo"] == "instalacoes_eletricas"
    assert "Prontuario:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Inventario:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_301 - indice_prontuario_qgbt07.pdf"
    assert "PIE:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "ART:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao_texto"] == "Sim"
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr10_implantacao_loto() -> None:
    laudo = SimpleNamespace(
        id=316,
        catalog_family_key="nr10_implantacao_loto",
        catalog_family_label="NR10 · Implantacao LOTO",
        catalog_variant_label="Prime campo",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="metalurgia",
        parecer_ia="Implantacao LOTO consolidada com energia zero confirmada e pendencia pontual de sinalizacao complementar.",
        primeira_mensagem="Implantacao LOTO na prensa hidraulica P-07.",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Linha de conformacao - area de prensas",
            "objeto_principal": "Prensa hidraulica P-07",
            "codigo_interno": "P-07",
            "referencia_principal": "IMG_810 - painel e chave seccionadora; DOC_410 - procedimento_loto_p07.pdf",
            "modo_execucao": "in loco",
            "metodo_aplicado": "Aplicacao da sequencia de desenergizacao, bloqueio, etiquetagem e teste de partida.",
            "condicoes_gerais": "Circuitos eletricos e hidraulicos identificados; sinalizacao complementar ausente no painel lateral.",
            "fontes_de_energia": "Energia eletrica do QDL-02 e energia hidraulica da unidade de potencia da prensa.",
            "pontos_de_bloqueio": "Chave seccionadora geral e valvula de alivio hidraulico identificadas e bloqueadas.",
            "dispositivos_e_sinalizacao": "Cadeados individuais, hasp coletivo e etiquetas de bloqueio aplicadas em campo.",
            "verificacao_energia_zero": "Teste de partida sem acionamento e descarga controlada do circuito hidraulico confirmaram energia zero.",
            "seccionamento": "Seccionamento eletrico confirmado na chave geral antes do inicio da intervencao.",
            "impedimento_reenergizacao": "Travamento mecanico e etiquetagem impediram religamento acidental.",
            "sequencia_reenergizacao": "Reenergizacao condicionada a retirada formal dos bloqueios e liberacao do responsavel.",
            "evidencia_execucao": "IMG_811 - cadeado principal; IMG_812 - etiqueta de bloqueio",
            "evidencia_principal": "IMG_811 - cadeado principal aplicado",
            "evidencia_complementar": "IMG_812 - etiqueta; IMG_813 - dreno hidraulico",
            "procedimento_loto": "DOC_410 - procedimento_loto_p07.pdf",
            "apr": "DOC_411 - apr_loto_p07.pdf",
            "matriz_energias": "DOC_412 - matriz_energias_p07.pdf",
            "checklist_loto": "DOC_413 - checklist_loto_p07.pdf",
            "descricao_pontos_atencao": "Sinalizacao complementar da fonte hidraulica ainda nao estava posicionada no painel lateral.",
            "evidencia_ponto_atencao": "IMG_814 - painel lateral sem etiqueta",
            "documentos_emitidos": "Registro tecnico de implantacao LOTO e checklist de verificacao da frente.",
            "observacoes": "Completar a sinalizacao lateral, revisar treinamento dos operadores e manter o procedimento versionado junto ao ativo.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr10_implantacao_loto",
            template_code="nr10_implantacao_loto",
        ),
        diagnostico="Resumo executivo do caso piloto NR10 para implantacao LOTO.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR10",
        data="14/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Prensa hidraulica P-07"
    assert payload["escopo_servico"]["tipo_entrega"] == "implantacao_loto"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert "Matriz de energias:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["checklist_componentes"]["fontes_de_energia"]["condicao"] == "conforme"
    assert payload["checklist_componentes"]["dispositivos_e_sinalizacao"]["condicao"] == "ajuste"
    assert "Reenergizacao controlada:" in str(
        payload["checklist_componentes"]["sequenciamento_e_reenergizacao_controlada"]["observacao"]
    )
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_410 - procedimento_loto_p07.pdf"


def test_build_catalog_pdf_payload_materializa_nr10_inspecao_spda() -> None:
    laudo = SimpleNamespace(
        id=317,
        catalog_family_key="nr10_inspecao_spda",
        catalog_family_label="NR10 · Inspecao de SPDA",
        catalog_variant_label="Prime campo",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="logistica",
        parecer_ia="SPDA com leitura tecnica suficiente, restando ajuste localizado em conexao de descida.",
        primeira_mensagem="Inspecao do SPDA do galpao principal.",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Centro Logistico Sul - cobertura do galpao 01",
            "objeto_principal": "SPDA do galpao principal",
            "codigo_interno": "SPDA-G01",
            "referencia_principal": "IMG_910 - vista geral da cobertura",
            "modo_execucao": "in loco",
            "metodo_aplicado": "Vistoria guiada com registro fotografico dos subsistemas e conferencia visual de continuidade aparente.",
            "condicoes_gerais": "Captacao e descidas em condicao geral adequada, com conexao lateral apresentando necessidade de reaperto.",
            "captacao": "Captacao periferica e conexoes principais visualmente integras na cobertura.",
            "descidas": "Descidas identificadas e continuas, com ponto lateral leste demandando reaperto em conexao aparente.",
            "aterramento_e_equipotencializacao": "Barramento de equipotencializacao identificado e acessivel, sem sinais aparentes de corrosao critica.",
            "medicoes_ou_testes": "Historico de medicao de resistencia do aterramento anexado como referencia documental complementar.",
            "evidencia_execucao": "IMG_911 - descida lateral; IMG_912 - barramento de equipotencializacao",
            "evidencia_principal": "IMG_911 - conexao lateral da descida",
            "evidencia_complementar": "IMG_910 - cobertura; IMG_912 - barramento",
            "laudo_medicao": "DOC_510 - medicao_aterramento_2025.pdf",
            "projeto_spda": "DOC_511 - croqui_spda_galpao01.pdf",
            "relatorio_anterior": "DOC_512 - relatorio_spda_2024.pdf",
            "descricao_pontos_atencao": "Conexao lateral da descida leste com necessidade de reaperto e revisao local.",
            "evidencia_ponto_atencao": "IMG_911 - conexao lateral da descida",
            "documentos_emitidos": "Laudo tecnico de inspecao do SPDA do galpao 01.",
            "observacoes": "Executar reaperto da conexao lateral leste, repetir a conferencia de continuidade e atualizar o historico do sistema.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr10_inspecao_spda",
            template_code="nr10_inspecao_spda",
        ),
        diagnostico="Resumo executivo do caso piloto NR10 para inspecao de SPDA.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR10",
        data="14/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "SPDA do galpao principal"
    assert payload["escopo_servico"]["ativo_tipo"] == "spda_edificacao"
    assert "Medicao/relatorio:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "Projeto/croqui:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["checklist_componentes"]["captacao"]["condicao"] == "conforme"
    assert payload["checklist_componentes"]["descidas"]["condicao"] == "ajuste"
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_510 - medicao_aterramento_2025.pdf"


def test_build_catalog_pdf_payload_mantem_analysis_basis_fotografico_fora_do_pdf_final() -> None:
    laudo = SimpleNamespace(
        id=350,
        catalog_family_key="nr35_inspecao_linha_de_vida",
        catalog_family_label="NR35 · Linha de vida",
        catalog_variant_label="Premium campo",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="utilidades",
        parecer_ia="Linha de vida com pontos de corrosao localizada no terminal superior.",
        primeira_mensagem="Inspecao da linha de vida do bloco oeste.",
        motivo_rejeicao=None,
        dados_formulario={
            "schema_type": "laudo_output",
            "family_key": "nr35_inspecao_linha_de_vida",
            "informacoes_gerais": {
                "local": "Bloco oeste",
            },
            "conclusao": {
                "status": "Aprovado",
            },
        },
        report_pack_draft_json={
            "analysis_basis": {
                "photo_evidence": [
                    {
                        "label": "Vista geral da linha de vida",
                        "caption": "Registro principal do conjunto instalado.",
                        "reference": "nr35_01_visao_geral.jpg",
                        "original_name": "nr35_01_visao_geral.jpg",
                    },
                    {
                        "label": "Ponto superior",
                        "caption": "Corrosao observada no terminal superior.",
                        "reference": "nr35_02_ponto_superior_corrosao.jpg",
                        "original_name": "nr35_02_ponto_superior_corrosao.jpg",
                    },
                ]
            }
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr35_inspecao_linha_de_vida",
            template_code="nr35_linha_vida",
        ),
        diagnostico="Resumo executivo do caso piloto NR35 com fotos sintéticas.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR35",
        data="13/04/2026",
    )

    assert payload["analysis_basis"]["photo_evidence"][0]["reference"] == "nr35_01_visao_geral.jpg"
    assert payload["delivery_package"]["analysis_basis_available"] is True
    assert payload["delivery_package"]["analysis_basis_visibility"] == "internal_audit_only"
    assert payload.get("registros_fotograficos") in (None, [])
    assert "nr35_01_visao_geral.jpg" not in str(payload.get("evidencias_e_anexos") or {})
    assert "nr35_02_ponto_superior_corrosao.jpg" not in str(payload.get("evidencias_e_anexos") or {})


def test_build_catalog_pdf_payload_normaliza_status_legado_nr35_para_vocabulario_final() -> None:
    laudo = SimpleNamespace(
        id=351,
        catalog_family_key="nr35_inspecao_linha_de_vida",
        catalog_family_label="NR35 · Linha de vida",
        catalog_variant_label="Premium campo",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="utilidades",
        parecer_ia="Linha de vida sem nao conformidades relevantes.",
        primeira_mensagem="Inspecao da linha de vida do bloco leste.",
        motivo_rejeicao=None,
        dados_formulario={
            "schema_type": "laudo_output",
            "family_key": "nr35_inspecao_linha_de_vida",
            "conclusao": {
                "status": "conforme",
            },
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr35_inspecao_linha_de_vida",
            template_code="nr35_linha_vida",
        ),
        diagnostico="Resumo executivo do caso piloto NR35 com alias legado.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR35",
        data="13/04/2026",
    )

    assert payload["conclusao"]["status"] == "Aprovado"


def test_materialize_runtime_document_editor_json_usa_shell_universal_quando_template_esta_generico() -> None:
    payload = {
        "schema_type": "laudo_output",
        "family_label": "NR13 - Inspecao de Vaso de Pressao",
        "document_control": {
            "document_code": "DOC-NR13-204",
            "revision": "R2",
            "title": "NR13 - Inspecao de Vaso de Pressao",
        },
        "case_context": {
            "empresa_nome": "Cliente XPTO",
            "unidade_nome": "Planta Sul",
            "data_execucao": "2026-04-09",
            "data_emissao": "2026-04-10",
        },
        "tokens": {
            "engenheiro_responsavel": "Gabriel Santos",
        },
        "escopo_servico": {
            "tipo_entrega": "inspecao_tecnica",
            "modo_execucao": "in_loco",
        },
        "identificacao": {
            "identificacao_do_vaso": "Vaso vertical VP-204",
            "localizacao": "Planta Sul",
        },
        "documentacao_e_registros": {
            "prontuario": {"referencias_texto": "DOC_014 - prontuario_vp204.pdf"},
        },
        "evidencias_e_anexos": {
            "documento_base": {"referencias_texto": "DOC_014 - prontuario_vp204.pdf"},
        },
        "conclusao": {
            "status": "ajuste",
            "conclusao_tecnica": "Equipamento apto com acompanhamento do ponto de corrosao.",
        },
    }

    runtime_document = materialize_runtime_document_editor_json(
        template_ref=_template_ref(
            family_key="nr13_inspecao_vaso_pressao",
            template_code="nr13_inspecao_vaso_pressao",
        ),
        payload=payload,
    )

    headings = _heading_texts(runtime_document)

    assert "NR13 - Inspecao de Vaso de Pressao" in headings
    assert "Quadro de Controle do Documento" in headings
    assert "Resumo Executivo" in headings
    assert "Conclusao Tecnica" in " | ".join(headings)
    assert "Template Tecnico Tariel.ia" not in " | ".join(headings)


def test_build_catalog_pdf_payload_blank_preview_remove_dados_demo_do_seed() -> None:
    payload = build_catalog_pdf_payload(
        laudo=None,
        template_ref=_template_ref(
            family_key="nr10_inspecao_instalacoes_eletricas",
            template_code="nr10_inspecao_instalacoes_eletricas",
        ),
        source_payload={
            "schema_type": "laudo_output",
            "family_key": "nr10_inspecao_instalacoes_eletricas",
            "tokens": {
                "cliente_nome": "Empresa Demo (DEV)",
                "unidade_nome": "Unidade Piloto Nacional",
                "engenheiro_responsavel": "Engenheiro Revisor (Dev)",
            },
            "case_context": {
                "data_execucao": "2026-04-11",
                "data_emissao": "2026-04-11",
            },
        },
        render_mode=RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
    )

    assert payload["render_mode"] == RENDER_MODE_TEMPLATE_PREVIEW_BLANK
    assert payload["tokens"]["cliente_nome"] is None
    assert payload["tokens"]["unidade_nome"] is None
    assert payload["tokens"]["engenheiro_responsavel"] is None
    assert payload["document_control"]["issue_date"] == ""
    assert payload["tenant_branding"]["display_name"] == ""


def test_should_use_rich_runtime_preview_promove_template_legado_sem_overlay_forte() -> None:
    payload = {
        "schema_type": "laudo_output",
        "family_key": "nr13_inspecao_vaso_pressao",
        "document_control": {
            "document_code": "DOC-NR13-204",
            "revision": "R2",
            "title": "NR13 - Inspecao de Vaso de Pressao",
        },
        "identificacao": {
            "identificacao_do_vaso": "Vaso vertical VP-204",
            "localizacao": "Planta Sul",
        },
        "conclusao": {
            "status": "ajuste",
            "conclusao_tecnica": "Equipamento apto com acompanhamento do ponto de corrosao.",
        },
    }
    template_ref = _template_ref(
        family_key="nr13_inspecao_vaso_pressao",
        template_code="nr13_legado_fraco",
        source_kind="tenant_template",
        modo_editor="legado_pdf",
        arquivo_pdf_base="/tmp/nr13_legado_fraco.pdf",
        mapeamento_campos_json={},
    )

    assert has_viable_legacy_preview_overlay_for_pdf_template(template_ref=template_ref) is False
    assert (
        should_use_rich_runtime_preview_for_pdf_template(
            template_ref=template_ref,
            payload=payload,
        )
        is True
    )


def test_should_use_rich_runtime_preview_respeita_overlay_legado_quando_viavel() -> None:
    payload = {
        "schema_type": "laudo_output",
        "family_key": "nr13_inspecao_vaso_pressao",
        "identificacao": {"identificacao_do_vaso": "Vaso vertical VP-204"},
    }
    template_ref = _template_ref(
        family_key="nr13_inspecao_vaso_pressao",
        template_code="nr13_legado_forte",
        source_kind="tenant_template",
        modo_editor="legado_pdf",
        arquivo_pdf_base="/tmp/nr13_legado_forte.pdf",
        mapeamento_campos_json={
            "pages": [
                {
                    "page": 1,
                    "fields": [{"key": "identificacao.identificacao_do_vaso", "x": 12, "y": 18, "w": 48, "h": 5}],
                }
            ]
        },
    )

    assert has_viable_legacy_preview_overlay_for_pdf_template(template_ref=template_ref) is True
    assert (
        should_use_rich_runtime_preview_for_pdf_template(
            template_ref=template_ref,
            payload=payload,
        )
        is False
    )


def test_materialize_runtime_document_editor_json_blank_preview_oculta_termos_internos() -> None:
    payload = {
        "schema_type": "laudo_output",
        "render_mode": RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
        "document_projection": {
            "render_mode": RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
            "audience": "client",
            "family_label": "NR10 - Inspecao instalacoes eletricas",
            "family_description": "Template documental governado.",
            "macro_category": "NR10",
            "master_template_id": "inspection_conformity",
            "master_template_label": "Laudo de Inspecao de Conformidade",
            "usage_classification": "Template pre-pronto",
            "section_order": [
                "controle_documental_sumario",
                "resumo_executivo",
                "objeto_escopo_base_normativa",
                "identificacao_tecnica_do_objeto",
            ],
        },
        "document_control": {
            "document_code": "NR10-TPL",
            "revision": "v1",
            "title": "NR10 - Inspecao instalacoes eletricas",
        },
        "document_contract": {
            "label": "Laudo de Inspecao de Conformidade",
        },
        "family_key": "nr10_inspecao_instalacoes_eletricas",
        "mesa_review": {
            "status": "aprovado",
            "family_lock": True,
            "scope_mismatch": False,
        },
        "tokens": {
            "cliente_nome": "Empresa Demo (DEV)",
        },
    }

    runtime_document = materialize_runtime_document_editor_json(
        template_ref=_template_ref(
            family_key="nr10_inspecao_instalacoes_eletricas",
            template_code="nr10_inspecao_instalacoes_eletricas",
        ),
        payload=payload,
        render_mode=RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
    )

    serialized = str(runtime_document)
    assert "Family key" not in serialized
    assert "Status Mesa" not in serialized
    assert "Empresa Demo" not in serialized
    assert "Template pre-pronto" in serialized


def test_materialize_runtime_style_json_for_blank_preview_sanitiza_header_e_footer() -> None:
    style = materialize_runtime_style_json_for_pdf_template(
        template_ref=_template_ref(
            family_key="nr10_inspecao_instalacoes_eletricas",
            template_code="nr10_inspecao_instalacoes_eletricas",
        ),
        payload={
            "render_mode": RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
            "document_projection": {
                "render_mode": RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
                "family_label": "NR10 - Inspecao instalacoes eletricas",
                "macro_category": "NR10",
                "usage_classification": "Template pre-pronto",
            },
            "document_control": {
                "document_code": "NR10-TPL",
                "revision": "v1",
                "title": "NR10 - Inspecao instalacoes eletricas",
            },
        },
        render_mode=RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
    )

    assert "Family" not in style["rodape_texto"]
    assert "Template pre-pronto" in style["rodape_texto"]
    assert "NR10" in style["cabecalho_texto"]


def test_materialize_runtime_style_json_for_promoted_legacy_template_usa_estilo_canonico() -> None:
    style = materialize_runtime_style_json_for_pdf_template(
        template_ref=_template_ref(
            family_key="nr13_inspecao_vaso_pressao",
            template_code="nr13_vaso_pressao",
            source_kind="tenant_template",
            modo_editor="legado_pdf",
            arquivo_pdf_base="/tmp/nr13_legado_fraco.pdf",
            documento_editor_json={},
            estilo_json={},
            mapeamento_campos_json={},
        ),
        payload={
            "render_mode": "client_pdf_filled",
            "document_projection": {
                "family_label": "NR13 - Inspecao de vaso de pressao",
                "macro_category": "NR13",
                "usage_classification": "Documento governado",
            },
            "document_control": {
                "document_code": "NR13-VP-204",
                "revision": "R4",
                "title": "NR13 - Inspecao de vaso de pressao",
            },
        },
        render_mode="client_pdf_filled",
    )

    assert "Tariel" in style["cabecalho_texto"]
    assert "NR13" in style["cabecalho_texto"]
    assert "NR13-VP-204" in style["rodape_texto"]
    assert "Revisao R4" in style["rodape_texto"]


def test_materialize_runtime_style_json_for_tenant_editor_rico_preserva_estilo_original() -> None:
    style = materialize_runtime_style_json_for_pdf_template(
        template_ref=_template_ref(
            family_key="nr13_inspecao_vaso_pressao",
            template_code="nr13_vaso_pressao",
            source_kind="tenant_template",
            modo_editor=MODO_EDITOR_RICO,
            documento_editor_json={"version": 1, "doc": {"type": "doc", "content": []}},
            estilo_json={
                "cabecalho_texto": "Cabecalho Tenant",
                "rodape_texto": "Rodape Tenant",
            },
        ),
        payload={
            "render_mode": "client_pdf_filled",
            "document_projection": {
                "family_label": "NR13 - Inspecao de vaso de pressao",
                "macro_category": "NR13",
                "usage_classification": "Documento governado",
            },
            "document_control": {
                "document_code": "NR13-VP-204",
                "revision": "R4",
                "title": "NR13 - Inspecao de vaso de pressao",
            },
        },
        render_mode="client_pdf_filled",
    )

    assert style["cabecalho_texto"] == "Cabecalho Tenant"
    assert style["rodape_texto"] == "Rodape Tenant"


def test_build_catalog_pdf_payload_materializa_nr18_inspecao_canteiro_obra() -> None:
    laudo = SimpleNamespace(
        id=801,
        catalog_family_key="nr18_inspecao_canteiro_obra",
        catalog_family_label="NR18 · Canteiro de obra",
        catalog_variant_label="Prime obra",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="construcao",
        parecer_ia="Foi identificada guarda-corpo incompleta no pavimento superior e necessidade de reforcar a sinalizacao de circulacao de pedestres.",
        primeira_mensagem="Inspecao inicial no canteiro da obra vertical Torre Norte",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Canteiro Torre Norte - pavimentos 1 a 4",
            "objeto_principal": "Canteiro da obra vertical Torre Norte",
            "codigo_interno": "OBR-TN-01",
            "referencia_principal": "IMG_1101 - vista geral do canteiro Torre Norte",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo com checklist NR18, registro fotografico e leitura das frentes simultaneas.",
            "condicoes_gerais": "Frentes ativas com protecao coletiva parcial no pavimento superior e circulacao de pedestres compartilhando area de descarga.",
            "etapa_obra": "Estrutura e alvenaria simultaneas",
            "protecao_periferica": "Guarda-corpo ausente em trecho da periferia do pavimento 4.",
            "andaimes": "Andaime fachadeiro com amarracao visivel e placas de carga instaladas.",
            "circulacao": "Fluxo de pedestres cruzando area de descarga sem segregacao completa.",
            "areas_vivencia": "Vestiario e refeitório organizados e sinalizados.",
            "sinalizacao": "Sinalizacao de circulacao de pedestres incompleta proxima ao guincho.",
            "maquinas_equipamentos": "Grua e elevador cremalheira operando na rotina da frente.",
            "evidencia_principal": "IMG_1102 - trecho sem guarda-corpo no pavimento 4",
            "evidencia_complementar": "IMG_1103 - circulacao compartilhada proxima a descarga",
            "pgr_obra": "DOC_1101 - pgr_torre_norte_rev03.pdf",
            "apr": "DOC_1102 - apr_frente_estrutura_pav4.pdf",
            "cronograma_obra": "DOC_1103 - cronograma_torre_norte.pdf",
            "descricao_pontos_atencao": "Trecho sem guarda-corpo no pavimento superior e segregacao incompleta da circulacao de pedestres.",
            "observacoes": "Regularizar a protecao coletiva e reordenar o fluxo de pedestres antes da proxima frente simultanea.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr18_inspecao_canteiro_obra",
            template_code="nr18_inspecao_canteiro_obra",
        ),
        diagnostico="Resumo executivo do caso piloto NR18 para canteiro de obra.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR18",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Canteiro da obra vertical Torre Norte"
    assert payload["identificacao"]["codigo_interno"] == "OBR-TN-01"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_1101 - vista geral do canteiro Torre Norte"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "canteiro_obra"
    assert "Protecao periferica:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Sinalizacao:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_1101 - pgr_torre_norte_rev03.pdf"
    assert "APR:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr18_inspecao_frente_construcao() -> None:
    laudo = SimpleNamespace(
        id=802,
        catalog_family_key="nr18_inspecao_frente_construcao",
        catalog_family_label="NR18 · Frente de construcao",
        catalog_variant_label="Prime obra",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="construcao",
        parecer_ia="Frente de concretagem liberada com ressalva pela necessidade de reorganizar o isolamento da vala lateral.",
        primeira_mensagem="Inspecao na frente de concretagem do bloco B",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Bloco B - frente de concretagem da ala oeste",
            "objeto_principal": "Frente de concretagem bloco B ala oeste",
            "codigo_interno": "FRN-B-OESTE",
            "referencia_principal": "IMG_1201 - vista geral da frente ala oeste",
            "modo_execucao": "in loco",
            "metodo_aplicado": "Inspecao de campo da frente de construcao com checklist NR18 e verificacao do isolamento operacional.",
            "condicoes_observadas": "Frente com fôrmas montadas, acesso controlado e vala lateral com isolamento incompleto.",
            "etapa_obra": "Concretagem de vigas e laje",
            "escavacoes": "Vala lateral sem barreira continua no trecho de acesso secundario.",
            "circulacao": "Acesso principal segregado, com desvio temporario sinalizado parcialmente.",
            "sinalizacao": "Placas de desvio presentes, mas sem repeticao no acesso secundario.",
            "maquinas_equipamentos": "Bomba de concreto e vibradores operando na frente.",
            "evidencia_principal": "IMG_1202 - vala lateral sem barreira continua",
            "evidencia_complementar": "IMG_1203 - acesso secundario com sinalizacao parcial",
            "pgr_obra": "DOC_1201 - pgr_bloco_b.pdf",
            "apr": "DOC_1202 - apr_concretagem_bloco_b.pdf",
            "pte": "DOC_1203 - permissao_concretagem_bloco_b.pdf",
            "conclusao": {"status": "Liberado com restricoes"},
            "descricao_pontos_atencao": "Necessidade de recompor o isolamento continuo da vala lateral antes do turno noturno.",
            "observacoes": "Regularizar o isolamento e repetir a verificacao antes da retomada do concreto no turno seguinte.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr18_inspecao_frente_construcao",
            template_code="nr18_inspecao_frente_construcao",
        ),
        diagnostico="Resumo executivo do caso piloto NR18 para frente de construcao.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR18",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Frente de concretagem bloco B ala oeste"
    assert payload["identificacao"]["codigo_interno"] == "FRN-B-OESTE"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_1201 - vista geral da frente ala oeste"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "frente_construcao"
    assert "Escavacoes:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "PTE:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_1201 - pgr_bloco_b.pdf"
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr22_inspecao_area_mineracao() -> None:
    laudo = SimpleNamespace(
        id=821,
        catalog_family_key="nr22_inspecao_area_mineracao",
        catalog_family_label="NR22 · Area de mineracao",
        catalog_variant_label="Prime mineracao",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="mineracao",
        parecer_ia="Foram identificadas drenagem superficial parcial e sinalizacao incompleta na rota de pedestres da cava norte.",
        primeira_mensagem="Inspecao na area de lavra da cava norte bancada 3",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Cava Norte - bancada 3",
            "objeto_principal": "Area de lavra Cava Norte - bancada 3",
            "codigo_interno": "MIN-CN-B3",
            "referencia_principal": "IMG_2101 - vista geral da cava norte bancada 3",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em area de mineracao com checklist NR22, leitura das frentes de lavra e verificacao visual das bancadas.",
            "condicoes_gerais": "Frente ativa com drenagem superficial parcial, talude principal monitorado e rota de pedestres com sinalizacao insuficiente.",
            "fase_operacional": "Lavra e carregamento",
            "estabilidade_taludes": "Talude principal monitorado com pequena fissura superficial sem deslocamento aparente.",
            "drenagem": "Canaleta lateral parcial com necessidade de recomposicao antes de nova chuva forte.",
            "ventilacao": "Area a ceu aberto com dispersao adequada de poeira durante a vistoria.",
            "trafego_equipamentos": "Fluxo de caminhoes fora de estrada cruzando a rota de pedestres em um ponto sem segregacao completa.",
            "detonacao": "Area de desmonte mantida isolada fora da janela operacional da vistoria.",
            "sinalizacao": "Sinalizacao de rota de pedestres incompleta proxima ao acesso da bancada 3.",
            "evidencia_principal": "IMG_2102 - canaleta lateral parcial na bancada 3",
            "evidencia_complementar": "IMG_2103 - rota de pedestres sem segregacao completa",
            "pgr_mineracao": "DOC_2101 - pgr_mineracao_cava_norte_rev05.pdf",
            "plano_emergencia": "DOC_2102 - plano_emergencia_cava_norte.pdf",
            "mapa_risco": "DOC_2103 - mapa_geotecnico_cava_norte.pdf",
            "art_numero": "ART 2026-00521",
            "descricao_pontos_atencao": "Drenagem superficial parcial e sinalizacao incompleta na rota de pedestres da bancada 3.",
            "conclusao": {"status": "Liberado com restricoes"},
            "observacoes": "Recompor a drenagem lateral e reforcar a segregacao da rota de pedestres antes do proximo turno chuvoso.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr22_inspecao_area_mineracao",
            template_code="nr22_inspecao_area_mineracao",
        ),
        diagnostico="Resumo executivo do caso piloto NR22 para area de mineracao.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR22",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Area de lavra Cava Norte - bancada 3"
    assert payload["identificacao"]["codigo_interno"] == "MIN-CN-B3"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_2101 - vista geral da cava norte bancada 3"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "area_mineracao"
    assert "Taludes:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Trafego equipamentos:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_2101 - pgr_mineracao_cava_norte_rev05.pdf"
    assert "Plano emergencia:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr22_inspecao_instalacao_mineira() -> None:
    laudo = SimpleNamespace(
        id=822,
        catalog_family_key="nr22_inspecao_instalacao_mineira",
        catalog_family_label="NR22 · Instalacao mineira",
        catalog_variant_label="Prime mineracao",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="mineracao",
        parecer_ia="Foi identificada protecao parcial na correia C-04 e falta de identificacao completa dos pontos de bloqueio de energia.",
        primeira_mensagem="Inspecao na britagem primaria BM-02",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Britagem primaria BM-02",
            "objeto_principal": "Instalacao mineira BM-02 - britagem primaria",
            "codigo_interno": "BM-02",
            "referencia_principal": "IMG_2201 - vista geral da britagem BM-02",
            "modo_execucao": "in loco",
            "metodo_aplicado": "Inspecao de campo em instalacao mineira com checklist NR22, verificacao operacional, bloqueios, acessos e protecoes mecânicas.",
            "condicoes_observadas": "Britagem em operacao com acessos organizados, mas correia C-04 sem protecao completa e pontos LOTO sem identificacao total.",
            "tipo_instalacao": "Britagem primaria",
            "bloqueio_energia": "Pontos de bloqueio de energia presentes, sem identificacao completa no painel local.",
            "ventilacao_exaustao": "Sistema de exaustao ativo com acúmulo leve de particulado no enclausuramento.",
            "acessos_passarelas": "Passarelas e guarda-corpos íntegros na rota principal de inspeção.",
            "correias_transportadoras": "Correia C-04 operando sem proteção integral no retorno inferior.",
            "combate_incendio": "Extintores e hidrantes inspecionados e dentro da validade.",
            "manutencao": "Rotina preventiva em dia com OS aberta para ajuste do enclausuramento.",
            "evidencia_principal": "IMG_2202 - retorno inferior da correia C-04 sem proteção integral",
            "evidencia_complementar": "IMG_2203 - painel local sem identificação completa dos pontos LOTO",
            "pgr_mineracao": "DOC_2201 - pgr_britagem_rev04.pdf",
            "procedimento_operacional": "DOC_2202 - procedimento_britagem_bm02.pdf",
            "plano_emergencia": "DOC_2203 - plano_emergencia_beneficiamento.pdf",
            "pte": "DOC_2204 - permissao_intervencao_bm02.pdf",
            "art_numero": "ART 2026-00522",
            "descricao_pontos_atencao": "Protecao parcial na correia C-04 e identificacao incompleta dos pontos de bloqueio de energia.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Completar a proteção da correia e revisar a identificação LOTO antes da próxima intervenção corretiva.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr22_inspecao_instalacao_mineira",
            template_code="nr22_inspecao_instalacao_mineira",
        ),
        diagnostico="Resumo executivo do caso piloto NR22 para instalação mineira.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR22",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Instalacao mineira BM-02 - britagem primaria"
    assert payload["identificacao"]["codigo_interno"] == "BM-02"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_2201 - vista geral da britagem BM-02"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "instalacao_mineira"
    assert "Bloqueio energia:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Correias:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_2201 - pgr_britagem_rev04.pdf"
    assert "Procedimento:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "PTE:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr29_inspecao_operacao_portuaria() -> None:
    laudo = SimpleNamespace(
        id=829,
        catalog_family_key="nr29_inspecao_operacao_portuaria",
        catalog_family_label="NR29 · Operacao portuaria",
        catalog_variant_label="Prime porto",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="portuario",
        parecer_ia="Foi identificada area de pedestres sem segregacao completa proxima ao guindaste movel e sinalizacao parcial no acesso ao cais.",
        primeira_mensagem="Inspecao na operacao de descarga do berco 5 terminal leste",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Terminal Leste - berco 5",
            "objeto_principal": "Operacao de descarga no berco 5 do terminal leste",
            "codigo_interno": "PORTO-B5-2026",
            "referencia_principal": "IMG_2901 - vista geral da operacao no berco 5",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em operacao portuaria com checklist NR29, verificacao de equipamentos, fluxos de carga e acessos ao cais.",
            "condicoes_gerais": "Operacao em andamento com guindaste movel, fluxo de caminhes e area de pedestres com segregacao parcial proxima ao berco.",
            "tipo_operacao": "Descarga de bobinas de aco",
            "equipamento_portuario": "Guindaste movel MHC-04",
            "movimentacao_carga": "Bobinas descarregadas do porao 2 para carretas no patio temporario.",
            "acesso_cais": "Acesso principal sinalizado, com cruzamento pontual de pedestres proximo a area de descarga.",
            "sinalizacao": "Sinalizacao parcial no corredor lateral de pedestres.",
            "amarracao": "Atracacao e amarracao estaveis durante a vistoria.",
            "comunicacao_operacional": "Comunicacao por radio entre equipe de bordo e operador do guindaste.",
            "condicoes_piso": "Piso do cais regular, com marca de oleo seca sem escorregamento no trecho lateral.",
            "evidencia_principal": "IMG_2902 - corredor de pedestres sem segregacao completa",
            "evidencia_complementar": "IMG_2903 - operacao do guindaste MHC-04 no berco 5",
            "pgr_portuario": "DOC_2901 - pgr_portuario_terminal_leste_rev03.pdf",
            "apr": "DOC_2902 - apr_descarga_bobinas_berco5.pdf",
            "procedimento_operacional": "DOC_2903 - procedimento_descarga_bobinas.pdf",
            "plano_emergencia": "DOC_2904 - plano_emergencia_terminal_leste.pdf",
            "descricao_pontos_atencao": "Segregacao incompleta de pedestres proxima a area de descarga e sinalizacao parcial no acesso lateral do cais.",
            "conclusao": {"status": "Liberado com restricoes"},
            "observacoes": "Reforcar a segregacao de pedestres e completar a sinalizacao lateral antes da proxima janela operacional.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr29_inspecao_operacao_portuaria",
            template_code="nr29_inspecao_operacao_portuaria",
        ),
        diagnostico="Resumo executivo do caso piloto NR29 para operacao portuaria.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR29",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Operacao de descarga no berco 5 do terminal leste"
    assert payload["identificacao"]["codigo_interno"] == "PORTO-B5-2026"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_2901 - vista geral da operacao no berco 5"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "operacao_portuaria"
    assert "Equipamento:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Movimentacao carga:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_2901 - pgr_portuario_terminal_leste_rev03.pdf"
    assert "Procedimento:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "Plano emergencia:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr30_inspecao_trabalho_aquaviario() -> None:
    laudo = SimpleNamespace(
        id=830,
        catalog_family_key="nr30_inspecao_trabalho_aquaviario",
        catalog_family_label="NR30 · Trabalho aquaviario",
        catalog_variant_label="Prime aquaviario",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="aquaviario",
        parecer_ia="Foi identificada protecao parcial no acesso ao conves inferior e comunicacao operacional irregular durante a transferencia de carga.",
        primeira_mensagem="Inspecao na embarcacao Atlas durante transferencia no conves principal",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Embarcacao Atlas - conves principal",
            "objeto_principal": "Transferencia de carga na embarcacao Atlas",
            "codigo_interno": "AQUA-ATL-01",
            "referencia_principal": "IMG_3001 - vista geral do conves principal da Atlas",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em trabalho aquaviario com checklist NR30, verificacao de acessos, condicoes de bordo e controles de emergencia.",
            "condicoes_gerais": "Operacao em andamento com acesso ao conves inferior sem barreira completa e ruido alto prejudicando a comunicacao da equipe.",
            "tipo_embarcacao": "Carga geral",
            "atividade_bordo": "Transferencia de carga no conves principal",
            "acesso_embarcacao": "Escada de acesso lateral com trecho inferior sem protecao completa.",
            "coletes_epis": "Tripulacao com coletes e capacetes, com necessidade de reforcar uso de protetor auricular no trecho ruidoso.",
            "comunicacao_operacional": "Comunicacao por radio com falhas intermitentes entre conves principal e equipe de apoio.",
            "estabilidade_operacao": "Operacao mantida estavel durante a vistoria, sem oscilacao anormal da embarcacao.",
            "abandono_emergencia": "Rotas de abandono sinalizadas, com ponto de encontro confirmado no portal de bombordo.",
            "condicoes_conves": "Conves principal seco, com treliça lateral organizada e um ponto de acesso sem barreira completa.",
            "evidencia_principal": "IMG_3002 - acesso inferior sem protecao completa",
            "evidencia_complementar": "IMG_3003 - equipe em comunicacao por radio durante a transferencia",
            "pgr_embarcacao": "DOC_3001 - pgr_embarcacao_atlas_rev02.pdf",
            "apr": "DOC_3002 - apr_transferencia_carga_atlas.pdf",
            "procedimento_operacional": "DOC_3003 - procedimento_transferencia_conves.pdf",
            "plano_emergencia": "DOC_3004 - plano_emergencia_atlas.pdf",
            "checklist_bordo": "DOC_3005 - checklist_nr30_conves_principal.pdf",
            "descricao_pontos_atencao": "Acesso ao conves inferior sem protecao completa e comunicacao operacional irregular durante a transferencia de carga.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Regularizar a protecao do acesso inferior e revisar a redundancia de comunicacao antes da proxima transferencia.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr30_inspecao_trabalho_aquaviario",
            template_code="nr30_inspecao_trabalho_aquaviario",
        ),
        diagnostico="Resumo executivo do caso piloto NR30 para trabalho aquaviario.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR30",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Transferencia de carga na embarcacao Atlas"
    assert payload["identificacao"]["codigo_interno"] == "AQUA-ATL-01"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_3001 - vista geral do conves principal da Atlas"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "trabalho_aquaviario"
    assert "Tipo embarcacao:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Comunicacao:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_3001 - pgr_embarcacao_atlas_rev02.pdf"
    assert "Checklist:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "Plano emergencia:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr31_inspecao_frente_rural() -> None:
    laudo = SimpleNamespace(
        id=831,
        catalog_family_key="nr31_inspecao_frente_rural",
        catalog_family_label="NR31 · Frente rural",
        catalog_variant_label="Prime rural",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="rural",
        parecer_ia="Foi identificada protecao incompleta na tomada de forca do trator e armazenamento inadequado de defensivos proximo a area de vivencia.",
        primeira_mensagem="Inspecao na frente rural do talhao 7 da Fazenda Boa Esperanca",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Fazenda Boa Esperanca - talhao 7",
            "objeto_principal": "Frente rural de colheita no talhao 7",
            "codigo_interno": "RURAL-T7-2026",
            "referencia_principal": "IMG_3101 - vista geral da frente de colheita no talhao 7",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em frente rural com checklist NR31, verificacao de maquinas, frentes de trabalho, areas de apoio e controles operacionais.",
            "condicoes_gerais": "Frente de colheita em operacao com trator e carreta, area de apoio provisoria e deposito de defensivos proximo ao refeitório.",
            "cultura_atividade": "Colheita de cana-de-acucar",
            "maquinas_tratores": "Trator T-19 com tomada de forca sem protecao completa no eixo secundario.",
            "aplicacao_defensivos": "Pulverizacao encerrada no dia anterior, com embalagens vazias aguardando recolhimento.",
            "armazenamento_insumos": "Defensivos armazenados provisoriamente em abrigo sem segregacao adequada do ponto de refeicao.",
            "alojamento_apoio": "Area de apoio com sombra, agua e refeitorio improvisado a 30 metros da frente principal.",
            "abastecimento_agua": "Agua potavel disponivel em reservatorio identificado e protegido.",
            "transporte_trabalhadores": "Transporte interno realizado em caminhonete com lotacao controlada.",
            "sinalizacao": "Sinalizacao parcial no limite entre frente de maquinario e circulacao de pedestres.",
            "evidencia_principal": "IMG_3102 - tomada de forca com protecao parcial",
            "evidencia_complementar": "IMG_3103 - armazenamento provisório de defensivos proximo ao refeitorio",
            "pgr_rural": "DOC_3101 - pgr_rural_fazenda_boa_esperanca_rev03.pdf",
            "apr": "DOC_3102 - apr_colheita_talhao7.pdf",
            "procedimento_operacional": "DOC_3103 - procedimento_colheita_mecanizada.pdf",
            "treinamento_operadores": "DOC_3104 - treinamento_operadores_talhao7.pdf",
            "descricao_pontos_atencao": "Tomada de forca com protecao incompleta e armazenamento inadequado de defensivos proximo a area de vivencia.",
            "conclusao": {"status": "Liberado com restricoes"},
            "observacoes": "Completar a protecao da tomada de forca e reorganizar o armazenamento de defensivos antes do proximo turno.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr31_inspecao_frente_rural",
            template_code="nr31_inspecao_frente_rural",
        ),
        diagnostico="Resumo executivo do caso piloto NR31 para frente rural.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR31",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Frente rural de colheita no talhao 7"
    assert payload["identificacao"]["codigo_interno"] == "RURAL-T7-2026"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_3101 - vista geral da frente de colheita no talhao 7"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "frente_rural"
    assert "Maquinas tratores:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Armazenamento insumos:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_3101 - pgr_rural_fazenda_boa_esperanca_rev03.pdf"
    assert "Treinamento:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "Procedimento:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr32_inspecao_servico_saude() -> None:
    laudo = SimpleNamespace(
        id=832,
        catalog_family_key="nr32_inspecao_servico_saude",
        catalog_family_label="NR32 · Inspecao servico saude",
        catalog_variant_label="Prime saude",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="saude",
        parecer_ia="Foi identificada segregacao parcial de residuos e necessidade de reforcar o fluxo de perfurocortantes no CME.",
        primeira_mensagem="Inspecao no centro de material e esterilizacao do Hospital Central",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Hospital Central - centro de material e esterilizacao",
            "objeto_principal": "CME do Hospital Central",
            "codigo_interno": "NR32-CME-01",
            "referencia_principal": "IMG_3201 - vista geral do CME do Hospital Central",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em servico de saude com checklist NR32, leitura de fluxos limpo/sujo e verificacao das barreiras de biosseguranca.",
            "condicoes_gerais": "Setor em operacao com segregacao funcional adequada, mas com ponto de descarte de perfurocortantes e segregacao de residuos precisando de reforco.",
            "setor_assistencial": "Centro de material e esterilizacao",
            "segregacao_residuos": "Segregacao presente, com coletor de residuos infectantes sem identificacao completa em uma das bancadas.",
            "perfurocortantes": "Caixa de perfurocortantes acima da linha recomendada em posto secundario.",
            "higienizacao": "Rotina de limpeza e desinfeccao registrada e atualizada.",
            "epc_epi": "Equipe com avental impermeavel, luvas e protetor facial disponiveis.",
            "fluxo_material_biologico": "Fluxo limpo/sujo definido, com um ponto de cruzamento temporario em horario de pico.",
            "sinalizacao": "Sinalizacao biossegura presente, com reforco necessario no posto secundario.",
            "evidencia_principal": "IMG_3202 - coletor de perfurocortantes no posto secundario",
            "evidencia_complementar": "IMG_3203 - bancada de segregacao de residuos do CME",
            "pgrss": "DOC_3201 - pgrss_hospital_central_rev06.pdf",
            "pcmso": "DOC_3202 - pcmso_hospital_central_2026.pdf",
            "procedimento_operacional": "DOC_3203 - procedimento_cme_fluxo_limpo_sujo.pdf",
            "plano_contingencia": "DOC_3204 - plano_contingencia_exposicao_biologica.pdf",
            "treinamento_equipe": "DOC_3205 - treinamento_biosseguranca_cme_2026.pdf",
            "descricao_pontos_atencao": "Segregacao parcial de residuos e caixa de perfurocortantes acima da linha recomendada no posto secundario.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Regularizar o descarte de perfurocortantes e reforcar a identificacao dos coletores do CME.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr32_inspecao_servico_saude",
            template_code="nr32_inspecao_servico_saude",
        ),
        diagnostico="Resumo executivo do caso piloto NR32 para servico de saude.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR32",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "CME do Hospital Central"
    assert payload["identificacao"]["codigo_interno"] == "NR32-CME-01"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_3201 - vista geral do CME do Hospital Central"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "servico_saude"
    assert "Setor assistencial:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Perfurocortantes:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_3201 - pgrss_hospital_central_rev06.pdf"
    assert "PGRSS:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "Plano contingencia:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr32_plano_risco_biologico() -> None:
    laudo = SimpleNamespace(
        id=833,
        catalog_family_key="nr32_plano_risco_biologico",
        catalog_family_label="NR32 · Plano risco biologico",
        catalog_variant_label="Prime saude documental",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="saude",
        parecer_ia="O plano de risco biologico foi consolidado, mas ainda depende de fechar o protocolo de exposicao para o laboratorio de microbiologia.",
        primeira_mensagem="Analise documental do plano de risco biologico do Hospital Central",
        motivo_rejeicao=None,
        dados_formulario={
            "localizacao": "Hospital Central - laboratorio de microbiologia",
            "objeto_principal": "Plano de risco biologico do Hospital Central",
            "codigo_interno": "PRB-HC-2026",
            "numero_plano": "PRB-2026-04",
            "referencia_principal": "DOC_3210 - plano_risco_biologico_hospital_central_rev02.pdf",
            "modo_execucao": "analise documental",
            "metodo_aplicado": "Analise documental do plano de risco biologico com consolidacao do inventario de agentes, protocolos de exposicao e planos de contingencia.",
            "status_documentacao": "Plano consolidado com pendencia de detalhar o protocolo de exposicao do laboratorio de microbiologia.",
            "plano_risco_biologico": "DOC_3210 - plano_risco_biologico_hospital_central_rev02.pdf",
            "mapa_risco_biologico": "DOC_3211 - mapa_risco_biologico_laboratorios.pdf",
            "inventario_agentes": "DOC_3212 - inventario_agentes_biologicos_2026.xlsx",
            "protocolo_exposicao": "DOC_3213 - protocolo_exposicao_acidentes_biologicos.docx",
            "plano_contingencia": "DOC_3214 - plano_contingencia_biologica_hc.pdf",
            "treinamento_equipe": "DOC_3215 - treinamento_biosseguranca_laboratorio_2026.pdf",
            "pgrss": "DOC_3216 - pgrss_hospital_central_rev06.pdf",
            "pcmso": "DOC_3217 - pcmso_hospital_central_2026.pdf",
            "art_numero": "ART 2026-00532",
            "evidencia_principal": "DOC_3210 - plano_risco_biologico_hospital_central_rev02.pdf",
            "descricao_pontos_atencao": "Detalhar o protocolo de exposicao do laboratorio de microbiologia e vincular a contingencia especifica ao plano consolidado.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Fechar o protocolo de exposicao do laboratorio e reemitir a revisao do plano de risco biologico.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr32_plano_risco_biologico",
            template_code="nr32_plano_risco_biologico",
        ),
        diagnostico="Resumo executivo do caso piloto NR32 para plano de risco biologico.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR32",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Plano de risco biologico do Hospital Central"
    assert payload["identificacao"]["codigo_interno"] == "PRB-HC-2026"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "DOC_3210 - plano_risco_biologico_hospital_central_rev02.pdf"
    assert payload["escopo_servico"]["tipo_entrega"] == "pacote_documental"
    assert payload["escopo_servico"]["modo_execucao"] == "analise_documental"
    assert payload["escopo_servico"]["ativo_tipo"] == "risco_biologico"
    assert "Mapa risco:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Status documental:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_3210 - plano_risco_biologico_hospital_central_rev02.pdf"
    assert "Inventario agentes:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "PGRSS:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr34_inspecao_frente_naval() -> None:
    laudo = SimpleNamespace(
        id=834,
        catalog_family_key="nr34_inspecao_frente_naval",
        catalog_family_label="NR34 · Frente naval",
        catalog_variant_label="Prime naval",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="naval",
        parecer_ia="Foi identificada ventilacao parcial no tanque lateral e isolamento incompleto da area de trabalho a quente no bloco 12.",
        primeira_mensagem="Inspecao na frente de reparacao naval do bloco 12 no Estaleiro Atlantico",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Estaleiro Atlantico - doca 2 bloco 12",
            "objeto_principal": "Frente de reparacao naval do bloco 12",
            "codigo_interno": "NAV-B12-2026",
            "referencia_principal": "IMG_3401 - vista geral da frente naval do bloco 12",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em frente naval com checklist NR34, verificacao de trabalho a quente, ventilacao e segregacao da area operacional.",
            "condicoes_gerais": "Frente de reparacao em andamento com solda estrutural, tanque lateral sob ventilacao auxiliar e corredor de acesso parcialmente isolado.",
            "fase_obra_naval": "Reparacao estrutural com solda e esmerilhamento",
            "trabalho_quente": "Solda em chaparia lateral com permissao emitida e necessidade de ampliar o isolamento do entorno imediato.",
            "espaco_confinado": "Tanque lateral acessado para ajuste interno com monitoramento ativo.",
            "ventilacao_exaustao": "Ventilacao auxiliar presente, mas com renovacao insuficiente no fundo do tanque lateral.",
            "movimentacao_cargas": "Içamento de chapas programado na mesma doca, fora do raio imediato da frente.",
            "protecao_contra_queda": "Linha de vida e guarda-corpos presentes no acesso superior da estrutura.",
            "isolamento_area": "Isolamento parcial no corredor lateral durante trabalho a quente.",
            "sinalizacao": "Sinalizacao de risco presente, com necessidade de reforco no acesso secundario.",
            "evidencia_principal": "IMG_3402 - ventilacao auxiliar no tanque lateral",
            "evidencia_complementar": "IMG_3403 - isolamento parcial do corredor lateral",
            "pgr_naval": "DOC_3401 - pgr_naval_estaleiro_atlantico_rev03.pdf",
            "apr": "DOC_3402 - apr_reparo_bloco12.pdf",
            "permissao_trabalho_quente": "DOC_3403 - pte_quente_bloco12.pdf",
            "permissao_espaco_confinado": "DOC_3404 - pte_tanque_lateral_bloco12.pdf",
            "procedimento_operacional": "DOC_3405 - procedimento_reparo_estrutural_bloco12.pdf",
            "plano_emergencia": "DOC_3406 - plano_emergencia_doca2.pdf",
            "descricao_pontos_atencao": "Ventilacao parcial no tanque lateral e isolamento incompleto da area de trabalho a quente no bloco 12.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Reforcar o isolamento do corredor lateral e elevar a renovacao de ar no tanque antes da proxima janela de solda.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr34_inspecao_frente_naval",
            template_code="nr34_inspecao_frente_naval",
        ),
        diagnostico="Resumo executivo do caso piloto NR34 para frente naval.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR34",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Frente de reparacao naval do bloco 12"
    assert payload["identificacao"]["codigo_interno"] == "NAV-B12-2026"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_3401 - vista geral da frente naval do bloco 12"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "frente_naval"
    assert "Trabalho a quente:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Ventilacao:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_3401 - pgr_naval_estaleiro_atlantico_rev03.pdf"
    assert "Permissao quente:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "Plano emergencia:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr36_inspecao_unidade_abate_processamento() -> None:
    laudo = SimpleNamespace(
        id=836,
        catalog_family_key="nr36_inspecao_unidade_abate_processamento",
        catalog_family_label="NR36 · Unidade abate processamento",
        catalog_variant_label="Prime frigorifico",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="frigorifico",
        parecer_ia="Foi identificada pausa termica insuficiente na desossa e piso umido sem segregacao completa no corredor de abastecimento.",
        primeira_mensagem="Inspecao na unidade de desossa e corte da Planta Sul",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Planta Sul - setor de desossa e corte",
            "objeto_principal": "Unidade de desossa e corte da Planta Sul",
            "codigo_interno": "FRIGO-DS-12",
            "referencia_principal": "IMG_3601 - vista geral da linha de desossa 12",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em unidade de abate e processamento com checklist NR36, verificacao de pausas, ergonomia e condicoes termicas.",
            "condicoes_gerais": "Linha em operacao com ritmo elevado, pausas insuficientes na desossa e corredor de abastecimento com piso umido.",
            "setor_produtivo": "Desossa e corte",
            "temperatura_ambiente": "10 C no setor com exposicao continua da equipe.",
            "pausas_termicas": "Escala de pausas abaixo do previsto para o turno da tarde.",
            "ergonomia_posto": "Postos repetitivos com necessidade de rever altura da mesa secundaria.",
            "facas_ferramentas": "Facas em uso com chaira e suporte organizados no posto principal.",
            "higienizacao": "Rotina de higienizacao em andamento entre lotes.",
            "epc_epi": "Luvas, mangotes e aventais disponiveis, com reforco necessario no uso do protetor auricular.",
            "piso_drenagem": "Corredor de abastecimento com umidade e drenagem parcial no trecho lateral.",
            "evidencia_principal": "IMG_3602 - piso umido no corredor de abastecimento",
            "evidencia_complementar": "IMG_3603 - posto de desossa com ajuste ergonomico pendente",
            "pgr_frigorifico": "DOC_3601 - pgr_planta_sul_rev04.pdf",
            "apr": "DOC_3602 - apr_desossa_turno_tarde.pdf",
            "procedimento_operacional": "DOC_3603 - procedimento_desossa_corte.pdf",
            "programa_pausas": "DOC_3604 - programa_pausas_termicas_turno_tarde.pdf",
            "pcmso": "DOC_3605 - pcmso_planta_sul_2026.pdf",
            "descricao_pontos_atencao": "Pausa termica insuficiente na desossa e piso umido sem segregacao completa no corredor de abastecimento.",
            "conclusao": {"status": "Liberado com restricoes"},
            "observacoes": "Ajustar a escala de pausas e reforcar a segregacao do corredor antes do proximo pico operacional.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr36_inspecao_unidade_abate_processamento",
            template_code="nr36_inspecao_unidade_abate_processamento",
        ),
        diagnostico="Resumo executivo do caso piloto NR36 para unidade de abate e processamento.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR36",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Unidade de desossa e corte da Planta Sul"
    assert payload["identificacao"]["codigo_interno"] == "FRIGO-DS-12"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_3601 - vista geral da linha de desossa 12"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "unidade_abate_processamento"
    assert "Pausas termicas:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Ergonomia:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_3601 - pgr_planta_sul_rev04.pdf"
    assert "Programa pausas:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "PCMSO:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr37_inspecao_plataforma_petroleo() -> None:
    laudo = SimpleNamespace(
        id=837,
        catalog_family_key="nr37_inspecao_plataforma_petroleo",
        catalog_family_label="NR37 · Plataforma petroleo",
        catalog_variant_label="Prime offshore",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="offshore",
        parecer_ia="O pacote documental da plataforma foi consolidado, mas ainda depende de atualizar o inventario de riscos do modulo de compressao.",
        primeira_mensagem="Analise documental da Plataforma Aurora",
        motivo_rejeicao=None,
        dados_formulario={
            "localizacao": "Plataforma Aurora - modulo de processo e habitacao",
            "objeto_principal": "Pacote documental da Plataforma Aurora",
            "codigo_interno": "PLAT-AUR-2026",
            "codigo_plataforma": "AUR-01",
            "referencia_principal": "DOC_3701 - pacote_nr37_plataforma_aurora_rev03.pdf",
            "modo_execucao": "analise documental",
            "metodo_aplicado": "Analise documental de plataforma de petroleo com consolidacao do inventario de riscos, planos de resposta e matriz de treinamentos.",
            "status_documentacao": "Pacote consolidado com pendencia de atualizar o inventario de riscos do modulo de compressao.",
            "unidade_offshore": "Plataforma fixa Aurora",
            "inventario_riscos": "DOC_3702 - inventario_riscos_modulo_compressao.xlsx",
            "trabalho_quente": "Procedimento e controle documental vigentes para o modulo de manutencao.",
            "espaco_confinado": "Permissao e matriz de controles documentadas para tanques de processo.",
            "abandono_emergencia": "Plano de abandono e pontos de encontro revisados em 2026.",
            "habitabilidade": "Acomodacoes e areas comuns com programa de manutencao e limpeza registrado.",
            "matriz_treinamentos": "DOC_3703 - matriz_treinamentos_offshore_2026.xlsx",
            "pgr_plataforma": "DOC_3704 - pgr_plataforma_aurora_rev05.pdf",
            "plano_resposta_emergencia": "DOC_3705 - plano_resposta_aurora_rev04.pdf",
            "procedimento_operacional": "DOC_3706 - procedimento_operacional_modulo_processo.pdf",
            "pcmso": "DOC_3707 - pcmso_offshore_aurora_2026.pdf",
            "art_numero": "ART 2026-00537",
            "evidencia_principal": "DOC_3701 - pacote_nr37_plataforma_aurora_rev03.pdf",
            "descricao_pontos_atencao": "Atualizar o inventario de riscos do modulo de compressao e reemitir a referencia consolidada do pacote NR37.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Fechar a revisao do inventario de riscos e republicar o pacote documental offshore.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr37_inspecao_plataforma_petroleo",
            template_code="nr37_inspecao_plataforma_petroleo",
        ),
        diagnostico="Resumo executivo do caso piloto NR37 para plataforma de petroleo.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR37",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Pacote documental da Plataforma Aurora"
    assert payload["identificacao"]["codigo_interno"] == "PLAT-AUR-2026"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "DOC_3701 - pacote_nr37_plataforma_aurora_rev03.pdf"
    assert payload["escopo_servico"]["tipo_entrega"] == "pacote_documental"
    assert payload["escopo_servico"]["modo_execucao"] == "analise_documental"
    assert payload["escopo_servico"]["ativo_tipo"] == "plataforma_petroleo"
    assert "Inventario riscos:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Status documental:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_3704 - pgr_plataforma_aurora_rev05.pdf"
    assert "Plano emergencia:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "PCMSO:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr38_inspecao_limpeza_urbana_residuos() -> None:
    laudo = SimpleNamespace(
        id=838,
        catalog_family_key="nr38_inspecao_limpeza_urbana_residuos",
        catalog_family_label="NR38 · Limpeza urbana residuos",
        catalog_variant_label="Prime urbana",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="limpeza_urbana",
        parecer_ia="Foi identificada segregacao parcial do trafego viario e necessidade de reforcar a higienizacao do compartimento traseiro do caminhão.",
        primeira_mensagem="Inspecao na rota de coleta Centro Norte",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Base Centro Norte e rota de coleta urbana",
            "objeto_principal": "Rota de coleta urbana Centro Norte",
            "codigo_interno": "URB-CN-07",
            "referencia_principal": "IMG_3801 - vista geral do caminhão coletor CN-07",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao de campo em limpeza urbana com checklist NR38, verificacao da coleta, manuseio de residuos e trafego da rota.",
            "condicoes_gerais": "Operacao em andamento com equipe completa, trafego intenso em corredor central e compartimento traseiro com higienizacao pendente.",
            "tipo_operacao": "Coleta domiciliar convencional",
            "coleta_manual": "Coleta porta a porta com equipe de tres garis na rota central.",
            "manuseio_residuos": "Volume regular com pontos de descarte irregular misturados ao fluxo convencional.",
            "frota_equipamento": "Caminhão coletor compactador CN-07 em operacao regular.",
            "segregacao_trafego": "Corredor central sem cones suficientes em trecho de travessia intensa.",
            "higienizacao": "Lavagem do compartimento traseiro pendente ao fim do turno anterior.",
            "epc_epi": "Luvas, botinas, uniforme refletivo e protetor auricular disponiveis.",
            "sinalizacao": "Sinalizacao luminosa ativa, com reforco necessario na travessia do corredor central.",
            "evidencia_principal": "IMG_3802 - travessia com segregacao parcial do trafego",
            "evidencia_complementar": "IMG_3803 - compartimento traseiro aguardando higienizacao final",
            "pgr_limpeza_urbana": "DOC_3801 - pgr_limpeza_urbana_rev03.pdf",
            "apr": "DOC_3802 - apr_rota_centro_norte.pdf",
            "procedimento_operacional": "DOC_3803 - procedimento_coleta_domiciliar.pdf",
            "plano_emergencia": "DOC_3804 - plano_emergencia_frota_urbana.pdf",
            "checklist_frota": "DOC_3805 - checklist_caminhao_cn07.pdf",
            "treinamento_equipe": "DOC_3806 - treinamento_seguranca_coleta_2026.pdf",
            "descricao_pontos_atencao": "Segregacao parcial do trafego viario e necessidade de reforcar a higienizacao do compartimento traseiro do caminhão.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Completar a segregacao do corredor central e normalizar a higienizacao do compartimento antes do proximo turno.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr38_inspecao_limpeza_urbana_residuos",
            template_code="nr38_inspecao_limpeza_urbana_residuos",
        ),
        diagnostico="Resumo executivo do caso piloto NR38 para limpeza urbana e residuos.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR38",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Rota de coleta urbana Centro Norte"
    assert payload["identificacao"]["codigo_interno"] == "URB-CN-07"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_3801 - vista geral do caminhão coletor CN-07"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "limpeza_urbana_residuos"
    assert "Coleta manual:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Segregacao trafego:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_3801 - pgr_limpeza_urbana_rev03.pdf"
    assert "Checklist:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "Treinamento:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr12_inspecao_maquina_equipamento() -> None:
    laudo = SimpleNamespace(
        id=512,
        catalog_family_key="nr12_inspecao_maquina_equipamento",
        catalog_family_label="NR12 · Maquina e equipamento",
        catalog_variant_label="Prime machine",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="estamparia",
        parecer_ia="Foi identificado intertravamento inoperante na porta frontal e acesso perigoso na zona de alimentacao.",
        primeira_mensagem="Inspecao inicial na prensa hidraulica PH-07 da linha de estampagem",
        motivo_rejeicao=None,
        dados_formulario={
            "unidade": "Itumbiara - GO",
            "local_inspecao": "Linha de estampagem - prensa PH-07",
            "objeto_principal": "Prensa hidraulica PH-07",
            "codigo_interno": "PH-07",
            "relatorio_codigo": "wf.crm.202604.est.00007 ph07",
            "numero_laudo": "EST0426WF_PRS",
            "data_laudo": "2026-04-09",
            "mes_inspecao": "Abril 2026",
            "tipo_inspecao": "Inicial",
            "contratante": "Caramuru Alimentos S/A",
            "executante": "WF Solucoes Industriais e Inspecoes LTDA",
            "responsavel_tecnico": "Gabriel Santos",
            "inspetor": "Marcel Renato Silva",
            "funcao": "Prensagem de componentes metalicos",
            "fabricante": "Promec",
            "modelo": "PH-07",
            "numero_serie": "PRS77821",
            "tag": "PH-07",
            "voltagem": "380",
            "comando": "Semi-automatico",
            "operadores_por_turno": "2",
            "art_numero": "ART 2026-00412",
            "referencia_principal": "IMG_401 - vista frontal da PH-07",
            "modo_execucao": "in loco",
            "objetivo": "Verificar protecoes, intertravamentos, parada de emergencia e acessos de risco conforme NR12.",
            "normas_aplicaveis": "NR-12; NR-10; NBR 14153; ISO 13850",
            "generalidades": "Inspecao realizada com a maquina em operacao controlada e entrevistas com operadores.",
            "descricao_escopo": "Inspecao inicial da prensa hidraulica PH-07 com checklist por grupos, registro fotografico e recomendacoes de adequacao.",
            "categoria_maquina": "Prensa hidraulica",
            "processo_associado": "Linha de estampagem",
            "metodo_inspecao": "Inspecao visual funcional com checklist NR12 e teste de parada de emergencia.",
            "checklist_referencia": "Checklist NR12 estruturado por grupos 5.1 a 5.6.",
            "criterios_risco": "Grafico de Risco NBR 14153 com priorizacao HRN.",
            "condicoes_gerais": "Protecoes laterais presentes, com porta frontal abrindo sem bloqueio de movimento.",
            "guardas_protecoes": "Protecao lateral integra, com abertura frontal sem enclausuramento efetivo.",
            "parada_emergencia": "Botoeira frontal presente e reset manual disponivel.",
            "intertravamentos": "Porta frontal abre sem bloquear o movimento da maquina.",
            "zona_risco": "Acesso perigoso identificado no lado de alimentacao durante setup.",
            "sinalizacao": "Sinalizacao frontal insuficiente para troca de ferramental.",
            "procedimento_bloqueio": "LOTO aplicavel descrito no procedimento de manutencao.",
            "evidencia_principal": "IMG_402 - porta frontal aberta com movimento habilitado",
            "evidencia_complementar": "IMG_403 - botoeira de emergencia frontal",
            "manual_maquina": "DOC_051 - manual_prensa_ph07.pdf",
            "inventario_maquinas": "DOC_052 - inventario_nr12_linha_a.pdf",
            "checklist_nr12": "DOC_053 - checklist_nr12_ph07.pdf",
            "apreciacao_risco": "DOC_054 - apreciacao_risco_ph07.pdf",
            "grafico_risco_categoria": "Categoria 3 | S2 F2 P1",
            "grau_risco_antes": "Alto para acesso frontal e intertravamento inoperante.",
            "grau_risco_apos": "Pendente de reavaliacao apos adequacoes.",
            "resumo_risco": "Risco principal concentrado na porta frontal sem bloqueio de movimento e no acesso perigoso durante setup.",
            "grupos_checklist": {
                "arranjos_fisicos_instalacoes": {
                    "status": "atencao",
                    "comentarios": "Area permite operacao, mas requer melhor isolamento no setup.",
                    "risco_nivel": "Atencao",
                },
                "instalacoes_eletricas_partida_parada": {
                    "status": "ajuste",
                    "comentarios": "Dispositivos de partida exigem reorganizacao do conjunto de acionamento.",
                    "risco_nivel": "Moderado",
                },
                "sistemas_seguranca_transportadores": {
                    "status": "nao_conforme",
                    "comentarios": "Intertravamento frontal inoperante e acesso perigoso na alimentacao.",
                    "risco_nivel": "Alto",
                },
                "aspectos_ergonomicos": {
                    "status": "conforme",
                    "comentarios": "Posto de operacao com boa visibilidade geral.",
                    "risco_nivel": "Baixo",
                },
                "riscos_adicionais_manutencao_sinalizacao": {
                    "status": "ajuste",
                    "comentarios": "Sinalizacao frontal e bloqueio para manutencao precisam ser reforcados.",
                    "risco_nivel": "Significativo",
                },
                "manuais_procedimentos_capacitacao": {
                    "status": "conforme_com_ressalvas",
                    "comentarios": "Manual disponivel; POP precisa revisao apos adequacoes.",
                    "risco_nivel": "Controlado",
                },
            },
            "descricao_pontos_atencao": "Intertravamento da porta frontal inoperante e acesso perigoso na zona de alimentacao.",
            "observacoes": "Ajustar intertravamento, revisar enclausuramento frontal e revalidar a maquina apos correcoes.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr12_inspecao_maquina_equipamento",
            template_code="nr12_inspecao_maquina_equipamento",
        ),
        diagnostico="Resumo executivo do caso piloto NR12 para prensa hidraulica.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR12",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Prensa hidraulica PH-07"
    assert payload["identificacao"]["codigo_interno"] == "PH-07"
    assert payload["identificacao"]["relatorio_codigo"] == "wf.crm.202604.est.00007 ph07"
    assert payload["identificacao"]["numero_laudo"] == "EST0426WF_PRS"
    assert payload["identificacao"]["tipo_inspecao"] == "Inicial"
    assert payload["identificacao"]["contratante"] == "Caramuru Alimentos S/A"
    assert payload["identificacao"]["executante"] == "WF Solucoes Industriais e Inspecoes LTDA"
    assert payload["identificacao"]["responsavel_tecnico"] == "Gabriel Santos"
    assert payload["identificacao"]["inspetor"] == "Marcel Renato Silva"
    assert payload["identificacao"]["tag"] == "PH-07"
    assert payload["identificacao"]["art_numero"] == "ART 2026-00412"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_401 - vista frontal da PH-07"
    assert payload["objetivo_e_base_normativa"]["objetivo"].startswith("Verificar protecoes")
    assert "NBR 14153" in str(payload["objetivo_e_base_normativa"]["normas_aplicaveis"])
    assert payload["objeto_inspecao"]["categoria_maquina"] == "Prensa hidraulica"
    assert payload["objeto_inspecao"]["processo_associado"] == "Linha de estampagem"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "prensa_hidraulica"
    assert payload["metodologia_e_criterios"]["checklist_referencia"] == "Checklist NR12 estruturado por grupos 5.1 a 5.6."
    assert "NBR 14153" in str(payload["metodologia_e_criterios"]["criterios_risco"])
    assert "Intertravamentos:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["checklist_grupos"]["sistemas_seguranca_transportadores"]["status"] == "nao_conforme"
    assert payload["checklist_grupos"]["sistemas_seguranca_transportadores"]["risco_nivel"] == "Alto"
    assert payload["checklist_componentes"]["comandos_e_intertravamentos"]["condicao"] == "NC"
    assert payload["checklist_componentes"]["zona_de_risco_e_acesso"]["condicao"] == "NC"
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_051 - manual_prensa_ph07.pdf"
    assert "Manual:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "Checklist NR12:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["documentacao_e_registros"]["manual_maquina"] == "DOC_051 - manual_prensa_ph07.pdf"
    assert payload["documentacao_e_registros"]["apreciacao_risco"] == "DOC_054 - apreciacao_risco_ph07.pdf"
    assert payload["analise_risco"]["grafico_risco_categoria"] == "Categoria 3 | S2 F2 P1"
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao_texto"] == "Sim"
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["conclusao"]["status_operacional"] == "adequacao_requerida"
    assert payload["conclusao"]["parecer_final"] == "Necessita adequacao NR12 antes do fechamento definitivo."
    assert "revalidar a maquina" in str(payload["conclusao"]["proxima_acao"])
    assert payload["case_context"]["tipo_inspecao"] == "Inicial"
    assert payload["case_context"]["local_documento"] == "Linha de estampagem - prensa PH-07"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr12_apreciacao_risco_maquina() -> None:
    laudo = SimpleNamespace(
        id=618,
        catalog_family_key="nr12_apreciacao_risco_maquina",
        catalog_family_label="NR12 · Apreciacao de risco",
        catalog_variant_label="Prime engineering",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="estamparia",
        parecer_ia="Foi identificado risco alto de aprisionamento na zona de alimentacao durante setup da prensa.",
        primeira_mensagem="Apreciacao de risco na prensa hidraulica PH-07 da linha de estampagem",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Linha de estampagem - prensa PH-07",
            "objeto_principal": "Prensa hidraulica PH-07",
            "codigo_interno": "PH-07",
            "referencia_principal": "IMG_451 - vista geral da PH-07",
            "modo_execucao": "analise e modelagem",
            "metodo_aplicado": "Apreciacao de risco com matriz HRN, checklist NR12 e memoria tecnica.",
            "perigo_identificado": "Aprisionamento na zona de alimentacao durante setup e limpeza.",
            "zona_risco": "Zona frontal de alimentacao com acesso perigoso ao ferramental.",
            "categoria_risco": "alto",
            "severidade": "grave",
            "probabilidade": "provavel",
            "medidas_existentes": "Protecoes laterais fixas e parada de emergencia frontal.",
            "medidas_recomendadas": "Intertravar acesso frontal e revisar procedimento de setup seguro.",
            "evidencia_principal": "DOC_061 - matriz_risco_ph07.pdf",
            "evidencia_complementar": "IMG_452 - zona de alimentacao frontal",
            "apreciacao_risco": "DOC_061 - matriz_risco_ph07.pdf",
            "checklist_nr12": "DOC_062 - checklist_nr12_ph07.pdf",
            "manual_maquina": "DOC_063 - manual_prensa_ph07.pdf",
            "descricao_pontos_atencao": "Risco alto de aprisionamento na zona de alimentacao durante setup.",
            "observacoes": "Implementar intertravamento frontal, revisar o procedimento e revalidar a matriz apos ajuste.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr12_apreciacao_risco_maquina",
            template_code="nr12_apreciacao_risco_maquina",
        ),
        diagnostico="Resumo executivo do caso piloto NR12 para apreciacao de risco de prensa hidraulica.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR12",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Prensa hidraulica PH-07"
    assert payload["identificacao"]["codigo_interno"] == "PH-07"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_451 - vista geral da PH-07"
    assert payload["escopo_servico"]["tipo_entrega"] == "engenharia"
    assert payload["escopo_servico"]["modo_execucao"] == "analise_e_modelagem"
    assert payload["escopo_servico"]["ativo_tipo"] == "prensa_hidraulica"
    assert "Categoria:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Probabilidade:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["analise_de_risco"][0]["perigo"] == "Aprisionamento na zona de alimentacao durante setup e limpeza."
    assert payload["analise_de_risco"][0]["cenario"] == "Zona frontal de alimentacao com acesso perigoso ao ferramental."
    assert payload["analise_de_risco"][0]["severidade"] == "grave"
    assert payload["analise_de_risco"][0]["probabilidade"] == "provavel"
    assert payload["analise_de_risco"][0]["controle"] == "Protecoes laterais fixas e parada de emergencia frontal."
    assert payload["analise_de_risco"][0]["acao_recomendada"].startswith("Intertravar acesso frontal")
    assert payload["document_projection"]["risk_primary"]["cenario"] == "Zona frontal de alimentacao com acesso perigoso ao ferramental."
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_061 - matriz_risco_ph07.pdf"
    assert "Apreciacao de risco:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert "Checklist NR12:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao_texto"] == "Sim"
    assert "intertravamento frontal" in str(payload["recomendacoes"]["texto"]).lower()
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr20_inspecao_instalacoes_inflamaveis() -> None:
    laudo = SimpleNamespace(
        id=631,
        catalog_family_key="nr20_inspecao_instalacoes_inflamaveis",
        catalog_family_label="NR20 · Inspecao de instalacoes inflamaveis",
        catalog_variant_label="Prime inflamaveis",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="petroquimica",
        parecer_ia="Foi identificado desgaste no aterramento do skid e necessidade de recompor a sinalizacao da area classificada.",
        primeira_mensagem="Inspecao NR20 no skid de abastecimento SK-02",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Parque de tancagem - skid SK-02",
            "objeto_principal": "Skid de abastecimento SK-02",
            "codigo_interno": "SK-02",
            "referencia_principal": "IMG_601 - vista geral do SK-02",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao visual com checklist NR20 e verificacao de aterramento e contencao.",
            "classificacao_area": "Zona 2 no entorno do skid de abastecimento",
            "bacia_contencao": "Bacia com necessidade de limpeza e recomposicao parcial do revestimento.",
            "aterramento": "Cabo de aterramento com desgaste no terminal principal.",
            "sinalizacao": "Placa de area classificada desgastada na lateral norte.",
            "combate_incendio": "Extintor classe B dentro da validade e hidrante proximo sinalizado.",
            "detector_gas": "Detector portatil calibrado utilizado durante a vistoria.",
            "evidencia_principal": "IMG_602 - terminal de aterramento com desgaste",
            "evidencia_complementar": "IMG_603 - sinalizacao lateral norte",
            "prontuario_nr20": "DOC_071 - prontuario_nr20_sk02.pdf",
            "plano_inspecao": "DOC_072 - plano_inspecao_sk02.pdf",
            "procedimento_operacional": "DOC_073 - procedimento_operacao_sk02.pdf",
            "art_numero": "ART 2026-00231",
            "descricao_pontos_atencao": "Desgaste no aterramento e necessidade de recompor a sinalizacao da area classificada.",
            "observacoes": "Recompor aterramento, renovar sinalizacao e reinspecionar o skid apos as correcoes.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr20_inspecao_instalacoes_inflamaveis",
            template_code="nr20_inspecao_instalacoes_inflamaveis",
        ),
        diagnostico="Resumo executivo do caso piloto NR20 para inspecao de instalacoes inflamaveis.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR20",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Skid de abastecimento SK-02"
    assert payload["identificacao"]["codigo_interno"] == "SK-02"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_601 - vista geral do SK-02"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "NR20"
    assert "Classificacao:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Aterramento:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_071 - prontuario_nr20_sk02.pdf"
    assert "Plano de inspecao:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao_texto"] == "Sim"
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr20_prontuario_instalacoes_inflamaveis() -> None:
    laudo = SimpleNamespace(
        id=632,
        catalog_family_key="nr20_prontuario_instalacoes_inflamaveis",
        catalog_family_label="NR20 · Prontuario de instalacoes inflamaveis",
        catalog_variant_label="Prime documental",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="combustiveis",
        parecer_ia="Prontuario consolidado, mas ainda depende de anexar revisao atualizada do estudo de risco.",
        primeira_mensagem="Consolidacao do prontuario NR20 da base de carregamento BC-05",
        motivo_rejeicao=None,
        dados_formulario={
            "localizacao": "Base de carregamento BC-05",
            "objeto_principal": "Base de carregamento BC-05",
            "codigo_interno": "PRT-20-BC05",
            "numero_prontuario": "PRT-20-BC05",
            "referencia_principal": "DOC_081 - indice_prontuario_bc05.pdf",
            "modo_execucao": "analise documental",
            "metodo_aplicado": "Consolidacao documental do prontuario NR20 com validacao de inventario, risco e emergencia.",
            "inventario_instalacoes": "DOC_082 - inventario_bc05.xlsx",
            "analise_riscos": "DOC_083 - estudo_risco_bc05.pdf",
            "procedimentos_operacionais": "DOC_084 - procedimentos_bc05.pdf",
            "plano_resposta_emergencia": "DOC_085 - plano_emergencia_bc05.pdf",
            "matriz_treinamentos": "DOC_086 - treinamentos_bc05.xlsx",
            "classificacao_area": "Areas classificadas revisadas parcialmente em 2024",
            "evidencia_principal": "DOC_083 - estudo_risco_bc05.pdf",
            "evidencia_complementar": "DOC_085 - plano_emergencia_bc05.pdf",
            "prontuario_nr20": "DOC_081 - indice_prontuario_bc05.pdf",
            "descricao_pontos_atencao": "Necessidade de anexar revisao atualizada do estudo de risco da base.",
            "conclusao": {"status": "Liberado com ressalvas"},
            "observacoes": "Atualizar o estudo de risco e reemitir o indice do prontuario apos a inclusao.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr20_prontuario_instalacoes_inflamaveis",
            template_code="nr20_prontuario_instalacoes_inflamaveis",
        ),
        diagnostico="Resumo executivo do caso piloto NR20 para prontuario de instalacoes inflamaveis.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR20",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Base de carregamento BC-05"
    assert payload["identificacao"]["codigo_interno"] == "PRT-20-BC05"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "DOC_081 - indice_prontuario_bc05.pdf"
    assert payload["escopo_servico"]["tipo_entrega"] == "pacote_documental"
    assert payload["escopo_servico"]["modo_execucao"] == "analise_documental"
    assert payload["escopo_servico"]["ativo_tipo"] == "NR20"
    assert "Inventario:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Analise de riscos:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_081 - indice_prontuario_bc05.pdf"
    assert "Plano de emergencia:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao_texto"] == "Sim"
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr33_avaliacao_espaco_confinado() -> None:
    laudo = SimpleNamespace(
        id=641,
        catalog_family_key="nr33_avaliacao_espaco_confinado",
        catalog_family_label="NR33 · Avaliacao de espaco confinado",
        catalog_variant_label="Prime confinados",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="quimica",
        parecer_ia="Foi identificada necessidade de reforcar a ventilacao e repetir a leitura atmosferica antes da liberacao final.",
        primeira_mensagem="Avaliacao NR33 do tanque TQ-11 na casa de bombas",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Casa de bombas - tanque TQ-11",
            "objeto_principal": "Tanque TQ-11",
            "codigo_interno": "TQ-11",
            "referencia_principal": "IMG_901 - boca de visita do TQ-11",
            "modo_execucao": "in loco",
            "metodo_aplicado": "Avaliacao de espaco confinado com leitura atmosferica e checklist NR33.",
            "classificacao_espaco": "Tanque vertical com acesso por boca de visita superior",
            "atmosfera_inicial": "O2 20,8%; LEL 0%; H2S 0 ppm",
            "ventilacao": "Ventilacao forcada prevista antes da entrada",
            "isolamento_energias": "Bloqueio eletrico e flange cego confirmados",
            "supervisor_entrada": "Carlos Lima",
            "vigia": "Patricia Souza",
            "plano_resgate": "Equipe interna com tripe e guincho dedicada ao atendimento",
            "evidencia_principal": "IMG_902 - leitura atmosferica inicial",
            "evidencia_complementar": "IMG_903 - bloqueio e isolamento",
            "documento_base": "DOC_091 - avaliacao_pre_entrada_tq11.pdf",
            "apr": "DOC_092 - apr_tq11.pdf",
            "descricao_pontos_atencao": "Necessidade de reforcar a ventilacao antes da liberacao final.",
            "conclusao": {"status": "Liberado com restricoes"},
            "observacoes": "Executar nova leitura apos ventilacao e validar a liberacao final.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr33_avaliacao_espaco_confinado",
            template_code="nr33_avaliacao_espaco_confinado",
        ),
        diagnostico="Resumo executivo do caso piloto NR33 para avaliacao de espaco confinado.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR33",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Tanque TQ-11"
    assert payload["identificacao"]["codigo_interno"] == "TQ-11"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_901 - boca de visita do TQ-11"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "NR33"
    assert "Classificacao:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Ventilacao:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_091 - avaliacao_pre_entrada_tq11.pdf"
    assert "APR:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao_texto"] == "Sim"
    assert payload["conclusao"]["status"] == "ajuste"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr33_permissao_entrada_trabalho() -> None:
    laudo = SimpleNamespace(
        id=642,
        catalog_family_key="nr33_permissao_entrada_trabalho",
        catalog_family_label="NR33 · Permissao de entrada",
        catalog_variant_label="Prime confinados",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="saneamento",
        parecer_ia="PET liberada com rastreabilidade documental e monitoramento continuo registrado.",
        primeira_mensagem="Permissao de entrada para galeria subterranea G-03",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Galeria subterranea G-03",
            "objeto_principal": "Galeria subterranea G-03",
            "codigo_interno": "PET-33-118",
            "numero_pet": "PET-33-118",
            "referencia_principal": "IMG_951 - entrada da galeria G-03",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Verificacao da PET com checklist documental e leitura atmosferica de liberacao.",
            "validade_pet": "09/04/2026 08:00-16:00",
            "supervisor_entrada": "Juliana Ferreira",
            "vigia": "Marcos Silva",
            "atmosfera_liberacao": "O2 20,9%; LEL 0%; CO 2 ppm",
            "bloqueios": "Bloqueio eletrico e travamento mecanico executados",
            "epi_epc": "Detector multigas, ventilacao exaustora e tripe",
            "equipe_autorizada": "Equipe manutencao M-3",
            "evidencia_principal": "IMG_952 - PET assinada e instrumentos",
            "evidencia_complementar": "IMG_953 - bloqueios instalados",
            "pet_documento": "DOC_101 - pet_33_118.pdf",
            "apr": "DOC_102 - apr_g03.pdf",
            "conclusao": {"status": "Liberado"},
            "observacoes": "Entrada liberada durante a vigencia da PET com monitoramento continuo.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr33_permissao_entrada_trabalho",
            template_code="nr33_permissao_entrada_trabalho",
        ),
        diagnostico="Resumo executivo do caso piloto NR33 para permissao de entrada.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR33",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Galeria subterranea G-03"
    assert payload["identificacao"]["codigo_interno"] == "PET-33-118"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_951 - entrada da galeria G-03"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "NR33"
    assert "PET:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Validade:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_101 - pet_33_118.pdf"
    assert "APR:" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is False
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao_texto"] == "Nao"
    assert payload["conclusao"]["status"] == "conforme"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_materializa_nr35_linha_de_vida_estruturada() -> None:
    laudo = SimpleNamespace(
        id=731,
        catalog_family_key="nr35_inspecao_linha_de_vida",
        catalog_family_label="NR35 · Linha de vida",
        catalog_variant_label="Prime altura",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="usina",
        parecer_ia="Linha de vida vertical com nao conformidade localizada no cabo de aco proximo ao topo.",
        primeira_mensagem="Inspecao NR35 na linha de vida vertical da escada de acesso ao elevador 01",
        motivo_rejeicao=None,
        dados_formulario={
            "informacoes_gerais": {
                "unidade": "Usina Orizona",
                "local": "Orizona - GO",
                "tipo_inspecao": "Inspecao Periodica",
                "contratante": "Caramuru Alimentos S/A",
                "contratada": "ATY Service LTDA",
                "engenheiro_responsavel": "Gabriel Santos",
                "inspetor_lider": "Marcel Renato Silva",
                "numero_laudo_fabricante": "MC-CRMR-0032",
                "numero_laudo_inspecao": "AT-IN-OZ-001-01-26",
                "art_numero": "ART 2026-00077",
                "data_vistoria": "2026-01-29",
            },
            "objeto_inspecao": {
                "identificacao_linha_vida": "MC-CRMRSS-0977 Escada de acesso ao elevador 01",
                "tipo_linha_vida": "Vertical",
                "escopo_inspecao": "Diagnostico geral da linha de vida vertical da escada de acesso.",
                "classificacao_uso": "Sistema de trabalho em altura com acesso vertical",
            },
            "componentes_inspecionados": {
                "fixacao_dos_pontos": {"condicao": "C", "observacao": "Fixacao integra."},
                "condicao_cabo_aco": {
                    "condicao": "NC",
                    "observacao": "Corrosao inicial proxima ao ponto superior.",
                },
                "condicao_esticador": {"condicao": "C", "observacao": "Tensionamento adequado."},
                "condicao_sapatilha": {"condicao": "C", "observacao": "Montagem integra."},
                "condicao_olhal": {"condicao": "C", "observacao": "Sem deformacao aparente."},
                "condicao_grampos": {"condicao": "C", "observacao": "Aperto visivel regular."},
            },
            "registros_fotograficos": [
                {
                    "titulo": "Vista geral",
                    "legenda": "Vista geral da linha de vida vertical.",
                    "referencia_anexo": "IMG_701 - vista_geral.png",
                },
                {
                    "titulo": "Ponto superior",
                    "legenda": "Corrosao inicial no cabo proximo ao topo.",
                    "referencia_anexo": "IMG_702 - ponto_superior.png",
                },
                {
                    "titulo": "Ponto inferior",
                    "legenda": "Terminal inferior registrado durante a vistoria.",
                    "referencia_anexo": "IMG_703 - ponto_inferior.png",
                },
            ],
            "metodologia_e_recursos": {
                "metodologia": "Inspecao visual e dimensional da linha de vida com checklist tecnico e rastreabilidade fotografica.",
                "instrumentos_utilizados": "Paquimetro 300 mm; Trena manual 5 m; Trena de fita 50 m; Trena digital; Dinamometro",
                "aviso_importante": "O presente laudo limita-se a analise visual e dimensional do sistema nas condicoes observadas na vistoria.",
            },
            "conclusao": {
                "status": "Reprovado",
                "proxima_inspecao_periodica": "2026-07",
                "observacoes": "Substituir o trecho comprometido do cabo e reinspecionar o sistema.",
            },
            "resumo_executivo": "Linha de vida vertical com corrosao inicial no cabo de aco e necessidade de bloqueio para correcoes.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr35_inspecao_linha_de_vida",
            template_code="nr35_inspecao_linha_de_vida",
        ),
        diagnostico="Resumo executivo do caso piloto NR35 para linha de vida vertical.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR35",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "MC-CRMRSS-0977 Escada de acesso ao elevador 01"
    assert payload["identificacao"]["codigo_interno"] == "AT-IN-OZ-001-01-26"
    assert payload["identificacao"]["documento_codigo"] == "AT-IN-OZ-001-01-26"
    assert payload["identificacao"]["tipo_ativo"] == "Vertical"
    assert payload["identificacao"]["tipo_inspecao"] == "Inspecao Periodica"
    assert payload["identificacao"]["tipo_sistema"] == "Linha de vida vertical"
    assert payload["identificacao"]["unidade_operacional"] == "Usina Orizona"
    assert payload["identificacao"]["local_documento"] == "Orizona - GO"
    assert payload["identificacao"]["contratante"] == "Caramuru Alimentos S/A"
    assert payload["identificacao"]["contratada"] == "ATY Service LTDA"
    assert payload["identificacao"]["engenheiro_responsavel"] == "Gabriel Santos"
    assert payload["identificacao"]["inspetor_lider"] == "Marcel Renato Silva"
    assert payload["identificacao"]["numero_laudo_inspecao"] == "AT-IN-OZ-001-01-26"
    assert payload["identificacao"]["numero_laudo_fabricante"] == "MC-CRMR-0032"
    assert payload["identificacao"]["art_numero"] == "ART 2026-00077"
    assert payload["identificacao"]["vinculado_art"] == "ART 2026-00077"
    assert payload["identificacao"]["data_vistoria"] == "2026-01-29"
    assert "IMG_701" in str(payload["identificacao"]["referencia_principal"]["referencias_texto"])
    assert payload["objeto_inspecao"]["descricao_escopo"] == "Diagnostico geral da linha de vida vertical da escada de acesso."
    assert payload["objeto_inspecao"]["tipo_linha_de_vida"] == "Vertical"
    assert "Cabo de aco" in str(payload["objeto_inspecao"]["resumo_componentes_avaliados"])
    assert payload["objeto_inspecao"]["classificacao_uso"] == "Sistema de trabalho em altura com acesso vertical"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "linha_de_vida_vertical"
    assert payload["metodologia_e_recursos"]["metodologia"] == "Inspecao visual e dimensional da linha de vida com checklist tecnico e rastreabilidade fotografica."
    assert "Dinamometro" in str(payload["metodologia_e_recursos"]["instrumentos_utilizados"])
    assert "analise visual e dimensional" in str(payload["metodologia_e_recursos"]["aviso_importante"])
    assert "Vista geral" in str(payload["registros_fotograficos"]["referencias_texto"])
    assert "Cabo de aco: NC" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["checklist_componentes"]["condicao_cabo_aco"]["condicao"] == "NC"
    assert payload["checklist_componentes"]["condicao_cabo_aco"]["observacao"] == "Corrosao inicial proxima ao ponto superior."
    assert payload["checklist_componentes"]["fixacao_dos_pontos"]["condicao"] == "C"
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "AT-IN-OZ-001-01-26"
    assert "ART: ART 2026-00077" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["documentacao_e_registros"]["proxima_inspecao_planejada"] == "2026-07"
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao_texto"] == "Sim"
    assert payload["conclusao"]["status"] == "Reprovado"
    assert payload["conclusao"]["status_operacional"] == "bloqueio"
    assert payload["conclusao"]["proxima_inspecao_periodica"] == "2026-07"
    assert "reinspecionar o sistema" in str(payload["conclusao"]["observacoes"])
    assert payload["case_context"]["tipo_inspecao"] == "Inspecao Periodica"
    assert payload["case_context"]["local_documento"] == "Orizona - GO"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_build_catalog_pdf_payload_mantem_analysis_basis_apenas_na_trilha_interna() -> None:
    laudo = SimpleNamespace(
        id=733,
        catalog_family_key="nr35_inspecao_linha_de_vida",
        catalog_family_label="NR35 · Linha de vida",
        catalog_variant_label="Prime altura",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="usina",
        parecer_ia="Linha de vida com ponto de corrosao localizado no trecho superior.",
        primeira_mensagem="Inspecao NR35 com fotos de linha de vida na escada de acesso.",
        motivo_rejeicao=None,
        report_pack_draft_json={
            "analysis_basis": {
                "coverage_summary": "3 foto(s), 2 mensagem(ns) de contexto, 1 documento(s) complementar(es).",
                "context_summary": "Linha de vida vertical da escada de acesso com foco em corrosao e terminais.",
                "photo_summary": "Vista geral: linha de vida vertical; Ponto superior: corrosao inicial no cabo",
                "document_summary": "Documento enviado: ART da ultima manutencao",
                "photo_evidence": [
                    {
                        "message_id": 701,
                        "reference": "msg:701",
                        "label": "Vista geral",
                        "caption": "Linha de vida vertical na escada de acesso",
                    },
                    {
                        "message_id": 702,
                        "reference": "msg:702",
                        "label": "Ponto superior",
                        "caption": "Corrosao inicial no cabo proximo ao topo",
                    },
                ],
            }
        },
        dados_formulario={
            "informacoes_gerais": {
                "unidade": "Usina Orizona",
                "local": "Orizona - GO",
                "contratante": "Caramuru Alimentos S/A",
                "contratada": "ATY Service LTDA",
                "engenheiro_responsavel": "Gabriel Santos",
                "inspetor_lider": "Marcel Renato Silva",
                "numero_laudo_fabricante": "MC-CRMR-0032",
                "numero_laudo_inspecao": "AT-IN-OZ-001-01-26",
                "art_numero": "ART 2026-00077",
                "data_vistoria": "2026-01-29",
            },
            "objeto_inspecao": {
                "identificacao_linha_vida": "MC-CRMRSS-0977 Escada de acesso ao elevador 01",
                "tipo_linha_vida": "Vertical",
                "escopo_inspecao": "Diagnostico geral da linha de vida vertical da escada de acesso.",
            },
            "componentes_inspecionados": {
                "fixacao_dos_pontos": {"condicao": "C", "observacao": "Fixacao integra."},
                "condicao_cabo_aco": {
                    "condicao": "NC",
                    "observacao": "Corrosao inicial proxima ao ponto superior.",
                },
            },
            "conclusao": {
                "status": "Reprovado",
                "proxima_inspecao_periodica": "2026-07",
                "observacoes": "Substituir o trecho comprometido do cabo e reinspecionar o sistema.",
            },
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr35_inspecao_linha_de_vida",
            template_code="nr35_inspecao_linha_de_vida",
        ),
        diagnostico="Resumo executivo do caso piloto NR35 para linha de vida vertical.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR35",
        data="09/04/2026",
    )

    assert payload["delivery_package"]["analysis_basis_available"] is True
    assert payload["delivery_package"]["analysis_basis_visibility"] == "internal_audit_only"
    assert payload["document_projection"]["analysis_basis_summary"] == (
        "3 foto(s), 2 mensagem(ns) de contexto, 1 documento(s) complementar(es)."
    )
    assert payload.get("registros_fotograficos") in (None, [])
    assert "msg:701" not in str(payload.get("registros_fotograficos") or [])
    assert "Fotos:" not in str((payload.get("execucao_servico") or {}).get("evidencia_execucao") or {})
    assert "Contexto:" not in str((payload.get("execucao_servico") or {}).get("evidencia_execucao") or {})


def test_build_catalog_pdf_payload_materializa_nr35_ponto_ancoragem() -> None:
    laudo = SimpleNamespace(
        id=732,
        catalog_family_key="nr35_inspecao_ponto_ancoragem",
        catalog_family_label="NR35 · Ponto de ancoragem",
        catalog_variant_label="Prime altura",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="logistica",
        parecer_ia="Ponto de ancoragem com corrosao superficial localizada no olhal e necessidade de ajuste preventivo.",
        primeira_mensagem="Inspecao NR35 do ponto de ancoragem ANC-12 na cobertura do bloco C",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Cobertura bloco C - ponto ANC-12",
            "objeto_principal": "Ponto de ancoragem ANC-12",
            "codigo_interno": "ANC-12",
            "referencia_principal": "IMG_801 - visao geral do ponto ANC-12",
            "modo_execucao": "in loco",
            "metodo_inspecao": "Inspecao visual com verificacao de fixacao, corrosao e deformacoes aparentes.",
            "tipo_ancoragem": "Olhal quimico em base metalica",
            "fixacao": "Fixacao com chumbador quimico e base metalica.",
            "chumbador": "Chumbador com torque conferido em campo.",
            "corrosao": "Corrosao superficial no olhal com perda localizada de pintura.",
            "deformacao": "Sem deformacao permanente aparente.",
            "trinca": "Nao foram observadas trincas na base ou no olhal.",
            "carga_nominal": "15 kN",
            "evidencia_principal": "IMG_802 - detalhe do olhal com corrosao superficial",
            "evidencia_complementar": "IMG_803 - chumbador e base metalica",
            "certificado_ancoragem": "DOC_081 - certificado_ancoragem_anc12.pdf",
            "memorial_calculo": "DOC_082 - memorial_anc12.pdf",
            "art_numero": "ART 2026-00155",
            "descricao_pontos_atencao": "Corrosao superficial no olhal e necessidade de limpeza com protecao anticorrosiva.",
            "observacoes": "Executar limpeza, protecao anticorrosiva e reinspecionar o ponto apos o tratamento.",
        },
    )

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr35_inspecao_ponto_ancoragem",
            template_code="nr35_inspecao_ponto_ancoragem",
        ),
        diagnostico="Resumo executivo do caso piloto NR35 para ponto de ancoragem.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR35",
        data="09/04/2026",
    )

    assert payload["identificacao"]["objeto_principal"] == "Ponto de ancoragem ANC-12"
    assert payload["identificacao"]["codigo_interno"] == "ANC-12"
    assert payload["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_801 - visao geral do ponto ANC-12"
    assert payload["escopo_servico"]["tipo_entrega"] == "inspecao_tecnica"
    assert payload["escopo_servico"]["modo_execucao"] == "in_loco"
    assert payload["escopo_servico"]["ativo_tipo"] == "ponto_ancoragem"
    assert "Fixacao:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert "Corrosao:" in str(payload["execucao_servico"]["parametros_relevantes"])
    assert payload["evidencias_e_anexos"]["documento_base"]["referencias_texto"] == "DOC_081 - certificado_ancoragem_anc12.pdf"
    assert "ART: ART 2026-00155" in str(payload["documentacao_e_registros"]["documentos_disponiveis"])
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao"] is True
    assert payload["nao_conformidades_ou_lacunas"]["ha_pontos_de_atencao_texto"] == "Sim"
    assert payload["conclusao"]["status"] == "Reprovado"
    assert payload["case_context"]["data_execucao"] == "2026-04-09"


def test_materialize_catalog_payload_for_laudo_usa_source_payload_contextual() -> None:
    laudo = SimpleNamespace(
        id=7,
        catalog_family_key="nr13_inspecao_vaso_pressao",
        catalog_family_label="NR13 · Vaso de Pressao",
        catalog_variant_label="Premium campo",
        status_revisao=StatusRevisao.RASCUNHO.value,
        setor_industrial="utilidades",
        parecer_ia="Sem vazamentos aparentes e com corrosao superficial localizada.",
        primeira_mensagem="Inspecao inicial em vaso vertical VP-777",
        motivo_rejeicao=None,
        criado_em=None,
        atualizado_em=None,
        encerrado_pelo_inspetor_em=None,
        dados_formulario=None,
    )

    payload = materialize_catalog_payload_for_laudo(
        laudo=laudo,
        source_payload={
            "local_inspecao": "Casa de utilidades - Linha 7",
            "nome_equipamento": "Vaso vertical VP-777",
            "tag_patrimonial": "TAG-VP-777",
            "prontuario": "DOC_777 - prontuario_vp777.pdf",
            "pontos_de_corrosao": "Corrosao superficial proxima ao apoio inferior.",
        },
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR13",
        data="09/04/2026",
    )

    assert payload is not None
    assert payload["schema_type"] == "laudo_output"
    assert payload["identificacao"]["identificacao_do_vaso"] == "Vaso vertical VP-777"
    assert payload["identificacao"]["localizacao"] == "Casa de utilidades - Linha 7"
    assert payload["documentacao_e_registros"]["prontuario"]["referencias_texto"] == "DOC_777 - prontuario_vp777.pdf"


def test_resolve_pdf_template_for_laudo_prefere_snapshot_ao_runtime(monkeypatch) -> None:
    laudo = SimpleNamespace(
        id=18,
        empresa_id=99,
        catalog_family_key="nr10_inspecao_instalacoes_eletricas",
        pdf_template_snapshot_json={
            "version": 1,
            "template_ref": {
                "source_kind": "tenant_template",
                "family_key": "nr10_inspecao_instalacoes_eletricas",
                "template_id": 77,
                "codigo_template": "nr10_snapshot_v5",
                "versao": 5,
                "modo_editor": MODO_EDITOR_RICO,
                "arquivo_pdf_base": "",
                "documento_editor_json": {"version": 1, "doc": {"type": "doc", "content": []}},
                "estilo_json": {},
                "assets_json": [],
                "mapeamento_campos_json": {
                    "pages": [
                        {
                            "page": 1,
                            "fields": [{"key": "campo_a", "x": 12, "y": 24, "w": 30, "h": 4.5}],
                        }
                    ]
                },
            },
        },
    )

    monkeypatch.setattr(
        catalog_pdf_templates,
        "_load_family_template_seed",
        lambda _family_key: (_ for _ in ()).throw(AssertionError("nao deveria consultar seed com snapshot")),
    )

    template_ref = resolve_pdf_template_for_laudo(
        banco=SimpleNamespace(),
        empresa_id=99,
        laudo=laudo,
        allow_runtime_fallback=False,
    )

    assert template_ref is not None
    assert template_ref.codigo_template == "nr10_snapshot_v5"
    assert template_ref.versao == 5
    assert template_ref.source_kind == "tenant_template"
    assert template_ref.mapeamento_campos_json["pages"][0]["fields"][0]["key"] == "campo_a"


def test_resolve_runtime_field_mapping_for_pdf_template_normaliza_overlay_legado() -> None:
    template_ref = ResolvedPdfTemplateRef(
        source_kind="tenant_template",
        family_key=None,
        template_id=77,
        codigo_template="cbmgo_cmar",
        versao=2,
        modo_editor="legado_pdf",
        arquivo_pdf_base="/tmp/cbmgo.pdf",
        documento_editor_json={},
        estilo_json={},
        assets_json=[],
        mapeamento_campos_json={
            "pages": [
                {
                    "page": "1",
                    "fields": [
                        {"key": "campo_a", "x": "10", "y": "20", "w": "40", "h": "5"},
                        {"key": "", "x": 0, "y": 0},
                    ],
                },
                {"page": 0, "fields": [{"key": "ignorar", "x": 1, "y": 1}]},
            ]
        },
    )

    mapping = resolve_runtime_field_mapping_for_pdf_template(template_ref=template_ref)

    assert len(mapping["pages"]) == 1
    assert mapping["pages"][0]["page"] == 1
    assert len(mapping["pages"][0]["fields"]) == 1
    assert mapping["pages"][0]["fields"][0]["key"] == "campo_a"
    assert mapping["pages"][0]["fields"][0]["x"] == 10.0


def test_resolve_pdf_template_for_laudo_consumo_governado_nao_consulta_template_atual(monkeypatch) -> None:
    laudo = SimpleNamespace(
        id=19,
        empresa_id=99,
        tipo_template="nr10",
        catalog_selection_token="catalog:nr10_inspecao_instalacoes_eletricas:prime_site",
        catalog_family_key="nr10_inspecao_instalacoes_eletricas",
        pdf_template_snapshot_json=None,
        catalog_snapshot_json={
            "selection_token": "catalog:nr10_inspecao_instalacoes_eletricas:prime_site",
            "family": {"key": "nr10_inspecao_instalacoes_eletricas"},
            "artifacts": {
                "template_master_seed": {
                    "template_code": "nr10_snapshot_seed",
                    "versao": 4,
                    "modo_editor": MODO_EDITOR_RICO,
                }
            },
        },
    )

    monkeypatch.setattr(
        catalog_pdf_templates,
        "_pick_active_template_by_codes",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("nao deveria consultar template atual no modo de consumo")
        ),
    )
    monkeypatch.setattr(
        catalog_pdf_templates,
        "selecionar_template_ativo_para_tipo",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("nao deveria cair no fallback runtime em caso governado")
        ),
    )

    template_ref = resolve_pdf_template_for_laudo(
        banco=SimpleNamespace(),
        empresa_id=99,
        laudo=laudo,
        allow_runtime_fallback=True,
        allow_current_binding_lookup=False,
    )

    assert template_ref is not None
    assert template_ref.codigo_template == "nr10_snapshot_seed"
    assert template_ref.versao == 4
    assert template_ref.source_kind == "catalog_canonical_seed"


def test_resolve_pdf_template_for_laudo_captura_governada_congela_template_atual(monkeypatch) -> None:
    laudo = SimpleNamespace(
        id=20,
        empresa_id=99,
        tipo_template="nr10",
        catalog_selection_token="catalog:nr10_inspecao_instalacoes_eletricas:prime_site",
        catalog_family_key="nr10_inspecao_instalacoes_eletricas",
        pdf_template_snapshot_json=None,
        catalog_snapshot_json={
            "selection_token": "catalog:nr10_inspecao_instalacoes_eletricas:prime_site",
            "family": {"key": "nr10_inspecao_instalacoes_eletricas"},
            "artifacts": {
                "template_master_seed": {
                    "template_code": "nr10_snapshot_seed",
                    "versao": 4,
                    "modo_editor": MODO_EDITOR_RICO,
                }
            },
        },
    )
    template_ativo = SimpleNamespace(
        id=321,
        codigo_template="nr10_template_tenant_v6",
        versao=6,
        modo_editor=MODO_EDITOR_RICO,
        arquivo_pdf_base="/tmp/nr10_tenant_v6.pdf",
        documento_editor_json={"version": 1, "doc": {"type": "doc", "content": []}},
        estilo_json={"page": {"size": "a4"}},
        assets_json=[{"kind": "logo", "path": "tenant/logo.png"}],
    )

    monkeypatch.setattr(
        catalog_pdf_templates,
        "_catalog_specific_template_codes",
        lambda *args, **kwargs: ["nr10_template_tenant_v6"],
    )
    monkeypatch.setattr(
        catalog_pdf_templates,
        "_pick_active_template_by_codes",
        lambda *args, **kwargs: template_ativo,
    )

    template_ref = resolve_pdf_template_for_laudo(
        banco=SimpleNamespace(),
        empresa_id=99,
        laudo=laudo,
        allow_runtime_fallback=True,
        allow_current_binding_lookup=True,
    )

    assert template_ref is not None
    assert template_ref.codigo_template == "nr10_template_tenant_v6"
    assert template_ref.versao == 6
    assert template_ref.source_kind == "tenant_template"


def test_materialize_catalog_payload_for_laudo_prefere_artifacts_do_snapshot(monkeypatch) -> None:
    laudo = SimpleNamespace(
        id=29,
        empresa_id=7,
        tipo_template="nr10",
        catalog_family_key="nr10_inspecao_instalacoes_eletricas",
        catalog_family_label="NR10 · Instalacoes eletricas",
        catalog_variant_label="Premium campo",
        status_revisao=StatusRevisao.RASCUNHO.value,
        setor_industrial="metalurgia",
        parecer_ia="Snapshot imutavel do caso.",
        primeira_mensagem="Inspecao no QGBT principal",
        motivo_rejeicao=None,
        criado_em=None,
        atualizado_em=None,
        encerrado_pelo_inspetor_em=None,
        dados_formulario={
            "resumo_executivo": "Caso congelado a partir do snapshot.",
            "local_inspecao": "QGBT principal - laminação",
            "objeto_principal": "QGBT principal",
        },
        catalog_snapshot_json={
            "family": {"key": "nr10_inspecao_instalacoes_eletricas"},
            "artifacts": {
                "family_schema": {
                    "family_key": "nr10_inspecao_instalacoes_eletricas",
                    "nome_exibicao": "NR10 · Instalacoes eletricas",
                    "macro_categoria": "NR10",
                    "descricao": "Schema congelado.",
                    "document_blueprint": {
                        "opening_statement": "Blueprint congelado para NR10.",
                    },
                    "evidence_policy": {"required_slots": [], "optional_slots": []},
                },
                "template_master_seed": {
                    "template_code": "nr10_snapshot_seed",
                    "versao": 4,
                    "modo_editor": MODO_EDITOR_RICO,
                },
                "laudo_output_seed": {
                    "schema_type": "laudo_output",
                    "schema_version": 1,
                    "family_key": "nr10_inspecao_instalacoes_eletricas",
                    "template_code": "nr10_snapshot_seed",
                    "tokens": {
                        "cliente_nome": None,
                        "unidade_nome": None,
                        "engenheiro_responsavel": None,
                        "crea_art": None,
                        "revisao_template": None,
                    },
                    "case_context": {
                        "laudo_id": None,
                        "empresa_nome": None,
                        "unidade_nome": None,
                        "data_execucao": None,
                        "data_emissao": None,
                        "status_mesa": None,
                        "modalidade_laudo": "snapshot_congelado",
                    },
                    "mesa_review": {
                        "status": None,
                        "family_lock": True,
                        "scope_mismatch": False,
                        "bloqueios": [],
                        "bloqueios_texto": None,
                        "pendencias_resolvidas_texto": None,
                        "observacoes_mesa": None,
                    },
                    "resumo_executivo": None,
                    "identificacao": {
                        "objeto_principal": None,
                        "localizacao": None,
                        "referencia_principal": {
                            "disponivel": None,
                            "referencias": [],
                            "referencias_texto": None,
                            "descricao": None,
                            "observacao": None,
                        },
                        "codigo_interno": None,
                    },
                    "escopo_servico": {
                        "tipo_entrega": "inspecao_tecnica",
                        "modo_execucao": None,
                        "ativo_tipo": None,
                        "resumo_escopo": None,
                    },
                    "execucao_servico": {
                        "metodo_aplicado": None,
                        "condicoes_observadas": None,
                        "parametros_relevantes": None,
                        "evidencia_execucao": {
                            "disponivel": None,
                            "referencias": [],
                            "referencias_texto": None,
                            "descricao": None,
                            "observacao": None,
                        },
                    },
                    "evidencias_e_anexos": {
                        "evidencia_principal": {
                            "disponivel": None,
                            "referencias": [],
                            "referencias_texto": None,
                            "descricao": None,
                            "observacao": None,
                        }
                    },
                    "documentacao_e_registros": {"pie": None},
                    "checklist_componentes": {},
                    "nao_conformidades_ou_lacunas": {
                        "ha_pontos_de_atencao": None,
                        "ha_pontos_de_atencao_texto": None,
                        "descricao": None,
                        "evidencias": {
                            "disponivel": None,
                            "referencias": [],
                            "referencias_texto": None,
                            "descricao": None,
                            "observacao": None,
                        },
                    },
                    "recomendacoes": {"texto": None},
                    "conclusao": {
                        "status": None,
                        "conclusao_tecnica": None,
                        "justificativa": None,
                    },
                },
                "laudo_output_exemplo": {},
            },
        },
        pdf_template_snapshot_json={
            "version": 1,
            "template_ref": {
                "source_kind": "catalog_canonical_seed",
                "family_key": "nr10_inspecao_instalacoes_eletricas",
                "template_id": None,
                "codigo_template": "nr10_snapshot_seed",
                "versao": 4,
                "modo_editor": MODO_EDITOR_RICO,
                "arquivo_pdf_base": "",
                "documento_editor_json": {},
                "estilo_json": {},
                "assets_json": [],
            }
        },
    )

    monkeypatch.setattr(
        catalog_pdf_templates,
        "_load_family_output_seed",
        lambda _family_key: {
            "schema_type": "laudo_output",
            "schema_version": 1,
            "family_key": "nr10_inspecao_instalacoes_eletricas",
            "template_code": "nr10_disk_changed",
            "tokens": {"cliente_nome": "Empresa Demo (DEV)"},
            "case_context": {"modalidade_laudo": "alterado_em_disco"},
        },
    )

    payload = materialize_catalog_payload_for_laudo(
        laudo=laudo,
        inspetor="Gabriel Santos",
        empresa="Metal Forte",
        data="10/04/2026",
    )

    assert payload is not None
    assert payload["template_code"] == "nr10_snapshot_seed"
    assert payload["case_context"]["modalidade_laudo"] == "snapshot_congelado"
    assert payload["document_projection"]["opening_statement"] == "Blueprint congelado para NR10."
    assert payload["tenant_branding"]["display_name"] == "Metal Forte"
