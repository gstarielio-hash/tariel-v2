import type {
  MobileGuidedInspectionDraftPayload,
  MobileGuidedInspectionMessageContextPayload,
} from "../../types/mobile";

export type GuidedInspectionTemplateKey =
  | "padrao"
  | "avcb"
  | "cbmgo"
  | "loto"
  | "nr11_movimentacao"
  | "nr12maquinas"
  | "nr13"
  | "nr13_calibracao"
  | "nr13_teste_hidrostatico"
  | "nr13_ultrassom"
  | "nr20_instalacoes"
  | "nr33_espaco_confinado"
  | "nr35_linha_vida"
  | "nr35_montagem"
  | "nr35_ponto_ancoragem"
  | "nr35_projeto"
  | "pie"
  | "rti"
  | "spda";

export interface GuidedInspectionTemplateOption {
  key: GuidedInspectionTemplateKey;
  label: string;
}

export interface GuidedInspectionChecklistItem {
  id: string;
  title: string;
  prompt: string;
  evidenceHint: string;
}

export interface GuidedInspectionDraft {
  templateKey: GuidedInspectionTemplateKey;
  templateLabel: string;
  startedAt: string;
  currentStepIndex: number;
  completedStepIds: string[];
  checklist: GuidedInspectionChecklistItem[];
  evidenceBundleKind: "case_thread";
  evidenceRefs: GuidedInspectionEvidenceRef[];
  mesaHandoff: GuidedInspectionMesaHandoff | null;
}

export interface GuidedInspectionEvidenceRef {
  messageId: number;
  stepId: string;
  stepTitle: string;
  capturedAt: string;
  evidenceKind: "chat_message";
  attachmentKind: "none" | "image" | "document" | "mixed";
}

export interface GuidedInspectionMesaHandoff {
  required: boolean;
  reviewMode: string;
  reasonCode: string;
  recordedAt: string;
  stepId: string;
  stepTitle: string;
}

export interface GuidedInspectionProgress {
  completedCount: number;
  currentItem: GuidedInspectionChecklistItem | null;
  isComplete: boolean;
  remainingCount: number;
  totalCount: number;
}

function item(
  id: string,
  title: string,
  prompt: string,
  evidenceHint: string,
): GuidedInspectionChecklistItem {
  return {
    evidenceHint,
    id,
    prompt,
    title,
  };
}

const GUIDED_INSPECTION_TEMPLATES: Record<
  GuidedInspectionTemplateKey,
  {
    checklist: GuidedInspectionChecklistItem[];
    label: string;
  }
