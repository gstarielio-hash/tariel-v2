# ==========================================
# TARIEL CONTROL TOWER — TEMPLATES_IA.PY
# Responsabilidade: Modelos estruturados (Pydantic)
# para forçar a IA a preencher checklists perfeitamente.
# ==========================================

from __future__ import annotations

from typing import Literal, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains.chat.normalization import normalizar_tipo_template

# Tipos de resposta padrão do Bombeiro
CondicaoEnum = Literal["C", "NC", "N/A"]
TipologiaInspecaoEnum = Literal["Residencial", "Comercial", "Industrial", "Outros", "Não informado"]
SimNaoEnum = Literal["Sim", "Não", "Não informado"]
StatusConclusaoNR35Enum = Literal["Aprovado", "Reprovado", "Pendente", "Não informado"]
TipoLinhaVidaNR35Enum = Literal["Vertical", "Horizontal", "Ponto de Ancoragem", "Não identificado"]

TITULOS_SECOES_CBMGO: dict[str, str] = {
    "seguranca_estrutural": "SEGURANCA ESTRUTURAL",
    "cmar": "CMAR - CONTROLE DE MATERIAL DE ACABAMENTO E REVESTIMENTO",
    "verificacao_documental": "VERIFICACAO DOCUMENTAL DAS INSTALACOES",
    "recomendacoes_gerais": "RECOMENDACOES GERAIS",
}

MAPA_VERIFICACOES_CBMGO: dict[str, dict[str, str]] = {
    "seguranca_estrutural": {
        "item_01_fissuras_trincas": "Avaliar fissuras diagonais em paredes/vigas, trincas horizontais e fissuras em cantos de portas e janelas.",
        "item_02_corrosao_concreto": "Verificar corrosao, descolamento do concreto, armadura exposta e flambagem de pilares/lajes.",
        "item_03_revestimento_teto": "Desprendimento de revestimento de fachadas/paredes, teto/forro.",
        "item_04_pisos": "Trincas/ranhuras em pisos, desprendimento/afundamento ou caimento irregular.",
        "item_05_vazamentos_subsolo": "Vazamentos pelas prumadas no subsolo/areas comuns.",
        "item_06_infiltracoes": "Infiltracoes cronicas que comprometem aderencia e corroem aco.",
        "item_07_esquadrias": "Esquadrias soltas, desalinhadas ou com mau funcionamento.",
        "item_08_ferragens": "Ferragens e metais avariados.",
        "item_09_geometria": "Irregularidades geometricas (esquadro/prumo/nivel) ou falhas de concretagem.",
        "item_10_deformacao": "Peca estrutural com deformacao excessiva.",
        "item_11_armaduras_expostas": "Armaduras expostas.",
        "item_12_recalques": "Recalques diferenciais, novas fissuras e inclinacoes nas edificacoes.",
    },
    "cmar": {
        "item_01_piso": "Material empregado no piso confere com memorial/projeto aprovado.",
        "item_02_paredes": "Material empregado nas paredes confere com memorial/projeto aprovado.",
        "item_03_teto": "Material empregado no teto/forro confere com memorial/projeto aprovado.",
        "item_04_cobertura": "Material empregado na cobertura confere com memorial/projeto aprovado.",
        "item_05_tratamento_retardante": "Existencia de material com funcao retardante/antichama/antipropagante.",
        "item_06_laudo_fabricante": "Existe laudo de conformidade do fabricante atestando tratamento.",
    },
    "verificacao_documental": {
        "item_01_plano_manutencao": "Ha plano de manutencao preditiva das instalacoes.",
        "item_02_coerencia_plano": "Plano coerente com fabricantes, normas e instrucoes tecnicas.",
        "item_03_adequacao_rotinas": "Adequacao de rotinas/frequencias considerando idade e uso das instalacoes.",
        "item_04_acesso_equipamentos": "Condicoes de acesso aos equipamentos para manutencao.",
        "item_05_seguranca_usuarios": "Condicoes de seguranca para usuarios durante a manutencao.",
        "item_06_documentos_pertinentes": "Documentos pertinentes a manutencao disponiveis.",
    },
    "recomendacoes_gerais": {
        "item_01_interdicao": "Situacoes de interdição parcial ou total da edificacao.",
        "item_02_mudanca_uso": "Mudancas significativas no uso que gerem deficiencias futuras.",
        "item_03_intervencao_imediata": "Instalacoes passivas com necessidade de intervencao imediata.",
    },
}

