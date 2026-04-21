# Proposta Mobile Chat-First com Órbita NR

Status: proposta de produto e implementação
Escopo: app mobile do inspetor
Piloto de apresentação: NR35
Direção estrutural: reproduzível para todas as NRs

## Objetivo

O app mobile do inspetor deve ter como centro um `chat com IA`.

Esse chat precisa servir para:

- analisar imagens, documentos, áudios e texto sobre itens industriais ou não;
- identificar contexto técnico e sugerir NRs aplicáveis;
- produzir saída profissional a partir do que foi enviado;
- permitir escalada opcional para fluxo guiado por NR;
- preservar o mesmo `caso técnico` ao longo da conversa, da revisão e da emissão.

O mobile não deve nascer `document-first`.
Ele deve nascer `chat-first`.

## Regra principal de experiência

### 1. Entrada padrão

A entrada padrão do app é sempre `chat livre`.

O usuário entra no app e já pode:

- mandar foto;
- mandar texto;
- mandar documento;
- pedir análise técnica;
- pedir interpretação profissional;
- pedir apoio para enquadramento em NR.

### 2. Fluxo opcional

`Chat guiado` não é a entrada padrão.
Ele é uma opção de evolução do caso.

O usuário pode subir do `chat livre` para `chat guiado` quando:

- quiser estruturar a análise por uma NR específica;
- a IA sugerir que existe NR claramente aplicável;
- a política do tenant exigir formalização;
- o próprio operador quiser transformar a conversa em coleta orientada.

## Dois modos oficiais do chat

## Chat Livre

Papel:

- análise aberta;
- interpretação de imagem;
- triagem de item, ativo, ambiente, instalação ou documento;
- apoio técnico rápido;
- geração de `relatório profissional livre` a partir da conversa.

Saída esperada:

- um relatório profissional com base no que foi enviado;
- linguagem técnica, clara e aproveitável operacionalmente;
- sem forçar checklist de NR se o usuário não pediu isso.

O `chat livre` pode:

- continuar só como histórico;
- gerar `relatório genérico`;
- sugerir NRs prováveis;
- evoluir para `pré-laudo` ou `chat guiado`.

## Chat Guiado

Papel:

- orientar a coleta pela NR escolhida;
- exigir checkpoints, evidências e perguntas faltantes;
- gerar `relatório guiado por NR`;
- preparar o caso para revisão humana e emissão quando aplicável.

Saída esperada:

- relatório profissional focado na NR selecionada;
- estrutura alinhada ao template/catalogo governado;
- rastreabilidade de evidências e lacunas.

## Modelo canônico de saída

O app deve suportar pelo menos estas saídas:

1. `histórico simples`
2. `relatório genérico profissional`
3. `relatório guiado por NR`
4. `laudo emitido`

## Regra de formação do relatório

### No chat livre

O relatório deve ser montado a partir do que o usuário realmente enviou:

- imagens;
- mensagens;
- documentos;
- observações adicionadas no chat.

Esse relatório precisa ter tom profissional e técnico, por exemplo:

- objeto analisado;
- contexto observado;
- achados principais;
- riscos percebidos;
- evidências consideradas;
- possíveis NRs relacionadas;
- recomendações iniciais;
- limitações da análise.

### No chat guiado

O relatório deve ser montado pela NR escolhida.

Ele precisa:

- seguir a lógica da NR ou do template governado;
- cobrar apenas os dados que faltam;
- apontar pendências de coleta;
- deixar explícito o que está pronto e o que ainda bloqueia avanço.

## Contexto ideal do caso no mobile

Tudo deve orbitar em torno do chat.

Acima da conversa, o app deve mostrar um `contexto compacto do caso`, com leitura rápida:

- o que está sendo analisado;
- modo atual: `chat livre` ou `chat guiado`;
- NR selecionada ou NRs sugeridas;
- estágio do caso;
- quantidade de evidências;
- o que falta;
- próxima ação sugerida.

Esse contexto deve ser colapsável e não pode competir com a conversa.

## Contrato sugerido para o contexto do chat

