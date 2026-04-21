# Backend - checkpoint continuo de execucao e evolucao

Criado em `2026-04-15`.
Atualizado em `2026-04-15`.

## Objetivo

Transformar o diagnostico geral do backend em uma trilha executavel, com criterio de pronto, validacao obrigatoria e apontamento explicito do proximo ponto de evolucao.

Este documento e a referencia continua para acompanhar a evolucao real do backend. Ele nao existe para demo, apresentacao ou roteiro comercial. Ele existe para dizer:

- o que ja esta solido;
- o que ainda falta programar;
- qual e a fase atual;
- como validar a fase atual;
- qual documento e qual frente devem ser abertos em seguida.

## Escopo

Este checkpoint cobre o backend real de:

- `adminceo`
- `admincliente`
- `inspetor web`
- `inspetor mobile`
- `mesa avaliadora`
- governanca de tenant, portais e capabilities
- lifecycle de caso e laudo
- catalogo, templates, emissao documental e pacote oficial
- motor semantico de laudos com IA
- observabilidade, contratos compartilhados e filas/jobs futuros

Este checkpoint nao cobre:

- lapidacao visual
- apresentacao comercial
- ajustes cosmeticos de frontend sem impacto de dominio

## Como usar este documento

1. Abrir este checkpoint antes de iniciar qualquer slice relevante de backend.
2. Trabalhar apenas na fase marcada como `atual`.
3. Ao concluir um slice, atualizar obrigatoriamente:
   - `Atualizado em`
   - `Estado atual consolidado`
   - `Fase atual por status`
   - `Validacao consolidada`
   - `Impactos de frontend em aberto`
   - `Proximo ponto exato`
   - `Log de execucao`
4. Se o slice alterar contrato, capability, bootstrap, CTA, visibilidade ou estado consumido pelo frontend, registrar handoff em `artifacts/terminal_handoff/queue.json` via `scripts/dev/terminal_handoff_queue.py`.
5. Nao avancar para a fase seguinte sem cumprir o criterio de pronto da fase atual.

## Estado atual consolidado

Estado consolidado em `2026-04-15`:

- o backend principal esta unificado em `web/` e sustenta `adminceo`, `admincliente`, `inspetor web/mobile` e `mesa`;
- a governanca por tenant, portal e capability ja existe e ja foi endurecida em superfices criticas;
- o provisionamento inicial de empresa e usuarios operacionais ja existe, incluindo senha temporaria e first access;
- o lifecycle de laudo entre inspetor e mesa ja possui espinha compartilhada e cobertura especifica;
- o catalogo de templates e a emissao de PDF por familia estao avancados;
- o motor semantico de `report pack` esta funcional apenas nas familias modeladas e allowlisted, nao em cobertura ampla;
- a `Fase 1` ja abriu dois slices reais de observabilidade leve em `chat`, bootstrap do admin-cliente, onboarding de tenant, `admin/painel`, `revisao/painel`, geracao de PDF do inspetor, preview de template da mesa e operacoes centrais da `mesa`, com agregacao local em `web/app/shared/backend_hotspot_metrics.py` e leitura administrativa em `/admin/api/backend-hotspots/summary`;
- o resumo operacional documental agora tambem embute `backend_hotspots`, permitindo ler sinais de documento pesado e sinais gerais de backend no mesmo payload administrativo;
- o profiling local controlado da `Fase 1` ja consolidou `5` hotspots objetivos com `PERF_MODE=1`, artefato persistido e leitura registrada em `docs/full-system-audit/08_performance_hotspots.md`;
- a `Fase 2` ja abriu o primeiro slice estrutural real com `build_technical_case_context_bundle(...)` e `bind_technical_case_runtime_bundle_to_request(...)` em `web/app/v2/case_runtime.py`, reduzindo a composicao manual de `case_snapshot + tenant_policy_context + policy_decision + document_facade` em `chat`, `mobile` e `mesa`;
- `chat_stream_support`, `laudo_service`, `auth_mobile_support`, `mesa_mobile_support`, `mesa_common` e `mesa_thread_routes` agora consomem o mesmo builder compartilhado do `caso tecnico` para leitura canonica;
- os adapters Android de feed/thread foram ajustados para preservar paridade com o payload legado publicado, incluindo lifecycle top-level e `attachment_policy` quando o contrato esperado os expoe;
- `web/app/domains/chat/laudo_state_helpers.py` agora concentra uma autoridade canonica de mutacao do caso tecnico, com helpers compartilhados para finalizacao do inspetor, decisao da mesa, sinalizacao de feedback da mesa e reabertura manual;
- `laudo_service`, `revisor/service_messaging` e `report_finalize_stream_shadow` passaram a consumir esse write-path compartilhado, reduzindo `status_revisao` e `reabertura_pendente_em` escritos manualmente em multiplos lugares;
- `panel_state`, `templates_laudo_support`, `service_package` e `mesa/service` agora tambem reutilizam leitura compartilhada de lifecycle e ownership do `caso tecnico`, reduzindo classificacoes locais presas a `status_revisao` puro;
- o read-side da mesa deixou de tratar `REJEITADO` automaticamente como historico: casos em `devolvido_para_correcao` voltam para o fluxo operacional do inspetor e o `revisor_id` so permanece publico quando a ownership ativa continua na mesa;
- o payload `/revisao/api/laudo/{laudo_id}/completo` e o manifesto/pacote da mesa passaram a expor, de forma aditiva, `case_status`, `case_lifecycle_status`, `active_owner_role`, `allowed_next_lifecycle_statuses` e `allowed_surface_actions`;
- a projection V2 da mesa agora reemite essas mesmas chaves canonicas na fila e no adapter do pacote, e o shadow mode passou a detectar divergencia quando lifecycle/ownership se perdem ao promover a projection;
- `document_boundary`, `mesa_api` e `panel_shadow` agora centralizam a promotion/fallback da mesa: projection compativel passa a governar a resposta final e projection divergente deixa de ser promovida silenciosamente como se fosse source-of-truth;
- a base ja esta em estado de produto funcional, mas ainda nao esta fechada como plataforma madura;
- ainda faltam observabilidade forte, delimitacao de hotspots, consolidacao do `caso tecnico`, expansao segura do motor semantico, pipeline documental mais explicito e tratamento assincrono das operacoes pesadas;
- o worktree segue em consolidacao ativa, com muitos arquivos backend modificados ou novos.

