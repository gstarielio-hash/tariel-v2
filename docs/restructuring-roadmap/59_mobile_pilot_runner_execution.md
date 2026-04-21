# Runner Operacional - execucao assistida do piloto mobile V2 no tenant demo

## Escopo desta execucao

- Workspace:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- Tenant alvo:
  - `empresa_id=1`
  - `Empresa Demo (DEV)`
- Objetivo:
  - executar um runner operacional real para o piloto mobile V2 no Android, com preparacao de ambiente, backend local, sessao organica, operator run, abertura do app, tentativa de navegacao assistida, coleta de artefatos e encerramento conservador.

## Ambiente encontrado

- Device ADB ativo:
  - `RQCW20887GV`
  - `SM-S918B`
- Ferramentas:
  - `adb 37.0.0`
  - `node v20.20.1`
  - `npm 11.12.0`
  - `python 3.12.3`
  - `maestro 2.3.0`
- App Android:
  - package `com.tarielia.inspetor`
  - main activity `.MainActivity`
  - script de instalacao usado: `npm run android:preview`
- Backend local:
  - `http://127.0.0.1:8000`
  - `adb reverse` garantido para `8000`, `8081`, `19000` e `19001`

## Flags e configuracao usadas

- Android:
  - `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED=1`
  - `EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`
- Backend:
  - `TARIEL_V2_ANDROID_PUBLIC_CONTRACT=1`
  - `TARIEL_V2_ANDROID_ROLLOUT=1`
  - `TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY=1`
  - `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=1=pilot_enabled`
  - `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=promoted,1:thread=promoted`
  - `TARIEL_V2_ANDROID_PILOT_PROBE=1`
- Observacao:
  - o runner gerou um snapshot completo das flags em `artifacts/mobile_pilot_run/.../flags_snapshot.json`; este documento lista apenas as flags relevantes para o piloto.

## Artefatos gerados

- Tentativa 1:
  - `artifacts/mobile_pilot_run/20260326_111352`
- Tentativa 2:
  - `artifacts/mobile_pilot_run/20260326_112134`
- Tentativa 3:
  - `artifacts/mobile_pilot_run/20260326_113319`
- Tentativa 4:
  - `artifacts/mobile_pilot_run/20260326_141933`
- Principais arquivos em cada run:
  - `environment.txt`
  - `adb_devices.txt`
  - `adb_reverse.txt`
  - `backend_summary_before.json`
  - `backend_summary_after.json`
  - `capabilities_before.json`
  - `capabilities_after.json`
  - `operator_run_status_before.json`
  - `operator_run_status_after.json`
  - `maestro_run.txt`
  - `logcat_excerpt.txt`
  - `screenshots/`
  - `ui_dumps/`
  - `final_report.md`

## O que o runner executou de verdade

- Descobriu o device ADB real e validou o ambiente.
- Garantiu `adb reverse` para o backend local e portas auxiliares do fluxo React Native.
- Validou credenciais do usuario mobile demo e do admin legado.
- Coletou `summary`, `capabilities` e `operator run status` antes da rodada.
- Subiu sessao organica e `operator validation run` do tenant demo.
- Instalou e relancou o app Android via `npm run android:preview`.
- Rodou automacao Maestro com captura de screenshots, debug e logcat.
- Fechou o run de forma conservadora quando a cobertura nao foi confirmada.

## Tentativas reais e resultado observado

### Tentativa 1 - `20260326_111352`

- O app foi instalado, aberto e autenticado com sucesso.
- A automacao chegou ao shell do app e abriu configuracoes.
- O flow falhou ao tentar localizar `settings-system-activity-center-row`.
- Resultado:
  - execucao parcial
  - sem cobertura confirmada de `feed`
  - sem cobertura confirmada de `thread`

### Tentativa 2 - `20260326_112134`

- O flow foi ajustado para entrar na secao correta de configuracoes.
- A automacao abriu a central de atividade com sucesso.
- A central apareceu vazia no screenshot `pilot-run-activity-center.png`.
- Depois disso, a automacao tentou abrir historico usando um alvo fixo `history-item-1`.
- Esse ponto revelou um problema real do backend operacional:
  - o `operator run` estava escolhendo `laudo_id=1`
  - esse laudo nao era do inspetor demo autenticado (`usuario_id=10`)
  - a automacao nao conseguia cobrir `feed` e `thread` com esse target
- Resultado:
  - execucao parcial
  - sem cobertura confirmada de `feed`
  - sem cobertura confirmada de `thread`

## Correcao concreta feita a partir da execucao

- O backend de validacao organica foi corrigido para preferir targets do tenant demo que sejam acessiveis aos usuarios internos seguros do proprio demo.
- Arquivo ajustado:
  - `web/app/v2/mobile_organic_validation.py`
- Efeito observado apos restart do backend:
  - `operator run` passou a selecionar `laudo_id=80` para `feed` e `thread`
  - o target passou a ser coerente com o inspetor demo autenticado
- Teste adicionado:
  - `web/tests/test_v2_android_operator_run.py::test_operator_run_prefere_targets_acessiveis_ao_inspetor_demo`

### Tentativa 3 - `20260326_113319`

