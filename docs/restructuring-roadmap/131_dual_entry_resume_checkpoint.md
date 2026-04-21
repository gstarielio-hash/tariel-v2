# Inspecao - checkpoint oficial de retomada da entrada configuravel

Criado em `2026-04-06`.
Atualizado em `2026-04-18`.

## Estado atual

Status desta frente:

- `documentada`
- `fase A implementada no backend`
- `fase B implementada no backend e nos contratos mobile`
- `fase C concluida no web`
- `fase D concluida no fluxo atual`
- `fase E implementada para nr35_linha_vida, cbmgo, nr35_ponto_ancoragem, nr13_inspecao_caldeira, nr13_inspecao_vaso_pressao, nr20_prontuario_instalacoes_inflamaveis e nr10_prontuario_instalacoes_eletricas`
- `fase F implementada para nr35_linha_vida e cbmgo, com gates modelados em mesa_required para nr35_ponto_ancoragem, nr13_inspecao_caldeira, nr13_inspecao_vaso_pressao, nr20_prontuario_instalacoes_inflamaveis e nr10_prontuario_instalacoes_eletricas`
- `fase G implementada no backend com observabilidade local do rollout`

Isso significa:

- os documentos de arquitetura e governanca ja existem;
- o contrato do caso para `entry_mode_preference`, `entry_mode_effective` e `entry_mode_reason` ja existe;
- a persistencia do contrato no `Laudo`, a serializacao base e a precedencia minima ja foram implementadas;
- a preferencia persistida do usuario agora entra pelas configuracoes mobile existentes e novos casos ja herdam essa politica;
- o contrato mobile agora preserva `entry_mode_preference` e `remember_last_case_mode` no round-trip de settings;
- o web agora ja tem seletor de inicio na nova inspecao, bootstrap SSR com defaults do usuario, abertura inicial orientada pelo modo efetivo, nota visivel quando a politica do caso prevalece e reabertura coerente de laudos existentes pelo modo efetivo;
- o mobile agora expoe a preferencia de entrada nas settings, resolve o modo efetivo localmente e usa a inspecao guiada como entrada `evidence_first` para casos novos;
- o mobile agora persiste e retoma localmente o draft guiado por caso no cache de leitura;
- o mobile agora permite alternancia explicita entre chat e coleta guiada no mesmo caso, sem criar laudo duplicado;
- o mobile agora resolve o template guiado pelo `tipo_template` do caso e usa `padrao` quando a familia ainda nao foi definida, em vez de cair sempre no piloto `nr35_linha_vida`;
- o backend agora persiste um `report_pack_draft_json` por `laudo`, atualizado incrementalmente a partir do draft guiado, evidencias da thread e template vigente;
- as familias modeladas `nr35_linha_vida`, `cbmgo`, `nr35_ponto_ancoragem`, `nr13_inspecao_caldeira`, `nr13_inspecao_vaso_pressao`, `nr20_prontuario_instalacoes_inflamaveis` e `nr10_prontuario_instalacoes_eletricas` agora expoem `image_slots`, faltas de evidencia, candidato estruturado para `dados_formulario` e `final_validation_mode` antes da emissao;
- a finalizacao das familias allowlisted agora pode sair em `mobile_autonomous` com aprovacao direta quando os gates semanticos e o policy engine convergem para autonomia; `nr35_ponto_ancoragem`, `nr13_inspecao_caldeira`, `nr13_inspecao_vaso_pressao`, `nr20_prontuario_instalacoes_inflamaveis` e `nr10_prontuario_instalacoes_eletricas` ficam modeladas, mas permanecem em `mesa_required` neste checkpoint;
- o backend agora agrega observabilidade local do rollout, cobrindo preferencia x modo efetivo, troca de modo, gaps de evidencia, decisao final e divergencia IA-humano por familia/modo;
- o ponto de retomada correto passa a ser a expansao segura de familias/modelagem e a eventual superficie operacional de consulta.

## Fonte de verdade desta frente

Documentos canonicos:

1. `docs/restructuring-roadmap/127_semantic_report_pack_execution_plan.md`
2. `docs/restructuring-roadmap/128_normative_override_and_learning_governance.md`
3. `docs/restructuring-roadmap/129_dual_entry_configurable_inspection_roadmap.md`
4. `docs/restructuring-roadmap/130_dual_entry_implementation_checklist.md`
5. `PLANS.md`

## Ultima decisao consolidada

Decisao vigente em `2026-04-18`:

- o produto nao vai trocar `chat-first` por `evidence-first` de forma obrigatoria;
- o produto vai suportar `entrada configuravel` definida pelo usuario;
- tenant, familia documental, criticidade e hard safety podem restringir o modo efetivo;
- qualquer modo de entrada deve alimentar o mesmo caso tecnico e o mesmo pipeline de laudo;
- override humano continua separado de aprendizado elegivel;
- `mobile_autonomous` segue allowlisted por template e tenant; neste checkpoint, esta operacional para as familias modeladas `nr35_linha_vida` e `cbmgo`, enquanto `nr35_ponto_ancoragem`, `nr13_inspecao_caldeira`, `nr13_inspecao_vaso_pressao`, `nr20_prontuario_instalacoes_inflamaveis` e `nr10_prontuario_instalacoes_eletricas` entram apenas com espinha semantica e fallback fixo para `mesa_required`.

## Proximo passo exato

Retomar por aqui:

1. aguardar os dados reais da empresa para medir divergencia normativa e taxa de queda para Mesa nas familias modeladas;
2. enquanto os dados nao chegam, usar a consulta operacional do rollout para acompanhar as familias ja modeladas e escolher com calma a proxima expansao fora deste lote;
3. manter `nr35_ponto_ancoragem`, `nr13_inspecao_caldeira`, `nr13_inspecao_vaso_pressao`, `nr20_prontuario_instalacoes_inflamaveis` e `nr10_prontuario_instalacoes_eletricas` em `mesa_required` ate existir telemetria suficiente para discutir autonomia;
4. usar a consulta operacional do rollout como leitura principal quando a amostra real estiver disponivel, antes de qualquer ampliacao de allowlist.

