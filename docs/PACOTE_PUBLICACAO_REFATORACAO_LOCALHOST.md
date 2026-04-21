# Pacote de Publicação da Refatoração Fullstack

## Objetivo

Concentrar, em um único lugar, o pacote local de mudanças antes da próxima subida ao GitHub.

Este arquivo existe para evitar duas perdas de tempo:

- esquecer o que mudou ao longo de vários ciclos locais;
- subir um pacote grande sem uma lista objetiva do que validar depois.

## Regra deste arquivo

Atualize este documento a cada corte local relevante, sem fazer push.

Quando o pacote estiver pronto para publicação, este arquivo deve responder quatro perguntas:

1. O que mudou?
2. O que já foi validado em localhost?
3. O que ainda precisa ser validado antes do push?
4. O que precisa ser conferido no GitHub e no Render depois da publicação?

## Estado do pacote atual

- status: em preparação local
- branch: `checkpoint/20260331-current-worktree`
- estratégia: `localhost first`
- último push publicado: `eb3fa48` `Trim inspector entry mode leftovers`

## Cortes locais acumulados desde o último push

### 1. Extração do serviço de signatários governados do tenant

Status:

- concluído localmente
- ainda não publicado

Problema observado:

- `web/app/domains/admin/services.py` ainda concentrava o bloco de normalização, serialização e persistência de signatários governados;
- esse trecho era coeso, já possuía testes focados e não precisava permanecer misturado ao restante do catálogo administrativo.

Corte executado:

- criação de `web/app/domains/admin/tenant_signatory_services.py`;
- extração de `_serializar_signatario_governado_admin` para o novo módulo;
- extração de `upsert_signatario_governado_laudo` para o novo módulo;
- `web/app/domains/admin/services.py` passou a reexportar essas rotinas, preservando a API pública atual.

Arquivos alterados:

- `web/app/domains/admin/services.py`
- `web/app/domains/admin/tenant_signatory_services.py`

Validação local já executada:

- `git diff --check`
- `python -m py_compile web/app/domains/admin/services.py web/app/domains/admin/tenant_signatory_services.py`
- `pytest -q web/tests/test_admin_services.py -k 'signatario_governado_do_tenant_salva_escopo_e_aparece_no_detalhe'`
  - resultado:
    - `1 passed, 41 deselected`
- `pytest -q web/tests/test_admin_client_routes.py -k 'salva_signatario_governado_no_tenant'`
  - resultado:
    - `1 passed, 38 deselected`

### 2. Extração do detalhe administrativo do tenant

Status:

- concluído localmente
- ainda não publicado

Problema observado:

- `web/app/domains/admin/services.py` ainda mantinha o serializer do usuário admin e o resumo de primeiro acesso, embora o fluxo de detalhe do tenant já estivesse concentrado em `tenant_client_read_services.py`;
- isso deixava a fachada admin carregando lógica de leitura que já pertencia ao read-side do tenant.

Corte executado:

- `_serializar_usuario_admin` foi movido para `web/app/domains/admin/tenant_client_read_services.py`;
- `_resumir_primeiro_acesso_empresa` foi movido para `web/app/domains/admin/tenant_client_read_services.py`;
- `web/app/domains/admin/services.py` passou a reexportar essas rotinas, mantendo a fachada atual;
- `buscar_detalhe_cliente` permaneceu estável na superfície pública, agora consumindo apenas as dependências do read-side já localizadas no módulo certo.

Arquivos alterados:

- `web/app/domains/admin/services.py`
- `web/app/domains/admin/tenant_client_read_services.py`

Validação local já executada:

- `git diff --check`
- `python -m py_compile web/app/domains/admin/services.py web/app/domains/admin/tenant_client_read_services.py web/app/domains/admin/tenant_signatory_services.py`
- `pytest -q web/tests/test_admin_services.py -k 'busca_detalhe_cliente_tolera_falha_no_portfolio_catalogo or signatario_governado_do_tenant_salva_escopo_e_aparece_no_detalhe'`
  - resultado:
    - `2 passed, 40 deselected`
- `pytest -q web/tests/test_admin_client_routes.py -k 'admin_clientes_renderiza_console_operacional_na_lista_e_no_detalhe or admin_cliente_salva_signatario_governado_no_tenant'`
  - resultado:
    - `2 passed, 37 deselected`

### 3. Extração do histórico do workspace para módulo dedicado