> = {
  padrao: {
    label: "Inspecao Geral",
    checklist: [
      item(
        "identificacao_ativo",
        "Identificacao do ativo e da area",
        "registre o ativo, setor, local e o motivo tecnico da coleta",
        "nome do ativo, area inspecionada, tag ou referencia principal",
      ),
      item(
        "contexto_operacao",
        "Contexto da atividade",
        "descreva o contexto operacional, quem acompanhou a vistoria e a condicao observada no momento da inspecao",
        "responsaveis, data da coleta e contexto resumido da operacao",
      ),
      item(
        "achado_principal",
        "Achado principal e risco",
        "explique o principal achado tecnico, a ausencia de nao conformidade relevante ou o risco predominante",
        "achado principal, risco associado e impacto resumido",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos com legenda curta cobrindo vista geral e detalhe do ponto mais relevante",
        "vista geral, detalhe critico e legenda objetiva",
      ),
      item(
        "conclusao",
        "Conclusao e proximo passo",
        "conclua a coleta com status preliminar, pendencias e proximo encaminhamento do caso",
        "status preliminar, pendencias e observacoes finais",
      ),
    ],
  },
  avcb: {
    label: "AVCB Projeto Bombeiro",
    checklist: [
      item(
        "identificacao_edificacao",
        "Identificacao da edificacao",
        "registre a edificacao, ocupacao, area avaliada e referencias basicas do projeto",
        "nome da edificacao, ocupacao e area vistoriada",
      ),
      item(
        "contexto_ocupacao",
        "Contexto de uso e abandono",
        "confirme tipo de uso, fluxo esperado de pessoas e qualquer restricao observada para abandono",
        "ocupacao, publico e restricoes operacionais relevantes",
      ),
      item(
        "rotas_sinalizacao",
        "Rotas de fuga e sinalizacao",
        "avalie circulacao, saídas, sinalizacao e condicoes de abandono seguro",
        "saidas, rotas, placas e condicoes de circulacao",
      ),
      item(
        "combate_incendio",
        "Meios de combate e protecao",
        "registre extintores, hidrantes, alarme, iluminacao e outros sistemas de protecao contra incendio",
        "equipamentos de combate, alarme e iluminacao de emergencia",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos panoramicas e de detalhe das rotas, sinalizacao e meios de combate",
        "vista geral, rota principal, sinalizacao e equipamento relevante",
      ),
      item(
        "conclusao",
        "Conclusao e pendencias",
        "sintetize conformidade geral, pendencias e necessidade de ajuste antes da emissao",
        "status tecnico, pendencias e observacoes finais",
      ),
    ],
  },
  cbmgo: {
    label: "CBM-GO Vistoria Bombeiro",
    checklist: [
      item(
        "informacoes_gerais",
        "Informacoes gerais da vistoria",
        "registre responsavel pela inspecao, local, tipologia, data e acompanhamentos do cliente",
        "responsavel, local, tipologia, data e acompanhamento",
      ),
      item(
        "seguranca_estrutural",
        "Seguranca estrutural",
        "consolide fissuras, corrosao, desprendimentos, recalques e outros achados estruturais relevantes",
        "principais achados estruturais e localizacao resumida",
      ),
      item(
        "cmar",
        "CMAR e materiais de acabamento",
        "avalie piso, paredes, teto, cobertura e existencia de material retardante ou laudo do fabricante",
        "materiais empregados e eventuais divergencias do memorial",
      ),
      item(
        "verificacao_documental",
        "Verificacao documental",
        "relacione plano de manutencao, documentos disponiveis, coerencia do plano e condicoes de acesso para manutencao",
        "documentos conferidos e principais lacunas",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos de achados estruturais, circulacao e evidencias documentais principais",
        "vista geral, detalhe do achado e apoio documental fotografado",
      ),
      item(
        "conclusao",
        "Conclusao e formulario estruturado",
        "feche com recomendacoes, necessidade de intervencao e confirme se o formulario estruturado esta consistente",
        "resumo executivo, recomendacoes e prontidao do formulario",
      ),
    ],
  },
  loto: {
    label: "NR10 LOTO",
    checklist: [
      item(
        "identificacao_processo",
        "Identificacao do processo e das energias",
        "registre ativo, processo, setor e as fontes de energia perigosa envolvidas no bloqueio",
        "ativo, setor, energias perigosas e referencia principal",
      ),
      item(
        "escopo_bloqueio",
        "Escopo de bloqueio e intervencao",
        "descreva a atividade, o motivo da intervencao e quem autorizou ou acompanhou o bloqueio",
        "atividade, responsaveis e motivo do bloqueio",
      ),
      item(
        "pontos_isolamento",
        "Pontos de isolamento",
        "identifique disjuntores, valvulas, chaves, linhas e demais pontos que exigem isolamento antes da intervencao",
        "pontos de isolamento e ordem de bloqueio",
      ),
      item(
        "dispositivos_sinalizacao",
        "Dispositivos de bloqueio e sinalizacao",
        "registre cadeados, etiquetas, travas, caixas de bloqueio e qualquer ausencia ou improviso observado",
        "cadeados, etiquetas, travas e lacunas de sinalizacao",
      ),
      item(
        "energia_residual",
        "Energia residual e teste de zero",
        "confirme descarte de energia residual, tentativa de partida e criterio usado para liberar a atividade",
        "teste de zero energia, energia residual e validacao final",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos do ponto bloqueado, da etiqueta, do dispositivo aplicado e da condicao segura para intervencao",
        "bloqueio aplicado, etiqueta, ponto isolado e detalhe critico",
      ),
      item(
        "conclusao",
        "Conclusao e liberacao",
        "registre status do bloqueio, pendencias, liberacao ou necessidade de reforco antes do retorno da energia",
        "status do bloqueio, pendencias e proximo passo",
      ),
    ],
  },
  nr11_movimentacao: {
    label: "NR11 Movimentacao e Armazenagem",
    checklist: [
      item(
        "identificacao_operacao",
        "Identificacao da operacao",
        "registre unidade, setor, equipamento principal, carga movimentada e contexto basico da operacao",
        "equipamento, carga, setor e referencia operacional",
      ),
      item(
        "levantamento_campo",
        "Levantamento em campo",
        "descreva fluxo, area percorrida, condicoes de piso, armazenamento e interfaces com pedestres ou outras maquinas",
        "layout, fluxo da operacao e condicoes do ambiente",
      ),
      item(
        "diagnostico_nr",
        "Diagnostico dos itens da NR",
        "consolide os requisitos da NR11 aplicaveis, o que esta conforme e as lacunas tecnicas principais",
        "itens aplicaveis, conformidades e nao conformidades",
      ),
      item(
        "dispositivos_seguranca",
        "Dispositivos de seguranca",
        "avalie freios, buzinas, alarmes, limitadores, protecoes, sinalizadores e demais dispositivos de seguranca",
        "dispositivos verificados e condicao observada",
      ),
      item(
        "seguranca_eletrica",
        "Seguranca eletrica dos dispositivos",
        "documente comandos, botoeiras, quadros, cabos, aterramento e integridade eletrica dos sistemas associados",
        "comandos, cabos, quadros e riscos eletricos",
      ),
      item(
        "zonas_risco",
        "Zonas de risco",
        "identifique pontos de esmagamento, raio de giro, cruzamentos, corredores de empilhadeiras e areas segregadas",
        "zonas de risco, interferencias e sinalizacao da area",
      ),
      item(
        "documentacao_art",
        "Documentacao e ART",
        "registre manuais, planos, treinamentos, manutencoes, certificacoes e a necessidade de ART quando aplicavel",
        "documentos conferidos, lacunas e ART vinculada",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe vista geral da operacao, pontos criticos, dispositivos e evidencias documentais relevantes",
        "vista geral, ponto critico, dispositivo e apoio documental",
      ),
      item(
        "conclusao",
        "Conclusao e recomendacoes",
        "sintetize o diagnostico da NR11, criticidade dos desvios e o encaminhamento tecnico recomendado",
        "status tecnico, criticidade e recomendacoes finais",
      ),
    ],
  },
  nr12maquinas: {
    label: "NR12 Maquinas e Equipamentos",
    checklist: [
      item(
        "identificacao_maquina",
        "Identificacao da maquina",
        "registre maquina, setor, fabricante, tag e contexto basico de uso",
        "maquina, setor, tag e referencia do equipamento",
      ),
      item(
        "levantamento_campo",
        "Levantamento em campo",
        "descreva a atividade, modo de operacao, interfaces da maquina e quem acompanhou a vistoria",
        "atividade observada, operacao e responsaveis",
      ),
      item(
        "diagnostico_nr",
        "Diagnostico dos itens da NR",
        "consolide os requisitos da NR12 aplicaveis, as conformidades e os desvios tecnicos observados",
        "itens aplicaveis, conformidades e nao conformidades",
      ),
      item(
        "dispositivos_seguranca",
        "Dispositivos de seguranca",
        "avalie protecoes fisicas, enclausuramento, sensores, cortinas, intertravamentos e parada de emergencia",
        "protecoes, intertravamentos e botoes de emergencia",
      ),
      item(
        "seguranca_eletrica",
        "Seguranca eletrica dos dispositivos",
        "documente comandos, paineis, cabos, aterramento, integridade eletrica e riscos associados aos dispositivos de seguranca",
        "paineis, comandos, cabos e riscos eletricos",
      ),
      item(
        "zonas_risco",
        "Zonas de risco das maquinas",
        "identifique pontos de esmagamento, corte, aprisionamento, alcance e acessos indevidos as zonas perigosas",
        "zonas de risco, acessos e pontos criticos de operacao",
      ),
      item(
        "documentacao_art",
        "Documentacao e ART",
        "registre manuais, inventario, diagramas, procedimentos, treinamentos e a necessidade de ART ou memorial tecnico",
        "documentos conferidos, lacunas e ART vinculada",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe vista geral da maquina e detalhes dos pontos com risco ou protecao relevante",
        "vista geral, ponto perigoso e detalhe da protecao",
      ),
      item(
        "conclusao",
        "Conclusao e recomendacoes",
        "sintetize conformidade, nao conformidades, recomendacoes e proximo passo do caso",
        "status tecnico, risco e recomendacoes finais",
      ),
    ],
  },
  nr13: {
    label: "NR13 Inspecoes e Integridade",
    checklist: [
      item(
        "identificacao_equipamento",
        "Identificacao do equipamento",
        "registre equipamento, local, placa, tag, categoria e referencia do prontuario quando existir",
        "equipamento, tag, placa e local resumido",
      ),
      item(
        "tipo_inspecao",
        "Tipo de inspecao",
        "marque se a atividade e inicial, periodica ou extraordinaria e descreva o motivo tecnico do escopo",
        "tipo de inspecao, motivo e norma aplicada",
      ),
      item(
        "contexto_operacao",
        "Contexto da vistoria",
        "confirme condicao operacional, responsaveis presentes e limites da inspecao executada",
        "responsaveis, data e escopo da coleta",
      ),
      item(
        "dispositivos_seguranca",
        "Dispositivos de seguranca",
        "avalie valvulas, instrumentos, indicadores, isolamentos, manometros e condicoes visiveis de seguranca",
        "valvulas, instrumentos e dispositivos relevantes",
      ),
      item(
        "documentacao_registros",
        "Prontuario, laudos e livros",
        "relacione prontuario, livros de registro, relatorios anteriores, certificados e pendencias documentais",
        "documentos conferidos, historico e pendencias",
      ),
      item(
        "ensaios_encaminhamentos",
        "Ensaios e encaminhamentos",
        "registre se houve necessidade de ultrassom, calibracao, teste hidrostatico ou outro ensaio complementar",
        "ensaios realizados, recomendados ou pendentes",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos da identificacao do equipamento, dispositivos e achados criticos",
        "placa, vista geral e detalhe do dispositivo ou achado",
      ),
      item(
        "conclusao",
        "Conclusao e encaminhamento",
        "resuma conformidade, pendencias e necessidade de acao antes da emissao do laudo",
        "status tecnico, pendencias e recomendacoes finais",
      ),
    ],
  },
  nr13_calibracao: {
    label: "NR13 Calibracao de Valvulas e Manometros",
    checklist: [
      item(
        "identificacao_dispositivos",
        "Identificacao dos dispositivos",
        "registre valvulas de seguranca, manometros, tags, faixa de operacao e vinculacao ao equipamento principal",
        "dispositivos, tag, faixa e equipamento vinculado",
      ),
      item(
        "escopo_calibracao",
        "Escopo da calibracao",
        "descreva tipo de servico, padrao usado, laboratorio ou bancada e responsaveis pela execucao",
        "escopo, padrao de referencia e responsaveis",
      ),
      item(
        "condicao_inicial",
        "Condicao inicial e preservacao",
        "documente lacres, estado visual, limpeza, danos aparentes e qualquer restricao antes da calibracao",
        "lacres, estado visual e restricoes",
      ),
      item(
        "resultado_calibracao",
        "Resultado da calibracao",
        "registre set points, desvios encontrados, ajustes executados e criterio de aceitacao adotado",
        "set points, desvios e resultado aprovado ou reprovado",
      ),
      item(
        "certificados_rastreabilidade",
        "Certificados e rastreabilidade",
        "confirme emissao de certificado, rastreabilidade metrologica e vinculacao com o prontuario ou laudo",
        "certificado, rastreabilidade e vinculo documental",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos dos dispositivos, identificacao, bancada e evidencias do resultado final",
        "dispositivo, identificacao, bancada e evidencia do resultado",
      ),
      item(
        "conclusao",
        "Conclusao e liberacao",
        "resuma os dispositivos calibrados, pendencias e a recomendacao tecnica para retorno a operacao",
        "resultado final, pendencias e recomendacoes",
      ),
    ],
  },
  nr13_teste_hidrostatico: {
    label: "NR13 Teste Hidrostatico e Estanqueidade",
    checklist: [
      item(
        "identificacao_sistema",
        "Identificacao do sistema",
        "registre equipamento, trecho, fluido de teste, pressao de projeto e referencias do procedimento aplicado",
        "equipamento, trecho, fluido e pressao de referencia",
      ),
      item(
        "preparo_teste",
        "Preparo do teste",
        "descreva isolamento, drenagem, limpeza, enchimento, bloqueios e condicoes de seguranca antes da pressurizacao",
        "isolamento, preparo e condicoes de seguranca",
      ),
      item(
        "instrumentacao_controle",
        "Instrumentacao e controle",
        "registre manometros, bombas, pontos de medicao, tempo de estabilizacao e criterio de aceite adotado",
        "instrumentacao, faixa de medicao e criterio de aceite",
      ),
      item(
        "execucao_teste",
        "Execucao do teste",
        "documente patamar de pressao, tempo de permanencia, quedas observadas e qualquer anomalia durante o teste",
        "pressao aplicada, tempo e comportamento observado",
      ),
      item(
        "estanqueidade_vazamentos",
        "Estanqueidade e vazamentos",
        "registre pontos de vazamento, reapertos, reparos provisiorios e resultado final da verificacao de estanqueidade",
        "vazamentos, pontos criticos e resultado final",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos do preparo, instrumentacao, patamar de teste e dos pontos de vazamento ou aprovacao",
        "instrumentacao, patamar de teste e pontos criticos",
      ),
      item(
        "conclusao",
        "Conclusao e liberacao",
        "defina se o sistema foi aprovado, reprovado ou ficou pendente de correcao antes da liberacao",
        "status final, restricoes e recomendacoes",
      ),
    ],
  },
  nr13_ultrassom: {
    label: "NR13 Medicao por Ultrassom",
    checklist: [
      item(
        "identificacao_equipamento",
        "Identificacao do equipamento",
        "registre o equipamento, trecho medido, espessura nominal, material e referencia do prontuario",
        "equipamento, trecho, espessura nominal e material",
      ),
      item(
        "planejamento_pontos",
        "Planejamento dos pontos",
        "descreva a malha de medicao, quantidade de pontos, criterio de amostragem e areas criticas selecionadas",
        "malha de medicao, pontos e criterio adotado",
      ),
      item(
        "calibracao_aparelho",
        "Calibracao do aparelho",
        "registre equipamento de ultrassom, bloco padrao, acoplante e ajustes usados antes da leitura",
        "aparelho, bloco padrao e ajustes iniciais",
      ),
      item(
        "leituras_espessura",
        "Leituras de espessura",
        "consolide valores medidos, minima encontrada, dispersao relevante e localizacao dos pontos mais criticos",
        "leituras, minima medida e pontos criticos",
      ),
      item(
        "avaliacao_integridade",
        "Avaliacao de integridade",
        "interprete perda de espessura, corrosao, desgaste e necessidade de calculos ou ensaios complementares",
        "avaliacao da integridade e necessidade de complemento",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos dos pontos medidos, da tela do aparelho e das regioes com maior desgaste",
        "pontos medidos, tela do aparelho e detalhe critico",
      ),
      item(
        "conclusao",
        "Conclusao e recomendacoes",
        "resuma a condicao da espessura remanescente, limites aceitaveis e a recomendacao tecnica final",
        "status tecnico, espessura critica e recomendacoes",
      ),
    ],
  },
  nr20_instalacoes: {
    label: "NR20 Instalacoes e Analise de Riscos",
    checklist: [
      item(
        "identificacao_instalacao",
        "Identificacao da instalacao",
        "registre unidade, area classificada, substancias envolvidas e o escopo do servico em NR20",
        "unidade, area, produto inflamavel e escopo",
      ),
      item(
        "projeto_instalacao",
        "Projeto de instalacao",
        "descreva arranjo geral, capacidade, segregacoes, bacias, ventilacao e referencias de projeto disponiveis",
        "arranjo, capacidade, referencias e condicionantes",
      ),
      item(
        "plano_inspecao_manutencao",
        "Plano de inspecoes e manutencoes",
        "confirme periodicidades, rotinas previstas, historico de manutencao e pontos sem cobertura adequada",
        "periodicidades, historico e lacunas do plano",
      ),
      item(
        "analise_riscos",
        "Analises de riscos",
        "registre cenarios de incendio, explosao, vazamento, ignicao e controles preventivos ou mitigadores existentes",
        "cenarios de risco e controles identificados",
      ),
      item(
        "prevencao_controles",
        "Prevencao e controles",
        "avalie sinalizacao, aterramento, deteccao, combate, procedimentos, permissao de trabalho e resposta a emergencia",
        "controles existentes, sinalizacao e resposta a emergencia",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos da instalacao, dos sistemas de seguranca, da sinalizacao e dos pontos de maior risco",
        "vista geral, sistema de seguranca e ponto critico",
      ),
      item(
        "conclusao",
        "Conclusao e recomendacoes",
        "sintetize maturidade da instalacao, riscos prioritarios e a recomendacao tecnica do servico NR20",
        "status tecnico, riscos prioritarios e proximo passo",
      ),
    ],
  },
  nr33_espaco_confinado: {
    label: "NR33 Espaco Confinado",
    checklist: [
      item(
        "identificacao_espaco",
        "Identificacao do espaco",
        "registre o espaco confinado, localizacao, processo associado e a finalidade da avaliacao",
        "espaco, localizacao e processo associado",
      ),
      item(
        "classificacao_mapeamento",
        "Classificacao e mapeamento",
        "descreva acessos, dimensoes, pontos de entrada, energias perigosas e a classificacao do espaco",
        "classificacao, acessos e mapa resumido do espaco",
      ),
      item(
        "riscos_controles",
        "Riscos e controles",
        "consolide atmosferas perigosas, engolfamento, energia residual, ventilacao, isolamento e bloqueios necessarios",
        "riscos principais, controles existentes e lacunas",
      ),
      item(
        "padronizacoes_layouts",
        "Padronizacoes e layouts",
        "registre sinalizacao, identificacao visual, fluxos de entrada e saida e padroes operacionais adotados",
        "sinalizacao, layout e padroes operacionais",
      ),
      item(
        "plano_resgate",
        "Plano de resgate",
        "verifique equipe, meios de comunicacao, pontos de retirada, equipamentos de resgate e tempo de resposta esperado",
        "plano de resgate, recursos e responsaveis",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos dos acessos, da sinalizacao, da ventilacao, dos bloqueios e dos recursos de resgate",
        "acesso, sinalizacao, bloqueio e recurso de resgate",
      ),
      item(
        "conclusao",
        "Conclusao e liberacao",
        "sintetize se o espaco esta apto, restrito ou pendente de adequacoes antes da PET ou da entrada",
        "status final, restricoes e recomendacoes",
      ),
    ],
  },
  nr35_linha_vida: {
    label: "NR35 Inspecao de Linha de Vida",
    checklist: [
      item(
        "identificacao_laudo",
        "Identificacao do ativo e do laudo",
        "registre unidade, local, tag ou nome da linha de vida e qualquer numero de laudo ou referencia do fabricante ja disponivel",
        "codigo do ativo, local resumido, unidade e identificacao do ponto inspecionado",
      ),
      item(
        "contexto_vistoria",
        "Contexto da vistoria",
        "confirme contratante, contratada, engenheiro responsavel, inspetor lider e data da vistoria",
        "nome dos responsaveis, data da coleta e quem acompanhou a inspecao",
      ),
      item(
        "objeto_inspecao",
        "Objeto da inspecao",
        "descreva o objeto da inspecao e marque se a linha de vida e vertical, horizontal ou ponto de ancoragem",
        "descricao tecnica curta do ativo e classificacao do tipo de linha de vida",
      ),
      item(
        "componentes_inspecionados",
        "Componentes inspecionados",
        "avalie fixacao dos pontos, cabo de aco, esticador, sapatilha, olhal e grampos marcando C, NC ou NA",
        "tabela com os seis componentes e observacao tecnica quando houver NC ou NA",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos panoramicas e de detalhe com legenda curta para cada evidencia principal",
        "vista geral, ponto superior, ponto inferior, detalhe critico e legenda objetiva",
      ),
      item(
        "conclusao",
        "Conclusao e proxima inspecao",
        "defina se o status final e aprovado, reprovado ou pendente, registre a proxima inspecao e escreva as observacoes finais",
        "status final, justificativa tecnica, proxima inspecao periodica e observacoes objetivas",
      ),
    ],
  },
  nr35_montagem: {
    label: "NR35 Montagem e Fabricacao",
    checklist: [
      item(
        "identificacao_servico",
        "Identificacao do servico",
        "registre unidade, local, tipo de sistema, escopo de fabricacao ou montagem e referencias tecnicas disponiveis",
        "unidade, local, sistema e escopo do servico",
      ),
      item(
        "componentes_materiais",
        "Componentes e materiais",
        "liste cabo, trilho, postes, chumbadores, conectores, elementos de fixacao e certificados disponiveis",
        "componentes aplicados, materiais e certificados",
      ),
      item(
        "execucao_montagem",
        "Execucao da montagem",
        "descreva sequencia de montagem, fixacoes, torque, alinhamento, tensao e controles de campo adotados",
        "etapas executadas, fixacoes e controles de montagem",
      ),
      item(
        "fabricacao_rastreabilidade",
        "Fabricacao e rastreabilidade",
        "registre identificacao de pecas, lotes, soldas, tratamentos, responsaveis e evidencias de rastreabilidade",
        "lotes, identificacoes, soldas e rastreabilidade",
      ),
      item(
        "validacao_liberacao",
        "Validacao e liberacao",
        "confirme testes, ajustes finais, pendencias de campo e criterio de liberacao para uso ou inspecao final",
        "testes executados, ajustes e criterio de liberacao",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos da montagem, dos componentes, dos detalhes de fixacao e da condicao final instalada",
        "montagem, detalhe de fixacao, componente e condicao final",
      ),
      item(
        "conclusao",
        "Conclusao e proximo passo",
        "resuma o estado da fabricacao ou montagem, pendencias e a recomendacao para liberacao ou correcoes",
        "status final, pendencias e recomendacoes",
      ),
    ],
  },
  nr35_ponto_ancoragem: {
    label: "NR35 Ponto de Ancoragem",
    checklist: [
      item(
        "identificacao_ponto",
        "Identificacao do ponto",
        "registre unidade, local, tipo de ponto de ancoragem, tag e referencia estrutural do elemento inspecionado",
        "local, tipo de ponto, tag e referencia estrutural",
      ),
      item(
        "contexto_vistoria",
        "Contexto da vistoria",
        "confirme responsaveis, data, condicao de acesso e finalidade operacional do ponto avaliado",
        "responsaveis, data e contexto de uso",
      ),
      item(
        "substrato_fixacao",
        "Substrato e fixacao",
        "avalie base estrutural, fixadores, chumbadores, soldas e qualquer evidencia de deformacao ou corrosao",
        "substrato, fixadores, soldas e integridade visual",
      ),
      item(
        "capacidade_identificacao",
        "Capacidade e identificacao",
        "registre identificacao do fabricante, capacidade declarada, sinalizacao e rastreabilidade disponivel",
        "capacidade, fabricante e identificacao do ponto",
      ),
      item(
        "ensaio_condicao_uso",
        "Condicao de uso e ensaio",
        "documente se houve ensaio, torque, tracao, verificacao funcional ou restricao tecnica para uso imediato",
        "ensaio executado, resultado e restricoes de uso",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos da base estrutural, da fixacao, da identificacao e dos achados relevantes",
        "base estrutural, fixacao, identificacao e detalhe critico",
      ),
      item(
        "conclusao",
        "Conclusao e recomendacoes",
        "defina se o ponto esta apto, inapto ou pendente de adequacao antes do uso em altura",
        "status final, justificativa tecnica e recomendacoes",
      ),
    ],
  },
  nr35_projeto: {
    label: "NR35 Projeto de Protecao Contra Queda",
    checklist: [
      item(
        "escopo_projeto",
        "Escopo do projeto",
        "registre unidade, local, atividade em altura, objetivo do projeto e premissas de contratacao",
        "unidade, local, atividade e objetivo do projeto",
      ),
      item(
        "levantamento_areas",
        "Levantamento das areas",
        "descreva geometria, acessos, interferencias, cobertura, estrutura e pontos de risco para quedas",
        "geometria, acessos e interferencias principais",
      ),
      item(
        "criterios_normativos",
        "Criterios normativos",
        "consolide requisitos da NR35, normas complementares, hipoteses de carga e criterios de desempenho adotados",
        "normas aplicadas, hipoteses e criterios do projeto",
      ),
      item(
        "solucao_tecnica",
        "Solucao tecnica proposta",
        "detalhe linha de vida, pontos de ancoragem, suportes, acessos, zonas livres e elementos de protecao previstos",
        "solucao tecnica, componentes previstos e zonas de protecao",
      ),
      item(
        "documentacao_art",
        "Documentacao e ART",
        "registre memoriais, desenhos, calculos, especificacoes, ART e documentos complementares necessarios",
        "desenhos, calculos, memorial e ART",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos do local, da estrutura base e dos pontos relevantes para o desenvolvimento do projeto",
        "local, estrutura base e pontos relevantes",
      ),
      item(
        "conclusao",
        "Conclusao e entregaveis",
        "resuma escopo fechado, restricoes do projeto e os entregaveis que seguirao para emissao ou revisao",
        "escopo final, restricoes e entregaveis",
      ),
    ],
  },
  pie: {
    label: "PIE Instalacoes Eletricas",
    checklist: [
      item(
        "identificacao_instalacao",
        "Identificacao da instalacao",
        "registre unidade, area, quadro ou circuito principal inspecionado e o escopo do PIE",
        "unidade, area, quadro principal e escopo resumido",
      ),
      item(
        "contexto_documental",
        "Contexto documental",
        "confirme documentos disponiveis, referencia do prontuario e responsaveis que acompanharam a coleta",
        "documentos base, responsaveis e escopo documental",
      ),
      item(
        "quadros_protecao",
        "Quadros e protecao eletrica",
        "avalie quadros, identificacao, protecoes e condicoes visuais das instalacoes criticas",
        "quadros, protecoes e identificacao eletrica",
      ),
      item(
        "documentacao_riscos",
        "Riscos e lacunas documentais",
        "relacione principais riscos observados e lacunas documentais que impactam o PIE",
        "riscos identificados e documentos ausentes ou inconsistentes",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos dos quadros, protecoes, identificacoes e achados relevantes",
        "vista geral, quadro, protecao e detalhe do achado",
      ),
      item(
        "conclusao",
        "Conclusao e encaminhamento",
        "sintetize conformidade, principais riscos e proximo passo do documento",
        "status tecnico, riscos e recomendacoes finais",
      ),
    ],
  },
  rti: {
    label: "NR10 RTI Eletrica",
    checklist: [
      item(
        "identificacao_instalacao",
        "Identificacao da instalacao",
        "registre unidade, local, quadro ou circuito critico e o escopo da RTI",
        "unidade, local, quadro/circuito e escopo resumido",
      ),
      item(
        "contexto_inspecao",
        "Contexto da inspecao",
        "descreva condicao da coleta, responsaveis e contexto operacional da instalacao",
        "responsaveis, data e contexto da instalacao",
      ),
      item(
        "quadros_circuitos",
        "Quadros e circuitos criticos",
        "documente os pontos eletricos mais relevantes, sua identificacao e estado geral de conservacao",
        "quadros, circuitos e identificacao dos pontos criticos",
      ),
      item(
        "nao_conformidades",
        "Nao conformidades eletricas",
        "consolide riscos, desvios e evidencias objetivas das nao conformidades encontradas",
        "risco eletrico, desvio tecnico e justificativa curta",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos de quadros, circuitos, protecoes e nao conformidades principais",
        "vista geral, quadro, detalhe do desvio e legenda objetiva",
      ),
      item(
        "conclusao",
        "Conclusao e prioridade de acao",
        "feche com status tecnico, criticidade e prioridade de correcao ou envio para mesa",
        "status tecnico, criticidade e proximo passo",
      ),
    ],
  },
  spda: {
    label: "SPDA Protecao Descargas",
    checklist: [
      item(
        "identificacao_sistema",
        "Identificacao do sistema",
        "registre a edificacao, area avaliada e referencias basicas do sistema SPDA",
        "edificacao, area e identificacao do sistema",
      ),
      item(
        "contexto_inspecao",
        "Contexto da inspecao",
        "descreva escopo da vistoria, acesso aos pontos e responsaveis presentes",
        "escopo, acessos e responsaveis da coleta",
      ),
      item(
        "captacao_descidas",
        "Captacao e descidas",
        "avalie pontos de captacao, descidas, conexoes e descontinuidades relevantes",
        "captacao, descidas e conexoes visiveis",
      ),
      item(
        "aterramento_equipotencializacao",
        "Aterramento e equipotencializacao",
        "registre evidencias de aterramento, barramentos e integracoes do sistema",
        "aterramento, barramentos e equipotencializacao",
      ),
      item(
        "registros_fotograficos",
        "Registros fotograficos",
        "anexe fotos dos pontos de captacao, descidas, aterramento e achados relevantes",
        "vista geral, captacao, descida e detalhe do achado",
      ),
      item(
        "conclusao",
        "Conclusao e recomendacoes",
        "sintetize conformidade do sistema, pendencias e recomendacoes de correcao",
        "status tecnico, pendencias e recomendacoes finais",
      ),
    ],
  },
};

