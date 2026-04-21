# ruff: noqa: E501
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PortfolioFamilySpec:
    family_key: str
    nome_exibicao: str
    macro_categoria: str
    kind: str
    wave: int
    objeto_exemplo: str
    localizacao_exemplo: str
    scope_example: str
    method_example: str
    document_example: str
    point_example: str
    recommendation_example: str
    status_example: str
    template_code: str | None = None


REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILY_SCHEMAS_DIR = REPO_ROOT / "docs" / "family_schemas"
WEB_DOCS_DIR = REPO_ROOT / "web" / "docs"

TOKENS_EXEMPLO = {
    "cliente_nome": "Empresa Teste NR13",
    "unidade_nome": "Unidade Piloto NR13",
    "engenheiro_responsavel": "Gabriel Santos",
    "crea_art": "CREA 123456/D | ART 922024900",
    "revisao_template": "v1",
}

KIND_DEFAULTS: dict[str, dict[str, Any]] = {
    "inspection": {
        "min_fotos": 4,
        "min_documentos": 0,
        "min_textos": 1,
        "tipo_entrega": "inspecao_tecnica",
        "modo_execucao": "in_loco",
        "section_titles": {
            "identificacao": "Identificacao do Ativo",
            "escopo_servico": "Escopo da Inspecao",
            "execucao_servico": "Execucao em Campo",
            "evidencias_e_anexos": "Evidencias Principais",
            "documentacao_e_registros": "Documentacao e Registros",
            "nao_conformidades_ou_lacunas": "Nao Conformidades ou Lacunas",
            "recomendacoes": "Recomendacoes",
            "conclusao": "Conclusao",
        },
    },
    "test": {
        "min_fotos": 3,
        "min_documentos": 0,
        "min_textos": 1,
        "tipo_entrega": "teste_tecnico",
        "modo_execucao": "campo_controlado",
        "section_titles": {
            "identificacao": "Identificacao do Objeto de Teste",
            "escopo_servico": "Escopo do Teste",
            "execucao_servico": "Execucao do Teste",
            "evidencias_e_anexos": "Evidencias e Registros",
            "documentacao_e_registros": "Documentacao e Registros",
            "nao_conformidades_ou_lacunas": "Desvios ou Lacunas",
            "recomendacoes": "Recomendacoes",
            "conclusao": "Conclusao",
        },
    },
    "documentation": {
        "min_fotos": 1,
        "min_documentos": 1,
        "min_textos": 1,
        "tipo_entrega": "pacote_documental",
        "modo_execucao": "analise_documental",
        "section_titles": {
            "identificacao": "Identificacao do Pacote",
            "escopo_servico": "Escopo Documental",
            "execucao_servico": "Execucao do Levantamento",
            "evidencias_e_anexos": "Evidencias e Anexos",
            "documentacao_e_registros": "Documentacao e Registros",
            "nao_conformidades_ou_lacunas": "Lacunas ou Pendencias",
            "recomendacoes": "Recomendacoes",
            "conclusao": "Conclusao",
        },
    },
    "engineering": {
        "min_fotos": 0,
        "min_documentos": 1,
        "min_textos": 1,
        "tipo_entrega": "engenharia",
        "modo_execucao": "analise_e_modelagem",
        "section_titles": {
            "identificacao": "Identificacao do Objeto",
            "escopo_servico": "Escopo de Engenharia",
            "execucao_servico": "Execucao Tecnica",
            "evidencias_e_anexos": "Anexos e Referencias",
            "documentacao_e_registros": "Documentacao e Registros",
            "nao_conformidades_ou_lacunas": "Lacunas Tecnicas",
            "recomendacoes": "Recomendacoes",
            "conclusao": "Conclusao",
        },
    },
    "calculation": {
        "min_fotos": 0,
        "min_documentos": 1,
        "min_textos": 1,
        "tipo_entrega": "calculo_tecnico",
        "modo_execucao": "memoria_de_calculo",
        "section_titles": {
            "identificacao": "Identificacao do Calculo",
            "escopo_servico": "Escopo do Calculo",
            "execucao_servico": "Dados e Premissas",
            "evidencias_e_anexos": "Memoria e Referencias",
            "documentacao_e_registros": "Documentacao e Registros",
            "nao_conformidades_ou_lacunas": "Lacunas Tecnicas",
            "recomendacoes": "Recomendacoes",
            "conclusao": "Conclusao",
        },
    },
    "training": {
        "min_fotos": 1,
        "min_documentos": 1,
        "min_textos": 1,
        "tipo_entrega": "treinamento",
        "modo_execucao": "turma_programada",
        "section_titles": {
            "identificacao": "Identificacao da Turma",
            "escopo_servico": "Escopo do Treinamento",
            "execucao_servico": "Execucao do Treinamento",
            "evidencias_e_anexos": "Evidencias e Registros",
            "documentacao_e_registros": "Documentacao e Registros",
            "nao_conformidades_ou_lacunas": "Pontos de Atencao",
            "recomendacoes": "Recomendacoes",
            "conclusao": "Conclusao",
        },
    },
    "ndt": {
        "min_fotos": 2,
        "min_documentos": 0,
        "min_textos": 1,
        "tipo_entrega": "ensaio_nao_destrutivo",
        "modo_execucao": "campo_e_registro_tecnico",
        "section_titles": {
            "identificacao": "Identificacao do Ensaio",
            "escopo_servico": "Escopo da Tecnica Aplicada",
            "execucao_servico": "Execucao do Ensaio",
            "evidencias_e_anexos": "Evidencias e Registros",
            "documentacao_e_registros": "Documentacao e Registros",
            "nao_conformidades_ou_lacunas": "Indicacoes ou Pontos de Atencao",
            "recomendacoes": "Recomendacoes",
            "conclusao": "Conclusao",
        },
    },
}

