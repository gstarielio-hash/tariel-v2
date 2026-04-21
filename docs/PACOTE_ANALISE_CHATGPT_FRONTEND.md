# Pacote Para Analise Do Frontend No ChatGPT

## Objetivo

Usar o ChatGPT para analisar o frontend sem receber uma resposta generica.

A melhor forma de fazer isso hoje nao e mandar "o frontend inteiro".
O melhor resultado vem de enviar uma fatia funcional por vez, com contexto claro e uma pergunta objetiva.

No estado atual do projeto, a melhor primeira fatia e o painel do revisor, porque:

- o template principal esta claro em `web/templates/painel_revisor.html`;
- o JS esta separado por responsabilidades em arquivos diferentes;
- a entrada inicial do CSS ja foi bastante modularizada;
- a parte mais pesada que ainda resta ficou concentrada em `web/static/css/revisor/painel_revisor.css`.

## Estado Atual Util Para Analise

Hoje o CSS do revisor ja tem estes modulos extraidos:

- `web/static/css/revisor/painel_revisor/_base.css`
- `web/static/css/revisor/painel_revisor/_topbar.css`
- `web/static/css/revisor/painel_revisor/_layout.css`
- `web/static/css/revisor/painel_revisor/_whispers.css`
- `web/static/css/revisor/painel_revisor/_view_column.css`
- `web/static/css/revisor/painel_revisor/_timeline.css`
- `web/static/css/revisor/painel_revisor/_reply.css`
- `web/static/css/revisor/painel_revisor/_modal.css`
- `web/static/css/revisor/painel_revisor/_return_dialog.css`
- `web/static/css/revisor/painel_revisor/_status.css`

O arquivo principal `web/static/css/revisor/painel_revisor.css` agora ficou mais util como "camada de overrides e legado", especialmente a partir de `Tariel Mesa Refresh`.

## Regra De Ouro

Envie os pacotes nesta ordem:

1. contexto da tela;
2. bootstrap e arquitetura do JS;
3. modulo operacional mais pesado;
4. modulo complementar;
5. camada legado/override;
6. testes e contratos, se quiser uma analise mais segura.

Se mandar tudo de uma vez, a resposta tende a virar lista superficial de boas praticas.

## Pacote 1 - Shell Da Tela E Bootstrap

Quando usar:

- quando quiser diagnostico arquitetural;
- quando quiser saber onde estao as responsabilidades misturadas;
- quando quiser um plano de modularizacao por tela.

Arquivos:

- `web/templates/painel_revisor.html`
- `web/static/js/revisor/painel_revisor_page.js`
- `web/static/js/revisor/revisor_painel_core.js`

Tamanho aproximado:

- `painel_revisor.html`: 601 linhas
- `painel_revisor_page.js`: 1141 linhas
- `revisor_painel_core.js`: 1101 linhas

Comando para gerar um zip:

```bash
zip -r chatgpt_front_01_shell_revisor.zip \
  web/templates/painel_revisor.html \
  web/static/js/revisor/painel_revisor_page.js \
  web/static/js/revisor/revisor_painel_core.js
```

Pergunta ideal:

- "Quero que voce analise a arquitetura dessa tela, identifique responsabilidades misturadas, pontos de acoplamento alto, duplicacao de estado e oportunidades de modularizacao incremental sem trocar stack nem quebrar contratos."

## Pacote 2 - Mesa Operacional

Quando usar:

- quando quiser melhorar o fluxo principal do revisor;
- quando quiser separar melhor logica de workspace, fila e timeline;
- quando quiser identificar o que deveria virar modulo proprio.

Arquivos:

- `web/static/js/revisor/revisor_painel_mesa.js`
- `web/static/css/revisor/painel_revisor/_view_column.css`
- `web/static/css/revisor/painel_revisor/_timeline.css`

Opcional:

- `web/templates/painel_revisor.html`
  - se o ChatGPT precisar rever o markup do workspace