Nao pular para:

- rollout amplo sem telemetria;
- autonomia mobile para familias nao modeladas;
- recomendacao automatica por familia;

antes de validar a expansao alem das familias atuais.

## Fase atual por status

### Fase A - contrato de politica de entrada

- `status`: concluida
- `owner esperado`: backend/estado do caso
- `saida obrigatoria`: contrato canonico de preferencia e modo efetivo

### Fase B - preferencia persistida por usuario

- `status`: concluida
- `dependencia`: Fase A

### Fase C - workspace web com entrada configuravel

- `status`: concluida
- `dependencia`: Fase A e Fase B

### Fase D - mobile com entrada configuravel

- `status`: concluida no fluxo atual
- `dependencia`: Fase A e Fase B

### Fase E - draft estruturado incremental

- `status`: implementada para `nr35_linha_vida`, `cbmgo`, `nr35_ponto_ancoragem`, `nr13_inspecao_caldeira`, `nr13_inspecao_vaso_pressao`, `nr20_prontuario_instalacoes_inflamaveis` e `nr10_prontuario_instalacoes_eletricas`
- `dependencia`: Fase A

### Fase F - gates unificados e conflito normativo

- `status`: implementada para `nr35_linha_vida` e `cbmgo`; `nr35_ponto_ancoragem`, `nr13_inspecao_caldeira`, `nr13_inspecao_vaso_pressao`, `nr20_prontuario_instalacoes_inflamaveis` e `nr10_prontuario_instalacoes_eletricas` entraram com gates modelados e `final_validation_mode` fixado em `mesa_required`
- `dependencia`: Fase E e documento `128`

### Fase G - rollout controlado e telemetria

- `status`: implementada no backend com observabilidade local
- `dependencia`: Fases A-F

## Arquivos a abrir primeiro na retomada

Backend:

- `web/app/domains/chat/report_pack_helpers.py`
- `web/app/domains/chat/gate_helpers.py`
- `web/app/domains/chat/laudo_service.py`
- `web/app/v2/policy/engine.py`
- `web/app/v2/report_pack_rollout_metrics.py`
- `web/app/shared/db/models_laudo.py`
- `web/alembic/versions/9c4b6d1e2f3a_laudo_report_pack_draft.py`
- `web/app/domains/chat/laudo_state_helpers.py`
- `web/app/domains/chat/chat_runtime.py`
- `web/app/domains/chat/schemas.py`
- `web/app/domains/chat/chat_stream_support.py`
- `web/app/domains/chat/auth_mobile_support.py`

Depois:

- `web/tests/test_semantic_report_pack_nr35_autonomy.py`
- `web/tests/test_semantic_report_pack_cbmgo_autonomy.py`
- `web/tests/test_semantic_report_pack_nr35_anchor_modeling.py`
- `web/tests/test_semantic_report_pack_nr13_vaso_pressao_modeling.py`
- `web/tests/test_semantic_report_pack_nr13_caldeira_modeling.py`
- `web/tests/test_semantic_report_pack_nr20_prontuario_modeling.py`
- `web/tests/test_semantic_report_pack_nr10_prontuario_modeling.py`
- `web/tests/test_report_pack_rollout_metrics.py`
- `web/tests/test_v2_policy_engine.py`
- `web/tests/test_inspection_entry_mode_phase_d_mobile.py`
- `android/src/features/chat/useInspectorChatController.ts`
- `android/src/features/inspection/guidedInspection.ts`
- `android/src/features/chat/buildThreadContextState.ts`

## Riscos conhecidos antes de implementar

- abrir `chat_first` e `evidence_first` como experiencias separadas;
- duplicar estado do caso entre web e mobile;
- confundir preferencia do usuario com autorizacao normativa;
- permitir que um modo tenha gates diferentes do outro;
- misturar override humano com aprendizado automatico;
- ampliar `mobile_autonomous` para familias sem `report pack` modelado e sem telemetria minima;
- tratar a agregacao local do rollout como substituto definitivo de superficie operacional se o time ainda precisar de endpoint/dashboard dedicado.

## Regras de retomada

Ao retomar esta frente:

1. abrir este checkpoint;
2. abrir `129_dual_entry_configurable_inspection_roadmap.md`;
3. abrir `130_dual_entry_implementation_checklist.md`;
4. confirmar se a retomada e de rollout do piloto (`Fase G`) ou de expansao de familias sobre a mesma espinha;
5. so depois abrir os hotspots de codigo.

## Como atualizar este checkpoint

Ao final de cada slice implementado, atualizar:

- `Atualizado em`
- `Ultima decisao consolidada`
- `Fase atual por status`
- `Arquivos a abrir primeiro na retomada`
- `Log de execucao`

## Log de execucao

### 2026-04-18 - expansao segura para nr35_ponto_ancoragem

- alteracao de escopo consolidada:
  - `nr35_ponto_ancoragem` entrou na espinha semantica do `report pack` sem ampliar a allowlist de `mobile_autonomous`
- codigo funcional desta frente:
  - `web/app/domains/chat/report_pack_helpers.py`
  - `web/tests/test_semantic_report_pack_nr35_anchor_modeling.py`
- comportamento novo:
  - a familia `nr35_ponto_ancoragem` agora gera `items`, `image_slots`, `structured_data_candidate` canonico e gates dedicados
  - a finalizacao continua indo para `mesa_required`, mesmo com caso completo e evidencias suficientes
