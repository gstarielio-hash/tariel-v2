"""Helpers de gate de qualidade do laudo para o domínio Chat/Inspetor."""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.paths import resolve_family_schemas_dir
from app.domains.chat.media_helpers import mensagem_representa_documento
from app.domains.chat.normalization import nome_template_humano, normalizar_tipo_template
from app.domains.chat.report_pack_helpers import atualizar_report_pack_draft_laudo
from app.shared.database import AprendizadoVisualIa, Laudo, MensagemLaudo, TipoMensagem
from app.v2.report_pack_rollout_metrics import record_report_pack_gate_observation

REGRAS_GATE_QUALIDADE_TEMPLATE: dict[str, dict[str, Any]] = {
    "padrao": {
        "min_textos": 1,
        "min_evidencias": 2,
        "min_fotos": 1,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "avcb": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "spda": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "pie": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "rti": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "loto": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "nr11_movimentacao": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "nr12maquinas": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "nr13": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "nr13_calibracao": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "nr13_teste_hidrostatico": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "nr13_ultrassom": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "nr20_instalacoes": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "nr33_espaco_confinado": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "nr35_linha_vida": {
        "min_textos": 2,
        "min_evidencias": 4,
        "min_fotos": 3,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": True,
    },
    "nr35_montagem": {
        "min_textos": 2,
        "min_evidencias": 4,
        "min_fotos": 3,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "nr35_ponto_ancoragem": {
        "min_textos": 2,
        "min_evidencias": 4,
        "min_fotos": 3,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "nr35_projeto": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": False,
    },
    "cbmgo": {
        "min_textos": 2,
        "min_evidencias": 3,
        "min_fotos": 2,
        "min_mensagens_ia": 1,
        "requer_dados_formulario": True,
    },
}

ROTEIRO_COLETA_TEMPLATE: dict[str, dict[str, Any]] = {
    "padrao": {
        "descricao": "Feche a coleta com contexto inicial claro, evidências mínimas e um parecer preliminar antes do envio.",
        "itens_especificos": [
            {
                "id": "padrao_ativo_risco",
                "categoria": "coleta",
                "titulo": "Delimitar ativo, área e risco principal",
                "descricao": "Registre no chat qual equipamento, setor ou processo está sendo inspecionado e qual risco motivou a coleta.",
            },
            {
                "id": "padrao_achado_principal",
                "categoria": "coleta",
                "titulo": "Consolidar o achado principal da inspeção",
                "descricao": "Antes de enviar para a mesa, deixe explícito o principal achado técnico ou a ausência de não conformidade relevante.",
            },
        ],
    },
    "avcb": {
        "descricao": "Priorize evidências de abandono seguro, sinalização e meios de combate a incêndio compatíveis com a planta.",
        "itens_especificos": [
            {
                "id": "avcb_rotas_sinalizacao",
                "categoria": "norma",
                "titulo": "Cobrir rotas de fuga e sinalização",
                "descricao": "Inclua registros de circulação, saídas, sinalização e condições gerais para abandono da edificação.",
            },
            {
                "id": "avcb_combate_incendio",
                "categoria": "norma",
                "titulo": "Registrar meios de combate e proteção",
                "descricao": "Priorize extintores, hidrantes, alarme, iluminação ou outros sistemas de combate existentes.",
            },
        ],
    },
    "nr35_linha_vida": {
        "descricao": "Feche a vistoria com identificação do ativo, avaliação dos componentes da linha de vida, fotos legendadas e conclusão formal.",
        "itens_especificos": [
            {
                "id": "nr35_linha_vida_identificacao",
                "categoria": "coleta",
                "titulo": "Identificar ativo, unidade e referência do laudo",
                "descricao": (
                    "Registre unidade, local, código/tag da linha de vida, "
                    "número do laudo de inspeção e qualquer referência do "
                    "fabricante já disponível."
                ),
            },
            {
                "id": "nr35_linha_vida_componentes",
                "categoria": "norma",
                "titulo": "Avaliar os seis componentes críticos",
                "descricao": "Deixe explícito o status C, NC ou NA para fixação dos pontos, cabo de aço, esticador, sapatilha, olhal e grampos.",
            },
            {
                "id": "nr35_linha_vida_fotos_conclusao",
                "categoria": "coleta",
                "titulo": "Amarrar registros fotográficos à conclusão",
                "descricao": (
                    "Anexe fotos panorâmicas e de detalhe com legenda curta, "
                    "depois conclua em aprovado, reprovado ou pendente com "
                    "observação objetiva."
                ),
            },
        ],
    },
    "spda": {
        "descricao": "A coleta deve deixar claro o estado do sistema de captação, descidas e aterramento do SPDA.",
        "itens_especificos": [
            {
                "id": "spda_captacao_descidas",
                "categoria": "norma",
                "titulo": "Cobrir captação e descidas",
                "descricao": "Registre pontos visíveis de captação, descidas, conexões e eventuais descontinuidades relevantes.",
            },
            {
                "id": "spda_aterramento_equipotencializacao",
                "categoria": "norma",
                "titulo": "Cobrir aterramento e equipotencialização",
                "descricao": "Deixe evidências das condições de aterramento, barramentos e integrações do sistema.",
            },
        ],
    },
    "pie": {
        "descricao": "Feche o PIE com rastros claros de documentação, quadros, proteção e condições de segurança elétrica.",
        "itens_especificos": [
            {
                "id": "pie_quadros_protecao",
                "categoria": "norma",
                "titulo": "Cobrir quadros e proteção elétrica",
                "descricao": "Inclua evidências de quadros, proteção, identificação e condições visuais das instalações críticas.",
            },
            {
                "id": "pie_documentacao_base",
                "categoria": "norma",
                "titulo": "Relacionar base documental e riscos",
                "descricao": "Amarre a inspeção aos documentos disponíveis e aos principais riscos ou lacunas observadas.",
            },
        ],
    },
    "rti": {
        "descricao": "A RTI deve chegar à mesa com foco em quadros, circuitos críticos, proteção e estado geral da instalação.",
        "itens_especificos": [
            {
                "id": "rti_quadros_circuitos",
                "categoria": "norma",
                "titulo": "Cobrir quadros e circuitos críticos",
                "descricao": "Registre os pontos elétricos mais relevantes, sua identificação e o estado geral de conservação.",
            },
            {
                "id": "rti_nao_conformidades",
                "categoria": "norma",
                "titulo": "Consolidar não conformidades elétricas",
                "descricao": "Se houver desvios, deixe o risco elétrico claramente descrito com foto e observação objetiva.",
            },
        ],
    },
    "loto": {
        "descricao": (
            "A implantação LOTO deve deixar claro quais energias perigosas foram isoladas, "
            "quais pontos de bloqueio foram usados e como a energia zero foi verificada."
        ),
        "itens_especificos": [
            {
                "id": "loto_fontes_bloqueio",
                "categoria": "norma",
                "titulo": "Mapear fontes de energia e pontos de bloqueio",
                "descricao": "Registre a fonte perigosa, o ponto de isolamento correspondente e a identificação do dispositivo aplicado.",
            },
            {
                "id": "loto_energia_zero",
                "categoria": "coleta",
                "titulo": "Confirmar teste de energia zero e sinalização",
                "descricao": "Descreva a verificação da condição segura, etiquetas aplicadas e qualquer pendência de padronização.",
            },
        ],
    },
    "nr11_movimentacao": {
        "descricao": "A coleta precisa fechar o fluxo de movimentação, os dispositivos de segurança e as zonas de risco observadas no equipamento.",
        "itens_especificos": [
            {
                "id": "nr11_fluxo_operacao",
                "categoria": "coleta",
                "titulo": "Cobrir levantamento em campo e fluxo operacional",
                "descricao": "Deixe registrado o equipamento, a carga movimentada, o percurso e as condições do ambiente de operação.",
            },
            {
                "id": "nr11_dispositivos_zonas",
                "categoria": "norma",
                "titulo": "Avaliar dispositivos e zonas de risco",
                "descricao": "Amarre dispositivos de segurança, segurança elétrica e delimitação das zonas de risco com evidências objetivas.",
            },
        ],
    },
    "nr12maquinas": {
        "descricao": "A mesa precisa receber uma coleta fechada sobre proteções, intertravamentos e zonas de risco da máquina.",
        "itens_especificos": [
            {
                "id": "nr12_protecoes_emergencia",
                "categoria": "norma",
                "titulo": "Cobrir proteções e parada de emergência",
                "descricao": "Registre dispositivos de proteção, parada de emergência, enclausuramento e acessos perigosos.",
            },
            {
                "id": "nr12_intertravamentos_operacao",
                "categoria": "norma",
                "titulo": "Cobrir intertravamentos e condição operacional",
                "descricao": "Documente pontos de bloqueio, intertravamentos e condição operacional observada na máquina.",
            },
        ],
    },
    "nr13": {
        "descricao": "A coleta deve deixar rastreável a condição do equipamento e a base documental exigida para NR-13.",
        "itens_especificos": [
            {
                "id": "nr13_identificacao_segurança",
                "categoria": "norma",
                "titulo": "Cobrir identificação e dispositivos de segurança",
                "descricao": "Inclua dados de identificação visível, válvulas, instrumentos e dispositivos de segurança relevantes.",
            },
            {
                "id": "nr13_documentacao_prontuario",
                "categoria": "norma",
                "titulo": "Relacionar prontuário e histórico disponível",
                "descricao": "Deixe claro o que foi conferido de prontuário, inspeções anteriores ou pendências documentais.",
            },
        ],
    },
    "nr13_calibracao": {
        "descricao": "A calibração deve chegar com identificação dos instrumentos, parâmetros de ajuste e rastreabilidade da execução.",
        "itens_especificos": [
            {
                "id": "nr13_calibracao_instrumentos",
                "categoria": "coleta",
                "titulo": "Identificar válvulas, manômetros e faixa de ajuste",
                "descricao": "Registre os instrumentos calibrados, seus códigos, faixas e o critério técnico usado na intervenção.",
            },
            {
                "id": "nr13_calibracao_rastreabilidade",
                "categoria": "norma",
                "titulo": "Fechar certificados, resultados e lacunas",
                "descricao": "Amarre evidências da calibração, certificados emitidos e qualquer desvio ou restrição encontrada.",
            },
        ],
    },
    "nr13_teste_hidrostatico": {
        "descricao": "O teste deve deixar claras as condições do ativo, o procedimento executado e o resultado técnico final.",
        "itens_especificos": [
            {
                "id": "nr13_teste_parametros",
                "categoria": "coleta",
                "titulo": "Registrar parâmetros, pressão e duração do teste",
                "descricao": "Descreva ativo, pressão aplicada, período do teste e condições de execução observadas.",
            },
            {
                "id": "nr13_teste_resultado",
                "categoria": "norma",
                "titulo": "Consolidar resultado, vazamentos e estanqueidade",
                "descricao": "Registre aprovação ou reprovação, ocorrências de vazamento e recomendações técnicas decorrentes do ensaio.",
            },
        ],
    },
    "nr13_ultrassom": {
        "descricao": "A medição por ultrassom precisa chegar com pontos medidos, espessuras mínimas e interpretação do resultado.",
        "itens_especificos": [
            {
                "id": "nr13_ultrassom_pontos",
                "categoria": "coleta",
                "titulo": "Mapear pontos medidos e referências do ativo",
                "descricao": "Indique ativo, localização, malha de medição e a referência usada para identificar cada ponto lido.",
            },
            {
                "id": "nr13_ultrassom_criterio",
                "categoria": "norma",
                "titulo": "Comparar leituras com critério mínimo",
                "descricao": "Deixe explícita a espessura encontrada, o limite técnico adotado e qualquer conclusão de integridade ou reparo.",
            },
        ],
    },
    "nr20_instalacoes": {
        "descricao": "Feche a coleta NR20 com escopo da instalação, análise de riscos e controles operacionais existentes.",
        "itens_especificos": [
            {
                "id": "nr20_instalacao_risco",
                "categoria": "coleta",
                "titulo": "Identificar instalação, produto e cenários de risco",
                "descricao": "Registre a área, o sistema com inflamáveis ou combustíveis e os principais cenários de risco analisados.",
            },
            {
                "id": "nr20_planos_controles",
                "categoria": "norma",
                "titulo": "Amarrar inspeções, manutenção e prevenção",
                "descricao": "Consolide a existência de planos, rotinas de inspeção e controles preventivos ou as lacunas encontradas.",
            },
        ],
    },
    "nr33_espaco_confinado": {
        "descricao": "A coleta deve mapear o espaço confinado, riscos de entrada e plano de resgate com rastreabilidade.",
        "itens_especificos": [
            {
                "id": "nr33_classificacao",
                "categoria": "coleta",
                "titulo": "Classificar o espaço e o cenário operacional",
                "descricao": "Registre tipo do espaço, acesso, atividade executada e responsáveis envolvidos na frente de trabalho.",
            },
            {
                "id": "nr33_risco_resgate",
                "categoria": "norma",
                "titulo": "Cobrir riscos, controles e resgate",
                "descricao": "Deixe evidentes atmosfera, bloqueios, comunicação, vigia e plano de resgate ou lacunas críticas do caso.",
            },
        ],
    },
    "cbmgo": {
        "descricao": "Além das evidências mínimas, este template exige estruturação do formulário antes do envio para a mesa.",
        "itens_especificos": [
            {
                "id": "cbmgo_estrutura_rotas",
                "categoria": "norma",
                "titulo": "Cobrir estrutura, circulação e abandono",
                "descricao": "Registre condições estruturais, circulação, rotas de saída e pontos críticos ligados à segurança contra incêndio.",
            },
            {
                "id": "cbmgo_formulario_estruturado",
                "categoria": "formulario",
                "titulo": "Gerar formulário estruturado obrigatório",
                "descricao": "Finalize a coleta apenas quando o formulário estruturado do template estiver gerado e consistente.",
            },
        ],
    },
    "nr35_ponto_ancoragem": {
        "descricao": "O ponto de ancoragem precisa chegar com base estrutural, fixações e conclusão objetiva sobre liberação de uso.",
        "itens_especificos": [
            {
                "id": "nr35_ancoragem_base",
                "categoria": "coleta",
                "titulo": "Cobrir base estrutural e identificação do ponto",
                "descricao": "Registre a estrutura suporte, o tipo do ponto de ancoragem e sua localização exata na frente inspecionada.",
            },
            {
                "id": "nr35_ancoragem_fixacoes",
                "categoria": "norma",
                "titulo": "Avaliar fixações, plaqueta e integridade",
                "descricao": "Amarre chumbadores, soldas, plaqueta, corrosão e deformações com evidência fotográfica e parecer técnico.",
            },
        ],
    },
    "nr35_projeto": {
        "descricao": "O projeto precisa consolidar premissas, cargas, layout e documentos técnicos suficientes para revisão.",
        "itens_especificos": [
            {
                "id": "nr35_projeto_premissas",
                "categoria": "coleta",
                "titulo": "Registrar escopo, layout e premissas de projeto",
                "descricao": "Deixe claro o ativo, a área coberta, os trechos previstos e as premissas de uso consideradas no projeto.",
            },
            {
                "id": "nr35_projeto_calculo_art",
                "categoria": "norma",
                "titulo": "Amarrar memória de cálculo, ART e critérios",
                "descricao": "Consolide referências de cálculo, ART, cargas admissíveis e qualquer pendência documental da solução proposta.",
            },
        ],
    },
    "nr35_montagem": {
        "descricao": "A montagem deve fechar sequência executiva, componentes instalados e condição de liberação do sistema.",
        "itens_especificos": [
            {
                "id": "nr35_montagem_componentes",
                "categoria": "coleta",
                "titulo": "Registrar componentes instalados e frente de montagem",
                "descricao": "Liste componentes, pontos montados, equipe executora e a etapa atual da montagem com evidência rastreável.",
            },
            {
                "id": "nr35_montagem_liberacao",
                "categoria": "norma",
                "titulo": "Fechar tensionamento, fixação e liberação",
                "descricao": "Descreva ajustes finais, checagens de fixação, pendências de montagem e condição de liberação ou bloqueio do sistema.",
            },
        ],
    },
}

_OVERRIDE_CASE_LABELS: dict[str, str] = {
    "documento_opcional_ausente_com_justificativa_registrada": (
        "Documento opcional ausente com justificativa registrada"
    ),
    "evidencia_complementar_substituida_por_registro_textual_com_rastreabilidade": (
        "Evidência complementar substituída por registro textual com rastreabilidade"
    ),
    "limitacao_controlada_sem_impacto_na_conclusao_critica": (
        "Limitação controlada sem impacto na conclusão crítica"
    ),
}
_OVERRIDE_CASE_ALIASES: dict[str, str] = {
    "documentos_opcionais_nao_disponiveis_mas_ausencia_foi_registrada": (
        "documento_opcional_ausente_com_justificativa_registrada"
    ),
    "evidencia_opcional_substituida_por_registro_textual_justificado_sem_perda_da_rastreabilidade": (
        "evidencia_complementar_substituida_por_registro_textual_com_rastreabilidade"
    ),
    "limitacao_de_acesso_a_item_nao_critico_com_justificativa_sem_impacto_nos_campos_criticos": (
        "limitacao_controlada_sem_impacto_na_conclusao_critica"
    ),
}
_GATE_HARD_BLOCKER_ITEM_IDS = {
    "campo_escopo_inicial",
    "evidencias_textuais",
    "evidencias_minimas",
    "formulario_estruturado",
}
_GATE_HARD_BLOCKER_CODES = {
    "catalog_case_thread_empty",
    "catalog_structured_form_missing",
    "cbmgo_structured_form_missing",
    "guided_checklist_incomplete",
}


def normalize_human_override_case_key(case_key: Any) -> str:
    texto = str(case_key or "").strip().lower()
    if not texto:
        return ""
    return _OVERRIDE_CASE_ALIASES.get(texto, texto)


def _dict_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _family_key_gate_qualidade(laudo: Laudo, tipo_template: str) -> str:
    catalog_snapshot = _dict_payload(getattr(laudo, "catalog_snapshot_json", None))
    family_payload = _dict_payload(catalog_snapshot.get("family"))
    family_key = str(
        getattr(laudo, "catalog_family_key", None)
        or family_payload.get("key")
        or tipo_template
        or "padrao"
    ).strip()
    return family_key.lower() or "padrao"


def _load_family_schema_gate_qualidade(laudo: Laudo, *, tipo_template: str) -> dict[str, Any]:
    catalog_snapshot = _dict_payload(getattr(laudo, "catalog_snapshot_json", None))
    artifacts = _dict_payload(catalog_snapshot.get("artifacts"))
    family_schema_snapshot = (
        dict(artifacts.get("family_schema") or {})
        if isinstance(artifacts.get("family_schema"), dict)
        else None
    )
    if family_schema_snapshot:
        return family_schema_snapshot

    family_key = _family_key_gate_qualidade(laudo, tipo_template)
    if not family_key or family_key == "padrao":
        return {}

    path = (resolve_family_schemas_dir() / f"{family_key}.json").resolve()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_override_cases(raw_value: Any) -> list[str]:
    if not isinstance(raw_value, list):
        return []
    seen: set[str] = set()
    resultado: list[str] = []
    for item in raw_value:
        chave = normalize_human_override_case_key(item)
        if not chave:
            continue
        if chave in seen:
            continue
        seen.add(chave)
        resultado.append(chave)
    return resultado


def _override_case_label(case_key: str) -> str:
    return _OVERRIDE_CASE_LABELS.get(
        str(case_key or "").strip().lower(),
        str(case_key or "").strip().replace("_", " ") or "Exceção governada",
    )


def _gate_item_is_hard_blocker(item: dict[str, Any]) -> bool:
    item_id = str(item.get("id") or "").strip().lower()
    categoria = str(item.get("categoria") or "").strip().lower()
    observacao = str(item.get("observacao") or item.get("titulo") or "").strip().lower()
    if item_id == "report_pack_incremental":
        return False
    if item_id in _GATE_HARD_BLOCKER_ITEM_IDS:
        return True
    if any(code in item_id for code in _GATE_HARD_BLOCKER_CODES):
        return True
    if categoria in {"structured_form", "checklist", "report_pack"}:
        return True
    if categoria == "campo_critico" and item_id != "campo_parecer_ia":
        return True
    if categoria == "evidencia" and item_id not in {"fotos_essenciais"}:
        return True
    if "checklist" in observacao or "payload estruturado" in observacao:
        return True
    return False


def _gate_item_override_case_candidates(item: dict[str, Any]) -> list[str]:
    item_id = str(item.get("id") or "").strip().lower()
    categoria = str(item.get("categoria") or "").strip().lower()
    observacao = str(item.get("observacao") or item.get("titulo") or "").strip().lower()
    candidatos: list[str] = []

    if item_id == "campo_parecer_ia":
        candidatos.append("limitacao_controlada_sem_impacto_na_conclusao_critica")

    if categoria in {"foto", "image_slot"} or "foto" in item_id or "imagem" in observacao:
        candidatos.append(
            "evidencia_complementar_substituida_por_registro_textual_com_rastreabilidade"
        )

    if categoria in {"document", "documento"} or "document" in item_id or "prontuario" in item_id:
        candidatos.append("documento_opcional_ausente_com_justificativa_registrada")

    if categoria in {"normative_item", "norma"} or "normativo" in observacao:
        candidatos.append("limitacao_controlada_sem_impacto_na_conclusao_critica")

    vistos: set[str] = set()
    resultado: list[str] = []
    for candidato in candidatos:
        chave = str(candidato or "").strip().lower()
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(chave)
    return resultado


def _build_human_override_policy(
    *,
    laudo: Laudo,
    tipo_template: str,
    resultado_gate: dict[str, Any],
) -> dict[str, Any]:
    family_schema = _load_family_schema_gate_qualidade(laudo, tipo_template=tipo_template)
    review_policy = (
        dict(family_schema.get("review_policy") or {})
        if isinstance(family_schema.get("review_policy"), dict)
        else {}
    )
    allowed_override_cases = _normalize_override_cases(
        review_policy.get("allowed_override_cases")
    )
    override_enabled = bool(review_policy.get("allow_override_with_reason"))
    faltantes = list(resultado_gate.get("faltantes") or [])
    overrideable_items: list[dict[str, Any]] = []
    hard_blockers: list[dict[str, Any]] = []
    matched_cases: list[str] = []

    for item in faltantes:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "").strip().lower() == "report_pack_incremental":
            continue
        candidates = [
            case_key
            for case_key in _gate_item_override_case_candidates(item)
            if case_key in allowed_override_cases
        ]
        payload_item = {
            "id": str(item.get("id") or "").strip(),
            "titulo": str(item.get("titulo") or "Pendência do gate").strip(),
            "categoria": str(item.get("categoria") or "").strip(),
            "candidate_cases": candidates,
            "candidate_case_labels": [_override_case_label(case_key) for case_key in candidates],
        }
        if not candidates or _gate_item_is_hard_blocker(item):
            hard_blockers.append(payload_item)
            continue
        overrideable_items.append(payload_item)
        for case_key in candidates:
            if case_key not in matched_cases:
                matched_cases.append(case_key)

    available = bool(override_enabled and overrideable_items and not hard_blockers)
    message = (
        "A divergência pode seguir como exceção governada com justificativa interna obrigatória."
        if available
        else (
            "Este bloqueio ainda depende de correção da coleta antes do envio."
            if faltantes
            else "Nenhuma exceção governada está pendente neste gate."
        )
    )

    return {
        "available": available,
        "reason_required": bool(override_enabled),
        "allowed_override_cases": allowed_override_cases,
        "allowed_override_case_labels": [
            _override_case_label(case_key) for case_key in allowed_override_cases
        ],
        "matched_override_cases": matched_cases,
        "matched_override_case_labels": [
            _override_case_label(case_key) for case_key in matched_cases
        ],
        "overrideable_items": overrideable_items,
        "hard_blockers": hard_blockers,
        "family_key": _family_key_gate_qualidade(laudo, tipo_template),
        "responsibility_notice": (
            "A justificativa fica apenas na trilha interna do caso. "
            "A responsabilidade final continua sendo da validação e assinatura humana."
        ),
        "message": message,
    }


def _mensagem_eh_comando_sistema(conteudo: str) -> bool:
    texto = (conteudo or "").strip()
    if not texto:
        return False

    texto_lower = texto.lower()
    return (
        "[comando_sistema]" in texto_lower
        or "[comando_rapido]" in texto_lower
        or "comando_sistema finalizarlaudoagora" in texto_lower
        or "solicitou encerramento e geração do laudo" in texto_lower
        or "solicitou encerramento e geracao do laudo" in texto_lower
    )


def _mensagem_representa_foto(conteudo: str) -> bool:
    texto = (conteudo or "").strip().lower()
    return texto in {"[imagem]", "imagem enviada", "[foto]"}


def _mensagem_representa_documento(conteudo: str) -> bool:
    return mensagem_representa_documento(conteudo)


def _mensagem_textual_relevante(conteudo: str) -> bool:
    texto = (conteudo or "").strip()
    if not texto:
        return False
    if _mensagem_eh_comando_sistema(texto):
        return False
    if _mensagem_representa_foto(texto):
        return False
    if _mensagem_representa_documento(texto):
        return False

    texto_util = re.sub(r"[\W_]+", "", texto, flags=re.UNICODE)
    return len(texto_util) >= 8


def _primeira_mensagem_qualificada(laudo: Laudo) -> bool:
    texto = (laudo.primeira_mensagem or "").strip()
    if not texto:
        return False

    texto_lower = texto.lower()
    if texto_lower in {"nova conversa", "imagem enviada", "[imagem]"}:
        return False
    if (texto_lower.startswith("relatório ") or texto_lower.startswith("relatorio ")) and "iniciado" in texto_lower:
        return False

    texto_util = re.sub(r"[\W_]+", "", texto, flags=re.UNICODE)
    return len(texto_util) >= 8


def _item_gate_qualidade(
    *,
    item_id: str,
    categoria: str,
    titulo: str,
    ok: bool,
    atual: Any,
    minimo: Any,
    observacao: str,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "categoria": categoria,
        "titulo": titulo,
        "status": "ok" if ok else "faltante",
        "atual": atual,
        "minimo": minimo,
        "observacao": observacao,
    }


def _item_roteiro_template(
    *,
    item_id: str,
    categoria: str,
    titulo: str,
    descricao: str,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "categoria": categoria,
        "titulo": titulo,
        "descricao": descricao,
        "obrigatorio": True,
    }


def _montar_roteiro_template_qualidade(tipo_template: str, regra: dict[str, Any]) -> dict[str, Any]:
    configuracao = ROTEIRO_COLETA_TEMPLATE.get(
        tipo_template,
        ROTEIRO_COLETA_TEMPLATE["padrao"],
    )
    min_textos = int(regra.get("min_textos", 0) or 0)
    min_evidencias = int(regra.get("min_evidencias", 0) or 0)
    min_fotos = int(regra.get("min_fotos", 0) or 0)
    min_mensagens_ia = int(regra.get("min_mensagens_ia", 0) or 0)
    requer_dados_formulario = bool(regra.get("requer_dados_formulario", False))

    itens = [
        _item_roteiro_template(
            item_id="roteiro_escopo_inicial",
            categoria="campo_critico",
            titulo="Registrar escopo inicial qualificado",
            descricao="Abra a inspeção com contexto técnico útil, identificando ativo, área ou processo e o motivo da coleta.",
        ),
        _item_roteiro_template(
            item_id="roteiro_textos_campo",
            categoria="evidencia",
            titulo="Consolidar registros textuais de campo",
            descricao=f"Registre pelo menos {min_textos} observação(ões) textual(is) úteis com achados, medições ou contexto operacional.",
        ),
        _item_roteiro_template(
            item_id="roteiro_evidencias_minimas",
            categoria="evidencia",
            titulo="Fechar evidências mínimas da coleta",
            descricao=f"Combine texto, foto e/ou documento até atingir ao menos {min_evidencias} evidência(s) válida(s) para sustentar o laudo.",
        ),
        _item_roteiro_template(
            item_id="roteiro_fotos_essenciais",
            categoria="foto",
            titulo="Registrar fotos essenciais",
            descricao=f"Garanta ao menos {min_fotos} foto(s) dos pontos críticos antes do envio para a mesa.",
        ),
        _item_roteiro_template(
            item_id="roteiro_parecer_ia",
            categoria="ia",
            titulo="Obter parecer preliminar da IA",
            descricao=f"Feche a coleta com pelo menos {min_mensagens_ia} resposta(s) técnica(s) da IA consolidando o contexto observado.",
        ),
    ]

    if requer_dados_formulario:
        itens.append(
            _item_roteiro_template(
                item_id="roteiro_formulario_estruturado",
                categoria="formulario",
                titulo="Gerar formulário estruturado do template",
                descricao="Este template exige estruturação obrigatória antes da finalização e envio para a mesa.",
            )
        )

    for item in configuracao.get("itens_especificos", []):
        itens.append(
            _item_roteiro_template(
                item_id=str(item.get("id") or "roteiro_template_item"),
                categoria=str(item.get("categoria") or "coleta"),
                titulo=str(item.get("titulo") or "Ponto crítico do template"),
                descricao=str(item.get("descricao") or "").strip(),
            )
        )

    return {
        "titulo": "Roteiro obrigatório do template",
        "descricao": str(configuracao.get("descricao") or "").strip(),
        "itens": itens,
    }


def avaliar_gate_qualidade_laudo(banco: Session, laudo: Laudo) -> dict[str, Any]:
    tipo_template = normalizar_tipo_template(getattr(laudo, "tipo_template", "padrao"))
    regra = REGRAS_GATE_QUALIDADE_TEMPLATE.get(
        tipo_template,
        REGRAS_GATE_QUALIDADE_TEMPLATE["padrao"],
    )

    mensagens = banco.query(MensagemLaudo).filter(MensagemLaudo.laudo_id == laudo.id).order_by(MensagemLaudo.criado_em.asc()).all()
    mensagens_usuario = [item for item in mensagens if item.tipo in (TipoMensagem.USER.value, TipoMensagem.HUMANO_INSP.value)]
    mensagens_ia = [item for item in mensagens if item.tipo == TipoMensagem.IA.value]
    mensagens_com_evidencia_visual = {
        int(mensagem_id)
        for (mensagem_id,) in (
            banco.query(AprendizadoVisualIa.mensagem_referencia_id)
            .filter(
                AprendizadoVisualIa.laudo_id == laudo.id,
                AprendizadoVisualIa.mensagem_referencia_id.isnot(None),
                AprendizadoVisualIa.imagem_url.isnot(None),
            )
            .all()
        )
        if mensagem_id
    }

    qtd_textos = 0
    qtd_fotos = 0
    qtd_documentos = 0
    qtd_evidencias = 0

    for item in mensagens_usuario:
        conteudo = (item.conteudo or "").strip()
        eh_texto = _mensagem_textual_relevante(conteudo)
        eh_foto = _mensagem_representa_foto(conteudo) or int(getattr(item, "id", 0) or 0) in mensagens_com_evidencia_visual
        eh_documento = _mensagem_representa_documento(conteudo)

        if eh_texto:
            qtd_textos += 1
        if eh_foto:
            qtd_fotos += 1
        if eh_documento:
            qtd_documentos += 1
        qtd_evidencias += int(eh_texto) + int(eh_foto) + int(eh_documento)

    min_textos = int(regra.get("min_textos", 0) or 0)
    min_evidencias = int(regra.get("min_evidencias", 0) or 0)
    min_fotos = int(regra.get("min_fotos", 0) or 0)
    min_mensagens_ia = int(regra.get("min_mensagens_ia", 0) or 0)
    requer_dados_formulario = bool(regra.get("requer_dados_formulario", False))

    report_pack_draft = atualizar_report_pack_draft_laudo(banco=banco, laudo=laudo)
    report_pack_quality_gates = dict((report_pack_draft or {}).get("quality_gates") or {})
    report_pack_missing_evidence = list(report_pack_quality_gates.get("missing_evidence") or [])
    report_pack_structured_ready = bool((report_pack_draft or {}).get("structured_data_candidate"))

    primeira_ok = _primeira_mensagem_qualificada(laudo)
    mensagens_ia_ok = report_pack_structured_ready or len(mensagens_ia) >= min_mensagens_ia
    textos_ok = qtd_textos >= min_textos
    evidencias_ok = qtd_evidencias >= min_evidencias
    fotos_ok = qtd_fotos >= min_fotos
    dados_formulario_ok = (not requer_dados_formulario) or bool(laudo.dados_formulario)
    roteiro_template = _montar_roteiro_template_qualidade(tipo_template, regra)

    itens = [
        _item_gate_qualidade(
            item_id="campo_escopo_inicial",
            categoria="campo_critico",
            titulo="Escopo inicial da inspeção",
            ok=primeira_ok,
            atual="registrado" if primeira_ok else "ausente",
            minimo="registrado",
            observacao="Defina contexto técnico inicial da inspeção no chat.",
        ),
        _item_gate_qualidade(
            item_id="campo_parecer_ia",
            categoria="campo_critico",
            titulo="Parecer técnico preliminar da IA",
            ok=mensagens_ia_ok,
            atual="dispensado" if report_pack_structured_ready else len(mensagens_ia),
            minimo="dispensado" if report_pack_structured_ready else min_mensagens_ia,
            observacao=(
                "O report pack canonico ja materializou o formulario estruturado; o parecer previo da IA deixa de ser obrigatorio."
                if report_pack_structured_ready
                else "A IA precisa consolidar ao menos uma resposta técnica antes do envio."
            ),
        ),
        _item_gate_qualidade(
            item_id="evidencias_textuais",
            categoria="evidencia",
            titulo="Registros textuais de campo",
            ok=textos_ok,
            atual=qtd_textos,
            minimo=min_textos,
            observacao="Descreva achados, medições e contexto operacional.",
        ),
        _item_gate_qualidade(
            item_id="evidencias_minimas",
            categoria="evidencia",
            titulo="Evidências mínimas consolidadas",
            ok=evidencias_ok,
            atual=qtd_evidencias,
            minimo=min_evidencias,
            observacao="Combine texto, fotos e documentos para suportar o laudo.",
        ),
        _item_gate_qualidade(
            item_id="fotos_essenciais",
            categoria="foto",
            titulo="Fotos essenciais da inspeção",
            ok=fotos_ok,
            atual=qtd_fotos,
            minimo=min_fotos,
            observacao="Envie imagens dos pontos críticos antes de finalizar.",
        ),
    ]

    if requer_dados_formulario:
        itens.append(
            _item_gate_qualidade(
                item_id="formulario_estruturado",
                categoria="campo_critico",
                titulo="Formulário estruturado obrigatório",
                ok=dados_formulario_ok,
                atual="gerado" if dados_formulario_ok else "pendente",
                minimo="gerado",
                observacao="O template selecionado exige estruturação automática antes do envio.",
            )
        )

    if report_pack_draft is not None and bool(report_pack_draft.get("modeled")):
        itens.append(
            _item_gate_qualidade(
                item_id="report_pack_incremental",
                categoria="report_pack",
                titulo="Draft incremental do report pack",
                ok=not report_pack_missing_evidence,
                atual="consistente" if not report_pack_missing_evidence else "com pendencias",
                minimo="consistente",
                observacao="O caso precisa manter o draft incremental consistente antes da finalizacao.",
            )
        )
        for index, missing in enumerate(report_pack_missing_evidence, start=1):
            code = str(missing.get("code") or f"report_pack_missing_{index}").strip()
            label = str(missing.get("message") or "Pendencia do report pack.").strip()
            item_ref = str(missing.get("item_codigo") or missing.get("slot") or "").strip()
            itens.append(
                _item_gate_qualidade(
                    item_id=code if not item_ref else f"{code}:{item_ref}",
                    categoria=str(missing.get("kind") or "report_pack"),
                    titulo=label[:120],
                    ok=False,
                    atual="pendente",
                    minimo="resolvido",
                    observacao=label,
                )
            )

    faltantes = [item for item in itens if item["status"] == "faltante"]
    aprovado = len(faltantes) == 0

    resumo = {
        "mensagens_usuario": len(mensagens_usuario),
        "mensagens_ia": len(mensagens_ia),
        "textos_campo": qtd_textos,
        "fotos": qtd_fotos,
        "documentos": qtd_documentos,
        "evidencias": qtd_evidencias,
    }

    mensagem = (
        "Gate de qualidade aprovado. O laudo pode ser enviado para a mesa avaliadora."
        if aprovado
        else (f"Finalize bloqueado: faltam {len(faltantes)} item(ns) obrigatório(s) no checklist de qualidade.")
    )

    resultado = {
        "codigo": "GATE_QUALIDADE_OK" if aprovado else "GATE_QUALIDADE_REPROVADO",
        "aprovado": aprovado,
        "mensagem": mensagem,
        "tipo_template": tipo_template,
        "template_nome": nome_template_humano(tipo_template),
        "resumo": resumo,
        "itens": itens,
        "faltantes": faltantes,
        "roteiro_template": roteiro_template,
        "report_pack_draft": report_pack_draft,
        "review_mode_sugerido": str(
            report_pack_quality_gates.get("final_validation_mode") or "mesa_required"
        ),
        "human_override_policy": _build_human_override_policy(
            laudo=laudo,
            tipo_template=tipo_template,
            resultado_gate={
                "faltantes": faltantes,
            },
        ),
    }
    record_report_pack_gate_observation(
        laudo=laudo,
        report_pack_draft=report_pack_draft,
        approved=aprovado,
        review_mode_sugerido=str(resultado["review_mode_sugerido"]),
    )
    return resultado


def garantir_gate_qualidade_laudo(banco: Session, laudo: Laudo) -> dict[str, Any]:
    resultado = avaliar_gate_qualidade_laudo(banco, laudo)
    if not bool(resultado.get("aprovado", False)):
        raise HTTPException(
            status_code=422,
            detail=resultado,
        )
    return resultado


__all__ = [
    "REGRAS_GATE_QUALIDADE_TEMPLATE",
    "avaliar_gate_qualidade_laudo",
    "garantir_gate_qualidade_laudo",
    "normalize_human_override_case_key",
]
