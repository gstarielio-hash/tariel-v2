# ruff: noqa: E501
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILY_SCHEMAS_DIR = REPO_ROOT / "docs" / "family_schemas"
WEB_DOCS_DIR = REPO_ROOT / "web" / "docs"
OUTPUT_DOC_PATH = WEB_DOCS_DIR / "biblioteca_templates_inspecao_profissionais.md"

INSPECTION_LIKE_FAMILIES: tuple[str, ...] = (
    "nr10_implantacao_loto",
    "nr10_inspecao_spda",
    "nr13_inspecao_vaso_pressao",
    "nr13_inspecao_caldeira",
    "nr13_inspecao_tubulacao",
    "nr13_integridade_caldeira",
    "nr13_teste_hidrostatico",
    "nr13_teste_estanqueidade_tubulacao_gas",
    "end_medicao_espessura_ultrassom",
    "end_ultrassom_junta_soldada",
    "end_liquido_penetrante",
    "end_particula_magnetica",
    "end_visual_solda",
)


@dataclass(frozen=True)
class SpecializedTemplateConfig:
    family_key: str
    objeto_label: str
    objeto_path: str
    localizacao_path: str
    referencia_path: str
    referencia_descricao_path: str
    extra_identificacao_rows: tuple[tuple[str, str], ...]
    caracterizacao_rows: tuple[tuple[str, str], ...]
    criticidade_rows: tuple[tuple[str, str], ...]
    documentacao_rows: tuple[tuple[str, str], ...]
    findings_flag_path: str
    findings_text_path: str
    recommendation_path: str
    execution_date_path: str
    checklist_rows: tuple[tuple[str, str, str], ...] = ()
    identificacao_heading: str = "Identificacao do Equipamento"
    characterization_heading: str = "Caracterizacao Operacional e Inspecao"
    checklist_heading: str = "Checklist Tecnico"
    critical_heading: str = "Dispositivos, Itens Criticos e Controles"
    documentation_heading: str = "Documentacao e Registros"
    findings_heading: str = "Nao Conformidades e Recomendacoes"