MISSING_PORTFOLIO_FAMILIES: list[PortfolioFamilySpec] = [
    PortfolioFamilySpec(
        family_key="nr13_inspecao_tubulacao",
        nome_exibicao="NR13 - Inspecao de Tubulacao",
        macro_categoria="NR13",
        kind="inspection",
        wave=1,
        objeto_exemplo="Tubulacao de vapor linha TV-203",
        localizacao_exemplo="Rack norte da unidade de utilidades",
        scope_example="Inspecao de seguranca periodica em tubulacao abrangida pela NR13, com foco em identificacao, suportacao, acessorios aparentes, sinais visuais e registros disponiveis.",
        method_example="Inspecao visual da linha, suportes, identificacao e acessorios aparentes, com consolidacao textual das condicoes observadas.",
        document_example="Fluxograma das linhas e relatorio anterior da tubulacao.",
        point_example="Oxidacao superficial localizada em suporte secundario e necessidade de reforcar identificacao visual da linha.",
        recommendation_example="Atualizar identificacao visual da linha e acompanhar o ponto de oxidacao em proxima rodada de inspecao.",
        status_example="ajuste",
    ),
    PortfolioFamilySpec(
        family_key="nr13_integridade_caldeira",
        nome_exibicao="NR13 - Integridade de Caldeira",
        macro_categoria="NR13",
        kind="inspection",
        wave=1,
        objeto_exemplo="Caldeira horizontal CAL-02",
        localizacao_exemplo="Casa de caldeiras da unidade norte",
        scope_example="Avaliacao de integridade em caldeira com foco em registros, evidencias de campo, complementacao de historico e consolidacao tecnica para decisao de continuidade operacional.",
        method_example="Analise de integridade combinando evidencias visuais, registros tecnicos disponiveis e apontamentos complementares da equipe responsavel.",
        document_example="Prontuario da caldeira, relatorio anterior e registros de acompanhamento.",
        point_example="Necessidade de complementar memoria historica e consolidar registros de espessura e intervencoes anteriores.",
        recommendation_example="Completar o pacote historico e manter rastreabilidade das avaliacoes complementares associadas a integridade do ativo.",
        status_example="ajuste",
    ),
    PortfolioFamilySpec(
        family_key="nr13_teste_hidrostatico",
        nome_exibicao="NR13 - Teste Hidrostatico",
        macro_categoria="NR13",
        kind="test",
        wave=1,
        objeto_exemplo="Vaso de pressao VPH-11 submetido a teste hidrostatico",
        localizacao_exemplo="Area controlada de manutencao pesada",
        scope_example="Execucao e registro de teste hidrostatico em ativo abrangido pela NR13, com parametros de teste, evidencias do procedimento e consolidacao de resultado tecnico.",
        method_example="Preparacao do ativo, aplicacao do procedimento de teste, registro dos parametros e consolidacao do comportamento observado durante a execucao.",
        document_example="Procedimento de teste e ficha de registro da execucao.",
        point_example="Necessidade de repetir leitura complementar de um ponto por oscilacao de registro durante a execucao.",
        recommendation_example="Manter o registro consolidado do teste e anexar a ficha final ao pacote documental do ativo.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="nr13_teste_estanqueidade_tubulacao_gas",
        nome_exibicao="NR13 - Teste de Estanqueidade em Tubulacao de Gas",
        macro_categoria="NR13",
        kind="test",
        wave=1,
        objeto_exemplo="Tubulacao de gas combustivel linha TG-12",
        localizacao_exemplo="Casa de utilidades e alimentacao do queimador principal",
        scope_example="Execucao e registro de teste de estanqueidade em tubulacao de gas, com consolidacao de parametros, evidencias e resultado da verificacao.",
        method_example="Preparacao do trecho, aplicacao do teste de estanqueidade e registro das leituras e do comportamento observado.",
        document_example="Ficha do teste e croqui do trecho inspecionado.",
        point_example="Necessidade de reforcar a identificacao de um trecho secundario antes da liberacao documental final.",
        recommendation_example="Anexar o croqui final e manter a rastreabilidade do trecho testado no prontuario da linha.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="nr13_reconstituicao_prontuario",
        nome_exibicao="NR13 - Reconstituicao de Prontuario",
        macro_categoria="NR13",
        kind="documentation",
        wave=2,
        objeto_exemplo="Prontuario NR13 do vaso de pressao VP-204",
        localizacao_exemplo="Base documental da unidade de utilidades",
        scope_example="Levantamento, consolidacao e reconstituicao de prontuario e documentos exigidos para o ativo abrangido pela NR13.",
        method_example="Levantamento documental, consolidacao de fontes, verificacao de lacunas e montagem do pacote reconstituido.",
        document_example="Prontuario reconstituido e matriz de documentos consolidados.",
        point_example="Ausencia parcial de historico anterior e necessidade de registrar formalmente a lacuna remanescente.",
        recommendation_example="Manter o pacote reconstituido versionado e atualizar sempre que novos registros forem incorporados.",
        status_example="ajuste",
    ),
    PortfolioFamilySpec(
        family_key="nr13_abertura_livro_registro_seguranca",
        nome_exibicao="NR13 - Abertura de Livro de Registro de Seguranca",
        macro_categoria="NR13",
        kind="documentation",
        wave=2,
        objeto_exemplo="Livro de registro de seguranca da caldeira CAL-01",
        localizacao_exemplo="Casa de caldeiras da unidade piloto",
        scope_example="Estruturacao inicial do livro de registro de seguranca com consolidacao de dados basicos, referencias e orientacoes de uso.",
        method_example="Levantamento dos dados minimos do ativo, definicao do formato de registro e consolidacao do documento inicial.",
        document_example="Livro de registro de seguranca aberto e instrucoes de preenchimento.",
        point_example="Necessidade de complementar historico inicial de registros para fechamento do primeiro ciclo.",
        recommendation_example="Definir responsavel pelo registro continuo e manter a atualizacao auditavel do livro.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="nr13_levantamento_in_loco_equipamentos",
        nome_exibicao="NR13 - Levantamento In Loco de Equipamentos",
        macro_categoria="NR13",
        kind="documentation",
        wave=2,
        objeto_exemplo="Levantamento in loco dos ativos NR13 da unidade norte",
        localizacao_exemplo="Planta industrial da unidade norte",
        scope_example="Levantamento em campo dos equipamentos abrangidos pela NR13 com inventario inicial e consolidacao de referencias para regularizacao.",
        method_example="Percurso em campo, identificacao dos ativos, registro visual e consolidacao do inventario inicial.",
        document_example="Inventario preliminar dos equipamentos NR13 da unidade.",
        point_example="Divergencia entre identificacao visual de um ativo e a nomenclatura documental anteriormente utilizada.",
        recommendation_example="Fechar o inventario oficial e alinhar a nomenclatura documental dos ativos identificados.",
        status_example="ajuste",
    ),
    PortfolioFamilySpec(
        family_key="nr13_fluxograma_linhas_acessorios",
        nome_exibicao="NR13 - Fluxograma com Identificacao das Linhas e Acessorios",
        macro_categoria="NR13",
        kind="documentation",
        wave=2,
        objeto_exemplo="Fluxograma das linhas e acessorios da casa de caldeiras",
        localizacao_exemplo="Planta de utilidades da unidade piloto",
        scope_example="Elaboracao e consolidacao de fluxograma com identificacao das linhas e acessorios vinculados aos ativos NR13.",
        method_example="Levantamento das linhas em campo e consolidacao grafica das referencias principais utilizadas na operacao e manutencao.",
        document_example="Fluxograma revisado com identificacao das linhas e acessorios principais.",
        point_example="Trecho secundario ainda necessita confirmacao final de identificacao em campo.",
        recommendation_example="Atualizar o fluxograma sempre que houver alteracao relevante no arranjo das linhas ou acessorios.",
        status_example="ajuste",
    ),
    PortfolioFamilySpec(
        family_key="nr13_adequacao_planta_industrial",
        nome_exibicao="NR13 - Adequacao de Planta Industrial",
        macro_categoria="NR13",
        kind="engineering",
        wave=3,
        objeto_exemplo="Adequacao da planta industrial aos requisitos NR13",
        localizacao_exemplo="Planta industrial da unidade norte",
        scope_example="Avaliacao e proposta de adequacao da planta industrial com foco nos itens aplicaveis da NR13 para os ativos existentes.",
        method_example="Analise tecnica das condicoes atuais da planta, consolidacao das lacunas observadas e proposta de encaminhamento de adequacao.",
        document_example="Pacote de adequacao com memoria descritiva e referencias de campo.",
        point_example="Necessidade de compatibilizar a identificacao dos ativos em planta com os registros de campo levantados.",
        recommendation_example="Executar adequacoes por frente priorizada e manter a planta industrial versionada com os ativos NR13 consolidados.",
        status_example="ajuste",
    ),
    PortfolioFamilySpec(
        family_key="nr13_projeto_instalacao",
        nome_exibicao="NR13 - Projeto de Instalacao",
        macro_categoria="NR13",
        kind="engineering",
        wave=3,
        objeto_exemplo="Projeto de instalacao da casa de caldeiras da unidade piloto",
        localizacao_exemplo="Unidade piloto NR13",
        scope_example="Elaboracao e aprovacao de projeto de instalacao com consolidacao tecnica, referencias de campo e premissas de engenharia aplicaveis ao escopo contratado.",
        method_example="Levantamento tecnico, definicao de premissas, consolidacao de memoria descritiva e referencias do projeto de instalacao.",
        document_example="Projeto de instalacao com memoria descritiva e referencias anexas.",
        point_example="Necessidade de validar um ponto de interface entre o arranjo atual e a solucao proposta.",
        recommendation_example="Consolidar o projeto aprovado como base unica para implantacao e controle de alteracoes posteriores.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="nr13_par_projeto_alteracao_reparo",
        nome_exibicao="NR13 - PAR Projeto de Alteracao ou Reparo",
        macro_categoria="NR13",
        kind="engineering",
        wave=3,
        objeto_exemplo="PAR-2026-001 para alteracao localizada em vaso de pressao",
        localizacao_exemplo="Area de manutencao e engenharia da unidade piloto",
        scope_example="Elaboracao e aprovacao de projeto de alteracao ou reparo com consolidacao tecnica e rastreabilidade das decisoes associadas ao ativo.",
        method_example="Levantamento do escopo de alteracao ou reparo, consolidacao das premissas e formalizacao do pacote tecnico correspondente.",
        document_example="PAR aprovado com memoria descritiva, referencias e anexos do reparo ou alteracao.",
        point_example="Necessidade de anexar uma referencia complementar de rastreabilidade do trecho tratado.",
        recommendation_example="Versionar o PAR como referencia oficial da intervencao e manter vinculo com o historico do ativo.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="nr13_calculo_pmta_vaso_pressao",
        nome_exibicao="NR13 - Calculo de PMTA de Vaso de Pressao",
        macro_categoria="NR13",
        kind="calculation",
        wave=3,
        objeto_exemplo="Calculo de PMTA do vaso de pressao VP-204",
        localizacao_exemplo="Base tecnica da unidade de utilidades",
        scope_example="Determinacao tecnica da PMTA de vaso de pressao com consolidacao das premissas, dados de entrada e resultados do calculo.",
        method_example="Levantamento de dados tecnicos, consolidacao de premissas e memoria de calculo para determinacao da PMTA.",
        document_example="Memoria de calculo da PMTA e referencias anexas.",
        point_example="Necessidade de confirmar um dado dimensional complementar antes do fechamento definitivo da memoria.",
        recommendation_example="Manter a memoria de calculo vinculada ao historico do vaso e revisar quando houver alteracao relevante do ativo.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="nr13_calculo_espessura_minima_caldeira",
        nome_exibicao="NR13 - Calculo de Espessura Minima de Caldeira",
        macro_categoria="NR13",
        kind="calculation",
        wave=3,
        objeto_exemplo="Calculo de espessura minima da caldeira CAL-01",
        localizacao_exemplo="Base tecnica da casa de caldeiras",
        scope_example="Determinacao tecnica da espessura minima de caldeira a partir dos dados levantados e da memoria de calculo correspondente.",
        method_example="Levantamento dos dados de entrada, consolidacao de premissas e elaboracao da memoria de calculo da espessura minima.",
        document_example="Memoria de calculo da espessura minima da caldeira.",
        point_example="Necessidade de complementar um dado de referencia do componente analisado para fechamento integral do registro.",
        recommendation_example="Versionar o calculo e manter vinculo com futuras campanhas de medicao e integridade da caldeira.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="nr13_calculo_espessura_minima_vaso_pressao",
        nome_exibicao="NR13 - Calculo de Espessura Minima de Vaso de Pressao",
        macro_categoria="NR13",
        kind="calculation",
        wave=3,
        objeto_exemplo="Calculo de espessura minima do vaso de pressao VP-204",
        localizacao_exemplo="Base tecnica da unidade de utilidades",
        scope_example="Determinacao tecnica da espessura minima de vaso de pressao com memoria de calculo e rastreabilidade dos dados de entrada.",
        method_example="Consolidacao dos dados tecnicos, definicao de premissas e elaboracao da memoria de calculo do vaso de pressao.",
        document_example="Memoria de calculo da espessura minima do vaso de pressao.",
        point_example="Necessidade de confirmar uma referencia secundaria para fechamento final do documento.",
        recommendation_example="Registrar a memoria como base de comparacao para futuras avaliacoes de integridade do vaso.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="nr13_calculo_espessura_minima_tubulacao",
        nome_exibicao="NR13 - Calculo de Espessura Minima de Tubulacao",
        macro_categoria="NR13",
        kind="calculation",
        wave=3,
        objeto_exemplo="Calculo de espessura minima da tubulacao TV-203",
        localizacao_exemplo="Rack norte da unidade de utilidades",
        scope_example="Determinacao tecnica da espessura minima de tubulacao abrangida pela NR13 com consolidacao dos dados e da memoria de calculo correspondente.",
        method_example="Levantamento de dados, consolidacao das premissas e memoria de calculo aplicada ao trecho de tubulacao analisado.",
        document_example="Memoria de calculo da espessura minima da tubulacao.",
        point_example="Necessidade de complementar um dado de referencia do trecho analisado para fechamento definitivo do calculo.",
        recommendation_example="Manter a memoria vinculada ao trecho identificado e atualiza-la quando houver alteracao relevante na linha.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="nr13_treinamento_operacao_caldeira",
        nome_exibicao="NR13 - Treinamento de Operacao de Caldeira",
        macro_categoria="NR13",
        kind="training",
        wave=4,
        objeto_exemplo="Turma de operacao de caldeira - abril de 2026",
        localizacao_exemplo="Sala de treinamento da unidade piloto",
        scope_example="Planejamento, execucao e registro do treinamento de operacao de caldeira para a equipe operacional.",
        method_example="Realizacao do treinamento com registro de turma, conteudo aplicado, evidencias de execucao e consolidacao final.",
        document_example="Lista de presenca, conteudo programatico e registro final do treinamento.",
        point_example="Necessidade de complementar a assinatura de um participante na lista final da turma.",
        recommendation_example="Manter o historico das turmas versionado e vinculado aos operadores habilitados para a atividade.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="nr13_treinamento_operacao_unidades_processo",
        nome_exibicao="NR13 - Treinamento de Operacao de Unidades de Processo",
        macro_categoria="NR13",
        kind="training",
        wave=4,
        objeto_exemplo="Turma de operacao de unidades de processo - abril de 2026",
        localizacao_exemplo="Sala de treinamento da unidade de processo",
        scope_example="Planejamento, execucao e registro do treinamento de operacao de unidades de processo para a equipe operacional.",
        method_example="Realizacao do treinamento com evidencias da execucao, consolidacao de conteudo e registros da turma.",
        document_example="Lista de presenca, conteudo programatico e registro final do treinamento.",
        point_example="Necessidade de consolidar a versao final de um material complementar utilizado na turma.",
        recommendation_example="Versionar o material aplicado e manter o historico das turmas vinculado aos participantes.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="end_medicao_espessura_ultrassom",
        nome_exibicao="END - Medicao de Espessura por Ultrassom",
        macro_categoria="END",
        kind="ndt",
        wave=5,
        objeto_exemplo="Campanha de medicao de espessura por ultrassom no vaso VP-204",
        localizacao_exemplo="Area de utilidades da unidade piloto",
        scope_example="Execucao e registro tecnico de medicao de espessura por ultrassom em ativo ou trecho contratado, com consolidacao dos pontos avaliados e dos resultados obtidos.",
        method_example="Aplicacao da tecnica de ultrassom nos pontos definidos, com registro de parametros, leituras e consolidacao dos resultados.",
        document_example="Mapa de pontos medidos e tabela consolidada das leituras.",
        point_example="Necessidade de repetir um ponto complementar para fechamento integral da campanha de medicao.",
        recommendation_example="Anexar o mapa de pontos ao historico do ativo e comparar com campanhas futuras quando aplicavel.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="end_ultrassom_junta_soldada",
        nome_exibicao="END - Ultrassom em Junta Soldada",
        macro_categoria="END",
        kind="ndt",
        wave=5,
        objeto_exemplo="Ultrassom em junta soldada JS-14",
        localizacao_exemplo="Trecho de manutencao industrial da unidade piloto",
        scope_example="Execucao e registro tecnico de ultrassom em junta soldada com consolidacao das indicacoes e do resultado do ensaio.",
        method_example="Aplicacao do ultrassom na junta definida, com registro dos parametros de ensaio e consolidacao das indicacoes observadas.",
        document_example="Registro do ensaio e consolidacao das indicacoes da junta avaliada.",
        point_example="Necessidade de complementar o registro de um trecho marginal para fechamento do relatorio.",
        recommendation_example="Manter a rastreabilidade da junta ensaiada e vincular o resultado ao pacote tecnico correspondente.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="end_liquido_penetrante",
        nome_exibicao="END - Liquido Penetrante",
        macro_categoria="END",
        kind="ndt",
        wave=5,
        objeto_exemplo="Ensaio por liquido penetrante no componente LP-07",
        localizacao_exemplo="Area de manutencao controlada da unidade piloto",
        scope_example="Execucao e registro tecnico de ensaio por liquido penetrante com consolidacao das indicacoes e rastreabilidade do componente ensaiado.",
        method_example="Aplicacao da tecnica de liquido penetrante no componente definido com registro das etapas, evidencias e indicacoes observadas.",
        document_example="Registro fotografico e consolidacao das indicacoes do ensaio por liquido penetrante.",
        point_example="Necessidade de registrar uma foto complementar de confirmacao de indicacao localizada.",
        recommendation_example="Vincular o resultado do ensaio ao historico do componente e ao pacote tecnico correspondente.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="end_particula_magnetica",
        nome_exibicao="END - Particula Magnetica",
        macro_categoria="END",
        kind="ndt",
        wave=5,
        objeto_exemplo="Ensaio por particula magnetica no componente PM-09",
        localizacao_exemplo="Area de manutencao controlada da unidade piloto",
        scope_example="Execucao e registro tecnico de ensaio por particula magnetica com consolidacao das indicacoes e rastreabilidade do componente ensaiado.",
        method_example="Aplicacao da tecnica de particula magnetica no componente definido com registro dos parametros, evidencias e indicacoes observadas.",
        document_example="Registro do ensaio por particula magnetica e consolidacao das indicacoes observadas.",
        point_example="Necessidade de reforcar o registro de uma indicacao secundaria para fechamento integral do documento.",
        recommendation_example="Anexar o relatorio ao historico do componente e manter a rastreabilidade da avaliacao executada.",
        status_example="conforme",
    ),
    PortfolioFamilySpec(
        family_key="end_visual_solda",
        nome_exibicao="END - Ensaio Visual de Solda",
        macro_categoria="END",
        kind="ndt",
        wave=5,
        objeto_exemplo="Ensaio visual de solda na junta VS-03",
        localizacao_exemplo="Area de manutencao e fabricacao da unidade piloto",
        scope_example="Execucao e registro tecnico de ensaio visual de solda com consolidacao das observacoes e do resultado do exame executado.",
        method_example="Inspecao visual da solda definida, com registro das observacoes, evidencias e consolidacao final do exame.",
        document_example="Registro fotografico e consolidacao das observacoes do ensaio visual de solda.",
        point_example="Necessidade de complementar a identificacao fotografica de um trecho final da junta avaliada.",
        recommendation_example="Manter o registro visual vinculado ao historico da junta ou do componente avaliado.",
        status_example="conforme",
    ),
]


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _objeto_referencia(disponivel: bool | None = None) -> dict[str, Any]:
    return {
        "disponivel": disponivel,
        "referencias": [],
        "referencias_texto": None,
        "descricao": None,
        "observacao": None,
    }


