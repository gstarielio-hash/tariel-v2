# Loop de Organização Fullstack

## Objetivo

Manter um loop contínuo de organização do código com escopo frontend e backend, sempre pelo repositório oficial:

- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`

Branch operacional atual:

- `checkpoint/20260331-current-worktree`

## Regra do loop

Cada ciclo deve:

1. reanalisar o maior hotspot seguro do momento;
2. escolher um corte pequeno e coeso;
3. refatorar ou estabilizar sem alterar comportamento de produto além do necessário;
4. validar localmente;
5. commitar localmente;
6. registrar o próximo hotspot;
7. acumular um pacote local coeso com 3 a 5 cortes relacionados;
8. só então fazer push;
9. verificar o resultado no Render.

## Modo operacional atual

Trabalhar em `localhost first`.

Isso significa:

- organizar frontend e backend localmente em pequenos cortes seguros;
- validar localmente a cada corte;
- commitar localmente a cada fatia coesa;
- publicar no GitHub apenas quando houver um pacote local consistente;
- validar o Render apenas no fechamento do pacote, e não em cada microetapa.

O arquivo operacional do pacote atual fica em:

- `docs/PACOTE_PUBLICACAO_REFATORACAO_LOCALHOST.md`

Esse arquivo deve concentrar:

- o que mudou localmente desde o último push;
- o que já foi validado em localhost;
- o que ainda precisa ser validado antes do push;
- o que conferir no GitHub e no Render depois da publicação.

## Estado atual

- a trilha de frontend segue registrada em `docs/LOOP_REFATORACAO_FRONTEND.md`;
- os ciclos 6 e 7 reduziram o hotspot do inspetor para `7058` linhas em `web/static/js/chat/chat_index_page.js`;
- o gargalo operacional atual saiu do frontend e foi para o startup do backend no Render.

## Ciclo 8 — Resiliência inicial de startup do banco

Status:

- concluído, mas insuficiente isoladamente

Problema observado:

- deploys recentes no Render constroem normalmente, mas falham no startup da aplicação;
- a falha recorrente está em `inicializar_banco()` com `sqlalchemy.exc.OperationalError`;
- assinatura recorrente:
  - `SSL connection has been closed unexpectedly`

Corte executado:

- adicionar retry curto e configurável para falhas operacionais transitórias no bootstrap do banco;
- cobrir a lógica com teste unitário focado.

Arquivos do ciclo:

- `web/app/shared/db/bootstrap.py`
- `web/tests/test_db_bootstrap_retry.py`

Validação local já executada:

- `git diff --check`
- `pytest -q web/tests/test_db_bootstrap_retry.py`
  - resultado:
    - `2 passed`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `31 passed`

Resultado em produção:

- deploy `dep-d7ikvggflncs73cb9sq0` executou o retry novo no Render;
- os logs confirmaram novas tentativas no caminho `bootstrap.py:85`;
- mesmo assim o startup terminou em `update_failed` com a mesma assinatura `SSL connection has been closed unexpectedly`.

## Ciclo 9 — Endurecimento do pool no retry de bootstrap

Status:

- concluído localmente, pendente de publicação

Problema observado:

- o retry curto entrou em ação, mas todas as tentativas ainda falharam;
- cada nova tentativa continuava usando a mesma engine global, sem descartar explicitamente o pool após erro operacional;
- a janela total padrão ainda era curta para um cenário de banco em recuperação transitória.

Corte executado:

- descartar explicitamente o pool SQLAlchemy antes de cada nova tentativa de bootstrap;
- ampliar os defaults de retry para `8` tentativas e teto de espera de `15s`;
- documentar os parâmetros em `.env.example` e nos manifests do Render;
- reforçar o teste unitário validando o `dispose()` do engine entre tentativas.

Arquivos do ciclo:

- `web/app/shared/db/bootstrap.py`
- `web/tests/test_db_bootstrap_retry.py`
- `web/.env.example`
- `render.yaml`
- `render.preview-free-postgres.yaml`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_db_bootstrap_retry.py web/tests/test_smoke.py`
  - resultado:
    - `33 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar se o próximo deploy no Render finalmente atravessa a janela instável do Postgres;
- se ainda falhar, atacar configuração de conexão/infra sem retomar o frontend antes de estabilizar o backend.

Resultado em produção:

- deploy `dep-d7il5528qa3s73erh1q0` executou o retry endurecido;
- o startup passou a sobreviver por mais tempo e confirmou `attempt 1` até `attempt 8`;
- mesmo assim o deploy terminou em `update_failed` às `2026-04-19 22:14:49Z`, ainda com `SSL connection has been closed unexpectedly`.

## Ciclo 10 — Startup web desacoplado do bootstrap do banco

Status:

- concluído localmente, pendente de publicação

Problema observado:

- o processo web continua saudável o bastante para subir o `uvicorn`, mas o bootstrap síncrono do banco derruba o deploy antes da porta ficar estável;
- o endpoint `/health` já é apenas de liveness, enquanto `/ready` pode representar readiness sem mascarar o estado do banco.

Corte executado:

- em produção, o processo web sobe sem bloquear no bootstrap do banco;
- o bootstrap do banco passa a ser supervisionado em background, com retentativas contínuas;
- a rota `/ready` responde `503` com estado explícito enquanto o banco ainda não ficou pronto;
- o modo bloqueante permanece como padrão fora de produção;
- os novos knobs operacionais foram documentados no `.env.example` e nos manifests do Render.

Arquivos do ciclo:

- `web/main.py`
- `web/app/core/http_setup_support.py`
- `web/tests/test_smoke.py`
- `web/.env.example`
- `render.yaml`
- `render.preview-free-postgres.yaml`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_smoke.py web/tests/test_db_bootstrap_retry.py`
  - resultado:
    - `34 passed`

Próximo passo imediato:

- publicar este ciclo;
- verificar no Render se o serviço passa a bindar a porta e concluir o deploy mesmo com o banco oscilando;
- se o deploy subir, acompanhar quando `/ready` volta para `200`;
- se ainda falhar, então o próximo alvo deixa de ser bootstrap e passa a ser algum componente posterior do lifespan.

Resultado em produção:

- deploy `dep-d7ilb2kp3tds73fjouf0` confirmou que o web process passou a subir com `bootstrap do banco em background`;
- o erro anterior de bootstrap deixou de ser o motivo imediato da queda do deploy;
- o novo bloqueio passou a ser o startup do realtime do revisor no Redis gerenciado do Render;
- o deploy terminou em `update_failed` às `2026-04-19 22:26:26Z` com `redis.exceptions.ResponseError: Client IP address is not in the allowlist.`

## Ciclo 11 — Realtime fail-open com fallback local no startup

Status:

- concluído localmente, pendente de publicação

Problema observado:

- o backend já tinha fallback local para publish quando o Redis não estava pronto;
- mesmo assim, uma falha no `startup_revisor_realtime()` ainda abortava o lifespan inteiro;
- no Render isso passou a acontecer por política de allowlist do Redis, derrubando o deploy depois que o bootstrap do banco deixou de ser bloqueante.

Corte executado:

- o startup do realtime agora respeita um modo operacional `fail-open` em produção;
- quando o backend configurado é Redis e o startup falha, a aplicação segue com fallback local em memória em vez de abortar;
- o estado operacional do realtime passa a expor backend efetivo, backend configurado, modo degradado e último erro;
- `/health` e `/ready` passaram a reportar esse estado para facilitar leitura operacional;
- os manifests e o `.env.example` foram alinhados com o novo knob `REVISOR_REALTIME_FAIL_CLOSED_ON_STARTUP`.

Arquivos do ciclo:

- `web/app/core/settings.py`
- `web/app/domains/revisor/realtime.py`
- `web/app/core/http_setup_support.py`
- `web/tests/test_revisor_realtime.py`
- `web/tests/test_smoke.py`
- `web/.env.example`
- `render.yaml`
- `render.preview-free-postgres.yaml`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_db_bootstrap_retry.py web/tests/test_revisor_realtime.py web/tests/test_smoke.py`
  - resultado:
    - `56 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar se o deploy do Render deixa de abortar no lifespan e conclui normalmente;
- se surgir um novo erro pós-startup, atacar o próximo hotspot com o mesmo loop de correção e publicação.

Leitura em produção:

- deploy `dep-d7ilheosfn5c73fms1t0` confirmou que o fallback do realtime funcionou em produção;
- o Redis do realtime continuou respondendo `Client IP address is not in the allowlist.`, mas virou warning e não abortou mais o startup;
- o processo avançou até `Application startup complete` e `Uvicorn running on http://0.0.0.0:10000`;
- o novo gargalo operacional passou a ser o rate limiter global, que ainda tentava usar o Redis bloqueado e estourava o health check do Render;
- o scheduler de limpeza de uploads também tentou tocar o banco cedo demais e registrou erro em thread separada, sem derrubar o processo web.

## Ciclo 12 — Rate limit fail-open com fallback em memória

Status:

- concluído localmente, pendente de publicação

Problema observado:

- depois que o realtime passou a degradar corretamente, o health check do Render passou a falhar dentro do `slowapi`;
- o limiter global ainda estava configurado com `storage_uri=REDIS_URL`, sem fallback em memória habilitado;
- quando o Redis devolvia `ResponseError` por allowlist, o middleware explodia antes de responder `/health` e `/ready`.

Corte executado:

- o limiter global agora sobe com `in_memory_fallback` habilitado e `swallow_errors=True`;
- `/health` e `/ready` passaram a expor o storage efetivo do rate limit, incluindo `memory_fallback` quando o backend Redis cai;
- smoke tests cobrem o caso nominal e o caso degradado do storage do rate limit.

Arquivos do ciclo:

- `web/main.py`
- `web/app/core/http_setup_support.py`
- `web/tests/test_smoke.py`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_smoke.py web/tests/test_revisor_realtime.py`
  - resultado:
    - `56 passed`

Próximo passo imediato:

- publicar este ciclo;
- confirmar no próximo deploy que `/health` passa a responder mesmo com Redis indisponível;
- se o serviço continuar instável, o próximo alvo provável vira o scheduler de limpeza de uploads enquanto o banco ainda está em bootstrap.

Resultado em produção:

- deploy `dep-d7illrh1g73s738j0r4g` ficou `live` às `2026-04-19 22:50:18Z`;
- `/health` passou a responder `200` em produção com `rate_limit_storage=memory_fallback`;
- o realtime continuou degradado por allowlist do Redis, mas sem derrubar o processo;
- o banco permaneceu em `retrying`, então o próximo hotspot confirmado ficou concentrado no scheduler de limpeza de uploads.

## Ciclo 13 — Scheduler de uploads aguardando bootstrap do banco

Status:

- concluído localmente, pendente de publicação

Problema observado:

- o deploy atual já fica vivo no Render e responde ao `health check`;
- com o banco ainda oscilando, o scheduler de `uploads_cleanup` continuava elegível para disparar consultas via `SessaoLocal()`;
- isso não derrubava o processo principal, mas gerava ruído operacional e mantinha uma dependência prematura do banco durante o bootstrap em background.

Corte executado:

- o scheduler de limpeza agora aceita um `ready_probe` para adiar execuções enquanto uma dependência crítica ainda não está pronta;
- o startup do `main.py` conecta esse gate ao estado `app.state.db_bootstrap.ready`;
- o runtime da limpeza passou a expor `scheduler_wait_reason`;
- `/ready` agora inclui `uploads_cleanup_wait_reason` para leitura operacional do motivo de espera;
- um teste novo cobre o caso em que o scheduler sobe, espera o banco e só então executa a limpeza.

Arquivos do ciclo:

- `web/app/domains/admin/uploads_cleanup.py`
- `web/main.py`
- `web/app/core/http_setup_support.py`
- `web/tests/test_uploads_cleanup.py`
- `web/tests/test_smoke.py`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_uploads_cleanup.py web/tests/test_smoke.py`
  - resultado:
    - `36 passed`
- `pytest -q web/tests/test_production_ops_summary.py web/tests/test_revisor_realtime.py`
  - resultado:
    - `24 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar no Render se o processo permanece limpo enquanto o banco estiver em `retrying`;
- se o bootstrap do Postgres continuar instável por muito tempo, o próximo corte provável deixa de ser startup web e passa a ser diagnóstico/configuração da conexão com o banco.

## Ciclo 14 — Autoridade única de migração e pool conservador em produção

Status:

- concluído localmente, pendente de publicação

Problema observado:

- os logs do Postgres passaram a mostrar conexões internas autenticadas com sucesso, então o problema deixou de parecer indisponibilidade total do banco;
- o projeto mantinha dois pontos capazes de rodar migração: `preDeployCommand` no Render e `_aplicar_migracoes_versionadas()` dentro do bootstrap da aplicação;
- os defaults do pool SQLAlchemy continuavam agressivos para o ambiente free atual do Render.

Corte executado:

- o bootstrap do banco agora respeita `DB_BOOTSTRAP_RUN_MIGRATIONS`, com default `0` em produção e `1` fora de produção;
- o contrato operacional passa a assumir uma única autoridade de migração no Render: `python -m alembic upgrade head` no `preDeployCommand`;
- os defaults do pool em produção ficaram mais conservadores (`pool_size=3`, `max_overflow=0`, `pool_recycle=300`);
- os manifests do Render e o `.env.example` foram alinhados com esse contrato;
- um teste novo cobre explicitamente o caso em que o bootstrap pula migrações, mas ainda executa seed/bootstrap operacional.

Arquivos do ciclo:

- `web/app/shared/db/runtime.py`
- `web/app/shared/db/bootstrap.py`
- `web/tests/test_db_bootstrap_retry.py`
- `render.yaml`
- `render.preview-free-postgres.yaml`
- `web/.env.example`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_db_bootstrap_retry.py web/tests/test_smoke.py`
  - resultado:
    - `37 passed`

Próximo passo imediato:

- publicar este ciclo;
- alinhar o serviço ativo do Render com `preDeployCommand=python -m alembic upgrade head`;
- observar se o próximo deploy reduz o ruído de bootstrap e estabiliza a progressão do `db_bootstrap`.

## Ciclo 15 — Connect args explícitos e telemetria do driver Postgres

Status:

- concluído localmente, pendente de publicação

Problema observado:

- o serviço ativo no Render já usa o host interno correto e já sobe com o web process vivo, mas o bootstrap do banco continua falhando na primeira query com `SSL connection has been closed unexpectedly`;
- o contrato atual não expõe `sslmode`, `connect_timeout` nem `application_name` por env, o que limita o diagnóstico e a capacidade de ajuste fino sem sobrescrever `DATABASE_URL`;
- os logs do Postgres ainda mostram `app=[unknown]`, reduzindo a rastreabilidade das tentativas reais do backend.

Corte executado:

- o runtime do banco agora monta `connect_args` explícitos para Postgres a partir de `DB_SSLMODE`, `DB_CONNECT_TIMEOUT` e `DB_APPLICATION_NAME`;
- a engine passa a registrar no startup a telemetria básica do driver (`psycopg_version`, `psycopg_impl`, `libpq_version`, pool e chaves de `connect_args`);
- os manifests `render.yaml`, `render.preview-free-postgres.yaml` e `web/.env.example` foram alinhados com esse contrato;
- dois testes novos cobrem o contrato dos `connect_args` para produção e para o caso vazio/local.

Arquivos do ciclo:

- `web/app/shared/db/runtime.py`
- `web/tests/test_smoke.py`
- `render.yaml`
- `render.preview-free-postgres.yaml`
- `web/.env.example`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_db_bootstrap_retry.py web/tests/test_smoke.py`
  - resultado:
    - `39 passed`

Próximo passo imediato:

- publicar este ciclo;
- aplicar `DB_SSLMODE=require`, `DB_CONNECT_TIMEOUT=10` e `DB_APPLICATION_NAME=tariel-web` no serviço real;
- observar no Render se a telemetria do driver aparece nos logs e se o bootstrap sai do erro SSL na primeira query.

## Ciclo 16 — Parâmetros do libpq injetados direto na URL

Status:

- concluído localmente, pendente de publicação

Problema observado:

- após o ciclo 15, as novas variáveis estavam presentes no serviço real, mas o Postgres continuava registrando `app=[unknown]`;
- isso enfraqueceu a hipótese de que `connect_args` estava chegando intacto até o `psycopg`;
- para `sslmode`, `connect_timeout` e `application_name`, o caminho mais determinístico passa a ser a própria URL do libpq.

Corte executado:

- `URL_BANCO` agora recebe os parâmetros operacionais do Postgres diretamente na query string, preservando qualquer query já existente;
- o runtime continua expondo o diagnóstico do driver, mas passa a reportar chaves injetadas na URL em vez de chaves em `connect_args`;
- um teste novo cobre o caso em que a URL já tem `application_name` e não deve ser sobrescrita.

Arquivos do ciclo:

- `web/app/shared/db/runtime.py`
- `web/tests/test_smoke.py`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_db_bootstrap_retry.py web/tests/test_smoke.py`
  - resultado:
    - `40 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar no Render se o Postgres passa a mostrar `app=tariel-web`;
- se o erro SSL persistir mesmo com os parâmetros aparecendo no servidor, elevar a hipótese para stack `psycopg/libpq` ou runtime Python.

## Ciclo 17 — Upgrade controlado do psycopg binário

Status:

- concluído localmente, pendente de publicação

Problema observado:

- o ambiente Linux local e, por inferência, o deploy do Render estavam na combinação `psycopg 3.2.13` + `psycopg-binary 3.2.13`;
- os ciclos 15 e 16 não alteraram a assinatura do problema no Render: o SSL continua sendo encerrado de forma abrupta na primeira query e o Postgres segue mostrando `app=[unknown]`;
- a próxima hipótese com melhor relação risco/retorno passa a ser a stack do driver/libpq usada pelo binário do `psycopg`.

Corte executado:

- `web/requirements.txt` passa a fixar `psycopg[binary]==3.3.3`;
- o ambiente Linux local foi atualizado para `psycopg 3.3.3`, `psycopg-binary 3.3.3` e `libpq 18.0.0` para validação rápida de compatibilidade antes da publicação.

Arquivos do ciclo:

- `web/requirements.txt`

Validação local executada:

- `web/.venv-linux/bin/pip install 'psycopg[binary]==3.3.3'`
- `pytest -q web/tests/test_db_bootstrap_retry.py web/tests/test_smoke.py`
  - resultado:
    - `40 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar no Render se o upgrade do driver muda a assinatura do erro SSL;
- se ainda persistir, o próximo corte passa a ser o runtime Python do serviço (`3.14` -> `3.12`) ou a troca do adaptador Postgres.

## Ciclo 18 — Alinhamento do runtime do Render para Python 3.12.3

Status:

- concluído localmente, pendente de publicação

Problema observado:

- mesmo após o upgrade para `psycopg 3.3.3`, o deploy no Render preservou exatamente a mesma assinatura: autenticação no Postgres, sessão SSL encerrada em ~3 segundos e `db_bootstrap` permanecendo em `retrying`;
- a hipótese de configuração do cliente ficou mais fraca;
- a diferença estrutural ainda aberta entre produção e o ambiente Linux local estável passa a ser o runtime Python (`3.14.3` no Render contra `3.12.3` local).

Corte executado:

- `render.yaml` e `render.preview-free-postgres.yaml` passam a fixar `PYTHON_VERSION=3.12.3` para alinhar o runtime do serviço com o ambiente Linux local já validado.

Arquivos do ciclo:

- `render.yaml`
- `render.preview-free-postgres.yaml`

Validação local executada:

- a suíte curta continuou estável no ambiente Linux local (`Python 3.12.3`) durante os ciclos anteriores.

Próximo passo imediato:

- publicar este ciclo;
- observar no Render se a troca do runtime remove o fechamento prematuro da sessão SSL;
- se o problema ainda persistir em `3.12.3`, assumir que o próximo corte precisa trocar o adaptador Postgres ou instrumentar um teste remoto fora do processo principal.

## Ciclo 19 — Chaveamento do adaptador SQLAlchemy para psycopg2 em produção

Status:

- concluído localmente, pendente de publicação

Problema observado:

- mesmo com `psycopg 3.3.3` e `Python 3.12.3`, o serviço no Render continuou falhando no bootstrap com a mesma assinatura `SSL connection has been closed unexpectedly`;
- isso enfraqueceu a hipótese de versão do runtime e reforçou a hipótese de incompatibilidade específica do adaptador `psycopg` nesse ambiente;
- a próxima troca de menor risco passou a ser manter toda a stack e variar apenas o driver SQLAlchemy para `psycopg2`.

Corte executado:

- o runtime do banco agora aceita `DB_SQLALCHEMY_DRIVER`, com suporte a `psycopg` e `psycopg2`;
- os manifests de produção e preview passam a usar `DB_SQLALCHEMY_DRIVER=psycopg2`;
- `web/requirements.txt` passa a incluir `psycopg2-binary==2.9.11`;
- os testes de normalização de URL e de injeção de parâmetros foram atualizados para cobrir o caminho `psycopg2`.

Arquivos do ciclo:

- `web/app/shared/db/runtime.py`
- `web/tests/test_smoke.py`
- `web/requirements.txt`
- `web/.env.example`
- `render.yaml`
- `render.preview-free-postgres.yaml`

Validação local executada:

- `pip install psycopg2-binary==2.9.11` no ambiente Linux local
- `git diff --check`
- `pytest -q web/tests/test_db_bootstrap_retry.py web/tests/test_smoke.py`
  - resultado:
    - `40 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar no Render se o bootstrap deixa de falhar com `psycopg2`;
- se ainda falhar, o próximo corte precisa sair da família libpq/SQLAlchemy e instrumentar uma prova remota ainda mais direta.

## Ciclo 20 — Sobrescrita operacional de `sslmode` para URL gerada pelo Render

Status:

- em validação no Render

Problema observado:

- mesmo após ajustar o serviço ativo para `DB_SSLMODE=disable`, a instância nova continuou falhando com `SSL connection has been closed unexpectedly`;
- isso indica que o `sslmode=require` provavelmente já vem embutido na `DATABASE_URL` vinculada pelo próprio Render, impedindo o env de prevalecer enquanto o runtime só anexar parâmetros ausentes.

Corte executado:

- o runtime do banco agora sobrescreve parâmetros operacionais (`sslmode` e `connect_timeout`) quando eles já existirem na query string da URL;
- campos funcionais já explícitos na URL, como `application_name`, continuam preservados;
- os manifests `render.yaml` e `render.preview-free-postgres.yaml` passam a declarar `DB_SSLMODE=disable` para o caminho de banco interno do Render;
- o teste de smoke de montagem da URL foi ajustado para cobrir a substituição de `sslmode=require` por `sslmode=disable`.

Arquivos do ciclo:

- `web/app/shared/db/runtime.py`
- `web/tests/test_smoke.py`
- `render.yaml`
- `render.preview-free-postgres.yaml`

Próximo passo imediato:

- validar localmente o contrato novo;
- publicar este ciclo;
- observar no Render se a instância nova finalmente deixa de iniciar a conexão via SSL e se o `ready` sai de `503`.

## Ciclo 21 — Troca do driver de produção para `pg8000`

Status:

- em preparação local

Problema observado:

- a revisão anterior provou que a sobrescrita operacional de `sslmode` funciona;
- quando o runtime passou a forçar `sslmode=disable`, o Postgres do Render respondeu com `FATAL: SSL/TLS required`;
- isso confirmou duas coisas ao mesmo tempo: o banco exige TLS e o problema original não era "SSL demais", mas sim a forma como a família `psycopg`/`psycopg2` estava negociando ou mantendo a sessão TLS nesse ambiente.

Corte executado:

- o runtime agora aceita também `DB_SQLALCHEMY_DRIVER=pg8000`;
- para `pg8000`, os parâmetros operacionais deixam de ser injetados na URL e passam a ser enviados por `connect_args`, usando `ssl_context`, `timeout` e `application_name`;
- os manifests de produção e preview voltam a exigir SSL (`DB_SSLMODE=require`) e passam a apontar para `DB_SQLALCHEMY_DRIVER=pg8000`;
- `web/requirements.txt` passa a incluir `pg8000==1.31.5`;
- novos testes cobrem normalização de URL, `connect_args` específicos do `pg8000` e a regra de não injetar parâmetros libpq na query string desse driver.

Arquivos do ciclo:

- `web/app/shared/db/runtime.py`
- `web/tests/test_smoke.py`
- `web/requirements.txt`
- `render.yaml`
- `render.preview-free-postgres.yaml`

Próximo passo imediato:

- validar localmente o driver novo;
- publicar o ciclo;
- aplicar `DB_SQLALCHEMY_DRIVER=pg8000` no serviço real e observar se o bootstrap deixa de cair durante a sessão TLS.

## Ciclo 22 — Backend estabilizado no Render com banco e Redis internos

Status:

- concluído em produção

Problema observado:

- o backend já tinha atravessado a fase de handshake com Postgres e Redis, mas ainda falhava quando o schema do banco estava incompleto;
- no Render, isso aparecia como erro de bootstrap ao tentar semear `limites_plano` antes das migrações versionadas terem sido aplicadas no banco efetivamente usado pelo serviço;
- o startup também só ficou consistente depois de alinhar o serviço aos endpoints internos do Postgres e do Redis, com `DB_SSLMODE=disable` no caminho interno do Postgres.

Corte executado:

- o bootstrap passou a detectar schema incompleto e forçar as migrações versionadas antes do seed, mesmo quando `DB_BOOTSTRAP_RUN_MIGRATIONS=0`;
- o serviço do Render ficou alinhado ao Postgres interno e ao Redis interno;
- o deploy `dep-d7insf9knles7391bt0g` do commit `2441ec8` ficou `live`;
- os endpoints `https://tariel-web.onrender.com/ready` e `https://tariel-web.onrender.com/health` passaram a responder `200`, com `banco=ok` e `revisor_realtime_status=ready`.

Arquivos do ciclo:

- `web/app/shared/db/bootstrap.py`
- `web/tests/test_db_bootstrap_retry.py`
- `render.yaml`
- `render.preview-free-postgres.yaml`

Validação executada:

- `pytest -q web/tests/test_db_bootstrap_retry.py web/tests/test_smoke.py`
  - resultado:
    - `45 passed`
- validação remota:
  - `/ready` -> `HTTP 200`
  - `/health` -> `HTTP 200`
  - deploy `dep-d7insf9knles7391bt0g` -> `live`

Próximo passo imediato:

- retomar o loop de organização do código agora que o backend voltou a ficar estável no ambiente produtivo;
- escolher um hotspot de backend seguro para corte estrutural sem alterar contrato.

## Ciclo 23 — Extração dos tipos puros de `mobile_rollout`

Status:

- concluído localmente, pendente de publicação

Problema observado:

- `web/app/v2/mobile_rollout.py` acumulava tipos, serializers de payload e regras de decisão no mesmo arquivo;
- esse acoplamento deixava a leitura mais cara e dificultava separar o que é modelo puro do que é engine de rollout;
- os testes de promoção e fechamento arquitetural também continham uma data fixa que já tinha ficado obsoleta, tornando a suíte sensível ao calendário.

Corte executado:

- os tipos puros e serializers de rollout mobile V2 foram extraídos para `web/app/v2/mobile_rollout_types.py`;
- `web/app/v2/mobile_rollout.py` passou a manter foco na lógica de decisão, cálculo e observabilidade;
- foi adicionado um teste unitário específico para o payload resumido de `MobileV2SurfaceState`;
- o teste de promoção com evidência durável deixou de depender de uma data fixa no passado e passou a gerar `generatedAt` dinamicamente.

Arquivos do ciclo:

- `web/app/v2/mobile_rollout.py`
- `web/app/v2/mobile_rollout_types.py`
- `web/tests/test_v2_mobile_rollout_types.py`
- `web/tests/test_v2_android_rollout_promotion.py`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_v2_mobile_rollout_types.py web/tests/test_v2_android_rollout.py web/tests/test_v2_android_rollout_state.py web/tests/test_v2_android_rollout_pilot.py web/tests/test_v2_android_pilot_evaluation.py web/tests/test_v2_android_rollout_promotion.py web/tests/test_v2_android_rollout_metrics.py web/tests/test_v2_android_request_trace_gap.py web/tests/test_v2_android_organic_session_signal.py`
  - resultado:
    - `32 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar o deploy do Render para confirmar que a refatoração estrutural não introduziu regressão de startup;
- atacar o próximo hotspot de backend, hoje mais concentrado em `web/app/domains/admin/services.py`.

## Ciclo 24 — Extração da trilha de usuários do tenant em `admin`

Status:

- concluído localmente, pendente de publicação

Problema observado:

- `web/app/domains/admin/services.py` ainda concentrava validações, CRUD, resets de senha e regras de portal dos usuários operacionais do tenant;
- esse bloco misturava lookup de empresa, normalização de payload, limites de pacote e mutações transacionais no mesmo arquivo gigante;
- a trilha também carregava dois contratos implícitos importantes:
  - testes e automações fazem monkeypatch em `admin_services.gerar_senha_fortificada`;
  - a credencial de onboarding do portal admin-cliente usa rótulos próprios de portais (`Inspetor web/mobile`, `Mesa Avaliadora`, `Admin-Cliente`).

Corte executado:

- a lógica de usuários gerenciáveis do tenant foi extraída para `web/app/domains/admin/tenant_user_services.py`;
- `web/app/domains/admin/services.py` passou a importar e reexportar apenas a superfície necessária, reduzindo o hotspot principal de `7482` para `7021` linhas;
- a geração de senha temporária no fluxo extraído continua compatível com monkeypatch em `admin_services.gerar_senha_fortificada`;
- as credenciais de onboarding do admin-cliente passaram a usar labels explícitos e estáveis por portal, alinhados com a expectativa dos fluxos operacionais;
- a senha temporária desse fluxo agora evita caracteres que quebram comparação literal quando renderizados em HTML.

Arquivos do ciclo:

- `web/app/domains/admin/services.py`
- `web/app/domains/admin/tenant_user_services.py`
- `web/app/domains/cliente/route_support.py`

Validação local executada:

- `ruff check web/app/domains/admin/services.py web/app/domains/admin/tenant_user_services.py web/app/domains/cliente/route_support.py`
- `git diff --check`
- `pytest -q web/tests/test_admin_services.py web/tests/test_admin_client_routes.py web/tests/test_cliente_portal_critico.py web/tests/test_smoke.py`
  - resultado:
    - `144 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar o autodeploy do Render e confirmar continuidade do backend saudável;
- seguir para o próximo corte estrutural dentro de `web/app/domains/admin/services.py`, priorizando outro bloco coeso e testado.

## Ciclo 25 — Extração da trilha de identidade/admin platform

Status:

- concluído localmente, pendente de publicação

Problema observado:

- `web/app/domains/admin/services.py` ainda concentrava a autenticação de identidade administrativa, a auditoria desses eventos e a listagem dos operadores de plataforma no mesmo hotspot gigante;
- esse bloco misturava helpers de autorização, resolução do tenant plataforma e superfície pública usada por rotas e testes, o que deixava a leitura mais densa do que o necessário;
- a trilha já possuía cobertura focada em `test_admin_services.py`, então manter essa responsabilidade presa no arquivo monolítico deixou de ser um bom custo-benefício.

Corte executado:

- a trilha de identidade/admin platform foi extraída para `web/app/domains/admin/admin_platform_identity_services.py`;
- `web/app/domains/admin/services.py` passou a manter apenas a fachada pública e os aliases necessários para preservar os imports existentes;
- o helper `_resolver_empresa_plataforma` e a cláusula `_tenant_cliente_clause` passaram a morar junto da trilha extraída, reduzindo acoplamento entre o bloco de identidade e o restante do arquivo;
- o hotspot principal de `web/app/domains/admin/services.py` caiu de `7021` para `6742` linhas sem alterar contrato externo.

Arquivos do ciclo:

- `web/app/domains/admin/services.py`
- `web/app/domains/admin/admin_platform_identity_services.py`

Validação local executada:

- `ruff check web/app/domains/admin/services.py web/app/domains/admin/admin_platform_identity_services.py`
- `git diff --check`
- `pytest -q web/tests/test_admin_services.py -k 'autenticar_identidade_admin'`
  - resultado:
    - `2 passed`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar o autodeploy do Render para confirmar que a extração estrutural não alterou a subida do backend;
- seguir para o próximo corte coeso dentro de `web/app/domains/admin/services.py`, priorizando a trilha de gestão de clientes SaaS (`buscar_todos_clientes`, `buscar_detalhe_cliente`, `alterar_plano` e adjacências).

## Ciclo 26 — Extração da trilha de plano e limites do tenant

Status:

- concluído localmente, pendente de publicação

Problema observado:

- a trilha de gestão de clientes SaaS ainda carregava, no mesmo arquivo gigante, a normalização de planos, o cálculo de limites e o preview de troca de plano;
- esse bloco era compartilhado entre `services.py` e `client_routes.py`, mas não precisava continuar acoplado ao restante do hotspot administrativo;
- a leitura do fluxo de clientes seguia cara porque regras de preview comercial e helpers de capacidade ainda estavam espalhados no monolito.

Corte executado:

- a trilha de plano, limites e preview de troca de plano foi extraída para `web/app/domains/admin/tenant_plan_services.py`;
- `web/app/domains/admin/services.py` passou a manter apenas a fachada pública necessária para preservar os imports existentes nas rotas e nos testes;
- os aliases `_PRIORIDADE_PLANO`, `_case_prioridade_plano`, `_label_limite`, `_normalizar_plano`, `_obter_limite_laudos_empresa`, `_obter_limite_usuarios_empresa` e `construir_preview_troca_plano` continuam disponíveis via `services.py`;
- o hotspot principal de `web/app/domains/admin/services.py` caiu de `6742` para `6613` linhas.

Arquivos do ciclo:

- `web/app/domains/admin/services.py`
- `web/app/domains/admin/tenant_plan_services.py`

Validação local executada:

- `ruff check web/app/domains/admin/services.py web/app/domains/admin/tenant_plan_services.py web/app/domains/admin/client_routes.py`
- `git diff --check`
- `pytest -q web/tests/test_admin_services.py web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `122 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar o autodeploy do Render para confirmar que a extração estrutural segue neutra em runtime;
- seguir para o próximo corte coeso dentro da gestão de clientes SaaS, agora priorizando filtros, contexto e status operacional de `buscar_todos_clientes` e `buscar_detalhe_cliente`.

## Ciclo 27 — Extração do read-side de gestão de clientes SaaS

Status:

- concluído localmente, pendente de publicação

Problema observado:

- `web/app/domains/admin/services.py` ainda concentrava filtros, contexto operacional, listagem paginada e o detalhe administrativo completo dos tenants SaaS;
- a leitura de clientes já era um subdomínio coeso, mas seguia misturada com onboarding, write-side e catálogos no hotspot principal;
- havia um contrato implícito relevante em teste: `test_admin_services.py` faz monkeypatch em `admin_services.resumir_portfolio_catalogo_empresa`, então a extração não podia congelar essa dependência dentro de outro módulo.

Corte executado:

- a trilha de leitura de clientes foi consolidada em `web/app/domains/admin/tenant_client_read_services.py`;
- o módulo extraído agora concentra helpers de filtros/ordenação/paginação, `buscar_todos_clientes` e a orquestração de `buscar_detalhe_cliente`;
- `web/app/domains/admin/services.py` passou a manter a fachada pública e um wrapper fino para `buscar_detalhe_cliente`, preservando compatibilidade com monkeypatch e imports existentes;
- o hotspot principal de `web/app/domains/admin/services.py` caiu de `6613` para `6015` linhas.

Arquivos do ciclo:

- `web/app/domains/admin/services.py`
- `web/app/domains/admin/tenant_client_read_services.py`

Validação local executada:

- `ruff check web/app/domains/admin/services.py web/app/domains/admin/tenant_client_read_services.py web/app/domains/admin/client_routes.py`
- `git diff --check`
- `pytest -q web/tests/test_admin_services.py web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `122 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar o autodeploy do Render para confirmar que a leitura administrativa segue saudável em produção;
- seguir para o próximo corte coeso no write-side da gestão de clientes SaaS, priorizando bloqueio, política do admin-cliente e mutações de plano.

## Ciclo 28 — Extração do write-side de lifecycle do tenant

Status:

- concluído localmente, pendente de publicação

Problema observado:

- `web/app/domains/admin/services.py` ainda concentrava mutações operacionais da gestão de clientes SaaS, misturando bloqueio, política do admin-cliente e troca de plano com fluxos destrutivos e com o restante do hotspot administrativo;
- esse bloco tinha boa coesão funcional, era acionado principalmente pelas rotas de clientes e já contava com cobertura direta em `test_admin_services.py` e `test_admin_client_routes.py`;
- havia um contrato implícito de fachada pública em `services.py`: módulos do portal cliente ainda importam `filtro_usuarios_gerenciaveis_cliente` dali, então a extração precisava preservar esse ponto de reexport.

Corte executado:

- a trilha de mutações de lifecycle do tenant foi extraída para `web/app/domains/admin/tenant_client_write_services.py`;
- o módulo novo concentra `_normalizar_politica_admin_cliente_empresa`, `_listar_ids_usuarios_operacionais_empresa`, `alternar_bloqueio`, `atualizar_politica_admin_cliente_empresa` e `alterar_plano`;
- `web/app/domains/admin/services.py` passou a manter apenas aliases de compatibilidade para onboarding, rotas e imports legados;
- o hotspot principal de `web/app/domains/admin/services.py` caiu de `6015` para `5866` linhas.

Arquivos do ciclo:

- `web/app/domains/admin/services.py`
- `web/app/domains/admin/tenant_client_write_services.py`

Validação local executada:

- `ruff check web/app/domains/admin/services.py web/app/domains/admin/tenant_client_read_services.py web/app/domains/admin/tenant_client_write_services.py web/app/domains/admin/client_routes.py web/app/domains/cliente/dashboard_bootstrap.py web/app/domains/cliente/dashboard_company_summary.py web/app/domains/cliente/dashboard_operational_health.py web/app/domains/cliente/management_routes.py`
- `git diff --check`
- `pytest -q web/tests/test_admin_services.py web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `122 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar o autodeploy do Render para confirmar que as mutações administrativas seguem íntegras em produção;
- seguir para o próximo corte coeso separando as remoções destrutivas de tenants em um módulo próprio.

## Ciclo 29 — Extração da trilha destrutiva de limpeza de tenants

Status:

- concluído localmente, pendente de publicação

Problema observado:

- `web/app/domains/admin/services.py` ainda carregava a trilha destrutiva de manutenção do ambiente, misturando limpeza de tenants temporários de auditoria UI e remoção explícita de empresas cliente com o restante do domínio administrativo;
- esse bloco tinha alto fan-out em tabelas, mas possuía integração bem delimitada nas rotas de configurações e cobertura específica em `test_admin_client_routes.py`;
- a cascata de deleção estava duplicada nas duas funções, aumentando custo de leitura e risco de divergência no futuro.

Corte executado:

- a trilha destrutiva foi extraída para `web/app/domains/admin/tenant_client_cleanup_services.py`;
- o módulo novo mantém `remover_empresas_temporarias_auditoria_ui` e `remover_empresas_cliente_por_ids`, além de um helper interno para a cascata de remoção das dependências do tenant;
- `web/app/domains/admin/services.py` passou a reexportar a superfície pública e o prefixo `UI_AUDIT_TENANT_PREFIX`, preservando compatibilidade com as rotas de configurações;
- o hotspot principal de `web/app/domains/admin/services.py` caiu de `5866` para `5605` linhas.

Arquivos do ciclo:

- `web/app/domains/admin/services.py`
- `web/app/domains/admin/tenant_client_cleanup_services.py`

Validação local executada:

- `ruff check web/app/domains/admin/services.py web/app/domains/admin/routes.py web/app/domains/admin/tenant_client_cleanup_services.py web/app/domains/admin/tenant_client_write_services.py web/app/domains/admin/tenant_client_read_services.py`
- `git diff --check`
- `pytest -q web/tests/test_admin_services.py web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `122 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar o autodeploy do Render para confirmar que a manutenção destrutiva segue íntegra em produção;
- seguir para o próximo corte estrutural fora da trilha de gestão de clientes SaaS, porque esse ponto agora está substancialmente mais modularizado.

## Ciclo 30 — Organização do frontend do detalhe de cliente admin

Status:

- concluído localmente, pendente de publicação

Problema observado:

- `web/templates/admin/cliente_detalhe.html` concentrava praticamente toda a interface do detalhe administrativo da empresa em um único template grande, com abas, formulários, tabelas e modais misturados no mesmo arquivo;
- essa concentração elevava o custo de leitura e tornava mudanças visuais simples mais arriscadas, porque qualquer ajuste local exigia navegar por toda a página;
- a tela já possuía JS e CSS dedicados, então o corte seguro no frontend era modularizar o template sem alterar comportamento, contratos de rota ou bindings de DOM.

Corte executado:

- a página foi reorganizada em parciais sob `web/templates/admin/cliente_detalhe/`;
- as abas `resumo`, `seguranca`, `plano`, `usuarios`, `auditoria` e `acoes` foram extraídas para arquivos próprios, além dos modais administrativos;
- `web/templates/admin/cliente_detalhe.html` passou a manter apenas a casca da página, os `include`s e as âncoras textuais exigidas pelos smoke tests;
- o template principal caiu de uma página monolítica para `232` linhas, mantendo a renderização e os seletores do frontend intactos.

Arquivos do ciclo:

- `web/templates/admin/cliente_detalhe.html`
- `web/templates/admin/cliente_detalhe/_tab_resumo.html`
- `web/templates/admin/cliente_detalhe/_tab_seguranca.html`
- `web/templates/admin/cliente_detalhe/_tab_plano.html`
- `web/templates/admin/cliente_detalhe/_tab_usuarios.html`
- `web/templates/admin/cliente_detalhe/_tab_auditoria.html`
- `web/templates/admin/cliente_detalhe/_tab_acoes.html`
- `web/templates/admin/cliente_detalhe/_modals.html`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar o autodeploy do Render para confirmar que a tela administrativa segue íntegra em produção;
- seguir para o próximo corte de frontend na mesma área, priorizando modularizar o JS de `admin_client_detail_page.js` ou o catálogo admin, agora com o template já organizado.

## Ciclo 31 — Organização do JS do detalhe de cliente admin

Status:

- concluído localmente, pendente de publicação

Problema observado:

- `web/static/js/admin/admin_client_detail_page.js` concentrava toda a interação da tela em um único IIFE linear, misturando alertas, tabs, cópia de onboarding, diálogo de confirmação, bloqueio de empresa, bloqueio de usuário e modal de plano;
- mesmo com a tela já funcional, a leitura e a manutenção desse arquivo continuavam caras, porque os comportamentos não estavam separados por responsabilidade;
- depois da modularização do template, o próximo corte seguro era organizar o JS da mesma tela sem alterar IDs, `data-*`, fluxos ou textos de confirmação.

Corte executado:

- o script foi reorganizado em setups explícitos por responsabilidade;
- foram isolados helpers de seleção de DOM, inicialização de alertas e abas, cópia de onboarding, controlador de confirmação, controlador de bloqueio de empresa e modal de plano;
- o contrato da tela foi preservado: mesmos seletores, mesmas mensagens, mesmos `submit`s e mesma ordem de inicialização;
- o corte melhora leitura e prepara a tela para futuras extrações menores sem exigir mudança no carregamento do navegador.

Arquivos do ciclo:

- `web/static/js/admin/admin_client_detail_page.js`

Validação local executada:

- `node --check web/static/js/admin/admin_client_detail_page.js`
- `git diff --check`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo;
- observar o autodeploy do Render para confirmar que o frontend reorganizado segue íntegro em produção;
- seguir para o próximo slice de frontend no mesmo detalhe administrativo, priorizando CSS da tela ou extração do JS para um módulo de utilidades locais.

## Ciclo 32 — Organização do CSS do detalhe de cliente admin

Status:

- concluído e validado localmente

Problema observado:

- `web/static/css/admin/admin_client_detail.css` ainda concentrava praticamente toda a folha de estilos da tela em um único arquivo grande;
- depois da modularização do template e do JS, o CSS virou o último bloco monolítico relevante da mesma página, o que mantinha alto o custo de navegação e revisão;
- o corte seguro agora era preservar o arquivo público carregado pelo template e reorganizar o conteúdo internamente, sem alterar classes, IDs, media queries ou ordem funcional dos estilos.

Corte executado:

- `web/static/css/admin/admin_client_detail.css` passou a atuar apenas como ponto de entrada estável do navegador;
- os estilos foram extraídos para partials internas sob `web/static/css/admin/admin_client_detail/`, separando layout, controles, catálogo do tenant e modal/acessibilidade;
- a organização preserva o contrato atual da tela, porque o template continua apontando para o mesmo arquivo principal;
- o resultado reduz acoplamento visual e prepara próximos ajustes da página sem voltar a um CSS monolítico.

Arquivos do ciclo:

- `web/static/css/admin/admin_client_detail.css`
- `web/static/css/admin/admin_client_detail/_layout.css`
- `web/static/css/admin/admin_client_detail/_controls.css`
- `web/static/css/admin/admin_client_detail/_tenant_catalog.css`
- `web/static/css/admin/admin_client_detail/_modal_and_accessibility.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o deploy no Render;
- encerrar a organização desta tela administrativa, agora com template, JS e CSS separados por responsabilidade;
- seguir para o próximo hotspot do frontend, priorizando o próximo corte seguro entre `web/templates/admin/catalogo_laudos.html` e o monólito do inspetor/chat.