const GUIDED_INSPECTION_TEMPLATE_ORDER: GuidedInspectionTemplateKey[] = [
  "padrao",
  "rti",
  "pie",
  "spda",
  "loto",
  "nr11_movimentacao",
  "nr12maquinas",
  "nr13",
  "nr13_ultrassom",
  "nr13_calibracao",
  "nr13_teste_hidrostatico",
  "nr20_instalacoes",
  "nr33_espaco_confinado",
  "nr35_linha_vida",
  "nr35_ponto_ancoragem",
  "nr35_projeto",
  "nr35_montagem",
  "avcb",
  "cbmgo",
];

export function listGuidedInspectionTemplates(): GuidedInspectionTemplateOption[] {
  return GUIDED_INSPECTION_TEMPLATE_ORDER.map((key) => ({
    key,
    label: GUIDED_INSPECTION_TEMPLATES[key].label,
  }));
}

const TEMPLATE_KEY_ALIASES: Record<string, GuidedInspectionTemplateKey> = {
  avcb: "avcb",
  cbmgo: "cbmgo",
  cbmgo_cmar: "cbmgo",
  checklist_cbmgo: "cbmgo",
  calibracao_manometros: "nr13_calibracao",
  calibracao_valvulas_seguranca: "nr13_calibracao",
  linha_vida_nr35: "nr35_linha_vida",
  loto: "loto",
  loto_nr10: "loto",
  nr10: "rti",
  nr10_implantacao_loto: "loto",
  nr10_inspecao_spda: "spda",
  nr10_inspecao_instalacoes_eletricas: "rti",
  nr10_loto: "loto",
  nr10_pie: "pie",
  nr10_rti: "rti",
  nr10_prontuario_instalacoes_eletricas: "pie",
  nr10_spda: "spda",
  nr11: "nr11_movimentacao",
  nr11_inspecao_equipamento_icamento: "nr11_movimentacao",
  nr11_inspecao_movimentacao_armazenagem: "nr11_movimentacao",
  nr11_movimentacao: "nr11_movimentacao",
  nr12: "nr12maquinas",
  nr12_apreciacao_risco_maquina: "nr12maquinas",
  nr12_inspecao_maquina_equipamento: "nr12maquinas",
  nr12_maquinas: "nr12maquinas",
  nr12maquinas: "nr12maquinas",
  nr13: "nr13",
  nr13_caldeira: "nr13",
  nr13_calculo_espessura_minima_tubulacao: "nr13_ultrassom",
  nr13_calculo_espessura_minima_vaso_pressao: "nr13_ultrassom",
  nr13_calibracao: "nr13_calibracao",
  nr13_calibracao_valvulas_manometros: "nr13_calibracao",
  nr13_inspecao_caldeira: "nr13",
  nr13_inspecao_tubulacao: "nr13",
  nr13_inspecao_vaso_pressao: "nr13",
  nr13_integridade_caldeira: "nr13",
  nr13_medicao_espessura_ultrassom: "nr13_ultrassom",
  nr13_teste_estanqueidade_tubulacao_gas: "nr13_teste_hidrostatico",
  nr13_teste_hidrostatico: "nr13_teste_hidrostatico",
  nr13_ultrassom: "nr13_ultrassom",
  nr20: "nr20_instalacoes",
  nr20_inspecao_instalacoes_inflamaveis: "nr20_instalacoes",
  nr20_instalacoes: "nr20_instalacoes",
  nr20_prontuario_instalacoes_inflamaveis: "nr20_instalacoes",
  nr33: "nr33_espaco_confinado",
  nr33_avaliacao_espaco_confinado: "nr33_espaco_confinado",
  nr33_espaco_confinado: "nr33_espaco_confinado",
  nr33_permissao_entrada_trabalho: "nr33_espaco_confinado",
  nr35: "nr35_linha_vida",
  nr35_fabricacao: "nr35_montagem",
  nr35_fabricacao_linha_vida: "nr35_montagem",
  nr35_inspecao_linha_de_vida: "nr35_linha_vida",
  nr35_inspecao_ponto_ancoragem: "nr35_ponto_ancoragem",
  nr35_linha_vida: "nr35_linha_vida",
  nr35_montagem: "nr35_montagem",
  nr35_montagem_geral: "nr35_montagem",
  nr35_montagem_linha_de_vida: "nr35_montagem",
  nr35_ponto_ancoragem: "nr35_ponto_ancoragem",
  nr35_projeto: "nr35_projeto",
  nr35_projeto_protecao_queda: "nr35_projeto",
  nr35_projeto_linha_vida: "nr35_projeto",
  nr35_usina: "nr35_linha_vida",
  padrao: "padrao",
  pie: "pie",
  projeto_nr35: "nr35_projeto",
  rti: "rti",
  spda: "spda",
};

