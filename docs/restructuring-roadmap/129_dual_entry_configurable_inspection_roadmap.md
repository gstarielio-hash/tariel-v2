# Inspecao - roadmap de entrada configuravel entre chat-first e evidence-first

Criado em `2026-04-06`.

## Contexto

O produto nao deve forcar uma unica forma de iniciar a inspecao.

A direcao correta nao e trocar `chat-first` por `evidence-first` de forma absoluta. A direcao correta e permitir que a entrada da inspecao seja configuravel, mantendo o mesmo caso tecnico, o mesmo `report pack`, o mesmo bundle de evidencias e o mesmo pipeline de laudo.

Isso atende melhor o uso real porque:

- alguns inspetores pensam primeiro por narrativa e contexto;
- outros trabalham melhor por checklist, foto e item;
- algumas familias documentais exigem coleta objetiva logo no inicio;
- algumas operacoes precisam comecar rapido no mobile e organizar depois;
- a criticidade do caso pode mudar a politica efetiva de entrada.

## Correcao de direcao

Fica consolidada a seguinte decisao:

- o produto nao impora `chat-first` como unica entrada;
- o produto nao impora `evidence-first` como unica entrada;
- o usuario podera definir sua preferencia de inicio;
- tenant, familia documental e criticidade poderao restringir ou recomendar a entrada efetiva;
- a qualquer momento o caso podera migrar de uma entrada para a outra sem perder estado.

## Objetivo

Construir uma arquitetura unica de inspecao com `entrada configuravel`, em que o usuario possa iniciar pela conversa ou pelas evidencias, mas sempre alimentando o mesmo caso operacional e o mesmo laudo canonico.

## Decisao central

`Modo de entrada` e concern de experiencia e operacao, nao de regra de negocio.

O que nao muda:

- `case_id` / `laudo_id`;
- `tipo_template` e `report pack`;
- checklist estruturado;
- bundle de evidencias;
- politica de validacao;
- governanca normativa;
- renderer final do laudo.

O que muda:

- apenas a forma como o workspace abre, conduz a primeira coleta e prioriza a interface.

## Modos de entrada suportados

### `chat_first`

O caso abre priorizando:

- conversa;
- contextualizacao do ativo;
- narrativa livre do inspetor;
- envio de evidencias a partir do chat.

Uso ideal:

- inspecoes exploratorias;
- contexto inicial complexo;
- inspetor que prefere descrever antes de classificar;
- familias que toleram coleta progressiva antes do checklist pesado.

### `evidence_first`

O caso abre priorizando:

- checklist;
- itens obrigatorios;
- fotos;
- anexos;
- slots de evidencia.

Uso ideal:

- familias normativas com requisitos objetivos;
- casos em que foto, documento e marcacao sao mais importantes que narrativa livre;
- operacao com alta repetibilidade;
- situacoes em que o sistema precisa garantir completude minima antes de aceitar conclusoes.

### `auto_recommended`

Modo opcional para o produto sugerir o melhor inicio com base em:

- familia documental;
- historico do usuario;
- criticidade;
- qualidade do dispositivo/conectividade;
- politica do tenant.

Regra:

- `auto_recommended` nao elimina a preferencia do usuario;
- ele apenas define o modo inicial sugerido quando nao houver bloqueio ou exigencia mais forte.

## Politica de preferencia e precedencia

O sistema precisa distinguir:

- `entry_mode_preference`
  - preferencia persistida do usuario;
- `entry_mode_effective`
  - modo realmente usado naquele caso;
- `entry_mode_reason`
  - por que esse modo foi aplicado.

Ordem recomendada de precedencia:

1. `hard_safety_rule`
2. `family_required_mode`
3. `tenant_policy`
4. `role_policy`
5. `user_preference`
6. `last_case_mode`
7. `auto_recommended`
8. fallback padrao do produto

Exemplos:

- se o usuario preferir `chat_first`, mas a familia exigir coleta objetiva minima antes da emissao, o caso pode abrir em `evidence_first`;
- se nao houver bloqueio, a preferencia do usuario prevalece;
- se o caso mudar de criticidade no meio do fluxo, o `entry_mode_effective` pode mudar sem apagar o que ja foi coletado.

## Regra importante de produto

O sistema nao deve criar dois produtos paralelos.

`chat_first` e `evidence_first` sao duas portas de entrada para o mesmo workspace.

Isso implica:

- mesmo `case state`;
- mesma timeline;
- mesmo conjunto de anexos;
- mesmo checklist;
- mesmo bundle de evidencias;
- mesmo motor normativo;
- mesmo pipeline de laudo.

## Modelo tecnico recomendado

### 1. Caso canonico

Cada inspecao precisa carregar:

- `case_id`;
- `tipo_template`;
- `report_pack_family`;
- `report_pack_version`;
- `entry_mode_preference`;
- `entry_mode_effective`;
- `entry_mode_reason`;
- `final_validation_mode`;
- `status_operacional`.

### 2. Workspace com duas views oficiais

O workspace deve oferecer duas views primarias:

- `conversation view`
- `evidence view`

Regra:

- as duas views enxergam o mesmo caso;
- o usuario pode alternar entre elas sem perder progresso;
- o sistema registra qual modo iniciou o caso e qual foi o ultimo modo ativo.

### 3. Shared evidence composer

Toda evidencia entra por uma camada unica, mesmo que a origem seja diferente.

Origens suportadas:

- texto no chat;
- foto capturada no fluxo guiado;
- documento anexado;
- observacao estruturada;
- validacao da Mesa;
- override humano.

### 4. Report state incremental

O laudo nao deve nascer apenas na finalizacao.

O sistema deve manter um `draft estruturado incremental` do caso, atualizado conforme:

- novas evidencias entram;
- checklist e respondido;
- IA reavalia item;
- humano valida ou sobrescreve;
- slots de imagem sao resolvidos.

### 5. Gates de completude e criticidade

O modo de entrada pode ser livre, mas a saida nao.

Antes de:

- enviar para Mesa;
- concluir no mobile;
- renderizar o laudo final;

o sistema precisa avaliar:

- completude do checklist;
- evidencias obrigatorias;
- conflitos normativos;
- criticidade por item;
- elegibilidade para autonomia.

## Experiencia recomendada por superficie

### Web do inspetor

Abertura recomendada:

- seletor de modo ao iniciar nova inspecao;
- preferencia persistida por usuario;
- alternancia explicita entre conversa e evidencias no workspace;
- banner quando a politica efetiva sobrescrever a preferencia.