- validacao:
  - `PYTHONPATH=. ./.venv-linux/bin/python -m pytest -q tests/test_semantic_report_pack_nr35_anchor_modeling.py tests/test_semantic_report_pack_nr35_autonomy.py tests/test_semantic_report_pack_catalog_fallback.py tests/test_report_pack_rollout_metrics.py`
- proximo passo:
  - observar a queda para Mesa da nova familia modelada e escolher a primeira familia fora de `NR35` para entrar na mesma espinha

### 2026-04-18 - expansao segura para nr13_inspecao_caldeira

- alteracao de escopo consolidada:
  - `nr13_inspecao_caldeira` entrou na espinha semantica do `report pack` sem ampliar a allowlist de `mobile_autonomous`
- codigo funcional desta frente:
  - `web/app/domains/chat/report_pack_helpers.py`
  - `web/tests/test_semantic_report_pack_nr13_caldeira_modeling.py`
- comportamento novo:
  - a familia `nr13_inspecao_caldeira` agora gera `items`, `image_slots`, `structured_data_candidate` canonico e gates dedicados
  - a finalizacao continua indo para `mesa_required`, mesmo com caso completo e evidencias suficientes
- validacao:
  - `PYTHONPATH=. ./.venv-linux/bin/python -m pytest -q tests/test_semantic_report_pack_nr13_caldeira_modeling.py tests/test_semantic_report_pack_nr35_anchor_modeling.py tests/test_semantic_report_pack_nr35_autonomy.py tests/test_semantic_report_pack_cbmgo_autonomy.py tests/test_semantic_report_pack_catalog_fallback.py tests/test_report_pack_rollout_metrics.py tests/test_v2_policy_engine.py`
  - `PYTHONPATH=. ./.venv-linux/bin/python -m mypy app/domains/chat/report_pack_helpers.py`
- proximo passo:
  - seguir expandindo familias catalogadas em `mesa_required` enquanto os dados reais da empresa nao chegam para calibrar a autonomia

### 2026-04-18 - expansao segura para nr13_inspecao_vaso_pressao

- alteracao de escopo consolidada:
  - `nr13_inspecao_vaso_pressao` entrou na espinha semantica do `report pack` sem ampliar a allowlist de `mobile_autonomous`
- codigo funcional desta frente:
  - `web/app/domains/chat/report_pack_helpers.py`
  - `web/tests/test_semantic_report_pack_nr13_vaso_pressao_modeling.py`
  - `web/tests/test_semantic_report_pack_catalog_fallback.py`
- comportamento novo:
  - a familia `nr13_inspecao_vaso_pressao` agora gera `items`, `image_slots`, `structured_data_candidate` canonico e gates dedicados
  - a finalizacao continua indo para `mesa_required`, mesmo com caso completo e evidencias suficientes
  - o fallback catalogado permanece coberto para familias nao modeladas, sem depender mais de `nr13_inspecao_vaso_pressao`
- validacao:
  - `PYTHONPATH=. ./.venv-linux/bin/python -m pytest -q tests/test_semantic_report_pack_nr13_vaso_pressao_modeling.py tests/test_semantic_report_pack_nr13_caldeira_modeling.py tests/test_semantic_report_pack_nr35_anchor_modeling.py tests/test_semantic_report_pack_nr35_autonomy.py tests/test_semantic_report_pack_cbmgo_autonomy.py tests/test_semantic_report_pack_catalog_fallback.py tests/test_report_pack_rollout_metrics.py tests/test_v2_policy_engine.py`
  - `PYTHONPATH=. ./.venv-linux/bin/python -m mypy app/domains/chat/report_pack_helpers.py`
- proximo passo:
  - seguir com `nr20_prontuario_instalacoes_inflamaveis` e `nr10_prontuario_instalacoes_eletricas` no mesmo modo conservador

### 2026-04-18 - expansao segura para nr20_prontuario_instalacoes_inflamaveis

- alteracao de escopo consolidada:
  - `nr20_prontuario_instalacoes_inflamaveis` entrou na espinha semantica do `report pack` sem ampliar a allowlist de `mobile_autonomous`
- codigo funcional desta frente:
  - `web/app/domains/chat/report_pack_helpers.py`
  - `web/tests/test_semantic_report_pack_nr20_prontuario_modeling.py`
- comportamento novo:
  - a familia `nr20_prontuario_instalacoes_inflamaveis` agora gera `items`, `image_slots`, `structured_data_candidate` canonico e gates dedicados
  - a finalizacao continua indo para `mesa_required`, mesmo com caso completo e rastreabilidade documental suficiente
- validacao:
  - `PYTHONPATH=. ./.venv-linux/bin/python -m pytest -q tests/test_semantic_report_pack_nr20_prontuario_modeling.py tests/test_semantic_report_pack_nr13_vaso_pressao_modeling.py tests/test_semantic_report_pack_catalog_fallback.py tests/test_report_pack_rollout_metrics.py tests/test_v2_policy_engine.py`
  - `PYTHONPATH=. ./.venv-linux/bin/python -m pytest -q tests/test_regras_rotas_criticas.py -k 'finalizacao_catalogada_persiste_laudo_output_canonico_nr20_prontuario'`
  - `PYTHONPATH=. ./.venv-linux/bin/python -m mypy app/domains/chat/report_pack_helpers.py`
- proximo passo:
  - seguir com `nr10_prontuario_instalacoes_eletricas` no mesmo modo conservador

### 2026-04-18 - expansao segura para nr10_prontuario_instalacoes_eletricas

- alteracao de escopo consolidada:
  - `nr10_prontuario_instalacoes_eletricas` entrou na espinha semantica do `report pack` sem ampliar a allowlist de `mobile_autonomous`