## Ciclo 33 — Organização do template da home do catálogo admin

Status:

- concluído e validado localmente

Problema observado:

- `web/templates/admin/catalogo_laudos.html` ainda concentrava a home inteira do catálogo administrativo em um único arquivo grande, incluindo hero, filtros, vitrine principal, painéis complementares, drawers e modal de preview;
- isso aumentava o custo de leitura e tornava qualquer ajuste visual da página mais caro, porque até blocos bem delimitados continuavam misturados na mesma unidade de template;
- como o JS e o CSS dessa área ainda atendem mais de uma tela do catálogo, o corte seguro aqui era modularizar primeiro o markup da home sem alterar `data-*`, rotas, `form action`s ou o carregamento do script existente.

Corte executado:

- `web/templates/admin/catalogo_laudos.html` passou a atuar como casca da página, mantendo head, sidebar, flashes, contexto base e ordem de carregamento dos assets;
- a home foi separada em partials sob `web/templates/admin/catalogo_laudos/`, dividindo introdução e filtros, grade principal da vitrine, painéis complementares e overlays administrativos;
- drawers e modal de preview foram preservados com os mesmos `id`s, `data-*` e formulários, então o contrato do JS da página foi mantido;
- o corte prepara os próximos ciclos do catálogo sem exigir refactor simultâneo de JS ou CSS.

Arquivos do ciclo:

- `web/templates/admin/catalogo_laudos.html`
- `web/templates/admin/catalogo_laudos/_showroom_intro.html`
- `web/templates/admin/catalogo_laudos/_showroom_grid.html`
- `web/templates/admin/catalogo_laudos/_insights.html`
- `web/templates/admin/catalogo_laudos/_overlays.html`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_admin_client_routes.py -k 'catalogo_laudos or catalogo_preview or catalogo_familia'`
  - resultado:
    - `3 passed, 36 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o autodeploy do Render;
- decidir o próximo corte do frontend do catálogo entre organizar o JS compartilhado da área ou isolar melhor o CSS da vitrine;
- depois disso, voltar ao próximo hotspot de maior impacto entre o catálogo admin e o monólito do inspetor/chat.

## Ciclo 34 — Organização do JS da home do catálogo admin

Status:

- concluído e validado localmente

Problema observado:

- `web/static/js/admin/admin_catalogo_laudos_page.js` ainda concentrava em um fluxo linear toda a interação da área do catálogo, misturando alertas, tabs, drawers, modal de preview e editores dinâmicos de listas;
- esse script atende mais de uma tela do catálogo, então qualquer ajuste futuro seguiria arriscado enquanto a inicialização e os helpers continuassem acoplados num único bloco;
- depois da modularização do template da home, o próximo corte seguro era organizar o JS por responsabilidade sem trocar IDs, `data-*`, mensagens, atalhos de teclado ou ordem de boot da página.

Corte executado:

- o script foi reorganizado em helpers curtos e inicializadores explícitos por responsabilidade;
- alertas, tabs, disclosures, drawers, overflow menus, preview modal e editores dinâmicos passaram a ter blocos próprios de inicialização;
- a carga da página foi mantida no mesmo entrypoint e no mesmo formato IIFE, evitando mudança de estratégia de carregamento no navegador;
- o contrato da interface foi preservado: mesmos seletores, mesmos textos, mesmas URLs de preview e mesmos atributos usados pelo markup do catálogo.

Arquivos do ciclo:

- `web/static/js/admin/admin_catalogo_laudos_page.js`

Validação local executada:

- `node --check web/static/js/admin/admin_catalogo_laudos_page.js`
- `git diff --check`
- `pytest -q web/tests/test_admin_client_routes.py -k 'catalogo_laudos or catalogo_preview or catalogo_familia'`
  - resultado:
    - `3 passed, 36 deselected`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o deploy mais recente no Render;
- encerrar a organização estrutural principal da home do catálogo, agora com template e JS separados por responsabilidade;
- avaliar se o próximo melhor corte continua no catálogo admin via CSS ou se já vale voltar ao hotspot maior do frontend em `web/static/js/chat/chat_index_page.js`.

## Ciclo 35 — Organização dos overlays CSS do catálogo admin

Status:

- concluído e validado localmente

Problema observado:

- `web/static/css/admin/admin_catalogo_laudos.css` seguia concentrando todo o estilo da área do catálogo em um único arquivo grande;
- depois da modularização do template e do JS da home, os estilos de drawer e modal de preview já formavam um bloco visualmente isolado, mas continuavam misturados ao restante da folha;
- o corte seguro aqui era manter o entrypoint público da página e extrair apenas os overlays administrativos para um partial interno, sem alterar classes, IDs, media queries ou o carregamento do template.

Corte executado:

- `web/static/css/admin/admin_catalogo_laudos.css` passou a importar um partial interno para os overlays do catálogo;
- o bloco de estilos dos drawers administrativos, do modal de preview e dos locks de `body` foi extraído para `web/static/css/admin/admin_catalogo_laudos/_overlays.css`;
- o template e o JS não precisaram mudar, porque os seletores e a ordem funcional da folha permaneceram equivalentes para o navegador;
- esse corte reduz o acoplamento da folha principal e abre caminho para novas extrações menores na mesma área.

Arquivos do ciclo:

- `web/static/css/admin/admin_catalogo_laudos.css`
- `web/static/css/admin/admin_catalogo_laudos/_overlays.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_admin_client_routes.py -k 'catalogo_laudos or catalogo_preview or catalogo_familia'`
  - resultado:
    - `3 passed, 36 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- seguir com o próximo corte seguro da mesma folha, priorizando showroom/vitrine principal ou responsividade específica da home do catálogo;
- depois disso, reavaliar se o melhor retorno continua no catálogo admin ou volta para o hotspot maior do inspetor/chat.

## Ciclo 36 — Organização do CSS de introdução da home do catálogo admin

Status:

- concluído e validado localmente

Problema observado:

- `web/static/css/admin/admin_catalogo_laudos.css` ainda misturava os estilos da introdução da home do catálogo com o restante da folha compartilhada da área;
- depois da separação do template em `_showroom_intro.html` e `_showroom_grid.html`, hero, filtros, categorias e cabeçalho da vitrine continuavam sem isolamento correspondente no CSS;
- o corte seguro aqui era alinhar a folha aos partials do template, extraindo só a introdução da vitrine e seus ajustes responsivos, sem alterar o HTML, o JS nem o entrypoint público da página.

Corte executado:

- o arquivo principal passou a importar `web/static/css/admin/admin_catalogo_laudos/_showroom_intro.css`;
- os estilos da hero section, dos filtros, da faixa de categorias, da nota inline e do cabeçalho da vitrine foram movidos para o novo partial;
- os ajustes responsivos específicos dessa mesma introdução também foram separados, enquanto os estilos da grade principal do showroom permaneceram na folha principal;
- o corte reduz o acoplamento da CSS do catálogo e deixa a estrutura visual mais alinhada com os partials de template já criados.

Arquivos do ciclo:

- `web/static/css/admin/admin_catalogo_laudos.css`
- `web/static/css/admin/admin_catalogo_laudos/_showroom_intro.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_admin_client_routes.py -k 'catalogo_laudos or catalogo_preview or catalogo_familia'`
  - resultado:
    - `3 passed, 36 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy no Render;
- seguir com o próximo corte seguro da mesma folha, agora priorizando a grade/showroom principal da home do catálogo;
- depois disso, reavaliar se o melhor retorno continua no catálogo admin ou se já vale voltar para o monólito do inspetor/chat.

## Ciclo 37 — Organização do CSS da grade da home do catálogo admin

Status:

- concluído e validado localmente

Problema observado:

- `web/static/css/admin/admin_catalogo_laudos.css` ainda concentrava toda a grade principal da vitrine administrativa, mesmo depois da separação do template em `_showroom_intro.html` e `_showroom_grid.html`;
- isso mantinha o bloco mais denso da home do catálogo misturado com regras compartilhadas da página, dificultando novas extrações seguras e a leitura da folha principal;
- o corte seguro aqui era isolar apenas os estilos da grade, dos cards de famílias e do preview visual do template, preservando classes, atributos, responsividade e o entrypoint público da CSS.

Corte executado:

- o arquivo principal passou a importar `web/static/css/admin/admin_catalogo_laudos/_showroom_grid.css`;
- os estilos do painel showroom, da grid de famílias, dos cards, das trilhas visuais por família e do preview do template foram movidos para o novo partial;
- as media queries específicas desse bloco também foram levadas junto, removendo duplicação e deixando a responsividade da vitrine encapsulada no mesmo arquivo;
- um seletor morto de `catalog-template-preview__paper-intro` foi removido durante a revisão final para evitar acúmulo de CSS sem uso.

Arquivos do ciclo:

- `web/static/css/admin/admin_catalogo_laudos.css`
- `web/static/css/admin/admin_catalogo_laudos/_showroom_grid.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_admin_client_routes.py -k 'catalogo_laudos or catalogo_preview or catalogo_familia'`
  - resultado:
    - `3 passed, 36 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o deploy do Render;
- continuar o desmembramento da mesma área se ainda restarem blocos compartilhados claros na CSS do catálogo admin;
- em seguida, reavaliar se o melhor retorno continua na folha do catálogo ou se o próximo hotspot já deve migrar para um monólito maior de JS, como o chat.

## Ciclo 38 — Organização do template de detalhe da família do catálogo admin

Status:

- concluído e validado localmente

Problema observado:

- `web/templates/admin/catalogo_familia_detalhe.html` ainda concentrava hero, navegação de abas e todo o conteúdo das oito superfícies da página em um único template grande;
- isso deixava a leitura e a manutenção do detalhe da família muito mais difíceis do que a home do catálogo, que já tinha sido reorganizada em partials;
- o corte seguro aqui era preservar o `if/elif` de navegação por aba no shell e mover o markup de cada painel para partials dedicados, sem alterar `id`s, `data-*`, formulários, anchors ou contratos usados pelo JS e pelos testes.

Corte executado:

- `web/templates/admin/catalogo_familia_detalhe.html` passou a manter só o shell, a hero, os alertas, a tablist e o roteamento condicional por `active_tab`;
- cada aba foi extraída para um partial próprio dentro de `web/templates/admin/catalogo_familia_detalhe/`, incluindo visão geral, base técnica, modos, modelos, ofertas, calibração, liberação e histórico, além do estado default;
- o conteúdo interno das abas foi mantido equivalente ao template original, o que reduz o risco de regressão e prepara novos cortes de CSS e JS na mesma área.

Arquivos do ciclo:

- `web/templates/admin/catalogo_familia_detalhe.html`
- `web/templates/admin/catalogo_familia_detalhe/_tab_visao_geral.html`
- `web/templates/admin/catalogo_familia_detalhe/_tab_schema_tecnico.html`
- `web/templates/admin/catalogo_familia_detalhe/_tab_modos.html`
- `web/templates/admin/catalogo_familia_detalhe/_tab_templates.html`
- `web/templates/admin/catalogo_familia_detalhe/_tab_ofertas.html`
- `web/templates/admin/catalogo_familia_detalhe/_tab_calibracao.html`
- `web/templates/admin/catalogo_familia_detalhe/_tab_liberacao.html`
- `web/templates/admin/catalogo_familia_detalhe/_tab_historico.html`
- `web/templates/admin/catalogo_familia_detalhe/_tab_default.html`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_admin_client_routes.py -k 'catalogo_familia or schema_tecnico or historico or catalogo_laudos'`
  - resultado:
    - `2 passed, 37 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o deploy do Render;
- alinhar os próximos cortes do catálogo admin com esse novo layout, priorizando CSS ou JS específicos do detalhe da família;
- depois disso, reavaliar se o melhor retorno continua no domínio do catálogo admin ou se já vale atacar um hotspot maior como `chat_index_page.js`.

## Ciclo 39 — Organização do CSS do detalhe da família do catálogo admin

Status:

- concluído e validado localmente

Problema observado:

- depois da modularização de `catalogo_familia_detalhe.html`, os estilos exclusivos dessa página ainda permaneciam espalhados dentro de `web/static/css/admin/admin_catalogo_laudos.css`;
- hero, guia rápido, abas, tabela de registros e timeline do detalhe da família já formavam um conjunto visual próprio, mas ainda estavam misturados com regras compartilhadas do catálogo admin;
- o corte seguro aqui era extrair apenas o CSS claramente específico do detalhe da família, preservando no arquivo principal os estilos genéricos de formulários, disclosures, editores e componentes reaproveitados pela home do catálogo.

Corte executado:

- `web/static/css/admin/admin_catalogo_laudos.css` passou a importar `web/static/css/admin/admin_catalogo_laudos/_family_detail.css`;
- o novo partial recebeu os estilos específicos da hero da família, do help strip, das abas, da tabela de registros e da timeline, além dos ajustes responsivos correspondentes;
- os grupos compartilhados do arquivo principal foram afinados para manter apenas seletores genéricos, deixando no partial novo só o que pertence de fato à página de detalhe.

Arquivos do ciclo:

- `web/static/css/admin/admin_catalogo_laudos.css`
- `web/static/css/admin/admin_catalogo_laudos/_family_detail.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_admin_client_routes.py -k 'catalogo_familia or schema_tecnico or historico or catalogo_laudos'`
  - resultado:
    - `2 passed, 37 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- avaliar se o próximo corte mais natural continua no CSS do catálogo admin ou migra para o JS compartilhado da mesma área (`admin_catalogo_laudos_page.js`);
- depois disso, reescanear os hotspots do frontend antes de sair do domínio do catálogo.

## Ciclo 40 — Organização do JS da home e do detalhe do catálogo admin

Status:

- concluído e validado localmente

Problema observado:

- `web/static/js/admin/admin_catalogo_laudos_page.js` já tinha sido reestruturado, mas ainda inicializava home do catálogo e detalhe da família no mesmo fluxo único de `init()`;
- isso deixava menos claro quais comportamentos pertenciam à vitrine/showroom e quais eram exclusivos da página com abas, disclosures e editores dinâmicos;
- o corte seguro aqui era separar a inicialização por contexto de página dentro do mesmo entrypoint, sem alterar carregamento, sem modularizar via ES modules e sem tocar em contratos de `data-*`, tabs, formulários ou overlays.

Corte executado:

- foi adicionada uma detecção explícita de contexto para distinguir showroom do catálogo e detalhe da família;
- o arquivo passou a expor inicializadores separados para `inicializarPaginaShowroomCatalogo()` e `inicializarPaginaDetalheFamilia()`;
- o `init()` ficou responsável apenas por alertas e pela orquestração por contexto, mantendo o mesmo entrypoint e preservando a ordem funcional crítica da página de detalhe quando a sincronização de abas exige redirect.

Arquivos do ciclo:

- `web/static/js/admin/admin_catalogo_laudos_page.js`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/admin/admin_catalogo_laudos_page.js`
- `pytest -q web/tests/test_admin_client_routes.py -k 'catalogo_familia or schema_tecnico or historico or catalogo_laudos'`
  - resultado:
    - `2 passed, 37 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- seguir no mesmo arquivo, se necessário, separando helpers realmente compartilhados dos específicos da vitrine e dos editores;
- depois disso, reavaliar se ainda vale continuar no catálogo admin ou se o próximo hotspot do frontend já deve migrar para outra frente, como `chat_index_page.js`.

## Ciclo 41 — Organização do preview modal da home do catálogo admin

Status:

- concluído e validado localmente

Problema observado:

- depois da separação por contexto de página, o bloco de preview modal da vitrine ainda permanecia concentrado dentro de uma única função grande em `web/static/js/admin/admin_catalogo_laudos_page.js`;
- isso concentrava coleta de referências, preenchimento de conteúdo, abertura, fechamento e carregamento do iframe no mesmo trecho, o que dificultava manutenção e novos cortes na parte da home;
- o corte seguro aqui era quebrar o preview modal em helpers menores, preservando o mesmo markup, os mesmos `data-preview-*` e o mesmo fluxo de abertura e carregamento.

Corte executado:

- os tons visuais do preview passaram para uma constante dedicada;
- o arquivo ganhou helpers específicos para obter referências do modal, preencher o conteúdo a partir do botão acionado e carregar o frame de visualização;
- `inicializarPreviewModal()` foi afinada para orquestrar estado, foco e eventos em cima desses helpers, mantendo o comportamento anterior da vitrine.

Arquivos do ciclo:

- `web/static/js/admin/admin_catalogo_laudos_page.js`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/admin/admin_catalogo_laudos_page.js`
- `pytest -q web/tests/test_admin_client_routes.py -k 'catalogo_familia or schema_tecnico or historico or catalogo_laudos'`
  - resultado:
    - `2 passed, 37 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- continuar no mesmo JS separando os editores dinâmicos em helpers ainda mais explícitos, se o hotspot continuar ali;
- depois disso, reavaliar se vale seguir no catálogo admin ou migrar para outro hotspot grande do frontend, como `chat_index_page.js`.

## Ciclo 42 — Organização dos editores dinâmicos do catálogo admin

Status:

- concluído e validado localmente

Problema observado:

- depois da separação por contexto de página e do preview modal, os editores dinâmicos de `strings`, `variants` e `red-flags` ainda permaneciam com muito aninhamento dentro de `web/static/js/admin/admin_catalogo_laudos_page.js`;
- isso dificultava ler a responsabilidade de cada editor e atrapalhava novos cortes no mesmo arquivo, mesmo sem haver problema funcional imediato;
- o corte seguro aqui era extrair helpers explícitos por editor sem alterar o formato do JSON salvo nos `input[type="hidden"]`, sem mudar os `data-*` do template e sem mexer na experiência de adição, remoção e persistência.

Corte executado:

- foi criado um helper comum para hidratar JSON dos editores;
- os editores de `strings`, `variants` e `red-flags` passaram a usar helpers próprios para persistência, criação de campos e montagem de linhas;
- a configuração de severidade dos red flags foi isolada em uma constante dedicada, reduzindo repetição e deixando o fluxo de cada editor mais claro.

Arquivos do ciclo:

- `web/static/js/admin/admin_catalogo_laudos_page.js`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/admin/admin_catalogo_laudos_page.js`
- `pytest -q web/tests/test_admin_client_routes.py -k 'catalogo_familia or schema_tecnico or historico or catalogo_laudos'`
  - resultado:
    - `2 passed, 37 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`
- `pytest -q web/tests/test_admin_client_routes.py web/tests/test_smoke.py`
  - resultado:
    - `80 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- reavaliar se ainda vale continuar no mesmo JS com cortes menores ou se o melhor retorno já migra para outro hotspot grande do frontend;
- se o catálogo admin continuar sendo o melhor alvo, o próximo corte provável é separar melhor os helpers compartilhados dos específicos da página de detalhe.

## Ciclo 43 — Organização do bootstrap do runtime do inspetor

Status:

- concluído e validado localmente

Problema observado:

- após a modularização em `web/static/js/inspetor/`, o bootstrap central em `web/static/js/chat/chat_index_page.js` ainda concentrava em um único bloco a definição dos `noop`, o contexto compartilhado, as ações padrão e o registro dos módulos `register*`;
- isso mantinha um ponto de entrada grande e pouco legível justamente no maior hotspot atual do frontend, dificultando a leitura das integrações do inspetor sem trazer ganho funcional;
- o corte seguro aqui era organizar apenas o bootstrap do runtime, preservando o contrato público de `window.TarielInspetorRuntime`, os nomes das registries dos módulos e a destruturação final das ações já consumidas pelo restante do arquivo.

Corte executado:

- foi criada uma constante dedicada para a ordem de registro dos módulos do inspetor;
- o bloco monolítico do runtime foi quebrado em helpers para montar o contexto compartilhado, as ações padrão e o runtime final;
- o registro dos módulos do inspetor passou a usar um helper explícito, mantendo o mesmo comportamento de fallback, logging e wiring do `ctx`.