TITULOS_SECOES_NR35_LINHA_VIDA: dict[str, str] = {
    "informacoes_gerais": "IDENTIFICACAO E CONTEXTO DA VISTORIA",
    "objeto_inspecao": "OBJETO DA INSPECAO",
    "componentes_inspecionados": "COMPONENTES / ACESSORIOS INSPECIONADOS",
    "conclusao": "CONCLUSAO E ENCAMINHAMENTO",
}

MAPA_COMPONENTES_NR35_LINHA_VIDA: dict[str, str] = {
    "fixacao_dos_pontos": "Fixação dos pontos de ancoragem e da estrutura visível.",
    "condicao_cabo_aco": "Condição do cabo de aço da linha de vida.",
    "condicao_esticador": "Condição do esticador e do tensionamento visível.",
    "condicao_sapatilha": "Condição da sapatilha e da montagem do terminal.",
    "condicao_olhal": "Condição do olhal, conexão e deformações aparentes.",
    "condicao_grampos": "Condição dos grampos, aperto e integridade visível.",
}


class ItemChecklist(BaseModel):
    """Estrutura base para qualquer item de checklist do laudo."""

    condicao: CondicaoEnum = Field(description="Selecione 'C' (Conforme), 'NC' (Não Conforme) ou 'N/A' (Não se Aplica) com base no relato.")
    localizacao: Optional[str] = Field(
        default="",
        description="Localização do item avaliado (setor, ambiente, pavimento, equipamento).",
    )
    observacao: Optional[str] = Field(
        default="",
        description="Justificativa técnica curta para NC, pendência, ressalva ou evidência complementar.",
    )

    @field_validator("condicao", mode="before")
    @classmethod
    def _normalizar_condicao(cls, valor: object) -> object:
        texto = str(valor or "").strip().upper().replace(" ", "")
        if texto == "NA":
            return "N/A"
        return valor

    model_config = ConfigDict(extra="ignore")


class InformacoesGerais(BaseModel):
    """Metadados principais do checklist CMAR/CBMGO."""

    responsavel_pela_inspecao: str = Field(default="", description="Nome do inspetor responsável.")
    data_inspecao: str = Field(default="", description="Data da inspeção.")
    local_inspecao: str = Field(default="", description="Local da inspeção.")
    cnpj: str = Field(default="", description="CNPJ do local/cliente inspecionado.")
    numero_projeto_cbmgo: str = Field(default="", description="Número do projeto no CBM-GO, quando existir.")
    possui_cercon: SimNaoEnum = Field(default="Não informado", description="Indica existência de CERCON.")
    numero_cercon: str = Field(default="", description="Número do CERCON.")
    validade_cercon: str = Field(default="", description="Validade do CERCON.")
    responsavel_empresa_acompanhamento: str = Field(
        default="",
        description="Nome de quem acompanhou a inspeção na empresa.",
    )
    tipologia: TipologiaInspecaoEnum = Field(
        default="Não informado",
        description="Tipologia predominante da edificação/instalação.",
    )
    outros_tipologia: str = Field(default="", description="Preencher quando tipologia for 'Outros'.")

    model_config = ConfigDict(extra="ignore")


class SegurancaEstrutural(BaseModel):
    """Checklist de inspeção predial visual para condições estruturais (CBM-GO)."""

    item_01_fissuras_trincas: ItemChecklist
    item_02_corrosao_concreto: ItemChecklist
    item_03_revestimento_teto: ItemChecklist
    item_04_pisos: ItemChecklist
    item_05_vazamentos_subsolo: ItemChecklist
    item_06_infiltracoes: ItemChecklist
    item_07_esquadrias: ItemChecklist
    item_08_ferragens: ItemChecklist
    item_09_geometria: ItemChecklist
    item_10_deformacao: ItemChecklist
    item_11_armaduras_expostas: ItemChecklist
    item_12_recalques: ItemChecklist

    model_config = ConfigDict(extra="ignore")


class CMAR(BaseModel):
    """Controle de Material de Acabamento e Revestimento (NT 10/2022)."""

    item_01_piso: ItemChecklist
    item_02_paredes: ItemChecklist
    item_03_teto: ItemChecklist
    item_04_cobertura: ItemChecklist
    item_05_tratamento_retardante: ItemChecklist
    item_06_laudo_fabricante: ItemChecklist

    model_config = ConfigDict(extra="ignore")