- codigo funcional desta frente:
  - `web/app/domains/chat/report_pack_helpers.py`
  - `web/tests/test_semantic_report_pack_nr10_prontuario_modeling.py`
- comportamento novo:
  - a familia `nr10_prontuario_instalacoes_eletricas` agora gera `items`, `image_slots`, `structured_data_candidate` canonico e gates dedicados
  - a finalizacao continua indo para `mesa_required`, mesmo com caso completo e rastreabilidade documental suficiente
- validacao:
  - `PYTHONPATH=. ./.venv-linux/bin/python -m pytest -q tests/test_semantic_report_pack_nr10_prontuario_modeling.py tests/test_semantic_report_pack_nr20_prontuario_modeling.py tests/test_semantic_report_pack_nr13_vaso_pressao_modeling.py tests/test_semantic_report_pack_catalog_fallback.py tests/test_report_pack_rollout_metrics.py tests/test_v2_policy_engine.py`
  - `PYTHONPATH=. ./.venv-linux/bin/python -m pytest -q tests/test_regras_rotas_criticas.py -k 'finalizacao_catalogada_persiste_laudo_output_canonico_nr10_prontuario'`
  - `PYTHONPATH=. ./.venv-linux/bin/python -m mypy app/domains/chat/report_pack_helpers.py`
- proximo passo:
  - usar os dados reais da empresa e a consulta operacional do rollout para decidir a proxima familia ou eventual discussao de autonomia

### 2026-04-06 - checkpoint inicial desta frente

- documentos criados:
  - `127_semantic_report_pack_execution_plan.md`
  - `128_normative_override_and_learning_governance.md`
  - `129_dual_entry_configurable_inspection_roadmap.md`
  - `130_dual_entry_implementation_checklist.md`
  - `131_dual_entry_resume_checkpoint.md`
- alteracao de orientacao consolidada:
  - `entrada configuravel` substitui a ideia de forcar `evidence-first`
- codigo funcional desta frente:
  - nenhum ainda
- proximo passo:
  - iniciar `Fase A`

### 2026-04-06 - fase A implementada no backend

- contrato persistido no modelo `Laudo`:
  - `entry_mode_preference`
  - `entry_mode_effective`
  - `entry_mode_reason`
- precedencia minima implementada:
  - `hard_safety_rule`
  - `family_required_mode`
  - `tenant_policy`
  - `role_policy`
  - `user_preference`
  - `last_case_mode`
  - `auto_recommended`
  - `default_product_fallback`
- hotspots alterados:
  - `web/app/shared/db/contracts.py`
  - `web/app/shared/db/models_laudo.py`
  - `web/app/domains/chat/chat_runtime.py`
  - `web/app/domains/chat/laudo_state_helpers.py`
  - `web/app/domains/chat/session_helpers.py`
  - `web/app/domains/chat/schemas.py`
  - `web/app/domains/chat/laudo_service.py`
  - `web/app/domains/chat/chat_stream_support.py`
  - `web/app/domains/chat/laudo.py`
  - `web/app/domains/cliente/portal_bridge.py`
  - `web/app/domains/cliente/chat_routes.py`
  - `web/alembic/versions/6f2b1c4d8e9a_laudo_entry_mode_contract.py`
- testes adicionados:
  - `web/tests/test_inspection_entry_mode_phase_a.py`
- limite deste slice:
  - nenhuma UI nova ainda
  - nenhuma preferencia persistida por usuario ainda
- proximo passo:
  - iniciar `Fase B`

### 2026-04-06 - fase B implementada no backend e no contrato mobile

- preferencia persistida reutiliza `PreferenciaMobileUsuario.experiencia_ia_json`
- configuracao mobile agora aceita:
  - `entry_mode_preference`
  - `remember_last_case_mode`
- boot do caso agora herda preferencia persistida quando nao houver override explicito na requisicao
- `last_case_mode` passa a ser recuperado do ultimo `Laudo` do usuario quando `remember_last_case_mode=true`
- fluxo do chat sem `laudo` ativo tambem passou a respeitar a preferencia persistida
- contrato Android atualizado para preservar os novos campos no `round-trip` local/remoto das settings
- hotspots alterados:
  - `web/app/domains/chat/auth_contracts.py`
  - `web/app/domains/chat/auth_mobile_support.py`
  - `web/app/domains/chat/laudo_service.py`
  - `web/app/domains/chat/chat_stream_support.py`
  - `android/src/types/mobile.ts`
  - `android/src/features/settings/criticalSettings.ts`
  - `android/src/settings/schema/types.ts`
  - `android/src/settings/schema/defaults.ts`
  - `android/src/settings/repository/settingsRemoteAdapter.ts`
  - `android/src/settings/migrations/migrateSettingsDocument.ts`
- testes adicionados:
  - `web/tests/test_inspection_entry_mode_phase_b.py`
- verificacao executada:
  - `python3 -m py_compile web/app/domains/chat/auth_contracts.py web/app/domains/chat/auth_mobile_support.py web/app/domains/chat/laudo_service.py web/app/domains/chat/chat_stream_support.py web/tests/test_inspection_entry_mode_phase_b.py`
  - `python3 -m pytest -q web/tests/test_inspection_entry_mode_phase_b.py web/tests/test_inspection_entry_mode_phase_a.py`
  - `python3 -m pytest -q web/tests/test_portais_acesso_critico.py -k 'test_login_mobile_inspetor_retorna_token_e_bootstrap_funciona'`
  - `npm run typecheck` em `android/`
- limite deste slice:
  - nenhuma UI nova de escolha de modo no web
  - nenhuma UI nova de escolha de modo nas settings mobile
- proximo passo:
  - iniciar `Fase C`

### 2026-04-06 - fase C concluida no web

- o portal SSR agora injeta no HTML:
  - `entry_mode_preference_default`
  - `entry_mode_remember_last_case_mode`
  - `entry_mode_last_case_mode`