def _kind_defaults(kind: str) -> dict[str, Any]:
    try:
        return KIND_DEFAULTS[kind]
    except KeyError as exc:
        raise ValueError(f"Kind nao suportado: {kind}") from exc


def _build_required_slots(spec: PortfolioFamilySpec) -> list[dict[str, Any]]:
    kind_cfg = _kind_defaults(spec.kind)
    slots = [
        {
            "slot_id": "referencia_principal",
            "label": "Referencia principal",
            "accepted_types": ["foto", "documento"],
            "required": True,
            "min_items": 1,
            "binding_path": "identificacao.referencia_principal",
            "purpose": f"Vincular a referencia principal do objeto do servico {spec.family_key}.",
        },
        {
            "slot_id": "evidencia_execucao",
            "label": "Evidencia de execucao",
            "accepted_types": ["foto", "documento", "texto"],
            "required": True,
            "min_items": 1,
            "binding_path": "execucao_servico.evidencia_execucao",
            "purpose": "Registrar a execucao principal do servico com evidencia rastreavel.",
        },
        {
            "slot_id": "evidencia_principal",
            "label": "Evidencia principal",
            "accepted_types": ["foto", "documento", "texto"],
            "required": True,
            "min_items": 1,
            "binding_path": "evidencias_e_anexos.evidencia_principal",
            "purpose": "Consolidar a evidencia principal que sustenta a conclusao do servico.",
        },
    ]
    if int(kind_cfg["min_documentos"]) > 0:
        slots.append(
            {
                "slot_id": "documento_base",
                "label": "Documento base",
                "accepted_types": ["documento"],
                "required": True,
                "min_items": 1,
                "binding_path": "evidencias_e_anexos.documento_base",
                "purpose": "Vincular o documento base ou memoria principal do servico.",
            }
        )
    slots.append(
        {
            "slot_id": "conclusao_servico",
            "label": "Conclusao do servico",
            "accepted_types": ["texto"],
            "required": True,
            "min_items": 1,
            "binding_path": "conclusao.conclusao_tecnica",
            "purpose": "Registrar a conclusao tecnica estruturada para revisao.",
        }
    )
    return slots


