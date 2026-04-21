# Mobile, IA e Templates: diretriz para inspeção guiada, pré-preenchimento e gate humano

Data: `2026-04-05`

## Objetivo

Registrar a direção de produto e arquitetura para o fluxo de inspeção no mobile, uso de IA no preenchimento dos laudos e papel da `Mesa Avaliadora`, evitando que essas decisões fiquem espalhadas em conversa informal.

Este documento não autoriza um rewrite amplo. Ele fixa a leitura correta do problema, a arquitetura recomendada e os próximos passos de implementação.

## Contexto que motivou este documento

O cenário discutido foi:

- o inspetor vai a campo, por exemplo em uma usina, e executa uma inspeção `NR35`;
- já existem templates reais de laudo em [Templates/](../Templates);
- o desejo é usar IA para ajudar a transformar o que foi coletado no mobile em laudo preenchido corretamente;
- em parte dos casos o fluxo não deveria depender obrigatoriamente da `Mesa Avaliadora`;
- a `Mesa Avaliadora` deve continuar existindo como gate humano onde houver risco, ambiguidade, criticidade ou exigência formal de revisão;
- surgiu a dúvida de usar `Gemini` para análise e `ChatGPT` para preenchimento do relatório.

## O que já foi validado no código e nos templates

### 1. Os PDFs reais da pasta `Templates/` não são formulários preenchíveis

Os arquivos reais usados como referência, como:

- [Templates/WF-MC-115-04-23-1.pdf](../Templates/WF-MC-115-04-23-1.pdf)
- [Templates/01 - MC-CRMRSS-0746 ESC DE AC. AO ELEVADOR 02(Repro)-1.pdf](../Templates/01%20-%20MC-CRMRSS-0746%20ESC%20DE%20AC.%20AO%20ELEVADOR%2002(Repro)-1.pdf)
- [Templates/1 motor limp-1.pdf](../Templates/1%20motor%20limp-1.pdf)

têm texto extraível, mas não trazem `AcroForm` com campos nativos para preenchimento automático.

Leitura correta:

- não vale a pena desenhar a solução como "preencher campos PDF";
- o caminho pragmático é `template base + mapeamento de campos + overlay/renderização`.

### 2. O sistema já possui metade da infraestrutura necessária

Já existe no código:

- schema estruturado para geração de formulário/checklist em [web/app/domains/chat/templates_ai.py](../web/app/domains/chat/templates_ai.py);
- geração de saída estruturada por IA em [web/nucleo/cliente_ia.py](../web/nucleo/cliente_ia.py);
- renderização de preview PDF por overlay em [web/nucleo/template_laudos.py](../web/nucleo/template_laudos.py);
- biblioteca e gestão de templates da mesa em [web/app/domains/revisor/templates_laudo.py](../web/app/domains/revisor/templates_laudo.py);
- binding canônico do documento/template em [web/app/v2/document/template_binding.py](../web/app/v2/document/template_binding.py);
- fachada de readiness/materialização documental em [web/app/v2/document/facade.py](../web/app/v2/document/facade.py);
- contratos do mobile com `policy_summary`, `document_readiness` e `document_blockers` em [web/app/v2/contracts/mobile.py](../web/app/v2/contracts/mobile.py).

### 3. O bloqueio atual está mais na política do que no renderer

Hoje a política V2 ainda força a leitura mínima de revisão humana quando há laudo ativo em [web/app/v2/policy/engine.py](../web/app/v2/policy/engine.py).

Leitura correta:

- o problema de "mobile sem mesa" não deve ser resolvido como atalho de tela;
- ele deve ser resolvido como `policy mode`.

### 4. O runtime de IA atual é Gemini-first

O boot do cliente de IA hoje depende de `CHAVE_API_GEMINI` em [web/app/domains/chat/ia_runtime.py](../web/app/domains/chat/ia_runtime.py).

Leitura correta:

- se houver provider secundário, ele deve entrar atrás de um contrato comum de saída;
- não deve existir acoplamento de template a um provider específico.

