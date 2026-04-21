# Epic 09L - History Navigation Stabilization

## Objetivo

Estabilizar de forma conservadora a rodada assistida do piloto Android V2 no tenant demo, sem alterar UX visivel, payloads publicos ou regras de negocio, para que o runner:

- encontre o laudo alvo `80` no historico com selecao deterministica
- atravesse a abertura da thread `Mesa` sem depender de sinais visuais frageis
- gere artefatos operacionais honestos sobre o que foi realmente aberto e o que ainda nao tem `human_ack`

## Causa mais provavel da falha anterior

Os artefatos reais mostraram uma cadeia de falhas, nao um unico problema:

1. `artifacts/mobile_pilot_run/20260326_144559`
   - o `hideKeyboard` apos digitar `80` no historico disparava `KEYCODE_BACK`
   - o Android voltava para o launcher e a rodada perdia o shell do app
2. `artifacts/mobile_pilot_run/20260326_145944`
   - o laudo `80` aparecia filtrado no historico
   - quando era o primeiro item da lista, o wrapper usava apenas `history-first-item-button`
   - o seletor `history-item-80` nao existia naquele caso
3. `artifacts/mobile_pilot_run/20260326_151541`
   - depois da correcao dos IDs, o target `80` passou a ser encontrado e tocado
   - a tela `Mesa` abriu, mas o flow ainda esperava `mesa-composer-input`
   - o composer da Mesa so fica visivel quando `mesaTemMensagens` e isso nao era verdade para o laudo `80`

Conclusao:

- a falha original do `history-item-80` veio de uma combinacao entre perda de contexto pelo teclado, fechamento indevido do historico e conflito entre marker do primeiro item e marker do alvo
- o bloqueio final desta fase nao e mais navegacao do historico; agora o limitador real e ausencia de `human_ack` e de trafego V2 observado pelo backend

## Implementacao aplicada

### Ganchos estaveis no app

Arquivos principais:

- `android/src/features/common/useSidePanelsController.ts`
- `android/src/features/history/HistoryDrawerPanel.tsx`
- `android/src/features/chat/ThreadConversationPane.tsx`
- `android/src/features/InspectorMobileApp.tsx`
- `android/src/features/common/buildAuthenticatedLayoutSections.ts`
- `android/src/features/common/inspectorUiBuilderTypes.ts`

Mudancas:

- o historico nao fecha mais quando o teclado sobe durante a busca do drawer
- a busca do historico passou a propagar `focus/blur` para o controlador lateral
- cada laudo do historico agora expõe sempre `history-item-<id>`
- o primeiro item continua com `history-first-item-button`, mas sem esconder o ID real do laudo
- a superficie `Mesa` ganhou markers estaveis:
  - `mesa-thread-surface`
  - `mesa-thread-loading`
  - `mesa-thread-unavailable`
  - `mesa-thread-loaded`
  - `mesa-thread-empty-state`

### Runner e Maestro

Arquivos principais:

- `android/maestro/mobile-v2-pilot-run.yaml`
- `scripts/run_mobile_pilot_runner.py`

Mudancas:

- remoção do `hideKeyboard` destrutivo depois da busca do historico
- screenshots adicionais do historico e da thread
- `retry` curto no tap de `history-item-${TARGET_LAUDO_ID}` com `retryTapIfNoChange: true`
- troca da espera final de `mesa-composer-input` para `mesa-thread-surface`
- classificacao do runner ajustada para distinguir `thread_opened_but_no_human_ack`

## Validacao real executada

Checks executados nesta fase:

- `maestro check-syntax android/maestro/mobile-v2-pilot-run.yaml`
- `cd android && npm test -- --runInBand src/features/common/useSidePanelsController.test.ts src/features/history/HistoryDrawerPanel.test.tsx src/features/history/useHistoryController.test.ts src/features/chat/ThreadConversationPane.test.tsx`
- `cd android && npm run typecheck`
- `python3 -m py_compile scripts/run_mobile_pilot_runner.py`
- `python3 -m pytest -q web/tests/test_smoke.py`

Todos passaram antes da rodada final.

## Rodadas reais desta fase

### Rodada intermediaria - `20260326_151541`

- o target `80` foi encontrado, a gaveta do historico fechou e a UI chegou na tela `Mesa`
- o bloqueio foi deslocado para `mesa-composer-input`
- essa rodada provou que o problema do historico estava resolvido, mas o criterio final do flow ainda era invalido

### Rodada final e autoritativa - `20260326_152441`

Artefatos:

- `artifacts/mobile_pilot_run/20260326_152441/final_report.md`
- `artifacts/mobile_pilot_run/20260326_152441/maestro_run.txt`
- `artifacts/mobile_pilot_run/20260326_152441/operator_run_status_after.json`
- `artifacts/mobile_pilot_run/20260326_152441/backend_summary_after.json`
- `artifacts/mobile_pilot_run/20260326_152441/screenshots/screenshots/pilot-run-mesa-thread.png`
- `artifacts/mobile_pilot_run/20260326_152441/ui_dumps/ui_after_maestro.xml`

O que aconteceu de verdade:

- device fisico usado: `RQCW20887GV / SM-S918B`
- backend local subiu e o `operator_run` foi iniciado para `feed/thread -> laudo 80`
- o app foi rebuildado/reinstalado e aberto com sucesso
- o flow abriu configuracoes, central de atividade e historico
- a busca por `80` encontrou o laudo alvo
- o tap no item do historico exigiu retry conservador
- a tela `Mesa` abriu de forma real e o marker `mesa-thread-surface` ficou visivel
- a screenshot `pilot-run-mesa-thread.png` foi gerada
- o `operator_run` encerrou em `completed_inconclusive`
- o `final_report.md` passou a classificar corretamente `thread_opened_but_no_human_ack`

## Resultado honesto desta fase

- navegacao do historico estabilizada: sim
- thread `Mesa` aberta de forma automatizada: sim
- `feed` coberto no backend com evidencia V2: nao
- `thread` coberta no backend com evidencia V2: nao
- `human_ack`: nao
- resultado operacional correto da rodada final: `thread_opened_but_no_human_ack`

O backend continuou reportando:

- `v2_served=0`
- `human_confirmed_count=0`
- `candidate_ready_for_real_tenant=false`

Portanto o piloto segue inconclusivo para promocao, apesar de a navegacao UI ter sido estabilizada.

## Como repetir

No workspace atual:

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado"
python3 scripts/run_mobile_pilot_runner.py
```

Artefatos esperados:

- nova pasta em `artifacts/mobile_pilot_run/<timestamp>`
- `final_report.md`
- `maestro_run.txt`
- screenshots da rodada
- `operator_run_status_after.json`
- `backend_summary_after.json`

## O que ainda falta

- confirmar por que a rodada abre a thread `Mesa`, mas ainda nao produz requests V2 observados pelo backend
- obter `human_ack` real da superficie `feed` e da superficie `thread`
- decidir se a cobertura final exigira uma confirmacao humana assistida no device ou um evento de validacao explicito sem alterar UX
