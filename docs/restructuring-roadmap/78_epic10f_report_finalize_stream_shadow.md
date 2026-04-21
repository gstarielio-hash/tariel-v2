# Epic 10F+ - abertura de `report_finalize_stream` em `shadow_only`

## Objetivo

Abrir o recorte de finalizacao via stream do inspetor no hard gate do V2 de forma:

- aditiva
- reversivel
- local/controlada
- restrita a tenant allowlisted e operation allowlisted
- sem bloquear a finalizacao real no `POST /app/api/chat`
- sem mudar payload publico nem UX

## Escopo implementado

O ponto aberto foi:

- rota:
  - `POST /app/api/chat`
- recorte:
  - branch `eh_comando_finalizar`
  - comando `COMANDO_SISTEMA FINALIZARLAUDOAGORA`
- integracao real:
  - `web/app/domains/chat/chat_stream_routes.py::rota_chat`
  - `web/app/domains/chat/laudo_service.py::_avaliar_gate_documental_finalizacao`
  - `web/app/v2/document/hard_gate.py`
- `operation_kind` aberto:
  - `report_finalize_stream`

## Como o 10F+ ficou contido

- `report_finalize_stream` entra na instrumentacao nova apenas quando todos os criterios abaixo forem verdadeiros:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - host local/controlado:
    - `127.0.0.1`
    - `::1`
    - `localhost`
    - `testclient`
  - tenant allowlisted
  - operation allowlisted com `report_finalize_stream`
- fora desse recorte, o branch do stream segue sem acionar a nova observacao documental
- dentro do recorte, a decisao canônica e calculada, registrada em `request.state` e enviada ao summary operacional

## Invariantes de `shadow_only`

- `report_finalize_stream` foi adicionado ao contrato de `operation_kind`
- o hard gate trata `report_finalize_stream` como operacao estritamente `shadow_only`
- para `report_finalize_stream`:
  - `would_block=true` apenas quando houver blockers relevantes de materializacao
  - `did_block=false` sempre nesta fase
  - `enforce_enabled=false` sempre nesta fase
- mesmo com `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`, a finalizacao via stream nao entra em `enforce_controlled`
- o side effect real do fluxo foi preservado:
  - o laudo continua mudando de `Rascunho` para `Aguardando Aval`
  - `encerrado_pelo_inspetor_em` continua sendo gravado
  - o SSE continua retornando `text/event-stream`

## Observabilidade adicionada

- o summary passa a separar o novo recorte por `operation_kind=report_finalize_stream`
- cada decisao recente agora carrega tambem:
  - `route_name`
  - `route_path`
  - `source_channel`
  - `legacy_pipeline_name`
- no recorte do stream, a rota registrada ficou:
  - `route_name=rota_chat_report_finalize_stream`
  - `route_path=/app/api/chat`
  - `source_channel=web_app_chat`
  - `legacy_pipeline_name=legacy_report_finalize_stream`

## Blockers observados na validacao real

Blockers vistos de fato em `artifacts/document_hard_gate_validation_10f/20260327_155813/`:

- no caso sem template ativo compativel:
  - `template_not_bound`
  - `template_source_unknown`
- no caso com template ativo compativel:
  - nenhum blocker relevante de materializacao permaneceu

Blockers recomendados na selecao do 10F que continuam apenas observaveis e nao foram promovidos nesta fase:

- `materialization_disallowed_by_policy`
- `no_active_report`

## Validacao operacional executada

Base de validacao:

- tenant allowlisted:
  - `1`
  - `Empresa A`
- operation allowlisted:
  - `report_finalize_stream`
- host:
  - `testclient`
- banco:
  - SQLite temporario controlado em `artifacts/document_hard_gate_validation_10f/20260327_155813/validation_10f.db`

Casos executados por HTTP real:

- `shadow_report_finalize_stream_with_template_gap`
  - HTTP `200`
  - `content-type: text/event-stream`
  - laudo persistido em `Aguardando Aval`
  - summary registrou `would_block=true` e `did_block=false`
- `shadow_report_finalize_stream_with_active_template`
  - HTTP `200`
  - `content-type: text/event-stream`
  - laudo persistido em `Aguardando Aval`
  - summary registrou `would_block=false` e `did_block=false`

Resultado agregado do summary:

- `evaluations=2`
- `would_block=1`
- `did_block=0`
- `shadow_only=2`

Artefatos principais:

- `artifacts/document_hard_gate_validation_10f/20260327_155813/runtime_summary.json`
- `artifacts/document_hard_gate_validation_10f/20260327_155813/validation_cases.json`
- `artifacts/document_hard_gate_validation_10f/20260327_155813/final_report.md`
- `artifacts/document_hard_gate_validation_10f/20260327_155813/boot_import_check.txt`

## Boot/import check

Foi executado boot/import check dedicado com:

- `PYTHONPATH=web python3 -c "import main; main.create_app(); print('boot_import_ok')"`

Resultado registrado em:

- `artifacts/document_hard_gate_validation_10f/20260327_155813/boot_import_check.txt`

## Rollback rapido

- remover `report_finalize_stream` de `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
- ou desligar `TARIEL_V2_DOCUMENT_HARD_GATE`

Nao ha migracao de banco nova nem alteracao de payload publico para desfazer.

## O que ainda falta antes de qualquer discussao de enforce

- gate review dedicado do novo recorte com base nos artifacts do 10F+
- amostra operacional maior do que os 2 casos atuais
- provar se `template_not_bound` e `template_source_unknown` permanecem consistentes neste recorte fora do harness local
- decidir se o caminho do stream deve continuar apenas como observacao ou se algum blocker maduro pode ser discutido em `enforce_controlled` futuro