## Decisões estabelecidas aqui

### 1. A IA deve pré-preencher a estrutura do laudo, não aprovar nem "escrever o PDF final"

Esta é a decisão principal.

O papel correto da IA é:

- ler histórico, mensagens, anexos, OCR, fotos e checklist;
- extrair e organizar isso em `dados_formulario` estruturado;
- apontar baixa confiança, conflito ou ausência de evidência;
- sugerir texto técnico onde o template exigir narrativa;
- nunca ser tratada como aprovadora final do documento.

O papel do renderer é:

- transformar `dados_formulario` aprovado em `preview` e depois em laudo final.

O papel humano é:

- validar, corrigir, complementar e aprovar o conteúdo documental antes da emissão formal quando a política exigir.

### 2. O mobile deve abrir em chat livre por padrão

O fluxo de entrada recomendado no app é:

- `Chat livre` como porta de entrada padrão;
- ação rápida `Nova inspeção guiada com IA`;
- a IA identifica ou recebe o template alvo;
- o app passa a operar uma sessão estruturada de inspeção por trás do chat.

Razão:

- o chat reduz fricção de entrada;
- o inspetor pode começar falando normalmente, enviando foto, áudio ou documento;
- o sistema não perde estrutura porque a conversa alimenta uma sessão formal de inspeção.

### 3. O checklist guiado deve existir por trás do chat

O chat é a interface humana.

O estado oficial da inspeção não pode morar apenas nas mensagens.

Por trás do chat, cada sessão deve manter:

- template escolhido;
- itens exigidos pelo template;
- estado de cada item: `pendente`, `respondido`, `validado`, `revisar`;
- evidências vinculadas por item;
- campos já consolidados em `dados_formulario`;
- nível de confiança por campo ou bloco.

Leitura correta:

- conversa sem estrutura vira histórico difícil de auditar;
- checklist sem conversa vira experiência rígida e de baixa adoção;
- o produto certo é híbrido: `chat + sessão estruturada`.

### 4. A Mesa Avaliadora deve deixar de ser o lugar onde o laudo nasce

A `Mesa Avaliadora` deve ser tratada prioritariamente como:

- gate humano;
- camada de revisão técnica;
- camada de correção e aprovação;
- espaço de comentários, pendências e exceções.

Ela não deve ser o ponto principal de digitação do laudo.

O laudo deve chegar à mesa já como rascunho estruturado, com:

- evidências vinculadas;
- resumo executivo sugerido;
- checklist preenchido;
- confiança por campo;
- pendências automáticas detectadas.

### 5. "Aprender com a mesa" é desejável, mas não como autoaprendizado solto em produção

O ciclo correto de aprendizado é:

- salvar evidência bruta coletada;
- salvar o `JSON sugerido pela IA`;
- salvar o diff das correções da mesa;
- salvar o `JSON final aprovado`;
- salvar o laudo emitido.

Esse acervo deve alimentar:

- melhoria de prompts por template;
- exemplos `few-shot`;
- métricas de acerto por campo;
- futura estratégia de fine-tuning ou avaliação offline.

Não é recomendável começar com:

- autoaprendizado implícito sem curadoria;
- alteração de comportamento do modelo em produção sem trilha auditável;
- ajuste de template baseado apenas em conversa solta.

### 6. A decisão "sem mesa" deve ser policy-driven

O sistema deve evoluir para suportar modos como:

- `none`
- `optional`
- `engineer_required`
- `mesa_required`

Regra recomendada:

- `none` ou `optional`: template padronizado, caso simples, checklist completo, evidências obrigatórias presentes, sem achado crítico, sem conflito e alta confiança;
- `engineer_required`: caso sem necessidade de mesa operacional, mas com exigência de aprovação humana final;
- `mesa_required`: achado crítico, risco alto, ambiguidade, baixa confiança, anexos insuficientes, conflito entre evidências ou fluxo regulatório sensível.

### 7. Não desenhar a solução como "Gemini pesquisa e ChatGPT preenche"