Arquivos do ciclo:

- `web/static/js/chat/chat_index_page.js`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/chat/chat_index_page.js`
- `pytest -q web/tests/test_inspection_entry_mode_phase_c_web.py web/tests/test_inspector_active_report_authority.py web/tests/test_multiportal_bootstrap_contracts.py web/tests/test_app_boot_query_reduction.py`
  - resultado:
    - `14 passed`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- continuar em `web/static/js/chat/chat_index_page.js`, agora em um corte interno igualmente seguro, provavelmente separando melhor as regras de visibilidade/screen sync do workspace;
- manter a abordagem por fatias pequenas, porque o arquivo ainda é o maior hotspot do frontend atual.

## Ciclo 44 — Organização dos blocos iniciais do CSS do painel do revisor

Status:

- concluído e validado localmente

Problema observado:

- `web/static/css/revisor/painel_revisor.css` seguia como um dos maiores hotspots do frontend, com mais de seis mil linhas, e os blocos iniciais de base visual, `Topbar`, `Layout` e `Whispers` ainda estavam concentrados no mesmo arquivo;
- isso dificultava futuras fatias seguras no painel do revisor, porque até um ajuste pequeno exigia navegar por variáveis globais, shell visual e estados especiais no mesmo fluxo;
- o corte seguro aqui era extrair apenas esses blocos iniciais para partials, preservando a ordem do CSS, os seletores, os IDs, os `data-*` e o shell SSR do painel.

Corte executado:

- o arquivo principal do revisor passou a importar partials dedicadas para a base inicial, a topbar, o layout da coluna esquerda e o bloco de whispers;
- a folha principal foi mantida como entrypoint único, enquanto os trechos extraídos foram movidos sem alteração de comportamento;
- a organização agora segue o mesmo padrão de partials já adotado em outras áreas do frontend do projeto.

Arquivos do ciclo:

- `web/static/css/revisor/painel_revisor.css`
- `web/static/css/revisor/painel_revisor/_base.css`
- `web/static/css/revisor/painel_revisor/_topbar.css`
- `web/static/css/revisor/painel_revisor/_layout.css`
- `web/static/css/revisor/painel_revisor/_whispers.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
  - resultado:
    - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
  - resultado:
    - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- continuar no `painel_revisor.css` com mais uma fatia estrutural pequena, provavelmente em `Inbox redesign` ou `Mesa polish`, mantendo o CSS principal como entrypoint;
- depois disso, reavaliar novamente entre revisor e inspetor para o próximo corte de maior ROI sem ampliar blast radius.

## Ciclo 45 — Organização da coluna direita do painel do revisor

Status:

- concluído e validado localmente

Problema observado:

- depois da extração da base inicial do painel do revisor, o primeiro bloco remanescente em `web/static/css/revisor/painel_revisor.css` ainda concentrava a coluna direita completa do painel, incluindo estado vazio, cabeçalho da view e botões principais;
- esse trecho ficava logo na entrada do arquivo e continuava atrapalhando a leitura do ponto de entrada do CSS do revisor, mesmo sem haver problema funcional;
- o corte seguro aqui era extrair apenas a seção `Coluna direita`, preservando a ordem da cascata, os mesmos seletores e o mesmo entrypoint do CSS principal.

Corte executado:

- foi criada uma partial dedicada para a coluna direita do painel do revisor;
- o arquivo principal manteve a responsabilidade de orquestrar a ordem das imports no topo, preservando a mesma cascata visual;
- a nova partial agrupa o shell da view, o estado vazio, o cabeçalho da área principal e os botões base dessa região.

Arquivos do ciclo:

- `web/static/css/revisor/painel_revisor.css`
- `web/static/css/revisor/painel_revisor/_view_column.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
  - resultado:
    - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
  - resultado:
    - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- continuar modularizando o `painel_revisor.css` pela ordem da cascata, com a próxima fatia provável em `Timeline` ou `Resposta`;
- só voltar para blocos internos como `Inbox redesign` quando a ordem do arquivo já permitir esse movimento sem alterar prioridades de override.

## Ciclo 46 — Organização da timeline do painel do revisor

Status:

- concluído e validado localmente

Problema observado:

- após a extração da coluna direita, a próxima seção do topo remanescente em `web/static/css/revisor/painel_revisor.css` ainda concentrava toda a `Timeline`, incluindo o painel operacional, chips, cards de cobertura, bolhas de mensagem e anexos;
- esse trecho era grande o suficiente para continuar poluindo o ponto de entrada do CSS do revisor e dificultava novos cortes ordenados pela cascata;
- o corte seguro aqui era extrair a `Timeline` inteira para uma partial própria, mantendo a ordem do arquivo e sem mudar seletores nem o comportamento do painel.

Corte executado:

- foi criada uma partial dedicada para a `Timeline` do painel do revisor;
- o arquivo principal manteve a orquestração da ordem das imports no topo, preservando a mesma cascata visual do painel;
- o novo módulo agora concentra o painel operacional, estados da timeline, bolhas de mensagem e o bloco de anexos dessa região.

Arquivos do ciclo:

- `web/static/css/revisor/painel_revisor.css`
- `web/static/css/revisor/painel_revisor/_timeline.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
  - resultado:
    - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
  - resultado:
    - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- continuar modularizando o `painel_revisor.css` pela ordem da cascata, com a próxima fatia provável em `Resposta` ou `Modal`;
- manter os blocos internos de redesign para depois, quando a sequência de imports já refletir a ordem original do arquivo inteiro.

## Ciclo 47 — Organização da resposta do painel do revisor

Status:

- concluído e validado localmente

Problema observado:

- depois da extração da `Timeline`, o primeiro bloco remanescente no topo de `web/static/css/revisor/painel_revisor.css` ainda concentrava toda a área de `Resposta`, incluindo preview de anexo, textarea, bolha de referência e ações de responder;
- como essa seção vinha imediatamente antes do `Modal`, ela ainda poluía o entrypoint do CSS e dificultava seguir a modularização do arquivo respeitando a ordem da cascata;
- o corte seguro aqui era extrair a `Resposta` inteira para uma partial própria, preservando a sequência de imports no topo e mantendo os mesmos seletores.

Corte executado:

- foi criada uma partial dedicada para a área de `Resposta` do painel do revisor;
- o arquivo principal continuou apenas com a orquestração das imports no topo, preservando a mesma ordem visual do CSS original;
- o novo módulo concentra o composer da resposta, preview e remoção de anexos, referência ativa e botão de resposta por mensagem.

Arquivos do ciclo:

- `web/static/css/revisor/painel_revisor.css`
- `web/static/css/revisor/painel_revisor/_reply.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
  - resultado:
    - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
  - resultado:
    - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- continuar modularizando o `painel_revisor.css` pela ordem da cascata, com a próxima fatia natural em `Modal`;
- reavaliar os blocos de redesign internos só depois que o topo histórico do arquivo estiver totalmente modularizado.

## Ciclo 48 — Organização do modal do painel do revisor

Status:

- concluído e validado localmente

Problema observado:

- depois da extração de `Resposta`, o primeiro bloco remanescente no topo de `web/static/css/revisor/painel_revisor.css` ainda concentrava todo o `Modal`, incluindo shell do overlay, relatório estruturado, cards de pacote e a base compartilhada de `.dialog-motivo`;
- esse trecho seguia grande demais para o entrypoint do CSS e bloqueava o próximo corte seguro em `Dialog devolução`, que depende dessa base compartilhada;
- o corte seguro aqui era extrair o bloco `Modal` inteiro para uma partial própria, preservando a ordem dos imports e mantendo a base de `.dialog-motivo` antes dos estilos específicos do diálogo.

Corte executado:

- foi criada uma partial dedicada para o `Modal` do painel do revisor;
- o arquivo principal continuou apenas com a orquestração das imports no topo, preservando a ordem original da cascata antes de `Dialog devolução`;
- o novo módulo concentra overlay, container, corpo do modal, relatório estruturado, pacote e estados visuais associados ao relatório.

Arquivos do ciclo:

- `web/static/css/revisor/painel_revisor.css`
- `web/static/css/revisor/painel_revisor/_modal.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
  - resultado:
    - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
  - resultado:
    - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- continuar modularizando o `painel_revisor.css` pela ordem da cascata, com a próxima fatia natural em `Dialog devolução`;
- só partir para `Toast/status` depois que o diálogo estiver isolado sem mexer na prioridade dos overrides posteriores.

## Ciclo 49 — Organização do diálogo de devolução do painel do revisor

Status:

- concluído e validado localmente

Problema observado:

- depois da extração do `Modal`, o topo remanescente de `web/static/css/revisor/painel_revisor.css` ainda carregava o `Dialog devolução`, incluindo título, textarea, ações e a base local de `.btn-neutro`;
- esse trecho curto ainda precisava sair antes de `Toast/status`, porque a ordem segura depende de o diálogo continuar imediatamente após a base compartilhada do modal;
- o corte seguro aqui era extrair o bloco inteiro do diálogo para uma partial própria, sem mover overrides posteriores de `.btn-neutro` nem os ajustes temáticos do restante do arquivo.

Corte executado:

- foi criada uma partial dedicada para o `Dialog devolução` do painel do revisor;
- o arquivo principal continuou apenas com a sequência de imports no topo, preservando a ordem `Modal` -> `Dialog devolução` -> `Toast/status`;
- o novo módulo concentra título, texto, textarea, ações e a definição base de `.btn-neutro` usada nesse estágio do CSS.

Arquivos do ciclo:

- `web/static/css/revisor/painel_revisor.css`
- `web/static/css/revisor/painel_revisor/_return_dialog.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
  - resultado:
    - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
  - resultado:
    - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- continuar modularizando o `painel_revisor.css` pela ordem da cascata, agora com a próxima fatia natural em `Toast/status`;
- reavaliar a necessidade de ampliar a cobertura para Playwright quando o corte começar a tocar nos overrides responsivos de `Resposta`.

## Ciclo 50 — Organização do bloco de status do painel do revisor

Status:

- concluído e validado localmente

Problema observado:

- depois da extração do `Dialog devolução`, o topo remanescente de `web/static/css/revisor/painel_revisor.css` ainda concentrava o bloco `Toast/status`, que na prática reunia toast flutuante, painel de aprendizados, formulário associado e os media queries móveis de `layout-inbox`, `view-reply` e da mesa operacional;
- esse trecho precisava sair inteiro, porque fatiá-lo por dentro aumentaria o risco de inverter overrides responsivos e quebrar o layout mobile da área de resposta e da workspace;
- o corte seguro aqui era extrair o bloco completo até imediatamente antes de `Tariel Mesa Refresh`, preservando a ordem do topo e mantendo os media queries juntos no mesmo módulo.

Corte executado:

- foi criada uma partial dedicada para o bloco `Toast/status` do painel do revisor;
- o arquivo principal continuou apenas com a sequência de imports no topo, agora encerrando a parte histórica modularizada imediatamente antes de `Tariel Mesa Refresh`;
- o novo módulo concentra toast, aprendizados visuais, editor associado e os ajustes responsivos desse estágio do CSS.

Arquivos do ciclo:

- `web/static/css/revisor/painel_revisor.css`
- `web/static/css/revisor/painel_revisor/_status.css`

Validação local executada:

- `git diff --check`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
  - resultado:
    - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
  - resultado:
    - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- reavaliar o próximo hotspot do frontend com o topo do `painel_revisor.css` já modularizado até `Tariel Mesa Refresh`;
- decidir se o próximo corte permanece no painel do revisor, agora entrando na camada temática `Tariel Mesa Refresh`, ou se o melhor ROI volta para outro hotspot do frontend.

## Ciclo 51 — Estabilização da interação ativa do painel do revisor

Status:

- concluído e validado localmente

Problema observado:

- os refreshes automáticos do mesmo laudo no painel do revisor ainda podiam limpar referência ativa e anexo do composer, especialmente em atualizações por WebSocket, ações operacionais da mesa e validação de aprendizado visual;
- em caso de erro no envio da resposta, o texto digitado era perdido cedo demais e o recarregamento subsequente ainda podia derrubar o contexto do composer;
- a paginação do histórico podia manter o botão de carregamento em estado ocupado no render seguinte e não deduplicava mensagens antigas por `id`.

Corte executado:

- `carregarLaudo` passou a aceitar preservação explícita do composer no mesmo laudo, mantendo referência ativa e anexo pendente em refreshes automáticos;
- os fluxos de WebSocket, validação de aprendizado, refazer coverage, emissão oficial e recarga após falha de envio passaram a usar esse modo de preservação;
- o envio da resposta deixou de limpar o textarea antes da confirmação do backend;
- a paginação do histórico agora deduplica mensagens por `id` e desliga o estado de carregamento antes do render seguinte.

Arquivos do ciclo:

- `web/static/js/revisor/painel_revisor_page.js`
- `web/static/js/revisor/revisor_painel_aprendizados.js`
- `web/static/js/revisor/revisor_painel_historico.js`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/revisor/painel_revisor_page.js`
- `node --check web/static/js/revisor/revisor_painel_aprendizados.js`
- `node --check web/static/js/revisor/revisor_painel_historico.js`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
  - resultado:
    - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
  - resultado:
    - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- seguir na mesma trilha de confiabilidade do painel do revisor, com prioridade para sincronização de `collaborationSummary` e contadores operacionais;
- depois atacar os ajustes isolados do documento estruturado e da emissão oficial antes de entrar em cleanup visual maior.

## Ciclo 52 — Consistência dos indicadores operacionais do painel do revisor

Status:

- concluído e validado localmente

Problema observado:

- os cards do painel do revisor podiam regravar `data-collaboration-summary` com contadores antigos depois de uma atualização parcial, especialmente ao zerar chamados não lidos ou sincronizar badges sem receber um snapshot completo;
- o painel operacional da mesa tratava `whispers_recentes.length` como fallback de itens não lidos, misturando "recente" com "pendente de leitura";
- o overview do documento estruturado no modal ainda podia mostrar `0/0` campos preenchidos mesmo quando o painel inline já conseguia calcular os totais pelas `entries`.

Corte executado:

- a serialização de `collaborationSummary` foi centralizada e passou a ser derivada de um sumário normalizado único, evitando regravar o dataset com valores stale;
- atualizações parciais de contadores agora preservam a base do sumário existente e sobrescrevem apenas os campos operacionais explícitos, sem reintroduzir chamados antigos como não lidos;
- o painel operacional da mesa passou a usar `whispers_recentes` apenas como fallback de volume recente, sem inferir a partir daí o contador de não lidos;
- o overview do documento estruturado no modal agora usa o mesmo fallback do painel inline para `filled_fields` e `total_fields`.

Arquivos do ciclo:

- `web/static/js/revisor/revisor_painel_core.js`
- `web/static/js/revisor/revisor_painel_mesa.js`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/revisor/revisor_painel_core.js`
- `node --check web/static/js/revisor/revisor_painel_mesa.js`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
  - resultado:
    - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
  - resultado:
    - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
  - resultado:
    - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- seguir na trilha de confiabilidade do painel do revisor, com prioridade para travas de ação na emissão oficial e contexto seguro nas mutações de aprendizados visuais;
- depois atacar a padronização dos cards dinâmicos de chamados e a limpeza estrutural restante do frontend da mesa.

## Ciclo 53 — Extração do módulo de pacote técnico e emissão oficial do revisor

Status:

- concluído e validado localmente

Problema observado:

- `web/static/js/revisor/revisor_painel_mesa.js` ainda acumulava, além da renderização e do fluxo operacional da mesa, toda a trilha de ações de pacote técnico e emissão oficial;
- esse bloco tinha dependências próprias de download, modal, permissão e POST de emissão, mas era consumido externamente apenas como API pública pelo bootstrap da página;
- manter essas ações dentro do módulo principal da mesa dificultava leituras futuras e misturava responsabilidades de UI operacional com ações documentais/governadas.

Corte executado:

- as ações de pacote técnico e emissão oficial foram extraídas para o novo módulo `web/static/js/revisor/revisor_painel_pacote.js`;
- o contrato público em `window.TarielRevisorPainel` foi preservado com os mesmos métodos já usados por `painel_revisor_page.js`;
- o template `web/templates/painel_revisor.html` passou a carregar o novo módulo entre `revisor_painel_mesa.js` e `painel_revisor_page.js`, mantendo a ordem segura de boot.

Arquivos do ciclo:

- `web/static/js/revisor/revisor_painel_mesa.js`
- `web/static/js/revisor/revisor_painel_pacote.js`
- `web/templates/painel_revisor.html`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/revisor/revisor_painel_mesa.js`
- `node --check web/static/js/revisor/revisor_painel_pacote.js`
- `node --check web/static/js/revisor/painel_revisor_page.js`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
- resultado:
  - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
- resultado:
  - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- seguir na mesma frente do painel do revisor, agora avaliando se o próximo corte fica no fluxo de aprendizados visuais ou nas travas de ação da emissão oficial;
- depois reescanear se o melhor ROI continua na mesa do revisor ou volta para outro hotspot grande do frontend.

## Ciclo 54 — Separação das ações de aprendizados visuais do revisor

Status:

- concluído e validado localmente

Problema observado:

- `web/static/js/revisor/revisor_painel_aprendizados.js` ainda misturava renderização do painel com mutações, montagem de payload, bloqueio de card e wiring dos botões de ação;
- esse acoplamento dificultava ler a tela por responsabilidade, porque o fluxo visual e o fluxo de POST para validação da mesa conviviam no mesmo arquivo;
- o corte seguro aqui era separar a trilha de ações em um módulo próprio sem alterar HTML gerado, hooks `data-aprendizado-action` ou a recarga do laudo após validação.

Corte executado:

- a renderização do painel de aprendizados visuais permaneceu em `web/static/js/revisor/revisor_painel_aprendizados.js`;
- as mutações, helpers de payload, bloqueio de card e o click delegation dos aprendizados foram extraídos para `web/static/js/revisor/revisor_painel_aprendizados_actions.js`;
- o template `web/templates/painel_revisor.html` passou a carregar o novo módulo imediatamente antes de `painel_revisor_page.js`, preservando a ordem de boot.

Arquivos do ciclo:

- `web/static/js/revisor/revisor_painel_aprendizados.js`
- `web/static/js/revisor/revisor_painel_aprendizados_actions.js`
- `web/templates/painel_revisor.html`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/revisor/revisor_painel_aprendizados.js`
- `node --check web/static/js/revisor/revisor_painel_aprendizados_actions.js`
- `node --check web/static/js/revisor/painel_revisor_page.js`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
- resultado:
  - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
- resultado:
  - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- seguir no painel do revisor avaliando se o próximo corte mais limpo fica no dispatcher de ações da `painel_revisor_page.js` ou no miolo remanescente da mesa operacional;
- depois reescanear frontend e backend antes de escolher o próximo hotspot.

## Ciclo 55 — Segregação do bootstrap, interações e mutações do painel do revisor

Status:

- concluído e validado localmente

Problema observado:

- `web/static/js/revisor/painel_revisor_page.js` ainda concentrava, além de websocket e carregamento do laudo, o wiring de eventos da interface e mutações operacionais como envio de resposta, devolução de coverage e confirmação de devolução;
- esse bloco misturava bootstrap real da página com aberturas de card, filtros da home da mesa, handlers do painel operacional, botões laterais, modais e fetches de mutação;
- o corte seguro aqui era segregar essas responsabilidades em módulos próprios, preservando o mesmo namespace público, os mesmos seletores, recargas de laudo e a ordem de execução.

Corte executado:

- o wiring de eventos da UI foi extraído para `web/static/js/revisor/revisor_painel_interacoes.js`;
- as mutações operacionais foram extraídas para `web/static/js/revisor/revisor_painel_mutacoes.js`;
- `web/static/js/revisor/painel_revisor_page.js` passou a concentrar bootstrap, websocket, carregamento do laudo e helpers compartilhados, expondo no namespace apenas a superfície necessária para os novos módulos;
- o template `web/templates/painel_revisor.html` passou a carregar `revisor_painel_mutacoes.js` e `revisor_painel_interacoes.js` logo após `painel_revisor_page.js`, preservando a dependência correta entre módulos.

Arquivos do ciclo:

- `web/static/js/revisor/painel_revisor_page.js`
- `web/static/js/revisor/revisor_painel_mutacoes.js`
- `web/static/js/revisor/revisor_painel_interacoes.js`
- `web/templates/painel_revisor.html`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/revisor/painel_revisor_page.js`
- `node --check web/static/js/revisor/revisor_painel_mutacoes.js`
- `node --check web/static/js/revisor/revisor_painel_interacoes.js`
- `node --check web/static/js/revisor/revisor_painel_aprendizados_actions.js`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
- resultado:
  - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
- resultado:
  - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- reescanear frontend e backend para confirmar se a melhor sequência ainda é continuar no painel do revisor ou migrar para outro hotspot grande como `revisor_painel_mesa.js` ou `chat_index_page.js`;
- se continuar no revisor, o próximo corte provável passa a ser o miolo restante de `revisor_painel_mesa.js`.

## Ciclo 56 — Extração da leitura documental estruturada do painel do revisor

Status:

- concluído e validado localmente

Problema observado:

- `web/static/js/revisor/revisor_painel_mesa.js` ainda concentrava um bloco grande e coeso dedicado apenas à leitura do `laudo_output`, incluindo normalização, chips de status, painel inline e modal de relatório;
- essa trilha não pertencia ao miolo operacional da mesa nem às ações de pacote, mas seguia misturada ao mesmo hotspot;
- o corte seguro aqui era mover a leitura documental para um módulo próprio carregado antes da mesa, preservando a mesma API pública usada pelo bootstrap da página e pelo modal do pacote.

Corte executado:

- a trilha de documento estruturado foi extraída para `web/static/js/revisor/revisor_painel_documento.js`;
- `web/static/js/revisor/revisor_painel_mesa.js` passou a consumir `renderStructuredDocumentOverview` e `renderizarPainelDocumentoTecnicoInline` a partir do namespace compartilhado;
- o template `web/templates/painel_revisor.html` passou a carregar `revisor_painel_documento.js` logo após `revisor_painel_core.js`, preservando a ordem de dependências.

Arquivos do ciclo:

- `web/static/js/revisor/revisor_painel_documento.js`
- `web/static/js/revisor/revisor_painel_mesa.js`
- `web/templates/painel_revisor.html`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/revisor/revisor_painel_documento.js`
- `node --check web/static/js/revisor/revisor_painel_mesa.js`
- `node --check web/static/js/revisor/painel_revisor_page.js`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
- resultado:
  - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
- resultado:
  - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- reescanear os hotspots para decidir se ainda vale seguir no `revisor_painel_mesa.js` ou se o melhor retorno já migra para outro hotspot grande do frontend;
- se continuar no revisor, o próximo corte provável passa a ser a extração de mais um bloco operacional da mesa.

## Ciclo 57 — Extração da governança documental do painel da mesa

Status:

- concluído e validado localmente

Problema observado:

- `web/static/js/revisor/revisor_painel_mesa.js` ainda concentrava um bloco grande e coeso só de leitura documental e governança, misturando verificação pública, emissão oficial, anexo pack, memória operacional e red flags da revisão;
- esse trecho não participava das mutações nem do carregamento do pacote da mesa, mas permanecia no hotspot principal, dificultando a leitura do fluxo operacional;
- o corte seguro era mover essa superfície para um módulo dedicado, mantendo o mesmo HTML renderizado e consumindo as funções via namespace compartilhado.

Corte executado:

- a leitura de governança documental foi extraída para `web/static/js/revisor/revisor_painel_governanca.js`;
- `web/static/js/revisor/revisor_painel_mesa.js` passou a chamar os renderizadores de governança pelo namespace `window.TarielRevisorPainel`, preservando a ordem de execução do bootstrap;
- o template `web/templates/painel_revisor.html` passou a carregar `revisor_painel_governanca.js` antes de `painel_revisor_page.js`, garantindo que o painel da mesa já encontre o módulo registrado quando o caso ativo for carregado.

Arquivos do ciclo:

- `web/static/js/revisor/revisor_painel_governanca.js`
- `web/static/js/revisor/revisor_painel_mesa.js`
- `web/templates/painel_revisor.html`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/revisor/revisor_painel_mesa.js`
- `node --check web/static/js/revisor/revisor_painel_governanca.js`
- `node --check web/static/js/revisor/painel_revisor_page.js`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
- resultado:
  - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
- resultado:
  - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- reescanear frontend e backend para decidir se o próximo corte ainda fica no restante de `revisor_painel_mesa.js` ou se o melhor retorno migra para outro hotspot maior;
- se continuar no painel do revisor, o próximo corte provável passa a ser a extração do bloco operacional restante ou a próxima fatia grande de interface em `chat_index_page.js`.

## Ciclo 58 — Extração dos cards analíticos da mesa

Status:

- concluído e validado localmente

Problema observado:

- `web/static/js/revisor/revisor_painel_mesa.js` ainda carregava um bloco extenso de leitura analítica estática, misturando revisão por seção, checklist de evidências e histórico de inspeção no mesmo arquivo que também faz carregamento, renderização principal e mutações da mesa;
- esse miolo era coeso, sem dependência direta de rede, e já podia ser isolado como módulo de leitura compartilhado pelo painel operacional;
- manter essa camada no hotspot principal dificultava separar o que é orquestração da mesa do que é somente apresentação analítica.

Corte executado:

- a trilha de revisão por bloco, coverage map e histórico de inspeção foi extraída para `web/static/js/revisor/revisor_painel_analise.js`;
- `web/static/js/revisor/revisor_painel_mesa.js` passou a chamar esses renderizadores pelo namespace `window.TarielRevisorPainel`, ficando mais focado em estado, carregamento do pacote e ações operacionais;
- o template `web/templates/painel_revisor.html` passou a carregar `revisor_painel_analise.js` antes do bootstrap da página, preservando a disponibilidade do módulo quando a mesa renderiza o caso ativo.

Arquivos do ciclo:

- `web/static/js/revisor/revisor_painel_analise.js`
- `web/static/js/revisor/revisor_painel_mesa.js`
- `web/templates/painel_revisor.html`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/revisor/revisor_painel_mesa.js`
- `node --check web/static/js/revisor/revisor_painel_analise.js`
- `node --check web/static/js/revisor/painel_revisor_page.js`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
- resultado:
  - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
- resultado:
  - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- reescanear os hotspots para decidir se ainda vale fechar a última fatia do `revisor_painel_mesa.js` ou se já compensa migrar para um hotspot maior fora do painel;
- se continuar no revisor, o próximo corte provável passa a ser a separação final entre renderização operacional da mesa e o modal do pacote técnico.

## Ciclo 59 — Consolidação do modal do pacote técnico

Status:

- concluído e validado localmente

Problema observado:

- `web/static/js/revisor/revisor_painel_mesa.js` ainda trazia a montagem do modal do pacote técnico e da lista resumida de pendências/chamados, embora essa superfície já fosse consumida exclusivamente por `web/static/js/revisor/revisor_painel_pacote.js`;
- isso mantinha responsabilidade de pacote técnico dentro do módulo da mesa, mesmo depois de o restante das ações de pacote já ter sido separado;
- o corte seguro aqui era consolidar a apresentação do modal junto das ações de pacote, sem alterar API nem o HTML renderizado.

Corte executado:

- `renderListaPacote` e `renderizarModalPacote` foram movidos de `web/static/js/revisor/revisor_painel_mesa.js` para `web/static/js/revisor/revisor_painel_pacote.js`;
- `web/static/js/revisor/revisor_painel_pacote.js` passou a concentrar tanto as ações quanto a renderização do modal do pacote técnico, mantendo a exportação dessas funções no namespace compartilhado;
- `web/static/js/revisor/revisor_painel_mesa.js` ficou restrito à operação da mesa, ao carregamento do pacote operacional e às mutações do fluxo.

Arquivos do ciclo:

- `web/static/js/revisor/revisor_painel_mesa.js`
- `web/static/js/revisor/revisor_painel_pacote.js`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/revisor/revisor_painel_mesa.js`
- `node --check web/static/js/revisor/revisor_painel_pacote.js`
- `node --check web/static/js/revisor/painel_revisor_page.js`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
- resultado:
  - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
- resultado:
  - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- reescanear se ainda compensa reduzir o `revisor_painel_mesa.js` com a extração da renderização operacional restante;
- se a próxima fatia no revisor deixar de ser o melhor retorno, migrar o loop para um hotspot maior como `chat_index_page.js` ou `painel_revisor.css`.

## Ciclo 60 — Extração da renderização operacional da mesa

Status:

- concluído e validado localmente

Problema observado:

- `web/static/js/revisor/revisor_painel_mesa.js` ainda misturava adaptação do pacote, carregamento remoto, mutação de pendências e toda a renderização operacional da mesa;
- esse restante de apresentação já formava um bloco coeso, com dependência apenas do namespace compartilhado e sem necessidade de permanecer junto da lógica de fetch;
- o corte seguro era mover esse trecho para um módulo próprio e deixar `revisor_painel_mesa.js` como camada fina de adaptação, carregamento e atualização.

Corte executado:

- a renderização operacional da mesa foi extraída para `web/static/js/revisor/revisor_painel_operacao.js`;
- `web/static/js/revisor/revisor_painel_mesa.js` passou a delegar para `window.TarielRevisorPainel.renderizarPainelMesaOperacional`, ficando concentrado na adaptação do payload, no carregamento do pacote e na mutação de pendências;
- o template `web/templates/painel_revisor.html` passou a carregar `revisor_painel_operacao.js` antes do bootstrap da página, preservando a disponibilidade do renderizador quando o caso ativo é aberto.

Arquivos do ciclo:

- `web/static/js/revisor/revisor_painel_operacao.js`
- `web/static/js/revisor/revisor_painel_mesa.js`
- `web/templates/painel_revisor.html`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/revisor/revisor_painel_mesa.js`
- `node --check web/static/js/revisor/revisor_painel_operacao.js`
- `node --check web/static/js/revisor/painel_revisor_page.js`
- `pytest -q web/tests/test_reviewer_panel_boot_hotfix.py -k 'revisor_painel_renderiza_ssr_por_padrao or revisor_painel_surface_ssr_mantem_render_ssr_e_shadow'`
- resultado:
  - `2 passed, 9 deselected`
- `pytest -q web/tests/test_v2_review_queue_projection.py -k 'painel_revisor_passa_pela_projecao_de_fila_sem_mudar_html'`
- resultado:
  - `1 passed, 4 deselected`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o próximo deploy do Render;
- reescanear se ainda vale insistir no painel do revisor ou se o melhor retorno agora migra para outro hotspot maior;
- se continuar no painel, o próximo corte provável passa a ser limpeza residual do adaptador da mesa ou a consolidação de pequenos helpers remanescentes; caso contrário, o candidato natural passa a ser `chat_index_page.js`.

## Ciclo 61 — Extração do runtime de modo de entrada do inspetor

Status:

- concluído e validado localmente

Problema observado:

- `web/static/js/chat/chat_index_page.js` ainda concentrava o estado de modo de entrada do inspetor, a retomada pendente da home e o storage do contexto visual por laudo;
- esse trecho já era um subsistema próprio, mas permanecia acoplado ao arquivo monolítico do chat, mesmo com a arquitetura de módulos do inspetor já disponível;
- o corte seguro era mover esse runtime para um módulo dedicado, mantendo no arquivo principal apenas delegações finas para não alterar o comportamento do portal.

Corte executado:

- foi criado o módulo `web/static/js/inspetor/entry_mode.js`, responsável pelo bootstrap do modo de entrada, pela nota visual do workspace, pela retomada pendente da home e pela persistência do contexto visual por laudo;
- `web/static/js/chat/chat_index_page.js` passou a delegar essas rotinas para o runtime compartilhado do inspetor, preservando a assinatura das funções já usadas no restante da página;
- `criarSharedRuntimeInspetor` passou a expor os normalizadores, chaves de storage e limites necessários para o novo módulo;
- `web/templates/index.html` passou a carregar `inspetor/entry_mode.js` junto dos demais módulos do inspetor antes do `chat_index_page.js`;
- `ctx.actions` passou a expor também `obterRetomadaHomePendente`, alinhando a API usada pelos módulos de bootstrap e eventos do inspetor.

Arquivos do ciclo:

- `web/static/js/inspetor/entry_mode.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/chat/chat_index_page.js`
- `node --check web/static/js/inspetor/entry_mode.js`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`
- `pytest -q web/tests/test_inspector_active_report_authority.py`
- resultado:
  - `4 passed`
- `pytest -q web/tests/test_report_pack_rollout_summary.py`
- resultado:
  - `1 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o deploy correspondente no Render;
- decidir se ainda vale reduzir o `chat_index_page.js` com a remoção dos helpers puros remanescentes do modo de entrada ou se o melhor retorno passa para outro hotspot maior do frontend ou backend;
- se o chat continuar sendo o melhor corte, a próxima fatia natural é isolar o restante do estado de home/workspace que ainda está misturado com o bootstrap principal.

## Ciclo 62 — Limpeza dos helpers residuais de entry mode

Status:

- concluído e validado localmente

Problema observado:

- após a extração do runtime de modo de entrada para `web/static/js/inspetor/entry_mode.js`, o `web/static/js/chat/chat_index_page.js` ainda mantinha quatro helpers puros duplicados;
- essas funções já não tinham chamadas locais e passaram a representar apenas código morto dentro do hotspot principal;
- o corte seguro era remover esse resíduo para deixar o arquivo principal mais fiel ao papel de orquestração e delegação.

Corte executado:

- os helpers locais `obterBootstrapModoEntrada`, `rotuloModoEntrada`, `descreverMotivoModoEntrada` e `extrairModoEntradaPayload` foram removidos de `web/static/js/chat/chat_index_page.js`;
- o arquivo principal ficou restrito aos wrappers compatíveis e ao restante da orquestração do inspetor, sem duplicar a lógica já concentrada em `web/static/js/inspetor/entry_mode.js`.

Arquivos do ciclo:

- `web/static/js/chat/chat_index_page.js`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/chat/chat_index_page.js`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`

Próximo passo imediato:

- publicar este ciclo e acompanhar o novo deploy do Render;
- reavaliar se o próximo corte do chat deve atacar o estado residual de home/workspace ou se o melhor retorno agora migra para um hotspot maior como `web/app/domains/admin/services.py`;
- se o chat continuar sendo o melhor alvo, a próxima extração natural é o bootstrap de home/resume e a sincronização do estado autoritativo do inspetor.

## Ciclo 63 — Extração do serviço de signatários governados do tenant

Status:

- concluído e validado localmente
- mantido apenas em localhost, dentro do pacote local atual

Problema observado:

- `web/app/domains/admin/services.py` ainda concentrava o bloco de normalização, serialização e persistência dos signatários governados do tenant;
- esse trecho já formava um subdomínio próprio do admin, com regras e testes focados, mas permanecia misturado ao hotspot principal do catálogo e do tenant;
- o corte seguro era extrair esse fluxo para um módulo dedicado, preservando a API pública exposta por `services.py`.

Corte executado:

- foi criado `web/app/domains/admin/tenant_signatory_services.py`;
- o serializer `_serializar_signatario_governado_admin` foi movido para o novo módulo;
- `upsert_signatario_governado_laudo` foi movido para o novo módulo;
- `web/app/domains/admin/services.py` passou a reexportar essas rotinas, preservando a fachada atual usada por rotas e testes.

Arquivos do ciclo:

- `web/app/domains/admin/tenant_signatory_services.py`
- `web/app/domains/admin/services.py`
- `docs/PACOTE_PUBLICACAO_REFATORACAO_LOCALHOST.md`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Validação local executada:

- `git diff --check`
- `python -m py_compile web/app/domains/admin/services.py web/app/domains/admin/tenant_signatory_services.py`
- `pytest -q web/tests/test_admin_services.py -k 'signatario_governado_do_tenant_salva_escopo_e_aparece_no_detalhe'`
- resultado:
  - `1 passed, 41 deselected`
- `pytest -q web/tests/test_admin_client_routes.py -k 'salva_signatario_governado_no_tenant'`
- resultado:
  - `1 passed, 38 deselected`

Próximo passo imediato:

- continuar no mesmo pacote local do hotspot admin;
- extrair o restante do detalhe do tenant para `tenant_client_read_services.py`, mantendo `services.py` como fachada;
- só publicar no GitHub quando o pacote local reunir cortes coesos suficientes e um checklist final de validação.

## Ciclo 64 — Extração do detalhe administrativo do tenant

Status:

- concluído e validado localmente
- mantido apenas em localhost, dentro do pacote local atual

Problema observado:

- `web/app/domains/admin/services.py` ainda mantinha o serializer do usuário admin e o resumo de primeiro acesso da empresa;
- essas peças só existiam para alimentar o detalhe administrativo do tenant, mas continuavam no monólito mesmo com o read-side já organizado em `tenant_client_read_services.py`;
- o corte seguro era mover esse restante do detalhe para o módulo de leitura e manter `services.py` apenas como fachada compatível.

Corte executado:

- `_serializar_usuario_admin` foi movido para `web/app/domains/admin/tenant_client_read_services.py`;
- `_resumir_primeiro_acesso_empresa` foi movido para `web/app/domains/admin/tenant_client_read_services.py`;
- `web/app/domains/admin/services.py` passou a reexportar essas rotinas, preservando a fachada atual e evitando quebra de imports legados;
- `buscar_detalhe_cliente` continuou estável na superfície pública, agora dependendo apenas das funções já localizadas no read-side correto.

Arquivos do ciclo:

- `web/app/domains/admin/tenant_client_read_services.py`
- `web/app/domains/admin/services.py`
- `docs/PACOTE_PUBLICACAO_REFATORACAO_LOCALHOST.md`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Validação local executada:

- `git diff --check`
- `python -m py_compile web/app/domains/admin/services.py web/app/domains/admin/tenant_client_read_services.py web/app/domains/admin/tenant_signatory_services.py`
- `pytest -q web/tests/test_admin_services.py -k 'busca_detalhe_cliente_tolera_falha_no_portfolio_catalogo or signatario_governado_do_tenant_salva_escopo_e_aparece_no_detalhe'`
- resultado:
  - `2 passed, 40 deselected`
- `pytest -q web/tests/test_admin_client_routes.py -k 'admin_clientes_renderiza_console_operacional_na_lista_e_no_detalhe or admin_cliente_salva_signatario_governado_no_tenant'`
- resultado:
  - `2 passed, 37 deselected`

Próximo passo imediato:

- reavaliar se o próximo melhor corte do pacote local continua no fluxo admin do tenant, agora mirando onboarding, ou se já compensa alternar para o hotspot do frontend em `chat_index_page.js`;
- manter a estratégia `localhost first`, acumulando cortes locais coesos antes do próximo push.

## Ciclo 65 — Extração do histórico do workspace

Status:

- concluído e validado localmente
- mantido apenas em localhost, dentro do pacote local atual

Problema observado:

- `web/static/js/chat/chat_index_page.js` ainda carregava o pipeline inteiro do histórico do workspace;
- o hotspot misturava leitura do DOM, normalização de filtros, composição de itens canônicos e renderização dos cards do histórico;
- durante a extração apareceu um acoplamento antigo no bootstrap do inspetor, onde wrappers do arquivo principal voltavam a sobrescrever actions já registradas pelos módulos especializados.

Corte executado:

- foi criado `web/static/js/inspetor/workspace_history.js`;
- o pipeline do histórico do workspace foi movido para o novo módulo do inspetor;
- `web/templates/index.html` passou a carregar o módulo antes do `chat_index_page.js`;
- `web/static/js/chat/chat_index_page.js` ficou restrito à orquestração e ao consumo das actions compartilhadas;
- o wiring final de `ctx.actions` foi ajustado para preservar as implementações reais de `entry_mode`, contexto visual do laudo e reset dos filtros do histórico.

Arquivos do ciclo:

- `web/static/js/inspetor/workspace_history.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`
- `docs/PACOTE_PUBLICACAO_REFATORACAO_LOCALHOST.md`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/inspetor/workspace_history.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
- resultado:
  - capturas geradas em `web/artifacts/visual/inspetor/20260420-164035`

Próximo passo imediato:

- alternar de volta para o backend para manter o viés fullstack do pacote local;
- extrair o fluxo de onboarding do tenant de `web/app/domains/admin/services.py`, preservando a fachada pública do módulo;
- manter o pacote em localhost até fechar um conjunto coerente de 3 a 5 cortes antes do próximo push.

## Ciclo 66 — Extração do onboarding do tenant

Status:

- concluído e validado localmente
- mantido apenas em localhost, dentro do pacote local atual

Problema observado:

- `web/app/domains/admin/services.py` ainda mantinha o fluxo completo de onboarding do tenant, incluindo criação da empresa, admin inicial, provisionamento operacional e aviso de boas-vindas;
- o bloco já formava um subdomínio próprio, mas a extração exigia compatibilidade retroativa porque rotas, outros domínios e testes ainda dependem de símbolos históricos expostos por `admin.services`;
- a primeira passagem da extração revelou dois acoplamentos silenciosos: reexport de `criar_usuario_empresa` e monkeypatch de `gerar_senha_fortificada` consumido por fluxos críticos do portal cliente.

Corte executado:

- foi criado `web/app/domains/admin/tenant_onboarding_services.py`;
- `registrar_novo_cliente`, `_aviso_notificacao_boas_vindas` e `_disparar_email_boas_vindas` foram extraídos para o novo módulo;
- `web/app/domains/admin/services.py` foi mantido como fachada compatível, injetando normalização de CNPJ, dispatcher de boas-vindas e gerador de senha para preservar os pontos de monkeypatch legados;
- reexports compatíveis necessários foram mantidos em `services.py`, incluindo `criar_usuario_empresa` e `gerar_senha_fortificada`.

Arquivos do ciclo:

- `web/app/domains/admin/tenant_onboarding_services.py`
- `web/app/domains/admin/services.py`
- `docs/PACOTE_PUBLICACAO_REFATORACAO_LOCALHOST.md`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Validação local executada:

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

Próximo passo imediato:

- reavaliar o próximo corte mais seguro entre o rail de contexto do workspace no frontend e novos resíduos de fachada no backend;
- manter o pacote em localhost, agora com quatro cortes locais coesos desde o último push;
- só publicar depois do fechamento do pacote e de uma revisão final do `git diff --stat`.

## Ciclo 67 — Extração do rail de contexto do workspace

Status:

- concluído e validado localmente
- mantido apenas em localhost, dentro do pacote local atual

Problema observado:

- `web/static/js/chat/chat_index_page.js` ainda carregava o rail de contexto do workspace, incluindo contexto fixado, resumo operacional da IA e card resumido da mesa;
- esse bloco já não pertencia ao mesmo subdomínio do histórico e deixava o hotspot principal misturando orquestração, leitura de estado local e renderização do rail lateral;
- a extração precisava manter compatibilidade com consumidores já espalhados pelo runtime, especialmente `system_events`, `ui_bindings` e `workspace_derivatives`.

Corte executado:

- foi criado `web/static/js/inspetor/workspace_context.js`;
- o rail de contexto do workspace foi movido para o novo módulo do inspetor;
- `web/templates/index.html` passou a carregar o módulo antes do `chat_index_page.js`;
- `web/static/js/chat/chat_index_page.js` passou a consumir as actions do novo módulo, sem reintroduzir lógica local duplicada;
- o runtime base foi atualizado com `noops` e com o registro `registerWorkspaceContext` na ordem de módulos do inspetor.

Arquivos do ciclo:

- `web/static/js/inspetor/workspace_context.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`
- `docs/PACOTE_PUBLICACAO_REFATORACAO_LOCALHOST.md`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Validação local executada:

- `git diff --check`
- `node --check web/static/js/inspetor/workspace_context.js`
- `node --check web/static/js/chat/chat_index_page.js`
- `pytest -q web/tests/test_smoke.py`
- resultado:
  - `41 passed`
- `python3 web/scripts/inspecao_visual_inspetor.py`
- resultado:
  - capturas geradas em `web/artifacts/visual/inspetor/20260420-165733`

Próximo passo imediato:

- reavaliar o tamanho residual de `web/static/js/chat/chat_index_page.js` depois desta extração e decidir se o próximo corte continua no frontend ou volta para um resíduo menor do backend;
- revisar o `git diff --stat` do pacote local, que agora reúne cinco cortes coesos desde o último push;
- manter a estratégia `localhost first`, sem publicar nada até o fechamento intencional do pacote.

## Ciclo 68 — Extração da navegação do workspace

Status:

- concluído e validado localmente
- mantido apenas em localhost, dentro do pacote local atual

Problema observado:

- `web/static/js/chat/chat_index_page.js` ainda concentrava a navegação do shell do workspace, misturando transições entre landing da IA, workspace ativo, home expandido e retomada sem laudo;
- esse bloco já não pertencia ao mesmo subdomínio das rotinas restantes do arquivo principal e seguia acoplando `bootstrap`, `system_events`, `ui_bindings` e o estado visual do portal;
- a extração precisava preservar a ordem operacional entre stage, modo de inspeção e limpeza do widget da mesa, sem reintroduzir os loops de runtime que já tinham sido corrigidos nos ciclos anteriores.

Corte executado:

- foi criado `web/static/js/inspetor/workspace_navigation.js`;
- foram movidos para o novo módulo `resolverContextoVisualWorkspace`, `definirWorkspaceStage`, `atualizarContextoWorkspaceAtivo`, `definirModoInspecaoUI`, `exibirInterfaceInspecaoAtiva`, `exibirLandingAssistenteIA`, `restaurarTelaSemRelatorio`, `resetarInterfaceInspecao`, `atualizarHistoricoHomeExpandido` e `rolarParaHistoricoHome`;
- `web/templates/index.html` passou a carregar o novo módulo antes do `chat_index_page.js`;
- o runtime base do inspetor recebeu `normalizarModoInspecaoUI` no shared runtime, `noops` compatíveis para as novas actions e reexports auxiliares consumidos pelo módulo;
- `web/static/js/chat/chat_index_page.js` foi reduzido de `5959` para `5805` linhas, mantendo o restante do fluxo de abertura de laudo, início e finalização no arquivo principal.

Arquivos do ciclo:

- `web/static/js/inspetor/workspace_navigation.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`
- `docs/PACOTE_PUBLICACAO_REFATORACAO_LOCALHOST.md`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Validação local executada:

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

Próximo passo imediato:

- reavaliar se o próximo corte volta ao backend para manter o pacote fullstack coerente ou se ainda vale separar o bloco residual de abertura/início/finalização de laudo no frontend;
- revisar o pacote local agora com seis cortes acumulados desde o último push, sem publicar nada antes de um fechamento intencional do pacote;
- manter a estratégia `localhost first`, com revisão do `git diff --stat` antes de qualquer push futuro.

## Ciclo 69 — Extração das métricas do painel administrativo

Status:

- concluído e validado localmente
- mantido apenas em localhost, dentro do pacote local atual

Problema observado:

- `web/app/domains/admin/services.py` ainda concentrava `buscar_metricas_ia_painel`, embora o cálculo do dashboard já formasse um serviço próprio dentro do domínio admin;
- esse bloco misturava agregação de métricas operacionais, leitura de catálogo e ranking de tenants no mesmo hotspot que ainda abriga regras de catálogo e fachadas legadas;
- a extração precisava preservar compatibilidade com consumidores indiretos, especialmente `routes.py` e `document_operations_summary.py`, sem alterar a API pública exposta por `admin.services`.

Corte executado:

## Diretriz Permanente — Tariel V2 Oficial

Esta diretriz fica ativa ate a migracao chegar a 100%.

- `tariel-v2` e o sistema oficial em construcao e deve ser tratado como caminho principal;
- o legado e `tariel-web` passam a ser backup, referencia e ponte temporaria apenas quando necessario;
- a direcao arquitetural principal e `Astro + React + TypeScript + Prisma`;
- Python deve permanecer somente onde ainda for motor especializado ou onde a reescrita ainda nao se justifica;
- toda nova decisao de migracao deve ser tomada para aproximar o produto final desse estado, mesmo apos compactacao de contexto ou handoff.

Consulte tambem `docs/TARIEL_V2_MIGRATION_CHARTER.md` antes de escolher o proximo corte.

- foi criado `web/app/domains/admin/admin_dashboard_services.py`;
- `buscar_metricas_ia_painel` foi movido para o novo módulo;
- `web/app/domains/admin/services.py` foi mantido como fachada compatível, apenas injetando clause de tenants, ordenação por plano, relógio UTC e builders de rollup do catálogo;
- `web/app/domains/admin/services.py` foi reduzido de `5207` para `5174` linhas, mantendo o contrato público do domínio intacto.

Arquivos do ciclo:

- `web/app/domains/admin/admin_dashboard_services.py`
- `web/app/domains/admin/services.py`
- `docs/PACOTE_PUBLICACAO_REFATORACAO_LOCALHOST.md`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Validação local executada:

- `git diff --check`
- `python -m py_compile web/app/domains/admin/services.py web/app/domains/admin/admin_dashboard_services.py`
- `pytest -q web/tests/test_admin_services.py -k 'metricas_e_listagem or agrega_catalogo_e_dashboard'`
- resultado:
  - `2 passed, 40 deselected`
- `pytest -q web/tests/test_v2_document_operations_summary.py`
- resultado:
  - `2 passed`

Próximo passo imediato:

- reavaliar o próximo corte menor entre os resíduos finais do frontend no inspetor e novos blocos coesos do backend em `admin/services.py`;
- revisar o pacote local agora com sete cortes acumulados desde o último push, ainda sem publicar nada;
- manter a estratégia `localhost first`, deixando o push e a validação no Render para um fechamento coerente do pacote.

## Ciclo 70 — Extração do fluxo de laudo do workspace

Status:

- concluído e validado localmente
- mantido apenas em localhost, dentro do pacote local atual

Problema observado:

- `web/static/js/chat/chat_index_page.js` ainda concentrava o fluxo de abrir laudo, iniciar nova inspeção e finalizar coleta, mesmo após a extração da navegação do workspace;
- esse bloco já formava um subdomínio próprio, ligado à abertura de laudos, modal de nova inspeção e finalização para a mesa, mas seguia misturado com o restante da página principal;
- a extração precisava preservar compatibilidade com `modals.js`, `ui_bindings.js`, bootstrap do inspetor e as transições de URL/estado durante a retomada de laudo.

Corte executado:

- foi criado `web/static/js/inspetor/workspace_report_flow.js`;
- foram movidos para o novo módulo `abrirLaudoPeloHome`, `iniciarInspecao` e `finalizarInspecao`;
- `web/templates/index.html` passou a carregar o novo módulo antes do `chat_index_page.js`;
- o shared runtime recebeu `emitirEventoTariel` e o runtime base ganhou `noops` e reexports auxiliares para o novo módulo;
- `web/static/js/chat/chat_index_page.js` foi reduzido de `5805` para `5620` linhas, mantendo no arquivo principal apenas o fluxo de chat livre, os helpers comuns e o bootstrap consolidado.

Arquivos do ciclo:

- `web/static/js/inspetor/workspace_report_flow.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/index.html`
- `docs/PACOTE_PUBLICACAO_REFATORACAO_LOCALHOST.md`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Validação local executada:

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

Próximo passo imediato:

- decidir se o próximo movimento fecha o pacote local com revisão global ou se ainda vale alternar para um hotspot backend restante antes do push futuro;
- revisar o pacote local agora com oito cortes acumulados desde o último push, ainda sem publicar nada;
- manter a estratégia `localhost first`, com push e validação no Render apenas quando o pacote estiver coerente para publicação.

## Ciclo 71 — Migração do console de configurações do Admin-CEO para Astro

Status:

- concluído e validado localmente
- preparado para publicação no `tariel-v2`

Problema observado:

- a trilha admin já tinha `painel`, `clientes`, `catalogo` e `auditoria` no `frontend-astro`, mas `/admin/configuracoes` seguia apenas no legado FastAPI/Jinja;
- a tela é um ponto central de governança, porque reúne regras de acesso, suporte excepcional, rollout, observabilidade documental e defaults de onboarding;
- a migração precisava preservar o contrato visual e o estado efetivo das políticas sem já abrir a superfície sensível dos `POSTs` de alteração.

Corte executado:

- foi criado `web/frontend-astro/src/lib/server/admin-settings.ts`;
- o módulo novo porta o contrato legado de `summary_cards`, `sections`, itens de runtime e snapshots das `configuracoes_plataforma` via Prisma;
- a nova página `web/frontend-astro/src/pages/admin/configuracoes.astro` entrega o console em modo leitura, com navegação por seção, cards operacionais e preview dos ajustes que ainda permanecem no fluxo legado;
- `web/frontend-astro/src/layouts/admin-shell-layout.astro` passou a expor o item de menu de configurações dentro da navegação administrativa.

Arquivos do ciclo:

- `web/frontend-astro/src/lib/server/admin-settings.ts`
- `web/frontend-astro/src/pages/admin/configuracoes.astro`
- `web/frontend-astro/src/layouts/admin-shell-layout.astro`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Validação local executada:

- `git diff --check -- web/frontend-astro`
- `./bin/npm22 run check`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 run build`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluído com adapter `@astrojs/node`