function dedupeIds(items: string[]): string[] {
  return Array.from(new Set(items));
}

function clampGuidedStepIndex(
  totalCount: number,
  preferredIndex: number,
): number {
  if (totalCount <= 0) {
    return 0;
  }
  return Math.min(Math.max(preferredIndex, 0), totalCount - 1);
}

function resolveGuidedCurrentStepIndex(
  checklist: GuidedInspectionChecklistItem[],
  completedStepIds: string[],
  preferredIndex: number,
): number {
  if (!checklist.length) {
    return 0;
  }

  if (completedStepIds.length) {
    const completedSet = new Set(completedStepIds);
    const firstIncompleteIndex = checklist.findIndex(
      (item) => !completedSet.has(item.id),
    );
    if (firstIncompleteIndex >= 0) {
      return firstIncompleteIndex;
    }
    return checklist.length - 1;
  }

  return clampGuidedStepIndex(checklist.length, preferredIndex);
}

function normalizeGuidedAttachmentKind(
  value: unknown,
): "none" | "image" | "document" | "mixed" {
  if (value === "image" || value === "document" || value === "mixed") {
    return value;
  }
  return "none";
}

export function createGuidedInspectionDraft(
  templateKey: GuidedInspectionTemplateKey = "padrao",
): GuidedInspectionDraft {
  const template = GUIDED_INSPECTION_TEMPLATES[templateKey];
  return {
    checklist: template.checklist,
    completedStepIds: [],
    currentStepIndex: 0,
    evidenceBundleKind: "case_thread",
    evidenceRefs: [],
    mesaHandoff: null,
    startedAt: new Date().toISOString(),
    templateKey,
    templateLabel: template.label,
  };
}