Status:

- concluído localmente
- ainda não publicado

Problema observado:

- `web/static/js/chat/chat_index_page.js` ainda concentrava todo o pipeline do histórico do workspace, misturando normalização de filtros, leitura do DOM, composição dos cards e renderização;
- esse bloco já era um subdomínio claro do inspetor e impedia o arquivo principal de ficar restrito à orquestração;
- durante a extração apareceu um acoplamento residual no bootstrap do runtime, com actions do `entry_mode` sendo sobrescritas por wrappers do arquivo principal e causando recursão no carregamento visual.

Corte executado:

- criação de `web/static/js/inspetor/workspace_history.js`;
- extração do pipeline de histórico do workspace para o novo módulo;
- `web/templates/index.html` passou a carregar o novo script do inspetor;
- `web/static/js/chat/chat_index_page.js` foi reduzido, passando a consumir as actions do módulo para histórico e cópia;
- o wiring final de `ctx.actions` foi corrigido para preservar as implementações reais de `entry_mode`, contexto visual do laudo e reset de filtros.

Arquivos alterados:

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/inspetor/workspace_history.js`
- `web/templates/index.html`

Validação local já executada:

- `git diff --check`
- `node --check web/static/js/inspetor/workspace_history.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
  - resultado:
    - capturas geradas em `web/artifacts/visual/inspetor/20260420-164035`

### 4. Extração do onboarding do tenant para módulo dedicado

Status:

- concluído localmente
- ainda não publicado

Problema observado:

- `web/app/domains/admin/services.py` ainda concentrava todo o fluxo de onboarding do tenant, incluindo criação da empresa, usuário admin, provisionamento inicial e aviso de boas-vindas;
- o bloco já era um subdomínio coeso, mas a extração precisava preservar compatibilidade porque vários testes e domínios ainda importam ou monkeypatcheiam símbolos históricos expostos por `admin.services`;
- durante a validação, a primeira versão da extração revelou duas dependências implícitas dessa fachada: `criar_usuario_empresa` como reexport público e `gerar_senha_fortificada` como ponto de monkeypatch para fluxos críticos do portal cliente.

Corte executado:

- criação de `web/app/domains/admin/tenant_onboarding_services.py`;
- extração de `registrar_novo_cliente`, `_aviso_notificacao_boas_vindas` e `_disparar_email_boas_vindas` para o novo módulo;
- `web/app/domains/admin/services.py` passou a atuar como fachada compatível, injetando normalização de CNPJ, disparo de boas-vindas e gerador de senha para preservar monkeypatches existentes;
- reexports legados necessários para compatibilidade foram mantidos em `services.py`, incluindo `criar_usuario_empresa` e `gerar_senha_fortificada`.

Arquivos alterados:

- `web/app/domains/admin/services.py`
- `web/app/domains/admin/tenant_onboarding_services.py`

Validação local já executada:

- `git diff --check`
- `python -m py_compile web/app/domains/admin/services.py web/app/domains/admin/tenant_onboarding_services.py web/app/domains/admin/tenant_client_read_services.py web/app/domains/admin/tenant_signatory_services.py`
- `pytest -q web/tests/test_admin_services.py -k 'boas_vindas or registrar_novo_cliente'`
  - resultado:
    - `6 passed, 36 deselected`
- `pytest -q web/tests/test_admin_client_routes.py -k 'cadastrar_empresa_exibe_aviso_operacional_quando_boas_vindas_nao_sao_entregues or cadastrar_empresa_exibe_pacote_inicial_com_operacao_provisionada'`
  - resultado:
    - `2 passed, 37 deselected`
- `pytest -q web/tests/test_backend_hotspot_metrics.py -k onboarding`
  - resultado:
    - `1 passed, 2 deselected`
- `pytest -q web/tests/test_cliente_portal_critico.py -k 'fluxo_fixo_empresa_admin_cliente_equipe_e_logins_operacionais_funciona'`
  - resultado:
    - `1 passed, 21 deselected`

### 5. Extração do rail de contexto do workspace

Status:

- concluído localmente
- ainda não publicado

Problema observado:

- `web/static/js/chat/chat_index_page.js` ainda concentrava o rail de contexto do workspace, incluindo contexto fixado, resumo operacional da IA e card resumido da mesa;
- esse bloco já formava um subdomínio separado do histórico e impedia o arquivo principal de ficar restrito à orquestração, ações de conversa e bootstrap do portal;
- o corte precisava preservar integrações já existentes com `system_events`, `ui_bindings`, `workspace_derivatives` e o resumo operacional vindo do módulo da mesa.

