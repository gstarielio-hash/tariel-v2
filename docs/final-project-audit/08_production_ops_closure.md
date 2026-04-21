# 08 Production Ops Closure

Data: 2026-04-04

## O que mudou nesta fase

A operacao de producao deixou de depender de inferencia espalhada em envs e docs. Agora existe:

- configuracao central em `web/app/core/settings.py`
- resumo operacional canônico em `web/app/domains/admin/production_ops_summary.py`
- endpoint admin `GET /admin/api/production-ops/summary`
- sinal resumido no `/ready`
- check executavel: `python3 scripts/run_production_ops_check.py --json --strict`

## Politica operacional explicitada

Uploads e anexos:

- storage mode canônico: `persistent_disk` em producao
- paths canônicos:
  - `PASTA_UPLOADS_PERFIS`
  - `PASTA_ANEXOS_MESA`
- retencao explicita:
  - perfis: `TARIEL_UPLOADS_PROFILE_RETENTION_DAYS`
  - anexos Mesa: `TARIEL_UPLOADS_MESA_RETENTION_DAYS`
- backup obrigatorio: `TARIEL_UPLOADS_BACKUP_REQUIRED=1`
- restore drill obrigatorio: `TARIEL_UPLOADS_RESTORE_DRILL_REQUIRED=1`
- cleanup automatico continua opcional e hoje segue desativado por default (`manual_review`)

Sessao:

- politica endurecida para producao: `SESSAO_FAIL_CLOSED_ON_DB_ERROR=1`
- quando combinada com `SESSAO_CACHE_DB_REVALIDACAO_SEGUNDOS=0`, a leitura oficial passa a ser:
  - `db_authoritative_with_local_cache`
  - `multi_instance_ready = true`

## Validacao executada

Check estrito em modo producao:

- `python3 scripts/run_production_ops_check.py --json --strict`
- resultado: `production_ready = true`
- blockers: nenhum
- warning remanescente: `automatic_upload_cleanup_disabled`

## Decisao canonica

A operacao real de producao pode ser considerada **fechada com ressalva operacional conhecida**:

- storage persistente, backup, restore e sessao multi-instancia agora estao explicitados e verificaveis;
- a limpeza automatica de uploads continua fora do fluxo automatico e permanece em `manual_review`.

## Leitura honesta

Depois desta fase, o gap principal de producao deixou de ser ambiguidade de politica. O que sobra e apenas uma escolha de automacao:

- manter cleanup manual como decisao consciente; ou
- automatizar limpeza/rotação em etapa futura.