SPECIALIZED_CONFIGS: dict[str, SpecializedTemplateConfig] = {
    "nr10_implantacao_loto": SpecializedTemplateConfig(
        family_key="nr10_implantacao_loto",
        objeto_label="Ativo, frente ou sistema bloqueado",
        objeto_path="identificacao.objeto_principal",
        localizacao_path="identificacao.localizacao",
        referencia_path="identificacao.referencia_principal.referencias_texto",
        referencia_descricao_path="identificacao.referencia_principal.descricao",
        extra_identificacao_rows=(("Codigo interno", "identificacao.codigo_interno"),),
        caracterizacao_rows=(
            ("Tipo de entrega", "escopo_servico.tipo_entrega"),
            ("Modo de execucao", "escopo_servico.modo_execucao"),
            ("Ativo ou categoria principal", "escopo_servico.ativo_tipo"),
            ("Escopo consolidado", "escopo_servico.resumo_escopo"),
            ("Metodo aplicado", "execucao_servico.metodo_aplicado"),
            ("Condicoes observadas", "execucao_servico.condicoes_observadas"),
            ("Parametros relevantes", "execucao_servico.parametros_relevantes"),
        ),
        criticidade_rows=(
            ("Evidencia de execucao", "execucao_servico.evidencia_execucao.referencias_texto"),
            ("Evidencia principal", "evidencias_e_anexos.evidencia_principal.referencias_texto"),
            ("Evidencia complementar", "evidencias_e_anexos.evidencia_complementar.referencias_texto"),
            ("Documento base", "evidencias_e_anexos.documento_base.referencias_texto"),
        ),
        documentacao_rows=(
            ("Documentos disponiveis", "documentacao_e_registros.documentos_disponiveis"),
            ("Documentos emitidos", "documentacao_e_registros.documentos_emitidos"),
            ("Observacoes documentais", "documentacao_e_registros.observacoes_documentais"),
        ),
        findings_flag_path="nao_conformidades_ou_lacunas.ha_pontos_de_atencao_texto",
        findings_text_path="nao_conformidades_ou_lacunas.descricao",
        recommendation_path="recomendacoes.texto",
        execution_date_path="case_context.data_execucao",
        checklist_rows=(
            (
                "Fontes de energia",
                "checklist_componentes.fontes_de_energia.condicao",
                "checklist_componentes.fontes_de_energia.observacao",
            ),
            (
                "Pontos de bloqueio",
                "checklist_componentes.pontos_de_bloqueio.condicao",
                "checklist_componentes.pontos_de_bloqueio.observacao",
            ),
            (
                "Dispositivos e sinalizacao",
                "checklist_componentes.dispositivos_e_sinalizacao.condicao",
                "checklist_componentes.dispositivos_e_sinalizacao.observacao",
            ),
            (
                "Verificacao de energia zero",
                "checklist_componentes.verificacao_energia_zero.condicao",
                "checklist_componentes.verificacao_energia_zero.observacao",
            ),
            (
                "Sequenciamento e reenergizacao controlada",
                "checklist_componentes.sequenciamento_e_reenergizacao_controlada.condicao",
                "checklist_componentes.sequenciamento_e_reenergizacao_controlada.observacao",
            ),
        ),
        identificacao_heading="Identificacao do Ativo e Referencias de Campo",
        characterization_heading="Execucao do Bloqueio e Desenergizacao",
        checklist_heading="Checklist de Bloqueio e Condicao Segura",
        critical_heading="Evidencias do Bloqueio e Registros Criticos",
        documentation_heading="Documentacao do Procedimento e Registros",
        findings_heading="Desvios, Pendencias e Recomendacoes",
    ),
    "nr10_inspecao_spda": SpecializedTemplateConfig(
        family_key="nr10_inspecao_spda",
        objeto_label="Sistema ou estrutura inspecionada",
        objeto_path="identificacao.objeto_principal",
        localizacao_path="identificacao.localizacao",
        referencia_path="identificacao.referencia_principal.referencias_texto",
        referencia_descricao_path="identificacao.referencia_principal.descricao",
        extra_identificacao_rows=(("Codigo interno", "identificacao.codigo_interno"),),
        caracterizacao_rows=(
            ("Tipo de entrega", "escopo_servico.tipo_entrega"),
            ("Modo de execucao", "escopo_servico.modo_execucao"),
            ("Ativo ou categoria principal", "escopo_servico.ativo_tipo"),
            ("Escopo consolidado", "escopo_servico.resumo_escopo"),
            ("Metodo aplicado", "execucao_servico.metodo_aplicado"),
            ("Condicoes observadas", "execucao_servico.condicoes_observadas"),
            ("Parametros relevantes", "execucao_servico.parametros_relevantes"),
        ),
        criticidade_rows=(
            ("Evidencia de execucao", "execucao_servico.evidencia_execucao.referencias_texto"),
            ("Evidencia principal", "evidencias_e_anexos.evidencia_principal.referencias_texto"),
            ("Evidencia complementar", "evidencias_e_anexos.evidencia_complementar.referencias_texto"),
            ("Documento base", "evidencias_e_anexos.documento_base.referencias_texto"),
        ),
        documentacao_rows=(
            ("Documentos disponiveis", "documentacao_e_registros.documentos_disponiveis"),
            ("Documentos emitidos", "documentacao_e_registros.documentos_emitidos"),
            ("Observacoes documentais", "documentacao_e_registros.observacoes_documentais"),
        ),
        findings_flag_path="nao_conformidades_ou_lacunas.ha_pontos_de_atencao_texto",
        findings_text_path="nao_conformidades_ou_lacunas.descricao",
        recommendation_path="recomendacoes.texto",
        execution_date_path="case_context.data_execucao",
        checklist_rows=(
            ("Captacao", "checklist_componentes.captacao.condicao", "checklist_componentes.captacao.observacao"),
            ("Descidas", "checklist_componentes.descidas.condicao", "checklist_componentes.descidas.observacao"),
            (
                "Aterramento e equipotencializacao",
                "checklist_componentes.aterramento_e_equipotencializacao.condicao",
                "checklist_componentes.aterramento_e_equipotencializacao.observacao",
            ),
            (
                "Medicoes ou testes",
                "checklist_componentes.medicoes_ou_testes.condicao",
                "checklist_componentes.medicoes_ou_testes.observacao",
            ),
        ),
        identificacao_heading="Identificacao do Sistema e Referencias",
        characterization_heading="Execucao da Vistoria do SPDA",
        checklist_heading="Checklist do SPDA e Aterramento",
        critical_heading="Evidencias e Registros de Medicao",
        documentation_heading="Documentacao e Registros",
        findings_heading="Nao Conformidades e Acoes Recomendadas",
    ),
    "nr13_inspecao_vaso_pressao": SpecializedTemplateConfig(
        family_key="nr13_inspecao_vaso_pressao",
        objeto_label="Identificacao do vaso",
        objeto_path="identificacao.identificacao_do_vaso",
        localizacao_path="identificacao.localizacao",
        referencia_path="identificacao.placa_identificacao.referencias_texto",
        referencia_descricao_path="identificacao.placa_identificacao.descricao",
        extra_identificacao_rows=(("Tag patrimonial", "identificacao.tag_patrimonial"),),
        caracterizacao_rows=(
            ("Vista geral do equipamento", "caracterizacao_do_equipamento.vista_geral_equipamento.referencias_texto"),
            ("Descricao sumaria", "caracterizacao_do_equipamento.descricao_sumaria"),
            ("Condicao de operacao no momento", "caracterizacao_do_equipamento.condicao_de_operacao_no_momento"),
            ("Condicao geral", "inspecao_visual.condicao_geral"),
            ("Integridade aparente", "inspecao_visual.integridade_aparente"),
            ("Area de instalacao", "inspecao_visual.area_instalacao.referencias_texto"),
            ("Acessibilidade para inspecao", "inspecao_visual.acessibilidade_para_inspecao"),
            ("Pontos de corrosao", "inspecao_visual.pontos_de_corrosao.descricao"),
            ("Vazamentos", "inspecao_visual.vazamentos.descricao"),
            ("Isolamento termico", "inspecao_visual.isolamento_termico.descricao"),
        ),
        criticidade_rows=(
            ("Dispositivos de seguranca", "dispositivos_e_acessorios.dispositivos_de_seguranca.referencias_texto"),
            ("Leitura dos dispositivos de seguranca", "dispositivos_e_acessorios.leitura_dos_dispositivos_de_seguranca"),
            ("Manometro", "dispositivos_e_acessorios.manometro.descricao"),
            ("Valvula de seguranca em detalhe", "dispositivos_e_acessorios.valvula_seguranca_detalhe.descricao"),
            ("Suportes e fixacao", "dispositivos_e_acessorios.suportes_e_fixacao.descricao"),
        ),
        documentacao_rows=(
            ("Registros disponiveis no local", "documentacao_e_registros.registros_disponiveis_no_local"),
            ("Prontuario", "documentacao_e_registros.prontuario.referencias_texto"),
            ("Certificado", "documentacao_e_registros.certificado.referencias_texto"),
            ("Relatorio anterior", "documentacao_e_registros.relatorio_anterior.referencias_texto"),
        ),
        findings_flag_path="nao_conformidades.ha_nao_conformidades_texto",
        findings_text_path="nao_conformidades.descricao",
        recommendation_path="recomendacoes.texto",
        execution_date_path="case_context.data_inspecao",
    ),
    "nr13_inspecao_caldeira": SpecializedTemplateConfig(
        family_key="nr13_inspecao_caldeira",
        objeto_label="Identificacao da caldeira",
        objeto_path="identificacao.identificacao_da_caldeira",
        localizacao_path="identificacao.localizacao",
        referencia_path="identificacao.placa_identificacao.referencias_texto",
        referencia_descricao_path="identificacao.placa_identificacao.descricao",
        extra_identificacao_rows=(("Tag patrimonial", "identificacao.tag_patrimonial"),),
        caracterizacao_rows=(
            ("Vista geral da caldeira", "caracterizacao_do_equipamento.vista_geral_caldeira.referencias_texto"),
            ("Descricao sumaria", "caracterizacao_do_equipamento.descricao_sumaria"),
            ("Condicao de operacao no momento", "caracterizacao_do_equipamento.condicao_de_operacao_no_momento"),
            ("Condicao geral", "inspecao_visual.condicao_geral"),
            ("Integridade aparente", "inspecao_visual.integridade_aparente"),
            ("Area de instalacao", "inspecao_visual.area_instalacao.referencias_texto"),
            ("Acessibilidade para inspecao", "inspecao_visual.acessibilidade_para_inspecao"),
            ("Pontos de vazamento ou fuligem", "inspecao_visual.pontos_de_vazamento_ou_fuligem.descricao"),
            ("Isolamento termico", "inspecao_visual.isolamento_termico.descricao"),
            ("Chamine ou exaustao", "inspecao_visual.chamine_ou_exaustao.descricao"),
        ),
        criticidade_rows=(
            ("Dispositivos de seguranca", "dispositivos_e_controles.dispositivos_de_seguranca.referencias_texto"),
            ("Leitura dos dispositivos de seguranca", "dispositivos_e_controles.leitura_dos_dispositivos_de_seguranca"),
            ("Painel e comandos", "dispositivos_e_controles.painel_e_comandos.descricao"),
            ("Leitura dos comandos e indicadores", "dispositivos_e_controles.leitura_dos_comandos_e_indicadores"),
            ("Manometro", "dispositivos_e_controles.manometro.descricao"),
            ("Indicador de nivel", "dispositivos_e_controles.indicador_nivel.descricao"),
            ("Queimador ou sistema termico", "dispositivos_e_controles.queimador_ou_sistema_termico.descricao"),
        ),
        documentacao_rows=(
            ("Registros disponiveis no local", "documentacao_e_registros.registros_disponiveis_no_local"),
            ("Prontuario", "documentacao_e_registros.prontuario.referencias_texto"),
            ("Certificado", "documentacao_e_registros.certificado.referencias_texto"),
            ("Relatorio anterior", "documentacao_e_registros.relatorio_anterior.referencias_texto"),
        ),
        findings_flag_path="nao_conformidades.ha_nao_conformidades_texto",
        findings_text_path="nao_conformidades.descricao",
        recommendation_path="recomendacoes.texto",
        execution_date_path="case_context.data_inspecao",
    ),
    "nr13_inspecao_tubulacao": SpecializedTemplateConfig(
        family_key="nr13_inspecao_tubulacao",
        objeto_label="Trecho ou linha avaliada",
        objeto_path="identificacao.objeto_principal",
        localizacao_path="identificacao.localizacao",
        referencia_path="identificacao.referencia_principal.referencias_texto",
        referencia_descricao_path="identificacao.referencia_principal.descricao",
        extra_identificacao_rows=(("Codigo interno", "identificacao.codigo_interno"),),
        caracterizacao_rows=(
            ("Tipo de entrega", "escopo_servico.tipo_entrega"),
            ("Modo de execucao", "escopo_servico.modo_execucao"),
            ("Ativo ou categoria principal", "escopo_servico.ativo_tipo"),
            ("Escopo consolidado", "escopo_servico.resumo_escopo"),
            ("Metodo aplicado", "execucao_servico.metodo_aplicado"),
            ("Condicoes observadas", "execucao_servico.condicoes_observadas"),
            ("Parametros relevantes", "execucao_servico.parametros_relevantes"),
        ),
        criticidade_rows=(
            ("Evidencia de execucao", "execucao_servico.evidencia_execucao.referencias_texto"),
            ("Evidencia principal", "evidencias_e_anexos.evidencia_principal.referencias_texto"),
            ("Evidencia complementar", "evidencias_e_anexos.evidencia_complementar.referencias_texto"),
            ("Documento base", "evidencias_e_anexos.documento_base.referencias_texto"),
        ),
        documentacao_rows=(
            ("Documentos disponiveis", "documentacao_e_registros.documentos_disponiveis"),
            ("Documentos emitidos", "documentacao_e_registros.documentos_emitidos"),
            ("Observacoes documentais", "documentacao_e_registros.observacoes_documentais"),
        ),
        findings_flag_path="nao_conformidades_ou_lacunas.ha_pontos_de_atencao_texto",
        findings_text_path="nao_conformidades_ou_lacunas.descricao",
        recommendation_path="recomendacoes.texto",
        execution_date_path="case_context.data_execucao",
        checklist_rows=(
            (
                "Identificacao do trecho",
                "checklist_componentes.identificacao_do_trecho.condicao",
                "checklist_componentes.identificacao_do_trecho.observacao",
            ),
            (
                "Suportes e ancoragens",
                "checklist_componentes.suportes_e_ancoragens.condicao",
                "checklist_componentes.suportes_e_ancoragens.observacao",
            ),
            (
                "Valvulas e acessorios",
                "checklist_componentes.valvulas_e_acessorios.condicao",
                "checklist_componentes.valvulas_e_acessorios.observacao",
            ),
            (
                "Juntas e conexoes",
                "checklist_componentes.juntas_e_conexoes.condicao",
                "checklist_componentes.juntas_e_conexoes.observacao",
            ),
            (
                "Isolamento e protecao",
                "checklist_componentes.isolamento_e_protecao.condicao",
                "checklist_componentes.isolamento_e_protecao.observacao",
            ),
        ),
        identificacao_heading="Identificacao do Trecho e Referencias",
        characterization_heading="Escopo e Execucao Tecnica",
        checklist_heading="Checklist Tecnico do Trecho",
        critical_heading="Evidencias e Registros Criticos",
        documentation_heading="Documentacao e Registros",
        findings_heading="Nao Conformidades e Recomendacoes",
    ),
    "nr13_integridade_caldeira": SpecializedTemplateConfig(
        family_key="nr13_integridade_caldeira",
        objeto_label="Caldeira ou ativo avaliado",
        objeto_path="identificacao.objeto_principal",
        localizacao_path="identificacao.localizacao",
        referencia_path="identificacao.referencia_principal.referencias_texto",
        referencia_descricao_path="identificacao.referencia_principal.descricao",
        extra_identificacao_rows=(("Codigo interno", "identificacao.codigo_interno"),),
        caracterizacao_rows=(
            ("Tipo de entrega", "escopo_servico.tipo_entrega"),
            ("Modo de execucao", "escopo_servico.modo_execucao"),
            ("Escopo consolidado", "escopo_servico.resumo_escopo"),
            ("Metodo aplicado", "execucao_servico.metodo_aplicado"),
            ("Condicoes observadas", "execucao_servico.condicoes_observadas"),
            ("Parametros relevantes", "execucao_servico.parametros_relevantes"),
        ),
        criticidade_rows=(
            ("Evidencia de execucao", "execucao_servico.evidencia_execucao.referencias_texto"),
            ("Evidencia principal", "evidencias_e_anexos.evidencia_principal.referencias_texto"),
            ("Evidencia complementar", "evidencias_e_anexos.evidencia_complementar.referencias_texto"),
            ("Documento base", "evidencias_e_anexos.documento_base.referencias_texto"),
        ),
        documentacao_rows=(
            ("Documentos disponiveis", "documentacao_e_registros.documentos_disponiveis"),
            ("Documentos emitidos", "documentacao_e_registros.documentos_emitidos"),
            ("Observacoes documentais", "documentacao_e_registros.observacoes_documentais"),
        ),
        findings_flag_path="nao_conformidades_ou_lacunas.ha_pontos_de_atencao_texto",
        findings_text_path="nao_conformidades_ou_lacunas.descricao",
        recommendation_path="recomendacoes.texto",
        execution_date_path="case_context.data_execucao",
        identificacao_heading="Identificacao da Caldeira e Referencias",
        characterization_heading="Escopo e Analise de Integridade",
        critical_heading="Evidencias, Historico e Registros Criticos",
        documentation_heading="Documentacao e Registros",
        findings_heading="Lacunas Tecnicas e Recomendacoes",
    ),
    "nr13_teste_hidrostatico": SpecializedTemplateConfig(
        family_key="nr13_teste_hidrostatico",
        objeto_label="Ativo submetido ao teste",
        objeto_path="identificacao.objeto_principal",
        localizacao_path="identificacao.localizacao",
        referencia_path="identificacao.referencia_principal.referencias_texto",
        referencia_descricao_path="identificacao.referencia_principal.descricao",
        extra_identificacao_rows=(("Codigo interno", "identificacao.codigo_interno"),),
        caracterizacao_rows=(
            ("Tipo de entrega", "escopo_servico.tipo_entrega"),
            ("Modo de execucao", "escopo_servico.modo_execucao"),
            ("Escopo consolidado", "escopo_servico.resumo_escopo"),
            ("Metodo aplicado", "execucao_servico.metodo_aplicado"),
            ("Condicoes observadas", "execucao_servico.condicoes_observadas"),
            ("Parametros relevantes", "execucao_servico.parametros_relevantes"),
        ),
        criticidade_rows=(
            ("Evidencia de execucao", "execucao_servico.evidencia_execucao.referencias_texto"),
            ("Evidencia principal", "evidencias_e_anexos.evidencia_principal.referencias_texto"),
            ("Evidencia complementar", "evidencias_e_anexos.evidencia_complementar.referencias_texto"),
            ("Documento base", "evidencias_e_anexos.documento_base.referencias_texto"),
        ),
        documentacao_rows=(
            ("Documentos disponiveis", "documentacao_e_registros.documentos_disponiveis"),
            ("Documentos emitidos", "documentacao_e_registros.documentos_emitidos"),
            ("Observacoes documentais", "documentacao_e_registros.observacoes_documentais"),
        ),
        findings_flag_path="nao_conformidades_ou_lacunas.ha_pontos_de_atencao_texto",
        findings_text_path="nao_conformidades_ou_lacunas.descricao",
        recommendation_path="recomendacoes.texto",
        execution_date_path="case_context.data_execucao",
        identificacao_heading="Identificacao do Ativo e Referencias de Teste",
        characterization_heading="Escopo e Procedimento do Teste",
        critical_heading="Evidencias, Parametros e Registros Criticos",
        documentation_heading="Documentacao e Registros",
        findings_heading="Desvios e Recomendacoes",
    ),
    "nr13_teste_estanqueidade_tubulacao_gas": SpecializedTemplateConfig(
        family_key="nr13_teste_estanqueidade_tubulacao_gas",
        objeto_label="Trecho ou linha submetida ao teste",
        objeto_path="identificacao.objeto_principal",
        localizacao_path="identificacao.localizacao",
        referencia_path="identificacao.referencia_principal.referencias_texto",
        referencia_descricao_path="identificacao.referencia_principal.descricao",
        extra_identificacao_rows=(("Codigo interno", "identificacao.codigo_interno"),),
        caracterizacao_rows=(
            ("Tipo de entrega", "escopo_servico.tipo_entrega"),
            ("Modo de execucao", "escopo_servico.modo_execucao"),
            ("Escopo consolidado", "escopo_servico.resumo_escopo"),
            ("Metodo aplicado", "execucao_servico.metodo_aplicado"),
            ("Condicoes observadas", "execucao_servico.condicoes_observadas"),
            ("Parametros relevantes", "execucao_servico.parametros_relevantes"),
        ),
        criticidade_rows=(
            ("Evidencia de execucao", "execucao_servico.evidencia_execucao.referencias_texto"),
            ("Evidencia principal", "evidencias_e_anexos.evidencia_principal.referencias_texto"),
            ("Evidencia complementar", "evidencias_e_anexos.evidencia_complementar.referencias_texto"),
            ("Documento base", "evidencias_e_anexos.documento_base.referencias_texto"),
        ),
        documentacao_rows=(
            ("Documentos disponiveis", "documentacao_e_registros.documentos_disponiveis"),
            ("Documentos emitidos", "documentacao_e_registros.documentos_emitidos"),
            ("Observacoes documentais", "documentacao_e_registros.observacoes_documentais"),
        ),
        findings_flag_path="nao_conformidades_ou_lacunas.ha_pontos_de_atencao_texto",
        findings_text_path="nao_conformidades_ou_lacunas.descricao",
        recommendation_path="recomendacoes.texto",
        execution_date_path="case_context.data_execucao",
        identificacao_heading="Identificacao do Trecho e Referencias de Teste",
        characterization_heading="Escopo e Procedimento do Teste",
        critical_heading="Evidencias, Parametros e Registros Criticos",
        documentation_heading="Documentacao e Registros",
        findings_heading="Desvios e Recomendacoes",
    ),
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _text(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def _placeholder(mode: str, key: str) -> dict[str, Any]:
    return {
        "type": "placeholder",
        "attrs": {
            "mode": mode,
            "key": key,
            "raw": f"{mode}:{key}",
        },
    }


def _paragraph(parts: list[dict[str, Any]], class_name: str = "") -> dict[str, Any]:
    payload: dict[str, Any] = {"type": "paragraph", "content": parts}
    if class_name:
        payload["attrs"] = {"className": class_name}
    return payload


def _heading(level: int, text: str) -> dict[str, Any]:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [_text(text)],
    }


def _list_item(parts: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "listItem", "content": [_paragraph(parts)]}


def _bullet_list(items: list[list[dict[str, Any]]]) -> dict[str, Any]:
    return {"type": "bulletList", "content": [_list_item(item) for item in items]}


def _table_cell(parts: list[dict[str, Any]], *, header: bool = False) -> dict[str, Any]:
    return {
        "type": "tableHeader" if header else "tableCell",
        "content": [_paragraph(parts)],
    }


def _table(headers: tuple[str, ...], rows: list[tuple[list[dict[str, Any]], ...]]) -> dict[str, Any]:
    return {
        "type": "table",
        "attrs": {"className": "doc-compact"},
        "content": [
            {
                "type": "tableRow",
                "content": [_table_cell([_text(header)], header=True) for header in headers],
            },
            *[
                {
                    "type": "tableRow",
                    "content": [_table_cell(cell) for cell in row],
                }
                for row in rows
            ],
        ],
    }


def _value_path(path: str) -> list[dict[str, Any]]:
    return [_placeholder("json_path", path)]


def _value_ref_desc(ref_path: str, desc_path: str) -> list[dict[str, Any]]:
    return [
        _placeholder("json_path", ref_path),
        _text(" | "),
        _placeholder("json_path", desc_path),
    ]


def _build_style(title: str) -> dict[str, Any]:
    return {
        "pagina": {
            "size": "A4",
            "orientation": "portrait",
            "margens_mm": {"top": 18, "right": 14, "bottom": 18, "left": 14},
        },
        "tipografia": {
            "font_family": "Georgia, 'Times New Roman', serif",
            "font_size_px": 11,
            "line_height": 1.5,
        },
        "tema": {
            "primaria": "#17324d",
            "secundaria": "#55697a",
            "acento": "#b6813a",
            "suave": "#eef3f7",
            "borda": "#c5d2dc",
        },
        "cabecalho_texto": f"{{{{token:cliente_nome}}}} | {title} | {{{{token:cliente_cnpj}}}}",
        "rodape_texto": "{{token:documento_codigo}} | {{token:documento_revisao}} | {{token:status_assinatura}} | {{token:confidencialidade_documento}}",
        "marca_dagua": {"texto": "", "opacity": 0.08, "font_size_px": 72, "rotate_deg": -32},
    }


def _macro_categoria_from_family_key(family_key: str) -> str:
    key = str(family_key or "").strip().lower()
    if key.startswith("end_"):
        return "END"
    match = re.match(r"^(nr\d{2})_", key)
    if match:
        return match.group(1).upper()
    return "NR"


def _generic_context(family_key: str) -> dict[str, str]:
    macro = _macro_categoria_from_family_key(family_key)
    key = str(family_key or "").strip().lower()
    if family_key.startswith("end_"):
        return {
            "kicker": "Tariel.ia | Biblioteca Tecnica END",
            "objeto_titulo": "Identificacao do Ensaio e do Objeto",
            "execucao_titulo": "Execucao do Ensaio",
            "findings_titulo": "Indicacoes Tecnicas e Pontos de Atencao",
            "lead": "Template profissional para consolidacao de ensaio nao destrutivo, rastreabilidade das evidencias e fechamento tecnico auditavel pela Mesa.",
        }
    if "teste" in key:
        return {
            "kicker": f"Tariel.ia | Biblioteca Tecnica de Testes {macro}",
            "objeto_titulo": "Identificacao do Objeto de Teste",
            "execucao_titulo": "Execucao do Teste",
            "findings_titulo": "Desvios e Pontos de Atencao",
            "lead": "Template profissional para consolidacao de teste tecnico com parametros, evidencias principais, registros e conclusao formal.",
        }
    if any(token in key for token in ("prontuario", "programa", "plano", "ordem_servico", "analise_ergonomica", "gestao_", "laudo_")):
        return {
            "kicker": f"Tariel.ia | Biblioteca Tecnica Documental {macro}",
            "objeto_titulo": "Identificacao do Objeto e da Base Documental",
            "execucao_titulo": "Consolidacao Tecnica e Documental",
            "findings_titulo": "Lacunas Documentais e Pontos de Atencao",
            "lead": "Template profissional para consolidacao documental, rastreabilidade de base tecnica e fechamento auditavel pela Mesa.",
        }
    if any(token in key for token in ("apreciacao_", "projeto_", "adequacao_", "par_")):
        return {
            "kicker": f"Tariel.ia | Biblioteca Tecnica de Engenharia {macro}",
            "objeto_titulo": "Identificacao do Objeto e Premissas de Engenharia",
            "execucao_titulo": "Analise Tecnica e Desenvolvimento",
            "findings_titulo": "Lacunas Tecnicas e Interfaces Criticas",
            "lead": "Template profissional para consolidacao de analise de engenharia, memoria de decisao e conclusao rastreavel para liberacao controlada.",
        }
    return {
        "kicker": f"Tariel.ia | Biblioteca Tecnica de Inspecao {macro}",
        "objeto_titulo": "Identificacao do Objeto Inspecionado",
        "execucao_titulo": "Execucao Tecnica",
        "findings_titulo": "Achados Tecnicos e Providencias",
        "lead": "Template profissional para consolidacao de inspecao tecnica com quadro de controle, escopo, evidencias e fechamento estruturado para emissao.",
    }


def _build_generic_template_seed(
    *,
    family_key: str,
    nome_exibicao: str,
    descricao: str,
    template_code: str,
) -> dict[str, Any]:
    ctx = _generic_context(family_key)
    title = nome_exibicao.strip() or family_key
    doc_content = [
        _paragraph([_text(ctx["kicker"])], class_name="doc-kicker"),
        _heading(1, title),
        _paragraph([_text(descricao.strip() or ctx["lead"])], class_name="doc-lead"),
        _heading(2, "1. Quadro de Controle do Documento"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Cliente")], [_placeholder("token", "cliente_nome")]),
                ([_text("Unidade")], [_placeholder("token", "unidade_nome")]),
                ([_text("ID do laudo")], [_placeholder("json_path", "case_context.laudo_id")]),
                ([_text("Data da execucao")], [_placeholder("json_path", "case_context.data_execucao")]),
                ([_text("Data da emissao")], [_placeholder("json_path", "case_context.data_emissao")]),
                ([_text("Status Mesa")], [_placeholder("json_path", "mesa_review.status")]),
                ([_text("Family key")], [_placeholder("json_path", "family_key")]),
            ],
        ),
        _heading(2, "2. Resumo Executivo"),
        _paragraph([_placeholder("json_path", "resumo_executivo")]),
        _heading(2, "3. Escopo Tecnico e Premissas"),
        _bullet_list(
            [
                [_text("Tipo de entrega: "), _placeholder("json_path", "escopo_servico.tipo_entrega")],
                [_text("Modo de execucao: "), _placeholder("json_path", "escopo_servico.modo_execucao")],
                [_text("Ativo ou categoria principal: "), _placeholder("json_path", "escopo_servico.ativo_tipo")],
                [_text("Escopo registrado: "), _placeholder("json_path", "escopo_servico.resumo_escopo")],
            ]
        ),
        _paragraph(
            [_text("A emissao formal deste documento depende de rastreabilidade suficiente, coerencia de escopo e governanca valida pela Mesa.")],
            class_name="doc-note",
        ),
        _heading(2, f"4. {ctx['objeto_titulo']}"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Objeto principal")], _value_path("identificacao.objeto_principal")),
                ([_text("Localizacao")], _value_path("identificacao.localizacao")),
                ([_text("Codigo interno")], _value_path("identificacao.codigo_interno")),
                (
                    [_text("Referencia principal")],
                    _value_ref_desc("identificacao.referencia_principal.referencias_texto", "identificacao.referencia_principal.descricao"),
                ),
            ],
        ),
        _heading(2, f"5. {ctx['execucao_titulo']}"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Metodo aplicado")], _value_path("execucao_servico.metodo_aplicado")),
                ([_text("Condicoes observadas")], _value_path("execucao_servico.condicoes_observadas")),
                ([_text("Parametros relevantes")], _value_path("execucao_servico.parametros_relevantes")),
                (
                    [_text("Evidencia de execucao")],
                    _value_ref_desc("execucao_servico.evidencia_execucao.referencias_texto", "execucao_servico.evidencia_execucao.descricao"),
                ),
            ],
        ),
        _heading(2, "6. Matriz de Evidencias"),
        _table(
            ("Item", "Consolidacao"),
            [
                (
                    [_text("Evidencia principal")],
                    _value_ref_desc("evidencias_e_anexos.evidencia_principal.referencias_texto", "evidencias_e_anexos.evidencia_principal.descricao"),
                ),
                (
                    [_text("Evidencia complementar")],
                    _value_ref_desc("evidencias_e_anexos.evidencia_complementar.referencias_texto", "evidencias_e_anexos.evidencia_complementar.descricao"),
                ),
                (
                    [_text("Documento base")],
                    _value_ref_desc("evidencias_e_anexos.documento_base.referencias_texto", "evidencias_e_anexos.documento_base.descricao"),
                ),
            ],
        ),
        _heading(2, "7. Documentacao e Registros"),
        _table(
            ("Item", "Consolidacao"),
            [
                ([_text("Documentos disponiveis")], _value_path("documentacao_e_registros.documentos_disponiveis")),
                ([_text("Documentos emitidos")], _value_path("documentacao_e_registros.documentos_emitidos")),
                ([_text("Observacoes documentais")], _value_path("documentacao_e_registros.observacoes_documentais")),
            ],
        ),
        _heading(2, f"8. {ctx['findings_titulo']}"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Ha pontos de atencao")], _value_path("nao_conformidades_ou_lacunas.ha_pontos_de_atencao_texto")),
                ([_text("Descricao")], _value_path("nao_conformidades_ou_lacunas.descricao")),
                (
                    [_text("Evidencias relacionadas")],
                    _value_ref_desc("nao_conformidades_ou_lacunas.evidencias.referencias_texto", "nao_conformidades_ou_lacunas.evidencias.descricao"),
                ),
            ],
        ),
        _heading(2, "9. Recomendacoes"),
        _paragraph([_placeholder("json_path", "recomendacoes.texto")]),
        _heading(2, "10. Conclusao Tecnica"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Status")], _value_path("conclusao.status")),
                ([_text("Conclusao tecnica")], _value_path("conclusao.conclusao_tecnica")),
                ([_text("Justificativa")], _value_path("conclusao.justificativa")),
            ],
        ),
        _heading(2, "11. Governanca da Mesa"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Status da Mesa")], _value_path("mesa_review.status")),
                ([_text("Family lock")], _value_path("mesa_review.family_lock")),
                ([_text("Scope mismatch")], _value_path("mesa_review.scope_mismatch")),
                ([_text("Bloqueios")], _value_path("mesa_review.bloqueios_texto")),
                ([_text("Pendencias resolvidas")], _value_path("mesa_review.pendencias_resolvidas_texto")),
                ([_text("Observacoes da Mesa")], _value_path("mesa_review.observacoes_mesa")),
            ],
        ),
        _heading(2, "12. Assinatura e Responsabilidade"),
        _table(
            ("Campo", "Valor"),
            [
                ([_text("Engenheiro responsavel")], [_placeholder("token", "engenheiro_responsavel")]),
                ([_text("CREA / ART")], [_placeholder("token", "crea_art")]),
                ([_text("Data de emissao")], [_placeholder("json_path", "case_context.data_emissao")]),
            ],
        ),
        _paragraph([_text("Documento emitido a partir do template canonicamente governado pela Tariel e validado pela Mesa.")], class_name="doc-small"),
    ]
    return {
        "family_key": family_key,
        "template_code": template_code,
        "nome_template": f"{title} - Template Profissional",
        "modo_editor": "editor_rico",
        "observacoes": "Template profissional de inspecao ou ensaio, com quadro de controle, matriz de evidencias, governanca da Mesa e fechamento tecnico estruturado.",
        "estilo_json": _build_style(title),
        "documento_editor_json": {
            "version": 1,
            "doc": {"type": "doc", "content": doc_content},
        },
    }