- o modal `Nova Inspecao` agora permite escolher:
  - `chat_first`
  - `evidence_first`
  - `auto_recommended`
- a criacao de laudo no web agora envia `entry_mode_preference` junto do formulario da inspecao
- o workspace passa a:
  - abrir em `conversa` quando o modo efetivo for `chat_first`
  - abrir em `anexos` quando o modo efetivo for `evidence_first`
  - mostrar nota explicando o modo efetivo e o motivo do override quando houver
- cards do portal e da sidebar agora propagam:
  - `entry_mode_preference`
  - `entry_mode_effective`
  - `entry_mode_reason`
- reabrir um laudo pelo portal, sidebar, reload ou `popstate` agora respeita o modo efetivo do caso quando nao houver `?aba=` explicita
- a copy do workspace passa a ficar orientada por modo
- o composer no web continua unico, mas agora respeita o fluxo `evidence_first` no slice inicial
- testes adicionados:
  - `web/tests/test_inspection_entry_mode_phase_c_web.py`
- validacao executada:
  - `node --check web/static/js/inspetor/modals.js`
  - `node --check web/static/js/chat/chat_index_page.js`
  - `node --check web/static/js/chat/chat_painel_laudos.js`
  - `python3 -m py_compile web/app/domains/chat/auth_mobile_support.py web/tests/test_inspection_entry_mode_phase_c_web.py`
  - `python3 -m pytest -q web/tests/test_inspection_entry_mode_phase_c_web.py web/tests/test_inspection_entry_mode_phase_b.py web/tests/test_inspection_entry_mode_phase_a.py`
  - `10 passed`
- limite atual deste slice:
  - o mobile ainda nao recebeu a UI equivalente
- proximo passo:
  - iniciar a `Fase D`

### 2026-04-06 - fase D iniciada no mobile

- as settings mobile agora expoem:
  - `entryModePreference`
  - `rememberLastCaseMode`
- o app mobile agora resolve `entry_mode_effective` localmente a partir de:
  - preferencia do inspetor
  - ultimo caso quando `rememberLastCaseMode=true`
  - estado salvo do caso ativo quando existir
- o fluxo `handleAbrirNovoChat` agora respeita o modo efetivo:
  - `chat_first` continua abrindo conversa livre
  - `evidence_first` passa a iniciar o draft de `inspecao guiada`
- o card de contexto do workspace mobile agora ajusta copy, spotlight e CTA do estado vazio conforme o modo efetivo
- hotspots alterados:
  - `android/src/features/inspection/inspectionEntryMode.ts`
  - `android/src/features/inspection/useInspectorRootGuidedInspectionController.ts`
  - `android/src/features/chat/useInspectorChatController.ts`
  - `android/src/features/chat/useInspectorRootChatController.ts`
  - `android/src/features/useInspectorRootConversationControllers.ts`
  - `android/src/features/chat/buildThreadContextState.ts`
  - `android/src/features/common/inspectorDerivedStateTypes.ts`
  - `android/src/features/buildInspectorRootFinalScreenState.ts`
  - `android/src/features/settings/useInspectorSettingsBindings.ts`
  - `android/src/features/settings/SettingsExperienceAiSection.tsx`
  - `android/src/features/settings/settingsDrawerBuilderTypes.ts`
  - `android/src/features/settings/buildInspectorSettingsDrawerSections.ts`
  - `android/src/features/settings/buildInspectorRootSettingsDrawerProps.ts`
  - `android/src/features/settings/buildInspectorRootSettingsDrawerState.ts`
- testes adicionados ou atualizados:
  - `android/src/features/inspection/inspectionEntryMode.test.ts`
  - `android/src/features/inspection/useInspectorRootGuidedInspectionController.test.ts`
  - `android/src/features/chat/buildThreadContextState.test.ts`
  - `android/src/features/settings/useInspectorSettingsBindings.test.ts`
  - `android/src/features/chat/useInspectorRootChatController.test.ts`
- validacao executada:
  - `npm run typecheck` em `android/`
  - `npm test -- --runInBand src/features/inspection/inspectionEntryMode.test.ts src/features/inspection/useInspectorRootGuidedInspectionController.test.ts src/features/chat/buildThreadContextState.test.ts src/features/settings/useInspectorSettingsBindings.test.ts src/features/chat/useInspectorRootChatController.test.ts`
  - `15 passed`
- limite atual deste slice:
  - ainda nao existe persistencia canonica do draft guiado fora do cache local do aparelho
  - o fluxo guiado continua piloto de `nr35_linha_vida`
- proximo passo:
  - continuar a `Fase D` pela retomada/reabertura coerente do caso mobile

### 2026-04-06 - fase D mobile com retomada de caso e alternancia explicita

- o cache de leitura mobile agora guarda `guidedInspectionDrafts` por caso
- ao reabrir um laudo com `entry_mode_effective=evidence_first`, o app:
  - restaura o draft guiado do caso quando houver cache local
  - mantem a orientacao `evidence_first` no card de contexto mesmo sem draft restaurado
- o card de contexto agora oferece alternancia explicita no mesmo caso:
  - `Retomar coleta guiada`
  - `Abrir coleta guiada`
  - `Voltar ao chat`
- `handleAbrirColetaGuiadaAtual` reaproveita o mesmo `laudoId` e nao cria um caso paralelo
- hotspots alterados:
  - `android/src/features/common/readCacheTypes.ts`
  - `android/src/features/common/inspectorLocalPersistence.ts`
  - `android/src/features/common/useInspectorRootPersistenceEffects.ts`
  - `android/src/features/chat/useInspectorChatController.ts`
  - `android/src/features/chat/useInspectorRootChatController.ts`
  - `android/src/features/chat/buildThreadContextState.ts`
  - `android/src/features/common/inspectorDerivedStateTypes.ts`
  - `android/src/features/buildInspectorRootFinalScreenState.ts`
  - `android/src/features/inspection/useInspectorRootGuidedInspectionController.ts`