## Fonte de verdade desta frente

Abrir estes documentos junto com este checkpoint:

1. `PLANS.md`
2. `docs/product-canonical-vision/02_open_questions.md`
3. `docs/full-system-audit/10_improvement_priorities.md`
4. `docs/full-system-audit/08_performance_hotspots.md`
5. `docs/restructuring-roadmap/127_semantic_report_pack_execution_plan.md`
6. `docs/restructuring-roadmap/128_normative_override_and_learning_governance.md`
7. `docs/restructuring-roadmap/129_dual_entry_configurable_inspection_roadmap.md`
8. `docs/restructuring-roadmap/130_dual_entry_implementation_checklist.md`
9. `docs/restructuring-roadmap/131_dual_entry_resume_checkpoint.md`

## Invariantes

Estas regras nao podem ser quebradas ao longo da execucao:

- `adminceo` governa liberacao e revogacao de portais, templates e capabilities do tenant;
- `admincliente`, `inspetor web/mobile` e `mesa` so podem ver ou executar o que estiver liberado ao tenant e ao usuario;
- `inspetor web` e `inspetor mobile` continuam compartilhando o mesmo nucleo de dominio;
- a `mesa` continua finalizando o mesmo fluxo que o inspetor iniciou, e nao um pipeline paralelo;
- a regra de negocio nao pode divergir por superficie;
- o frontend nao deve inferir permissao por heuristica quando o backend ja expoe politica governada;
- nenhuma expansao do motor semantico entra sem cobertura de teste e rollout controlado;
- nenhuma reestruturacao profunda deve preceder medicao, observabilidade minima e delimitacao de hotspots;
- todo impacto de frontend deve ser registrado como handoff explicito.

## Validacao consolidada

Baseline validada localmente em `2026-04-15`:

- `ruff check app/shared/tenant_entitlement_guard.py app/domains/revisor/ws.py app/domains/revisor/mesa_api.py tests/test_revisor_ws.py tests/test_tenant_entitlements_critical.py` -> `ok`
- `pytest -q tests/test_revisor_ws.py tests/test_tenant_entitlements_critical.py` -> `22 passed`
- `pytest -q tests/test_multiportal_bootstrap_contracts.py tests/test_tenant_access.py tests/test_v2_tenant_admin_projection.py` -> `18 passed`
- `pytest -q tests/test_admin_services.py tests/test_admin_client_routes.py -k 'politica or mobile_single_operator or provisiona_equipe_inicial'` -> `7 passed`
- `pytest -q tests/test_admin_services.py tests/test_admin_client_routes.py -k 'acesso or senha or primeiro or provisiona_equipe_inicial'` -> `6 passed`
- `pytest -q tests/test_regras_rotas_criticas.py -k 'test_revisor_exportar_pacote_mesa_pdf_retorna_arquivo or test_revisor_exportar_pacote_oficial_zip_retorna_manifesto_e_hashes or test_revisor_emite_oficialmente_bundle_congelado_com_replay_idempotente'` -> `3 passed`
- `http://127.0.0.1:8000/ready` -> `status=ok`

Slice atual de observabilidade validado localmente em `2026-04-15`:

- `ruff check app/shared/backend_hotspot_metrics.py app/domains/chat/chat_stream_routes.py app/domains/cliente/dashboard_bootstrap.py app/domains/admin/services.py app/domains/admin/client_routes.py app/domains/revisor/mesa_api.py app/domains/admin/routes.py tests/test_backend_hotspot_metrics.py` -> `ok`
- `pytest -q tests/test_backend_hotspot_metrics.py` -> `2 passed`
- `pytest -q tests/test_tenant_entitlements_critical.py tests/test_v2_tenant_admin_projection.py tests/test_admin_services.py tests/test_admin_client_routes.py -k 'tenant or onboarding or provisiona_equipe_inicial or acesso_inicial or policy or first_access'` -> `25 passed`
- `pytest -q tests/test_v2_document_hard_gate_10g.py tests/test_revisor_ws.py -k 'rota_chat or exportar or download or broadcast_mesa'` -> `4 passed`

Slice adicional de observabilidade validado localmente em `2026-04-15`:

- `ruff check web/app/domains/admin/routes.py web/app/domains/revisor/panel.py web/app/domains/chat/chat_aux_routes.py web/app/domains/revisor/templates_laudo.py web/app/domains/admin/document_operations_summary.py web/app/domains/revisor/mesa_api.py web/tests/test_backend_hotspot_metrics.py web/tests/test_v2_document_operations_summary.py` -> `ok`
- `python3 -m py_compile web/app/domains/admin/routes.py web/app/domains/revisor/panel.py web/app/domains/chat/chat_aux_routes.py web/app/domains/revisor/templates_laudo.py web/app/domains/admin/document_operations_summary.py web/app/domains/revisor/mesa_api.py web/tests/test_backend_hotspot_metrics.py web/tests/test_v2_document_operations_summary.py` -> `ok`
- `pytest -q web/tests/test_backend_hotspot_metrics.py web/tests/test_v2_document_operations_summary.py` -> `4 passed`
- `pytest -q web/tests/test_revisor_ws.py web/tests/test_tenant_entitlements_critical.py` -> `22 passed`
- `pytest -q web/tests/test_regras_rotas_criticas.py::test_revisor_login_funciona_e_painel_abre web/tests/test_regras_rotas_criticas.py::test_revisor_painel_exibe_resumo_operacional_templates web/tests/test_regras_rotas_criticas.py::test_revisor_preview_template_laudo_retorna_pdf web/tests/test_regras_rotas_criticas.py::test_api_gerar_pdf_usa_template_ativo_da_empresa web/tests/test_regras_rotas_criticas.py::test_api_gerar_pdf_usa_template_editor_rico_ativo web/tests/test_regras_rotas_criticas.py::test_api_gerar_pdf_fallback_legacy_quando_render_rico_falha web/tests/test_regras_rotas_criticas.py::test_api_gerar_pdf_fallback_legacy_quando_nao_ha_template_ativo web/tests/test_regras_rotas_criticas.py::test_revisor_painel_em_andamento_prioriza_por_sla web/tests/test_admin_client_routes.py::test_admin_catalogo_e_dashboard_exibem_rollup_de_governanca` -> `9 passed`
- `git diff --check -- web/app/domains/admin/routes.py web/app/domains/revisor/panel.py web/app/domains/chat/chat_aux_routes.py web/app/domains/revisor/templates_laudo.py web/app/domains/admin/document_operations_summary.py web/app/domains/revisor/mesa_api.py web/tests/test_backend_hotspot_metrics.py web/tests/test_v2_document_operations_summary.py` -> `ok`

Fechamento da Fase 1 validado localmente em `2026-04-15`:

- `python3 scripts/dev/profile_phase1_hotspots.py` -> artefato `artifacts/observability_phase_acceptance/20260415_174837/phase1_hotspots_profile.json`
- `docs/full-system-audit/08_performance_hotspots.md` atualizado com o ranking objetivo dos `5` hotspots locais
- `ruff check scripts/dev/profile_phase1_hotspots.py` -> `ok`
- `python3 -m py_compile scripts/dev/profile_phase1_hotspots.py` -> `ok`
- `git diff --check -- scripts/dev/profile_phase1_hotspots.py docs/full-system-audit/08_performance_hotspots.md docs/restructuring-roadmap/132_backend_execution_checkpoint.md` -> `ok`

Primeiro slice estrutural da Fase 2 validado localmente em `2026-04-15`:

- `ruff check web/app/v2/case_runtime.py web/app/domains/chat/chat_stream_support.py web/app/domains/chat/laudo_service.py web/app/domains/chat/auth_mobile_support.py web/app/domains/chat/mesa_common.py web/app/domains/chat/mesa_thread_routes.py web/app/domains/chat/mesa_mobile_support.py web/app/v2/adapters/android_case_feed.py web/app/v2/adapters/android_case_thread.py web/tests/test_v2_case_runtime.py` -> `ok`
- `python3 -m py_compile web/app/v2/case_runtime.py web/app/domains/chat/chat_stream_support.py web/app/domains/chat/laudo_service.py web/app/domains/chat/auth_mobile_support.py web/app/domains/chat/mesa_common.py web/app/domains/chat/mesa_thread_routes.py web/app/domains/chat/mesa_mobile_support.py web/app/v2/adapters/android_case_feed.py web/app/v2/adapters/android_case_thread.py web/tests/test_v2_case_runtime.py` -> `ok`
- `pytest -q web/tests/test_v2_case_runtime.py web/tests/test_v2_android_case_adapter.py web/tests/test_v2_android_case_feed_adapter.py web/tests/test_v2_android_case_thread_adapter.py web/tests/test_v2_inspector_projection.py web/tests/test_v2_reviewdesk_projection.py` -> `27 passed`
- `pytest -q web/tests/test_v2_policy_engine.py web/tests/test_v2_document_facade.py web/tests/test_v2_document_shadow.py` -> `23 passed`
- `pytest -q web/tests/test_laudo_lifecycle_unification.py` -> `3 passed`

Segundo slice estrutural da Fase 2 validado localmente em `2026-04-15`:

- `ruff check web/app/domains/chat/laudo_state_helpers.py web/app/domains/chat/laudo_service.py web/app/domains/revisor/service_messaging.py web/tests/test_laudo_lifecycle_unification.py web/app/domains/chat/report_finalize_stream_shadow.py web/tests/test_report_finalize_stream_binding.py` -> `ok`
- `python3 -m py_compile web/app/domains/chat/laudo_state_helpers.py web/app/domains/chat/laudo_service.py web/app/domains/revisor/service_messaging.py web/tests/test_laudo_lifecycle_unification.py web/app/domains/chat/report_finalize_stream_shadow.py web/tests/test_report_finalize_stream_binding.py` -> `ok`
- `pytest -q web/tests/test_laudo_lifecycle_unification.py` -> `5 passed`
- `pytest -q web/tests/test_approval_idempotency.py web/tests/test_operational_memory.py -k 'pendencia_reaberta or approved_case or mobile_autonomous'` -> `2 passed, 10 deselected`
- `pytest -q web/tests/test_regras_rotas_criticas.py -k 'revisor_aprovar_atualiza_status_e_registra_mensagem or revisor_rejeitar_via_api_com_header_sem_motivo_assume_padrao or laudo_com_ajustes_exige_reabertura_manual_para_chat_e_mesa or revisor_historico_reflete_retorno_do_inspetor_apos_reabertura or laudo_emitido_pode_ser_reaberto_para_novo_ciclo'` -> `5 passed, 179 deselected`
- `pytest -q web/tests/test_mesa_mobile_sync.py -k 'aprovar_no_mobile_fecha_caso_autonomo or enviar_para_mesa_forca_handoff'` -> `2 passed, 7 deselected`
- `pytest -q web/tests/test_v2_technical_case_snapshot.py web/tests/test_v2_inspector_projection.py` -> `10 passed`
- `pytest -q web/tests/test_semantic_report_pack_nr35_autonomy.py -k 'finalizacao_nr35_mobile_autonomous_aprova_direto'` -> `1 passed, 1 deselected`
- `pytest -q web/tests/test_semantic_report_pack_cbmgo_autonomy.py -k 'finalizacao_cbmgo_mobile_autonomous_aprova_direto_sem_parecer_previo_da_ia'` -> `1 passed`
- `pytest -q web/tests/test_report_finalize_stream_binding.py web/tests/test_v2_document_hard_gate_10g.py -k 'finalizacao_preserva_binding_governado_do_caso or report_finalize_stream_shadow_persiste_evidencia_duravel_e_expoe_summary_local_only'` -> `2 passed, 1 deselected`
- `git diff --check` -> `ok`