export function resolveGuidedInspectionTemplateKey(
  tipoTemplate: string | null | undefined,
): GuidedInspectionTemplateKey {
  const normalized = String(tipoTemplate || "")
    .trim()
    .toLowerCase();
  return TEMPLATE_KEY_ALIASES[normalized] || "padrao";
}

export function guidedInspectionDraftFromMobilePayload(
  payload: MobileGuidedInspectionDraftPayload | null | undefined,
): GuidedInspectionDraft | null {
  if (!payload) {
    return null;
  }

  const templateKey = resolveGuidedInspectionTemplateKey(payload.template_key);
  const fallbackDraft = createGuidedInspectionDraft(templateKey);
  const checklist = Array.isArray(payload.checklist)
    ? payload.checklist
        .map((item) => ({
          id: String(item?.id || "").trim(),
          title: String(item?.title || "").trim(),
          prompt: String(item?.prompt || "").trim(),
          evidenceHint: String(item?.evidence_hint || "").trim(),
        }))
        .filter(
          (item) => item.id && item.title && item.prompt && item.evidenceHint,
        )
    : [];

  const normalizedChecklist = checklist.length
    ? checklist
    : fallbackDraft.checklist;
  const checklistIds = new Set(normalizedChecklist.map((item) => item.id));
  const completedStepIds = dedupeIds(
    Array.isArray(payload.completed_step_ids)
      ? payload.completed_step_ids
          .map((item) => String(item || "").trim())
          .filter((item) => item && checklistIds.has(item))
      : [],
  );

  return {
    checklist: normalizedChecklist,
    completedStepIds,
    currentStepIndex: resolveGuidedCurrentStepIndex(
      normalizedChecklist,
      completedStepIds,
      Number(payload.current_step_index) || 0,
    ),
    evidenceBundleKind: "case_thread",
    evidenceRefs: Array.isArray(payload.evidence_refs)
      ? Array.from(
          new Map(
            payload.evidence_refs
              .map((item) => ({
                messageId: Number(item?.message_id) || 0,
                stepId: String(item?.step_id || "").trim(),
                stepTitle: String(item?.step_title || "").trim(),
                capturedAt: String(item?.captured_at || "").trim(),
                evidenceKind: "chat_message" as const,
                attachmentKind: normalizeGuidedAttachmentKind(
                  item?.attachment_kind,
                ),
              }))
              .filter(
                (item) =>
                  item.messageId > 0 &&
                  item.stepId &&
                  checklistIds.has(item.stepId) &&
                  item.stepTitle &&
                  item.capturedAt,
              )
              .map((item) => [item.messageId, item]),
          ).values(),
        )
      : [],
    mesaHandoff:
      payload.mesa_handoff &&
      typeof payload.mesa_handoff === "object" &&
      checklistIds.has(String(payload.mesa_handoff.step_id || "").trim()) &&
      String(payload.mesa_handoff.step_id || "").trim() &&
      String(payload.mesa_handoff.step_title || "").trim() &&
      String(payload.mesa_handoff.recorded_at || "").trim()
        ? {
            required: Boolean(payload.mesa_handoff.required),
            reviewMode:
              String(payload.mesa_handoff.review_mode || "").trim() ||
              "mesa_required",
            reasonCode:
              String(payload.mesa_handoff.reason_code || "").trim() ||
              "policy_review_mode",
            recordedAt: String(payload.mesa_handoff.recorded_at || "").trim(),
            stepId: String(payload.mesa_handoff.step_id || "").trim(),
            stepTitle: String(payload.mesa_handoff.step_title || "").trim(),
          }
        : null,
    startedAt:
      String(payload.started_at || "").trim() || fallbackDraft.startedAt,
    templateKey,
    templateLabel:
      String(payload.template_label || "").trim() ||
      fallbackDraft.templateLabel,
  };
}