- testes adicionados ou atualizados:
  - `android/src/features/chat/useInspectorChatController.entryMode.test.ts`
  - `android/src/features/chat/buildThreadContextState.test.ts`
  - `android/src/features/common/inspectorLocalPersistence.test.ts`
- validacao executada:
  - `npm run typecheck` em `android/`
  - `npm test -- --runInBand src/features/chat/useInspectorChatController.entryMode.test.ts src/features/chat/buildThreadContextState.test.ts src/features/inspection/useInspectorRootGuidedInspectionController.test.ts src/features/inspection/inspectionEntryMode.test.ts src/features/settings/useInspectorSettingsBindings.test.ts src/features/chat/useInspectorRootChatController.test.ts src/features/common/inspectorLocalPersistence.test.ts`
  - `25 passed`
- limite atual deste slice:
  - ainda nao existe persistencia canonica do draft guiado entre dispositivos
  - o modo guiado continua acoplado ao piloto `nr35_linha_vida`
- proximo passo:
  - decidir a persistencia canonica do draft guiado e generalizar o `evidence_first` para familias alem do piloto

### 2026-04-06 - fase D mobile com resolucao de template por familia documental

- o motor de `inspecao guiada` mobile agora conhece familias documentais alem do piloto:
  - `padrao`
  - `avcb`
  - `cbmgo`
  - `nr12maquinas`
  - `nr13`
  - `nr35_linha_vida`
  - `pie`
  - `rti`
  - `spda`
- o fallback sem `tipo_template` definido deixou de abrir o checklist de `NR35` e agora cria um draft generico `padrao`
- casos `evidence_first` reabertos sem draft cacheado agora iniciam checklist coerente com o `tipo_template` do caso
- a copy do card de contexto do chat deixou de anunciar `NR35` como atalho fixo do modo guiado
- hotspots alterados:
  - `android/src/features/inspection/guidedInspection.ts`
  - `android/src/features/inspection/useInspectorRootGuidedInspectionController.ts`
  - `android/src/features/chat/useInspectorChatController.ts`
  - `android/src/features/chat/buildThreadContextState.ts`
- testes adicionados ou atualizados:
  - `android/src/features/inspection/guidedInspection.test.ts`
  - `android/src/features/inspection/useInspectorRootGuidedInspectionController.test.ts`
  - `android/src/features/chat/useInspectorChatController.entryMode.test.ts`
  - `android/src/features/chat/buildThreadContextState.test.ts`
- validacao executada:
  - `npm run typecheck` em `android/`
  - `npm test -- --runInBand src/features/inspection/guidedInspection.test.ts src/features/inspection/useInspectorRootGuidedInspectionController.test.ts src/features/chat/useInspectorChatController.entryMode.test.ts src/features/chat/buildThreadContextState.test.ts src/features/chat/useInspectorRootChatController.test.ts`
  - `18 passed`
- limite atual deste slice:
  - a selecao de template guiado ainda nasce localmente no app
  - o draft guiado continua sem persistencia canonica no backend
- proximo passo:
  - decidir e implementar a persistencia canonica do draft guiado por caso no backend ou no snapshot tecnico do caso

### 2026-04-06 - fase D mobile com persistencia canonica do draft guiado por laudo

- o backend agora persiste o draft guiado no `laudo` via `guided_inspection_draft_json`
- o mobile ganhou endpoint dedicado para salvar o draft canonico:
  - `PUT /app/api/mobile/laudo/{laudo_id}/guided-inspection-draft`
- `status` e `mensagens` do laudo agora fazem round-trip de `guided_inspection_draft`, permitindo retomada entre reinstalacoes e entre dispositivos do mesmo inspetor
- o app deixou de apagar o draft cacheado ao sair do modo guiado e agora:
  - preserva o rascunho local por caso
  - promove o draft de `rascunho` para o `laudo` real quando o caso ganha `laudo_id`
  - sincroniza o payload canonico com o backend quando o caso ja existe
- hotspots alterados:
  - `web/app/shared/db/models_laudo.py`
  - `web/alembic/versions/8d2c4f6a1b3e_laudo_guided_inspection_draft.py`
  - `web/app/domains/chat/schemas.py`
  - `web/app/domains/chat/laudo_state_helpers.py`
  - `web/app/domains/chat/laudo_service.py`
  - `web/app/domains/chat/chat_service.py`
  - `web/app/domains/chat/auth_mobile_routes.py`
  - `web/tests/test_inspection_entry_mode_phase_d_mobile.py`
  - `android/src/types/mobile.ts`
  - `android/src/config/chatApi.ts`
  - `android/src/config/api.ts`
  - `android/src/config/chatApi.test.ts`
  - `android/src/features/inspection/guidedInspection.ts`
  - `android/src/features/chat/useInspectorChatController.ts`
  - `android/src/features/chat/useInspectorChatController.entryMode.test.ts`
- testes adicionados ou atualizados:
  - `web/tests/test_inspection_entry_mode_phase_d_mobile.py`
  - `android/src/config/chatApi.test.ts`
  - `android/src/features/chat/useInspectorChatController.entryMode.test.ts`
- validacao executada:
  - `python3 -m py_compile web/app/domains/chat/auth_mobile_routes.py web/app/domains/chat/chat_service.py web/app/domains/chat/laudo_service.py web/app/domains/chat/laudo_state_helpers.py web/app/domains/chat/schemas.py web/app/shared/db/models_laudo.py`
  - `python3 -m pytest -q web/tests/test_inspection_entry_mode_phase_c_web.py web/tests/test_inspection_entry_mode_phase_d_mobile.py`
  - `npm run typecheck` em `android/`
  - `npm test -- --runInBand src/features/inspection/guidedInspection.test.ts src/features/chat/useInspectorChatController.entryMode.test.ts src/config/chatApi.test.ts`
  - `5 passed` no recorte web e `13 passed` no recorte mobile