Terceiro slice estrutural da Fase 2 validado localmente em `2026-04-15`:

- `python3 -m ruff check web/app/domains/chat/laudo_state_helpers.py web/app/domains/revisor/panel_state.py web/app/domains/revisor/templates_laudo_support.py web/app/domains/revisor/service_package.py web/app/domains/mesa/service.py web/tests/test_v2_reviewdesk_read_side.py` -> `ok`
- `python3 -m pytest -q web/tests/test_v2_reviewdesk_read_side.py web/tests/test_v2_review_queue_projection.py web/tests/test_v2_reviewdesk_projection.py` -> `13 passed`

Quarto slice estrutural da Fase 2 validado localmente em `2026-04-15`:

- `python3 -m ruff check web/app/v2/contracts/review_queue.py web/app/v2/adapters/review_queue_dashboard.py web/app/v2/adapters/reviewdesk_package.py web/tests/test_v2_review_queue_projection.py web/tests/test_v2_reviewdesk_projection.py` -> `ok`
- `python3 -m pytest -q web/tests/test_v2_review_queue_projection.py web/tests/test_v2_reviewdesk_projection.py` -> `12 passed`
- `python3 -m pytest -q web/tests/test_v2_reviewdesk_read_side.py web/tests/test_v2_review_queue_projection.py web/tests/test_v2_reviewdesk_projection.py` -> `15 passed`

Quinto slice estrutural da Fase 2 validado localmente em `2026-04-15`:

- `python3 -m ruff check web/app/domains/revisor/document_boundary.py web/app/domains/revisor/mesa_api.py web/app/domains/revisor/panel.py web/app/domains/revisor/panel_shadow.py web/tests/test_v2_reviewdesk_projection.py web/tests/test_v2_review_queue_projection.py` -> `ok`
- `python3 -m pytest -q web/tests/test_v2_reviewdesk_projection.py web/tests/test_v2_review_queue_projection.py web/tests/test_v2_reviewdesk_read_side.py` -> `17 passed`
- `python3 -m pytest -q web/tests/test_v2_document_facade.py web/tests/test_v2_document_shadow.py web/tests/test_v2_provenance.py -k 'obter_pacote_mesa_laudo or pacote_mesa or reviewdesk_projection or reviewer_case_view or completo'` -> `2 passed, 15 deselected`

Interpretacao desta baseline:

- a governanca critica entre tenant, mobile, admin-cliente, inspetor e mesa esta coberta;
- onboarding e first access estao cobertos em recortes importantes;
- a base esta valida para continuar evolucao estrutural;
- esta baseline nao substitui a suite completa nem fecha todas as frentes abertas.

## Impactos de frontend em aberto

Handoffs ja registrados e que continuam validos:

- `HF-0008`: o frontend deve consumir `tenant_access_policy` para esconder ou desabilitar portais e acoes governadas, sem depender apenas de `403`;
- `HF-0009`: a `mesa` deve desabilitar CTAs de exportacao e download e tratar erro governado do websocket usando `tenant_access_policy.user_capability_entitlements`.
- `HF-0010`: a `mesa` deve preferir `case_status`, `case_lifecycle_status`, `active_owner_role` e `allowed_surface_actions` nos badges, filtros e CTAs do painel/pacote, sem continuar inferindo ownership so por `status_revisao` ou `revisado_por`.

Regra para novos slices:

- se o backend mudar bootstrap, ACL, contract shape, CTA permitido, estado de lifecycle ou mensagens de erro governado, registrar novo handoff antes de fechar a fase.
- este slice estrutural da `Fase 2` abriu o handoff `HF-0010` por adicionar sinais canonicos no read-side consumido pela mesa.
- este slice de inversao de dependencia nao abriu novo handoff: ele consolidou promotion/fallback sobre o contrato aditivo ja publicado.

## Fase atual por status

### Fase 0 - baseline consolidada

- `status`: concluida
- `saida obrigatoria`: fotografia objetiva do backend atual, com testes criticos e backlog de evolucao definido

### Fase 1 - observabilidade e delimitacao de hotspots

- `status`: concluida
- `owner esperado`: backend/operacao
- `saida obrigatoria`: rotas criticas instrumentadas, erros classificados e hotspots priorizados com evidencia

### Fase 2 - nucleo compartilhado do caso tecnico

- `status`: atual
- `dependencia`: Fase 1
- `saida obrigatoria`: lifecycle, ownership, ACL e transicoes centrados em um nucleo explicito reutilizado por todas as superfices

### Fase 3 - expansao segura do motor semantico de laudos

- `status`: pendente
- `dependencia`: Fase 2
- `saida obrigatoria`: novas familias entram com `report pack`, gates, rollout e testes, sem romper o fluxo atual

### Fase 4 - pipeline documental e processamento assincrono

- `status`: pendente
- `dependencia`: Fase 3
- `saida obrigatoria`: emissao, exportacao, congelamento e operacoes pesadas com fronteiras explicitas e suporte a execucao assincrona

### Fase 5 - contrato estavel multi-superficie

- `status`: pendente
- `dependencia`: Fase 4
- `saida obrigatoria`: contrato versionado e governado entre web, mobile e mesa, com fallback e rollout por superficie

## Ordem executavel

### Fase 1 - observabilidade e delimitacao de hotspots

Objetivo:

- medir antes de reestruturar;
- transformar gargalos e erros silenciosos em sinais objetivos de operacao;
- reduzir risco de mexer em areas criticas sem telemetria.

Checklist:

- instrumentar correlacao por `request_id`, `tenant_id`, `user_id`, `laudo_id` e `case_id` onde aplicavel;
- medir duracao por etapa nas rotas criticas de `chat`, `mesa`, `bootstrap`, onboarding e emissao/exportacao;
- classificar erros em pelo menos `governado`, `negocio`, `infra` e `integracao`;
- registrar quedas para `mesa_required`, falhas de finalizacao e gargalos de exportacao;
- produzir inventario real de hotspots a partir de evidencia de execucao, nao de intuicao.

Arquivos e documentos a abrir primeiro:

- `docs/full-system-audit/10_improvement_priorities.md`
- `docs/full-system-audit/08_performance_hotspots.md`
- `web/app/domains/chat/chat_stream_support.py`
- `web/app/domains/chat/laudo_service.py`
- `web/app/domains/revisor/mesa_api.py`
- `web/app/domains/cliente/dashboard_bootstrap.py`
- `web/app/domains/admin/services.py`

Validacao minima:

- logs e metricas emitidos nas rotas criticas sem quebrar contrato externo;
- testes ou smokes cobrindo a classificacao basica de erro governado x erro operacional;
- evidencia objetiva de pelo menos os `5` maiores hotspots reais do backend.

Status do slice atual:

- `chat`, `bootstrap`, onboarding e `mesa` ja emitem observacao agregada;
- `admin/painel`, `revisao/painel`, `app/api/gerar_pdf` e `revisao/api/templates-laudo/{template_id}/preview` agora tambem emitem observacao agregada;
- o resumo em `/admin/api/document-operations/summary` agora agrega `backend_hotspots` junto da visao documental;
- respostas `500` em JSON que antes ficavam contabilizadas como sucesso nas exportacoes da mesa agora entram como `error` com classificacao `infra`;
- correlacao por `tenant_id`, `user_id`, `laudo_id` e `case_id` entrou onde aplicavel;
- classificacao `governado`, `negocio`, `infra` e `integracao` ja existe no agregador;
- a leitura administrativa local foi exposta em `/admin/api/backend-hotspots/summary`;
- contagem de queries continua dependente do `PERF_MODE` ja existente para virar evidencia mais rica de hotspot.

Resultado objetivo que encerra a fase:

- `cliente_bootstrap` liderou a amostra local com `avg_duration_ms=32.999` e `avg_sql_count=61`;
- `mesa_export_package_pdf` veio em seguida com `avg_duration_ms=29.561` e `avg_sql_count=29`;
- `review_panel_html` confirmou custo de composicao SSR com `avg_duration_ms=25.590`, `avg_sql_count=16` e `avg_render_ms=25.590`;
- `admin_dashboard_html` confirmou agregacao SSR relevante com `avg_duration_ms=17.758` e `avg_sql_count=15`;
- `inspector_pdf_generation` fechou o top 5 com `avg_duration_ms=14.333` e `avg_sql_count=5`;
- `review_template_preview` ficou imediatamente abaixo do top 5, com `avg_duration_ms=11.554`.

Critico para concluir:

- o time consegue dizer com evidencia onde o backend perde tempo, onde cai e onde a governanca bloqueou uma acao.

Ao concluir:

- atualizar este checkpoint;
- abrir `docs/product-canonical-vision/02_open_questions.md`;
- mover a fase atual para `Fase 2 - nucleo compartilhado do caso tecnico`.

### Fase 2 - nucleo compartilhado do caso tecnico

Objetivo:

- parar de depender de compat layers e regras espalhadas para lifecycle, ownership e ACL;
- consolidar um `caso tecnico` real como centro do produto.

Checklist:

- extrair servicos compartilhados para lifecycle, owner, handoff e transicoes;
- reduzir duplicacao de regra entre `chat`, `cliente`, `mobile` e `mesa`;
- consolidar leitura e escrita de estado do caso em fronteiras mais explicitas;
- tornar ACL e policy reutilizaveis por comando, consulta e websocket.

Arquivos e documentos a abrir primeiro:

- `docs/product-canonical-vision/02_open_questions.md`
- `docs/restructuring-roadmap/37_epic02_case_core_acl.md`
- `web/app/domains/chat/laudo_state_helpers.py`
- `web/app/domains/chat/laudo_service.py`
- `web/app/domains/mesa/service.py`
- `web/app/domains/revisor/service_contracts.py`

Validacao minima:

- `test_laudo_lifecycle_unification.py` verde;
- cobertura de transicao e ownership pelo nucleo compartilhado;
- reducao objetiva de duplicacao entre superfices.

Status do slice atual:

- `web/app/v2/case_runtime.py` agora separa o builder puro do `caso tecnico` do binding de `request.state`, permitindo reuso fora das rotas HTTP sem recompor snapshot/policy/documento na mao;
- a leitura canonica compartilhada passou a ser consumida por:
  - `chat_stream_support`
  - `laudo_service`
  - `auth_mobile_support`
  - `mesa_mobile_support`
  - `mesa_common`
  - `mesa_thread_routes`
- `web/app/domains/chat/laudo_state_helpers.py` agora tambem concentra o write-path canonico do lifecycle com:
  - autoridade de mutacao baseada no snapshot V2;
  - helpers para `aplicar_finalizacao_inspetor_ao_laudo`;
  - helpers para `aplicar_decisao_mesa_ao_laudo`;
  - helper para `sinalizar_reabertura_pendente_por_feedback_mesa`;
  - helper para `aplicar_reabertura_manual_ao_laudo`;