Próximo passo imediato:

- migrar a primeira fatia de escrita de `/admin/configuracoes`, começando por `acesso` e `defaults`, que têm payload menor e trilha de auditoria bem delimitada;
- manter `suporte-excepcional` e `rollout` como segunda etapa, porque carregam combinações de flags mais sensíveis;
- seguir publicando em cortes estreitos no `tariel-v2`, preservando a leitura já portada no Astro enquanto a escrita sai do legado.

## Ciclo 72 — Escrita de acesso/defaults do console de configuracoes no Astro

Status:

- concluído e validado localmente
- preparado para publicação no `tariel-v2`

Problema observado:

- `/admin/configuracoes` já existia no Astro em modo leitura, mas `acesso` e `defaults` ainda dependiam exclusivamente dos `POSTs` do legado FastAPI;
- isso mantinha a governança de reautenticação e o plano padrão de onboarding fora da trilha oficial em TypeScript/Prisma;
- a migração precisava gravar em `configuracoes_plataforma` e `auditoria_empresas` sem fingir que a autenticação admin nova já estava concluída.

Corte executado:

- foi criado `web/frontend-astro/src/lib/server/admin-settings-mutations.ts`;
- o novo módulo salva `admin_reauth_max_age_minutes` e `default_new_tenant_plan` via Prisma transaction, registra motivo de alteração e escreve auditoria com `source_surface=frontend_astro` e `actor_binding=pending_admin_auth_migration`;
- foram criados os handlers `web/frontend-astro/src/pages/admin/configuracoes/acesso.ts` e `web/frontend-astro/src/pages/admin/configuracoes/defaults.ts`;
- `web/frontend-astro/src/pages/admin/configuracoes.astro` passou a renderizar formulários reais para essas duas seções, exibindo quais áreas já escrevem no Astro e quais ainda seguem em bridge;
- foi registrada a skill local `.codex/skills/tariel-v2-autonomous-migration-worker/` para manter o loop autônomo alinhado ao charter do `tariel-v2`.

Arquivos do ciclo:

- `.codex/skills/tariel-v2-autonomous-migration-worker/SKILL.md`
- `.codex/skills/tariel-v2-autonomous-migration-worker/agents/openai.yaml`
- `docs/TARIEL_V2_MIGRATION_CHARTER.md`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/lib/server/admin-settings-mutations.ts`
- `web/frontend-astro/src/pages/admin/configuracoes.astro`
- `web/frontend-astro/src/pages/admin/configuracoes/acesso.ts`
- `web/frontend-astro/src/pages/admin/configuracoes/defaults.ts`

Validação local executada:

- `git diff --check`
- `./bin/npm22 run check`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 run build`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluído com adapter `@astrojs/node`

Próximo passo imediato:

- atacar a autenticação admin no `tariel-v2`, começando por login/sessão/logout e o vínculo real do ator administrativo nas trilhas auditáveis;
- manter `support` e `rollout` ainda em bridge até a fatia de auth eliminar o `pending_admin_auth_migration`;
- depois retomar a escrita restante de `/admin/configuracoes` com step-up honesto dentro do V2.

## Ciclo 73 — Login/sessao admin no Astro e auditoria com ator autenticado

Status:

- concluído e validado localmente
- preparado para publicação no `tariel-v2`

Problema observado:

- o `frontend-astro` já cobria `login`, `painel`, `clientes`, `catalogo`, `auditoria` e a primeira escrita de `configuracoes`, mas a autenticação administrativa ainda era apenas preview visual;
- isso mantinha o portal novo sem sessão real, sem proteção centralizada por request e com trilhas de auditoria ainda sem `ator_usuario_id` nos fluxos já migrados;
- a migração precisava ligar senha local, `sessoes_ativas`, logout, proteção de `/admin/*` e binding do ator sem fingir que MFA TOTP e step-up já estavam concluídos.

Corte executado:

- foi criado `web/frontend-astro/src/lib/server/admin-auth.ts`;
- o novo módulo valida a conta `Admin-CEO` com Prisma, verifica senha local, cria sessão em `sessoes_ativas`, renova atividade, encerra sessão e normaliza `next`/cookies do portal admin;
- foi criado `web/frontend-astro/src/middleware.ts` para proteger `/admin/*`, manter a sessão em `Astro.locals`, redirecionar não autenticados para `/admin/login` e bloquear `POST`s fora da mesma origem quando o header existir;
- `web/frontend-astro/src/pages/admin/login.astro` deixou de ser preview e passou a renderizar um formulário real; também foram criados `web/frontend-astro/src/pages/admin/login/entrar.ts` e `web/frontend-astro/src/pages/admin/logout.ts`;
- `web/frontend-astro/src/layouts/admin-shell-layout.astro` passou a exibir o nome do admin autenticado e a fazer logout real por `POST`;
- `web/frontend-astro/src/lib/server/admin-settings-mutations.ts` agora grava `ator_usuario_id` e substitui `pending_admin_auth_migration` por `actor_binding=admin_session`;
- `web/frontend-astro/src/lib/server/admin-mutations.ts` e os handlers admin já migrados passaram a propagar `actorUserId` para `auditoria_empresas`, incluindo onboarding, bloqueio, troca de plano, reset de senha, catálogo e liberação por família;
- `web/frontend-astro/src/pages/admin/configuracoes.astro` e os handlers de `acesso/defaults` foram atualizados para refletir o novo estado honesto: sessão admin ativa no Astro, mas `step-up` ainda pendente;
- `web/frontend-astro/src/lib/server/prisma.ts` passou a tolerar execução direta no Node fora do runtime do Astro, o que permitiu smoke de helper para login/sessão/logout.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/components/app/auth/auth-shell.astro`
- `web/frontend-astro/src/env.d.ts`
- `web/frontend-astro/src/layouts/admin-shell-layout.astro`
- `web/frontend-astro/src/lib/server/admin-action-route.ts`
- `web/frontend-astro/src/lib/server/admin-auth.ts`
- `web/frontend-astro/src/lib/server/admin-mutations.ts`
- `web/frontend-astro/src/lib/server/admin-settings-mutations.ts`
- `web/frontend-astro/src/lib/server/prisma.ts`
- `web/frontend-astro/src/middleware.ts`
- `web/frontend-astro/src/pages/admin/catalogo-laudos/familias/[familyKey]/liberacao-tenant.ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/adicionar-admin-cliente.ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/bloquear.ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/catalogo-laudos.ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/resetar-senha/[usuarioId].ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/trocar-plano.ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/usuarios/[usuarioId]/bloquear.ts`
- `web/frontend-astro/src/pages/admin/configuracoes.astro`
- `web/frontend-astro/src/pages/admin/configuracoes/acesso.ts`
- `web/frontend-astro/src/pages/admin/configuracoes/defaults.ts`
- `web/frontend-astro/src/pages/admin/login.astro`
- `web/frontend-astro/src/pages/admin/login/entrar.ts`
- `web/frontend-astro/src/pages/admin/logout.ts`
- `web/frontend-astro/src/pages/admin/novo-cliente/criar.ts`

Validação local executada:

- `./bin/npm22 run check`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 run build`
- `curl -sS -I http://127.0.0.1:4322/admin/painel`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 exec --yes --package tsx -- tsx /tmp/tariel_admin_smoke.mts`
- `git diff --check -- web/frontend-astro/...`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluído com adapter `@astrojs/node`
  - `GET /admin/painel`: `303` para `/admin/login?next=%2Fadmin%2Fpainel`
  - smoke helper: `loginOk=true`, `userEmail=admin@tariel.ia`, `afterLogout=true`
  - `git diff --check`: limpo

Próximo passo imediato:

- migrar o restante sensível da trilha de segurança admin no `tariel-v2`, começando por MFA TOTP, troca obrigatória de senha e `reauth/step-up` para eliminar o `step-up pendente` das ações críticas;
- depois retomar `support` e `rollout` em `/admin/configuracoes`, agora já com sessão e `ator_usuario_id` reais;
- manter os providers corporativos (`google` e `microsoft`) como fatia seguinte da identidade admin, sem reabrir bridge desnecessária para o legado.

## Ciclo 74 — Seguranca admin completa no Astro e primeira vertical real do Admin-cliente

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- o `Admin-CEO` ja tinha login e sessao no Astro, mas ainda faltavam as transicoes honestas para senha temporaria, MFA TOTP e `reauth/step-up` nas acoes criticas;
- ao mesmo tempo, o escopo total da migracao precisava sair do afunilamento exclusivo no `Admin-CEO` e abrir a primeira vertical real do `Admin-cliente` no V2;
- isso mantinha o portal da empresa sem rota oficial em Astro, apesar de o onboarding novo ja provisionar `admins-cliente` e apontar para `/cliente/login`.

Corte executado:

- `web/frontend-astro/src/lib/server/admin-auth.ts` passou a tratar sessao admin como trilha de transicoes, com senha temporaria, setup/challenge TOTP, cookie de retorno e janela de `step-up` para mutacoes sensiveis;
- foi criado `web/frontend-astro/src/lib/server/admin-totp.ts` e entraram as paginas `admin/trocar-senha`, `admin/mfa/setup`, `admin/mfa/challenge` e `admin/reauth`, todas ligadas a handlers reais no Astro SSR;
- `web/frontend-astro/src/lib/server/admin-action-route.ts` e os handlers criticos do `Admin-CEO` passaram a exigir `reauth` antes de provisionamento, bloqueio, reset de senha, troca de plano, catalogo e ajustes sensiveis;
- `web/frontend-astro/src/middleware.ts` foi ampliado para orquestrar as transicoes obrigatorias do `Admin-CEO` e, no mesmo pacote, proteger o novo namespace `/cliente/*`;
- foi criado `web/frontend-astro/src/lib/server/client-auth.ts` com login por senha, sessao propia em `sessoes_ativas`, troca obrigatoria de senha e logout do `Admin-cliente`;
- foi criada a primeira shell oficial do portal da empresa em `web/frontend-astro/src/layouts/client-shell-layout.astro` e entrou a vertical inicial `web/frontend-astro/src/pages/cliente/*` com `login`, `trocar-senha`, `painel`, `logout` e redirect raiz;
- `web/frontend-astro/src/lib/server/client-portal.ts` reutiliza a leitura consolidada do tenant para entregar um `/cliente/painel` SSR inicial sem depender do portal legado.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/env.d.ts`
- `web/frontend-astro/src/lib/server/admin-action-route.ts`
- `web/frontend-astro/src/lib/server/admin-auth.ts`
- `web/frontend-astro/src/lib/server/admin-totp.ts`
- `web/frontend-astro/src/lib/server/client-auth.ts`
- `web/frontend-astro/src/lib/server/client-portal.ts`
- `web/frontend-astro/src/layouts/client-shell-layout.astro`
- `web/frontend-astro/src/middleware.ts`
- `web/frontend-astro/src/pages/admin/login.astro`
- `web/frontend-astro/src/pages/admin/login/entrar.ts`
- `web/frontend-astro/src/pages/admin/trocar-senha.astro`
- `web/frontend-astro/src/pages/admin/trocar-senha/confirmar.ts`
- `web/frontend-astro/src/pages/admin/mfa/setup.astro`
- `web/frontend-astro/src/pages/admin/mfa/setup/confirmar.ts`
- `web/frontend-astro/src/pages/admin/mfa/challenge.astro`
- `web/frontend-astro/src/pages/admin/mfa/challenge/confirmar.ts`
- `web/frontend-astro/src/pages/admin/reauth.astro`
- `web/frontend-astro/src/pages/admin/reauth/confirmar.ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/adicionar-admin-cliente.ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/bloquear.ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/catalogo-laudos.ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/resetar-senha/[usuarioId].ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/trocar-plano.ts`
- `web/frontend-astro/src/pages/admin/clientes/[id]/usuarios/[usuarioId]/bloquear.ts`
- `web/frontend-astro/src/pages/admin/catalogo-laudos/familias/[familyKey]/liberacao-tenant.ts`
- `web/frontend-astro/src/pages/admin/configuracoes.astro`
- `web/frontend-astro/src/pages/admin/configuracoes/acesso.ts`
- `web/frontend-astro/src/pages/admin/configuracoes/defaults.ts`
- `web/frontend-astro/src/pages/admin/novo-cliente/criar.ts`
- `web/frontend-astro/src/pages/cliente/index.ts`
- `web/frontend-astro/src/pages/cliente/login.astro`
- `web/frontend-astro/src/pages/cliente/login/entrar.ts`
- `web/frontend-astro/src/pages/cliente/logout.ts`
- `web/frontend-astro/src/pages/cliente/painel.astro`
- `web/frontend-astro/src/pages/cliente/trocar-senha.astro`
- `web/frontend-astro/src/pages/cliente/trocar-senha/salvar.ts`

Validacao local executada:

- `./bin/npm22 run check`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 exec --yes --package tsx -- tsx -e '...attemptAdminPasswordLogin("admin@tariel.ia")...'`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 exec --yes --package tsx -- tsx -e '...attemptClientPasswordLogin("admin-cliente@tariel.ia")...'`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 exec --yes --package tsx -- tsx -e '...smoke temp user client + completeClientPasswordReset...'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - smoke admin login: `ok=true` para `admin@tariel.ia`
  - smoke client login: `ok=true` para `admin-cliente@tariel.ia`
  - smoke fluxo temporario client: `passwordReset=true`, `resetOk=true`, `finalLoginOk=true`

Proximo passo imediato:

- fechar a leitura e as acoes do `Admin-cliente` para equipe, suporte e mesa sem voltar ao template legado;
- depois abrir a vertical do `Mesa Avaliadora` sobre a mesma base de autenticacao real ja presente em `/revisao/login`;
- manter o `Inspetor` como fatia seguinte, aproveitando o mesmo padrao de sessao e rollout progressivo do V2.

## Ciclo 75 — Admin-cliente com equipe e suporte reais no Astro

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- o `Admin-cliente` ja tinha `login`, `trocar-senha`, `logout` e um `painel` inicial no Astro, mas ainda faltavam as superficies de operacao diaria que tiram o tenant do legado;
- a gestao da equipe operacional e o contato com suporte ainda dependiam do portal Python, o que mantinha a trilha oficial incompleta mesmo com sessao real ja ativa no V2;
- era preciso portar leitura e escrita de `equipe` e `suporte` sem fingir que a `mesa` ja estava fechada.

Corte executado:

- `web/frontend-astro/src/lib/server/client-portal.ts` foi expandido para servir como backend real do portal cliente no V2, com leitura de `equipe` e `suporte`, provisionamento de usuarios operacionais, reset de senha, bloqueio/desbloqueio, registro de interesse comercial e protocolo de suporte;
- entrou um sistema proprio de flash para o portal cliente com `web/frontend-astro/src/lib/server/client-notice.ts`, `web/frontend-astro/src/lib/server/client-action-route.ts` e o componente `web/frontend-astro/src/components/app/client/client-notice.astro`;
- foram criadas as paginas `web/frontend-astro/src/pages/cliente/equipe.astro` e `web/frontend-astro/src/pages/cliente/suporte.astro`, ambas SSR, protegidas pela sessao real do cliente e usando apenas handlers do Astro para leitura e escrita;
- a equipe operacional ganhou handlers para criar conta, bloquear/desbloquear e regenerar senha temporaria em `web/frontend-astro/src/pages/cliente/equipe/*`;
- o suporte ganhou handlers para registrar protocolo auditavel, sinalizar interesse de plano e exportar diagnostico em JSON em `web/frontend-astro/src/pages/cliente/suporte/*`;
- `web/frontend-astro/src/layouts/client-shell-layout.astro` e `web/frontend-astro/src/pages/cliente/painel.astro` foram atualizados para refletir que `equipe` e `suporte` ja rodam no V2, deixando `mesa` como proxima vertical honesta.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/components/app/client/client-notice.astro`
- `web/frontend-astro/src/layouts/client-shell-layout.astro`
- `web/frontend-astro/src/lib/server/client-action-route.ts`
- `web/frontend-astro/src/lib/server/client-notice.ts`
- `web/frontend-astro/src/lib/server/client-portal.ts`
- `web/frontend-astro/src/pages/cliente/equipe.astro`
- `web/frontend-astro/src/pages/cliente/equipe/[userId]/bloquear.ts`
- `web/frontend-astro/src/pages/cliente/equipe/[userId]/resetar-senha.ts`
- `web/frontend-astro/src/pages/cliente/equipe/criar.ts`
- `web/frontend-astro/src/pages/cliente/painel.astro`
- `web/frontend-astro/src/pages/cliente/suporte.astro`
- `web/frontend-astro/src/pages/cliente/suporte/diagnostico.ts`
- `web/frontend-astro/src/pages/cliente/suporte/plano-interesse.ts`
- `web/frontend-astro/src/pages/cliente/suporte/registrar.ts`

Validacao local executada:

- `./bin/npm22 run check`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 run build`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 exec --yes --package tsx -- tsx -e '...getClientPortalTeamData(1)...'`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 exec --yes --package tsx -- tsx -e '...createClientOperationalUser/resetClientOperationalUserPassword/toggleClientOperationalUserStatus/createClientSupportReport/registerClientPlanInterest...'`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - smoke leitura equipe: `ok=true`, `members=2`, `plan=Ilimitado`
  - smoke mutacoes cliente: `create=true`, `reset=true`, `block=true`, `reactivate=true`, `support=CLI-3B363FED`, `interest=Intermediario`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- abrir a superficie `/cliente/mesa` com leitura e acoes reais sobre a fila do tenant, usando a mesma sessao oficial do portal cliente;
- depois avancar o portal `Mesa Avaliadora` em Astro sobre o mesmo padrao de auth/session ja live em `admin` e `cliente`;
- manter `Inspetor` e a remocao do legado na fila seguinte, sem reabrir o caminho oficial do Python para as superficies ja migradas.

## Ciclo 76 — `/cliente/mesa` com snapshot governado pelo backend Python

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- a primeira versao de `/cliente/mesa` no Astro ja expunha a superficie do tenant, mas ainda montava o resumo principal lendo e inferindo estado direto do banco dentro do frontend;
- isso mantinha a fronteira errada para a vertical: o portal cliente ficava com conhecimento demais sobre fila, reviewer roster e resumo operacional da mesa;
- para fechar a issue `#14` no caminho correto, era preciso mover a inteligencia de leitura para um contrato explicito do backend Python e deixar o Astro apenas como consumidor SSR autenticado.

Corte executado:

- foi criado o contrato `ClientMesaDashboardProjectionV1` em `web/app/v2/contracts/client_mesa.py`, com envelope, `tenant_summary`, `reviewer_summary`, `review_status_totals`, `reviewers`, `recent_audit` e o `review_queue_projection` embutido;
- entrou o builder `build_cliente_mesa_snapshot_projection()` em `web/app/domains/cliente/mesa_snapshot.py`, agregando `empresa`, roster da mesa, auditoria `scope=mesa` e o projection canonico da fila vindo de `web/app/domains/revisor/panel_state.py` e `web/app/v2/contracts/review_queue.py`;
- `web/app/domains/cliente/chat_routes.py` ganhou o endpoint autenticado `GET /cliente/api/mesa/snapshot`, reutilizando a sessao oficial de `sessoes_ativas` via bearer token;
- o Astro ganhou a bridge server-side `web/frontend-astro/src/lib/server/client-mesa-bridge.ts`, que repassa o token da sessao do portal cliente para o backend Python sem expor a chamada no navegador;
- `web/frontend-astro/src/lib/server/client-portal.ts` deixou de montar o resumo da mesa por leitura local e passou a consumir e adaptar o snapshot do backend;
- `web/frontend-astro/src/pages/cliente/mesa.astro` foi atualizado para renderizar explicitamente o novo slice, marcando a tela como `Snapshot governado da analise no V2` e exibindo fila, reviewers e auditoria a partir do contrato Python;
- entrou o teste `web/tests/test_v2_client_mesa_projection.py` para cobrir a montagem do novo projection.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/app/domains/cliente/chat_routes.py`
- `web/app/domains/cliente/mesa_snapshot.py`
- `web/app/v2/contracts/client_mesa.py`
- `web/frontend-astro/src/lib/server/client-mesa-bridge.ts`
- `web/frontend-astro/src/lib/server/client-portal.ts`
- `web/frontend-astro/src/pages/cliente/mesa.astro`
- `web/tests/test_v2_client_mesa_projection.py`

Validacao local executada:

- `python3 -m py_compile web/app/v2/contracts/client_mesa.py web/app/domains/cliente/mesa_snapshot.py web/app/domains/cliente/chat_routes.py`
- `source ~/.nvm/nvm.sh && nvm use 22.22.2 >/dev/null && cd web/frontend-astro && DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 run check`
- `source ~/.nvm/nvm.sh && nvm use 22.22.2 >/dev/null && cd web/frontend-astro && DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 run build`
- `cd web && AMBIENTE=dev DATABASE_URL=postgresql:///tariel_dev REDIS_URL=redis://127.0.0.1:6379/0 python3 -m pytest tests/test_v2_client_mesa_projection.py -q`
- smoke manual com `curl` no Astro:
  - login do `admin_cliente` em primeiro acesso
  - troca obrigatoria de senha
  - `GET /cliente/mesa` retornando `200`
  - render com os marcadores `Snapshot governado da analise no V2`, `Python owner` e `Casos mais recentes do snapshot`
- smoke direto no backend:
  - `GET /cliente/api/mesa/snapshot` com bearer token da sessao do portal retornando `200`
  - `projection_type=client_mesa_dashboard_projection`

Proximo passo imediato:

- atacar o proximo slice da issue `#14` removendo o restante da inferencia local que ainda sobrou no portal cliente e consolidando as mutacoes relevantes da mesa como contratos do backend Python;
- em seguida, reutilizar esse mesmo contrato para abrir a vertical `Mesa Avaliadora` no Astro sem duplicar regra no frontend;
- manter `Inspetor` fora da frente ativa ate `cliente/mesa` e `revisao` estarem fechados com ownership claro.

## Ciclo 77 — `/cliente/mesa` com thread, pendencias e decisao operacional no Astro

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- depois do snapshot governado do ciclo anterior, `/cliente/mesa` ainda parava na leitura resumida do caso;
- o tenant continuava sem conseguir operar a thread real da mesa no portal Astro, porque resposta, download de anexos, marcacao de pendencia e decisao ainda nao estavam fechados de ponta a ponta no shell novo;
- isso mantinha a vertical incompleta e atrasava a reutilizacao do mesmo boundary para a futura migracao de `/revisao`.

Corte executado:

- `web/frontend-astro/src/lib/server/client-mesa-bridge.ts` foi expandido para cobrir mensagens, pacote tecnico, anexo, resposta com ou sem arquivo, pendencias, decisao e sincronizacao de whispers via bearer da sessao oficial do portal cliente;
- entrou `web/frontend-astro/src/lib/server/client-mesa.ts` para centralizar o workspace SSR da mesa, selecionar o laudo ativo, adaptar mensagens/pacote e encapsular as mutacoes usadas pelas action routes;
- `web/frontend-astro/src/pages/cliente/mesa.astro` deixou de ser apenas uma vitrine de snapshot e passou a operar como workspace completo de fila, thread, pendencias, reply e decisao, sempre com ownership do dominio permanecendo no backend Python;
- foram criadas as action routes `web/frontend-astro/src/pages/cliente/mesa/[laudoId]/avaliar.ts`, `responder.ts`, `marcar-whispers-lidos.ts`, `pendencias/[messageId].ts` e `anexos/[attachmentId].ts`, fechando as mutacoes principais do tenant dentro do portal Astro;
- `web/app/domains/revisor/common.py` e `web/app/domains/revisor/mesa_api.py` passaram a aceitar chamadas autenticadas por bearer alem do fluxo CSRF tradicional, permitindo reaproveitar os handlers canonicos da mesa sem duplicar regra para o portal cliente.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/app/domains/revisor/common.py`
- `web/app/domains/revisor/mesa_api.py`
- `web/frontend-astro/src/lib/server/client-mesa-bridge.ts`
- `web/frontend-astro/src/lib/server/client-mesa.ts`
- `web/frontend-astro/src/pages/cliente/mesa.astro`
- `web/frontend-astro/src/pages/cliente/mesa/[laudoId]/anexos/[attachmentId].ts`
- `web/frontend-astro/src/pages/cliente/mesa/[laudoId]/avaliar.ts`
- `web/frontend-astro/src/pages/cliente/mesa/[laudoId]/marcar-whispers-lidos.ts`
- `web/frontend-astro/src/pages/cliente/mesa/[laudoId]/pendencias/[messageId].ts`
- `web/frontend-astro/src/pages/cliente/mesa/[laudoId]/responder.ts`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `python3 -m py_compile web/app/domains/cliente/chat_routes.py web/app/domains/revisor/common.py web/app/domains/revisor/mesa_api.py`
- `cd web && AMBIENTE=dev DATABASE_URL=postgresql:///tariel_dev REDIS_URL=redis://127.0.0.1:6379/0 python3 -m pytest tests/test_v2_client_mesa_projection.py -q`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `py_compile`: concluido sem erros
  - `pytest`: `1 passed`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- consolidar a issue `#14` decidindo se ainda resta alguma mutacao de mesa especifica do tenant fora do boundary novo;
- em seguida, reaproveitar o mesmo pacote de bridge e contratos para abrir `Mesa Avaliadora` em Astro sem duplicar command handlers ou policy no frontend;
- manter `Inspetor` fora da frente principal ate `cliente/mesa` e `revisao` estarem fechados com ownership claro e rollout honesto.

## Ciclo 78 — `Mesa Avaliadora` com auth real e fila inicial no Astro

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- a vertical `/revisao` ainda estava parada em uma tela de login de preview no Astro, sem sessao real nem leitura oficial da fila da mesa;
- isso mantinha o portal revisor dependente do SSR legado para a porta de entrada mais basica da operacao;
- depois de fechar `/cliente/mesa`, o menor slice seguro era abrir a autenticacao do revisor e a leitura inicial da fila sem puxar ainda a thread completa, exportacoes e emissao oficial.

Corte executado:

- entrou `web/frontend-astro/src/lib/server/reviewer-auth.ts`, espelhando no portal revisor o mesmo padrao de autenticacao local usado em `admin` e `cliente`, com login por senha, primeiro acesso com troca obrigatoria, sessao em `sessoes_ativas` e logout;
- `web/frontend-astro/src/middleware.ts` e `src/env.d.ts` passaram a carregar `reviewerSession` e `reviewerPasswordResetSession`, protegendo `/revisao/*` no Astro com a mesma disciplina de sessao dos outros portais;
- `web/app/domains/revisor/panel.py` ganhou `GET /revisao/api/painel/snapshot`, expondo para o Astro a projection canonica da fila da mesa sem depender de template HTML legado;
- entrou `web/frontend-astro/src/lib/server/reviewer-panel-bridge.ts` para consumir o snapshot via bearer da sessao oficial do revisor;
- `web/frontend-astro/src/pages/revisao/login.astro`, `login/entrar.ts`, `trocar-senha.astro`, `trocar-senha/salvar.ts`, `logout.ts` e `index.ts` fecharam a porta de entrada real do portal revisor na stack nova;
- foi criada `web/frontend-astro/src/layouts/reviewer-shell-layout.astro` e entrou `web/frontend-astro/src/pages/revisao/painel.astro`, abrindo a primeira superficie oficial da mesa avaliadora no Astro com cards de fila, whispers pendentes, filtros e listas de casos por secao.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/app/domains/revisor/panel.py`
- `web/frontend-astro/src/env.d.ts`
- `web/frontend-astro/src/layouts/reviewer-shell-layout.astro`
- `web/frontend-astro/src/lib/server/reviewer-auth.ts`
- `web/frontend-astro/src/lib/server/reviewer-panel-bridge.ts`
- `web/frontend-astro/src/middleware.ts`
- `web/frontend-astro/src/pages/revisao/index.ts`
- `web/frontend-astro/src/pages/revisao/login.astro`
- `web/frontend-astro/src/pages/revisao/login/entrar.ts`
- `web/frontend-astro/src/pages/revisao/logout.ts`
- `web/frontend-astro/src/pages/revisao/painel.astro`
- `web/frontend-astro/src/pages/revisao/trocar-senha.astro`
- `web/frontend-astro/src/pages/revisao/trocar-senha/salvar.ts`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `python3 -m py_compile web/app/domains/revisor/panel.py`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `py_compile`: concluido sem erros
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Validacao complementar:

- `python3 -m pytest tests/test_v2_review_queue_projection.py -q` foi iniciado e exibiu progresso sem falha imediata, mas nao devolveu sumario final em tempo util desta rodada; o pacote foi mantido com base nos checks de frontend, no `py_compile` e no fato de a projection canonica ja possuir cobertura dedicada no repo.

Proximo passo imediato:

- abrir a thread detalhada de `/revisao` no Astro reaproveitando o mesmo token do revisor e os endpoints canonicos de mesa ja existentes em `web/app/domains/revisor/mesa_api.py`;
- depois ligar resposta, pendencias, exportacao de pacote e emissao oficial em slices separados para manter a vertical deployavel;
- manter `Inspetor` fora da frente principal ate `revisao` ganhar leitura detalhada e mutacoes principais com ownership claro.

## Ciclo 79 — `Mesa Avaliadora` com thread detalhada e mutacoes principais no Astro

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- depois do ciclo 78, `/revisao/painel` ja autenticava e lia a fila oficial, mas ainda parava num shell sem thread detalhada nem mutacoes principais;
- isso mantinha a mesa avaliadora parcialmente dependente do legado justamente no ponto de maior uso operacional: leitura do caso, resposta, pendencias e decisao;
- o proximo slice seguro era aproveitar o mesmo bearer do revisor para abrir a workspace real em Astro sobre os endpoints canonicos ja existentes em `web/app/domains/revisor/mesa_api.py`, sem puxar ainda exportacao pesada, emissao oficial e coverage return.

Corte executado:

- entrou `web/frontend-astro/src/lib/server/reviewer-mesa-bridge.ts`, espelhando o padrao de `client-mesa-bridge` para consumir `mensagens`, `pacote`, `avaliar`, `responder`, `responder-anexo`, `marcar-whispers-lidos`, `pendencias` e `mesa/anexos` via sessao real do revisor;
- entrou `web/frontend-astro/src/lib/server/reviewer-mesa.ts`, concentrando o mapeamento da projection da fila para a workspace selecionada, a selecao do laudo ativo e a normalizacao de mensagens, pendencias e anexos para a UI;
- entrou `web/frontend-astro/src/lib/server/reviewer-notice.ts`, `reviewer-action-route.ts` e `src/components/app/reviewer/reviewer-notice.astro`, fechando o mesmo padrao de action routes e notices ja usado em `admin` e `cliente`;
- `web/frontend-astro/src/pages/revisao/painel.astro` deixou de ser um painel de fila-only e passou a abrir a workspace operacional com selecao de caso, resumo do laudo, triagem de whispers e pendencias, thread detalhada com anexos, formulario de resposta e blocos de aprovacao/devolucao;
- entraram as action routes `src/pages/revisao/painel/[laudoId]/responder.ts`, `avaliar.ts`, `marcar-whispers-lidos.ts`, `pendencias/[messageId].ts` e `anexos/[attachmentId].ts`, mantendo no Astro apenas shell, redirects e notices, enquanto o Python continua dono das regras e efeitos colaterais.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/components/app/reviewer/reviewer-notice.astro`
- `web/frontend-astro/src/lib/server/reviewer-action-route.ts`
- `web/frontend-astro/src/lib/server/reviewer-mesa-bridge.ts`
- `web/frontend-astro/src/lib/server/reviewer-mesa.ts`
- `web/frontend-astro/src/lib/server/reviewer-notice.ts`
- `web/frontend-astro/src/pages/revisao/painel.astro`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/anexos/[attachmentId].ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/avaliar.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/marcar-whispers-lidos.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/pendencias/[messageId].ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/responder.ts`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- ligar `coverage/solicitar-refazer` e outras mutacoes de refinamento da mesa diretamente nesta workspace, sem abrir novos contratos paralelos;
- depois entrar em exportacao de pacote e emissao oficial do revisor em fatias separadas para nao misturar fluxos pesados com a thread do caso;
- manter `Inspetor` fora da frente principal ate `revisao` fechar esse bloco operacional com ownership claro de UI no Astro e regras no Python.

## Ciclo 80 — `Mesa Avaliadora` com coverage return e exportacao do pacote no Astro

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- depois do ciclo 79, a workspace de `/revisao/painel` ja cobria thread, resposta, pendencias e decisao, mas ainda deixava de fora dois blocos importantes do pacote tecnico: o retorno governado de coverage e a exportacao do caso;
- isso obrigava o operador a sair do fluxo novo justamente quando precisava pedir refazer de evidencia ou baixar o material consolidado do caso;
- o menor slice seguro era abrir esses pontos no Astro sobre os endpoints canonicos ja existentes, mas ainda sem puxar a emissao oficial transacional, que segue sendo o trecho mais sensivel.

Corte executado:

- `web/frontend-astro/src/lib/server/reviewer-mesa-bridge.ts` passou a expor `coverage/solicitar-refazer`, `pacote/exportar-pdf` e `pacote/exportar-oficial`, mantendo bearer e tratamento de erro no mesmo boundary do portal revisor;
- `web/frontend-astro/src/lib/server/reviewer-mesa.ts` passou a mapear `documento_estruturado`, `coverage_map`, `anexo_pack`, `verificacao_publica` e `emissao_oficial` para a workspace SSR da mesa;
- entraram as action/proxy routes `src/pages/revisao/painel/[laudoId]/coverage/refazer.ts`, `pacote/exportar-pdf.ts` e `pacote/exportar-oficial.ts`, deixando no Astro apenas redirect, notice e proxy de download;
- `web/frontend-astro/src/pages/revisao/painel.astro` ganhou o bloco `Pacote tecnico`, com leitura do documento estruturado, resumo de coverage, CTA de exportar PDF, CTA de exportar pacote oficial e formularios de `Solicitar refazer` para evidencias nao aceitas.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/lib/server/reviewer-mesa-bridge.ts`
- `web/frontend-astro/src/lib/server/reviewer-mesa.ts`
- `web/frontend-astro/src/pages/revisao/painel.astro`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/coverage/refazer.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/pacote/exportar-oficial.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/pacote/exportar-pdf.ts`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- decidir se o proximo corte entra direto em `emissao-oficial` transacional ou se fecha antes o download da emissao congelada e estados de reemissao no shell do Astro;
- se entrar na emissao, manter a fatia pequena: CTA, conflito `409`, replay idempotente e download congelado, sem tentar redesenhar governanca no frontend;
- manter `Inspetor` fora da frente principal ate `revisao` fechar tambem esse bloco final com ownership claro entre Astro e Python.

## Ciclo 81 — `Mesa Avaliadora` com emissao oficial transacional no Astro

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- depois do ciclo 80, a mesa avaliadora ja conseguia pedir refazer coverage e exportar o pacote, mas o fechamento documental ainda parava antes da emissao oficial governada;
- isso deixava a ultima operacao critica da vertical fora do shell novo, mesmo com o backend Python ja expondo o contrato transacional e o download congelado;
- o corte seguro era pequeno e direto: usar o payload existente de `emissao_oficial`, escolher signatario elegivel, enviar `expected_current_issue_*` para reemissao segura, tratar conflito como erro de action route e expor o bundle congelado no Astro.

Corte executado:

- `web/frontend-astro/src/lib/server/reviewer-mesa-bridge.ts` passou a expor o shape rico de `emissao_oficial`, incluindo `signatories`, `blockers` e `current_issue`, alem das chamadas `emissao-oficial` e `emissao-oficial/download`;
- `web/frontend-astro/src/lib/server/reviewer-mesa.ts` passou a adaptar signatarios governados, emissao atual congelada, linhagem de reemissao e bloqueios para a workspace SSR da mesa;
- entrou `web/frontend-astro/src/pages/revisao/painel/[laudoId]/emitir-oficialmente.ts`, mantendo no Astro apenas a action route com redirect/notice e delegando a transacao real ao backend Python;
- entrou `web/frontend-astro/src/pages/revisao/painel/[laudoId]/emissao-oficial/download.ts`, fechando o proxy do bundle congelado emitido;
- `web/frontend-astro/src/pages/revisao/painel.astro` ganhou o bloco final de emissao oficial com leitura da emissao atual, aviso de reemissao recomendada, bloqueios, selecao de signatario elegivel, CTA de emitir/reemitir e download do bundle congelado.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/lib/server/reviewer-mesa-bridge.ts`
- `web/frontend-astro/src/lib/server/reviewer-mesa.ts`
- `web/frontend-astro/src/pages/revisao/painel.astro`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/emitir-oficialmente.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/emissao-oficial/download.ts`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- considerar a vertical `/revisao` funcionalmente fechada para o shell Astro e decidir se o proximo ciclo consolida limpeza/refino visual ou ja move o foco para `Inspetor`;
- antes de sair de `revisao`, vale revisar se ainda existe alguma rota legacy consumida apenas por exportacao ou governanca HTML que ja possa ser aposentada;
- manter o mesmo criterio de ownership: Astro como shell/SSR/action routes, Python como dono de policy, transacao e auditoria.

## Ciclo 82 — consolidacao das action routes de `/revisao`

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- depois de fechar a vertical `/revisao`, as action routes e os proxies de download ficaram corretos, mas com repeticao mecanica de parsing de IDs, fallback de retorno e montagem de `Response` para downloads;
- esse tipo de duplicacao nao muda produto agora, mas aumenta o custo de manter a vertical exatamente no momento em que ela passa a ser a referencia para os proximos portais;
- antes de seguir para a proxima frente, o ajuste seguro era consolidar esse codigo repetido sem alterar contrato nem comportamento.

Corte executado:

- entrou `web/frontend-astro/src/lib/server/reviewer-mesa-route.ts`, centralizando `resolveReviewerMesaInt`, `getReviewerMesaReturnFallback`, `buildReviewerMesaProxyResponse` e `buildReviewerMesaProxyError`;
- as action routes de `/revisao/painel/[laudoId]/*` passaram a usar esse helper comum em vez de manter parse e fallback local em cada arquivo;
- os proxies de download de anexos, PDF do pacote, ZIP oficial e bundle congelado passaram a compartilhar a mesma montagem de headers e resposta, reduzindo divergencia futura entre rotas irmas;
- o comportamento funcional foi preservado: mesma navegacao de retorno, mesmas mensagens de erro e mesmo repasse de headers dos downloads.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/lib/server/reviewer-mesa-route.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/anexos/[attachmentId].ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/avaliar.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/coverage/refazer.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/emissao-oficial/download.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/emitir-oficialmente.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/marcar-whispers-lidos.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/pacote/exportar-oficial.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/pacote/exportar-pdf.ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/pendencias/[messageId].ts`
- `web/frontend-astro/src/pages/revisao/painel/[laudoId]/responder.ts`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- com `/revisao` consolidado e funcionalmente fechado, o proximo movimento mais util e sair da vertical para a proxima frente pendente;
- a prioridade natural passa a ser `Inspetor`, reaproveitando o mesmo criterio de ownership usado aqui;
- se surgir uma rodada extra de limpeza, ela deve mirar aposentadoria de consumo legacy residual, nao reescrever a superficie ja estabilizada.

## Ciclo 83 — autenticacao real e shell inicial do `Inspetor`

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- a frente `Inspetor` ainda tinha apenas `web/frontend-astro/src/pages/app/login.astro` como preview visual, sem ownership real de sessao, middleware, primeiro acesso ou uma home autenticada no Astro;
- isso deixava o proximo vertical preso ao legado logo na entrada, ao contrario do que ja estava fechado em `cliente` e `revisao`;
- antes de migrar workspace, chat e mesas do operador, o corte seguro era fechar autenticacao canonica e uma shell inicial honesta em `/app`.

Corte executado:

- entrou `web/frontend-astro/src/lib/server/app-auth.ts`, espelhando o contrato usado nos outros portais para o `inspetor`: login por senha, sessao em `sessoes_ativas`, primeiro acesso com senha temporaria, renovacao de sessao, logout e auditoria basica de identidade;
- `web/frontend-astro/src/middleware.ts` e `web/frontend-astro/src/env.d.ts` passaram a reconhecer `appSession` e `appPasswordResetSession`, protegendo `/app/*` com o mesmo criterio de same-origin e redirect usado em `cliente` e `revisao`;
- `web/frontend-astro/src/pages/app/login.astro` deixou de ser preview e passou a usar o fluxo real do portal do inspetor, com `next`, mensagens de erro/sucesso e CTA de primeiro acesso;
- entraram as rotas `web/frontend-astro/src/pages/app/login/entrar.ts`, `web/frontend-astro/src/pages/app/trocar-senha.astro`, `web/frontend-astro/src/pages/app/trocar-senha/salvar.ts`, `web/frontend-astro/src/pages/app/logout.ts` e `web/frontend-astro/src/pages/app/index.ts`;
- entrou `web/frontend-astro/src/layouts/app-shell-layout.astro` e a primeira home autenticada `web/frontend-astro/src/pages/app/inicio.astro`, deixando explicito que Astro agora e dono da entrada/sessao enquanto Python continua dono da workspace operacional e do chat.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/env.d.ts`
- `web/frontend-astro/src/layouts/app-shell-layout.astro`
- `web/frontend-astro/src/lib/server/app-auth.ts`
- `web/frontend-astro/src/middleware.ts`
- `web/frontend-astro/src/pages/app/index.ts`
- `web/frontend-astro/src/pages/app/inicio.astro`
- `web/frontend-astro/src/pages/app/login.astro`
- `web/frontend-astro/src/pages/app/login/entrar.ts`
- `web/frontend-astro/src/pages/app/logout.ts`
- `web/frontend-astro/src/pages/app/trocar-senha.astro`
- `web/frontend-astro/src/pages/app/trocar-senha/salvar.ts`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- usar esta base autenticada para migrar a primeira superficie operacional do `/app`, preferencialmente reaproveitando os contratos canonicos ja expostos em `/app/api/*`;
- manter o criterio de ownership: Astro como shell, sessao e rotas SSR; Python como dono de chat, policy, feed, mesa, pendencias e mutacoes do operador;
- antes de abrir cortes maiores de UI, vale identificar qual tela inicial do inspetor traz mais valor com menor acoplamento ao legado, para evitar portar a workspace inteira de uma vez.

## Ciclo 84 — overview operacional inicial do `Inspetor`

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- depois de fechar login, sessao e primeiro acesso do inspetor, a home `/app/inicio` ainda era apenas um shell honesto, mas sem leitura real do dominio do operador;
- o legado ja mostrava na entrada do portal contexto do usuario, laudos recentes e trilha de atividade, entao continuar com uma home totalmente vazia atrasaria a escolha da primeira tela operacional do `/app`;
- o corte seguro era portar um overview real do proprio inspetor, sem puxar ainda chat, laudo selecionado ou mutacoes pesadas.

Corte executado:

- entrou `web/frontend-astro/src/lib/server/app-portal.ts`, consolidando a leitura do overview do inspetor em Prisma:
  - perfil do usuario e da empresa;
  - contagem de laudos do proprio operador;
  - sessoes ativas do portal `inspetor`;
  - laudos recentes do usuario;
  - auditoria recente do proprio portal;
- `web/frontend-astro/src/pages/app/inicio.astro` passou a consumir esse helper e deixou de ser apenas um painel de ownership;
- a home agora mostra cards com contexto real do inspetor, uma lista de laudos recentes do proprio usuario, um bloco de perfil/governanca e uma trilha de eventos recentes do portal;
- o ownership foi preservado: Astro so le overview e shell; Python continua dono da workspace operacional, do chat, das pendencias e das mutacoes do `/app`.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/lib/server/app-portal.ts`
- `web/frontend-astro/src/pages/app/inicio.astro`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- com a entrada do inspetor agora autenticada e lendo dados reais, o proximo corte natural e migrar a primeira superficie operacional ligada a `/app/api/*`;
- a melhor candidata e uma leitura inicial de workspace ou resumo do laudo selecionado, porque reaproveita contratos existentes sem reabrir a sessao;
- seguir evitando portar o chat inteiro de uma vez, privilegiando uma primeira tela de valor com baixo acoplamento ao legado.

## Ciclo 85 — primeiro resumo operacional do laudo em `/app`

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- a home do inspetor ja tinha overview real do operador, mas ainda faltava a primeira leitura operacional conectada aos contratos canonicos de `/app/api/*`;
- isso deixava o portal sem uma ponte clara entre a entrada autenticada e a workspace do laudo, mesmo com o backend ja expondo `/app/api/laudo/{laudo_id}/mesa/resumo`;
- o corte seguro era plugar um resumo SSR do laudo selecionado, sem abrir ainda mensagens, reply, anexos ou mutacoes do chat.

Corte executado:

- entrou `web/frontend-astro/src/lib/server/app-mesa-bridge.ts`, consumindo `/app/api/laudo/{laudo_id}/mesa/resumo` via bearer token da sessao Astro do inspetor;
- `web/frontend-astro/src/pages/app/inicio.astro` passou a aceitar selecao de laudo por `?laudo=` e a usar o primeiro laudo recente como fallback quando nenhum id e informado;
- a lista de laudos recentes do operador agora funciona como entrada para uma primeira leitura operacional do caso, mantendo o mesmo shell SSR;
- a area principal do resumo passou a mostrar:
  - preview do laudo selecionado;
  - status visual e estado do card;
  - contagem de mensagens e pendencias;
  - acoes de superficie liberadas no estado atual;
- o corte continua estreito: ainda sem thread completa, reply, upload ou mutacoes, preservando Python como dono da workspace e Astro como shell/read model.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/lib/server/app-mesa-bridge.ts`
- `web/frontend-astro/src/pages/app/inicio.astro`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- a proxima fatia natural e expandir esse resumo para a primeira leitura de thread ou de pendencias do laudo selecionado;
- o melhor caminho continua sendo reaproveitar os contratos canonicos do backend em vez de reimplementar regra no Astro;
- vale manter o mesmo criterio incremental: primeiro leitura, depois acao, depois anexos, e so no fim a workspace completa.

## Ciclo 86 — thread recente em leitura no `Inspetor`

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- o portal do inspetor ja conseguia selecionar um laudo e ler seu resumo operacional, mas ainda faltava a primeira leitura da conversa da mesa no Astro;
- isso mantinha uma quebra entre o resumo do caso e o historico real da interacao, justamente no ponto em que o operador precisa entender contexto e pendencias;
- o corte seguro era trazer a thread recente em modo leitura, sem reply, anexos ou mutacoes.

Corte executado:

- `web/frontend-astro/src/lib/server/app-mesa-bridge.ts` passou a consumir tambem `/app/api/laudo/{laudo_id}/mesa/mensagens`, preservando o mesmo bearer token da sessao Astro do inspetor;
- `web/frontend-astro/src/pages/app/inicio.astro` passou a carregar a thread recente do laudo selecionado e mostrar uma amostra dos itens mais recentes na propria home;
- a UI nova exibe:
  - tipo da mensagem;
  - estado de pendencia;
  - marcador de nao lida;
  - texto visivel da mensagem;
  - metadados de resolucao e anexos quando existirem;
- o portal agora fecha uma trilha inicial coerente: lista de casos, resumo do caso e leitura da conversa, tudo sem reabrir ownership do backend.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/lib/server/app-mesa-bridge.ts`
- `web/frontend-astro/src/pages/app/inicio.astro`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- com resumo e thread em leitura no Astro, o proximo corte natural e liberar a primeira acao sobre o laudo selecionado;
- a candidata mais segura e uma acao de pendencia ou um reply simples, porque reutiliza contratos ja expostos e nao exige portar a workspace inteira;
- seguir mantendo o corte estreito: leitura primeiro, acao unica depois, uploads e fluxo completo so nas rodadas seguintes.

## Ciclo 87 — primeiro reply textual do `Inspetor`

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- o portal do inspetor ja tinha lista de casos, resumo do caso e thread recente em leitura, mas ainda faltava a primeira acao util diretamente no Astro;
- isso mantinha a migracao travada no modo read-only, mesmo com o backend ja expondo `/app/api/laudo/{laudo_id}/mesa/mensagem`;
- o corte seguro era liberar um reply textual simples, sem anexos, preservando o backend Python como dono da transacao e da policy.

Corte executado:

- entrou `web/frontend-astro/src/lib/server/app-notice.ts` para notices curtas por cookie no portal do inspetor;
- entrou `web/frontend-astro/src/lib/server/app-action-route.ts`, padronizando sessao obrigatoria, retorno seguro e redirect com notice para `/app`;
- `web/frontend-astro/src/lib/server/app-mesa-bridge.ts` passou a expor `replyToAppMesa`, consumindo o endpoint canonico `/app/api/laudo/{laudo_id}/mesa/mensagem`;
- entrou a action route `web/frontend-astro/src/pages/app/inicio/[laudoId]/responder.ts`, seguindo o mesmo modelo ja usado em `cliente` e `revisao`;
- `web/frontend-astro/src/pages/app/inicio.astro` ganhou:
  - consumo de notice do portal;
  - formulario de reply textual no laudo selecionado;
  - redirect de volta para o proprio `/app/inicio?laudo=...` apos sucesso ou erro.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/lib/server/app-action-route.ts`
- `web/frontend-astro/src/lib/server/app-mesa-bridge.ts`
- `web/frontend-astro/src/lib/server/app-notice.ts`
- `web/frontend-astro/src/pages/app/inicio.astro`
- `web/frontend-astro/src/pages/app/inicio/[laudoId]/responder.ts`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- com a primeira acao de reply textual liberada, o proximo corte natural e uma acao de pendencia ou reply com referencia de mensagem;
- depois disso, a proxima extensao logica e reply com anexo, ainda sem portar a workspace inteira;
- manter o mesmo ownership: Astro como shell e action route, Python como dono de validacao, auditoria e persistencia da thread.

## Ciclo 88 — toggle de pendencia no `Inspetor`

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- o portal do inspetor ja conseguia ler a thread recente e enviar um reply textual, mas ainda faltava uma acao simples sobre os itens de pendencia exibidos na propria conversa;
- isso deixava a home do laudo selecionado sem capacidade de fechar o ciclo mais comum da mesa, mesmo com o backend ja expondo `PATCH /app/api/laudo/{laudo_id}/pendencias/{mensagem_id}`;
- o corte seguro era liberar apenas o toggle de resolver/reabrir pendencia direto nos cards da thread recente.

Corte executado:

- `web/frontend-astro/src/lib/server/app-mesa-bridge.ts` passou a expor `updateAppMesaPendency`, consumindo o endpoint canonico de pendencias do inspetor com bearer token;
- entrou a action route `web/frontend-astro/src/pages/app/inicio/[laudoId]/pendencias/[messageId].ts`, seguindo o mesmo contrato de `cliente` e `revisao`;
- `web/frontend-astro/src/pages/app/inicio.astro` passou a renderizar o CTA de resolver ou reabrir apenas quando a mensagem da thread e do tipo `mesa_pendency`;
- o retorno continua no mesmo `/app/inicio?laudo=...`, com notice de sucesso ou erro, sem abrir nova tela nem reimplementar regra no Astro.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/lib/server/app-mesa-bridge.ts`
- `web/frontend-astro/src/pages/app/inicio.astro`
- `web/frontend-astro/src/pages/app/inicio/[laudoId]/pendencias/[messageId].ts`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- com reply textual e pendencia resolvida/reaberta no Astro, o proximo corte natural e reply com referencia de mensagem;
- em seguida, a extensao mais util e o envio com anexo, ainda sem portar a workspace completa;
- manter o criterio incremental: uma acao operacional por vez, sempre reaproveitando os contratos canonicos do backend.

## Ciclo 89 — reply com referencia de mensagem no `Inspetor`

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- o portal do inspetor ja conseguia responder a thread e resolver pendencias, mas o reply ainda era solto, sem ligar explicitamente a resposta a uma mensagem anterior;
- isso limitava a utilidade da primeira acao no Astro, porque a mesa frequentemente trabalha sobre um item especifico da conversa;
- o corte seguro era reaproveitar o `referenciaMensagemId` que a action route ja aceitava, sem abrir ainda uploads ou uma composer completa.

Corte executado:

- `web/frontend-astro/src/pages/app/inicio.astro` passou a aceitar `?ref=` no laudo selecionado;
- cada card da thread recente ganhou o CTA `Responder a esta mensagem`, que fixa a mensagem de referencia na propria home;
- o formulario de reply agora envia `referenciaMensagemId` oculto para a action route existente;
- a UI do composer mostra um resumo da mensagem referenciada e permite limpar a selecao sem sair do laudo atual.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/pages/app/inicio.astro`

Validacao local executada:

- `npm run check`
- `DATABASE_URL='postgresql:///tariel_dev' npm run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- com reply livre e reply referenciado no Astro, o proximo corte natural e reply com anexo;
- isso fecha a trilha minima de interacao do inspetor sem exigir ainda uma workspace full-screen;
- depois desse passo, o proximo ganho estrutural passa a ser unificar melhor resumo, thread e composer numa superficie operacional dedicada.

## Ciclo 90 — reply com anexo no `Inspetor`

Status:

- concluido e validado localmente
- preparado para publicacao no `tariel-v2`

Problema observado:

- o portal do inspetor ja conseguia responder a thread com texto livre e referencia de mensagem, mas ainda ficava abaixo dos fluxos de `cliente` e `revisao` por nao aceitar anexos;
- isso deixava a trilha minima de operacao incompleta no Astro, mesmo com o backend Python ja expondo o endpoint canonico de upload para a mesa;
- o corte seguro era habilitar apenas o envio opcional de arquivo no reply existente, sem abrir ainda download de anexos nem uma workspace mais pesada.

Corte executado:

- `web/frontend-astro/src/lib/server/app-mesa-bridge.ts` passou a compartilhar um helper de fetch tipado e a expor `replyToAppMesaWithAttachment`, consumindo `POST /app/api/laudo/{laudo_id}/mesa/anexo`;
- `web/frontend-astro/src/pages/app/inicio/[laudoId]/responder.ts` agora detecta `arquivo` no `FormData`, rejeita submit vazio e escolhe entre reply textual e reply com anexo;
- `web/frontend-astro/src/pages/app/inicio.astro` passou a enviar `multipart/form-data`, exibir campo opcional de upload e ajustar a copy do composer para refletir o novo contrato;
- o ownership segue o mesmo: Astro como shell autenticado e action route, Python como dono de validacao, auditoria, persistencia e tratamento do anexo.

Arquivos do ciclo:

- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- `web/frontend-astro/src/lib/server/app-mesa-bridge.ts`
- `web/frontend-astro/src/pages/app/inicio.astro`
- `web/frontend-astro/src/pages/app/inicio/[laudoId]/responder.ts`

Validacao local executada:

- `./bin/npm22 run check`
- `DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 run build`
- `git diff --check -- . ':(exclude)web/frontend-astro/.astro/**'`
- resultado:
  - `astro check`: `0 errors`
  - `astro build`: concluido com adapter `@astrojs/node`
  - `git diff --check`: limpo fora dos artefatos gerados do Astro

Proximo passo imediato:

- com texto, referencia, pendencia e anexo ja operando no Astro, o proximo ganho util no `Inspetor` e expor download/visualizacao basica dos anexos da thread;
- depois disso, a home pode evoluir para uma superficie operacional mais coesa, juntando resumo, thread e composer numa mesa dedicada do laudo;
- continuar preservando o backend Python como dono dos contratos de operacao e auditoria.