def _build_optional_slots(spec: PortfolioFamilySpec) -> list[dict[str, Any]]:
    return [
        {
            "slot_id": "evidencia_complementar",
            "label": "Evidencia complementar",
            "accepted_types": ["foto", "documento", "texto"],
            "required": False,
            "min_items": 0,
            "binding_path": "evidencias_e_anexos.evidencia_complementar",
            "purpose": "Registrar evidencias complementares que ajudem a contextualizar o servico.",
        },
        {
            "slot_id": "documento_base",
            "label": "Documento base",
            "accepted_types": ["documento"],
            "required": False,
            "min_items": 0,
            "binding_path": "evidencias_e_anexos.documento_base",
            "purpose": "Vincular documentos de apoio quando disponiveis.",
        },
        {
            "slot_id": "registro_lacuna_ou_ponto",
            "label": "Registro de lacuna ou ponto de atencao",
            "accepted_types": ["foto", "documento", "texto"],
            "required": False,
            "min_items": 0,
            "binding_path": "nao_conformidades_ou_lacunas.evidencias",
            "purpose": "Registrar visualmente ou documentalmente os pontos de atencao do servico.",
        },
    ]


def _build_output_sections(spec: PortfolioFamilySpec) -> list[dict[str, Any]]:
    titles = _kind_defaults(spec.kind)["section_titles"]
    return [
        {
            "section_id": "identificacao",
            "title": titles["identificacao"],
            "required": True,
            "fields": [
                {
                    "field_id": "objeto_principal",
                    "label": "Objeto principal",
                    "type": "text",
                    "required": True,
                    "critical": True,
                    "binding_path": "identificacao.objeto_principal",
                    "source_hint": "Identificacao principal do servico, ativo, pacote ou turma.",
                },
                {
                    "field_id": "localizacao",
                    "label": "Localizacao",
                    "type": "text",
                    "required": True,
                    "critical": True,
                    "binding_path": "identificacao.localizacao",
                    "source_hint": "Referencia de localizacao do servico.",
                },
                {
                    "field_id": "referencia_principal",
                    "label": "Referencia principal",
                    "type": "document_ref",
                    "required": False,
                    "critical": False,
                    "binding_path": "identificacao.referencia_principal",
                    "source_hint": "Slot referencia_principal.",
                },
                {
                    "field_id": "codigo_interno",
                    "label": "Codigo interno",
                    "type": "text",
                    "required": False,
                    "critical": False,
                    "binding_path": "identificacao.codigo_interno",
                    "source_hint": "Codigo interno do servico quando existir.",
                },
            ],
        },
        {
            "section_id": "escopo_servico",
            "title": titles["escopo_servico"],
            "required": True,
            "fields": [
                {
                    "field_id": "tipo_entrega",
                    "label": "Tipo de entrega",
                    "type": "text",
                    "required": True,
                    "critical": False,
                    "binding_path": "escopo_servico.tipo_entrega",
                    "source_hint": "Natureza do servico contratado.",
                },
                {
                    "field_id": "modo_execucao",
                    "label": "Modo de execucao",
                    "type": "text",
                    "required": True,
                    "critical": False,
                    "binding_path": "escopo_servico.modo_execucao",
                    "source_hint": "Modo principal de execucao do servico.",
                },
                {
                    "field_id": "ativo_tipo",
                    "label": "Tipo de ativo ou escopo",
                    "type": "text",
                    "required": False,
                    "critical": False,
                    "binding_path": "escopo_servico.ativo_tipo",
                    "source_hint": "Tipo principal de ativo ou escopo do servico.",
                },
                {
                    "field_id": "resumo_escopo",
                    "label": "Resumo do escopo",
                    "type": "textarea",
                    "required": True,
                    "critical": True,
                    "binding_path": "escopo_servico.resumo_escopo",
                    "source_hint": "Sintese objetiva do escopo entregue.",
                },
            ],
        },
        {
            "section_id": "execucao_servico",
            "title": titles["execucao_servico"],
            "required": True,
            "fields": [
                {
                    "field_id": "metodo_aplicado",
                    "label": "Metodo aplicado",
                    "type": "textarea",
                    "required": True,
                    "critical": True,
                    "binding_path": "execucao_servico.metodo_aplicado",
                    "source_hint": "Como o servico foi executado.",
                },
                {
                    "field_id": "condicoes_observadas",
                    "label": "Condicoes observadas",
                    "type": "textarea",
                    "required": True,
                    "critical": True,
                    "binding_path": "execucao_servico.condicoes_observadas",
                    "source_hint": "Condicoes observadas durante a execucao.",
                },
                {
                    "field_id": "parametros_relevantes",
                    "label": "Parametros relevantes",
                    "type": "textarea",
                    "required": False,
                    "critical": False,
                    "binding_path": "execucao_servico.parametros_relevantes",
                    "source_hint": "Parametros, leituras ou premissas relevantes do servico.",
                },
                {
                    "field_id": "evidencia_execucao",
                    "label": "Evidencia de execucao",
                    "type": "image_slot",
                    "required": False,
                    "critical": False,
                    "binding_path": "execucao_servico.evidencia_execucao",
                    "source_hint": "Slot evidencia_execucao.",
                },
            ],
        },
        {
            "section_id": "evidencias_e_anexos",
            "title": titles["evidencias_e_anexos"],
            "required": True,
            "fields": [
                {
                    "field_id": "evidencia_principal",
                    "label": "Evidencia principal",
                    "type": "image_slot",
                    "required": False,
                    "critical": False,
                    "binding_path": "evidencias_e_anexos.evidencia_principal",
                    "source_hint": "Slot evidencia_principal.",
                },
                {
                    "field_id": "evidencia_complementar",
                    "label": "Evidencia complementar",
                    "type": "image_slot",
                    "required": False,
                    "critical": False,
                    "binding_path": "evidencias_e_anexos.evidencia_complementar",
                    "source_hint": "Slot evidencia_complementar.",
                },
                {
                    "field_id": "documento_base",
                    "label": "Documento base",
                    "type": "document_ref",
                    "required": False,
                    "critical": False,
                    "binding_path": "evidencias_e_anexos.documento_base",
                    "source_hint": "Slot documento_base.",
                },
            ],
        },
        {
            "section_id": "documentacao_e_registros",
            "title": titles["documentacao_e_registros"],
            "required": True,
            "fields": [
                {
                    "field_id": "documentos_disponiveis",
                    "label": "Documentos disponiveis",
                    "type": "textarea",
                    "required": True,
                    "critical": False,
                    "binding_path": "documentacao_e_registros.documentos_disponiveis",
                    "source_hint": "Registro textual dos documentos disponiveis.",
                },
                {
                    "field_id": "documentos_emitidos",
                    "label": "Documentos emitidos",
                    "type": "textarea",
                    "required": False,
                    "critical": False,
                    "binding_path": "documentacao_e_registros.documentos_emitidos",
                    "source_hint": "Pacote ou entregavel emitido pelo servico.",
                },
                {
                    "field_id": "observacoes_documentais",
                    "label": "Observacoes documentais",
                    "type": "textarea",
                    "required": False,
                    "critical": False,
                    "binding_path": "documentacao_e_registros.observacoes_documentais",
                    "source_hint": "Observacoes documentais complementares.",
                },
            ],
        },
        {
            "section_id": "nao_conformidades_ou_lacunas",
            "title": titles["nao_conformidades_ou_lacunas"],
            "required": True,
            "fields": [
                {
                    "field_id": "ha_pontos_de_atencao",
                    "label": "Ha pontos de atencao",
                    "type": "boolean",
                    "required": True,
                    "critical": False,
                    "binding_path": "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
                    "source_hint": "Registro do servico sobre a existencia de pontos de atencao.",
                },
                {
                    "field_id": "descricao",
                    "label": "Descricao",
                    "type": "textarea",
                    "required": True,
                    "critical": False,
                    "binding_path": "nao_conformidades_ou_lacunas.descricao",
                    "source_hint": "Descricao das lacunas, pontos de atencao ou ausencia declarada.",
                },
                {
                    "field_id": "evidencias",
                    "label": "Evidencias relacionadas",
                    "type": "image_slot",
                    "required": False,
                    "critical": False,
                    "binding_path": "nao_conformidades_ou_lacunas.evidencias",
                    "source_hint": "Slot registro_lacuna_ou_ponto.",
                },
            ],
        },
        {
            "section_id": "recomendacoes",
            "title": titles["recomendacoes"],
            "required": True,
            "fields": [
                {
                    "field_id": "texto",
                    "label": "Recomendacoes",
                    "type": "textarea",
                    "required": True,
                    "critical": False,
                    "binding_path": "recomendacoes.texto",
                    "source_hint": "Recomendacoes e proximos passos do servico.",
                },
            ],
        },
        {
            "section_id": "conclusao",
            "title": titles["conclusao"],
            "required": True,
            "fields": [
                {
                    "field_id": "status",
                    "label": "Status",
                    "type": "enum",
                    "required": True,
                    "critical": False,
                    "binding_path": "conclusao.status",
                    "source_hint": "Status final do servico.",
                },
                {
                    "field_id": "conclusao_tecnica",
                    "label": "Conclusao tecnica",
                    "type": "textarea",
                    "required": True,
                    "critical": True,
                    "binding_path": "conclusao.conclusao_tecnica",
                    "source_hint": "Conclusao tecnica do servico.",
                },
                {
                    "field_id": "justificativa",
                    "label": "Justificativa",
                    "type": "textarea",
                    "required": True,
                    "critical": False,
                    "binding_path": "conclusao.justificativa",
                    "source_hint": "Sintese das evidencias e fundamentos da conclusao.",
                },
            ],
        },
    ]