class VerificacaoDocumental(BaseModel):
    """Verificação documental das instalações."""

    item_01_plano_manutencao: ItemChecklist
    item_02_coerencia_plano: ItemChecklist
    item_03_adequacao_rotinas: ItemChecklist
    item_04_acesso_equipamentos: ItemChecklist
    item_05_seguranca_usuarios: ItemChecklist
    item_06_documentos_pertinentes: ItemChecklist

    model_config = ConfigDict(extra="ignore")


class RecomendacoesGerais(BaseModel):
    """Recomendações e intervenções."""

    item_01_interdicao: ItemChecklist
    item_02_mudanca_uso: ItemChecklist
    item_03_intervencao_imediata: ItemChecklist
    outros: Optional[str] = Field(
        default="",
        description="Observações adicionais ou notas do inspetor.",
    )

    model_config = ConfigDict(extra="ignore")


class ColetaAssinaturas(BaseModel):
    """Coleta de assinaturas da inspeção."""

    responsavel_pela_inspecao: str = Field(default="", description="Nome do responsável pela inspeção.")
    assinatura_responsavel: str = Field(default="", description="Assinatura do responsável pela inspeção.")
    responsavel_empresa_acompanhamento: str = Field(
        default="",
        description="Nome do responsável da empresa que acompanhou a inspeção.",
    )
    assinatura_empresa: str = Field(default="", description="Assinatura do responsável da empresa.")

    model_config = ConfigDict(extra="ignore")


class RelatorioCBMGO(BaseModel):
    """Modelo raiz que engloba o checklist CMAR/CBMGO completo."""

    informacoes_gerais: InformacoesGerais = Field(default_factory=InformacoesGerais)
    seguranca_estrutural: SegurancaEstrutural
    cmar: CMAR
    trrf_observacoes: str = Field(
        default="",
        description="Síntese técnica do TRRF e referências normativas aplicadas.",
    )
    verificacao_documental: VerificacaoDocumental
    recomendacoes_gerais: RecomendacoesGerais
    coleta_assinaturas: ColetaAssinaturas = Field(default_factory=ColetaAssinaturas)
    resumo_executivo: str = Field(description=("Um parágrafo de resumo destacando principais achados, criticidades e orientação para validação de engenharia."))

    model_config = ConfigDict(extra="ignore")


class InformacoesGeraisNR35LinhaVida(BaseModel):
    """Metadados principais do laudo NR35 de linha de vida."""

    unidade: str = Field(default="", description="Unidade/filial da inspeção.")
    local: str = Field(default="", description="Cidade/UF ou local resumido da inspeção.")
    contratante: str = Field(default="", description="Empresa contratante.")
    contratada: str = Field(default="", description="Empresa executora da inspeção.")
    engenheiro_responsavel: str = Field(default="", description="Nome do responsável técnico.")
    inspetor_lider: str = Field(default="", description="Nome do inspetor líder em campo.")
    numero_laudo_fabricante: str = Field(default="", description="Número de identificação do fabricante.")
    numero_laudo_inspecao: str = Field(default="", description="Número do laudo da inspeção periódica.")
    art_numero: str = Field(default="", description="Número da ART vinculada.")
    data_vistoria: str = Field(default="", description="Data da vistoria em campo.")

    model_config = ConfigDict(extra="ignore")


class ObjetoInspecaoNR35LinhaVida(BaseModel):
    """Descrição do ativo e do escopo da inspeção NR35."""

    identificacao_linha_vida: str = Field(
        default="",
        description="Código/tag e descrição do ativo ou linha de vida inspecionada.",
    )
    tipo_linha_vida: TipoLinhaVidaNR35Enum = Field(
        default="Não identificado",
        description="Classifique o ativo principal como Vertical, Horizontal ou Ponto de Ancoragem.",
    )
    escopo_inspecao: str = Field(
        default="",
        description="Resumo técnico curto do objeto da inspeção e do ponto vistoriado.",
    )

    model_config = ConfigDict(extra="ignore")


