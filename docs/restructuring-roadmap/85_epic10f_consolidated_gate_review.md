# Gate review consolidado do `report_finalize_stream` com toda a evidencia ate 10H

## Objetivo

Consolidar toda a evidencia acumulada do recorte:

- `POST /app/api/chat`
- branch `eh_comando_finalizar`
- `operation_kind=report_finalize_stream`

para fechar uma decisao unica de roadmap, sem abrir `enforce` e sem repetir campanha operacional desnecessaria.

## Escopo consolidado

Fontes obrigatorias usadas nesta revisao:

- arquitetura/produto canonicos em `/home/gabriel/Area de trabalho/Tarie 2`
- docs locais de `67` ate `84`
- artifacts:
  - `artifacts/document_hard_gate_validation_10f/20260327_155813/`
  - `artifacts/document_hard_gate_review_10f/20260327_161354/`
  - `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/`
  - `artifacts/document_hard_gate_review_10f_campaign/20260327_204148/`
  - `artifacts/document_hard_gate_validation_10g/20260327_211111/`
  - `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/`
  - `artifacts/document_hard_gate_shadow_campaign_10h/20260327_214808/`
- codigo atual auditado:
  - `web/app/domains/chat/chat_stream_routes.py`
  - `web/app/domains/chat/report_finalize_stream_shadow.py`
  - `web/app/v2/document/hard_gate.py`
  - `web/app/v2/acl/technical_case_core.py`
  - `web/app/v2/policy/engine.py`

## Como as fases se conectam

- 10F abriu `report_finalize_stream` em `shadow_only`
  - confirmou semantica forte e ausencia de `did_block`
- review inicial 10F:
  - decidiu `hold_before_any_enforce`
  - principais faltas:
    - amostra pequena
    - summary volatil em memoria
    - branch ainda dentro do endpoint principal de chat/SSE
- campanha ampliada 10F:
  - aumentou a amostra em shadow
- review apos campanha 10F:
  - decidiu `approved_for_shadow_continuation`
  - abriu condicoes para qualquer futura conversa de `enforce`
- 10G:
  - extraiu o slice para modulo dedicado
  - criou trilha duravel local-only de evidencia
- campanha ampliada 10G:
  - repetiu o comportamento com artifacts duraveis
- 10H:
  - executou campanha cruzada com segundo harness
  - removeu a dependencia do harness unico como principal limitacao

Leitura consolidada:

- nao houve contradicao material entre as decisoes anteriores
- houve acumulacao coerente de evidencia e reducao gradual das incertezas

## Evidencia total consolidada

Amostra operacional total usada na consolidacao:

- execucoes uteis:
  - `15`
- `template_gap`:
  - `8`
- `template_ok`:
  - `7`
- `HTTP 200`:
  - `15`
- SSE preservado:
  - `15`
- `would_block=true`:
  - `8`
- `did_block=true`:
  - `0`
- `shadow_without_bleed_count`:
  - `15`
- tenants observados:
  - somente `1`
- host/contextos observados:
  - `testclient/local controlled`
  - `local/direct controlled harness`

Distribuicao por harness:

- `pre10g_testclient_local`
  - `6` execucoes
- `main_runner_direto_rota_chat`
  - `7` execucoes
- `testclient_http_harness`
  - `2` execucoes

## Blockers consolidados

Observados com repeticao estavel:

- `template_not_bound`
  - `8` ocorrencias
- `template_source_unknown`
  - `8` ocorrencias

Ainda nao observados:

- `materialization_disallowed_by_policy`
- `no_active_report`

Classificacao final:

- `template_not_bound`
  - maduro para observacao
  - parcialmente maduro para `future_enforce` muito estreito
- `template_source_unknown`
  - maduro para observacao
  - parcialmente maduro para `future_enforce` muito estreito
- `materialization_disallowed_by_policy`
  - sem base suficiente neste slice
- `no_active_report`
  - sem base suficiente neste slice

Leitura importante:

- os blockers nao observados nao impedem manter o slice em `shadow_only`
- eles precisam permanecer fora de qualquer escopo de `enforce` neste recorte
- logo, um `future_enforce` teorico neste ponto so seria admissivel, algum dia, num escopo maximamente estreito limitado aos blockers de template

## Auditoria estrutural final

Respostas claras:

- o recorte esta isolado o suficiente para shadow:
  - sim
- o recorte esta isolado o suficiente para `future_enforce` como prioridade de roadmap:
  - nao
- a extracao para modulo dedicado e a trilha duravel resolveram as maiores restricoes anteriores:
  - sim
- o branch dentro de `/app/api/chat` ainda e um risco estrutural relevante:
  - sim, para qualquer ambicao de endurecimento futuro

Leitura consolidada:

- 10G resolveu a principal fragilidade de acoplamento para observacao
- 10H adicionou um segundo caminho operacional real
- mas o recorte continua subordinado ao endpoint generico de chat/SSE
- isso nao bloqueia shadow
- isso pesa contra continuar investindo neste ponto como proximo candidato ativo de endurecimento

## Auditoria final da observabilidade

Classificacao:

- `suficiente_com_restricoes`

Racional:

- a trilha duravel do 10G e a campanha cruzada do 10H retiraram o summary em memoria do papel de fonte principal
- agora existem:
  - JSON por execucao
  - durable summary
  - artifacts por campanha
  - segundo harness
- o limite remanescente nao e mais volatilidade pura
- o limite remanescente e:
  - observabilidade local/admin-only
  - ausencia de trilha central de producao

## Decisao consolidada final

Decisao:

- `retire_from_active_focus_and_keep_as_observed_slice`

Rationale curto:

- `report_finalize_stream` ja saiu da zona de duvida: ele e estavel e seguro em `shadow_only`
- a evidencia acumulada ficou forte o suficiente para encerrar a discussao sobre repetir campanha
- o ganho marginal de continuar investindo caiu:
  - os blockers faltantes seguem estruturalmente nao observados neste recorte
  - o branch continua dentro do endpoint generico de chat
  - a observabilidade continua local-only

Condicoes objetivas para qualquer future_enforce, se um dia este slice voltar a pauta:

- limitar o escopo no maximo a `template_not_bound` e `template_source_unknown`
- manter `materialization_disallowed_by_policy` e `no_active_report` fora de qualquer `enforce` ate observacao dedicada neste proprio slice
- so reabrir discussao se houver necessidade de produto clara e rollout extremamente estreito no contexto de `/app/api/chat`

## O que isso muda no roadmap

Impacto consolidado:

- `report_finalize_stream` deve permanecer em `shadow_only` como slice observado
- nao faz sentido continuar rodando novas campanhas dedicadas deste recorte agora
- este ponto sai do foco ativo imediato
- o investimento documental ativo deve migrar para um ponto mais forte e menos acoplado ao endpoint generico de chat

## Proximo passo recomendado

- congelar `report_finalize_stream` em shadow como benchmark observado
- selecionar outro ponto documental mais forte para a proxima frente ativa
- so voltar a este recorte se surgir necessidade real de produto ou arquitetura que justifique uma conversa muito estreita de `enforce`