def build_family_schema(spec: PortfolioFamilySpec) -> dict[str, Any]:
    kind_cfg = _kind_defaults(spec.kind)
    template_code = spec.template_code or spec.family_key
    return {
        "family_key": spec.family_key,
        "nome_exibicao": spec.nome_exibicao,
        "macro_categoria": spec.macro_categoria,
        "descricao": spec.scope_example,
        "schema_version": 1,
        "scope": {
            "family_lock": True,
            "allowed_nrs": ["nr13"] if spec.macro_categoria != "END" else ["nr13", "end"],
            "allowed_contexts": [spec.family_key, spec.kind, f"wave_{spec.wave}"],
            "scope_signals": [
                f"servico_principal_identificado_como_{spec.family_key}",
                "escopo_registrado_de_forma_estruturada",
                "evidencias_vinculadas_ao_servico",
                "conclusao_tecnica_formalizada",
            ],
            "out_of_scope_examples": [
                "troca_silenciosa_do_tipo_de_servico",
                "mistura_de_entregaveis_sem_definicao_de_escopo",
                "documento_sem_rastreabilidade_de_evidencias",
            ],
            "review_required": [
                "quando_o_servico_principal_nao_estiver_claro",
                "quando_houver_escopo_misto_que_induza_troca_de_familia",
                "quando_o_caso_nao_tiver_rastreabilidade_documental_minima",
            ],
        },
        "evidence_policy": {
            "minimum_evidence": {
                "fotos": kind_cfg["min_fotos"],
                "documentos": kind_cfg["min_documentos"],
                "textos": kind_cfg["min_textos"],
            },
            "required_slots": _build_required_slots(spec),
            "optional_slots": _build_optional_slots(spec),
            "checklist_groups": [
                {
                    "group_id": "identificacao_e_escopo",
                    "title": "Identificacao e escopo",
                    "required": True,
                    "items": [
                        {"item_id": "objeto_registrado", "label": "Objeto principal registrado", "critical": True},
                        {"item_id": "localizacao_registrada", "label": "Localizacao registrada", "critical": True},
                        {"item_id": "escopo_registrado", "label": "Escopo registrado", "critical": True},
                    ],
                },
                {
                    "group_id": "execucao_e_evidencias",
                    "title": "Execucao e evidencias",
                    "required": True,
                    "items": [
                        {"item_id": "metodo_registrado", "label": "Metodo aplicado registrado", "critical": True},
                        {"item_id": "evidencia_principal_vinculada", "label": "Evidencia principal vinculada", "critical": True},
                        {"item_id": "documento_base_registrado_quando_existente", "label": "Documento base registrado quando existente", "critical": False},
                    ],
                },
                {
                    "group_id": "conclusao_e_pontos",
                    "title": "Conclusao e pontos de atencao",
                    "required": True,
                    "items": [
                        {"item_id": "conclusao_registrada", "label": "Conclusao tecnica registrada", "critical": True},
                        {"item_id": "pontos_de_atencao_registrados", "label": "Pontos de atencao registrados ou ausencia declarada", "critical": True},
                        {"item_id": "recomendacoes_registradas", "label": "Recomendacoes registradas", "critical": False},
                    ],
                },
            ],
            "review_required": [
                "quando_as_evidencias_minimas_nao_forem_atendidas",
                "quando_a_referencia_principal_estiver_ilegivel_sem_documento_equivalente",
                "quando_houver_duvida_sobre_qual_documento_base_ancora_o_servico",
            ],
        },
        "review_policy": {
            "requires_family_lock": True,
            "block_on_scope_mismatch": True,
            "block_on_missing_required_evidence": True,
            "block_on_critical_field_absent": True,
            "allow_override_with_reason": True,
            "allowed_override_cases": [
                "documento_opcional_ausente_com_justificativa_registrada",
                "evidencia_complementar_substituida_por_registro_textual_com_rastreabilidade",
                "limitacao_controlada_sem_impacto_na_conclusao_critica",
            ],
            "blocking_conditions": [
                "escopo_principal_divergente_da_familia",
                "troca_silenciosa_da_familia_principal",
                "ausencia_de_objeto_principal",
                "ausencia_de_localizacao",
                "ausencia_de_slot_obrigatorio",
                "ausencia_de_conclusao_tecnica",
            ],
            "non_blocking_conditions": [
                "documento_complementar_nao_disponivel",
                "evidencia_opcional_ausente_sem_impacto_critico",
                "lacuna_documental_secundaria_registrada",
            ],
            "preferred_pendencia_types": [
                "solicitar_foto",
                "solicitar_documento",
                "pedir_confirmacao",
                "apontar_inconsistencia",
                "corrigir_familia",
                "evidencia_insuficiente",
                "campo_critico_ausente",
                "revisao_conclusao",
                "aprovacao_com_ressalva",
            ],
            "review_required": [
                "qualquer_override_deve_ser_justificado_e_revisado_pela_mesa",
                "casos_com_inconsistencia_entre_evidencia_e_registro_textual_devem_ir_para_revisao",
                "casos_com_duvida_de_enquadramento_devem_ser_bloqueados_para_revisao",
            ],
        },
        "output_schema_seed": {
            "sections": _build_output_sections(spec),
            "conclusion_model": {
                "required_inputs": [
                    "identificacao.objeto_principal",
                    "identificacao.localizacao",
                    "escopo_servico.resumo_escopo",
                    "execucao_servico.metodo_aplicado",
                    "execucao_servico.condicoes_observadas",
                    "conclusao.conclusao_tecnica",
                ],
                "status_options": ["conforme", "nao_conforme", "ajuste", "pendente"],
                "notes": f"A conclusao da familia {spec.family_key} depende da identificacao, do escopo, do registro de execucao e da evidencia principal vinculada.",
            },
            "review_required": [
                "validar_os_bindings_definitivos_entre_slots_e_template",
                "confirmar_enums_fechados_do_status_final_do_servico",
            ],
        },
        "template_binding_hints": {
            "preferred_template_codes": [template_code, spec.family_key],
            "suggested_binding_paths": [
                "identificacao.objeto_principal",
                "identificacao.localizacao",
                "identificacao.referencia_principal",
                "escopo_servico.tipo_entrega",
                "escopo_servico.modo_execucao",
                "escopo_servico.resumo_escopo",
                "execucao_servico.metodo_aplicado",
                "execucao_servico.condicoes_observadas",
                "execucao_servico.evidencia_execucao",
                "evidencias_e_anexos.evidencia_principal",
                "evidencias_e_anexos.documento_base",
                "documentacao_e_registros.documentos_disponiveis",
                "documentacao_e_registros.documentos_emitidos",
                "nao_conformidades_ou_lacunas.descricao",
                "recomendacoes.texto",
                "conclusao.status",
                "conclusao.conclusao_tecnica",
            ],
            "expected_image_slots": [
                "referencia_principal",
                "evidencia_execucao",
                "evidencia_principal",
                "evidencia_complementar",
                "registro_lacuna_ou_ponto",
            ],
        },
        "notes": {
            "assumptions": [
                "A familia foi gerada a partir do portfolio real da empresa focada em NR13.",
                "O modelo usa contrato canonico de laudo_output e template_master compatível com o renderer atual.",
                "Detalhamento fino por cliente pode ser refinado sem quebrar o contrato base gerado.",
            ],
            "open_questions": [
                "Validar em operacao real se o servico exige campo tecnico adicional alem do seed generico.",
                "Confirmar se existe exigencia de documento ancora especifico para todos os casos desta familia.",
            ],
        },
    }