class ComponentesInspecionadosNR35LinhaVida(BaseModel):
    """Checklist dos componentes principais da linha de vida."""

    fixacao_dos_pontos: ItemChecklist
    condicao_cabo_aco: ItemChecklist
    condicao_esticador: ItemChecklist
    condicao_sapatilha: ItemChecklist
    condicao_olhal: ItemChecklist
    condicao_grampos: ItemChecklist

    model_config = ConfigDict(extra="ignore")


class RegistroFotograficoNR35LinhaVida(BaseModel):
    """Registro fotográfico associado ao laudo."""

    titulo: str = Field(default="", description="Título curto da foto, ex: Vista geral ou Ponto superior.")
    legenda: str = Field(default="", description="Legenda técnica curta da evidência.")
    referencia_anexo: str = Field(
        default="",
        description="Nome do arquivo, id do anexo ou referência equivalente da foto usada.",
    )

    model_config = ConfigDict(extra="ignore")


class ConclusaoNR35LinhaVida(BaseModel):
    """Conclusão final do laudo NR35."""

    status: StatusConclusaoNR35Enum = Field(
        default="Não informado",
        description="Conclusão final: Aprovado, Reprovado ou Pendente.",
    )
    proxima_inspecao_periodica: str = Field(
        default="",
        description="Data ou mês previsto para a próxima inspeção periódica.",
    )
    observacoes: str = Field(
        default="",
        description="Observações finais e justificativa técnica da conclusão.",
    )

    model_config = ConfigDict(extra="ignore")


class RelatorioNR35LinhaVida(BaseModel):
    """Modelo estruturado do laudo NR35 de inspeção periódica de linha de vida."""

    informacoes_gerais: InformacoesGeraisNR35LinhaVida = Field(
        default_factory=InformacoesGeraisNR35LinhaVida
    )
    objeto_inspecao: ObjetoInspecaoNR35LinhaVida = Field(
        default_factory=ObjetoInspecaoNR35LinhaVida
    )
    componentes_inspecionados: ComponentesInspecionadosNR35LinhaVida
    registros_fotograficos: list[RegistroFotograficoNR35LinhaVida] = Field(
        default_factory=list,
        description="Lista ordenada de evidências fotográficas com legenda curta.",
    )
    conclusao: ConclusaoNR35LinhaVida = Field(
        default_factory=ConclusaoNR35LinhaVida
    )
    resumo_executivo: str = Field(
        description=(
            "Parágrafo curto consolidando o estado da linha de vida, os principais achados "
            "e a justificativa da conclusão."
        )
    )

    model_config = ConfigDict(extra="ignore")


class ReferenciaCatalogada(BaseModel):
    """Referência textual, fotográfica ou documental ligada ao caso."""

    disponivel: bool | None = Field(
        default=None,
        description="Indica se a referência foi apresentada ou vinculada ao caso.",
    )
    referencias_texto: str = Field(
        default="",
        description="Resumo curto dos anexos, fotos, tags ou documentos associados.",
    )
    descricao: str = Field(
        default="",
        description="Descrição técnica curta da evidência ou referência vinculada.",
    )
    observacao: str = Field(
        default="",
        description="Observação complementar quando houver limitação, lacuna ou ressalva.",
    )

    model_config = ConfigDict(extra="ignore")


class IdentificacaoCatalogada(BaseModel):
    objeto_principal: str = Field(default="", description="Ativo, sistema ou documento principal avaliado.")
    localizacao: str = Field(default="", description="Localização resumida do ativo ou frente inspecionada.")
    codigo_interno: str = Field(default="", description="Código, tag ou identificação interna do objeto.")
    referencia_principal: ReferenciaCatalogada = Field(default_factory=ReferenciaCatalogada)

    model_config = ConfigDict(extra="ignore")


class EscopoServicoCatalogado(BaseModel):
    tipo_entrega: str = Field(default="", description="Tipo de entrega técnica prevista para o caso.")
    modo_execucao: str = Field(default="", description="Modo de execução, como in loco, documental ou híbrido.")
    ativo_tipo: str = Field(default="", description="Classificação resumida do ativo, sistema ou documento.")
    resumo_escopo: str = Field(default="", description="Escopo técnico curto do serviço executado.")

    model_config = ConfigDict(extra="ignore")


