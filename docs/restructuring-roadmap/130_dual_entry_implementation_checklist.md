# Inspecao - checklist pratico de implementacao da entrada configuravel

Criado em `2026-04-06`.

## Contexto

Este documento transforma a direcao registrada em `127_semantic_report_pack_execution_plan.md`, `128_normative_override_and_learning_governance.md` e `129_dual_entry_configurable_inspection_roadmap.md` em um checklist executavel no repositorio principal.

O foco aqui nao e inventar outro produto. O foco e adicionar `entrada configuravel` ao mesmo fluxo tecnico de inspecao e laudo.

## Objetivo

Permitir que o inspetor inicie o caso por conversa ou por evidencias, com preferencia definida pelo usuario e restricoes aplicadas por familia, tenant ou criticidade, sem duplicar pipeline nem quebrar a governanca normativa.

## Invariantes

Estas regras nao devem mudar durante a execucao:

- `chat_first` e `evidence_first` alimentam o mesmo `case_id`;
- o mesmo `report pack` governa qualquer modo de entrada;
- a mesma politica normativa vale para qualquer modo;
- a mesma governanca de aprendizado vale para qualquer modo;
- a finalizacao do laudo continua dependendo de gates de completude, criticidade e conflito;
- a troca de modo nao pode apagar mensagens, anexos, checklist ou rascunho estruturado;
- override humano continua separado de elegibilidade para aprendizado.

## Hotspots reais no codigo

### Backend e contratos

- `web/app/domains/chat/normalization.py`
- `web/app/domains/chat/templates_ai.py`
- `web/app/domains/chat/gate_helpers.py`
- `web/app/domains/chat/report_finalize_stream_shadow.py`
- `web/app/domains/chat/laudo_state_helpers.py`
- `web/app/domains/chat/chat_runtime.py`
- `web/app/domains/chat/schemas.py`
- `web/app/domains/chat/learning_helpers.py`
- `web/app/domains/revisor/panel_state.py`
- `web/app/shared/db/models_laudo.py`
- `web/app/shared/db/models_auth.py`

### Web do inspetor

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_laudos.js`
- `web/static/js/chat/chat_painel_relatorio.js`
- `web/static/js/chat/chat_painel_mesa.js`

### Renderizacao documental

- `web/nucleo/template_laudos.py`
- `web/nucleo/template_editor_word.py`

### Mobile do inspetor

- `android/src/features/chat/useInspectorChatController.ts`
- `android/src/features/useInspectorRootConversationControllers.ts`
- `android/src/features/inspection/guidedInspection.ts`
- `android/src/features/inspection/useInspectorRootGuidedInspectionController.ts`
- `android/src/features/settings/SettingsExperienceSections.tsx`
- `android/src/features/settings/SettingsExperienceAiSection.tsx`

### Gates e validacao

- `web/nucleo/inspetor/confianca_ia.py`
- `web/app/domains/revisor/learning_api.py`
- `web/app/domains/chat/commands_helpers.py`

## Ordem executavel

### Fase A - contrato de politica de entrada

Objetivo:

- criar o contrato canonico de preferencia e modo efetivo.

Checklist:

- definir `entry_mode_preference`;
- definir `entry_mode_effective`;
- definir `entry_mode_reason`;
- definir precedencia entre `hard_safety_rule`, `family_required_mode`, `tenant_policy`, `role_policy`, `user_preference` e fallback;
- registrar esse contrato no estado do caso.

Arquivos-alvo:

- `web/app/domains/chat/laudo_state_helpers.py`
- `web/app/domains/chat/chat_runtime.py`
- `web/app/domains/chat/schemas.py`
- `web/app/shared/db/models_laudo.py`

Validacao minima:

- cobertura de serializacao do estado do caso;
- cobertura da precedencia da politica;
- garantia de backward compatibility para casos antigos sem esses campos.

Critico para concluir:

- o sistema consegue dizer qual e a preferencia do usuario e qual foi o modo realmente aplicado.

### Fase B - preferencia persistida por usuario

Objetivo:

- permitir que o usuario configure como prefere iniciar.

Checklist:

- adicionar preferencia persistida no perfil/configuracoes;
- permitir `chat_first`, `evidence_first` e opcionalmente `auto_recommended`;
- permitir `lembrar_ultimo_modo_usado`;
- expor o motivo quando a politica sobrescrever a preferencia.

Arquivos-alvo:

- `android/src/features/settings/SettingsExperienceSections.tsx`
- `android/src/features/settings/SettingsExperienceAiSection.tsx`
- `web/static/js/chat/chat_index_page.js`
- camada de persistencia/configuracao do usuario

Validacao minima:

- cobertura de persistencia da preferencia;
- cobertura de leitura no boot do workspace;
- garantia de que a preferencia nao burla hard rules.

Critico para concluir:

- o usuario consegue escolher como quer iniciar, mas a interface nao promete o que a politica nao pode cumprir.

### Fase C - workspace web com entrada configuravel

Objetivo:

- transformar o web do inspetor em workspace de duas entradas para o mesmo caso.

Checklist:

- adicionar seletor de modo ao iniciar nova inspecao;
- abrir o workspace no modo efetivo;
- permitir alternancia entre conversa e evidencias no mesmo caso;
- preservar `history.state` e URL quando a troca de modo for concern de navegacao;
- manter timeline, anexos, checklist e rascunho estruturado sincronizados.

Arquivos-alvo:

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_laudos.js`
- `web/static/js/chat/chat_painel_relatorio.js`