def _build_specialized_template_seed(
    *,
    config: SpecializedTemplateConfig,
    nome_exibicao: str,
    descricao: str,
    template_code: str,
) -> dict[str, Any]:
    title = nome_exibicao.strip() or config.family_key
    identificacao_rows: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = [
        ([_text(config.objeto_label)], _value_path(config.objeto_path)),
        ([_text("Localizacao")], _value_path(config.localizacao_path)),
        ([_text("Referencia principal")], _value_ref_desc(config.referencia_path, config.referencia_descricao_path)),
    ]
    for label, path in config.extra_identificacao_rows:
        identificacao_rows.append(([_text(label)], _value_path(path)))

    caracterizacao_rows = [([_text(label)], _value_path(path)) for label, path in config.caracterizacao_rows]
    criticidade_rows = [([_text(label)], _value_path(path)) for label, path in config.criticidade_rows]
    documentacao_rows = [([_text(label)], _value_path(path)) for label, path in config.documentacao_rows]
    checklist_rows = [
        ([_text(label)], _value_path(condicao_path), _value_path(observacao_path))
        for label, condicao_path, observacao_path in config.checklist_rows
    ]

    doc_content = [
        _paragraph([_text("Tariel.ia | Biblioteca Tecnica de Inspecao NR13")], class_name="doc-kicker"),
        _heading(1, title),
        _paragraph(
            [
                _text(
                    descricao.strip()
                    or "Template profissional para consolidacao de inspecao tecnica NR13 com foco em rastreabilidade, evidencia vinculada e fechamento auditavel pela Mesa."
                )
            ],
            class_name="doc-lead",
        ),
    ]
    section_number = 1

    doc_content.extend(
        [
            _heading(2, f"{section_number}. Quadro de Controle do Documento"),
            _table(
                ("Campo", "Valor"),
                [
                    ([_text("Cliente")], [_placeholder("token", "cliente_nome")]),
                    ([_text("Unidade")], [_placeholder("token", "unidade_nome")]),
                    ([_text("ID do laudo")], [_placeholder("json_path", "case_context.laudo_id")]),
                    ([_text("Data da inspecao")], [_placeholder("json_path", config.execution_date_path)]),
                    ([_text("Data da emissao")], [_placeholder("json_path", "case_context.data_emissao")]),
                    ([_text("Status Mesa")], [_placeholder("json_path", "mesa_review.status")]),
                    ([_text("Family key")], [_placeholder("json_path", "family_key")]),
                ],
            ),
        ]
    )
    section_number += 1
    doc_content.extend(
        [
            _heading(2, f"{section_number}. Resumo Executivo"),
            _paragraph([_placeholder("json_path", "resumo_executivo")]),
        ]
    )
    section_number += 1
    doc_content.extend(
        [
            _heading(2, f"{section_number}. Escopo Tecnico e Premissas"),
            _bullet_list(
                [
                    [_text("Escopo principal: "), _placeholder("json_path", "conclusao.justificativa")],
                    [_text("Conclusao condicionada a evidencia vinculada, family lock e governanca valida pela Mesa.")],
                    [_text("Documento preparado para uso comercial, revisao tecnica e emissao controlada.")],
                ]
            ),
            _paragraph(
                [_text("Este template foi estruturado para emissao profissional, leitura humana e rastreabilidade de campo sem depender de dump cru de JSON.")],
                class_name="doc-note",
            ),
        ]
    )
    section_number += 1
    doc_content.extend(
        [
            _heading(2, f"{section_number}. {config.identificacao_heading}"),
            _table(("Campo", "Valor"), identificacao_rows),
        ]
    )
    section_number += 1
    doc_content.extend(
        [
            _heading(2, f"{section_number}. {config.characterization_heading}"),
            _table(("Campo", "Valor"), caracterizacao_rows),
        ]
    )
    section_number += 1
    if checklist_rows:
        doc_content.extend(
            [
                _heading(2, f"{section_number}. {config.checklist_heading}"),
                _table(("Item", "Condicao", "Observacao"), checklist_rows),
            ]
        )
        section_number += 1

    doc_content.extend(
        [
            _heading(2, f"{section_number}. {config.critical_heading}"),
            _table(("Campo", "Valor"), criticidade_rows),
        ]
    )
    section_number += 1
    doc_content.extend(
        [
            _heading(2, f"{section_number}. {config.documentation_heading}"),
            _table(("Item", "Consolidacao"), documentacao_rows),
        ]
    )
    section_number += 1
    doc_content.extend(
        [
            _heading(2, f"{section_number}. {config.findings_heading}"),
            _table(
                ("Campo", "Valor"),
                [
                    ([_text("Ha nao conformidades")], _value_path(config.findings_flag_path)),
                    ([_text("Descricao")], _value_path(config.findings_text_path)),
                    ([_text("Recomendacoes")], _value_path(config.recommendation_path)),
                ],
            ),
        ]
    )
    section_number += 1
    doc_content.extend(
        [
            _heading(2, f"{section_number}. Conclusao Tecnica"),
            _table(
                ("Campo", "Valor"),
                [
                    ([_text("Status")], _value_path("conclusao.status")),
                    ([_text("Conclusao tecnica")], _value_path("conclusao.conclusao_tecnica")),
                    ([_text("Justificativa")], _value_path("conclusao.justificativa")),
                ],
            ),
        ]
    )
    section_number += 1
    doc_content.extend(
        [
            _heading(2, f"{section_number}. Governanca da Mesa"),
            _table(
                ("Campo", "Valor"),
                [
                    ([_text("Status da Mesa")], _value_path("mesa_review.status")),
                    ([_text("Family lock")], _value_path("mesa_review.family_lock")),
                    ([_text("Scope mismatch")], _value_path("mesa_review.scope_mismatch")),
                    ([_text("Bloqueios")], _value_path("mesa_review.bloqueios_texto")),
                    ([_text("Pendencias resolvidas")], _value_path("mesa_review.pendencias_resolvidas_texto")),
                    ([_text("Observacoes da Mesa")], _value_path("mesa_review.observacoes_mesa")),
                ],
            ),
        ]
    )
    section_number += 1
    doc_content.extend(
        [
            _heading(2, f"{section_number}. Assinatura e Responsabilidade"),
            _table(
                ("Campo", "Valor"),
                [
                    ([_text("Engenheiro responsavel")], [_placeholder("token", "engenheiro_responsavel")]),
                    ([_text("CREA / ART")], [_placeholder("token", "crea_art")]),
                    ([_text("Data de emissao")], [_placeholder("json_path", "case_context.data_emissao")]),
                ],
            ),
            _paragraph([_text("Documento emitido a partir do template canonicamente governado pela Tariel e validado pela Mesa.")], class_name="doc-small"),
        ]
    )
    return {
        "family_key": config.family_key,
        "template_code": template_code,
        "nome_template": f"{title} - Template Profissional",
        "modo_editor": "editor_rico",
        "observacoes": "Template profissional NR13 com quadro de controle do documento, leitura humana, governanca da Mesa e fechamento tecnico estruturado.",
        "estilo_json": _build_style(title),
        "documento_editor_json": {
            "version": 1,
            "doc": {"type": "doc", "content": doc_content},
        },
    }