class ExecucaoServicoCatalogado(BaseModel):
    metodo_aplicado: str = Field(default="", description="Método, procedimento ou roteiro técnico adotado.")
    condicoes_observadas: str = Field(default="", description="Condições relevantes encontradas durante a execução.")
    parametros_relevantes: str = Field(default="", description="Parâmetros, ajustes, medições ou critérios relevantes.")
    evidencia_execucao: ReferenciaCatalogada = Field(default_factory=ReferenciaCatalogada)

    model_config = ConfigDict(extra="ignore")


class EvidenciasCatalogadas(BaseModel):
    evidencia_principal: ReferenciaCatalogada = Field(default_factory=ReferenciaCatalogada)
    evidencia_complementar: ReferenciaCatalogada = Field(default_factory=ReferenciaCatalogada)
    documento_base: ReferenciaCatalogada = Field(default_factory=ReferenciaCatalogada)

    model_config = ConfigDict(extra="ignore")


class ProcedimentosControleCatalogado(BaseModel):
    fontes_de_energia: str = Field(default="", description="Fontes de energia perigosa identificadas no escopo.")
    pontos_de_bloqueio: str = Field(default="", description="Pontos de isolamento e bloqueio aplicados.")
    dispositivos_e_sinalizacao: str = Field(default="", description="Dispositivos de bloqueio, etiquetas e sinalização empregados.")
    verificacao_energia_zero: str = Field(default="", description="Descrição da confirmação de condição segura ou energia zero.")

    model_config = ConfigDict(extra="ignore")


class SistemaSpdaCatalogado(BaseModel):
    captacao: str = Field(default="", description="Estado do subsistema de captação observado em campo.")
    descidas: str = Field(default="", description="Condição das descidas, conexões e continuidade aparente.")
    aterramento_e_equipotencializacao: str = Field(default="", description="Condição do aterramento e da equipotencialização.")
    medicoes_ou_testes: str = Field(default="", description="Resultados resumidos de medições, continuidade ou resistência quando existentes.")

    model_config = ConfigDict(extra="ignore")


class EquipamentosCalibradosCatalogado(BaseModel):
    instrumentos_ou_componentes: str = Field(default="", description="Lista resumida de válvulas, manômetros ou instrumentos calibrados.")
    parametros_ajuste: str = Field(default="", description="Faixas, set points ou parâmetros de calibração aplicados.")
    resultado_da_calibracao: str = Field(default="", description="Resultado técnico da calibração e condição final dos instrumentos.")
    certificados_emitidos: str = Field(default="", description="Certificados, tags ou registros emitidos após a calibração.")

    model_config = ConfigDict(extra="ignore")


class ParametrosProjetoCatalogado(BaseModel):
    premissas_de_uso: str = Field(default="", description="Premissas operacionais consideradas no projeto.")
    layout_ou_arranjo: str = Field(default="", description="Layout, arranjo ou trechos abrangidos pela solução.")
    memoria_de_calculo: str = Field(default="", description="Memória de cálculo, critérios e cargas adotadas.")
    art_e_documentos: str = Field(default="", description="ART, desenhos, memoriais ou outros documentos associados.")

    model_config = ConfigDict(extra="ignore")


class ExecucaoMontagemCatalogada(BaseModel):
    componentes_instalados: str = Field(default="", description="Componentes ou módulos instalados na etapa de montagem.")
    fixacoes_e_suportes: str = Field(default="", description="Situação de fixações, suportes e interfaces estruturais.")
    alinhamento_ou_tensionamento: str = Field(default="", description="Ajustes de alinhamento, nivelamento ou tensionamento realizados.")
    liberacao_para_uso: str = Field(default="", description="Condição de liberação, restrição ou pendência após a montagem.")

    model_config = ConfigDict(extra="ignore")


class DocumentacaoRegistrosCatalogados(BaseModel):
    documentos_disponiveis: str = Field(default="", description="Principais documentos apresentados ou vinculados ao caso.")
    documentos_emitidos: str = Field(default="", description="Documentos emitidos, atualizados ou consolidados ao final do serviço.")
    observacoes_documentais: str = Field(default="", description="Pendências, lacunas ou observações documentais relevantes.")

    model_config = ConfigDict(extra="ignore")