Tamanho aproximado:

- `revisor_painel_mesa.js`: 2169 linhas
- `_view_column.css`: 108 linhas
- `_timeline.css`: 748 linhas

Comando para gerar um zip:

```bash
zip -r chatgpt_front_02_mesa_operacional.zip \
  web/static/js/revisor/revisor_painel_mesa.js \
  web/static/css/revisor/painel_revisor/_view_column.css \
  web/static/css/revisor/painel_revisor/_timeline.css
```

Pergunta ideal:

- "Quero uma analise de organizacao desse modulo operacional. Aponte funcoes ou grupos de responsabilidade que deveriam ser separados, quais dependencias parecem excessivas e como eu faria isso em etapas pequenas sem quebrar a tela."

## Pacote 3 - Historico, Aprendizados, Resposta E Modais

Quando usar:

- quando quiser melhorar a parte secundaria da experiencia;
- quando quiser reduzir acoplamento entre acoes, modais, resposta e aprendizados;
- quando quiser saber o que vale transformar em componentes ou helpers.

Arquivos:

- `web/static/js/revisor/revisor_painel_historico.js`
- `web/static/js/revisor/revisor_painel_aprendizados.js`
- `web/static/css/revisor/painel_revisor/_reply.css`
- `web/static/css/revisor/painel_revisor/_modal.css`
- `web/static/css/revisor/painel_revisor/_return_dialog.css`
- `web/static/css/revisor/painel_revisor/_status.css`

Opcional:

- `web/templates/painel_revisor.html`
  - se o ChatGPT precisar ver os anchors dos modais e da resposta

Comando para gerar um zip:

```bash
zip -r chatgpt_front_03_secundarios_revisor.zip \
  web/static/js/revisor/revisor_painel_historico.js \
  web/static/js/revisor/revisor_painel_aprendizados.js \
  web/static/css/revisor/painel_revisor/_reply.css \
  web/static/css/revisor/painel_revisor/_modal.css \
  web/static/css/revisor/painel_revisor/_return_dialog.css \
  web/static/css/revisor/painel_revisor/_status.css
```

Pergunta ideal:

- "Quero analisar se essa parte do frontend esta organizada por responsabilidade ou se ainda ha mistura entre fluxo de resposta, historico, aprendizados, modais e feedback visual. Liste o que voce separaria primeiro."

## Pacote 4 - Camada Legada E Overrides

Quando usar:

- quando quiser um plano serio para continuar a reestruturacao;
- quando quiser saber quais blocos ainda estao perigosos;
- quando quiser descobrir clusters de override que ainda merecem extracao.

Arquivo:

- `web/static/css/revisor/painel_revisor.css`

Observacao importante:

- este arquivo nao e mais o "CSS inteiro da tela";
- ele agora funciona, em boa parte, como camada de tema, polimento, layout legado e overrides de prioridade;
- por isso a analise dele deve ser feita separadamente.

Comando para gerar um zip:

```bash
zip -r chatgpt_front_04_css_legado_revisor.zip \
  web/static/css/revisor/painel_revisor.css
```

Pergunta ideal:

- "Esse arquivo agora concentra a camada remanescente de overrides e legado do painel do revisor. Quero que voce identifique clusters coerentes de extracao, riscos de cascata e uma ordem segura de refatoracao."

## Pacote 5 - Contratos E Testes

Use este pacote so depois que o ChatGPT ja tiver entendido a tela.

Quando usar:

- quando quiser uma proposta de refatoracao sem quebrar contrato;
- quando quiser pedir uma lista de riscos reais, e nao so opinioes de estilo;
- quando quiser confrontar sugestoes com anchors existentes.

Arquivos mais uteis:

- `web/tests/test_reviewer_panel_boot_hotfix.py`
- `web/tests/test_v2_review_queue_projection.py`
- `web/tests/test_smoke.py`