Corte executado:

- criação de `web/static/js/inspetor/workspace_context.js`;
- extração do rail de contexto do workspace para o novo módulo;
- `web/templates/index.html` passou a carregar o novo script do inspetor;
- `web/static/js/chat/chat_index_page.js` foi reduzido e passou a consumir as actions registradas pelo novo módulo;
- o runtime do inspetor recebeu `noops` compatíveis e o registro `registerWorkspaceContext` na sequência de módulos.

Arquivos alterados:

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/inspetor/workspace_context.js`
- `web/templates/index.html`

Validação local já executada:

- `git diff --check`
- `node --check web/static/js/inspetor/workspace_context.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
  - resultado:
    - capturas geradas em `web/artifacts/visual/inspetor/20260420-165733`

### 6. Extração da navegação do workspace

Status:

- concluído localmente
- ainda não publicado

Problema observado:

- `web/static/js/chat/chat_index_page.js` ainda concentrava a navegação do shell do workspace, incluindo transições de landing da IA, restauração sem laudo, stage ativo do workspace e expansão do histórico da home;
- esse bloco já formava um subdomínio separado do restante do arquivo principal e mantinha acoplamentos diretos com `bootstrap`, `system_events`, `ui_bindings` e a sincronização visual do widget da mesa;
- o corte precisava preservar a ordem entre `workspaceStage`, `modoInspecaoUI` e a limpeza do estado lateral, sem reintroduzir regressões de runtime.

Corte executado:

- criação de `web/static/js/inspetor/workspace_navigation.js`;
- extração de `resolverContextoVisualWorkspace`, `definirWorkspaceStage`, `atualizarContextoWorkspaceAtivo`, `definirModoInspecaoUI`, `exibirInterfaceInspecaoAtiva`, `exibirLandingAssistenteIA`, `restaurarTelaSemRelatorio`, `resetarInterfaceInspecao`, `atualizarHistoricoHomeExpandido` e `rolarParaHistoricoHome` para o novo módulo;
- `web/templates/index.html` passou a carregar o novo script do inspetor;
- `web/static/js/chat/chat_index_page.js` foi reduzido e passou a consumir as actions registradas pelo novo módulo;
- o runtime do inspetor recebeu `normalizarModoInspecaoUI` no shared runtime, `noops` compatíveis e reexports auxiliares para o novo módulo.

Arquivos alterados:

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/inspetor/workspace_navigation.js`
- `web/templates/index.html`

Validação local já executada:

- `git diff --check`
- `node --check web/static/js/inspetor/workspace_navigation.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `node --check web/static/js/inspetor/bootstrap.js`
- `node --check web/static/js/inspetor/system_events.js`
- `node --check web/static/js/inspetor/ui_bindings.js`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
  - resultado:
    - capturas geradas em `web/artifacts/visual/inspetor/20260420-171202`

### 7. Extração das métricas do painel administrativo

Status:

- concluído localmente
- ainda não publicado

Problema observado:

- `web/app/domains/admin/services.py` ainda concentrava `buscar_metricas_ia_painel`, embora esse cálculo já representasse um serviço próprio do dashboard administrativo;
- o bloco misturava contagem de tenants, receita agregada, ranking por plano e rollups do catálogo dentro do hotspot principal do domínio admin;
- o corte precisava manter compatibilidade com chamadas indiretas feitas por `routes.py` e `document_operations_summary.py`, preservando a API pública do módulo.

Corte executado:

- criação de `web/app/domains/admin/admin_dashboard_services.py`;
- extração de `buscar_metricas_ia_painel` para o novo módulo;
- `web/app/domains/admin/services.py` passou a atuar como fachada compatível, injetando os helpers necessários de tenant, ordenação, tempo e rollups do catálogo;
- o hotspot principal foi reduzido sem alterar os contratos externos do domínio.

Arquivos alterados:

- `web/app/domains/admin/services.py`
- `web/app/domains/admin/admin_dashboard_services.py`

Validação local já executada:

- `git diff --check`
- `python -m py_compile web/app/domains/admin/services.py web/app/domains/admin/admin_dashboard_services.py`
- `pytest -q web/tests/test_admin_services.py -k 'metricas_e_listagem or agrega_catalogo_e_dashboard'`
  - resultado:
    - `2 passed, 40 deselected`