class NaoConformidadesCatalogadas(BaseModel):
    ha_pontos_de_atencao_texto: SimNaoEnum = Field(
        default="Não informado",
        description="Indique se existem não conformidades, lacunas ou pontos de atenção relevantes.",
    )
    descricao: str = Field(default="", description="Descrição técnica das não conformidades ou lacunas encontradas.")
    evidencias: ReferenciaCatalogada = Field(default_factory=ReferenciaCatalogada)

    model_config = ConfigDict(extra="ignore")


class RecomendacoesCatalogadas(BaseModel):
    texto: str = Field(default="", description="Recomendações técnicas, ações corretivas ou encaminhamentos do caso.")

    model_config = ConfigDict(extra="ignore")


class ConclusaoCatalogada(BaseModel):
    status: str = Field(default="", description="Status técnico final resumido do serviço ou do ativo avaliado.")
    conclusao_tecnica: str = Field(default="", description="Síntese conclusiva do caso para revisão ou emissão.")
    justificativa: str = Field(default="", description="Justificativa técnica da conclusão adotada.")

    model_config = ConfigDict(extra="ignore")


class RelatorioTecnicoCatalogado(BaseModel):
    """Estrutura genérica para famílias catalogadas do chat guiado."""

    resumo_executivo: str = Field(
        default="",
        description="Parágrafo curto consolidando escopo, principais achados e condição final do caso.",
    )
    identificacao: IdentificacaoCatalogada = Field(default_factory=IdentificacaoCatalogada)
    escopo_servico: EscopoServicoCatalogado = Field(default_factory=EscopoServicoCatalogado)
    execucao_servico: ExecucaoServicoCatalogado = Field(default_factory=ExecucaoServicoCatalogado)
    evidencias_e_anexos: EvidenciasCatalogadas = Field(default_factory=EvidenciasCatalogadas)
    procedimentos_de_controle: ProcedimentosControleCatalogado = Field(default_factory=ProcedimentosControleCatalogado)
    sistema_spda: SistemaSpdaCatalogado = Field(default_factory=SistemaSpdaCatalogado)
    equipamentos_calibrados: EquipamentosCalibradosCatalogado = Field(default_factory=EquipamentosCalibradosCatalogado)
    parametros_de_projeto: ParametrosProjetoCatalogado = Field(default_factory=ParametrosProjetoCatalogado)
    execucao_montagem: ExecucaoMontagemCatalogada = Field(default_factory=ExecucaoMontagemCatalogada)
    documentacao_e_registros: DocumentacaoRegistrosCatalogados = Field(default_factory=DocumentacaoRegistrosCatalogados)
    nao_conformidades_ou_lacunas: NaoConformidadesCatalogadas = Field(default_factory=NaoConformidadesCatalogadas)
    recomendacoes: RecomendacoesCatalogadas = Field(default_factory=RecomendacoesCatalogadas)
    conclusao: ConclusaoCatalogada = Field(default_factory=ConclusaoCatalogada)

    model_config = ConfigDict(extra="ignore")


_SCHEMAS_TEMPLATE_IA: dict[str, Type[BaseModel]] = {
    "cbmgo": RelatorioCBMGO,
    "loto": RelatorioTecnicoCatalogado,
    "nr11_movimentacao": RelatorioTecnicoCatalogado,
    "nr12maquinas": RelatorioTecnicoCatalogado,
    "nr13": RelatorioTecnicoCatalogado,
    "nr13_calibracao": RelatorioTecnicoCatalogado,
    "nr13_teste_hidrostatico": RelatorioTecnicoCatalogado,
    "nr13_ultrassom": RelatorioTecnicoCatalogado,
    "nr20_instalacoes": RelatorioTecnicoCatalogado,
    "nr33_espaco_confinado": RelatorioTecnicoCatalogado,
    "nr35_linha_vida": RelatorioNR35LinhaVida,
    "nr35_montagem": RelatorioTecnicoCatalogado,
    "nr35_ponto_ancoragem": RelatorioTecnicoCatalogado,
    "nr35_projeto": RelatorioTecnicoCatalogado,
    "pie": RelatorioTecnicoCatalogado,
    "rti": RelatorioTecnicoCatalogado,
    "spda": RelatorioTecnicoCatalogado,
}


def obter_schema_template_ia(tipo_template: str | None) -> Type[BaseModel] | None:
    tipo_normalizado = normalizar_tipo_template(str(tipo_template or ""))
    return _SCHEMAS_TEMPLATE_IA.get(tipo_normalizado)