Trechos do `test_smoke.py` que valem muito:

- anchors de contrato visual e hooks do painel;
- ids e data-attributes como:
  - `modal-pacote`
  - `mesa-operacao-painel`
  - `btn-anexo-resposta`
  - `preview-resposta-anexo`
  - `data-mesa-action="responder-item"`
  - `data-mesa-action="alternar-pendencia"`

Comando para gerar um zip:

```bash
zip -r chatgpt_front_05_testes_contratos_revisor.zip \
  web/tests/test_reviewer_panel_boot_hotfix.py \
  web/tests/test_v2_review_queue_projection.py \
  web/tests/test_smoke.py
```

Pergunta ideal:

- "Agora quero que voce revise suas sugestoes anteriores considerando esses testes e contratos. O que continua seguro, o que muda e quais pontos exigem mais cuidado."

## Prompt Mestre

Use este prompt antes de enviar o primeiro pacote:

```text
Vou te mandar pacotes do frontend de um produto SaaS em Flask/Jinja + JavaScript vanilla + CSS.

Quero uma analise tecnica real, nao uma resposta generica de boas praticas.

Objetivo:
- identificar acoplamento alto
- identificar responsabilidades misturadas
- apontar duplicacao estrutural
- propor uma ordem de refatoracao incremental
- preservar comportamento, contratos SSR, IDs, classes, data-attributes e hooks usados pela tela

Restricoes:
- nao proponha trocar stack
- nao proponha reescrever tudo
- nao responda com "use React/Vue/TypeScript" como atalho
- considere que eu quero melhorar o codigo para continuar programando em cima dele
- priorize pequenas etapas seguras

Formato da resposta:
1. Diagnostico objetivo
2. Principais riscos de manutencao
3. O que eu separaria primeiro
4. Ordem sugerida de refatoracao
5. Quick wins
6. O que eu nao mexeria agora

Sempre cite arquivos e trechos concretos.
Se faltar contexto, me diga exatamente qual arquivo faltou.
```

## Prompt De Seguimento

Use este prompt depois que ele ja tiver entendido um pacote:

```text
Agora quero que voce seja mais especifico.

Com base nesses arquivos:
- liste modulos ou funcoes que deveriam existir e ainda nao existem
- diga o que pode ser extraido sem regressao
- separe problemas de arquitetura, problemas de organizacao e problemas de legibilidade
- proponha um plano de 5 a 10 commits pequenos
- para cada commit, diga objetivo, arquivos tocados e risco

Nao quero pseudocodigo longo.
Quero um plano executavel.
```

## Ordem Recomendada De Uso

Se voce quiser o melhor retorno pratico, use esta sequencia:

1. mande o Pacote 1
2. espere a analise
3. mande o Pacote 2
4. peca para o ChatGPT revisar a analise anterior a luz do Pacote 2
5. mande o Pacote 3
6. so depois mande o Pacote 4
7. por ultimo, mande o Pacote 5 para validar riscos

## Se Quiser A Resposta Mais Forte

Nao pergunte:

- "o que acha desse frontend?"
- "pode melhorar?"
- "esta bom?"

Pergunte assim:

- "Quais 5 pontos hoje mais atrapalham a manutencao?"
- "Qual ordem de refatoracao me da mais ganho com menos risco?"
- "O que esta grande demais e por que?"
- "Quais partes ainda estao acopladas ao DOM de forma perigosa?"
- "O que eu deveria modularizar antes de adicionar novas features?"

## Melhor Uso Hoje

Se fosse para comecar agora, eu faria assim:

1. enviar `Pacote 1`
2. enviar `Pacote 2`
3. pedir um plano de modularizacao do painel do revisor
4. so depois enviar `Pacote 4` para tratar o restante legado do CSS

Isso tende a gerar uma analise muito melhor do que mandar todos os arquivos do frontend do sistema de uma vez.