export function guidedInspectionDraftToMobilePayload(
  draft: GuidedInspectionDraft,
): MobileGuidedInspectionDraftPayload {
  return {
    template_key: draft.templateKey,
    template_label: draft.templateLabel,
    started_at: draft.startedAt,
    current_step_index: draft.currentStepIndex,
    completed_step_ids: dedupeIds(draft.completedStepIds),
    checklist: draft.checklist.map((item) => ({
      id: item.id,
      title: item.title,
      prompt: item.prompt,
      evidence_hint: item.evidenceHint,
    })),
    evidence_bundle_kind: "case_thread",
    evidence_refs: draft.evidenceRefs.map((item) => ({
      message_id: item.messageId,
      step_id: item.stepId,
      step_title: item.stepTitle,
      captured_at: item.capturedAt,
      evidence_kind: item.evidenceKind,
      attachment_kind: item.attachmentKind,
    })),
    mesa_handoff: draft.mesaHandoff
      ? {
          required: draft.mesaHandoff.required,
          review_mode: draft.mesaHandoff.reviewMode,
          reason_code: draft.mesaHandoff.reasonCode,
          recorded_at: draft.mesaHandoff.recordedAt,
          step_id: draft.mesaHandoff.stepId,
          step_title: draft.mesaHandoff.stepTitle,
        }
      : null,
  };
}