- limite atual deste slice:
  - o modo guiado ainda nao alimenta explicitamente o mesmo bundle canonico de evidencias do caso
  - a queda para Mesa por criticidade ainda nao fica registrada como parte do fluxo guiado
- proximo passo:
  - integrar o modo guiado ao mesmo bundle de evidencias do caso e registrar a transicao para Mesa quando a politica exigir

### 2026-04-06 - fase D mobile com bundle canonico do caso e mesa handoff no draft guiado

- o `chat` mobile agora envia `guided_inspection_draft` e `guided_inspection_context` no mesmo request do caso
- o backend passou a fundir esse contexto no `guided_inspection_draft_json` do `laudo`, sem criar pipeline paralelo:
  - `evidence_bundle_kind=case_thread`
  - `evidence_refs[]` com `message_id`, etapa e tipo de anexo da propria thread do caso
  - `mesa_handoff` quando a politica vigente do caso retorna `review_mode=mesa_required`
- o app mobile agora mescla o draft remoto com o draft local ao reabrir o caso, preservando progresso local sem perder `evidence_refs` e `mesa_handoff` gravados no backend
- o card de contexto da thread guiada passou a expor:
  - quantidade de evidencias vinculadas ao bundle canonico do caso
  - estado de `Mesa requerida` quando o handoff ja foi registrado
- hotspots alterados:
  - `web/app/domains/chat/schemas.py`
  - `web/app/domains/chat/laudo_state_helpers.py`
  - `web/app/domains/chat/chat_stream_support.py`
  - `web/tests/test_inspection_entry_mode_phase_d_mobile.py`
  - `android/src/types/mobile.ts`
  - `android/src/config/chatApi.ts`
  - `android/src/config/chatApi.test.ts`
  - `android/src/features/inspection/guidedInspection.ts`
  - `android/src/features/inspection/guidedInspection.test.ts`
  - `android/src/features/chat/messageSendFlows.ts`
  - `android/src/features/chat/useInspectorChatController.ts`
  - `android/src/features/chat/useInspectorChatController.entryMode.test.ts`
  - `android/src/features/chat/buildThreadContextState.ts`
  - `android/src/features/chat/buildThreadContextState.test.ts`
- validacao executada:
  - `python3 -m py_compile web/app/domains/chat/schemas.py web/app/domains/chat/laudo_state_helpers.py web/app/domains/chat/chat_stream_support.py web/tests/test_inspection_entry_mode_phase_d_mobile.py`
  - `python3 -m pytest -q web/tests/test_inspection_entry_mode_phase_d_mobile.py`
  - `npm run typecheck` em `android/`
  - `npm test -- --runInBand src/features/inspection/guidedInspection.test.ts src/config/chatApi.test.ts src/features/chat/useInspectorChatController.entryMode.test.ts src/features/chat/buildThreadContextState.test.ts`
  - `3 passed` no recorte web e `22 passed` no recorte mobile
- limite atual deste slice:
  - a queda para Mesa ainda fica ancorada no `review_mode` vigente do policy engine, nao em criticidade por item
  - o draft estruturado incremental com `image_slots` e faltas explicitas de evidencia ainda nao existe
- proximo passo:
  - abrir a `Fase E` com draft estruturado incremental, `image_slots`, faltas de evidencia e pre-materializacao antes da emissao

### 2026-04-06 - fases E/F em piloto com report pack incremental e full automatico allowlisted

- o backend ganhou `report_pack_draft_json` no `laudo` como estado canonico incremental do piloto
- o helper `web/app/domains/chat/report_pack_helpers.py` agora modela o piloto `nr35_linha_vida` com:
  - `items` estruturados por componente
  - `image_slots` resolvidos ou pendentes
  - `missing_evidence`
  - `structured_data_candidate`
  - `final_validation_mode`
- `gate_qualidade` passou a usar esse draft incremental quando a familia esta modelada, expondo faltas semanticas antes da emissao
- a finalizacao agora tenta materializar `dados_formulario` a partir do draft canonico antes de recorrer ao pipeline legado de geracao estruturada
- o policy engine ganhou o modo `mobile_autonomous` para familias allowlisted quando:
  - o template esta modelado
  - o `entry_mode_effective` foi `evidence_first`
  - os `image_slots` obrigatorios estao completos
  - o checklist critico esta fechado
  - o conflito normativo estimado segue abaixo do threshold do piloto
- no piloto allowlisted, a rota de finalizacao aprova direto o caso quando o policy engine libera `mobile_autonomous`; fora disso, o fallback continua sendo `mesa_required`
- a compatibilidade publica da Mesa foi estabilizada: a API continua devolvendo `reviewer_case_view`, mas com envelope publico saneado para nao divergir entre `policy off` e `policy on`, enquanto a projeção completa segue em `request.state`
- hotspots alterados:
  - `web/app/shared/db/models_laudo.py`
  - `web/alembic/versions/9c4b6d1e2f3a_laudo_report_pack_draft.py`
  - `web/app/domains/chat/report_pack_helpers.py`
  - `web/app/domains/chat/gate_helpers.py`
  - `web/app/domains/chat/chat_service.py`
  - `web/app/domains/chat/laudo_service.py`
  - `web/app/domains/chat/chat_stream_support.py`
  - `web/app/v2/runtime.py`
  - `web/app/v2/policy/models.py`
  - `web/app/v2/policy/engine.py`
  - `web/app/domains/revisor/document_boundary.py`
  - `web/app/domains/revisor/mesa_api.py`
  - `web/nucleo/inspetor/confianca_ia.py`
  - `web/tests/test_semantic_report_pack_nr35_autonomy.py`
  - `web/tests/test_v2_policy_engine.py`
