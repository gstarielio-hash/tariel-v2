# 13. Visual System Audit

## Data da execucao

- 2026-04-04

## Escopo oficial auditado

- `/admin`
- `/cliente`
- `/app`
- `/revisao`
- telas criticas de templates/documentos/mesa dentro do portal de revisao

`mesa-next` ficou explicitamente fora desta fase.

## Fontes de verdade revisadas antes da implementacao

- `12_FOR_CHATGPT.md`
- `docs/full-system-audit/12_FOR_CHATGPT.md`
- `docs/final-project-audit/00_final_project_state.md`
- `docs/final-project-audit/01_routes_and_surfaces.md`
- `docs/final-project-audit/02_flows_and_gaps.md`
- `docs/final-project-audit/03_frontend_and_visual_review.md`
- `docs/final-project-audit/04_final_closure_plan.md`
- `docs/restructuring-roadmap/99_execution_journal.md`
- `artifacts/final_project_audit/20260404_171250/visual_product_review.md`
- `artifacts/final_project_audit/20260404_171250/buttons_actions_inventory.md`
- `artifacts/final_project_audit/20260404_171250/route_inventory.json`
- `artifacts/final_project_audit/20260404_171250/source_index.txt`

## Metodo real aplicado

1. `pwd` e `git status --short` no repo oficial.
2. Leitura das rotas e shells canonicos.
3. Mapeamento dos templates, CSS e JS visuais por superficie.
4. Geracao de screenshots reais e inventarios before em `artifacts/final_visual_audit/20260404_191730/`.
5. Definicao do novo sistema visual e rollout real nos templates oficiais.
6. Geracao de screenshots e inventarios after no mesmo artifact root.
7. Validacao com `make verify`, `make mesa-smoke` e `make mesa-acceptance`.

## Artefatos da auditoria

- `artifacts/final_visual_audit/20260404_191730/screenshots_before/`
- `artifacts/final_visual_audit/20260404_191730/screenshots_after/`
- `artifacts/final_visual_audit/20260404_191730/visual_inventory_before.json`
- `artifacts/final_visual_audit/20260404_191730/visual_inventory_after.json`
- `artifacts/final_visual_audit/20260404_191730/visual_inventory.json`
- `artifacts/final_visual_audit/20260404_191730/source_inventory_before.json`
- `artifacts/final_visual_audit/20260404_191730/source_inventory_after.json`
- `artifacts/final_visual_audit/20260404_191730/style_tokens.json`
- `artifacts/final_visual_audit/20260404_191730/source_index.txt`

## Superficie base escolhida

Base principal para rollout: `/cliente`.

Motivo:

- ja era a superficie mais organizada do ponto de vista estrutural
- tinha separacao clara entre foundation, components e surfaces
- estava mais proxima de um shell enterprise limpo do que `/app` e `/revisao`
- oferecia o melhor ponto de propagacao para tokens, CTA e hierarquia

## Problemas visuais encontrados

### 1. Fragmentacao entre portais

- `/admin` ja estava em um eixo enterprise claro, mas isolado do restante
- `/cliente` era o mais limpo, porem verbose e com excesso de cards/textos
- `/app` estava visualmente distante do produto oficial por excesso de contraste e linguagem propria
- `/revisao` usava outra familia de superfices, outra densidade e outra semantica de CTA

### 2. Excesso de ruido textual

- shells e hero sections com subtitulos longos demais
- blocos com explicacao duplicada entre cabecalho, card e estado interno
- labels de CTA longos e por vezes diferentes entre superficies que fazem a mesma coisa

### 3. Cores e estilos concorrentes

- varias paletas locais com azuis, cinzas e estados nao equivalentes
- badges e chips com tratamentos diferentes por portal
- formularios e tabelas sem um mesmo acabamento visual

### 4. Hotspots de fragmentacao tecnica

- `web/static/css/chat/chat_base.css`
- `web/static/css/inspetor/reboot.css`
- `web/static/css/inspetor/workspace.css`
- `web/static/css/revisor/painel_revisor.css`
- `web/static/css/revisor/templates_biblioteca.css`
- `web/static/js/chat/chat_index_page.js`

## Leitura quantitativa before -> after

- `admin`:
  - stylesheets carregados: `7 -> 8`
  - `admin_login` wordsMain: `54 -> 50`
- `cliente`:
  - stylesheets carregados: `28 -> 32`
  - `cliente_login` wordsMain: `206 -> 178`
  - `cliente_admin` wordsMain: `485 -> 471`
  - `cliente_chat` wordsMain: `251 -> 208`
  - `cliente_mesa` wordsMain: `164 -> 139`
- `app`:
  - stylesheets carregados: `19 -> 23`
  - `app_login` wordsMain: `141 -> 123`
  - `app_home` wordsMain: `189 -> 178`
- `revisao`:
  - stylesheets carregados: `7 -> 11`
  - `revisao_painel` wordsMain: `22 -> 15`
  - `revisao_templates_biblioteca` wordsMain: `202 -> 183`
  - `revisao_templates_editor` wordsMain: `350 -> 327`

Os deltas completos ficaram serializados em `artifacts/final_visual_audit/20260404_191730/visual_inventory.json`.

## Diagnostico final da auditoria

- o problema real nao era ausencia de UI; era divergencia de linguagem visual
- o eixo enterprise oficial agora deve partir de uma base clara, sobria e de baixa saturacao
- a principal reducao desta fase veio de:
  - unificacao de superfices
  - consolidacao de tokens
  - encurtamento de microcopy
  - padronizacao de CTA, chips, inputs, tabelas e cards

## O que ficou para fases seguintes

- reduzir mais estilos legacy diretamente em `chat_base.css`, `reboot.css` e `painel_revisor.css`
- migrar mais componentes para tokens sem depender tanto de overrides globais
- adicionar gates visuais dedicados de diff de screenshot se a stack do repo for promovida para isso