export function isGuidedInspectionComplete(
  draft: GuidedInspectionDraft | null | undefined,
): boolean {
  if (!draft) {
    return false;
  }
  return draft.completedStepIds.length >= draft.checklist.length;
}

export function getGuidedInspectionProgress(
  draft: GuidedInspectionDraft,
): GuidedInspectionProgress {
  const totalCount = draft.checklist.length;
  const completedCount = draft.completedStepIds.length;
  const isComplete = completedCount >= totalCount;
  const currentItem = isComplete
    ? null
    : draft.checklist[draft.currentStepIndex] || draft.checklist[0] || null;

  return {
    completedCount,
    currentItem,
    isComplete,
    remainingCount: Math.max(totalCount - completedCount, 0),
    totalCount,
  };
}

export function advanceGuidedInspectionDraft(
  draft: GuidedInspectionDraft,
): GuidedInspectionDraft {
  const currentItem = draft.checklist[draft.currentStepIndex];
  if (!currentItem) {
    return draft;
  }

  const completedStepIds = dedupeIds([
    ...draft.completedStepIds,
    currentItem.id,
  ]);
  const nextIndex = draft.checklist.findIndex(
    (item, index) =>
      index > draft.currentStepIndex && !completedStepIds.includes(item.id),
  );

  return {
    ...draft,
    completedStepIds,
    currentStepIndex:
      nextIndex >= 0
        ? nextIndex
        : Math.max(draft.checklist.length - 1, draft.currentStepIndex),
  };
}