- `laudo_service` deixou de mutar diretamente `status_revisao`, `reabertura_pendente_em`, `revisado_por`, `motivo_rejeicao` e `encerrado_pelo_inspetor_em` nos fluxos de finalizacao mobile e reabertura manual;
- `revisor/service_messaging` passou a reutilizar o mesmo nucleo para aprovar, devolver, sinalizar feedback que exige reabertura e reabrir pendencias da mesa;
- `report_finalize_stream_shadow` tambem passou a reaproveitar o mesmo helper de envio para mesa, evitando uma nova ramificacao legado-only de lifecycle;
- `web/app/domains/chat/laudo_state_helpers.py` passou a expor helpers de leitura compartilhada para o shell legado da mesa, incluindo cache de snapshot canonico por `laudo`;
- `panel_state` deixou de classificar fila operacional e historico apenas por `status_revisao`, reutilizando lifecycle/ownership do `caso tecnico` para devolver `devolvido_para_correcao` ao acompanhamento do inspetor;
- `templates_laudo_support` passou a contar `devolvido_para_correcao` como `uso_em_campo`, em vez de inflar `uso_aguardando` por inferencia legado-only;
- `service_package` e `mesa/service` agora enriquecem o payload legado com campos canonicos aditivos de lifecycle/ownership e deixam de publicar `revisor_id` como owner ativo quando o caso ja voltou para o inspetor;
- o contrato legado permaneceu estavel; as novas chaves canonicas entraram de forma aditiva e geraram o handoff `HF-0010` para consumo explicito do frontend;
- `v2/contracts/review_queue.py` passou a reemitir `case_status`, `case_lifecycle_status`, `case_workflow_mode`, `active_owner_role`, `allowed_next_lifecycle_statuses` e `allowed_surface_actions` nos itens da fila canonica da mesa;
- `v2/adapters/review_queue_dashboard.py` passou a validar essas chaves no shadow mode, evitando marcar a projection como compativel quando lifecycle/ownership forem perdidos ao promover o SSR;
- `v2/adapters/reviewdesk_package.py` passou a reconstituir o pacote legado com os mesmos sinais canonicos aditivos ja publicados pelo read-side legado;
- `document_boundary` passou a tratar compatibilidade como decisao real de promotion: payload compativel vira resposta preferida, payload divergente volta para fallback legado sem promover o erro silenciosamente;
- `mesa_api` passou a reutilizar esse boundary tambem em `/revisao/api/laudo/{id}/completo`, fazendo a sintese do caso vir do mesmo caminho do pacote e deixando o legado principalmente como fonte de historico/aprendizados;
- `panel_shadow` passou a centralizar a promocao da projection da fila para o contexto SSR, reduzindo logica paralela espalhada em `panel.py`;
- o adapter Android de feed passou a reemitir as chaves top-level de lifecycle quando o contrato esperado as publica;
- o adapter Android de thread passou a preservar `attachment_policy` do payload legado;
- o read-side legado da mesa ficou mais alinhado ao `caso tecnico`, mas `/revisao/api/laudo/{id}/completo` ainda recomputa um summary legado antes de receber a promotion/fallback centralizada.

Critico para concluir:

- o backend passa a ter uma espinha unica de `caso tecnico`, e nao apenas contratos alinhados por convencao.

Ao concluir:

- atualizar este checkpoint;
- abrir `docs/restructuring-roadmap/131_dual_entry_resume_checkpoint.md`;
- mover a fase atual para `Fase 3 - expansao segura do motor semantico de laudos`.

### Fase 3 - expansao segura do motor semantico de laudos

Objetivo:

- ampliar o `report pack` e a finalizacao semantica para mais familias sem abrir regressao operacional.

Checklist:

- selecionar o proximo lote de familias modeladas;
- garantir `schema`, `image_slots`, gates, candidato estruturado e politica de autonomia por familia;
- manter rollout allowlisted por template e tenant;
- medir divergencia IA-humano e taxa de queda para `mesa_required` antes de ampliar cobertura.

Arquivos e documentos a abrir primeiro:

- `docs/restructuring-roadmap/127_semantic_report_pack_execution_plan.md`
- `docs/restructuring-roadmap/128_normative_override_and_learning_governance.md`
- `docs/restructuring-roadmap/129_dual_entry_configurable_inspection_roadmap.md`
- `docs/restructuring-roadmap/130_dual_entry_implementation_checklist.md`
- `docs/restructuring-roadmap/131_dual_entry_resume_checkpoint.md`

Validacao minima:

- testes por familia nova;
- gates semanticos e policy engine verdes;
- rollout controlado por allowlist, com metrica local disponivel.

Critico para concluir:

- o backend consegue ampliar familias sem criar um segundo pipeline nem prometer autonomia fora da cobertura modelada.

Ao concluir:

- atualizar este checkpoint;
- abrir `docs/product-canonical-vision/02_open_questions.md` na linha de pipeline documental;
- mover a fase atual para `Fase 4 - pipeline documental e processamento assincrono`.

### Fase 4 - pipeline documental e processamento assincrono

Objetivo:

- tornar emissao, exportacao e congelamento documental mais previsiveis;
- tirar do caminho sincronico o que for pesado demais para request/response simples.

Checklist:

- explicitar fronteiras entre montagem documental, pacote oficial, emissao e download;
- garantir idempotencia, replay e rastreabilidade nos fluxos de emissao;
- mover operacoes pesadas para jobs ou filas quando a evidencia mostrar necessidade real;
- manter fallback seguro para operacao sincronica quando apropriado.

Arquivos e documentos a abrir primeiro:

- `docs/product-canonical-vision/02_open_questions.md`
- `docs/restructuring-roadmap/42_epic07_document_facade.md`
- `web/app/shared/official_issue_package.py`
- `web/app/domains/revisor/service_package.py`
- `web/app/domains/revisor/command_side_effects.py`

Validacao minima:

- testes de idempotencia e pacote oficial verdes;
- exportacao e emissao com fronteiras explicitas;
- operacoes pesadas com estrategia documentada de retry, replay ou fila.

Critico para concluir:

- o backend deixa de depender integralmente de requests sincronicos para partes pesadas e sensiveis do fluxo documental.