def build_laudo_output_seed(spec: PortfolioFamilySpec) -> dict[str, Any]:
    template_code = spec.template_code or spec.family_key
    return {
        "schema_type": "laudo_output",
        "schema_version": 1,
        "family_key": spec.family_key,
        "template_code": template_code,
        "tokens": dict(TOKENS_EXEMPLO),
        "case_context": {
            "laudo_id": None,
            "empresa_nome": None,
            "unidade_nome": None,
            "data_execucao": None,
            "data_emissao": None,
            "status_mesa": None,
            "wave_portfolio": spec.wave,
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
            "referencia_principal": _objeto_referencia(),
            "codigo_interno": None,
        },
        "escopo_servico": {
            "tipo_entrega": None,
            "modo_execucao": None,
            "ativo_tipo": None,
            "resumo_escopo": None,
        },
        "execucao_servico": {
            "metodo_aplicado": None,
            "condicoes_observadas": None,
            "parametros_relevantes": None,
            "evidencia_execucao": _objeto_referencia(),
        },
        "evidencias_e_anexos": {
            "evidencia_principal": _objeto_referencia(),
            "evidencia_complementar": _objeto_referencia(),
            "documento_base": _objeto_referencia(),
        },
        "documentacao_e_registros": {
            "documentos_disponiveis": None,
            "documentos_emitidos": None,
            "observacoes_documentais": None,
        },
        "nao_conformidades_ou_lacunas": {
            "ha_pontos_de_atencao": None,
            "ha_pontos_de_atencao_texto": None,
            "descricao": None,
            "evidencias": _objeto_referencia(),
        },
        "recomendacoes": {"texto": None},
        "conclusao": {
            "status": None,
            "conclusao_tecnica": None,
            "justificativa": None,
        },
    }