- validacao executada:
  - `python3 -m py_compile web/app/domains/revisor/document_boundary.py web/app/domains/revisor/mesa_api.py`
  - `python3 -m pytest -q web/tests/test_v2_policy_engine.py::test_pacote_mesa_com_policy_engine_preserva_payload_publico web/tests/test_v2_reviewdesk_projection.py`
  - `python3 -m pytest -q web/tests/test_semantic_report_pack_nr35_autonomy.py web/tests/test_v2_policy_engine.py web/tests/test_inspection_entry_mode_phase_d_mobile.py`
  - `python3 -m pytest -q web/tests/test_regras_rotas_criticas.py -k "gate_qualidade or finalizar or status_relatorio"`
  - `python3 -m pytest -q web/tests/test_v2_document_hard_gate.py web/tests/test_v2_document_hard_gate_enforce.py web/tests/test_v2_document_hard_gate_summary.py`
  - total deste recorte: `34 passed`
- limite atual deste slice:
  - o `full automatico` esta fechado apenas para o piloto allowlisted `nr35_linha_vida`
  - a queda para Mesa ainda usa estimativa heuristica de conflito, nao criticidade normativa fina por item
  - `report packs` de outras familias ainda nao foram modelados
- proximo passo:
  - abrir a `Fase G` com rollout controlado, telemetria e criterio de expansao da allowlist

### 2026-04-06 - expansao para cbmgo e Fase G com observabilidade local

- a allowlist default de autonomia mobile agora cobre `nr35_linha_vida` e `cbmgo`, e o policy engine passou a aceitar restricao adicional por tenant via `TARIEL_V2_MOBILE_AUTONOMY_TENANTS`
- o `report_pack` de `cbmgo` agora foi modelado no backend com:
  - `image_slots` obrigatorios
  - leitura incremental do `dados_formulario` estruturado
  - gate semantico que continua permitindo queda simples para `mesa_required` quando houver `NC`, conflito ou lacuna estrutural
- o gate de qualidade passou a dispensar resposta previa da IA quando o `report pack` ja materializou o formulario canonico, destravando o fluxo `evidence_first` puro nas familias modeladas
- a finalizacao guiada passou a considerar mensagens `HUMANO_INSP` como entrada valida para o fallback de geracao estruturada, reduzindo dependencia do chat tradicional
- o backend ganhou `web/app/v2/report_pack_rollout_metrics.py`, agregando:
  - preferencia do usuario x modo efetivo
  - troca de modo observada
  - gaps de evidencia
  - decisao final (`mobile_autonomous` x `mesa_required`)
  - divergencia IA-humano por familia/modo no que for comparavel
- a decisao de review da Mesa agora tambem alimenta essa observabilidade, reutilizando o `report_pack_draft_json` do caso
- hotspots alterados:
  - `web/app/v2/runtime.py`
  - `web/app/v2/policy/engine.py`
  - `web/app/v2/report_pack_rollout_metrics.py`
  - `web/app/domains/chat/report_pack_helpers.py`
  - `web/app/domains/chat/gate_helpers.py`
  - `web/app/domains/chat/laudo_service.py`
  - `web/app/domains/revisor/service_messaging.py`
  - `web/tests/test_semantic_report_pack_cbmgo_autonomy.py`
  - `web/tests/test_report_pack_rollout_metrics.py`
  - `web/tests/test_v2_policy_engine.py`
- validacao executada:
  - `python3 -m py_compile web/app/v2/runtime.py web/app/v2/policy/engine.py web/app/v2/report_pack_rollout_metrics.py web/app/domains/chat/report_pack_helpers.py web/app/domains/chat/gate_helpers.py web/app/domains/chat/laudo_service.py web/app/domains/revisor/service_messaging.py web/tests/test_semantic_report_pack_cbmgo_autonomy.py web/tests/test_report_pack_rollout_metrics.py web/tests/test_v2_policy_engine.py`
  - `python3 -m pytest -q web/tests/test_semantic_report_pack_cbmgo_autonomy.py web/tests/test_report_pack_rollout_metrics.py web/tests/test_v2_policy_engine.py`
  - `python3 -m pytest -q web/tests/test_semantic_report_pack_nr35_autonomy.py web/tests/test_semantic_report_pack_cbmgo_autonomy.py web/tests/test_report_pack_rollout_metrics.py web/tests/test_v2_policy_engine.py web/tests/test_inspection_entry_mode_phase_d_mobile.py web/tests/test_regras_rotas_criticas.py -k "gate_qualidade or finalizar or status_relatorio or semantic_report_pack or rollout_metrics or mobile_autonomous" web/tests/test_v2_document_hard_gate.py web/tests/test_v2_document_hard_gate_enforce.py web/tests/test_v2_document_hard_gate_summary.py`
  - `python3 -m pytest -q web/tests/test_v2_reviewdesk_projection.py web/tests/test_revisor_command_side_effects.py web/tests/test_revisor_realtime.py`
  - total deste recorte: `52 passed`, `1 skipped`
- limite atual deste slice:
  - a observabilidade do rollout esta local/backend; ainda nao existe endpoint ou dashboard dedicado para consulta operacional
  - a heuristica de conflito continua agregada por item, nao por matriz normativa fina
  - familias fora de `nr35_linha_vida` e `cbmgo` seguem no fallback legado
- proximo passo:
  - escolher a proxima familia documental a modelar sobre a mesma espinha e decidir se a consulta operacional do rollout sobe para superficie explicita