Ao concluir:

- atualizar este checkpoint;
- abrir `docs/restructuring-roadmap/17_mobile_shared_api_contract_freeze.md`;
- mover a fase atual para `Fase 5 - contrato estavel multi-superficie`.

### Fase 5 - contrato estavel multi-superficie

Objetivo:

- impedir regressao silenciosa entre `web`, `mobile` e `mesa` enquanto o backend continua evoluindo.

Checklist:

- versionar contratos sensiveis de bootstrap e lifecycle quando necessario;
- definir fallback e rollout por superficie;
- endurecer testes de contrato para mobile, SSR do inspetor e mesa;
- explicitar compatibilidade minima por superficie e tenant.

Arquivos e documentos a abrir primeiro:

- `docs/restructuring-roadmap/17_mobile_shared_api_contract_freeze.md`
- `docs/restructuring-roadmap/47_epic08d_android_public_contract.md`
- `web/tests/test_multiportal_bootstrap_contracts.py`
- `web/tests/test_v2_tenant_admin_projection.py`
- `web/templates/inspetor/base.html`

Validacao minima:

- contratos compartilhados versionados ou congelados explicitamente;
- fallback de superficie comprovado em teste;
- regressao de bootstrap ou capability detectada por teste de contrato.

Critico para concluir:

- o backend consegue continuar evoluindo sem quebrar `mobile`, `inspetor web` ou `mesa` por mudanca implicita de contrato.

Ao concluir:

- atualizar este checkpoint;
- reavaliar `PLANS.md` e `docs/full-system-audit/10_improvement_priorities.md`;
- abrir um novo checkpoint para a proxima macrofrente.

## Proximo ponto exato

O proximo corte de backend a ser atacado a partir deste checkpoint e:

1. continuar na `Fase 2 - nucleo compartilhado do caso tecnico`;
2. abrir `docs/product-canonical-vision/02_open_questions.md`, `docs/restructuring-roadmap/37_epic02_case_core_acl.md` e `docs/restructuring-roadmap/131_dual_entry_resume_checkpoint.md`;
3. atacar o proximo slice estrutural da fase em `web/app/domains/revisor/service_package.py`, `web/app/domains/revisor/document_boundary.py`, `web/app/domains/revisor/panel_state.py` e `web/app/domains/revisor/panel_shadow.py`;
4. separar o que ainda e complemento legado (`historico`, `whispers`, `aprendizados_visuais`, filtros SSR) do que ja deve nascer do `caso tecnico`, para que `/revisao/api/laudo/{id}/completo` e o painel da mesa parem de recomputar summary legado antes da promotion;
5. decidir nesse slice se os builders legados de summary podem virar helpers internos de compatibilidade e se a `Fase 2` ja atingiu criterio de pronto; se houver mudanca publica adicional de contrato ou CTA, atualizar o handoff `HF-0010` antes de fechar.

Documento a abrir imediatamente para a execucao atual:

- `docs/product-canonical-vision/02_open_questions.md`
- `docs/restructuring-roadmap/37_epic02_case_core_acl.md`
- `web/app/domains/revisor/service_package.py`
- `web/app/domains/revisor/document_boundary.py`
- `web/app/domains/revisor/panel_state.py`

Documento a abrir logo apos fechar a fase atual:

- `docs/restructuring-roadmap/131_dual_entry_resume_checkpoint.md`

## Log de execucao

### 2026-04-15 - checkpoint inicial da evolucao real do backend

- diagnostico consolidado a partir do estado atual do repositorio e da documentacao interna;
- baseline registrada com foco em governanca de tenant, onboarding, lifecycle compartilhado, templates/PDF e mesa;
- backlog reorganizado em `5` fases executaveis;
- `Fase 1 - observabilidade e delimitacao de hotspots` definida como ponto atual de evolucao;
- handoffs de frontend `HF-0008` e `HF-0009` reconhecidos como dependencias abertas;
- proximo ponto travado explicitamente em observabilidade antes de reestruturacao profunda ou expansao ampla.

### 2026-04-15 - fase 1 slice 1 instrumentado

- agregador local criado em `web/app/shared/backend_hotspot_metrics.py`;
- rotas e servicos criticos instrumentados:
  - `chat_stream`
  - `cliente_bootstrap`
  - `admin_tenant_onboarding`
  - `admin_tenant_initial_access_view`
  - `mesa_case_package_read`
  - `mesa_export_package_pdf`
  - `mesa_export_package_zip`
  - `mesa_official_issue`
  - `mesa_official_issue_download`
- endpoint administrativo local publicado em `/admin/api/backend-hotspots/summary`;
- classificacao inicial de falhas consolidada em `governado`, `negocio`, `infra` e `integracao`;
- regressao focal validada com `31` testes verdes neste slice;
- nenhum novo handoff de frontend aberto;

### 2026-04-15 - fase 1 slice 2 instrumentado

- observabilidade expandida para:
  - `admin_dashboard_html`
  - `review_panel_html`
  - `inspector_pdf_generation`
  - `review_template_preview`
- `/admin/api/document-operations/summary` passou a embutir `backend_hotspots`;
- exportacoes PDF e ZIP da mesa passaram a registrar `500` engolido como `error` com `error_class=infra`;
- regressao focal validada com `35` testes verdes somando os recortes deste slice;
- nenhum novo handoff de frontend aberto;

### 2026-04-15 - fase 1 concluida com profiling local objetivo

- coletor dev reproducivel adicionado em `scripts/dev/profile_phase1_hotspots.py`;
- profiling local executado com `PERF_MODE=1` e artefato persistido em `artifacts/observability_phase_acceptance/20260415_174837/phase1_hotspots_profile.json`;
- top `5` hotspots objetivos consolidados em `docs/full-system-audit/08_performance_hotspots.md`;
- a leitura local confirmou que o gargalo atual da base e de composicao por request e operacao documental sincronica, nao de uma query isolada lenta;
- nenhum novo handoff de frontend aberto;
- fase atual movida para `Fase 2 - nucleo compartilhado do caso tecnico`.
- proximo passo travado no primeiro slice estrutural da `Fase 2`.