Hotspots provaveis:

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_laudos.js`
- `web/static/js/chat/chat_painel_relatorio.js`
- `web/app/domains/chat/chat_runtime.py`
- `web/app/domains/chat/laudo_state_helpers.py`

### Mobile do inspetor

Abertura recomendada:

- preferencia configuravel em settings;
- CTA inicial `Comecar pela conversa` ou `Comecar pelas evidencias`;
- possibilidade de troca no mesmo caso;
- perda automatica de autonomia quando a criticidade exigir.

Hotspots provaveis:

- `android/src/features/chat/useInspectorChatController.ts`
- `android/src/features/inspection/guidedInspection.ts`
- `android/src/features/inspection/useInspectorRootGuidedInspectionController.ts`
- `android/src/features/useInspectorRootConversationControllers.ts`
- `android/src/features/settings/SettingsExperienceSections.tsx`
- `android/src/features/settings/SettingsExperienceAiSection.tsx`

### Mesa avaliadora

A Mesa nao precisa herdar o modo de entrada do inspetor, mas precisa enxergar:

- como o caso foi iniciado;
- quando houve troca de modo;
- se a coleta partiu de narrativa ou de checklist;
- quais gaps ainda existem no bundle de evidencias.

Hotspots provaveis:

- `web/app/domains/revisor/panel_state.py`
- `web/app/domains/revisor/mesa_api.py`
- `web/app/domains/revisor/templates_laudo_support.py`

## Politicas por familia documental

Cada `report pack` deve poder definir:

- `recommended_entry_mode`
- `required_entry_mode` quando houver
- `minimum_evidence_before_free_chat`
- `minimum_context_before_checklist_lock`
- `autonomy_tier`

Exemplos de comportamento:

- uma familia pode recomendar `evidence_first`, mas permitir `chat_first`;
- outra pode exigir pelo menos identificacao do ativo antes de liberar conversa livre;
- outra pode aceitar qualquer entrada, mas travar finalizacao se faltarem fotos obrigatorias.

## Politica por usuario

Cada usuario deve poder configurar:

- `preferencia_padrao_de_inicio`
- `lembrar_ultimo_modo_usado`
- `abrir_sempre_em_auto_recommended`

O produto deve registrar:

- modo preferido;
- modo efetivo;
- taxa de troca de modo;
- familias em que o usuario abandona a recomendacao.

Isso ajuda a melhorar a UX sem confundir regra normativa com preferencia operacional.

## Ganhos esperados

- mais aderencia ao modo real de trabalho do inspetor;
- menos friccao na abertura do caso;
- mais completude em familias documentais duras;
- menor dependencia de um unico paradigma de interface;
- preservacao do mesmo pipeline tecnico de laudo.

## Riscos a evitar

- duplicar logica entre `chat_first` e `evidence_first`;
- tratar os modos como produtos separados;
- esconder regra normativa dentro da experiencia de entrada;
- permitir que o modo livre burle gates de completude;
- deixar o usuario escolher algo que depois o produto nao consegue honrar.

## Fases recomendadas

### Fase 0 - contrato de politica de entrada

- definir `entry_mode_preference`, `entry_mode_effective` e `entry_mode_reason`;
- definir precedencia entre usuario, tenant, familia e hard safety;
- registrar a direcao nos contratos do caso.

### Fase 1 - web do inspetor

- habilitar seletor de inicio e alternancia no workspace web;
- persistir preferencia por usuario;
- exibir razao quando a politica sobrescrever a preferencia.

### Fase 2 - mobile do inspetor

- expor preferencia nas configuracoes;
- permitir abrir por conversa ou por evidencias;
- manter o mesmo caso ao alternar de modo.

### Fase 3 - report state incremental

- consolidar o draft estruturado incremental do caso;
- evitar que um modo tenha pipeline documental diferente do outro.

### Fase 4 - gates e criticidade

- aplicar gates iguais para qualquer modo de entrada;
- derrubar autonomia quando criticidade ou conflito exigirem Mesa.

### Fase 5 - rollout controlado

- ativar por allowlist;
- medir taxa de conclusao, gaps de evidencia, divergencia IA-humano e troca de modo;
- ajustar recomendacoes por familia.

## Criterio de pronto desta frente

Esta frente so deve ser considerada pronta quando:

- o usuario puder definir a preferencia de inicio;
- o caso puder abrir em `chat_first` ou `evidence_first` sem mudar o pipeline tecnico do laudo;
- a politica efetiva puder sobrescrever a preferencia com razao explicita;
- a troca de modo no meio do caso preservar estado e evidencias;
- web, mobile e Mesa enxergarem o mesmo caso e o mesmo draft estruturado.

## Relacao com os documentos anteriores

Este documento complementa:

- `127_semantic_report_pack_execution_plan.md`
- `128_normative_override_and_learning_governance.md`

A regra consolidada fica assim:

- `127` define a espinha semantica do laudo;
- `128` define governanca normativa e aprendizado seguro;
- `129` define como o usuario entra no caso sem quebrar a espinha tecnica.

## Proximo passo exato

O primeiro slice util desta frente e implementar apenas o contrato de politica de entrada:

- campos de preferencia e modo efetivo;
- precedencia entre politica e usuario;
- persistencia de preferencia;
- registro do motivo de override da preferencia.

Enquanto isso nao existir, qualquer tentativa de abrir dois modos de forma seria apenas variacao de interface sem contrato confiavel.