```ts
type AnalysisIntent =
  | "consulta_nr"
  | "triagem_item"
  | "relatorio_generico"
  | "laudo_formal";

type ChatOperatingMode =
  | "chat_livre"
  | "chat_guiado";

type CaseStage =
  | "analise_livre"
  | "relatorio_generico_em_preparo"
  | "pre_laudo"
  | "laudo_em_coleta"
  | "em_revisao_humana"
  | "devolvido_para_ajuste"
  | "aprovado_humano"
  | "emitido"
  | "encerrado_sem_documento"
  | "reaberto";

interface AnalysisFocusContext {
  caseId: number | null;
  operatingMode: ChatOperatingMode;
  intent: AnalysisIntent;
  stage: CaseStage;
  objectLabel: string;
  objectKind:
    | "maquina"
    | "linha_de_vida"
    | "instalacao"
    | "documento"
    | "ambiente"
    | "processo"
    | "nao_classificado";
  nrCandidates: Array<{
    code: string;
    label: string;
    confidence: number;
    reason: string;
  }>;
  selectedNrCode: string | null;
  evidenceSummary: {
    total: number;
    photos: number;
    documents: number;
    notes: number;
    missingRequired: number;
  };
  blockers: string[];
  nextActions: Array<{
    id: string;
    label: string;
    kind: "chat" | "collect" | "review" | "issue";
  }>;
}
```

## Comportamento da IA

## IA no chat livre

A IA precisa:

- analisar a imagem enviada;
- explicar o que está vendo de forma técnica;
- dizer quando a confiança for baixa;
- sugerir NRs candidatas sem travar a conversa;
- consolidar um `relatório profissional livre` com base na conversa.

Ela não deve:

- forçar enquadramento em NR cedo demais;
- fingir certeza visual quando não houver;
- transformar toda conversa em laudo automaticamente.

## IA no chat guiado

A IA precisa:

- assumir a NR escolhida como trilho principal;
- conduzir coleta por checkpoints;
- pedir somente o que falta;
- consolidar um `relatório guiado` coerente com a NR;
- preparar handoff para revisão humana quando necessário.

Ela não deve:

- abrir um segundo chat redundante para corrigir o primeiro;
- quebrar a continuidade do mesmo caso;
- declarar documento final como válido sem decisão humana.

## Arquitetura reproduzível para todas as NRs

NR35 deve ser tratada apenas como `piloto de apresentação`.

O desenho estrutural não pode ficar preso à NR35.

## Regra

O app deve funcionar por `catálogo governado de famílias/NRs`.

Cada NR ou família precisa ter metadados como:

- `nr_code`
- `family_key`
- `label`
- `analysis_prompts`
- `guided_checkpoints`
- `required_evidence`
- `report_schema`
- `review_mode_policy`
- `version`

## Consequência prática

O frontend mobile não deve manter checklist fixo hardcoded como estratégia final.
O piloto pode existir com fixture controlada, mas o destino correto é backend governado.

## UX recomendada

Tela principal única, centrada no chat.

Elementos:

1. `Context bar` compacta no topo
   - modo atual
   - NR escolhida ou sugerida
   - estágio do caso
   - pendências

2. `Timeline da conversa`
   - mensagens
   - anexos
   - análises da IA
   - cartões de resumo

3. `Action rail` contextual
   - `Continuar análise livre`
   - `Gerar relatório profissional`
   - `Escolher NR`
   - `Abrir modo guiado`
   - `Enviar para mesa`

4. `Composer`
   - texto
   - foto
   - documento
   - áudio

5. `Sheets orbitando o chat`
   - contexto do caso
   - quality gate
   - pendências
   - emissão/PDF

## Fluxo de apresentação NR35

Para demo, o melhor fluxo é:

1. usuário abre o app;
2. entra direto em `chat livre`;
3. envia foto de linha de vida, ponto de ancoragem ou condição de trabalho em altura;
4. IA analisa a imagem e descreve achados;
5. IA sugere `NR35` como candidata forte;
6. app oferece duas opções:
   - `Gerar relatório profissional livre`
   - `Abrir modo guiado NR35`
7. no modo guiado NR35, a IA passa a pedir checkpoints específicos;
8. o relatório guiado NR35 é consolidado;
9. o caso pode seguir para revisão e emissão.

Isso demonstra:

- chat livre útil desde o primeiro segundo;
- análise de imagem real;
- escalada opcional e inteligente;
- especialização por NR sem perder continuidade.

## Sequência recomendada de implementação

1. alinhar o lifecycle mobile ao canônico novo do caso técnico;
2. criar `AnalysisFocusContext` no backend e consumir isso no app;
3. tratar `chat livre` como fluxo principal com geração de `relatório profissional livre`;
4. transformar `chat guiado` em modo opcional do mesmo caso;
5. mover o guiado para catálogo governado de NR/família;
6. fechar o piloto de `NR35` como primeira família apresentada;
7. expandir o mesmo mecanismo para as demais NRs.

## Decisão prática

Se houver conflito entre `chat-first` e `template-first`, a prioridade do mobile deve ser:

1. `chat-first`
2. `relatório profissional livre`
3. `chat guiado por NR como opção`
4. `emissão governada`

Esse é o desenho mais coerente com o uso real em campo e com a proposta de valor do app móvel.