### 2026-04-15 - fase 2 slice 1 consolidou a leitura compartilhada do caso tecnico

- `web/app/v2/case_runtime.py` passou a expor um builder puro (`build_technical_case_context_bundle`) e um binder de `request.state` (`bind_technical_case_runtime_bundle_to_request`);
- a montagem de `case_snapshot + tenant_policy_context + policy_decision + document_facade` deixou de ser recomposta manualmente em multiplas superfices de `chat`, `mobile` e `mesa`;
- `chat_stream_support`, `laudo_service`, `auth_mobile_support`, `mesa_mobile_support`, `mesa_common` e `mesa_thread_routes` foram alinhados ao mesmo nucleo de leitura canonica;
- os adapters Android de feed/thread foram ajustados para manter paridade com os payloads legados publicados quando o rollout V2 estiver ativo;
- regressao focal e de policy/documento fechou verde neste slice;
- nenhum novo handoff de frontend foi aberto;
- proximo passo travado no segundo slice da `Fase 2`: mover guardas de transicao e ownership do write-path para um nucleo compartilhado.

### 2026-04-15 - fase 2 slice 2 consolidou o write-path compartilhado do caso tecnico

- `web/app/domains/chat/laudo_state_helpers.py` passou a expor uma autoridade canonica de mutacao baseada no snapshot V2, com helpers reutilizaveis de finalizacao, decisao da mesa, feedback que exige reabertura e reabertura manual;
- `laudo_service` foi alinhado a esse write-path compartilhado para `finalizar`, `enviar para mesa`, `aprovar no mobile` e `reabrir`, incluindo limpeza consistente de ancora de reabertura quando um novo ciclo e consolidado;
- `revisor/service_messaging` passou a reaproveitar o mesmo nucleo para `aprovar`, `rejeitar`, respostas da mesa, solicitacoes de refazer coverage, anexos da mesa e reabertura de pendencia;
- `report_finalize_stream_shadow` tambem passou a usar o helper compartilhado de envio para mesa, evitando mais uma borda manual de lifecycle;
- regressao focal de lifecycle, reabertura, aprovacao, mobile sync, snapshot/projection e shadow finalize fechou verde neste slice;
- nenhum novo handoff de frontend foi aberto;
- proximo passo travado no read-side da `Fase 2`: alinhar painel da mesa, pacote e estatisticas administrativas ao mesmo lifecycle canonico do `caso tecnico`.

### 2026-04-15 - fase 2 slice 3 alinhou o read-side da mesa ao lifecycle canonico

- `web/app/domains/chat/laudo_state_helpers.py` passou a fornecer snapshot canonico compartilhado para o shell legado da mesa;
- `panel_state` passou a agrupar `em_andamento`, `pendente` e `historico` pelo lifecycle/ownership do `caso tecnico`, devolvendo `devolvido_para_correcao` ao fluxo do inspetor;
- `templates_laudo_support` passou a contar `devolvido_para_correcao` como uso operacional em campo;
- `service_package` e `mesa/service` enriqueceram o payload legado com campos canonicos aditivos e deixaram de anunciar `revisor_id` como owner ativo quando o caso ja retornou ao inspetor;
- o handoff `HF-0010` foi aberto para o frontend consumir os sinais canonicos do caso no painel e no pacote da mesa;
- regressao focal do read-side e das projections da mesa fechou verde com `13` testes;
- proximo passo travado na projection V2 da mesa: alinhar `document_boundary`, `panel_shadow` e adapters ao mesmo criterio canonico antes de promover preferencia de rota.

### 2026-04-15 - fase 2 slice 4 alinhou a projection V2 da mesa ao read-side canonico

- `v2/contracts/review_queue.py` passou a carregar as chaves canonicas de lifecycle/ownership nos itens da fila da mesa;
- `v2/adapters/review_queue_dashboard.py` passou a tratar perda dessas chaves como divergencia real de compatibilidade no shadow mode;
- `v2/adapters/reviewdesk_package.py` passou a reconstruir o pacote legado com as mesmas chaves canonicas aditivas do read-side legado;
- a projection preferida do painel SSR e do pacote da mesa deixou de perder `case_lifecycle_status`, `active_owner_role` e `allowed_surface_actions` quando promovida;
- nenhum novo handoff de frontend foi aberto alem do `HF-0010`, porque a mudanca apenas fechou a paridade da projection com o contrato aditivo ja publicado;
- regressao focal da fila/projection/pacote fechou verde com `15` testes combinados;
- proximo passo travado na inversao de dependencia da mesa: reduzir a montagem paralela em `document_boundary`, `mesa_api` e `panel.py` agora que a projection esta alinhada.

### 2026-04-15 - fase 2 slice 5 centralizou promotion e fallback da mesa

- `document_boundary` passou a tratar compatibilidade da projection como decisao real de promotion, em vez de sempre mesclar projection e legado mesmo quando houver divergencia;
- `/revisao/api/laudo/{id}/completo` passou a reutilizar o mesmo boundary do pacote para a sintese do caso, reduzindo a diferenca estrutural entre os dois endpoints;
- `panel_shadow` passou a centralizar a promotion da fila canonica para o contexto SSR, deixando `panel.py` mais fino e com fallback unico;
- nenhum novo handoff de frontend foi aberto alem do `HF-0010`, porque a mudanca consolidou comportamento sobre o contrato aditivo ja existente;
- regressao focal do painel, do pacote, do completo e dos hooks documentais ligados ao boundary fechou verde com `17` testes do recorte principal e mais `2` testes documentais correlatos;
- proximo passo travado no cleanup final da `Fase 2`: separar complementos legados de summary legado e decidir se a fase ja pode ser encerrada.