def _build_inventory_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Biblioteca de Templates Profissionais de Inspecao",
        "",
        "Resumo da biblioteca profissionalizada para inspecoes, testes e tecnicas END da linha atual do projeto.",
        "",
        "## Cobertura atual",
        "",
        "- macro categorias presentes no projeto: `NR10`, `NR13` e `END`;",
        "- templates profissionais desta biblioteca: `13`;",
        "- isso cobre a carteira tecnica principal de inspecao da empresa, mas nao cobre ainda o universo inteiro das NRs brasileiras;",
        "- continuam fora do projeto, por exemplo, frentes como `NR12`, `NR20`, `NR33`, `NR35` e outras familias nao modeladas.",
        "",
        "## Templates profissionais",
        "",
        "| Family key | Template code | Nome exibicao | Tipo |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| `{row['family_key']}` | `{row['template_code']}` | {row['nome_exibicao']} | `{row['tipo']}` |")
    lines.extend(
        [
            "",
            "## Padrao adotado",
            "",
            "- quadro de controle do documento;",
            "- resumo executivo e escopo tecnico;",
            "- matriz de evidencias e documentacao;",
            "- conclusao tecnica e governanca da Mesa;",
            "- bloco final de assinatura e responsabilidade.",
            "",
            "## Operacao",
            "",
            "1. manter a familia tecnica como fonte de verdade;",
            "2. usar o template profissional como base comercial e operacional;",
            "3. evoluir variantes por modalidade quando o portfolio pedir versoes separadas como inicial, periodica e extraordinaria.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    WEB_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    inventory_rows: list[dict[str, str]] = []

    for family_key in INSPECTION_LIKE_FAMILIES:
        schema = _load_json(FAMILY_SCHEMAS_DIR / f"{family_key}.json")
        current_seed = _load_json(FAMILY_SCHEMAS_DIR / f"{family_key}.template_master_seed.json")
        nome_exibicao = str(schema.get("nome_exibicao") or family_key).strip()
        descricao = str(schema.get("descricao") or "").strip()
        template_code = str(current_seed.get("template_code") or schema.get("family_key") or family_key).strip()

        config = SPECIALIZED_CONFIGS.get(family_key)
        if config:
            payload = _build_specialized_template_seed(
                config=config,
                nome_exibicao=nome_exibicao,
                descricao=descricao,
                template_code=template_code,
            )
            tipo = "inspection"
        else:
            payload = _build_generic_template_seed(
                family_key=family_key,
                nome_exibicao=nome_exibicao,
                descricao=descricao,
                template_code=template_code,
            )
            if family_key.startswith("end_"):
                tipo = "ndt"
            elif family_key.startswith("nr13_teste_"):
                tipo = "test"
            else:
                tipo = "inspection"

        _dump_json(FAMILY_SCHEMAS_DIR / f"{family_key}.template_master_seed.json", payload)
        inventory_rows.append(
            {
                "family_key": family_key,
                "template_code": template_code,
                "nome_exibicao": nome_exibicao,
                "tipo": tipo,
            }
        )

    OUTPUT_DOC_PATH.write_text(_build_inventory_markdown(inventory_rows), encoding="utf-8")
    print(
        json.dumps(
            {
                "templates_profissionalizados": len(inventory_rows),
                "doc_saida": str(OUTPUT_DOC_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