export function buildGuidedInspectionPrompt(
  draft: GuidedInspectionDraft,
): string {
  const progress = getGuidedInspectionProgress(draft);
  if (!progress.currentItem || progress.isComplete) {
    return (
      "Checklist base concluido. Revise o chat, complemente evidencias " +
      "e gere o rascunho estruturado do laudo."
    );
  }

  return (
    `Inspecao guiada ${draft.templateLabel}. ` +
    `Etapa ${progress.completedCount + 1}/${progress.totalCount}: ` +
    `${progress.currentItem.title}. ` +
    `Registre ${progress.currentItem.prompt}. ` +
    `Evidencia esperada: ${progress.currentItem.evidenceHint}.`
  );
}

export function buildGuidedInspectionPlaceholder(
  draft: GuidedInspectionDraft | null | undefined,
): string {
  if (!draft) {
    return "Escreva sua mensagem de inspeção...";
  }

  const progress = getGuidedInspectionProgress(draft);
  if (!progress.currentItem || progress.isComplete) {
    return "Descreva a evidência final ou anexe o que falta para concluir.";
  }

  const titulo = String(progress.currentItem.title || "")
    .trim()
    .replace(/\.+$/, "");
  const dica = String(progress.currentItem.evidenceHint || "")
    .trim()
    .replace(/\.+$/, "");

  if (titulo && dica) {
    return `${titulo}: ${dica}.`;
  }
  if (titulo) {
    return `${titulo}: registre a evidência principal.`;
  }
  return "Descreva a etapa atual ou anexe a evidência.";
}

export function buildGuidedInspectionMessageContext(
  draft: GuidedInspectionDraft | null | undefined,
  attachmentKind: "none" | "image" | "document" | "mixed" = "none",
): MobileGuidedInspectionMessageContextPayload | null {
  if (!draft) {
    return null;
  }

  const progress = getGuidedInspectionProgress(draft);
  const currentItem =
    progress.currentItem ||
    draft.checklist[draft.currentStepIndex] ||
    draft.checklist[draft.checklist.length - 1] ||
    null;
  if (!currentItem) {
    return null;
  }

  return {
    template_key: draft.templateKey,
    step_id: currentItem.id,
    step_title: currentItem.title,
    attachment_kind: attachmentKind,
  };
}

export function mergeGuidedInspectionDraftWithRemote(
  localDraft: GuidedInspectionDraft | null | undefined,
  remoteDraft: GuidedInspectionDraft | null | undefined,
): GuidedInspectionDraft | null {
  if (!localDraft) {
    return remoteDraft || null;
  }
  if (!remoteDraft) {
    return localDraft;
  }
  if (localDraft.templateKey !== remoteDraft.templateKey) {
    return localDraft;
  }

  const checklist =
    remoteDraft.checklist.length > 0
      ? remoteDraft.checklist
      : localDraft.checklist;
  const checklistIds = new Set(checklist.map((item) => item.id));
  const completedStepIds = dedupeIds([
    ...remoteDraft.completedStepIds,
    ...localDraft.completedStepIds,
  ]).filter((item) => checklistIds.has(item));
  const evidenceRefs = Array.from(
    new Map(
      [...remoteDraft.evidenceRefs, ...localDraft.evidenceRefs].map((item) => [
        item.messageId,
        item,
      ]),
    ).values(),
  ).sort((left, right) => left.messageId - right.messageId);

  return {
    ...remoteDraft,
    checklist,
    completedStepIds,
    currentStepIndex: resolveGuidedCurrentStepIndex(
      checklist,
      completedStepIds,
      Math.max(localDraft.currentStepIndex, remoteDraft.currentStepIndex),
    ),
    evidenceBundleKind: "case_thread",
    evidenceRefs,
    mesaHandoff: remoteDraft.mesaHandoff || localDraft.mesaHandoff,
  };
}