Essa divisão de responsabilidade parece intuitiva, mas não é o melhor primeiro passo.

Riscos:

- duas IAs com estilos diferentes preenchendo o mesmo artefato;
- custo e latência maiores;
- dificuldade para auditoria;
- variabilidade sem necessidade;
- mais complexidade antes de fechar o contrato de dados.

Direção recomendada:

- primeiro definir um único contrato canônico de saída: `dados_formulario`;
- depois usar um provider principal;
- só então, se necessário, introduzir provider secundário compatível com o mesmo schema.

### Uso de OpenAI / ChatGPT: decisão prática

Não assumir a existência de uma "API grátis do ChatGPT" como base de arquitetura.

Em 5 de abril de 2026, a documentação oficial informa que:

- a API é cobrada e gerenciada separadamente do ChatGPT;
- o caminho atual para integração programática passa pela `Responses API`;
- a maneira correta de obter saída confiável para documento estruturado é usar `Structured Outputs`.

Referências oficiais:

- [OpenAI Help: API separada do ChatGPT](https://help.openai.com/en/articles/8156019)
- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI API Pricing](https://openai.com/api/pricing/)

Leitura correta:

- se OpenAI for usada, que seja como provider secundário ou experimental;
- ela deve devolver o mesmo schema estruturado que o Gemini devolveria;
- não deve existir "modo ChatGPT" preenchendo template por texto livre.

## Arquitetura de produto recomendada

### Camadas

### 1. Coleta

Responsável por:

- mensagens de chat;
- perguntas guiadas;
- anexos;
- OCR;
- metadados de campo;
- seleção do template;
- checklist por template.

### 2. Normalização estruturada

Responsável por:

- consolidar o que foi coletado em uma sessão única de inspeção;
- transformar conversa e anexos em campos normatizados;
- registrar confiabilidade, pendências e proveniência.

Saída esperada:

- `inspection_session`
- `template_checklist_state`
- `dados_formulario`
- `field_confidence`
- `provenance_summary`

### 3. Revisão humana

Responsável por:

- revisão técnica na mesa quando a política exigir;
- resolução de pendências;
- correção do rascunho IA;
- aprovação humana final quando aplicável.

### 4. Materialização documental

Responsável por:

- transformar `dados_formulario` em preview;
- gerar artefato final do laudo;
- manter vínculo com template, versão e fontes.

## Fluxo recomendado no mobile

### Entrada padrão

O app abre em `chat livre`.

A IA pode sugerir:

- `Identifiquei uma inspeção NR35. Deseja iniciar a inspeção guiada?`

### Modo guiado

Ao entrar no modo guiado:

1. o inspetor escolhe o template ou a IA propõe um template;
2. o app abre o checklist desse template;
3. a conversa continua no chat;
4. cada resposta atualiza a sessão estruturada;
5. o app mostra progresso e faltantes.

Elementos obrigatórios da UX:

- progresso do checklist, por exemplo `18/26 itens`;
- itens com estado `pendente`, `respondido`, `validado`, `revisar`;
- aviso de evidências obrigatórias faltantes;
- botão `Ver checklist`;
- botão `Gerar rascunho`;
- botão `Gerar preview do laudo`.

### Finalização

Depois de consolidar a sessão:

- a IA gera `dados_formulario`;
- o sistema exibe preview;
- a política decide o próximo passo:
  - `emitir no mobile`
  - `enviar para mesa`
  - `exigir aprovação de engenheiro`

## Papel dos templates reais da pasta `Templates/`

Os templates reais devem ser tratados como base de verdade documental para o MVP.

Estratégia recomendada:

1. escolher um template prioritário de `NR35`;
2. mapear campos visíveis e blocos textuais;
3. definir o schema correspondente;
4. alimentar esse schema via IA;
5. gerar preview PDF sobre o template base.

Isso é melhor do que tentar resolver todos os templates ao mesmo tempo.

## Modelo de dados recomendado para o MVP

O MVP precisa explicitar ao menos estes artefatos:

- `inspection_session`
  - sessão ativa de inspeção no mobile;
- `template_key`
  - template alvo da sessão;
- `template_checklist_state`
  - estado de cada item exigido;
- `inspection_evidence`
  - anexos, OCR, mensagens e evidências estruturadas;
- `dados_formulario`
  - payload canônico de preenchimento do laudo;
- `ai_fill_attempt`
  - tentativa de preenchimento gerada pela IA;
- `human_review_diff`
  - correções da mesa ou do aprovador;
- `approval_decision`
  - decisão final de gate humano;
- `materialized_document`
  - preview e documento final emitido.

## Critérios para permitir conclusão no mobile sem mesa

Recomendação inicial:

- checklist 100% concluído;
- evidências obrigatórias anexadas;
- nenhum campo crítico com baixa confiança;
- nenhum conflito entre foto, OCR e resposta textual;
- nenhum achado classificado como crítico;
- template previamente homologado para fluxo simplificado;
- tenant e política habilitados para esse modo.

Se qualquer um desses pontos falhar, o caso sobe de modo:

- `optional` para `engineer_required`;
- `engineer_required` para `mesa_required`.

## Backlog recomendado

### Fase 1. Fixar um template piloto

Escolher um template `NR35` prioritário da pasta [Templates/](../Templates).

Saída:

- template piloto nomeado;
- inventário dos campos obrigatórios;
- inventário dos anexos e evidências mínimas.

### Fase 2. Fechar o schema do piloto

Criar o schema canônico do laudo piloto.

Saída:

- Pydantic model ou equivalente;
- chave por campo;
- classificação de obrigatoriedade;
- blocos narrativos que a IA pode sugerir.

### Fase 3. Criar a sessão estruturada de inspeção guiada

Adicionar suporte de domínio para:

- template escolhido;
- itens do checklist;
- estado por item;
- vínculo entre mensagem/anexo e item do checklist.

### Fase 4. Ligar o chat à sessão estruturada

Permitir que cada mensagem ou anexo:

- atualize campos;
- feche pendências;
- gere próximas perguntas;
- alimente a geração de rascunho.

### Fase 5. Gerar rascunho IA no schema do template

Usar o provider atual para preencher `dados_formulario` no formato do template piloto.

Somente depois dessa etapa decidir se existe necessidade real de provider secundário.

### Fase 6. Gerar preview real do laudo

Usar o template base já homologado e o renderer documental para gerar preview navegável.

### Fase 7. Evoluir o policy engine

Trocar a leitura binária atual por `review_mode` mais granular.

Saída:

- `none`
- `optional`
- `engineer_required`
- `mesa_required`

### Fase 8. Instrumentar aprendizado auditável

Salvar:

- versão IA;
- versão corrigida;
- diff humano;
- decisão final;
- métrica de confiança.

## O que não fazer agora

- não tentar resolver todos os templates ao mesmo tempo;
- não colocar o PDF final como responsabilidade direta do modelo;
- não usar duas IAs em cadeia antes de fechar o schema;
- não depender de "API grátis do ChatGPT" para a arquitetura;
- não liberar "sem mesa" como exceção manual de tela sem política explícita;
- não tratar conversa livre como único storage do estado da inspeção.

## Resultado esperado desta direção

Se esta diretriz for seguida, o produto passa a operar assim:

- o inspetor trabalha de forma natural no mobile;
- a IA ajuda na coleta e no pré-preenchimento;
- o sistema mantém estrutura e auditabilidade;
- a mesa revisa quando realmente precisa;
- o laudo nasce de dados estruturados e não de texto solto;
- o aprendizado futuro vem de correções humanas rastreáveis;
- o fluxo documental deixa de depender de digitação manual repetitiva.

## Próximo passo sugerido

Abrir um slice único e bem delimitado:

- selecionar um template `NR35` piloto da pasta [Templates/](../Templates);
- fechar o schema dele;
- desenhar a sessão `chat livre + inspeção guiada`;
- gerar o primeiro preview de laudo a partir de `dados_formulario`.