- `pytest -q web/tests/test_v2_document_operations_summary.py`
  - resultado:
    - `2 passed`

### 8. Extração do fluxo de laudo do workspace

Status:

- concluído localmente
- ainda não publicado

Problema observado:

- `web/static/js/chat/chat_index_page.js` ainda concentrava o fluxo de abrir laudo, iniciar nova inspeção e finalizar coleta, mesmo após a navegação do workspace já ter saído do monólito;
- esse bloco misturava integração com `TarielChatPainel`, API de laudos, modal de nova inspeção e transição de finalização para a mesa;
- o corte precisava preservar os contratos consumidos por `modals.js`, `ui_bindings.js` e pelo bootstrap do inspetor.

Corte executado:

- criação de `web/static/js/inspetor/workspace_report_flow.js`;
- extração de `abrirLaudoPeloHome`, `iniciarInspecao` e `finalizarInspecao` para o novo módulo;
- `web/templates/index.html` passou a carregar o novo script do inspetor;
- `web/static/js/chat/chat_index_page.js` foi reduzido e passou a expor apenas os helpers necessários para o novo módulo.

Arquivos alterados:

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/inspetor/workspace_report_flow.js`
- `web/templates/index.html`

Validação local já executada:

- `git diff --check`
- `node --check web/static/js/inspetor/workspace_report_flow.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `node --check web/static/js/inspetor/bootstrap.js`
- `node --check web/static/js/inspetor/ui_bindings.js`
- `node --check web/static/js/inspetor/modals.js`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
  - resultado:
    - capturas geradas em `web/artifacts/visual/inspetor/20260420-172400`

## Checklist local antes do próximo push

- [x] `git diff --check`
- [x] validação sintática dos arquivos Python alterados
- [x] teste de serviço mais específico do corte backend atual
- [x] teste de rota mais específico do corte backend atual
- [ ] concluir os próximos cortes locais do mesmo pacote
- [ ] revisar o `git diff --stat` final do pacote
- [ ] registrar neste arquivo todos os cortes incluídos no pacote
- [ ] registrar no `docs/LOOP_ORGANIZACAO_FULLSTACK.md` o fechamento do pacote

## Checklist para o push ao GitHub

Executar apenas quando o pacote local estiver fechado.

- [ ] confirmar que só os arquivos do pacote estão staged
- [ ] consolidar commits locais já prontos ou manter commits pequenos em sequência, sem misturar áreas não relacionadas
- [ ] rodar os testes finais do pacote
- [ ] fazer `git push origin checkpoint/20260331-current-worktree`
- [ ] anotar o SHA final publicado
- [ ] atualizar este arquivo com o intervalo publicado

## Checklist de validação pós-push

### GitHub

- [ ] confirmar que a branch remota recebeu o SHA esperado
- [ ] revisar rapidamente o diff publicado para garantir que o pacote remoto bate com o pacote local
- [ ] confirmar que os arquivos não rastreados do usuário não entraram por engano

### Render

Serviço principal:

- `srv-d7ii6f3eo5us73e05920`

Checagens mínimas:

- [ ] listar deploys com `render deploys list srv-d7ii6f3eo5us73e05920 --output json`
- [ ] confirmar que o deploy do SHA publicado entrou na fila
- [ ] acompanhar se o status evolui para `build_in_progress` e depois `live`
- [ ] se falhar, anotar o `deploy id`, a fase da falha e a assinatura principal do erro
- [ ] só começar um novo pacote depois de entender se a regressão veio deste pacote ou de infraestrutura externa

## Resumo pronto para publicação

Preencher quando o pacote local estiver fechado.

- intervalo de commits locais:
  - `[preencher]`
- foco do pacote:
  - `[preencher]`
- áreas afetadas:
  - `[preencher]`
- validação local final:
  - `[preencher]`
- checagens obrigatórias pós-push:
  - GitHub: branch, diff, arquivos incluídos
  - Render: fila, build, status final, erro se houver

## Próximo uso

Toda vez que um novo corte local entrar no pacote:

1. adicionar uma nova subseção em `Cortes locais acumulados desde o último push`;
2. marcar a validação local correspondente;
3. só remover itens pendentes quando o pacote for realmente publicado e conferido.