- O backend foi reiniciado com a correcao acima.
- O `operator run` subiu corretamente com:
  - `operator_run_id=oprv_92496d5e88cb`
  - `session_id=orgv_e80f694c4ed9`
  - target `80` para `feed` e `thread`
- O app foi reinstalado e relancado.
- O Maestro falhou no primeiro checkpoint visual do shell:
  - `open-settings-button` nao estava visivel
  - o screenshot de falha mostra o device em tela preta/estado travado, nao no shell do app
- O runner abortou o `operator run` de forma conservadora.
- Resultado:
  - `operator_run_outcome=aborted`
  - `operator_run_reason=operator_aborted`
  - `pilot_outcome_after=insufficient_evidence`
  - `candidate_ready_for_real_tenant_after=false`

### Tentativa 4 - `20260326_141933`

- O runner foi reexecutado de verdade no mesmo workspace, sem alterar contratos, UX ou regras de negocio.
- O preflight confirmou:
  - `device_id=RQCW20887GV`
  - backend `healthy` em `127.0.0.1:8000`
  - `operator_run_id=oprv_b75587c2d930`
  - `session_id=orgv_04a5acc2f99c`
  - targets minimos:
    - `feed -> laudo 80`
    - `thread -> laudo 80`
- O app foi rebuildado, reinstalado e relancado com sucesso via `npm run android:preview`.
- O flow Maestro cobriu de forma real:
  - login do app
  - shell principal
  - abertura de configuracoes
  - abertura da central de atividade
  - retorno ao shell
  - abertura do historico
  - digitacao do target `80` em `history-search-input`
- O bloqueio operacional aconteceu no historico:
  - o Maestro falhou em `Assert that id: history-item-80 is visible`
  - o dump de UI coletado apos a falha nao trazia `history-item-80` nem `history-search-input`
  - a tela ja tinha voltado para o shell principal com `open-history-button`, `mesa-tab-button` e `chat-composer-input`
- O runner abortou o `operator run` de forma conservadora.
- Resultado:
  - `operator_run_outcome=aborted`
  - `operator_run_reason=operator_aborted`
  - `pilot_outcome_after=insufficient_evidence`
  - `candidate_ready_for_real_tenant_after=false`

## Summary antes e depois da ultima tentativa

### Antes

- `rollout_state=pilot_enabled`
- `feed_rollout_state=promoted`
- `thread_rollout_state=promoted`
- `operator_run_outcome=in_progress`
- `organic_validation_active=true`
- `operator_run_id=oprv_b75587c2d930`
- `session_id=orgv_04a5acc2f99c`
- targets minimos exigidos:
  - `feed -> laudo 80`
  - `thread -> laudo 80`
- cobertura observada:
  - `0` requests V2
  - `0` human confirmed

### Depois

- `operator_run_outcome=aborted`
- `organic_validation_active=false`
- `organic_validation_outcome=insufficient_evidence`
- `candidate_ready_for_real_tenant=false`
- `capabilities_checks=1`
- `v2_served=0`
- `legacy_fallbacks=0`
- cobertura observada:
  - `feed`: nao coberto
  - `thread`: nao coberto
  - `human_confirmed_count=0`
  - `observed_requests=0`

## Resultado operacional honesto

- O runner operacional foi executado de verdade no device fisico.
- A instalacao do app, o bootstrap do backend, a abertura de sessao organica e o `operator run` funcionaram.
- A automacao UI foi apenas parcial:
  - houve navegacao real ate o app, ate a central de atividade e ate o historico
  - a busca do historico nao confirmou visibilidade do target `history-item-80`
  - nao houve cobertura confirmada de `feed` nem `thread`
  - nao houve `human_ack`
- Classificacao honesta desta rodada:
  - `partial_execution`

## Como repetir

1. Garantir o device desbloqueado, com a tela ligada e no launcher.
2. Manter o backend local acessivel em `127.0.0.1:8000`.
3. Rodar:
   - `python3 scripts/run_mobile_pilot_runner.py`
4. Conferir os artefatos em:
   - `artifacts/mobile_pilot_run/<timestamp>/`

## Rollback rapido

- Encerrar sessao organica:
  - `POST /admin/api/mobile-v2-rollout/organic-validation/stop`
- Encerrar ou abortar run:
  - `POST /admin/api/mobile-v2-rollout/operator-run/finish`
  - `POST /admin/api/mobile-v2-rollout/operator-run/finish?abort=1`
- Forcar o tenant demo ao legado:
  - `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=1=legacy_only`
- Forcar rollback por superficie:
  - `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=rollback_forced,1:thread=rollback_forced`
- Desligar o gate do app:
  - `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED=0`

## O que ainda falta

- garantir um estado previsivel do device antes da automacao UI, evitando tela bloqueada ou preta no relancamento
- estabilizar a transicao do historico depois da busca por `80`, sem assumir clique cego quando o item nao esta visivel
- cobrir o `feed` real do laudo `80` com o app aberto e responsivo
- abrir a `thread` do mesmo laudo e observar `human_ack`
- sair de `insufficient_evidence` com evidencias humanas reais, nao apenas com bootstrap tecnico