Validacao minima:

- deep link e reload continuam coerentes;
- troca de modo nao perde estado;
- historico continua apontando para o mesmo caso.

Critico para concluir:

- `chat_first` e `evidence_first` deixam de ser experiencias isoladas no web.

### Fase D - mobile com entrada configuravel

Objetivo:

- permitir escolha de inicio no mobile sem criar pipeline documental paralelo.

Checklist:

- abrir o caso com CTA de conversa ou evidencias;
- respeitar preferencia persistida do usuario;
- permitir alternancia no mesmo caso;
- integrar o modo guiado ao mesmo bundle de evidencias;
- registrar quando a autonomia cair para Mesa por criticidade.

Arquivos-alvo:

- `android/src/features/chat/useInspectorChatController.ts`
- `android/src/features/useInspectorRootConversationControllers.ts`
- `android/src/features/inspection/guidedInspection.ts`
- `android/src/features/inspection/useInspectorRootGuidedInspectionController.ts`

Validacao minima:

- testes focais de controllers de chat e guided inspection;
- garantia de que alternar o modo nao cria caso duplicado;
- garantia de que as evidencias entram no mesmo bundle.

Critico para concluir:

- o mobile inicia do jeito escolhido, mas continua produzindo o mesmo caso tecnico.

### Fase E - draft estruturado incremental

Objetivo:

- parar de depender da finalizacao como unico momento de montagem do laudo.

Checklist:

- manter draft estruturado incremental do caso;
- atualizar itens do checklist conforme novas evidencias entram;
- registrar `image_slots` resolvidos ou pendentes;
- expor faltas de evidencia antes da emissao.

Arquivos-alvo:

- `web/app/domains/chat/report_finalize_stream_shadow.py`
- `web/app/domains/chat/templates_ai.py`
- `web/app/domains/chat/gate_helpers.py`
- `web/nucleo/template_laudos.py`
- `web/nucleo/template_editor_word.py`

Validacao minima:

- laudo parcial continua consistente ao longo da coleta;
- faltantes aparecem antes da finalizacao;
- mesmo draft pode ser revisado pela Mesa.

Critico para concluir:

- o pipeline tecnico do laudo deixa de depender do modo de entrada.

### Fase F - gates unificados e conflito normativo

Objetivo:

- garantir que qualquer modo de entrada respeita a mesma seguranca de emissao.

Checklist:

- aplicar gates de completude por familia;
- aplicar criticidade por item;
- impedir `mobile_autonomous` em conflito grave;
- separar emissao aprovada de aprendizado elegivel;
- exigir `override_reason` em divergencia normativa relevante.

Arquivos-alvo:

- `web/app/domains/chat/gate_helpers.py`
- `web/nucleo/inspetor/confianca_ia.py`
- `web/app/domains/chat/learning_helpers.py`
- `web/app/domains/revisor/learning_api.py`

Validacao minima:

- conflito normativo nao entra em aprendizado automatico;
- autonomia cai para Mesa quando exigido;
- override humano continua auditavel.

Critico para concluir:

- o produto continua seguro mesmo com entrada mais flexivel.

### Fase G - rollout controlado e telemetria

Objetivo:

- ligar a funcionalidade sem perder rastreabilidade.

Checklist:

- ativar por allowlist;
- medir preferencia do usuario x modo efetivo;
- medir troca de modo por familia;
- medir gaps de evidencia por modo de entrada;
- medir divergencia IA-humano por familia e modo.

Arquivos-alvo:

- pontos de telemetria do web, mobile e backend do caso

Validacao minima:

- dashboards ou logs conseguem mostrar se o modo configuravel esta ajudando ou atrapalhando;
- rollback simples continua disponivel.

Critico para concluir:

- o rollout pode ser desacelerado sem reverter a espinha do laudo.

## Sequencia recomendada de commits

1. `inspection: add entry mode policy contract`
2. `inspection: persist user entry preference`
3. `inspetor-web: support configurable case entry`
4. `mobile: support configurable case entry`
5. `laudo: add incremental draft and unified gates`
6. `learning: block normative conflicts from automatic reuse`
7. `telemetry: track entry mode effectiveness`

## Pacote minimo de validacao por rodada

Rodar no minimo:

- recortes backend de `chat`, `gate`, `laudo` e `learning`;
- `web/tests/test_smoke.py`;
- testes focais do workspace do inspetor e suas abas;
- testes focais do mobile ligados a `chat`, `guidedInspection` e `settings`;
- validacao manual de um caso iniciado por conversa e outro iniciado por evidencias;
- validacao manual de troca de modo no mesmo caso;
- validacao manual de conflito normativo com override humano.

## Rollback

Rollback seguro deve permitir:

1. ocultar o seletor de modo configuravel;
2. voltar o produto para um modo default oficial;
3. manter os campos de estado sem uso, sem quebrar casos antigos;
4. preservar o draft estruturado e o bundle de evidencias;
5. manter a governanca normativa e o firewall de aprendizado ativos.

## Proximo passo recomendado

Comecar pela `Fase A`.

Se a equipe tentar abrir web e mobile ao mesmo tempo sem contrato de politica de entrada, o resultado tende a ser interface nova sobre estado inconsistente.