def build_laudo_output_exemplo(spec: PortfolioFamilySpec) -> dict[str, Any]:
    kind_cfg = _kind_defaults(spec.kind)
    payload = build_laudo_output_seed(spec)
    template_code = spec.template_code or spec.family_key
    payload["template_code"] = template_code
    payload["case_context"] = {
        "laudo_id": f"{spec.family_key.upper()}-2026-001",
        "empresa_nome": "Empresa Teste NR13",
        "unidade_nome": TOKENS_EXEMPLO["unidade_nome"],
        "data_execucao": "2026-04-08",
        "data_emissao": "2026-04-08",
        "status_mesa": "aprovado_com_ressalva",
        "wave_portfolio": spec.wave,
    }
    payload["mesa_review"] = {
        "status": "aprovado_com_ressalva",
        "family_lock": True,
        "scope_mismatch": False,
        "bloqueios": [],
        "bloqueios_texto": "Sem bloqueios pendentes para emissao.",
        "pendencias_resolvidas_texto": "Pendencias documentais secundarias foram registradas e tratadas pela Mesa.",
        "observacoes_mesa": f"Caso mantido em {spec.family_key} com rastreabilidade de escopo e evidencias.",
    }
    payload["resumo_executivo"] = (
        f"Foi executado o servico {spec.nome_exibicao.lower()} com registro estruturado do objeto principal, "
        f"evidencias vinculadas, documentacao de apoio e conclusao tecnica consolidada para a Mesa."
    )
    payload["identificacao"] = {
        "objeto_principal": spec.objeto_exemplo,
        "localizacao": spec.localizacao_exemplo,
        "referencia_principal": {
            "disponivel": True,
            "referencias": ["IMG_001", "DOC_001"],
            "referencias_texto": "IMG_001; DOC_001",
            "descricao": "Referencia principal do objeto identificada com apoio de evidencia visual e documento associado.",
            "observacao": "Rastreabilidade principal confirmada para o servico.",
        },
        "codigo_interno": f"{spec.family_key.upper()}-001",
    }
    payload["escopo_servico"] = {
        "tipo_entrega": kind_cfg["tipo_entrega"],
        "modo_execucao": kind_cfg["modo_execucao"],
        "ativo_tipo": spec.macro_categoria,
        "resumo_escopo": spec.scope_example,
    }
    payload["execucao_servico"] = {
        "metodo_aplicado": spec.method_example,
        "condicoes_observadas": "Servico executado dentro do escopo previsto, com registros suficientes para revisao da Mesa e consolidacao do documento final.",
        "parametros_relevantes": spec.document_example,
        "evidencia_execucao": {
            "disponivel": True,
            "referencias": ["IMG_010", "DOC_010"],
            "referencias_texto": "IMG_010; DOC_010",
            "descricao": "Evidencia da execucao principal do servico.",
            "observacao": "Registros principais consolidados.",
        },
    }
    payload["evidencias_e_anexos"] = {
        "evidencia_principal": {
            "disponivel": True,
            "referencias": ["IMG_020"],
            "referencias_texto": "IMG_020",
            "descricao": "Evidencia principal que suporta a conclusao tecnica.",
            "observacao": "Material principal vinculado ao caso.",
        },
        "evidencia_complementar": {
            "disponivel": True,
            "referencias": ["IMG_021"],
            "referencias_texto": "IMG_021",
            "descricao": "Evidencia complementar para contextualizacao do servico.",
            "observacao": "Registro complementar sem impacto critico.",
        },
        "documento_base": {
            "disponivel": True,
            "referencias": ["DOC_001"],
            "referencias_texto": spec.document_example,
            "descricao": "Documento base ou ancora principal do servico.",
            "observacao": "Documento vinculado ao pacote final.",
        },
    }
    payload["documentacao_e_registros"] = {
        "documentos_disponiveis": spec.document_example,
        "documentos_emitidos": f"Pacote tecnico de {spec.nome_exibicao.lower()} consolidado para entrega.",
        "observacoes_documentais": "Documentacao complementar registrada e vinculada ao caso.",
    }
    payload["nao_conformidades_ou_lacunas"] = {
        "ha_pontos_de_atencao": spec.status_example != "conforme",
        "ha_pontos_de_atencao_texto": "Sim" if spec.status_example != "conforme" else "Nao",
        "descricao": spec.point_example if spec.status_example != "conforme" else "Nao foram identificados pontos de atencao relevantes no fechamento deste servico.",
        "evidencias": {
            "disponivel": True,
            "referencias": ["IMG_030"],
            "referencias_texto": "IMG_030",
            "descricao": "Registro relacionado aos pontos de atencao ou a ausencia declarada deles.",
            "observacao": "Evidencia vinculada ao fechamento da analise.",
        },
    }
    payload["recomendacoes"] = {"texto": spec.recommendation_example}
    payload["conclusao"] = {
        "status": spec.status_example,
        "conclusao_tecnica": (
            f"O servico {spec.nome_exibicao.lower()} foi consolidado com rastreabilidade suficiente, "
            f"evidencias principais vinculadas e conclusao tecnica formalizada."
        ),
        "justificativa": (
            "A conclusao considera o escopo registrado, o metodo aplicado, a documentacao disponivel, "
            "a evidencia principal e os pontos de atencao ou sua ausencia declarada."
        ),
    }
    return payload


def _placeholder(mode: str, key: str) -> dict[str, Any]:
    return {
        "type": "placeholder",
        "attrs": {
            "mode": mode,
            "key": key,
            "raw": f"{mode}:{key}",
        },
    }


def _paragraph(parts: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "paragraph", "content": parts}


def _heading(level: int, text: str) -> dict[str, Any]:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [{"type": "text", "text": text}],
    }


def _text(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def build_template_master_seed(spec: PortfolioFamilySpec) -> dict[str, Any]:
    titles = _kind_defaults(spec.kind)["section_titles"]
    template_code = spec.template_code or spec.family_key
    doc_content = [
        _heading(1, spec.nome_exibicao),
        _paragraph([_text("Cliente: "), _placeholder("token", "cliente_nome"), _text(" | Unidade: "), _placeholder("token", "unidade_nome")]),
        _paragraph([_text("ID do laudo: "), _placeholder("json_path", "case_context.laudo_id"), _text(" | Data da execucao: "), _placeholder("json_path", "case_context.data_execucao")]),
        _heading(2, "1. Resumo Executivo"),
        _paragraph([_placeholder("json_path", "resumo_executivo")]),
        _heading(2, f"2. {titles['identificacao']}"),
        _paragraph([_text("Objeto principal: "), _placeholder("json_path", "identificacao.objeto_principal")]),
        _paragraph([_text("Localizacao: "), _placeholder("json_path", "identificacao.localizacao")]),
        _paragraph([_text("Referencia principal: "), _placeholder("json_path", "identificacao.referencia_principal.referencias_texto")]),
        _heading(2, f"3. {titles['escopo_servico']}"),
        _paragraph([_text("Tipo de entrega: "), _placeholder("json_path", "escopo_servico.tipo_entrega"), _text(" | Modo de execucao: "), _placeholder("json_path", "escopo_servico.modo_execucao")]),
        _paragraph([_placeholder("json_path", "escopo_servico.resumo_escopo")]),
        _heading(2, f"4. {titles['execucao_servico']}"),
        _paragraph([_text("Metodo aplicado: "), _placeholder("json_path", "execucao_servico.metodo_aplicado")]),
        _paragraph([_text("Condicoes observadas: "), _placeholder("json_path", "execucao_servico.condicoes_observadas")]),
        _paragraph([_text("Parametros relevantes: "), _placeholder("json_path", "execucao_servico.parametros_relevantes")]),
        _paragraph([_text("Evidencia de execucao: "), _placeholder("json_path", "execucao_servico.evidencia_execucao.referencias_texto")]),
        _heading(2, f"5. {titles['evidencias_e_anexos']}"),
        _paragraph([_text("Evidencia principal: "), _placeholder("json_path", "evidencias_e_anexos.evidencia_principal.referencias_texto")]),
        _paragraph([_text("Documento base: "), _placeholder("json_path", "evidencias_e_anexos.documento_base.referencias_texto")]),
        _heading(2, f"6. {titles['documentacao_e_registros']}"),
        _paragraph([_text("Documentos disponiveis: "), _placeholder("json_path", "documentacao_e_registros.documentos_disponiveis")]),
        _paragraph([_text("Documentos emitidos: "), _placeholder("json_path", "documentacao_e_registros.documentos_emitidos")]),
        _paragraph([_text("Observacoes documentais: "), _placeholder("json_path", "documentacao_e_registros.observacoes_documentais")]),
        _heading(2, f"7. {titles['nao_conformidades_ou_lacunas']}"),
        _paragraph([_text("Descricao: "), _placeholder("json_path", "nao_conformidades_ou_lacunas.descricao")]),
        _heading(2, f"8. {titles['recomendacoes']}"),
        _paragraph([_placeholder("json_path", "recomendacoes.texto")]),
        _heading(2, f"9. {titles['conclusao']}"),
        _paragraph([_text("Status: "), _placeholder("json_path", "conclusao.status")]),
        _paragraph([_text("Conclusao tecnica: "), _placeholder("json_path", "conclusao.conclusao_tecnica")]),
        _paragraph([_text("Justificativa: "), _placeholder("json_path", "conclusao.justificativa")]),
        _paragraph([_text("Status Mesa: "), _placeholder("json_path", "mesa_review.status"), _text(" | Family lock: "), _placeholder("json_path", "mesa_review.family_lock")]),
        _paragraph([_text("Bloqueios: "), _placeholder("json_path", "mesa_review.bloqueios_texto")]),
        _paragraph([_text("Pendencias tratadas: "), _placeholder("json_path", "mesa_review.pendencias_resolvidas_texto")]),
        _heading(2, "10. Assinatura Tecnica"),
        _paragraph([_text("Engenheiro responsavel: "), _placeholder("token", "engenheiro_responsavel")]),
        _paragraph([_text("CREA / ART: "), _placeholder("token", "crea_art")]),
        _paragraph([_text("Data de emissao: "), _placeholder("json_path", "case_context.data_emissao")]),
    ]
    return {
        "family_key": spec.family_key,
        "template_code": template_code,
        "modo_editor": "editor_rico",
        "observacoes": f"Seed inicial de template_master para {spec.nome_exibicao.lower()} usando o contrato canonico generico da carteira NR13 desta empresa.",
        "estilo_json": {
            "pagina": {
                "size": "A4",
                "orientation": "portrait",
                "margens_mm": {"top": 18, "right": 14, "bottom": 18, "left": 14},
            },
            "tipografia": {
                "font_family": "Inter, 'Segoe UI', Arial, sans-serif",
                "font_size_px": 12,
                "line_height": 1.45,
            },
            "cabecalho_texto": "Tariel.ia Portfolio NR13 | {{token:cliente_nome}} | {{token:unidade_nome}}",
            "rodape_texto": "Familia {{json_path:family_key}} | Revisao {{token:revisao_template}} | Emissao {{json_path:case_context.data_emissao}}",
            "marca_dagua": {"texto": "", "opacity": 0.08, "font_size_px": 72, "rotate_deg": -32},
        },
        "documento_editor_json": {
            "version": 1,
            "doc": {"type": "doc", "content": doc_content},
        },
    }


def build_summary_markdown(specs: list[PortfolioFamilySpec]) -> str:
    lines = [
        "# Portfolio Empresa NR13: Artefatos Canonicos",
        "",
        "Resumo dos artefatos gerados para a carteira completa da empresa focada em NR13.",
        "",
        "## Regra",
        "",
        "- cada familia abaixo possui `family_schema`, `laudo_output_seed`, `laudo_output_exemplo` e `template_master_seed`;",
        "- as familias existentes `nr13_inspecao_vaso_pressao` e `nr13_inspecao_caldeira` foram preservadas;",
        "- os artefatos desta lista foram gerados em lote a partir do portfolio comercial real da empresa.",
        "",
        "## Familias geradas neste lote",
        "",
        "| Wave | Family key | Categoria | Kind | Template code |",
        "| --- | --- | --- | --- | --- |",
    ]
    for spec in specs:
        lines.append(
            f"| {spec.wave} | `{spec.family_key}` | `{spec.macro_categoria}` | `{spec.kind}` | `{spec.template_code or spec.family_key}` |"
        )
    lines.extend(
        [
            "",
            "## Uso operacional",
            "",
            "1. publicar as familias no catalogo do Admin-CEO;",
            "2. bootstrapar os templates canônicos para a empresa piloto;",
            "3. liberar familia e template por empresa;",
            "4. ativar por codigo quando o servico entrar em operacao.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    FAMILY_SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    for spec in MISSING_PORTFOLIO_FAMILIES:
        _dump_json(FAMILY_SCHEMAS_DIR / f"{spec.family_key}.json", build_family_schema(spec))
        _dump_json(FAMILY_SCHEMAS_DIR / f"{spec.family_key}.laudo_output_seed.json", build_laudo_output_seed(spec))
        _dump_json(FAMILY_SCHEMAS_DIR / f"{spec.family_key}.laudo_output_exemplo.json", build_laudo_output_exemplo(spec))
        _dump_json(FAMILY_SCHEMAS_DIR / f"{spec.family_key}.template_master_seed.json", build_template_master_seed(spec))

    summary_path = WEB_DOCS_DIR / "portfolio_empresa_nr13_artefatos.md"
    summary_path.write_text(build_summary_markdown(MISSING_PORTFOLIO_FAMILIES), encoding="utf-8")

    print(
        json.dumps(
            {
                "familias_geradas": len(MISSING_PORTFOLIO_FAMILIES),
                "family_schemas_dir": str(FAMILY_SCHEMAS_DIR),
                "summary_doc": str(summary_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
